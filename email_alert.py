import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

from utils import timestamp

# Load credentials from .env
load_dotenv()

SENDER_EMAIL    = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL  = os.getenv("RECEIVER_EMAIL")


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
            f"  Admin privileges : {'Yes' if cleanup_summary.get('admin') else 'No'}",
            f"  Items deleted    : {cleanup_summary['deleted']}",
            f"  Locked (in use)  : {cleanup_summary.get('locked', 0)} - skipped safely",
            f"  Space freed      : {cleanup_summary['freed_mb']:.1f} MB",
            f"  Errors skipped   : {cleanup_summary['errors']}",
        ]

    return "\n".join(lines)


def send_alert_email(report: str, cleanup_summary: dict = None):
    """
    Send a Gmail alert when OVERALL status is WARNING.
    Uses EmailMessage (Python 3 modern API) — handles encoding natively.
    Credentials are loaded from .env — never hardcoded.
    """
    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL]):
        print("  [EMAIL] Skipped — missing credentials in .env")
        return

    msg = EmailMessage()
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECEIVER_EMAIL
    msg["Subject"] = f"[WARNING] System Health Alert - {timestamp()}"
    msg.set_content(_build_email_body(report, cleanup_summary))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print("  [EMAIL] Alert sent successfully.")
    except smtplib.SMTPAuthenticationError:
        print("  [EMAIL] Authentication failed — check .env credentials.")
    except Exception as e:
        print(f"  [EMAIL] Failed to send: {e}")