# HyprDo — Entity Relationship Diagram (ERD)

> **Version**: 0.1.0  
> **Author**: boemi  
> **Created**: 2026-07-15  
> **Status**: Draft

---

## 1. Entity Overview

HyprDo menyimpan semua data secara lokal di SQLite (`~/.local/share/hyprdo/hyprdo.db`).

Terdapat **5 entitas utama**:

| Entity | Deskripsi |
|---|---|
| `tasks` | Task utama (judul, deskripsi, priority, deadline, status) |
| `subtasks` | Child task dari sebuah task |
| `labels` | Label/tag warna yang bisa ditempel ke task |
| `task_labels` | Junction table — relasi many-to-many antara task dan label |
| `reminders` | Reminder notifikasi yang terikat ke task |

---

## 2. ERD Diagram

```
┌─────────────────────────────────┐
│              tasks              │
├─────────────────────────────────┤
│ id          INTEGER PK          │
│ title       TEXT NOT NULL       │
│ description TEXT                │
│ priority    TEXT DEFAULT 'none' │  → 'high' | 'medium' | 'low' | 'none'
│ status      TEXT DEFAULT 'todo' │  → 'todo' | 'done'
│ deadline    TEXT                │  → ISO 8601: "2026-07-20T15:00:00"
│ created_at  TEXT NOT NULL       │  → ISO 8601
│ updated_at  TEXT NOT NULL       │  → ISO 8601
│ done_at     TEXT                │  → ISO 8601, null jika belum selesai
│ position    INTEGER DEFAULT 0   │  → untuk drag & drop reorder
└──────────┬──────────────────────┘
           │
           │ 1 ──< n
           │
┌──────────▼──────────────────────┐      ┌──────────────────────────┐
│            subtasks             │      │          labels           │
├─────────────────────────────────┤      ├──────────────────────────┤
│ id          INTEGER PK          │      │ id    INTEGER PK          │
│ task_id     INTEGER FK → tasks  │      │ name  TEXT NOT NULL       │
│ title       TEXT NOT NULL       │      │ color TEXT NOT NULL       │  → hex: "#ff5555"
│ is_done     INTEGER DEFAULT 0   │      │                          │
│ position    INTEGER DEFAULT 0   │      └────────────┬─────────────┘
│ created_at  TEXT NOT NULL       │                   │
└─────────────────────────────────┘                   │ n
                                                       │
                                    ┌──────────────────▼───────────────────┐
                                    │             task_labels               │
                                    ├───────────────────────────────────────┤
                                    │ task_id   INTEGER FK → tasks          │
                                    │ label_id  INTEGER FK → labels         │
                                    │ PRIMARY KEY (task_id, label_id)       │
                                    └───────────────────────────────────────┘
           │
           │ 1 ──< n
           │
┌──────────▼──────────────────────┐
│            reminders            │
├─────────────────────────────────┤
│ id          INTEGER PK          │
│ task_id     INTEGER FK → tasks  │
│ remind_at   TEXT NOT NULL       │  → ISO 8601
│ is_sent     INTEGER DEFAULT 0   │  → 0 = belum, 1 = sudah dikirim
│ created_at  TEXT NOT NULL       │
└─────────────────────────────────┘
```

---

## 3. Detail Tabel

### 3.1 `tasks`

```sql
CREATE TABLE tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    description TEXT,
    priority    TEXT    NOT NULL DEFAULT 'none'
                        CHECK(priority IN ('high', 'medium', 'low', 'none')),
    status      TEXT    NOT NULL DEFAULT 'todo'
                        CHECK(status IN ('todo', 'done')),
    deadline    TEXT,                          -- ISO 8601 atau NULL
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    done_at     TEXT,                          -- diisi saat status → 'done'
    position    INTEGER NOT NULL DEFAULT 0     -- urutan tampilan
);
```

### 3.2 `subtasks`

```sql
CREATE TABLE subtasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    title       TEXT    NOT NULL,
    is_done     INTEGER NOT NULL DEFAULT 0 CHECK(is_done IN (0, 1)),
    position    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
```

### 3.3 `labels`

```sql
CREATE TABLE labels (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL UNIQUE,
    color TEXT NOT NULL DEFAULT '#bd93f9'   -- hex color
);
```

Seed data default (warna dracula-inspired, cocok dengan pywal):

| name | color |
|---|---|
| work | #ff5555 |
| personal | #50fa7b |
| study | #8be9fd |
| urgent | #ffb86c |

### 3.4 `task_labels` (junction table)

```sql
CREATE TABLE task_labels (
    task_id  INTEGER NOT NULL REFERENCES tasks(id)  ON DELETE CASCADE,
    label_id INTEGER NOT NULL REFERENCES labels(id) ON DELETE CASCADE,
    PRIMARY KEY (task_id, label_id)
);
```

### 3.5 `reminders`

```sql
CREATE TABLE reminders (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id    INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    remind_at  TEXT    NOT NULL,               -- ISO 8601
    is_sent    INTEGER NOT NULL DEFAULT 0 CHECK(is_sent IN (0, 1)),
    created_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);
```

---

## 4. Relasi Summary

```
tasks (1) ──────────── (n) subtasks
      (1) ──────────── (n) reminders
      (n) ──── task_labels ──── (n) labels
```

| Relasi | Type | On Delete |
|---|---|---|
| tasks → subtasks | One-to-Many | CASCADE |
| tasks → reminders | One-to-Many | CASCADE |
| tasks ↔ labels | Many-to-Many (via task_labels) | CASCADE |

---

## 5. Auto-generated Reminders Logic

Saat user set `deadline` pada task, sistem otomatis buat 2 reminder:

```
deadline - 1 jam   → reminder pertama
deadline - 5 menit → reminder kedua
```

Reminder daemon (`notifier.py`) query reminders yang `is_sent = 0` dan `remind_at <= now()` setiap 1 menit, lalu kirim notifikasi via `notify-send`.

---

## 6. `hyprdo status` JSON Output (untuk Waybar)

Query yang dijalankan:
```sql
SELECT COUNT(*) FROM tasks WHERE status = 'todo';
SELECT title FROM tasks 
WHERE status = 'todo' AND priority = 'high' 
ORDER BY deadline ASC NULLS LAST 
LIMIT 1;
```

Output format:
```json
{
  "text": "󰄲 5",
  "tooltip": "High: fix login bug (due: 2026-07-16 15:00)",
  "class": "has-tasks",
  "percentage": 0
}
```

Jika tidak ada task: `{"text": "󰄲", "tooltip": "No pending tasks", "class": "no-tasks"}`

---

## 7. Index

```sql
-- Untuk query list task yang sering dipakai
CREATE INDEX idx_tasks_status   ON tasks(status);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_deadline ON tasks(deadline);

-- Untuk reminder daemon
CREATE INDEX idx_reminders_sent_at ON reminders(is_sent, remind_at);

-- Untuk subtask per task
CREATE INDEX idx_subtasks_task_id ON subtasks(task_id);
```
