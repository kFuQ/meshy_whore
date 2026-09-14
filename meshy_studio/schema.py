"""Input/output schema for the Meshy v7 multi-image-to-3D endpoint.

Mirrors the official fal.ai API docs. Centralising the schema here keeps the
UI, validation and the service wrapper in agreement.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

TOPOLOGY_VALUES = ("triangle", "quad")
SYMMETRY_VALUES = ("off", "auto", "on")
POSE_VALUES = ("", "a-pose", "t-pose")

POLYCOUNT_MIN = 100
POLYCOUNT_MAX = 300_000
RIG_HEIGHT_MIN = 0.1
RIG_HEIGHT_MAX = 10.0
ANIM_ACTION_MIN = 0
ANIM_ACTION_MAX = 696

# Model formats returned under result["model_urls"].
MODEL_FORMATS = ("glb", "fbx", "obj", "usdz", "blend", "stl")


@dataclass
class MeshyParams:
    """Validated parameter set for a generation request.

    ``image_urls`` is filled in by the service after uploading local files.
    """

    image_urls: list[str] = field(default_factory=list)
    topology: str = "triangle"
    target_polycount: int = 30_000
    symmetry_mode: str = "auto"
    should_remesh: bool = True
    should_texture: bool = True
    enable_pbr: bool = False
    pose_mode: str = ""
    texture_prompt: str = ""
    texture_image_url: str = ""
    enable_rigging: bool = False
    rigging_height_meters: float = 1.7
    enable_animation: bool = False
    animation_action_id: int = 92
    enable_safety_checker: bool = True

    def validate(self) -> list[str]:
        """Return a list of human-readable validation errors (empty if valid)."""
        errors: list[str] = []
        if self.topology not in TOPOLOGY_VALUES:
            errors.append(f"topology must be one of {TOPOLOGY_VALUES}.")
        if self.symmetry_mode not in SYMMETRY_VALUES:
            errors.append(f"symmetry_mode must be one of {SYMMETRY_VALUES}.")
        if self.pose_mode not in POSE_VALUES:
            errors.append("pose_mode must be '', 'a-pose' or 't-pose'.")
        if not (POLYCOUNT_MIN <= self.target_polycount <= POLYCOUNT_MAX):
            errors.append(
                f"target_polycount must be between {POLYCOUNT_MIN:,} and {POLYCOUNT_MAX:,}."
            )
        if not (RIG_HEIGHT_MIN <= self.rigging_height_meters <= RIG_HEIGHT_MAX):
            errors.append("rigging_height_meters must be between 0.1 and 10.0.")
        if not (ANIM_ACTION_MIN <= self.animation_action_id <= ANIM_ACTION_MAX):
            errors.append("animation_action_id must be between 0 and 696.")

        # Cross-field dependencies enforced by the API.
        if self.enable_pbr and not self.should_texture:
            errors.append("enable_pbr requires should_texture to be enabled.")
        if self.texture_prompt and not self.should_texture:
            errors.append("texture_prompt requires should_texture to be enabled.")
        if self.texture_image_url and not self.should_texture:
            errors.append("texture_image_url requires should_texture to be enabled.")
        if self.enable_animation and not self.enable_rigging:
            errors.append("enable_animation requires enable_rigging to be enabled.")
        return errors

    def to_arguments(self) -> dict[str, Any]:
        """Build the ``arguments`` payload sent to fal.ai.

        Only meaningful fields are included so we don't send empty strings or
        options that the API would reject given the current toggles.
        """
        args: dict[str, Any] = {
            "image_urls": list(self.image_urls),
            "topology": self.topology,
            "target_polycount": int(self.target_polycount),
            "symmetry_mode": self.symmetry_mode,
            "should_remesh": bool(self.should_remesh),
            "should_texture": bool(self.should_texture),
            "enable_safety_checker": bool(self.enable_safety_checker),
        }
        if self.should_texture:
            args["enable_pbr"] = bool(self.enable_pbr)
            if self.texture_prompt.strip():
                args["texture_prompt"] = self.texture_prompt.strip()
            if self.texture_image_url.strip():
                args["texture_image_url"] = self.texture_image_url.strip()
        if self.pose_mode:
            args["pose_mode"] = self.pose_mode
        if self.enable_rigging:
            args["enable_rigging"] = True
            args["rigging_height_meters"] = float(self.rigging_height_meters)
            if self.enable_animation:
                args["enable_animation"] = True
                args["animation_action_id"] = int(self.animation_action_id)
        return args


def iter_result_files(result: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Flatten a result dict into ``(label, file_obj)`` pairs for download.

    A ``file_obj`` is a dict with at least a ``url`` key (per the File schema).
    """
    files: list[tuple[str, dict[str, Any]]] = []
    seen_urls: set[str] = set()

    def add(label: str, obj: Any) -> None:
        if isinstance(obj, dict) and obj.get("url"):
            url = obj["url"]
            if url in seen_urls:  # e.g. model_glb duplicates model_urls.glb
                return
            seen_urls.add(url)
            files.append((label, obj))

    if not isinstance(result, dict):
        return files

    add("Model (GLB)", result.get("model_glb"))
    add("Thumbnail", result.get("thumbnail"))

    model_urls = result.get("model_urls")
    if isinstance(model_urls, dict):
        for fmt in MODEL_FORMATS:
            add(f"Model ({fmt.upper()})", model_urls.get(fmt))

    for i, tex in enumerate(result.get("texture_urls") or []):
        if isinstance(tex, dict):
            for kind, obj in tex.items():
                add(f"Texture {i} · {kind}", obj)

    add("Animation (GLB)", result.get("animation_glb"))
    add("Animation (FBX)", result.get("animation_fbx"))
    add("Rigged character (GLB)", result.get("rigged_character_glb"))
    add("Rigged character (FBX)", result.get("rigged_character_fbx"))

    basic = result.get("basic_animations")
    if isinstance(basic, dict):
        for kind, obj in basic.items():
            add(f"Basic animation · {kind}", obj)

    return files
