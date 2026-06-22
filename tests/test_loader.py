"""Tests for user-space lifecycle event helpers."""

from __future__ import annotations

import os
import threading
import unittest
from collections import deque

from user.loader import EVENT_EXEC, EVENT_EXIT, ExecMonitor


class ExecMonitorHelperTests(unittest.TestCase):
    def test_decode_successful_exit(self) -> None:
        self.assertEqual(ExecMonitor._decode_exit_status(0), (0, None))

    def test_decode_nonzero_exit(self) -> None:
        self.assertEqual(ExecMonitor._decode_exit_status(7 << 8), (7, None))

    def test_decode_signal_exit(self) -> None:
        self.assertEqual(ExecMonitor._decode_exit_status(15), (None, 15))

    def test_read_current_process_details(self) -> None:
        executable, arguments = ExecMonitor._read_process_details(os.getpid())

        self.assertTrue(executable)
        self.assertTrue(arguments)

    def test_metrics_track_exec_exit_and_lost_events(self) -> None:
        monitor = ExecMonitor.__new__(ExecMonitor)
        monitor._metrics_lock = threading.Lock()
        monitor._recent_event_times = deque()
        monitor._exec_events = 0
        monitor._exit_events = 0
        monitor._lost_events = 0

        monitor._record_event(EVENT_EXEC)
        monitor._record_event(EVENT_EXIT)
        with self.assertLogs("user.loader", level="WARNING"):
            monitor._handle_lost_events(cpu=0, lost=3)

        self.assertEqual(
            monitor.metrics(),
            {
                "event_rate": 0.2,
                "kernel_events": 2,
                "exec_events": 1,
                "exit_events": 1,
                "lost_events": 3,
                "buffer_healthy": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
