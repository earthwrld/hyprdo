"""
HyprDo — TaskRow widget.

Single responsibility: display one Task as a GTK ListBoxRow.
Handles expand/collapse (for subtasks) and done/undo toggle.
"""

from __future__ import annotations

from typing import Callable

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from .. import database as db
from ..models import Priority, Task

_PRIORITY_SYMBOL = {
    Priority.HIGH:   ("●", "dot-high"),
    Priority.MEDIUM: ("●", "dot-medium"),
    Priority.LOW:    ("●", "dot-low"),
    Priority.NONE:   ("●", "dot-none"),
}


class TaskRow(Gtk.ListBoxRow):
    """A single task row with optional subtask expansion."""

    def __init__(self, task: Task, on_changed: Callable[[], None]) -> None:
        super().__init__(css_classes=["task-card"])
        self._task = task
        self._on_changed = on_changed  # called whenever DB changes
        self._expanded = False

        self._outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._outer.append(self._build_collapsed_row())
        self.set_child(self._outer)

    # ------------------------------------------------------------------
    # Row construction
    # ------------------------------------------------------------------

    def _build_collapsed_row(self) -> Gtk.Box:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        row.append(self._priority_dot())
        row.append(self._title_label())
        row.append(Gtk.Box(hexpand=True))  # spacer
        
        for label in self._task.labels:
            lbl = Gtk.Label(label=f" {label.name} ", css_classes=["label-pill"])
            # Apply dynamic color via CSS later, for now just use the class
            row.append(lbl)
            
        row.append(self._deadline_badge())
        if self._task.subtasks:
            row.append(self._expand_button())
        row.append(self._done_checkbox())
        return row

    def _build_subtask_section(self) -> Gtk.Box:
        section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        section.set_margin_start(20)

        for subtask in self._task.subtasks:
            section.append(self._subtask_row(subtask))

        if self._task.subtasks:
            section.append(self._progress_bar())

        return section

    # ------------------------------------------------------------------
    # Individual widgets — each builds exactly one thing
    # ------------------------------------------------------------------

    def _priority_dot(self) -> Gtk.Label:
        symbol, css_class = _PRIORITY_SYMBOL.get(self._task.priority, ("●", "dot-none"))
        label = Gtk.Label(label=symbol, css_classes=[css_class])
        if self._task.is_done:
            label.remove_css_class(css_class)
            label.add_css_class("dot-none")
        return label

    def _title_label(self) -> Gtk.Label:
        label = Gtk.Label(
            label=self._task.title,
            xalign=0,
            css_classes=["task-title"],
            ellipsize=3,  # PANGO_ELLIPSIZE_END
        )
        if self._task.is_done:
            label.add_css_class("done")
        return label

    def _deadline_badge(self) -> Gtk.Widget:
        badge_text = self._task.deadline_badge()
        badge_type = self._task.deadline_badge_type()
        if not badge_text:
            return Gtk.Box()  # empty placeholder

        label = Gtk.Label(
            label=badge_text,
            css_classes=["badge", f"badge-{badge_type}"],
        )
        return label

    def _expand_button(self) -> Gtk.Button:
        icon = Gtk.Image(icon_name="pan-down-symbolic" if self._expanded else "pan-end-symbolic")
        btn = Gtk.Button(child=icon, css_classes=["flat"])
        btn.connect("clicked", self._on_expand_clicked)
        return btn

    def _done_checkbox(self) -> Gtk.CheckButton:
        check = Gtk.CheckButton(active=self._task.is_done)
        check.connect("toggled", self._on_done_toggled)
        return check

    def _subtask_row(self, subtask) -> Gtk.Box:
        row  = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, css_classes=["subtask-row"])
        check = Gtk.CheckButton(active=subtask.is_done)
        check.connect("toggled", self._on_subtask_toggled, subtask.id)

        label = Gtk.Label(label=subtask.title, xalign=0)
        if subtask.is_done:
            label.add_css_class("done")

        row.append(check)
        row.append(label)
        return row

    def _progress_bar(self) -> Gtk.ProgressBar:
        bar = Gtk.ProgressBar(
            fraction=self._task.subtask_progress,
            css_classes=["progress-bar"],
        )
        bar.set_show_text(True)
        bar.set_margin_top(4)
        return bar

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_expand_clicked(self, _btn: Gtk.Button) -> None:
        self._expanded = not self._expanded
        if self._expanded:
            self._subtask_widget = self._build_subtask_section()
            self._outer.append(self._subtask_widget)
        else:
            self._outer.remove(self._subtask_widget)

    def _on_done_toggled(self, check: Gtk.CheckButton) -> None:
        if check.get_active():
            db.mark_done(self._task.id)
        else:
            db.mark_todo(self._task.id)
        self._on_changed()

    def _on_subtask_toggled(self, _check: Gtk.CheckButton, subtask_id: int) -> None:
        db.toggle_subtask(subtask_id)
        self._on_changed()
