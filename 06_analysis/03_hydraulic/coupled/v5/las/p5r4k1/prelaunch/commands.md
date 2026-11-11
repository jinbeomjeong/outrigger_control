# LAS-b P5r4 + K1 실행 전 기록: 실행 명령 목록

- 규칙: `las_p5r4_k1_rules.md`(`5ee2bac0…`) + rev1(`f39846d6…`) + rev2(`e0a7d1e5…`) + rev3(`31ba01df…`)와 0절 표의 이어받는 규칙 10개. sha 전체 값은 `manifest.json` `rules`에 있다. rev3는 두 판정 경로가 K-0에서 대조하고, 실행 도구의 줄·행 기록 목록에는 넣지 않는다(RV3-5).
- 작성: python-expert(경로 1), 2026-11-11. master `a916e04`(rev3 판정 도구·경로 2 병합) 기준으로 갱신했다. **이 문서의 명령은 하나도 실행하지 않았다.** 다만 `gs_list.json`·`chrono_rows_main.json`은 행 목록만 생성했다(시뮬레이션 0건).
- 실행 HEAD: `{RUN_HEAD}`. 실행 checkout은 main checkout `C:\workspace\outrigger_control`이고 cwd도 그 루트다.
- **prelaunch 추적 해제(rev3 RV3-3)**: 이 폴더 `06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/prelaunch/`는 실행 HEAD 커밋에서 git 추적을 해제한다(`git rm --cached` + `.git/info/exclude`에 그 폴더 줄). 16.4 자리표시(`{RUN_HEAD}`, `{BATCH_GS}`, `{BATCH_CHRONO}`, `{POSTRUN_HEAD}`, `{JUDGE_COMMIT}`)는 그 뒤 **추적 밖이 된 이 폴더 파일에** 채운다. `{RUN_HEAD}`에는 메인 세션이 실행 HEAD 커밋 id를 채운다(실행 전 감사 2 전). 판정서에는 채운 파일마다 채우기 전 blob·sha와 채운 뒤 raw sha를 적는다.
- sha 규약: 이 문서와 `manifest.json`의 도구·스케줄·계획 파일 sha는 **LF 내용 sha256**이다(main checkout은 `-text`라 작업 트리 = LF). 규약은 `manifest.json` `sha_conventions`에 있다.
- 배치(코어 배정)는 compute-scheduler-expert 배치표(2026-11-11, 메인 세션 전달)로 채웠다.

| 단계 | 풀 | affinity | 동시 실행·옵션 |
|---|---|---|---|
| G-S 하네스 117줄 | ecore | `0x0FFF0000` | `--workers 12` |
| G-S Chrono 12행 | 12행 모두 pcore | s9_batch가 풀로 정함 | `--parallel 4 --schedule prelaunch/sched_gs.json` |
| 본 하네스 6묶음 | P+E 혼합(마스크) | `0x0FFF5555`(P 물리 8 + E 12) | `--workers 20` |
| 본 Chrono 12행 | 12행 모두 pcore(원판 4.3 계획 풀 P, rev3 RV3-4) | 풀로 정함 | `--parallel 4 --schedule prelaunch/sched_main.json`(예상 7~7.5 h) |

- 스케줄·계획 파일 sha256(LF 내용): `sched_gs.json` `8450a86281bdd2edfeea85c3f46ac62e77b925e3c544c211d9347cd7be9aeb1f`, `sched_main.json` `1b086744406b6413555acf7fc839a684da4958a364a71fd5ccf0247a9d33f5c8`, `chrono_batch_plan.json` `ae1cd38f7187366a1ac3268aadd7e6e50eec8dd377d791e0235b33eb393bb6be`(`manifest.json` `schedules`·`chrono_batch_plan`).
- 셸: PowerShell. Python은 아래 인터프리터 절대경로로 직접 부른다(`conda run` 쓰지 않음: dynamics-dev는 `conda run`과 직접 실행의 해시가 다를 수 있다).

## 0. 인터프리터·공통 env

| 용도 | 인터프리터 | 비고 |
|---|---|---|
| 하네스 실행 도구 | `C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B` | 저장 기준 파일을 만든 도구와 같은 호출 꼴. 도구가 `MKL_NUM_THREADS`·`OMP_NUM_THREADS`·`OPENBLAS_NUM_THREADS`·`NUMBA_NUM_THREADS`를 1로 덮어쓰고 `MKL_THREADING_LAYER`는 없으면 `TBB`(16.5) |
| Chrono 배치 | `C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe -I -X utf8 -u` | `s9_batch`가 행마다 `OMP_WAIT_POLICY=PASSIVE`, `OUTRIGGER_HULL_HOOK=fast`(행 키 `start_env`), `OUTRIGGER_PLACEMENT`(풀)를 자식 env에 넣는다. 호출 셸에 다른 값을 두지 않는다. `--threads 4`(`run_S9.SCM_THREADS_FIXED`)는 행 argv에 있다 |
| 판정·점검 도구 | `C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B` | 표준 라이브러리만 |

- 셸 env 조항(16.5): `OMP_WAIT_POLICY` 없거나 `PASSIVE`, `OUTRIGGER_HULL_HOOK` 없거나 `fast`, `OUTRIGGER_HULL_HOOK_DLL` 없음, `OUTRIGGER_HULL_HOOK_ALLOW_UNVALIDATED` 없음, `OUTRIGGER_HULL_HOOK_DUMP*` 없음. 실행 직전 `Get-ChildItem env:OUTRIGGER*, env:OMP*, env:MKL*`로 확인해 이 기록 옆에 남긴다.
- DLL `03_src/outrigger_sim/native/chrono_hull/bin/chrono_hull_hook.dll` sha256 `cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15`(git 제외 파일, Chrono 판정 도구 prelaunch가 기록).
- 판정 도구 기대 sha(LF 내용 = main checkout 작업 트리): 하네스 판정 `las_p5r4k1_judge.py` `d07888ba3993b90978d3e3481ec76753920aa720f5643dca3cefef4f259e5aab`, Chrono 판정 `las_p5r4k1_chrono_judge.py` `0b357e386db2de8e3a1e95a254ddbc3ba462c6d509a4abc1e7d3cebee4ac1e73`, G-S 도구 `las_p5r4k1_gs.py` `03d1d0bb06fdf0bb8146c238bcbb315c571930e99508b76f79a0e4b6d33416db`.

## 1. G-S 하네스 (16.2 (가), 117줄, 출력 `v5/las/p5r4k1/gs/p5k_GS_<묶음>.jsonl`)

목록 `prelaunch/gs_list.json`, 하네스 목록 sha256 `41157880063e171fb35b1fb664d22b59923325b4602da0a92edda8e107851dc3`. 묶음마다 한 번씩 돌린다(줄 수: Z-0 6, Z-A 6, Z-T 16, Z-S 24, Z-C 64, Z-X 1). 로그는 묶음마다 파일로 남긴다(16.3).

```powershell
$py = "C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe"
$gs = "06_analysis\03_hydraulic\coupled\v5\las\p5r4k1\prelaunch\gs_list.json"
foreach ($b in "Z-0","Z-A","Z-T","Z-S","Z-C","Z-X") {
  & $py -I -B 04_scripts/04_hydraulic/coupled/las_p5r4k1_targeted.py run --bundle $b `
      --gs-list $gs --workers 12 --affinity 0x0FFF0000 2>&1 |
      Tee-Object -FilePath "06_analysis\03_hydraulic\coupled\v5\las\p5r4k1\gs\run_GS_$b.log"
}
```

점검(값을 출력하지 않음):

```powershell
& "C:\ProgramData\miniforge3\envs\python-dev\python.exe" -I -B 06_analysis/02_control/verif_matrix/scripts/las_p5r4k1_gs.py check `
    --list 06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/prelaunch/gs_list.json `
    --log (Get-ChildItem 06_analysis\03_hydraulic\coupled\v5\las\p5r4k1\gs\run_GS_*.log).FullName `
    --out 06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/prelaunch/gs_check_harness.json
& "C:\ProgramData\miniforge3\envs\python-dev\python.exe" -I -B C:\Users\jinbeom\.claude\tools\verif\log_errors.py `
    06_analysis\03_hydraulic\coupled\v5\las\p5r4k1\gs --glob "run_GS_*.log" --require-line
```

## 2. G-S Chrono (16.2 (나), 12행, 배치 `V5-LAS-P5R4-K1-GS`, `--duration 10`)

행 목록은 `gs_list.json` `chrono`(argv 포함, 목록 sha256 `9d3a5f200daa6559e0e5abbbe1b421df9d1972be987428bc32f27391b7083602`, main checkout 행 모듈 + Chrono-dev로 생성). 출력 폴더 `07_results/S9/batch_V5-LAS-P5R4-K1-GS_<시각>/` = `{BATCH_GS}`(시작 직후 채움).

```powershell
& "C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe" -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py run V5-LAS-P5R4-K1-GS --parallel 4 --schedule 06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/prelaunch/sched_gs.json
& "C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe" -I -X utf8 -u 04_scripts/02_chrono/las_p5r4_k1_chrono_rows.py gs-check {BATCH_GS}
& "C:\ProgramData\miniforge3\envs\python-dev\python.exe" -I -B 06_analysis/02_control/verif_matrix/scripts/las_p5r4k1_chrono_judge.py `
    --rules-rev3 06_analysis/02_control/verif_matrix/las_p5r4_k1_rules_rev3.md `
    --out 06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/prelaunch/gs_fields_chrono.json fields --batch {BATCH_GS}
& "C:\ProgramData\miniforge3\envs\python-dev\python.exe" -I -B C:\Users\jinbeom\.claude\tools\verif\log_errors.py `
    {BATCH_GS}\progress.log --pattern "\brc=(\d+)" --require-line
```

- G-S Chrono는 12행 모두 P 풀(`sched_gs.json`: `e_cases` 없음, `parallel_p` 4). 짝은 같은 풀 종류(K-6).

## 3. 실행 전 기록과 감사 (11.5 E-6·E-7·E-10)

```powershell
& "C:\ProgramData\miniforge3\envs\python-dev\python.exe" -I -B 06_analysis/02_control/verif_matrix/scripts/las_p5r4k1_chrono_judge.py `
    --rules-rev3 06_analysis/02_control/verif_matrix/las_p5r4_k1_rules_rev3.md prelaunch `
    --batch-plan 06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/prelaunch/chrono_batch_plan.json `
    --audit-report 06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/prelaunch/p5k_prelaunch_audit.md `
    --path2-sha p5k_recount.py=1b85aacca3b74e01cf5223c7f45b8962edbcbba7 p5k_chrono_recount.py=8888336ec58a736b9b637583d69636f98e897232 test_p5k_recount.py=1f00d1eddabaff85189d7139e0b602d664eb2db3 `
    --gs-list-sha 41157880063e171fb35b1fb664d22b59923325b4602da0a92edda8e107851dc3
& "C:\ProgramData\miniforge3\envs\python-dev\python.exe" -I -B C:\Users\jinbeom\.claude\tools\verif\placeholder_scan.py `
    --repo C:\workspace\outrigger_control "06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/prelaunch/*.json" `
    "06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/prelaunch/*.md"
```

- 감사 리포트는 verif-protocol-auditor `[시점] 실행 전` 원문을 `p5k_prelaunch_audit.md`로 저장한 뒤 prelaunch를 돌린다(K-0). `--path2-sha` 값은 경로 2 git blob(파일 내용을 열지 않고 `git rev-parse HEAD:<path>`로 얻음).
- prelaunch 출력: `v5/las/p5r4k1/p5k_chrono_prelaunch.json`.
- 자리표시 점검(16.4, rev3 RV3-3 5)의 대상은 채운 뒤의 추적 밖 prelaunch 파일 전부(`commands_path2.md` 포함)다. 판정 전에는 `placeholder_unfilled` 0이어야 한다.

## 4. 하네스 본 실행 (4.2 순서, 출력 `v5/las/p5r4k1/p5k_<묶음>.jsonl`)

Z-0 → Z-A → Z-T·Z-S·Z-C → Z-X. 도구가 앞 묶음 비트 예측(BT-0·BT-A)과 정체성을 확인한 뒤에만 시작한다(S-2). Z-X 대상이 10개를 넘으면 도구가 종료 2로 멈춘다(RV2-6: 묻는다).

```powershell
$py = "C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe"
foreach ($b in "Z-0","Z-A","Z-T","Z-S","Z-C","Z-X") {
  & $py -I -B 04_scripts/04_hydraulic/coupled/las_p5r4k1_targeted.py run --bundle $b `
      --workers 20 --affinity 0x0FFF5555 2>&1 |
      Tee-Object -FilePath "06_analysis\03_hydraulic\coupled\v5\las\p5r4k1\run_$b.log"
  # 각 묶음 뒤(rev3 RV3-2): 묶음 줄 파일의 errors_left(정상 줄이 하나도 없는 (팔, 키)의 수)가 0이면 다음 묶음으로 진행한다.
  # 첫 시도 오류(errors N > 0, attempt 2로 회복)는 판정서에 기록한다. errors_left > 0이면 멈춘다(S-9).
  # errors_left는 실행 도구 요약 JSON의 "errors_left"(또는 판정 도구 completeness)로 본다. 종료 코드만으로 판단하지 않는다.
}
```

- 오류 키 재실행(10.1, 1회): `run --bundle <묶음> --resume` → `p5k_<묶음>_resume.jsonl`(rev3 RV3-2는 같은 파일 안의 attempt 2만 다룬다. resume 파일은 앞 판 그대로).
- 실제로는 Z-T·Z-S·Z-C를 배치표대로 동시에 띄울 수 있다. 위 반복문은 순서만 보인다.

## 5. 하네스 판정 (경로 1)

```powershell
& "C:\ProgramData\miniforge3\envs\python-dev\python.exe" -I -B 06_analysis/02_control/verif_matrix/scripts/las_p5r4k1_judge.py `
    --expect-judge-sha d07888ba3993b90978d3e3481ec76753920aa720f5643dca3cefef4f259e5aab `
    --rules-rev3 06_analysis/02_control/verif_matrix/las_p5r4_k1_rules_rev3.md `
    --out 06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/judge_p5k_harness.json
```

- `--expect-judge-sha`는 하네스 판정 도구의 LF 내용 sha256이다. main checkout은 `-text`라 작업 트리 raw = LF이므로 이 값이 곧 작업 트리 sha다. 판정 커밋은 `{JUDGE_COMMIT}`.
- 판정 전 관문(16.3·16.4, rev3 RV3-2 5): 모든 묶음 `errors_left` 0, `placeholder_scan.py` `placeholder_unfilled` 0. 하네스가 `통과`가 아니면 Chrono를 시작하지 않는다(S-6).

## 6. Chrono 본 실행 (4.3, 12행, 배치 `V5-LAS-P5R4-K1`, P 전용)

행 목록 `chrono_rows_main.json`(목록 sha256 `3fdbf80ee426cb9ef4eeab13d5943d08fbef9b89d9a2ef230f13ce45c4f8de3c`). 12행 모두 pcore, `--parallel 4`(4행 × 4스레드), 예상 7~7.5 h. 출력 폴더 `{BATCH_CHRONO}`(시작 직후 15분 안에 채움).

```powershell
$py = "C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe"
$cs = "C:\Users\jinbeom\.claude\tools\cpu-scheduler"
$pd = "C:\ProgramData\miniforge3\envs\python-dev\python.exe"
Get-ChildItem env:OUTRIGGER*, env:OMP*, env:MKL*
$env:OMP_WAIT_POLICY = "PASSIVE"
& $pd -I "$cs\reserve.py" prune
$p = Start-Process -FilePath $py -PassThru -NoNewWindow -WorkingDirectory C:\workspace\outrigger_control -ArgumentList @("-I","-X","utf8","-u","04_scripts/02_chrono/s9_batch.py","run","V5-LAS-P5R4-K1","--parallel","4","--schedule","06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/prelaunch/sched_main.json")
$r = & $pd -I "$cs\reserve.py" add --owner "V5-LAS-P5R4-K1" --mask 0xFFFF --pid $p.Id --ttl-min 600 --note "P 4x4 threads, 12 rows, est 7-7.5 h"
```

점검:

```powershell
& "C:\ProgramData\miniforge3\envs\python-dev\python.exe" -I -B C:\Users\jinbeom\.claude\tools\verif\log_errors.py `
    {BATCH_CHRONO}\progress.log --pattern "\brc=(\d+)" --require-line
```

- 배치가 끝나면 `reserve.py release --id <$r의 id>`로 예약을 푼다. 예상보다 길어지면 만료 전에 `renew`.

## 7. postrun과 Chrono 판정 (경로 1)

```powershell
& "C:\ProgramData\miniforge3\envs\python-dev\python.exe" -I -B 06_analysis/02_control/verif_matrix/scripts/las_p5r4k1_chrono_judge.py `
    --rules-rev3 06_analysis/02_control/verif_matrix/las_p5r4_k1_rules_rev3.md postrun --batch {BATCH_CHRONO}
& "C:\ProgramData\miniforge3\envs\python-dev\python.exe" -I -B 06_analysis/02_control/verif_matrix/scripts/las_p5r4k1_chrono_judge.py `
    --rules-rev3 06_analysis/02_control/verif_matrix/las_p5r4_k1_rules_rev3.md judge --batch {BATCH_CHRONO} `
    --expect-tool-sha 0b357e386db2de8e3a1e95a254ddbc3ba462c6d509a4abc1e7d3cebee4ac1e73 `
    --rem-batch 07_results/S9/batch_V5-LAS-K1-REM_20261109_235554
```

- postrun HEAD는 `{POSTRUN_HEAD}`로 기록한다. Chrono 판정 도구의 K-0은 `--expect-tool-sha`를 prelaunch·postrun·judge가 잰 작업 트리 sha256과 그대로 비교한다. main checkout은 `-text`라 작업 트리 = LF이므로 위 LF 값과 같다.
- 경로 2(`p5k_path2/`)의 실행 명령은 control-expert가 정한다(`commands_path2.md`). 이 문서는 그 blob만 고정한다(`manifest.json` `path2_tools_git_blob`).
