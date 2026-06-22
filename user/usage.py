"""Lightweight process and host usage sampling from Linux procfs."""

from __future__ import annotations

import os
import threading
import time
from collections import deque
from typing import Any


class UsageSampler:
    """Collect one-second CPU and memory samples with rolling history."""

    def __init__(self, max_samples: int = 60, minimum_interval: float = 0.8) -> None:
        self._history: deque[dict[str, float]] = deque(maxlen=max_samples)
        self._minimum_interval = minimum_interval
        self._lock = threading.Lock()
        self._last_wall_time: float | None = None
        self._last_process_cpu: float | None = None
        self._last_system_total: int | None = None
        self._last_system_idle: int | None = None

    @staticmethod
    def _read_system_cpu() -> tuple[int, int]:
        with open("/proc/stat", encoding="utf-8") as stat:
            values = [int(value) for value in stat.readline().split()[1:]]
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        return sum(values), idle

    @staticmethod
    def _read_memory() -> tuple[float, float]:
        memory: dict[str, int] = {}
        with open("/proc/meminfo", encoding="utf-8") as meminfo:
            for line in meminfo:
                key, value = line.split(":", 1)
                if key in {"MemTotal", "MemAvailable"}:
                    memory[key] = int(value.split()[0])

        total = memory["MemTotal"]
        used_percent = (1 - memory["MemAvailable"] / total) * 100
        return total / 1024, used_percent

    @staticmethod
    def _read_process_memory_mb() -> float:
        with open("/proc/self/statm", encoding="utf-8") as statm:
            resident_pages = int(statm.read().split()[1])
        return resident_pages * os.sysconf("SC_PAGE_SIZE") / (1024 * 1024)

    def snapshot(self) -> dict[str, Any]:
        """Return current usage plus up to 60 recent samples."""
        with self._lock:
            now = time.monotonic()
            if self._history and now - self._history[-1]["sample_time"] < self._minimum_interval:
                return self._payload()

            system_total, system_idle = self._read_system_cpu()
            process_cpu = time.process_time()
            process_memory_mb = self._read_process_memory_mb()
            total_memory_mb, system_memory_percent = self._read_memory()

            system_cpu_percent = 0.0
            process_cpu_percent = 0.0
            if self._last_system_total is not None and self._last_system_idle is not None:
                total_delta = system_total - self._last_system_total
                idle_delta = system_idle - self._last_system_idle
                if total_delta > 0:
                    system_cpu_percent = (1 - idle_delta / total_delta) * 100

            if self._last_wall_time is not None and self._last_process_cpu is not None:
                wall_delta = now - self._last_wall_time
                if wall_delta > 0:
                    process_cpu_percent = (process_cpu - self._last_process_cpu) / wall_delta * 100

            self._last_wall_time = now
            self._last_process_cpu = process_cpu
            self._last_system_total = system_total
            self._last_system_idle = system_idle

            self._history.append(
                {
                    "sample_time": now,
                    "monitor_cpu": round(max(0.0, process_cpu_percent), 1),
                    "monitor_memory_mb": round(process_memory_mb, 1),
                    "system_cpu": round(min(100.0, max(0.0, system_cpu_percent)), 1),
                    "system_memory": round(min(100.0, max(0.0, system_memory_percent)), 1),
                    "system_memory_total_mb": round(total_memory_mb, 1),
                    "load_average": round(os.getloadavg()[0], 2),
                }
            )
            return self._payload()

    def _payload(self) -> dict[str, Any]:
        history = list(self._history)
        current = history[-1] if history else {
            "monitor_cpu": 0.0,
            "monitor_memory_mb": 0.0,
            "system_cpu": 0.0,
            "system_memory": 0.0,
            "system_memory_total_mb": 0.0,
            "load_average": 0.0,
        }
        return {
            "current": {key: value for key, value in current.items() if key != "sample_time"},
            "history": [
                {key: value for key, value in sample.items() if key != "sample_time"}
                for sample in history
            ],
        }
