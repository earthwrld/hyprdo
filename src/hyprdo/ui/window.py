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
        self._active_sort = "created"  # can be: priority, deadline, created

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
        # Clear default center title widget
        bar.set_title_widget(Gtk.Box())

        # Left side: App icon + Title
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title_box.set_margin_start(8)
        
        icon = Gtk.Image(icon_name="view-list-symbolic")
        # Scale icon slightly larger
        icon.set_pixel_size(24)
        
        title_lbl = Gtk.Label(label="HyprDo", css_classes=["title", "heading"])
        title_lbl.set_halign(Gtk.Align.START)
        
        title_box.append(icon)
        title_box.append(title_lbl)
        bar.pack_start(title_box)

        # Right side: Add button
        add_btn = Gtk.Button(icon_name="list-add-symbolic", css_classes=["add-btn", "suggested-action"])
        add_btn.connect("clicked", self._on_add_clicked)
        bar.pack_end(add_btn)

        # Right side: Sort Dropdown
        sort_btn = Gtk.MenuButton(icon_name="view-sort-descending-symbolic", css_classes=["flat"])
        sort_popover = Gtk.Popover()
        sort_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        
        for sort_key, sort_label in [("priority", "Sort by Priority"), 
                                     ("deadline", "Sort by Deadline"), 
                                     ("created", "Sort by Created")]:
            btn = Gtk.Button(label=sort_label, css_classes=["flat"])
            btn.connect("clicked", self._on_sort_clicked, sort_key, sort_popover)
            sort_box.append(btn)
            
        sort_popover.set_child(sort_box)
        sort_btn.set_popover(sort_popover)
        
        bar.pack_end(sort_btn)
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
        self._list_box.connect("row-activated", self._on_task_row_activated)
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
        tasks = []

        if self._active_filter_index == 0:  # All
            tasks = db.list_tasks(status=TaskStatus.TODO)

        elif self._active_filter_index == 1:  # Today
            all_todo = db.list_tasks(status=TaskStatus.TODO)
            tasks = [t for t in all_todo if t.is_due_today]

        elif self._active_filter_index == 2:  # High Priority
            tasks = db.list_tasks(status=TaskStatus.TODO, priority=Priority.HIGH)
            
        # Apply sorting
        if self._active_sort == "priority":
            # Priority: HIGH (1) -> MEDIUM (2) -> LOW (3) -> NONE (0)
            # We want High first. Let's map them to 0, 1, 2, 3
            def prio_sort(t):
                if t.priority == Priority.HIGH: return 0
                if t.priority == Priority.MEDIUM: return 1
                if t.priority == Priority.LOW: return 2
                return 3
            tasks.sort(key=prio_sort)
        elif self._active_sort == "deadline":
            import datetime
            def deadline_sort(t):
                # tasks without deadline go to the end
                return t.deadline or datetime.datetime.max
            tasks.sort(key=deadline_sort)
        elif self._active_sort == "created":
            tasks.sort(key=lambda t: t.created_at, reverse=True)

        return tasks

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

    def _on_task_row_activated(self, listbox: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        dialog = AddTaskDialog(parent=self, task=row._task)
        dialog.connect("close-request", self._on_dialog_closed, dialog)
        dialog.present()

    def _on_dialog_closed(self, _dialog, dialog: AddTaskDialog) -> None:
        res = dialog.result
        if not res:
            return
            
        if res.get("delete_task"):
            db.delete_task(dialog._task.id)
            self.refresh()
            return
            
        if dialog._task:
            task_id = dialog._task.id
            db.update_task(
                task_id,
                title=res["title"],
                description=res["description"],
                priority=res["priority"],
                deadline=res["deadline"],
            )
            # Sync labels
            old_labels = set(l.id for l in dialog._task.labels)
            new_labels = set(res["labels"])
            for l_id in old_labels - new_labels:
                db.detach_label(task_id, l_id)
            for l_id in new_labels - old_labels:
                db.attach_label(task_id, l_id)
                
            # Sync subtasks
            for s_id in res.get("deleted_subtask_ids", []):
                db.delete_subtask(s_id)
            for title in res.get("new_subtasks", []):
                db.add_subtask(task_id, title)
        else:
            task = db.create_task(
                title=res["title"],
                description=res["description"],
                priority=res["priority"],
                deadline=res["deadline"],
            )
            for label_id in res.get("labels", []):
                db.attach_label(task.id, label_id)
            for subtask_title in res.get("new_subtasks", []):
                db.add_subtask(task.id, subtask_title)
            
        self.refresh()

    def _on_filter_toggled(self, btn: Gtk.ToggleButton, index: int) -> None:
        if btn.get_active():
            self._active_filter_index = index
            self.refresh()

    def _on_sort_clicked(self, _btn: Gtk.Button, sort_key: str, popover: Gtk.Popover) -> None:
        self._active_sort = sort_key
        self.refresh()
        popover.popdown()
