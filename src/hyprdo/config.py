"""
HyprDo — User configuration.

Config file: ~/.config/hyprdo/config.toml

Example config.toml:
    [theme]
    mode = "hyde"        # "auto" | "hyde" | "pywal" | "builtin"

    [app]
    default_priority = "none"
    remind_before_minutes = [60, 5]
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]


CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser() / "hyprdo"
CONFIG_FILE = CONFIG_DIR / "config.toml"

DATA_DIR = Path(os.environ.get("XDG_DATA_HOME", "~/.local/share")).expanduser() / "hyprdo"
DB_PATH = DATA_DIR / "hyprdo.db"


@dataclass
class ThemeConfig:
    # "auto"    → try HyDE dcols → pywal → builtin (default, universal)
    # "hyde"    → HyDE dcols only, fallback to builtin
    # "pywal"   → pywal only, fallback to builtin
    # "builtin" → always use built-in dark theme
    mode: str = "auto"


@dataclass
class AppConfig:
    default_priority: str = "none"
    remind_before_minutes: list[int] = field(default_factory=lambda: [60, 5])
    window_width: int = 440
    window_height: int = 620


@dataclass
class Config:
    theme: ThemeConfig = field(default_factory=ThemeConfig)
    app: AppConfig = field(default_factory=AppConfig)


def load_config() -> Config:
    """Load config from ~/.config/hyprdo/config.toml, falling back to defaults."""
    config = Config()

    if not CONFIG_FILE.exists():
        return config

    if tomllib is None:
        # No TOML parser available — return defaults silently
        return config

    try:
        with open(CONFIG_FILE, "rb") as f:
            data = tomllib.load(f)

        if theme_data := data.get("theme", {}):
            if mode := theme_data.get("mode"):
                if mode in ("auto", "hyde", "pywal", "builtin"):
                    config.theme.mode = mode

        if app_data := data.get("app", {}):
            if prio := app_data.get("default_priority"):
                config.app.default_priority = prio
            if remind := app_data.get("remind_before_minutes"):
                config.app.remind_before_minutes = remind
            if w := app_data.get("window_width"):
                config.app.window_width = w
            if h := app_data.get("window_height"):
                config.app.window_height = h

    except Exception:
        pass  # Corrupt config — use defaults

    return config


def write_default_config() -> None:
    """Write a default config.toml if it doesn't exist yet."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        return
    CONFIG_FILE.write_text(
        """\
[theme]
# Theme detection mode:
#   "auto"    - try HyDE dcols → pywal → built-in (recommended for sharing)
#   "hyde"    - HyDE dcols only, fallback to built-in
#   "pywal"   - pywal only, fallback to built-in
#   "builtin" - always use built-in dark theme
mode = "auto"

[app]
default_priority = "none"
remind_before_minutes = [60, 5]
""",
        encoding="utf-8",
    )


# Singleton — loaded once at import time
_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = load_config()
    return _config
