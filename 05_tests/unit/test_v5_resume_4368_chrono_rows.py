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


# ------------------------------------------------------------------------- gs_conditional_absent (user decision (a))
COND_KEYS = {
    "p3b.P3-3_leg_force.F_min_after_N": "p3b.departure.departed",
    "p3b.P3-3_leg_force.F_min_transient_N": "p3b.departure.departed",
    "c2_setup.las_off": "<off arm>",
    **{f"controller_meta.liftoff_approach_slow.{k}": "<on arm>"
       for k in ("start_s", "end_s", "end_reason", "active_periods", "ramp", "ramp.periods_applied")}}


def test_conditional_table_from_code_is_deterministic(mod):
    t1, t2 = mod.gs_conditional_table(), mod.gs_conditional_table()
    assert json.dumps(t1, sort_keys=True) == json.dumps(t2, sort_keys=True)
    assert {k: v["condition"] for k, v in t1["keys"].items()} == COND_KEYS
    assert list(t1["keys"]) == sorted(t1["keys"]) and t1["row_kind"] == "level"
    assert t1["keys"]["c2_setup.las_off"]["required_when"].startswith("off arm")


def test_absence_rules(mod):
    dep = "p3b.P3-3_leg_force.F_min_after_N"
    assert mod.absence_allowed(dep, "p3b.departure.departed", {"p3b": {"departure": {"departed": False}}}, False)[0]
    for doc in ({"p3b": {"departure": {"departed": True}}}, {"p3b": {}}):  # condition true or missing: required
        assert not mod.absence_allowed(dep, "p3b.departure.departed", doc, False)[0]
    assert mod.absence_allowed("c2_setup.las_off", "<off arm>", {}, False)[0]
    assert not mod.absence_allowed("c2_setup.las_off", "<off arm>", {}, True)[0]
    assert mod.absence_allowed("x", "<on arm>", {}, True)[0] and not mod.absence_allowed("x", "<on arm>", {}, False)[0]


TEST_BATCH = "V5-RESUME-K1-T"
"""Full batch name of the synthetic level folders (rev10 R10-1a: batch.json batch = folder part = manifest key)."""


@pytest.fixture(autouse=True)
def _rows_manifest(request, tmp_path_factory, monkeypatch):
    """Rev10 R10-2: gs-check reads a rows manifest; the synthetic folders' bundle holds case ``LV``."""
    if "mod" not in request.fixturenames:
        return
    mod = request.getfixturevalue("mod")
    path = tmp_path_factory.mktemp("rows") / "rows_manifest.json"
    path.write_text(json.dumps({"batches": {TEST_BATCH: {"rows": [{"case": "LV"}]}}}), "utf-8")
    monkeypatch.setattr(mod, "ROWS_MANIFEST_DEFAULT", path)


CODE_AT_LAUNCH = {"files": {"03_src/outrigger_sim/control/c2.py": "0" * 64},
                  "git": {"head": "4312b8e" + "0" * 33, "paths": ["03_src/outrigger_sim/control"], "dirty": [],
                          "clean": True, "taken_utc": "2026-11-13T00:00:00+09:00"}}
"""s9_batch ``launch_code_state`` form (rev11 R11-4: gs-check needs a 40-hex ``code_at_launch.git.head``)."""


def _level_folder(tmp_path: Path, mod, departed, drop: list[str], arm: str = "on", law_locked=True,
                  expect_ok=True, t_step_s: float = 1e-3) -> Path:
    np = pytest.importorskip("numpy")
    keys, _ = mod.gs_key_paths()
    doc: dict = {}
    for k in sorted(keys, key=lambda s: -s.count(".")):  # deeper paths first: a prefix key stays a dict
        node = doc
        parts = k.split(".")
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node.setdefault(parts[-1], 1)
    doc.setdefault("p3b", {})["departure"] = {"departed": departed}
    if expect_ok is not None:  # rev9 R9-1: the controller-tag check of the row
        doc.setdefault("c2_setup", {})["expect_controller"] = {"name": "x", "ok": expect_ok}
    for k in drop:
        parts = k.split(".")
        node = doc
        for p in parts[:-1]:
            node = node[p]
        node.pop(parts[-1], None)
    f = tmp_path / f"batch_{TEST_BATCH}_20261113_000000"
    case = "LV"
    (f / case).mkdir(parents=True)
    (f / case / "result.json").write_text(json.dumps(doc), "utf-8")
    np.savez(f / case / "controller_commands.npz", t_s=np.arange(3.0), issued_u_m_s=np.zeros(3))
    for n in mod.SERIES_FILES:
        np.savez(f / case / n, t=np.arange(2.0))
    if law_locked is True:  # the run_S9 record (Q-R8-1 = B)
        law_locked = np.array([[-1, -1, -1, -1], [1, 0, 1, 1]], dtype=np.int8)
    series = {"t_s": np.arange(2.0) * t_step_s} | ({} if law_locked is None else {"law_locked": law_locked})
    np.savez(f / case / "step_series.npz", **series)
    entry = {k: "x" for k in mod.GS_ENTRY_KEYS}
    entry.update(case=case, argv=["python", "run_S9.py", "level"], r4368={"engine": "SCM", "arm": arm},
                 code_at_launch=CODE_AT_LAUNCH)
    (f / "batch.json").write_text(json.dumps({"batch": TEST_BATCH, "cases": [entry]}), "utf-8")
    (f / "progress.log").write_text(f"END {case} 2026-11-13T00:00:00 rc=0\n", "utf-8")
    return f


def test_gs_check_condition_true_but_absent_is_error(mod, tmp_path, capsys):
    dep = ["p3b.P3-3_leg_force.F_min_after_N", "c2_setup.las_off"]
    ok = _level_folder(tmp_path / "a", mod, False, dep)
    assert mod.cmd_gs_check(str(ok)) == 0
    out = json.loads(capsys.readouterr().out.rsplit("errors", 1)[0])
    assert out["cases"][0]["conditional_absent"] == dep
    bad = _level_folder(tmp_path / "b", mod, True, dep)  # departed: F_min_after_N is required
    assert mod.cmd_gs_check(str(bad)) == 1
    c = json.loads(capsys.readouterr().out.rsplit("errors", 1)[0])["cases"][0]
    assert c["result_missing"] == ["p3b.P3-3_leg_force.F_min_after_N"]
    assert c["conditional_required_but_absent"][0]["condition_value"] is True
    off = _level_folder(tmp_path / "c", mod, False, ["c2_setup.las_off"], arm="off")  # off arm needs las_off
    assert mod.cmd_gs_check(str(off)) == 1
    capsys.readouterr()


def test_gs_check_law_locked_series_key(mod, tmp_path, capsys):
    """Q-R8-1 = B (2026-11-13): a level row without step_series.npz law_locked, or with a wrong form, is an error;
    the manifest table (result.json keys) does not list it."""
    np = pytest.importorskip("numpy")
    assert mod.SERIES_KEYS == {"step_series.npz": ("t_s", "law_locked")}
    assert not any("law_locked" in k for k in mod.gs_conditional_table()["keys"])
    assert mod.cmd_gs_check(str(_level_folder(tmp_path / "a", mod, False, []))) == 0
    capsys.readouterr()
    assert mod.cmd_gs_check(str(_level_folder(tmp_path / "b", mod, False, [], law_locked=None))) == 1
    c = json.loads(capsys.readouterr().out.rsplit("errors", 1)[0])["cases"][0]
    assert c["series_keys_missing"] == ["step_series.npz:law_locked"]
    for bad in (np.zeros((2, 4), dtype=np.int64), np.zeros((2, 3), dtype=np.int8),
                np.full((2, 4), 2, dtype=np.int8)):
        assert mod.cmd_gs_check(str(_level_folder(tmp_path / f"c{bad.dtype}{bad.shape}{bad.max()}", mod, False, [],
                                                  law_locked=bad))) == 1
        c = json.loads(capsys.readouterr().out.rsplit("errors", 1)[0])["cases"][0]
        assert c["series_key_problems"] and not c["series_keys_missing"]


def test_gs_check_rev9_law_locked_form_and_expect_check(mod, tmp_path, capsys):
    """Rev9 R9-1 (expect_controller.ok false or missing), R9-2 (1 ms spacing) and R9-3 (-1 patterns) at G-S."""
    np = pytest.importorskip("numpy")
    cases = {
        "spacing": {"t_step_s": 1.0},
        "after_arm": {"law_locked": np.array([[1, 0, 1, 1], [-1, -1, -1, -1]], dtype=np.int8)},
        "whole_run": {"law_locked": np.full((2, 4), -1, dtype=np.int8)},
        "leg_mismatch": {"law_locked": np.array([[-1, 0, -1, -1], [1, 0, 1, 1]], dtype=np.int8)},
    }
    for name, kwargs in cases.items():
        assert mod.cmd_gs_check(str(_level_folder(tmp_path / name, mod, False, [], **kwargs))) == 1, name
        c = json.loads(capsys.readouterr().out.rsplit("errors", 1)[0])["cases"][0]
        assert c["series_key_problems"] and not c["series_keys_missing"], name
    for name, ok in (("expect_false", False), ("expect_missing", None)):
        assert mod.cmd_gs_check(str(_level_folder(tmp_path / name, mod, False, [], expect_ok=ok))) == 1
        c = json.loads(capsys.readouterr().out.rsplit("errors", 1)[0])["cases"][0]
        assert c["expect_controller_ok"] is False and not c["series_key_problems"]
    assert mod.cmd_gs_check(str(_level_folder(tmp_path / "pre_arm", mod, False, []))) == 0
    c = json.loads(capsys.readouterr().out.rsplit("errors", 1)[0])["cases"][0]
    assert c["law_locked_minus_one"] == "pre_arm_prefix"


def _openloop_folder(tmp_path: Path, mod, entry_changes: dict | None = None, drop_head: bool = False) -> Path:
    """Synthetic G-S folder with one open-loop ``run_S9.py machine`` row (case ``LV``, the rows-manifest case)."""
    np = pytest.importorskip("numpy")
    doc: dict = {}
    for k in sorted(mod.OPENLOOP_KEY_PATHS, key=lambda s: -s.count(".")):
        node = doc
        parts = k.split(".")
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node.setdefault(parts[-1], 1)
    if drop_head:
        doc["code_state"]["git_at_start"].pop("head")
    f = tmp_path / f"batch_{TEST_BATCH}_20261113_000000"
    (f / "LV").mkdir(parents=True)
    (f / "LV" / "result.json").write_text(json.dumps(doc), "utf-8")
    for n in mod.OPENLOOP_FILES:
        np.savez(f / "LV" / n, t=np.arange(2.0))
    entry = {k: "x" for k in mod.GS_ENTRY_KEYS if k != "controller"}
    entry.update(case="LV", argv=["python", "run_S9.py", "machine", "--lift-s", "10"],
                 r4368={"engine": "SCM"}, code_at_launch=CODE_AT_LAUNCH)
    for k, v in (entry_changes or {}).items():
        if v is None:
            entry.pop(k, None)
        else:
            entry[k] = v
    (f / "batch.json").write_text(json.dumps({"batch": TEST_BATCH, "cases": [entry]}), "utf-8")
    (f / "progress.log").write_text("END LV 2026-11-13T00:00:00 rc=0\n", "utf-8")
    return f


def test_gs_check_rev11_open_loop_code_at_launch(mod, tmp_path, capsys):
    """Rev11 R11-4 (Q-R11-1 = B): an open-loop row needs batch.json code_at_launch with a 40-hex git.head and
    result.json code_state.git_at_start.head; a missing or malformed record fails the row (S-12 at the judge)."""
    assert "code_state.git_at_start.head" in mod.OPENLOOP_KEY_PATHS
    assert mod.cmd_gs_check(str(_openloop_folder(tmp_path / "ok", mod))) == 0
    c = json.loads(capsys.readouterr().out.rsplit("errors", 1)[0])["cases"][0]
    assert c["kind"] == "openloop" and c["code_at_launch_head_ok"] and not c["batch_entry_missing"]
    bad = {"none": {"code_at_launch": None},
           "error": {"code_at_launch": {"files": {}, "git": {"error": "CalledProcessError: x"}}},
           "short": {"code_at_launch": {"files": {}, "git": {**CODE_AT_LAUNCH["git"], "head": "4312b8e"}}}}
    for name, change in bad.items():
        assert mod.cmd_gs_check(str(_openloop_folder(tmp_path / name, mod, change))) == 1, name
        c = json.loads(capsys.readouterr().out.rsplit("errors", 1)[0])["cases"][0]
        assert not c["code_at_launch_head_ok"] and c["code_at_launch_head_problem"], name
        assert (c["batch_entry_missing"] == ["code_at_launch"]) == (name == "none"), name
    assert mod.cmd_gs_check(str(_openloop_folder(tmp_path / "nohead", mod, drop_head=True))) == 1
    c = json.loads(capsys.readouterr().out.rsplit("errors", 1)[0])["cases"][0]
    assert c["result_missing"] == ["code_state.git_at_start.head"] and c["code_at_launch_head_ok"]


def test_gs_check_rev11_level_head_form(mod, tmp_path, capsys):
    """Rev11 R11-4 item 4: level rows also need a 40-hex code_at_launch.git.head (presence was already required)."""
    f = _level_folder(tmp_path / "a", mod, False, [])
    assert mod.cmd_gs_check(str(f)) == 0
    assert json.loads(capsys.readouterr().out.rsplit("errors", 1)[0])["cases"][0]["code_at_launch_head_ok"]
    _rewrite_batch(f, cases=[{**json.loads((f / "batch.json").read_text("utf-8"))["cases"][0], "code_at_launch": "x"}])
    assert mod.cmd_gs_check(str(f)) == 1
    c = json.loads(capsys.readouterr().out.rsplit("errors", 1)[0])["cases"][0]
    assert not c["code_at_launch_head_ok"] and not c["batch_entry_missing"]


def _rewrite_batch(folder: Path, **changes) -> None:
    doc = json.loads((folder / "batch.json").read_text("utf-8"))
    doc.update(changes)
    (folder / "batch.json").write_text(json.dumps(doc), "utf-8")


def test_gs_check_rev10_ls_sources(mod, tmp_path, capsys):
    """Rev10 R10-2: full batch name decided and the case exactly once per source, else the row fails (S-11)."""
    assert mod.cmd_gs_check(str(_level_folder(tmp_path / "ok", mod, False, []))) == 0
    out = json.loads(capsys.readouterr().out.rsplit("errors", 1)[0])
    assert out["ls_sources_R10_2"]["batch_name"]["name"] == TEST_BATCH and out["cases"][0]["ls_sources_ok"]
    assert out["ls_sources_R10_2"]["counts"]["both_sources_without_v5_setting"] == 0  # batch.json says "x"
    other = _level_folder(tmp_path / "name", mod, False, [])
    _rewrite_batch(other, batch="V5-RESUME-K1-C5")  # differs from the folder name part
    assert mod.cmd_gs_check(str(other)) == 1
    c = json.loads(capsys.readouterr().out.rsplit("errors", 1)[0])["cases"][0]
    assert (c["ls_boundary_case"], c["ls_sources_ok"]) == ("batch_name_unknown", False)
    absent = _level_folder(tmp_path / "nokey", mod, False, [])
    doc = json.loads((absent / "batch.json").read_text("utf-8"))
    del doc["batch"]
    (absent / "batch.json").write_text(json.dumps(doc), "utf-8")
    assert mod.cmd_gs_check(str(absent)) == 0  # no batch key: the folder name part
    capsys.readouterr()
    twice = _level_folder(tmp_path / "twice", mod, False, [])
    doc = json.loads((twice / "batch.json").read_text("utf-8"))
    _rewrite_batch(twice, cases=doc["cases"] * 2)
    assert mod.cmd_gs_check(str(twice)) == 1
    out = json.loads(capsys.readouterr().out.rsplit("errors", 1)[0])
    assert out["ls_sources_R10_2"]["counts"]["batch_json_entries_not_one"] == 1
    missing_row = tmp_path / "rows_without_case.json"
    missing_row.write_text(json.dumps({"batches": {TEST_BATCH: {"rows": []}}}), "utf-8")
    assert mod.cmd_gs_check(str(_level_folder(tmp_path / "m0", mod, False, [])), None, str(missing_row)) == 1
    c = json.loads(capsys.readouterr().out.rsplit("errors", 1)[0])["cases"][0]
    assert c["ls_boundary_case"] == "manifest_rows_not_one"


def test_gs_check_rev10_missing_rows_manifest_is_an_input_error(mod, tmp_path, capsys):
    folder = _level_folder(tmp_path / "a", mod, False, [])
    assert mod.cmd_gs_check(str(folder), None, str(tmp_path / "none.json")) == 2
    bad = tmp_path / "bad.json"
    bad.write_text("{", "utf-8")
    assert mod.cmd_gs_check(str(folder), None, str(bad)) == 2
    bad.write_text(json.dumps({"rows": []}), "utf-8")
    assert mod.cmd_gs_check(str(folder), None, str(bad)) == 2
    capsys.readouterr()


def test_gs_check_manifest_table(mod, tmp_path, capsys):
    f = _level_folder(tmp_path, mod, False, [])
    m = tmp_path / "m.json"
    m.write_text(json.dumps({"gs_conditional_absent": mod.gs_conditional_table()}), "utf-8")
    assert mod.cmd_gs_check(str(f), str(m)) == 0
    doc = json.loads(m.read_text("utf-8"))
    doc["gs_conditional_absent"]["keys"].pop("c2_setup.las_off")
    m.write_text(json.dumps(doc), "utf-8")
    assert mod.cmd_gs_check(str(f), str(m)) == 1
    assert mod.cmd_gs_check(str(f), str(tmp_path / "none.json")) == 1
    capsys.readouterr()


STORED_MANIFEST = PROJECT_ROOT / "06_analysis" / "02_control" / "verif_matrix" / "v5_resume_4368" / \
    "chrono_rows_manifest.json"


@pytest.mark.skipif(not STORED_MANIFEST.is_file(), reason="stored manifest absent")
def test_stored_manifest_table_and_scope(mod, batches):
    _, b = batches
    doc = json.loads(STORED_MANIFEST.read_text("utf-8"))
    assert json.dumps(doc["gs_conditional_absent"], sort_keys=True) == json.dumps(mod.gs_conditional_table(b),
                                                                                   sort_keys=True)
    scope = doc["gs_conditional_absent"]["scope"]
    assert sorted(scope[mod.B_C4]["off_arm_rows"]) == sorted(r["case"] for r in b[mod.B_C4] if mod.is_off_arm(r))
    assert scope[mod.B_C1]["level_rows"] == [] and len(scope[mod.B_C5]["level_rows"]) == 11
