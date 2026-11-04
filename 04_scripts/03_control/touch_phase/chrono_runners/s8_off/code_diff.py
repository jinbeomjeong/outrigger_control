"""Compare stored-run code state, the commit it ran on, the main branch head and the main tree files.

Git runs in the worktree (same repository objects). Main-tree files are only read. Blob comparison normalizes CRLF to LF.
Usage: python -I code_diff.py
"""
import hashlib
import json
import subprocess
from pathlib import Path

WT = Path(r"C:\workspace\outrigger_control\.claude\worktrees\agent-ae9039e69988d5282")
MAIN = Path(r"C:\workspace\outrigger_control")
D = MAIN / "07_results/S9/batch_FINAL-REP_20261030_223359/S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0"
OUT = Path(__file__).resolve().parent / "code_diff.json"
PATHS = ("03_src", "04_scripts/02_chrono/run_S9.py", "02_params/rexome33.yaml", "02_params/scm_soil_sets.json", "02_params/pad_variants.json")


def git(*a: str) -> str:
    return subprocess.run(["git", *a], cwd=WT, capture_output=True, text=True, encoding="utf-8", check=True,
                          stdin=subprocess.DEVNULL).stdout


def sha(data: bytes) -> str:
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


r = json.loads((D / "result.json").read_text(encoding="utf-8"))
cs = r["code_state"]
print("git_at_start", json.dumps(cs["git_at_start"])[:900])
print("files_at_start", json.dumps(cs["files_at_start"])[:700])
stored = cs["git_at_start"].get("commit") or cs["git_at_start"].get("head")
head_txt = (MAIN / ".git/refs/heads/master").read_text(encoding="utf-8").strip()
print("stored commit", stored, "main head", head_txt)
files = [ln for ln in git("ls-tree", "-r", "--name-only", head_txt, "--", *PATHS).splitlines()]
stored_files = set(git("ls-tree", "-r", "--name-only", stored, "--", *PATHS).splitlines())
report = {"stored_commit": stored, "main_head": head_txt, "commit_vs_head": [], "head_vs_tree": [], "only_stored": sorted(stored_files - set(files))}
for f in files:
    head_blob = subprocess.run(["git", "show", f"{head_txt}:{f}"], cwd=WT, capture_output=True, check=True, stdin=subprocess.DEVNULL).stdout
    tree = MAIN / f
    if f in stored_files:
        old = subprocess.run(["git", "show", f"{stored}:{f}"], cwd=WT, capture_output=True, check=True, stdin=subprocess.DEVNULL).stdout
        if sha(old) != sha(head_blob):
            report["commit_vs_head"].append(f)
    else:
        report["commit_vs_head"].append(f + " (new)")
    if not tree.exists() or sha(tree.read_bytes()) != sha(head_blob):
        report["head_vs_tree"].append(f)
extra = [str(p.relative_to(MAIN)).replace("\\", "/") for p in (MAIN / "03_src").rglob("*.py") if str(p.relative_to(MAIN)).replace("\\", "/") not in set(files)]
report["tree_only"] = extra
OUT.write_text(json.dumps(report, indent=1), encoding="utf-8")
print(json.dumps(report, indent=1))
print(git("log", "--oneline", f"{stored}..{head_txt}", "--", *PATHS)[:1800])
print(git("diff", "--stat", stored, head_txt, "--", *PATHS)[-1600:])
