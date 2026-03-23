# sys-health-check

> **"Instead of manually checking every system one by one, I built a tool that does it automatically — and tells you exactly what's wrong."**

A cross-platform IT support automation tool that diagnoses system health, identifies root causes, cleans up temp files, and sends a Gmail alert when action is needed.

No manual digging. No wasted time. Just run it and get answers.

---

## Scenario

A user submits a ticket: *"My computer is running slow."*

The technician manually checks Task Manager, disk usage, and network status one by one — spending 10–15 minutes just to figure out what's wrong, before any fix even starts.

## Problem

Every ticket like this follows the same repetitive steps:

1. Open Task Manager — check CPU and RAM manually
2. Open File Explorer — check disk usage manually
3. Run `ping` / `ipconfig` — check network manually
4. Check each service — one by one

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
- Validates and installs dependencies automatically on first run

### How it works

```
python health_check.py
        |
        v
  setup.py                Validate dependencies from config.json
  (auto-install missing)
        |
        v
  checkers.py             Measure CPU / RAM / Disk / Network / Services
        |
        v
  reporter.py             Build report — if WARNING -> call analyzers.py
        |
        +-- OK ---------->  Print report + save log
        |
        +-- WARNING ------->  Print report + save log
                               |
                               v
                        remediation.py
                        | Check admin privileges
                        |   +-- Admin    : clean user temp + system temp
                        |   +-- No admin : clean user temp only
                        |                 prompt to relaunch as admin
                        |
                        v
                        email_alert.py
                        | Send Gmail alert with report + cleanup summary
```

### Module breakdown

```
sys-health-check/
├── health_check.py   # Entry point — orchestrates the full workflow
├── checkers.py       # Measures CPU, RAM, Disk, Network, Services
├── analyzers.py      # Identifies root cause when WARNING is detected
├── remediation.py    # Temp file cleanup with admin-aware logic
├── email_alert.py    # Gmail alert — standalone, single responsibility
├── reporter.py       # Builds the report and saves the log
├── utils.py          # Shared helpers (separator, timestamp)
├── config.json       # Dependency definitions
├── setup.py          # Auto dependency checker and installer
├── .env.example      # Credential template (never commit .env)
├── .gitignore
└── logs/             # Auto-generated timestamped log files
```

**`health_check.py`** — Entry point. Validates dependencies first, then orchestrates the workflow.

```python
run_setup()                              # 0. validate dependencies
results          = run_all_checks()      # 1. measure
report, overall  = build_report(results) # 2. build report
save_log(report)                         # 3. save log
if WARNING:                              # 4. act
    cleanup_temp_files()
    send_alert_email()
```

**`config.json`** — Single source of truth for all third-party dependencies.

```json
{
  "dependencies": [
    { "import_name": "psutil",  "install_name": "psutil",        "version": ">=5.9.0" },
    { "import_name": "dotenv",  "install_name": "python-dotenv", "version": ">=1.0.0" }
  ]
}
```

**`setup.py`** — Reads `config.json`, checks if each package is installed, and installs any that are missing via pip. Exits with an error if installation fails.

**`checkers.py`** — Runs all health checks and returns structured results.

| Function | What it checks | WARNING threshold |
|---|---|---|
| `check_cpu()` | Usage %, core count | >= 80% |
| `check_ram()` | Used / total GB | >= 80% |
| `check_disk()` | Used / total GB | >= 85% |
| `check_network()` | DNS resolution to google.com | Unreachable |
| `check_services()` | Key OS services running status | Not running |

**`analyzers.py`** — Triggered automatically when a check returns WARNING. Surfaces the root cause so the technician knows exactly what to fix.

| Function | Triggered by | What it finds |
|---|---|---|
| `analyze_cpu()` | CPU WARNING | Top 5 CPU-consuming processes (PID, name, %) |
| `analyze_ram()` | RAM WARNING | Top 5 memory-consuming processes (PID, name, MB) |
| `analyze_disk()` | Disk WARNING | Top 5 largest items in home directory |
| `analyze_network()` | Network WARNING | DNS -> interfaces -> internet reachability |

**`remediation.py`** — Triggered only when OVERALL status is WARNING. Handles temp file cleanup with admin-aware logic.

| Function | What it does |
|---|---|
| `is_admin()` | Checks for administrator privileges (Windows UAC / Unix root) |
| `_get_temp_paths(admin)` | Returns temp paths based on privilege level |
| `_clean_directory(path)` | Cleans a single directory, distinguishes locked files from real errors |
| `cleanup_temp_files()` | Orchestrates cleanup, prompts admin relaunch if needed |

Temp file cleanup behavior:

| Privilege | Directories cleaned |
|---|---|
| Admin | User temp + `C:\Windows\Temp` (Windows) / `/tmp` + `~/.cache` (macOS/Linux) |
| No admin | User temp only — prompts to relaunch as admin for system temp |

File handling during cleanup:

| Case | Behavior |
|---|---|
| Deleted successfully | Counted in `deleted`, size added to `freed_mb` |
| Locked by another process (WinError 32) | Counted in `locked` — skipped safely |
| Other OS error | Counted in `errors` |

**`email_alert.py`** — Standalone Gmail alert module. Single responsibility: compose and send the alert email.

| Function | What it does |
|---|---|
| `_build_email_body()` | Composes email body from report and cleanup summary |
| `send_alert_email()` | Sends Gmail alert via SMTP SSL using EmailMessage API |

Uses Python's `EmailMessage` (modern API) which handles encoding natively. Credentials loaded from `.env` — never hardcoded.

**`reporter.py`** — Assembles the final report from all check and analysis results, then saves it as a timestamped log.

**`utils.py`** — Shared helpers used across all modules (`separator()`, `timestamp()`).

## Result

| | Before | After |
|---|---|---|
| Diagnosis time | 10-15 min manual | Under 60 sec automated |
| Root cause | Found manually | Surfaced automatically |
| Temp file cleanup | Done manually | Triggered automatically on WARNING |
| System temp cleanup | Requires manual admin steps | Auto-detected, UAC prompt on demand |
| Locked files | Caused confusing errors | Identified and skipped safely |
| Documentation | Not saved | Timestamped log auto-saved |
| Alert | Phone call / chat | Gmail alert auto-sent |
| Dependencies | Manual pip install | Auto-checked and installed via config.json |
| OS support | Single platform | Windows, macOS, Linux |

---

## Sample Output

Normal state:
```
Checking dependencies...

  [OK]      Already installed : psutil, python-dotenv

Running system health check...

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

Log saved -> C:\...\logs\health_20260323_143201.log
```

WARNING with root cause analysis, cleanup, and alert:
```
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
----------------------------------------
  OVERALL : WARNING - check items above
----------------------------------------

OVERALL WARNING detected — running cleanup and sending alert...

  [CLEANUP] Admin privileges : No
  [CLEANUP] C:\Users\username\AppData\Local\Temp    3 deleted, 20 locked (in use), 45.2 MB freed

  [CLEANUP] System temp (C:\Windows\Temp) was skipped — requires admin privileges.
  [CLEANUP] Relaunch as administrator to clean system temp? [y/N]:

  [EMAIL] Alert sent successfully.
```

---

## Requirements

- Python 3.7+
- Dependencies are defined in `config.json` and installed automatically on first run.

To install manually:
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

**2. Configure credentials**

Copy `.env.example` to `.env` and fill in your Gmail details:
```
SENDER_EMAIL=your_gmail@gmail.com
SENDER_PASSWORD=your_16_digit_app_password
RECEIVER_EMAIL=receiver_email@gmail.com
```

> Gmail requires an [App Password](https://support.google.com/accounts/answer/185833) — not your regular password.
> Go to Google Account -> Security -> App Passwords to generate one.
> When copying the app password, type it manually without spaces to avoid hidden non-breaking space characters.

**3. Run**
```bash
python health_check.py
```

Dependencies are checked and installed automatically on first run.

---

## Cross-Platform Support

| OS | Disk path | User temp | System temp (admin only) | Services monitored |
|---|---|---|---|---|
| Windows | C:\ | %TEMP% | C:\Windows\Temp | Spooler, wuauserv |
| macOS | / | ~/.cache | /tmp | com.apple.metadata.mds |
| Linux | / | ~/.cache | /tmp | cron, ssh |

---

## Skills Demonstrated

- Modular Python design (single-responsibility per module)
- IT support troubleshooting logic — detect -> analyze -> remediate -> alert
- Automated root cause analysis (`psutil`)
- Admin privilege detection and graceful degradation
- OS-level error handling (WinError 32 file lock distinction)
- Cross-platform compatibility (Windows / macOS / Linux)
- Dependency management via `config.json` + auto-installer
- Secure credential handling via `.env` + `.gitignore`
- Structured log generation
- Gmail SMTP integration (`EmailMessage` API)