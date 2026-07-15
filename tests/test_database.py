"""
Tests for HyprDo database layer and models.
Uses an in-memory / temp SQLite DB — no side effects.
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from hyprdo.database import (
    add_subtask,
    attach_label,
    create_label,
    create_task,
    delete_task,
    get_pending_reminders,
    get_task,
    get_waybar_status,
    init_db,
    list_labels,
    list_tasks,
    mark_done,
    mark_reminder_sent,
    mark_todo,
    toggle_subtask,
    update_task,
)
from hyprdo.models import Priority, TaskStatus


@pytest.fixture
def db(tmp_path: Path) -> Path:
    """Create and init a fresh temp DB for each test."""
    db_path = tmp_path / "test.db"
    init_db(db_path)
    return db_path


# ---------------------------------------------------------------------------
# Task CRUD
# ---------------------------------------------------------------------------


class TestCreateTask:
    def test_basic_create(self, db: Path) -> None:
        task = create_task("Fix login bug", db_path=db)
        assert task.id is not None
        assert task.title == "Fix login bug"
        assert task.priority == Priority.NONE
        assert task.status == TaskStatus.TODO

    def test_create_with_priority_and_deadline(self, db: Path) -> None:
        deadline = datetime.now() + timedelta(days=1)
        task = create_task(
            "Deploy app",
            priority=Priority.HIGH,
            deadline=deadline,
            db_path=db,
        )
        assert task.priority == Priority.HIGH
        assert task.deadline is not None
        assert abs((task.deadline - deadline).total_seconds()) < 2


class TestListTasks:
    def test_list_all(self, db: Path) -> None:
        create_task("Task A", db_path=db)
        create_task("Task B", db_path=db)
        tasks = list_tasks(db_path=db)
        assert len(tasks) == 2

    def test_filter_by_status(self, db: Path) -> None:
        t = create_task("Task A", db_path=db)
        create_task("Task B", db_path=db)
        mark_done(t.id, db_path=db)

        pending = list_tasks(status=TaskStatus.TODO, db_path=db)
        done = list_tasks(status=TaskStatus.DONE, db_path=db)
        assert len(pending) == 1
        assert len(done) == 1

    def test_filter_by_priority(self, db: Path) -> None:
        create_task("High task", priority=Priority.HIGH, db_path=db)
        create_task("Low task", priority=Priority.LOW, db_path=db)

        highs = list_tasks(priority=Priority.HIGH, db_path=db)
        assert len(highs) == 1
        assert highs[0].title == "High task"


class TestUpdateTask:
    def test_update_title(self, db: Path) -> None:
        task = create_task("Old title", db_path=db)
        updated = update_task(task.id, title="New title", db_path=db)
        assert updated.title == "New title"

    def test_update_priority(self, db: Path) -> None:
        task = create_task("Task", db_path=db)
        updated = update_task(task.id, priority=Priority.HIGH, db_path=db)
        assert updated.priority == Priority.HIGH


class TestMarkDone:
    def test_mark_done(self, db: Path) -> None:
        task = create_task("Task", db_path=db)
        done = mark_done(task.id, db_path=db)
        assert done.status == TaskStatus.DONE
        assert done.done_at is not None
        assert done.is_done is True

    def test_mark_todo_again(self, db: Path) -> None:
        task = create_task("Task", db_path=db)
        mark_done(task.id, db_path=db)
        reverted = mark_todo(task.id, db_path=db)
        assert reverted.status == TaskStatus.TODO
        assert reverted.done_at is None


class TestDeleteTask:
    def test_delete(self, db: Path) -> None:
        task = create_task("Task", db_path=db)
        assert delete_task(task.id, db_path=db) is True
        assert get_task(task.id, db_path=db) is None

    def test_delete_nonexistent(self, db: Path) -> None:
        assert delete_task(9999, db_path=db) is False


# ---------------------------------------------------------------------------
# Subtasks
# ---------------------------------------------------------------------------


class TestSubtasks:
    def test_add_and_fetch(self, db: Path) -> None:
        task = create_task("Task", db_path=db)
        sub = add_subtask(task.id, "Read docs", db_path=db)
        assert sub.title == "Read docs"
        assert sub.is_done is False

        fetched = get_task(task.id, db_path=db)
        assert len(fetched.subtasks) == 1

    def test_toggle_subtask(self, db: Path) -> None:
        task = create_task("Task", db_path=db)
        sub = add_subtask(task.id, "Write test", db_path=db)
        toggled = toggle_subtask(sub.id, db_path=db)
        assert toggled.is_done is True

    def test_subtask_progress(self, db: Path) -> None:
        task = create_task("Task", db_path=db)
        s1 = add_subtask(task.id, "Step 1", db_path=db)
        add_subtask(task.id, "Step 2", db_path=db)
        toggle_subtask(s1.id, db_path=db)

        fetched = get_task(task.id, db_path=db)
        assert fetched.subtask_progress_pct == 50


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------


class TestLabels:
    def test_default_labels_seeded(self, db: Path) -> None:
        labels = list_labels(db_path=db)
        names = [l.name for l in labels]
        assert "work" in names
        assert "personal" in names

    def test_create_and_attach(self, db: Path) -> None:
        task = create_task("Task", db_path=db)
        label = create_label("backend", "#7c3aed", db_path=db)
        attach_label(task.id, label.id, db_path=db)

        fetched = get_task(task.id, db_path=db)
        assert any(l.name == "backend" for l in fetched.labels)


# ---------------------------------------------------------------------------
# Reminders
# ---------------------------------------------------------------------------


class TestReminders:
    def test_auto_reminders_created_on_deadline(self, db: Path) -> None:
        deadline = datetime.now() + timedelta(hours=3)
        task = create_task("Task", deadline=deadline, db_path=db)

        fetched = get_task(task.id, db_path=db)
        # Both H-1 and H-5min should be created (both are in the future)
        assert len(fetched.reminders) == 2

    def test_pending_reminders_query(self, db: Path) -> None:
        # Create a task with a deadline in the past → reminders will be overdue
        deadline = datetime.now() - timedelta(hours=2)
        # Manually create: init_db, then raw insert to bypass future check
        import sqlite3 as _sqlite3
        conn = _sqlite3.connect(db)
        conn.execute("PRAGMA foreign_keys = ON")
        now_str = deadline.strftime("%Y-%m-%dT%H:%M:%S")
        conn.execute(
            "INSERT INTO tasks (title, priority, status, created_at, updated_at) VALUES (?, 'none', 'todo', ?, ?)",
            ("Past task", now_str, now_str),
        )
        task_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        remind_at = (datetime.now() - timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%S")
        conn.execute(
            "INSERT INTO reminders (task_id, remind_at, is_sent, created_at) VALUES (?, ?, 0, ?)",
            (task_id, remind_at, now_str),
        )
        conn.commit()
        conn.close()

        pending = get_pending_reminders(db_path=db)
        assert len(pending) >= 1

    def test_mark_sent(self, db: Path) -> None:
        deadline = datetime.now() + timedelta(hours=3)
        task = create_task("Task", deadline=deadline, db_path=db)
        fetched = get_task(task.id, db_path=db)
        reminder_id = fetched.reminders[0].id
        mark_reminder_sent(reminder_id, db_path=db)

        fetched2 = get_task(task.id, db_path=db)
        sent = next(r for r in fetched2.reminders if r.id == reminder_id)
        assert sent.is_sent is True


# ---------------------------------------------------------------------------
# Model computed properties
# ---------------------------------------------------------------------------


class TestModelProperties:
    def test_overdue(self, db: Path) -> None:
        task = create_task(
            "Task",
            deadline=datetime.now() - timedelta(hours=1),
            db_path=db,
        )
        fetched = get_task(task.id, db_path=db)
        assert fetched.is_overdue is True
        assert fetched.deadline_badge_type() == "overdue"

    def test_due_today(self, db: Path) -> None:
        deadline = datetime.now().replace(hour=23, minute=59)
        task = create_task("Task", deadline=deadline, db_path=db)
        fetched = get_task(task.id, db_path=db)
        assert fetched.is_due_today is True
        assert fetched.deadline_badge_type() == "today"

    def test_due_tomorrow(self, db: Path) -> None:
        deadline = datetime.now() + timedelta(days=1)
        deadline = deadline.replace(hour=10, minute=0)
        task = create_task("Task", deadline=deadline, db_path=db)
        fetched = get_task(task.id, db_path=db)
        assert fetched.is_due_tomorrow is True
        assert fetched.deadline_badge_type() == "tomorrow"


# ---------------------------------------------------------------------------
# Waybar status
# ---------------------------------------------------------------------------


class TestWaybarStatus:
    def test_no_tasks(self, db: Path) -> None:
        status = get_waybar_status(db_path=db)
        assert status["class"] == "no-tasks"
        assert "󰄲" in status["text"]

    def test_has_tasks(self, db: Path) -> None:
        create_task("Task A", db_path=db)
        create_task("Task B", priority=Priority.HIGH, db_path=db)
        status = get_waybar_status(db_path=db)
        assert status["class"] == "has-tasks"
        assert "2" in status["text"]

    def test_overdue_class(self, db: Path) -> None:
        create_task(
            "Overdue task",
            deadline=datetime.now() - timedelta(hours=1),
            db_path=db,
        )
        status = get_waybar_status(db_path=db)
        assert status["class"] == "has-overdue"
