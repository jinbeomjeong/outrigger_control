"""rev4 R4-A2 option c for PS-c E-7 (rev18 R18-3 1): path 2 runs the designated tool itself — the study A
E judgement of `04_scripts/03_control/s9/s9_soil_event_screen.py` (`judge_soil_event`, spec 426.3) — on the
1 ms event rows of each C-2 PS-c row, and keeps the item value (twist-work bundles). Conditions of R4-A2:

1. the tool file has 0 commits in `git log f46b5ab..<git_at_start> -- <file>` and the executed file is the
   `<git_at_start>` blob. The tool imports `r67_g1_screen` (`judge_event`, `twist_work`, `is_fast`) and
   `r51_reapp_closed_loop` (`_intervals`); those files changed after f46b5ab outside these functions, so the
   gate compares the source of the functions and constants used (f46b5ab = git_at_start = executed file);
   per-file commit counts are recorded.
2. (t45 regression only; not part of E-7.)
3. output goes to the path 2 folder; path 1 output is never read.
4. path 2 grades the value (p2_psc.e7_item: bundles <= 1); the tool's gates and `pass` are recorded, not used.

The branch rows given to the tool are the 426.3 branch of p2_psc (t_ev - 0.5 s .. branch end). The tool
needs a controller only for its soil record (`_soil_records`); a stub is passed and that record is dropped.

Usage: p2_e7.py <repo> <out_dir> --git-at-start <ref> <PS-c row folder> [...]
Exit 0 = gate ok and every row judged by the tool, 1 = gate failed or a row error, 2 = input error.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
import types
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import p2_core as C  # noqa: E402
import p2_psc as P  # noqa: E402
import p2_rules as R  # noqa: E402

BASE_COMMIT = "f46b5ab"   # rev4 R4-A2 condition 1
TOOL = "04_scripts/03_control/s9/s9_soil_event_screen.py"
DEPS = {  # file -> names (functions / module constants) the E judgement uses
    "04_scripts/03_control/s8/r67_g1_screen.py": ("judge_event", "twist_work", "is_fast", "_intervals", "LEGS",
                                                  "DIAG", "N_TWIST", "V_MAX", "T3_S", "F_MIN_N"),
    "04_scripts/03_control/s8/r51_reapp_closed_loop.py": ("_intervals",),
}
TOOL_NAMES = ("judge_soil_event", "_event_window_end_s", "_per_leg_lift_rows", "_adjacent_outside_lift",
              "_pressure_rows", "_crawler_rows", "_soil_records", "_fast_gates", "_slow_gates", "_common_gates",
              "BranchResult")
RECORDED = ("04_scripts/03_control/s9/s9_soil_closed_loop.py", "04_scripts/03_control/s8/r64_g4_closed_loop.py")


def git(repo: Path, *args) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8",
                          check=True).stdout


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def segments(src: str, names) -> dict:
    """Source text of top-level defs / classes / assignments with the given names."""
    tree = ast.parse(src)
    out = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names:
            out[node.name] = ast.get_source_segment(src, node)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            tg = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in tg:
                if isinstance(t, ast.Name) and t.id in names:
                    out[t.id] = ast.get_source_segment(src, node)
    return out


def tool_gate(repo: Path, ref: str) -> dict:
    files, ok, problems = {}, True, []
    for f in (TOOL, *DEPS, *RECORDED):
        n = len([x for x in git(repo, "log", "--oneline", f"{BASE_COMMIT}..{ref}", "--", f).splitlines() if x])
        work = (repo / f).read_bytes()
        at_ref = git(repo, "show", f"{ref}:{f}").encode("utf-8")
        files[f] = {"commits_base_to_ref": n, "sha256_executed": sha(work),
                    "executed_is_ref_blob": work.replace(b"\r\n", b"\n") == at_ref.replace(b"\r\n", b"\n")}
    t = files[TOOL]
    if t["commits_base_to_ref"] != 0:
        ok = False
        problems.append(f"{TOOL}: {t['commits_base_to_ref']} commits {BASE_COMMIT}..{ref}")
    for f, names in [(TOOL, TOOL_NAMES), *DEPS.items()]:
        srcs = {lab: s for lab, s in (("base", git(repo, "show", f"{BASE_COMMIT}:{f}")),
                                     ("ref", git(repo, "show", f"{ref}:{f}")),
                                     ("executed", (repo / f).read_text(encoding="utf-8")))}
        segs = {lab: segments(s, names) for lab, s in srcs.items()}
        same = {}
        for nm in names:
            vals = [segs[lab].get(nm) for lab in ("base", "ref", "executed")]
            same[nm] = vals[0] is not None and vals[0] == vals[1] == vals[2]
            if not same[nm]:
                ok = False
                problems.append(f"{f}: {nm} differs between {BASE_COMMIT}, {ref} and the executed file")
        files[f]["used_names_same"] = same
    return {"clause": "rev4 R4-A2 condition 1 (E-7 tool)", "base": BASE_COMMIT, "git_at_start": ref,
            "head": git(repo, "rev-parse", "HEAD").strip(), "files": files, "problems": problems, "ok": ok}


class _NoController:
    """Stub for the tool's soil record only (`_soil_records`); its output is dropped."""

    def _soil_state(self):
        return types.SimpleNamespace(soil_mode_start_s=None)


def run_row(s9e, folder: Path, argv, params) -> dict:
    row = C.load_row(folder, "scm", argv)
    ev, why = P.load_event(row)
    if ev is None:
        return {"case": row.case, "folder": str(folder), "error": why}
    be = P.branch_end(row, ev)
    rows = ev["rows"][ev["rows"][:, 0] <= be["t_end_s"] + R.CMP_TOL]
    t_ev = ev["t_ev_s"]
    rel_ph = [(round(t - t_ev, 3), n) for t, n in row.phases if t_ev - R.E_PRE_S <= t <= be["t_end_s"]]
    rel_ev = [(round(t - t_ev, 3), n) for t, n in row.events if t_ev - R.E_PRE_S <= t <= be["t_end_s"]]
    att0 = rows[0, 17:19]
    pre = row.tF < t_ev - R.E_PRE_S
    branch = s9e.BranchResult(ev["event_id"], {"depth": ev["depth_m"], "ramp": ev["ramp_s"]},
                              R.LEGS.index(ev["leg"]), t_ev, np.asarray(att0, float), rows,
                              phases=rel_ph, events=rel_ev, controller=_NoController())
    branch.crawler_clear_end_mm = float("nan")
    fs = row.result.get("fs_kN")
    judged = s9e.judge_soil_event(branch, float(fs), params["head_area_m2"],
                                  float(row.s_motor[pre].max() * 1e3) if pre.any() else 0.0)
    judged.pop("soil", None)
    return {"case": row.case, "folder": str(folder), "event_id": ev["event_id"], "t_ev_s": t_ev,
            "branch": be, "rows": int(len(rows)), "twist": judged.get("twist"),
            "tool_gates_record_not_used": judged.get("gates"), "tool_pass_record_not_used": judged.get("pass")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("out_dir")
    ap.add_argument("--git-at-start", required=True)
    ap.add_argument("folders", nargs="*")
    a = ap.parse_args(argv)
    repo, out_dir = Path(a.repo).resolve(), Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ref = a.git_at_start
    gate = tool_gate(repo, ref)
    doc = {"tool": "p2_e7.py", "tool_gate": gate, "rows": {}}
    n_err = 0
    if gate["ok"]:
        for p in (repo / "04_scripts" / "03_control" / "s9", repo / "04_scripts" / "03_control" / "s8"):
            sys.path.insert(0, str(p))
        import s9_soil_event_screen as s9e  # noqa: PLC0415  (the designated tool, R4-A2 table)
        params = C.load_params(repo)
        for f in a.folders:
            f = Path(f)
            try:
                rec = run_row(s9e, f, ["run_S9.py", "level"], params)
            except Exception as exc:  # noqa: BLE001  (recorded; the row is then 판정 불가)
                rec = {"case": f.name, "folder": str(f), "error": f"{type(exc).__name__}: {exc}"}
            n_err += 1 if rec.get("error") else 0
            doc["rows"][P.row_key(f)] = rec
    data = json.dumps(C.jsonable(doc), ensure_ascii=False, indent=1, default=str).encode("utf-8")
    p = out_dir / "e7_path2.json"
    p.write_bytes(data)
    print(json.dumps({"tool": "p2_e7.py", "gate_ok": gate["ok"], "rows": len(doc["rows"]), "row_errors": n_err,
                      "out": str(p), "out_sha256": sha(data)}))
    return 0 if gate["ok"] and n_err == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
