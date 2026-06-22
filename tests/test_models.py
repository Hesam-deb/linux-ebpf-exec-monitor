"""Tests for the execution event models."""

from __future__ import annotations

import unittest
from datetime import datetime

from user.models import EventStore, ExecEvent


class ExecEventTests(unittest.TestCase):
    def test_to_dict_formats_timestamp(self) -> None:
        timestamp = datetime(2026, 6, 22, 12, 34, 56).timestamp()
        event = ExecEvent(
            pid=42,
            command="python3",
            timestamp_ns=int(timestamp * 1_000_000_000),
        )

        self.assertEqual(
            event.to_dict(),
            {
                "pid": 42,
                "command": "python3",
                "timestamp": "2026-06-22 12:34:56",
            },
        )


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
        self.assertEqual(store.stats()["latest_command"], "third")

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
                "last_update": "در انتظار رویداد",
                "latest_command": "—",
            },
        )


if __name__ == "__main__":
    unittest.main()
