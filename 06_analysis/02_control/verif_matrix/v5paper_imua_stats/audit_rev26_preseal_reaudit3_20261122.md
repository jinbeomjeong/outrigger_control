# verif-protocol-auditor: rev26 봉인 전 수정 4 네 번째 재감사 (2026-11-22)

(hand-back 원문 그대로)

## 감사 요약 (rev26 봉인 전 수정 4, 네 번째 재감사, [시점] 실행 전)
- 대상: `v5_resume_4368_rules_rev26.md`(87908309). 머리줄에 "봉인 전 수정 4"가 있는 것을 확인했습니다.
  - 부록 `excl_fields_r3.py`(bfe6354e), `rev26_excluded_fields_r3.json`(3a5d637c, LF). :227 명령으로 다시 만들면 sha가 같고, 수도 d 1,020(I 105 / S 647 / F 172 / NM 88 / NT 8), c 13으로 :224와 같습니다.
  - A형 `v5paper_imua_rules_draft.md`(85f437e3, 수정 7)
- 본 결과: 스크립트로 `judge_932f1fb` 출력 72개와 `judge_b9f5707/harness_path1`의 r79 하위 출력 파일을 읽었습니다.
  - 출력한 것은 키 경로·범주·개수, 루트 뒤 첫 두 경로 단계, 64자리 16진 값과 `git show 932f1fb:<도구>` sha의 일치 여부(맞은 파일 이름만), 두 실행 사이 파일 sha가 같은지(참·거짓)뿐입니다.
  - H-3·H-4 값과 판정서는 열지 않았습니다.
- **판정: 차단 1 / 실행 전 수정 3 / 기록 4. 아직 봉인 불가.**
  - 차단은 `.gitattributes` 한 줄 문제 하나입니다(T26 허용 변경 목록). 고치면 봉인 가능으로 봅니다.
  - A형(수정 7)은 같은 원인을 물려받는 것 말고는 차단이 없습니다.

## 닫힌 것
- **N-3b**: :72-88이 경로별로 바꿀 줄을 행 번호와 함께 열거합니다.
  - 경로 1: cwd는 메인, `$Judge`·`$Co`는 worktree, 입력은 상대 경로 그대로.
  - 경로 2: `Set-Location`·`$P2`·`$V5c`는 worktree, `$Repo`·입력은 메인.
  - 두 실행본을 읽어 대조했습니다. 경로 1에서 도구를 부르는 곳은 `$Judge`·`$Co`·`$FirstSidecars`·`log_errors.py`(외부 도구)뿐입니다. 경로 2에서 `$Repo` 없이 cwd 기준으로 쓰는 경로는 git 경로(`$BaseGit`)뿐입니다.
- **A-2**: 3.2가 J-2 실행본을 "T26 실행본 + 6개 변경"으로 열거하고, `Test-CheckoutState`의 03_src 확인을 목록과 같은지 보는 것으로 바꿨습니다(:109·:116).
- **W-f**: 루트의 모든 출현을 대소문자 무시·두 구분자 꼴·긴 것 먼저 바꿉니다(:203, docstring :49).
- **W-g**: 입력 경로·sha 블록을 비교 대상으로 돌렸습니다(docstring :38, S 672→647).
  - 이 블록에 이번 실행이 만든 r79 하위 출력의 sha(`inputs.judge.sha256` 등)가 들어 있습니다.
  - 그래서 결정론을 따로 확인했습니다. `h8_r79_judge/*` 6개 파일과 `h6_r79_judge.json`의 sha가 `judge_932f1fb`(M4) 실행과 `judge_b9f5707` 실행 사이에서 모두 같았습니다. 비교에 남겨도 됩니다.
- **W-h**: docstring과 Usage가 r3 규칙과 맞습니다.
- **(c) NT 목록에 입력 경로가 섞이지 않음**
  - NT 8건은 모두 도구 위치입니다: `p2v5c_*` 4파일의 `imports.p2_dir`, `p2v5c_grid`·`noise`·`stage1`·`v5j_u9`의 `v5_options.path`.
  - 한 문자열 안에 도구 위치와 다른 위치가 같이 든 경우는 0건입니다. `root_kind`는 출현 하나라도 도구면 NT로 판정하는데(:151-152), 실측상 이 경우가 없습니다.
  - NM 88건 문자열의 루트 뒤 첫 단계: `06_analysis/02_control` 163, `06_analysis/03_hydraulic` 75, `07_results/S9` 10, 루트 없는 원소 10. 모두 입력 쪽 폴더이고, 루트 자체만 적힌 문자열은 없습니다.
  - NM에 worktree 루트가 남으면 불일치(:203)이므로, 입력을 worktree에서 읽으면 드러납니다.
- **(d) 인자 순서열 비교**: I 원소(출력 토큰, 커밋, `.py`·`.ps1`, `--root`·`--allowed-src-changes`와 그 다음 원소)를 양쪽에서 지운 뒤 순서를 포함해 비교합니다. 순서가 바뀌거나, 비-I 원소가 더해지거나 빠지거나 바뀌면 모두 드러납니다. 숨는 것은 `--root`의 값뿐이고, 아래 기록 1에서 다룹니다.
- **4′ 도구 sha 잎 점검**: r3 기준으로 다시 돌렸고 0건입니다. 입력 sha 블록을 되돌린 뒤에도 0건입니다.

## 발견 사항

### [차단][S·R] B-4 T26의 허용 변경에 `.gitattributes`가 없음 → T26 worktree에서 rev26 봉인 확인이 깨짐
- **근거**
  - :64에서 T26에 규칙 파일(rev26 `.md`·`.sha256`·`rev26_fixed/**`)을 넣습니다. 두 경로 도구는 자기 checkout의 규칙 파일을 원시 바이트로 확인합니다(`judge4368_common.py`:40 `RULES_DIR = ROOT / …`, RD-2 "원시 바이트 sha256(LF)").
  - worktree는 `core.autocrlf=true`입니다(:66). 932f1fb의 `.gitattributes`에는 rev26 줄이 없습니다. 메인의 현 `.gitattributes`에도 아직 없고, 지난 감사에서 attr unspecified를 확인했습니다.
  - :176은 "T26에 들어갈 … `.gitattributes` 줄도 같은 바이트로 넣는다"고 적습니다. 그러나 허용 집합(:60-64)과 RD-1 4 대체 1항 "`932f1fb..T26`가 위 허용 집합 안"(:68)에는 `.gitattributes`가 없습니다.
- **실패 시나리오**
  - `.gitattributes`를 넣으면 1항이 거짓이 되어 4′에서 멈춥니다.
  - 넣지 않으면 worktree에서 rev26 `.md`가 CRLF로 풀려 sha가 봉인값과 달라지고, 두 경로가 S-1(전 묶음 멈춤)이 됩니다.
  - 어느 쪽이든 새 사용자 결정이 필요해집니다.
- **권장 조치**: :60-64 허용 집합에 "`.gitattributes`(7절의 `-text` 줄을 더하는 변경만, 다른 줄 diff 0)"를 더합니다. 4′에서 `git diff 932f1fb..T26 -- .gitattributes`가 그 줄들뿐인지와, worktree의 `git check-attr text`·`ls-files --eol`(rev26 파일 `-text`, `w/lf`)을 확인합니다.
  - RD-1 4 대체의 나머지는 성립합니다. 2항(03_src·02_params 0)과 3항(바뀌지 않은 허용 목록 파일의 blob이 932f1fb와 같음)은 규칙 파일을 더해도 영향이 없고, :64의 "master 봉인 판과 바이트 같음" 확인이 규칙 파일 쪽을 맡습니다.

### 실행 전 수정
- **[I] W-i 경로 1은 worktree가 깨끗한지 보지 않음**
  - 경로 1 `Assert-CleanTree`는 cwd(메인)만 봅니다(실행본 :73-79, rev26:179).
  - head-check는 `git show T26:<파일>` blob과 HEAD만 비교하므로(`resume4368_judge.py`:5084-5092), worktree 작업 파일이 고쳐져 있어도 HEAD = T26이면 그 코드로 판정합니다.
  - 경로 2는 cwd = worktree에서 `git status`를 보므로 잡지만, 두 실행본 사이에 상태가 바뀔 수 있습니다.
  - 권장: 메인이 5단계 앞뒤로 `git -C <WT> status --porcelain`이 빈지 보고 `t26_identity.json`에 기록한다고 2절에 적습니다. 실행본은 고치지 않아도 됩니다. A형 J-2·TA worktree도 같습니다.
- **[R] W-j 경로 1의 ROOT 의존은 지금 코드로 미리 정할 수 있음** → :78의 "(조건부) 4′ 코드 확인으로 정한 목록"을 봉인 전에 확정하기를 권합니다. 932f1fb 코드 기준 예측은 다음과 같습니다.
  - 이미 `--root`를 받는 호출: `r4-inputs`(:90), `jp-reuse`(:120), `r4-lists`(:121), `grid-h10`(:172)
  - `--root` 없이 기본 ROOT(= worktree)를 쓰는 호출: `head-check`(의도대로), `import-check`·`appendix-a`(checkout 파일 = 932f1fb 내용, 출력에 절대 경로 없음), `h11`(`--las-k1-dir` 기본값 = worktree의 추적 사본, 내용 같음, 출력에 절대 경로 없음)
  - 내부 ROOT 사용: `02_params/rexome33.yaml`, `04_scripts/02_chrono`, `coupled` 모듈(`resume4368_judge.py`:182·:1652·:3197·:4618·:4638). 도구 쪽이라 worktree가 맞습니다.
  - → 더할 `--root .`는 없다고 예측합니다. 그 근거를 :78에 적고, 4′는 확인만 하도록 바꿉니다.
  - 주의: `judge4368_common.repo_relative(path)`(:691-698)는 기본 base가 ROOT(worktree)입니다. 메인 cwd 기준 상대 입력은 `relative_to`에 실패해 `Path(path).as_posix()`로 떨어집니다(`h6_judge`:215, `judge_stage1`:642·:687, `u3_judge`:386의 `result_file`). 입력을 `/` 구분 상대 경로로 주는 지금 실행본 꼴에서만 원 출력과 같은 문자열이 됩니다. 4′ 항목에 "경로 1 실행본의 입력 인자는 모두 cwd 상대 + `/` 꼴(절대 경로·`\`·`./` 없음)"을 더하기를 권합니다.
- **[R] W-k A형 3.2-5가 경로 2 도구에도 `--allowed-src-changes`를 줍니다.** P-4 (ii)가 경로 2 도구의 인자 파서에도 이 인자를 넣는다고 명시해야 합니다. 지금 문장은 "head-check 허용 인자"뿐입니다.

### 기록
1. 인자 쌍 제외 때문에 `--root`의 값(`.` 또는 worktree)은 출력 비교로 드러나지 않습니다. 대신 4′ 실행본 diff 점검과, NM에 worktree 루트가 남으면 불일치로 보는 규칙이 이를 맡습니다. 경로 1 출력에는 argv가 거의 남지 않습니다(`h6`·`h8`의 `judge_run(s).command`뿐).
2. (d) 범위는 `harness_path{1,2}/*.json` 최상위뿐입니다. 하위 폴더(`items/`, `h8_r79_judge/`, `logs/`)는 기록된 sha(`item_list :: sha256`, `inputs.*.sha256`)로만 간접 비교됩니다. 위 결정론 실측으로 충분해 보입니다.
3. (g)의 `v5_options.sha256`은 CRLF 작업 트리 바이트 sha라 worktree의 `core.autocrlf=true`(:66)를 전제합니다. 4′에서 worktree 설정을 기록하는 항목(:89)이 이를 맡습니다.
4. A형 J-2: 고를 여지와 결정론 판단은 지난번과 같습니다. 제외 열거(`v5_options` 전체, head-check, 인자 쌍)와 r3의 S 범주로 TA 정체성 필드가 덮입니다. 비교에 남는 03_src 쪽 sha는 `v5_options`(제외됨)와 `h6_L1_reference :: meta.c2_py_sha256`인데, 후자는 저장 입력 메타를 옮긴 값이라(`h6_judge_4368.py`:257, `r79_L3L4_final.py`:285-286) TA에 영향받지 않습니다.

## 위임 필요
- control-expert: B-4(허용 집합에 `.gitattributes`), W-i, W-j, W-k(A형 P-4).

## 검사하지 못한 것
- T26·TA와 실제 실행본 수정본이 아직 없습니다. W-j 예측과 NT·NM 분류가 새 출력에서도 맞는지는 4′ 세 번 실행에서 실측해야 합니다.
- 경로 2 출력은 다른 실행과 비교할 같은 이름 파일이 없어 결정론을 실측하지 못했습니다.

## 실행한 검증
- **인터프리터**: python-dev `-I -B -X utf8`(`MKL_THREADING_LAYER=TBB`, `PYTHONDONTWRITEBYTECODE=1`)
- **부록 B r3 재생성**: sha 3a5d637c가 같았습니다.
- **즉석 스크립트**(scratchpad `verif-rev26d\`)
  - `d1.py`: 범주 수, NT 목록, 도구·비도구가 섞인 문자열
  - `d2.py`: NM 문자열의 루트 뒤 첫 두 단계, r3 기준 4′ 도구 sha 점검
  - PowerShell: r79 하위 출력의 두 실행 간 파일 sha 비교
- **Read·Grep**: rev26 :55-234, `excl_fields_r3.py` 전체, 두 M4 실행본(경로 1 호출과 `--root` 목록, 경로 2 상대 경로), `resume4368_judge.py`의 ROOT 사용(:181-5247), `judge4368_common.py`:38-40·:691-698·:747-811, 판정기별 `repo_relative` 호출, A형 :88-123
- **메모리**: `audit_pitfalls.md`에 넷째 판 함정을 덧붙였습니다(옛 기준 커밋 가지에 봉인 파일을 넣을 때 `.gitattributes`, worktree가 깨끗한지 보지 않는 HEAD·blob 확인, ROOT 기준 `repo_relative`의 대체 동작).
- **지운 파일**: scratchpad `verif-rev26d\` 전부. 프로젝트 쓰기 0.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha v5_resume_4368_rules_rev26.md 87908309…, v5paper_imua_rules_draft.md 85f437e3…, abs_roots.py c3bcd25f…, excl_check.py d00f2c54…, excl_fields_r1.py 3da897c3…, excl_fields_r2.py bda5e7da…, excl_fields_r3.py bfe6354e…, excl_fields.py 37c57662…, rev26_d_excluded_fields.json 6051f77f…, rev26_excluded_fields_r1.json 8074503d…, rev26_excluded_fields_r2.json f450784b…, rev26_excluded_fields_r3.json 3a5d637c…, anchor_map.json 7336a5bd…, appendix_a.json 0b6ad25a…, d1_judge.json 7559c750…, dg3_hash.json 73584733…, family_f_trigger.json 925a0eb9…, family_f.json 4ed034b5…, family_table.json 01dfa819…, grid_h10.json 5d35ae3c…, grid_v0_sample.json 62d9e339…, h11.json c19e49d2…, h12_t4h_replay.json 1e14a694…, h12.json 51cfd778…, h2_select.json 23ef679c…, h6_judge.json f8352c5d…, h6_L1_reference.json a591c3a8…, h6_r79_judge.json d95627ac…, h8_noise_judge.json 6cc77f3f…, head_check.json 3a6d6f7f…, import_check.json 3bf4b824…, ind_las.json 00de905b…, item_list.json 9e9c0d4d…, jp_reuse.json f895c431…, k1_class.json 084b2ab0…, key_map.json 19dcae15…, keyset_grid_r67_main.json eff326d5…, keyset_grid_r67_top.json 79f9b8cc…, keyset_grid_r69_bottom.json ba8ec1f7…, keyset_grid_r69_top.json b881b6a2…, keyset_h6.json 834753e0…, keyset_h7.json bd799bfa…, keyset_h8_noise_V0.json cdc71f2f…, keyset_h8_noise_VB.json c93ee88f…, keyset_h8_seedext_V0.json 61a492ff…, keyset_h8_seedext_VB.json 7790591a…, log_errors_run_harness.json a691ca27…, overlap_steps.json c8dfe4b0…, r4_inputs.json 729022c3…, r4_lists.json f1a3cf5d…, reagg_items.json 257e6e35…, record_check.json 70b98750…, sidecars.json 476ae5b7…, stroke_H-1.json f53a327e…, stroke_H-10.json 0d189282…, stroke_H-3.json 662bcbb0…, stroke_H-4.json 5a8b3a69…, stroke_H-5.json d1453d0d…, stroke_H-6.json 6f4922ab…, stroke_H-7.json bb5c781e…, stroke_H-8.json 9698cff2…, u3_judge_k1.json 4ac5b939…, u3_judge.json 8794234b…, u9_judge.json d52e203e…, x16_records.json 18caaadc…, head_check.json 3a6d6f7f…, r4_inputs.json 729022c3…, stage1_judge.json a6fd45ec…, stroke_H-9.json ce6d4f86…, anchors.json a1ec53ce…, c16.json 3c000cb9…, d1.json 581b15ae…, g3.json 58bafd59…, harness.json 62910051…, jp.json 5d43e366…, manifest.json fa0b72bf…, p2v5c_grid.json e6c47d76…, p2v5c_merge.json 3d981bc4…, p2v5c_noise.json 8c06ebdb…, p2v5c_stage1.json 75f8e3ca…, rd13_items.json c800cc9e…, seal.json 5921db8e…, u3.json e2944ad3…, v5j_u9.json 2f1b60c6…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
