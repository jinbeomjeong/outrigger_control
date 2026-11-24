"""436.9 edition 7 key lists (``jp3_remedy_spec_v7.md`` 4.2, 6.2, 6.3; spec 8 Y7-6).

Files in ``--out-dir`` (an existing file is never overwritten; ``--only`` writes a subset):

* ``probe_keys_ed7.json`` (4.2): the probe main part (``ed7_probe.PROBE_KEY_JOBS``: 15 keys x
  six plants x seven arms = 630 lines) and the ③ prediction part P7-8 (the 12 grid keys of
  record part D x plants ``M`` / ``Mslow`` x arm ``a2`` = 24 lines; the D key file is read from
  its git blob and its sha256 checked). Every line: the job, the key and the part.
* ``sens_keys_ed7.json`` (6.2): the ten sensitivity settings (judged VBMslow, VBMfast,
  VBMc005, VBMc04; recorded the other six) x the edition 6 subset rows
  (``ed6_key_lists.is_sens_row``: 46 per setting), each with its V0 pair, ``head_only_declared``
  and ``judged`` (the four representatives). A probe key among them is ``probe_seen`` (a stop
  condition only, spec 6.3 / Q7-U1).
* ``confirm_g1_grid171.json`` (6.3 G1, only with ``--g1-seed``: the seed is fixed at the seal):
  per cluster of the stored V0 grid one V0-passing offset not used in edition 6
  (``s30_pool_runs.csv`` ``used_ed6``; the file's sha256 is checked), drawn with numpy
  ``default_rng(seed)`` in sorted cluster order (the stats s50 form); the three clusters whose
  V0 result differs between offsets and those without an unused V0-passing offset are left
  out (171 lines). Two flags per line (user decision 2026-11-24, stats review 3 ①):
  ``counted_for_k`` is false on the three U832 clusters (``jp3_ed7_rules.U832_CLUSTERS``:
  left out of the V0 pass -> fail allowance k only, 168 lines), ``judged_fault_jp3`` is true
  on all 171 (FAULT 0 and J-P3 with the ③ rev 7 condition rows). Each count uses its own
  flag (``k_counted_lines``, ``fault_jp3_judged_lines``, ``expected_j_p3_judged_rows``).
  Setting ``VBM``; the V0 pair is the stored grid run (file, key, run id, V0 command hash).
* ``g1_pool_ed7.json`` (always): the pool counts without a draw (clusters, the mixed and the
  U832 clusters, the 171 eligible clusters and the two denominators), so the line count is
  known before the seed.

The ③ rev 7 condition rows (6.3 (다′)) are counted on the run outputs by
``jp3_rev7_condition.py`` (a condition is a property of the run, not of the key).

Exit 0 = written, 2 = input error (an output exists, an input of another sha256, a missing V0
pair or grid file, a count other than the spec's), 3 = tool error. The stdout's last line is
JSON with ``status`` and the counts.

Usage (python-dev or Chrono-dev, the code checkout root):
  python -I -B 04_scripts/04_hydraulic/coupled/ed7_key_lists.py --out-dir <keys folder>
      --pool-csv <s30_pool_runs.csv> --pool-csv-sha256 <sha> --grid-root <stored grid folder>
      [--g1-seed <int>] [--repo <main checkout>] [--only <names>]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import traceback
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import d0_plant_split as d0  # noqa: E402  (imports run_v5)
import ed6_key_lists  # noqa: E402
import ed7_probe  # noqa: E402
import jp3_ed7_rules as rules  # noqa: E402
import run_v5  # noqa: E402

EXIT_WRITTEN, EXIT_INPUT, EXIT_TOOL = 0, 2, 3
POOL_CSV_SHA256 = "8d2626afa5b43a54554e92a828407d19e46ba2063a44daaf40a157efcf269db0"
"""``ed7_design/stats_v7/s30_pool_runs.csv`` as written by stats s30 (2026-11-24)."""
GRID_FILES = ("grid_r67_main.json", "grid_r67_top.json", "grid_r69_bottom.json",
              "grid_r69_top.json")
"""The stored V0 grid (``touch_phase/acceptance/c4g2_only/grid``), later file wins (s50)."""
GRID_SETTING = "VBM"
EXPECTED_G1_LINES = 171
EXPECTED_U832_LINES = 3
EXPECTED_K_COUNTED_LINES = EXPECTED_G1_LINES - EXPECTED_U832_LINES
SENS_ROWS_PER_SETTING = 46
G1_FLAG_MEANINGS = {
    "counted_for_k": "the line enters the V0 pass -> fail allowance k (false on the three "
                     "U832 clusters only)",
    "judged_fault_jp3": "FAULT 0 and J-P3 (③ rev 7 condition rows included) are judged on "
                        "the line (all 171 lines)"}
"""G1 line flags (user decision 2026-11-24 on the stats review 3 ①; spec 6.3 U832)."""
OUTPUTS = ("probe_keys_ed7.json", "sens_keys_ed7.json", "g1_pool_ed7.json",
           "confirm_g1_grid171.json")


class InputError(Exception):
    """No output is written (exit 2)."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ------------------------------------------------------------------------------ probe keys
def d_key_blob(repo: Path) -> bytes:
    """The record part D key file from its git blob (sha256 checked)."""
    done = subprocess.run(["git", "-C", str(repo), "cat-file", "-p", ed7_probe.D_KEY_FILE_BLOB],
                          capture_output=True, timeout=120, check=False)
    if done.returncode != 0:
        raise InputError(f"git cat-file {ed7_probe.D_KEY_FILE_BLOB} failed: "
                         f"{done.stderr.decode('utf-8', 'replace').strip()}")
    if _sha256(done.stdout) != ed7_probe.D_KEY_FILE_SHA256:
        raise InputError("the record part D key blob is not of the pinned sha256")
    return done.stdout


def d_jobs_from_blob(data: bytes) -> list[dict]:
    """The 12 jobs of the D key file, without the run-only keys."""
    return [{key: value for key, value in entry["job"].items() if key not in ("setting",)}
            for entry in json.loads(data)["jobs"]]


def probe_document(repo: Path, command: str) -> dict:
    blob_jobs = d_jobs_from_blob(d_key_blob(repo))
    if blob_jobs != [dict(job) for job in ed7_probe.D_KEY_JOBS]:
        raise InputError("ed7_probe.D_KEY_JOBS differ from the record part D key file")
    jobs = ed7_probe.probe_jobs()
    lines = [{"job": job, "key": d0.key_name(job),
              "part": "d" if ed7_probe._is_d_job(job) else "main"} for job in jobs]
    main_lines = sum(line["part"] == "main" for line in lines)
    return {"rule": "jp3_remedy_spec_v7.md 4.2 (keys >= 14, plants, arms; P7-8 D part)",
            "generation_command": command, "code_identity": ed6_key_lists.code_identity(),
            "keys": list(ed7_probe.KEYS), "plants": list(ed7_probe.PLANTS),
            "arms": {arm: list(components) for arm, components in ed7_probe.ARMS.items()},
            "arm_parameters": ed7_probe.ARM_PARAMETERS,
            "arms_without_d6": list(ed7_probe.ARMS_WITHOUT_D6),
            "d_key_file": {"blob": ed7_probe.D_KEY_FILE_BLOB,
                           "sha256": ed7_probe.D_KEY_FILE_SHA256},
            "expected_lines": len(lines), "main_part_lines": main_lines,
            "d_part_lines": len(lines) - main_lines, "lines": lines}


# ------------------------------------------------------------------------------ sensitivity
def sens_document(command: str) -> dict:
    settings = tuple(f"VBM{key}" for key in run_v5.ED7_SENSITIVITY)
    lines = ed6_key_lists.required_lines(ed6_key_lists.is_sens_row, settings,
                                         run_v5.required_rows())
    probe_keys = set(ed7_probe.KEYS)
    for line in lines:
        line["judged"] = line["job"]["setting"] in run_v5.ED7_SENSITIVITY_SETTINGS
        line["probe_seen"] = line["key"] in probe_keys
    if len(lines) != SENS_ROWS_PER_SETTING * len(settings):
        raise InputError(f"sensitivity: {len(lines)} lines, expected "
                         f"{SENS_ROWS_PER_SETTING * len(settings)}")
    judged = [line for line in lines if line["judged"]]
    return {"rule": "jp3_remedy_spec_v7.md 6.2 (judged four, recorded six; the edition 6 "
                    "subset rows)", "generation_command": command,
            "code_identity": ed6_key_lists.code_identity(),
            "settings_judged": list(run_v5.ED7_SENSITIVITY_SETTINGS),
            "settings_record": list(run_v5.ED7_SENSITIVITY_RECORD_SETTINGS),
            "expected_lines": len(lines), "judged_lines": len(judged),
            "expected_j_p3_judged_rows": sum(not line["head_only_declared"] for line in judged),
            "probe_seen_units": sum(line["probe_seen"] for line in lines), "lines": lines}


# ------------------------------------------------------------------------------ G1 grid
def read_pool(path: Path, expected_sha256: str) -> list[dict]:
    data = path.read_bytes()
    if _sha256(data) != expected_sha256:
        raise InputError(f"--pool-csv {path} is not of the given sha256")
    return list(csv.DictReader(data.decode("utf-8").splitlines()))


def _cluster_of(row: dict) -> tuple:
    return (row["level"], float(row["fs_kN"]), row["timing"], row["leg"], row["event"])


def pool_clusters(rows: list[dict]) -> dict:
    """Clusters, their V0-mixed flag and their candidates (unused in edition 6, V0 passing)."""
    clusters: dict[tuple, list[dict]] = defaultdict(list)
    for row in rows:
        clusters[_cluster_of(row)].append(row)
    out = {}
    for cluster in sorted(clusters):
        members = clusters[cluster]
        out[cluster] = {
            "is_mixed": len({member["v0_pass"] for member in members}) > 1,
            "candidates": sorted((member for member in members
                                  if member["used_ed6"] == "False" and member["v0_pass"] == "True"),
                                 key=lambda member: float(member["offset_s"]))}
    return out


def _is_u832(cluster: tuple) -> bool:
    level, fs_kN, timing, leg, event = cluster
    return rules.is_u832_cluster(level, leg, fs_kN, event, timing)


def pool_document(rows: list[dict], pool_sha256: str) -> dict:
    clusters = pool_clusters(rows)
    eligible = [cluster for cluster, entry in clusters.items()
                if entry["candidates"] and not entry["is_mixed"]]
    u832 = [cluster for cluster in eligible if _is_u832(cluster)]
    if len(eligible) != EXPECTED_G1_LINES or len(u832) != EXPECTED_U832_LINES:
        raise InputError(f"G1: {len(eligible)} eligible clusters / {len(u832)} U832, expected "
                         f"{EXPECTED_G1_LINES} / {EXPECTED_U832_LINES}")
    return {"rule": "jp3_remedy_spec_v7.md 6.3 G1 (one unused V0-passing offset per cluster; "
                    "V0-mixed clusters out; U832 run and recorded)",
            "pool_csv_sha256": pool_sha256, "clusters": len(clusters),
            "mixed_clusters": [list(cluster) for cluster, entry in clusters.items()
                               if entry["is_mixed"]],
            "without_candidate": sum(not entry["candidates"] for entry in clusters.values()),
            "eligible_clusters": len(eligible), "u832_clusters": [list(c) for c in u832],
            "line_flags": G1_FLAG_MEANINGS, "expected_lines": len(eligible),
            "k_counted_lines": len(eligible) - len(u832),
            "fault_jp3_judged_lines": len(eligible)}


def grid_event_name(event) -> str:
    """The event name of a stored grid run (stats s50 ``event_name``)."""
    if isinstance(event, dict):
        for key in ("name", "kind", "type", "label"):
            if key in event:
                return str(event[key])
    return str(event)


def stored_grid_runs(grid_root: Path) -> dict[tuple, dict]:
    """Identifier -> (file, key, run id, V0 command hash) of the stored V0 grid (s50 form)."""
    runs = {}
    for name in GRID_FILES:
        path = grid_root / name
        if not path.is_file():
            raise InputError(f"stored grid file {path} not found")
        document = json.loads(path.read_text(encoding="utf-8"))
        for job in document["results"]:
            items = (job["runs"].items() if isinstance(job["runs"], dict)
                     else enumerate(job["runs"]))
            for run_id, run in items:
                identifier = (job["level"], float(job["fs_kN"]), job["timing"], job["leg"],
                              grid_event_name(run.get("event")), float(run["offset_s"]))
                runs[identifier] = {"file": name, "key": job["key"], "run_id": str(run_id),
                                    "v0_commands_sha256": run.get("commands_sha256")}
    return runs


def g1_document(rows: list[dict], grid_root: Path, seed: int, pool: dict,
                command: str) -> dict:
    clusters = pool_clusters(rows)
    stored = stored_grid_runs(grid_root)
    rng = np.random.default_rng(seed)
    lines = []
    for cluster, entry in clusters.items():
        if entry["is_mixed"] or not entry["candidates"]:
            continue
        pick = entry["candidates"][int(rng.integers(len(entry["candidates"])))]
        level, fs_kN, timing, leg, event = cluster
        identifier = (*cluster, float(pick["offset_s"]))
        reference = stored.get(identifier)
        if reference is None or reference["v0_commands_sha256"] != pick["v0_sha"]:
            raise InputError(f"no stored V0 grid run of the hash {pick['v0_sha']} for "
                             f"{identifier}")
        twin = {"level": level, "leg": leg, "fs_kN": fs_kN, "event": event, "timing": timing}
        job = {"case": "R12", "eps": 0.0, "offset_s": float(pick["offset_s"]), "twin": twin,
               "setting": GRID_SETTING}
        lines.append({"job": job, "t4h_file": run_v5.t4h_file_name(job),
                      "v0_pair": {**reference, "file": f"{ed6_key_lists.GRID_FILE_ROOT}/"
                                                        f"{reference['file']}",
                                  "v0_pass": True},
                      **g1_line_flags(cluster),
                      "head_only_declared": ed6_key_lists.is_head_only(job)})
    denominators = g1_denominators(lines)
    if (len(lines), denominators["k_counted_lines"]) != (EXPECTED_G1_LINES,
                                                         EXPECTED_K_COUNTED_LINES):
        raise InputError(f"G1: {len(lines)} lines / {denominators['k_counted_lines']} counted "
                         f"for k, expected {EXPECTED_G1_LINES} / {EXPECTED_K_COUNTED_LINES}")
    return {"rule": pool["rule"], "generation_command": command,
            "code_identity": ed6_key_lists.code_identity(), "seed": seed,
            "extraction": "numpy default_rng(seed), sorted cluster order, uniform among the "
                          "cluster's unused V0-passing offsets (stats s50 form)",
            "pool_csv_sha256": pool["pool_csv_sha256"], "settings": [GRID_SETTING],
            "line_flags": G1_FLAG_MEANINGS, "expected_lines": len(lines), **denominators,
            "lines": lines}


def g1_line_flags(cluster: tuple) -> dict[str, bool]:
    """The two per-line criteria flags of G1 (user decision 2026-11-24, stats review 3 ①)."""
    return {"counted_for_k": not _is_u832(cluster), "judged_fault_jp3": True}


def g1_denominators(lines: list[dict]) -> dict[str, int]:
    """Each G1 criterion counted on its own flag, so no count mixes the two denominators."""
    fault_jp3_lines = [line for line in lines if line["judged_fault_jp3"]]
    return {"k_counted_lines": sum(line["counted_for_k"] for line in lines),
            "fault_jp3_judged_lines": len(fault_jp3_lines),
            "expected_j_p3_judged_rows": sum(not line["head_only_declared"]
                                             for line in fault_jp3_lines)}


# ------------------------------------------------------------------------------ CLI
def selected_outputs(text: str, has_seed: bool) -> tuple[str, ...]:
    names = tuple(name for name in text.split(",") if name)
    unknown = [name for name in names if name not in OUTPUTS]
    if unknown or not names:
        raise InputError(f"--only {text}: names of {OUTPUTS}")
    if "confirm_g1_grid171.json" in names and not has_seed:
        raise InputError("confirm_g1_grid171.json needs --g1-seed (fixed at the seal)")
    return names


def build(args: argparse.Namespace, names: tuple[str, ...], command: str) -> dict[str, dict]:
    documents: dict[str, dict] = {}
    if "probe_keys_ed7.json" in names:
        documents["probe_keys_ed7.json"] = probe_document(args.repo, command)
    if "sens_keys_ed7.json" in names:
        documents["sens_keys_ed7.json"] = sens_document(command)
    if {"g1_pool_ed7.json", "confirm_g1_grid171.json"} & set(names):
        rows = read_pool(args.pool_csv, args.pool_csv_sha256)
        pool = pool_document(rows, args.pool_csv_sha256)
        if "g1_pool_ed7.json" in names:
            documents["g1_pool_ed7.json"] = {**pool, "generation_command": command}
        if "confirm_g1_grid171.json" in names:
            documents["confirm_g1_grid171.json"] = g1_document(rows, args.grid_root,
                                                               args.g1_seed, pool, command)
    return documents


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--pool-csv", type=Path, required=True)
    parser.add_argument("--pool-csv-sha256", default=POOL_CSV_SHA256)
    parser.add_argument("--grid-root", type=Path, required=True)
    parser.add_argument("--g1-seed", type=int, default=None)
    parser.add_argument("--repo", type=Path, default=Path(r"C:\workspace\outrigger_control"),
                        help="git checkout that holds the record part D commit")
    parser.add_argument("--only", default="probe_keys_ed7.json,sens_keys_ed7.json,"
                                          "g1_pool_ed7.json")
    args = parser.parse_args(argv)
    command = ("python -I -B 04_scripts/04_hydraulic/coupled/ed7_key_lists.py --out-dir "
               f"{args.out_dir} --pool-csv {args.pool_csv} --pool-csv-sha256 "
               f"{args.pool_csv_sha256} --grid-root {args.grid_root} --repo {args.repo} "
               f"--only {args.only}" + ("" if args.g1_seed is None
                                        else f" --g1-seed {args.g1_seed}"))
    try:
        names = selected_outputs(args.only, args.g1_seed is not None)
        if any((args.out_dir / name).exists() for name in names):
            raise InputError("an output exists (never overwritten)")
        documents = build(args, names, command)
    except InputError as exc:
        print(json.dumps({"status": "input_error", "reason": str(exc)}))
        return EXIT_INPUT
    except Exception:  # every unexpected failure is a tool error (exit 3)
        traceback.print_exc()
        print(json.dumps({"status": "tool_error"}))
        return EXIT_TOOL
    args.out_dir.mkdir(parents=True, exist_ok=True)
    shas = {}
    for name in names:
        data = (json.dumps(documents[name], indent=1) + "\n").encode("utf-8")
        with (args.out_dir / name).open("xb") as handle:
            handle.write(data)
        shas[name] = _sha256(data)
    print(json.dumps({"status": "written", "sha256": shas,
                      "lines": {name: documents[name].get("expected_lines") for name in names}}))
    return EXIT_WRITTEN


if __name__ == "__main__":
    sys.exit(main())
