"""436.9 addendum 4a-3 K-9: the record-test values of the 1.2 disclosure sentence, as a table for
the judgement document, checked against the record files of the remedy's unit tests
(``j4a_remedy_3b949f5/records_full``: written by ``test_jp3_rev5_property.py`` with
``JP3_RECORD_DIR``).

Every number the 1.2 sentence (and the 1.1 table) prints is in :data:`SENTENCE_VALUES` with the
precision it is printed at; a file value matches when it rounds to the printed value (a
difference of at most half the last printed digit). The folder's ``SHA256SUMS`` (when present)
is checked for the files read.

Exit codes: 0 every value matches, 1 a value differs, 2 a record file or key missing, a SUMS
mismatch or an existing ``--out``, 3 error. The stdout's last line is JSON with ``status``, the
counts and the output path only.

Usage (python-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_record_table.py <evidence folder>
      --out <table.json> [--markdown <table.md>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

RECORDS = "records_full"
P4_7_FILE = "P4-7.json"
OPENING_ROWS = (("P4-6_F14.8kN_1mms_0.1s.json", "1 mm/s, 0.1 s"),
                ("P4-6_F14.8kN_1mms_0.2s.json", "1 mm/s, 0.2 s"))
SLOW_ROWS = ("P4-6_F14.8kN_0.3mms_0.1s.json", "P4-6_F14.8kN_0.3mms_0.2s.json",
             "P4-6_F14.8kN_0.3mms_0.5s.json", "P4-6_F5kN_0.3mms_0.2s.json")
EXIT_PASS, EXIT_FAILED, EXIT_NOT_JUDGEABLE, EXIT_ERROR = 0, 1, 2, 3


@dataclass(frozen=True)
class SentenceValue:
    """One printed number of 4a-3 1.1 / 1.2 and where the record holds it."""

    label: str
    printed: float
    decimals: int
    file: str
    path: tuple[str, ...]


def _opening(file: str, row: str) -> list[SentenceValue]:
    values = {"1 mm/s, 0.1 s": (48.50, -6.85, 43.46, -23.71, 5.05),
              "1 mm/s, 0.2 s": (44.33, -6.62, 47.63, -20.008, 9.45)}[row]
    start, difference, gap, model_only, lower = values
    return [SentenceValue(f"P4-6 {row} HOLD start p_tr [bar]", start, 2, file,
                          ("hold_start_p_tr_bar",)),
            SentenceValue(f"P4-6 {row} p_tr - table [bar]", difference, 2, file,
                          ("hold_start_p_tr_bar", "-", "table_row", "start_bar")),
            SentenceValue(f"P4-6 {row} R5-7 gap [bar]", gap, 2, file, ("r5_7_gap_bar",)),
            SentenceValue(f"P4-6 {row} model_only gap [bar]", model_only,
                          3 if row.endswith("0.2 s") else 2, file, ("model_only_gap_bar",)),
            SentenceValue(f"P4-6 {row} lower gap of the table [bar]", lower, 2, file,
                          ("table_row", "lower_gap_bar"))]


SENTENCE_VALUES: tuple[SentenceValue, ...] = (
    *(value for file, row in OPENING_ROWS for value in _opening(file, row)),
    *(SentenceValue(f"P4-6 0.3 mm/s {file[5:-5]} min used - p_tr [bar]", 11.0, 1, file,
                    ("min_used_minus_p_tr_bar",)) for file in SLOW_ROWS),
    *(SentenceValue(f"P4-7 N {n} band {band} q1 excess [bar]", excess, 3, P4_7_FILE,
                    ("values", f"N{n}_band{band}kN", "model_only_first_excess_bar"))
      for n, excess in ((14, 27.204), (12, 29.194)) for band in ("0", "4")),
    *(SentenceValue(f"P4-7 N {n} band {band} p_tr - ④ [bar]", value, 3, P4_7_FILE,
                    ("values", f"N{n}_band{band}kN", "model_only_first_p_tr_minus_bound_bar"))
      for n, value in ((14, 28.468), (12, 30.444)) for band in ("0", "4")),
    *(SentenceValue(f"P4-7 N {n} band {band} R5-7 margin [bar]", value, decimals, P4_7_FILE,
                    ("values", f"N{n}_band{band}kN", "r5_7_min_margin_bar"))
      for n, value, decimals in ((14, 50.817, 3), (12, 48.620, 3)) for band in ("0", "4")),
    *(SentenceValue(f"P4-7 monitor shortest N, band {band}", 12, 0, P4_7_FILE,
                    ("monitor_shortest_N", f"band{band}kN")) for band in ("0", "4")),
)
"""The numbers of 4a-3 1.1 (table) and 1.2 (sentence) with their printed decimals."""
FLAG_CHECKS = (
    *((file, ("first_read_source",), "retract_tracker") for file, _ in OPENING_ROWS),
    *((file, ("gate_opened",), True) for file, _ in OPENING_ROWS),
    *((file, ("gate_opened",), False) for file in SLOW_ROWS),
)
"""1.2: the first read's source of the 1 mm/s rows, the gate opening of all six rows."""


class MissingRecord(Exception):
    """A record file or key the sentence needs is missing (exit 2)."""


def _lookup(data: dict, path: tuple[str, ...]):
    value = data
    for key in path:
        if not isinstance(value, dict) or key not in value:
            raise MissingRecord(f"key {'.'.join(path)} missing")
        value = value[key]
    return value


def record_value(records: dict[str, dict], item: SentenceValue) -> float:
    """The record value of one printed number (``a - b`` for a path with ``"-"``)."""
    data = records[item.file]
    if "-" in item.path:
        split = item.path.index("-")
        return float(_lookup(data, item.path[:split])) - float(_lookup(data, item.path[split + 1:]))
    return float(_lookup(data, item.path))


def matches(item: SentenceValue, value: float) -> bool:
    """The record value rounds to the printed number (half the last printed digit)."""
    return abs(value - item.printed) <= 0.5 * 10.0 ** (-item.decimals) + 1e-12


def _check_sums(folder: Path, names: list[str]) -> list[str]:
    sums = folder / "SHA256SUMS"
    if not sums.is_file():
        return []
    listed = {}
    for line in sums.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            listed[name.lstrip("*").removeprefix("./")] = digest
    problems = []
    for name in names:
        relative = f"{RECORDS}/{name}"
        digest = hashlib.sha256((folder / relative).read_bytes()).hexdigest()
        if listed.get(relative) != digest:
            problems.append(f"{relative}: not the SHA256SUMS hash")
    return problems


def build_table(folder: Path) -> tuple[dict, int]:
    names = sorted({item.file for item in SENTENCE_VALUES})
    missing = [name for name in names if not (folder / RECORDS / name).is_file()]
    if missing:
        raise MissingRecord(f"record files missing: {missing}")
    sums_problems = _check_sums(folder, names)
    if sums_problems:
        raise MissingRecord("; ".join(sums_problems))
    records = {name: json.loads((folder / RECORDS / name).read_text(encoding="utf-8"))
               for name in names}
    rows = []
    for item in SENTENCE_VALUES:
        value = record_value(records, item)
        rows.append({"label": item.label, "printed": item.printed, "record": value,
                     "matches": matches(item, value),
                     "source": f"{RECORDS}/{item.file}:{'.'.join(item.path)}"})
    flags = [{"source": f"{RECORDS}/{file}:{'.'.join(path)}", "expected": expected,
              "record": _lookup(records[file], path),
              "matches": _lookup(records[file], path) == expected}
             for file, path, expected in FLAG_CHECKS]
    mismatches = sum(not row["matches"] for row in [*rows, *flags])
    return ({"rows": rows, "flags": flags, "mismatches": mismatches},
            EXIT_FAILED if mismatches else EXIT_PASS)


def markdown(table: dict) -> str:
    lines = ["| 항목 | 문장 값 | 기록 값 | 일치 | 출처 |", "|---|---|---|---|---|"]
    lines += [f"| {row['label']} | {row['printed']} | {row['record']:.6g} | "
              f"{'예' if row['matches'] else '아니오'} | `{row['source']}` |"
              for row in table["rows"]]
    lines += [f"| {row['source'].split(':')[-1]} | {row['expected']} | {row['record']} | "
              f"{'예' if row['matches'] else '아니오'} | `{row['source']}` |"
              for row in table["flags"]]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, default=None)
    args = parser.parse_args(argv)
    for path in (args.out, args.markdown):
        if path is not None and path.exists():
            parser.error(f"{path} exists (a new table never overwrites one)")
    try:
        table, code = build_table(args.folder)
    except MissingRecord as exc:
        table, code = {"not_judgeable": str(exc)}, EXIT_NOT_JUDGEABLE
    except (OSError, ValueError) as exc:
        table, code = {"error": f"{type(exc).__name__}: {exc}"}, EXIT_ERROR
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(table, indent=1, ensure_ascii=False), encoding="utf-8")
    if args.markdown is not None and "rows" in table:
        args.markdown.write_text(markdown(table), encoding="utf-8")
    status = {EXIT_PASS: "pass", EXIT_FAILED: "failed", EXIT_NOT_JUDGEABLE: "not_judgeable",
              EXIT_ERROR: "error"}[code]
    print(json.dumps({"status": status, "mismatches": table.get("mismatches"),
                      "out": str(args.out)}))
    return code


if __name__ == "__main__":
    sys.exit(main())
