"""Fill the K-2 command slots from the placement table and write step lists (reads, writes only in the sched folder).

Usage: python -I -B build_runners.py
"""
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLACEMENT = HERE / "k2_placement_20261110.json"
pl = json.loads(PLACEMENT.read_text(encoding="utf-8"))
WT = pl["run_wt"]
SRC = Path(WT) / pl["commands_source"]
cmds = json.loads(SRC.read_text(encoding="utf-8"))
steps = cmds["steps"]
byid = {s["id"]: s for s in steps}

POOL = pl["slots"]["{POOL}"]
MASK = pl["slots"]["{MASK}"]
WORKERS = pl["slots"]["{WORKERS}"]
APPEND_V7 = pl["v7_appended_args"]


def fill(text, step):
    b = step["bundle"]
    eng = step.get("engine")
    rep = {"{POOL}": POOL[b]}
    if b in MASK:
        rep["{MASK}"] = MASK[b]
        rep["{WORKERS}"] = str(WORKERS[b])
    if b == "v6" and eng == "L1":
        rep["{PLACEMENT}"] = pl["slots"]["{PLACEMENT}"]["v6_L1"]
    if b == "v6" and eng == "L2b":
        rep["{L2B_WORKERS}"] = pl["slots"]["{L2B_WORKERS}"]["v6_L2b"]
    if b == "v7":
        rep["{P}"] = str(pl["slots"]["{P}"]["v7"])
    for k, v in rep.items():
        text = text.replace(k, v)
    return text


def fill_obj(o, step):
    if isinstance(o, str):
        return fill(o, step)
    if isinstance(o, list):
        return [fill_obj(x, step) for x in o]
    if isinstance(o, dict):
        return {k: fill_obj(v, step) for k, v in o.items()}
    return o


filled = []
for s in steps:
    f = fill_obj(s, s)
    if s["bundle"] == "v7":
        f["argv"] = f["argv"] + APPEND_V7
        f["appended_args_note"] = "plan k2-sched-20261110a: E pool, 4 rows at once"
    filled.append(f)

# only the runtime slot {BATCH_V7} may remain
left = {}
for f in filled:
    for m in re.findall(r"\{[A-Z_0-9]+\}", json.dumps(f, ensure_ascii=False)):
        left.setdefault(m, []).append(f["id"])
assert set(left) <= {"{BATCH_V7}", "{RUN_HEAD}"}, left

out = dict(cmds)
out["steps"] = filled
out["plan_id"] = pl["plan_id"]
(HERE / "k2_commands_filled.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")


def cmd_string(argv):
    toks = []
    for t in argv:
        assert not re.search(r"""[\s"']""", t), t
        toks.append(t)
    return " ".join(toks)


def to_step(f):
    return {"id": f["id"], "cmd": cmd_string(f["argv"]), "cwd": f["cwd"], "env": f.get("env", {})}


# order ------------------------------------------------------------------
def pair(stem):
    return [stem + "_off", stem + "_tcl"]


p_main = []
p_main += pair("v2_k1off") + pair("v2_k1on")
p_main += pair("v4")[0:0] + ["v4_off", "v4_tcl"]
for aug in ("H0", "L1eq", "L1eq_fs", "L1eq_zm", "AUG", "AUG_crc2", "AUG_eps"):
    p_main += [f"v3_{aug}_off", f"v3_{aug}_tcl"]
v5_names = ["reg1", "reg2", "reg3", "reg4", "reg5", "reg6", "reg7", "grid_r67_main", "grid_r67_top", "grid_r69_top",
            "grid_r69_bottom", "soil_A", "d8", "noise_L1L2", "ps7", "g8_jobs1", "g8_jobs3", "g8_jobs5"]
for n in v5_names:
    p_main += [f"v5_{n}_off", f"v5_{n}_tcl"]
p_post = []
for arm in ("off", "tcl"):
    p_post += [f"v5_judge_r79_L1L2_{arm}", f"v5_judge_clip_r79_L1L2_{arm}", f"v5_flatten_{arm}"]

lanes = {
    "P_main": p_main,
    "P_post": p_post,
    "E_pre": ["v6_snaps_k2_check"],
    "E_V6_off": ["v6_L1_off", "v6_L2b_off"],
    "E_V6_tcl": ["v6_L1_tcl", "v6_L2b_tcl"],
    "E_V7": ["v7_k2_v7"],
}
used = [i for v in lanes.values() for i in v]
allids = [s["id"] for s in steps]
assert sorted(used) == sorted(allids), (set(allids) - set(used), set(used) - set(allids))
assert len(used) == len(set(used)) == 68
fby = {f["id"]: f for f in filled}
manifest = {"plan_id": pl["plan_id"], "lanes": {}}
for lane, ids in lanes.items():
    sj = [to_step(fby[i]) for i in ids]
    p = HERE / f"steps_{lane}.json"
    p.write_text(json.dumps(sj, indent=1, ensure_ascii=False), encoding="utf-8")
    manifest["lanes"][lane] = {"steps_file": str(p), "n": len(ids), "ids": ids}
# done-marker list for the P_post gate
manifest["p_main_done_markers_file"] = str(HERE / "p_main_done_markers.txt")
LOGS = HERE / "logs"
(HERE / "p_main_done_markers.txt").write_text(
    "\n".join(str(LOGS / "P_main" / f"{i}.done") for i in p_main if i.startswith("v5_")), encoding="utf-8")
manifest["p_main_v5_step_count"] = sum(1 for i in p_main if i.startswith("v5_"))
(HERE / "k2_sched_lanes.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
print(json.dumps({"filled_left": left, "lanes": {k: len(v) for k, v in lanes.items()}, "v5_gate": manifest["p_main_v5_step_count"]}))
print("filled_sha256", hashlib.sha256((HERE / "k2_commands_filled.json").read_bytes()).hexdigest())
print("src_sha256", hashlib.sha256(SRC.read_bytes()).hexdigest())
