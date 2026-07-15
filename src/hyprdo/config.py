"""HyprDo config — reads ~/.config/hyprdo/config.toml if present."""

from __future__ import annotations

import os
import tomllib  # ponytail: Python 3.11+ stdlib, no fallback needed
from pathlib import Path

CONFIG_FILE = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser() / "hyprdo" / "config.toml"
DATA_DIR    = Path(os.environ.get("XDG_DATA_HOME",   "~/.local/share")).expanduser() / "hyprdo"
DB_PATH     = DATA_DIR / "hyprdo.db"

_DEFAULTS = {
    "theme_mode":             "auto",   # auto | hyde | pywal | builtin
    "default_priority":       "none",
    "remind_before_minutes":  [60, 5],
}


def get_config() -> dict:
    """Return config dict. Falls back to defaults on any error."""
    cfg = dict(_DEFAULTS)
    if not CONFIG_FILE.exists():
        return cfg
    try:
        data = tomllib.loads(CONFIG_FILE.read_text())
        if mode := data.get("theme", {}).get("mode"):
            if mode in ("auto", "hyde", "pywal", "builtin"):
                cfg["theme_mode"] = mode
        if app := data.get("app", {}):
            if p := app.get("default_priority"):
                cfg["default_priority"] = p
            if r := app.get("remind_before_minutes"):
                cfg["remind_before_minutes"] = r
    except Exception:
        pass  # ponytail: corrupt config → use defaults silently
    return cfg
