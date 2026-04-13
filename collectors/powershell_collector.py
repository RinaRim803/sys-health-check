"""
collectors/powershell_collector.py
PowerShell collector for Windows.

Calls scripts/collect_health.ps1 via subprocess,
reads its stdout as JSON, and returns a v1.1 schema-compliant dict.

The .ps1 script owns all data collection logic.
This module owns the subprocess call and error handling only.

Public interface:
    collect() -> dict   # returns v1.1 schema-compliant dict
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

# Path to the PowerShell script — relative to project root
_PS1_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts", "collect_health.ps1")


def _error_schema(message: str) -> dict:
    """
    Return a minimal v1.1 schema dict when the PowerShell script fails.
    Marked as WARNING so health_check.py still sends an alert.
    """
    return {
        "report_metadata": {
            "timestamp":      datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "hostname":       "unknown",
            "os_type":        "Windows",
            "os_version":     "unknown",
            "executor":       "PowerShell_Collector_v1",
            "schema_version": "1.1",
        },
        "summary": {
            "overall_status": "WARNING",
            "alert_count":    1,
        },
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

    Execution policy is set to Bypass per-process — does not change system policy.
    """
    ps1_path = os.path.normpath(_PS1_PATH)

    if not os.path.exists(ps1_path):
        return _error_schema(f"PowerShell script not found: {ps1_path}")

    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy", "Bypass",   # per-process only
                "-File", ps1_path,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        return _error_schema("PowerShell is not available on this system.")
    except subprocess.TimeoutExpired:
        return _error_schema("PowerShell script timed out after 60 seconds.")

    # Check stderr for script-level errors
    if result.returncode != 0:
        stderr = result.stderr.strip()
        return _error_schema(f"PowerShell script failed (exit {result.returncode}): {stderr}")

    # Parse stdout as JSON
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return _error_schema(f"Failed to parse PowerShell output as JSON: {e}")

    return data
