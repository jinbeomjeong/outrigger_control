"""Spec 426.7 identity checks of the study A..D harness extensions (T-2 .. T-5 and the reference
identities of 426.5 / 426.6), written to ``06_analysis/02_control/s9/rev85/x426_identity.json``.

Parts (each item runs in a fresh worker process: r72 / s9_soil_slope patch the s9 module):
  t2     study A base run (readings "head", no event) to READY + 10 s = ``sl.run_case`` of the same
         case (settle hook "harness", project preset controller): command SHA-256
  t3     study 1 cases without ``pad_start_gap`` (``s9_soil_slope.run_one``) = rev83 R2DS hashes
  t4     r72 keys of the former sets (``r72_g6_screen.job``, settle hook p0) = rev83 R2DS g6
  c_ref  spec 426.5: the x426 uniform references = the P3b rows of rev83 R2DS p3b
  d_ref  spec 426.6: the H8 references (no start gap) = study 1 H1 / H5 flat
  t5     ``apply_pad_start_gap`` after the settle: start gap within 0.1 mm (soil and rigid)
Stored hashes come from the rev83 files (full 64 hex digits); the spec's 8-hex prefixes are
checked too.

Usage (dynamics-dev, MKL_THREADING_LAYER=TBB, OMP_NUM_THREADS=1):
  python -I x426_identity.py <out_json> [workers] [parts comma list, default all]
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
import time
import traceback
from multiprocessing import Pool
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for _path in (HERE, ROOT / "04_scripts" / "03_control" / "s8"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

REV83 = ROOT / "06_analysis" / "02_control" / "s9" / "rev83"
DEFAULT_OUT = ROOT / "06_analysis" / "02_control" / "s9" / "rev85" / "x426_identity.json"
SETTLE_TABLE = ROOT / "06_analysis" / "00_dynamics" / "slope_crawler_settle.json"
START_GAP_TOL_MM = 0.1
PARTS = ("t2", "t3", "t4", "c_ref", "d_ref", "t5")

T2_CASE = {"soil": "J2", "pad": "B", "level": "top", "fs_kN": 8.0}
T3_CASES = {  # case id: (stored file, spec prefix)
    "H1|G1|B|top|flat": ("R2DS_slope_rejudged.json", "f805759d"),
    "H3|J1|B|top|nose_down@k0.5": ("R2DS_slope_rejudged.json", "36be51a4"),
    "H5|rigid|B|top|flat": ("R2DS_slope_rejudged.json", "a91e9579"),
    "H6|J1|B|top|flat|Fs0|m1.1": ("R2DS_h6.json", "80ae99f6"),
}
T4_KEYS = {
    "g6|G1+J1@RR|top|Fs4": "69288ee3", "g6|G1+J2@FL|bottom|Fs0": "b6b6006e",
    "ref|J2|top|Fs0": "5b0f466c", "g6r|rigid+S1@FL|top|Fs4": "1145e904",
    "ref|rigid|top|Fs0": "269521d3",
}
C_REF_KEYS = {  # x426 key: (P3b id, spec prefix)
    "ref|G1|top|Fs4|PA": ("base|G1|A|top|Fs4", "6e716d52"),
    "ref|J2|top|Fs4|PA": ("base|J2|A|top|Fs4", "40977d68"),
    "ref|J1|top|Fs4|PA": ("base|J1|A|top|Fs4", "44f1cbc7"),
    "ref|S1|top|Fs4|PA": ("base|S1|A|top|Fs4", "0cf67d72"),
    "ref|G1|top|Fs8": ("base|G1|B|top|Fs8", "db39f965"),
    "ref|J2|middle|Fs4": ("base|J2|B|middle|Fs4", "2c5cb149"),
}
D_REF_CASES = {  # H8 reference: (study 1 id, spec prefix)
    "H8|G1|B|top|flat": ("H1|G1|B|top|flat", "f805759d"),
    "H8|J2|B|top|flat": ("H1|J2|B|top|flat", "09326147"),
    "H8|rigid|B|top|flat": ("H5|rigid|B|top|flat", "a91e9579"),
}
T5_CASES = (("J2", {"leg": "FL", "gap_m": 0.055}), ("rigid", {"leg": "RR", "delta_m": 0.060}))


@contextlib.contextmanager
def _argv_as_root():
    saved = sys.argv
    sys.argv = [saved[0] if saved else "", str(ROOT)]
    try:
        yield
    finally:
        sys.argv = saved


def stored_hash(file_name: str, case_id: str) -> str:
    """Full command hash of the ``current`` record of a rev83 re-check file."""
    records = json.loads((REV83 / file_name).read_text(encoding="utf-8"))["records"]
    (record,) = [r for r in records if r["id"] == case_id and r["candidate"] == "current"]
    return record["hash"]


def _slope_case(case_id: str) -> dict:
    import s9_soil_slope as slope

    group = case_id.split("|")[0]
    table = json.loads(SETTLE_TABLE.read_text(encoding="utf-8"))["hook_harness"]
    cases = slope.attach_settle_table(slope.build_cases((group,)), table)
    (case,) = [c for c in cases if c.case_id == case_id]
    return case.to_dict()


def _run_t2() -> dict:
    import s9_soil_closed_loop as sl
    import s9_soil_event_screen as screen

    cl, c2, Meas = sl._imports()
    plant, ctrl, _ = screen.make_event_base(cl, c2, T2_CASE["soil"], T2_CASE["level"],
                                            T2_CASE["pad"], T2_CASE["fs_kN"])
    base = screen.run_base_soil(cl, Meas, plant, ctrl, screen.READINGS_HEAD)
    sl.make_controller = screen.preset_controller
    out = sl.run_case({"id": "t2", **T2_CASE, "variant": {}, "settle_hook": screen.SETTLE_HOOK})
    return {"expected_source": "s9_soil_closed_loop.run_case (same case)",
            "expected_hash": out["commands_sha256"], "actual_hash": base["commands_sha256"],
            "t_ready_s": [base["t_ready"], out["t_ready_s"]]}


def _run_slope(case_id: str) -> str:
    import s9_soil_slope as slope

    result = slope.run_one(_slope_case(case_id))
    if "error" in result:
        raise RuntimeError(result["error"] + "\n" + result.get("tb", ""))
    return result["run"]["commands_sha256"]


def _run_r72(key: str) -> str:
    with _argv_as_root():
        import r72_g6_screen as r72
    record = r72.job(key)
    if "error" in record:
        raise RuntimeError(record["error"] + "\n" + record.get("tb", ""))
    return record["commands_sha256"]


def _run_t5(soil: str, spec: dict) -> dict:
    import numpy as np
    import s9_soil_closed_loop as sl

    cl, _, _ = sl._imports()
    cl.rmf.CONFIG.clear()
    cl.rpt.RCFG.clear()
    plant = sl.make_plant(cl, "top", soil, "B", 4.0, settle_hook=sl.SETTLE_HOOK_HARNESS)
    plant.step(np.zeros(4), int(round(cl.rcc.SETTLE_ON_CRAWLER_S / plant.dt)))
    record = sl.apply_pad_start_gap(cl, plant, spec)
    target_mm = (spec["gap_m"] * 1e3 if "gap_m" in spec
                 else record["g0_mm"] + spec["delta_m"] * 1e3)
    error_mm = record["g_start_mm"] - target_mm
    return {**record, "target_mm": target_mm, "error_mm": error_mm,
            "equal": abs(error_mm) <= START_GAP_TOL_MM}


def run_item(item: dict) -> dict:
    """Worker entry: one identity item."""
    t0 = time.perf_counter()
    row = dict(item)
    try:
        if item["part"] == "t2":
            row.update(_run_t2())
        elif item["part"] in ("t3", "d_ref"):
            row["actual_hash"] = _run_slope(item["id"])
        elif item["part"] in ("t4", "c_ref"):
            row["actual_hash"] = _run_r72(item["id"])
        elif item["part"] == "t5":
            row.update(_run_t5(item["soil"], item["spec"]))
        if "actual_hash" in row:
            row["equal"] = row["actual_hash"] == row["expected_hash"]
    except Exception as exc:  # keep the batch going; the item fails with its error
        row.update(error=repr(exc), tb=traceback.format_exc()[-2000:], equal=False)
    row["wall_s"] = round(time.perf_counter() - t0, 1)
    return row


def build_items(parts) -> list[dict]:
    """Identity items of the named parts with their stored hashes and spec prefixes."""
    items = []
    if "t2" in parts:
        items.append({"part": "t2", "id": "A|{soil}|{pad}|{level}|Fs{fs_kN:g}|head".format(
            **T2_CASE)})
    for case_id, (file_name, prefix) in T3_CASES.items():
        if "t3" in parts:
            items.append({"part": "t3", "id": case_id, "expected_source": f"rev83/{file_name}",
                          "expected_hash": stored_hash(file_name, case_id), "spec_prefix": prefix})
    for key, prefix in T4_KEYS.items():
        if "t4" in parts:
            items.append({"part": "t4", "id": key, "expected_source": "rev83/R2DS_g6.json",
                          "expected_hash": stored_hash("R2DS_g6.json", key), "spec_prefix": prefix})
    for key, (p3b_id, prefix) in C_REF_KEYS.items():
        if "c_ref" in parts:
            items.append({"part": "c_ref", "id": key, "expected_id": p3b_id,
                          "expected_source": "rev83/R2DS_p3b.json",
                          "expected_hash": stored_hash("R2DS_p3b.json", p3b_id),
                          "spec_prefix": prefix})
    for case_id, (study_id, prefix) in D_REF_CASES.items():
        if "d_ref" in parts:
            items.append({"part": "d_ref", "id": case_id, "expected_id": study_id,
                          "expected_source": "rev83/R2DS_slope_rejudged.json",
                          "expected_hash": stored_hash("R2DS_slope_rejudged.json", study_id),
                          "spec_prefix": prefix})
    if "t5" in parts:
        for soil, spec in T5_CASES:
            items.append({"part": "t5", "id": f"{soil}|{spec['leg']}", "soil": soil, "spec": spec})
    for item in items:
        if "spec_prefix" in item:
            item["stored_matches_spec_prefix"] = item["expected_hash"].startswith(
                item["spec_prefix"])
    return items


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    parts = tuple(sys.argv[3].split(",")) if len(sys.argv) > 3 else PARTS
    os.environ["S9_SETTLE_HOOK"] = "p0"  # the rev83 g6 / p3b rows ran the p0 hook
    items = build_items(parts)
    t0 = time.perf_counter()
    with Pool(max(1, min(workers, len(items))), maxtasksperchild=1) as pool:
        rows = pool.map(run_item, items, chunksize=1)
    meta = {"script": "04_scripts/03_control/s9/x426_identity.py", "spec": "426.7 T-2 .. T-5",
            "parts": parts, "settle_hook_env": "p0", "workers": workers,
            "wall_s": round(time.perf_counter() - t0, 1)}
    payload = {"meta": meta, "all_equal": all(r.get("equal") for r in rows), "rows": rows}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1, default=float), encoding="utf-8")
    for row in rows:
        print(row["part"], row["id"], "equal", row.get("equal"), row.get("error", ""))
    print("all_equal", payload["all_equal"], "wall", meta["wall_s"], "s ->", out)


if __name__ == "__main__":
    main()
