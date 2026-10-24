"""S7 control ③ preparation: R8 C2 closed loop on L2b-NSC, judgement and L1 / L2b pair rows.

``00_docs/01_dynamics/dynamics_model.md`` 5.23.4 (control ③: L2b judges, L1 bundle-C pairs give
the D8 minimum-force difference; a pair difference above the open-loop bound 1.84 kN is looked
at separately), 5.22.3 (NSC read-out rule). Inputs are the case directories of
``04_scripts/02_chrono/run_S7C.py`` (same files as a bundle-C case: ``record/``, ``pads.npz``,
``result.json``, ``r8_series.npz``; ``result.json / settings / s7c`` names the engine and the
pair).

Rows (``passed`` True / False judged, None = record):

* every case: the bundle-C rows of :func:`outrigger_sim.verify.s6_bundle_c.judge` (S6 items,
  D8 / REANCHOR / C-8, warnings), each carrying ``engine`` (``"L2b_NSC"`` / ``"L1R"``);
* NSC read-out (L2b cases, judged): the pad record reads loads from the force-law output and
  the contact force only as a centred mean of at least 20 ms (``pads.npz`` ``meta_json``,
  ``chrono/l2b_pad_record``);
* READY hold (smoke case, judged): first READY reached and held (no phase change) for at least
  :data:`READY_HOLD_S` until the run end, attitude error of the last 5 s + mount <= 0.2 deg;
* pair rows (``kind`` "pair", record): ``L2b - L1`` of the D8 minimum true cylinder force after
  the crawler lift-off as the 1 s centred mean (slow component, C-R18 / spec rev. 37 193.2,
  :func:`slow_force_metrics`) and raw 1 ms, the raw minimum from lift-off + 5 s to READY, the
  oscillation half-amplitude 0-3 s after lift-off per leg, the minimum outside / inside
  REANCHOR, READY - TOUCH time, the final twist load and the last-5 s attitude error; only the
  slow-component D8 row carries ``pair_flag`` when ``|diff| > PAIR_FLAG_N`` (5.23.4, U-S7-3;
  never a failure). The L1 value comes from the L1 twin of the same batch, else from the
  ``pair_batch`` (argument or ``s7c.pair_batch``; L2b-only re-runs), else from an earlier
  bundle-C batch (``external_l1``) named in the case settings;
* through :func:`outrigger_sim.verify.s6_bundle_c.judge`: C-R16 (A1 rejection of an L2b case
  judged with the identity map) and C-R19 (sensitivity-condition D8 / REANCHOR rows reported).

Units SI internally; kN / deg / s in the rows.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

PAIR_FLAG_N = 1840.0
"""5.23.3 / 5.23.4: open-loop upper bound of the L1 / L2b model difference (RR roll+ 1.84 kN)."""
READY_HOLD_S = 60.0
"""Smoke case: READY held at least this long (S7 control ③ preparation, coordinator 2026-10-24)."""
NSC_CONTACT_WINDOW_MIN_S = 0.020
"""5.22.3: contact force only as a >= 20 ms window mean."""
MOUNT_SHARE_DEG = 0.02
ATT_TOL_DEG = 0.2

SLOW_WINDOW_S = 1.0
"""C-R18 (spec rev. 37 193.2, ASSUMPTION 196.4): slow component = centred moving mean of this
length of the 1 ms true cylinder force (two periods of the ~2 Hz first rocking mode)."""
OSC_WINDOW_S = (0.0, 3.0)
"""C-R18: window after the crawler lift-off of the oscillation half-amplitude record."""
LATE_WINDOW_START_S = 5.0
"""C-R18: the late window runs from lift-off + this to the first READY."""
LEGS = ("FL", "FR", "RL", "RR")

PAIR_KEYS: tuple[tuple[str, str, float | None], ...] = (
    ("min_cyl_slow_after_liftoff_kN",
     "D8 min true cylinder force after crawler lift-off, 1 s centred mean [kN]",
     PAIR_FLAG_N / 1e3),
    ("min_cyl_after_liftoff_kN",
     "D8 min true cylinder force after crawler lift-off, raw 1 ms [kN]", None),
    ("min_cyl_late_kN", "min true cylinder force lift-off + 5 s .. READY, raw 1 ms [kN]", None),
    ("min_cyl_excl_reanchor_kN", "min true cylinder force outside REANCHOR [kN]", None),
    ("min_cyl_reanchor_kN", "min true cylinder force inside REANCHOR [kN]", None),
    ("t_ready_minus_touch_s", "READY - TOUCH end [s]", None),
    ("final_twist_kN", "final twist load n^T F (last 5 s) [kN]", None),
    ("att_err_last5_maxabs_deg", "attitude error last 5 s max [deg]", None),
)


def _row(item: str, case: str, value: Any, limit: Any, passed: bool | None, note: str = "",
         kind: str = "judged") -> dict[str, Any]:
    return {"item": item, "case": case, "value": value, "limit": limit, "passed": passed,
            "note": note, "kind": kind, "source": "s7_control"}


def pair_rows(l2b: Mapping[str, Any], l1: Mapping[str, Any] | None, *, l1_source: str
              ) -> list[dict[str, Any]]:
    """``L2b - L1`` rows of one pair (module docstring). ``l1`` None = no L1 value."""
    cid = l2b["case"]
    out = []
    for key, what, flag_kN in PAIR_KEYS:
        a = l2b.get(key)
        b = None if l1 is None else l1.get(key)
        if a is None or b is None:
            out.append(_row(f"pair L2b - L1: {what}", cid, None, None, None,
                            f"L2b {a}, L1 {b} ({l1_source})", kind="pair"))
            continue
        diff = float(a) - float(b)
        row = _row(f"pair L2b - L1: {what}", cid, diff,
                   None if flag_kN is None else f"|diff| <= {flag_kN:g} (flag only)", None,
                   f"L2b {float(a):.3f}, L1 {float(b):.3f} ({l1_source})", kind="pair")
        if flag_kN is not None:
            row["pair_flag"] = bool(abs(diff) > flag_kN)
            if row["pair_flag"]:
                row["note"] += ("; FLAG: slow-component difference above the open-loop bound, "
                                "look at guard overshoot / S_ii / H4 (dynamics 5.23.4)")
        out.append(row)
    a_osc = l2b.get("osc_half_amp_kN")
    b_osc = None if l1 is None else l1.get("osc_half_amp_kN")
    lo, hi = OSC_WINDOW_S
    for j, leg in enumerate(LEGS):
        what = (f"oscillation half-amplitude {lo:g}-{hi:g} s after lift-off (1 ms - 1 s centred "
                f"mean), {leg} [kN]")
        a = None if a_osc is None else a_osc[j]
        b = None if b_osc is None else b_osc[j]
        if a is None or b is None:
            out.append(_row(f"pair L2b - L1: {what}", cid, None, None, None,
                            f"L2b {a}, L1 {b} ({l1_source})", kind="pair"))
            continue
        out.append(_row(f"pair L2b - L1: {what}", cid, float(a) - float(b), None, None,
                        f"L2b {float(a):.3f}, L1 {float(b):.3f}, ratio "
                        f"{float(a) / float(b) if float(b) else float('nan'):.2f} ({l1_source})",
                        kind="pair"))
    return out


def centred_mean(x: np.ndarray, n: int) -> np.ndarray:
    """Centred moving mean of ``n`` (made odd) samples along axis 0; the window is truncated at
    the ends (mean of the samples that exist)."""
    x = np.asarray(x, dtype=float)
    n = max(1, int(n) | 1)
    h = n // 2
    c = np.concatenate([np.zeros((1, *x.shape[1:])), np.cumsum(x, axis=0)], axis=0)
    k = np.arange(x.shape[0])
    lo = np.clip(k - h, 0, x.shape[0])
    hi = np.clip(k + h + 1, 0, x.shape[0])
    cnt = (hi - lo).reshape((-1,) + (1,) * (x.ndim - 1))
    return (c[hi] - c[lo]) / cnt


def slow_force_metrics(t_rel: np.ndarray, force_N: np.ndarray, liftoff_s: float | None,
                       ready_s: float | None, *, window_s: float = SLOW_WINDOW_S
                       ) -> dict[str, Any]:
    """C-R18 (spec rev. 37 193.2): split the 1 ms true cylinder force ``force_N`` (n x 4, N) at
    ``t_rel`` (s after the controller start) into the ``window_s`` centred mean and the rest.

    Returns (kN, s): ``min_cyl_slow_after_liftoff_kN`` (minimum of the slow component over all
    legs from lift-off to the end) with leg and time, ``osc_half_amp_kN`` per leg = (max - min) / 2
    of force minus slow in :data:`OSC_WINDOW_S` after lift-off, ``min_cyl_late_kN`` = raw minimum
    from lift-off + :data:`LATE_WINDOW_START_S` to the first READY. Empty dict without lift-off."""
    if liftoff_s is None:
        return {}
    t = np.asarray(t_rel, dtype=float)
    f = np.asarray(force_N, dtype=float)
    dt = float(np.median(np.diff(t))) if t.size > 1 else window_s
    n = int(round(window_s / dt)) | 1
    slow = centred_mean(f, n)
    after = t >= liftoff_s
    out: dict[str, Any] = {"slow_window_s": window_s, "slow_window_samples": n,
                           "slow_sample_s": dt}
    if not after.any():
        return out
    sa = slow[after]
    k = np.unravel_index(int(np.argmin(sa)), sa.shape)
    out["min_cyl_slow_after_liftoff_kN"] = float(sa[k]) / 1e3
    out["min_cyl_slow_leg"] = LEGS[k[1]]
    out["min_cyl_slow_t_s"] = float(t[after][k[0]])
    w = (t >= liftoff_s + OSC_WINDOW_S[0]) & (t <= liftoff_s + OSC_WINDOW_S[1])
    if w.any():
        osc = f[w] - slow[w]
        out["osc_half_amp_kN"] = ((osc.max(axis=0) - osc.min(axis=0)) / 2e3).tolist()
    if ready_s is not None:
        late = (t >= liftoff_s + LATE_WINDOW_START_S) & (t <= ready_s)
        if late.any():
            out["min_cyl_late_kN"] = float(f[late].min()) / 1e3
    return out


def slow_force_metrics_case(case: Mapping[str, Any], m: Mapping[str, Any]) -> dict[str, Any]:
    """:func:`slow_force_metrics` on a loaded case (``pads.F_cyl_min_interval``) and its
    ``times_s`` (case metrics)."""
    pads = case.get("pads")
    tm = m.get("times_s") or {}
    if pads is None or tm.get("liftoff") is None:
        return {}
    t_rel = np.asarray(pads["t"], dtype=float) - float(tm["t0"])
    return slow_force_metrics(t_rel, pads["F_cyl_min_interval"], tm["liftoff"], tm.get("ready"))


def ready_hold_metrics(phases: Sequence[Sequence[Any]], end_s: float) -> dict[str, Any]:
    """First READY time, the time it was held without a phase change until ``end_s`` and the
    phases after it (``phases`` = ``[(t_rel, name), ...]``, times relative to the start)."""
    ph = [(float(t), str(p)) for t, p in phases]
    first = next((i for i, (_t, p) in enumerate(ph) if p == "ready"), None)
    if first is None:
        return {"first_ready_s": None, "held_s": 0.0, "left_ready": None}
    later = [p for _t, p in ph[first + 1:]]
    left = any(p != "ready" for p in later)
    t_ready = ph[first][0]
    if left:
        t_leave = next(t for t, p in ph[first + 1:] if p != "ready")
        held = t_leave - t_ready
    else:
        held = float(end_s) - t_ready
    return {"first_ready_s": t_ready, "held_s": held, "left_ready": left,
            "phases_after_ready": later}


def ready_hold_rows(m: Mapping[str, Any], hold_s: float = READY_HOLD_S) -> list[dict[str, Any]]:
    cid = m["case"]
    rh = ready_hold_metrics(m["phases"], m["times_s"]["end"])
    rows = [_row(f"smoke READY held >= {hold_s:g} s", cid, rh["held_s"], hold_s,
                 rh["first_ready_s"] is not None and rh["held_s"] >= hold_s,
                 f"first READY {rh['first_ready_s']} s, left READY {rh['left_ready']}")]
    att = m.get("att_err_last5_maxabs_deg")
    rows.append(_row("smoke attitude last 5 s + mount <= 0.2 deg", cid,
                     None if att is None else att + MOUNT_SHARE_DEG, ATT_TOL_DEG,
                     None if att is None else att + MOUNT_SHARE_DEG <= ATT_TOL_DEG))
    return rows


def nsc_readout_row(cid: str, pads_meta: Mapping[str, Any] | None) -> dict[str, Any]:
    """5.22.3 rule on the pad record of an L2b case."""
    if pads_meta is None:
        return _row("5.22.3 NSC read-out (contact >= 20 ms mean, loads = law output)", cid,
                    None, NSC_CONTACT_WINDOW_MIN_S, False, "pads.npz meta_json missing")
    w = float(pads_meta.get("contact_window_s", 0.0))
    ok = w >= NSC_CONTACT_WINDOW_MIN_S - 1e-12 and pads_meta.get("format") == "l2b_pad_record_v1"
    return _row("5.22.3 NSC read-out (contact >= 20 ms mean, loads = law output)", cid, w,
                NSC_CONTACT_WINDOW_MIN_S, ok, str(pads_meta.get("rule", "")))


def _pads_meta(case_dir: Path) -> dict[str, Any] | None:
    p = case_dir / "pads.npz"
    if not p.exists():
        return None
    with np.load(p, allow_pickle=False) as data:
        if "meta_json" not in data.files:
            return None
        return json.loads(str(data["meta_json"]))


def external_l1_metrics(root: Path, batch: str, case_id: str) -> dict[str, Any] | None:
    """Metrics of ``case_id`` from an earlier bundle-C batch (its ``verify_S6C.json``)."""
    path = root / batch / "verify_S6C.json"
    if not path.exists():
        return None
    doc = json.loads(path.read_text(encoding="utf-8"))
    return next((m for m in doc.get("metrics") or [] if m.get("case") == case_id), None)


def _load_case_metrics(d: Path):
    """(case, metrics, probes) of one case directory: bundle-C metrics + :func:`slow_force_
    metrics_case` (C-R18)."""
    from outrigger_sim.params import load_params
    from outrigger_sim.verify import s6_bundle_c as bc
    from outrigger_sim.verify import s6_control as s6

    case = s6.load_case(d)
    s = case["result"]["settings"]
    over = (s.get("bundle_c") or {}).get("param_overrides") or {}
    params = load_params(level=s["level"], overrides=over or None)
    m = bc.bundle_c_metrics(case, params)
    m["rerun_group"] = None
    m.update(slow_force_metrics_case(case, m))
    pr = s6.probe_metrics(case)
    bc.probe_truth_ringing(case, pr)
    return case, m, pr


def pair_batch_metrics(pair_batch: Path, case_id: str) -> dict[str, Any] | None:
    """Metrics of the L1 twin ``case_id`` from an earlier ``run_S7C.py`` batch directory
    (recomputed from its case files, so the C-R18 slow component is present)."""
    d = Path(pair_batch) / case_id
    if not (d / "result.json").exists():
        return None
    return _load_case_metrics(d)[1]


def judge_batch(batch_dir: Path, out_path: Path | None = None, *,
                root: Path | None = None, pair_batch: Path | None = None) -> Path:
    """Judge a ``run_S7C.py`` batch; writes ``verify_S7C.json`` (module docstring).

    ``pair_batch``: batch directory holding the L1 twins when they are not in ``batch_dir``
    (a re-run of L2b cases only, e.g. ``--set ctrl3_rerun``); the case setting
    ``s7c.pair_batch`` is used when the argument is None. Relative paths are taken from the
    project root."""
    from outrigger_sim.verify import s6_bundle_c as bc

    root = root or bc.PROJECT_ROOT
    metrics, probes, info = [], {}, {}
    for d in sorted(p for p in Path(batch_dir).iterdir() if (p / "result.json").exists()):
        case, m, pr = _load_case_metrics(d)
        s = case["result"]["settings"]
        metrics.append(m)
        probes[case["result"]["case"]] = pr
        info[m["case"]] = {"s7c": s.get("s7c") or {}, "dir": d}
    rows = bc.judge(metrics, probes, None)
    by_id = {m["case"]: m for m in metrics}
    for row in rows:
        row["engine"] = (info.get(row.get("case"), {}).get("s7c") or {}).get("engine")
    flags = []
    pair_sources: dict[str, str] = {}
    pair_cache: dict[tuple[str, str], dict[str, Any] | None] = {}
    for cid, m in list(by_id.items()):
        s7c = info[cid]["s7c"]
        engine = s7c.get("engine")
        if engine == "L2b_NSC":
            rows.append({**nsc_readout_row(cid, _pads_meta(info[cid]["dir"])), "engine": engine})
        if s7c.get("smoke"):
            rows.extend({**r, "engine": engine} for r in ready_hold_rows(m))
        if engine != "L2b_NSC":
            continue
        twin = s7c.get("pair_l1")
        l1 = by_id.get(twin) if twin else None
        source = f"same batch {twin}"
        pb = pair_batch if pair_batch is not None else s7c.get("pair_batch")
        if l1 is None and twin and pb:
            pb_path = Path(pb) if Path(pb).is_absolute() else Path(root) / pb
            key = (str(pb_path), twin)
            if key not in pair_cache:
                pair_cache[key] = pair_batch_metrics(pb_path, twin)
            l1 = pair_cache[key]
            source = f"pair batch {pb} / {twin}"
        if l1 is None and s7c.get("external_l1"):
            batch, ext_id = s7c["external_l1"]
            l1 = external_l1_metrics(root, batch, ext_id)
            source = f"{batch} / {ext_id}"
        if l1 is None and not twin and not s7c.get("external_l1"):
            continue
        pair_sources[cid] = source if l1 is not None else f"none ({source})"
        for r in pair_rows(m, l1, l1_source=source):
            r["engine"] = engine
            rows.append(r)
            if r.get("pair_flag"):
                flags.append(cid)
    n_fail = sum(1 for r in rows if r["passed"] is False)
    out = out_path or Path(batch_dir) / "verify_S7C.json"
    doc = {"meta": {"batch": str(batch_dir), "module": __name__, "rows": len(rows),
                    "failed": n_fail, "pair_flags": flags, "pair_flag_N": PAIR_FLAG_N,
                    "pair_flag_basis": f"{SLOW_WINDOW_S:g} s centred mean of the 1 ms true "
                                       "cylinder force (C-R18, spec rev. 37 193)",
                    "pair_batch": None if pair_batch is None else str(pair_batch),
                    "pair_sources": pair_sources,
                    "ready_hold_s": READY_HOLD_S,
                    "failed_by_engine": {e: sum(1 for r in rows if r["passed"] is False
                                                and r.get("engine") == e)
                                         for e in ("L2b_NSC", "L1R")}},
           "rows": rows, "metrics": metrics}
    out.write_text(json.dumps(doc, indent=1, default=bc._json_default, ensure_ascii=False),
                   encoding="utf-8")
    return out


__all__ = ["LATE_WINDOW_START_S", "OSC_WINDOW_S", "PAIR_FLAG_N", "PAIR_KEYS", "READY_HOLD_S",
           "SLOW_WINDOW_S", "centred_mean", "external_l1_metrics", "judge_batch",
           "nsc_readout_row", "pair_batch_metrics", "pair_rows", "ready_hold_metrics",
           "ready_hold_rows", "slow_force_metrics", "slow_force_metrics_case"]
