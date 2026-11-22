# verif-protocol-auditor: rev26 봉인 전 수정 2 재감사 (2026-11-22)

(hand-back 원문 그대로)

## 감사 요약 (rev26 봉인 전 수정 2 재감사, [시점] 실행 전)
- 본 결과: 스크립트로 `judge_932f1fb/{harness_path1, harness_path1_retry1, harness_path2}`의 JSON 72개를 읽었습니다. 출력한 것은 키 경로, 자식 키 이름, 형 이름, 값 꼴(64자리 16진·커밋·절대 경로·출력 폴더 토큰·ISO 시각), 개수뿐입니다. 64자리 16진 값은 `git show 932f1fb:<도구 파일>`의 sha와 맞는지만 대조하고, 맞은 파일 이름만 적었습니다.
  - 입력 쪽 `v5_rerun/las_k1/u6_*.json`에서 `records[].controller`와 `records[].v5.controller_tag`의 (설정 이름, 태그) 쌍을 셌습니다. 판정 결과값이 아닙니다.
  - H-3·H-4 값과 판정서 4.4·4.5절은 열지 않았습니다.
- 대상
  - rev26: `v5_resume_4368_rules_rev26.md`(cd0aacf5)
  - 부록: `excl_fields_r1.py`(3da897c3), `rev26_excluded_fields_r1.json`(8074503d). 재생성 결과 sha가 같고, d 912경로(68파일, I 94 / S 645 / F 173), c 13경로로 :182와 같습니다.
  - 점검 스크립트 `excl_check.py`(eb0356ee)
  - A형 TA 부분: `v5paper_imua_rules_draft.md`(3804880e)
- **판정: 차단 3 / 실행 전 수정 5 / 기록 4. 봉인 불가.**
  - B-2(지적한 노드 복원)는 해소됐습니다.
  - B-1은 기준 커밋·허용 파일·RD-1 4 대체·HEAD·실패 처리표·`-text` 목록까지 잘 닫혔습니다. 그러나 좁힌 규칙이 도구 판에 따라 바뀌는 필드를 새로 비교 대상에 넣었고, (h) 문구와 5단계 실행본 변경 범위에도 걸림이 남아 아래 차단이 됩니다.
  - A형 J-2는 결과를 보고 고를 여지는 없지만, 문안대로는 돌 수 없습니다(A-1).

## B-2 해소 확인 (지적한 노드가 모두 비교 대상으로 돌아왔는지)
- 비교 대상으로 돌아옴
  - `grid_h10`·`family_f_trigger :: v0_pair_source.source`, `p2v5c_grid :: v0_pair.source`
  - `retry1/r4_inputs :: files`(`files[].stops` 포함), `retry1/stage1_judge :: R4.H-9_grid_R16_7.files`
  - `harness.json :: bundles.H-{1,4,5,6,7,8,9,10}.files`
  - `p2v5c_noise :: reaggregated.seedext.{V0,VB}.detail`, `p2v5c_stage1 :: H-10.LS_conditions.LS1~4.detail`
  - `c16 :: rows.<4행>.items.G6_source`
  - `sidecars :: rows[].{start,end}.{times,seals_ok}`
  - `family_table :: rows[].source`, `overlap_steps :: rows[].output`, `log_errors :: steps[].done_line`, `p2v5c_noise :: TABLE_REAGG[].source`
- 여전히 빠지는 것은 `p2v5c_grid :: v0_pair.sample.detail[].why`(자유 문장 잎)뿐이며, 의도대로입니다.
- 인자 목록은 통째로 빠지는 노드가 0입니다. 원소만 37개 빠집니다(출력 폴더 토큰이 든 원소, `.py` 경로).
- 판정 목록 digest가 비교에 남습니다: `rd13_items :: list_sha256.*`, `p2v5c_merge :: RD-13_sha256.*`.
- 주의: `excl_check.py`:15의 c16 시험 경로 `rows/{*}/…`는 틀렸습니다. c16의 rows는 8키라 `{*}`로 접히지 않으므로, 그 줄은 무엇이든 "compared"로 나옵니다. 위 c16 결론은 실제 행 이름으로 다시 시험한 것입니다.

## 발견 사항

### [차단][E·I] N-1 좁힌 규칙이 도구 판·checkout에 따라 바뀌는 필드를 비교에 넣음 → (d)가 예측 가능하게 불일치, 4′는 일부만 잡음
- **근거**: 비교 대상 잎 가운데 64자리 16진 값을 `932f1fb`의 도구 파일 sha와 대조했습니다. 맞은 것이 아래이며, 모두 부록 B 밖입니다.
  1. **경로 1 `diff_vs_existing[]`**
     - 대상 파일: `d1_judge`·`h8_noise_judge`·`u3_judge`·`u9_judge`·`retry1/stage1_judge`
     - `new_sha256`는 판정 스크립트 자신(`u3_judge_4368.py` 등)의 sha입니다. 이 블록에는 numstat 줄 수도 듭니다(`judge4368_common.py`:747-761, :811).
     - 경로 1 RD-5 키 대응표는 이 블록을 RD-5 범주로 적었습니다: `resume4368_judge.py`:5039 `("definition_changes, diff_vs_existing", …, "도구 판·규칙 설명 문자열")`. 좁힌 규칙 rev26:170에는 이 이름이 없습니다.
     - 1.1 "모드" 행(:32, H-1~H-12 두 경로에 `--tag-mode`)과 R26-2·R26-3 때문에 판정 스크립트가 바뀌므로, 이 값들은 반드시 달라집니다.
  2. **경로 2 `imports.p2_4368_sha256`·`imports.p2_v5j_sha256`·`common_sha256`**
     - 대상 파일: `p2v5c_grid`·`p2v5c_merge`·`p2v5c_noise`·`p2v5c_stage1`
     - `path2/p2_4368.py`·`p2_v5j.py`·`path2_v5c/p2v5c_common.py`의 sha입니다. 2절이 경로 2 `seals` 블록에 rev26을 더하라고 하므로 `p2_4368.py`가 바뀝니다.
  3. **경로 2 `argv`의 `--expect-head <40자리 커밋>` 원소**
     - 대상 파일 9개: `anchors`·`c16`·`g3`·`harness`·`jp`·`p2v5c_grid`·`p2v5c_merge`·`p2v5c_noise`·`p2v5c_stage1`
     - 예: `harness.json` argv 꼴 `['--out', <출력 폴더>, <str>, '--manifest', <출력 폴더>, '--expect-head', <hex40 M4>]`
     - 인자 목록 규칙은 원소 가운데 출력 폴더 토큰과 `.py`·`.ps1`만 뺍니다(`excl_fields_r1.py`:140-146; 인자 목록에서 `continue`하므로 :155의 커밋 값 규칙은 원소에 닿지 않음). rev26:173의 "스칼라 문자열 잎 … 도구 커밋" 문장과도 다릅니다.
     - 5단계에서는 이 원소가 T26 해시가 됩니다.
  4. **checkout 절대 경로**: `imports.p2_dir`(`p2v5c_*` 4파일), `v5_options.path`(`p2v5c_grid`·`noise`·`stage1`·`v5j_u9` 4파일). (g)는 `harness.json`의 `v5_options`만 비교에서 뺍니다.
- **실패 시나리오**
  - 1·2·3 때문에 5단계 (d)는 반드시 불일치하고, rev26 낱말이 "판정 불가(rev26 기대 효과 불일치)"로 굳습니다(:112).
  - 4′ 세 번 실행 가운데 3번(다른 checkout + 빈 커밋)은 3·4를 잡습니다. 그러면 :98에 따라 "5단계로 가지 않고 멈춰 묻는다(규칙 수정은 새 사용자 결정)"가 되어, 봉인 직후 막힙니다.
  - 1·2는 빈 커밋으로는 파일 내용이 그대로라 4′에서도 드러나지 않고, 5단계에서 처음 드러납니다.
- **권장 조치(control-expert, 봉인 전)**
  - S 범주에 `diff_vs_existing`·`definition_changes`(스칼라 잎과 numstat 수), `imports.*_sha256`·`common_sha256`를 더합니다.
  - I 인자 목록 규칙에 "도구 커밋 토큰이 든 원소"를 더합니다.
  - 절대 경로 문제는 둘 중 하나로 정합니다.
    - (가) 5단계는 메인 checkout `C:\workspace\outrigger_control`에서 돈다고 적고, 4′ 3번은 같은 경로에서 빈 커밋만 더해 돌린다.
    - (나) checkout 루트 토큰을 I에 더한다.
  - 4′에 다음 항목을 더하기를 권합니다: "비교 대상 64자리 16진 잎을 `git show <기준>:<허용 목록 파일>` sha와 대조해 맞는 것이 0건". 빈 커밋으로는 내용에 딸린 sha가 드러나지 않기 때문입니다.

### [차단][S·R] N-2 (h)가 실제 출력의 봉인 블록 꼴과 맞지 않고, 중첩 봉인 사본과 (d)가 부딪힘
- **근거**
  - rev26:110 (h) "경로 1의 **모든 출력** `rules_seal.revisions`에 … 세 sha(`expected_sha256`·`seal_file_sha256`·`rules_file_sha256`)". 실제 경로 1 출력 57개(retry1 포함)는 다음과 같습니다.
    - 43개는 `revisions` 26칸에 expected·rules_file·seal_file 키
    - 6개는 `file_sha256`·`pinned_sha256`·`seal_file_sha256` 키(`judge4368_common.py`:720 꼴)
    - 8개는 `rules_seal`이 없음: `family_table`, `h12_t4h_replay`, `h2_select`, `h6_L1_reference`, `h6_r79_judge`, `log_errors_run_harness`, `sidecars`, `u3_judge_k1`
  - `u3_judge.json`의 중첩 블록 `G-3.rules_seal.revisions.<26판>.{expected,seal_file,rules_file}_sha256`과 `G-3.rules_rev*_sha256`·`G-3.rules_rev13_to_rev25_sha256`(13키)는 판정 실행이 계산한 봉인 확인입니다. 최상위가 아니라서 좁힌 S 규칙(:169)에 걸리지 않고 비교 대상입니다.
- **실패 시나리오**
  - (h)를 글자대로 읽으면 14개 출력에서 불일치입니다.
  - 2절대로 rev26을 봉인 목록에 넣으면 `u3_judge :: G-3.rules_seal.revisions.v5_resume_4368_rules_rev26.md`가 새 경로로 생겨 (d) 불일치입니다(:164).
- **권장 조치**
  - (h)를 "`rules_seal.revisions`가 있는 출력에서, 그 출력의 기존 하위 키 꼴로"라고 고칩니다.
  - `u3_judge :: G-3` 봉인 블록을 S로 열거하거나 (h) 대상으로 명시합니다.
  - 덧붙여 `v5j_u9 :: r4_rev13_25_sha256`은 rev26:171이 "판정 목록 digest"로 적었지만, 실제로는 판 이름 → 규칙 sha 지도입니다. 2절에 따라 여기에 rev26을 넣지 않는다고 명시하기를 권합니다.

### [차단][R] N-3 5단계 실행본에서 바꿔도 되는 줄(:92)로는 경로 2 관문을 통과할 수 없음
- **근거**: `run_judgement_path2_M4.ps1`:56-72에 경로 2 허용 목록 15개의 blob sha 표 `$AllowListPath2`가 박혀 있습니다. :201은 `$atM4 -eq $atR4 -and $atR4 -eq $AllowListPath2[$file]`가 아니면 관문 문제로 처리합니다. T26에서 바뀐 경로 2 파일은 표 값과 다르므로 반드시 멈춥니다. rev26:92는 "기대 HEAD·비교 커밋·출력 폴더·인터프리터 경로"만 바꿀 수 있게 합니다.
- **권장 조치**: 바꿔도 되는 줄에 경로 2 blob 표를 더합니다. 표 값은 T26 blob이고, 4′에서 `t26_identity.json`과 대조합니다.

### 실행 전 수정
- **W-a [R]** R26-3의 행 종류 "C2"는 원판 4.1 표의 행 이름이 아닙니다. 4.1에는 V0 / VB·LS / ABL / IND·IND_LAS 행이 있습니다.
  - 입력 실측: `u6_*` 네 파일의 (controller, v5.controller_tag)는 (C2, `final_C4G2_P3_LAS_K1`), (ABL, `ABL_LAS_K1`), (IND, `IND`), (IND_LAS, `IND_LAS`)뿐이고, 모두 같은 쌍입니다.
  - 두 작성자가 C2를 V0 행으로 대면 436.8 데이터에서 모든 C2 줄이 S-2가 되어 (e)가 깨집니다.
  - 권장: C2 → `final_C4G2_P3_LAS_K1`(VB 행, `u3_u6_rerun_rules.md`:16) 대응을 문장으로 적습니다.
- **W-b [R]** 5단계 실행본이 다른 세션의 scratchpad 파일에 기댑니다.
  - 경로 1:46 `$FirstSidecars`, 경로 2:35 `$ManifestSource`. 지금은 있고 sha도 같습니다(0962f639…, fa0b72bf…).
  - 저장소에 같은 sha의 사본이 있습니다: `_fixed/tools/sidecars_b9f5707.py`, `_fixed/manifest/p2_manifest_draft.json`.
  - 권장: 바꿔도 되는 줄에 이 두 경로를 사본으로 돌리는 것을 더합니다. 그러지 않으면 scratchpad가 지워질 때 :120의 "종료 ≠ 0"이 됩니다.
- **W-c [I]** 바꿔도 되는 항목에 "인터프리터 경로"가 있습니다. 그러나 경로 1 `judge_run.command`·경로 2 `judge_runs.*.cmd`의 인터프리터 원소는 비교 대상입니다. 바꾸면 (d)가 불일치하므로 "바꾸지 않는다"로 고치거나 I에 더합니다.
- **W-d [I]** 외부 도구와 환경을 `t26_identity.json`에 고정하지 않습니다: `~/.claude/tools/verif/log_errors.py`(3b9a8eac…, 11-11 뒤 변경 없음), sidecar 사본, dynamics-dev·python-dev 패키지 판. 적어 두기를 권합니다.
- **W-e [R]** 부록 A:147 "두 결과의 경로 집합이 다르면(정체성 필드 말고) 불일치"는 지우는 집합을 정하지 않습니다(양쪽 각자인지, 합집합인지). "각 쪽은 자기 목록을 지운다"를 한 줄 더합니다.

### 기록
- R-a (g)의 `v5_options.sha256` = d2b903a2…는 CRLF 작업 트리 바이트의 sha입니다. git blob(LF)은 a88ad603…이고 `w/crlf`, attr 없음입니다. autocrlf=true checkout에서만 성립하므로 (g)에 그렇게 적기를 권합니다.
- R-b W-2·W-3(필드 경로, 둘 다 다름, 모드 인자)·W-4(`state`, `gate_unreadable`, 순서)·W-6(실패 처리표, `compare_r4` 다시 돌림)·W-7((c) 13경로)·R-1(0절 공개, :19·:49·:129)·R-4·R-5·R-7은 문안상 닫혔습니다. 남은 것은 위 N-3·W-a·W-b입니다.
- R-c C16 이름은 `x16_records`·`c16` 안에서 스칼라 `dt_s`·`duration_expected_s`·`folder`·`rc_source`를 여전히 뺍니다. 비교기 선례와 같고, (:122) 문장 예외로 공개하면 충분합니다.
- R-d J-2 출력(TA의 436.8 모드 판정)은 rev26 낱말로 쓰지 않는다고 A형 규칙에 한 줄 두기를 권합니다.

## A형 규칙 수정 5 (TA 부분)
- **[차단(A형 봉인 전)] A-1 J-2가 문안대로는 돌 수 없음**
  - 3.1:100 "436.8 모드에서는 이 허용이 없다"이고, TA는 03_src를 바꿉니다(3.1:96).
  - 436.8 모드 head-check의 `b9f5707..TA -- 03_src 02_params` 확인은 경로 1에서 `resume4368_judge.py`:5093-5098 S-11, 경로 2 실행본에서 :190-192 관문 문제가 됩니다. 결과는 "nothing judged"입니다.
  - 돌더라도 N-1의 1·2(TA는 판정 도구를 더 고침)와 `p2v5c_*`·`v5j_u9`의 `v5_options.sha256`(TA는 `v5_options.py`를 바꿈, (g)는 `harness.json`만 뺌) 때문에 J-2 비교가 반드시 불일치합니다.
  - 권장: J-2용 head-check 허용(3.1 2항 목록)을 436.8 모드에도 적용하고, J-2 비교에서 뺄 TA 정체성 필드(도구 sha, `v5_options` 블록)를 열거합니다.
- 결정론과 고를 여지: J-2의 통과·불통과는 A형 결과와 무관합니다. 고정된 436.8 입력에 대한 회귀 확인이므로 결과를 보고 고를 여지는 보이지 않습니다. 같은 커밋 두 실행의 실측(`harness_path1` 대 `retry1`의 `head_check`·`r4_inputs`)도 완전히 같았습니다.
- 다만 J-2가 불일치한 뒤 TA를 고치고 다시 돌리는 횟수 규칙이 없습니다. "J-2는 TA 커밋당 1회, 재시도는 TA를 새로 고정한 뒤 공개"를 권합니다.

## 확인 필요
1. N-1의 절대 경로 처리를 (가) 메인 checkout 고정 또는 (나) checkout 루트 토큰을 I에 더함 가운데 무엇으로 할지. (가)이면 5단계 동안 메인 checkout이 T26(932f1fb 기반)으로 분리되므로, 다른 세션이 그 checkout을 쓰지 않는지 메인이 확인해야 합니다.

## 위임 필요
- control-expert: N-1~N-3, W-a~W-e를 문안과 `excl_fields_r1.py`에 반영하고, 부록 B를 다시 만들어 sha를 갱신합니다. 이어서 A형 A-1을 반영합니다.
- 위임 필요(python-expert): tools/verif 후보. 이번 즉석 점검 둘을 도구로 만들 만합니다.
  - "제외 목록 대 도구 파일 sha 대조"(비교 대상 64자리 16진 잎 ↔ `git show <commit>:<files>` raw·LF·CRLF sha, 값 비출력)
  - "인자 목록 원소 꼴 열거"
  - 입력은 출력 폴더, 제외 목록, 커밋, 파일 글롭입니다. 출력은 경로와 맞은 파일 이름이고, 종료 코드는 0 없음 / 1 발견 / 2 입력 오류입니다.

## 검사하지 못한 것
- T26·TA 코드는 아직 없어, 실제로 어느 파일이 바뀌는지는 추정입니다. `diff_vs_existing` 변화는 1.1 "모드" 행과 R26-2·R26-3에서 도출했습니다.
- 경로 2 출력의 다른 커밋 비교는 이름이 달라 하지 못했습니다(지난 감사와 같음).
- `v5paper_imua_rules_draft.md`는 TA 관련 줄(14, 84, 87, 88, 95-101, 223, 226, 257)만 읽었습니다.

## 실행한 검증
- **인터프리터**: python-dev `-I -B -X utf8`(`MKL_THREADING_LAYER=TBB`, `PYTHONDONTWRITEBYTECODE=1`)
- **부록 B 재생성**: rev26:185 명령 그대로 scratchpad에 실행했고, sha 8074503d가 같았습니다.
- **즉석 스크립트**(scratchpad `verif-rev26b\`)
  - b1: 제외 노드의 자식 키 이름, 시험 경로, 인자 목록 항목
  - b2: 비교 대상 잎의 커밋·절대 경로 꼴
  - b3: 비교 대상 16진 잎의 키 이름
  - b4: `932f1fb` 도구 파일 sha 대조
  - `-c` 한 줄 스크립트: 봉인 블록 꼴 집계, `u6` (설정 이름, 태그) 쌍, `argv` 원소 꼴
- **Grep·Read**: `judge4368_common.py`:720·747-811, `resume4368_judge.py`:5035-5099, 두 M4 실행본
- **git**: `show`(blob sha), `ls-files --eol`, `check-attr`
- **Get-FileHash**: 매니페스트·sidecar 사본, `log_errors.py`
- **지운 파일**: scratchpad `verif-rev26b\` 전부(guard.json, regen.json, b1~b4.py). 프로젝트 폴더 쓰기 0.
- **메모리**: `audit_pitfalls.md` 제외 목록 항목에 재감사 함정(좁힌 규칙이 놓친 도구 판 필드, 중첩 봉인 사본, 빈 커밋 이중 실행의 한계, "모든 출력" 기대식)을 덧붙였습니다.
- 원본 불변: verify 결과는 pass=True, folder_status=unchanged, 입력 79개였습니다. report_line은 앞부분만 받아 두고 state 파일을 지워서 전문을 다시 낼 수 없습니다. 받은 앞부분은 다음과 같습니다: "원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha v5_resume_4368_rules_rev26.md cd0aacf5…, v5paper_imua_rules_draft.md 3804880e…, excl_check.py eb0356ee…, excl_fields_r1.py 3da897c3…, excl_fields.py 37c57662…, …"
- 사용한 스킬: 없음
