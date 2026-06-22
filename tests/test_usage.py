"""Tests for Linux process and host usage sampling."""

from __future__ import annotations

import unittest

from user.usage import UsageSampler


class UsageSamplerTests(unittest.TestCase):
    def test_snapshot_reports_monitor_system_and_history(self) -> None:
        sampler = UsageSampler(max_samples=3, minimum_interval=0)

        first = sampler.snapshot()
        second = sampler.snapshot()

        self.assertEqual(len(second["history"]), 2)
        self.assertIn("monitor_cpu", second["current"])
        self.assertGreater(second["current"]["monitor_memory_mb"], 0)
        self.assertGreaterEqual(second["current"]["system_cpu"], 0)
        self.assertLessEqual(second["current"]["system_cpu"], 100)
        self.assertGreater(second["current"]["system_memory"], 0)
        self.assertLessEqual(second["current"]["system_memory"], 100)
        self.assertGreater(first["current"]["system_memory_total_mb"], 0)

    def test_history_respects_capacity(self) -> None:
        sampler = UsageSampler(max_samples=2, minimum_interval=0)

        sampler.snapshot()
        sampler.snapshot()
        payload = sampler.snapshot()

        self.assertEqual(len(payload["history"]), 2)


if __name__ == "__main__":
    unittest.main()
