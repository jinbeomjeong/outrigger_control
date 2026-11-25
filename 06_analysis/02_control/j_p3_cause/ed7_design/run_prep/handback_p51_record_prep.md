판 7 정오 1 1-7에 따른 "P5-1형 33줄 판 6 기록 대조"를 실행 직전 단계까지 준비했습니다. 러너와 대조 스크립트를 만들었고 건식 확인은 모두 통과했습니다. Chrono 실행은 하지 않았고 커밋도 하지 않았습니다. 사용한 스킬은 없습니다.

## 1. 33줄과 대조 대상
- **33줄의 정의**: 정오 1 1-7의 문장 그대로입니다. "판 5 `j9_cases` 15, `j9_case_f` 15, 사례 C·D 2, X11 1"이고, 대조 항목은 `commands_sha256`입니다.
- **판 6 쪽 출력**: `j9_runs\79495405\impl_p51.done`이 가리키는 폴더는 `impl_p51_a1` 하나입니다(exit 0, commit 79495405). 그 안의 `j9_cases.jsonl`·`j9_case_f.jsonl`·`cd.jsonl`·`lsj4_x11.jsonl` 줄 수는 15/15/2/1이고, 모두 64자 해시를 가지며 error 줄은 없습니다.
- **실행 경로**: 판 6 `step5_impl_ed6.ps1 -Part p51`의 네 호출을 같은 꼴로 C에서 돌립니다. 건식 확인 결과 C의 `run_v5.py --list`가 `j9_cases` 15줄, `j9_case_f` 15줄을 냈습니다(각 exit 0).
- **판 6과 다른 점**은 둘이고 둘 다 기록합니다.
  - `NUMBA_CACHE_DIR`를 출력 폴더 안에 둡니다(사용자 허용, M-c 러너와 같은 방식).
  - 마스크·worker 수는 인자로 받습니다. 판 6은 `0x0FFFFFFF` 한 마스크에 5/8/2/1 worker였습니다.

## 2. 만든 파일
**러너** `C:\Users\jinbeom\.claude\runners\outrigger-ed7-p51-record\run_p51_record.ps1`
- C의 `run_steps\common.ps1`과 `run_steps_ed7\core_kind_ed7.ps1`을 dot-source합니다. 단, C가 깨끗한 실행 커밋인지 먼저 확인한 뒤에 합니다.
  - 그래서 스레드 변수·화면 변수 정리(`Set-RunEnvironment`), dynamics-dev `python.exe -I -B` 직접 호출, 고정 입력 12개의 sha와 C `jp3_fixed_inputs.py` 상수 대조가 C 정의 그대로입니다.
- 시작과 끝에 C 정체성(HEAD, tracked clean, 03_src tree)을 기록합니다. C worktree의 미추적·무시 파일 지문도 남기는데, 개수와 정렬 목록 sha만 남기고 파일 이름은 남기지 않습니다.
- 실행이 끝나면 `baseline_check.py identity --mtime`을 돌립니다.
- 출력 위치는 `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\p51_record_8a2a52ce\`입니다.
  - 하위: `runs\`(4개 jsonl, `*_t4h\`, `*.identity.json`, `logs\`), `numba_cache\`, `identity_check.md`, `run_record.json`, `progress.json`
- 거부 조건:
  - 출력 폴더가 이미 있으면 거부합니다.
  - 출력 폴더가 C worktree나 `j9_runs\8a2a52ce` 안이면 거부합니다.
  - **`j9_runs\8a2a52ce`가 이미 있으면 거부합니다.** 실행 단계가 시작됐다는 뜻이고 1-7은 "본 실행 전"을 요구하기 때문입니다. `-AfterRunStart`를 주면 진행하고 그 사실을 기록합니다.
- 종료 코드:

| 코드 | 뜻 |
|---|---|
| 0 | 정상 |
| 2 | 시작 전 거부(인자·경로·시점) |
| 3 | C가 깨끗한 실행 커밋이 아님, 고정 입력 불일치, 실행 실패, 실행 중 C 변경 |
| 4 | 실행·C는 정상이나 `baseline_check identity`가 0이 아님 |

- `progress.json` 키는 `stage`·`done`·`total`(33)·`unit`(line)·`started_at`·`updated_at`뿐이고 결과값은 없습니다. 15초마다 원자적으로 갱신합니다.

**대조 스크립트** `C:\Users\jinbeom\.claude\runners\outrigger-ed7-p51-record\compare_p51_record.py` (python-dev)
- 파일별로 짝을 짓고, 줄은 `run_v5.job_key`(판 6 hash-match와 같은 키)로 맞춰 `commands_sha256` 같음·다름을 냅니다.
- 다음이 있으면 문제(incomplete)로 남깁니다: `run_record`가 깨끗하지 않음, 판 6 `.done`의 exit·commit 이상, 줄 수(15/15/2/1)와 다름, 누락·추가·중복·error 줄, 64자가 아닌 해시, 짝 수가 33이 아님.
- 출력은 `...\p51_record_8a2a52ce\compare\`의 `p51_record_compare.json`과 `p51_record_lines.tsv`입니다. `compare\`가 이미 있으면 거부합니다.
- stdout 끝줄에는 상태와 건수만 나옵니다. 해시·결과값은 파일에만 있습니다.
- 종료 코드:

| 코드 | 상태 |
|---|---|
| 0 | equal |
| 1 | differ |
| 2 | incomplete |
| 3 | error |

## 3. 실행 명령 (메인이 띄움)
```
& 'C:\Program Files\WindowsApps\Microsoft.PowerShell_7.6.9.0_x64__8wekyb3d8bbwe\pwsh.exe' -NoProfile -NonInteractive -File C:\Users\jinbeom\.claude\runners\outrigger-ed7-p51-record\run_p51_record.ps1 -MaskHex <마스크> [-MaskCases ..] [-MaskCaseF ..] [-MaskCd ..] [-MaskX11 ..] [-CasesWorkers 5] [-CaseFWorkers 8] [-CdWorkers 2]
```
- 러너가 띄우는 인터프리터는 `C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B`이고, 작업 폴더는 C worktree입니다.
- 실행 마스크를 정한 뒤 `-Check`를 붙여 다시 돌리면, 아무것도 쓰지 않고 C 정체성·고정 입력·계획 명령만 출력합니다.

대조 명령(실행이 끝난 뒤):
```
C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B C:\Users\jinbeom\.claude\runners\outrigger-ed7-p51-record\compare_p51_record.py --root C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\p51_record_8a2a52ce
```

## 4. 예상 자원 (compute-scheduler-expert 배치용)
판 6 `impl_p51_a1`의 `logs\*.record.json` 실측(마스크 `0x0FFFFFFF`, P+E 혼합)을 근거로 했습니다.

| 실행 | 줄 | workers | cpu_time_s | wall_s | 줄당 wall_s | peak RSS |
|---|---|---|---|---|---|---|
| j9_cases | 15 | 5 | 1483 | 309 | 78~112 | 1150 MB |
| j9_case_f | 15 | 8 | 1687 | 238 | 103~123 | 1650 MB |
| case_cd | 2 | 2 | 267 | 137 | 133~136 | 478 MB |
| x11_both | 1 | 1 | 140 | 142 | 140 | 289 MB |

- 합계는 CPU 약 3580 s(약 60 CPU-분), 동시 단일 스레드 프로세스 16개, 메모리 합 약 3.6 GB입니다. 판 6 단계 전체 wall은 313 s(약 5.2분)였습니다.
- 임계 경로는 `j9_cases`입니다(5 worker × 3회). `-CasesWorkers 8`이면 2회로 줄어 약 4분이 예상됩니다(추정).
- `numba_cache`가 새로 비어 있어 처음 컴파일에 시간이 더 듭니다(추정 +0.5~1.5분). 판 6은 기존 캐시를 썼습니다. M-c 건식 실행이 같은 방식(새 캐시, 3개 동시)으로 exit 0이었습니다.
- 전체 예상은 P코어 16논리(`0x0000FFFF`, 16 프로세스)로 약 6~9분, 혼합 28논리로 약 5~6분입니다(추정).
- 비용 측정이 아니므로 다른 계산과 겹쳐도 됩니다. 단 **판 7 실행 단계와는 겹치면 안 됩니다.**
- 러너는 cpu-scheduler 이력(`record.py`)을 쓰지 않습니다. 실측은 `runs\logs\<label>.sample.json` 4개를 기록 모드에 넘겨 주세요.

## 5. 검증과 도구 종료 코드 (그대로)
- depcheck: STAMP(이 세션에서 이미 점검, 모두 있음)
- `run_p51_record.ps1 -MaskHex 0x0000FFFF -Check`: exit 0. 계획 명령 4개가 판 6 명령과 경로만 다르고 같습니다. C worktree 미추적·무시 지문은 전후 같았고 출력 폴더는 생기지 않았습니다.
- C에서 `run_v5.py j9_cases --list`·`j9_case_f --list`: 각 exit 0(15줄씩). `jp3_case_replay.py --help`·`jp3_x11_replay.py --help`: 각 exit 0. 실행 뒤 C 지문은 그대로였습니다.
- `tools\verif\ps1_lint.py` (러너): exit 0(오류·경고 0)
- ruff `--isolated`: 처음 exit 1(BLE001: `main`의 `except Exception` — 예상 밖 예외를 모두 도구 오류(종료 3)로 내려는 의도). `noqa` 사유를 달고 다시 돌려 exit 0
- codespell: exit 0. `py_compile -W error`: exit 0. `compare --help`: exit 0
- 대조 스크립트 자체 시험: 판 6 실제 출력 4개를 새 쪽으로 복사한 생산자 꼴 입력을 썼고, 작업 폴더는 입력과 다른 곳에 두고 `main`을 끝까지 돌렸습니다. 시험 스크립트는 exit 0이고, 사례별 결과는 모두 기대와 같았습니다.

| 사례 | 결과 |
|---|---|
| 같음 | 0 / equal, 33짝 |
| 해시 하나 바꿈 | 1 / differ, 다름 1 |
| cd 줄 하나 뺌 | 2 / incomplete |
| run 종료 코드 3 | 2 |
| `compare\` 있음 | 2 |
| 깨진 JSON | 3 / error |
| 최상위 키 하나 더함 | 0. 보조 기록에 키 차이 15짝, 상태는 그대로 |

- 시험 입력과 scratchpad `python-p51\`는 지웠습니다.

## 확인 필요
1. **보조 기록 항목**: 정오가 정한 대조는 `commands_sha256`뿐입니다. 저는 상태를 바꾸지 않는 보조 기록 둘을 더 넣었습니다(정오에 없는 제안).
   - `harness_commands_sha256` 같음 여부
   - 최상위 키 이름의 한쪽 차이(예: C에 기록 키가 더해졌는지)
   
   판정서에 이 둘도 적을지, 빼고 `commands_sha256`만 적을지 정해 주세요.
2. **실행 단계가 이미 시작됐을 때**: 러너는 기본으로 거부합니다. 그래도 돌릴지(`-AfterRunStart`)는 메인·사용자가 정합니다.
3. **identity 검사 `--mtime`**: C worktree에서 경고가 나면 러너는 종료 4로 끝납니다. 판 7 실행 단계도 같은 검사로 멈추므로 본 실행 전에 미리 신호를 받는 셈입니다. 대조 자체는 그대로 진행됩니다.
4. **결과 처리(정오 1-7)**: 대조가 `differ`(종료 1)이면 사용자에게 알리고 판단을 받아야 합니다. 판정 상태와 실행 단계를 자동으로 막지는 않습니다.

## 메인 세션 권고
- 판 7 실행 단계 1 전에 compute-scheduler-expert로 마스크·worker를 받아 위 명령으로 띄워 주세요(약 6~9분 예상). 진행 파일은 `...\p51_record_8a2a52ce\progress.json`이고, 감시할 때 `블라인드 예외(진행 파일)`로 넘기면 됩니다.
- 끝나면 대조 명령을 돌리고, 출력 폴더(`compare\` 포함)에 `baseline_check.py write-sums`로 SHA256SUMS를 만들어 두는 것을 권합니다.
