"""Final-controller acceptance B (control spec 429.11): B1 = B2 command hashes per id.

B1 ran the wrapper token ``P36sa+R4c30`` before the R8 preset switch, B2 ran the implementation
(candidate ``current``) after it. The acceptance criterion is that every id has the same command
hash in both runs (1,220 wrapper records + H9 36 + study A 80 + r67 384 = 1,720).

Two record layouts are read:
  wrapper  ``s9_slope_fix_candidates.py`` output: ``records[]`` with ``id``, ``hash``, ``verdict``
  event    ``s9_soil_event_screen.py`` (study A) and ``r67_g1_screen.py`` output: ``results[]``
           with ``key`` and ``runs[]``; each run has ``commands_sha256`` and ``pass``. A run id is
           ``<key>#<index>:<event descriptor>``. The shared prefix before the branch is compared
           per result as well (``prefix_commands_sha256``, or ``base.commands_sha256`` when the
           layout stores the prefix there, as study A does).

Usage (python-dev or dynamics-dev):
  python -I final_b1b2_identity.py [--dir <rev85 folder>] [--out <json>]
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DIR = ROOT / "06_analysis" / "02_control" / "s9" / "rev85"
DEFAULT_OUT_NAME = "final_b1b2_identity.json"
B1_TAG = "finB1"
B2_TAG = "finB2"
TOTAL_EXPECTED = 1720
RUN_DESCRIPTOR_KEYS = ("event", "timing", "sample", "offset_s", "phase_at_event")
HASH_PREVIEW_CHARS = 16


@dataclass(frozen=True)
class Bundle:
    """One B1/B2 file pair: name, record layout and the expected number of compared ids."""

    name: str
    layout: str  # "wrapper" or "event"
    expected_count: int

    def path(self, folder: Path, tag: str) -> Path:
        return folder / f"{tag}_{self.name}.json"


@dataclass(frozen=True)
class Entry:
    """Hash and verdict of one compared id."""

    hash: str | None
    verdict: str | None


BUNDLES = (
    Bundle("harness", "wrapper", 209),
    Bundle("x426b", "wrapper", 84),
    Bundle("p0", "wrapper", 927),
    Bundle("A", "event", 80),
    Bundle("r67_main", "event", 192),
    Bundle("r67_top", "event", 192),
    Bundle("h9", "wrapper", 36),
)


def _put_unique(entries: dict[str, Entry], entry_id: str, entry: Entry) -> None:
    if entry_id in entries:
        raise ValueError(f"duplicate id {entry_id!r}")
    entries[entry_id] = entry


def load_wrapper_entries(payload: dict) -> dict[str, Entry]:
    """Entries of a wrapper result keyed by record id."""
    entries: dict[str, Entry] = {}
    for record in payload["records"]:
        _put_unique(entries, record["id"], Entry(record.get("hash"), record.get("verdict")))
    return entries


def run_id(key: str, index: int, run: dict) -> str:
    """Readable, unique id of one event run: result key, run index and event descriptor."""
    descriptor = "|".join(str(run[name]) for name in RUN_DESCRIPTOR_KEYS if name in run)
    return f"{key}#{index}:{descriptor}"


def _run_verdict(run: dict) -> str | None:
    if "pass" not in run:
        return None
    return "pass" if run["pass"] else "fail"


def prefix_hash(result: dict) -> tuple[str | None, str]:
    """Prefix command hash of an event result and the field it came from."""
    if "prefix_commands_sha256" in result:
        return result["prefix_commands_sha256"], "prefix_commands_sha256"
    base = result.get("base") or {}
    if "commands_sha256" in base:
        return base["commands_sha256"], "base.commands_sha256"
    return None, "missing"


def load_event_entries(payload: dict) -> tuple[dict[str, Entry], dict[str, Entry], set[str]]:
    """Run entries, prefix entries (per result key) and the prefix source fields of a result."""
    runs: dict[str, Entry] = {}
    prefixes: dict[str, Entry] = {}
    prefix_sources: set[str] = set()
    for result in payload["results"]:
        key = result["key"]
        prefix, source = prefix_hash(result)
        prefix_sources.add(source)
        _put_unique(prefixes, key, Entry(prefix, None))
        for index, run in enumerate(result["runs"]):
            entry = Entry(run.get("commands_sha256"), _run_verdict(run))
            _put_unique(runs, run_id(key, index, run), entry)
    return runs, prefixes, prefix_sources


def _short(value: str | None) -> str | None:
    return value[:HASH_PREVIEW_CHARS] if value else value


def compare_entries(b1: dict[str, Entry], b2: dict[str, Entry]) -> dict:
    """Per-id hash and verdict comparison of two entry maps.

    A missing hash on either side counts as different, never as equal.
    """
    matched_ids = sorted(b1.keys() & b2.keys())
    hash_different = []
    verdict_different = []
    for entry_id in matched_ids:
        before, after = b1[entry_id], b2[entry_id]
        is_hash_equal = before.hash is not None and before.hash == after.hash
        if not is_hash_equal:
            hash_different.append(
                {
                    "id": entry_id,
                    "hash_b1": _short(before.hash),
                    "hash_b2": _short(after.hash),
                    "verdict_b1": before.verdict,
                    "verdict_b2": after.verdict,
                }
            )
        if before.verdict != after.verdict:
            verdict_different.append(
                {
                    "id": entry_id,
                    "verdict_b1": before.verdict,
                    "verdict_b2": after.verdict,
                    "hash_equal": is_hash_equal,
                }
            )
    only_b1 = sorted(b1.keys() - b2.keys())
    only_b2 = sorted(b2.keys() - b1.keys())
    return {
        "n_b1": len(b1),
        "n_b2": len(b2),
        "matched": len(matched_ids),
        "hash_equal": len(matched_ids) - len(hash_different),
        "hash_different": len(hash_different),
        "verdict_equal": len(matched_ids) - len(verdict_different),
        "verdict_different": len(verdict_different),
        "unmatched": len(only_b1) + len(only_b2),
        "only_b1": only_b1,
        "only_b2": only_b2,
        "hash_different_ids": hash_different,
        "verdict_different_ids": verdict_different,
    }


def _is_clean(comparison: dict) -> bool:
    return comparison["hash_different"] == 0 and comparison["unmatched"] == 0


def compare_bundle(bundle: Bundle, folder: Path) -> dict:
    """Comparison block of one bundle (runs or records, plus prefixes for event layouts)."""
    payloads = [
        json.loads(bundle.path(folder, tag).read_text(encoding="utf-8")) for tag in (B1_TAG, B2_TAG)
    ]
    block: dict = {
        "b1_file": bundle.path(folder, B1_TAG).name,
        "b2_file": bundle.path(folder, B2_TAG).name,
        "layout": bundle.layout,
        "expected_count": bundle.expected_count,
    }
    if bundle.layout == "wrapper":
        before, after = (load_wrapper_entries(payload) for payload in payloads)
        block.update(compare_entries(before, after))
    else:
        (runs_b1, prefix_b1, sources_b1), (runs_b2, prefix_b2, sources_b2) = (
            load_event_entries(payload) for payload in payloads
        )
        block.update(compare_entries(runs_b1, runs_b2))
        block["prefix"] = compare_entries(prefix_b1, prefix_b2)
        block["prefix"]["source_fields"] = sorted(sources_b1 | sources_b2)
    block["count_ok"] = block["n_b1"] == block["n_b2"] == bundle.expected_count
    is_prefix_clean = "prefix" not in block or _is_clean(block["prefix"])
    block["all_equal"] = _is_clean(block) and block["count_ok"] and is_prefix_clean
    return block


def build_report(
    folder: Path, bundles: tuple[Bundle, ...] = BUNDLES, total_expected: int = TOTAL_EXPECTED
) -> dict:
    """Full B1/B2 identity report over all bundles."""
    blocks = {bundle.name: compare_bundle(bundle, folder) for bundle in bundles}
    totals = {
        name: sum(block[name] for block in blocks.values())
        for name in (
            "matched",
            "hash_equal",
            "hash_different",
            "unmatched",
            "verdict_equal",
            "verdict_different",
        )
    }
    totals["expected"] = total_expected
    totals["all_equal"] = (
        all(block["all_equal"] for block in blocks.values())
        and totals["hash_equal"] == total_expected
    )
    meta = {
        "script": "04_scripts/03_control/s9/final_b1b2_identity.py",
        "spec": "429.11 acceptance B (finB1 = finB2 command hash per id)",
        "folder": str(folder),
        "b1": f"{B1_TAG} (wrapper P36sa+R4c30, before preset switch)",
        "b2": f"{B2_TAG} (implementation current, after preset switch)",
        "run_id_rule": "<result key>#<run index>:" + "|".join(RUN_DESCRIPTOR_KEYS),
    }
    return {"meta": meta, "totals": totals, "bundles": blocks}


def _verdict_line(totals: dict) -> str:
    if totals["all_equal"]:
        return f"B1=B2 {totals['hash_equal']:,}/{totals['expected']:,} equal"
    mismatches = totals["hash_different"] + totals["unmatched"]
    return (
        f"MISMATCH {mismatches} (hash different {totals['hash_different']}, "
        f"unmatched {totals['unmatched']})"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR, help="folder of finB1/finB2")
    parser.add_argument("--out", type=Path, default=None, help="output JSON path")
    args = parser.parse_args()
    out = args.out or args.dir / DEFAULT_OUT_NAME
    report = build_report(args.dir)
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    for name, block in report["bundles"].items():
        prefix = block.get("prefix")
        prefix_text = (
            f" prefix {prefix['hash_equal']}/{prefix['matched']} unmatched {prefix['unmatched']}"
            if prefix
            else ""
        )
        print(
            f"{name:9s} n {block['n_b1']}/{block['n_b2']} (expected {block['expected_count']})"
            f" hash equal {block['hash_equal']} different {block['hash_different']}"
            f" unmatched {block['unmatched']} verdict different {block['verdict_different']}"
            f"{prefix_text}"
        )
    print(_verdict_line(report["totals"]), "->", out)


if __name__ == "__main__":
    main()
