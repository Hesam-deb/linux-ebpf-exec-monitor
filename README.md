# Linux eBPF Process Execution Monitor

> See what your Linux machine executes, live from the kernel.

[راهنمای فارسی](README.fa.md)

This small educational project listens for successful process executions with eBPF and presents them in a clean Persian dashboard. It is a practical way to explore Linux tracepoints, BCC perf buffers, thread-safe event storage, and a Flask web interface without starting from a large observability stack.

## What you will see

Every time a program starts, the dashboard shows:

- its command name;
- its process ID (PID);
- the local time at which the event was received;
- total and unique command counts;
- monitor health and in-memory retention information.

The page refreshes every two seconds and keeps the newest 100 events in memory.

## How it works

```text
Linux tracepoint: sched:sched_process_exec
                   │
                   ▼
            BCC/eBPF program
                   │ perf buffer
                   ▼
           Python event loader
                   │
                   ▼
       Thread-safe in-memory store
                   │
                   ▼
          Persian Flask dashboard
```

## Requirements

### Supported environment

- Ubuntu 24.04 LTS or a recent Ubuntu/Debian-based distribution
- Linux kernel 6.x or newer
- An x86_64 or ARM64 machine supported by the installed BCC packages
- Internet access during installation
- `sudo` access

The installer uses `apt` and installs:

- `python3`, `python3-pip`, and `python3-venv`
- `bpfcc-tools`, `libbpfcc-dev`, and `python3-bpfcc`
- headers for the currently running kernel
- Flask 3.x inside a local `.venv`

BCC is intentionally installed through Ubuntu packages rather than PyPI because its native bindings must match the system libraries and kernel tooling.

> Windows and macOS cannot run this project directly because it loads a program into the Linux kernel. Use an Ubuntu virtual machine. WSL may work only when its kernel and BCC support are configured correctly, so a VM is the simpler option.

## Get the project

Choose either HTTPS:

```bash
git clone https://github.com/Hesam-deb/linux-ebpf-exec-monitor.git
cd linux-ebpf-exec-monitor
```

Or SSH, if your GitHub SSH key is configured:

```bash
git clone git@github.com:Hesam-deb/linux-ebpf-exec-monitor.git
cd linux-ebpf-exec-monitor
```

Repository addresses:

- HTTPS: `https://github.com/Hesam-deb/linux-ebpf-exec-monitor.git`
- SSH: `git@github.com:Hesam-deb/linux-ebpf-exec-monitor.git`

## Install

```bash
chmod +x scripts/install.sh scripts/run.sh
./scripts/install.sh
```

The installer checks the operating system and kernel, installs the required system packages, creates `.venv`, installs the Python dependencies, and verifies that both BCC and Flask can be imported.

## Run

Start the monitor:

```bash
sudo ./scripts/run.sh
```

Then open:

```text
http://127.0.0.1:5000
```

Keep the first terminal running. In a second terminal, generate a few events:

```bash
ls
whoami
ip a
ping -c 2 8.8.8.8
```

The dashboard should show the new commands within two seconds. Press `Ctrl+C` in the first terminal to stop the monitor.

## Useful configuration

The dashboard binds to localhost on port 5000 by default. To use another address or port:

```bash
sudo FLASK_HOST=0.0.0.0 FLASK_PORT=8080 ./scripts/run.sh
```

Binding to `0.0.0.0` exposes the dashboard to your local network. This demo has no authentication, so only do that on a trusted network.

The current data is also available as JSON:

```text
http://127.0.0.1:5000/api/events
```

## Run the tests

Tests do not load eBPF and do not require root:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

## Troubleshooting

### `BCC Python bindings are not installed`

Run the installer again and use the generated virtual environment:

```bash
./scripts/install.sh
```

### Missing kernel headers

Update the package index and install headers matching the running kernel:

```bash
sudo apt update
sudo apt install "linux-headers-$(uname -r)"
```

### Permission denied while loading eBPF

Start the application through the provided script with `sudo`:

```bash
sudo ./scripts/run.sh
```

### The dashboard is empty

Make sure the monitor status is active, then execute a command in another terminal. The page updates every two seconds.

## Project layout

```text
linux-ebpf-exec-monitor/
├── ebpf/                  # Kernel-side eBPF program
├── user/                  # BCC loader and event store
├── web/                   # Flask app, template, and styles
├── scripts/               # Installation and run helpers
├── tests/                 # Model and dashboard tests
├── requirements.txt       # Python dashboard dependency
├── README.md
├── README.fa.md
└── LICENSE
```

## Scope and limitations

This is a learning project, not a production security agent:

- it records process execution only, not file, network, or login activity;
- events are lost when the application stops;
- only the newest 100 events are retained;
- the dashboard has no authentication or TLS;
- the command field is limited to Linux's task command length;
- no persistence, enrichment, alerting, or tamper protection is provided.

## Ideas for extending it

- capture the executable path and parent PID;
- add filters and search;
- export events as CSV or JSON Lines;
- stream updates with Server-Sent Events;
- add optional persistent storage;
- package the monitor as a systemd service.
