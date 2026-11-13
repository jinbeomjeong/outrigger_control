# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev7 (기록 정의 보충: 태그 확인·첫 DONE·이름 대응표·Chrono 조건부 결측·경로 1 집계 v2·풀 마스크, 결과 전, 봉인 후보 초안)

- **상태: 봉인 후보 초안(봉인 전).** 봉인 전에는 실행·판정에 쓰지 않는다. 봉인 때 바꿀 머리 줄은 끝 절에 원문으로 적었다.
- 원판 `v5_resume_4368_rules.md`(sha256 `9019b405…`), rev1(`d9094fda…`), rev2(`497e4614…`), rev3(`dad8dfa6…`), rev4(`7ea87a30…`), rev5(`452a8436…`), rev6(`809e5639…`)는 고치지 않는다. 이 판은 rev6(sha256 `809e563971ea451aba7c9d0787c660bdcab1c495af39c513c8f158e09b4fe6c9`) 위에 쌓인다. 전체 sha256은 각 판의 `.sha256`에 있다. 봉인 뒤 이 판과 앞 판이 다르면 이 판이 맞다. 이 판이 말하지 않는 것은 앞 판 그대로다.
- **시점: 436.8 본 실행 결과가 없을 때(봉인 SEAL_TIME, 봉인 커밋 SEAL_COMMIT).** 436.8 본 묶음과 0단계 T-3K는 한 줄·한 행도 돌지 않았다. 있는 것은 G-S 실행뿐이다(R7-0).
- 작성: control-expert, 2026-11-13. 기준 master `e860578`(작성 시점 HEAD). 계기는 두 가지다.
  - `b1ddeae`에서 한 번 돈 G-S(하네스·Chrono)에서 드러난 기록 결함과 정의 빈칸: r79·격자 최상위 `controller_tag`, rev4 R4-B2 첫 DONE의 기록 모양, T-3K R-0 줄의 태그 키, Chrono 조건부 결측, Chrono 경로 1 집계의 행 폴더, 풀 마스크
  - 그에 대한 사용자 결정 9개(모두 2026-11-13, 메시지 박스)와 경로 2 이름 차이. 메인 세션 정리본 `rev7_inputs.md`(scratchpad, 추적 밖)의 제안 문안 R7-1~R7-6을 뜻을 바꾸지 않고 이 판의 문체로 옮겼다
- **봉인 준비판이다.** 사용자 결정이 필요한 새 항목은 없다(R7-9 결정 표). 사용자 결정 9개(2026-11-13)는 R7-1~R7-7에 반영했다. 이 줄은 봉인 때 바뀐다.
- **바꾸지 않는 것**: 숫자 문턱, 등급과 우선순위, 멈춤 조건의 뜻, 묶음 범위와 행 목록, 사전 예측 값, 두 경로 요건(원판 9.2), rev1~rev6의 정의(R7-2가 바꾸는 rev4 R4-B2 문장만 예외). 이 판은 결과를 보기 전에 기록 정의를 메운다.

## R7-0. 결과 전 근거와 공개

- 2026-11-13 확인: 436.8 본 출력이 없다. G-S는 `b1ddeae`에서 하네스·Chrono를 한 번 돌았다. `e860578`에서 시작한 G-S 전체 재실행은 중단했다(사용자 결정 9). G-S는 이 판의 봉인 뒤 경로 1 도구 커밋에서 다시 돈다(R7-7). 이 작성자는 G-S 출력의 값과 필드를 읽지 않았다.
- 읽은 것:
  - 규칙: 원판, rev1~rev6 전부(각 `.sha256` 기록 포함), `las_targeted_rules_rev3.md` 3절(K-2·H-T3-3), `las_targeted_rules_rev5.md` 2.2절(묶음별 기대 태그)
  - 메인 세션 정리본 `rev7_inputs.md`(사용자 결정 1~8과 제안 문안 R7-1~R7-6, 근거 사실 숫자 포함)과 사용자 결정 9(메인 세션 전달, 2026-11-13)
  - 코드(정의 확인만, 실행 안 함, master `e860578`): `06_analysis/02_control/verif_matrix/scripts/resume4368_judge.py`(`read_controller_tag`, `gs_presence`, `first_done_check`와 그 보조 함수), `04_scripts/02_chrono/chrono_rows_judge_4368.py`(`TOOL_VERSION`, `OPENLOOP_CRITERIA`, `_rigid_row_dir`, `runner_log_dir`), `04_scripts/02_chrono/v5_resume_4368_chrono_rows.py`(`gs_conditional_table`, `manifest_table_check`), `04_scripts/03_control/s8/r72_g6_screen.py`(`preloc_starts`·`preloc_flag_ok` 기록), `04_scripts/04_hydraulic/coupled/d1_runs.py`(`g6_preloc_record`), `las_t3.py`·`las_targeted.py`(`run_identity`, `line_identity`), `las_t3_judge.py`(`expected_tag`), `03_src/outrigger_sim/hostcpu.py`·`04_scripts/02_chrono/s9_batch.py`(풀 마스크), 커밋 `c4e0ed9`·`5325164`·`870d8fa`·`e237e97`의 메시지
  - `v5_resume_4368/chrono_rows_manifest.json`의 `gs_conditional_absent` 블록(키 이름·조건 문장·`table_sha256`만). 작업본 sha256 `7b4ae7c46e39f0944c5c542a367a9dec760bb121a1eca5c804e5179af725dac2`, `git show HEAD:` 본 sha256 `a2752380cf898b1360d18b9197ced682cf63176756c19d4b8b4fec47adf8c033`, 키 JSON의 sha256 = 기록된 `table_sha256`(이 작성자가 다시 계산)
  - 판정 값과 경로 2 폴더(`v5_resume_4368/path2*`)는 읽지 않았다.
- 이 작성자는 경로 2 작성자가 아니다(rev2 R2-0).

## R7-1. 태그 확인 (원판 4.1·8.2 S-2 보충, 사용자 결정 1·5)

### R7-1a. r79 계열과 격자의 최상위 태그

- **정의**: r79 계열(H-6·H-7·H-8) 결과 항목과 격자(H-9) 결과 항목의 최상위 `controller_tag`는 그 실행의 제어기 설정(실행된 C2 설정의 LAS-b·K1 전환)으로 정한다.
  - 같은 실행에 T4h 기록이 있으면 최상위 `controller_tag`는 T4h meta의 `controller_tag`와 같아야 한다.
  - 두 값이 다르거나 한쪽에만 있으면 그 묶음은 원판 8.2 S-2로 멈춘다.
  - 이 대조는 **경로 1 도구**가 한다(`resume4368_judge`의 G-S·기록 확인 하위 명령 또는 그 묶음의 `*_4368` 판정기). G-S(원판 11.2)와 판정 전에 돌린다. 도구 결과에서 다름이 하나라도 있으면 S-2다.
  - 대조한 줄 수와 어긋난 줄 수를 판정서 13절 3항에 적는다.
- 근거: 커밋 `c4e0ed9` 전에는 r79·r67·r69 스크린이 실행 설정을 받지 않아 최상위 태그가 옵션만 반영했다(`b1ddeae` G-S: H-6·H-8 `final_C4G2_P3`, H-7 키 없음, 격자 `final_C4G2_P3`). `c4e0ed9` 뒤에는 T4h meta와 같은 함수로 태그를 만든다. `e860578`의 경로 1 도구에는 이 대조가 없어서 도구에 넣는다(사용자 결정 9, R7-7).
- 결정 필요: **아니오**(사용자 결정 1·9).

### R7-1b. `b1ddeae` G-S 출력의 태그

- **정의**: `b1ddeae` G-S의 r79·격자 출력(최상위 `final_C4G2_P3`, H-7 키 없음)은 기록 결함(커밋 `c4e0ed9` 이전)이다. 그 출력의 태그는 판정에 쓰지 않는다. 판정은 `c4e0ed9` 이후 커밋을 `git_at_start`로 한 실행의 출력으로만 한다(원판 A-5).
- 명령 해시는 이 결함으로 바뀌지 않았다. `c4e0ed9`에서 H-6·H-7·H-8 seedext·격자 1키를 다시 돌려 `commands_sha256`·`base.cmd_sha256`이 같음을 확인했다(커밋 메시지 기록).
- 결정 필요: **아니오**(사용자 결정 1).

### R7-1c. T-3K R-0 줄의 태그 키

- **정의**: H-0 출력(`las_T3_*.jsonl`) 줄 가운데 `t3.las` = `off`이고 `t3.gate` = `off`인 줄(R-0)은 `controller_tag` 키가 없어도 제어기 판 `final_C4G2`(LAS-b·K1 관문 끔 프리셋)로 읽는다. 이 줄은 키 결측(S-11)으로 세지 않는다. 기록에 태그 키가 있으면 기록값을 쓴다.
- 이 읽기는 G-S 키 있음 확인과 판 확인(원판 4.1 "한 묶음 같은 판")에 쓴다. `las_targeted_rules_rev5.md` 2.2 표의 R-0 V0 기대 태그 "없음" 대조(K-2, H-T3-3)는 rev3 R3-D2 그대로 **기록된 키**로 한다.
  - 키가 없거나 null이면 "없음"과 맞는다.
  - 키에 문자열(`final_C4G2` 포함)이 있으면 R3-D2대로 H-T3-3이다.
  - 두 문장은 같은 사실(R-0 V0 줄은 태그 키를 남기지 않는다)을 서로 다른 확인에 쓴다. 이 판은 K-2를 바꾸지 않는다.
- 결정 필요: **아니오**(사용자 결정 5).

## R7-2. 첫 DONE의 근거 교체 (rev4 R4-B2를 바꾼다, 사용자 결정 2·4)

- **정의**: r79 실행 기록의 첫 DONE은 `base`의 기록 모양에 따라 정한다.
  - (가) `base.t_done_s` 키가 있는 기록(g6·ref 하네스): rev4 R4-B2 원문대로 `base.t_done_s`를 첫 DONE으로 쓴다. 그 값은 `base.phase_path`의 첫 DONE 항목 시각과 5 ms 안에서 같아야 한다. 다르면 S-11이다. `base.t_done_s`가 None인데 `base.phase_path`에 DONE이 있어도 S-11이다.
  - (나) `base.t_done_s` 키가 없는 기록(g8 하네스): `base.timeline`(`[t_s, phase]` 단계 전환 목록)의 첫 DONE 항목 시각을 쓴다. `base.timeline`이 없거나 비었으면 S-11이다.
  - (가)·(나) 모두 DONE이 없을 때(`base.t_done_s` = None이고 `base.phase_path`에 DONE이 없음, 또는 `base.timeline`에 DONE이 없음):
    - `base.final_phase`가 `fault` 또는 `fault_reground`면 첫 DONE = None(DONE 없음)으로 정상 기록한다.
    - 그 밖이면 S-11이다.
  - 419.8 조건 5는 rev3 R3-G10 Q-12대로 읽는다: LOC가 있고 (DONE 없음 ∨ 최종 LOC < 첫 DONE).
- 적용 범위: 첫 DONE을 읽는 모든 곳에 쓴다. G-S의 모든 r79 줄과, 경로 2가 419.8 조건 5를 다시 계산하는 모든 줄이다. rev4 R4-B2의 "G-S에서 한 줄을 `phase_path`와 대조"는 이 줄마다 규칙으로 바뀐다.
- 5 ms는 기록 대조 허용이다. `phase_path` 시각은 0.01 s, `timeline` 시각은 1 ms로 반올림돼 있어 둘을 다 받아들이고, 0.1 s 제어 주기 둘은 가른다. 판정 문턱이 아니다(R7-8).
- 사건 이름 검색(`first_done` 등)은 rev4 R4-B2대로 쓰지 않는다.
- 공개(문턱 불변): H-8 경로 1의 S-4 FLAG는 저장된 419.8 기록(`base.late_loc_reapproach`, `late_loc_rule`)을 읽고, 그 조건 5는 최종 LOC ≤ 첫 DONE + 10⁻⁹ s(비엄격)다. 경로 2는 rev3 Q-12의 엄격 비교(최종 LOC < 첫 DONE)로 다시 계산한다. 두 값은 LOC와 첫 DONE이 같은 시각일 때만 다르고, 다르면 원판 9.2 대조로 드러난다. 이 판은 어느 쪽의 비교도 바꾸지 않는다.
- 근거 사실(메인 세션 전달, 2026-11-13): 저장 r79 base 6,524개 = `t_done_s` 경로 4,547 + `timeline` 경로 1,977. 모두 이 규칙을 통과한다. DONE이 없는 4개는 모두 `r79_V0_L1L2L3`의 fault 실행이다.
- 결정 필요: **아니오**(사용자 결정 2: 기록 모양 두 가지 구분 승인, 사용자 결정 4: DONE 없음 + fault는 정상).

## R7-3. 이름 대응표 (경로 2는 이 표의 경로·단위·형식만 쓴다, 사용자 결정 3)

- 경로 2는 아래 표의 기록 경로·형식·단위·뜻만 쓴다. 표에 없는 필드는 앞 판의 정의대로 읽는다. 표와 실제 기록이 다르면 S-11이다(G-S에서 확인).

### R7-3a. F-8 `d1.g6_preloc` (run_v5 d1 줄, `d1.path` = `g6`, rev5 R5-D1·R5-D4)

| 기록 경로 | 형식 | 단위·뜻 |
|---|---|---|
| `d1.g6_preloc.preloc_flag_ok` | bool 또는 null | 시작(`preloc_starts`)이 하나 이상이고, 모든 시작의 `true_min_kN`이 null이 아니며 F_min(9.414589 kN) 이상이고, 실행 `final_phase`가 `fault`·`fault_reground`가 아니면 true. 시작이 하나도 없으면 false. r72 기록에 키가 없으면 null |
| `d1.g6_preloc.preloc_starts` | list(빈 목록 가능) | LOC 전(LOC가 없으면 전부) `leg_reapproach_start:<leg>` 사건마다 원소 하나, 사건 순서 |
| `…preloc_starts[].t_s` | float | 재접근 시작 사건 시각 [s]. 제어기 사건 시각(하네스 plant 시각과 같은 원점), 0.01 s 반올림 |
| `…preloc_starts[].leg` | str | `FL`·`FR`·`RL`·`RR` |
| `…preloc_starts[].true_min_kN` | float 또는 null | 그 다리 참 실린더 힘 최소 [kN], 0.01 kN 반올림. 표본 = 제어 주기(10 Hz)마다 그 주기 1 ms 하위 스텝 최소(패드 접촉력 − 로드 무게). 창 [사건 시각 − 0.1 s, LOC + 1 s](LOC가 없으면 마지막 표본 시각 + 1 s), 양 끝 포함. 창에 표본이 없으면 null |
| `d1.g6_preloc.source` | str | 고정 문자열 `r72_g6_screen record (spec 377, rev5 R5-D1)` |

- 이 표의 "LOC"는 r72 기록의 판정 LOC다. LOC 취소가 없으면 첫 `crawler_liftoff_confirmed`, 취소가 있으면 최종 LOC(t_LOC^fin, 424.8.1)다. 같은 기록의 `G6-7_preloc`(강등 대상 사건)도 같은 LOC를 쓴다.
- `preloc_flag_ok`의 F_min 비교는 0.01 kN으로 반올림된 기록값으로 한다. 경로 2가 이 표로 377 조건을 다시 계산할 때(rev5 R5-D1 4)도 기록값을 쓴다.
- 공개(판정서 한계 절): Chrono 새 판의 377 창 끝은 rev6 R6-B3대로 첫 확정 LOC + 1 s다. 하네스의 377은 rev5 R5-D1·rev6 R6-C3대로 이 기록으로 판정하므로, LOC 취소가 있는 줄에서 두 엔진의 창 끝이 다르다. 두 엔진 모두 강등 대상 사건과 창이 같은 LOC를 쓴다. 판정서에 LOC 취소가 있었던 g6 경로 줄 수를 적는다.

### R7-3b. T-3K 정체성 (`las_T3_*.jsonl`, 첫 줄 `header`, 다음 줄부터 줄마다 `t3`, rev6 R6-C2 표의 "제어기·도구 sha" 원본)

| 기록 경로 | 형식 | 단위·뜻 |
|---|---|---|
| `header.identity.git_head` / `t3.identity.git_head` | str, 40자리 16진수 | 부모 프로세스가 시작 때 읽은 `git rev-parse HEAD` |
| `t3.commit` | str, 40자리 16진수 | 같은 값 |
| `header.identity.sha256` / `t3.identity.sha256` | dict {파일 이름: 64자리 16진수} | 키 6개 `las_t3.py`, `las_t3_dg3.py`, `las_h7.py`, `las_judge.py`, `las_targeted.py`, `las_t3_presets.py`. 그 프로세스가 읽은 작업본 바이트(CRLF 포함)의 sha256 |
| `…identity.c2_sha256` | str, 64자리 16진수 | `03_src/outrigger_sim/control/c2.py` 작업본 바이트의 sha256 |
| `…identity.threads` | dict {변수: str 또는 null} | 키 5개 `MKL_NUM_THREADS`, `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `NUMBA_NUM_THREADS`, `MKL_THREADING_LAYER` |
| `…identity.workers` / `t3.workers` | int | `--workers` 값 |
| `…identity.affinity` | str 또는 null | `--affinity` 인자 문자열 그대로(예 `"0x00FF0000"`). 주지 않으면 null |
| `t3.affinity_hex` | str 또는 null | 같은 값 |

- `header.identity`는 부모 프로세스가 한 번 잰 값이다. 줄마다의 `t3.identity`는 그 줄을 돈 작업자 프로세스가 다시 잰 값이다.
- rev6 R6-C2 표의 조건(헤더와 모든 줄이 같고, R-0·R-0K·T-3K 세 출력이 서로 같다)은 이 필드로 대조한다.
- 결정 필요: **아니오**(사용자 결정 3).

## R7-4. Chrono 조건부 결측 (원판 11.2·8.2 S-11 보충, 사용자 결정 6)

- **정의**: G-S와 본 실행의 `run_S9.py level` 행에서 키 결측을 허용하는지는 `v5_resume_4368/chrono_rows_manifest.json`의 `gs_conditional_absent` 조건으로 정한다.
  - 표는 `v5_resume_4368_chrono_rows.gs_conditional_table()`이 코드에서 만든다. `table_sha256` = `eef5129f43114877a005950ddd30eca8216d4d08a3196a2d1e82e5dc3363c9aa`(정렬한 `keys` JSON의 sha256)다.
  - 표 안의 키는 `absent_allowed_when`이 성립할 때만 `conditional_absent`다. `required_when`이 성립하는데 없으면 `result_missing`이고, 그 행은 G-S 실패(원판 8.2 S-11)다.
  - 표 밖의 키는 언제나 있어야 한다.
  - `gs-check --manifest`는 저장된 표의 `keys`가 코드 표와 같을 때만 종료 0이다.
  - 이전 G-S에서 관측한 `conditional_absent` 목록은 기준으로 쓰지 않고 기록만 한다.
- 표의 키 9개:

| 키 | 결측 허용 | 필수 |
|---|---|---|
| `p3b.P3-3_leg_force.F_min_after_N`, `p3b.P3-3_leg_force.F_min_transient_N` | `result.json` `p3b.departure.departed`가 False | 그 밖(True, 다른 값, 키 없음) |
| `c2_setup.las_off` | 켬 팔(`r4368.arm` ≠ `"off"`) | 끔 팔(`r4368.arm` = `"off"`) |
| `controller_meta.liftoff_approach_slow.start_s`, `.end_s`, `.end_reason`, `.active_periods`, `.ramp`, `.ramp.periods_applied` | 끔 팔 | 켬 팔 |

- manifest 작업본 sha256 `7b4ae7c46e39f0944c5c542a367a9dec760bb121a1eca5c804e5179af725dac2`(LF 본 `a2752380…`)이다. 묶음별 `list_sha256` 10개는 `b1ddeae` 판과 같다(메인 세션 전달).
- 이 표는 키 있음 확인(원판 11.2)에만 쓴다. 판정에서 키가 없을 때의 처리는 원판 9.3과 rev2 R2-2 그대로다.
- 결정 필요: **아니오**(사용자 결정 6).

## R7-5. Chrono 경로 1 집계 v2 (공개, rev5 R5-A1·rev6 R6-A 보충)

- **정의**: `04_scripts/02_chrono/chrono_rows_judge_4368.py` v2(`TOOL_VERSION` "chrono_rows_judge_4368 v2 …")는 C-1~C-5와 C-8 기록 행을 읽는다.
  - C-6·C-7은 원판 9.1대로 경로 1 = `result.json` `p3a`이다. 새 판은 이 행을 판정하지 않고 `skipped_rows`에만 남긴다(근거 원판 9.1·7.5·8.1, rev5 R5-A1, rev3 R3-G11). 종료 코드에 영향이 없다.
  - L2b·L1-R 행 폴더는 행 로그 `<batch>/<case>.log`의 마지막 `batch wall … -> <폴더>` 줄로 정한다. 그 폴더에 `result.json`이 없으면 결과 루트 아래 같은 상대 경로를 한 번 더 보고, 그래도 없으면 멈춘다.
  - 그 줄이 없으면 그 행의 시각 창(`progress.log` START~END, 없으면 배치 시각 + `wall_s`) ±2 s 안에 시각이 든 러너 폴더가 하나뿐일 때 그 폴더를 쓴다. 없거나 둘 이상이면 판정하지 않고 멈춘다.
- v1과의 차이는 입력(행 폴더) 선택과 열린 루프 행 제외뿐이다. 판정 정의(D-26~D-39)는 바뀌지 않는다. 판정서에 v2의 sha256과 행마다 폴더를 찾은 방법(`case_log`, `case_log_relocated`, `time_window`)을 적는다(R5-A1 요건 3).
- 결정 필요: **아니오**.

## R7-6. 실행 정체성: 풀 마스크 (원판 6절 보충, 사용자 결정 7)

- **정의**: `s9_batch run`의 `--p-mask`·`--e-mask`는 환경 변수 `OUTRIGGER_PCORE_MASK`·`OUTRIGGER_ECORE_MASK`로만 전달한다. argv와 명령 해시는 바뀌지 않는다.
  - 적용된 마스크는 `result.json` `placement.affinity_mask_process`·`affinity_mask_ok`와 `batch.json` `affinity_masks`, 행마다 `placement_applied`에 기록된다. 기록은 실제로 적용된 마스크다.
  - 원판 6절의 SCM 판정 행 조건(`pool` = `planned_pool` = `pcore`)은 그대로다. 마스크는 그 풀 안이어야 한다(풀 밖이면 러너가 affinity를 바꾸기 전에 거부한다).
  - `affinity_mask_ok`가 거짓인 행은 원판 6절의 "실행 중 affinity 변경 기록"과 같이 판정서에 적는다.
- `b1ddeae` G-S의 E행 `placement` 기록(논리 CPU 16~27)은 외부 재고정으로 실제로는 16~23이었다. G-S는 판정하지 않으므로 기록만 한다.
- 결정 필요: **아니오**(사용자 결정 7).

## R7-7. G-S의 지위와 순서 (원판 11.2 보충, 사용자 결정 8·9)

- `b1ddeae` G-S 출력(하네스·Chrono 1회)은 기록 결함 수정(`c4e0ed9`, R7-1b) 이전의 출력이다. 원판 11.2 충족의 근거로 쓰지 않고 기록만 한다. 그 출력의 태그(R7-1b), `conditional_absent` 관측(R7-4), `placement`(R7-6)도 기록만 한다.
- `e860578`에서 시작했다가 중단한 G-S(사용자 결정 9)는 기록만 남긴다. 판정과 원판 11.2 충족에 쓰지 않는다.
- **순서**(사용자 결정 9):
  1. 이 판을 봉인한다.
  2. 경로 1 도구를 고친 커밋(이하 "도구 커밋")을 넣는다. 고치는 것은 R7-1a 대조와 이 판의 봉인 확인이다.
  3. 도구 커밋에서 G-S 전체를 다시 돈다.
- **봉인 확인**: 경로 1 판정 도구의 봉인 확인 목록(`chrono_rows_judge_4368.py` `RULES_SEALS`, `judge4368_common.py`의 봉인 목록)에 이 판(`v5_resume_4368_rules_rev7.md`)과 그 봉인 sha를 더한다. 도구는 rev7 파일의 sha256이 봉인 sha와 `.sha256` 기록 둘 다와 같은지 확인한다. 다르거나 없으면 원판 8.2 S-1이다.
- **도구 커밋에서 rev7 봉인 뒤 G-S 전체를 다시 돌린 것을 원판 11.2 충족으로 본다.**
  - 도구 커밋 sha와 G-S 배치(하네스 출력 경로, Chrono 배치 폴더)는 판정서에 적는다.
  - `git_at_start`는 도구 커밋이거나, 그 위에 판정서·감사 기록만 더한 커밋이다. `git diff --stat <도구 커밋>..GIT_AT_START`로 확인하고 판정서에 적는다.
  - 그 밖의 파일이 바뀌면 원판 11.2대로 바뀐 커밋에서 G-S를 다시 돈다.
  - G-S 결과로 적을 것: R7-1a 대조 결과, rev7 봉인 확인 결과, R7-2 S-11 수, R7-4 `gs-check --manifest` 종료 코드, R7-6 마스크 기록(원판 13절 10항).
- 본 실행 배치는 compute-scheduler-expert가 정한다. 제약은 SCM 판정 행 = P(원판 6절)다.
- 결정 필요: **아니오**(사용자 결정 8·9).

## R7-8. 이 판이 쓰는 숫자 (원판 7.6 표에 더함)

| 숫자 | 쓰는 곳 | 성격 |
|---|---|---|
| 5 ms | R7-2 (가) | 기록 대조 허용(시각 반올림 0.01 s·1 ms를 받아들임). 판정 문턱 아님 |
| ±2 s | R7-5 | 행 폴더 찾기 창의 여유(폴더 시각 1 s 해상도). 절차 값, 판정 문턱 아님 |
| 0.01 s, 0.01 kN | R7-3a | 기록 형식(반올림 자리) |
| F_min 9.414589 kN | R7-3a | 기존 문턱(YAML, 원판 2절) |

## R7-9. 결정 표

| 항목 | 권고·정의 | 결정 필요 |
|---|---|---|
| R7-1a 최상위 태그 | 실행 제어기 설정으로, T4h meta와 같아야 함, 경로 1 도구가 대조, 다르거나 한쪽만 = S-2 | 결정됨: 사용자 결정 1·9(2026-11-13) |
| R7-1b `b1ddeae` 태그 | 기록 결함, 판정에 안 씀, 명령 해시 불변 | 결정됨: 사용자 결정 1 |
| R7-1c R-0 태그 키 | 키 없음 = `final_C4G2`로 읽음(결측 아님), K-2 대조는 R3-D2 그대로 | 결정됨: 사용자 결정 5 |
| R7-2 첫 DONE | (가) `t_done_s` + `phase_path` 5 ms, (나) `timeline`, DONE 없음 + fault = None | 결정됨: 사용자 결정 2·4 |
| R7-3 이름 대응표 | F-8 `d1.g6_preloc`, T-3K 정체성 | 결정됨: 사용자 결정 3 |
| R7-4 Chrono 조건부 결측 | manifest `gs_conditional_absent`(코드 표, `table_sha256` `eef5129f…`) | 결정됨: 사용자 결정 6 |
| R7-5 경로 1 집계 v2 | 행 폴더는 행 로그, 없으면 ±2 s 유일 후보, C-6·C-7은 `skipped_rows` | 아니오 |
| R7-6 풀 마스크 | env로만 전달, 기록 = 실제 마스크, 풀 안 | 결정됨: 사용자 결정 7 |
| R7-2 공개 | H-8 조건 5 경로 1 ≤(+10⁻⁹) / 경로 2 <, 문턱 불변 | 아니오 |
| R7-7 G-S 지위와 순서 | `b1ddeae`·`e860578`(중단) 기록만. rev7 봉인 → 도구 커밋(R7-1a 대조, rev7 봉인 확인) → 그 커밋에서 G-S 전체 = 11.2 충족. `git_at_start` = 도구 커밋(+ 판정서·감사 기록만) | 결정됨: 사용자 결정 8·9 |
| R7-8 숫자 | 5 ms·±2 s는 절차 값, 문턱 아님 | 아니오 |

### 결과 전 사용자 결정 기록 (모두 2026-11-13, 메시지 박스)

| # | 결정 | 반영 |
|---|---|---|
| 1 | r79·격자 최상위 `controller_tag` 결함 → 코드 수정 + rev7 확인 문장 | R7-1a, R7-1b |
| 2 | R4-B2 근거 → timeline 재구성(기록 모양 두 가지 구분 승인) | R7-2 |
| 3 | 경로 2 이름 차이 → rev7에 이름 대응표, 경로 2 수정 | R7-3 |
| 4 | DONE 없음 → timeline 결측만 멈춤, DONE 없음 + fault는 정상(None) | R7-2 |
| 5 | T-3K R-0 태그 결측 → `final_C4G2`로 읽음 | R7-1c |
| 6 | Chrono 조건부 결측 → manifest `gs_conditional_absent` 조건 표(코드 생성) 기준 | R7-4 |
| 7 | 러너 마스크 옵션 추가(기록 = 실제 마스크) | R7-6 |
| 8 | 병합 뒤 G-S 전체 재실행, 본 실행 배치는 compute-scheduler-expert(제약 SCM 판정 행 = P, 원판 6절) | R7-7 |
| 9 | (가) 경로 1 도구에 R7-1a T4h meta 태그 대조와 rev7 봉인 확인을 넣고 그 커밋에서 G-S 전체 재실행. `e860578` G-S 중단. 순서 rev7 봉인 → 도구 커밋 → G-S | R7-1a, R7-7 |

## 봉인 때 바꿀 머리 줄 (메인 세션)

1. 파일 이름: `v5_resume_4368_rules_rev7_seal_candidate_draft.md` → `v5_resume_4368_rules_rev7.md`(같은 폴더). 초안 파일은 지우지 않고 그대로 둔다.
2. 1행을 다음으로 바꾼다:
   `# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev7 (기록 정의 보충: 태그 확인·첫 DONE·이름 대응표·Chrono 조건부 결측·경로 1 집계 v2·풀 마스크, 결과 전, 봉인)`
3. 3행(첫 글머리 "상태")을 다음으로 바꾼다:
   `- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev7.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev7_seal_candidate_draft.md`와 1·3·5·9행만 다르다.`
4. 5행("시점")에서 `SEAL_TIME`(예: 2026-11-13 10:00:00 +09:00)과 `SEAL_COMMIT`(봉인 파일을 넣는 커밋의 앞 커밋, 7자리)을 값으로 바꾼다. 이 두 이름 말고는 5행을 바꾸지 않는다.
5. 9행("봉인 준비판이다")을 다음으로 바꾼다:
   `- **봉인본이다.** 사용자 결정이 필요한 새 항목은 없었고, 사용자 결정 9개(2026-11-13)는 R7-1~R7-7과 R7-9 결정 표에 반영했다.`
6. 바꾼 뒤 sha256을 계산해 `v5_resume_4368_rules_rev7.sha256`에 `<sha256>  v5_resume_4368_rules_rev7.md  sealed <SEAL_TIME 값> (436.8 rev7: record definitions filled before results on top of rev6; r79/grid top-level controller_tag from the run config = T4h meta tag (else S-2), b1ddeae G-S tags = record defect; T-3K all-off line reads final_C4G2 for key presence (K-2 unchanged); R4-B2 first DONE by base shape (t_done_s with phase_path 5 ms / timeline), DONE-less fault = None; path 2 name table for d1.g6_preloc and T-3K identity; Chrono gs_conditional_absent manifest table eef5129f; Chrono path 1 v2 row folders and open-loop rows skipped; pool affinity masks recorded; H-8 condition 5 path 1 <= / path 2 < disclosed; b1ddeae and stopped e860578 G-S record only; order rev7 seal -> path 1 tool commit (R7-1a tag check, rev7 seal check) -> full G-S there = 11.2, git_at_start = that commit (+ judgement and audit records only); user decisions 2026-11-13; thresholds and grades unchanged)` 한 줄로 쓴다.
7. `.gitattributes`에 다음을 더한다:
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev7.md -text`
   - `…/v5_resume_4368_rules_rev7.sha256 -text`
   - `…/v5_resume_4368_rules_rev7_seal_candidate_draft.md -text`
8. `tools/verif/seal_check.py`와 `tools/verif/placeholder_scan.py`(봉인본에 `SEAL_TIME`·`SEAL_COMMIT`이 남지 않음)로 확인한 뒤 커밋한다. 봉인 뒤 이 문서를 고치지 않는다. 고칠 것이 생기면 `v5_resume_4368_rules_rev8.md`로 새로 봉인한다.
