"""Dump lsb_record.blind of a2 lines with triggers, an event-path line's events, extend_bound_check."""
import json

PATH = (r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs"
        r"\6bfb2560\ed7_probe_a1\ed7_probe.jsonl")

shown_blind = shown_ebc = shown_ev = 0
with open(PATH, encoding="utf-8") as fh:
    for line in fh:
        rec = json.loads(line)
        arm = rec["ed7_probe"]["arm"]
        blind = rec["lsb_record"].get("blind")
        if shown_blind == 0 and arm == "a2" and blind:
            s = json.dumps(blind)
            if '"shots": [{' in s or "trigger" in s:
                print("BLIND", rec["job"], s[:6000])
                shown_blind += 1
        ebc = rec["hydraulics_record"].get("extend_bound_check")
        if ebc is not None and shown_ebc == 0:
            print("EBC", rec["job"], json.dumps(ebc)[:2500])
            shown_ebc += 1
        if rec.get("t_event_s") is not None and shown_ev == 0:
            print("EVENT", rec["job"], rec["t_event_s"], json.dumps(rec["events"])[:1500])
            print("EVENT_NAMES", json.dumps(rec["event_names"])[:2500])
            print("VALUES.events", json.dumps(rec["values"]["events"])[:1500])
            print("event_output", json.dumps(rec["event_output"])[:1500])
            shown_ev += 1
        if shown_blind and shown_ebc and shown_ev:
            break
