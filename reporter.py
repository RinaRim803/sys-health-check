import os
import datetime
import platform

from utils import separator, timestamp
from analyzers import run_analysis


def _format_cpu(cpu: dict) -> list:
    lines = [
        "[CPU]",
        f"  Usage   : {cpu['usage']}%  ({cpu['count']} cores)  [{cpu['status']}]",
    ]
    if cpu["status"] == "WARNING":
        lines.extend(run_analysis("cpu"))
    return lines


def _format_ram(ram: dict) -> list:
    lines = [
        "[RAM]",
        f"  Used    : {ram['used_gb']:.1f} GB / {ram['total_gb']:.1f} GB  "
        f"({ram['percent']}%)  [{ram['status']}]",
    ]
    if ram["status"] == "WARNING":
        lines.extend(run_analysis("ram"))
    return lines


def _format_disk(disk: dict) -> list:
    lines = [
        "[DISK]",
        f"  Used    : {disk['used_gb']:.1f} GB / {disk['total_gb']:.1f} GB  "
        f"({disk['percent']}%)  [{disk['status']}]",
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


def _format_services(services: list) -> list:
    lines = ["[SERVICES]"]
    if services:
        for svc in services:
            state = "Running" if svc["running"] else "Not found"
            lines.append(f"  {svc['name']:<20} {state}  [{svc['status']}]")
    else:
        lines.append("  No services configured for this OS.")
    return lines


def _get_overall(results: dict) -> str:
    """Determine overall status from all check results."""
    all_statuses = (
        [
            results["cpu"]["status"],
            results["ram"]["status"],
            results["disk"]["status"],
            results["network"]["status"],
        ]
        + [s["status"] for s in results["services"]]
    )
    return "WARNING - check items above" if "WARNING" in all_statuses else "ALL SYSTEMS OK"


def build_report(results: dict) -> tuple[str, str]:
    """
    Build a formatted report string from check results.
    Returns (report_string, overall_status).
    """
    lines = []
    lines.append(separator())
    lines.append("  SYSTEM HEALTH CHECK REPORT")
    lines.append(f"  {timestamp()}")
    lines.append(f"  OS : {platform.system()} {platform.release()}")
    lines.append(separator())

    lines.extend(_format_cpu(results["cpu"]))
    lines.extend(_format_ram(results["ram"]))
    lines.extend(_format_disk(results["disk"]))
    lines.extend(_format_network(results["network"]))
    lines.extend(_format_services(results["services"]))

    lines.append(separator())
    overall = _get_overall(results)
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