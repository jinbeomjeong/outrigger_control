"""T8'''' byte check (ed8-judge4 working tree): run path list blobs, 03_src tree, the
"do not change" files against T8''' 2263b246, the changed path set. Prints JSON only (no hashes
of judged data; git blob ids of code files only)."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

WT = Path(r"C:\workspace\outrigger_control\.claude\worktrees\ed8-judge4")
T8PPP = "2263b2461238da7f93eda147838c01c847315561"
C8 = "56849248371b4916e2fe683265e7abffdd6fb8d7"
COUPLED = "04_scripts/04_hydraulic/coupled/"
UNCHANGED = [COUPLED + name for name in (
    "jp3_ed8_judge.py", "jp3_tjr_judge_ed8.py", "jp3_ed8_rules.py", "p816_compare.py",
    "run_v5.py", "ed7_probe.py", "j_p3_inputs.py")]
UNCHANGED.append("05_tests/unit/test_ed8_gate_judge.py")
CHANGED = [COUPLED + "jp3_ed8_gate_judge.py", "05_tests/unit/test_ed8_gate_p80_key.py",
           "05_tests/unit/test_ed8_jp3_settings.py"]


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(WT), *args], capture_output=True, encoding="utf-8",
                          timeout=300, check=True).stdout


def main() -> int:
    out: dict = {"head": git("rev-parse", "HEAD").strip()}
    document = json.loads((WT / "05_tests/data/ed8_run_path_modules_56849248.json")
                          .read_text(encoding="utf-8"))
    mismatched = [entry["path"] for entry in document["files"]
                  if git("hash-object", str(WT / entry["path"])).strip() != entry["blob"]]
    out["run_path_files"] = len(document["files"])
    out["run_path_working_blob_mismatch"] = mismatched
    out["src_tree_head_eq_list"] = git("rev-parse", "HEAD:03_src").strip() == document["src_tree"]
    out["src_working_diff"] = git("diff", "--name-only", "HEAD", "--", "03_src").splitlines()
    out["unchanged_vs_t8ppp"] = {
        path: git("hash-object", str(WT / path)).strip() == git("rev-parse", f"{T8PPP}:{path}").strip()
        for path in UNCHANGED}
    out["diff_vs_t8ppp_working"] = git("diff", "--name-only", T8PPP).splitlines()
    out["untracked"] = git("ls-files", "--others", "--exclude-standard").splitlines()
    document_paths = {entry["path"] for entry in document["files"]}
    diff_c8 = git("diff", "--name-only", C8).splitlines()
    out["diff_vs_c8_working_count"] = len(diff_c8)
    out["diff_vs_c8_outside_scripts_tests"] = [
        path for path in diff_c8 if not path.startswith(("04_scripts/", "05_tests/"))]
    out["diff_vs_c8_in_run_path"] = [path for path in diff_c8 if path in document_paths]
    out["changed_files_sha256_raw"] = {
        path: hashlib.sha256((WT / path).read_bytes()).hexdigest() for path in CHANGED}
    out["changed_files_has_crlf"] = {path: b"\r\n" in (WT / path).read_bytes() for path in CHANGED}
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
