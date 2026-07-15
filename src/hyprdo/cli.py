"""
HyprDo CLI — hyprdo <command> [args]

Commands:
    add     Add a new task
    list    List tasks
    done    Mark a task done
    undo    Mark a done task as todo again
    delete  Delete a task
    status  Print Waybar JSON status
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from typing import NoReturn

from . import database as db
from .models import Priority, Task, TaskStatus

_DEADLINE_FORMATS = ("%Y-%m-%d %H:%M", "%Y-%m-%d")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)
    db.init_db()
    args.func(args)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hyprdo",
        description="HyprDo — to-do list for Hyprland",
    )
    sub = parser.add_subparsers(metavar="command")

    _add_add_command(sub)
    _add_list_command(sub)
    _add_done_command(sub)
    _add_undo_command(sub)
    _add_delete_command(sub)
    _add_status_command(sub)

    return parser


def _add_add_command(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("add", help="Add a new task")
    p.add_argument("title", help="Task title")
    p.add_argument("-d", "--description", default="", metavar="TEXT")
    p.add_argument(
        "-p", "--priority",
        choices=["high", "medium", "low", "none"],
        default="none",
    )
    p.add_argument("--deadline", metavar="YYYY-MM-DD [HH:MM]")
    p.set_defaults(func=_cmd_add)


def _add_list_command(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("list", help="List tasks")
    p.add_argument(
        "-s", "--status",
        choices=["todo", "done", "all"],
        default="todo",
    )
    p.add_argument(
        "-p", "--priority",
        choices=["high", "medium", "low", "none"],
        default=None,
    )
    p.add_argument("--json", action="store_true", help="Output as JSON")
    p.set_defaults(func=_cmd_list)


def _add_done_command(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("done", help="Mark a task as done")
    p.add_argument("id", type=int)
    p.set_defaults(func=_cmd_done)


def _add_undo_command(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("undo", help="Revert a done task to todo")
    p.add_argument("id", type=int)
    p.set_defaults(func=_cmd_undo)


def _add_delete_command(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("delete", help="Delete a task permanently")
    p.add_argument("id", type=int)
    p.set_defaults(func=_cmd_delete)


def _add_status_command(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser("status", help="Print Waybar JSON status")
    p.set_defaults(func=_cmd_status)


# ---------------------------------------------------------------------------
# Command handlers — each does exactly one thing
# ---------------------------------------------------------------------------


def _cmd_add(args: argparse.Namespace) -> None:
    deadline = _parse_deadline(args.deadline)
    task = db.create_task(
        title=args.title,
        description=args.description,
        priority=Priority.from_str(args.priority),
        deadline=deadline,
    )
    print(f"✓ Added #{task.id}: {task.title}")


def _cmd_list(args: argparse.Namespace) -> None:
    status_filter = None if args.status == "all" else TaskStatus.from_str(args.status)
    priority_filter = Priority.from_str(args.priority) if args.priority else None
    tasks = db.list_tasks(status=status_filter, priority=priority_filter)

    if args.json:
        print(json.dumps([_task_to_dict(t) for t in tasks], indent=2))
        return

    if not tasks:
        print("No tasks found.")
        return

    for task in tasks:
        print(_format_task_row(task))


def _cmd_done(args: argparse.Namespace) -> None:
    task = _require_task(args.id)
    db.mark_done(task.id)
    print(f"✓ Done #{task.id}: {task.title}")


def _cmd_undo(args: argparse.Namespace) -> None:
    task = _require_task(args.id)
    db.mark_todo(task.id)
    print(f"↩ Reverted #{task.id}: {task.title}")


def _cmd_delete(args: argparse.Namespace) -> None:
    task = _require_task(args.id)
    db.delete_task(task.id)
    print(f"🗑 Deleted #{task.id}: {task.title}")


def _cmd_status(args: argparse.Namespace) -> None:
    print(json.dumps(db.get_waybar_status()))


# ---------------------------------------------------------------------------
# Helpers — small, single-purpose
# ---------------------------------------------------------------------------


def _parse_deadline(raw: str | None) -> datetime | None:
    if not raw:
        return None
    for fmt in _DEADLINE_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    _die(f"Invalid deadline '{raw}'. Use YYYY-MM-DD or YYYY-MM-DD HH:MM")


def _require_task(task_id: int) -> Task:
    """Fetch task or exit with a clear error message."""
    task = db.get_task(task_id)
    if task is None:
        _die(f"Task #{task_id} not found")
    return task


def _die(message: str) -> NoReturn:
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)


def _format_task_row(task: Task) -> str:
    priority_symbol = {"high": "🔴", "medium": "🟡", "low": "🟢", "none": "⚪"}
    dot = priority_symbol.get(task.priority.value, "⚪")
    status = "✓" if task.is_done else " "
    badge = f"  [{task.deadline_badge()}]" if task.deadline_badge() else ""
    progress = f"  ({task.subtask_progress_pct}%)" if task.subtasks else ""
    return f"[{status}] #{task.id:>3}  {dot} {task.title}{badge}{progress}"


def _task_to_dict(task: Task) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "priority": task.priority.value,
        "status": task.status.value,
        "deadline": task.deadline.isoformat() if task.deadline else None,
        "deadline_badge": task.deadline_badge(),
        "subtask_progress_pct": task.subtask_progress_pct,
        "subtasks": [{"id": s.id, "title": s.title, "done": s.is_done} for s in task.subtasks],
        "labels": [{"id": l.id, "name": l.name, "color": l.color} for l in task.labels],
        "created_at": task.created_at.isoformat(),
    }
