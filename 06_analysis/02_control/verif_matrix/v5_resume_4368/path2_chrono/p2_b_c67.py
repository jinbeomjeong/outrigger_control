"""C-6 / C-7a / C-7b: G1 open-loop rows (rules 5.3, 7.5, 9.1; rev2 R2-4; rev3 R3-G11). Record rows.

Path 2 = the existing `openloop_compare.py` `analyse` definition, executed as written (its function
and constant definitions are taken from the file by `ast`; the module-level driver with its fixed
run list is not executed), plus the rev2 R2-4 speed ratios computed separately:
  r_vu: per leg median of v/u over flow_series 1 ms rows with 8.5 s < t <= run end and u >= 0.1 v_max
  r_v : per leg (s_motor(last) - s_motor(first)) / (t_last - t_first) / v_max over 10 s <= t <= 20 s
Keys of `analyse` that copy the row judge's stored block (`stored_*`) are dropped from the output.
Spec 11047: pre-lift-off min F_a < F_min -> FLAG (record).
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import numpy as np

import p2_rules as R

CRITERIA = ("C-6", "C-7", "C-7a", "C-7b")
OPENLOOP_REL = "06_analysis/03_hydraulic/coupled/v5/paper_runs/scripts/openloop_compare.py"
KEEP_DEFS = ("first_run", "plane_fit", "analyse")
KEEP_CONSTS = ("F_MIN", "T_LIFT", "PAD_XY")
EXPECTED = {"C-6": 1, "C-7a": 1, "C-7b": 1}


def _repo():
    here = Path(__file__).resolve().parent
    for p in [here] + list(here.parents):
        if (p / R.REPO_MARKER).exists():
            return p
    raise RuntimeError("repo not found")


def load_analyse():
    src_p = _repo() / OPENLOOP_REL
    src = src_p.read_text(encoding="utf-8")
    tree = ast.parse(src)
    body = [n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))
            or (isinstance(n, ast.FunctionDef) and n.name in KEEP_DEFS)
            or (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in KEEP_CONSTS
                                                  for t in n.targets))]
    ns: dict = {}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(src_p), "exec"), ns)  # noqa: S102
    return ns["analyse"], hashlib.sha256(src_p.read_bytes()).hexdigest()


class OpenLoopRow:
    def __init__(self, folder, engine, argv):
        self.folder = Path(folder)
        self.engine = engine
        self.argv = list(argv)
        self.case = self.folder.name
        self.notes = []


def load(folder, engine, argv):
    return OpenLoopRow(folder, engine, argv)


def kind_of(case):
    cid = str(case.get("criteria_id") or (case.get("r4368") or {}).get("criteria_id") or "")
    name = str(case.get("case") or "")
    if cid == "C-6" or name.endswith("_prop"):
        return "C-6"
    if "_V0_" in name or name.endswith("V0_FB"):
        return "C-7b"
    return "C-7a"


def speed_ratios(folder: Path, v_max: float) -> dict:
    out = {"clause": "rev2 R2-4", "v_max_m_s": v_max}
    fp = folder / "flow_series.npz"
    if fp.exists():
        z = np.load(fp)
        cols = [str(c) for c in z["columns"]]
        rows = z["rows"]
        t = rows[:, cols.index("t")]
        t_end = float(t[-1])
        r = []
        for leg in R.LEGS:
            u = rows[:, cols.index(f"u_{leg}")]
            v = rows[:, cols.index(f"v_{leg}")]
            m = (t > 8.5 + R.CMP_TOL) & (t <= t_end + R.CMP_TOL) & (u >= 0.1 * v_max - R.CMP_TOL)
            r.append(float(np.median(v[m] / u[m])) if m.any() else None)
        out["r_vu"] = r
        out["r_vu_window_s"] = [8.5, t_end]
    else:
        out["r_vu"] = None
        out["r_vu_reason"] = "no flow_series.npz (V0: not applicable, rules 5.3)"
    s = np.load(folder / "series.npz")
    t = s["t_s"]
    sm = s["s_motor_m"]
    m = (t >= 10.0 - R.CMP_TOL) & (t <= 20.0 + R.CMP_TOL)
    idx = np.nonzero(m)[0]
    if idx.size >= 2:
        i0, i1 = int(idx[0]), int(idx[-1])
        out["r_v"] = ((sm[i1] - sm[i0]) / (t[i1] - t[i0]) / v_max).tolist()
        out["r_v_window_s"] = [float(t[i0]), float(t[i1])]
    else:
        out["r_v"] = None
        out["r_v_reason"] = "run shorter than 20 s"
    return out


def judge_row(row, case, kind, params):
    analyse, sha = load_analyse()
    items = {}
    try:
        res, _ = analyse(row.folder)
        dropped = sorted(k for k in res if k.startswith("stored_"))
        for k in dropped:
            res.pop(k)
        items["analyse"] = {"clause": "rules 5.3 / 9.1: openloop_compare.analyse", "verdict": "record",
                            "script_sha256": sha, "dropped_keys": dropped, "values": res}
        pre = res.get("pre_liftoff_min_F_kN") or []
        low = [i for i, v in enumerate(pre) if v is not None and R.lt(v * 1e3, params["F_min_N"])]
        items["spec_11047"] = {"clause": "spec 11047: open-loop pre-lift-off min F_a < F_min -> FLAG",
                               "verdict": "record", "flag": bool(low),
                               "legs": [R.LEGS[i] for i in low]}
    except Exception as e:  # noqa: BLE001
        items["analyse"] = {"verdict": "indeterminate", "reason": f"{type(e).__name__}: {e}"[:300]}
    items["speed_ratios"] = dict(speed_ratios(row.folder, params["v_max_m_s"]), verdict="record")
    keys = list(items)
    return items, keys, [], True


def bundle_status(rows):
    import p2_kinds as K
    kinds = [r["kind"] for r in rows]
    stops = [f"S-15: {k} rows {kinds.count(k)} != {n}" for k, n in EXPECTED.items() if kinds.count(k) != n]
    return K.bundle_status(rows, None, record_bundle=True, extra_stops=stops)
