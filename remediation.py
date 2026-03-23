import os
import platform
import shutil
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

from utils import timestamp

# Load credentials from .env
load_dotenv()

SENDER_EMAIL    = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL  = os.getenv("RECEIVER_EMAIL")


# ─────────────────────────────────────────
# Temp file cleanup
# ─────────────────────────────────────────

def _get_temp_paths() -> list:
    """Return OS-specific temp directory paths."""
    if platform.system() == "Windows":
        return [
            os.environ.get("TEMP", ""),
            os.environ.get("TMP", ""),
            os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Temp"),
        ]
    # macOS and Linux
    return ["/tmp", os.path.join(os.path.expanduser("~"), ".cache")]


def _get_entry_size(entry) -> int:
    """Return the size of a file or directory entry in bytes."""
    if entry.is_file(follow_symlinks=False):
        return entry.stat().st_size
    if entry.is_dir(follow_symlinks=False):
        total = 0
        try:
            for f in os.scandir(entry.path):
                if f.is_file():
                    total += f.stat().st_size
        except (PermissionError, OSError):
            pass
        return total
    return 0


def cleanup_temp_files() -> dict:
    """
    Delete temporary files from OS temp directories.
    Returns a summary: items deleted, MB freed, errors skipped.
    """
    total_deleted = 0
    total_freed   = 0
    errors        = 0

    for temp_dir in _get_temp_paths():
        if not temp_dir or not os.path.exists(temp_dir):
            continue

        for entry in os.scandir(temp_dir):
            try:
                size = _get_entry_size(entry)
                if entry.is_file(follow_symlinks=False):
                    os.remove(entry.path)
                elif entry.is_dir(follow_symlinks=False):
                    shutil.rmtree(entry.path, ignore_errors=True)
                else:
                    continue
                total_deleted += 1
                total_freed   += size
            except (PermissionError, OSError):
                errors += 1

    return {
        "deleted":  total_deleted,
        "freed_mb": total_freed / (1024 ** 2),
        "errors":   errors,
    }


# ─────────────────────────────────────────
# Email alert
# ─────────────────────────────────────────

def _build_email_body(report: str, cleanup_summary: dict = None) -> str:
    """Compose the email body from the report and optional cleanup summary."""
    lines = [
        "A system health check has detected one or more WARNING conditions.",
        "",
        "=" * 40,
        report,
        "=" * 40,
    ]

    if cleanup_summary:
        lines += [
            "",
            "TEMP FILE CLEANUP PERFORMED:",
            f"  Items deleted : {cleanup_summary['deleted']}",
            f"  Space freed   : {cleanup_summary['freed_mb']:.1f} MB",
            f"  Errors skipped: {cleanup_summary['errors']}",
        ]

    return "\n".join(lines)


def send_alert_email(report: str, cleanup_summary: dict = None):
    """
    Send a Gmail alert when OVERALL status is WARNING.
    Credentials are loaded from .env — never hardcoded.
    """
    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL]):
        print("  [EMAIL] Skipped — missing credentials in .env")
        return

    msg = MIMEMultipart()
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECEIVER_EMAIL
    msg["Subject"] = f"[WARNING] System Health Alert — {timestamp()}"
    msg.attach(MIMEText(_build_email_body(report, cleanup_summary), "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        print("  [EMAIL] Alert sent successfully.")
    except smtplib.SMTPAuthenticationError:
        print("  [EMAIL] Authentication failed — check .env credentials.")
    except Exception as e:
        print(f"  [EMAIL] Failed to send: {e}")