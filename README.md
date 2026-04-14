# sys-health-check

> **"Instead of manually checking every system one by one, I built a tool that does it automatically — and tells you exactly what's wrong."**

A cross-platform IT support automation tool that diagnoses system health, identifies root causes, cleans up temp files, and sends a Gmail alert when action is needed.

No manual digging. No wasted time. Just run it and get answers.


---

## 📋 Scenario & Problem Solving

### The Standard Ticket: *"My computer is running slow."*
**The Situation:** A user submits a ticket: *"My computer is running slow."*

**The Problem:** The technician manually checks Task Manager, disk usage, and network status one by one — spending 10–15 minutes just to figure out what's wrong, before any fix even starts. 

Every ticket like this follows the same repetitive steps:

1. Open Task Manager — check CPU and RAM manually
2. Open File Explorer — check disk usage manually
3. Run `ping` / `ipconfig` — check network manually
4. Check each service — one by one

There is no quick way to get a full system snapshot *and* identify the root cause at the same time. Time is wasted on diagnosis instead of resolution.

**The Solution:** A modular Python tool that runs a full system health check in one command — and automatically digs into the root cause when something is wrong.

```bash
python health_check.py
```

- Detects the current OS and selects the appropriate collector automatically
- **Windows**: collects via PowerShell (`Collectors.psm1`) for native WMI accuracy
- **macOS / Linux**: collects via Python (`psutil`)
- Both collectors output a canonical v1.1 JSON schema — reporter handles both identically
- Automatically identifies root cause when a WARNING is detected
- Cleans up temporary files if the system is under stress
- Sends a Gmail alert with the full report when overall status is WARNING
- **Auto-creates tickets in IT Ticket System for each WARNING item**
- Saves a timestamped log for every run
- All thresholds and service targets controlled via `config.json` — no code changes needed

## 📌 Performance Impact


| Category | Manual Process (Before) | **Automated Solution (After)** |
| :--- | :--- | :--- |
| **Response Velocity** | 10–15 min per case | **< 60 seconds (93% faster)** |
| **Root Cause Analysis** | Manual log inspection | **Instant automated surfacing** |
| **Incident Management** | Manual ticket entry | **Auto-ticket per WARNING item (full report attached)** |
| **System Maintenance** | Ad-hoc temp file cleanup | **Proactive cleanup on WARNING threshold** |
| **Notification** | Manual escalation (Call / Chat) | **Real-time SMTP / Gmail alert** |
| **Configuration** | Thresholds hardcoded in source | **Controlled via config.json — no code changes needed** |
| **Scalability** | Single platform, manual setup | **Cross-platform: Windows (PowerShell) / macOS / Linux (Python)** |
| **Data Integrity** | No persistent records | **Timestamped log + full audit trail per run** |
 

---
## 🛠️ How it works

<img width="704" height="384" alt="sys-health-checker-system-architecture-visualization" src="https://github.com/user-attachments/assets/ba63a820-0b5c-4b88-99ad-458b83a5d461" />

```
python health_check.py
        |
        v
  health_check.py         Detect OS → select collector
        |
        +-- Windows -----> collectors/powershell/collector.py
        |                  | subprocess call to collect_health.ps1
        |                  | collect_health.ps1 imports Collectors.psm1
        |                  | Get-CpuInfo / Get-MemoryInfo / Get-DiskInfo
        |                  | Get-ServicesInfo / Get-NetworkInfo
        |                  | ConvertTo-Json → stdout
        |                  v
        |                  json.loads() → v1.1 schema dict
        |
        +-- macOS/Linux -> collectors/python/collector.py
                           | checkers.py → psutil
                           | translate to v1.1 schema dict
                           v
 
  Both paths produce identical v1.1 schema dict
        |
        v
  reporter.py             Build report from schema — OS-aware service section
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
                        |
                        v
                        integrations/health_check_client.py
                        | POST /api/tickets -> IT Ticket System
                        | One ticket per WARNING item
                        | Full diagnostic report attached
                        | Fails gracefully if server is not running
```


## 📊 Sample Report Output

 
**Windows (PowerShell collector):**
```
  [COLLECTOR] Windows detected — using PowerShell collector
 
----------------------------------------
  SYSTEM HEALTH CHECK REPORT
  2026-04-07 14:32:01
  OS       : Windows Windows 11
  Executor : PowerShell_Collector_v1
  Host     : VAN-IT-WS01
----------------------------------------
[CPU]
  Usage   : 23.0%  (8 cores)  [OK]
[RAM]
  Used    : 5.2 GB / 16.0 GB  (32.5%)  [OK]
[DISK]
  Used    : 112.4 GB / 476.0 GB  (23.6%)  [OK]
[NETWORK]
  Status  : Connected  [OK]
[SERVICES]  (Windows)
  Spooler              Running  [OK]
  wuauserv             Running  [OK]
----------------------------------------
  OVERALL : ALL SYSTEMS OK
----------------------------------------
```
 
**WARNING with root cause analysis, cleanup, alert, and auto-ticketing:**
```
  [COLLECTOR] Windows detected — using PowerShell collector
 
----------------------------------------
[CPU]
  Usage   : 91.0%  (8 cores)  [WARNING]
  >> Root cause analysis: top CPU-consuming processes
     PID 4821   chrome.exe                47.3%
     PID 1204   python.exe                18.1%
     PID 3390   Teams.exe                 12.4%
[RAM]
  Used    : 14.1 GB / 16.0 GB  (88.1%)  [WARNING]
  >> Root cause analysis: top RAM-consuming processes
     PID 4821   chrome.exe                4821.3 MB
     PID 3390   Teams.exe                 1203.7 MB
[SERVICES]  (Windows)
  Spooler              Running   [OK]
  wuauserv             Not found [WARNING]
----------------------------------------
  OVERALL : WARNING - check items above
----------------------------------------
 
OVERALL WARNING detected — running cleanup and sending alert...
 
  [CLEANUP] Admin privileges : No
  [CLEANUP] C:\Users\username\AppData\Local\Temp    3 deleted, 20 locked, 45.2 MB freed
  [CLEANUP] Relaunch as administrator to clean system temp? [y/N]:
 
  [EMAIL] Alert sent successfully.
 
  [TICKET] Creating tickets for WARNING items...
  [TICKET] #1 created — P2 | Hardware | High CPU Usage Detected
  [TICKET] #2 created — P2 | Hardware | High Memory Usage Detected
  [TICKET] #3 created — P2 | Hardware | Service Unavailable: wuauserv
```

## Module breakdown

```
sys-health-check/
├── health_check.py              # Orchestrator — detects OS, selects collector
├── reporter.py                  # Builds report from v1.1 schema, saves log
├── analyzers.py                 # Root cause analysis when WARNING detected
├── remediation.py               # Temp file cleanup with admin-aware logic
├── email_alert.py               # Gmail alert — standalone, single responsibility
├── utils.py                     # Shared helpers (separator, timestamp)
├── config.json                  # Thresholds, service targets, network settings
├── config.py                    # Python config loader (cached)
├── .env.example                 # Credential template (never commit .env)
├── .gitignore
├── logs/                        # Auto-generated timestamped log files
│
├── collectors/
│   ├── python/
│   │   ├── checkers.py          # psutil-based checks (macOS / Linux)
│   │   └── collector.py        # Translates checkers.py output → v1.1 schema
│   └── powershell/
│       ├── Collectors.psm1      # PowerShell collection functions (Windows)
│       ├── collect_health.ps1   # Orchestrator — imports .psm1, outputs JSON
│       └── collector.py        # subprocess call → json.loads() → v1.1 schema
│
├── schemas/
│   └── health_schema_v1.1.json  # Canonical data contract for all collectors
│
└── integrations/
    ├── __init__.py
    └── health_check_client.py   # HTTP client → IT Ticket System API
```


**`health_check.py`** — Orchestrator. Detects OS, selects the correct collector, then drives the full workflow.
 
```python
collect          = get_collector()       # 0. select by OS
data             = collect()             # 1. measure → v1.1 schema dict
report, overall  = build_report(data)    # 2. build report
save_log(report)                         # 3. save log
if WARNING:                              # 4. act
    cleanup_temp_files()
    send_alert_email()
    create_tickets_for_warnings()        # 5. auto-create tickets per WARNING item
```
**`config.json`** — Single source of truth for thresholds, service targets, and network settings. Shared by both Python and PowerShell collectors — no hardcoding in either.
 
```json
{
  "thresholds": {
    "cpu_warning_pct":    80,
    "memory_warning_pct": 80,
    "disk_warning_pct":   85
  },
  "services": {
    "Windows": ["Spooler", "wuauserv"],
    "Darwin":  ["com.apple.metadata.mds"],
    "Linux":   ["cron", "ssh"]
  },
  "network": {
    "dns_check_host": "google.com",
    "dns_timeout_sec": 3
  }
}
```
 
**`collectors/python/checkers.py`** — Runs health checks via psutil on macOS and Linux. Thresholds and service targets loaded from `config.json`.
 
| Function | What it checks | WARNING threshold |
|---|---|---|
| `check_cpu()` | Usage %, core count | `cpu_warning_pct` from config |
| `check_ram()` | Used / total GB | `memory_warning_pct` from config |
| `check_disk()` | Used / total GB | `disk_warning_pct` from config |
| `check_network()` | DNS resolution | Unreachable |
| `check_services()` | OS-specific services | Not running |
 
**`collectors/powershell/Collectors.psm1`** — PowerShell module containing all collection functions for Windows. Mirrors `checkers.py` in structure. Thresholds and service targets loaded from the same `config.json`.
 
| Function | Method | What it collects |
|---|---|---|
| `Get-CpuInfo` | Performance Counter (Cooked Value avg) | CPU usage %, core count |
| `Get-MemoryInfo` | WMI Win32_OperatingSystem | Memory used / total GB |
| `Get-DiskInfo` | WMI Win32_LogicalDisk | Disk used / total GB (C:) |
| `Get-ServicesInfo` | Get-Service | Windows service running status |
| `Get-NetworkInfo` | System.Net.Dns | DNS resolution check |
 
**`collectors/powershell/collect_health.ps1`** — Orchestrator for the PowerShell side. Imports `Collectors.psm1`, calls each function, assembles the v1.1 schema, and outputs it as JSON to stdout. Python reads this via subprocess.
 
**`collectors/python/collector.py` / `collectors/powershell/collector.py`** — Translation layer. Converts raw collector output into the canonical v1.1 schema dict. `reporter.py` only knows about this schema — never about where the data came from.
 
**`schemas/health_schema_v1.1.json`** — Data contract. Defines the exact field names and structure both collectors must produce. Acts as the source of truth when adding a new collector (e.g. Bash).
 
**`analyzers.py`** — Triggered automatically when a check returns WARNING. Surfaces the root cause so the technician knows exactly what to fix.
 
| Function | Triggered by | What it finds |
|---|---|---|
| `analyze_cpu()` | CPU WARNING | Top 5 CPU-consuming processes (PID, name, %) |
| `analyze_ram()` | RAM WARNING | Top 5 memory-consuming processes (PID, name, MB) |
| `analyze_disk()` | Disk WARNING | Top 5 largest items in home directory |
| `analyze_network()` | Network WARNING | DNS → interfaces → internet reachability |
 
**`remediation.py`** — Triggered only when OVERALL status is WARNING. Handles temp file cleanup with admin-aware logic.
 
| Privilege | Directories cleaned |
|---|---|
| Admin | User temp + `C:\Windows\Temp` (Windows) / `/tmp` + `~/.cache` (macOS/Linux) |
| No admin | User temp only — prompts to relaunch as admin for system temp |
 
| Case | Behavior |
|---|---|
| Deleted successfully | Counted in `deleted`, size added to `freed_mb` |
| Locked by another process (WinError 32) | Counted in `locked` — skipped safely |
| Other OS error | Counted in `errors` |
 
**`email_alert.py`** — Standalone Gmail alert module. Uses Python's `EmailMessage` API. Credentials loaded from `.env` — never hardcoded.
 
**`integrations/health_check_client.py`** — HTTP client that converts WARNING check results into ticket payloads and POSTs them to the IT Ticket System API.
 
| Alert type | Triggered by | Ticket title |
|---|---|---|
| `cpu` | CPU WARNING | High CPU Usage Detected |
| `memory` | RAM WARNING | High Memory Usage Detected |
| `disk` | Disk WARNING | Low Disk Space Detected |
| `network` | Network WARNING | Network Connectivity Lost |
| `service` | Service WARNING | Service Unavailable: {name} |

---
## Integration with IT Ticket System
 
This tool is part of a three-project IT support automation pipeline:
 
```
sys-health-check   (this project)
  └─ Detects system anomalies
       └─ Auto-creates tickets in IT Ticket System on WARNING
 
network-troubleshooter
  └─ Runs full-stack network diagnostics
       └─ Auto-creates tickets with diagnostic report attached
 
it-ticket-system
  └─ Central ITSM server — receives alerts, classifies, prioritizes,
     tracks tickets to resolution via REST API
```
 
The integration is **optional and non-blocking** — if the IT Ticket System server is not running, `health_check.py` continues normally and prints `[TICKET] Skipped`.
 


## 🗺️ Roadmap
 
- [x] **v1.0** — Python-based health check: CPU, RAM, Disk, Network, Services
- [x] **v1.0** — Root cause analysis, temp cleanup, Gmail alert, auto-ticketing
- [x] **v1.1** — Collector architecture: OS detection → Python or PowerShell collector
- [x] **v1.1** — PowerShell collector: `Collectors.psm1` module + `collect_health.ps1`
- [x] **v1.1** — Canonical v1.1 JSON schema: shared data contract across all collectors
- [x] **v1.1** — `config.json`: thresholds and service targets shared by both collectors
- [ ] **v1.2** — Bash collector for Linux environments
- [ ] **v1.3** — Scheduled task support: run silently without prompts (`--mode user/admin`)

---
## Requirements

- Python 3.7+
- Dependencies are defined in `requirements.txt`

**Install dependencies:**
```bash
pip install -r requirements.txt
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
pip install -r requirements.txt
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


**3. (Optional) Start IT Ticket System server**
 
To enable auto-ticketing on WARNING, start the IT Ticket System server first:
```bash
cd ../it-ticket-system
python server.py
```

**4. Run**
```bash
python health_check.py
```


---

## Cross-Platform Support

| OS | Disk path | User temp | System temp (admin only) | Services monitored |
|---|---|---|---|---|
| Windows | C:\ | %TEMP% | C:\Windows\Temp | Spooler, wuauserv |
| macOS | / | ~/.cache | /tmp | com.apple.metadata.mds |
| Linux | / | ~/.cache | /tmp | cron, ssh |

---

## 💻 Skills Demonstrated 
- Modular Python design (single-responsibility per module)
- IT support troubleshooting logic — detect -> analyze -> remediate -> alert
- Automated root cause analysis (`psutil`)
- Admin privilege detection and graceful degradation
- OS-level error handling (WinError 32 file lock distinction)
- Cross-platform compatibility (Windows / macOS / Linux)
- Secure credential handling via `.env` + `.gitignore`
- Structured log generation
- Gmail SMTP integration (`EmailMessage` API)
- REST API integration — HTTP client sending structured payloads to a Flask API server
