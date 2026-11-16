"""Record-only predictions P-7, P-11, P-11b computed by the judgement author from the raw records (decision 114 (9)).

P-7 (original 10, rev3 Q-S4 not applicable: C-3 Chrono): C-3 rows vs stored rows, controller command bits equal when
    --threads and P placement are the same. Compared: controller_commands.npz arrays (t_s, issued_u_m_s) byte equality,
    plus num_threads_chrono and placement of both result.json.
P-11 / P-11b (rev2 R2-4 r_v): per leg, 10 s <= t <= 20 s (absolute simulation time), (s_last - s_first) / (t_last - t_first)
    / v_max, v_max = YAML actuator.max_speed_m_s. Predicted 0.8769.
Usage: python -I -B _p7_p11.py <repo> <out.json>
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import yaml

repo = Path(sys.argv[1])
out = {}
S9 = repo / "07_results/S9"
C3 = S9 / "batch_V5-RESUME-K1-C3_20261114_010541"
STORED = S9 / "batch_D1-CHRONO_20261108_131710"
C67 = S9 / "batch_V5-RESUME-K1-C6C7_20261113_215638"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def arrays(p):
    with np.load(p, allow_pickle=False) as z:
        return {k: np.array(z[k]) for k in z.files}


p7 = {}
for row in ("D1S_G1_B_middle_Fs4_spJ1FL", "D1S_G1_B_bottom_Fs4_spJ1FL"):
    a, b = C3 / row, STORED / row
    ca, cb = arrays(a / "controller_commands.npz"), arrays(b / "controller_commands.npz")
    same_names = sorted(ca) == sorted(cb)
    eq = {k: bool(k in cb and ca[k].shape == cb[k].shape and ca[k].dtype == cb[k].dtype
                  and ca[k].tobytes() == cb[k].tobytes()) for k in ca}
    first_diff = None
    if "issued_u_m_s" in ca and "issued_u_m_s" in cb and ca["issued_u_m_s"].shape == cb["issued_u_m_s"].shape:
        d = np.nonzero(np.any(ca["issued_u_m_s"] != cb["issued_u_m_s"], axis=1))[0]
        first_diff = None if d.size == 0 else {"index": int(d[0]), "t_s": float(ca["t_s"][d[0]]), "n_rows": int(d.size)}
    ja, jb = (json.loads((x / "result.json").read_text("utf-8")) for x in (a, b))
    p7[row] = {"new": str(a.relative_to(repo)).replace("\\", "/"), "stored": str(b.relative_to(repo)).replace("\\", "/"),
               "new_npz_sha256": sha(a / "controller_commands.npz"),
               "stored_npz_sha256": sha(b / "controller_commands.npz"),
               "array_names_same": same_names, "arrays_equal": eq, "bits_equal": same_names and all(eq.values()),
               "first_differing_period": first_diff,
               "threads": [ja.get("num_threads_chrono"), jb.get("num_threads_chrono")],
               "placement_new": ja.get("placement"), "placement_stored": jb.get("placement")}
out["P-7"] = p7

params = yaml.safe_load((repo / "02_params/rexome33.yaml").read_text("utf-8"))
vmax = float(params["actuator"]["max_speed_m_s"])
p11 = {"v_max_m_s": vmax}
for row in ("P3a_G1_B_VB_FB", "P3a_G1_B_V0_FB", "P3a_G1_B_VB_prop"):
    d = C67 / row
    z = arrays(d / "series.npz")
    keys = {k: list(v.shape) for k, v in z.items()}
    tkey = next((k for k in ("t_s", "t", "time_s") if k in z), None)
    skey = next((k for k in ("s_motor_m", "s_motor", "stroke_motor_m") if k in z), None)
    rec = {"series_keys": keys, "t_key": tkey, "s_key": skey}
    if tkey and skey:
        t, s = z[tkey], z[skey]
        m = (t >= 10.0 - 1e-12) & (t <= 20.0 + 1e-12)
        idx = np.nonzero(m)[0]
        i0, i1 = int(idx[0]), int(idx[-1])
        rv = (s[i1] - s[i0]) / (t[i1] - t[i0]) / vmax
        rec.update(t_first=float(t[i0]), t_last=float(t[i1]), r_v=[float(x) for x in rv],
                   r_v_minus_0p8769=[float(x - 0.8769) for x in rv])
    p11[row] = rec
out["P-11_P-11b"] = p11
Path(sys.argv[2]).write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
print(json.dumps({"P-7": {r: v["bits_equal"] for r, v in p7.items()},
                  "r_v": {r: v.get("r_v") for r, v in p11.items() if isinstance(v, dict)}}, ensure_ascii=False))
