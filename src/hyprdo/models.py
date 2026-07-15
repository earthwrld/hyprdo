"""
HyprDo — Data models.

All domain objects as Python dataclasses with validation helpers.
These are plain data containers — no DB logic here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"

    @classmethod
    def from_str(cls, value: str) -> "Priority":
        try:
            return cls(value.lower())
        except ValueError:
            return cls.NONE

    def label(self) -> str:
        return self.value.capitalize()

    def color_key(self) -> str:
        """Returns the theme color variable key for this priority."""
        return f"priority_{self.value}" if self != Priority.NONE else "priority_none"


class TaskStatus(str, Enum):
    TODO = "todo"
    DONE = "done"

    @classmethod
    def from_str(cls, value: str) -> "TaskStatus":
        try:
            return cls(value.lower())
        except ValueError:
            return cls.TODO


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@dataclass
class Subtask:
    id: int
    task_id: int
    title: str
    is_done: bool = False
    position: int = 0
    created_at: datetime = field(default_factory=datetime.now)

    def toggle(self) -> "Subtask":
        """Return a new Subtask with is_done flipped."""
        return Subtask(
            id=self.id,
            task_id=self.task_id,
            title=self.title,
            is_done=not self.is_done,
            position=self.position,
            created_at=self.created_at,
        )


@dataclass
class Label:
    id: int
    name: str
    color: str = "#bd93f9"  # default: violet


@dataclass
class Reminder:
    id: int
    task_id: int
    remind_at: datetime
    is_sent: bool = False
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Task:
    id: int
    title: str
    description: str = ""
    priority: Priority = Priority.NONE
    status: TaskStatus = TaskStatus.TODO
    deadline: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    done_at: Optional[datetime] = None
    position: int = 0
    # Populated on demand (not stored here, loaded from DB joins)
    subtasks: list[Subtask] = field(default_factory=list)
    labels: list[Label] = field(default_factory=list)
    reminders: list[Reminder] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Computed properties
    # ------------------------------------------------------------------

    @property
    def is_done(self) -> bool:
        return self.status == TaskStatus.DONE

    @property
    def is_overdue(self) -> bool:
        if self.deadline is None or self.is_done:
            return False
        return datetime.now() > self.deadline

    @property
    def is_due_today(self) -> bool:
        if self.deadline is None or self.is_done:
            return False
        now = datetime.now()
        return self.deadline.date() == now.date() and not self.is_overdue

    @property
    def is_due_tomorrow(self) -> bool:
        if self.deadline is None or self.is_done:
            return False
        from datetime import timedelta
        tomorrow = (datetime.now() + timedelta(days=1)).date()
        return self.deadline.date() == tomorrow

    @property
    def subtask_progress(self) -> float:
        """Returns completion ratio 0.0–1.0. Returns 0.0 if no subtasks."""
        if not self.subtasks:
            return 0.0
        done = sum(1 for s in self.subtasks if s.is_done)
        return done / len(self.subtasks)

    @property
    def subtask_progress_pct(self) -> int:
        return int(self.subtask_progress * 100)

    def deadline_badge(self) -> Optional[str]:
        """Returns badge text for deadline status, or None."""
        if self.deadline is None or self.is_done:
            return None
        if self.is_overdue:
            return "overdue!"
        if self.is_due_today:
            return f"due today {self.deadline.strftime('%H:%M')}"
        if self.is_due_tomorrow:
            return "due tomorrow"
        return None

    def deadline_badge_type(self) -> Optional[str]:
        """Returns 'overdue' | 'today' | 'tomorrow' | None."""
        if self.is_overdue:
            return "overdue"
        if self.is_due_today:
            return "today"
        if self.is_due_tomorrow:
            return "tomorrow"
        return None
