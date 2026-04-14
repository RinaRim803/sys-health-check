"""
collectors/powershell/collector.py
PowerShell collector for Windows.

Calls collect_health.ps1 (sibling in this package) via subprocess,
reads its stdout as JSON, and returns a v1.1 schema-compliant dict.

The .ps1 script owns all data collection logic.
This module owns the subprocess call and error handling only.

Public interface:
    collect() -> dict   # returns v1.1 schema-compliant dict
"""

import json
import os
import subprocess
from datetime import datetime, timezone

# collect_health.ps1 is a sibling in the same package (collectors/powershell/)
_PS1_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "collect_health.ps1")


def _error_schema(message: str) -> dict:
    """Return a minimal WARNING schema when the PowerShell script fails."""
    return {
        "report_metadata": {
            "timestamp":      datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "hostname":       "unknown",
            "os_type":        "Windows",
            "os_version":     "unknown",
            "executor":       "PowerShell_Collector_v1",
            "schema_version": "1.1",
        },
        "summary": {"overall_status": "WARNING", "alert_count": 1},
        "checks": {
            "system_resources": {
                "cpu":    {"usage_pct": None, "core_count": None, "status": "WARNING", "message": message},
                "memory": {"usage_pct": None, "used_gb": None, "total_gb": None, "status": "WARNING", "message": message},
                "disk":   {"usage_pct": None, "used_gb": None, "total_gb": None, "status": "WARNING", "message": message},
            },
            "services": [],
            "network":  {"connected": None, "status": "WARNING", "message": message},
        },
    }


def collect() -> dict:
    """
    Call collect_health.ps1 and return its output as a v1.1 schema dict.
    Called by health_check.py on Windows.
    """
    if not os.path.exists(_PS1_PATH):
        return _error_schema(f"PowerShell script not found: {_PS1_PATH}")

    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy", "Bypass",
                "-File", _PS1_PATH,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        return _error_schema("PowerShell is not available on this system.")
    except subprocess.TimeoutExpired:
        return _error_schema("PowerShell script timed out after 60 seconds.")

    if result.returncode != 0:
        return _error_schema(f"PowerShell script failed (exit {result.returncode}): {result.stderr.strip()}")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return _error_schema(f"Failed to parse PowerShell output as JSON: {e}")
