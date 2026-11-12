"""436.8 path 2 Chrono judgement (C-1..C-5, + C-8 m / time records) from raw series.

Usage (dynamics-dev, activated):
  conda run -n dynamics-dev python -I -B p2_chrono.py seal [--repo R]
  conda run -n dynamics-dev python -I -B p2_chrono.py judge --bundle C-1 --batch <batch.json> [--batch ...]
        [--results-root <repo>/07_results] [--row-dir CASE=PATH ...] --out <out.json> [--repo R]

Exit: 0 bundle 통과 / 기록 완료, 1 미달 / 판정 불가 / 기록 불완전 / stop, 2 input or seal error,
3 internal error. Last stdout line: JSON summary with tool_sha256 and out_sha256.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # -I drops the script folder from sys.path

import p2_core as C  # noqa: E402
import p2_rules as R  # noqa: E402

BUNDLE_MODULES = {"C-1": "p2_b_c1", "C-2": "p2_b_c2", "C-3": "p2_b_c3", "C-4": "p2_b_c4",
                  "C-5": "p2_b_c5", "C-8": "p2_b_c8"}
COMMON_FILES = ("p2_chrono.py", "p2_rules.py", "p2_core.py", "p2_kinds.py")


def file_sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tool_sha(bundle_module: str | None):
    files = list(COMMON_FILES) + ([bundle_module + ".py"] if bundle_module else [])
    per = {f: file_sha(HERE / f) for f in files}
    joined = "".join(f"{f} {per[f]}\n" for f in sorted(per))
    return hashlib.sha256(joined.encode()).hexdigest(), per


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


def resolve_dir(case: dict, batch_dir: Path, results_root: Path, overrides: dict) -> Path:
    name = case["case"]
    if name in overrides:
        return Path(overrides[name])
    eng = engine_of(case["argv"])
    if eng == "scm":
        return batch_dir / name
    tag = _arg(case["argv"], "--tag")
    only = _arg(case["argv"], "--only") or name
    sub = "S8" if eng == "l2b" else "S6"
    hits = [d for d in (results_root / sub).glob(f"*{tag}*") if d.is_dir()] if tag else []
    cands = [d / only for d in hits if (d / only / "result.json").exists()]
    if len(cands) != 1:
        raise C.InputError(f"{name}: {len(cands)} result folders for tag {tag!r} / {only!r} (use --row-dir)")
    return cands[0]


def case_criteria(case: dict):
    return case.get("criteria_id") or (case.get("r4368") or {}).get("criteria_id")


def is_gs(case: dict) -> bool:
    return (case.get("r4368") or {}).get("role") == "gs" or "GS" in str(case.get("rep_bundle") or "")


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
    params = C.load_params(repo)
    results_root = Path(args.results_root) if args.results_root else repo / "07_results"
    overrides = dict(x.split("=", 1) for x in (args.row_dir or []))
    rows = []
    for bp in args.batch:
        bp = Path(bp)
        b = json.loads(bp.read_text(encoding="utf-8"))
        for case in b.get("cases", []):
            if case_criteria(case) not in mod.CRITERIA or is_gs(case):
                continue
            d = resolve_dir(case, bp.parent, results_root, overrides)
            eng = engine_of(case["argv"])
            row = C.load_row(d, eng, case["argv"])
            kind = mod.kind_of(case)
            items, keys, notes, record = mod.judge_row(row, case, kind, params)
            st = C.row_status(items, keys)
            if record:
                st = "기록 완료" if st != "판정 불가" else "기록 불완전"
            rows.append({"case": case["case"], "batch": str(bp), "folder": str(d), "engine": eng,
                         "kind": kind, "criteria_id": case_criteria(case), "d1_id": case.get("d1_id"),
                         "pool": case.get("pool"), "rc": case.get("rc"),
                         "status": st, "judged_keys": keys, "items": items, "notes": notes})
    bundle = mod.bundle_status(rows)
    out = {"tool": "p2_chrono.py (436.8 path 2, Chrono)", "bundle": args.bundle,
           "tool_sha256": tsha, "tool_files_sha256": per, "seal": seal, "params": params,
           "rows": rows, "bundle_result": bundle}
    out_p = Path(args.out)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(C.jsonable(out), ensure_ascii=False, indent=1).encode("utf-8")
    out_p.write_bytes(data)
    osha = hashlib.sha256(data).hexdigest()
    summary.update(status=bundle["status"], rows=len(rows), stops=bundle.get("stops", []),
                   out=str(out_p), out_sha256=osha)
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if bundle["status"] in ("통과", "기록 완료") else 1


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
    j.add_argument("--out", required=True)
    j.add_argument("--repo")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "seal":
            repo = Path(a.repo).resolve() if a.repo else find_repo(HERE)
            seal = R.seal_check(repo)
            print(json.dumps(seal, ensure_ascii=False, indent=1))
            print(json.dumps({"tool": "p2_chrono.py", "cmd": "seal", "ok": seal["ok"],
                              "tool_sha256": tool_sha(None)[0], "out_sha256": None}))
            return 0 if seal["ok"] else 2
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
