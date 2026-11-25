판 7 본 실행 준비를 마쳤습니다. 실행 설정 파일을 만들었고 `check_ed7.ps1`은 **종료 0(CHECK ok)**입니다. Chrono 실행과 커밋은 하지 않았고, C·T′ worktree도 고치지 않았습니다(실행 뒤 `git -C ed7-impl status --porcelain` 빈 출력, `j9_runs\8a2a52ce`는 아직 없음).

## 1. 만든 파일
| 파일 | 내용 |
|---|---|
| `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\prelaunch_j9\ed7_run_config.json` | C의 `run_steps_ed7\ed7_run_config.template.json`으로 만든 실행 설정 |
| `C:\Users\jinbeom\.claude\runners\outrigger-ed7-run\pre10a_c92c93_check.ps1` | 정오 1-2 조건 1 확인 스크립트(12b_plan 바로 전) |
| `C:\Users\jinbeom\.claude\runners\outrigger-ed7-run\resource_estimate_ed7.json` | 단계별 자원 추정(compute-scheduler-expert에 넘길 데이터) |
| `C:\Users\jinbeom\.claude\runners\outrigger-ed7-run\audit_commands_ed7.txt` | 실행 전·중 감사 명령 목록 |

**설정 파일 내용**
- 스텝이 읽는 칸(`common_ed7.ps1` 98~99행)은 두 개뿐이다.
  - `run_commit` = `8a2a52ce2c07d2af11a6212a2932d2061261f156`
  - `worktree` = `C:\workspace\outrigger_control\.claude\worktrees\ed7-impl`
- 나머지는 `record` 블록에 넣었다. 스텝은 이 블록을 읽지 않고, 메인 세션 실행표와 감사용 기록으로만 쓴다.
  - 명세 판 7 rev 6: sha `10902ffd…`, 봉인 e241638d
  - 정오 1: sha `74c49bdaddf3…`, 커밋 265dc641
  - C의 부모 b46bdf8f, 03_src tree `0cffdbdf…`
  - T′ `60ebb4a4…`와 판정 worktree
  - 출력 루트 `j9_runs\8a2a52ce`
  - 판정 출력 루트, `main_checks` 루트
  - 입력 sha 7개(G1, 감도, L1 12b·12a, c92, c93): 모두 실측값과 정오 1-2 표가 같다.
  - 단계 순서, 실행 명령, 블라인드 경로
- 마스크·worker 자리표시는 12개다: `<ED7_MASK_T8>`·`<ED7_WORKERS_T8>`, 같은 꼴로 CASES·PROBE·CONFIRM·J9MAIN·SENS. 위치는 `record.placement`와 `record.launch_commands`다.

**pre10a 스크립트 시험**(출력은 scratchpad에 썼고 지금은 지움)
- `-Rehearsal` 정상: 종료 0. blob이 f9332882…/d323c25d…로 감사 값과 같았다.
- dg3 전에 `-Rehearsal` 없이: 종료 2
- 출력 파일이 이미 있음: 종료 2
- 기대 sha를 바꾼 사본: 종료 1

## 2. `check_ed7.ps1` 출력(그대로)
```
CHECK ok: 8a2a52ce2c07d2af11a6212a2932d2061261f156 (C:\workspace\outrigger_control\.claude\worktrees\ed7-impl), parent b46bdf8fdbad730eabf9226c5e1cfed0e980b5e9, 03_src 0cffdbdfc64f6a3daa855f5c2f2fdaf1c7dbf04f
check_ed7 exit=0
```
- 설정을 고친 뒤 한 번 더 돌렸고 같은 출력, 종료 0이었다.
- **자리표시 때문에 실패하는 항목: 없다.** `Get-Ed7ConfigProblem`은 `run_commit`·`worktree`에서만 `^<ED7_`를 찾는다. 마스크·worker 자리표시는 스텝이 읽지 않는 칸이라 check에 걸리지 않는다. 대신 아래 `placeholder_scan`으로 잡힌다.

**도구 종료 코드**

| 도구 | 범위 | 종료 코드 | 결과 |
|---|---|---|---|
| `ps1_lint` | run_steps_ed7 14개 + common·record_helper(16파일) | 0 | 문제 0 |
| `ps1_lint` | pre10a 스크립트 | 0 | 문제 0 |
| `placeholder_scan --pattern-set both` | 설정, `--allow` 12개 | 0 | allowed 24 |
| `placeholder_scan` | 설정, `--allow` 없이 | 1 | unfilled 27 |
| `placeholder_scan` | run_steps ps1 | 0 | 자리표시 0 |
| `worktree_locks --repo` | repo 전체 | 1 | 판 7과 무관한 stale 경고 2(imu-att, journal-v0) |
| `worktree_locks --worktree` | ed7-impl·ed7-judge | 0 | 둘 다 confirmed |

- `--allow` 없는 1회는 수정 전이다. 그때 문장 속 `<step>`·`<subcommand>`와 `<ED7_PRE10A_RECORD>`가 더 잡혔고, 셋은 문장 고침과 실제 경로로 없앴다. 지금 돌리면 24가 남는다.

## 3. 자원 표(판 6·판 5 runner sample/record 실측 기준, 결과 값은 읽지 않음)
단계는 앞 단계 `.done`이 있어야 시작하므로 서로 겹치지 않는다. 이 표로 compute-scheduler-expert 배치를 받으면 된다.

| # | 단계 | 줄 | 배치 | 프로세스 | CPU-s 추정 | wall 추정 | RSS 정점 | 근거 |
|---|---|---|---|---|---|---|---|---|
| 1 | impl_scope | 0 | 없음(git) | 1 | ~5 | ~30 s | 0.1 GB | – |
| 2 | l1ref | 167+167+102+102 키 | **C 고정** 0x000F/0x00F0/0x0F00/0xF000 ×4w | 28 | 48,400 | ~4,000 s | ~5.5 GB | 판 6 l1ref_a1(같은 키·마스크): wall 3,800/3,989/2,543/2,705 s, CPU 합 48,422, run당 1.1~1.3 GB |
| 3 | impl_t8 | 44 | 자리표시 | W+2 | 4,400 | ~270 s @20w | ~5 GB @20w | 판 6: 260 s, 4,319 CPU-s, 3.66 GB, 22개 |
| 4 | impl_cases | 10 | 자리표시(min(10,W)) | 12 | 1,100 | ~115 s | ~3 GB | 판 6: 113 s, 1,084, 2.18 GB |
| 5 | impl_probe | 114 | 자리표시 | W+2 | ~18,300 | ~900 s @20w | ~5.2 GB | b46bdf8f repro_a2(같은 114줄): wall 876 s @0xFFFFFFF(worker·CPU·RSS 미기록). 판 6 probe 40줄: 160 CPU-s/줄, 3.86 GB |
| 6 | confirm | G1 171 + D 24 | 자리표시(D는 min(24,W)) | W+2 | 22,000~31,500 | 1,300~1,900 s @20w | ~5.3 GB | 판 6 confirm_a 216줄 107/줄, confirm_b 192줄 161/줄, 3.7~3.9 GB |
| 7 | j9main | 388 | 자리표시 | W+2 | ~51,000 | ~3,100 s @20w | ~5.5 GB | 판 6 기록 B: 3,083 s, 50,678, 4.14 GB. 판 5: 2,967 s |
| 8 | sens | 460 | 자리표시 | W+2 | ~60,300 | ~3,650 s @20w | ~5.5 GB | 판 6 기록 B sens 184줄: 1,448 s, 24,073(131/줄)을 460줄로 환산(±25 %) |
| 9 | dg3 | 135 키 × VBM·VBM0 | **C 고정** 0x00FF/0xFF00 ×4w | 14 | ~17,500 | ~2,250 s | ~3.2 GB | 판 5 dg3_a1(같은 마스크): 2,236/2,205 s, 8,772/8,703, 1.44/1.35 GB |
| 10 | 12b_plan | 0 | 스텝 셸 안 도구 | 1 | 300~1,800(**미측정**) | 5~30분 | ~1.5 GB | 06_analysis json 전체와 필수 루트 4개(npz 포함)를 통째로 읽음 |
| 11 | 12b_vbkm0 base | b1+b2 | **C 고정** 0x000F/0x00F0 ×4w | 14 | ~26,600 | ~3,600 s | ~2.6 GB | 판 5 VBK0 b1/b2: 3,550/3,555 s, 13,752/12,846, 1.07/1.09 GB |
| (뒤) | b4 / vbkm | 블록당 | C 고정 ×4w | 7/블록 | ~13,500~14,000/블록 | ~3,600~3,800 s | ~1.3 GB/블록 | 판 5 VBK b1/b2: 3,757/3,748 s |

- 합계(1~11단계): CPU 약 250,000~260,000 s. 순수 실행 wall 약 5.4~6.0 h(판정·SUMS 대기 제외). 어느 단계도 RSS 6 GB를 넘지 않을 것으로 본다(RAM 31.7 GB).
- RSS 여유: 판 7 건식(M-c)에서 프로세스 하나가 320~336 MB였다(판 6은 200~290 MB). 그래서 20 worker 단계에 약 ×1.35 여유를 뒀다.
- 30분이 넘는 단계(l1ref, j9main, sens, dg3, 12b)는 `reserve.py` 예약 대상이다.

## 4. 실행 전 감사용 명령(전체는 `audit_commands_ed7.txt`)
```powershell
$py='C:\ProgramData\miniforge3\envs\python-dev\python.exe'; $t='C:\Users\jinbeom\.claude\tools\verif'
$main='C:\workspace\outrigger_control'; $wt="$main\.claude\worktrees\ed7-impl"; $wtj="$main\.claude\worktrees\ed7-judge"
# ps1_lint (기대 0)
& $py -I -B "$t\ps1_lint.py" --repo $wt '06_analysis/02_control/j_p3_cause/prelaunch_j9/run_steps_ed7/*.ps1' '06_analysis/02_control/j_p3_cause/prelaunch_j9/run_steps/common.ps1' '06_analysis/02_control/j_p3_cause/prelaunch_j9/run_steps/record_helper.ps1' --out <감사 scratch>\ps1_lint.md
& $py -I -B "$t\ps1_lint.py" --repo 'C:\Users\jinbeom\.claude\runners\outrigger-ed7-run' 'pre10a_c92c93_check.ps1' --out <감사 scratch>\ps1_lint_pre10a.md
# placeholder_scan: 배치 채우기 전(기대 0, placeholder_allowed 24) / 채운 뒤에는 --allow 없이(기대 0)
& $py -I -B "$t\placeholder_scan.py" --repo $main --pattern-set both '06_analysis/02_control/j_p3_cause/prelaunch_j9/ed7_run_config.json' --allow ED7_MASK_T8 ED7_WORKERS_T8 ED7_MASK_CASES ED7_WORKERS_CASES ED7_MASK_PROBE ED7_WORKERS_PROBE ED7_MASK_CONFIRM ED7_WORKERS_CONFIRM ED7_MASK_J9MAIN ED7_WORKERS_J9MAIN ED7_MASK_SENS ED7_WORKERS_SENS --out <감사 scratch>\placeholder_config.md
# worktree_locks (ed7 둘만이면 기대 0, repo 전체는 판 7 무관 stale 2로 1)
& $py -I -B "$t\worktree_locks.py" --repo $main --worktree $wt $wtj --out <감사 scratch>\worktree_locks_ed7.md
& $py -I -B "$t\worktree_locks.py" --repo $main --out <감사 scratch>\worktree_locks_all.md
# 1단계 직전: C 시작 점검(쓰기 없음, 기대 CHECK ok / 0)과 worktree 깨끗함
pwsh -NoProfile -File "$wt\06_analysis\02_control\j_p3_cause\prelaunch_j9\run_steps_ed7\check_ed7.ps1"
git -C $wt status --porcelain
# 10a 직전 c92·c93(정오 1-2 조건 1): 0 같음 / 1 다름(12b_plan 금지) / 2 너무 이르거나 늦음, 출력 있음 / 3 git 실패
pwsh -NoProfile -File 'C:\Users\jinbeom\.claude\runners\outrigger-ed7-run\pre10a_c92c93_check.ps1' -Out 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\8a2a52ce\main_checks\pre10a_c92c93_a1.json'
#   같은 내용을 손으로:
$c92='06_analysis/02_control/j_p3_cause/prelaunch_j9/ed5_inputs/x11/c92_keys.txt'; $c93='06_analysis/02_control/j_p3_cause/prelaunch_j9/ed5_inputs/x11/c93_keys.txt'
Get-FileHash -Algorithm SHA256 -LiteralPath "$main\$c92","$main\$c93"   # fa538512… / e5d1d52e…
git -C $main diff --quiet HEAD -- $c92 $c93; "diff-exit=$LASTEXITCODE"  # 0
git -C $main hash-object -- $c92 $c93; git -C $main rev-parse "HEAD:$c92" "HEAD:$c93"   # 두 쌍이 같아야 함
```

목록 파일에는 다음도 들어 있다.
- 정오 1-10: 각 `.done` 직후 `baseline_check.py write-sums --recursive <step 폴더>`, 판정 직전 `baseline_check.py sums <step>\SHA256SUMS --no-git`
- `log_errors.py <step>\logs`
- 정오 1-13: 첫 l1ref·dg3의 `key_presence.py --npz-dir …_t4h --array t_s,phase,jp3_t_s,jp3_class,jp3_plant_state,jp3_p_tr_Pa,jp3_used_bound_Pa`
- `run_hazards.py --check update`

## 5. 판정 출력 위치 제안(정오 1-18)
- 판정 `--out`: `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\8a2a52ce\judge_60ebb4a4\<하위 명령>_a<N>\`(정오 1-18의 예시 그대로). T′ worktree 밖이고 단계 폴더(`<step>_aN`) 밖이다.
- 메인 확인 기록(pre10a, SUMS 보고): `…\j9_runs\8a2a52ce\main_checks\`
- 판정 뒤마다 `git -C ed7-judge status --porcelain`이 비어 있는지 본다.
- 스텝 코드와 충돌하지 않는다: l1ref가 막는 폴더 이름은 `12b_*`·`dg3_*`뿐이고, `.stop` 탐색은 파일 이름 기준이다.

## 확인 필요
1. **마스크·worker는 설정 파일이 아니라 스텝 명령줄 인자다.** 템플릿에는 `run_commit`·`worktree`만 있다(판 6 `ed6_run_config.json`도 두 칸뿐). 그래서 `record.placement`·`launch_commands`의 값은 스텝이 읽지 않는다. 배치를 받아 채울 때 실제 실행 명령(`-MaskHex`·`-Workers`)과 같게 메인이 맞춰야 한다. 판 6처럼 두 칸만 두고 싶으면 `record` 블록을 지워도 check 결과는 같다.
2. **l1ref·dg3·12b 마스크는 C에 고정돼 있다.** 바꾸려면 C를 다시 커밋해야 한다.
   - l1ref는 4 worker를 논리 4개(코어 2개)에 둔다. 판 6에서 이 배치는 판 5(논리 8개)보다 wall이 1.7배였다.
   - 이 세 단계 동안 E 코어는 놀고, 단계 순서 규칙 때문에 다른 단계를 겹쳐 돌릴 수도 없다.
3. **판정·확인 기록이 12b 스캔에 들어간다.** 판정 출력과 `main_checks`가 `j9_runs\8a2a52ce` 아래에 있으면 12b_plan 스캔이 이를 읽는다(`--scan-required` 실행 루트, `--scan-root` 06_analysis 전체).
   - 판정 report 안의 r79 키는 실행 출력 키의 사본이라 seed는 바뀌지 않는다(정오 1-1 근거 4). 다만 `selection.json`의 파일 목록에는 이 파일들이 들어간다.
   - 06_analysis 아래 어디에 두어도 스캔 대상이라, 정오 예시 위치를 그대로 제안했다. 바꾸려면 06_analysis 밖이어야 한다.
4. **추정 근거가 약한 단계가 셋이다.**
   - 12b_plan: 자원 실측이 없다.
   - impl_probe: repro(b46bdf8f)는 worker 수·CPU·RSS가 기록되지 않았다.
   - sens: 판 6 기록 B의 184줄(설정 구성이 다름)을 환산한 값이다.

## 메인 세션 권고
- 본 실행 1~11단계: 순수 실행 약 5.4~6.0 h다. 먼저 위 자원 표로 compute-scheduler-expert 배치를 받는다.
- 다음에 `placement` 자리표시를 채우고 `placeholder_scan`을 `--allow` 없이 돌려 0인지 본다. 그 뒤 실행 전 감사(verif-protocol-auditor)를 거쳐 메인이 띄운다(`pwsh -NoProfile -File`, `-NoExit` 금지).
- 각 단계가 끝날 때마다 SUMS(1-10)를 만들고, 10a 직전에 pre10a 확인을 한다.

## 공개(블라인드 절차)
- 블라인드 경로(`606f8713\cdry_a1\VBK_c92*`·`VBK_c93*`·`cdry_a1\logs\`, 판 6 `ed6_inputs\x11\selection.json`, worktree 사본)는 Read·Grep·Glob·스캔하지 않았다.
- 상위 폴더를 비재귀로 한 번씩 본 것이 둘 있다.
  - `j9_runs\606f8713` 최상위 목록: 폴더·파일 이름만 보였고, `cdry_a1` 안쪽은 열지 않았다.
  - `j_p3_cause` 최상위에서 `jp3_remedy_spec_v7*` 이름 필터: 명세 4개 파일 이름만 보였다.
- 그 밖에 읽은 것은 모두 경로를 직접 지정했다.
  - runner `*.record.json`·`*.sample.json`의 자원 필드: 판 6 79495405 단계 폴더와 records_after_stop, 판 5 606f8713의 l1ref·t8·cases·casef·j9main·dg3·12b·p1·records(cdry 제외), p51_record, dry_mc
  - identity의 시각, progress의 계획 수, 판 6 jsonl의 줄 수
- 결과 값은 읽거나 출력하지 않았다.

사용한 스킬: 없음. scratchpad 하위 폴더 `python-ed7run\`는 지웠다.
