## 감사 요약
- 결론: 병합할 수 있다. 차단은 0건이다. 실행 전 수정 W-1~W-4는 병합 뒤, `12b_decide_e8`를 시작하기 전에 메인이 처리한다. 코드 수정은 필요 없다.
- 판정: 차단 0 / 실행 전 수정 4(W-1~W-4) / 기록 9(R-1~R-9).
- 본 결과: python-expert의 건식 decide 출력 `dry_decision.json`·`dry_decision_bad.json`(scratchpad\python-ed5tool8). 키가 있는지만 봤다(`key_presence`, 값은 출력하지 않음). 12b_vbk0_base_a1에서는 VBK0 b1·b2의 파일 sha·T4h 요약, step_record의 환경 변수 이름·`--workers`·mask, identity의 키 구조, 로그 오류 줄 수, READY 필드에 NaN·문자열이 있는지만 봤다. READY 값과 A/A 값은 출력하지 않았다. 블라인드(`cdry_a1/VBK_c92*`·`VBK_c93*`·`cdry_a1/logs/`, 12b VBK 출력)는 열지 않았다. 12b VBK 출력은 아직 없다.
- 시점과 대상
  - 시점: 실행 전(정오 8 도구 커밋 재개 직전, 병합 전)
  - 브랜치 `ed5-tool8`: c895bb72 → d4162add → 74a4bbf4. 부모는 master b853e107이라 fast-forward로 병합할 수 있다.
  - 실행 커밋 606f8713(`ed5-run5`, 잠김, 깨끗함)
- 기준 문서(봉인 일치, raw = LF, `-text`, CRLF 0, BOM 없음)
  - 정오 8 `jp3_remedy_spec_v5_erratum8.md`: 8c420e85
  - 경로 2 정오 `jp3_rev6_p2_handoff_ed5_e8.md`: ef33e619
  - 근거 SUMS 넷(정오 8 인용값과 같음): aa_stop e387907e, stats_e8 8b906fb9, stats_e8_review b00eb95a, e8_p2_leak 1247a9ee

## 발견 사항 (심각도순)

[실행 전 수정][I] W-1. 다음 단계부터 마지막 단계까지 master를 허용 경로로 묶어야 한다(확인 필요 2의 답: 규칙대로다)
- 근거
  - 정오 8:229 "'도구 커밋'은 실행에 쓰는 커밋(목록 커밋 포함)"
  - 정오 8:241 "판 5와 무관한 작업 트리 변경(예: `.claude/agents/` 아래 파일)은 … 커밋하면 위 규칙 밖이라 멈춘다"
  - 구현 `common_ed5.ps1:387-400` `Assert-ToolDiff`는 606f8713을 도구 커밋과 메인 HEAD 둘 다와 비교한다. 규칙 밖이면 종료 3이다.
  - 직접 분류한 결과(독립 스크립트), 규칙 밖 0줄
    - 606f8713↔74a4bbf4: 2267줄
    - 606f8713↔b853e107: 2248줄
  - 메인 작업 트리에 `.claude/agents/paper-reviewer.md`(M)가 커밋되지 않은 채 남아 있다.
- 실패 시나리오: step8까지 끝나기 전에 아래 가운데 하나가 master에 커밋되면 남은 단계가 모두 종료 3으로 멈춘다.
  - 다른 worktree 병합(v5-imua·imu-att 등)
  - `.claude/`·`.gitattributes`·`03_src`·`02_params` 변경
  - 다른 시험 파일 변경
  - `06_analysis` 기존 파일 수정(M)
  - 이 멈춤은 안전 쪽이지만 재시도 폴더가 늘어난다.
- 권장 조치(메인): 마지막 게이트 단계(step8 j9_main)가 끝날 때까지 master에는 다음만 커밋한다. 그 밖의 병합·커밋은 미룬다.
  - `00_docs/`·루트 `CLAUDE.md`의 M·A
  - `06_analysis/` 아래 추가(A)
  - `run_steps_ed5/common_ed5.ps1`의 `$ToolCommit` 줄
- 참고: 새 출력 폴더는 이미 `-text` 보호를 받는다. `12b_decide_e8_a1/decision.json`, `12b_vbk_a1/judge/judge.json`, `FIXED_INPUTS_74a4bbf4.SHA256SUMS`의 check-attr 값이 모두 unset이다. 그러므로 `.gitattributes`를 고칠 필요가 없다.

[실행 전 수정][I] W-2. `ed5-tool8` worktree가 잠겨 있지 않다
- 근거
  - `git worktree list --porcelain`: `ed5-tool8`은 74a4bbf4이고 locked 표시가 없다.
  - `Assert-ToolCheckout`(common_ed5.ps1:346-355)는 HEAD가 `$ToolCommit`이고 작업 트리가 깨끗해야 한다. 아니면 종료 3이다.
  - 프로젝트 CLAUDE.md: "판정 실행에 쓰는 고정 checkout은 `git worktree lock`"
- 실패 시나리오: 누가 이 브랜치에 커밋하거나 체크아웃을 바꾸면 모든 판정 명령이 종료 3으로 멈춘다.
- 권장 조치(메인): 병합 뒤 `git worktree lock --reason "436.9 ed5 erratum 8 tool commit 74a4bbf4" .claude/worktrees/ed5-tool8`. 브랜치는 지우지 않는다.

[실행 전 수정][R] W-3. "메인이 해시를 덧붙임으로 고정"(8-9:229)의 기록 위치가 정해지지 않았다
- 근거
  - 재감사 원문 180행·최종 감사 105행은 "도구 커밋 해시와 그 덧붙임"을 재개 직전 감사 입력으로 적었다.
  - 지금 해시를 고정하는 곳은 `common_ed5.ps1:312` `$ToolCommit` 한 줄뿐이다.
  - 주의: 덧붙임을 `run_steps_ed5/` 아래 파일(예: `fixed_inputs_entries_e8.txt`)에 넣으면 막힌다. `Assert-ToolScripts`(367-385행)는 `$ToolCommit` 줄 밖의 차이에서 종료 3으로 멈춘다.
- 권장 조치(메인): `00_docs/decision_log.md`(M 허용)에 한 줄을 남긴다.
  - 내용: "정오 8 도구 커밋 = 74a4bbf4a27fc119d0116f8b67bfe40ee168cadc. 코드는 c895bb72, 시험 보강은 d4162add, 74a4bbf4는 06_analysis에 A만 더함. ff-only 병합"
  - `$ToolCommit` 채움 커밋과 같은 커밋에 넣는다.

[실행 전 수정][T] W-4. python-expert가 판정 대상 단계를 미리 실행했다. 공개가 필요하다
- 근거
  - scratchpad `python-ed5tool8\dry_decision.json`의 수정 시각은 14:19:57이다. 이는 c895bb72 커밋(14:27:01) 전이므로 커밋되지 않은 코드로 실제 b1·b2 VBK0에 decide를 돌린 것이다.
  - 출력에는 decided 꼴 키(`blocks`·`blocks_used`·`allow_k`)가 있다(key_presence 20/20).
  - VBK 파일은 열지 않았다. decide는 VBK 인자를 받지 않는다.
  - smoke(`smoke2`)는 74a4bbf4 기준으로 돌렸다.
- 판단: VBK0만 쓰는 결정이고, 실제 단계 `12b_decide_e8`가 같은 입력으로 다시 계산한다. 그래서 판정 오염은 아니다. 그러나 메모리의 "공개하지 않은 smoke 실행" 함정에 해당한다.
- 권장 조치(메인): 12b 판정서나 decision_log에 공개한다. 실행 시각, 커밋 전 코드라는 점, VBK0만 썼다는 점, 출력 위치를 적는다. 판정 근거로 쓰지 않으면 scratchpad 파일은 옮기지 않아도 된다.

[기록][R] R-1. 목록 생성 스크립트 주석이 실행 위치와 다르다
- 근거
  - `prelaunch_ed5.ps1:126-131` `list_e8` 주석은 "tool checkout의 jp3_fixed_inputs_list.py"라고 적었다.
  - 그러나 53행 `Set-Location $Worktree` 뒤에 상대 경로 `"$Coupled/jp3_fixed_inputs_list.py"`로 부른다. 그래서 실제로는 ed5-run5(606f8713)의 사본이 돈다.
- 영향: 없다. 이 파일은 diff에 없어 blob이 같고, `jp3_fixed_inputs_list.py:183`이 `--worktree $ToolWorktree --commit $ToolCommit`로 도구 checkout의 HEAD와 깨끗함을 확인한다.
- 권장: 다음 손질 때 주석을 고친다(python-expert, 급하지 않음).

[기록][E] R-2. `ready_rule.verdict`에 세 번째 값 `not_judgeable`이 있다(확인 필요 5: 허용)
- 근거
  - `jp3_12b_judge.py:751-752`: 기회 짝이 0이면 `not_judgeable`
  - 1417-1418행: 같은 조건에서 `problems.not_judgeable`에 사유를 더하므로 상태는 종료 2다.
  - 정오 8 8-8.2 표는 `pass`/`failed`만 적었다.
  - 2-9.6 관문 `Get-E8ReadyRuleStop`(e8_gates:170)은 `pass`가 아니면 멈춘다.
- 판단: 빈 집합이 통과하는 길을 막는 쪽이고, 규칙(원판 "판정 행 0 = 판정 불가")과 같은 뜻이다. 판정서에 세 번째 값의 뜻을 적는다.

[기록][R] R-3. b4 기대값 인자를 거부한다(확인 필요 8: 허용)
- 근거
  - 정오 8:172 "b4 VBK0는 … 기록만 한다"
  - `jp3_12b_judge.py:1344-1346`: b4 기대값을 주면 문제로 잡아 종료 2
  - 실행 스크립트는 b1·b2 기대값만 넘긴다(common_ed5.ps1:318-323, 492-495).
  - b4의 sha와 T4h 요약은 `input_record`에 기록된다.
- 판단: 막는 쪽 해석이고 판정에 영향이 없다.

[기록][I] R-4. 두 목록 운용 (a″)(확인 필요 4: 허용)
- 정오 8:232가 요구한 7종이 `fixed_inputs_entries_e8.txt`에 모두 있다.
  - 정오 8·경로 2 정오와 각 `.sha256`
  - VBK0 b1·b2 json
  - 근거 SUMS 넷
- `FIXED_INPUTS_606f8713`도 목록 항목으로 연결된다.
- 옛 목록 확인
  - 코드 경로가 없다(04_scripts·05_tests·03_src 0줄).
  - `run_steps_ed5/` 줄은 `Get-E8FixedListStop`(e8_gates:281-307)이 새 목록에서 다시 대조한다.
  - `baseline_check sums --base repo-root`로 254항목 mismatch 0, missing 0.
- `fixed_inputs_entries.txt`는 고치지 않고 새 파일을 둔 것은 8-12 "갱신" 문구와 다르다. 다만 8-9 (a″)가 연결 방식을 python-expert에 맡겼고, 옛 목록을 바꾸지 않으므로 더 보수적이다.
- 코드 경로를 목록에서 뺀 것도 문제 없다
  - 도구 checkout에서 `jp3_12b_judge.py`는 `w/crlf`(text 미지정)라 작업 트리 sha가 blob과 다르다.
  - 그래서 HEAD와 깨끗함 확인(`Assert-ToolCheckout`)으로 대신한 것은 타당하다.
  - 실행에 쓰는 ps1은 모두 `-text`·LF이고 sha로 목록에 들어간다.
- 옛 목록에는 원래부터 추적되지 않은 인용 파일이 있다. 새 목록 `h8_noise_VB.json`에도 같은 사정이 이어진다. 로컬 sha로는 대조된다.
  - 추적 안 됨 4: `resume_k1/h10_reuse_rerun.jsonl`, `h6_dg3_v4on.json`, `h8_noise_VB.json`, `h9_grid/grid_r67_top.json`
  - `.git/info/exclude`에 걸림 4: `l1ref_a1/L1_VBJ.json`, `78fd5d2d/dg3_a1/dg3_VBH.json`·`dg3_VBJ.json`, `v5/main.jsonl`

[기록][I] R-5. 실행 스크립트 일치 확인 `Assert-ToolScripts`의 범위(확인 필요 3: 규칙대로)
- 메인 checkout의 `run_steps_ed5`를 도구 커밋과 `git diff`로 비교한다. `common_ed5.ps1`의 `$ToolCommit` 줄 두 개(−/+)만 허용한다.
- 정오 8 (f) 표 "실행 스크립트 커밋 = 도구 커밋(목록 커밋 포함)"과 맞다.
- 한계: `git diff`는 추적되지 않은 새 파일을 보지 못한다. 그런 `.ps1`이 `list_e8` 생성 때 있으면 글롭 `run_steps_ed5/*.ps1`로 새 목록에 들어간다.
- 권장: 목록을 만들기 전에 `git status --porcelain -- …/run_steps_ed5`가 비어 있는지 본다(병합 뒤 항목 4).

[기록][R] R-6. 종료 코드 배정(확인 필요 7: 허용)
- 배정
  - (a) diff 위반, 도구 checkout HEAD·깨끗함, 폐포 meets: 3
  - (c) 환경 변수·`--workers`·identity 불일치, 결정 기록 상태: 2
  - 폐포 도구 `tool:e8_tool_closure`: `$RecordCodeTools`(common_ed5.ps1:97)
- 정오 8 8-9는 "멈춘다"만 정하고 종료 코드는 정하지 않았다. 두 값 모두 판정 실패(1)가 아니다.
- 폐포 도구를 `RecordCodeTools`에 넣었으므로 `Read-PreviousStops`가 재시도를 거부하지 않는다. 그래서 일관된다.
- 단계 머리 주석에 표가 있다. 판정서에는 "정체성 위반 3, 실행 조건·결정 기록 2"로 적는다.

[기록][R] R-7. `step6b_vbk0.ps1`을 b4 전용으로 바꿨다(확인 필요 6: 허용)
- 근거
  - `-Phase base`·`b3`는 표지를 쓰지 않고 종료 2로 끝난다(16-20행).
  - b4는 단계 이름이 `12b_vbk0_b4`이고 출력은 `VBK0_b4.json`·`VBK0_b4_t4h`다. 정오 8 8-9 3과 같다.
  - `run_steps_ed5/` 아래 M이므로 (a)상 허용된다.

[기록][I] R-8. step7b 판정 도구가 바뀐 판정 도구의 함수를 import한다
- `jp3_ckdrop_record.py`는 blob이 같지만 바뀐 `jp3_12b_judge.py`를 import한다.
- 실제로 쓰는 함수는 `fault_pairs`·`phase_fault_pairs` 둘이다. 이 둘은 diff 덩어리 밖이다.
- step7b 주석(10-13행)은 `ready_time`도 쓴다고 적었지만 실제로는 쓰지 않는다.
- 정오 8 (f) "같은 blob" 조건은 만족한다. 판정서에 "import한 함수는 바뀌지 않음"을 적는다.

[기록][E] R-9. `placeholder_scan --pattern-set both`가 종료 1이다. 모두 주석 안의 설명용 꺾쇠다
- 53건 모두 주석의 설명용 표기다(`<k>`, `<tool commit 8>`, `<code>` 등).
- 주석이 아닌 줄의 꺾쇠 자리는 `common_ed5.ps1:312 '<ED5_TOOL_COMMIT>'` 하나다(Grep `^\s*[^#\s][^#]*<…>`).
- `ps1_lint --allow ED5_TOOL_COMMIT`은 종료 0이다(21파일, AST).

## 규칙↔도구 대조표

| 규칙(정오 8) | 도구·스크립트 | 판단 |
|---|---|---|
| 8-8.1 A/A 기록 `aa_floor`{pairs, counted_pairs, counted, rule, is_stop false}, `stop_at` 없음 | judge.py:482-500, 549 | 같음 |
| 8-8.1 b3 필요·b3 입력 → not_judgeable, 사유 문구 | :558-562, B3_REASON:150 | 같음 |
| 8-8.1 decided면 `blocks`=`blocks_used`, `allow_k` 7/9 | :588-589, ALLOW_K_BY_BLOCKS:147 | 같음 |
| 8-8.1·8-9 (d) 기대값 필수, 불일치·누락 → 상태·사유·입력 sha만 | :1330-1374. 음성 건식 출력의 키는 {exit, inputs, reason, rule, status} | 같음 |
| 8-8.1 `aa_floor_stop` 폐지, 옛 기록 거부 | EXIT_OF_STATUS:1450. `load_decision`은 decided만 받는다(:961) | 같음 |
| 8-8.2 W-5 네 조건 | :923-943, 스크립트 e8_gates:93-118 | 같음 |
| 8-2 READY 상실·지연(round 1e-6, `>` 30) | :722-729. 재계산: 130.000001 → 30.000001 셈, 130.0·130.0000004 → 30.0 안 셈 | 같음 |
| 8-2 n23은 쓴 블록 합, 7 / 9 | :740-763 | 같음 |
| 8-2 VBK0 미도달 짝은 n23 밖 | :699-700, 746 | 같음 |
| 8-3 교착 서명 네 조건, 소문자, 20 s − 1e-6, < 1 mm 네 다리 | :817-840 | 같음 |
| 8-6 `n_vbk0_worse_loss`·`_plus30`(두 쪽 READY) | :803-814 | 같음 |
| 8-6 `by_cell`(0-7 + TRw)·`by_block` | :787-800. selection의 cell 값은 정수(21952행~) | 같음 |
| 8-8.2 기록 항목 예외 → computed false, 상태 불변 | :878-899 | 같음 |
| 8-8.2 `n_fault_judged` = 기회 + VBK0 미도달 | :693-694, 719 | 같음 |
| 2-10 상태 순서 실패 > 결함 > 판정 불가 > 통과 | :205-215 | 같음 |
| 8-9 (a) 허용 경로 | e8_gates:61-91. 시험 파일 패턴이 `test_jp3_12b*`로 더 좁다 | 같음(더 엄격) |
| 8-9 (b) `pre_las_preset_runner.py` 불변, 공용 `run_steps/` 불변 | e8_gates:64-65. diff 실측 0줄 | 같음 |
| 8-9 폐포 검사 | common_ed5:424-434. 직접 실행: disjoint, 225파일 중 만나는 것 0 | 같음 |
| 8-9 (a′) 판정 명령은 도구 checkout, HEAD·깨끗함 기록 | common_ed5:451-470. step6b/6c/7/7b/8의 판정 명령 모두 Invoke-ToolJudge | 같음 |
| 8-9 (c) 허용 차이(PLAN·T4H_DIR·SETTING, mask), workers 4, identity 6필드 | e8_gates:192-261, common_ed5:509-530 | 같음 |
| 8-9 (d) 8-1.3 고정값 | common_ed5:318-323. 재계산: b1·b2 run sha와 T4h 요약 모두 일치(167/167 파일) | 같음 |
| 8-9 (e) base_a1 stop(종료 2)만 받음 | e8_gates:136-159. 실측: 표지 1개, a1, exit_code 2, done 없음 | 같음 |
| 8-9 (f)·3·4 b4 사슬, `12b_decide_e8_b4.done` 우선 | step6b_decide_e8(_b4).ps1, step6b_vbk0.ps1, step6c:19-29, e8_gates:120-134 | 같음 |
| 2-9.6(8-10) `ready_rule` 대조 | step8:52-53, e8_gates:161-178 | 같음 |
| 8-8.3 시험 1~14 | test_e8_01~14, junit 150 통과·skip 0 | 같음 |

## 확인 필요
- W-3: 덧붙임 위치를 decision_log 한 줄로 해도 되는지(메인 결정)

## 위임 필요
- 없음. R-1·R-8 주석 정정은 다음 손질 때 python-expert에 맡긴다(급하지 않음).

## 메인 세션 권고 — 병합 가능 여부와 병합 뒤 확인 항목

**병합 가능**: 차단이 없다. 방법은 `git merge --ff-only ed5-tool8`이다.
- squash·rebase는 쓰지 않는다. 74a4bbf4가 master 이력에 남아야 목록 커밋이 도구 커밋을 포함한다.
- 메인 작업 트리와 부딪히는 파일은 0개다(새로 더할 11개 경로 모두 없음).

**병합 뒤 확인 항목**(메인이 순서대로)
1. master HEAD가 74a4bbf4인지 확인한다. `ed5-tool8`을 lock한다(W-2).
2. `common_ed5.ps1:312`를 `$ToolCommit = '74a4bbf4a27fc119d0116f8b67bfe40ee168cadc'`로 바꾼다.
   - 한 줄만, LF를 유지한다. CRLF가 섞이면 `Assert-ToolScripts`의 정규식이 맞지 않아 종료 3이 된다.
   - 같은 커밋에 decision_log 덧붙임을 넣고 커밋한다(W-3).
   - 확인: `git diff 74a4bbf4 -- …/run_steps_ed5`가 정확히 −1/+1줄이다.
3. `ps1_lint`를 메인 checkout `run_steps_ed5`에 다시 돌린다. 자리표시가 0이고 종료 0이어야 한다.
4. `git status --porcelain -- 06_analysis/02_control/j_p3_cause/prelaunch_j9/run_steps_ed5`가 비어 있는지 본다(R-5). 그 뒤 `prelaunch_ed5.ps1 -Part list_e8`로 `FIXED_INPUTS_74a4bbf4.SHA256SUMS`를 만들고 커밋한다(A).
   - 확인: 추적됨, `git status --ignored` 해당 없음, LF·`-text`
   - 확인: `baseline_check sums --base repo-root` mismatch·missing 0
   - 확인: `FIXED_INPUTS_606f8713` 줄, 정오 8 두 문서와 두 `.sha256`, SUMS 넷, VBK0 b1·b2 json이 있다.
5. `Assert-ToolScripts`와 `Assert-E8FixedLists`를 읽기 전용 smoke로 돌린다. 둘 다 이번 감사에서 실행하지 못했다.
   - 방법: python-expert의 `smoke_tool_checks.ps1`처럼 `Stop-Step`을 바꿔 끼우고, j9_runs에는 쓰지 않는다.
   - `Assert-ToolDiff`(main_head = 목록 커밋)도 다시 돌려 규칙 밖 0을 확인한다.
   - 이 smoke를 건너뛰면 `12b_decide_e8_a1`의 Initialize가 같은 검사를 한다. 실패하면 a1이 `.stop`이 되고 재시도는 a2가 된다.
6. 마지막 단계까지 master 동결을 지킨다(W-1). `.claude/agents/paper-reviewer.md`는 커밋하지 않는다.
7. `12b_decide_e8`(→ 필요하면 `12b_vbk0_b4` → `12b_decide_e8_b4`) → `step6c` 순서로 진행한다. W-4 공개 문장은 판정서 초안에 넣는다.

## 사용자 조치 필요
- 없음

## 검사하지 못한 것
- `Assert-ToolScripts`·`Assert-E8FixedLists`(병합과 목록 생성 뒤에만 가능, 위 항목 5)
- `jp3_fixed_inputs_list.py`의 `list_e8` 실제 실행(출력 파일을 만들므로 하지 않음)
- 단계 스크립트 본문 전체 실행(`Initialize-E8Step`·`Start-Run`·`Wait-Runs`의 연쇄). 단위 시험이 없다(구현자 공백 보고와 같음).
- 판정 도구 시험을 다시 돌리지는 않았다. 커밋된 junit(150/150, skip 0)과 record.json(clean_before·after true)만 확인했다.

## 실행한 검증
- 인터프리터: python-dev `python.exe -I -B`(+ `MKL_THREADING_LAYER=TBB`). 프로젝트 모듈은 import하지 않았다.
- 프로젝트 도구 `jp3_import_closure.py`는 ed5-run5 사본을 python-dev로 정적 실행했다. `--out`은 scratchpad에 두었고, 실행 뒤 ed5-run5는 깨끗했다.
- seal_check 결과
  - 정오 8·경로 2 정오 + `--code` 판정 도구: 종료 0
  - 근거 SUMS 넷 각각 `--sums --rev cd2de978 --check-tracked`: 종료 0, cited_untracked·ignored 0
- baseline_check sums
  - SUMS 넷: 종료 0, sha 4개 모두 정오 8 인용값과 같음
  - FIXED_INPUTS_606f8713(`--base repo-root`): mismatch·missing 0
- ref_check(정오 8, --rev 74a4bbf4): ref_missing 10건이 모두 앞으로 생길 출력이거나 글롭 조각이다(오탐).
- 검사 도구
  - ps1_lint 종료 0
  - placeholder_scan both 종료 1(R-9, 주석 안 표기)
  - key_presence: 건식 decided 출력 20/20 키, 음성 출력은 결정 키 없음 확인
  - junit_skips 종료 0(150, skip·xfail 0)
  - gate_scan 종료 0(info 3, 바뀌지 않은 dry-c의 기본값 1건)
  - log_errors(base_a1/logs) 종료 0
- 독립 스크립트(scratchpad, 이미 지움)
  - diff 허용 규칙 분류(도구 커밋·master HEAD 둘 다 규칙 밖 0)
  - VBK0 b1·b2 sha와 T4h 요약 재계산(8-1.3과 일치)
  - base stop·step_record·identity 구조 확인
- git 조회: worktree 목록, `ls-files --eol`, `check-attr`, 커밋 시각
- 최종 판정 직전 다시 확인: master HEAD b853e107, ed5-tool8 HEAD 74a4bbf4, 깨끗함. 감사 중 바뀐 파일 없음.
- 만든 뒤 지운 것: `<scratchpad>\auditor-ed5tool8\` 전체(스크립트, guard.json, 보고서). 메모리 `audit_pitfalls.md`·`MEMORY.md`에 일반 함정 한 줄을 더했다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v5_erratum8.md 8c420e85…, jp3_remedy_spec_v5_erratum8.md.sha256 a95fc2fe…, jp3_rev6_p2_handoff_ed5_e8.md ef33e619…, jp3_rev6_p2_handoff_ed5_e8.md.sha256 95b2b3a4…, SHA256SUMS e387907e…, SHA256SUMS 8b906fb9…, SHA256SUMS b00eb95a…, SHA256SUMS 1247a9ee…, jp3_12b_judge.py 273d1ed9…, test_jp3_12b_erratum8.py 12ed785d…, test_jp3_12b_tools.py 1e1da9b7…, dry_decision.json 9c33f420…, dry_decision_bad.json ca4b697d…, common_ed5.ps1 816ad2f0…, e8_gates_ed5.ps1 ed6f9e2a…, fixed_inputs_entries_e8.txt b7085a65…, fixed_inputs_entries.txt 4ea25cc7…, prelaunch_ed5.ps1 fa41a6f5…, record_gates_ed5.ps1 d00d52fc…, step_l1ref.ps1 935d019e…, step_p5fixed.ps1 4f7ece36…, step0_cdry.ps1 910446ca…, step1_p1.ps1 f933ec19…, step2_dry.ps1 53a49b6d…, step3_fpath.ps1 b30111dc…, step4a_cases.ps1 cc6c6df4…, step4b_casef.ps1 c43283b6…, step5_t8.ps1 c13a193d…, step6_dg3.ps1 31e0634e…, step6b_decide_e8_b4.ps1 4fd95d81…, step6b_decide_e8.ps1 60749a15…, step6b_vbk0.ps1 80e7c7d3…, step6c_vbk.ps1 0cdbab7e…, step7_records.ps1 137de23a…, step7b_ckdrop.ps1 dc497b12…, step8_j9main.ps1 fb077000…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
- 참고: 초기에 Bash 파이프(`| head`, `| sed`)를 세 번 썼다. 공통 실행 규칙 위반이다. 모두 즉시 끝났고 남은 프로세스는 없다.
