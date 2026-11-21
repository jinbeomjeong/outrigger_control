"""Does the r79 runner take the stored H-6 as --keys-file for --levels L2,L3 (no run)?"""
import sys
from pathlib import Path

root, h6 = sys.argv[1], sys.argv[2]
sys.argv = [sys.argv[0], root]  # the r51 / r64 harness modules read sys.argv[1] as ROOT
sys.path.insert(0, str(Path(root) / "04_scripts" / "03_control" / "s8"))
import r79_L3L4_final as final  # noqa: E402

keys = final.read_keys_file(Path(h6))
problems = final.keys_file_problems(keys, ["L2", "L3"])
print("keys", len(keys), "problems", len(problems), problems[:2])
