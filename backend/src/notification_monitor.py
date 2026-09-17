"""Persistent monitoring of official FSSAI Gazette notifications."""

from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path

from src.scrape_notifications import main as scrape_notifications


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
STATE_FILE = OUTPUT_DIR / "notification_state.json"
DISCOVERY_FILE = OUTPUT_DIR / "latest_fssai_notifications.json"
CHECK_INTERVAL = timedelta(minutes=5)
RECENT_NOTIFICATION_WINDOW = timedelta(days=7)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def notification_id(notification):
    """Create a stable identifier without guessing an official URL."""
    pdf_url = (notification.get("pdf_url") or "").strip()

    if pdf_url:
        identity = pdf_url
    else:
        identity = "|".join(
            [
                (notification.get("title") or "").strip(),
                (notification.get("uploaded_date") or "").strip(),
            ]
        )

    return sha256(identity.encode("utf-8")).hexdigest()


def empty_state():
    return {
        "version": 1,
        "monitor_initialized": False,
        "last_successful_check": None,
        "notifications": {},
    }


def load_state():
    if not STATE_FILE.exists():
        return empty_state()

    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        # Do not overwrite a broken state file.  The API will surface the
        # error instead of silently treating every historical item as new.
        raise RuntimeError("Notification state file is unreadable")

    if not isinstance(state.get("notifications"), dict):
        raise RuntimeError("Notification state file has an invalid format")

    return state


def save_state(state):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    temporary_file = STATE_FILE.with_suffix(".tmp")
    temporary_file.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary_file.replace(STATE_FILE)


def seed_existing_notifications(state):
    """Mark previously stored/downloaded notifications as already known."""
    source_files = [
        OUTPUT_DIR / "notifications.json",
        OUTPUT_DIR / "pdf_downloads.json",
    ]
    timestamp = utc_now()

    for source_file in source_files:
        if not source_file.exists():
            continue

        try:
            notifications = json.loads(source_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        if not isinstance(notifications, list):
            continue

        for notification in notifications:
            if not isinstance(notification, dict):
                continue

            identifier = notification_id(notification)
            if not identifier or identifier in state["notifications"]:
                continue

            state["notifications"][identifier] = {
                "id": identifier,
                "title": notification.get("title", ""),
                "uploaded_date": notification.get("uploaded_date", ""),
                "Month": notification.get("Month"),
                "Year": notification.get("Year"),
                "pdf_url": notification.get("pdf_url") or "PDF_NOT_FOUND",
                "first_seen": timestamp,
                "last_seen": timestamp,
                "read": True,
                "alerted": True,
                "source": "existing_project_data",
            }


def check_for_new_notifications():
    """Discover the latest seven days and return unread and fresh items.

    The scraper is reused here and writes its recent-results snapshot to a
    dedicated file, so a monitor check never replaces a user's date search.
    """
    state = load_state()
    seed_existing_notifications(state)
    recent_start = date.today() - RECENT_NOTIFICATION_WINDOW
    expire_old_unread_notifications(state, recent_start)

    last_check = state.get("last_successful_check")
    if last_check:
        try:
            checked_at = datetime.fromisoformat(last_check)
            if datetime.now(timezone.utc) - checked_at < CHECK_INTERVAL:
                save_state(state)
                return {
                    "notifications": unread_notifications_from_state(
                        state,
                        recent_start,
                    ),
                    "fresh_notifications": [],
                    "latest_notification": latest_known_notification(state),
                    "last_successful_check": last_check,
                }
        except ValueError:
            # A malformed timestamp is treated as stale and gets refreshed.
            pass

    official_notifications = scrape_notifications(
        start_date=recent_start,
        end_date=date.today(),
        output_file=DISCOVERY_FILE,
        save_raw=False,
    )

    timestamp = utc_now()
    fresh_notifications = []
    is_first_monitor_check = not state.get("monitor_initialized", False)

    for notification in official_notifications:
        identifier = notification_id(notification)
        existing = state["notifications"].get(identifier)

        if existing is None:
            existing = {
                "id": identifier,
                "title": notification.get("title", ""),
                "uploaded_date": notification.get("uploaded_date", ""),
                "Month": notification.get("Month"),
                "Year": notification.get("Year"),
                "pdf_url": notification.get("pdf_url") or "PDF_NOT_FOUND",
                "first_seen": timestamp,
                # The first full archive scan establishes a baseline.  Old
                # portal records are not newly published notifications and
                # therefore must not create a historical alert flood.
                "read": is_first_monitor_check,
                "alerted": is_first_monitor_check,
                "source": (
                    "official_fssai_baseline"
                    if is_first_monitor_check
                    else "official_fssai"
                ),
            }
            state["notifications"][identifier] = existing

        existing["last_seen"] = timestamp

        if not is_first_monitor_check and not existing.get("alerted", False):
            fresh_notifications.append(existing.copy())
            existing["alerted"] = True

    state["monitor_initialized"] = True
    state["last_successful_check"] = timestamp
    save_state(state)

    unread_notifications = unread_notifications_from_state(state, recent_start)

    return {
        "notifications": unread_notifications,
        "fresh_notifications": fresh_notifications,
        "latest_notification": latest_known_notification(state),
        "last_successful_check": timestamp,
    }


def notification_date(notification):
    try:
        return datetime.strptime(
            notification.get("uploaded_date", ""),
            "%d-%m-%Y",
        ).date()
    except ValueError:
        return None


def expire_old_unread_notifications(state, recent_start):
    timestamp = utc_now()

    for notification in state["notifications"].values():
        published_date = notification_date(notification)
        if (
            not notification.get("read", False)
            and (published_date is None or published_date < recent_start)
        ):
            notification["read"] = True
            notification["expired_at"] = timestamp


def latest_known_notification(state):
    """Return the single most recently published notification, if any.

    Unlike unread_notifications_from_state, this ignores read status and the
    recent-window cutoff, so the bell panel always has something to show
    instead of appearing empty once everything has been marked read.
    """
    dated_notifications = [
        (notification_date(notification), notification)
        for notification in state["notifications"].values()
    ]
    dated_notifications = [
        item for item in dated_notifications if item[0] is not None
    ]

    if not dated_notifications:
        return None

    dated_notifications.sort(key=lambda item: item[0], reverse=True)
    return dated_notifications[0][1].copy()


def unread_notifications_from_state(state, recent_start=None):
    unread_notifications = [
        notification.copy()
        for notification in state["notifications"].values()
        if (
            not notification.get("read", False)
            and (
                recent_start is None
                or (
                    notification_date(notification) is not None
                    and notification_date(notification) >= recent_start
                )
            )
        )
    ]

    unread_notifications.sort(
        key=lambda notification: notification_date(notification) or date.min,
        reverse=True,
    )
    return unread_notifications


def mark_notifications_read(notification_ids):
    state = load_state()
    updated = 0

    for identifier in notification_ids:
        notification = state["notifications"].get(identifier)
        if notification and not notification.get("read", False):
            notification["read"] = True
            notification["read_at"] = utc_now()
            updated += 1

    save_state(state)
    return updated
