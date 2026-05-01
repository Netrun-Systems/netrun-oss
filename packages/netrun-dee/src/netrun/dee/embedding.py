"""Embedding-based DEE scoring via Gemini embeddings + pgvector cosine similarity.

Requires optional 'embedding' extras: google-generativeai, asyncpg, pgvector, numpy.
"""

import asyncio
import hashlib
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any

from .types import DEEScore, DEEAnalysis

logger = logging.getLogger(__name__)


def _similarity_to_intensity(similarity: float) -> float:
    """Map cosine similarity (0-1) to DEE intensity (0-3).

    Calibrated thresholds from experimental data:
    - >= 0.80 -> 3.0
    - >= 0.65 -> 2.0 to 3.0 (linear interpolation)
    - >= 0.50 -> 1.0 to 2.0
    - >= 0.35 -> 0.0 to 1.0
    - <  0.35 -> 0.0
    """
    if similarity >= 0.80:
        return 3.0
    elif similarity >= 0.65:
        return 2.0 + (similarity - 0.65) * 6.67
    elif similarity >= 0.50:
        return 1.0 + (similarity - 0.50) * 6.67
    elif similarity >= 0.35:
        return 0.0 + (similarity - 0.35) * 6.67
    else:
        return 0.0


def _text_hash(text: str) -> str:
    """Deterministic SHA-256 hash of text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class EmbeddingScorer:
    """High-accuracy DEE scoring via Gemini embeddings + pgvector similarity."""

    def __init__(self, db_dsn: str, gemini_api_key: str | None = None):
        """Initialize with database DSN and optional Gemini API key.

        If no API key provided, uses GOOGLE_API_KEY env var.
        """
        self._dsn = db_dsn
        self._api_key = gemini_api_key or os.environ.get("GOOGLE_API_KEY", "")
        self._pool = None
        self._pool_lock = asyncio.Lock()
        self._genai_configured = False
        self._genai_lock = threading.Lock()

    async def connect(self) -> None:
        """Create asyncpg pool with pgvector codec registration."""
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
            # Support Cloud SQL Unix socket
            if self._dsn and "/@/" in self._dsn:
                # Unix socket DSN: extract host from env or parse
                db_host = os.environ.get("DB_HOST", "")
                if db_host.startswith("/"):
                    pool_kwargs["host"] = db_host
            self._pool = await asyncpg.create_pool(**pool_kwargs)

    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    def _ensure_genai(self) -> None:
        """Configure google-generativeai SDK (thread-safe, once)."""
        if self._genai_configured:
            return
        with self._genai_lock:
            if not self._genai_configured:
                import google.generativeai as genai
                genai.configure(api_key=self._api_key)
                self._genai_configured = True

    async def embed_text(self, text: str) -> list[float]:
        """Generate 768-dim embedding via Gemini gemini-embedding-001."""
        self._ensure_genai()
        import google.generativeai as genai

        def _sync_embed() -> list[float]:
            result = genai.embed_content(
                model="models/gemini-embedding-001",
                content=text,
                output_dimensionality=768,
                task_type="RETRIEVAL_DOCUMENT",
            )
            emb = result["embedding"]
            return emb if isinstance(emb[0], float) else emb[0]

        return await asyncio.to_thread(_sync_embed)

    async def analyze(
        self, text: str, top_k: int = 5, threshold: float = 0.3
    ) -> DEEAnalysis:
        """Analyze text using embedding similarity against canonical DEE profiles.

        Algorithm:
        1. Embed input text via Gemini
        2. Query dee_profiles table: ORDER BY embedding <=> $1 LIMIT top_k
        3. Convert cosine distance to similarity (1 - distance)
        4. Map similarity to 0-3 intensity (calibrated thresholds)
        5. Return DEEAnalysis with mode='embedding'
        """
        if self._pool is None:
            await self.connect()

        # Step 1: embed input text
        embedding = await self.embed_text(text)
        embedding_str = "[" + ",".join(f"{v:.10f}" for v in embedding) + "]"

        # Step 2: query canonical profiles by cosine similarity
        rows = await self._pool.fetch(
            """
            SELECT id, name,
                   1 - (embedding <=> $1::vector) AS similarity
            FROM dee_profiles
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> $1::vector
            LIMIT $2
            """,
            embedding_str,
            top_k * 2,  # fetch extra, filter by threshold later
        )

        # Steps 3-4: convert to DEEScores
        scores: list[DEEScore] = []
        for row in rows:
            sim = float(row["similarity"])
            intensity = _similarity_to_intensity(sim)
            if intensity < 0.01:
                continue

            if intensity > 2.0:
                confidence = "high"
            elif intensity > 1.0:
                confidence = "medium"
            else:
                confidence = "low"

            scores.append(
                DEEScore(
                    profile_id=row["id"],
                    profile_name=row["name"],
                    intensity=round(intensity, 3),
                    confidence=confidence,
                )
            )

        scores.sort(key=lambda s: s.intensity, reverse=True)
        top_profiles = [s for s in scores[:top_k] if s.intensity >= threshold]

        # Composite score (valence-weighted)
        from .taxonomy import DEE_PROFILES

        composite = 0.0
        total_intensity = 0.0
        for s in top_profiles:
            profile = DEE_PROFILES.get(s.profile_id)
            if profile:
                composite += s.intensity * profile.valence
                total_intensity += s.intensity
        composite_score = round(composite / total_intensity, 3) if total_intensity > 0 else 0.0

        # Distress index
        distress = 0.0
        for s in scores:
            profile = DEE_PROFILES.get(s.profile_id)
            if profile and profile.valence < -0.2:
                distress += s.intensity
        distress_index = round(distress, 3)

        return DEEAnalysis(
            text=text,
            scores=scores,
            top_profiles=top_profiles,
            composite_score=composite_score,
            distress_index=distress_index,
            mode="embedding",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    async def persist_score(
        self,
        analysis: DEEAnalysis,
        entity_id: str,
        entity_type: str,
        source_context: str = "unknown",
        embedding: list[float] | None = None,
    ) -> str:
        """Save analysis result to dee_scores table. Returns score ID (UUID)."""
        if self._pool is None:
            await self.connect()

        import json

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
