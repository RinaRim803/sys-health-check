# System Health Check

A cross-platform IT support automation script that diagnoses common system issues — CPU, RAM, disk, network, and services — and saves a timestamped report automatically.

---

## Scenario

> A user submits a ticket: *"My computer is running slow."*
> The technician manually checks Task Manager, disk usage, and network status one by one — taking 10–15 minutes per ticket.

## Problem

Repetitive manual diagnostics consume significant time on every ticket.
There is no quick way to get a full system snapshot before jumping into troubleshooting.

## Solution

A single Python script that automatically checks all key system health indicators and outputs a structured report — ready in under 60 seconds.

## Result

| Before | After |
|---|---|
| 10–15 min manual check | Under 1 min automated report |
| No log saved | Timestamped log saved automatically |
| Windows only workflow | Works on Windows, macOS, and Linux |

---

## What It Checks

| Category | Details |
|---|---|
| CPU | Usage percentage, core count |
| RAM | Used / total GB, usage percentage |
| Disk | Used / total GB, usage percentage (C:\ on Windows, / on others) |
| Network | Connectivity check via DNS resolution |
| Services | Key OS services running status |

Each item is flagged as `OK` or `WARNING` based on thresholds.
A final `OVERALL` status summarizes the result.

---

## Sample Output

```
----------------------------------------
  SYSTEM HEALTH CHECK REPORT
  2026-03-23 14:32:01
  OS : Windows 11
----------------------------------------
[CPU]
  Usage   : 23.0%  (8 cores)  [OK]
[RAM]
  Used    : 5.2 GB / 16.0 GB  (32%)  [OK]
[DISK]
  Used    : 112.4 GB / 476.0 GB  (24%)  [OK]
[NETWORK]
  Status  : Connected  [OK]
[SERVICES]
  Spooler              Running  [OK]
  wuauserv             Running  [OK]
----------------------------------------
  OVERALL : ALL SYSTEMS OK
----------------------------------------
```

---

## Requirements

- Python 3.7+
- [psutil](https://pypi.org/project/psutil/)

```bash
pip install psutil
```

---

## Usage

```bash
python health_check.py
```

The report is printed to the console and automatically saved to a `logs/` folder in the same directory.

```
logs/
└── health_20260323_143201.log
```

---

## Cross-Platform Support

| OS | Disk Path | Services Monitored |
|---|---|---|
| Windows | C:\ | Spooler, wuauserv |
| macOS | / | com.apple.metadata.mds |
| Linux | / | cron, ssh |

---

## Skills Demonstrated

- Python scripting (`psutil`, `socket`, `platform`)
- Cross-platform compatibility (Windows / macOS / Linux)
- Automated log generation
- IT support troubleshooting workflow automation