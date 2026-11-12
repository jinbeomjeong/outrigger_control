"""436.8 v5 resume Chrono rows (cad 2026-11-13, ``04_scripts/02_chrono/v5_resume_4368_chrono_rows.py``; rules
``v5_resume_4368_rules.md`` sha256 ``9019b405`` 4.1 / 4.2 / 5.2 / 5.3 / 5.4 / 11.2).

No Chrono run: row counts and tags, the C-4 / C-8 argv differences, the O-C5 R_c probe procedure (5.4-3 .. 5.4-8) on
written-out R_c values, the probe reader on a synthetic batch folder.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHRONO_SCRIPTS = PROJECT_ROOT / "04_scripts" / "02_chrono"
VB, V0, OFF = "final_C4G2_P3_LAS_K1", "final_C4G2_LAS_K1", "final_C4G2_P3_K1"


def _import(name: str):
    sys.path.insert(0, str(CHRONO_SCRIPTS))
    try:
        return __import__(name)
    finally:
        sys.path.remove(str(CHRONO_SCRIPTS))


@pytest.fixture(scope="module")
def mod():
    return _import("v5_resume_4368_chrono_rows")


@pytest.fixture(scope="module")
def batches():
    pytest.importorskip("pychrono")
    sb = _import("s9_batch")
    return sb, sb.batches()


# ------------------------------------------------------------------------------------------ procedure (no Chrono)
def test_probe_duration_and_first_k(mod):
    assert mod.PROBE_DURATION_S == {"A3": 7.0, "A5": 7.0}  # CHECK end 4.8 s + 2 s, ceil
    assert mod.oc5_first_k("C-8a") == 0.9179
    assert mod.oc5_first_k("C-8b") == 0.8829
    assert mod.floor_of_k(0.9179) == (2.1434, 1.3784)
    assert mod.floor_of_k(1.0) == (2.3351, 1.5017)


def _p(n, k, rc, attempt=1):
    return {"n": n, "attempt": attempt, "k": k, "R_c": rc, "case": f"c{n}{attempt}", "folder": "f"}


def test_first_probe_within(mod):
    assert mod.oc5_evaluate("C-8a", [])["next"] == {"n": 1, "attempt": 1, "k": 0.9179, "duration_s": 7.0}
    ev = mod.oc5_evaluate("C-8a", [_p(1, 0.9179, 0.97)])  # |0.97 - 0.95| = 0.02 -> within (7.6 allowance)
    assert ev["status"] == "decided" and ev["k"] == 0.9179 and ev["n_probes"] == 1


def test_proportional_then_secant(mod):
    ev = mod.oc5_evaluate("C-8a", [_p(1, 0.9179, 1.0)])
    assert ev["status"] == "probing" and ev["next"]["n"] == 2
    k2 = ev["next"]["k"]
    assert k2 == round(0.9179 * 0.95 / 1.0, 4)
    ev3 = mod.oc5_evaluate("C-8a", [_p(1, 0.9179, 1.0), _p(2, k2, 0.90)])
    k3 = round(0.9179 + (0.95 - 1.0) * (k2 - 0.9179) / (0.90 - 1.0), 4)
    assert ev3["next"] == {"n": 3, "attempt": 1, "k": k3, "duration_s": 7.0}
    stop = mod.oc5_evaluate("C-8a", [_p(1, 0.9179, 1.0), _p(2, k2, 0.90), _p(3, k3, 0.99)])
    assert stop["status"] == "stopped" and "5.4-7" in stop["reason"]


def test_secant_undefined_and_k_range(mod):
    ev = mod.oc5_evaluate("C-8b", [_p(1, 0.8829, 1.2), _p(2, 0.699, 1.2)])
    assert ev["status"] == "stopped" and "no secant" in ev["reason"]
    ev = mod.oc5_evaluate("C-8b", [_p(1, 0.8829, 0.5)])  # k2 = 1.6775 > 1
    assert ev["status"] == "stopped" and "(0, 1]" in ev["reason"]


def test_missing_rc_retry_not_counted(mod):
    ev = mod.oc5_evaluate("C-8a", [_p(1, 0.9179, None)])
    assert ev["next"] == {"n": 1, "attempt": 2, "k": 0.9179, "duration_s": 14.0}
    assert ev["n_probes"] == 1
    ev = mod.oc5_evaluate("C-8a", [_p(1, 0.9179, None), _p(1, 0.9179, None, attempt=2)])
    assert ev["status"] == "stopped" and "5.4-3" in ev["reason"]
    ev = mod.oc5_evaluate("C-8a", [_p(1, 0.9179, None), _p(1, 0.9179, 0.94, attempt=2)])
    assert ev["status"] == "decided" and ev["n_probes"] == 1


def test_probe_reader_reads_start_condition_only(mod, tmp_path, monkeypatch):
    state = tmp_path / "state.json"
    monkeypatch.setenv(mod.OC5_STATE_ENV, str(state))
    folder = tmp_path / "batch"
    case = "OC5P_Kc3_VB_n1_k0p9179"
    (folder / case).mkdir(parents=True)
    (folder / case / "result.json").write_text(json.dumps({
        "p3b_ext": {"start_condition": {"R_c_operating": 0.951, "crawler_attitude_deg": [2.0, 1.4]}},
        "args": {"floor_roll": 2.1434, "floor_pitch": 1.3784, "duration": 7.0}, "phases": [],
        "p3b": {"P3-3_leg_force": {"F_min_after_N": 1.0}}}), "utf-8")
    (folder / "batch.json").write_text(json.dumps({"cases": [{"case": case, "rc": 0, "r4368": {
        "role": "probe", "oc5_row": "C-8a", "probe": {"n": 1, "attempt": 1, "k": 0.9179, "duration_s": 7.0}}}]}),
        "utf-8")
    assert mod.cmd_oc5_read(str(folder)) == 0
    st = json.loads(state.read_text("utf-8"))
    p = st["rows"]["C-8a"]["probes"][0]
    assert p["R_c"] == 0.951 and "F_min_after_N" not in json.dumps(p)
    assert mod.oc5_evaluate("C-8a", st["rows"]["C-8a"]["probes"])["status"] == "decided"
    assert mod.cmd_oc5_read(str(folder)) == 0  # idempotent
    assert len(json.loads(state.read_text("utf-8"))["rows"]["C-8a"]["probes"]) == 1


# --------------------------------------------------------------------------------------------- rows (pychrono)
def test_counts_and_tags(mod, batches):
    _, b = batches
    assert len(b[mod.B_C1]) == 10 and len(b[mod.B_C3]) == 2 and len(b[mod.B_C4]) == 4
    assert len(b[mod.B_C5]) == 35 and len(b[mod.B_C6C7]) == 3 and len(b[mod.B_JP]) == 12
    assert [r["case"] for r in b[mod.B_C3]] == list(mod.C3_NAMES)
    assert not set(mod.C5_DROP) & {r["case"] for r in b[mod.B_C5]}
    for name in mod.BATCHES:
        for r in b[name]:
            tail = mod.script_tail(r["argv"])
            off = r["r4368"].get("arm") == "off"
            if r.get("controller") is not None:
                assert r["controller"] in ((OFF,) if off else (VB, V0))
            if "--expect-controller" in tail:
                assert tail[tail.index("--expect-controller") + 1] == r["controller"]
            for tok in mod.FORBIDDEN_TOKENS:
                assert tok not in tail or (off and tok in ("--las-off", "--k1-order-gate")), (r["case"], tok)
            if r["r4368"]["engine"] == "SCM":
                assert r["start_env"] == {"OMP_WAIT_POLICY": "PASSIVE"}
                assert tail[tail.index("--threads") + 1] == "4"


def test_c4_and_c8_diffs(mod, batches):
    sb, b = batches
    c4 = {(r["r4368"]["crawler"], r["r4368"]["arm"]): r for r in b[mod.B_C4]}
    for crawler, a in (("Kc1", "A1"), ("Kc3", "A3")):
        assert mod.option_diff(c4[(crawler, "on")]["argv"], mod._a_row_argv(sb, a)) == ["--las-candidate"]
        assert mod.option_diff(c4[(crawler, "off")]["argv"], c4[(crawler, "on")]["argv"]) == [
            "--expect-controller", "--k1-order-gate", "--las-off"]
    for rid, spec in mod.OC5_ROWS.items():
        assert mod.option_diff(mod.oc5_argv(sb, rid, 0.9), mod._a_row_argv(sb, spec["base"])) == [
            "--floor-pitch", "--floor-roll", "--las-candidate"]
    probe = next(r for r in b[mod.B_PROBE] if r["r4368"]["oc5_row"] == "C-8a")
    main = mod.oc5_argv(sb, "C-8a", probe["k"])
    assert mod.option_diff(probe["argv"], main) == ["--duration"]
