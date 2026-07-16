"""
HyprDo reminder daemon.

Polls the DB every 60 seconds and fires notify-send for due reminders.
Intended to run as a systemd user service or background process.
"""

from __future__ import annotations

import subprocess
import time

from . import database as db


_POLL_INTERVAL_SECONDS = 60
_APP_NAME = "HyprDo"


def send_notification(title: str, body: str) -> None:
    """Fire a desktop notification via notify-send."""
    subprocess.run(
        ["notify-send", "--app-name", _APP_NAME, "--icon", "checkbox-checked-symbolic", title, body],
        check=False,
    )


def process_due_reminders() -> int:
    """Fire notifications for all pending reminders. Returns count fired."""
    reminders = db.get_pending_reminders()
    for reminder in reminders:
        task = db.get_task(reminder.task_id)
        if task:
            send_notification(
                f"⏰ Task due soon",
                task.title,
            )
        db.mark_reminder_sent(reminder.id)
    return len(reminders)


def run_forever() -> None:
    """Main loop — poll every 60 seconds until killed."""
    db.init_db()
    while True:
        process_due_reminders()
        time.sleep(_POLL_INTERVAL_SECONDS)


def main() -> None:
    run_forever()
