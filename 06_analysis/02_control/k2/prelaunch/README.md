# K-2 V-2~V-7 실행 전 묶음 (초안, 실행 안 함)

- 작성: control-expert, 2026-11-10. 브랜치 `k2-prelaunch`(master `dc2029b` 위).
- 규칙: `k2_touch_creep_rules.md`(봉인 `a3658197…7263`) + `k2_touch_creep_rules_rev1.md`(봉인 `5ba081c6…4776`). dynamics 명세 `k2_dyn_spec.md`(`502b0bb7…27ff`).
- **이 폴더는 실행 전 기록의 초안이다.** `{RUN_HEAD}`, `{POOL}`, `{MASK}`, `{WORKERS}`, `{PLACEMENT}`, `{L2B_WORKERS}`, `{P}`, `{PLAN_ID}`, `{BATCH_V7}` 자리는 배치표와 실행 시작 때 채운다. 채운 뒤 `make_prelaunch.py`를 다시 돌리면 입력 sha가 다시 계산된다.

## 0. 묶음 HEAD와 고정 값

- `{RUN_HEAD}`는 master `dc2029b`에 다음 세 브랜치를 병합한 커밋이다.
  - `k2-v7k1-dhat`(cad-expert `09f66c4`)
  - `k2-prelaunch-fix`(python-expert `c77ecf5`)
  - `k2-prelaunch`(이 브랜치)
- 실행은 그 커밋의 고정 checkout(`git worktree add C:\workspace\outrigger_control\.claude\worktrees\k2-run {RUN_HEAD}`)에서만 한다.

| 대상 | 값 | 확인 방법 |
|---|---|---|
| 원판 / rev1 / 명세 sha256 | `a3658197…7263` / `5ba081c6…4776` / `502b0bb7…27ff` | raw sha256 |
| rev2 / rev3 / rev4 sha256 (결과 전, 브랜치 `k2-prelaunch-record`) | `b3f1b41f…94ea` / `8bcdb0ed…6e61` / `82160ff5…00c5` | raw sha256 |
| 경로 2 `k2_recount.py` **1.3** blob (판정 때 이 브랜치·병합 뒤 main에서 실행. k2-run에는 1.2가 있다) | `78a3d2c7c9d26523288f5f3ab05b9a3d6e63466c` | `git rev-parse <판정 커밋>:<path>` |
| 경로 1 `k2_judge.py` | **`{PATH1_BLOB}` 대기**(python-expert, rev2~rev4 반영판). 이전 `7ee9ccc1…`은 쓰지 않음 | 같음 |
| `k2_v5_flatten.py` | **`{FLATTEN_BLOB}` 대기**(python-expert). 이전 `a83abd80…`은 쓰지 않음 | 같음 |
| `run_with_identity.py` | `fab7664bd3ba16723e4202bf71dc7d87ab0cf7f0` | 같음 |
| `run_ps7.py` | `248f5363cbdbaf1bc20eac3ef5e73bdfd6e05acd` | 같음 |
| `g8trace.py` | `d8bfe68e4350195951ec58a6a69bc24c04d293cc` | 같음 |
| 점 파일 `k2_points_5p5_3p5.json` | sha256 `a15cbe95275be11c163028ca2113d896254d49a4554286c54bdbfa88680cccc3` | `k2_recount points-check` 통과 |
| V-3 키 | 273, 정렬 목록 sha `d4a030d7…` | `k2_v3_keys.txt` |
| 입력 파일 | `k2_prelaunch_*.json`의 `inputs` | `make_prelaunch.py` 재실행 |

### 0.1 실행 전 기록 채움 (2026-11-10)

- `{RUN_HEAD}` = `6a44ff81d25aea1fa162daf9b14c23b99beb9db0`. 고정 checkout은 `C:\workspace\outrigger_control\.claude\worktrees\k2-run`이다.
- 위 표의 blob 6개(경로 1·2, 평탄화기, 래퍼, run_ps7, g8trace)를 `git rev-parse 6a44ff8:<path>`로 대조했고 모두 같았다.
- 배치표: `sched/k2_placement_20261110.json`(sha256 `f349ce4e…`, `k2-sched-20261110a`), `sched/k2_commands_filled.json`(`402a1ef3…`), `sched/build_runners.py`(`7182fb37…`), `sched/runners/k2run_*.ps1` 6개. compute-scheduler-expert scratch에서 복사했고, 파일별 sha는 `k2_prelaunch_*.json`의 `schedule.files_sha256`에 있다.
- 자리 값
  - V-2~V-5: pcore `0xFFFF`, worker 8
  - V-6: ecore `0x0FFF0000`, L1 `--placement ecore`, L2b `--workers e6`
  - V-7: ecore, `--parallel 0 --parallel-e 4 --e-cases <4행>`. `{BATCH_V7}`는 시작 뒤 채운다.
- V-2 I-4의 저장 행은 git 제외 파일이다. **main checkout의 `06_analysis/02_control/d8x/ra/`를 쓴다**(`k2-run`에는 없다): `ra_off.json` `100985bf…cb10`, `ra_on.json` `e3c8c95f…247a`.
- **실행 전 기록은 `k2-run`이 아니라 master 위 브랜치 `k2-prelaunch-record`에 있다.** 실행 중 도구가 읽는 입력(`k2_commands.json`, `k2_v3_keys.txt`, 점 파일)은 `6a44ff8`의 것과 바이트가 같다. 그래서 `k2-run`을 고칠 필요가 없다.
- **(rev2~rev4 뒤 갱신)** `k2_manifest.json`(`v5_raw` 추가)과 `k2_expect.json`(note)은 이 브랜치에서 바뀌었다. 둘 다 **판정 때만** 읽는 입력이다. 판정 때는 반드시 이 브랜치(병합 뒤 main)의 사본과 `--rules-dir 06_analysis/02_control/k2`(원판·rev1~rev4 봉인 포함)를 쓴다. k2-run의 사본은 구판이다.
  - 실행 중 `acc_d8`은 `k2-run` 안의 `k2_v3_keys.txt`와 점 파일을 읽는다.
  - 판정 때 경로 1·2에는 `--manifest`/`--expect`/`--fields`로 이 브랜치(병합 뒤 main checkout)의 파일을 넘긴다. 내용이 같으니 `k2-run`의 사본을 넘겨도 된다.
  - 다만 manifest의 V-7 `{BATCH_V7}`는 시작 뒤 이 브랜치의 manifest에만 채운다. `k2-run`의 사본은 바꾸지 않는다.

## 1. 파일

| 파일 | 내용 |
|---|---|
| `make_prelaunch.py` | 아래 파일을 모두 만든다(읽기만, 실행 없음) |
| `k2_commands.json` | 68단계. 하네스 단계는 `run_with_identity.py`로 감쌌다(`argv`, 원래 명령은 `inner_argv`) |
| `k2_manifest.json` | 경로 1·2 공용 입력. V-5 칸은 평탄화 출력 `runs/v5/<arm>/flat/<bundle>.json` |
| `k2_expect.json` | `expect-template` + g8 83 + regression 93 |
| `k2_fields.json` | 경로 2 필드 지도 |
| `k2_v3_keys.txt` | V-3 273키 |
| `k2_prelaunch_v2.json` … `v7.json` | 실행 전 기록 초안 |

## 2. 실행 명령 (요지, 정확한 argv는 `k2_commands.json`)

공통 env(하네스): `CONDA_PREFIX`·`PATH` = dynamics-dev, `MKL_THREADING_LAYER=TBB`, `MKL/OMP/OPENBLAS/NUMBA_NUM_THREADS=1`, `PYTHONDONTWRITEBYTECODE=1`. 하네스 인터프리터 `C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B`, Chrono는 `C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe -I -X utf8 -u`.

**래퍼**: 하네스 단계는 모두 `python.exe -I -B run_with_identity.py <sidecar> --git-dir <k2-run> -- <원래 argv>`로 띄운다. 래퍼는 affinity를 바꾸지 않는다. 그래서 **부모(러너 셸, `make_runner` 러너, 또는 `start /affinity`)를 먼저 `{MASK}`에 고정**한다.

| 묶음 | 단계 | 명령 핵심 |
|---|---|---|
| V-2 | 4 | `acc_d8.py <out> --points d8x_points.json --stages main,robust,kt --k1 off --k2 off\|on` (910) / `--stages main --k1 on` (192). 시계열은 `<out stem>_series` |
| V-3 | 14 | `acc_d8.py <out> --points d8x_points.json --stages main,robust,kt --k1 off --k2 off\|on --aug <팔> --keys-file k2_v3_keys.txt` |
| V-4 | 2 | `acc_d8.py <out> --points k2_points_5p5_3p5.json --stages main,robust,kt --levels top --k1 off --k2 off\|on` |
| V-5 실행 | 36 | 저장 인수 단계 14개(reg1~7, grid 4, soil_A, d8, noise_L1L2)를 고정 checkout으로 옮겼다. `acc_launch.py`, env `ACC_COMBO=preset`, **`ACC_K2=off\|on`**, `ACC_PROVENANCE`. 출력 `runs/v5/<off\|tcl>/`. PS-7 `acc_launch.py run_ps7.py E … --out runs/v5/<arm>/ps7.json`. G8 `g8trace.py <k2-run> jobs{1,3,5}.json <out.jsonl>`(env `ACC_COMBO=off`, `ACC_K2`) |
| V-5 후처리 | 6 | 팔마다 `r79_sensor_judge.py judge <out>_judgement.json <run>.json` 두 번(`r79_L1L2`, `clip_r79_L1L2`), 그다음 `k2_v5_flatten.py --arm-dir runs/v5/<arm> --out-dir runs/v5/<arm>/flat --checkout <k2-run>` |
| V-6 | 5 | `run_S6C.py snaps-k2 --jobs 1 --dry-run`. **확인만**: `existing`에 `S6_crawler_top_k2pp025`가 있고 `missing`이 비어야 한다. 아니면 멈추고 묻는다. L1은 `run_S6C.py run --set k2_v6 --approved --jobs 2 --k2 off\|on --k1-order-gate off --expect-controller final_C4G2_LAS(_TCL) --pad-zeta-moving 0.1 --tag k2v6_<arm> --placement {ecore\|pcore} --batch-dir <k2-run>\07_results\S6\k2v6_L1_<arm>`. L2b는 `run_S8C.py run --set k2_v6 --approved --workers {e6\|p7} --k2 off\|on --k1-order-gate off --expect-controller … --tag k2v6_<arm> --batch-dir <k2-run>\07_results\S8\k2v6_L2b_<arm>` |
| V-7 | 1 | `s9_batch.py run k2_v7 --parallel {P} [--parallel-e …]`, env `OMP_WAIT_POLICY=PASSIVE`. 행 `K2V7_P3b_J1/J2_B_top_Fs4_off\|tcl`, 태그 `final_C4G2_LAS_K1(_TCL)`, 기록 전용 |

- acc_d8 D8x 모드는 `ACC_K2`가 env에 있으면 멈춘다. V-2~V-4 env에는 `ACC_K2`를 넣지 않았다.
- `--batch-dir`는 이미 있는 폴더를 거부한다. 다시 돌릴 때는 새 이름을 쓰고 실행 전 기록에 적는다.
- V-6 manifest의 행 파일 경로는 `<batch-dir>\<행 이름>\k2_row.json` 등으로 적었다. 실제 행 폴더 이름이 다르면 실행 전 기록 때 고친다(cad-expert 확인).

## 3. V-5 regression 행 수 결정 (기록 수준 정정 (a))

- 규칙 3.4와 `criteria.md`의 회귀 행은 "118 | L1·L2·토양·경사 행 통과→실패 0 (L3 행은 기록만)"이다. 봉인 문구가 이미 판정 대상을 L1·L2·토양·경사 행으로 한정한다.
- 기존 판정기 `acc_judge`가 판정 행으로 세는 것은 **93**(13 + 17 + 2 + 11 + clip_A 20 + r79 L1/L2 30)이다. **기록 행은 49**다(3.1절, 키 sha로 고정).
- **rev2 2절이 이를 규칙으로 정했다**: 판정 93 + 기록 49이고, 118은 다시 만들 수 없는 옛 목록 수다. rev4 1 (c)에 따라 r79 판정 파일의 `unmatched`는 기록이다. (앞 판의 "기록 25"는 118 − 93 산술이었고 폐기했다.)

### 3.1 키 목록 고정 (2026-11-10, 실행 전 기록 브랜치 `k2-prelaunch-record`)

- `regression_keys.py`가 저장 인수 출력(`touch_phase/acceptance/regression/`)에서 두 키 목록을 만든다. K-2 V-5 회귀 단계는 같은 단계라 키가 같다. 결과는 `k2_v5_regression_keys.json`.
  - **판정 93**: sha256 `2900db889efc73070c3a8fbe557b1a4ad9ee3392afc099ba00be1d0549174ec9`. 구성은 clip_harness 13, clip_p0 17, clip_x426_C 2, clip_x426_D 11, clip_A 20, r79 L1/L2 판정 30.
  - **판정하지 않는 출력 항목 49**: sha256 `d4f58334c6ca7c393c35072a798c09f4995d7fde274e0af6b21b99f977d503eb`. 구성은 clip_r79_L1L2 가운데 판정 행이 아닌 7(L1 6 + L2 1), clip_r79_L3L4 42(L3·L4).
- **"118 − 93 = 25"와 다르다.** 저장 출력에서 판정하지 않는 항목은 49개다. 판정 93 + 비판정 49 = 출력 항목 142다.
  - criteria.md의 118은 옛 재실행 목록(py_c2clip `rerun_commands.ps1`)의 행 수다. 그 구성은 저장 출력만으로는 다시 만들 수 없다(그 목록 파일은 옛 scratch에 있었다).
  - 판정 대상(93)은 `acc_judge` 정의와 같으므로 등급에는 영향이 없다. 그래도 봉인 문구의 118과 도구 93·출력 142의 대응은 **실행 전 감사의 '확인 필요'**로 올린다.
- 실행 뒤 같은 함수를 K-2 두 팔 폴더(`runs/v5/<arm>`)에 돌린다. 판정·비판정 키 sha가 위 값과 같아야 한다(다르면 V-5는 판정 불가).

## 4. 배치표 입력 (compute-scheduler-expert)

worker-초 추정이다.
- 하네스 근거는 실측이다: R-a 8.7 s/행(P), 진단 상단 12.4 s/행(P).
- 가정은 다음 셋이다: K-2 기록 부담 ×1.15, V-5의 E→P 환산 ÷1.7, PS-7·G8 행당 60·50 s.
- V-6은 cad-expert의 `--dry-run` 값이다.

| 묶음 | 단계 | 행(팔당) | P worker-s (합) | E 대안 | 같은 풀로 둘 짝 |
|---|---|---|---|---|---|
| V-2 | 4 | 1,102 | 약 22,000 | – | 같은 K1 칸의 off·tcl |
| V-3 | 14 | 273 | 약 54,600 | – | 같은 aug 팔의 off·tcl |
| V-4 | 2 | 596 | 약 17,000 | – | off·tcl |
| V-5 | 36 + 후처리 6 | 잡음 1,026 / 격자 768 / D8 576 / 토양 60 / 회귀 118(판정 93) / PS-7 20 / G8 83 | 약 78,000 | 약 133,000 | 같은 단계 id의 off·tcl. 후처리는 그 팔 실행이 끝난 뒤 |
| V-6 | 1(확인) + 4 | L1 4행, L2b 4행 | L1 177~270 s/행, L2b 507~529 s/행. 8행 동시 약 9~10분 | L1 624 s/행, L2b 829~865 s/행(상한 약 1,400). 8행 동시 약 15~18분 | 엔진별 off·tcl 같은 풀(L1 `--placement`, L2b `--workers`가 두 팔 같게) |
| V-7 | 1 | 4행 | 약 44,000(행당 11,000 s) | – | 같은 토양 행의 off·tcl |

- 하네스(V-2~V-5)만 합해 약 172,000 P worker-s이고, P 8 worker로 약 6.0 h다.
- 풀 상황: P코어 `0xFFFF`는 비어 있다. E코어는 격자 시험 GC 4행이 20~25분 쓴다.

## 5. 행 신원 기록 점검표

| 실행기 | argv | rc | HEAD·clean | env·마스크 | 경로 1 | 경로 2 |
|---|---|---|---|---|---|---|
| 하네스 단계 전부(V-2~V-5, 후처리) | **sidecar**(`run_with_identity.py`: argv, cwd, env 부분집합, 상속 마스크와 자식 마스크, 시각, pid, rc) | sidecar | sidecar(시작·끝 HEAD와 `git status`) | sidecar | 읽지 않음 | 읽지 않음 |
| `acc_d8.py` 자체 | `meta.d8x`(인자 값) | – | `meta.d8x.identity_start/end` | identity_start | 확인 필요 | 읽지 않음 |
| `acc_launch.py` 자체 | `ACC_PROVENANCE`(script·argv) | – | provenance git_head | provenance threads | 읽지 않음 | 읽지 않음 |
| `run_ps7.py` | provenance | – | provenance | provenance | 행 태그·`touch_creep_latch`를 평탄화가 옮김 | 평탄 행만 |
| `g8trace.py` | sidecar만 | sidecar | sidecar | sidecar | 평탄 행 | 평탄 행 |
| `run_S6C`·`run_S8C`(V-6) | `batch_meta.json identity_start/end.orig_argv` | 행별 `exit_code`, `all_rc_zero`, batch.json exit_code | identity(git HEAD·status) | identity(env, affinity) | 확인 필요 | `k2_row.json`의 tag·k1·tcl·floor만 |
| `s9_batch`(V-7) | batch.json argv | batch.json rc | 확인 필요 | `--threads`·`OMP_WAIT_POLICY`·hull hook | record-v7 | 해당 없음 |

- 경로 1·2 모두 sidecar와 batch_meta 신원을 읽지 않는다.
- 제안: 실행 전 감사와 판정 후 감사(verif-protocol-auditor `record_check identity`)에서 다음 둘을 전수 확인하는 것을 G-S·G-F 조건으로 둔다.
  - sidecar 68 − 6(Chrono·V-7) = 62개
  - V-6 `batch_meta` 4개와 V-7 `batch.json`
- 내용: 모든 rc = 0, HEAD = `{RUN_HEAD}`, 시작·끝 clean, 마스크 = 배치표 값.

## 6. 남은 막힌 것

| # | 내용 | 담당 |
|---|---|---|
| R-1 | 묶음 HEAD 병합과 고정 checkout 생성. 생성 뒤 위 0절 blob을 `git rev-parse`로 대조 | 메인 세션 |
| R-2 | 배치표: `{POOL}`·`{MASK}`·`{WORKERS}`·`{PLACEMENT}`·`{L2B_WORKERS}`·`{P}`·`{PLAN_ID}` | compute-scheduler-expert |
| R-3 | V-6 행 폴더 이름이 `<batch-dir>\<행 이름>`인지 | cad-expert(확인) |
| R-4 | 실행 전 감사 | verif-protocol-auditor |

(앞 판의 B-g8·B-ps7·B-V5·B-V6-dhat·B-V6-cost는 `c77ecf5`·`09f66c4`로 처리됐다. 각 수정은 실행 전 감사에서 blob으로 확인한다.)

## 7. 판정서 주석으로 남길 것

- **D̂ 행정 기준 차이(rev1 4 (a), 기록 전용)**: 하네스 `k2.dhat_window_stroke_mm`는 `sref` 기준이고, Chrono V-6은 `GetMotorPos` 기준이다(1 ms `k2_valve.npz`). 하네스와 Chrono 사이 수치 비교에는 쓰지 않는다. 묶음 안의 off·K-2 짝 비교는 같은 기준이다.
- 경로 1·2 모두 V-6 D̂를 `k2_row.json`의 `k2` 블록에서 읽는다. 경로 1은 `c77ecf5`, 경로 2는 1.2이고 시험 `test_chrono_row_dhat_from_k2_block`으로 확인했다.
- V-7은 경로 2 밖이다(기록 전용, 경로 1 `record-v7`만).
- V-5 regression은 판정 93, 기록 49다(3절, rev2 2).

## 8. 러너 띄우는 순서 (감사 6, rev2 5)

러너(`sched/runners`)는 E 쪽 의존을 스스로 강제하지 않는다(E_V6 `$WaitArguments = $null`). 러너 파일은 배치표 sha로 고정돼 있으므로 고치지 않고, **메인 세션이 아래 순서로 띄운다.**

1. **E_pre** (`k2run_E_pre.ps1`): `snaps-k2 --dry-run`을 돌린다. 로그(`sched\logs\E_pre`)의 JSON에서 `existing`에 `S6_crawler_top_k2pp025`가 있고 `missing`이 비어 있으며 exit 0이어야 한다. 아니면 멈추고 묻는다.
2. **E_V6_off·E_V6_tcl** (`k2run_E_V6_off.ps1`, `k2run_E_V6_tcl.ps1`): 1이 끝난 뒤에만 띄운다.
3. 두 V-6 러너 프로세스가 살아 있고 배치 폴더(`07_results\S6\k2v6_L1_*`, `07_results\S8\k2v6_L2b_*`)가 생겼는지 확인한다.
4. **E_V7** (`k2run_E_V7.ps1`): 3을 확인한 뒤에만 띄운다. 먼저 띄우면 `--proc-absent` 대기가 바로 통과한다.

P 쪽 `P_main` → `P_post`는 1~4와 무관하다(`P_post`는 `.done` 36개를 기다린다).

## 9. 판정 명령 (경로 2, 결과가 모두 들어온 뒤)

```powershell
# E코어, dynamics-dev, 이 브랜치(병합 뒤 main) 기준
& C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B 04_scripts\03_control\k2\k2_recount.py recount `
    --manifest 06_analysis\02_control\k2\prelaunch\k2_manifest.json --expect 06_analysis\02_control\k2\prelaunch\k2_expect.json `
    --fields 06_analysis\02_control\k2\prelaunch\k2_fields.json --rules-dir 06_analysis\02_control\k2 --out <판정 폴더>\k2_path2.json
```

- 실행 전에 `selftest-v5-stored --acc 06_analysis\02_control\touch_phase\acceptance --ps7 06_analysis\02_control\touch_phase\ps7_E.json`(rev4 2 형식 점검, 2026-11-10 통과)를 다시 돌려 통과를 확인한다.
- V-5 regression 키는 두 팔 출력에서 `prelaunch/regression_keys.py keys`와 같은 정의로 다시 낸다. 경로 2가 내부에서 sha를 대조한다.
