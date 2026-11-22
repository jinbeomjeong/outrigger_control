# verif-protocol-auditor: rev26 봉인 전 감사 (2026-11-22)

(hand-back 원문 그대로)

## 감사 요약
- 본 결과: `judge_932f1fb/{harness_path1, harness_path1_retry1, harness_path2}`의 JSON 72개(`ind_las.json`·`u3.json` 포함)와 `judge_b9f5707/harness_path1`의 같은 이름 파일을 스크립트로 읽었습니다. 출력한 것은 키 경로·자식 키 이름·형 이름·값 꼴 분류(iso/commit/path/plain)·잎 개수, 그리고 두 실행 사이 같음/다름 표시뿐입니다. H-3·H-4 값은 출력하지 않았고 판정서 4.4·4.5절은 열지 않았습니다. 같음/다름 대조에서는 `u3_judge*.json`·`u3.json`·`ind_las.json`·경로 2 `harness.json`을 뺐습니다. 식별자 점검 `key_collide.json`은 수만 봤습니다(1,114 / 0 / 0).
- 대상: `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev26.md`(d27faa4b), 부록 B `rev26_fixed/rev26_d_excluded_fields.json`(6051f77f), `rev26_fixed/excl_fields.py`(37c57662). 시점은 실행 전(봉인 전)입니다.
- 기준 문서: 원판·rev1~rev25(seal_check 결과 seal_mismatch 0), `u3_u6_rerun_rules.md`(8de31882), 등급 대조 표 `r4_grade_compare_table.md`(602618ea), `compare_r4.py`(8ff3d32b), R4 공통 블록 `r4_common_block_draft.md`(d4788a60). 마지막 파일은 RD-1·RD-2·RD-5 원문이라 호출 입력 밖이지만 저장소에서 찾아 읽었습니다.
- **판정: 차단 2 / 실행 전 수정 7 / 기록 7. 봉인 불가.** 차단 둘 모두 봉인 뒤에는 고칠 수 없는 문안·부록 내용입니다(rev26:3 "봉인 뒤에는 고치지 않는다", :193 "봉인 뒤 이 목록에 경로를 더하거나 빼지 않는다").

## 발견 사항 (심각도순)

### [차단][R·T·I] B-1 새 도구 커밋으로 하는 재판정이 물려받은 RD-1 4·5와 RD-2 확인을 통과할 수 없음 — 5단계가 멈추거나 봉인 뒤 임의로 바꿔야 함
- **근거**
  - rev26:9 "여기 적지 않은 정의·…·두 경로 절차는 그대로다". rev26에는 판정 checkout·HEAD·blob 확인을 다시 정한 문장이 없습니다.
  - R4 공통 블록:14 RD-1 4: "두 경로 R4 허용 목록 파일마다 `git show M4:<파일>`과 `git show R4:<파일>`의 LF 바이트 sha256이 같다. `git diff --name-only b9f5707..M4 -- 03_src 02_params`가 비어 있다". 공통 블록:15 RD-1 5: "판정 도구는 M4 checkout에서 돈다 … HEAD가 M4 전체 해시인지 확인하고 아니면 S-12".
  - `_fixed/run/run_judgement_path1_M4.ps1`:13-14 `$M4='932f1fb…'`, `$R4='1ab93f0…'`. :30-43 허용 목록에 `u3_judge_4368.py`·`judge4368_common.py`·`resume4368_judge.py`가 들어 있습니다. :84-86에서 head-check가 0이 아니면 `throw "… nothing judged"`입니다.
  - `scripts/resume4368_judge.py`:5079-5098: HEAD ≠ expect면 `S-12`. 목록 파일 blob이 expect와 R4에서 다르거나 `03_src 02_params` 변경이 있으면 `S-11`.
  - git 결과: `b9f5707..master -- 03_src 02_params`에 6개 파일(`hydraulics/v5_options.py` 포함), `b9f5707..v5-imua`에 14개 파일이 있습니다.
  - rev26:29 "A형 태그 처리(`_IMUA`) … 같은 도구 커밋에 넣는 것은 허용한다". rev26:30은 그 처리가 `03_src/.../v5_options.py`에 있다고 적습니다.
  - (d) 대상 안에 커밋에 따라 바뀌는 필드가 있고 부록 B에 없습니다. 구조 점검 결과, 비교에 남는 잎은 다음과 같습니다.
    - `harness_path1(_retry1)/head_check.json`: `blobs[].M4`, `blobs[].R4`, `blobs[].same`, `diff_exit`, `exit_code`. 원 출력에서 빈 리스트인 `markers`·`src_params_changed`가 새 출력에서 채워지면 새 경로가 생깁니다.
    - 경로 2 `harness.json`: `v5_options.sha256`(64자리 16진), `v5_options.path`, `head_check.ok`.
- **실패 시나리오**
  - 5단계를 M4 실행본 꼴로 돌리면 HEAD ≠ 932f1fb이라 S-12, 또는 고친 도구 파일의 blob ≠ R4라 S-11로 "nothing judged"에서 끝납니다. 이 시도가 "1회"(rev26:62)를 쓴 것인지 정해져 있지 않습니다.
  - 메인이 `--expect`·`--r4`·`--files`를 봉인 뒤에 고르면, 결과를 아는 사람이 고르는 갈림길이 됩니다.
  - 어떻게 고르든 `head_check.json`의 `blobs[]`와 `v5_options.sha256`이 바뀝니다. 그러면 (d)가 "판정 불가(rev26 기대 효과 불일치)"가 되고, rev26:86에 따라 새 사용자 결정 없이는 더 고칠 수 없습니다.
  - A형 처리를 같은 커밋에 넣으면 03_src가 바뀌어, 하네스 판정이 쓰는 태그 술어 모듈 자체가 달라집니다. RD-1 4가 막던 경우입니다.
  - 봉인 목록도 정해져 있지 않습니다. rev26 봉인을 도구가 확인할지(RD-2의 26판 → 27판), 확인하면 새 값이 어느 키에 들어가는지가 없습니다. `rules_seal.revisions`·`rules_rev13_to_rev25_sha256`·경로 2 `seals` 안이면 (d)의 제외 경로 아래라 괜찮지만, `rules_rev26_sha256` 같은 새 최상위 키면 rev26:111에 따라 불일치입니다. 확인하지 않으면 S축 공백입니다.
- **권장 조치(control-expert, 봉인 전 rev26에 한 절을 더함)**
  1. 보완 브랜치의 기준 커밋을 정합니다. `932f1fb`를 권합니다.
  2. 바꿔도 되는 파일 목록을 둡니다. 두 경로 판정 도구 파일만 허용하고 03_src·02_params는 0으로 합니다.
  3. 5단계의 기대 HEAD를 새 도구 커밋 전체 해시로 두고, 4′에서 고정합니다.
  4. RD-1 4를 대신할 조건을 적습니다. 바뀌지 않은 파일은 blob = M4, 바뀐 파일은 목록으로 열거하고, `b9f5707..<새 커밋> -- 03_src 02_params`는 0이어야 합니다.
  5. head-check 출력과 `v5_options` 블록을 (d)에서 어떻게 볼지 정합니다. 따로 기대 효과로 두기를 권합니다.
  6. A형의 03_src 변경은 이 커밋에 넣지 않는다고 적습니다.
  7. rev26 봉인을 도구가 확인하는지와 그 값이 들어갈 키 위치를 적습니다.

### [차단][E·R] B-2 부록 B의 제외가 RD-5와 rev26 본문보다 넓음 — 비교기 S-13 원천과 판정값이 (d)에서 빠짐
- **근거**
  - rev26:122 "물리 시각·판정값은 빼지 않는다". rev26:123 "비교기 S-13 항목의 원천 키(예: `v0_pair_source.source` …)는 위 범주에 걸리지 않아 모두 비교 대상으로 남는다". rev26:106 "경로 2 `harness.json`의 `bundles.H-4`도 diff 0이어야 한다". rev26:184 "부록 B와 이 표가 다르면 부록 B가 맞다".
  - RD-5(공통 블록:55)에서 빼는 것: 실행 정체성 키(checkout 커밋, 실행 시각, 그 실행의 출력 위치; "출력 경로 인자는 인자 목록 전체가 아니라 그 원소만"), 봉인 블록, 도구 판·규칙 설명 문자열, 도구 sha·공개 블록, 입력 파일 경로·sha256 블록, 자유 문장 사유 키.
  - 생성 규칙 `excl_fields.py`:30 `^sources?$`와 :32-35 F 이름 집합(`files`, `detail`, `folder`, `dt_s` 등)이 문제입니다. :41-44 이름이 맞으면 값의 꼴과 무관하게, :67-70 그 키의 하위 나무 전체를 뺍니다. 이 집합의 출처는 `compare_r4.py`:437-456 `C16_EXCLUDED_KEYS`인데, 이는 C-9~C-11 행 항목용입니다(:456 "RD-5 / CD-10"). 그것을 모든 파일에 넓혔습니다.
- **값 비출력 대조 결과**(제외 경로가 가리키는 원 출력 노드의 형·자식 키 이름·잎 수)
  1. 비교기 원천이 빠짐(rev26:123과 모순)
     - `harness_path1/grid_h10.json :: v0_pair_source.source`, `harness_path2/p2v5c_grid.json :: v0_pair.source`가 S로 빠집니다. 둘 다 str.
     - 이것은 `compare_r4.py`:84·:135 `pair_source`의 원천이고, 등급 대조 표:111(H-9 격자 등급 출처 "`v0_pair_source.source`")와 :151(`pair_source` → S-13)에 쓰입니다.
     - `family_f_trigger.json :: v0_pair_source.source`도 빠집니다.
  2. 판정값이 든 구조 노드를 이름만 보고 뺌(rev26:122·:106과 모순)
     - `harness_path1_retry1/r4_inputs.json :: files`: 잎 355, 자식 키 `stops`, `events`, `exists`, `kinds`, `results`, `IND_LAS` …. 등급 대조 표:72 "r4_inputs.json의 멈춤·판정 불가 항목"이 경로 1 436.8 층의 원천입니다.
     - `harness_path1_retry1/stage1_judge.json :: R4.H-9_grid_R16_7.files`: 자식 키 `j_p3_status`, `pass`, `runs`, `H-7`.
     - `harness_path2/harness.json :: bundles.H-{1,4,5,6,7,8,9,10}.files`: H-4는 잎 58, 자식 키 `classes`, `kind_lines`, `lines`, `unchanged`, `stored_hash`, `IND_LAS`, `ABL`, `IND`. 그래서 rev26:106이 요구하는 "`bundles.H-4` diff 0"의 일부가 실제로는 비교되지 않습니다.
     - `harness_path2/p2v5c_grid.json :: v0_pair.sample.detail`: 자식 키 `status`, `runs`, `key`, `results_index`.
     - `harness_path2/p2v5c_noise.json :: reaggregated.seedext.{V0,VB}.detail`: 자식 키 `same_hash`, `noise_found`, `hash_missing`.
     - `harness_path2/p2v5c_stage1.json :: H-10.LS_conditions.LS1~LS4.detail`: 자식 키 `L-a`~`L-e`, `lines`.
     - `harness_path2/c16.json :: rows.*.items.G6_source`: 자식 키 `P3-2_verdict`, `t_ready_after_loop_start_s`. 비교기 C16 선례와는 같지만 rev26:122 문장과는 맞지 않습니다.
  3. 인자 목록 전체를 뺌(RD-5 "그 원소만"과 모순)
     - `argv` 11개(잎 117), `cmd` 4개(잎 31, `p2v5c_noise.json`), `command` 5개(잎 39, `h6_judge`·`h8_noise_judge`)가 통째로 빠집니다.
     - 그래서 5단계가 다른 모드 플래그(예: (f)의 A형 모드)나 다른 입력 인자로 돌아도 (d)에 드러나지 않습니다.
  4. 판정 실행의 정체성이 아닌 입력 쪽 값이 I·S로 빠짐
     - `sidecars.json :: rows[].start/end.times[]`(iso 24개씩, 436.8 실행 sidecar의 시각)과 `rows[].start/end.seals_ok`(int 20개씩)
     - `log_errors_run_harness.json :: steps[].done_line`(73)
     - `overlap_steps.json :: rows[].output`(73, 값 꼴 plain. 판정 출력 위치가 아님)
     - `family_table.json :: rows[].source`(7,028), `p2v5c_noise.json :: TABLE_REAGG[].source`(14)
- **실패 시나리오**: 보완 커밋(또는 B-1의 03_src 변경)이 위 노드의 값을 바꿔도 (d)는 "diff 0"으로 나옵니다. 4′의 "범위 밖 변경 0" 확인이 틀린 확증이 됩니다. 차이를 숨기는 쪽이라 위험한 방향입니다.
- **권장 조치(control-expert, 봉인 전 부록 B를 다시 만듦)**
  - F·S 이름 규칙은 값이 스칼라인 잎이나, 자식이 경로·sha뿐인 블록(예: `files[].{result_file, sha256}`)에만 적용합니다.
  - `^source$`를 빼거나 도구 출처 문자열로 좁힙니다.
  - `argv`·`cmd`·`command`는 출력 경로 원소만 뺍니다.
  - ISO·경로 꼴 규칙은 판정 실행 자신의 필드로 좁힙니다. 판별에는 아래 4′ 이중 실행에서 값이 달라지는 필드만 정체성으로 보는 방법을 쓸 수 있습니다.
  - 다시 만든 뒤 sha를 새로 적습니다.

## 실행 전 수정
- **[S] W-1 줄바꿈 보호 없음**
  - `git check-attr text`가 `v5_resume_4368_rules_rev26.md`, `rev26_seal_candidate_draft.md`, `rev26_fixed/*`에서 모두 unspecified입니다. `core.autocrlf=true`입니다. `seal_check`가 `attr_unprotected` 2건을 냈습니다.
  - 부록 JSON은 CRLF(4,120줄)이고 sha `6051f77f`도 CRLF 바이트 값입니다. `-text` 없이 `git add`하면 색인에 LF로 들어가 다른 checkout에서 봉인이 깨집니다.
  - `.gitattributes`에 `-text`를 더할 대상: rev26 `.md`, `.sha256`, `_seal_candidate_draft.md`, `v5_resume_4368/rev26_fixed/**`, 5단계 새 폴더 `v5_resume_4368/judge_rev26_*/**`, 근거 폴더 `v5paper_imua_stats/**`.
  - `.sha256` 첫 줄은 rev26.md 값으로 둡니다. RD-2·R2-9의 "첫 토큰" 읽기 때문입니다. 부록 두 파일은 그다음 줄에 적습니다. (메인)
- **[R] W-2 부록 A 경로 표기가 모호함**
  - 제외 경로 10개가 점이 든 키를 지납니다. 예: `u9_judge.json :: keys[].VB0.8.J[].detail`, `g3.json :: identity.u3_C_none.json.why`, `p2v5c_noise.json :: reaggregated.line_grades.noise_V0.{*}.why`. 점이 든 키가 있는 파일은 60개입니다. rev26:110의 "`.`는 dict 단계"로는 이 경로를 한 가지로 풀 수 없습니다.
  - `{*}`는 파일마다 "키 > 40"에 따라 정해지므로 새 출력에서 수가 40을 넘나들면 경로 꼴이 달라집니다.
  - retry1 목록을 새 `harness_path1` 파일에 대는 방법, 그리고 파일이 빠지거나 더 생길 때의 처리도 없습니다.
  - 권고: "경로는 `excl_fields.py` `walk`와 같은 방식으로 양쪽 출력에서 만들어 문자열로 맞춘다", "`{*}` 판정은 원 출력 기준", "파일 집합도 같아야 한다"를 더합니다.
- **[R] W-3 R26-3 정의가 덜 닫힘**
  - rev26:26 "하나만 4.1 표와 맞거나 태그가 없으면 … S-2"는, 둘 다 있는데 둘 다 4.1과 다른 경우를 정하지 않습니다.
  - `controller`·`controller_tag`를 어느 경로에서 읽는지도 없습니다. 경로 2에는 `controller_tag`, `v5.controller_tag`, `v5_hydraulics.controller_tag`, `resume_k1.controller_tag`가 있습니다(`path2/p2_4368.py`:824, `path2/p2_u3.py`:440·:687). 두 작성자가 각자 맞추면(rev26:57) 갈릴 수 있습니다.
  - (e)의 합성 고정물 3건에 "둘 다 다름"이 없습니다.
  - (f)의 "436.8 모드 / A형 모드"를 무엇으로 고르는지(인자·설정)도 정해져 있지 않습니다.
  - 권고: "두 필드가 모두 있고 모두 4.1 문자열과 같을 때만 통과, 그 밖은 S-2"로 쓰고, 필드 경로와 모드 선택 방법을 적습니다.
- **[R] W-4 R26-2 키 이름**
  - 등급 대조 표:42는 경로 1의 `기록 완료`를 `state` 키에서 읽는다고 적는데, R26-2는 `status`를 더합니다(rev26:25·:36).
  - 2절 표의 "판독 불가 n"이 어느 키인지 이름이 없습니다. `ind_las.json`에는 `gate_unreadable`(int), `gate_not_started`, `gate_started`가 있습니다.
  - 칸 2·5 사이 우선순위가 없습니다. 예: `adapter_defect` 참이면서 `record_state` ≠ "기록"인 경우.
  - 436.8 데이터는 첫 칸이라 지금은 영향이 없지만, A형이 같은 커밋을 씁니다.
- **[E] W-5 4′ 합성 이중 실행으로는 목록 밖 정체성 필드를 다 못 잡음**
  - 같은 커밋·같은 checkout에서 두 번 돌리면, 커밋이나 checkout에 따라 바뀌는 필드(B-1의 `blobs[]`, `v5_options.sha256`·`.path`)는 차이가 나지 않습니다.
  - 부록 B에는 행별 경로가 있어(`c16.json :: rows.R4368X_….files`, `g3.json :: identity.u3_….json.why`) 합성 고정물에는 옮겨지지 않습니다. rev26:71은 "범주"로, :193은 "목록"으로 적어 두 기준이 섞여 있습니다.
  - 참고: 실측으로 `harness_path1`과 `retry1`(같은 커밋, 다른 실행)의 `head_check`·`r4_inputs`를 비교했더니 목록 밖 차이 0이었고, `head_check`는 완전히 같았습니다. 즉 실행 시각·폴더만 바꿔서는 커밋에 딸린 필드가 드러나지 않습니다.
  - 권고: 4′에 다른 checkout(다른 절대 경로)과 빈 커밋 하나를 더 둔 실행을 더하고, 범주 규칙으로 판정합니다.
- **[R·T] W-6 5단계 실패 처리표와 실행 자료 고정이 없음**
  - 종료 코드·멈춤별 조치(다시 돌려도 되는지, 결과를 본 것으로 치는 시점, 출력 처리)가 없습니다. 원 M4 실행도 `harness_path1_retry1`이 생겼습니다.
  - 5단계 실행 스크립트의 sha를 실행 전에 고정하고 감사(`ps1_lint`)하는 절차가 없습니다.
  - rev26:87은 재판정 뒤 표지 집합 비교를 전제하지만, `compare_r4.py`(8ff3d32b, `--path1-dir`·`--path2-dir`·`--baseline`)를 새 폴더에 돌린다는 문장이 없습니다.
- **[S] W-7 (c)의 제외 집합이 정의되지 않음**: rev26:81 "부록 B의 `ind_las.json` 해당 범주 필드 제외"라고 적었지만, 부록 B에서 `ind_las.json`은 `scope_skipped`라 경로가 하나도 없습니다. `ind_las.json`에는 `rules_seal.*`·`rules_rev*_sha256`·`rules_rev13_to_rev25_sha256.*`가 있습니다. B-1의 봉인 목록이 바뀌면 (c)가 깨집니다. 경로를 열거해야 합니다.

## 기록
- R-1 rev26:48("IND_LAS 표지로 생긴 경로 1 H-4 `판정 불가`는 … S-13으로 세지 않고")은 등급 대조 표 1.2 4에 예외를 하나 더하는 것입니다. 그래서 rev26:9·:25의 "등급 대조 표는 고치지 않는다", "규칙 변경 아님"과 어긋납니다. 436.8 데이터는 첫 칸이라 효과가 없고, 작성자가 그 칸을 안다는 사실은 :49에 공개되어 있습니다. 판정서에는 결과 뒤에 넣은 예외로 적기를 권합니다.
- R-2 통계 검토 3의 "봉인 가능"은 `_seal_candidate_draft.md` 수정 1을 대상으로 했습니다(`stats_review_rev3_20261122.md`:16). 부록 A·B(rev26:97-193)는 그 뒤에 더해졌습니다(diff `@@ -95 +95,99`). S-2(열거) 조건은 꼴로 충족했지만, 통계 검토는 B의 내용을 보지 않았습니다.
- R-3 부록 B는 다시 만들 수 있습니다. python-dev 3.13으로 `excl_fields.py`를 scratchpad에 다시 돌린 sha가 `6051f77f`로 같았고, 수도 I 101 / S 667 / F 225 = 993, 파일 70으로 rev26:117-120과 같습니다. 다만 ROOT가 절대 경로이고(:22), 텍스트 모드로 써서 CRLF가 되므로(:96) 다른 OS에서는 바이트가 달라집니다.
- R-4 rev26:18이 가리키는 `v5paper_imua_rules.md`는 아직 없습니다(`ref_check` ref_missing, 있는 것은 `_draft`뿐).
- R-5 인용 근거가 git 밖에 있습니다: `rev26_fixed/*`, `v5paper_imua_stats/*`(`key_collide.json` 포함). `baseline_check sums`에서 SUMS 48항목은 불일치 0·결측 0이지만 49개 모두 `cited_untracked`입니다. 봉인 커밋에 함께 넣어야 합니다.
- R-6 R26-1의 동치 대안 근거 `key_collide.json`은 distinct 1,114, 연구 사이 중복 0, 연구 안 중복 0으로 rev26:24·:56과 맞습니다. 이 파일은 SUMS 9행에 sha가 고정되어 있습니다.
- R-7 11-16 이후 판정 도구 파일을 고친 커밋은 모든 브랜치에서 0입니다(`git log --all --since=2026-11-16`). 미리 만들어 둔 보완은 없습니다. rev26:60의 금지는 "봉인 뒤"만 다루고, 그 앞의 실행은 :62의 공개로 다룹니다. 4′에서 셀 범위로 적어 둘 것을 권합니다.

## 규칙↔도구 대조표 (근거 줄 원문 대조)
| rev26 인용 | 원문 확인 | 판단 |
|---|---|---|
| `u3_u6_rerun_rules.md`:19 | "키 \| v4 저장 파일의 `records[].id`(wrapper) 또는 `results[].key`(screen) 문자열 그대로". rev1·rev2에 이 정의를 바꾸는 줄 없음 | 일치 |
| 등급 대조 표 36~46 | 1.1 낱말 대응표, :46 "위에 없는 낱말이 나오면 … 판정 불가" | 일치. 단 :42 경로 1 키는 `state`(W-4) |
| 등급 대조 표 61·105·108·115 | 기록 묶음 / H-4 "멈춤·판정 불가는 H-3과 같은 규칙 … IND_LAS는 기록 열 … 표지 키가 없으면 결정 133의 4" / H-7 기록 불완전 정의 / H-12 한 경로 기록 | 일치 |
| 등급 대조 표 140~153 | S-13 항목 표(:151 `pair_source`) | 일치. 그러나 부록 B가 그 원천을 뺌(B-2) |
| 원판 70~75·80·281 | 4.1 표(V0·VB·ABL `ABL_LAS_K1`·IND/IND_LAS), :80 "섞이면 멈춘다(8.2 S-2)", :281 "S-2 \| 4.1 태그와 다르거나 한 묶음 안에 두 판이 섞였다" | 일치 |
| `compare_r4.py` 81·132·291·437~455 | `bundles.{bundle}.markers` / `bundles.{bundle}.gates` / `RD8_MARKER` / `C16_EXCLUDED_KEYS` | 일치. :802-812·:1094-1099도 RD-8 유무만 봄. `ind_las` 참조 0(Grep) |
| R4 공통 블록 54(RD-4) | 묶음 이름과 멈춤 이름을 섞지 말라는 규칙 | 표지 접두 `IND_LAS:`의 근거로는 넓혀 읽은 것(기록 수준) |
| (인용 없음) RD-1 4·5, RD-2 | 공통 블록:14-15·:18 | rev26이 다시 정하지 않음(B-1) |

## 확인 필요
1. 5단계 도구 커밋의 기준과 RD-1 4·5를 대신할 조건(B-1). 932f1fb에서 가르고 03_src는 0, A형은 별도 커밋으로 둘지 정해야 합니다. 사용자 결정 또는 control-expert 문안이 필요합니다.
2. 도구가 rev26 봉인을 확인할지(27판), 그리고 그 출력 키 위치(B-1·W-7).
3. 부록 B를 다시 만드는 규칙(B-2): 구조 노드를 어떻게 다룰지, `source`, `argv` 원소, 입력 쪽 시각.

## 위임 필요
- control-expert: B-1·B-2·W-2~W-7 문안을 고치고 부록 B를 다시 만듭니다. 아직 봉인 전이므로 같은 rev26 후보를 고치면 됩니다.
- 위임 필요(python-expert): tools/verif 후보. 제외 경로 목록이 있는 K-10 JSON 비교기입니다.
  - 입력: 원 출력 폴더, 새 출력 폴더, 제외 목록 JSON(`excl_fields` 꼴).
  - 출력: 파일·경로별 같음/다름/새 경로, 값 비출력.
  - 같이 볼 것: 제외 노드 자식 키 이름 점검, 점이 든 키, `{*}` 기준.
  - 종료 코드: 0 같음 / 1 다름 / 2 입력 오류.
  - 이번에 즉석으로 한 "제외 경로 아래 자식 키 열거"와 "비교기 FIELD_SOURCES 접두 대조"를 이 도구의 하위 명령으로 넣을 수 있습니다. 6단계 (d) 대조에 바로 쓰입니다.

## 메인 세션 권고
- 봉인 커밋 전에 `.gitattributes -text` 줄을 더하고 `git status --ignored`로 인용 파일이 빠지지 않는지 봅니다(W-1).
- 문안을 고친 뒤 이 감사를 다시 부릅니다(실행 전).

## 검사하지 못한 것
- 경로 2는 다른 커밋 출력과 같음/다름 대조를 하지 못했습니다(`judge_b9f5707/harness_path2` 파일 이름이 `p2h_*`라 겹치지 않음).
- R26-1의 결함 원인 코드 줄(경로 2 screen 키 처리)은 읽지 않았습니다. 정의 문장만 대조했습니다.
- 경로 1 IND_LAS를 만드는 코드와 `gate_unreadable`의 뜻은 키 이름만 봤습니다.
- `timeline.py`는 돌리지 않았습니다(결과 뒤 개정이라는 사실은 0절에 공개되어 있음).

## 실행한 검증
- **인터프리터**: python-dev `C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B`(`MKL_THREADING_LAYER=TBB`).
- **verif 도구**
  - `seal_check.py --repo … rules*.md u3_u6_rerun_rules*.md --no-git`: error 0. rev26은 `seal_missing`(봉인 전이라 정상)과 `attr_unprotected` 2건.
  - `ref_check.py rev26.md --repo`: 진짜 결측은 R-4와 `.sha256`(아직 만들기 전). 나머지는 이름만 적은 경로를 못 푼 거짓 양성.
  - `baseline_check.py sums v5paper_imua_stats/SHA256SUMS`: 불일치 0, 49개 untracked.
- **git 조회**: `check-attr text eol`, `config core.autocrlf`, `check-ignore -v`, `ls-files --eol`, `diff --no-index`(초안 대 rev26), `diff --name-only b9f5707..{HEAD,master} -- 03_src 02_params`, `log --all --since`, `worktree list`.
- **Get-FileHash, CRLF·BOM 셈**: JSON CRLF 4120, md·py LF, BOM 없음.
- **즉석 스크립트**(scratchpad `verif-rev26\`에서 실행, 값 비출력, 모두 지움)
  - `excl_fields.py` 재생성 sha 대조
  - `a1_struct.py`/`a1_show*.py`: 제외 경로의 노드 형·자식 키·점 키
  - `a2_sources.py`: `compare_r4.py` FIELD_SOURCES를 ast로 읽고 등급 대조 표 원천과 접두 대조
  - `a3_crossrun.py`: path1 대 retry1, 932f1fb 대 b9f5707의 같음/다름
  - `-c` 한 줄 스크립트로 `ind_las.json`·`seal.json`·`head_check.json`·`harness.json` 키 구조를 봄
  - 검사 이름 "제외 목록 구조 점검"을 tools/verif 후보로 위 위임에 올렸습니다.
- **만든 뒤 지운 파일**: scratchpad `verif-rev26\`(guard.json, regen.json, a1.json, a1_struct.py, a1_show.py, a1_show2.py, a2_sources.py, a3_crossrun.py) 전부. 프로젝트 폴더에 남긴 부산물 없음(`-B`, `PYTHONDONTWRITEBYTECODE=1`).
- **메모리**: `audit_pitfalls.md`에 두 항목(새 도구 커밋 재판정 대 물려받은 HEAD·blob·03_src 확인 / 출력 키 이름으로 만든 제외 목록)과 `MEMORY.md` 색인을 더했습니다.
- 최종 판정 직전에 source_guard verify로 입력 162개가 불변임을 다시 확인했고, 판정은 그 내용 기준입니다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha v5_resume_4368_rules_rev1_seal_candidate_draft.md 187b6c2d…, v5_resume_4368_rules_rev1.md d9094fda…, v5_resume_4368_rules_rev10_seal_candidate_draft.md 5739ac66…, v5_resume_4368_rules_rev10.md 62a0bd8d…, v5_resume_4368_rules_rev11_seal_candidate_draft.md ccdf42b2…, v5_resume_4368_rules_rev11.md 9bac4524…, v5_resume_4368_rules_rev12_seal_candidate_draft.md 45dcf2f9…, v5_resume_4368_rules_rev12.md 78f1f99b…, v5_resume_4368_rules_rev13_seal_candidate_draft.md 5f0658de…, v5_resume_4368_rules_rev13.md 383bffc1…, v5_resume_4368_rules_rev14_seal_candidate_draft.md d46ca3fd…, v5_resume_4368_rules_rev14.md baedeab4…, v5_resume_4368_rules_rev15_seal_candidate_draft.md 1107aa24…, v5_resume_4368_rules_rev15.md 0162561c…, v5_resume_4368_rules_rev16_seal_candidate_draft.md 292b1420…, v5_resume_4368_rules_rev16.md b3899194…, v5_resume_4368_rules_rev17_seal_candidate_draft.md 121e7258…, v5_resume_4368_rules_rev17.md 9400660e…, v5_resume_4368_rules_rev18_seal_candidate_draft.md 1488d875…, v5_resume_4368_rules_rev18.md 3693a69c…, v5_resume_4368_rules_rev19_seal_candidate_draft.md 631bd2ff…, v5_resume_4368_rules_rev19.md 7f87b8bb…, v5_resume_4368_rules_rev2_seal_candidate_draft.md 3fbb990a…, v5_resume_4368_rules_rev2.md 497e4614…, v5_resume_4368_rules_rev20_seal_candidate_draft.md ceca2c25…, v5_resume_4368_rules_rev20.md 615a8fbd…, v5_resume_4368_rules_rev21_seal_candidate_draft.md 39cb349f…, v5_resume_4368_rules_rev21.md ecd70949…, v5_resume_4368_rules_rev22_seal_candidate_draft.md 787de1cd…, v5_resume_4368_rules_rev22.md a48a81f9…, v5_resume_4368_rules_rev23_seal_candidate_draft.md dde11cdb…, v5_resume_4368_rules_rev23.md fa72e172…, v5_resume_4368_rules_rev24_seal_candidate_draft.md 75fca3cc…, v5_resume_4368_rules_rev24.md f475cf77…, v5_resume_4368_rules_rev25_seal_candidate_draft.md c1f28d62…, v5_resume_4368_rules_rev25.md c0b778fd…, v5_resume_4368_rules_rev26_seal_candidate_draft.md f0361dd2…, v5_resume_4368_rules_rev26.md d27faa4b…, v5_resume_4368_rules_rev3_seal_candidate_draft.md 2919e3bb…, v5_resume_4368_rules_rev3.md dad8dfa6…, v5_resume_4368_rules_rev4_seal_candidate_draft.md be8feeaa…, v5_resume_4368_rules_rev4.md 7ea87a30…, v5_resume_4368_rules_rev5_seal_candidate_draft.md 9881e0e6…, v5_resume_4368_rules_rev5.md 452a8436…, v5_resume_4368_rules_rev6_seal_candidate_draft.md e9341fdc…, v5_resume_4368_rules_rev6.md 809e5639…, v5_resume_4368_rules_rev7_seal_candidate_draft.md 8539ee31…, v5_resume_4368_rules_rev7.md e81f7d31…, v5_resume_4368_rules_rev8_seal_candidate_draft.md 8dcd2cb3…, v5_resume_4368_rules_rev8.md 3ecafaaf…, v5_resume_4368_rules_rev9_seal_candidate_draft.md f7025830…, v5_resume_4368_rules_rev9.md 4cf7843c…, v5_resume_4368_rules_seal_candidate_draft.md 8dce4e3a…, v5_resume_4368_rules.md 9019b405…, v5_resume_4368_rules_rev1.sha256 6dd3d6f6…, v5_resume_4368_rules_rev10.sha256 459acd26…, v5_resume_4368_rules_rev11.sha256 d3cf5188…, v5_resume_4368_rules_rev12.sha256 4b77430f…, v5_resume_4368_rules_rev13.sha256 7fb38b57…, v5_resume_4368_rules_rev14.sha256 94f20305…, v5_resume_4368_rules_rev15.sha256 d19ea913…, v5_resume_4368_rules_rev16.sha256 d832afbd…, v5_resume_4368_rules_rev17.sha256 cb5b9bb9…, v5_resume_4368_rules_rev18.sha256 8860af1e…, v5_resume_4368_rules_rev19.sha256 9e3db2ea…, v5_resume_4368_rules_rev2.sha256 ef3e0b73…, v5_resume_4368_rules_rev20.sha256 c3923122…, v5_resume_4368_rules_rev21.sha256 799ddcb2…, v5_resume_4368_rules_rev22.sha256 b35891d3…, v5_resume_4368_rules_rev23.sha256 b58a175e…, v5_resume_4368_rules_rev24.sha256 0341a47e…, v5_resume_4368_rules_rev25.sha256 0168d28a…, v5_resume_4368_rules_rev3.sha256 14413dcb…, v5_resume_4368_rules_rev4.sha256 d7b71c73…, v5_resume_4368_rules_rev5.sha256 3358d9ed…, v5_resume_4368_rules_rev6.sha256 36459846…, v5_resume_4368_rules_rev7.sha256 d23bab29…, v5_resume_4368_rules_rev8.sha256 4dab8d2f…, v5_resume_4368_rules_rev9.sha256 620876ab…, v5_resume_4368_rules.sha256 d69873c7…, excl_fields.py 37c57662…, rev26_d_excluded_fields.json 6051f77f…, r4_grade_compare_table.md 602618ea…, compare_r4.py 8ff3d32b…, r4_common_block_draft.md d4788a60…, u3_u6_rerun_rules.md 8de31882…, u3_u6_rerun_rules.sha256 318a0532…, stats_review_rev2_rev26_20261122.md 48465452…, stats_review_rev3_20261122.md dcd7bd51…, key_collide.json 3125a1be…, anchor_map.json 7336a5bd…, appendix_a.json 0b6ad25a…, d1_judge.json 7559c750…, dg3_hash.json 73584733…, family_f_trigger.json 925a0eb9…, family_f.json 4ed034b5…, family_table.json 01dfa819…, grid_h10.json 5d35ae3c…, grid_v0_sample.json 62d9e339…, h11.json c19e49d2…, h12_t4h_replay.json 1e14a694…, h12.json 51cfd778…, h2_select.json 23ef679c…, h6_judge.json f8352c5d…, h6_L1_reference.json a591c3a8…, h6_r79_judge.json d95627ac…, h8_noise_judge.json 6cc77f3f…, head_check.json 3a6d6f7f…, import_check.json 3bf4b824…, ind_las.json 00de905b…, item_list.json 9e9c0d4d…, jp_reuse.json f895c431…, k1_class.json 084b2ab0…, key_map.json 19dcae15…, keyset_grid_r67_main.json eff326d5…, keyset_grid_r67_top.json 79f9b8cc…, keyset_grid_r69_bottom.json ba8ec1f7…, keyset_grid_r69_top.json b881b6a2…, keyset_h6.json 834753e0…, keyset_h7.json bd799bfa…, keyset_h8_noise_V0.json cdc71f2f…, keyset_h8_noise_VB.json c93ee88f…, keyset_h8_seedext_V0.json 61a492ff…, keyset_h8_seedext_VB.json 7790591a…, log_errors_run_harness.json a691ca27…, overlap_steps.json c8dfe4b0…, r4_inputs.json 729022c3…, r4_lists.json f1a3cf5d…, reagg_items.json 257e6e35…, record_check.json 70b98750…, sidecars.json 476ae5b7…, stroke_H-1.json f53a327e…, stroke_H-10.json 0d189282…, stroke_H-3.json 662bcbb0…, stroke_H-4.json 5a8b3a69…, stroke_H-5.json d1453d0d…, stroke_H-6.json 6f4922ab…, stroke_H-7.json bb5c781e…, stroke_H-8.json 9698cff2…, u3_judge_k1.json 4ac5b939…, u3_judge.json 8794234b…, u9_judge.json d52e203e…, x16_records.json 18caaadc…, head_check.json 3a6d6f7f…, r4_inputs.json 729022c3…, stage1_judge.json a6fd45ec…, stroke_H-9.json ce6d4f86…, anchors.json a1ec53ce…, c16.json 3c000cb9…, d1.json 581b15ae…, g3.json 58bafd59…, harness.json 62910051…, jp.json 5d43e366…, manifest.json fa0b72bf…, p2v5c_grid.json e6c47d76…, p2v5c_merge.json 3d981bc4…, p2v5c_noise.json 8c06ebdb…, p2v5c_stage1.json 75f8e3ca…, rd13_items.json c800cc9e…, seal.json 5921db8e…, u3.json e2944ad3…, v5j_u9.json 2f1b60c6…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
