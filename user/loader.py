"""BCC loader for the eBPF process execution monitor."""

from __future__ import annotations

import logging
import signal
import threading
import time
from pathlib import Path
from types import FrameType
from typing import Any

from user.models import EventStore, ExecEvent

LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EBPF_SOURCE = PROJECT_ROOT / "ebpf" / "exec_monitor.c"


class ExecMonitor:
    """Load the eBPF program and stream execution events into EventStore."""

    def __init__(self, store: EventStore, source_path: Path = DEFAULT_EBPF_SOURCE) -> None:
        self.store = store
        self.source_path = source_path
        self._bpf: Any | None = None
        self._running = threading.Event()
        self._wall_time_offset_ns = time.time_ns() - time.monotonic_ns()

    def start(self) -> None:
        """Load the BPF program and begin polling events."""
        if self._running.is_set():
            return

        try:
            from bcc import BPF  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise RuntimeError(
                "BCC Python bindings are not installed. Run scripts/install.sh first."
            ) from exc

        if not self.source_path.exists():
            raise FileNotFoundError(f"eBPF source not found: {self.source_path}")

        LOGGER.info("Loading eBPF program from %s", self.source_path)
        self._bpf = BPF(src_file=str(self.source_path))
        self._bpf["events"].open_perf_buffer(self._handle_event)
        self._running.set()

    def stop(self) -> None:
        """Stop polling for events."""
        self._running.clear()

    def poll_forever(self) -> None:
        """Poll the perf buffer until stopped."""
        self.start()
        assert self._bpf is not None

        LOGGER.info("eBPF process execution monitor started")
        while self._running.is_set():
            try:
                self._bpf.perf_buffer_poll(timeout=1000)
            except KeyboardInterrupt:
                self.stop()
            except Exception:
                LOGGER.exception("Error while polling eBPF events")

        LOGGER.info("eBPF process execution monitor stopped")

    def _handle_event(self, cpu: int, data: Any, size: int) -> None:
        """Convert a raw perf event into an ExecEvent."""
        if self._bpf is None:
            return

        try:
            raw_event = self._bpf["events"].event(data)
            command = raw_event.comm.decode("utf-8", errors="replace").rstrip("\x00")
            self.store.add(
                ExecEvent(
                    pid=int(raw_event.pid),
                    command=command,
                    timestamp_ns=int(raw_event.timestamp_ns) + self._wall_time_offset_ns,
                )
            )
        except Exception:
            LOGGER.exception("Failed to decode eBPF event")


def run_cli() -> None:
    """Run the monitor without the web dashboard for quick terminal testing."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    store = EventStore()
    monitor = ExecMonitor(store)

    def handle_signal(signum: int, frame: FrameType | None) -> None:
        LOGGER.info("Received signal %s, stopping", signum)
        monitor.stop()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    monitor.poll_forever()


if __name__ == "__main__":
    run_cli()
