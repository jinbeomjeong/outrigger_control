"""P-S9-9 (spec rev. 57 285): the s9 case sets with the project soil response instead of SoilC2.

The reduced closed loop of ``s9_soil_closed_loop.py`` and the case lists of ``s9_runs.py`` are
used unchanged; only the controller factory is replaced (environment variable ``S9_CTRL``, read
in every pool worker):

  ref     the original factory: project C2 for "base", ``s9_soil_rules.SoilC2`` for rule cases
  proj    project C2 for every case: "base" with ``C2Config.soil`` explicitly off, rule cases
          with ``SoilResponseSettings(enable=True, ...)`` from the rule keys (``S9_RULE``)
  preset  the harness preset as it is (``with_10hz_d1``) for every case, no override

Commands:
  python -I s9_project_check.py run <set> <out_json> [workers]   (set: rigid soil sensor beta)
  python -I s9_project_check.py compare <out_json> <ref_json> [<ref_json> ...]

``compare`` matches runs by id; a run whose id has no reference is matched to the same case of
the other variant ("base|" <-> "loc|"), because the rigid references hold the soil-rule runs
only (they equal the base runs bit for bit, spec rev. 57 281). It prints the number of equal
command SHA-256 values and the first differing ids. Units SI. Run in dynamics-dev or Chrono-dev
(numba); the outputs go where ``<out_json>`` points (keep them out of the project tree when
only checking).
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
MAIN_TREE_ROOT = Path(r"C:\workspace\outrigger_control")
"""``r8d1/r8d1_td.py`` inserts this absolute path; in a git worktree it would mix in the main
tree's scripts (and through ``dyn_model`` its YAML)."""


class _ProjectLocalPath(list):
    """``sys.path`` that maps the hard-coded main-tree script paths onto this checkout."""

    def insert(self, index, value):
        super().insert(index, _project_local(value))

    def append(self, value):
        super().append(_project_local(value))


def _project_local(entry):
    path = Path(str(entry))
    if PROJECT_ROOT == MAIN_TREE_ROOT or not path.is_relative_to(MAIN_TREE_ROOT):
        return entry
    if path.is_relative_to(MAIN_TREE_ROOT / ".claude"):
        return entry
    return str(PROJECT_ROOT / path.relative_to(MAIN_TREE_ROOT))


sys.path = _ProjectLocalPath(sys.path)
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import s9_runs  # noqa: E402
import s9_soil_closed_loop as harness  # noqa: E402
import s9_soil_rules  # noqa: E402

CONTROLLER_MODES = ("ref", "proj", "preset")
RULE_TO_SETTINGS = {
    "win_m": "plateau_window_m",
    "ext_min_frac": "plateau_mean_speed_fraction",
    "dF_thr_N": "plateau_rise_max_N",
    "rho": "plausibility_fraction",
    "push_frac": "push_speed_fraction",
    "bias_min_m": "corner_bias_deadzone_m",
    "max_push_m": "max_push_m",
    "settle_samples": "settle_tilt_samples",
}
"""Reference rule keys (``s9_soil_rules.DEFAULTS``) -> ``SoilResponseSettings`` fields."""
FIXED_RULE_VALUES = {
    "recontact_N": None,
    "window_mode": "no_retract",
    "bias_mode": "corner_imu",
    "max_window_samples": 200,
}
"""Reference options the project implements only in this form (spec rev. 57 282.4)."""
RISE_LOG_LENGTH = 400
"""As ``SoilC2.soil_meta``: the harness takes the pinned-window margin from these entries."""

_reference_make_controller = harness.make_controller


def soil_settings_from_rule(c2, rule: dict):
    """``SoilResponseSettings`` (on) of a reference rule dict (defaults filled in)."""
    full_rule = {**s9_soil_rules.DEFAULTS, **rule}
    for key, value in FIXED_RULE_VALUES.items():
        if full_rule[key] != value:
            raise ValueError(f"rule {key}={full_rule[key]!r} is not implemented (only {value!r})")
    values = {field: full_rule[key] for key, field in RULE_TO_SETTINGS.items()}
    return c2.SoilResponseSettings(enable=True, **values)


def _attach_reference_meta(controller) -> None:
    """Give the project controller the ``soil_meta`` the harness records for SoilC2 runs."""
    rise_log = []
    compute_rise = controller._plateau_rise_N

    def logged_rise(tail):
        rise_N = compute_rise(tail)
        mean_load_N = float(sum(sample.load_sum_N for sample in tail) / len(tail))
        t_s = controller._state.last_reading.t_s
        rise_log.append((round(float(t_s), 2), round(rise_N, 1), round(mean_load_N, 1)))
        return rise_N

    def soil_meta():
        soil = controller.meta()["soil"]
        bias = soil.get("bias_corner_m") or [0.0] * 4
        return {
            "loc": soil.get("loc"),
            "t_loc_s": soil.get("t_loc_s"),
            "t_P_s": soil.get("t_P_s"),
            "W_hat_N": soil.get("W_hat_N"),
            "soil_mode_entered": soil.get("soil_mode_t_s"),
            "bias_corner_mm": [round(value * 1e3, 2) for value in bias],
            "project_soil_meta": soil,
            "rise_log": rise_log[:RISE_LOG_LENGTH],
        }

    controller._plateau_rise_N = logged_rise
    controller.soil_meta = soil_meta


def _check_no_main_tree_modules() -> None:
    if PROJECT_ROOT == MAIN_TREE_ROOT:
        return
    for name, module in list(sys.modules.items()):
        module_file = getattr(module, "__file__", None)
        if not module_file:
            continue
        path = Path(module_file)
        if path.is_relative_to(MAIN_TREE_ROOT) and not path.is_relative_to(PROJECT_ROOT):
            raise RuntimeError(f"module {name} imported from the main tree: {module_file}")


def project_make_controller(cl, c2, variant: dict):
    """Controller factory of the selected ``S9_CTRL`` mode (runs inside the pool workers)."""
    _check_no_main_tree_modules()
    mode = os.environ.get("S9_CTRL", "ref")
    if mode == "ref":
        return _reference_make_controller(cl, c2, variant)
    config = cl.preset_config(c2.ContactJudge.COMBINED, with_imu_samples=True, with_reapproach=True)
    rule = variant.get("rule")
    if mode == "proj":
        soil = c2.SoilResponseSettings() if rule is None else soil_settings_from_rule(c2, rule)
        config = replace(config, soil=soil)
    controller = c2.C2Controller.from_params(cl.PARAMS, config)
    controller.reset()
    if config.soil.enable:
        _attach_reference_meta(controller)
    return controller


# Module level on purpose: spawned pool workers import this module as __mp_main__ and must see
# the replaced factory before they run their first case.
harness.make_controller = project_make_controller


def run(case_set: str, out_path: Path, workers: int) -> None:
    mode = os.environ.get("S9_CTRL", "ref")
    if mode not in CONTROLLER_MODES:
        raise SystemExit(f"S9_CTRL must be one of {CONTROLLER_MODES}, got {mode!r}")
    builders = {
        "rigid": s9_runs.rigid_cases,
        "soil": s9_runs.soil_cases,
        "sensor": s9_runs.sensor_cases,
        "beta": s9_runs.beta_cases,
    }
    cases = builders[case_set]()
    case_filter = os.environ.get("S9_FILTER")
    if case_filter:
        cases = [
            case for case in cases if all(part in case["id"] for part in case_filter.split("&"))
        ]
    meta = {"set": case_set, "rule": s9_runs.RULE, "n_cases": len(cases), "controller": mode}
    result = harness.run_batch(cases, out_path, workers, meta=meta)
    errors = sum(1 for run_record in result["runs"] if "error" in run_record)
    print("done", out_path, result["meta"]["wall_s"], "s", errors, "errors")


def _other_variant_id(run_id: str) -> str | None:
    variant, _, rest = run_id.partition("|")
    if variant.startswith("base"):
        return "loc" + variant.removeprefix("base") + "|" + rest
    if variant.startswith("loc"):
        return "base" + variant.removeprefix("loc") + "|" + rest
    return None


PROJECT_ONLY_EVENT_PREFIXES = ("INFO_CLEARANCE_BIAS", "WARN_WEIGHT_MISMATCH")
"""Events of spec rev. 57 P-S9-7 the reference rules do not raise."""
SOIL_META_KEYS = ("loc", "t_loc_s", "t_P_s", "W_hat_N", "soil_mode_entered", "bias_corner_mm")


def _comparable_events(run_record: dict) -> list[str]:
    return [
        event
        for event in run_record.get("events", [])
        if not event.split(" ", 1)[-1].startswith(PROJECT_ONLY_EVENT_PREFIXES)
    ]


def _soil_meta_differences(run_record: dict, reference_record: dict) -> list[str]:
    own = run_record.get("soil_rule_meta")
    expected = reference_record.get("soil_rule_meta")
    if own is None and expected is None:
        return []
    if own is None or expected is None:
        return ["soil_rule_meta presence"]
    return [key for key in SOIL_META_KEYS if own.get(key) != expected.get(key)]


def compare(out_path: Path, reference_paths: list[Path]) -> int:
    """Command hashes, events (without the project-only ones) and the LOC record per run."""
    reference = {}
    for path in reference_paths:
        for run_record in json.loads(path.read_text(encoding="utf-8"))["runs"]:
            reference.setdefault(run_record["id"], run_record)
    runs = json.loads(out_path.read_text(encoding="utf-8"))["runs"]
    equal, different, missing, event_diffs, meta_diffs = 0, [], [], [], []
    for run_record in runs:
        run_id = run_record["id"]
        expected = reference.get(run_id)
        is_same_variant = expected is not None
        if expected is None:
            expected = reference.get(_other_variant_id(run_id) or "")
        if expected is None:
            missing.append(run_id)
            continue
        if expected.get("commands_sha256") == run_record.get("commands_sha256"):
            equal += 1
        else:
            different.append(run_id)
        if not is_same_variant:
            continue  # events and the LOC record differ between the variants by design
        if _comparable_events(run_record) != _comparable_events(expected):
            event_diffs.append(run_id)
        meta_keys = _soil_meta_differences(run_record, expected)
        if meta_keys:
            meta_diffs.append((run_id, meta_keys))
    print(
        f"{out_path.name}: {equal} / {len(runs)} command hashes equal, {len(different)} "
        f"different, {len(missing)} without reference; events differ {len(event_diffs)}, "
        f"LOC record differs {len(meta_diffs)}"
    )
    for run_id in different[:20]:
        print("  different:", run_id)
    for run_id in missing[:20]:
        print("  no reference:", run_id)
    for run_id in event_diffs[:10]:
        print("  events differ:", run_id)
    for run_id, keys in meta_diffs[:10]:
        print("  LOC record differs:", run_id, keys)
    is_equal = not (different or missing or event_diffs or meta_diffs)
    return 0 if is_equal else 1


def main() -> None:
    command = sys.argv[1]
    if command == "run":
        workers = int(sys.argv[4]) if len(sys.argv) > 4 else 6
        run(sys.argv[2], Path(sys.argv[3]), workers)
    elif command == "compare":
        raise SystemExit(compare(Path(sys.argv[2]), [Path(arg) for arg in sys.argv[3:]]))
    else:
        raise SystemExit(f"unknown command {command!r} (run | compare)")


if __name__ == "__main__":
    main()
