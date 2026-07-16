"""
HyprDo theme loader.

Priority: HyDE dcols → pywal → built-in dark.
Returns a flat dict of color hex strings used to generate GTK CSS.
"""

from __future__ import annotations

import re
from pathlib import Path

from .config import get_config

_DCOLS_DIR = Path.home() / ".cache" / "hyde" / "dcols"
_PYWAL_FILE = Path.home() / ".cache" / "wal" / "colors.json"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_theme() -> dict[str, str]:
    mode = get_config()["theme_mode"]
    if mode == "hyde":
        return _load_hyde() or _builtin()
    if mode == "pywal":
        return _load_pywal() or _builtin()
    if mode == "builtin":
        return _builtin()
    # "auto" — try all
    return _load_hyde() or _load_pywal() or _builtin()


def build_css(theme: dict[str, str]) -> str:
    """Generate GTK CSS from a theme dict."""
    t = theme
    return f"""
* {{
    --bg-primary:      #{t["bg_primary"]};
    --bg-card:         #{t["bg_card"]};
    --bg-card-hover:   #{t["bg_card_hover"]};
    --accent:          #{t["accent"]};
    --accent-green:    #{t["accent_green"]};
    --text-primary:    #{t["text_primary"]};
    --text-secondary:  #{t["text_secondary"]};
    --text-done:       #{t["text_done"]};
    --border:          #{t["border"]};
    --priority-high:   #{t["priority_high"]};
    --priority-medium: #{t["priority_medium"]};
    --priority-low:    #{t["priority_low"]};
    --badge-today:     #{t["badge_today"]};
    --badge-tomorrow:  #{t["badge_tomorrow"]};
    --badge-overdue:   #{t["badge_overdue"]};
    --destructive:     #{t["destructive"]};
}}

window {{
    background-color: #{t["bg_primary"]};
    color: #{t["text_primary"]};
}}

.task-card {{
    background-color: #{t["bg_card"]};
    border-radius: 10px;
    border: 1px solid alpha(#{t["text_primary"]}, 0.06);
    margin: 3px 8px;
    padding: 10px 14px;
}}

.task-card:hover {{
    background-color: #{t["bg_card_hover"]};
}}

.task-title {{
    font-weight: 600;
    font-size: 14px;
    color: #{t["text_primary"]};
}}

.task-title.done {{
    text-decoration: line-through;
    color: #{t["text_done"]};
    opacity: 0.6;
}}

.task-meta {{
    font-size: 12px;
    color: #{t["text_secondary"]};
}}

.badge {{
    border-radius: 99px;
    padding: 1px 8px;
    font-size: 11px;
    font-weight: 600;
}}

.badge-today    {{ background-color: #{t["badge_today"]};    color: white; }}

.label-pill {{
    background-color: alpha(#{t["text_primary"]}, 0.08);
    color: #{t["text_primary"]};
    border-radius: 99px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 500;
}}
.label-pill:checked {{
    background-color: #{t["accent"]};
    color: white;
}}
.badge-tomorrow {{ background-color: #{t["badge_tomorrow"]};  color: black; }}
.badge-overdue  {{ background-color: #{t["badge_overdue"]};   color: white; }}

.dot-high   {{ color: #{t["priority_high"]};   }}
.dot-medium {{ color: #{t["priority_medium"]}; }}
.dot-low    {{ color: #{t["priority_low"]};    }}
.dot-none   {{ color: #{t["text_done"]};       }}

.filter-bar {{
    padding: 4px 8px 8px;
}}

.filter-btn {{
    border-radius: 99px;
    padding: 4px 14px;
    font-size: 13px;
}}

.filter-btn:checked {{
    background-color: #{t["accent"]};
    color: white;
}}

.add-btn {{
    background-color: #{t["accent"]};
    color: white;
    border-radius: 99px;
    padding: 6px 16px;
    font-weight: 600;
}}

.footer-label {{
    font-size: 12px;
    color: #{t["text_secondary"]};
    padding: 6px;
}}

.progress-bar progress {{
    background-color: #{t["accent_green"]};
    border-radius: 99px;
}}

.progress-bar {{
    min-height: 4px;
    border-radius: 99px;
}}

.subtask-row {{
    font-size: 13px;
    padding: 2px 0;
    color: #{t["text_primary"]};
}}

.priority-pill {{
    border-radius: 99px;
    padding: 4px 14px;
    font-size: 12px;
}}
"""


# ---------------------------------------------------------------------------
# Loaders — each returns None on failure
# ---------------------------------------------------------------------------


def _load_hyde() -> dict[str, str] | None:
    if not _DCOLS_DIR.exists():
        return None
    dcol_files = sorted(_DCOLS_DIR.glob("*.dcol"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not dcol_files:
        return None
    return _parse_dcol(dcol_files[0])


def _load_pywal() -> dict[str, str] | None:
    if not _PYWAL_FILE.exists():
        return None
    try:
        import json
        data = json.loads(_PYWAL_FILE.read_text())
        colors = data.get("colors", {})
        return {
            "bg_primary":    _strip_hash(colors.get("color0", "0F172A")),
            "bg_card":       _strip_hash(colors.get("color8", "192134")),
            "bg_card_hover": _strip_hash(colors.get("color8", "1E2A40")),
            "accent":        _strip_hash(colors.get("color4", "7C3AED")),
            "accent_green":  _strip_hash(colors.get("color2", "22C55E")),
            "text_primary":  _strip_hash(colors.get("color7", "FFFFFF")),
            "text_secondary": _strip_hash(colors.get("color8", "94A3B8")),
            "text_done":     _strip_hash(colors.get("color8", "64748B")),
            "border":        _strip_hash(colors.get("color0", "1E293B")),
            "priority_high": "EF4444",
            "priority_medium": "EAB308",
            "priority_low":  "22C55E",
            "badge_today":   "F97316",
            "badge_tomorrow": "EAB308",
            "badge_overdue": "EF4444",
            "destructive":   "DC2626",
        }
    except Exception:
        return None


def _builtin() -> dict[str, str]:
    return {
        "bg_primary":    "0F172A",
        "bg_card":       "192134",
        "bg_card_hover": "1E2A40",
        "accent":        "7C3AED",
        "accent_green":  "22C55E",
        "text_primary":  "FFFFFF",
        "text_secondary": "94A3B8",
        "text_done":     "64748B",
        "border":        "1E293B",
        "priority_high": "EF4444",
        "priority_medium": "EAB308",
        "priority_low":  "22C55E",
        "badge_today":   "F97316",
        "badge_tomorrow": "EAB308",
        "badge_overdue": "EF4444",
        "destructive":   "DC2626",
    }


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------


def _parse_dcol(path: Path) -> dict[str, str] | None:
    """Parse a HyDE .dcol file and map its variables to our theme dict."""
    try:
        raw = dict(re.findall(r'^dcol_(\w+)="([^"]+)"', path.read_text(), re.MULTILINE))
        return {
            "bg_primary":    raw.get("pry1", "0F172A"),
            "bg_card":       raw.get("1xa2", "192134"),
            "bg_card_hover": raw.get("1xa3", "1E2A40"),
            "accent":        raw.get("1xa7", "7C3AED"),
            "accent_green":  "22C55E",
            "text_primary":  raw.get("txt1", "FFFFFF"),
            "text_secondary": raw.get("1xa5", "94A3B8"),
            "text_done":     raw.get("1xa4", "64748B"),
            "border":        raw.get("1xa1", "1E293B"),
            "priority_high": raw.get("4xa6", "EF4444"),
            "priority_medium": "EAB308",
            "priority_low":  "22C55E",
            "badge_today":   "F97316",
            "badge_tomorrow": "EAB308",
            "badge_overdue": raw.get("pry4", "EF4444"),
            "destructive":   raw.get("pry4", "DC2626"),
        }
    except Exception:
        return None


def _strip_hash(color: str) -> str:
    return color.lstrip("#")
