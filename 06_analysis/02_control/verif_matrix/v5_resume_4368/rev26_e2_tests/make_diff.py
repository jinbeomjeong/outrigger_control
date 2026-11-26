"""Write the r5 -> r6 unified diff (LF) and print sha256 / line-ending facts of the erratum 2 files."""
import difflib
import hashlib
import json
from pathlib import Path

FIX = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368")
R5 = FIX / "rev26_fixed" / "excl_fields_r5.py"
E2 = FIX / "rev26_e2_fixed"
R6 = E2 / "excl_fields_r6.py"
DIFF = E2 / "excl_fields_r5_to_r6.diff"

a = R5.read_bytes().decode("utf-8").splitlines(keepends=True)
b = R6.read_bytes().decode("utf-8").splitlines(keepends=True)
text = "".join(difflib.unified_diff(a, b, "rev26_fixed/excl_fields_r5.py", "rev26_e2_fixed/excl_fields_r6.py", n=1))
DIFF.write_bytes(text.encode("utf-8"))
out = {}
for p in (R5, R6, DIFF, E2 / "list_diff_r5_r6.py"):
    raw = p.read_bytes()
    out[p.name] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "cr": raw.count(b"\r"),
                   "lines": raw.count(b"\n"), "ends_lf": raw.endswith(b"\n")}
sm = difflib.SequenceMatcher(None, a, b)
out["opcodes"] = [(t, i1 + 1, i2, j1 + 1, j2) for t, i1, i2, j1, j2 in sm.get_opcodes() if t != "equal"]
print(json.dumps(out, indent=1))
print(text)
