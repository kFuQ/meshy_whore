"""Small reusable Tk widgets."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class ScrollableFrame(ttk.Frame):
    """A vertically scrollable container. Put content in ``self.body``."""

    def __init__(self, parent, bg: str, **kwargs):
        super().__init__(parent, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0, background=bg, bd=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical",
                                       command=self.canvas.yview,
                                       style="Vertical.TScrollbar")
        self.body = ttk.Frame(self.canvas, style="TFrame")

        self._win = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self.body.bind("<Configure>", self._on_body_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        # Mouse wheel (bound while pointer is over the canvas).
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)

    def set_bg(self, bg: str) -> None:
        self.canvas.configure(background=bg)

    def _on_body_configure(self, _evt=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, evt) -> None:
        self.canvas.itemconfigure(self._win, width=evt.width)

    def _bind_wheel(self, _evt=None) -> None:
        self.canvas.bind_all("<MouseWheel>", self._on_wheel)
        self.canvas.bind_all("<Button-4>", self._on_wheel)
        self.canvas.bind_all("<Button-5>", self._on_wheel)

    def _unbind_wheel(self, _evt=None) -> None:
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_wheel(self, evt) -> None:
        if getattr(evt, "num", None) == 4:
            delta = -1
        elif getattr(evt, "num", None) == 5:
            delta = 1
        else:
            delta = -1 if evt.delta > 0 else 1
        self.canvas.yview_scroll(delta, "units")


class Tooltip:
    """A lightweight hover tooltip."""

    def __init__(self, widget, text: str, bg: str, fg: str):
        self.widget = widget
        self.text = text
        self.bg = bg
        self.fg = fg
        self._tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def update_colors(self, bg: str, fg: str) -> None:
        self.bg, self.fg = bg, fg

    def _show(self, _evt=None) -> None:
        if self._tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 16
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self._tip = tk.Toplevel(self.widget)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(self._tip, text=self.text, justify="left", background=self.bg,
                       foreground=self.fg, relief="solid", borderwidth=1,
                       wraplength=320, padx=8, pady=5, font=("TkDefaultFont", 9))
        lbl.pack()

    def _hide(self, _evt=None) -> None:
        if self._tip:
            self._tip.destroy()
            self._tip = None
