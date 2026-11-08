"""Judge of the T-3 targeted check (sealed ``las_targeted_rules_rev3.md`` 3 K-0 .. K-7 and 4
H-T3-0 .. H-T3-6, ``las_targeted_rules_rev4.md`` 1 #1: T-3c fixed at 76); called by
``las_judge.py --stage T-3`` and by ``las_t3.py`` (R-0 gate and the final judge).

Baselines: the composite-key line of ``v5/d1.jsonl`` (its sha256 must be the key list's
``d1_baseline.sha256``) for the D-1 lines, the key list's stored T4h hash
(``shadow_commands_sha256_all_folders``, one value) for the Dg-3 lines. The key list's own
baseline fields are checked against ``d1.jsonl`` first (hash, verdict, P3-2, READY, stroke,
FAULT names); its ``G6-2`` field is None where ``d1.items["G6-2_loc"]`` is true (all 76 T-3c
entries), so K-6 reads the items of ``d1.jsonl`` (rev3 K-6b "d1.items") and the report lists the
field difference as a note.

  K-0  seals (the six sealed files) and every line's ``t3.identity`` = its file header's
  K-1  key set per bundle = the key list (R-0 7, T-3a 228, T-3b 4, T-3c 76); no error left
       after the one retry (H-T3-2)
  K-2  R-0: hash = baseline, controller tag without ``_LAS`` (V0 none, VB ``final_C4G2_P3``;
       Dg-3: as its folder), LAS-b off and not fired
  K-3  T-3: tag = ``final_C4G2_LAS`` (V0, Dg-3 off) / ``final_C4G2_P3_LAS`` (VB, Dg-3 v4_on),
       ``_FB`` fails; Dg-3 also its folder's ③ start rule
  K-4  T-3a G1 uniform 72 + T-3b 4: not fired and hash = baseline
  K-5  every T-3 line that did not fire: hash = baseline
  K-6  every fired T-3 D-1 line: ``las_h7.h7_violations`` with the J-1 format (C2, C3, C4'
       G6-2, P3-2, C5'-R READY, C5'-S stroke; a missing value fails as rev4 2)
  K-7  table of the fired lines (start, leg, end, active / scaled periods, LOC - t_off,
       Delta F_judged_min, start rho); a record, not a criterion
Stops: H-T3-0 (K-0), H-T3-3 (K-1 key set, K-3), H-T3-2 (errors), H-T3-1 (K-2), H-T3-4 (K-4),
H-T3-5 (K-5), H-T3-6 (K-6). Exit codes: 0 passed, 1 a criterion failed (K-2, K-4 .. K-6), 2 a
stop without a verdict (H-T3-0, H-T3-2, H-T3-3) or an input error.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import las_h7
import las_t3
import las_targeted as lt

TAG_V0_LAS = "final_C4G2_LAS"
TAG_P3 = "final_C4G2_P3"
TAG_P3_LAS = "final_C4G2_P3_LAS"
"""``v5_options`` tags (``LAS_CONTROLLER_TAG``, ``EXTEND_START_CONTROLLER_TAG``,
``EXTEND_START_LAS_CONTROLLER_TAG``)."""
FB_TAG_TOKEN = "_FB"
IDENTITY_KEYS = ("git_head", "sha256", "c2_sha256", "threads", "workers", "affinity")
UNIFORM_G1 = "G1"
NO_VERDICT_STOPS = ("H-T3-0", "H-T3-2", "H-T3-3")
STOP_ORDER = ("H-T3-0", "H-T3-3", "H-T3-2", "H-T3-1", "H-T3-4", "H-T3-5", "H-T3-6")
CRITERION_STOP = {"K-0": "H-T3-0", "K-1": "H-T3-3", "K-3": "H-T3-3", "errors": "H-T3-2",
                  "K-2": "H-T3-1", "K-4": "H-T3-4", "K-5": "H-T3-5", "K-6": "H-T3-6"}


# ------------------------------------------------------------------------------- input
def read_jsonl(path: Path) -> tuple[dict | None, list[dict]]:
    """(header, result lines) of a T-3 file."""
    header, lines = None, []
    for text in path.read_text(encoding="utf-8").splitlines():
        if not text.strip():
            continue
        record = json.loads(text)
        if "header" in record:
            header = record["header"]
        else:
            lines.append(record)
    return header, lines


def line_key(line: dict) -> str:
    return line["t3"]["line_key"]


def good_lines(lines: list[dict]) -> tuple[dict[str, dict], list[str]]:
    """(line key -> last error-free line, keys whose every line is an error)."""
    good = {line_key(line): line for line in lines if "error" not in line}
    errors = sorted({line_key(line) for line in lines if "error" in line} - set(good))
    return good, errors


def load_baseline(path: Path) -> dict[str, dict]:
    return lt.load_baseline(path)


def baseline_hash(entry: dict, baseline: dict[str, dict]) -> str | None:
    if entry["kind"] == las_t3.KIND_D1:
        record = baseline.get(entry["line_key"])
        return None if record is None else record["commands_sha256"]
    hashes = entry.get("shadow_commands_sha256_all_folders") or []
    return hashes[0] if len(hashes) == 1 else None


def expected_tag(entry: dict, line: dict, is_las_on: bool) -> str | None:
    """Rev3 2.2: the tag of a T-3 line (LAS-b on) or of an R-0 line (off)."""
    if entry["kind"] == las_t3.KIND_D1:
        is_p3 = line["job"]["setting"] == "VB"
    else:
        is_p3 = entry["folder"] == "v4_on"
    if is_las_on:
        return TAG_P3_LAS if is_p3 else TAG_V0_LAS
    return TAG_P3 if is_p3 else None


def is_fired(line: dict) -> bool:
    return bool((line.get("las_t3") or {}).get("fired"))


# ------------------------------------------------------------------------------- checks
def identity_problems(label: str, header: dict | None, lines: list[dict]) -> list[str]:
    """K-0: every line's identity equals the header's."""
    if header is None:
        return [f"{label}: no header line"]
    reference = header.get("identity") or {}
    problems = []
    for line in lines:
        identity = (line.get("t3") or {}).get("identity") or {}
        differing = [key for key in IDENTITY_KEYS if identity.get(key) != reference.get(key)]
        if differing:
            problems.append(f"{label} {line_key(line)}: {differing} differ from the header")
    return problems


def key_list_problems(keys: dict, entries: dict[str, list[dict]], baseline: dict[str, dict],
                      baseline_path: Path) -> tuple[list[str], list[str]]:
    """(problems, notes) of the key list against ``d1.jsonl``."""
    problems, notes = [], []
    digest = hashlib.sha256(baseline_path.read_bytes()).hexdigest()
    if digest != keys["d1_baseline"]["sha256"]:
        problems.append(f"d1.jsonl sha256 {digest} != key list {keys['d1_baseline']['sha256']}")
    g62_differences = 0
    for bundle in ("T-3a", "T-3c"):
        for entry in entries[bundle]:
            record = baseline.get(entry["line_key"])
            if record is None:
                problems.append(f"{entry['line_key']}: no d1.jsonl line")
                continue
            problems += _entry_differences(entry, record)
            if entry.get("G6-2") != record["d1"]["items"].get("G6-2_loc"):
                g62_differences += 1
    for entry in entries[las_t3.R0] + entries["T-3b"]:
        if entry["kind"] == las_t3.KIND_DG3 and baseline_hash(entry, baseline) is None:
            problems.append(f"{entry['line_key']}: not one stored T4h hash")
    if g62_differences:
        notes.append(f"key list G6-2 field differs from d1.items G6-2_loc on {g62_differences} "
                     f"entries (K-6 reads d1.jsonl)")
    return problems, notes


def _entry_differences(entry: dict, record: dict) -> list[str]:
    d1 = record["d1"]
    faults = sorted(name for name in (record.get("event_names") or {})
                    if name.startswith(las_h7.FAULT_PREFIX))
    pairs = {"commands_sha256": (entry["commands_sha256"], record["commands_sha256"]),
             "verdict": (entry["verdict"], d1["verdict"]),
             "P3-2": (entry["P3-2"], d1["items"].get("P3-2")),
             "t_ready_s": (entry["t_ready_s"], d1["t_ready_s"]),
             "stroke_max_m": (entry["stroke_max_m"], d1["stroke_max_m"]),
             "fault_names": (sorted(entry["fault_names"]), faults)}
    return [f"{entry['line_key']}: key list {name} {a!r} != d1.jsonl {b!r}"
            for name, (a, b) in pairs.items() if a != b]


def key_set_problems(bundle: str, entries: list[dict], good: dict[str, dict],
                     all_lines: list[dict]) -> list[str]:
    """K-1 of a bundle (an empty expected set is never a pass)."""
    expected = {entry["line_key"] for entry in entries}
    have = {key for key, line in good.items() if line["t3"]["bundle"] == bundle}
    seen = {line_key(line) for line in all_lines if line["t3"]["bundle"] == bundle}
    problems = []
    if not expected:
        problems.append(f"{bundle}: empty key set")
    missing, extra = sorted(expected - have), sorted(seen - expected)
    if missing:
        problems.append(f"{bundle}: {len(missing)} keys without a good line {missing[:3]}")
    if extra:
        problems.append(f"{bundle}: {len(extra)} keys not in the key list {extra[:3]}")
    return problems


def tag_problems(entry: dict, line: dict, is_las_on: bool) -> list[str]:
    """K-3 (T-3) / the tag part of K-2 (R-0) for one line."""
    tag = line.get("controller_tag")
    problems = []
    if tag is not None and FB_TAG_TOKEN in tag:
        problems.append(f"tag {tag} has {FB_TAG_TOKEN}")
    wanted = expected_tag(entry, line, is_las_on)
    if tag != wanted:
        problems.append(f"tag {tag} != {wanted}")
    las_enable = (line.get("las_t3") or {}).get("enable")
    if bool(las_enable) != is_las_on:
        problems.append(f"LAS-b enable {las_enable}")
    if entry["kind"] == las_t3.KIND_DG3:
        rule = line.get("extend_start_rule")
        if rule != las_t3.DG3_RULE_OF_FOLDER[entry["folder"]]:
            problems.append(f"③ start rule {rule} != folder {entry['folder']}")
    return problems


def hash_problem(entry: dict, line: dict, baseline: dict[str, dict]) -> str | None:
    stored = baseline_hash(entry, baseline)
    new = line.get("commands_sha256")
    if stored is not None and new == stored:
        return None
    return f"hash {str(new)[:12]} != baseline {str(stored)[:12]}"


def k7_row(entry: dict, line: dict, baseline: dict[str, dict]) -> dict:
    las = line.get("las_t3") or {}
    row = {"key": entry["line_key"], "start_s": las.get("start_s"),
           "start_leg": las.get("start_leg"), "end_reason": las.get("end_reason"),
           "active_periods": las.get("active_periods"),
           "scaled_periods": las.get("scaled_periods"),
           "loc_minus_t_off_s": las.get("loc_minus_t_off_s"),
           "start_rho": las.get("start_rho"), "events": las.get("events")}
    record = baseline.get(entry["line_key"]) if entry["kind"] == las_t3.KIND_D1 else None
    if record is not None and "d1" in line:
        new_f, base_f = line["d1"].get("F_judged_min_N"), record["d1"].get("F_judged_min_N")
        row["dF_judged_min_N"] = None if None in (new_f, base_f) else new_f - base_f
    return row


# ------------------------------------------------------------------------------- R-0
def r0_criteria(lines: list[dict], entries: list[dict], baseline: dict[str, dict]) -> dict:
    """K-1 (R-0), errors and K-2 of the R-0 lines: ``criterion -> problems``."""
    good, errors = good_lines(lines)
    k2 = {}
    for entry in entries:
        line = good.get(entry["line_key"])
        if line is None:
            continue
        found = tag_problems(entry, line, is_las_on=False)
        problem = hash_problem(entry, line, baseline)
        if problem:
            found.append(problem)
        if is_fired(line):
            found.append("fired")
        if found:
            k2[entry["line_key"]] = found
    return {"K-1": key_set_problems(las_t3.R0, entries, good, lines),
            "errors": errors, "K-2": k2}


def first_stop(criteria: dict) -> str | None:
    stops = {CRITERION_STOP[name] for name, found in criteria.items() if found}
    return next((stop for stop in STOP_ORDER if stop in stops), None)


def r0_gate(lines: list[dict], entries: list[dict], baseline_path: Path) -> dict:
    """The run's R-0 gate: T-3 starts only without a stop (H-T3-1 / H-T3-2 / H-T3-3)."""
    criteria = r0_criteria(lines, entries, load_baseline(baseline_path))
    return {"criteria": criteria, "stop": first_stop(criteria)}


# ------------------------------------------------------------------------------- T-3
def t3_criteria(lines: list[dict], entries: dict[str, list[dict]],
                baseline: dict[str, dict]) -> tuple[dict, list[dict]]:
    """K-1 (T-3 bundles), errors, K-3 .. K-6 and the K-7 rows."""
    good, errors = good_lines(lines)
    criteria = {"K-1": [], "errors": errors, "K-3": {}, "K-4": {}, "K-5": {}, "K-6": {}}
    k7 = []
    for bundle in las_t3.T3_BUNDLES:
        criteria["K-1"] += key_set_problems(bundle, entries[bundle], good, lines)
        for entry in entries[bundle]:
            line = good.get(entry["line_key"])
            if line is None:
                continue
            _judge_t3_line(bundle, entry, line, baseline, criteria)
            if is_fired(line):
                k7.append(k7_row(entry, line, baseline))
    return criteria, k7


def _is_k4_line(bundle: str, entry: dict) -> bool:
    return bundle == "T-3b" or (bundle == "T-3a" and entry.get("base") == UNIFORM_G1)


def _judge_t3_line(bundle: str, entry: dict, line: dict, baseline: dict[str, dict],
                   criteria: dict) -> None:
    key = entry["line_key"]
    found = tag_problems(entry, line, is_las_on=True)
    if found:
        criteria["K-3"][key] = found
    fired = is_fired(line)
    hash_issue = hash_problem(entry, line, baseline)
    if _is_k4_line(bundle, entry) and (fired or hash_issue):
        criteria["K-4"][key] = "fired" if fired else hash_issue
    if not fired and hash_issue:
        criteria["K-5"][key] = hash_issue
    if fired and entry["kind"] == las_t3.KIND_D1:
        violations = las_h7.h7_violations(line, baseline[key], las_h7.D1_FORMAT)
        if violations:
            criteria["K-6"][key] = violations


def judge_t3(r0_path: Path, t3_path: Path, keys_path: Path, baseline_path: Path,
             rules_dir: Path) -> dict:
    """The T-3 verdict (module docstring).

    Raises:
        OSError, KeyError, ValueError: An input file is missing or not of this form.
    """
    keys = las_t3.load_key_list(keys_path)
    entries = las_t3.bundle_entries(keys)
    baseline = load_baseline(baseline_path)
    r0_header, r0_lines = read_jsonl(r0_path)
    t3_header, t3_lines = read_jsonl(t3_path)
    seals = lt.seal_problems(rules_dir, las_t3.T3_REQUIRED_SEALS)
    list_problems, notes = key_list_problems(keys, entries, baseline, baseline_path)
    k0 = seals + list_problems + las_t3.count_problems(entries)
    k0 += identity_problems("R-0", r0_header, r0_lines)
    k0 += identity_problems("T-3", t3_header, t3_lines)
    if r0_header and t3_header and r0_header.get("identity") != t3_header.get("identity"):
        k0.append("R-0 and T-3 headers have other identities")
    for label, header in (("R-0", r0_header), ("T-3", t3_header)):
        if header and header.get("keys_subset"):
            k0.append(f"{label}: a --keys subset run is not a T-3 verdict")
    r0 = r0_criteria(r0_lines, entries[las_t3.R0], baseline)
    t3, k7 = t3_criteria(t3_lines, entries, baseline)
    criteria = {"K-0": k0, "K-1": r0["K-1"] + t3["K-1"], "errors": r0["errors"] + t3["errors"],
                "K-2": r0["K-2"], "K-3": t3["K-3"], "K-4": t3["K-4"], "K-5": t3["K-5"],
                "K-6": t3["K-6"]}
    stops = [CRITERION_STOP[name] for name, found in criteria.items() if found]
    counts = {"R-0": len(good_lines(r0_lines)[0]),
              **{bundle: sum(line["t3"]["bundle"] == bundle
                             for line in good_lines(t3_lines)[0].values())
                 for bundle in las_t3.T3_BUNDLES}}
    fired = sorted(row["key"] for row in k7)
    return {"stage": "T-3", "criteria": criteria,
            "passed": {name: not found for name, found in criteria.items()},
            "stops": sorted(set(stops), key=STOP_ORDER.index), "counts": counts,
            "fired": fired, "fired_count": len(fired),
            "silent_count": sum(counts.values()) - counts["R-0"] - len(fired),
            "k7": k7, "notes": notes, "format_absent_k6": las_h7.D1_FORMAT.absent,
            "seals": {name: lt.SEALS[name].sha256 for name in las_t3.T3_REQUIRED_SEALS},
            "identity": (t3_header or r0_header or {}).get("identity")}


def exit_code(result: dict) -> int:
    if any(stop in NO_VERDICT_STOPS for stop in result["stops"]):
        return 2
    return 1 if result["stops"] else 0


# ------------------------------------------------------------------------------- report
def _cell(text) -> str:
    return str(text).replace("|", "\\|")


def report_lines(result: dict) -> list[str]:
    lines = ["# LAS T-3 judge (rules rev3 3 / 4, rev4 1 #1)", "",
             f"lines per bundle: {result['counts']}; fired {result['fired_count']}, "
             f"silent {result['silent_count']}", "",
             "| criterion | result | problems |", "|---|---|---|"]
    for name, found in result["criteria"].items():
        count = len(found)
        lines.append(f"| {name} | {'ok' if not found else 'NG'} | {count} |")
    lines.append("")
    for name, found in result["criteria"].items():
        items = found.items() if isinstance(found, dict) else ((None, f) for f in found)
        for key, problem in items:
            prefix = f"`{_cell(key)}`: " if key is not None else ""
            lines.append(f"- {name} {prefix}{_cell(problem)}")
    if result["k7"]:
        lines += ["", "## K-7 fired lines", "",
                  "| key | start s | leg | end | active | scaled | LOC-t_off s | dF kN | rho |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for row in result["k7"]:
            d_f = row.get("dF_judged_min_N")
            lines.append(
                f"| `{_cell(row['key'])}` | {row['start_s']} | {row['start_leg']} | "
                f"{row['end_reason']} | {row['active_periods']} | {row['scaled_periods']} | "
                f"{row['loc_minus_t_off_s']} | {'-' if d_f is None else f'{d_f / 1e3:.3f}'} | "
                f"{row['start_rho']} |")
    for note in result["notes"]:
        lines.append(f"- note: {note}")
    lines.append(f"- K-6 criteria without a field in the J-1 format: "
                 f"{result['format_absent_k6'] or 'none'}")
    lines.append(f"result: stops {result['stops'] or 'none'}")
    return lines


def main_t3(args) -> int:
    """``las_judge.py --stage T-3 <las_T3.jsonl> --r0 <las_T3_R0.jsonl> ...``."""
    out_dir = args.jsonl.parent
    r0_path = args.r0 or out_dir / las_t3.R0_FILE
    keys_path = args.keys or las_t3.KEYS_PATH
    rules_dir = (args.rules.parent if args.rules is not None else las_t3.RULES_DIR)
    try:
        result = judge_t3(r0_path, args.jsonl, keys_path, args.baseline, rules_dir)
        text = "\n".join(report_lines(result)) + "\n"
        if args.out is not None:
            with args.out.open("x", encoding="utf-8") as handle:
                handle.write(text)
        if args.json_out is not None:
            with args.json_out.open("x", encoding="utf-8") as handle:
                handle.write(json.dumps(result, indent=1, default=str))
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"stage": "T-3", "error": repr(exc)}))
        return 2
    print(text, end="")
    print(json.dumps({key: result[key] for key in ("stage", "stops", "counts", "fired_count",
                                                   "passed")}))
    return exit_code(result)
