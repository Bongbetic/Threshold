def test_placeholder():
    """Placeholder test — verifies pytest is wired into meson."""
    assert True


def test_import():
    """Verify the threshold package is importable."""
    from threshold.application import ThresholdApplication
    assert ThresholdApplication is not None
