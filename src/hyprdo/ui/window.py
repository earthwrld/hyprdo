"""
HyprDo — Main application window.

Single responsibility: orchestrate the main UI layout and task list.
Delegates task display to TaskRow, task creation to AddTaskDialog.
"""

from __future__ import annotations

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from .. import database as db
from ..models import Priority, TaskStatus
from .add_dialog import AddTaskDialog
from .task_row import TaskRow

_FILTERS = [
    ("All",           None,              None),
    ("Today",         TaskStatus.TODO,   "today"),
    ("High Priority", TaskStatus.TODO,   Priority.HIGH),
]


class HyprDoWindow(Adw.ApplicationWindow):
    """Main HyprDo floating window."""

    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app, title="HyprDo", default_width=440, default_height=620)
        self._active_filter_index = 0

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content.append(self._build_headerbar())
        content.append(self._build_filter_bar())
        content.append(self._build_task_list())
        content.append(self._build_footer())
        self.set_content(content)

        self.refresh()

    # ------------------------------------------------------------------
    # UI construction — newspaper metaphor: high-level → details
    # ------------------------------------------------------------------

    def _build_headerbar(self) -> Adw.HeaderBar:
        bar = Adw.HeaderBar()
        bar.set_title_widget(Gtk.Label(label="HyprDo", css_classes=["title"]))

        add_btn = Gtk.Button(label="+ New", css_classes=["add-btn"])
        add_btn.connect("clicked", self._on_add_clicked)
        bar.pack_end(add_btn)
        return bar

    def _build_filter_bar(self) -> Gtk.Box:
        bar = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=6,
            css_classes=["filter-bar"],
        )
        self._filter_buttons: list[Gtk.ToggleButton] = []
        first = None

        for i, (label, *_) in enumerate(_FILTERS):
            btn = Gtk.ToggleButton(label=label, css_classes=["filter-btn"])
            if first:
                btn.set_group(first)
            else:
                first = btn
                btn.set_active(True)
            btn.connect("toggled", self._on_filter_toggled, i)
            self._filter_buttons.append(btn)
            bar.append(btn)

        return bar

    def _build_task_list(self) -> Gtk.ScrolledWindow:
        self._list_box = Gtk.ListBox(
            selection_mode=Gtk.SelectionMode.NONE,
            css_classes=["background"],
            show_separators=False,
        )
        scroll = Gtk.ScrolledWindow(
            child=self._list_box,
            vexpand=True,
            hscrollbar_policy=Gtk.PolicyType.NEVER,
        )
        return scroll

    def _build_footer(self) -> Gtk.Label:
        self._footer = Gtk.Label(css_classes=["footer-label"])
        return self._footer

    # ------------------------------------------------------------------
    # Task list management
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Reload tasks from DB and rebuild the list."""
        self._clear_list()
        tasks = self._fetch_filtered_tasks()
        for task in tasks:
            self._list_box.append(TaskRow(task, on_changed=self.refresh))
        self._update_footer()

    def _clear_list(self) -> None:
        while row := self._list_box.get_first_child():
            self._list_box.remove(row)

    def _fetch_filtered_tasks(self):
        _, status, extra = _FILTERS[self._active_filter_index]

        if self._active_filter_index == 0:  # All
            return db.list_tasks(status=TaskStatus.TODO)

        if self._active_filter_index == 1:  # Today
            all_todo = db.list_tasks(status=TaskStatus.TODO)
            return [t for t in all_todo if t.is_due_today]

        if self._active_filter_index == 2:  # High Priority
            return db.list_tasks(status=TaskStatus.TODO, priority=Priority.HIGH)

        return db.list_tasks(status=TaskStatus.TODO)

    def _update_footer(self) -> None:
        pending = len(db.list_tasks(status=TaskStatus.TODO, include_subtasks=False))
        done    = len(db.list_tasks(status=TaskStatus.DONE, include_subtasks=False))
        self._footer.set_label(f"{pending} pending · {done} done")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_add_clicked(self, _btn: Gtk.Button) -> None:
        dialog = AddTaskDialog(parent=self)
        dialog.connect("close-request", self._on_dialog_closed, dialog)
        dialog.present()

    def _on_dialog_closed(self, _dialog, dialog: AddTaskDialog) -> None:
        if not dialog.result:
            return
        db.create_task(
            title=dialog.result["title"],
            description=dialog.result["description"],
            priority=dialog.result["priority"],
            deadline=dialog.result["deadline"],
        )
        self.refresh()

    def _on_filter_toggled(self, btn: Gtk.ToggleButton, index: int) -> None:
        if btn.get_active():
            self._active_filter_index = index
            self.refresh()
