"""Read-only model catalog for the local workbench.

This module reads model names that ComfyUI already exposes through its
``/object_info`` endpoint and, when the user has configured an external model
directory, checks whether each listed file exists on disk. It never copies
weights, never hashes files in this slice, and never writes into ComfyUI
directories.

Scope (M3 first slice):
  * checkpoint names from checkpoint / UNET loader widgets
  * LoRA names from the LoRA loader widget
  * optional on-disk existence check against a configured local directory

SHA256 identity records, architecture/rule inheritance and conflict detection
are later M3 work and are intentionally not implemented here.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# Loader node -> widget input that holds the model filename option list.
# Checkpoint / UNET weights, CLIP and VAE are kept as separate groups so the
# catalog can report them without mixing a VAE into the checkpoint list.
CHECKPOINT_WIDGETS: dict[str, tuple[str, ...]] = {
    "CheckpointLoaderSimple": ("ckpt_name",),
    "CheckpointLoader": ("ckpt_name",),
    "UNETLoader": ("unet_name",),
}
CLIP_WIDGETS: dict[str, tuple[str, ...]] = {
    "DualCLIPLoader": ("clip_name1", "clip_name2"),
    "CLIPLoader": ("clip_name",),
}
VAE_WIDGETS: dict[str, tuple[str, ...]] = {
    "VAELoader": ("vae_name",),
}
LORA_WIDGETS: dict[str, tuple[str, ...]] = {
    "LoraLoader": ("lora_name",),
    "LoraLoaderModelOnly": ("lora_name",),
}

# File extensions treated as model weights for the on-disk existence check.
_MODEL_SUFFIXES = {".safetensors", ".ckpt", ".pt", ".pth", ".bin", ".gguf"}


def _http_get_json(url: str, timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "ComfyUI-Prompt-Workbench"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
    return json.loads(body.decode("utf-8"))


def _widget_options(spec: dict[str, Any], widget: str) -> list[str]:
    """Return the filename option list for one widget, if present."""
    required = spec.get("input", {}).get("required", {})
    value = required.get(widget)
    if not isinstance(value, list) or not value:
        return []
    options = value[0]
    if not isinstance(options, list):
        return []
    return [str(item) for item in options if isinstance(item, str)]


def _extract_options(
    object_info: dict[str, Any],
    widgets: dict[str, tuple[str, ...]],
) -> list[str]:
    names: set[str] = set()
    for node_type, widget_names in widgets.items():
        spec = object_info.get(node_type)
        if not isinstance(spec, dict):
            continue
        for widget in widget_names:
            names.update(_widget_options(spec, widget))
    return sorted(names)


def _index_directory(directory: str) -> set[str]:
    """Index weight filenames directly under ``directory`` (read-only).

    ComfyUI keeps checkpoints and LoRAs in flat subfolders; nested model
    folders are not traversed in this slice. Missing/invalid directories
    return an empty set.
    """
    if not directory:
        return set()
    path = Path(directory).expanduser()
    if not path.is_dir():
        return set()
    names: set[str] = set()
    for entry in path.iterdir():
        if entry.is_file() and entry.suffix.lower() in _MODEL_SUFFIXES:
            names.add(entry.name)
    return names


def _annotate(names: list[str], directory: str) -> list[dict[str, Any]]:
    indexed = _index_directory(directory)
    if indexed:
        return [
            {"name": name, "on_disk": name in indexed} for name in names
        ]
    # No directory configured: existence is unknown, not false.
    return [{"name": name, "on_disk": None} for name in names]


def fetch_catalog(
    comfyui_url: str,
    checkpoint_dir: str = "",
    lora_dir: str = "",
    timeout: float = 4.0,
) -> dict[str, Any]:
    """Fetch checkpoint / LoRA names from ComfyUI and annotate on-disk status.

    Returns a report with ``online``, ``checkpoints`` and ``loras``. When
    ComfyUI is unreachable, ``online`` is False and lists are empty; the
    caller surfaces the error separately.
    """
    base = comfyui_url.rstrip("/")
    try:
        object_info = _http_get_json(base + "/object_info", timeout=timeout)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "online": False,
            "error": str(exc),
            "checkpoints": [],
            "clips": [],
            "vaes": [],
            "loras": [],
        }

    checkpoints = _extract_options(object_info, CHECKPOINT_WIDGETS)
    clips = _extract_options(object_info, CLIP_WIDGETS)
    vaes = _extract_options(object_info, VAE_WIDGETS)
    loras = _extract_options(object_info, LORA_WIDGETS)
    return {
        "online": True,
        "error": None,
        "checkpoints": _annotate(checkpoints, checkpoint_dir),
        "clips": [{"name": name, "on_disk": None} for name in clips],
        "vaes": [{"name": name, "on_disk": None} for name in vaes],
        "loras": _annotate(loras, lora_dir),
    }
