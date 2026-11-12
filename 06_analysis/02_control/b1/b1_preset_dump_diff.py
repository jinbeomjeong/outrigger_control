"""B1 rules I-17 (CR-1): R8 preset dump of ``HEAD_M`` against the base commit ``e67dae8``.

Rules: ``b1_creep_rules.md`` 1.2 CR-1 and 4.1 I-17 (sealed 2026-11-12,
:data:`RULES_SHA256`). The check: every field present in both dumps of
``C2Config().with_10hz_d1()`` has the same value; every field that is new since the base
(present only at ``HEAD_M``) equals its class default at ``HEAD_M`` (``C2Config()``, i.e. off).
A field that the base has and ``HEAD_M`` lost is a violation too (the dump changed shape).

Subcommands::

    dump    --src <checkout>/03_src --out <dump.json>
            (any interpreter that imports the checkout's ``outrigger_sim``: numpy needed)
    compare --base <dump.json> --head <dump.json> --out <diff.json>
    run     --repo <checkout> [--base-rev e67dae8] [--python <interpreter>] --out <diff.json>
            (``git archive`` of the base 03_src into a temporary folder, both dumps in child
            processes of ``--python``, then compare; the dumps are kept next to ``--out``)

Values are compared after a JSON normalisation: floats by ``repr`` (bit for bit), enums by
``Class.NAME``, tuples as lists, numpy arrays as lists, ``None`` as null.
Exit: 0 I-17 satisfied, 1 a violation, 2 input error, 3 internal error. The last stdout line is a
one-line JSON summary.
"""

from __future__ import annotations

import argparse
import dataclasses
import enum
import hashlib
import json
import math
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

RULES_FILE = "b1_creep_rules.md"
RULES_SHA256 = "6b99702ce26d6da28fbfe6473b622c7e51419241916cbc101f795828f498774e"
"""Sealed rules (``b1_creep_rules.sha256``, master ``1ad3e5d``, 2026-11-12)."""
BASE_REV = "e67dae8"
SCHEMA_DUMP = "b1-preset-dump/1"
SCHEMA_DIFF = "b1-preset-dump-diff/1"
PRESET_EXPRESSION = "C2Config().with_10hz_d1()"
DEFAULT_EXPRESSION = "C2Config()"
EXIT_OK, EXIT_FOUND, EXIT_INPUT, EXIT_INTERNAL = 0, 1, 2, 3
CHILD_TIMEOUT_S = 600


# ----------------------------------------------------------------------------- dump
def normalise(value):
    """JSON form of a config value (exact floats by repr, enums by class and name)."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {field.name: normalise(getattr(value, field.name))
                for field in dataclasses.fields(value)}
    if isinstance(value, enum.Enum):
        return f"{type(value).__name__}.{value.name}"
    if isinstance(value, bool) or value is None or isinstance(value, str | int):
        return value
    if isinstance(value, float):
        return {"float": repr(value)} if not math.isfinite(value) else float(value)
    if isinstance(value, dict):
        return {str(key): normalise(item) for key, item in sorted(value.items(), key=str)}
    if isinstance(value, list | tuple | frozenset | set):
        items = sorted(value, key=repr) if isinstance(value, frozenset | set) else value
        return [normalise(item) for item in items]
    if hasattr(value, "tolist"):  # numpy array or scalar
        return normalise(value.tolist())
    return {"repr": repr(value)}


def flatten(tree, prefix: str = "") -> dict[str, object]:
    """Dotted path -> leaf value (dataclass fields are dict keys after :func:`normalise`)."""
    is_leaf_marker = set(tree) <= {"float", "repr"} and len(tree) == 1 if isinstance(
        tree, dict) else False
    if isinstance(tree, dict) and tree and not is_leaf_marker:
        out: dict[str, object] = {}
        for key, item in tree.items():
            out.update(flatten(item, f"{prefix}.{key}" if prefix else key))
        return out
    return {prefix: tree}


def dump(src: Path) -> dict:
    """Preset and class-default dumps of the ``outrigger_sim`` under ``src``."""
    sys.path.insert(0, str(src))
    from outrigger_sim.control import c2

    module_file = Path(c2.__file__).resolve()
    if not module_file.is_relative_to(src.resolve()):
        raise RuntimeError(f"imported {module_file}, not the c2 of {src}")
    preset = normalise(c2.C2Config().with_10hz_d1())
    default = normalise(c2.C2Config())
    return {"schema": SCHEMA_DUMP, "src": str(src), "c2_file": str(module_file),
            "c2_sha256": hashlib.sha256(module_file.read_bytes()).hexdigest(),
            "preset_expression": PRESET_EXPRESSION, "default_expression": DEFAULT_EXPRESSION,
            "preset": flatten(preset), "default": flatten(default)}


# ----------------------------------------------------------------------------- compare
def _same(a, b) -> bool:
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def compare(base: dict, head: dict) -> dict:
    """I-17 of two dumps (module docstring)."""
    base_preset, head_preset, head_default = base["preset"], head["preset"], head["default"]
    common = sorted(set(base_preset) & set(head_preset))
    new = sorted(set(head_preset) - set(base_preset))
    removed = sorted(set(base_preset) - set(head_preset))
    common_diff = [{"field": name, "base": base_preset[name], "head": head_preset[name]}
                   for name in common if not _same(base_preset[name], head_preset[name])]
    new_not_default = []
    for name in new:
        if name not in head_default:
            new_not_default.append({"field": name, "head": head_preset[name],
                                    "class_default": "<absent>"})
        elif not _same(head_preset[name], head_default[name]):
            new_not_default.append({"field": name, "head": head_preset[name],
                                    "class_default": head_default[name]})
    violations = len(common_diff) + len(new_not_default) + len(removed)
    return {"schema": SCHEMA_DIFF, "rules_file": RULES_FILE, "rules_sha256": RULES_SHA256,
            "rule": "I-17: common fields equal; new fields = HEAD_M class default; none removed",
            "base_c2_sha256": base.get("c2_sha256"), "head_c2_sha256": head.get("c2_sha256"),
            "counts": {"common": len(common), "new": len(new), "removed": len(removed)},
            "new_fields": new, "removed_fields": removed, "common_diff": common_diff,
            "new_not_default": new_not_default, "violations": violations,
            "i17_ok": violations == 0}


# ----------------------------------------------------------------------------- run
def _git(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True,
                          timeout=CHILD_TIMEOUT_S).stdout


def _extract_src(repo: Path, rev: str, target: Path) -> Path:
    """``git archive <rev> 03_src`` into ``target``; the 03_src folder."""
    archive = target / "base_src.tar"
    archive.write_bytes(_git(repo, "archive", "--format=tar", rev, "03_src"))
    with tarfile.open(archive) as tar:
        tar.extractall(target, filter="data")
    return target / "03_src"


def _child_dump(python: str, src: Path, out: Path) -> dict:
    subprocess.run([python, "-I", "-B", str(Path(__file__).resolve()), "dump", "--src", str(src),
                    "--out", str(out)], check=True, capture_output=True, timeout=CHILD_TIMEOUT_S)
    return json.loads(out.read_text(encoding="utf-8"))


def run(repo: Path, base_rev: str, python: str, out: Path) -> dict:
    head_commit = _git(repo, "rev-parse", "HEAD").decode().strip()
    base_commit = _git(repo, "rev-parse", base_rev).decode().strip()
    dump_dir = out.parent
    with tempfile.TemporaryDirectory(prefix="b1_i17_") as folder:
        base_src = _extract_src(repo, base_rev, Path(folder))
        base = _child_dump(python, base_src, dump_dir / f"{out.stem}_base_dump.json")
    head = _child_dump(python, repo / "03_src", dump_dir / f"{out.stem}_head_dump.json")
    result = compare(base, head)
    result.update(head_commit=head_commit, base_rev=base_rev, base_commit=base_commit,
                  python=python)
    return result


# ----------------------------------------------------------------------------- CLI
def _write(path: Path, data: dict) -> str:
    text = json.dumps(data, indent=1, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p_dump = sub.add_parser("dump")
    p_dump.add_argument("--src", type=Path, required=True)
    p_dump.add_argument("--out", type=Path, required=True)
    p_cmp = sub.add_parser("compare")
    p_cmp.add_argument("--base", type=Path, required=True)
    p_cmp.add_argument("--head", type=Path, required=True)
    p_cmp.add_argument("--out", type=Path, required=True)
    p_run = sub.add_parser("run")
    p_run.add_argument("--repo", type=Path, required=True)
    p_run.add_argument("--base-rev", default=BASE_REV)
    p_run.add_argument("--python", default=sys.executable)
    p_run.add_argument("--out", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.command == "dump":
            data = dump(args.src)
        elif args.command == "compare":
            data = compare(json.loads(args.base.read_text(encoding="utf-8")),
                           json.loads(args.head.read_text(encoding="utf-8")))
        else:
            data = run(args.repo, args.base_rev, args.python, args.out)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"status": "input_error", "error": str(exc)[:500]}))
        return EXIT_INPUT
    except Exception as exc:  # noqa: BLE001  (reported with the exit code of the CLI contract)
        print(json.dumps({"status": "internal_error", "error": repr(exc)[:500]}))
        return EXIT_INTERNAL
    out_sha = _write(args.out, data)
    is_found = args.command != "dump" and not data["i17_ok"]
    summary = {"status": "ok", "command": args.command, "out": str(args.out),
               "out_sha256": out_sha, "tool_sha256": hashlib.sha256(
                   Path(__file__).read_bytes()).hexdigest()}
    if args.command != "dump":
        summary.update(i17_ok=data["i17_ok"], violations=data["violations"])
    print(json.dumps(summary))
    return EXIT_FOUND if is_found else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
