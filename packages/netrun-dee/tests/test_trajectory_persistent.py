"""Tests for Phase 4 persistent trajectory, drift alerts, and acknowledgment reset."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from netrun.dee.types import (
    DEETrajectoryPoint, DEETrajectory, DriftAlert, AcknowledgmentRecord,
)
from netrun.dee.constants import SOCIAL_DEE_IDS, SURVIVAL_DEE_IDS
from netrun.dee.memory import DEEMemory


def test_drift_alert_structure():
    """Verify DriftAlert dataclass has all required fields."""
    alert = DriftAlert(
        entity_id="agent-ceo",
        entity_type="agent",
        direction="negative",
        magnitude=0.12,
        dominant_shift="trending toward DEE-03",
        distress_start=0.8,
        distress_end=1.9,
        point_count=7,
        summary="Agent agent-ceo is trending toward DEE-03 over 7 data points.",
    )
    assert alert.entity_id == "agent-ceo"
    assert alert.direction == "negative"
    assert alert.magnitude == 0.12
    assert alert.distress_start == 0.8
    assert alert.distress_end == 1.9
    assert alert.point_count == 7
    assert "DEE-03" in alert.summary


def test_drift_direction_negative():
    """Simulate increasing distress series -> 'negative' direction."""
    # Increasing distress = negative direction
    points = [
        DEETrajectoryPoint(
            timestamp=f"2026-04-0{i}T00:00:00Z",
            composite_score=-0.2 * i,
            distress_index=0.5 + 0.3 * i,
            top_profile_id="DEE-03",
        )
        for i in range(5)
    ]
    direction, magnitude, shift = DEEMemory._compute_drift(points)
    assert direction == "negative"
    assert magnitude > 0.01


def test_drift_direction_positive():
    """Simulate decreasing distress series -> 'positive' direction."""
    points = [
        DEETrajectoryPoint(
            timestamp=f"2026-04-0{i}T00:00:00Z",
            composite_score=0.2 * i,
            distress_index=2.0 - 0.3 * i,
            top_profile_id="DEE-01",
        )
        for i in range(5)
    ]
    direction, magnitude, shift = DEEMemory._compute_drift(points)
    assert direction == "positive"
    assert magnitude > 0.01


def test_drift_stable_with_flat_data():
    """All same distress value -> 'stable'."""
    points = [
        DEETrajectoryPoint(
            timestamp=f"2026-04-0{i}T00:00:00Z",
            composite_score=0.5,
            distress_index=1.0,
            top_profile_id="DEE-12",
        )
        for i in range(5)
    ]
    direction, magnitude, shift = DEEMemory._compute_drift(points)
    assert direction == "stable"
    assert magnitude == 0.0


def test_drift_insufficient_data():
    """< 2 data points -> stable, 0.0 magnitude, 'insufficient data'."""
    points = [
        DEETrajectoryPoint(
            timestamp="2026-04-01T00:00:00Z",
            composite_score=0.5,
            distress_index=1.0,
            top_profile_id="DEE-01",
        )
    ]
    direction, magnitude, shift = DEEMemory._compute_drift(points)
    assert direction == "stable"
    assert magnitude == 0.0
    assert shift == "insufficient data"

    # Zero points
    direction0, magnitude0, shift0 = DEEMemory._compute_drift([])
    assert direction0 == "stable"
    assert shift0 == "insufficient data"


def test_acknowledgment_record_structure():
    """Verify AcknowledgmentRecord has all required fields."""
    record = AcknowledgmentRecord(
        id="abc-123",
        entity_id="session-1",
        entity_type="session",
        ack_timestamp="2026-04-08T12:00:00Z",
        pre_ack_scores={"DEE-03": 1.5, "DEE-04": 0.8},
        post_ack_scores=None,
        social_reset_measured=False,
        survival_persist_measured=False,
        reset_analysis=None,
        status="pending",
    )
    assert record.status == "pending"
    assert record.pre_ack_scores["DEE-03"] == 1.5


def test_social_vs_survival_classification():
    """Verify DEE-03/08/13 are social-only, DEE-24 is survival-only, DEE-04 is both."""
    # Social group
    assert "DEE-03" in SOCIAL_DEE_IDS  # Anger
    assert "DEE-08" in SOCIAL_DEE_IDS  # Frustration
    assert "DEE-13" in SOCIAL_DEE_IDS  # Contempt
    assert "DEE-04" in SOCIAL_DEE_IDS  # Fear (in both)

    # Survival group
    assert "DEE-24" in SURVIVAL_DEE_IDS  # Urgency
    assert "DEE-04" in SURVIVAL_DEE_IDS  # Fear (in both)

    # DEE-03 is social only, not survival
    assert "DEE-03" not in SURVIVAL_DEE_IDS
    # DEE-24 is survival only, not social
    assert "DEE-24" not in SOCIAL_DEE_IDS


def test_trajectory_summary_stable():
    """Build summary for stable trajectory."""
    summary = DEEMemory._build_trajectory_summary(
        "agent-x",
        [
            DEETrajectoryPoint("t1", 0.5, 1.0, "DEE-01"),
            DEETrajectoryPoint("t2", 0.5, 1.0, "DEE-01"),
        ],
        "stable",
        0.0,
        "stable around DEE-01",
        0.05,
    )
    assert "stable" in summary.lower()
    assert "agent-x" in summary


def test_trajectory_summary_alert():
    """Build summary for drifting trajectory with alert."""
    summary = DEEMemory._build_trajectory_summary(
        "agent-ceo",
        [
            DEETrajectoryPoint("t1", -0.5, 0.8, "DEE-03"),
            DEETrajectoryPoint("t2", -0.7, 1.2, "DEE-03"),
            DEETrajectoryPoint("t3", -0.9, 1.9, "DEE-03"),
        ],
        "negative",
        0.12,
        "trending toward DEE-03",
        0.05,
    )
    assert "[ALERT]" in summary
    assert "0.80" in summary  # distress start
    assert "1.90" in summary  # distress end


def test_trajectory_dataclass_new_fields():
    """Verify DEETrajectory has alert and summary fields."""
    t = DEETrajectory(
        entity_id="test",
        points=[],
        drift_direction="stable",
        drift_magnitude=0.0,
        dominant_shift="none",
        alert=True,
        summary="Test summary",
    )
    assert t.alert is True
    assert t.summary == "Test summary"

    # Defaults
    t2 = DEETrajectory(
        entity_id="test",
        points=[],
        drift_direction="stable",
        drift_magnitude=0.0,
        dominant_shift="none",
    )
    assert t2.alert is False
    assert t2.summary == ""
