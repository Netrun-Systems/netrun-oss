"""Tests for embedding module — mocked, no real API/DB calls needed."""


def test_similarity_to_intensity_mapping():
    """Verify the calibrated similarity -> intensity mapping."""
    from netrun.dee.embedding import _similarity_to_intensity

    # High band: >= 0.80 -> 3.0
    assert _similarity_to_intensity(0.85) == 3.0
    assert _similarity_to_intensity(0.80) == 3.0
    assert _similarity_to_intensity(0.99) == 3.0

    # Upper-mid band: 0.65 to 0.80 -> 2.0 to 3.0
    val_070 = _similarity_to_intensity(0.70)
    assert 2.0 <= val_070 <= 3.0

    val_065 = _similarity_to_intensity(0.65)
    assert abs(val_065 - 2.0) < 0.01

    # Lower-mid band: 0.50 to 0.65 -> 1.0 to 2.0
    val_055 = _similarity_to_intensity(0.55)
    assert 1.0 <= val_055 <= 2.0

    val_050 = _similarity_to_intensity(0.50)
    assert abs(val_050 - 1.0) < 0.01

    # Low band: 0.35 to 0.50 -> 0.0 to 1.0
    val_040 = _similarity_to_intensity(0.40)
    assert 0.0 < val_040 < 1.0

    val_035 = _similarity_to_intensity(0.35)
    assert abs(val_035 - 0.0) < 0.01

    # No match: < 0.35 -> 0.0
    assert _similarity_to_intensity(0.20) == 0.0
    assert _similarity_to_intensity(0.0) == 0.0


def test_similarity_to_intensity_monotonic():
    """Verify mapping is monotonically non-decreasing."""
    from netrun.dee.embedding import _similarity_to_intensity

    prev = 0.0
    for i in range(0, 101):
        sim = i / 100.0
        val = _similarity_to_intensity(sim)
        assert val >= prev, f"Non-monotonic at sim={sim}: {val} < {prev}"
        prev = val


def test_text_hash_deterministic():
    """Verify deterministic text hashing."""
    from netrun.dee.embedding import _text_hash

    h1 = _text_hash("hello world")
    h2 = _text_hash("hello world")
    h3 = _text_hash("different text")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64  # SHA-256 hex length


def test_text_hash_from_memory():
    """Verify memory module uses same hash function."""
    from netrun.dee.memory import _text_hash

    h1 = _text_hash("hello world")
    h2 = _text_hash("hello world")
    h3 = _text_hash("different text")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64
