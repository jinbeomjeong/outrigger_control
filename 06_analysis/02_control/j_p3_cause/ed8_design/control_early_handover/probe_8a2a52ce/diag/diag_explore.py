"""Diagnosis step 1 (record): hash identity with p89 main lines, T4h keys, phase timeline after
the event, twist-work bins, re-approach and A(i) / A(i)-b episodes. Output diag_explore_out.txt.

Usage: conda run -n dynamics-dev python -I -B diag_explore.py
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
MAIN = HERE.parent / "raw" / "runs.jsonl"
U10 = HERE.parents[2] / "dynamics_u832_o00" / "rerun_raw" / "runs.jsonl"


def jk(job):
    return json.dumps({k: v for k, v in job.items() if k not in ("mask", "t4h_dir")},
                      sort_keys=True)


main = {jk(json.loads(x)["job"]): json.loads(x) for x in MAIN.read_text("utf-8").splitlines()}
u10 = {jk(json.loads(x)["job"]): json.loads(x) for x in U10.read_text("utf-8").splitlines()}
out = []
for line in (RAW / "runs.jsonl").read_text("utf-8").splitlines():
    r = json.loads(line)
    key = jk(r["job"])
    ref = main.get(key) or u10.get(key)
    stem = r["diag"]["stem"]
    eo = r.get("event_output") or {}
    t_ev = r["t_event_s"]
    out.append(f"===== {stem}  sha {r['commands_sha256'][:12]}  ref {None if ref is None else ref['commands_sha256'][:12]}"
               f"  equal {None if ref is None else ref['commands_sha256'] == r['commands_sha256']}")
    out.append(f"  t_event {t_ev} final {r['final_phase']} gates_failed "
               f"{[g for g, ok in (eo.get('gates') or {}).items() if not ok]} PU {eo.get('pair_union_s')} "
               f"tRb {eo.get('t_ready_back_s')} sign_changes {eo.get('sign_changes')} "
               f"n_late {eo.get('n_late_starts')} starts {eo.get('reapproach_starts')}")
    jpath = RAW / "logs" / f"{stem}_judge.json"
    if jpath.exists():
        j = json.loads(jpath.read_text("utf-8"))
        out.append(f"  twist {j['twist']}")
        ph = j["phases"]
        seg, last = [], None
        for t, p in ph:
            if p != last:
                seg.append((round(t - t_ev, 2), p))
                last = p
        out.append(f"  phases after event (rel s): {seg}")
    t4 = RAW / "t4h" / f"{stem}.npz"
    if t4.exists():
        z = np.load(t4, allow_pickle=False)
        out.append(f"  t4h keys: {sorted(z.files)}")
    lsb = RAW / "logs" / f"{stem}_lsb.json"
    if lsb.exists():
        L = json.loads(lsb.read_text("utf-8"))
        rel = lambda t: None if t is None else round(t - t_ev, 2)  # noqa: E731
        out.append(f"  A(i) episodes: {[(e['kind'], rel(e.get('t') or e.get('t_last')), e.get('leg'), e.get('reason') or e.get('sign')) for e in L['a1'] if (e.get('t') or e.get('t_last') or 0) >= t_ev - 1]}")
        out.append(f"  A_ib episodes: {[(e['kind'], rel(e.get('t') or e.get('t_last')), e.get('leg'), e.get('reason') or e.get('sign')) for e in L['ib'] if (e.get('t') or e.get('t_last') or 0) >= t_ev - 1]}")
        ev = [(rel(f['t']), f['events']) for f in L['floors'] if f['events'] and f['t'] >= t_ev - 1]
        out.append(f"  lsb events: {ev}")
    p = json.loads((RAW / "logs" / f"{stem}_p89.json").read_text("utf-8"))
    out.append(f"  reapp ends: {[(round(e['t'] - t_ev, 3), e['leg'], e['outcome']) for e in p['ends'] if e['t'] >= t_ev - 1e-9]}")
    out.append(f"  h3: {[(round(h['t'] - t_ev, 3), h['leg']) for h in p['h3']]}")
    out.append(f"  event_names {r.get('event_names')}")
text = "\n".join(out)
(HERE / "diag_explore_out.txt").write_text(text, "utf-8")
print(text.encode("ascii", "replace").decode())
