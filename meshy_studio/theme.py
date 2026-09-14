"""Central theme tokens.

All colours used anywhere in the UI come from one of these named tokens, so
there are no hard-coded colour literals in the widget code. Switching the
active palette (light / dark / high-contrast) re-themes the whole app.
"""
from __future__ import annotations

from dataclasses import dataclass

THEME_NAMES = ("light", "dark", "high-contrast")


@dataclass(frozen=True)
class Palette:
    name: str
    bg: str            # window background
    surface: str       # cards / panels
    surface_alt: str   # secondary panels, list stripes
    border: str        # separators / outlines
    fg: str            # primary text
    fg_muted: str      # secondary text
    accent: str        # primary action
    accent_fg: str     # text on accent
    accent_hover: str
    field_bg: str      # entry / input background
    field_fg: str
    success: str
    warning: str
    danger: str
    focus: str         # focus ring / selection


_LIGHT = Palette(
    name="light",
    bg="#f4f5f7",
    surface="#ffffff",
    surface_alt="#eef0f3",
    border="#d3d7de",
    fg="#1b1f24",
    fg_muted="#5b6472",
    accent="#4c5fd5",
    accent_fg="#ffffff",
    accent_hover="#3d4fc0",
    field_bg="#ffffff",
    field_fg="#1b1f24",
    success="#1f8a4c",
    warning="#b26a00",
    danger="#c0392b",
    focus="#4c5fd5",
)

_DARK = Palette(
    name="dark",
    bg="#14161a",
    surface="#1d2027",
    surface_alt="#262a33",
    border="#333844",
    fg="#e8eaed",
    fg_muted="#9aa3b2",
    accent="#7c8cff",
    accent_fg="#0f1115",
    accent_hover="#95a2ff",
    field_bg="#101216",
    field_fg="#e8eaed",
    success="#4cc38a",
    warning="#e0a13a",
    danger="#f2795f",
    focus="#7c8cff",
)

# WCAG AAA-oriented, maximum contrast, no mid-tones.
_HIGH_CONTRAST = Palette(
    name="high-contrast",
    bg="#000000",
    surface="#000000",
    surface_alt="#0a0a0a",
    border="#ffffff",
    fg="#ffffff",
    fg_muted="#ffff00",
    accent="#ffff00",
    accent_fg="#000000",
    accent_hover="#ffffff",
    field_bg="#000000",
    field_fg="#ffffff",
    success="#00ff66",
    warning="#ffcc00",
    danger="#ff5555",
    focus="#ffff00",
)

_PALETTES = {
    "light": _LIGHT,
    "dark": _DARK,
    "high-contrast": _HIGH_CONTRAST,
}


def resolve_theme(name: str) -> str:
    """Map a stored preference (incl. 'system') to a concrete palette name."""
    if name in _PALETTES:
        return name
    if name == "system":
        return _detect_system_theme()
    return "light"


def get_palette(name: str) -> Palette:
    return _PALETTES[resolve_theme(name)]


def _detect_system_theme() -> str:
    """Best-effort OS dark-mode detection; defaults to light."""
    import os
    import subprocess

    try:
        if os.sys.platform == "darwin":
            out = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if "Dark" in out.stdout:
                return "dark"
            return "light"
        if os.name == "posix":
            out = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if "dark" in out.stdout.lower():
                return "dark"
    except Exception:
        pass
    return "light"
