"""Changed line ranges of the harness judgement vs HEAD, new sha256, line endings, placeholder leftovers."""
import difflib
import hashlib
import json
import subprocess
from pathlib import Path

REPO = r"C:\workspace\outrigger_control"
REL = "06_analysis/02_control/verif_matrix/v5_resume_4368_harness_judgement.md"
old = subprocess.run(["git", "-C", REPO, "show", f"HEAD:{REL}"], capture_output=True, timeout=60).stdout
new = (Path(REPO) / REL).read_bytes()
a, b = old.decode("utf-8").splitlines(), new.decode("utf-8").splitlines()
ops = [(t, i1 + 1, i2, j1 + 1, j2) for t, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
       if t != "equal"]
print(json.dumps({"old_sha256": hashlib.sha256(old).hexdigest(), "new_sha256": hashlib.sha256(new).hexdigest(),
                  "old_lines": len(a), "new_lines": len(b), "cr": new.count(b"\r"), "ends_lf": new.endswith(b"\n"),
                  "ops": ops, "placeholder_left": new.decode("utf-8").count("<G-5 사용자 결정>")}, ensure_ascii=False,
                 indent=1))
