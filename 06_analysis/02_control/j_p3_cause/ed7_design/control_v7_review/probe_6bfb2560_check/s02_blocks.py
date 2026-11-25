"""Dump the probe_d6_record of the first line that has one, and lsb_record legs of an a2 line."""
import json

PATH = (r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs"
        r"\6bfb2560\ed7_probe_a1\ed7_probe.jsonl")

d6_done = lsb_done = False
n = n_d6 = 0
with open(PATH, encoding="utf-8") as fh:
    for line in fh:
        rec = json.loads(line)
        n += 1
        d6 = rec.get("probe_d6_record")
        if d6 is not None:
            n_d6 += 1
        if d6 is not None and not d6_done:
            print("D6 line", rec["job"], rec["t4h_file"])
            rounds = d6.get("rounds", [])
            print("keys", list(d6.keys()), "n rounds", len(rounds))
            for r in rounds[:6]:
                print(json.dumps(r))
            print({k: v for k, v in d6.items() if k != "rounds"})
            d6_done = True
        if not lsb_done and rec["ed7_probe"]["arm"] == "a2":
            legs = rec["lsb_record"]["legs"]
            for leg, v in legs.items():
                print("LSB", leg, json.dumps(v)[:3000])
            print("lsb_record keys", list(rec["lsb_record"].keys()))
            lsb_done = True
print("lines", n, "with d6 record", n_d6)
