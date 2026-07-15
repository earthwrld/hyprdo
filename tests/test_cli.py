"""Tests for HyprDo CLI commands."""

import json
from pathlib import Path

import pytest

from hyprdo import database as db
from hyprdo.cli import main
from hyprdo.models import Priority


@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect DB to a temp path and init it for every test."""
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("hyprdo.database.DB_PATH", db_path)
    db.init_db(db_path)


def _run(*argv: str, capsys: pytest.CaptureFixture) -> tuple[str, str]:
    """Run CLI with given argv, return (stdout, stderr)."""
    import sys
    monkeypatch_argv = ["hyprdo"] + list(argv)
    old_argv = sys.argv
    try:
        sys.argv = monkeypatch_argv
        try:
            main()
        except SystemExit:
            pass
    finally:
        sys.argv = old_argv
    captured = capsys.readouterr()
    return captured.out, captured.err


class TestAddCommand:
    def test_add_basic(self, capsys: pytest.CaptureFixture) -> None:
        out, _ = _run("add", "Buy milk", capsys=capsys)
        assert "#1" in out
        assert "Buy milk" in out

    def test_add_with_priority(self, capsys: pytest.CaptureFixture) -> None:
        _run("add", "Fix bug", "--priority", "high", capsys=capsys)
        tasks = db.list_tasks()
        assert tasks[0].priority == Priority.HIGH

    def test_add_with_deadline(self, capsys: pytest.CaptureFixture) -> None:
        _run("add", "Deploy", "--deadline", "2030-01-15 10:00", capsys=capsys)
        tasks = db.list_tasks()
        assert tasks[0].deadline is not None
        assert tasks[0].deadline.year == 2030

    def test_add_deadline_date_only(self, capsys: pytest.CaptureFixture) -> None:
        _run("add", "Review", "--deadline", "2030-06-01", capsys=capsys)
        tasks = db.list_tasks()
        assert tasks[0].deadline.month == 6

    def test_invalid_deadline_exits(self, capsys: pytest.CaptureFixture) -> None:
        import sys
        with pytest.raises(SystemExit) as exc:
            sys.argv = ["hyprdo", "add", "Task", "--deadline", "not-a-date"]
            main()
        assert exc.value.code == 1


class TestListCommand:
    def test_list_empty(self, capsys: pytest.CaptureFixture) -> None:
        out, _ = _run("list", capsys=capsys)
        assert "No tasks" in out

    def test_list_shows_tasks(self, capsys: pytest.CaptureFixture) -> None:
        db.create_task("Task Alpha")
        db.create_task("Task Beta")
        out, _ = _run("list", capsys=capsys)
        assert "Task Alpha" in out
        assert "Task Beta" in out

    def test_list_filters_done(self, capsys: pytest.CaptureFixture) -> None:
        t = db.create_task("Pending task")
        done = db.create_task("Done task")
        db.mark_done(done.id)
        out, _ = _run("list", "--status", "done", capsys=capsys)
        assert "Done task" in out
        assert "Pending task" not in out

    def test_list_json_output(self, capsys: pytest.CaptureFixture) -> None:
        db.create_task("JSON task", priority=Priority.HIGH)
        out, _ = _run("list", "--json", capsys=capsys)
        data = json.loads(out)
        assert isinstance(data, list)
        assert data[0]["title"] == "JSON task"
        assert data[0]["priority"] == "high"


class TestDoneCommand:
    def test_mark_done(self, capsys: pytest.CaptureFixture) -> None:
        task = db.create_task("Task to finish")
        _run("done", str(task.id), capsys=capsys)
        assert db.get_task(task.id).is_done

    def test_done_nonexistent_exits(self, capsys: pytest.CaptureFixture) -> None:
        import sys
        with pytest.raises(SystemExit) as exc:
            sys.argv = ["hyprdo", "done", "9999"]
            main()
        assert exc.value.code == 1


class TestUndoCommand:
    def test_undo_done_task(self, capsys: pytest.CaptureFixture) -> None:
        task = db.create_task("Finished task")
        db.mark_done(task.id)
        _run("undo", str(task.id), capsys=capsys)
        assert not db.get_task(task.id).is_done


class TestDeleteCommand:
    def test_delete_task(self, capsys: pytest.CaptureFixture) -> None:
        task = db.create_task("Temporary task")
        _run("delete", str(task.id), capsys=capsys)
        assert db.get_task(task.id) is None

    def test_delete_nonexistent_exits(self, capsys: pytest.CaptureFixture) -> None:
        import sys
        with pytest.raises(SystemExit) as exc:
            sys.argv = ["hyprdo", "delete", "9999"]
            main()
        assert exc.value.code == 1


class TestStatusCommand:
    def test_status_no_tasks(self, capsys: pytest.CaptureFixture) -> None:
        out, _ = _run("status", capsys=capsys)
        data = json.loads(out)
        assert data["class"] == "no-tasks"

    def test_status_with_tasks(self, capsys: pytest.CaptureFixture) -> None:
        db.create_task("Task A")
        out, _ = _run("status", capsys=capsys)
        data = json.loads(out)
        assert data["class"] == "has-tasks"
        assert "󰄲" in data["text"]
