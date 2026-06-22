#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KERNEL_MAJOR="$(uname -r | cut -d. -f1)"

if [[ "${KERNEL_MAJOR}" -lt 6 ]]; then
  echo "Linux kernel 6.x or newer is recommended. Current kernel: $(uname -r)"
  exit 1
fi

echo "Kernel version OK: $(uname -r)"

sudo apt update
sudo apt install -y \
  python3 \
  python3-pip \
  python3-venv \
  bpfcc-tools \
  libbpfcc-dev \
  python3-bpfcc \
  linux-headers-"$(uname -r)"

python3 -m venv --system-site-packages "${PROJECT_ROOT}/.venv"
"${PROJECT_ROOT}/.venv/bin/pip" install --upgrade pip
"${PROJECT_ROOT}/.venv/bin/pip" install -r "${PROJECT_ROOT}/requirements.txt"
"${PROJECT_ROOT}/.venv/bin/python" -c "from bcc import BPF"

echo "Installation complete."
echo "Run the monitor with: sudo ${PROJECT_ROOT}/scripts/run.sh"
