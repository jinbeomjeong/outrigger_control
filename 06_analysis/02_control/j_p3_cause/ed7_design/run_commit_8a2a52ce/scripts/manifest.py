"""Write manifest.json of the run commit C evidence folder (identity, constants, checks, steps)."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

RUN_COMMIT = "8a2a52ce2c07d2af11a6212a2932d2061261f156"
IMPL_COMMIT = "b46bdf8fdbad730eabf9226c5e1cfed0e980b5e9"
STEPS = [
    ("step5_impl_ed7.ps1 -Part scope", "impl_scope", "P7-10 evidence (git diff), no run", 0),
    ("step_l1ref_ed7.ps1", "l1ref", "L1_VBM0 / L1_VBM 167 + 167, L1a_VBM0 / L1a_VBM 102 + 102", 538),
    ("step5_impl_ed7.ps1 -Part t8", "impl_t8", "P7-1 run_v5 ed7_t8 (22 jobs x VBM, VBM0)", 44),
    ("step5_impl_ed7.ps1 -Part cases", "impl_cases", "P7-2 run_v5 ed7_cases (E, F x 5)", 10),
    ("step5_impl_ed7.ps1 -Part probe", "impl_probe", "P7-3 / P7-9 ed7_probe --arms a2 --part all", 114),
    ("step6_confirm_ed7.ps1", "confirm", "G1 ed7_keys 171 + ed7_probe --part d 24", 195),
    ("step7_j9main_ed7.ps1", "j9main", "run_v5 ed7_j9_main", 388),
    ("step8_sens_ed7.ps1", "sens", "run_v5 ed7_keys sens_keys_ed7.json", 460),
    ("step9_dg3_ed7.ps1", "dg3", "T-JR-12a VBM / VBM0 on the 135 H-6 keys", 270),
    ("step10a_plan_ed7.ps1", "12b_plan", "jp3_12b_plan.py --edition 7 (no run)", 0),
    ("step10b_vbkm0_ed7.ps1 -Phase base", "12b_vbkm0", "VBKM0 b1 / b2 (167 each)", 334),
    ("step10b_vbkm0_ed7.ps1 -Phase b4 (T decision needs_b4)", "12b_vbkm0_b4", "VBKM0 b4", 167),
    ("step10c_vbkm_ed7.ps1 (T decision decided)", "12b_vbkm", "VBKM of the decided blocks",
     "334 (b1, b2) or 501 (with b4)"),
]


def git(worktree: Path, *arguments: str) -> str:
    return subprocess.run(["git", "-C", str(worktree), *arguments], check=True,
                          capture_output=True, text=True).stdout.strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    worktree, folder = Path(sys.argv[1]), Path(sys.argv[2])
    files = {str(path.relative_to(folder)).replace("\\", "/"): sha256(path)
             for path in sorted(folder.rglob("*")) if path.is_file() and path.name != "manifest.json"}
    manifest = {
        "purpose": "436.9 edition 7 run commit C (jp3_remedy_spec_v7.md revision 6, 5.1)",
        "run_commit": RUN_COMMIT, "parent": IMPL_COMMIT,
        "parent_of_run_commit": git(worktree, "rev-parse", f"{RUN_COMMIT}^"),
        "src_tree_03": git(worktree, "rev-parse", f"{RUN_COMMIT}:03_src"),
        "worktree": str(worktree), "worktree_head": git(worktree, "rev-parse", "HEAD"),
        "worktree_status_porcelain": git(worktree, "status", "--porcelain"),
        "sealed_spec_sha256": "10902ffdb763aa092588b1be0dd13f55874826b489f9aa9f1351dd7f48c1da45",
        "constants": {"JP3_SPEC_EDITION_V7": "10902ffd",
                      "ED7_KEY_FILE_SHA256": {
                          "sens_keys_ed7.json": "be930b75a375877d07fc84fa98a9f8b0ee463f5b592319cfd6869fcc62a05b1b",
                          "confirm_g1_grid171.json": "684054abb1ad05d8f82141f58eafdfa3c096edae1c05c9a4b9e8ae9ffe5b5dec"}},
        "changed_paths": git(worktree, "diff", "--name-only", IMPL_COMMIT, RUN_COMMIT).splitlines(),
        "run_steps": [{"command": command, "step": step, "content": content, "lines": lines}
                      for command, step, content, lines in STEPS],
        "checks": {
            "p7_10_scope": "Get-ScopeProblem passed in every dry step; diff_name_only.txt / diff_03_src.txt",
            "tests_at_c": "tests_at_c/tests_record.json",
            "ps1_lint": "ps1_lint.json", "placeholder_scan": "placeholder_scan.json",
            "ruff": "ruff_check.txt (3 E501 in run_v5.py lines 927 / 932 / 936, present at b46bdf8f)",
            "codespell": "codespell.txt (empty: no finding)",
            "dry_run": "dry_run/commands_ed7.json, dry_run/dry1_summary.txt",
            "refusals": "dry_run/refusals_console.txt (scripts/refusals.ps1)",
            "list_counts": "list_counts/*.txt (scripts/list_counts.ps1, --list only)",
            "core_kind": "core_kind_check.txt (scripts/core_kind_check.ps1)",
            "mtime": "mtime_vs_commit.json (ed7-impl worktree files vs the commit time)"},
        "files_sha256": files,
    }
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n",
                                          encoding="utf-8")
    print(json.dumps({"files": len(files)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
