"""Thin, testable wrapper around the fal.ai client for Meshy v7.

The wrapper is import-safe even when ``fal_client`` is not installed, so the
UI can start and show a helpful message instead of crashing.
"""
from __future__ import annotations

import os
import urllib.request
from pathlib import Path
from typing import Any, Callable

from . import config
from .schema import MeshyParams

try:  # fal_client is optional at import time, required at call time.
    import fal_client  # type: ignore

    _IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - depends on environment
    fal_client = None  # type: ignore
    _IMPORT_ERROR = exc


ProgressCb = Callable[[str], None]

# Cap downloads to avoid an unbounded write filling the disk if a URL returns
# far more data than expected. 3D models + textures are comfortably under this.
MAX_DOWNLOAD_BYTES = 1024 * 1024 * 1024  # 1 GiB


class FalServiceError(Exception):
    """User-facing error from the fal.ai integration."""


def is_available() -> bool:
    return fal_client is not None


def import_hint() -> str:
    return (
        f"The 'fal-client' package could not be imported ({_IMPORT_ERROR}). "
        "Install dependencies with: pip install -r requirements.txt"
    )


def _mask(key: str) -> str:
    if not key:
        return "(none)"
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}…{key[-4:]}"


class MeshyClient:
    """Owns a fal.ai client bound to a single API key."""

    def __init__(self, api_key: str):
        if fal_client is None:
            raise FalServiceError(import_hint())
        api_key = (api_key or "").strip()
        if not api_key:
            raise FalServiceError("No fal.ai API key configured. Add one in Settings.")
        self._api_key = api_key
        # SyncClient reads the key from the constructor; we never mutate the
        # global environment so concurrent keys stay isolated.
        self._client = fal_client.SyncClient(key=api_key)

    @property
    def masked_key(self) -> str:
        return _mask(self._api_key)

    # ---- uploads -----------------------------------------------------
    def upload_images(
        self, paths: list[str], progress: ProgressCb | None = None
    ) -> list[str]:
        urls: list[str] = []
        for i, p in enumerate(paths, start=1):
            path = Path(p)
            if not path.is_file():
                raise FalServiceError(f"Image not found: {path}")
            if progress:
                progress(f"Uploading image {i}/{len(paths)}: {path.name}")
            try:
                url = self._client.upload_file(str(path))
            except Exception as exc:  # noqa: BLE001 - surface as friendly error
                raise FalServiceError(f"Failed to upload {path.name}: {exc}") from exc
            urls.append(url)
        return urls

    # ---- generation --------------------------------------------------
    def submit(self, params: MeshyParams) -> str:
        errors = params.validate()
        if errors:
            raise FalServiceError("Invalid parameters:\n- " + "\n- ".join(errors))
        if not params.image_urls:
            raise FalServiceError("At least one input image is required.")
        try:
            handle = self._client.submit(config.FAL_ENDPOINT, arguments=params.to_arguments())
        except Exception as exc:  # noqa: BLE001
            raise FalServiceError(f"Failed to submit request: {exc}") from exc
        return handle.request_id

    def poll_until_done(
        self,
        request_id: str,
        progress: ProgressCb | None = None,
        should_cancel: Callable[[], bool] | None = None,
        interval: float = 2.0,
    ) -> dict[str, Any]:
        """Block (in a worker thread) until the request completes.

        Raises :class:`FalServiceError` on failure or cancellation.
        """
        import time

        Completed = getattr(fal_client, "Completed", None)
        InProgress = getattr(fal_client, "InProgress", None)
        Queued = getattr(fal_client, "Queued", None)

        last_msg = ""
        while True:
            if should_cancel and should_cancel():
                try:
                    self._client.cancel(config.FAL_ENDPOINT, request_id)
                except Exception:
                    pass
                raise FalServiceError("Generation cancelled.")

            try:
                status = self._client.status(
                    config.FAL_ENDPOINT, request_id, with_logs=True
                )
            except Exception as exc:  # noqa: BLE001
                raise FalServiceError(f"Failed to fetch status: {exc}") from exc

            if progress:
                msg = self._status_message(status, Queued, InProgress)
                if msg and msg != last_msg:
                    last_msg = msg
                    progress(msg)

            if Completed is not None and isinstance(status, Completed):
                break
            # Fallback for string/other status shapes.
            if Completed is None and getattr(status, "status", "") == "COMPLETED":
                break

            time.sleep(interval)

        try:
            return self._client.result(config.FAL_ENDPOINT, request_id)
        except Exception as exc:  # noqa: BLE001
            raise FalServiceError(f"Failed to fetch result: {exc}") from exc

    @staticmethod
    def _status_message(status: Any, Queued: Any, InProgress: Any) -> str:
        # Prefer streamed logs when present.
        logs = getattr(status, "logs", None)
        if logs:
            try:
                last = logs[-1]
                msg = last.get("message") if isinstance(last, dict) else str(last)
                if msg:
                    return str(msg).strip()
            except (IndexError, KeyError, TypeError):
                pass
        if Queued is not None and isinstance(status, Queued):
            pos = getattr(status, "position", None)
            return f"Queued (position {pos})…" if pos is not None else "Queued…"
        if InProgress is not None and isinstance(status, InProgress):
            return "In progress…"
        return "Working…"


def download_file(url: str, dest_dir: str, filename: str | None = None) -> str:
    """Download ``url`` into ``dest_dir`` and return the local path.

    Only http(s) URLs are accepted; the filename is sanitised to prevent path
    traversal into parent directories.
    """
    if not url.lower().startswith(("http://", "https://")):
        raise FalServiceError(f"Refusing to download non-HTTP URL: {url!r}")

    dest = Path(dest_dir).expanduser()
    dest.mkdir(parents=True, exist_ok=True)

    name = filename or os.path.basename(url.split("?", 1)[0]) or "download.bin"
    name = os.path.basename(name)  # strip any directory components
    name = "".join(c for c in name if c not in '<>:"/\\|?*').strip() or "download.bin"
    target = dest / name

    # Avoid clobbering existing files.
    if target.exists():
        stem, suffix = target.stem, target.suffix
        n = 1
        while target.exists():
            target = dest / f"{stem}-{n}{suffix}"
            n += 1

    req = urllib.request.Request(url, headers={"User-Agent": "MeshyStudio/1.0"})
    written = 0
    try:
        with urllib.request.urlopen(req, timeout=120) as resp, open(target, "wb") as fh:
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > MAX_DOWNLOAD_BYTES:
                    raise FalServiceError(
                        f"{name} exceeds the {MAX_DOWNLOAD_BYTES // (1024 * 1024)} MB "
                        "download limit; aborting."
                    )
                fh.write(chunk)
    except FalServiceError:
        _safe_unlink(target)
        raise
    except Exception as exc:  # noqa: BLE001
        _safe_unlink(target)
        raise FalServiceError(f"Download failed for {name}: {exc}") from exc
    return str(target)


def _safe_unlink(path) -> None:
    try:
        os.remove(path)
    except OSError:
        pass
