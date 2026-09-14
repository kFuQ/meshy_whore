"""Background generation worker.

Runs the full pipeline (upload → submit → poll → optional download) on a
daemon thread and reports progress through a thread-safe queue that the Tk
main loop drains. Keeping this out of the UI module makes it unit-testable
without a display.
"""
from __future__ import annotations

import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .fal_service import FalServiceError, MeshyClient, download_file
from .schema import MeshyParams, iter_result_files
from .timeutils import iso_utc


@dataclass
class WorkerEvent:
    kind: str  # "status" | "done" | "error" | "cancelled"
    job_id: str
    message: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


class GenerationJob:
    """A single generation run, driven on its own thread."""

    def __init__(
        self,
        api_key: str,
        image_paths: list[str],
        params: MeshyParams,
        events: "queue.Queue[WorkerEvent]",
        output_dir: str | None = None,
        auto_download: bool = True,
    ):
        self.job_id = uuid.uuid4().hex[:12]
        self._api_key = api_key
        self._image_paths = image_paths
        self._params = params
        self._events = events
        self._output_dir = output_dir
        self._auto_download = auto_download
        self._cancel = threading.Event()
        self._thread: threading.Thread | None = None
        self.request_id: str | None = None

    # ---- control -----------------------------------------------------
    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True, name=f"job-{self.job_id}")
        self._thread.start()

    def cancel(self) -> None:
        self._cancel.set()

    @property
    def cancelled(self) -> bool:
        return self._cancel.is_set()

    # ---- internals ---------------------------------------------------
    def _emit(self, kind: str, message: str = "", **payload: Any) -> None:
        self._events.put(WorkerEvent(kind=kind, job_id=self.job_id, message=message, payload=payload))

    def _run(self) -> None:
        started = time.time()
        try:
            client = MeshyClient(self._api_key)

            self._emit("status", "Uploading images…")
            urls = client.upload_images(
                self._image_paths, progress=lambda m: self._emit("status", m)
            )
            if self._cancel.is_set():
                self._emit("cancelled", "Cancelled before submission.")
                return

            self._params.image_urls = urls
            self._emit("status", "Submitting to Meshy v7…")
            self.request_id = client.submit(self._params)
            self._emit("status", f"Request accepted ({self.request_id}). Generating…",
                       request_id=self.request_id)

            result = client.poll_until_done(
                self.request_id,
                progress=lambda m: self._emit("status", m),
                should_cancel=self._cancel.is_set,
            )

            downloads: list[dict[str, str]] = []
            if self._auto_download and self._output_dir:
                files = iter_result_files(result)
                for idx, (label, obj) in enumerate(files, start=1):
                    if self._cancel.is_set():
                        break
                    self._emit("status", f"Downloading {label} ({idx}/{len(files)})…")
                    try:
                        local = download_file(
                            obj["url"], self._output_dir, obj.get("file_name")
                        )
                        downloads.append({"label": label, "path": local, "url": obj["url"]})
                    except FalServiceError as exc:
                        self._emit("status", f"Skipped {label}: {exc}")

            elapsed = time.time() - started
            self._emit(
                "done",
                f"Completed in {elapsed:.1f}s.",
                result=result,
                downloads=downloads,
                request_id=self.request_id,
                image_urls=urls,
                params=self._params.to_arguments(),
                finished_at=iso_utc(),
                elapsed=elapsed,
            )
        except FalServiceError as exc:
            self._emit("error", str(exc))
        except Exception as exc:  # noqa: BLE001 - never let the thread die silently
            self._emit("error", f"Unexpected error: {exc}")
