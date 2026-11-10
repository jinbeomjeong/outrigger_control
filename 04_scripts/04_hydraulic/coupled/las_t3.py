"""T-3 targeted check of LAS-b (sealed ``las_targeted_rules_rev3.md`` 2 .. 4, its key list
``las_targeted_rules_rev3_keys.json``, ``las_targeted_rules_rev4.md`` 1 #1: T-3c included, and
``las_targeted_rules_rev4a.md``: G6-2_loc, stop attribution, Dg-3 off reproduction).

Bundles (key list): R-0 7 (LAS-b off: D-1 5 + Dg-3 2), T-3a 228, T-3b 4 (Dg-3 2 keys x folders
``off`` / ``v4_on``), T-3c 76; R-0 runs first and T-3 starts only when R-0 passes K-1 .. K-3
(H-T3-1). LAS-b is the 03_src preset (``C2Config.with_10hz_d1()``, b0); no wrapper is installed.

D-1 lines: ``d1_rows.jobs()`` filtered by the key list (counts asserted), each one
``run_v5.run_one`` in a spawned worker (``maxtasksperchild=1``). An R-0 worker first makes the
switch of ``05_tests/unit/pre_las_preset_runner.py`` (it imports that file). The worker refuses a
run when ``C2Controller`` / ``C2Config`` carry a function from another module (a wrapper; for R-0
only ``with_10hz_d1`` of the pre-LAS runner is allowed), when the thread variables are not 1 or
when the run's controller is not LAS-b b0 (T-3) / has LAS-b on (R-0). The worker keeps the run's
controller through a record-only wrapper of ``d1_runs.d1_record`` (arguments and return value
passed on unchanged, as ``las_targeted`` / ``fb_targeted``) and adds ``las_t3``: the
``INFO_LIFTOFF_SLOW*`` events (time, name), the controller meta ``liftoff_approach_slow`` (start,
leg, rho, end, active and scaled periods) and the judge's LOC - t_off
(``las_targeted.loc_delay_record``: the P3-2 row ``loc_delay_s`` of a steady row, the G6 record
of a g6 row). The command is never touched.

Dg-3 lines: ``las_t3_dg3.py`` (the r79 runner unchanged under the folder's condition) in a
subprocess, with the arguments of the stored result meta (``levels``, ``rod_model``,
``r72_path``, the record's ``v5_setting``) and ``--keys`` of one key, T4h into a new folder
``v5/las/t3_dg3_t4h/<bundle>_<folder>_<key>/``. The hash is the T4h meta ``commands_sha256``
(the definition ``las_shadow`` read on the stored records); "fired" = an ``INFO_LIFTOFF_SLOW``
event in the T4h meta events.

Every file starts with a header line (``{"header": ...}``): commit, tool and ``c2.py`` sha256,
thread variables, workers, affinity, seals; every line carries the same values (``t3.identity``,
the worker's own reading). Before any run (H-T3-0): the nine sealed files (original, rev1 ..
rev4, rev4a .. rev4c, the rev3 key list) equal their ``.sha256``
values, ``git status --porcelain -- 03_src 04_scripts`` is empty, no output exists (files are
opened with ``"x"``: no resume, no overwrite), no wrapper is installed, the preset is LAS-b b0 and
has no flow budget (FB). An error line is retried once (H-T3-2: both lines are kept).
At the end ``las_judge.judge_t3`` writes ``las_T3.md`` and ``las_T3_judge.json``.

Rules mode ``rev5`` (the default since ``las_targeted_rules_rev5.md``, sealed 2026-11-10; T-3
under the K1 preset). ``--rules rev4c`` keeps the run above unchanged. In ``rev5``:
  bundles  R-0 (LAS-b off, gate off, ``pre_las_preset_runner``) -> R-0K (45 D-1 keys of the
           sealed ``las_targeted_rules_rev5_r0k_keys.json``; LAS-b off, gate on, the switch
           ``las_t3_presets.install_las_off_gate_on``) -> T-3K (T-3a / b / c, the preset as it
           is: LAS-b b0 and gate on, no patch); each starts only when the one before passed
  checks   eleven seals (the nine + rev5 + its R-0K key list); the preset has the gate on,
           ``slope_clearance_margin.enable`` and ``flat_soil_margin_m`` 0.03 (H-T3-0); every
           run's controller has its bundle's LAS-b and gate state and R4c30 (error line); the
           stored Dg-3 T4h events have no ``INFO_LOC_FLAT_SOIL_MARGIN`` (H-T3-0); the worker
           allows ``with_10hz_d1`` only from the bundle's switch module
  records  ``las_t3.k1``: ``order_gate`` of the controller meta (``enabled``, ``decisions``) and
           ``would_block_any``, ``applied_any``, ``applied_count``, ``first_dP``,
           ``blocked_t_loc_s``
  output   ``v5/las/t3_k1/`` (``las_T3_R0.jsonl``, ``las_T3_R0K.jsonl``, ``las_T3.jsonl``, ...)

Usage (dynamics-dev python.exe, project root, PowerShell):
  python -I -B 04_scripts/04_hydraulic/coupled/las_t3.py list [--rules rev5|rev4c]
  python -I -B 04_scripts/04_hydraulic/coupled/las_t3.py run --workers N --affinity 0x...
      [--rules rev5|rev4c] [--only R-0|R-0K] [--keys K1,K2] [--out-dir DIR]
``--only R-0`` runs R-0 alone and stops (no T-3, no judge); ``--only R-0K`` (rev5) runs R-0, then
R-0K when R-0 passed, and stops before T-3K; ``--keys`` keeps the named line keys of the bundles
it runs (smoke checks; a subset is never a T-3 verdict, the judge's K-1 fails).
Exit codes: 0 passed, 1 a criterion failed (K-2, K-4, K-5, K-6; rev5: H-T3-1K too), 2 a stop
before or without a verdict (H-T3-0, H-T3-1, H-T3-2, H-T3-3; rev5: H-T3-1Q, stop and ask) or an
input error.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
import traceback
from collections.abc import Mapping
from multiprocessing import get_context
from pathlib import Path

# As run_v5: one BLAS / OpenMP thread, set before numpy loads (here and in every spawned worker).
# The value is forced: another value would make lines of another run identity.
for _name in ("MKL_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMBA_NUM_THREADS"):
    os.environ[_name] = "1"
os.environ.setdefault("MKL_THREADING_LAYER", "TBB")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import las_h7  # noqa: E402
import las_targeted as lt  # noqa: E402

V5_DIR = ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5"
OUT_DIR = V5_DIR / "las"
"""Output folder of the ``rev4c`` mode."""
OUT_DIR_REV5 = OUT_DIR / "t3_k1"
"""Output folder of the ``rev5`` mode (rev5 2.6: never mixed with the ``v5/las/`` smoke)."""
RULES_DIR = lt.RULES_PATH.parent
KEYS_PATH = RULES_DIR / "las_targeted_rules_rev3_keys.json"
R0K_KEYS_PATH = RULES_DIR / "las_targeted_rules_rev5_r0k_keys.json"
PRE_LAS_RUNNER = ROOT / "05_tests" / "unit" / "pre_las_preset_runner.py"
DG3_RUNNER = HERE / "las_t3_dg3.py"
R0_FILE = "las_T3_R0.jsonl"
R0K_FILE = "las_T3_R0K.jsonl"
T3_FILE = "las_T3.jsonl"
REPORT_FILE = "las_T3.md"
JUDGE_FILE = "las_T3_judge.json"
DG3_FOLDER = "t3_dg3_t4h"
RULES_REV4C = "rev4c"
RULES_REV5 = "rev5"
RULES_MODES = (RULES_REV5, RULES_REV4C)
"""Rules modes of the tool and the judge; the first is the default."""
REV4C_REQUIRED_SEALS = ("original", "rev1", "rev2", "rev3", "rev3_keys", "rev4", "rev4a",
                        "rev4b", "rev4c")
"""Rev3 K-0 with the rev4 .. rev4c seals (2026-11-08): all nine before a ``rev4c`` run."""
T3_REQUIRED_SEALS = (*REV4C_REQUIRED_SEALS, "rev5", "rev5_r0k_keys")
"""Rev5 1 #5: the nine and rev5 with its R-0K key list, eleven before a ``rev5`` run."""
R0 = "R-0"
R0K = "R-0K"
T3_BUNDLES = ("T-3a", "T-3b", "T-3c")
BUNDLES = (R0, *T3_BUNDLES)
EXPECTED_COUNTS = {R0: 7, "T-3a": 228, "T-3b": 4, "T-3c": 76}
"""Rev3 2.1 and rev4 1 #1 (T-3c fixed at 76)."""
R0K_EXPECTED_COUNT = 45
R0K_LIST_SHA256 = "9399c4922828973fe5129c6c5964dc2cf6c53137a8858d1f92e69f9c85452e3c"
"""Rev5 2.3: sha256 of the sorted R-0K keys, each followed by LF, UTF-8."""
R0K_CLASS_COUNTS = {"uniform_r4": 36, "patch_r4": 5, "r0_no_r4": 4}
CLASS_UNIFORM_R4 = "uniform_r4"
CLASS_R0_NO_R4 = "r0_no_r4"
KIND_D1 = "d1"
KIND_DG3 = "dg3"
LAS_ON = "on"
LAS_OFF = "off"
GATE_ON = "on"
GATE_OFF = "off"
BUNDLE_GATE = {R0: GATE_OFF, R0K: GATE_ON, **{bundle: GATE_ON for bundle in T3_BUNDLES}}
"""Rev5 2.2: the K1 order gate of each bundle (R-0 has the stored baseline's gate off). In the
``rev4c`` mode the same values are only recorded (the preset has had the gate on since the K1
switch); they are checked in ``rev5``."""
ALLOWED_PRESET_PATCHES: dict[str, dict[str, str]] = {
    R0: {"with_10hz_d1": "pre_las_preset_runner"},
    R0K: {"with_10hz_d1": "las_t3_presets"},
    **{bundle: {} for bundle in T3_BUNDLES},
}
"""Rev5 2.2: the only foreign method (name -> module) a worker of each bundle may carry."""
GATE_FIELD = "flat_soil_margin_order_gate"
GATE_SETTING_KEY = f"slope_clearance_margin.{GATE_FIELD}"
R4C30_MARGIN_M = 0.03
"""Rev5 2.2: ``slope_clearance_margin.flat_soil_margin_m`` of every run (R4c30)."""
R4C30_EVENT = "INFO_LOC_FLAT_SOIL_MARGIN"
DG3_P3_OF_FOLDER = {"off": "off", "v4_on": "on"}
"""The ③ condition of a stored Dg-3 folder (``las_t3_dg3.py``)."""
DG3_RULE_OF_FOLDER = {"off": "constant", "v4_on": "tracked_bound"}
"""``two_pressure.extend_start_rule`` the stored folders recorded."""
LAS_EVENT_PREFIX = "INFO_LIFTOFF_SLOW"
TOOL_FILES = {"las_t3.py": HERE / "las_t3.py", "las_t3_dg3.py": DG3_RUNNER,
              "las_h7.py": HERE / "las_h7.py", "las_judge.py": HERE / "las_judge.py",
              "las_targeted.py": HERE / "las_targeted.py",
              "las_t3_presets.py": HERE / "las_t3_presets.py"}
GIT_TIMEOUT_S = 60
DG3_TIMEOUT_S = 3600
"""One Dg-3 record takes 60 .. 120 s stored; an hour means a hung run."""
FB_FIELD_TOKEN = "flow_budget"
"""A C2 config block whose name has this would be the command flow budget (FB). At this
commit FB exists only as the ``fb_targeted`` wrapper; the check covers a later 03_src FB."""


# ------------------------------------------------------------------------------- key list
def dg3_line_key(folder: str, key: str) -> str:
    return f"dg3:{folder}:{key}"


def load_key_list(path: Path = KEYS_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def bundle_entries(keys: dict) -> dict[str, list[dict]]:
    """``bundle -> [{"key", "kind", ...}]`` of the key list (R-0 dg3 entries take the T-3b
    entry of the same folder and key as their baseline)."""
    dg3 = {(entry["folder"], entry["key"]): entry for entry in keys["T-3b"]}
    r0 = [{"line_key": key, "kind": KIND_D1, "key": key} for key in keys[R0]["d1"]]
    for folder, key in keys[R0]["dg3"]:
        r0.append({"line_key": dg3_line_key(folder, key), "kind": KIND_DG3,
                   **dg3[(folder, key)]})
    out = {R0: r0}
    for bundle in ("T-3a", "T-3c"):
        out[bundle] = [{"line_key": entry["key"], "kind": KIND_D1, **entry}
                       for entry in keys[bundle]]
    out["T-3b"] = [{"line_key": dg3_line_key(entry["folder"], entry["key"]), "kind": KIND_DG3,
                    **entry} for entry in keys["T-3b"]]
    return out


def count_problems(entries: dict[str, list[dict]]) -> list[str]:
    problems = []
    for bundle, expected in EXPECTED_COUNTS.items():
        keys = [entry["line_key"] for entry in entries[bundle]]
        if len(keys) != expected or len(set(keys)) != expected:
            problems.append(f"{bundle}: {len(keys)} keys ({len(set(keys))} unique) != {expected}")
    return problems


def load_r0k_key_list(path: Path = R0K_KEYS_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def r0k_entries(r0k_keys: dict) -> list[dict]:
    """The R-0K D-1 entries of the sealed rev5 key list (each with its ``class`` and stored
    hash)."""
    return [{"line_key": entry["key"], "kind": KIND_D1, **entry} for entry in r0k_keys[R0K]]


def key_list_digest(keys: list[str]) -> str:
    """Rev5 2.3: sha256 of the sorted keys, each followed by LF, UTF-8."""
    text = "".join(f"{key}\n" for key in sorted(keys))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def r0k_key_problems(r0k: list[dict], entries: dict[str, list[dict]]) -> list[str]:
    """Rev5 2.3 / K-1K: the R-0K list has 45 unique keys of the sealed digest and class counts,
    and every key is a D-1 key of T-3a, T-3c or R-0 of the rev3 key list."""
    keys = [entry["line_key"] for entry in r0k]
    problems = []
    if len(keys) != R0K_EXPECTED_COUNT or len(set(keys)) != R0K_EXPECTED_COUNT:
        problems.append(f"{R0K}: {len(keys)} keys ({len(set(keys))} unique) "
                        f"!= {R0K_EXPECTED_COUNT}")
    digest = key_list_digest(keys)
    if digest != R0K_LIST_SHA256:
        problems.append(f"{R0K}: list sha256 {digest} != {R0K_LIST_SHA256}")
    counts = {name: sum(entry.get("class") == name for entry in r0k) for name in R0K_CLASS_COUNTS}
    if counts != R0K_CLASS_COUNTS:
        problems.append(f"{R0K}: class counts {counts} != {R0K_CLASS_COUNTS}")
    rev3_d1 = {entry["line_key"] for bundle in (R0, "T-3a", "T-3c")
               for entry in entries.get(bundle, []) if entry["kind"] == KIND_D1}
    outside = sorted(set(keys) - rev3_d1)
    if outside:
        problems.append(f"{R0K}: {len(outside)} keys not D-1 keys of the rev3 list {outside[:3]}")
    return problems


def rules_entries(rules: str) -> dict[str, list[dict]]:
    """Bundle entries of a rules mode: the rev3 key list, plus R-0K in ``rev5``.

    Raises:
        OSError, KeyError, ValueError: A key list is missing or not of this form.
    """
    entries = bundle_entries(load_key_list())
    if rules == RULES_REV5:
        entries[R0K] = r0k_entries(load_r0k_key_list())
    return entries


def expected_count(bundle: str) -> int:
    return R0K_EXPECTED_COUNT if bundle == R0K else EXPECTED_COUNTS[bundle]


def d1_jobs(keys: list[str]) -> dict[str, dict]:
    """``composite key -> d1_rows job`` of ``keys``.

    Raises:
        KeyError: A key that ``d1_rows.jobs()`` does not have.
    """
    import d1_rows

    by_key = {lt.composite_key(job): job for job in d1_rows.jobs()}
    missing = [key for key in keys if key not in by_key]
    if missing:
        raise KeyError(f"not D-1 jobs: {missing[:5]}")
    return {key: by_key[key] for key in keys}


# ------------------------------------------------------------------------------- identity
def git_output(*args: str) -> str:
    completed = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True,
                               text=True, encoding="utf-8", check=True, timeout=GIT_TIMEOUT_S)
    return completed.stdout


def tree_changes() -> list[str]:
    """``git status --porcelain -- 03_src 04_scripts`` lines (untracked files included)."""
    return [line for line in git_output("status", "--porcelain", "--", "03_src",
                                        "04_scripts").splitlines() if line.strip()]


def _is_allowed(name: str, module: str, allowed: Mapping[str, str] | tuple[str, ...]) -> bool:
    if isinstance(allowed, Mapping):
        return allowed.get(name) == module
    return name in allowed


def foreign_functions(cls, module_name: str,
                      allowed: Mapping[str, str] | tuple[str, ...] = ()) -> list[str]:
    """Methods of ``cls`` defined in another module than ``module_name`` (a wrapper).

    Args:
        cls: The class to scan.
        module_name: The module the methods should come from.
        allowed: Method name -> the one module it may come from (rev5 2.2); a tuple of names
            allows those names from any module.
    """
    out = []
    for name, value in vars(cls).items():
        function = getattr(value, "__func__", value)
        module = getattr(function, "__module__", None)
        if callable(function) and module is not None and module != module_name \
                and not _is_allowed(name, module, allowed):
            out.append(f"{cls.__name__}.{name} from {module}")
    return out


def wrapper_problems(allowed: Mapping[str, str]) -> list[str]:
    """H-T3-0: a wrapper on the controller or config class of this process.

    Args:
        allowed: The foreign ``C2Config`` methods the bundle may carry
            (``ALLOWED_PRESET_PATCHES``); the controller class may carry none.
    """
    from outrigger_sim.control import c2

    problems = foreign_functions(c2.C2Controller, c2.__name__)
    problems += foreign_functions(c2.C2Config, c2.__name__, allowed)
    if lt._INSTALLED:
        problems.append("las_targeted wrapper installed")
    return problems


def fb_problems(config) -> list[str]:
    """H-T3-0: a flow budget (FB) block of the config that is on."""
    out = []
    for name in getattr(config, "__dataclass_fields__", {}):
        block = getattr(config, name, None)
        if FB_FIELD_TOKEN in name and bool(getattr(block, "enable", False)):
            out.append(f"config.{name}.enable is True")
    return out


def gate_problems(config, gate: str) -> list[str]:
    """Rev5 2.2: the config has the bundle's K1 order gate and R4c30 (``enable`` True,
    ``flat_soil_margin_m`` 0.03; a gate without R4c30 means nothing)."""
    margin = getattr(config, "slope_clearance_margin", None)
    if margin is None:
        return ["no slope_clearance_margin settings"]
    problems = []
    is_gate_on = bool(getattr(margin, GATE_FIELD, False))
    if is_gate_on != (gate == GATE_ON):
        problems.append(f"{GATE_SETTING_KEY} is {is_gate_on}, the bundle has the gate {gate}")
    if not margin.enable:
        problems.append("slope_clearance_margin.enable is False")
    if margin.flat_soil_margin_m != R4C30_MARGIN_M:
        problems.append(f"slope_clearance_margin.flat_soil_margin_m {margin.flat_soil_margin_m!r}"
                        f" != {R4C30_MARGIN_M}")
    return problems


def config_problems(config, las: str, gate: str | None) -> list[str]:
    """Why ``config`` is not the condition ``las`` / ``gate`` (``gate`` None: the ``rev4c``
    check, LAS-b only): LAS-b b0 (``on``) or LAS-b off (``off``), FB off, the gate state."""
    import fb_targeted

    settings = config.liftoff_approach_slow
    if las == LAS_OFF:
        problems = ["the controller has LAS-b on"] if settings.enable else []
    else:
        problems = fb_targeted.preset_las_problems(settings)
    problems += fb_problems(config)
    if gate is not None:
        problems += gate_problems(config, gate)
    return problems


def preset_problems(gate_expected: bool | None = None) -> list[str]:
    """H-T3-0: the preset of this process is not LAS-b b0, has FB on, or (``gate_expected``
    not None, rev5) has another K1 gate state or no R4c30."""
    from outrigger_sim.control import c2

    config = c2.C2Config().with_10hz_d1()
    gate = None if gate_expected is None else (GATE_ON if gate_expected else GATE_OFF)
    return config_problems(config, LAS_ON, gate)


def run_identity(commit: str, workers: int, affinity: str | None) -> dict:
    """The identity every line repeats (rev3 K-0)."""
    return {**lt.line_identity(commit, TOOL_FILES), "workers": workers, "affinity": affinity}


def required_seals(rules: str) -> tuple[str, ...]:
    return T3_REQUIRED_SEALS if rules == RULES_REV5 else REV4C_REQUIRED_SEALS


def dg3_r4c30_counts(entries: list[dict], stored_dir: Path = V5_DIR) -> dict[str, int | None]:
    """Rev5 2.5: ``INFO_LOC_FLAT_SOIL_MARGIN`` events of each stored Dg-3 T4h meta (line key ->
    count; None: the meta has no event list).

    Raises:
        OSError, KeyError, ValueError: A stored T4h file is missing or not of this form.
    """
    counts = {}
    for entry in entries:
        path = stored_dir / Path(*entry["t4h_file"].replace("\\", "/").split("/"))
        events = read_t4h_meta(path).get("events")
        counts[entry["line_key"]] = None if events is None else lt_counts(events).get(
            R4C30_EVENT, 0)
    return counts


def dg3_r4c30_problems(entries: dict[str, list[dict]], stored_dir: Path = V5_DIR) -> list[str]:
    """Rev5 2.5 (H-T3-0): a stored Dg-3 record of T-3b with R4c30 events or without events."""
    try:
        counts = dg3_r4c30_counts(entries["T-3b"], stored_dir)
    except (OSError, KeyError, ValueError) as exc:
        return [f"stored Dg-3 T4h not readable: {exc!r}"]
    return [f"stored Dg-3 {key}: {R4C30_EVENT} count {count} (rev5 2.5 needs 0)"
            for key, count in counts.items() if count != 0]


def preflight(out_dir: Path, rules: str = RULES_REV4C, stored_dir: Path = V5_DIR,
              entries: dict[str, list[dict]] | None = None) -> list[str]:
    """H-T3-0 problems before any run (empty = start).

    Args:
        out_dir: The output folder (no output may exist).
        rules: ``rev4c`` (the nine seals, LAS-b b0) or ``rev5`` (eleven seals, the gate on with
            R4c30, the R-0K key list, no R4c30 in the stored Dg-3 records).
        stored_dir: The v5 folder of the stored results (rev5 Dg-3 check).
        entries: The bundle entries (rev5: the R-0K list is checked against them).
    """
    problems = lt.seal_problems(RULES_DIR, required_seals(rules))
    try:
        problems += [f"tree change: {line}" for line in tree_changes()]
    except (OSError, subprocess.SubprocessError) as exc:
        problems.append(f"git status failed: {exc!r}")
    for path in output_paths(out_dir, rules):
        if path.exists():
            problems.append(f"output exists: {path}")
    problems += wrapper_problems(ALLOWED_PRESET_PATCHES["T-3a"])
    if rules != RULES_REV5:
        return problems + preset_problems()
    problems += preset_problems(gate_expected=True)
    if entries is not None:
        problems += r0k_key_problems(entries.get(R0K, []), entries)
        problems += dg3_r4c30_problems(entries, stored_dir)
    return problems


def output_paths(out_dir: Path, rules: str = RULES_REV4C) -> list[Path]:
    names = [R0_FILE, T3_FILE, REPORT_FILE, JUDGE_FILE, DG3_FOLDER]
    if rules == RULES_REV5:
        names.insert(1, R0K_FILE)
    return [out_dir / name for name in names]


RULES_TEXT = {RULES_REV4C: "las_targeted_rules_rev3.md 2 .. 4, rev4 1 #1",
              RULES_REV5: "las_targeted_rules_rev5.md 2 .. 4 (rev3 2 .. 4, rev4 1 #1, rev4a)"}


def header_record(identity: dict, out_dir: Path, bundles: tuple[str, ...],
                  rules: str = RULES_REV4C) -> dict:
    header = {
        "tool": "las_t3.py", "rules": RULES_TEXT[rules],
        "identity": identity, "bundles": list(bundles),
        "expected_counts": {name: expected_count(name) for name in bundles},
        "seals": {name: lt.SEALS[name].sha256 for name in required_seals(rules)},
        "interpreter": sys.executable, "out_dir": repo_path(out_dir),
        "started": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}
    if rules == RULES_REV5:
        header["rules_mode"] = rules
        header["conditions"] = {name: {"las": LAS_OFF if name in (R0, R0K) else LAS_ON,
                                       "gate": BUNDLE_GATE[name]} for name in bundles}
    return {"header": header}


def repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


# ------------------------------------------------------------------------------- D-1 worker
_CAPTURE: dict = {}


def capture_d1_record() -> None:
    """Keep the plant, controller and harness record of the run (record only: the arguments
    and the return value pass through unchanged)."""
    import d1_runs

    original = d1_runs.d1_record

    def d1_record(row, setting_name, eps, result, plant, controller, harness):
        _CAPTURE.update(controller=controller, harness=harness)
        return original(row, setting_name, eps, result, plant, controller, harness)

    d1_runs.d1_record = d1_record


def turn_preset_las_off() -> None:
    """The switch of ``pre_las_preset_runner.py`` (that file, executed as a module)."""
    spec = importlib.util.spec_from_file_location("pre_las_preset_runner", PRE_LAS_RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


def las_events(controller) -> list[list]:
    return [[float(event.t_s), event.name] for event in controller.events
            if event.name.startswith(LAS_EVENT_PREFIX)]


def k1_record(order_gate: dict | None) -> dict:
    """Rev5 ``las_t3.k1`` from the controller meta ``slope_clearance_margin.order_gate``: the
    gate state, the decisions as recorded (kept with the gate off too: a shadow record) and
    what the judge reads of them. ``enabled`` None: the meta has no order-gate record."""
    if order_gate is None:
        return {"enabled": None, "decisions": None, "would_block_any": None,
                "applied_any": None, "applied_count": None, "first_dP": None,
                "blocked_t_loc_s": None}
    decisions = list(order_gate.get("decisions") or [])
    return {"enabled": order_gate.get("enabled"), "decisions": decisions,
            "would_block_any": any(bool(d.get("would_block")) for d in decisions),
            "applied_any": any(bool(d.get("applied")) for d in decisions),
            "applied_count": sum(bool(d.get("applied")) for d in decisions),
            "first_dP": decisions[0].get("dP") if decisions else None,
            "blocked_t_loc_s": [d.get("t_loc_s") for d in decisions if d.get("would_block")]}


def las_record(controller, harness: dict | None, with_k1: bool = False) -> dict:
    """``las_t3`` of a D-1 run: LAS-b events, the meta, the judge's LOC - t_off; with
    ``with_k1`` (rev5) the K1 block :func:`k1_record`."""
    all_meta = controller.meta()
    meta = all_meta.get("liftoff_approach_slow") or {}
    events = las_events(controller)
    record = {"enable": bool(controller.config.liftoff_approach_slow.enable),
              "fired": las_h7.is_fired(events), "events": events,
              **{key: value for key, value in meta.items() if key != "settings"},
              "settings": meta.get("settings"), **lt.loc_delay_record(harness)}
    if with_k1:
        margin = all_meta.get("slope_clearance_margin") or {}
        record["k1"] = k1_record(margin.get("order_gate"))
    return record


def controller_problems(controller, las: str, gate: str | None = None) -> list[str]:
    """The run's controller is LAS-b b0 (T-3) or has LAS-b off (R-0, R-0K); with ``gate``
    (rev5) also the bundle's K1 gate state, R4c30 and FB off."""
    import fb_targeted

    if gate is not None:
        return config_problems(controller.config, las, gate)
    settings = controller.config.liftoff_approach_slow
    if las == LAS_OFF:
        return ["the R-0 controller has LAS-b on"] if settings.enable else []
    return fb_targeted.preset_las_problems(settings) + fb_problems(controller.config)


def _error_line(job: dict, t3: dict, message: str, t_start: float) -> dict:
    return {"job": job, "t3": t3, "error": message,
            "wall_s": round(time.perf_counter() - t_start, 1)}


def switch_preset(bundle: str) -> None:
    """The bundle's preset switch in this worker (rev5 2.2): R-0 ``pre_las_preset_runner``
    (LAS-b and gate off), R-0K ``las_t3_presets`` (LAS-b off, gate as the preset), T-3 none."""
    if bundle == R0:
        turn_preset_las_off()
    elif bundle == R0K:
        import las_t3_presets

        las_t3_presets.install_las_off_gate_on()


def is_rev5(t3: dict) -> bool:
    return t3.get("rules") == RULES_REV5


def run_d1_job(job: dict, t3: dict, t_start: float) -> dict:
    """One D-1 line (module docstring)."""
    import run_v5  # sys.path and thread variables first

    switch_preset(t3["bundle"])
    problems = wrapper_problems(ALLOWED_PRESET_PATCHES[t3["bundle"]])
    problems += lt.thread_problems(lt.thread_values())
    if problems:
        return _error_line(job, t3, f"refused: {problems}", t_start)
    capture_d1_record()
    line = run_v5.run_one(job)
    controller = _CAPTURE.get("controller")
    if "error" in line:
        return {**line, "t3": t3}
    if controller is None:
        return _error_line(job, t3, "no controller captured", t_start)
    gate = t3["gate"] if is_rev5(t3) else None
    problems = controller_problems(controller, t3["las"], gate)
    if problems:
        return _error_line(job, t3, f"controller: {problems}", t_start)
    record = las_record(controller, _CAPTURE.get("harness"), with_k1=is_rev5(t3))
    return {**line, "t3": t3, "las_t3": record}


# ------------------------------------------------------------------------------- Dg-3 worker
def safe_name(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text)


def stored_dg3_record(entry: dict, stored_dir: Path = V5_DIR) -> tuple[dict, dict]:
    """(stored result meta, stored record) of a Dg-3 entry (``result_file`` is relative to the
    v5 folder, Windows separators as the key list wrote it)."""
    path = stored_dir / Path(*entry["result_file"].replace("\\", "/").split("/"))
    stored = json.loads(path.read_text(encoding="utf-8"))
    record = next(r for r in stored["results"] if r["key"] == entry["key"])
    return stored["meta"], record


def dg3_command(entry: dict, out_json: Path, affinity: str | None,
                stored_dir: Path = V5_DIR) -> tuple[list[str], dict]:
    """(argv, environment) of one Dg-3 record with the stored meta's arguments."""
    meta, record = stored_dg3_record(entry, stored_dir)
    plain_key = entry["key"].split("#", 1)[1]
    argv = [sys.executable, "-I", "-B", str(DG3_RUNNER), str(ROOT), "run", str(out_json),
            "--levels", meta["levels"], "--keys", plain_key, "--workers", "1"]
    if affinity:
        argv += ["--affinity", affinity]
    env = {"R79_V5_SETTING": record["v5_setting"], "R72_PATH": meta["r72_path"],
           "R79_ROD_MODEL": meta["rod_model"], "R79_T4H_DIR": str(out_json.parent / "t4h")}
    return argv, env


def read_t4h_meta(path: Path) -> dict:
    import numpy as np

    with np.load(path, allow_pickle=False) as data:
        return json.loads(str(data["meta_json"]))


def dg3_line(job: dict, t3: dict, record: dict, t4h_path: Path, folder: Path) -> dict:
    meta = read_t4h_meta(t4h_path)
    events = meta.get("events")
    settings = record.get("controller_settings") or {}
    las_events_ = [list(event) for event in events or []
                   if str(event[1]).startswith(LAS_EVENT_PREFIX)]
    base = record.get("base") or {}
    return {"job": job, "t3": t3, "commands_sha256": meta.get("commands_sha256"),
            "controller_tag": meta.get("controller_tag"),
            "event_names": None if events is None else lt_counts(events),
            "extend_start_rule": settings.get("two_pressure.extend_start_rule"),
            "las_enable": settings.get("liftoff_approach_slow.enable"),
            "base_pass": base.get("pass"), "G6-2_loc": (base.get("gates") or {}).get("G6-2_loc"),
            "hydraulic_options": record.get("hydraulic_options"),
            "controller_settings": settings, "v5_setting": record.get("v5_setting"),
            "las_t3": {"enable": settings.get("liftoff_approach_slow.enable"),
                       "fired": las_h7.is_fired(las_events_), "events": las_events_,
                       "loc_minus_t_off_s": base.get("loc_delay_s")},
            "wall_s": record.get("wall_s"), "r79_dir": repo_path(folder),
            "t4h_file": repo_path(t4h_path)}


def lt_counts(events) -> dict[str, int]:
    """Event-name counts with the head before ``:`` (``run_m1.event_names``)."""
    counts: dict[str, int] = {}
    for _, name in events:
        head = str(name).split(":")[0]
        counts[head] = counts.get(head, 0) + 1
    return counts


def run_dg3_job(job: dict, t3: dict, t_start: float) -> dict:
    """One Dg-3 line: ``las_t3_dg3.py`` in a subprocess into its own new folder."""
    entry = job["entry"]
    folder = Path(job["folder_dir"])
    folder.mkdir(parents=True, exist_ok=False)
    out_json = folder / "r79.json"
    argv, env = dg3_command(entry, out_json, job.get("affinity"), Path(job["stored_dir"]))
    full_env = {**os.environ, **env, "LAS_T3_DG3_LAS": t3["las"],
                "LAS_T3_DG3_P3": DG3_P3_OF_FOLDER[entry["folder"]],
                "LAS_T3_DG3_K1": t3["gate"]}
    with (folder / "run.log").open("x", encoding="utf-8") as log:
        completed = subprocess.run(argv, cwd=str(ROOT), env=full_env, stdout=log,
                                   stderr=subprocess.STDOUT, timeout=DG3_TIMEOUT_S, check=False)
    if completed.returncode != 0 or not out_json.exists():
        return _error_line(job, t3, f"las_t3_dg3 exit {completed.returncode} "
                           f"(log {repo_path(folder / 'run.log')})", t_start)
    record = json.loads(out_json.read_text(encoding="utf-8"))["results"][0]
    if "error" in record or not record.get("t4h_file"):
        return _error_line(job, t3, f"r79: {record.get('error', 'no T4h record')}", t_start)
    return dg3_line(job, t3, record, folder / "t4h" / record["t4h_file"], folder)


# ------------------------------------------------------------------------------- worker entry
def run_t3_job(job: dict) -> dict:
    """Worker: one line of any bundle; never raises (an error becomes an error line)."""
    t_start = time.perf_counter()
    t3 = job.pop("t3")
    try:
        t3["identity"] = run_identity(t3["commit"], t3["workers"], t3["affinity_hex"])
        if t3["kind"] == KIND_D1:
            line = run_d1_job(job, t3, t_start)
        else:
            line = run_dg3_job(job, t3, t_start)
    except Exception as exc:  # the batch goes on; the line records the failure
        return _error_line(job, t3, f"{exc!r} {traceback.format_exc()[-1500:]}", t_start)
    line.setdefault("wall_s", round(time.perf_counter() - t_start, 1))
    return line


def build_jobs(entries: list[dict], bundle: str, commit: str, workers: int,
               affinity: str | None, out_dir: Path, stored_dir: Path = V5_DIR,
               attempt: int = 1, rules: str = RULES_REV4C) -> list[dict]:
    """Worker jobs of a bundle's entries (VB first: the longer runs start early).

    Each job's ``t3`` carries the bundle condition: ``las`` off for R-0 and R-0K, on for T-3;
    ``gate`` (``BUNDLE_GATE``) off for R-0, on otherwise; ``rules`` the mode (the worker checks
    the gate in ``rev5`` only).
    """
    mask = None if affinity is None else int(affinity, 16)
    las = LAS_OFF if bundle in (R0, R0K) else LAS_ON
    d1 = d1_jobs([e["line_key"] for e in entries if e["kind"] == KIND_D1])
    jobs = []
    for entry in entries:
        t3 = {"bundle": bundle, "line_key": entry["line_key"], "kind": entry["kind"],
              "las": las, "gate": BUNDLE_GATE[bundle], "rules": rules, "attempt": attempt,
              "commit": commit, "workers": workers, "affinity_hex": affinity}
        if entry["kind"] == KIND_D1:
            jobs.append({**d1[entry["line_key"]], "mask": mask, "t3": t3})
            continue
        name = f"{bundle}_{entry['folder']}_{safe_name(entry['key'])}_a{attempt}"
        jobs.append({"kind": KIND_DG3, "entry": entry, "affinity": affinity,
                     "folder_dir": str(out_dir / DG3_FOLDER / name),
                     "stored_dir": str(stored_dir), "t3": t3})
    return sorted(jobs, key=lambda job: job.get("setting") != "VB")


def _json_default(value):
    return value.item() if hasattr(value, "item") else str(value)


def _print_line(count: int, total: int, line: dict) -> None:
    t3 = line.get("t3") or {}
    if "error" in line:
        state = f"ERROR {str(line['error'])[:200]}"
    else:
        las = line.get("las_t3") or {}
        d1 = line.get("d1") or {}
        state = (f"{d1.get('verdict', line.get('base_pass'))} "
                 f"{str(line.get('commands_sha256'))[:12]} fired {las.get('fired')} "
                 f"tag {line.get('controller_tag')} {line.get('wall_s')} s")
    print(f"{count}/{total} {t3.get('bundle')} {t3.get('line_key')} a{t3.get('attempt')}: "
          f"{state}", flush=True)


def run_pool(jobs: list[dict], handle, workers: int) -> list[dict]:
    """Run ``jobs`` (one spawned process each), write every line; returns the lines."""
    lines = []
    if not jobs:
        return lines
    with get_context("spawn").Pool(min(workers, len(jobs)), maxtasksperchild=1) as pool:
        for count, line in enumerate(pool.imap_unordered(run_t3_job, jobs), 1):
            line.get("job", {}).pop("mask", None)
            handle.write(json.dumps(line, default=_json_default) + "\n")
            handle.flush()
            _print_line(count, len(jobs), line)
            lines.append(line)
    return lines


def run_bundles(bundles: list[tuple[str, list[dict]]], path: Path, header: dict,
                options: dict) -> list[dict]:
    """Run bundles into the new file ``path``; every error line is retried once (H-T3-2).

    Raises:
        FileExistsError: ``path`` is there (before any run: no resume, no overwrite).
    """
    lines = []
    with path.open("x", encoding="utf-8") as handle:
        import verdict_runs

        handle.write(json.dumps(header, default=_json_default) + "\n")
        handle.flush()
        verdict_runs.warm_numba_cache()
        jobs = []
        for bundle, entries in bundles:
            jobs += build_jobs(entries, bundle, **options)
        lines += run_pool(jobs, handle, options["workers"])
        retry = []
        by_bundle = dict(bundles)
        for line in lines:
            if "error" in line:
                t3 = line["t3"]
                entry = next(e for e in by_bundle[t3["bundle"]]
                             if e["line_key"] == t3["line_key"])
                retry += build_jobs([entry], t3["bundle"], **{**options, "attempt": 2})
        lines += run_pool(retry, handle, options["workers"])
    return lines


# ------------------------------------------------------------------------------- CLI
def select_keys(entries: dict[str, list[dict]], keys: list[str] | None) -> dict:
    if not keys:
        return entries
    wanted = set(keys)
    picked = {bundle: [e for e in group if e["line_key"] in wanted]
              for bundle, group in entries.items()}
    unknown = wanted - {e["line_key"] for group in picked.values() for e in group}
    if unknown:
        raise KeyError(f"keys not in the key list: {sorted(unknown)[:3]}")
    return picked


def list_bundles(entries: dict[str, list[dict]]) -> int:
    problems = count_problems(entries)
    if R0K in entries:
        problems += r0k_key_problems(entries[R0K], entries)
    for bundle, group in entries.items():
        wall_s = sum(float(e.get("wall_s") or 0.0) for e in group)
        print(f"{bundle}: {len(group)} lines (expected {expected_count(bundle)}), "
              f"stored wall {wall_s:.0f} s")
    for problem in problems:
        print(f"MISMATCH {problem}")
    print(json.dumps({"command": "list", "counts": {b: len(g) for b, g in entries.items()},
                      "problems": problems}))
    return 1 if problems else 0


ONLY_CHOICES = (R0, R0K)


def _parse_args(argv: list[str] | None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("list", help="bundle counts of the sealed key lists")
    listing.add_argument("--rules", choices=RULES_MODES, default=RULES_REV5)
    run = sub.add_parser("run", help="R-0, (rev5: R-0K,) then T-3 (each run once; no resume)")
    run.add_argument("--rules", choices=RULES_MODES, default=RULES_REV5,
                     help="sealed rules mode (rev5: T-3K under the K1 preset; rev4c: rev3 T-3)")
    run.add_argument("--workers", type=int, required=True)
    run.add_argument("--affinity", default=None, help="hex mask of every worker, e.g. 0x0FF")
    run.add_argument("--only", choices=ONLY_CHOICES, default=None,
                     help="R-0 alone, or (rev5) R-0 then R-0K; no T-3 (smoke)")
    run.add_argument("--keys", default=None, help="comma-separated line keys (smoke)")
    run.add_argument("--out-dir", type=Path, default=None,
                     help=f"default {repo_path(OUT_DIR_REV5)} (rev5), {repo_path(OUT_DIR)} (rev4c)")
    run.add_argument("--stored-dir", type=Path, default=V5_DIR,
                     help="v5 folder with the stored d1.jsonl and Dg-3 results (read only)")
    args = parser.parse_args(argv)
    if args.command == "run":
        if args.out_dir is None:
            args.out_dir = OUT_DIR_REV5 if args.rules == RULES_REV5 else OUT_DIR
        if args.only == R0K and args.rules != RULES_REV5:
            parser.error("--only R-0K needs --rules rev5")
    return args


def _prepare_run(args, entries: dict[str, list[dict]]) -> tuple[dict | None, str | None, int]:
    """(selected entries, commit, 0) or (None, None, exit code) after the H-T3-0 checks."""
    try:
        problems = count_problems(entries) + preflight(args.out_dir, args.rules,
                                                       args.stored_dir, entries)
        if problems:
            print(json.dumps({"command": "run", "stop": "H-T3-0", "problems": problems}))
            return None, None, 2
        selected = select_keys(entries, args.keys.split(",") if args.keys else None)
        if args.affinity is not None:
            int(args.affinity, 16)
        commit = git_output("rev-parse", "HEAD").strip()
    except (OSError, KeyError, ValueError, subprocess.SubprocessError) as exc:
        print(json.dumps({"command": "run", "error": repr(exc)}))
        return None, None, 2
    return selected, commit, 0


def _stage_header(identity: dict, args, bundles: tuple[str, ...]) -> dict:
    header = header_record(identity, args.out_dir, bundles, args.rules)
    header["header"]["keys_subset"] = bool(args.keys)
    return header


def _run_gate_stage(stage: str, file_name: str, entries: dict[str, list[dict]], args,
                    identity: dict, options: dict) -> dict:
    """Run R-0 or R-0K into its file and return its gate (``las_t3_judge``)."""
    import las_t3_judge

    lines = run_bundles([(stage, entries[stage])], args.out_dir / file_name,
                        _stage_header(identity, args, (stage,)), options)
    baseline_path = args.stored_dir / "d1.jsonl"
    if stage == R0:
        gate = las_t3_judge.r0_gate(lines, entries[R0], baseline_path, rules=args.rules)
    else:
        gate = las_t3_judge.r0k_gate(lines, entries[R0K], baseline_path)
    print(json.dumps({"stage": stage, "keys_subset": bool(args.keys), **gate}, default=str),
          flush=True)
    return gate


def _judge_argv(args) -> list[str]:
    argv = ["--stage", "T-3", str(args.out_dir / T3_FILE), "--r0", str(args.out_dir / R0_FILE),
            "--baseline", str(args.stored_dir / "d1.jsonl"),
            "--out", str(args.out_dir / REPORT_FILE),
            "--json-out", str(args.out_dir / JUDGE_FILE)]
    if args.rules == RULES_REV5:
        argv += ["--t3-rules", RULES_REV5, "--r0k", str(args.out_dir / R0K_FILE)]
    else:
        argv += ["--t3-rules", RULES_REV4C]
    return argv


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        entries = rules_entries(args.rules)
    except (OSError, KeyError, ValueError) as exc:
        print(json.dumps({"command": args.command, "error": repr(exc)}))
        return 2
    if args.command == "list":
        return list_bundles(entries)
    entries, commit, code = _prepare_run(args, entries)
    if entries is None:
        return code
    import las_judge
    import las_t3_judge

    identity = run_identity(commit, args.workers, args.affinity)
    options = {"commit": commit, "workers": args.workers, "affinity": args.affinity,
               "out_dir": args.out_dir, "stored_dir": args.stored_dir, "rules": args.rules}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    gate = _run_gate_stage(R0, R0_FILE, entries, args, identity, options)
    if gate["stop"] or args.only == R0:
        return 2 if gate["stop"] else 0
    if args.rules == RULES_REV5:
        gate = _run_gate_stage(R0K, R0K_FILE, entries, args, identity, options)
        if gate["stop"]:
            return las_t3_judge.stop_exit_code(gate["stop"])
        if args.only == R0K:
            return 0
    run_bundles([(bundle, entries[bundle]) for bundle in T3_BUNDLES], args.out_dir / T3_FILE,
                _stage_header(identity, args, T3_BUNDLES), options)
    return las_judge.main(_judge_argv(args))


if __name__ == "__main__":
    sys.exit(main())
