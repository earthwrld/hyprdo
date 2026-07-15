"""
HyprDo — Add/Edit Task dialog.

Single responsibility: collect task data from the user.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from ..models import Priority

_DEADLINE_FORMATS = ("%Y-%m-%d %H:%M", "%Y-%m-%d")
_PRIORITY_OPTIONS = [
    ("High",   Priority.HIGH,   "dot-high"),
    ("Medium", Priority.MEDIUM, "dot-medium"),
    ("Low",    Priority.LOW,    "dot-low"),
    ("None",   Priority.NONE,   "dot-none"),
]


class AddTaskDialog(Gtk.Window):
    """Modal window for adding or editing a task."""

    def __init__(self, parent: Gtk.Window, task=None) -> None:
        super().__init__(
            title="Edit Task" if task else "New Task",
            transient_for=parent,
            modal=True,
            default_width=420,
            resizable=False,
        )
        self._selected_priority = task.priority if task else Priority.NONE
        self._task = task
        self._result: Optional[dict] = None

        self.set_child(self._build_content())
        self._populate_from_task(task)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    @property
    def result(self) -> Optional[dict]:
        """Returns task dict if confirmed, None if cancelled."""
        return self._result

    # ------------------------------------------------------------------
    # UI construction — top-down (newspaper metaphor)
    # ------------------------------------------------------------------

    def _build_content(self) -> Gtk.Box:
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.append(self._build_headerbar())
        root.append(self._build_form())
        return root

    def _build_headerbar(self) -> Adw.HeaderBar:
        bar = Adw.HeaderBar()
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda _: self.close())
        bar.pack_start(cancel_btn)

        label = self._task and "Save" or "Add Task"
        confirm_btn = Gtk.Button(label=label, css_classes=["add-btn", "suggested-action"])
        confirm_btn.connect("clicked", self._on_confirm)
        bar.pack_end(confirm_btn)
        return bar

    def _build_form(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(8)
        box.set_margin_bottom(16)

        self._title_entry = self._labeled_entry("Title", "What needs to be done?")
        self._desc_entry  = self._labeled_text_view("Description (optional)")
        priority_row      = self._build_priority_row()
        self._deadline_entry = self._labeled_entry("Deadline", "YYYY-MM-DD HH:MM  (optional)")

        box.append(self._title_entry[0])
        box.append(self._desc_entry[0])
        box.append(priority_row)
        box.append(self._deadline_entry[0])
        return box

    def _build_priority_row(self) -> Gtk.Box:
        label = Gtk.Label(label="Priority", xalign=0, css_classes=["task-meta"])
        row   = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        pills = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self._priority_buttons: dict[Priority, Gtk.ToggleButton] = {}
        first = None
        for text, prio, css in _PRIORITY_OPTIONS:
            btn = Gtk.ToggleButton(label=text, css_classes=["priority-pill"])
            if first:
                btn.set_group(first)
            else:
                first = btn
            if prio == self._selected_priority:
                btn.set_active(True)
            btn.connect("toggled", self._on_priority_toggled, prio)
            self._priority_buttons[prio] = btn
            pills.append(btn)

        row.append(label)
        row.append(pills)
        return row

    # ------------------------------------------------------------------
    # Helpers — small, single-purpose
    # ------------------------------------------------------------------

    def _labeled_entry(self, label_text: str, placeholder: str) -> tuple[Gtk.Box, Gtk.Entry]:
        label = Gtk.Label(label=label_text, xalign=0, css_classes=["task-meta"])
        entry = Gtk.Entry(placeholder_text=placeholder)
        box   = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.append(label)
        box.append(entry)
        return box, entry

    def _labeled_text_view(self, placeholder: str) -> tuple[Gtk.Box, Gtk.TextView]:
        label   = Gtk.Label(label="Description", xalign=0, css_classes=["task-meta"])
        view    = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD, height_request=72)
        view.get_buffer().set_text("")
        scroll  = Gtk.ScrolledWindow(child=view, height_request=72)
        box     = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.append(label)
        box.append(scroll)
        self._desc_view = view
        return box, view

    def _populate_from_task(self, task) -> None:
        if not task:
            return
        self._title_entry[1].set_text(task.title)
        self._desc_view.get_buffer().set_text(task.description or "")
        if task.deadline:
            self._deadline_entry[1].set_text(task.deadline.strftime("%Y-%m-%d %H:%M"))
        self._priority_buttons[task.priority].set_active(True)

    def _on_priority_toggled(self, btn: Gtk.ToggleButton, prio: Priority) -> None:
        if btn.get_active():
            self._selected_priority = prio

    def _on_confirm(self, _btn) -> None:
        title = self._title_entry[1].get_text().strip()
        if not title:
            self._title_entry[1].add_css_class("error")
            return

        buf   = self._desc_view.get_buffer()
        desc  = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False).strip()
        deadline = self._parse_deadline(self._deadline_entry[1].get_text().strip())

        self._result = {
            "title":       title,
            "description": desc,
            "priority":    self._selected_priority,
            "deadline":    deadline,
        }
        self.close()

    def _parse_deadline(self, raw: str) -> Optional[datetime]:
        if not raw:
            return None
        for fmt in _DEADLINE_FORMATS:
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
        return None  # silently ignore invalid input — entry has no red state yet
