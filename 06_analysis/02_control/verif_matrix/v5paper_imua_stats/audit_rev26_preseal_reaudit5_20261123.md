# verif-protocol-auditor: rev26 봉인 전 수정 6 여섯 번째 재감사 (2026-11-23)

(hand-back 원문 그대로)

## 감사 요약 (rev26 봉인 전 수정 6, 여섯 번째 재감사, [시점] 실행 전)
- 대상: `v5_resume_4368_rules_rev26.md`(0e39d5b9, 머리 "봉인 전 수정 6"을 확인했습니다).
  - 부록 `excl_fields_r4.py`(1fb6f701), `rev26_excluded_fields_r4.json`(fafca423). 다시 만들면 sha가 같고, r3 목록과는 `rules` 이름만 다릅니다(나머지 같음). r3→r4 스크립트 변경은 7줄 추가·6줄 삭제입니다.
  - A형 `v5paper_imua_rules_draft.md`(27895485). 근거 폴더 `v5paper_imua_stats/input_base_20261123/`.
- 본 결과: 932f1fb 코드와 원 출력의 키 구조, 절대 경로 문자열에서 루트 뒤 경로 접두만 봤습니다. 판정값은 보지 않았습니다.
- **판정: 차단 1 / 실행 전 수정 1 / 기록 4 → 아직 봉인 불가.**
  - 차단은 원 출력의 잎 하나(`h2_select.json :: rules`) 때문입니다.
  - B-5의 D/W 분류 자체는 제가 932f1fb 코드에서 따로 대조한 결과와 맞습니다.

## 닫힌 것
- **B-5, 경로 2 D/W**: 경로 2 비시험 파일 9개(`p2_4368`·`p2_x16`·`p2_u3`·`p2_v5j`·`p2_d1`·`p2v5c_common`·`p2v5c_grid`·`p2v5c_noise`·`p2v5c_stage1`)의 932f1fb 판을 함수 단위로 직접 훑어, `repo` 사용처를 모두 :75-76 표와 대조했습니다.
  - D로 맞음: `rel_posix`, `key_source_index`, `_rel_entry_path`, `r4_input_check`, `cmd_harness`, `cmd_anchors`, `jp_result_json`/`cmd_jp`, Chrono 계열(`resolve_result`, `resolve_runner_row`, `runner_root`, `chrono_row`, `cmd_chrono`), `p2_x16.cmd_g3`·`cmd_c16`, `p2_u3`의 `study_keys`·`settle_v2_recount`·`recount_u3`의 `rel_posix`, `p2v5c`의 `rel_file`·`dg3_keys`
  - W로 맞음: `check_seals`, `check_chrono_seals`, `check_rev3`, `_check_one`, `git_head`, `head_check`, `git_commits_since`, `git_diff_stat`, `load_is_extend_start`, `run_judge`, `cmd_noise`의 `jtool`, `yaml_vmax`, `cmd_openloop`, 각 `main`의 봉인·규칙 sha
  - 빠진 곳은 없습니다. `p2_d1`·`p2_v5j`는 `main`의 W뿐이라 "D 없음"이 맞습니다.
  - `--data-root` 위치: 실행본에서 `--out`은 네 도구 모두 최상위 인자이고(`p2v5c_common.add_common_args`:660-662), 9개 호출에서 `--out` 쌍 바로 뒤가 최상위 위치입니다(실행본 :327-392).
- **출력 상대 경로 문자열이 원 출력과 같은가(논리)**: M4 때는 `repo`가 메인 checkout이었습니다. D를 `--data-root $Repo`로 옮기면 `rel_posix(path, data_root)`·`data_root / rel`이 M4와 같은 기준이 되고, 입력 인자 문자열도 그대로입니다. 그래서 같은 문자열이 나옵니다.
- **경로 1**: 932f1fb 판 12개 파일을 훑었습니다. 결과 입력을 도구 ROOT 기준으로 푸는 기본값은 `h11 --las-k1-dir`(`resume4368_judge.py`:5224)과 `resume_k1_family.py --data-root`(:367)뿐입니다.
  - `u3_judge_k1`의 `DEFAULT_V4_DIR`는 실행본이 `--v4-dir`로 덮습니다.
  - `d1_select.DEFAULT_RULES`는 W(규칙 파일)입니다. 단, 출력에 남습니다 → 아래 B-6.
  - 2절 경로 1 5·6번이 맞습니다.
- **W-l**: 4′ 줄바꿈 점검 대상이 파일 4개로 정해졌고, 폐기본은 attr만 봅니다(:144).
- **W-m**: h11 문장을 고쳤습니다(:79·:95·:147).
- **기록 1**: `.gitattributes` 들여쓰기를 고쳤습니다(:67).
- **4′ 문장이 확인 가능한가**
  - "`ls-tree` 수 > 0 뒤 diff"(:151): 확인 가능합니다.
  - "W에 열거한 것뿐"(:148): 코드 대조로 확인할 수 있습니다. 구조상으로도 안전합니다. worktree에서 읽는 추적 자료는 932f1fb 내용이라 M4 때 메인이 읽은 것과 같고, 추적되지 않은 자료는 worktree에 없어 소리 없이 틀리는 대신 바로 실패합니다.
  - 근거 `closure_paths.tsv`의 untracked > 0 폴더(`s8/rev79` 3개, `s9` 46개, `verif_matrix` 1,989개 등)도 이 원리로 덮입니다. 표본 확인: `r79_L3L4_final`의 `REV79_DIR` 기본 파일 2개는 932f1fb 추적 파일이고, `r79_sensor_judge`의 `BASELINE_DIR`(`rev76`)는 W 목록에 있습니다.

## 발견 사항

### [차단][R·I] B-6 W 쪽 읽기의 절대 경로가 원 출력 비교 잎에 남는 곳이 하나 있음 → NM 규칙으로 (d) 불일치
- **근거**
  - 원 출력 NM 문자열의 루트 뒤 경로를 W 접두와 대조한 결과, W 자료를 가리키는 것은 2건입니다.
    - `harness_path1/h2_select.json :: rules`: `verif_matrix/d1_selection_rules…`, 932f1fb 추적 파일
    - `harness_path2/jp.json :: argv/#4`: `v5/las/shadow_jp_b0.jsonl`. 실행본이 메인 절대 경로(`$V5`)로 주므로 문제없습니다.
  - `h2_select.json`은 `d1_select.py`가 씁니다. `rules`는 `DEFAULT_RULES = ROOT / … / d1_selection_rules.md`(932f1fb `d1_select.py`:35·:39)이고, `$Co`가 worktree라 ROOT도 worktree가 됩니다.
  - 그러면 새 출력에서는 worktree 절대 경로가 됩니다. 이 경로는 NT 접두(`03_src`·`04_scripts`·…·`path2*`·`paper_runs/scripts`)에 없어 NM으로 분류되고, 부록 A(:203·:158, r4 docstring)는 "NM에 worktree 루트가 남으면 불일치"입니다.
- **실패 시나리오**: 5단계 (d)에서 `h2_select.json`이 반드시 불일치하여 "판정 불가(rev26 기대 효과 불일치)"가 됩니다. 4′ 3번 실행(다른 worktree)에서 먼저 드러나면 멈추고 새 사용자 결정이 필요합니다.
- **권장 조치(봉인 전)**: NT 정의를 "도구 위치 + 2절 W 자료 위치"로 넓힙니다. 최소한 `06_analysis/02_control/verif_matrix/` 아래 규칙 파일(`*.md`·`*.sha256`), `02_params/`, :80의 W 자료 목록을 넣고, 부록 r5와 sha를 갱신합니다. 이 경우 다른 NM 판정은 바뀌지 않습니다. 원 출력 NM 88건 가운데 W 접두에 걸리는 것은 위 2건뿐이고, 그중 `jp` 원소는 메인 경로라 NT로 옮겨도 결과가 같습니다. 대신 `rules` 키 하나를 빼는 방식도 가능하지만, 규칙 위치를 비교에서 잃게 됩니다.

### 실행 전 수정
- **W-n [R] :81·:152와 A형 1a의 전제가 틀렸습니다.** 이 문장들은 `h6_L1_reference.json :: meta.c2_py_sha256`이 worktree의 `c2.py` 줄바꿈이나 TA의 `c2.py` 변경에 따라 바뀐다고 봅니다.
  - 실제로 이 값은 저장 입력(`h8_noise_VB.json`)의 `meta`를 옮긴 것입니다. 932f1fb `h8_noise_judge_4368.py`:444-450 `reference_extract`가 `{**(noise.get("meta") or {}), …}`로 옮기고, `h6_judge_4368.py`가 이 함수로 만듭니다.
  - 그래서 :152의 `c2.py` 줄바꿈 점검은 통과는 하지만 근거가 틀렸습니다. A형 1a 제외는 영향이 없으면서 J-2 비교 잎을 하나 줄입니다.
  - 권장: :81을 "줄바꿈이 비교 잎에 닿는 03_src 파일은 `v5_options.py`뿐(`c2_py_sha256`은 저장 입력 메타)"으로 고치고, :152와 A형 1a에서 `c2.py`를 뺍니다. 빼지 않고 두는 것도 위험하지는 않습니다.

### 기록
1. :75 D 표의 "`cmd_chrono` 매니페스트 기본값"과 :80 W 목록의 `chrono_rows_manifest.json`이 겹칩니다. 5단계에서 돌지 않는 경로라 영향은 없습니다. 한쪽으로 정리하기를 권합니다.
2. 경로 2 `run_judge`(`p2v5c_noise`)는 worktree의 `r79_sensor_judge.py`를 메인 입력으로 돌립니다. 그 출력의 sha(`out_sha256`)가 비교에 남지만, 앞선 감사에서 r79 판정 출력이 다른 커밋 실행 사이에서도 바이트가 같은 것을 확인했습니다.
3. A형 P-4 (iv)와 3.2 "그대로 두는 것"(:123)이 rev26 입력 기준 인자를 그대로 물려받는 것을 확인했습니다. J-2 비교 쪽 인자 쌍 제외(:127)도 r4 `PAIR_FLAGS`와 맞습니다.
4. 원 출력의 비교 대상 잎 가운데 03_src 파일 sha와 같은 64자리 값은 지난 감사 실측으로 `v5_options.sha256`과 `c2_py_sha256`뿐입니다. 근거 `src_sha_leaves.json`과도 맞습니다.

## 위임 필요
- control-expert: B-6(NT 범위를 W 위치로 넓히고 부록 r5), W-n, 기록 1.

## 실행한 검증
- **인터프리터**: python-dev `-I -B -X utf8`
- **source_guard**: snapshot을 먼저 돌리고, 끝에 verify를 돌렸습니다.
- **부록 r4 재생성**: sha fafca423이 같았습니다. r3와 r4 목록은 `rules` 말고 같습니다.
- **즉석 스크립트**(scratchpad `verif-rev26e\`)
  - `e1.py`: `git show 932f1fb:<파일>`을 ast로 읽어 함수별 `repo`·`ROOT`·`HERE` 사용처를 뽑았습니다(경로 2 9개, 경로 1 12개 파일).
  - `e2.py`: 원 출력 NM 문자열이 W 접두를 가리키는지 대조했습니다.
- **git**: `diff --name-only 932f1fb..master -- <도구 폴더>`(경로 1 coupled 파일 일부가 master에서 바뀐 것을 확인했고, 그래서 932f1fb 판으로 읽었습니다), `ls-tree`(`rev79` 기본 파일).
- **Bash 사용**: 932f1fb 판 `resume_k1_family.py`·`r72_g6_screen.py`·`r79_*`·`h8_noise_judge_4368.py`를 볼 때 `git show … | sed/grep` 파이프를 썼습니다. 공통 실행 규칙(Bash 파이프 금지) 위반이고, 프로세스는 정상 종료됐습니다.
- **Read**: rev26 :60-160, A형 :91·:97-104·:123·:127, 근거 `base_sites_p1.tsv`·`closure_sites.tsv`·`closure_paths.tsv`, 경로 2 실행본 :324-395
- **메모리**: `audit_pitfalls.md`에 "W 쪽 읽기의 절대 경로가 출력에 남는 경우"와 "옮겨 온 입력 메타 sha를 checkout에 따라 바뀌는 값으로 오인하는 경우"를 덧붙였습니다.
- **지운 파일**: scratchpad `verif-rev26e\` 전부. 프로젝트 쓰기 0.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha v5_resume_4368_rules_rev26.md 0e39d5b9…, v5paper_imua_rules_draft.md 27895485…, abs_roots.py c3bcd25f…, excl_check.py d00f2c54…, excl_fields_r1.py 3da897c3…, excl_fields_r2.py bda5e7da…, excl_fields_r3.py bfe6354e…, excl_fields_r4.py 1fb6f701…, excl_fields.py 37c57662…, rev26_d_excluded_fields.json 6051f77f…, rev26_excluded_fields_r1.json 8074503d…, rev26_excluded_fields_r2.json f450784b…, rev26_excluded_fields_r3.json 3a5d637c…, rev26_excluded_fields_r4.json fafca423…, apply_r6_r9.py aed8f1c4…, appx_a_check.py ca16ff57…, appx_a_check.tsv bb4a39e5…, base_sites_p1.tsv 6dff2cdd…, base_sites_p2.tsv b632307a…, base_sites.py 66b40f60…, closure_paths.py 0af45c6e…, closure_paths.tsv bf53bb78…, closure_sites.py e0ac1c64…, closure_sites.tsv ecb9428e…, eol_risk.json 3307da1f…, eol_risk.py 4457a835…, src_sha_leaves.json 6ade2c84…, src_sha_leaves.py eba671e6…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
