import psutil
import platform
import datetime
import socket
import os


# ─────────────────────────────────────────
# Helper
# ─────────────────────────────────────────

def separator():
    return "-" * 40


def timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─────────────────────────────────────────
# Check functions
# ─────────────────────────────────────────

def check_cpu():
    """Check CPU usage and core count."""
    usage = psutil.cpu_percent(interval=1)
    count = psutil.cpu_count()
    status = "WARNING" if usage >= 80 else "OK"
    return {"usage": usage, "count": count, "status": status}


def check_ram():
    """Check RAM usage."""
    ram = psutil.virtual_memory()
    used_gb = ram.used / (1024 ** 3)
    total_gb = ram.total / (1024 ** 3)
    percent = ram.percent
    status = "WARNING" if percent >= 80 else "OK"
    return {"used_gb": used_gb, "total_gb": total_gb, "percent": percent, "status": status}


def check_disk():
    """Check disk usage for the root/system drive."""
    # Use C:\ on Windows, / on macOS and Linux
    path = "C:\\" if platform.system() == "Windows" else "/"
    disk = psutil.disk_usage(path)
    used_gb = disk.used / (1024 ** 3)
    total_gb = disk.total / (1024 ** 3)
    percent = disk.percent
    status = "WARNING" if percent >= 85 else "OK"
    return {"used_gb": used_gb, "total_gb": total_gb, "percent": percent, "status": status}


def check_network():
    """Check basic network connectivity by resolving a public DNS address."""
    try:
        socket.setdefaulttimeout(3)
        socket.gethostbyname("google.com")
        return {"connected": True, "status": "OK"}
    except socket.error:
        return {"connected": False, "status": "WARNING"}


def check_services():
    """Check whether key system services are running."""
    # Services to monitor — adjust names per OS if needed
    targets = {
        "Windows": ["Spooler", "wuauserv"],    # Print Spooler, Windows Update
        "Darwin":  ["com.apple.metadata.mds"], # Spotlight (macOS)
        "Linux":   ["cron", "ssh"],
    }
    os_name = platform.system()
    service_names = targets.get(os_name, [])

    results = []
    for svc in service_names:
        found = False
        for proc in psutil.process_iter(["name"]):
            if svc.lower() in proc.info["name"].lower():
                found = True
                break
        results.append({"name": svc, "running": found, "status": "OK" if found else "WARNING"})
    return results


# ─────────────────────────────────────────
# Report builder
# ─────────────────────────────────────────

def build_report(cpu, ram, disk, network, services):
    """Compile all check results into a formatted report string."""
    lines = []
    lines.append(separator())
    lines.append("  SYSTEM HEALTH CHECK REPORT")
    lines.append(f"  {timestamp()}")
    lines.append(f"  OS : {platform.system()} {platform.release()}")
    lines.append(separator())

    # CPU
    lines.append("[CPU]")
    lines.append(f"  Usage   : {cpu['usage']}%  ({cpu['count']} cores)  [{cpu['status']}]")

    # RAM
    lines.append("[RAM]")
    lines.append(
        f"  Used    : {ram['used_gb']:.1f} GB / {ram['total_gb']:.1f} GB  "
        f"({ram['percent']}%)  [{ram['status']}]"
    )

    # Disk
    lines.append("[DISK]")
    lines.append(
        f"  Used    : {disk['used_gb']:.1f} GB / {disk['total_gb']:.1f} GB  "
        f"({disk['percent']}%)  [{disk['status']}]"
    )

    # Network
    lines.append("[NETWORK]")
    connected_str = "Connected" if network["connected"] else "Not connected"
    lines.append(f"  Status  : {connected_str}  [{network['status']}]")

    # Services
    lines.append("[SERVICES]")
    if services:
        for svc in services:
            state = "Running" if svc["running"] else "Not found"
            lines.append(f"  {svc['name']:<20} {state}  [{svc['status']}]")
    else:
        lines.append("  No services configured for this OS.")

    lines.append(separator())

    # Overall status
    all_statuses = (
        [cpu["status"], ram["status"], disk["status"], network["status"]]
        + [s["status"] for s in services]
    )
    overall = "WARNING — check items above" if "WARNING" in all_statuses else "ALL SYSTEMS OK"
    lines.append(f"  OVERALL : {overall}")
    lines.append(separator())

    return "\n".join(lines)


# ─────────────────────────────────────────
# Log writer
# ─────────────────────────────────────────

def save_log(report: str):
    """Save the report to a timestamped log file in a 'logs' folder."""
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)

    filename = datetime.datetime.now().strftime("health_%Y%m%d_%H%M%S.log")
    filepath = os.path.join(log_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)

    return filepath


# ─────────────────────────────────────────
# Main
# ─────────────────────────────────────────

def main():
    print("\nRunning system health check...\n")

    cpu      = check_cpu()
    ram      = check_ram()
    disk     = check_disk()
    network  = check_network()
    services = check_services()

    report = build_report(cpu, ram, disk, network, services)

    # Print to console
    print(report)

    # Save to log file
    log_path = save_log(report)
    print(f"\nLog saved → {log_path}\n")


if __name__ == "__main__":
    main()
