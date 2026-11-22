"""436.9 addendum 4a-8 6.1: the static import closure of a runner against the files a commit
range changed (the VBJ re-judgement exception holds only when they do not meet).

The closure starts at ``--entry`` and follows, in every Python file it reaches:

* every ``import`` / ``from ... import`` statement anywhere in the file (module level, inside
  functions, ``try`` blocks; relative imports against the file's package), resolved against
  the search folders: ``03_src`` and every folder under ``04_scripts`` and ``05_tests`` that
  holds a ``.py`` file (the runners put such folders on ``sys.path``). A name found in several
  folders takes all of them (the conservative side); ``from a import b`` also takes a
  submodule ``a/b.py``; a package import takes its ``__init__.py`` files;
* every string literal ending in ``.py`` whose file name is a file of the search folders (a
  module loaded by ``importlib.util.spec_from_file_location``, e.g. ``las_t3_dg3.py``'s
  ``pre_las_preset_runner.py``).

Names outside the repository (standard library, installed packages) are not followed. Data
files (YAML parameters, keys files) are not code and are not part of the closure.

Edition 5 X-6 (``jp3_remedy_spec_v5.md`` 7): ``--entry`` may be given more than once (the
closure is the union of the entries'), and ``--with-run-tools`` adds :data:`RUN_TOOL_ENTRIES`
(the run identity wrapper every judged run goes through and the r79 grade tool the judges read
grades from), so a change of either meets the closure like a runner change.

Exit codes (and ``status``):

======  =================  ==========================================================
exit    status             meaning
======  =================  ==========================================================
0       ``disjoint``       no changed file is in the closure (the exception may be used)
1       ``meets``          a changed file is in the closure (4a-8 6.1: the full rerun)
2       ``input_error``    an entry outside the repository, a git failure, an existing
                           ``--out``
3       ``error``          an unexpected tool error
======  =================  ==========================================================

The stdout's last line is JSON with ``status``, the counts and the report path.

Usage (python-dev or dynamics-dev):
  python -I -B jp3_import_closure.py --repo <worktree> --entry
      04_scripts/04_hydraulic/coupled/las_t3_dg3.py --base 78fd5d2d --head <commit>
      --out <report.json>
"""
from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

SEARCH_TOPS = ("04_scripts", "05_tests")
SOURCE_TOP = "03_src"
SKIPPED_PARTS = ("__pycache__", ".git", ".venv", "venv")
EXIT_DISJOINT, EXIT_MEETS, EXIT_INPUT, EXIT_ERROR = 0, 1, 2, 3
RUN_TOOL_ENTRIES = ("04_scripts/04_hydraulic/coupled/jp3_run_identity.py",
                    "04_scripts/03_control/s8/r79_sensor_judge.py")
"""X-6: the identity wrapper of the judged runs and the r79 grade tool."""


class InputError(Exception):
    """A bad argument or a git failure (exit 2)."""


@dataclass
class Closure:
    """Files reached from the entry (repository-relative POSIX paths) and why."""

    repo: Path
    files: dict[str, str] = field(default_factory=dict)
    """Path -> the first file that reached it (the entry: itself)."""


def search_folders(repo: Path) -> list[Path]:
    """``03_src`` and every folder under ``04_scripts`` / ``05_tests`` with a ``.py`` file."""
    folders = [repo / SOURCE_TOP]
    for top in SEARCH_TOPS:
        folders += sorted({path.parent for path in (repo / top).rglob("*.py")
                           if not any(part in SKIPPED_PARTS for part in path.parts)})
    return [folder for folder in folders if folder.is_dir()]


def _module_files(folders: list[Path], dotted: str) -> list[Path]:
    """Files of ``dotted`` (the module or package and the packages above it)."""
    parts = dotted.split(".")
    found = []
    for folder in folders:
        module = folder.joinpath(*parts)
        for candidate in (module.with_suffix(".py"), module / "__init__.py"):
            if candidate.is_file():
                found.append(candidate)
                found += [folder.joinpath(*parts[:depth], "__init__.py")
                          for depth in range(1, len(parts))
                          if folder.joinpath(*parts[:depth], "__init__.py").is_file()]
    return found


def _package_of(path: Path, folders: list[Path]) -> list[str] | None:
    """The dotted package of ``path`` below the search folder holding it (relative imports)."""
    for folder in folders:
        try:
            relative = path.parent.relative_to(folder)
        except ValueError:
            continue
        return list(relative.parts)
    return None


def imported_names(path: Path, folders: list[Path]) -> tuple[set[str], set[str]]:
    """Dotted module names imported anywhere in ``path`` and ``.py`` file names in strings."""
    tree = ast.parse(path.read_bytes(), filename=str(path))
    names: set[str] = set()
    literals: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                package = _package_of(path, folders) or []
                keep = len(package) - (node.level - 1)
                base = ".".join([*package[:max(keep, 0)], *([base] if base else [])])
            if base:
                names.add(base)
            names.update(f"{base}.{alias.name}" if base else alias.name
                         for alias in node.names if alias.name != "*")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value.endswith(".py"):
                literals.add(Path(node.value.replace("\\", "/")).name)
    return names, literals


def import_closure(repo: Path, entry: Path | list[Path]) -> Closure:
    """The closure of ``entry`` (one path or several: the union; module docstring)."""
    entries = entry if isinstance(entry, list) else [entry]
    folders = search_folders(repo)
    by_file_name: dict[str, list[Path]] = {}
    for folder in folders:
        for path in folder.glob("*.py"):
            by_file_name.setdefault(path.name, []).append(path)
    closure = Closure(repo)
    todo = [(path, path) for path in entries]
    while todo:
        path, origin = todo.pop()
        relative = path.resolve().relative_to(repo).as_posix()
        if relative in closure.files:
            continue
        closure.files[relative] = origin.resolve().relative_to(repo).as_posix()
        names, literals = imported_names(path, folders)
        reached = [file for name in sorted(names) for file in _module_files(folders, name)]
        reached += [file for name in sorted(literals) for file in by_file_name.get(name, [])]
        todo += [(file, path) for file in reached]
    return closure


def changed_files(repo: Path, base: str, head: str) -> list[str]:
    """``git diff --name-only base head`` (a git failure is an input error, never empty)."""
    completed = subprocess.run(["git", "-C", str(repo), "diff", "--name-only", base, head],
                               capture_output=True, text=True, timeout=120)
    if completed.returncode != 0:
        raise InputError(f"git diff failed: {completed.stderr.strip()[:200]}")
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog="exit codes: 0 disjoint, 1 meets, 2 input error, "
                                            "3 tool error")
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--entry", required=True, action="append",
                        help="repository-relative runner path (repeat for more entries)")
    parser.add_argument("--with-run-tools", action="store_true",
                        help="add the run identity wrapper and the r79 grade tool (X-6)")
    parser.add_argument("--base", required=True, help="the commit the outputs were made at")
    parser.add_argument("--head", required=True, help="the fixed commit")
    parser.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    names = [*args.entry, *(RUN_TOOL_ENTRIES if args.with_run_tools else ())]
    report: dict = {"entry": args.entry[0] if len(names) == 1 else names, "base": args.base,
                    "head": args.head}
    try:
        if args.out.exists():
            raise InputError(f"{args.out} exists (never overwritten)")
        repo = args.repo.resolve()
        entries = []
        for name in names:
            entry = (repo / name).resolve()
            if not entry.is_file() or repo not in entry.parents:
                raise InputError(f"--entry {name} is not a file of {repo}")
            entries.append(entry)
        closure = import_closure(repo, entries)
        changed = changed_files(repo, args.base, args.head)
        meeting = sorted(set(changed) & set(closure.files))
        report.update(closure=sorted(closure.files), closure_files=len(closure.files),
                      reached_from=closure.files, changed=changed, meeting=meeting)
        status, code = (("meets", EXIT_MEETS) if meeting else ("disjoint", EXIT_DISJOINT))
    except InputError as exc:
        report["error"], status, code = str(exc), "input_error", EXIT_INPUT
    except Exception as exc:  # noqa: BLE001 (every other error is a tool error, exit 3)
        report["error"], status, code = f"{type(exc).__name__}: {exc}", "error", EXIT_ERROR
    report["status"] = status
    if not (code == EXIT_INPUT and args.out.exists()):
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({"status": status, "closure_files": report.get("closure_files"),
                      "changed": len(report.get("changed") or []),
                      "meeting": len(report.get("meeting") or []), "out": str(args.out)}))
    return code


if __name__ == "__main__":
    sys.exit(main())
