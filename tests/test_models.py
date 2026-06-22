"""Tests for process lifecycle models."""

from __future__ import annotations

import unittest
from datetime import datetime

from user.models import EventStore, ExecEvent


class ExecEventTests(unittest.TestCase):
    def test_to_dict_includes_lifecycle_details(self) -> None:
        timestamp = datetime(2026, 6, 22, 12, 34, 56).timestamp()
        start_ns = int(timestamp * 1_000_000_000)
        event = ExecEvent(
            pid=42,
            ppid=7,
            uid=1000,
            username="hesam",
            command="python3",
            executable="/usr/bin/python3",
            arguments="python3 app.py",
            timestamp_ns=start_ns,
            status="exited",
            exit_timestamp_ns=start_ns + 2_500_000_000,
            exit_code=0,
        )

        self.assertEqual(
            event.to_dict(),
            {
                "pid": 42,
                "ppid": 7,
                "uid": 1000,
                "username": "hesam",
                "command": "python3",
                "executable": "/usr/bin/python3",
                "arguments": "python3 app.py",
                "status": "exited",
                "timestamp": "2026-06-22 12:34:56",
                "exit_timestamp": "2026-06-22 12:34:58",
                "duration": "2.5 s",
                "duration_seconds": 2.5,
                "exit_code": 0,
                "signal": None,
                "outcome": "exit:0",
            },
        )

    def test_signal_outcome(self) -> None:
        event = ExecEvent(
            pid=42,
            command="sleep",
            timestamp_ns=0,
            status="exited",
            exit_timestamp_ns=1_000_000,
            signal=15,
        )

        self.assertEqual(event.outcome, "signal:15")


class EventStoreTests(unittest.TestCase):
    def test_store_retains_newest_events_and_tracks_total(self) -> None:
        store = EventStore(max_events=2)

        store.add(ExecEvent(pid=1, command="first", timestamp_ns=1_000_000_000))
        store.add(ExecEvent(pid=2, command="second", timestamp_ns=2_000_000_000))
        store.add(ExecEvent(pid=3, command="third", timestamp_ns=3_000_000_000))

        self.assertEqual([event.pid for event in store.latest()], [3, 2])
        self.assertEqual(store.stats()["total_events"], 3)
        self.assertEqual(store.stats()["retained_events"], 2)
        self.assertEqual(store.stats()["max_events"], 2)
        self.assertEqual(store.stats()["unique_commands"], 2)
        self.assertEqual(store.stats()["running_processes"], 2)
        self.assertEqual(store.stats()["exited_processes"], 0)
        self.assertEqual(store.stats()["latest_command"], "third")

    def test_store_correlates_exit_with_exec(self) -> None:
        store = EventStore()
        store.add(ExecEvent(pid=10, command="false", timestamp_ns=1_000_000_000))

        found = store.mark_exited(
            pid=10,
            timestamp_ns=2_000_000_000,
            exit_code=1,
            signal=None,
        )

        event = store.latest()[0]
        self.assertTrue(found)
        self.assertEqual(event.status, "exited")
        self.assertEqual(event.exit_code, 1)
        self.assertEqual(event.duration, "1.0 s")
        self.assertEqual(store.stats()["running_processes"], 0)
        self.assertEqual(store.stats()["exited_processes"], 1)

    def test_unknown_exit_is_ignored(self) -> None:
        self.assertFalse(EventStore().mark_exited(999, 1, 0, None))

    def test_store_rejects_non_positive_capacity(self) -> None:
        with self.assertRaises(ValueError):
            EventStore(max_events=0)

    def test_stats_reports_latest_event_timestamp(self) -> None:
        store = EventStore()
        event = ExecEvent(pid=1, command="sh", timestamp_ns=0)
        store.add(event)

        self.assertEqual(store.stats()["last_update"], event.timestamp)

    def test_empty_store_reports_waiting(self) -> None:
        self.assertEqual(
            EventStore().stats(),
            {
                "total_events": 0,
                "retained_events": 0,
                "max_events": 100,
                "unique_commands": 0,
                "running_processes": 0,
                "exited_processes": 0,
                "last_update": "در انتظار رویداد",
                "latest_command": "—",
            },
        )


if __name__ == "__main__":
    unittest.main()
