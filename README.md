# System Health Check

A cross-platform IT support automation script that diagnoses system issues and automatically traces the root cause — so technicians spend less time investigating and more time resolving.

---

## Scenario

> A user submits a ticket: *"My computer is running slow."*
> The technician manually checks Task Manager, disk usage, and network status one by one — taking 10–15 minutes before even starting to fix the issue.

## Problem

Repetitive manual diagnostics consume significant time on every ticket.
There is no quick way to get a full system snapshot — let alone identify *why* a resource is under pressure — before jumping into troubleshooting.

## Solution

A single Python script that:
1. Checks all key system health indicators (CPU, RAM, Disk, Network, Services)
2. Flags any item that exceeds safe thresholds as `WARNING`
3. **Automatically traces the root cause** of each warning — no manual follow-up needed

## Result

| | Before | After |
|---|---|---|
| Diagnosis time | 10–15 min manual | Under 1 min automated |
| Root cause | Manual investigation | Auto-identified |
| Log | None | Timestamped log saved automatically |
| OS support | Windows only workflow | Windows / macOS / Linux |

---

## What It Checks

| Category | Threshold | Auto Root Cause Analysis |
|---|---|---|
| CPU | ≥ 80% | Top 5 CPU-consuming processes (PID + usage %) |
| RAM | ≥ 80% | Top 5 RAM-consuming processes (PID + memory MB) |
| Disk | ≥ 85% | Top 5 largest items in home directory |
| Network | DNS failure | Step-by-step path diagnosis (DNS → interfaces → internet) |
| Services | Not running | Flagged by name |

Each item is reported as `OK` or `WARNING`.
When `WARNING` is detected, root cause analysis runs automatically — no extra commands needed.

---

## Sample Output

### All systems healthy

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

### WARNING detected — root cause auto-traced

```
----------------------------------------
  SYSTEM HEALTH CHECK REPORT
  2026-03-23 09:15:44
  OS : Windows 11
----------------------------------------
[CPU]
  Usage   : 91.0%  (8 cores)  [WARNING]
  >> Root cause analysis: top CPU-consuming processes
     PID 4821   chrome.exe                52.3%
     PID 1032   MsMpEng.exe               18.1%
     PID 7204   python.exe                10.4%
     PID 392    svchost.exe               4.2%
     PID 2140   Teams.exe                 3.8%
[RAM]
  Used    : 13.8 GB / 16.0 GB  (86%)  [WARNING]
  >> Root cause analysis: top RAM-consuming processes
     PID 4821   chrome.exe                3,840.2 MB
     PID 2140   Teams.exe                 1,204.5 MB
     PID 1032   MsMpEng.exe               512.3 MB
     PID 7204   python.exe                198.7 MB
     PID 908    explorer.exe              143.1 MB
[DISK]
  Used    : 418.0 GB / 476.0 GB  (88%)  [WARNING]
  >> Root cause analysis: largest items in home directory
     Downloads                           48,302.4 MB
     Videos                              31,500.0 MB
     AppData                             12,880.1 MB
     Documents                           2,304.6 MB
     Desktop                             980.2 MB
[NETWORK]
  Status  : Connected  [OK]
[SERVICES]
  Spooler              Running  [OK]
  wuauserv             Running  [OK]
----------------------------------------
  OVERALL : WARNING — check items above
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
sys-health-check/
├── health_check.py
└── logs/
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

- Python scripting (`psutil`, `socket`, `platform`, `os`)
- Cross-platform compatibility (Windows / macOS / Linux)
- IT support troubleshooting logic (detect → trace → report)
- Automated log generation
- Process-level root cause analysis