#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${FLASK_HOST:-127.0.0.1}"
PORT="${FLASK_PORT:-5000}"
PYTHON_BIN="${PROJECT_ROOT}/.venv/bin/python"

if [[ "${EUID}" -ne 0 ]]; then
  echo "This program must run as root so BCC can load eBPF programs."
  echo "Try: sudo ${PROJECT_ROOT}/scripts/run.sh"
  exit 1
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="$(command -v python3)"
fi

echo "Starting Linux eBPF Process Execution Monitor"
echo "Dashboard URL: http://${HOST}:${PORT}"

export PYTHONPATH="${PROJECT_ROOT}"
export FLASK_HOST="${HOST}"
export FLASK_PORT="${PORT}"
exec "${PYTHON_BIN}" "${PROJECT_ROOT}/web/app.py"
