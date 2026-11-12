"""Ground-family table of the 436.8 harness keys (rules ``v5_resume_4368_rules_rev1.md`` RV1-6).

Every job key of H-1, H-3, H-4 and H-6 .. H-10 gets one family, read from the ground the runner
builds for that key (base soil, weak-patch soil and leg, prescribed sink), not from the key text:

  강체           rigid base, no patch, no prescribed sink
  패치·처방 침하   a weak patch on one pad or a prescribed floor / soil sink (any base)
  균일 연약        a soil base (SCM soil set) without patch or prescribed sink
  해당 없음        the run has no C2 configuration (U-6 IND / IND_LAS; RV1-6 덧붙임)

Ground sources per runner (each the runner's own case definition):
  run_v5 d1 jobs         ``d1_rows.D1Row`` (``base``, ``patch_soil`` / ``patch_leg``, ``sink``)
  run_v5 verdict jobs    ``verdict_cases.resolve_case``: ``SteadyTwin.soil`` (s9_soil_slope run)
                         or ``EventTwin`` (r67 floor event on a leg of the rigid r51 floor)
  U-3 slope-like suites  the ``s9_soil_slope`` case dict ``soil`` (``s9_slope_fix_candidates``)
  U-3 p3b                the ``s9_runs`` case dict ``soil``
  U-3 g6 / C, r79 g6/ref ``r72_g6_screen.parse_soil`` of the soil field the runner passes on
  U-3 g8, r79 g8         ``r69_g8_screen`` rigid floor (a pad floor offset, no soil)
  U-3 D                  ``s9_soil_slope`` H8 case ``soil`` (a start gap is no soil patch)
  U-6                    ``b5_baseline_compare.case_spec`` (slope src soil, g6 src soil, floor-drop
                         ``event`` = prescribed sink on the rigid floor)
  H-9 grid               ``r67_g1_screen`` screen job: floor event on the rigid r51 floor
A key the table cannot place is written with family ``미분류``; the judge treats it as 균일 연약
(RV1-6: a K1 block there is S-6). The table is the input of ``resume4368_judge.py k1-class
--family-table``; its sha256 goes to ``<out>.sha256`` and must be recorded before the first main
run (RV1-6). It reads case definitions and stored key lists only; it never starts a run.

Usage (dynamics-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/resume_k1_family.py <out.json>
      [--data-root <checkout with the stored v5 files>]
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import sys
from collections import Counter
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
S8_DIR = ROOT / "04_scripts" / "03_control" / "s8"
S9_DIR = ROOT / "04_scripts" / "03_control" / "s9"
for _path in (HERE, S8_DIR, S9_DIR, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import resume_k1_steps as steps  # noqa: E402
import run_v5  # noqa: E402

FAMILY_RIGID = "강체"
FAMILY_PATCH_OR_SINK = "패치·처방 침하"
FAMILY_UNIFORM = "균일 연약"
FAMILY_NOT_APPLICABLE = "해당 없음"
FAMILY_UNRESOLVED = "미분류"
FAMILIES = (
    FAMILY_RIGID,
    FAMILY_PATCH_OR_SINK,
    FAMILY_UNIFORM,
    FAMILY_NOT_APPLICABLE,
    FAMILY_UNRESOLVED,
)
RIGID = "rigid"
NOT_APPLICABLE_CONTROLLERS = ("IND", "IND_LAS")
U6_CONTROLLERS = ("C2", "ABL", "IND", "IND_LAS")
RULES_REV1 = "v5_resume_4368_rules_rev1.md"


@dataclass(frozen=True)
class Ground:
    """The ground a runner builds for one key."""

    base: str | None
    patch_soil: str | None = None
    patch_leg: str | None = None
    sink: str | None = None
    note: str = ""


def family_of(ground: Ground | None) -> str:
    """RV1-6 family of a ground (:data:`FAMILY_UNRESOLVED` without one)."""
    if ground is None or ground.base is None:
        return FAMILY_UNRESOLVED
    if ground.patch_soil is not None or ground.sink is not None:
        return FAMILY_PATCH_OR_SINK
    return FAMILY_RIGID if ground.base == RIGID else FAMILY_UNIFORM


@contextlib.contextmanager
def _argv_as_root() -> Iterator[None]:
    """``r72_g6_screen`` reads the project root from ``sys.argv[1]`` at import."""
    saved = sys.argv
    sys.argv = [saved[0] if saved else "", str(ROOT)]
    try:
        yield
    finally:
        sys.argv = saved


def _r72():
    with _argv_as_root():
        import r72_g6_screen

    return r72_g6_screen


def g6_soil_ground(soil: str, note: str) -> Ground:
    """``r72_g6_screen.parse_soil``: ``<base>`` or ``<base>+<weak>@<leg>``."""
    base, per_leg = _r72().parse_soil(soil)
    weak = [(leg, name) for leg, name in zip(steps.GRID_LEGS, per_leg, strict=True) if name != base]
    if not weak:
        return Ground(base, note=note)
    ((leg, name),) = weak
    return Ground(base, patch_soil=name, patch_leg=leg, note=note)


def rigid_floor_ground(note: str) -> Ground:
    return Ground(RIGID, note=note)


# ------------------------------------------------------------------------------- run_v5 jobs
def run_v5_job_ground(job: dict) -> Ground | None:
    """Ground of a ``run_v5`` job: the D-1 row, else the verdict case twin."""
    if job.get("d1") is not None:
        import d1_rows

        row = d1_rows.D1Row.from_job(job["d1"])
        sink = None if row.sink is None else f"{row.sink.name}@{row.sink.leg}"
        return Ground(row.base, row.patch_soil, row.patch_leg, sink, note="d1_rows.D1Row")
    import verdict_cases

    decision = job.get("decision")
    decisions = {"R13": "ss_fs4"} | ({job["case"]: decision} if decision else {})
    case = verdict_cases.resolve_case(job["case"], decisions)
    twin = None if case is None else case.twin
    if isinstance(twin, verdict_cases.SteadyTwin):
        return Ground(twin.soil, note="verdict SteadyTwin (s9_soil_slope run)")
    if isinstance(twin, verdict_cases.EventTwin):
        event = job.get("twin") or {}
        leg = event.get("leg", twin.leg)
        return Ground(
            RIGID,
            sink=f"{twin.event}@{leg}",
            note="verdict EventTwin (r67 floor event, rigid r51 floor)",
        )
    return None


def run_v5_rows(bundle: str, jobs: list[dict]) -> list[dict]:
    return [_row(bundle, run_v5.job_key(job), run_v5_job_ground(job), "run_v5") for job in jobs]


# ---------------------------------------------------------------------------------- U-3 (H-3)
SLOPE_LIKE_SUITES = ("slope", "h6", "x426b", "h9", "p3b")


def u3_suite_rows(ids_path: Path, suite: str) -> list[dict]:
    """U-3 rows of one fix-candidates suite: the ``--ids-from`` keys and the suite's case."""
    import s9_slope_fix_candidates as fix
    import v5_rerun

    keys = v5_rerun.ids_from(ids_path, "B", suites=(suite,))
    payloads = dict(fix.suite_cases(suite))
    rows = []
    for key in keys:
        payload = payloads.get(key)
        if payload is None:
            ground = None
        elif suite in SLOPE_LIKE_SUITES:
            ground = Ground(str(payload["soil"]), note=f"{suite} case soil")
        elif suite == "g6":
            ground = g6_soil_ground(key.split("|")[1], "r72 parse_soil")
        else:  # g8: r69 non-planar start on the rigid floor
            ground = rigid_floor_ground("r69 g8 rigid floor (pad floor offset)")
        rows.append(_row("H-3", key, ground, f"s9_slope_fix_candidates {suite}"))
    return rows


def u3_c_rows(ids_path: Path) -> list[dict]:
    import v5_rerun

    keys = v5_rerun.ids_from(ids_path, "B")
    return [
        _row("H-3", key, g6_soil_ground(key.split("|")[1], "r72 parse_soil"), "r72_g6_screen x426")
        for key in keys
    ]


def u3_d_rows(ids_path: Path) -> list[dict]:
    import s9_soil_slope as slope
    import v5_rerun

    cases = {case.case_id: case for case in slope.build_cases((slope.H8_GROUP,))}
    rows = []
    for key in v5_rerun.ids_from(ids_path, "B"):
        case = cases.get(key)
        ground = None if case is None else Ground(case.soil, note="s9_soil_slope H8 case soil")
        rows.append(_row("H-3", key, ground, "s9_soil_slope H8"))
    return rows


def u3_rows(data_root: Path) -> list[dict]:
    rows = []
    for suite, _, ids, _ in steps.FIX_SUITES:
        rows += u3_suite_rows(data_root / steps.RV85 / f"{ids}.json", suite)
    rows += u3_c_rows(data_root / steps.RV85 / "fin_x426_C.json")
    rows += u3_d_rows(data_root / steps.RV85 / "fin_x426_D.json")
    return rows


# ---------------------------------------------------------------------------------- U-6 (H-4)
def b5_case_ground(case_id: str) -> Ground | None:
    """``b5_baseline_compare.case_spec`` of a U-6 case."""
    import b5_baseline_compare as b5

    spec = b5.case_spec(case_id)
    soil = spec["src"].split("|")[1]  # the field b5.check_event_allowed reads as the soil
    if spec["harness"] == "g6":
        return g6_soil_ground(soil, "b5 g6 src, r72 parse_soil")
    if spec["harness"] != "slope":
        return None
    sink = None if "event" not in spec else f"floor drop@{spec['event'][0]}"
    return Ground(soil, sink=sink, note="b5 slope src soil")


def u6_rows(data_root: Path) -> list[dict]:
    import v5_rerun

    rows = []
    for ids, pad in (("fin2_b5_wide_official", "B"), ("fin_b5_main", None)):
        for key in v5_rerun.ids_from(data_root / steps.RV84 / f"{ids}.json", pad):
            row = _row("H-4", key, b5_case_ground(key), "b5_baseline_compare")
            row["not_applicable_controllers"] = list(NOT_APPLICABLE_CONTROLLERS)
            rows.append(row)
    return rows


# -------------------------------------------------------------------------- r79 (H-6 .. H-8)
def r79_key_ground(key: str) -> Ground:
    """r79 ``run_job``: g6 and ref go through ``r72_g6_screen.job`` with a soil string, g8
    through ``r69_g8_screen.job`` on the rigid floor."""
    import r79_sensor_screen as screen

    _, _, case = screen.parse_job_key(key)
    if case.harness == "g8":
        return rigid_floor_ground("r79 g8: r69 rigid floor (pad floor offset)")
    soil = case.inner.split("|")[0 if case.harness == "ref" else 1]
    return g6_soil_ground(soil, f"r79 {case.harness}: r72 parse_soil")


def r79_rows(data_root: Path) -> list[dict]:
    rows = []
    for bundle, names in (
        ("H-6", ("dg3_v4_on",)),
        ("H-7", ("dg3_off",)),
        ("H-8", ("noise_VB", "noise_V0", "seedext_VB", "seedext_V0")),
    ):
        for name in names:
            relative, document = steps.stored_source(data_root, name)
            rows += [
                _row(bundle, key, r79_key_ground(key), f"r79 ({relative})")
                for key in steps.stored_r79_keys(document)
            ]
    return rows


# ---------------------------------------------------------------------------- H-9 grid, all
def grid_rows() -> list[dict]:
    rows = []
    for name in steps.GRID_RUNS:
        for key in steps.grid_expected_keys(name):
            _, _, _, _, leg = key.split("|")
            ground = Ground(
                RIGID,
                sink=f"r67 floor events@{leg}",
                note="r67 screen: floor event on the rigid r51 floor",
            )
            rows.append(_row("H-9", key, ground, f"r67 screen ({name})"))
    return rows


def _row(bundle: str, key: str, ground: Ground | None, source: str) -> dict:
    return {
        "bundle": bundle,
        "key": key,
        "family": family_of(ground),
        "ground": None if ground is None else asdict(ground),
        "source": source,
    }


def harness_jobs() -> dict[str, list[dict]]:
    """run_v5 jobs of H-1, H-9 (main V0 .. V8 L1 L2, pressure_only) and H-10 (RV1-2)."""
    import d1_rows

    main = run_v5.batch_jobs("main")
    return {
        "H-1": d1_rows.jobs(),
        "H-9": (
            run_v5.select_settings(main, steps.MAIN_STAGE1_SETTINGS)
            + run_v5.batch_jobs("pressure_only")
        ),
        "H-10": (
            run_v5.select_settings(main, steps.MAIN_REUSE_SETTINGS)
            + run_v5.select_settings(run_v5.u9_targeted_jobs(), ("VB",))
            + run_v5.batch_jobs("item8")
            + run_v5.batch_jobs("overlap")
        ),
    }


def conflicting_keys(rows: list[dict]) -> list[str]:
    """Keys that two rows place in different families (the judge looks keys up across bundles)."""
    families: dict[str, set[str]] = {}
    for row in rows:
        families.setdefault(row["key"], set()).add(row["family"])
    return sorted(key for key, found in families.items() if len(found) > 1)


def build_table(data_root: Path) -> dict:
    rows = []
    for bundle, jobs in harness_jobs().items():
        rows += run_v5_rows(bundle, jobs)
    rows += u3_rows(data_root) + u6_rows(data_root) + r79_rows(data_root) + grid_rows()
    conflicts = conflicting_keys(rows)
    for row in rows:
        if row["key"] in conflicts:
            row["family"] = FAMILY_UNRESOLVED
    counts = Counter((row["bundle"], row["family"]) for row in rows)
    return {
        "rules": RULES_REV1,
        "section": "RV1-6",
        "families": list(FAMILIES),
        "unresolved_rule": (
            f"{FAMILY_UNRESOLVED} = {FAMILY_UNIFORM} for the judge (K1 block -> S-6)"
        ),
        "rows": rows,
        "counts": {f"{bundle}|{family}": n for (bundle, family), n in sorted(counts.items())},
        "unresolved": sum(row["family"] == FAMILY_UNRESOLVED for row in rows),
        "conflicting_keys": conflicts,
    }


def write_table(out: Path, table: dict) -> str:
    """Write the table and ``<out>.sha256``; return the sha256."""
    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(table, indent=1, ensure_ascii=False) + "\n"
    out.write_bytes(text.encode("utf-8"))
    sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    out.with_name(out.name + ".sha256").write_text(f"{sha256}  {out.name}\n", encoding="utf-8")
    return sha256


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=ROOT,
        help="checkout with the stored v5 / rev84 / rev85 files",
    )
    args = parser.parse_args(argv)
    table = build_table(args.data_root)
    sha256 = write_table(args.out, table)
    print(
        json.dumps(
            {
                "rows": len(table["rows"]),
                "unresolved": table["unresolved"],
                "conflicting_keys": len(table["conflicting_keys"]),
                "sha256": sha256,
                "out": str(args.out),
            },
            ensure_ascii=True,
        )
    )
    return 1 if table["unresolved"] else 0


if __name__ == "__main__":
    sys.exit(main())
