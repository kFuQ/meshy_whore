"""Application paths and constants.

Meshy Studio keeps all of its local state under a per-user application data
directory so it never writes secrets into the source tree.
"""
from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "Meshy Studio"
APP_SLUG = "meshy-studio"
APP_VERSION = "1.0.0"

# fal.ai endpoint for the Meshy v7 multi-image-to-3D model.
FAL_ENDPOINT = "meshy/v7/multi-image-to-3d"

# Environment variable fal_client itself reads for auth.
FAL_KEY_ENV = "FAL_KEY"


def _app_data_dir() -> Path:
    """Return the OS-appropriate per-user data directory."""
    override = os.environ.get("MESHY_STUDIO_HOME")
    if override:
        return Path(override).expanduser()

    if os.name == "nt":  # Windows
        base = os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")
        return Path(base) / "MeshyStudio"

    if os.sys.platform == "darwin":  # macOS
        return Path.home() / "Library" / "Application Support" / "MeshyStudio"

    # Linux / other: respect XDG.
    base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return Path(base) / APP_SLUG


DATA_DIR = _app_data_dir()
MASTER_KEY_FILE = DATA_DIR / "master.key"
SETTINGS_FILE = DATA_DIR / "settings.enc"
HISTORY_FILE = DATA_DIR / "history.enc"
DEFAULT_OUTPUT_DIR = Path.home() / "MeshyStudioOutputs"

# Upload validation limits.
MAX_IMAGES = 4
MIN_IMAGES = 1
ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".avif", ".heic", ".heif"}
MAX_IMAGE_BYTES = 25 * 1024 * 1024  # 25 MB per image


def ensure_data_dir() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        # Best-effort: keep the data dir private (0700).
        os.chmod(DATA_DIR, 0o700)
    except OSError:
        pass
    return DATA_DIR
