"""Path-2 recount of H-3 (U-3) and H-4 (U-6 + IND_LAS record column), 436.8 v5 resume.

Rules: ``u3_u6_rerun_rules.md`` (8de31882...) + rev1 (2c5e6921...) + rev2 (be1584a4...), read through the 436.8
rules 7.1 "rev3 share" (tags V0 ``final_C4G2_LAS_K1``, VB C2 ``final_C4G2_P3_LAS_K1``, ABL ``ABL_LAS_K1``,
IND ``IND``, IND_LAS ``IND_LAS``; D-1 reuse input ``resume_k1/h1_d1.jsonl``; folder ``v5_rerun/las_k1/``).
Author: dynamics-expert (path 2). The path-1 tools (u3_judge, u3_judge_k1, resume4368_judge) and their
outputs were not opened (436.8 9.2).

U-3 (rule section): G-1 run errors 0 and key counts (2: 1,114 keys x V0 / VB, per-suite counts where the
suite name is known), G-2 meta fields and tags (7, rev2 4: one tag per file), G-4 J-P3 on every VB run
selected by file setting, not by tag (rev1 4, rev2 5: selected count = VB key count), G-6 g8 VB rod
fallback events 0 (rev1 5), 5.1 V0 -> VB grade transition table, VB-unique fail (G-5), differences,
bundle sentence counts, 6 D-1 reuse records (Q-1, tag carried from the D-1 line, hash equal).
G-3 (option-free path identity) needs extra runs and is not recounted here.

U-6 (3, 5.2, rev2 3): per controller (C2 / ABL / IND, and the IND_LAS record column) counts of lite pass,
official verdicts, C2 safe stops, crawler_liftoff_fail; G-1 242 cases per controller, G-2 tags; IND_LAS
command hash = IND hash count (rev2 3, record).

Exit codes: 0 no stop / nothing undecidable, 1 undecidable grade or a G-5 VB-unique fail, 2 a gate stop
(G-1 / G-2 / G-4 / G-6) or a rules sha mismatch, 3 tool error.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import importlib.util
import json
import sys
import traceback
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("p2_4368_core", _HERE / "p2_4368.py")
core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(core)

TOOL_NAME = "p2_u3.py"
TOOL_VERSION = "1"
U3_RULES = {
    "06_analysis/02_control/verif_matrix/u3_u6_rerun_rules.md": "8de318825764114ad14afcec362c87c1e01a2ad47195b8491b1c96056e1960b3",
    "06_analysis/02_control/verif_matrix/u3_u6_rerun_rules_rev1.md": "2c5e69213b29fc930c478306676efc72b515d67af08634adab3eba2d05f5f15d",
    "06_analysis/02_control/verif_matrix/u3_u6_rerun_rules_rev2.md": "be1584a4448d68a30c4fe9ec613d3d7b3cb0b47169c2f5eff72e9a9ca0776880",
}
U3_TOTAL = 1114
U3_SUITES = {"slope": 110, "h6": 26, "h9": 24, "g6": 116, "g8": 516, "p3b": 171}   # 2 (names of the stored suites)
U3_OTHER = 84 + 34 + 33          # study B, C, D: suite names not fixed by the rules text
ROD_SUITES = {"g8"}              # rev1 1
TAG = {"V0": core.TAG_V0, "VB": core.TAG_VB, "C2": core.TAG_VB, "ABL": core.TAG_ABL, "IND": core.TAG_IND,
       "IND_LAS": core.TAG_IND_LAS}
U6_CASES = 242                   # 3: wide 226 + main 16
GRADES = ("pass", "flag", "safe_stop", "fail")
META_FIELDS = ("v5_setting", "controller_tag", "definition_sha256", "code", "head_only_declared", "has_rod_reading")


def records_of(path):
    """(suite, key, rec) of a U-3 / U-6 output file: wrapper ``records[]`` (id) or screen ``results[]`` (key)."""
    data = json.loads(Path(path).read_text("utf-8"))
    stem_suite = Path(path).stem
    if isinstance(data.get("records"), list):
        for r in data["records"]:
            yield r.get("suite") or stem_suite, r.get("id") or r.get("case") or r.get("key"), r, data
    elif isinstance(data.get("results"), list):
        for r in data["results"]:
            yield r.get("suite") or stem_suite, r.get("key") or r.get("id"), r, data


def v5_of(rec):
    return rec.get("v5") if isinstance(rec.get("v5"), dict) else {}


def grade_u3(rec):
    """(grade, why): pass / flag / safe_stop / fail, None = undecidable (rules 4, 5.1 four grades)."""
    v = rec.get("verdict")
    if v is None and isinstance(rec.get("pass"), bool):
        v = "pass" if rec["pass"] else "fail"
    if v == "pass":
        flag = bool(rec.get("flags")) or core.dig(rec, "late_loc_reapproach.is_flag", False) is True
        return ("flag" if flag else "pass"), None
    if v == "stroke_limited_stop":
        ss = rec.get("soil_stop")
        if isinstance(ss, dict) and ss.get("pass") is False:
            return "fail", "stroke_limited_stop with soil_stop.pass false"
        return "safe_stop", None
    if v == "fail":
        return "fail", None
    return None, f"verdict {v!r} has no path-2 grade (e.g. settle v2 re-judgement not recorded)"


def ndiff(a, b):
    return None if a is None or b is None else b - a


def att_max(x):
    if isinstance(x, (list, tuple)) and x and all(isinstance(y, (int, float)) for y in x):
        return max(abs(y) for y in x)
    return core.num(x)


def recount_u3(files, h1_path, is_p3):
    fnd = core.Findings()
    sets = {"V0": {}, "VB": {}}
    per_file = []
    for f in files:
        setting = f["setting"]
        n = 0
        tags = set()
        for suite, key, rec, data in records_of(f["path"]):
            n += 1
            where = f"U-3:{Path(f['path']).name}:{suite}|{key}"
            if "error" in rec:
                fnd.stop("G-1", where, "run error")
                continue
            k = f"{suite}|{key}"
            if k in sets[setting]:
                fnd.stop("G-1", where, "duplicate key")
            sets[setting][k] = (suite, rec)
            v5 = v5_of(rec)
            miss = [m for m in META_FIELDS if m not in v5]
            if miss:
                fnd.stop("G-2", where, f"v5 meta missing {miss}")
            tag = v5.get("controller_tag")
            tags.add(tag)
            if tag != TAG[setting]:
                fnd.stop("G-2", where, f"tag {tag!r} != {TAG[setting]!r}")
            elif is_p3 is not None and is_p3(tag) != (setting == "VB"):
                fnd.stop("G-2", where, f"is_extend_start_tag({tag}) wrong for {setting}")
            if v5.get("v5_setting") not in (None, setting):
                fnd.stop("G-2", where, f"v5_setting {v5.get('v5_setting')!r} in a {setting} file")
        if len(tags) > 1:
            fnd.stop("G-2", Path(f["path"]).name, f"{len(tags)} tags in one file {sorted(map(str, tags))}")
        per_file.append({"path": f["path"], "sha256": core.sha256_file(f["path"]), "setting": setting, "records": n})
    # G-1 counts
    counts = {}
    for s in ("V0", "VB"):
        by = {}
        for k, (suite, _) in sets[s].items():
            by[suite] = by.get(suite, 0) + 1
        counts[s] = by
        if len(sets[s]) != U3_TOTAL:
            fnd.stop("G-1", s, f"{len(sets[s])} keys, rules say {U3_TOTAL}")
        for suite, want in U3_SUITES.items():
            if by.get(suite, 0) != want:
                fnd.stop("G-1", f"{s}:{suite}", f"{by.get(suite, 0)} keys, rules say {want}")
        other = sum(v for k, v in by.items() if k not in U3_SUITES)
        if other != U3_OTHER:
            fnd.stop("G-1", f"{s}:B+C+D", f"{other} keys in other suites {sorted(set(by) - set(U3_SUITES))}, rules say {U3_OTHER}")
    if set(sets["V0"]) != set(sets["VB"]):
        fnd.stop("G-1", "pairs", f"V0 / VB key sets differ ({len(set(sets['V0']) ^ set(sets['VB']))})")
    # G-4 / G-6 on every VB run selected by file setting
    sel = 0
    for k, (suite, rec) in sets["VB"].items():
        sel += 1
        v5 = v5_of(rec)
        where = f"VB:{k}"
        if suite in ROD_SUITES:
            if not (v5.get("has_rod_reading") is True and v5.get("j_p3") == "pass"):
                fnd.stop("G-4", where, f"g8: has_rod_reading {v5.get('has_rod_reading')!r}, J-P3 {v5.get('j_p3')!r}")
            fb = v5.get("rod_pressure_fallback_events")
            nfb = len(fb) if isinstance(fb, list) else (fb if isinstance(fb, int) else None)
            if nfb is None:
                fnd.stop("G-6", where, "rod_pressure_fallback_events missing")
            elif nfb != 0:
                fnd.stop("G-6", where, f"{nfb} WARN_ROD_PRESSURE_FALLBACK")
        else:
            if not (v5.get("j_p3") == "no_rod_reading" and v5.get("head_only_declared") is True
                    and v5.get("has_rod_reading") is False):
                fnd.stop("G-4", where, f"head-only: J-P3 {v5.get('j_p3')!r}, declared {v5.get('head_only_declared')!r}, "
                                       f"rod {v5.get('has_rod_reading')!r}")
    if sel != len(sets["VB"]) or sel == 0:
        fnd.stop("G-4", "VB", f"selected {sel} VB runs (empty set or count mismatch)")
    # 5.1 transitions
    table = {a: {b: 0 for b in GRADES + ("undecidable",)} for a in GRADES + ("undecidable",)}
    vb_unique, base_fail, improve, safe_moves, undec, diffs = [], [], [], [], [], {}
    sentence = {g: 0 for g in GRADES}
    for k in sorted(set(sets["V0"]) & set(sets["VB"])):
        r0, r1 = sets["V0"][k][1], sets["VB"][k][1]
        g0, w0 = grade_u3(r0)
        g1, w1 = grade_u3(r1)
        table[g0 or "undecidable"][g1 or "undecidable"] += 1
        if g1 is None:
            undec.append({"key": k, "why": w1})
            fnd.undec(f"VB:{k}", w1)
        else:
            sentence[g1] += 1
        if g1 == "fail" and g0 in ("pass", "flag", "safe_stop"):
            vb_unique.append(k)
            fnd.stop("G-5", k, f"VB-unique fail (V0 {g0})")
        elif g1 == "fail" and g0 == "fail":
            base_fail.append(k)
        elif g0 == "fail" and g1 in ("pass", "flag", "safe_stop"):
            improve.append(k)
        if {g0, g1} == {"pass", "safe_stop"}:
            safe_moves.append(k)
        diffs[k] = {"t_ready_s": ndiff(core.num(r0.get("t_ready_s")), core.num(r1.get("t_ready_s"))),
                    "min_force_kN": ndiff(core.num(r0.get("min_force_kN")), core.num(r1.get("min_force_kN"))),
                    "max_stroke_mm": ndiff(core.num(r0.get("max_stroke_mm")), core.num(r1.get("max_stroke_mm"))),
                    "rut_ready_mm": ndiff(core.num(r0.get("rut_ready_mm")), core.num(r1.get("rut_ready_mm"))),
                    "att_end_deg": ndiff(att_max(r0.get("att_end_deg")), att_max(r1.get("att_end_deg")))}
    # 6 D-1 reuse
    reuse = {"n": 0, "checked": 0, "problems": []}
    d1_index = {}
    if h1_path:
        for line in core.read_jsonl(h1_path):
            d1_index.setdefault(core.dig(line, "job.d1.key", None), []).append(line)
    for s in ("V0", "VB"):
        for k, (suite, rec) in sets[s].items():
            if rec.get("reuse") != "d1" and v5_of(rec).get("reuse") != "d1":
                continue
            reuse["n"] += 1
            dkey = rec.get("reuse_key") or rec.get("d1_key") or v5_of(rec).get("reuse_d1_key")
            cands = [x for x in d1_index.get(dkey, []) if x.get("job", {}).get("setting") == s
                     and core.same_value(x.get("job", {}).get("eps"), 0.0)]
            if len(cands) != 1:
                reuse["problems"].append({"key": k, "setting": s, "why": f"{len(cands)} D-1 eps-0 lines for {dkey!r}"})
                continue
            reuse["checked"] += 1
            if cands[0].get("controller_tag") != v5_of(rec).get("controller_tag"):
                reuse["problems"].append({"key": k, "setting": s, "why": "tag not carried from the D-1 line"})
            if cands[0].get("commands_sha256") != v5_of(rec).get("commands_sha256"):
                reuse["problems"].append({"key": k, "setting": s, "why": "commands_sha256 differs from the D-1 line"})
    if reuse["problems"]:
        fnd.fail("D-1 reuse", f"{len(reuse['problems'])} reuse problem(s)")
    out = {"files": per_file, "counts": counts, "transition": table, "vb_unique_fail": vb_unique,
           "baseline_fail": base_fail, "vb_improve": improve, "pass_safe_stop_moves": safe_moves,
           "undecidable": undec, "sentence_VB": sentence, "differences": diffs, "d1_reuse": reuse,
           "G-3": "not recounted (needs option-free runs; path 1 record only)"}
    return out, fnd


def recount_u6(files, is_p3):
    fnd = core.Findings()
    cols = {}
    hashes = {}
    for f in files:
        for _suite, key, rec, data in records_of(f["path"]):
            ctrl = rec.get("controller") or f.get("controller")
            if f.get("controller") == "IND_LAS":
                ctrl = "IND_LAS"
            where = f"U-6:{Path(f['path']).name}:{key}|{ctrl}"
            if "error" in rec:
                fnd.stop("G-1", where, "run error")
                continue
            c = cols.setdefault(ctrl, {"cases": set(), "lite_pass": 0, "official": {}, "crawler_liftoff_fail": 0,
                                       "safe_stop": 0, "tags": set()})
            if key in c["cases"]:
                fnd.stop("G-1", where, "duplicate case")
            c["cases"].add(key)
            c["lite_pass"] += rec.get("lite_pass") is True
            ov = rec.get("official_verdict")
            c["official"][str(ov)] = c["official"].get(str(ov), 0) + 1
            c["crawler_liftoff_fail"] += rec.get("crawler_liftoff_fail") is True
            c["safe_stop"] += ov == "stroke_limited_stop"
            tag, _ = core.first_path(rec, ("v5.controller_tag", "controller_tag"))
            tag = None if tag is core.MISSING else tag
            c["tags"].add(tag)
            want = TAG.get(ctrl)
            if want is None or tag != want:
                fnd.stop("G-2", where, f"tag {tag!r} != {want!r}")
            elif is_p3 is not None and is_p3(tag) != (ctrl == "C2"):
                fnd.stop("G-2", where, "③ only on C2")
            hashes[(key, ctrl)] = rec.get("commands_sha256") or core.dig(rec, "v5.commands_sha256", None)
    for ctrl in ("C2", "ABL", "IND", "IND_LAS"):
        n = len(cols.get(ctrl, {}).get("cases", ()))
        if n != U6_CASES:
            fnd.stop("G-1", ctrl, f"{n} cases, rules say {U6_CASES}")
    if cols.get("IND_LAS") and cols.get("IND") and cols["IND_LAS"]["cases"] != cols["IND"]["cases"]:
        fnd.stop("G-1", "IND_LAS", "case set differs from IND (rev2 3)")
    same = sum(1 for (k, c), h in hashes.items() if c == "IND_LAS" and h and h == hashes.get((k, "IND")))
    table = {c: {"cases": len(v["cases"]), "lite_pass": v["lite_pass"], "official": v["official"],
                 "crawler_liftoff_fail": v["crawler_liftoff_fail"],
                 "safe_stop": v["safe_stop"] if c == "C2" else None, "tags": sorted(map(str, v["tags"]))}
             for c, v in cols.items()}
    # IND_LAS failures are records, never a stop (rev2 3): only G-1 / G-2 apply to that column
    return {"table": table, "IND_LAS_hash_equal_to_IND": same, "judged_runs": sum(
        len(cols.get(c, {}).get("cases", ())) for c in ("C2", "ABL", "IND"))}, fnd


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--u3", action="append", default=[], help="SETTING=path (SETTING V0 or VB), repeatable")
    ap.add_argument("--u6", action="append", default=[], help="CONTROLLER=path (C2|ABL|IND|IND_LAS|ALL), repeatable")
    ap.add_argument("--h1", default=None, help="resume_k1/h1_d1.jsonl for the D-1 reuse check")
    args = ap.parse_args(argv)
    repo = Path(args.repo) if args.repo else _HERE.parents[4]
    tool_sha = core.sha256_file(Path(__file__))
    summary = {"tool": TOOL_NAME, "version": TOOL_VERSION, "tool_sha256": tool_sha,
               "core_sha256": core.sha256_file(_HERE / "p2_4368.py")}
    try:
        seals = core.check_seals(repo)
        rs = {rel: core.sha256_file(repo / rel) if (repo / rel).is_file() else None for rel in U3_RULES}
        if not seals["ok"] or any(rs[r] != w for r, w in U3_RULES.items()):
            report, code = {"seals": seals, "u3_rules": rs, "stop_codes": ["S-1"]}, 2
        else:
            is_p3, mod = core.load_is_extend_start(repo)
            report = {"u3_rules": rs, "v5_options": mod}
            fnds = []
            if args.u3:
                files = [{"setting": a.split("=", 1)[0], "path": a.split("=", 1)[1]} for a in args.u3]
                body, f3 = recount_u3(files, args.h1, is_p3)
                report["U-3"] = {**body, **f3.as_dict()}
                fnds.append(f3)
            if args.u6:
                files = []
                for a in args.u6:
                    c, p = a.split("=", 1)
                    files.append({"controller": None if c == "ALL" else c, "path": p})
                body, f6 = recount_u6(files, is_p3)
                report["U-6"] = {**body, **f6.as_dict()}
                fnds.append(f6)
            codes = sorted({s["code"] for f in fnds for s in f.stops})
            report["stop_codes"] = codes
            gate = [c for c in codes if c in ("G-1", "G-2", "G-4", "G-6")]
            code = 2 if gate else (1 if (codes or any(f.undecidable or f.fails for f in fnds)) else 0)
        report.update(tool=TOOL_NAME, version=TOOL_VERSION, tool_sha256=tool_sha,
                      created=_dt.datetime.now().astimezone().isoformat(timespec="seconds"))
        text = json.dumps(report, indent=1, ensure_ascii=False, default=str)
        out_sha = None
        if args.out:
            Path(args.out).write_text(text + "\n", encoding="utf-8", newline="\n")
            out_sha = core.sha256_file(args.out)
        summary.update(exit=code, out=args.out, out_sha256=out_sha, stop_codes=report.get("stop_codes", []))
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        code = 3
        summary.update(exit=3, error=repr(exc)[:300], out_sha256=None)
    print(json.dumps(summary, ensure_ascii=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
