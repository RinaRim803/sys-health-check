# sys-health-check

> **"Instead of manually checking every system one by one, I built a tool that does it automatically — and tells you exactly what's wrong."**

A cross-platform IT support automation tool that diagnoses system health, identifies root causes, cleans up temp files, and sends a Gmail alert when action is needed.

---

## Scenario

A user submits a ticket: *"My computer is running slow."*

The technician manually checks Task Manager, disk usage, and network status one by one — spending 10–15 minutes just to figure out what's wrong, before any fix even starts.

## Problem

Every ticket like this follows the same repetitive steps:

1. Open Task Manager → check CPU and RAM manually
2. Open File Explorer → check disk usage manually
3. Run `ping` / `ipconfig` → check network manually
4. Check each service → one by one

There is no quick way to get a full system snapshot *and* identify the root cause at the same time. Time is wasted on diagnosis instead of resolution.

## Solution

A modular Python tool that runs a full system health check in one command — and automatically digs into the root cause when something is wrong.

```bash
python health_check.py
```

- Checks CPU, RAM, Disk, Network, and Services in a single run
- Automatically identifies root cause when a WARNING is detected
- Cleans up temporary files if the system is under stress
- Sends a Gmail alert with the full report when overall status is WARNING
- Saves a timestamped log for every run

### How it works

```
Run health_check.py
        │
        ▼
  checkers.py          Measure CPU / RAM / Disk / Network / Services
        │
        ▼
  reporter.py          Build report — if WARNING → call analyzers.py
        │
        ├─ OK ──────▶  Print report + save log
        │
        └─ WARNING ──▶  Print report + save log
                               │
                               ▼
                        remediation.py
                        ├─ Clean up temp files
                        └─ Send Gmail alert
```

### Module breakdown

```
sys-health-check/
├── health_check.py   # Entry point — orchestrates the full workflow
├── checkers.py       # Measures CPU, RAM, Disk, Network, Services
├── analyzers.py      # Identifies root cause when WARNING is detected
├── remediation.py    # Cleans temp files and sends Gmail alert
├── reporter.py       # Builds the report and saves the log
├── utils.py          # Shared helpers (separator, timestamp)
├── .env.example      # Credential template (never commit .env)
├── .gitignore
└── logs/             # Auto-generated timestamped log files
```

**`health_check.py`** — Entry point. Orchestrates the full workflow in four steps, contains no logic of its own.

```python
results          = run_all_checks()       # 1. measure
report, overall  = build_report(results)  # 2. build report
save_log(report)                          # 3. save log
if WARNING → cleanup + send_alert_email() # 4. act
```

**`checkers.py`** — Runs all health checks and returns structured results.

| Function | What it checks | WARNING threshold |
|---|---|---|
| `check_cpu()` | Usage %, core count | ≥ 80% |
| `check_ram()` | Used / total GB | ≥ 80% |
| `check_disk()` | Used / total GB | ≥ 85% |
| `check_network()` | DNS resolution to google.com | Unreachable |
| `check_services()` | Key OS services running status | Not running |

**`analyzers.py`** — Triggered automatically when a check returns WARNING. Surfaces the root cause so the technician knows exactly what to fix.

| Function | Triggered by | What it finds |
|---|---|---|
| `analyze_cpu()` | CPU WARNING | Top 5 CPU-consuming processes (PID, name, %) |
| `analyze_ram()` | RAM WARNING | Top 5 memory-consuming processes (PID, name, MB) |
| `analyze_disk()` | Disk WARNING | Top 5 largest items in home directory |
| `analyze_network()` | Network WARNING | DNS → interfaces → internet reachability |

**`remediation.py`** — Triggered only when OVERALL status is WARNING. Takes action without waiting for a technician.

| Function | What it does |
|---|---|
| `cleanup_temp_files()` | Deletes temp files from OS temp directories |
| `send_alert_email()` | Sends Gmail alert with full report and cleanup summary |

**`reporter.py`** — Assembles the final report and saves the log.

**`utils.py`** — Shared helpers used across all modules (`separator()`, `timestamp()`).

## Result

| | Before | After |
|---|---|---|
| Diagnosis time | 10–15 min manual | Under 60 sec automated |
| Root cause | Found manually | Surfaced automatically |
| Temp file cleanup | Done manually | Triggered automatically on WARNING |
| Documentation | Not saved | Timestamped log auto-saved |
| Alert | Phone call / chat | Gmail alert auto-sent |
| OS support | Single platform | Windows, macOS, Linux |

---

## Sample Output

Normal state:
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

WARNING with automatic root cause analysis:
```
----------------------------------------
  SYSTEM HEALTH CHECK REPORT
  2026-03-23 14:35:20
  OS : Windows 11
----------------------------------------
[CPU]
  Usage   : 91.0%  (8 cores)  [WARNING]
  >> Root cause analysis: top CPU-consuming processes
     PID 4821   chrome.exe                47.3%
     PID 1204   python.exe                18.1%
     PID 3390   Teams.exe                 12.4%
     PID 992    SearchIndexer.exe          8.2%
     PID 512    svchost.exe                3.1%
[RAM]
  Used    : 14.1 GB / 16.0 GB  (88%)  [WARNING]
  >> Root cause analysis: top RAM-consuming processes
     PID 4821   chrome.exe                4821.3 MB
     PID 3390   Teams.exe                 1203.7 MB
     PID 1204   python.exe                 512.2 MB
     PID 788    explorer.exe               204.1 MB
     PID 512    svchost.exe                189.6 MB
----------------------------------------
  OVERALL : WARNING — check items above

OVERALL WARNING detected — running cleanup and sending alert...
  [CLEANUP] Done — 142 items deleted, 380.4 MB freed, 3 errors skipped.
  [EMAIL] Alert sent successfully.
----------------------------------------
```

---

## Requirements

- Python 3.7+
- [psutil](https://pypi.org/project/psutil/)
- [python-dotenv](https://pypi.org/project/python-dotenv/)

```bash
pip install psutil python-dotenv
```

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/username/sys-health-check.git
cd sys-health-check
```

**2. Install dependencies**
```bash
pip install psutil python-dotenv
```

**3. Configure credentials**

Copy `.env.example` to `.env` and fill in your Gmail details:
```
SENDER_EMAIL=your_gmail@gmail.com
SENDER_PASSWORD=your_16_digit_app_password
RECEIVER_EMAIL=receiver_email@gmail.com
```

> Gmail requires an [App Password](https://support.google.com/accounts/answer/185833) — not your regular password.
> Go to Google Account → Security → App Passwords to generate one.

**4. Run**
```bash
python health_check.py
```

---

## Cross-Platform Support

| OS | Disk path | Temp directories | Services monitored |
|---|---|---|---|
| Windows | C:\ | %TEMP%, %TMP%, C:\Windows\Temp | Spooler, wuauserv |
| macOS | / | /tmp, ~/.cache | com.apple.metadata.mds |
| Linux | / | /tmp, ~/.cache | cron, ssh |

---

## Skills Demonstrated

- Modular Python design (single-responsibility per module)
- IT support troubleshooting logic — detect → analyze → remediate → alert
- Automated root cause analysis (`psutil`)
- Cross-platform compatibility (Windows / macOS / Linux)
- Secure credential handling via `.env` + `.gitignore`
- Structured log generation
- Gmail SMTP integration