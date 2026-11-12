"""436.8 rules rev1 (``v5_resume_4368_rules_rev1.md``, sealed d9094fda) path 1 follow-up.

H-10 440 and the main total, the H-6 .. H-9 grid steps from the stored key sources, the r79
``--keys-file`` option, the run_v5 overlap reference path, the rev1 seal check and the judge
subcommands keyset / dg3-hash / anchor-map / import-check / fmin-time / stroke-exposure, the
family table in ``k1-class``. Synthetic inputs only; no harness or Chrono run.
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
COUPLED = ROOT / "04_scripts" / "04_hydraulic" / "coupled"
S8 = ROOT / "04_scripts" / "03_control" / "s8"
SCRIPTS = ROOT / "06_analysis" / "02_control" / "verif_matrix" / "scripts"
for _path in (COUPLED, SCRIPTS, ROOT / "03_src"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import resume4368_judge as judge  # noqa: E402
import resume_k1_record as record  # noqa: E402
import run_v5  # noqa: E402

steps = importlib.import_module("resume_k1_steps")
family = importlib.import_module("resume_k1_family")

DG3_KEYS = [
    "cand=current#L2|s0|g6|52|ref|J1|top|Fs0",
    "cand=current#L3|s0|g6|5|g6|G1+J1@FR|top|Fs4",
]
NOISE_KEYS = [
    "cand=current#L1|s0|g6|0|g6|G1+J1@FL|top|Fs0",
    "cand=current#L2|s0|g6|1|g6|G1+J1@FL|top|Fs4",
    "cand=current#L3|s0|g6|2|g6|G1+J1@FL|bottom|Fs0",
]
SEEDEXT_KEYS = [
    "cand=current#L2|s0|g6|56|ref|J2|top|Fs0",
    "cand=current#L2|s24|g6|56|ref|J2|top|Fs0",
]


def _sha(path: Path) -> str:
    return judge.file_sha256(path)


def _write_json(path: Path, document: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def _grid_document(name: str) -> dict:
    offsets = [float(v) for v in steps.GRID_RUNS[name]["env"]["R67_OFFSETS"].split(",")]
    results = [
        {
            "key": key,
            "runs": [
                {"event": event, "offset_s": offset}
                for event in steps.GRID_EVENTS
                for offset in offsets
            ],
        }
        for key in steps.grid_expected_keys(name)
    ]
    return {"meta": steps.grid_expected_meta(name), "results": results}


def _stored_sources(data_root: Path) -> dict:
    """Synthetic appendix B files under ``data_root`` and STORED_SOURCES with their sha."""
    documents = {
        "dg3_v4_on": {"results": [{"key": k} for k in DG3_KEYS]},
        "dg3_off": {"results": [{"key": k} for k in reversed(DG3_KEYS)]},
        "noise_VB": {"results": [{"key": k} for k in NOISE_KEYS]},
        "noise_V0": {"results": [{"key": k} for k in NOISE_KEYS]},
        "seedext_VB": {"results": [{"key": k} for k in SEEDEXT_KEYS]},
        "seedext_V0": {"results": [{"key": k} for k in SEEDEXT_KEYS]},
        **{name: _grid_document(name) for name in steps.GRID_RUNS},
    }
    table = {}
    for name, document in documents.items():
        relative = steps.STORED_SOURCES[name][0]
        path = _write_json(data_root / steps.V5 / relative, document)
        table[name] = (relative, _sha(path))
    for name in steps.GRID_RUNS:  # the stored V0 grid of the R3-E1 sample
        _write_json(data_root / steps.GRID_V0_STORED / f"{name}.json", _grid_document(name))
    return table


def _build(data_root: Path, out: Path):
    args = steps.argparse.Namespace(
        root=r"C:\workspace\outrigger_control",
        data_root=str(data_root),
        workers=4,
        mask="0x00FF0000",
    )
    return steps.write(out, steps.build(args))


# --------------------------------------------------------------------------------- RV1-2 counts
def test_h10_is_440_and_the_main_total(tmp_path) -> None:
    report = _build(tmp_path, tmp_path / "steps")
    counts = report["counts"]
    assert steps.TABLE_LINES["H-10"] == 440
    assert counts["H-10"]["derived"] == 440 and counts["H-10"]["differs_S15"] is False
    assert counts["H-10"]["parts"]["jobs"] == {
        "main": 388,
        "u9_targeted": 28,
        "item8": 12,
        "overlap": 12,
    }
    doc = json.loads((tmp_path / "steps" / "steps_h2.json").read_text(encoding="utf-8"))
    assert not [s for s in doc["steps"] if "p3_hash" in s["cmd"]]  # RV1-2: no p3_hash run
    total = counts["main_total"]
    # rev3 R3-F1: the sum is 9,570 and a record only (S-15 compares the bundle counts)
    assert total["rules_value"] == 9570 == total["table_sum"]
    assert total["differs_S15"] is None and "record_only" in total


def test_p3_hash_jobs_are_main_vb_jobs(tmp_path) -> None:
    main_vb = [job for job in run_v5.batch_jobs("main") if job["setting"] == "VB"]
    seen, lines = set(), []
    for job in main_vb:  # the first VB job per case, as p3_hash_jobs picks them
        if job["case"] not in seen:
            seen.add(job["case"])
            lines.append({"job": job})
    stored = tmp_path / steps.V5 / "main.jsonl"
    stored.parent.mkdir(parents=True)
    stored.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    counts = steps.h10_counts(tmp_path)
    assert counts["p3_hash_in_main_vb"] == "22/22" and counts["p3_hash_all_in_main_vb"] is True


# ------------------------------------------------------------------------- RV1-3 steps / names
def test_h6_to_h9_grid_steps_from_the_stored_sources(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(steps, "STORED_SOURCES", _stored_sources(tmp_path))
    out = tmp_path / "steps"
    report = _build(tmp_path, out)
    assert report["blocked"] == {}
    counts = report["counts"]
    assert counts["H-6"]["derived"] == counts["H-7"]["derived"] == 2
    assert counts["H-8"]["derived"] == 3 + 3 + 2 + 2
    h6, h7 = (
        json.loads((out / f"steps_bundle_{n}.json").read_text(encoding="utf-8"))["steps"]
        for n in ("h6", "h7")
    )
    assert [s["id"] for s in h6] == [
        "h6_dg3_v4on_identity_start",
        "h6_dg3_v4on",
        "h6_dg3_v4on_identity_end",
    ]
    run6, run7 = h6[1], h7[1]
    assert steps.DG3 in run6["cmd"] and "--levels L2,L3" in run6["cmd"]
    assert '--keys "L2|s0|g6|52|ref|J1|top|Fs0;L3|s0|g6|5|g6|G1+J1@FR|top|Fs4"' in run6["cmd"]
    assert run6["env"]["LAS_T3_DG3_P3"] == "on" and run7["env"]["LAS_T3_DG3_P3"] == "off"
    assert run6["env"]["R79_T4H_DIR"] == f"{steps.RESUME}/h6_dg3_v4on_t4h"
    assert run7["resume_k1"]["output"] == f"{steps.RESUME}/h7_dg3_off.json"
    assert run6["resume_k1"]["expected_tags"] == {"VB": judge.TAG_P3}
    assert run7["resume_k1"]["expected_tags"] == {"VB": judge.TAG_V0}  # RV1-3.2: ③ off
    h8 = json.loads((out / "steps_bundle_h8.json").read_text(encoding="utf-8"))["steps"]
    runs = [s for s in h8 if "identity" not in s["id"]]
    assert [s["resume_k1"]["output"].rsplit("/", 1)[1] for s in runs] == [
        "h8_noise_VB.json",
        "h8_noise_V0.json",
        "h8_seedext_VB.json",
        "h8_seedext_V0.json",
    ]
    assert "--keys" not in runs[0]["cmd"] and "--levels L1,L2,L3" in runs[0]["cmd"]
    assert f"--keys-file {steps.V5}/seedext/r79_VB_seedext.json" in runs[2]["cmd"]
    assert all("LAS_T3_DG3_P3" not in s.get("env", {}) for s in runs)
    h9 = json.loads((out / "steps_bundle_h9.json").read_text(encoding="utf-8"))["steps"]
    grid = [s for s in h9 if s["id"].startswith("h9_grid") and "identity" not in s["id"]]
    assert [s["resume_k1"]["output"] for s in grid] == [
        f"{steps.RESUME}/h9_grid/{name}.json" for name in steps.GRID_RUNS
    ]
    assert grid[2]["env"]["R67_FILTER"] == "|bottom|" and steps.R69 in grid[2]["cmd"]
    assert all(s["env"]["R67_V5_SETTING"] == "VB" for s in grid)
    assert counts["H-9"]["derived"] == 812 + 96 + 768
    assert (
        judge.main(
            [
                "overlap",
                "--steps",
                str(out / "steps_h2.json"),
                "--out",
                str(tmp_path / "overlap.json"),
            ]
        )
        == 0
    )


def test_a_changed_stored_source_blocks_its_bundle(tmp_path, monkeypatch) -> None:
    table = _stored_sources(tmp_path)
    table["seedext_V0"] = (table["seedext_V0"][0], "0" * 64)
    monkeypatch.setattr(steps, "STORED_SOURCES", table)
    report = _build(tmp_path, tmp_path / "steps")
    assert list(report["blocked"]) == ["H-8"] and "sha256" in report["blocked"]["H-8"]
    assert report["counts"]["H-8"]["derived"] is None


def test_grid_mirror_rebuilds_the_stored_grid_keys() -> None:
    expected = {"grid_r67_main": 32, "grid_r67_top": 16, "grid_r69_bottom": 16, "grid_r69_top": 16}
    assert {name: len(steps.grid_expected_keys(name)) for name in steps.GRID_RUNS} == expected
    assert {name: steps.grid_expected_runs(name) for name in steps.GRID_RUNS} == dict.fromkeys(
        steps.GRID_RUNS, 192
    )
    assert steps.grid_expected_keys("grid_r69_top")[0] == "screen|top|2.0|level|FL"


def _run_python(code: str, tmp_path: Path) -> dict:
    script = tmp_path / "probe.py"
    script.write_text(code, encoding="utf-8")
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "MKL_THREADING_LAYER": "TBB"}
    done = subprocess.run(
        [sys.executable, "-I", "-B", str(script), str(ROOT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout.strip().splitlines()[-1])


def test_grid_mirror_is_the_r67_job_list(tmp_path) -> None:
    pytest.importorskip("numba", reason="r67 / r51 import the harness (dynamics-dev)")
    code = (
        "import json, sys\n"
        f"sys.path.insert(0, {str(S8)!r})\n"
        "import r67_g1_screen as r67\n"
        "out = {}\n"
        "for fs in ((0.0, 8.0), (2.0, 4.0)):\n"
        "    r67.FS_KN = fs\n"
        "    out[str(fs)] = sorted(r67.all_jobs('screen'))\n"
        "print(json.dumps(out))\n"
    )
    jobs = _run_python(code, tmp_path)
    for name, spec in steps.GRID_RUNS.items():
        substrings = spec["env"].get("R67_FILTER")
        listed = jobs[str(tuple(spec["fs_kN"]))]
        if substrings:
            listed = [j for j in listed if any(p in j for p in substrings.split(","))]
        assert sorted(steps.grid_expected_keys(name)) == listed, name


# ------------------------------------------------------------------------ r79 --keys-file
def test_r79_keys_file_option(tmp_path) -> None:
    pytest.importorskip("numba", reason="r79 imports the harness (dynamics-dev)")
    stored = _write_json(tmp_path / "seedext.json", {"results": [{"key": k} for k in SEEDEXT_KEYS]})
    text = tmp_path / "keys.txt"
    text.write_text("\n".join(SEEDEXT_KEYS) + "\n", encoding="utf-8")
    repeated = tmp_path / "repeated.txt"
    repeated.write_text(SEEDEXT_KEYS[0] + "\n" + SEEDEXT_KEYS[0] + "\n", encoding="utf-8")
    code = (
        "import json, sys\n"
        f"sys.path.insert(0, {str(S8)!r})\n"
        "from pathlib import Path\n"
        "import r79_L3L4_final as f\n"
        f"stored, text, rep = Path({str(stored)!r}), Path({str(text)!r}), Path({str(repeated)!r})\n"
        "keys = f.read_keys_file(stored)\n"
        "try:\n"
        "    f.read_keys_file(rep)\n"
        "    repeated = 'accepted'\n"
        "except SystemExit as exc:\n"
        "    repeated = str(exc)\n"
        "plain = f.plain_jobs(['L2'])\n"
        "bad = ['cand=K1on#' + plain[0], 'cand=current#L2|s3|g6|9999|ref|J2|top|Fs0',\n"
        "       'cand=current#L3|s3|' + plain[0].split('|', 2)[2]]\n"
        "print(json.dumps({'json': keys, 'text': f.read_keys_file(text), 'repeated': repeated,\n"
        "                  'ok': f.keys_file_problems(keys, ['L2']),\n"
        "                  'bad': f.keys_file_problems(bad, ['L2']),\n"
        "                  'default_plain_has_s24': any('|s24|' in k for k in plain)}))\n"
    )
    out = _run_python(code, tmp_path)
    assert out["json"] == SEEDEXT_KEYS == out["text"]
    assert "repeated keys" in out["repeated"]
    assert out["ok"] == [] and len(out["bad"]) == 3
    assert out["default_plain_has_s24"] is False  # the default list keeps refusing seed 24


# ------------------------------------------------------------------------ run_v5 RV1-4 option
def test_run_v5_overlap_reference_option(tmp_path, monkeypatch) -> None:
    reference = tmp_path / "h10_overlap_t_a.json"
    args = run_v5._parse_args(
        ["overlap", "--out", str(tmp_path / "h10.jsonl"), "--overlap-reference", str(reference)]
    )
    assert args.overlap_reference == reference
    for argv in (
        ["overlap", "--out", str(tmp_path / "h10.jsonl")],
        ["main", "--overlap-reference", str(reference)],
        ["overlap", "--overlap-reference", str(run_v5.OVERLAP_REFERENCE_PATH)],
    ):
        with pytest.raises(SystemExit):
            run_v5._parse_args(argv)
    monkeypatch.delenv(run_v5.OVERLAP_REFERENCE_ENV, raising=False)
    assert run_v5.overlap_reference_path() == run_v5.OVERLAP_REFERENCE_PATH
    monkeypatch.setenv(run_v5.OVERLAP_REFERENCE_ENV, str(reference))
    assert run_v5.overlap_reference_path() == reference
    with pytest.raises(RuntimeError, match="no t_a reference"):
        run_v5.overlap_reference()
    reference.write_text(json.dumps({"t_a_s": 31.5, "basis": "x"}), encoding="utf-8")
    assert run_v5.overlap_reference()["t_a_s"] == 31.5


def test_h10_overlap_step_uses_the_new_reference(tmp_path) -> None:
    _build(tmp_path, tmp_path / "steps")
    h10 = json.loads((tmp_path / "steps" / "steps_bundle_h10.json").read_text(encoding="utf-8"))
    overlap = [s for s in h10["steps"] if s["id"] == "h10_overlap"][0]
    assert f"--overlap-reference {steps.RESUME}/h10_overlap_t_a.json" in overlap["cmd"]
    assert "overlap_t_a.json" not in overlap["cmd"].replace("h10_overlap_t_a.json", "")


# ------------------------------------------------------------------------------ rev1 seal / S-1
def test_rev1_and_rev2_seal_check(tmp_path, monkeypatch) -> None:
    assert judge.sealed_rules_check()["problems"] == []
    assert set(judge.sealed_rules_check()["revisions"]) == {
        judge.RULES_REV1_NAME,
        judge.RULES_REV2_NAME,
        judge.RULES_REV3_NAME,
    }
    assert judge.sealed_rules_check(tmp_path)["stop_S1"] is True
    for name, _ in judge.SEALED_REVISIONS:  # both sealed files copied, rev1 seal value wrong
        source = judge.RULES_DIR / name
        (tmp_path / name).write_bytes(source.read_bytes())
        seal_file = source.with_suffix(".sha256")
        (tmp_path / seal_file.name).write_bytes(seal_file.read_bytes())
    assert judge.sealed_rules_check(tmp_path)["problems"] == []
    (tmp_path / "v5_resume_4368_rules_rev1.sha256").write_text("0" * 64 + "  x\n", encoding="utf-8")
    seal = judge.sealed_rules_check(tmp_path)
    assert seal["stop_S1"] is True and len(seal["problems"]) == 1
    crlf = (tmp_path / judge.RULES_REV2_NAME).read_bytes().replace(b"\n", b"\r\n")
    (tmp_path / judge.RULES_REV2_NAME).write_bytes(crlf)  # R2-9: sealed rule files raw only
    assert len(judge.sealed_rules_check(tmp_path)["problems"]) == 2
    monkeypatch.setattr(judge, "RULES_DIR", tmp_path)
    out = tmp_path / "gs.json"
    assert judge.main(["gs", "--harness", str(out), "--out", str(out)]) == 1
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["rules_seal"]["stop_S1"] is True and report["rules_sha256"] == judge.RULES_SHA256


def test_appendix_a_lf_normalisation(tmp_path, monkeypatch) -> None:
    text = (
        "## 부록 A. x\n\n| 파일 | sha256 |\n|---|---|\n"
        f"| `d/a.md` | `{judge.lf_normalised_sha256(b'a' + bytes([10]) + b'b')}` |\n"
        f"| `…/b.md`(봉인 아님) | `{judge.lf_normalised_sha256(b'b')}` |\n\n## next\n"
    )
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / judge.RULES_NAME).write_text(text, encoding="utf-8")
    assert judge.appendix_a_entries(text)[1][0] == "d/b.md"
    root = tmp_path / "root"
    (root / "d").mkdir(parents=True)
    (root / "d" / "a.md").write_bytes(b"a\r\nb")
    (root / "d" / "b.md").write_bytes(b"b")
    monkeypatch.setattr(judge, "RULES_DIR", rules)
    monkeypatch.setattr(judge, "sealed_rules_check", lambda: {"problems": [], "stop_S1": False})
    out = tmp_path / "a.json"
    assert judge.main(["appendix-a", "--root", str(root), "--out", str(out)]) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["crlf_only"] == ["d/a.md"]
    (root / "d" / "b.md").write_bytes(b"c")
    assert judge.main(["appendix-a", "--root", str(root), "--out", str(out)]) == 1


def test_record_conflicts_are_s5() -> None:
    """R2-1: would_block / applied without r4_due = record conflict, 판정 불가 + S-5."""
    for decision in (
        {"would_block": True, "r4_due_without_gate": False, "applied": False},
        {"would_block": False, "r4_due_without_gate": False, "applied": True},
    ):
        block = record.controller_record(_Controller(blocked=True))
        block["slope_clearance_margin"]["order_gate"]["decisions"] = [decision]
        row = judge._class_row("k", block, "patch_or_sink", None, 0, {})
        assert row["class"] == judge.CLASS_UNDECIDABLE
        assert row["stops"] and all(s.startswith("S-5 record conflict") for s in row["stops"])


def test_absent_start_s_is_not_started() -> None:
    """R2-2: a LAS-b block without start_s = not started; no block = 판정 불가."""
    block = record.controller_record(_Controller(blocked=False))
    del block["liftoff_approach_slow"]["start_s"]
    inputs, reason = judge.classification_inputs(block)
    assert reason is None and inputs["start_s"] is None
    del block["liftoff_approach_slow"]
    assert judge.classification_inputs(block)[0] is None


def test_engine_results_read_controller_meta() -> None:
    """R2-3: L2b / L1-R K1 applied value from controller_meta, no c2_setup needed."""
    meta = {
        "slope_clearance_margin": {
            "settings": {"flat_soil_margin_order_gate": True},
            "order_gate": {"enabled": True},
        },
        "liftoff_approach_slow": {"settings": dict(judge.LAS_PRESET)},
    }
    result = {"controller_meta": meta, "expect_controller": {"ok": True}}
    assert judge.chrono_result_problems(result, is_c4_off=False, is_engine=True) == []
    meta["slope_clearance_margin"]["order_gate"]["enabled"] = False
    assert judge.chrono_result_problems(result, is_c4_off=False, is_engine=True)
    assert any(
        "missing" in p for p in judge.chrono_result_problems({}, is_c4_off=False, is_engine=True)
    )
    assert judge._is_engine_row({"argv": ["x/run_S8C.py", "run"]})


# --------------------------------------------------------------------------- keyset / dg3-hash
def test_keyset_r79_and_grid(tmp_path, monkeypatch) -> None:
    stored = _write_json(
        tmp_path / "v5" / "dg3" / "dg3_v4_on.json", {"results": [{"key": k} for k in DG3_KEYS]}
    )
    grid = _write_json(
        tmp_path / "v5" / "grid_vb" / "grid_r67_top.json", _grid_document("grid_r67_top")
    )
    monkeypatch.setattr(
        judge,
        "APPENDIX_B",
        {"dg3/dg3_v4_on.json": _sha(stored), "grid_vb/grid_r67_top.json": _sha(grid)},
    )
    same = _write_json(tmp_path / "new.json", {"results": [{"key": k} for k in reversed(DG3_KEYS)]})
    out = tmp_path / "k.json"
    assert (
        judge.main(
            [
                "keyset",
                "--kind",
                "r79",
                "--new",
                str(same),
                "--stored",
                str(stored),
                "--out",
                str(out),
            ]
        )
        == 0
    )
    short = _write_json(tmp_path / "short.json", {"results": [{"key": DG3_KEYS[0]}]})
    assert (
        judge.main(
            [
                "keyset",
                "--kind",
                "r79",
                "--new",
                str(short),
                "--stored",
                str(stored),
                "--out",
                str(out),
            ]
        )
        == 1
    )
    assert json.loads(out.read_text(encoding="utf-8"))["keys"]["missing_in_new"] == [DG3_KEYS[1]]
    new_grid = _grid_document("grid_r67_top")
    assert (
        judge.main(
            [
                "keyset",
                "--kind",
                "grid",
                "--new",
                str(_write_json(tmp_path / "g.json", new_grid)),
                "--stored",
                str(grid),
                "--out",
                str(out),
            ]
        )
        == 0
    )
    new_grid["results"][0]["runs"].pop()
    new_grid["meta"]["offsets_s"] = "0,0.05"
    assert (
        judge.main(
            [
                "keyset",
                "--kind",
                "grid",
                "--new",
                str(_write_json(tmp_path / "g.json", new_grid)),
                "--stored",
                str(grid),
                "--out",
                str(out),
            ]
        )
        == 1
    )
    problems = json.loads(out.read_text(encoding="utf-8"))["problems"]
    assert any("runs[]" in p for p in problems) and "meta offsets_s differs" in problems
    monkeypatch.setattr(judge, "APPENDIX_B", {"dg3/dg3_v4_on.json": "0" * 64})
    assert (
        judge.main(
            [
                "keyset",
                "--kind",
                "r79",
                "--new",
                str(same),
                "--stored",
                str(stored),
                "--out",
                str(out),
            ]
        )
        == 1
    )  # changed stored file (S-1)


def test_dg3_hash_records_differences(tmp_path) -> None:
    """R3-E4: the top-level commands_sha256 only; R3-D1: the cand= prefix is the same key."""
    h6 = _write_json(
        tmp_path / "h6.json",
        {
            "results": [
                {"key": "cand=current#L2|s0|a", "commands_sha256": "x"},
                {
                    "key": "cand=current#L3|s0|b",
                    "commands_sha256": "y",
                    "base": {"commands_sha256": "z"},
                },
            ]
        },
    )
    h8 = _write_json(
        tmp_path / "h8.json",
        {
            "results": [
                {"key": "L2|s0|a", "commands_sha256": "x"},
                {"key": "cand=current#L3|s0|b", "commands_sha256": "z"},
            ]
        },
    )
    seed = _write_json(
        tmp_path / "seed.json",
        {
            "results": [
                {"key": "cand=current#L2|s3|a", "commands_sha256": "p"},
                {"key": "cand=current#L2|s7|a", "commands_sha256": "q"},
            ]
        },
    )
    noise = _write_json(tmp_path / "noise.json", {"results": [{"key": "L2|s3|a"}]})
    out = tmp_path / "d.json"
    argv = [
        "dg3-hash",
        "--h6",
        str(h6),
        "--h8-vb",
        str(h8),
        "--seedext",
        str(seed),
        "--noise",
        str(noise),
        "--out",
        str(out),
    ]
    assert judge.main(argv) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    pair = report["h6_vs_h8_vb"]
    assert (pair["same"], pair["differ"]) == (1, ["L3|s0|b"])
    seeds = report["seedext_vs_noise"][0]
    assert seeds["keys"] == 1 and seeds["missing"] == ["L2|s3|a"]  # noise line without a hash
    assert report["record_state"] == "기록 불완전"


# ------------------------------------------------------------------------------ RV1-5 anchors
def _job(group: str, case: str, setting: str = "VB") -> dict:
    return {"d1": {"key": f"D1|{group}|{case}", "group": group}, "setting": setting, "eps": 0.0}


def _jsonl(path: Path, lines: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    return path


def _anchor_files(v5: Path) -> list[dict]:
    """Small anchor files: T-1 1 key, T-2 2, d1 rest 1 (H-R-0), Y-Pa 1, s2d_SC rest 1."""
    t1 = [
        {"job": _job("H-R-A", "t1"), "las": {"candidate": "b0"}, "commands_sha256": "t1"},
        {"job": _job("H-R-A", "t1"), "las": {"candidate": "P5r4"}, "commands_sha256": "no"},
    ]
    t2 = [
        {"job": _job("H-R-0", "t2a"), "las": {"candidate": "b0"}, "commands_sha256": "t2a"},
        {"job": _job("H-R-A", "t2b"), "las": {"candidate": "b0"}, "commands_sha256": "t2b"},
        {"job": _job("H-R-0", "err"), "las": {"candidate": "b0"}, "error": "x"},
    ]
    d1 = [
        {"job": _job("H-R-0", "t2a"), "commands_sha256": "old"},
        {"job": _job("H-R-0", "rest"), "commands_sha256": "rest"},
        {"job": _job("H-R-A-stop", "stop"), "commands_sha256": "stop"},
    ]
    ypa = [
        {
            "job": _job("H-S-0", "ypa"),
            "k1": {"sub_bundle": "Y-Pa"},
            "las": {"candidate": "P0"},
            "commands_sha256": "ypa",
        },
        {
            "job": _job("H-S-0", "ypb"),
            "k1": {"sub_bundle": "Y-Pb"},
            "las": {"candidate": "P0"},
            "commands_sha256": "no",
        },
    ]
    sc = [
        {"job": _job("H-S-0", "ypa"), "commands_sha256": "old"},
        {"job": _job("H-S-A", "sc"), "commands_sha256": "sc"},
    ]
    for entry, lines in (
        ("las/las_T1.jsonl", t1),
        ("las/las_T2.jsonl", t2),
        ("d1.jsonl", d1),
        ("las/k1/k1_YP.jsonl", ypa),
        ("soil_defer/s2d_SC.jsonl", sc),
    ):
        _jsonl(v5 / entry, lines)
    return d1


def test_anchor_map_selection_and_pairs(tmp_path, monkeypatch) -> None:
    v5 = tmp_path / "v5"
    _anchor_files(v5)
    monkeypatch.setattr(
        judge, "APPENDIX_B", {e: _sha(v5 / e) for _, e, _ in judge.ANCHOR_SELECTIONS}
    )
    monkeypatch.setattr(
        judge,
        "ANCHOR_SELECTIONS",
        tuple(
            (name, entry, n)
            for (name, entry, _), n in zip(judge.ANCHOR_SELECTIONS, (1, 2, 1, 1, 1), strict=True)
        ),
    )
    keys = {
        case: judge.job_key_of({"job": job})
        for case, job in (
            ("t1", _job("H-R-A", "t1")),
            ("t2a", _job("H-R-0", "t2a")),
            ("rest", _job("H-R-0", "rest")),
            ("ypa", _job("H-S-0", "ypa")),
            ("sc", _job("H-S-A", "sc")),
        )
    }
    h1 = [
        {"job": {**_job("H-R-A", "t1"), "mask": 3}, "commands_sha256": "t1"},
        {"job": _job("H-R-0", "t2a"), "commands_sha256": "changed"},
        {"job": _job("H-R-A-stop", "stop"), "commands_sha256": "stop"},
    ]
    out = tmp_path / "a.json"
    assert (
        judge.main(
            [
                "anchor-map",
                "--v5-dir",
                str(v5),
                "--h1",
                str(_jsonl(tmp_path / "h1.jsonl", h1)),
                "--out",
                str(out),
            ]
        )
        == 0
    )
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["anchors"][keys["t2a"]] == "t2a"  # T-2, not the old d1 line
    assert report["anchors"][keys["ypa"]] == "ypa" and report["anchors"][keys["sc"]] == "sc"
    assert report["h1"]["same"] == 1 and report["h1"]["differ"] == 1
    _jsonl(
        v5 / "las/las_T2.jsonl",
        [
            {"job": _job("H-R-0", "t2a"), "las": {"candidate": "b0"}, "commands_sha256": n}
            for n in ("a", "b")
        ],
    )
    monkeypatch.setattr(
        judge, "APPENDIX_B", {e: _sha(v5 / e) for _, e, _ in judge.ANCHOR_SELECTIONS}
    )
    assert judge.main(["anchor-map", "--v5-dir", str(v5), "--out", str(out)]) == 1
    assert json.loads(out.read_text(encoding="utf-8"))["stop_S7"] is True


def test_job_key_of_is_run_v5_job_key() -> None:
    job = {"case": "R12", "eps": 0.0, "setting": "VB", "mask": 7, "t4h_dir": "x"}
    assert judge.job_key_of({"job": job}) == run_v5.job_key(job)


# ----------------------------------------------------------------------------- RV1-9 imports
def test_import_check(tmp_path) -> None:
    root = tmp_path / "repo"
    scripts = root / "04_scripts"
    (root / "03_src").mkdir(parents=True)
    (root / "05_tests" / "unit").mkdir(parents=True)
    scripts.mkdir()
    (scripts / "runner.py").write_text("import helper\n", encoding="utf-8")
    (scripts / "helper.py").write_text("def f():\n    import os\n", encoding="utf-8")
    (scripts / "loc_anchor_shadow.py").write_text("def install(): pass\n", encoding="utf-8")
    steps_file = _write_json(
        tmp_path / "steps.json",
        {"steps": [{"id": "a", "cmd": "python -I -B 04_scripts/runner.py run", "env": {}}]},
    )
    out = tmp_path / "i.json"
    assert (
        judge.main(
            ["import-check", "--steps", str(steps_file), "--root", str(root), "--out", str(out)]
        )
        == 0
    )
    (scripts / "helper.py").write_text("def f():\n    import loc_anchor_shadow\n", encoding="utf-8")
    assert (
        judge.main(
            ["import-check", "--steps", str(steps_file), "--root", str(root), "--out", str(out)]
        )
        == 1
    )
    _write_json(
        steps_file,
        {
            "steps": [
                {
                    "id": "a",
                    "cmd": "python 04_scripts/runner.py",
                    "env": {"OUTRIGGER_LOC_SHADOW": "1"},
                }
            ]
        },
    )
    (scripts / "helper.py").write_text("", encoding="utf-8")
    assert (
        judge.main(
            ["import-check", "--steps", str(steps_file), "--root", str(root), "--out", str(out)]
        )
        == 1
    )
    assert json.loads(out.read_text(encoding="utf-8"))["env_hits"] == ["a"]


# ---------------------------------------------------------------------------- RV1-7 F<F_min
def test_fmin_time(tmp_path) -> None:
    np = pytest.importorskip("numpy")
    case = tmp_path / "case"
    case.mkdir()
    t = np.round(np.arange(0.0, 20.0, 0.001), 6)
    force = np.full((t.size, 4), 30_000.0)
    force[(t >= 10.5) & (t < 10.6), 2] = judge.F_MIN_N - 1.0  # 100 ms below F_min, RL
    force[(t >= 10.6) & (t < 10.65), 2] = judge.F_MIN_N + 1000.0  # 50 ms more below +2 kN
    force[(t >= 19.0) & (t < 19.5), 0] = 0.0  # outside departure + 8 s
    weight_N = 400_000.0
    crawler = np.where(t < 10.0, 100_000.0, 0.0)
    crawler[(t >= 9.0) & (t < 9.05)] = 0.0  # 50 ms dip: shorter than 0.1 s, not t_D (R2-5)
    np.savez(case / "step_series.npz", t_s=t, F_cyl_N=force, scm_crawler_normal_N=crawler)
    _write_json(case / "result.json", {"p3b": {"weight_N": weight_N}})
    out = tmp_path / "f.json"
    assert judge.main(["fmin-time", "--case", str(case), "--out", str(out)]) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["t_D_s"] == pytest.approx(10.0) and report["window_complete"] is True
    assert report["F_below_F_min"]["ms"] == pytest.approx([0.0, 0.0, 100.0, 0.0])
    assert report["F_below_F_min_plus_2kN"]["ms"] == pytest.approx([0.0, 0.0, 150.0, 0.0])
    assert report["F_below_F_min_plus_2kN"]["max_ms"] == pytest.approx(150.0)
    whole = report["F_below_F_min"]["to_run_end_record_only"]["ms"]
    assert whole == pytest.approx([500.0, 0.0, 100.0, 0.0])  # the 19 s dip, record only
    np.savez(
        case / "step_series.npz",
        t_s=t,
        F_cyl_N=force,
        scm_crawler_normal_N=np.full(t.size, 100_000.0),
    )
    assert judge.main(["fmin-time", "--case", str(case), "--out", str(out)]) == 1  # no t_D
    _write_json(case / "result.json", {"p3b": {}})
    assert judge.main(["fmin-time", "--case", str(case), "--out", str(out)]) == 1


# ---------------------------------------------------------------------- RV1-10 j stroke counts
def test_stroke_exposure_counts(tmp_path) -> None:
    lines = [
        {
            "job": {"d1": {}},
            "d1": {"stroke_max_m": 0.6790},
            "events": [[1.0, "FAULT_STROKE_END:FL"]],
        },
        {"job": {"d1": {}}, "d1": {"stroke_max_m": 0.6848 - 1e-12}, "event_names": []},
        {"job": {"case": "R1"}, "events": []},
    ]
    harness = _jsonl(tmp_path / "h.jsonl", lines)
    r79 = _write_json(
        tmp_path / "r79.json",
        {
            "results": [
                {
                    "key": "a",
                    "base": {"max_motor_stroke_mm": 690.0},
                    "r79": {"max_true_stroke_mm": 679.0, "n_stroke_end_fault": 0},
                }
            ]
        },
    )
    out = tmp_path / "s.json"
    assert (
        judge.main(
            [
                "stroke-exposure",
                "--bundle",
                "X",
                "--harness",
                str(harness),
                str(r79),
                "--out",
                str(out),
            ]
        )
        == 0
    )
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["lines"] == 4
    assert report["s_ref"]["recorded"] == 3 and report["s_ref"]["no_record"] == 1
    assert report["s_ref"]["ge_678_mm"] == 3 and report["s_ref"]["ge_684.8_mm"] == 2
    assert report["piston"]["recorded"] == 1 and report["piston"]["ge_684.8_mm"] == 0
    assert report["FAULT_STROKE_END"] == {"lines": 1, "no_event_record": 0}
    grid = _write_json(
        tmp_path / "g.json", {"results": [{"key": "k", "runs": [{"fault_events": []}]}]}
    )
    assert (
        judge.main(["stroke-exposure", "--bundle", "G", "--harness", str(grid), "--out", str(out)])
        == 0
    )
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["lines"] == 1 and report["s_ref"]["note"] == "기록 없음"


# ---------------------------------------------------------------------- RV1-6 family table
def _blocked_block() -> dict:
    return record.controller_record(_Controller(blocked=True))


class _Controller:
    """The K1-blocked controller meta of ``resume_k1_record.controller_record``."""

    def __init__(self, blocked: bool) -> None:
        decision = {
            "t_loc_s": 10.0,
            "would_block": blocked,
            "r4_due_without_gate": blocked,
            "applied": False,
        }
        self.events = [
            type("E", (), {"t_s": 1.0, "name": "INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order"})()
        ]
        self.config = type(
            "C",
            (),
            {"slope_clearance_margin": type("M", (), {"flat_soil_margin_order_gate": True})()},
        )()
        self._meta = {
            "liftoff_approach_slow": {"settings": dict(judge.LAS_PRESET), "start_s": None},
            "slope_clearance_margin": {
                "settings": {"flat_soil_margin_order_gate": True},
                "order_gate": {"decisions": [decision]},
            },
        }

    def meta(self) -> dict:
        return self._meta


def test_k1_class_with_the_family_table(tmp_path) -> None:
    block = _blocked_block()
    key = "cand=current#L3|s0|g6|5|g6|G1+J1@FR|top|Fs4"
    harness = _write_json(
        tmp_path / "r79.json", {"results": [{"key": key, judge.RECORD_KEY: block}]}
    )
    table = _write_json(
        tmp_path / "family.json", {"rows": [{"key": key, "family": family.FAMILY_PATCH_OR_SINK}]}
    )
    out = tmp_path / "k.json"
    argv = ["k1-class", "--harness", str(harness), "--family-table", str(table), "--out", str(out)]
    assert judge.main(argv) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["counts"] == {judge.CLASS_K1: 1} and report["family_table"]["sha256"]
    assert report["rows"][0]["family_source"] == key
    _write_json(table, {"rows": [{"key": "other", "family": family.FAMILY_RIGID}]})
    assert judge.main(argv) == 1  # not in the table = uniform: S-6
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["counts"] == {judge.CLASS_K1_UNIFORM: 1}


def test_grid_lines_take_the_r2_7_family(tmp_path) -> None:
    """R2-7: grid lines are runs[]; meta.spec + event give the family (else uniform, S-6)."""
    block = _blocked_block()
    grid = {
        "meta": {"spec": judge.GRID_SPEC},
        "results": [
            {
                "key": "screen|top|0.0|level|FL",
                judge.RECORD_KEY: block,
                "runs": [{judge.RECORD_KEY: block, "event": "G4"}],
            }
        ],
    }
    harness = _write_json(tmp_path / "grid.json", grid)
    out = tmp_path / "k.json"
    argv = ["k1-class", "--harness", str(harness), "--out", str(out)]
    assert judge.main(argv) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["runs"] == 1 and report["counts"] == {judge.CLASS_K1: 1}
    assert report["rows"][0]["family_source"] == "R2-7 (meta.spec + event)"
    grid["results"][0]["runs"][0]["event"] = "other"
    _write_json(harness, grid)
    assert judge.main(argv) == 1
    assert json.loads(out.read_text(encoding="utf-8"))["counts"] == {judge.CLASS_K1_UNIFORM: 1}


# ------------------------------------------------------------- Q-U1 = A: settle v2 record
S9 = ROOT / "04_scripts" / "03_control" / "s9"


def _settle_result(*, start_gap: bool = False, mass_scale: float = 1.0) -> dict:
    check = {
        "q_floor_mean_deg": [0.10, -0.20],
        "attitude_error_deg": [0.001, -0.004],
        "pen_plus_gap_mm": [0.0, 0.0, 0.0, 0.0],
        "window_end_s": 5.0,
    }
    if start_gap:
        check["gap_target_mm"] = [40.0, 30.0, 30.0, 30.0]
    return {
        "case": {
            "settle_table_status": "applied",
            "harness_settle_key": "J1|top|0|0",
            "settle_table": {"gap_target_mm": [30.0, 30.0, 30.0, 30.0]},
            "mass_scale": mass_scale,
        },
        "settle": {
            "pen_mm": [-30.2, -29.9, -30.0, -30.1],
            "q_floor_deg": [0.11, -0.21],
            "check": check,
        },
    }


def _settle_table_file(tmp_path: Path) -> Path:
    table = {
        "pad_xy_m": [[2.3, 1.3], [2.3, -1.3], [-2.6, 1.2], [-2.6, -1.2]],
        "hook_harness": {"J1|top|0|0": {"residual_roll_deg": 0.004, "residual_pitch_deg": 0.0}},
    }
    return _write_json(tmp_path / "settle_table.json", table)


def _rejudge_module():
    if str(S9) not in sys.path:
        sys.path.insert(0, str(S9))
    pytest.importorskip("numba", reason="s9_soil_slope imports the harness (dynamics-dev)")
    return importlib.import_module("s9_settle_rejudge")


def test_settle_v2_record_inputs_and_result(tmp_path) -> None:
    rejudge = _rejudge_module()
    table = _settle_table_file(tmp_path)
    result = _settle_result()
    before = json.dumps(result, sort_keys=True)
    record = rejudge.settle_v2_record(result, table)
    assert json.dumps(result, sort_keys=True) == before  # record only: input unchanged
    assert record["status"] == "checked" and record["inputs"]["gap_target_source"] == "table"
    assert record["inputs"]["d_attitude_deg"] == pytest.approx([0.01, -0.01])
    assert record["inputs"]["residual_deg"] == [0.004, 0.0]
    assert record["result"]["attitude_tol_deg"] == pytest.approx([0.006, 0.005])
    loaded = json.loads(table.read_text(encoding="utf-8"))
    check = rejudge.corrected_check(
        result, loaded["hook_harness"]["J1|top|0|0"], loaded["pad_xy_m"]
    )
    assert record["result"]["pen_plus_gap_mm"] == pytest.approx(check["pen_plus_gap_mm"])
    assert record["result"]["ok"] == check["ok"] and record["result"]["gate"] in (
        "judged",
        "settle_check_fail",
    )
    gap = rejudge.settle_v2_record(_settle_result(start_gap=True), table)
    assert gap["inputs"]["gap_target_source"] == "start_gap"
    assert gap["inputs"]["gap_target_mm"][0] == 40.0 and gap["result"]["gap_ok"] is False
    assert (
        rejudge.settle_v2_record(_settle_result(start_gap=True, mass_scale=1.1), table)["result"][
            "gate"
        ]
        == "record_only"
    )
    no_table = _settle_result()
    no_table["case"]["settle_table_status"] = "rigid_reference"
    assert rejudge.settle_v2_record(no_table, table) == {
        "version": rejudge.CHECK_VERSION,
        "status": "no_table_check",
        "settle_table_status": "rigid_reference",
    }
    broken = _settle_result()
    broken["case"]["harness_settle_key"] = "missing"
    assert rejudge.safe_settle_v2_record(broken, table)["status"] == "error"


def test_settle_v2_keys_in_gs(tmp_path) -> None:
    record = {
        "suite": "slope",
        "id": "H1|J1|B|top|flat",
        "v5": {judge.RECORD_KEY: record_block_of_gs(), "controller_tag": judge.TAG_V0},
    }
    assert judge.settle_v2_presence(record) == {"settle_v2.status": False}
    record["settle_v2"] = {"status": "no_table_check"}
    assert judge.settle_v2_presence(record) == {"settle_v2.status": True}
    record["settle_v2"] = {"status": "checked", "inputs": {}, "result": {}}
    missing = [k for k, ok in judge.settle_v2_presence(record).items() if not ok]
    assert len(missing) == len(judge.SETTLE_V2_CHECKED_KEYS)
    harness = _write_json(tmp_path / "u3.json", {"records": [record]})
    out = tmp_path / "gs.json"
    assert judge.main(["gs", "--harness", str(harness), "--out", str(out)]) == 1
    d1_line = {"job": {"d1": {}}, "u3": {"settle_v2": {"status": "no_table_check"}}}
    assert judge.settle_v2_presence(d1_line) == {"u3.settle_v2.status": True}
    assert judge.settle_v2_presence({"suite": "g6", "id": "x"}) == {}


def record_block_of_gs() -> dict:
    return record.controller_record(_Controller(blocked=False))


def test_settle_v2_record_keeps_the_command_hash(tmp_path) -> None:
    """The record is computed after the run: the same case with and without it has the same
    command hash (one harness case run twice, about 40 s)."""
    pytest.importorskip("numba", reason="harness run (dynamics-dev)")
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "MKL_THREADING_LAYER": "TBB"}
    done = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(ROOT / "05_tests" / "unit" / "settle_v2_hash_runner.py"),
            str(ROOT),
            "H1|G1|B|top|flat",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert done.returncode == 0, done.stderr[-2000:]
    out = json.loads(done.stdout.strip().splitlines()[-1])
    assert out["error"] is None and out["with"] == out["without"] and out["with"]
    assert out["settle_v2"]["status"] == "checked" and out["record_fields_settle_v2"] is True


def test_k1_class_has_no_anchor_option(tmp_path) -> None:
    with pytest.raises(SystemExit):
        judge._parser().parse_args(["k1-class", "--anchor", "x", "--out", str(tmp_path / "o")])


# --------------------------------------------------------------------------------- rev3 tests
def _grid_runs(key: str, gates: dict, *, final: str = "ready") -> list[dict]:
    return [
        {
            "event": "FS24",
            "offset_s": o,
            "gates": gates,
            "pass": all(gates.values()),
            "final_phase": final,
            "commands_sha256": f"{key}|{o}",
        }
        for o in (0.0, 0.05)
    ]


def test_rev3_conditional_steps(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(steps, "STORED_SOURCES", _stored_sources(tmp_path))
    out = tmp_path / "steps"
    report = _build(tmp_path, out)
    assert report["blocked"] == {}
    sample = json.loads((out / "steps_bundle_h9_v0_sample.json").read_text(encoding="utf-8"))
    runs = [s for s in sample["steps"] if "identity" not in s["id"]]
    assert len(runs) == 4 and all(s["env"]["R67_V5_SETTING"] == "V0" for s in runs)
    first = steps.grid_expected_keys("grid_r67_main")
    assert f'--keys "{first[0]},{first[-1]}"' in runs[0]["cmd"]
    h2 = json.loads((out / "steps_h2.json").read_text(encoding="utf-8"))
    assert any(s["id"] == runs[0]["id"] for s in h2["steps"])  # the sample always runs
    v0 = json.loads((out / "steps_conditional_h9_grid_v0_768.json").read_text(encoding="utf-8"))
    v0_runs = [s for s in v0["steps"] if "identity" not in s["id"]]
    assert [s["resume_k1"]["output"] for s in v0_runs] == [
        f"{steps.GRID_V0_DIR}/{name}.json" for name in steps.GRID_RUNS
    ]
    assert not any(s["id"].startswith("h9_v0_grid") for s in h2["steps"])  # conditional only
    family = json.loads((out / "steps_conditional_h9_family_f.json").read_text(encoding="utf-8"))
    run_f = family["steps"][1]
    assert run_f["env"]["R67_OFFSETS"].split(",")[-1] == "0.09375"
    assert len(run_f["env"]["R67_OFFSETS"].split(",")) == 16
    assert family["steps"][-1]["resume_k1"]["output"] == steps.FAMILY_F_OUT
    conditional = report["counts"]["conditional"]
    assert conditional["H-9 grid V0 768"]["lines"] == 768
    assert conditional["H-9 family F"]["lines"] == 64


def test_rev3_crlf_only_stored_source(tmp_path, monkeypatch) -> None:
    table = _stored_sources(tmp_path)
    path = tmp_path / steps.V5 / table["seedext_VB"][0]
    lf = path.read_bytes()
    path.write_bytes(lf.replace(b"\n", b"\r\n") if b"\n" in lf else lf + b"\r\n")
    table["seedext_VB"] = (table["seedext_VB"][0], judge.lf_normalised_sha256(path.read_bytes()))
    monkeypatch.setattr(steps, "STORED_SOURCES", table)
    monkeypatch.setattr(steps, "CRLF_ONLY_SOURCES", {})
    report = _build(tmp_path, tmp_path / "steps")
    assert "H-8" not in report["blocked"]
    assert list(report["counts"]["appendix_b_crlf_only"]) == [
        f"{steps.V5}/{table['seedext_VB'][0]}"
    ]


def test_rev3_grid_v0_sample(tmp_path) -> None:
    stored, sample = tmp_path / "stored", tmp_path / "sample"
    for name in judge.GRID_FILES:
        rows = [{"key": f"{name}-{i}", "runs": [{"commands_sha256": f"h{i}"}]} for i in range(3)]
        _write_json(stored / f"{name}.json", {"results": rows})
        _write_json(sample / f"{name}.json", {"results": [rows[0], rows[2]]})
    out = tmp_path / "s.json"
    argv = [
        "grid-v0-sample",
        "--sample-dir",
        str(sample),
        "--stored-dir",
        str(stored),
        "--out",
        str(out),
    ]
    assert judge.main(argv) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["jobs"] == 8 and report["v0_768_required"] is False
    doc = json.loads((sample / "grid_r69_top.json").read_text(encoding="utf-8"))
    doc["results"][1]["runs"][0]["commands_sha256"] = "other"
    _write_json(sample / "grid_r69_top.json", doc)
    assert judge.main(argv) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["v0_768_required"] is True


def test_rev3_family_f_trigger_and_rules(tmp_path) -> None:
    good = dict.fromkeys(("Fmin_after_W", "U57_outside", "fault0", "end_att"), True)
    bad_two = {**good, "Fmin_after_W": False}
    vb, v0 = tmp_path / "vb", tmp_path / "v0"
    for folder, gates in ((vb, bad_two), (v0, good)):
        for name in ("grid_r67_main", "grid_r67_top"):
            offsets = (0.0, 0.05) if name == "grid_r67_main" else (0.025, 0.075)
            rows = [
                {
                    "key": key,
                    "runs": [
                        {
                            "event": "FS24",
                            "offset_s": o,
                            "gates": gates,
                            "pass": all(gates.values()),
                        }
                        for o in offsets
                    ],
                }
                for key in judge.FAMILY_F_KEYS
            ]
            _write_json(folder / f"{name}.json", {"results": rows})
    out = tmp_path / "t.json"
    assert (
        judge.main(
            ["family-f-trigger", "--vb-dir", str(vb), "--v0-dir", str(v0), "--out", str(out)]
        )
        == 0
    )
    assert json.loads(out.read_text(encoding="utf-8"))["trigger"] is True
    lines = []
    for setting in ("V0", "VB"):
        for key in judge.FAMILY_F_KEYS:
            for i in range(16):
                gates = dict(good)
                if setting == "VB" and i < 5:  # 5 VB failures per key vs V0 0: R-1 fails (> 4)
                    gates["U57_outside"] = False
                lines.append(
                    {
                        "setting": setting,
                        "key": key,
                        "offset_s": i * 0.00625,
                        "gates": gates,
                        "final_phase": "ready",
                    }
                )
    path = _jsonl(tmp_path / "f.jsonl", lines)
    assert judge.main(["family-f", "--lines", str(path), "--out", str(out)]) == 1
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["R-1"] == dict.fromkeys(judge.FAMILY_F_KEYS, False) and report["R-2"] is False
    for line in lines:
        if line["setting"] == "VB" and line["gates"]["U57_outside"] is False:
            line["gates"]["U57_outside"] = line["offset_s"] > 0.01  # 2 failures per key
    _jsonl(path, lines)
    assert judge.main(["family-f", "--lines", str(path), "--out", str(out)]) == 0


def test_rev3_ind_las_gate(tmp_path) -> None:
    records = [
        {"case": "a", "controller": "IND", "commands_sha256": "x"},
        {
            "case": "a",
            "controller": "IND_LAS",
            "commands_sha256": "x",
            "liftoff_slow_events": ["INFO_LIFTOFF_SLOW_END:sum"],
        },
        {"case": "b", "controller": "IND", "commands_sha256": "y"},
        {
            "case": "b",
            "controller": "IND_LAS",
            "commands_sha256": "z",
            "liftoff_slow_events": ["INFO_LIFTOFF_SLOW:RL"],
        },
        {"case": "c", "controller": "IND_LAS", "commands_sha256": "w"},
    ]
    path = _write_json(tmp_path / "u6.json", {"records": records})
    out = tmp_path / "i.json"
    assert judge.main(["ind-las", "--harness", str(path), "--out", str(out)]) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert (report["gate_started"], report["gate_not_started"], report["gate_unreadable"]) == (
        1,
        1,
        1,
    )
    assert report["not_started_same_hash"] == 1 and report["record_state"] == "기록 불완전"


def test_rev3_reagg_items(tmp_path) -> None:
    out = tmp_path / "r.json"
    assert judge.main(["reagg-items", "--out", str(out)]) == 0
    rows = json.loads(out.read_text(encoding="utf-8"))["rows"]
    assert {row["bundle"]: row["count"] for row in rows}["C-5 (R3-G1)"] == 6


def test_rev3_gs_hash_and_grid_fields(tmp_path) -> None:
    block = record.controller_record(_Controller(blocked=False))
    r79 = {
        "key": "cand=current#L2|s0|x",
        "seed_index": 0,
        "harness": "g6",
        "inner": "x",
        judge.RECORD_KEY: block,
        "controller_tag": judge.TAG_V0,
        "base": {"commands_sha256": "a"},
    }
    path = _write_json(tmp_path / "r79.json", {"results": [r79]})
    out = tmp_path / "g.json"
    assert judge.main(["gs", "--harness", str(path), "--out", str(out)]) == 1
    assert "commands_sha256" in json.loads(out.read_text(encoding="utf-8"))["files"][0]["missing"]
    r79["commands_sha256"] = "a"
    _write_json(path, {"results": [r79]})
    assert judge.main(["gs", "--harness", str(path), "--out", str(out)]) == 0
    run = {judge.RECORD_KEY: block, "event": "G4", "commands_sha256": "h"}
    grid = {
        "meta": {"spec": judge.GRID_SPEC, "v5_setting": "VB"},
        "results": [
            {
                "key": "screen|top|0.0|level|FL",
                judge.RECORD_KEY: block,
                "controller_tag": judge.TAG_P3,
                "runs": [run],
            }
        ],
    }
    gpath = _write_json(tmp_path / "grid.json", grid)
    assert judge.main(["gs", "--harness", str(gpath), "--out", str(out)]) == 1
    missing = json.loads(out.read_text(encoding="utf-8"))["files"][0]["missing"]
    assert missing == ["runs[].hydraulics_record.extend_bound_check"]
    run["hydraulics_record"] = {"extend_bound_check": {}}
    _write_json(gpath, grid)
    assert judge.main(["gs", "--harness", str(gpath), "--out", str(out)]) == 0


def test_rev3_appendix_b_crlf_pass(tmp_path, monkeypatch) -> None:
    path = _write_json(tmp_path / "v5" / "dg3" / "dg3_v4_on.json", {"results": []})
    lf_sha = _sha(path)
    path.write_bytes(path.read_bytes() + b"\r\n")
    monkeypatch.setattr(
        judge, "APPENDIX_B", {"dg3/dg3_v4_on.json": judge.lf_normalised_sha256(path.read_bytes())}
    )
    monkeypatch.setattr(judge, "CRLF_ONLY_FILES", {})
    entry, problems = judge.appendix_b_problems(path)
    assert problems == [] and entry in judge.CRLF_ONLY_FILES
    assert lf_sha != judge.CRLF_ONLY_FILES[entry]["raw_sha256"]


def test_rev3_r79_top_level_hash(tmp_path) -> None:
    """R3-E4: the top-level hash is the harness-line digest and the log keeps the commands
    (one r79 key run twice, about 3 minutes)."""
    pytest.importorskip("numba", reason="harness run (dynamics-dev)")
    env = {
        **os.environ,
        "PYTHONDONTWRITEBYTECODE": "1",
        "MKL_THREADING_LAYER": "TBB",
        "R79_V5_SETTING": "VB",
        "R72_PATH": "per_leg",
    }
    done = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(ROOT / "05_tests" / "unit" / "r79_hash_runner.py"),
            str(ROOT),
            "cand=current#L2|s0|g6|52|ref|J1|top|Fs0",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=1200,
    )
    assert done.returncode == 0, done.stderr[-2000:]
    out = json.loads(done.stdout.strip().splitlines()[-1])
    assert out["error"] is None and out["base_with"] == out["base_without"]
    assert out["top"] == out["base_with"] and out["top_without"] is None
