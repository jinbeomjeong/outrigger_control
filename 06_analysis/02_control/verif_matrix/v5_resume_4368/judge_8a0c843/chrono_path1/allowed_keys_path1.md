# R3f 허용 차이 키 목록, 경로 1 (초안, rules rev24 R24-3 재판정 2 + rev25 R25-3 재판정)

- 작성: python-expert, 2026-11-16.
  - R3e 초안(실행하지 않음)에 rev25 범주를 더했다.
  - 실행 전 초안이며 R3f 실행 결과를 보지 않고 썼다.
- 대상: 경로 1 R3f 출력(`judge_<R3F_SHORT>\chrono_path1\`)과 R3d 출력(`judge_0220671\chrono_path1\`)의 K-10 대조.
  - R3e 출력 폴더는 만들지 않았으므로 대조 대상이 아니다(R25-3).
- 비교기: `compare_r3d.py`(같은 폴더). 그 안의 `ALLOWED`·`REASON_KEYS`·`*_IGNORED`가 이 목록과 같다.
- 키 표기
  - 점으로 이은 경로이고, `#`은 아무 목록 번호, `*`는 그 아래 모든 키다(fnmatch).
  - 파일 이름은 출력 파일이다. 행 판정은 `judge_<묶음>.json`, 묶음 집계는 `bundle_<묶음>.json`.

## 1. 대조에서 빼는 키 (앞 판들과 같음)
| 범주 | 키 | 생산 위치 |
|---|---|---|
| 봉인 블록 | `seals` | 두 도구 (`rows_judge.seal_check`) |
| 도구 판·규칙 설명 문자열 | `tool`, `rules` | 두 도구 (`TOOL_VERSION`, `RULES_DESCRIPTION` / `RULES_TEXT`) |
| 공개 블록(도구 sha·diff 수치) | `disclosure` (행 판정만) | `chrono_rows_judge_4368.py` `disclose()` |
| 입력 파일 경로·sha256 | `inputs.rows_judge.path`, `inputs.rows_judge.sha256` (묶음) | `chrono_bundle_grade_4368.py` `_input_files` |
| 앞 판 기록 블록 | `t45_pairing_R22_1`, `runner_name_map_R23_1` (묶음) | 같은 도구 (rev22·rev23) |

## 2. CD-10 실행 정체성 키
| 범주 | 키 | 생산 위치 | 비고 |
|---|---|---|---|
| 판정 도구가 돈 checkout 커밋 | `disclosure` (행 판정) | `disclose()`: 실행 checkout 기준 `git diff --no-index` 수치 | 1절에서 이미 뺀다 |
| 실행 시각 | 없음 | 두 도구 모두 실행 시각을 출력에 쓰지 않는다 | — |
| 출력 위치(출력 경로 인자의 원소) | `inputs.rows_judge.path` (묶음) | 행 판정 출력 경로 = R3f 출력 폴더 | 1절에서 이미 뺀다. 출력에 인자 목록 전체를 담은 키는 없다 |
| 출력 위치 | 마지막 줄 요약 `out` (`*.stdout.txt`) | 두 도구 `main()` | stdout 파일은 대조하지 않는다 |

- `commit_identity_R11_4.git_at_start`는 R2(`b9f5707`)를 그대로 받으므로 실행 정체성이 아니다. 대조에 남긴다.
- `inputs.runner_judge_dir`·`inputs.t45`(R3c 경로, 바뀌지 않음)와 `inputs.rows_judge_tool`도 대조에 남긴다.

## 3. CD-7 사유 문구 키 (어느 깊이에서든 뺀다)
| 키 | 생산 위치 |
|---|---|
| `reason` | 두 도구. 항목 사유, 427.9 행 사유(표시 문구 정정 포함), `bundle_grade.reason`, 행 판정 `ready_D-27_D-28.reason` |
| `override_reason` | 묶음 `_override` (CD-2로 바꾼 러너 항목과 `overrides[]`) |
| `grade_reason` | 묶음 `grade_row` (판정 불가 행) |
| `record_reason` | 묶음 `oc5_row`·`c4_row` (기록 불완전 행) |
| `reason_not_judgeable` | 묶음 `overrides[]` |
| `gate_reasons_CD_5` | 행 판정 `g6_grade`, 묶음 G6 항목 |
| `condition_note` | 묶음 P3-1 (READY 없음) |
| `reasons_CD_7` (블록 전체) | 묶음 `reason_check`·`record_reason_check` |

## 4. 차이 범주와 허용 키 (rev24 범주 + rev25 범주)
| 범주 | 판 | 파일 | 허용 키 |
|---|---|---|---|
| C-5 묶음 전체 | rev24 | `bundle_C5.json` | `*` |
| CD-3 사건 행 항목 | rev24 | `judge_C5.json` | `rows.#.items.moving_pressure_D-32*` |
| CD-3 판별 기록(모든 L2b 행) | rev24 | `judge_C1.json`, `judge_C2.json` | `rows.#.items.moving_pressure_D-32.event_test_CD_3*` |
| CD-5 READY 없음 항목 | rev24·rev25 | `judge_C5.json` | `rows.#.items.ready_D-27_D-28.*` |
| CD-5 READY 없음 항목 | rev24·rev25 | `judge_C2.json` | `rows.#.items.ready_D-27_D-28.P3-6`, `rows.#.items.ready_D-27_D-28.ready_reached` |
| CD-4 P3-6 역할·한계, CD-11 P3-9 기록, CD-5 P3-6 줄(기록 행 해당 없음) | rev25 | `bundle_C2.json` | `rows.#.items`, `rows.#.items.#*`, `rows.#.record_items`, `rows.#.record_items.#*` |
| CD-2 표의 재계산 항목 값, rev24 범위 안 결함 수정(case `*` 항목 표시 `case_star`) | rev24·rev25 | `bundle_C1.json`, `bundle_C2.json` | `rows.#.overrides.#*`, `rows.#.runner_items.#*` |
| CD-11 항목 목록(분류·조항 ID·설명 열, G6 펼침, 427.9 조건, 관문) | rev24·rev25 | `bundle_C1.json`, `bundle_C2.json`, `bundle_C3.json` | `item_list_CD_11*` |
| CD-8 C-8 기록 값·기록 상태(rev25 1·7·8·9) | rev24·rev25 | `bundle_OC5.json` | `rows.#.record_values_CD_8*`, `rows.#.complete`, `rows.#.missing_inputs*`, `rows.#.inputs_sha256*`, `record_status`, `inputs.rows_judge`, `inputs.rows_judge_tool` |
| CD-9 C-4 기록 출력, C-4 CD-7 빈 사유 멈춤 기록(rev24 범위 안 결함 수정) | rev24·rev25 | `bundle_C4.json` | 새 출력이다. R3d에 없어 대조하지 않고 표에 적는다(R24-3 재판정 3) |
| 표시 문구 정정 | rev24 | `judge_C2/C4/C5/OC5/OC5PROBE.json` | `rows.#.items.SGS_427_9_D-26.reason`. 3절의 `reason`이라 이미 빠진다 |
| CD-2 C1 줄 사건 시각 절단으로 바뀐 재계산 값 | rev25 | — | 경로 1의 C1 재계산은 R3d부터 이미 `event_t_s` 앞에서 자른다. 바뀌는 키가 없다 |
| CD-4 P3-7 문턱으로 바뀐 값 | rev25 | — | 경로 1의 P3-7은 원 판정기 P3b `P3-7_within`이다(원 판정기는 `mass_scale`을 이미 쓴다). 바뀌는 키가 없다 |
| C-1~C-3 ③ 켬 행에 새로 더한 J-P3 항목 | rev25 | — | 경로 1은 R3d부터 ③ 켬 행의 J-P3를 등급 항목으로 낸다. ③ 끔 행의 `해당 없음(③ 끔)`은 `item_list_CD_11` 안에만 있다 |
| CD-10 제외 키(rev24 범위 안 결함 수정) | rev25 | — | 2절과 같다 |
| CD-4로 더한 P3 항목 | rev24 | — | 경로 1은 P3 열 개를 이미 내므로 해당 키가 없다 |
| CD-6 대상 밖 행의 T4·T5 | rev24 | — | 경로 1은 바꾸지 않았다 |

- C-8 멈춤 목록 `stops`와 `m_N`·`min_leg`는 허용 키가 아니다.
  - CD-8 S-9 처리 조건은 "m과 최소 다리가 R3d와 K-10으로 같음"이다.
  - 이 키들이 다르면 대조 실패이고, 그 묶음은 멈추고 묻는다.
- C-1·C-2·C-3의 묶음 등급(`bundle_grade.grade`·`status`·`grade_without_stop`)과 행 등급(`rows[].grade`)이 R3d와 다르면 허용 키와 관계없이 대조 실패다.
  - 실행 스크립트 compare 단계는 이 차이를 `grade_differences_C1_C3.txt`로 따로 뽑는다.
  - 1건 이상이면 종료 3으로 멈춘다(R25-3).
- 위 키 밖의 차이가 하나라도 있으면 그 묶음은 판정 전에 멈추고 묻는다.
