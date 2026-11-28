"""Regression check: the event-band CSVs summed over event_band equal the earlier CSVs.

Prints only counts of matching / differing rows (no values).
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

COUNT_COLUMNS = ("candidates", "c0_flagged", "cm_flagged", "d1p_flagged")


def read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def summed(rows: list[dict], key_columns: tuple[str, ...]) -> dict:
    totals: dict = defaultdict(lambda: dict.fromkeys(COUNT_COLUMNS, 0))
    for row in rows:
        key = tuple(row[name] for name in key_columns)
        for name in COUNT_COLUMNS:
            totals[key][name] += int(row[name])
    return dict(totals)


def compare(old_path: Path, new_path: Path, key_columns: tuple[str, ...]) -> tuple[int, int]:
    old = summed(read(old_path), key_columns)
    new = summed(read(new_path), key_columns)
    same = sum(old.get(key) == value for key, value in new.items())
    return same, len(old) + len(new) - 2 * same


def main() -> None:
    folder = Path(sys.argv[1])
    keys = ("population", "injected_jump_bar", "period_class", "band")
    print("bands", compare(folder / "ml_inject_cm_bands.csv",
                           folder / "ml_inject_cm_bands_ev.csv", keys))
    print("runs", compare(folder / "ml_inject_cm_runs.csv",
                          folder / "ml_inject_cm_runs_ev.csv", ("run", *keys)))
    roles = {(row["population"], row["band"], row["row_role"])
             for row in read(folder / "ml_inject_cm_bands_ev.csv")}
    print("roles", sorted(roles))
    events = {(row["population"], row["event_band"])
              for row in read(folder / "ml_inject_cm_bands_ev.csv")}
    print("event bands", sorted(events))


if __name__ == "__main__":
    main()
