# 436.8 rev26 도구 보완: 경로 2 구현 기록 (T26 경로 2 몫)

- 작성: python-expert, 새 인스턴스(경로 2). 2026-11-26. 사용자 승인 2026-11-26.
- 규칙: `v5_resume_4368_rules_rev26.md`, sha256 `f6591836…` (master `c77b1dcf`에서 봉인). 근거로 쓴 절은 1절(정의 문장), 2절(도구 커밋·허용 파일·입력 기준 표), 3절, 4절, 5절 (a)(b)(e)(f)(g)(h)입니다. 원판과 다른 rev 본문은 열지 않았습니다. 원판 쪽 근거는 rev26 문장이 인용한 위치로만 적습니다.
- 의존성 점검: 이번 세션 스탬프가 있었고, 필요한 도구는 모두 있었습니다.
- 사용한 스킬: 없음

## 0. 결과 요약

- **커밋 `b587a841593275a3a6f64b5ebbac614777430a1b`**: 커밋 하나입니다.
  - 브랜치·worktree: `rev26-p2`, `C:\workspace\outrigger_control\.claude\worktrees\rev26-p2`
  - 기준: `932f1fb1724f074e4ee93a9c02193c7c840d13c4`
  - 설정: `core.autocrlf=true`. 잠그지 않았습니다.
- 정션·링크는 만들지 않았습니다. 커밋 뒤 `git status --porcelain`(ignored 포함)은 비어 있습니다.
- **시험: 353 통과, 0 실패.** 실데이터 시험 2개는 `-k`로 뺐습니다(3절).
- 인터프리터: 경로 2 실행본과 같은 `conda run -n dynamics-dev python -I -B`
- 기준 커밋(932f1fb)에서 같은 묶음: 329 통과. 이때 빼려던 2개가 실제로 돌았습니다(7절 공개).

## 1. 바뀐 파일 (`git diff --name-only 932f1fb..b587a84`)

모두 2절 허용 집합 안입니다. 03_src·02_params·04_scripts는 바꾸지 않았습니다.

| 파일 | 상태 | blob raw sha256 (b587a84) |
|---|---|---|
| `.gitattributes` | 7절 `-text` 6줄만 추가 (아래 주) | — |
| `path2/README.md` | 바뀜 | `a45c4e1c8f2fc247a52f7bc03e1193d55baddefdd72841958f2d90d9741e0f1d` |
| `path2/p2_4368.py` | 바뀜 | `4c89a3758983083b768a30ffef13990e5030212d9765df0d086a05d254a687d2` |
| `path2/p2_u3.py` | 바뀜 | `7ec2d245bcdf42890c78fc00010a774a666a163c29487f57516b3ca1b954911f` |
| `path2/p2_x16.py` | 바뀜 | `4bd6b19ba308d10f9c894de820ebee6f202e67bc36bff176220b88ea08b21d03` |
| `path2/test_p2_4368.py` | 바뀜 | `a965ab75f3b41059609ff0f5637463002f9312cea79cc55df24e5392cdd9c855` |
| `path2/test_p2_u3.py` | 바뀜 | `98d9d7f255dbc6c09b26a9f2659c01be11adbaf63624946ebd3adfe662b7d9a7` |
| `path2/test_rev26_p2.py` | **새 파일** | `3e8166b2132a530d4330f6c150fb594eb0c12f87fbd3e4c2df9ee8cc76ca2877` |
| `path2_v5c/README.md` | 바뀜 | `b5952a9acac1472a69cf10a1ef93ea124e340f91d0259677250f43b21a8a5daf` |
| `path2_v5c/p2v5c_common.py` | 바뀜 | `f15e75a4433a572f3a9ac5b34df71460a19bac6cbad422522dd2ff1abb8cb232` |
| `path2_v5c/p2v5c_grid.py` | 바뀜 | `0d9c6d0f661f9334c7b259eb83b661c45161b901c31cbea7699f09b6350abc44` |
| `path2_v5c/p2v5c_noise.py` | 바뀜 | `48fe9cb1b43d9fea02043f58381697fe60009fb8cfd52490b7fb6cff4aecf687` |
| `path2_v5c/p2v5c_stage1.py` | 바뀜 | `6b5a10841d6a61efd89173cfb7351616c31946490fe36c9a448d0e41c7fcad34` |
| `path2_v5c/test_p2v5c.py` | 바뀜 | `65537a8e3864213ae3f457a20273268e81ea6c240b1ba41b3e7b3eeff9e31cd6` |
| `path2/p2_v5j.py`, `test_p2_v5j.py`, `test_p2_x16.py` | 그대로 | `b815771d…` / `017d4327…` / `c7efdefd…` |
| `v5_resume_4368_rules_rev26.md` | 새 파일(master 복사) | `f6591836…` (= 봉인 값) |
| `v5_resume_4368_rules_rev26.sha256` | 새 파일(master 복사) | `e74aeca93554d65a5e2344142827fa5cafa054153feff7f9d64406233676b80b` |
| `v5_resume_4368/rev26_fixed/**` 14개 | 새 파일(master 복사) | `excl_fields_r5.py` `bee9eee7…`, `rev26_excluded_fields_r5.json` `9e1831f5…` (= 봉인 값) |

경로 앞의 `path2*`는 `06_analysis/02_control/verif_matrix/v5_resume_4368/` 아래이고, 규칙 파일은 `verif_matrix/` 아래입니다.

**`.gitattributes`**
- master의 rev26 줄 6개(`…rev26.md`, `.sha256`, `_seal_candidate_draft.md`, `rev26_fixed/**`, `judge_rev26_*/**`, `v5paper_imua_stats/**`)만 같은 바이트로 더했습니다.
- master에 있는 주석 줄 `# rev26 seal (2026-11-23)`은 "그 밖의 줄 diff 0"을 지키려고 넣지 않았습니다.

**규칙 파일 복사**
- `git checkout master -- <경로>`로 가져왔습니다. `git diff master -- <경로>`가 비어 있음(바이트 같음)을 확인했습니다.
- worktree에서 `check-attr text`는 `unset`, `ls-files --eol`은 `w/lf`입니다(`rev26_d_excluded_fields.json`만 i/crlf 폐기본).

## 2. 보완별 구현 기록 (3절)

### 2.1 R26-1 (경로 2, `p2_u3.py`)

**근거 정의 문장**
- rev26:39가 인용한 `u3_u6_rerun_rules.md`:19 "키 = v4 저장 파일의 `records[].id`(wrapper) 또는 `results[].key`(screen) 문자열 그대로"
- rev26:39 "파일 이름을 키·suite에 섞지 않는다"

**값 대응표**

| 꼴 | 932f1fb 짝 키 | T26 짝 키 | suite |
|---|---|---|---|
| screen `results[i]` | `<suite 또는 파일 stem>\|<key 또는 id>` | `results[].key` 그대로 | 기록의 `suite` 필드, 없으면 None (파일 이름 안 씀) |
| wrapper `records[i]` | `<suite 또는 stem>\|<id>` | `<suite>\|<id>` (suite는 기록 필드, 없으면 id만) | 기록 필드 |

**코드 위치**
- `_own_suite`·`records_loc`·`u3_pair_key`(213~239행)
- 연구 판별은 기록이 든 파일로 합니다(`graded`, 538행). 예전에는 `key.split("|",1)[1]`로 파일을 찾았습니다.
- U-6가 쓰는 wrapper 키 순서(id→case→key)는 그대로입니다.

**동치 대안 확인**
- 이름만 읽는 AST 점검: `test_d_and_w_sites_by_identifiers`
- 932f1fb판과의 대조
  - wrapper 고정물: 본문·결과가 932f1fb판과 같음(`test_r261_wrapper_keys_unchanged`)
  - screen 고정물: 932f1fb판에서는 `pairs` G-1이 나고 G-5가 비지만, T26에서는 짝이 맞고 G-5 1행이 나옴(`test_r261_screen_keys_pair_and_g5`)

### 2.2 R26-3 (`p2_4368.py` harness의 u6 줄, `p2_u3.py` U-6)

**근거 정의 문장**
- rev26:41. 원판 4.1 표(70~75행), 80행, 281행 S-2, `u3_u6_rerun_rules.md`:16을 인용합니다.

**값 대응표(짝 표 `U6_PAIR_TAGS`, 296행 근처)**

| controller | 짝 태그 |
|---|---|
| C2 | `final_C4G2_P3_LAS_K1` |
| ABL | `ABL_LAS_K1` |
| IND | `IND` |
| IND_LAS | `IND_LAS` |

- 읽는 것: 줄의 `controller`와 `v5.controller_tag`만 읽습니다.
- 통과 조건: 둘 다 있고, controller가 표의 이름이며, 태그가 짝 문자열과 그대로 같을 때만 통과입니다(`u6_pair_check`, 642행).
- 그 밖은 S-2입니다. 파일 머리 블록은 읽지 않고, 접미사를 떼지 않습니다.

**줄 단위 동작(harness)**
- 짝 실패 → S-2
  - by_setting 파일에서 controller가 없거나 모르는 이름일 때: 예전 S-11을 대신합니다.
  - ABL 한쪽만 맞을 때: 예전 R16-3 S-3을 대신합니다.
  - 태그가 없을 때: 예전 S-11을 대신합니다.
- 짝 통과 → 예전 그대로
  - 종류의 기대 태그 대조(예: IND_LAS 파일에 (IND, IND) 줄이면 S-2)와 ③ 대조를 그대로 합니다.
- u6 줄의 태그는 `v5.controller_tag`에서만 읽습니다(1269~1305행).

**U-6 동작(`p2_u3`)**
- 짝 실패는 S-2입니다(713행). 짝이 통과하면 열(column) 태그 G-2와 ③ G-2는 예전대로입니다.
- 종료 코드 2를 내는 코드에 S-2를 더했습니다(803행). 실행본 기대 종료 코드 `u3 = (0,1,2)` 안입니다.

**동치 대안 확인**
- `test_r263_pair_table`: 짝 표, 접미사를 붙이거나 뺀 태그, 파일 머리 블록을 읽지 않음
- 932f1fb판과 같은 고정물에서 네 쌍만 쓰면 harness·U-6 출력이 같음(`test_data_root_absent_*`)

### 2.3 모드 `--tag-mode {4368,imua}` (rev26:42)

**코드 위치**
- 최상위 인자: `p2_4368.py`, `p2_u3.py`, v5c `add_common_args`. 기본값은 `4368`입니다.
- `tag_matches`(p2_4368 632행; v5c common 384행에 같은 규칙. 두 정의가 같은지는 `test_tag_matches_same_as_core`가 표로 확인)

**동작**
- 4368: 기대 태그와 그대로 같아야 합니다.
- imua: 그대로 같거나 `기대 태그 + "_IMUA"`와 정확히 같으면 통과입니다.

**적용 자리**
- harness 기대 태그
- U-3 G-2
- U-6 R26-3 짝
- v5c `plate_check`(grid·family F·stage1)

**출력에 모드 키를 쓰지 않습니다.** 경로 2 출력의 `argv` 목록에는 인자가 주어졌을 때만 문자열로 남습니다(436.8 재판정은 주지 않음).

### 2.4 RD-2 봉인 목록 (rev26:111~118)

**동작**
- `check_seals`가 모든 하위 명령(chrono 포함)에서 rev26 `f6591836…`을 봅니다. 기준은 raw sha, LF, BOM 없음, `.sha256` 첫 토큰입니다. 틀리면 S-1입니다.
- 성공 출력의 `seals` 블록에 같은 이름의 칸 `v5_resume_4368_rules_rev26.md` = `{sha256, want, seal_file_sha, ok}`를 더합니다.
  - 대상 출력: `p2_4368` seal·harness·anchors·jp·chrono, `p2_x16` g3·c16·items, v5c 4개 명령
- 새 최상위 키는 없습니다. 판→sha 지도(`r4_rev13_25_sha256`)에도 넣지 않았습니다.
- `p2_u3`, `p2_v5j`, `p2_d1`은 성공 출력에 `seals` 블록이 없어 칸이 없습니다. 확인 자체는 공용 `check_seals`로 합니다.

**v5c**
- `rd2_union` 기준을 `RD2_REV26_SEALS`(27판)로 했습니다. `check_rev3`(rev3~25)는 그대로입니다.
- **`P2_CORE_SHA`를 `4c89a375…`로 다시 고정했습니다**(T26의 p2_4368 blob).

**시험**
- `test_rd2_rev26_cell_in_seals`, `test_rd2_rev26_mismatch_stops`, `test_rd2_no_new_top_level_keys`(출력 키 집합이 932f1fb와 같고 `seals`에 이 칸만 더해짐)
- v5c `TestRev26.test_rd2_union_and_seal_cell`

### 2.5 `--data-root` (2절 '입력 기준', rev26:71~79·81)

- 추가 위치: `p2_4368.py`, `p2_x16.py`, `p2_u3.py`, `p2v5c_common.py`(공통 인자)의 최상위 파서
- 기본값은 None, 즉 `--repo`입니다(`data_root_of`, p2_4368 619행).
- D 자리는 `data_root`, W 자리는 `repo`를 씁니다.
- 가독성을 위해 D 함수의 인자 이름을 `data_root`로 바꿨습니다(`rel_posix`는 `root`). 위치 인자라 호출 방식은 같습니다.
- `p2_x16 d1`은 넘기지 않습니다(`--repo`만 p2_d1로 전달).
- `p2_d1.py`, `p2_v5j.py`, `p2_t3k.py`는 바꾸지 않았습니다.

## 3. 하위 명령별 입력·출력 경로 기준 (경로 2 행만)

- 인자로 받은 파일·폴더는 그대로 엽니다. 상대 경로면 cwd 기준인데, 5단계 실행본은 모두 `$Repo\…` 절대 경로를 줍니다.
- "D"는 `--data-root`(없으면 `--repo`) 기준, "W"는 `--repo`(도구 checkout) 기준입니다.

| 도구·하위 명령 | 입력을 푸는 기준 | 출력에 적는 상대 경로 기준 | W 자리 (모두 2절 W 목록 안) |
|---|---|---|---|
| p2_4368 `seal` | — | — | 봉인(원판~rev25, rev26, 부록 A 34) |
| p2_4368 `harness` | 매니페스트 `path`·`stored`·`key_source`·`key_source_override` 상대값 = D. `--manifest`는 인자. 보충 4-4 `r4_input_check` 존재 확인 = D | `result_file`, `r4_input_check` 경로 = D (`rel_posix(…, data_root)`) | 봉인, HEAD(`head_check`), 03_src `v5_options.py`(`load_is_extend_start`) |
| p2_4368 `anchors` | `--v5-root` 기본값 = D/`06_analysis/03_hydraulic/coupled/v5`. `--h1`은 인자 | — (절대 경로 문자열 `h1`은 인자 그대로) | 봉인, HEAD |
| p2_4368 `jp` | `batch.json`의 `07_results/` 꼬리 재배치 = D (`jp_result_json`). `--batch`·`--shadow`는 인자 | — | 봉인, HEAD |
| p2_4368 `chrono` (5단계 안 돔) | `resolve_result`·`resolve_runner_row`·`runner_root` = D | — | 봉인(+rev16~21), 03_src, `chrono_rows_manifest.json` 기본값 = W |
| p2_4368 `oc5k`·`compare` | 인자만 | — | 봉인 |
| p2_4368 `openloop` (5단계 안 돔) | 인자 | — | `paper_runs/scripts/openloop_compare.py`, 02_params `rexome33.yaml` |
| p2_x16 `g3` | `--las-k1-dir` 기본값 = D/`06_analysis/02_control/v5_rerun/las_k1`. `--h11-dir`은 인자 | `none_file`·`compare_file` = D | 봉인, HEAD |
| p2_x16 `c16` | `--out-root`·`--identity-dir`·`--runners-dir` 인자 | `rows.*.folder` = D | 봉인, HEAD |
| p2_x16 `items` | 없음 | — | 봉인 |
| p2_x16 `d1` | `--`뒤 인자를 p2_d1에 그대로 넘김(`--repo` = 도구 checkout) | (p2_d1, D 없음) | 봉인, HEAD, d1 규칙 sha |
| p2_u3 | `--u3`·`--u6`·`--h1` 인자. 연구 키 파일 `s9/rev85/*` = D (`study_keys`). 정착 표 = D (`settle_v2_recount`) | G-5·G-6 목록 `result_file` = D (`rd7_row`) | 봉인, u3 규칙 sha, HEAD, 03_src |
| p2_v5j `u9` (안 바뀜) | 인자, T4h 관례 폴더(입력 파일 옆) | — | 봉인, u9 규칙 sha, HEAD, 03_src |
| v5c `stage1` | `--h9`·`--h10`·`--overlap-ta` 인자, T4h(입력 옆) | 결과 파일 열 `rel_file` = D | 봉인(27판), HEAD, 03_src, import(`--p2-dir` 기본 = 도구 폴더) |
| v5c `grid` | `--vb`·`--v0-*`·`--family-f` 인자 | 결과 파일 열 = D | 위와 같음 |
| v5c `noise` | 인자. dg3 키 원본 기본값 = D/`…/v5/dg3/dg3_v4_on.json` | 결과 파일 열 = D | 위와 같음, r79 판정기 스크립트(`JUDGE_REL`)·git log/diff |
| v5c `merge` | `--part` 인자 | — | 위와 같음 |

**도구 저장소 기준 자리가 2절 W와 같은지**
- 위 W 자리는 다음 묶음에 모두 들어갑니다.
  - 규칙 파일(`verif_matrix/*.md`·`.sha256`, 부록 A)
  - 03_src
  - 04_scripts·`paper_runs/scripts`·도구 폴더 코드(r79 판정기, import)
  - 02_params
  - `chrono_rows_manifest.json`
  - HEAD·git 기록
- D 자리는 2절 표의 함수 목록과 같습니다.
  - `rel_posix` 모든 호출처, `_rel_entry_path`, `r4_input_check`, `key_source_index`, `cmd_harness`, `cmd_anchors`, `jp_result_json`, `resolve_result`·`resolve_runner_row`·`runner_root`
  - g3·c16, `study_keys`·`settle_v2_recount`·`rd7_row`, `rel_file` 모든 호출처, `dg3_keys`
- **이름만 읽는 점검**: `test_d_and_w_sites_by_identifiers`가 7개 도구 파일을 AST로 읽어 확인합니다.
  - D 함수 14개의 모든 호출이 뿌리 인자로 `data_root`나 `data_root_of(args, repo)`를 받습니다.
  - W 함수 9개(`check_seals`, `check_chrono_seals`, `check_rev3`, `head_check`, `load_is_extend_start`, `yaml_vmax`, `run_judge`, `git_commits_since`, `git_diff_stat`)의 모든 호출이 `repo`를 받습니다.
  - 각 함수가 실제로 호출되는지도 확인합니다.
- **인자가 없을 때 = 932f1fb**(`git show 932f1fb:`판과 출력 대조, 변하는 키 `created`·`tool_sha256`·`argv`와 `seals` 블록만 뺌)
  - harness: `test_data_root_absent_harness_equals_932f1fb`. `--data-root <repo>`로 준 실행도 인자 없는 실행과 같음.
  - p2_u3 U-6, p2_x16 g3: `test_data_root_absent_u6_and_g3_equal_932f1fb`
  - v5c grid 본문 전체: `TestRev26.test_grid_data_root_file_column_and_932f1fb`
- **`--data-root`를 줄 때 D만 따라감**
  - `test_data_root_harness_d_sites`: 입력·stored·키 원본·`result_file`은 D, `v5_options.path`는 도구 checkout의 03_src
  - `test_data_root_anchors_jp_chrono`, `test_data_root_x16_and_u3_d_sites`, `test_data_root_settle_table`
  - v5c `test_noise_dg3_default_under_data_root`

## 4. 합성 고정물 시험: (e) 5건 + 네 대응 쌍, (f)

**(e) 고정물**: 모두 경로 2에서 S-2만 납니다(harness 줄 단위와 U-6 모두).

| 고정물 | controller | v5.controller_tag |
|---|---|---|
| 태그만 맞음 | IND | `final_C4G2_P3_LAS_K1` |
| controller만 맞음 | C2 | `final_C4G2_LAS_K1` |
| 둘 다 다름 | ABL | `final_C4G2_K1` |
| 하나 이상 없음 (1) | 없음 | 있음 |
| 하나 이상 없음 (2) | C2 | 없음 |
| 표에 없는 이름 | C3 | `final_C4G2_P3_LAS_K1` |

- 해당 시험: `test_r263_harness_five_fixtures_s2_four_pairs_pass`(줄마다 코드 목록이 정확히 `["S-2"]`), `test_r263_u6_five_fixtures_s2_four_pairs_pass`
- 네 대응 쌍(C2/ABL/IND는 by_setting 파일, IND_LAS는 IND_LAS 파일)은 두 시험 모두 그 줄에 멈춤이 없습니다.
- `test_r263_u3_main_exit_2_on_s2_only`: 쌍이 통과할 때 종료 0, S-2만 있을 때 종료 2와 `stop_codes ["S-2"]`입니다.
- `test_r263_pair_ok_in_the_other_column_stays_g2`: IND_LAS 열의 (IND, IND) 줄은 G-2 그대로입니다.

**(f) 모드**
- `test_tag_mode_harness_imua_suffix`
  - `_IMUA` 접미 V0 줄은 기본 모드에서 S-2, `--tag-mode imua`에서 멈춤 없음
  - u6 (ABL, `ABL_LAS_K1_IMUA`)도 같음
  - imua 실행 출력의 키 집합이 기본 실행과 같고, 어디에도 `tag_mode` 키가 없음
  - `_IMUAX`는 거부
- `test_tag_mode_u3_and_u6`, `test_tag_mode_argument`(허용 밖 값은 거부, 기본 `4368`)
- v5c `test_plate_check_tag_mode`

## 5. 시험·점검 결과

| 항목 | 명령·결과 |
|---|---|
| 단위 시험 | `conda run --no-capture-output -n dynamics-dev python -I -B -m pytest -q -p no:cacheprovider -k "not test_rev3_study_key_files_real and not test_dg3_key_source"`. 대상: `test_p2_4368`, `test_p2_u3`, `test_p2_x16`, `test_p2_v5j`, `test_p2_d1`, `test_p2_t3k`, `test_p2v5c`, `test_rev26_p2`. **353 passed, 2 deselected, 실패 0, skip 0, xfail 0** (커밋 후 HEAD b587a84에서 다시 돌림) |
| 기준선 (932f1fb, 같은 7개 파일) | 329 passed |
| 기존 시험을 고친 곳 | `test_r4_rd2_seal_list_26_sheets`: 27판, chrono 14판<br>`test_r4_b1_by_setting_u6_controller_and_h4_kind_counts`: IND_LAS 파일 줄을 (IND_LAS, IND_LAS)로, ABL 한쪽 맞음 3건을 S-3 대신 S-2로<br>`test_p2_u3` 인자 이름 `data_root=`<br>`test_p2v5c.test_rd2_union`: 27판<br>모두 rev26가 정한 동작 변경 때문입니다 |
| 뺀 시험 2개 | `test_rev3_study_key_files_real`: 작업 트리에 추적된 `s9/rev85` 연구 키 파일을 읽음<br>`test_dg3_key_source`: v5 dg3 실파일이 있으면 읽음<br>개발 시험은 합성 고정물로만 한다는 규칙 때문에 뺐습니다 |
| 커버리지 (dynamics-dev pytest-cov, 분기 포함) | p2_4368 85%, p2_u3 86%, p2_x16 92%, v5c common 87%, grid 90%, noise 52%, stage1 75% |
| 바뀐 줄 중 시험이 닿지 않은 줄 (검증 공백) | `p2_4368.py:1713,1726,1844` (Chrono 재배치·`runner_root`, 5단계에서 안 돔)<br>`p2_u3.py:561` (연구 D의 start_gap 표 재계산)<br>`p2v5c_noise.py:484,485,511` (`cmd_noise` 본문은 r79 판정기 하위 프로세스가 필요해 단위 시험이 없음)<br>이 줄들의 뿌리 인자는 AST 점검이 덮습니다 |
| ruff (python-dev 0.16, 프로젝트 `pyproject.toml`) | 새로 생긴 위반은 E501뿐입니다. 이 파일들은 원래 120자 줄 꼴입니다(예: p2_4368 기존 445건). 새 줄은 120자 이하로 맞췄습니다.<br>F(pyflakes) 0건. B905/B007은 모두 기존 줄이라 고치지 않았습니다 |
| codespell | `--ignore-words-list abl,pres`로 0건. 제외한 단어 `ABL`(제어기 이름), `pres`(기존 축약)는 오탐입니다 |
| 줄바꿈 | -text 파일은 원래 꼴 그대로입니다(p2_4368 LF, p2v5c_common·grid·stage1 CRLF, noise·test LF). 커밋 뒤 작업 트리 = blob |

## 6. 확인 필요 (고치지 않고 올림)

1. **RD-13 항목 문구가 낡았습니다.**
   - `p2_x16.RD13_ITEMS["H-4"]`에 "u6 controller ABL과 태그 ABL_LAS_K1 짝(하나만 맞으면 S-3)"이 남아 있습니다. R26-3 이후 실제로는 S-2입니다.
   - 이 목록과 sha는 `rd13_items.json`에 들어가 (d) 비교 대상입니다. 고치면 (d) 불일치가 나므로 그대로 두었습니다. 판정서에 적을지는 메인과 control-expert가 정합니다.
2. **imua 모드의 범위**
   - "imua에서만 `_IMUA` 허용"을 *더 받아들임*으로 읽었습니다. imua에서도 접미 없는 태그가 통과합니다.
   - 엄격한 해석("imua면 `_IMUA`만")이 맞으면 `tag_matches` 한 곳만 바꾸면 됩니다. TA(A형 규칙) 쪽 확인이 필요합니다.
3. **imua와 ③ 판정이 맞물리지 않습니다.**
   - T26의 03_src(932f1fb)에서는 `is_extend_start_tag("final_C4G2_P3_LAS_K1_IMUA")`가 거짓입니다.
   - 그래서 imua 모드에서도 VB·C2 `_IMUA` 줄은 ③ 대조(harness S-2, U-6 G-2), v5c J-P3 태그 범위(S-2)로 멈춥니다.
   - `p2_v5j`·`p2_d1`·`p2_t3k`에는 모드 인자가 없습니다(2절이 이 세 파일을 바꾸지 않는다고 정함). A형 처리는 T26 밖(TA)입니다.
4. **IND_LAS 파일 줄의 controller 값**
   - R4 작성자의 합성 시험은 IND_LAS 파일 줄을 (IND, IND_LAS)로 만들었습니다. `p2_u3`에도 IND_LAS 파일이면 열을 IND_LAS로 강제하는 코드가 있습니다.
   - rev26는 "436.8 입력의 쌍은 넷뿐(감사 실측)"이라고 하므로 실데이터 줄은 (IND_LAS, IND_LAS)일 것입니다.
   - 실제 줄이 (IND, IND_LAS)라면 242줄이 모두 S-2가 되어 (e) "diff 0"이 깨집니다. 저는 실데이터를 보지 않았습니다. 4′ 점검 몫입니다.
5. **u6 줄의 태그 읽기 경로가 바뀌었습니다.**
   - harness의 u6 줄 태그를 예전에는 최상위 `controller_tag`를 먼저 읽었습니다. 이제 R26-3대로 `v5.controller_tag`만 읽습니다.
   - 두 값이 다른 줄이 있으면 `bundles.H-4.tags` 집계((d) 대상)가 달라집니다. 감사 실측대로라면 없습니다.
6. **U-3 `counts`의 suite 열쇠**
   - screen 줄(연구 C·D)이 예전 파일 stem 대신 `null`로 집계됩니다.
   - `u3.json`은 (a)(b) 대상이고, 실행본 `Assert-U3Counts`는 값의 합(1,114)만 봅니다.
7. **`.gitattributes` 주석 줄**
   - master의 주석 줄 `# rev26 seal (2026-11-23)`은 넣지 않았습니다.
   - 경로 1 브랜치가 주석까지 넣었다면 합칠 때 충돌할 수 있습니다. 4′의 "`-text` 줄 추가뿐" 점검과 함께 메인이 정해 주십시오.

## 7. 공개 (행위 그대로)

**연 파일 (Read)**
- 규칙: `v5_resume_4368_rules_rev26.md` 전체(부록 A 문장 포함)
- 규칙이 인용한 근거: `v5paper_imua_stats/key_collide.json`
- 허용된 경로 2 실행본: `judge_932f1fb\_fixed\run\run_judgement_path2_M4.ps1`
- worktree 안의 경로 2 도구
  - `p2_4368.py` 대부분, `p2_u3.py`·`p2_x16.py` 전체, `p2v5c_common.py` 전체
  - `p2v5c_grid.py`·`p2v5c_noise.py`·`p2v5c_stage1.py` 일부, `p2_v5j.py`·`p2_d1.py`의 main 부분
- 시험 파일: `test_p2_u3.py` 전체, `test_p2_4368.py`·`test_p2_x16.py`·`test_p2v5c.py` 일부
- 두 README의 제목 목록과 일부, worktree `.gitattributes` 끝부분
- 03_src `v5_options.py`: `is_extend_start_tag` 주변만 Grep

**검색 path**
- Grep: worktree의 `path2`·`path2_v5c`·`path2_chrono`(`*.py`, p2_4368 import 여부), worktree `03_src/.../v5_options.py`, 제 Grep 결과 임시 파일
- Glob: worktree `path2*` 패턴(결과 없음), `judge_932f1fb\_fixed\run`(실행본 이름 찾기)
- 상위 폴더(저장소 루트, `06_analysis`, `02_control`, `verif_matrix`)는 검색 path로 쓰지 않았습니다.

**git 명령**
- `worktree list`, `ls .claude/worktrees`(이름 목록)
- `git log`/`ls-tree` master의 rev26 파일, `git diff 932f1fb master -- .gitattributes`
- worktree의 `git ls-files`: `v5_rerun/las_k1`·`resume_k1`은 추적 없음, `v5/las/las_T1.jsonl` 등은 이름만 확인
- `Test-Path`: worktree의 `v5/dg3/dg3_v4_on.json`(없음), `s9/rev85/fin_x426_C.json`(있음)

**열지 않은 것**
- 경로 1 코드·출력·브랜치(`verif_matrix\scripts\`, 경로 1 실행본, R4 허용 목록, `harness_path1`, `rev26-p1`), `04_scripts\04_hydraulic\coupled`
- `judge_932f1fb\` 결과 json, `v5_resume_4368_harness_judgement.md`, 판정 후 감사 문서
- 블라인드 경로 전부
- **부록 B**(`rev26_excluded_fields_r5.json`): 내용을 열지 않았습니다. `git checkout master --`로 바이트를 복사했고, sha256만 `sha256sum`과 blob 표로 계산했습니다.

**판정 도구를 436.8 저장 결과에 돌린 횟수: 0**
- 모든 실행은 pytest `tmp_path`의 합성 입력이었습니다.
- worktree에는 `resume_k1`·`las_k1`·`07_results`가 없습니다.
- 추적된 v5 파일(`las_T1.jsonl` 등)은 읽지 않았습니다. `anchors`는 합성 `--data-root`로만 돌렸습니다.
- 기존 시험의 harness 경로는 rules 묶음 이름을 쓸 때 보충 4-4로 worktree 안 436.8 결과 경로의 `is_file()`만 확인합니다(모두 없음, 내용은 읽지 않음).

**실데이터를 읽은 실행(공개)**
- 기준 커밋 932f1fb의 첫 시험 실행에서 `--deselect`(절대 node id)가 먹히지 않았습니다.
- 그래서 `test_rev3_study_key_files_real`이 worktree에 추적된 `06_analysis/02_control/s9/rev85/{finB2_x426b, fin_x426_C, fin_x426_D}.json`(연구 키 입력 파일)을 읽었습니다.
- 같은 실행에서 `test_dg3_key_source`도 돌았지만, worktree에 dg3 파일이 없어 존재 확인만 했습니다.
- 그 뒤 실행은 모두 `-k`로 뺐습니다.

**그 밖**
- 줄 길이 점검 스크립트가 커밋 대비 추가 줄의 길이를 재면서 `rev26_fixed/*.py`(봉인 복사본) 줄 길이도 셌습니다. 길이 숫자 말고 내용은 출력하지 않았습니다.
- 932f1fb판 비교용으로 `git show 932f1fb:`의 `p2_4368.py`, `p2_u3.py`, `p2_x16.py`, `p2_v5j.py`, `p2v5c_common.py`, `p2v5c_grid.py`를 시험 임시 폴더에 풀었습니다.
- 중간에 연결이 끊긴(ECONNRESET) 뒤 다시 시작했습니다. 재시작 시점에 worktree는 아직 없었고, 남은 제 프로세스도 없었습니다.
- scratchpad 하위 폴더 `python-rev26-p2`는 보고 전에 지웠습니다.

## 8. 메인 세션에 넘길 것

1. 경로 1 브랜치와 합쳐 T26을 만들어 주십시오.
   - 합친 뒤 `p2v5c_common.P2_CORE_SHA`(`4c89a375…`)가 T26의 `path2/p2_4368.py` blob과 같은지 확인이 필요합니다. 경로 1이 이 파일을 건드리지 않으면 같습니다.
2. 5단계 실행본 `$AllowListPath2`
   - 2절 4번의 T26 blob 값은 위 1절 표(b587a84 기준)와 같아야 합니다(합친 뒤 다시 계산).
   - 새 파일 `path2/test_rev26_p2.py`는 932f1fb의 15개 목록에 없습니다. 목록에 넣을지는 2절 실행본 규정을 따라 정해 주십시오(4′ "바뀐 파일 목록"에는 들어갑니다).
3. 6절 확인 필요 1~7을 4′ 점검 지시문에 넣어 주십시오. 특히 4(IND_LAS 줄의 controller 값)와 7(`.gitattributes` 주석 줄)입니다.

## 메모리 반영

- 새 파일 `tool_pytest_deselect_outside_rootdir.md`: `--rootdir` 밖 시험에 절대 node id로 `--deselect`를 주면 아무것도 빠지지 않습니다. `-k`를 쓰고 "N deselected"를 확인합니다.
- `MEMORY.md`에 한 줄을 더했습니다.
