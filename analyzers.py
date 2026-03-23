import time
import os
import socket
import psutil


def analyze_cpu():
    """Identify the top 5 processes consuming the most CPU."""
    lines = ["  >> Root cause analysis: top CPU-consuming processes"]

    # Brief pause to let cpu_percent collect a meaningful sample
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
    """Identify the top 5 processes consuming the most memory."""
    lines = ["  >> Root cause analysis: top RAM-consuming processes"]
    procs = []

    for proc in psutil.process_iter(["pid", "name", "memory_info"]):
        try:
            mem_mb = proc.info["memory_info"].rss / (1024 ** 2)
            procs.append({
                "pid":    proc.info["pid"],
                "name":   proc.info["name"],
                "mem_mb": mem_mb,
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    top = sorted(procs, key=lambda p: p["mem_mb"], reverse=True)[:5]
    for p in top:
        lines.append(f"     PID {p['pid']:<6} {p['name']:<25} {p['mem_mb']:.1f} MB")
    return lines


def analyze_disk():
    """Identify the top 5 largest items in the home directory."""
    lines = ["  >> Root cause analysis: largest items in home directory"]
    home  = os.path.expanduser("~")
    sizes = []

    try:
        for entry in os.scandir(home):
            try:
                if entry.is_file(follow_symlinks=False):
                    size = entry.stat().st_size
                elif entry.is_dir(follow_symlinks=False):
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
            lines.append(f"     {name:<35} {size / (1024 ** 2):.1f} MB")
    except PermissionError:
        lines.append("     Could not access home directory.")

    return lines


def analyze_network():
    """Step through DNS → interfaces → internet to locate where connectivity breaks."""
    lines = ["  >> Root cause analysis: network path diagnosis"]

    # Step 1 — DNS resolution
    try:
        socket.setdefaulttimeout(3)
        socket.gethostbyname("google.com")
        lines.append("     DNS resolution     : OK")
    except socket.error:
        lines.append("     DNS resolution     : FAILED — possible DNS server issue")

    # Step 2 — Active network interfaces
    try:
        active = [iface for iface, stats in psutil.net_if_stats().items() if stats.isup]
        label  = ", ".join(active) if active else "NONE — check network adapter"
        lines.append(f"     Active interfaces  : {label}")
    except Exception:
        lines.append("     Active interfaces  : Could not retrieve")

    # Step 3 — Internet reachability via raw socket
    for host in ["8.8.8.8", "1.1.1.1"]:
        try:
            socket.create_connection((host, 53), timeout=3)
            lines.append(f"     Internet ({host})  : Reachable")
            break
        except OSError:
            lines.append(f"     Internet ({host})  : Unreachable")

    return lines


# Mapping: check key → analyzer function
ANALYZERS = {
    "cpu":     analyze_cpu,
    "ram":     analyze_ram,
    "disk":    analyze_disk,
    "network": analyze_network,
}


def run_analysis(check_key: str) -> list:
    """Run the appropriate analyzer for a given check key if one exists."""
    analyzer = ANALYZERS.get(check_key)
    return analyzer() if analyzer else []