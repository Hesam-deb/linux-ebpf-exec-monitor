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

    def add_exited_event(self) -> ExecEvent:
        event = ExecEvent(
            pid=42,
            ppid=7,
            uid=1000,
            username="hesam",
            command="pytest",
            executable="/usr/bin/pytest",
            arguments="pytest -q",
            timestamp_ns=1_000_000_000,
        )
        dashboard.event_store.add(event)
        dashboard.event_store.mark_exited(42, 2_000_000_000, 0, None)
        return event

    def test_index_renders_process_details(self) -> None:
        self.add_exited_event()

        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"pytest", response.data)
        self.assertIn(b"/usr/bin/pytest", response.data)
        self.assertIn(b"pytest -q", response.data)
        self.assertIn(b"42", response.data)
        self.assertIn('lang="fa" dir="rtl"'.encode(), response.data)
        self.assertIn("جزئیات پردازش".encode(), response.data)
        self.assertIn("پایان‌یافته".encode(), response.data)
        self.assertIn(b'href="/?lang=en"', response.data)

    def test_english_dashboard_uses_ltr_translations(self) -> None:
        response = self.client.get("/?lang=en")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'lang="en" dir="ltr"', response.data)
        self.assertIn(b"Process Lifecycle Monitor", response.data)
        self.assertIn(b"Running now", response.data)
        self.assertIn(b"Waiting for an event", response.data)
        self.assertIn("فارسی".encode(), response.data)

    def test_unknown_language_falls_back_to_persian(self) -> None:
        response = self.client.get("/?lang=unknown")

        self.assertEqual(response.status_code, 200)
        self.assertIn('lang="fa" dir="rtl"'.encode(), response.data)

    def test_api_returns_lifecycle_details_and_stats(self) -> None:
        event = self.add_exited_event()

        response = self.client.get("/api/events")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["monitor_status"], "active")
        self.assertEqual(payload["monitor_error"], None)
        self.assertEqual(payload["stats"]["running_processes"], 0)
        self.assertEqual(payload["stats"]["exited_processes"], 1)
        self.assertEqual(payload["events"][0]["pid"], event.pid)
        self.assertEqual(payload["events"][0]["ppid"], 7)
        self.assertEqual(payload["events"][0]["username"], "hesam")
        self.assertEqual(payload["events"][0]["executable"], "/usr/bin/pytest")
        self.assertEqual(payload["events"][0]["arguments"], "pytest -q")
        self.assertEqual(payload["events"][0]["status"], "exited")
        self.assertEqual(payload["events"][0]["exit_code"], 0)
        self.assertEqual(payload["events"][0]["duration_seconds"], 1.0)


if __name__ == "__main__":
    unittest.main()
