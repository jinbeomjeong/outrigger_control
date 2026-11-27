"""436.9 edition 8 stage 4 judgement: independent recount of the gate counts (C axis).

Reads the eight judge outputs at T8'''' 7ea78232 (``j9_runs/56849248/judge_7ea78232``), the
C8 stage outputs they judged (``impl_*_a1``, ``l1ref_a1``; the stage 4 blind list was emptied
on 2026-11-27 after the gate judgement) and the two pinned references. Recounts the core
numbers of each gate with its own code (no judge module is imported) and compares them with the
judge output fields.

The recount implements the rule sentences of ``jp3_remedy_spec_v8_rules.md`` (35f9eba8) 12:
  * P8-0  (361): 114 lines, line-wise ``commands_sha256`` against b46bdf8f, line identity =
    the job without ``mask`` / ``t4h_dir`` (producer resume key).
  * P8-16 (377): per arm, the 27 run hashes against the reference arm (multiset, no key).
  * P8-5 / P8-8 / P8-15 (365 / 368 / 376): on/off pairs per (plant, row), pair selectors as
    the rule text, the minimum pair counts 15 / 5 / 20.
  * P8-1  (362): VBN against VBN0 per job, fallback pairs are records.
  * P8-2  (363): 10 case lines, J-P3 rev 7 breach reads.
  * l1ref: line counts and controller tags of the four L1 files.
It prints and writes counts, booleans and label counters only: never a hash, a metric value or
a line. Field paths are the record keys the producer writes (checked by key names only).

Usage (python-dev or dynamics-dev): python.exe -X utf8 -I -B recount_stage4.py OUT_JSON
Exit: 0 every recount equals the judge output / 1 a difference / 2 an input error.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control")
JP3 = ROOT / "06_analysis" / "02_control" / "j_p3_cause"
RUN = JP3 / "j9_runs" / "56849248"
NEW = RUN / "judge_7ea78232"
OLD = RUN / "judge_2263b246"
REF_P80 = JP3 / "j9_runs" / "b46bdf8f" / "repro_a2" / "ed7_probe_a2.jsonl"
REF_P816 = (JP3 / "ed8_design" / "control_level_deadlock" / "probe_8a2a52ce" / "raw"
            / "runs.jsonl")
JUDGE_HEAD = "7ea782323c427917709ecbb365a58044449beac2"
OLD_HEAD = "2263b2461238da7f93eda147838c01c847315561"
RUN_COMMIT = "56849248371b4916e2fe683265e7abffdd6fb8d7"
SPEC_SHA = "35f9eba8f98f93ddb0fa850ff60844ebd7a443f819febcdf0906a5502c121520"
REF_P80_SHA = "d60306db8073b3ffba285f58e54d8fd9779867d47c4e79e9878d02974f082430"
REF_P816_SHA = "89efe66fc521f6d58c8c90304a9258747eef45d422ef43666a53f5ddd7fa9418"
GATES = ("p80", "p816", "p85", "p88", "p815", "t8", "cases", "l1ref")
PRODUCER_RUNTIME = ("mask", "t4h_dir")                       # run_v5.RUNTIME_JOB_KEYS
PAIR_DROP = ("mask", "t4h_dir", "setting", "_part", "_r79_plan")  # arm-pair row identity
ARMS = {"p85": ("a8", "a8_psw_off"), "p88": ("a8", "a8_h3_off"), "p815": ("a8", "a8_l2_off")}
MIN_PAIRS = {"p85": 15, "p88": 5, "p815": 20}                 # spec 12 365 / 368 / 376
WAIVER_COUNTS = ("n_waiver_done", "n_waiver_periods")
FALLBACK = "WARN_ROD_PRESSURE_FALLBACK"
RULE_OF = {"p85": "P8-5", "p88": "P8-8", "p815": "P8-15"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(text) for text in path.read_text(encoding="utf-8").splitlines()
            if text.strip()]


def is_hash(value) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        c in "0123456789abcdef" for c in value)


def key_without(job: dict, drop: tuple[str, ...]) -> str:
    return json.dumps({k: v for k, v in job.items() if k not in drop}, sort_keys=True)


def t4h_lookup(rows_path: Path):
    folder = rows_path.with_name(f"{rows_path.stem}_t4h")
    cache: dict[str, dict] = {}

    def lookup(line: dict, key: str):
        if key in line:
            return line[key]
        name = line.get("t4h_file")
        if not name or not (folder / str(name)).is_file():
            return None
        if name not in cache:
            import numpy as np
            with np.load(folder / str(name), allow_pickle=False) as data:
                cache[name] = (json.loads(str(data["meta_json"]))
                               if "meta_json" in data.files else {})
        return cache[name].get(key)

    return lookup


# ------------------------------------------------------------------------------ identity
def identity(report: dict, head: str) -> dict:
    inputs = report.get("inputs") or {}
    rows = inputs.get("rows") or {}
    done = Path(rows.get("step_done", ""))
    out = {"status": report.get("status"),
           "head_ok": (report.get("judge_code") or {}).get("head") == head,
           "is_clean": (report.get("judge_code") or {}).get("is_clean") is True,
           "spec_ok": report.get("spec_v8_sha256") == SPEC_SHA,
           "run_commit_ok": rows.get("run_commit") == RUN_COMMIT,
           "step_done_sha_ok": done.is_file() and sha256(done) == rows.get("step_done_sha256"),
           "outputs": len(rows.get("outputs") or []),
           "outputs_sha_ok": all(Path(o["path"]).is_file() and sha256(Path(o["path"])) == o["sha256"]
                                 for o in rows.get("outputs") or [])}
    for name in ("reference", "main_jsonl"):
        if name in inputs:
            block = inputs[name]
            out[f"{name}_sha_ok"] = sha256(Path(block["path"])) == block["sha256"]
            out[f"{name}_pinned"] = block.get("pinned") is True
    return out


# ------------------------------------------------------------------------------ P8-0
def recount_p80(report: dict) -> dict:
    run = read_jsonl(RUN / "impl_p80_a1" / "ed7_probe_a2.jsonl")
    ref = read_jsonl(REF_P80)

    def table(rows):
        table, dup = {}, 0
        for row in rows:
            if "error" in row or not is_hash(row.get("commands_sha256")):
                continue
            key = key_without(row.get("job") or {}, PRODUCER_RUNTIME)
            dup += key in table
            table[key] = row["commands_sha256"]
        return table, dup

    run_t, run_dup = table(run)
    ref_t, ref_dup = table(ref)
    common = set(run_t) & set(ref_t)
    out = {"run_lines": len(run), "reference_lines": len(ref),
           "run_error_lines": sum("error" in r for r in run),
           "run_hashless_lines": sum("error" not in r and not is_hash(r.get("commands_sha256"))
                                     for r in run),
           "run_distinct_keys": len(run_t), "reference_distinct_keys": len(ref_t),
           "run_duplicate_keys": run_dup, "reference_duplicate_keys": ref_dup,
           "equal": sum(run_t[k] == ref_t[k] for k in common),
           "differing": sum(run_t[k] != ref_t[k] for k in common),
           "missing": len(set(ref_t) - set(run_t)), "extra": len(set(run_t) - set(ref_t)),
           "settings_run": dict(sorted(Counter(str((r.get("job") or {}).get("setting"))
                                               for r in run).items())),
           "folded_keys_t8ppp_form": len({key_without(r.get("job") or {}, PAIR_DROP)
                                          for r in run}),
           "reference_sha_ok": sha256(REF_P80) == REF_P80_SHA}
    out["matches_tool"] = (report.get("jobs") == out["reference_distinct_keys"] == 114
                           and report.get("run_jobs") == out["run_distinct_keys"]
                           and report.get("equal") == out["equal"]
                           and len(report.get("differing") or []) == out["differing"]
                           and len(report.get("missing") or []) == out["missing"]
                           and len(report.get("extra") or []) == out["extra"]
                           and report.get("settings_run") == out["settings_run"])
    out["rule_status"] = ("pass" if out["equal"] == 114 and out["differing"] == out["missing"]
                          == out["extra"] == out["run_duplicate_keys"] == 0
                          and out["run_error_lines"] == out["run_hashless_lines"] == 0
                          else "failed")
    return out


# ------------------------------------------------------------------------------ P8-16
def recount_p816(report: dict) -> dict:
    run = read_jsonl(RUN / "impl_p816_a1" / "p816.jsonl")
    ref = read_jsonl(REF_P816)
    run_arm = Counter(str((r.get("ed8_probe") or {}).get("arm")) for r in run)
    ref_arm = Counter(str((r.get("p814") or {}).get("arm")) for r in ref)

    def hashes(rows, arm, field):
        return Counter(r.get("commands_sha256") for r in rows
                       if str((r.get(field) or {}).get("arm")) == arm)

    arm_map = {"B_impl": "B", "L2_impl": "L2"}  # spec 12 P8-16: B arm 27, L2 arm 27
    per_arm = {}
    for run_name, ref_name in arm_map.items():
        a, b = hashes(run, run_name, "ed8_probe"), hashes(ref, ref_name, "p814")
        per_arm[run_name] = {"run_lines": sum(a.values()), "reference_lines": sum(b.values()),
                             "run_hashless": sum(n for h, n in a.items() if not is_hash(h)),
                             "multiset_equal": a == b}
    out = {"run_lines": len(run), "run_arms": dict(sorted(run_arm.items())),
           "reference_arms": dict(sorted(ref_arm.items())), "per_arm": per_arm,
           "reference_sha_ok": sha256(REF_P816) == REF_P816_SHA}
    tool = report.get("counts") or {}
    out["matches_tool"] = (report.get("equal") == 54 and report.get("keys") == 54
                           and all(per_arm[a]["multiset_equal"] and per_arm[a]["run_lines"] == 27
                                   and (tool.get(a) or {}).get("equal") == 27 for a in arm_map))
    out["rule_status"] = "pass" if all(per_arm[a]["multiset_equal"] and per_arm[a]["run_lines"]
                                       == 27 for a in arm_map) else "failed"
    return out


# ------------------------------------------------------------------------------ arm pairs
def scale_list(line, lookup):
    rounds = lookup(line, "probe_stiffness_record")
    if not isinstance(rounds, list) or any(
            not isinstance(e, dict) or "twist_stiffness_scale" not in e for e in rounds):
        return None
    return [e["twist_stiffness_scale"] for e in rounds]


def select(part, on, off, lookup):
    if part == "p85":
        a, b = scale_list(on, lookup), scale_list(off, lookup)
        return None if a is None or b is None else json.dumps(a) == json.dumps(b)
    record = lookup(on, "ed8_record")
    if part == "p88":
        runs = record.get("reapproach_runs") if isinstance(record, dict) else None
        if not isinstance(runs, list) or any(
                not isinstance(r, dict) or "short_run_extended" not in r for r in runs):
            return None
        return not any(r["short_run_extended"] for r in runs)
    waiver = record.get("twist_waiver") if isinstance(record, dict) else None
    if not isinstance(waiver, dict) or any(waiver.get(n) is None for n in WAIVER_COUNTS):
        return None
    if any(isinstance(waiver[n], bool) or not isinstance(waiver[n], int) for n in WAIVER_COUNTS):
        return "malformed"
    return all(waiver[n] == 0 for n in WAIVER_COUNTS)


def recount_pairs(part: str, report: dict) -> dict:
    path = RUN / f"impl_{part}_a1" / f"{part}.jsonl"
    rows = read_jsonl(path)
    lookup = t4h_lookup(path)
    on_arm, off_arm = ARMS[part]
    found: dict[tuple, list] = {}
    for row in rows:
        block = row.get("ed8_probe") or {}
        if block.get("arm") in (on_arm, off_arm):
            key = (block["arm"], str(block.get("plant")), key_without(row.get("job") or {}, PAIR_DROP))
            found.setdefault(key, []).append(row)
    keys = sorted({(p, r) for _, p, r in found})
    pairs, problems = [], 0
    for plant, row in keys:
        on, off = found.get((on_arm, plant, row), []), found.get((off_arm, plant, row), [])
        if len(on) != 1 or len(off) != 1:
            problems += 1
            continue
        pairs.append((on[0], off[0]))
    states = Counter()
    judged = differing = hashless = 0
    for on, off in pairs:
        chosen = select(part, on, off, lookup)
        if chosen is None:
            states["no_record"] += 1
            continue
        if chosen == "malformed":
            states["malformed"] += 1
            continue
        if not chosen:
            states["not_selected"] += 1
            continue
        if not (is_hash(on.get("commands_sha256")) and is_hash(off.get("commands_sha256"))):
            hashless += 1
            continue
        judged += 1
        differing += on["commands_sha256"] != off["commands_sha256"]
    out = {"rule": RULE_OF[part], "lines": len(rows),
           "lines_by_arm": dict(sorted(Counter(str((r.get("ed8_probe") or {}).get("arm"))
                                               for r in rows).items())),
           "pairs": len(pairs), "pairing_problems": problems, "judged_pairs": judged,
           "differing_judged_pairs": differing, "hashless_judged_pairs": hashless,
           "pair_states": dict(sorted(states.items())), "min_pairs": MIN_PAIRS[part]}
    out["matches_tool"] = (report.get("pairs") == out["pairs"]
                           and report.get("judged_pairs") == judged
                           and len(report.get("differing") or []) == differing
                           and len(report.get("unread") or []) == states["no_record"]
                           and len(report.get("malformed") or []) == states["malformed"]
                           and len(report.get("hashless") or []) == hashless
                           and len(report.get("pairing_problems") or []) == problems)
    if differing:
        out["rule_status"] = "failed"
    elif problems or states["malformed"]:
        out["rule_status"] = "setting_defect"
    elif (states["no_record"] and part != "p815") or hashless or judged < MIN_PAIRS[part]:
        out["rule_status"] = "not_judgeable"
    else:
        out["rule_status"] = "pass"
    return out


# ------------------------------------------------------------------------------ P8-1
def recount_t8(report: dict) -> dict:
    rows = read_jsonl(RUN / "impl_t8_a1" / "ed8_t8.jsonl")
    by_job: dict[str, dict] = {}
    for row in rows:
        job = row.get("job") or {}
        by_job.setdefault(key_without(job, ("mask", "t4h_dir", "setting")), {})[
            str(job.get("setting"))] = row

    def fallback(line):
        names = [str(n) for n in line.get("event_names") or []]
        names += [str(e[1]) for e in line.get("events") or [] if len(e) > 1]
        return any(n.startswith(FALLBACK) for n in names)

    complete = [v for v in by_job.values() if set(v) == {"VBN", "VBN0"}]
    records = sum(1 for v in complete if fallback(v["VBN"]) or fallback(v["VBN0"]))
    judged = [v for v in complete if not (fallback(v["VBN"]) or fallback(v["VBN0"]))]
    out = {"lines": len(rows),
           "settings": dict(sorted(Counter(str((r.get("job") or {}).get("setting"))
                                           for r in rows).items())),
           "jobs": len(by_job), "complete_jobs": len(complete), "fallback_pair_records": records,
           "judged_pairs": len(judged),
           "differing_pairs": sum(v["VBN"].get("commands_sha256") != v["VBN0"].get("commands_sha256")
                                  for v in judged)}
    out["matches_tool"] = (report.get("judged_pairs") == out["judged_pairs"]
                           and len(report.get("differing_pairs") or []) == out["differing_pairs"]
                           and len(report.get("fallback_pairs_record") or []) == records)
    out["rule_status"] = ("pass" if out["differing_pairs"] == 0 and out["judged_pairs"] > 0
                          and out["complete_jobs"] == out["jobs"] == 22 else "check")
    return out


# ------------------------------------------------------------------------------ P8-2
def recount_cases(report: dict) -> dict:
    rows = read_jsonl(RUN / "impl_cases_a1" / "ed8_cases.jsonl")
    ebc = [((r.get("hydraulics_record") or {}).get("extend_bound_check")) for r in rows]
    have = [e for e in ebc if isinstance(e, dict)]
    def reads(value) -> int:
        # a count; a list of per-leg counts (their sum); a list of breach entries (its length)
        if isinstance(value, list):
            if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value):
                return int(sum(value))
            return len(value)
        return int(value or 0)

    sums = {name: sum(reads(e.get(name)) for e in have)
            for name in ("jp3a_breach_reads", "jp3b_breach_over_tol_reads", "jp3c_breach_reads")}
    kinds = {name: sorted({type(e.get(name)).__name__ for e in have})
             for name in ("jp3a_breach_reads", "jp3b_breach_over_tol_reads", "jp3c_breach_reads")}
    out = {"lines": len(rows), "error_lines": sum("error" in r for r in rows),
           "settings": dict(sorted(Counter(str((r.get("job") or {}).get("setting"))
                                           for r in rows).items())),
           "cases": dict(sorted(Counter(str((r.get("job") or {}).get("case")) for r in rows).items())),
           "extend_bound_check_records": len(have),
           "rule_revisions": dict(sorted(Counter(str(e.get("rule_revision")) for e in have).items())),
           "breach_read_sums": sums, "breach_read_field_types": kinds}
    rev7 = (report.get("J-P3") or {}).get("rev7") or {}
    out["matches_tool"] = (report.get("J-P3_judged_rows") == 10 == len(have)
                           and rev7.get("runs_judged") == 10
                           and all(rev7.get(k) == v for k, v in sums.items())
                           and (report.get("J-P3") or {}).get("rev7_unjudged_setting_runs") == 0)
    out["rule_status"] = ("pass" if len(have) == 10 and not any(sums.values())
                          and out["error_lines"] == 0 else "check")
    return out


# ------------------------------------------------------------------------------ l1ref
def recount_l1ref(report: dict) -> dict:
    out = {}
    for name in ("L1_VBN0", "L1_VBN", "L1a_VBN0", "L1a_VBN"):
        document = json.loads((RUN / "l1ref_a1" / f"{name}.json").read_text(encoding="utf-8"))
        lists = {k: len(v) for k, v in document.items() if isinstance(v, list)}
        rows = max((v for v in document.values() if isinstance(v, list)), key=len, default=[])
        tags = Counter(str(r.get("controller_tag")) for r in rows if isinstance(r, dict))
        tool = (report.get("runs") or {}).get(name) or {}
        out[name] = {"top_lists": lists, "rows": len(rows), "controller_tags": dict(tags),
                     "tool_lines": tool.get("lines"),
                     "matches_tool": tool.get("lines") == len(rows)
                     and tool.get("controller_tags") == dict(tags)
                     and tool.get("identity_problems") == []}
    out["matches_tool"] = all(v["matches_tool"] for v in out.values() if isinstance(v, dict))
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(json.dumps({"status": "input_error", "reason": "OUT_JSON expected"}))
        return 2
    out_path = Path(argv[0])
    if out_path.exists():
        print(json.dumps({"status": "input_error", "reason": "output exists"}))
        return 2
    try:
        new = {g: json.loads((NEW / f"{g}.json").read_text(encoding="utf-8")) for g in GATES}
        old = {g: json.loads((OLD / f"{g}.json").read_text(encoding="utf-8")) for g in GATES}
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "input_error", "reason": type(exc).__name__}))
        return 2
    result = {"judge_new": {g: identity(new[g], JUDGE_HEAD) for g in GATES},
              "judge_old_status": {g: old[g].get("status") for g in GATES},
              "judge_old_head_ok": {g: (old[g].get("judge_code") or {}).get("head") == OLD_HEAD
                                    for g in GATES},
              "p80_t8ppp_signature": {
                  "status": old["p80"].get("status"), "jobs": old["p80"].get("jobs"),
                  "equal": old["p80"].get("equal"),
                  "differing": len(old["p80"].get("differing") or []),
                  "failures": (old["p80"].get("status_basis") or {}).get("failures"),
                  "setting_defects": (old["p80"].get("status_basis") or {}).get("setting_defects")},
              "p80": recount_p80(new["p80"]), "p816": recount_p816(new["p816"]),
              "p85": recount_pairs("p85", new["p85"]), "p88": recount_pairs("p88", new["p88"]),
              "p815": recount_pairs("p815", new["p815"]), "t8": recount_t8(new["t8"]),
              "cases": recount_cases(new["cases"]), "l1ref": recount_l1ref(new["l1ref"])}
    gate_ok = all(result[g]["matches_tool"] for g in GATES)
    ident_ok = all(v["head_ok"] and v["is_clean"] and v["spec_ok"] and v["run_commit_ok"]
                   and v["step_done_sha_ok"] and v["outputs_sha_ok"]
                   for v in result["judge_new"].values())
    status_ok = all(result[g].get("rule_status", new[g].get("status")) == new[g].get("status")
                    for g in GATES)
    result["summary"] = {"recount_matches_tool": gate_ok, "identity_ok": ident_ok,
                         "rule_status_matches_tool": status_ok,
                         "status": "same" if gate_ok and ident_ok and status_ok else "differs"}
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8",
                        newline="\n")
    print(json.dumps(result["summary"]))
    return 0 if result["summary"]["status"] == "same" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
