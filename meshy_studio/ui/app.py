"""Meshy Studio — main Tkinter application window."""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

from .. import config
from ..fal_service import is_available as fal_available, import_hint
from ..schema import (
    ANIM_ACTION_MAX,
    ANIM_ACTION_MIN,
    MeshyParams,
    POLYCOUNT_MAX,
    POLYCOUNT_MIN,
    POSE_VALUES,
    SYMMETRY_VALUES,
    TOPOLOGY_VALUES,
    iter_result_files,
)
from ..store import SecureStore
from ..theme import THEME_NAMES, get_palette, resolve_theme
from ..timeutils import format_local, now_utc
from ..worker import GenerationJob, WorkerEvent
from .images import load_thumbnail
from .styling import BASE_FONT, MONO_FONT, SMALL_FONT, apply_palette
from .widgets import ScrollableFrame, Tooltip

PARAM_HELP = {
    "topology": "Quad for smooth surfaces, Triangle for detailed geometry.",
    "target_polycount": "Target polygon count of the generated mesh (100–300,000).",
    "symmetry_mode": "Controls symmetry behaviour during generation.",
    "should_remesh": "When off, returns a raw triangular mesh and ignores topology / polycount.",
    "should_texture": "Generate textures for the model.",
    "enable_pbr": "Generate PBR maps (metallic, roughness, normal). Requires textures.",
    "pose_mode": "Force an A-pose or T-pose, or leave unset for no specific pose.",
    "texture_prompt": "Optional text prompt to guide texturing. Requires textures.",
    "texture_image_url": "Optional 2D image URL to guide texturing. Requires textures.",
    "enable_rigging": "Auto-rig a humanoid character with walk/run animations.",
    "rigging_height_meters": "Approximate character height in metres. Requires rigging.",
    "enable_animation": "Apply an animation preset to the rigged model. Requires rigging.",
    "animation_action_id": "Meshy animation preset ID (0–696; 0 = Idle). Requires animation.",
    "enable_safety_checker": "Check input images for safety before processing.",
}

# Longer, menu-facing explanations of each parameter (Help → Parameter Guide).
PARAM_GUIDE = [
    ("Input images",
     "Add 1 to 4 photos of the SAME object from different angles (front, side, "
     "back…). More consistent angles generally yield a better model. Supported: "
     "JPG, PNG, AVIF, HEIC/HEIF, up to 25 MB each."),
    ("Topology",
     "How the mesh is wired. 'triangle' gives detailed geometry and is the safe "
     "default; 'quad' produces cleaner edge loops for smooth surfaces and is "
     "friendlier to sculpting/subdivision in DCC tools."),
    ("Target polycount",
     "Roughly how many polygons you want (100–300,000; default 30,000). The "
     "actual count varies with the object's complexity. Lower = lighter for "
     "real-time/games; higher = more detail. Ignored when Remesh is off."),
    ("Symmetry mode",
     "'auto' lets the model decide; 'on' enforces left/right symmetry (good for "
     "characters and symmetric props); 'off' preserves asymmetric detail."),
    ("Remesh",
     "On (default) produces clean topology honouring the topology + polycount "
     "settings. Turn it OFF to get the raw triangular mesh straight from "
     "reconstruction — those two settings are then ignored."),
    ("Generate textures",
     "On (default) paints the model with colour textures. Turn off for an "
     "untextured mesh (faster/cheaper) when you only need geometry."),
    ("Generate PBR maps",
     "Adds metallic, roughness and normal maps alongside base colour for "
     "physically-based rendering. Requires 'Generate textures'."),
    ("Pose mode",
     "For humanoids: force an A-pose or T-pose (handy for rigging), or leave "
     "'(none)' to keep the pose implied by your images."),
    ("Texture prompt",
     "Optional text to steer the look of the textures (e.g. 'weathered bronze'). "
     "Requires 'Generate textures'."),
    ("Texture image URL",
     "Optional URL of a 2D image to guide texturing/style. Requires "
     "'Generate textures'."),
    ("Auto-rig (humanoid)",
     "Automatically rigs a humanoid character and includes basic walk/run "
     "animations. Works best on characters with clearly defined limbs."),
    ("Rig height (m)",
     "Approximate real-world height of the character in metres (default 1.7). "
     "Only used when auto-rig is on."),
    ("Apply animation preset",
     "Applies one of Meshy's animation presets to the rigged model. Requires "
     "auto-rig."),
    ("Animation action ID",
     "Which animation preset to apply (0–696; 0 = Idle). See Meshy's animation "
     "library for the full list. Only used when 'Apply animation preset' is on."),
    ("Safety checker",
     "On by default: input images are screened for safety before processing."),
]

_HELP_GETTING_STARTED = """# Getting Started

Meshy Studio turns photos of an object into a textured 3D model using fal.ai's
Meshy v7 model.

## 1. Add your API key
Open File → Set API Key… (or the Settings tab) and paste your fal.ai key.
It is encrypted on this device with AES-256-GCM. Don't have one yet? See
Help → How to Get an API Key.

## 2. Choose an output folder
File → Set Output Directory… picks where finished models are saved. By default
that's a "MeshyStudioOutputs" folder in your home directory.

## 3. Add 1–4 images
On the Generate tab, click "Add images…" and select up to four photos of the
SAME object from different angles.

## 4. Set parameters (optional)
The defaults produce a textured, ~30k-polygon model. Hover the ⓘ icons for a
quick note on each option, or read Help → Parameter Guide for details.

## 5. Generate
Click "Generate 3D Model". Progress appears in the Status panel and you can
Cancel at any time. When it finishes, every output file (GLB, FBX, OBJ, USDZ,
textures, animations) is listed and — if auto-download is on — saved to your
output folder. Click "Open output folder" to find them.

## Where things are saved
Your encrypted key and history live in the app data directory (shown at the
bottom of the Settings tab). Models are saved to your chosen output folder.

## Note on privacy
Images you add are uploaded to fal.ai for processing. Only upload images you
have the rights to use.
"""

_HELP_API_KEY = """# How to Get a fal.ai API Key

You need a fal.ai account and an API key to generate models.

## Steps
## 1. Create an account
Go to https://fal.ai and sign up (or log in).

## 2. Open the API Keys page
Visit https://fal.ai/dashboard/keys — you can also reach it from your fal.ai
dashboard under "API Keys".

## 3. Create a key
Click "Add key" / "Create key", give it a name, and copy the value shown.
You usually can't view it again later, so copy it now.

## 4. Add billing if required
Generating 3D models consumes fal.ai credits. Add a payment method / credits in
your fal.ai billing settings if prompted.

## 5. Paste it into Meshy Studio
File → Set API Key… → paste → Save. It's stored encrypted on this device.

## Advanced
You can instead set a FAL_KEY environment variable before launching the app;
if present, it's used for that session and takes precedence over the stored key.

## Keep it secret
Treat the key like a password. Meshy Studio never logs it and never stores it in
your job history. If a key leaks, revoke it on the fal.ai keys page and create a
new one.
"""

_HELP_ABOUT = f"""# {config.APP_NAME} v{config.APP_VERSION}

A clean desktop client for the fal.ai Meshy v7 multi-image-to-3D model.

## What it does
Reconstructs a textured, game-ready 3D model from 1–4 images of one object,
with control over topology, polycount, symmetry, textures/PBR, pose, rigging
and animation.

## Privacy & security
• Your API key and job history are encrypted at rest with AES-256-GCM.
• The app talks only to fal.ai, and only to run the generation you request.
• All times are shown in your local time zone.

## Links
fal.ai model page: https://fal.ai/models/meshy/v7/multi-image-to-3d
fal.ai Terms & Privacy: https://fal.ai/legal/terms-of-service

Review fal.ai's Terms of Service and Privacy Policy before uploading images you
do not own the rights to.
"""


def _build_parameter_guide() -> str:
    parts = ["# Parameter Guide", ""]
    for name, desc in PARAM_GUIDE:
        parts.append(f"## {name}")
        parts.append(desc)
        parts.append("")
    return "\n".join(parts)


class MeshyStudioApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.store = SecureStore()
        self.settings = self.store.load_settings()
        self.history = self.store.load_history()

        self.events: "queue.Queue[WorkerEvent]" = queue.Queue()
        self.current_job: GenerationJob | None = None
        self.image_paths: list[str] = []
        self._thumb_refs: list[object] = []  # keep PhotoImage refs alive
        self._preview_ref = None
        self._tooltips: list[Tooltip] = []
        self.last_result: dict | None = None

        self.theme_name = self.settings.get("theme", "system")
        self.palette = get_palette(self.theme_name)

        self.style = ttk.Style(self.root)
        self._build_vars()
        self._build_ui()
        self.apply_theme(self.theme_name, persist=False)
        self._tick_clock()
        self._drain_events()
        self.root.after(200, self._startup_checks)

    # ------------------------------------------------------------------
    # State variables
    # ------------------------------------------------------------------
    def _build_vars(self) -> None:
        last = self.settings.get("last_params", {}) or {}
        d = MeshyParams()

        self.var_topology = tk.StringVar(value=last.get("topology", d.topology))
        self.var_polycount = tk.IntVar(value=int(last.get("target_polycount", d.target_polycount)))
        self.var_symmetry = tk.StringVar(value=last.get("symmetry_mode", d.symmetry_mode))
        self.var_remesh = tk.BooleanVar(value=last.get("should_remesh", d.should_remesh))
        self.var_texture = tk.BooleanVar(value=last.get("should_texture", d.should_texture))
        self.var_pbr = tk.BooleanVar(value=last.get("enable_pbr", d.enable_pbr))
        pose_val = last.get("pose_mode", d.pose_mode) or ""
        self.var_pose = tk.StringVar(value="(none)" if pose_val == "" else pose_val)
        self.var_texprompt = tk.StringVar(value=last.get("texture_prompt", ""))
        self.var_teximg = tk.StringVar(value=last.get("texture_image_url", ""))
        self.var_rigging = tk.BooleanVar(value=last.get("enable_rigging", d.enable_rigging))
        self.var_righeight = tk.DoubleVar(value=float(last.get("rigging_height_meters", d.rigging_height_meters)))
        self.var_animation = tk.BooleanVar(value=last.get("enable_animation", d.enable_animation))
        self.var_actionid = tk.IntVar(value=int(last.get("animation_action_id", d.animation_action_id)))
        self.var_safety = tk.BooleanVar(value=last.get("enable_safety_checker", d.enable_safety_checker))

        self.var_theme = tk.StringVar(value=self.theme_name)
        self.var_apikey = tk.StringVar(value=self.settings.get("api_key", ""))
        self.var_show_key = tk.BooleanVar(value=False)
        self.var_output_dir = tk.StringVar(value=self.settings.get("output_dir", str(config.DEFAULT_OUTPUT_DIR)))
        self.var_autodownload = tk.BooleanVar(value=self.settings.get("auto_download", True))
        self.var_status = tk.StringVar(value="Ready.")
        self.var_clock = tk.StringVar(value="")

        # Re-evaluate dependent-field enable state when toggles change.
        for v in (self.var_texture, self.var_rigging, self.var_animation):
            v.trace_add("write", lambda *_: self._sync_dependent_states())

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.root.title(f"{config.APP_NAME} — fal.ai Meshy v7")
        self.root.minsize(1040, 680)
        self.root.geometry("1180x760")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        self._build_menubar()
        self._build_header()

        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 6))

        self.tab_generate = ttk.Frame(self.notebook, style="TFrame", padding=10)
        self.tab_history = ttk.Frame(self.notebook, style="TFrame", padding=10)
        self.tab_settings = ttk.Frame(self.notebook, style="TFrame", padding=10)
        self.tab_about = ttk.Frame(self.notebook, style="TFrame", padding=10)
        self.notebook.add(self.tab_generate, text="  Generate  ")
        self.notebook.add(self.tab_history, text="  History  ")
        self.notebook.add(self.tab_settings, text="  Settings  ")
        self.notebook.add(self.tab_about, text="  About  ")

        self._build_generate_tab()
        self._build_history_tab()
        self._build_settings_tab()
        self._build_about_tab()
        self._build_statusbar()
        self._sync_dependent_states()

    def _build_header(self) -> None:
        header = ttk.Frame(self.root, style="TFrame", padding=(14, 12))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        title = ttk.Label(header, text="Meshy Studio", style="H1.TLabel")
        title.grid(row=0, column=0, sticky="w")
        subtitle = ttk.Label(header,
                             text="Multi-image → 3D · fal.ai Meshy v7",
                             style="Muted.TLabel")
        subtitle.grid(row=1, column=0, sticky="w")

        right = ttk.Frame(header, style="TFrame")
        right.grid(row=0, column=2, rowspan=2, sticky="e")
        ttk.Label(right, text="Theme", style="Muted.TLabel").pack(side="left", padx=(0, 6))
        theme_box = ttk.Combobox(right, textvariable=self.var_theme, width=14,
                                 state="readonly",
                                 values=("system",) + THEME_NAMES)
        theme_box.pack(side="left")
        theme_box.bind("<<ComboboxSelected>>", lambda *_: self.apply_theme(self.var_theme.get()))

    # ---- Menu bar ----
    def _build_menubar(self) -> None:
        self.menubar = tk.Menu(self.root)

        # File menu.
        self.menu_file = tk.Menu(self.menubar, tearoff=0)
        self.menu_file.add_command(label="Set API Key…", command=self.on_menu_set_api_key)
        self.menu_file.add_command(label="Set Output Directory…", command=self.on_menu_set_output_dir)
        self.menu_file.add_command(label="Open Output Folder", command=self.on_open_output_folder)
        self.menu_file.add_separator()
        self.menu_file.add_command(label="Exit", command=self.root.destroy)
        self.menubar.add_cascade(label="File", menu=self.menu_file)

        # View menu (theme).
        self.menu_view = tk.Menu(self.menubar, tearoff=0)
        for label, value in (("System", "system"), ("Light", "light"),
                             ("Dark", "dark"), ("High contrast", "high-contrast")):
            self.menu_view.add_radiobutton(
                label=label, value=value, variable=self.var_theme,
                command=lambda v=value: self.apply_theme(v))
        self.menubar.add_cascade(label="View", menu=self.menu_view)

        # Help menu.
        self.menu_help = tk.Menu(self.menubar, tearoff=0)
        self.menu_help.add_command(label="Getting Started", command=self.show_help_getting_started)
        self.menu_help.add_command(label="Parameter Guide", command=self.show_help_parameters)
        self.menu_help.add_command(label="How to Get an API Key", command=self.show_help_api_key)
        self.menu_help.add_separator()
        self.menu_help.add_command(
            label="fal.ai Model Page",
            command=lambda: webbrowser.open("https://fal.ai/models/meshy/v7/multi-image-to-3d"))
        self.menu_help.add_command(label="About Meshy Studio", command=self.show_about)
        self.menubar.add_cascade(label="Help", menu=self.menu_help)

        self.root.config(menu=self.menubar)
        self._apply_menu_colors()

    def _apply_menu_colors(self) -> None:
        p = self.palette
        opts = dict(background=p.surface, foreground=p.fg,
                    activebackground=p.accent, activeforeground=p.accent_fg,
                    borderwidth=0)
        for m in (getattr(self, "menubar", None), getattr(self, "menu_file", None),
                  getattr(self, "menu_view", None), getattr(self, "menu_help", None)):
            if m is not None:
                try:
                    m.configure(**opts)
                except tk.TclError:
                    pass

    # ---- Generate tab ----
    def _build_generate_tab(self) -> None:
        t = self.tab_generate
        t.columnconfigure(0, weight=3, uniform="cols")
        t.columnconfigure(1, weight=4, uniform="cols")
        t.rowconfigure(0, weight=1)

        # Left column (inputs) — scrollable.
        left_scroll = ScrollableFrame(t, bg=self.palette.bg)
        left_scroll.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.left_scroll = left_scroll
        left = left_scroll.body
        left.columnconfigure(0, weight=1)

        self._build_images_card(left)
        self._build_params_card(left)

        actions = ttk.Frame(left, style="TFrame", padding=(0, 8))
        actions.grid(row=2, column=0, sticky="ew", pady=(4, 8))
        actions.columnconfigure(0, weight=1)
        self.btn_generate = ttk.Button(actions, text="Generate 3D Model",
                                       style="Accent.TButton", command=self.on_generate)
        self.btn_generate.grid(row=0, column=0, sticky="ew")
        self.btn_cancel = ttk.Button(actions, text="Cancel", style="Danger.TButton",
                                     command=self.on_cancel, state="disabled")
        self.btn_cancel.grid(row=0, column=1, sticky="e", padx=(8, 0))

        # Right column (output).
        right = ttk.Frame(t, style="TFrame")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)
        self._build_progress_card(right)
        self._build_preview_card(right)
        self._build_downloads_card(right)

    def _card(self, parent, title: str) -> ttk.Frame:
        wrap = ttk.Frame(parent, style="Card.TFrame", padding=14)
        wrap.columnconfigure(0, weight=1)
        head = ttk.Label(wrap, text=title, style="CardH2.TLabel")
        head.grid(row=0, column=0, sticky="w", pady=(0, 8))
        return wrap

    def _build_images_card(self, parent) -> None:
        card = self._card(parent, "Input images  ·  1–4 angles of one object")
        card.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        btns = ttk.Frame(card, style="Card.TFrame")
        btns.grid(row=1, column=0, sticky="ew")
        ttk.Button(btns, text="Add images…", command=self.on_add_images).pack(side="left")
        ttk.Button(btns, text="Clear", style="Ghost.TButton",
                   command=self.on_clear_images).pack(side="left", padx=(8, 0))
        self.lbl_imgcount = ttk.Label(btns, text="0 / 4 selected", style="CardMuted.TLabel")
        self.lbl_imgcount.pack(side="right")

        self.images_container = ttk.Frame(card, style="Card.TFrame", padding=(0, 10, 0, 0))
        self.images_container.grid(row=2, column=0, sticky="ew")
        self._render_image_chips()

    def _build_params_card(self, parent) -> None:
        card = self._card(parent, "Parameters")
        card.grid(row=1, column=0, sticky="ew")
        body = ttk.Frame(card, style="Card.TFrame")
        body.grid(row=1, column=0, sticky="ew")
        body.columnconfigure(1, weight=1)
        r = 0

        r = self._row_combo(body, r, "Topology", self.var_topology, TOPOLOGY_VALUES, "topology")
        r = self._row_spin(body, r, "Target polycount", self.var_polycount,
                           POLYCOUNT_MIN, POLYCOUNT_MAX, 1000, "target_polycount")
        r = self._row_combo(body, r, "Symmetry mode", self.var_symmetry, SYMMETRY_VALUES, "symmetry_mode")
        r = self._row_check(body, r, "Remesh", self.var_remesh, "should_remesh")
        r = self._row_check(body, r, "Generate textures", self.var_texture, "should_texture")
        self.chk_pbr = self._row_check_widget(body, r, "Generate PBR maps", self.var_pbr, "enable_pbr")
        r += 1
        r = self._row_combo(body, r, "Pose mode", self.var_pose,
                           tuple(("(none)" if p == "" else p) for p in POSE_VALUES),
                           "pose_mode", value_map={"(none)": ""})
        self.ent_texprompt = self._row_entry(body, r, "Texture prompt", self.var_texprompt, "texture_prompt")
        r += 1
        self.ent_teximg = self._row_entry(body, r, "Texture image URL", self.var_teximg, "texture_image_url")
        r += 1

        ttk.Separator(body, orient="horizontal").grid(row=r, column=0, columnspan=3,
                                                      sticky="ew", pady=8)
        r += 1
        r = self._row_check(body, r, "Auto-rig (humanoid)", self.var_rigging, "enable_rigging")
        self.spin_righeight = self._row_spin_float(body, r, "Rig height (m)", self.var_righeight,
                                                   0.1, 10.0, 0.1, "rigging_height_meters")
        r += 1
        self.chk_anim = self._row_check_widget(body, r, "Apply animation preset",
                                               self.var_animation, "enable_animation")
        r += 1
        self.spin_action = self._row_spin_widget(body, r, "Animation action ID", self.var_actionid,
                                                 ANIM_ACTION_MIN, ANIM_ACTION_MAX, 1, "animation_action_id")
        r += 1
        ttk.Separator(body, orient="horizontal").grid(row=r, column=0, columnspan=3,
                                                      sticky="ew", pady=8)
        r += 1
        r = self._row_check(body, r, "Safety checker", self.var_safety, "enable_safety_checker")

    # ---- parameter row builders ----
    def _label_with_help(self, parent, text: str, help_key: str, row: int):
        lbl = ttk.Label(parent, text=text, style="Card.TLabel")
        lbl.grid(row=row, column=0, sticky="w", pady=5, padx=(0, 10))
        info = ttk.Label(parent, text="ⓘ", style="CardMuted.TLabel", cursor="question_arrow")
        info.grid(row=row, column=2, sticky="e", padx=(6, 0))
        tip = Tooltip(info, PARAM_HELP.get(help_key, ""), self.palette.surface_alt, self.palette.fg)
        self._tooltips.append(tip)
        return lbl

    def _row_combo(self, parent, row, label, var, values, help_key, value_map=None):
        self._label_with_help(parent, label, help_key, row)
        box = ttk.Combobox(parent, textvariable=var, values=list(values),
                           state="readonly")
        box.grid(row=row, column=1, sticky="ew", pady=5)
        # ``value_map`` documents the display→API mapping (e.g. "(none)" → "");
        # the conversion itself happens in ``_collect_params``.
        return row + 1

    def _row_entry(self, parent, row, label, var, help_key):
        self._label_with_help(parent, label, help_key, row)
        ent = ttk.Entry(parent, textvariable=var)
        ent.grid(row=row, column=1, sticky="ew", pady=5)
        return ent

    def _row_spin(self, parent, row, label, var, lo, hi, step, help_key):
        self._label_with_help(parent, label, help_key, row)
        sp = ttk.Spinbox(parent, textvariable=var, from_=lo, to=hi, increment=step, width=14)
        sp.grid(row=row, column=1, sticky="w", pady=5)
        return row + 1

    def _row_spin_widget(self, parent, row, label, var, lo, hi, step, help_key):
        self._label_with_help(parent, label, help_key, row)
        sp = ttk.Spinbox(parent, textvariable=var, from_=lo, to=hi, increment=step, width=14)
        sp.grid(row=row, column=1, sticky="w", pady=5)
        return sp

    def _row_spin_float(self, parent, row, label, var, lo, hi, step, help_key):
        self._label_with_help(parent, label, help_key, row)
        sp = ttk.Spinbox(parent, textvariable=var, from_=lo, to=hi, increment=step,
                         width=14, format="%.1f")
        sp.grid(row=row, column=1, sticky="w", pady=5)
        return sp

    def _row_check(self, parent, row, label, var, help_key):
        self._row_check_widget(parent, row, label, var, help_key)
        return row + 1

    def _row_check_widget(self, parent, row, label, var, help_key):
        chk = ttk.Checkbutton(parent, text=label, variable=var, style="Card.TCheckbutton")
        chk.grid(row=row, column=0, columnspan=2, sticky="w", pady=5)
        info = ttk.Label(parent, text="ⓘ", style="CardMuted.TLabel", cursor="question_arrow")
        info.grid(row=row, column=2, sticky="e", padx=(6, 0))
        self._tooltips.append(Tooltip(info, PARAM_HELP.get(help_key, ""),
                                      self.palette.surface_alt, self.palette.fg))
        return chk

    # ---- output cards ----
    def _build_progress_card(self, parent) -> None:
        card = self._card(parent, "Status")
        card.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.progress = ttk.Progressbar(card, mode="indeterminate", style="TProgressbar")
        self.progress.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.log = tk.Text(card, height=7, wrap="word", font=MONO_FONT,
                           relief="flat", borderwidth=0, state="disabled")
        self.log.grid(row=2, column=0, sticky="ew")
        card.rowconfigure(2, weight=1)

    def _build_preview_card(self, parent) -> None:
        card = self._card(parent, "Preview")
        card.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.preview_label = ttk.Label(card, text="No preview yet.", style="CardMuted.TLabel",
                                       anchor="center")
        self.preview_label.grid(row=1, column=0, sticky="ew", pady=6)
        self.preview_meta = ttk.Label(card, text="", style="CardMuted.TLabel", anchor="center")
        self.preview_meta.grid(row=2, column=0, sticky="ew")

    def _build_downloads_card(self, parent) -> None:
        card = self._card(parent, "Outputs")
        card.grid(row=2, column=0, sticky="nsew")
        card.rowconfigure(1, weight=1)
        self.downloads_frame = ScrollableFrame(card, bg=self.palette.surface)
        self.downloads_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        self.downloads_frame.set_bg(self.palette.surface)
        self._downloads_body = self.downloads_frame.body
        self.lbl_no_downloads = ttk.Label(self._downloads_body,
                                          text="Generated files will appear here.",
                                          style="CardMuted.TLabel")
        self.lbl_no_downloads.pack(anchor="w")
        bar = ttk.Frame(card, style="Card.TFrame")
        bar.grid(row=2, column=0, sticky="ew")
        self.btn_open_folder = ttk.Button(bar, text="Open output folder",
                                          command=self.on_open_output_folder, state="disabled")
        self.btn_open_folder.pack(side="left")

    # ---- History tab ----
    def _build_history_tab(self) -> None:
        t = self.tab_history
        t.columnconfigure(0, weight=1)
        t.rowconfigure(1, weight=1)
        bar = ttk.Frame(t, style="TFrame")
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(bar, text="Recent generations", style="H2.TLabel").pack(side="left")
        ttk.Button(bar, text="Refresh", style="Ghost.TButton",
                   command=self.refresh_history).pack(side="right")
        ttk.Button(bar, text="Clear history", style="Ghost.TButton",
                   command=self.on_clear_history).pack(side="right", padx=(0, 6))

        cols = ("when", "status", "request", "files")
        self.tree = ttk.Treeview(t, columns=cols, show="headings", selectmode="browse")
        for c, txt, w in (("when", "When (local)", 220), ("status", "Status", 100),
                          ("request", "Request ID", 220), ("files", "Files", 80)):
            self.tree.heading(c, text=txt)
            self.tree.column(c, width=w, anchor="w")
        self.tree.grid(row=1, column=0, sticky="nsew")
        sb = ttk.Scrollbar(t, orient="vertical", command=self.tree.yview)
        sb.grid(row=1, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<Double-1>", self.on_history_open)
        self.refresh_history()

    # ---- Settings tab ----
    def _build_settings_tab(self) -> None:
        t = self.tab_settings
        t.columnconfigure(0, weight=1)
        card = self._card(t, "fal.ai credentials")
        card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        body = ttk.Frame(card, style="Card.TFrame")
        body.grid(row=1, column=0, sticky="ew")
        body.columnconfigure(1, weight=1)

        ttk.Label(body, text="API key", style="Card.TLabel").grid(row=0, column=0, sticky="w", pady=6, padx=(0, 10))
        self.ent_key = ttk.Entry(body, textvariable=self.var_apikey, show="•")
        self.ent_key.grid(row=0, column=1, sticky="ew", pady=6)
        ttk.Checkbutton(body, text="Show", variable=self.var_show_key,
                        style="Card.TCheckbutton", command=self._toggle_key).grid(row=0, column=2, padx=(8, 0))
        note = "Stored encrypted (AES-256-GCM) on this device. Never sent anywhere but fal.ai."
        if self.settings.get("_api_key_from_env"):
            note = "Loaded from the FAL_KEY environment variable for this session."
        ttk.Label(body, text=note, style="CardMuted.TLabel").grid(row=1, column=1, sticky="w")

        out = self._card(t, "Output & behaviour")
        out.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        ob = ttk.Frame(out, style="Card.TFrame")
        ob.grid(row=1, column=0, sticky="ew")
        ob.columnconfigure(1, weight=1)
        ttk.Label(ob, text="Output folder", style="Card.TLabel").grid(row=0, column=0, sticky="w", pady=6, padx=(0, 10))
        ttk.Entry(ob, textvariable=self.var_output_dir).grid(row=0, column=1, sticky="ew", pady=6)
        ttk.Button(ob, text="Browse…", command=self.on_pick_output_dir).grid(row=0, column=2, padx=(8, 0))
        ttk.Checkbutton(ob, text="Automatically download all result files when a job finishes",
                        variable=self.var_autodownload, style="Card.TCheckbutton").grid(
            row=1, column=1, sticky="w", pady=(2, 0))

        actions = ttk.Frame(t, style="TFrame")
        actions.grid(row=2, column=0, sticky="ew")
        ttk.Button(actions, text="Save settings", style="Accent.TButton",
                   command=self.on_save_settings).pack(side="left")
        ttk.Label(actions, text=f"Data location: {config.DATA_DIR}",
                  style="Muted.TLabel").pack(side="right")

    # ---- About tab ----
    def _build_about_tab(self) -> None:
        t = self.tab_about
        t.columnconfigure(0, weight=1)
        card = self._card(t, f"{config.APP_NAME} v{config.APP_VERSION}")
        card.grid(row=0, column=0, sticky="ew")
        msg = (
            "A clean desktop client for the fal.ai Meshy v7 multi-image-to-3D model.\n\n"
            "• Your API key and job history are encrypted at rest with AES-256-GCM.\n"
            "• Images are uploaded to fal.ai storage, then reconstructed into a\n"
            "  textured, game-ready 3D model (GLB/FBX/OBJ/USDZ and more).\n"
            "• All times are shown in your local time zone.\n\n"
            "This tool talks only to fal.ai. Review fal.ai's Terms of Service and\n"
            "Privacy Policy before uploading images you do not own the rights to."
        )
        ttk.Label(card, text=msg, style="Card.TLabel", justify="left").grid(row=1, column=0, sticky="w")
        links = ttk.Frame(card, style="Card.TFrame")
        links.grid(row=2, column=0, sticky="w", pady=(12, 0))
        ttk.Button(links, text="fal.ai model page", style="Ghost.TButton",
                   command=lambda: webbrowser.open("https://fal.ai/models/meshy/v7/multi-image-to-3d")).pack(side="left")
        ttk.Button(links, text="fal.ai Terms & Privacy", style="Ghost.TButton",
                   command=lambda: webbrowser.open("https://fal.ai/legal/terms-of-service")).pack(side="left", padx=(6, 0))

    def _build_statusbar(self) -> None:
        bar = ttk.Frame(self.root, style="Alt.TFrame", padding=(14, 6))
        bar.grid(row=2, column=0, sticky="ew")
        bar.columnconfigure(1, weight=1)
        self.lbl_status = ttk.Label(bar, textvariable=self.var_status, style="Muted.TLabel")
        self.lbl_status.grid(row=0, column=0, sticky="w")
        self.lbl_clock = ttk.Label(bar, textvariable=self.var_clock, style="Muted.TLabel")
        self.lbl_clock.grid(row=0, column=2, sticky="e")

    # ------------------------------------------------------------------
    # Theming
    # ------------------------------------------------------------------
    def apply_theme(self, name: str, persist: bool = True) -> None:
        self.theme_name = name
        self.palette = get_palette(name)
        apply_palette(self.root, self.style, self.palette)

        # Re-colour non-ttk widgets.
        p = self.palette
        if hasattr(self, "log"):
            self.log.configure(background=p.field_bg, foreground=p.fg,
                               insertbackground=p.fg, selectbackground=p.accent,
                               selectforeground=p.accent_fg)
        for sf in (getattr(self, "left_scroll", None), getattr(self, "downloads_frame", None)):
            if sf is not None:
                sf.set_bg(p.surface if sf is getattr(self, "downloads_frame", None) else p.bg)
        for tip in self._tooltips:
            tip.update_colors(p.surface_alt, p.fg)
        self._apply_menu_colors()

        if persist:
            self.settings["theme"] = name
            self._safe_save_settings()
        self.var_theme.set(name)
        # Re-render dynamic content that carries colour.
        self._render_image_chips()

    # ------------------------------------------------------------------
    # Image handling
    # ------------------------------------------------------------------
    def on_add_images(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select 1–4 images of the same object",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.avif *.heic *.heif"), ("All files", "*.*")],
        )
        for p in paths:
            if len(self.image_paths) >= config.MAX_IMAGES:
                messagebox.showinfo(config.APP_NAME, f"You can select up to {config.MAX_IMAGES} images.")
                break
            ok, why = self._validate_image(p)
            if not ok:
                messagebox.showwarning(config.APP_NAME, why)
                continue
            if p not in self.image_paths:
                self.image_paths.append(p)
        self._render_image_chips()

    def _validate_image(self, path: str) -> tuple[bool, str]:
        ext = os.path.splitext(path)[1].lower()
        if ext not in config.ALLOWED_IMAGE_EXTS:
            return False, f"Unsupported file type: {os.path.basename(path)}"
        try:
            if os.path.getsize(path) > config.MAX_IMAGE_BYTES:
                return False, f"{os.path.basename(path)} is larger than 25 MB."
        except OSError:
            return False, f"Cannot read {os.path.basename(path)}."
        return True, ""

    def on_clear_images(self) -> None:
        self.image_paths.clear()
        self._render_image_chips()

    def _remove_image(self, path: str) -> None:
        if path in self.image_paths:
            self.image_paths.remove(path)
        self._render_image_chips()

    def _render_image_chips(self) -> None:
        if not hasattr(self, "images_container"):
            return
        for w in self.images_container.winfo_children():
            w.destroy()
        self._thumb_refs.clear()

        if not self.image_paths:
            ttk.Label(self.images_container, text="No images selected yet.",
                      style="CardMuted.TLabel").grid(row=0, column=0, sticky="w")
        else:
            for i, path in enumerate(self.image_paths):
                chip = ttk.Frame(self.images_container, style="Alt.TFrame", padding=6)
                chip.grid(row=i // 2, column=i % 2, sticky="ew", padx=4, pady=4)
                self.images_container.columnconfigure(i % 2, weight=1)
                thumb = load_thumbnail(path, size=64)
                if thumb is not None:
                    self._thumb_refs.append(thumb)
                    lbl = ttk.Label(chip, image=thumb, style="Card.TLabel")
                    lbl.grid(row=0, column=0, rowspan=2, padx=(0, 8))
                name = os.path.basename(path)
                ttk.Label(chip, text=(name[:22] + "…") if len(name) > 23 else name,
                          style="Card.TLabel").grid(row=0, column=1, sticky="w")
                ttk.Button(chip, text="Remove", style="Ghost.TButton",
                           command=lambda p=path: self._remove_image(p)).grid(row=1, column=1, sticky="w")

        n = len(self.image_paths)
        if hasattr(self, "lbl_imgcount"):
            self.lbl_imgcount.configure(text=f"{n} / {config.MAX_IMAGES} selected")

    # ------------------------------------------------------------------
    # Dependent-field enable/disable
    # ------------------------------------------------------------------
    def _sync_dependent_states(self) -> None:
        tex = self.var_texture.get()
        rig = self.var_rigging.get()
        anim = self.var_animation.get() and rig
        for w, on in (
            (getattr(self, "chk_pbr", None), tex),
            (getattr(self, "ent_texprompt", None), tex),
            (getattr(self, "ent_teximg", None), tex),
            (getattr(self, "spin_righeight", None), rig),
            (getattr(self, "chk_anim", None), rig),
            (getattr(self, "spin_action", None), anim),
        ):
            if w is not None:
                try:
                    w.configure(state=("normal" if on else "disabled"))
                except tk.TclError:
                    pass

    # ------------------------------------------------------------------
    # Generation flow
    # ------------------------------------------------------------------
    def _collect_params(self) -> MeshyParams:
        pose = self.var_pose.get()
        if pose == "(none)":
            pose = ""
        return MeshyParams(
            topology=self.var_topology.get(),
            target_polycount=int(self.var_polycount.get()),
            symmetry_mode=self.var_symmetry.get(),
            should_remesh=bool(self.var_remesh.get()),
            should_texture=bool(self.var_texture.get()),
            enable_pbr=bool(self.var_pbr.get()),
            pose_mode=pose,
            texture_prompt=self.var_texprompt.get(),
            texture_image_url=self.var_teximg.get(),
            enable_rigging=bool(self.var_rigging.get()),
            rigging_height_meters=float(self.var_righeight.get()),
            enable_animation=bool(self.var_animation.get()),
            animation_action_id=int(self.var_actionid.get()),
            enable_safety_checker=bool(self.var_safety.get()),
        )

    def on_generate(self) -> None:
        if self.current_job is not None:
            return
        if not fal_available():
            messagebox.showerror(config.APP_NAME, import_hint())
            return
        api_key = (self.var_apikey.get() or "").strip()
        if not api_key:
            messagebox.showerror(config.APP_NAME,
                                 "Add your fal.ai API key in the Settings tab first.")
            self.notebook.select(self.tab_settings)
            return
        if not self.image_paths:
            messagebox.showwarning(config.APP_NAME, "Select at least one input image.")
            return

        try:
            params = self._collect_params()
        except (tk.TclError, ValueError):
            messagebox.showerror(config.APP_NAME, "One or more parameters is not a valid number.")
            return
        errors = params.validate()
        if errors:
            messagebox.showerror(config.APP_NAME, "Please fix:\n\n• " + "\n• ".join(errors))
            return

        # Persist the current parameters for next launch.
        self.settings["last_params"] = params.to_arguments()
        self._safe_save_settings()

        self._clear_log()
        self._set_running(True)
        self._log("Starting generation…")
        self.current_job = GenerationJob(
            api_key=api_key,
            image_paths=list(self.image_paths),
            params=params,
            events=self.events,
            output_dir=self.var_output_dir.get(),
            auto_download=bool(self.var_autodownload.get()),
        )
        self.current_job.start()

    def on_cancel(self) -> None:
        if self.current_job is not None:
            self.current_job.cancel()
            self._log("Cancelling…")
            self.btn_cancel.configure(state="disabled")

    def _set_running(self, running: bool) -> None:
        self.btn_generate.configure(state=("disabled" if running else "normal"))
        self.btn_cancel.configure(state=("normal" if running else "disabled"))
        if running:
            self.progress.configure(mode="indeterminate")
            self.progress.start(12)
        else:
            self.progress.stop()
            self.progress.configure(mode="determinate", value=0)

    # ------------------------------------------------------------------
    # Event pump (worker → UI)
    # ------------------------------------------------------------------
    def _drain_events(self) -> None:
        try:
            while True:
                evt = self.events.get_nowait()
                self._handle_event(evt)
        except queue.Empty:
            pass
        self.root.after(120, self._drain_events)

    def _handle_event(self, evt: WorkerEvent) -> None:
        if self.current_job is None or evt.job_id != self.current_job.job_id:
            return
        if evt.kind == "status":
            self._log(evt.message)
            self.var_status.set(evt.message)
        elif evt.kind == "done":
            self._on_job_done(evt)
        elif evt.kind == "cancelled":
            self._log(evt.message or "Cancelled.")
            self.var_status.set("Cancelled.")
            self._finish_job(status="cancelled", evt=evt)
        elif evt.kind == "error":
            self._log("ERROR: " + evt.message)
            self.var_status.set("Error.")
            messagebox.showerror(config.APP_NAME, evt.message)
            self._finish_job(status="error", evt=evt)

    def _on_job_done(self, evt: WorkerEvent) -> None:
        self._log(evt.message)
        self.var_status.set("Done.")
        result = evt.payload.get("result", {})
        self.last_result = result
        self._render_result(result, evt.payload.get("downloads", []))
        self._finish_job(status="completed", evt=evt)

    def _finish_job(self, status: str, evt: WorkerEvent) -> None:
        self._set_running(False)
        # Record history (never store the API key).
        entry = {
            "when": now_utc().isoformat(),
            "status": status,
            "request_id": evt.payload.get("request_id") or (self.current_job.request_id if self.current_job else None),
            "params": evt.payload.get("params", {}),
            "downloads": evt.payload.get("downloads", []),
            "elapsed": evt.payload.get("elapsed"),
            "message": evt.message,
        }
        try:
            self.history = self.store.append_history(entry)
            self.refresh_history()
        except Exception as exc:  # noqa: BLE001
            self._log(f"(Could not save history: {exc})")
        self.current_job = None

    # ------------------------------------------------------------------
    # Result rendering
    # ------------------------------------------------------------------
    def _render_result(self, result: dict, downloads: list[dict]) -> None:
        # Preview thumbnail.
        self._preview_ref = None
        self.preview_label.configure(image="", text="No preview available.")
        thumb = result.get("thumbnail") or {}
        local_thumb = next((d["path"] for d in downloads
                            if d.get("label") == "Thumbnail"), None)
        img = None
        if local_thumb and os.path.exists(local_thumb):
            img = load_thumbnail(local_thumb, size=260)
        if img is not None:
            self._preview_ref = img
            self.preview_label.configure(image=img, text="")
        elif thumb.get("url"):
            self.preview_label.configure(text="Thumbnail available — open output folder to view.")

        seed = result.get("seed")
        self.preview_meta.configure(text=(f"Seed: {seed}" if seed is not None else ""))

        # Downloads / output list.
        for w in self._downloads_body.winfo_children():
            w.destroy()
        files = iter_result_files(result)
        dl_by_label = {d.get("label"): d for d in downloads}
        if not files:
            ttk.Label(self._downloads_body, text="No output files were returned.",
                      style="CardMuted.TLabel").pack(anchor="w")
        for label, obj in files:
            row = ttk.Frame(self._downloads_body, style="Card.TFrame", padding=(0, 3))
            row.pack(fill="x", anchor="w")
            ttk.Label(row, text=label, style="Card.TLabel").pack(side="left")
            saved = dl_by_label.get(label)
            if saved and os.path.exists(saved.get("path", "")):
                ttk.Button(row, text="Open", style="Ghost.TButton",
                           command=lambda p=saved["path"]: self._open_path(p)).pack(side="right")
                ttk.Label(row, text="saved", style="Success.TLabel").pack(side="right", padx=6)
            else:
                url = obj.get("url")
                ttk.Button(row, text="Open URL", style="Ghost.TButton",
                           command=lambda u=url: webbrowser.open(u)).pack(side="right")

        self.btn_open_folder.configure(state="normal")

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------
    def refresh_history(self) -> None:
        if not hasattr(self, "tree"):
            return
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for idx, entry in enumerate(reversed(self.history)):
            from datetime import datetime

            try:
                when = format_local(datetime.fromisoformat(entry.get("when")))
            except Exception:
                when = entry.get("when", "?")
            self.tree.insert("", "end", iid=str(idx), values=(
                when, entry.get("status", "?"),
                entry.get("request_id") or "—",
                str(len(entry.get("downloads", []))),
            ))

    def on_history_open(self, _evt=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        entry = list(reversed(self.history))[idx]
        dls = entry.get("downloads", [])
        if dls:
            folder = os.path.dirname(dls[0].get("path", ""))
            if folder and os.path.isdir(folder):
                self._open_path(folder)
                return
        messagebox.showinfo(config.APP_NAME,
                            f"Request: {entry.get('request_id')}\n"
                            f"Status: {entry.get('status')}\n"
                            f"No local files saved for this job.")

    def on_clear_history(self) -> None:
        if messagebox.askyesno(config.APP_NAME, "Clear all saved history? This cannot be undone."):
            self.history = []
            self.store.save_history([])
            self.refresh_history()

    # ------------------------------------------------------------------
    # Settings actions
    # ------------------------------------------------------------------
    def _toggle_key(self) -> None:
        self.ent_key.configure(show="" if self.var_show_key.get() else "•")

    def on_pick_output_dir(self) -> None:
        d = filedialog.askdirectory(title="Choose output folder",
                                    initialdir=self.var_output_dir.get() or str(config.DEFAULT_OUTPUT_DIR))
        if d:
            self.var_output_dir.set(d)

    def on_save_settings(self) -> None:
        self.settings["api_key"] = self.var_apikey.get().strip()
        self.settings["output_dir"] = self.var_output_dir.get().strip() or str(config.DEFAULT_OUTPUT_DIR)
        self.settings["auto_download"] = bool(self.var_autodownload.get())
        self.settings["theme"] = self.theme_name
        if self._safe_save_settings():
            self.var_status.set("Settings saved (encrypted).")
            messagebox.showinfo(config.APP_NAME, "Settings saved and encrypted on this device.")

    def _safe_save_settings(self) -> bool:
        try:
            self.store.save_settings(self.settings)
            return True
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(config.APP_NAME, f"Could not save settings: {exc}")
            return False

    # ------------------------------------------------------------------
    # Menu: File actions
    # ------------------------------------------------------------------
    def on_menu_set_api_key(self) -> None:
        """Modal dialog to enter and store the fal.ai API key (encrypted)."""
        win = self._themed_toplevel("Set fal.ai API Key", width=520)
        frame = ttk.Frame(win, style="Card.TFrame", padding=16)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)

        ttk.Label(frame, text="fal.ai API key", style="CardH2.TLabel").grid(
            row=0, column=0, sticky="w")
        ttk.Label(frame, style="CardMuted.TLabel",
                  text="Stored encrypted (AES-256-GCM) on this device and sent only to fal.ai."
                  ).grid(row=1, column=0, sticky="w", pady=(2, 10))

        key_var = tk.StringVar(value=self.var_apikey.get())
        show_var = tk.BooleanVar(value=False)
        entry = ttk.Entry(frame, textvariable=key_var, show="•", width=52)
        entry.grid(row=2, column=0, sticky="ew")
        entry.focus_set()

        def toggle():
            entry.configure(show="" if show_var.get() else "•")

        ttk.Checkbutton(frame, text="Show key", variable=show_var,
                        style="Card.TCheckbutton", command=toggle).grid(
            row=3, column=0, sticky="w", pady=(6, 4))

        link = ttk.Button(frame, text="Get a key at fal.ai/dashboard/keys",
                          style="Ghost.TButton",
                          command=lambda: webbrowser.open("https://fal.ai/dashboard/keys"))
        link.grid(row=4, column=0, sticky="w", pady=(0, 12))

        btns = ttk.Frame(frame, style="Card.TFrame")
        btns.grid(row=5, column=0, sticky="e")

        def save():
            key = key_var.get().strip()
            self.var_apikey.set(key)
            self.settings["api_key"] = key
            if self._safe_save_settings():
                self.var_status.set("API key saved (encrypted).")
                win.destroy()

        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(btns, text="Save", style="Accent.TButton", command=save).pack(side="right")
        win.bind("<Return>", lambda *_: save())
        win.bind("<Escape>", lambda *_: win.destroy())

    def on_menu_set_output_dir(self) -> None:
        d = filedialog.askdirectory(
            title="Choose output folder",
            initialdir=self.var_output_dir.get() or str(config.DEFAULT_OUTPUT_DIR))
        if d:
            self.var_output_dir.set(d)
            self.settings["output_dir"] = d
            if self._safe_save_settings():
                self.var_status.set(f"Output folder set to {d}")

    # ------------------------------------------------------------------
    # Menu: Help windows
    # ------------------------------------------------------------------
    def _themed_toplevel(self, title: str, width: int = 640, height: int | None = None) -> tk.Toplevel:
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(background=self.palette.bg)
        win.transient(self.root)
        win.resizable(True, True)
        if height:
            win.geometry(f"{width}x{height}")
        else:
            win.geometry(f"{width}x{min(560, width)}")
        # Centre over the main window.
        self.root.update_idletasks()
        x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - width) // 2)
        y = self.root.winfo_rooty() + 80
        win.geometry(f"+{x}+{y}")
        try:
            win.grab_set()
        except tk.TclError:
            pass
        return win

    def _show_text_window(self, title: str, content: str) -> None:
        win = self._themed_toplevel(title, width=680, height=560)
        p = self.palette
        outer = ttk.Frame(win, style="TFrame", padding=12)
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        text = tk.Text(outer, wrap="word", relief="flat", borderwidth=0,
                       padx=14, pady=12, font=BASE_FONT,
                       background=p.surface, foreground=p.fg,
                       insertbackground=p.fg, highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=text.yview,
                           style="Vertical.TScrollbar")
        text.configure(yscrollcommand=sb.set)
        text.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")

        # Simple markup: lines ending with a tab-less '::' heading marker.
        text.tag_configure("h1", font=(BASE_FONT[0], 15, "bold"), foreground=p.fg,
                            spacing1=4, spacing3=8)
        text.tag_configure("h2", font=(BASE_FONT[0], 11, "bold"), foreground=p.accent,
                            spacing1=10, spacing3=4)
        text.tag_configure("body", foreground=p.fg, spacing3=3, lmargin1=4, lmargin2=4)
        for line in content.split("\n"):
            if line.startswith("# "):
                text.insert("end", line[2:] + "\n", "h1")
            elif line.startswith("## "):
                text.insert("end", line[3:] + "\n", "h2")
            else:
                text.insert("end", line + "\n", "body")
        text.configure(state="disabled")

        bar = ttk.Frame(win, style="TFrame", padding=(12, 0, 12, 12))
        bar.pack(fill="x")
        ttk.Button(bar, text="Close", style="Accent.TButton",
                   command=win.destroy).pack(side="right")
        win.bind("<Escape>", lambda *_: win.destroy())

    def show_help_getting_started(self) -> None:
        self._show_text_window("Getting Started", _HELP_GETTING_STARTED)

    def show_help_parameters(self) -> None:
        self._show_text_window("Parameter Guide", _build_parameter_guide())

    def show_help_api_key(self) -> None:
        self._show_text_window("How to Get an API Key", _HELP_API_KEY)

    def show_about(self) -> None:
        self._show_text_window("About Meshy Studio", _HELP_ABOUT)

    # ------------------------------------------------------------------
    # Misc helpers
    # ------------------------------------------------------------------
    def on_open_output_folder(self) -> None:
        self._open_path(self.var_output_dir.get())

    def _open_path(self, path: str) -> None:
        if not path or not os.path.exists(path):
            messagebox.showinfo(config.APP_NAME, "That location doesn't exist yet.")
            return
        try:
            if os.name == "nt":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(["open", path], check=False)
            else:
                subprocess.run(["xdg-open", path], check=False)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(config.APP_NAME, f"Could not open: {exc}")

    def _log(self, msg: str) -> None:
        ts = format_local(now_utc()).split(", ")[-1]
        self.log.configure(state="normal")
        self.log.insert("end", f"[{ts}] {msg}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _tick_clock(self) -> None:
        self.var_clock.set("🕒 " + format_local(now_utc()))
        self.root.after(1000, self._tick_clock)

    def _startup_checks(self) -> None:
        if not fal_available():
            self.var_status.set("fal-client not installed — see Settings.")
            self._log(import_hint())
        elif not (self.var_apikey.get() or "").strip():
            self.var_status.set("Add your fal.ai API key in Settings to begin.")
