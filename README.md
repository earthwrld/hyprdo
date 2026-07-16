<div align="center">

# 🗒 HyprDo
*A native GTK4 to-do list app tailored for Hyprland with Waybar integration.*

[![Version](https://img.shields.io/badge/version-0.1.0-blue?style=flat-square)](https://github.com/earthwrld/hyprdo)
[![Python](https://img.shields.io/badge/Python->=3.11-3776AB?style=flat-square)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-blue?style=flat-square)](LICENSE)

⭐ If you find this project useful, consider giving it a star!

[Features](#features) • [Installation](#installation) • [Usage](#usage) • [Configuration](#configuration)

</div>

HyprDo is a lightweight, fully native GTK4/libadwaita to-do list application designed specifically to blend perfectly into the Hyprland ecosystem. It integrates natively with Waybar and automatically matches your system theme dynamically.

## Features

- **Native GTK4 Interface** - Built with `PyGObject` and `libadwaita` for a modern, fluid user experience.
- **Waybar Integration** - Operates as a background daemon with instant toggle capability from Waybar.
- **Dynamic Theming** - Automatically adapts to your Hyprland ecosystem colors (supports pywal and HyDE dcols out of the box).
- **Advanced Task Management**:
  - Filter and sort by priority, deadline, or creation date.
  - Subtask tracking with inline editing and progress bars.
  - Custom colored priority pills and dynamic labels.
- **Desktop Environment Aware** - Runs as a scratchpad window in Hyprland for quick access without disrupting your workflow.

## Installation

### Prerequisites

Ensure you have the following system dependencies installed:
- Python 3.11 or higher
- `gtk4` and `libadwaita`
- `gobject-introspection` (for `PyGObject` bindings)

### Setup

Clone the repository and install the application locally using `pip`:

```bash
git clone https://github.com/earthwrld/hyprdo.git
cd hyprdo
pip install .
```

For development and testing, install with the `dev` dependencies:

```bash
pip install -e .[dev]
```

## Usage

HyprDo consists of three main components:

1. **The Background Daemon**  
   Run `hyprdo-daemon` in the background to handle data persistence and dbus communication.
   ```bash
   hyprdo-daemon &
   ```

2. **The Graphical Interface**  
   Run `hyprdo-gui` to launch the main GTK4 window. If the daemon is running, this connects to the primary instance.
   ```bash
   hyprdo-gui
   ```

3. **The Waybar Module**  
   Configure Waybar to launch `hyprdo-toggle` to quickly show or hide the application scratchpad.

## Configuration

> [!NOTE]
> HyprDo relies on Hyprland window rules to function as a floating scratchpad.

Add the following to your `~/.config/hypr/hyprland.conf` or `userprefs.conf`:

```ini
windowrule {
    name = hyprdo-scratchpad
    match:class = ^(io\.github\.earthwrld\.hyprdo)$
    float = true
    pin = true
    size = 440 620
    move = 100%-460 50
    animation = slide right
}
```

This configuration ensures HyprDo always opens as a perfectly sized, floating window positioned near your taskbar or notification area.
