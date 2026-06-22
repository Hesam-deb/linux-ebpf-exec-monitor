"""Tests for the Flask dashboard."""

from __future__ import annotations

import unittest

import web.app as dashboard
from user.models import EventStore, ExecEvent
from user.usage import UsageSampler


class DashboardTests(unittest.TestCase):
    def setUp(self) -> None:
        dashboard.event_store = EventStore()
        dashboard.monitor_error = None
        dashboard.monitor_status = "active"
        dashboard.usage_sampler = UsageSampler(minimum_interval=0)
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
        self.assertNotIn(b'http-equiv="refresh"', response.data)
        self.assertIn(b"dashboard.js", response.data)
        self.assertIn("بار خط لولهٔ eBPF".encode(), response.data)
        self.assertIn(b"fonts.googleapis.com", response.data)
        self.assertIn(b"family=Vazirmatn", response.data)
        self.assertIn(b"background-aurora", response.data)
        self.assertIn(b"background-grid", response.data)
        self.assertIn(b"background-particles", response.data)
        self.assertIn("مصرف پایشگر".encode(), response.data)
        self.assertIn(b"monitor-cpu-line", response.data)
        self.assertIn(b"system-cpu-line", response.data)

    def test_english_dashboard_uses_ltr_translations(self) -> None:
        response = self.client.get("/?lang=en")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'lang="en" dir="ltr"', response.data)
        self.assertIn(b"Process Lifecycle Monitor", response.data)
        self.assertIn(b"Running now", response.data)
        self.assertIn(b"Waiting for an event", response.data)
        self.assertIn(b"eBPF pipeline load", response.data)
        self.assertIn("فارسی".encode(), response.data)

    def test_unknown_language_falls_back_to_persian(self) -> None:
        response = self.client.get("/?lang=unknown")

        self.assertEqual(response.status_code, 200)
        self.assertIn('lang="fa" dir="rtl"'.encode(), response.data)

    def test_live_dashboard_script_polls_and_preserves_open_details(self) -> None:
        response = self.client.get("/static/dashboard.js")

        try:
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"window.setInterval(poll", response.data)
            self.assertIn(b"sessionStorage.setItem", response.data)
            self.assertIn(b"details.dataset.eventId === selectedEventId", response.data)
            self.assertIn(b'event.key === "Escape"', response.data)
            self.assertIn(b"detail-overlay-open", response.data)
            self.assertIn(b"knownEventIds", response.data)
            self.assertIn(b"is-new-event", response.data)
            self.assertIn(b"value-pop", response.data)
            self.assertIn(b"updateLiveDurations", response.data)
            self.assertIn(b"is-status-change", response.data)
            self.assertIn(b"language-leaving", response.data)
            self.assertIn(b"window.location.assign", response.data)
            self.assertIn(b"updateUsage", response.data)
            self.assertIn(b"chartPoints", response.data)
        finally:
            response.close()

    def test_css_keeps_modal_viewport_fixed_and_updates_layout_stable(self) -> None:
        response = self.client.get("/static/style.css")

        try:
            css = response.get_data(as_text=True)
            self.assertIn("animation: section-enter 380ms ease-in-out backwards", css)
            self.assertIn(".process-details[open]", css)
            self.assertIn("position: fixed", css)
            self.assertIn("will-change: color, filter, text-shadow", css)
            value_animation = css.split("@keyframes value-pop", 1)[1].split(
                "@keyframes section-enter",
                1,
            )[0]
            self.assertNotIn("scale(", value_animation)
            self.assertIn("width: min(96vw, 1580px)", css)
        finally:
            response.close()

    def test_api_returns_lifecycle_details_and_stats(self) -> None:
        event = self.add_exited_event()

        response = self.client.get("/api/events")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["monitor_status"], "active")
        self.assertEqual(payload["monitor_error"], None)
        self.assertIn("event_rate", payload["monitor_metrics"])
        self.assertIn("lost_events", payload["monitor_metrics"])
        self.assertIn("monitor_cpu", payload["usage"]["current"])
        self.assertIn("system_cpu", payload["usage"]["current"])
        self.assertGreaterEqual(len(payload["usage"]["history"]), 1)
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
