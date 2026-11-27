"""M-5 supplement (counts only, no values):

(a) r79 KM0 lines of p815 / p816: does the T4h meta in the ``r79_<v5_setting>`` sub-folder
    carry the records the gate looks up (``ed8_record``, ``probe_stiffness_record``,
    ``hydraulic_options.ed8_settings``)? The gate's own lookup reads ``<stem>_t4h/<t4h_file>``.
(b) ``event_names`` / ``events`` name classes per line kind (fallback warning, reason event).
(c) ``head_only_declared`` true among the lines whose ``hydraulics_record.extend_bound_check``
    is null (the ③-on identity reads both).

Usage: python -I -B m5_extra.py <stage root> <out.json>
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

FALLBACK_WARNING = "WARN_ROD_PRESSURE_FALLBACK"
REASON_EVENT = "INFO_ROD_PRESSURE_FAULT_REASON"
META_KEYS = ("ed8_record", "probe_stiffness_record", "hydraulic_options",
             "hydraulic_options.ed8_settings", "lsb_components", "lsb_settings",
             "probe_d6_settings", "controller_tag")
FILES = {"impl_p85": "p85.jsonl", "impl_p88": "p88.jsonl", "impl_p815": "p815.jsonl",
         "impl_p816": "p816.jsonl", "impl_t8": "ed8_t8.jsonl", "impl_cases": "ed8_cases.jsonl"}


def dotted_state(node, path: str) -> str:
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return "absent"
        node = node[part]
    return "null" if node is None else "present"


def kind_of(row: dict) -> str:
    probe = row.get("ed8_probe")
    if isinstance(probe, dict):
        return f"arm={probe.get('arm')} plant={probe.get('plant')}"
    return f"setting={(row.get('job') or {}).get('setting')}"


def name_class(name: str) -> str:
    head = name.split(":", 1)[0]
    if head == FALLBACK_WARNING:
        return "fallback_warning"
    if head == REASON_EVENT:
        return "reason_event"
    return "other"


def main() -> int:
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    report: dict = {"km0_meta": {}, "event_name_classes": {}, "head_only": {}}
    for stage, name in FILES.items():
        path = root / f"{stage}_a1" / name
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()]
        folder = path.with_name(f"{path.stem}_t4h")
        classes: dict[str, Counter] = {}
        head_only: dict[str, Counter] = {}
        for row in rows:
            kind = kind_of(row)
            counter = classes.setdefault(kind, Counter())
            for event_name in row.get("event_names") or []:
                counter[f"event_names:{name_class(str(event_name))}"] += 1
            for event in row.get("events") or []:
                if isinstance(event, list) and len(event) > 1:
                    counter[f"events:{name_class(str(event[1]))}"] += 1
            check = (row.get("hydraulics_record") or {}).get("extend_bound_check")
            declared = row.get("head_only_declared")
            head_only.setdefault(kind, Counter())[
                f"check_{'null' if check is None else 'present'}/head_only_{declared!r}"] += 1
            if "v5_setting" in row and "key" in row:
                sub = folder / f"r79_{row.get('v5_setting')}" / str(row.get("t4h_file"))
                top = folder / str(row.get("t4h_file"))
                entry = report["km0_meta"].setdefault(f"{stage} {kind}", Counter())
                entry[f"top_file_exists:{top.is_file()}"] += 1
                entry[f"sub_file_exists:{sub.is_file()}"] += 1
                if sub.is_file():
                    with np.load(sub, allow_pickle=False) as data:
                        meta = json.loads(str(data["meta_json"])) if "meta_json" in data.files \
                            else {}
                    for key in META_KEYS:
                        entry[f"sub_meta {key}:{dotted_state(meta, key)}"] += 1
        report["event_name_classes"][stage] = {k: dict(v) for k, v in classes.items()}
        report["head_only"][stage] = {k: dict(v) for k, v in head_only.items()}
    report["km0_meta"] = {k: dict(v) for k, v in report["km0_meta"].items()}
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
