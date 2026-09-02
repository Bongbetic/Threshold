"""Notification-area readiness state machine (deterministic, no GI imports).

States: unavailable -> registering -> ready | lost, per issue #86:
- Registration must be confirmed within five seconds (injectable clock).
- Watcher loss revokes readiness immediately.
- Watcher return starts an event-driven registration attempt (no polling).
- Duplicate events and stale callbacks are idempotent.
"""

import enum


class ReadinessState(enum.Enum):
    UNAVAILABLE = "unavailable"
    REGISTERING = "registering"
    READY = "ready"
    LOST = "lost"


REGISTRATION_TIMEOUT_MS = 5000


class NotificationAreaReadiness:
    """Pure readiness state machine; transport drives it with evidence."""

    def __init__(self, now_ms: int = 0, timeout_ms: int = REGISTRATION_TIMEOUT_MS):
        self._state = ReadinessState.UNAVAILABLE
        self._now = now_ms
        self._timeout_ms = timeout_ms
        self._attempt_started_at = None
        self._generation = 0  # increments per registration attempt

    @property
    def state(self) -> ReadinessState:
        return self._state

    def advance_clock(self, now_ms: int) -> None:
        """Advance time; expire a stale registration attempt if elapsed."""
        if now_ms < self._now:
            raise ValueError("clock must not go backwards")
        self._now = now_ms
        self._check_timeout()

    def _check_timeout(self) -> None:
        if (
            self._state is ReadinessState.REGISTERING
            and self._attempt_started_at is not None
            and self._now - self._attempt_started_at >= self._timeout_ms
        ):
            self._state = ReadinessState.UNAVAILABLE
            self._attempt_started_at = None
            self._generation += 1

    def watcher_appeared(self) -> bool:
        """Watcher present: start an event-driven registration attempt.

        Returns True when a registration call should be issued.
        No-op (False) while already registering — duplicate watcher
        events must not stack attempts.
        """
        if self._state is ReadinessState.REGISTERING:
            return False
        if self._state is ReadinessState.READY:
            return False
        self._state = ReadinessState.REGISTERING
        self._attempt_started_at = self._now
        self._generation += 1
        return True

    def registration_confirmed(self, generation: int | None = None) -> bool:
        """Watcher accepted registration -> ready. Stale callbacks ignored."""
        if generation is not None and generation != self._generation:
            return False
        if self._state not in (ReadinessState.REGISTERING, ReadinessState.READY):
            return False
        self._state = ReadinessState.READY
        self._attempt_started_at = None
        return True

    def registration_failed(self, generation: int | None = None) -> bool:
        """Registration call errored -> unavailable; caller may retry on
        the next watcher event."""
        if generation is not None and generation != self._generation:
            return False
        if self._state is not ReadinessState.REGISTERING:
            return False
        self._state = ReadinessState.UNAVAILABLE
        self._attempt_started_at = None
        self._generation += 1
        return True

    def watcher_lost(self) -> bool:
        """Watcher vanished: revoke readiness immediately."""
        if self._state is ReadinessState.LOST:
            return False
        self._state = ReadinessState.LOST
        self._attempt_started_at = None
        return True

    @property
    def generation(self) -> int:
        return self._generation

    def can_close_to_notification_area(self) -> bool:
        """Close-to-notification-area is allowed only in `ready`."""
        return self._state is ReadinessState.READY
