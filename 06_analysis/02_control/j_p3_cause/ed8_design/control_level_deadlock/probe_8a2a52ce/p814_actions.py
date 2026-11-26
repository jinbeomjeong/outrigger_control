"""Summary of the L-1 openings / shots and the L-2 waivers per line (record) from
p814_selection.json, plus the P8-15-form check (candidate line equal to B when it never acted).

Usage: conda run -n dynamics-dev python -I -B p814_actions.py   -> p814_actions_out.txt
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
doc = json.loads((HERE / "p814_selection.json").read_text("utf-8"))
lines = doc["lines"]
out = []
for name, v in lines.items():
    key, arm = name.rsplit("|", 1)
    if arm == "B" or v is None:
        continue
    b = lines[f"{key}|B"]
    acted = v["n_rise_open"] > 0 or v["n_waivers"] > 0
    same = v["sha"] == b["sha"]
    if not acted and not same:
        out.append(f"P8-15 FORM MISMATCH {name}")
    if arm == "L1" and v["n_rise_open"]:
        out.append(f"L1 {key}: open periods {v['n_rise_open']} (t, |D| kN, rise kN) {v['rise_open_rel']}; "
                   f"shots in open periods {v['shots_in_open']}; DONE {v['acted_dones']}; "
                   f"t_ready {v['t_ready']} (B {b['t_ready']}); same sha as B {same}")
    if arm == "L2" and v["n_waivers"]:
        ds = [w[1] for w in v["waivers_rel"]]
        rs = [w[2] for w in v["waivers_rel"]]
        out.append(f"L2 {key}: waiver periods {v['n_waivers']}, t {v['waivers_rel'][0][0]}..{v['waivers_rel'][-1][0]}, "
                   f"|D| {min(ds)}..{max(ds)} kN, rise {min(rs)}..{max(rs)} kN, legs {v['waivers_rel'][0][3]}; "
                   f"DONE {v['acted_dones']}; t_ready {v['t_ready']} (B {b['t_ready']}); same sha as B {same}")
n_same = {arm: sum(1 for n, v in lines.items() if n.endswith("|" + arm) and v
                   and v["sha"] == lines[n.rsplit("|", 1)[0] + "|B"]["sha"]) for arm in ("L1", "L2")}
out.append(f"lines equal to B: {n_same} of 27 keys")
text = "\n".join(out)
(HERE / "p814_actions_out.txt").write_text(text, "utf-8")
print(text.encode("ascii", "replace").decode())
