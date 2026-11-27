"""Smoke checks on the two C8 V0 lines (keys and kinds only; the A/A pass / fail is not
printed): the producer premises of the NB-1 reading, then the T8'' identity and the A/A pair
verdict (``jp3_ed8_judge`` of the given judge checkout, no stub).

Usage (Chrono-dev ``python.exe -I -B``): python -I -B check_smoke.py <judge checkout> <runner>
Writes ``smoke_check.json`` beside the lines.
"""
import json
import sys
from pathlib import Path

JUDGE = Path(sys.argv[1]).resolve()
for _path in (JUDGE / "04_scripts" / "04_hydraulic" / "coupled", JUDGE / "03_src"):
    sys.path.insert(0, str(_path))

import jp3_ed8_judge as ed8  # noqa: E402


def premises(line: dict) -> dict:
    return {"has_error": "error" in line,
            "controller_tag_is_v0_tag": line.get("controller_tag") == ed8.V0_CONTROLLER_TAG,
            "controller_tag_present": "controller_tag" in line,
            "v0_absent_keys_present": [name for name in ed8.V0_ABSENT_KEYS
                                       if line.get(name) is not None],
            "hydraulic_options_is_null": line.get("hydraulic_options") is None,
            "hydraulics_record_is_null": line.get("hydraulics_record") is None,
            "lock_window_alignment_absent": "lock_window_alignment" not in line,
            "t4h_file_absent": "t4h_file" not in line,
            "has_event_output": bool(line.get("event_output")),
            "has_reapproach_starts_key": "reapproach_starts" in (line.get("event_output") or {})}


def main() -> int:
    folder = Path(sys.argv[2])
    lines = [json.loads(text) for text in
             (folder / "v0_smoke.jsonl").read_text(encoding="utf-8").splitlines() if text.strip()]
    lines.sort(key=lambda line: line["job"]["offset_s"])
    report = {"judge_code": str(JUDGE), "lines": len(lines),
              "premises": [premises(line) for line in lines],
              "v0_identity_problems": [ed8.v0_identity_problems(line) for line in lines]}
    try:
        verdict = ed8.aa_pair_verdict(lines[0], lines[1], ())
        report["aa_pair"] = {"raised": None, "j11_state": verdict["j11_state"],
                             "fail_is_bool": isinstance(verdict["fail"], bool)}
    except Exception as exc:  # noqa: BLE001 - the kind is the result
        report["aa_pair"] = {"raised": type(exc).__name__, "message": str(exc)[:300]}
    import jp3_ed7_judge as ed7

    reference = ed7.metric_of(lines[0], (), ed8.V0_LABEL)
    treatment = ed7.metric_of(lines[1], (), ed8.TREATMENT_LABEL)
    treatment["row"], treatment["phase"] = reference["row"], reference["phase"]
    unit = ed8.unit_item_verdicts([treatment], [reference],
                                  own_setting_items=ed8.AA_OWN_SETTING_ITEMS)["units"][
        (reference["row"], str(reference["phase"]))]
    report["not_judgeable_item_names"] = sorted(ed8._item_names(unit["not_judgeable_items"]))
    report["own_setting_record_items"] = [r["item"] for r in unit["own_setting_records"]]
    report["base_pass_is_bool"] = isinstance(ed8.is_base_pass(reference), bool)
    out = folder / "smoke_check.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "written", "out": str(out)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
