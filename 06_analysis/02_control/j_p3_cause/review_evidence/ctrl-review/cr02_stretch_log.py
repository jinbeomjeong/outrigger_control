"""Print rev 5 stretch_log rows and head history of one leg (read only).

Usage: python -I -B cr02_stretch_log.py <jsonl> <t4h_dir> <setting> <leg> <t0> <t1>
"""

import json
import sys
from pathlib import Path

import numpy as np

LEGS = ("FL", "FR", "RL", "RR")


def find(obj, key, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                yield path + "/" + k, v
            yield from find(v, key, path + "/" + k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from find(v, key, f"{path}[{i}]")


def main() -> None:
    jsonl, t4h_dir, setting, leg_name = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], sys.argv[4]
    t0, t1 = float(sys.argv[5]), float(sys.argv[6])
    leg = LEGS.index(leg_name)
    for line in map(json.loads, jsonl.read_text(encoding="utf-8").splitlines()):
        if line["job"]["setting"] != setting:
            continue
        for where, rows in find(line, "stretch_log"):
            if not isinstance(rows, list):
                continue
            print("stretch_log at", where, "rows", len(rows))
            for row in rows:
                if row.get("leg") == leg_name and (row.get("t_close_s") or 1e9) >= t0 - 10 \
                        and row.get("t_open_s", 0) <= t1:
                    print("  ", json.dumps(row))
        with np.load(t4h_dir / line["t4h_file"], allow_pickle=False) as data:
            t = data["jp3_t_s"]
            names = [str(n) for n in data["jp3_class_names"]]
            sel = np.flatnonzero((t >= t0) & (t <= t1))
            ts = data["t_s"]
            head = data["head_pressure_Pa"][:, leg] / 1e5
            for k in sel:
                j = int(np.argmin(np.abs(ts - t[k])))
                print(f"  t={t[k]:6.2f} {names[data['jp3_class'][k, leg]]:9s} "
                      f"u={data['jp3_u_m_s'][k, leg] * 1e3:8.4f} head={head[j]:7.2f} "
                      f"model={data['jp3_model_bound_Pa'][k, leg] / 1e5:7.2f} "
                      f"used={data['jp3_used_bound_Pa'][k, leg] / 1e5:7.2f} "
                      f"p_tr={data['jp3_p_tr_Pa'][k, leg] / 1e5:7.2f} "
                      f"state={int(data['jp3_plant_state'][k, leg])}")


if __name__ == "__main__":
    main()
