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
    used_gb  = ram.used  / (1024 ** 3)
    total_gb = ram.total / (1024 ** 3)
    percent  = ram.percent
    status = "WARNING" if percent >= 80 else "OK"
    return {"used_gb": used_gb, "total_gb": total_gb, "percent": percent, "status": status}


def check_disk():
    """Check disk usage for the root/system drive."""
    # Use C:\ on Windows, / on macOS and Linux
    path = "C:\\" if platform.system() == "Windows" else "/"
    disk     = psutil.disk_usage(path)
    used_gb  = disk.used  / (1024 ** 3)
    total_gb = disk.total / (1024 ** 3)
    percent  = disk.percent
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
    targets = {
        "Windows": ["Spooler", "wuauserv"],    # Print Spooler, Windows Update
        "Darwin":  ["com.apple.metadata.mds"], # Spotlight (macOS)
        "Linux":   ["cron", "ssh"],
    }
    os_name       = platform.system()
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
# Root cause analysis
# ─────────────────────────────────────────

def analyze_cpu():
    """
    Triggered when CPU usage is WARNING.
    Identify the top 5 processes consuming the most CPU.
    """
    lines = ["  >> Root cause analysis: top CPU-consuming processes"]
    procs = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent"]):
        try:
            procs.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # cpu_percent needs a second sample — sleep briefly then re-collect
    import time
    time.sleep(0.5)
    procs = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent"]):
        try:
            procs.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    top = sorted(procs, key=lambda p: p["cpu_percent"] or 0, reverse=True)[:5]
    for p in top:
        lines.append(f"     PID {p['pid']:<6} {p['name']:<25} {p['cpu_percent']}%")
    return lines


def analyze_ram():
    """
    Triggered when RAM usage is WARNING.
    Identify the top 5 processes consuming the most memory.
    """
    lines = ["  >> Root cause analysis: top RAM-consuming processes"]
    procs = []
    for proc in psutil.process_iter(["pid", "name", "memory_info"]):
        try:
            mem_mb = proc.info["memory_info"].rss / (1024 ** 2)
            procs.append({"pid": proc.info["pid"], "name": proc.info["name"], "mem_mb": mem_mb})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    top = sorted(procs, key=lambda p: p["mem_mb"], reverse=True)[:5]
    for p in top:
        lines.append(f"     PID {p['pid']:<6} {p['name']:<25} {p['mem_mb']:.1f} MB")
    return lines


def analyze_disk():
    """
    Triggered when disk usage is WARNING.
    Identify the top 5 largest items in the home directory.
    """
    lines = ["  >> Root cause analysis: largest items in home directory"]
    home = os.path.expanduser("~")
    sizes = []

    try:
        for entry in os.scandir(home):
            try:
                if entry.is_file(follow_symlinks=False):
                    size = entry.stat().st_size
                elif entry.is_dir(follow_symlinks=False):
                    # Walk the directory to get total size
                    size = sum(
                        f.stat().st_size
                        for f in os.scandir(entry.path)
                        if f.is_file(follow_symlinks=False)
                    )
                else:
                    continue
                sizes.append((entry.name, size))
            except (PermissionError, OSError):
                continue

        top = sorted(sizes, key=lambda x: x[1], reverse=True)[:5]
        for name, size in top:
            size_mb = size / (1024 ** 2)
            lines.append(f"     {name:<35} {size_mb:.1f} MB")
    except PermissionError:
        lines.append("     Could not access home directory.")

    return lines


def analyze_network():
    """
    Triggered when network is WARNING.
    Step through DNS → gateway → internet to locate where connectivity breaks.
    """
    lines = ["  >> Root cause analysis: network path diagnosis"]

    # Step 1 — DNS resolution
    try:
        socket.setdefaulttimeout(3)
        socket.gethostbyname("google.com")
        lines.append("     DNS resolution     : OK")
    except socket.error:
        lines.append("     DNS resolution     : FAILED  — possible DNS server issue")

    # Step 2 — Gateway reachability (best-effort via default route)
    try:
        gateways = psutil.net_if_stats()
        active = [iface for iface, stats in gateways.items() if stats.isup]
        if active:
            lines.append(f"     Active interfaces  : {', '.join(active)}")
        else:
            lines.append("     Active interfaces  : NONE — check network adapter")
    except Exception:
        lines.append("     Active interfaces  : Could not retrieve")

    # Step 3 — Internet reachability via raw socket
    for host in ["8.8.8.8", "1.1.1.1"]:
        try:
            socket.setdefaulttimeout(3)
            socket.create_connection((host, 53))
            lines.append(f"     Internet ({host})  : Reachable")
            break
        except OSError:
            lines.append(f"     Internet ({host})  : Unreachable")

    return lines


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
    if cpu["status"] == "WARNING":
        lines.extend(analyze_cpu())

    # RAM
    lines.append("[RAM]")
    lines.append(
        f"  Used    : {ram['used_gb']:.1f} GB / {ram['total_gb']:.1f} GB  "
        f"({ram['percent']}%)  [{ram['status']}]"
    )
    if ram["status"] == "WARNING":
        lines.extend(analyze_ram())

    # Disk
    lines.append("[DISK]")
    lines.append(
        f"  Used    : {disk['used_gb']:.1f} GB / {disk['total_gb']:.1f} GB  "
        f"({disk['percent']}%)  [{disk['status']}]"
    )
    if disk["status"] == "WARNING":
        lines.extend(analyze_disk())

    # Network
    lines.append("[NETWORK]")
    connected_str = "Connected" if network["connected"] else "Not connected"
    lines.append(f"  Status  : {connected_str}  [{network['status']}]")
    if network["status"] == "WARNING":
        lines.extend(analyze_network())

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
