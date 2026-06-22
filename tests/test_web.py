"""Tests for the Flask dashboard."""

from __future__ import annotations

import unittest

import web.app as dashboard
from user.models import EventStore, ExecEvent


class DashboardTests(unittest.TestCase):
    def setUp(self) -> None:
        dashboard.event_store = EventStore()
        dashboard.monitor_error = None
        dashboard.monitor_status = "active"
        self.client = dashboard.app.test_client()

    def test_index_renders_current_events(self) -> None:
        dashboard.event_store.add(ExecEvent(pid=42, command="pytest", timestamp_ns=0))

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"pytest", response.data)
        self.assertIn(b"42", response.data)
        self.assertIn('lang="fa" dir="rtl"'.encode(), response.data)
        self.assertIn("پایشگر اجرای پردازش‌ها".encode(), response.data)
        self.assertIn(b"Vazirmatn", response.data)
        self.assertIn("مشاهدهٔ خروجی JSON".encode(), response.data)
        self.assertIn("پایشگر فعال است".encode(), response.data)

    def test_api_returns_current_events_and_stats(self) -> None:
        event = ExecEvent(pid=7, command="bash", timestamp_ns=0)
        dashboard.event_store.add(event)

        response = self.client.get("/api/events")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {
                "events": [
                    {
                        "command": "bash",
                        "pid": 7,
                        "timestamp": event.timestamp,
                    }
                ],
                "monitor_error": None,
                "monitor_status": "active",
                "stats": {
                    "last_update": event.timestamp,
                    "latest_command": "bash",
                    "max_events": 100,
                    "retained_events": 1,
                    "total_events": 1,
                    "unique_commands": 1,
                },
            },
        )


if __name__ == "__main__":
    unittest.main()
