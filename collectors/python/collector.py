"""
collectors/python/collector.py
Python collector for macOS and Linux.

Calls checkers.py (sibling in this package) and converts the output
into the canonical v1.1 JSON schema.

checkers.py is NOT modified — this module owns the translation layer only.

Public interface:
    collect() -> dict   # returns v1.1 schema-compliant dict
"""

import platform
import socket
import sys
import os
from datetime import datetime, timezone

# checkers.py is a sibling in the same package (collectors/python/)
from collectors.python.checkers import run_all_checks


# ── Thresholds (mirrors checkers.py logic) ────────────────────────────────────
_CPU_WARN  = 80
_MEM_WARN  = 80
_DISK_WARN = 85


def _status(condition: bool) -> str:
    return "WARNING" if condition else "OK"


def _build_metadata() -> dict:
    os_name = platform.system()
    return {
        "timestamp":      datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hostname":       socket.gethostname(),
        "os_type":        os_name,
        "os_version":     f"{os_name} {platform.release()}",
        "executor":       "Python_Collector_v1",
        "schema_version": "1.1",
    }


def _build_cpu(raw: dict) -> dict:
    usage  = raw["usage"]
    status = _status(usage >= _CPU_WARN)
    return {
        "usage_pct":  round(usage, 1),
        "core_count": raw["count"],
        "status":     status,
        "message":    f"CPU at {usage}% — above threshold" if status == "WARNING" else "Normal",
    }


def _build_memory(raw: dict) -> dict:
    pct    = raw["percent"]
    status = _status(pct >= _MEM_WARN)
    return {
        "usage_pct": round(pct, 1),
        "used_gb":   round(raw["used_gb"], 1),
        "total_gb":  round(raw["total_gb"], 1),
        "status":    status,
        "message":   f"Memory at {pct}% — above threshold" if status == "WARNING" else "Normal",
    }


def _build_disk(raw: dict) -> dict:
    pct    = raw["percent"]
    status = _status(pct >= _DISK_WARN)
    return {
        "usage_pct": round(pct, 1),
        "used_gb":   round(raw["used_gb"], 1),
        "total_gb":  round(raw["total_gb"], 1),
        "status":    status,
        "message":   f"Disk at {pct}% — above threshold" if status == "WARNING" else "Normal",
    }


def _build_services(raw: list) -> list:
    result = []
    for svc in raw:
        entry = {
            "name":    svc["name"],
            "running": svc["running"],
            "status":  svc["status"],
        }
        if not svc["running"]:
            entry["message"] = f"Service '{svc['name']}' not found"
        result.append(entry)
    return result


def _build_network(raw: dict) -> dict:
    connected = raw["connected"]
    return {
        "connected": connected,
        "status":    raw["status"],
        "message":   "No internet connectivity" if not connected else "Connected",
    }


def _build_summary(checks: dict) -> dict:
    statuses = [
        checks["system_resources"]["cpu"]["status"],
        checks["system_resources"]["memory"]["status"],
        checks["system_resources"]["disk"]["status"],
        checks["network"]["status"],
    ] + [svc["status"] for svc in checks["services"]]

    alert_count = statuses.count("WARNING")
    return {
        "overall_status": "WARNING" if alert_count > 0 else "OK",
        "alert_count":    alert_count,
    }


def collect() -> dict:
    """
    Run all checks via checkers.py and return a v1.1 schema-compliant dict.
    Called by health_check.py on macOS and Linux.
    """
    raw = run_all_checks()

    checks = {
        "system_resources": {
            "cpu":    _build_cpu(raw["cpu"]),
            "memory": _build_memory(raw["ram"]),
            "disk":   _build_disk(raw["disk"]),
        },
        "services": _build_services(raw["services"]),
        "network":  _build_network(raw["network"]),
    }

    return {
        "report_metadata": _build_metadata(),
        "summary":         _build_summary(checks),
        "checks":          checks,
    }
