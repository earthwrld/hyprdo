"""
HyprDo — Toggle script for Waybar/Keybinds.

Checks if the main window is running. If so, kills it (hide).
If not, launches it (show).
"""

import json
import subprocess
import sys

_APP_ID = "io.github.earthwrld.hyprdo"


def main() -> None:
    # Check if window is open via hyprctl
    try:
        out = subprocess.check_output(["hyprctl", "clients", "-j"], text=True)
        clients = json.loads(out)
    except Exception:
        # Fallback if hyprctl fails
        clients = []

    is_running = any(c.get("class") == _APP_ID or c.get("initialClass") == _APP_ID for c in clients)

    if is_running:
        # Kill all instances gracefully
        subprocess.run(["killall", "-q", "hyprdo-gui"], check=False)
    else:
        # Launch detached
        subprocess.Popen(
            ["hyprdo-gui"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )


if __name__ == "__main__":
    main()
