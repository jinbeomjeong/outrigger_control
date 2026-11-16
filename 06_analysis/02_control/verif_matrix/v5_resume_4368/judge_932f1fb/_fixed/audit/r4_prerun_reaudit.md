# 436.8 R4 하네스 판정 실행 전 재감사 (verif-protocol-auditor, 2026-11-16)

## 감사 요약
- 대상
  - 새 R4 = `z4373-r4` `1ab93f0204eee35a39e84a85b2878b35310884b1`. worktree `C:\workspace\z4373-r4`는 clean이다.
  - 병합: p1harness 끝 `295d995` → `0cda003`, p2harness 끝 `f918eca` → `1ab93f0`.
  - master는 `da339b7` 그대로다.
- 기준 문서
  - 원판~rev25 26판
  - 블록 `e451f067`
  - 보충 1~3: `8736f68d`·`a9a15a13`·`5360becf`
  - 보충 4 `de45d301`(`supplement_r4_3.md` `caec9a47`)
  - 보충 5 `89cb422d`(`supplement_r4_4.md` `94944250`)
  - 보충 6 `0ad43866`(`supplement_r4_5.md` `d5c0bf32`)
  - 결정 113~129
  - 경로 2 manifest `scratchpad\r4-p2\p2_manifest_draft.json` `fa0b72bf`
  - 경로 1 실행 스크립트 `run_judgement_path1_draft.ps1` `8e801fa3`
- 판정: 차단 0 / 권고 8 / 참고 10.
  - 앞 감사의 차단 B-1·B-2는 해소됐다.
  - 경로 1 쪽 권고 A-3·A-4는 해소됐다.
  - 아직 남은 것은 메인 몫이다. 경로 2 ps1 관문(A-2·A-3), 기준 집합 비교기(A-1), 기준 집합 sha 기록(A-6), 공개 목록 정리(A-5), blob 표 정의(A-7)이고, 아래에 명세를 적었다.
  - 이 다섯 가지를 만들어 sha로 고정하면 M4 병합과 판정 실행을 할 수 있다.

## 앞 감사 항목 처리 상태

| 항목 | 상태 | 근거 |
|---|---|---|
| B-1 manifest / 섞인 원 파일 | 해소 | 아래 1~5 |
| B-2 계열 𝓕 R-1~R-4 | 해소 | 아래 1~3 |
| A-1 기준 집합 비교기 | 미해결(메인 몫) | 아래 명세 M-1 |
| A-2 경로 2 HEAD | 도구 쪽 해소, ps1 관문은 메인 몫 | 아래 1~2, 명세 M-2 |
| A-3 dirty 검사 | 경로 1 해소, 경로 2는 메인 몫 | 아래 1~2, 명세 M-2 |
| A-4 경로 1 빈 통과 | 해소 | 아래 1~5 |
| A-5 공개 목록 | 미정리 | 아래 "판정서 공개 의무 목록" |
| A-6 기준 집합 sha 기록 | 미해결 | 아래 권고 R-6 |
| A-7 blob 표 정의 | 미해결 | 아래 권고 R-7과 새 blob 표 |

B-1 근거
1. 경로 2 `p2_4368.py harness`에 `kind` `by_setting`이 생겼다(1002~1007, 1092~1098, 1199~1204행). 판별 필드가 없으면 S-11이다.
2. 결과 파일·위치는 원 파일 기준이다(1151행).
3. `R4_INPUTS` 42개 대조(1026~1053, 1063~1089행)와 빠진 묶음 S-15(1370~1393행)가 들어갔다.
4. manifest `fa0b72bf`는 42개 항목, 키 원본 5개, H-9 part 셋으로 보충 4-2 표와 맞다. 아래 R-4를 본다.
5. 경로 1 `r4-inputs`가 43개 원 파일을 단언한다(`resume4368_judge.py:3600-3765`). `r4-lists`는 원 파일을 이름으로 하나씩 읽는다(README_judges_4368.md:106-107).

B-2 근거
1. 경로 1 실행 스크립트에 `family-f --lines h9_family_F.jsonl --grid-root .`(167~168행)과 `family-f-trigger --grid-root .`(164~165행)이 들어갔다.
2. 경로 2는 `p2v5c_grid.py`에서 `--family-f`가 필수가 됐다(646행). 파일이 없거나 이름이 다르면 S-15다(79~98행). R-1~R-4는 항상 계산한다(555행).
3. 첫 판정에 이것이 없었다는 공개는 보충 4 공개 표에 있다.

A-2 근거
1. `p2_d1.py`는 (라) 밖이라 고치지 않았다. 대신 `p2_x16.py d1` 래퍼가 HEAD를 확인한다(`p2_x16.py:606-628`). 나머지 경로 2 하위 명령은 `--expect-head`가 필수다.
2. RD-1 4의 (라) 15개 blob 대조, `03_src`/`02_params` diff 0, clean 확인은 경로 2 쪽에 없다. 메인 ps1 몫이다(M-2).

A-3 근거
1. 경로 1은 `Assert-CleanTree`를 시작과 끝에 돈다(73~79, 197행).
2. head-check는 `--r4`인데 `--files`가 비면 S-11로 멈춘다(`resume4368_judge.py:5081`).
3. 경로 2 시작·끝 관문은 메인 몫이다(M-2).

A-4 근거
1. `-Always`를 단 단계는 `-Only`여도 head_check와 r4_inputs를 돈다(48~50, 84~91행).
2. sidecars 사본이 없거나 identity 파일이 0개이면 throw한다(104~106행).
3. u3 18·u6 4 글롭 수를 단언한다(67~69행).
4. 끝에 rc.tsv 관문이 있다(198~205행).

## 확인 결과

### (2) R4 조건, 봉인, 고정 sha
- R3f..R4는 28개 파일이고 모두 허용 목록 (다)·(라) 안이다.
  - 새 시험 `test_resume4368_supplement4.py`·`_supplement5.py`는 `test_resume4368*.py` 꼴이다.
  - `p2_d1.py`는 바뀌지 않았다.
- `b9f5707..R4 -- 03_src 02_params`는 0이다.
- `b9f5707..R4 -- 04_scripts`는 9개로 rev16:319·rev18:39 범위 안이다.
- R3f..R4에서 바뀌지 않은 것: Chrono 판정 도구, `path2_chrono/`, `chrono_rows_manifest.json`, `.gitattributes`, `00_docs`, 규칙 파일.
- master `8a0c843..da339b7` 변경과 겹치는 파일이 0이라 M4 병합 충돌은 예상되지 않는다.
- 봉인 26판
  - 블록 표, R4 blob, 같은 폴더 `.sha256` 첫 토큰이 26/26 같다. LF이고 BOM이 없다.
  - 네 도구 목록(`judge4368_common`, `resume4368_judge`, `p2_4368`, `p2v5c_common`)에도 26/26 있다.
- `P2_CORE_SHA` `51a0e7cc…`는 R4 `p2_4368.py` blob과 같고, `P2_V5J_SHA` `b815771d…`는 `p2_v5j.py` blob과 같다.
- README sha 표
  - 경로 1 README_judges(`339a5127`, `ac1e84f8`, `5d69e013`, `b46cfa7c`, `e9ae3ed9`, 시험 3개), 2-dyn README 현재 값 표, 2-terra README 표는 모두 R4 blob과 같다.
  - 경로 1 실행 스크립트의 `$Path1Files` 14개 = (다) 14개.
- 보충 구간 sha
  - 보충 4·5·6이 원본과 경로별 사본(`r4-p1`·`r4-p2`의 `r4_supplement_3/4/5_common.md`, 각 `92b62dcc`·`7bd7cb17`·`369d1625`)에서 같다.
  - 경로 1 README와 2-terra README에는 보충 4·5·6 sha가 모두 기록돼 있다. 2-dyn README에는 보충 4·5만 있다(참고 C-5).

### (3) 보충 4~6 반영(각 경로 README 대조 표 기준, 경로 안에서만)
- 경로 1: README_judges_4368.md 106~112행 표와 134행 읽기 11이 보충 4-1~4-5, 5-1~5-4, 6-1~6-4를 덮는다. 실행 스크립트에 `r4-inputs`·`family-f`·`grid-h10`·`grid-v0-sample`이 들어 있다.
- 2-dyn
  - 덮는 범위: README 841~964행 B-1, 보충 3판(보충 4 (a)~(d)), 결정 129 절(5-1 격자 태그 = `results[i].controller_tag`만, 1206~1211행).
  - 보충 5의 나머지(5-2~5-4)와 보충 6은 `path2/` 몫이 아니다. 둘 다 격자 H-10 목록 쪽이고, 그것은 `path2_v5c`가 낸다. 다만 받은 기록이 없다(C-5).
- 2-terra
  - README 56~120행이 보충 4-1~4-5, 5-1·5-3·5-4, 6-1~6-4를 덮는다.
  - 코드 대응
    - 5-2 행 통과 = 기록된 `pass`와 `gates` 논리곱 대조: `row_state`, `p2v5c_grid.py:458`. 다시 계산한 관문은 기록용이다(452~456행).
    - 5-1 짝 열쇠·±1e-9: 471~481행
    - 5-3 (가)(나)(다)·B안: 486~513행
    - 6-2 짝 출처·태그: 226~265, 404~422행
    - 6-3 세 값 적용 조건: 495~512, 569~578행
    - 6-4 표지 "H-10" 하나: 580~596행
- 결정 129의 "격자 run 태그는 `results[i]`만"은 2-dyn harness와 2-terra grid가 모두 반영했다.

### (4) 빈 집합·0건 통과
- `gate_scan`(p2_4368, p2_x16, p2v5c_grid, p2v5c_stage1, resume4368_judge)은 후보 9건을 냈다. 손으로 확인했다.
  - `pass_without_two_gates`(`resume4368_judge.py:3887-3889`), `reduced_pass`(`p2v5c_grid.py:387-389`)
    - 남은 관문의 논리곱이다.
    - 두 관문이 빠지거나 관문 이름 집합이 다르면 그 행을 먼저 판정 불가로 거른다(`p2v5c_grid.py:500-502`). 실제 𝓕 run은 관문이 9개다(보충 5 구조 기록).
    - 결함 아님.
  - `run_pass`(`p2v5c_grid.py:146`): 기록용 재계산 관문이고 None이면 None이다. 결함 아님.
  - `family_f_rule` `"ok": not form`(306행): 문제 목록이 비면 통과다. 앞에서 줄 수 64·위상 16·칸 대조를 한다(296~303행). 결함 아님.
  - 나머지 후보는 R4 범위 밖이다(Chrono 하위 명령, `item8_order` 가드 있음).
- 남은 E 공백(권고 R-1~R-3)
  - `p2v5c_noise --seedext-*`가 선택 인자다.
  - `p2_4368 harness`에 규칙 묶음이 하나도 없으면 입력 대조를 건너뛴다.
  - `p2v5c_grid --v0-sample` 선택 인자다.

### (5) manifest(`fa0b72bf`)와 보충 4-2
- 항목 42개 = H-1 1, H-3 18, H-4 4, H-5 1, H-6 1, H-7 1, H-8 4, H-9 11(본 5, V0-sample 4, family-F 2), H-10 1.
- `h9_family_F.jsonl`은 `path2_v5c` 입력이라 목록에 없다. 이것까지 합쳐 4-4의 43개다.
- `expect_lines` 합: H-1 868, H-3 2,228, H-4 968, H-5 14, H-6·H-7 각 135, H-8 3,106, H-9 본 1,676, V0-sample 84, family-F 192, H-10 440. 4-2·4-4 수와 같다.
- `by_setting`: `h1_d1.jsonl`, `h10_reuse_rerun.jsonl`, `u6_b5_main_VB.json`, `u6_b5_wide_VB.json`
- 키 원본 5개: dg3, noise_vb, noise_v0, seedext VB·V0. `key_source_override`는 `h8_noise_VB.json`에만 있고, H-6 키 원본은 dg3다. `stored`는 없다.
- 모든 경로가 메인 checkout에 있다.
- 도구가 `R4_INPUTS`로 같은 표를 다시 대조하므로 manifest가 어긋나면 S-15로 멈춘다.
- 식별 필드만 센 확인
  - 격자 VB 4파일 `results[i].controller_tag` = `final_C4G2_P3_LAS_K1`, V0 표본 4파일·`h9_family_F_V0.json` = `final_C4G2_LAS_K1`, `h9_family_F_VB.json` = P3 태그. 모두 있다.
  - 저장 V0 격자에는 `controller_tag`가 없다(6-2대로 대조하지 않음).
  - `h9_family_F.jsonl`은 V0 32·VB 32줄이고 모두 FS24이며 태그가 있다.
  - `resume_k1/h9_grid_v0/`는 없다(저장 V0 짝이면 쓰지 않음).

### (6) 실행 명령에서 빠진 단계
- 경로 1: 빠진 단계는 없다(r4-inputs, family-f, family-f-trigger, grid-v0-sample, grid-h10, h11, x16, h12, jp-reuse, r4-lists, 묶음 판정기).
  - `sidecars` 대상 identity 파일은 지금 20개다. 첫 판정 때는 18개였고, 계열 𝓕 두 실행의 identity가 더해졌다. 결과에서 `files = 20`인지 메인이 대조한다.
- 경로 2: README "R4 실행 예"(2-dyn README 708~719행)는 옛 판이다. d1 래퍼·anchors·u9·v5c 단계가 없다. 메인 ps1에는 아래 명세 M-2의 명령을 넣는다.

### (7) 두 경로 독립(R3f..R4 추가 줄, 이름 사전 두 개)
- 경로 2 쪽에서 `family-f` 8건이 걸렸는데, 경로 2 자기 CLI 인자 `--family-f`다.
- 경로 1 쪽에서 `KIND_TAG` 7건이 걸렸다(`test_resume4368_supplement4.py:23`의 `KIND_TAG = judge.KIND_TAGS`). 경로 1 자기 상수의 별칭이다. 이름이 같은 것은 우연으로 본다[추정].

### (8) 시간 순서
- 보충 4 파일 13:49:44(사본 13:51:44) < `8824499` 13:57, `c8197f6` 14:00, `8130954` 14:07.
  - `680aac8`(13:42)은 보충 4보다 앞서지만, 결정 127 (a) B-1 몫이다. 보충 4와의 차이는 결정 128 뒤 `8824499`에서 맞췄다.
- 보충 5 파일 14:11:36(사본 14:12:15) < `5125134` 14:19, `f3bd686` 14:20, `6139bb2` 14:23.
- 보충 6 파일 14:24:13(사본 14:26:57) < `f918eca` 14:33, `7ece9a1` 14:35.
- manifest `fa0b72bf` 13:56:41. 그 뒤 `R4_INPUTS`를 바꾼 커밋은 없다(`6139bb2`는 태그 읽기만).
- R4 판정 출력은 아직 없다.

## 권고 (실행 전 수정, 메인 몫)

### R-1 [E] `p2v5c_noise --seedext-vb/--seedext-v0`가 선택 인자다
- 근거: `p2v5c_noise.py:680-681`, `:476`, `:595-608`.
- 빼먹으면 H-8 seedext 100줄의 J-P3·J11 목록, RD-8~RD-10 수, seedext 기록이 경로 2에서 소리 없이 빠진다.
- 권장: 메인 ps1에 두 인자를 넣는다. 출력에 seedext 블록이 있는지 단언한다.

### R-2 [E] `p2_4368 harness`의 입력 대조가 조건부다
- 근거: manifest에 원판 5.1 묶음이 하나도 없으면 `r4_input_check`와 빠진 묶음 S-15를 건너뛴다(`p2_4368.py:1375`).
- 권장: 메인 ps1이 harness 출력에서 다음을 단언한다.
  - `bundles`에 H-1·H-3~H-10 9개가 있다.
  - `r4_input_check.expected_files` = 42이고 `stops`가 없다.
  - `bundles.H-9.parts`가 셋 다 있다.

### R-3 [E] `p2v5c_grid --v0-sample`이 선택 인자다
- 근거: 빠지면 짝 출처가 판정 불가가 된다(`p2v5c_grid.py:236-239`). 기록만 하고 멈추지 않는다.
- 권장
  - `--v0-stored` 4개와 `--v0-sample` 4개를 꼭 넣는다.
  - 출력 `v0_pair.source` = `stored`이고 `sample.jobs` = 8인지 단언한다.
  - 경로 1 `grid_v0_sample.json`·`grid-h10`의 짝 출처와 대조는 판정서에서 K-10으로 한다.

### R-4 [공개·정체성] manifest 판 차이
- 근거
  - 결정 128 메모리는 control-expert 초안 `a069ce97…`(`r4-handoff\p2_manifest_draft.json`)을 적고 있다.
  - 실행에 쓸 것은 2-dyn이 `R4_INPUTS`로 만든 `fa0b72bf…`(`r4-p2\`)다(2-dyn README 904·916행).
  - 둘은 6개 항목이 다르다. 초안은 `H-9-V0-sample`·`H-9-family-F` 묶음 문자열을 쓰고, 𝓕 원 실행을 `r79_json`·`expect_lines` 2·`family_run`으로 적었다.
  - 초안을 R4 도구에 주면 입력 대조 S-15로 멈춘다.
- 권장: 결정 기록과 판정서에 실행 manifest = `fa0b72bf…`, 만든 이(2-dyn, `R4_INPUTS`), 판정 출력 폴더에 넣을 사본의 sha를 결과 전에 적는다. 초안 `a069ce97`은 쓰지 않는다.

### R-5 [I] d1 래퍼의 HEAD 확인 증거
- 근거: `p2_x16.py d1`은 `head_check`를 stdout 첫 줄에만 쓴다(620행). `--out`은 `p2_d1`의 출력이다.
- 권장: 메인 ps1에서 이 단계의 stdout을 파일로 저장한다(`> <o>\logs\d1.out.txt`). Tee+return 함수 꼴은 쓰지 않는다.

### R-6 [T] 기준 집합 sha를 판정서 초안에 적는다(A-6, 그대로 남음)
- 근거: scratchpad에서 `a5627304`를 담은 파일은 앞 감사 보고서뿐이다.
- 권장: M4 병합 전에 판정서 초안이나 결정 기록에 시각과 함께 적는다. 적을 것: `a5627304…`, 뽑은 이, 시각 11:35:36(고정 11:36:07), 출처 87개 목록 sha, 뽑기 스크립트 sha.

### R-7 [S] R4 blob 표는 raw 바이트로 적는다(A-7, 그대로 남음)
- 근거
  - `p2v5c_common.py`(raw `6640cc93` / LF `53a76654`), `p2v5c_grid.py`(`88e54e34` / `661fa5d4`), `p2v5c_stage1.py`(`d49cf4e6` / `25a33dd3`)는 CRLF blob이다.
  - 2-terra README·`merge` 단계는 raw sha를 쓰고, 경로 1 head-check는 LF 정규화 sha를 쓴다.
- 권장: 메인의 (라) 대조와 판정서 blob 표는 `git show` raw sha로 한다. 아래 표가 이번 감사 값이다.

### R-8 [공개] 판정서 공개 의무 목록이 흩어져 있다
- 권장: 아래 목록을 판정서 한계 절의 표 하나로 모은다(A-5).

## 메인이 만들 것: 명세

### M-1 기준 집합·고정 집합 비교기(A-1)
- 입력
  - 경로 1: `harness_path1\r4_lists.json`(`lists.J-P3`·`J11`·`S-6`, `markers`), `u3_judge.json`(G-5·G-6 목록), `h11.json`(G-3), `grid_h10.json`, `family_f.json`, `jp_reuse.json`
  - 경로 2: `harness.json`(`stop_S6_list`, `bundles.*.gates`), `p2v5c_merge.json`(J-P3·J11 목록, RD-8~RD-10 수), `p2v5c_grid.json`(a·b·c, 적용 조건, `h10_grid_term`, `v0_pair`, family F), `u3.json`(`G-5_list`·`G-6_list`), `g3.json`, `jp.json`
  - 기준: `r4_baseline_sets.json`(`a5627304`)
  - 입력마다 sha256을 출력에 적는다.
- 열 이름 대응(결과 전 고정)

  | 대상 | 경로 1 | 경로 2 harness | 경로 2 v5c | 기준 파일 |
  |---|---|---|---|---|
  | 결과 파일 | `result_file` | `result_file` | `file` | `file` |
  | 위치 | `location` | `position` | `position` | `location` |

  묶음·다리·k·키·설정은 같은 이름을 쓴다. 이름이 다르면 이 표에 더한다.
- 비교
  1. RD-7 2: 두 경로 목록이 (묶음, 결과 파일, 위치[, 다리] / S-6은 k까지) 집합으로 같고, 값 열이 RD-5 허용 오차 안이다. 한쪽에만 있는 줄과 값 차이를 출력한다.
  2. JD-1: J-P3 목록 (묶음, 파일, 위치, 다리) 집합 = `jp_base` 5줄.
  3. JD-3: S-6 목록을 (묶음, 파일, 위치)로 줄인 집합 = `s6_base` 67줄. 어느 경로든 목록이 비면 멈춘다.
  4. JD-2: G-5 키 집합 = 5키(블록 JD-2).
  5. JD-7: G-6 키 집합 = 3키(블록 JD-7).
  6. JD-8: 묶음 H-1·H-3·H-4의 `J-P3 입력 형식(RD-8)` 표지 유무가 두 경로에서 같다.
  7. 보충 5·6
     - (가)(다) 목록, N_raw·N_F
     - (나) 표와 세 값 적용 조건
     - 기록(실패→통과·실패→실패·FAULT 행·판정 불가 행)
     - 짝 출처
     - 표지 "멈춤 H-10" 유무
     - 계열 𝓕 R-1~R-4 결과(k, 네 조건, 위반 목록)
  8. RD-11 J_P 행 항목과 재사용 값, H-11 G-3 참거짓과 거짓 짝 목록.
- 출력: 항목별 `equal` / `differ` / `missing`과 차이 목록, 입력 sha. 종료 코드는 0 모두 같음 / 1 차이 / 2 입력 오류(파일 없음, 빈 목록, 키 없음).
- 비교 스크립트와 열 대응표의 sha를 결과 전에 결정 기록에 적는다.

### M-2 경로 2 ps1(A-2·A-3, 단계별 stdout·stderr를 파일로, 단계별 exit와 `out_sha256` 기록)
- 공통: 인터프리터는 `conda run -n dynamics-dev python -I -B`, 출력 폴더는 `judge_<M4 7자리>\harness_path2\`(경로 1과 같은 7자리)다.
- 실행 순서
  0. 시작 관문(하나라도 거짓이면 아무것도 돌리지 않고 멈춘다)
     - `git rev-parse HEAD` = M4 40자리
     - `git status --porcelain --untracked-files=no`가 빈 출력
     - (라) 15개 파일마다 `git show <M4>:<f>`와 `git show <R4>:<f>`의 raw sha256이 같음
     - `git diff --name-only b9f5707..<M4> -- 03_src 02_params`가 빔
     - manifest 사본의 sha256 = `fa0b72bf…`
     - 원 결과 파일 43개, 키 원본 5개, 저장 V0 격자 4개가 있음(보충 4-4)
  1. `path2\p2_4368.py --out <o>\seal.json seal`
  2. `path2\p2_4368.py --out <o>\harness.json harness --manifest <o>\manifest.json --expect-head <M4>`, 그리고 R-2 단언
  3. `path2\p2_4368.py --out <o>\anchors.json anchors --h1 <RK>\h1_d1.jsonl --expect-head <M4>`
  4. `path2\p2_4368.py --out <o>\jp.json jp --shadow <V5>\las\shadow_jp_b0.jsonl --batch 07_results\S9\batch_V5-JP-VB_20261108_115631 --batch 07_results\S9\batch_V5-JP-V0_20261108_131212 --expect-head <M4>`
  5. `path2\p2_x16.py --out <o>\g3.json g3 --h11-dir <X>\H-11 --expect-head <M4>`. G-3이 거짓이면 H-3·H-4 등급을 쓰지 않고 멈춘다.
  6. `path2\p2_x16.py d1 --expect-head <M4> -- --h1 <RK>\h1_d1.jsonl --out <o>\d1.json`, stdout을 파일로 저장(R-5)
  7. `path2\p2_u3.py --out <o>\u3.json`에 다음 인자를 붙인다: u3 18파일을 `--u3 V0=…`·`--u3 VB=…`로 이름별로, `--u6 ALL=<u6_b5_main_VB.json> --u6 ALL=<u6_b5_wide_VB.json> --u6 IND_LAS=<u6_b5_main_VB_IND_LAS.json> --u6 IND_LAS=<u6_b5_wide_VB_IND_LAS.json> --h1 <RK>\h1_d1.jsonl --expect-head <M4>`. 출력의 U-3 키 수와 U-6 242를 확인한다.
  8. `path2\p2_v5j.py --out <o>\v5j_u9.json u9 --v0 <RK>\h5_u9_v0.jsonl --vb <…> --expect-head <M4>`. `--vb` 등 나머지 인자는 2-dyn README H-5 절과 첫 판정 실행 기록으로 정한다(첫 출력에 argv가 없다).
  9. `path2\p2_x16.py --out <o>\c16.json c16 --out-root <X> --expect-head <M4>`
  10. `path2\p2_x16.py --out <o>\rd13_items.json items`
  11. `path2_v5c\p2v5c_stage1.py --expect-head <M4> --out <o>\p2v5c_stage1.json stage1 --h9 <RK>\h9_stage1.jsonl --h10 <RK>\h10_reuse_rerun.jsonl --overlap-ta <RK>\h10_overlap_t_a.json`
  12. `path2_v5c\p2v5c_grid.py --expect-head <M4> --out <o>\p2v5c_grid.json grid`에 다음 인자를 붙인다. 출력의 `v0_pair.source`를 단언한다(R-3).
      - `--vb <stem>=<RK>\h9_grid\<stem>.json` ×4
      - `--v0-stored <stem>=06_analysis\02_control\touch_phase\acceptance\c4g2_only\grid\<stem>.json` ×4
      - `--v0-sample <stem>=<RK>\h9_grid_v0_sample\<stem>.json` ×4
      - `--family-f <RK>\h9_family_F.jsonl`
  13. `path2_v5c\p2v5c_noise.py --expect-head <M4> --out <o>\p2v5c_noise.json noise --noise-vb … --noise-v0 … --h6 … --seedext-vb … --seedext-v0 … --judge-dir <o>\p2v5c_r79_judge --git-at-start b9f5707d7f3f7a26230b25f4edbc1fec587ca612`(R-1)
  14. `path2_v5c\p2v5c_stage1.py --expect-head <M4> --out <o>\p2v5c_merge.json merge --part <o>\p2v5c_noise.json --part <o>\p2v5c_stage1.json --part <o>\p2v5c_grid.json`
  15. 출력 전체 sha256 목록 파일(경로 1 6단계와 같은 꼴)
  16. 끝 관문: HEAD·clean 다시 확인. 단계별 기대 종료 코드 표(결과 전 고정)로 rc를 가른다.
- 쓰지 않는 것: `--allow-import-sha`, `--gs`, `--t4h-root`. 관례 폴더가 없을 때만 `--t4h-root`를 쓰고, 그 경우 결과 전에 정한다.
- ps1 안에서 `Tee-Object`와 `return`을 함께 쓰는 함수를 만들지 않는다.
- 첫 판정 경로 2의 도구 밖 보조 출력은 결정 127대로 "규칙 요구분만, 나머지 미재현 공개"다.

## 판정서 공개 의무 목록(모아 둔 것)

| 출처 | 항목 |
|---|---|
| 블록 JD-6 1~30 | 그대로(r4_common_block_draft.md:109-140) |
| 보충 1·2 공개 표 | 1-2, 2-1, 2-2, 2-3, 2-4, 2-5, 2-6, 2-7(supplement_r4_1.md:162-172) |
| 보충 3 공개 표 | 3-1, 3-3, 3-7(supplement_r4_2.md:98-104) |
| 보충 4 공개 표 | 4-1·4-3, 4-3(판별 결측 S-11), 4-2(키 원본 H-6·H-8만), 4-2(H-9 네 부분), 4-2(V0 표본 S-6), 4-5(첫 판정 𝓕 누락), 4-4(43개 단언)(supplement_r4_3.md:124-134) |
| 보충 5 공개 표 | 5-3 (다) B안(고르지 않은 안 C·A, 작성자가 값 안 봄, 첫 판정 출력은 메인·앞 검토가 봄), 5-1 격자 태그 우선, 5-2 pass 정의, 5-1 짝 열쇠, 보충 5 전체(첫 판정 H-10 수치 안 씀)(supplement_r4_4.md:98-106) |
| 보충 6 | 공개 절이 따로 없다. 판단 요약 (i)~(vii)(supplement_r4_5.md:17-25)을 "규칙 문장으로 닫힘 / 권고안으로 닫음"과 함께 싣기를 권한다. 특히 (v) 등급 순서(판정 불가 > FAULT 미달)와 (vi) 세 값 적용 조건 |
| 결정 113 | rev26 후보, 새 판정서 문서, 0절 종합 문장 갱신 |
| 결정 122 | 멈춤 S-6 목록 대상 묶음을 닫음, J-P3 목록에서 H-1·H-3·H-4 뺌, RD-4 이름 구분(JD-6에 줄 없음) |
| 결정 123 | MD-3 출처를 본 뒤 고름: H-4 41줄 뺌, H-3 4줄을 경로 1 B판에서 넣음. 시나리오 ① twin FL과 위반 다리 RR 구분(JD-6에 줄 없음) |
| 결정 124 | 보충 2-3·2-4·2-6 줄로 덮임 |
| 결정 125 | `sidecars` 보존 사본(`0962f639`, R4 blob 밖). rc `.done` 0개·2개 이상·`exit=` 없음 = 기록 불완전(control-expert가 더함). `@` 토큰(3-7 줄) |
| 결정 126 | 3-3 줄로 덮임 |
| 결정 127 | 첫 판정은 섞인 파일을 나누고 합친 입력을 썼다(4-1 줄). 첫 판정 경로 2 보조 출력은 R4에서 미재현이다(규칙 요구분만). R4를 재생성한 경위(옛 R4 `2ceafef`는 `z4373-r4-discarded-2ceafef`로 남김) |
| 결정 128 | 읽기 4건 그대로 + 공개(보충 4 줄). 2-dyn `680aac8` 차이를 `8824499`에서 맞춤. 실행 manifest `fa0b72bf`이고 초안 `a069ce97`과 다름(R-4) |
| 결정 129 | 보충 5 줄들과 같다. 격자 태그 공통 정의가 앞 판(결정 19)보다 앞선다 |
| 메인이 결과 전에 본 첫 판정 출력 | 메인이 첫 판정 경로 1 출력 `grid_v0_sample.json`(8/8 같음)을 R4 전에 열었다. 첫 판정 출력은 기록만이라는 RD-3 3(두 경로 대상)과 별개로, 짝 출처 판단에 쓴 정보이므로 언제·누가 봤는지 공개한다 |
| R4 작성자가 함께 본 값 | 2-dyn README 759·782행(구조 확인 중 함께 출력된 값), 경로 1 README "읽은 것" 5번(H-11 8키 양쪽 건수) |
| 도구 범위 | 경로 1 `x16-records`가 import하는 Chrono 판정 모듈은 M4 blob이 R4 blob과 다르다(`25effee`, `TOOL_VERSION` 문자열만). `p2_d1.py`는 (라) 밖이라 래퍼로 HEAD를 확인한다 |
| 2-dyn 보충 6 | 받았는지와 "해당 없음" 확인 기록이 README에 없다(C-5) |

## 참고
- C-1 B-1·B-2와 A-3·A-4(경로 1)는 해소됐다(위 표).
- C-2 R4 조건, 봉인 26판, `P2_*_SHA`, README sha 표, 보충 sha가 모두 맞다.
- C-3 manifest `fa0b72bf`는 보충 4-2와 같다. 도구가 `R4_INPUTS`로 다시 대조한다.
- C-4 [추정] 두 경로의 잠복 차이가 하나 있다. u6 기록에서 `controller` = ABL인데 태그가 없을 때 경로 1은 S-3(`resume4368_judge.py:3666-3668`, 태그 None도 "ABL 아님"으로 셈), 경로 2는 S-11이다(`p2_4368.py:1218-1221`, 태그가 문자열일 때만 ABL 대조).
  - 지금 R2 파일은 태그가 모두 있어 걸리지 않는다. 두 경로 모두 멈추는 경우라 등급이 갈리지는 않는다.
  - 판정서 정의 차이 표 후보이고, 작성자에게는 넘기지 않는다(교차 정보).
- C-5 2-dyn README에 보충 6(`0ad43866`) 기록이 없다. 내용상 보충 6은 `path2_v5c` 몫이라 `path2/` 코드 변경은 필요 없어 보인다. 2-dyn에 보충 6을 넘겼는지와 "해당 없음" 기록 여부는 메인이 확인한다.
- C-6 2-dyn README "R4 실행 예"(708~719행)는 옛 판이다. 실행은 M-2를 따른다.
- C-7 첫 판정 `sidecars`는 identity 18개였고, 지금은 20개다(`h9_family_F_{VB,V0}.identity.json`이 더해짐).
- C-8 이름 사전 검사에서 걸린 2건은 각 경로 자기 이름이다(위 (7)).
- C-9 `gate_scan` 후보 9건은 모두 결함이 아니다(위 (4)).
- C-10 보충 6 확인 필요 1(`h9_grid_v0/` 없음)은 표본 8/8 같음이면 저장 V0 짝이라 쓰이지 않는다. 경로 1 `grid-h10`·경로 2 grid의 짝 출처 출력이 "저장"인지 판정서가 확인한다.

## R4 blob 표 (`1ab93f0`, `git show` raw sha256)

| 파일 | sha256 |
|---|---|
| 04_scripts/04_hydraulic/coupled/README_judges_4368.md | 3b1fa4b09ad27b04f75cb0e2856d376ff832ce0fa176eb2da60f5d7b89309032 |
| 04_scripts/04_hydraulic/coupled/h6_judge_4368.py | e9ae3ed9866dd8cc91ba8db275985544c1ab489bb297f9d672d3f8b7a224c31e |
| 04_scripts/04_hydraulic/coupled/h8_noise_judge_4368.py (변경 없음) | c037fe9ea8a10c1ba208a441ad2be1218d62841246db001e9d5ba9a54a3acf69 |
| 04_scripts/04_hydraulic/coupled/judge4368_common.py | 339a51277c064ae98105dc01fadd492f67fb2c1866e3eac675cc2856b34d2a52 |
| 04_scripts/04_hydraulic/coupled/judge_stage1_4368.py | 5d69e01335b2bd73397e4679423661046a53761cb646b91679834e6b0ae2d4ee |
| 04_scripts/04_hydraulic/coupled/u3_judge_4368.py | b46cfa7cc80211905c1c83c9bce5e8b16c2d567e2cc267b08c68d3854766096e |
| 05_tests/unit/test_judges_4368.py | d46ed1568225fc822588ee73c410b82068e9daed2ba7c793efef2168ea912703 |
| 05_tests/unit/test_judges_4368_h6_h8.py | ea81a4c6bc526ac8fec9b9b38516e58df89e37916a7f41dbea32cefd7e98b259 |
| 05_tests/unit/test_resume4368.py | b8851f7d80a8a185a577dd66f1a3a991511ce0fe60129bc64ee175fd37ac0498 |
| 05_tests/unit/test_resume4368_rev1.py | 407699a71b2ef6ce06aebe1be0cfd3c53cfe7a67ee513ed02901ae692975cc13 |
| 05_tests/unit/test_resume4368_rev16.py | 761f3d110da9958453faf35f71e147511e363465ce7509047d4798d3c4f1acc2 |
| 05_tests/unit/test_resume4368_supplement4.py | 1945148f8c2e05896ee07dbcc0b32fc5ba3399b0099dd4d13d3cacd4f0c1397e |
| 05_tests/unit/test_resume4368_supplement5.py | e443b5539052b73c86ec25a34884430a97ab1db788719d0bd9323204d2c45ae7 |
| .../verif_matrix/scripts/resume4368_judge.py | ac1e84f85b4f4534d11c5248169720ac4f7026a3ab65e96360e8bd650563ffbb |
| .../v5_resume_4368/path2/README.md | f1803a5852a387630bf2cd5c8f43de114e1267e4e151b93dbbe35f999d5e0dd4 |
| .../path2/p2_4368.py | 51a0e7ccca2a6cbd3abfdf0c09d27fb03eac6985c31954e0b526c075ceba12e6 |
| .../path2/p2_u3.py | 7eb119223dfbb5236ee43213843edb1ae4e2ea1e618b5a33b72ae22660ffaf72 |
| .../path2/p2_v5j.py | b815771dcaee69f5b474a7a6328f7699631d4c69309a973314a0ba3eaf06ecb8 |
| .../path2/p2_x16.py | e17a144c38b3fc3a8b8f5b47209be0d3711a3ccba643863be44a820d275223e5 |
| .../path2/test_p2_4368.py | cd9c10a3aa8d2f5ed5e3bcd0c8e6bf301b84d153d663e7d76786d8f1e7fd7985 |
| .../path2/test_p2_u3.py | 533501dd889e8f263eee8215910d18f451bc0fca576732c8eb452d527a619c23 |
| .../path2/test_p2_v5j.py | 017d432730bc6e52d11fc116cd29692f1af3b38b4d098b53f80edb7a061f9092 |
| .../path2/test_p2_x16.py | c7efdefd7e7c6633823d6283d72086623055c6c73acafc40307b64b695f890d8 |
| .../path2_v5c/README.md | c64a5282f42a68481c7389b61a063c8ba190952d8da37589b4eefd69f5c02888 |
| .../path2_v5c/p2v5c_common.py (CRLF blob) | 6640cc93d58a3eafe875e7b890472ac68263a31f511ea9d8f18123f69476fa82 |
| .../path2_v5c/p2v5c_grid.py (CRLF blob) | 88e54e3438b145c2f6459e8fa1ea61acf819e1ae7f93311276216137cc476388 |
| .../path2_v5c/p2v5c_noise.py | 7fa4153fe254d0d59d2f4dbb94b543f9235b6b76adea071ee637b16a73a112a1 |
| .../path2_v5c/p2v5c_stage1.py (CRLF blob) | d49cf4e617eb55283b68907524e56c6bd6659a93c656a9280ad0d24fe3421996 |
| .../path2_v5c/test_p2v5c.py | 4793f54b31bb94cf6f1f3b64bc217efef998a08de543a025be7fddf5436fbb37 |

## 확인 필요
- Q1 2-dyn에 보충 6을 넘겼는가? 넘겼다면 "path2/ 해당 없음" 확인을 README나 기록에 남길지, 판정서 공개로만 할지 정해야 한다.
- Q2 경로 2 `p2_v5j u9`의 `--vb` 등 인자 출처: 첫 판정 출력에 argv가 없다. 메인의 첫 실행 기록에서 같은 인자를 확인할 수 있는가? 없으면 2-dyn README H-5 절대로 정해 결과 전에 고정한다.
- Q3 C-4 잠복 차이(ABL·태그 없음)를 지금 정의 차이 표에 올릴지, 걸릴 때만 다룰지 정해야 한다(지금 데이터에서는 걸리지 않는다).

## 메인 세션 권고
- M-1·M-2를 만들어 sha를 고정하고, R-4·R-6 기록을 남긴 뒤 M4를 병합한다. 그다음 판정 전 감사(MD-2)에서 M-1·M-2 스크립트, manifest 사본, blob 표 대조 결과를 본다.
- 두 경로 자체 시험을 R4 또는 M4에서 한 번 돌려 통과 수를 판정서에 적는다. 이 감사에서는 돌리지 않았다.

## 검사하지 못한 것
- 경로 1 `grid-h10`·`family-f`·`r4-inputs`의 함수 단위 세부 로직(README 대조 표와 핵심 상수·입력 표만 봤다), 경로 2 `p2_u3`·`c16`·`g3` 변경분 세부.
- 자체 시험 실행.
- 결과 값은 열지 않았다. 식별 필드(태그·설정·run 수·manifest 입력, 첫 판정 `sidecars.json`의 파일 수)만 셌다.

## 실행한 검증
- 인터프리터: python-dev `-I -B [-X utf8]`, `MKL_THREADING_LAYER=TBB`. 프로젝트 모듈은 import하지 않았다.
- 도구: `gate_scan`(5파일, 후보 9건을 손으로 확인), `source_guard` snapshot/verify.
- 즉석 스크립트(`scratchpad\audit-r4-reaudit\`, 보고 전에 지움)
  - `suppsha.py`, `seals_blobs.py`
  - `mcmp.py`(manifest 두 판 대조·파일 존재·수)
  - `gridtags.py`(격자·계열 𝓕 태그·설정·run 수)
  - `leak.py`(이름 교차)
- git 조회 명령만 썼다.
- 다시 확인한 것: R4 HEAD `1ab93f0`, worktree clean, master `da339b7`.
- 원본 불변: (핸드백 말미 source_guard verify report_line)
- 사용한 스킬: 없음
