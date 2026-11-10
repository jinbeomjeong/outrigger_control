# K-2 V-2~V-7 실행 전 묶음 (초안, 실행 안 함)

- 작성: control-expert, 2026-11-10. 브랜치 `k2-prelaunch`(master `dc2029b` 위).
- 규칙: `k2_touch_creep_rules.md`(봉인 `a3658197…7263`) + `k2_touch_creep_rules_rev1.md`(봉인 `5ba081c6…4776`). dynamics 명세 `k2_dyn_spec.md`(`502b0bb7…27ff`).
- **이 폴더는 실행 전 기록의 초안이다.** `{RUN_HEAD}`, `{POOL}`, `{MASK}`, `{WORKERS}`, `{P}`, `{PLAN_ID}`, `{BATCH_*}` 자리는 배치표와 실행 시작 때 채운다. 채운 뒤 `make_prelaunch.py`를 다시 돌리면 입력 sha가 다시 계산된다.

## 0. 묶음 HEAD

- `{RUN_HEAD}`는 master에 다음 두 브랜치를 병합한 커밋이다.
  - `k2-v7k1-dhat`(cad-expert `bf3f475`: V-7 K1 켬, V-6 `k2_row.json`에 D̂ 기록)
  - `k2-prelaunch`(이 브랜치: `k2_recount.py` 1.2, 이 폴더)
- 실행은 그 커밋의 고정 checkout(`git worktree add C:\workspace\outrigger_control\.claude\worktrees\k2-run {RUN_HEAD}`)에서만 한다. 결과는 그 checkout의 `06_analysis/02_control/k2/runs/` 아래에 쓴다(추적 안 함).
- `k2_recount.py` 1.2의 blob은 `d2240795f06893eb2d3eca6e61c55b6dd6c60eeb`(`git hash-object`)다. 1.1(`9ada2f2`)에서 바뀐 것은 두 가지다.
  - 시계열 폴더를 파일마다 `<stem>_series`로 찾는다(acc_d8 기본값과 같다). off·K-2 파일이 같은 행 이름의 시계열을 따로 가지기 때문이다.
  - `k2.dhat_window_stroke_mm`의 `None`(닫힌 다리)을 건너뛴다(k2_record 형식).
  - 어느 결과에도 1.1은 쓰이지 않았다.

## 1. 파일

| 파일 | 내용 |
|---|---|
| `make_prelaunch.py` | 아래 파일을 모두 만든다(읽기만, 실행 없음). `--run-wt`, `--ra-off` |
| `k2_commands.json` | 62단계: argv(인터프리터 절대경로), cwd, env, 출력, 신원 sidecar 경로, 풀 자리 |
| `k2_manifest.json` | 경로 1(`k2_judge.py`)·경로 2(`k2_recount.py`) 공용 입력. `points`(경로 1)와 `points_file`(경로 2)가 같은 파일 |
| `k2_expect.json` | `k2_recount expect-template` + g8 83 |
| `k2_fields.json` | 경로 2 필드 지도(= `DEFAULT_FIELDS`), sha 고정용 |
| `k2_v3_keys.txt` | V-3 273키(규칙 3.3 선정, 정렬 목록 sha `d4a030d7…`) |
| `k2_prelaunch_v2.json` … `v7.json` | 실행 전 기록 초안: HEAD, 원판·rev1·명세 sha, 경로 1·2 blob, 점 파일 sha(`a15cbe95…` / D8x `d8x_points.json`), 입력 sha, 스레드, 풀 자리, notes 세 문구 |

## 2. 실행 명령 (요지, 정확한 argv는 `k2_commands.json`)

공통 env(하네스): `CONDA_PREFIX`·`PATH` = dynamics-dev, `MKL_THREADING_LAYER=TBB`, `MKL/OMP/OPENBLAS/NUMBA_NUM_THREADS=1`, `PYTHONDONTWRITEBYTECODE=1`. 인터프리터 `C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B`. Chrono는 `C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe -I -X utf8 -u`.

| 묶음 | 단계 | 명령 핵심 |
|---|---|---|
| V-2 | 4 | `acc_d8.py <out> --points d8x_points.json --stages main,robust,kt --k1 off --k2 off\|on` (910) / `--stages main --k1 on` (192). 시계열은 `<out stem>_series` |
| V-3 | 14 | `acc_d8.py <out> --points d8x_points.json --stages main,robust,kt --k1 off --k2 off\|on --aug <H0\|L1eq\|L1eq_fs\|L1eq_zm\|AUG\|AUG_crc2\|AUG_eps> --keys-file k2_v3_keys.txt` |
| V-4 | 2 | `acc_d8.py <out> --points k2_points_5p5_3p5.json --stages main,robust,kt --levels top --k1 off --k2 off\|on` |
| V-5 | 36 | 저장 인수 단계(`steps_E1/E2.json`의 reg1~7, grid_r67_main·top, grid_r69_top·bottom, soil_A, d8, noise_L1L2)를 고정 checkout으로 옮김. `acc_launch.py <script> …`, env `ACC_WT=<k2-run>`, `ACC_COMBO=preset`, **`ACC_K2=off\|on`**, `ACC_PROVENANCE=<runs/v5/<arm>/provenance/<id>.json>`. 출력은 `runs/v5/<off\|tcl>/`. 추가: PS-7 `acc_launch.py run_ps7.py E --workers {W} --mask {MASK}`, G8 `g8trace.py <k2-run> g8_safe_stop/jobs{1,3,5}.json <out.jsonl> --workers {W}`(env `ACC_COMBO=off`, `ACC_K2`) |
| V-6 | 5 | 먼저 `run_S6C.py snaps-k2 --jobs 1`(`--dry-run`로 먼저 확인). L1: `run_S6C.py run --set k2_v6 --approved --jobs 2 --k2 off\|on --k1-order-gate off --expect-controller final_C4G2_LAS(_TCL) --pad-zeta-moving 0.1 --tag k2v6_<arm>`. L2b: `run_S8C.py run --set k2_v6 --approved --workers {W} --k2 off\|on --k1-order-gate off --expect-controller final_C4G2_LAS(_TCL) --tag k2v6_<arm>` |
| V-7 | 1 | `s9_batch.py run k2_v7 --parallel {P} [--parallel-e …]`, env `OMP_WAIT_POLICY=PASSIVE`. 행 `K2V7_P3b_J1_B_top_Fs4_off\|tcl`, `K2V7_P3b_J2_B_top_Fs4_off\|tcl`, 태그 `final_C4G2_LAS_K1` / `final_C4G2_LAS_K1_TCL`(K1 켬, 사용자 결정), 기록 전용 |

- acc_d8 D8x 모드는 `ACC_K2`가 env에 있으면 멈춘다. V-2~V-4 단계 env에는 `ACC_K2`를 넣지 않았다.
- V-5 d8 단계는 acc_d8의 옛 모드(`--points` 없음)라 `ACC_K2`로 팔을 정한다.

## 3. 배치표 입력 (compute-scheduler-expert)

CPU 시간은 worker-초다. **추정 근거**:
- R-a 910행 992 s × P 8 = 8.7 s/행(P).
- 진단 상단 596행 923 s × P 8 = 12.4 s/행(P).
- K-2 기록·시계열 부담 ×1.15(**가정**).
- V-5는 저장 인수 실행의 행별 wall 합(E코어, 2026-11-04~05)이고, P 환산은 E/1.7(**가정**)이다.
- PS-7·G8은 행당 60 s·50 s로 **가정**했다.

| 묶음 | 단계 | 행(팔당) | 팔 | P worker-s (합) | 짝 규칙 |
|---|---|---|---|---|---|
| V-2 | 4 | 1,102 (910 + 192) | 2 | 약 22,000 | 같은 K1 칸의 off·tcl은 같은 풀 |
| V-3 | 14 | 273 | 7 × 2 | 약 54,600 | 같은 aug 팔의 off·tcl은 같은 풀 |
| V-4 | 2 | 596 | 2 | 약 17,000 | off·tcl 같은 풀 |
| V-5 | 36 | 잡음 1,026, 격자 80결과(768), D8 576, 토양 16결과(60), 회귀 7단계(118), PS-7 20, G8 83 | 2 | 약 78,000 (E 약 133,000) | 같은 단계 id의 off·tcl은 같은 풀 |
| V-6 | 5 | snaps 1 + L1 2배치(행 2) + L2b 2배치(행 2) | 2 | cad-expert `--dry-run`의 추정 필요(**미정**) | L1 off·tcl 같은 풀, L2b off·tcl 같은 풀 |
| V-7 | 1 | 4행 | 2 | 약 44,000 (행당 11,000 s, P) | 같은 토양 행의 off·tcl 같은 풀 |

- 하네스(V-2~V-5)는 합해 약 172,000 P worker-s다. P 8 worker로 약 6.0 h 걸린다.
- 풀 상황: P코어 `0xFFFF`는 비어 있다. E코어는 격자 시험 GC 4행이 20~25분 쓴다.
- 이 표는 판정과 무관하다.

## 4. 행 신원 기록 점검표 (argv·rc·HEAD·env 어디에, 누가 읽나)

격자 시험 감사의 함정(직접 실행기가 batch.json의 argv·rc를 남기지 않아 argv 조항이 검사 없이 지나감)을 K-2 실행기마다 확인했다.

| 실행기 | argv | rc | HEAD·clean | env(스레드·마스크) | 경로 1 | 경로 2 |
|---|---|---|---|---|---|---|
| `acc_d8.py`(V-2~V-4, D8x 모드) | **원시 argv 없음.** `meta.d8x`에 k1·k2·aug·levels·keys_file(sha)·points sha·stages·series_dir | **없음** | `meta.d8x.identity_start/end.git`(HEAD·clean), `meta`(acc_common provenance: git_head·combo) | identity_start(스레드·affinity) | 확인 필요(prelaunch가 봉인·git 상태를 봄) | **읽지 않음**(행 수준 tag·k1·tcl·aug만) |
| `acc_launch.py`(V-5 대부분, PS-7) | `ACC_PROVENANCE` 파일에 script·argv | **없음** | provenance git_head(clean 없음) | provenance threads(마스크는 스크립트 인자에만) | 읽지 않음 | 읽지 않음 |
| `run_ps7.py` | 위 provenance | 없음 | 위 | 위 | 읽지 않음 | 읽지 않음. 출력에 태그·`touch_creep_latch` 없음 |
| `g8trace.py`(G8) | **없음** | **없음** | **없음** | 없음(행에 `touch_creep_latch`·`controller_tag`만) | 읽지 않음 | 읽지 않음 |
| `run_S6C.py`·`run_S8C.py`(V-6) | `batch_meta.json k2`(행·팔·기대 태그·게이트), `result.json touch_creep_requested/effective` | 확인 필요(cad-expert) | 확인 필요 | 확인 필요 | 확인 필요 | `k2_row.json`의 tag·k1·tcl·floor만 |
| `s9_batch.py`(V-7) | batch.json argv(행마다) | batch.json rc | 확인 필요 | `--threads`·`OMP_WAIT_POLICY`·hull hook | record-v7 | 해당 없음(V-7은 경로 2 밖) |

**대책(제안)**
1. 모든 단계를 신원 sidecar(`k2_commands.json`의 `identity_sidecar`)를 쓰는 래퍼로 띄운다. sidecar에는 정확한 argv, cwd, env 부분집합, affinity 마스크, 시작·끝 시각, **종료 코드**를 담는다. 시작·끝의 `git rev-parse HEAD`와 `git status --porcelain --untracked-files=no`도 넣는다.
   - compute-scheduler-expert `make_runner` 로그가 이 항목을 다 남기면 그것으로 대신한다.
2. 경로 1·2 모두 지금은 sidecar를 읽지 않는다.
   - 실행 전 감사와 판정 후 감사(verif-protocol-auditor `record_check identity`)에서 sidecar 전수를 확인하는 것을 관문 G-S·G-F의 조건으로 둘 것을 제안한다.
   - 경로 도구가 직접 읽게 하려면 결과 전에 도구를 바꿔야 한다(경로 2는 control-expert, 경로 1은 python-expert).

## 5. 막힌 것 (실행 전에 고쳐야 함)

| # | 내용 | 담당 |
|---|---|---|
| B-g8 | `g8trace.py` 18행이 `acc_common`을 `acceptance/c4g2k1`(옛 scratch 폴더, 저장소에 없음)에서 import한다. `-I` 실행이라 시작하자마자 ImportError가 날 것이다(**추정**, 코드 읽기로 확인). G8 단계 6개가 돌지 못한다 | python-expert |
| B-ps7 | `run_ps7.py`는 출력이 `touch_phase/ps7_<cand>.json`으로 고정이다. 저장소에 추적되는 `ps7_E.json`을 덮어쓴다(작업 사본 dirty, 두 팔 충돌). `--out` 인자를 추가하거나 단계 뒤 옮기고 되돌려야 한다. 또 출력에 `controller_tag`·`touch_creep_latch`가 없어 E-4·E-6을 볼 수 없다 | python-expert |
| B-V5 | V-5 판정 입력 형식: 두 경로의 `v5_bundle`은 평탄한 행(`key`, `pass`, g8은 `ready`·`faults`)을 읽는다. 저장 구동기 출력(r67/r69 `results[].runs[]`, 토양, 회귀 clip, r79 판정, D8 `fails`)은 중첩 형식이다. **기존 스크립트 판정을 평탄 행으로 옮기는 변환기**(`k2_v5_flatten.py`, criteria.md의 "각 스크립트의 기존 판정 그대로")가 결과 전에 있어야 한다. 실행은 할 수 있고 판정만 막힌다. 변환기는 두 경로가 공유하는 입력이 되므로 결과 전 blob 고정이 필요하다 | python-expert(작성), control-expert(검토) |
| B-V6-dhat | 경로 1 `k2_judge.py` V-6은 D̂를 `row.get("dhat_N")`(최상위, 1026행)에서 읽는다. cad-expert는 `k2_row.json`의 `k2` 블록에 넣었다. 경로 2는 `k2.dhat_N`을 읽는다. 이대로면 경로 1의 V-6 D̂ 기록이 비어 두 경로 기록 수치가 다르다(규칙 8 일치 기준). 경로 1이 `k2.dhat_*`를 읽도록 맞춘다 | python-expert |
| B-V6-cost | V-6 Chrono 행당 비용과 결과 폴더 이름(`{BATCH_*}`) | cad-expert |

## 6. 판정서 주석으로 남길 것

- **D̂ 행정 기준 차이(rev1 4 (a), 기록 전용)**: 하네스 `k2.dhat_window_stroke_mm`는 `sref`(모터 명령 적분) 기준이고, Chrono V-6은 `GetMotorPos` 기준이다(cad-expert, 1 ms `k2_valve.npz`). 하네스와 Chrono 사이 수치 비교에는 쓰지 않는다. 묶음 안의 off·K-2 짝 비교는 같은 기준이다.
- V-7은 경로 2 밖(기록 전용, 경로 1 `record-v7`만)이다. 규칙 8의 두 경로 일치 대상이 아니다.
