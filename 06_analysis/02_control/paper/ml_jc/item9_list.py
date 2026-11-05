"""List J_P / J_C episodes per case from the item-9 evidence file."""
import json
import math

P = r"C:\workspace\outrigger_control\06_analysis\02_control\s8\s8_rest_rev46_item9.json"
d = json.load(open(P, encoding="utf-8"))
print("top keys:", list(d.keys()))
for k, v in d.items():
    if k != "cases":
        print(k, json.dumps(v, ensure_ascii=False)[:1500])
cases = d["cases"]
print("n_cases", len(cases))
tot_c = tot_p = miss_c = miss_p = 0
for name, c in cases.items():
    jp, jc = c["J_P"], c["J_C"]
    nc, np_ = jc.get("episodes", 0), jp.get("episodes", 0)
    print(f"{name:40s} batch={c.get('batch','')[-24:]:24s} Fs={c.get('fs_kN')} contact={c.get('contact')} ev={c.get('event')} "
          f"JP_ep={np_} JP_M1={jp['value'][0]} JP_M1p={jp['value'][1]} JC_ep={nc} JC_M1={jc['value'][0]} JC_M1p={jc['value'][1]} tr={jc.get('transient')} M5={[round(x,2) if x is not None else None for x in c.get('M5',[])]}")
    tot_c += nc or 0
    tot_p += np_ or 0
    miss_c += jc["value"][0] or 0
    miss_p += jp["value"][0] or 0
print("episodes JC", tot_c, "JP", tot_p, "missJC", miss_c, "missJP", miss_p)
