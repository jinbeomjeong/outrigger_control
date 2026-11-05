"""Values of v5 Chrono S9 runs (criteria ``v5_criteria.md`` 13.8 (⑧) and 3.1 (⑦)); no verdict text.

Modelled on ``06_analysis/03_hydraulic/coupled/verdict/judgement_chrono/judge_soil.py``: the run
folders are read only (``run_S9.rejudge_case(write=False)`` and ``run_S9.judge_chrono_soil_event``,
the same judge code as the runs) and nothing is written into them.

- Level rows (``result.json`` action ``level`` with ``p3b``): the P3 checks of the re-judgement.
  P3-4 is read from ``P3-4_verdict`` (pass / flag / fail, spec 433.6); ``P3-4_within_0p2`` is not
  read. A ``window_short`` row counts as ``flag``, never as a pass, even where a stored legacy
  creep rule called it ``pass``. The P3-4 count of the summary takes the level rows without a
  soil event.
- Soil event rows (``soil_event`` in ``result.json``): after the event window (fast: W, slow: ramp
  end + 3 s) on the 1 ms Chrono rows cut at the harness branch end, the values of
  ``verdict_metrics.after_window_force_values`` (the harness X-8 function, so one definition):
  1 ms minimum, trailing 0.5 s mean minimum, pad lift after the window [ms] and ``FLAG_E3_1ms``
  (minimum, summed and longest time below F_min [ms]).

Usage (dynamics-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/judge_chrono_v5.py <out_json> <case_or_batch> [...]
A batch folder stands for its case folders (sub-folders with a ``result.json``).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "04_scripts" / "02_chrono", ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from verdict_metrics import after_window_force_values  # noqa: E402

RESULT_FILE = "result.json"
P3_CHECK_KEYS = ("P3-1_recontact_pass", "P3-2_verdict", "P3-3_within", "P3-4_verdict",
                 "P3-4_absmax_deg", "P3-4_window_s", "P3-4_window_short", "P3-4_flags",
                 "P3-4_creep_vibration_suspect", "P3-5_within", "P3-6_within", "P3-7_within",
                 "P3-8_within", "P3-9_flags")
"""``p3b.checks`` keys copied per row; ``P3-4_within_0p2`` is left out on purpose (13.8)."""
P34_VERDICTS = ("pass", "flag", "fail")
EVENT_JUDGEMENT_KEYS = ("event", "fast", "trigger", "t_ev_loop_s", "stop_rel_s", "stop_reason",
                        "event_window_end_s", "phase_at_event", "pass", "gates", "flags")
SLOW_EVENT_E3_GATE = "E-3_Fmin_after_event"
FAST_EVENT_E3_GATE = "E-3_Fmin_after_W"


def case_folders(paths: list[str]) -> list[Path]:
    """Case folders of the arguments (a batch folder gives its sub-folders with a result)."""
    folders = []
    for path in map(Path, paths):
        if (path / RESULT_FILE).exists():
            folders.append(path)
            continue
        folders += sorted(child for child in path.iterdir()
                          if child.is_dir() and (child / RESULT_FILE).exists())
    return folders


def counted_p34(checks: dict) -> str | None:
    """P3-4 as the v5 count reads it: ``P3-4_verdict``, a short window never a pass."""
    verdict = checks.get("P3-4_verdict")
    if verdict == "pass" and checks.get("P3-4_window_short"):
        return "flag"
    return verdict


def level_values(case_dir: Path, run_s9) -> dict:
    """P3 checks of one level row from the re-judgement of its stored records."""
    rejudged = run_s9.rejudge_case(case_dir, write=False)
    checks = rejudged["p3b"]["checks"]
    return {"checks": {key: checks.get(key) for key in P3_CHECK_KEYS},
            "P3-4_counted": counted_p34(checks),
            "unchanged_blocks_equal": rejudged["unchanged_blocks_equal"],
            "params_file_match": rejudged["params_file_match"]}


def soil_event_values(case_dir: Path, run_s9, f_min_N: float) -> dict:
    """Criteria 3.1 values of one Chrono soil event row (rows cut where the judge cuts them)."""
    judged = run_s9.judge_chrono_soil_event(case_dir)
    with np.load(case_dir / run_s9.SOIL_EVENT_SERIES_NAME, allow_pickle=False) as series:
        rows = np.asarray(series["rows"], float)
    t_rel_s = rows[:, 0] - float(judged["t_ev_s"])
    kept = t_rel_s <= float(judged["stop_rel_s"]) + 1e-9
    after_window = after_window_force_values(
        t_rel_s[kept], rows[kept, 5:9], rows[kept, 1:5], float(judged["event_window_end_s"]),
        f_min_N)
    gate = FAST_EVENT_E3_GATE if judged.get("fast") else SLOW_EVENT_E3_GATE
    return {"judgement": {key: judged.get(key) for key in EVENT_JUDGEMENT_KEYS},
            "E3_1ms_gate": (judged.get("gates") or {}).get(gate),
            "after_window_force": after_window}


def case_values(case_dir: Path, run_s9, f_min_N: float) -> dict:
    """Every v5 value one case folder has (level checks, soil event values)."""
    result = json.loads((case_dir / RESULT_FILE).read_text(encoding="utf-8"))
    out = {"case": case_dir.name, "dir": case_dir.as_posix(),
           "final_phase": str(result["phases"][-1]["phase"]).lower() if result.get("phases")
           else None}
    if result.get("action") == "level" and "p3b" in result:
        out["level"] = level_values(case_dir, run_s9)
    if result.get("soil_event"):
        out["soil_event"] = soil_event_values(case_dir, run_s9, f_min_N)
    return out


def summary(cases: list[dict]) -> dict:
    """Counts: P3-4 as counted (pass / flag / fail / none) over the level rows without an event
    (event rows are judged by E-1 .. E-7; their P3 checks stay in the row only) and the soil
    event rows with ``FLAG_E3_1ms``."""
    level_rows = [case for case in cases if "level" in case and "soil_event" not in case]
    p34 = Counter(str(case["level"]["P3-4_counted"]) for case in level_rows)
    events = [case for case in cases if "soil_event" in case]
    flagged = [case["case"] for case in events
               if case["soil_event"]["after_window_force"].get("FLAG_E3_1ms")]
    return {"level_rows": len(level_rows),
            "P3-4_counted": {verdict: p34.get(verdict, 0) for verdict in (*P34_VERDICTS, "None")},
            "soil_event_rows": len(events), "FLAG_E3_1ms_rows": flagged}


def harness_f_min_N() -> float:
    """F_min of the harness X-8 values (``r67_g1_screen.F_MIN_N``), one definition for both."""
    s9_dir = ROOT / "04_scripts" / "03_control" / "s9"
    if str(s9_dir) not in sys.path:
        sys.path.insert(0, str(s9_dir))
    import s9_soil_event_screen

    return float(s9_soil_event_screen._s8_modules()["r67"].F_MIN_N)


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    import run_S9

    out_path = Path(sys.argv[1])
    f_min_N = harness_f_min_N()
    cases = []
    for case_dir in case_folders(sys.argv[2:]):
        cases.append(case_values(case_dir, run_S9, f_min_N))
        print(case_dir.name, "done", flush=True)
    report = {"criteria": "v5_criteria.md 13.8 (P3-4_verdict), 3.1 (after-window force)",
              "F_min_N": f_min_N, "summary": summary(cases), "cases": cases}
    out_path.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=float),
                        encoding="utf-8")
    print(json.dumps(report["summary"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
