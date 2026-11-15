# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev19 (R3b 도구 구현 질문 뒤: 427.9 안전 종료 등급, PS-c 기준 행·C1 기록 행, 사건 E 항목 창, 러너 passed None, 러너 t_lift 항목, VB↔V0 짝, E-7 도구 확인, 결과 본 뒤 개정, 봉인)

- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev19.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev19_seal_candidate_draft.md`와 1·3·5·9행만 다르다.
- 원판~rev17은 고치지 않는다. 이 판은 rev18(sha256 `3693a69c3f04eb6c5b26556ec5997d081e38f8f6fa6a581aee66ba512d122a9e`, 봉인 2026-11-15 14:28:43 +09:00, 봉인 기준 커밋 S5 `de195938ce9ae0da90769ac475298f5e74314bf7`, 봉인 파일 커밋 S6 `59c933b50d6a32db999c42951d3c168cd552640d`, 브랜치 `z4373-s4`) 위에 쌓인다. 봉인 뒤 이 판과 앞 판이 다르면 이 판이 맞다. 이 판이 말하지 않는 것은 앞 판 그대로다. 용어(봉인 기준 커밋, 봉인 파일 커밋)는 rev16 4행과 같다.
- **시점: R3b 도구 브랜치의 구현 질문과 해석(경로 1 `z4374-p1chrono` `6390747`의 README 9절, 경로 2 `z4374-p2chrono` `6d4b490`의 README 6절 질문 표)을 본 뒤, `z4373-r3b`를 만들기 전, 메인 checkout은 R3(봉인 2026-11-15 15:25:13 +09:00, 봉인 기준 커밋 59c933b).** 이 판은 결과를 본 뒤의 개정이다. 본 자료는 R19-0에 적었다.
- 작성: control-expert, 2026-11-15. 기준: R2 `b9f5707`(실행), R3 `576eb87`(판정 도구), S6 `59c933b`(rev18).
  - 계기: R3b 두 도구 브랜치가 rev18 R18-2·R18-3을 구현하면서 원 규칙이 정하지 않았거나 두 경로가 다르게 읽은 곳을 질문으로 올렸다.
  - 사용자 결정 63·64·65(2026-11-15)와 봉인 전 감사(대상 초안 `20c68016`, 차단 0·권고 4·확인 필요 1)를 R19-1~R19-10에 반영했다. 결정 64는 R19-4(러너 셈 그대로, 묶음별 러너 미판정 항목 수·이름 공개), 결정 65는 R19-1의 `allowed_stop` 셈이다.
- **봉인본이다.** 봉인 전 확인 필요는 없었고(S6 해시·rev18 봉인 sha는 4행), 사용자 결정 63·64·65(2026-11-15)와 봉인 전 감사(대상 초안 `20c68016`)의 권고는 R19-1~R19-10에 반영했다(결정 64 = R19-4 러너 셈 그대로·묶음별 러너 미판정 항목 수·이름 공개, 결정 65 = R19-1 `allowed_stop` 셈).
- **바꾸지 않는 것**: 숫자 문턱, 등급과 우선순위(원판 8.1), 멈춤 조건의 뜻(원판 8.2), 묶음 범위와 행 목록, 사전 예측, 두 경로 요건, 실행 커밋 R2, 이미 돈 실행의 argv·코드, rev16~rev18의 다른 조항. 이 판이 더하는 것은 원 규칙에서 읽어 낸 항목 정의와 창, 러너 출력을 읽는 방법, R3b 순서·허용 목록의 rev19 반영이다.

## R19-0. 결과 본 뒤 개정의 공개 (본 자료 목록)

- 이 작성자(control-expert)가 본 것(읽기 전용, 2026-11-15): 경로 2 `path2_chrono/README.md` 6절 질문 표(T-1~T-7), 경로 1 `04_scripts/02_chrono/chrono_rows_judge_4368_README.md` 9절(러너 행 분기 표, C-5 짝, 러너 t_lift 항목), `chrono_bundle_grade_4368.py`(`30ef4b1`), `judge_b9f5707/chrono_path1/runner_judge/`의 러너 판정 출력 10개(`meta.failed`·`meta.hold`와 행 셈의 대조만), R3 판정 출력(rev18 R18-0 목록 그대로).
- 원 규칙 근거로 읽은 것: 명세 `s6_control_spec.md` 426.3(17246행 부근)·427.9(17680~17699행), `04_scripts/03_control/s9/soil_guard_stop_rule.py` 머리 문서(1~23행), `s9_soil_slope.py` `classify`(976~979행), `s9_soil_event_screen.py` `_pressure_rows`(481~497행)·E 항목 표(550~557행), `04_scripts/03_control/s8/r67_g1_screen.py` `judge_event`(309~373행), `04_scripts/02_chrono/run_S9.py` 1185~1195행·`soil_event_stop_s`·`judge_chrono_soil_event`(1374~1446행), `03_src/outrigger_sim/verify/s8_control.py` `_row`(407행)·CB 집계(3115~3126행)·`meta`(5477~5482행)·`judge_summary`(7523행), `verify/s6_control.py` 1196~1209·1261~1271·1991~2000·2096~2099·2318~2338행, `d1_selection_rules.md` 7·11절, rev3 R3-G10(Q-13·Q-14), rev6 R6-A(D-26~D-39)·R6-B4·R6-B5·R6-B8·R6-B9, `git diff f46b5ab 59c933b -- 04_scripts/03_control/s8/r67_g1_screen.py`.
- 판정서에는 이 목록을 그대로 싣는다. 이 판의 정의는 위 질문·해석을 본 뒤 정했으므로 "결과 본 뒤 정한 정의"로 적는다. 정의는 원 규칙 문장과 원 판정 도구에서 정했고, 어느 경로의 값으로 정하지 않았다.

## R19-1. S-01~04 427.9 안전 종료 등급 (rev18 R18-2 "S-01~04" 글머리의 고쳐 씀)

- **[정의] 분류**: 정지 사유가 토양 가드인 행(첫 `FAULT*` 사건이 `FAULT_LIFT_STROKE_LIMIT:soil:<legs>`)의 등급은 427.9 조건 1~5만으로 정한다. 모두 참이면 `allowed_stop`, 하나라도 거짓이면 `fail`이다. 근거: 명세 17690~17692행 "판정 분류", `s9_soil_slope.py` `classify`(토양 정지면 이 다섯 조건으로만 분류), rev6 R6-B8(D-26).
- **[정의] 기록으로 내리는 항목**(그 행에서 등급에 쓰지 않고 값만 적는다): P3-1~P3-9 전부(하위 키 포함, `P3-3_within`, `P3-6_ready`·READY ≤ 120 s(D-28), P3-6 FLAG(D-27)), P3 FAULT 0(FAULT0), S-03·04의 G6-1~G6-7(`G6-3_pass`, `G6-6_fault_ready` 포함), 그 밖에 READY·DONE·끝 자세에 기대는 항목. rev18 R18-2의 "그때 P3-5·P3-6·FAULT0은 이 조건으로 대신한다"는 이 목록의 예로 읽는다. 근거: `classify`는 토양 정지 행에서 이 항목을 보지 않고, `STROKE_LIMITED_REQUIRED_ROWS`(P3-1·P3-3·P3-4)는 `stroke_limited_pass`에만 쓴다.
- **[정의] 조건과 창**(Chrono SCM 행)
  1. 정지 사유: 그 행 `result.json` `events`의 첫 `FAULT*` 사건 이름이 `FAULT_LIFT_STROKE_LIMIT:soil:`로 시작한다.
  2. `FAULT_STROKE_END` 사건이 실행 전체에서 0개다.
  3. 다리 부상 0: 첫 LEVEL 시작(`s9_rows`에서 `c2_phase` = `level`인 첫 행의 시각)부터 기록 끝까지, 네 다리 `step_series.npz` `scm_pad_normal_N` ≤ 0인 1 ms 표본이 0개다. 창의 근거는 `soil_guard_stop_rule.py` 조건 3("after the LEVEL start")이고, 부상의 정의는 rev3 Q-14·rev6 R6-B9다(Q-14는 창을 새로 만들지 않는다).
  4. 크롤러 이탈 뒤 최소: t_D(rev6 R6-B4, 100표본 규칙)부터 기록 끝까지 네 다리 1 ms 참 F_cyl 최소가 각각 ≥ F_min이다(비교 허용은 원판 7.6). t_D가 없으면 거짓이다(`soil_guard_stop_rule.py` 427.12.1 기록 문장: 이탈 전 정지는 조건 4 미충족).
  5. 이동 중 압력 ≤ 180 bar, 포화 0: 표본은 rev6 R6-B5·D-32의 10 Hz 제어 주기 행(`record.npz` `u_applied`와 같은 행의 F_cyl, 압력 = F_cyl/A_p, 다리별 헤드 면적)이고 창은 실행 전체다(`soil_guard_stop_rule.py` 조건 5 "over the whole run"). 이동 = |u_applied| > 10⁻⁹ m/s인 행, 포화 = u_applied > 10⁻⁹ m/s(신장)이고 F_cyl/A_p ≥ 210 bar인 행이다. 포화 행은 이동 행이므로 이동 최대가 ≤ 180 bar면 포화는 0이다. 두 값을 따로 적는다.
  - 1 ms 작용 명령 기록이 없으므로 하네스 꼴(1 ms, |valve| > 10⁻⁶ m/s)을 Chrono에 쓰지 않는다(R6-B5). 이 차이는 판정서 한계 절에 적는다.
- **[정의] 결측**: 조건 1~5의 입력(`events`, `s9_rows`, `scm_pad_normal_N`, 1 ms 참 F_cyl, `record.npz` `u_applied`·F_cyl) 가운데 하나라도 없으면 그 행은 `판정 불가`다(원판 9.3).
- **[정의] 묶음에서의 셈**(사용자 결정 65): `allowed_stop`은 묶음 등급에서 통과 쪽으로 센다. 묶음 문구는 `통과 n / 안전 종료 m`으로 따로 적는다(명세 427.9 "안전 종료(목표 미달)로 따로 센다").
  - 근거 1: `d1_selection_rules.md` 11절 173행, S-01·02 행 "P3, READY 120 s, `stroke_limited_stop` 허용".
  - 근거 2: rev6 R6-B8(124행) "`d1_selection_rules.md` 11절은 S-01·02 행을 "P3, READY 120 s, `stroke_limited_stop` 허용"으로 적었다. 그래서 새 판 N-1(427.9 조건 1~5로 `stroke_limited_stop` = `allowed_stop`)을 S-01·02·03·04 네 행에 같이 쓴다(D-26)."
  - 원판 8.1의 등급 순서에는 안전 종료가 없으므로, "허용"을 묶음 등급의 통과 쪽으로 읽는 것은 이 판이 정한 읽기다. 판정서에는 "결과 본 뒤 정한 정의"(사용자 결정 65)로 공개한다.
- 결정 필요: **아니오**(사용자 결정 63의 1, 65).

## R19-2. PS-c 기준 행과 C1-09~12

- **[정의] PS-c 기준 행**(`D1PSC_J1_B_top_Fs4_spFLJ1_base`, `d1_role` = 시각 기준): 기록 행이다. 이 행에는 사건이 없으므로 E-1~E-7을 계산하지 않고, 그 행의 E 항목이 없는 것은 결측이 아니다. 이 행의 P3·D8 값은 기록하고 실패는 보고한다. 근거: `d1_selection_rules.md` 7절(사건 행에 "그 다리의 기준 행(`depends_on`)"을 더함), 11절 D1-PSC 행(426.3 E-1~E-7은 사건 행의 판정), `run_S9.py` `SOIL_EVENT_RULE`(기준 실행은 사건 시각을 주는 같은 argv의 사건 없는 실행), rev4 R4-A2(E 항목 재계산은 사건 행 대상). rev18 R18-2 결측 문장의 "C-2 PS-c 행"은 사건 행으로 읽는다.
- **[정의] C1-09~12**(크롤러 ×3 L1-R V0): 기록 행이다(`d1_selection_rules.md` 11절 "기록(D8·P 계산, 실패는 보고), 8절 규칙"). C-1 묶음 등급에 넣지 않는다. 실패는 보고하고, 보류(D-31)는 `기록 불완전`으로 적는다.
- 결정 필요: **아니오**.

## R19-3. 사건 행 E 항목의 창 (426.3)

- **[정의] 가지 창**: Chrono 사건 행의 E-1~E-7은 원 Chrono 어댑터 `run_S9.judge_chrono_soil_event`(A1, 사용자 결정 2026-10-30)의 창으로 계산한다: 시작 = 사건 − 0.5 s, 끝 = `soil_event_stop_s`(사건 뒤 max(12 s, ramp + 3 s) 이상이고 READY가 3 s 이어진 첫 주기, 최대 60 s, 둘 다 아니면 기록 끝). 끝 뒤의 기록은 E 항목에 쓰지 않고, 그 구간의 다리별 최소 F_cyl·부상 수를 기록으로 적는다. 끝 사유(`ready_held`·`max_after`·`run_end`)를 행마다 적는다.
- **[정의] "실행 끝"의 뜻**: E 항목 원문(426.3)의 "실행 끝"(E-3 느린 사건 "사건 뒤 실행 끝까지" 등)은 이 가지 창의 끝이다. 근거: `run_S9.py` 1194~1195행("the Chrono run keeps its fixed --duration; the judge cuts").
- **[정의] E-4**: 창 안 = 사건 뒤(t ≥ 사건)이고 W 끝 이하(느린 사건은 사건 시작 ~ ramp 끝 + 3 s), F_cyl/A_p ≤ 350 bar. 창 밖 = t ≥ 사건이고 W 끝 뒤 ~ 가지 창 끝. 사건 전(사건 − 0.5 s ~ 사건)은 E-4의 어느 쪽에도 넣지 않는다. 창 밖 이동은 |valve| > 10⁻⁶ m/s인 1 ms 행, 포화는 창 밖의 신장 1 ms 행 중 ≥ 210 bar다. 근거: `s9_soil_event_screen.py` `_pressure_rows`(`after = t >= 0`, `outside = after & (t > w_end_s)`)와 어댑터의 1 ms 사건 기록(`soil_event_series.npz`). 이 E-4와 검증 항목 4의 이동 압력(D-32, 10 Hz 제어 행)은 다른 항목이고, 같은 행에서 따로 적는다.
- **[정의] E-5**: 가지 창 끝의 마지막 `c2_phase`가 `ready`이고, 끝 1 s 평균 자세가 두 축 모두 ≤ 0.2°, 창 안 FAULT 주기 0, 실행 최대 행정 ≤ 684.8 mm다(`r67_g1_screen.judge_event` `end_att`·`fault0`, `s9_soil_event_screen.py` E-5 행). "60 s 안 READY 복귀"는 따로 판정하는 관문이 아니다. 60 s(`max_after`)에서 끝났는데 마지막 주기가 READY가 아니면 E-5는 거짓이다. 끝 사유가 `run_end`면 어댑터대로 그 기록으로 판정하고, 사유를 판정서에 적는다.
- 결정 필요: **아니오**(사용자 결정 63의 1).

## R19-4. 러너 판정 출력의 `passed` None (rev18 R18-2 행 등급의 읽기)

- **[정의] 원칙**: L2b·L1-R 행의 러너 행 등급은 러너 판정기 자신의 셈을 따른다. 근거: `verify_S8C` `meta.failed` = `passed`가 False인 행 수, `meta.hold` = `kind` = `hold`인 행 수(`s8_control.py` 5477~5482행), `judge_summary`의 실패 목록도 `passed` False만이다. CB 집계는 판정 종류의 None을 열린 항목으로 세어 `hold` 행을 낸다(3115~3126행).
- **[정의] 행 등급**(사용자 결정 64): `passed` False인 행이 하나라도 있으면 `미달`, 아니면 `kind` = `hold`인 행이 하나라도 있으면 `판정 불가`, 아니면 `통과`다.
- **[정의] 빈 통과 막기**: 행마다 `passed` True인 판정 종류(`function`·`judged`·`anomaly`·`replay`·`quality`·`kind` 없음) 항목 수를 적는다. 그 수가 0이면 그 행은 `판정 불가`다(원판 E축, 9.3). 이 규칙은 러너 셈(결정 64) 위에 더하는 결측 규칙이고, 러너가 `통과`로 셀 행에만 작동한다. FLAG는 `anomaly` 행의 note `FLAG`와 `flag` 표시 행에서 붙인다(등급 순위는 원판 8.1). 그 위에 R3 재계산 항목(D-26~D-39)과 R19-5의 D-29 재계산을 같은 이름 항목에 덮어쓴다(rev18 R18-2).
- **[정의] 판정 종류(`function`·`judged`·`anomaly`·`replay`·`quality`)의 `passed` None**: 러너가 세지 않으므로 실패도 판정 불가도 아니다. `러너 미판정`으로 행마다 항목 이름과 note를 적는다(예: `2/5b window`의 "run too short", `3 F_min after the re-READY`의 "failed in the re-READY row", `5a rocking amplitude after the re-READY`, `8 level trend time`, `I3 J_C: M4 max <= sensor share`). 실패를 다른 행이 지는 항목(note가 그 행을 가리키는 것)은 그 행의 판정으로 셈이 끝난다. 묶음마다 `러너 미판정` 항목 수와 행을 판정서에 싣는다.
- **[정의] 그 밖의 분기**: 기록 종류(`record`, `report`, `info`, `consistency`, `comparison`, `pair`, `sensitivity`, `superseded`, `leak_compare`)는 기록이다. 목록에 없는 `kind`는 러너도 세지 않으므로 `러너 미판정`으로 적고, 판정서에 따로 표로 싣는다.
- **[정의] 셈 대조**: 도구는 행마다 자신이 센 `passed` False 수·`hold` 수가 러너 `meta.failed`·`meta.hold`(L1-R `verify_S6C`처럼 `hold` 키가 없으면 0)와 같은지 적는다. 다르면 S-11이다.
- 결정 필요: **아니오**(사용자 결정 64: 러너 셈 그대로, 묶음별 러너 미판정 항목 수·이름 공개. 빈 통과 막기는 봉인 전 감사 권고 2).

## R19-5. 러너 t_lift에 기대는 항목

- **[정의] D-29로 다시 계산하는 항목**: rev6 D-29의 "D8 t_lift"는 검증 항목 D8의 이륙 시각이다. 그래서 C-1·C-2·C-5 L2b 행에서 창이 러너 자체 이륙 시각(`verify/s6_control.py` `_times` `liftoff`)에서 시작하는 **D8 항목** 셋을 D-29 t_lift(1 ms `pads.npz` `crawler_normal_N`, 단계 절대 시각)로 다시 계산해 같은 이름 항목에 덮어쓴다.
  1. `C1 D8 min true rod force`(D-39, C-1)
  2. `D8 min true cylinder force >= F_min + 5 kN`
  3. `D8 no pad lift-off`(부상 = `pads.npz` `N` ≤ 0인 1 ms 표본, rev3 Q-14)
  - 창 끝과 문턱은 러너 항목 그대로다. 행마다 러너 값·새 값·두 t_lift를 적는다(rev6 R6-A 끝 문장).
  - D-29 t_lift는 1 ms `crawler_normal_N`이 있는 행은 rev6 D-29로, 없는 V0 L2b 행은 rev15 R15-3의 10 Hz 구간 대체(`t_lift_basis` = `bracket_10Hz`)로 얻는다. 어느 쪽으로도 D-29 t_lift가 없으면(R15-3의 원본 결측 포함) 그 행의 D8 세 항목은 `판정 불가`다(원판 9.3).
- **[정의] 러너 값을 그대로 쓰는 항목**: `3 F_min (1 ms)`, `3 F_min before the event`, `5a rocking amplitude`, `F2 lower-bound soundness`. 이 넷은 D8 항목이 아니고 창을 그 항목 원문(사건 행 항목 3·5a, F2)이 정하므로 D-29 범위 밖이다(rev3 Q-14 "판정 구간은 각 항목 원문이 정한 구간"). 행마다 러너 t_lift와 D-29 t_lift의 차를 적고, 차가 한 제어 주기(0.1 s)를 넘는 행이 있으면 판정서에 적고 그 묶음은 판정 전에 멈추고 묻는다(rev18 R18-4와 같은 꼴).
  - **차의 계산(해상도)**: 러너 t_lift(`_times` `liftoff`)는 10 Hz 표본 시각이다. 그래서 비교는 10 Hz 격자끼리 한다. 1 ms 기준(D-29) t_lift는 그 시각 이상인 첫 10 Hz 제어 주기 표본 시각(같은 행 `record.npz` `t`)으로 올려 맞추고, 10 Hz 구간 대체(R15-3) t_lift는 그 값 그대로 쓴다. 차 = |러너 t_lift − 맞춘 D-29 t_lift|이고, 차 > 0.1 s + 10⁻⁹ s(두 주기 이상 어긋남)이면 멈춘다. 행마다 쓴 기준(`1ms`→10 Hz 올림, `bracket_10Hz`)을 적는다.
  - **차를 계산할 수 없을 때**: 러너 t_lift 또는 D-29 t_lift가 없어 차를 계산할 수 없으면 그 묶음은 판정 전에 멈추고 묻는다.
- **[정의] 구현 위치**: 경로 1은 `chrono_rows_judge_4368.py`·`chrono_bundle_grade_4368.py`(R3b 허용 목록 (나))에서 한다. 러너 판정기·`03_src`는 고치지 않는다(rev18 R18-1 조건).
- 결정 필요: **아니오**(사용자 결정 63의 5, 봉인 전 감사 권고 3).

## R19-6. C-5 VB↔V0 짝

- **[정의]** 짝은 v5 기준 개정 12 2.1의 여섯 쌍이다: `E_G4_Fs4`↔`E_G4_Fs4_V0`, `E_G4_Fs4_ph0.05`↔`E_G4_Fs4_ph0.05_V0`, `G1R_FS24_FL_top_o050_Fs0`↔`G1R_FS24_FL_top_o050_Fs0_V0`, `P3b_J1_B_top_Fs4`↔`P3b_J1_B_top_Fs4_v0v`, `P3b_J2_B_top_Fs4_m1p1_t180`↔`P3b_J2_B_top_Fs4_m1p1_t180_v0v`, `S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0`↔`S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0_v0v`. 도구가 행 이름에서 찾은 짝이 이 여섯과 정확히 같지 않으면 S-15이고 등급을 내지 않는다. VB 실패 ∧ V0 통과는 멈추고 묻는다(개정 12 2.2). 시드 기준 비교 행(P-2·P-3)은 짝이 아니다. 짝의 등급 비교는 기록이다.
- 결정 필요: **아니오**.

## R19-7. E-7 도구의 함수 단위 확인

- **[정의]** E-7을 원 판정 도구로 돌릴 때(rev4 R4-A2 안 c), `r67_g1_screen.py`가 봉인 기준점 `f46b5ab` 뒤에 바뀌었으면 파일 단위가 아니라 함수 단위로 같음을 보여도 된다. 조건: (1) `git diff f46b5ab <쓴 커밋> -- 04_scripts/03_control/s8/r67_g1_screen.py`의 바뀐 줄(+/−)이 모두 기록 전용 함수(`v5_job_record`, `v5_branch_record`, `v5_setting_record`, 새 함수 `resume_k1_block`) 안에 있다(rev13 R13-2 #10: 기록 키만 바꿈). (2) E-7이 지나는 함수(`judge_event`, `twist_work`, `_intervals`와 그 함수들이 부르는 이 파일의 함수)의 본문 바이트가 같다. 덩어리 표(덩어리 머리, 감싸는 함수)를 판정서에 싣는다. 하나라도 어기면 S-11이다.
- 결정 필요: **아니오**(사용자 결정 63의 6).

## R19-8. R3b 순서와 허용 목록의 rev19 반영 (rev18 R18-1의 고쳐 씀)

- **[정의] 순서**
  1. 이 판을 봉인한다. 봉인 파일 커밋 S7을 S6 `59c933b` 위에 만든다(부모 = S6 = 봉인 기준 커밋 SEAL_COMMIT = `59c933b50d6a32db999c42951d3c168cd552640d`, 브랜치 `z4373-s4`). S7이 바꾸는 것은 이 판의 세 파일과 `.gitattributes`의 `-text` 3줄뿐이다.
  2. 두 도구 브랜치 `z4374-p1chrono`·`z4374-p2chrono`가 각각 S7을 병합한 뒤 R19-1~R19-7을 구현한다. Chrono 판정 도구의 봉인 목록에는 rev16~rev19를 넣는다(두 경로 같게). `resume4368_judge.py`의 봉인 목록은 R3b에서 고치지 않는다(rev18 R18-1 2 그대로). 하네스 도구(R4)의 봉인 목록은 rev13~rev19다.
  3. 메인 세션이 S7에서 `z4373-r3b`를 만들고 `z4374-p1chrono` → `z4374-p2chrono`를 `--no-ff`로 병합한다. 마지막 병합 커밋이 R3b다.
  4. 메인 checkout을 `git merge --ff-only z4373-r3b`로 R3에서 R3b로 맞춘다. R3..R3b에는 S4~S7과 두 도구 브랜치의 커밋만 있다.
  - rev18 R18-1 순서 1~3의 S6은 S7로 읽는다. R3b 조건의 나머지(`03_src`·`02_params` diff 0, `04_scripts` 세 파일, 러너·manifest diff 0, `resume4368_judge.py` 함수 단위 조건, R3b blob 표)는 그대로다.
- **[정의] 허용 목록 (가)**: rev16~rev19의 규칙 파일 각 세 개와 그 `.gitattributes` `-text` 줄(지운 줄 0). rev19 몫은 `v5_resume_4368_rules_rev19.md`, `v5_resume_4368_rules_rev19.sha256`, `v5_resume_4368_rules_rev19_seal_candidate_draft.md`와 그 `-text` 3줄이다.
- **[사실]** 경로 2 하네스 도구 `path2_v5c`의 `P2_CORE_SHA`는 R4에서 맞춘다(사용자 결정 63). R3b는 하네스 판정을 하지 않으므로 이 판정에 영향이 없다.
- 결정 필요: **아니오**(사용자 결정 63의 8).

## R19-9. 두 경로에 넘기는 문장

- **[정의]** 두 경로 작성자(경로 1 python-expert, 경로 2 원 작성자)에게 **같은 문장**을 넘긴다: 이 판 R19-1~R19-8의 [정의] 글머리, 그리고 거기서 인용한 원 규칙 절(명세 426.3·427.9 "판정 분류" 문단, `d1_selection_rules.md` 7·11절, rev3 Q-13·Q-14, rev6 D-26~D-39·R6-B4·R6-B5·R6-B8·R6-B9, rev4 R4-A2, v5 기준 개정 12 2.1·2.2, rev13 R13-2 #10). 다른 경로의 코드·출력·결함 문장과 이 판의 R19-0·R19-10은 넘기지 않는다. 지시문에 "이 판의 다른 절은 열지 않는다"를 넣고, 두 경로 판정서의 읽은 것 목록으로 확인한다.
- 결정 필요: **아니오**(사용자 결정 63의 7).

## R19-10. 9.2 예외와 바꾸지 않는 것의 공개

- **[사실]** 원판 9.2는 "상대 출력을 본 뒤에는 어느 경로도 고치지 않는다"이다. 이 판의 정의는 두 경로의 R3b 구현 질문·해석(R19-0)을 본 뒤 정했다. 판정서 한계 절에 그대로 적는다: "rev19 정의는 메인 세션과 도메인 검토가 R3b 두 경로의 구현 질문과 해석을 본 뒤 원 규칙 문장과 원 판정 도구에서 정했다. 두 경로는 같은 정의 문장만 받았고, 구현과 값은 경로마다 따로 만들었다. 정의할 곳의 선택은 두 경로에서 독립이 아니다."
- **[사실]** 숫자 문턱, 등급과 우선순위, 멈춤 조건의 뜻은 바뀌지 않는다. R19-5의 "멈추고 묻는다"는 rev18 R18-4와 같은 꼴의 판정 전 멈춤이고 원판 8.2의 새 멈춤 조건이 아니다.

### 결정 표

| 항목 | 정의 | 결정 필요 |
|---|---|---|
| R19-1 안전 종료 | 427.9 조건 1~5만, P3·G6 기록 목록, 조건 3 창 LEVEL 시작~끝(Q-14), 조건 4 t_D~끝, 조건 5 D-32 10 Hz 실행 전체(포화 = 신장 ≥ 210 bar), 결측 판정 불가, `allowed_stop`은 통과 쪽·문구는 `통과 n / 안전 종료 m`(d1 11절 173행, R6-B8, 결과 본 뒤 정한 정의) | 결정됨: 사용자 결정 63의 1, 65 |
| R19-2 PS-c 기준·C1-09~12 | 기록 행, E 항목 없음은 결측 아님, 실패 보고·보류는 기록 불완전 | 결정됨: 사용자 결정 63의 2 |
| R19-3 E 창 | 어댑터 가지 창(−0.5 s ~ `soil_event_stop_s`), "실행 끝" = 가지 끝, E-4 창 밖 = 사건 뒤·W 뒤~가지 끝, E-5 = 가지 끝 READY·자세·FAULT 0·행정 | 결정됨: 사용자 결정 63의 3·4 |
| R19-4 passed None | 러너 셈 그대로(False = 미달, hold = 판정 불가), 판정 종류 None = 러너 미판정 기록, 셈 대조 S-11, 판정 종류 True 0개 행 = 판정 불가 | 결정됨: 사용자 결정 64 |
| R19-5 t_lift | D8 세 항목만 D-29 재계산, 나머지 넷은 러너 값 + t_lift 차 > 0.1 s(10 Hz 격자끼리)면 멈추고 묻기, D-29 t_lift 없음 = D8 세 항목 판정 불가, 차 계산 불가 = 멈추고 묻기 | 결정됨: 사용자 결정 63의 5 |
| R19-6 VB↔V0 | 여섯 쌍 정확히, 다르면 S-15 | 아니오 |
| R19-7 E-7 함수 단위 | 기록 전용 함수 안 덩어리만 + E-7 경로 함수 바이트 같음, 아니면 S-11 | 결정됨: 사용자 결정 63의 6 |
| R19-8 순서·허용 목록 | S7(부모 S6) → 두 도구 브랜치가 S7 병합 뒤 구현 → `z4373-r3b`(S7에서, `--no-ff`) → 메인 ff-only, 허용 (가) rev16~rev19, 봉인 목록 Chrono rev16~19·하네스 rev13~19 | 결정됨: 사용자 결정 63의 8 |
| R19-9 넘길 문장 | 두 경로 같은 문장, "다른 절은 열지 않는다" | 결정됨: 사용자 결정 63의 7 |

### 결과 본 뒤 사용자 결정 기록

| 날짜 | # | 결정 | 반영 |
|---|---|---|---|
| 2026-11-15 | 65 | 사용자 결정 65(2026-11-15, rev19 봉인 전 감사 권고 4): S-01~04의 `allowed_stop`은 묶음 등급에서 통과 쪽으로 세고, 묶음 문구는 `통과 n / 안전 종료 m`으로 따로 적는다. 판정서에는 결과 본 뒤 정한 정의로 공개한다 | R19-1 |
| 2026-11-15 | 64 | 사용자 결정 64(2026-11-15, rev19 봉인 전 감사 권고 1): 러너 행 등급은 러너 판정기 자신의 셈을 따르고(판정 종류 `passed` None = 러너 미판정 기록), 묶음별 러너 미판정 항목 수와 이름을 판정서에 공개한다 | R19-4 |
| 2026-11-15 | 63 | 사용자 결정 63(2026-11-15): R3b 두 도구 브랜치의 구현 질문을 원 규칙으로 정의하는 rev19를 쓰고 봉인한 뒤(S7, S6 위) 두 도구 브랜치가 S7을 병합해 정의를 맞춘다. 경로 2 하네스 도구의 `P2_CORE_SHA`는 R4에서 맞춘다 | R19-1~R19-10 |

## 봉인 때 바꿀 머리 줄 (메인 세션)

1. 봉인 전 확인 필요는 없다(S6 해시·rev18 봉인 sha는 4행과 R19-8에 적었다).
2. 파일 이름: `v5_resume_4368_rules_rev19_seal_candidate_draft.md`를 같은 폴더에 `v5_resume_4368_rules_rev19.md`로 복사한다. 초안 파일은 지우지 않는다.
3. 1행을 다음으로 바꾼다:
   `# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev19 (R3b 도구 구현 질문 뒤: 427.9 안전 종료 등급, PS-c 기준 행·C1 기록 행, 사건 E 항목 창, 러너 passed None, 러너 t_lift 항목, VB↔V0 짝, E-7 도구 확인, 결과 본 뒤 개정, 봉인)`
4. 3행(첫 글머리 "상태")을 다음으로 바꾼다:
   `- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev19.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev19_seal_candidate_draft.md`와 1·3·5·9행만 다르다.`
5. 5행("시점")에서 `SEAL_TIME`과 `SEAL_COMMIT`(S6 `59c933b`)을 값으로 바꾼다. 이 두 이름 말고는 5행을 바꾸지 않는다.
6. 9행("봉인 준비판이다")을 다음으로 바꾼다:
   `- **봉인본이다.** 봉인 전 확인 필요는 없었고(S6 해시·rev18 봉인 sha는 4행), 사용자 결정 63·64·65(2026-11-15)와 봉인 전 감사(대상 초안 `20c68016`)의 권고는 R19-1~R19-10에 반영했다(결정 64 = R19-4 러너 셈 그대로·묶음별 러너 미판정 항목 수·이름 공개, 결정 65 = R19-1 `allowed_stop` 셈).`
7. 바꾼 뒤 sha256을 계산해 `v5_resume_4368_rules_rev19.sha256`에 `<sha256>  v5_resume_4368_rules_rev19.md  sealed <SEAL_TIME 값> (436.8 rev19: after the R3b tool-branch questions on top of rev18; thresholds, grades and stop meanings unchanged, seen-data list disclosed; seal commit S7 on S6 59c933b; S-01..04 427.9 safe stop graded by conditions 1-5 only (P3-1..P3-9, FAULT0, READY 120 s, G6-1..G6-7 recorded), condition 3 window LEVEL start to the record end by Q-14, condition 4 from t_D, condition 5 on the D-32 10 Hz control rows over the whole run with saturation = extending row at >= 210 bar, missing inputs = not judgeable, allowed_stop on the pass side of the bundle grade, bundle phrase pass n / safe stop m (d1_selection_rules 11 line 173, rev6 R6-B8, user decision 65, defined after results); PS-c base row and C1-09..12 are record rows; E-1..E-7 in the run_S9 adapter branch window (event - 0.5 s to soil_event_stop_s), run end = branch end, E-4 outside = after the event and after W to the branch end, E-5 = READY at the branch end; runner rows by the runner's own count (passed False = fail, kind hold = not judgeable, judged-kind None = runner-unjudged record with per-bundle counts and names disclosed (user decision 64), a row with no passed-True judged item = not judgeable, count check S-11); D-29 t_lift recomputes the three D8 items only, the four other t_lift items keep runner values and stop-and-ask past 0.1 s compared on the 10 Hz grid (1 ms D-29 t_lift rounded up to the next control period, R15-3 bracket as is), no D-29 t_lift = the D8 items not judgeable, difference not computable = stop and ask; C-5 VB / V0 six pairs or S-15; r67_g1_screen.py E-7 identity by function (record-only hunks, E-7 path bytes equal) or S-11; tool branches merge S7 then align, z4373-r3b from S7, allow list (a) rev16..rev19, seal lists Chrono rev16..19 / harness rev13..19; same definition sentences to both paths; path2_v5c P2_CORE_SHA aligned at R4 (user decision 63); 9.2 exception disclosed)` 한 줄로 쓴다.
8. `.gitattributes`에 다음 3줄을 더한다(**`git add`보다 먼저**, 지우는 줄 없음):
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev19.md -text`
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev19.sha256 -text`
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev19_seal_candidate_draft.md -text`
9. 확인: `tools/verif/seal_check.py`와 `tools/verif/placeholder_scan.py`를 돌리고, 봉인본 5행에 `SEAL_TIME`·`SEAL_COMMIT`이 남지 않았는지 Grep으로 따로 본다.
10. `git add`(세 파일과 `.gitattributes`)와 봉인 파일 커밋 S7을 S6 위에 만든다(브랜치 `z4373-s4`). 메인 checkout의 HEAD는 바꾸지 않는다(R3 그대로, R19-8 순서 4에서 R3b로 맞춘다). 봉인 뒤 이 문서를 고치지 않는다.
