<!-- verif-protocol-auditor 리포트 원문(2026-11-10, 가벼운 실행 전 감사). 대상: B1-GRIDCONV GC-1~4, master dc2029b. 메인 세션이 편집 없이 저장. -->

**차단 2건, 실행 전 수정 3건, 기록 6건.** 지시하신 명령을 그대로 실행하면 결과가 나와도 판정이 `UNDETERMINED`로 굳을 수 있습니다. 차단 2건(batch.json과 인자 순서)을 고친 뒤에 실행하십시오. 봉인, 경로 A의 정의, 빈 집합 처리, 시간 순서에는 문제가 없습니다.

## 감사 요약
- 대상: B1-GRIDCONV GC-1~4. 시점은 실행 전(가벼운 범위). 저장소는 master `dc2029b`(HEAD_G 예정)입니다.
- 기준 문서
  - 원판 `06_analysis/02_control/b1/b1_gridconv_plan.md`(sha `0e909bf1`)
  - 덧붙임 `b1_gridconv_plan_rev1.md`(sha `3f354eb7`)
  - 경로 A `gridconv_judge.py`(sha `4a5c4246`, blob `91d8d80c`)
- 판정: 차단 2 / 실행 전 수정 3 / 기록 6.

## 발견 사항 (심각도순)

**[차단][I·R] 1. run_S9 single-pad는 `batch.json`을 만들지 않습니다. 그래서 rc와 argv가 남지 않습니다**
- 근거
  - `--out-root`는 폴더만 만듭니다(`run_S9.py:2509-2514` `out_dir`). single-pad가 쓰는 파일은 `series.npz`와 `result.json`뿐입니다(`run_S9.py:2884-2887`). `result.json`에도 `vars(args)`만 들어가고 실제 argv는 없습니다(`:2820`).
  - s9_batch에 GRIDCONV 묶음이 없습니다(`04_scripts`를 Grep해 0건).
  - 경로 A는 rc를 `batch.json`의 `cases[].rc`나 `--rc`에서 읽고, argv는 `batch.json`의 `cases[].argv`에서만 읽습니다(`gridconv_judge.py:125-153`).
- scratchpad 재현: 자체 시험의 pass 묶음을 복사해 경로 A를 돌렸습니다.
  - batch.json 없음 → 4행 모두 `V-1 rc None` → `UNDETERMINED`(exit 1)
  - batch.json 없음 + `--rc` → `PASS`. 이때 `argv_checked: false`이고 사유가 남지 않습니다. 원판 V-2의 "argv가 3.2 표와 한 글자씩 같음"이 실행되지 않은 채 지나갑니다.
  - 자체 시험의 batch.json에도 `argv`가 없어서 이 경로는 한 번도 시험되지 않았습니다(`gridconv_judge_selftest.py:83`).
- 실패 시나리오
  - 지시대로 실행하면 rc 근거가 없습니다. 판정이 `UNDETERMINED`로 끝나거나, 손으로 넣은 `--rc`로 argv 조항 없이 `PASS`가 납니다.
  - parsed args 대조(`:199-202`)는 대부분을 잡지만 `--t-end`·`--t-settle`·인자 순서는 잡지 못합니다. 두 값은 실행 중 덮어써집니다(`run_S9.py:2733-2734`).
- 권장 조치(메인 세션, 실행 래퍼)
  - 각 행을 띄울 때 실제 argv 목록과 프로세스 종료 코드를 잡습니다.
  - 그것을 `<batch>/batch.json`에 `{"cases":[{"case":"GC1_J2_B_RL_1cm","argv":[...],"rc":0}, ...]}` 형식으로 씁니다.
  - argv의 `single-pad` 뒤는 아래 2번의 순서이고 `--out-root <batch>`로 끝나야 합니다(`:207-213`).
  - PowerShell이면 `Start-Process -PassThru` 뒤 `WaitForExit()`와 `.ExitCode`로 받습니다.
  - prelaunch에 argv를 적고, 경로 A에는 `--rc`를 쓰지 않습니다.

**[차단][R] 2. 지시 명령의 인자 순서가 계획서 3.2의 argv 예와 경로 A의 기대 argv와 다릅니다**
- 근거
  - 경로 A의 기대 순서는 계획서 `b1_gridconv_plan.md:88`의 예와 같습니다(`gridconv_judge.py:156-160`).
    `single-pad --soil J2 --pad-variant dwg_rear250 --level top --leg <L> --joint fixed --grid <g> --threads 4 --normal-load <N> --load-steps <s> --load-ramp 3 --step-ramp 2 --step-hold 8 --case <c> --out-root <batch>`
  - 지시 명령은 "공통 + 행별"이라 `--joint fixed --threads 4 --load-ramp 3 --step-ramp 2 --step-hold 8 --leg …` 순서가 됩니다.
  - 재현: 이 순서를 argv로 batch.json에 넣으면 4행 모두 `V-2 batch.json argv … != …` → INVALID → `UNDETERMINED`.
- 실패 시나리오: 1번을 고쳐 argv를 기록해도 4행이 모두 INVALID가 됩니다. 원판 V-2는 "INVALID(다시 돌리지 않는다)"이므로 판정을 되살릴 수 없습니다.
- 권장 조치(메인 세션·cad-expert): 행마다 argv를 위 순서 그대로 한 줄로 씁니다. 값 표기도 맞춥니다: `--grid 0.01`/`0.005`, `--normal-load 74850`/`122010`, `--load-steps 0.97327989,1.0`/`0.98016556,1.0`.

**[실행 전 수정][I] 3. result.json에 커밋이 없고, 실행 장소가 main checkout입니다**
- 근거
  - single-pad summary에는 git 상태가 없습니다(`run_S9.py:2819-2845`). git rev-parse는 `:4046`, level 경로에만 있습니다.
  - main checkout은 오늘 17:34에 merge 5건이 들어온 작업 트리입니다(reflog). worktree는 30개가 열려 있습니다.
  - 지금은 추적 파일 변경 0이고(`git diff --stat HEAD` 비어 있음), 03_src·04_scripts·02_params에 추적되지 않은 파일도 없습니다(git 제외 DLL `bin/` 하나뿐). rev1 28행의 "깨끗한 checkout" 조건은 지금 충족됩니다.
  - rev1 순서는 "HEAD_G checkout에 DLL 복사"를 전제로 합니다.
- 실패 시나리오: 실행 중에 master에 merge가 들어오거나 행마다 시작 시각이 다르면, 어느 코드로 돌았는지 결과에 남지 않습니다.
- 권장 조치(메인 세션)
  - prelaunch에 시작 직전과 끝난 직후의 `git rev-parse HEAD`와 `git status --porcelain --untracked-files=no`를 적습니다.
  - 실행 중에는 main checkout에 merge·checkout을 하지 않습니다. 또는 `dc2029b`의 전용 worktree에 DLL을 복사해서 돌립니다.
  - main checkout을 쓰면 C-2의 "복사본 sha"는 원본과 같은 파일입니다(지금 `cec997d7…` 일치). prelaunch에 그 사실을 적습니다.

**[실행 전 수정][R] 4. 배치표 단계 확인**
- 근거: 원판 7절 "풀·동시 수는 compute-scheduler-expert 배치표로 정한다"(`:151`), 순서 "… → 배치표 → 실행"(`:152`, rev1 45행).
- 지시 명령: 4행을 동시에 띄우고 각 행이 E 12코어 전체에 고정되며 `--threads 4`입니다. 그러면 12코어에 16 OMP 스레드가 됩니다.
- 권장 조치: 배치표가 있으면 그 경로와 sha를 prelaunch에 적습니다. 없으면 compute-scheduler-expert에서 받습니다(`self_pin`, 동시 개수).

**[실행 전 수정][I] 5. 실행 환경 변수를 명시적으로 정리하고 기록합니다**
- 근거
  - `OUTRIGGER_HULL_HOOK`이 세션에 상속돼 `fast`로 남아 있으면 source=env가 됩니다. 원판의 "미설정" 조건을 어겨도 경로 A는 통과시킵니다(`gridconv_judge.py:248-253`).
  - `OPENBLAS_NUM_THREADS=1`은 계획서에 없는 env이고 result.json에 남지 않습니다. placement에는 `omp_wait_policy`만 남습니다(`run_S9.py:2493-2494`).
- 권장 조치
  - 실행 셸에서 `Remove-Item Env:OUTRIGGER_HULL_HOOK, Env:OUTRIGGER_HULL_HOOK_ALLOW_UNVALIDATED, Env:OUTRIGGER_HULL_HOOK_DLL -ErrorAction SilentlyContinue`를 먼저 실행합니다.
  - 추가 env 목록과 인터프리터 플래그는 prelaunch에 적습니다. `-I` 권장: PYTHONPATH가 주입되지 않습니다.

**[기록]**
- 6. [E] 경로 A가 비정상 입력에서 예외로 끝나는 곳이 있습니다. `load_steps.levels`에 `None`이 들어가거나 `end` 키가 없으면 TypeError/KeyError로 끝납니다(`:191`, `:164`). result.json이 깨져도 같습니다(`:184`). 모두 출력 없이 0이 아닌 종료라서 거짓 PASS는 아닙니다.
- 7. [E] G-5를 계산할 수 없으면(공통 표본 < 2) `flag`가 False로 남고 NA가 되지 않습니다(`:335-336`, `:355`). G-5는 기록 지표라 판정은 바뀌지 않습니다. 판정서에 `g5_samples`를 적으면 됩니다.
- 8. [R] rev1 15행의 근거 행 번호 `run_S9.py 2764-2768`은 K-2 merge(9080fab) 뒤 `2782-2786`으로 밀렸습니다.
  - `01dd321..dc2029b` 사이 run_S9 diff hunk는 1532·1560·3924·5950·6382 다섯 곳입니다. 모두 level/controller/parser(lp) 쪽이고, single-pad(2542-2892)와 single-pad parser(6289-6309)는 그대로입니다.
  - 03_src에서는 scm_model·hull_hook이 바뀌지 않았습니다.
- 9. [I] [추정] 동시 실행이 결과 비트를 바꾸지 않는다는 근거는 프로젝트 규칙(비트는 스레드 수에 의존)뿐이고, 이번 묶음에서 확인하지는 않았습니다. 짝 비교가 같은 묶음 안에서 이루어지므로 판정 영향은 작습니다. placement 기록(affinity)은 남습니다.
- 10. [R] 패드 시작 위치 인자는 single-pad parser에 아예 없습니다(`run_S9.py:6289-6309`). "인자 없음" 조건은 구조적으로 충족되고, C-1 `series.npz` x[0]·y[0] 검사가 그것을 대신합니다(`gridconv_judge.py:230-245`). 정의는 rev1과 일치합니다.
- 11. [S] 결과 폴더 `07_results/`는 `.gitignore:39`로 git 밖입니다. 결과 sha는 판정서와 metrics에 인용하는 수밖에 없습니다. 예정된 `b1_gridconv_metrics_A/B.json`·`b1_gridconv_judgement.md`·prelaunch는 `-text`(check-attr `unset`)로 보호됩니다.

## 규칙↔도구 대조표 (경로 A)
| 항목 | 규칙 | 도구 | 판단 |
|---|---|---|---|
| 행 4개(case·leg·grid·N·steps) | plan:79-84 | judge:41-46 | 일치 |
| V-1 rc 0, result.json, levels 2, 끝 ≥ 21−1e-6 | plan:94 | :176-196 | 일치(rc 출처는 1번 참고) |
| V-2 argv 한 글자씩 | plan:95, 예 :88 | :203-213 | 일치. 단 batch.json argv가 없으면 건너뜀(1번) |
| V-2 threads 4, PASSIVE, grid_m, J2 Kc·Kphi·n, plane (0,0,0) | plan:95 | :216-227 | 일치. 키는 `scm_model.py:930-933`, `run_S9.py:2628`·`:2494`에서 나옴 |
| C-1 series.npz x[0]·y[0] ≤ 1e-9 m, 없으면 INVALID | rev1:14-17 | :230-245 | 일치. x·y는 `share.GetPos()`(`run_S9.py:2782-2786`) |
| hull requested = effective = fast | plan:95 | :248-253 | 일치(`hull_hook.py:121`, source default → requested "fast") |
| C-2 dll_sha256 = cec997d7…, validated true | rev1:27 | :254-256 | 일치 |
| 패드 면적(YAML 대조) | plan:29 | :257-259 | 추가 검사, 일치(YAML RL 0.0607/0.130578967, FL 0.1071/0.171400364) |
| V-3 N_h ≥ 3, b_hull 있음 | plan:96 | :265-271 | 일치(+ z_node None 거부) |
| z_ref, f 식 | plan:19-22 | :102-107 | 일치 |
| G-1 nε ≤ 0.5 %, 8개, 실패 → REJECT | plan:106 | :276, :346, :359 | 일치(count guard 있음) |
| G-2 \|z/f 차\| ≤ 1 mm, 4개, geo | plan:107 | :278, :326, :349, :361 | 일치 |
| G-3 ≤ 0.002, 2개 → HOLD | plan:108 | :327, :352, :363 | 일치 |
| G-5 ≤ 0.05 기록 | plan:110 | :328-336, :355 | 일치(7번 참고) |
| 판정 순서·`UNDETERMINED` | plan:112-116 | :357-366 | 일치. 비교는 모두 `<=` |
| E-1~4 상한, E-5~8 ±0.5 mm | plan:123-132 | :59-64, :367-377 | 일치 |
| 건조 실행 건수 | plan 4행 | 판정 대상 4행 | 결과를 쓰는 건조 실행은 돌리지 않음 |

## 확인 필요
- 원판 V-2는 "INVALID(다시 돌리지 않는다)"이고 6절 UNDETERMINED는 "빠진 행만 1회 다시"입니다. INVALID 때문에 생긴 UNDETERMINED에서 다시 돌릴 수 있는지 문구가 엇갈립니다. 결과 전에 정하는 것을 권합니다(control-expert).
- 원판 7절: 경로 B는 "G-1·G-4를 따로 계산"하는데 대조는 "행 상태·판정은 완전 일치"입니다. 경로 B가 G-2·G-3과 판정까지 내는지(G-4 원시값에서 유도) 정해야 합니다. 경로 B 지시문에 그렇게 적거나, 개정판에서 대조 범위를 G-1·G-4와 행 상태로 좁히십시오.

## 위임 필요
- 없음. 경로 A는 sha로 고정돼 있어 고칠 대상이 아닙니다. 1·2번은 실행 래퍼와 명령 쪽에서 고칩니다.
- 6·7번을 고치려면 새 sha와 개정이 필요하므로 이번에는 권하지 않습니다.

## 메인 세션 권고
- 실행 래퍼로 batch.json(case·argv·rc)을 만들고, argv는 계획서 순서로 씁니다(1·2번).
- prelaunch에 넣을 것: HEAD 시작·끝 기록, DLL sha, 배치표, env 정리 결과(3~5번).
- 이 감사 범위는 실행 전이 전부입니다. 판정 뒤에는 사용자 결정대로 재집계만 합니다.

## 검사하지 못한 것
- 실제 Chrono 출력(결과가 0건이라 실측 키 확인은 코드 읽기로 대신했습니다).
- 동시 실행·과밀 상태의 비트 동일성(9번).
- cad 쪽 `grid_conv_judge.py`(판정에 쓰지 않는 보조라 읽지 않았습니다).
- 경로 B는 아직 없습니다.

## 실행한 검증
- 인터프리터: python-dev(`-I -B`, `MKL_THREADING_LAYER=TBB`).
- S(봉인)
  - `Get-FileHash` 결과가 원판·rev1의 `.sha256` 첫 토큰과 같고, 경로 A 상수 `PLAN_SHA256`과도 같습니다.
  - `git hash-object` 결과 judge `91d8d80c…`, selftest `848e45e8…`로 rev1 표와 같고 HEAD 트리 blob과도 같습니다.
  - `ls-files --eol`: 규칙·`.sha256`·judge 모두 `i/lf w/lf attr/-text`이고 `check-attr text: unset`입니다.
  - `seal_check.py`(2판, `--const …:PLAN_SHA256`): 발견 0.
- E: `gate_scan.py` 결과 `count_guard` info 1건뿐입니다.
- T(시간 순서)
  - 원판 봉인 16:35:32, 커밋 71bf74d 16:35:46.
  - rev1 봉인 16:50:36, 커밋 01dd321 16:50:48. judge의 마지막 변경도 01dd321입니다.
  - `01dd321`은 `dc2029b`의 조상입니다.
  - GC 결과는 main checkout `07_results/S9`와 모든 worktree에서 0건입니다.
  - `timeline.py`는 `--results`가 필수라 실행하지 못했습니다(입력 오류 종료 2, 결과 0건). git log로 대신했습니다.
- 자체 시험 `gridconv_judge_selftest.py`: `{"status":"ok"}`. TMP를 scratchpad로 돌려 실행했습니다.
- scratchpad 탐침 `probe.py`(자체 시험 pass 묶음 복사본에 경로 A 실행)
  - batch.json 없음 → UNDETERMINED
  - `--rc` → PASS(argv 미검사)
  - 계획서 순서 argv → PASS
  - 지시 순서 argv → UNDETERMINED
  - 빈 폴더 → UNDETERMINED(exit 1)
- 읽은 코드: `run_S9.py` 2470-2910·6198-6310, `hull_hook.py` 60-198, `scm_model.py` 915-936, YAML `pad_shapes`, `git diff 01dd321 dc2029b`(run_S9·03_src).
- 만든 뒤 지운 것: scratchpad `verif\`(guard.json, probe.py, tmp·work·tool). 저장소에 생긴 파일과 `__pycache__`는 없습니다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha b1_gridconv_plan.md 0e909bf1…, b1_gridconv_plan.sha256 2cc150c3…, b1_gridconv_plan_rev1.md 3f354eb7…, b1_gridconv_plan_rev1.sha256 67069c63…, gridconv_judge.py 4a5c4246…, gridconv_judge_selftest.py ec3126cd…, rexome33.yaml ef2880f9…, run_S9.py 9efaf217…, hull_hook.py afef13ec…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
- 메모리: `C:\Users\jinbeom\.claude\agent-memory\verif-protocol-auditor\audit_pitfalls.md`에 "직접 실행기는 batch.json을 쓰지 않아 argv 조항이 건너뛰어짐 / 인자 순서" 함정 1줄을 더했습니다.
