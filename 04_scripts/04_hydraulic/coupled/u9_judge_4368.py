"""436.8 path 1 judge of U-9 (H-5), new version (rules rev5 R5-A1; ``u9_targeted_rules_rev1.md``).

Inputs are arguments: the H-5 V0 lines (``resume_k1/h5_u9_v0.jsonl``) and the H-10 output
(``resume_k1/h10_reuse_rerun.jsonl``: its U-9 VB lines, those with ``u9_metrics``, and its
main VB lines). The T3 / T4 / classification code is the one of ``u9_judge.py``; the changes:

  D-18  H0 ① reference = the main VB line of the same ``git_at_start`` H-10 output with the same
        (case, eps) (no ``u9_metrics`` / ``eta_v``), not the stored ``p3_hash.jsonl`` (rev3
        R3-C1). Unequal or missing = stop. Stored ``p3_hash`` / ``main`` comparisons are records.
  Grade (rev3 R3-C2): T1 of eta_v 0.85 VB vs V0 (J items of ``judge_stage1_4368``, D-07 ..
  D-11 and J-P3) and H0. T1 failure = 미달; eta_v 0.80 T1, T3a .. T3c, T4 and the 4.1 class A .. D
  are records; class C asks the user before the v5 summary sentence (``ask_user``).

Usage (python-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/u9_judge_4368.py --out <report.json>
      --v0 <h5_u9_v0.jsonl> --h10 <h10_reuse_rerun.jsonl> [--t4h-dir <dir> ...]
      [--stored-p3-hash <v5/p3_hash.jsonl>] [--rules-dir <verif_matrix>]
Exit codes: 0 judged, 1 H0 stop / T1 failure / 판정 불가, 2 input error, 3 internal error.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

import judge4368_common as common  # noqa: E402
import judge_stage1_4368 as stage1  # noqa: E402

T3A_DEG, T3B_DEG, T3C_DEG = 0.10, 0.05, 0.10
T4_FLOOR_S, T4_ADD_S = 20.0, 5.0
AB_EDGE_S = 0.5
H0_KEYS = {("S2", 0.002), ("S3", 0.0), ("R3", 0.0), ("S5", 0.0)}
"""``u9_targeted_rules_rev1.md`` 4 H0 ① keys."""
DEFINITION_CHANGES = ("D-18",)
OLD_TOOL = stage1.STAGE1_SCRIPTS / "u9_judge.py"


def _eps(line: dict) -> float:
    return float(line["job"].get("eps", 0.0))


def setting_of(line: dict) -> str:
    job = line["job"]
    return "V0" if job["setting"] == "V0" else f"VB{float(job.get('eta_v', 0.85)):g}"


def is_u9_line(line: dict) -> bool:
    return bool(line["job"].get("u9_metrics"))


def is_main_steady_vb(line: dict) -> bool:
    job = line["job"]
    return (
        job.get("setting") == "VB"
        and not is_u9_line(line)
        and job.get("eta_v") is None
        and job.get("offset_s") is None
        and not job.get("twin")
        and job.get("decision") != "reanchor_on"
        and "timing" not in job
    )


def h0(u9_lines: list[dict], h10_lines: list[dict], stored_p3: list[dict] | None) -> dict:
    """D-18: H0 ① against the same-commit H-10 main VB line; stored p3_hash as a record."""
    main_vb = defaultdict(list)
    for line in h10_lines:
        if "error" not in line and is_main_steady_vb(line):
            main_vb[(line["job"]["case"], _eps(line))].append(line["commands_sha256"])
    stored = defaultdict(list)
    for line in stored_p3 or []:
        job = line.get("job") or {}
        stored[(job.get("case"), float(job.get("eps", 0.0)))].append(line.get("commands_sha256"))
    rows = []
    for line in u9_lines:
        key = (line["job"]["case"], _eps(line))
        if setting_of(line) != "VB0.85" or key not in H0_KEYS:
            continue
        reference = main_vb.get(key, [])
        rows.append(
            {
                "case": key[0],
                "eps": key[1],
                "sha": line["commands_sha256"][:16],
                "reference": [s[:16] for s in reference],
                "equal": len(reference) == 1 and reference[0] == line["commands_sha256"],
                "stored_p3_hash_equal_record": (
                    line["commands_sha256"] in stored.get(key, [])
                    if stored_p3 is not None
                    else None
                ),
            }
        )
    found = {(r["case"], r["eps"]) for r in rows}
    return {
        "rows": rows,
        "missing_keys": sorted(map(list, H0_KEYS - found)),
        "stop": not rows or any(not r["equal"] for r in rows) or found != H0_KEYS,
    }


def _axes(value) -> list[float]:
    return [value["roll"], value["pitch"]] if isinstance(value, dict) else list(value)


def t3_t4(low: dict, high: dict) -> dict:
    """Rules 4 T3a .. T3c and T4 of eta_v 0.80 (``u9_judge.py`` definitions), records."""
    deltas = [max(abs(x) for x in _axes(g["max_abs_delta_deg"])) for g in low["ge3_runs"]]
    t3b = [
        {
            "t_start_s": g["t_start_s"],
            "ok": all(
                abs(b) <= abs(a) + T3B_DEG
                for a, b in zip(
                    _axes(g["filtered_start_deg"]), _axes(g["filtered_end_deg"]), strict=True
                )
            ),
        }
        for g in low["ge3_runs"]
    ]
    t3c = low["att_max_after_liftoff"] - high["att_max_after_liftoff"]
    back_low = low["E5"].get("back_in_band_after_saturation_s")
    back_high = high["E5"].get("back_in_band_after_saturation_s")
    limit = max(T4_FLOOR_S, (back_high or 0.0) + T4_ADD_S)
    return {
        "T3a": {
            "max_delta_deg": max(deltas, default=None),
            "pass": all(d <= T3A_DEG for d in deltas),
        },
        "T3b": {"pass": all(r["ok"] for r in t3b), "runs": t3b},
        "T3c": {"delta_deg": t3c, "pass": t3c <= T3C_DEG},
        "T4": {
            "value_s": back_low,
            "limit_s": limit,
            "pass": back_low is not None and back_low <= limit,
        },
    }


def key_values(line: dict, row: dict) -> dict:
    values = line["values"]
    u9 = values.get("U9") or {}
    return {
        "final": row["final"],
        "class": row["class"],
        "t_ready": row["t_ready"],
        "F_after": row["F_after"],
        "att_max_after_liftoff": values["attitude"]["max_abs_after_liftoff_deg"],
        "longest_ge3_s": u9.get("longest_ge3_s"),
        "longest_eq4_s": u9.get("longest_eq4_s"),
        "ge3_runs": u9.get("ge3_runs") or [],
        "E5": values.get("E5") or {},
        "sha": line["commands_sha256"][:16],
    }


def per_key(u9_lines: list[dict], t4h_dirs: tuple[Path, ...]) -> list[dict]:
    rows = {}
    for line in u9_lines:
        row = stage1.metrics(line, t4h_dirs)
        row["setting"] = setting_of(line)
        rows[(line["job"]["case"], _eps(line), row["setting"])] = (row, line)
    v0_groups = defaultdict(list)
    for (case, _, setting), (row, _) in rows.items():
        if setting == "V0":
            v0_groups[case].append(row)
    out = []
    for case, eps in sorted({(c, e) for c, e, _ in rows}):
        entry: dict[str, Any] = {"case": case, "eps": eps}
        missing = [s for s in ("V0", "VB0.85", "VB0.8") if (case, eps, s) not in rows]
        if missing:
            entry["missing_settings"] = missing
            out.append(entry)
            continue
        base = rows[(case, eps, "V0")][0]
        n_rev_max = max(r["n_rev"] for r in v0_groups[case])
        for setting in ("VB0.85", "VB0.8"):
            row, line = rows[(case, eps, setting)]
            entry[setting] = key_values(line, row)
            entry[setting]["J"] = stage1.j_items(base, row, v0_groups[case], n_rev_max)
        entry["V0"] = key_values(rows[(case, eps, "V0")][1], base)
        entry.update(t3_t4(entry["VB0.8"], entry["VB0.85"]))
        entry["T1"] = {setting: _t1_state(entry[setting]["J"]) for setting in ("VB0.85", "VB0.8")}
        out.append(entry)
    return out


def _t1_state(items: list[dict]) -> str:
    kinds = {i["kind"] for i in items}
    if "stop" in kinds:
        return "stop"
    if "not_judgeable" in kinds:
        return "판정 불가"
    return "fail" if "fail" in kinds else "pass"


def classification(keys: list[dict]) -> dict:
    """Rules 4.1 class (record, rev3 R3-C2)."""
    complete = [k for k in keys if "T1" in k]
    saturation = any(k["T1"]["VB0.85"] == "pass" and k["T1"]["VB0.8"] == "fail" for k in complete)
    t3_t4_fail = any(
        not (k["T3a"]["pass"] and k["T3b"]["pass"] and k["T4"]["pass"]) for k in complete
    )
    t3c_fail = any(not k["T3c"]["pass"] for k in complete)
    longest = max(((k["VB0.8"]["longest_ge3_s"] or 0.0) for k in complete), default=0.0)
    if saturation or t3_t4_fail or t3c_fail:
        name = "C"
    else:
        name = "A" if longest >= AB_EDGE_S else "B"
    return {
        "class": name,
        "saturation_caused_T1_fail": saturation,
        "T3ab_T4_fail": t3_t4_fail,
        "T3c_fail": t3c_fail,
        "longest_ge3_s_eta080": longest,
        "D_rows_VB0.85_fail": [
            f"{k['case']}|{k['eps']}" for k in complete if k["T1"]["VB0.85"] != "pass"
        ],
        "ask_user": name == "C",
    }


def judge(args: argparse.Namespace) -> dict:
    t4h_dirs = tuple(Path(p) for p in args.t4h_dir or [])
    v0_lines = common.read_jsonl(args.v0)
    h10_lines = common.read_jsonl(args.h10)
    u9_vb = [line for line in h10_lines if is_u9_line(line)]
    u9_lines = [line for line in [*v0_lines, *u9_vb] if "error" not in line]
    stored = None if args.stored_p3_hash is None else common.read_jsonl(args.stored_p3_hash)
    report: dict[str, Any] = {
        "inputs": {"v0": str(args.v0), "h10": str(args.h10)},
        "lines": {"V0": len(v0_lines), "VB_u9": len(u9_vb)},
        "errors": sum("error" in line for line in [*v0_lines, *u9_vb]),
    }
    report["H0"] = h0(u9_lines, h10_lines, stored)
    report["keys"] = per_key(u9_lines, t4h_dirs)
    report["classification_record"] = classification(report["keys"])
    t1 = [k["T1"]["VB0.85"] for k in report["keys"] if "T1" in k]
    report["grade"] = (
        "멈춤"
        if report["H0"]["stop"] or "stop" in t1
        else "판정 불가"
        if "판정 불가" in t1 or any("missing_settings" in k for k in report["keys"])
        else "미달"
        if "fail" in t1
        else "통과"
    )
    findings = [] if report["grade"] == "통과" else [f"H-5 grade {report['grade']}"]
    if report["errors"]:
        findings.append(f"{report['errors']} error lines")
    if report["classification_record"]["ask_user"]:
        findings.append("4.1 class C: ask the user before the v5 summary (record, rev3 R3-C2)")
    report["findings"] = findings
    return report


def parser() -> argparse.ArgumentParser:
    out = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    common.add_common_arguments(out)
    out.add_argument("--v0", type=Path, required=True, help="resume_k1/h5_u9_v0.jsonl")
    out.add_argument("--h10", type=Path, required=True, help="resume_k1/h10_reuse_rerun.jsonl")
    out.add_argument("--t4h-dir", action="append", help="folder of the T4h files (repeatable)")
    out.add_argument(
        "--stored-p3-hash", type=Path, default=None, help="stored v5/p3_hash.jsonl (record only)"
    )
    return out


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    return common.run_judge(
        judge,
        args,
        script=Path(__file__).resolve(),
        old_tools=(OLD_TOOL,),
        changes=DEFINITION_CHANGES,
    )


if __name__ == "__main__":
    sys.exit(main())
