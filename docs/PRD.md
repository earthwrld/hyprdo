# HyprDo — Product Requirements Document (PRD)

> **Version**: 0.2.0-draft  
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
- **Theme-aware** — auto-detect color scheme: HyDE dcols, pywal, atau built-in dark (universal, bukan HyDE-only)
- **Full-featured** tapi tetap ringan dan non-bloat
- **Bisa dikontrol via CLI** — sehingga AI agent (AGY/Claude) bisa add task langsung dari terminal

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
- Theme-aware dengan **auto-detection**: HyDE dcols → pywal → built-in dark (works untuk semua Hyprland user)
- Full-featured: priority, deadline, notifikasi, subtask
- Data tersimpan lokal (SQLite)
- **CLI interface** — bisa dipakai dari terminal maupun oleh AI agent (AGY/Claude)
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

- **Auto-detect theme** dengan urutan prioritas:
  1. **HyDE dcols** (primary): `~/.cache/hyde/dcols/<hash>.dcol` — untuk HyDE users
  2. **pywal** (fallback): `~/.cache/wal/colors.json` — untuk non-HyDE Hyprland users
  3. **Built-in dark theme** (fallback akhir): hardcoded palette yang tetap keren
- App bisa dipakai oleh **semua pengguna Hyprland**, tidak harus pakai HyDE
- Animasi: fade in/out saat toggle
- Modern glassmorphism look

### 5.5 CLI Interface (AI Agent Integration)

HyprDo menyediakan CLI sehingga AI agent (AGY CLI, Claude Code) bisa mengontrol app langsung dari terminal.

```bash
# Tambah task baru
hyprdo add "judul task" --priority high --deadline "2026-07-20"
hyprdo add "belajar GTK4" --priority medium

# Lihat semua task pending
hyprdo list
hyprdo list --priority high
hyprdo list --format json

# Mark selesai
hyprdo done <id>

# Hapus task
hyprdo delete <id>

# Toggle window
hyprdo show
hyprdo hide
hyprdo toggle

# Output JSON untuk Waybar
hyprdo status
# → {"text": "󰄲 5", "tooltip": "High: fix login bug", "class": "has-tasks"}
```

**Contoh penggunaan dengan AGY:**
> _"AGY, tambah task: pelajari GTK4 dengan priority medium deadline minggu depan"_
> → AGY menjalankan: `hyprdo add "pelajari GTK4" --priority medium --deadline "2026-07-22"`
> → Task langsung muncul di app ✅

---

## 6. Technical Requirements

### Stack
| Layer | Teknologi |
|---|---|
| Language | Python 3.11+ |
| UI Framework | GTK4 + libadwaita |
| Database | SQLite (via `sqlite3` stdlib) |
| CLI | `argparse` (stdlib) atau `typer` |
| Notification | `libnotify` / `notify-send` |
| Theme | Auto-detect: HyDE dcols → pywal → built-in dark |
| Waybar | Custom `custom/` module (`hyprdo status`) |
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
│   │   ├── main.py         ← entry point (GUI)
│   │   ├── cli.py          ← CLI entry point (argparse/typer)
│   │   ├── database.py     ← SQLite layer (shared oleh GUI & CLI)
│   │   ├── models.py       ← data models
│   │   ├── ui/
│   │   │   ├── window.py   ← main window
│   │   │   ├── task_row.py ← task list item widget
│   │   │   └── dialogs.py  ← add/edit task dialog
│   │   ├── notifier.py     ← libnotify integration
│   │   └── theme.py        ← HyDE dcols / pywal color reader
├── waybar/
│   └── hyprdo.json     ← Waybar module config snippet
├── hyprland/
│   └── hyprdo.conf     ← Hyprland keybind + window rules
├── assets/
│   └── icons/
├── README.md
└── pyproject.toml      ← scripts: hyprdo = hyprdo.cli:main
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
| US-09 | Sebagai user, tampilan app mengikuti color scheme sistem saya (HyDE/pywal/built-in) otomatis | Medium |
| US-10 | Sebagai user, saya bisa filter task berdasarkan label/kategori | Medium |
| US-11 | Sebagai user, saya bisa sort task berdasarkan priority/deadline | Medium |
| US-12 | Sebagai user (atau AGY), saya bisa `hyprdo add` task dari terminal | High |
| US-13 | Sebagai user (atau AGY), saya bisa `hyprdo list` untuk lihat task pending | High |
| US-14 | Sebagai user (atau AGY), saya bisa `hyprdo done <id>` untuk mark selesai | High |
| US-15 | Sebagai user, `hyprdo status` output JSON yang bisa dibaca Waybar | High |

---

## 8. Milestones

| Milestone | Deliverables | Status |
|---|---|---|
| M0 — Setup | Repo init, PRD, ERD, Wireframe | 🔄 In Progress |
| M1 — Core | Database layer, models, basic CRUD | ⏳ Pending |
| M2 — CLI | CLI interface (`add`, `list`, `done`, `delete`, `status`) | ⏳ Pending |
| M3 — GUI | GTK4 window, task list, add/edit dialog | ⏳ Pending |
| M4 — Features | Priority, deadline, subtask, notifikasi | ⏳ Pending |
| M5 — Integration | Waybar module, Hyprland scratchpad, hotkey | ⏳ Pending |
| M6 — Polish | HyDE dcols theming, animasi, packaging | ⏳ Pending |
| M7 — Release | README lengkap, install script, distribusi | ⏳ Pending |

---

## 9. Inspiration & References

- [WeekToDo](https://github.com/manuelernestog/weektodo) — minimalis, privacy-first, open source weekly planner
- [HyDE](https://github.com/HyDE-Project/HyDE) — Hyprland dotfiles framework
- [HyDE dcols](https://github.com/HyDE-Project/HyDE) — wallpaper-based color palette system yang dipakai di setup ini
- [pywal](https://github.com/dylanaraps/pywal) — color scheme dari wallpaper (fallback)
- [Waybar docs](https://github.com/Alexays/Waybar/wiki) — custom module integration
