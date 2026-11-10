"""C4G2 / K1 acceptance: pinned checkout on sys.path and the candidate combination on the R8 preset.

The project is not changed. ``C2Config.with_10hz_d1`` gets other keyword defaults in this process and in its
spawned workers, as ``05_tests/unit/pre_switch_preset_runner.py`` does; a caller that passes a keyword keeps it.
Env: ACC_WT (pinned checkout, required), ACC_COMBO both | c4g2 | k1 | off | preset (default both).
``preset`` (D8x, ``d8x_rules.md`` 2.1) leaves ``with_10hz_d1`` untouched. "Main tree" means the
main checkout outside the pinned tree: a pinned git worktree under ``.claude/worktrees`` and the
main checkout itself (ACC_WT = main) keep their own folders (before 2026-11-10 such a run removed
its own 03_src and stopped at ``import outrigger_sim``).
ACC_K2 off | on (``k2_touch_creep_rules.md`` 9.1-4, V-5): the ``touch_creep_latch`` keyword default of
``with_10hz_d1`` in this process and its workers (both arms explicit, also with ``ACC_COMBO=preset``); the provenance
then records ``k2``, ``touch_creep_latch`` and ``controller_tag``. Unset = as before.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

MAIN_TREE = Path(r"C:\workspace\outrigger_control").resolve()
COMBOS = {"both": (True, True), "c4g2": (True, False), "k1": (False, True), "off": (False, False)}
PRESET_COMBO = "preset"
"""D8x: the preset as it is (no keyword default replaced)."""
K2_ENV = "ACC_K2"
K2_CHOICES = ("off", "on")


def wt_root() -> Path:
    return Path(os.environ["ACC_WT"]).resolve()


def _is_within(path: Path, folder: Path) -> bool:
    return path == folder or folder in path.parents


def is_main_tree_path(path: str | Path) -> bool:
    """A path in the main checkout but not in the pinned tree ACC_WT."""
    resolved = Path(path).resolve()
    return _is_within(resolved, MAIN_TREE) and not _is_within(resolved, wt_root())


def combo() -> str:
    name = os.environ.get("ACC_COMBO", "both")
    if name not in COMBOS and name != PRESET_COMBO:
        raise SystemExit(f"ACC_COMBO {name!r}: expected one of {sorted([*COMBOS, PRESET_COMBO])}")
    return name


class MainTreeGuard:
    """First meta path finder: main-tree folders leave sys.path before every import.

    Some harness files insert the main tree themselves (``r8d1/r8d1_td.py`` line 24); with the folder gone the same
    module name resolves in the pinned checkout, in the parent and in every spawned worker.
    """

    @staticmethod
    def find_spec(name, path=None, target=None):
        for entry in list(sys.path):
            try:
                inside = entry and is_main_tree_path(entry)
            except OSError:
                inside = False
            if inside:
                sys.path.remove(entry)
                print(f"[acc_guard] removed from sys.path: {entry}", file=sys.stderr, flush=True)
        return None


def install() -> None:
    """Pinned 03_src first, the preset defaults of the combination, no main-tree import."""
    if not any(isinstance(f, type) and f is MainTreeGuard for f in sys.meta_path):
        sys.meta_path.insert(0, MainTreeGuard)
    root = wt_root()
    for sub in ("03_src", "04_scripts/03_control/s8", "04_scripts/03_control/s9", "04_scripts/03_control/r8d1",
                "04_scripts/03_control", "04_scripts/04_hydraulic/coupled", "04_scripts/01_dynamics",
                "04_scripts/02_chrono"):
        text = str(root / sub)
        if text in sys.path:
            sys.path.remove(text)
        sys.path.insert(0, text)
    sys.path.insert(0, str(root / "03_src"))
    from outrigger_sim.control import c2

    if root not in Path(c2.__file__).resolve().parents:
        raise SystemExit(f"c2 comes from {c2.__file__}, not from {root}")
    _install_k2(c2)
    if getattr(c2.C2Config, "_acc_patched", False) or combo() == PRESET_COMBO:
        return
    hold, retrigger = COMBOS[combo()]
    original = c2.C2Config.with_10hz_d1

    def with_10hz_d1(self, *args, touch_twist_hold=hold, reapproach_retrigger_two_samples=retrigger, **kwargs):
        return original(self, *args, touch_twist_hold=touch_twist_hold,
                        reapproach_retrigger_two_samples=reapproach_retrigger_two_samples, **kwargs)

    c2.C2Config.with_10hz_d1 = with_10hz_d1
    c2.C2Config._acc_patched = True


def k2_arm() -> str | None:
    """``ACC_K2`` (``off`` / ``on``), None when unset."""
    value = os.environ.get(K2_ENV)
    if value in (None, ""):
        return None
    if value not in K2_CHOICES:
        raise SystemExit(f"{K2_ENV} {value!r}: expected one of {K2_CHOICES}")
    return value


def _install_k2(c2) -> None:
    """``ACC_K2``: the ``touch_creep_latch`` default of ``with_10hz_d1`` (once per process)."""
    arm = k2_arm()
    if arm is None or getattr(c2.C2Config, "_acc_k2_patched", False):
        return
    original = c2.C2Config.with_10hz_d1

    def with_10hz_d1(self, *args, touch_creep_latch=arm == "on", **kwargs):
        return original(self, *args, touch_creep_latch=touch_creep_latch, **kwargs)

    c2.C2Config.with_10hz_d1 = with_10hz_d1
    c2.C2Config._acc_k2_patched = True


def main_tree_modules() -> list[str]:
    bad = []
    for name, module in list(sys.modules.items()):
        path = getattr(module, "__file__", None)
        if path:
            try:
                if is_main_tree_path(path):
                    bad.append(f"{name}: {path}")
            except OSError:
                pass
    return bad


def provenance() -> dict:
    root = wt_root()
    from outrigger_sim.control import c2

    config = c2.C2Config().with_10hz_d1()
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=30).stdout.strip()
    k2 = {}
    if k2_arm() is not None:  # keys only with ACC_K2
        from outrigger_sim.hydraulics.v5_options import controller_tag

        k2 = {"k2": k2_arm(), "touch_creep_latch": config.touch_creep_latch.enable,
              "controller_tag": controller_tag(None, config)}
    return {"wt": str(root), "git_head": head, "combo": combo(), **k2,
            "c2_sha256": hashlib.sha256(Path(c2.__file__).read_bytes()).hexdigest(),
            "touch_twist_hold": config.touch_twist_hold.enable, "vector_ramp": config.touch_twist_hold.vector_ramp,
            "ramp_twist_tol_m_s": config.touch_twist_hold.ramp_twist_tol_m_s,
            "retrigger_samples": getattr(config.r8.lifted_reapproach, "retrigger_samples", None),
            "threads": {k: os.environ.get(k) for k in ("MKL_THREADING_LAYER", "MKL_NUM_THREADS", "OMP_NUM_THREADS", "NUMBA_NUM_THREADS", "OPENBLAS_NUM_THREADS")}}


def write_provenance(path: Path, extra: dict | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({**provenance(), **(extra or {})}, indent=1), encoding="utf-8")
