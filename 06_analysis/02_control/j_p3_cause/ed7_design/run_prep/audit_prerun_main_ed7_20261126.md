# 436.9 J-P3 판 7 본 실행 직전 감사 (verif-protocol-auditor, 2026-11-26)

## 감사 요약
- 본 결과: 판 7 실행 출력은 없다(`j9_runs\8a2a52ce` 없음, 감사 전후 두 번 확인). 판정 대상 결과 값은 보지 않았다. 다음은 볼 수밖에 없었던 것이다.
  - M-c 건식 확인 `ed7_design\dry_mc_8a2a52ce\judge\dry_mc_summary.json`에서 Grep에 걸린 줄 몇 개(l1ref stand-in의 상태 단어와 키 이름, 건식 기록)
  - 건식 로그 3개의 `errors N` 줄 유무와 개수(log_errors)
  - 판 6 커밋 bdb3739d의 `--stat`(파일 이름·줄 수)
- 대상: 판 7 본 실행 연쇄 러너 `C:\Users\jinbeom\.claude\runners\outrigger-ed7-run\run_ed7_chain.ps1`(sha256 `bc83c834…`, 감사 전후 같음). 함께 본 것:
  - C(8a2a52ce)의 run steps `run_steps_ed7\*.ps1`와 dot-source되는 `run_steps\common.ps1`
  - `pre10a_c92c93_check.ps1`, 실행 설정 `prelaunch_j9\ed7_run_config.json`(sha256 `9ede99fb…`)
  - T′(60ebb4a4)의 판정 CLI `jp3_ed7_judge.py`
- 시점: 실행 전.
- 기준 문서
  - 봉인 명세 `jp3_remedy_spec_v7.md`: sha256 `10902ffd…`. 실측 = `.sha256` 첫 토큰, `i/lf w/lf attr/-text`.
  - 정오 1 `jp3_remedy_spec_v7_erratum1.md`: sha256 `74c49bda…`. 실측 = `.sha256`, 커밋 265dc641(2026-11-26T00:14:27+09:00).
  - 이어받은 판 6 명세 4절(`jp3_remedy_spec_v6.md` 320~401행).
- **판정: 차단 0 / 실행 전 수정 2 / 기록 10. 본 실행 가능.** 조건은 M-1이다. 사용자가 정한 띄우기 명령 `-PauseAfter probe,confirm`은 `pwsh -File`로는 받아들여지지 않으므로, 띄우는 명령만 고쳐서 띄운다. 러너·C·T′ 코드는 고칠 필요가 없다.

## 발견 사항 (심각도순)

### [실행 전 수정][R·I] M-1 `pwsh -File … -PauseAfter probe,confirm`은 매개변수 검증에서 거부되고 아무 단계도 시작하지 않는다
- 근거
  - 러너 88~89행은 `[ValidateSet(...)][string[]]$PauseAfter`다. `-File`로 부르면 `probe,confirm`이 배열로 풀리지 않고 문자열 하나로 묶인다.
  - 실측: `pwsh -NoProfile -File run_ed7_chain.ps1 -DryRun -PauseAfter probe,confirm`은 ValidateSet 거부(`인수 "probe,confirm"은(는) ValidateSet 특성에 지정된 집합 … 에 속하지 않습니다`)로 **종료 1**이었다. 잠금·로그·progress는 생기지 않았다.
  - 비교 실측
    - `-PauseAfter probe` 하나만 주면 종료 0이고, probe에 `pause` 줄이 붙는다.
    - `-Command "& '<러너>' -DryRun -PauseAfter probe,confirm; exit $LASTEXITCODE"`는 종료 0이고, probe·confirm 두 곳에 `pause` 줄이 붙는다.
  - 준비 보고 `handback_chain_runner.md` 74행의 예시 명령(`-File … -PauseAfter probe,confirm`)도 같은 결함을 가진다.
- 실패 시나리오: WMI로 그대로 띄우면 창이 곧바로 닫히고 아무것도 돌지 않는다. 안전 쪽 실패라 판정이 틀어지지는 않지만, 메인이 "시작했다"고 오인할 수 있다. 종료 1은 러너 표의 "멈춤"과 같은 번호다.
- 권장 조치(메인, 코드 변경 없음). 셋 다 `-File` 그대로, 값은 하나씩 준다.
  1. 첫 실행: `"<pwsh>" -NoProfile -File "…\run_ed7_chain.ps1" -PauseAfter probe`
  2. probe 판정 뒤: `… -File "…\run_ed7_chain.ps1" -StartAt confirm -PauseAfter confirm`(건식 파싱 확인: ValidateSet 통과)
  3. confirm 판정 뒤: `… -File "…\run_ed7_chain.ps1" -StartAt j9main`
  - 또는 `-Command` 형식을 쓴다(위 실측). 다만 WMI 따옴표가 복잡하므로 1~3을 권한다.
  - 띄우기 전에 같은 인자로 `-DryRun`을 한 번 돌려 `pause` 줄 위치를 확인한다.

### [실행 전 수정][E] M-2 run_v5 단계(t8·cases·confirm G1·j9main·sens)의 오류 줄은 러너 검사를 모두 통과한다. log_errors 관문이 이 단계들에서는 공허하다
- 근거
  - `run_v5.py` 865~867행: 줄이 실패하면 `error` 줄을 쓰고 배치는 계속된다. `_run_pool` 1087~1098행은 `{count}/{N} {job}: {state}`만 찍고 `errors N` 줄을 찍지 않으며, 종료 코드는 0이다.
  - 러너 496~510행은 `log_errors.py <폴더>\logs`를 돌린다. 패턴은 `\berrors\s*[:=]?\s*(\d+)\b`(log_errors.py 50행)이고, 맞는 줄이 없으면 `no_errors_line` info로 종료 0이다(12~13행).
  - 실측(M-c 건식 로그 `dry_mc_8a2a52ce\runs\logs`)
    - `ed7_t8.log`(run_v5)는 `no_errors_line`이다.
    - r79 로그 `L1_VBM`·`L1_VBM0`은 `errors` 줄이 있다(`r79_L3L4_final.py` 295·392행이 오류 줄 수를 찍는다).
  - 덮이는 단계
    - probe와 D 24줄: `ed7_probe.py` 294~296행이 오류 줄이 있으면 0이 아닌 값으로 끝나 Wait-Runs가 멈춘다.
    - l1ref·dg3·12b(r79): `errors N`이 찍힌다.
  - 덮이지 않는 단계: t8·cases·confirm G1·j9main·sens(run_v5).
  - 판정 쪽은 오류 줄을 통과로 읽지 않는다(실패를 숨기지 않으므로 차단은 아님).
    - `jp3_ed6_judge._rows_by_job` 876~877행: 오류 줄 → `not_judgeable`. t8·cases·probe-repro가 이 함수를 쓴다.
    - `jp3_j9main_judge.py` 215~217행: 오류 줄 → 문제 목록.
    - sens는 확인하지 않았다([추정] 같은 처리).
- 실패 시나리오: j9main이나 sens에 오류 줄이 생겨도 `.done`이 써진다. 그 뒤 정지 지점이 없으므로 dg3·12b_plan·12b_vbkm0가 이어서 돈다.
  - 판정에서야 `not_judgeable`이 나온다.
  - 그때 그 단계는 `.done`이 있어 run steps가 재시도를 거부한다(`common.ps1` 221행 "done already … results seen"). 정오 없이는 다시 돌릴 수 없다.
- 권장 조치(메인, 코드 변경 없음)
  - (a) 정지 지점마다 판정 전에 오류 줄을 값 없이 확인한다. 아래 명령이 종료 0이어야 한다(오류 줄에는 `commands_sha256`이 없다, run_v5.py 838·866행).
    - probe 정지 때: `key_presence.py <impl_t8_a1\ed7_t8.jsonl> <impl_cases_a1\ed7_cases.jsonl> --key commands_sha256`
    - confirm 정지 때: `<confirm_a1\confirm_g1.jsonl>`에 같은 명령
  - (b) j9main·sens는 확인 필요 1의 정지 지점 추가를 함께 판단한다(`-StartAt j9main -PauseAfter sens`로 띄우면 dg3 전에 (a)를 할 수 있다).
  - 러너에 이 검사를 넣으려면 python-expert에 위임한다. 러너 sha가 바뀌므로 재감사가 필요하다. 지금은 메인 절차로 충분하다.

### [기록][R] R-1 l1ref 뒤 관문 없음은 정오 1-2·1-10과 맞다. 다만 고정 방식이 판 6보다 약하다
- 근거
  - 정오 1-2 53행: "판 7은 목록 파일 대신 단계별 단언으로 하므로, 아래 표가 판 7 데이터 입력 목록이다."
  - 정오 1-2 67행: L1 기준 4개는 "2번째 단계 기록 | T(조건 2)"다.
  - 정오 1-10 147행: 메인이 `.done` 직후 SUMS를 만들고 판정 직전에 대조한다.
  - 판 6은 l1ref 뒤 L1 출력과 `FIXED_INPUTS_79495405.SHA256SUMS`를 git에 커밋했다(bdb3739d "fixed input list after l1ref (step 5 gate)", 9파일).
  - 판 7은 단계 폴더 안 SUMS로 고정한다. 그 SUMS는 git 미추적이고, `main_checks\sums_write_*.md` 보고서도 미추적이다.
- 판단: 판 6 목록 커밋을 1-2가 문장으로 대체했다. 러너의 "관문 없음"은 맞다.
- 선택 권고: probe 정지 때 l1ref 출력(json·identity·step_record, npz는 `.gitignore:41 *.npz`라 판 6처럼 `LOCAL_ONLY.SHA256SUMS`)을 master에 커밋하면 판 6과 같은 git 고정이 된다.
  - 안전성: master 커밋은 실행 단계 정체성(ed7-impl HEAD), pre10a(c92·c93 blob만), T′ `code_identity`(ed7-judge) 어디에도 걸리지 않는다.
  - ed7-impl에는 아무것도 쓰지 않는다.

### [기록][I] R-2 일시 정지 경로는 끝 정체성 실패를 멈춤으로 바꾸지 않는다
- 근거: 러너 528~533행. `Test-RunIdentity 'end'` 결과로는 `done`만 `stop`으로 바뀌고, `pause`는 `[identity] … entries=N` 줄만 남긴다.
- 영향: 다음 `-StartAt`의 시작 정체성 검사(627~629행)가 거부(종료 2)하므로 다음 단계로 새지는 않는다.
- 조치: 정지 때 메인이 `[identity] end check_ed7 exit=0, worktree status entries=0` 줄을 확인한다.

### [기록][E] R-3 E축 질문 답(빈·0건 처리)
- logs 폴더가 없거나 `.log`가 0개: run이 있는 단계면 `[stop]`(505행). scope만 건너뛴다(501~503행). log_errors 자신도 로그 0개면 종료 2다.
- key_presence 대상 폴더가 없거나 npz가 0개: 도구 종료 2(key_presence.py 33~34행) → 러너 `[pause]`(490~492행). 통과가 아니다.
- `.done`
  - 없음: `[stop]`(249행)
  - JSON 깨짐: 예외 → `[stop] internal error`, 종료 3(639~641행)
  - `exit_code`나 `commit` 키 없음: `$null -ne 0` → 멈춤
- 종료 코드 미확보(-1): `[stop]`(225·466행).
- 새 `.stop*`: 시작 1초 전 이후 것을 본다(449·269~274행). 앞 시도의 표지와 섞이지 않는다.
- 종료 3 경로는 `progress.json`을 갱신하지 않는다(갱신은 Exit-Chain에만 있다). 주기 점검은 progress가 아니라 chain log의 `[stop]`을 먼저 grep한다.

### [기록][I] R-4 실행 설정 `ed7_run_config.json`은 미추적이다
- 상태: `git ls-files --error-unmatch` 실패, ignore 아님, `-text`.
- 모든 단계가 `run_commit`·`worktree`를 이 파일에서 읽는다(common_ed7.ps1 76·95~99행). step record에는 이 파일의 sha가 없다.
- 판정서에 sha256 `9ede99fb…`를 인용하거나, 본 실행 전 run_prep 보고와 함께 커밋한다.

### [기록][I] R-5 마스크·worker·attempt·출력 경로는 설정·배치와 같다. P+E 혼합은 기록된다
- placement 6단계: 러너 121행 `-MaskHex 0x0FFFFFFF -Workers 20` = 설정 `placement` 38~43행.
  - cases는 min(10,20)이다(step5 55행).
  - confirm D는 min(24,20)이다(step6 23행).
- C 고정 마스크(설정 44~50행과 대조)
  - l1ref: 0x000F/0x00F0/0x0F00/0xF000(step_l1ref 17행)
  - dg3: 0x00FF/0xFF00(step9 11행)
  - 12b base: 0x000F/0x00F0(step10b 15행)
- 러너 예약 마스크는 각 단계 마스크의 합집합이다(l1ref·dg3 0xFFFF, 12b 0x00FF).
- attempt는 `STEP_a<N>`의 마지막 + 1(259~267행)이다. 출력은 각 단계 스크립트가 `RunsRoot\STEP_aN\`에 쓰고, 이미 있으면 거부한다(Assert-NewOutput, Initialize-Step 224행).
- 혼합 기록
  - `core_kind_ed7.ps1` 24~34행의 `mixed`가 step record `core:<label>`에 남는다(common_ed7 246행).
  - `record.py`는 `--core mixed`를 받는다(record.py 306~307행).
- 정체성 검사
  - 러너 시작·끝: `check_ed7.ps1`과 미추적 포함 porcelain 0.
  - 각 단계 시작·끝: HEAD·tracked clean·03_src tree(common_ed7 151~172·193~229행).
  - 단계 끝: `baseline_check identity --mtime`(common.ps1 311~323행).
  - 이 마지막 검사를 건식 출력으로 미리 돌렸다(`dry_mc_8a2a52ce\runs`, `--expect-commit 8a2a52ce… --mtime`): 종료 0, dirty 0이다. 정오 1-5의 mtime 경고 위험은 지금 없다.

### [기록][R] R-6 러너 보고 2절 관문 표 대조: 맞음(M-1·M-2 제외)
- 1단계 전
  - P5-1 기록 `run_record.json` 있음. 폴더 SUMS `baseline_check sums` 종료 0(81항목, 불일치 0).
  - M-c 건식 폴더 SUMS도 종료 0(57항목).
- l1ref·dg3 key_presence → `[pause]`: 정오 1-13(배열 없음 = `setting_defect`)과 맞다.
  - 대상은 ③ 켬 폴더다(L1_VBM_t4h·L1a_VBM_t4h·dg3 VBM_t4h).
  - `--npz-dir` 반복은 누적된다(key_presence.py 635~636행 `action="append"`).
- pre10a: 정오 1-2 조건 1과 맞다. 0이 아니면 `[stop]`(441행). `-StartAt 12b_plan`이면 pre10a부터 돈다(281~285행).
- 12b_vbkm0 base 뒤 끝: 정오 1-1·1-3과 맞다.
- 표에 없는 것: M-2(log_errors 공허), 확인 필요 1(j9main 뒤 정지 없음의 결과).

### [기록][R] R-7 `-PauseAfter probe`, `confirm`이면 P7 관문이 다음 단계보다 먼저 판정된다
- 러너 636행: 단계 검사(sums·logs·T4h) 통과 뒤 `Exit-Chain 'pause' 4`. 그 뒤에야 다음 단계가 뜬다.
- probe 정지 시점에는 4절 5의 실행(t8·cases·probe)이 모두 끝나 있다. P7-1·P7-2·P7-3·P7-9 판정은 확인 단계(6) 실행 전에 할 수 있다.
- t8·cases 판정이 probe 실행 뒤로 밀리는 것은 명세 4절 5("C에서 실행만 하고 판정은 T와 그 감사 뒤")·5a와 맞다.

### [기록][S·T] R-8 봉인·시간 순서
- `seal_check`(명세·정오, `--const jp3_ed7_judge.py:SPEC_V7_SHA256`, `--sums postseal\SHA256SUMS judge_commit_60ebb4a4\SHA256SUMS`, `--check-tracked --rev 265dc641`): 종료 0, findings 0, cited 32, untracked 0, ignored 0.
- 커밋 시각: 봉인 e241638d 11-25 15:25 → C 16:33 → T 17:20 → T′ 19:05 → 정오 1 11-26 00:14. 실행 출력은 없다. 정오 1-19(T′·감사가 실행 출력보다 먼저)를 만족한다.
- 작업본 상태
  - 메인 HEAD = 265dc641
  - ed7-impl HEAD = C, status 0항목
  - ed7-judge HEAD = T′, status 0항목
  - 둘 다 lock(`worktree_locks` 종료 0. info 1 `lock_reason_other_commits`는 계보 토큰이라 정상)
- 실행 출력 경로 속성: `j9_runs/8a2a52ce/**`의 json·jsonl·SUMS·`.done`·판정 report·chain log는 `text: unset`(-text)이고 ignore가 아니다. npz는 `.gitignore:41`이다.

### [기록] R-9 도구 종료 코드 요약

| 도구 | 종료 | 비고 |
|---|---|---|
| `ps1_lint` run_steps_ed7 14 + common + record_helper(16파일) | 0 | 발견 0 |
| `ps1_lint` 러너 + pre10a | 0 | info 9: 주석 `<N>` 7, 주석 `-NoExit` 1, `tee_captured_with_return` 1(Tee가 `\| Out-Host`로 끝나 거짓 양성, 218~219행) |
| `placeholder_scan --pattern-set both` 설정 | 0 | unfilled 0 |
| 같은 도구, run_steps(16파일) | 0 | unfilled 0 |
| 같은 도구, 러너·pre10a·resource json | 1 | unfilled 30. 모두 `run_ed7_chain.ps1`의 주석(37~83·181·260행)과 건식 출력 문자열(575·578행 `<runner PID>`·`<lease id>`)이다. 실행 명령에 남은 자리표시는 0이다(거짓 양성) |
| `worktree_locks --worktree ed7-impl ed7-judge` | 0 | — |
| `check_ed7.ps1` | 0 | `CHECK ok: 8a2a52ce…, parent b46bdf8f…, 03_src 0cffdbdf…` |
| 러너 `-DryRun -PauseAfter probe` | 0 | 쓰기 없음(`j9_runs\8a2a52ce`·progress·lock 없음, ed7-impl status 0) |
| 러너 `-DryRun -PauseAfter probe,confirm` | 1 | M-1 |
| `ref_check` 정오 1 | 1 | missing 13, untracked 5. 아래 설명 |
| `ref_check` 명세 | 1 | missing 18, untracked 1. 아래 설명 |
| `run_hazards --check update` | 0 | Low 1 `pending_file_rename`, 일시 정지 남은 시간 621.7 h |

- `ref_check` 결과
  - 제외 옵션 `--exclude` 블라인드 3 + `.claude` + 판 6 selection.json을 붙였다.
  - missing은 C·T′ 브랜치에만 있는 파일이다. `git cat-file -e`로 10개를 확인했다(예: `8a2a52ce:…/run_steps_ed7/step10a_plan_ed7.ps1`, `60ebb4a4:…/jp3_ed7_judge.py`, `60ebb4a4:05_tests/data/ed7_run_path_modules_8a2a52ce.json`). C는 master 조상이 아니다.
  - 나머지 missing은 설명용 이름(`VBK_c93.json` 등 봉인문 안의 블라인드 파일 이름, 글롭)이다.
  - D 키 파일은 git blob `3ecf61f1:…/d_grid_keys12.json`이 있다.
  - untracked는 sha로 고정된 기존 입력(h6·h8·probe jsonl·p51 기록·판 6 L1)이다.
  - 실행 입력의 존재는 `check_ed7`(모든 고정 입력 sha 대조)가 보증한다.

### [기록] R-10 기타
- confirm 단계는 배치표 상한이 1,900 s(약 32분)인데 예약이 없다(`handback_placement_ed7.md` 43·58행). 상한이 30분 규칙 경계라 기록만 한다.
- 12b_plan의 `--scan-root 06_analysis`에는 probe·confirm 정지 때 만드는 `judge_60ebb4a4\…` 판정 보고서와 `main_checks\`가 들어간다(사용자 결정: 판정서에 공개).
  - [추정] seed에는 영향이 없다. run_v5 판정 보고서에는 r79 키가 없다. l1ref 판정 보고서의 r79 키는 이미 `l1ref_a<N>` 출력에 있는 키다.
- 러너는 단계 안 EcoQoS를 다루지 않는다(판 6과 같다).

## 규칙↔도구 대조표 (R축)

| 규칙 | 원문 위치 | 러너·run steps | 판단 |
|---|---|---|---|
| 단계 순서 5 → 6 → 7 → 8 → 9 → 10 | 명세 v7 587~589행 | 러너 130~160행: scope, l1ref, t8, cases, probe, confirm, j9main, sens, dg3, pre10a, 12b_plan, 12b_vbkm0. 설정 `step_order` 35행과 같음 | 맞음 |
| l1ref는 12a·12b 출력 전 | 명세 6.4(판 6 6.4)·step_l1ref 2~3·12~15행 | 2번째 단계. dg3·12b 폴더가 있으면 거부 | 맞음 |
| "앞 단계 종료 0 아니면 다음으로 가지 않는다" | 판 6 명세 399행 | 466·633행 `[stop]` | 맞음 |
| "판정 실패(종료 1)는 멈추고 묻는다, 재실행 안 함" | 판 6 명세 400행 | 판정은 러너 밖(T′). 정지는 probe·confirm 뒤만(사용자 결정). 자동 재실행 없음 | 확인 필요 1 |
| 실행은 T 전에도 가능, 판정은 T와 감사 뒤 | 명세 588·652행 | 러너는 판정하지 않음(3~4행) | 맞음 |
| 출력 경로는 새 경로, 있으면 거부 | 명세 591행 | Assert-NewOutput(common_ed7 231~236행), Initialize-Step 224행 | 맞음 |
| 12b 계획 = dg3 뒤·12b 앞, 12·13번째는 T 뒤 | 정오 1-1 29·44행 | pre10a → 12b_plan → 12b_vbkm0 base → `[done]`. b4·VBKM은 메인 | 맞음 |
| c92·c93 sha와 HEAD blob을 12b_plan 직전에 | 정오 1-2 조건 1(73행) | pre10a(`git diff --quiet HEAD`, hash-object = `rev-parse HEAD:`) | 맞음 |
| 고정 목록 대신 단계별 단언 | 정오 1-2 47~75행 | l1ref 뒤 관문 없음 | 맞음(R-1) |
| P5-1형 33줄 기록은 본 실행 전, 겹치지 않게 | 정오 1-7 117행 | `run_record.json` 없으면 시작 거부(338~340행) | 맞음 |
| `.done` 직후 SUMS | 정오 1-10 147행 | write-sums `--recursive` → 실패 시 `[stop]`(477~479행) | 맞음. 판정 직전 `sums` 대조는 메인 몫 |
| 첫 l1ref·dg3 출력에서 T4h 조건 배열 확인 | 정오 1-13 165행 | key_presence(T4hDirs) → `[pause]` | 맞음 |
| 판정 `--out`은 T′ worktree 밖·단계 폴더 밖 | 정오 1-18 203행 | 러너는 판정하지 않음. 설정 `judge_out_root` 22~23행 | 맞음(아래 초안) |
| T′·재감사는 실행 출력보다 먼저 | 정오 1-19 206행 | 실행 출력 없음 | 맞음 |

## 판정 명령 초안 (메인 실행용, T′ `jp3_ed7_judge.py`)

공통 준비. dynamics-dev는 직접 실행하고 cwd는 T′ worktree 루트다(도구 docstring 83행). `<…_a1>`은 각 `.done`의 `folder` 값으로 바꾼다(attempt가 2 이상일 수 있다).

```powershell
$env:MKL_THREADING_LAYER = 'TBB'
$env:NUMBA_CACHE_DIR = "$env:TEMP\ed7_judge_numba"    # T′ worktree에 캐시를 남기지 않게
$dpy  = 'C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe'
$main = 'C:\workspace\outrigger_control'
$c    = "$main\06_analysis\02_control\j_p3_cause"
$wtj  = "$main\.claude\worktrees\ed7-judge"
$runs = "$c\j9_runs\8a2a52ce"
$J    = "$runs\judge_60ebb4a4"
$tool = '04_scripts/04_hydraulic/coupled/jp3_ed7_judge.py'
$v0   = "$main\06_analysis\03_hydraulic\coupled\v5\main.jsonl"                     # 9ad74990
$ft   = "$c\ed7_design\fixed_table_b46bdf8f\fixed_table_a2.json"                    # f7754a69
$grid = "$c\ed6_design\keys\confirm_b_grid192.json"                                 # 4e80e69b
function Get-DoneFolder($s) { (Get-Content -Raw "$runs\$s.done" | ConvertFrom-Json).folder }
Set-Location $wtj
```

### probe 정지 뒤(P7-1·P7-2·P7-3·P7-9 + l1ref 정체성)

```powershell
$L  = Get-DoneFolder 'l1ref'; $T8 = Get-DoneFolder 'impl_t8'; $CS = Get-DoneFolder 'impl_cases'; $PR = Get-DoneFolder 'impl_probe'
& $dpy -I -B $tool l1ref --runs "$L\L1_VBM0.json" "$L\L1_VBM.json" "$L\L1a_VBM0.json" "$L\L1a_VBM.json" `
    --step-done "$runs\l1ref.done" --out "$J\l1ref_a1\l1ref.json"; "exit=$LASTEXITCODE"
& $dpy -I -B $tool t8 --rows "$T8\ed7_t8.jsonl" --step-done "$runs\impl_t8.done" --main-jsonl $v0 `
    --out "$J\t8_a1\t8.json"; "exit=$LASTEXITCODE"
& $dpy -I -B $tool cases --rows "$CS\ed7_cases.jsonl" --step-done "$runs\impl_cases.done" `
    --out "$J\cases_a1\cases.json"; "exit=$LASTEXITCODE"
& $dpy -I -B $tool probe-repro --rows "$PR\ed7_probe_a2.jsonl" --step-done "$runs\impl_probe.done" `
    --reference "$c\j9_runs\6bfb2560\ed7_probe_a1\ed7_probe.jsonl" --fixed-table $ft --v0 $v0 `
    --grid-keys $grid --grid-root $main --probe-keys "$c\ed7_design\tool_6bfb2560\keys\probe_keys_ed7.json" `
    --sens-keys "$c\ed7_design\keys_seal_b46bdf8f\sens_keys_ed7.json" `
    --out "$J\probe-repro_a1\probe-repro.json"; "exit=$LASTEXITCODE"
```

- 고정 입력(감사 시점 실측, 도구 `PINNED_SHA256` 151~160행과 같음)
  - 참조 probe `1107b309`
  - 키 `189dbb13`·`be930b75`
  - V0 `9ad74990`
  - D V0 짝 `4e80e69b`
  - 고정 표 `f7754a69`
- `--grid-root`는 docstring 91·96행 `<repo>`대로 메인 checkout 루트다. 틀리면 `not_judgeable`이 나온다(통과로 새지 않음).
- l1ref는 실행 관문이 아니다. 그래도 정오 1-9 조건 3(출처별 값 기록)을 여기서 남기고, 12a·12b 전에 L1 정체성 결함을 드러내려고 함께 돈다.

### confirm 정지 뒤

```powershell
$CF = Get-DoneFolder 'confirm'
& $dpy -I -B $tool confirm --g1-keys "$c\ed7_design\keys_seal_b46bdf8f\confirm_g1_grid171.json" `
    --g1-rows "$CF\confirm_g1.jsonl" --d-rows "$CF\ed7_probe_d.jsonl" --step-done "$runs\confirm.done" `
    --fixed-table $ft --grid-keys $grid --grid-root $main --out "$J\confirm_a1\confirm.json"; "exit=$LASTEXITCODE"
```

## 판정 실행 전·뒤 점검 항목

**전(정지마다)**
1. chain log `main_checks\chain_log\chain_ed7_a<N>.log`를 확인한다.
   - `[pause] <stage> -PauseAfter … checks passed`가 있어야 한다.
   - 그 앞 `[identity] end check_ed7 exit=0, worktree status entries=0`가 있어야 한다(R-2).
   - 해당 단계들의 `.stop*`가 없어야 한다. 있으면 attempt 기록을 판정서에 옮긴다.
2. 정오 1-10: 판정이 읽는 단계마다 `baseline_check.py sums "<단계 폴더>\SHA256SUMS" --no-git --out "$runs\main_checks\sums_check_<단계>_r<N>.md"`가 종료 0이어야 한다. 불일치가 있으면 그 단계는 판정하지 않는다.
   - probe 정지: l1ref·impl_t8·impl_cases·impl_probe
   - confirm 정지: confirm
3. M-2(a): `key_presence.py <run_v5 jsonl…> --key commands_sha256`가 종료 0이어야 한다(오류 줄 0, 값 비출력).
4. T′ 상태: `git -C $wtj rev-parse HEAD` = `60ebb4a4…`, `git -C $wtj status --porcelain` 0항목, `worktree_locks.py --worktree ed7-impl ed7-judge` 종료 0.
5. `--out` 파일이 아직 없어야 한다. 위치는 `judge_60ebb4a4\<하위 명령>_a<N>\`이다(단계 폴더·T′ worktree 밖, 정오 1-18).

**뒤**
1. 종료 코드로 다음 조치를 정한다(도구 docstring 69~81행, 판 6 4절)
   - 0 `pass`: 다음으로 간다.
   - 1 `failed`: 멈추고 사용자에게 묻는다. 재실행하지 않는다.
   - 2 `setting_defect`·`not_judgeable`: 멈추고 원인을 본 뒤 사용자에게 묻는다(P7-9: 재현 불일치 = `setting_defect`, 그 단계 판정 불가).
   - 3 `error`: 도구 오류다. 위임 필요(python-expert)로 올린다. T′을 실행 출력이 있는 상태에서 고치면 정오 1-19 문제가 생기므로 사용자 결정 사항이다.
   - **P7-1·P7-2·P7-3·P7-9 넷이 모두 0일 때만** `-StartAt confirm -PauseAfter confirm`으로 잇는다. confirm은 0일 때만 `-StartAt j9main`으로 잇는다.
2. `git -C $wtj status --porcelain` 0항목인지 본다. report의 `code_identity.head` = 60ebb4a4이고 `is_clean` true인지 본다.
3. 판정이 읽은 단계 폴더의 `sums`를 다시 돌려 종료 0인지 본다(판정이 단계 폴더에 쓰지 않았음).
4. 판정서 옮김용으로 다음을 남긴다.
   - t8 report의 `controller_tags.VBM0`(정오 1-8)
   - l1ref report의 `runs.<stem>.identity_sources`(1-9)
   - 각 report와 `--out` 폴더의 sha256(`write-sums`)
5. 12b_plan 스캔에 판정 report가 들어간다는 사실을 판정서에 공개한다(사용자 결정).

## 확인 필요
1. **j9main·sens 뒤 판정 대기 정지 여부**(M-2·R-7 관련)
   - 사정: 판 6은 단계 안에서 판정해 j9main 판정 실패가 12a·12b 실행을 막았다(판 6 명세 393~400행, `step7_j9main_ed6.ps1`에 판정 호출 있음). 판 7 지금 계획은 confirm 뒤 정지가 없어, j9main·sens 판정 전에 dg3·12b_plan·12b_vbkm0까지 돈다.
   - 명세 5a는 실행 선행을 허용하므로 규칙 위반은 아니다.
   - 대가
     - (i) j9main·sens에 실패나 오류 줄이 있어도 뒤 단계 출력이 생긴다. "본 출력"이 늘어난다.
     - (ii) 이 출력은 다음 판의 12b 스캔 키가 된다.
   - 선택지: `-StartAt j9main -PauseAfter sens`로 띄우고 j9main·sens 판정(또는 최소한 M-2(a) 오류 줄 확인) 뒤 `-StartAt dg3`로 잇는다. 정할 것은 사용자다.
2. **key_presence 정지(l1ref·dg3)가 나왔을 때의 처리**: 정오 1-13은 "배열 없음 = 12a·12b `setting_defect`"만 정했다. 실행을 이어갈지는 정하지 않았다. 정지가 나오면 사용자에게 묻는다(러너 보고 확인 필요 2와 같음).

## 위임 필요
- (선택) python-expert: 러너에 M-2 검사를 넣는 일이다. run_v5 jsonl 단계 뒤 `key_presence.py <rows> --key commands_sha256`를 돌리고, 0이 아니면 `[pause]`로 둔다. 바꾸면 러너 sha가 바뀌므로 재감사 대상이다. 메인 절차(위 점검 3)로 대신할 수 있으므로 본 실행을 막지 않는다.
- tools/verif 후보: `log_errors`에 "패턴 줄이 하나도 없는 로그 폴더"를 warning으로 올리는 옵션(`--require-line`이 있으나 러너가 쓰지 않음). 실제 구현 필요 여부는 python-expert가 판단한다.

## 메인 세션 권고
- 본 실행은 M-1의 세 단계 명령으로 띄운다. 띄우기 전에 같은 인자로 `-DryRun`을 한다. WMI 분리 창, `-NoExit` 없음.
- 띄우기 직전에 `git -C ed7-impl status --porcelain` 0, `Test-Path j9_runs\8a2a52ce` False, `reserve.py prune`을 확인한다.
- 실행 설정 `ed7_run_config.json`(sha `9ede99fb…`)과 `run_prep\` 보고를 본 실행 전에 커밋하거나, sha를 판정서에 적는다(R-4).

## 검사하지 못한 것
- 실제 단계 실행 중 동작: 본 실행을 돌리지 않았다. 러너 제어 흐름은 준비 보고의 리허설 7가지를 근거로만 본다.
- `jp3_ed7_judge.py sens`·`jp3_tjr_judge_ed7.py`·`jp3_12b_judge_ed7.py`의 오류 줄 처리(M-2의 판정 쪽, sens는 [추정]).
- 12a·12b·j9main·sens 판정 명령 초안(요청 범위 밖). 12b decide 형식은 정오 1-3을 따른다.
- `--grid-root`의 정확한 기대값: docstring의 `<repo>`만 확인했고 시험 코드는 보지 않았다.

## 실행한 검증
- 인터프리터: python-dev `C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B`(`MKL_THREADING_LAYER=TBB`). dynamics-dev와 대상 모듈은 import하지 않았다.
- PowerShell 실행
  - `check_ed7.ps1`
  - 러너 `-DryRun` 4회: `-PauseAfter probe,confirm`, `-PauseAfter probe`, `-StartAt confirm -PauseAfter confirm`, `-Command` 형식
- verif 도구
  - `ps1_lint` ×2, `placeholder_scan` ×3, `worktree_locks`, `seal_check`(`--const --sums --check-tracked --rev 265dc641`), `ref_check` ×2(블라인드 제외 5개)
  - `baseline_check sums` ×2(p51 기록·M-c 건식), `baseline_check identity --mtime`(M-c 건식 출력)
  - `log_errors`(M-c 건식 로그), `run_hazards --check update`
- git 조회: `status --porcelain`, `rev-parse`, `ls-files --eol`·`--error-unmatch`, `check-attr`, `check-ignore -v`, `cat-file -e`, `merge-base --is-ancestor`, `show --stat`·`-s`
- 만든 파일: scratchpad `verif-ed7run\`(source_guard state, 도구 보고서 md). 보고 전에 폴더째 지웠다.
- 메모리: `agent-memory\verif-protocol-auditor\audit_pitfalls.md`·`MEMORY.md`에 프로젝트 무관 함정 1항목을 더했다(pwsh `-File` 배열 매개변수, rc 0 오류 줄 생산자에서 log_errors 공허, 정지 경로 정체성).
- 블라인드 절차 공개(판정서에 옮길 것)
  - **(a)** Grep 1회의 `path`로 블라인드를 품은 상위 폴더인 C worktree `…\.claude\worktrees\ed7-impl\…\prelaunch_j9`를 썼다. 판 6 `ed6_inputs\x11\selection.json`의 worktree 사본이 그 안에 있다. glob은 `*.ps1`, 건수 모드였고, 출력은 ps1 파일 건수뿐이었다.
  - **(b)** Grep 1회의 `path`로 메인 `j_p3_cause`를 썼다. glob은 `jp3_remedy_spec_v6_erratum*.md`, 내용 모드였고 0건, 출력은 없었다. ripgrep이 `j9_runs` 아래를 순회했을 수 있다(O7-13·O7-19와 같은 종류).
  - **(c)** `ref_check`가 비슷한 이름 후보로 블라인드 정의 밖의 파일 이름을 화면에 냈다. `j9_runs/606f8713/cases_a1/{judge,logs}/baseline_compare.*`, `j9_runs/78fd5d2d/cases_a1/judge/baseline_compare.json`, `j9_runs/6bfb2560/ed7_probe_a1/condition*.json` 등이다.
  - 블라인드 파일 자체는 Read·Glob하지 않았다. `git ls-files`·`ls-tree`로 블라인드 폴더를 열거하지 않았다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v7.md 10902ffd…, jp3_remedy_spec_v7.md.sha256 8cfd1981…, jp3_remedy_spec_v7_erratum1.md 74c49bda…, jp3_remedy_spec_v7_erratum1.md.sha256 b1cfb220…, ed7_run_config.json 9ede99fb…, run_ed7_chain.ps1 bc83c834…, pre10a_c92c93_check.ps1 9f22938c…, audit_commands_ed7.txt c377b22f…, resource_estimate_ed7.json 8727cd4c…, handback_chain_runner.md f9feafe7…, handback_p51_record_prep.md 9e4483f1…, handback_placement_ed7.md dc947b90…, handback_run_config_prep.md 8cb61efc…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
