"""Legacy profile source scanning (M3 eighth slice, read-only).

Locates legacy ``profiles/*.txt`` notes and exposes their parsed candidates for
review. This layer never writes to the rule store: listing and preview are
read-only, and any audit/import decision remains a later slice.

The source directory defaults to ``<repo>/legacy-materials/profiles`` and can be
overridden with the ``WORKBENCH_PROFILES_DIR`` env var so tests can point at a
temporary directory.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import profile_parser


def profiles_dir() -> Path:
    override = os.environ.get("WORKBENCH_PROFILES_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parent.parent / "legacy-materials" / "profiles"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def list_profiles(source_dir: Path | None = None) -> list[dict[str, Any]]:
    """Return a summary for every ``.txt`` profile in the source directory.

    Unreadable or corrupt files are reported with an ``error`` field instead of
    raising, so the listing endpoint never returns 500 over a single bad note.
    """
    directory = source_dir or profiles_dir()
    items: list[dict[str, Any]] = []
    if not directory.is_dir():
        return items

    for path in sorted(directory.glob("*.txt")):
        entry: dict[str, Any] = {
            "file": path.name,
            "filename": None,
            "display_name": None,
            "architecture": None,
            "candidates": 0,
            "unknown_fields": [],
            "error": None,
        }
        try:
            parsed = profile_parser.parse_profile_text(_read_text(path), path.name)
            entry["filename"] = parsed.filename
            entry["display_name"] = parsed.display_name
            entry["architecture"] = parsed.architecture
            entry["candidates"] = len(parsed.candidates)
            entry["unknown_fields"] = parsed.unknown_fields
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            entry["error"] = str(exc)
        items.append(entry)
    return items


def preview_profile(file_name: str, source_dir: Path | None = None) -> dict[str, Any]:
    """Parse one profile and return its identity plus candidate records.

    The returned records are the same projection used for later import review;
    they are not persisted. Raises ``FileNotFoundError`` when the file is absent
    so the API layer can map it to 404.
    """
    directory = source_dir or profiles_dir()
    safe_name = Path(file_name).name
    path = directory / safe_name
    if not path.is_file():
        raise FileNotFoundError(safe_name)

    parsed = profile_parser.parse_profile_text(_read_text(path), safe_name)
    records = profile_parser.candidates_to_records(
        parsed, level="checkpoint", scope_key=parsed.filename
    )
    return {
        "file": safe_name,
        "filename": parsed.filename,
        "display_name": parsed.display_name,
        "architecture": parsed.architecture,
        "unknown_fields": parsed.unknown_fields,
        "candidates": records,
    }
