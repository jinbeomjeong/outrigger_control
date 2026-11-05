"""L1 harness pass of the final merged r79 study with the judge's own definition (read-only).

Uses r79_sensor_judge.harness_verdict(base, run) exactly as the 'reference' block (line 478) does, on the L1
records of fin_r79_merged.json; splits pad A (ref '<soil>|A|0,0') from the rest.  Also prints the plain
base['pass'] count for comparison (python-expert's 159/183).
"""
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(r"C:\workspace\outrigger_control")
spec = importlib.util.spec_from_file_location("r79j", ROOT / "04_scripts/03_control/s8/r79_sensor_judge.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
res = json.loads((ROOT / "06_analysis/02_control/s8/rev79/fin_r79_merged.json").read_text(encoding="utf-8"))["results"]
L1 = [r for r in res if r["level"] == "L1"]


def pad_a(inner):
    return re.fullmatch(r"(G1|J1|J2|S1)\|A\|.*", inner) is not None


for name, sel in (("all", L1), ("pad B", [r for r in L1 if not pad_a(r["inner"])]),
                  ("pad A", [r for r in L1 if pad_a(r["inner"])])):
    hv = sum(bool(mod.harness_verdict(r["base"], r)) for r in sel)
    bp = sum(bool(r["base"].get("pass")) for r in sel)
    print(f"{name}: n {len(sel)}  harness_verdict {hv}  base.pass {bp}")
fails = [r["inner"] for r in L1 if not mod.harness_verdict(r["base"], r)]
print("harness_verdict failures:", fails)
