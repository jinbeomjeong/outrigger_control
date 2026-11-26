## 판 8 준비 P-1~P-3 구현 보고 (python-expert, 2026-11-26)

판 8 준비용 기록 키(P-1·P-2)와 probe 드라이버(P-3)를 만들어 worktree 브랜치에 커밋했습니다. 명령 불변 시험과 관련 시험은 모두 통과했습니다. 7개 비교 줄 가운데 V0를 뺀 6개는 줄 내용·T4h 배열·T4h meta까지 판 7 C 출력과 같습니다(V0는 T4h를 쓰지 않음). master 병합과 push는 하지 않았습니다.

**의존성 점검:** 생략(이 세션 STAMP, 필요한 도구 모두 있음).

### worktree와 커밋
- worktree `C:\workspace\outrigger_control\.claude\worktrees\ed8-impl`, 브랜치 `ed8-impl`, 기준 C `8a2a52ce`
- 커밋 **`7fc83456`**("436.9 ed8 prep P-1 .. P-3 …"). `git status` 깨끗함.
- **T′(`60ebb4a4`)는 병합하지 않았습니다.** T′의 `test_ed7_judge.py::test_run_path_modules_are_the_run_commit_bytes`가 C의 실행 경로 모듈 바이트가 같다고 단언합니다. P-1·P-2가 `c2.py`와 `lock_start_b.py`를 바꾸므로, 병합하면 이 시험이 설계상 실패합니다. 판정 도구는 잠긴 `ed7-judge` worktree에서 실행만 하면 됩니다. 판 8 판정 도구를 이 브랜치에 들일 때 그 시험의 기준 목록을 판 8 실행 커밋으로 바꿔야 합니다.
- `ed7-impl`·`ed7-judge`는 열람·실행하지 않았습니다. 정션·링크도 만들지 않았습니다.

### 바뀐 파일
| 파일 | 내용 |
|---|---|
| `03_src/outrigger_sim/control/c2.py` | **P-1**: 탐침 라운드가 끝날 때마다 기록을 남깁니다(`_record_probe_stiffness`, `probe_stiffness_record()`)<br>· 다리별 `k1_N_m`·`k_nom_N_m`·`ratio`·`is_scale_leg`·접지·skip·역순·탐침 시각<br>· 라운드의 `raw_ratio`(원비)·`scale_leg_count`·`is_warned`·`warning_range`·`twist_stiffness_scale`·`scale_in_use`<br>· 기존 비율 조건식은 `_is_stiffness_scale_leg`로 뽑았고 의미는 같습니다<br>· 상태 필드는 옛 pickle을 고려해 불변 클래스 기본값 `()`로 두었습니다 |
| `03_src/outrigger_sim/control/lock_start_b.py` | **P-2**: `A_ib`가 켜진 LEVEL 주기마다 다리별로 처음 실패한 시험을 기록합니다(`BlindBlock`)<br>· 사유: `condition_1_none`/`condition_1_short`/`priority`/`condition_2`/`condition_3`/`protect`/`latch`/`latched`/`floor_on`/`trigger`<br>· 집계: 다리별 합계, LEVEL 구간(stretch)별 합계, 읽기별 int8 코드 `lsb_ib_block`(LEVEL 밖 = −1)<br>· 키는 0 건수까지 모두 둡니다<br>· `_is_blind_trigger`를 사유를 돌려주는 `_blind_block_reason`으로 바꿨습니다. 검사 순서와 NaN 처리는 그대로입니다 |
| `04_scripts/04_hydraulic/coupled/verdict_runs.py` | 프로세스 스위치 `enable_ed8_record()`(기본 꺼짐)<br>· 켜면 줄과 T4h meta에 `probe_stiffness_record`·`ib_block_record`, T4h에 `lsb_ib_block`을 씁니다<br>· `ib_block_record`와 `lsb_ib_block`은 `A_ib`가 켜진 줄에만 있습니다 |
| `04_scripts/04_hydraulic/coupled/run_v5.py` | 줄 복사 키 묶음을 상수 `LINE_RECORD_KEYS`로 빼고 새 키 2개를 끝에 더했습니다. 순서는 그대로입니다 |
| `04_scripts/04_hydraulic/coupled/ed8_probe.py`(새 파일) | **P-3** probe 드라이버. `ed7_probe.py`는 그대로 둡니다(654 jobs 시험 통과) |
| `05_tests/unit/test_ed8_records.py`(새 파일) | 하네스 없는 단위 시험 28개 |
| `05_tests/unit/test_ed8_harness.py`(새 파일) | dynamics-dev 하네스 시험 6개 |

`ed8_probe.py`의 구성
- **팔 (가)**: ed7 팔 a1~a6·c2에 **`a2w`**를 더했습니다. a2w는 a2에서 (i-b)만 끈 팔이고, `probe_d6_settings` = `{"witness": True, "retract_position_target": False}`입니다. 기존 플래그를 그대로 써서 새 옵션은 만들지 않았습니다.
- **플랜트 (다)**: M, M<key>(감도 10키), **LSM1~4**, L.
  - P8-M-a2의 옵션은 VBM, P8-LSM<n>-a2는 LSM<n>, P8-M<key>-a2는 VBM<key>와 같습니다(단위 시험으로 확인).
- **키 지정 (나)**: `--part main,d,j9main,file`
  - `j9main`은 `ed7_j9_main`의 388행을 그 행의 설정에 맞는 플랜트에 올립니다.
  - `file`은 `--jobs-file`(job 목록 또는 봉인 키 파일 꼴 `{"lines":[{"job":…}]}`)을 받습니다.
  - `--keys`로 행 이름(`R12_top-FR-Fs0-o0.05` 등)을 골라 거릅니다.
- 출력 규칙
  - 이미 있는 `--out`은 거부합니다(종료 2). `--resume`이면 같은 계획일 때만 이어 씁니다(`<stem>.selection.json`의 `plan_sha256` 대조).
  - 진행 파일 `<stem>.progress.json`: `stage`·`done`·`total`·`unit`·`started_at`·`updated_at`(판정값 없음).
  - 종료 코드: 0 정상 / 1 오류 줄 / 2 입력 오류 / 3 도구 오류.
- 전체 기록 probe 계획: `--part j9main,file,d --jobs-file sens_keys_ed7.json --list` → **1744 jobs**(= 2팔 × (388 + 460 + 24)), `plan_sha256 bd04579b…`, 종료 0.

### 명령 불변 증명
- **변경 전(C, 편집 전 ed8-impl)**: 아래 8 job 모두 저장 `commands_sha256`과 같았습니다(8/8).
- **변경 후, 스위치 꺼짐(`test_ed8_harness`)**: 모두 같았습니다.

| 대표 job | 기대값 출처 | 해시 앞 8자 |
|---|---|---|
| V0 S8 e0 | `v5/main.jsonl`(sha `9ad74990…`) | `67c4494d` |
| VB R10 e0.002 | `v5/main.jsonl` | `3c0a2db2` |
| VBM S8 e0 | `8a2a52ce/j9main_a1/j9_main.jsonl` | `09d2c988` |
| VBM R12 top-FL-Fs8 o0.0(강성 경고 키) | 같은 파일 | `906bcf42` |
| VBM0 S2 e0.002 | `impl_t8_a1/ed7_t8.jsonl` | `4bfb2684` |
| LSM4 R12 top-FR-Fs0 o0.05(F3 꼬리 키) | `j9_main.jsonl` | `e5aec722` |
| VBMslow R16 o0.075 | `sens_a1/sens.jsonl` | `d87037c6` |
| P7-M-a2 R2 e0.003(`ed7_probe.py`) | `impl_probe_a1/ed7_probe_a2.jsonl` | `f329c5ef` |

- 변경 전후 비교는 check runner 보고 전체(`wall_s` 제외: line_keys, lsb_record, probe_d6_record 등)와 T4h npz로 했습니다. V0를 뺀 6개는 모든 배열과 meta까지 같습니다. V0는 T4h를 쓰지 않습니다. 비교 대상은 `ed7_check_runner.py`로 돈 7 job이고, P7-M-a2(`ed7_probe.py`로 돈 줄)는 해시만 비교했습니다.
- **스위치 켬(probe 줄)**: P8-M-a2(R12 FL-Fs8, S8), P8-LSM4-a2(R12 FR-Fs0 o0.05), P8-Mslow-a2(R16, jobs-file 경로)가 저장된 VBM·LSM4·VBMslow 해시와 같습니다. 즉 기록 스위치는 명령을 바꾸지 않습니다.
- P8-M-a2w R12 FL-Fs8은 a2와 해시가 다릅니다. (i-b)를 끈 효과가 실제로 나타난 것입니다.
- ed7 하네스 시험(P7-0: 판 6 설정의 79495405 해시, VBM 정체성, P7-1)도 통과했습니다.
- VBM0·VBL·V0 계열의 다른 행과 LSM1~3은 이번에 따로 대조하지 않았습니다(대표 키만).

### 시험 결과 (dynamics-dev `python.exe -m pytest -p no:cacheprovider`, `MKL_THREADING_LAYER=TBB`)
- `test_ed8_records.py`·`test_ed7_units.py`·`test_ed6_lock_start_b.py`·`test_c2_r8d1.py`·`test_ed7_run_commit.py`·`test_ed7_adoption.py`·`test_ed7_harness.py`·`test_d0_plant_split.py`, `-m "not slow"`: **367 passed, 9 deselected**(종료 0). 9개는 `test_ed7_harness`의 slow 시험이고 아래에서 따로 돌렸습니다.
- `test_ed8_harness.py`: **6 passed**(122.8 s, 종료 0).
  - 처음 두 번은 **시험 쪽 결함**으로 실패해 시험을 고쳤습니다. 코드는 바꾸지 않았습니다.
    - R16 o0.075는 사건 행인데 head-only로 가정했습니다.
    - V0는 T4h가 없는데 meta 키를 가정했습니다.
    - **steady 행 S8은 탐침 라운드가 없어 `probe_stiffness_record`가 빈 목록입니다.** 키 자체는 있습니다.
    - Counter의 0 키 처리를 잘못했습니다.
- `test_ed7_harness.py` 전체: **7 passed**(145.7 s, 종료 0).
- skip 0, xfail 0. 전체 suite는 돌리지 않았습니다(지시대로).
- 생산자 꼴 시험에 넣은 줄 종류
  - 사건 행: R12, R16+offset
  - steady(head-only 선언) 행: S8
  - LS 플랜트 행, jobs-file 행, 새 팔 a2w
  - 스위치를 끈 run_v5 줄
- 함께 확인한 것
  - 경고가 난 라운드와 `WARN_PROBE_STIFFNESS_OUT_OF_RANGE:<값>` 사건이 서로 하나씩 대응합니다.
  - 블록 사유 다리별 합계 = 구간별 합 = T4h 코드 집계, 그리고 줄 기록 = T4h meta 기록입니다.
  - **미시험: 오류 줄**(기록 없음. `run_one`이 복사 전에 반환하므로 하네스에서 만들지 못했습니다). 이 경로는 생산자 꼴로 시험하지 못했습니다.

### 커버리지 (dynamics-dev pytest-cov, 단위 시험 프로세스 안만)
- 대상 모듈: c2.py 69 %, lock_start_b.py 76 %, ed8_probe.py 78 %, verdict_runs.py 26 %.
- 변경 줄 중 단위 시험이 덮지 않은 줄
  - `c2.py` 3101, 10507~10516(controller 기록 접근자)
  - `lock_start_b.py` 1431~1432(옛 pickle용 늦은 생성. 하네스로도 닿지 않습니다)
  - `verdict_runs.py` 252·336·373
  - `ed8_probe.py`의 실행 경로(install·worker·run_batch·main 실행)
- 접근자, `verdict_runs`, `ed8_probe` 실행 경로는 하네스 subprocess 시험이 지나가지만 측정에는 잡히지 않습니다.

### 도구 종료 코드
- `ruff check --no-cache`(변경 7파일, 프로젝트 `pyproject.toml` 설정): 종료 1, E501 3건 — `run_v5.py` 928·933·937행. 모두 기존 argparse help 줄이고 이번 변경이 아닙니다.
- `codespell`: 종료 65, `ABL` 3건. 기존 태그 이름 `ABL_LAS_K1`라 오탐입니다.
- `ruff format`은 돌리지 않았습니다. 기존 파일들이 포맷되어 있지 않아 범위 밖 변경이 생깁니다.

### j_items_recount 검토 (설계안만, 구현하지 않음)
- **필요합니다.** 판 5·6·7 판정 후 감사가 J3·J4·J5·J7((이름, 다리, 사유))·읽기 (1)·L-a·L-b를 매번 즉석 스크립트로 셌습니다. `pair_recount.py`는 원시 통과 표지만 받습니다.
- 위치: `tools/verif/j_items_recount.py`. `pair_recount`의 설정 JSON 꼴을 잇습니다.
- 설정 JSON
  - 판정 줄·기준 줄 파일과 설정 대응(VBM→V0, LSM<n>→VBM)
  - 키(행·위상) 경로
  - 항목 정의(J1 `event_output.gates`, J3 `values.t_first_ready_s` 한계, J4·J5 `event_output.t_ready_back_s`, J7 이름 집합(숫자 마디 제거)과 (이름, 다리, 사유) 집합 차)
  - 감도 강성 예외 설정 목록
  - L-a 항목 묶음(J1·J2·J4·J6·J7), L-b 상대
- 출력: (설정, 행, 위상, 항목) 실패 집합. 판정 json(`J_vs_V0`·`LS_vs_VB`·`units`)과 집합 차(`only_in_judgement`·`only_in_recount`).
- 규칙
  - 키나 필드가 없으면 판정 불가로 둡니다(0으로 읽지 않음).
  - `fallback_triples`처럼 다리마다 첫 사유만 쓰지 않고 다리의 모든 사유를 씁니다(감사 R-1 차이).
  - 판정 모듈은 import하지 않습니다(독립 재집계).
- 종료 코드: 0 일치 / 1 차이 / 2 입력 오류 / 3 버그.
- 시험: 판 7 실제 줄 꼴(head-only 행, 강성 예외 행, L-b 짝 없음 포함)로 만든 합성 자료로, CWD를 입력과 다른 폴더에 두고 `main`까지 돌립니다.

### 메인 세션 권고
- 판 8 봉인 전 기록 probe(원인 분석 7 A 실험 2). compute-scheduler-expert 배치표를 받고, 출력은 새 커밋 폴더에 둡니다.
  - 명령: `C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B 04_scripts\04_hydraulic\coupled\ed8_probe.py --part j9main,file,d --jobs-file C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\keys_seal_b46bdf8f\sens_keys_ed7.json --arms a2,a2w --out <j9_runs\7fc83456\ed8_probe_a1\ed8_probe.jsonl> --workers 8 --mask <배치표>`(cwd = ed8-impl)
  - 1744 jobs, 줄당 벽시계 약 100~200 s → 8 worker로 약 6~10시간.
  - 30분을 넘으므로 §3 감시와 §4 예약 대상입니다. 진행 파일 `<stem>.progress.json`은 `블라인드 예외(진행 파일)`로 넘길 수 있습니다.

### 확인 필요
- 판 8 실행 커밋을 이 브랜치에서 만들면 새 파일 3개가 worktree에서 LF입니다(`core.autocrlf true`, 기존 파일은 CRLF). 실행 커밋 전에 CRLF 정규화를 끝낼지 정해야 합니다. 커밋 뒤 다시 checkout하면 mtime 검사에 걸립니다.

### 메모리 반영안
- `env_dynamics_dev_no_pytest_cov.md` 갱신: dynamics-dev에 pytest-cov가 생겼고(2026-11-26 확인) xdist는 없습니다. 쓰기 전에 import로 확인합니다.

사용한 스킬: 없음 · scratchpad `python-ed8impl\`은 지웠습니다. 블라인드 경로는 열지도 검색하지도 않았습니다(Grep·Glob은 `03_src`·`04_scripts`·`05_tests`·`j9_runs\8a2a52ce`·`ed7_design` 하위만 직접 지정).
