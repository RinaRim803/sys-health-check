"""
reporter.py
Builds a formatted report string from v1.1 schema data
and saves it as a timestamped log file.

Reads from the canonical schema — works identically regardless of
whether data came from python_collector or powershell_collector.
"""

import os
import datetime

from utils import separator, timestamp
from analyzers import run_analysis


# ── Section formatters ────────────────────────────────────────────────────────

def _format_cpu(cpu: dict) -> list:
    usage = cpu["usage_pct"]
    cores = cpu["core_count"]
    lines = [
        "[CPU]",
        f"  Usage   : {usage}%  ({cores} cores)  [{cpu['status']}]",
    ]
    if cpu["status"] == "WARNING":
        lines.extend(run_analysis("cpu"))
    return lines


def _format_memory(memory: dict) -> list:
    lines = [
        "[RAM]",
        f"  Used    : {memory['used_gb']} GB / {memory['total_gb']} GB  "
        f"({memory['usage_pct']}%)  [{memory['status']}]",
    ]
    if memory["status"] == "WARNING":
        lines.extend(run_analysis("ram"))
    return lines


def _format_disk(disk: dict) -> list:
    lines = [
        "[DISK]",
        f"  Used    : {disk['used_gb']} GB / {disk['total_gb']} GB  "
        f"({disk['usage_pct']}%)  [{disk['status']}]",
    ]
    if disk["status"] == "WARNING":
        lines.extend(run_analysis("disk"))
    return lines


def _format_network(network: dict) -> list:
    connected_str = "Connected" if network["connected"] else "Not connected"
    lines = [
        "[NETWORK]",
        f"  Status  : {connected_str}  [{network['status']}]",
    ]
    if network["status"] == "WARNING":
        lines.extend(run_analysis("network"))
    return lines


def _format_services(services: list, os_type: str) -> list:
    lines = [f"[SERVICES]  ({os_type})"]
    if services:
        for svc in services:
            state = "Running" if svc["running"] else "Not found"
            lines.append(f"  {svc['name']:<20} {state}  [{svc['status']}]")
    else:
        lines.append("  No services configured for this OS.")
    return lines


def _get_overall(data: dict) -> str:
    return (
        "WARNING - check items above"
        if data["summary"]["overall_status"] == "WARNING"
        else "ALL SYSTEMS OK"
    )


# ── Public interface ──────────────────────────────────────────────────────────

def build_report(data: dict) -> tuple[str, str]:
    """
    Build a formatted report string from v1.1 schema data.
    Returns (report_string, overall_status).

    Args:
        data : v1.1 schema dict — from python_collector or powershell_collector
    """
    meta   = data["report_metadata"]
    checks = data["checks"]
    res    = checks["system_resources"]

    lines = []
    lines.append(separator())
    lines.append("  SYSTEM HEALTH CHECK REPORT")
    lines.append(f"  {timestamp()}")
    lines.append(f"  OS       : {meta['os_type']} {meta.get('os_version', '')}")
    lines.append(f"  Executor : {meta['executor']}")
    lines.append(f"  Host     : {meta['hostname']}")
    lines.append(separator())

    lines.extend(_format_cpu(res["cpu"]))
    lines.extend(_format_memory(res["memory"]))
    lines.extend(_format_disk(res["disk"]))
    lines.extend(_format_network(checks["network"]))
    lines.extend(_format_services(checks["services"], meta["os_type"]))

    lines.append(separator())
    overall = _get_overall(data)
    lines.append(f"  OVERALL : {overall}")
    lines.append(separator())

    return "\n".join(lines), overall


def save_log(report: str) -> str:
    """Save the report to a timestamped log file in a 'logs' folder."""
    log_dir  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    filename = datetime.datetime.now().strftime("health_%Y%m%d_%H%M%S.log")
    filepath = os.path.join(log_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)
    return filepath