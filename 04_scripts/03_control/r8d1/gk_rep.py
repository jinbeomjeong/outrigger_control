import json, re
d = json.load(open("" + __import__("sys").argv[1] + ""))["summary"]
agg = {}
for k, v in d.items():
    base = re.sub(r"_g\d$", "", k)
    a = agg.setdefault(base, [0, None, 0, 0])
    if v["Ms_worst"] > a[0]:
        a[0] = v["Ms_worst"]; a[1] = (v["plant"], v["ch"], v["w_Ms"])
    a[2] = max(a[2], v["over1.5"]); a[3] = max(a[3], v["Ms_leg_max"])
for k, a in agg.items():
    print(f"{k:28s} worst Ms over guard legs {a[0]:.3f} {a[1]} max#>1.5 {a[2]} Ms_leg {a[3]:.2f}")
