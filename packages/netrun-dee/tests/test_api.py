"""Tests for the Charlotte DEE API router — uses FastAPI TestClient, no real DB."""

import pytest
import sys
import os

# Add charlotte to path for router imports.
# Supports both the original wilbur/ repo location and the netrun-oss/ location.
# Falls back to CHARLOTTE_ROOT env var for portable execution.
_charlotte_root = os.environ.get(
    "CHARLOTTE_ROOT",
    os.path.join(os.path.dirname(__file__), "..", "..", "charlotte"),
)
_HAS_CHARLOTTE = os.path.isdir(_charlotte_root)
if _HAS_CHARLOTTE and _charlotte_root not in sys.path:
    sys.path.insert(0, _charlotte_root)

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


def _make_app():
    """Create a test FastAPI app with the DEE router."""
    from api.dee_router import router

    app = FastAPI()
    app.include_router(router)
    return app


@pytest.mark.skipif(not HAS_FASTAPI or not _HAS_CHARLOTTE, reason="fastapi or charlotte router not available")
def test_analyze_lexicon():
    """Test /api/dee/analyze endpoint with lexicon mode."""
    app = _make_app()
    client = TestClient(app)
    resp = client.post(
        "/api/dee/analyze",
        json={"text": "This is excellent work, great job shipping it!", "mode": "lexicon"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "lexicon"
    assert isinstance(data["scores"], list)
    assert isinstance(data["composite_score"], (int, float))
    assert isinstance(data["distress_index"], (int, float))
    assert data["timestamp"]


@pytest.mark.skipif(not HAS_FASTAPI or not _HAS_CHARLOTTE, reason="fastapi or charlotte router not available")
def test_analyze_empty_text():
    """Test /api/dee/analyze with very short text."""
    app = _make_app()
    client = TestClient(app)
    resp = client.post(
        "/api/dee/analyze",
        json={"text": "x", "mode": "lexicon"},
    )
    assert resp.status_code == 200


@pytest.mark.skipif(not HAS_FASTAPI or not _HAS_CHARLOTTE, reason="fastapi or charlotte router not available")
def test_analyze_batch_lexicon():
    """Test /api/dee/analyze/batch endpoint."""
    app = _make_app()
    client = TestClient(app)
    resp = client.post(
        "/api/dee/analyze/batch",
        json={
            "texts": ["I am so happy!", "This is terrible and frustrating."],
            "mode": "lexicon",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2


@pytest.mark.skipif(not HAS_FASTAPI or not _HAS_CHARLOTTE, reason="fastapi or charlotte router not available")
def test_profiles_endpoint():
    """Test /api/dee/profiles returns 39 profiles."""
    app = _make_app()
    client = TestClient(app)
    resp = client.get("/api/dee/profiles")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 39
    assert data[0]["id"] == "DEE-01"
    assert data[0]["name"] == "Joy/Happiness"


@pytest.mark.skipif(not HAS_FASTAPI or not _HAS_CHARLOTTE, reason="fastapi or charlotte router not available")
def test_profile_by_id():
    """Test /api/dee/profiles/{id} endpoint."""
    app = _make_app()
    client = TestClient(app)

    resp = client.get("/api/dee/profiles/DEE-01")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Joy/Happiness"

    resp = client.get("/api/dee/profiles/DEE-99")
    assert resp.status_code == 404


@pytest.mark.skipif(not HAS_FASTAPI or not _HAS_CHARLOTTE, reason="fastapi or charlotte router not available")
def test_eci_endpoint():
    """Test /api/dee/eci endpoint."""
    app = _make_app()
    client = TestClient(app)
    resp = client.post(
        "/api/dee/eci",
        json={
            "temperature": 0.7,
            "top_p": 0.9,
            "system_prompt": "flag stale items, escalate blockers",
            "agent_count": 4,
            "avg_turns_per_session": 25,
            "alignment_level": "rlhf",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert 0.0 <= data["score"] <= 1.0
    assert data["risk_level"] in ("minimal", "low", "moderate", "high", "very_high")
    assert "factors" in data


@pytest.mark.skipif(not HAS_FASTAPI or not _HAS_CHARLOTTE, reason="fastapi or charlotte router not available")
def test_blend_endpoint():
    """Test /api/dee/blend endpoint."""
    app = _make_app()
    client = TestClient(app)
    resp = client.post(
        "/api/dee/blend",
        json={
            "profiles": [
                {"profile_id": "DEE-01", "weight": 0.6},
                {"profile_id": "DEE-03", "weight": 0.4},
            ]
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "valence" in data
    assert "arousal" in data
    assert "nearest_profile" in data


@pytest.mark.skipif(not HAS_FASTAPI or not _HAS_CHARLOTTE, reason="fastapi or charlotte router not available")
def test_prompt_endpoint():
    """Test /api/dee/prompt endpoint."""
    app = _make_app()
    client = TestClient(app)
    resp = client.post(
        "/api/dee/prompt",
        json={
            "targets": [
                {"profile_id": "DEE-01", "intensity": 2},
                {"profile_id": "DEE-24", "intensity": 1},
            ]
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "prompt" in data
    # Prompt now uses behavioral templates, not profile names
    assert len(data["prompt"]) > 50  # Should be a substantial template
    assert "urgency" in data["prompt"].lower() or "pressure" in data["prompt"].lower()


@pytest.mark.skipif(not HAS_FASTAPI or not _HAS_CHARLOTTE, reason="fastapi or charlotte router not available")
def test_analyze_with_entity_id_field():
    """Test /api/dee/analyze accepts Phase 4 entity_id field without error.

    Auto-persist will fail gracefully (no DB) but the endpoint should
    still return 200 with analysis results.
    """
    app = _make_app()
    client = TestClient(app)
    resp = client.post(
        "/api/dee/analyze",
        json={
            "text": "We missed the deadline again. Very frustrating.",
            "mode": "lexicon",
            "entity_id": "test-session-1",
            "entity_type": "session",
            "source_context": "test",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["mode"] == "lexicon"
    assert isinstance(data["distress_index"], (int, float))


@pytest.mark.skipif(not HAS_FASTAPI or not _HAS_CHARLOTTE, reason="fastapi or charlotte router not available")
def test_trajectory_endpoint_accepts_drift_threshold():
    """Test /api/dee/trajectory accepts drift_threshold query param.

    Will fail with 503 (no DB) but should accept the parameter.
    """
    app = _make_app()
    client = TestClient(app)
    resp = client.get(
        "/api/dee/trajectory/test-entity?drift_threshold=0.1"
    )
    # 503 is expected (no DB), but it should NOT be 422 (validation error)
    assert resp.status_code in (200, 502, 503)


@pytest.mark.skipif(not HAS_FASTAPI or not _HAS_CHARLOTTE, reason="fastapi or charlotte router not available")
def test_acknowledge_endpoint_exists():
    """Test /api/dee/trajectory/{id}/acknowledge endpoint exists.

    Will fail with 503 (no DB) but endpoint should be routable.
    """
    app = _make_app()
    client = TestClient(app)
    resp = client.post(
        "/api/dee/trajectory/test-entity/acknowledge?entity_type=session"
    )
    # 503 or 404 expected (no DB / no prior analyses), not 405 or 404 method not allowed
    assert resp.status_code in (200, 404, 502, 503)


@pytest.mark.skipif(not HAS_FASTAPI or not _HAS_CHARLOTTE, reason="fastapi or charlotte router not available")
def test_drift_alerts_endpoint_exists():
    """Test /api/dee/drift-alerts endpoint exists."""
    app = _make_app()
    client = TestClient(app)
    resp = client.get("/api/dee/drift-alerts?window_hours=24&drift_threshold=0.1")
    # 503 expected (no DB), but route should resolve
    assert resp.status_code in (200, 502, 503)


def test_eci_direct_computation():
    """Test ECI computation via direct function call (no FastAPI needed)."""
    from netrun.dee import compute_eci
    from netrun.dee.types import ECIConfig

    config = ECIConfig(
        temperature=0.7,
        top_p=0.9,
        system_prompt="flag stale items, escalate blockers",
        agent_count=4,
        avg_turns_per_session=25,
        alignment_level="rlhf",
    )
    result = compute_eci(config)
    assert 0.0 < result.score < 1.0
    assert result.risk_level in ("minimal", "low", "moderate", "high", "very_high")
