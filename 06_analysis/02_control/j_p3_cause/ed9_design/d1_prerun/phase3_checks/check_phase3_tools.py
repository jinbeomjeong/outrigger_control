"""Synthetic checks of the phase 3 changes to the d1_prerun scripts (not project tests).

compare_identity: B-2 --stored-tag-absent, --require-prior (order 4 -> 5), --allowed-from with
r3c_expected / scan_d1_step_rows files, --with-d1-reasons, path markers, --only-common.
scan_d1_step_rows: key-only scan. r3c_run.head_problem: M-5. Synthetic lines only.
"""
import json
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(sys.argv[1])
sys.path.insert(0, str(SCRIPTS))
import compare_identity as ci  # noqa: E402
import r3c_run  # noqa: E402
import scan_d1_step_rows as rows_scan  # noqa: E402

REASON = "INFO_HEAD_PRESSURE_FAULT_REASON:FR:D1_step"
CHECKS = []


def check(name: str, condition: bool) -> None:
    CHECKS.append((name, bool(condition)))


def line(offset: float, *, tag=None, settings=None, sha="a", final="ready", warnings=(),
         marker=None, setting="V0", mask=None) -> dict:
    row = {"job": {"case": "R12", "offset_s": offset, "setting": setting, "mask": mask},
           "commands_sha256": sha * 64, "final_phase": final,
           "event_output": {"warnings": list(warnings)}}
    if tag is not None:
        row["controller_tag"] = tag
    if settings is not None:
        row["d1_settings"] = settings
    if marker is not None:
        row["diag"] = {"two_pressure_file": marker}
    return row


def write(folder: Path, name: str, rows: list[dict]) -> Path:
    path = folder / name
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def run(argv: list[str]) -> tuple[int, dict | None]:
    out = Path(argv[argv.index("--out") + 1])
    code = ci.main(argv)
    return code, json.loads(out.read_text(encoding="utf-8")) if out.exists() else None


ON = {"imu_residual_median_check": True}
TAG = "final_C4G2_LAS_K1"


def check_stored_tag_absent(tmp: Path) -> None:
    stored = write(tmp, "stored.jsonl", [line(0.1), line(0.2), line(0.3, setting="VB")])
    off = write(tmp, "off.jsonl", [line(0.1, tag=TAG), line(0.2, tag=TAG)])
    code, report = run(["--stored", str(stored), "--new", str(off), "--only-setting", "V0",
                        "--expect-switch", "off", "--out", str(tmp / "r1.json")])
    check("B-2 without the option: tag mismatch differs", code == 1
          and report["counts"]["switch_mismatch"] == 2)
    code, report = run(["--stored", str(stored), "--new", str(off), "--only-setting", "V0",
                        "--expect-switch", "off", "--stored-tag-absent", TAG,
                        "--out", str(tmp / "r2.json")])
    check("B-2 with --stored-tag-absent: identical", code == 0
          and report["status"] == "identical" and report["stored_lines_without_tag"] == 2)
    wrong = write(tmp, "wrong.jsonl", [line(0.1, tag=TAG + "_ED8"), line(0.2, tag=TAG)])
    code, report = run(["--stored", str(stored), "--new", str(wrong), "--only-setting", "V0",
                        "--expect-switch", "off", "--stored-tag-absent", TAG,
                        "--out", str(tmp / "r3.json")])
    check("B-2: another tag still differs", code == 1
          and report["counts"]["switch_mismatch"] == 1)
    tagged = write(tmp, "tagged.jsonl", [line(0.1, tag="x"), line(0.2, tag="x")])
    code, report = run(["--stored", str(tagged), "--new", str(off), "--expect-switch", "off",
                        "--stored-tag-absent", TAG, "--out", str(tmp / "r4.json")])
    check("B-2: a stored tag wins over the option", code == 1)


def check_require_prior(tmp: Path) -> None:
    stored = write(tmp, "p_stored.jsonl", [line(0.1), line(0.2)])
    off = write(tmp, "p_off.jsonl", [line(0.1, tag=TAG), line(0.2, tag=TAG)])
    on = write(tmp, "p_on.jsonl", [line(0.1, tag=TAG + "_CM", settings=ON),
                                   line(0.2, tag=TAG + "_CM", settings=ON)])
    four = tmp / "four.json"
    code, report = run(["--stored", str(off), "--new", str(on), "--expect-switch", "on",
                        "--require-prior", str(four), "--out", str(tmp / "five_a.json")])
    check("order: 5 before 4 is refused (not judgeable, no report)", code == 2 and report is None)
    run(["--stored", str(stored), "--new", str(off), "--expect-switch", "off",
         "--stored-tag-absent", TAG, "--out", str(four)])
    code, report = run(["--stored", str(off), "--new", str(on), "--expect-switch", "on",
                        "--require-prior", str(four), "--out", str(tmp / "five_b.json")])
    check("order: 5 after an identical 4 runs", code == 0
          and report["inputs"]["priors"][0]["status"] == "identical")
    code, report = run(["--stored", str(stored), "--new", str(off), "--expect-switch", "off",
                        "--stored-tag-absent", TAG, "--require-prior", str(four),
                        "--out", str(tmp / "two_after_one.json")])
    check("order: 2 shares 1's stored files and runs", code == 0)
    code, report = run(["--stored", str(on), "--new", str(on), "--require-prior", str(four),
                        "--out", str(tmp / "five_c.json")])
    check("order: --stored files the prior never compared are refused", code == 2
          and report is None)
    code, report = run(["--stored", str(off), "--new", str(on), "--expect-switch", "on",
                        "--require-prior", str(four), "--require-prior", str(tmp / "none.json"),
                        "--out", str(tmp / "five_e.json")])
    check("order: every repeated prior must exist", code == 2 and report is None)
    bad_four = tmp / "four_bad.json"
    run(["--stored", str(stored), "--new", str(on), "--expect-switch", "off",
         "--stored-tag-absent", TAG, "--out", str(bad_four)])
    code, report = run(["--stored", str(on), "--new", str(on), "--require-prior",
                        str(bad_four), "--out", str(tmp / "five_d.json")])
    check("order: a differing 4 stops 5", code == 2 and report is None)


def check_allowed_sets(tmp: Path) -> None:
    off = write(tmp, "a_off.jsonl", [line(0.1, tag=TAG, warnings=[REASON]),
                                     line(0.2, tag=TAG)])
    on = write(tmp, "a_on.jsonl", [line(0.1, tag=TAG + "_CM", settings=ON, sha="b",
                                        final="level"),
                                   line(0.2, tag=TAG + "_CM", settings=ON)])
    scan_out = tmp / "scan_off.json"
    code = rows_scan.main(["--rows", str(off), "--group", "same_shape_off", "--out",
                           str(scan_out)])
    scan = json.loads(scan_out.read_text(encoding="utf-8"))
    check("rows scan: one D1_step key", code == 0
          and scan["groups"]["same_shape_off"]["d1_step_lines"] == 1)
    code, report = run(["--stored", str(off), "--new", str(on), "--expect-switch", "on",
                        "--allowed-from", str(scan_out), "--allowed-group", "same_shape_off",
                        "--require-allowed-change", "--out", str(tmp / "c3.json")])
    check("③ with the off-twin scan: as_expected", code == 0
          and report["status"] == "as_expected")
    same = write(tmp, "a_same.jsonl", [line(0.1, tag=TAG + "_CM", settings=ON,
                                            warnings=[REASON]),
                                       line(0.2, tag=TAG + "_CM", settings=ON)])
    code, report = run(["--stored", str(off), "--new", str(same), "--expect-switch", "on",
                        "--allowed-from", str(scan_out), "--allowed-group", "same_shape_off",
                        "--require-allowed-change", "--out", str(tmp / "c3b.json")])
    check("③: an allowed job that did not change differs", code == 1
          and report["counts"]["allowed_unchanged"] == 1)
    expected = {"groups": {"r3c_expected": {"d1_step_keys": [json.dumps(
        {"case": "R12", "offset_s": 0.1, "setting": "V0"}, sort_keys=True)]}}}
    expected_path = tmp / "r3c_expected.json"
    expected_path.write_text(json.dumps(expected), encoding="utf-8")
    code, report = run(["--stored", str(off), "--new", str(on), "--expect-switch", "on",
                        "--allowed-from", str(expected_path), "--allowed-group",
                        "r3c_expected", "--require-allowed-change", "--out",
                        str(tmp / "c6.json")])
    check("⑥②: the expected-job file is an allowed set (mask ignored)", code == 0)
    code, report = run(["--stored", str(stored_scan_input(tmp)), "--new", str(on),
                        "--out", str(tmp / "c_none.json")])
    check("no allowed set: any change differs", code == 1)


def stored_scan_input(tmp: Path) -> Path:
    return write(tmp, "n_stored.jsonl", [line(0.1, tag=TAG), line(0.2, tag=TAG)])


def check_r3c_gates(tmp: Path) -> None:
    c9 = tmp / "wt_c9"
    diag = tmp / "wt_diag"
    two = c9 / "03_src" / "two_pressure.py"
    two_diag = diag / "03_src" / "two_pressure.py"
    plain = write(tmp, "g_plain.jsonl", [line(0.1, marker=str(two), warnings=[REASON]),
                                         line(0.2, marker=str(two))])
    traced = write(tmp, "g_trace.jsonl", [line(0.1, marker=str(two_diag)),
                                          line(0.2, marker=str(two_diag))])
    code, report = run(["--stored", str(plain), "--new", str(traced), "--out",
                        str(tmp / "g1.json")])
    check("③ ≡ ② without D1 reasons: identical", code == 0)
    code, report = run(["--stored", str(plain), "--new", str(traced), "--with-d1-reasons",
                        "--out", str(tmp / "g2.json")])
    check("③ ≡ ② with D1 reasons: differs", code == 1
          and report["differing"][0]["fields"] == ["d1_info_reasons"])
    code, report = run(["--stored", str(plain), "--new", str(traced), "--stored-path-under",
                        str(c9), "--new-path-under", str(diag), "--out", str(tmp / "g3.json")])
    check("path markers under the right worktrees: identical", code == 0)
    code, report = run(["--stored", str(plain), "--new", str(traced), "--stored-path-under",
                        str(diag), "--out", str(tmp / "g4.json")])
    check("a path marker outside: differs", code == 1
          and report["counts"]["path_marker_problems"] == 2)
    many = write(tmp, "g_many.jsonl", [line(0.1, marker=str(two), warnings=[REASON]),
                                       line(0.2, marker=str(two)), line(0.3), line(0.4)])
    code, report = run(["--stored", str(plain), "--new", str(many), "--only-common",
                        "--expect-compared", "2", "--out", str(tmp / "g5.json")])
    check("② ≡ R3b overlap: identical on the common jobs", code == 0
          and report["counts"]["compared"] == 2)
    code, report = run(["--stored", str(plain), "--new", str(many), "--only-common",
                        "--expect-compared", "5", "--out", str(tmp / "g6.json")])
    check("overlap of another size: not judgeable", code == 2)
    twice = write(tmp, "g_twice.jsonl", [line(0.3), line(0.4)])
    code, report = run(["--stored", str(plain), "--new", str(many), "--new", str(twice),
                        "--only-common", "--expect-compared", "2", "--out",
                        str(tmp / "g7.json")])
    check("overlap: a repeat outside the common jobs is out of scope", code == 0)
    code, report = run(["--stored", str(plain), "--new", str(many), "--new", str(plain),
                        "--only-common", "--expect-compared", "2", "--out",
                        str(tmp / "g8.json")])
    check("overlap: a repeat of a common job is not judgeable", code == 2)


def check_head_problem() -> None:
    head = "a" * 40
    check("M-5 same head, clean", r3c_run.head_problem({"head": head, "is_clean": True}, head,
                                                       "start") is None)
    check("M-5 another head", r3c_run.head_problem({"head": "b" * 40, "is_clean": True}, head,
                                                   "start") is not None)
    check("M-5 tracked change", r3c_run.head_problem({"head": head, "is_clean": False}, head,
                                                     "end") is not None)
    check("M-5 git failure is no clean tree", r3c_run.head_problem(
        {"head": None, "is_clean": None}, head, "end") is not None)
    check("M-5 short id refused", r3c_run.FULL_COMMIT_PATTERN.fullmatch("a" * 8) is None)


def main() -> None:
    with tempfile.TemporaryDirectory(dir=sys.argv[2]) as name:
        tmp = Path(name)
        for step in (check_stored_tag_absent, check_require_prior, check_allowed_sets,
                     check_r3c_gates):
            folder = tmp / step.__name__
            folder.mkdir()
            step(folder)
    check_head_problem()
    for name, is_ok in CHECKS:
        print(("ok  " if is_ok else "FAIL"), name)
    print(json.dumps({"checks": len(CHECKS), "failed": sum(not ok for _, ok in CHECKS)}))


if __name__ == "__main__":
    main()
