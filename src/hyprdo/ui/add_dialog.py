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

from .. import database as db
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
        self._selected_label_ids: set[int] = set(l.id for l in task.labels) if task else set()
        self._new_subtasks: list[str] = []
        self._deleted_subtask_ids: set[int] = set()

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

        if self._task:
            del_btn = Gtk.Button(label="Delete Task", css_classes=["destructive-action"])
            del_btn.connect("clicked", self._on_delete_task)
            bar.pack_start(del_btn)

        label = "Save Changes" if self._task else "Add Task"
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
        self._deadline_entry = self._build_deadline_row()
        labels_row        = self._build_labels_row()
        subtasks_row      = self._build_subtasks_row()

        box.append(self._title_entry[0])
        box.append(self._desc_entry[0])
        box.append(priority_row)
        box.append(self._deadline_entry)
        box.append(labels_row)
        box.append(subtasks_row)
        return box

    def _build_priority_row(self) -> Gtk.Box:
        label = Gtk.Label(label="Priority", xalign=0, css_classes=["task-meta"])
        row   = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        pills = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self._priority_buttons: dict[Priority, Gtk.ToggleButton] = {}
        first = None
        for text, prio, css in _PRIORITY_OPTIONS:
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            box.append(Gtk.Label(label="●", css_classes=[css]))
            box.append(Gtk.Label(label=text))
            
            btn = Gtk.ToggleButton(child=box, css_classes=["priority-pill"])
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

    def _build_deadline_row(self) -> Gtk.Box:
        label = Gtk.Label(label="Deadline", xalign=0, css_classes=["task-meta"])
        
        entry = Gtk.Entry(placeholder_text="YYYY-MM-DD HH:MM  (optional)", hexpand=True)
        self._deadline_entry_widget = entry

        cal_btn = Gtk.MenuButton(icon_name="calendar-symbolic")
        popover = Gtk.Popover()
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        calendar = Gtk.Calendar()
        
        time_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        time_box.append(Gtk.Label(label="Time:"))
        self._hour_spin = Gtk.SpinButton.new_with_range(0, 23, 1)
        self._hour_spin.set_value(12)
        self._min_spin = Gtk.SpinButton.new_with_range(0, 59, 1)
        self._min_spin.set_value(0)
        time_box.append(self._hour_spin)
        time_box.append(Gtk.Label(label=":"))
        time_box.append(self._min_spin)
        
        apply_btn = Gtk.Button(label="Set Deadline")
        vbox.append(calendar)
        vbox.append(time_box)
        vbox.append(apply_btn)
        popover.set_child(vbox)
        
        def on_apply(_btn):
            date = calendar.get_date()
            h = int(self._hour_spin.get_value())
            m = int(self._min_spin.get_value())
            entry.set_text(date.format("%Y-%m-%d") + f" {h:02d}:{m:02d}")
            popover.popdown()
            
        apply_btn.connect("clicked", on_apply)
        cal_btn.set_popover(popover)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        hbox.append(entry)
        hbox.append(cal_btn)

        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        row.append(label)
        row.append(hbox)
        return row

    def _build_labels_row(self) -> Gtk.Box:
        label = Gtk.Label(label="Labels", xalign=0, css_classes=["task-meta"])
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        
        self._labels_flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE)
        self._labels_flow.set_max_children_per_line(5)
        
        for db_label in db.list_labels():
            btn = Gtk.ToggleButton(label=f"+ {db_label.name}", css_classes=["label-pill"])
            if db_label.id in self._selected_label_ids:
                btn.set_active(True)
            btn.connect("toggled", self._on_label_toggled, db_label.id)
            self._labels_flow.insert(btn, -1)
        
        add_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self._new_label_entry = Gtk.Entry(placeholder_text="New label...", has_frame=False)
        self._new_label_entry.connect("activate", self._on_new_label_activate)
        add_box.append(Gtk.Image(icon_name="list-add-symbolic"))
        add_box.append(self._new_label_entry)

        row.append(label)
        row.append(self._labels_flow)
        row.append(add_box)
        return row

    def _build_subtasks_row(self) -> Gtk.Box:
        label = Gtk.Label(label="Subtasks", xalign=0, css_classes=["task-meta"])
        self._subtasks_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, css_classes=["background"])
        
        # Entry to add new subtask
        entry_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        add_icon = Gtk.Image(icon_name="list-add-symbolic")
        self._subtask_entry = Gtk.Entry(placeholder_text="Add subtask... (Press Enter)", hexpand=True, has_frame=False)
        self._subtask_entry.connect("activate", self._on_subtask_entry_activate)
        
        entry_row.append(add_icon)
        entry_row.append(self._subtask_entry)
        
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        row.append(label)
        row.append(self._subtasks_list)
        row.append(entry_row)
        return row

    def _add_subtask_row_ui(self, title: str, subtask_id: Optional[int] = None) -> None:
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.append(Gtk.Label(label=title, hexpand=True, xalign=0))
        
        del_btn = Gtk.Button(icon_name="window-close-symbolic", css_classes=["flat"])
        def on_delete(_btn):
            if subtask_id is not None:
                self._deleted_subtask_ids.add(subtask_id)
            else:
                if title in self._new_subtasks:
                    self._new_subtasks.remove(title)
            self._subtasks_list.remove(row)
        
        del_btn.connect("clicked", on_delete)
        box.append(del_btn)
        row.set_child(box)
        self._subtasks_list.append(row)

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
            self._deadline_entry_widget.set_text(task.deadline.strftime("%Y-%m-%d %H:%M"))
        self._priority_buttons[task.priority].set_active(True)
        for subtask in task.subtasks:
            self._add_subtask_row_ui(subtask.title, subtask.id)

    def _on_label_toggled(self, btn: Gtk.ToggleButton, label_id: int) -> None:
        if btn.get_active():
            self._selected_label_ids.add(label_id)
        else:
            self._selected_label_ids.discard(label_id)

    def _on_new_label_activate(self, entry: Gtk.Entry) -> None:
        name = entry.get_text().strip()
        if name:
            new_lbl = db.create_label(name)
            self._selected_label_ids.add(new_lbl.id)
            
            btn = Gtk.ToggleButton(label=f"+ {new_lbl.name}", css_classes=["label-pill"])
            btn.set_active(True)
            btn.connect("toggled", self._on_label_toggled, new_lbl.id)
            
            self._labels_flow.insert(btn, -1)
            entry.set_text("")

    def _on_subtask_entry_activate(self, entry: Gtk.Entry) -> None:
        text = entry.get_text().strip()
        if text:
            self._new_subtasks.append(text)
            self._add_subtask_row_ui(text, None)
            entry.set_text("")

    def _on_delete_task(self, _btn) -> None:
        self._result = {"delete_task": True}
        self.close()

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
        
        deadline = self._deadline_entry_widget.get_text().strip()
        parsed_dt = None
        if deadline:
            for fmt in _DEADLINE_FORMATS:
                try:
                    parsed_dt = datetime.strptime(deadline, fmt)
                    break
                except ValueError:
                    pass

        unsubmitted_subtask = self._subtask_entry.get_text().strip()
        if unsubmitted_subtask:
            self._new_subtasks.append(unsubmitted_subtask)

        unsubmitted_label = self._new_label_entry.get_text().strip()
        if unsubmitted_label:
            new_lbl = db.create_label(unsubmitted_label)
            self._selected_label_ids.add(new_lbl.id)

        self._result = {
            "title": title,
            "description": desc or None,
            "deadline": parsed_dt,
            "priority": self._selected_priority,
            "labels": list(self._selected_label_ids),
            "new_subtasks": self._new_subtasks,
            "deleted_subtask_ids": self._deleted_subtask_ids,
            "delete_task": False,
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
