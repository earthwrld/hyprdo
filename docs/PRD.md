# HyprDo — Product Requirements Document (PRD)

> **Version**: 0.1.0-draft  
> **Author**: boemi  
> **Created**: 2026-07-15  
> **Status**: Draft

---

## 1. Overview

**HyprDo** adalah aplikasi to-do list modern yang dibuat khusus untuk pengguna **Hyprland** di Linux (terutama CachyOS + HyDE). Diinspirasi oleh [WeekToDo](https://github.com/manuelernestog/weektodo) yang minimalis dan privacy-first, HyprDo mengambil pendekatan yang lebih native dan terintegrasi penuh ke dalam ekosistem Wayland/Hyprland.

### Tagline
> _"Tasks that live where you work — your desktop."_

---

## 2. Problem Statement

Pengguna Hyprland yang produktif tidak memiliki to-do list yang:
- **Terintegrasi native** dengan Waybar (bukan web app, bukan Electron)
- **Toggle show/hide** seamlessly dari Waybar atau keyboard shortcut
- **Theme-aware** — mengikuti color scheme pywal/HyDE secara otomatis
- **Full-featured** tapi tetap ringan dan non-bloat

Alternatif yang ada:
| App | Masalah |
|---|---|
| GNOME Todo | Tidak cocok di Hyprland, butuh GNOME stack |
| Todoist/TickTick | Butuh internet, cloud-based |
| WeekToDo | Electron-based, berat, tidak bisa integrasi Waybar |
| Rofi scripts | Terlalu minimalis, tidak support subtask/deadline |

---

## 3. Goals & Non-Goals

### Goals ✅
- Aplikasi GTK4 native yang ringan dan cepat
- Integrasi penuh dengan Waybar sebagai custom module
- Toggle via klik icon Waybar dan keyboard shortcut Hyprland
- Theme-aware menggunakan pywal color scheme
- Full-featured: priority, deadline, notifikasi, subtask
- Data tersimpan lokal (SQLite)
- Dapat di-share / didistribusikan ke pengguna Hyprland lain

### Non-Goals ❌
- Tidak ada sync cloud / akun
- Tidak ada kolaborasi multi-user
- Tidak ada mobile app (fokus desktop Linux)
- Tidak ada integrasi kalender eksternal (untuk v1)

---

## 4. Target Users

- Pengguna **CachyOS / Arch Linux** dengan Hyprland
- Pengguna **HyDE** (Hyde dotfiles framework)
- Pengguna Linux yang peduli estetika desktop tapi juga butuh produktivitas

---

## 5. Feature Requirements

### 5.1 Core Features (MVP — v1.0)

#### Task Management
- [ ] Tambah task baru (judul, deskripsi opsional)
- [ ] Edit task yang sudah ada
- [ ] Hapus task
- [ ] Mark task sebagai selesai / belum selesai
- [ ] Urutkan berdasarkan priority / deadline / created date

#### Priority
- 🔴 High
- 🟡 Medium
- 🟢 Low
- ⚪ None (default)

#### Deadline
- Pilih tanggal dan waktu
- Tampilkan indikator "overdue" jika sudah lewat deadline
- Tampilkan "due today", "due tomorrow" badge

#### Subtask
- Setiap task bisa punya list subtask
- Subtask bisa di-check/uncheck independen
- Progress bar menunjukkan % subtask selesai

#### Notifikasi
- Reminder otomatis via `libnotify` (`notify-send`)
- Notifikasi H-1 jam sebelum deadline
- Notifikasi H-5 menit sebelum deadline

#### Categories / Labels
- Tag task dengan label warna
- Filter view berdasarkan label

### 5.2 Waybar Integration

- Custom module yang menampilkan: **icon + jumlah task pending**
- Klik kiri icon → toggle show/hide app window
- Tooltip menampilkan: task paling urgent yang aktif
- Update otomatis setiap 30 detik (atau trigger saat ada perubahan)

### 5.3 Hyprland Integration

- Window terdaftar sebagai **scratchpad** (`hyprctl dispatch togglespecialworkspace`)
- Keyboard shortcut default: `Super + T`
- Window bersifat floating, centered, tidak punya border berlebih

### 5.4 Theme / Appearance

- **pywal-aware**: baca file `~/.cache/wal/colors.json` untuk color scheme
- Fallback: built-in dark theme jika pywal tidak ada
- Animasi: fade in/out saat toggle
- Modern glassmorphism look

---

## 6. Technical Requirements

### Stack
| Layer | Teknologi |
|---|---|
| Language | Python 3.11+ |
| UI Framework | GTK4 + libadwaita |
| Database | SQLite (via `sqlite3` stdlib) |
| Notification | `libnotify` / `notify-send` |
| Theme | pywal (`~/.cache/wal/colors.json`) |
| Waybar | Custom `custom/` module (JSON output) |
| Packaging | (future) AUR package / install script |

### File Structure (planned)
```
hyprdo/
├── docs/
│   ├── PRD.md          ← dokumen ini
│   ├── ERD.md          ← entity relationship diagram
│   └── WIREFRAME.md    ← wireframe / UI spec
├── src/
│   ├── hyprdo/
│   │   ├── __init__.py
│   │   ├── main.py         ← entry point
│   │   ├── database.py     ← SQLite layer
│   │   ├── models.py       ← data models
│   │   ├── ui/
│   │   │   ├── window.py   ← main window
│   │   │   ├── task_row.py ← task list item widget
│   │   │   └── dialogs.py  ← add/edit task dialog
│   │   ├── notifier.py     ← libnotify integration
│   │   └── theme.py        ← pywal color reader
├── waybar/
│   ├── hyprdo.sh       ← Waybar module script
│   └── hyprdo.json     ← Waybar module config snippet
├── hyprland/
│   └── hyprdo.conf     ← Hyprland keybind + window rules
├── assets/
│   └── icons/
├── README.md
└── pyproject.toml
```

---

## 7. User Stories

| ID | Story | Priority |
|---|---|---|
| US-01 | Sebagai user, saya bisa melihat icon HyprDo di Waybar dengan jumlah task pending | High |
| US-02 | Sebagai user, saya bisa mengklik icon di Waybar untuk toggle show/hide app | High |
| US-03 | Sebagai user, saya bisa tekan `Super+T` untuk toggle app | High |
| US-04 | Sebagai user, saya bisa menambah task baru dengan judul dan deskripsi | High |
| US-05 | Sebagai user, saya bisa set priority (High/Medium/Low) untuk task | High |
| US-06 | Sebagai user, saya bisa set deadline tanggal + waktu untuk task | High |
| US-07 | Sebagai user, saya bisa menambah subtask ke dalam sebuah task | High |
| US-08 | Sebagai user, saya mendapat notifikasi desktop sebelum deadline | High |
| US-09 | Sebagai user, tampilan app mengikuti color scheme wallpaper saya (pywal) | Medium |
| US-10 | Sebagai user, saya bisa filter task berdasarkan label/kategori | Medium |
| US-11 | Sebagai user, saya bisa sort task berdasarkan priority/deadline | Medium |

---

## 8. Milestones

| Milestone | Deliverables | Status |
|---|---|---|
| M0 — Setup | Repo init, PRD, ERD, Wireframe | 🔄 In Progress |
| M1 — Core | Database layer, basic CRUD UI | ⏳ Pending |
| M2 — Features | Priority, deadline, subtask, notif | ⏳ Pending |
| M3 — Integration | Waybar module, Hyprland scratchpad, hotkey | ⏳ Pending |
| M4 — Polish | Theming pywal, animasi, packaging | ⏳ Pending |
| M5 — Release | README lengkap, install script, distribusi | ⏳ Pending |

---

## 9. Inspiration & References

- [WeekToDo](https://github.com/manuelernestog/weektodo) — minimalis, privacy-first, open source weekly planner
- [HyDE](https://github.com/HyDE-Project/HyDE) — Hyprland dotfiles framework
- [pywal](https://github.com/dylanaraps/pywal) — color scheme dari wallpaper
- [Waybar docs](https://github.com/Alexays/Waybar/wiki) — custom module integration
