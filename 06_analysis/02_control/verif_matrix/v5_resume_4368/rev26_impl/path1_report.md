# 436.8 rev26 도구 보완: 경로 1 구현 보고 (python-expert, 2026-11-26)

## 0. 요약
- **커밋**: `ebda7c0c9a0a5fb383975abcf121786493337518`. 브랜치 `rev26-p1`, worktree `C:\workspace\outrigger_control\.claude\worktrees\rev26-p1`이고 기준은 `932f1fb1724f074e4ee93a9c02193c7c840d13c4`, `core.autocrlf=true`다. 커밋은 하나다. 커밋 뒤 `git status --porcelain --untracked-files=all`은 0줄이다.
- **연결이 끊긴 뒤 재개한 상태**: 재개했을 때 `rev26-p1` worktree와 브랜치는 아직 없었다(`git worktree list`에 없었고 `cannot change to …` 오류가 났다). 그래서 지시받은 명령으로 새로 만들었다. 끊긴 사이에 남은 내 프로세스는 없었다. 실행 중에 다른 세션의 Chrono-dev pytest(PID 116856)를 보았는데, 손대지 않았다.
- **구현 범위**: R26-2(경로 1), R26-3, `--tag-mode`, RD-2 경로 1 봉인 칸, 규칙 파일 복사(master와 바이트 같음), `.gitattributes` 7절 `-text` 6줄을 구현했다. 입력 해석 코드는 바꾸지 않았다.
- **시험**: 마지막 커밋 트리에서 `test_*4368*.py` 18개 파일을 돌렸다. 결과는 714 통과, 6 건너뜀(pychrono 없음, 기준선과 같음), 3 제외(main `07_results`를 읽는 G-S 시험, 6절), 실패 0이다.

## 1. 바뀐 파일 (`git diff --name-only 932f1fb..ebda7c0c`)
| 파일 | 구분 | 커밋 blob sha256(raw) |
|---|---|---|
| `.gitattributes` | 7절 `-text` 6줄 추가만 | `909690554a6a7ca6b169b5de7a4778b92ac6bd70e82ecd7de81309287d69b2d4` |
| `04_scripts/04_hydraulic/coupled/README_judges_4368.md` | 허용 목록 | `0c3acd8dc00949d7d01fffaee215be5141abb0ed1dd3081175ee92d609574341` |
| `04_scripts/04_hydraulic/coupled/judge4368_common.py` | 허용 목록 | `f7a448d3b8656ac764b3074450b1ba1e800618a4797a04de50395451c82d7fb4` |
| `04_scripts/04_hydraulic/coupled/u3_judge_4368.py` | 허용 목록 | `7967096cfba750547af475ec9dd4087be4c3fe21923e98d0b1abf0d2dfbd5a9c` |
| `05_tests/unit/test_resume4368_rev1.py` | 허용 목록(시험) | `8147b4188d30d85b038c0d15f4a5973092d1c971b9257675af6ddb5e69dbde2a` |
| `05_tests/unit/test_resume4368_rev16.py` | 허용 목록(시험) | `19f6df34e46353321ca97368279e852c85eab7ec06d72fb57a4c3f63f9ff59a9` |
| `05_tests/unit/test_resume4368_supplement4.py` | 허용 목록(시험) | `af44551481a5a9ab6210e9e775d3cc102c5d05a16b6861d0273aea5233dad6c9` |
| `06_analysis/02_control/verif_matrix/scripts/resume4368_judge.py` | 허용 목록 | `1e8e567326cc15703639466af07157a592599ab75ab3628fce0885026b5d3787` |
| `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev26.md`, `.sha256` | 규칙 파일(master에서 `git checkout master -- …`) | master와 `git diff` 0. `.md` sha `f6591836…` |
| `06_analysis/02_control/verif_matrix/v5_resume_4368/rev26_fixed/**`(14개) | 규칙 파일(같은 방법) | master와 `git diff` 0. `excl_fields_r5.py` `bee9eee7…`, `rev26_excluded_fields_r5.json` `9e1831f5…` |

- 바꾸지 않은 허용 목록 파일은 6개다: `judge_stage1_4368.py`, `h8_noise_judge_4368.py`, `h6_judge_4368.py`, `test_judges_4368.py`, `test_judges_4368_h6_h8.py`, `test_resume4368.py`, `test_resume4368_supplement5.py`. 이 가운데 `test_resume4368_supplement5.py`도 바꾸지 않았다.
- `git diff --name-only 932f1fb..ebda7c0c -- 03_src 02_params`는 0건이다.
- worktree 4개 대상 파일의 `git ls-files --eol`은 모두 `i/lf w/lf attr/-text`다.
- worktree `03_src/outrigger_sim/hydraulics/v5_options.py`의 raw sha256은 `d2b903a2a666c97859a4a73b908ebdabe2cef28ae1dd5f47b728527f5762b28e`다. (g)의 원 값과 같다.
- `.gitattributes`에는 master의 주석 줄 `# rev26 seal (2026-11-23)`을 넣지 않았다. 7절 `-text` 줄만 더했다. diff를 `+` 6줄로 맞추려고 그렇게 했다.

## 2. 구현 기록

### 2.1 R26-2: `ind-las`의 `state`·`status`·`markers` (경로 1)
- **근거 정의 문장**
  - `v5_resume_4368_rules_rev26.md`:40(R26-2 행)과 :45~59(1.2 값 대응표)
  - 등급 대조 표 `judge_932f1fb/_fixed/grade/r4_grade_compare_table.md`:42(경로 1 기록 낱말 키 `state`), :105(H-4 행), :108(H-7 행)
- **구현**: `resume4368_judge.py` `ind_las()`가 기존 보고에 `ind_las_record_words(report)` 결과를 덧붙인다. 다른 필드와 `exit_code`는 바꾸지 않았다. 표지는 `r4_lists`로 옮기지 않는다.
- **값 대응표(코드와 1.2가 같음)**

  | 순서 | 조건(기존 필드) | 표지 |
  |---|---|---|
  | 1 | `adapter_defect`가 참(`is True`) | `IND_LAS:adapter_defect` |
  | 2 | `gate_unreadable`가 정수이고 0보다 큼 | `IND_LAS:판독 불가 <n>` |
  | 3 | `record_state` ≠ `"기록"`, 또는 세 키 가운데 하나라도 없음 | `IND_LAS:기록 상태 미정` |
  | 결과 | 표지가 없음 → `state` = `status` = `"기록 완료"` / 표지가 있음 → 둘 다 `"기록 불완전"` | |

  - 해석 하나(확인 필요 3): 정해진 형(문자열·참거짓·정수)이 아닌 값은 "없음"으로 읽는다. 결측 수를 0으로 읽지 않기 위해서다.
- **동치 대안 확인(식별자만 읽는 점검)**
  - `identifier_check.py`(AST)로 확인했다. `ind_las_record_words`가 읽는 문자열 키는 `record_state`·`adapter_defect`·`gate_unreadable`뿐이다.
  - 1.2 문장을 그대로 옮긴 함수와 128개 조합(값 형 포함)으로 대조했다. 차이는 0이다.

### 2.2 R26-3: u6 저장 줄의 (controller, v5.controller_tag) (두 경로 공통 정의, 경로 1 구현)
- **근거**
  - rev26:41
  - 원판 `v5_resume_4368_rules.md`:70~75(4.1 표), :80(섞이면 멈춤), :281(S-2)
  - `u3_u6_rerun_rules.md`:16(U-6 VB, C2 = ③ 켬)
- **구현(`resume4368_judge.py`)**
  - `u6_line_check(unit)`: 두 필드가 있고, `controller`가 넷 가운데 하나이고, `v5.controller_tag`가 대응 문자열과 통째로 같을 때만 통과한다. 그 밖은 모두 `S-2`이고 사유에 `rev26 R26-3`을 적는다.
  - `unit_kind_check`: u6 줄(`field="controller"`)은 이 함수로만 읽는다. 그래서 보충 4-3의 u6 ABL 한쪽 S-3과 결측 S-11이 u6 줄에서는 S-2로 바뀐다.
  - IND_LAS 두 파일(`u6_b5_{main,wide}_VB_IND_LAS.json`)도 고정 종류 대신 같은 쌍으로 읽게 바꿨다(`InputFile(..., field="controller")`). 4-2 종류 수(IND_LAS 242)는 `controller`에서 나온다.
  - 파일 머리의 `<제어기>.controller_tag` 메타와 최상위 `controller_tag`는 읽지 않는다. 접미사를 떼는 호출도 없다.
- **값 대응표**: `U6_CONTROLLER_TAGS`

  | controller | v5.controller_tag(436.8 모드) | 종류 |
  |---|---|---|
  | C2 | `final_C4G2_P3_LAS_K1` | ③ 켬(VB) |
  | ABL | `ABL_LAS_K1` | ABL |
  | IND | `IND` | IND |
  | IND_LAS | `IND_LAS` | IND_LAS |

- **동치 대안 확인(identifier_check.py)**
  - `u6_line_check`의 호출은 `get`, `get_path`, `isinstance`, `join`, `mode_tag`, `sorted`뿐이다. 접미사를 떼는 호출(`removesuffix`·`rstrip`·`endswith`·`split`·`replace`·`is_extend_start_tag`·`switch_base_tag`·정규식 등)은 0개다.
  - 규칙 문장을 그대로 옮긴 함수와 208개 조합(controller 8종 × tag 13종 × 모드 2)으로 대조했다. 차이는 0이다.
- **생산자 꼴 확인**: 생산자 코드를 읽어 확인했다. `v5_rerun.py`:498~528(레코드 `v5` 블록의 `controller_tag`)과 :586~599(파일 메타 `controller_tags`)다. 실제 출력으로는 시험하지 않았다(규칙상 금지).

### 2.3 모드 인자 `--tag-mode {4368,imua}`
- **근거**
  - rev26:42(모드 행), (f) :172
  - A형 규칙 초안 `v5paper_imua_rules_draft.md`:39 "436.8 원판 4.1 표에 `_IMUA`를 붙인 것"
- **구현**
  - `resume4368_judge.py`: 모든 하위 파서에 `--tag-mode`를 더했다(기본 `4368`). `main()`이 호출마다 `set_tag_mode()`로 정하므로 앞 호출의 imua가 다음 호출로 넘어가지 않는다. `mode_tag(tag)`는 imua일 때만 4.1 문자열 뒤에 `_IMUA`를 붙인다(떼지 않는다).
  - 모드를 적용한 곳(AST로 셈한 `mode_tag` 호출 6곳):
    - `kind_tag_problem`(보충 4-3 종류 표: r4-inputs·family-f·grid)
    - `u6_line_check`(R26-3)
    - `_tag_recompute_record`(R8-1 재계산)
    - `abl_line`(rev16 R16-3)
    - `_is_extend_start_split`(R11-3, 2곳)
  - `u3_judge_4368.py`: `--tag-mode`를 더했다. U-3 G-2의 기대 태그(`base.EXPECTED_TAGS[setting]`)에 `common.tag_in_mode`를 적용한다.
  - `judge4368_common.py`: `TAG_MODES`·`IMUA_TAG_SUFFIX`·`tag_in_mode`를 두었다. 시험에서 두 모듈의 값이 같은지 확인한다.
  - 모드는 출력 파일에 쓰지 않는다(시험으로 확인).
- **모드가 닿지 않는 곳(AST로 확인)**
  - `expected_harness_tag`: 호출처가 0인 기존 함수다.
  - `read_controller_tag`의 `T3_ALL_OFF_TAG`: 4.1 표가 아니다.
  - Chrono 행의 `_is_c4_off`: 하네스 묶음 밖이다.
  - 허용 목록 밖: `u3_judge_k1.judge_u6`(U-6 G-2 태그 표)와 03_src `is_extend_start_tag`. 확인 필요 2에 적었다.

### 2.4 RD-2: 봉인 목록 (경로 1)
- **근거**: rev26:111~118, (h) :174
- **구현**
  - `judge4368_common.SEALED_RULES`에 rev26을 27번째로 더했다. 파일 꼴 칸은 `{pinned_sha256, file_sha256, seal_file_sha256}`이고 `seal_report`가 만든다. `run_judge`를 쓰는 판정기 출력(`u3_judge`·`h6_judge`·`h8_noise_judge`·`stage1_judge`·`d1_judge`·`u9_judge`)에 칸이 생긴다.
  - `resume4368_judge.SEALED_REVISIONS`에도 rev26을 27번째로 더했다(`RULES_REV26_NAME/SHA256`). revisions 꼴 칸은 `{expected_sha256, seal_file_sha256, rules_file_sha256}`이고 모든 하위 명령 출력에 생긴다.
  - `u3_judge.json :: G-3.rules_seal`은 `--g3 h11.json`(resume4368_judge 출력)을 그대로 옮긴 것이다. 그래서 같은 칸이 함께 생긴다(시험으로 확인).
  - 판→sha 지도 `rules_rev13_to_rev25_sha256`에는 넣지 않았다. 새 최상위 키도 없다.
  - `rules_seal`이 없는 8개 출력의 도구(`resume_k1_family`, `t4h_replay`, `d1_select`, `r79_sensor_judge`, log_errors, sidecars, `u3_judge_k1`, h6 L1 참조)는 바꾸지 않았다.
- 봉인 실패 때의 `section` 문자열을 "original .. rev26 seals"로 고쳤다. 실패할 때만 출력에 나오는 문자열이다.

## 3. 경로 1 하위 명령별 입력·출력 경로 기준표 (5단계 실행본 꼴: cwd = 메인, 도구 = worktree)
| 단계(M4 실행본) | 입력 경로 해석 기준 | 출력에 적는 상대 경로 기준 | 도구 저장소(worktree)에서 읽는 것 → 2절 W와 대조 |
|---|---|---|---|
| head_check | `--root` 기본 ROOT = worktree(git만) | 인자 그대로 | HEAD·`git show <커밋>:<파일>`·`git diff` → W(HEAD·git 기록) ✓ |
| r4_inputs | `--root .`(cwd 메인) | `result_file` = 표의 상수 이름, `root` = `"."` | 없음 |
| key_map·item_list·reagg_items | 입력 없음 | — | 없음 |
| log_errors(python-dev 외부 도구) | 실행본 인자(cwd 상대) | 도구 몫 | 없음 |
| import_check | `--steps` cwd 상대 / `--root` 기본 worktree | 도구 몫(NT 정규화 대상) | 03_src·04_scripts 등 코드 모듈 색인 → W(코드) ✓ |
| appendix_a | `--root` 기본 worktree | — | 규칙 파일(원판 부록 A 34개) → W ✓ |
| overlap_steps | `--steps` cwd 상대 | 인자 그대로 | 없음 |
| sidecars(메인의 저장소 사본) | 실행본 인자(cwd 상대) | 도구 몫 | 없음 |
| family_table(`resume_k1_family.py`) | `--data-root .`(실행본 6번, 없으면 기본 ROOT = worktree) | 도구 몫 | 코드만 → W ✓ |
| anchor_map·record_check·k1_class·dg3_hash·keyset·grid_v0_sample·stroke_* ·ind_las·h12 | 실행본 인자(cwd 상대). T4h 폴더는 결과 파일 옆(cwd 상대) | 인자 문자열 그대로(`str(path)`) | gs·record-check의 `saturation_rule`·`extend_bound_rule` 코드 → W ✓ |
| h11 | `--h11-dir` cwd 상대, `--las-k1-dir`(실행본 5번, 기본 ROOT/las_k1 = worktree) | 인자 기준 | 없음(기본값은 실행본이 덮음) |
| x16_records(python-dev) | `--out-root` cwd 상대(기본 하위 폴더는 out-root에서) | out-root 기준 | Chrono 도구 코드, `02_params/rexome33.yaml` → W ✓ |
| h12_t4h_replay(`t4h_replay.py`) | 인자 cwd 상대 | 도구 몫 | 코드 → W ✓ |
| jp_reuse·r4_lists·grid_h10 | `--root .` | `repo_relative(path, root=".")` → 메인 기준 | `read_dg3_keys`는 `--root` 아래(메인) |
| family_f_trigger·family_f | `--grid-root .`, `--lines` cwd 상대 | 메인 기준 | 없음 |
| d1_judge(+ `d1_select`) | 인자 cwd 상대 | `*_4368`의 `repo_relative`는 ROOT = worktree 밖이라 대체 동작(인자 문자열 그대로) | `d1_select --rules` 기본값 = worktree `verif_matrix/d1_selection_rules*.md` → W(규칙 파일) ✓. 출력 `h2_select.json :: rules`(부록 A r5에서 NT) |
| u3_judge_k1·u3_judge | `--u3-dir`·`--v4-dir`·`--g3`·`--h1-d1` cwd 상대. settle 표는 기록 문자열 그대로(`Path(table)`: 절대면 그 경로, 상대면 cwd) | `repo_relative(path)` 대체 동작(인자 문자열 그대로) | `--rules-dir` 기본 = worktree `verif_matrix` → W ✓. `s9_settle_rejudge.DEFAULT_BASELINE` = worktree `s9/rev80/…` → W(`s9/rev80/*`) ✓ |
| u9_judge·h8_noise_judge·h6_judge·stage1_judge | 인자 cwd 상대 | `repo_relative` 대체 동작 | `r79_sensor_judge.py`·`r79_L3L4_final.py`·`paper_runs/scripts` 코드 → W ✓ |

- 결과 입력을 worktree 기준으로 푸는 기본값은 `h11 --las-k1-dir`와 `resume_k1_family.py --data-root` 둘뿐이다(rev26 2절 경로 1과 같다). 둘 다 5단계 실행본이 cwd 상대 값으로 덮는다.
- 그 밖에 worktree에서 읽는 것은 모두 2절 W(코드, 규칙 파일, `02_params`, `s9/rev80`, HEAD·git)다.
- 이 표는 인자 파서·기본값·`ROOT` 사용 줄(identifier_check.json의 `path_sites`)과 해당 함수를 읽어 만들었다. 실행으로 확인하지는 않았다.

## 4. 시험
- **실행 환경**: 인터프리터는 M4 실행본 `$Py`와 같은 `C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B -m pytest -q -p no:cacheprovider`이고, `PYTHONDONTWRITEBYTECODE=1`, `MKL_THREADING_LAYER=TBB`를 주었다. cwd는 worktree다.
- **기준선(변경 전 코드)**: 18개 파일, 675 통과, 6 건너뜀. 종료 0이다. 이 실행에 main 데이터를 읽는 시험 3개가 포함됐다(6절 공개 1).
- **변경 뒤 첫 전체 실행**: 713 통과, 1 실패, 6 건너뜀, 3 제외. 종료 1이다.
  - 실패: `test_resume4368_rev1.py::test_rev1_and_rev2_seal_check`. 봉인 집합에 rev26이 더해져 26판 집합과 달라졌다.
  - 이 시험의 기대 집합을 27판으로 고쳤다(허용 목록 시험 파일).
- **커밋 트리 최종 실행**: 714 통과, 6 건너뜀(pychrono 없음: `test_v5_resume_4368_chrono_rows.py` 3개, `test_v5_resume_4368_manifest_oc5.py` 3개. 기준선과 같은 6개), 3 제외. 종료 0이다. 제외한 3개는 아래다:
  - `test_chrono_rows_judge_4368.py::test_gs_batch_execution_path`
  - `test_chrono_rows_judge_4368.py::test_gs_batch_082117_execution_path`
  - `test_resume4368_rev11.py::test_the_gs_ba2da55_batch_stops_only_on_the_open_loop_row`
  - 셋 모두 main `07_results/S9`의 G-S 배치를 Chrono 판정기로 읽는다.
- **새·바뀐 시험(합성 고정물만)**
  - 위치: `test_resume4368_supplement4.py` 끝의 "rev26 (path 1)" 절, `test_resume4368_rev16.py` 봉인 목록, `test_resume4368_rev1.py` 봉인 집합. 새 파일은 만들지 않았다. 바뀐 파일을 허용 목록 안에 두기 위해서다.
  - **(e) 다섯 경우 → S-2**: 태그만 맞음 / controller만 맞음 / 둘 다 다름 / 하나 이상 없음(tag·controller·둘 다 세 꼴) / 표에 없는 controller 이름.
  - 추가 S-2 경우: 최상위 tag만 있음, `v5`는 있으나 tag 없음, `_TCL` 접미, 기준 태그만 있음, controller null.
  - 최상위 tag가 틀려도 `v5` 쌍이 맞으면 통과한다(정의대로 `v5`만 읽음).
  - **(e) 네 대응 쌍 통과**
  - **끝까지 도는 시험 1**: cwd를 입력 폴더 밖에 두고 `r4-inputs` main을 돌린다. 다섯 경우와 IND_LAS 파일의 controller 결측이 정확한 위치에서 S-2이고, 표지는 `S-2 (8 lines, supplement 4-3)`이며, 파일 머리 메타는 무시된다.
  - **끝까지 도는 시험 2**: 5단계 꼴(cwd = 입력 폴더, `--root .`)에서 종료 0, H-4 종류 수가 각 242, H-4 파일 집합이 같음을 확인한다.
  - **(f)**:
    - 인자 없이 `_IMUA` u6 줄과 `_IMUA` H-1 줄은 S-2다.
    - `--tag-mode imua`이면 전부 `_IMUA`인 입력 폴더가 종료 0이다.
    - 같은 폴더를 모드 없이 돌리거나, 접미 없는 폴더를 imua로 돌리면 모든 멈춤이 S-2다.
    - 모드는 출력에 쓰이지 않고, 다음 호출로 넘어가지 않는다.
    - ABL 판별, R8-1, `mode_tag(None)`, 잘못된 모드 값의 거부도 시험한다.
    - `u3_judge_4368 --tag-mode`의 기본값·선택지·값 일치를 시험한다.
  - **R26-2 칸**: 1.2 표 11칸을 둔다(정상, 각 표지, 세 표지 순서, 키 결측 셋, None·형 불일치, 빈 dict).
    - `ind-las` main을 cwd를 바꾼 채 끝까지 돌리는 시험 2건: 기록 완료 `[]` / `판독 불가 1`+`기록 상태 미정`. 둘 다 옛 키 집합에 새 세 키만 더해지고, 종료 코드는 그대로인지 본다.
    - adapter_defect일 때 종료 1이 그대로인지 본다.
  - **RD-2 (h)**:
    - revisions 꼴 칸의 세 sha가 봉인 값과 같고, 판→sha 지도에 없고, 새 최상위 키가 없다.
    - 파일 꼴 칸이 있고, `u3_judge_4368` 출력의 `rules_seal`과 `G-3.rules_seal`에 rev26 칸이 있다.
    - rev26 파일이 바뀌면 두 도구 모두 S-1이다.
- **기존 시험에서 바꾼 기대값(rev26이 정한 동작 변경)**: `test_resume4368_supplement4.py`에서 u6 ABL 한쪽 S-3 → S-2(2곳), 표에 없는 controller의 S-11 → S-2(1곳)로 바꿨다. 합성 IND_LAS 파일은 `controller`/`v5.controller_tag` 쌍으로 만들게 했다.
- **정적 점검**
  - ruff(프로젝트 설정 `line-length = 100`): 바뀐 파이썬 파일에서 E501 18건이 나왔다. 모두 `resume4368_judge.py`에 원래 있던 위반이다(932f1fb 판도 18건). 새 위반은 0건이다. 종료 1의 원인은 기존 위반뿐이다.
  - codespell: 처음에는 종료 65였는데, 모두 `ABL`(도메인 약어, "ablation")이었다. `--ignore-words-list abl`로 다시 돌려 종료 0이다.
  - `-W error` 컴파일 5개 파일은 통과했다.
- **생산자 꼴 미시험(다′)**: u6 레코드는 규칙 문장과 생산자 코드(`v5_rerun.py`)로 만든 합성 고정물이다. 실제 생산자 출력으로는 시험하지 않았다(rev26 3: 5단계 전 0회). 실제 꼴은 4′의 정체성 필드 덮음 점검과 5단계에서 처음 닿는다.

## 5. 확인 필요
1. **record-check의 ABL 한쪽 S-3이 남는다.** R26-3 문장은 rev26:41 "그 밖은 두 경로 모두 S-2"다. 그런데 `record-check`의 `abl_line`(rev16 R16-3, `resume4368_judge.py` `abl_line`·`_harness_record_row`)은 바꾸지 않았다. 이 함수는 4.2 기록 확인(ABL의 LAS 기대값 선택)이고 최상위 `controller_tag`를 먼저 읽는다. 그래서 controller ABL에 다른 태그가 붙은 합성 u6 줄은 경로 1에서 r4-inputs S-2와 record-check S-3이 함께 나온다. 436.8 데이터에서는 걸리지 않는다(규칙의 감사 실측). 이 S-3을 그대로 둘지, R26-3에 맞춰 바꿀지는 규칙 해석 문제다(작성자 control-expert 또는 사용자).
2. **`--tag-mode`가 닿지 않는 곳(A형 TA 몫)**: 아래 셋은 허용 목록 밖이라 imua 모드에서 A형 줄을 통과시키지 못할 수 있다. 4′ J-2 전에 TA 범위로 정해야 한다.
   - `u3_judge_k1.judge_u6`의 U-6 G-2 태그 표 `U6_TAGS`(`u3_judge.json u6.*.gates`)
   - 03_src `v5_options.is_extend_start_tag`의 `_IMUA` 처리(RD-9 ③ 수, J-P3)
   - Chrono 판정기
3. **R26-2 형 불일치**: 1.2는 "키가 없음"만 정한다. 구현은 정해진 형이 아닌 값도 없음으로 읽는다. 세 필드는 같은 함수가 만들므로 436.8 데이터에서는 차이가 없다.
4. **IND_LAS 파일의 종류 수 출처가 바뀌었다.** 전에는 파일 상수로 정했고, 지금은 R26-3 쌍의 `controller`에서 정한다. 그 파일의 줄이 모두 `controller` = IND_LAS이면 원 출력과 같다(규칙은 "436.8 입력의 쌍은 위 넷뿐"이라 적는다). 다르면 S-2와 함께 S-15 수 표지도 생긴다.
5. **`.gitattributes` 병합**: T26에는 master의 `-text` 6줄만 같은 바이트로 있고 주석 줄은 없다. master와 합칠 때 파일 끝에 충돌하거나 줄이 중복될 수 있으니 메인이 정리해야 한다.

## 6. 공개 (행위 그대로)
1. **금지 범위에 닿은 실행 1건.** 기준선 시험(변경 전 코드, 1회)에 아래 시험 3개가 들어 있었다. 각 시험은 Chrono 판정기(`04_scripts/02_chrono/chrono_rows_judge_4368.py`, 경로 1 Chrono 도구)를 main checkout의 `07_results/S9` G-S 배치에 돌렸다.
   - `test_chrono_rows_judge_4368.py::test_gs_batch_execution_path`: `batch_V5-RESUME-K1-GS_20261113_020211`
   - `test_chrono_rows_judge_4368.py::test_gs_batch_082117_execution_path`: `…_082117`
   - `test_resume4368_rev11.py::test_the_gs_ba2da55_batch_stops_only_on_the_open_loop_row`: `…_130358`
   - 시험 코드에 `MAIN_CHECKOUT` 절대 경로가 박혀 있었다. 세 `batch.json`이 있는 것은 `Test-Path`로 확인했다. 내용은 내가 열지 않았고, 출력은 pytest tmp에만 썼다.
   - 이 배치들은 2026-11-13 G-S 건조 실행 결과다. R2 `b9f5707` 저장 결과도, 경로 1 R4 하네스 판정 도구도 아니다. 그러나 지시문의 금지 목록에 `07_results`가 있으므로 그대로 공개한다.
   - 이후 두 번의 실행에서는 세 시험을 `--deselect`로 뺐다.
2. **worktree 루트를 Grep path로 1회 썼다.** path `C:\workspace\outrigger_control\.claude\worktrees\rev26-p1`, glob `{04_scripts/04_hydraulic/coupled/*.py,06_analysis/02_control/verif_matrix/scripts/*.py,05_tests/unit/test_*4368*.py}`. 결과는 "No matches found"(출력 없음)여서 블라인드 사본 이름은 나오지 않았다. 그 뒤로는 하위 폴더만 path로 썼다.
3. **저장소 루트 git 질의**
   - `git ls-files '*v5paper_imua_rules*'`, `'*u3_u6_rerun_rules*'`(이름 패턴; 출력은 해당 파일 이름뿐)
   - `git ls-tree -r --name-only master -- …/v5_resume_4368/rev26_fixed/`(이름 14개)
   - `git worktree list`
   - `git branch --list 'rev26*'`: `rev26-p2` 브랜치가 있다는 것만 보았다. 내용과 worktree는 열지 않았다.
   - `git diff 932f1fb master -- .gitattributes`
4. **연 파일**
   - `v5_resume_4368_rules_rev26.md` 전체(1~264행). 부록 A절 본문과 부록 B **절 설명**(249~263행: 파일 이름·수·sha)이 포함된다.
   - 원판 `v5_resume_4368_rules.md` 66~83·276~285행
   - `u3_u6_rerun_rules.md` 10~21행
   - `judge_932f1fb/_fixed/grade/r4_grade_compare_table.md` 30~119행
   - `judge_932f1fb/_fixed/run/run_judgement_path1_M4.ps1` 전체
   - `v5paper_imua_rules_draft.md`: Grep(`_IMUA|tag-mode|J-2`)에 걸린 줄만. 14~19행 수정 이력, 39~47행 A형 태그 표, 91~128행 일부(P-2·J-2·3.1·3.2·P-6·C-1 행)다.
   - worktree 코드:
     - `resume4368_judge.py`(여러 구간)
     - `judge4368_common.py`(1~147, 660~842행)
     - `u3_judge_4368.py`(1~120, 295~360, 520~630행)
     - `README_judges_4368.md`(1~30, 180~216행)
     - `v5_rerun.py` 375~414·490~599행
     - 시험 `test_resume4368_supplement4.py` 전체, `test_resume4368_rev16.py` 1~95행, `test_resume4368_rev1.py` 318~347·1215~1246행, `test_resume4368_rev11.py` 475~495행, `test_chrono_rows_judge_4368.py` 672~701행
   - Grep 결과 줄: worktree `04_scripts/04_hydraulic/coupled`, `05_tests/unit`(`test_*4368*.py`), `06_analysis/02_control/verif_matrix/scripts`, `04_scripts/03_control/s9`(`ROOT`·`DEFAULT_` 줄)
5. **부록 B 파일**(`rev26_excluded_fields_r5.json`과 폐기본 json들)은 열지 않았다. 바이트 복사(`git checkout master -- …`)와 sha256 계산(`sha256sum`, 값 `9e1831f5…` 확인)만 했다. `excl_fields_r5.py`도 열지 않았다(복사와 sha만).
6. **열지 않은 것**
   - 경로 2: `path2/`, `path2_v5c/`, `harness_path2` 출력, `rev26-p2` 브랜치·worktree, `run_judgement_path2_M4.ps1`
   - `judge_932f1fb/`의 결과 json
   - `v5_resume_4368_harness_judgement.md`
   - 판정 후 감사 문서
   - 블라인드 경로 전부
7. 판정 도구(경로 1 R4 하위 명령·`*_4368` 판정기)는 합성 고정물(pytest tmp)에만 돌렸다. `resume_k1`·`las_k1`·v5 저장 결과에는 0회다.

## 7. 산출·임시 파일
- `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\0d95027e-6012-4053-b99a-1e505935768c\scratchpad\python-rev26-p1\identifier_check.py`, `identifier_check.json`: 식별자 점검과 진리표(동치 대안 확인의 근거). 판정 근거라서 남겼다. 메인이 `rev26_impl\`로 옮기고 SHA256SUMS를 만들 것을 권한다.
- 같은 폴더의 `pytest_after.txt`(1 실패 판), `pytest_final.txt`(최종 714 통과): 시험 기록으로 남겼다.
- 같은 폴더의 `append_gitattributes.py`(`.gitattributes` 6줄 추가 스크립트), `commit_msg.txt`: 기록용으로 남겼다.
- 비교용 `base\` 사본은 지웠다.

## 8. 메모리 반영안
- `tool_tests_hardcoded_main_data.md`: worktree 시험도 절대 경로로 main `07_results`를 읽는다. 금지 범위 실행 전에 grep하고 `--deselect`한다.

사용한 스킬: 없음
