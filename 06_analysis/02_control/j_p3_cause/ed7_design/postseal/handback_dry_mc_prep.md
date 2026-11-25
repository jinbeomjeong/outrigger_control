## M-c 건식 확인 준비 (실행 없음, 커밋 없음)

러너와 점검 스크립트를 만들었다. **Chrono 실행은 하지 않았다.** C에서 건식 인자 확인 두 가지만 돌렸다(아래). 출력 폴더 `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\dry_mc_8a2a52ce\`는 아직 없다. C worktree는 확인 뒤에도 미추적 파일까지 0으로 clean이다.

### 1. 만든 파일 (`C:\Users\jinbeom\.claude\runners\outrigger-ed7-dry-mc\`)

**`run_dry_mc.ps1`**: C(8a2a52ce, `ed7-impl`, 고치지 않음)의 판 7 실행 경로 그대로 세 묶음을 동시에 띄운다.

| 묶음 | 키·job | 실행 꼴 |
|---|---|---|
| `L1_VBM` | r79 l1ref, `L1\|s0\|g8\|38\|main\|flat\|top\|4.0\|FR\|raised\|200.0` | `step_l1ref_ed7.ps1`과 같음 |
| `L1_VBM0` | 같은 키 | 같음 |
| `ed7_t8` | 1쌍: R12 top-FL-Fs8 o0.0 × VBM·VBM0 | `step5_impl_ed7.ps1 -Part t8`에 `--one-per-setting`을 더함 |

- **키 선택 근거**: l1ref 키는 `l1_keys_12b.txt`(167개) 가운데 판 6 L1 실행에서 가장 짧았던 키다(54 s; 중앙 103 s, 최대 148 s). 읽은 것은 키 이름과 wall_s뿐이다. t8 쌍은 C의 `run_v5`가 `--one-per-setting`으로 고르는 첫 p3 job이다.
- **실행 조건**(run steps와 같음):
  - `dynamics-dev\python.exe -I -B`, 작업 폴더는 C worktree
  - 스레드 변수 1·TBB, `R72_PATH=per_leg`, `LAS_T3_DG3_LAS/K1/P3=on`, `R79_ROD_MODEL=plant_truth`
  - r79 실행은 `jp3_run_identity.py wrap`으로 감싼다
  - `R79_/R72_/R67_/LAS_T3_` 잔여 변수를 지운다
- **run steps와 다른 점 하나(기록함)**: `NUMBA_CACHE_DIR`를 출력 폴더 안으로 두었다. C worktree에 쓰지 않기 위해서이고, 결과에는 영향이 없다. 대신 numba 컴파일이 처음부터 다시 되므로 시간이 조금 는다.
- **거부 조건**: 출력 경로가 이미 있거나 C worktree·`j9_runs\8a2a52ce` 아래면 종료 2. C의 HEAD·tracked clean·03_src tree(`0cffdbdf`)가 맞지 않거나, `l1_keys_12b.txt`(`9f815533…`)·`main.jsonl`(`9ad74990…`) sha가 다르면 종료 3.
- **출력**: `runs\`에 다음을 쓴다.
  - `L1_VBM.json`·`L1_VBM0.json`과 `_t4h\`, identity sidecar
  - `ed7_t8.jsonl`과 `ed7_t8_t4h\`
  - `l1_keys_dry.txt`
  - `logs\`(log·err, cpu-scheduler `sample.py` 실측)
- 루트의 `run_record.json`에 시작·끝 C 정체성, 명령, 환경, 종료 코드를 남긴다. 종료 코드는 0 정상, 3 실행 실패 또는 C 변경이다.

**`check_dry_mc.py`**(python-dev): 러너가 끝난 뒤 돌린다. 모든 출력은 `<root>\judge\`에 쓰고(`runs\` 밖), 이미 있으면 거부한다.
1. `run_record.json`을 확인하고 stand-in `judge\stand_in_runs.done`을 만든다: folder = `runs\`, exit 0, commit C, 끝 정체성.
2. `key_presence.py`를 키·배열 목록은 감사 원문 M-c 그대로 두고 네 묶음에 돌린다. 값은 출력하지 않는다. 묶음은 r79 VBM, r79 VBM0, t8 VBM(`--where job.setting=VBM`, `*_VBM.npz`), t8 VBM0이다. 원래 없는 것만 허용한다.
   - ③ 끔(VBM0 두 묶음): `hydraulics_record.extend_bound_check`, `run_extend_start_revision`, `jp3_*` 5종
   - t8 VBM: `run_extend_start_revision`(run_v5 줄은 태그에만 담는다)
   - null 값도 결측으로 센다.
3. T′ worktree(HEAD `60ebb4a4`·clean 단언)에서 `jp3_ed7_judge.py`의 `l1ref`(L1_VBM·L1_VBM0)와 `t8`을 stand-in `.done`으로 돌린다.
   - **두 판정의 status는 not_judgeable이 정상이다**: l1ref는 L1a 두 개가 없고, t8은 22 job 중 1 job뿐이다.
   - 점검이 읽는 것은 정체성 결과뿐이다.
4. 요약은 `judge\dry_mc_summary.json`, stdout 끝줄은 status·건수만 담는다.

**성공 기준(`status: pass`, 종료 0)**: 다음을 모두 만족해야 한다. 하나라도 어기면 종료 1, 입력 오류는 2, 도구 오류는 3이다.
- 실행 기록이 clean이다.
- 예상 밖 결측 키·배열이 0이다.
- l1ref 두 run의 정체성 문제가 0이다.
- t8 정체성 결함이 0이다.
- t8 쌍이 판정 1쌍이거나 fallback 기록 1쌍이다.

### 2. 실행 명령 (메인)
```powershell
# 1) 러너 (마스크는 배치표대로; r79 각 1코어, t8 2코어)
& "C:\Program Files\PowerShell\7\pwsh.exe" -File C:\Users\jinbeom\.claude\runners\outrigger-ed7-dry-mc\run_dry_mc.ps1 -MaskVBM <hex> -MaskVBM0 <hex> -MaskT8 <hex> [-T8Workers 2]
# 2) 점검 (러너 종료 0 뒤)
& C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B C:\Users\jinbeom\.claude\runners\outrigger-ed7-dry-mc\check_dry_mc.py --root C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\dry_mc_8a2a52ce
```
pwsh 경로는 이 PC의 실제 pwsh 경로로 바꿔 넣는다.

### 3. 예상 시간 (compute-scheduler-expert 입력)
| 묶음 | 코어 | CPU 시간 어림 | 벽시계 어림 | 근거 |
|---|---|---|---|---|
| L1_VBM | 1 | 2~3 분 | 2~3 분 | 판 6 같은 키 54 s + 프로세스 시작·빈 캐시 numba 컴파일(어림 1~2 분) |
| L1_VBM0 | 1 | 2~3 분 | 2~3 분 | 같음 |
| ed7_t8 | 2 | 5~7 분 | 3~5 분 | 판 6 같은 job: VBL 160 s, VBL0 142 s + 컴파일 |
| 점검 | 1 | 1~2 분 | 1~2 분 | key_presence 8회 + 판정 2개 |

- 합계 CPU 약 10~15 CPU·분, 동시에 4코어면 벽시계 약 5~6 분이다. 마감은 없다.
- 메모리는 프로세스당 1 GB 안팎으로 어림하고, 합계 6 GB 미만이다. 실측은 `runs\logs\*.sample.json`에 남는다.

### 4. 한 검증
- C 건식 인자 확인: `run_v5.py ed7_t8 --p3-hash-source … --one-per-setting --out <scratch> --list` → "2 runs, 2 to do", 출력 파일은 생기지 않음. `r79_L3L4_final.py … list --levels L1` → 167 jobs. 확인 뒤 C 상태 0건.
- 러너 ps1은 PowerShell 파서 오류 0이다.
- `key_presence` json 필드(`keys[].key/absent/missing`, `npz.arrays[].array/absent`, `summary.selected`)와 `--where` 동작을 작은 표본으로 확인했다.
- ruff(BLE001 하나는 의도한 것이라 noqa), codespell 0건이다.
- **점검 스크립트의 본 경로는 판 7 r79·t8 실출력으로 돌려 보지 못했다**(그 출력이 이번 건식 실행으로 처음 생긴다). 입력 오류 경로(run_record 없음 → 종료 2, judge 폴더를 만들지 않음)만 확인했다.

### 5. 확인 필요
- 점검 스크립트가 쓰는 `judge\`는 dry 폴더 안이고 판정 단계 폴더가 아니다(M-5의 대상 밖). 이 건식 출력은 판정에 쓰지 않는 기록이다.
- `NUMBA_CACHE_DIR`를 바꾼 것이 "C 실행 경로 그대로"에서 허용되는 차이인지 메인이 판단하기 바란다. 바꾸지 않으면 numba 캐시가 C worktree 아래에 쓰일 수 있다(미추적이라 `--untracked-files=no` 정체성은 그대로지만 "C worktree 안에 쓰지 않음" 조건과 어긋난다).

### 6. 공개(블라인드 절차)
- 경로를 지정해 읽은 것: 감사 원문 M-c 절, C run steps·`run_v5`·`las_t3_dg3`·`r79_L3L4_final`, `79495405/l1ref_a1/L1_VBL.json`(key·wall_s만), `79495405/impl_t8_a1/ed6_t8.jsonl`(job·wall_s만).
- 디렉터리 목록은 `79495405/impl_t8_a1`만 봤다.
- 블라인드 경로, 판 6 `selection.json`, 상위 루트 검색은 쓰지 않았다.
- scratchpad `python-ed7mc`는 지웠다.

사용한 스킬: 없음
