"""Check (no blind data): the P8-0 producer plan keys under the producer job key and under the
T8''' gate row_identity, the T8''' p80 signature on synthetic producer-shaped lines, and the
pinned reference (git blob of e241638d and main checkout copy): sha, key set vs plan.
Prints counts only (no command hashes)."""
from __future__ import annotations

import collections
import hashlib
import json
import subprocess
import sys
from pathlib import Path

WT = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed8-judge3")
MAIN = Path(r"C:\workspace\outrigger_control")
REF_REL = "06_analysis/02_control/j_p3_cause/j9_runs/b46bdf8f/repro_a2/ed7_probe_a2.jsonl"
for p in (WT / "04_scripts" / "04_hydraulic" / "coupled", WT / "03_src"):
    sys.path.insert(0, str(p))

import ed7_probe  # noqa: E402
import jp3_ed8_gate_judge as gate  # noqa: E402
import run_v5  # noqa: E402

out: dict = {}
jobs = ed7_probe.probe_jobs(arms=("a2",), part="all")
out["plan_jobs"] = len(jobs)
out["plan_settings"] = dict(collections.Counter(j["setting"] for j in jobs))
out["run_v5_runtime_keys"] = list(run_v5.RUNTIME_JOB_KEYS)
withrt = [{**j, "mask": 255, "t4h_dir": "x"} for j in jobs]
out["distinct_producer_job_key"] = len({run_v5.job_key(j) for j in withrt})
out["distinct_gate_row_identity"] = len({gate.row_identity(j) for j in withrt})

# synthetic producer-shaped lines: a unique fake hash per producer job key
lines = [{"job": j, "commands_sha256": hashlib.sha256(run_v5.job_key(j).encode()).hexdigest()}
         for j in withrt]
rep = gate.judge_p80(lines, list(reversed(lines)))
out["t8ppp_on_synthetic"] = {"status": rep["status"], "jobs": rep["jobs"], "equal": rep["equal"],
                             "line_problems": len(rep["line_problems"]),
                             "basis": rep["status_basis"]}

# pinned reference: blob and main checkout copy
blob = subprocess.run(["git", "-C", str(MAIN), "show", f"e241638d:{REF_REL}"],
                      capture_output=True, check=True).stdout
disk = (MAIN / REF_REL).read_bytes()
out["ref_blob_sha_ok"] = hashlib.sha256(blob).hexdigest() == gate.P80_REFERENCE_SHA256
out["ref_disk_sha_ok"] = hashlib.sha256(disk).hexdigest() == gate.P80_REFERENCE_SHA256
ref = [json.loads(x) for x in blob.decode("utf-8").splitlines() if x.strip()]
out["ref_lines"] = len(ref)
ref_keys = [run_v5.job_key(r.get("job") or {}) for r in ref]
out["ref_distinct_producer_key"] = len(set(ref_keys))
out["ref_keys_equal_plan"] = set(ref_keys) == {run_v5.job_key(j) for j in withrt}
out["ref_extra_job_fields"] = sorted({k for r in ref for k in (r.get("job") or {})}
                                     - {k for j in withrt for k in j})
print(json.dumps(out, indent=1))
