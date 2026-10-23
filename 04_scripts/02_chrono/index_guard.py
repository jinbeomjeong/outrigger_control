"""Revision guard for the stage summaries (S3, S4, S4_energy, S5).

``07_results/<stage>/index.json`` keeps the latest *successful* directory per case. When a case fails in a new batch,
its index entry still points to an older batch, possibly run with another ``02_params/rexome33.yaml``. A summary
that read it would mix revisions. This module keeps only the cases whose ``case.json`` ``run_meta.params_file_sha256``
equals the sha256 of the current YAML file. The others are returned as *held* ("없음 / 판정 보류") and the summary
writes a warning in its meta. Cases whose ``reference_sha256`` (reference.json) differs from the current file are
kept but listed as a warning (the judged references may have changed).

Rule (coordinator 2026-10-22): never substitute a result of another params revision; mark it missing / held.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PARAMS_YAML = ROOT / "02_params" / "rexome33.yaml"
REFERENCE_JSON = ROOT / "06_analysis" / "00_dynamics" / "reference.json"

_LAST: dict = {}


def _sha(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def case_run_meta(case_dir: Path) -> dict:
    p = Path(case_dir) / "case.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8")).get("run_meta") or {}


def _reference_sha(meta: dict) -> str | None:
    ref = meta.get("reference_sha256")
    if isinstance(ref, str):  # stored as a repr in some records
        try:
            ref = json.loads(ref.replace("'", '"'))
        except ValueError:
            return None
    return (ref or {}).get("reference.json") if isinstance(ref, dict) else None


def guard(results: dict, dir_of) -> dict:
    """Filter ``results`` {case_id: result} in place-free fashion; ``dir_of(case_id)`` -> case directory (Path or
    project-relative str). Returns the kept results; the guard record is available from :func:`last_guard`."""
    current = _sha(PARAMS_YAML)
    current_ref = _sha(REFERENCE_JSON)
    kept, held, ref_mixed = {}, {}, {}
    for cid, res in results.items():
        d = dir_of(cid)
        d = d if isinstance(d, Path) else ROOT / d
        meta = case_run_meta(d)
        sha = meta.get("params_file_sha256")
        if sha != current:
            held[cid] = {"dir": str(Path(d).relative_to(ROOT)).replace("\\", "/"), "params_file_sha256": sha,
                         "status": "없음 / 판정 보류 (params revision differs)"}
            continue
        kept[cid] = res
        rsha = _reference_sha(meta)
        if rsha and current_ref and rsha != current_ref:
            ref_mixed[cid] = rsha[:16]
    record = {"params_file_sha256": current, "reference_json_sha256": current_ref,
              "cases_kept": len(kept), "cases_held": held, "reference_sha_differs": ref_mixed,
              "rule": "index entries of another params_file_sha256 are not used (missing / held, not substituted)"}
    if held:
        record["warning"] = (f"{len(held)} index entr{'y' if len(held) == 1 else 'ies'} point to batches of another "
                             "params revision; held (not judged): " + ", ".join(sorted(held)))
        print("WARNING " + record["warning"], flush=True)
    _LAST.clear()
    _LAST.update(record)
    return kept


def last_guard() -> dict:
    return dict(_LAST)
