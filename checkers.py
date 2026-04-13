import psutil
import platform
import socket
import subprocess
import json


def check_cpu():
    """Check CPU usage and core count."""
    usage  = psutil.cpu_percent(interval=1)
    count  = psutil.cpu_count()
    status = "WARNING" if usage >= 80 else "OK"
    return {"usage": usage, "count": count, "status": status}


def check_ram():
    """Check RAM usage."""
    ram      = psutil.virtual_memory()
    used_gb  = ram.used  / (1024 ** 3)
    total_gb = ram.total / (1024 ** 3)
    percent  = ram.percent
    status   = "WARNING" if percent >= 80 else "OK"
    return {"used_gb": used_gb, "total_gb": total_gb, "percent": percent, "status": status}


def check_disk():
    """Check disk usage for the root/system drive."""
    path     = "C:\\" if platform.system() == "Windows" else "/"
    disk     = psutil.disk_usage(path)
    used_gb  = disk.used  / (1024 ** 3)
    total_gb = disk.total / (1024 ** 3)
    percent  = disk.percent
    status   = "WARNING" if percent >= 85 else "OK"
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
        "Windows": ["Spooler", "wuauserv"],
        "Darwin":  ["com.apple.metadata.mds"],
        "Linux":   ["cron", "ssh"],
    }
    os_name       = platform.system()
    service_names = targets.get(os_name, [])

    results = []
    for svc in service_names:
        found = False
        for proc in psutil.process_iter(["name"]):
            try:
                if svc.lower() in proc.info["name"].lower():
                    found = True
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        results.append({
            "name":    svc,
            "running": found,
            "status":  "OK" if found else "WARNING"
        })
    return results

def get_powershell_stats():
    """Run PowerShell command to get system stats on Windows."""
    try:
        process = subprocess.run(
            ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", "./check_system.ps1"],
            capture_output=True, text=True, check=True
        )
        check =  json.loads(process.stdout)
        print(f"[*] PowerShell check results: {check}")
        return {}
    except Exception as e:
        return {"error": str(e), "status": "WARNING"}

def run_all_checks():
    
    """Run all checks and return results as a dict."""
    current_os = platform.system()
    print(f"[*] Currently detected OS: {current_os}")
    if current_os == "Windows":
        # Run PowerShell for Windows 
        return get_powershell_stats()
    else:

        # Linux나 macOS라면 기존 psutil 로직 실행
        return {
        "cpu":      check_cpu(),
        "ram":      check_ram(),
        "disk":     check_disk(),
        "network":  check_network(),
        "services": check_services(),
    }