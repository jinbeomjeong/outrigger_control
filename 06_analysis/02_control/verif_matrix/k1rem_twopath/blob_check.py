"""Recompute HEAD blob sha256 (git show, raw bytes) for the K-2 files and compare with prelaunch/postrun."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control")
K1 = ROOT / "06_analysis/03_hydraulic/coupled/v5/las/k1"
pre = json.loads((K1 / "rem_prelaunch.json").read_text(encoding="utf-8"))["code_files"]["files"]
post = json.loads((K1 / "rem_postrun.json").read_text(encoding="utf-8"))["code_files"]["files"]
out = {}
for rel, rec in pre.items():
    blob = subprocess.run(["git", "-C", str(ROOT), "show", f"HEAD:{rel}"], capture_output=True, check=True).stdout
    wt = (ROOT / rel).read_bytes()
    b = hashlib.sha256(blob).hexdigest()
    w = hashlib.sha256(wt).hexdigest()
    out[rel] = dict(blob_ok=(b == rec["blob_sha256"] == post[rel]["blob_sha256"]),
                    wt_ok=(w == rec["worktree_sha256"] == post[rel]["worktree_sha256"]), blob8=b[:8], wt8=w[:8])
base = subprocess.run(["git", "-C", str(ROOT), "show", "859deef:03_src/outrigger_sim/control/c2.py"],
                      capture_output=True, check=True).stdout
out["c2_blob_eq_859deef"] = hashlib.sha256(base).hexdigest() == pre["03_src/outrigger_sim/control/c2.py"]["blob_sha256"]
print(json.dumps(out, indent=1))
print("ALL_OK", all(v["blob_ok"] and v["wt_ok"] for k, v in out.items() if isinstance(v, dict)) and out["c2_blob_eq_859deef"])
