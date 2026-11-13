"""436.8 path 2 Chrono judgement (C-1..C-5, + C-8 m / time records) from raw series.

Usage (dynamics-dev, activated):
  conda run -n dynamics-dev python -I -B p2_chrono.py seal [--repo R]
  conda run -n dynamics-dev python -I -B p2_chrono.py judge --bundle C-1 --batch <batch.json> [--batch ...]
        --git-at-start <judgement git_at_start> [--results-root <repo>/07_results] [--row-dir CASE=PATH ...]
        [--manifest M] --out <out.json> [--repo R]
  conda run -n dynamics-dev python -I -B p2_chrono.py gs-load --batch <G-S batch.json> --git-at-start <commit> --out <out.json>
        (read-only loader run on G-S rows: folders, input sha, absent inputs, exceptions; no judgement)

Exit: 0 bundle 통과 / 기록 완료, 1 미달 / 판정 불가 / 기록 불완전 / stop, 2 input or seal error,
3 internal error. Last stdout line: JSON summary with tool_sha256 and out_sha256.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import re
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # -I drops the script folder from sys.path

import p2_core as C  # noqa: E402
import p2_kinds as K  # noqa: E402
import p2_rules as R  # noqa: E402

BUNDLE_MODULES = {"C-1": "p2_b_c1", "C-2": "p2_b_c2", "C-3": "p2_b_c3", "C-4": "p2_b_c4",
                  "C-5": "p2_b_c5", "C-6C7": "p2_b_c67", "C-8": "p2_b_c8"}
COMMON_FILES = ("p2_chrono.py", "p2_rules.py", "p2_core.py", "p2_kinds.py", "p2_t45.py")


def file_sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tool_sha(bundle_module: str | None):
    files = list(COMMON_FILES) + ([bundle_module + ".py"] if bundle_module else [])
    per = {f: file_sha(HERE / f) for f in files}
    joined = "".join(f"{f} {per[f]}\n" for f in sorted(per))
    return hashlib.sha256(joined.encode()).hexdigest(), per


INPUT_FILES = ("result.json", "step_series.npz", "r8_series.npz", "s8_series.npz", "pads.npz",
               "controller_events.json", "series.npz", "flow_series.npz", "record/record.npz")


def input_shas(d: Path) -> dict:
    """rev3 R3-G2: names and sha256 of the raw files read for the row."""
    return {f: file_sha(d / f) for f in INPUT_FILES if (d / f).exists()}


def find_repo(start: Path) -> Path:
    for p in [start] + list(start.parents):
        if (p / R.REPO_MARKER).exists():
            return p
    raise C.InputError("repository root not found")


def engine_of(argv) -> str:
    s = " ".join(argv)
    if "run_S9.py" in s:
        return "scm"
    if "run_S8C.py" in s:
        return "l2b"
    if "run_S6C.py" in s:
        return "l1r"
    raise C.InputError("engine not recognised from argv")


def _arg(argv, name):
    if name in argv:
        i = argv.index(name)
        return argv[i + 1] if i + 1 < len(argv) else None
    return None


RUNNER_LINE = re.compile(r"batch wall .*->\s*(\S.*?)\s*$")


def case_log_folder(batch_dir: Path, name: str):
    """Last `batch wall ... -> <runner folder>` line of the row log `<batch>/<case>.log` (run record)."""
    lp = batch_dir / f"{name}.log"
    if not lp.exists():
        return None
    hit = None
    for line in lp.read_text(encoding="utf-8", errors="replace").splitlines():
        m = RUNNER_LINE.search(line)
        if m:
            hit = m.group(1)
    return Path(hit) if hit else None


def _relocate(p: Path, results_root: Path, sub: str) -> Path:
    """Same relative path under the given results root (after a `07_results` component if any)."""
    parts = list(p.parts)
    low = [x.lower() for x in parts]
    if "07_results" in low:
        rel = parts[low.index("07_results") + 1:]
        return results_root.joinpath(*rel)
    return results_root / sub / p.name


def resolve_dir(case: dict, batch_dir: Path, results_root: Path, overrides: dict):
    """Row folder and how it was found.

    SCM: `<batch folder>/<case>` (`batch_folder`). L2b / L1-R: the row log's last runner line
    (`case_log`; if that folder has no `<--only>/result.json`, the same relative path under the
    results root, `case_log_relocated`), cross-checked against the `--tag` folder search: the folder
    name must contain `--tag`. Without a runner line: rev12 R12-5 time window (`time_window`, exact
    folder names, exactly one candidate). Anything else is an input error (exit 2; `--row-dir
    CASE=PATH`, `row_dir`).
    """
    name = case["case"]
    if name in overrides:
        return Path(overrides[name]), "row_dir"
    eng = engine_of(case["argv"])
    if eng == "scm":
        return batch_dir / name, "batch_folder"
    tag = _arg(case["argv"], "--tag")
    only = _arg(case["argv"], "--only") or name
    sub = "S8" if eng == "l2b" else "S6"
    logged = case_log_folder(batch_dir, name)
    if logged is not None:
        if tag and tag not in logged.name:
            raise C.InputError(f"{name}: row log runner folder {logged.name!r} does not carry tag {tag!r}")
        if (logged / only / "result.json").exists():
            return logged / only, "case_log"
        rel = _relocate(logged, results_root, sub)
        if (rel / only / "result.json").exists():
            return rel / only, "case_log_relocated"
        raise C.InputError(f"{name}: row log runner folder {str(logged)!r} has no {only}/result.json"
                           f" (also not under {str(results_root)!r})")
    return time_window_folder(case, batch_dir, results_root, eng), "time_window"


PROGRESS_RE = re.compile(r"^(START|END)\s+(\S+)\s+(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})\b")
STAMP_FMT = "%Y%m%d_%H%M%S"
WINDOW_PAD_S = 2.0   # rev12 R12-5 1 / rev7 R7-8: +- 2 s on both window ends (procedure value)


def row_window(case: dict, batch_dir: Path):
    """rev12 R12-5 1: the row's `progress.log` START..END (the last START of the case and the first END
    after it); else the batch folder stamp .. stamp + `wall_s` (`est_s` not used). Returns
    (t0, t1, how) with the +- 2 s pad applied, or None when the window cannot be determined."""
    from datetime import datetime, timedelta
    name = case["case"]
    start = end = None
    pl = batch_dir / "progress.log"
    if pl.exists():
        for line in pl.read_text(encoding="utf-8", errors="replace").splitlines():
            m = PROGRESS_RE.match(line.strip())
            if not m or m.group(2) != name:
                continue
            t = datetime.fromisoformat(m.group(3))
            if m.group(1) == "START":
                start, end = t, None
            elif start is not None and end is None:
                end = t
    pad = timedelta(seconds=WINDOW_PAD_S)
    if start is not None and end is not None:
        return start - pad, end + pad, "progress.log START..END"
    m = BATCH_DIR_RE.match(batch_dir.name)
    wall = case.get("wall_s")
    if m is None or wall is None:
        return None
    stamp = batch_dir.name[-15:]
    t0 = datetime.strptime(stamp, STAMP_FMT)
    return t0 - pad, t0 + timedelta(seconds=float(wall)) + pad, "batch folder stamp + wall_s"


def time_window_folder(case: dict, batch_dir: Path, results_root: Path, eng: str) -> Path:
    """rev12 R12-5 (rev7 R7-5 fallback when the row log has no `->` line). Candidates: `run_S8C.py` rows
    `07_results/S8/<tag>_<YYYYmmdd_HHMMSS>` (exact name), `run_S6C.py` rows `07_results/S6/*` whose name
    ends with `_<tag>_L1R_<YYYYmmdd_HHMMSS>` (the check form `_<tag>_check_L1R_` does not match), stamp in
    the window, with `<--only>/result.json`. No window, 0 or 2+ candidates = input error (exit 2, S-11)."""
    from datetime import datetime
    name = case["case"]
    tag = _arg(case["argv"], "--tag")
    only = _arg(case["argv"], "--only") or name
    if not tag:
        raise C.InputError(f"{name}: no row log runner line and no --tag (rev12 R12-5, S-11)")
    win = row_window(case, batch_dir)
    if win is None:
        raise C.InputError(f"{name}: no row log runner line and no window (no START..END, no wall_s;"
                           " est_s not used; rev12 R12-5, S-11)")
    t0, t1, how = win
    if eng == "l2b":
        sub, pat = "S8", re.compile(r"^" + re.escape(tag) + r"_(\d{8}_\d{6})$")
    else:
        sub, pat = "S6", re.compile(r"^.+_" + re.escape(tag) + r"_L1R_(\d{8}_\d{6})$")
    cands = []
    root = results_root / sub
    for d in (root.iterdir() if root.is_dir() else []):
        mm = pat.match(d.name) if d.is_dir() else None
        if not mm:
            continue
        ts = datetime.strptime(mm.group(1), STAMP_FMT)
        if t0 <= ts <= t1 and (d / only / "result.json").exists():
            cands.append(d / only)
    if len(cands) != 1:
        raise C.InputError(f"{name}: no row log runner line and {len(cands)} folders for {sub}/{tag!r} in the"
                           f" window {t0.isoformat()}..{t1.isoformat()} ({how}) (rev12 R12-5, S-11)")
    return cands[0]


def placement_record(case: dict, res: dict, batch: dict) -> dict:
    """Rules 6 pool row + rev7 R7-6 (record only; the judgement document writes it)."""
    pl = res.get("placement") or {}
    out = {"clause": "rules 6 pool / rev7 R7-6 (record)",
           "pool": case.get("pool"), "planned_pool": case.get("planned_pool"),
           "placement_applied": case.get("placement_applied"),
           "affinity_mask_process": pl.get("affinity_mask_process"),
           "affinity_mask_ok": pl.get("affinity_mask_ok"),
           "power_throttling_off_ok": pl.get("power_throttling_off_ok"),
           "batch_affinity_masks": batch.get("affinity_masks"),
           "r4368_arm": (case.get("r4368") or {}).get("arm")}
    notes = []
    if out["affinity_mask_ok"] is False:
        notes.append("R7-6: placement.affinity_mask_ok false -> write in the judgement (rules 6 affinity change)")
    if out["pool"] != out["planned_pool"]:
        notes.append("rules 6: pool != planned_pool -> record, drop this row's hash comparison")
    arm_off = out["r4368_arm"] == "off"
    if arm_off != ("--las-off" in case.get("argv", [])) and out["r4368_arm"] is not None:
        notes.append("R7-4: r4368.arm and argv --las-off differ (record)")
    out["notes"] = notes
    return out


BATCH_DIR_RE = re.compile(r"^batch_(.+?)_\d{8}_\d{6}$")


def batch_name_of(b: dict, bp: Path, manifest: dict | None = None):
    """rev10 R10-1a full batch name (with the `V5-RESUME-K1-` prefix). Returns (name or None, reason).

    `batch.json` `batch` value, checked against the folder name part between `batch_` and
    `_<YYYYmmdd_HHMMSS>`. No key -> the folder part. Key and folder part differ, the key is present but
    the folder name is not of that form (no comparison possible: path 2 reading), neither can be
    determined, or the name is not a manifest `batches` key -> None ("묶음 이름 불명")."""
    m = BATCH_DIR_RE.match(bp.parent.name)
    folder = m.group(1) if m else None
    if "batch" in b:
        key = b.get("batch")
        if folder is None:
            return None, (f"batch key {key!r} but folder name {bp.parent.name!r} is not batch_<name>_<stamp>"
                          " (cannot be checked)")
        if key != folder:
            return None, f"batch key {key!r} != folder name part {folder!r}"
        name, how = str(key), "batch key = folder name"
    elif folder is not None:
        name, how = folder, "folder name (no batch key)"
    else:
        return None, f"no batch key and folder name {bp.parent.name!r} is not batch_<name>_<stamp>"
    if manifest is not None and name not in (manifest.get("batches") or {}):
        return None, f"{name!r} is not a manifest batches key"
    return name, how


def batch_id_of(b: dict, bp: Path):
    """Full batch name without the manifest check (record use only)."""
    return batch_name_of(b, bp, None)[0]


def batch_ctx(b: dict, bp: Path, manifest: dict | None) -> dict:
    """K.ls_input_case context of one S9 batch (rev10 R10-1)."""
    name, why = batch_name_of(b, bp, manifest)
    return {"batch_name": name, "batch_name_reason": why, "mrows": K.manifest_rows(manifest, name),
            "bcount": K.batch_case_counts(b)}


def load_manifest(args, repo: Path, required: bool):
    """`v5_resume_4368/chrono_rows_manifest.json` (shared row list, not a path 1 output, rev9 R9-4).
    rev10 R10-1b: missing, not readable as JSON or without `batches` = input error (exit 2, S-11) when
    `required`."""
    p = Path(args.manifest) if getattr(args, "manifest", None) else repo / R.MANIFEST_REL
    if not p.exists():
        if required:
            raise C.InputError(f"manifest {p} missing (rev10 R10-1b: input error, S-11)")
        return None, str(p), None
    data = p.read_bytes()
    try:
        man = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as e:
        if required:
            raise C.InputError(f"manifest {p} not readable as JSON (rev10 R10-1b, S-11): {e}")
        return None, str(p), hashlib.sha256(data).hexdigest()
    if not isinstance(man, dict) or not isinstance(man.get("batches"), dict):
        if required:
            raise C.InputError(f"manifest {p} has no batches object (rev10 R10-1b, S-11)")
        return None, str(p), hashlib.sha256(data).hexdigest()
    return man, str(p), hashlib.sha256(data).hexdigest()


GIT_REF_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")


def git_ref_arg(v, required: bool):
    """Judgement `git_at_start` (rev11 R11-4 2): 7..40 hex digits."""
    if v is None:
        if required:
            raise C.InputError("--git-at-start missing (rev11 R11-4 / rev12 R12-3: the judgement git_at_start is the reference)")
        return None
    if not GIT_REF_RE.match(v):
        raise C.InputError(f"--git-at-start {v!r} is not 7..40 hex digits")
    return v.lower()


def augment_items(bundle: str, row, items: dict, keys: list, case: dict | None = None,
                  res: dict | None = None, git_ref: str | None = None, commit: bool = False):
    """Items common to the Chrono bundles. rev11 R11-4 commit identity (S-12 stop) for every bundle,
    open loop C-6C7 included (when `commit`); rev9 R9-1 expect check (S-2 stop) for every bundle but
    C-6C7 (open loop, no controller); rev9 R9-6 J11 record for every bundle but C-5 / C-6C7."""
    if commit:
        items["R11-4_commit"] = K.commit_item(bundle, case or {}, res or {}, git_ref)
        keys.append("R11-4_commit")
    if bundle == "C-6C7":
        return
    items["R9-1_expect_controller"] = K.expect_item(row)
    keys.append("R9-1_expect_controller")
    if bundle != "C-5":
        items["J11_record"] = K.j11_record_item(row)


def r9_6_summary(rows: list) -> dict:
    recs = [r["items"].get("J11_record") for r in rows if isinstance(r["items"].get("J11_record"), dict)]
    return {"clause": "rev9 R9-6 (J11 outside C-5: record only, input absent counted)", "rows": len(recs),
            "input_absent_rows": sum(1 for x in recs if x.get("input_absent")),
            "n_late_positive_on_actual_leg_rows": sum(1 for x in recs if x.get("late_fallback_legs"))}


def case_criteria(case: dict):
    return case.get("criteria_id") or (case.get("r4368") or {}).get("criteria_id")


def is_gs(case: dict) -> bool:
    """G-S rows and R_c probes are not judged (rules 11.2, 5.4-2)."""
    role = (case.get("r4368") or {}).get("role")
    return role in ("gs", "probe") or "GS" in str(case.get("rep_bundle") or "")


def judge(args) -> int:
    repo = Path(args.repo).resolve() if args.repo else find_repo(HERE)
    seal = R.seal_check(repo)
    mod_name = BUNDLE_MODULES.get(args.bundle)
    if mod_name is None:
        raise C.InputError(f"unknown bundle {args.bundle}")
    tsha, per = tool_sha(mod_name)
    summary = {"tool": "p2_chrono.py", "bundle": args.bundle, "tool_sha256": tsha}
    if not seal["ok"]:
        print(json.dumps(C.jsonable(seal), ensure_ascii=False))
        summary.update(status="seal_error", stop="S-1")
        print(json.dumps(summary))
        return 2
    mod = importlib.import_module(mod_name)
    mod.AUX = dict(x.split("=", 1) for x in (args.aux or []))
    params = C.load_params(repo)
    results_root = Path(args.results_root) if args.results_root else repo / "07_results"
    overrides = dict(x.split("=", 1) for x in (args.row_dir or []))
    manifest, man_path, man_sha = load_manifest(args, repo, required=(args.bundle == "C-5"))
    git_ref = git_ref_arg(args.git_at_start, required=True)
    rows = []
    for bp in args.batch:
        bp = Path(bp)
        b = json.loads(bp.read_text(encoding="utf-8"))
        if hasattr(mod, "CTX"):
            mod.CTX = batch_ctx(b, bp, manifest)
        for case in b.get("cases", []):
            if case_criteria(case) not in mod.CRITERIA or is_gs(case):
                continue
            d, how = resolve_dir(case, bp.parent, results_root, overrides)
            eng = engine_of(case["argv"])
            loader = getattr(mod, "load", None)
            row = loader(d, eng, case["argv"]) if loader else C.load_row(d, eng, case["argv"])
            kind = mod.kind_of(case)
            items, keys, notes, record = mod.judge_row(row, case, kind, params)
            augment_items(args.bundle, row, items, keys, case, _result_of(d), git_ref, commit=True)
            st = C.row_status(items, keys)
            if record:
                st = "기록 완료" if st != "판정 불가" else "기록 불완전"
            plc = placement_record(case, _result_of(d), b)
            rows.append({"case": case["case"], "batch": str(bp), "folder": str(d), "folder_method": how,
                         "engine": eng, "input_files_sha256": input_shas(d),
                         "kind": kind, "criteria_id": case_criteria(case), "d1_id": case.get("d1_id"),
                         "pool": case.get("pool"), "rc": case.get("rc"), "placement_record": plc,
                         "status": st, "judged_keys": keys, "items": items,
                         "notes": list(notes) + plc["notes"]})
    bundle = mod.bundle_status(rows)
    if args.bundle not in ("C-5", "C-6C7"):
        bundle["rev9_R9_6_j11_record"] = r9_6_summary(rows)
    out = {"tool": "p2_chrono.py (436.8 path 2, Chrono)", "bundle": args.bundle,
           "tool_sha256": tsha, "tool_files_sha256": per, "seal": seal, "params": params,
           "manifest": {"path": man_path, "sha256": man_sha}, "rows": rows, "bundle_result": bundle}
    out_p = Path(args.out)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(C.jsonable(out), ensure_ascii=False, indent=1).encode("utf-8")
    out_p.write_bytes(data)
    osha = hashlib.sha256(data).hexdigest()
    summary.update(status=bundle["status"], rows=len(rows), stops=bundle.get("stops", []),
                   out=str(out_p), out_sha256=osha)
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if bundle["status"] in ("통과", "기록 완료") else 1


def _result_of(d: Path) -> dict:
    p = d / "result.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except (OSError, ValueError):
        return {}


MISSING_WORDS = ("missing", "absent", "not found", "no ")


def _walk_missing(items: dict) -> list:
    """Item names whose reason reads as an absent input (no values, no verdicts; `na` items skipped)."""
    out = []
    for k, v in items.items():
        if not isinstance(v, dict) or v.get("verdict") == "na":
            continue
        r = str(v.get("reason") or "")
        if r and any(w in r.lower() for w in MISSING_WORDS):
            out.append({"item": k, "reason": r[:200]})
    return out


def _jp3_scope(it):
    """rev8 R8-2 / R8-4 G-S record: J-P3 scope only (tag reading, request records; no breach values)."""
    if not isinstance(it, dict):
        return None
    stop = str(it.get("stop") or "")
    if stop.startswith("S-2"):
        scope = "S-2"
    elif it.get("verdict") == "na":
        scope = "not_applicable"
    elif "9.3" in str(it.get("reason") or ""):
        scope = "key_missing_9.3"
    else:
        scope = "applicable"
    return {"scope": scope, "tag": it.get("tag"), "tag_established": it.get("tag_established"),
            "extend_start_tag": it.get("extend_start_tag"), "request_compared": it.get("request_compared"),
            "request_mismatch": it.get("request_mismatch"), "s2_reason": stop if scope == "S-2" else None}


def _r9_record(bundle, row, items) -> dict:
    """rev9 R9-8 G-S record per row (classes and counts only, no item values / verdicts):
    R9-1 expect check (S-2, G-S also S-11), R9-2 / R9-3 law_locked codes and -1 pattern, R9-5 class
    (C-5 rows: absent / malformed = S-11 at G-S; other rows: input absent record, R9-6), R9-4 LS class."""
    ex = items.get("R9-1_expect_controller")
    out = {"r9_1": None if ex is None else {"expect_ok": ex.get("expect_ok"), "source": ex.get("source"),
                                            "s2": "stop" in ex}}
    if hasattr(row, "law_locked_problems"):
        present = row.law_locked_source is not None
        bad = (not present) or bool(row.law_locked_problems)
        if bundle == "C-5":
            r95 = "S-11 (R9-5: law_locked absent or malformed on a C-5 row)" if bad else "ok"
        else:
            r95 = "input absent (R9-6 record; 11.2 key check unchanged)" if bad else "ok"
        out["r9_5"] = r95
    ls = items.get("LS_class")
    if isinstance(ls, dict):
        out["r9_4"] = {"ls": ls.get("ls"), "manifest_v5_setting": ls.get("manifest_v5_setting"),
                       "batch_v5_setting": ls.get("batch_v5_setting"), "s2": "stop" in ls}
    return out


def _r11_record(it) -> dict | None:
    """rev11 R11-4 G-S record per row (heads and the S-12 class only, no verdict)."""
    if not isinstance(it, dict):
        return None
    return {"git_at_start": it.get("git_at_start"), "code_at_launch_head": it.get("code_at_launch_head"),
            "code_at_launch_clean": it.get("code_at_launch_clean"), "code_state_head": it.get("code_state_head"),
            "code_state_compared": it.get("code_state_compared"), "open_loop": it.get("open_loop"),
            "dirty_record": it.get("dirty_record"), "code_at_launch_paths": it.get("code_at_launch_paths"),
            "open_loop_code_state_same_record": it.get("open_loop_code_state_same_record"),
            "problems": it.get("problems"),
            # without --git-at-start only a missing code_at_launch head can be counted
            "s12": ("stop" in it) if it.get("git_at_start") else it.get("code_at_launch_head") is None}


def _r11_summary(rows: list, seal: dict, git_ref) -> dict:
    """rev11 G-S items: R11-4 S-12 rows (missing / different commit records, open loop counted apart),
    R11-5 (path 2 gs-load writes no grades), rev11 seal check."""
    recs = [r.get("r11_4") for r in rows if r.get("r11_4")]
    rev11 = next((s for s in seal.get("sealed", []) if s["file"].endswith("v5_resume_4368_rules_rev11.md")), None)
    return {"git_at_start": git_ref,
            "r11_4_rows": len(recs),
            "r11_4_s12_rows": sum(1 for x in recs if x["s12"]),
            "r11_4_open_loop_rows": sum(1 for x in recs if x["open_loop"]),
            "r11_4_open_loop_s12_rows": sum(1 for x in recs if x["open_loop"] and x["s12"]),
            "r11_4_code_at_launch_missing_rows": sum(1 for x in recs if x["code_at_launch_head"] is None),
            "r11_4_code_state_compared_rows": sum(1 for x in recs if x["code_state_compared"]),
            "r12_2_dirty_record_rows": sum(1 for x in recs if x.get("dirty_record")),
            "r12_4_open_loop_code_state_rows": sum(1 for x in recs if x.get("open_loop_code_state_same_record") is not None),
            "r11_5_grades_written": False,
            "rev11_seal": None if rev11 is None else rev11.get("status")}


def _r10_record(case: dict, bctx: dict) -> dict:
    """rev10 R10-2 G-S record per Chrono row (every G-S row, all bundles): full batch name, rows of the
    case in the manifest batch and in batch.json cases[], R10-1b labels; `s11` = any blocking label."""
    ls = K.ls_classification(case, bctx)
    inp = ls["input"]
    labels = list(inp["blocking"]) + ([inp["value_case"]] if inp.get("value_case") else [])
    return {"batch_name": inp["batch_name"], "batch_name_reason": inp["batch_name_reason"],
            "manifest_rows": inp["manifest_rows"], "batch_cases": inp["batch_cases"], "labels": labels,
            "s11": bool(inp["blocking"])}


def _r10_summary(rows: list, seal: dict) -> dict:
    """rev10 R10-2 G-S items: rows per R10-1b case, G-S failure rows (S-11), rev10 seal check."""
    counts = {k: 0 for k in K.LS_INPUT_CASES}
    for r in rows:
        for lab in (r.get("r10") or {}).get("labels") or []:
            counts[lab] = counts.get(lab, 0) + 1
    rev10 = next((s for s in seal.get("sealed", []) if s["file"].endswith("v5_resume_4368_rules_rev10.md")), None)
    return {"r10_1b_rows_per_case": counts,
            "r10_2_s11_rows": sum(1 for r in rows if (r.get("r10") or {}).get("s11")),
            "rows": len(rows), "rev10_seal": None if rev10 is None else rev10.get("status")}


def _r9_summary(rows: list, seal: dict) -> dict:
    """rev9 R9-8 G-S items: R9-1 S-2 count, R9-2 mismatches per item, R9-3 pattern counts, R9-4 LS rows and
    not-judgeable rows, rev9 seal check."""
    ok_rows = [r for r in rows if not r.get("error")]
    item_counts = {k: 0 for k in R.LAW_LOCK_ITEMS}
    pat_counts = {}
    for r in ok_rows:
        ll = r.get("law_locked_record") or {}
        for c in ll.get("codes") or []:
            item_counts[c] = item_counts.get(c, 0) + 1
        for p in ll.get("pattern") or []:
            pat_counts[p] = pat_counts.get(p, 0) + 1
    r94 = [(r.get("r9") or {}).get("r9_4") for r in ok_rows]
    r94 = [x for x in r94 if x]
    rev9 = next((s for s in seal.get("sealed", []) if s["file"].endswith("v5_resume_4368_rules_rev9.md")), None)
    return {"r9_1_s2_rows": sum(1 for r in ok_rows if ((r.get("r9") or {}).get("r9_1") or {}).get("s2")),
            "r9_2_rows_per_item": item_counts,
            "r9_3_pattern_rows": pat_counts,
            "r9_4_ls_rows": sum(1 for x in r94 if x["ls"] is True),
            "r9_4_not_judgeable_rows": sum(1 for x in r94 if x["ls"] is None),
            "r9_4_ls_non_extend_tag_s2_rows": sum(1 for x in r94 if x["s2"]),
            "r9_5_c5_s11_rows": sum(1 for r in ok_rows if str((r.get("r9") or {}).get("r9_5", "")).startswith("S-11")),
            "r9_6_input_absent_rows": sum(1 for r in ok_rows
                                          if str((r.get("r9") or {}).get("r9_5", "")).startswith("input absent")),
            "rev9_seal": None if rev9 is None else rev9.get("status")}


def gs_load(args) -> int:
    """Read-only loader run on G-S rows (rules 11.2): every G-S row is resolved, loaded and passed
    through its bundle's item functions; the output keeps folders, input sha256, absent-input
    reasons and exceptions only (no item values, no verdicts, no bundle status). Not a judgement."""
    repo = Path(args.repo).resolve() if args.repo else find_repo(HERE)
    seal = R.seal_check(repo)
    tsha, per = tool_sha(None)
    summary = {"tool": "p2_chrono.py", "cmd": "gs-load", "tool_sha256": tsha}
    if not seal["ok"]:
        print(json.dumps(C.jsonable(seal), ensure_ascii=False))
        summary.update(status="seal_error", stop="S-1", out_sha256=None)
        print(json.dumps(summary))
        return 2
    mods = {b: importlib.import_module(m) for b, m in BUNDLE_MODULES.items()}
    for m in mods.values():
        m.AUX = {}
    params = C.load_params(repo)
    results_root = Path(args.results_root) if args.results_root else repo / "07_results"
    overrides = dict(x.split("=", 1) for x in (args.row_dir or []))
    manifest, man_path, man_sha = load_manifest(args, repo, required=True)   # rev10 R10-1b / R10-2: G-S checks every Chrono row
    git_ref = git_ref_arg(getattr(args, "git_at_start", None), required=True)   # rev12 R12-3
    rows, n_err, n_input_err = [], 0, 0
    for bp in args.batch:
        bp = Path(bp)
        b = json.loads(bp.read_text(encoding="utf-8"))
        bctx = batch_ctx(b, bp, manifest)
        mods["C-5"].CTX = bctx
        for case in b.get("cases", []):
            if not is_gs(case):
                continue
            crit = case_criteria(case)
            bundle = next((k for k, m in mods.items() if crit in m.CRITERIA), None)
            ent = {"case": case["case"], "criteria_id": crit, "bundle": bundle, "r10": _r10_record(case, bctx)}
            try:
                if bundle is None:
                    raise C.InputError(f"criteria_id {crit!r} not in any bundle")
                mod = mods[bundle]
                d, how = resolve_dir(case, bp.parent, results_root, overrides)
                eng = engine_of(case["argv"])
                loader = getattr(mod, "load", None)
                row = loader(d, eng, case["argv"]) if loader else C.load_row(d, eng, case["argv"])
                kind = mod.kind_of(case)
                items, keys, notes, record = mod.judge_row(row, case, kind, params)
                augment_items(bundle, row, items, keys, case, _result_of(d), git_ref, commit=True)
                res = _result_of(d)
                ident = items.get("identity") if isinstance(items.get("identity"), dict) else {}
                plc = placement_record(case, res, b)
                ent.update(folder=str(d), folder_method=how, engine=eng, kind=kind,
                           input_files_sha256=input_shas(d), n_items=len(items), n_judged_keys=len(keys),
                           absent_inputs=_walk_missing(items),
                           r7_4_absent_where_required=(ident.get("r7_4_las_keys") or {}).get(
                               "absent_where_required"),
                           r7_6_keys_present={"placement.affinity_mask_process":
                                              "affinity_mask_process" in (res.get("placement") or {}),
                                              "placement.affinity_mask_ok":
                                              "affinity_mask_ok" in (res.get("placement") or {}),
                                              "batch.affinity_masks": "affinity_masks" in b,
                                              "case.placement_applied": "placement_applied" in case},
                           law_locked_record=({"source": row.law_locked_source,
                                               "present": row.law_locked_source is not None,
                                               "well_formed": row.law_locked is not None,
                                               "problems": list(row.law_locked_problems),
                                               "codes": (C.law_locked_codes(row.law_locked_problems)
                                                         if row.law_locked_source is not None else ["key"]),
                                               "pattern": (row.law_locked_pattern or {}).get("patterns"),
                                               "unarmed_prefix_samples":
                                                   (row.law_locked_pattern or {}).get("unarmed_prefix_samples")}
                                              if hasattr(row, "law_locked_problems") else None),
                           jp3_scope=_jp3_scope(items.get("J-P3")),
                           r9=_r9_record(bundle, row, items),
                           r11_4=_r11_record(items.get("R11-4_commit")),
                           folder_notes=plc["notes"], error=None)
            except Exception as e:  # noqa: BLE001
                n_err += 1
                if isinstance(e, C.InputError):
                    n_input_err += 1   # e.g. rev12 R12-5 no / several row folders = input error (S-11)
                ent["error"] = f"{type(e).__name__}: {e}"[:400]
                ent["input_error"] = isinstance(e, C.InputError)
            rows.append(ent)
    out = {"tool": "p2_chrono.py gs-load (436.8 path 2, Chrono; read-only, no judgement)",
           "tool_sha256": tsha, "tool_files_sha256": per, "seal": seal,
           "manifest": {"path": man_path, "sha256": man_sha}, "rows": rows,
           "n_rows": len(rows), "n_errors": n_err, "n_input_errors": n_input_err, "rev9_R9_8_gs_items": _r9_summary(rows, seal),
           "rev10_R10_2_gs_items": _r10_summary(rows, seal),
           "rev11_gs_items": _r11_summary(rows, seal, git_ref)}
    out_p = Path(args.out)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(C.jsonable(out), ensure_ascii=False, indent=1).encode("utf-8")
    out_p.write_bytes(data)
    summary.update(status="ok" if n_err == 0 and rows else ("input_error" if n_input_err else "errors"),
                   rows=len(rows), errors=n_err, input_errors=n_input_err,
                   out=str(out_p), out_sha256=hashlib.sha256(data).hexdigest())
    print(json.dumps(summary, ensure_ascii=False))
    if n_input_err:
        return 2   # rev12 R12-3 / R12-5: input error, G-S check not done for those rows (S-11)
    return 0 if (n_err == 0 and rows) else 1


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap =argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("seal")
    s.add_argument("--repo")
    j = sub.add_parser("judge")
    j.add_argument("--bundle", required=True, choices=sorted(BUNDLE_MODULES))
    j.add_argument("--batch", action="append", required=True)
    j.add_argument("--results-root")
    j.add_argument("--row-dir", action="append")
    j.add_argument("--aux", action="append", help="NAME=PATH extra input for a bundle (C-5: t45=<t45_path2.json>)")
    j.add_argument("--git-at-start", help="judgement git_at_start commit (7..40 hex, required, rev11 R11-4)")
    j.add_argument("--manifest", help="chrono_rows_manifest.json (default: repo v5_resume_4368/, rev9 R9-4)")
    j.add_argument("--out", required=True)
    j.add_argument("--repo")
    g = sub.add_parser("gs-load", help="read-only loader run on G-S rows (no judgement)")
    g.add_argument("--batch", action="append", required=True)
    g.add_argument("--results-root")
    g.add_argument("--row-dir", action="append")
    g.add_argument("--git-at-start", help="judgement git_at_start commit (7..40 hex, required, rev12 R12-3)")
    g.add_argument("--manifest", help="chrono_rows_manifest.json (default: repo v5_resume_4368/, rev9 R9-4)")
    g.add_argument("--out", required=True)
    g.add_argument("--repo")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "seal":
            repo = Path(a.repo).resolve() if a.repo else find_repo(HERE)
            seal = R.seal_check(repo)
            print(json.dumps(seal, ensure_ascii=False, indent=1))
            print(json.dumps({"tool": "p2_chrono.py", "cmd": "seal", "ok": seal["ok"],
                              "tool_sha256": tool_sha(None)[0], "out_sha256": None}))
            return 0 if seal["ok"] else 2
        if a.cmd == "gs-load":
            return gs_load(a)
        return judge(a)
    except C.InputError as e:
        print(json.dumps({"tool": "p2_chrono.py", "status": "input_error", "error": str(e),
                          "tool_sha256": None, "out_sha256": None}, ensure_ascii=False))
        return 2
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        print(json.dumps({"tool": "p2_chrono.py", "status": "internal_error",
                          "tool_sha256": None, "out_sha256": None}))
        return 3


if __name__ == "__main__":
    sys.exit(main())
