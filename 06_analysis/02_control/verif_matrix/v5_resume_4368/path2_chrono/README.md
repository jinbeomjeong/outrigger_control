# 436.8 경로 2 — Chrono C-1~C-8 (C-1~C-5 판정 블록 재계산·재집계, C-6·C-7·C-8 값)

- 작성: control-expert(새 인스턴스, 2026-11-13). 이 작성자는 경로 1 도구를 만들거나 고친 적이 없다(아래 "독립성 공개").
- 규칙: 원판 `v5_resume_4368_rules.md`(9019b405), rev1(d9094fda), rev2(497e4614), rev3(dad8dfa6) ~ rev12(78f1f99b), rev15(0162561c), rev16(b3899194), rev17(9400660e), rev18(3693a69c), rev19(7f87b8bb), rev20(615a8fbd), rev21(ecd70949), rev22(a48a81f9, 우선; rev13·rev14는 도구 목록 밖, R13-7·R14-7·R15-7).
- **rev22 R3d(2026-11-15, 같은 새 작성자, 브랜치 `z4376-p2chrono` = R3c `f9bc3c7` + S10 `570a9c1` 병합 `c6b257f`)**: 읽은 정의는 메인 세션이 옮긴 rev22 R22-2(순서 3, 봉인 목록, 변경 범위, R3d 조건 (다))·R22-3(K-10에서 빼는 것, 경로 2 재사용과 재판정) 줄뿐이다(인계 파일 sha `89669b1e…`). 봉인본 본문은 열지 않고 sha만 계산했다. 바꾼 것은 봉인 목록 변경의 범위뿐이다: `p2_rules.SEALED`에 rev22(`a48a81f9…`)를 더하고 우선 표기("wins")를 rev22로 옮겼고, `RAW_ONLY`에 rev22를 넣었고, `seal_check` 설명 문자열의 범위 표기(rev15..rev22)와 판별 설명(rev22 R22-2)을 고쳤다. 시험 기대값(`test_p2_synthetic.py` `t_seal`의 기대 sha 표와 "only rev22 wins")을 고쳤다. 판정 동작은 바뀌지 않았다. `path2/p2_4368.py`는 R22-2 (다)의 범위 밖이라 이번에 고치지 않았다(그 `chrono` 봉인 목록은 rev16~rev21 그대로).
- **rev21 R3c 보완(2026-11-15, 같은 새 작성자, 새 브랜치 `z4375-p2chrono`, R3b `062e051`에서 갈라 S9 `da12622` 병합 `b06fd0a` 위)**: 읽은 정의는 메인 세션이 옮긴 rev21 R21-1~R21-4 [정의] 글머리 파일(sha `e9744fac…`, 결과 문장 1개 생략본)과 정의가 인용하는 v5 기준 rev6 5절 t_lift,sus 표 줄뿐이다. 바꾼 것: (1) 봉인 목록 rev16~rev21(rev21 `ecd70949…`, 우선), `path2/p2_4368.py` `CHRONO_SEALS`도(출력 키 `seals.chrono_rev16_21`). (2) R21-1: L2b 행 D8 항목(`D8_F_after_liftoff`, C-1 D8·P와 C-2 L2b D8·P 행; 경로 2의 D8 항목은 이것 하나이고 D-39 C1 행 재계산도 이 항목)이 쓰는 t_lift를 `p2_core.t_lift_sus_d29`로 바꿨다: 1 ms `crawler_normal_N` ≤ 0.01 W(W = 376.7 kN, `R.W_TLIFT_SUS_N`, 7.6 허용)가 기록 끝까지 이어지기 시작한 표본부터 단계가 idle·check·touch가 아닌 첫 표본(단계 = `phases` + `settings.start_t_s`), `t_lift_basis` = `1ms_sus`. 앞 판의 첫 ≤ 0 표본(rev6 5 t_lift)은 `t_lift_first_le0_record_s`로 기록. t_lift,sus가 없으면 그 항목 판정 불가 + 멈춤("R21-1 … stop the bundle and ask", 묶음 판정 불가). V0 L2b 행(10 Hz 구간 대체)은 R15-3 t_b 그대로이고, 같은 10 Hz 계열에서 같은 규칙으로 구한 대응값을 `t_lift_sus_10Hz_record_s`(없으면 "기록 결측")와 t_b와 다른지(`t_lift_sus_10Hz_differs_from_t_b`)로 기록한다. SCM·L1-R 행의 D8 t_lift와 C-5 H-9의 t_lift(rev6 5)는 R21-1 범위 밖이라 그대로다. (3) R21-2: 경로 2에는 러너 t_lift(`liftoff_s`)와 비교하는 항목이 없다(러너 판정 출력을 읽지 않음). 올림 규칙만 기록값으로 낸다: `t_lift_sus_up_10Hz_record_s` = 같은 행 `record.npz` `t`에서 t ≥ t_lift,sus − 10⁻⁹ s인 첫 표본(`p2_core.up_to_control_instant`, 배열에서 고름, ceil 안 씀). 시각은 모두 엔진 절대 시각(`pads.npz`·`record.npz` `t`, 단계 + `start_t_s`). (4) 공통 파일(`p2_core.py`·`p2_rules.py`)이 바뀌었으므로 R21-4대로 C-1~C-8 전부를 R3c 도구로 다시 판정하고 D-29 밖 항목을 R3b 출력과 K-10으로 대조한다.
- **rev20 정렬(2026-11-15, 같은 새 작성자, S8 `4d8a95d` 병합 `e620fea` 위)**: 읽은 정의는 메인 세션이 옮긴 rev20 R20-1·R20-2·R20-4 [정의] 글머리 파일(sha `49b469f4…`)뿐이다. 바꾼 것: (1) 봉인 목록 rev16~rev20(rev20 `615a8fbd…`, 우선), `path2/p2_4368.py` `CHRONO_SEALS`도(출력 키 `seals.chrono_rev16_20`). (2) R20-1: `p2_e7.r19_7_function_check`의 조건 (1)을 (1a) 기록 전용 함수 안 / (1b) 함수 밖 모듈 수준 이름(대입과 그 바로 아래 docstring)의 정의이고 그 이름을 읽는 이 파일의 모든 함수(모듈 수준 문장이 읽으면 `<module>`)가 기록 전용 함수이며 다른 파일이 `r67_g1_screen`의 그 이름을 읽지 않음으로 바꿨다. 다른 파일 확인은 `git grep -n -E "import +r67_g1_screen|from +r67_g1_screen +import" <ref> -- *.py`로 import하는 파일을 찾고, 그 파일들의 import 문을 파싱해 `from r67_g1_screen import <이름>`과 `<별칭>.<이름>`만 읽기로 센다(다른 모듈의 같은 이름은 세지 않음). 이름마다 `git grep -n -w <이름> <ref> -- *.py`도 돌려 명령과 결과 줄을 `tool_gate.r19_7.names_1b_cross_file_check.greps`에 싣는다. 덩어리 표(`hunks[].lines`)는 바뀐 줄마다 `rule`(1a/1b)·감싸는 함수 또는 그 줄·정의하는 이름·읽는 함수·판정을 적는다. 빈 줄은 어느 문장에도 속하지 않아 수만 센다(앞 판과 같음). **결과**: b9f5707·현재 HEAD 모두 관문 통과(`RESUME_K1_KEY` 두 줄 = (1b), 읽는 함수 `v5_job_record`·`v5_branch_record`, 다른 파일의 `r67_g1_screen.RESUME_K1_KEY` 읽기 0; 조건 (2) 네 함수 같음). (3) R20-2: 안전 종료 행의 판정 키에 `identity`(4.2·6)·`K1_class`(7.2)가 남는 것은 rev19 정렬판 그대로이고, 6절 커밋·태그 항목(`R11-4_commit`·`R9-1_expect_controller`)도 `augment_items`가 행 뒤에 더한다(확인만, 동작 변경 없음).
- **rev19 정렬(2026-11-15, 같은 새 작성자, S7 `38897f0` 병합 `493f140` 위)**: 읽은 정의는 메인 세션이 옮긴 rev19 R19-1~R19-8 [정의] 글머리 파일(sha `ff5e61b8…`)뿐이고 봉인본의 다른 절은 열지 않았다. rev19가 앞 판(rev18 보완)의 읽기와 다르면 rev19가 맞다. 바꾼 것:
  1. 봉인 목록에 rev19(`7f87b8bb…`)를 넣고 우선 표기를 rev19로 옮겼다(R19-8 순서 2: rev16~rev19). `path2/p2_4368.py`의 `chrono` 봉인 목록(`CHRONO_SEALS`)에도 넣었다.
  2. R19-1(S-01~04 안전 종료): 분기는 행에 `FAULT_LIFT_STROKE_LIMIT` 사건이 있을 때 연다. 등급은 427.9 조건 1~5만으로 정한다(`safe_stop_427_9`). 조건 1 = `events`의 **첫 `FAULT*` 사건**이 `FAULT_LIFT_STROKE_LIMIT:soil:`로 시작, 3 = **첫 LEVEL 시작**(`s9_rows` `c2_phase` = level 첫 행)부터 끝까지 `scm_pad_normal_N` ≤ 0 표본 0, 4 = t_D부터 끝까지 다리마다 최소 ≥ F_min, **t_D 없음 = 거짓**, 5 = `record.npz` 10 Hz 행 전체에서 이동(\|u_applied\| > 10⁻⁹) ≤ 180 bar, 포화(u_applied > 10⁻⁹ ∧ ≥ 210 bar) 0(두 값 따로). 입력(`events`·`s9_rows`·`scm_pad_normal_N`·1 ms F_cyl·`record.npz`) 하나라도 없으면 판정 불가(`missing_inputs`). 그 행의 P3-1~P3-9·FAULT0·P3-6·G6-6은 기록(`record_only`, `recorded_items`)이고 판정 키에는 `identity`·`K1_class`(4.2·6 기록 대조와 7.2 분류, P3 등급 항목 아님)와 `safe_stop_427_9`만 남는다. `allowed_stop`은 통과 쪽으로 세고, 묶음 출력 `safe_stop_427_9.phrase` = `통과 n / 안전 종료 m`과 공개 문장(사용자 결정 65)을 낸다.
  3. R19-2: PS-c 기준 행(argv에 `--soil-event`가 없는 D1PSC 행, kind `PSC_base`)은 기록 행이다. E 항목을 만들지 않고(결측 아님), P3·D8 값을 기록한다. C1-09~12는 앞 판부터 기록 행이다(`D8P_record`, C-1 등급 밖). 기록 행의 실패 항목은 `rows[].failures_reported`에 적는다. C1-09~12는 L1-R이라 R40-2 보류가 생기지 않는다(`hold` 계산 안 함; 생기면 `기록 불완전`).
  4. R19-3: 가지 창 = 원 어댑터 `run_S9.judge_chrono_soil_event`·`soil_event_stop_s` 그대로(`s9_rows` `c2_phase` 10 Hz 행, 사건 기준 t > 0에서 "ready" 포함이면 `ready_since` 유지·시작, 아니면 지움, t ≥ 60 s 첫 행 = `max_after`, t ≥ max(12 s, 램프 + 3 s) ∧ READY 3 s = `ready_held`, 둘 다 없으면 기록 끝 `run_end`). 끝 뒤 행은 E 항목에 쓰지 않고 다리별 최소 F_cyl·부상 수를 `after_branch_end_record`에 적는다. E-4 창 밖 = 사건 뒤·W 끝 뒤 ~ 가지 끝(사건 전 0.5 s는 어느 쪽도 아님), 1 ms \|valve\| > 10⁻⁶. E-5 = 가지 끝 마지막 `c2_phase` = ready ∧ 끝 1 s 평균 자세 ≤ 0.2° ∧ **가지 안 FAULT 주기(`c2_phase` fault) 0** ∧ 최대 행정 ≤ 684.8 mm, `run_end`도 그 기록으로 판정(사유 기록). E-6 끝 틈 = 가지 끝까지 마지막 `s9_rows.crawler_gap_min_m`(어댑터와 같은 필드; 앞 판은 `rut_clearance_m`). `p2_e7.py`가 도구에 넘기는 가지 행·단계도 같은 창이다.
  5. R19-6: C-5 묶음에서 VB↔V0 짝(`<이름>`과 `<이름>_V0`/`_v0v`)을 C-5 배치 행 이름과 manifest C-5 행 이름을 합쳐 찾고, 개정 12 2.1의 여섯 쌍과 정확히 같지 않으면 S-15·판정 불가(`bundle_result.rev19_R19_6_pairs`). VB 미달 ∧ V0 통과는 멈춤(개정 12 2.2), 짝 등급 비교는 기록. 저장 manifest `V5-RESUME-K1-C5`에서 찾은 짝은 정확히 여섯이다(확인).
  6. R19-7: `p2_e7.tool_gate.r19_7` = `git diff -U0 f46b5ab <git_at_start> -- r67_g1_screen.py`의 덩어리마다 머리·감싸는 함수·함수 밖 줄(그 줄이 정의하는 이름과 그 이름을 읽는 함수)의 표, (1) 바뀐 줄이 모두 `v5_job_record`·`v5_branch_record`·`v5_setting_record`·`resume_k1_block` 안인지(빈 줄은 함수에 귀속하지 않고 수만 적음), (2) `judge_event`·`twist_work`·`_intervals`와 이 파일에서 그들이 부르는 함수(`is_fast`)의 본문이 f46b5ab·git_at_start·실행 파일에서 같은지. 어기면 E-7 관문 실패 = S-11. **결과(b9f5707·현재 HEAD)**: (2)는 네 함수 모두 같다. (1)은 첫 덩어리(`@@ -615 +615,19 @@`)에 모듈 수준 줄 `RESUME_K1_KEY = "resume_k1"`과 그 docstring이 있어 함수 밖이다(이 이름을 읽는 함수는 `v5_job_record`·`v5_branch_record`뿐). 문장 그대로 읽어 관문 실패(S-11)로 두었다 — 아래 6절 T-8.
  7. R19-4(러너 `passed` None)·R19-5(러너 t_lift 항목): 경로 2는 러너 판정 출력(`verify_S8C`·`verify_S6C`의 행·`meta`)을 읽지 않고 D8·P를 1 ms 시계열에서 다시 계산한다(9.1 경로 2 = 재계산). 그래서 러너 셈·`러너 미판정`·셈 대조는 쓰는 곳이 없다. D8 항목은 앞 판부터 D-29 t_lift(1 ms, V0 L2b는 R15-3 10 Hz 대체, 없으면 판정 불가)로 계산한다. 러너 이름 항목(`D8 min true cylinder force >= F_min + 5 kN`, `D8 no pad lift-off`, `C1 D8 min true rod force`)과 러너 값 네 항목의 t_lift 차는 경로 2에 해당 항목이 없어 만들지 않았다(R19-5 [정의] 구현 위치 = 경로 1).
- **rev18 R3b 보완(2026-11-15, worktree `z4374-p2chrono`, 부모 S6 `59c933b`, R18-1 (다)·R18-3, 사용자 결정 60의 2·61·62)**: 작성자 공개 — 원 경로 2 작성자를 다시 부를 수 없어 **새 작성자**(control-expert와 다른 새 에이전트 실행, 이 프로젝트 경로 1 코드·출력을 열지 않음)가 고쳤다(사용자 결정 62, 판정서 공개). 9.2 예외 공개: R18-3 [사실] 문장("R3b 두 경로 보완 항목은 메인 세션과 도메인 검토가 R3 두 경로 출력을 본 뒤 정했다. 보완의 구현과 재판정 값은 경로마다 따로 만들었다. 보완 항목의 선택은 두 경로 출력에서 독립이 아니다.")을 판정서 한계 절에 그대로 적는다. 바꾼 것:
  1. 봉인 목록 `SEALED`·`RAW_ONLY`에 rev16·rev17·rev18(`.sha256` 첫 토막)을 넣었다. raw sha = 코드 봉인 sha = `.sha256` 첫 토막, 다르거나 없으면 S-1. 우선 표기("wins")는 rev18로 옮겼다(D-29 판별 `d29_l2b_bracket_enabled`는 rev15 파일이 목록에 있는지만 보므로 그대로 켜져 있다).
  2. **S-01~04 427.9 안전 종료 분기**(R18-2, rev6 R6-B8·D-26, 명세 17690~17692행): `p2_core.safe_stop_427_9`. 실행 기록의 정지 사건은 `FAULT_LIFT_STROKE_LIMIT:<사유>:<다리>`(실제 C-2 행 `…:soil:RL`)이고, 앞 판의 `stop_classification`은 `endswith(":soil")`로 찾아 이 이름을 놓쳤다(R18-3 [사실]의 "S-01·02 안전 종료 분기 누락"). 조건 1~5를 따로 계산해 행마다 `conditions`·`values`에 남긴다: 1 정지 사유 토막 = `soil`, 2 `FAULT_STROKE_END` 사건 0, 3 t_D 뒤 패드 법선 ≤ 0인 1 ms 표본 0(R6-B9, rev3 Q-14, SCM `scm_pad_normal_N`), 4 t_D ~ 실행 끝 네 다리 1 ms 실제 F_cyl 최소 ≥ F_min, 5 `record/record.npz` 10 Hz 제어 행에서 작용 명령 ≠ 0 표본의 헤드 등가 압력 ≤ 180 bar(rev6 R6-B5)이고 포화 0(포화 = 신장 명령 > 0 ∧ F_cyl/A_p ≥ 210 bar, `s9_soil_event_screen` 문서의 하네스판·CLAUDE.md 릴리프 210 bar). 모두 참 → `allowed_stop`, 하나라도 거짓 → `fail`, 거짓 없이 계산 불가가 있으면 `indeterminate`(판정 불가). `allowed_stop`이면 P3-5·P3-6·FAULT0을 판정 키에서 빼고(`superseded_by`) 나머지 P3 항목은 그대로 판정한다(R18-2 문장 그대로). 묶음 출력 `bundle_result.safe_stop_427_9`에 행별 분류·조건·부상 표본·이동 최대 압력(R18-4 "두 값")과 분류별 개수(427.9 "따로 센다")를 낸다. C-3(S-03·04)에도 같은 분기를 쓰고 G6-6은 그대로 판정한다. C-4(`allow_stop` 거짓)는 앞 판 경로를 바꾸지 않았다.
  3. **PS-c E-1~E-7**(R18-3 1, rev4 R4-A2): 새 파일 `p2_psc.py`(E-1~E-6 재계산, 안 b)와 `p2_e7.py`(E-7 도구 실행, 안 c). `judge --bundle C-2 --aux e7=<e7_path2.json>`. 아래 2절 표.
  4. `p2_chrono.INPUT_FILES`에 `soil_event_series.npz`를 더했고(rev3 R3-G2 입력 sha), 공통 파일(`COMMON_FILES`)에 `p2_psc.py`·`p2_e7.py`를 더했다. 공통 파일이 바뀌었으므로 R18-4대로 C-1·C-3~C-8도 R3b 도구로 다시 돌려 R3 출력과 대조한다. 9.1 표 C-1~C-5 행의 경로 2 = "`series.npz`·`r8_series` 재계산". 입력 파일은 rev3 R3-G2(SCM `step_series.npz`·`r8_series.npz`, L2b `pads.npz`, L1-R `record/record.npz` + `pads.npz`). 담당 범위는 rev2 R2-0 + rev3 R3-G11(C-6·C-7·C-8 추가).
- **rev15(0162561c, 우선, 2026-11-15 반영, 봉인 커밋 S3 `cc0d9b8`, 봉인 2026-11-15 00:08:30 +09:00)**: R15-7대로 봉인 목록 `SEALED`·`RAW_ONLY`에 rev15를 넣었다(경로 1 `RULES_SEALS`와 대칭; rev13·rev14는 넣지 않음 — `tools/verif/seal_check.py`가 본다). raw sha = 코드 봉인 sha = `.sha256` 첫 토막이어야 하고 다르거나 없으면 S-1이다. 목록에 들어갔으므로 R15-3 D-29 읽기(V0 L2b 10 Hz 대체, `d29_l2b_bracket_enabled` 참)가 켜진다. 이 브랜치(R2 기준) checkout에는 rev15 파일이 없어 `seal`이 S-1(종료 2)이고, R3 병합 뒤에 통과한다. 자체 시험은 봉인 파일이 없는 checkout에서 `--rules-repo <봉인 worktree>`(예: `C:\workspace\z4372-seal`)를 주면 없는 파일을 그곳에서 복사해 봉인 시험을 하고 CLI 시험에 `--repo`로 넘긴다. 주지 않으면 봉인·CLI 시험을 건너뛴다(SKIP 줄).
- **도구 결함 수정(2026-11-14, 사용자 결정 19, worktree `z4372-p2t45`, 기준 R2 `b9f5707`)**: (1) `p2_t45.py` 회귀 행을 저장 3단계 18행의 정확한 폴더 이름(stamp 포함, `REG_ROWS`)으로 고정했다. 출처는 rev7 4(95행 "3단계 저장 기록 18행")·5("18행(VB 12 + LS 6)")·v5 rev6 3절 1~18행이고, 이름은 저장 3단계 배치 `07_results/S9/batch_V5-STAGE3_20261107_184341`의 행 로그 `->` 줄에서 옮겼다(`REG_BATCH`). 436.8 C-5 L2b 행이 같은 태그 접두어로 새 폴더를 만들어 접두어 glob이 2개씩 잡혔던 결함이다. 이름마다 폴더가 정확히 하나가 아니면 회귀 실패 = T4-0·T4·T5 S-11이다. (2) 재생 결과를 `--only` 폴더 이름 대신 행 폴더 경로(`p2_t45.row_key`, 해석한 경로의 소문자)로 키 잡는다. VB·LS1·LS4와 V0 짝이 같은 이름을 써서 24행이 15키로 겹쳤던 결함이다. 도구는 입력 순서대로 행을 내고 `case`에 폴더 이름만 적으므로 위치로 맞추고, 행 수·이름이 어긋나거나 같은 폴더가 두 번 오면 매핑을 비우고(`mapping_problems`) `t45_items`가 S-11로 둔다. 예전 이름 키 문서(`row_key` 없음)도 S-11이다. (3) D-29: L2b 행에 1 ms `crawler_normal_N`이 없으면(V0 행) t_lift를 R6-B1 10 Hz 구간 대체로 계산하는 읽기(사용자 결정 2026-11-14)는 rev15에 들어간다. 이 도구는 rev15 파일이 봉인 목록 `SEALED`에 들어가야만(`p2_rules.d29_l2b_bracket_enabled`, `D29_RULE_FILE`) 그 대체를 쓰고, 그 전에는 L2b t_lift를 계산하지 않는다(`cr_basis` = `bracket_10Hz_d29_pending_rev15`, rev6 D-29는 1 ms 기록). L1-R은 앞 판대로 R6-B1이다. 엔진은 `batch.json` argv(`engine_of`)로 판별한다. C-5에서 t_lift는 기록 항목이고 V0 행은 H-9 해당 없음이라 등급은 바뀌지 않는다. (4) R15-3(봉인 전, 메인 세션 전달 2026-11-15): 10 Hz 구간 대체의 원본을 R6-B1과 같게 맞췄다(`p2_core.bracket_crawler_normal`). 크롤러 힘 `record/record.npz` `F_crawler`([N, 3], N, 세계)를 `result.json` `floor_plane.normal_world`(단위 벡터로 정규화)에 사영하고, 시간축은 `record.npz` `t`(0.1 s), 단계는 `phases` + `settings.start_t_s`다. 앞 커밋 `e0238de`는 `F_crawler`의 세계 z 성분을 썼다(평지에서만 같음). 원본이 없거나 꼴이 틀리면(`F_crawler` 없음·[N, 3] 아님·`t`와 길이 다름, `normal_world` 없음·0) t_lift를 계산하지 않는다(`cr_basis` = `bracket_10Hz_source_missing`, 판정 불가). 실제 기록 확인(2026-11-15): C-1 L1-R 4행(평지 2, rpBop 2)의 t_lift는 사영 전과 같았고(93.1 / 93.1 / 92.8 / 93.1 s), C-5 V0 L2b 3행은 rev15를 목록에 넣은 시험에서 27.4 s(t_a 27.3 s)다.
- **rev12(78f1f99b, 2026-11-13 반영, worktree `z4368-p2c`, master `61f066f` 병합본 `7080c71`)**: 봉인 확인 목록에 rev12를 넣었다(raw sha = 코드 봉인 sha = `.sha256` 첫 토막, 다르거나 없으면 S-1, R12-6). R12-2: `code_at_launch.git`의 `clean`·`dirty`·`paths`는 기록만 한다(`R11-4_commit`의 `dirty_record`·`code_at_launch_paths`, `gs-load` `rev11_gs_items.r12_2_dirty_record_rows`). rev11판도 dirty로 멈추지 않았으므로 판정 동작은 같고, 기록 칸만 더했다. R12-3: `gs-load`도 `--git-at-start`가 필수다(없으면 종료 2). R12-4: 열린 루프 행의 `result.json` `code_state`는 대조하지 않고 `open_loop_code_state_same_record`(같음 여부)로 기록만 한다(rev11판도 열린 루프 `code_state`를 대조하지 않았다). R12-5: 행 로그에 `->` 줄이 없을 때의 대체를 `tag_glob`(부분 문자열)에서 `time_window`로 바꿨다(`row_window`, `time_window_folder`). 창은 그 행의 `progress.log` START~END(그 case의 마지막 START와 그 뒤 첫 END)이고, 없으면 배치 폴더 이름 시각 ~ 시각 + `wall_s`(`batch.json` `cases[].wall_s`, `est_s`는 쓰지 않음)다. 양 끝에 ±2 s를 둔다. 후보는 S8 `^<tag>_<YYYYmmdd_HHMMSS>$`, S6 `^.+_<tag>_L1R_<YYYYmmdd_HHMMSS>$`(`_<tag>_check_L1R_`·`<tag>x` 제외)이고, 폴더 시각이 창 안이며 `<--only>/result.json`이 있어야 한다. 창 없음·후보 0개·2개 이상은 입력 오류(종료 2, S-11)다. `gs-load`에서 행 폴더 입력 오류가 나면 그 행에 `input_error`를 적고 종료 2로 끝난다(이전에는 종료 1). R12-1(T4h 찾기 범위)은 이 도구가 T4h를 읽지 않아 해당 없다(5.00000절).
- **rev11(9bac4524, 2026-11-13 반영, worktree `z4368-p2c`, master `4312b8e`)**: 봉인 확인 목록에 rev11을 넣었다(raw sha = 코드 봉인 sha = `.sha256` 첫 토막, 다르거나 없으면 S-1, R11-7). R11-4: 모든 묶음의 모든 행(열린 루프 C-6C7 포함)에 `R11-4_commit` 항목을 더했다(`p2_kinds.commit_item`). `batch.json` `cases[].code_at_launch.git.head`가 판정서 `git_at_start`(입력 인자 `--git-at-start`, 7~40자리 16진, `judge`는 필수·없으면 종료 2)로 시작해야 한다. level·L2b·L1-R 행은 `result.json` `code_state.git_at_start.head`가 있으면 그것도 같아야 한다(R11-4 4 "그 기록이 있는 행"; 저장 G-S `…_130358`에서는 SCM 행 9개에 있고 L2b·L1-R 행에는 없다). 기록 없음이나 다름은 S-12 멈춤이다. `gs-load`는 `--git-at-start`를 선택으로 받아 행마다 `r11_4`(두 head, clean, 대조 여부, 문제, `s12`)와 끝의 `rev11_gs_items`(S-12 행 수, 열린 루프 행·그 S-12 수, `code_at_launch` 없음 수, `code_state` 대조 수, `r11_5_grades_written` = 거짓, rev11 봉인 상태)를 낸다. 기준 없이 돌리면 `s12`는 `code_at_launch` 없음만 센다. R11-1(Chrono 행 기대 스위치): `identity_scm`에 `liftoff_approach_slow.settings.enable` 대조를 더했다(C-4 끔 팔 = 거짓, 그 밖 Chrono 행 = 참, 다르거나 없으면 identity 판정 불가). 관문 요청·적용과 `flat_soil_margin_order_gate`는 앞 판부터 그 표대로 보고 있었다. 9값 프리셋 대조는 하지 않는다(앞 판과 같음, 5절). R11-5: `gs-load`는 앞 판부터 등급(verdict·묶음 상태)을 쓰지 않는다(시험으로 확인, `rev11_gs_items.r11_5_grades_written`). R11-6: 이 도구의 G-S 출력(`gs-load --out`)도 "Chrono G-S의 도구 출력"이므로 `v5_resume_4368/gs_chrono_<7자리 커밋>/`에 둔다(파일 이름 예: `p2c_gs_load.json`; R11-6의 "등"에 드는 것으로 읽음, 도구는 경로를 강제하지 않는다). R11-2(T4h)·R11-3(`commands_sha256`)·R11-1의 H-0 줄은 하네스 기록이라 이 도구가 읽는 곳이 없다(5.0000절).
- **rev10(62a0bd8d, 2026-11-13 반영)**: 봉인 확인 목록에 rev10을 넣었다(raw sha = 코드 봉인 sha = `.sha256` 첫 토막, 다르거나 없으면 S-1, R10-3). R10-1a: 전체 묶음 이름(`V5-RESUME-K1-` 접두어 포함)은 `batch.json` 최상위 `batch` 값이고 폴더 이름의 `batch_`~`_<YYYYmmdd_HHMMSS>` 부분과 대조한다(`p2_chrono.batch_name_of`). 키가 없으면 폴더 이름 부분을 쓴다. 키와 폴더 부분이 다름, 둘 다 정할 수 없음, manifest `batches` 키가 아님 = 묶음 이름 불명. 키는 있는데 폴더 이름이 그 꼴이 아니어서 대조할 수 없는 경우도 불명으로 둔다(경로 2 읽기, 6절 R-5). 짧은 묶음 ID(`C5` 등)는 manifest 키가 아니어서 불명이 된다. R10-1b(`ls_input_case`): 묶음 이름 불명, manifest `batches.<이름>.rows[]`에 같은 case 0개·여럿, `batch.json` `cases[]`에 같은 case 0개·여럿은 LS 판별 판정 불가다. 이전 rev9판은 manifest 행 0개(또는 묶음 없음)이고 `batch.json` 값도 없으면 "LS 아님"으로 읽었다. 이 경우를 판정 불가로 고쳤다. "LS 아님"은 두 출처 모두 그 case가 정확히 한 행이고 둘 다 `v5_setting`이 없거나 None일 때만이다. manifest 파일이 없거나, JSON으로 읽히지 않거나, `batches` 객체가 없으면 입력 오류(종료 2, S-11)다. C-5 `judge`는 rev9판부터 없음을 종료 2로 처리했고, 이번에 JSON 오류·`batches` 없음을 더했다. `gs-load`도 manifest를 필수로 바꿨다(R10-2: G-S가 모든 Chrono 행을 본다). R10-2: `gs-load`가 행마다 `r10`(전체 묶음 이름과 그 근거, manifest 행 수, `batch.json` 항목 수, R10-1b 경우 라벨, `s11`)을 내고, 끝에 `rev10_R10_2_gs_items`(경우별 행 수: 묶음 이름 불명, manifest 0개·여럿, `batch.json` 0개·여럿, 두 출처 값 없음; S-11 행 수; rev10 봉인 상태)를 낸다(값·verdict 없음). `r10`은 열린 루프 C-6C7을 포함한 모든 G-S 행에 대해 적재 전에 만든다.
- **rev9(4cf7843c, 2026-11-13 반영)**: 봉인 확인 목록에 rev9를 넣었다(raw sha = 코드 봉인 sha = `.sha256` 첫 토막, 다르거나 없으면 S-1, R9-8). R9-1: 열린 루프 C-6C7을 뺀 모든 묶음의 모든 행에 `R9-1_expect_controller` 항목을 더했다. SCM `c2_setup.expect_controller.ok`, L2b·L1-R `expect_controller.ok`가 참이 아니면(거짓·키 없음) 그 항목이 S-2 멈춤이다(G-S에서는 S-11로도 센다). J-P3만 판정 불가로 두지 않는다. R9-2: `law_locked` 형식 검사 여섯 항목(1 시간 열, 2 [N, 4]·N = 시간 열 길이, 3 int8, 4 {−1, 0, 1}, 5 인접 Δt 모두 \|Δt − 1 ms\| ≤ 10⁻⁶ s, 6 R9-3 −1 꼴)을 SCM·L2b에 같게 쓰고, 문제마다 항목 부호(`R9-2.1`~`R9-2.6`, 키 없음 = `key`)를 붙인다. R9-3: 첫 무장 전 −1(실행 처음부터, 네 다리가 같은 표본에서 함께 벗어남)만 허용하고 잠김으로 읽는다. 무장 뒤 −1·전 구간 −1·다리별 시점 불일치는 형식 오류다(이전 판의 "무장 뒤 −1 = 판정 불가 + 멈춤" 별도 분기는 없앴다). R9-4: LS 행은 manifest `batches.<묶음>.rows[].v5_setting`과 S9 배치 `batch.json` `cases[]` 같은 case의 `v5_setting`으로만 판별한다(이름 토큰 안 씀, `--manifest` 기본 = `v5_resume_4368/chrono_rows_manifest.json`, C-5 judge에서 manifest가 없으면 종료 2). 둘 다 없음·None = LS 아님, 한쪽만·다름 = 판정 불가(대체 다리 n_late > 0이면 "LS 판별 불가"로 멈춤), LS인데 태그가 ③가 아니면 S-2. 묶음 ID는 `batch.json` `batch`, 없으면 폴더 이름 `batch_<ID>_<stamp>`. R9-5: C-5 행 두 엔진 모두 `law_locked` 키 없음·형식 오류 = J11 판정 불가 + 멈춤(L2b 키 없음 = rev6 R6-B7·rev3 R3-C7 처리를 대체). R9-6: C-5 밖 닫힌 루프 묶음(C-1~C-4, C-8)에 `J11_record`(같은 계산, 멈춤 없음, 결측·형식 오류는 `input_absent`로 셈, `bundle_result.rev9_R9_6_j11_record`)를 더했다. R9-7은 경로 2가 태그를 재계산하지 않으므로 바꿀 것이 없었다(`is_extend_start_tag("final_C4G2_K1")` 거짓, `"final_C4G2_P3_K1"` 참을 시험으로 확인). `gs-load`는 행마다 `r9`(R9-1 확인값·S-2, R9-5 분류, R9-4 LS 분류)와 `law_locked_record.codes`·`pattern`을, 끝에 `rev9_R9_8_gs_items`(R9-1 S-2 수, R9-2 항목별 어긋난 행 수, R9-3 꼴별 수, R9-4 LS 행·판정 불가 수, C-5 S-11 후보 수, R9-6 입력 없음 수, rev9 봉인 상태)를 낸다(값·verdict 없음).
- **rev8(3ecafaaf, 2026-11-13 반영)**: 봉인 확인 목록에 rev8을 넣었다(raw sha = 코드 봉인 sha = `.sha256` 첫 토막, 다르거나 없으면 S-1, R8-4). R8-2: J-P3 적용 범위를 행 태그로 판별한다(원판 4.1 `v5_options.is_extend_start_tag`, rev3 R3-C8). 태그 = argv `--expect-controller`이고 실행 기록의 확인(SCM `c2_setup.expect_controller`, L2b `expect_controller`)이 참이어야 한다. 태그가 서지 않으면 S-2, ③ 요청 기록(argv `--extend-start-tracked`, `v5_hydraulics` 블록이 있으면 `hydraulic_options.extend_start_tracked`도, 키 없음 = 끔)이 태그와 다르면 S-2, 비③ 태그는 해당 없음, ③ 태그에서 `two_pressure.settings.extend_start_rule` 없음은 판정 불가(9.3), `tracked_bound`가 아니면 S-2. R8-3: SCM C-5 J11은 `step_series.npz` `law_locked`(시간축 `t_s`), L2b는 `pads.npz` `law_locked`(`t`)로 개정 6 6절·rev6 R6-B7·rev2 D-1 그대로 판정한다. 형식(R8-3a: [N, 4] int8, 같은 파일 시간축과 행 수 같음, 1 ms, 값 {1, 0, −1})이 틀리면 그 배열을 쓰지 않는다. SCM 키 없음·형식 오류는 J11 판정 불가 + 멈춤(대체 다리 유무와 무관, Q-R8-1 = B)이다. L2b 키 없음은 rev6 R6-B7 그대로다. `gs-load` 출력에 `law_locked_record`(키 있음·형식)와 `jp3_scope`(R8-4 G-S 기록용 범위 분류)를 더했다. R8-1(r79·격자 태그 재계산)은 경로 1 도구 몫이라 바꾸지 않았다(5.0절).
- **rev7(e81f7d31, 2026-11-13 반영)**: 봉인 확인에 rev7을 넣고, 436.8 규칙 파일(원판·rev1~rev7)은 raw sha가 코드의 봉인 sha와 같은 폴더 `.sha256` 첫 토막 둘 다와 같아야 통과한다(R7-7, 없거나 다르면 S-1). R7-4: 판정의 키 결측 처리는 원판 9.3·rev2 R2-2 그대로이고, 켬 팔에서 없어도 되는 `c2_setup.las_off`는 끔이 아닌 것으로 읽는다(끔 팔 = argv `--las-off`, 기록과 다르거나 끔 팔에서 키가 없으면 identity 판정 불가). 팔별 키 있음은 `identity.r7_4_las_keys`에 기록만 한다(키 있음 확인은 경로 1 `gs-check --manifest`). R7-5: L2b·L1-R 행 폴더는 행 로그 `<batch>/<case>.log`의 마지막 `batch wall … -> <폴더>` 줄을 먼저 쓰고(태그 대조), `rows[].folder_method`에 방법을 적는다. C-6·C-7 경로 2는 이 도구(`--bundle C-6C7`, rev3 R3-G11). R7-6: `rows[].placement_record`에 풀·마스크 기록. R7-1·R7-2·R7-3은 하네스·경로 1 몫이라 바꾸지 않았다(5.1절). G-S에서 드러난 J-P3 V0 행 처리도 고쳤다(2절 표).
- **rev5(452a8436)·rev6(809e5639)**: 시각 원점(R6-1: L2b·L1-R `phases`만 상대 → + `start_t_s`, 사건·`fallback_lock_log`·npz는 절대), L1-R D8 t_lift = 첫 10 Hz 행 t_b(t_a 기록, R6-B1), L2b 판정 힘 = S8-A2(`F_cyl_min_interval`, 부상 표본은 `F_cyl_mean_20ms`; R40-2 느린 성분도 같은 힘, R6-B2), 377 창의 LOC = 첫 확정 LOC(최종 LOC로 했을 때 결과는 기록, R6-B3), t_D = 100표본(R6-B4), 이동 압력 = `record.npz` 10 Hz 행의 `u_applied`·`F_cyl`(R6-B5), 실제 대체 다리 = 로그 ∪ 대체 사건(로그에만 있으면 S-11, R6-B7), S-01·02 안전 정지 허용(R6-B8), SGS 부상 = 정지 뒤 패드 법선 ≤ 0(R6-B9), U-S9-G6c `P3-8_preloc_loss` 분기(R6-C3), J11 `fallback_lock_log`(`leg`·`t_start_s`·`window_end_s`, R5-B1)·LS 행 L-e(R5-B3), D2 사유 = `INFO_ROD_PRESSURE_FAULT_REASON:<다리>:<사유>`가 `D2`로 시작(R5-B2), PS-c 순서(R5-B4).
- **rev4(7ea87a30) R4-A2 (사용자 결정 Q-R4-1 = C)**: C-5 J-P3(`hydraulics_record.extend_bound_check.breach_reads`)·J11 창(`pads.npz` `law_locked` + 명령 기록 + `fallback_lock_log`)·D2(사유 D2 대체 사건, `d2_violation_start_ratio`)는 **재계산** 층. C-5 T4-0·T4·T5는 경로 2가 `chrono_t45_replay`를 **직접 실행**(`p2_t45.py`: 도구 파일 f46b5ab 뒤 0커밋 확인, 개정 7 95행 회귀 18행 확인, 출력은 경로 2 폴더, 등급은 `p2_kinds.t45_items`가 따로 적용). PS-c E-1~E-6(재계산)·E-7(연구 A 판정 함수 실행)은 **아직 만들지 않았다**(PS-c 행이 생기면 그 행은 판정 불가). 한계 공개 문장은 rev4 R4-A2 문장을 판정서에 그대로 적는다.
- (이전) **세 층(rev3 R3-G1, 사용자 결정 Q-C1 = A)**: (1) 시계열로 정의가 닫히는 항목은 재계산, (2) 감시기·사건 판정 논리가 필요한 항목(C-5 T4-0·T4·T5·J11 창·J-P3·D2, PS-c E-1~E-4·E-6·E-7)은 `result.json`의 항목별 기록 결과를 **재집계**하고 등급 규칙(FLAG·멈춤·해당 없음)을 경로 2가 따로 적용, (3) 출력의 `bundle_result.TABLE_REAGG`(항목·행 수·출처 키·판정 수)와 `recalculated_judged_items`·`reaggregated_items`. **재집계 항목은 독립 재계산이 아니다**(판정서 한계 절에 rev3 R3-G1 문장을 그대로 적는다).
- 이 도구는 결과의 **판정 값을 입력으로 쓰지 않는다**(재집계 층 제외). 규칙이 이름으로 지정한 입력 키 두 개만 읽는다: `p3b.weight_N`(rev2 R2-5의 W), `p3b_ext.start_condition.crawler_attitude_deg`(원판 9.1 C-8). rev3 R3-G13이 이를 위반 아님으로 정했다.
- C-6·C-7은 `openloop_compare.py`의 `analyse`(함수·상수 정의만 `ast`로 꺼내 그대로 실행, 고정 실행 목록 드라이버는 실행 안 함)이고, 그 함수가 읽는 `p3a`의 저장 판정 복사 키(`stored_*`)는 출력에서 뺀다. 속도비 r_vu·r_v는 rev2 R2-4 식으로 따로 계산한다.
- 행마다 읽은 원 파일 이름과 sha256을 `rows[].input_files_sha256`에 적는다(rev3 R3-G2).

## 1. 실행

dynamics-dev 활성화, PowerShell, E코어(0x00FF0000)로 돌렸다.

```powershell
[System.Diagnostics.Process]::GetCurrentProcess().ProcessorAffinity = [IntPtr]0x00FF0000
$d = "<repo>\06_analysis\02_control\verif_matrix\v5_resume_4368\path2_chrono"
& C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B "$d\p2_chrono.py" seal
& C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B "$d\p2_chrono.py" judge --bundle C-1 `
    --batch <repo>\07_results\S9\batch_V5-RESUME-K1-C1_<stamp>\batch.json --git-at-start <판정서 git_at_start> `
    --out <출력>\p2_C1.json
& C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B "$d\test_p2_synthetic.py" --tmp <빈 폴더>
```

- `--bundle`은 `C-1`·`C-2`·`C-3`·`C-4`·`C-5`·`C-6C7`·`C-8`이다.
- `gs-load --batch <G-S batch.json> --git-at-start <최종 Y 커밋> --out <출력> [--results-root R] [--row-dir CASE=PATH]`(`--git-at-start` 필수, rev12 R12-3): G-S 행(`r4368.role` = `gs`)마다 폴더를 찾고 적재해 그 묶음의 항목 함수를 돌린다. 출력은 폴더·찾은 방법·입력 sha·입력이 없어 판정 불가·기록이 된 항목 이름과 사유·예외·R7-4 팔별 키·R7-6 키 있음·`law_locked_record`(rev8 R8-3a 키 있음·형식·문제 목록)·`jp3_scope`(rev8 R8-2 범위 분류 `applicable`/`not_applicable`/`key_missing_9.3`/`S-2`, 태그, 대조한 요청 기록)·`r9`(rev9 R9-1·R9-4·R9-5 분류)·`r10`(rev10 R10-2)과 끝의 `rev9_R9_8_gs_items`·`rev10_R10_2_gs_items`·`rev11_gs_items`(G-S 기록 항목 수)와 행마다 `r11_4`(rev11 R11-4)뿐이다(값·verdict·묶음 상태 없음, 판정 아님). `--manifest` 기본은 `v5_resume_4368/chrono_rows_manifest.json`이고, 없거나 읽히지 않거나 `batches`가 없으면 종료 2다(rev10 R10-1b). 종료 0 = 모든 행이 예외 없이 돌았음, 1 = 예외 행 있음 또는 G-S 행 0, 2 = 봉인 오류.
- C-5는 먼저 `p2_t45.py <repo(git_at_start checkout)> <07_results(저장 3단계 18행이 정확한 이름으로 있는 결과 루트)> <경로 2 출력 폴더> <C-5 L2b 행 폴더 ...>`(종료 0 = 관문·회귀 통과 + 재생 매핑 문제 없음)로 도구 관문·회귀·재생을 돌리고(종료 0 = 관문·회귀 통과), 그 `t45_path2.json`을 `judge --bundle C-5 ... --aux t45=<경로>`로 넘긴다.
- C-2는 PS-c 행이 있으면 먼저 `p2_e7.py <repo(git_at_start 판 도구가 있는 checkout)> <경로 2 출력 폴더> --git-at-start <판정서 git_at_start> <PS-c 사건 행 폴더 ...>`(종료 0 = 관문 통과 + 모든 행 도구 실행, 1 = 관문 실패 또는 행 오류(사건 없는 기준 행 포함))로 E-7 도구를 돌리고, 그 `e7_path2.json`을 `judge --bundle C-2 ... --aux e7=<경로>`로 넘긴다. 넘기지 않으면 PS-c 행의 E-7은 판정 불가다.
- `judge`는 `batch.json`의 `cases[]` 가운데 `criteria_id`(최상위 또는 `r4368.criteria_id`)가 묶음과 같고 G-S가 아닌 행만 판정한다. 행 폴더(`rows[].folder_method`):
  - SCM: `batch.json` 폴더/`case`(`batch_folder`).
  - L2b·L1-R: 행 로그 `<batch>/<case>.log`의 마지막 `batch wall … -> <러너 폴더>` 줄의 `<러너 폴더>/<argv --only>/`(`case_log`). 러너 폴더 이름에 argv `--tag`가 없으면 종료 2. 그 폴더에 `result.json`이 없으면 결과 루트 아래 같은 상대 경로(`07_results` 뒤, `case_log_relocated`), 그래도 없으면 종료 2.
  - 그 줄이 없으면 rev12 R12-5 시각 창(`time_window`): 창 = `progress.log` START~END, 없으면 배치 폴더 시각 + `wall_s`(`est_s` 안 씀), 양 끝 ±2 s. 후보 = `07_results/S8/<tag>_<stamp>` 또는 `07_results/S6/…_<tag>_L1R_<stamp>`(정확 맞춤, `_check_L1R_` 제외) 가운데 시각이 창 안이고 `<--only>/result.json`이 있는 폴더. 정확히 1개가 아니거나 창이 없으면 종료 2(S-11). rev11판까지의 `tag_glob`(부분 문자열 맞춤)는 없앴다.
  - `--row-dir CASE=PATH`(`row_dir`)가 모두에 앞선다.
  - 행 로그를 먼저 쓴다(실행 기록이고 경로 1 출력이 아니다). 시각 창은 rev12 R12-5 문장대로 이 도구가 따로 구현했다(경로 1 코드는 보지 않음).
- **도구 sha(rev22 R3d 판, 현재 값, LF 바이트)**: 공통 `863a8d6feba7e80d6115b2cfae5f13f2ddfb5c852885fbe576809187bbc97920`. 묶음별: C-1 `9e14e7df…`, C-2 `418191df…`, C-3 `a4405a3b…`, C-4 `1804276d…`, C-5 `5e4b4292…`, C-6C7 `80520582…`, C-8 `08df7b2e…`. 바뀐 파일: `p2_rules.py` `1f835a3d…`(봉인 목록만). 그 밖 도구 파일은 rev21 R3c 판과 같다. 자체 시험 330/330.
- (이전) 도구 sha(rev21 R3c 보완판): 공통 `dba04b89359e3ff2f914677e72fb28135770bc008b19a2a8a1fa560eb566a9c7`. 묶음별: C-1 `95be41fd…`, C-2 `ff6b27f7…`, C-3 `ba8b4aa0…`, C-4 `23dccb21…`, C-5 `82cfac5e…`, C-6C7 `9f3d4402…`, C-8 `e50ad90a…`. 바뀐 파일: `p2_core.py` `009427c7…`, `p2_rules.py` `80c17e5e…`. 그 밖 파일은 rev20 정렬판과 같다. 자체 시험 328/328.
- (이전) 도구 sha(rev20 정렬판): 공통 `ad34b0cf10bc7071e161d9fd7db75e617996b31a5cf73b3106408f95ecdfccc1`. 묶음별: C-1 `06c879e1…`, C-2 `21026a54…`, C-3 `b12eaef0…`, C-4 `1fcc55f1…`, C-5 `faec0a35…`, C-6C7 `2d6e6b43…`, C-8 `37170358…`. 바뀐 파일: `p2_rules.py` `f2f72fcb…`, `p2_kinds.py` `96846945…`(주석만), `p2_e7.py` `49974318…`. 그 밖 파일은 rev19 정렬판과 같다. 자체 시험 312/312.
- (이전) 도구 sha(rev19 정렬판): 공통 `c6c999ad9362470b1561c7b4df22aba0a05c9de57f180a6ac62718c3a7fcbe4a`. 묶음별: C-1 `18bd7b95…`, C-2 `bd9e4f65…`, C-3 `4d465cd4…`, C-4 `5601637f…`, C-5 `8428d83e…`, C-6C7 `87bdb047…`, C-8 `c752cb34…`. 파일별: `p2_chrono.py` `bb1f9028…`, `p2_rules.py` `971e5362…`, `p2_core.py` `88d8be72…`, `p2_kinds.py` `c7cf3089…`, `p2_t45.py` `03317f2a…`, `p2_psc.py` `fe2f414d…`, `p2_e7.py` `63ae3169…`, `p2_b_c2.py` `7f51c053…`, `p2_b_c3.py` `3054e670…`, `p2_b_c5.py` `e454eb2c…`. 자체 시험 304/304.
- (이전) 도구 sha(rev18 R3b 보완판): 공통 파일(`p2_chrono.py`·`p2_rules.py`·`p2_core.py`·`p2_kinds.py`·`p2_t45.py`·`p2_psc.py`·`p2_e7.py`, `seal`·`gs-load`) `359d1fe3e62efbe472b93c1508c6a5b8dd7b83fb78b4d4759b267ae09f18ba73`. 묶음별 `tool_sha256`: C-1 `25e6cce0…`, C-2 `2ffb35d6…`, C-3 `7f4ccc24…`, C-4 `1f8630d6…`, C-5 `296168e0…`, C-6C7 `c1effd14…`, C-8 `75fc8cea…`. 파일별: `p2_chrono.py` `5c52f457…`, `p2_rules.py` `fffad83c…`, `p2_core.py` `b591eba2…`, `p2_kinds.py` `37670169…`, `p2_t45.py` `03317f2a…`(그대로), `p2_psc.py` `ef16ea9f…`(새 파일), `p2_e7.py` `3d88fa53…`(새 파일), `p2_b_c2.py` `b9b005c1…`, `p2_b_c3.py` `3054e670…`. 자체 시험 282/282(`--lawlock-record` 없이; 저장 3단계 배치 출처 대조 1건 SKIP). `path2/p2_4368.py`가 바뀌어 `../path2_v5c/p2v5c_common.py`의 `P2_CORE_SHA`(`0ccc5186…`)와 어긋난다(R18-1 (다) 밖이라 이 커밋에서 고치지 않음, `path2/README.md` 끝 절).
- (이전) 도구 sha(rev15 봉인 목록판, 2026-11-15): 공통 4파일 + `p2_t45.py`(`seal`·`gs-load`) `3c0f81e9fd4b37ee46f3e22494a7e2c7b2ead57d0730942ad46ac33641ad2552`(이전 R15-3 원본판 `8e05e83c…`, `e0238de`판 `a021a3a1…`, rev12판 `e7473997…`). 묶음별 `tool_sha256`: C-1 `ab4c7710…`, C-2 `ef0af69d…`, C-3 `053c8697…`, C-4 `4e43fc1c…`, C-5 `79b22f6b…`, C-6C7 `51bc10d2…`, C-8 `e63bd968…`. 파일별: `p2_rules.py` `1d497f7b…`, `p2_core.py` `11c978ae…`, `p2_t45.py` `03317f2a…`, `p2_kinds.py` `5823443d…`, `p2_chrono.py` `4702d328…`, `p2_b_c5.py` `4a5e3536…`. 자체 시험 227/227(`--rules-repo C:\workspace\z4372-seal --lawlock-record …`; 저장 3단계 배치가 없는 checkout에서는 출처 대조 1건을 건너뜀), `--lawlock-record` 없이 223/223, `--rules-repo` 없이 이 브랜치에서 170/170(봉인·CLI SKIP). README·`test_p2_synthetic.py`는 도구 sha에 들지 않는다.
- (이전) rev12 반영판 공통 `e7473997…`, C-5 `a2dff49d…`.
- (이전) rev11 반영판 공통 `70c930b0…`, C-5 `8d263788…`. rev10 반영판 공통 `171104ad…`, C-5 `31e6fe46…`.
- (이전) rev9 반영판 공통 `6f229e07…`, C-5 `c716c711…`. rev8 반영판 공통 `b4d3c177…`, C-5 `ef2c91cb…`.
- 자체 시험의 `--lawlock-record <SCM 행 폴더>`(선택): 러너 커밋 `7527fc3`으로 만든 짧은 SCM 기록(경로 1 산출물 아님)으로 `step_series.npz` `law_locked` 읽기·형식·J11 계산·전이 수·J-P3 태그 판별을 본다(이 기록의 argv는 result.json에 없어 시험이 ③ VB argv를 준다). 2026-11-13 사용 기록: scratchpad `cad-lawlock\new\LL_new`(3600행, 1 ms, int8, 값 {0, 1}, 다리마다 1→0→1→0→1).
- ③ 판별(원판 4.1)은 이 checkout의 `03_src/outrigger_sim/hydraulics/v5_options.py`를 `03_src`에서 불러와 `is_extend_start_tag`만 부른다(다른 경로에서 불러오면 입력 오류). 이 파일은 제어기 옵션 코드이고 436.8 판정 도구가 아니다. sha는 `seal.recorded`에 기록만 한다.
- 종료: 0 = 묶음 `통과`·`기록 완료`, 1 = `미달`·`판정 불가`·`기록 불완전`·멈춤 있음, 2 = 입력·봉인 오류(S-1), 3 = 내부 오류. 마지막 줄 JSON에 `tool_sha256`(공통 4파일 + 묶음 모듈, 파일별 sha를 이름순 "이름 sha\n"로 이은 문자열의 sha256), `out_sha256`(출력 파일 바이트).
- 봉인 대조(원판 8.2 S-1, rev2 R2-9, rev7 R7-7, rev8 R8-4, rev9 R9-8, rev10 R10-3, rev11 R11-7, rev12 R12-6): 436.8 규칙 원판·rev1~rev12는 raw sha만 보고, 그 sha가 코드의 봉인 sha와 같은 폴더 `.sha256` 첫 토막 둘 다와 같아야 한다(`sidecar_missing`·`sidecar_mismatch`·`mismatch`는 S-1). 부록 A 파일(d1 규칙·rev1, v5 rev6·12·12a·12b, `las_p5r4_k1_judgement.md`)은 raw가 다르면 CRLF→LF 정규화 sha를 보고 같으면 통과 + "CRLF 변환만 다름" 공개. 명세·YAML sha는 기록만.

## 2. 파일과 규칙 절 ↔ 함수

| 파일 | 역할 |
|---|---|
| `p2_rules.py` | 봉인 대조, 문턱 숫자(각 줄에 원문 절), 7.6 비교 허용(`ge`·`lt`·`gt`·`le`) |
| `p2_core.py` | 행 적재(`load_row`), 시각·항목 계산 |
| `p2_kinds.py` | 행 종류별 항목 묶음(D8·P, P3/G6, C-5), 묶음 상태(8.1) |
| `p2_b_c1.py`~`p2_b_c5.py`, `p2_b_c8.py` | 묶음별 행 종류 대응과 기대 행 수 |
| `p2_chrono.py` | CLI |
| `p2_psc.py` | C-2 PS-c 행 426.3 E-1~E-7(rev18 R18-3 1) |
| `p2_e7.py` | E-7 도구 실행기(rev4 R4-A2 안 c): `p2_e7.py <repo> <out_dir> --git-at-start <ref> <PS-c 행 폴더 ...>` → `<out_dir>/e7_path2.json` |
| `test_p2_synthetic.py` | 합성 입력 자체 시험(실제 결과를 읽지 않음) |

| 규칙 절 | 함수 | 정의(이 도구가 쓴 문장) |
|---|---|---|
| 원판 7.6 | `p2_rules.ge/lt/gt/le` | 비교 허용 10⁻⁹(그 단위) |
| 명세 284 P3-2 t_D, rev2 R2-5 | `p2_core.t_departure` | 폐루프 시작 뒤 크롤러 1 ms 법선 < 0.01 W가 0.1 s 이상 이어지는 첫 구간의 첫 표본. W = `p3b.weight_N` |
| v5 rev6 5 t_lift | `t_lift`, `t_lift_sus` | 단계가 idle·check·touch가 아니고 크롤러 ≤ 0인 첫 1 ms 표본, 1 ms 기록이 없으면 10 Hz 괄호(t_a + 1 ms) |
| 424.8.1 최종 LOC | `loc_times` | 뒤에 `INFO_LOC_REVOKED`가 없는 마지막 `crawler_liftoff_confirmed` |
| P3-1 + U-S9-G6d + 423.3 Q-G | `recontacts`, `classify_recontact`, `p3_1` | t_D 뒤 ≥ 0.01 W 구간을 사건으로. 최종 LOC 이전 시작: 지속 ≤ 0.5 s ∧ LOC 전 종료 ∧ 최대 ≤ 0.15 W → transient FLAG. LOC 뒤: 시작 ≤ LOC + 1.0 s ∧ 지속 ≤ 0.1 s ∧ 최대 ≤ 1.2 × 0.01 W → chatter FLAG. READY 뒤 시작·LOC 없음 → 엄격 실패. READY ~ +10 s 크롤러 최대 > 0 → 실패, 창이 안 차면 판정 불가 |
| P3-2 + 419.8/419.8.1 + 424.8.1 | `p3_2`, `reapproach_intervals` | 최종 LOC 존재 ∧ 첫 DONE 전 ∧ (t_LOC − 0.1, t_LOC] 크롤러 최대 < 0.01 W ∧ t_LOC − t_D ≤ T_lim. T_lim = 0.010/(0.25 v_max) + 1.0 s(YAML v_max, 규칙 표기 2.9 s는 기록). 시간만 넘으면 419.8 다섯 조건(창 재시작 포함 재접근, 재접근 끝 기준 지연, 거짓 LOC 아님, P3-3·FAULT 0, 순서) 또는 424.8.1 다섯 조건 + 조건 6(424.9: t_LOC_fin − t_off ≤ (1 + n_revoke) T_lim, rev3 R3-G12)이 모두 참일 때 FLAG. 취소된 LOC의 하중 중 확정은 기록만(R3-G10 Q-17) |
| P3-3 | `p3_3`, `min_force_after` | [t_D, 끝] 다리별 1 ms 참 F_cyl 최소 ≥ F_min(YAML) |
| P3-4 + 284.1 + 433.6, rev3 R3-G7·G9 | `creep_stop_times`, `p3_4` | 1.0 s 후향 침하 속도(`pad_sinkage_geometric_m` 차분) \|v\| < 0.1 mm/s 네 패드가 끝까지 이어지는 마지막 구간 시작, 없으면 부호 판정 + `creep_vibration_suspect`. 창 = [max(그 시각, 마지막 READY 진입), 끝], 창 안 \|roll\|·\|pitch\| 최대 ≤ 0.2°(장착 몫 더하지 않음). 창 < 5 s → `window_short` FLAG(항목 집계는 통과 아님 `item_tally`, 행 등급은 실패 아님) |
| P3-5 | `p3_5` | 첫 READY ~ 끝 `s9_rows.rut_clearance_m` 최소 ≥ 25 mm, 실행 전체 `s_motor_m` 최대 ≤ 0.6848 m |
| P3-6, d1 rev1 | `ready_item` | 첫 READY 진입 − 폐루프 시작 ≤ 한계 |
| P3-8 + 377 | `p3_8` | min(첫 LOC, 토양 모드 시작) 전 `leg_reapproach_start`·`relevel_predicted`·`probe_aborted_low_load` 0. G6 행만 377 강등: 시작 다리 [시작, 첫 LOC + 1 s] 최소 ≥ F_min(rev3 R3-G8) ∧ FAULT 0이면 FLAG |
| P3-9 | `p3_9` | 기록: `leg_reapproach_deferred`마다 보류 다리 [보류, 다음 재접근 시작 + 0.3 s] 최소 |
| G6-6 | `items_p3(g6=True)` | FAULT 0 ∧ READY ≤ 120 s |
| 명세 427.9 판정 분류(17690~17692), rev6 R6-B8·D-26, rev18 R18-2 (S-01~04) | `p2_core.safe_stop_427_9`, `saturation_rows`, `p2_kinds.items_p3(allow_stop=True)`, `safe_stop_summary` | 행에 `FAULT_LIFT_STROKE_LIMIT` 사건이 있으면 분기. 조건 1 첫 정지 사건 사유 토막 = `soil`, 2 `FAULT_STROKE_END` 0, 3 t_D 뒤 패드 법선 ≤ 0 표본 0, 4 [t_D, 끝] 네 다리 1 ms 최소 ≥ F_min, 5 작용 명령 ≠ 0 제어 행 ≤ 180 bar ∧ 포화(신장 ∧ ≥ 210 bar) 0. 모두 참 `allowed_stop`(P3-5·P3-6·FAULT0 대신), 하나라도 거짓 `fail`, 그 밖 `indeterminate`. 행 등급에서 `allowed_stop`은 실패가 아니고 묶음 출력에서 따로 센다 |
| 명세 426.3 연구 A E-1~E-6, rev4 R4-A2 안 b (C-2 PS-c) | `p2_psc.load_event`, `branch_end`, `e_items` | 입력 `soil_event_series.npz`(열 20개 이름 대조, 1 ms, 시작 = t_ev − 0.5 s), `result.json` `soil_event.spec`·`driver.t_ev_s`·`event_reached`(`soil_event.judgement`는 읽지 않음), `phases`·`events`·`s9_rows`, `step_series.npz` `s_motor_m`. 가지 끝 = t_ev 뒤 10 Hz 제어 시각 가운데 t ≥ t_ev + max(12 s, 램프 + 3 s)이고 READY가 3 s 유지된 첫 시각, 없으면 t_ev + 60 s. 사건 G4·SS = 느린, FS24·RE1bF = 빠른(그 밖 = 판정 불가). E-1 느린: 사건 뒤 모든 다리 부상(접촉 ≤ 0) 0 / 빠른: 사건 다리 + 대각 다리별 누적 ≤ 1.8 s, 마지막 재접지 ≤ 3.0 s. E-2 빠른만(느린 = 해당 없음, 판정 키 밖): W = [0, min(쌍 마지막 재접지 + 0.82, 5) s](부상 없으면 0 + 0.82), 인접 두 다리 W 안 부상 합 ≤ 0.5 s·틈 ≤ 2 mm, W 밖 0(앞 F_s < 2 kN이고 밖 합 ≤ 0.1 s·틈 ≤ 0.5 mm면 FLAG). E-3 빠른 W 뒤 / 느린 사건 뒤 가지 끝까지 네 다리 F_cyl ≥ F_min. E-4 창(빠른 W, 느린 [0, 램프 + 3 s]) 안 다리별 F_cyl/A_p ≤ 350 bar, 창 밖(사건 뒤) 밸브 \|u\| > 10⁻⁶ 표본 ≤ 180 bar, 포화(u > 10⁻⁶ ∧ ≥ 210 bar) 0. E-5 가지 끝 단계 READY, 끝 1 s 평균 \|roll\|·\|pitch\| ≤ 0.2°, 가지 끝까지 FAULT 사건·단계 0, 실행 시작 ~ 가지 끝 최대 모터 행정 ≤ 0.6848 m(실행이 가지 끝 전에 끝나면 판정 불가). E-6 크롤러 > 0: 빠른 W 안 FLAG `E-6_event_transient_recontact`, W 밖·느린 사건 뒤 → 실패, 가지 끝 크롤러 > 0 → 실패, 가지 끝까지 마지막 `s9_rows.rut_clearance_m` ≥ 25 mm(0 < c < 25 mm FLAG `E-6_post_event_clearance`, ≤ 0 실패). 기록: `INFO_DIFF_SINK*`(DSb75), 사건 뒤 LOC 취소 수. 계산할 수 없는 항목은 판정 불가이고 행도 판정 불가 |
| 426.3 E-7, rev4 R4-A2 안 c (C-2 PS-c) | `p2_e7.py`(`tool_gate`, `run_row`), `p2_psc.e7_item` | 원 규칙이 지정한 `04_scripts/03_control/s9/s9_soil_event_screen.py`의 `judge_soil_event`를 경로 2가 직접 부른다. 가지 행(위 가지 끝까지)으로 `BranchResult`를 만들고 그 출력의 `twist.n_bundles`만 쓴다. 조건 1: 그 파일 `git log f46b5ab..<git_at_start>` 0커밋 ∧ 실행 파일 = `<git_at_start>` blob, 그 파일이 쓰는 이름과 `r67_g1_screen`(`judge_event`·`twist_work`·`is_fast`·`_intervals`·상수 6개)·`r51_reapp_closed_loop`(`_intervals`)의 해당 소스가 f46b5ab·git_at_start·실행 파일에서 같아야 한다(r67은 f46b5ab 뒤 2커밋이 있으나 다른 함수만 바뀜 — 함수 단위 대조, 파일별 커밋 수 기록). 조건 3: 출력은 경로 2 폴더. 조건 4: 등급 = n_bundles ≤ 1을 경로 2가 적용(도구의 `gates`·`pass`는 기록만). 도구의 토양 기록(`_soil_records`)에 쓰는 제어기는 빈 대역이고 그 기록은 버린다. 관문 실패 = E-7 판정 불가 + S-11, 출력 없음·행 없음·n_bundles 없음 = 판정 불가. 한계 공개 문장(rev4 R4-A2)은 묶음 출력 `psc_E.limit_disclosure`에 그대로 싣는다 |
| 398.1 SL-1, 427.12.5 SA-4 | `items_p3`, `stop_classification` | `WARN_LIFT_STROKE_LIMITED` → FAULT 0·부상 0·P3-1·P3-3·P3-4 통과면 P3-5 완화. `FAULT_LIFT_STROKE_LIMIT:soil` → SA-4 조건 전부 ∧ 이탈 뒤 정지면 `stroke_limited_stop`(허용 행은 통과), 아니면 실패 |
| 명세 3 항목 2·3·4, d1 11 D8·P | `d8_force`, `d8_end_attitude`, `pressure_item`, `ready_item` | t_lift 뒤 1 ms 최소(L2b·L1-R `F_cyl_min_interval`) ≥ F_min. 마지막 5 s(전부 READY) \|자세 − 목표\| 최대 + 0.02 ≤ 0.2°. 헤드 등가 F_cyl/A_p: 작용 명령 ≠ 0(\|u\| > 10⁻⁹, rev3 R3-G10 Q-13) 표본 ≤ 180 bar, 전 표본 ≤ 350 bar. READY 평지 90 / 경사 120 s. FAULT 0. 이륙 = rev6 t_lift(rev3 R3-G5) |
| 명세 210.2 R40-2, rev3 R3-G6 | `d8_force(rigid_nsc_hold=True)` | L2b 판정 행: 원값 최소 < F_min ∧ 그 시각이 t_lift + 8 s 안 ∧ 같은 8 s의 1 s 중심 이동평균 최소 ≥ F_min + 5 kN(14,414.589 N) → `hold`(행은 판정 불가, 멈춤 "d1 8절 L1 짝으로 풀거나 묻기") |
| rev3 R3-G1 재집계 | `reagg_item`, `reagg_table`, `items_c5`, `p2_b_c2._psc` | `result.json`에서 항목 이름(T4-0·T4·T5·J11·J-P3·D2·E-k와 별칭)인 키를 찾아 그 값(bool, 또는 `verdict`·`status`·`result`·`passed`·`ok`·`pass`)을 pass/fail/flag로 읽는다. 못 찾거나 못 읽으면 판정 불가. 등급 규칙: T4-0 실패 → 도구 결함 멈춤, T4·T5 실패 → H-7, J-P3는 `two_pressure.extend_start_rule` = `tracked_bound`(③ 켬) 행만, J11은 `fallback_lock_log`가 비면 `not_computed` 기록(rev3 R3-C7), 있으면 재집계하고 실패 → H-7 |
| rev2 R2-4, 원판 5.3·9.1 | `p2_b_c67` | `analyse` 그대로 + r_vu·r_v. 명세 11047 FLAG = 이륙 전 최소 < F_min |
| 원판 4.2·6, rev2 R2-3, rev1 RV1-10 a | `identity_scm`, `identity_l2b` | 기록 확인(어긋나면 판정 불가 + S-2/S-3/S-4 검토) |
| rev7 R7-4, rev2 R2-2, 원판 9.3 | `identity_scm`, `r7_4_las_presence` | 끔 팔 = argv `--las-off`. `c2_setup.las_off`는 켬 팔에서 없어도 끔 아님으로 읽고(결측 아님), 끔 팔에서 없거나 기록이 argv와 다르면 identity 판정 불가. R7-4 표의 팔별 키(`c2_setup.las_off`, `liftoff_approach_slow.start_s`·`end_s`·`end_reason`·`active_periods`·`ramp`·`ramp.periods_applied`) 있음과 표의 조건은 기록만(`absent_where_required`). 판정의 `start_s` 없음은 R2-2대로 LAS-b 시작 안 함. `p3b.P3-3_leg_force` 두 키는 경로 2가 읽지 않는다(P3-3은 1 ms 시계열로 다시 계산) |
| 436.8 rev8 R8-2, 원판 4.1·6, rev3 R3-C8, v5 rev8 3.2·rev9 3.2 (J-P3 적용 범위) | `jp3_item`, `p2_core.row_tag`, `is_extend_start_tag` | ③ 판별 = 행 태그(argv `--expect-controller`, 확인 `ok` 참, 기록 `name`이 있으면 같아야 함)의 `v5_options.is_extend_start_tag`. 태그가 서지 않음 → S-2. 요청 기록 대조: argv `--extend-start-tracked`, `v5_hydraulics` 블록이 있으면 `hydraulic_options.extend_start_tracked`(키 없음 = 끔)도. 다르면 S-2. 블록이 없으면 argv만. 비③ 태그 → 해당 없음(`extend_start_rule` 없어도 결측 아님). 단 비③ 태그인데 `extend_start_rule` = `tracked_bound`면 태그와 실행 제어기가 다르므로 S-2(경로 2 읽기, 6절 R-2). ③ 태그: `controller_meta.two_pressure.settings.extend_start_rule` 없음 → 판정 불가(9.3), `tracked_bound`가 아님 → S-2, 맞으면 `extend_bound_check.breach_reads` 합 > 0 → 실패 + H-7. rev7판의 `two_pressure.extend_start_rule`(settings 밖) 대체 읽기는 뺐다(R8-2가 settings 키를 지정) |
| 436.8 rev9 R9-2·R9-3·R9-5 (rev8 R8-3·R8-3a 대체), v5 rev6 6, rev6 R6-B7, rev2 D-1, rev5 R5-B1 (J11) | `j11_item`, `p2_core.law_locked_check`, `law_locked_pattern`, `law_lock_view` | 잠금 상태: SCM `step_series.npz` `law_locked`(시간 열 `t_s`), L2b `pads.npz` `law_locked`(`t`). R9-2 형식(두 엔진 같음): 1 시간 열 있음, 2 [N, 4]·N = 시간 열 길이, 3 int8, 4 값 ⊂ {−1, 0, 1}, 5 인접 Δt 모두 \|Δt − 10⁻³\| ≤ 10⁻⁶ s(절차 값), 6 R9-3 꼴. R9-3: −1이 없거나, 실행 처음부터 이어지는 −1을 네 다리가 같은 표본에서 함께 벗어나고 그 뒤 −1이 없으면 허용(그 −1 = 잠김). 무장 뒤 −1(`after_arming`)·전 구간 −1(`whole_run`)·다리별 시점 불일치(`per_leg_mismatch`)는 형식 오류. R9-5: C-5 행에서 키 없음·형식 오류 → 배열을 쓰지 않고 J11 판정 불가 + 멈춤(SCM·L2b, 대체 다리 유무와 무관). 창 끝·짝짓기·늦음은 위 P-1 읽기 그대로(t_w + 10⁻⁶ s 뒤 첫 표본이 잠김이 아니면 늦음) |
| 436.8 rev9 R9-4 + rev10 R10-1, rev5 R5-B3 (J11 LS 행) | `ls_classification`, `ls_input_case`, `ls_item`, `manifest_rows`, `batch_case_counts`, `p2_chrono.batch_name_of`·`batch_ctx` | manifest `batches.<전체 묶음 이름>.rows[]` 같은 `case`의 `v5_setting`과 `batch.json` `cases[].v5_setting`. 묶음 이름 불명·manifest 행 0개/여럿·`batch.json` 항목 0개/여럿 → 판정 불가(R10-1b). 두 출처 모두 한 행: 같고 ∈ LS1~LS4 → LS(n_late > 0 = L-e), 같고 그 밖 → LS 아님(H-7), 둘 다 값 없음·None → LS 아님, 한쪽만·다름 → 판정 불가(`LS_class` indeterminate, n_late > 0이면 "LS 판별 불가" 멈춤). LS인데 태그 비③ → S-2. C-5 행에서만 씀 |
| 436.8 rev12 R12-5 (rev7 R7-5 대체 경로) | `p2_chrono.row_window`, `time_window_folder` | 행 로그 `->` 줄이 없을 때: 창 START~END 또는 배치 폴더 시각 + `wall_s`, ±2 s, S8 `<tag>_<stamp>`·S6 `…_<tag>_L1R_<stamp>` 정확 맞춤, 후보 1개만, 아니면 종료 2(S-11) |
| 436.8 rev12 R12-2·R12-4 (기록만) | `commit_item` | `clean`·`dirty`·`paths` 기록(`dirty_record`), 열린 루프 `code_state`는 같음 여부만 기록(`open_loop_code_state_same_record`), 멈춤 아님 |
| 436.8 rev11 R11-4 (원판 6 커밋 칸, 8.2 S-12, Q-R11-1 = B) | `commit_item`, `p2_chrono.git_ref_arg`, `augment_items(commit=True)` | 모든 묶음 행(C-6C7 포함): `cases[].code_at_launch.git.head`가 `--git-at-start`(판정서 `git_at_start`)로 시작. C-6C7 밖 행은 `result.json` `code_state.git_at_start.head`가 있으면 그것도. 기록 없음·다름·기준 없음 → S-12 |
| 436.8 rev11 R11-1 (Chrono 행 기대 스위치) | `identity_scm` | C-4 끔 팔(argv `--las-off`·`c2_setup.las_off` 참): LAS-b `settings.enable` = 거짓, `k1_order_gate` = `on`. 그 밖 SCM 행: `enable` = 참, `preset`. 둘 다 `k1_order_gate_effective`·`flat_soil_margin_order_gate` 참. 다르면 identity 판정 불가 |
| 436.8 rev9 R9-1 (원판 6 태그 칸, 8.2 S-2) | `expect_item`, `p2_chrono.augment_items` | C-6C7을 뺀 모든 묶음 행: `c2_setup.expect_controller.ok`(SCM) / `expect_controller.ok`(L2b·L1-R)가 참이 아님(거짓·키 없음) → S-2 멈춤(G-S S-11) |
| 436.8 rev9 R9-6 (C-5 밖 J11) | `j11_record_item`, `p2_chrono.r9_6_summary` | C-1~C-4·C-8 행: `j11_item`과 같은 계산을 기록만(`verdict` = record, `stop` 없음, C-5였다면의 멈춤 문구는 `c5_stop_would_be_record`), `law_locked` 결측·형식 오류는 `input_absent`로 셈 |
| rev7 R7-6, 원판 6 풀 | `p2_chrono.placement_record` | 행마다 `placement_record`: 배치 행 `pool`·`planned_pool`·`placement_applied`, result.json `placement.affinity_mask_process`·`affinity_mask_ok`·`power_throttling_off_ok`, batch.json `affinity_masks`, `r4368.arm`. 기록만(등급에 넣지 않음). `affinity_mask_ok` 거짓, `pool` ≠ `planned_pool`, `r4368.arm`과 argv `--las-off` 불일치는 `notes`에 적는다 |
| 원판 7.2, rev2 R2-1·R2-2 | `k1_classification` | 기록 모순(`would_block`∧¬due, `applied`∧¬due, `applied`∧`would_block`) → S-5. `_SKIPPED:order` 수 ≠ 막힘 수 → S-5 |
| v5 rev6 5 H-9 | `items_c5` | M2 켬(`v5_hydraulics.hydraulic_options.m2_law`) 행에서 `hydraulics_record.m2_clip_times_s` 중 t_lift 뒤 잘림 > 0 → H-9 멈춤 |
| v5 rev6 6, rev8 R8-3 (기록) | `items_c5` | `law_locked` 잠김↔이동 전이 수(SCM·L2b, 첫 무장 전 −1 = 잠김), 첫 무장 뒤 −1 표본 수 |
| 원판 7.4, rev2 R2-5·R2-6 | `p2_b_c8.judge_row`, `p2_b_c4` | m = t ≥ t_D 다리별 최소의 네 다리 최소 → 멈춤 / 여유 기록 / 기록. F<F_min·F<F_min+2 kN 시간 = [t_D, t_D + 8 s] 표본 수 × 1 ms(끝까지 창은 기록) |

## 3. 묶음별 대응

| 묶음 | 행 | 판정 항목(경로 2) | 등급에 넣는 항목 |
|---|---|---|---|
| C-1 | C2-01·02·04·05·06·08 L2b | D8·P | F·끝 자세·READY·압력·FAULT 0·기록 확인·K1 분류 |
| C-1 | C1-09~12 L1-R | D8·P(기록) | 기록 행 |
| C-2 | C2-03·07 L2b / S-01·02 SCM / 기준선 추가 / PS-c | D8·P / P3 + READY 120 s + 427.9 안전 종료 분기(rev18 R18-2) / 같은 계열 / E-1~E-7(rev18 R18-3, E-7 `--aux e7=`) | 고정 4행 정확히 1번씩(rev2 R2-8), 추가 ≤ 4, PS-c ≤ 2, 합 4~10 |
| C-3 | S-03·04 SCM | P3 + G6(P3-6 90 s는 기록) | 2행 |
| C-4 | 4행 SCM 혼합 | D8 + G6 + P3-3 + R_c + 8 s 창 시간 + K1(끔 팔 'LAS 없음') | 기록 묶음 |
| C-5 | 35행 | 재계산: t_lift·H-9, J-P3(436.8 rev8 R8-2, 태그 ③ 행), J11 창(실제 대체 다리, rev2 D-1, SCM `step_series.npz`·L2b `pads.npz` `law_locked`, rev9 R9-2·R9-3·R9-5), LS 분류(rev9 R9-4, `rev9_R9_4_ls`), D2(기록), K1, R9-1. 도구 실행: T4-0·T4·T5(L2b 행만, SCM은 해당 없음). 묶음 문구 개정 6 4.6(`rev6_4_6_phrase`) | H-9, K1, J-P3, J11 창, T4-0·T4·T5, R9-1 |
| C-6C7 (`--bundle C-6C7`) | C-6 1 + C-7a 1 + C-7b 1 | `analyse` 값, 명세 11047 FLAG, r_vu·r_v | 기록 묶음(rev3 R3-G11) |
| C-8 | O-C5 2행 | 7.4 m·처리 칸·시간·R_c | 기록 묶음(rev3 R3-G11) |

## 4. 읽은 것 (원판 9.2, 1.2절 꼴)

- 규칙: 원판 전체, rev1 전체, rev2 전체(코디네이터 통지 뒤, master `b33e686`), rev3 1~32행·360~553행(R3-F·R3-G·결정 표, master `9ce2fdc`), `d1_selection_rules.md` 1~64행·145~204행, `d1_selection_rules_rev1.md` 전체, `v5_criteria_rev6.md` 81~200행 + T4·T5·J11 줄 grep, `v5_criteria_rev12.md` 전체, `v5_criteria_rev12a.md` 60~105행, `v5_criteria_rev12b.md` 15~47행.
- 명세 `00_docs/04_control/s6_control_spec.md`(sha `1924ae89…`): 300~345행(S6 항목 1~8), 11010~11075행(284·284.1), 14278~14300행(377), 14795~14812행·15138~15165행(423.3), 15340~15360행(424.8.1), 16940~16975행(419.8), 17246~17270행(426.3), 15420~15435행(424.9 조건 6), 그리고 grep 결과 줄(D8, 180 bar, 마지막 5 s, 8 s 규칙 210.2, chatter, `window_short`·433.6, `stroke_limited_stop`, 427.12, 17279·17475 줄 등).
- rev5 89~119행·140~156행, rev6 25~183행(master 병합 `825159f`). 제어기 코드 `03_src/outrigger_sim/control/two_pressure.py`의 `window_end_s` 대입부(2525~2562행, `_open_lock_stretch` 창 식). 제어기 코드이고 판정 도구가 아니다. G-S L2b 행 `controller_meta.two_pressure`와 `settings`·`extend_bound_check`의 키 이름(값 없음).
- rev4 전체(master `136b455`), v5 rev7 1~130행, rev8 40~75행, rev9 45~67행, rev2 72행(D-1). `chrono_t45_replay.py`의 docstring(1~60행)·`summary`·`rev7_summary`·`report_of`·`parse_args`·`main`·`replay_case` 행 키(R4-A2가 실행을 지정한 도구, 436.8 경로 1 도구 아님). 회귀용 저장 3단계 L2b 18행 폴더 이름(`07_results/S8/v5s3_*`).
- `06_analysis/03_hydraulic/coupled/v5/paper_runs/scripts/openloop_compare.py` 전체(R3-G11이 지정한 기존 분석 정의, 436.8 경로 1 도구 아님). G-S 열린 루프 행 `GS_P3a_G1_B_VB_prop_lift10`의 `flow_series.npz` 열 이름과 `series.npz` 배열 이름, `result.json` 키 이름 검색(T4·T5·J11·J-P3·D2 등, 값 없음).
- YAML `02_params/rexome33.yaml`의 `head_area_m2`, `max_speed_m_s`, `F_min_cylinder_N` 줄.
- 원 데이터(키 이름·형식 확인, G-S 배치만): `batch_V5-RESUME-K1-GS_20261113_010654`(두 행), `_012403`·`_020211`의 `batch.json`, `07_results/S8/r4368gs_D1C2_middle_fdown3.2_Fs4_20261113_020211/`, `07_results/S6/bundleC_d1c1_r4368gs_D1C1_top_flat_crx3_L1R_20261113_020211/`. 읽은 것: npz 배열 이름·모양, `result.json` 키 트리(값은 기록 필드만: `phases`, `events`, `settings`, `controller_tag`, `expect_controller`, `pad_record`, `runner`, `s9_rows[0]`, `start_condition` 키 이름, `mass_scale.judgement_weights`, `c2_setup.expect_controller`, `hydraulics_record.m2_*`, `v5_hydraulics.hydraulic_options`, `c2_soil`의 두 키, `args` 일부), `controller_events.json` 형식, 시각 기준(쿼터니언 ↔ `roll_pitch_deg` 차 3×10⁻¹²°, L2b·L1-R 단계·사건 시각 = `settings.start_t_s` 기준 상대). G-S 행으로 적재기·항목 함수가 키 결측 없이 도는지만 봤고 값·판정은 출력하지 않았다.
- rev7 반영(2026-11-13, worktree `292f9d2`): rev7 전체와 `.sha256`, 원판·rev1~rev6 `.sha256` 첫 토막, rev2 R2-2 표(30~44행), 원판 6절 표·9.3, v5 rev8 42·59행 줄과 rev9 1~65행 grep 줄(J-P3 적용 범위). G-S 배치 `07_results/S9/batch_V5-RESUME-K1-GS_20261113_082117`: `batch.json`(키 이름, `cases[]`의 `case`·`criteria_id`·`r4368`·`pool`·`placement_applied`·`argv`), 행 로그 `GS_D1C1_*.log`·`GS_D1C2_*.log` 본문(러너 폴더 줄), L2b·L1-R 러너 폴더 목록, SCM C-5 G-S 세 행의 `controller_meta.two_pressure` 키 이름·`settings` 키 이름과 `v5_hydraulics.hydraulic_options` 값. `gs-load` 출력(값·verdict 없음)만 보았다.
- rev8 반영(2026-11-13, worktree `y4368-p2c`, 9b8c449·7527fc3 병합본): rev8 전체와 `.sha256`. `03_src/outrigger_sim/hydraulics/v5_options.py`의 import 줄과 `switch_base_tag`·`is_extend_start_tag` 정의(원판 4.1이 지정한 판별 함수, 판정 도구 아님). 러너 기록 `cad-lawlock\new\LL_new`(7527fc3, 경로 1 산출물 아님): `step_series.npz` 배열 이름·`law_locked` 모양·자료형·값 집합·전이 시각, `t_s` 간격, `result.json`의 `step_series.law_locked_rule` 문장, `controller_meta.two_pressure` 키 이름과 `settings`의 잠금 창 세 값, `fallback_lock_log`(빈 목록), `c2_setup.expect_controller`, `v5_hydraulics.hydraulic_options`. G-S 배치 `…_082117`은 `gs-load` 출력(값·verdict 없음, `law_locked_record`·`jp3_scope`)만 보았다.
- rev9 반영(2026-11-13, worktree `y4368-p2c`, master `e5a2c19` 병합본 `8a1b903`): rev9 전체와 `.sha256`. `v5_resume_4368/chrono_rows_manifest.json`(R9-4가 판별 입력으로 지정한 공용 행 목록, 경로 1 산출물 아님): 최상위 키, `batches`의 묶음 이름·행 수, `rows[]` 필드 이름, C-5·GS 묶음 행의 `case`·`v5_setting`·`criteria_id`·`controller`. G-S 배치 `…_082117`의 `batch.json` 최상위 키·`batch` 값, `cases[]`의 `case`·`v5_setting`. 배치 `…_094502`는 `batch.json`이 없는 미완 폴더임을 목록으로만 보았다. 이 배치로 `gs-load`를 다시 돌려 R9 기록(값·verdict 없음)만 보았다(5.2절).
- rev12 반영(2026-11-13): rev12 전체와 `.sha256`. 저장 G-S `…_130358`의 `progress.log`(START·END 줄 꼴, `wall_s`), `batch.json` `cases[]` 키 이름과 `wall_s`·`est_s`, `07_results/S6`·`S8`의 `r4368gs` 폴더 이름 목록(이름 꼴 확인만).
- rev11 반영(2026-11-13, worktree `z4368-p2c`, master `4312b8e`): rev11 전체와 `.sha256`. 저장 G-S `07_results/S9/batch_V5-RESUME-K1-GS_20261113_130358`의 `batch.json` `cases[].code_at_launch.git`(head·clean)과 C-4 끔 팔 SCM 행 `result.json`의 `code_state` 키 이름·`git_at_start` 값, `controller_meta.liftoff_approach_slow.settings` 키 이름과 `enable` 값. 같은 배치로 `gs-load --git-at-start ba2da55`와 SCM 9행의 `identity_scm`을 돌려 R11 기록만 보았다(5.2절).
- rev10 반영(2026-11-13, master `8b4ad93` 병합본 `6bc1102`): rev10 전체와 `.sha256`. README 5.0절 표기 정정을 위해 `path2_v5c/p2v5c_common.py`의 `P2_V5J_SHA`·`P2_CORE_SHA` 두 줄 위치를 이 브랜치·master·`y4368`에서 grep으로만 보았다(dynamics-expert 경로 2 파일, 경로 1 아님).
- **보지 않은 것**: `resume4368_judge.py`, `u3_judge_k1.py`, `resume_k1_record.py`, `resume_k1_steps.py`, `gs_check_*.txt`, `chrono_rows_check.json`, `chrono_rows_manifest.json`(rev9 반영 전까지. 위 줄의 필드만 rev9 R9-4로 읽음), `run_S9.py`·`run_S8C.py`·`run_S6C.py`·p3b 판정 함수, `result.json`의 `p3b`(위 `weight_N` 1개 제외)·`p3b_ext`(위 1개 키와 `start_condition` 키 이름 제외)·`acceptance`·`h4`·`c2`·`stroke`·`s8_end` 값, `las_p5r4_k1_judgement.md` 본문(sha만), `03_src` 코드.

- rev18 R3b 보완(2026-11-15, 새 작성자)에서 읽은 것: 메인 세션이 만든 rev18 인계 파일(봉인본 R18-1, R18-2의 S-01~04 글머리, R18-3, R18-4를 옮긴 것; 봉인본의 다른 절은 열지 않음), rev4 R4-A2(51~84행)와 R4 필드 표(220~232행), rev6 R6-A 표(34~48행, D-26~D-34)·R6-B8·R6-B9, `d1_selection_rules.md` 11절 표(162~177행), 명세 17690~17692행(427.9 판정 분류)과 **426.3 연구 A(17246~17270행)** — R4-A2 안 b가 "명세 426.3 정의대로"를 지정해 E-1~E-6 정의 문장을 읽었다(메인 세션 지시의 읽기 목록 밖이므로 공개), 원판 9.1~9.3, 이 README와 `path2/README.md`, 경로 2 코드. 원 규칙 지정 도구 `04_scripts/03_control/s9/s9_soil_event_screen.py` 전체, `04_scripts/03_control/s8/r67_g1_screen.py`의 머리·상수·`is_fast`·`twist_work`·`judge_event`(60~123·280~384행), `r51_reapp_closed_loop.py`의 `_intervals`(경로 1 도구 아님). `r67_g1_screen.py`의 f46b5ab 뒤 두 커밋(`24495d8`·`c4e0ed9`, 메시지가 "436.8 path 1")은 메시지와 diff 덩어리 머리(`@@` 줄: `v5_job_record`·`v5_branch_record` 둘레)만 보았고 본문은 열지 않았다. 원 데이터: C-2 배치 `07_results/S9/batch_V5-RESUME-K1-C2_20261114_230123`의 `batch.json`(case·criteria_id·d1_id·r4368·argv), PS-c 두 행의 파일 목록·`soil_event_series.npz` 배열 이름·모양·열 이름, `result.json` 최상위 키·`soil_event`의 `spec`·`driver`·`series`·`head_area_m2`·`event_reached`, `phases`, `events` 일부, `s9_rows` 마지막 행, 시간축 대조(사건 시각과 `offset_m`, `step_series`와 같은 값); `batch_V5-RESUME-K1-C2_20261114_222633`의 `D1S_J1_B_bottom_Fs4_r0_pm2p8`의 `phases`·`events`·`record.npz` 배열 이름, C-2 두 배치·C-3 배치 행의 `result.json`에서 `FAULT_LIFT_STROKE_LIMIT`·`FAULT_STROKE_END`·`WARN_LIFT_STROKE_LIMITED` 문자열 grep 개수. **공개(사고)**: 첫 확인 스크립트가 `soil_event` 블록의 앞 1,500자를 출력해 러너의 `soil_event.judgement` 앞부분(cslow 행)을 보았다. 도구는 그 블록을 읽지 않고 그 값에 맞춰 구현하지 않았다. 실제 행에는 적재 확인(예외·판정 불가 사유만 출력, verdict 출력 없음)만 돌렸다.

- rev19 정렬에서 더 읽은 것: rev19 [정의] 글머리 파일(`rev19_definitions_handoff.md`, sha `ff5e61b8…`), `run_S9.py` 1185~1200행(A1 상수)·1374~1446행(`soil_event_stop_s`·`judge_chrono_soil_event`), `git diff -U0 f46b5ab b9f5707 -- r67_g1_screen.py`의 첫 덩어리 본문(R19-7이 덩어리 확인을 지정함; 경로 1 커밋 `24495d8`·`c4e0ed9`의 그 파일 변경분)과 그 판의 `RESUME_K1_KEY` grep, manifest `batches`별 행 이름(짝 확인). `soil_guard_stop_rule.py`·`s9_soil_slope.classify`·`verify/s8_control.py`는 열지 않았다(R19-1·R19-4 정의 문장으로 충분했고 R19-4는 경로 2에 해당 없음).

### 독립성 공개

- 이 작성자는 rev1·rev2를 쓴 control-expert와 같은 에이전트 정의지만 다른 실행이다. 이 실행에서 경로 1 코드·출력은 열지 않았다.
- 에이전트 메모리 색인(`MEMORY.md`, 일반 함정 목록)이 시작 때 문맥에 들어 있었다. 이 프로젝트 경로 1의 코드·값은 들어 있지 않다.
- `d1_selection_rules_interp.md`(부록 A 밖 해석 문서)의 11행 한 줄을 grep 출력으로 보았다("D8 잠김 ≤ 350 bar = 실행 전체 F_cyl/A_p 최대"). 이 도구의 350 bar 정의(전 표본)는 그 줄과 같다. 그 문서의 나머지는 열지 않았다.
- rev1 머리 6행은 "경로 2는 dynamics-expert"라고 적었고, rev2 R2-0이 Chrono C-1~C-5를 새 control-expert 인스턴스로 다시 배정했다(사용자 결정 2026-11-13).

## 5. 만들지 않은 것 · 재집계로 낮춘 것

| 항목 | 처리 |
|---|---|
| C-5 T4-0·T4·T5 | 도구 실행(rev4 R4-A2 c). 감시기 독립 재구현(B안)은 하지 않았다 |
| PS-c E-1~E-6 / E-7 | rev18 R3b 보완에서 만듦(`p2_psc.py` 재계산, `p2_e7.py` 도구 실행). 앞 판은 미구현이었다 |
| C-5 짝 비교(VB↔V0, LS−VB, 시드), 재실행↔저장 비트 비교, 12a 플랜트 선행 | 만들지 않음(기록 항목, 판정 무관) |
| S-01·02 "토양 사건 0.5 s 평균(v5 3.1 ⑦)" | 만들지 않음(원문 미독) |
| D8 LAS-b 설정 9값 대조 | 만들지 않음(프리셋 값이 규칙 문장에 없음) |
| R40-2 보류의 해제(d1 8절 L1 짝 대조) | 자동화하지 않음. 보류 행은 판정 불가 + 멈춤 문구 |

### 5.00000 rev12에서 바꾸지 않은 것 · 해당 없음

| rev12 절 | 이유 |
|---|---|
| R12-1 T4h 찾기 범위(Q-R12-1 = A) | 이 도구는 T4h 파일을 읽지 않는다(`grep -i t4h` 0건, C-5 T4·T5는 `p2_t45.py`가 `chrono_t45_replay`를 실행하고 그 출력의 등급만 매김, J-P3는 Chrono `hydraulics_record.extend_bound_check`). 해당 없음 |
| R12-2 dirty | rev11판의 `commit_item`도 `head`만 대조하고 dirty로 멈추지 않았다. 판정 동작은 그대로이고 기록 칸(`dirty_record`, `code_at_launch_paths`, G-S 수)만 더했다 |
| R12-4 열린 루프 `code_state` | rev11판도 열린 루프 행의 `code_state`를 대조하지 않았다(`code_state_compared` 거짓). 같음 여부 기록만 더했다 |
| R12-3 `judge` | `judge`의 `--git-at-start`는 rev11판부터 필수였다. 바꾼 것은 `gs-load`뿐 |
| R12-6 순서·G-S 재실행 | 메인 세션 절차 |

### 5.0000 rev11에서 바꾸지 않은 것 · 해당 없음

| rev11 절 | 이유 |
|---|---|
| R11-1 H-0 줄(R-0·R-0K·T-3K, `t3.*` 판별) | 하네스 `las_t3` 줄이다. 이 도구는 Chrono 행만 읽는다. Chrono 쪽 두 줄(C-4 끔 팔, 그 밖 행)은 위 표대로 맞췄다 |
| R11-2 T4h 찾기 | T4h는 하네스 r79·격자 기록의 감시기 출력이다. 이 도구는 T4h 파일을 읽지 않는다(C-5 T4·T5는 `p2_t45.py`가 `chrono_t45_replay`를 실행) |
| R11-3 `commands_sha256` | 하네스 명령 해시. 이 도구는 쓰지 않는다. ③ 판별은 앞 판부터 태그(`is_extend_start_tag`)·`hydraulic_options`·`extend_start_rule`로 한다(R11-3이 정한 구분과 같음) |
| R11-5 G-S 행 등급 | `gs-load`는 앞 판부터 verdict·묶음 상태를 쓰지 않는다(시험 "no verdict / status keys"). 바꿀 것 없음, 확인만 |
| R11-6 `judge --out` 필수 | 이 도구의 `judge`·`gs-load`는 앞 판부터 `--out`이 필수다 |
| R11-7 순서·G-S 재실행 | 메인 세션 절차. 러너의 열린 루프 `code_at_launch` 기록(cad-expert)이 들어간 최종 Y에서 G-S를 다시 돌려야 C-6C7 G-S 행의 S-12가 풀린다 |

### 5.000 rev10에서 바꾸지 않은 것

| rev10 절 | 이유 |
|---|---|
| R10-3 순서·`git_at_start`·G-S 재실행 | 메인 세션 절차. 이 도구는 봉인 목록에 rev10을 넣고 `gs-load`가 R10-2 항목을 내는 것까지다 |
| 본 실행의 LS 판별 불가 처리 | rev9 R9-4 그대로(늦은 대체 다리가 있으면 "LS 판별 불가"로 멈춤, 없으면 기록). R10-1b의 새 경우는 `LS_class.input.blocking`에 라벨로 남는다 |
| 숫자·등급 | rev10은 새 숫자가 없다 |

### 5.00 rev9에서 바꾸지 않은 것

| rev9 절 | 이유 |
|---|---|
| R9-7 (K1 단독 태그, R8-1c 규칙 3·5) | 태그 재계산(R8-1)은 경로 1 도구 몫이다(R8-1d). 경로 2는 행 태그를 argv `--expect-controller`로 받고 ③만 `v5_options.is_extend_start_tag`로 읽는다. `final_C4G2_K1` → 비③, `final_C4G2_P3_K1` → ③을 시험으로 확인만 했다 |
| R9-8 순서·`git_at_start`·G-S 재실행 | 메인 세션 절차. 이 도구는 봉인 목록에 rev9를 넣고, 최종 Y에서 `gs-load`가 R9-8 기록 항목(`rev9_R9_8_gs_items`)을 내는 것까지다 |
| 숫자 문턱·등급 | rev9 새 숫자는 절차 값 10⁻⁶ s 하나이고, 이 도구는 rev8 때부터 같은 값을 쓰고 있었다(검사 방식만 "증가 확인 + 최대 편차"에서 "모든 Δt가 허용 안"으로 고쳐 비증가 시간 열도 R9-2.5로 셈) |
| T4-0·T4·T5, J-P3 판정 문장 | rev9가 바꾸지 않았다. R9-1 S-2는 J-P3의 rev8 태그 불성립 S-2와 별도 항목으로 겹쳐 나온다(멈춤 사유 둘) |

### 5.0 rev8에서 바꾸지 않은 것

| rev8 절 | 이유 |
|---|---|
| R8-1 (T4h 없는 r79·격자 태그 재계산 대조) | 하네스 r79·격자 기록의 최상위 `controller_tag` 대조이고 R8-1d가 "대조는 경로 1 도구가 한다"고 정했다. Chrono 행 태그는 그대로 argv `--expect-controller`와 확인 `ok`(R8-2도 같은 읽기)로 본다 |
| R8-4 순서 중 `path2_v5c`의 `P2_CORE_SHA` | 그 값은 `path2/p2_4368.py`(dynamics-expert 경로 2) 파일 sha다. 위치는 최종 Y 후보 `y4368`의 `path2_v5c/p2v5c_common.py`의 상수 `P2_V5J_SHA`·`P2_CORE_SHA`이고(줄 번호는 개정마다 바뀌므로 이름으로 적는다), 현재 값은 그 파일의 `P2_CORE_SHA` 상수를 본다(이 README에 값을 옮겨 적지 않는다). 이 README의 앞 판은 "14·43행"이라고 적었는데, 14행은 docstring의 두 이름 언급이고 43행은 갱신 전 판(이 브랜치·master는 아직 42·43행)의 위치라 최종 Y 기준으로는 틀렸다. 이 도구의 파일이 아니므로 이 작성자가 바꿀 것은 없다. 갱신은 `path2`·`path2_v5c` 작성자 몫이다 |
| R8-4 `git_at_start`·G-S 재실행 | 메인 세션 절차. 이 도구는 Y에서 `gs-load`로 `law_locked_record`·`jp3_scope`를 내는 것까지다 |
| 숫자 문턱·등급 | rev8은 새 숫자를 쓰지 않는다(머리 10행). R8-3a "1 ms"의 형식 허용 10⁻⁶ s는 판정 문턱이 아닌 도구 읽기다(6절 R-4) |
| L2b J11 키 없음 | R8-3 정의 4 "L2b 행은 … rev6 R6-B7 그대로". 결측 시 멈춤 문장은 SCM 절에만 있어 L2b는 그대로 두었다(rev9 R9-5가 대체: 지금은 SCM과 같이 판정 불가 + 멈춤) |

### 5.1 rev7에서 바꾸지 않은 것

| rev7 절 | 이유 |
|---|---|
| R7-1a·R7-1b (r79·격자 최상위 태그) | 하네스 r79·격자 기록이고 대조는 경로 1 도구가 한다고 정했다. Chrono 행 태그는 그대로 `--expect-controller`·`expect_controller.ok`(L2b·L1-R)와 `v5_hydraulics.controller_tag`(SCM)로 본다 |
| R7-1c (T-3K R-0 태그 키) | 하네스 T-3K 줄. Chrono 경로 2와 무관 |
| R7-2 (첫 DONE) | r79 하네스 `base` 기록 모양의 규칙. Chrono 첫 DONE은 `phases`(L2b·L1-R은 + `start_t_s`, rev6 R6-1)의 첫 `done`이고, 419.8 조건 5는 이미 엄격 비교(최종 LOC < 첫 DONE − 10⁻⁹, rev3 Q-12, `p3_2`)다. DONE 없음은 조건 참(Q-12) |
| R7-3 (이름 대응표) | 하네스 `d1.g6_preloc`·T-3K 정체성. Chrono 377 창은 rev6 R6-B3(첫 확정 LOC + 1 s) 그대로 |
| R7-5 경로 1 v2 시각 창 | 경로 1 방법. 경로 2는 행 로그 → 태그 검색 순서를 따로 정했다(1절) |
| R7-8 숫자 | ±2 s는 경로 1 절차 값이라 쓰지 않는다. 5 ms는 R7-2 하네스 대조 |

### 5.2 G-S 적재 확인 (판정 아님, 2026-11-13)

- 배치 `07_results/S9/batch_V5-RESUME-K1-GS_20261113_082117`, `gs-load` 종료 0, 12행 예외 0. L2b·L1-R 두 행은 `case_log`로 찾았다(같은 태그 G-S 폴더가 여럿이라 `tag_glob`였으면 종료 2였다).
- 입력이 없어 판정 불가·기록이 된 항목은 10 s G-S 길이 때문(READY·LOC·이륙 없음: P3-1·P3-2·P3-4·P3-5·D8 F·H-9)과 SCM C-5 행의 `pads.npz law_locked` 없음(J11 창은 실제 대체 다리가 없으면 기록, 있으면 판정 불가, rev6 R6-B7 그대로)이다. V0 SCM 행의 J-P3는 이번 수정으로 해당 없음이다.
- 이 배치는 마스크 기록 도입(`e860578`) 전 실행이라 `placement.affinity_mask_*`·`affinity_masks`·`placement_applied`가 없다. `placement_record`는 None으로 적는다.
- rev8판으로 같은 배치를 다시 적재(2026-11-13, `gs-load` 종료 0, 12행 예외 0): SCM C-5 세 행의 `law_locked_record.present` = 거짓이고 J11 사유가 "step_series.npz law_locked missing"이다. 이 배치는 7527fc3 이전 실행이라 예상된 결과다(rev8 R8-4: 기록 추가 이전 G-S는 기록만). L2b 행(`GS_D1C2_…`)의 `pads.npz` `law_locked`는 형식 확인을 통과했다. `jp3_scope`: VB SCM 행 `applicable`(argv·`hydraulic_options` 대조), V0v 행 `not_applicable`(argv·`hydraulic_options`), S6SEED V0 행 `not_applicable`(`v5_hydraulics` 블록 없음 → argv만), S-2 0행.

- rev9판으로 같은 배치를 다시 적재(2026-11-13, `gs-load` 종료 0, 12행 예외 0, 출력 sha `0935be85…`): `rev9_R9_8_gs_items` = R9-1 S-2 0행(11행 모두 `ok` 참, C-6C7은 대상 아님), R9-2 항목별 어긋난 행 `key` 10(C-5 SCM 3 + C-5 밖 SCM 6 + L1-R 1), `R9-2.1`~`R9-2.6` 0, R9-3 꼴 `none` 1(L2b 행), R9-4 LS 0·판정 불가 0(C-5 G-S 세 행 S6SEED·VB·V0v가 manifest·`batch.json`에서 같음), C-5 S-11 후보 3, R9-6 입력 없음 7, rev9 봉인 `match`.

- rev10판으로 같은 배치를 다시 적재(2026-11-13, `gs-load` 종료 0, 12행 예외 0, 출력 sha `9f934a00…`): `rev10_R10_2_gs_items` = 12행 모두 전체 묶음 이름 `V5-RESUME-K1-GS`(`batch` 키 = 폴더 이름 부분), manifest 행과 `batch.json` 항목이 case마다 1개씩, 묶음 이름 불명 0·manifest 0개/여럿 0·`batch.json` 0개/여럿 0, 두 출처 값 없음 1(`GS_D1C1_top_flat_crx3`, L1-R 행), S-11 0행, rev10 봉인 `match`. rev9 항목은 앞 줄과 같다.

- rev11판으로 저장 G-S `…_130358`(`ba2da55`에서 돈 배치, R11-7에 따라 기록만, 인용하지 않음)을 적재(2026-11-13, `gs-load --git-at-start ba2da55` 종료 0, 12행 예외 0, 출력 sha `84f909f3…`): `rev11_gs_items` = S-12 1행(열린 루프 `GS_P3a_G1_B_VB_prop_lift10`, `code_at_launch` 없음, 러너 수정 전이라 예상된 결과), 나머지 11행은 `code_at_launch.git.head` = `ba2da55…`, `code_state` 대조 9행(SCM) 모두 같음, rev11 봉인 `match`. SCM 9행 `identity_scm`은 모두 pass(C-4 끔 팔 `enable` 거짓, 그 밖 참). rev9·rev10 G-S 항목: `law_locked` 키 없음 1행(L1-R, R9-6 입력 없음), SCM 9행·L2b 1행 형식 통과, R10-1b 두 출처 값 없음 1행(L1-R), S-11 0행.

## 6. 확인 필요

### 6.00000000000 rev21 뒤

- 새로 묻는 것 없음. 경로 2의 읽기: t_lift,sus의 "단계가 idle·check·touch가 아니고 … 이어지기 시작한 첫 표본"을 "끝까지 ≤ 0.01 W가 이어지는 구간 안에서 단계 조건을 처음 만족하는 표본"으로 읽었다(두 조건을 함께 만족하는 첫 표본과 같다). 정확히 0.01 W인 표본은 ≤ 0.01 W로 센다(7.6).
- 실제 기록 확인(값·verdict 출력 없음): 원 자료 행 `07_results/S8/v5s3_VB_D1C2_middle_rollm4.4_Fs4_20261115_004908/D1C2_middle_rollm4.4_Fs4`에서 `d8_force`가 예외 없이 돌고 `1ms_sus` 기준 t_lift,sus와 10 Hz 올림 값이 있음만 보았다.

### 6.0000000000 rev20 뒤

- T-8 → rev20 R20-1, T-9 → rev20 R20-2로 정해졌다. 새로 묻는 것 없음.
- 공개: (1b) 다른 파일 확인 때 도구가 `r67_g1_screen`을 import하는 파일(경로 1 시험 `05_tests/unit/test_resume4368_rev1.py` 포함)의 import 문과 속성 접근을 프로그램으로 파싱했다. 작성자는 파일 이름과 grep 결과의 파일 목록만 보았고 그 본문은 열지 않았다.

### 6.000000000 rev19 뒤

- T-1·T-2·T-3·T-4·T-5·T-6은 rev19 R19-1·R19-2·R19-3으로 정해졌다(위 머리 rev19 줄). T-7은 R4에서 맞추기로 정해졌다(사용자 결정).

| # | 곳 | 이 도구의 읽기 | 묻는 것 |
|---|---|---|---|
| T-8 | R19-7 (1) "바뀐 줄이 모두 기록 전용 함수 안" | `r67_g1_screen.py`의 f46b5ab..b9f5707 diff 첫 덩어리에 모듈 수준 상수 `RESUME_K1_KEY = "resume_k1"`(+ docstring 줄)이 있다. 함수 안이 아니므로 문장 그대로 (1) 위반 → E-7 관문 실패(S-11) → PS-c 사건 행 E-7 판정 불가 + 멈춤. 그 이름을 읽는 함수는 기록 전용 함수 둘뿐이다(`tool_gate.r19_7.hunks[].outside_function_lines`) | 기록 전용 함수만 읽는 모듈 상수를 (1)의 "안"으로 볼지 |
| T-9 | R19-1 판정 키 | `identity`(4.2·6 기록 대조)와 `K1_class`(7.2)는 P3 등급 항목이 아니라 남겼다 | 맞는가 |

### 6.00000000 rev18 R3b 보완 뒤 (새 작성자의 읽기, 메인 세션 확인 필요; rev19로 정해짐)

| # | 곳 | 이 도구의 읽기 | 묻는 것 |
|---|---|---|---|
| T-1 | R18-2 "그때 P3-5·P3-6·FAULT0은 이 조건으로 대신한다" | 문장 그대로 세 항목만 뺀다. 안전 종료 행은 READY가 없어서 P3-1(READY 창)·P3-4(마지막 READY 뒤 창)가 판정 불가가 되고, 그러면 `allowed_stop` 행도 판정 불가다. S-03·04의 G6-6(FAULT 0 + READY ≤ 120 s)은 실패가 된다. 그 항목들의 판정과 사유를 `safe_stop_427_9.ready_dependent_items`에 남긴다. 앞 판(SA-4 기반)은 P3-1·P3-2·P3-4·G6-6도 대신했다 | READY에 기대는 P3-1·P3-2·P3-4·G6-6도 안전 종료로 대신하는가 |
| T-2 | 427.9 조건 3·4의 창 | 부상: t_D ~ 끝 패드 법선 ≤ 0 표본(rev3 Q-14). 최소: t_D ~ 끝(명세 "크롤러 이탈 뒤 실행 끝까지"). 정지 시각 ~ 끝 부상 표본은 따로 내지 않는다 | 맞는가 |
| T-3 | 427.9 조건 5 "포화 0" | 이동 압력 ≤ 180 bar와 같은 10 Hz 제어 행에서 "신장 명령 > 0 ∧ F_cyl/A_p ≥ 210 bar"를 포화로 센다(412절 원문은 읽지 않음, 하네스판 정의는 `s9_soil_event_screen` 문서) | 412절 정의와 같은가 |
| T-4 | PS-c 기준 행(`PSC-base-FL`) | 사건이 없어(`soil_event` 블록·`soil_event_series.npz` 없음) E-1~E-7을 계산할 수 없다 → 판정 불가(R18-3 "항목 하나라도 계산할 수 없으면 판정 불가") | 기준 행을 E 판정 행으로 두는가, 기록 행으로 두는가 |
| T-5 | 426.3 가지를 Chrono 행에 읽기 | Chrono 실행은 사건 뒤에도 계속되지만 E 항목은 426.3 가지(사건 − 0.5 s ~ "≥ max(12 s, 램프 + 3 s) ∧ READY 3 s 유지", 최대 60 s) 안에서만 본다. 그래서 60 s 안에 READY로 돌아오지 않으면 E-5가 실패다. 실행 끝까지 보는 읽기와 결과가 다를 수 있다 | 가지 창 읽기가 맞는가 |
| T-6 | E-4 "창 밖" | 사건 뒤 창 밖(빠른 W 뒤, 느린 램프 + 3 s 뒤 ~ 가지 끝)만 본다(사건 전 레벨링 구간은 넣지 않음) | 맞는가 |
| T-7 | `path2_v5c` `P2_CORE_SHA` | `path2/p2_4368.py`를 바꿔 고정값과 어긋난다(`path2_v5c` 시험 1건 실패). R18-1 (다) 밖이라 고치지 않았다 | R4 하네스 도구 커밋에서 맞출지 |

### 6.0000000 rev12 뒤

- 새로 묻는 것 없음. 6.000000의 R-6(`code_state`가 없는 L2b·L1-R 행은 `code_at_launch`만 대조)은 rev12 R12-4가 열린 루프만 다뤄서 이 도구의 읽기 그대로다.
- 사실 기록: rev12판으로 저장 G-S `…_130358`(기록만, 인용 안 함)을 `gs-load --git-at-start ba2da55`로 적재(종료 0, 12행 예외 0, 입력 오류 0, 출력 sha `5d054482…`): 행 폴더는 L2b·L1-R 2행 `case_log`, SCM 10행 `batch_folder`(시각 창 대체는 쓰이지 않음). `rev11_gs_items`는 rev11판과 같고(S-12 1행 = 열린 루프 `code_at_launch` 없음), `r12_2_dirty_record_rows` 0, `r12_4_open_loop_code_state_rows` 0. `--git-at-start` 없이 돌리면 종료 2.

### 6.000000 rev11 뒤

| # | 곳 | 이 도구의 읽기 | 묻는 것 |
|---|---|---|---|
| R-6 | R11-4 4 `code_state` 없음 | level·L2b·L1-R 행의 `result.json` `code_state.git_at_start`는 "그 기록이 있는 행"에서만 대조한다. 없으면 `code_at_launch` 대조만으로 두고 S-12로 보지 않는다(저장 G-S의 L2b·L1-R 행에는 없다) | 이 읽기가 맞는가(5항 "기록이 없거나"는 `code_at_launch` 기록으로 읽음) |
| R-7 | `git_at_start` 비교 | 판정서 값은 7~40자리 16진이고, 기록 head(40자리)가 그 값으로 시작하면 같다고 본다 | 없음(기록) |

### 6.00000 rev10 뒤

| # | 곳 | 이 도구의 읽기 | 묻는 것 |
|---|---|---|---|
| R-5 | R10-1a `batch` 키는 있는데 폴더 이름이 `batch_<이름>_<YYYYmmdd_HHMMSS>` 꼴이 아님 | R10-1a는 "키가 폴더 부분과 다름"과 "키 없음 + 폴더 꼴 아님"만 불명으로 적었다. 키가 있어도 폴더로 대조할 수 없으면 "폴더 이름으로 대조"를 할 수 없으므로 불명(판정 불가)으로 둔다 | 이 읽기가 맞는가. 실제 S9 배치 폴더는 늘 그 꼴이라(`s9_batch.py`, R10-0) 본 행에서는 생기지 않을 것으로 본다 |

### 6.0000 rev9 뒤 (R-1 → R9-3, R-3 → R9-2·R9-5, R-4 → R9-2 항목 5로 정해짐)

- 새로 묻는 것 없음. R-2(비③ 태그 + `tracked_bound` = S-2)는 rev9가 다루지 않아 이 도구의 읽기 그대로다.
- 사실 기록: 저장 G-S `…_082117`은 7527fc3 이전 실행이라 SCM 행 `step_series.npz`에 `law_locked`가 없다. 이 도구로 적재하면 C-5 SCM 세 행이 R9-5 S-11 후보, C-5 밖 SCM·L1-R 일곱 행이 R9-6 입력 없음으로 셈해진다(5.2절). rev9 R9-8대로 최종 Y에서 G-S 전체를 다시 돌린 결과가 기준이다.

### 6.000 rev8 뒤 남은 것 (P-3 → R8-2, P-4 → R8-3로 정해짐. R-1·R-3·R-4는 rev9에서 정해짐)

| # | 곳 | 이 도구의 읽기 | 묻는 것 |
|---|---|---|---|
| R-1 | J11 `law_locked` −1 | 개정 6 6절은 "첫 무장 전 −1 = 잠김"만 정한다. 그 다리의 첫 무장 표본 뒤에 −1이 나오면 읽기가 정해지지 않았으므로 J11 판정 불가 + 멈춤으로 둔다 | 무장 뒤 −1이 실제로 생길 수 있는가(러너 쪽 `LAW_LOCK_UNARMED`의 뜻). 생기지 않으면 이 분기는 쓰이지 않는다 |
| R-2 | J-P3 비③ 태그 + `tracked_bound` | R8-2는 ③ 태그 행의 "다른 값 = S-2"만 적었다. 비③ 태그인데 실행 제어기가 `tracked_bound`이면 같은 이유(태그와 실행 제어기 다름, 원판 8.2 S-2)로 S-2로 둔다 | 이 대칭 읽기가 맞는가 |
| R-3 | L2b `law_locked` 형식 오류 | R8-3a 표가 L2b 형식도 정하므로 형식 오류는 SCM과 같이 판정 불가 + 멈춤으로 둔다(키 없음은 rev6 R6-B7 그대로) | 맞는가 |
| R-4 | R8-3a "1 ms" | 시간축 간격이 모두 1 ms ± 10⁻⁶ s가 아니면 형식 오류로 본다(도구 허용값, 판정 문턱 아님). 7527fc3 SCM 기록과 G-S L2b 행은 통과했다 | 없음(기록) |

### 6.00 rev6 뒤 남은 것 (rev7은 P-1·P-2를 다루지 않았다. P-3·P-4는 rev8에서 정해짐)

| # | 곳 | 이 도구의 읽기 | 묻는 것 |
|---|---|---|---|
| P-3 | J-P3 V0 행 | (정해짐: 436.8 rev8 R8-2. 판별은 태그, 두 필드는 대조. 2절 표) | — |
| P-4 | SCM C-5 J11 창 | (정해짐: 436.8 rev8 R8-3·R8-3a, Q-R8-1 = B. SCM `step_series.npz` `law_locked`. 2절 표) | — |

(아래는 rev6 뒤 표 그대로)

| # | 곳 | 이 도구의 읽기 | 묻는 것 |
|---|---|---|---|
| P-1 | J11 창 끝 재계산 | 다리별 발령 명령(`r8_series` `issued_u`)이 0이 아닌 값 뒤 처음 0인 제어 시각 t_s에서 구간이 열리고, u_last = 바로 앞 발령 명령, t_w = t_s + τ_v ln(max(\|u_last\|, ε)/ε) + t_c + T(`two_pressure.settings`의 `lock_window_valve_tau_s`·`lock_window_eps_m_s`·`lock_window_closing_delay_s`; 감시기 docstring의 10.4 ② 식). 로그 항목과 `t_start_s`(반 주기 안)로 짝짓고 `window_end_s`와 10⁻¹² s 대조, 어긋나면 S-11 | t_s·u_last의 기준(발령 명령인지 작용 명령인지)이 맞는가. 맞지 않으면 실제 대체 다리가 있는 첫 행에서 S-11로 드러난다 |
| P-2 | PS-c | E-1~E-7 미구현(R5-B4 순서: PS-c 행이 정해지면 G-S 1행으로 열 확인 → 본 행 전 구현·sha 고정) | 없음(순서대로 진행) |

### 6.0 rev4 뒤 남은 것 (rev5·rev6에서 정해짐: M-1 → R5-B1, M-2 → R5-B2, M-3 → R5-B3, M-4 → R5-B4)

| # | 곳 | 이 도구의 읽기 | 묻는 것 |
|---|---|---|---|
| M-1 | J11 창 끝 | `fallback_lock_log` 항목에서 `leg`와 이름에 `window_end`가 든 키를 읽는다. L2b·L1-R은 `settings.start_t_s`를 더해 절대 시각으로 본다(사건과 같은 상대 시각으로 가정). 키가 없으면 판정 불가 | 로그 항목의 필드 이름과 시각 기준. 비대체 다리의 n_late(기록)는 창 끝 식이 규칙에 없어 계산하지 않았다 |
| M-2 | D2 사유 | 사건 `WARN_ROD_PRESSURE_FALLBACK:<leg>:...`의 세 번째 이후 토막에 `D2`가 있으면 D2 대체로 센다 | 사유가 사건 이름에 어떻게 적히는가 |
| M-3 | J11 LS 행 | n_late > 0은 모두 H-7 멈춤으로 둔다 | 원판 65행 "LS 행은 L-e"를 C-5 LS 행에 적용하는가 |
| M-4 | PS-c | E-1~E-7 미구현 | H-2가 PS-c를 넣으면 만든다(형식 확인 필요: `soil_event_series.npz` 열, 연구 A 판정 함수 호출 꼴) |

### 6.1 rev3 뒤 새로 생긴 것 (rev4에서 정해짐: N-1·N-2 → R4-A2, N-4 → R4-A3)

| # | 곳 | 사실 | 묻는 것 |
|---|---|---|---|
| N-1 | C-5 재집계 입력 | G-S L2b 행 `result.json`의 키 이름 검색(T4·T5·J11·J-P3·D2·`lock_log`·`records` 등)에서 항목별 T4·T5·J-P3·D2 결과 키가 없었다(`controller_meta.two_pressure.fallback_lock_log`, `review_record.d2_violation_start_ratio`, `v5_hydraulics.records`만 있음). 본 행에도 없으면 C-5 재집계 항목은 모두 판정 불가다 | 재집계할 항목별 결과가 `result.json`의 어느 키에 쓰이는가(또는 어느 기록 파일인가). 정해지면 `REAGG_ALIASES`에 출처를 고정한다 |
| N-2 | PS-c 재집계 입력 | E-k 키가 `result.json`에 있는지 확인하지 못했다(PS-c G-S 행 없음) | N-1과 같음 |
| N-3 | C-6·C-7 `analyse` | G-S 열린 루프 행(10 s)에서는 이탈이 없어 `analyse`가 예외로 끝났다(그 함수의 `first_run`이 None). 본 행 길이에서는 나지 않을 것으로 본다 | 없음(기록) |
| N-4 | C-6·C-7 `criteria_id` | G-S에는 `C-6`만 있다. C-7 행의 값(`C-7` / `C-7a` / `C-7b`)을 모두 받는다 | cad 행 생성기의 실제 값 |

### 6.2 rev3 R3-G에서 정해진 앞 질문 (Q-1~Q-18, 기록)

모두 rev3 R3-G1~G13·R3-G10 표대로 반영했다(Q-1 → G1 재집계, Q-2 → G2, Q-3 → G3 허용, Q-4 → G4, Q-5 → G5, Q-6 → G6 F_min + 5 kN, Q-7 → G7 FLAG, Q-8 → G8 F_min, Q-9 → G9, Q-10~Q-14·Q-17 → G10, Q-15 → G11, Q-16 → G12 조건 6, Q-18 → G13). 아래는 원 질문 표(기록)다.

| # | 곳 | 이 도구의 읽기 | 묻는 것 |
|---|---|---|---|
| Q-1 | C-5 9.1 경로 2 | T4·T5·J-P3·D2는 만들지 않아 C-5 행 전부 판정 불가 | C-5 경로 2의 범위(감시기 독립 재구현을 누가 하는가, 또는 경로 2를 t_lift·H-9·전이 기록으로 좁히는가). 그대로면 C-5는 S-13에 준해 판정 불가 |
| Q-2 | RV1-10 h | L2b·L1-R의 1 ms 참 F_cyl·크롤러·자세는 `r8_series`·`s8_series`(10 Hz)에 없어 `pads.npz`(`F_cyl_min_interval`, `F_cyl`, `crawler_normal_N`, `body_quat_wxyz`, `N`, `law_locked`)와 `record/record.npz`(L1-R 자세·크롤러 10 Hz)를 읽었다 | 이 두 파일을 경로 2 입력으로 인정하는가 |
| Q-3 | d1 11 S-03·04 | H-S-A처럼 `stroke_limited_stop` 허용 | S-03·04 행에 허용이 적혀 있지 않다. 허용인가 |
| Q-4 | d1 11 S-03·04 READY | P3-6(90 s)은 기록, G6-6에서 READY ≤ 120 s 판정 | rev1이 H-S-A G1 평지를 90 s로 정했는데 Chrono S-03·04에도 적용하는가 |
| Q-5 | D8 "이륙" | L2b·L1-R·SCM 모두 rev6 5 t_lift(단계 조건 + 크롤러 ≤ 0 첫 표본) | 명세 3 "법선력 합이 0이 된 첫 시각"·P3 t_D 중 무엇인가 |
| Q-6 | R40-2 | 느린 성분 문턱 14.41 kN(문자 그대로), `hold` 행은 판정 불가 | 현 F_min 기준(F_min + 5 kN = 14.415 kN)인가, `hold` 행의 등급은 무엇인가 |
| Q-7 | 433.6 `window_short` | 통과로 세지 않으므로 판정 불가 | d1 3절 "FLAG는 pass"와 충돌. 등급은 무엇인가 |
| Q-8 | 377 강등 문턱 | ≥ F_min(377)과 ≥ 14.4 kN(17279행 "424.11.2와 같음")이 갈리면 판정 불가 | 어느 문턱인가 |
| Q-9 | P3-4 장착 몫 | P3-4는 창 최대 ≤ 0.2°(장착 몫을 더하지 않음, 284.1 `sensor_allowance_left_deg` 식으로 읽음). D8 끝 자세는 + 0.02° | 맞는가 |
| Q-10 | P3-8 구간 | min(첫 LOC(취소된 것 포함), 토양 모드 시작) 전. 둘 다 없으면 실행 전체 | 맞는가 |
| Q-11 | 재접촉 지속 | (마지막 표본 − 첫 표본 + 1 ms) | 표본 수 × 1 ms로 맞는가 |
| Q-12 | P3-2 순서 | DONE이 없으면 순서 조항 참 | 맞는가 |
| Q-13 | 이동 압력 | 작용 명령(발령 `issued_u`가 다음 주기를 구동) \|u\| > 10⁻⁶을 이동으로, 압력 = F_cyl/A_p. 밸브 지연 꼬리는 이동으로 세지 않는다. L2b `head_pressure`·`law_locked`는 쓰지 않는다 | 맞는가 |
| Q-14 | 부상 | t_D 뒤 패드 법선 ≤ 0 표본(SCM `scm_pad_normal_N`, L2b `N`) | 부상 정의 원문 |
| Q-15 | 배정 | C-8은 배정 밖이지만 rev2 R2-5·R2-6을 받아 `p2_b_c8.py`로 더했다. C-6·C-7(R2-4)은 9.1이 경로 2를 `openloop_compare.py analyse`로 정해 만들지 않았다 | C-8을 이 도구로 낼지, C-6·C-7 경로 2 담당 |
| Q-16 | 424.11.2 "조건 1~6" | 424.8.1 다섯 조건만 구현 | 6번째 조건 원문 |
| Q-17 | P3-2 하중 조항 | 최종 LOC 주기만 본다(취소된 LOC는 LOC로 보지 않음, 424.8.1) | 원 표 "크롤러가 하중을 진 동안 LOC 0"을 취소된 LOC에도 적용하는가 |
| Q-18 | rev2 R2-5 W | `p3b.weight_N`을 읽는다(판정 블록 안의 키 1개). `mass_scale.judgement_weights.weight_N`과 다르면 기록 | 판정 블록 키 1개 읽기를 독립성 위반으로 보지 않는가 |
