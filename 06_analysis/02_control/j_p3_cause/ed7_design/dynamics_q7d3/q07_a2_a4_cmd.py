"""Q7-D3: are arm a2 (condition (da)) and arm a4 (condition (na)) command-identical
on every probe 6bfb2560 main line? (commands_sha256 per key x plant, control table)."""
from pathlib import Path

import pandas as pd

F = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\control_v7_review\probe_6bfb2560_check\out\lines.csv")
d = pd.read_csv(F)
for other in ("a4", "a3"):
    x = d[d.arm == "a2"][["key", "plant", "part", "commands_sha256"]].merge(
        d[d.arm == other][["key", "plant", "part", "commands_sha256"]], on=["key", "plant", "part"], suffixes=("_a2", f"_{other}"))
    same = (x.commands_sha256_a2 == x[f"commands_sha256_{other}"])
    print(f"a2 vs {other}: pairs {len(x)}, identical commands {int(same.sum())}, different {int((~same).sum())}")
    if (~same).any():
        print(x[~same][["key", "plant", "part"]].to_string())
