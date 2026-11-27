# 436.9 판 8 T8: 판정 도구 커밋 완성 (실제 결과에는 아직 안 돌림)

## 요약
- **T8 = `ecf6c1428fb2cd71097ff56aa13f21406d3452c7`**입니다. 브랜치 `ed8-judge`, worktree `C:\workspace\outrigger_control\.claude\worktrees\ed8-judge`에 있습니다.
  - C8 `56849248`의 자식 커밋 하나입니다. WIP `01b5cc2c`는 이 커밋으로 합쳐졌고, 이제 브랜치에서는 도달할 수 없습니다.
  - C8 대비 diff는 `04_scripts/04_hydraulic/coupled`의 판정 도구와 `05_tests`뿐입니다.
  - 03_src와 C8 실행 경로 모듈 156개가 바이트 단위로 같다는 것을 시험으로 확인했습니다.
- **T8 전체 단위 시험:** 2 실패, 8816 통과, 134 건너뜀. C8 junit과 비교하면 새 실패 0, 새 건너뜀 0입니다.
  - 실패 두 건은 기존 실패입니다: `test_hydraulics_flow_limit_run::test_coupled_batch_rows_and_resume`, `test_d8x_diag::test_rerun_gives_the_stored_command_hash`.
  - 새로 추가된 시험은 211건입니다.
- ruff·codespell은 새로 쓰거나 바꾼 파일에서 0건입니다.
- 판정 도구는 실제 결과에 돌리지 않았고, 4단계 실행도 하지 않았습니다. 판 6·7 저장 줄도 fixture로 쓰지 않았습니다.

## 1. 판 7 판정 도구 들여오기
- 방법: `git checkout 60ebb4a4 -- <파일>`로 가져왔습니다(cherry-pick과 결과가 같습니다).
  - 60ebb4a4와 C8의 merge-base는 8a2a52ce입니다. 그 뒤 ed8 쪽에서 바뀐 파일은 없고, C8 실행 경로 목록에 든 파일도 없습니다.
- 기록 파일: `ed8_design\impl_report_ed8\t8\imported_from_60ebb4a4.json`

| 파일 | 60ebb4a4 blob | T8 |
|---|---|---|
| `ed7_condition3_adoption.py` | 5402b7ca9239531533897f2f24c840e586047b85 | 같음 |
| `jp3_12b_judge_ed7.py` | 8d6cfdf108998886d1bd9f620605220701fc9d5a | 같음 |
| `jp3_ed7_judge.py` | a3a842a5c7f4a3406282bef37e8de20f8d9d0771 | 같음 |
| `jp3_ed7_rules.py` | e55b3e6da10ec416dcc9b29dbe145e480824776b | 같음 |
| `jp3_rev7_condition.py` | fb9230ff2fe739346c86f279ce320ec409edd7c3 | 같음 |
| `jp3_tjr_judge_ed7.py` | 673aecaef9176ccadb5674e49ad21b39231f822a | 같음 |
| `test_ed7_adoption.py` | de891586ee2a6e5b7e6c6937bb51393d7f454052 | 같음 |
| `test_ed7_judge.py` | 7e62648cf432881de701f2d369e786f73efbdf43 | **바꿈**(아래) |
| `05_tests/data/ed7_run_path_modules_8a2a52ce.json` | a3491352465663bd2985966d140573fcd24148bd | 들여오지 않음 |

- 같음 여부는 T8과 60ebb4a4의 blob을 비교해 확인했습니다.
- `test_ed7_judge.py`를 고친 이유: 판 7 P7-11 시험 두 개는 판 8 트리에서 실패합니다. 판 8은 설계상 실행 경로가 판 7과 다르기 때문입니다(실제로 03_src 트리가 달라 실패했습니다). 그래서 두 시험과 그 데이터 목록을 뺐고, 판 8 P8-11 시험(`test_ed8_run_path.py`)으로 대신합니다.

## 2. T8 내용

### `jp3_ed8_rules.py` — 규칙 핵심
- census
  - 6.2 병합: 해시, eps 0 / 0.001, 소유 단계, 기회·실패·층. 오류 줄은 병합하지 않고 그 단계를 판정 불가로 둡니다.
  - 5.2 칸: C-J·C-S·C-G × E/N. 허용 수 0, 빈 층은 `not_applicable`, 기회 0이면 판정 불가.
  - 선택 사용 키 칸, 상태 순서.
- G′ 5단계(`ho_k_selection` 레코드)
  - 7.3 순서, 7.4 A/A(같은 층, 최대 3회), 7.5 Jeffreys k_N, k_E 1, CP95, n_AA = 0 처리.
- G′ 8단계: 2차 별칭을 계산 전에 적용하고, 동결된 A/A 값으로 k_N을 다시 계산합니다.
- 검토 중인 해석은 상수 한 곳씩으로 분리했습니다: `D_OWNER_COUNT_CELL`, `AA_MATCH_LAYERS="original"`, `AA_SAME_HASH_TRIES_NEXT=False`, `MDE_POWER`, `MDE80_DEFINITION`.
- **stats 권고 4건 반영(사용자 확정 해석 유지)**
  - Q1-a: `MDE80_DEFINITION` 문자열에 정의 출처를 적고, `ho_k_selection.mde80_definition`으로 기록합니다. 공개 수치 "N n 200, x_AA 0 → 2.7 %" 재현을 시험합니다.
  - Q1-b: 8단계 층마다 최종 `mde80`과 `mde80_frozen`을 짝으로 기록합니다.
  - Q2-c
    - 슬롯 입력에 `aa_order_length`를 둡니다. 필요한 시도 수 min(3, len)보다 적게 제공됐고 제공된 것이 모두 엇갈리면 `RuleInputError`를 내고, 판정 도구는 이를 `setting_defect`로 처리합니다.
    - 결정된 후보 뒤에 러너가 더 돌린 후보는 무시하고 `ignored_after`로 기록합니다. 같은 해시면 `same_layer_after`도 기록합니다.
    - 판정 도구는 후보 층을 V0(o″) 줄의 `reapproach_starts`로 6.3 함수를 다시 적용해 정하고, 결정된 후보 하나만 판정합니다.
  - Q2-d: `aa_summary`에 층별로 같은 해시 슬롯 수, 그 가운데 뒤에 같은 층 후보가 남은 수, 엇갈린 시도 수, 짝 수, 짝 없음 슬롯 수를 둡니다.

### `jp3_ed8_gate_judge.py` — 4단계 관문
- P8-0, P8-1, P8-5, P8-8(켬 팔 기록), P8-15, P8-16(C8 시점).
- P8-15 "면제 사용"의 정의는 `WAIVER_USE_COUNTS` 상수 한 곳에 있습니다.

### `jp3_ed8_judge.py` — census·G′·사례·l1ref
- `census`
  - C-J (i): VBN 대 V0. 판 7 J7, 읽기 (1)~(3), S8, R15 (b)를 쓰고 강성 경고 예외는 쓰지 않습니다.
  - C-J (ii): L-a·L-b·L-c·L-e를 줄 단위로 셉니다.
  - C-S: 판정 4설정, 강성 경고 예외 적용. 기록 6설정은 기록만 합니다.
  - C-D: 24줄 J-P3a·FAULT를 보고, VBN 줄은 C-G 칸에서 셉니다.
  - C-G: V0 비교, FAULT 0, U832도 셉니다.
  - 층(6.3)을 정하고 병합합니다. J-P3 경로 1은 줄 단위로 판정합니다. 정체성은 `_ED8` 태그로 봅니다.
  - 기록: L-2 면제 줄, 교착 서명, 선택 사용 키 칸.
- `stage5`, `heldout`, `cases`(P8-2), `l1ref`.

### 12a·12b
- `jp3_tjr_judge_ed8.py`: 12a, VBN/VBN0.
- `jp3_12b_judge_ed8.py`
  - 12b는 VBKN0/VBKN, `--spec`은 spec v8 sha, step 기록은 C8 기준입니다.
  - `four-case`는 8절 기록입니다: P8-14 계획(sha 고정)의 4사례에서 seed를 빼고 12b 사례 틀과 대조하고, 그 사례를 뺀 줄·사례 수와 4사례 VBKN0 줄의 교착 서명을 남깁니다.

### 시험 (모두 합성 입력)
| 시험 파일 | 건수 | 내용 |
|---|---|---|
| `test_ed8_judge_rules.py` | 58 | Q1-a·Q1-b·Q2-c(후보 2개만 제공·모두 엇갈림 → 오류, 같은 해시 뒤 후보 무시)·Q2-d, 상수를 바꾼 대체 해석 |
| `test_ed8_gate_judge.py` | 32 | 관문 판정 |
| `test_ed8_judge.py` | 47 | 아래 참조 |
| `test_ed8_run_path.py` | 4 | P8-11 |

- `test_ed8_judge.py` 47건이 덮는 것:
  - 정체성 패치와 복원, 기준 통과 판정, census 조립(C-D → C-G, 오류 단위, 해시 병합, 선택 칸).
  - 단계 조립 C-J·C-S·C-D·C-G(436.8 읽기는 스텁), 층 결함 → `setting_defect`.
  - 5단계 슬롯 입력: 층 재계산, 결정 후보만 판정, 누락 거부, 같은 해시.
  - `stage5` main을 CWD를 다른 폴더에 둔 채 끝까지 실행.
  - main 종료 코드 0/1/2/3, 12a·12b 래퍼 이름과 복원, 4사례 기록.

## 3. 검증
| 검증 | 결과 |
|---|---|
| T8 전체 단위 시험 | 2 실패(기존), 8816 통과, 134 건너뜀, 1524 s, 끝 시점 HEAD T8·clean |
| C8 junit 대비 | 새 실패 0, 새 건너뜀 0, 상태가 바뀐 시험 0 |
| ruff / codespell (새로 쓰거나 바꾼 파일) | 0 / 0 |
| 들여온 판 7 시험(이식 직후) | 104 통과, 판 7 P7-11 1건 실패 → 제거 |

- 전체 시험은 ed8-judge에서 Chrono-dev `-n 12 --dist loadfile`, `OUTRIGGER_RECORDS_ROOT=main`, `NUMBA_CACHE_DIR`은 scratch로 돌렸습니다.
- 들여온 판 7 시험은 이식 직후 `test_ed7_judge.py`와 `test_ed7_adoption.py`만 따로 돌린 결과입니다.
- 증거(`impl_report_ed8\tests\`): `junit_T8_ecf6c142.xml`(`19ccba59…9860`), `junit_diff_C8_vs_T8_ecf6c142.txt`, `suite_T8_ecf6c142.log`
- **생산자 꼴 미시험(다′):** census·heldout·cases·l1ref와 12a·12b의 실제 판정 경로는 판 7 판정 함수와 436.8 지표를 그대로 씁니다. 시험에서는 이 읽기를 스텁으로 바꿨으므로, 실제 run_v5·r79 출력 꼴로 끝까지 돈 적은 없습니다. 실제 출력에는 쓰지 말라는 지시가 있었으므로, verif 감사에서 이 경로를 확인하거나 4단계 출력이 나온 뒤 건식 판정(출력은 실행 폴더 밖)을 권합니다.
- 정리: ed8-judge worktree의 `__pycache__` 13개와 `.hypothesis`를 지웠습니다(status --ignored 비어 있음). scratchpad `python-ed8-t8`도 지웠습니다.

## 확인 필요
1. **C-J·C-S·G′ "기준 통과"(6.1) 해석.** V0 줄이 J 항목 가운데 `fail` 상태를 하나도 갖지 않으면 통과로 봅니다(FLAG·record·undetermined는 실패로 보지 않음). R15의 J2는 악화 규칙 몫이라 뺍니다. 상수는 `BASE_FAIL_STATES` 한 곳입니다. C-D·C-G 기준 통과는 키 파일의 `v0_pass`(V0 비교의 `v0_opportunity`)입니다.
2. **C-J (ii)를 병합하지 않음.** LSN 대 VBN(L-a·L-b·L-c·L-e)은 병합 단위가 아니라 줄 단위 위반 수로 셉니다.
3. **census `--selection-keys` 입력 파일을 누가 만들지.** P8-9·P8-9′·P8-14에서 돌린 키 목록 `{"jobs": [...]}`이 필수 입력인데, 만드는 주체가 정해져 있지 않습니다.
4. **8절 "P-pred 입력 통계"의 범위.** `four-case`는 4사례를 뺀 줄·사례 수와 교착 서명만 냅니다. 4사례를 뺀 P-pred k_allow를 다시 계산하지는 않습니다.
5. **J-P3 판정 행 수 기대값.** census 단계별 기대값을 두지 않았습니다(spec 9 "판정 때 T4h로 센다"). 0이면 판정 불가로 둡니다.

## 메인 세션 권고
- T8 worktree `ed8-judge`(ecf6c142)를 잠가 주십시오: `git -C C:\workspace\outrigger_control worktree lock .claude\worktrees\ed8-judge`
- T8 감사(verif-protocol-auditor)에 아래 항목을 넣어 주십시오.
  - 위 확인 필요 1~5.
  - C8 5단계 러너가 aa2·aa3을 돌리는 조건이 판정 도구의 짝 규칙(같은 해시에서 넘어가지 않음, 층 함수 같음)과 맞는지.
  - 생산자 꼴 미시험 범위.

## 공개
- 블라인드 경로는 열지 않았습니다.
- Grep은 `ed8-judge\04_scripts\04_hydraulic\coupled`, `05_tests\unit`, `03_src\outrigger_sim\control` 등 하위 경로와 단일 파일만 지정했습니다. worktree 루트를 Grep path로 쓴 적은 이번에 없습니다.
- 메인 checkout에서는 P8-14 계획 파일의 키 이름만 열어 봤습니다. 판정값은 아닙니다.
- Bash는 git 단일 명령과 반복문 한 번(blob 비교 for 루프)에만 썼고, 파이프는 쓰지 않았습니다.
- 프로세스를 종료하지 않았습니다. 실제 결과에 판정 도구를 실행하지 않았습니다.

사용한 스킬: 없음
