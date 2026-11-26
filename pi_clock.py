#!/usr/bin/python3
# Clock for Raspberry Pi, styled after the Windows 11 Clock app (dark).
import os
import sys
import re
import json
import math
import time
import shutil
import signal
import threading
import subprocess

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf, Pango, Gio, GObject  # noqa: E402,F401
import cairo  # noqa: E402

HOME = os.path.expanduser("~")
C_ACCENT = "#4CC2FF"
def hexc(h, a=1.0):
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)


def _rr(cr, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    cr.close_path()


def _line(cr, *pts):
    cr.move_to(*pts[0])
    for p in pts[1:]:
        cr.line_to(*p)
    cr.stroke()


def draw_glyph(cr, name, s, col):
    """Monochrome line icons for buttons."""
    cr.save()
    cr.scale(s / 16.0, s / 16.0)
    cr.set_source_rgba(*col)
    cr.set_line_width(1.15)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    pi = math.pi
    L = lambda *p: _line(cr, *p)  # noqa: E731
    if name == "back":
        L((13.5, 8), (2.5, 8))
        L((7, 3.5), (2.5, 8), (7, 12.5))
    elif name == "forward":
        L((2.5, 8), (13.5, 8))
        L((9, 3.5), (13.5, 8), (9, 12.5))
    elif name == "up":
        L((8, 13.5), (8, 2.5))
        L((3.5, 7), (8, 2.5), (12.5, 7))
    elif name == "refresh":
        cr.arc(8, 8, 5.5, -pi * 0.35, pi * 1.55)
        cr.stroke()
        L((12.9, 1.8), (12.6, 4.9), (9.6, 4.6))
    elif name == "plus":
        L((8, 2.5), (8, 13.5))
        L((2.5, 8), (13.5, 8))
    elif name == "new":
        cr.set_source_rgba(*hexc(C_ACCENT))
        cr.arc(8, 8, 6.5, 0, 2 * pi)
        cr.stroke()
        L((8, 4.8), (8, 11.2))
        L((4.8, 8), (11.2, 8))
    elif name == "cut":
        cr.arc(4.5, 12, 2, 0, 2 * pi)
        cr.stroke()
        cr.arc(11.5, 12, 2, 0, 2 * pi)
        cr.stroke()
        L((5.8, 10.5), (11, 1.8))
        L((10.2, 10.5), (5, 1.8))
    elif name == "copy":
        _rr(cr, 5, 1.5, 9, 10.5, 1.5)
        cr.stroke()
        cr.move_to(3, 4.5)
        cr.line_to(3, 13)
        cr.arc_negative(4.5, 13, 1.5, pi, pi / 2)
        cr.line_to(11, 14.5)
        cr.stroke()
    elif name == "paste":
        _rr(cr, 2.5, 3, 11, 11.5, 1.5)
        cr.stroke()
        _rr(cr, 5.5, 1.5, 5, 3, 1)
        cr.stroke()
        L((5.5, 8), (10.5, 8))
        L((5.5, 11), (9, 11))
    elif name == "rename":
        _rr(cr, 1.5, 4.5, 13, 7, 1.3)
        cr.stroke()
        L((4, 8), (8, 8))
        L((10.5, 2.5), (10.5, 13.5))
        L((9, 2.5), (12, 2.5))
        L((9, 13.5), (12, 13.5))
    elif name == "delete" or name == "trash":
        L((2.5, 4), (13.5, 4))
        L((6, 4), (6.5, 2), (9.5, 2), (10, 4))
        cr.move_to(4, 4)
        cr.line_to(4.8, 14)
        cr.line_to(11.2, 14)
        cr.line_to(12, 4)
        cr.stroke()
        L((6.8, 6.8), (7, 11.5))
        L((9.2, 6.8), (9, 11.5))
    elif name == "sort":
        L((4.5, 2.5), (4.5, 13.5))
        L((2, 5), (4.5, 2.5), (7, 5))
        L((11.5, 2.5), (11.5, 13.5))
        L((9, 11), (11.5, 13.5), (14, 11))
    elif name == "view":
        for y in (3, 8, 13):
            L((2, y), (14, y))
    elif name == "more":
        for x in (3, 8, 13):
            cr.arc(x, 8, 1.1, 0, 2 * pi)
            cr.fill()
    elif name == "chevdown":
        L((4, 6), (8, 10), (12, 6))
    elif name == "chevright":
        L((6, 4), (10, 8), (6, 12))
    elif name == "close":
        L((3.5, 3.5), (12.5, 12.5))
        L((12.5, 3.5), (3.5, 12.5))
    elif name == "min":
        L((3, 8), (13, 8))
    elif name == "max":
        _rr(cr, 3, 3, 10, 10, 1.2)
        cr.stroke()
    elif name == "restore":
        _rr(cr, 3, 5, 8, 8, 1.2)
        cr.stroke()
        L((5, 3), (12, 3), (13, 4), (13, 11))
    elif name == "search":
        cr.arc(6.6, 6.6, 4.6, 0, 2 * pi)
        cr.stroke()
        L((10, 10), (14, 14))
    elif name == "pane":
        _rr(cr, 1.5, 2.5, 13, 11, 1.5)
        cr.stroke()
        L((10, 2.5), (10, 13.5))
    elif name == "terminal":
        _rr(cr, 1.5, 2.5, 13, 11, 1.5)
        cr.stroke()
        L((4, 6), (6.5, 8), (4, 10))
        L((8, 10.5), (11.5, 10.5))
    elif name == "properties":
        _rr(cr, 2.5, 1.5, 11, 13, 1.5)
        cr.stroke()
        for y in (5, 8, 11):
            cr.arc(5.2, y, 0.8, 0, 2 * pi)
            cr.fill()
            L((7.2, y), (11, y))
    elif name == "pin":
        cr.move_to(6, 2)
        cr.line_to(10, 2)
        cr.line_to(9.5, 6.5)
        cr.line_to(12, 9)
        cr.line_to(4, 9)
        cr.line_to(6.5, 6.5)
        cr.close_path()
        cr.stroke()
        L((8, 9), (8, 14))
    elif name == "pin-fill":
        cr.set_line_width(1.0)
        cr.translate(8, 8)
        cr.rotate(pi / 4)
        cr.translate(-8, -8)
        cr.move_to(6, 2)
        cr.line_to(10, 2)
        cr.line_to(9.5, 6.5)
        cr.line_to(12, 9)
        cr.line_to(4, 9)
        cr.line_to(6.5, 6.5)
        cr.close_path()
        cr.stroke()
        L((8, 9), (8, 14))
    elif name == "folder":
        cr.move_to(1.5, 4)
        cr.line_to(6, 4)
        cr.line_to(7.5, 5.5)
        cr.line_to(14.5, 5.5)
        cr.line_to(14.5, 13)
        cr.line_to(1.5, 13)
        cr.close_path()
        cr.stroke()
    elif name == "file":
        cr.move_to(3.5, 1.5)
        cr.line_to(9.5, 1.5)
        cr.line_to(12.5, 4.5)
        cr.line_to(12.5, 14.5)
        cr.line_to(3.5, 14.5)
        cr.close_path()
        cr.stroke()
        L((9.5, 1.5), (9.5, 4.5), (12.5, 4.5))
    elif name == "zip":
        _rr(cr, 2.5, 1.5, 11, 13, 1.5)
        cr.stroke()
        for y in (3, 5, 7):
            L((7, y), (9, y))
        _rr(cr, 6.5, 9, 3, 3.5, 0.6)
        cr.stroke()
    elif name == "extract":
        _rr(cr, 2.5, 6.5, 11, 8, 1.5)
        cr.stroke()
        L((8, 1.5), (8, 10))
        L((5.5, 7.5), (8, 10), (10.5, 7.5))
    elif name == "restoreitem":
        cr.arc(8.5, 8.5, 5, -pi * 0.9, pi * 0.6)
        cr.stroke()
        L((2, 3.5), (3.6, 6.6), (6.6, 5.4))
    elif name == "open":
        _rr(cr, 1.5, 1.5, 13, 13, 2)
        cr.stroke()
        L((7, 9), (12.5, 3.5))
        L((8.5, 3.5), (12.5, 3.5), (12.5, 7.5))
    elif name == "newtab":
        _rr(cr, 1.5, 3.5, 13, 10, 1.5)
        cr.stroke()
        L((1.5, 6), (8, 6))
        L((8, 3.5), (8, 6))
    elif name == "check":
        L((3, 8.5), (6.5, 12), (13, 4.5))
    elif name == "eject":
        cr.move_to(8, 3)
        cr.line_to(13, 9)
        cr.line_to(3, 9)
        cr.close_path()
        cr.stroke()
        L((3, 12.5), (13, 12.5))
    elif name == "details-view":
        for y in (3.5, 8, 12.5):
            _rr(cr, 1.5, y - 1.2, 2.4, 2.4, 0.5)
            cr.stroke()
            L((6, y), (14.5, y))
    elif name == "icons-view":
        for x in (2, 9):
            for y in (2, 9):
                _rr(cr, x, y, 5, 5, 1.2)
                cr.stroke()
    elif name == "selectall":
        _rr(cr, 2, 2, 12, 12, 1.5)
        cr.stroke()
        L((5, 8), (7.2, 10.2), (11, 6))
    elif name == "info":
        cr.arc(8, 8, 6, 0, 2 * pi)
        cr.stroke()
        L((8, 7), (8, 11.5))
        cr.arc(8, 4.8, 0.9, 0, 2 * pi)
        cr.fill()
    elif name == "share":
        cr.arc(4, 8, 1.8, 0, 2 * pi)
        cr.stroke()
        cr.arc(12, 3.8, 1.8, 0, 2 * pi)
        cr.stroke()
        cr.arc(12, 12.2, 1.8, 0, 2 * pi)
        cr.stroke()
        L((5.6, 7.1), (10.4, 4.7))
        L((5.6, 8.9), (10.4, 11.3))
    elif name == "network":
        _rr(cr, 5, 1.5, 6, 4.5, 1)
        cr.stroke()
        L((8, 6), (8, 9))
        L((3, 9), (13, 9))
        L((3, 9), (3, 11))
        L((13, 9), (13, 11))
        _rr(cr, 1, 11, 4, 3.5, 0.8)
        cr.stroke()
        _rr(cr, 11, 11, 4, 3.5, 0.8)
        cr.stroke()
    elif name == "link":
        cr.arc(5.5, 10.5, 3, pi * 0.25, pi * 1.75)
        cr.stroke()
        cr.arc(10.5, 5.5, 3, pi * 1.25, pi * 0.75)
        cr.stroke()
        L((6.5, 9.5), (9.5, 6.5))
    else:
        draw_glyph_extra(cr, name, L, pi)
    cr.restore()




# ----------------------------------------------------------------------------
# Shared Windows 11 dark style
# ----------------------------------------------------------------------------
BASE_CSS = """
* { font-family: "Segoe UI Variable Text", "Segoe UI", "Selawik", "Open Sans", "Noto Sans", sans-serif; }
window.fx, window.fx-dialog { background-color: #202020; color: #ffffff; font-size: 12px; }
.fx label { color: #ffffff; }
headerbar.fx-title { background: #202020; border: none; box-shadow: none; min-height: 40px; padding: 0; margin: 0; }
headerbar.fx-title:backdrop { background: #202020; }
.app-title { font-size: 12px; color: #ffffff; margin-left: 4px; }
.app-title:backdrop { color: rgba(255,255,255,0.55); }
button.wc { background: transparent; border: none; border-radius: 0; min-width: 46px; min-height: 32px; padding: 0; box-shadow: none; }
button.wc:hover { background-color: rgba(255,255,255,0.06); }
button.wc.close:hover { background-color: #C42B1C; }
.tabstrip { margin-top: 6px; margin-left: 6px; }
button.tab { outline-color: transparent; background: transparent; border: none; border-radius: 8px 8px 0 0; min-height: 34px;
   padding: 0 6px 0 12px; box-shadow: none; margin-right: 1px; }
button.tab:hover { background-color: rgba(255,255,255,0.04); }
button.tab.active { background-color: #2C2C2C; }
button.tab label { font-size: 12px; }
button.tab-x { background: transparent; border: none; border-radius: 4px; min-width: 24px; min-height: 24px; padding: 0; box-shadow: none; }
button.tab-x:hover { background-color: rgba(255,255,255,0.08); }
button.tab-new { background: transparent; border: none; border-radius: 4px; min-width: 32px; min-height: 28px; padding: 0;
   box-shadow: none; margin-top: 4px; margin-left: 2px; }
button.tab-new:hover { background-color: rgba(255,255,255,0.06); }
.bar { background-color: #2C2C2C; padding: 4px 8px; }
.bar-bottom { border-bottom: 1px solid rgba(255,255,255,0.06); }
button.tb, button.nb { background: transparent; border: none; border-radius: 4px; min-height: 32px; padding: 0 9px; box-shadow: none; color: #ffffff; }
button.nb { min-width: 34px; padding: 0; }
button.tb:hover, button.nb:hover { background-color: rgba(255,255,255,0.06); }
button.tb:active, button.nb:active { background-color: rgba(255,255,255,0.04); }
button.tb:disabled label { color: rgba(255,255,255,0.36); }
button.tb label { font-size: 12px; }
button.tb.on, button.nb.on { background-color: rgba(255,255,255,0.09); }
.vsep { background-color: rgba(255,255,255,0.08); min-width: 1px; margin: 6px 6px; }
.status { background-color: #202020; padding: 4px 12px; border-top: 1px solid rgba(255,255,255,0.06); }
.status label { font-size: 12px; color: rgba(255,255,255,0.786); }
.sec { color: rgba(255,255,255,0.786); }
.ter { color: rgba(255,255,255,0.545); }
.big-title { font-size: 20px; font-weight: 600; }
.sect-title { font-size: 14px; font-weight: 600; }
entry.field, entry.fx-search { background-color: rgba(255,255,255,0.06); color: #ffffff; border: 1px solid rgba(255,255,255,0.07);
   border-bottom: 1px solid rgba(255,255,255,0.54); border-radius: 4px; min-height: 30px; padding: 0 10px; box-shadow: none;
   font-size: 12px; caret-color: #ffffff; }
entry.field:focus, entry.fx-search:focus { background-color: #1c1c1c; border-bottom: 2px solid #4CC2FF; }
entry selection, textview text selection, entry selection:focus, textview text selection:focus { background-color: #0078D4; color: #ffffff; }
scrollbar { background: transparent; border: none; }
scrollbar slider { background-color: rgba(255,255,255,0.45); border-radius: 6px; min-width: 3px; min-height: 3px; border: none; }
scrollbar:hover slider { min-width: 6px; min-height: 6px; background-color: rgba(255,255,255,0.55); }
scrollbar trough { background: transparent; border: none; }
scale trough { background-color: rgba(255,255,255,0.3); border: none; border-radius: 2px; min-height: 4px; min-width: 4px; }
scale highlight { background-color: #4CC2FF; border: none; border-radius: 2px; min-height: 4px; min-width: 4px; }
scale slider { background-color: #4CC2FF; border: 5px solid #454545; border-radius: 50%; min-width: 12px; min-height: 12px; box-shadow: none; }
scale slider:hover { border-width: 4px; }
menu, .menu, .context-menu { background-color: #2C2C2C; color: #ffffff; border: 1px solid rgba(0,0,0,0.45); border-radius: 8px; padding: 4px; }
menu menuitem { padding: 6px 12px; border-radius: 4px; color: #ffffff; min-height: 18px; }
menu menuitem:hover { background-color: rgba(255,255,255,0.06); }
menu menuitem:disabled label { color: rgba(255,255,255,0.36); }
menu menuitem label { color: #ffffff; font-size: 12px; }
menu menuitem arrow { color: rgba(255,255,255,0.786); }
menu separator { background-color: rgba(255,255,255,0.08); margin: 4px 0; min-height: 1px; }
window.fx button, window.fx-dialog button { background-image: none; text-shadow: none; -gtk-icon-shadow: none; }
button.primary { background-color: #4CC2FF; color: #000000; border: none; border-radius: 4px; min-height: 30px; padding: 0 16px; box-shadow: none; }
button.primary label { color: #000000; }
button.primary:hover { background-color: #48B1E8; }
button.secondary { background-color: rgba(255,255,255,0.06); color: #ffffff; border: 1px solid rgba(255,255,255,0.09); border-radius: 4px; min-height: 30px; padding: 0 16px; box-shadow: none; }
button.secondary:hover { background-color: rgba(255,255,255,0.09); }
.dlg-body { background-color: #2B2B2B; padding: 24px; }
.dlg-foot { background-color: #202020; padding: 22px 24px; border-top: 1px solid rgba(0,0,0,0.3); }
.dlg-title { font-size: 20px; font-weight: 600; }
.fx-dialog label { color: #ffffff; }
.fx-dialog label.sec { color: rgba(255,255,255,0.786); }
.fx-dialog label.ter { color: rgba(255,255,255,0.545); }
checkbutton check { background-color: rgba(0,0,0,0.1); border: 1px solid rgba(255,255,255,0.6); border-radius: 4px; min-width: 18px; min-height: 18px; -gtk-icon-source: none; color: #000000; }
checkbutton check:checked { background-color: #4CC2FF; border-color: #4CC2FF; -gtk-icon-source: -gtk-icontheme("object-select-symbolic"); }
checkbutton label { color: #ffffff; font-size: 12px; margin-left: 6px; }
radiobutton radio { background-color: rgba(0,0,0,0.1); border: 1px solid rgba(255,255,255,0.6); border-radius: 50%; min-width: 18px; min-height: 18px; -gtk-icon-source: none; }
radiobutton radio:checked { background-color: #000000; border: 5px solid #4CC2FF; }
radiobutton label { color: #ffffff; font-size: 12px; margin-left: 6px; }
switch { background-color: transparent; border: 1px solid rgba(255,255,255,0.6); border-radius: 12px; min-width: 40px; min-height: 18px; }
switch:checked { background-color: #4CC2FF; border-color: #4CC2FF; }
switch slider { background-color: rgba(255,255,255,0.8); border-radius: 50%; min-width: 12px; min-height: 12px; margin: 3px; border: none; box-shadow: none; }
switch:checked slider { background-color: #000000; }
switch image { color: transparent; }
combobox button, combobox box { background-color: rgba(255,255,255,0.06); color: #ffffff; border: 1px solid rgba(255,255,255,0.07); border-radius: 4px; box-shadow: none; min-height: 30px; }
combobox button cellview, combobox button label, combobox arrow { color: #ffffff; }
spinbutton { background-color: rgba(255,255,255,0.06); color: #ffffff; border: 1px solid rgba(255,255,255,0.07); border-radius: 4px; box-shadow: none; }
spinbutton entry { background: transparent; border: none; box-shadow: none; color: #ffffff; }
spinbutton button { background: transparent; border: none; box-shadow: none; color: #ffffff; }
tooltip, tooltip.background { background-color: #2C2C2C; border: 1px solid rgba(0,0,0,0.4); border-radius: 4px; }
tooltip label { color: #ffffff; font-size: 12px; }
.set-group { background-color: rgba(255,255,255,0.05); border-radius: 4px; border: 1px solid rgba(0,0,0,0.2); padding: 12px 16px; }
.set-head { font-size: 13px; }
.set-desc { font-size: 12px; color: rgba(255,255,255,0.6); }
"""


def apply_css(extra=""):
    prov = Gtk.CssProvider()
    prov.load_from_data((BASE_CSS + extra).encode())
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), prov,
                                             Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 10)
    Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", True)


def draw_glyph_extra(cr, name, L, pi):
    if name == "save":
        _rr(cr, 2, 2, 12, 12, 1.5)
        cr.stroke()
        _rr(cr, 4.5, 2, 6, 4, 0.5)
        cr.stroke()
        _rr(cr, 4.5, 9, 7, 5, 0.5)
        cr.stroke()
    elif name == "undo":
        cr.move_to(3, 7)
        cr.curve_to(6, 3.5, 13, 4.5, 13, 10)
        cr.stroke()
        L((3, 3), (3, 7), (7, 7))
    elif name == "redo":
        cr.move_to(13, 7)
        cr.curve_to(10, 3.5, 3, 4.5, 3, 10)
        cr.stroke()
        L((13, 3), (13, 7), (9, 7))
    elif name == "replace":
        L((2, 5), (10, 5))
        L((7.5, 2.5), (10, 5), (7.5, 7.5))
        L((14, 11), (6, 11))
        L((8.5, 8.5), (6, 11), (8.5, 13.5))
    elif name == "zoomin":
        cr.arc(6.6, 6.6, 4.6, 0, 2 * pi)
        cr.stroke()
        L((10, 10), (14, 14))
        L((4.6, 6.6), (8.6, 6.6))
        L((6.6, 4.6), (6.6, 8.6))
    elif name == "zoomout":
        cr.arc(6.6, 6.6, 4.6, 0, 2 * pi)
        cr.stroke()
        L((10, 10), (14, 14))
        L((4.6, 6.6), (8.6, 6.6))
    elif name == "fit":
        L((2, 5.5), (2, 2), (5.5, 2))
        L((10.5, 2), (14, 2), (14, 5.5))
        L((14, 10.5), (14, 14), (10.5, 14))
        L((5.5, 14), (2, 14), (2, 10.5))
    elif name == "wrap":
        L((2, 3), (14, 3))
        cr.move_to(2, 8)
        cr.line_to(11.5, 8)
        cr.curve_to(15, 8, 15, 13, 11.5, 13)
        cr.line_to(8, 13)
        cr.stroke()
        L((9.5, 11.3), (8, 13), (9.5, 14.7))
        L((2, 13), (5, 13))
    elif name == "play":
        cr.move_to(4.5, 2.5)
        cr.line_to(13, 8)
        cr.line_to(4.5, 13.5)
        cr.close_path()
        cr.fill()
    elif name == "pause":
        _rr(cr, 3.5, 2.5, 3, 11, 0.8)
        cr.fill()
        _rr(cr, 9.5, 2.5, 3, 11, 0.8)
        cr.fill()
    elif name in ("next", "prev"):
        if name == "prev":
            cr.translate(16, 0)
            cr.scale(-1, 1)
        cr.move_to(3, 3)
        cr.line_to(10.5, 8)
        cr.line_to(3, 13)
        cr.close_path()
        cr.fill()
        _rr(cr, 11, 3, 2, 10, 0.6)
        cr.fill()
    elif name == "shuffle":
        L((2, 4), (5, 4), (11, 12), (14, 12))
        L((2, 12), (5, 12), (11, 4), (14, 4))
        L((12, 2), (14, 4), (12, 6))
        L((12, 10), (14, 12), (12, 14))
    elif name in ("repeat", "repeat1"):
        cr.move_to(3, 9)
        cr.line_to(3, 6)
        cr.arc(5, 6, 2, pi, 1.5 * pi)
        cr.line_to(13, 4)
        cr.stroke()
        L((11, 2), (13, 4), (11, 6))
        cr.move_to(13, 7)
        cr.line_to(13, 10)
        cr.arc(11, 10, 2, 0, 0.5 * pi)
        cr.line_to(3, 12)
        cr.stroke()
        L((5, 10), (3, 12), (5, 14))
        if name == "repeat1":
            cr.set_font_size(5)
            cr.move_to(6.8, 9.8)
            cr.show_text("1")
    elif name in ("volume", "mute"):
        cr.move_to(1.5, 6)
        cr.line_to(4.5, 6)
        cr.line_to(8, 2.5)
        cr.line_to(8, 13.5)
        cr.line_to(4.5, 10)
        cr.line_to(1.5, 10)
        cr.close_path()
        cr.stroke()
        if name == "mute":
            L((10.5, 6), (14.5, 10))
            L((14.5, 6), (10.5, 10))
        else:
            cr.arc(8, 8, 3.5, -pi / 3.5, pi / 3.5)
            cr.stroke()
            cr.arc(8, 8, 6.2, -pi / 3.5, pi / 3.5)
            cr.stroke()
    elif name == "fullscreen":
        L((2, 6), (2, 2), (6, 2))
        L((10, 2), (14, 2), (14, 6))
        L((14, 10), (14, 14), (10, 14))
        L((6, 14), (2, 14), (2, 10))
        L((2, 2), (6, 6))
        L((14, 14), (10, 10))
    elif name == "unfullscreen":
        L((6, 2), (6, 6), (2, 6))
        L((10, 2), (10, 6), (14, 6))
        L((10, 14), (10, 10), (14, 10))
        L((6, 14), (6, 10), (2, 10))
    elif name == "rotate":
        cr.arc(8, 9, 5, pi * 1.15, pi * 2.85)
        cr.stroke()
        L((2.5, 2.5), (3.4, 6.4), (7.2, 5.4))
    elif name == "heart":
        cr.move_to(8, 13.5)
        cr.curve_to(1, 8, 1.5, 2.5, 5, 2.5)
        cr.curve_to(6.5, 2.5, 7.5, 3.5, 8, 4.5)
        cr.curve_to(8.5, 3.5, 9.5, 2.5, 11, 2.5)
        cr.curve_to(14.5, 2.5, 15, 8, 8, 13.5)
        cr.stroke()
    elif name == "pen":
        L((2.5, 13.5), (3.2, 10.5), (11, 2.7), (13.3, 5), (5.5, 12.8), (2.5, 13.5))
        L((9.5, 4.2), (11.8, 6.5))
    elif name == "highlighter":
        L((3, 13.5), (13, 13.5))
        cr.move_to(5, 11)
        cr.line_to(11, 3)
        cr.line_to(13.5, 5)
        cr.line_to(7.5, 12.5)
        cr.line_to(5, 12.5)
        cr.close_path()
        cr.stroke()
    elif name == "eraser":
        cr.move_to(2.5, 10)
        cr.line_to(9, 3.5)
        cr.line_to(13.5, 8)
        cr.line_to(8, 13.5)
        cr.line_to(5.5, 13.5)
        cr.close_path()
        cr.stroke()
        L((6, 6.5), (10.5, 11))
        L((8, 13.5), (14, 13.5))
    elif name == "crop":
        L((4.5, 1.5), (4.5, 11.5), (14.5, 11.5))
        L((1.5, 4.5), (11.5, 4.5), (11.5, 14.5))
    elif name == "camera":
        _rr(cr, 1.5, 4, 13, 9.5, 1.6)
        cr.stroke()
        L((5, 4), (6, 2.5), (10, 2.5), (11, 4))
        cr.arc(8, 8.8, 2.6, 0, 2 * pi)
        cr.stroke()
    elif name == "timer":
        cr.arc(8, 9, 5.5, 0, 2 * pi)
        cr.stroke()
        L((8, 9), (8, 5.8))
        L((6.3, 1.8), (9.7, 1.8))
    elif name == "settings":
        n = 8
        cr.new_path()
        for i in range(n * 2):
            a = i * pi / n
            r = 6.6 if i % 2 == 0 else 5.0
            a1, a2 = a - pi / (n * 2.4), a + pi / (n * 2.4)
            cr.line_to(8 + r * math.cos(a1), 8 + r * math.sin(a1))
            cr.line_to(8 + r * math.cos(a2), 8 + r * math.sin(a2))
        cr.close_path()
        cr.stroke()
        cr.arc(8, 8, 2.2, 0, 2 * pi)
        cr.stroke()
    elif name == "history":
        cr.arc(8, 8, 6, pi * 1.05, pi * 2.85)
        cr.stroke()
        L((1.2, 6.2), (2.3, 8.6), (4.6, 7.3))
        L((8, 4.6), (8, 8.2), (10.5, 9.7))
    elif name == "image":
        _rr(cr, 1.5, 2.5, 13, 11, 1.5)
        cr.stroke()
        L((1.5, 11), (5.5, 7), (9, 10.5), (11, 8.5), (14.5, 12))
        cr.arc(10.5, 5.5, 1.2, 0, 2 * pi)
        cr.stroke()
    elif name == "music":
        cr.arc(4.5, 12, 2, 0, 2 * pi)
        cr.stroke()
        cr.arc(12, 10.5, 2, 0, 2 * pi)
        cr.stroke()
        L((6.5, 12), (6.5, 3.5), (14, 2), (14, 10.5))
    elif name == "video":
        _rr(cr, 1.5, 3.5, 9.5, 9, 1.5)
        cr.stroke()
        L((11, 6.5), (14.5, 4.5), (14.5, 11.5), (11, 9.5))
    elif name == "queue":
        for y in (3, 7):
            L((2, y), (14, y))
        L((2, 11), (8, 11))
        cr.move_to(10.5, 9)
        cr.line_to(14, 11.5)
        cr.line_to(10.5, 14)
        cr.close_path()
        cr.fill()
    elif name == "edit":
        L((2.5, 13.5), (3.2, 10.5), (11, 2.7), (13.3, 5), (5.5, 12.8), (2.5, 13.5))
    elif name == "slideshow":
        _rr(cr, 1.5, 2.5, 13, 9, 1.5)
        cr.stroke()
        cr.move_to(6.5, 5)
        cr.line_to(10, 7)
        cr.line_to(6.5, 9)
        cr.close_path()
        cr.fill()
        L((5, 14), (11, 14))
    elif name == "print":
        _rr(cr, 1.5, 6, 13, 6, 1.2)
        cr.stroke()
        L((4.5, 6), (4.5, 1.5), (11.5, 1.5), (11.5, 6))
        _rr(cr, 4.5, 9.5, 7, 5, 0.5)
        cr.stroke()
    elif name == "wallpaper":
        _rr(cr, 1.5, 2.5, 13, 9, 1.2)
        cr.stroke()
        L((1.5, 9.5), (5, 6), (8, 9), (10, 7), (14.5, 10.5))
        L((5.5, 14), (10.5, 14))
        L((8, 11.5), (8, 14))
    elif name == "list":
        for y in (3.5, 8, 12.5):
            cr.arc(2.5, y, 0.9, 0, 2 * pi)
            cr.fill()
            L((5.5, y), (14, y))
    elif name == "add":
        L((8, 2.5), (8, 13.5))
        L((2.5, 8), (13.5, 8))
    elif name == "split":
        _rr(cr, 1.5, 2.5, 13, 11, 1.5)
        cr.stroke()
        L((8, 2.5), (8, 13.5))
    elif name == "keyboard":
        _rr(cr, 1, 3.5, 14, 9, 1.5)
        cr.stroke()
        for x in (4, 6.7, 9.3, 12):
            cr.rectangle(x - 0.5, 6, 1, 1)
        cr.fill()
        L((4.5, 10), (11.5, 10))


class Icon(Gtk.DrawingArea):
    """Monochrome glyph icon."""

    def __init__(self, name, size=16, color=None):
        super().__init__()
        self.name = name
        self.size = size
        self.color = color
        self.set_size_request(size, size)
        self.set_valign(Gtk.Align.CENTER)
        self.connect("draw", self._draw)

    def set_icon(self, name):
        self.name = name
        self.queue_draw()

    def _draw(self, w, cr):
        col = self.color or (1, 1, 1, 1)
        p = self.get_parent()
        if not self.is_sensitive() or (p and not p.is_sensitive()):
            col = (1, 1, 1, 0.36)
        draw_glyph(cr, self.name, self.size, col)


class WinTitlebar(Gtk.HeaderBar):
    """Title bar with Windows 11 caption buttons. Pack your own widgets with pack_start()."""

    def __init__(self, window):
        super().__init__()
        self.win = window
        self.get_style_context().add_class("fx-title")
        self.set_show_close_button(False)
        self.set_custom_title(Gtk.Box())
        wc = Gtk.Box(spacing=0)
        wc.set_valign(Gtk.Align.START)
        for name, cb, extra in (("min", lambda *_: window.iconify(), ""),
                                ("max", lambda *_: self.toggle_max(), ""),
                                ("close", lambda *_: window.close(), "close")):
            b = Gtk.Button()
            b.get_style_context().add_class("wc")
            if extra:
                b.get_style_context().add_class(extra)
            ic = Icon(name, 10)
            b.add(ic)
            b.connect("clicked", cb)
            if name == "max":
                self.max_icon = ic
            wc.pack_start(b, False, False, 0)
        self.pack_end(wc)
        window.connect("window-state-event", self._wstate)
        window.set_titlebar(self)

    def toggle_max(self):
        if self.win.is_maximized():
            self.win.unmaximize()
        else:
            self.win.maximize()

    def _wstate(self, w, ev):
        maxed = bool(ev.new_window_state & Gdk.WindowState.MAXIMIZED)
        self.max_icon.set_icon("restore" if maxed else "max")
        return False


def app_title(text, logo_draw):
    """Little logo + app name for the left of the title bar."""
    box = Gtk.Box(spacing=8)
    box.set_margin_start(14)
    da = Gtk.DrawingArea()
    da.set_size_request(16, 16)
    da.set_valign(Gtk.Align.CENTER)
    da.connect("draw", lambda w, cr: logo_draw(cr, 16))
    box.pack_start(da, False, False, 0)
    lb = Gtk.Label(label=text)
    lb.get_style_context().add_class("app-title")
    box.pack_start(lb, False, False, 0)
    return box, lb


class JsonSettings(dict):
    def __init__(self, app_dir, defaults):
        super().__init__(defaults)
        self.dir = os.path.join(HOME, ".config", app_dir)
        self.file = os.path.join(self.dir, "settings.json")
        try:
            with open(self.file) as f:
                self.update(json.load(f))
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            os.makedirs(self.dir, exist_ok=True)
            tmp = self.file + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self, f, indent=1)
            os.replace(tmp, self.file)
        except OSError:
            pass


def vsep():
    s = Gtk.Box()
    s.get_style_context().add_class("vsep")
    return s


def logo_pixbuf(draw, size):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    draw(cairo.Context(surf), size)
    return Gdk.pixbuf_get_from_surface(surf, 0, 0, size, size)
def label(text="", cls=None, xalign=0.0, ellipsize=False, wrap=False, markup=False):
    lb = Gtk.Label()
    if markup:
        lb.set_markup(text)
    else:
        lb.set_text(text)
    lb.set_xalign(xalign)
    if cls:
        for c in cls.split():
            lb.get_style_context().add_class(c)
    if ellipsize:
        lb.set_ellipsize(Pango.EllipsizeMode.END)
    if wrap:
        lb.set_line_wrap(True)
        lb.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
    return lb


def add_cls(w, *cls):
    ctx = w.get_style_context()
    for c in cls:
        ctx.add_class(c)
    return w


def tb_button(icon, text, cb=None, chev=False, tip=None):
    b = Gtk.Button()
    add_cls(b, "tb")
    box = Gtk.Box(spacing=7)
    if icon:
        box.pack_start(Icon(icon), False, False, 0)
    if text:
        box.pack_start(Gtk.Label(label=text), False, False, 0)
    if chev:
        box.pack_start(Icon("chevdown", 10), False, False, 0)
    b.add(box)
    b.set_relief(Gtk.ReliefStyle.NONE)
    b.set_tooltip_text(tip or text or None)
    if cb:
        b.connect("clicked", lambda w: cb(w))
    return b


def icon_button(icon, cb, cls="nb", tip=None, size=16):
    b = Gtk.Button()
    add_cls(b, cls)
    b.add(Icon(icon, size))
    b.set_relief(Gtk.ReliefStyle.NONE)
    if tip:
        b.set_tooltip_text(tip)
    b.connect("clicked", lambda w: cb(w))
    return b


def build_menu(spec):
    """spec: list of None (separator) or dicts: label, cb, icon, place, accel, sensitive, checked, sub."""
    menu = Gtk.Menu()
    add_cls(menu, "context-menu")
    for it in spec:
        if it is None:
            menu.append(Gtk.SeparatorMenuItem())
            continue
        mi = Gtk.MenuItem()
        box = Gtk.Box(spacing=12)
        ic = None
        if it.get("checked"):
            ic = Icon("check", 16)
        elif it.get("pixbuf") is not None:
            ic = Gtk.Image.new_from_pixbuf(it["pixbuf"])
        elif it.get("icon"):
            ic = Icon(it["icon"], 16)
        if ic is None:
            ic = Gtk.Box()
            ic.set_size_request(16, 16)
        box.pack_start(ic, False, False, 0)
        lb = Gtk.Label(label=it["label"])
        lb.set_xalign(0)
        box.pack_start(lb, True, True, 0)
        if it.get("accel"):
            al = Gtk.Label(label=it["accel"])
            al.get_style_context().add_class("dim-label")
            al.set_opacity(0.55)
            al.set_margin_start(24)
            box.pack_end(al, False, False, 0)
        mi.add(box)
        mi.set_sensitive(it.get("sensitive", True))
        if it.get("sub") is not None:
            mi.set_submenu(build_menu(it["sub"]))
        elif it.get("cb"):
            cb = it["cb"]
            mi.connect("activate", lambda w, cb=cb: GLib.idle_add(cb))
        menu.append(mi)
    menu.show_all()
    return menu


def popup_menu(menu, widget, event=None):
    menu.attach_to_widget(widget, None)
    if event is not None:
        menu.popup_at_pointer(event)
    else:
        menu.popup_at_widget(widget, Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST, None)


# ----------------------------------------------------------------------------
# Windows 11 style dialogs
# ----------------------------------------------------------------------------
class WinDialog(Gtk.Window):
    def __init__(self, parent, title, body=None, primary="OK", secondary="Cancel", width=440, extra=None,
                 markup=False):
        super().__init__(transient_for=parent, modal=True)
        add_cls(self, "fx-dialog")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_default_size(width, -1)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_title(title)
        self.cb = None
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        add_cls(self.body, "dlg-body")
        self.body.pack_start(label(title, "dlg-title"), False, False, 0)
        if body:
            lb = label(body, wrap=True, markup=markup)
            lb.set_max_width_chars(60)
            self.body.pack_start(lb, False, False, 0)
        if extra:
            self.body.pack_start(extra, False, False, 0)
        outer.pack_start(self.body, True, True, 0)
        self.foot = Gtk.Box(spacing=8, homogeneous=True)
        add_cls(self.foot, "dlg-foot")
        self.primary_btn = None
        if primary:
            pb = Gtk.Button(label=primary)
            add_cls(pb, "primary")
            pb.connect("clicked", lambda *_: self.done(True))
            self.foot.pack_start(pb, True, True, 0)
            pb.set_can_default(True)
            self.set_default(pb)
            self.primary_btn = pb
        if secondary:
            sb = Gtk.Button(label=secondary)
            add_cls(sb, "secondary")
            sb.connect("clicked", lambda *_: self.done(False))
            self.foot.pack_start(sb, True, True, 0)
        if primary or secondary:
            outer.pack_start(self.foot, False, False, 0)
        self.add(outer)
        self.connect("key-press-event", self._key)

    def _key(self, w, ev):
        if ev.keyval == Gdk.KEY_Escape:
            self.done(False)
            return True
        return False

    def done(self, ok):
        cb = self.cb
        self.cb = None
        self.hide()
        if cb:
            cb(ok)
        self.destroy()

    def ask(self, cb=None):
        self.cb = cb
        self.show_all()
        if self.primary_btn:
            self.primary_btn.grab_focus()


def info_dialog(parent, title, body):
    WinDialog(parent, title, body, primary="OK", secondary=None).ask()


def confirm(parent, title, body, yes, cb, no="Cancel"):
    WinDialog(parent, title, body, primary=yes, secondary=no).ask(cb)


def error_list_dialog(parent, title, errors):
    lines = []
    for p, msg in errors[:12]:
        lines.append(f"{os.path.basename(p) or p}: {msg}" if p else msg)
    if len(errors) > 12:
        lines.append(f"...and {len(errors) - 12} more")
    info_dialog(parent, title, "\n".join(lines))




# ----------------------------------------------------------------------------
# Clock
# ----------------------------------------------------------------------------
import datetime  # noqa: E402
import wave  # noqa: E402
import struct  # noqa: E402
import uuid  # noqa: E402
try:
    from zoneinfo import ZoneInfo, available_timezones  # noqa: E402
except ImportError:
    ZoneInfo = None

APP_ID = "io.github.piclock"
DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
SOUNDS = ["Chimes", "Bells", "Beeps", "Xylophone"]
SNOOZES = [0, 5, 10, 20, 30]
DEFAULTS = {
    "width": 1060, "height": 700, "page": "timer", "h24": False, "sound": "Chimes",
    "timers": [{"id": "t1", "name": "", "secs": 60}, {"id": "t3", "name": "", "secs": 180},
               {"id": "t5", "name": "", "secs": 300}, {"id": "t10", "name": "", "secs": 600}],
    "alarms": [{"id": "a1", "name": "Good morning", "h": 7, "m": 0, "days": [], "on": False,
                "sound": "Chimes", "snooze": 10}],
    "zones": ["America/New_York", "Europe/London", "Asia/Tokyo"],
    "focus_len": 30, "focus_breaks": True, "focus_goal": 60, "focus_log": {},
}

# city, time zone
CITIES = [
    ("Honolulu", "Pacific/Honolulu"), ("Anchorage", "America/Anchorage"), ("Los Angeles", "America/Los_Angeles"),
    ("San Francisco", "America/Los_Angeles"), ("Seattle", "America/Los_Angeles"), ("Vancouver", "America/Vancouver"),
    ("Las Vegas", "America/Los_Angeles"), ("Phoenix", "America/Phoenix"), ("Denver", "America/Denver"),
    ("Salt Lake City", "America/Denver"), ("Chicago", "America/Chicago"), ("Dallas", "America/Chicago"),
    ("Houston", "America/Chicago"), ("Mexico City", "America/Mexico_City"), ("New York", "America/New_York"),
    ("Washington, D.C.", "America/New_York"), ("Boston", "America/New_York"), ("Miami", "America/New_York"),
    ("Atlanta", "America/New_York"), ("Detroit", "America/Detroit"), ("Toronto", "America/Toronto"),
    ("Montreal", "America/Toronto"), ("Halifax", "America/Halifax"), ("San Juan", "America/Puerto_Rico"),
    ("Bogota", "America/Bogota"), ("Lima", "America/Lima"), ("Santiago", "America/Santiago"),
    ("Buenos Aires", "America/Argentina/Buenos_Aires"), ("Sao Paulo", "America/Sao_Paulo"),
    ("Rio de Janeiro", "America/Sao_Paulo"), ("Reykjavik", "Atlantic/Reykjavik"), ("London", "Europe/London"),
    ("Dublin", "Europe/Dublin"), ("Lisbon", "Europe/Lisbon"), ("Madrid", "Europe/Madrid"), ("Paris", "Europe/Paris"),
    ("Brussels", "Europe/Brussels"), ("Amsterdam", "Europe/Amsterdam"), ("Berlin", "Europe/Berlin"),
    ("Zurich", "Europe/Zurich"), ("Rome", "Europe/Rome"), ("Vienna", "Europe/Vienna"), ("Prague", "Europe/Prague"),
    ("Stockholm", "Europe/Stockholm"), ("Oslo", "Europe/Oslo"), ("Copenhagen", "Europe/Copenhagen"),
    ("Warsaw", "Europe/Warsaw"), ("Athens", "Europe/Athens"), ("Helsinki", "Europe/Helsinki"),
    ("Kyiv", "Europe/Kyiv"), ("Istanbul", "Europe/Istanbul"), ("Moscow", "Europe/Moscow"), ("Cairo", "Africa/Cairo"),
    ("Johannesburg", "Africa/Johannesburg"), ("Lagos", "Africa/Lagos"), ("Nairobi", "Africa/Nairobi"),
    ("Casablanca", "Africa/Casablanca"), ("Tel Aviv", "Asia/Jerusalem"), ("Riyadh", "Asia/Riyadh"),
    ("Dubai", "Asia/Dubai"), ("Tehran", "Asia/Tehran"), ("Karachi", "Asia/Karachi"), ("New Delhi", "Asia/Kolkata"),
    ("Mumbai", "Asia/Kolkata"), ("Kathmandu", "Asia/Kathmandu"), ("Dhaka", "Asia/Dhaka"), ("Bangkok", "Asia/Bangkok"),
    ("Jakarta", "Asia/Jakarta"), ("Singapore", "Asia/Singapore"), ("Kuala Lumpur", "Asia/Kuala_Lumpur"),
    ("Hong Kong", "Asia/Hong_Kong"), ("Beijing", "Asia/Shanghai"), ("Shanghai", "Asia/Shanghai"),
    ("Taipei", "Asia/Taipei"), ("Manila", "Asia/Manila"), ("Seoul", "Asia/Seoul"), ("Tokyo", "Asia/Tokyo"),
    ("Perth", "Australia/Perth"), ("Adelaide", "Australia/Adelaide"), ("Brisbane", "Australia/Brisbane"),
    ("Sydney", "Australia/Sydney"), ("Melbourne", "Australia/Melbourne"), ("Auckland", "Pacific/Auckland"),
]
ZONE_CITY = {}
for _c, _z in CITIES:
    ZONE_CITY.setdefault(_z, _c)

CSS = """
.navpane { background-color: #202020; padding: 4px 4px 8px 4px; }
button.nav { background: transparent; border: none; border-radius: 4px; min-height: 38px; padding: 0 12px; box-shadow: none; }
button.nav:hover { background-color: rgba(255,255,255,0.06); }
button.nav.sel { background-color: rgba(255,255,255,0.06); }
button.nav label { font-size: 13px; }
.navbar { background-color: transparent; min-width: 3px; border-radius: 2px; margin: 10px 0; }
.navbar.sel { background-color: #4CC2FF; }
.page { background-color: #272727; border-top-left-radius: 8px; border-top: 1px solid rgba(255,255,255,0.05);
   border-left: 1px solid rgba(255,255,255,0.05); }
.page-title { font-size: 28px; font-weight: 600; }
.card { background-color: #2D2D2D; border: 1px solid rgba(0,0,0,0.25); border-radius: 8px; }
.card-name { font-size: 14px; font-weight: 600; }
.card-sub { font-size: 12px; color: rgba(255,255,255,0.6); }
.big-time { font-size: 30px; font-weight: 600; }
.huge-time { font-size: 80px; font-weight: 600; }
.huge-frac { font-size: 80px; font-weight: 300; color: rgba(255,255,255,0.6); }
.alarm-time { font-size: 40px; font-weight: 600; }
.alarm-ampm { font-size: 14px; font-weight: 600; margin-left: 4px; }
.alarm-off .alarm-time, .alarm-off .alarm-ampm, .alarm-off .card-name { color: rgba(255,255,255,0.45); }
.day { font-size: 11px; color: rgba(255,255,255,0.45); margin-right: 6px; }
.day.on { color: #4CC2FF; font-weight: 600; }
button.round { background-color: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08); border-radius: 50%;
   min-width: 40px; min-height: 40px; padding: 0; box-shadow: none; }
button.round:hover { background-color: rgba(255,255,255,0.1); }
button.round.accent { background-color: #4CC2FF; border-color: #4CC2FF; }
button.round.accent:hover { background-color: #48B1E8; }
button.round.big { min-width: 56px; min-height: 56px; }
button.fab { background-color: #4CC2FF; border: none; border-radius: 6px; min-width: 44px; min-height: 44px; padding: 0; box-shadow: 0 4px 12px rgba(0,0,0,0.4); }
button.fab:hover { background-color: #48B1E8; }
button.ghost { background: transparent; border: none; box-shadow: none; border-radius: 4px; min-width: 32px; min-height: 32px; padding: 0; }
button.ghost:hover { background-color: rgba(255,255,255,0.06); }
.lap-head { font-size: 12px; color: rgba(255,255,255,0.6); }
.lap { font-size: 13px; }
.lap-row { border-bottom: 1px solid rgba(255,255,255,0.06); padding: 8px 0; }
button.daybtn { background-color: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08); border-radius: 50%;
   min-width: 36px; min-height: 36px; padding: 0; box-shadow: none; }
button.daybtn.on { background-color: #4CC2FF; border-color: #4CC2FF; }
button.daybtn.on label { color: #000000; }
button.daybtn label { font-size: 11px; }
.ring-label { font-size: 13px; color: rgba(255,255,255,0.7); }
.focus-big { font-size: 46px; font-weight: 600; }
.stat-num { font-size: 26px; font-weight: 600; }
.ring-window { background-color: #2B2B2B; }
.ring-title { font-size: 20px; font-weight: 600; }
.zone-time { font-size: 34px; font-weight: 600; }
button.cityrow { background: transparent; border: none; box-shadow: none; border-radius: 4px; padding: 6px 10px; }
button.cityrow:hover { background-color: rgba(255,255,255,0.06); }
combobox > box.linked > button, combobox box { border: none; background: transparent; box-shadow: none; }
combobox { background-color: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.07); border-radius: 4px; }
.setting-row { background-color: #2D2D2D; border: 1px solid rgba(0,0,0,0.25); border-radius: 6px; padding: 14px 18px; }
"""


def draw_logo(cr, s):
    cr.save()
    cr.scale(s / 16.0, s / 16.0)
    g = cairo.LinearGradient(0, 0, 16, 16)
    g.add_color_stop_rgb(0, 0.33, 0.80, 1.0)
    g.add_color_stop_rgb(1, 0.0, 0.42, 0.85)
    cr.arc(8, 8, 7, 0, 2 * math.pi)
    cr.set_source(g)
    cr.fill()
    cr.arc(8, 8, 5.3, 0, 2 * math.pi)
    cr.set_source_rgb(0.12, 0.14, 0.18)
    cr.fill()
    cr.set_source_rgb(1, 1, 1)
    cr.set_line_width(1.2)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.move_to(8, 8)
    cr.line_to(8, 4.4)
    cr.stroke()
    cr.move_to(8, 8)
    cr.line_to(10.6, 9.4)
    cr.stroke()
    cr.restore()


_orig_extra = draw_glyph_extra


def draw_glyph_extra(cr, name, L, pi):  # noqa: F811
    if name == "focus":
        cr.arc(8, 8, 6, 0, 2 * pi)
        cr.stroke()
        cr.arc(8, 8, 3, 0, 2 * pi)
        cr.stroke()
        cr.arc(8, 8, 0.6, 0, 2 * pi)
        cr.fill()
    elif name == "alarm":
        cr.arc(8, 8.8, 5.2, 0, 2 * pi)
        cr.stroke()
        L((8, 6), (8, 9), (10, 10.2))
        L((2.2, 4), (4.2, 2))
        L((13.8, 4), (11.8, 2))
    elif name == "stopwatch":
        cr.arc(8, 9.2, 5.3, 0, 2 * pi)
        cr.stroke()
        L((6.5, 1.8), (9.5, 1.8))
        L((8, 1.8), (8, 3.9))
        L((8, 9.2), (10, 6.8))
    elif name == "globe":
        cr.arc(8, 8, 6.2, 0, 2 * pi)
        cr.stroke()
        cr.save()
        cr.scale(0.45, 1)
        cr.arc(8 / 0.45, 8, 6.2, 0, 2 * pi)
        cr.restore()
        cr.stroke()
        L((1.8, 8), (14.2, 8))
        L((3, 4.6), (13, 4.6))
        L((3, 11.4), (13, 11.4))
    elif name == "gear":
        cr.arc(8, 8, 2.2, 0, 2 * pi)
        cr.stroke()
        for i in range(8):
            a = i * pi / 4
            L((8 + 4.4 * math.cos(a), 8 + 4.4 * math.sin(a)), (8 + 6.2 * math.cos(a), 8 + 6.2 * math.sin(a)))
        cr.arc(8, 8, 4.6, 0, 2 * pi)
        cr.stroke()
    elif name == "reset":
        cr.arc(8, 8, 5.2, pi * 1.1, pi * 2.8)
        cr.stroke()
        L((2.2, 3.2), (2.6, 6.8), (6.1, 6.1))
    elif name == "flag":
        L((3.5, 14.5), (3.5, 2))
        cr.move_to(3.5, 2.5)
        cr.line_to(13, 2.5)
        cr.line_to(10.5, 5.5)
        cr.line_to(13, 8.5)
        cr.line_to(3.5, 8.5)
        cr.stroke()
    elif name == "expand":
        L((9.5, 2.5), (13.5, 2.5), (13.5, 6.5))
        L((6.5, 13.5), (2.5, 13.5), (2.5, 9.5))
        L((13.5, 2.5), (9, 7))
        L((2.5, 13.5), (7, 9))
    elif name == "stop":
        _rr(cr, 3.5, 3.5, 9, 9, 1.5)
        cr.fill()
    else:
        _orig_extra(cr, name, L, pi)


# ---------------------------------------------------------------- helpers
def fmt_hms(secs, always_h=True):
    secs = max(0, int(round(secs)))
    h, r = divmod(secs, 3600)
    m, s = divmod(r, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if (always_h or h) else f"{m:02d}:{s:02d}"


def fmt_clock(h, m, h24):
    if h24:
        return f"{h:02d}:{m:02d}", ""
    return f"{(h % 12) or 12}:{m:02d}", ("AM" if h < 12 else "PM")


def nice_len(secs):
    h, r = divmod(int(secs), 3600)
    m, s = divmod(r, 60)
    parts = []
    if h:
        parts.append(f"{h} hr")
    if m:
        parts.append(f"{m} min")
    if s or not parts:
        parts.append(f"{s} sec")
    return " ".join(parts)


SOUND_DIR = os.path.join(HOME, ".cache", "pi-clock")


def make_sounds():
    """Small built-in alarm sounds, made once, so no sound packages are needed."""
    os.makedirs(SOUND_DIR, exist_ok=True)
    rate = 22050
    specs = {
        "Chimes": [(880, 0.25), (1108.7, 0.25), (1318.5, 0.5), (0, 0.6)],
        "Bells": [(1046.5, 0.7), (0, 0.15), (784, 0.9), (0, 0.6)],
        "Beeps": [(1000, 0.12), (0, 0.08), (1000, 0.12), (0, 0.08), (1000, 0.12), (0, 0.08), (1000, 0.12), (0, 0.6)],
        "Xylophone": [(523.3, 0.15), (659.3, 0.15), (784, 0.15), (1046.5, 0.3), (784, 0.15), (1046.5, 0.4), (0, 0.6)],
    }
    for name, notes in specs.items():
        path = os.path.join(SOUND_DIR, name.lower() + ".wav")
        if os.path.exists(path):
            continue
        frames = bytearray()
        for freq, dur in notes:
            n = int(rate * dur)
            for i in range(n):
                if freq == 0:
                    v = 0
                else:
                    t = i / rate
                    env = min(1.0, i / (rate * 0.01)) * math.exp(-3.2 * t / max(dur, 0.1))
                    v = env * (0.6 * math.sin(2 * math.pi * freq * t) + 0.25 * math.sin(4 * math.pi * freq * t))
                frames += struct.pack("<h", int(max(-1, min(1, v)) * 14000))
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(bytes(frames))


class Player:
    """Loops a sound until stopped."""

    def __init__(self):
        self.proc = None
        self.loop_id = None
        self.until = 0

    def _cmd(self, path):
        for c in (["pw-play", path], ["paplay", path], ["aplay", "-q", path]):
            if shutil.which(c[0]):
                return c
        return None

    def play(self, sound, loop=True, max_secs=300):
        self.stop()
        path = os.path.join(SOUND_DIR, (sound or "Chimes").lower() + ".wav")
        cmd = self._cmd(path)
        if not cmd:
            Gdk.beep()
            return
        self.until = time.time() + max_secs
        self.loop = loop

        def again():
            if self.proc is None or self.proc.poll() is not None:
                if time.time() > self.until:
                    self.loop_id = None
                    return False
                try:
                    self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except OSError:
                    return False
                if not self.loop:
                    self.loop_id = None
                    return False
            return True
        self.proc = None
        again()
        if loop:
            self.loop_id = GLib.timeout_add(300, again)

    def stop(self):
        if self.loop_id:
            GLib.source_remove(self.loop_id)
            self.loop_id = None
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.terminate()
            except OSError:
                pass
        self.proc = None


class Ring(Gtk.DrawingArea):
    """Progress ring like the Windows Clock timers."""

    def __init__(self, size, width=6):
        super().__init__()
        self.size = size
        self.width = width
        self.frac = 0.0
        self.color = hexc(C_ACCENT)
        self.set_size_request(size, size)
        self.connect("draw", self._draw)

    def set_frac(self, f):
        self.frac = max(0.0, min(1.0, f))
        self.queue_draw()

    def _draw(self, w, cr):
        a = w.get_allocation()
        r = min(a.width, a.height) / 2 - self.width
        cx, cy = a.width / 2, a.height / 2
        cr.set_line_width(self.width / 2)
        cr.set_source_rgba(1, 1, 1, 0.16)
        cr.arc(cx, cy, r, 0, 2 * math.pi)
        cr.stroke()
        if self.frac > 0:
            cr.set_line_width(self.width)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.set_source_rgba(*self.color)
            cr.arc(cx, cy, r, -math.pi / 2, -math.pi / 2 + 2 * math.pi * self.frac)
            cr.stroke()


def round_btn(icon, cb, accent=False, big=False, tip=None):
    b = Gtk.Button()
    add_cls(b, "round")
    if accent:
        add_cls(b, "accent")
    if big:
        add_cls(b, "big")
    ic = Icon(icon, 18 if big else 14, color=(0, 0, 0, 1) if accent else None)
    ic.set_halign(Gtk.Align.CENTER)
    b.add(ic)
    if tip:
        b.set_tooltip_text(tip)
    b.connect("clicked", lambda w: cb())
    return b


def center_icon(name, size, color=None):
    ic = Icon(name, size, color=color)
    ic.set_halign(Gtk.Align.CENTER)
    return ic


def set_round_icon(b, icon):
    b.get_child().set_icon(icon)


def spin(lo, hi, val, step=1, wrap=True, digits2=True):
    adj = Gtk.Adjustment(value=val, lower=lo, upper=hi, step_increment=step, page_increment=step * 5)
    s = Gtk.SpinButton(adjustment=adj)
    s.set_orientation(Gtk.Orientation.VERTICAL)
    s.set_wrap(wrap)
    s.set_numeric(True)
    if digits2:
        s.connect("output", lambda w: (w.set_text(f"{int(w.get_value()):02d}"), True)[1])
    return s


# ---------------------------------------------------------------- pages
class TimerPage(Gtk.Box):
    def __init__(self, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.win = win
        self.st = win.st
        self.run = {}   # id -> {"end": t or None, "left": secs, "running": bool}
        ov = Gtk.Overlay()
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.flow = Gtk.FlowBox()
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_homogeneous(True)
        self.flow.set_max_children_per_line(4)
        self.flow.set_column_spacing(12)
        self.flow.set_row_spacing(12)
        self.flow.set_valign(Gtk.Align.START)
        self.flow.set_margin_start(28)
        self.flow.set_margin_end(28)
        self.flow.set_margin_bottom(90)
        sw.add(self.flow)
        ov.add(sw)
        fab = Gtk.Button()
        add_cls(fab, "fab")
        fab.add(center_icon("add", 16, (0, 0, 0, 1)))
        fab.set_tooltip_text("Add new timer")
        fab.set_halign(Gtk.Align.END)
        fab.set_valign(Gtk.Align.END)
        fab.set_margin_end(28)
        fab.set_margin_bottom(24)
        fab.connect("clicked", lambda w: self.edit(None))
        ov.add_overlay(fab)
        self.pack_start(ov, True, True, 0)
        self.cards = {}
        self.fill()

    def fill(self):
        for c in self.flow.get_children():
            self.flow.remove(c)
        self.cards = {}
        for t in self.st["timers"]:
            self.flow.add(self._card(t))
        self.flow.show_all()
        self.tick()

    def _card(self, t):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        add_cls(box, "card")
        box.set_size_request(250, 280)
        top = Gtk.Box()
        top.set_margin_start(16)
        top.set_margin_end(8)
        top.set_margin_top(10)
        top.pack_start(label(t.get("name") or nice_len(t["secs"]), "card-name", ellipsize=True), True, True, 0)
        eb = Gtk.Button()
        add_cls(eb, "ghost")
        eb.add(Icon("edit", 14))
        eb.set_tooltip_text("Edit timer")
        eb.connect("clicked", lambda w: self.edit(t))
        top.pack_end(eb, False, False, 0)
        box.pack_start(top, False, False, 0)
        ov = Gtk.Overlay()
        ring = Ring(170, 6)
        ring.set_halign(Gtk.Align.CENTER)
        ov.add(ring)
        tl = label("", "big-time", xalign=0.5)
        tl.set_halign(Gtk.Align.CENTER)
        tl.set_valign(Gtk.Align.CENTER)
        ov.add_overlay(tl)
        box.pack_start(ov, True, True, 0)
        btns = Gtk.Box(spacing=12)
        btns.set_halign(Gtk.Align.CENTER)
        btns.set_margin_bottom(16)
        play = round_btn("play", lambda: self.toggle(t), accent=True, tip="Start")
        reset = round_btn("reset", lambda: self.reset(t), tip="Reset")
        btns.pack_start(play, False, False, 0)
        btns.pack_start(reset, False, False, 0)
        box.pack_start(btns, False, False, 0)
        self.cards[t["id"]] = (ring, tl, play, reset)
        return box

    def state(self, t):
        return self.run.setdefault(t["id"], {"end": None, "left": t["secs"], "running": False})

    def left(self, t):
        r = self.state(t)
        if r["running"]:
            return max(0.0, r["end"] - time.time())
        return r["left"]

    def toggle(self, t):
        r = self.state(t)
        if r["running"]:
            r["left"] = max(0.0, r["end"] - time.time())
            r["running"] = False
        else:
            if r["left"] <= 0:
                r["left"] = t["secs"]
            r["end"] = time.time() + r["left"]
            r["running"] = True
        self.win.app.ensure_ticking()
        self.tick()

    def reset(self, t):
        self.run[t["id"]] = {"end": None, "left": t["secs"], "running": False}
        self.tick()

    def any_running(self):
        return any(r["running"] for r in self.run.values())

    def tick(self):
        for t in self.st["timers"]:
            if t["id"] not in self.cards:
                continue
            ring, tl, play, reset = self.cards[t["id"]]
            r = self.state(t)
            left = self.left(t)
            if r["running"] and left <= 0:
                r["running"] = False
                r["left"] = 0
                self.win.app.timer_done(t)
            tl.set_text(fmt_hms(math.ceil(left)))
            ring.set_frac(left / t["secs"] if t["secs"] else 0)
            set_round_icon(play, "pause" if r["running"] else "play")
            play.set_tooltip_text("Pause" if r["running"] else "Start")
            reset.set_sensitive(r["running"] or abs(left - t["secs"]) > 0.5)

    def edit(self, t):
        new = t is None
        t = t or {"id": uuid.uuid4().hex[:8], "name": "", "secs": 300}
        grid = Gtk.Box(spacing=8)
        grid.set_halign(Gtk.Align.CENTER)
        hh, rem = divmod(t["secs"], 3600)
        mm, ss = divmod(rem, 60)
        sh, sm, ssb = spin(0, 99, hh), spin(0, 59, mm), spin(0, 59, ss)
        for s, cap in ((sh, "hours"), (sm, "minutes"), (ssb, "seconds")):
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            v.pack_start(s, False, False, 0)
            v.pack_start(label(cap, "card-sub", xalign=0.5), False, False, 0)
            grid.pack_start(v, False, False, 0)
        name = Gtk.Entry()
        add_cls(name, "field")
        name.set_placeholder_text("Timer name")
        name.set_text(t.get("name", ""))
        extra = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        extra.pack_start(grid, False, False, 0)
        extra.pack_start(name, False, False, 0)
        if not new:
            db = Gtk.Button(label="Delete timer")
            add_cls(db, "secondary")
            db.connect("clicked", lambda w: (dlg.done(False), self.delete(t)))
            extra.pack_start(db, False, False, 0)
        dlg = WinDialog(self.win, "Add new timer" if new else "Edit timer", primary="Save", secondary="Cancel", width=360, extra=extra)

        def done(ok):
            if not ok:
                return
            secs = int(sh.get_value()) * 3600 + int(sm.get_value()) * 60 + int(ssb.get_value())
            if secs <= 0:
                return
            t["secs"] = secs
            t["name"] = name.get_text().strip()
            if new:
                self.st["timers"].append(t)
            self.run.pop(t["id"], None)
            self.st.save()
            self.fill()
        dlg.ask(done)

    def delete(self, t):
        self.st["timers"] = [x for x in self.st["timers"] if x["id"] != t["id"]]
        self.run.pop(t["id"], None)
        self.st.save()
        self.fill()


class AlarmPage(Gtk.Box):
    def __init__(self, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.win = win
        self.st = win.st
        ov = Gtk.Overlay()
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.flow = Gtk.FlowBox()
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_homogeneous(True)
        self.flow.set_max_children_per_line(3)
        self.flow.set_column_spacing(12)
        self.flow.set_row_spacing(12)
        self.flow.set_valign(Gtk.Align.START)
        self.flow.set_margin_start(28)
        self.flow.set_margin_end(28)
        self.flow.set_margin_bottom(90)
        sw.add(self.flow)
        ov.add(sw)
        self.note = label("", "card-sub")
        self.note.set_margin_start(28)
        self.note.set_margin_bottom(8)
        fab = Gtk.Button()
        add_cls(fab, "fab")
        fab.add(center_icon("add", 16, (0, 0, 0, 1)))
        fab.set_tooltip_text("Add an alarm")
        fab.set_halign(Gtk.Align.END)
        fab.set_valign(Gtk.Align.END)
        fab.set_margin_end(28)
        fab.set_margin_bottom(24)
        fab.connect("clicked", lambda w: self.edit(None))
        ov.add_overlay(fab)
        self.pack_start(self.note, False, False, 0)
        self.pack_start(ov, True, True, 0)
        self.fill()

    def fill(self):
        for c in self.flow.get_children():
            self.flow.remove(c)
        for a in self.st["alarms"]:
            self.flow.add(self._card(a))
        self.flow.show_all()
        self.update_note()

    def update_note(self):
        nxt = self.win.app.next_alarm()
        if nxt:
            d = nxt[0] - datetime.datetime.now()
            h, r = divmod(int(d.total_seconds()) + 59, 3600)
            self.note.set_text(f"Next alarm in {h} hr {r // 60} min" if h else f"Next alarm in {r // 60} min")
        else:
            self.note.set_text("No alarms are on")

    def _card(self, a):
        ev = Gtk.EventBox()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        add_cls(box, "card")
        if not a.get("on"):
            add_cls(box, "alarm-off")
        box.set_size_request(300, 170)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        inner.set_margin_start(20)
        inner.set_margin_end(16)
        inner.set_margin_top(16)
        inner.set_margin_bottom(16)
        top = Gtk.Box()
        tm, ap = fmt_clock(a["h"], a["m"], self.st["h24"])
        tb = Gtk.Box()
        tb.pack_start(label(tm, "alarm-time"), False, False, 0)
        if ap:
            al = label(ap, "alarm-ampm")
            al.set_valign(Gtk.Align.END)
            al.set_margin_bottom(9)
            tb.pack_start(al, False, False, 0)
        top.pack_start(tb, True, True, 0)
        sw = Gtk.Switch()
        sw.set_active(bool(a.get("on")))
        sw.set_valign(Gtk.Align.START)
        sw.connect("notify::active", lambda w, p: self.set_on(a, w.get_active()))
        top.pack_end(sw, False, False, 0)
        inner.pack_start(top, False, False, 0)
        inner.pack_start(label(a.get("name") or "Alarm", "card-name", ellipsize=True), False, False, 0)
        days = Gtk.Box()
        if a.get("days"):
            for i, d in enumerate(DAYS):
                dl = label(d, "day")
                if i in a["days"]:
                    add_cls(dl, "on")
                days.pack_start(dl, False, False, 0)
        else:
            days.pack_start(label("Only once", "day"), False, False, 0)
        inner.pack_start(days, False, False, 0)
        sn = a.get("snooze", 10)
        inner.pack_start(label(f"{a.get('sound', 'Chimes')}  |  " + (f"Snooze {sn} min" if sn else "No snooze"), "card-sub"), False, False, 0)
        box.pack_start(inner, True, True, 0)
        ev.add(box)
        ev.connect("button-release-event", lambda w, e: self.edit(a) if e.button == 1 else None)
        return ev

    def set_on(self, a, on):
        if bool(a.get("on")) == on:
            return
        a["on"] = on
        a.pop("snooze_until", None)
        self.st.save()
        GLib.idle_add(self.fill)

    def edit(self, a):
        new = a is None
        now = datetime.datetime.now()
        a = a or {"id": uuid.uuid4().hex[:8], "name": "Alarm", "h": now.hour, "m": now.minute, "days": [],
                  "on": True, "sound": self.st.get("sound", "Chimes"), "snooze": 10}
        h24 = self.st["h24"]
        row = Gtk.Box(spacing=8)
        row.set_halign(Gtk.Align.CENTER)
        hh = a["h"] if h24 else ((a["h"] % 12) or 12)
        sh = spin(0, 23, hh) if h24 else spin(1, 12, hh, digits2=False)
        sm = spin(0, 59, a["m"])
        row.pack_start(sh, False, False, 0)
        row.pack_start(label(":", "alarm-time"), False, False, 0)
        row.pack_start(sm, False, False, 0)
        pm = {"v": a["h"] >= 12}
        if not h24:
            apb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            apb.set_valign(Gtk.Align.CENTER)
            amb, pmb = Gtk.Button(label="AM"), Gtk.Button(label="PM")

            def mark():
                for b, v in ((amb, False), (pmb, True)):
                    ctx = b.get_style_context()
                    ctx.remove_class("primary")
                    ctx.remove_class("secondary")
                    ctx.add_class("primary" if pm["v"] == v else "secondary")
            amb.connect("clicked", lambda w: (pm.update(v=False), mark()))
            pmb.connect("clicked", lambda w: (pm.update(v=True), mark()))
            mark()
            apb.pack_start(amb, False, False, 0)
            apb.pack_start(pmb, False, False, 0)
            row.pack_start(apb, False, False, 8)
        name = Gtk.Entry()
        add_cls(name, "field")
        name.set_placeholder_text("Alarm name")
        name.set_text(a.get("name", ""))
        days = set(a.get("days", []))
        dbox = Gtk.Box(spacing=6)
        dbox.set_halign(Gtk.Align.CENTER)
        for i, d in enumerate(DAYS):
            b = Gtk.Button(label=d[:2])
            add_cls(b, "daybtn")
            if i in days:
                add_cls(b, "on")

            def flip(w, i=i):
                if i in days:
                    days.discard(i)
                    w.get_style_context().remove_class("on")
                else:
                    days.add(i)
                    w.get_style_context().add_class("on")
            b.connect("clicked", flip)
            dbox.pack_start(b, False, False, 0)
        snd = Gtk.ComboBoxText()
        for s in SOUNDS:
            snd.append(s, s)
        snd.set_active_id(a.get("sound", "Chimes"))
        snd.connect("changed", lambda w: self.win.app.player.play(w.get_active_id(), loop=False))
        snz = Gtk.ComboBoxText()
        for s in SNOOZES:
            snz.append(str(s), f"{s} minutes" if s else "Off")
        snz.set_active_id(str(a.get("snooze", 10)))
        extra = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        extra.pack_start(row, False, False, 0)
        extra.pack_start(name, False, False, 0)
        extra.pack_start(label("Repeat", "card-sub"), False, False, 0)
        extra.pack_start(dbox, False, False, 0)
        for cap, w in (("Alarm sound", snd), ("Snooze time", snz)):
            r = Gtk.Box(spacing=12)
            r.pack_start(label(cap), True, True, 0)
            r.pack_end(w, False, False, 0)
            extra.pack_start(r, False, False, 0)
        if not new:
            db = Gtk.Button(label="Delete alarm")
            add_cls(db, "secondary")
            db.connect("clicked", lambda w: (dlg.done(False), self.delete(a)))
            extra.pack_start(db, False, False, 0)
        dlg = WinDialog(self.win, "Add new alarm" if new else "Edit alarm", primary="Save", secondary="Cancel", width=380, extra=extra)

        def done(ok):
            self.win.app.player.stop()
            if not ok:
                return
            h = int(sh.get_value())
            if not h24:
                h = (h % 12) + (12 if pm["v"] else 0)
            a.update(h=h, m=int(sm.get_value()), name=name.get_text().strip(), days=sorted(days),
                     sound=snd.get_active_id() or "Chimes", snooze=int(snz.get_active_id() or 10), on=True)
            a.pop("snooze_until", None)
            a.pop("last_fired", None)
            if new:
                self.st["alarms"].append(a)
            self.st.save()
            self.fill()
        dlg.ask(done)

    def delete(self, a):
        self.st["alarms"] = [x for x in self.st["alarms"] if x["id"] != a["id"]]
        self.st.save()
        self.fill()


class StopwatchPage(Gtk.Box):
    def __init__(self, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.win = win
        self.start = None
        self.acc = 0.0
        self.laps = []
        self.set_margin_start(28)
        self.set_margin_end(28)
        tb = Gtk.Box()
        tb.set_halign(Gtk.Align.CENTER)
        tb.set_margin_top(40)
        self.tmain = label("00:00:00", "huge-time")
        self.tfrac = label(".00", "huge-frac")
        tb.pack_start(self.tmain, False, False, 0)
        tb.pack_start(self.tfrac, False, False, 0)
        self.pack_start(tb, False, False, 0)
        caps = Gtk.Box(spacing=0)
        caps.set_halign(Gtk.Align.CENTER)
        for c, w in (("hr", 120), ("min", 120), ("sec", 120)):
            lb = label(c, "card-sub", xalign=0.5)
            lb.set_size_request(w, -1)
            caps.pack_start(lb, False, False, 0)
        self.pack_start(caps, False, False, 0)
        btns = Gtk.Box(spacing=20)
        btns.set_halign(Gtk.Align.CENTER)
        btns.set_margin_top(10)
        self.play = round_btn("play", self.toggle, accent=True, big=True, tip="Start")
        self.lapb = round_btn("flag", self.lap, big=True, tip="Lap")
        self.resetb = round_btn("reset", self.reset, big=True, tip="Reset")
        for b in (self.play, self.lapb, self.resetb):
            btns.pack_start(b, False, False, 0)
        self.pack_start(btns, False, False, 0)
        self.lap_head = Gtk.Box()
        self.lap_head.set_margin_top(16)
        for c in ("Laps", "Time", "Total"):
            self.lap_head.pack_start(label(c, "lap-head"), True, True, 0)
        self.pack_start(self.lap_head, False, False, 0)
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.lapbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sw.add(self.lapbox)
        self.pack_start(sw, True, True, 0)
        self.tick()

    def elapsed(self):
        return self.acc + (time.time() - self.start if self.start else 0)

    def running(self):
        return self.start is not None

    def toggle(self):
        if self.start:
            self.acc += time.time() - self.start
            self.start = None
        else:
            self.start = time.time()
            self.win.app.ensure_ticking()
        self.tick()

    def lap(self):
        total = self.elapsed()
        prev = self.laps[0][1] if self.laps else 0
        self.laps.insert(0, (total - prev, total))
        self.fill_laps()

    def reset(self):
        self.start = None
        self.acc = 0
        self.laps = []
        self.fill_laps()
        self.tick()

    def fill_laps(self):
        for c in self.lapbox.get_children():
            self.lapbox.remove(c)
        n = len(self.laps)
        if n > 1:
            fast = min(range(n), key=lambda i: self.laps[i][0])
            slow = max(range(n), key=lambda i: self.laps[i][0])
        else:
            fast = slow = -1
        for i, (lt, tot) in enumerate(self.laps):
            row = Gtk.Box()
            add_cls(row, "lap-row")
            tag = "  Fastest" if i == fast else ("  Slowest" if i == slow else "")
            row.pack_start(label(f"{n - i}{tag}", "lap"), True, True, 0)
            row.pack_start(label(self.fmt(lt), "lap"), True, True, 0)
            row.pack_start(label(self.fmt(tot), "lap"), True, True, 0)
            self.lapbox.pack_start(row, False, False, 0)
        self.lapbox.show_all()
        self.lap_head.set_visible(bool(self.laps))

    @staticmethod
    def fmt(s):
        cs = int(s * 100) % 100
        return fmt_hms(int(s)) + f".{cs:02d}"

    def tick(self):
        e = self.elapsed()
        self.tmain.set_text(fmt_hms(int(e)))
        self.tfrac.set_text(f".{int(e * 100) % 100:02d}")
        set_round_icon(self.play, "pause" if self.start else "play")
        self.lapb.set_sensitive(bool(self.start))
        self.resetb.set_sensitive(e > 0)
        self.lap_head.set_visible(bool(self.laps))


class WorldPage(Gtk.Box):
    def __init__(self, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.win = win
        self.st = win.st
        ov = Gtk.Overlay()
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.flow = Gtk.FlowBox()
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_homogeneous(True)
        self.flow.set_max_children_per_line(3)
        self.flow.set_column_spacing(12)
        self.flow.set_row_spacing(12)
        self.flow.set_valign(Gtk.Align.START)
        self.flow.set_margin_start(28)
        self.flow.set_margin_end(28)
        self.flow.set_margin_bottom(90)
        sw.add(self.flow)
        ov.add(sw)
        fab = Gtk.Button()
        add_cls(fab, "fab")
        fab.add(center_icon("add", 16, (0, 0, 0, 1)))
        fab.set_tooltip_text("Add a new city")
        fab.set_halign(Gtk.Align.END)
        fab.set_valign(Gtk.Align.END)
        fab.set_margin_end(28)
        fab.set_margin_bottom(24)
        fab.connect("clicked", lambda w: self.add_city())
        ov.add_overlay(fab)
        self.pack_start(ov, True, True, 0)
        self.labels = []
        self.fill()

    def local_zone(self):
        if os.environ.get("TZ", "").count("/"):
            return os.environ["TZ"].lstrip(":")
        try:
            return os.path.realpath("/etc/localtime").split("zoneinfo/", 1)[1]
        except (IndexError, OSError):
            return None

    def fill(self):
        for c in self.flow.get_children():
            self.flow.remove(c)
        self.labels = []
        lz = self.local_zone()
        self.flow.add(self._card(None, f"Local time{(' (' + ZONE_CITY.get(lz, lz.split('/')[-1].replace('_', ' ')) + ')') if lz else ''}"))
        for z in self.st["zones"]:
            self.flow.add(self._card(z, ZONE_CITY.get(z, z.split("/")[-1].replace("_", " "))))
        self.flow.show_all()
        self.tick()

    def _card(self, zone, title):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        add_cls(box, "card")
        box.set_size_request(300, 150)
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        inner.set_margin_start(20)
        inner.set_margin_end(12)
        inner.set_margin_top(14)
        inner.set_margin_bottom(16)
        top = Gtk.Box()
        top.pack_start(label(title, "card-name", ellipsize=True), True, True, 0)
        if zone:
            db = Gtk.Button()
            add_cls(db, "ghost")
            db.add(Icon("delete", 14))
            db.set_tooltip_text("Remove")
            db.connect("clicked", lambda w: self.remove(zone))
            top.pack_end(db, False, False, 0)
        inner.pack_start(top, False, False, 0)
        tl = label("", "zone-time")
        dl = label("", "card-sub")
        inner.pack_start(tl, False, False, 0)
        inner.pack_start(dl, False, False, 0)
        box.pack_start(inner, True, True, 0)
        self.labels.append((zone, tl, dl))
        return box

    def tick(self):
        now = datetime.datetime.now().astimezone()
        for zone, tl, dl in self.labels:
            if zone and ZoneInfo:
                try:
                    t = now.astimezone(ZoneInfo(zone))
                except Exception:
                    t = now
            else:
                t = now
            tm, ap = fmt_clock(t.hour, t.minute, self.st["h24"])
            tl.set_text(f"{tm} {ap}".strip())
            diff = (t.utcoffset() - now.utcoffset()).total_seconds() / 3600 if zone else 0
            day = t.strftime("%a, %b %d").replace(" 0", " ")
            if not zone:
                rel = "Your time"
            elif diff == 0:
                rel = "Same time"
            else:
                hrs = abs(diff)
                hs = f"{hrs:g} hr" + ("s" if hrs != 1 else "")
                rel = f"{hs} {'ahead' if diff > 0 else 'behind'}"
            if t.date() != now.date():
                rel += "  |  " + ("Tomorrow" if t.date() > now.date() else "Yesterday")
            dl.set_text(f"{day}  |  {rel}")

    def remove(self, z):
        self.st["zones"] = [x for x in self.st["zones"] if x != z]
        self.st.save()
        self.fill()

    def add_city(self):
        entry = Gtk.Entry()
        add_cls(entry, "field")
        entry.set_placeholder_text("Enter a city or time zone")
        lst = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_size_request(-1, 260)
        sw.add(lst)
        extra = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        extra.pack_start(entry, False, False, 0)
        extra.pack_start(sw, True, True, 0)
        dlg = WinDialog(self.win, "Add new city", primary=None, secondary="Cancel", width=400, extra=extra)
        zones = sorted(available_timezones()) if ZoneInfo else []

        def pick(z):
            if z not in self.st["zones"]:
                self.st["zones"].append(z)
                self.st.save()
                self.fill()
            dlg.done(False)

        def refill(*a):
            q = entry.get_text().strip().lower()
            for c in lst.get_children():
                lst.remove(c)
            res = [(c, z) for c, z in CITIES if q in c.lower()][:30]
            if q:
                seen = {z for _, z in res}
                res += [(z.split("/")[-1].replace("_", " "), z) for z in zones
                        if q in z.lower().replace("_", " ") and z not in seen][:20]
            for c, z in res:
                b = Gtk.Button()
                add_cls(b, "cityrow")
                h = Gtk.Box(spacing=10)
                h.pack_start(label(c), False, False, 0)
                h.pack_end(label(z, "card-sub"), False, False, 0)
                b.add(h)
                b.connect("clicked", lambda w, z=z: pick(z))
                lst.pack_start(b, False, False, 0)
            lst.show_all()
        entry.connect("changed", refill)
        refill()
        dlg.ask()
        entry.grab_focus()


class FocusPage(Gtk.Box):
    BLOCK = 25 * 60
    BREAK = 5 * 60

    def __init__(self, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.win = win
        self.st = win.st
        self.plan = []          # list of (kind, secs)
        self.idx = 0
        self.end = None
        self.left = 0
        self.paused = False
        self.set_margin_start(28)
        self.set_margin_end(28)
        row = Gtk.Box(spacing=16)
        row.set_homogeneous(True)
        # session card
        self.sess = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        add_cls(self.sess, "card")
        self.sess.set_size_request(-1, 400)
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        # setup view
        setup = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        setup.set_valign(Gtk.Align.CENTER)
        setup.set_halign(Gtk.Align.CENTER)
        setup.pack_start(label("Get ready to focus", "card-name", xalign=0.5), False, False, 0)
        setup.pack_start(label("Focus sessions help you get more done. Pick a length and start.", "card-sub", xalign=0.5, wrap=True), False, False, 0)
        lr = Gtk.Box(spacing=12)
        lr.set_halign(Gtk.Align.CENTER)
        self.len_spin = spin(15, 240, self.st["focus_len"], step=5, wrap=False, digits2=False)
        self.len_spin.connect("value-changed", lambda w: self._len_changed())
        lr.pack_start(self.len_spin, False, False, 0)
        lr.pack_start(label("mins", "card-sub"), False, False, 0)
        setup.pack_start(lr, False, False, 0)
        self.break_note = label("", "card-sub", xalign=0.5)
        setup.pack_start(self.break_note, False, False, 0)
        self.skip = Gtk.CheckButton(label="Skip breaks")
        self.skip.set_active(not self.st["focus_breaks"])
        self.skip.set_halign(Gtk.Align.CENTER)
        self.skip.connect("toggled", lambda w: self._len_changed())
        setup.pack_start(self.skip, False, False, 0)
        sb = Gtk.Button()
        add_cls(sb, "primary")
        sbx = Gtk.Box(spacing=8)
        sbx.pack_start(Icon("play", 12, color=(0, 0, 0, 1)), False, False, 0)
        sbx.pack_start(Gtk.Label(label="Start focus session"), False, False, 0)
        sb.add(sbx)
        sb.set_halign(Gtk.Align.CENTER)
        sb.connect("clicked", lambda w: self.start())
        setup.pack_start(sb, False, False, 6)
        self.stack.add_named(setup, "setup")
        # running view
        runv = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        runv.set_valign(Gtk.Align.CENTER)
        self.phase = label("", "card-name", xalign=0.5)
        runv.pack_start(self.phase, False, False, 0)
        ov = Gtk.Overlay()
        self.ring = Ring(220, 8)
        self.ring.set_halign(Gtk.Align.CENTER)
        ov.add(self.ring)
        tb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        tb.set_valign(Gtk.Align.CENTER)
        self.rtime = label("", "focus-big", xalign=0.5)
        tb.pack_start(self.rtime, False, False, 0)
        tb.pack_start(label("min", "ring-label", xalign=0.5), False, False, 0)
        ov.add_overlay(tb)
        runv.pack_start(ov, False, False, 0)
        self.rnote = label("", "card-sub", xalign=0.5)
        runv.pack_start(self.rnote, False, False, 0)
        rb = Gtk.Box(spacing=12)
        rb.set_halign(Gtk.Align.CENTER)
        self.pbtn = round_btn("pause", self.pause, accent=True, tip="Pause")
        rb.pack_start(self.pbtn, False, False, 0)
        rb.pack_start(round_btn("stop", self.stop, tip="End session"), False, False, 0)
        runv.pack_start(rb, False, False, 0)
        self.stack.add_named(runv, "run")
        self.sess.pack_start(self.stack, True, True, 0)
        row.pack_start(self.sess, True, True, 0)
        # daily progress card
        prog = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        add_cls(prog, "card")
        pin = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        pin.set_margin_start(22)
        pin.set_margin_end(22)
        pin.set_margin_top(18)
        top = Gtk.Box()
        top.pack_start(label("Daily progress", "card-name"), True, True, 0)
        eb = Gtk.Button()
        add_cls(eb, "ghost")
        eb.add(Icon("edit", 14))
        eb.set_tooltip_text("Change daily goal")
        eb.connect("clicked", lambda w: self.edit_goal())
        top.pack_end(eb, False, False, 0)
        pin.pack_start(top, False, False, 0)
        stats = Gtk.Box(spacing=8)
        stats.set_homogeneous(True)
        self.s_yday = label("", "stat-num", xalign=0.5)
        self.s_streak = label("", "stat-num", xalign=0.5)
        cg = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        ov2 = Gtk.Overlay()
        self.goal_ring = Ring(130, 8)
        ov2.add(self.goal_ring)
        gb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        gb.set_valign(Gtk.Align.CENTER)
        gb.pack_start(label("Daily goal", "ring-label", xalign=0.5), False, False, 0)
        self.s_goal = label("", "stat-num", xalign=0.5)
        gb.pack_start(self.s_goal, False, False, 0)
        self.s_goal_u = label("", "ring-label", xalign=0.5)
        gb.pack_start(self.s_goal_u, False, False, 0)
        ov2.add_overlay(gb)
        cg.pack_start(ov2, False, False, 0)
        for num, cap in ((self.s_yday, "Yesterday"), (None, None), (self.s_streak, "Streak")):
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            v.set_valign(Gtk.Align.CENTER)
            if num is None:
                stats.pack_start(cg, True, True, 0)
                continue
            v.pack_start(label(cap, "card-sub", xalign=0.5), False, False, 0)
            v.pack_start(num, False, False, 0)
            v.pack_start(label("minutes" if cap == "Yesterday" else "days", "card-sub", xalign=0.5), False, False, 0)
            stats.pack_start(v, True, True, 0)
        pin.pack_start(stats, False, False, 10)
        self.s_today = label("", "card-sub", xalign=0.5)
        pin.pack_start(self.s_today, False, False, 0)
        prog.pack_start(pin, True, True, 0)
        row.pack_start(prog, True, True, 0)
        row.set_margin_top(6)
        self.pack_start(row, False, False, 0)
        self._len_changed()
        self.update_stats()

    def _len_changed(self):
        mins = int(self.len_spin.get_value())
        self.st["focus_len"] = mins
        self.st["focus_breaks"] = not self.skip.get_active()
        n = sum(1 for k, _ in self._plan(mins * 60) if k == "break")
        self.break_note.set_text("You'll have no breaks." if n == 0 else f"You'll have {n} break{'s' if n > 1 else ''}.")

    def _plan(self, total):
        if not self.st["focus_breaks"] or total <= 30 * 60:
            return [("focus", total)]
        plan, left = [], total
        while left > 0:
            f = min(self.BLOCK, left)
            plan.append(("focus", f))
            left -= f
            if left > 0:
                b = min(self.BREAK, left)
                plan.append(("break", b))
                left -= b
        return plan

    def start(self):
        self.plan = self._plan(int(self.len_spin.get_value()) * 60)
        self.idx = 0
        self._begin()
        self.st.save()
        self.stack.set_visible_child_name("run")
        self.win.app.ensure_ticking()

    def _begin(self):
        kind, secs = self.plan[self.idx]
        self.left = secs
        self.end = time.time() + secs
        self.paused = False
        self.tick()

    def running(self):
        return self.end is not None and not self.paused

    def pause(self):
        if self.end is None:
            return
        if self.paused:
            self.end = time.time() + self.left
            self.paused = False
        else:
            self.left = max(0, self.end - time.time())
            self.paused = True
        self.tick()

    def stop(self):
        if self.plan and self.end is not None:
            kind, secs = self.plan[self.idx]
            if kind == "focus":
                self._log(secs - (self.left if self.paused else max(0, self.end - time.time())))
        self.end = None
        self.plan = []
        self.stack.set_visible_child_name("setup")
        self.update_stats()

    def _log(self, secs):
        day = datetime.date.today().isoformat()
        log = self.st["focus_log"]
        log[day] = log.get(day, 0) + int(secs)
        self.st.save()

    def tick(self):
        if self.end is None or not self.plan:
            return
        kind, secs = self.plan[self.idx]
        left = self.left if self.paused else max(0, self.end - time.time())
        if left <= 0 and not self.paused:
            if kind == "focus":
                self._log(secs)
            self.idx += 1
            if self.idx >= len(self.plan):
                self.end = None
                self.stack.set_visible_child_name("setup")
                self.update_stats()
                self.win.app.notify_done("Focus session finished", "Nice work. Take a moment before your next task.")
                return
            nk = self.plan[self.idx][0]
            self.win.app.notify_done("Time for a break" if nk == "break" else "Break is over",
                                     "Step away for a few minutes." if nk == "break" else "Back to focusing.", ring=False)
            self._begin()
            return
        self.phase.set_text("Break" if kind == "break" else "Focus period")
        self.rtime.set_text(str(math.ceil(left / 60)))
        self.ring.color = hexc("#6CCB5F") if kind == "break" else hexc(C_ACCENT)
        self.ring.set_frac(left / secs if secs else 0)
        nb = sum(1 for k, _ in self.plan[self.idx + 1:] if k == "break")
        self.rnote.set_text(("Paused  |  " if self.paused else "") +
                            (f"{nb} break{'s' if nb != 1 else ''} left" if nb else "No more breaks"))
        set_round_icon(self.pbtn, "play" if self.paused else "pause")

    def update_stats(self):
        log = self.st["focus_log"]
        today = datetime.date.today()
        tmin = log.get(today.isoformat(), 0) // 60
        ymin = log.get((today - datetime.timedelta(days=1)).isoformat(), 0) // 60
        goal = self.st["focus_goal"]
        streak = 0
        d = today if log.get(today.isoformat(), 0) // 60 >= goal else today - datetime.timedelta(days=1)
        while log.get(d.isoformat(), 0) // 60 >= goal and streak < 3650:
            streak += 1
            d -= datetime.timedelta(days=1)
        self.s_yday.set_text(str(ymin))
        self.s_streak.set_text(str(streak))
        self.s_goal.set_text(str(goal // 60) if goal % 60 == 0 else str(goal))
        self.s_goal_u.set_text("hour" + ("s" if goal != 60 else "") if goal % 60 == 0 else "minutes")
        self.goal_ring.set_frac(tmin / goal if goal else 0)
        self.s_today.set_text(f"Completed today: {tmin} minutes")

    def edit_goal(self):
        s = spin(15, 600, self.st["focus_goal"], step=15, wrap=False, digits2=False)
        box = Gtk.Box(spacing=10)
        box.set_halign(Gtk.Align.CENTER)
        box.pack_start(s, False, False, 0)
        box.pack_start(label("minutes a day"), False, False, 0)
        dlg = WinDialog(self.win, "Daily goal", primary="Save", secondary="Cancel", width=340, extra=box)

        def done(ok):
            if ok:
                self.st["focus_goal"] = int(s.get_value())
                self.st.save()
                self.update_stats()
        dlg.ask(done)


class SettingsPage(Gtk.Box):
    def __init__(self, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.win = win
        st = win.st
        self.set_margin_start(28)
        self.set_margin_end(28)

        def row(title, desc, widget):
            r = Gtk.Box(spacing=12)
            add_cls(r, "setting-row")
            v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            v.pack_start(label(title), False, False, 0)
            if desc:
                v.pack_start(label(desc, "card-sub", wrap=True), False, False, 0)
            r.pack_start(v, True, True, 0)
            widget.set_valign(Gtk.Align.CENTER)
            r.pack_end(widget, False, False, 0)
            self.pack_start(r, False, False, 0)
        sw = Gtk.Switch()
        sw.set_active(st["h24"])

        def set24(w, p):
            st["h24"] = w.get_active()
            st.save()
            self.win.alarm.fill()
            self.win.world.fill()
        sw.connect("notify::active", set24)
        row("24-hour clock", "Show times like 18:30 instead of 6:30 PM", sw)
        cb = Gtk.ComboBoxText()
        for s in SOUNDS:
            cb.append(s, s)
        cb.set_active_id(st["sound"])

        def setsnd(w):
            st["sound"] = w.get_active_id()
            st.save()
            self.win.app.player.play(st["sound"], loop=False)
        cb.connect("changed", setsnd)
        row("Timer sound", "Plays when a timer or focus session ends", cb)
        test = Gtk.Button(label="Play")
        add_cls(test, "secondary")
        test.connect("clicked", lambda w: self.win.app.player.play(st["sound"], loop=False))
        row("Test sound", "Check your speakers or headphones", test)
        note = label("Clock keeps running in the background after you close it, so alarms and timers still go off. "
                     "It also starts when you log in.", "card-sub", wrap=True)
        note.set_margin_top(10)
        self.pack_start(note, False, False, 0)


# ---------------------------------------------------------------- window
class ClockWindow(Gtk.ApplicationWindow):
    PAGES = [("focus", "Focus sessions", "focus"), ("timer", "Timer", "timer"), ("alarm", "Alarm", "alarm"),
             ("stopwatch", "Stopwatch", "stopwatch"), ("world", "World clock", "globe")]

    def __init__(self, app):
        super().__init__(application=app)
        self.app = app
        self.st = app.settings
        self.set_title("Clock")
        self.set_icon_name("pi-clock")
        add_cls(self, "fx")
        self.set_default_size(self.st["width"], self.st["height"])
        self.connect("delete-event", self._close)
        tb = WinTitlebar(self)
        t, _ = app_title("Clock", draw_logo)
        tb.pack_start(t)
        tb.show_all()
        root = Gtk.Box()
        nav = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        add_cls(nav, "navpane")
        nav.set_size_request(240, -1)
        self.navbtns = {}
        for key, name, icon in self.PAGES:
            nav.pack_start(self._navbtn(key, name, icon), False, False, 0)
        nav.pack_end(self._navbtn("settings", "Settings", "gear"), False, False, 0)
        root.pack_start(nav, False, False, 0)
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        add_cls(page, "page")
        self.title = label("", "page-title")
        self.title.set_margin_start(28)
        self.title.set_margin_top(20)
        self.title.set_margin_bottom(16)
        page.pack_start(self.title, False, False, 0)
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(120)
        self.focus = FocusPage(self)
        self.timer = app.timer_page(self)
        self.alarm = AlarmPage(self)
        self.stopwatch = StopwatchPage(self)
        self.world = WorldPage(self)
        for k, w in (("focus", self.focus), ("timer", self.timer), ("alarm", self.alarm),
                     ("stopwatch", self.stopwatch), ("world", self.world), ("settings", SettingsPage(self))):
            self.stack.add_named(w, k)
        page.pack_start(self.stack, True, True, 0)
        root.pack_start(page, True, True, 0)
        self.add(root)
        root.show_all()
        self.go(self.st.get("page", "timer"))
        self.connect("configure-event", self._cfg)

    def _navbtn(self, key, name, icon):
        b = Gtk.Button()
        add_cls(b, "nav")
        h = Gtk.Box(spacing=14)
        bar = Gtk.Box()
        add_cls(bar, "navbar")
        h.pack_start(bar, False, False, 0)
        h.pack_start(Icon(icon, 16), False, False, 0)
        h.pack_start(label(name), False, False, 0)
        b.add(h)
        b.connect("clicked", lambda w: self.go(key))
        self.navbtns[key] = (b, bar)
        return b

    def go(self, key):
        if key not in self.navbtns:
            key = "timer"
        for k, (b, bar) in self.navbtns.items():
            for w in (b, bar):
                ctx = w.get_style_context()
                if k == key:
                    ctx.add_class("sel")
                else:
                    ctx.remove_class("sel")
        self.stack.set_visible_child_name(key)
        names = dict((k, n) for k, n, _ in self.PAGES)
        names["settings"] = "Settings"
        self.title.set_text(names[key])
        self.st["page"] = key
        if key == "alarm":
            self.alarm.update_note()

    def _cfg(self, w, ev):
        if not self.is_maximized():
            self.st["width"], self.st["height"] = self.get_size()
        return False

    def _close(self, *a):
        self.st.save()
        self.hide()
        return True

    def tick(self):
        self.timer.tick()
        self.stopwatch.tick()
        self.focus.tick()
        if self.stack.get_visible_child_name() == "world":
            self.world.tick()


class RingWindow(Gtk.Window):
    """'Time's up' / alarm window with Snooze and Dismiss."""

    def __init__(self, app, title, body, snooze=None, on_snooze=None):
        super().__init__()
        self.app = app
        add_cls(self, "fx-dialog")
        self.set_title(title)
        self.set_icon_name("pi-clock")
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_default_size(360, -1)
        self.set_position(Gtk.WindowPosition.CENTER)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        add_cls(box, "dlg-body")
        h = Gtk.Box(spacing=10)
        da = Gtk.DrawingArea()
        da.set_size_request(20, 20)
        da.connect("draw", lambda w, cr: draw_logo(cr, 20))
        h.pack_start(da, False, False, 0)
        h.pack_start(label("Clock", "card-sub"), False, False, 0)
        box.pack_start(h, False, False, 0)
        box.pack_start(label(title, "ring-title"), False, False, 0)
        box.pack_start(label(body, "card-sub", wrap=True), False, False, 0)
        foot = Gtk.Box(spacing=8, homogeneous=True)
        add_cls(foot, "dlg-foot")
        if snooze:
            sb = Gtk.Button(label=f"Snooze {snooze} min")
            add_cls(sb, "secondary")
            sb.connect("clicked", lambda w: (on_snooze(), self.close_ring()))
            foot.pack_start(sb, True, True, 0)
        db = Gtk.Button(label="Dismiss")
        add_cls(db, "primary")
        db.connect("clicked", lambda w: self.close_ring())
        foot.pack_start(db, True, True, 0)
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.pack_start(box, True, True, 0)
        outer.pack_start(foot, False, False, 0)
        self.add(outer)
        self.connect("delete-event", lambda *a: (self.close_ring(), True)[1])
        self.show_all()
        self.present()

    def close_ring(self):
        self.app.player.stop()
        self.destroy()


# ---------------------------------------------------------------- app
class ClockApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.win = None
        self.tick_id = None
        self.player = Player()

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.settings = JsonSettings("pi-clock", DEFAULTS)
        apply_css(CSS)
        try:
            make_sounds()
        except OSError:
            pass
        self.hold()
        GLib.timeout_add_seconds(1, self.check_alarms)
        GLib.timeout_add_seconds(30, lambda: (self.settings.save(), True)[1])

    def timer_page(self, win):
        return TimerPage(win)

    def ensure_ticking(self):
        if self.tick_id is None:
            self.tick_id = GLib.timeout_add(50, self._tick)

    def _tick(self):
        if self.win:
            self.win.tick()
            busy = self.win.timer.any_running() or self.win.stopwatch.running() or self.win.focus.running()
            if busy:
                return True
        self.tick_id = None
        return False

    def window(self):
        if self.win is None:
            self.win = ClockWindow(self)
        return self.win

    # ---- alarms
    def next_alarm(self):
        now = datetime.datetime.now()
        best = None
        for a in self.settings["alarms"]:
            if not a.get("on"):
                continue
            if a.get("snooze_until"):
                t = datetime.datetime.fromtimestamp(a["snooze_until"])
                if t > now and (best is None or t < best[0]):
                    best = (t, a)
                continue
            for add in range(8):
                d = now.date() + datetime.timedelta(days=add)
                t = datetime.datetime.combine(d, datetime.time(a["h"], a["m"]))
                if t <= now:
                    continue
                if a.get("days") and (d.isoweekday() % 7) not in a["days"]:
                    continue
                if best is None or t < best[0]:
                    best = (t, a)
                break
        return best

    def check_alarms(self):
        now = datetime.datetime.now()
        key = now.strftime("%Y-%m-%d %H:%M")
        changed = False
        for a in self.settings["alarms"]:
            if not a.get("on"):
                continue
            due = False
            if a.get("snooze_until"):
                if time.time() >= a["snooze_until"]:
                    a.pop("snooze_until")
                    due = True
            elif now.hour == a["h"] and now.minute == a["m"] and a.get("last_fired") != key:
                if not a.get("days") or (now.isoweekday() % 7) in a["days"]:
                    due = True
                    a["last_fired"] = key
            if due:
                changed = True
                if not a.get("days") and not a.get("snooze_until"):
                    a["on"] = False
                self.ring_alarm(a)
        if changed:
            self.settings.save()
            if self.win:
                self.win.alarm.fill()
        return True

    def ring_alarm(self, a):
        tm, ap = fmt_clock(a["h"], a["m"], self.settings["h24"])
        self.player.play(a.get("sound", "Chimes"))
        sn = a.get("snooze", 10)

        def snooze():
            a["snooze_until"] = time.time() + sn * 60
            a["on"] = True
            self.settings.save()
            if self.win:
                self.win.alarm.fill()
        self._notify(a.get("name") or "Alarm", f"{tm} {ap}".strip())
        RingWindow(self, a.get("name") or "Alarm", f"{tm} {ap}".strip(), snooze=sn or None, on_snooze=snooze)

    def timer_done(self, t):
        name = t.get("name") or nice_len(t["secs"]) + " timer"
        self.player.play(self.settings.get("sound", "Chimes"))
        self._notify("Time's up", name)
        RingWindow(self, "Time's up", name)

    def notify_done(self, title, body, ring=True):
        self.player.play(self.settings.get("sound", "Chimes"), loop=False)
        self._notify(title, body)
        if ring:
            RingWindow(self, title, body)

    def _notify(self, title, body):
        try:
            n = Gio.Notification.new(title)
            n.set_body(body)
            self.send_notification(None, n)
        except Exception:
            pass

    def do_command_line(self, cmd):
        args = cmd.get_arguments()[1:]
        if "--quit" in args:
            self.settings.save()
            self.quit()
            return 0
        if "--background" in args:
            return 0
        w = self.window()
        for a in args:
            if a.startswith("--page="):
                w.go(a.split("=", 1)[1])
        w.show()
        w.present()
        return 0


def main():
    GLib.set_prgname("pi-clock")
    GLib.set_application_name("Clock")
    app = ClockApp()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
