"""Placeholder slot names, shared so that every ``--allow`` means the same thing.

``placeholder_scan.py`` and ``ps1_lint.py`` both take ``--allow``. A slot may be
named bare (``MASK``) or as it is written (``{MASK}``, ``<MASK>``); all three
name the slot ``MASK`` and allow every token of that slot (2026-11-22).
"""

from __future__ import annotations

from collections.abc import Iterable


def is_angle_token(token: str) -> bool:
    """True for ``<...>`` tokens."""
    return len(token) > 1 and token.startswith("<") and token.endswith(">")


def slot_name(token: str) -> str:
    """``{MASK}`` and ``<MASK>`` name the slot ``MASK``; bare words name themselves."""
    if is_angle_token(token):
        return token[1:-1]
    return token.strip("{}")


def allowed_slot_names(names: Iterable[str]) -> set[str]:
    """Slot names of ``--allow`` values (``MASK``, ``{MASK}`` and ``<MASK>`` alike)."""
    return {slot_name(name.strip()) for name in names}
