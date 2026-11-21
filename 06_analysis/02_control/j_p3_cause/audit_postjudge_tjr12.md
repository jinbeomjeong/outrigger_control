# T-JR-12 판정 후 감사 (verif-protocol-auditor, 2026-11-21) — 원문 그대로

## 감사 요약
- 판정: **B(차단) 0 / M(중간) 2 / N(참고) 6.**
  - 재집계 결과 판정서의 핵심 수치는 모두 원본과 같다. 결론 "T-JR-12 = 실패"(13.9절)는 그대로 성립한다.
  - 판정서 커밋 전에 공개 문장 두 곳을 보완한다(M-1, M-2). 결론 값은 바뀌지 않는다.
- 대상: 판정 후 감사.
  - 판정서 초안: `jp3_tjr12_judgement_78fd5d2d_d3c6c57e.md`(미커밋, sha `ecfcf05e`, LF, `-text`).
  - 실행: `j9_runs/78fd5d2d/dg3_a1/`(커밋 78fd5d2d), 재판정 `j9_runs/d3c6c57e/dg3_vbj_a1/`(커밋 d3c6c57e).
  - master `2c935daa`.
- 기준 문서(sha 앞 8자리): 판 4a `8be9de22` 13.9·6.3절, 4a-3 4절, 4a-5 3·5절, 4a-8 `fde367f0`, 정오 1 `c2d158ab`, 정오 2 `64f7dae1`(미커밋, `.sha256` 일치, `-text`).
- 본 결과: 판정 후 감사라 결과 파일을 열었다.
  - Dg-3 VBH·VBJ·VBJ0 줄: READY, FAULT 이름, 명령 해시, `retract_tracker_*`, `extend_bound_check` 판정 키·읽기 수·최소 간격, B2 증거, `base` 필드 차이.
  - L1 VBJ·VBJ0 줄.
  - 등급 판정 파일의 행 수와 sha.
  - t12·dg3-judge·l1-hash-record·폐포 보고.
  - 경로 2 보고와 중립 입력 SUMS, T4h npz의 배열 이름.
  - control-expert 교차 재판정 출력의 sha.

## 재집계 표(독립 스크립트, 판정 도구 import 없음; READY는 4a-3 4.1, FAULT는 `warn_fault`의 `FAULT` 접두)

| 항목 | 판정서 값 | 재집계 값 | 판단 |
|---|---|---|---|
| VBH 짝 / L2 / 오류 줄 | 135 / 1 / 0 | 135 / 1 / 0(양쪽) | 같음 |
| VBH 새 FAULT | 2키 `L3\|s0\|g8\|32\|…\|RR\|raised\|200.0`, `L3\|s1\|g8\|19\|…\|FL\|raised\|170.0`(`FAULT_LIFT_STROKE_LIMIT`) | 같은 2키, 같은 이름 | 같음 |
| VBH READY 실패 | 11(없음 9, +34.1·+163.6 s) | 11. 없음 9, 늦음 `L3\|s1\|g6\|65…` +34.1, `L3\|s2\|g6\|69…` +163.6. 11키 목록은 t12 보고·멈춤 보고와 같음 | 같음 |
| VBH 둘 다 없음 / 개선 | 5 / 2 | 5 / 2 | 같음 |
| VBH L2·L3 전이 | L2 pass→pass, L3 94/20/10/7/3 | t12 보고와 같음. 등급 산출은 r79 판정 도구 값이고 독립 재구현하지 않았다(검사하지 못한 것) | 도구 값 대조 |
| VBH `retract_tracker` 합 | 7,338 / 7,338 / 509, `ret_after_gate_s` 349개·최대 5.3 s | 7,338 / 7,338 / 509, 349개, 최대 5.300 | 같음 |
| VBH 명령 해시 같은 짝 | 115/135 | 115/135 | 같음 |
| VBJ 새 FAULT / READY 실패 / 둘 다 없음 / 개선 | 0/0/0/0 | 0/0/0/0 | 같음 |
| VBJ J-P3 판정 행 | `L2\|s0\|g6\|52\|ref\|J1\|top\|Fs0`, normal, rev 5, 정체성 기본 | 같음. 등급 normal 1 / conservative 134 | 같음 |
| jp3a/b/c 판정 키 | 각 [0,0,0,0] | 각 [0,0,0,0] | 같음 |
| 읽기 수 a / b / c | 442/447/421/441, 130/139/65/146, 17/28/25/20 | 같음(`jp3a_reads`·`jp3b_reads`·`jp3c_reads`) | 같음 |
| 최소 간격 a / b / c | +0.50 / +8.0 / +13.3 bar | 0.49999… / 7.99999… / 13.3077(c의 최솟값) | 같음(반올림) |
| B2 판정 행 | ① = ② = 857(g6, k = 1) | 857 / 857, g6 | 같음 |
| B2 전체(4a-8 2 k 규칙) | 위반 0 | VBJ·VBJ0 270줄 위반 0(g8 80줄 k = 2) | 같음 |
| VBJ `retract_tracker` | 14 / 14 / 0, `ret_after_gate_s` 1개 0.0 s | 14 / 14 / 0, 1개, 0.0 | 같음 |
| VBJ 대 VBJ0 | r79 기록 135짝 같음, base는 134짝이 `wall_s`만 다름, 명령 해시 134/135 | r79 같음 135, base 차이: `wall_s`만 134, 1짝은 8필드, 명령 해시 134/135 | 같음 |
| 대체 다리 행 | VBJ·VBJ0 각 4, VBH 133 | 4 / 4 / 133(`rod_fallback_reasons`) | 같음 |
| L1 | 설정마다 102줄(g6 63, g8 29, ref 10), 오류 0, plant_truth, 설정 일치, 대체 0 | 같음(두 설정) | 같음 |
| L1 해시 같음 | 102/102 | 102/102(`base.cmd_sha256`), 도구 보고도 102/0/0 | 같음 |
| 등급 판정 파일 | 135 / 짝 없음 0 / 오류 0, 같은 바이트 `e3593c86` | 두 파일 모두 sha `e3593c86`, 135/0/0 | 같음 |

## 발견 사항

### [M][T] M-1: T-JR-12의 전제 단계 P-1이 다시 돌려졌는데(a1 → a2), 판정서에 4a-5 5.3 공개 문구가 없다
- 근거:
  - `j9_runs/78fd5d2d/p1.stop`: exit 2, 사유 "baseline_check identity exit 1 (`_identity_checks/p1_a1.md`)". `p1_a1.md`에는 `mtime_after_commit_before_run` 8건이 있다. 모두 "지금 내용은 커밋과 같다"(17:36:54 mtime, 커밋 직후)라는 내용이다.
  - `p1.done`의 folder는 `p1_a2`이고, `previous_attempts`에 a1 `.stop`이 기록돼 있다.
  - a1의 codes는 `run:base_judge` 0, `identity_check` 1이다. 판정 도구(base-judge-compare·selfcheck)를 돌리기 전에 멈췄으므로 결과를 본 것이 아니다(4a-5 5.4). 재시도는 규칙대로였다.
  - 판정서 1절 입력표의 "H-6 등급 판정(P-1a) `d95627ac…`"는 `p1_a2/h6_base_judge.json`이고, `P1_OUTPUTS_78fd5d2d.SHA256SUMS`(추적됨)와 같다.
  - 그러나 판정서와 멈춤 보고에 a1·a2 언급이 없다(`j_p3_cause` md 전체 Grep에 `p1_a1`·`p1_a2`가 판정서·멈춤 보고에서 0건).
- 영향: 결론에는 영향이 없다. 4a-5 5.3 "다시 돌릴 때 판정서에 넣을 공개 문구"가 빠져 있다.
- 권장 조치(메인·control-expert): 5절에 다음 꼴의 문장을 넣는다. "단계 (1) 시도 a1은 실행 전 정체성 확인(종료 1: 커밋 직후 저장된 파일의 mtime 경고, 내용은 커밋과 같음)으로 판정 불가(종료 2)였다. 같은 커밋·같은 명령 파일로 a2를 돌렸다. a1 출력은 `j9_runs/78fd5d2d/p1_a1/`에 그대로 있다. a1에서 판정 값을 본 적은 없다."

### [M][T] M-2: 정오 2는 재판정 뒤에 쓴 규칙인데, 판정서 1절 규칙 목록에 구분 없이 들어 있다
- 근거:
  - 판정서 `:16` "4a-8(+정오 1·2)".
  - 정오 2 머리 `:4`는 "시점: 6.2절 재판정 뒤다. 이번 VBJ·VBJ0 입력 270줄에는 오류 줄이 0이라 이 정오는 이번 결과를 바꾸지 않는다"이다.
  - mtime: 정오 2는 20:49:18, 재판정 끝은 20:43:01이다.
  - 재집계에서도 오류 줄은 0이다.
- 영향: 결과에는 영향이 없다. 그러나 결과 뒤 개정이 사전 규칙처럼 읽힌다(T축).
- 권장 조치: 1절을 "4a-8·정오 1(결과 전), 정오 2(재판정 뒤 작성, 이번 입력에 해당 줄 0이라 결과 불변)"로 고친다. 정오 2와 `.sha256`은 판정서와 함께 커밋한다.

### [N]
- N-1 [R] 13.9절 결론 대조:
  - 짝은 두 묶음 모두 정확히 135이고, VBJ J-P3 판정 행은 정확히 1이다. 오류 줄 0, 결과 없는 짝 0, 판정 파일 행 수 검사(4a-8 5)도 통과했다(dg3-judge 보고 `judge_rows` 135/0/0/135).
  - VBH는 새 FAULT 2, READY 실패 11로 실패다. 그래서 T-JR-12는 실패다. 판정 불가 조건은 없다.
  - 봉인 595행 인용("T-JR-12(Dg-3)가 비용 관문… 실패하면 판 5")은 원문과 맞는다.
- N-2 [S·I] 입력 sha·정체성:
  - 판정서 1절 표의 sha 9개가 실제 파일·각 보고 `inputs`와 모두 같다.
  - 고정 목록 `FIXED_INPUTS_d3c6c57e`에 든 것(H-6, dg3_VBJ, dg3_VBJ0, L1 키)은 "fixed"로 일치한다.
  - 목록 밖 것은 다른 곳에서 고정돼 있다. `h6_base_judge.json`(`d95627ac`)은 `P1_OUTPUTS_78fd5d2d`, dg3_VBH(`1cf7f866`)는 `dg3_a1_LOCAL_ONLY`, l1_VBJ(`4698ee33`)는 `dg3_vbj_a1_LOCAL_ONLY`, l1_VBJ0(`9cf0ceae`)는 추적 파일이다. 등급 판정 파일 `b7f81009`·`e3593c86`도 추적되고 step_record에 sha가 있다.
  - LOCAL_ONLY 두 목록 3/3 일치. 정체성 보고 `_identity_checks/dg3_a1.md`·`dg3_vbj_a1.md` 모두 "발견 사항 없음"이고, step_record의 `identity_check`는 0이다.
  - T4h npz는 강제 추가로 추적된다(VBJ_t4h 135).
- N-3 [C] 3.3절 같은 바이트 근거를 확인했다. scratchpad `control-tjr12\rejudge\`:
  - VBJ+L1VBJ, VBJ0+L1VBJ0, 교차 두 조합 모두 `e3593c86`이다.
  - VBJ0 한 줄에 FAULT 이름을 더한 변조는 `38fd6730`이다. 스크립트 `v4_rejudge.py`는 봉인 r79 판정 도구를 같은 인자(`--s4-late-loc`)로 불렀다.
  - 독립 재집계로도 r79 기록 135짝 같음, L1 102/102 해시 같음이라 같은 바이트와 정합한다.
  - 판정서의 "해석(한계)"(P4에서는 대체 4/135라 rev 5 비용의 증거가 약함)는 이 사실과 맞는다. VBJ 묶음의 등급 비교는 사실상 같은 입력끼리의 비교라 판별력이 낮다.
- N-4 [R] 8절 경로 2 대조 서술은 보고와 맞는다.
  - `tjr12_p2_report.json`: P2-1·2·3·5·6 pass, P2-2 k = 2 80줄, P2-7 record(새 FAULT 2, READY 실패 11, 둘 다 없음 5, 개선 2). P2-4는 `judged_key_missing`(두 보고 모두).
  - 근거 확인: r79 T4h(`VBJ_t4h`·`VBJ0_t4h` 각 135)에는 `jp3_*` 배열이 0이다. 배열 이름은 `command_m_s`·`head_pressure_Pa` 등 14개뿐이다. P2-4b 발췌 잘림 60줄도 보고와 같다.
  - 중립 입력 SUMS 8/8 일치. 원본과 같은 sha인 것은 dg3 세 개와 L1 두 개다.
  - 경로 2 코드(`z4369-p2/04_scripts/path2`)와 넘김 7에 경로 1 도구 이름(`jp3_tjr_judge` 등)·`z4369-jp3`가 Grep 0건이다. 데이터 meta의 실행 쪽 경로를 따라가지 않았다는 보고는 transcript로 확인하지 못했다(검사하지 못한 것).
  - P2-6은 경로 2가 등급을 독립으로 다시 매긴 것이 아니라, "같은 등급 입력이면 같은 등급"이라는 논리로 통과→실패 0을 낸 것이다. 판정서 8절 표현("L2 짝 필드·L1 줄이 같아 통과 → 실패 0")은 이를 정확히 적었다.
- N-5 [R] P2-4 판정 불가 처리(판정서 기록 + 판 5에서 r79 T4h 배열 기록 수정)와 4a-5 5.4·6.3절:
  - 모순은 없다. VBJ J-P3 통과는 경로 1 단일(실행 중 모니터 집계 키)이다. 6.3절 per-read 기록이 r79 경로에 없는 것은 실행 쪽 기록 결함으로 공개됐다. T-JR-12 결론(VBH 실패)은 VBJ와 관계없다(4a-8 6.3). 5.4절대로 VBJ를 지금 다시 판정해 바꾸는 것도 아니다.
  - 권고: 0절 표의 VBJ "J-P3 pass" 칸에 "(경로 1 단일)"을 함께 적어, 표만 읽어도 두 경로 미확인이 보이게 한다.
- N-6 [T] 5절 공개 문구와 실제 경위:
  - 4a-8 6.4 문구, 커밋 혼합(폐포 223 ∩ diff 13 = 0, `import_closure.json` disjoint), 배치는 실제와 맞는다. 배치는 step_record 기준으로 Dg-3이 VBH `0x00FF`/4, VBJ `0xFF00`/4, VBJ0 `0x0FFF0000`/12이고, L1이 VBJ `0xFFFF`/12, VBJ0 `0x0FFF0000`/12다.
  - 판정서는 Dg-3 배치에서 VBH를 빼고 적었다. 범위 밖이지만 넣으면 완전하다.
  - "결과를 본 시점": 멈춤 보고 `:54`가 78fd5d2d `t12_VBJ.json`을 열지 않았다고 적었다. 그 파일(종료 2)에는 J-P3 `status: pass`가 들어 있으므로, 판정서에도 "78fd5d2d `t12_VBJ.json`(J-P3 상태 포함)은 열지 않았다"를 한 줄 더하면 근거가 닫힌다.
  - 열람 사실 자체는 기록으로만 확인할 수 있다(검사하지 못한 것).

## 확인 필요
없음.

## 위임 필요
없음. M-1·M-2와 N-5·N-6의 문장 보완은 메인 또는 control-expert가 한다.

## 메인 세션 권고
- M-1·M-2를 반영한 뒤 판정서·정오 2(+`.sha256`)·넘김 7을 커밋한다. 커밋 전 integrity-checker를 거친다.
- 9절에 이 감사 경로를 적는다.

## 검사하지 못한 것
- r79 등급(L2·L3 전이)의 독립 재구현: 등급 규칙(S-1~S-6, S4_late_loc)을 다시 구현하지 않았다. 판정 도구 보고 값과의 대조뿐이다.
- 경로 2가 데이터 meta의 경로 1 쪽 경로를 따라가지 않았는지, VBJ 판정 값을 재판정 전에 열지 않았는지: transcript가 없어 보고에 의존한다.
- VBJ `retract_tracker` 14가 `L3|s1|g8|15` 한 줄에서 나왔다는 귀속은 확인하지 않았다(합계만 확인).

## 실행한 검증
- python-dev(`-I -B`, TBB) 즉석 스크립트:
  - `recount.py`: READY·FAULT·추적기 합·해시·J-P3 키·B2·L1·판정 파일 sha.
  - `reports.py`: 보고 status·전이·inputs sha 대 고정 목록·LOCAL_ONLY·정체성·step_record.
  - `p2check.py`: 경로 2 보고·중립 SUMS·T4h 배열 이름.
  - 모두 판정 도구를 import하지 않았다.
- PowerShell `Get-FileHash`. git 조회: `log`, `status --porcelain`, `ls-files --error-unmatch`, `check-ignore -v`, `check-attr text`.
- Grep: 경로 2 코드·넘김 7의 경로 1 이름, `p1_a1/a2` 언급, 봉인 595행.
- 만든 뒤 지운 파일: scratchpad `verif-postjudge-tjr12\`(guard.json, recount.py, reports.py, p2check.py). 폴더째 지웠고 Test-Path는 False다.
- 메모리: `audit_pitfalls.md`에 한 항목을 더했다(전제 단계 재시도 공개, 결과 뒤 정오 표기).
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_tjr12_judgement_78fd5d2d_d3c6c57e.md ecfcf05e…, jp3_tjr12_stop_report_78fd5d2d.md 6907f354…, jp3_remedy_spec_addendum_4a8.md fde367f0…, jp3_remedy_spec_addendum_4a8_erratum1.md c2d158ab…, jp3_remedy_spec_addendum_4a8_erratum2.md 64f7dae1…, dg3_a1_LOCAL_ONLY.SHA256SUMS 4205ea90…, dg3_vbj_a1_LOCAL_ONLY.SHA256SUMS bf0b10ee…, t12_VBH.json b24e5986…, t12_VBJ.json 4bebb3d5…, dg3_VBJ0.json c1201b2d…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음

---

## 메인 결정(2026-11-21)

- M-1(5절 "전제 단계 재시도" 문장), M-2(1절 정오 2 구분), N-5(0절 표 "경로 1 단일"), N-6(Dg-3 VBH 배치, 78fd5d2d `t12_VBJ.json` 비열람)을 판정서에 반영했다(감사 대상 sha `ecfcf05e`에서 바뀜). 9절에 이 감사 경로를 적었다. 판정서 커밋은 integrity-checker 뒤 사용자에게 묻는다.
- 정오(integrity-checker 확인): M-1 근거의 "`mtime_after_commit_before_run` 8건"은 실제 9건이다(`_identity_checks/p1_a1.md` "변경 파일 9개"). 판정서 5절의 "파일 9개"가 맞다.
