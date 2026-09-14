"""Apply a :class:`~meshy_studio.theme.Palette` to ttk styles.

Uses the ``clam`` ttk theme as a base because it is the most customisable,
then drives every widget colour from palette tokens. No colour literals live
in the widget code — they all flow from here.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..theme import Palette

FONT_FAMILY = "TkDefaultFont"
BASE_FONT = (FONT_FAMILY, 10)
BOLD_FONT = (FONT_FAMILY, 10, "bold")
H1_FONT = (FONT_FAMILY, 16, "bold")
H2_FONT = (FONT_FAMILY, 12, "bold")
SMALL_FONT = (FONT_FAMILY, 9)
MONO_FONT = ("TkFixedFont", 9)


def apply_palette(root: tk.Misc, style: ttk.Style, p: Palette) -> None:
    """Configure all ttk styles + root option database from palette ``p``."""
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(background=p.bg)

    # ---- base widgets ----
    style.configure(".", background=p.bg, foreground=p.fg, font=BASE_FONT,
                    bordercolor=p.border, focuscolor=p.focus)
    style.configure("TFrame", background=p.bg)
    style.configure("Card.TFrame", background=p.surface, relief="flat")
    style.configure("Alt.TFrame", background=p.surface_alt)

    style.configure("TLabel", background=p.bg, foreground=p.fg, font=BASE_FONT)
    style.configure("Card.TLabel", background=p.surface, foreground=p.fg)
    style.configure("Muted.TLabel", background=p.bg, foreground=p.fg_muted, font=SMALL_FONT)
    style.configure("CardMuted.TLabel", background=p.surface, foreground=p.fg_muted, font=SMALL_FONT)
    style.configure("H1.TLabel", background=p.bg, foreground=p.fg, font=H1_FONT)
    style.configure("H2.TLabel", background=p.bg, foreground=p.fg, font=H2_FONT)
    style.configure("CardH2.TLabel", background=p.surface, foreground=p.fg, font=H2_FONT)
    style.configure("Success.TLabel", background=p.bg, foreground=p.success, font=BOLD_FONT)
    style.configure("Warning.TLabel", background=p.bg, foreground=p.warning, font=BOLD_FONT)
    style.configure("Danger.TLabel", background=p.bg, foreground=p.danger, font=BOLD_FONT)

    # ---- buttons ----
    style.configure("TButton", background=p.surface_alt, foreground=p.fg,
                    bordercolor=p.border, focusthickness=2, focuscolor=p.focus,
                    padding=(12, 7), relief="flat", font=BASE_FONT)
    style.map(
        "TButton",
        background=[("active", p.border), ("pressed", p.border), ("disabled", p.surface)],
        foreground=[("disabled", p.fg_muted)],
    )

    style.configure("Accent.TButton", background=p.accent, foreground=p.accent_fg,
                    bordercolor=p.accent, padding=(14, 8), font=BOLD_FONT)
    style.map(
        "Accent.TButton",
        background=[("active", p.accent_hover), ("pressed", p.accent_hover),
                    ("disabled", p.surface_alt)],
        foreground=[("disabled", p.fg_muted)],
    )

    style.configure("Danger.TButton", background=p.danger, foreground=p.accent_fg,
                    bordercolor=p.danger, padding=(12, 7))
    style.map("Danger.TButton", background=[("active", p.danger), ("pressed", p.danger)])

    style.configure("Ghost.TButton", background=p.surface, foreground=p.accent,
                    bordercolor=p.surface, padding=(8, 5))
    style.map("Ghost.TButton", background=[("active", p.surface_alt)])

    # ---- inputs ----
    style.configure("TEntry", fieldbackground=p.field_bg, foreground=p.field_fg,
                    bordercolor=p.border, insertcolor=p.fg, padding=6)
    style.map("TEntry", bordercolor=[("focus", p.focus)])

    style.configure("TSpinbox", fieldbackground=p.field_bg, foreground=p.field_fg,
                    bordercolor=p.border, arrowcolor=p.fg, insertcolor=p.fg, padding=4)
    style.map("TSpinbox", bordercolor=[("focus", p.focus)])

    style.configure("TCombobox", fieldbackground=p.field_bg, foreground=p.field_fg,
                    background=p.surface_alt, bordercolor=p.border, arrowcolor=p.fg,
                    padding=5)
    style.map("TCombobox",
              fieldbackground=[("readonly", p.field_bg)],
              bordercolor=[("focus", p.focus)],
              foreground=[("readonly", p.field_fg)])
    # The dropdown list is a classic Tk Listbox — theme via the option DB.
    root.option_add("*TCombobox*Listbox.background", p.field_bg)
    root.option_add("*TCombobox*Listbox.foreground", p.field_fg)
    root.option_add("*TCombobox*Listbox.selectBackground", p.accent)
    root.option_add("*TCombobox*Listbox.selectForeground", p.accent_fg)

    style.configure("TCheckbutton", background=p.bg, foreground=p.fg,
                    indicatorcolor=p.field_bg, focuscolor=p.focus)
    style.map("TCheckbutton",
              indicatorcolor=[("selected", p.accent), ("active", p.surface_alt)],
              background=[("active", p.bg)])
    style.configure("Card.TCheckbutton", background=p.surface, foreground=p.fg,
                    indicatorcolor=p.field_bg)
    style.map("Card.TCheckbutton",
              indicatorcolor=[("selected", p.accent), ("active", p.surface_alt)],
              background=[("active", p.surface)])

    # ---- scale / progress ----
    style.configure("Horizontal.TScale", background=p.bg, troughcolor=p.surface_alt)
    style.configure("TProgressbar", background=p.accent, troughcolor=p.surface_alt,
                    bordercolor=p.border, lightcolor=p.accent, darkcolor=p.accent)

    # ---- notebook ----
    style.configure("TNotebook", background=p.bg, bordercolor=p.border, tabmargins=(4, 4, 4, 0))
    style.configure("TNotebook.Tab", background=p.surface_alt, foreground=p.fg_muted,
                    padding=(16, 8), font=BASE_FONT, bordercolor=p.border)
    style.map("TNotebook.Tab",
              background=[("selected", p.surface)],
              foreground=[("selected", p.fg)],
              expand=[("selected", (1, 1, 1, 0))])

    # ---- separators / scrollbars ----
    style.configure("TSeparator", background=p.border)
    style.configure("Vertical.TScrollbar", background=p.surface_alt, troughcolor=p.bg,
                    bordercolor=p.border, arrowcolor=p.fg)
    style.map("Vertical.TScrollbar", background=[("active", p.border)])
    style.configure("Horizontal.TScrollbar", background=p.surface_alt, troughcolor=p.bg,
                    bordercolor=p.border, arrowcolor=p.fg)

    style.configure("TLabelframe", background=p.bg, foreground=p.fg, bordercolor=p.border)
    style.configure("TLabelframe.Label", background=p.bg, foreground=p.fg_muted, font=BOLD_FONT)

    # ---- treeview (history) ----
    style.configure("Treeview", background=p.surface, fieldbackground=p.surface,
                    foreground=p.fg, bordercolor=p.border, rowheight=26, font=BASE_FONT)
    style.map("Treeview",
              background=[("selected", p.accent)],
              foreground=[("selected", p.accent_fg)])
    style.configure("Treeview.Heading", background=p.surface_alt, foreground=p.fg_muted,
                    font=BOLD_FONT, relief="flat", padding=6)
    style.map("Treeview.Heading", background=[("active", p.border)])
