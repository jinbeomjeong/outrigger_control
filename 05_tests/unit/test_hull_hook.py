"""Opt-in SCM convex-hull hook wrapper (outrigger_sim.chrono.hull_hook): default off loads nothing."""

from outrigger_sim.chrono import hull_hook


def test_absent_or_empty_env_is_off() -> None:
    assert hull_hook.install_from_env({}) is None
    assert hull_hook.install_from_env({hull_hook.ENV_MODE: ""}) is None
    assert hull_hook.install_from_env({hull_hook.ENV_MODE: "   "}) is None


def test_no_record_when_off() -> None:
    if hull_hook.active():  # a session that set OUTRIGGER_HULL_HOOK on purpose
        return
    assert hull_hook.stats_record() is None
    assert hull_hook.stats() is None


def test_dll_path_inside_native_folder() -> None:
    assert hull_hook.DLL_PATH.parts[-4:] == ("native", "chrono_hull", "bin", "chrono_hull_hook.dll")
