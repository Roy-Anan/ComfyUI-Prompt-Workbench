"""Conservative normalization of legacy base-architecture labels.

Legacy profiles write the same family several ways (``SDXL``, ``SDXL 1.0``,
``sdxl``). This module maps those variants onto a small set of canonical
families so architecture rules can be inherited across same-family checkpoints.

Conservative by design:

  * only explicit keyword matches are promoted to a canonical family;
  * mixed or derived labels (``Pony / SDXL 系``, ``微调自 IL-XL``) keep
    ``mixed=True`` and are not silently merged into a plain family;
  * an unrecognized label stays ``other`` with ``matched=False``; the engine
    never invents a family from the checkpoint filename.

Pure module: no filesystem, network or store access.
"""

from __future__ import annotations

import re
from typing import Any

# Canonical family keys.
FAMILY_SD15 = "SD1.5"
FAMILY_SDXL = "SDXL"
FAMILY_PONY = "Pony"
FAMILY_OTHER = "other"

_SD15 = re.compile(r"sd\s*1\.5|sd15\b")
_SDXL = re.compile(r"sd\s*xl\b|sdxl\b")
_PONY = re.compile(r"pony")
_DERIVED = re.compile(r"illustrious|il-?xl|微调自|派生|混合")


def _detect(text: str) -> set[str]:
    families: set[str] = set()
    if _SD15.search(text):
        families.add(FAMILY_SD15)
    if _SDXL.search(text):
        families.add(FAMILY_SDXL)
    if _PONY.search(text):
        families.add(FAMILY_PONY)
    return families


def normalize(label: str | None) -> dict[str, Any]:
    """Return the normalized family for one raw architecture label.

    Result keys: ``raw`` (original text), ``canonical`` (canonical family key
    or None), ``family`` (``sd15``/``sdxl``/``pony``/``other``), ``mixed``
    (multiple families or a derived marker present), ``matched`` (a known
    family was recognized).
    """
    raw = label.strip() if isinstance(label, str) and label.strip() else None
    if raw is None:
        return {
            "raw": None,
            "canonical": None,
            "family": FAMILY_OTHER.lower(),
            "mixed": False,
            "matched": False,
        }

    lowered = raw.lower()
    families = _detect(lowered)
    derived = bool(_DERIVED.search(lowered))

    if not families:
        return {
            "raw": raw,
            "canonical": None,
            "family": FAMILY_OTHER.lower(),
            "mixed": derived,
            "matched": False,
        }

    mixed = len(families) > 1 or derived
    if FAMILY_PONY in families:
        canonical = FAMILY_PONY
    elif FAMILY_SDXL in families:
        canonical = FAMILY_SDXL
    else:
        canonical = next(iter(families))

    family_key = canonical.lower().replace(".", "")
    return {
        "raw": raw,
        "canonical": canonical,
        "family": family_key,
        "mixed": mixed,
        "matched": True,
    }


def same_family(a: str | None, b: str | None) -> bool:
    """True when two labels normalize to the same canonical family."""
    left = normalize(a)
    right = normalize(b)
    return bool(left["matched"] and right["matched"] and left["canonical"] == right["canonical"])
