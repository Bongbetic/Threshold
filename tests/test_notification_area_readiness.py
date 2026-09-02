"""Notification-area readiness state machine tests (fake clock)."""

import pytest

from threshold.notification_area_readiness import (
    NotificationAreaReadiness,
    ReadinessState,
    REGISTRATION_TIMEOUT_MS,
)


def test_initial_state_unavailable():
    assert NotificationAreaReadiness().state is ReadinessState.UNAVAILABLE


def test_watcher_appeared_starts_registration():
    r = NotificationAreaReadiness()
    assert r.watcher_appeared() is True
    assert r.state is ReadinessState.REGISTERING


def test_confirmation_within_timeout_becomes_ready():
    r = NotificationAreaReadiness()
    r.watcher_appeared()
    r.advance_clock(2000)
    assert r.registration_confirmed() is True
    assert r.state is ReadinessState.READY


def test_registration_timeout_reverts_to_unavailable():
    r = NotificationAreaReadiness()
    r.watcher_appeared()
    r.advance_clock(REGISTRATION_TIMEOUT_MS)
    assert r.state is ReadinessState.UNAVAILABLE


def test_timeout_exactly_at_boundary_expires():
    r = NotificationAreaReadiness()
    r.watcher_appeared()
    r.advance_clock(REGISTRATION_TIMEOUT_MS - 1)
    assert r.state is ReadinessState.REGISTERING


def test_duplicate_watcher_appearance_does_not_stack_attempts():
    r = NotificationAreaReadiness()
    r.watcher_appeared()
    gen = r.generation
    assert r.watcher_appeared() is False
    assert r.generation == gen
    assert r.state is ReadinessState.REGISTERING


def test_stale_confirmation_callback_ignored():
    r = NotificationAreaReadiness()
    r.watcher_appeared()          # gen 1
    r.advance_clock(REGISTRATION_TIMEOUT_MS)  # expires, gen 2
    # Late confirmation from the dead attempt
    assert r.registration_confirmed(generation=1) is False
    assert r.state is ReadinessState.UNAVAILABLE


def test_current_confirmation_accepted():
    r = NotificationAreaReadiness()
    r.watcher_appeared()
    assert r.registration_confirmed(generation=r.generation) is True
    assert r.state is ReadinessState.READY


def test_watcher_loss_revokes_readiness_immediately():
    r = NotificationAreaReadiness()
    r.watcher_appeared()
    r.registration_confirmed()
    assert r.watcher_lost() is True
    assert r.state is ReadinessState.LOST
    assert r.can_close_to_notification_area() is False


def test_watcher_return_after_loss_is_event_driven():
    r = NotificationAreaReadiness()
    r.watcher_appeared()
    r.registration_confirmed()
    r.watcher_lost()
    # Watcher comes back: one new attempt, no polling loop needed
    assert r.watcher_appeared() is True
    assert r.state is ReadinessState.REGISTERING


def test_duplicate_watcher_lost_is_idempotent():
    r = NotificationAreaReadiness()
    r.watcher_appeared()
    r.registration_confirmed()
    assert r.watcher_lost() is True
    assert r.watcher_lost() is False


def test_registration_failure_returns_to_unavailable():
    r = NotificationAreaReadiness()
    r.watcher_appeared()
    assert r.registration_failed() is True
    assert r.state is ReadinessState.UNAVAILABLE


def test_clock_must_not_go_backwards():
    r = NotificationAreaReadiness()
    r.advance_clock(100)
    with pytest.raises(ValueError):
        r.advance_clock(50)


def test_close_to_tray_only_when_ready():
    r = NotificationAreaReadiness()
    assert r.can_close_to_notification_area() is False
    r.watcher_appeared()
    assert r.can_close_to_notification_area() is False
    r.registration_confirmed()
    assert r.can_close_to_notification_area() is True
    r.watcher_lost()
    assert r.can_close_to_notification_area() is False
