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
sha256 of the rules, rev1, rev2 and the design copy.

rev2 (sealed before any run): S-1 (R2-1, ``check_s1``) = the L hash of both F-0 keys equals
the stored b0 act hash; a mismatch makes the verdict an S-1 stop and the R2-1 wording ① .. ③
(``LAS_PATH_NOTE``) is written only after S-1 and C-7 passed. R2-3: s = Q_b / Q(u) is reported
for every LF / OL-LF run per phase (record only): s_nom = the run's Q_nom / Q(4 v_max)
(0.8768421 with the 94e03bb YAML; rev2 prints 0.876840 from the 57.1902 L/min of rules 1.1,
the geometry gives 57.1900), floor 0.5 s_nom; a run with s < s_nom and no cut, or s < floor,
or an s_nom other than the other runs', is an implementation defect candidate.

rev3: the s report reads s_eff (returned-flow ratio, R3-1); s_vec < s_nom caused by a leg above
v_max is listed with the run's ``INFO_DIFF_SINK_*`` events, not as a defect, and such runs
are left out of the margin-table check (record only). H-4 counts pairs (R3-2). Lines of a tool
without R3-1 hold the verdict (R3-4). The draft carries the R3-3 disclosure verbatim and the
four rule sha256.

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
SCALE_NOMINAL_REV2 = 0.876840
"""The s_nom rev2 R2-3 prints (50.1466 / 57.1902 L/min; replaces the rules 4 value 0.8947).
Record only: the reference is the value each run computes from its geometry
(``fb.budget.nominal_scale`` = Q_nom / Q(4 v_max)), 0.8768421 with the YAML of 94e03bb, where
Q(4 v_max) is 57.19000 L/min, not the 57.1902 of rules 1.1."""
SCALE_TOLERANCE = 1e-6
NOMINAL_SPREAD_TOLERANCE = 1e-9
"""Runs of one judgement share the geometry, so their s_nom must agree to rounding."""
DIFF_SINK_PREFIX = "INFO_DIFF_SINK"
"""DSb75 events shown next to the runs with clipped budget periods (rev3 R3-1)."""
PRIOR_OBSERVATION_NOTE = (
    "**사전 관찰(공개)**: rev2 봉인(2026-11-08 19:00:42) 전에 scratch에서 F-0 4줄(L·LF-off × K1 "
    "VB e0·K3 V0 e0, 커밋 `5468c67`, `scratchpad\\fbfix\\f0\\fb_F0.jsonl`)을 돌렸다. S-1·C-7 "
    "결과(해시 `aff9b0f10ac5`·`fc2ca22f2850`, 저장 b0 act와 같음)를 rev2 작성 전에 봤다. rev2 "
    "머리말의 \"실행 줄 0줄\"은 저장소 기준이었고, 이 4줄을 빠뜨렸다. 이 줄들은 예산 꺼짐 "
    "경로라 LF 결과는 포함하지 않는다. S-1 기준 해시는 저장 값에서 정해졌다. 판정에는 저장소 "
    "`v5/fb/fb_F0.jsonl`(rev3 도구로 다시 돈 줄)만 쓴다."
)
"""rev3 R3-3 wording, verbatim."""
PRIOR_OBSERVATION_REV3_NOTE = (
    "**사전 관찰(공개, rev3 봉인 뒤)**: rev3 봉인(19:31:35) 뒤 rev3 도구 확인으로 scratch에서 "
    "F-0 4줄을 다시 돌렸다(`scratchpad\\fbfix\\f0_rev3\\fb_F0.jsonl`, 커밋 `b6a8a82`, 19:42, "
    "L·LF-off만이라 LF 결과는 없다). 해시는 rev2 R2-1 표와 같았다. 판정에는 쓰지 않는다."
)
CHANGED_RUNS_NOTE = (
    "명령이 바뀐 실행 수는 R3-5 정의 기준(예산 작용 + 절단 다리 주기)이며, rev3:41의 둘째 "
    "경우(옛 식은 작용하고 새 식은 작용하지 않는 주기)는 줄에 기록이 없어 세지 않았다."
)
CLIP_NOTE = (
    "`clip_returned_command`는 R8 프리셋 기본 켬(`c2.py:2496`, 클래스 기본 꺼짐)이다. 실행 "
    "줄에는 이 값이 없고 `controller_tag`만 있다. 그래서 줄의 `controller_tag`가 기대 태그"
    "(C4G2 포함)인지로 절단 켬 가정을 확인한다."
)
EXPECTED_CONTROLLER_TAGS = {"VB": "final_C4G2_P3_LAS", "V0": "final_C4G2_LAS"}
"""rev2 R2-1 ①: the controller tag of a new line per setting (C4G2 = the preset with the
returned-command clip; LAS = 03_src LAS-b)."""
PHASE_LEVEL = "level"
"""``str(c2.C2Phase.LEVEL)``, the phase string of ``acted_periods``."""
SCALE_CANDIDATES = ("LF", "OL-LF")
"""rev2 R2-3 report 1: the runs with the budget on."""
FAMILY_KEY_COUNT = 8
"""Rules 4 C-3: the G-3 family of F-2 T-1."""
NEW_EVENT_PREFIXES = ("FAULT", "WARN")
FAILED_ITEM_PREFIXES = ("P3-2", "G6-2")
REFERENCE = "L"
CANDIDATE = "LF"
LAS_PATH_TITLE = "**LAS-b 구현(원판 3.1 대체, rev2 R2-1)**"
LAS_PATH_NOTE = (
    "① 이 판정의 모든 새 실행(F-0 L·LF-off, F-1·F-3·F-4의 L·LF, F-2 LF, F-5 OL-L·OL-LF)은 "
    "LAS-b를 03_src 프리셋 구현(`C2Config.with_10hz_d1().liftoff_approach_slow`, P-S8-39, "
    "병합 `bacb2d2`, 이후 `334d544` 포함)으로 돌렸다. 원판 3.1의 `las_targeted.install` b0 "
    "래퍼는 설치하지 않았다. 실행 코드는 각 줄 `fb.identity`의 커밋 `{commit}`과 도구 "
    "sha256이다. 새 L 줄의 제어기 태그는 `final_C4G2_P3_LAS`(VB)·`final_C4G2_LAS`(V0)다. 저장 "
    "F-2 L 줄의 태그는 `final_C4G2_P3`·`final_C4G2`(래퍼)다. 짝은 키로만 맞추고 태그로 거르지 "
    "않았다.\n"
    "② 이 대체는 원판 3.1에 따른 것이다. 원판 7절의 사후 변경 공개 대상이 아니다. 대체 전에 "
    "S-1을 확인했다. F-0 두 키의 03_src L 해시는 K1 VB `aff9b0f1…`와 K3 V0 `fc2ca22f…`였고, 둘 "
    "다 저장 b0 act 해시와 {s1}. C-7(LF-off = L 2/2)은 {c7}.\n"
    "③ F-2의 L은 원판 3.2대로 저장 `v5/las/las_T1.jsonl`·`las_T2.jsonl`의 b0 act 줄이다. 이 "
    "줄은 03_src에 LAS-b가 들어가기 전의 코드에 b0 래퍼를 얹어 만든 것이다. 줄에는 커밋 필드가 "
    "없다. 파일 시각 15:28·15:51과 git 기록으로 보면 `655844a`(15:09) 뒤, `11d28c6`(17:37) "
    "앞이다. 따라서 F-2의 LF − L 짝에는 FB의 효과와 함께 \"03_src LAS-b ↔ 래퍼 b0\" 구현 차이가 "
    "들어갈 수 있다. 이 차이가 0이라는 근거는 다음과 같다. 첫째, 비트 시험 B-1~B-3"
    "(`11d28c6`)이다. B-2는 T-1 8키 = 래퍼, B-3은 T-2 작동 12키 = 래퍼, 미작동 10키 = 기준이다. "
    "둘째, `334d544` 뒤 재확인 3키(K3 V0 e0, K3 VB e0, K1 VB e0)다. 셋째, 위 ②의 S-1이다. "
    "그래서 F-2 192키 가운데 해시로 같음을 직접 보인 것은 T-1 8키와 T-2 22키, 합 30키다. "
    "나머지 162키는 구현 동등성 가정이다(한계)."
)
"""rev2 R2-1 wording ① .. ③, verbatim; ``{commit}``, ``{s1}`` ("같았다") and ``{c7}``
("통과했다") are filled after the run. With S-1 or C-7 not passed the wording is not written
(rev2: an S-1 stop is reported instead)."""
S1_STOP_NOTE = "S-1 멈춤(rev2 R2-1): LAS-b 구현 문구를 쓰지 않는다. {problems}"


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


def is_events_truncated(line: dict) -> bool:
    """The run had more events than ``verdict_runs`` stores: its event set is incomplete."""
    return bool((line.get("fb") or {}).get("events_truncated"))


def is_pair_truncated(reference: dict, candidate: dict) -> bool:
    return is_events_truncated(reference) or is_events_truncated(candidate)


def c2_violations(reference: dict, candidate: dict) -> list[str]:
    """C-2 (a) .. (c) of one pair (texts; empty = no violation). (c) is not judged on a pair
    with a truncated event list (the pair stays incomplete in :func:`c2`)."""
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
    if not is_pair_truncated(reference, candidate):
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
    truncated = [f"{b} {k}" for b, k, ref, cand in pairs if is_pair_truncated(ref, cand)]
    details = failures + notes + [f"사건 목록 절단(400개 초과)으로 (c) 미완: {text}"
                                  for text in truncated]
    is_complete = data.missing_pairs() == 0 and not truncated
    return Criterion("C-2", "판정", _status(is_complete, failures),
                     f"짝 {len(pairs)}, 위반 {len(failures)}, 사건 절단 짝 {len(truncated)}",
                     details)


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
    deltas, different, failures, truncated = [], [], [], []
    for bundle, key, ref, cand in data.pairs():
        t_ref, t_cand = ready_time_s(ref), ready_time_s(cand)
        if t_ref is None or t_cand is None:
            continue
        if is_pair_truncated(ref, cand):  # the event set is not known: no READY judgement
            truncated.append(f"{bundle} {key}")
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
    details += [f"사건 목록 절단(400개 초과)으로 미완: {text}" for text in truncated]
    # No judged pair is no evidence: incomplete, not a pass; so is a truncated event set.
    is_complete = data.missing_pairs() == 0 and bool(deltas) and not truncated
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


def check_s1(f0_lines: list[dict], stored_t1: dict[str, dict],
             expected: dict[str, str] | None = None) -> dict:
    """rev2 R2-1 S-1: the 03_src L hash of both F-0 keys = the stored b0 act hash.

    ``expected`` (default the hashes rev2 states) must also be the hash of the stored
    ``las_T1`` b0 act line of the key, when that line is there.
    """
    expected = ft.S1_STORED_HASHES if expected is None else expected
    by_key = lines_by_key(f0_lines)
    problems, rows = [], []
    for key, sealed_hash in expected.items():
        stored = stored_t1.get(key)
        if stored is not None and stored["commands_sha256"] != sealed_hash:
            problems.append(f"{key}: stored las_T1 b0 {stored['commands_sha256'][:12]} != "
                            f"rev2 {sealed_hash[:12]}")
        reference = by_key.get(key, {}).get(REFERENCE)
        if reference is None:
            problems.append(f"{key}: missing L")
            continue
        rows.append(f"S-1 {key}: L {reference['commands_sha256'][:12]} 저장 b0 "
                    f"{sealed_hash[:12]}")
        if reference["commands_sha256"] != sealed_hash:
            problems.append(f"{key}: L hash {reference['commands_sha256']} != stored b0 "
                            f"{sealed_hash}")
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


def s1_result(data: Data) -> dict:
    lines = [line for lines in data.bundles.get("F-0", {}).values() for line in lines.values()]
    return check_s1(lines, data.stored)


def stop_report(data: Data, out_dir: Path) -> list[str]:
    c7_result = c7(data)
    s1 = s1_result(data)
    lines = [f"H-2 (F-0 C-7): {'통과' if c7_result.passed else c7_result.summary}",
             f"S-1 (rev2 R2-1, H-2와 같이 처리): "
             f"{'통과' if s1['pass'] else '; '.join(s1['problems'])}"]
    lines += [f"  {row}" for row in s1["rows"]]
    errors = error_lines(out_dir)
    for bundle, labels in errors.items():
        twice = sorted({label for label in labels if labels.count(label) >= 2})
        lines.append(f"H-3 {bundle}: 오류 줄 {len(labels)}, 두 번 실패 {twice or '없음'}")
    if not errors:
        lines.append("H-3: 오류 줄 없음")
    for bundle in JUDGED_BUNDLES:
        pairs, texts = h4_counts(data, bundle)
        stop = " (멈춤 조건)" if pairs >= ft.C2_STOP_COUNT else ""
        lines.append(f"H-4 {bundle}: C-2 위반 짝 {pairs}(문장 {texts}){stop}")
    return lines


def h4_counts(data: Data, bundle: str) -> tuple[int, int]:
    """rev3 R3-2: (pairs with at least one C-2 violation, violation texts) of a bundle."""
    per_pair = [len(c2_violations(r, c)) for _, _, r, c in data.pairs((bundle,))]
    return sum(1 for count in per_pair if count), sum(per_pair)


def budget_lines(data: Data) -> list[tuple[str, str, dict]]:
    """(bundle, key, line) of every run with the budget on: LF and OL-LF (rev2 R2-3 1)."""
    out = []
    for name in SCALE_CANDIDATES:
        out += data.candidate_lines(ft.BUNDLES, name)
    return out


def _budget(line: dict) -> dict | None:
    return (line.get("fb") or {}).get("budget")


def _spread(values: list[float]) -> str:
    return (f"최소 {min(values):.6f} · 중앙 {statistics.median(values):.6f} · "
            f"최대 {max(values):.6f}")


def has_clipped_periods(line: dict) -> bool:
    """rev3 R3-1: the run had budget periods with a leg above v_max (its commands changed)."""
    return bool((_budget(line) or {}).get("clipped_budget_periods"))


def scale_summary(data: Data, key_name: str = "min_scale_eff_by_phase",
                  label: str = "s_eff") -> list[str]:
    """rev2 R2-3 1 (s = s_eff by rev3 R3-1): per bundle and phase, the runs' smallest s and
    acted periods; ``key_name`` "min_scale_by_phase" gives the s_vec summary."""
    by_group: dict[tuple[str, str], tuple[list[float], list[float]]] = {}
    for bundle, _, line in budget_lines(data):
        budget = _budget(line) or {}
        acted = budget.get("acted_periods") or {}
        for phase, scale in (budget.get(key_name) or {}).items():
            scales, periods = by_group.setdefault((bundle, phase), ([], []))
            scales.append(scale)
            periods.append(float(acted.get(phase, 0)))
    return [f"{bundle} {phase}: 실행 {len(scales)}, {label} {_spread(scales)}; 작용 주기 "
            f"{_spread(periods)}"
            for (bundle, phase), (scales, periods) in sorted(by_group.items())]


def diff_sink_events(line: dict) -> list[str]:
    return sorted(name for name in event_set(line) if name.startswith(DIFF_SINK_PREFIX))


def clipped_report(data: Data) -> list[str]:
    """rev3 R3-1 / R3-5: runs whose budget periods had a leg above v_max (commands changed by
    R3-1; the margin table does not cover them), with s_vec, s_eff and the DSb75 events."""
    out = []
    for bundle, key, line in budget_lines(data):
        if not has_clipped_periods(line):
            continue
        budget = _budget(line) or {}
        out.append(f"{bundle} {line['fb']['candidate']} {key}: 절단 주기 "
                   f"{budget['clipped_budget_periods']}, s_vec {budget['min_scale']:.6f}, "
                   f"s_eff {budget.get('min_scale_eff')}, 사건 "
                   f"{diff_sink_events(line) or '없음'}")
    return out


def cut_scale_report(data: Data) -> list[str]:
    """rev2 R2-3 2: runs a detection cut (rule, time, final Q_b, smallest s), one per line."""
    out = []
    for bundle, key, line in budget_lines(data):
        budget = _budget(line) or {}
        cuts = budget.get("cuts") or []
        if cuts:
            rules = ", ".join(f"{cut['rule']}@{cut['t_s']:g}s" for cut in cuts)
            out.append(f"{bundle} {key}: 깎기 {len(cuts)}({rules}), 최종 Q_b "
                       f"{budget['Q_b_final_L_min']:.2f} L/min, 최소 s_eff "
                       f"{budget.get('min_scale_eff')}, 최소 s_vec "
                       f"{budget['min_scale']:.6f}")
    return out


def reference_nominal_scale(data: Data) -> float | None:
    """The median s_nom of the budget-on runs (None without one)."""
    values = [(_budget(line) or {}).get("nominal_scale") for _, _, line in budget_lines(data)]
    values = [value for value in values if value is not None]
    return statistics.median(values) if values else None


def scale_defects(line: dict, reference_nominal: float | None) -> list[str]:
    """rev3 R3-1 (replaces rev2 R2-3 3): why a budget-on run is an implementation defect
    candidate (empty = none).

    No budget meta, s_nom or ``min_scale_eff`` (an older tool, R3-4); an s_nom other than the
    other runs'; (가) s_eff outside its range: > 1, < s_nom without a cut, < 0.5 s_nom; (나)
    s_vec != s_eff in a phase without clipped budget periods (per phase: a run's clipped
    LEVEL does not exempt its TOUCH). s_vec < s_nom from a leg above v_max is not a defect
    (:func:`clipped_report`). Tolerance 1e-6; s_nom = the run's own value.
    """
    budget = _budget(line)
    if budget is None:
        return ["예산 meta 없음"]
    nominal = budget.get("nominal_scale")
    if nominal is None:
        return ["s_nom 없음"]
    if "min_scale_eff" not in budget:
        return ["min_scale_eff 없음(R3-1 미구현 도구, rev3 R3-4)"]
    out = []
    if reference_nominal is not None and abs(nominal - reference_nominal) > \
            NOMINAL_SPREAD_TOLERANCE:
        out.append(f"s_nom {nominal:.9f} != 다른 실행 {reference_nominal:.9f}")
    effective = budget.get("min_scale_eff_by_phase") or {}
    if effective:
        smallest = min(effective.values())
        if max(effective.values()) > 1.0 + SCALE_TOLERANCE:
            out.append(f"s_eff {max(effective.values()):.6f} > 1")
        if not budget.get("cuts") and smallest < nominal - SCALE_TOLERANCE:
            out.append(f"깎기 없이 s_eff {smallest:.6f} < s_nom {nominal:.6f}")
        floor = ft.FLOOR_FRACTION * nominal
        if smallest < floor - SCALE_TOLERANCE:
            out.append(f"s_eff {smallest:.6f} < 하한 {floor:.6f}")
    vector = budget.get("min_scale_by_phase") or {}
    clipped_phases = set(budget.get("clipped_budget_periods") or {})
    differing = sorted(phase for phase in (set(vector) | set(effective)) - clipped_phases
                       if vector.get(phase) != effective.get(phase))
    if differing:
        out.append(f"절단 없이 s_vec != s_eff ({differing})")
    return out


def defect_report(data: Data) -> list[str]:
    reference = reference_nominal_scale(data)
    out = []
    for bundle, key, line in budget_lines(data):
        problems = scale_defects(line, reference)
        if problems:
            out.append(f"{bundle} {line['fb']['candidate']} {key}: {'; '.join(problems)}")
    return out


def level_range_report(data: Data) -> str:
    """rev2 R2-3 4: the LEVEL smallest s against the linear margin table range [floor, 1]; a
    run whose LEVEL had clipped budget periods is left out (rev3 R3-1: not a uniform-scale
    map, record only); clipped periods in another phase do not remove its LEVEL value."""
    level, clipped = [], 0
    for _, _, line in budget_lines(data):
        budget = _budget(line) or {}
        value = (budget.get("min_scale_eff_by_phase") or {}).get(PHASE_LEVEL)
        if value is None:
            continue
        if PHASE_LEVEL in (budget.get("clipped_budget_periods") or {}):
            clipped += 1
            continue
        level.append(value)
    note = f", LEVEL 절단 주기가 있어 표 대조에서 뺀 실행 {clipped}(기록만)" if clipped else ""
    if not level:
        return f"LEVEL 작용 없음(대조할 s 없음){note}"
    smallest = min(level)
    # The margin table's lower point is rev2's printed floor 0.438420.
    inside = ft.FLOOR_FRACTION * SCALE_NOMINAL_REV2 - SCALE_TOLERANCE <= smallest <= 1.0
    return (f"LEVEL 최소 s_eff {smallest:.6f}({len(level)}실행): "
            + ("선형 여유 표 범위 안" if inside else "선형 여유 표 범위 밖(control-expert 재판단)")
            + note)


# ------------------------------------------------------------------------------- identity
def _identity_tuple(line: dict) -> tuple | None:
    identity = (line.get("fb") or {}).get("identity")
    if not identity:
        return None
    hashes = (identity.get("code_diff_sha256"),
              tuple(sorted((identity.get("sha256") or {}).items())))
    return identity.get("git_head"), hashes


def is_pre_r3_line(line: dict) -> bool:
    """rev3 R3-4: a line of a tool without R3-1 (no ``budget_rule`` in the identity, or a
    budget meta without ``min_scale_eff``); such lines are not used for the judgement."""
    fb = line.get("fb") or {}
    if (fb.get("identity") or {}).get("budget_rule") != ft.BUDGET_RULE:
        return True
    budget = fb.get("budget")
    return budget is not None and "min_scale_eff" not in budget


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
                       "pre_r3_lines": sum(is_pre_r3_line(line) for line in lines),
                       "dirty_lines": sum(bool(((line.get("fb") or {}).get("identity") or {})
                                               .get("git_dirty")) for line in lines)}
    return out


def identity_problems(identities: dict[str, dict]) -> list[str]:
    """A bundle whose lines do not carry exactly one commit and one set of tool hashes (code
    diff included), or that has lines of a tool without R3-1 (rev3 R3-4)."""
    problems = []
    for bundle, record in identities.items():
        if record["without_identity"]:
            problems.append(f"{bundle}: {record['without_identity']} lines without identity")
        if record.get("pre_r3_lines"):
            problems.append(f"{bundle}: {record['pre_r3_lines']} lines of a tool without R3-1 "
                            "(rev3 R3-4, not used)")
        if len(record["commits"]) > 1:
            problems.append(f"{bundle}: {len(record['commits'])} commits {record['commits']}")
        if record["tool_hash_sets"] > 1:
            problems.append(f"{bundle}: {record['tool_hash_sets']} tool sha256 sets")
    return problems


def controller_tag_check(data: Data) -> tuple[int, list[str]]:
    """(lines with the expected tag, texts of the others) over our lines (the stored F-2 L
    lines are wrapper-era and not checked): the evidence for the clip-on assumption."""
    matching, others = 0, []
    for bundle in ft.BUNDLES:
        for key, by_candidate in data.bundles.get(bundle, {}).items():
            for name, line in by_candidate.items():
                setting = (line.get("job") or {}).get("setting")
                expected = EXPECTED_CONTROLLER_TAGS.get(setting)
                tag = line.get("controller_tag")
                if expected is not None and tag == expected:
                    matching += 1
                else:
                    others.append(f"{bundle} {name} {key}: 설정 {setting}, 태그 {tag!r}, "
                                  f"기대 {expected!r}")
    return matching, others


def clip_report(data: Data) -> list[str]:
    matching, others = controller_tag_check(data)
    lines = [CLIP_NOTE, f"기대 태그 줄 {matching}, 그 밖 {len(others)}"
             + ("" if others else "(절단 켬 가정의 근거)")]
    lines += [f"기대와 다른 태그(절단 켬 가정 근거 없음): {text}" for text in others]
    return lines


def commit_table(identities: dict[str, dict]) -> list[str]:
    """Markdown rows: every bundle's commits, and whether all bundles share one."""
    rows = ["| 묶음 | 줄 | 커밋 |", "|---|---|---|"]
    rows += [f"| {bundle} | {record['lines']} | "
             f"{', '.join(f'`{commit[:12]}`' for commit in record['commits']) or '-'} |"
             for bundle, record in identities.items()]
    commits = {commit for record in identities.values() for commit in record["commits"]}
    if not commits:
        verdict = "커밋 기록 없음"
    elif len(commits) == 1:
        verdict = "묶음 사이 커밋 같음"
    else:
        verdict = f"묶음 사이 커밋 다름({len(commits)}개)"
    return [*rows, "", f"- {verdict}"]


def identity_report(data: Data, identities: dict[str, dict]) -> list[str]:
    lines = [f"{bundle}: 줄 {record['lines']}, 커밋 {record['commits']}, 도구 해시 묶음 "
             f"{record['tool_hash_sets']}, dirty 줄 {record['dirty_lines']}, 정체성 없는 줄 "
             f"{record['without_identity']}, R3-1 이전 도구 줄 {record['pre_r3_lines']}"
             for bundle, record in identities.items()]
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
S1_VERDICT = "멈춤(S-1 불일치, rev2 R2-1)"


def _is_s1_mismatch(s1: dict | None) -> bool:
    """S-1 failed on a hash (missing L lines leave C-7 incomplete instead)."""
    return s1 is not None and any("missing" not in text for text in s1["problems"])


def verdict_of(criteria: list[Criterion], identity_issues: list[str] | None = None,
               s1: dict | None = None) -> str:
    if identity_issues:
        return IDENTITY_VERDICT
    if _is_s1_mismatch(s1):
        return S1_VERDICT
    if any(c.passed is False for c in criteria):
        return "미달"
    if any(c.passed is None for c in criteria):
        return "판정 보류(줄 부족)"
    return "채택 권고"


def _mark(passed: bool | None) -> str:
    return {True: "만족", False: "위반", None: "미완"}[passed]


def sealed_hashes() -> dict[str, str]:
    """Measured sha256 of the sealed rules, the addenda rev1 and rev2 and the design copy."""
    return {path.name: ft.file_sha256(path)
            for path in (ft.RULES_PATH, ft.RULES_REV1_PATH, ft.RULES_REV2_PATH,
                         ft.RULES_REV3_PATH, ft.DESIGN_PATH)}


def las_path_text(data: Data, identities: dict[str, dict]) -> list[str]:
    """rev2 R2-1 wording ① .. ③ with the commit, S-1 and C-7 filled; an S-1 stop note (or a
    placeholder before F-0) instead when they did not pass."""
    s1, c7_result = s1_result(data), c7(data)
    if not (s1["pass"] and c7_result.passed):
        reason = s1["problems"] + ([] if c7_result.passed else [f"C-7 {c7_result.summary}"])
        return [S1_STOP_NOTE.format(problems="; ".join(reason))]
    commits = sorted({commit for record in identities.values() for commit in record["commits"]})
    commit = ", ".join(commit[:12] for commit in commits) or "(기록 없음)"
    note = LAS_PATH_NOTE.format(commit=commit, s1="같았다", c7="통과했다")
    return [LAS_PATH_TITLE, *note.split("\n")]


def scale_text(data: Data) -> list[str]:
    """rev2 R2-3 report 1 .. 4 (record only, not a criterion)."""
    reference = reference_nominal_scale(data)
    computed = "실행 없음" if reference is None else (
        f"{reference:.7f}(차 {reference - SCALE_NOMINAL_REV2:+.1e})")
    clipped = clipped_report(data)
    text = ["", "## 예산 축척 s(rev2 R2-3, rev3 R3-1 정정, 기록)", "",
            "- R3-1 정정: 예산 유량은 반환 명령 기준 Q(c(u))(c = ±v_max 절단, "
            "`clip_returned_command` 켬)이고, 축척 s* = max{s ≤ 1 : Q(c(s u)) ≤ Q_b}를 절단 전 "
            "벡터에 곱한다. 모든 |u_i| ≤ v_max이거나 절단이 꺼진 주기는 원판 식 그대로다.",
            f"- 명령이 바뀐 실행(예산 작용 + 절단 다리 주기가 있는 LF·OL-LF 줄): {len(clipped)}",
            f"- {CHANGED_RUNS_NOTE}",
            f"- s = s_eff = Q(c(s* u))/Q(c(u)), s_vec = s*. s_nom = Q_nom/Q(4 v_max): 실행 계산값 "
            f"{computed}, rev2 표기 {SCALE_NOMINAL_REV2:.6f}(규칙 1.1의 57.1902 L/min 기준; "
            "YAML로는 57.1900 L/min). 하한 = 0.5 s_nom, 결함 후보 판정은 실행 계산값 기준, 허용 "
            f"{SCALE_TOLERANCE:g}",
            "", "### 1. LF·OL-LF 실행의 단계별 최소 s_eff(묶음별)", ""]
    text += [f"- {line}" for line in scale_summary(data)] or ["- 작용 없음"]
    text += ["", "#### s_vec(참고)", ""]
    text += [f"- {line}" for line in scale_summary(data, "min_scale_by_phase", "s_vec")] \
        or ["- 작용 없음"]
    text += ["", "### 2. 검출로 예산을 깎은 실행", ""]
    text += [f"- {line}" for line in cut_scale_report(data)] or ["- 없음"]
    text += ["", "### 3. 구현 결함 후보(rev3 R3-1 정의)", ""]
    text += [f"- {line}" for line in defect_report(data)] or ["- 없음"]
    text += ["", "### 절단 다리 주기가 있는 실행(R3-1, 결함 후보 아님, `INFO_DIFF_SINK_*` 함께)",
             ""]
    text += [f"- {line}" for line in clipped] or ["- 없음"]
    text += ["", "### 4. LEVEL s_eff와 선형 여유 표 범위 [0.438420, 1]", "",
             f"- {level_range_report(data)}"]
    return text


def render(data: Data, criteria: list[Criterion], out_dir: Path,
           seal: dict[str, str] | None = None) -> str:
    counts = {bundle: sum(len(v) for v in data.bundles[bundle].values()) for bundle in ft.BUNDLES}
    identities = bundle_identities(data)
    issues = identity_problems(identities)
    seal_lines = [f"  - `{name}` 실측 sha256 `{digest}`" for name, digest in (seal or {}).items()]
    text = ["# FB 표적 판정서 (초안, fb_judge.py 생성)", "",
            f"- 규칙: `fb_targeted_rules.md`(sha256 `{ft.RULES_SHA256[:12]}…`) + 덧붙임 판 "
            f"`fb_targeted_rules_rev1.md`(sha256 `{ft.RULES_REV1_SHA256[:12]}…`) + "
            f"`fb_targeted_rules_rev2.md`(sha256 `{ft.RULES_REV2_SHA256[:12]}…`) + "
            f"`fb_targeted_rules_rev3.md`(sha256 `{ft.RULES_REV3_SHA256[:12]}…`), 후보 LF 대 L",
            "- H-1 봉인 확인(판정 시작 때 `fb_targeted.sealed_check` 통과)", *seal_lines,
            f"- 실행 줄: `{out_dir}` " + ", ".join(f"{b} {n}/{ft.BUNDLE_COUNTS[b]}"
                                                  for b, n in counts.items()),
            "- F-2의 L: 저장 `v5/las/las_T1.jsonl`·`las_T2.jsonl` b0 act 줄",
            "- 두 경로 판정(python-expert 도구, control-expert 재집계)이 같아야 확정이다"
            "(규칙 8절).",
            "", "## 사전 관찰(rev3 R3-3)", "", f"> {PRIOR_OBSERVATION_NOTE}", "",
            f"> {PRIOR_OBSERVATION_REV3_NOTE}",
            "", "## LAS-b 구현", ""]
    text += [f"> {line}" for line in las_path_text(data, identities)]
    text += ["", f"## 판정: **{verdict_of(criteria, issues, s1_result(data))}**", "",
            "| # | 항목 | 결과 | 요약 |", "|---|---|---|---|"]
    text += [f"| {c.name} | {c.title} | {_mark(c.passed)} | {c.summary} |" for c in criteria]
    text += ["", "## 실행 정체성", ""] + commit_table(identities) + [""]
    text += [f"- {line}" for line in identity_report(data, identities)]
    text += ["", "### 반환 명령 절단 스위치", ""] + [f"- {line}" for line in clip_report(data)]
    text += [f"- 문제: {issue}" for issue in issues] or ["- 묶음별 커밋·도구 해시 하나씩"]
    text += ["", "## 멈춤 조건", ""] + [f"- {line}" for line in stop_report(data, out_dir)]
    text += scale_text(data)
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
             "- F-4 verdict 1번 = `R2ra`(reanchor_on), rev1 1절",
             "- A97 단계 조건의 `touch_seen`은 주기 k+1 update 끝 값(rev2 R2-2)",
             "- H-4는 C-2 위반 문장이 하나 이상 있는 짝을 1건으로 센다(rev3 R3-2)",
             "- R3-1 이전 도구의 줄(정체성 `budget_rule` 또는 meta `min_scale_eff` 없음)은 "
             "판정에 쓰지 않는다(rev3 R3-4)", ""]
    return "\n".join(text)


def judge(out_dir: Path, md_path: Path | None, family_keys: list[str] | None = None,
          seal: dict[str, str] | None = None) -> dict:
    data = load_data(out_dir, family_keys)
    criteria = [criterion(data) for criterion in CRITERIA]
    issues = identity_problems(bundle_identities(data))
    s1 = s1_result(data)
    if md_path is not None:
        md_path.write_text(render(data, criteria, out_dir, seal), encoding="utf-8")
    return {"verdict": verdict_of(criteria, issues, s1),
            "criteria": {c.name: c.passed for c in criteria},
            "s1": {"pass": s1["pass"], "problems": s1["problems"]},
            "scale_defects": len(defect_report(data)),
            "clipped_budget_runs": len(clipped_report(data)),
            "controller_tag_others": len(controller_tag_check(data)[1]),
            "h4_pairs": {bundle: h4_counts(data, bundle)[0] for bundle in JUDGED_BUNDLES},
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
