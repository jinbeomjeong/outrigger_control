"""SCM convex-hull hook wrapper (outrigger_sim.chrono.hull_hook): default fast since 2026-11-09, env off restores
the original path (nothing loaded)."""

import pytest

from outrigger_sim.chrono import hull_hook


def test_requested_mode_default_is_fast() -> None:
    assert hull_hook.DEFAULT_MODE == "fast"
    assert hull_hook.requested_mode({}) == ("fast", "default")
    assert hull_hook.requested_mode({hull_hook.ENV_MODE: ""}) == ("fast", "default")
    assert hull_hook.requested_mode({hull_hook.ENV_MODE: "   "}) == ("fast", "default")


def test_requested_mode_explicit() -> None:
    assert hull_hook.requested_mode({hull_hook.ENV_MODE: "off"}) == ("off", "env")
    assert hull_hook.requested_mode({hull_hook.ENV_MODE: " OFF "}) == ("off", "env")
    assert hull_hook.requested_mode({hull_hook.ENV_MODE: "Fast"}) == ("fast", "env")


def test_env_off_loads_nothing(monkeypatch) -> None:
    monkeypatch.setattr(hull_hook, "_state", {"lib": None, "meta": None})
    meta = hull_hook.install_from_env({hull_hook.ENV_MODE: "off"})
    assert meta["mode"] == "off" and meta["requested"] == "off" and meta["source"] == "env"
    assert meta["dll"] is None and not hull_hook.active()
    rec = hull_hook.stats_record()
    assert rec["mode"] == "off" and rec["stats"] is None


def test_bad_value_exits_2(monkeypatch) -> None:
    monkeypatch.setattr(hull_hook, "_state", {"lib": None, "meta": None})
    with pytest.raises(SystemExit) as e:
        hull_hook.install_from_env({hull_hook.ENV_MODE: "fastest"})
    assert e.value.code == 2


def test_default_missing_dll_falls_back_to_off(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(hull_hook, "_state", {"lib": None, "meta": None})
    monkeypatch.setitem(hull_hook.sys.modules, "pychrono.vehicle", object())
    missing = str(tmp_path / "none.dll")
    meta = hull_hook.install_from_env({hull_hook.ENV_DLL: missing})
    assert meta["mode"] == "off" and meta["requested"] == "fast" and meta["source"] == "default"
    assert "DLL missing" in meta["fallback_reason"] and not hull_hook.active()


def test_explicit_missing_dll_exits_2(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(hull_hook, "_state", {"lib": None, "meta": None})
    monkeypatch.setitem(hull_hook.sys.modules, "pychrono.vehicle", object())
    with pytest.raises(SystemExit) as e:
        hull_hook.install_from_env({hull_hook.ENV_MODE: "fast", hull_hook.ENV_DLL: str(tmp_path / "none.dll")})
    assert e.value.code == 2


def test_no_record_before_install(monkeypatch) -> None:
    monkeypatch.setattr(hull_hook, "_state", {"lib": None, "meta": None})
    assert hull_hook.stats_record() is None
    assert hull_hook.stats() is None


def test_dll_path_inside_native_folder() -> None:
    assert hull_hook.DLL_PATH.parts[-4:] == ("native", "chrono_hull", "bin", "chrono_hull_hook.dll")
