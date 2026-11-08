"""FB targeted-run judge (sealed ``fb_targeted_rules.md`` 4 C-1 .. C-10, 6 H-2 .. H-4, with
the sealed addendum ``fb_targeted_rules_rev1.md``).

Reads ``v5/fb/fb_F<n>.jsonl`` (``fb_targeted.py``), pairs LF with L by key (F-2: L = the stored
``v5/las/las_T1.jsonl`` / ``las_T2.jsonl`` b0 act line of the key) and writes the judgement
draft ``06_analysis/02_control/verif_matrix/fb_judgement.md``. Values only from the lines; no
run here.

Readings of the rules text (fixed by rev1 2 I-1 .. I-8; stated in the draft too):
  * C-2 (a) "L pass -> LF fail": ``d1.verdict`` "pass" -> "fail" (``allowed_stop`` is not
    "fail"; such pairs are listed); "P3-2 / G6-2 new failure" = an LF fail item whose name
    starts with ``P3-2`` or ``G6-2`` that L does not fail.
  * C-2 (c) / C-4 event names = the keys of ``event_names`` (``run_m1.event_names``: the
    part before ``:``); "new" = in LF, not in L, prefix ``FAULT`` / ``WARN``.
  * C-1 / C-9 "VB (eta 0.85)" = setting VB with ``eta_v`` absent (the 0.85 default) or 0.85.
  * C-6 "within 1.0 s after the first TOUCH period" = the first cut time minus the time of
    the first period that ended in TOUCH, in [0, 1.0] s.
  * C-10 attitude change "size" = hypot(roll change, pitch change) over the window; the
    per-axis values are listed as well.
  * C-4 (I-6): the pairs whose event sets differ are left out of the READY check and
    counted per bundle in the details.
  * F-4 verdict case 1 is ``R2ra`` (decision ``reanchor_on``, rev1 1).

Missing values never pass: a line without ``saturation_s`` breaks C-1 / C-5; a criterion is
complete only when the paired keys equal the expected key set; C-4 without a judged pair is
incomplete; the G-3 family must be the 8 keys. The lines of one bundle must carry one run
identity (``fb.identity``: commit and tool sha256); the stored F-2 L lines are not ours and are
listed apart. H-1 (``fb_targeted.sealed_check``) runs first; the draft records the measured
sha256 of the rules, rev1 and the design copy.

Usage (dynamics-dev python, project root):
  python -I -B 04_scripts/04_hydraulic/coupled/fb_judge.py [--out-dir DIR] [--md PATH]
      [--json PATH]
Exit codes: 0 adoption recommended, 1 not met or incomplete, 2 input error (H-1 included).
The last stdout line is JSON.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fb_targeted as ft  # noqa: E402

JUDGEMENT_PATH = ft.RULES_DIR / "fb_judgement.md"
JUDGED_BUNDLES = ("F-1", "F-2", "F-3", "F-4")
"""Rules 4: C-2 / C-4 / C-9 cover F-1 .. F-4."""
D1_STROKE_BUNDLES = ("F-2", "F-3", "F-4")
SATURATION_LIMIT_S = 0.01
FAMILY_F_MIN_N = 10.4e3
READY_MAX_DELTA_S = 5.0
READY_MEDIAN_DELTA_S = 2.5
ETA80_LEVEL_GE3_S = 0.01
ETA80_TOUCH_SAT_S = 1.0
ETA80_COUNT = 14
ETA70_CUT_WINDOW_S = 1.0
ETA70_COUNT = 4
STROKE_INCREASE_M = 1.0e-3
OPEN_LOOP_SPREAD_MM = 1.0
OPEN_LOOP_ATTITUDE_MARGIN_DEG = 0.05
OPEN_LOOP_VB_COUNT = 3
SCALE_REPORT_BELOW = 0.8947
"""Rules 4 last bullet: report the smallest s of a run whose budget a detection cut."""
FAMILY_KEY_COUNT = 8
"""Rules 4 C-3: the G-3 family of F-2 T-1."""
NEW_EVENT_PREFIXES = ("FAULT", "WARN")
FAILED_ITEM_PREFIXES = ("P3-2", "G6-2")
REFERENCE = "L"
CANDIDATE = "LF"
LAS_PATH_NOTE = (
    "LAS-b 경로: 규칙 3.1절(80행)에 따라 래퍼(`las_targeted.install`) 대신 병합된 03_src "
    "LAS-b(bacb2d2, R8 프리셋 기본 켬, b0 값)를 썼다. 실행마다 프리셋·실행 제어기의 LAS-b "
    "켬과 b0 값을 단언했고, FB 래퍼만 설치했다. F-0 C-7(L 해시 = 저장 `las_T1` b0 해시, "
    "LF-off = L)로 재현 조건을 다시 확인했다. 이 대체는 사후 변경 공개 대상이 아니다. "
    "`las` 블록은 제어기 meta `liftoff_approach_slow`에서 만들었다(`s7p_first`는 없음, "
    "`start_rho`·`start_rho_prev`를 더함)."
)
"""Rules 3.1 line 80: the judgement states the replacement of the wrapper."""


# ------------------------------------------------------------------------------- reading
def read_lines(path: Path) -> list[dict]:
    """Error-free lines of a jsonl file (``[]`` when it does not exist)."""
    if not path.exists():
        return []
    lines = []
    for text in path.read_text(encoding="utf-8").splitlines():
        record = json.loads(text)
        if "error" not in record:
            lines.append(record)
    return lines


def load_stored_reference(paths) -> dict[str, dict]:
    """Key -> stored LAS-b ``b0`` act line (rules 3.2 F-2 L, C-7 stored hash)."""
    stored = {}
    for path in paths:
        for record in read_lines(Path(path)):
            las = record.get("las") or {}
            if las.get("candidate") == "b0" and las.get("mode") == "act":
                stored[las["key"]] = record
    return stored


def lines_by_key(lines: list[dict]) -> dict[str, dict[str, dict]]:
    """Key -> candidate -> line (a later line of the same label replaces an earlier one)."""
    out: dict[str, dict[str, dict]] = {}
    for record in lines:
        fb = record["fb"]
        out.setdefault(fb["key"], {})[fb["candidate"]] = record
    return out


def reference_and_candidate(bundle: str, key: str, by_candidate: dict[str, dict],
                            stored: dict[str, dict]) -> tuple[dict, dict] | None:
    """(L, LF) of a key of a judged bundle, None while one is missing (or not judged)."""
    if bundle not in JUDGED_BUNDLES:
        return None
    candidate = by_candidate.get(CANDIDATE)
    reference = stored.get(key) if bundle == "F-2" else by_candidate.get(REFERENCE)
    if candidate is None or reference is None:
        return None
    return reference, candidate


# ------------------------------------------------------------------------------- line values
def event_set(line: dict) -> set[str]:
    return set(line.get("event_names") or {})


def new_events(reference: dict, candidate: dict) -> list[str]:
    """FAULT / WARN names of LF that L does not have."""
    names = event_set(candidate) - event_set(reference)
    return sorted(name for name in names if name.startswith(NEW_EVENT_PREFIXES))


def ready_time_s(line: dict) -> float | None:
    d1 = line.get("d1")
    if d1 is not None:
        return d1.get("t_ready_s")
    return ((line.get("values") or {}).get("times") or {}).get("t_first_ready_s")


def is_eta85_vb(line: dict) -> bool:
    job = line["job"]
    return job["setting"] == "VB" and job.get("eta_v") in (None, 0.85)


def is_eta(line: dict, eta: float) -> bool:
    job = line["job"]
    eta_v = job.get("eta_v")
    return job["setting"] == "VB" and eta_v is not None and abs(eta_v - eta) < 1e-9


def cut_list(line: dict) -> list[dict]:
    return ((line.get("fb") or {}).get("budget") or {}).get("cuts") or []


def has_cut_event(line: dict) -> bool:
    return ft.CUT_EVENT in event_set(line) or bool(cut_list(line))


def saturation_s(line: dict, phase: str = "all") -> float | None:
    return (((line.get("fb") or {}).get("saturation_s") or {}).get(phase) or {}).get("any_s")


def level_ge3_longest_s(line: dict) -> float | None:
    return ((line.get("fb") or {}).get("u9_values") or {}).get("longest_ge3_s")


def c2_violations(reference: dict, candidate: dict) -> list[str]:
    """C-2 (a) .. (c) of one pair (texts; empty = no violation)."""
    out = []
    ref_d1, cand_d1 = reference.get("d1"), candidate.get("d1")
    if ref_d1 is not None and cand_d1 is not None:
        if ref_d1["verdict"] == "pass" and cand_d1["verdict"] == "fail":
            out.append(f"(a) pass -> fail {cand_d1['fail_items']}")
        new_items = sorted(set(cand_d1["fail_items"]) - set(ref_d1["fail_items"]))
        for item in new_items:
            if item.startswith(FAILED_ITEM_PREFIXES):
                out.append(f"(a) new {item} failure")
    elif reference["final_phase"] == "ready" and candidate["final_phase"] != "ready":
        out.append(f"(b) final ready -> {candidate['final_phase']}")
    out += [f"(c) new {name}" for name in new_events(reference, candidate)]
    return out


# ------------------------------------------------------------------------------- criteria
@dataclass
class Criterion:
    """One row of rules 4."""

    name: str
    title: str
    passed: bool | None = None
    """None = incomplete (lines missing)."""
    summary: str = ""
    details: list[str] = field(default_factory=list)


def _status(is_complete: bool, failures: list) -> bool | None:
    if failures:
        return False
    return True if is_complete else None


@dataclass
class Data:
    """All lines the judge reads."""

    bundles: dict[str, dict[str, dict[str, dict]]]
    stored: dict[str, dict]
    family_keys: list[str]
    expected_keys: dict[str, list[str]]

    def pairs(self, bundles=JUDGED_BUNDLES) -> list[tuple[str, str, dict, dict]]:
        out = []
        for bundle in bundles:
            for key, by_candidate in self.bundles.get(bundle, {}).items():
                pair = reference_and_candidate(bundle, key, by_candidate, self.stored)
                if pair is not None:
                    out.append((bundle, key, *pair))
        return out

    def candidate_lines(self, bundles=JUDGED_BUNDLES, name: str = CANDIDATE) -> list[tuple]:
        return [(bundle, key, lines[name]) for bundle in bundles
                for key, lines in self.bundles.get(bundle, {}).items() if name in lines]

    def missing_pairs(self, bundles=JUDGED_BUNDLES) -> int:
        """Keys whose pair is missing plus paired keys nobody expected; a bundle without
        expected keys counts 1 (0 = the paired key set equals the expected one everywhere)."""
        count = 0
        for bundle in bundles:
            expected = set(self.expected_keys.get(bundle, []))
            paired = {key for _, key, _, _ in self.pairs((bundle,))}
            count += len(expected ^ paired) + (0 if expected else 1)
        return count


def _exceeds(value: float | None, limit: float) -> bool:
    """A missing value is a violation (never a pass)."""
    return value is None or value > limit


def c1(data: Data) -> Criterion:
    lines = [(b, k, line) for b, k, line in data.candidate_lines() if is_eta85_vb(line)]
    failures = [f"{b} {k}: {saturation_s(line)} s" for b, k, line in lines
                if _exceeds(saturation_s(line), SATURATION_LIMIT_S)]
    present = [saturation_s(line) for _, _, line in lines if saturation_s(line) is not None]
    worst = max(present, default=None)
    return Criterion("C-1", "eta 0.85 포화 제거", _status(data.missing_pairs() == 0, failures),
                     f"VB eta 0.85 LF {len(lines)}줄, 최대 {worst} s, 초과 {len(failures)}",
                     failures)


def c2(data: Data) -> Criterion:
    pairs = data.pairs()
    failures = [f"{b} {k}: {v}" for b, k, ref, cand in pairs for v in c2_violations(ref, cand)]
    notes = []
    for bundle, key, ref, cand in pairs:
        if not (ref.get("d1") and cand.get("d1")):
            continue
        change = (ref["d1"]["verdict"], cand["d1"]["verdict"])
        if change[0] != change[1] and change != ("pass", "fail"):
            notes.append(f"참고(위반 아님) {bundle} {key}: {change[0]} -> {change[1]}")
    details = failures + notes
    return Criterion("C-2", "판정", _status(data.missing_pairs() == 0, failures),
                     f"짝 {len(pairs)}, 위반 {len(failures)}", details)


def c3(data: Data) -> Criterion:
    found = [(key, data.bundles.get("F-2", {}).get(key, {}).get(CANDIDATE))
             for key in data.family_keys]
    failures = [f"{key}: {line['d1']['F_judged_min_N'] / 1e3:.3f} kN" for key, line in found
                if line is not None and (line["d1"]["F_judged_min_N"] or 0.0) < FAMILY_F_MIN_N]
    present = [line for _, line in found if line is not None]
    smallest = min((line["d1"]["F_judged_min_N"] or 0.0 for line in present), default=None)
    present_keys = {key for key, line in found if line is not None}
    is_complete = (len(data.family_keys) == FAMILY_KEY_COUNT
                   and present_keys == set(data.family_keys))
    return Criterion("C-3", "계열 최소 힘", _status(is_complete, failures),
                     f"{len(present)}/{len(data.family_keys)}키, 최소 "
                     f"{None if smallest is None else round(smallest / 1e3, 3)} kN", failures)


def c4(data: Data) -> Criterion:
    deltas, different, failures = [], [], []
    for bundle, key, ref, cand in data.pairs():
        t_ref, t_cand = ready_time_s(ref), ready_time_s(cand)
        if t_ref is None or t_cand is None:
            continue
        if event_set(ref) != event_set(cand):
            different.append(f"{bundle} {key}: dt {t_cand - t_ref:+.1f} s, 사건 차 "
                             f"+{sorted(event_set(cand) - event_set(ref))} "
                             f"-{sorted(event_set(ref) - event_set(cand))}")
            continue
        delta = t_cand - t_ref
        deltas.append(delta)
        if delta > READY_MAX_DELTA_S:
            failures.append(f"{bundle} {key}: dt {delta:+.1f} s")
    median = statistics.median(deltas) if deltas else None
    if median is not None and median > READY_MEDIAN_DELTA_S:
        failures.append(f"중앙값 {median:+.2f} s > {READY_MEDIAN_DELTA_S}")
    summary = (f"같은 사건 집합 {len(deltas)}짝, 중앙값 "
               f"{None if median is None else round(median, 2)} s, 최대 "
               f"{None if not deltas else round(max(deltas), 2)} s, 집합이 다른 짝 "
               f"{len(different)}")
    # rev1 4 (I-6): the pairs left out for a different event set, counted per bundle.
    details = failures + [f"집합 다름으로 빠진 짝 {bundle}: "
                          f"{sum(text.startswith(f'{bundle} ') for text in different)}"
                          for bundle in JUDGED_BUNDLES]
    details += [f"집합 다름(READY 판정 제외) {text}" for text in different]
    # No judged pair is no evidence: incomplete, not a pass.
    is_complete = data.missing_pairs() == 0 and bool(deltas)
    return Criterion("C-4", "READY", _status(is_complete, failures), summary, details)


def c5(data: Data) -> Criterion:
    lines = [(k, line) for _, k, line in data.candidate_lines(("F-1",)) if is_eta(line, 0.80)]
    failures = []
    for key, line in lines:
        level, touch = level_ge3_longest_s(line), saturation_s(line, ft.PHASE_TOUCH)
        if _exceeds(level, ETA80_LEVEL_GE3_S):
            failures.append(f"{key}: LEVEL k>=3 최장 {level} s")
        if _exceeds(touch, ETA80_TOUCH_SAT_S):
            failures.append(f"{key}: TOUCH 포화 {touch} s")
    return Criterion("C-5", "eta 0.80", _status(len(lines) == ETA80_COUNT, failures),
                     f"{len(lines)}/{ETA80_COUNT}줄, 위반 {len(failures)}", failures)


def c6(data: Data) -> Criterion:
    lines = [(k, line) for _, k, line in data.candidate_lines(("F-1",)) if is_eta(line, 0.70)]
    failures, details = [], []
    for key, line in lines:
        budget = (line.get("fb") or {}).get("budget") or {}
        cuts, t_touch = cut_list(line), budget.get("t_first_touch_s")
        delay = None if not cuts or t_touch is None else cuts[0]["t_s"] - t_touch
        details.append(f"{key}: 첫 깎기 {None if not cuts else cuts[0]} 첫 TOUCH {t_touch} "
                       f"지연 {delay}")
        if delay is None or not 0.0 <= delay <= ETA70_CUT_WINDOW_S + ft.TIME_TOLERANCE_S:
            failures.append(f"{key}: 깎기 지연 {delay}")
        level = level_ge3_longest_s(line)
        if level is None or level > ETA80_LEVEL_GE3_S:
            failures.append(f"{key}: LEVEL k>=3 최장 {level} s")
    return Criterion("C-6", "eta 0.70", _status(len(lines) == ETA70_COUNT, failures),
                     f"{len(lines)}/{ETA70_COUNT}줄, 위반 {len(failures)}", failures + details)


def check_c7(f0_lines: list[dict], stored_t1: dict[str, dict]) -> dict:
    """C-7: LF-off hash = L hash (both keys), L hash = stored b0 hash (VB key)."""
    by_key = lines_by_key(f0_lines)
    problems, rows = [], []
    for key in ft.F0_KEYS:
        lines = by_key.get(key, {})
        ref, off = lines.get(REFERENCE), lines.get("LF-off")
        if ref is None or off is None:
            absent = [name for name in (REFERENCE, "LF-off") if name not in lines]
            problems.append(f"{key}: missing {absent}")
            continue
        rows.append(f"{key}: L {ref['commands_sha256'][:12]} LF-off {off['commands_sha256'][:12]}")
        if ref["commands_sha256"] != off["commands_sha256"]:
            problems.append(f"{key}: LF-off hash != L hash")
        if "|VB|" in key:
            stored = stored_t1.get(key)
            stored_hash = None if stored is None else stored["commands_sha256"]
            rows.append(f"{key}: stored b0 {str(stored_hash)[:12]}")
            if stored_hash != ref["commands_sha256"]:
                problems.append(f"{key}: L hash != stored b0 hash {stored_hash}")
    return {"pass": not problems, "problems": problems, "rows": rows}


def c7(data: Data) -> Criterion:
    lines = [line for lines in data.bundles.get("F-0", {}).values() for line in lines.values()]
    result = check_c7(lines, data.stored)
    is_complete = not any("missing" in text for text in result["problems"])
    failures = [text for text in result["problems"] if "missing" not in text]
    return Criterion("C-7", "스위치", _status(is_complete, failures),
                     "일치" if result["pass"] else f"문제 {len(result['problems'])}",
                     result["problems"] + result["rows"])


def c8(data: Data) -> Criterion:
    pairs = [(b, k, r, c) for b, k, r, c in data.pairs(D1_STROKE_BUNDLES)
             if r.get("d1") and c.get("d1")]
    increases = [(b, k, c["d1"]["stroke_max_m"] - r["d1"]["stroke_max_m"]) for b, k, r, c in pairs]
    failures = [f"{b} {k}: +{inc * 1e3:.3f} mm" for b, k, inc in increases
                if inc > STROKE_INCREASE_M]
    worst = max((inc for _, _, inc in increases), default=None)
    return Criterion("C-8", "행정", _status(data.missing_pairs(D1_STROKE_BUNDLES) == 0, failures),
                     f"D-1 짝 {len(pairs)}, 최대 증가 "
                     f"{None if worst is None else round(worst * 1e3, 3)} mm", failures)


def c9(data: Data) -> Criterion:
    lines = [(b, k, line) for b, k, line in data.candidate_lines()
             if line["job"]["setting"] == "V0" or is_eta85_vb(line)]
    failures = [f"{b} {k}: {cut_list(line)}" for b, k, line in lines if has_cut_event(line)]
    return Criterion("C-9", "거짓 검출", _status(data.missing_pairs() == 0, failures),
                     f"V0·VB eta 0.85 LF {len(lines)}줄, 깎기 {len(failures)}", failures)


def _row_of(key: str) -> str:
    return key.rsplit("|", 2)[0]


def c10(data: Data) -> Criterion:
    by_key = data.bundles.get("F-5", {})
    v0_attitude = {_row_of(key): lines["OL-L"]["fb"]["open_loop"]["attitude_change_deg"]
                   for key, lines in by_key.items()
                   if "|V0|" in key and "OL-L" in lines and "open_loop" in lines["OL-L"]["fb"]}
    failures, details, count = [], [], 0
    for key, lines in sorted(by_key.items()):
        line = lines.get("OL-LF")
        if "|VB|" not in key or line is None or "open_loop" not in line["fb"]:
            continue
        count += 1
        window = line["fb"]["open_loop"]
        reference = v0_attitude.get(_row_of(key))
        details.append(f"{key}: 행정 차 {window['stroke_spread_mm']:.3f} mm, 자세 "
                       f"{window['attitude_change_deg']:.3f} deg (roll "
                       f"{window['roll_change_deg']:+.3f}, pitch {window['pitch_change_deg']:+.3f})"
                       f", V0 OL-L {reference}")
        if window["stroke_spread_mm"] > OPEN_LOOP_SPREAD_MM:
            failures.append(f"{key}: 행정 차 {window['stroke_spread_mm']:.3f} mm")
        attitude = window["attitude_change_deg"]
        if reference is None or attitude > reference + OPEN_LOOP_ATTITUDE_MARGIN_DEG:
            failures.append(f"{key}: 자세 {attitude:.3f} > V0 {reference} + 0.05")
    is_complete = count == OPEN_LOOP_VB_COUNT and len(v0_attitude) == OPEN_LOOP_VB_COUNT
    return Criterion("C-10", "열린 루프 상당", _status(is_complete, failures),
                     f"VB {count}/{OPEN_LOOP_VB_COUNT}, 위반 {len(failures)}", failures + details)


CRITERIA = (c1, c2, c3, c4, c5, c6, c7, c8, c9, c10)


# ------------------------------------------------------------------------------- stops
def error_lines(out_dir: Path) -> dict[str, list[str]]:
    """Bundle -> labels of the error sidecar lines (H-3)."""
    out = {}
    for bundle in ft.BUNDLES:
        path = out_dir / f"fb_{bundle.replace('-', '')}_errors.jsonl"
        if not path.exists():
            continue
        labels = []
        for text in path.read_text(encoding="utf-8").splitlines():
            fb = json.loads(text).get("fb") or {}
            labels.append(f"{fb.get('candidate')} {fb.get('key')}")
        out[bundle] = labels
    return out


def stop_report(data: Data, out_dir: Path) -> list[str]:
    c7_result = c7(data)
    lines = [f"H-2 (F-0 C-7): {'통과' if c7_result.passed else c7_result.summary}"]
    errors = error_lines(out_dir)
    for bundle, labels in errors.items():
        twice = sorted({label for label in labels if labels.count(label) >= 2})
        lines.append(f"H-3 {bundle}: 오류 줄 {len(labels)}, 두 번 실패 {twice or '없음'}")
    if not errors:
        lines.append("H-3: 오류 줄 없음")
    for bundle in JUDGED_BUNDLES:
        count = sum(len(c2_violations(r, c)) for _, _, r, c in data.pairs((bundle,)))
        stop = " (멈춤 조건)" if count >= ft.C2_STOP_COUNT else ""
        lines.append(f"H-4 {bundle}: C-2 위반 {count}{stop}")
    return lines


def detection_scale_report(data: Data) -> list[str]:
    """Rules 4 last bullet: runs a detection cut, with their smallest scale s."""
    out = []
    for bundle, key, line in data.candidate_lines(ft.BUNDLES, CANDIDATE) + \
            data.candidate_lines(("F-5",), "OL-LF"):
        budget = (line.get("fb") or {}).get("budget") or {}
        if budget.get("cuts"):
            note = " (< 0.8947)" if budget["min_scale"] < SCALE_REPORT_BELOW else ""
            out.append(f"{bundle} {key}: 깎기 {len(budget['cuts'])}, 최종 Q_b "
                       f"{budget['Q_b_final_L_min']:.2f} L/min, "
                       f"최소 s {budget['min_scale']:.4f}{note}")
    return out


# ------------------------------------------------------------------------------- identity
def _identity_tuple(line: dict) -> tuple | None:
    identity = (line.get("fb") or {}).get("identity")
    if not identity:
        return None
    return (identity.get("git_head"), tuple(sorted((identity.get("sha256") or {}).items())))


def bundle_identities(data: Data) -> dict[str, dict]:
    """Bundle -> its commits, tool-hash sets and lines without an identity (our lines only;
    the stored F-2 L lines are counted apart in ``stored_reference_lines``)."""
    out = {}
    for bundle in ft.BUNDLES:
        lines = [line for by_candidate in data.bundles.get(bundle, {}).values()
                 for line in by_candidate.values()]
        if not lines:
            continue
        tuples = [_identity_tuple(line) for line in lines]
        known = [value for value in tuples if value is not None]
        out[bundle] = {"lines": len(lines), "without_identity": tuples.count(None),
                       "commits": sorted({commit for commit, _ in known}),
                       "tool_hash_sets": len({hashes for _, hashes in known}),
                       "dirty_lines": sum(bool(((line.get("fb") or {}).get("identity") or {})
                                               .get("git_dirty")) for line in lines)}
    return out


def identity_problems(identities: dict[str, dict]) -> list[str]:
    """A bundle whose lines do not carry exactly one commit and one set of tool hashes."""
    problems = []
    for bundle, record in identities.items():
        if record["without_identity"]:
            problems.append(f"{bundle}: {record['without_identity']} lines without identity")
        if len(record["commits"]) > 1:
            problems.append(f"{bundle}: {len(record['commits'])} commits {record['commits']}")
        if record["tool_hash_sets"] > 1:
            problems.append(f"{bundle}: {record['tool_hash_sets']} tool sha256 sets")
    return problems


def identity_report(data: Data, identities: dict[str, dict]) -> list[str]:
    lines = [f"{bundle}: 줄 {record['lines']}, 커밋 {record['commits']}, 도구 해시 묶음 "
             f"{record['tool_hash_sets']}, dirty 줄 {record['dirty_lines']}, 정체성 없는 줄 "
             f"{record['without_identity']}" for bundle, record in identities.items()]
    used = sum(1 for key in data.bundles.get("F-2", {}) if key in data.stored)
    lines.append(f"F-2 L = 저장 `las_T1`·`las_T2` b0 act 줄 {used}개(예외: 이 도구의 실행이 "
                 "아니어서 커밋 검사에서 뺌, LAS-b 래퍼 시기 줄)")
    return lines


# ------------------------------------------------------------------------------- report
def load_data(out_dir: Path, family_keys: list[str] | None = None,
              stored_paths=ft.LAS_STORED_PATHS) -> Data:
    """All lines of ``out_dir`` and the stored F-2 references.

    Raises:
        ValueError: The G-3 family is not the 8 keys of rules 4 C-3.
    """
    bundles = {bundle: lines_by_key(read_lines(out_dir / f"fb_{bundle.replace('-', '')}.jsonl"))
               for bundle in ft.BUNDLES}
    if family_keys is None:
        import las_targeted

        family_keys = las_targeted.stage_keys("T-1")
    if len(set(family_keys)) != FAMILY_KEY_COUNT or len(family_keys) != FAMILY_KEY_COUNT:
        raise ValueError(f"G-3 family has {len(family_keys)} keys "
                         f"(unique {len(set(family_keys))}), rules 4 C-3 needs "
                         f"{FAMILY_KEY_COUNT}")
    expected = {bundle: sorted({ft.fb_key(job) for job in ft.bundle_base_jobs(bundle)})
                for bundle in JUDGED_BUNDLES}
    return Data(bundles, load_stored_reference(stored_paths), family_keys, expected)


IDENTITY_VERDICT = "판정 보류(실행 정체성)"


def verdict_of(criteria: list[Criterion], identity_issues: list[str] | None = None) -> str:
    if identity_issues:
        return IDENTITY_VERDICT
    if any(c.passed is False for c in criteria):
        return "미달"
    if any(c.passed is None for c in criteria):
        return "판정 보류(줄 부족)"
    return "채택 권고"


def _mark(passed: bool | None) -> str:
    return {True: "만족", False: "위반", None: "미완"}[passed]


def sealed_hashes() -> dict[str, str]:
    """Measured sha256 of the sealed rules, the addendum rev1 and the design copy."""
    return {path.name: ft.file_sha256(path)
            for path in (ft.RULES_PATH, ft.RULES_REV1_PATH, ft.DESIGN_PATH)}


def render(data: Data, criteria: list[Criterion], out_dir: Path,
           seal: dict[str, str] | None = None) -> str:
    counts = {bundle: sum(len(v) for v in data.bundles[bundle].values()) for bundle in ft.BUNDLES}
    identities = bundle_identities(data)
    issues = identity_problems(identities)
    seal_lines = [f"  - `{name}` 실측 sha256 `{digest}`" for name, digest in (seal or {}).items()]
    text = ["# FB 표적 판정서 (초안, fb_judge.py 생성)", "",
            f"- 규칙: `fb_targeted_rules.md`(sha256 `{ft.RULES_SHA256[:12]}…`) + 덧붙임 판 "
            f"`fb_targeted_rules_rev1.md`(sha256 `{ft.RULES_REV1_SHA256[:12]}…`), 후보 LF 대 L",
            "- H-1 봉인 확인(판정 시작 때 `fb_targeted.sealed_check` 통과)", *seal_lines,
            f"- 실행 줄: `{out_dir}` " + ", ".join(f"{b} {n}/{ft.BUNDLE_COUNTS[b]}"
                                                  for b, n in counts.items()),
            "- F-2의 L: 저장 `v5/las/las_T1.jsonl`·`las_T2.jsonl` b0 act 줄",
            f"- {LAS_PATH_NOTE}",
            "- 두 경로 판정(python-expert 도구, control-expert 재집계)이 같아야 확정이다"
            "(규칙 8절).",
            "", f"## 판정: **{verdict_of(criteria, issues)}**", "",
            "| # | 항목 | 결과 | 요약 |", "|---|---|---|---|"]
    text += [f"| {c.name} | {c.title} | {_mark(c.passed)} | {c.summary} |" for c in criteria]
    text += ["", "## 실행 정체성", ""]
    text += [f"- {line}" for line in identity_report(data, identities)]
    text += [f"- 문제: {issue}" for issue in issues] or ["- 묶음별 커밋·도구 해시 하나씩"]
    text += ["", "## 멈춤 조건", ""] + [f"- {line}" for line in stop_report(data, out_dir)]
    scale = detection_scale_report(data)
    text += ["", "## 검출로 예산을 깎은 실행(규칙 4절 마지막 항목)", ""]
    text += [f"- {line}" for line in scale] or ["- 없음"]
    text += ["", "## 항목별 상세", ""]
    for criterion in criteria:
        text.append(f"### {criterion.name} {criterion.title}")
        text += [f"- {line}" for line in criterion.details] or ["- (상세 없음)"]
        text.append("")
    text += ["## 이 판정 도구가 정한 해석", "",
             "- C-2 (a): `d1.verdict` pass → fail만 센다(allowed_stop은 참고 목록). "
             "P3-2·G6-2 새 실패 = L이 실패하지 않은 이름이 `P3-2`·`G6-2`로 시작하는 "
             "LF 실패 항목",
             "- 사건 이름 = `event_names` 키(`:` 앞). 새 사건 = LF에만 있는 FAULT·WARN 접두 이름",
             "- VB(eta 0.85) = 설정 VB이고 `eta_v`가 없거나 0.85",
             "- C-6: 첫 깎기 시각 − 첫 TOUCH 주기(그 주기 끝 단계가 TOUCH) 시각 ∈ [0, 1.0] s",
             "- C-10 자세 변화 크기 = hypot(roll 변화, pitch 변화), 축별 값은 상세에 둔다",
             "- 위 해석은 rev1 2절 I-1~I-8로 확정",
             "- F-4 verdict 1번 = `R2ra`(reanchor_on), rev1 1절", ""]
    return "\n".join(text)


def judge(out_dir: Path, md_path: Path | None, family_keys: list[str] | None = None,
          seal: dict[str, str] | None = None) -> dict:
    data = load_data(out_dir, family_keys)
    criteria = [criterion(data) for criterion in CRITERIA]
    issues = identity_problems(bundle_identities(data))
    if md_path is not None:
        md_path.write_text(render(data, criteria, out_dir, seal), encoding="utf-8")
    return {"verdict": verdict_of(criteria, issues),
            "criteria": {c.name: c.passed for c in criteria},
            "identity_problems": issues, "sealed_sha256": seal or {},
            "lines": {b: sum(len(v) for v in data.bundles[b].values()) for b in ft.BUNDLES}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, default=ft.OUT_DIR)
    parser.add_argument("--md", type=Path, default=JUDGEMENT_PATH)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)
    problems = ft.sealed_check()
    if problems:
        print("\n".join(f"H-1 {problem}" for problem in problems))
        print(json.dumps({"stop": "H-1", "problems": problems}))
        return 2
    if not args.out_dir.exists():
        print(json.dumps({"error": f"no {args.out_dir}"}))
        return 2
    try:
        result = judge(args.out_dir, args.md, seal=sealed_hashes())
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}))
        return 2
    if args.json is not None:
        args.json.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True))
    return 0 if result["verdict"] == "채택 권고" else 1


if __name__ == "__main__":
    sys.exit(main())
