# Meshy Studio

A clean, cross-platform **desktop** app (Python + Tkinter) for turning **1–4
images of an object into a textured, game-ready 3D model** using the
[fal.ai **Meshy v7** multi-image-to-3D](https://fal.ai/models/meshy/v7/multi-image-to-3d)
model.

No web server, no browser — just a native window. Your fal.ai API key and job
history are **encrypted at rest with AES-256-GCM**.

> **Meshy Studio talks only to fal.ai.** Images you add are uploaded to fal.ai
> storage so the model can process them. Review fal.ai's Terms & Privacy before
> uploading images you don't own the rights to.

## Documentation index

| Document | What's inside |
|----------|---------------|
| [README.md](README.md) | This file — overview, install, usage |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [TODO.md](TODO.md) | Roadmap and known limitations |
| [SECURITY.md](SECURITY.md) | Threat model, encryption, reporting |
| [PRIVACY.md](PRIVACY.md) | Data handling & GDPR notes |
| [LICENSE](LICENSE) | MIT license |

## Features

- 🖼️ **Multi-image input** — drag in 1–4 angles of the same object (JPG/PNG/AVIF/HEIC).
- 🎛️ **Full v7 parameter control** — topology, target polycount, symmetry,
  remesh, textures, PBR maps, pose, texture prompt/image, auto-rigging,
  animation presets, and the safety checker. Dependent options enable/disable
  automatically to match the API's rules.
- 🧵 **Responsive UI** — generation runs on a background thread with live status
  and a cancel button; the window never freezes.
- 🧭 **Native menu bar** — **File** (set API key, set output directory, open
  output folder), **View** (theme), and **Help** (Getting Started, a full
  Parameter Guide, and how to get an API key).
- 🌓 **Global theming** — light, dark, and high-contrast palettes (plus
  "system" auto-detect). All colours come from a single token set — no
  hard-coded colours in the UI.
- ♿ **Accessible** — keyboard-friendly widgets, high-contrast theme, tooltips
  describing every parameter.
- 💾 **Auto-download** — every output (GLB / FBX / OBJ / USDZ / textures /
  animations) is fetched to a folder you choose; open it in one click.
- 🔒 **Encrypted at rest** — API key and history sealed with AES-256-GCM.
- 🕒 **Pacific time** — all timestamps display in US Pacific time.

## Requirements

- **Python 3.9+** with **Tkinter** (Tk 8.6).
  - macOS / Windows: bundled with the [python.org](https://www.python.org/downloads/) installer.
  - Debian/Ubuntu: `sudo apt install python3-tk`
  - Fedora: `sudo dnf install python3-tkinter`
- A **fal.ai API key** — create one at <https://fal.ai/dashboard/keys>.

## Install

```bash
git clone <this-repo>
cd meshy_whore
python -m pip install -r requirements.txt
```

## Run

```bash
python main.py
# or
python -m meshy_studio
```

Then:

1. Set your fal.ai API key via **File → Set API Key…** (or the **Settings** tab).
   It's encrypted on disk. You can alternatively set the `FAL_KEY` environment
   variable before launching.
2. Optionally choose where models are saved via **File → Set Output Directory…**.
3. Back on **Generate**, click **Add images…** and pick 1–4 views of one object.
4. Adjust parameters as desired and click **Generate 3D Model**.
5. Watch progress; when it finishes, outputs are listed and (if auto-download is
   on) saved to your output folder. Click **Open output folder**.

New to it? Use the **Help** menu — *Getting Started*, a full *Parameter Guide*,
and *How to Get an API Key*.

## Configuration & data location

| Item | Default location |
|------|------------------|
| Encrypted settings / history | `~/.local/share/meshy-studio/` (Linux), `~/Library/Application Support/MeshyStudio/` (macOS), `%APPDATA%\MeshyStudio\` (Windows) |
| AES master key | `master.key` in the data dir (`0600`, auto-generated) |
| Outputs | `~/MeshyStudioOutputs/` (configurable in Settings) |

Optional environment overrides:

- `FAL_KEY` — API key for the session (takes precedence over the stored key).
- `MESHY_MASTER_KEY` — passphrase to derive the AES-256-GCM master key (makes
  encrypted data portable across machines).
- `MESHY_STUDIO_HOME` — override the data directory.

## Development

```bash
python -m unittest discover -s tests -v
```

The codebase is split into a UI-free core (`crypto`, `store`, `schema`,
`fal_service`, `worker`) that is unit-tested headlessly, and a Tkinter UI
(`meshy_studio/ui/`).

```
meshy_studio/
├── config.py        # paths & constants
├── crypto.py        # AES-256-GCM envelope
├── store.py         # encrypted settings + history
├── schema.py        # Meshy v7 params + validation + result flattening
├── fal_service.py   # fal.ai client wrapper (upload/submit/poll/download)
├── worker.py        # threaded generation job
├── theme.py         # colour palettes
└── ui/              # Tkinter app, styling, widgets
```

## License

[MIT](LICENSE).
