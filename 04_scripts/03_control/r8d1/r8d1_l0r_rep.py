import json
d = json.load(open("r8d1_l0r.json"))
rows = d["rows"]
names = list(d["summary"])
for ks in ("1.3", "1.75", "2.2"):
    sub = [(t, r) for t, r in rows if t.endswith(f"_k{ks}-{ks}-{ks}-{ks}")]
    f1 = [r["f"][0] for _, r in sub]
    print(f"k_scale {ks}: n {len(sub)}, f1 {min(f1):.2f}-{max(f1):.2f} Hz")
    agg = {}
    for n in names:
        base = n[:-1] if n[-2] == "G" else n
        w = max(sub, key=lambda x: x[1][n])
        v = (w[1][n], w[0], sum(r[n] > 1.5 for _, r in sub))
        if base not in agg or v[0] > agg[base][0]:
            agg[base] = v
    for k, v in agg.items():
        print(f"   {k:16s} {v[0]:.3f} n>1.5 {v[2]:2d} ({v[1]})")
