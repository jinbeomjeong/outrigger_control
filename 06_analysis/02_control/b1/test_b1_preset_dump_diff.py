"""Unit tests of the I-17 preset dump comparison ``b1_preset_dump_diff.py`` (synthetic dumps)."""

from __future__ import annotations

import dataclasses
import enum
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import b1_preset_dump_diff as pdd  # noqa: E402


def _dump(preset: dict, default: dict | None = None) -> dict:
    return {"preset": preset, "default": preset if default is None else default}


def test_equal_dumps_pass() -> None:
    base = _dump({"a.x": 1.0, "a.y": True})
    assert pdd.compare(base, base)["i17_ok"] is True


def test_changed_common_field_fails() -> None:
    result = pdd.compare(_dump({"a.x": 1.0}), _dump({"a.x": 1.0000000000000002}))
    assert result["i17_ok"] is False and result["common_diff"][0]["field"] == "a.x"


def test_new_field_must_equal_the_class_default() -> None:
    base = _dump({"a.x": 1.0})
    head_ok = _dump({"a.x": 1.0, "b.enable": False}, {"a.x": 2.0, "b.enable": False})
    head_on = _dump({"a.x": 1.0, "b.enable": True}, {"a.x": 2.0, "b.enable": False})
    assert pdd.compare(base, head_ok)["i17_ok"] is True
    result = pdd.compare(base, head_on)
    assert result["i17_ok"] is False and result["new_not_default"][0]["field"] == "b.enable"


def test_removed_field_fails() -> None:
    result = pdd.compare(_dump({"a.x": 1.0, "a.z": 0}), _dump({"a.x": 1.0}))
    assert result["removed_fields"] == ["a.z"] and result["i17_ok"] is False


class _Mode(enum.Enum):
    ON = 1


@dataclasses.dataclass(frozen=True)
class _Inner:
    gain: float = 0.5
    mode: _Mode = _Mode.ON
    items: tuple = (1, 2)
    table: dict = dataclasses.field(default_factory=dict)


@dataclasses.dataclass(frozen=True)
class _Outer:
    inner: _Inner = dataclasses.field(default_factory=_Inner)
    limit: float = float("inf")


def test_normalise_and_flatten_nested_dataclasses() -> None:
    flat = pdd.flatten(pdd.normalise(_Outer()))
    assert flat == {"inner.gain": 0.5, "inner.mode": "_Mode.ON", "inner.items": [1, 2],
                    "inner.table": {}, "limit": {"float": "inf"}}
