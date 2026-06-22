"""Data models and in-memory storage for execution events."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Any, Deque


@dataclass(frozen=True)
class ExecEvent:
    """A process execution event received from the eBPF program."""

    pid: int
    command: str
    timestamp_ns: int

    @property
    def timestamp(self) -> str:
        """Return a display-friendly local timestamp."""
        seconds = self.timestamp_ns / 1_000_000_000
        return datetime.fromtimestamp(seconds).strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict[str, Any]:
        """Serialize the event for templates or JSON output."""
        return {
            "pid": self.pid,
            "command": self.command,
            "timestamp": self.timestamp,
        }


class EventStore:
    """Thread-safe in-memory store that keeps only the latest events."""

    def __init__(self, max_events: int = 100) -> None:
        if max_events <= 0:
            raise ValueError("max_events must be greater than zero")

        self._max_events = max_events
        self._events: Deque[ExecEvent] = deque(maxlen=max_events)
        self._total_events = 0
        self._lock = Lock()

    def add(self, event: ExecEvent) -> None:
        """Add an event to the store."""
        with self._lock:
            self._events.appendleft(event)
            self._total_events += 1

    def latest(self) -> list[ExecEvent]:
        """Return the newest events first."""
        with self._lock:
            return list(self._events)

    def stats(self) -> dict[str, Any]:
        """Return dashboard statistics."""
        with self._lock:
            commands = {event.command for event in self._events}
            last_update = self._events[0].timestamp if self._events else "در انتظار رویداد"
            latest_command = self._events[0].command if self._events else "—"
            return {
                "total_events": self._total_events,
                "retained_events": len(self._events),
                "max_events": self._max_events,
                "unique_commands": len(commands),
                "last_update": last_update,
                "latest_command": latest_command,
            }
