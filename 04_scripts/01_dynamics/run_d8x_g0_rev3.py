"""D8x G0 under rules rev3 4: all 60 evaluations recomputed (reuse 0).

Rules ``06_analysis/02_control/d8x/d8x_rules_rev3.md`` 4 (sha256 2318fb5c...) replaces the rev1 3
reuse: the rev1 reuse condition broke (``03_src/outrigger_sim/control/target.py`` blob changed in
the G0 import closure), so the 20 rev1 1.2 points x 3 levels are all computed again with the same
G0 stage code (``run_s6_slope_boundary_check`` ``_d8x_job`` / ``d8x_eval``, the rev1 wrapper's
helpers). The G0-4 gate is the rev2 3 scope (top ``pitch+`` / ``pitch-`` / ``roll+`` / ``rpX``);
the other G0-4 values are records. ``d8x_judge.py judge-g0 --g0`` judges the file.

Recorded in ``meta`` (rules I-1, rev3 4): ``rules_rev`` "rev3", the rules seals, the run commit,
``git status --porcelain --untracked-files=no`` at the start and the end (both must be empty for
a judged run), the blob id at the run commit of every repository file of the import closure
(+ YAML), ``reuse`` 0 / ``recompute`` 60, and the item differences against the rev1 60
(``e37f42c`` ``d8x_g0_rev1.json``; a record, not a grade).

Run (worktree or master root, dynamics-dev, E-cores; nothing else is written)::

    conda run -n dynamics-dev python -I 04_scripts/01_dynamics/run_d8x_g0_rev3.py

Output ``06_analysis/00_dynamics/d8x_g0_rev3.json`` unless ``--out``; ``d8x_g0.json`` and
``d8x_g0_rev1.json`` are never written.
"""
from __future__ import annotations

import os

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import platform  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_d8x_g0_rev1 as rev1  # noqa: E402

sb = rev1.sb
ROOT = sb.ROOT
OUT = ROOT / "06_analysis" / "00_dynamics" / "d8x_g0_rev3.json"
RULES_REV = "rev3"
RULES_DIR = "06_analysis/02_control/d8x"
RULES_FILES = ("d8x_rules.md", "d8x_rules_rev1.md", "d8x_rules_rev2.md", "d8x_rules_rev3.md",
               "d8x_rules_rev4.md")
REV1_REF = "e37f42c:06_analysis/00_dynamics/d8x_g0_rev1.json"
GATE_G04_TOP = ("pitch+", "pitch-", "roll+", "rpX")
"""Rev2 3: G0-4 gate = the floors of the L1-R rows #7 .. #11 at the top; the rest is a record."""
COMPARE_KEYS = {"G0-1": "s_max_m", "G0-2": "F_static_min_N", "G0-3": "swivel_deg",
                "G0-4": "floor_hat_deg"}
EXPECTED_EVALUATIONS = 60


def rules_seals() -> dict:
    """Raw sha256 of each rules file and the value of its ``.sha256`` file."""
    out = {}
    for name in RULES_FILES:
        path = ROOT / RULES_DIR / name
        sidecar = path.with_suffix(".sha256")
        out[name] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                     "sidecar": sidecar.read_text(encoding="utf-8").split()[0]}
    return out


def closure_record() -> dict:
    """Blob ids at HEAD of the repository files loaded in this process (+ YAML)."""
    files = {"02_params/rexome33.yaml"}
    for module in list(sys.modules.values()):
        path = getattr(module, "__file__", None)
        if not path:
            continue
        try:
            files.add(Path(path).resolve().relative_to(ROOT).as_posix())
        except ValueError:
            continue
    blobs = {name: rev1.git("rev-parse", f"HEAD:{name}") for name in sorted(files)}
    return {"files": blobs, "n_files": len(blobs),
            "untracked": sorted(name for name, blob in blobs.items() if not blob)}


def judge_row(row: dict) -> dict:
    """The rev1 wrapper's row judgement with the rev2 3 G0-4 scope."""
    judged = rev1.rejudge(row)
    is_gate = judged["level"] == "top" and judged["tag"] in GATE_G04_TOP
    if judged["g04_role"] == "chrono" and not is_gate:
        judged["g04_role"] = "record"
    required = ["G0-1", "G0-2", "G0-3"] + (["G0-4"] if is_gate else [])
    values = [judged["G0"][item].get("pass") for item in required]
    judged["judged_items"] = required
    judged["verdict"] = ("not_judgeable" if any(v is None for v in values)
                         else "pass" if all(values) else "fail")
    judged["source"] = "recomputed (rev3)"
    return judged


def compare_with_rev1(rows: list[dict]) -> dict:
    """Rev3 4 record: item values of rev3 minus rev1 per evaluation (0 expected)."""
    stored = json.loads(rev1.git("show", REV1_REF))
    old = {(r["level"], r["tag"]): r for r in stored["rows"]}
    per_row, nonzero = {}, []
    for row in rows:
        before = old.get((row["level"], row["tag"]))
        key = f"{row['level']}|{row['tag']}"
        if before is None:
            per_row[key] = None
            nonzero.append(key)
            continue
        diffs = {}
        for item, name in COMPARE_KEYS.items():
            now, then = row["G0"][item].get(name), before["G0"][item].get(name)
            diffs[f"{item}.{name}"] = 0.0 if now == then else rev1._num_diff(now, then)
        per_row[key] = diffs
        if any(d is None or d != 0.0 for d in diffs.values()):
            nonzero.append(key)
    return {"ref": REV1_REF, "blob": rev1.git("rev-parse", REV1_REF), "keys": COMPARE_KEYS,
            "per_row": per_row, "nonzero": nonzero}


def summary_of(rows: list[dict]) -> dict:
    counts = {v: sum(r["verdict"] == v for r in rows) for v in ("pass", "fail", "not_judgeable")}
    complete = len(rows) == EXPECTED_EVALUATIONS and not counts["not_judgeable"]
    gate = "pass" if complete and counts["pass"] == EXPECTED_EVALUATIONS else (
        "fail" if complete else "not_judgeable")
    fails = {item: [f"{r['level']}|{r['tag']}" for r in rows
                    if item in r["judged_items"] and r["G0"][item].get("pass") is False]
             for item in ("G0-1", "G0-2", "G0-3", "G0-4")}
    return {"expected": EXPECTED_EVALUATIONS, "actual": len(rows), "reused": 0,
            "recomputed": len(rows), **counts, "gate_G0": gate, "fails_by_item": fails}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workers", type=int, default=sb.WORKERS)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    t0 = time.perf_counter()
    status_start = rev1.git("status", "--porcelain", "--untracked-files=no")
    head = rev1.git("rev-parse", "HEAD")
    points = [(tag, roll, pitch) for tag, roll, pitch in rev1.REV1_POINTS]
    rows = [judge_row(r) for r in rev1.compute(points, sb.dm.LEVELS, args.workers)]
    closure = closure_record()  # after compute: the workers import the same modules
    status_end = rev1.git("status", "--porcelain", "--untracked-files=no")
    out = {
        "meta": {
            "rules_rev": RULES_REV, "rules": RULES_DIR, "rules_seals": rules_seals(),
            "sections": "rev3 4 (reuse 0 + recompute 60), rev2 3 G0-4 scope / W eligibility",
            "run_commit": head, "status_porcelain_start": status_start,
            "status_porcelain_end": status_end,
            "clean": status_start == "" and status_end == "",
            "reuse": 0, "recompute": len(rows), "closure": closure,
            "compare_rev1": compare_with_rev1(rows),
            "thresholds": {**sb.D8X_G0, "Rv_hat_max": rev1.RV_HAT_MAX,
                           "Rv_hat_max_d45_W": rev1.RV_HAT_MAX_D45_W,
                           "inv_err_max_deg": rev1.ERR_MAX},
            "diamond_deg": {"roll": rev1.SPAN_ROLL, "nose_down": rev1.SPAN_DN,
                            "nose_up": rev1.SPAN_UP},
            "G0-4_scope": "gate: top pitch+ / pitch- / roll+ / rpX (rev2 3); others record",
            "identity": {**sb._d8x_identity(), "python": sys.executable,
                         "python_version": platform.python_version()},
            "wall_s": round(time.perf_counter() - t0, 1),
            "script": "04_scripts/01_dynamics/run_d8x_g0_rev3.py",
        },
        "summary": summary_of(rows),
        "rows": rows,
    }
    args.out.write_text(json.dumps(out, indent=1, default=lambda v: v.tolist() if hasattr(
        v, "tolist") else (bool(v) if type(v).__name__ == "bool_" else float(v))),
        encoding="utf-8")
    print(json.dumps({"gate_G0": out["summary"]["gate_G0"], "pass": out["summary"]["pass"],
                      "clean": out["meta"]["clean"],
                      "rev1_nonzero": len(out["meta"]["compare_rev1"]["nonzero"]),
                      "out": str(args.out)}))


if __name__ == "__main__":
    main()
