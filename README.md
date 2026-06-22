# Linux eBPF Process Execution Monitor

[مطالعهٔ راهنما به فارسی](README.fa.md)

A lightweight university proof-of-concept that captures Linux process execution events with eBPF and shows them in a small Flask dashboard.

The goal is to demonstrate Linux kernel observability, eBPF event delivery, and a simple user-space presentation layer. It is intentionally small and not designed as a production security monitoring system.

## Architecture

```text
Kernel Space
  eBPF program attached to sched:sched_process_exec
        |
        v
User Space
  Python BCC loader receives perf events
        |
        v
In-memory Event Store
  Keeps the latest 100 events
        |
        v
Flask Dashboard
  Dark web UI refreshed every 2 seconds
```

## Captured Fields

- PID
- Process command name
- Kernel timestamp converted for dashboard display

## Requirements

- Ubuntu Desktop 24.04 LTS
- Linux kernel 6.x
- Python 3
- Flask
- BCC / bpfcc packages
- Root privileges to load eBPF programs

## Installation

```bash
chmod +x scripts/install.sh scripts/run.sh
./scripts/install.sh
```

The installer verifies the kernel major version, installs BCC dependencies with `apt`, creates a local Python virtual environment with access to the system-installed BCC bindings, and installs Flask.

## Run

```bash
sudo ./scripts/run.sh
```

Open the dashboard:

```text
http://127.0.0.1:5000
```

## Demo Scenario

Terminal 1:

```bash
sudo ./scripts/run.sh
```

Terminal 2:

```bash
ls
whoami
ip a
ping 8.8.8.8
```

Expected result: the dashboard updates automatically and displays process execution events for the commands.

## Dashboard

The dashboard shows:

- Total events
- Unique commands from the retained event window
- Last update time
- Event table with timestamp, PID, and command

It keeps only the last 100 events in memory and refreshes every 2 seconds.

## Screenshots

Add screenshots here after running the demo:

```text
docs/screenshots/dashboard.png
```

## Project Structure

```text
linux-ebpf-exec-monitor/
├── ebpf/
│   └── exec_monitor.c
├── user/
│   ├── loader.py
│   └── models.py
├── web/
│   ├── app.py
│   ├── static/
│   │   └── style.css
│   └── templates/
│       └── index.html
├── scripts/
│   ├── install.sh
│   └── run.sh
├── tests/
│   ├── test_models.py
│   └── test_web.py
├── requirements.txt
├── README.md
├── README.fa.md
├── LICENSE
└── .gitignore
```

## Educational Limitations

- Tracks process execution only, not file, network, or authentication activity.
- Stores events only in memory, so data is lost when the program stops.
- Uses a simple browser refresh instead of streaming updates.
- Does not include authentication or access control.
- Does not normalize or enrich events like a SIEM.
- Designed for a single Linux machine demonstration.

## Tests

Run the unit tests without root privileges:

```bash
python3 -m unittest discover -s tests
```

## Future Improvements

- Add command path capture from tracepoint fields.
- Add JSON export for captured events.
- Add filtering by PID or command.
- Add optional CSV logging.
- Add a small systemd service for lab environments.
