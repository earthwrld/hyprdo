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
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self.win = None

    def do_activate(self) -> None:
        if self.win is None:
            db.init_db()
            self.win = HyprDoWindow(app=self)
            self._apply_theme(self.win)
        
        if self.win.get_visible():
            self.win.set_visible(False)
        else:
            self.win.present()

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
