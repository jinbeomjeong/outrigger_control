## 감사 요약(판정 후 — 확인 단계 (가) 멈춤)
- 대상·시점·기준 문서: [시점] 판정 후. 판 6 본 실행(실행 커밋 79495405)의 confirm 단계, `confirm_a_judge` 종료 1.
  - 기준 문서: 봉인 `jp3_remedy_spec_v6.md`(07a55e17) 6.2·6.3 (가)·4절 멈춤, 정오 1(1d4f7539)·정오 2(20a60e57)·정오 3(bae389a3), v5 기준 `v5_criteria.md` 55~65행(J1~J11), 436.8 규칙 rev3 R3-C6.
  - 판정 근거
    - 결과: `06_analysis/02_control/j_p3_cause/j9_runs/79495405/confirm_a1/confirm_a.jsonl`(2f3b3587, 216줄)
    - V0: `06_analysis/03_hydraulic/coupled/v5/main.jsonl`(9ad74990)
    - 키 파일: `ed6_design/keys/confirm_a_keys_v2.json`(75413549)
    - 판정 출력: `confirm_a1/judge/confirm_a_judge.json`(4f6902ae)
- 본 결과
  - `confirm_a.jsonl`·V0 짝 줄: 판정 항목 값, 사건 이름, 정체성 필드, J-P3 침범 합계
  - `confirm_a_judge.json` 전문
  - 격자 `confirm_b.jsonl`: key_presence로 키 존재만 셌다(값 비출력). `confirm_b.log/err`와 T4h는 열지 않았다.
  - 블라인드 경로는 Read·Grep·Glob 어디에도 넣지 않았다.
- **판정: 차단 0 / 실행 전 수정 0 / 기록 4, 확인 필요 1**
  - 도구 판정 "failed"(군집 규칙 k = 2)는 원본에서 다시 세어도 같다.
  - 실패 단위 8개, 군집 VBLv15 R12, 단일 2, J7 예외 10단위, 읽기 (1) 이동 0, J-P3 판정 행 56·침범 0, 정체성 결함 0까지 모두 같다.
  - J7 대체(fallback) 읽기와 군집 묶음 단위를 어떻게 읽든(네 가지) 결론은 **failed**로 같다. 멈춤 처리(재실행 없음, 뒤 단계 미실행, 격자 미판정)도 규칙과 코드대로다.

## 재집계 표(C)
판정 도구 함수를 import하지 않았다. 원 줄과 v5 기준 문면으로 다시 구현했다(python-dev 스크립트). 짝은 job(설정 제외)으로 맞췄다.

| 항목 | 판정 출력 | 재집계 | 차이 | 판단 |
|---|---|---|---|---|
| 줄 수 / 키 파일 job 집합 일치 / 오류 줄 | 216 / – / – | 216, 집합 같음, 오류 0 | 0 | 일치 |
| V0 짝 없는 단위 | 0(no_reference 없음) | 0 | 0 | 일치 |
| 판정 단위 / probe 단위 | 216 / 0 | 216 / 0(키 파일 probe_seen 0) | 0 | 일치 |
| 읽기 (1) 이동 | 0 | V0가 J1 관문을 실패한 짝 0 | 0 | 일치 |
| J1 사건 관문 새 실패 | 3(VBLc04 top-FR-Fs0 o0.0, VBLv05·VBLv15 top-FR-Fs0 o0.05, `end_att`) | 3, 같은 단위 | 0 | 일치. VBLv15 R12에서는 `pair_recount.py`로도 gate_new 1(같은 단위·관문) |
| J1 정상 행(harness_class) | 0 | 0(160줄) | 0 | 일치 |
| J2(E-3 < F_min, V0 통과) | 0 | 0 | 0 | 일치 |
| J4(V0 ready → 다른 단계) | 3(ready → probe) | 3, 같은 단위 | 0 | 일치 |
| J5(`t_ready_back_s` 없음, V0 있음) | 3 | 3, 같은 단위 | 0 | 일치 |
| J6(`att_end_deg`) | 0 | 0 | 0 | 일치 |
| J11(대체 다리 n_late > 0 / None) | 0 | 0 / 0 | 0 | 일치 |
| J7 새 이름(첫 `:` 토큰 기준) | 판정 기록 10(모두 `WARN_PROBE_STIFFNESS_OUT_OF_RANGE`) | 10단위(VBLv15 R12 Fs8 6, R7 4), 새 이름은 이 경고 하나뿐 | 0 | 일치 |
| J7 예외 적용(감도 설정, 단독 조건) | `j7_stiffness_exempt` 10 | 10, 같은 단위 집합 | 0 | 일치 |
| J7 대체 사건(`WARN_ROD_PRESSURE_FALLBACK`) | 실패 5단위(VBLv15 top-FR-Fs0 o0.0, top-RL-Fs0 o0.0·o0.05, top-RR-Fs0 o0.0·o0.05) | (이름, 제어 주기) 읽기로 5, 같은 단위. 이름 읽기로는 0. V0도 FL 대체가 있고 주기만 다르다(V0 673~708 / VBLv15 710~733) | 읽기에 따름 | 아래 확인 필요 1 |
| 실패 단위 | 8 | (이름, 주기) 읽기 8(집합 같음) / 이름 읽기 3 | 읽기에 따름 | 도구 = (이름, 주기) 읽기 |
| 군집, (설정, 행) 묶음 | 군집 [VBLv15 R12], 단일 2, failed | 읽기 B: 같음. 읽기 A: 군집 0, 단일 3 > 2 → failed | 0 | 결론 불변 |
| 군집, (설정, 행, G4 키) 묶음 | – | 읽기 B: 군집 3(VBLv15 top-FR/RL/RR-Fs0), 단일 2 → failed. 읽기 A: 단일 3 → failed | – | 결론 불변 |
| R15 나빠짐(정오 3 3-1) | "not applicable" | 키 파일 R15 줄 0 | 0 | 정오 3 9항대로 |
| S8 읽기 (3) | 해당 없음 기록 16 | 재계산하지 않음(기록 항목) | – | 검사하지 못한 것 |
| J-P3 판정 행 / 침범 | 56 / 0, rev6 pass | `head_only_declared` 거짓 56(4설정 × R12 14, 키 파일 기대 56), `rule_revision` 6·`spec_edition` fe6f5844 56/56, jp3a + jp3b_over_tol + jp3c 합 0 | 0 | 일치 |
| 정체성 | 결함 0 | 태그 216/216 `final_C4G2_P3W_LAS_K1_LSB`, `lsb_components` 216/216 {A_i, A_ii, B3}, `lsb_settings` 1종이며 b1off 봉인 구성 줄과 같음 | 0 | 일치 |
| 상태 | failed(근거 "cluster rule (k = 2)") | failed(모든 읽기) | 0 | 일치 |

## 발견 사항

**[기록][R] 1. J7 대체 사건의 "새 항목"을 (이름·다리, 제어 주기)로 비교한다. V0와 같은 다리 대체가 시각만 다르면 실패로 센다**
- 근거
  - `judge_stage1_4368.py:173~175` `fallback_436 = {(n, control_period_index(t))}`, `:302~307` `(name, n) not in base_fallback`이면 J7 fail(판 5부터 쓴 436.8 계열 도구).
  - 규칙 원문
    - `v5_criteria.md:61`: "J7 | 새 FAULT·WARN | 이름 집합, `WARN_ROD_PRESSURE_FALLBACK`은 사유(D1~D6)와 시각까지 | … | V0에 없던 FAULT, WARN, 대체 사유"
    - `v5_resume_4368_rules_rev3.md:219~220`: "원 규칙대로 사유(D1~D6)와 시각까지 본다. **대체 시각 차는 기록이다.**"
  - 이번 5단위는 모두 V0에도 `WARN_ROD_PRESSURE_FALLBACK:FL`이 있다(V0는 네 다리, VBLv15는 FL 하나). 제어 주기만 2~59주기 다르다.
  - 사유 비교는 할 수 없다: VBL 줄은 `lock_window_alignment.fallback_legs.FL.reason` "D6"이다. V0 줄(r5)에는 `lock_window_alignment`가 없어 사유를 모른다.
- 영향: 이 판에서는 결론이 바뀌지 않는다(재집계 표). 근거 문장은 달라진다. 도구 읽기면 "VBLv15 R12 군집 + 단일 2", 시각 차를 기록으로 읽으면 "단일 3 > k"다.
- 권장: 판정서에 두 읽기와 결론 불변을 적는다. 다음 판 전에 R3-C6의 "시각 차는 기록"과 도구의 주기 비교 중 어느 쪽인지 정한다(확인 필요 1).

**[기록][R] 2. 군집 규칙의 "행"이 G4 쌍둥이 키를 모두 R12 하나로 묶는다**
- 근거: `jp3_ed6_judge.py` `cluster_rule`은 `(setting, row)`로 센다. 지표 행의 row는 "R12"이고 phase는 "top|FR|0|0.0" 꼴이다.
  - 명세 6.2: "한 (설정, 행)에서 미관측 위상 2개 이상이 실패". 6.3 (가) 근거: "G4 나머지 7키 × 2위상".
  - 명세 문면은 키 단위(위상 = 오프셋)로도 읽힌다.
- 영향: 네 조합 모두 failed라 결론이 바뀌지 않는다. 군집 수(1 대 3)는 읽기에 따라 다르다. 판정서에 적는다.

**[기록][I] 3. 예외 대상 확인: `WARN_ROD_PRESSURE_FALLBACK`은 J7 예외 대상이 아니다. 도구 동작이 맞다**
- 근거: 명세 6.2 예외는 "J7 새 항목 집합이 `WARN_PROBE_STIFFNESS_OUT_OF_RANGE` 하나뿐일 때만"이다. 대체 5단위의 새 항목은 대체 사유뿐이고 강성 경고는 없다(재집계). 그래서 예외가 걸리지 않는다.
- 강성 경고 예외 10단위는 모두 VBLv15다(R12 Fs8 6단위, R7 4단위).
  - 봉인 전 census는 경고가 "R12 계열"에서만 나왔다고 했다. R7은 이번에 처음 나왔다. 판정서 공개 대상이다.
  - 다른 3설정(c005·c04·v05)에서는 0이다.

**[기록][T·E] 4. 멈춤 처리 상태**
- confirm 단계는 run 2개(종료 0)와 identity check(0), L1 입력 가드(0)를 거쳐 `confirm_a_judge` 종료 1에서 Stop-Step 1로 멈췄다(`confirm.stop`, `step_record.json`). `confirm_b_judge`는 실행되지 않았다(`judge\` 파일 2개뿐).
- 뒤 단계(j9main·dg3·12b) 폴더와 표지가 없다. 러너 로그 `logs_r2\confirm.log` `[end] confirm exit=1` 뒤에 `[start]`가 없다.
- 재실행 거부: `confirm.stop` codes `tool:confirm_a_judge = 1`이다. `Read-PreviousStops`(common_ed6.ps1:118~130 → `Get-RefusedPreviousStop`, `$RecordCodeTools`에는 `tool:t12_VBL`만 있음)가 새 시도를 Stop 2로 거부한다. `confirm_a1` 폴더도 이미 있다.
- 빈 집합(E): 판정 단위 216, J-P3 판정 행 56(0 아님), 짝 없는 단위 0.
- 격자 (나): 192줄과 T4h 192가 **실행됐지만 판정되지 않았다**. 다섯 키(`event_output.pass/gates.fault0/fault_periods/fault_events`, `events`)는 192/192 있다(key_presence 종료 0).
  - 이 출력을 나중에 기록으로라도 열면 (가) 결과를 본 뒤의 열람이 된다. 열람 여부와 시점을 판정서에 공개해야 한다. 그 전까지는 `confirm_b.*`(log·err 포함)를 블라인드로 두길 권한다.
- 순서 근거: P6-4(79495405)는 10:06에 커밋됐고(3eee6100) l1ref는 10:35에 시작했다. 고정 목록 `FIXED_INPUTS_79495405`는 11:43 커밋(bdb3739d), step5 시작은 11:44다. 실행 전 감사 권고 순서와 맞다.

## 규칙↔도구 대조(R, 이번 단계에 해당하는 것)

| 규칙 | 도구 | 결과 |
|---|---|---|
| 6.3 (가) 216단위, 키 파일 sha, 줄 누락 판정 불가 | `load_key_file`·`matched_lines` | 216, sha 일치, 누락 0 |
| 6.3 (가) 6.2 군집 규칙 k = 2 | `cluster_rule`(군집 ≥ 2위상 또는 단일 > 2) | 문면과 같음(행 묶음은 발견 2) |
| 6.2 J7 예외(감도 4설정, 단독 조건, 첫 `:` 토큰) | `apply_j7_exception` | 10단위 적용, 대체 사건 미적용(발견 3) |
| 6.2 읽기 (1)·(3) | `apply_reading_1`·`s8_items` | 이동 0, S8 해당 없음 기록 16 |
| 6.3 (가) J-P3 기대 56 | `jp3_basis(jp3, 56)` | 56, 침범 0 |
| 6.1 정체성(태그·rev 6·spec_edition·lsb 집합·lsb_settings) | `ed6_identity_problems` | 결함 0(재집계 일치) |
| 정오 3 3-1 9항(R15는 sens 키 파일에만) | `R15_KEY_FILE` 조건 | "not applicable" |
| 4절 멈춤(종료 1은 멈추고 묻는다, 재실행 금지) | Stop-Step, Read-PreviousStops | 일치(발견 4) |
| 6.3 "확인 단계가 실패하면 판 6은 합격이 아니다, 결과를 본 뒤의 설계로 고치지 않는다" | – | 판정서·다음 판 몫. 사전 예측 P6-5 "군집 실패 0·단독 ≤ 2"는 맞지 않았다. 판정서에 대조를 적는다 |

## 확인 필요
1. (발견 1) J7의 `WARN_ROD_PRESSURE_FALLBACK` 비교를 정해야 한다.
   - R3-C6 "대체 시각 차는 기록"을 따르면: V0에 같은 다리 대체가 있고 주기만 다른 경우는 기록이다.
   - 도구대로라면: (이름, 주기)가 다르면 J7 실패다.
   - 판 6 결론에는 영향이 없다. 판정서 근거 문장과 다음 판 도구에 영향이 있다.
   - 판 5 j9_main 판정이 같은 도구로 이 읽기를 썼는지도 함께 확인하길 권한다(이번에는 보지 않음).
   - 결정 주체: 사용자 또는 control-expert.

## 위임 필요
- `tools/verif 후보`(python-expert): `pair_recount.py` 실데이터 공백을 보고한다.
  - (a) 키 일부가 없는 기준 줄을 건너뛰거나 null로 읽는 옵션이 없다. V0 R12 중 twin 없는 줄이 `key_missing` error를 낸다.
  - (b) 한 판정 파일에 여러 설정이 같은 키로 있으면 `judged_where`로 설정마다 따로 돌려야 한다. 반복 실행이 필요하다.
  - (c) 항목은 원 pass 값만 받는다. J4(단계 비교)·J5(None 여부)·J7(이름 집합, 주기 쌍)·예외·군집 규칙은 표현할 수 없다.
  - (d) `--out`이 설정 파일 폴더의 하위에 있어도 거부한다. 설정은 `cfg\`, 출력은 형제 `out\`에 두면 된다(README에 한 줄 추가 권장).
  - 이번 J1 관문 대조(VBLv15 R12, 짝 14)는 도구로 했고 나머지는 즉석 스크립트로 했다.

## 메인 세션 권고
- 판정서를 쓰기 전에 확인 필요 1을 정한다.
- 격자 `confirm_b.*`를 열지 여부를 사용자에게 묻고, 결정 전에는 블라인드로 둔다(발견 4).
- 판정서에 적을 것
  - 두 J7 읽기와 두 군집 묶음에서 모두 failed라는 점
  - J7 예외 10단위(R7 포함, v15만)
  - 사전 예측 P6-5 대조
  - (나) 미판정과 그 출력의 열람 상태

## 검사하지 못한 것
- J3(첫 READY 한계), J8(부호 전환·리밋 사이클), J9·J10, S8 SA-4·F-5의 독립 재계산. 도구는 모두 0으로 냈고 상태 결론과는 무관하다.
- V0 대체 사유(D1~D6): V0 줄에 기록이 없다.
- 판 5 j9_main의 대체 주기 비교 사례.

## 실행한 검증
- 인터프리터: python-dev `python.exe -I -B -X utf8`(TBB), PowerShell. 프로젝트 모듈은 import하지 않았다.
- 즉석 스크립트(scratchpad `auditor-ed6post\`, 끝나고 지움)
  - inspect.py·inspect2.py: 구조·키 이름
  - recount.py: 짝, J1·J2·J4·J5·J7 두 읽기, 예외, 군집 두 묶음, 정체성, J-P3
  - fallback.py: 대체 기록 위치
  - extra.py: J1 정상 행, J6, J11, lsb_settings 대 b1off
- 도구
  - `pair_recount.py`(cfg\·out\, VBLv15 R12 J1): 짝 14, gate_new 1. key_missing 1과 unpaired_reference 14는 도구 공백이다.
  - `key_presence`: confirm_b 키 8개 192/192, confirm_a 정체성 키 216/216
- 확인한 것: 러너 로그 `[start]/[end]` 줄, git 커밋 시각(P6-4·고정 목록)
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha confirm_a.jsonl 2f3b3587…, confirm_a_judge.json 4f6902ae…, confirm.stop 86124a56…, step_record.json 86124a56…, confirm_a_keys_v2.json 75413549…, main.jsonl 9ad74990…, jp3_remedy_spec_v6_erratum3.md bae389a3…, 디렉터리 목록 동일, ~$ 임시 파일 없음) · 경고: 형제 항목 수정 시각만 변경 1건(ed6_design)
  - ed6_design 폴더의 수정 시각 변경은 이 감사가 아닌 다른 작업의 쓰기다. 입력 파일은 바뀌지 않았다.
- 메모리: `audit_pitfalls.md`에 일반 함정 1항목을 더하고 MEMORY.md 색인을 갱신했다.
- 사용한 스킬: 없음
