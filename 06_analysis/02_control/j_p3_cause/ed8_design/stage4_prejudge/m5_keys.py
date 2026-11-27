"""M-5 key presence of the edition 8 stage 4 outputs (C8 56849248), value blind.

For every output line kind (job setting, ``ed8_probe`` arm / plant, r79 ``v5_setting``) this
counts, per dotted key the gate / judge tools read, the lines where the key is present
(non-null), null or absent - and, for the keys the tools also look up in the line's T4h meta
(``meta_json``), where the meta carries the key. Form checks count shapes only (list lengths,
element types, event name token classes). No value is printed or written: setting / arm /
plant names are job identities.

Usage: python -I -B m5_keys.py <stage root> <v0 smoke jsonl> <out.json>
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path

import numpy as np

ABSENT = object()

RUN_V5_KEYS = (
    "commands_sha256", "t4h_file", "controller_tag", "hydraulic_options", "lsb_components",
    "lsb_settings", "probe_d6_settings", "hydraulics_record", "head_only_declared", "events",
    "event_names", "event_output", "event_output.pass", "event_output.gates.fault0",
    "event_output.fault_periods", "event_output.fault_events", "lock_window_alignment",
    "probe_stiffness_record", "ed8_record", "ed8_record.reapproach_runs",
    "ed8_record.twist_waiver", "ed8_record.twist_waiver.n_waiver_done",
    "ed8_record.twist_waiver.n_waiver_periods", "ed8_settings",
    "ed8_settings.probe_k1_scale_settings.scale_mid_min_piston_travel_m",
    "ed8_settings.r8.stiffness_warning_range", "ed8_settings.r8.lifted_reapproach.short_run_s",
    "ed8_settings.r8.lifted_reapproach.short_run_exit_samples",
    "ed8_settings.twist_completion_relax.locked_drift_waiver",
    "ed8_settings.twist_completion_relax.waiver_max_rise_N",
    "ed8_settings.twist_completion_relax.waiver_margin_N",
    "hydraulics_record.extend_bound_check", "hydraulics_record.m2_clipped_steps_post_lift",
    "event_output.reapproach_starts", "probe_d6_record")
PROBE_EXTRA_KEYS = ("ed8_probe.arm", "ed8_probe.plant", "job")
R79_KEYS = (
    "commands_sha256", "t4h_file", "key", "v5_setting", "level", "rod_model", "controller_tag",
    "hydraulic_options", "hydraulic_options.p1_patch", "hydraulic_options.ed8_settings",
    "extend_bound_check", "hydraulics_record", "hydraulics_record.extend_bound_check",
    "run_extend_start_revision", "lsb_components", "lsb_settings", "probe_d6_settings",
    "head_only_declared", "events", "base", "rod_fault", "ed8_record", "probe_stiffness_record",
    "ed8_settings", "lock_window_alignment")
META_LOOKUP_KEYS = ("lsb_components", "lsb_settings", "probe_d6_settings", "controller_tag",
                    "hydraulic_options", "hydraulic_options.ed8_settings", "ed8_record",
                    "probe_stiffness_record", "ed8_record.twist_waiver",
                    "ed8_record.reapproach_runs")
V0_KEYS_PRESENT = ("controller_tag", "commands_sha256", "event_output.reapproach_starts")
V0_ABSENT_KEYS = ("lsb_components", "lsb_settings", "lsb_record", "probe_d6_settings",
                  "probe_d6_record", "probe_stiffness_record", "ib_block_record", "ed8_settings",
                  "ed8_record", "lock_window_alignment")
V0_NULL_KEYS = ("hydraulic_options", "hydraulics_record")
FALLBACK_REASON_EVENT = "INFO_ROD_PRESSURE_FAULT_REASON"
FALLBACK_REASONS = ("D1", "D1_stuck", "D2", "D3", "D4", "D6")
FALLBACK_WARNING = "WARN_ROD_PRESSURE_FALLBACK"
EVENT_LIST_CAP = 200
LEGS = ("FL", "FR", "RL", "RR")


def dotted(node, path: str):
    for part in path.split("."):
        if isinstance(node, Mapping) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            return ABSENT
    return node


def read_rows(path: Path) -> tuple[list[dict], dict | None]:
    if path.suffix == ".jsonl":
        text = path.read_text(encoding="utf-8")
        return [json.loads(line) for line in text.splitlines() if line.strip()], None
    document = json.loads(path.read_text(encoding="utf-8"))
    return list(document.get("results") or []), document


def kind_of(row: Mapping) -> str:
    probe = row.get("ed8_probe")
    if isinstance(probe, Mapping):
        return f"arm={probe.get('arm')} plant={probe.get('plant')}"
    job = row.get("job")
    if isinstance(job, Mapping) and "setting" in job:
        return f"setting={job.get('setting')}"
    return f"v5_setting={row.get('v5_setting')}"


def meta_of(folder: Path, row: Mapping) -> dict | None:
    name = row.get("t4h_file")
    if not name or not (folder / str(name)).is_file():
        return None
    with np.load(folder / str(name), allow_pickle=False) as data:
        if "meta_json" not in data.files:
            return {}
        return json.loads(str(data["meta_json"]))


def presence(rows: list[Mapping], keys: Iterable[str]) -> dict:
    out = {}
    for key in keys:
        counts = Counter()
        for row in rows:
            value = dotted(row, key)
            counts["absent" if value is ABSENT else ("null" if value is None else "present")] += 1
        out[key] = dict(counts)
    return out


def meta_presence(rows: list[Mapping], metas: list[dict | None], keys: Iterable[str]) -> dict:
    """Per key: lines whose line lacks it (absent / null) and whose T4h meta has it."""
    out = {}
    for key in keys:
        counts = Counter()
        for row, meta in zip(rows, metas, strict=True):
            in_line = dotted(row, key)
            if meta is None:
                in_meta = "no_t4h"
            else:
                value = dotted(meta, key)
                in_meta = "absent" if value is ABSENT else ("null" if value is None else "present")
            line_state = "line_absent" if in_line is ABSENT else (
                "line_null" if in_line is None else "line_present")
            counts[f"{line_state}/meta_{in_meta}"] += 1
        out[key] = dict(counts)
    return out


def is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def form_checks(rows: list[Mapping]) -> dict:
    """Shapes the judges read; counts only."""
    counts = Counter()
    tokens = Counter()
    for row in rows:
        counts["lines"] += 1
        counts["error_lines"] += "error" in row
        sha = row.get("commands_sha256")
        counts["commands_sha256_64hex"] += isinstance(sha, str) and len(sha) == 64 and all(
            ch in "0123456789abcdef" for ch in sha)
        stiffness = row.get("probe_stiffness_record", ABSENT)
        if stiffness is not ABSENT and stiffness is not None:
            is_form = isinstance(stiffness, list) and all(
                isinstance(entry, Mapping) and "twist_stiffness_scale" in entry
                for entry in stiffness)
            counts["probe_stiffness_record_list_of_scale_entries"] += is_form
            counts["probe_stiffness_record_other_form"] += not is_form
        record = row.get("ed8_record")
        if isinstance(record, Mapping):
            runs = record.get("reapproach_runs")
            is_form = isinstance(runs, list) and all(
                isinstance(run, Mapping) and "short_run_extended" in run for run in runs)
            counts["reapproach_runs_form_ok"] += is_form
            counts["reapproach_runs_other_form"] += not is_form
            waiver = record.get("twist_waiver")
            if not isinstance(waiver, Mapping):
                counts["twist_waiver_not_object"] += 1
            else:
                values = [waiver.get(name) for name in ("n_waiver_done", "n_waiver_periods")]
                if any(value is None for value in values):
                    counts["twist_waiver_count_missing"] += 1
                elif all(is_int(value) for value in values):
                    counts["twist_waiver_counts_int"] += 1
                else:
                    counts["twist_waiver_counts_malformed"] += 1
        d6 = row.get("probe_d6_record", ABSENT)
        if d6 is ABSENT:
            counts["probe_d6_record_absent"] += 1
        elif d6 is None:
            counts["probe_d6_record_null"] += 1
        else:
            rounds = d6.get("not_opened_rounds") if isinstance(d6, Mapping) else None
            warns = d6.get("would_warn") if isinstance(d6, Mapping) else None
            is_form = (isinstance(rounds, list) and isinstance(warns, list)
                       and len(rounds) == len(warns) == len(LEGS)
                       and all(is_int(value) for value in rounds)
                       and all(isinstance(value, bool) for value in warns))
            counts["probe_d6_record_witness_form_ok"] += is_form
            counts["probe_d6_record_witness_other_form"] += not is_form
        block = row.get("lock_window_alignment", ABSENT)
        if block is not ABSENT and block is not None:
            counts["lock_window_alignment_object"] += isinstance(block, Mapping)
        events = row.get("events")
        if isinstance(events, list):
            counts["events_at_cap"] += len(events) >= EVENT_LIST_CAP
            for event in events:
                counts["event_elements"] += 1
                if not (isinstance(event, list) and len(event) == 2):
                    counts["event_elements_not_pair"] += 1
                    continue
                parts = str(event[1]).split(":")
                if parts[0] == FALLBACK_WARNING:
                    counts["fallback_warning_events"] += 1
                if parts[0] != FALLBACK_REASON_EVENT:
                    continue
                counts["reason_events"] += 1
                if len(parts) < 3:
                    counts["reason_events_fewer_than_3_parts"] += 1
                    continue
                counts["reason_events_leg_known"] += parts[1] in LEGS
                token = parts[2].strip().split(" ", 1)[0]
                tokens[token if token in FALLBACK_REASONS else "outside_set"] += 1
        elif events is not None:
            counts["events_not_list"] += 1
    return {"counts": dict(counts), "reason_token_distribution": dict(tokens)}


def file_report(path: Path) -> dict:
    rows, document = read_rows(path)
    folder = path.with_name(f"{path.stem}_t4h")
    by_kind: dict[str, list[dict]] = {}
    for row in rows:
        by_kind.setdefault(kind_of(row), []).append(row)
    out = {"lines": len(rows), "kinds": {}}
    if document is not None:
        meta = document.get("meta") if isinstance(document.get("meta"), Mapping) else {}
        out["document"] = presence([{"meta": meta}],
                                   ("meta.keys_file", "meta.keys_file.sha256",
                                    "meta.keys_file.n_keys"))
    for kind, kind_rows in sorted(by_kind.items()):
        is_r79 = "v5_setting" in kind_rows[0] and "key" in kind_rows[0]
        keys = R79_KEYS if is_r79 else RUN_V5_KEYS
        if kind.startswith("arm="):
            keys = (*keys, *PROBE_EXTRA_KEYS)
        metas = [meta_of(folder, row) for row in kind_rows]
        out["kinds"][kind] = {"lines": len(kind_rows), "r79_form": is_r79,
                              "keys": presence(kind_rows, keys),
                              "meta_lookup": meta_presence(kind_rows, metas, META_LOOKUP_KEYS),
                              "form": form_checks(kind_rows)}
    return out


def v0_smoke_report(path: Path) -> dict:
    rows, _ = read_rows(path)
    return {"lines": len(rows), "present_expected": presence(rows, V0_KEYS_PRESENT),
            "absent_expected": presence(rows, V0_ABSENT_KEYS),
            "null_expected": presence(rows, V0_NULL_KEYS),
            "settings": dict(Counter(str((row.get("job") or {}).get("setting")) for row in rows))}


STAGE_FILES = {
    "impl_p80": ["ed7_probe_a2.jsonl"], "impl_p816": ["p816.jsonl"], "impl_p85": ["p85.jsonl"],
    "impl_p88": ["p88.jsonl"], "impl_p815": ["p815.jsonl"], "impl_t8": ["ed8_t8.jsonl"],
    "impl_cases": ["ed8_cases.jsonl"],
    "l1ref": ["L1_VBN.json", "L1_VBN0.json", "L1a_VBN.json", "L1a_VBN0.json"]}


def main() -> int:
    root, v0_smoke, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    report = {"note": "counts only, no values", "files": {}}
    for stage, names in STAGE_FILES.items():
        for name in names:
            report["files"][f"{stage}/{name}"] = file_report(root / f"{stage}_a1" / name)
            print(f"done {stage}/{name}")
    report["v0_smoke"] = v0_smoke_report(v0_smoke)
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
