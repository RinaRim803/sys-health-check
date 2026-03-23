from checkers import run_all_checks
from reporter import build_report, save_log
from remediation import cleanup_temp_files, send_alert_email


def main():
    print("\nRunning system health check...\n")

    # 1. Run all checks
    results = run_all_checks()

    # 2. Build and print report
    report, overall = build_report(results)
    print(report)

    # 3. Save log
    log_path = save_log(report)
    print(f"\nLog saved → {log_path}")

    # 4. If WARNING — clean temp files and send alert email
    if overall.startswith("WARNING"):
        print("\nOVERALL WARNING detected — running cleanup and sending alert...\n")

        print("  [CLEANUP] Removing temporary files...")
        cleanup_summary = cleanup_temp_files()
        print(
            f"  [CLEANUP] Done — {cleanup_summary['deleted']} items deleted, "
            f"{cleanup_summary['freed_mb']:.1f} MB freed, "
            f"{cleanup_summary['errors']} errors skipped."
        )

        send_alert_email(report, cleanup_summary)

    print()


if __name__ == "__main__":
    main()