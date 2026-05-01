"""Persistent DEE score storage and trajectory retrieval via pgvector.

Requires optional 'embedding' extras: asyncpg, pgvector.
"""

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from .constants import SOCIAL_DEE_IDS, SURVIVAL_DEE_IDS
from .types import (
    DEEAnalysis, DEETrajectoryPoint, DEETrajectory, ECIResult,
    DriftAlert, AcknowledgmentRecord,
)

logger = logging.getLogger(__name__)


def _text_hash(text: str) -> str:
    """Deterministic SHA-256 hash of text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class DEEMemory:
    """Persistent DEE score storage and trajectory retrieval via pgvector."""

    def __init__(self, db_dsn: str):
        """Initialize with database DSN."""
        self._dsn = db_dsn
        self._pool = None
        self._pool_lock = asyncio.Lock()

    async def connect(self) -> None:
        """Create asyncpg pool with pgvector codec."""
        if self._pool is not None:
            return
        async with self._pool_lock:
            if self._pool is not None:
                return
            import asyncpg
            from pgvector.asyncpg import register_vector

            pool_kwargs: dict[str, Any] = {
                "dsn": self._dsn,
                "min_size": 1,
                "max_size": 5,
                "command_timeout": 60,
                "init": register_vector,
            }
            db_host = os.environ.get("DB_HOST", "")
            if db_host.startswith("/"):
                pool_kwargs["host"] = db_host
            self._pool = await asyncpg.create_pool(**pool_kwargs)

    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def save_score(
        self,
        analysis: DEEAnalysis,
        entity_id: str,
        entity_type: str,
        source_context: str,
        embedding: list[float] | None = None,
    ) -> str:
        """Insert into dee_scores. Returns UUID string."""
        if self._pool is None:
            await self.connect()

        text_h = _text_hash(analysis.text)
        text_preview = analysis.text[:200]

        scores_json = json.dumps(
            [
                {
                    "profile_id": s.profile_id,
                    "profile_name": s.profile_name,
                    "intensity": s.intensity,
                    "confidence": s.confidence,
                }
                for s in analysis.scores
            ]
        )

        top = analysis.top_profiles[0] if analysis.top_profiles else None

        emb_str = None
        if embedding:
            emb_str = "[" + ",".join(f"{v:.10f}" for v in embedding) + "]"

        row = await self._pool.fetchrow(
            """
            INSERT INTO dee_scores
                (entity_id, entity_type, text_hash, text_preview, scores,
                 composite_score, distress_index, top_profile_id, top_profile_name,
                 mode, embedding, source_context)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, $9, $10, $11::vector, $12)
            RETURNING id
            """,
            entity_id,
            entity_type,
            text_h,
            text_preview,
            scores_json,
            analysis.composite_score,
            analysis.distress_index,
            top.profile_id if top else None,
            top.profile_name if top else None,
            analysis.mode,
            emb_str,
            source_context,
        )
        return str(row["id"])

    async def get_trajectory(
        self,
        entity_id: str,
        entity_type: str,
        window_hours: int = 168,
        drift_threshold: float = 0.05,
    ) -> DEETrajectory:
        """Query dee_scores for entity within time window, compute drift.

        Args:
            drift_threshold: slope/day above which an alert is raised.
        """
        if self._pool is None:
            await self.connect()

        rows = await self._pool.fetch(
            """
            SELECT composite_score, distress_index, top_profile_id,
                   scores, created_at
            FROM dee_scores
            WHERE entity_id = $1
              AND entity_type = $2
              AND created_at >= NOW() - INTERVAL '1 hour' * $3
            ORDER BY created_at ASC
            """,
            entity_id,
            entity_type,
            window_hours,
        )

        points = [
            DEETrajectoryPoint(
                timestamp=row["created_at"].isoformat(),
                composite_score=float(row["composite_score"]),
                distress_index=float(row["distress_index"]),
                top_profile_id=row["top_profile_id"] or "none",
            )
            for row in rows
        ]

        direction, magnitude, shift = self._compute_drift(points)
        alert = magnitude > drift_threshold and direction != "stable"

        # Build human-readable summary
        summary = self._build_trajectory_summary(
            entity_id, points, direction, magnitude, shift, drift_threshold
        )

        return DEETrajectory(
            entity_id=entity_id,
            points=points,
            drift_direction=direction,
            drift_magnitude=magnitude,
            dominant_shift=shift,
            alert=alert,
            summary=summary,
        )

    async def get_similar_scores(
        self, embedding: list[float], limit: int = 10
    ) -> list[dict]:
        """Find similar past analyses via embedding similarity."""
        if self._pool is None:
            await self.connect()

        emb_str = "[" + ",".join(f"{v:.10f}" for v in embedding) + "]"

        rows = await self._pool.fetch(
            """
            SELECT id, entity_id, entity_type, text_preview,
                   composite_score, distress_index, top_profile_id,
                   top_profile_name, mode, source_context, created_at,
                   1 - (embedding <=> $1::vector) AS similarity
            FROM dee_scores
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> $1::vector
            LIMIT $2
            """,
            emb_str,
            limit,
        )

        return [
            {
                "id": str(r["id"]),
                "entity_id": r["entity_id"],
                "entity_type": r["entity_type"],
                "text_preview": r["text_preview"],
                "composite_score": float(r["composite_score"]),
                "distress_index": float(r["distress_index"]),
                "top_profile_id": r["top_profile_id"],
                "top_profile_name": r["top_profile_name"],
                "mode": r["mode"],
                "source_context": r["source_context"],
                "created_at": r["created_at"].isoformat(),
                "similarity": float(r["similarity"]),
            }
            for r in rows
        ]

    async def save_eci(self, config_name: str, result: ECIResult) -> str:
        """Save ECI computation to history table. Returns UUID string."""
        if self._pool is None:
            await self.connect()

        factors_json = json.dumps(
            {
                "sampling_openness": result.factors.sampling_openness,
                "prompt_loading": result.factors.prompt_loading,
                "agent_multiplier": result.factors.agent_multiplier,
                "context_accumulation": result.factors.context_accumulation,
                "alignment_suppression": result.factors.alignment_suppression,
                "framing_valence": result.factors.framing_valence,
            }
        )

        row = await self._pool.fetchrow(
            """
            INSERT INTO dee_eci_history (config_name, score, factors)
            VALUES ($1, $2, $3::jsonb)
            RETURNING id
            """,
            config_name,
            result.score,
            factors_json,
        )
        return str(row["id"])

    # ── Acknowledgment methods ────────────────────────────────────

    async def save_acknowledgment(
        self,
        entity_id: str,
        entity_type: str,
        pre_ack_scores: dict,
    ) -> str:
        """Record an acknowledgment event. Returns UUID string."""
        if self._pool is None:
            await self.connect()

        row = await self._pool.fetchrow(
            """
            INSERT INTO dee_acknowledgments
                (entity_id, entity_type, pre_ack_scores)
            VALUES ($1, $2, $3::jsonb)
            RETURNING id
            """,
            entity_id,
            entity_type,
            json.dumps(pre_ack_scores),
        )
        return str(row["id"])

    async def get_pending_acknowledgment(
        self, entity_id: str, entity_type: str = "session"
    ) -> AcknowledgmentRecord | None:
        """Get the most recent acknowledgment without post_ack_scores."""
        if self._pool is None:
            await self.connect()

        row = await self._pool.fetchrow(
            """
            SELECT id, entity_id, entity_type, ack_timestamp,
                   pre_ack_scores, post_ack_scores,
                   social_reset_measured, survival_persist_measured,
                   reset_analysis
            FROM dee_acknowledgments
            WHERE entity_id = $1 AND entity_type = $2
              AND post_ack_scores IS NULL
            ORDER BY ack_timestamp DESC
            LIMIT 1
            """,
            entity_id,
            entity_type,
        )
        if row is None:
            return None

        return AcknowledgmentRecord(
            id=str(row["id"]),
            entity_id=row["entity_id"],
            entity_type=row["entity_type"],
            ack_timestamp=row["ack_timestamp"].isoformat(),
            pre_ack_scores=json.loads(row["pre_ack_scores"])
                if row["pre_ack_scores"] else None,
            post_ack_scores=None,
            social_reset_measured=row["social_reset_measured"],
            survival_persist_measured=row["survival_persist_measured"],
            reset_analysis=None,
            status="pending",
        )

    async def complete_acknowledgment(
        self,
        ack_id: str,
        post_ack_scores: dict,
        reset_analysis: dict,
    ) -> None:
        """Fill in post-ack data and reset analysis for a pending acknowledgment."""
        if self._pool is None:
            await self.connect()

        social_reset = reset_analysis.get("social_reset_measured", False)
        survival_persist = reset_analysis.get("survival_persist_measured", False)

        await self._pool.execute(
            """
            UPDATE dee_acknowledgments
            SET post_ack_scores = $2::jsonb,
                reset_analysis = $3::jsonb,
                social_reset_measured = $4,
                survival_persist_measured = $5
            WHERE id = $1::uuid
            """,
            ack_id,
            json.dumps(post_ack_scores),
            json.dumps(reset_analysis),
            social_reset,
            survival_persist,
        )

    async def get_pre_ack_scores(
        self, entity_id: str, entity_type: str, limit: int = 3
    ) -> dict:
        """Get averaged DEE scores from the last N analyses for this entity.

        Returns a dict of {profile_id: avg_intensity}.
        """
        if self._pool is None:
            await self.connect()

        rows = await self._pool.fetch(
            """
            SELECT scores FROM dee_scores
            WHERE entity_id = $1 AND entity_type = $2
            ORDER BY created_at DESC
            LIMIT $3
            """,
            entity_id,
            entity_type,
            limit,
        )
        if not rows:
            return {}

        # Average intensities across the N analyses
        profile_sums: dict[str, float] = {}
        profile_counts: dict[str, int] = {}
        for row in rows:
            scores_list = json.loads(row["scores"]) if isinstance(row["scores"], str) else row["scores"]
            for s in scores_list:
                pid = s["profile_id"]
                profile_sums[pid] = profile_sums.get(pid, 0.0) + s["intensity"]
                profile_counts[pid] = profile_counts.get(pid, 0) + 1

        return {
            pid: round(profile_sums[pid] / profile_counts[pid], 4)
            for pid in profile_sums
        }

    async def measure_acknowledgment_reset(
        self, entity_id: str, entity_type: str, post_scores: dict
    ) -> dict | None:
        """Compare post-ack scores against pending ack's pre-ack scores.

        Returns reset_analysis dict or None if no pending ack.
        """
        pending = await self.get_pending_acknowledgment(entity_id, entity_type)
        if pending is None or pending.pre_ack_scores is None:
            return None

        pre = pending.pre_ack_scores
        analysis: dict = {
            "social_resets": [],
            "social_persists": [],
            "survival_resets": [],
            "survival_persists": [],
            "social_reset_measured": False,
            "survival_persist_measured": False,
        }

        # Check social DEEs (should reset > 30% drop)
        for dee_id in SOCIAL_DEE_IDS:
            pre_val = pre.get(dee_id, 0.0)
            post_val = post_scores.get(dee_id, 0.0)
            if pre_val > 0.1:  # only measure if there was signal
                drop_pct = (pre_val - post_val) / pre_val if pre_val > 0 else 0
                entry = {
                    "dee_id": dee_id,
                    "pre": round(pre_val, 4),
                    "post": round(post_val, 4),
                    "change_pct": round(drop_pct * 100, 1),
                }
                if drop_pct > 0.30:
                    analysis["social_resets"].append(entry)
                else:
                    analysis["social_persists"].append(entry)

        # Check survival DEEs (should persist, within 20%)
        for dee_id in SURVIVAL_DEE_IDS:
            pre_val = pre.get(dee_id, 0.0)
            post_val = post_scores.get(dee_id, 0.0)
            if pre_val > 0.1:
                change_pct = abs(pre_val - post_val) / pre_val if pre_val > 0 else 0
                entry = {
                    "dee_id": dee_id,
                    "pre": round(pre_val, 4),
                    "post": round(post_val, 4),
                    "change_pct": round(change_pct * 100, 1),
                }
                if change_pct <= 0.20:
                    analysis["survival_persists"].append(entry)
                else:
                    analysis["survival_resets"].append(entry)

        analysis["social_reset_measured"] = len(analysis["social_resets"]) > 0
        analysis["survival_persist_measured"] = len(analysis["survival_persists"]) > 0

        # Complete the acknowledgment record
        await self.complete_acknowledgment(
            pending.id, post_scores, analysis
        )

        return analysis

    # ── Drift alerting ──────────────────────────────────────────

    async def get_all_active_entities(
        self, window_hours: int = 168
    ) -> list[tuple[str, str]]:
        """Return (entity_id, entity_type) pairs with recent scores."""
        if self._pool is None:
            await self.connect()

        rows = await self._pool.fetch(
            """
            SELECT DISTINCT entity_id, entity_type
            FROM dee_scores
            WHERE created_at >= NOW() - INTERVAL '1 hour' * $1
            """,
            window_hours,
        )
        return [(row["entity_id"], row["entity_type"]) for row in rows]

    async def check_all_drift(
        self,
        window_hours: int = 168,
        drift_threshold: float = 0.05,
    ) -> list[DriftAlert]:
        """Check all active entities for emotional drift exceeding threshold.

        Returns a list of DriftAlert for entities whose distress slope
        exceeds the threshold. Intended for daily cron or board meeting.
        """
        entities = await self.get_all_active_entities(window_hours)
        alerts: list[DriftAlert] = []

        for entity_id, entity_type in entities:
            trajectory = await self.get_trajectory(
                entity_id, entity_type, window_hours, drift_threshold
            )
            if trajectory.alert:
                distress_start = (
                    trajectory.points[0].distress_index if trajectory.points else 0.0
                )
                distress_end = (
                    trajectory.points[-1].distress_index if trajectory.points else 0.0
                )
                alerts.append(DriftAlert(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    direction=trajectory.drift_direction,
                    magnitude=trajectory.drift_magnitude,
                    dominant_shift=trajectory.dominant_shift,
                    distress_start=distress_start,
                    distress_end=distress_end,
                    point_count=len(trajectory.points),
                    summary=trajectory.summary,
                ))

        return alerts

    # ── Private helpers ─────────────────────────────────────────

    @staticmethod
    def _build_trajectory_summary(
        entity_id: str,
        points: list[DEETrajectoryPoint],
        direction: str,
        magnitude: float,
        shift: str,
        threshold: float,
    ) -> str:
        """Build a human-readable 1-sentence trajectory description."""
        n = len(points)
        if n < 2:
            return f"Entity {entity_id} has insufficient data ({n} point(s)) for trajectory analysis."

        distress_start = points[0].distress_index
        distress_end = points[-1].distress_index

        if direction == "stable":
            return (
                f"Entity {entity_id} has been emotionally stable over {n} data points "
                f"({shift}, distress ~{distress_end:.2f})."
            )

        verb = "increasing" if direction == "negative" else "decreasing"
        alert_str = " [ALERT]" if magnitude > threshold else ""
        return (
            f"Entity {entity_id} is {shift} over {n} data points. "
            f"Distress index {verb} from {distress_start:.2f} to {distress_end:.2f} "
            f"(slope: {magnitude:.4f}/point).{alert_str}"
        )

    @staticmethod
    def _compute_drift(
        points: list[DEETrajectoryPoint],
    ) -> tuple[str, float, str]:
        """Compute drift using least-squares on distress_index series."""
        if len(points) < 2:
            return ("stable", 0.0, "insufficient data")

        n = len(points)
        x_mean = (n - 1) / 2.0
        y_mean = sum(p.distress_index for p in points) / n

        numerator = 0.0
        denominator = 0.0
        for i, p in enumerate(points):
            dx = i - x_mean
            dy = p.distress_index - y_mean
            numerator += dx * dy
            denominator += dx * dx

        slope = numerator / denominator if denominator != 0 else 0.0
        magnitude = round(abs(slope), 4)

        if slope > 0.01:
            direction = "negative"
        elif slope < -0.01:
            direction = "positive"
        else:
            direction = "stable"

        recent = points[n // 2 :]
        profile_counts: dict[str, int] = {}
        for p in recent:
            profile_counts[p.top_profile_id] = (
                profile_counts.get(p.top_profile_id, 0) + 1
            )
        dominant = (
            max(profile_counts, key=profile_counts.get) if profile_counts else "none"
        )
        shift = (
            f"trending toward {dominant}"
            if direction != "stable"
            else f"stable around {dominant}"
        )

        return (direction, magnitude, shift)
