"""Build ``diag_jobs.json``: the diagnostic V0 jobs, where the sealed key file names them and
the stored stage-5 line of each (record only).

Usage (python-dev or dynamics-dev):
  python.exe -I -B make_diag_jobs.py <out folder>

Jobs 1-4 are those of ``aa_cause_analysis.md`` "메인 세션 권고" (closing judgement 4.5); S1-S3
are added stored neighbours (a reproduction check where jobs 2 and 3 have no stored line, and
the FAULT twin of job 3). Refuses an existing ``diag_jobs.json``; exit 2 when the key file sha
differs or a job is not in the key file.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

J_P3 = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause")
KEY_FILE = J_P3 / "ed8_design" / "keys_seal_41e107e9" / "heldout_g_ed8.json"
KEY_FILE_SHA256 = "a18b5818734f1b10840c903fb9e4b5c140f619705048344f9ea48d16d3142ee5"
RUN = J_P3 / "j9_runs" / "56849248"
STORED = {
    "ho_v0": RUN / "ho_v0_a1" / "ed8_heldout_v0.jsonl",
    "ho_aa2": RUN / "ho_aa2_a1" / "ed8_heldout_aa2.jsonl",
    "ho_aa3": RUN / "ho_aa3_a1" / "ed8_heldout_aa3.jsonl",
}
DEFAULT_SHAPE: dict = {}
SHAPE_30_004 = {"depth_m": 0.03, "ramp_s": 0.04}
SHAPE_25_005 = {"depth_m": 0.025, "ramp_s": 0.05}


def _job(leg: str, fs_kN: float, timing: str, offset_s: float, shape: dict) -> dict:
    twin = {"level": "bottom", "leg": leg, "fs_kN": fs_kN, "event": "RE1bF", "timing": timing,
            **shape}
    return {"case": "R12", "eps": 0.0, "offset_s": offset_s, "twin": twin, "setting": "V0"}


DIAG_JOBS = [
    ("J1_l179_FR_Fs0_level_30mm004_o0875", "key line 179 A/A candidate (FAULT)",
     _job("FR", 0.0, "level", 0.0875, SHAPE_30_004)),
    ("J2_l179_FR_Fs0_level_30mm004_o075", "same shape, o 0.075 (pass expected)",
     _job("FR", 0.0, "level", 0.075, SHAPE_30_004)),
    ("J3_l173_FL_Fs2_level_25mm005_o0875", "key line 173 base shape at o 0.0875 (pass expected)",
     _job("FL", 2.0, "level", 0.0875, SHAPE_25_005)),
    ("J4_l270_FR_Fs1_ready_default_o0875", "key line 270 A/A candidate (FAULT)",
     _job("FR", 1.0, "ready", 0.0875, DEFAULT_SHAPE)),
    ("S1_l173_FL_Fs2_level_30mm004_o0875", "added: key line 173 A/A candidate (FAULT), the "
     "shape twin of J3", _job("FL", 2.0, "level", 0.0875, SHAPE_30_004)),
    ("S2_FR_Fs2_level_30mm004_o075", "added: stored neighbour of J2 (F_s 2 kN)",
     _job("FR", 2.0, "level", 0.075, SHAPE_30_004)),
    ("S3_FL_Fs0_level_25mm005_o0875", "added: stored neighbour of J3 (F_s 0 kN)",
     _job("FL", 0.0, "level", 0.0875, SHAPE_25_005)),
]


def _key(job: dict) -> str:
    return json.dumps({k: job[k] for k in sorted(job) if k not in ("mask", "t4h_dir")},
                      sort_keys=True)


def _key_file_places(lines: list[dict]) -> dict[str, list[str]]:
    """Job key -> where the key file names it (``line <i> v0_pair`` / ``line <i> aa_order[k]``)."""
    places: dict[str, list[str]] = {}
    for index, line in enumerate(lines):
        named = [("v0_pair", line["v0_pair"]["job"])]
        named += [(f"aa_order[{k}]", job) for k, job in enumerate(line["aa_order"])]
        for where, job in named:
            places.setdefault(_key(job), []).append(
                f"line {index} {line['source']} {line['slot']} {where}")
    return places


def _stored_lines() -> dict[str, list[dict]]:
    stored: dict[str, list[dict]] = {}
    for name, path in STORED.items():
        for number, text in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            record = json.loads(text)
            stored.setdefault(_key(record["job"]), []).append({
                "file": f"{path.parent.name}/{path.name}", "batch": name, "file_line": number,
                "commands_sha256": record.get("commands_sha256"),
                "final_phase": record.get("final_phase"), "error": record.get("error"),
                "wall_s": record.get("wall_s")})
    return stored


def main() -> int:
    out = Path(sys.argv[1])
    target = out / "diag_jobs.json"
    if target.exists():
        print(f"refusing to overwrite {target}")
        return 2
    data = KEY_FILE.read_bytes()
    if hashlib.sha256(data).hexdigest() != KEY_FILE_SHA256:
        print(f"{KEY_FILE} sha256 differs from the sealed value")
        return 2
    places = _key_file_places(json.loads(data)["lines"])
    stored = _stored_lines()
    entries = []
    for label, purpose, job in DIAG_JOBS:
        key = _key(job)
        if key not in places:
            print(f"{label}: not in the key file")
            return 2
        entries.append({"label": label, "purpose": purpose, "job": job,
                        "key_file_places": places[key], "stored": stored.get(key, [])})
    target.write_text(json.dumps(entries, indent=1), encoding="utf-8")
    for entry in entries:
        print(entry["label"], len(entry["key_file_places"]), len(entry["stored"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
