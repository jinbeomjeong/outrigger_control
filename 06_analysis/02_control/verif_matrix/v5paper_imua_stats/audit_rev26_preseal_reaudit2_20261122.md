# verif-protocol-auditor: rev26 봉인 전 수정 3 재재감사 (2026-11-22)

(hand-back 원문 그대로)

## 감사 요약 (rev26 봉인 전 수정 3 재재감사, [시점] 실행 전)
- 대상과 sha
  - `v5_resume_4368_rules_rev26.md`(9ed66348): 머리말이 "봉인 전 수정 3"인 것을 확인했습니다(:1, :8).
  - 부록 `excl_fields_r2.py`(bda5e7da), `rev26_excluded_fields_r2.json`(f450784b)
    - LF이고 CRLF는 0입니다.
    - :214 명령으로 다시 만들면 sha가 같고, d 1,036(I 103 / S 672 / F 172 / N 89), c 13으로 :211과 같습니다.
  - 점검 스크립트 `excl_check.py`(d00f2c54), `abs_roots.py`(c3bcd25f)
  - A형 `v5paper_imua_rules_draft.md`(f2b68f69, 수정 6)
- 본 결과: 스크립트로 `judge_932f1fb` 출력 72개를 읽었습니다. 출력한 것은 다음뿐이고, H-3·H-4 값과 판정서는 열지 않았습니다.
  - 키 경로, 범주, 개수, 봉인 블록의 하위 키 꼴
  - 64자리 16진 값이 `git show 932f1fb:<파일>` sha와 맞는지(맞은 파일 이름만)
  - 절대 경로 문자열 안에서 루트의 위치(앞머리·중간)만 셈
- **판정: rev26은 차단 1 / 실행 전 수정 3 / 기록 3 → 아직 봉인 불가.**
  - 고칠 것은 5단계 실행본에서 바꿀 줄 목록 하나입니다.
  - 그 밖의 지난 지적(N-1·N-2·W-a~W-e·R-a·R-c·R-d)은 닫혔습니다.
- **A형(수정 6)은 차단 1**입니다(A-2). 같은 원인에 경로 2 실행본 관문이 더해집니다.

## 닫힌 것
- **N-1(도구 판 필드)**
  - S에 `diff_vs_existing`·`definition_changes`·`common_sha256`·`imports.*_sha256`를 넣었습니다(`excl_fields_r2.py`:115, :202-205).
  - `--expect-head <커밋>` 원소는 I로 빠집니다(:173).
  - **4′ "도구 sha 잎 0건" 점검은 실제로 돌고, 지금 0건입니다.** 비교 대상 잎 가운데 64자리 16진 값을 허용 목록 파일(경로 1 실행본 :30-43의 14개 + `path2/`·`path2_v5c/` 전체)의 `932f1fb` raw·LF·CRLF sha와 대조했습니다.
  - 허용 목록 밖에서는 6건이 비교에 남습니다. 모두 T26이 바꾸지 않는 파일이라 안정 확인으로 남는 것이 맞습니다.
    - `v5_options.py`: `p2v5c_grid`·`noise`·`stage1`·`v5j_u9` 4건
    - `04_scripts/03_control/s8/r79_sensor_judge.py`: `p2v5c_noise :: judge_tool.sha256`
    - `c2.py`: `h6_L1_reference :: meta.c2_py_sha256`. 이 값은 저장 입력의 메타를 옮긴 것입니다(`h6_judge_4368.py`:257, `r79_L3L4_final.py`:285-286).
- **절대 경로**: 비교 대상 절대 경로 문자열 가운데 N 표시가 없는 것은 0건, N 표시는 249건입니다(13파일, 대부분 `log_errors :: steps[].log` 142건).
  - 작성자 집계 334건(:206)은 빠지는 경로까지 센 수로 보입니다. 기록 수준입니다.
- **N-2((h)와 출력 꼴)**: 실측한 경로 1 `rules_seal` 꼴과 :82-86·:133이 맞습니다.
  - revisions 꼴(`expected/rules_file/seal_file`) 43개
  - 파일 꼴(`file/pinned/seal_file` + `rules_dir`) 6개
  - 없음 8개
  - `u3_judge :: G-3.rules_seal` 1개(revisions 꼴)
  - S 규칙에 `u3_judge`의 `G-3` 범위를 넣었습니다(:199).
- **B-2 노드**: 비교 대상 그대로입니다.
- **W-a**: C2 → `final_C4G2_P3_LAS_K1` 대응을 명시했습니다(:37). 입력 실측의 네 쌍과 맞습니다.
- **W-b**: 저장소 사본 sha가 실행본 고정값과 같습니다(fa0b72bf…, 0962f639…).
- **W-c**: 인터프리터를 바꾸지 않는다고 적었습니다(:79).
- **W-d**: `t26_identity.json`에 외부 도구 sha와 환경을 고정합니다(:80).
- **W-e**: 각 쪽이 자기 목록을 지웁니다(:169, :173).
- **R-a**: CRLF 바이트 sha(:132). **R-c**: 결과 뒤 예외 둘째를 0절에 공개(:25). **R-d**: (:28)

## 발견 사항

### [차단][R·I] N-3b worktree에서 돌린다는 결정(:65-66)이 5단계 실행본의 "바꿔도 되는 줄"(:73-79)에 반영되지 않음
- **근거**
  - 경로 1 `run_judgement_path1_M4.ps1`
    - :12 `Set-Location C:\workspace\outrigger_control`
    - :26·:27 도구를 상대 경로로 부릅니다(`$Judge='06_analysis/…/resume4368_judge.py'`, `$Co='04_scripts/…'`).
    - :29 `$X='07_results/S9/…'`와 :23·:25 입력도 cwd 기준 상대 경로입니다.
    - head-check(:84)에는 `--root`가 없어 기본값인 스크립트 자신의 저장소(`resume4368_judge.py`:181 `ROOT = HERE.parents[3]`)에서 HEAD를 봅니다.
    - jp-reuse 등 하위 명령도 `--root` 기본값이 `ROOT`이고 "checkout with the R2 results"입니다(:5127·:5210·:5217).
  - 경로 2 `run_judgement_path2_M4.ps1`
    - :23-24 `$Repo='C:\workspace\outrigger_control'` + `Set-Location $Repo`
    - 도구 `$P2`·`$V5c`와 입력 `$Rk`·`$X`가 모두 `$Repo` 아래입니다(:40-46).
    - 관문 :184-192는 cwd에서 `git rev-parse HEAD`와 `b9f5707..$M4 -- 03_src`를 봅니다.
  - rev26 :73-79가 허용하는 변경은 `$M4`·`$R4`, 출력 폴더, `$AllowListPath2`, `$FirstSidecars`, `$ManifestSource`뿐입니다. cwd, 도구 루트, 입력 루트를 나누는 줄은 없습니다.
- **실패 시나리오**
  - 허용 줄만 바꾸면 메인 checkout의 도구(master 판)가 돌고, head-check가 메인 HEAD ≠ T26으로 S-12가 되어 "nothing judged"입니다. :142에 따라 이것도 1회로 셉니다.
  - cwd를 worktree로 바꾸면 git 밖의 `07_results/…`(`$X`, J_P 배치)가 worktree에 없어 해당 단계가 멈춥니다.
  - 어느 쪽이든 4′의 "diff가 바꿔도 되는 줄뿐인지"(:114)에서 걸려 멈추고, 새 사용자 결정이 필요해집니다.
- **권장 조치(control-expert, 봉인 전)**: :73-79에 worktree 실행용 변경 줄을 열거합니다.
  - 경로 1: cwd는 메인 checkout을 그대로 둡니다(입력 상대 경로 문자열이 원 출력과 같게 남음). `$Judge`·`$Co`·`$PyDev` 도구 경로만 worktree 절대 경로로 바꿉니다(`.py` 원소는 I로 빠짐). head-check와, `ROOT` 기본값에 기대는 하위 명령에는 `--root`를 줍니다. head-check에는 worktree, R2 결과 쪽에는 메인 checkout입니다. 이 인자가 출력에 남는지와 N으로 같아지는지를 4′에서 확인합니다.
  - 경로 2: `Set-Location`과 git 관문은 worktree로, `$P2`·`$V5c`는 worktree로 옮기고, 입력 `$Rk`·`$X` 등은 메인 checkout `$Repo`를 그대로 둡니다.
  - 4′ 3번 실행(다른 checkout)에 이 실행본 꼴을 그대로 쓰게 하면 미리 걸러집니다.

### 실행 전 수정
- **[R] W-f "루트 접두"(:189, :202)라는 표현이 실제 꼴과 맞지 않음**
  - N 문자열의 루트 위치를 세면 앞머리 237, 중간 12, 루트 없는 원소 3입니다(`[]` 경로에 같이 묶인 원소).
  - 중간 12건(명령 문자열 등)을 접두만 바꾸면, 원 출력은 메인 루트이고 새 출력은 worktree 루트라 불일치가 남습니다.
  - 정규화 자체는 규범 스크립트에 구현이 없고(N 표시만), 6단계 비교기가 문장대로 구현합니다.
  - 권장: "문자열 안의 모든 출현을, 대소문자 무시·두 구분자 꼴로, 긴 루트 먼저 바꾼다"로 고칩니다.
- **[I] W-g N이 두 루트를 같은 토큰으로 만들고, 입력 경로·sha 블록은 S로 빠짐(:198)**
  - 그래서 T26이 입력을 메인이 아니라 worktree의 추적 사본에서 읽어도 드러나지 않습니다(:66 "입력은 메인 checkout에서 읽는다"를 검증할 수 없음).
  - 실측으로는 `932f1fb..master`에서 추적 입력 폴더(`resume_k1`, `v5_rerun/las_k1`, `v5/las`, `c4g2_only/grid`, `p3_hash.jsonl`)의 diff가 0이라 내용은 같습니다.
  - 권장: rerun 비교(같은 입력)에서는 입력 sha 잎을 빼지 말고 비교합니다. 값이 같아야 하므로 비용이 없고 더 엄격합니다.
- **[R] W-h** `excl_fields_r2.py`의 docstring(:1-54)이 r1 문장 그대로입니다. Usage에 `excl_fields_r1.py`가 적혀 있고, 인자 원소 규칙에 커밋과 N이 없습니다. 규범 스크립트이니 봉인 전에 맞추기를 권합니다. 동작은 코드가 정합니다.

### 기록
- `excl_check.py`(d00f2c54)의 c16 경로를 고친 것을 확인했습니다. 이번 결론은 제 독립 스크립트 기준입니다.
- 4′ 도구 sha 점검은 원 출력만 대상입니다. 새 출력에 생기는 새 필드는 :190 "원 출력에 없는 경로 = 불일치"가 맡습니다.
- 경로 1 출력 8개에는 `rules_seal`이 없고, 6개는 파일 꼴입니다. (h)가 이를 반영했습니다.

## A형 수정 6 (TA 부분)
- 닫힌 것
  - `--allowed-src-changes`(P-4 (ii), 3.1:105·:107)
  - J-2 제외 열거: `v5_options` 모든 출력, head-check, 인자 쌍(:96-99)
  - TA 커밋당 1회와 공개(:89)
  - J-2 출력을 rev26 낱말로 쓰지 않음
  - 결정론과 고를 여지: J-2 통과 여부는 A형 결과와 무관하고, 고정된 436.8 입력을 다시 재는 확인이라 고를 여지는 없습니다.
  - J-2에서 TA가 바꾸는 판정 도구 sha(`diff_vs_existing`, `imports`, `script/tool_sha256`)와 `--expect-head`는 rev26 r2 규칙이 이미 뺍니다.
- **[차단(A형 봉인 전)] A-2 J-2가 실행본 꼴 때문에 아직 돌 수 없음**
  - N-3b와 같은 cwd·도구 루트 문제가 J-2 실행본에도 있습니다.
  - 경로 2 실행본 자체의 관문 `Test-CheckoutState`(:190-192)는 `b9f5707..<HEAD> -- 03_src 02_params`가 비어 있어야 통과하는 PowerShell 확인입니다. 도구의 `--allowed-src-changes`가 닿지 않으므로, TA는 03_src를 바꾸는 이상 여기서 멈춥니다.
  - `$AllowListPath2` 표도 TA blob으로 바꿔야 합니다.
  - 권장: J-2 실행본을 "T26 5단계 실행본 + 다음 변경"으로 열거하고 sha를 `ta_identity.json`에 고정합니다.
    - 기대 HEAD: TA
    - 경로 2 관문: 03_src 확인을 3.1 2항 목록과의 같음으로 바꿈
    - blob 표: TA 값
    - 두 경로 도구에 `--allowed-src-changes` 추가

## 위임 필요
- control-expert: N-3b(:73-79 변경 줄 열거), W-f·W-g·W-h, A형 A-2.

## 검사하지 못한 것
- T26·TA 코드와 실행본 수정본이 아직 없어, N-3b의 권장 꼴이 출력 문자열을 원 출력과 같게 남기는지는 4′에서 실측해야 합니다.
- `abs_roots.py`는 sha만 확인하고 내용은 보지 않았습니다.

## 실행한 검증
- **인터프리터**: python-dev `-I -B -X utf8`(`MKL_THREADING_LAYER=TBB`, `PYTHONDONTWRITEBYTECODE=1`)
- **부록 B r2 재생성**: rev26:214 명령으로 sha f450784b가 같았습니다.
- **즉석 스크립트**(scratchpad `verif-rev26c\`)
  - `c1.py`: 4′ 도구 sha 점검 재현, 절대 경로 N 덮음, 봉인 블록 꼴
  - `c2.py`: N 문자열 안 루트 위치
- **조회**
  - Read·Grep: `run_judgement_path{1,2}_M4.ps1`, `resume4368_judge.py`:181·:5127-5247, `judge4368_common.py`:39·:720·:747·:811, `h6_judge_4368.py`:254-294, `r79_L3L4_final.py`:275-287
  - `git diff --name-only 932f1fb..master -- <추적 입력 폴더>`(0건)
- **메모리**: `audit_pitfalls.md` 제외 목록 항목에 셋째 판 함정(worktree 결정과 실행본 cwd·도구 루트, 루트 "접두" 표현)을 덧붙였습니다.
- **지운 파일**: scratchpad `verif-rev26c\` 전부. 프로젝트 쓰기 0.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha v5_resume_4368_rules_rev26.md 9ed66348…, v5paper_imua_rules_draft.md f2b68f69…, abs_roots.py c3bcd25f…, excl_check.py d00f2c54…, excl_fields_r1.py 3da897c3…, excl_fields_r2.py bda5e7da…, excl_fields.py 37c57662…, rev26_d_excluded_fields.json 6051f77f…, rev26_excluded_fields_r1.json 8074503d…, rev26_excluded_fields_r2.json f450784b…, anchor_map.json 7336a5bd…, appendix_a.json 0b6ad25a…, d1_judge.json 7559c750…, dg3_hash.json 73584733…, family_f_trigger.json 925a0eb9…, family_f.json 4ed034b5…, family_table.json 01dfa819…, grid_h10.json 5d35ae3c…, grid_v0_sample.json 62d9e339…, h11.json c19e49d2…, h12_t4h_replay.json 1e14a694…, h12.json 51cfd778…, h2_select.json 23ef679c…, h6_judge.json f8352c5d…, h6_L1_reference.json a591c3a8…, h6_r79_judge.json d95627ac…, h8_noise_judge.json 6cc77f3f…, head_check.json 3a6d6f7f…, import_check.json 3bf4b824…, ind_las.json 00de905b…, item_list.json 9e9c0d4d…, jp_reuse.json f895c431…, k1_class.json 084b2ab0…, key_map.json 19dcae15…, keyset_grid_r67_main.json eff326d5…, keyset_grid_r67_top.json 79f9b8cc…, keyset_grid_r69_bottom.json ba8ec1f7…, keyset_grid_r69_top.json b881b6a2…, keyset_h6.json 834753e0…, keyset_h7.json bd799bfa…, keyset_h8_noise_V0.json cdc71f2f…, keyset_h8_noise_VB.json c93ee88f…, keyset_h8_seedext_V0.json 61a492ff…, keyset_h8_seedext_VB.json 7790591a…, log_errors_run_harness.json a691ca27…, overlap_steps.json c8dfe4b0…, r4_inputs.json 729022c3…, r4_lists.json f1a3cf5d…, reagg_items.json 257e6e35…, record_check.json 70b98750…, sidecars.json 476ae5b7…, stroke_H-1.json f53a327e…, stroke_H-10.json 0d189282…, stroke_H-3.json 662bcbb0…, stroke_H-4.json 5a8b3a69…, stroke_H-5.json d1453d0d…, stroke_H-6.json 6f4922ab…, stroke_H-7.json bb5c781e…, stroke_H-8.json 9698cff2…, u3_judge_k1.json 4ac5b939…, u3_judge.json 8794234b…, u9_judge.json d52e203e…, x16_records.json 18caaadc…, head_check.json 3a6d6f7f…, r4_inputs.json 729022c3…, stage1_judge.json a6fd45ec…, stroke_H-9.json ce6d4f86…, anchors.json a1ec53ce…, c16.json 3c000cb9…, d1.json 581b15ae…, g3.json 58bafd59…, harness.json 62910051…, jp.json 5d43e366…, manifest.json fa0b72bf…, p2v5c_grid.json e6c47d76…, p2v5c_merge.json 3d981bc4…, p2v5c_noise.json 8c06ebdb…, p2v5c_stage1.json 75f8e3ca…, rd13_items.json c800cc9e…, seal.json 5921db8e…, u3.json e2944ad3…, v5j_u9.json 2f1b60c6…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
