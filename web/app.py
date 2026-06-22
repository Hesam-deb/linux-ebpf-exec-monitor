"""Flask dashboard for Linux eBPF Process Execution Monitor."""

from __future__ import annotations

import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from user.loader import ExecMonitor  # noqa: E402
from user.models import EventStore  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
LOGGER = logging.getLogger(__name__)

app = Flask(__name__)
event_store = EventStore(max_events=100)
monitor = ExecMonitor(event_store)
monitor_error: str | None = None
monitor_status = "starting"


def start_monitor_thread() -> None:
    """Start the eBPF monitor in a daemon thread."""
    global monitor_error, monitor_status

    def target() -> None:
        global monitor_error, monitor_status
        try:
            monitor.start()
            monitor_status = "active"
            monitor.poll_forever()
        except Exception as exc:
            monitor_error = str(exc)
            monitor_status = "error"
            LOGGER.exception("Monitor failed to start")

    thread = threading.Thread(target=target, name="ebpf-monitor", daemon=True)
    thread.start()


@app.route("/")
def index() -> str:
    """Render the dashboard page."""
    return render_template(
        "index.html",
        events=[event.to_dict() for event in event_store.latest()],
        stats=event_store.stats(),
        monitor_error=monitor_error,
        monitor_status=monitor_status,
    )


@app.route("/api/events")
def api_events() -> Any:
    """Return current dashboard data as JSON."""
    return jsonify(
        {
            "events": [event.to_dict() for event in event_store.latest()],
            "stats": event_store.stats(),
            "monitor_error": monitor_error,
            "monitor_status": monitor_status,
        }
    )


if __name__ == "__main__":
    start_monitor_thread()
    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_PORT", "5000"))
    app.run(host=host, port=port)
