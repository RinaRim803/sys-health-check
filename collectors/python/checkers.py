"""
collectors/python/checkers.py
System health check functions for macOS and Linux.

Thresholds and service targets are loaded from config.json —
no code changes needed to tune check behavior.
"""

import platform
import socket
import sys
import os
import psutil

# config.py is at the project root — two levels up from this file
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from config import get_thresholds, get_services, get_network_config


def check_cpu() -> dict:
    """Check CPU usage and core count."""
    cfg    = get_thresholds()
    usage  = psutil.cpu_percent(interval=1)
    count  = psutil.cpu_count()
    status = "WARNING" if usage >= cfg["cpu_warning_pct"] else "OK"
    return {"usage": usage, "count": count, "status": status}


def check_ram() -> dict:
    """Check RAM usage."""
    cfg      = get_thresholds()
    ram      = psutil.virtual_memory()
    used_gb  = ram.used  / (1024 ** 3)
    total_gb = ram.total / (1024 ** 3)
    percent  = ram.percent
    status   = "WARNING" if percent >= cfg["memory_warning_pct"] else "OK"
    return {"used_gb": used_gb, "total_gb": total_gb, "percent": percent, "status": status}


def check_disk() -> dict:
    """Check disk usage for the root/system drive."""
    cfg      = get_thresholds()
    path     = "C:\\" if platform.system() == "Windows" else "/"
    disk     = psutil.disk_usage(path)
    used_gb  = disk.used  / (1024 ** 3)
    total_gb = disk.total / (1024 ** 3)
    percent  = disk.percent
    status   = "WARNING" if percent >= cfg["disk_warning_pct"] else "OK"
    return {"used_gb": used_gb, "total_gb": total_gb, "percent": percent, "status": status}


def check_network() -> dict:
    """Check basic network connectivity by resolving a public DNS address."""
    cfg = get_network_config()
    try:
        socket.setdefaulttimeout(cfg["dns_timeout_sec"])
        socket.gethostbyname(cfg["dns_check_host"])
        return {"connected": True, "status": "OK"}
    except socket.error:
        return {"connected": False, "status": "WARNING"}


def check_services() -> dict:
    """Check whether key system services are running."""
    cfg         = get_services()
    os_name     = platform.system()
    svc_targets = cfg.get(os_name, [])

    results = []
    for svc in svc_targets:
        found = any(
            svc.lower() in (proc.info.get("name") or "").lower()
            for proc in psutil.process_iter(["name"])
        )
        results.append({
            "name":    svc,
            "running": found,
            "status":  "OK" if found else "WARNING",
        })
    return results


def run_all_checks() -> dict:
    """Run all checks and return results as a dict."""
    return {
        "cpu":      check_cpu(),
        "ram":      check_ram(),
        "disk":     check_disk(),
        "network":  check_network(),
        "services": check_services(),
    }