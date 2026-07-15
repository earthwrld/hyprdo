"""
HyprDo — GTK4 application entry point.

Single responsibility: initialize the app, load theme, launch window.
"""

from __future__ import annotations

import sys

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, Gtk

from . import database as db
from .theme import build_css, load_theme
from .ui.window import HyprDoWindow


class HyprDoApp(Adw.Application):
    """GTK4/libadwaita application."""

    def __init__(self) -> None:
        super().__init__(
            application_id="io.github.earthwrld.hyprdo",
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )

    def do_activate(self) -> None:
        db.init_db()
        win = HyprDoWindow(app=self)
        self._apply_theme(win)
        win.present()

    def _apply_theme(self, win: Gtk.Window) -> None:
        css      = build_css(load_theme())
        provider = Gtk.CssProvider()
        provider.load_from_string(css)
        display  = win.get_display() or Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
            )


def main() -> None:
    app = HyprDoApp()
    sys.exit(app.run(sys.argv))
