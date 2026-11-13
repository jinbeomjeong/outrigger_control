# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev8 (T4h 없는 실행의 태그 재계산 대조·J-P3 적용 범위·SCM J11 입력·도구 커밋 순서, 결과 전, 봉인)

- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev8.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev8_seal_candidate_draft.md`와 1·3·5·9행만 다르다.
- 원판 `v5_resume_4368_rules.md`(sha256 `9019b405…`), rev1(`d9094fda…`), rev2(`497e4614…`), rev3(`dad8dfa6…`), rev4(`7ea87a30…`), rev5(`452a8436…`), rev6(`809e5639…`), rev7(`e81f7d31…`)은 고치지 않는다. 이 판은 rev7(sha256 `e81f7d31779b0d69a140c9d90aa4684f3c9299e84aec6af06b13d48d58631502`, 봉인 커밋 `292f9d2`) 위에 쌓인다. 전체 sha256은 각 판의 `.sha256`에 있다. 봉인 뒤 이 판과 앞 판이 다르면 이 판이 맞다. 이 판이 말하지 않는 것은 앞 판 그대로다.
- **시점: 436.8 본 실행 결과가 없을 때(봉인 2026-11-13 10:47:09 +09:00, 봉인 커밋 292f9d2).** 436.8 본 묶음과 0단계 T-3K는 한 줄·한 행도 돌지 않았다. 있는 것은 G-S 실행뿐이다(R8-0).
- 작성: control-expert, 2026-11-13. 기준 master `292f9d2`(rev7 봉인 커밋). 계기는 두 가지다.
  - 사용자 결정 10(2026-11-13, 비권고안 채택): rev7 R7-1a는 T4h 기록이 있는 실행만 대조하므로 격자(H-9) job 기록과 `t4h_file`이 없는 r79 실행이 `not_compared`로만 남는다. T4h가 없는 실행은 기록된 C2 설정에서 태그를 다시 계산해 대조한다(R8-1)
  - 두 경로 작성자들의 rev8 후보 메모 P-3(V0 SCM 행의 J-P3)·P-4(SCM C-5 행의 J11 입력)(R8-2·R8-3)
- **봉인본이다.** 사용자 결정이 필요한 새 항목은 없었고, 사용자 결정 10과 Q-R8-1 = B(2026-11-13)는 R8-1~R8-4와 R8-9 결정 표에 반영했다.
- **바꾸지 않는 것**: 숫자 문턱, 등급과 우선순위, 멈춤 조건의 뜻, 묶음 범위와 행 목록, 사전 예측 값, 두 경로 요건(원판 9.2), rev1~rev7의 정의(R8-4가 바꾸는 rev7 R7-7의 순서·`git_at_start` 문장만 예외). 이 판은 새 숫자를 쓰지 않는다.

## R8-0. 결과 전 근거와 공개

- 2026-11-13 확인: 436.8 본 출력이 없다. G-S는 `b1ddeae`에서 한 번 돌았고, `e860578`에서 시작한 재실행은 중단했다(rev7 R7-7). rev7 도구 커밋 `4a8a092`(worktree, 병합 안 함)는 R7-1a 대조와 rev7 봉인 확인을 넣었다. cad-expert 커밋 `7527fc3`(부모 `292f9d2`, 병합 안 함)은 SCM 행에 1 ms `law_locked` 기록을 넣었다(R8-3, 메인 세션 전달 사실).
- 읽은 것:
  - 규칙: 원판~rev7, v5 기준 개정 6 6절·개정 8 3.1·3.2절·개정 9 3.1·3.2절·개정 11 1절·개정 12 2.1(판정 행), `las_k1_rules_adopt.md` 9.2절, `stage3_judgement.md` 3절(J11 대상 행)
  - 코드(읽기만): `03_src/outrigger_sim/hydraulics/v5_options.py`(`HydraulicOptions` 기록 168~172·218행, `controller_tag`, `with_switch_tags`, `is_liftoff_slow_on`, `is_order_gate_on`, `is_touch_creep_on`, `is_extend_start_tag`), 커밋 `4a8a092`의 메시지와 파일 목록
  - 기록(필드 이름과 태그·전환 값만, 판정 값은 읽지 않음):
    - `06_analysis/02_control/verif_matrix/v5_resume_4368/gs_harness_b1ddeae/`의 `h9_grid_r67_main.json`, `h8_seedext_VB.json`, `h6_dg3_v4on.json`, `h7_dg3_off.json`
    - `c4e0ed9` 재실행(scratchpad `pe_tagfix/runs/`)의 `grid/grid.json`, `seedext/result.json`, `h6/result.json`, `h7/result.json`
    - Chrono G-S 배치 `07_results/S9/batch_V5-RESUME-K1-GS_20261113_082117`의 행 폴더 파일 목록, `batch.json` 행 argv, `result.json` 키 경로(`args`, `c2_setup.expect_controller`, `v5_hydraulics`, `controller_meta.two_pressure`), npz 배열 이름
  - 경로 2 폴더는 열지 않았다.
- 이 작성자는 경로 2 작성자가 아니다(rev2 R2-0).

## R8-1. T4h 없는 실행의 태그 재계산 대조 (rev7 R7-1a 보충, 사용자 결정 10)

### R8-1a. 대상

- r79 계열(H-6·H-7·H-8) 결과 항목 가운데 `t4h_file` 키가 없는 것, 그리고 격자(H-9) job 기록(`results[]` 항목) 전부다.
- `t4h_file`이 있는 실행은 rev7 R7-1a(T4h meta 대조)로 한다. 기록이 가리키는 T4h 파일을 찾지 못하면 S-2이고, 재계산으로 대신하지 않는다(기록이 있다고 한 쪽이 없으므로 R7-1a의 "한쪽에만").

### R8-1b. 입력 필드 (기록 사실, 2026-11-13 저장 기록에서 확인)

| 입력 | r79 결과 항목 | 격자 job 기록 | 읽기 |
|---|---|---|---|
| ③ | `hydraulic_options.extend_start_tracked` | `results[].hydraulic_options.extend_start_tracked` | 키가 있고 참 = ③ 켬. 블록이 있는데 키가 없음 = ③ 끔(`HydraulicOptions` 기록은 ③ 켬일 때만 이 키를 남긴다, `v5_options.py` 168~172행, 읽을 때도 없음 = 끔, 218행). `hydraulic_options` 블록이 없으면 재계산 불가 |
| ③ 대조 | `controller_settings["two_pressure.extend_start_rule"]`(점 이름 키 하나) | 없음 | 키가 있으면 값 `tracked_bound` ⇔ ③ 켬이어야 한다. 다르면 S-2. 키가 없으면 이 대조는 하지 않는다(dg3 기록에만 있다) |
| C2 실행 | `resume_k1.applicable` | `results[].resume_k1.applicable` | 참이어야 한다. 거짓이거나 없으면 재계산 불가 |
| LAS-b | `resume_k1.liftoff_approach_slow.settings.enable` | `results[].resume_k1.liftoff_approach_slow.settings.enable` | bool. 없으면 재계산 불가 |
| K1 관문 | `resume_k1.slope_clearance_margin.settings.flat_soil_margin_order_gate` | `results[].resume_k1.slope_clearance_margin.settings.flat_soil_margin_order_gate` | bool. 없으면 재계산 불가 |
| 대조 대상 | 최상위 `controller_tag` | `results[].controller_tag` | 키가 없으면 "태그 없음" |

- 격자 job의 각 run(`results[].runs[]`)도 자기 `resume_k1` 블록을 가진다(rev1 RV1-3.2 "격자 줄의 태그 확인은 각 run의 `resume_k1` 블록"). 각 run의 LAS-b·K1 두 값은 그 job 기록의 두 값과 같아야 한다. 다르면 S-2다. run의 블록이 없으면 재계산 불가다.
- `controller_settings`의 그 밖 키(`lift_stroke_guard.*`, `slope_clearance_margin.enable` 등)는 태그를 정하지 않으므로 재계산에 쓰지 않는다.

### R8-1c. 재계산 규칙 (봉인된 태그 정의)

1. 바탕: ③ 켬이면 `final_C4G2_P3`(v5 기준 개정 8 3.1 "③ revision 4 … 태그 `final_C4G2_P3`"). ③ 끔이면 바탕 없음(러너 태그 `final_C4G2`, v5 기록은 키를 남기지 않음, 개정 8 3.1 "기준 `final_C4G2`").
2. LAS-b 켬이면 `_LAS`를 붙인다. 바탕이 없으면 `final_C4G2_LAS`다(개정 11 1절 #1 `final_C4G2_LAS` = `final_C4G2` + LAS-b, #2 `final_C4G2_P3_LAS`).
3. K1 관문 켬이면 `_LAS` 다음에 `_K1`을 붙인다(`las_k1_rules_adopt.md` 9.2: "LAS-b 접미사 `_LAS` 다음에 순서 관문 접미사 `_K1`을 붙인다", `final_C4G2_LAS_K1`·`final_C4G2_P3_LAS_K1`).
4. `_TCL`(K-2 TOUCH 크리프 래치)은 만들지 않는다. 위 기록에 TCL 켬을 나타내는 필드가 없고, TCL은 원판 4.2 금지 토큰이다. 기록 태그에 `_TCL`이 있으면 재계산 태그와 달라 S-2가 되고, 4.2 확인(S-3)도 따로 걸린다.
5. 셋 다 끔이고 ③도 끔이면 재계산 태그는 "태그 없음"이다.

- 436.8 행에서 나오는 값: ③ 켬 + LAS-b + K1 = `final_C4G2_P3_LAS_K1`(H-6, H-8 VB, 격자 VB), ③ 끔 + LAS-b + K1 = `final_C4G2_LAS_K1`(H-7, H-8 V0). 원판 4.1·rev1 RV1-3.2의 기대 태그와 같다.
- 이 규칙은 코드의 `v5_options.controller_tag(options, config)`(T4h meta와 `c4e0ed9` 뒤 최상위 태그를 만드는 함수)와 같은 결과를 낸다. 정의의 원본은 위 봉인 문장이다.

### R8-1d. 대조와 멈춤

- 재계산 태그와 최상위 `controller_tag`가 같으면(둘 다 "태그 없음"인 경우 포함) 일치다.
- 다르거나 한쪽에만 있으면 그 묶음은 원판 8.2 S-2로 멈춘다(사용자 결정 10).
- **재계산 불가**(R8-1b의 "재계산 불가" 경우)도 S-2로 멈춘다. G-S에서는 원판 11.2의 키 있음 실패(S-11)로도 센다.
  - 근거: 태그 확인(원판 4.1)은 등급 항목이 아니라 묶음을 시작·판정하기 위한 멈춤 조건이다. 그래서 원판 9.3의 `판정 불가`(등급 항목의 결측)로 넘기지 않는다. 재계산 불가는 "기록 태그는 있는데 설정 쪽 값이 없음"이므로 rev7 R7-1a와 사용자 결정 10의 "한쪽에만 있으면 S-2"에 해당한다. 필요한 키는 모두 원판 4.2 기록 확인 키(`resume_k1.*`)와 v5 기록 칸이라 정상 실행에서는 빠지지 않는다.
- 대조는 경로 1 도구가 한다(`resume4368_judge`의 G-S·기록 확인 하위 명령, rev7 R7-1a와 같은 곳). 대조 방법(T4h meta / 재계산), 대조한 수, 어긋난 수, 재계산 불가 수를 묶음마다 판정서 13절 3항에 적는다. `not_compared`로 남는 실행은 없어야 한다.

### R8-1e. 확인 사실 (저장 기록에 이 규칙을 적용, 2026-11-13, 이 작성자 계산)

| 기록 | 대조 방법 | 기록 태그 | 재계산 | 결과 |
|---|---|---|---|---|
| `b1ddeae` G-S 격자 job 1개(run 6개, LAS-b·K1 값 job과 같음) | 재계산 | `final_C4G2_P3` | `final_C4G2_P3_LAS_K1` | 다름(R7-1b의 기록 결함) |
| `b1ddeae` G-S H-8 seedext 1개(`t4h_file` 없음) | 재계산 | `final_C4G2_P3` | `final_C4G2_P3_LAS_K1` | 다름(같은 결함) |
| `c4e0ed9` 재실행 격자 job 1개(run 6개 같음) | 재계산 | `final_C4G2_P3_LAS_K1` | 같음 | 일치 |
| `c4e0ed9` 재실행 seedext·H-6·H-7 각 1개 | (T4h 있음, R7-1a) 참고로 재계산도 함 | `final_C4G2_P3_LAS_K1` / `final_C4G2_P3_LAS_K1` / `final_C4G2_LAS_K1` | 같음 | 일치. H-6·H-7은 `controller_settings` `two_pressure.extend_start_rule`(`tracked_bound` / `constant`)도 ③과 맞음 |

- 결정 필요: **아니오**(사용자 결정 10. 재계산 불가 처리는 R7-1a 문장의 적용).

## R8-2. J-P3 적용 범위와 ③ 판별 (경로 2 메모 P-3)

- **정의**: J-P3은 ③ 켬 행에만 적용한다(rev3 R3-C8 "J-P3은 ③ 켬(`is_extend_start_tag`) 줄에만 적용", v5 기준 개정 8 3.2 "VB·LS 모든 실행"). ③ 판별은 원판 4.1대로 그 행의 태그로만 한다. Chrono 행의 태그는 `--expect-controller` 값이고 `c2_setup.expect_controller`의 확인이 참이어야 한다(원판 6절, rev1 RV1-10 a).
  - 태그가 ③ 켬이 아닌 행(V0·V0v·S6SEED 등)의 J-P3은 **해당 없음**이다. `controller_meta.two_pressure.settings.extend_start_rule` 키가 없어도 결측으로 세지 않는다.
  - 태그가 ③ 켬인 행은 `controller_meta.two_pressure.settings.extend_start_rule` = `tracked_bound`여야 한다. 키가 없으면 그 행의 J-P3은 `판정 불가`(원판 9.3)다. 다른 값이면 태그와 실행 제어기가 달라 S-2다.
- **③ 요청 기록과의 대조**(경로 2 메모 P-3의 두 필드): 행 argv의 `--extend-start-tracked` 유무와, 있으면 `v5_hydraulics.hydraulic_options.extend_start_tracked`(키 없음 = 끔, R8-1b와 같은 기록 규칙)는 태그의 ③ 판별과 같아야 한다. 다르면 S-2다. `v5_hydraulics` 블록이 없는 행(2026-11-13 G-S에서 V0·S6SEED 행)은 argv만 대조한다.
- 열린 루프 C-6·C-7(제어기 없음, 원판 4.1 "태그 검사 대상 아님")은 이 절의 대상이 아니다.
- 메모와 같은 점·다른 점: 메모는 argv와 `hydraulic_options` 둘 다 끔이면 해당 없음이라고 했다. 이 판은 판별을 태그로 하고 두 필드를 대조에 쓴다. 정상 행에서 두 읽기는 같은 답을 낸다. 둘이 어긋나는 행은 이 판에서 S-2로 멈춘다. ③을 요청한 행에 키가 없으면 판정 불가라는 메모의 문장은 그대로 들어 있다.
- 결정 필요: **아니오**(R3-C8·원판 4.1·9.3의 적용).

## R8-3. SCM C-5 행의 J11 입력 (경로 2 메모 P-4, 사용자 결정 Q-R8-1 = B)

- 사실:
  - 2026-11-13 G-S `…_082117`의 SCM `run_S9.py level` 행 폴더에는 `pads.npz`가 없었다. `step_series.npz`·`record.npz`·`r8_series.npz`·`controller_commands.npz`에도 1 ms 법칙 잠금 상태가 없었다.
  - v5 기준 개정 6 6절의 J11은 플랜트 잠금 사건을 1 ms `law_locked` 전이로 정하고, $n_{late}$는 그 잠금이 제어기 창 끝보다 늦은 구간 수다(봉인본 18행). rev6 R6-B7은 대체 다리를 정하는 방법과 열린 구간의 창 끝 계산만 정했으므로, 잠금 상태 기록이 없으면 $n_{late}$가 나오지 않는다.
  - 그래서 사용자 결정 Q-R8-1 = B(2026-11-13)로 cad-expert가 SCM 행에 1 ms 다리별 `law_locked` 기록을 넣었다(커밋 `7527fc3`, 부모 `292f9d2`, 기록 전용). 수정 전후 SCM 1행에서 기존 npz 키, 명령 기록, `controller_commands`·`record`·`r8_series` 등의 파일 sha256이 모두 같고, argv와 manifest(작업본 `7b4ae7c4…`, `table_sha256` `eef5129f…`)도 같다(메인 세션 전달).
- **정의**:
  1. SCM C-5 행의 J11은 개정 6 6절 그대로 판정한다. 플랜트 잠금 사건 = `step_series.npz` `law_locked`의 다리별 0→1, 1→0 전이다. 첫 무장 전(−1)은 잠김으로 본다(개정 6 6절).
  2. 창 끝은 명령 기록에서 다시 계산한다. 실제 대체 다리는 rev6 R6-B7대로 `fallback_lock_log`의 다리 ∪ 사건 `WARN_ROD_PRESSURE_FALLBACK:<다리>`의 다리다. 로그 항목과의 ≤ 10⁻¹² s 대조, 열린 구간 처리도 R6-B7 그대로다.
  3. 판정·`unjudged` 규칙은 개정 2 D-1, 대체 다리 $n_{late}$ > 0은 H-7(LS 행은 L-e), 모든 다리 $n_{late}$는 기록이다(개정 6 6절, rev5 R5-B3).
  4. L2b 행은 `pads.npz` `law_locked`로 같은 정의를 쓴다(개정 6 6절, rev4 R4-A2, rev6 R6-B7 그대로).
- **기록이 없거나 형식이 틀릴 때(권고로 정함)**:
  - G-S(원판 11.2): 원판 8.2 S-11(G-S 실패)이다. 경로 1 `gs-check`가 level 행마다 이 키의 있음과 형식을 본다(`series_keys_missing`·`series_key_problems`).
  - 본 실행: 그 행의 J11은 원판 9.3대로 `판정 불가`다. 대체 다리 $n_{late}$ > 0(H-7·L-e 멈춤)을 확인할 수 없으므로 그 묶음은 멈추고 묻는다.
  - 근거: 키 있음은 G-S가 보장하는 항목이다(원판 11.2). 본 실행에서 빠지면 그것은 기록 결함이다. 그리고 멈춤 조건을 확인하지 못한 행을 통과로 둘 수 없다.
  - "형식이 틀림"은 R8-3a 표의 모양·자료형·값 집합·시간축과 다른 것이다.

### R8-3a. 이름 대응표 (J11 잠금 상태, 경로 2는 이 이름·형식만 쓴다)

| 엔진·행 | 파일·키 | 형식 | 시간축 | 값 |
|---|---|---|---|---|
| SCM `run_S9.py level` | `<행>/step_series.npz` `law_locked` | [N, 4] int8, 다리 순서 FL·FR·RL·RR | 같은 파일의 `t_s`(Chrono 절대 시각, 1 ms, 기존 키와 같은 행) | 1 잠김, 0 이동(꼬리), −1 미무장 |
| L2b `run_S8C.py` | `<행>/pads.npz` `law_locked` | [N, 4] int8, 다리 순서 FL·FR·RL·RR | 같은 파일의 `t`(Chrono 절대 시각, 1 ms) | 같음 |

- 두 키는 같은 함수(`s8_plant_adapter.law_lock_state`, 같은 `L2bForceActuator` 객체의 `rod_side.locked`)로 만든다. SCM 행 `result.json`의 `step_series.law_locked_rule`에 정의 문장이 들어간다.
- 시각 원점은 rev6 R6-1·rev5 R5-B1과 같다(`fallback_lock_log`·제어기 사건과 같은 Chrono 시각).
- 결정 필요: **아니오**(사용자 결정 Q-R8-1 = B. 결측·형식 오류 처리는 원판 11.2·9.3의 적용).

## R8-4. 수정 순서와 `git_at_start` (rev7 R7-7의 순서·`git_at_start` 문장을 바꾼다)

- **순서**:
  1. 이 판을 봉인한다.
  2. 도구 커밋을 넣는다. 한 커밋(이하 "도구 커밋 Y")에 다음을 모두 담는다. `4a8a092`와 `7527fc3`은 따로 병합하지 않고 Y에 흡수한다.
     - 러너: `7527fc3`(SCM 행 `law_locked` 기록, 기록 전용).
     - 경로 1: `4a8a092`(rev7 R7-1a T4h meta 대조, rev7 봉인 확인), R8-1 재계산 대조, R8-3 SCM J11 읽기, rev8 봉인 확인.
     - 경로 2: rev8 봉인 확인, Chrono 경로 2의 SCM J11 읽기(R8-3a), `path2_v5c`의 `P2_CORE_SHA` 고정값 갱신. 경로 2 작성자가 고치고, 원판 9.2의 독립성 요건은 그대로다.
     - 봉인 확인 목록(`chrono_rows_judge_4368.py` `RULES_SEALS`, `judge4368_common.py`, `resume4368_judge` 봉인 목록, 경로 2 도구의 봉인 목록)에 rev7·rev8 파일과 그 봉인 sha를 둔다. 도구는 파일 sha256이 봉인 sha와 `.sha256` 기록 둘 다와 같은지 보고, 다르거나 없으면 원판 8.2 S-1이다.
  3. 도구 커밋 Y에서 G-S 전체를 다시 돈다.
- **도구 커밋 Y에서 이 판 봉인 뒤 G-S 전체를 다시 돌린 것을 원판 11.2 충족으로 본다.**
  - Y의 sha와 G-S 배치(하네스 출력 경로, Chrono 배치 폴더)는 판정서에 적는다.
  - `git_at_start`는 Y이거나, Y 위에 판정서·감사 기록만 더한 커밋이다. `git diff --stat Y..GIT_AT_START`로 확인하고 판정서에 적는다.
  - 그 밖의 파일이 바뀌면 원판 11.2대로 바뀐 커밋에서 G-S를 다시 돈다.
  - 기록 추가 이전의 G-S는 기록만 하고 11.2 충족에 쓰지 않는다: `b1ddeae`, `e860578`(중단), Chrono G-S `…_082117`·`…_094502`(SCM 행에 `law_locked`가 없어 `gs-check` errors가 나는 것이 예상된 결과), `4a8a092`·`7527fc3`에서 돈 G-S가 있으면 그것도 같다.
  - G-S 결과로 적을 것: rev7 R7-7의 항목에 더해 R8-1 대조 결과(방법별 수, 어긋난 수, 재계산 불가 수), rev8 봉인 확인 결과, R8-2 S-2 수와 J-P3 해당 없음 수, R8-3 `law_locked` 키 확인 결과(행 수, `series_keys_missing`·`series_key_problems` 수).
- 결정 필요: **아니오**(사용자 결정 10·Q-R8-1과 메인 세션 지시의 순서).

## R8-9. 결정 표

| 항목 | 권고·정의 | 결정 필요 |
|---|---|---|
| R8-1 태그 재계산 대조 | T4h 없는 r79·격자 job: 기록된 ③·LAS-b·K1로 봉인 태그 규칙에 따라 재계산, 다르거나 한쪽만 = S-2, 재계산 불가 = S-2(G-S는 S-11도) | 결정됨: 사용자 결정 10(2026-11-13) |
| R8-2 J-P3 범위 | ③ 판별은 태그(4.1, R3-C8), 비③ 행은 해당 없음, ③ 행 키 없음 = 판정 불가, 요청 기록과 다르면 S-2 | 아니오 |
| R8-3 SCM J11 | 개정 6 6절 그대로 `step_series.npz` `law_locked` 1 ms 전이(−1 = 잠김), 창 끝·대체 다리는 R6-B7. 키 없음·형식 오류: G-S = S-11, 본 실행 = 판정 불가 + 멈춤 | 결정됨: 사용자 결정 Q-R8-1 = B(2026-11-13). 결측 처리는 권고로 정함 |
| R8-3a 이름 대응표 | SCM `step_series.npz` `law_locked`, L2b `pads.npz` `law_locked`, [N, 4] int8 | 아니오 |
| R8-4 순서 | rev8 봉인 → 도구 커밋 Y(`7527fc3`·`4a8a092` 흡수, 경로 1 재계산·T4h 대조·SCM J11 읽기·봉인 확인, 경로 2 봉인 확인·SCM J11 읽기·`P2_CORE_SHA`) → Y에서 G-S 전체, `git_at_start` = Y(+ 판정서·감사 기록만) | 아니오 |

- 고르지 않은 안(Q-R8-1, 기록): A = 대체 다리가 없으면 J11 해당 없음, 있으면 판정 불가 + 멈춤(코드 변경 없음, 대체 다리가 없는 행의 $n_{late}$는 기록 불가). C = SCM 행 J11을 모두 `판정 불가`로 두고 C-5 등급은 L2b 행으로만 낸다는 공개.

### 결과 전 사용자 결정 기록

| 날짜 | # | 결정 | 반영 |
|---|---|---|---|
| 2026-11-13 | 10 | T4h 없는 실행은 기록된 C2 설정에서 태그를 다시 계산해 최상위 `controller_tag`와 대조, 다르거나 한쪽만이면 S-2. rev8에 규칙을 넣고 경로 1 도구에 구현(비권고안 채택) | R8-1, R8-4 |
| 2026-11-13 | Q-R8-1 | B: 러너가 SCM 행에 1 ms 다리별 `law_locked`를 기록 전용으로 더하고 개정 6 6절 그대로 판정(권고 A와 다름) | R8-3, R8-3a, R8-4 |

## 봉인 때 바꿀 머리 줄 (메인 세션)

1. 파일 이름: `v5_resume_4368_rules_rev8_seal_candidate_draft.md` → `v5_resume_4368_rules_rev8.md`(같은 폴더). 초안 파일은 지우지 않고 그대로 둔다.
2. 1행을 다음으로 바꾼다:
   `# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev8 (T4h 없는 실행의 태그 재계산 대조·J-P3 적용 범위·SCM J11 입력·도구 커밋 순서, 결과 전, 봉인)`
3. 3행(첫 글머리 "상태")을 다음으로 바꾼다:
   `- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev8.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev8_seal_candidate_draft.md`와 1·3·5·9행만 다르다.`
4. 5행("시점")에서 `SEAL_TIME`(예: 2026-11-13 10:00:00 +09:00)과 `SEAL_COMMIT`(봉인 파일을 넣는 커밋의 앞 커밋, 7자리)을 값으로 바꾼다. 이 두 이름 말고는 5행을 바꾸지 않는다.
5. 9행("봉인 준비판이다")을 다음으로 바꾼다:
   `- **봉인본이다.** 사용자 결정이 필요한 새 항목은 없었고, 사용자 결정 10과 Q-R8-1 = B(2026-11-13)는 R8-1~R8-4와 R8-9 결정 표에 반영했다.`
6. 바꾼 뒤 sha256을 계산해 `v5_resume_4368_rules_rev8.sha256`에 `<sha256>  v5_resume_4368_rules_rev8.md  sealed <SEAL_TIME 값> (436.8 rev8: on top of rev7; runs without a T4h record (grid job records, r79 results without t4h_file) recompute the tag from the recorded switches (hydraulic_options extend_start_tracked, resume_k1 LAS-b enable and K1 order gate) by the sealed tag rules and compare with the top-level controller_tag, different / one side / not computable = S-2; J-P3 scope by the tag (non-extend-start rows not applicable, missing extend_start_rule on extend-start rows not judgeable, request record mismatch S-2); SCM C-5 J11 by revision 6 section 6 on the new 1 ms step_series.npz law_locked (record only, runner commit 7527fc3, Q-R8-1 = B), missing or malformed = G-S S-11 / main run not judgeable and stop, name table for SCM and L2b law_locked; order rev8 seal -> tool commit Y (7527fc3 and 4a8a092 absorbed, path 1 recompute / T4h / SCM J11 / seal checks, path 2 seal check / SCM J11 / P2_CORE_SHA) -> full G-S at Y = 11.2, git_at_start = Y (+ judgement and audit records only), earlier G-S record only; user decisions 10 and Q-R8-1 2026-11-13; thresholds and grades unchanged)` 한 줄로 쓴다.
7. `.gitattributes`에 다음을 더한다:
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev8.md -text`
   - `…/v5_resume_4368_rules_rev8.sha256 -text`
   - `…/v5_resume_4368_rules_rev8_seal_candidate_draft.md -text`
8. `tools/verif/seal_check.py`와 `tools/verif/placeholder_scan.py`(봉인본에 `SEAL_TIME`·`SEAL_COMMIT`이 남지 않음)로 확인한 뒤 커밋한다. 봉인 뒤 이 문서를 고치지 않는다. 고칠 것이 생기면 `v5_resume_4368_rules_rev9.md`로 새로 봉인한다.
