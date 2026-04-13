import sys
import platform
from reporter import build_report, save_log
from remediation import cleanup_temp_files
from email_alert import send_alert_email

# IT Ticket System integration — optional, fails gracefully if server is not running
try:
    from integrations.health_check_client import create_tickets_for_warnings
    TICKET_SYSTEM_ENABLED = True
except ImportError:
    TICKET_SYSTEM_ENABLED = False


def get_collector():
    """
    Select the appropriate collector based on the current OS.
    Returns the collect() function from the correct collector module.

    Windows → powershell_collector  (calls collect_health.ps1)
    macOS / Linux → python_collector (calls checkers.py via psutil)
    """
    os_name = platform.system()
    if os_name == "Windows":
        from collectors.powershell_collector import collect
        print("  [COLLECTOR] Windows detected — using PowerShell collector\n")
    else:
        from collectors.python_collector import collect
        print(f"  [COLLECTOR] {os_name} detected — using Python collector\n")
    return collect


def main():
    print("\nRunning system health check...\n")

    # 1. Select and run the correct collector
    collect = get_collector()
    data    = collect()   # returns v1.1 schema dict

    # 2. Build and print report
    report, overall = build_report(data)
    print(report)

    # 3. Save log
    log_path = save_log(report)
    print(f"\nLog saved -> {log_path}")

    # 4. If WARNING — clean temp files, send alert email, and create tickets
    if overall.startswith("WARNING"):
        print("\nOVERALL WARNING detected — running cleanup and sending alert...\n")

        print("  [CLEANUP] Removing temporary files...")
        cleanup_summary = cleanup_temp_files()
        print(
            f"  [CLEANUP] Done — {cleanup_summary['deleted']} items deleted, "
            f"{cleanup_summary['freed_mb']:.1f} MB freed, "
            f"{cleanup_summary['locked']} locked, "
            f"{cleanup_summary['errors']} errors."
        )

        send_alert_email(report, cleanup_summary)

        # Auto-create tickets in IT Ticket System for each WARNING item
        if TICKET_SYSTEM_ENABLED:
            print("\n  [TICKET] Creating tickets for WARNING items...")
            # Pass v1.1 schema checks dict — client reads status from schema fields
            create_tickets_for_warnings(data["checks"], report)
        else:
            print("\n  [TICKET] Skipped — integrations module not found.")

    print()


if __name__ == "__main__":
    main()