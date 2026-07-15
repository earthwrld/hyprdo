"""
HyprDo — SQLite database layer.

Single responsibility: read/write from SQLite.
All business logic lives in models.py or higher layers.

DB path: ~/.local/share/hyprdo/hyprdo.db
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

from .config import DB_PATH, get_config
from .models import Label, Priority, Reminder, Subtask, Task, TaskStatus

_DATETIME_FMT = "%Y-%m-%dT%H:%M:%S"


def _fmt_dt(dt: Optional[datetime]) -> Optional[str]:
    return dt.strftime(_DATETIME_FMT) if dt else None


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.strptime(s, _DATETIME_FMT)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    description TEXT    NOT NULL DEFAULT '',
    priority    TEXT    NOT NULL DEFAULT 'none'
                        CHECK(priority IN ('high', 'medium', 'low', 'none')),
    status      TEXT    NOT NULL DEFAULT 'todo'
                        CHECK(status IN ('todo', 'done')),
    deadline    TEXT,
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL,
    done_at     TEXT,
    position    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS subtasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    title       TEXT    NOT NULL,
    is_done     INTEGER NOT NULL DEFAULT 0,
    position    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS labels (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL UNIQUE,
    color TEXT NOT NULL DEFAULT '#bd93f9'
);

CREATE TABLE IF NOT EXISTS task_labels (
    task_id  INTEGER NOT NULL REFERENCES tasks(id)   ON DELETE CASCADE,
    label_id INTEGER NOT NULL REFERENCES labels(id)  ON DELETE CASCADE,
    PRIMARY KEY (task_id, label_id)
);

CREATE TABLE IF NOT EXISTS reminders (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id    INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    remind_at  TEXT    NOT NULL,
    is_sent    INTEGER NOT NULL DEFAULT 0,
    created_at TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_status    ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority  ON tasks(priority);
CREATE INDEX IF NOT EXISTS idx_tasks_deadline  ON tasks(deadline);
CREATE INDEX IF NOT EXISTS idx_subtasks_task   ON subtasks(task_id);
CREATE INDEX IF NOT EXISTS idx_reminders_due   ON reminders(is_sent, remind_at);
"""

_DEFAULT_LABELS = [
    ("work",     "#ef4444"),
    ("personal", "#22c55e"),
    ("study",    "#38bdf8"),
    ("urgent",   "#f97316"),
]


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------


def _get_db_path() -> Path:
    return DB_PATH


@contextmanager
def _connect(db_path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
    path = db_path or _get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def init_db(db_path: Optional[Path] = None) -> None:
    """Create tables and seed default labels if DB is new."""
    with _connect(db_path) as conn:
        conn.executescript(_SCHEMA)
        # Seed default labels only if table is empty
        count = conn.execute("SELECT COUNT(*) FROM labels").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO labels (name, color) VALUES (?, ?)",
                _DEFAULT_LABELS,
            )


# ---------------------------------------------------------------------------
# Row → Model converters
# ---------------------------------------------------------------------------


def _row_to_task(row: sqlite3.Row) -> Task:
    return Task(
        id=row["id"],
        title=row["title"],
        description=row["description"] or "",
        priority=Priority.from_str(row["priority"]),
        status=TaskStatus.from_str(row["status"]),
        deadline=_parse_dt(row["deadline"]),
        created_at=_parse_dt(row["created_at"]) or datetime.now(),
        updated_at=_parse_dt(row["updated_at"]) or datetime.now(),
        done_at=_parse_dt(row["done_at"]),
        position=row["position"],
    )


def _row_to_subtask(row: sqlite3.Row) -> Subtask:
    return Subtask(
        id=row["id"],
        task_id=row["task_id"],
        title=row["title"],
        is_done=bool(row["is_done"]),
        position=row["position"],
        created_at=_parse_dt(row["created_at"]) or datetime.now(),
    )


def _row_to_label(row: sqlite3.Row) -> Label:
    return Label(id=row["id"], name=row["name"], color=row["color"])


def _row_to_reminder(row: sqlite3.Row) -> Reminder:
    return Reminder(
        id=row["id"],
        task_id=row["task_id"],
        remind_at=_parse_dt(row["remind_at"]) or datetime.now(),
        is_sent=bool(row["is_sent"]),
        created_at=_parse_dt(row["created_at"]) or datetime.now(),
    )


# ---------------------------------------------------------------------------
# Task CRUD
# ---------------------------------------------------------------------------


def create_task(
    title: str,
    description: str = "",
    priority: Priority = Priority.NONE,
    deadline: Optional[datetime] = None,
    db_path: Optional[Path] = None,
) -> Task:
    """Insert a new task and return it with generated ID."""
    now = datetime.now()
    with _connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO tasks (title, description, priority, deadline, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (title, description, priority.value, _fmt_dt(deadline), _fmt_dt(now), _fmt_dt(now)),
        )
        task_id = cur.lastrowid

        # Auto-create reminders if deadline set
        cfg = get_config()
        if deadline:
            _create_reminders_for_task(conn, task_id, deadline, cfg["remind_before_minutes"])

        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return _row_to_task(row)


def get_task(task_id: int, db_path: Optional[Path] = None) -> Optional[Task]:
    """Fetch a single task with its subtasks and labels."""
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            return None
        task = _row_to_task(row)
        task.subtasks = _get_subtasks(conn, task_id)
        task.labels = _get_labels_for_task(conn, task_id)
        task.reminders = _get_reminders(conn, task_id)
        return task


def list_tasks(
    status: Optional[TaskStatus] = None,
    priority: Optional[Priority] = None,
    include_subtasks: bool = True,
    db_path: Optional[Path] = None,
) -> list[Task]:
    """List tasks with optional filters. Defaults to all tasks."""
    clauses, params = [], []
    if status is not None:
        clauses.append("status = ?")
        params.append(status.value)
    if priority is not None:
        clauses.append("priority = ?")
        params.append(priority.value)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT * FROM tasks {where} ORDER BY position, created_at"

    with _connect(db_path) as conn:
        rows = conn.execute(sql, params).fetchall()
        tasks = [_row_to_task(r) for r in rows]
        if include_subtasks:
            for task in tasks:
                task.subtasks = _get_subtasks(conn, task.id)
                task.labels = _get_labels_for_task(conn, task.id)
        return tasks


def update_task(
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[Priority] = None,
    deadline: Optional[datetime] = None,
    db_path: Optional[Path] = None,
) -> Optional[Task]:
    """Update task fields. Only provided (non-None) fields are changed."""
    now = _fmt_dt(datetime.now())
    sets, params = ["updated_at = ?"], [now]

    if title is not None:
        sets.append("title = ?")
        params.append(title)
    if description is not None:
        sets.append("description = ?")
        params.append(description)
    if priority is not None:
        sets.append("priority = ?")
        params.append(priority.value)
    if deadline is not None:
        sets.append("deadline = ?")
        params.append(_fmt_dt(deadline))

    params.append(task_id)
    with _connect(db_path) as conn:
        conn.execute(
            f"UPDATE tasks SET {', '.join(sets)} WHERE id = ?", params
        )
    return get_task(task_id, db_path)


def mark_done(task_id: int, db_path: Optional[Path] = None) -> Optional[Task]:
    now = _fmt_dt(datetime.now())
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE tasks SET status = 'done', done_at = ?, updated_at = ? WHERE id = ?",
            (now, now, task_id),
        )
    return get_task(task_id, db_path)


def mark_todo(task_id: int, db_path: Optional[Path] = None) -> Optional[Task]:
    now = _fmt_dt(datetime.now())
    with _connect(db_path) as conn:
        conn.execute(
            "UPDATE tasks SET status = 'todo', done_at = NULL, updated_at = ? WHERE id = ?",
            (now, task_id),
        )
    return get_task(task_id, db_path)


def delete_task(task_id: int, db_path: Optional[Path] = None) -> bool:
    with _connect(db_path) as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Subtask CRUD
# ---------------------------------------------------------------------------


def _get_subtasks(conn: sqlite3.Connection, task_id: int) -> list[Subtask]:
    rows = conn.execute(
        "SELECT * FROM subtasks WHERE task_id = ? ORDER BY position, id",
        (task_id,),
    ).fetchall()
    return [_row_to_subtask(r) for r in rows]


def add_subtask(task_id: int, title: str, db_path: Optional[Path] = None) -> Subtask:
    now = _fmt_dt(datetime.now())
    with _connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO subtasks (task_id, title, created_at) VALUES (?, ?, ?)",
            (task_id, title, now),
        )
        row = conn.execute("SELECT * FROM subtasks WHERE id = ?", (cur.lastrowid,)).fetchone()
        return _row_to_subtask(row)


def toggle_subtask(subtask_id: int, db_path: Optional[Path] = None) -> Optional[Subtask]:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT * FROM subtasks WHERE id = ?", (subtask_id,)).fetchone()
        if not row:
            return None
        new_done = 0 if row["is_done"] else 1
        conn.execute("UPDATE subtasks SET is_done = ? WHERE id = ?", (new_done, subtask_id))
        row = conn.execute("SELECT * FROM subtasks WHERE id = ?", (subtask_id,)).fetchone()
        return _row_to_subtask(row)


def delete_subtask(subtask_id: int, db_path: Optional[Path] = None) -> bool:
    with _connect(db_path) as conn:
        cur = conn.execute("DELETE FROM subtasks WHERE id = ?", (subtask_id,))
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Label CRUD
# ---------------------------------------------------------------------------


def _get_labels_for_task(conn: sqlite3.Connection, task_id: int) -> list[Label]:
    rows = conn.execute(
        """
        SELECT l.* FROM labels l
        JOIN task_labels tl ON tl.label_id = l.id
        WHERE tl.task_id = ?
        """,
        (task_id,),
    ).fetchall()
    return [_row_to_label(r) for r in rows]


def list_labels(db_path: Optional[Path] = None) -> list[Label]:
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM labels ORDER BY name").fetchall()
        return [_row_to_label(r) for r in rows]


def create_label(name: str, color: str = "#bd93f9", db_path: Optional[Path] = None) -> Label:
    with _connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO labels (name, color) VALUES (?, ?)", (name, color)
        )
        row = conn.execute("SELECT * FROM labels WHERE id = ?", (cur.lastrowid,)).fetchone()
        return _row_to_label(row)


def attach_label(task_id: int, label_id: int, db_path: Optional[Path] = None) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO task_labels (task_id, label_id) VALUES (?, ?)",
            (task_id, label_id),
        )


def detach_label(task_id: int, label_id: int, db_path: Optional[Path] = None) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "DELETE FROM task_labels WHERE task_id = ? AND label_id = ?",
            (task_id, label_id),
        )


# ---------------------------------------------------------------------------
# Reminders
# ---------------------------------------------------------------------------


def _get_reminders(conn: sqlite3.Connection, task_id: int) -> list[Reminder]:
    rows = conn.execute(
        "SELECT * FROM reminders WHERE task_id = ? ORDER BY remind_at",
        (task_id,),
    ).fetchall()
    return [_row_to_reminder(r) for r in rows]


def _create_reminders_for_task(
    conn: sqlite3.Connection,
    task_id: int,
    deadline: datetime,
    before_minutes: list[int],
) -> None:
    from datetime import timedelta
    now = datetime.now()
    for minutes in before_minutes:
        remind_at = deadline - timedelta(minutes=minutes)
        if remind_at > now:  # only future reminders
            conn.execute(
                "INSERT INTO reminders (task_id, remind_at, created_at) VALUES (?, ?, ?)",
                (task_id, _fmt_dt(remind_at), _fmt_dt(now)),
            )


def get_pending_reminders(db_path: Optional[Path] = None) -> list[Reminder]:
    """Return all reminders that are due and not yet sent."""
    now = _fmt_dt(datetime.now())
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM reminders WHERE is_sent = 0 AND remind_at <= ?",
            (now,),
        ).fetchall()
        return [_row_to_reminder(r) for r in rows]


def mark_reminder_sent(reminder_id: int, db_path: Optional[Path] = None) -> None:
    with _connect(db_path) as conn:
        conn.execute("UPDATE reminders SET is_sent = 1 WHERE id = ?", (reminder_id,))


# ---------------------------------------------------------------------------
# Waybar status query
# ---------------------------------------------------------------------------


def get_waybar_status(db_path: Optional[Path] = None) -> dict:
    """
    Returns a dict ready for Waybar JSON output:
      {"text": "󰄲 5", "tooltip": "High: Fix login bug", "class": "has-tasks"}
    """
    with _connect(db_path) as conn:
        pending = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status = 'todo'"
        ).fetchone()[0]

        top = conn.execute(
            """
            SELECT title, deadline FROM tasks
            WHERE status = 'todo' AND priority = 'high'
            ORDER BY deadline ASC NULLS LAST
            LIMIT 1
            """
        ).fetchone()

        overdue = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE status = 'todo' AND deadline < ?",
            (_fmt_dt(datetime.now()),),
        ).fetchone()[0]

    icon = "󰄲"
    if pending == 0:
        return {"text": icon, "tooltip": "No pending tasks", "class": "no-tasks", "percentage": 0}

    text = f"{icon} {pending}"
    css_class = "has-overdue" if overdue > 0 else "has-tasks"

    tooltip = f"{pending} pending task{'s' if pending != 1 else ''}"
    if top:
        deadline_str = ""
        if top["deadline"]:
            dt = _parse_dt(top["deadline"])
            if dt:
                deadline_str = f" (due: {dt.strftime('%b %d %H:%M')})"
        tooltip = f"High: {top['title']}{deadline_str}"

    return {"text": text, "tooltip": tooltip, "class": css_class, "percentage": 0}
