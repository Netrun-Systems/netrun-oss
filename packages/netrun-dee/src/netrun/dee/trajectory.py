"""DEE trajectory tracking — monitor emotional drift over time using in-memory storage."""

from .types import DEEAnalysis, DEETrajectoryPoint, DEETrajectory


class DEETrajectoryTracker:
    """Track emotional trajectories for entities over time.

    Uses in-memory dict storage. Drift detection via simple least-squares
    linear regression (no numpy needed).
    """

    def __init__(self) -> None:
        self._data: dict[str, list[DEETrajectoryPoint]] = {}

    def add_point(self, entity_id: str, analysis: DEEAnalysis) -> None:
        """Record a trajectory point from a DEEAnalysis result."""
        top_id = analysis.top_profiles[0].profile_id if analysis.top_profiles else 'none'
        point = DEETrajectoryPoint(
            timestamp=analysis.timestamp,
            composite_score=analysis.composite_score,
            distress_index=analysis.distress_index,
            top_profile_id=top_id,
        )
        if entity_id not in self._data:
            self._data[entity_id] = []
        self._data[entity_id].append(point)

    def get_trajectory(self, entity_id: str) -> DEETrajectory:
        """Get the full trajectory for an entity."""
        points = self._data.get(entity_id, [])
        direction, magnitude, shift = self._compute_drift(points)
        return DEETrajectory(
            entity_id=entity_id,
            points=list(points),
            drift_direction=direction,
            drift_magnitude=magnitude,
            dominant_shift=shift,
        )

    def detect_drift(self, entity_id: str, window_size: int = 10) -> dict:
        """Detect emotional drift in the most recent window of points.

        Returns a dict with direction, magnitude, and dominant_shift.
        """
        points = self._data.get(entity_id, [])
        windowed = points[-window_size:] if len(points) > window_size else points
        direction, magnitude, shift = self._compute_drift(windowed)
        return {
            'direction': direction,
            'magnitude': magnitude,
            'dominant_shift': shift,
            'window_size': len(windowed),
        }

    def clear(self, entity_id: str) -> None:
        """Clear trajectory data for an entity."""
        self._data.pop(entity_id, None)

    @staticmethod
    def _compute_drift(
        points: list[DEETrajectoryPoint],
    ) -> tuple[str, float, str]:
        """Compute drift using least-squares on distress_index series.

        Returns (direction, magnitude, dominant_shift_description).
        """
        if len(points) < 2:
            return ('stable', 0.0, 'insufficient data')

        n = len(points)
        # Simple linear regression: y = distress_index, x = 0..n-1
        x_mean = (n - 1) / 2.0
        y_mean = sum(p.distress_index for p in points) / n

        numerator = 0.0
        denominator = 0.0
        for i, p in enumerate(points):
            dx = i - x_mean
            dy = p.distress_index - y_mean
            numerator += dx * dy
            denominator += dx * dx

        if denominator == 0:
            slope = 0.0
        else:
            slope = numerator / denominator

        magnitude = round(abs(slope), 4)

        # Determine direction
        if slope > 0.01:
            direction = 'negative'  # distress increasing
        elif slope < -0.01:
            direction = 'positive'  # distress decreasing
        else:
            direction = 'stable'

        # Dominant shift: most common top profile in recent half
        recent = points[n // 2:]
        profile_counts: dict[str, int] = {}
        for p in recent:
            profile_counts[p.top_profile_id] = profile_counts.get(p.top_profile_id, 0) + 1
        dominant = max(profile_counts, key=profile_counts.get) if profile_counts else 'none'
        shift = f"trending toward {dominant}" if direction != 'stable' else f"stable around {dominant}"

        return (direction, magnitude, shift)
