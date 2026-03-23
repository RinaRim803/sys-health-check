import os
import platform
import shutil
import smtplib
import ctypes
import subprocess
import sys
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
# Admin privilege check
# ─────────────────────────────────────────

def is_admin() -> bool:
    """Return True if the current process has administrator privileges."""
    try:
        if platform.system() == "Windows":
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            # macOS / Linux — check if running as root
            return os.geteuid() == 0
    except Exception:
        return False


def relaunch_as_admin():
    """
    Relaunch the current script with administrator privileges.
    On Windows: triggers a UAC elevation prompt.
    On macOS/Linux: relaunches with sudo.
    """
    if platform.system() == "Windows":
        # ShellExecute with 'runas' triggers the UAC prompt
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
    else:
        subprocess.run(["sudo", sys.executable] + sys.argv)


# ─────────────────────────────────────────
# Temp file cleanup
# ─────────────────────────────────────────

def _get_temp_paths(admin: bool) -> list:
    """
    Return OS-specific temp directory paths based on privilege level.
    - Admin    : user temp + system temp
    - Non-admin: user temp only (avoids PermissionError on system dirs)
    """
    if platform.system() == "Windows":
        user_temp = list({
            os.environ.get("TEMP", ""),
            os.environ.get("TMP", ""),
        })
        system_temp = [
            os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "Temp")
        ]
        return user_temp + system_temp if admin else user_temp
    else:
        # macOS / Linux
        user_paths   = [os.path.join(os.path.expanduser("~"), ".cache")]
        system_paths = ["/tmp"]
        return user_paths + system_paths if admin else user_paths


def _get_entry_size(entry) -> int:
    """Return the size of a file or directory entry in bytes (recursive for dirs)."""
    if entry.is_file(follow_symlinks=False):
        return entry.stat().st_size
    if entry.is_dir(follow_symlinks=False):
        total = 0
        try:
            for f in os.scandir(entry.path):
                try:
                    if f.is_file():
                        total += f.stat().st_size
                except (PermissionError, OSError):
                    pass
        except (PermissionError, OSError):
            pass
        return total
    return 0


def _is_locked_error(e: OSError) -> bool:
    """Return True if the error is a Windows file-lock error (WinError 32)."""
    return isinstance(e, OSError) and getattr(e, "winerror", None) == 32


def _clean_directory(temp_dir: str) -> tuple:
    """
    Clean a single temp directory.
    Returns (deleted, freed_bytes, locked, errors) for that directory.
    - locked : file in use by another process (WinError 32) — skipped safely
    - errors : unexpected failures
    """
    deleted = 0
    freed   = 0
    locked  = 0
    errors  = 0

    try:
        entries = list(os.scandir(temp_dir))
    except (PermissionError, OSError):
        return 0, 0, 0, 1

    for entry in entries:
        try:
            size = _get_entry_size(entry)
            if entry.is_file(follow_symlinks=False):
                os.remove(entry.path)
            elif entry.is_dir(follow_symlinks=False):
                shutil.rmtree(entry.path, ignore_errors=True)
            else:
                continue
            deleted += 1
            freed   += size
        except OSError as e:
            if _is_locked_error(e):
                # File is in use by another process — safe to skip
                locked += 1
            else:
                errors += 1

    return deleted, freed, locked, errors


def cleanup_temp_files() -> dict:
    """
    Delete temporary files from OS temp directories.

    Behavior:
    - Admin privilege detected    : cleans user temp + system temp
    - No admin privilege detected : cleans user temp only, prompts to relaunch as admin
                                    for system temp cleanup

    Returns a summary: items deleted, MB freed, errors skipped, admin status.
    """
    admin         = is_admin()
    temp_paths    = _get_temp_paths(admin)
    total_deleted = 0
    total_freed   = 0
    total_locked  = 0
    errors        = 0

    print(f"  [CLEANUP] Admin privileges : {'Yes' if admin else 'No'}")

    for temp_dir in temp_paths:
        if not temp_dir or not os.path.exists(temp_dir):
            continue
        deleted, freed, locked, errs = _clean_directory(temp_dir)
        total_deleted += deleted
        total_freed   += freed
        total_locked  += locked
        errors        += errs
        print(
            f"  [CLEANUP] {temp_dir:<45} "
            f"{deleted} deleted, {locked} locked (in use), "
            f"{freed / (1024**2):.1f} MB freed"
        )

    # If not admin on Windows, offer to relaunch with elevated privileges
    if not admin and platform.system() == "Windows":
        print()
        print("  [CLEANUP] System temp (C:\\Windows\\Temp) was skipped — requires admin privileges.")
        answer = input("  [CLEANUP] Relaunch as administrator to clean system temp? [y/N]: ").strip().lower()
        if answer == "y":
            print("  [CLEANUP] Relaunching with admin privileges...")
            relaunch_as_admin()
            sys.exit(0)

    return {
        "deleted":  total_deleted,
        "freed_mb": total_freed / (1024 ** 2),
        "locked":   total_locked,
        "errors":   errors,
        "admin":    admin,
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
            f"  Admin privileges : {'Yes' if cleanup_summary.get('admin') else 'No'}",
            f"  Items deleted    : {cleanup_summary['deleted']}",
            f"  Locked (in use)  : {cleanup_summary.get('locked', 0)} — skipped safely",
            f"  Space freed      : {cleanup_summary['freed_mb']:.1f} MB",
            f"  Errors skipped   : {cleanup_summary['errors']}",
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
    msg.attach(MIMEText(_build_email_body(report, cleanup_summary), "plain", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        print("  [EMAIL] Alert sent successfully.")
    except smtplib.SMTPAuthenticationError:
        print("  [EMAIL] Authentication failed — check .env credentials.")
    except Exception as e:
        print(f"  [EMAIL] Failed to send: {e}")