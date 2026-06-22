"""Tests for user-space lifecycle event helpers."""

from __future__ import annotations

import os
import unittest

from user.loader import ExecMonitor


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


if __name__ == "__main__":
    unittest.main()
