"""Edition 8 run path module list at the run commit C8 (spec v8 11.2, P8-11; the edition 7
generator ``ed7_design/judge_commit_60ebb4a4/make_run_path_list.py`` with the edition 8 entries).

The run steps of C (``run_steps_ed7/*.ps1``) launch ``run_v5.py``, ``ed7_probe.py``,
``las_t3_dg3.py``, ``jp3_run_identity.py`` (wrap), ``jp3_12b_plan.py`` and, for the P7-4 suite,
``jp3_ed6_suite.py``; they dot-source ``run_steps/common.ps1`` and ``record_helper.ps1``. The
list holds those files and the static import closure of the Python entries
(``jp3_import_closure.import_closure``: imports anywhere in a file, ``.py`` names in strings),
computed on the tree of C itself (``git archive`` of C, never the working tree), each with its
git blob id at C, and the ``03_src`` tree id of C.

Usage (python-dev ``python.exe -I -B``):
  python -I -B make_run_path_list.py --repo <worktree> --commit <C> --work <empty scratch dir>
      --out <list.json>
Exit 0 written, 2 input error (an existing --out, a non-empty --work, git failure).
"""
from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

COUPLED = "04_scripts/04_hydraulic/coupled"
ENTRIES = tuple(f"{COUPLED}/{name}" for name in (
    "run_v5.py", "ed7_probe.py", "ed8_probe.py", "las_t3_dg3.py", "jp3_run_identity.py",
    "jp3_12b_plan.py", "jp3_ed6_suite.py"))
RUN_STEPS_ED7 = "06_analysis/02_control/j_p3_cause/prelaunch_j9/run_steps_ed8"
DOT_SOURCED = ("06_analysis/02_control/j_p3_cause/prelaunch_j9/run_steps/common.ps1",
               "06_analysis/02_control/j_p3_cause/prelaunch_j9/run_steps/record_helper.ps1",
               "06_analysis/02_control/j_p3_cause/prelaunch_j9/run_steps_ed7/core_kind_ed7.ps1")
ARCHIVE_PATHS = ("03_src", "04_scripts", "05_tests", RUN_STEPS_ED7, *DOT_SOURCED)


def git(repo: Path, *args: str, text: bool = True):
    completed = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=text,
                               timeout=600, check=False)
    if completed.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {completed.stderr!s:.300}")
    return completed.stdout


def extract_tree(repo: Path, commit: str, work: Path) -> Path:
    data = git(repo, "archive", "--format=tar", commit, "--", *ARCHIVE_PATHS, text=False)
    tree = work / "tree"
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        archive.extractall(tree, filter="data")
    return tree


def blob_ids(repo: Path, commit: str, paths: list[str]) -> dict[str, str]:
    out = {}
    listing = git(repo, "ls-tree", "-r", commit, "--", *paths)
    for line in listing.splitlines():
        meta, path = line.split("\t", 1)
        out[path] = meta.split()[2]
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists() or (args.work.exists() and any(args.work.iterdir())):
        print(json.dumps({"status": "input_error", "reason": "--out exists or --work not empty"}))
        return 2
    commit = git(args.repo, "rev-parse", f"{args.commit}^{{commit}}").strip()
    tree = extract_tree(args.repo, commit, args.work)
    sys.path.insert(0, str(tree / COUPLED))
    import jp3_import_closure as closure_tool  # the tool as it is at C

    closure = closure_tool.import_closure(tree.resolve(), [tree / entry for entry in ENTRIES])
    python_files = sorted(path for path in closure.files if not path.startswith("03_src/"))
    ps1_files = sorted(path.relative_to(tree).as_posix()
                       for path in (tree / RUN_STEPS_ED7).rglob("*") if path.is_file())
    listed = sorted({*python_files, *ps1_files, *DOT_SOURCED})
    blobs = blob_ids(args.repo, commit, listed)
    missing = [path for path in listed if path not in blobs]
    if missing:
        raise SystemExit(f"no blob at {commit} for {missing[:3]}")
    document = {
        "rule": "jp3_remedy_spec_v8_rules.md 11.2 / P8-11: the run path modules of the run "
                "commit C8 (entries, their static import closure outside 03_src, the run steps "
                "ps1 / json and the dot-sourced ps1); T8 keeps them byte-identical",
        "run_commit": commit,
        "src_tree": git(args.repo, "rev-parse", f"{commit}:03_src").strip(),
        "entries": list(ENTRIES), "dot_sourced": list(DOT_SOURCED),
        "closure_python_files_outside_03_src": len(python_files),
        "closure_03_src_files": sum(path.startswith("03_src/") for path in closure.files),
        "run_steps_files": len(ps1_files),
        "generator": "make_run_path_list_ed8.py (impl_report_ed8 evidence folder)",
        "files": [{"path": path, "blob": blobs[path]} for path in listed]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(document, indent=1) + "\n")
    print(json.dumps({"status": "written", "files": len(listed), "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
