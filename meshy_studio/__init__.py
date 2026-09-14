"""Meshy Studio — a clean desktop client for fal.ai's Meshy v7 model."""
from __future__ import annotations

from .config import APP_NAME, APP_VERSION

__all__ = ["APP_NAME", "APP_VERSION", "run"]


def run() -> int:
    """Launch the desktop application. Returns a process exit code."""
    # Optional: load FAL_KEY (and friends) from a local .env file.
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass

    try:
        import tkinter as tk
    except Exception as exc:  # pragma: no cover
        import sys

        print(
            "Meshy Studio needs Tk (tkinter), which isn't available in this "
            f"Python build: {exc}\n"
            "Install it (e.g. 'sudo apt install python3-tk', or use the "
            "python.org installer on macOS/Windows) and try again.",
            file=sys.stderr,
        )
        return 2

    from .ui.app import MeshyStudioApp

    root = tk.Tk()
    try:
        root.tk.call("tk", "scaling", 1.2)
    except tk.TclError:
        pass
    MeshyStudioApp(root)
    root.mainloop()
    return 0
