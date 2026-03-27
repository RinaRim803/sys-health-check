from checkers import run_all_checks
from reporter import build_report, save_log
from remediation import cleanup_temp_files
from email_alert import send_alert_email


# IT Ticket System integration — optional, fails gracefully if server is not running
try:
    from integrations.health_check_client import create_tickets_for_warnings
    TICKET_SYSTEM_ENABLED = True
except ImportError:
    TICKET_SYSTEM_ENABLED = False

    
def main():
    print("\nRunning system health check...\n")

    # 1. Run all checks
    results = run_all_checks()

    # 2. Build and print report
    report, overall = build_report(results)
    print(report)

    # 3. Save log
    log_path = save_log(report)
    print(f"\nLog saved -> {log_path}")

    # 4. If WARNING — clean temp files and send alert email
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
            create_tickets_for_warnings(results, report)
        else:
            print("\n  [TICKET] Skipped — integrations module not found.")

    print()


if __name__ == "__main__":
    main()