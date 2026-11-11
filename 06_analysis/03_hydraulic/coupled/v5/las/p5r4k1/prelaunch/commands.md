# LAS-b P5r4 + K1 실행 전 기록: 실행 명령 목록

- 규칙: `las_p5r4_k1_rules.md`(`5ee2bac0…`) + rev1(`f39846d6…`) + rev2(`e0a7d1e5…`)와 0절 표의 이어받는 규칙 10개. sha 전체 값은 `manifest.json` `rules`에 있다.
- 작성: python-expert(경로 1), 2026-11-11. **이 문서의 명령은 하나도 실행하지 않았다.** 다만 `gs_list.json`·`chrono_rows_main.json`은 행 목록만 생성했다(시뮬레이션 0건).
- 실행 HEAD: `{RUN_HEAD}`. 실행 checkout은 main checkout `C:\workspace\outrigger_control`이고 cwd도 그 루트다.
- 배치(코어 배정)는 compute-scheduler-expert 배치표(2026-11-11, 메인 세션 전달)로 채웠다.

| 단계 | 풀 | affinity | 동시 실행·옵션 |
|---|---|---|---|
| G-S 하네스 117줄 | ecore | `0x0FFF0000` | `--workers 12` |
| G-S Chrono 12행 | 12행 모두 pcore | s9_batch가 풀로 정함 | `--parallel 4 --schedule prelaunch/sched_gs.json` |
| 본 하네스 6묶음 | P+E 혼합(마스크) | `0x0FFF5555`(P 물리 8 + E 12) | `--workers 20` |
| 본 Chrono 12행 | A1~A4·B1·B2·C1·C2 pcore, A5·A6·C3·C4 ecore(짝 6쌍 같은 풀, K-6) | 풀로 정함 | `--parallel 4 --parallel-e 3 --schedule prelaunch/sched_main.json` |

- 스케줄 파일 sha256(복사 시점 raw): `sched_gs.json` `8450a86281bdd2edfeea85c3f46ac62e77b925e3c544c211d9347cd7be9aeb1f`, `sched_main.json` `7e499ba82b8e3c718b8de95133b7464a9ee738150e18775481ac99cc91f9e2ac`(`manifest.json` `schedules`).
- 셸: PowerShell. Python은 아래 인터프리터 절대경로로 직접 부른다(`conda run` 쓰지 않음: dynamics-dev는 `conda run`과 직접 실행의 해시가 다를 수 있다).

## 0. 인터프리터·공통 env

| 용도 | 인터프리터 | 비고 |
|---|---|---|
| 하네스 실행 도구 | `C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B` | 저장 기준 파일을 만든 도구와 같은 호출 꼴. 도구가 `MKL_NUM_THREADS`·`OMP_NUM_THREADS`·`OPENBLAS_NUM_THREADS`·`NUMBA_NUM_THREADS`를 1로 덮어쓰고 `MKL_THREADING_LAYER`는 없으면 `TBB`(16.5) |
| Chrono 배치 | `C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe -I -X utf8 -u` | `s9_batch`가 행마다 `OMP_WAIT_POLICY=PASSIVE`, `OUTRIGGER_HULL_HOOK=fast`(행 키 `start_env`), `OUTRIGGER_PLACEMENT`(풀)를 자식 env에 넣는다. 호출 셸에 다른 값을 두지 않는다. `--threads 4`(`run_S9.SCM_THREADS_FIXED`)는 행 argv에 있다 |
| 판정·점검 도구 | `C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B` | 표준 라이브러리만 |

- 셸 env 조항(16.5): `OMP_WAIT_POLICY` 없거나 `PASSIVE`, `OUTRIGGER_HULL_HOOK` 없거나 `fast`, `OUTRIGGER_HULL_HOOK_DLL` 없음, `OUTRIGGER_HULL_HOOK_ALLOW_UNVALIDATED` 없음, `OUTRIGGER_HULL_HOOK_DUMP*` 없음. 실행 직전 `Get-ChildItem env:OUTRIGGER*, env:OMP*, env:MKL*`로 확인해 이 기록 옆에 남긴다.
- DLL `03_src/outrigger_sim/native/chrono_hull/bin/chrono_hull_hook.dll` sha256 `cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15`(git 제외 파일, Chrono 판정 도구 prelaunch가 기록).

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
    --out 06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/prelaunch/gs_fields_chrono.json fields --batch {BATCH_GS}
& "C:\ProgramData\miniforge3\envs\python-dev\python.exe" -I -B C:\Users\jinbeom\.claude\tools\verif\log_errors.py `
    {BATCH_GS}\progress.log --pattern "\brc=(\d+)" --require-line
```

- G-S Chrono는 12행 모두 P 풀(`sched_gs.json`: `e_cases` 없음, `parallel_p` 4). 짝은 같은 풀 종류(K-6).

## 3. 실행 전 기록과 감사 (11.5 E-6·E-7·E-10)

```powershell
& "C:\ProgramData\miniforge3\envs\python-dev\python.exe" -I -B 06_analysis/02_control/verif_matrix/scripts/las_p5r4k1_chrono_judge.py prelaunch `
    --batch-plan 06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/prelaunch/chrono_batch_plan.json `
    --audit-report 06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/prelaunch/p5k_prelaunch_audit.md `
    --path2-sha p5k_recount.py=41a2bf0dc81e1eaa28bb9365df6b7ae0928d47da p5k_chrono_recount.py=d73ad2b5606e152283bf5ef3bf8cedab95f6939e test_p5k_recount.py=9a189c7312db6388f6c5bd77b653bc3e62d4d990 `
    --gs-list-sha 41157880063e171fb35b1fb664d22b59923325b4602da0a92edda8e107851dc3
& "C:\ProgramData\miniforge3\envs\python-dev\python.exe" -I -B C:\Users\jinbeom\.claude\tools\verif\placeholder_scan.py `
    --repo C:\workspace\outrigger_control "06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/prelaunch/*.json" `
    "06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/prelaunch/*.md" --allow POOL MASK WORKERS
```

- 감사 리포트는 verif-protocol-auditor `[시점] 실행 전` 원문을 `p5k_prelaunch_audit.md`로 저장한 뒤 prelaunch를 돌린다(K-0). `--path2-sha` 값은 경로 2 git blob(파일 내용을 열지 않고 `git rev-parse HEAD:<path>`로 얻음).
- prelaunch 출력: `v5/las/p5r4k1/p5k_chrono_prelaunch.json`.

## 4. 하네스 본 실행 (4.2 순서, 출력 `v5/las/p5r4k1/p5k_<묶음>.jsonl`)

Z-0 → Z-A → Z-T·Z-S·Z-C → Z-X. 도구가 앞 묶음 비트 예측(BT-0·BT-A)과 정체성을 확인한 뒤에만 시작한다(S-2). Z-X 대상이 10개를 넘으면 도구가 종료 2로 멈춘다(RV2-6: 묻는다).

```powershell
$py = "C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe"
foreach ($b in "Z-0","Z-A","Z-T","Z-S","Z-C","Z-X") {
  & $py -I -B 04_scripts/04_hydraulic/coupled/las_p5r4k1_targeted.py run --bundle $b `
      --workers 20 --affinity 0x0FFF5555 2>&1 |
      Tee-Object -FilePath "06_analysis\03_hydraulic\coupled\v5\las\p5r4k1\run_$b.log"
  # 각 묶음 뒤: log_errors.py <로그> --require-line 결과 errors 0 확인(S-9). 0이 아니면 다음 묶음을 띄우지 않는다.
}
```

- 오류 키 재실행(10.1, 1회): `run --bundle <묶음> --resume` → `p5k_<묶음>_resume.jsonl`.
- 실제로는 Z-T·Z-S·Z-C를 배치표대로 동시에 띄울 수 있다. 위 반복문은 순서만 보인다.

## 5. 하네스 판정 (경로 1)

```powershell
& "C:\ProgramData\miniforge3\envs\python-dev\python.exe" -I -B 06_analysis/02_control/verif_matrix/scripts/las_p5r4k1_judge.py `
    --expect-judge-sha f4ef93d5157df0fcfb03f2af57df73aefb30685b12e2bc130740fd7060d0b44d `
    --out 06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/judge_p5k_harness.json
```

- `--expect-judge-sha`는 main checkout 작업 트리가 CRLF일 때의 sha256이다. 하네스 판정 도구는 raw와 LF(`4c07bfef331078fc329bd065e4a78bb73dec1c9bd8e6b8ce1bd1561ce3f1ee3a`)를 모두 받는다. 판정 커밋은 `{JUDGE_COMMIT}`.
- 판정 전 관문(16.3·16.4): 모든 묶음 로그 `errors 0`(또는 `errors_left` 0), `placeholder_scan.py` `placeholder_unfilled` 0. 하네스가 `통과`가 아니면 Chrono를 시작하지 않는다(S-6).

## 6. Chrono 본 실행 (4.3, 12행, 배치 `V5-LAS-P5R4-K1`)

행 목록 `chrono_rows_main.json`(목록 sha256 `3fdbf80ee426cb9ef4eeab13d5943d08fbef9b89d9a2ef230f13ce45c4f8de3c`). 출력 폴더 `{BATCH_CHRONO}`(시작 직후 15분 안에 채움).

```powershell
& "C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe" -I -X utf8 -u 04_scripts/02_chrono/s9_batch.py run V5-LAS-P5R4-K1 --parallel 4 --parallel-e 3 --schedule 06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/prelaunch/sched_main.json
& "C:\ProgramData\miniforge3\envs\python-dev\python.exe" -I -B C:\Users\jinbeom\.claude\tools\verif\log_errors.py `
    {BATCH_CHRONO}\progress.log --pattern "\brc=(\d+)" --require-line
```

## 7. postrun과 Chrono 판정 (경로 1)

```powershell
& "C:\ProgramData\miniforge3\envs\python-dev\python.exe" -I -B 06_analysis/02_control/verif_matrix/scripts/las_p5r4k1_chrono_judge.py postrun --batch {BATCH_CHRONO}
& "C:\ProgramData\miniforge3\envs\python-dev\python.exe" -I -B 06_analysis/02_control/verif_matrix/scripts/las_p5r4k1_chrono_judge.py judge --batch {BATCH_CHRONO} `
    --expect-tool-sha 8d869e53c47c8d512fdb60cc818930eabb683b30a5c67e711928c1ca59e50756 `
    --rem-batch 07_results/S9/batch_V5-LAS-K1-REM_20261109_235554
```

- postrun HEAD는 `{POSTRUN_HEAD}`로 기록한다. Chrono 판정 도구의 K-0은 `--expect-tool-sha`를 prelaunch·postrun·judge가 잰 **작업 트리 raw sha256**과 그대로 비교한다(LF 값은 받지 않는다). 위 값은 main checkout이 CRLF로 체크아웃했을 때의 값이고, LF로 체크아웃돼 있으면 `2b7dcb7b54ed8b8c27fc0ebbeab3aadd47e2f11341fa3d92be1fd3844c1371c4`이다. 실행 전 `Get-FileHash`로 어느 쪽인지 확인해 감사 기록에 적는다.
- 경로 2(`p5k_path2/`)의 실행 명령은 control-expert가 정한다. 이 문서는 그 blob만 고정한다(`manifest.json` `path2_tools_git_blob`).
