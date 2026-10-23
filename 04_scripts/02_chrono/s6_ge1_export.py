"""S6 RE3: GE1′ shadow export (C2 R5) and the GE2 promotion pre-checks of control spec rev. 7.

Usage (Chrono-dev python, ``-I -X utf8``)::

    python s6_ge1_export.py <stage2 batch dir> [<previous summary json>] [--override <dir>]...
        [--tag NAME]

``--tag NAME`` (or ``--tag=NAME``, default ``re3``): output ``verify_S6_L1_ge1_<NAME>.json``,
and check (4) compares against the new closed-loop summary
``verify_S6_L1_closed_loop_<NAME>.json`` (make it first with ``s6_stage2_summary.py
... --tag NAME``). The default keeps the RE3 names, so give a new tag for a reprocessing run
or the RE3 files are overwritten.

Spec: ``00_docs/04_control/s6_control_spec.md`` rev. 7 37.3 (Delta definition), 38 (stationary
gate), 42.1-42.2 (the export records the controller's values, no own stationary rule), U39
(promotion criteria 1'-5).

Input per case: ``ge1_series.json`` (``s6_stage2.job_stage2``: every 20 ms ``(t, phase,
sample)``, ``sample`` = the controller's ``support_geometry`` merged with the controller
attributes ``is_geometry_valid`` / ``stationary_gate``), ``record/record.npz``, ``pads.npz``,
``result.json``, ``controller_events.json``.

**R5 names** (:data:`R5_KEYS`, single source ``s6_stage2.GE1_R5_REQUIRED``): the C2 R5 final
names (python-expert 2026-10-22, checked by ``run_S6.py check2``). A case whose samples lack one
of them stops the export with :class:`GE1KeyError` (missing names, the names that are there,
the case); no silent fallback to the R4.1 fields. ``ref_t_s`` in the CSV is case relative (the
controller's ``reference_t_s`` minus the case start).

Per case a CSV ``<case dir>/ge1_timeseries.csv``, one row per control period: time (case
relative, s), C2 phase, ``is_geometry_valid`` (controller gate, spec 38), the gate state fields
(``gate_*``: the R5 ``stationary_gate`` fields is_open, is_phase_allowed, zero_command_duration_s,
rates_quiet_since_s, motion_rms_rad_s_roll/_pitch (1 s deviation RMS, noise-corrected),
mean_rate_rad_s_roll/_pitch, rad/s),
``dD_<leg>_mm`` = d^Delta_i,
``r_mm`` = absolute r (RR component, sign fixed), ``dr_mm`` = Delta r, ``ref_t_s``, the four
applied leg commands (Record ``u_cmd``, m/s), gyro roll / pitch rate (Record
``meas.angular_rate``, deg/s, info), the true pad normal force ``N_<leg>_kN`` and the
**true-path** d^Delta ``dD_true_<leg>_mm``.

True path (dynamics-expert ruling 2026-10-22): pad bottom = floor point
``contact_point_world + (N / k_n) n`` (``pads.npz``: ``contact_point_world`` = ball centre -
r n, a point fixed to the ball; ``N`` true normal force, clipped at 0; ``n`` floor normal;
``k_n`` = YAML ``contact.rigid_floor.L1.kn_per_pad_N_m``, the L1 lumped contact stiffness).
The ball centre moves Delta F / k_n with the load (RE1b: FL 2.48-3.6 mm false height), the
floor point does not. Heights ``h_i = n . p_i``; ``d^Delta_true`` against the controller's
``ref_t_s`` (nearest 1 ms pad sample), the same median-of-the-others rule.

Summary ``06_analysis/01_chrono/16_S6/verify_S6_L1_ge1_<tag>.json``: per case the gate-open
tables (grounded legs = true N > 0), gate-open fraction in DONE / PROBE / READY, sensor - true
difference, GE1 events, and the U39 pre-checks (1') gate samples |d^Delta| <= 2.5 mm, |Delta r|
<= 0.8 mm (every case with the series; event cases before the event), (2') RE1b-F: first RR
d^Delta < -5 mm after the drop (gate-independent and in-gate), other legs < 5 mm (2.5 mm
reported), no GE1 flag after the re-READY, (3) RE1c: RR d^Delta > +5 mm within 1 s after the
forced retraction, (4) G4 judged rows unchanged against a previous summary, (5) L2b: not
available. Pre-checks only; control-expert judges.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "03_src"))
sys.path.insert(0, str(HERE))

from outrigger_sim.control.c2 import (  # noqa: E402
    SHADOW_LIFT_THRESHOLD_M,
    SHADOW_NONPLANARITY_THRESHOLD_M,
    SHADOW_SINK_THRESHOLD_M,
    is_shadow_event,
)

OUT_DIR = ROOT / "06_analysis" / "01_chrono" / "16_S6"
DEFAULT_TAG = "re3"
"""Tag without ``--tag`` (the RE3 names the script used before the option existed)."""


def output_paths(tag: str = DEFAULT_TAG) -> tuple[Path, Path]:
    """(export JSON, closed-loop summary of check (4)) for ``tag``."""
    if (not tag or any(c in tag for c in '\\/:*?"<>|') or tag.strip() != tag
            or not tag.isprintable()):
        raise ValueError(f"bad tag {tag!r}: non-empty file-name part without path characters")
    return (OUT_DIR / f"verify_S6_L1_ge1_{tag}.json",
            OUT_DIR / f"verify_S6_L1_closed_loop_{tag}.json")


OUT = output_paths()[0]
"""Default export path (tag :data:`DEFAULT_TAG`)."""
D_TOL_MM, R_TOL_MM = 2.5, 0.8
D_TRIGGER_MM = 5.0
LEGS = ("FL", "FR", "RL", "RR")
GATE_PHASES = ("done", "probe", "ready")
TOUCH_ONLY = "touch_only"
TOUCH_ONLY_NOTE = "touch_only reference (pressure judge): reported, not judged (U59, spec 55.7)"


def _r5_keys() -> dict[str, str]:
    import s6_stage2

    return dict(s6_stage2.GE1_R5_REQUIRED)


R5_KEYS = _r5_keys()
"""R5 sample names required by the export (``s6_stage2.GE1_R5_REQUIRED``)."""
K_D, K_R, K_DR, K_REF, K_VALID = ("heights_delta_above_others_m", "nonplanarity_m",
                                  "nonplanarity_delta_m", "reference_t_s", "is_geometry_valid")
K_GATE = "stationary_gate"


NO_SAMPLES: list[str] = []
"""Cases whose GE1 series has no sample (listed in the summary meta)."""


class GE1KeyError(KeyError):
    """The GE1 series lacks R5 names (module docstring)."""


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def check_keys(rows: list, case: str) -> bool:
    """Raise :class:`GE1KeyError` unless every sample dict has all of :data:`R5_KEYS`; False
    when there is no sample at all (no floor reference was ever stored, e.g. a rejected start
    that never touches down)."""
    samples = [v for _t, _p, v in rows if isinstance(v, dict)]
    if not samples:
        return False
    for v in samples:
        missing = [k for k in R5_KEYS if k not in v]
        if missing:
            raise GE1KeyError(
                f"{case}: GE1 sample lacks the R5 names {missing} (spec rev. 7 42.1/42.2; "
                f"present: {sorted(v)}). Adjust s6_stage2.GE1_R5_REQUIRED and the K_* names "
                "of s6_ge1_export.py to python-expert's R5 names.")
    return True


def _scalars(prefix: str, value) -> dict:
    out = {}
    if isinstance(value, dict):
        for k, x in value.items():
            if isinstance(x, (bool, int, float)) or x is None:
                out[f"{prefix}{k}"] = x
            elif isinstance(x, (list, tuple)):  # per-axis (roll, pitch) values
                for n, xn in zip(("roll", "pitch"), x, strict=False):
                    out[f"{prefix}{k}_{n}"] = xn
    return out


def _median_rule(h: np.ndarray) -> np.ndarray:
    """d_i = h_i - median of the other three, rows = samples."""
    out = np.empty_like(h)
    for i in range(h.shape[1]):
        out[:, i] = h[:, i] - np.median(np.delete(h, i, axis=1), axis=1)
    return out


def true_pad_heights(pads: dict, kn_N_m: np.ndarray) -> np.ndarray:
    """(n, 4) true pad-bottom height along the floor normal: n . (contact point + N / k_n n)."""
    n = np.asarray(pads["n_world"], dtype=float)  # (n, 3) one floor normal, or (n, 4, 3)
    if n.ndim == 2:
        n = np.repeat(n[:, None, :], 4, axis=1)
    cp = np.asarray(pads["contact_point_world"], dtype=float)
    N = np.clip(np.asarray(pads["N"], dtype=float), 0.0, None)
    floor = cp + (N / kn_N_m)[..., None] * n
    return np.einsum("tij,tij->ti", floor, n)


def true_delta_heights(h_true: np.ndarray, tp_rel: np.ndarray, j: int,
                       ref_rel_s: float | None) -> list:
    """True-path d^Delta of pad sample ``j`` against the reference time ``ref_rel_s`` (case
    relative, like ``tp_rel``; the controller's ``reference_t_s`` is absolute and must have the
    case start subtracted); four None without a reference."""
    if ref_rel_s is None:
        return [None] * 4
    jr = min(int(np.searchsorted(tp_rel, ref_rel_s - 1e-9)), len(tp_rel) - 1)
    return _median_rule((h_true[j] - h_true[jr])[None, :])[0].tolist()


def _kn(level: str) -> np.ndarray:
    from outrigger_sim.params import load_params

    kn = load_params(level=level).get("contact.rigid_floor.L1.kn_per_pad_N_m")
    return np.array([float(kn[leg]) for leg in LEGS])


def _events(case_dir: Path) -> list[tuple[float, str]]:
    import re

    f = case_dir / "controller_events.json"
    if not f.exists():
        return []
    pat = re.compile(r"t_s=([-0-9.eE+]+), name='([^']*)'")
    out = []
    for line in json.loads(f.read_text(encoding="utf-8")):
        m = pat.search(str(line))
        if m:
            out.append((float(m.group(1)), m.group(2)))
    return out


def case_export(case_dir: Path) -> dict | None:
    gf = case_dir / "ge1_series.json"
    if not gf.exists():
        return None
    res = json.loads((case_dir / "result.json").read_text(encoding="utf-8"))
    cid = res["case"]
    rows = json.loads(gf.read_text(encoding="utf-8"))
    if not check_keys(rows, cid):
        NO_SAMPLES.append(cid)
        return None
    t0 = float(res["settings"]["start_t_s"])
    with np.load(case_dir / "record" / "record.npz") as z:
        rec = {k: z[k] for k in ("t", "u_cmd", "meas.angular_rate")}
    t_rec = rec["t"] - t0
    with np.load(case_dir / "pads.npz") as z:
        pads = {k: z[k] for k in ("t", "N", "n_world", "contact_point_world")}
    tp = pads["t"] - t0
    h_true = true_pad_heights(pads, _kn(res["settings"]["level"]))
    out_rows = []
    for t, phase, v in rows:
        i = int(np.argmin(np.abs(t_rec - t)))
        j = min(int(np.searchsorted(tp, t - 1e-9)), len(tp) - 1)
        sample = v if isinstance(v, dict) else {}
        d = sample.get(K_D)
        ref = sample.get(K_REF)
        ref_rel = None if ref is None else float(ref) - t0  # controller time is absolute
        dd_true = true_delta_heights(h_true, tp, j, ref_rel)
        row = {
            "t_s": t, "phase": phase,
            "is_geometry_valid": sample.get(K_VALID),
            **_scalars("gate_", sample.get(K_GATE)),
            **{f"dD_{leg}_mm": (None if d is None else d[k] * 1e3) for k, leg in enumerate(LEGS)},
            "r_mm": None if sample.get(K_R) is None else sample[K_R] * 1e3,
            "dr_mm": None if sample.get(K_DR) is None else sample[K_DR] * 1e3,
            "ref_t_s": ref_rel,
            **{f"u_{leg}_m_s": float(rec["u_cmd"][i, k]) for k, leg in enumerate(LEGS)},
            "gyro_p_deg_s": float(np.degrees(rec["meas.angular_rate"][i, 0])),
            "gyro_q_deg_s": float(np.degrees(rec["meas.angular_rate"][i, 1])),
            **{f"N_{leg}_kN": float(pads["N"][j, k]) / 1e3 for k, leg in enumerate(LEGS)},
            **{f"dD_true_{leg}_mm": (None if dd_true[k] is None else dd_true[k] * 1e3)
               for k, leg in enumerate(LEGS)},
        }
        out_rows.append(row)
    fields = list(dict.fromkeys(k for r in out_rows for k in r))
    with (case_dir / "ge1_timeseries.csv").open("w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=fields)
        wr.writeheader()
        wr.writerows(out_rows)

    t_event = res.get("event_t_s")
    if t_event is None and res["settings"].get("event") and res.get("ready_t_s") is not None:
        # batches before RE3 (no event_t_s): the event was at first READY + 5 s (G5 change + 2 s).
        # RE3 batches carry event_t_s = the time the scenario actually used, counted from the
        # measured first READY (or PROBE), so the R5 CHECK extension and the +8 s run length
        # do not shift it.
        lead = 2.0 if res["settings"]["event"] == "target_change" else 5.0
        t_event = float(res["ready_t_s"]) + lead

    def table(sel):
        blk = {"n": len(sel)}
        dv = [abs(r[f"dD_{leg}_mm"]) for r in sel for leg in LEGS
              if r[f"dD_{leg}_mm"] is not None and r[f"N_{leg}_kN"] > 0.0]
        rv = [abs(r["dr_mm"]) for r in sel if r["dr_mm"] is not None]
        diff = [abs(r[f"dD_{leg}_mm"] - r[f"dD_true_{leg}_mm"]) for r in sel for leg in LEGS
                if r[f"dD_{leg}_mm"] is not None and r[f"dD_true_{leg}_mm"] is not None
                and r[f"N_{leg}_kN"] > 0.0]
        blk["grounded_dD_maxabs_mm"] = max(dv) if dv else None
        blk["dr_maxabs_mm"] = max(rv) if rv else None
        blk["sensor_minus_true_dD_maxabs_mm"] = max(diff) if diff else None
        return blk

    gate = [r for r in out_rows if r["is_geometry_valid"] is True]
    in_phases = [r for r in out_rows if r["phase"] in GATE_PHASES]
    pre = [r for r in gate if t_event is None or r["t_s"] < t_event]
    post = [r for r in gate if t_event is not None and r["t_s"] >= t_event]
    events = [(t - t0, name) for t, name in _events(case_dir)
              if is_shadow_event(name) or name.startswith("WARN_SUPPORT")]
    return {
        "case": cid, "group": res["settings"]["group"], "floor": res["settings"]["floor"],
        "grade": res["settings"]["grade"], "seed": res["settings"].get("seed"),
        "event": res["settings"].get("event"), "t_event_s": t_event,
        "t_forced_s": None if not (res.get("forced_retract") or {}).get("t_start_s")
        else float(res["forced_retract"]["t_start_s"]) - t0,
        "ready_t_s": res.get("ready_t_s"), "phases": res["phases"], "rows": out_rows,
        "gate_open": table(gate), "gate_before_event": table(pre),
        "gate_after_event": table(post),
        "gate_open_fraction_done_probe_ready": (sum(r["is_geometry_valid"] is True
                                                    for r in in_phases) / len(in_phases))
        if in_phases else None,
        "ge1_events": events,
        "reference_source": (((res.get("controller_meta") or {}).get("support_geometry") or {})
                             .get("reference_source")),
        "stationary_gate_settings": ((res.get("controller_meta") or {}).get("stationary_gate")
                                     or {}).get("settings"),
        "reference_updates_max_abs_height_change_mm": [
            None if u.get("max_abs_height_change_m") is None
            else u["max_abs_height_change_m"] * 1e3
            for u in ((res.get("controller_meta") or {}).get("support_geometry") or {}).get(
                "reference_updates", [])],
        "controller_support_geometry_meta": (res.get("controller_meta") or {}).get(
            "support_geometry"),
    }


def _first(rows, t_from, cond):
    for r in rows:
        if r["t_s"] >= t_from and cond(r):
            return r["t_s"]
    return None


def _re_ready(c) -> float | None:
    t_ev = c["t_event_s"]
    if t_ev is None:
        return None
    phases = [(float(t), p) for t, p in c["phases"]]
    left = next((t for t, p in phases if t > t_ev and p != "ready"), None)
    if left is None:
        return None
    return next((t for t, p in phases if t > left and p == "ready"), None)


def promotion_checks(cases: dict, prev_summary: Path | None, new_summary: Path | None):
    """U39 (spec rev. 7 43) pre-checks 1'-5."""
    rows = []
    for cid, c in cases.items():
        if c["group"] == "RE1c":
            continue
        st = c["gate_before_event"] if c["t_event_s"] is not None else c["gate_open"]
        if st["n"]:
            ok = ((st["grounded_dD_maxabs_mm"] or 0.0) <= D_TOL_MM
                  and (st["dr_maxabs_mm"] or 0.0) <= R_TOL_MM)
            row = {"check": "(1') gate |d^Delta| <= 2.5 mm, |Delta r| <= 0.8 mm"
                   + (" (before the event)" if c["t_event_s"] is not None else ""),
                   "case": cid, "value": [st["grounded_dD_maxabs_mm"], st["dr_maxabs_mm"]],
                   "passed": ok}
            if c.get("reference_source") == TOUCH_ONLY:
                # U59 / J-6 (spec 55.7): the pressure judge never refreshes its TOUCH-end
                # reference, so the later support changes stay in d^Delta: reported only.
                row.update(passed=None, passed_raw=ok, kind="info", note=TOUCH_ONLY_NOTE)
            rows.append(row)
        else:
            rows.append({"check": "(1')", "case": cid, "value": "gate never open",
                         "passed": None})
    for cid, c in cases.items():
        r = c["rows"]
        t_ev = c["t_event_s"]
        if c["event"] == "drop_RR_30" and t_ev is not None:
            first_any = _first(r, t_ev, lambda x: x["dD_RR_mm"] is not None
                               and x["dD_RR_mm"] < -D_TRIGGER_MM)
            first_gate = _first(r, t_ev, lambda x: x["is_geometry_valid"] is True
                                and x["dD_RR_mm"] is not None and x["dD_RR_mm"] < -D_TRIGGER_MM)
            others = [abs(x[f"dD_{leg}_mm"]) for x in r if x["t_s"] >= t_ev
                      and x["is_geometry_valid"] is True for leg in ("FL", "FR", "RL")
                      if x[f"dD_{leg}_mm"] is not None]
            others_all = [abs(x[f"dD_{leg}_mm"]) for x in r if x["t_s"] >= t_ev
                          for leg in ("FL", "FR", "RL") if x[f"dD_{leg}_mm"] is not None]
            rows.append({"check": "(2') RE1b-F RR d^Delta < -5 mm (first crossing after the drop)",
                         "case": cid, "value": {
                             "gate_independent_s": None if first_any is None else first_any - t_ev,
                             "in_gate_s": None if first_gate is None else first_gate - t_ev},
                         "passed": first_any is not None})
            mx = max(others) if others else None
            rows.append({"check": "(2') RE1b-F other legs |d^Delta| < 5 mm in the gate "
                         "(2.5 mm reported)", "case": cid,
                         "value": {"gate_max_mm": mx,
                                   "gate_over_2p5mm": None if mx is None else mx > D_TOL_MM,
                                   "all_samples_max_mm": max(others_all) if others_all else None},
                         "passed": None if mx is None else mx < D_TRIGGER_MM})
            t_rr = _re_ready(c)
            flags = [e for e in c["ge1_events"] if t_rr is not None and e[0] >= t_rr
                     and e[1].startswith("shadow_")]
            rows.append({"check": "(2') RE1b-F no GE1 flag after the re-READY", "case": cid,
                         "value": {"re_ready_s": t_rr, "flags": flags},
                         "passed": None if t_rr is None else not flags})
        if c["group"] == "RE1c":
            t_f = c["t_forced_s"] or 0.0
            neg = [x["t_s"] for x in r if x["t_s"] >= t_f and x["u_RR_m_s"] < 0.0]
            if neg:
                t_end = neg[-1]
                hit = _first(r, neg[0], lambda x: x["dD_RR_mm"] is not None
                             and x["dD_RR_mm"] > D_TRIGGER_MM)
                first = None if hit is None else hit - t_end
                rows.append({"check": "(3) RE1c RR d^Delta > +5 mm within 1 s after the retraction",
                             "case": cid, "value": {"first_after_end_s": first,
                                                    "retract_s": [neg[0], t_end]},
                             "passed": first is not None and first <= 1.0})
    if prev_summary and new_summary and prev_summary.exists() and new_summary.exists():
        old = json.loads(prev_summary.read_text(encoding="utf-8"))["rows"]
        new = json.loads(new_summary.read_text(encoding="utf-8"))["rows"]
        for cid in ("G4_top_flat_settleRR_pressure", "G4_top_flat_settleRR_combined"):
            o = {x["item"]: x["passed"] for x in old
                 if x["case"] == cid and x["passed"] is not None}
            n = {x["item"]: x["passed"] for x in new
                 if x["case"] == cid and x["passed"] is not None}
            rows.append({"check": "(4) G4 judged rows unchanged", "case": cid,
                         "value": {"old_failed": [k for k, v in o.items() if not v],
                                   "new_failed": [k for k, v in n.items() if not v]},
                         "passed": o == {k: n[k] for k in o if k in n}
                         and not [k for k, v in n.items() if not v]})
    else:
        rows.append({"check": "(4) G4 judged rows unchanged", "case": "G4",
                     "value": "previous / new closed-loop summary not given", "passed": None})
    rows.append({"check": "(5) L2b F_s 12 kN RE1b-F", "case": None,
                 "value": "L2b not prepared (report item, U39)", "passed": None})
    return rows


def main(batch: Path, prev_summary: Path | None = None,
         overrides: tuple[Path, ...] = (), tag: str = DEFAULT_TAG) -> Path:
    """Export ``batch``; case directories of the ``overrides`` batches (in order) replace the
    case directories of the same name (as ``s6_stage2_summary.py``). ``tag`` names the
    output and the check (4) summary (:func:`output_paths`). Returns the output path."""
    out, new_summary = output_paths(tag)
    dirs = {d.name: d for d in sorted(batch.iterdir()) if d.is_dir()}
    for extra in overrides:
        dirs.update({d.name: d for d in sorted(extra.iterdir()) if d.is_dir()})
    cases = {}
    for _name, d in sorted(dirs.items()):
        if (d / "result.json").exists():
            c = case_export(d)
            if c is not None:
                cases[c["case"]] = c
    checks = promotion_checks(cases, prev_summary, new_summary)
    doc = {
        "meta": {"batch": _rel(batch), "override_batches": [_rel(p) for p in overrides],
                 "cases_without_ge1_samples": list(NO_SAMPLES),
                 "script": "04_scripts/02_chrono/s6_ge1_export.py", "tag": tag,
                 "spec": "control spec rev. 7 37.3, 38, 42.1-42.2, U39 (pre-checks)",
                 "gate": "controller is_geometry_valid (no own stationary rule); gate state "
                         "stationary_gate -> CSV gate_* columns",
                 "shadow_G2_threshold_mm": SHADOW_NONPLANARITY_THRESHOLD_M * 1e3,
                 "shadow_G1_thresholds_mm": [SHADOW_SINK_THRESHOLD_M * 1e3,
                                              SHADOW_LIFT_THRESHOLD_M * 1e3],
                 "shadow_thresholds_source": "outrigger_sim.control.c2 constants",
                 "r5_keys": R5_KEYS, "csv": "<case dir>/ge1_timeseries.csv",
                 "true_path": "pad bottom = contact_point_world + (N / k_n) n, k_n = "
                              "contact.rigid_floor.L1.kn_per_pad_N_m (dynamics-expert "
                              "2026-10-22); ball centre not used",
                 "check4_previous_summary": None if prev_summary is None else _rel(prev_summary),
                 "check4_new_summary": _rel(new_summary)},
        "tables": {cid: {k: c[k] for k in ("group", "floor", "grade", "seed", "event",
                                            "t_event_s", "gate_open", "gate_before_event",
                                            "gate_after_event",
                                            "gate_open_fraction_done_probe_ready", "ge1_events",
                                            "reference_source", "stationary_gate_settings",
                                            "reference_updates_max_abs_height_change_mm",
                                            "controller_support_geometry_meta")}
                   for cid, c in cases.items()},
        "promotion_checks": checks,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False, default=float), encoding="utf-8")
    print(f"-> {_rel(out)}: {len(cases)} cases")
    for r in checks:
        print(r["check"], r["case"], r["value"], r["passed"])
    return out


def parse_args(argv: list[str]) -> tuple[Path, Path | None, tuple[Path, ...], str]:
    """(batch, previous summary or None, override batches, tag) from the command line
    (module docstring); unknown ``--`` options and missing values stop with a message."""
    positional: list[str] = []
    over: list[Path] = []
    tag = DEFAULT_TAG
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--override", "--tag"):
            if i + 1 >= len(argv):
                raise SystemExit(f"{a} needs a value")
            if a == "--override":
                over.append(Path(argv[i + 1]).resolve())
            else:
                tag = argv[i + 1]
            i += 2
            continue
        if a.startswith("--tag="):
            tag = a.split("=", 1)[1]
        elif a.startswith("--override="):
            over.append(Path(a.split("=", 1)[1]).resolve())
        elif a.startswith("--"):
            raise SystemExit(f"unknown option {a}")
        else:
            positional.append(a)
        i += 1
    if not positional or len(positional) > 2:
        raise SystemExit(__doc__)
    try:
        output_paths(tag)
    except ValueError as e:
        raise SystemExit(str(e)) from None
    batch = Path(positional[0]).resolve()
    prev = Path(positional[1]).resolve() if len(positional) > 1 else None
    return batch, prev, tuple(over), tag


if __name__ == "__main__":
    b, p, o, t = parse_args(sys.argv[1:])
    main(b, p, o, tag=t)
