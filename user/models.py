"""Data models and thread-safe lifecycle storage for monitored processes."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, replace
from datetime import datetime
from threading import Lock
from typing import Any, Deque


def format_timestamp(timestamp_ns: int | None) -> str | None:
    """Convert a wall-clock nanosecond timestamp into local display time."""
    if timestamp_ns is None:
        return None

    seconds = timestamp_ns / 1_000_000_000
    return datetime.fromtimestamp(seconds).strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class ExecEvent:
    """A process lifecycle record built from exec and exit events."""

    pid: int
    command: str
    timestamp_ns: int
    ppid: int = 0
    uid: int = 0
    username: str = "unknown"
    executable: str = ""
    arguments: str = ""
    status: str = "running"
    exit_timestamp_ns: int | None = None
    exit_code: int | None = None
    signal: int | None = None

    @property
    def timestamp(self) -> str:
        """Return the process start time for display."""
        return format_timestamp(self.timestamp_ns) or ""

    @property
    def exit_timestamp(self) -> str | None:
        """Return the process exit time for display."""
        return format_timestamp(self.exit_timestamp_ns)

    @property
    def duration_seconds(self) -> float:
        """Return elapsed runtime, including live time for running processes."""
        end_ns = self.exit_timestamp_ns or time.time_ns()
        return max(0.0, (end_ns - self.timestamp_ns) / 1_000_000_000)

    @property
    def duration(self) -> str:
        """Return a compact human-readable runtime."""
        seconds = self.duration_seconds
        if seconds < 1:
            return f"{seconds * 1000:.0f} ms"
        if seconds < 60:
            return f"{seconds:.1f} s"

        minutes, remaining_seconds = divmod(int(seconds), 60)
        if minutes < 60:
            return f"{minutes}m {remaining_seconds}s"

        hours, remaining_minutes = divmod(minutes, 60)
        return f"{hours}h {remaining_minutes}m"

    @property
    def outcome(self) -> str:
        """Return a machine-friendly exit outcome."""
        if self.status == "running":
            return "running"
        if self.signal is not None:
            return f"signal:{self.signal}"
        if self.exit_code is not None:
            return f"exit:{self.exit_code}"
        return "exited"

    def to_dict(self) -> dict[str, Any]:
        """Serialize the lifecycle record for templates and JSON."""
        return {
            "event_id": f"{self.pid}:{self.timestamp_ns}",
            "pid": self.pid,
            "ppid": self.ppid,
            "uid": self.uid,
            "username": self.username,
            "command": self.command,
            "executable": self.executable,
            "arguments": self.arguments,
            "status": self.status,
            "timestamp": self.timestamp,
            "exit_timestamp": self.exit_timestamp,
            "duration": self.duration,
            "duration_seconds": round(self.duration_seconds, 3),
            "exit_code": self.exit_code,
            "signal": self.signal,
            "outcome": self.outcome,
        }


class EventStore:
    """Keep and correlate the newest process lifecycle records."""

    def __init__(self, max_events: int = 100) -> None:
        if max_events <= 0:
            raise ValueError("max_events must be greater than zero")

        self._max_events = max_events
        self._events: Deque[ExecEvent] = deque()
        self._active_by_pid: dict[int, ExecEvent] = {}
        self._total_events = 0
        self._lock = Lock()

    def add(self, event: ExecEvent) -> None:
        """Add a newly executed process."""
        with self._lock:
            if len(self._events) >= self._max_events:
                removed = self._events.pop()
                if self._active_by_pid.get(removed.pid) is removed:
                    self._active_by_pid.pop(removed.pid, None)

            previous = self._active_by_pid.get(event.pid)
            if previous is not None:
                previous.status = "exited"
                previous.exit_timestamp_ns = event.timestamp_ns

            self._events.appendleft(event)
            self._active_by_pid[event.pid] = event
            self._total_events += 1

    def mark_exited(
        self,
        pid: int,
        timestamp_ns: int,
        exit_code: int | None,
        signal: int | None,
    ) -> bool:
        """Complete a running process record. Return whether it was found."""
        with self._lock:
            event = self._active_by_pid.pop(pid, None)
            if event is None:
                return False

            event.status = "exited"
            event.exit_timestamp_ns = timestamp_ns
            event.exit_code = exit_code
            event.signal = signal
            return True

    def latest(self) -> list[ExecEvent]:
        """Return snapshots of the newest process records first."""
        with self._lock:
            return [replace(event) for event in self._events]

    def stats(self) -> dict[str, Any]:
        """Return dashboard statistics."""
        with self._lock:
            commands = {event.command for event in self._events}
            running_processes = sum(event.status == "running" for event in self._events)
            last_update = self._events[0].timestamp if self._events else "در انتظار رویداد"
            latest_command = self._events[0].command if self._events else "—"
            return {
                "total_events": self._total_events,
                "retained_events": len(self._events),
                "max_events": self._max_events,
                "unique_commands": len(commands),
                "running_processes": running_processes,
                "exited_processes": len(self._events) - running_processes,
                "last_update": last_update,
                "latest_command": latest_command,
            }
