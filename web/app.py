"""Flask dashboard for Linux eBPF Process Execution Monitor."""

from __future__ import annotations

import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request

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

TRANSLATIONS = {
    "fa": {
        "direction": "rtl",
        "language_name": "فارسی",
        "other_language": "English",
        "page_title": "پایشگر پردازش‌های لینوکس با eBPF",
        "description": "داشبورد آموزشی پایش اجرای پردازش‌های لینوکس با eBPF",
        "eyebrow": "مشاهده‌پذیری هستهٔ لینوکس",
        "heading": "پایشگر اجرای پردازش‌ها",
        "hero_description": "مشاهدهٔ اجرای دستورها در هستهٔ لینوکس با eBPF؛ سبک، زنده و مناسب یادگیری.",
        "status_active": "پایشگر فعال است",
        "status_starting": "در حال راه‌اندازی پایشگر",
        "status_error": "پایشگر با خطا متوقف شده",
        "load_error": "بارگذاری eBPF ناموفق بود",
        "stats_label": "آمار پایشگر",
        "total_events": "مجموع رویدادها",
        "since_start": "از زمان اجرای برنامه",
        "retained_events": "رویدادهای موجود",
        "of": "از",
        "retained_help": "جدیدترین رویدادهای داخل حافظه",
        "unique_commands": "دستورهای یکتا",
        "window_help": "در بازهٔ فعلی رویدادها",
        "last_update": "آخرین به‌روزرسانی",
        "local_time": "زمان محلی سیستم",
        "waiting": "در انتظار رویداد",
        "latest_command": "آخرین دستور",
        "event_source": "منبع رویداد",
        "refresh_rate": "نرخ به‌روزرسانی",
        "every_two_seconds": "هر ۲ ثانیه",
        "transport": "روش انتقال",
        "event_stream": "جریان رویدادها",
        "latest_processes": "آخرین پردازش‌های اجراشده",
        "view_json": "مشاهدهٔ خروجی JSON",
        "command": "دستور",
        "pid": "شناسهٔ پردازش (PID)",
        "timestamp": "زمان ثبت",
        "empty_title": "هنوز رویدادی دریافت نشده است",
        "empty_help": "در یک ترمینال دیگر دستوری مثل",
        "or": "یا",
        "empty_suffix": "اجرا کنید.",
        "footer": "این داشبورد یک نمونهٔ آموزشی است و جایگزین ابزارهای امنیتی عملیاتی نیست.",
    },
    "en": {
        "direction": "ltr",
        "language_name": "English",
        "other_language": "فارسی",
        "page_title": "Linux eBPF Process Monitor",
        "description": "Educational dashboard for monitoring Linux process execution with eBPF",
        "eyebrow": "Linux Kernel Observability",
        "heading": "Process Execution Monitor",
        "hero_description": "Watch commands execute in the Linux kernel with eBPF—a lightweight, live learning project.",
        "status_active": "Monitor is active",
        "status_starting": "Monitor is starting",
        "status_error": "Monitor stopped with an error",
        "load_error": "Failed to load eBPF",
        "stats_label": "Monitor statistics",
        "total_events": "Total events",
        "since_start": "Since the application started",
        "retained_events": "Retained events",
        "of": "of",
        "retained_help": "Newest events kept in memory",
        "unique_commands": "Unique commands",
        "window_help": "Within the current event window",
        "last_update": "Last update",
        "local_time": "System local time",
        "waiting": "Waiting for an event",
        "latest_command": "Latest command",
        "event_source": "Event source",
        "refresh_rate": "Refresh rate",
        "every_two_seconds": "Every 2 seconds",
        "transport": "Transport",
        "event_stream": "Event stream",
        "latest_processes": "Latest executed processes",
        "view_json": "View JSON output",
        "command": "Command",
        "pid": "Process ID (PID)",
        "timestamp": "Timestamp",
        "empty_title": "No events received yet",
        "empty_help": "Run a command such as",
        "or": "or",
        "empty_suffix": "in another terminal.",
        "footer": "This dashboard is an educational demo, not a replacement for production security tooling.",
    },
}


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
    language = request.args.get("lang", "fa")
    if language not in TRANSLATIONS:
        language = "fa"

    translations = TRANSLATIONS[language]
    stats = event_store.stats()
    if stats["retained_events"] == 0:
        stats["last_update"] = translations["waiting"]

    return render_template(
        "index.html",
        events=[event.to_dict() for event in event_store.latest()],
        stats=stats,
        monitor_error=monitor_error,
        monitor_status=monitor_status,
        language=language,
        alternate_language="en" if language == "fa" else "fa",
        t=translations,
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
