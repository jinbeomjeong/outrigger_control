"""SCM convex-hull hook wrapper (outrigger_sim.chrono.hull_hook): default fast since 2026-11-09, env off restores
the original path (nothing loaded)."""

import hashlib
from types import SimpleNamespace

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


# --- validated DLL build (post-switch audit 2026-11-09) ---------------------------------------------------------


class _FakeFunction:
    """ctypes function stand-in: accepts ``restype`` / ``argtypes`` and returns a fixed value."""

    def __init__(self, value) -> None:
        self.value = value

    def __call__(self, *_args):
        return self.value


def _fake_lib() -> SimpleNamespace:
    return SimpleNamespace(chrono_hull_hook_status_string=_FakeFunction(b"ok"),
                           chrono_hull_hook_install=_FakeFunction(0),
                           chrono_hull_hook_install_from_env=_FakeFunction(0),
                           chrono_hull_hook_mode=_FakeFunction(hull_hook.MODE_CODES["fast"]),
                           chrono_hull_hook_version=_FakeFunction(hull_hook.API_VERSION),
                           chrono_hull_hook_get_stats=_FakeFunction(0))


@pytest.fixture
def fake_dll(monkeypatch, tmp_path):
    """A stand-in DLL file whose hash is not the validated build; loading it records the path instead."""
    monkeypatch.setattr(hull_hook, "_state", {"lib": None, "meta": None})
    monkeypatch.setitem(hull_hook.sys.modules, "pychrono.vehicle", object())
    dll = tmp_path / "chrono_hull_hook.dll"
    dll.write_bytes(b"not the validated build")
    loaded: list[str] = []

    def fake_cdll(path):
        loaded.append(path)
        return _fake_lib()

    monkeypatch.setattr(hull_hook.ctypes, "CDLL", fake_cdll)
    return SimpleNamespace(path=dll, sha=hashlib.sha256(dll.read_bytes()).hexdigest(), loaded=loaded)


def test_validated_sha_constant() -> None:
    assert hull_hook.VALIDATED_DLL_SHA256 == "cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15"


def test_default_unvalidated_dll_falls_back_to_off(fake_dll) -> None:
    meta = hull_hook.install_from_env({hull_hook.ENV_DLL: str(fake_dll.path)})
    assert meta["mode"] == "off" and meta["requested"] == "fast" and meta["source"] == "default"
    assert meta["fallback_reason"] == "dll_sha_unvalidated"
    assert meta["dll_sha256"] == fake_dll.sha and meta["dll_sha_validated"] is False
    assert meta["allow_unvalidated"] is False
    assert fake_dll.loaded == [] and not hull_hook.active()  # the unvalidated DLL is never loaded
    assert hull_hook.stats_record()["fallback_reason"] == "dll_sha_unvalidated"


@pytest.mark.parametrize("mode", ["fast", "shadow", "dump"])
def test_explicit_unvalidated_dll_exits_2(fake_dll, mode) -> None:
    with pytest.raises(SystemExit) as e:
        hull_hook.install_from_env({hull_hook.ENV_MODE: mode, hull_hook.ENV_DLL: str(fake_dll.path)})
    assert e.value.code == 2 and fake_dll.loaded == []


def test_allow_unvalidated_warns_and_installs(fake_dll, capsys) -> None:
    meta = hull_hook.install_from_env({hull_hook.ENV_DLL: str(fake_dll.path),
                                       hull_hook.ENV_ALLOW_UNVALIDATED: "1"})
    assert meta["mode"] == "fast" and meta["fallback_reason"] is None and hull_hook.active()
    assert meta["dll_sha_validated"] is False and meta["allow_unvalidated"] is True
    assert meta["env"][hull_hook.ENV_ALLOW_UNVALIDATED] == "1"
    assert fake_dll.loaded == [str(fake_dll.path.resolve())]
    assert "not the validated build" in capsys.readouterr().out
    rec = hull_hook.stats_record()
    assert rec["allow_unvalidated"] is True and rec["stats"]["calls"] == 0


def test_allow_unvalidated_explicit_mode_proceeds(fake_dll) -> None:
    meta = hull_hook.install_from_env({hull_hook.ENV_MODE: "fast", hull_hook.ENV_DLL: str(fake_dll.path),
                                       hull_hook.ENV_ALLOW_UNVALIDATED: "1"})
    assert meta["mode"] == "fast" and meta["source"] == "env" and meta["dll_sha_validated"] is False


def test_allow_unvalidated_needs_exactly_1(fake_dll) -> None:
    meta = hull_hook.install_from_env({hull_hook.ENV_DLL: str(fake_dll.path),
                                       hull_hook.ENV_ALLOW_UNVALIDATED: "0"})
    assert meta["mode"] == "off" and meta["fallback_reason"] == "dll_sha_unvalidated"


def test_validated_dll_installs_without_warning(fake_dll, monkeypatch, capsys) -> None:
    monkeypatch.setattr(hull_hook, "VALIDATED_DLL_SHA256", fake_dll.sha)
    meta = hull_hook.install_from_env({hull_hook.ENV_DLL: str(fake_dll.path)})
    assert meta["mode"] == "fast" and meta["dll_sha_validated"] is True and meta["allow_unvalidated"] is False
    assert "WARNING" not in capsys.readouterr().out
