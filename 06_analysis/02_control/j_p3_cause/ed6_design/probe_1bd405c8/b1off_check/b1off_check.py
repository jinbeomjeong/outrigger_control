"""Spec revision 6 Q6-14 (user decision 2026-11-24): the B1-off check of the sealed range and
the n_rev / L-c record of the probe's full arm.

1. The 40 lines of the sealed range ``a1a2b3`` (A_i, A_ii, B3; ``ed6_probe.py --arms
   a1a2b3`` at e8ddf04e) against the 40 ``a1a2b`` lines (A_i, A_ii, B1, B3) of the probe run
   1bd405c8: same ``commands_sha256`` per (plant, key)?
2. ``n_rev`` of the a1a2b lines (path 1 metric, ``judge_stage1_4368.metrics``) with the
   largest V0 ``n_rev`` of the row's group (stored ``main.jsonl``) and the criteria 4 L-c rule
   (``jp3_j9main_judge``: ``n_rev >= 2 max`` and ``n_rev >= max + 6``) as a record.

Writes ``b1off_check.json`` and ``b1off_check.csv`` next to this file (an existing output is
refused). Exit 0 = every pair has the same hash, 1 = some differ, 2 = input error,
3 = tool error. The stdout's last line is JSON with ``status`` and the counts.

Usage (dynamics-dev):
  python -I -B b1off_check.py <code checkout> <probe jsonl> <probe sha256> <check jsonl>
      <stored v5 main.jsonl> <main sha256>
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXIT_SAME, EXIT_DIFFER, EXIT_INPUT, EXIT_TOOL = 0, 1, 2, 3
FULL_ARM, SEALED_ARM = "a1a2b", "a1a2b3"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_lines(path: Path) -> list[dict]:
    return [json.loads(text) for text in path.read_text(encoding="utf-8").splitlines()
            if text.strip()]


def by_plant_key(lines: list[dict], arm: str, probe) -> dict:
    out = {}
    for line in lines:
        plant, line_arm = probe.split_setting_name(line["job"]["setting"])
        if line_arm == arm and "error" not in line:
            out[(plant, probe.d0.key_name(line["job"]))] = line
    return out


def n_rev_rows(full: dict, folders: tuple[Path, ...], v0_metrics: list[dict], j9judge,
               path1) -> list[dict]:
    off_max: dict[str, int | None] = {}
    for row in v0_metrics:
        group, n_rev = row["group"], row.get("n_rev")
        if n_rev is None or (group in off_max and off_max[group] is None):
            off_max[group] = None
        else:
            off_max[group] = max(off_max.get(group) or 0, n_rev)
    rows = []
    for (plant, key), line in sorted(full.items()):
        metric = path1.metrics(line, folders)
        reference = off_max.get(metric["group"])
        n_rev = metric.get("n_rev")
        flagged = (None if reference is None or n_rev is None
                   else bool(n_rev >= j9judge.LIMIT_CYCLE_FACTOR * reference
                             and n_rev >= reference + j9judge.LIMIT_CYCLE_MARGIN))
        rows.append({"plant": plant, "key": key, "row": metric["row"], "phase": metric["phase"],
                     "group": metric["group"], "n_rev": n_rev, "v0_group_n_rev_max": reference,
                     "l_c_threshold": (None if reference is None else
                                       max(j9judge.LIMIT_CYCLE_FACTOR * reference,
                                           reference + j9judge.LIMIT_CYCLE_MARGIN)),
                     "l_c_rule_met": flagged})
    return rows


def main(argv: list[str]) -> int:
    try:
        checkout, probe_path, probe_sha, check_path, main_path, main_sha = argv[1:7]
    except ValueError:
        print(json.dumps({"status": "input_error", "reason": "six arguments"}))
        return EXIT_INPUT
    out_json, out_csv = HERE / "b1off_check.json", HERE / "b1off_check.csv"
    if out_json.exists() or out_csv.exists():
        print(json.dumps({"status": "input_error", "reason": "output exists"}))
        return EXIT_INPUT
    probe_path, check_path, main_path = Path(probe_path), Path(check_path), Path(main_path)
    if sha256(probe_path) != probe_sha or sha256(main_path) != main_sha:
        print(json.dumps({"status": "input_error", "reason": "input sha256 differs"}))
        return EXIT_INPUT
    try:
        sys.path.insert(0, str(Path(checkout) / "04_scripts" / "04_hydraulic" / "coupled"))
        import ed6_probe as probe
        import judge_stage1_4368 as path1
        import jp3_j9main_judge as j9judge

        probe.install_probe_switches()
        full = by_plant_key(read_lines(probe_path), FULL_ARM, probe)
        sealed = by_plant_key(read_lines(check_path), SEALED_ARM, probe)
        pairs = []
        for plant_key in sorted(set(full) | set(sealed)):
            a, b = full.get(plant_key), sealed.get(plant_key)
            pairs.append({"plant": plant_key[0], "key": plant_key[1],
                          "a1a2b_sha256": None if a is None else a["commands_sha256"],
                          "a1a2b3_sha256": None if b is None else b["commands_sha256"],
                          "same": a is not None and b is not None
                          and a["commands_sha256"] == b["commands_sha256"],
                          "a1a2b_b1_blocked_periods": None if a is None else sum(
                              leg["b1_blocked_periods"]
                              for leg in a["lsb_record"]["legs"].values())})
        v0 = j9judge.stored_v0_rows(main_path, main_sha)
        import judge4368_common as common

        v0_metrics = j9judge._metric_rows(v0, tuple(common.t4h_folders(main_path, v0)),
                                          relabel=False)
        folders = (probe_path.with_name(f"{probe_path.stem}_t4h"),)
        rows = n_rev_rows(full, folders, v0_metrics, j9judge, path1)
    except Exception:  # every unexpected failure is a tool error (exit 3)
        traceback.print_exc()
        print(json.dumps({"status": "tool_error"}))
        return EXIT_TOOL
    same = sum(pair["same"] for pair in pairs)
    report = {"rule": "spec revision 6 Q6-14: a1a2b3 (B1 out) against a1a2b, commands_sha256",
              "inputs": {"probe": {"path": str(probe_path), "sha256": probe_sha},
                         "check": {"path": str(check_path), "sha256": sha256(check_path)},
                         "v0": {"path": str(main_path), "sha256": main_sha},
                         "code_checkout": str(checkout)},
              "pairs": pairs, "pairs_total": len(pairs), "pairs_same": same,
              "n_rev_a1a2b": rows,
              "l_c_rule": "criteria 4 (jp3_j9main_judge LIMIT_CYCLE_FACTOR / _MARGIN): "
                          "n_rev >= 2 max_V0(group) and n_rev >= max_V0(group) + 6; record",
              "l_c_rule_met": sum(bool(row["l_c_rule_met"]) for row in rows)}
    out_json.write_text(json.dumps(report, indent=1), encoding="utf-8")
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    status = "same" if same == len(pairs) == 40 else "differ"
    print(json.dumps({"status": status, "pairs": len(pairs), "same": same,
                      "l_c_rule_met": report["l_c_rule_met"], "out": str(out_json)}))
    return EXIT_SAME if status == "same" else EXIT_DIFFER


if __name__ == "__main__":
    sys.exit(main(sys.argv))
