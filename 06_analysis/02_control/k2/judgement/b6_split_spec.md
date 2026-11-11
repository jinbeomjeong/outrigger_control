# K-2 V-5 B-6 가름 실행 명세 (D-5, 실행 전 명세)

- 작성: control-expert, 2026-11-11. **이 명세는 실행하지 않았다.** 실행은 메인 세션이 띄운다.
- 근거
  - 원판 10.1 B-6: "실패 키만 끔·K-2로 다시 돌려 가름(원인 분석, 합격 수는 바꾸지 않음)"
  - 사용자 결정 D-5(2026-11-11)
  - 판정 후 감사 `k2_post_audit.md` "D-5 덧붙임"
- 판정서: `k2_judgement.md` 3.2 A3·A4

> **기록 전용**: 이 실행의 결과는 K-2 판정(등급 "판정 불가", G-D 실패)과 V-5 합격 수를 바꾸지 않는다. **합격 수를 바꾸지 않는다.** 결과는 원인 분석의 기록으로만 쓴다.

## 1. 목적

| # | 대상 키 | 물음 | 가름 방법 |
|---|---|---|---|
| S | 토양 `A\|J2\|FL\|Fs8\|two`(회차 1 `ready`/`SS`) | K-2 실패가 "창 끝(60 s) 여유 0"(끔 팔이 마지막 표본에서 READY)에서 생긴 작은 시간 이동인가 | ① 같은 명령의 재현(명령 해시가 저장값과 같은가). ② 회차 1의 `t_ready_back`·최종 단계·자세·힘 비교 |
| G | G8 `L2\|s{6,8,10,16}\|g8\|29\|slope\|rpB\|top\|4.0\|RL\|raised\|230.0`(구동기 조합 태그 `off`) | K-2가 TOUCH에서 바꾼 행정이 52.6 s의 FR 행정 가드(682.8 mm)까지 어떻게 이어지는가 | ① 재현(명령 해시). ② `trace: true`로 LEVEL 주기마다 다리 행정 `m`·`r`, 힘 `F`, 단계, 가드 모드, 틈 추정을 기록해 두 팔을 맞댄다 |

- 창 연장(토양 `MAX_AFTER_S` 60 s → 더 길게)은 코드 상수라 이 명세에 넣지 않는다. 필요하면 python-expert가 기록 전용 env 옵션을 따로 추가한다(blob 고정·공개). 이것은 별도 결정이다.

## 2. 실행 정체성

| 항목 | 값 |
|---|---|
| 실행 checkout | **k2-run 잠김 사본을 그대로 쓴다**: `C:\workspace\outrigger_control\.claude\worktrees\k2-run`, HEAD `6a44ff81d25aea1fa162daf9b14c23b99beb9db0`. 시작·끝 clean(`git status --porcelain --untracked-files=no` 빈 문자열). 이유: V-5 원 실행과 같은 코드라야 재현 비교가 성립한다. 이 checkout에는 아무것도 쓰지 않는다 |
| 구동기 blob | `04_scripts/03_control/s9/s9_soil_event_screen.py`, `04_scripts/03_control/touch_phase/acceptance/acc_launch.py`, `06_analysis/02_control/touch_phase/acceptance/g8_safe_stop/g8trace.py`, `04_scripts/03_control/k2/run_with_identity.py`, `03_src/outrigger_sim/control/c2.py`(작업 사본 sha256 `f58ee42b…`). 실행 전 기록에 `git -C <k2-run> rev-parse 6a44ff8:<경로>` 값을 적는다 |
| 인터프리터 | `C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B`(3.12.x). 실행 전 기록에 `sys.version`을 적는다(감사 Q2 재발 방지) |
| 마스크 | E코어 `0x0FFF0000`. 래퍼를 띄우는 셸을 먼저 고정한다. 래퍼는 affinity를 바꾸지 않는다. 원 실행은 P코어 `0xFFFF`였지만, 하네스는 스레드 1개라 비트 결과가 마스크와 무관하다고 본다(재현 해시로 확인한다). 비용 측정이 아니다 |
| 출력 폴더(main checkout, 미추적) | `C:\workspace\outrigger_control\06_analysis\02_control\k2\judgement\b6\{off,tcl}\` |
| sidecar | `…\judgement\b6\<arm>\soil_b6.launch.json`, `…\judgement\b6\<arm>\g8_b6.launch.json` |
| 실행 전 기록 | `…\judgement\b6\b6_prelaunch.json`. 내용: 이 명세 sha256, checkout HEAD·clean, 구동기 blob, 인터프리터 버전, 마스크, G8 작업 파일 sha256, 기대 해시(4절), 문구 "기록 전용, 합격 수 불변" |

### 2.1 env (`k2_commands_filled.json`의 원 단계 env와 같고 경로만 바꿈)

공통

```
CONDA_PREFIX=C:\ProgramData\miniforge3\envs\dynamics-dev
CONDA_DEFAULT_ENV=dynamics-dev
PATH=<원 단계와 같은 dynamics-dev PATH>
MKL_THREADING_LAYER=TBB
MKL_NUM_THREADS=1
OMP_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
NUMBA_NUM_THREADS=1
PYTHONDONTWRITEBYTECODE=1
ACC_WT=C:\workspace\outrigger_control\.claude\worktrees\k2-run
```

| 단계 | 추가 env |
|---|---|
| 토양(S) | `ACC_COMBO=preset`, `OUTRIGGER_ACC=k2`, `R426A_SET=all`, `R426A_FILTER=A\|J2\|FL\|Fs8\|two`(쉼표 없는 한 문자열, 부분 일치로 1키), `ACC_PROVENANCE=…\judgement\b6\<arm>\provenance\soil_b6.json`, `ACC_K2=off`(끔) / `on`(K-2) |
| G8(G) | `ACC_COMBO=off`, `R72_PATH=per_leg`, `R79_AFFINITY=0x0FFF0000`, `ACC_K2=off` / `on` |

## 3. 명령 (팔마다 2단계, 모두 4단계·약 10실행)

`<run>` = `C:\workspace\outrigger_control\.claude\worktrees\k2-run`, `<b6>` = `C:\workspace\outrigger_control\06_analysis\02_control\k2\judgement\b6`, `<py>` = `C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe`, cwd = `<run>`.

### 3.0 G8 작업 파일 (실행 전에 한 번)

- `<b6>\g8_b6_jobs.json`: 다음 4개 항목을 **원문 그대로** 옮기고 각 항목에 `"trace": true`만 더한다.
  - `<run>\06_analysis\02_control\touch_phase\acceptance\g8_safe_stop\jobs3.json`(sha256 `bb6c2f55…954c`) 색인 23·27·31
  - `jobs5.json`(sha256 `2195c6fb…fc51`) 색인 16
  - 4개 모두 `"tag": "off"`, 키는 s6·s8·s10·s16, `"kwargs": {}`다.
- `trace`는 g8trace의 기록 훅(`traced_level`)이 모으는 목록을 출력에 붙일 뿐이다. 훅은 `trace`와 무관하게 항상 설치되므로 명령에는 영향이 없다(재현 해시로 확인한다).
- 파일 sha256은 실행 전 기록에 적는다. 만드는 스크립트는 Write로 파일에 쓰고 `python -I`로 돌린다.

### 3.1 토양

```
<py> -I -B <run>\04_scripts\03_control\k2\run_with_identity.py <b6>\<arm>\soil_b6.launch.json --git-dir <run> --
  <py> -I -B <run>\04_scripts\03_control\touch_phase\acceptance\acc_launch.py
  <run>\04_scripts\03_control\s9\s9_soil_event_screen.py <run> <b6>\<arm>\soil_b6.json 1
```

- 실행 전에 `R426A_FILTER`가 정확히 1키를 고르는지 확인한다. 같은 env로 `s9_soil_event_screen.py <run> --list`를 돌려 출력이 `A|J2|FL|Fs8|two`와 "1 jobs, 5 branches"인지 본다.

### 3.2 G8

```
<py> -I -B <run>\04_scripts\03_control\k2\run_with_identity.py <b6>\<arm>\g8_b6.launch.json --git-dir <run> --
  <py> -I -B <run>\06_analysis\02_control\touch_phase\acceptance\g8_safe_stop\g8trace.py
  <run> <b6>\g8_b6_jobs.json <b6>\<arm>\g8_b6.jsonl --workers 4
```

- 팔은 `<arm>` ∈ {`off`, `tcl`}이다(`ACC_K2` = `off` / `on`).
- 예상 시간: 토양 약 70 s/팔, G8 약 15 s/작업(4 worker)이다. 합계는 5분 안팎이다. 띄우기 전에 compute-scheduler-expert의 배치를 받는다(마감을 주어 E코어로 보낸다).

## 4. 판정 기준 (기록 전용)

### 4.1 재현 확인

저장 V-5 행과 같은 명령 해시가 나와야 한다.

| 키 | 끔 | K-2 |
|---|---|---|
| 토양 base | `f2056a39…66ec0` | `8f1f881c…07564` |
| 토양 회차 1(ready/SS) | `70f016ca…38b9a` | `0daa8ca8…29a43` |
| 토양 나머지 회차 0·2·3·4 | 저장 `runs/v5/off/soil_A.json` 값 | 저장 `runs/v5/tcl/soil_A.json` 값 |
| G8 s6 / s8 / s10 / s16 | `c7b4bb5f…` / `3198d97c…` / `018ece9c…` / `e042eeda…` | `725c7bc9…` / `ef6da615…` / `db8fd9e7…` / `1597b9f3…` |

- 다르면 마스크·env 차이를 먼저 의심한다. 그 행은 "재현 불가"로 기록하고 가름에 쓰지 않는다.

### 4.2 가름 기록

| 대상 | 기록 내용 | 해석 규칙 |
|---|---|---|
| S | 회차 1의 `final_phase`, `t_ready_back_s`, `att_end_deg`, `min_F_after_event_kN`, 단계 경과(`base.timeline`) | 끔 팔 `t_ready_back` = 창 끝(60.0 s)이고 K-2 팔이 창 끝에 아직 `probe`면 "창 끝 여유 0에서 생긴 시간 이동"(판정서 A3)으로 기록한다 |
| G | 행정 `m`(모터)·`r`(로드) FR, 단계별 FR 행정 차(K-2 − 끔), 첫 차이가 생긴 주기, 가드 모드 `gm`, `lim`, 틈 추정 `ce`·`tg`, TOUCH 래치 시각, `stroke_at_latch_mm` | 차이가 TOUCH(K-2 크리프) 구간에서 시작해 LEVEL 끝까지 유지·누적되고, 끔 팔의 FR 최대 행정이 가드까지 0.3 mm 안이면 "행정 예산 여유 0 + K-2 행정 이동"(판정서 A4)으로 기록한다 |

## 5. 하지 않는 것

- V-5 합격 수, G-D 값, 등급을 바꾸지 않는다.
- k2-run checkout과 `runs/` 결과 원본에 쓰지 않는다.
- 다른 키·묶음으로 넓히지 않는다(넓히려면 이 명세를 개정한다).
- 결과를 보고 K-2 수치를 바꾸지 않는다. K-2b는 D-2에 따라 dynamics-expert 확인 뒤 별도로 설계·봉인한다.

## 6. 끝난 뒤

- 이 명세의 기록표를 `k2_judgement.md` 부록으로 덧붙인다(control-expert).
- sidecar 4개를 정체성 확인에 넣는다: rc 0, HEAD `6a44ff8` clean, env, 마스크 `0x0FFF0000`.
