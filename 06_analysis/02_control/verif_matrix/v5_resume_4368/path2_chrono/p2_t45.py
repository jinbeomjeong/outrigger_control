"""rev4 R4-A2 option c (user decision Q-R4-1 = C): path 2 runs the sealed-rule tool
`chrono_t45_replay` itself for C-5 T4-0 / T4 / T5, under the four conditions of R4-A2:

1. tool files have 0 commits in `git log f46b5ab..HEAD -- <file>` (checked at run time);
2. the rev7 4 (line 95) tool regression on the 18 stored stage-3 rows reproduces the rev7 5 counts
   in the same commit;
3. output goes to the path 2 folder; path 1 output is never read;
4. grades are applied by path 2 (p2_kinds.items_c5), not taken from the tool's summary.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

BASE_COMMIT = "f46b5ab"   # rev4 R4-A2 condition 1 (436.8 rules sealing commit)
TOOL = "04_scripts/04_hydraulic/coupled/chrono_t45_replay.py"
GATED_FILES = (TOOL, "03_src/outrigger_sim/control/contact_replay.py")   # rev4 R4-0 list
RECORDED_FILES = ("04_scripts/04_hydraulic/coupled/j_p3_inputs.py",)    # imported, recorded only
# rev7 4 / 5: the 18 stored stage-3 L2b rows (rev6 3 rows 1-18: VB 12 + LS 6)
REG_ROWS = (
    "v5s3_VB_K0V_top_fup3.5_Fs0_", "v5s3_VB_K0_top_fup3.2_Fs0_", "v5s3_VB_K0V_top_roll5.5_Fs0_",
    "v5s3_VB_K0_top_fdown3.2_Fs0_", "v5s3_VB_K0V_top_fdown3.5_Fs0_", "v5s3_VB_E_G4_Fs8_",
    "v5s3_VB_K0_top_rpBop_Fs0_", "v5s3_VB_E_RE1bF_Fs0_", "v5s3_VB_E_RE1bF_Fs8_",
    "v5s3_VB_K8_top_rpB_Fs8_", "v5s3_VB_S_top_fdown3.5_wika_Fs8_", "v5s3_VB_K8_top_fdown3.5_Fs8_",
    "v5s3_LS1_K0V_top_fup3.5_Fs0_", "v5s3_LS4_K0V_top_fup3.5_Fs0_", "v5s3_LS1_E_G4_Fs8_",
    "v5s3_LS4_E_G4_Fs8_", "v5s3_LS1_E_RE1bF_Fs8_", "v5s3_LS4_E_RE1bF_Fs8_",
)
# rev7 4 line 95 / 5 table (rule text values)
REG_EXPECT = {
    "T4_judged_samples_rev6": 26380, "T4_judged_samples": 26210, "T4_e_excluded": 170,
    "T4_over_0p6kN_rev6": 75, "T4_raw_over_0p6kN": 5, "T5_over_0p6kN_rev6": 104,
    "T5_raw_over_0p6kN": 31, "T4_guard_violations": 0, "T5_guard_violations": 0,
    "sensor_model_rows": 1,
}
REG_EXPECT_TOP = {"T4_over_0p6kN": 0, "T5_over_0p6kN": 0}   # B1 applied own excess
REG_OWN_MAX_KN = 0.189                                       # rounded to 3 decimals in the rule


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(repo: Path, *args) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          encoding="utf-8", check=True).stdout


def tool_gate(repo: Path) -> dict:
    head = git(repo, "rev-parse", "HEAD").strip()
    files = {}
    ok = True
    for f in GATED_FILES + RECORDED_FILES:
        n = len([x for x in git(repo, "log", "--oneline", f"{BASE_COMMIT}..HEAD", "--", f).splitlines() if x])
        files[f] = {"commits_since_base": n, "sha256": sha(repo / f), "gated": f in GATED_FILES}
        if f in GATED_FILES and n != 0:
            ok = False
    return {"clause": "rev4 R4-A2 condition 1", "head": head, "base": BASE_COMMIT, "files": files, "ok": ok}


def run_tool(repo: Path, out_json: Path, cases: list) -> dict:
    cmd = [sys.executable, "-I", "-B", str(repo / TOOL), str(out_json), *map(str, cases), "--t5",
           "--criteria", "rev7"]
    p = subprocess.run(cmd, cwd=str(repo), capture_output=True, text=True, encoding="utf-8")
    rep = json.loads(out_json.read_text(encoding="utf-8")) if out_json.exists() else None
    return {"cmd": cmd, "rc": p.returncode, "stdout_tail": p.stdout[-1500:], "stderr_tail": p.stderr[-1500:],
            "report": rep, "out_sha256": sha(out_json) if out_json.exists() else None}


def regression(repo: Path, results_root: Path, out_dir: Path) -> dict:
    s8 = results_root / "S8"
    folders = []
    missing = []
    for pre in REG_ROWS:
        hits = sorted(d for d in s8.glob(pre + "*") if d.is_dir())
        if len(hits) != 1:
            missing.append(pre)
        else:
            folders.append(hits[0])
    out = {"clause": "rev4 R4-A2 condition 2 / rev7 4 line 95", "rows_found": len(folders), "missing": missing}
    if missing:
        out["ok"] = False
        return out
    r = run_tool(repo, out_dir / "t45_regression_stage3_18.json", folders)
    out.update(rc=r["rc"], out_sha256=r["out_sha256"], stderr_tail=r["stderr_tail"])
    rep = r["report"] or {}
    summ = rep.get("summary") or {}
    rev7 = summ.get("rev7") or {}
    got = {k: rev7.get(k) for k in REG_EXPECT}
    got.update({k: summ.get(k) for k in REG_EXPECT_TOP})
    own = [rev7.get("T4_max_own_excess_N"), rev7.get("T5_max_own_excess_N")]
    got["max_own_kN_rounded"] = [None if v is None else round(v / 1000.0, 3) for v in own]
    diff = {k: (got.get(k), v) for k, v in {**REG_EXPECT, **REG_EXPECT_TOP}.items() if got.get(k) != v}
    if any(x != REG_OWN_MAX_KN for x in got["max_own_kN_rounded"]):
        diff["max_own_kN_rounded"] = (got["max_own_kN_rounded"], REG_OWN_MAX_KN)
    out.update(got=got, differences=diff, ok=(r["rc"] == 0 and not diff and rep.get("criteria") == "rev7"))
    return out


def replay_rows(repo: Path, folders: list, out_dir: Path) -> dict:
    r = run_tool(repo, out_dir / "t45_replay_C5.json", folders)
    rows = {row.get("case"): row for row in ((r["report"] or {}).get("rows") or [])}
    return {"rc": r["rc"], "out_sha256": r["out_sha256"], "stderr_tail": r["stderr_tail"], "rows": rows,
            "criteria": (r["report"] or {}).get("criteria")}


def main(argv=None):
    """p2_t45.py <repo> <results_root> <out_dir> <case folder> [...]: gate + regression + replay."""
    a = list(sys.argv[1:] if argv is None else argv)
    repo, results_root, out_dir = Path(a[0]), Path(a[1]), Path(a[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    gate = tool_gate(repo)
    doc = {"tool_gate": gate}
    if gate["ok"]:
        doc["regression"] = regression(repo, results_root, out_dir)
        if doc["regression"]["ok"] and a[3:]:
            doc["replay"] = replay_rows(repo, [Path(x) for x in a[3:]], out_dir)
    p = out_dir / "t45_path2.json"
    data = json.dumps(doc, ensure_ascii=False, indent=1, default=str).encode("utf-8")
    p.write_bytes(data)
    ok = gate["ok"] and doc.get("regression", {}).get("ok", False)
    print(json.dumps({"tool": "p2_t45.py", "gate_ok": gate["ok"], "regression_ok": doc.get("regression", {}).get("ok"),
                      "out": str(p), "out_sha256": hashlib.sha256(data).hexdigest()}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
