"""Follow-up (a) bit comparison (prereg 1.2) and identity fields of both rows (prereg 1.2-1, 2.5, rev1 R1-4).

File SHA-256 of series.npz vs the base row, then per common key dtype/shape/bytes; result.json identity fields.
Output JSON to argv[1].
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

S9 = Path(r"C:\workspace\outrigger_control\07_results\S9")
BASE = S9 / "batch_V5-OPENLOOP-V0_20261108_123517/P3a_J1_B_V0"
F = S9 / "batch_V5-OPENLOOP-RFU_20261109_0100"
ROWS = {"rep_a": F / "P3a_J1_B_V0_rep", "R1490k": F / "P3a_J1_B_V0_R1490k"}
EXPECT = {"params_sha256": "d06a97dddf71553995b89254b5e1161cd85af43bc87a1c1658945cada64d8859",
          "scm_run_sha256": "de20851ad27e121b9a30262685bf1af94be53a8419bbcbc7535ebed30310c07b",
          "pad_variants_sha256": "00cf734bddc2877be1365da2cf995689b38ccb2736156ba6d307823cfab443ee",
          "table_sha256": "b21f0fc11b8883aa0402c5e4e6c1d97b846460f3a50417a34df8980357d739a3"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def find(d, key):
    """All values of ``key`` anywhere in nested dict/list ``d``."""
    out = []
    if isinstance(d, dict):
        for k, v in d.items():
            if k == key:
                out.append(v)
            out += find(v, key)
    elif isinstance(d, list):
        for v in d:
            out += find(v, key)
    return out


out = {"base": {"series_sha256": sha(BASE / "series.npz"), "result_sha256": sha(BASE / "result.json")}}
with np.load(BASE / "series.npz") as zb:
    base = {k: zb[k] for k in zb.files}
for name, p in ROWS.items():
    res = json.loads((p / "result.json").read_text("utf-8"))
    o = {"series_sha256": sha(p / "series.npz"), "result_sha256": sha(p / "result.json")}
    o["file_equal_base"] = o["series_sha256"] == out["base"]["series_sha256"]
    with np.load(p / "series.npz") as z:
        keys = set(z.files)
        common = sorted(keys & set(base))
        diff = [k for k in common if not (z[k].dtype == base[k].dtype and z[k].shape == base[k].shape
                                          and z[k].tobytes() == base[k].tobytes())]
    o.update(n_keys=len(keys), n_common=len(common), only_row=sorted(keys - set(base)),
             only_base=sorted(set(base) - keys), keys_differ=diff)
    meta = res.get("meta", {})
    o["identity"] = {k: (find(res, k)[:1] or [None])[0] for k in EXPECT}
    o["identity_ok"] = {k: o["identity"][k] == v for k, v in EXPECT.items()}
    o["damping_R"] = sorted(set(float(v) for v in find(res, "damping_R")))
    o["overrides"] = find(res, "overrides")[:2]
    o["threads"] = res.get("args", {}).get("threads")
    o["placement"] = {k: res.get("placement", {}).get(k) for k in ("mode", "requested")}
    o["hull_hook_key"] = "hull_hook" in res
    out[name] = o
Path(sys.argv[1]).write_text(json.dumps(out, indent=1, default=str), "utf-8")
for n, o in out.items():
    print(n, json.dumps({k: v for k, v in o.items() if k not in ("only_row", "only_base")}, default=str))
