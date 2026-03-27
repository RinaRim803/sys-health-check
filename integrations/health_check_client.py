"""
integrations/health_check_client.py
IT Ticket System integration for sys-health-check.

Single responsibility: convert health check results into ticket payloads
and send them to the IT Ticket System API.

Public interface:
    create_tickets_for_warnings(results, report)
        Called from health_check.py when overall status is WARNING.
        Creates one ticket per WARNING item detected.
"""

import requests

TICKET_API_URL = "http://localhost:5000/api/tickets"

# Maps check key -> (alert_type, title, description template)
_ALERT_CONFIG = {
    "cpu": (
        "cpu",
        "High CPU Usage Detected",
        "CPU usage reached {value}% (threshold: {threshold}%).\n\nDiagnostic Report:\n{details}",
    ),
    "ram": (
        "memory",
        "High Memory Usage Detected",
        "Memory usage reached {value}% (threshold: {threshold}%).\n\nDiagnostic Report:\n{details}",
    ),
    "disk": (
        "disk",
        "Low Disk Space Detected",
        "Disk usage reached {value}% (threshold: {threshold}%).\n\nDiagnostic Report:\n{details}",
    ),
    "network": (
        "service_down",
        "Network Connectivity Lost",
        "Network connectivity check failed.\n\nDiagnostic Report:\n{details}",
    ),
}

# Maps check key -> value field to extract from results
_VALUE_FIELDS = {
    "cpu":     ("usage",   80),
    "ram":     ("percent", 80),
    "disk":    ("percent", 85),
    "network": (None,      None),
}


def _send_ticket(title: str, description: str) -> dict | None:
    """
    POST a single ticket to the IT Ticket System API.
    Returns the created ticket dict, or None on failure.
    """
    payload = {
        "title":       title,
        "description": description,
        "source":      "sys-health-check",
    }
    try:
        response = requests.post(TICKET_API_URL, json=payload, timeout=5)
        response.raise_for_status()
        ticket = response.json()
        print(f"  [TICKET] #{ticket['id']} created — {ticket['priority']} | {ticket['category']} | {title}")
        return ticket
    except requests.exceptions.ConnectionError:
        print("  [TICKET] Skipped — IT Ticket System server is not running.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"  [TICKET] Failed — {e}")
        return None


def create_tickets_for_warnings(results: dict, report: str):
    """
    Create one ticket per WARNING item in the health check results.

    Called from health_check.py:
        from integrations.health_check_client import create_tickets_for_warnings
        create_tickets_for_warnings(results, report)

    Args:
        results : dict returned by run_all_checks()
        report  : full formatted report string — attached to each ticket description
    """
    # CPU / RAM / Disk / Network
    for key, (alert_type, title, desc_template) in _ALERT_CONFIG.items():
        result = results.get(key, {})
        if result.get("status") != "WARNING":
            continue

        value_field, threshold = _VALUE_FIELDS[key]
        value = result.get(value_field, "N/A") if value_field else "N/A"

        description = desc_template.format(
            value=value,
            threshold=threshold or "N/A",
            details=report,
        )
        _send_ticket(title, description)

    # Services — each downed service becomes its own ticket
    for svc in results.get("services", []):
        if svc.get("status") != "WARNING":
            continue
        title = "Service Unavailable"
        description = (
            f"Service '{svc['name']}' was not found running on this system.\n\n"
            f"Diagnostic Report:\n{report}"
        )
        _send_ticket(title, description)