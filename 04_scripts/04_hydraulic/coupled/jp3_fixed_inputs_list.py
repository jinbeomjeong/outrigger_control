"""436.9 edition 5 ``FIXED_INPUTS_<run commit 8>.SHA256SUMS`` (``jp3_remedy_spec_v5.md`` 6.6, 8 1;
erratum 1 9.1): the sha256 list of every fixed input of the edition 5 run steps, written once
from the run commit, never overwritten.

Entries (repository-relative paths, ``/`` separators, files under ``--repo``, the main
checkout):

* the lines of ``--entries`` (one path or one glob pattern per line; ``#`` starts a comment;
  a pattern must match at least one file), in their order;
* ``--x11-selection``: the X-11 ``selection.json`` (``jp3_12b_plan.py``) and every output it
  names (plans and key files of b1 .. b4 and the c dry check), each with the sha256 the
  selection recorded;
* ``--dry-selection``: the X-4 dry ``select`` output (``jp3_dryrun_evidence.py select``) and
  its three key files (g6 / g8 / ref), each with the fixed sha256 of erratum 1 9.1
  (``jp3_fixed_inputs.DRY_KEYS_FILE_SHA256_BY_FAMILY``);
* ``--add`` (repeatable): more files, e.g. the 12b L1 key file and the two L1 reference runs
  of erratum 2 2-1.

Checks (any miss: not usable, nothing written):

* ``--commit`` is a full sha; the run worktree's HEAD is that commit and its tracked tree is
  clean (a git failure is never read as clean);
* every entry exists; a code path (:data:`CODE_PREFIXES`) has the bytes of its blob in the
  run commit (``git cat-file blob <commit>:<path>``);
* a ``<file>.sha256`` entry names the sha256 of its ``<file>``;
* the case source ``h8_noise_VB.json`` is listed with ``jp3_fixed_inputs.NOISE_VB_SHA256``;
* the output name holds the commit's first 8 characters and does not exist.

Line form: ``<sha256> *<path>`` and LF (the edition 4a lists). Usage (python-dev, read only
but for ``--out``):
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_fixed_inputs_list.py --repo <main checkout>
      --worktree <run worktree> --commit <full sha> --entries <entries.txt>
      --x11-selection <x11 folder>/selection.json --dry-selection <dry select json>
      --out <main>/06_analysis/02_control/j_p3_cause/prelaunch_j9/FIXED_INPUTS_<c8>.SHA256SUMS

======  ===============  ======================================================================
exit    status           meaning
======  ===============  ======================================================================
0       ``written``      the list written
2       ``not_usable``   a check above failed, or an existing ``--out``
3       ``error``        a tool error (unreadable file, broken JSON)
======  ===============  ======================================================================

The stdout's last line is JSON with ``status``, the entry count and the output path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import jp3_fixed_inputs as fixed  # noqa: E402

FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
NOISE_PATH = "06_analysis/03_hydraulic/coupled/v5/resume_k1/h8_noise_VB.json"
SHA_SIDECAR_SUFFIX = ".sha256"
EXIT_WRITTEN, EXIT_NOT_USABLE, EXIT_ERROR = 0, 2, 3
GIT_TIMEOUT_S = 120
CODE_PREFIXES = ("02_params/", "03_src/", "04_scripts/", "05_tests/")
"""Code paths: listed only with the bytes of the run commit. Data, documents and the run steps
(``06_analysis/``, filled in the main checkout after the run commit, as in edition 4a) are the
main checkout's files."""


class NotUsable(Exception):
    """A check failed: no list is written (exit 2)."""


def file_sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _git(worktree: Path, *arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603 (git with fixed arguments)
        ["git", "-C", str(worktree), *arguments], capture_output=True, check=False,
        timeout=GIT_TIMEOUT_S)


def assert_run_commit(worktree: Path, commit: str) -> None:
    """HEAD = ``commit`` and a clean tracked tree; a git failure stops (never "clean")."""
    if not FULL_SHA.match(commit):
        raise NotUsable(f"--commit {commit!r} is not a full sha")
    head = _git(worktree, "rev-parse", "HEAD")
    if head.returncode != 0:
        raise NotUsable("git rev-parse failed (no identity)")
    if head.stdout.decode().strip() != commit:
        raise NotUsable(f"worktree HEAD {head.stdout.decode().strip()} is not {commit}")
    status = _git(worktree, "status", "--porcelain", "--untracked-files=no")
    if status.returncode != 0:
        raise NotUsable("git status failed (no identity)")
    if status.stdout.strip():
        raise NotUsable("the run worktree is not clean")


def read_entries(entries_file: Path, repo: Path) -> list[str]:
    """The paths of ``--entries`` (glob lines expanded in sorted order).

    Raises:
        NotUsable: A pattern without a match.
    """
    paths = []
    for raw in entries_file.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if any(mark in line for mark in "*?["):
            found = sorted(path.relative_to(repo).as_posix() for path in repo.glob(line)
                           if path.is_file())
            if not found:
                raise NotUsable(f"entry pattern {line!r} matches no file")
            paths += found
        else:
            paths.append(line)
    return paths


def x11_entries(selection: Path, repo: Path) -> dict[str, str]:
    """The X-11 selection and its outputs with the recorded sha256."""
    document = json.loads(selection.read_text(encoding="utf-8"))
    expected = {_relative(selection, repo): None}
    for name, sha in (document.get("outputs") or {}).items():
        expected[_relative(selection.parent / name, repo)] = sha
    if len(expected) == 1:
        raise NotUsable(f"{selection} names no output")
    return expected


def dry_entries(selection: Path, repo: Path) -> dict[str, str]:
    """The dry ``select`` output and its three key files with the fixed sha256 (9.1)."""
    document = json.loads(selection.read_text(encoding="utf-8"))
    expected = {_relative(selection, repo): None}
    families = document.get("r79_families") or {}
    for family, sha in fixed.DRY_KEYS_FILE_SHA256_BY_FAMILY.items():
        record = (families.get(family) or {}).get("keys_file") or {}
        if family == "g6":
            record = document.get("r79_keys_file") or record
        if not record.get("path"):
            raise NotUsable(f"dry selection without the {family} key file")
        expected[_relative(Path(record["path"]), repo)] = sha
    return expected


def _relative(path: Path, repo: Path) -> str:
    try:
        return Path(path).resolve().relative_to(repo.resolve()).as_posix()
    except ValueError as exc:
        raise NotUsable(f"{path} is not under --repo {repo}") from exc


def entry_problems(path: str, repo: Path, worktree: Path, commit: str,
                   expected: str | None) -> tuple[str | None, list[str]]:
    """The entry's sha256 and why it is not usable (empty: usable)."""
    file = repo / path
    if not file.is_file():
        return None, [f"{path}: missing"]
    actual = file_sha256(file)
    problems = []
    if expected is not None and actual != expected:
        problems.append(f"{path}: sha256 {actual[:12]} is not the recorded {expected[:12]}")
    if path.startswith(CODE_PREFIXES):
        blob = _git(worktree, "cat-file", "blob", f"{commit}:{path}")
        if blob.returncode != 0:
            problems.append(f"{path}: not in the run commit")
        elif hashlib.sha256(blob.stdout).hexdigest() != actual:
            problems.append(f"{path}: differs from its blob in the run commit")
    return actual, problems


def build_list(args: argparse.Namespace) -> list[tuple[str, str]]:
    """The (sha256, path) lines (module docstring).

    Raises:
        NotUsable: A check failed.
    """
    assert_run_commit(args.worktree, args.commit)
    expected: dict[str, str | None] = dict.fromkeys(read_entries(args.entries, args.repo))
    expected.update(x11_entries(args.x11_selection, args.repo))
    expected.update(dry_entries(args.dry_selection, args.repo))
    for path in args.add:  # erratum 2 2-1: the L1 key file and the two L1 runs
        expected.setdefault(_relative(path, args.repo), None)
    if NOISE_PATH not in expected:
        raise NotUsable(f"{NOISE_PATH} is not an entry")
    expected[NOISE_PATH] = fixed.NOISE_VB_SHA256
    lines, problems = [], []
    shas: dict[str, str] = {}
    for path, sha in expected.items():
        actual, found = entry_problems(path, args.repo, args.worktree, args.commit, sha)
        problems += found
        if actual is not None:
            shas[path] = actual
            lines.append((actual, path))
    for path in shas:
        target = path.removesuffix(SHA_SIDECAR_SUFFIX)
        if path.endswith(SHA_SIDECAR_SUFFIX) and target in shas:
            named = (args.repo / path).read_text(encoding="utf-8").split()
            if not named or named[0].lower() != shas[target]:
                problems.append(f"{path}: does not name the sha256 of {target}")
    if problems:
        raise NotUsable("; ".join(problems[:5]) + (f" (+{len(problems) - 5})"
                                                     if len(problems) > 5 else ""))
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo", type=Path, required=True, help="the main checkout")
    parser.add_argument("--worktree", type=Path, required=True, help="the run worktree")
    parser.add_argument("--commit", required=True, help="the run commit (full sha)")
    parser.add_argument("--entries", type=Path, required=True)
    parser.add_argument("--x11-selection", type=Path, required=True)
    parser.add_argument("--dry-selection", type=Path, required=True)
    parser.add_argument("--add", type=Path, action="append", default=[],
                        help="one more file under --repo (repeatable): the 12b L1 key file and "
                             "the two L1 reference runs (erratum 2 2-1)")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    status, count = "written", 0
    try:
        if args.out.exists():
            raise NotUsable(f"{args.out} exists (never overwritten)")
        if args.commit[:8] not in args.out.name:
            raise NotUsable(f"{args.out.name} does not name the run commit {args.commit[:8]}")
        lines = build_list(args)
        with args.out.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write("".join(f"{sha} *{path}\n" for sha, path in lines))
        count, code = len(lines), EXIT_WRITTEN
    except NotUsable as exc:
        print(f"not usable: {exc}", file=sys.stderr)
        status, code = "not_usable", EXIT_NOT_USABLE
    except Exception as exc:  # noqa: BLE001 (every other failure is a tool error)
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        status, code = "error", EXIT_ERROR
    print(json.dumps({"status": status, "entries": count, "out": str(args.out)}))
    return code


if __name__ == "__main__":
    sys.exit(main())
