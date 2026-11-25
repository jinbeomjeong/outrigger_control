판 7 본 실행용 연쇄 러너를 만들었습니다. 실행하지 않았고 커밋도 하지 않았습니다. `ps1_lint`는 종료 0, `-DryRun`도 종료 0입니다. 건식 전후로 `j9_runs\8a2a52ce`, progress.json, 잠금 파일은 생기지 않았고 ed7-impl status 항목도 0개 그대로입니다.

## 1. 만든 파일
- `C:\Users\jinbeom\.claude\runners\outrigger-ed7-run\run_ed7_chain.ps1` (sha256 `bc83c83451cc95f0ae046df12dcf6b104571381b2a3a74c9e67f38fe3639b839`)
- 다른 파일은 만들지 않았습니다. C의 단계 스크립트와 `pre10a_c92c93_check.ps1`은 고치지 않았습니다.
- **단계 순서**: scope → l1ref → t8 → cases → probe → confirm → j9main → sens → dg3 → pre10a → 12b_plan → 12b_vbkm0(`-Phase base`). 12개이고, 단계 스크립트는 C의 것을 `-Attempt N`만 붙여 그대로 부릅니다.
  - placement 6단계(t8·cases·probe·confirm·j9main·sens)에는 `-MaskHex 0x0FFFFFFF -Workers 20`을 줍니다.
- **각 단계 뒤 검사**
  1. 종료 코드가 0이어야 합니다.
  2. 그 단계 시작 뒤에 생긴 `STEP.stop*`가 없어야 합니다.
  3. `STEP.done`의 `exit_code`가 0이고 `commit`이 C이며 폴더가 있어야 합니다.
  4. `baseline_check.py write-sums --recursive <단계 폴더>`가 0이어야 합니다(정오 1-10).
  5. `log_errors.py <단계 폴더>\logs`가 0이어야 합니다. scope는 `.log`를 남기지 않으므로 건너뜁니다.
  - 하나라도 어긋나면 `[stop]`(종료 1)으로 끝나고 다음 단계는 띄우지 않습니다.
- **pre10a**: 12b_plan 바로 앞에서 부르고, 0이 아니면 `[stop]`입니다. `-StartAt 12b_plan`으로 시작해도 pre10a부터 돕니다.
- **예약**: l1ref·j9main·sens·dg3·12b_vbkm0은 단계를 시작하기 직전에 `reserve.py add`(러너 PID)를 하고, 끝나면 `release`합니다.

| 단계 | 마스크 | RAM | TTL |
|---|---|---|---|
| l1ref | 0xFFFF | 6144 MB | 120분 |
| j9main | 0x0FFFFFFF | 7168 MB | 120분 |
| sens | 0x0FFFFFFF | 7168 MB | 150분 |
| dg3 | 0xFFFF | 4096 MB | 90분 |
| 12b_vbkm0 | 0x00FF | 3584 MB | 120분 |

  - 예약에 실패하면 경고만 남기고 단계는 그대로 돕니다(make_runner와 같은 방식).
- **진행 파일**: 러너 루트의 `progress.json`입니다. 키는 `stage`·`stage_number`·`done`·`total`(12)·`unit`('stage')·`started_at`·`updated_at`이고 결과 값은 없습니다. 단계 시작과 끝에 임시 파일로 쓴 뒤 바꿔 넣습니다.
- **로그**: `j9_runs\8a2a52ce\main_checks\chain_log\chain_ed7_a<N>.log`이고, 이미 있으면 N이 늘어납니다.
  - 제어 줄은 `[start]`·`[end]`·`[stop]`·`[pause]`·`[done]`입니다.
  - 보조 줄은 `[check]`·`[reserve]`·`[identity]`·`[info]`입니다.
  - 단계별 콘솔 출력은 `chain_ed7_a<N>.<nn>_<stage>.log`에 남습니다.
  - 도구 보고서는 `main_checks\{sums_write,log_errors,t4h_arrays}_<폴더>_r<N>.md`, pre10a 기록은 `main_checks\pre10a_c92c93_a<N>.json`입니다.
- **정체성**: 시작과 끝에 `check_ed7.ps1`이 종료 0인지, `git -C ed7-impl status --porcelain`(미추적 포함)이 0항목인지 봅니다.
  - 로그에는 항목 이름 없이 개수만 남깁니다.
  - 시작에서 어긋나면 어떤 단계도 띄우지 않고 멈춥니다(종료 2). 끝에서 어긋나면 `[done]` 대신 `[stop]`(종료 1)입니다.
- **창**: 창 제목을 러너 안에서 직접 단계마다 `[ed7 chain n/12 <stage>] do not close`로 바꿉니다. 시작할 때 안내 문구(무엇·코어·예상 종료·진행 파일·닫지 말 것)를 찍습니다.
  - `label_console.py`는 다른 콘솔에 붙어 제목을 바꾸는 외부용 도구라 쓰지 않았습니다. 러너가 자기 창이므로 직접 바꾸는 것이 같은 효과입니다.
  - `-NoExit`는 쓰지 않습니다.
- **추가한 안전장치**
  - 잠금 파일 `run_ed7_chain.lock`(PID와 시작 시각): 이중 실행을 막습니다. 두 번째 러너의 단계가 폴더 충돌로 `.stop`을 남기면 첫 러너가 그것을 보고 멈추기 때문입니다.
  - P5-1 기록(`j9_runs\p51_record_8a2a52ce\run_record.json`)이 끝나 있어야 시작합니다(정오 1-7 "본 실행 전, 겹치지 않게"). 지금은 있습니다.
  - 셸에 `ED7_DRY_RUN_ROOT`가 남아 있으면 지우고 기록합니다. 남아 있으면 단계가 건식으로 돌기 때문입니다.
- **종료 코드**: 0 완료 / 1 멈춤 / 2 시작 거부(어떤 단계도 띄우기 전) / 3 러너 내부 오류 / 4 일시 정지. 건식은 0 계획 출력·시작 조건 충족, 2 시작이 거부될 상황입니다.

## 2. 관문 표 (명세 rev 6·정오 1 문장 기준)

| 자리 | 근거 문장 | 러너 처리 |
|---|---|---|
| 1단계 전 | 정오 1-19 "T′과 그 재감사는 판 7 실행 출력이 생기기 전에 끝낸다", 1-19 M-c 건식 확인, 정오 1-7 P5-1형 33줄 기록 "본 실행 전에… 겹치지 않게" | 앞의 둘은 이미 끝난 전제(커밋 265dc641)라 메인이 확인합니다. P5-1은 `run_record.json`이 없으면 시작을 거부합니다(종료 2) |
| l1ref 뒤 | 판 6의 "고정 입력 목록 커밋" 관문은 판 7에서 정오 1-2가 단계별 sha 단언으로 바꿨습니다(`--edition 7`이 없어 목록 파일이 없음) | **관문 없음** |
| l1ref·dg3 뒤 | 정오 1-13 "첫 l1ref·dg3 출력에서 `key_presence.py --npz-dir … --array …`로 확인… 배열이 없으면 `setting_defect`" | 자동으로 돌립니다. 대상은 L1_VBM_t4h·L1a_VBM_t4h·dg3 VBM_t4h이고, 이름만 보고 값은 보지 않습니다. 0이 아니면 **`.pause`**(12a·12b 판정 불가로 이어지므로 메인 판단) |
| 각 단계 `.done` 뒤 | 정오 1-10 SUMS | 자동 write-sums. 실패하면 `[stop]` |
| impl_probe 뒤 (P7-1·2·3·9 "판정(관문)… 다르면 멈춤") | 명세 4절 5a "실행(4절 5의 줄 실행과 6~10의 줄 실행)은 T 전에도 할 수 있다", 5.2 "C의 실행 출력은 T를 기다리는 동안 그대로 둔다" | **기본은 멈추지 않습니다.** 실행보다 판정을 먼저 하라는 문장이 없기 때문입니다. 원하면 `-PauseAfter probe`(확인 필요 1) |
| confirm·j9main 등 각 단계 뒤 | 4절 6 "순서와 멈춤은 판 6 4절과 같다"(판 6: 판정 실패(종료 1)면 멈추고 사용자에게 묻는다) | 판 6은 판정이 단계 안에 있었고, 판 7은 판정이 T′에 있으며 5a가 실행 선행을 허용합니다. 그래서 기본은 멈추지 않고, `-PauseAfter <stage>`로 고를 수 있습니다 |
| dg3 뒤, 12b_plan 바로 앞 | 정오 1-2 조건 1(c92·c93 sha와 HEAD blob, "다르면 10번째 단계를 돌리지 않는다") | pre10a 자동. 0이 아니면 `[stop]` |
| 12b_vbkm0 base 뒤 | 정오 1-1 "12번째(b4)·13번째(VBKM) 단계는 T와 그 감사 뒤에만", 1-3 decide 형식 | 연쇄는 여기서 `[done]`으로 끝납니다. 다음은 메인이 T′ decide를 돌리고 step10b `-Phase b4` / step10c를 띄웁니다 |

- 재개: `-StartAt <다음 단계>`로 이어 갑니다.
  - 앞 단계마다 `.done`(종료 0, C)과 폴더의 `SHA256SUMS`가 있어야 합니다. 없으면 종료 2입니다.
  - attempt 번호는 기존 `STEP_a*`의 마지막 + 1로 자동으로 정합니다.
  - 일시 정지 표지(`chain_log\<stage>.pause`)에 재개 인자가 적힙니다.

## 3. 실행 명령 (메인이 사용자 승인 뒤에 띄웁니다)
```powershell
$pw = 'C:\Program Files\WindowsApps\Microsoft.PowerShell_7.6.9.0_x64__8wekyb3d8bbwe\pwsh.exe'
$r  = 'C:\Users\jinbeom\.claude\runners\outrigger-ed7-run'
# 건식(아무것도 띄우지 않고 쓰지 않음)
& $pw -NoProfile -File "$r\run_ed7_chain.ps1" -DryRun
# 본 실행: 분리 창(WMI), -NoExit 없음
Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{
    CommandLine = "`"$pw`" -NoProfile -File `"$r\run_ed7_chain.ps1`""; CurrentDirectory = $r }
# 이어 시작 / 일시 정지 지점 지정 예
#   ... -File "$r\run_ed7_chain.ps1" -StartAt t8
#   ... -File "$r\run_ed7_chain.ps1" -PauseAfter probe,confirm
```
- 주기 점검에서 먼저 grep할 것: `j9_runs\8a2a52ce\main_checks\chain_log\chain_ed7_a*.log`의 `[end]`·`[stop]`·`[pause]`·`[done]`. long-running-task-monitor에 넘길 `블라인드 예외(진행 파일)`은 `C:\Users\jinbeom\.claude\runners\outrigger-ed7-run\progress.json`입니다.
- 예상 시간은 배치표 상한 합계로 약 6.3시간이고 판정·대기는 빠져 있습니다. 시작 안내 문구에 예상 종료 시각이 찍힙니다.

## 4. 건식 출력 요약
- 기본(`-DryRun`): **종료 0**.
  - `start checks: ok`. 12단계 모두 attempt a1이고, 단계마다 run 명령, reserve 명령(5단계), 검사 명령(sums·log_errors, l1ref·dg3의 key_presence)을 출력했습니다.
  - pre10a 출력 경로는 `main_checks\pre10a_c92c93_a1.json`입니다.
  - 끝 줄은 `[done]` 뒤에 할 일(T′ decide)입니다.
- `-DryRun -StartAt 12b_plan`: **종료 2**(의도한 결과). `WOULD REFUSE - earlier stage scope: impl_scope.done missing`이 나왔고, 10/12 pre10a부터 시작하는 것을 확인했습니다.
- 건식 전후: `j9_runs\8a2a52ce` 없음, `progress.json` 없음, 잠금 파일 없음, ed7-impl status 0항목.

## 5. 검증 (도구 종료 코드는 그대로 적음)

| 검사 | 종료 코드 | 내용 |
|---|---|---|
| PowerShell 파서 | 오류 0 | – |
| `ps1_lint.py --repo outrigger-ed7-run run_ed7_chain.ps1` | **0** | error 0, warning 0, info 9(주석 안 `<N>` 7건, 주석의 `-NoExit` 1건, `Invoke-Logged` Tee 출력이 Out-Host로 잡힌다는 1건) |
| `run_ed7_chain.ps1 -DryRun` | **0** | – |
| `-DryRun -StartAt 12b_plan` | 2 | 의도한 거부 |
| `codespell run_ed7_chain.ps1` | 0 | – |

- **제어 흐름 리허설**: 실행 전이라 실제 단계를 돌릴 수 없어서, scratchpad에서 러너 사본으로 7가지 경우를 돌렸습니다.
  - 사본은 `$MainRoot`·`$ReserveScript` 두 줄만 바꿨습니다.
  - 가짜 단계 스크립트와 scratch git worktree를 썼고, write-sums·log_errors·key_presence는 진짜 verif 도구를 그대로 썼습니다.

| 경우 | 결과 |
|---|---|
| A 전체 | 종료 0, 11폴더 SUMS, 예약 5회 등록·해제 |
| B l1ref 배열 없음 | 종료 4, 표지 `l1ref.pause` → `-StartAt t8` 재개 종료 0 |
| C confirm 실패(.stop) | 종료 1 |
| D t8 로그 `errors 2` | 종료 1 |
| E 앞 단계 없이 `-StartAt t8` | 종료 2 |
| F pre10a 종료 1 | 종료 1, 12b_plan 안 띄움 |
| G `-PauseAfter probe` | 종료 4. 그 뒤 `-StartAt 12b_plan`은 2, `-StartAt scope`는 2 |

  - 모든 경우에 잠금 파일이 남지 않았고 worktree status는 0항목이었습니다.
  - 첫 리허설에서 결함 하나를 찾아 고쳤습니다. 빈 배열을 돌려주는 함수 결과가 `$null`이 되어 strict 모드에서 `.Count` 오류(종료 3)가 났고, 호출하는 곳을 `@(...)`로 감쌌습니다.
- scratchpad 하위 폴더 `python-ed7chain\`은 지웠습니다.

## 확인 필요
1. **impl_probe 뒤(그리고 confirm 뒤)에 판정 대기 정지를 둘지.** 문장끼리 긴장이 있습니다.
   - P7-1·P7-2·P7-3·P7-9는 "판정(관문)… 다르면 멈춤"이고, 4절 6은 "멈춤은 판 6 4절과 같다"입니다.
   - 반면 4절 5a는 "실행(4절 5의 줄 실행과 6~10의 줄 실행)은 T 전에도 할 수 있다"입니다.
   - 저는 5a에 따라 기본을 정지 없음으로 했습니다.
   - T′이 이미 감사를 통과했으므로, 판 6처럼 "판정 실패면 멈추고 묻는다"를 실행 순서에도 적용하려면 `-PauseAfter probe,confirm`으로 띄우면 됩니다. 그러면 밤사이 진행은 거기서 멈춥니다. 사용자 결정이 필요합니다.
2. **key_presence 결과를 `.pause`로 둔 것.** 정오 1-13은 "배열이 없으면 setting_defect"(판정 상태)라고만 했고 실행 정지 여부는 정하지 않았습니다.
   - l1ref에서 배열이 없으면 12a·12b가 판정 불가가 되므로 메인 판단으로 두었습니다.
   - 검사 대상은 ③ 켬 폴더(L1_VBM_t4h·L1a_VBM_t4h·dg3 VBM_t4h)뿐입니다. ③ 끔(VBM0)은 조건 배열이 없을 수 있어 넣지 않았습니다. 감사 명령 목록은 L1_VBM·dg3 VBM 둘만 보았는데, 저는 L1a_VBM을 더했습니다.
3. **main_checks 파일은 12b 스캔 범위 안에 있습니다.** 연쇄 로그와 검사 보고서는 `j9_runs\8a2a52ce\main_checks` 아래라 12b_plan의 `--scan-root`(06_analysis)·`--scan-required` 범위에 들어갑니다.
   - 내용은 `.log`·`.md`·pre10a json이고 r79 키가 없으니 seed에는 영향이 없을 것으로 봅니다(추정). 준비 보고 확인 필요 3과 같은 사정입니다.
   - 위치는 지시대로 두었습니다.
4. 러너는 단계 안의 EcoQoS를 다루지 않습니다. 판 6 러너와 같습니다.

## 공개(블라인드 절차)
- 블라인드 경로(`606f8713\cdry_a1\VBK_c92*`·`VBK_c93*`·`cdry_a1\logs\`와 worktree 사본, 판 6 `ed6_inputs\x11\selection.json`)는 Read·Grep·Glob·스캔 대상에 넣지 않았습니다.
- 경로를 직접 지정해 본 것은 다음뿐입니다.
  - C worktree의 `run_steps_ed7\*.ps1` 목록과 내용, `run_steps\common.ps1`·`record_helper.ps1`(Grep)
  - 명세 v7 4~5절, 정오 1 전문, 판 6 명세 4절
  - 러너 폴더(ed6 r2, p51 record)
  - verif README 해당 절
  - `p51_record_8a2a52ce\run_record.json`(존재 여부만), `ed7_run_config.json`(run_commit·worktree만)
- 결과 값은 읽거나 출력하지 않았습니다.

사용한 스킬: 없음
