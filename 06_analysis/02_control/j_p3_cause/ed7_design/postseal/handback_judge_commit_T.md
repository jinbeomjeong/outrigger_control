## 판 7 판정 도구 커밋 T 보고

**T = `c91065b7236fac16b8649be571e6379807609317`** (브랜치 `ed7-judge`, 부모 C `8a2a52ce`, 커밋 1개). worktree `C:\workspace\outrigger_control\.claude\worktrees\ed7-judge`는 clean이고, 명세 5.2대로 `git worktree lock`을 걸었다. 병합·push는 하지 않았다.

### 1. 범위 확인 (P7-11)
- T의 C 대비 diff는 9개 경로이고 모두 `04_scripts/`·`05_tests/` 아래다. `03_src` tree는 C와 같다.
- 실행 경로 모듈 목록 `05_tests/data/ed7_run_path_modules_8a2a52ce.json`은 155개 파일이다.
  - C의 트리를 `git archive`로 받아 만들었다(작업본은 쓰지 않음).
  - 진입점: `run_v5`·`ed7_probe`·`las_t3_dg3`·`jp3_run_identity`·`jp3_12b_plan`, 여기에 P7-4 suite가 부르는 `jp3_ed6_suite`를 더했다.
  - 포함: 진입점의 정적 import 닫힘 중 03_src 밖 파일 137개, `run_steps_ed7` 전체, dot-source되는 `run_steps/common.ps1`·`record_helper.ps1`. 파일마다 C의 blob id가 적혀 있다.
- `t_scope_check.json`은 `in_scope`다(실행 경로 파일 중 바뀐 것 0).
- 시험 `test_run_path_modules_are_the_run_commit_bytes`·`test_run_path_closure_is_unchanged_here`가 두 가지를 단언한다.
  - HEAD blob, 작업본 hash, 03_src tree가 C와 같다.
  - T에서 다시 계산한 닫힘이 목록과 같고, 판정 모듈은 닫힘에 들어가지 않는다.

### 2. 항목별 구현 위치 (5.2 항목 1~11, 정오 1)
| # | 내용 | 위치 |
|---|---|---|
| 1 | J7 `j7_items_ed7` 연결 | `jp3_ed7_judge.replace_j7` — j9main(V0 표와 LS 대 VB 표), sens, probe-repro 단위 판정 |
| 2 | 교착 서명 | `line_records` → `rules.is_stall_signature_ed7`. j9main·sens·confirm·cases에 줄별 기록(판정 아님) |
| 3 | ③ rev 7 판정 키·`plant_seed_artifact` | `condition_judgement`/`condition_basis`(`jp3_rev7_condition` 사용). 판정 집합 = rev 6 집합(rev 7 행 수 포함, `jp3_judged_rows`) + 조건 읽기. 조건 읽기 0이면 판정 불가 |
| 4 | 키 목록 대조 | sens·confirm이 봉인 키 sha를 고정값으로 단언하고, 키 줄과 결과 줄을 1:1로 맞춘다 |
| 5 | G1 `run_id` int | `rules.grid_run_index`, `jp3_ed7_judge.grid_v0_run` |
| 6 | 고정 표 합산·양방향 재현 | `rules.cluster_judgement_with_fixed`·`reproduction_differences`·`confirmation_judgement`. `sens_outcome`(재현 불일치는 집계 전에 setting_defect), `g1_outcome`과 D 24 재현 선행(`d_line_differences`) |
| 7 | 본 단위 = 판정 4설정 ∧ `probe_seen` | `sens_units`의 role. 기록 6설정의 `probe_seen`은 무시하고 대조하지 않는다. 키 파일은 바꾸지 않았다 |
| 8 | 조건 도구 head·is_clean | `jp3_rev7_condition.code_identity`가 report에 들어간다 |
| 9 | 팔 3·4 모두 만족 | `ed7_condition3_adoption.between_candidates`. 이 때문에 `undecided` 상태는 없어졌다 |
| 10 | 감도 4설정 합산, G1 U832 기록 표 | `sens_outcome`(k=4를 4설정 합산으로), `g1_outcome["u832_record"]`(게이트·오프셋 포함) |
| 11 | 판 7 설정 이름을 읽는 모든 판정 하위 명령 | 아래 표 |

판 7 설정을 읽는 하위 명령(항목 11):
| 대상 | 위치 |
|---|---|
| `j9main --edition 7` | `jp3_ed7_judge.py`(새 파일) |
| `t8`(P7-1, VBM 대 VBM0) | 같은 파일 |
| `cases`(P7-2) | 같은 파일 |
| `hash-match`(rev 7 `spec_edition` 확인 추가) | 같은 파일 |
| `probe-repro`(P7-3·P7-9: 6bfb2560 a2 해시 대조 + 고정 표 64행을 C 줄로 다시 계산해 양방향 대조) | 같은 파일 |
| sens, confirm | 같은 파일 |
| 12b VBKM/VBKM0, P-pred, decide | `jp3_12b_judge_ed7.py`(새 파일) |
| 12a VBM 대 VBM0 | `jp3_tjr_judge_ed7.py`(새 파일) |

판 6 도구 파일은 그대로 두었다.

정오 1 반영:
- **1-2 조건 2**
  - 판정만 읽는 입력(고정 표, probe jsonl, 격자 키, V0, 키 파일)은 sha를 고정해 두고, 다르면 setting_defect다.
  - 실행 단계 출력은 `--step-done <.done>`로 확인한다: exit 0, commit = C, 끝 정체성 head = C·clean, 파일이 그 단계 폴더 안에 있을 것. `selection.json`은 `selection_sha256`와 대조한다.
- **1-3**: decide 출력은 `status`가 `needs_b4`/`decided`, `blocks`는 b1·b2·b4의 부분집합이다. `ed7_record`에 입력 sha, seed 20261125, n_par·n_rep, k_allow, HEAD·is_clean이 들어간다. 형태가 어긋나면 setting_defect다.
- **1-5**: 실행 경로 목록 파일(위 1절).

Q7-D3 기록(`rules.twist_branch_records`, 줄별): |D_before| > 15 kN인 shot 수, 사건 뒤 10 s 안 shot 수, shot 창 [start, end + 1 s] 안에서 시작한 `twist_over_limit` 진입 수. 블록이 없으면 None으로 두고 0으로 읽지 않는다.

### 3. 시험 결과
- **T 시험 범위**(84개 파일): T가 바꾼·더한 시험, 판정 도구를 import하는 시험, 핵심 패턴과 `test_ed7_*`.
  - T의 clean 상태에서 `tools\verif\worktree_tests.py`로 돌렸다(Chrono-dev, E 코어 0x0FFF0000, 17:20~18:16).
  - 결과: **2650 통과, 실패·오류·건너뜀·xfail 0.**
  - 기준 목록 `571f42a1…`로 `jp3_ed6_suite judge`를 돌린 결과 `pass`: 새 실패 0, 핵심 미통과 0, 새 건너뜀 0.
  - 시작·끝 HEAD는 둘 다 `c91065b7`, is_clean은 둘 다 True다.
  - probe 모듈 `outrigger_sim`·`jp3_ed7_judge`는 모두 worktree에서 import됐다.
  - worktree_tests의 종료 1은 정보성 경고(`rebase_never_used`) 때문이고 시험 실패가 아니다.
- 새 시험 `test_ed7_judge.py` 62개가 모두 통과했다.
  - 명세가 요구한 단위 시험: 고정 표 합산 6꼴, D VBM 1 + G1 3이면 실패, VBMslow는 집계 제외, 재현 불일치 양방향, run_id 문자열, 기록 설정은 대조하지 않음, 판정 불가 분기, 12b 결정 형식.
  - **생산자 실제 출력 꼴 끝까지 실행**: b46bdf8f 재현 줄(`ed7_probe_a2.jsonl` + `_t4h`, 맨 파일 이름)을 복사하고 CWD를 다른 폴더에 둔 채 `main`을 끝까지 돌렸다. 대상은 probe-repro, confirm, sens, j9main, cases이고 status 목록 세 가지를 모두 단언했다. 초안 edition 85ce6e2a는 시험에서만 monkeypatch했다.
  - 실데이터 결과: 해시 114/114 일치, 고정 표 40단위·D 24줄 차이 0, D VBM 12줄의 J-P3 판정 행 12, ③ 조건 pass.
  - probe a2 M·Mslow의 정체성이 run_v5 VBM·VBMslow와 같음도 확인했다.
- `test_ed7_adoption.py`: 기존 `undecided` 시험을 새 규칙으로 고쳤고, 둘 다 채택 조건을 만족하는 경우 2개를 더했다.
- ruff(프로젝트 설정)·codespell은 변경 파일에서 0건이다. ruff format은 돌리지 않았다(기존 파일 스타일을 따름).
- 도구 점검 기록: clean T에서 `probe-repro`를 b46bdf8f 줄에 돌렸다. 해시 일치·고정 표 차이 0이고, setting_defect의 원인은 초안 `spec_edition` 78줄뿐이다(C 줄은 10902ffd여야 하므로 기대한 결과).

### 4. 근거
`C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\judge_commit_c91065b7\` — `SHA256SUMS` 13개 항목(재귀), sha256 `adb82c9cd4e1d0771d0675ff6b7fcf5fac54c940cb002ee942d9c9d381f70f64`.
- 생성·검사 스크립트: `make_run_path_list.py`, `t_scope_check.py`, `t_scope_tests.py`
- 산출: `t_scope_check.json`, `t_test_range.txt`, 목록 사본, `suite_T\`(junit, suite_judgement, suite_record, worktree_tests.md), 도구 점검 report와 그 stand-in `.done`, 커밋 메시지

scratchpad 하위 폴더는 지웠다.

### 5. 확인 필요
1. **j9main의 LS 대 VB 표 J7**: 6.1 새 비교를 LS 대 VB 표(L-a)에도 적용했다. 명세 문면은 "V0 대비"다. LS 표는 판 6 비교로 둘지 정해 주기 바란다.
2. **P7-2 사례 범위**: 명세는 "A~F·X11"인데 C run steps는 E·F 10줄만 돈다. `cases`는 그 10줄을 판정한다. A~D·X11 재생은 C에 없다.
3. **③ 끔 태그 미검증**: VBM0·VBKM0의 태그를 `final_C4G2_LAS_K1_LSB`로 가정했다(`with_switch_tags` 읽기). 판 7 ③ 끔 실데이터로는 확인하지 못했다. T8 VBM0 줄이 처음 확인이 된다. 다르면 setting_defect로 드러난다.
4. **r79 줄(12a/12b) 정체성**: `hydraulic_options`는 `p1_patch`만 대조하고, `lsb_*`·`probe_d6_settings`는 T4h meta에서 읽는다. 판 7 r79 실출력으로는 확인하지 못했다(l1ref가 처음).
5. **정오 1-2 조건 2의 해석**: `.done`에는 출력 sha가 없다(`selection_sha256` 제외). 그래서 단계 기록(exit·commit·clean 끝 정체성)과 폴더 소속을 단언하고, sha는 report에 기록한다. 이것이 "`.done` 값과 대조"를 충족하는지 확인이 필요하다.
6. **j9main J-P3 기대 행 수**: 판 6과 같이 200으로 두었다(같은 job 배치이고 head-only는 사례 경로로 정해짐). 명세는 "키 목록 단계에서 다시 센다"이다.
7. **12b decide의 `--spec`**: 봉인 명세(master e241638d)는 C·T 트리에 없다. 그래서 decide에 `--spec <메인 checkout 명세>`를 주게 했다. 없거나 sha가 다르면 setting_defect다.
8. **조건 읽기 0의 범위**: ③ rev 7 조건 읽기가 0이면 해당 하위 명령 전체 status가 not_judgeable이 된다(6.1·6.5를 그렇게 읽음).

### 6. 공개(블라인드 절차)
- 블라인드 경로(`606f8713/cdry_a1/...`)와 판 6 `ed6_inputs/x11/selection.json`은 열지 않았다.
- 검색 범위는 모두 경로를 직접 지정했다.
  - Grep: `run_steps_ed7`, `run_steps/common.ps1`, 03_src·04_scripts·05_tests, 지정한 명세·handback 파일
  - Glob: `fixed_table_b46bdf8f`
  - 디렉터리 이름만 나열: `j9_runs/79495405`, `j9_runs/b46bdf8f/repro_a2`
  - 구조 확인: `79495405/l1ref_a1`의 r79 줄과 T4h meta는 키 이름만 출력했다. 고정 표·키 파일은 필드명과 첫 항목을 출력했다.
- 첫 Glob 2회는 worktree 루트를 path로 줬으나 패턴이 `04_scripts/**`라 결과 0건이었다(`06_analysis`의 이름·건수 노출 없음).

### 7. 위임 필요
- verif-protocol-auditor의 T 감사는 메인이 맡긴다(P7-11).
- 판정 단계에서 넘겨야 하는 인자: 각 하위 명령에 해당 단계 `.done`, 12b decide에는 `--spec`.

사용한 스킬: 없음
메모리 반영안: `tool_edition_wrapper_patch.md` — 모듈 전역 patch 래퍼가 dict에 잡힌 COMMANDS, argparse choices 리터럴, 제자리 변경 dict를 놓친다(MEMORY.md에 추가함).
