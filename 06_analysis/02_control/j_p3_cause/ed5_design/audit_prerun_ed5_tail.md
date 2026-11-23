## 감사 요약
- 본 결과: `j9_runs/606f8713/12b_vbk_a1/judge/judge.json`(이미 판정된 12b 결과)에서 `status`, `exit`, `ready_rule.verdict`, `ready_rule.blocks_used`를 봤고, `allow_k`는 정수인지와 8-2 규칙값과 같은지만 확인했다(값은 출력하지 않음). 앞으로 판정할 records·ckdrop·j9main 출력은 아직 없고 열지 않았다. 블라인드 경로(`cdry_a1/VBK_c92*`·`VBK_c93*`·`cdry_a1/logs/`)도 열지 않았다.
- 대상: 판 5 남은 단계 step7 → 7b → 8의 러너 `C:\Users\jinbeom\.claude\runners\outrigger-ed5-tail\run_tail.ps1`(sha f259e2c9)과 `launch.ps1`(579c9ce5). 시점은 실행 전이다. 기준은 정오 2(erratum2.md 639c54e9) 2-6·2-7.1·2-9.5·2-9.6, 정오 8(8c420e85) 8-9·8-10, 덧붙임 4a-5의 4·5절, 덧붙임 4a8:198이다.
- 판정: 차단 0 / 실행 전 수정 0 / 기록 4. 마스크 `0x0FFFFFFF`와 worker 20은 규칙이 고정한 정체성이 아니다. 러너의 인자·순서·멈춤 처리도 규칙과 맞는다. 실행 가능하다.

## 발견 사항 (심각도순)

[기록][I] B-1: 마스크와 worker는 판정 정체성 필드가 아니다. 다만 step8의 V0 표본 해시 대조가 새 배치에서 돌기 때문에 배치가 결과 비트에 영향을 주면 재시도할 수 없는 실패가 된다 [추정: 영향 가능성 낮음]
- 정체성 필드가 아닌 근거
  - 4a-5 4절(`jp3_remedy_spec_addendum_4a5.md:71-82`)이 정한 실행 정체성은 head(40자, 실행 커밋), is_clean, git 실패 표지뿐이다. `Invoke-IdentityCheck`·`Invoke-IdentityCheckPart`(`run_steps/common.ps1:311-323`, `common_ed5.ps1:228-242`)도 `baseline_check identity --expect-commit 606f8713 --mtime`만 부른다.
  - `run_v5.py:412` `RUNTIME_JOB_KEYS = ("mask", "t4h_dir")`이고 `job_key`(:419)에서 mask를 뺀다. `jp3_j9main_judge.py:126` `RUNTIME_JOB_FIELDS = ("mask", "t4h_dir")`이고, v0-sample은 `commands_sha256`만 비교한다(:185).
  - j9main 판정의 H-2 정체성은 태그 기저, rev 6, `spec_edition`만 본다(:439-474). mask·workers·threads는 보지 않는다.
  - `jp3_ckdrop_record.py`에는 mask·workers를 읽는 코드가 없다(Grep 0건).
  - 판정 도구(도구 checkout ed5-tool8)를 grep한 결과 mask·workers 참조는 `RUNTIME_JOB_FIELDS` 한 곳뿐이다.
  - 덧붙임 4a8:198 원문은 "마스크·worker는 결과 비트와 무관한 배치 변수로 다뤄 옴"이다.
  - 2-7.1 비용 항목(erratum2:156)은 "배치표(compute-scheduler-expert), 예약, 감시"를 메인 몫으로 둔다. step7b 머리 주석에는 "the placement is the main session's", step8 머리 주석에는 "Batch table … by the main session"이라고 적혀 있다.
  - worker 수를 맞추라는 규칙은 정오 8 8-9 (c) 하나다("`--workers`는 4로 같아야 한다", erratum8:248). 이 조항은 12b의 VBK·b4 VBK0 대 저장 b1·b2 VBK0에만 적용되고, 코드도 step6b·6c에서만 부른다(`Assert-E8RunCondition`). 7b는 두 팔(VBK0·VBK) 16줄을 같은 마스크·worker 1로 한꺼번에 돌리므로 짝이 대칭이다.
  - "P 8 + E 12 약 2,360 s"(erratum2:155)는 비용 가정을 적은 문장이고, 실행 조건을 정한 문장이 아니다.
- 남는 위험
  - step8 1단계는 저장 V0(`main.jsonl`)와 `commands_sha256`을 비교한다. 이 표본도 `SampleMaskHex`의 기본값 = `MaskHex`(step8:63-64)로 P+E 혼합 배치에서 돈다.
  - 해시가 다르면 2-10(erratum2:278)에 따라 "실패"(종료 1)다. 이 경우 `Read-PreviousStops`(common.ps1:197-207)가 이후 시도를 모두 거부한다.
  - P코어와 E코어의 ISA가 같고 run_v5가 스레드 변수를 1로 두므로(:45-47) 영향 가능성은 낮다고 본다. 다만 저장 V0가 어느 마스크에서 만들어졌는지는 확인하지 않았다.
  - 4a-5 5절 "가. 실행 환경 원인" 재시도(:118)는 "같은 커밋·같은 명령"이다. 따라서 j9main을 다시 시도하면 `-MaskHex 0x0FFFFFFF -Workers 20`을 그대로 써야 한다.
- 권장 조치: 규칙상 바꿀 것은 없다. 위 두 점(해시 불일치는 재시도 불가 실패, 재시도는 같은 배치)을 메인이 알고 띄운다.

[기록][R] B-2: `--stop-on-fail`이면 7b가 실패할 때 8이 자동으로 시작되지 않는다. 규칙과 충돌하지 않는다.
- 2-6 103행: "앞 단계가 종료 0으로 끝나기 전에는 다음으로 가지 않는다". 러너 동작은 이 일반 규칙과 같다.
- 2-6 9·2-9.5(erratum2:114, :241): 7b는 "j9_main의 선행 조건이 아니다". 실제로 step8의 `$Required`(step8:31)에는 ckdrop이 없다.
- 7b 안의 기록 도구가 종료 2·3이면 `Invoke-RecordTool`(common_ed5:193-205, ContinueCodes 0·2·3)이 "계산 안 됨"으로 남기고 계속한다. 2-9.5 "다른 단계를 막지 않는다"는 이 경우다. 러너가 7b에서 멈추는 것은 실행 실패(`Wait-Runs` 종료 3), 정체성 실패(2), 시작 검사 실패뿐이다.
- `jp3_ckdrop_record.py:18`의 종료 코드는 0·2·3뿐이다. 종료 1로 재시도가 막히는 길은 없다.
- 7b가 멈추면 메인은 step8을 따로 띄우면 된다(`step8_j9main.ps1 -Attempt 1 -MaskHex 0x0FFFFFFF -Workers 20`). 이때 7b가 멈췄다는 사실과 이유를 기록에 공개한다.

[기록][I] B-3: 스케줄러 이력에 혼합 마스크가 'P'로 기록된다.
- `run_steps/common.ps1:179-184` `Get-CoreKind`는 `(mask -band 0xFFFF) -ne 0`이면 'P'를 돌려준다. 그래서 7b·8 실행의 `record.py --core`가 P로 남는다(:287).
- 판정·정체성과는 무관하다. 공용 `run_steps/`는 8-9 (a)에 따라 고칠 수 없으므로, compute-scheduler-expert를 기록 모드로 부를 때 "P 8 + E 12 혼합"이라고 따로 적는다.

[기록][도구] B-4: `ps1_lint`의 `tee_with_return`(run_tail.ps1:45)은 오탐이다.
- `Invoke-Logged` 줄 48-49의 파이프라인은 `Tee-Object … | Out-Host`로 끝난다. 그래서 Tee 출력은 반환값에 섞이지 않고, 함수는 정수 하나만 돌려준다.
- `launch.ps1:2`의 `noexit_in_comment`(info)는 주석 속 "no -NoExit" 문구에 걸린 것이다. 실제로는 -NoExit을 쓰지 않는다.

## 규칙↔도구 대조표
| 규칙 | 실행 자료 | 판단 |
|---|---|---|
| 2-6 9·10, 8-9 "순서는 2-6 그대로"(erratum8:279): (7) → 7b → j9_main | run_tail.ps1:24-26 records → ckdrop → j9main | 일치 |
| 원판 8 4.(7)·step7 머리: 단일 실행, mask 0xFFFF | 러너가 `-Attempt 1`만 넘긴다. 마스크는 스크립트 고정(step7:19). launch.ps1:10 설명도 "P 0xFFFF" | 일치 |
| 2-9.5: 16줄, 줄마다 worker 1, 동시 실행, 배치는 메인 | `-MaskHex 0x0FFFFFFF`(필수 인자), `--workers 1`, `--affinity $MaskHex`(step7b:39-43) | 일치 |
| 2-7.1: 배치는 compute-scheduler-expert, `-MaskHex`·`-Workers` 필수 | `-MaskHex 0x0FFFFFFF -Workers 20`. 표본은 기본값으로 같은 값 | 일치 |
| 2-6 10 선행 조건 (1)~(7) `.done`, dg3.done, 12b 판정 파일 sha·`status` pass·`exit` 0 | step8:31-53 | 일치 |
| 8-10 2-9.6 덧붙임: `ready_rule.verdict` pass, `allow_k` = 8-2 값, 블록·키 없으면 통과 아님 | `Get-E8ReadyRuleStop`(e8_gates_ed5.ps1:161-178), `Get-E8Allowance` b1,b2→7 / b1,b2,b4→9(:50-59) = erratum8:66-67 | 일치 |
| 8-9 (f): 스크립트 = 도구 커밋, 시뮬레이션 = 606f8713(ed5-run5), 판정 = 도구 checkout | `Initialize-E8Step`, `Invoke-ToolJudge`(common_ed5:436-470). step7·7b·8 모두 사용 | 일치 |
| 8-9 (a): diff 한정(main HEAD 포함) | `git diff --name-status 606f8713 HEAD`(521644d7): M은 00_docs·CLAUDE.md·jp3_12b_judge.py·05_tests·run_steps_ed5뿐이고 06_analysis는 A뿐이다(j9_runs도 M·D 0). `74a4bbf4..HEAD` run_steps_ed5 차이는 common_ed5.ps1 M 하나($ToolCommit 줄) | 허용 규칙 안 |

## step8 전제 입력(정적 확인, 2026-11-23)
- `p1`·`dry`·`fpath`·`cases`·`casef`·`t8`·`dg3`·`12b_vbk` `.done`이 모두 있다. 각각 `exit_code` 0, commit 606f8713이고 folder가 있다. `records`는 이 러너의 첫 단계가 만든다.
- `records`·`ckdrop`·`j9main`은 `.done`·`.stop`·`_a1`·`_a2`·`_a3` 폴더가 모두 없다. 따라서 `Initialize-Step`의 "이미 done", "폴더 있음", "이전 실패 거부" 멈춤에 걸리지 않는다.
- `12b_vbk.done` → `judge_file` `…/12b_vbk_a1/judge/judge.json`. 실제 sha 254d95ff…가 표지의 sha와 같다. `status` pass, `exit` 0이다. `ready_rule`에는 verdict·allow_k·blocks_used가 모두 있고, verdict는 pass, blocks_used는 [b1, b2]다. allow_k는 정수이고 8-2 값과 같다.
- `ed5_inputs/j9main_v0_sample_keys.json`과 `ckdrop/{tck,dropout}_keys.txt`·`_{FL,FR,RL,RR}_plan.json` 10개가 모두 있다. `FIXED_INPUTS_606f8713.SHA256SUMS`에 등재돼 있고 sha가 같다. `FIXED_INPUTS_74a4bbf4.SHA256SUMS`도 있다.
- ed5-tool8 HEAD = 74a4bbf4, ed5-run5 HEAD = 606f8713이다. 두 worktree 모두 추적 파일 변경이 없다.

## 확인 필요
- 없음. B-2(7b가 멈추면 8을 따로 띄울지)는 7b가 실제로 멈출 때 메인이 정한다.

## 위임 필요
- `위임 필요(python-expert): tools/verif 후보` — `ps1_lint.py`의 `tee_with_return`이 `Tee-Object … | Out-Host`로 끝나는 파이프라인을 경고로 낸다. 재현: `ps1_lint.py C:\Users\jinbeom\.claude\runners\outrigger-ed5-tail\run_tail.ps1` → 종료 1. 기대: 마지막 단계가 `Out-Host`·`Out-Null`이거나 `$null =`이면 제외한다.

## 메인 세션 권고
- `launch.ps1`로 띄운다(30분 초과이므로 §3 감시와 예약을 쓴다. 예약은 러너가 등록한다).
- 감시 지시문에 블라인드 경로로 `j9_runs/606f8713/{records_a1,ckdrop_a1,j9main_a1}/judge/`를 넣는다.
- j9main이 실행 환경 원인으로 멈춰 다시 시도하면 같은 `-MaskHex`·`-Workers`를 쓴다(B-1).

## 검사하지 못한 것
- 저장 V0(`main.jsonl`)를 만들 때의 마스크와 코어 종류(B-1의 위험 크기).
- P·E 혼합 배치가 비트를 바꾸지 않는다는 직접 증거(같은 키를 P와 E에서 돌린 해시 비교). 실행이 필요해 하지 않았다.
- `log_errors.py`: 대상 로그가 없다.
- `step7b`·`step8`의 `Get-R79Environment`·`$R79Common` 내용은 대조하지 않았다(직전 재개 감사 범위).

## 실행한 검증
- `depcheck.ps1` → STAMP(이 세션에서 이미 점검함). numpy·pyyaml·git 있음.
- python-dev `-I -B`, `MKL_THREADING_LAYER=TBB`, PowerShell 도구:
  - `ps1_lint.py run_tail.ps1 launch.ps1` → 종료 1(warning 1은 오탐 B-4, info 1)
  - `placeholder_scan.py run_tail.ps1 launch.ps1 --pattern-set both` → 종료 0(자리표시 0)
  - 즉석 스크립트 `pre8.py`(scratchpad `auditor-ed5tail\`): `.done` 파싱, 12b 판정 파일 sha와 ready_rule 키, 고정 입력 sha 대조
- Bash git 조회: `diff --name-status 606f8713 HEAD`(j9_runs 제외, 그리고 j9_runs의 M·D·R만), `diff 74a4bbf4 HEAD -- run_steps_ed5`, 두 worktree의 `rev-parse`·`status --porcelain`, `status -- prelaunch_j9 j9_runs/606f8713`(변경 0).
- Read·Grep: run_tail·launch, step7·7b·8, common_ed5.ps1, run_steps/common.ps1, e8_gates_ed5.ps1(ready_rule·allowance), 정오 2(2-6·2-7.1·2-9)·정오 8(8-9·8-10), 4a-5, run_v5.py·jp3_j9main_judge.py·jp3_ckdrop_record.py·jp3_run_identity.py·r79의 affinity 경로.
- scratchpad 폴더 `auditor-ed5tail\`(pre8.py, guard.json)를 만든 뒤 지웠다(삭제 확인).
- 에이전트 메모리 `audit_pitfalls.md`에 1항목, `MEMORY.md` 색인에 1줄을 덧붙였다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha run_tail.ps1 f259e2c9…, launch.ps1 579c9ce5…, step7_records.ps1 137de23a…, step7b_ckdrop.ps1 dc497b12…, step8_j9main.ps1 fb077000…, common_ed5.ps1 08184128…, e8_gates_ed5.ps1 ed6f9e2a…, jp3_remedy_spec_v5_erratum2.md 639c54e9…, jp3_remedy_spec_v5_erratum8.md 8c420e85…, 12b_vbk.done 63ad26d5…, judge.json 254d95ff…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
