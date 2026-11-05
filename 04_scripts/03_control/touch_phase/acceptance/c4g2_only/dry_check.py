"""Dry check without simulation: job lists of the harness under ACC_COMBO=c4g2 against the seeded keys, and the preset the combination gives. Uses the env of steps_c4g2only.json. Prints to-run counts."""
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
steps = {s["id"]: s for s in json.loads((HERE / "steps_c4g2only.json").read_text(encoding="utf-8"))}
OUT = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\touch_phase\acceptance\c4g2_only")
manifest = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))["files"]
for sid, name, levels in (("noise_L1L2", "r79_L1L2", "L1,L2"), ("noise_L3", "r79_L3", "L3")):
    st = steps[sid]
    head = st["cmd"].split(" run ")[0]
    env = {**os.environ, **{k: v for k, v in st["env"].items() if k != "ACC_PROVENANCE"}}
    r = subprocess.run(head.split() + ["list", "--levels", levels], env=env, cwd=st["cwd"], capture_output=True, text=True, timeout=300)
    print("list stdout head", r.stdout[:300].replace("\n", " / "), "tail", r.stdout[-200:].replace("\n", " / "))
    lines = [x for x in r.stdout.splitlines() if "|" in x]
    keys = {("cand=current#" + x.split()[0]) if not x.startswith("cand=") else x.split()[0] for x in lines}
    seeded = set()
    for line in (OUT / f"noise/{name}.json.partial.jsonl").read_text(encoding="utf-8").splitlines():
        seeded.add(json.loads(line)["key"])
    print(name, "rc", r.returncode, "job list", len(keys), "seeded", len(seeded), "seeded not in list", len(seeded - keys), "to run", len(keys - seeded), "manifest to run", manifest[name]["to_run"], "stderr tail", r.stderr[-200:] if r.returncode else "")
env = {**os.environ, **steps["noise_L1L2"]["env"]}
env.pop("ACC_PROVENANCE", None)
code = "import sys; sys.path.insert(0, r'" + str(HERE.parent / "c4g2k1") + "'); import acc_common as a, json; a.install(); p = a.provenance(); print(json.dumps({k: p[k] for k in ('combo', 'git_head', 'c2_sha256', 'touch_twist_hold', 'vector_ramp', 'retrigger_samples')}))"
r = subprocess.run([sys.executable, "-I", "-B", "-c", code], env=env, cwd=steps["noise_L1L2"]["cwd"], capture_output=True, text=True, timeout=120)
print(r.stdout.strip(), r.stderr[-300:])
