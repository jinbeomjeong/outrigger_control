"""JOURNAL-AUGER (cad 2026-10-31): journal table soil 4 x auger 3 on the final controller.

* the 6 soil rows are the FINAL1 / FINAL2 / FINAL5 rows unchanged (argv, source_run, controller) and differ from the
  FINAL-REP J1 / J2 top rows only in --level (and --soil / --grid for G1);
* the 2 rigid rows run run_S8C set ``jaug``, whose cases equal K24_top_flat_Fs4 except the auger level (and the
  case id / group / priority / pair_fs0 / notes)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "04_scripts" / "02_chrono"))


def _args(argv: list[str]) -> dict[str, str]:
    i = next(k for k, t in enumerate(argv) if t.endswith("run_S9.py"))
    rest, out, k = argv[i + 2:], {}, 0
    while k < len(rest):
        if k + 1 < len(rest) and not rest[k + 1].startswith("--"):
            out[rest[k]] = rest[k + 1]
            k += 2
        else:
            out[rest[k]] = "1"
            k += 1
    return out


def test_soil_rows_are_bundle_rows_with_only_level_soil_changed() -> None:
    import s9_batch

    b = s9_batch.batches()
    rows = b["JOURNAL-AUGER"]
    soil = [r for r in rows if not r.get("s8c")]
    assert [r["case"] for r in soil] == [c for _, c, _ in s9_batch.JOURNAL_AUGER_SOIL_ROWS]
    for (bundle, case, _), r in zip(s9_batch.JOURNAL_AUGER_SOIL_ROWS, soil):
        src = next(c for c in b[bundle] if c["case"] == case)
        assert r["argv"] == src["argv"] and r["source_run"] == src["source_run"]
        assert r["controller"] == "final_SGS_R4" and "--expect-controller" in r["argv"]
    ref = {c["case"]: _args(c["argv"]) for c in b["FINAL-REP"]}
    for r in soil:
        s = r["case"].split("_")[1]
        base = ref["P3b_J2_B_top_Fs4" if s == "J2" else "P3b_J1_B_top_Fs4"]
        a = _args(r["argv"])
        diff = {k for k in set(a) | set(base) if a.get(k) != base.get(k)}
        assert diff <= {"--level", "--soil", "--grid"}, (r["case"], diff)
        if s in ("J1", "J2"):
            assert diff == {"--level"}


def test_rigid_rows_equal_k24_flat_except_level() -> None:
    import run_S8C as s8
    import s9_batch

    rigid = [r for r in s9_batch.batches()["JOURNAL-AUGER"] if r.get("s8c")]
    assert [r["case"] for r in rigid] == list(s9_batch.JOURNAL_AUGER_RIGID_CASES)
    assert all(r["group"] == "FINAL-R" and "--set" in r["argv"] and "jaug" in r["argv"] for r in rigid)
    tab = s8.case_table()
    ref = tab["K24_top_flat_Fs4"].to_meta()
    for cid, lv in zip(s9_batch.JOURNAL_AUGER_RIGID_CASES, s8.JAUG_LEVELS):
        m = tab[cid].to_meta()
        assert m["level"] == lv and m["base"]["scenario"]["level"] == lv
        for k in ("engine", "fs_kN", "event", "lock_valve", "condition", "contact", "floor", "duration_s"):
            assert m[k] == ref[k], k
        strip = ("case_id", "level")
        b0 = {k: v for k, v in ref["base"]["scenario"].items() if k not in strip}
        b1 = {k: v for k, v in m["base"]["scenario"].items() if k not in strip}
        assert b0 == b1
