"""436.9 addendum 4a-6 G-4: do the steps (1) .. (4a) of a new run commit reproduce the
earlier attempt (``j9_runs/b51ed6e1/``)? Only these values are read, compared in memory and
never written:

=======  ==============================================================================
item     values compared (old attempt against new attempt)
=======  ==============================================================================
p1       sha256 of ``h6_base_judge.json`` and ``h6_base_judge_L1_reference.json``; the
         exit codes ``tool:base_judge_compare`` and ``tool:t12_selfcheck``
dry      the two evidence keys (``rod_reading_truth_calls``, ``two_pressure_reads``) of
         every record of the five dry runs; the exit code ``tool:summarize``
fpath    ``harness_commands_sha256`` of the three F-A path rows (by ``offset_s``); the exit
         code ``tool:case_f_path``
x11      ``commands_sha256`` of the ``LSJ4_X11`` row, the class and ``p_tr - ④`` gap of its
         FL 49.0 s read (``jp3_case_judge._x11_read``); the exit code ``tool:x11``
=======  ==============================================================================

A step's folder is the ``folder`` of ``<root>/<step>.done`` (else of the newest
``<step>.stop*``), taken by name under ``<root>``; its exit codes are those of its
``step_record.json``. Inside a running step (before its record exists) the new side is given
by ``--new-folder`` and ``--new-codes`` (a JSON file of the step's codes so far).

The report names each compared value and whether it is the same; no value is written. The
stdout's last line is JSON with ``status`` and counts.

Exit codes: 0 all the same, 1 a value differs, 2 an input missing (a folder, file, key or
code), 3 a tool error.

Usage (dynamics-dev, worktree root; the main session runs it before the judgement):
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_rerun_match.py --old <j9_runs>/b51ed6e1
      --new <j9_runs>/<new commit 8> --items p1,dry,fpath,x11 --out <report.json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

ITEM_STEPS = {"p1": "p1", "dry": "dry", "fpath": "fpath", "x11": "cases"}
"""Item -> the run step whose folder holds it."""
P1_FILES = ("h6_base_judge.json", "h6_base_judge_L1_reference.json")
P1_CODES = ("tool:base_judge_compare", "tool:t12_selfcheck")
DRY_EVENT_FILES = ("event_VBJ.jsonl", "event_VBH.jsonl", "event_VBJ0.jsonl")
DRY_R79_FILES = ("r79_VBJ.json", "r79_VBH.json")
EVIDENCE_KEYS = ("rod_reading_truth_calls", "two_pressure_reads")
FPATH_ROWS = "j9_case_f_path.jsonl"
X11_ROWS = "lsj4_x11.jsonl"
X11_SETTING = "LSJ4_X11"
ITEM_CODES = {"p1": P1_CODES, "dry": ("tool:summarize",), "fpath": ("tool:case_f_path",),
              "x11": ("tool:x11",)}
EXIT_SAME, EXIT_DIFFERS, EXIT_MISSING, EXIT_ERROR = 0, 1, 2, 3


class Missing(Exception):
    """An input of an item is missing (exit 2)."""


@dataclass
class Side:
    """One attempt: its runs root and, for a running step, its folder and codes."""

    root: Path
    folder: Path | None = None
    codes: dict | None = None
    cache: dict = field(default_factory=dict)

    def step_folder(self, step: str) -> Path:
        if self.folder is not None:
            return self.folder
        return _marked_folder(self.root, step)

    def step_codes(self, step: str) -> dict:
        if self.codes is not None:
            return self.codes
        record = self.step_folder(step) / "step_record.json"
        if not record.is_file():
            raise Missing(f"{record} missing")
        return json.loads(record.read_text(encoding="utf-8")).get("codes") or {}


def _marked_folder(root: Path, step: str) -> Path:
    """The folder of ``<step>.done``, else of the newest ``<step>.stop*`` (by name under root)."""
    markers = [root / f"{step}.done"]
    markers += sorted(root.glob(f"{step}.stop*"), key=lambda path: path.stat().st_mtime,
                      reverse=True)
    for marker in markers:
        if marker.is_file():
            folder = json.loads(marker.read_text(encoding="utf-8")).get("folder")
            if folder:
                return root / Path(folder).name
    raise Missing(f"no {step}.done / {step}.stop under {root}")


def _sha256(path: Path) -> str:
    if not path.is_file():
        raise Missing(f"{path} missing")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_lines(path: Path) -> list[dict]:
    if not path.is_file():
        raise Missing(f"{path} missing")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _evidence(records: list[dict]) -> list:
    return [[(record.get("hydraulics_record") or {}).get(key) for key in EVIDENCE_KEYS]
            for record in records]


def _codes(side: Side, item: str) -> dict:
    codes = side.step_codes(ITEM_STEPS[item])
    missing = [name for name in ITEM_CODES[item] if name not in codes]
    if missing:
        raise Missing(f"{item}: codes {missing} missing")
    return {f"code {name}": codes[name] for name in ITEM_CODES[item]}


def item_values(side: Side, item: str) -> dict:
    """The named values of one item on one side (module docstring)."""
    folder = side.step_folder(ITEM_STEPS[item])
    values = {}
    if item == "p1":
        values.update({f"sha256 {name}": _sha256(folder / name) for name in P1_FILES})
    elif item == "dry":
        for name in DRY_EVENT_FILES:
            values[f"evidence {name}"] = _evidence(_read_lines(folder / name))
        for name in DRY_R79_FILES:
            path = folder / name
            if not path.is_file():
                raise Missing(f"{path} missing")
            values[f"evidence {name}"] = _evidence(
                json.loads(path.read_text(encoding="utf-8")).get("results") or [])
    elif item == "fpath":
        for row in _read_lines(folder / FPATH_ROWS):
            offset = (row.get("job") or {}).get("offset_s")
            values[f"harness_commands_sha256 offset {offset}"] = row.get(
                "harness_commands_sha256")
    elif item == "x11":
        values.update(_x11_values(folder))
    values.update(_codes(side, item))
    return values


def _x11_values(folder: Path) -> dict:
    import jp3_baseline_compare as compare
    import jp3_case_judge as case_judge

    rows = [row for row in _read_lines(folder / X11_ROWS)
            if (row.get("job") or {}).get("setting") == X11_SETTING]
    if len(rows) != 1 or not rows[0].get("t4h_file"):
        raise Missing(f"{folder / X11_ROWS}: {len(rows)} {X11_SETTING} rows")
    npz = folder / f"{Path(X11_ROWS).stem}_t4h" / Path(rows[0]["t4h_file"]).name
    problems = compare.Problems()
    read = case_judge._x11_read(npz, problems)
    if read is None:
        raise Missing(f"{npz}: no FL 49.0 s read ({problems.not_judgeable})")
    return {"commands_sha256 LSJ4_X11": rows[0].get("commands_sha256"),
            "FL 49.0 s class": read["class"], "FL 49.0 s gap_bar": read["gap_bar"]}


def compare_items(old: Side, new: Side, items: list[str]) -> tuple[dict, int]:
    """Per item the names of the same and the differing values (no value in the report)."""
    report, code = {"items": {}}, EXIT_SAME
    for item in items:
        try:
            before, after = item_values(old, item), item_values(new, item)
        except Missing as exc:
            report["items"][item] = {"status": "missing", "reason": str(exc)}
            code = max(code, EXIT_MISSING)
            continue
        names = sorted(set(before) | set(after))
        differing = [name for name in names if before.get(name) != after.get(name)]
        report["items"][item] = {"status": "differs" if differing else "same",
                                 "compared": names, "differing": differing}
        if differing and code == EXIT_SAME:
            code = EXIT_DIFFERS
    return report, code


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog="exit codes: 0 same, 1 differs, 2 input missing, "
                                            "3 tool error")
    parser.add_argument("--old", type=Path, required=True, help="runs root of the earlier try")
    parser.add_argument("--new", type=Path, required=True, help="runs root of the new commit")
    parser.add_argument("--items", default=",".join(ITEM_STEPS),
                        help=f"comma list of {sorted(ITEM_STEPS)}")
    parser.add_argument("--new-folder", type=Path, default=None,
                        help="the running step's folder (one item only)")
    parser.add_argument("--new-codes", type=Path, default=None,
                        help="JSON file of the running step's codes (with --new-folder)")
    parser.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    items = [item for item in args.items.split(",") if item]
    unknown = sorted(set(items) - set(ITEM_STEPS))
    if unknown or not items:
        parser.error(f"--items takes {sorted(ITEM_STEPS)}, got {args.items!r}")
    if (args.new_folder is None) != (args.new_codes is None) or (
            args.new_folder is not None and len(items) != 1):
        parser.error("--new-folder and --new-codes go together, with one item")
    if args.out.exists():
        parser.error(f"{args.out} exists (a new report never overwrites one)")
    try:
        codes = None if args.new_codes is None else json.loads(
            args.new_codes.read_text(encoding="utf-8"))
        report, code = compare_items(Side(args.old), Side(args.new, args.new_folder, codes),
                                     items)
    except Exception as exc:  # noqa: BLE001 (any error is a tool error, exit 3)
        report, code = {"error": f"{type(exc).__name__}: {exc}"}, EXIT_ERROR
    status = {EXIT_SAME: "same", EXIT_DIFFERS: "differs", EXIT_MISSING: "missing",
              EXIT_ERROR: "error"}[code]
    report.update(status=status, old=str(args.old), new=str(args.new), items_asked=items)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({"status": status, "out": str(args.out),
                      "differing_items": sum(entry.get("status") == "differs"
                                             for entry in report.get("items", {}).values())}))
    return code


if __name__ == "__main__":
    sys.exit(main())
