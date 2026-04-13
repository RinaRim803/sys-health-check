"""
config.py
Central configuration loader for sys-health-check.

Reads config.json once and exposes typed accessors.
Used by both the Python collector and health_check.py.

Usage:
    from config import get_thresholds, get_services, get_network_config
"""

import json
import os

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
_config: dict = {}


def _get_config() -> dict:
    global _config
    if not _config:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            _config = json.load(f)
    return _config


def get_thresholds() -> dict:
    """
    Returns warning thresholds.
    Example: { "cpu_warning_pct": 80, "memory_warning_pct": 80, "disk_warning_pct": 85 }
    """
    return _get_config()["thresholds"]


def get_services() -> dict:
    """
    Returns OS-specific service names to monitor.
    Example: { "Windows": ["Spooler", "wuauserv"], "Linux": ["cron", "ssh"] }
    """
    return _get_config()["services"]


def get_network_config() -> dict:
    """
    Returns network check settings.
    Example: { "dns_check_host": "google.com", "dns_timeout_sec": 3 }
    """
    return _get_config()["network"]