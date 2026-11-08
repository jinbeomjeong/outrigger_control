"""Criteria revision 8 7.3: two stage 3 Chrono VB rows rerun with ③ on against the stored runs.

``argv``: the run command of a row, from the stored stage 3 ``batch.json`` row with the ③ argument
(``--extend-start-tracked``) added and the tag ``v5p3_VB_<case>``; printed as one JSON list.

``compare``: a rerun case folder against the stored ③-off folder:

1. ``record/record.npz`` ``u_applied``, ``u_cmd``, ``F_cyl``, ``body_quat_wxyz`` bit-identical
   (SHA-256 of ``np.ascontiguousarray(a).tobytes()``, P3-10), and the stored arrays equal the
   sealed values of revision 8 7.3 (:data:`SEALED_SHA256`);
2. ``controller_events.json`` events (name, time) equal (content, not file bytes);
3. ``result.json`` ``controller_meta`` differs only in ③ keys (:data:`P3_META_TOKENS`) and,
   by criteria revision 10, ``two_pressure.fallback_rod_estimate_Pa`` when (A) the rerun has no
   ``WARN_ROD_PRESSURE_FALLBACK`` event, (B) checks 1 and 2 passed and (C) per leg rerun >=
   stored - 1 Pa (output ``revision10_fallback_estimate``);
4. ``hydraulics_record.extend_bound_check`` present, ext_moving ``sum(breach_reads)`` = 0;
5. the rerun ran ③ on (two-pressure rule ``tracked_bound``, revision 4; ``v5_hydraulics``
   ``controller_tag`` ``final_C4G2_P3``).

Read only. Exit code 0 = pass, 1 = a check failed, 2 = input missing.

Usage (python-dev, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/p3_chrono_check.py argv <case>
      [--batch-json 07_results/S9/batch_V5-STAGE3_20261107_184341/batch.json]
  python -I -B 04_scripts/04_hydraulic/coupled/p3_chrono_check.py compare <case> <rerun case folder>
      <out_json> [--stored <stored case folder>]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STAGE3_BATCH_JSON = ROOT / "07_results" / "S9" / "batch_V5-STAGE3_20261107_184341" / "batch.json"
STORED_RUNS = {
    "E_G4_Fs8": ROOT / "07_results" / "S8" / "v5s3_VB_E_G4_Fs8_20261107_214226" / "E_G4_Fs8",
    "S_top_fdown3.5_wika_Fs8": (ROOT / "07_results" / "S8"
                                / "v5s3_VB_S_top_fdown3.5_wika_Fs8_20261107_222708"
                                / "S_top_fdown3.5_wika_Fs8"),
}
"""Criteria revision 8 7.3: the two rows and their stored ③-off runs."""
COMPARED_ARRAYS = ("u_applied", "u_cmd", "F_cyl", "body_quat_wxyz")
SEALED_SHA256 = {
    "E_G4_Fs8": {
        "u_applied": "793b816e769074229e598f29b8e6825b473814a305f79482ba60bcee1c3fb8ef",
        "u_cmd": "d7df90542d137a00ed090233be76a33009e6e9345ae63915c487964b9496ec22",
        "F_cyl": "3823afd977545ab0c3229f5ffa6d11514e63c047f817a7ffd2ac0a781e8dd2cd",
        "body_quat_wxyz": "625e1e07d0512595a2adb4aeae7ef6d9f6cf55fe824dc9102c9c98879c00cc06"},
    "S_top_fdown3.5_wika_Fs8": {
        "u_applied": "fc63355085b78c7bcd693999d7c7d9055e80d9d986b58ba85d32e3b6c27d6d2b",
        "u_cmd": "867634ce5d6a95de22ffc8474068e9ea5a95416bf5f98313ff315ae76d1d5815",
        "F_cyl": "19de3e78afbbe052ae1a8f5b98525377aabc82966f03e5e4e099ca19df85f70e",
        "body_quat_wxyz": "70a4da9df199a2a2a661bf54ca12fd36efa9c471b1421c054abe727408f550af"},
}
"""Criteria revision 8 7.3 table (control-expert, from the stored ``record.npz``)."""
P3_ARGUMENT = "--extend-start-tracked"
P3_TAG_PREFIX = "v5p3_VB_"
P3_META_TOKENS = ("extend_start", "extend_bound", "lock_seed")
"""Controller meta paths with one of these parts are the ③ keys (rule, bound, revision, its
records)."""
EXPECTED_TAG = "final_C4G2_P3"
EXPECTED_RULE = "tracked_bound"
EXPECTED_REVISION = 4
EVENT_TEXT = re.compile(r"t_s=([-+0-9.eE]+), name='([^']*)'")
FALLBACK_ESTIMATE_KEY = "fallback_rod_estimate_Pa"
FALLBACK_ESTIMATE_PATH = f"two_pressure.{FALLBACK_ESTIMATE_KEY}"
"""Criteria revision 10: the fallback shadow's run-end value, allowed in check 3 under A, B, C."""
FALLBACK_ESTIMATE_TOL_PA = 1.0
FALLBACK_EVENT = "WARN_ROD_PRESSURE_FALLBACK"
REVISION10_SEAL = (ROOT / "06_analysis" / "03_hydraulic" / "coupled" / "v5"
                   / "v5_criteria_rev10.sha256")


def rerun_argv(case: str, batch_json: Path = STAGE3_BATCH_JSON) -> list[str]:
    """The stored row's argv with the ③ argument and the ``v5p3_VB_<case>`` tag.

    Raises:
        KeyError: No VB row of that case in the batch.
    """
    batch = json.loads(batch_json.read_text(encoding="utf-8"))
    rows = [row for row in batch["cases"]
            if row.get("case") == case and row.get("v5_setting") == "VB"]
    if len(rows) != 1:
        raise KeyError(f"{batch_json.name}: {len(rows)} VB rows named {case!r}")
    argv = list(rows[0]["argv"])
    argv[argv.index("--tag") + 1] = f"{P3_TAG_PREFIX}{case}"
    if P3_ARGUMENT not in argv:
        argv.append(P3_ARGUMENT)
    return argv


def array_digests(case_dir: Path) -> dict[str, str]:
    with np.load(case_dir / "record" / "record.npz", allow_pickle=False) as data:
        return {name: hashlib.sha256(np.ascontiguousarray(data[name]).tobytes()).hexdigest()
                for name in COMPARED_ARRAYS}


def controller_events(case_dir: Path) -> list[tuple[float, str]]:
    """(time, name) of ``controller_events.json`` (``C2Event(...)`` strings or dicts)."""
    out = []
    for item in json.loads((case_dir / "controller_events.json").read_text(encoding="utf-8")):
        if isinstance(item, dict):
            out.append((float(item["t_s"]), str(item["name"])))
            continue
        match = EVENT_TEXT.search(str(item))
        if match is None:
            raise ValueError(f"controller event not readable: {item!r}")
        out.append((float(match.group(1)), match.group(2)))
    return out


def differing_paths(before, after, path: str = "") -> list[str]:
    """Dotted paths where two JSON values differ."""
    if isinstance(before, dict) and isinstance(after, dict):
        paths = []
        for key in sorted(set(before) | set(after)):
            child = f"{path}.{key}" if path else str(key)
            paths += differing_paths(before.get(key), after.get(key), child)
        return paths
    return [] if before == after else [path]


def is_p3_path(path: str) -> bool:
    return any(token in part for part in path.split(".") for token in P3_META_TOKENS)


def fallback_estimate_conditions(stored_meta: dict, rerun_meta: dict,
                                 rerun_events: list[tuple[float, str]],
                                 arrays_equal: bool, events_equal: bool) -> dict:
    """Criteria revision 10 3: conditions A, B, C under which a differing
    ``two_pressure.fallback_rod_estimate_Pa`` (the fallback shadow's run-end value) is allowed.

    A: no ``WARN_ROD_PRESSURE_FALLBACK`` event in the rerun; B: checks 1 and 2 passed;
    C: per leg rerun >= stored - 1 Pa (③ only raises the estimate).
    """
    stored_values = (stored_meta.get("two_pressure") or {}).get(FALLBACK_ESTIMATE_KEY)
    rerun_values = (rerun_meta.get("two_pressure") or {}).get(FALLBACK_ESTIMATE_KEY)
    fallback_events = [name for _, name in rerun_events if name.startswith(FALLBACK_EVENT)]
    per_leg = []
    if stored_values is not None and rerun_values is not None:
        for stored_Pa, rerun_Pa in zip(stored_values, rerun_values, strict=True):
            is_ok = (stored_Pa is not None and rerun_Pa is not None
                     and float(rerun_Pa) >= float(stored_Pa) - FALLBACK_ESTIMATE_TOL_PA)
            per_leg.append({"stored_Pa": stored_Pa, "rerun_Pa": rerun_Pa, "ok": is_ok})
    conditions = {
        "A_no_fallback_event": not fallback_events,
        "B_arrays_and_events_equal": bool(arrays_equal and events_equal),
        "C_rerun_not_below_stored": bool(per_leg) and all(leg["ok"] for leg in per_leg)}
    return {"conditions": conditions, "all": all(conditions.values()),
            "fallback_events": fallback_events[:20], "per_leg": per_leg}


def revision10_digest(seal_path: Path | None = None) -> str:
    """SHA-256 of revision 10 from its seal file (first token); if the seal file is missing,
    the digest of the document itself with a note."""
    seal_path = seal_path or REVISION10_SEAL
    if seal_path.is_file():
        return seal_path.read_text(encoding="utf-8").split()[0]
    document = seal_path.with_suffix(".md")
    if document.is_file():
        digest = hashlib.sha256(document.read_bytes()).hexdigest()
        return f"{digest} (document digest, seal file {seal_path.name} missing)"
    return f"unknown (neither {seal_path.name} nor its .md found)"


def compare(case: str, stored_dir: Path, rerun_dir: Path) -> dict:
    """The five checks of the module docstring."""
    stored_digests, rerun_digests = array_digests(stored_dir), array_digests(rerun_dir)
    stored_result = json.loads((stored_dir / "result.json").read_text(encoding="utf-8"))
    rerun_result = json.loads((rerun_dir / "result.json").read_text(encoding="utf-8"))
    meta_paths = differing_paths(stored_result["controller_meta"], rerun_result["controller_meta"])
    other_paths = [path for path in meta_paths
                   if not is_p3_path(path) and path != FALLBACK_ESTIMATE_PATH]
    bound_check = (rerun_result.get("hydraulics_record") or {}).get("extend_bound_check")
    breach_reads = None if bound_check is None else sum(bound_check["breach_reads"])
    settings = rerun_result["controller_meta"]["two_pressure"]["settings"]
    revision = (settings.get("extend_start_bound") or {}).get("revision")
    tag = (rerun_result.get("v5_hydraulics") or {}).get("controller_tag")
    arrays_equal = (stored_digests == rerun_digests
                    and stored_digests == SEALED_SHA256.get(case))
    rerun_events = controller_events(rerun_dir)
    events_equal = controller_events(stored_dir) == rerun_events
    fallback_differs = FALLBACK_ESTIMATE_PATH in meta_paths
    revision10 = fallback_estimate_conditions(stored_result["controller_meta"],
                                              rerun_result["controller_meta"], rerun_events,
                                              arrays_equal, events_equal)
    checks = {
        "1_arrays_bit_identical": arrays_equal,
        "2_events_equal": events_equal,
        "3_controller_meta_only_p3": (not other_paths
                                      and (not fallback_differs or revision10["all"])),
        "4_ext_moving_breach_zero": breach_reads == 0,
        "5_p3_on": (settings.get("extend_start_rule") == EXPECTED_RULE
                    and revision == EXPECTED_REVISION and tag == EXPECTED_TAG)}
    return {"case": case, "stored": str(stored_dir), "rerun": str(rerun_dir),
            "pass": all(checks.values()), "checks": checks,
            "stored_sha256": stored_digests, "rerun_sha256": rerun_digests,
            "stored_equals_sealed": stored_digests == SEALED_SHA256.get(case),
            "controller_meta_p3_paths": [p for p in meta_paths if is_p3_path(p)],
            "controller_meta_other_paths": other_paths,
            "fallback_rod_estimate_differs": fallback_differs,
            "revision10_fallback_estimate": revision10,
            "ext_moving_breach_reads": breach_reads,
            "margin_used_reads": None if bound_check is None
            else sum(bound_check["margin_used_reads"])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p_argv = sub.add_parser("argv")
    p_argv.add_argument("case", choices=tuple(STORED_RUNS))
    p_argv.add_argument("--batch-json", default=str(STAGE3_BATCH_JSON))
    p_compare = sub.add_parser("compare")
    p_compare.add_argument("case", choices=tuple(STORED_RUNS))
    p_compare.add_argument("rerun")
    p_compare.add_argument("out_json")
    p_compare.add_argument("--stored", default=None)
    p_compare.add_argument("--revision10-seal", default=str(REVISION10_SEAL),
                           help="seal file of criteria revision 10 (digest in the rule text)")
    args = parser.parse_args()
    if args.command == "argv":
        print(json.dumps(rerun_argv(args.case, Path(args.batch_json))))
        return 0
    stored = Path(args.stored) if args.stored else STORED_RUNS[args.case]
    rerun = Path(args.rerun)
    if not (stored / "result.json").is_file() or not (rerun / "result.json").is_file():
        print(json.dumps({"error": "case folder missing"}))
        return 2
    report = {"rule": ("criteria revision 8 7.3 (checks 1-5 of the module docstring) with "
                       f"revision 10 (sha256 {revision10_digest(Path(args.revision10_seal))}) "
                       "for check 3"),
              **compare(args.case, stored, rerun)}
    Path(args.out_json).write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("case", "pass", "checks")}))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
