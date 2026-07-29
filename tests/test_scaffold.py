def test_placeholder():
    """Placeholder test — verifies pytest is wired into meson."""
    assert True


def test_import():
    """Verify the batteryguard package is importable."""
    from batteryguard.application import BatteryGuardApplication
    assert BatteryGuardApplication is not None
