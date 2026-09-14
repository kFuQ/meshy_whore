"""Thumbnail loading helpers.

Uses Pillow when available for high-quality thumbnails of any format; falls
back to Tk's native PNG/GIF support otherwise. Never raises — returns ``None``
when an image cannot be rendered so the UI can show a placeholder.
"""
from __future__ import annotations

import tkinter as tk

try:
    from PIL import Image, ImageTk  # type: ignore

    _HAS_PIL = True
except Exception:  # pragma: no cover
    _HAS_PIL = False


def has_pillow() -> bool:
    return _HAS_PIL


def load_thumbnail(path_or_bytes, size: int = 96):
    """Return a Tk image object thumbnailed to fit ``size`` px, or ``None``."""
    try:
        if _HAS_PIL:
            if isinstance(path_or_bytes, (bytes, bytearray)):
                import io

                img = Image.open(io.BytesIO(path_or_bytes))
            else:
                img = Image.open(path_or_bytes)
            img = img.convert("RGBA")
            img.thumbnail((size, size))
            return ImageTk.PhotoImage(img)
        # Tk-native path: only PNG/GIF from a filesystem path.
        if isinstance(path_or_bytes, (bytes, bytearray)):
            return None
        photo = tk.PhotoImage(file=str(path_or_bytes))
        # Subsample down to roughly the requested size.
        w = photo.width()
        if w > size:
            factor = max(1, w // size)
            photo = photo.subsample(factor, factor)
        return photo
    except Exception:
        return None
