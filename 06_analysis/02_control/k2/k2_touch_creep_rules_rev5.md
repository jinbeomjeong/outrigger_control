# K-2 규칙 덧붙임 rev5 (결과 전, 2026-11-10)

- 작성: control-expert, 2026-11-10. 봉인 정보는 같은 폴더의 `k2_touch_creep_rules_rev5.sha256`.
- 원판(`a3658197…7263`), rev1(`5ba081c6…4776`), rev2(`b3f1b41f…94ea`), rev3(`8bcdb0ed…6e61`), rev4(`82160ff54874e3d43bf7c5a1ae96d6e8612b1e7635aaccea39a4299352ce00c5`)를 고치지 않고 아래만 덧붙인다. 다르면 rev5 > rev4 > rev3 > rev2 > rev1 > 원판 순으로 맞다.
- 시점: V-1~V-7 결과 0건. 경로 1(`k2_judge.py`, python-expert `5f22957`)과 경로 2(`k2_recount.py`)의 정의를 맞추는 과정에서 정한다. 판정 항목과 문턱은 바꾸지 않고, **확인 방법과 기록 출처만** 정한다. 등급 영향은 없다.

## 1. rev2 1절 공통 항목의 출처

| 단계 | provenance(`c2_sha256`, `combo`, `k2`, `touch_creep_latch`, `controller_tag`) 출처 |
|---|---|
| reg1~reg7, grid_r67_main, grid_r67_top, grid_r69_top, grid_r69_bottom, soil_A, noise_L1L2, ps7 | 팔 폴더의 `provenance/<단계명>.json`(`ACC_PROVENANCE`). 단계마다 1개씩 있어야 하고, 없으면 결측(E-9 실패) |
| d8 | `acc_d8.py`(옛 모드)는 `ACC_PROVENANCE`를 쓰지 않는다. `d8_both.json`의 `meta`(acc_common provenance 키가 그대로 들어 있음)를 그 단계의 provenance로 쓴다 |
| G8 (`g8_jobs1`, `g8_jobs3`, `g8_jobs5`) | `g8trace.py`는 provenance도 `c2_sha256`도 남기지 않는다. 아래 2절 방법으로 확인한다 |

- `combo`는 G8을 빼고 모두 `preset`이어야 한다. G8은 구동기 정의상 `ACC_COMBO=off`이고, 2절로 확인한다.

## 2. G8의 c2.py 확인과 K-2 증거

- **c2.py**: G8 단계 sidecar(`g8_jobsN.launch.json`, 팔마다 3개)가 다음을 모두 만족하면, G8이 쓴 `c2.py`는 그 커밋의 파일로 본다.
  - `git_start.head`와 `git_end.head`가 모두 `6a44ff81d25aea1fa162daf9b14c23b99beb9db0`이다.
  - `git_start.is_clean`과 `git_end.is_clean`이 모두 참이다.
  - `rc` = 0이다.
  - 판정 때 고정 checkout의 `03_src/outrigger_sim/control/c2.py` 작업 사본 sha256이 `f58ee42b0f10ea42ceac5768e6ed373a38ee5e14440d9fc831536700b45ba6b1`이다.
  - 하나라도 어기거나 없으면 G8 공통 항목은 실패다(E-9).
- **K-2 증거**: G8 행의 `touch_creep_latch`가 그 팔과 같아야 한다(K-2 팔은 참, 끔 팔은 거짓). `controller_tag`는 K-2 팔만 `_TCL`로 끝나야 한다. 이 두 필드는 g8trace가 `ACC_K2`를 받을 때 행마다 남긴다. G8 행의 `events`는 K-2 증거로 쓰지 않는다.
- 사건 행으로 보는 K-2 증거(rev2 1절)는 잡음 원 실행(`r79_L1L2.json`), PS-7(`ps7.json`), `clip_r79_L1L2.json`, `clip_r79_L3L4.json` 네 파일로 한정한다.

## 3. sidecar rc의 범위

- rev2 1절 공통 "단계 sidecar `rc` = 0"은 V-5 **실행 단계 36개와 r79 판정 단계 4개**에 적용한다.
- 평탄화 단계(`flatten.launch.json`)는 경로 2가 쓰지 않으므로 V-5 판정에 넣지 않는다. 경로 1이 평탄 파일을 쓸 때는 경로 1이 그 단계의 rc를 자기 입력 확인으로 본다.
- 판정 후 정체성 확인(rev2 6절)은 sidecar 62개 전부를 그대로 본다.

## 4. 두 경로 공통 해석

- **SH-6의 J2**: H4 구간(`reanchor_intervals_s`)이 있는 행에서만 필수다. H4가 없는 행의 J2 None은 결측이 아니다. J1은 모든 K-2 행에서 필수다.
- **D8 끔 팔 대비**: 기록만 한다(rev2 1절 표). manifest의 `kind` 표기와 무관하게 D8의 통과→실패는 G-D를 정하지 않는다. 잡음 L2의 통과→실패도 기록이다.
- **V-3 E-5 기준값**: rev3 1절의 상수를 그대로 쓴다. 판정 때 YAML을 다시 읽지 않는다. 실행 YAML이 바뀌지 않았다는 것은 `{RUN_HEAD}` 고정과 sidecar의 HEAD·clean으로 보증한다.
