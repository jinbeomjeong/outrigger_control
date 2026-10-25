import sys, json
v = json.load(open(sys.argv[1], encoding="utf-8"))
for m in v["metrics"]:
    if m["case"].startswith(("E_RE1b", "K8_top_flat", "E_G4_Fs8")):
        print(m["case"], {k: round(x, 2) if isinstance(x, float) else x for k, x in m["times_s"].items()})
