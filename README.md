# HyprDo 🗒️

> A native GTK4 to-do list app built for **Hyprland** — theme-aware, Waybar integrated, AI-agent friendly.

[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![GTK](https://img.shields.io/badge/GTK-4-green.svg)](https://gtk.org)
[![Wayland](https://img.shields.io/badge/Wayland-Hyprland-cyan.svg)](https://hyprland.org)

---

## ✨ Features

- 🖥️ **Native GTK4** — lightweight, no Electron, no browser
- 🎨 **HyDE/pywal theme-aware** — colors follow your wallpaper automatically
- 📌 **Waybar integration** — icon + pending task count in your bar
- ⌨️ **Toggle anywhere** — click Waybar icon or press `Super+T`
- 🤖 **AI-agent friendly CLI** — AGY/Claude can add tasks directly
- ✅ **Full-featured** — priority, deadline, subtasks, notifications

## 🚀 Quick Start

> ⚠️ This project is under active development. Installation guide coming in v1.0.

## 📖 Documentation

- [PRD — Product Requirements](docs/PRD.md)
- [ERD — Database Schema](docs/ERD.md)
- [Wireframe — UI Design](docs/WIREFRAME.md) *(coming soon)*

## 🤖 CLI Usage (for AGY/Claude)

```bash
hyprdo add "task title" --priority high --deadline "2026-07-20"
hyprdo list
hyprdo done <id>
hyprdo delete <id>
hyprdo status   # JSON output for Waybar
hyprdo toggle   # show/hide window
```

## 🏗️ Tech Stack

| Layer | Tech |
|---|---|
| Language | Python 3.11+ |
| UI | GTK4 + libadwaita |
| Database | SQLite (local) |
| CLI | typer |
| Theme | HyDE dcols / pywal |
| Notifications | libnotify |

## 📄 License

MIT © boemi
