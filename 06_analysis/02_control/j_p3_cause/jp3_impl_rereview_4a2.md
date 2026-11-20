# 436.9 J4a 보완 구현(`3b949f5`) 재검토 — 덧붙임 4a-2 4절 기준

작성: control-expert, 2026-11-20. 읽기·분석만 했습니다. 코드·명세는 고치지 않았고, 사례 재생·본 실행·단위 시험도 돌리지 않았습니다.
- 대상: worktree `C:\workspace\outrigger_control\.claude\worktrees\z4369-jp3`, `git diff ad5024b 3b949f5`(16파일, +2239/−364)
- 기준: 덧붙임 4a-2 저장본(sha256 `2f3e36bd…`, 6절 사용자 확인 포함), 명세 판 4a(`8be9de22…`)
- 연 자료
  - 근거 폴더 `j4a_remedy_3b949f5/`(records_full, junit 요약, `seed_cx.json`)
  - 기준선 npz의 열 이름만(값은 열지 않음)
  - 저장 기준 파일: `resume_k1/h6_dg3_v4on.json`·`h7_dg3_off.json`(READY 키만), `h9_grid/grid_r67_top.json` results[13].runs[3]
  - 새 사례 재생 출력은 없고, 열지 않았습니다.
- 두 경로: 경로 1 코드를 읽었으므로 이 작성자는 B5(경로 2) 작성자가 아닙니다.

## 0. 판정 요약

| 구분 | 건수 | 요지 |
|---|---|---|
| 차단(사례 재생·T-JR 실행 전) | 4 | C1 T-JR-12 READY 키, C2 T-JR-12 판정 범위(L2), C3 T-JR-10 meta 조항 미구현, C4 P4-7 측정량 정의 공개 |
| 차단(실행 전 절차) | 1 | C5 판정 입력·근거 파일 미추적(sha 고정 필요) |
| 권고 | 7 | 건식 확인, F-A 경로 동등성, VBJ0 증거 검사, T-JR-10 VB 재실행 기록, P4-6 경계 근접, 공개 문장 수치, `p3_hash_check.py` 정합 |
| 이상 없음 | 대부분 | 제어기 비트 동일 근거, 시드 순 힘 열과 반례 대조, P4-2 사슬, R2·R3·R4·R5·R6·R8·R9, X11, xfail 0 |

## 1. 4a-2 4절 항목별 적합

| # | 판정 | 비고 |
|---|---|---|
| B2 | 적합(건식 확인 미보고) | ①은 `harness_hydraulics.py:404`(P4 판독 안), ②는 `:890-891`(제어기 update 뒤, 시각 일치 때). 규칙은 `j_p3_inputs.rod_reading_evidence_problems`. r67에서 이미 import된 r64도 패치(`:994-996`). r79 `plant_truth`도 같은 함수를 쓴다(`r79_sensor_screen.py:271-277`). 건식 확인 결과가 보고에 없다(R-a) |
| B3 | 적합 | `finish_seed_rows`(`harness_hydraulics.py:311-330` 부근)가 3.2절 식 그대로다. `m2_previous_unset`은 `release()` 전에 읽고, 클립은 스텝별 `clipped_steps` 차로 본다. 반례 대조(`seed_cx.json`): 정상 +3.69×10⁻¹⁰ N, 시드 뺀 변형 −10,599 N(기대 약 10.6 kN). 기록 끔 실행 비트 동일(`records_off_bit_equal` true) |
| B4 | 부분 | t8·t12·records 도구와 배치 `j9_t8` 66행이 있다. C1·C2·C3이 남았고, T-P3-5 20행은 질문 1 |
| J4a-9 R1 | 적합 | `chain_explanation`(`jp3_baseline_compare.py:235-285`)이 2.2절 (i)(ii)(iii)과 2단계를 그대로 구현한다. lookback 0.3 s + 10⁻⁶ s, 출처는 이름으로 찾는다. 단위 시험 1(설명 안 된 상승 0)·2(사슬 끊긴 뒤 ≥ 1)가 있다 |
| J4a-9 R2 | 적합 | 판정 행은 VBJ·LSJ만 센다. P4-3a 키가 없으면 판정 불가(`:383-395`) |
| J4a-9 R3 | 적합 | `setting_defect`는 종료 2. 정체성 검사는 VBG5 포함 모든 rev 5 행(`:209-216`) |
| J4a-9 R4 | 적합 | rev 5 짝에 열이 없으면 판정 불가. 기준선 확인: A·C 행(VB, LS1~4, VBG4) npz에는 jp3 열이 0개라 "해당 없음"이 맞다. B·D·E 행에는 15열이 있다 |
| R5 | 적합 | `_retract_lock_start_model_Pa(leg, sign, model_Pa) = max(model, tracker)`를 두 적용 지점이 부른다. 값·출처 판정은 diff 전과 같다(`max` 결합 순서, `retract_start > model ⇔ tracker > model`). 모니터·플랜트 다이제스트 동일 보고와 맞는다 |
| R6 | 적합 | `j_p3_inputs.py`의 `REV5_JUDGED_SETTINGS`, 키 없는 rev 5 기록 거부, `status_by_revision` 분리. rev 4 판정은 rev 5 기록을 결함으로 거부(`extend_start_bound.py:1743-1749`) |
| R7 | 적합(C4·R-b 남음) | P4-5a는 정체성, 해시 `3672c7222519`, 다리 합 1이고 FL 1, FL 49.0 s HOLD 간격 +10.674 ± 0.05 bar를 본다. F-A·F-B·F-E 판정 도구가 있다(`jp3_case_judge.py`) |
| R8 | 적합 | run_v5 배치 `j9_case_f` 15행, 이벤트 경로. `jp3_case_f.py`는 삭제됐다 |
| R9 | 적합 | `RET_AFTER_GATE_RESOLUTION` 문장이 T-JR-12 보고에 들어간다 |
| X11 | 적합 | 비교 집합에 X11 행이 들어오면 `setting_defect`. fresh만 켠 행은 기록 |
| 시험 공백 | 적합 | 13.10절 skip 3건은 실행·통과. 공백 4파일은 57/1이고, 1건은 master에서도 같은 기존 실패라 J4a-17 예외로 적는다. 남은 skip 9건(torch 없음 5, 기능 미구현 1, VERIFICATION_EXT 1, YAML 재생성 1, LAS-b 병합 1)은 판정 근거 시험이 아니다. 목록으로 보고하고 통과로 세지 않는다 |
| xfail(1.4절) | 적합 | xfail 0. 기록 시험은 `JP3_RECORD_DIR`·`record_property`로 남긴다 |

## 2. 차단

### C1. T-JR-12: READY 시각 키를 하나만 읽는다(도구 결함)
- 도구는 `jp3_tjr_judge.py:227-228` `_ready_s`에서 `base.t_ready_s`만 읽는다. 반면 r79 판정은 `base.get("t_ready_s", base.get("t_ready"))`로 두 키를 다 본다(`r79_sensor_judge.py:245-247`).
- 저장 H-6(`h6_dg3_v4on.json`, sha256 `ea0ab94c…`)의 READY 키는 계열마다 다르다. 저장 H-7(`h7_dg3_off.json`, `43997bf1…`)도 같은 구조다(t_ready 37, 정말 없음 5).

| 계열 | READY 키 | 행 수 |
|---|---|---|
| ref·g6·g6r | `t_ready_s` | 91 |
| slope·main | `t_ready` | 37 |
| (없음) | 정말 READY 없음 | 7 |

- 이대로면 37행이 "기준 READY 없음"으로 읽혀 VBH 묶음은 반드시 판정 불가다. 기준만 고치고 새 행을 못 고치면 새 행이 'READY 없음 = 실패'가 된다.
- 단위 시험(`test_b4_t12_counts_faults_and_ready`)은 `t_ready_s`만 쓰는 합성 문서라 이 결함을 잡지 못했다.
- 수정: r79와 같은 읽기 함수를 쓰고(또는 가져다 쓰고), `t_ready` 계열 단위 시험을 더한다.
- 정말 READY가 없는 기준 7행(g6r/level 2, slope/probe 2, slope/level 1, ref/probe 2, 모두 L3)의 처리는 질문 2다.

### C2. T-JR-12: "통과 → 실패"를 L2만 판정해야 한다
- 봉인 13.9절은 "실패 판정: **L2** 통과 → 실패 0, 새 FAULT 0, 첫 READY +30 s 초과 0"이다.
- 도구는 `h8.grade_lines`(L0·L1만 제외, `h8_noise_judge_4368.py:72`)로 L2·L3 135키 모두에 pass·flag → fail을 실패로 센다(`jp3_tjr_judge.py:197-207`).
- 선례 Dg-3 v4(`p3_extend_start_spec.md` 13.1)는 "L2 통과 → 실패"만 조건으로 판정했고, "통과→실패/실패→통과(전체)"는 기록이었다. L3 conservative 행은 꺼짐에서도 9키가 실패하는 기록 등급이다(결정 147).
- 수정: 판정은 L2 1행으로 하고, 전 등급 전이는 기록으로 낸다. 새 FAULT와 READY +30 s는 선례대로 135키 전부다.

### C3. T-JR-10: meta 조항 미구현
- 봉인 5.5절 T-JR-10 합격은 "명령 해시 20/20, 22/22. **meta 차이는 끝 상태값만(개정 10 조건 A·B·C)**"이다. t8 도구는 해시만 본다.
- 436.9 코드는 기록 키를 일부러 더했다: `harness_commands_sha256`, B2 증거 2키, 시드 로그 3열, rev 5 `extend_bound_check` 키. 그래서 저장 h10(옛 코드)과의 기록 차이가 반드시 생긴다. python-expert도 "옛 `p3_hash_check.py` 검사 3이 새 키를 차이로 본다"고 보고했다.
- 개정 10 조건 C(끝값 ≥ 저장값 − 1 Pa)는 "③는 올리기만 한다"에 기댄다. rev 5 대 rev 4에서는 R5-1(HOLD에서 ④∨⑤ 사용)이 그 단조성을 보장한다고 증명되지 않았다.
- 필요: 허용 키 목록을 결과 전에 고정하고 조건 적용 방식을 정한다(질문 3). 그 뒤 도구에 넣는다.

### C4. P4-7: 측정량 정의 공개(값을 본 뒤의 해석)
- 봉인 T-JR-04 ⑪b-P1 문장은 "첫 HOLD 읽기 초과 $p_{tr}-④$ = +27.4 bar(± 0.5 bar, 유압 검토 표의 … 최대)"다.
- +27.4는 유압 검토 11.1절 지표 "초과 = $p_{tr}-(13+p_h/3)$, 참 헤드"의 값이다(q1 행: 27.213 bar).
- 시험은 q1 정의(`_first_excess_bar`, 참 헤드, `test_jp3_rev5_property.py:675-679`)로 assert한다. 기록값(`records_full/P4-7.json`):

| 경우 | q1 정의 초과 | $p_{tr}-④$ | R5-7 여유 |
|---|---|---|---|
| N = 14 | +27.204 bar | +28.468 bar | 50.82 bar |
| N = 12 | +29.194 bar | +30.444 bar | 48.62 bar |

- 두 띠(0·4 kN) 값은 같다.
- 글자대로의 $p_{tr}-④$는 ±0.5 밖이다. ④가 판독 헤드(참값 − 4.62 bar)로 계산되기 때문이다.
- 원인은 명세 작성자(control-expert)의 표기 오류다. 참조값의 정의는 q1 지표인데 문장에는 $p_{tr}-④$로 적었다.
- 처리안(질문 4): q1 정의로 회귀 대조하고, $p_{tr}-④$는 기록하며, 판정서에 "값을 본 뒤 정한 해석"으로 공개한다. 4a-2 6절(N = 14 기준)과 같은 성격의 사후 해석이다.

### C5. 판정 입력·근거 파일 미추적(실행 전 절차)
- `git status`에서 다음이 모두 `??`다. 일부는 직접 sha256을 쟀다.

| 파일 | sha256 앞부분 |
|---|---|
| `06_analysis/03_hydraulic/coupled/v5/resume_k1/h10_reuse_rerun.jsonl` | `ce526b1f71e635e6…` |
| `resume_k1/h6_dg3_v4on.json` | `ea0ab94c…` |
| `resume_k1/h7_dg3_off.json` | `43997bf1…` |
| `resume_k1/h9_grid/grid_r67_top.json` | `7160f9f1…` |
| `06_analysis/02_control/j_p3_cause/j4a_remedy_3b949f5/` | (폴더 안 `SHA256SUMS`가 있다) |
| `jp3_remedy_spec_addendum_4a2.md` | `2f3e36bd…`, `.sha256` 파일과 같다 |

- 판정 도구가 입력 sha를 기록하기는 하지만, 기준 파일은 실행 전에 고정해야 한다(`git add -f` 또는 고정 목록). verif-protocol-auditor 실행 전 감사 항목이다.

## 3. 권고

| # | 내용 |
|---|---|
| R-a | B2 건식 확인이 보고에 없다(4a-2 B2 "고친 뒤 VBJ F 1행 건식 확인"). 판정 대상이 아닌 잡(j9_cases·j9_case_f·j9_t8·Dg-3 135에 없는 행)으로 세 경로를 돌리고 증거 2키만 읽기를 권한다: 이벤트 경로 P4 켬(①=②>0), P4 끔(①=0), r79 `plant_truth`. `jp3_case_replay.py` C·D 행에 증거 키가 있는지도 본다. 키가 없으면 비교 전체가 `setting_defect`가 된다. ①은 매 판독 함수 호출에서, ②는 시각이 일치할 때만 세므로, 둘이 같은지는 실행으로만 확인된다 |
| R-b | F-A 경로 동등성. `j9_case_f`는 r67 screen 행을 이벤트 경로로 다시 구성한 것이다. 판정 대상(results[13].runs[3])이 아닌 같은 격자 파일의 다른 run 하나로, `harness_commands_sha256`가 저장 `commands_sha256`를 재현하는지 먼저 보인다. 그렇지 않으면 F-A 실패가 회귀인지 경로 차이인지 가를 수 없다 |
| R-c | T-JR-12 VBJ 묶음에서 기준 VBJ0 행에도 증거(P4 켬, ①=②>0) 검사를 건다(지금은 새 행만, `jp3_tjr_judge.py:174-177`) |
| R-d | T-JR-10: 도구가 저장 h10 행의 태그(`final_C4G2_P3_LAS_K1`)와 `rule_revision` 4를 assert하게 한다. `j9_t8`에 VB 22행 재실행을 기록으로 더해, 저장값이 낡은 경우와 T8 결함을 가른다 |
| R-e | P4-6 1 mm/s × 0.2 s 행의 `model_only` −20.008 bar는 기준 −20 bar와 0.008 bar 차로 통과다. 시험 상수 훅의 건전성 확인 값이라 기준은 바꾸지 않는다. 판정서에는 경계 근접으로 정확한 값을 적는다 |
| R-f | 4a-2 1.1 공개 문장의 수치는 기록값으로 적는다. 1 mm/s 두 행은 HOLD 시작 $p_{tr}$ 48.50·44.33 bar(표 55.35·50.95, −6.85·−6.62 bar), R5-7 간격 43.46·47.63 bar(하한 5.05·9.45), 관문 열림 2.906 s다. P4-7 값은 C4 표대로 쓴다. 0.3 mm/s 네 행은 관문 미개방, 사용 상계 − $p_{tr}$ ≥ 11.0 bar다. "약 0.13 s"는 기록에 없으니 "N 12 대 14"로 쓰거나 관문 시각을 기록한다. 4a-2 1.1의 멈춤 조건(부호가 다르거나 건전성이 깨짐)에는 해당하지 않는다 |
| R-g | 옛 `p3_hash_check.py` 검사 3을 쓰는 판정(T-JR-01 h10 대조 등)이 있으면 C3의 허용 키 목록과 맞춘다 |

## 4. 확인 필요 5건(python-expert) 권고

| # | 권고 | 근거 | 봉인 문장과의 관계 | 결과 전 여부 |
|---|---|---|---|---|
| 1 | 20행 → 22행 규칙으로 바꾸고 공개. 도구는 22행만 판정한다 | 20행 목록은 저장소에 없다. 개정 8 7.2절(`v5_criteria_rev8.md:125`)이 같은 이유로 "20행"을 22행 규칙으로 이미 바꿨다. 22행은 22사례를 모두 덮는다 | 봉인 문구 "20/20"을 바꾸는 것이라 사용자 결정(질문 1) | 결과 전(T8 미실행) |
| 2 | `resume_k1/h10_reuse_rerun.jsonl`(sha256 `ce526b1f…`) | 명세가 "저장 VB"를 이미 h10으로 쓴다(5.3절 A 행 "저장 h10 줄", T-JR-01 "h10 줄 28·172·245"). `p3_hash.jsonl`과 `main.jsonl`은 옛 태그다. R-d 조건(태그·rev 4 assert, VB 재실행 기록)과 C5 sha 고정을 붙인다 | 명세 안 용례와 같은 해석. 공개만 | 결과 전 |
| 3 | pass·flag → fail은 동의한다(flag는 실패가 아님, `h8` 등급 정의). C1 READY 키를 고친다. 판정 범위는 C2대로 L2만. 기준 READY 없음 처리는 질문 2. P4는 VBJ·VBJ0에 `R79_ROD_MODEL=plant_truth`가 맞다(r79가 같은 함수를 부른다). 증거 검사로 빠진 경우를 잡는다(R-c) | 13.9절, Dg-3 v4 선례 13.1, `r79_sensor_judge.py:245-247` | C2는 봉인 문구대로 되돌리는 것. READY 없음 처리는 봉인 문장이 정하지 않은 경우 | 결과 전(기준 파일만 셈) |
| 4 | 동의. sha256 `7160f9f1…`로 고정 | 명세 입력 원본이 이 경로를 명시한다(`jp3_cause_report.md:36` `.../resume_k1/h9_grid/grid_r67_top.json` results[13].runs[3]). 직접 확인: 키 `screen|top|8.0|ready|FR`, G4, 0.075 s, 해시 `3a50f96eadf3`, 태그 `final_C4G2_P3_LAS_K1`, FR 3 / −0.9000863 bar @ 48.7 s. `grid_vb/` 판에는 `extend_bound_check`가 없어 F-A 대조가 안 된다 | 봉인 문장 그대로 | 결과 전 |
| 5 | 동의(다리 합 1이고 FL 1) | 봉인 13.3절 "FL 49.0 s HOLD 읽기에서 J-P3b 허용 초과 1건". 도구는 그 읽기의 간격 +10.674 ± 0.05 bar(허용 0.6 kN/$A_{ann}$ = 전방 1.59 bar보다 큼)도 보므로, 합이 1이면 그 1건이 곧 이 읽기다 | 봉인 문장의 직접 구현 | 결과 전(X11 미실행) |

## 5. 확인 필요 질문(사용자)

1. T-JR-10/11 "20행"을 개정 8 7.2절 선례대로 22행 규칙으로 바꿀까요? 권고는 바꾸는 것입니다(결과 전). 바꾸지 않으면 T-JR-10/11은 영구히 판정 불가입니다.
2. T-JR-12에서 기준 행에 READY가 없는 짝(저장 H-6의 L3 7행)을 어떻게 판정할까요? 권고는 다음과 같습니다(결과 전, Dg-3 v4 선례).
   - 기준·새 행 둘 다 READY 없음: 기록
   - 기준 없음, 새 행 READY 도달: 기록(개선)
   - 기준 도달, 새 행 READY 없음: 실패
3. T-JR-10 meta 조항을 어떻게 적용할까요? 권고는 다음과 같습니다(결과 전).
   - 판정: 개정 10의 A(대체 사건 0)와 B(명령·사건 동일)
   - 436.9 코드가 더한 기록 키: 허용 목록으로 결과 전에 고정
   - C(끝값 ≥ 저장값 − 1 Pa): rev 5 대 rev 4에서 단조성이 증명되지 않았으므로 기록으로 낮춤
4. P4-7을 q1 정의(참 헤드 기준 초과, N = 14에서 +27.204 bar)로 회귀 대조하고, $p_{tr}-④$(+28.468 bar)는 기록하며, 명세 작성자의 표기 오류로 공개할까요? 권고는 그렇게 하는 것입니다(값을 본 뒤의 해석이라 공개).

## 6. 수행한 작업

- `git diff ad5024b 3b949f5`를 읽었다: 제어기 3파일, 하네스, `j_p3_inputs`, `jp3_baseline_compare` 전체, `jp3_case_judge` 전체, `jp3_tjr_judge` 전체, `run_v5`, 시험(`test_jp3_addendum_4a2.py`, `test_jp3_rev5_property.py` P4-6·P4-7 부분).
- 근거 폴더 `j4a_remedy_3b949f5/`를 확인했다(`SHA256SUMS`, `seed_cx.json`, `records_full/P4-6_*`, `P4-7.json`, junit 요약).
- 읽기 전용 스크립트 5개를 `conda run -n dynamics-dev python -I -B`로 돌렸다(scratchpad `control-4a2-rereview\`, 지금은 지움).
  - 저장 H-6·H-7의 READY 키 계열·READY 없는 행 수
  - `grid_r67_top` results[13].runs[3] 값과 파일 sha
  - 기준선 npz의 jp3 열 이름(값 아님)
- `Get-FileHash`로 h10과 4a-2의 sha를 쟀다.

## 7. 가정

- 제어기 비트 동일은 python-expert의 다이제스트 보고(모니터 552c768a…, 플랜트 7404b793…)와 diff 대조(값·출처 동치)에 기댄다. P4-1·P4-4 기준선 직접 대조는 사례 재생 뒤에야 한다.
- B2 ①=② 동치와 F-A 해시 재현은 실행해야 확인된다(R-a, R-b).
- 저장 H-6 READY 없는 7행은 지금 키 구조로 센 값이다. VBH·VBJ0에서 몇 행이 READY에 닿지 않을지는 실행 뒤에야 안다.

## 8. 핸드오프

- 위임 필요(python-expert): C1·C2·C3(질문 3 답 뒤), R-a~R-g(R-e는 판정서 기록 항목).
- 위임 필요(verif-protocol-auditor): C5 판정 입력 sha 고정, 질문 1~4 결정 문안의 실행 전 감사.
- 위임 필요(control-expert, 명세): 질문 1~4의 답을 정리한 덧붙임 문안(4a-3 또는 판정서 공개 문장).

## 9. 사용자 결정(2026-11-20, 메인 세션 덧붙임)

- 질문 1: T-JR-10/11 "20행"을 개정 8 7.2절 선례대로 22행 규칙으로 바꾸고 공개한다.
- 질문 2: T-JR-12 READY 없음은 Dg-3 v4 선례대로 처리한다. 둘 다 없음 = 기록, 기준 없음·새 행 도달 = 기록(개선), 기준 도달·새 행 없음 = 실패.
- 질문 3: T-JR-10 meta 조항은 개정 10의 A·B로 판정한다. 436.9가 더한 기록 키는 허용 목록으로 결과 전에 고정하고, C는 기록으로 낮춘다.
- 질문 4: P4-7은 q1 정의(참 헤드 기준 초과)로 회귀 대조한다. $p_{tr}-④$ 값은 기록하고, 명세 표기 오류이며 값을 본 뒤 정한 해석임을 공개한다.
