# 436.8 경로 2 — v5 기준 원 규칙 등급 재집계 (H-6·H-8·H-9·H-10)

- 규칙: 436.8 원판 `../../v5_resume_4368_rules.md`(`9019b405…`), rev1(`d9094fda…`), rev2(`497e4614…`), rev3(`dad8dfa6…`), rev4(`7ea87a30…`), rev5(`452a8436…`, 커밋 31d543e), rev6(`809e5639…`, 커밋 d581df4), rev7(`e81f7d31…`, 커밋 292f9d2), rev8(`3ecafaaf…`, 봉인 파일 커밋 27c76f3), rev9(`4cf7843c…`, 봉인 파일 커밋 e5a2c19), rev10(`62a0bd8d…`, 봉인 파일 커밋 8b4ad93), rev11(`9bac4524…`, 봉인 파일 커밋 4312b8e), **rev12(`78f1f99b1bb27473d6e3317c58af195cc3b477829ca1439f390aeeaf32565140`, 봉인 파일 커밋 61f066f)**. 원 규칙은 원판 부록 A의 `v5_criteria.md` + 개정 1~12b다.
  - **R4 판(2026-11-16)**: R4 공통 블록(sha256 `e451f067db9787c9a8a45b7fc2f3e711970a914b29bc089b37bd94414d259800`) RD-2의 봉인 목록 26판(원판 + rev1~rev25, rev25 `c0b778fd…`)을 확인한다. 아래 "R4 반영" 절.
  - 실행할 때마다 두 곳에서 확인한다.
    - `p2_4368.check_seals(r4=True)`: 원판~rev25(`6139bb2` 판 `51a0e7cc…`), 부록 A, R2-9·R3-F4 CRLF 정규화.
    - 이 폴더의 `check_rev3`: rev3~rev25의 raw sha가 코드 봉인 값(`RD2_SEALS`)과 `.sha256` 기록 첫 값 둘 다와 같은지, LF·BOM 없음.
    - 두 목록을 합친 것이 RD-2의 26판과 정확히 같아야 한다(`rd2_union`: 빠진 판, 다른 sha로 확인한 판이 없어야 함).
  - 어긋나거나 `.sha256`이 없으면 종료 2(S-1)다(rev7 R7-7, rev8 R8-4, rev9 R9-8, rev10 R10-3, rev11 R11-7, rev12 R12-6, R4 RD-2 봉인 확인).
- 작성자: terramechanics-expert(경로 2, 사용자 결정 2026-11-13). 경로 1 도구를 만들거나 고친 적이 없다. 읽은 것은 아래 "독립성 공개"에 적었다.
  - R4 판(2-terra 몫)은 앞 작성자의 맥락을 받지 않은 새 작성자(terramechanics-expert의 새 실행)가 R4 지시문(경로 2-terra)과 보충 1·2, 보충 2판(보충 3), 보충 3판(보충 4), 보충 4판(보충 5), 보충 5판(보충 6)만으로 고쳤다. 읽은 것은 "독립성 공개 — R4 작성자" 절.
- 환경: `conda run -n dynamics-dev python -I -B <도구> ...`. 쓰는 것은 표준 라이브러리, numpy, scipy, 그리고 git(`log`·`rev-parse` 조회만)이다.
- 공통 CLI:
  - 인자: `--repo`, `--out <JSON>`, `--p2-dir`, `--allow-import-sha`, `--expect-head <M4 40자리>`(필수, R4 RD-1 5: `git rev-parse HEAD`와 다르면 S-12, 판정 안 함).
  - `noise` 전용 `--dg3-key-source <파일>`: dg3 대체 키 원본(기본 `<repo>/06_analysis/03_hydraulic/coupled/v5/dg3/dg3_v4_on.json`). sha256이 rev1 부록 B 값(`5f912ca0…`)과 다르면 S-11로 판정하지 않는다(보충 2-1·3-2).
  - `grid` 전용 `--family-f <resume_k1/h9_family_F.jsonl>`(필수, 보충 4-4·4-5)와 `--v0-stored <stem>=<…/c4g2_only/grid/<stem>.json>` 네 개(보충 4-4). 없거나 이름이 다르면 S-15.
  - 종료 코드: 0(이상 없음), 1(실패 또는 판정 불가), 2(멈춤 H-*·S-*·P-*, 규칙 sha 불일치, import sha 불일치 `P2-SHA`), 3(도구 오류).
  - `grid`의 보충 5 격자 항(보충 6-4): 멈춤 표지 `H-10`이 붙으면 종료 2다. FAULT 행·판정 불가 행·짝 출처 판정 불가·적용 조건 판정 불가는 수와 목록(`grid.grid_records`, `grid.supplement6_inputs`)으로만 내고 종료 코드와 `grades_436_8`에 넣지 않는다(그 등급은 판정서가 정한다). 그 밖 격자 항목(J-P3·J9·J11·m2_law·태그·S-15 등)은 위 규칙대로 종료 코드에 들어간다.
  - 적용 조건과 (나) 표 `applicable`의 세 값은 JSON `true` / `false` / 문자열 `"undecidable"`이다(보충 6-3). `null`은 쓰지 않는다.
  - stdout 마지막 줄은 ASCII JSON(`tool_sha256`, `common_sha256`, `status`, `exit`, `out_sha256`, `stop_codes`)이다.
- `.gitattributes`에서 이 폴더 전체를 `-text`로 둔다(패턴 `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_v5c/* -text`. 줄 번호는 다른 줄이 더해지면 바뀌므로 적지 않는다). 저장소 blob 바이트가 그대로 작업본이 되고, 도구 sha는 그 바이트 기준이다. 줄바꿈은 파일마다 다르다: `p2v5c_common.py`·`p2v5c_grid.py`·`p2v5c_stage1.py`는 CRLF, `p2v5c_noise.py`·`test_p2v5c.py`·이 README는 LF다. 고칠 때 각 파일의 줄바꿈을 그대로 둔다.

## import (복사하지 않음, 메인 세션 결정 2026-11-13)

J 항목(R3-C3~C8, R4-C5의 `values.case_floor_deg`로 정하는 J3 바닥 각)은 dynamics-expert 파일을 경로로 import한다. 그 파일은 고치지 않는다.
- 찾는 순서: `--p2-dir` → `../path2` → dynamics-expert worktree `agent-a2e81c57365f0d7bb`.
- sha가 다르면 종료 2(`P2-SHA`)다.

| 파일 | 고정 sha256 | 판 | 쓰는 것 |
|---|---|---|---|
| `p2_v5j.py` | `b815771dcaee69f5b474a7a6328f7699631d4c69309a973314a0ba3eaf06ecb8` | **R4 보충 3 판**(2-dyn 커밋 `2aa0a40`: `j11_item(setting_required=True)`, 보충 3-6; 2-dyn `8824499`·`6139bb2`에서도 바뀌지 않음, blob = 작업본 확인). 앞 판 R4 판 `4a036b00…`(`da1e00e`). R4에서 이 폴더가 더 쓰는 것: `j11_item`(RD-10, `setting=` 인자, 격자 run은 `setting_required=True`), `apply_j11`, `jp3`의 `tag=` 인자와 RD-8 판정 불가, `breach_reads_input`(= `p2_4368.breach_reads_input`), `t4h_convention_dirs`. 앞 판: 사용자 결정 24 판 `69d0e747…`(dynamics-expert 커밋 `e6971e5`, 병합 `66dfe09`). `rod_reading_lookup`이 `t4h_file` 키의 값이 None·문자열 아님·빈 값이면 `bad_t4h_file`(S-2)을 낸다. 앞 판: rev11 `582fa93` `e5d769b9…`(R11-2 `t4h_convention_dirs`·`t4h_places`·`rod_reading_lookup` 추가, rev12에서 바뀌지 않음), rev5·rev6 `d49068e` `5772624c…`(rev7~rev10에서 바뀌지 않음) | `judge_pair`(M-3: LS J11 n_late > 0 → stop, 이 도구의 L-e로 이어짐), `j_values`, `jp3`, `nrev_max_by_row`, `pair_key`, `row_key`, `t4h_places`, `rod_reading_lookup`(rev11 R11-2), `tag_of`, `is_event`. `rod_reading_from_t4h`는 rev11 판부터 이 폴더가 쓰지 않는다 |
| `p2_4368.py`(`p2_v5j.core`) | `51a0e7ccca2a6cbd3abfdf0c09d27fb03eac6985c31954e0b526c075ceba12e6` | **`6139bb2` 판**(2-dyn, 사용자 결정 129 격자 태그; blob = 작업본 확인). 이 폴더가 쓰는 것: `check_seals(r4=True)` 26판(RD-2), `head_check`(RD-1 5), `breach_reads_format`·`breach_reads_input`(RD-8), `APPENDIX_B`(dg3 키 원본 sha), `bundle_key`(RD-7 3 정렬). 앞 판: 보충 4 판 `76d561cc…`(`8824499`), 보충 3 판 `dd3f266e…`(`2aa0a40`), R4 판 `92f6e0d4…`(`da1e00e`), 그 앞 `0ccc5186…` = b9f5707 Chrono 판정 뒤 판(dynamics-expert 브랜치 `z4372-p2chrono`: `chrono`가 C-7a·C-7b를 열린 루프로 읽음, V0 열린 루프의 `v5_hydraulics` 블록 없음을 정상으로 봄, probe 행에 O-C5 본 행 블록을 적용하지 않음. 결정 19·2026-11-14). 이 폴더가 쓰는 함수는 바뀌지 않았다. 앞 판: 결정 19 `c969b57` `424e12f9…`, rev12 `6d41462` `a948d9a1…`, rev11 `582fa93` `a8c625bf…`, rev10 `a9594dc` `6e297ea3…`, rev9 `b0d6382` `7d764a80…`, rev8 `fd9bb68` `bebed9f1…`, rev7 `69b563f` `e033ca4b…`, `d49068e` `dc631509…` | `check_seals`, `load_is_extend_start`, `Findings`, `t_ge/t_lt/t_gt`, `num`, `dig`, `read_jsonl`, `F_MIN_N` |

- 이 폴더의 rev7 판(c6a1b47)은 고정값 `dc631509…`였고, 이 브랜치에 dynamics-expert rev7 판(`69b563f`, `e033ca4b…`)이 병합된 뒤로는 맞지 않았다(`--allow-import-sha` 없이 실행하면 `P2-SHA` 멈춤). rev8 판에서 `bebed9f1…`로 맞췄다. 그 사이에 436.8 본 결과를 낸 적은 없다(R8-0).

## 도구와 sha256 (R4 보충 6 판, 2026-11-16, 이 폴더 커밋 전 작업본 바이트 = blob, `-text`)

| 도구 | 묶음 | R4 보충 6 판 sha256 | 앞 판: 보충 5 판(`f3bd686`) / 보충 4 판(`8130954`) / 보충 3 판(`e268b26`) |
|---|---|---|---|
| `p2v5c_common.py` | 공통 | `6640cc93d58a3eafe875e7b890472ac68263a31f511ea9d8f18123f69476fa82` | `c499e36f…` / `6e46600e…` / `8785db56…` |
| `p2v5c_stage1.py stage1`·`merge` | H-10, H-9(main·pressure_only), RD 묶음 합치기 | `d49cf4e617eb55283b68907524e56c6bd6659a93c656a9280ad0d24fe3421996`(보충 4 판부터 같음) | `d49cf4e6…` / `d49cf4e6…` / `67f3eaf6…` |
| `p2v5c_grid.py grid` | H-9(격자 768, 계열 𝓕 R-1~R-4, 보충 5·6 격자 항) | `88e54e3438b145c2f6459e8fa1ea61acf819e1ae7f93311276216137cc476388` | `874fc5fb…` / `162f55b8…` / `863cbe83…` |
| `p2v5c_noise.py noise` | H-6, H-8 | `7fa4153fe254d0d59d2f4dbb94b543f9235b6b76adea071ee637b16a73a112a1`(보충 3 판부터 같음) | `7fa4153f…` / `7fa4153f…` / `7fa4153f…` |
| `test_p2v5c.py` | 자체 시험 48개(보충 6 시험 1개 추가, 고정 sha 시험 `TestImports.test_pinned_sha` 포함) | `4793f54b31bb94cf6f1f3b64bc217efef998a08de543a025be7fddf5436fbb37` | `f1a026d2…`(47) / `1e2b7ce6…`(46) / `cdd4a48e…`(45) |
- `path2/` 고정값: `P2_V5J_SHA` `b815771d…`(그대로), `P2_CORE_SHA` `51a0e7cc…`(2-dyn `6139bb2` blob과 같음, 이 판에서 재고정).

- 실행 기록의 `common_sha256`과 세 도구의 `tool_sha256`으로 판을 가른다. 판정에는 R4 blob과 같은 도구만 쓴다(RD-1 2).

### 앞 판 표 (rev12 판 + 사용자 결정 24·19, 기록)

| 도구 | 묶음 | sha256 | rev11 판 |
|---|---|---|---|
| `p2v5c_common.py` | 공통 | `86e922f1e6721e098204e3eff686e20907ea984b393659d4515f66c46a402247` | `P2_CORE_SHA`만 `0ccc5186…`으로 바꿈(z4372-p2chrono). 그 전 결정 19 반영 `84d9c10b…`(`P2_CORE_SHA` `424e12f9…`). 그 전 결정 24 판 `1ae2d2c2…`. rev11 판 `122c2054…`(rev12 봉인 확인, `P2_CORE_SHA` `a948d9a1…`, `jp3_rod_input`·`strip_jp3`·`t4h_input_error` 추가). 결정 24 반영 전 rev12 판 `04793dbe…`(`P2_V5J_SHA` `e5d769b9…`, 이름 아닌 값을 자체 판단 `unreadable_name`으로 셈) |
| `p2v5c_stage1.py stage1` | H-10, H-9(main·pressure_only) | `c50495d255213d604efee8768ca74b6a5d8fe8ab2dece172c6b881897d15a42f` | `55e70931…`(R12-1: S-2 줄의 J-P3 판정 안 함, 이름 아닌 `t4h_file` 값도 S-2) |
| `p2v5c_grid.py grid` | H-9(격자 768, V0 짝, 계열 𝓕) | `762100a56ab09e10ef24a42a1caa626b79ebe266fadd95cbd1c7d608f7cabeb1` | 결정 19 반영(`run_tag_view`: run 태그가 없으면 job 기록 `results[i]` 태그). 그 전 rev12 판 `c2a74931…`(R12-1 T4h 찾기, `--t4h-root`). rev11 판 `4100dbdc…` |
| `p2v5c_noise.py noise` | H-6, H-8 | `11ee8d1562b515eb27493fadbb049ec50f9c5a42f8dc65d93e7c80b1196ee519` | `4e4e174f…`(R12-1 T4h 찾기, `--t4h-root`, R12-3 `--git-at-start` 필수) |
| `test_p2v5c.py` | 자체 시험 33개 | `677f4ac32d43dcee6010888fbbe03574c8bbc6bc63cac58a4b14a178cce7c28e` | `7a6ca870…`(29개). 더한 것: rev12 봉인 단언, `test_r121_grid_t4h`, `test_r121_jp3_rod_input`(결정 24: None·숫자·빈 문자열 = `bad_t4h_file` S-2), `test_r123_git_at_start_required`, `test_r81_grid_tag_from_job`(결정 19). 그 전 `9613d612…`(32개), `5fe467cf…` |

- 실행 기록의 `common_sha256`과 세 도구의 `tool_sha256`으로 판을 가른다. 네 파일 모두 rev11 판과 다르다.

## R4 반영 (2-terra 몫, 2026-11-16)

근거: R4 공통 블록(sha256 `e451f067…`, 지시문 머리 줄과 실제 표지 사이 바이트가 같음을 확인), 지시문 2-terra 몫, 보충 1(sha256 `8736f68d…`)·보충 2(sha256 `a9a15a13…`). 규칙 절을 새로 열지 않았다.

| 블록·보충 | 반영 | 함수 |
|---|---|---|
| RD-2 봉인 26판 | `RD2_SEALS`(원판~rev25, 블록 표 값). `check_rev3`는 rev3~rev25. `p2_4368.check_seals(r4=True)`와 합친 목록이 26판과 같아야 하고(`rd2_union`), 아니면 S-1 | `common.RD2_SEALS`, `common.rd2_union`, `common.run_main` |
| RD-1 5 HEAD | 모든 하위 명령에 `--expect-head <M4 40자리>` 필수. `git rev-parse HEAD`와 다르거나 40자리 hex가 아니면 S-12, 아무것도 판정하지 않음(`p2_4368.head_check`) | `common.add_common_args`, `common.run_main` |
| 재고정(지시문 2-terra 순서, rev19:93) | `P2_V5J_SHA` = `b815771d…`(`2aa0a40` 이후 그대로), `P2_CORE_SHA` = `51a0e7cc…`(2-dyn `6139bb2`, 위 import 표). 보충 4·5 판(`8130954`·`f3bd686`)은 `76d561cc…`, 보충 3 판(`e268b26`)은 `b815771d…`·`dd3f266e…`, R4 판(`41f99a4`)은 `4a036b00…`·`92f6e0d4…` | `common.import_record` |
| RD-7 J-P3 위반 목록 | 묶음 H-6(`h6_dg3_v4on.json`의 `results[i]`), H-8(`h8_noise_VB.json`에서 dg3 대체 135키를 뺀 `results[i]` + `h8_seedext_VB.json`), H-9(`h9_stage1.jsonl`의 ③ 켬 줄 + `h9_grid/grid_*.json` 768 run), H-10(`h10_reuse_rerun.jsonl`의 ③ 켬 줄 전부, U-9 VB 포함). J-P3 결과 `H-7`(RD-8 형식 통과, 합 ≥ 1)인 줄·run의 `breach_reads` ≥ 1 다리마다 한 줄. 열: `bundle`, `file`, `position`, `leg`, `key`, `setting`, `breach_reads`, `min_gap_bar`, `first_breach_t_s`. H-1·H-3·H-4·family run은 넣지 않음 | `common.jp3_rows`, `common.RdCounter`, `grid.cmd_grid`, `noise.run_checks`, `stage1.rd_scan` |
| RD-7 J11 목록 | 같은 네 묶음. `p2_v5j.j11_item`의 `list`(멈춤 설정 VB·LS1~LS4, 실제 대체 다리 `n_late_fallback_by_leg` > 0). 열: `bundle`, `file`, `position`, `leg`, `key`, `setting`, `n_late_fallback_by_leg`, `marker`(`H-7` / `L-e`) | `common.j11_rows` |
| RD-7 3 표기·정렬 | 위치 `line N`(물리 줄 번호, 빈 줄 셈) / `results[i]` / `results[i].runs[j]`, 결과 파일은 저장소 루트 상대 `/` 경로, 정수는 JSON 정수, 실수는 기록 수 그대로. 정렬 묶음(보충 3-5: `p2_4368.bundle_key`, `H-n`의 숫자 순, `H-9` < `H-10`) → 파일(문자열) → 위치(수) → 다리(FL, FR, RL, RR) | `common.read_jsonl_numbered`, `common.rel_file`, `common.rd7_sort(rows, bundle_key)`, `RdCounter(bundle_key)` |
| RD-7 1 표지 | J-P3 위반 = "멈춤 H-7", J11 = "멈춤 H-7"(VB) / "L-e"(LS). 등급으로 바꾸지 않음 | `common.rd7_markers` |
| RD-8 | `p2_v5j.jp3`가 낸 판정 불가(형식 결함, RD-7 3 최상위 사본 불일치)를 이 폴더가 통과로 바꾸지 않는다. noise·grid는 앞 판까지 `undecidable` 결과를 발견에 넣지 않았다 → 이제 판정 불가로 넣고 묶음마다 `RD-8.format`·`top_level_mismatch` 수를 적는다 | `common.jp3_apply`, `RdCounter.jp3_result` |
| RD-9 | 묶음마다 ③ 켬 줄·run 수(행 태그, `is_extend_start_tag`). H-6·H-8·H-10은 각 도구에서 0이면 S-8. H-9는 stage1(main·pressure_only)과 grid의 합으로 `merge`가 S-8을 정한다. family run은 입력이 아니므로 들어가지 않는다 | `RdCounter.line`, `stage1.cmd_merge` |
| RD-10 | 묶음마다 J11 `undecidable`(멈춤 설정의 블록 결측·대체 다리 값 결측) 수와 `input_missing`(기록 설정의 블록 결측) 수 | `RdCounter.j11_result` |
| RD-13 | 묶음 H-6·H-8·H-9·H-10의 항목 목록(항목, 근거 조항, 구분)과 sha256(정렬 키·`,`·`:` 구분 UTF-8 JSON). 넘겨받지 않은 앞 판 정의의 근거 조항은 이 폴더 코드 주석·README 인용에서 옮겼다 | `common.RD13_ITEMS`, `common.rd13_lists` |
| 보충 2-1 | H-8 ③ 켬 줄(`h8_noise_VB.json`·`h8_seedext_VB.json`)이 J-P3·J11 목록 대상. V0 줄은 J-P3 해당 없음, J11 기록. dg3 대체 135키(키 원본 `v5/dg3/dg3_v4_on.json`, sha = rev1 부록 B `5f912ca0…`, 다르면 S-11)의 H-8 VB 줄은 H-8에서 판정하지 않고(J-P3·J9·m2_law·J11 모두) H-6 줄로 판정한다. 키 원본 키 집합 ≠ H-6 키 집합이면 S-15 | `noise.dg3_keys`, `noise.run_checks(skip=)` |
| 보충 2-2 | 격자 768 run마다 J11 = `j11_item(run, setting=results[i].v5_setting, setting_required=True)`, J-P3 = `jp3(run, …, tag=<results[i].controller_tag>)`(사용자 결정 129로 run 자체 태그를 먼저 쓰던 앞 판 동작은 뺐다. 태그 없음 = J-P3 해당 없음 + S-2, 판 대조 S-11) | `grid.cmd_grid`, `grid.job_tag`, `grid.runs_indexed` |
| 보충 3-1 | H-8 RD-9 수 = H-8 결과 파일의 ③ 켬 줄 전부(dg3 대체 줄 포함), S-8은 이 수로 판단. 목록에서 뺀 줄 수는 `R4.H-8_dg3_substituted`에 기록(앞 판 구현 그대로) | `noise.run_checks`, `noise.cmd_noise` |
| 보충 3-2 | dg3 대체 키 제외는 `h8_noise_VB.json` 줄에만. seedext 줄은 키가 같아도 seedext 줄로 판정·기록(앞 판 구현 그대로; 저장 키 원본에서 dg3 ∩ seedext 키는 0) | `noise.cmd_noise` |
| 보충 3-3(사용자 결정 126) | `min_gap_bar`·`first_breach_t_s`의 그 다리 원소를 계산 없이 옮긴다. 없음·수 아님·비유한 = `null`. 앞 판의 `min_gap_Pa` ÷ 10⁵ 대체 경로를 뺐다 | `common.jp3_rows` |
| 보충 3-4 | H-10 = `h10_reuse_rerun.jsonl` 모든 줄. J-P3는 ③ 켬 태그 줄 전부, J11은 `job.setting` ∈ {VB, LS1~LS4} 줄 전부(U-9 VB 포함). 앞 판 구현 그대로 | `stage1.rd_scan` |
| 보충 3-5 | `bundle` 열 = `H-6`·`H-8`·`H-9`·`H-10`, 정렬은 `p2_4368.bundle_key`(숫자 순). 앞 판의 자체 순서표를 뺐다 | `common.rd7_sort` |
| 보충 3-6 | 격자 run 설정은 `results[i].v5_setting`만. 앞 판의 파일 `meta.v5_setting` 대체를 뺐다. 없으면 `setting` 열 `null`, J11 판정 불가(`j11_item(setting_required=True)`) | `grid.cmd_grid` |
| 보충 3-7 | 계열 판별의 `@` 토큰: 이 폴더는 계열(S-6 목록)을 내지 않으므로 바꿀 것 없음(`path2/` 몫) | – |
| 보충 4-1·4-2 | 입력은 R2 원 결과 파일 그대로. 이 폴더 입력: `RK/h9_stage1.jsonl`, `RK/h10_reuse_rerun.jsonl`, `RK/h9_grid/` 4개, `RK/h9_grid_v0_sample/` 4개, `RK/h9_family_F.jsonl`, `RK/h6_dg3_v4on.json`, `RK/h8_` 4개, 키 원본 `V5/dg3/dg3_v4_on.json`, V0 저장 격자 4개 | 각 도구 인자 |
| 보충 4-3 | 줄마다 판: `h10_reuse_rerun.jsonl`은 `job.setting`, `h9_family_F.jsonl`은 최상위 `setting`(VB·LS1~LS4 = ③ 켬, 그 밖 = ③ 없음). `h9_stage1.jsonl`은 파일 하나의 판(③ 없음). 판별 필드 없음(null·빈 값) = S-11, 태그 없음 = S-11, 판의 기대 태그(`final_C4G2_P3_LAS_K1` / `final_C4G2_LAS_K1`)와 다르면 S-2. `h10`·`h9_stage1` 판별 수는 `R4.supplement_4-3_plates`에 기록. ③ 켬 판별(RD-9, J-P3 목록)은 앞 판대로 태그로 한다 | `common.plate_check`, `stage1.cmd_stage1`, `grid.family_f_rule` |
| 보충 4-4(이 폴더 몫) | V0 저장 격자 4개(`--v0-stored`, 파일 이름 `<stem>.json`, `*_off.json` 아님)와 `h9_family_F.jsonl`(`--family-f`, 필수)이 있어야 한다. 없거나 이름이 다르면 S-15. 하네스 입력 42개 확인은 `path2/` 몫 | `grid.input_files_check` |
| 보충 4-5 | 계열 𝓕 R-1~R-4를 늘 낸다. 입력은 `h9_family_F.jsonl` 64줄(`key`, `setting`, `offset_s`, `event`, `gates`, `fault_events`, `final_phase`, `controller_tag`), 짝 단위 (key, offset_s). 꼴(64줄·FS24·2키 × 16위상 × V0·VB 한 줄씩) 아니면 S-15. k = `gates.Fmin_after_W` 또는 `gates.U57_outside` 거짓인 위상 수. R-1 k_VB ≤ k_V0 + 4(키마다), R-2 합 ≤ +6, R-3 VB `fault_events` = [] ∧ `final_phase` = ready, R-4 두 관문 밖 관문이 VB 거짓·같은 짝 V0 참인 수 = 0(관문 이름이 한쪽에만 있으면 그 줄 판정 불가). 필드 없음·형 다름 = 판정 불가(통과로 읽지 않음). 𝓕 행 = `grid_r67_main`·`grid_r67_top`의 두 키 FS24 run, 12행(아니면 S-15). 적용 조건 = 𝓕 행에 두 관문만의 통과→실패(V0 통과, VB 거짓 관문이 모두 두 관문 안). 참 ∧ 통과 = 그 두 관문 실패를 v5 H-10 셈에서 뺌, 참 ∧ 실패·판정 불가 = 멈춤 H-10(v5 기준), 거짓 = 기록. 다른 계열의 통과→실패는 앞 판대로 H-10 | `grid.family_f_rule`, `grid.cmd_grid` |
| 보충 5(사용자 결정 129) | 격자 행·짝·통과·출력을 아래 "보충 5 대조" 표대로 고쳤다. 격자 run 태그는 `results[i].controller_tag`만 | `grid.row_state`, `grid.reduced_pass`, `grid.v0_pair`, `grid.job_tag`, `grid.cmd_grid` |
| 보충 6-1 | (가)·(다)·(나)·기록 행의 `file` = VB 격자 파일의 저장소 루트 상대 경로(`/`, `common.rel_file`). 짝 열쇠의 파일은 stem. 정렬 = 경로 → 키 → 사건(코드 포인트) → `offset_s`(수). 관문 이름 목록은 코드 포인트 순, 없으면 빈 목록. (다)의 거짓 관문 열은 두 관문을 빼지 않은 전부. V0에만 있는 run의 `file`은 V0 파일의 상대 경로 | `grid.cmd_grid`, `grid._row_sort`, `grid.false_gates` |
| 보충 6-2 | 짝 출처 = 표본 대조(`sample_compare`): 작업 = 표본 파일의 `results[i]` 하나(8개, 아니면 S-15). 작업마다 표본 run이 저장 V0 짝(같은 stem·키·사건·위상 ±1e-9 s)을 정확히 하나 갖고 두 `commands_sha256`이 문자열이어야 한다. 같음 8 = 저장 V0, 다름이 있으면 `h9_grid_v0/`(없으면 판정 불가), 판정 불가 작업이 하나라도 있으면(다름보다 앞섬) 또는 표본·저장 V0가 없으면 짝 출처 `undecidable`(짝을 맺지 않음, 기록). 저장 V0 run 태그는 대조하지 않고, `h9_grid_v0/` run 태그는 ③ 없음 기대 태그와 대조(없음 S-11, 다름 S-2) | `grid.sample_compare`, `grid.v0_pair`, `grid.cmd_grid` |
| 보충 6-3 | 𝓕 행 `applicable` = `true` / `false` / `"undecidable"`(그 행이 5-1·5-2·5-3 (나)에서 판정 불가이거나 짝 출처가 판정 불가). 전체 = 참인 행 있음 → 참, 아니고 판정 불가 행 있음 → `"undecidable"`, 아니면 거짓(짝 출처 판정 불가면 `"undecidable"`). V0는 5-1 짝 하나(계열 𝓕 R-1~R-4 쪽은 적용 조건을 계산하지 않음). 조건 `"undecidable"`이면 H-10 격자 항으로 쓰는 수 없음(`h10_grid_term.uses` = `none`), 표지 없음 | `grid.cmd_grid` |
| 보충 6-4 | 이 계산의 멈춤 표지는 `H-10` 하나(세 경우). FAULT 행, 판정 불가 행, 짝 출처·적용 조건 판정 불가는 수·목록(`grid_records`, `supplement6_inputs`)으로만 내고 미달·판정 불가 발견을 만들지 않는다(앞 판의 `grid FAULT` 미달과 행마다 판정 불가 발견을 뺐다) | `grid.cmd_grid` |
| rev16:102~103 | 앞 판의 `lock_window_alignment.n_late_fallback` > 0 멈춤(stage1 V0 줄, grid, noise)을 뺐다. J11은 실제 대체 다리의 `n_late_fallback_by_leg`이고, V0~V8·L1·L2·pressure_only는 기록이다 | 같음 |
| 묶음 합치기 | `p2v5c_stage1.py merge --part <noise> --part <stage1> --part <grid>`: 세 출력의 RD-7 목록을 묶음별로 합쳐 다시 정렬하고(H-9 = stage1 + grid), RD-8·RD-9·RD-10을 더하고, RD-13과 각 목록의 sha256을 한 파일에 낸다. 다시 판정하지 않는다. 출력마다 도구·공통 sha가 이 checkout 파일과 같고(아니면 S-11) HEAD가 `--expect-head`와 같아야 한다(아니면 S-12) | `stage1.cmd_merge` |

### 보충 5 대조 (보충 4 판 `grid`가 계산하던 것 ↔ 보충 5-1~5-4, 규칙 문장만으로 대조)

보충 5 sha256 `89cb422d…`(`r4_supplement_4_common.md` sha256 `7bd7cb17…`). "앞 판"은 보충 4 판(`8130954`) `grid`다.

| 항목 | 보충 5 | 앞 판 | 이 판 |
|---|---|---|---|
| 행 | VB 격자 run 하나, 768 | 같음 | 같음 |
| 행·짝 열쇠 | (파일 이름, `results[i].key`, `runs[j].event`, `runs[j].offset_s`), 위상은 \|a − b\| ≤ 10⁻⁹ s면 같음 | 문자열 열쇠 `<stem>\|<key>\|<event>\|<offset_s>`(위상은 글자 그대로 같아야 함) | 5-1대로(`OFFSET_TOL_S` = 1e-9). 보충 6-1로 짝 열쇠의 파일은 stem, 목록의 `file`은 저장소 상대 경로 |
| V0 짝 출처 | 표본 해시가 모두 같으면 저장 V0 격자, 하나라도 다르면 `h9_grid_v0/`, 표본 파일은 짝 아님 | `--v0-new`가 있으면 표본과 상관없이 새 V0, 없으면 표본 같을 때 저장 V0 | 5-1대로. 보충 6-2로 표본 대조가 판정 불가(짝 결측·해시 결측)이면 다름보다 앞서 짝 출처 `undecidable` |
| 짝 0개·2개 이상 | 그 행 판정 불가, V0에만 있는 열쇠도 판정 불가 목록 | 짝 0개만 판정 불가(사전이라 2개 이상은 드러나지 않음), V0에만 있는 열쇠는 보지 않음 | 5-1대로(`grid_records.undecidable_rows`의 `side` = `pair` / `V0 only`) |
| 행 통과 | 기록 `pass`. `pass`가 bool이 아니거나 `gates`가 이름 → bool 사전이 아니거나 `pass` ≠ `gates` 논리곱이면 판정 불가 | 원시 필드로 관문을 다시 계산한 값(`gates_p2`)의 논리곱. 기록 `pass`·`gates`는 대조 기록뿐 | 5-2대로(`row_state`). `gates_p2` 재계산은 기록(`recorded_gate_differences`)으로만 남김 |
| 통과→실패 | V0 짝 통과 참 ∧ VB 통과 거짓. 실패→통과·실패→실패·통과→통과는 기록 | 같은 뜻(통과 값만 위와 다름) | 5-2대로. 기록 수는 `grid_records` |
| FAULT | VB 행 가운데 `fault_events`가 빈 목록 아님. 목록 아니면 판정 불가 | `gates_p2`의 `fault0` 거짓(`fault_periods` ≠ 0 또는 `fault_events` 있음) | 5-2대로 |
| (가) 원 통과→실패 | 768행 목록, 한 줄 = (파일 이름, 키, 사건, 위상, VB 거짓 관문, V0 거짓 관문), 정렬 파일 → 키 → 사건 → 위상, N_raw | 문자열 열쇠와 VB 거짓 관문만, 정렬 없음 | `a_pass_to_fail_raw`, `N_raw` |
| (나) 𝓕 행 표 | 𝓕 12행마다 열쇠, VB·V0 `pass`, 거짓 관문, 두 관문 뺀 통과(VB·V0), 적용 조건. 관문 이름 집합이 다르거나 두 관문이 없으면 판정 불가 | 없음(𝓕 통과→실패만 따로 모음) | `b_family_F_table`, `family_F_applicable` |
| (다) 𝓕 제외 목록 | 𝓕 밖 = (가). 𝓕 행은 V0·VB 모두 두 관문 뺀 논리곱으로 다시 판정(B안), V0 참 ∧ VB 거짓만. N_F | 𝓕 행 가운데 VB 거짓 관문이 두 관문 안인 통과→실패를 뺀 목록(V0는 다시 판정하지 않음) | `c_pass_to_fail_family_F_excluded`, `N_F`(B안). 거짓 관문 열은 두 관문을 빼지 않은 전부(보충 6-1과 같음) |
| 기록 | 실패→통과·실패→실패 수, FAULT 수와 행, 판정 불가 행 | FAULT 행, 기록 관문 차이 | `grid_records`(`pass_to_pass`, `fail_to_pass`, `fail_to_fail`, `fault_rows`, `N_fault`, `undecidable_rows`, `N_undecidable`) |
| v5 H-10 격자 항(5-4) | 조건 거짓: N_raw ≥ 1이면 H-10. 참 ∧ R 통과: N_F ≥ 1이면 H-10. 참 ∧ R 실패·판정 불가: H-10 | 𝓕 밖 통과→실패가 있으면 H-10, 𝓕만이면 R 실패일 때 H-10(조건 거짓일 때 N_raw로 보지 않고 𝓕 밖 수로 봄) | 5-4 표대로. 쓴 수는 `h10_grid_term`(`N_raw` / `N_F` / `none`) |
| FAULT ≥ 1 | v5 기준 10절 위반, H-10 격자 항과 함께 적음 | 미달(행마다) | 보충 6-4로 수와 행 목록만(등급은 판정서) |
| 판정 불가 행 ≥ 1 | 이 항목 판정 불가, 멈추고 묻는다 | 행마다 판정 불가 | 보충 6-4로 수와 행 목록만(등급은 판정서) |
| 격자 run 태그 | `results[i]`의 최상위 `controller_tag`만(사용자 결정 129) | run 자체 태그가 있으면 그것, 없으면 `results[i]` 태그 | 5-1대로(`job_tag`), 판 대조(보충 4-3) 없음 = S-11·다름 = S-2 |

### 읽기 공개 (블록·보충이 글자로 정하지 않아 이 작성자가 정한 곳)

1. **최소 간격 [bar]**(보충 3-3으로 확정, 사용자 결정 126): 하네스 기록(`03_src/outrigger_sim/control/extend_start_bound.py` 617행)의 `min_gap_bar` 다리 원소를 계산 없이 옮긴다. 첫 위반 시각은 `first_breach_t_s`(619행)다. 없음·4원소 목록 아님·수 아님·비유한이면 `null`. `min_gap_Pa`는 읽지 않는다.
2. **H-8 RD-9 수**(보충 3-1로 확정): H-8 결과 파일 네 개의 ③ 켬 줄 전부를 센다. dg3 대체 135키의 H-8 noise VB 줄도 `RD-9.p3_on`에 들어간다(같은 경로 2의 `p2_4368.py harness` RD-9 셈과도 같음, 그 파일 1,093~1,096행). 그 줄 수와 대체 줄을 뺀 수는 `R4.H-8_dg3_substituted`(`p3_on`, `p3_on_judged_in_H-8`)에 따로 적는다. RD-10 수와 RD-7 목록에서는 뺀다(보충 2-1 "H-6 줄로 판정").
3. **H-10 목록의 U-9 VB 28줄**(보충 3-4로 확정): U-9 VB 줄은 묶음 H-10의 결과 파일 줄이므로 J-P3·J11 목록과 RD-9·RD-10 수에 넣는다(등급은 앞 판대로 `p2_v5j u9`). 이 줄의 J-P3·J11 발견은 H-10 발견에도 넣는다.
4. **H-9 ③ 켬 줄의 T4h**: R12-1(C-13·C-14)을 H-9 main·pressure_only의 ③ 켬 줄에도 쓴다. 찾는 곳은 `--h9`의 관례 폴더뿐이다(`--t4h-root`는 `--h10` 몫). ③ 아닌 줄은 T4h를 찾지 않는다.
5. **격자 J11 설정**(보충 3-6으로 확정): `results[i].v5_setting`만 쓴다. 없으면 `setting` 열 `null`이고 그 run의 J11은 판정 불가다(파일 `meta.v5_setting`으로 대신하지 않음).
6. **noise VB 파일 줄의 `v5_setting` 없음**: J11 판정 불가. V0 파일 줄은 기록(`setting` 없으면 V0로 읽음).
7. **V0 파일 줄의 ③ 태그**: J-P3를 판정하지 않고 S-2(줄 설정과 태그가 다름, 원판 4.1·8.2)로 멈춘다.
8. **`bundle` 열 값**(보충 3-5로 확정): `H-6`·`H-8`·`H-9`·`H-10`(ASCII `H`, U+002D, 숫자), 정렬은 숫자 순.
9. **보충 5 "파일 이름"**(보충 6-1로 닫힘): `file`은 VB 격자 파일의 저장소 루트 상대 경로(`/`)다. 짝은 파일 stem으로 맞춘다. `offset_s`는 기록 수를 그대로 적는다. (앞 판의 `<stem>.json` 표기는 뺐다.)
10. **보충 5-4 FAULT·판정 불가의 등급 표기**(보충 6-4로 닫힘): 도구는 수와 목록만 내고 등급(미달·판정 불가 발견)을 만들지 않는다. 등급은 판정서가 원판 8.1 순서로 정한다. (앞 판의 `grid FAULT` 미달과 행마다 판정 불가 발견은 뺐다.)
11. **보충 5-3 (나)의 적용 조건 행**(보충 6-3으로 닫힘): `applicable`은 `true` / `false` / `"undecidable"` 세 값이고 `null`을 쓰지 않는다. 전체 적용 조건도 같은 세 값이다.

### RD-5 키 대응표 초안 (K-10 대조에서 빼는 키, 결과 보기 전 확정)

| 키(출력 JSON) | 범주 | 만드는 곳 |
|---|---|---|
| `created` | 실행 시각 | `common.run_main` |
| `argv`의 `--out`·`--judge-dir` 값 원소 | 출력 위치(인자 목록 전체가 아니라 그 원소) | `common.run_main` |
| `argv`의 입력 경로 원소(`--h9`, `--h10`, `--vb`, `--noise-vb`, `--part` 등), `--expect-head`·`--git-at-start` 값 | 입력 파일 경로 / 실행 정체성(커밋) | `common.run_main` |
| `head_check`(`expect`, `head`, `ok`, `why`) | 판정 도구가 돈 checkout 커밋 | `common.run_main` |
| `seals`(`rev3`, `rd2_union`, `eol_only*`) | 봉인 블록 | `common.run_main` |
| `tool`, `version`, `tool_sha256`, `common_sha256`, `imports` | 도구 판·sha 블록 | `common.run_main` |
| `inputs`, `R11-2_t4h`(찾는 폴더와 상태 수), `v5_options`, `judge_tool`, `judge_runs`, `R4.dg3_key_source`, `parts`(merge) | 입력 파일 경로·sha256 블록 | 각 `cmd_*` |
| `stops[].why`·`where`, `undecidable[].why`·`where`, `fails[].why`·`where`, `records[].what`·`where`, 항목 안의 `why`, `TABLE_REAGG[].source` | 자유 문장 사유(위치 표기 포함) | 각 `cmd_*`, `p2_v5j` |

- 대조하는 것: 묶음 등급(`grades_436_8`), `stop_codes`, RD-7 목록(줄 식별 = 묶음·파일·위치·다리, 값 열은 같은 줄에서 함께), `markers`, RD-8·RD-9·RD-10 수, 그 밖 수·참거짓.

### RD-13 항목 목록 sha256 (이 판 `common` `6640cc93…`)

| 묶음 | 항목 수 | sha256 | 앞 판: 보충 4 판(`8130954`) / 보충 3 판(`e268b26`) / R4 판(`41f99a4`) |
|---|---|---|---|
| H-6 | 18 | `11a421a528c253c62bc1f03e32609348bb4027fbf362cd7d65ac306621329ee4`(보충 3 판부터 같음) | 같음 / 같음 / `6f927367…` |
| H-8 | 21 | `a7f1e82f50cdef5252b7e22a076ad2b61470db0cefef31c91211c20b19ca0839`(보충 3 판부터 같음) | 같음 / 같음 / `396b534a…` |
| H-9 | 34 | `d2577764d72c0050edbd820d5fefd8c3157ee1e9a66335b2cda4f6c25e35c4ac` | 보충 5 판 `55ac9287…`(33) / 보충 4 판 `648a64b8…`(30) / 보충 3 판 `71f541d4…`(26) |
| H-10 | 23 | `35d2ca0106f7d2ecdd2e8f8f43053857d906514fff628127ee6382783829a47b`(보충 4 판과 같음) | 같음 / `fd46e7ff…`(22) / `8b52d2c8…` |

- 보충 6 판에서 바뀐 것(H-9만, 33 → 34): "격자 FAULT"·"격자 판정 불가 행"을 등급·관문에서 수·목록 기록으로(보충 6-4), "격자 V0 짝"을 짝 출처 세 값·V0 태그 대조 범위(보충 6-1·6-2)로, "계열 𝓕 행 표 (나)"에 세 값 적용 조건(보충 6-3)을, "v5 H-10 격자 항"에 조건 판정 불가 행(6-3·6-4)을 고쳐 넣었다. "격자 목록 표기"(RD-7 3, 보충 6-1)를 더했다. H-6·H-8·H-10 목록은 그대로다.
- 보충 5 판에서 바뀐 것(H-9만, 30 → 33): "격자 run 관문 342.3"을 "격자 행 통과 = 기록 pass(gates 대조), (가)·N_raw"(관문)로, "격자 FAULT 0"을 "fault_events 빈 목록"으로, "격자 V0 짝"에 열쇠·정확히 1개와 보충 5-1을, 격자 run 태그 항목을 "`results[i].controller_tag`만(사용자 결정 129)"으로 고쳤다. "계열 𝓕 적용"을 "v5 H-10 격자 항(5-4 표, (다) B안)"으로 고쳤다. "격자 판정 불가 행", "격자 기록", "계열 𝓕 행 표 (나)"를 더했다.
- 보충 4 판에서 바뀐 것
  - H-9: 계열 𝓕 항목을 "R-1~R-4 늘 냄(기록)"과 "적용(관문, 멈춤 H-10)" 둘로 나누고 근거에 "보충 4-5"를 더했다. "계열 𝓕 판정 입력 꼴·판 판별·태그 대조", "h9_stage1 판·태그 대조", "입력 파일 있음(V0 저장 격자 4·h9_family_F.jsonl)"을 더했다(26 → 30).
  - H-10: "줄마다 판 판별(job.setting)·태그 대조, 판별 수 기록"(보충 4-2·4-3)을 더했다(22 → 23).
- 보충 3 판에서 바뀐 것: J-P3 위반 목록 항목 근거에 "보충 3-3·3-5", ③ 켬 줄 수에 "보충 3-1", J11 목록에 "보충 3-5"를 더했다(네 묶음 공통). H-8 dg3 대체 항목을 "h8_noise_VB만, 뺀 수 기록"으로 고치고 근거에 "보충 3-1·3-2"를 더했다. H-9에 "격자 run J11 설정 = results[i].v5_setting만" 항목(보충 2-2·3-6)을 더했다. H-10 U-9 항목 근거에 "보충 3-4"를 더했다.

### R4 판정 실행 명령 예 (M4 checkout에서, 출력 `judge_<M4>/harness_path2/`)

```powershell
$M4 = '<M4 40자리>'; $R2 = 'b9f5707d7f3f7a26230b25f4edbc1fec587ca612'
$d = '<repo>\06_analysis\02_control\verif_matrix\v5_resume_4368\path2_v5c'; $r = '<repo>\06_analysis\03_hydraulic\coupled\v5\resume_k1'
$o = '<repo>\06_analysis\02_control\verif_matrix\v5_resume_4368\judge_<M4 짧은 해시>\harness_path2'
$s = '<repo>\06_analysis\02_control\touch_phase\acceptance\c4g2_only\grid'   # V0 저장 격자(보충 4-2, *_off.json 아님)
$c = 'C:\ProgramData\miniforge3\Scripts\conda.exe'
& $c run -n dynamics-dev python -I -B "$d\p2v5c_stage1.py" --expect-head $M4 --out "$o\p2v5c_stage1.json" stage1 --h9 "$r\h9_stage1.jsonl" --h10 "$r\h10_reuse_rerun.jsonl" --overlap-ta "$r\h10_overlap_t_a.json"
& $c run -n dynamics-dev python -I -B "$d\p2v5c_grid.py" --expect-head $M4 --out "$o\p2v5c_grid.json" grid --vb grid_r67_main="$r\h9_grid\grid_r67_main.json" --vb grid_r67_top="$r\h9_grid\grid_r67_top.json" --vb grid_r69_bottom="$r\h9_grid\grid_r69_bottom.json" --vb grid_r69_top="$r\h9_grid\grid_r69_top.json" --v0-stored grid_r67_main="$s\grid_r67_main.json" --v0-stored grid_r67_top="$s\grid_r67_top.json" --v0-stored grid_r69_bottom="$s\grid_r69_bottom.json" --v0-stored grid_r69_top="$s\grid_r69_top.json" --v0-sample grid_r67_main="$r\h9_grid_v0_sample\grid_r67_main.json" --v0-sample grid_r67_top="$r\h9_grid_v0_sample\grid_r67_top.json" --v0-sample grid_r69_bottom="$r\h9_grid_v0_sample\grid_r69_bottom.json" --v0-sample grid_r69_top="$r\h9_grid_v0_sample\grid_r69_top.json" [--v0-new <stem>="$r\h9_grid_v0\<stem>.json"] --family-f "$r\h9_family_F.jsonl"
& $c run -n dynamics-dev python -I -B "$d\p2v5c_noise.py" --expect-head $M4 --out "$o\p2v5c_noise.json" noise --noise-vb "$r\h8_noise_VB.json" --noise-v0 "$r\h8_noise_V0.json" --h6 "$r\h6_dg3_v4on.json" --seedext-vb "$r\h8_seedext_VB.json" --seedext-v0 "$r\h8_seedext_V0.json" --judge-dir "$o\p2v5c_r79_judge" --git-at-start $R2
& $c run -n dynamics-dev python -I -B "$d\p2v5c_stage1.py" --expect-head $M4 --out "$o\p2v5c_merge.json" merge --part "$o\p2v5c_noise.json" --part "$o\p2v5c_stage1.json" --part "$o\p2v5c_grid.json"
```

- 세 도구는 서로 기다리지 않는다. `merge`는 세 출력이 모두 확정된 뒤 돌린다. stdout 마지막 줄 JSON의 `out_sha256`을 판정서에 적는다(RD-6).
- `--t4h-root`는 관례 폴더(`h10_reuse_rerun_t4h\`, `h6_dg3_v4on_t4h\` 등)가 없을 때만 1개 준다(R11-2).
- 계열 𝓕 R-1~R-4(보충 4-5)는 위 `grid` 명령이 늘 낸다(`--family-f` 필수). 결과는 `p2v5c_grid.json`의 `grid.family_F_rule`(`k`, `R1`~`R4`, `result`, `application`), `grid.family_F_rows`(12), `grid.family_F_applicable`이다. 적용 조건이 참이고 결과가 실패·판정 불가이면 `stop_codes`에 `H-10`(v5 기준 멈춤)이 있다.

## 사용자 결정 19 반영 (격자 run 태그, dynamics-expert `c969b57`과 같은 읽기)

| 항목 | 반영 | 함수 |
|---|---|---|
| `P2_CORE_SHA` | `424e12f9…`(병합 `52f27f7` 뒤 실제 sha와 같음 확인). `P2_V5J_SHA`(`69d0e747…`)는 그대로. 그 뒤 z4372-p2chrono에서 `0ccc5186…`으로 갱신(위 표) | `common.import_record` |
| 격자 run 태그 | G-S `gs_harness_bbacfd7/h9_grid_r67_main.json`의 구조를 확인했다(키 위치만, 판정 값 아님). `results[i]` 1개 모두에 `controller_tag`가 있고, run 6개에는 태그가 없었다. rev8 판 이후 grid는 run의 태그만 읽었다. 그래서 본 실행 격자에서 VB run 전부가 "③ 아님 → J-P3 해당 없음 + S-2"로 잘못 멈출 결함이 있었다. 합성 시험 `fast_run`에는 run 태그가 있어 드러나지 않았다. 이제 run 태그가 있으면 그것을 쓰고, 없으면 job 기록 `results[i]`의 태그를 쓴다(rev8 R8-1 "최상위 `controller_tag`"). 둘 다 없으면 앞 판대로 J-P3 해당 없음 + S-2다(R8-2). 출력 `inputs.vb.<stem>.tags`와 V0 `tags`도 같은 읽기다 | `grid.run_tag_view`, `grid.cmd_grid` |
| noise·stage1 | r79 기록과 run_v5 줄은 줄 자체에 태그가 있다(합성 시험·앞 판 확인). 바꾸지 않았다 | – |

## rev12 반영

| 규칙 | 반영 | 함수 |
|---|---|---|
| R12-6 봉인 확인 | `LATER_RULES`에 rev12(`78f1f99b…`, `.sha256`)를 더했다. 파일 sha가 코드의 봉인 값·`.sha256` 첫 값 둘 다와 같고 LF·BOM 없음이어야 한다. 아니면 S-1(종료 2) | `common.check_rev3`, `common.run_main` |
| R12-6 import 고정값 | `P2_CORE_SHA` = `a948d9a1…`(rev12 판, 병합 뒤 실제 sha와 같음 확인). `P2_V5J_SHA`는 사용자 결정 24 판 `69d0e747…`(병합 `66dfe09` 뒤 실제 sha와 같음 확인) | `common.import_record` |
| 사용자 결정 24 `t4h_file` 값 결함 | `t4h_file` 키가 있는데 값이 None·문자열 아님·빈 값이면 S-2다. 판단은 import한 `p2_v5j.rod_reading_lookup`(상태 `bad_t4h_file`)에 맡겨 경로 2 안의 정의를 하나로 했다. 결정 24 전 이 폴더는 같은 경우를 자체 분기 `unreadable_name`으로 S-2 처리했고, 빈 문자열은 `not_found`로 S-2가 됐다. 결과(S-2, J-P3 판정 안 함)는 같고 상태 이름만 바뀐다 | `common.jp3_rod_input` |
| R12-1 적용 범위 (Q-R12-1 = A) | J-P3 로드 판독을 하는 세 도구 모두에 같은 입력 규칙을 쓴다. ① `t4h_file` 키가 없는 줄은 설정 읽기다(R3-C8). stage1은 `p2_v5j` 설정 규칙을 쓰고, noise·grid는 two-pressure 경로 = 로드 판독이다(rev9 3.2 #4). ② 키가 있으면 R11-2의 찾는 곳에서 정확히 1개여야 한다. 0개, 2개 이상, 또는 이름이 아닌 값이면 S-2이고, 그 줄의 J-P3는 판정하지 않는다(`t4h_unresolved`). 설정 읽기로 대신하지 않는다. ③ 찾는 곳은 각 입력 파일의 관례 폴더(`<stem>_t4h/`, `t4h/`)다. 어느 입력에도 관례 폴더가 없을 때만 `--t4h-root` 1개를 쓴다. 그 밖은 입력 오류(S-11, 종료 2, 판정 안 함)다. 대상 입력: stage1 `--h10`, noise `--noise-vb`·`--h6`·`--seedext-vb`, grid `--vb` 4개 | `common.jp3_rod_input`, `common.strip_jp3`, `common.t4h_input_error`, `stage1.judge_all`, `noise.run_checks`·`cmd_noise`, `grid.cmd_grid` |
| R12-1 rev11 판과 다른 점 | stage1은 rev11 판에서도 S-2를 냈다. 다만 `judge_pair`가 설정 읽기로 낸 J-P3 결과와 그 발견(H-7·J-P3-defect·판정 불가)이 남아 있었다. rev12 판은 그것을 지운다(`strip_jp3`). noise·grid는 rev11 판까지 T4h를 읽지 않고 늘 설정 읽기(True)였다. r79 러너(`r79_sensor_screen.py`)는 `R79_T4H_DIR`가 있으면 `t4h_file`을 쓴다(H-6 Dg-3, RV1-3.3 `h6_dg3_v4on_t4h/`). 그래서 기록된 T4h를 먼저 읽게 고쳤다 | – |
| R12-3 `--git-at-start` 필수 | `noise`는 `--git-at-start`를 필수로 받는다(없으면 argparse 종료 2). 이 값은 R4-A2 조건 1(`git log f46b5ab..GIT_AT_START -- r79_sensor_judge.py`)의 기준이고, 판정서의 `git_at_start`와 같아야 한다. 앞 판의 "없으면 repo HEAD" 기본값은 뺐다. R12-3 본문은 R11-4(Chrono 행 커밋 대조) 보충이다. 그래도 커밋을 기준으로 쓰는 이 폴더 유일의 인자에 "판정서에는 이 값이 항상 있다"를 같게 적용했다 | `noise.build_parser`, `noise.cmd_noise` |

### rev12에서 이 폴더가 바꿀 것이 없던 항목

| 규칙 | 이유 |
|---|---|
| R12-2 Chrono 행 dirty 기록만 | Chrono 행의 `code_at_launch.git`이라 이 폴더가 읽지 않는다 |
| R12-4 열린 루프 행 `code_state` 기록만 | Chrono C-6·C-7 행이라 이 폴더가 읽지 않는다 |
| R12-5 행 폴더 시각 창 | Chrono L2b·L1-R 행 폴더 찾기라 이 폴더가 읽지 않는다 |
| R12-6 순서·`git_at_start` | 메인 세션이 정하는 순서다 |

## rev11 반영

| 규칙 | 반영 | 함수 |
|---|---|---|
| R11-7 봉인 확인 | `LATER_RULES`에 rev11(`9bac4524…`, `.sha256`)을 더했다. 파일 sha가 코드의 봉인 값·`.sha256` 첫 값 둘 다와 같고 LF·BOM 없음이어야 한다. 아니면 S-1(종료 2) | `common.check_rev3`, `common.run_main` |
| R11-7 import 고정값 | `P2_CORE_SHA` = `a8c625bf…`, `P2_V5J_SHA` = `e5d769b9…`(rev11 판, 병합 뒤 실제 sha와 같음 확인) | `common.import_record` |
| R11-2 T4h 찾기 | 이 폴더에서 T4h를 읽는 것은 `stage1`뿐이다(H-10 줄의 J-P3 rod reading, rev9 3.1). 읽는 줄(main·item8·overlap)은 모두 `--h10` 파일에서 온다. ① 찾는 곳은 `--h10`의 러너 관례 폴더(`<stem>_t4h/`, 같은 폴더의 `t4h/`)뿐이다. ② 관례 폴더가 하나도 없을 때만 `--t4h-root` 1개를 쓴다. 관례 폴더가 있는데 주거나 2개 이상 주면 입력 오류다. 이때는 두 묶음(H-10·H-9 stage1)을 판정하지 않고 S-11(종료 2)로 끝낸다. ③ 줄에 기록된 `t4h_file`이 찾는 곳 전체에서 0개 또는 2개 이상이면 그 줄은 S-2다. `t4h_file`이 없는 줄은 앞 판대로 설정 읽기(rev3 R3-C8)다. 찾기 함수는 같은 경로 2의 `p2_v5j.t4h_places`·`rod_reading_lookup`(import, `u9`와 같은 정의)이다. 출력 `R11-2_t4h`에 찾는 폴더와 상태별 수(`ok`·`no_t4h_file`·`not_found`·`several`)를 적는다 | `stage1.cmd_stage1`, `stage1.judge_all` |
| R11-2 앞 판과 다른 점 | rev10 판까지는 `--t4h-root`를 주지 않으면 T4h를 읽지 않았고(설정 읽기), 파일이 없어도 설정 읽기로 넘어갔다. rev11 판에서는 `t4h_file`이 기록된 줄에서 파일을 찾지 못하면 S-2다(R11-2 3, rev8 R8-1a) | – |

### rev11에서 이 폴더가 바꿀 것이 없던 항목

| 규칙 | 이유 |
|---|---|
| R11-1 원판 4.2 기록 확인의 기대값(줄 종류) | 4.2 기록 확인(관문·LAS-b 기록 대조)은 경로 1 `record-check`와 경로 2 `p2_t3k`(H-0)·`p2_4368` 몫이다. 이 폴더는 4.2 기록 대조를 하지 않고, H-0(`t3.*`) 줄과 Chrono C-4 끔 팔도 읽지 않는다. ③ 판별은 앞 판대로 태그로만 한다(R8-2) |
| R11-3 `commands_sha256`의 뜻 | 이 폴더는 해시를 같은 설정끼리만 비교한다: P-6·P-7(L2 = L1, L1 ≠ V0), H-15(seedext 시드 0~4 ↔ 잡음 L2), V0 표본 같음(R4-B4). H-6과 H-7(③ 끔) 해시를 비교하지 않고, 해시로 ③ 켬·끔을 가르지도 않는다. H-7(③ 끔) 묶음은 이 폴더 입력이 아니다 |
| R11-4 열린 루프 행 커밋 정체성 | Chrono C-6·C-7 행의 `code_at_launch` 기록이다. 이 폴더는 Chrono 행을 읽지 않는다 |
| R11-5 G-S 행 등급 | Chrono judge의 G-S 행 등급 규정이다. 이 폴더 도구를 G-S에서 돌리더라도 그 등급은 원판 11.2대로 판정에 쓰지 않는다(메인 세션 판정서 몫). 코드 변경 없음 |
| R11-6 G-S 절차·출력 보관 | 메인 세션 절차다(`gs_harness_<커밋>/` 보관) |
| R11-7 순서·`git_at_start` | 메인 세션이 정하는 순서다. `noise`는 `--git-at-start`를 받는 그대로다 |

## rev10 반영

| 규칙 | 반영 | 함수 |
|---|---|---|
| R10-3 봉인 확인 | `LATER_RULES`에 rev10(`62a0bd8d…`, `.sha256`)을 더했다. 파일 sha가 코드의 봉인 값·`.sha256` 첫 값 둘 다와 같고 LF·BOM 없음이어야 한다. 아니면 S-1(종료 2) | `common.check_rev3`, `common.run_main` |
| R10-3 `P2_CORE_SHA` | `../path2/p2_4368.py` 고정값을 rev10 판 `6e297ea3…`로 바꿨다(병합 뒤 실제 sha와 같음 확인). `P2_V5J_SHA`(`5772624c…`)는 실제 sha와 같아 그대로다 | `common.import_record` |

### rev10에서 이 폴더가 바꿀 것이 없던 항목

| 규칙 | 이유 |
|---|---|
| R10-1a 전체 묶음 이름, R10-1b 경우별 처리(manifest·`batch.json` 행 수, manifest 파일 없음 = 입력 오류) | R9-4 LS 판별(Chrono 행, C-5 J11)의 입력 경계다. 이 폴더는 S9 배치 `batch.json`·`chrono_rows_manifest.json`을 읽지 않는다. 하네스 줄의 LS는 구조 필드 `job.setting`으로 가른다(rev9 반영 절) |
| R10-2 G-S 확인 항목 | Chrono 행마다의 묶음 이름·manifest 확인이다. 이 폴더는 G-S 출력을 만들거나 읽지 않는다 |
| R10-3 순서·`git_at_start` | 메인 세션이 정하는 순서다. 이 폴더 `noise`는 `--git-at-start`를 받는 그대로다 |

## rev9 반영

| 규칙 | 반영 | 함수 |
|---|---|---|
| R9-8 봉인 확인 | `LATER_RULES`에 rev9(`4cf7843c…`, `.sha256`)를 더했다. 파일 sha가 코드의 봉인 값·`.sha256` 첫 값 둘 다와 같고 LF·BOM 없음이어야 한다. 하나라도 어긋나거나 `.sha256`이 없으면 S-1(종료 2). `p2_4368.check_seals`(b0d6382 판)도 rev9를 따로 확인한다 | `common.check_rev3`, `common.run_main` |
| R9-8 `P2_CORE_SHA` | `../path2/p2_4368.py` 고정값을 rev9 판 `7d764a80…`로 바꿨다(병합 뒤 실제 sha와 같음 확인). `P2_V5J_SHA`(`5772624c…`)는 실제 sha와 같아 그대로다 | `common.import_record` |
| R9-7 확인 시험 | 태그 이름은 이 폴더가 만들지 않는다. ③ 판별은 `p2_v5j.tag_of` + 기준 태그 함수 `is_extend_start_tag`(import)다. 시험 `test_r97_k1_only_tags`로 `final_C4G2_K1` = ③ 아님(VB 줄이면 J-P3 해당 없음 + S-2, R8-2 그대로), `final_C4G2_P3_K1` = ③ 켬을 확인했다. 코드 변경 없음 | (시험만) |

### rev9에서 이 폴더가 바꿀 것이 없던 항목

| 규칙 | 이유 |
|---|---|
| R9-1 `expect_controller.ok` 거짓·없음 = S-2 | Chrono 행(`run_S9.py level`, `run_S8C.py`, `run_S6C.py`)의 `c2_setup` 필드다. 이 폴더는 하네스 줄만 읽고 Chrono 태그 확인을 하지 않는다. 하네스 줄의 태그 불일치는 R8-2(`jp3_tag_scope`, S-2) 그대로다 |
| R9-2·R9-3 `law_locked` 형식·−1 읽기 | SCM `step_series.npz`·L2b `pads.npz` 기록이다. 이 폴더는 읽지 않는다 |
| R9-4 LS 행 판별 | 정의 대상이 Chrono 행(manifest `rows[].v5_setting` ↔ S9 `batch.json` `cases[].v5_setting`)이고 쓰는 곳도 C-5 행의 J11뿐이다. 이 폴더는 하네스 줄의 LS를 구조 필드 `job.setting`(`LS1`~`LS4` 정확 일치, `stage1.LS_SETTINGS`)으로 가르고 행 이름 토큰은 쓰지 않는다. 하네스 LS 줄 J11의 L-e(`p2_v5j.judge_pair`의 `job.setting` 접두 `LS`)도 같은 구조 필드다. rev9 "지금" 칸의 `"_LS" in case` 읽기는 이 폴더 코드가 아니다 |
| R9-5 결측·형식 오류 처리 | C-5 Chrono 행 전용. R9-5가 "하네스 줄의 R3-C7은 그대로다"로 적었다 |
| R9-6 J11 범위(C-5만 멈춤) | Chrono 행 범위 규정. 하네스 줄 J11(`lock_window_alignment.n_late_fallback`, H-7·L-e)은 v5 11·원판 그대로다 |
| R9-7 태그 규칙 3·5(재계산 태그) | 재계산 대조 주체는 경로 1 도구(R8-1d)다. 이 폴더는 태그를 재계산하지 않는다(위 표의 확인 시험만) |
| R9-8 순서·G-S 재실행·`git_at_start` | 메인 세션이 정하는 순서다. 이 폴더 `noise`는 `--git-at-start`를 받는 그대로다 |

## rev8 반영

| 규칙 | 반영 | 함수 |
|---|---|---|
| R8-4 봉인 확인 | `LATER_RULES`에 rev8(`3ecafaaf…`, `.sha256`)을 더했다. 파일 sha가 코드의 봉인 값·`.sha256` 첫 값 둘 다와 같고 LF·BOM 없음이어야 한다. 하나라도 어긋나거나 `.sha256`이 없으면 S-1(종료 2) | `common.check_rev3`, `common.run_main` |
| R8-4 `P2_CORE_SHA` | `../path2/p2_4368.py` 고정값을 rev8 판 `bebed9f1…`로 바꿨다(위 import 표). `P2_V5J_SHA`(`5772624c…`)는 그대로다 | `common.import_record` |
| R8-2 J-P3 범위 | ③ 판별은 그 줄의 태그로만 한다(`p2_v5j.jp3` → `tag_of`, `is_extend_start_tag`). ③ 켬이어야 하는 설정(VB·LS)의 줄에서 태그가 ③ 켬이 아니거나 없으면, J-P3는 **해당 없음**으로 두고(결측·판정 불가로 세지 않음) 태그가 설정과 다르므로 S-2(원판 4.1·8.2) 멈춤이다. rev7 판까지는 같은 줄을 판정 불가로 두었다. V0 줄은 J-P3를 보지 않는다(그대로) | `common.jp3_tag_scope`(grid `cmd_grid`, noise `run_checks`, stage1 `judge_all`) |

- R8-2 적용 범위: 이 폴더 입력은 하네스 줄이다. R8-2의 ③ 요청 기록 대조(Chrono 행 argv `--extend-start-tracked`, `v5_hydraulics.hydraulic_options.extend_start_tracked`)와 `controller_meta.two_pressure.settings.extend_start_rule` 확인은 Chrono 행 필드라 이 폴더에 해당하지 않는다(Chrono 경로 2 몫). 하네스 줄의 ③ 켬 J-P3 판정 자체(rev9 3.2 표, `extend_bound_check`)는 import한 `p2_v5j.jp3` 그대로다.

### rev8에서 이 폴더가 바꿀 것이 없던 항목

| 규칙 | 이유 |
|---|---|
| R8-1 T4h 없는 실행의 태그 재계산 대조 | 대조 주체가 경로 1 도구다(R8-1d "대조는 경로 1 도구가 한다"). 이 폴더는 최상위 `controller_tag`를 재계산·대조하지 않는다 |
| R8-1b 점 이름 키 `controller_settings["two_pressure.extend_start_rule"]` | 이 폴더는 이 키를 읽지 않는다(H-6·H-7 기록 확인은 `../path2/p2_4368.py` harness 몫, fd9bb68에서 반영됨) |
| R8-3·R8-3a SCM `step_series.npz` `law_locked`, L2b `pads.npz` | Chrono 행 기록이다. 이 폴더는 하네스 묶음만 읽는다. 하네스 줄의 J11(`lock_window_alignment.n_late_fallback`, `p2_v5j.judge_pair`)은 바뀌지 않았다 |
| R8-4 순서·`git_at_start` = 도구 커밋 Y | 메인 세션이 정하는 커밋 순서다. 이 폴더 `noise`는 `--git-at-start`를 받는 그대로다 |

## rev7 반영

| 규칙 | 반영 | 함수 |
|---|---|---|
| R7-2 | rev4 R4-B2를 바꾼다. 첫 DONE은 `base` 모양으로 정한다. (가) `base.t_done_s` 키가 있으면 그 값이 첫 DONE이고 `base.phase_path`의 첫 `done` 시각과 5 ms(양 끝 포함) 안이어야 한다. `t_done_s` = None인데 `phase_path`에 `done`이 있거나, `phase_path`가 없으면 S-11. (나) 키가 없으면 `base.timeline`(`[t_s, phase]`)의 첫 `done`. `timeline`이 없거나 비었으면 S-11. DONE이 없으면 `base.final_phase`가 `fault`·`fault_reground`일 때만 첫 DONE = None(정상), 그 밖은 S-11. S-11이면 조건 5 = None(그 줄은 판정 불가)이고 멈춤 S-11을 적는다. 출력 `cond.first_done`에 모양(`t_done_s`·`timeline`)·사유를 남긴다 | `noise.first_done`, `noise.late_loc_conditions` |
| R7-2 공개 | 419.8 조건 5는 rev3 Q-12대로 엄격 비교(최종 LOC < 첫 DONE)로 그대로 둔다. 경로 1(저장 419.8 기록, ≤ + 10⁻⁹ s)과는 LOC = 첫 DONE일 때만 다르고 원판 9.2 대조로 드러난다 | `noise.late_loc_conditions` |
| R7-7 봉인 확인 | `LATER_RULES`에 rev7(`e81f7d31…`, `.sha256`)을 더했다. 파일 sha·`.sha256` 첫 낱말·LF·BOM 없음 중 하나라도 어긋나면 S-1 | `common.check_rev3`, `common.run_main` |

- 적용 범위: R7-2는 경로 2가 419.8 조건 5를 다시 계산하는 줄(S-4 시간 조항 실패 줄)에만 쓴다. G-S의 모든 r79 줄 대조와 그 S-11 수는 R7-7대로 경로 1 G-S가 적는다.
- `final_phase`는 `base.final_phase`(R7-2 원문)만 읽는다.

### rev7에서 이 폴더가 바꿀 것이 없던 항목

| 규칙 | 이유 |
|---|---|
| R7-1a 최상위 `controller_tag` ↔ T4h meta | 대조 주체가 경로 1 도구다(R7-1a "이 대조는 경로 1 도구가 한다"). 이 폴더는 태그를 J-P3 적용 여부(`p2_v5j.tag_of`, import)와 격자 파일별 태그 수 기록에만 쓴다 |
| R7-1b `b1ddeae` G-S 태그 | 기록 지위 규정. 이 폴더는 G-S 출력을 읽지 않는다 |
| R7-1c T-3K R-0 태그 `final_C4G2` | H-0(T-3K) 줄은 이 폴더 입력(H-6·H-8·H-9·H-10)이 아니다(경로 2 T-3K 도구 `../path2/p2_t3k.py` 몫) |
| R7-3a F-8 `d1.g6_preloc`(`true_min_kN` kN·0.01 kN) | F-8(d1 줄)은 이 폴더 입력이 아니다(`../path2/p2_d1.py` 몫). 이 폴더는 `g6_preloc`·`true_min_kN`을 읽지 않는다 |
| R7-3b T-3K 정체성(`identity.sha256` dict, `identity.affinity`, `t3.affinity_hex`) | 위와 같다(`p2_t3k.py` 몫) |
| R7-4 Chrono 조건부 결측, R7-5 Chrono 경로 1 v2, R7-6 풀 마스크 | Chrono 행·SCM 배치 기록이다. 이 폴더는 하네스 묶음만 읽는다 |

## rev5·rev6 반영

| 규칙 | 반영 | 함수 |
|---|---|---|
| R5-C1 | 판정기 출력에 없는 L1 게이트 개수(지금 `settings_mismatch`)는 경로 2가 센 값이 판정 값이다. 출력에는 `"대조 대상 없음"`으로 적고 판정 불가로 두지 않는다 | `noise.cmd_noise` |
| R5-C2 | 하위 항목으로도 13.2로도 설명되지 않는 S-4 실패는 실패다. 판정기 S-4 `flags`에 기존 FLAG 꼬리표(`S4_…`)가 있으면 그 FLAG로 둔다 | `noise.line_grade` |
| R5-C3 | seedext 판정기 입력은 seedext 파일과 같은 설정의 `h8_noise_<설정>.json` 두 파일이다. 경로 2가 입력 파일을 따로 만들지 않는다 | `noise.cmd_noise` |
| R5-E | 판정기 조건 1은 `r79_sensor_judge.py`만 본다. 판정기가 import하거나 같이 쓰는 모듈(`s9/late_loc_rule.py`, `s8/r79_sensor_screen.py`, `s9/s9_slope_fix_candidates.py`, 러너 `s8/r79_L3L4_final.py`)은 `git diff --stat f46b5ab..GIT_AT_START`를 `judge_tool.related_modules_diff_stat`에 기록한다. "기록 전용 변경"인지는 판정서에서 판단한다. `r79_L3L4_final.py`의 판정 함수는 쓰지 않는다 | `noise.cmd_noise` |
| R6-C1 | SA-4 "정지 뒤 네 다리 ≥ F_min"은 F-9 `values.sa4.F_min_after_stop_N`의 네 다리 최소 ≥ 9,414.589 N으로 본다. F-9가 없으면 이륙 뒤 최소 ≥ F_min이 충분조건이고, 아니면 판정 불가다. "포화 차단 0"은 `values.pressure.saturation_leg_chunks` = 0이다(정의 확인은 G-S) | `stage1.sa4_rest` |

## 규칙 절 ↔ 함수

| 규칙 | 내용 | 함수 |
|---|---|---|
| v5 3 J1~J11, 개정 2 2.1, 개정 8 3.2·9 3, rev3 R3-C3~C8, rev4 R4-C5 | 줄마다 V0 짝 대비 | `p2_v5j.judge_pair`(import) |
| v5 2 P-6·P-7, R3-E5 Q-S4 | L2 = L1 해시 8행. 모든 L1이 V0와 같을 때만 P-7 | `stage1.check_p6_p7` |
| v5 6 S8, R3-E5 Q-S6, **R4-B1** | 조항과 SA-4 나머지 7항목. "정지 뒤 부상 0" = `values.sa4.lift_after_stop_ms` 네 다리 모두 0. 필드가 없으면 판정 불가. F-5 기록, H-5 | `stage1.f5_clause`, `stage1.sa4_rest` |
| v5 8 VB × L1, L-a~L-e, Q-S9 | 멈춤 / H-6 / `감도 큼` 기록(구분됨일 때만) | `stage1.l1_table`, `stage1.ls_conditions`, `stage1.ld_large` |
| v5 11 H-2·H-3·H-4·H-7·H-8·H-9, Q-S7·Q-S8 | VB J 실패(item8 포함), R12, 리밋 사이클, 대체 n_late, S7 분류·FL 가드 주기, 이륙 뒤 잘림 | `stage1.cmd_stage1`, `stage1.fl_guard_cycle` |
| v5 13.1 Q-S5, 13.3, 13.4 | 완전 역순만 실패(H-11), `FLAG_overlap`, `unit_status` | `stage1.item8_order`, `stage1.overlap_record`, `stage1.pressure_only_record` |
| 개정 6 #9, 436.8 5.1·RV1-12·R3-F1·Q-S10 | `m2_law` r5. 묶음별 줄 수 S-15 | `stage1.m2_law_check`, `stage1.split_lines` |
| 명세 342.3 | r67 행 관문 재계산, 기록 관문과 대조 | `grid.gates_p2` |
| R3-E1, **R4-B4** | V0 표본 `resume_k1/h9_grid_v0_sample/<stem>.json`. 한 작업 = 저장 파일의 `results[]` 항목 하나(파일마다 첫·마지막). 그 항목의 모든 run 해시가 같아야 "같음"이다. 8작업이 모두 같으면 저장 V0를 쓰고, 아니면 `h9_grid_v0/` | `grid.sample_jobs`, `grid.v0_pair` |
| v5 10 격자 | 통과→실패 0, FAULT 0(H-10) | `grid.cmd_grid` |
| 개정 5 5.2, R3-E2, **R4-B5** | 𝓕 두 관문만의 통과→실패가 있으면 `h9_family_F.jsonl`의 `event` = FS24 64줄로 R-1~R-4를 판정한다. 다른 사건 줄은 빼고 수만 적는다. 원시 필드가 없으면 줄의 기록 `gates`를 쓰고 수를 적는다 | `grid.family_f_rule` |
| **R4-A2 안 c** | 잡음 S-1~S-6과 L1 게이트의 항목 값은 경로 2가 `r79_sensor_judge.py judge`·`judge-merged … --s4-late-loc`를 직접 실행해 얻는다. 출력은 `--judge-dir`에 쓴다. 조건 1(`git log f46b5ab..GIT_AT_START -- r79_sensor_judge.py` 0커밋, 아니면 S-11)을 확인하고 도구 sha256을 적는다. 경로 1 출력은 읽지 않는다 | `noise.run_judge`, `cmd_noise` |
| R3-E3 재집계, R4-A2 조건 4 | 판정기의 항목 행(`runs[].rows.S-1…S-6`)으로 줄 등급을 경로 2가 다시 만든다. S-1·S-2·S-3·S-5·S-6은 `ok`, S-4는 하위 항목(`fail_misfire_new`, `miss`, `recontact_new` 실패, `loc_minus_off_s` > T_lim이면 경로 2의 419.8 재계산)으로 본다. 판정기의 `pass`·표·결론은 쓰지 않고, 다른 줄 수만 적는다 | `noise.line_grade`, `noise.grade_set` |
| R4-B2 → **rev7 R7-2** | 419.8 조건 5: 첫 DONE은 `base` 모양별(위 "rev7 반영"), 최종 LOC = `base.t_loc_final_s`(없으면 `r79.t_loc_s`). 조건 5 = DONE 없음 ∨ 최종 LOC < 첫 DONE(엄격, rev3 Q-12) | `noise.first_done`, `noise.late_loc_conditions` |
| **R4-B3** | L1 게이트 네 개수를 실행 기록에서 센 값과 판정기 출력(`errors`, `unmatched`, `settings_mismatch`, `reference[].false_loc`)을 함께 적는다. 다르면 S-13(판정 불가) | `noise.l1_gate`, `noise.l1_gate_judge` |
| v5 10 L2·L3, rev3 | S1 전방 제외, CP 두 근(> 3 %면 H-10), L3 기록(실패 수, CP, 대체 행 수, n_late) | `noise.cmd_noise` |
| 개정 6 9 | seedext: 판정기 입력 = seedext + 잡음 파일의 같은 사례 L1(경로 2 폴더에 씀). k/25, CP, Fisher 단측, 문구 두 가지. 시드 0~4 해시(H-15) | `noise.seedext_with_l1`, `noise.seedext_record`, `noise.seedext` |
| **R4-B6** | H-6 등급: J-P3·J9·H-7 멈춤, 같은 사례 L1에 없던 FAULT 이름 = 미달, 줄 등급 판정 불가 = 판정 불가, L3 실패 수 기록 | `cmd_noise` |
| R3-E4 | r79 결과 최상위 `commands_sha256`만. 없으면 `기록 불완전` | `noise.h` |

## 실행 예 (앞 판 꼴; R4 판은 모든 명령에 `--expect-head <M4>`가 필수다. 위 "R4 판정 실행 명령 예"를 쓴다)

```powershell
$d = '<repo>\06_analysis\02_control\verif_matrix\v5_resume_4368\path2_v5c'; $r = '<repo>\06_analysis\03_hydraulic\coupled\v5\resume_k1'
$c = 'C:\ProgramData\miniforge3\Scripts\conda.exe'
& $c run -n dynamics-dev python -I -B "$d\p2v5c_stage1.py" --out <o>\h10_h9s.json stage1 --h9 "$r\h9_stage1.jsonl" --h10 "$r\h10_reuse_rerun.jsonl" [--t4h-root <H-10 T4h, 관례 폴더 h10_reuse_rerun_t4h\·t4h\가 없을 때만 1개>] --overlap-ta "$r\h10_overlap_t_a.json"
& $c run -n dynamics-dev python -I -B "$d\p2v5c_grid.py" --out <o>\h9_grid.json grid --vb <stem>="$r\h9_grid\<stem>.json" (4개) --v0-stored <stem>=<저장 V0 c4g2_only/grid> (4개) --v0-sample <stem>="$r\h9_grid_v0_sample\<stem>.json" (4개) [--v0-new <stem>="$r\h9_grid_v0\<stem>.json"] [--family-f "$r\h9_family_F.jsonl"]
& $c run -n dynamics-dev python -I -B "$d\p2v5c_noise.py" --out <o>\h6_h8.json noise --noise-vb "$r\h8_noise_VB.json" --noise-v0 "$r\h8_noise_V0.json" --h6 "$r\h6_dg3_v4on.json" --seedext-vb "$r\h8_seedext_VB.json" --seedext-v0 "$r\h8_seedext_V0.json" --judge-dir <o>\r79_judge --git-at-start <GIT_AT_START(필수)> [--t4h-root <관례 폴더가 없을 때만 1개>]
& $c run -n dynamics-dev python -I -B -m pytest -q -p no:cacheprovider --basetemp <scratch>\pt "$d\test_p2v5c.py"
```

## 동작 확인 (저장 기준선 = 옛 태그·LAS-b 전, 판정 아님, rev4 판)

| 도구 | 결과 |
|---|---|
| noise | 판정기 조건 1: `r79_sensor_judge.py`(sha `6c72b785…`)는 `f46b5ab..HEAD` 0커밋이다. 판정기 4회 실행, 모두 종료 0. L1 게이트 개수는 경로 2와 판정기가 같다(0/0/0, 판정기 출력에 `settings_mismatch` 키 없음). 재집계: L2 실패 5/835(CP 1.25 %), L3 10/501, FLAG 28(`S4_late_loc`). dg3 L3 실패 9는 개정 8 7.1 표의 "L3 9"와 같다. 판정기 `pass`와 다른 줄은 1. seedext 재집계는 `ref|J2|top|Fs0` VB 16/25 대 V0 1/25(Fisher p 5.3e-6, "의심" 문구). 옛 태그라 J-P3가 판정 불가 → H-6·H-8 판정 불가 |
| grid | 저장 V0를 표본으로도 넣으면 8/8 같음 → 저장 V0 짝(경로 확인). 𝓕 통과→실패 2건, `--family-f`가 없어 판정 불가 |
| stage1 | 앞 판과 같다(SA-4 부상 필드가 없어 S8 판정 불가) |

- 저장 기준선 seedext 값은 옛 제어기 결과의 동작 확인일 뿐 436.8 판정이 아니다.
- rev6 판으로 다시 돌린 결과:
  - 판정기 4회 모두 종료 0이다.
  - R5-C3 입력으로 바꾼 뒤에도 seedext 재집계는 같다(`ref|J2|top|Fs0` VB 16/25 대 V0 1/25, slope 3/25 대 0/25).
  - R5-E 기록: `r79_sensor_screen.py`는 `f46b5ab..HEAD` 사이 15줄 추가가 있다. 나머지 세 파일은 차이가 없다. `r79_L3L4_final.py`도 차이가 없다. rev5가 적은 `cf88ea8`이 이 브랜치의 조상이 아니기 때문이다(확인 필요 Q-R11).

- rev7 판 확인(2026-11-13, 판정 아님): `noise.first_done`을 저장 r79 기록 5개(`noise_vb`·`noise_v0`의 L1L2L3, `seedext` VB·V0, `dg3_v4_on`)의 모든 `base` 3,241개에 적용했다. `t_done_s` 모양 2,251 + `timeline` 모양 990, S-11 0. DONE 없음 4개는 모두 `r79_V0_L1L2L3`의 fault 끝 줄(None)이다. rev7 R7-2 근거 사실(DONE 없음 4개 = `r79_V0_L1L2L3` fault)과 맞는다. 스크립트는 scratchpad에 두었고 저장하지 않는다.

## 확인 필요

| # | 내용 | 처리 |
|---|---|---|
| Q-R8 | 판정기 출력에 `settings_mismatch` 키가 없다(저장 기준선으로 확인). R4-B3 대조의 넷째 개수 | 키가 없으면 그 개수는 대조에서 빼고 `None`으로 적는다 |
| Q-R9 | S-4 항목 `ok` 거짓을 하위 항목(`fail_misfire_new`, `miss`, `recontact_new`, 시간 조항)이 설명하지 못하는 줄 | 보수 쪽으로 실패로 두고 사유를 적는다 |
| Q-R10 | (rev5 R5-C3로 닫힘) seedext 판정기 입력 = seedext 파일 + 같은 설정 잡음 파일 | 시드 0~4는 잡음 L2 줄과 키가 같다. 판정기 출력에서는 같은 키의 마지막 줄(잡음 파일 쪽)을 읽는다. H-15가 두 줄의 해시가 같음을 확인한다 |
| Q-R4-1 | (보충 3-1로 닫힘) RD-9 H-8 수에 dg3 대체 135키의 H-8 noise VB 줄을 넣는지 | 넣는다. 뺀 수는 따로 기록(읽기 공개 2) |
| Q-R4-2 | (보충 3-3, 사용자 결정 126으로 닫힘) 최소 간격 [bar]의 값 | `min_gap_bar` 원소를 그대로 옮긴다. `min_gap_Pa` 대체 경로는 뺐다(읽기 공개 1) |
| Q-R4-3 | (보충 3-4로 닫힘) H-10의 U-9 VB 28줄 | 두 목록의 대상(읽기 공개 3) |
| Q-R4-4 | (보충 3-5·3-6으로 닫힘) `bundle` 열 표기·정렬, 격자 run 설정 | `p2_4368.bundle_key`, `results[i].v5_setting`만 |
| Q-R11 | R5-E는 `r79_L3L4_final.py`에 `f46b5ab` 뒤 커밋 `cf88ea8`이 있다고 적었다. `cf88ea8`은 있지만, 이 브랜치 HEAD(master d581df4 위)의 조상이 아니다(`git merge-base --is-ancestor` 거짓). 그래서 `f46b5ab..HEAD`에 그 파일의 차이가 없다. seedext `--keys-file` 옵션이 아직 master에 없을 수 있다 | 기록만 한다. 판정서에서 `GIT_AT_START`로 다시 센다 |

## 독립성 공개 (436.8 9.2)

- 규칙:
  - 436.8 원판·rev1·rev2 전체, rev3(머리·R3-1·C·E·F·G1·G10·9), rev4(머리·R4-0·A·B·9), rev5·rev6(해당 절), rev7 전체(2026-11-13, R7-2·R7-7 반영, 다른 절은 해당 없음 확인).
  - rev7 반영 때 경로 1 코드(`04_scripts/04_hydraulic/coupled/*_4368.py`, `judge4368_common.py`, `resume4368_judge.py`, `chrono_rows_judge_4368.py`, `README_judges_4368.md`)와 경로 1 출력은 열지 않았다. 기록 필드 이름·형식은 rev7 R7-2 원문만 근거로 썼다.
  - rev8 전체(2026-11-13, R8-2·R8-4 반영, R8-1·R8-3은 해당 없음 확인). 반영 때 경로 1 코드·출력은 열지 않았다. 같은 경로 2의 `fd9bb68` 커밋 메시지와 `p2_4368.py` 차이(`check_seals`·`r82_extend_start`·`law_locked_format` 부분)를 읽었다. ③ 판별 근거는 R8-2 원문이다.
  - rev9 전체(2026-11-13, R9-8 봉인 확인·`P2_CORE_SHA` 반영, R9-7 확인 시험 추가, R9-1~R9-6은 해당 없음 확인). 반영 때 경로 1 코드·출력은 열지 않았다. 같은 경로 2의 `b0d6382` 커밋 메시지와 `p2_4368.py`에서 rev9 머리 docstring·LS 처리 줄(grep)만 읽었다. `chrono_rows_manifest.json`은 열지 않았다.
  - 사용자 결정 19 반영(2026-11-13): 같은 경로 2의 `c969b57` 커밋 메시지와 `p2_4368.py` 차이를 읽었다. 또 G-S 하네스 출력 `gs_harness_bbacfd7/h9_grid_r67_main.json`의 태그 위치(`results[i]`·run의 키 유무 수)를 셌다. 이 파일은 러너 출력이고 경로 1 판정 출력이 아니다. 경로 1 코드·출력은 열지 않았다.
  - rev12 전체(2026-11-13, R12-6 봉인 확인·import 고정값, R12-1 세 도구 T4h 입력, R12-3 noise 인자 반영, R12-2·R12-4·R12-5는 해당 없음 확인). 경로 1 코드·출력은 열지 않았다. 같은 경로 2에서는 `6d41462` 커밋 제목, 파일 sha, `p2_v5j.judge_pair`의 J-P3 부분(`strip_jp3`가 지울 발견의 꼴)만 확인했다. 러너 `r79_sensor_screen.py`는 `t4h_file`을 쓰는 줄(925~1014행)만 읽었다(기록 필드 확인, 판정 함수 아님).
  - rev11 전체(2026-11-13, R11-7 봉인 확인·import 고정값, R11-2 stage1 T4h 찾기 반영, R11-1·R11-3~R11-6은 해당 없음 확인). 경로 1 코드·출력은 열지 않았다. 같은 경로 2의 `582fa93`은 커밋 제목, `p2_v5j.py` 차이(R11-2 함수 세 개와 `u9` 호출부), 파일 sha만 읽었다.
  - rev10 전체(2026-11-13, R10-3 봉인 확인·`P2_CORE_SHA` 반영, R10-1·R10-2는 해당 없음 확인). 경로 1 코드·출력과 `chrono_rows_manifest.json`은 열지 않았다. 같은 경로 2의 `a9594dc`는 커밋 제목과 `p2_4368.py` sha만 확인했다.
  - v5 기준 원판과 개정 1~11의 해당 절, `m1_criteria.md` 38~40행.
  - 명세 342.1~342.3, 405~407.1, 419.8·419.8.1, 423.1·423.4, 11025·11980행.
- 원 규칙이 지정한 판정 도구 `r79_sensor_judge.py`(R4-A2 안 c, 경로 2가 실행):
  - 머리 docstring(1~50행)과 `main`(773~822행)만 읽었다. CLI를 알기 위해서다.
  - 판정 함수 본문은 읽지 않았다.
  - 출력은 이 작성자가 직접 만든 것만 읽었다(키 구조).
- 같은 경로 2(dynamics-expert): README, `p2_4368.py`의 공통 부분, `p2_v5j.py`(bf52c89 판) 1~350행과 `main`, rev3·rev4 판의 함수 목록.
- 원 데이터(구조·식별 필드, 동작 확인용): 저장 `v5/main.jsonl`·`pressure_only`·`item8`·`overlap`·`u9_targeted`·`overlap_t_a.json`, `grid_vb/`, `c4g2_only/grid/`, `noise_*`, `seedext/`, `dg3/dg3_v4_on.json`.
- 보지 않은 것:
  - 경로 1 도구: `resume4368_judge.py`, `u3_judge_k1.py`, `resume_k1_*`, `gs_check_*`·`chrono_rows_*`, r67·r69·`las_t3_dg3` 판정 함수와 러너, `dg3v4_judge`, `run_v5.py`, 이전 단계 판정 스크립트.
  - 경로 1이 만든 r79 판정 출력 전부, 저장 r79 판정 파일(`s8/rev79/*judgement*`).
  - 이전 단계 다른 작성자의 경로 2 도구, `seedext_check.json`, `g0_compare.json`.

## 독립성 공개 — R4 작성자 (2-terra 몫, 2026-11-16)

- 작성자: terramechanics-expert의 새 실행. 앞 작성자의 맥락(대화·메모)을 받지 않았다. 경로 1 도구를 만들거나 고친 적이 없다.
- 지시문(전부 읽음): `r4_handoff_path2_terra.md`(sha256 `bafbdd52…`, 1~1,243행 전부; R4 공통 블록 sha256 `e451f067…`를 표지 사이 바이트로 다시 계산해 같음 확인), `r4_supplement_1_path2.md`(sha256 `f3651bf5…`, 1~130행 전부; 보충 1 `8736f68d…`·보충 2 `a9a15a13…` 다시 계산해 같음), `r4_supplement_2_common.md`(sha256 `62721996…`, 1~69행 전부; 보충 3 구간 `5360becf…` 다시 계산해 같음), `r4_supplement_3_common.md`(sha256 `92b62dcc…`, 1~107행 전부; 보충 4 구간 `de45d301…` 다시 계산해 같음), `r4_supplement_4_common.md`(sha256 `7bd7cb17…`, 1~51행 전부; 보충 5 구간 `89cb422d…` 다시 계산해 같음), `r4_supplement_5_common.md`(sha256 `369d1625…`, 1~57행 전부; 보충 6 구간 `0ad43866…` 다시 계산해 같음). 보충 5 대조는 이 폴더 `grid` 코드와 보충 5 문장만으로 했다(규칙 원문 절을 새로 열지 않음).
- 같은 경로 2(`path2/`, 읽기만, import·sha 확인 대상): `p2_v5j.py` 1~589행; `p2_4368.py` 40~239·290~599·805~953·1,269~1,283행과 grep 결과 줄(54~55, 105~107, 147, 231, 298, 320, 363, 382, 465, 502, 571, 813, 869, 884, 2,886~2,955행의 검색 줄만; RD-9 셈 확인 grep 857~866·1,034~1,041·1,091~1,116·1,238~1,244행). 보충 3 반영 때(`2aa0a40` 판) `p2_4368.py` `bundle_key` 1,271~1,276행과 `p2_v5j.py` `j11_item` 319~342행(grep 결과)만 더 읽었다. 보충 4 반영 때는 `path2/`를 더 열지 않았다(`git diff --stat 2aa0a40 8824499`의 파일 목록과 두 파일 sha만 봄). 시험 `path2/` 전체는 실행만 했다.
- 자기 폴더 `path2_v5c/`: 여섯 파일 전부.
- `03_src`(기록 키의 뜻): `outrigger_sim/control/extend_start_bound.py` 20~49·480~639행과 723~724행; `03_src` 전체 grep(`breach_reads`·`extend_bound_check`, `_bar_or_none`·`BAR_PA`)의 결과 줄과 앞뒤 5행(`verify/s6_control.py` 2,989~2,994·3,085~3,090행, `control/two_pressure.py` 130~135행, `sensors/pressure_error.py` 35~40행, `chrono/l2b_actuator.py` 513·630~631·660~662행).
- 원 데이터(키 구조만, 판정 값은 보지 않음): `v5/dg3/dg3_v4_on.json`·`v5/seedext/r79_VB_seedext.json`·`v5/noise_vb/r79_VB_L1L2L3.json`의 `results[].key` 집합(개수·겹침 수)과 첫 항목의 필드 이름, sha256 앞 16자리; `v5/resume_k1/`·`resume_k1/h9_grid/`의 파일 이름 목록. 결과: dg3 키 135개(중복 없음) ⊂ noise VB 키, dg3 ∩ seedext 키 = 0(그래서 보충 2-1의 대체 키 제외는 `h8_noise_VB.json`에만 해당).
- 규칙 파일 원판~rev25: 시험의 봉인 확인으로 바이트 sha만 읽었다. 본문 절은 열지 않았다.
- 열지 않은 것: 지시문 "열지 않는 것" 목록 전부(경로 1 도구·출력과 그것이 import하는 판), scratchpad의 `r4-p1`·`r4-handoff`·`r4-source`·`main`·`p2dyn` 폴더, `r4_handoff_path2_dyn.md`, 원 판정기 `r79_sensor_judge.py`·`r72_judge.py`(이번에 열 일이 없었다), 명세 `s6_control_spec.md`, v5 기준 문서. 이 README와 코드 주석에 있는 경로 1 파일 이름은 이름만 보았고 그 파일은 열지 않았다.
- 시험은 합성 입력만 쓴다. 436.8 하네스 결과 값으로 판정하지 않았다.
