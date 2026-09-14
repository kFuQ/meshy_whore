"""Encrypted-at-rest persistence for settings and job history.

Everything written to disk is sealed with AES-256-GCM via :mod:`crypto`. The
fal.ai API key, in particular, is never stored in plaintext. Files use a
``0600`` permission mask.
"""
from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any

from . import config
from .crypto import Cryptor, CryptoError, load_or_create_master_key

# Associated data binds each ciphertext to its logical purpose so a settings
# blob can never be swapped in for a history blob.
_AD_SETTINGS = b"meshy-studio/settings/v1"
_AD_HISTORY = b"meshy-studio/history/v1"

DEFAULT_SETTINGS: dict[str, Any] = {
    "api_key": "",  # sealed on disk; masked in the UI
    "theme": "system",  # system | light | dark | high-contrast
    "output_dir": str(config.DEFAULT_OUTPUT_DIR),
    "auto_download": True,
    "last_params": {},
}

MAX_HISTORY = 100


def _write_secure(path: Path, data: bytes) -> None:
    """Atomically write ``data`` to ``path`` with 0600 permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".enc")
    try:
        os.fchmod(fd, stat.S_IRUSR | stat.S_IWUSR)  # 0600
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


class SecureStore:
    """Loads and saves encrypted settings + history."""

    def __init__(self, passphrase: str | None = None):
        config.ensure_data_dir()
        passphrase = passphrase or os.environ.get("MESHY_MASTER_KEY")
        key = load_or_create_master_key(config.MASTER_KEY_FILE, passphrase)
        self._cryptor = Cryptor(key)

    # ---- settings ----------------------------------------------------
    def load_settings(self) -> dict[str, Any]:
        settings = dict(DEFAULT_SETTINGS)
        path = config.SETTINGS_FILE
        if path.exists():
            try:
                raw = self._cryptor.decrypt(path.read_bytes(), _AD_SETTINGS)
                stored = json.loads(raw.decode("utf-8"))
                if isinstance(stored, dict):
                    settings.update(stored)
            except (CryptoError, json.JSONDecodeError, OSError):
                # Corrupt or unreadable: fall back to defaults rather than crash.
                pass

        # An env-provided key always wins and is never persisted in plaintext.
        env_key = os.environ.get(config.FAL_KEY_ENV)
        if env_key and not settings.get("api_key"):
            settings["api_key"] = env_key
            settings["_api_key_from_env"] = True
        return settings

    def save_settings(self, settings: dict[str, Any]) -> None:
        payload = {k: v for k, v in settings.items() if not k.startswith("_")}
        raw = json.dumps(payload).encode("utf-8")
        token = self._cryptor.encrypt(raw, _AD_SETTINGS)
        _write_secure(config.SETTINGS_FILE, token)

    # ---- history -----------------------------------------------------
    def load_history(self) -> list[dict[str, Any]]:
        path = config.HISTORY_FILE
        if not path.exists():
            return []
        try:
            raw = self._cryptor.decrypt(path.read_bytes(), _AD_HISTORY)
            data = json.loads(raw.decode("utf-8"))
            return data if isinstance(data, list) else []
        except (CryptoError, json.JSONDecodeError, OSError):
            return []

    def save_history(self, history: list[dict[str, Any]]) -> None:
        trimmed = history[-MAX_HISTORY:]
        raw = json.dumps(trimmed).encode("utf-8")
        token = self._cryptor.encrypt(raw, _AD_HISTORY)
        _write_secure(config.HISTORY_FILE, token)

    def append_history(self, entry: dict[str, Any]) -> list[dict[str, Any]]:
        history = self.load_history()
        history.append(entry)
        self.save_history(history)
        return history
