# LAS-b 경계 키 재개정 K1 — R4c30 평탄 시작 순서 관문 봉인 규칙 (원판)

- 작성: control-expert, 2026-11-09
- 상태: **원판. K1 코드·하네스·실행 전에 봉인한다.** 이 판을 바꾸려면 새 판(rev1 …)을 만들고, 결과를 보기 전인지 본 뒤인지를 첫머리에 적는다.
- 사용자 결정(2026-11-09, control-expert 설계 검토 보고의 제안을 모두 그대로 고름)
  1. LAS-b 경계 키 `D1|H-S-A|G1+J1@FL|T|flat|K1|VB|e0`를 S2D와 다른 갈래로 재개정한다. 그 갈래는 K1(R4c30을 $t_P > t_S$일 때만 켬)이다.
  2. 패치 키의 변경(틈 목표 80 → 50 mm)을 받아들인다. Chrono SCM 패치 1키(G1+J2@FL, P0+K1, E-6형)를 넣는다.
  3. C-S 1 mm 기준은 그대로 둔다.
  4. 행정 예산 대응 B1은 K1 병합 뒤 따로 한다. 그 전에 Chrono 경사 J2 크리프 근거를 받는다. **이 규칙의 범위가 아니다.**
  5. 이상적 센서 진단은 K1 뒤에 따로 검토한다. **이 규칙의 범위가 아니다.**
- 재개 검증 436.8은 보류 상태 그대로다(이 규칙은 436.8을 재개하지 않는다).
- 규약: 이산 $T_s$ = 0.1 s(10 Hz), 출력 지연 $d$ = 1, C2 음되먹임($u$는 행정 속도 명령), 행정은 모터 행정 [m](표시는 mm), 힘은 실린더 순 힘 [N].

## 0. 배경과 봉인 전에 본 것 (공개)

### 0.1 기제 요약

- 주기 안 순서: S-1 창 갱신(LOC 판정, `_level_step`) → 래치 해제(`_update_crawler_zone`) → LOC 전이면 토양 모드 시작(`_hold_crawler_zone_until_liftoff`).
- R4c30(P-S8-37, 명세 429.9)은 LOC마다 `soil_mode_start_s is not None`(토양 모드를 한 번이라도 씀)이고 정착 기울기 ≤ 1°이며 run 틈 목표가 아직 없을 때 틈 목표를 +30 mm 올린다(`_is_flat_soil_margin_due`).
- 경계 키에서 b0(P0)는 LOC와 래치 해제가 같은 주기(23.5 s)에 와서 LOC가 먼저 처리됐다(토양 모드 없음, R4c30 없음, 여유 0 mm). P5r4는 LOC가 약 3 mm 늦어 래치가 먼저 풀렸고(23.8 s) 토양 모드 → R4c30 → 최대 행정 +30.10 mm(C-S 미달)였다.
- 이때 평탄 창 시작 $t_P$는 23.1 s로 토양 모드 시작 $t_S$ 23.8 s보다 7주기 앞이다(`v5/las/diagA/diagA.jsonl` sha256 `1590e79b…2ed5d`, `diag.soil_summary`).
- K1은 시작 시각을 옮기지 않고 **결과 규칙(R4c30의 적용 조건)**을 바꾼다. LOC 전 명령은 비트 단위로 같고 LOC 뒤 틈 목표만 달라진다.

### 0.2 봉인 전에 본 데이터 (과적합 공개)

| 자료 | 무엇을 봤나 |
|---|---|
| `v5/soil_defer/s2d_SC.jsonl`(S-C, P0, 456줄, sha256 `70e91ec1234d56a918af1b4fc053c3175f0f14ab41e2b5f334890f7dc6cb08aa`) | 토양 모드 301줄의 $t_S$·$t_P$·$t_{LOC}$·밀어 올림·`r4c30`·최대 행정·끝 단계·FAULT·INFO 이름, SGS 정지 36줄의 크롤러 하중. **K1 문턱(주기 차 > 0)은 이 분포를 본 뒤 정했다**: R4 행 165줄 중 진짜 연약 지면 160줄은 dP ≥ +31주기, 패치 5줄은 dP ≤ −4주기 |
| `v5/soil_defer/s2d_SD.jsonl`(106줄)·`s2d_SD_info.jsonl`(19줄) | dP 분포(H-S-0 R4 14줄 dP ≥ +36), S2D 판정서 값 |
| `v5/las/diagA/diagA.jsonl`(3줄) | 경계 키 P0·P5·P5r4의 $t_P$·$t_S$·LOC·최대 행정 |
| `v5/las/revA2/revA_RS.jsonl`(30줄, `7c407b6e…875d`), `revA_RP0.jsonl`(149줄, `9be02caf…7300`), `revA_RT.jsonl`(192줄, `c72f7e08…fd54`) | 키 목록, `commands_sha256`, `INFO_LOC_FLAT_SOIL_MARGIN` 유무, 토양 모드 유무. $t_P$·$t_S$ 필드는 이 줄들에 없다 |
| 판정서 `las_revA2_judgement.md`, `las_revA_diag_judgement.md`, `s2_soil_defer_judgement.md` | 판정 값 전부 |
| 명세 426.9·428·429.9(R4c30 채택 근거) | E-6 6/6 회복은 J2 균일 연약 지면, G6 패치 R4 행은 lite 판정 변화 0 |

- **따라서 Y-P(S-C 위 P0+K1)는 기구 확인일 뿐이다.** 표본 밖 근거는 Y-S의 P5r4 줄(경계 키를 뺀 P5r4의 $t_P$·$t_S$는 보지 않음), Y-T, S-Ch(Chrono)다.

## 1. K1 정의

### 1.1 조건

- 설정: `SlopeClearanceMarginSettings.flat_soil_margin_order_gate: bool = False`(클래스 기본 False, R8 프리셋 기본도 **False** — 이 규칙의 판정이 끝나고 사용자가 채택을 정하기 전까지 프리셋은 바꾸지 않는다). 하네스 토큰 이름은 `K1`.
- 기호

| 기호 | 정의 | 출처 |
|---|---|---|
| $t_P$ | 이번 LOC를 확정한 S-1 꼬리의 첫 표본 시각 | `soil.plateau_start_s`(`_confirm_liftoff`가 `_apply_slope_clearance_margin`보다 먼저 씀) |
| $t_S$ | LOC 시점의 가장 최근 토양 모드 시작 시각 | `soil.soil_mode_start_s`(LOC 취소 뒤 재시작하면 새 값) |
| $n_P$, $n_S$ | $\mathrm{round}(t_P/T_s)$, $\mathrm{round}(t_S/T_s)$ (정수 주기 번호, 부동소수 비교 금지) | — |

- K1이 켜지면 R4c30 조건(`_is_flat_soil_margin_due`)에 다음을 **더한다**(AND).
  - $t_S$가 있고 $t_P$가 있으며 $n_P > n_S$.
  - $n_P \le n_S$이면 R4c30을 적용하지 않는다(**관문 막음**). 그 LOC의 P-S8-31(E3c10) 판단은 그대로다(K1은 `elif` 쪽 R4c30만 건드린다).
- 다른 소비자는 바꾸지 않는다: L1gs 토양 관문, SGS, DSb75, S-3 편향, LOC 앵커, S-4, 토양 모드 밀어 올림 하한.
- **비트 동일**: K1이 False이면 명령·사건·메타의 기존 필드가 비트 단위로 같아야 한다(새 기록 필드 추가는 예외, 아래 1.2).

### 1.2 기록 필드 (K1 꺼짐에서도 그림자로 기록)

- `controller_meta.slope_clearance_margin.order_gate`
  - `enabled`: bool
  - `decisions`: LOC마다(R4c30 조건을 평가한 LOC만) 한 항목
    - `t_loc_s`, `t_P_s`, `t_S_s`, `n_P`, `n_S`, `dP` = $n_P - n_S$(없으면 None)
    - `r4_due_without_gate`: bool(기존 조건)
    - `would_block`: bool(= `r4_due_without_gate` 이고 $n_P \le n_S$ 또는 $t_P$·$t_S$ 없음)
    - `applied`: bool(실제 R4c30 적용)
- K1이 켜져 관문이 막으면 사건 `INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order`를 남긴다(INFO, 경고 아님). K1 꺼짐에서는 이 사건을 남기지 않는다.
- 판정에 쓰는 결과 줄 필드(하네스): `k1.decisions`(위 그대로 복사), `k1.enabled`, `k1.r4_applied`(bool), `k1.would_block_any`(bool).

## 2. 정체성 필드 (모든 줄)

- `git_head`, `git_dirty`, `dirty_files`(허용 목록: 이 묶음의 시험 파일만, 하네스가 import하지 않는 것), `code_diff_sha256`
- 도구 sha256: `c2.py`, K1 하네스, K1 판정기, 그리고 이어받은 하네스 경로 파일 전부(S2D 판정서 0.2절의 9개 + `s2_defer_targeted.py`)
- 규칙 sha256: **이 원판과 그 뒤 판 전부**, 이어받은 A안 6개(`las_rev_targeted_rules` 원판·rev1, `las_revA_targeted_rules` 원판·rev1·rev2·rev3)
- 스레드 env(MKL·OMP·OpenBLAS·Numba = 1, `MKL_THREADING_LAYER=TBB`), 러너 마스크(기록만, 정체성 항목 아님)
- `controller_tag`
- **후보 이름은 서로 다른 필드에 둔다**(S2D의 "P0" 이름 혼동 교훈)
  - `las_candidate`: `P0`(LAS-b b0) 또는 `P5r4`
  - `k1_candidate`: `K1off` 또는 `K1on`
  - `bundle`: `Y-0`·`Y-P`·`Y-S`·`Y-T`
- 기준 파일 경로와 sha256(줄마다 그 짝의 기준 파일)
- 한 묶음 안 모든 줄의 `git_head`·도구 sha256·규칙 sha256 집합이 같아야 한다. 묶음 사이에서도 같아야 한다(코드 diff 빈 해시). 다르면 **K-0 위반 → stop**.

## 3. 묶음

- 실행 순서: Y-0 → Y-P → Y-S → Y-T → (판정) → S-Ch(별도 계획 봉인·실행 전 감사 뒤)
- 출력 폴더: `06_analysis/03_hydraulic/coupled/v5/las/k1/`(로컬 전용, git exclude, `-text` 대상)
- 하네스는 S-C·revA2 줄을 만든 경로와 같은 작업 dict·플랜트 옵션을 쓴다. S2D 설정은 끈다(그림자 포함 — S2D 그림자는 기록만이므로 명령 해시에 영향이 없다. 영향이 있으면 Y-0에서 드러난다).

### 3.1 Y-0 — 구현 확인과 그림자 기록 (K1 꺼짐)

| 하위 | 키 | 건수 | `las`/`k1` | 기대 |
|---|---|---|---|---|
| Y-0a | 부록 A의 S-C 변경 예측 5키 | 5 | P0 / K1off | `commands_sha256` = S-C 저장값 |
| Y-0b | R-S 30키(부록 C) | 30 | P5r4 / K1off | = `revA_RS.jsonl` 저장값 |
| Y-0c | R-S 30키 | 30 | P0 / K1off | = A안 원판 3.3의 짝 기준 L 줄 해시(`las_T1`·`las_T2`·`fb_F3`·`fb_F4`). L 줄이 없는 키는 `revA_RP0.jsonl` 저장값 |
| Y-0d | S-C 비R4 표본 40키(부록 B) | 40 | P0 / K1off | = S-C 저장값 |

- **그림자 진단의 위치**: 사용자에게 물었던 R-S 30키 × {P0, P5r4}의 $t_P$·$t_S$ 그림자 기록은 **Y-0b·Y-0c로 넣는다**. 명령이 저장값과 같아야 하는 확인 묶음이라 사전 등록을 오염시키지 않는다. 대신 그림자 `would_block` 집합이 5절 예측과 다르면 Y-S 전에 멈추고 묻는다(SK-3).
- 건수 105, 예상 시간: 20 워커 기준 약 10분(추정).

### 3.2 Y-P — K1 효과(P0+K1 대 저장 P0)

| 하위 | 키 | 건수 | 기대 |
|---|---|---|---|
| Y-Pa | S-C R4 행 전부(부록 A) | 165 | 변경 예측 5키(부록 A 표시)만 해시가 바뀐다. 160키는 저장 S-C 해시와 같다 |
| Y-Pb | S-C 비R4 표본 40키(부록 B) | 40 | 40/40 저장 해시와 같다 |

- 짝 기준: `s2d_SC.jsonl`(sha256 `70e91ec1…08aa`)의 같은 전체 키 줄.
- 건수 205, 예상 시간: 약 20분(추정).

### 3.3 Y-S — LAS-b P5r4와 K1 함께(판정 묶음)

| 하위 | 키 | 건수 | `las`/`k1` |
|---|---|---|---|
| Y-Sa | R-S 30키 | 30 | P0 / K1on |
| Y-Sb | R-S 30키 | 30 | P5r4 / K1on |

- **판정 짝**: Y-Sb 대 Y-Sa(같은 전체 키). K1이 채택되면 기준선이 P0+K1이 되므로, LAS-b 후보는 그 위에서 판정한다.
- 해시 예측
  - Y-Sa 대 Y-0c: `D1|H-S-A-J2|G1+J2@FL|T|flat|K1|VB|e0` 1키만 바뀐다.
  - Y-Sb 대 Y-0b: `D1|H-S-A|G1+J1@FL|T|flat|K1|VB|e0`, `D1|H-S-A-J2|G1+J2@FL|T|flat|K1|VB|e0` 2키만 바뀐다.
- 건수 60, 예상 시간: 약 12분(추정).

### 3.4 Y-T — R-T 비트 확인

- R-T 192키(부록 D), P5r4 / K1on. 짝 기준 `revA_RT.jsonl`(sha256 `c72f7e08…fd54`).
- 기대: 192/192 해시 같음(R-T 줄에는 토양 모드·R4c30이 없다).
- 예상 시간: 약 20분(추정).

### 3.5 S-Ch — Chrono SCM 패치 1키 (사용자 결정 2)

- 대상: G1 바닥 + J2 패치@FL, 평지, 오거 상단, P0 대 P0+K1의 **2행**(P5r4 아님).
- 행 정의(SCM 세트·패드·스레드·OMP·P/E·시드·실행 시간)는 **cad-expert가 정한다**. control-expert는 그 행 정의와 아래 5.5 예측을 묶은 보충 계획 `las_k1_sch_plan.md`를 **따로 봉인**한다.
- 순서: Y-0~Y-T 판정 `통과` → cad-expert 행 정의 → 보충 계획 봉인 → verif-protocol-auditor 실행 전 감사(차단 0) → 실행 → 판정.
- Y 묶음이 `미달`이면 S-Ch는 `not_run`이다.

## 4. 판정 기준

### 4.1 정체성·구조 (K)

| # | 기준 |
|---|---|
| K-0 | 2절 정체성이 묶음 안·사이에서 같다. 규칙 sha256 기록에 이 원판이 있다 |
| K-1 | 모든 줄에 `k1.enabled`가 `k1_candidate`와 맞고, R4c30을 평가한 LOC마다 `decisions` 항목이 있다 |
| K-2 | K1off 줄은 `applied` = `r4_due_without_gate`이고 `INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED` 사건이 없다 |
| K-3 | K1on 줄은 `applied` = `r4_due_without_gate` ∧ ¬`would_block`이다 |
| K-4 | `would_block`이 거짓인 줄(K1on)은 같은 키의 K1off 줄과 `commands_sha256`이 같다 |

### 4.2 해시 예측 (H)

| # | 기준 |
|---|---|
| H-1 | Y-0 각 줄의 해시 = 3.1 표의 저장값 |
| H-2 | Y-Pa에서 해시가 바뀐 키 집합 = 부록 A의 변경 예측 5키(목록 sha256 `4cdc9bfe100a4b7d7504df8621eff2fd32660604ab423a61a070ca7a634c5da6`). Y-Pb 40/40 같음 |
| H-3 | Y-Sa·Y-Sb의 바뀐 키 집합 = 3.3의 1키·2키 |
| H-4 | Y-T 192/192 같음 |

### 4.3 나빠짐 0 (해시가 바뀐 줄과 Y-S 짝 전부)

| # | 기준 | 정의 |
|---|---|---|
| C-2형 | 나빠짐 0 | (a) `d1.verdict`가 `pass`·`allowed_stop`에서 그 밖으로 바뀌지 않는다. (b) `final_phase` `ready` → 비ready가 없다, verdict 사례(R12·R14·R15·R16·R2)는 (b)·(c)만 본다. (c) 새 FAULT·WARN 이름 0. 아울러 `d1.items`에서 참 → 거짓 0, 새 `fail_items` 0 |
| P3 | 끝 크롤러 | 해시가 바뀐 Y-P 줄과 Y-S 줄에서 `d1.items` 중 이름이 `P3-1`·`P3-5`로 시작하는 항목이 있으면 모두 참(끝 크롤러 실제 하중 0, 끝 전 절점 틈 ≥ 25 mm). 항목이 없는 그룹은 해당 없음으로 세고 건수를 적는다 |
| C-S | 행정 | 모든 짝에서 `d1.stroke_max_m` 증가 ≤ 0.001 m(LAS-b 원판 C5). **바꾸지 않는다**(사용자 결정 3) |
| C-F | 힘 여유선 | 기준 `d1.F_judged_min_N` ≥ 10,414.589 N인 모든 짝에서 후보도 ≥ 10,414.589 N |
| READY | 기록 | 짝마다 $\Delta t$ = 후보 − 기준(`values.times.t_first_ready_s`)을 적는다. 판정에 쓰지 않는다 |

- 짝: Y-P는 P0+K1 대 저장 P0, Y-S는 Y-Sb 대 Y-Sa. 짝은 **전체 키**(`row_key|setting|eps`)로 맺는다.
- 비교 허용치: 행정·힘은 절대값 그대로 비교한다(허용치 없음, 부등호는 위에 적은 그대로). 시각 비교는 5.0.2의 주기 번호로 한다.

### 4.4 등급

| 등급 | 조건 |
|---|---|
| `통과` | K·H·C 전부 참, 모든 묶음 완료 |
| `미달` | C-2형·P3·C-S·C-F 중 하나라도 거짓(**나오는 즉시 확정**, 6절) |
| `stop` | K 또는 H 거짓(예측하지 않은 해시 변화·정체성 문제). **멈추고 사용자에게 묻는다.** 결과를 보고 규칙을 고치려면 새 판을 결과 본 뒤 판으로 공개한다 |
| `incomplete` | 줄 누락·오류 줄이 재실행 1회 뒤에도 남음 |
| `not_run` | 앞 단계가 통과하지 않아 돌지 않음 |

### 4.5 판정 도구 종료 코드 ↔ 판정 어휘

| 종료 코드 | `status` | 판정서 어휘 |
|---|---|---|
| 0 | `pass` | `통과` |
| 1 | `fail` | `미달` |
| 2 | `stop` | `stop`(멈추고 묻기). `미달`과 함께 나오면 `미달`이 우선이고 `stop` 사유를 공개 항목에 적는다 |
| 3 | `incomplete` | `incomplete`. 앞 단계 미통과로 안 돈 묶음은 도구가 `not_run`으로 적는다 |

- 도구는 묶음별 `status`와 전체 `status`를 함께 낸다. 판정서는 도구 어휘를 위 표대로 옮기고 다른 낱말로 바꾸지 않는다.

## 5. 사전 예측

### 5.0 공통

- 5.0.1 예측은 0.2절의 데이터를 본 뒤 정했다. 어긋나면 판정서에 그대로 적는다(예측은 판정 기준이 아니다, 단 해시 예측 H는 판정 기준이다).
- 5.0.2 **같은 주기 짝 맞추기**: 모든 사건 시각은 $\mathrm{round}(t/T_s)$ 정수 주기로 바꿔 비교한다(예: 29.999999999975 s = 300주기).

### 5.1 Y-0

| # | 예측 |
|---|---|
| Q-0a | 105/105 해시 같음 |
| Q-0b | 그림자 `would_block` 참 집합: Y-0a 5/5, Y-0b 2키(`H-S-A\|G1+J1@FL\|T\|flat\|VB\|e0`, `H-S-A-J2\|G1+J2@FL\|T\|flat\|VB\|e0`), Y-0c 1키(`H-S-A-J2\|G1+J2@FL\|T\|flat\|VB\|e0`), Y-0d 0 |
| Q-0c | Y-0b·Y-0c에서 R4c30을 평가한 진짜 연약 지면 행(H-S-0 J1·J2 평지, H-S-1, H-S-C, H-R-A-S1)의 dP ≥ +20주기 |

### 5.2 Y-P

| # | 예측 |
|---|---|
| Q-P1 | 바뀐 키 = 부록 A 5키 정확히 |
| Q-P2 | 5키 모두 최대 행정이 25~35 mm 줄어든다(근거: 명세 429.9 R4c30 틈 +29.4~+33.2 mm). C-S 위반 0 |
| Q-P3 | 5키 C-2형 위반 0, P3 위반 0, 새 FAULT·WARN 0 |
| Q-P4 | READY Δt ≤ 0(빨라짐 쪽), 최대 −5 s 안 |

### 5.3 Y-S

| # | 예측 |
|---|---|
| Q-S1 | 경계 키 `D1\|H-S-A\|G1+J1@FL\|T\|flat\|K1\|VB\|e0`: Y-Sb − Y-Sa 최대 행정 Δ ∈ [−1, +1] mm, 중앙 +0.1 mm(근거: revA2 +30.10 mm − R4 30 mm). C-S 통과 |
| Q-S2 | `H-S-A-J2\|G1+J2@FL\|T\|flat\|VB\|e0`: 두 쪽 모두 R4c30 막힘, Δ ∈ [−1, +1] mm |
| Q-S3 | 나머지 18 D-1 짝과 verdict 사례 10짝은 revA2 판정과 같은 결과(C-2형·C-F·C-S 통과) |
| Q-S4 | Y-S 전체 `통과` |

### 5.4 Y-T

| # | 예측 |
|---|---|
| Q-T1 | 192/192 해시 같음, `decisions` 빈 줄 192 |

### 5.5 S-Ch (보충 계획에서 수치를 덧붙일 수 있으나 아래 방향은 바꾸지 않는다)

| # | 예측 |
|---|---|
| Q-C1 | P0 행에서 토양 모드가 시작되고 R4c30이 적용되며, $n_P \le n_S$이다(하네스 H-S-A-J2 4/4가 dP −4~−8) |
| Q-C2 | P0+K1 행은 R4c30이 막혀 최대 행정이 P0보다 25~35 mm 작다. LOC까지 명령은 P0와 같다 |
| Q-C3 | E-6형: P0+K1 행에서 끝 크롤러 하중 0, 끝 전 절점 틈 ≥ 25 mm, $W$ 밖·느린 사건 뒤 재접촉 0. READY |
| Q-C4 | Q-C1이 틀려 K1이 작동하지 않으면(Chrono에서 $n_P > n_S$ 또는 토양 모드 없음) S-Ch는 `K1 미작동(정보)`이다. 실패가 아니며, 판정서에 공개하고 사용자에게 다른 패치 키 추가 여부를 묻는다 |

## 6. 멈춤 조건과 멈춘 뒤

| # | 조건 | 처리 |
|---|---|---|
| SK-1 | K-0 위반(정체성) | 그 묶음 판정 `stop`. 다음 묶음을 돌지 않는다 |
| SK-2 | 오류 줄 | 같은 정체성으로 그 키만 1회 재실행(`--resume`, 공개). 남으면 `incomplete` |
| SK-3 | Y-0 해시 불일치 또는 그림자 `would_block` 집합 ≠ Q-0b | Y-P 전에 `stop`, 묻는다 |
| SK-4 | Y-P·Y-S·Y-T에서 H-2~H-4 거짓(예측하지 않은 해시 변화) | 그 묶음은 끝까지 돌리고(아래) `stop`, 묻는다 |
| SK-5 | C-2형·P3·C-S·C-F 위반 | **즉시 `미달` 확정.** 판정을 되돌리거나 기준을 고치지 않는다 |

- **멈춘 뒤 나머지 키(원판에서 미리 정함)**: 러너는 판정 위반이나 예측 밖 해시가 나와도 **진행 중인 묶음은 끝까지 돌린다**(오류 SK-1·SK-2 제외). 판정은 묶음이 끝난 뒤 판정기로 한다. 그 묶음의 나머지 줄은 판정을 바꾸지 않는 **정보용**으로 판정서에 적는다. 다음 묶음은 돌지 않는다(`not_run`).
  - 이유: 묶음은 작고(최대 205줄, 약 20분) 같은 정체성으로 이미 계획된 줄이다. S2D에서는 중간 멈춤 때문에 정보용 실행을 위해 rev5를 따로 봉인해야 했다. 끝까지 돌리면 위반의 범위(한 짝인지 계열인지)를 새 규칙 없이 알 수 있고, 등급은 위반이 이미 정한다.
- `stop`(SK-3·SK-4) 뒤 다음 묶음으로 가려면 사용자 결정이 필요하다. 결정 내용과 시각을 판정서에 적는다.

## 7. 부분 기록과 짝 없는 키

- **부분 기록**: R4c30을 평가한 LOC가 있는데 `decisions`가 비었거나 $t_P$·$t_S$가 빠진 줄은 K-1 위반 → `stop`(규칙보다 엄격하게 처리하지 않는다. 판정기와 이 원판이 같은 동작을 한다). R4c30을 평가하지 않은 줄(LOC 없음·경사 여유 적용·토양 모드 없음)은 `decisions`가 비어도 된다.
- **짝 없는 키**: 기준 파일에 그 전체 키가 없으면 그 키를 판정에 넣지 않고 `unpaired` 목록과 건수를 적는다. 부록 목록에서 계산한 키가 기준에 없을 수는 없으므로, 1건이라도 나오면 `stop`.
- **목록 밖 키**: 결과 줄 키가 그 묶음의 부록 목록에 없으면 `stop`.
- **중복 줄**: 같은 전체 키·같은 후보가 두 줄이면 `stop`(resume 겹침).
- 실행 도구는 목록을 저장 기준 파일에서 다시 계산하고 그 sha256을 부록 값과 대조한다. 다르면 실행하지 않는다. `--keys`·`--limit`은 본 실행에 쓰지 않는다.

## 8. 판정서 공개 체크리스트 (S2D 교훈, 판정서에 모두 적는다)

1. 규칙 파일 sha256 전부와 각 판의 봉인 시각. **봉인 시각과 봉인 커밋 시각을 대조**한다(S2D rev5 시각 표기 오류 교훈).
2. 봉인 전에 본 데이터(0.2절)와, 봉인 뒤 판정 전에 본 것(감사 보고·진행 로그 등).
3. 정체성: 묶음별 `git_head`·dirty·코드 diff·도구 sha256·스레드, 후보 필드(`las_candidate`·`k1_candidate`) 집계.
4. resume 사용 여부(SK-2), `--keys`·`--limit` 미사용, 목록 sha256 재계산 결과.
5. 본 뒤 버린 줄(있으면 경로·줄 수·본 범위).
6. 짝 없는 키·목록 밖 키·중복 줄 건수(0이어도 적는다).
7. 그림자 `would_block` 집합과 Q-0b 대조, dP 분포.
8. 사전 예측 대조표(5절 전부). 어긋난 예측은 숫자와 함께 적는다.
9. 해당 없음 건수(P3 항목이 없는 그룹 등).
10. 두 경로 재집계: 판정 도구 + control-expert 독립 집계(판정기를 import하지 않고 jsonl만 읽음). 수치 허용 1e-9.
11. 멈춤이 있었으면 멈춤 사유, 사용자 결정, 정보용으로 남은 줄.

## 9. 이 규칙이 하지 않는 것

- B1(행정 예산 반영 틈 여유), 이상적 센서 진단, 재개 검증 436.8, 프리셋 전환.
- K1 채택(프리셋 기본 켬)은 이 판정 `통과`와 S-Ch 판정 뒤 사용자가 정한다.
- 기준(C-S 1 mm 등)과 문턱($n_P > n_S$)은 결과를 보고 바꾸지 않는다.

## 부록 목록 규약

- 키 문자열은 결과 줄의 `d1.key`(R-S verdict 사례는 `rev.key`)다.
- 목록 sha256 = 키를 오름차순(파이썬 기본 문자열 정렬)으로 정렬해 각 줄 끝에 LF를 붙여 이은 UTF-8 바이트의 sha256.
- 해시 열은 저장 `commands_sha256`, dP 열은 S-C 저장 $n_P - n_S$.

## 부록 A. Y-Pa S-C R4 행 165키 (`s2d_SC.jsonl` sha256 `70e91ec1234d56a918af1b4fc053c3175f0f14ab41e2b5f334890f7dc6cb08aa`)

- 목록 sha256 `dc1e65d49bc0ea34fd04fdb7ba4eeceb7fc576ee15de9658dbe26927598b753b` (165키)
- 변경 예측 5키 목록 sha256 `4cdc9bfe100a4b7d7504df8621eff2fd32660604ab423a61a070ca7a634c5da6` (표의 `예측` 열이 `바뀜`인 키)
- 그 밖 160키는 해시가 같아야 한다.

| # | 키 | 저장 `commands_sha256` | dP [주기] | 예측 |
|---|---|---|---|---|
| 1 | `D1\|H-R-A-S1\|rigid+S1@FL\|T\|flat\|K1\|V0\|e0` | `98629961a5e816bf76be56b23af1a325d5879c99aab29cbf07c8fcde31a46e58` | 37 | 같음 |
| 2 | `D1\|H-R-A-S1\|rigid+S1@FL\|T\|flat\|K1\|V0\|e0.002` | `f5e1417e48b4197f77bdcde72f0ef64b35c0a95561c19d887a7543c90e6e5b3a` | 39 | 같음 |
| 3 | `D1\|H-R-A-S1\|rigid+S1@FL\|T\|flat\|K1\|VB\|e0` | `8f8e15f12042a98f9986b3e720d9633523c93f5d30392b06d828be896310e93d` | 31 | 같음 |
| 4 | `D1\|H-R-A-S1\|rigid+S1@FL\|T\|flat\|K1\|VB\|e0.002` | `7cc0b994df1279f81a06ecf7bcb4a2afcd47336f63f6ceca3e21ac64cfb9e5e3` | 41 | 같음 |
| 5 | `D1\|H-S-0\|J1\|B\|flat\|K1\|V0\|e0` | `6a482cca8314279607a783d3603d59b1a072feda5614812fb9e164dacecbfc2b` | 40 | 같음 |
| 6 | `D1\|H-S-0\|J1\|B\|flat\|K1\|V0\|e0.002` | `e2f3d2a42e6cf68b72a4519d33e35063409eb055911227b97e09678df7b5292d` | 40 | 같음 |
| 7 | `D1\|H-S-0\|J1\|B\|flat\|K1\|VB\|e0` | `66111f54953e7cdab8d959a9f9a918b46cbc31f8789911a39aae480507a6aa43` | 40 | 같음 |
| 8 | `D1\|H-S-0\|J1\|B\|flat\|K1\|VB\|e0.002` | `240cfadd1bca9030ca43adbb26c72b0e5b20c0ba1c40f1893923d2ab17516591` | 40 | 같음 |
| 9 | `D1\|H-S-0\|J1\|M\|flat\|K1\|V0\|e0` | `525f9e5c7089a227baf8e8bce4b7ffa49e4577b512ae2a0c82d7ee153cfb71e2` | 39 | 같음 |
| 10 | `D1\|H-S-0\|J1\|M\|flat\|K1\|V0\|e0.002` | `c47dad3d21ac07f8e595e254b785e8c78bbacdf2cea5a7fd5940903d33e9b234` | 39 | 같음 |
| 11 | `D1\|H-S-0\|J1\|M\|flat\|K1\|VB\|e0` | `3378f09f4e978923641985397380713109ec86bc587e3a5a631db1c61a01206c` | 39 | 같음 |
| 12 | `D1\|H-S-0\|J1\|M\|flat\|K1\|VB\|e0.002` | `591c04892bd3ab4a344059ec89c9f278a4408c8dd07826fc64c166de4f7448fe` | 39 | 같음 |
| 13 | `D1\|H-S-0\|J1\|T\|flat\|K1\|V0\|e0` | `2a3b8618080698f7bd95258c100000b57d7de413f473be45a63989e0d1fe66c4` | 38 | 같음 |
| 14 | `D1\|H-S-0\|J1\|T\|flat\|K1\|V0\|e0.002` | `e7ed750bf95993f488dbea96873d552d4d02b70ca26d60e4bcc1dc12b4cd4f57` | 38 | 같음 |
| 15 | `D1\|H-S-0\|J1\|T\|flat\|K1\|VB\|e0` | `4cdb5661e644adc4fadff1092f9021b16ffb5d8f6e586164ea0973298c2054fa` | 36 | 같음 |
| 16 | `D1\|H-S-0\|J1\|T\|flat\|K1\|VB\|e0.002` | `4ad557185b80e60c0e3aa640017e5765734774597067843f7ac09b0a0c6d942e` | 37 | 같음 |
| 17 | `D1\|H-S-0\|J2\|B\|flat\|K1\|V0\|e0` | `60f3c58e5c48e0b5c0c7ae6529c5b6a4e2111c20ec9a59b11577c3748dd6bb0c` | 94 | 같음 |
| 18 | `D1\|H-S-0\|J2\|B\|flat\|K1\|V0\|e0.002` | `f89c43291d6149ed97e52c0ecb0af4a4bfc17aef939467f9bd585f3fe5712c2e` | 95 | 같음 |
| 19 | `D1\|H-S-0\|J2\|B\|flat\|K1\|VB\|e0` | `5fa3c7ec1f66340b6b437cd2e6888d951510c13e869e4d2b6575642dc0213455` | 95 | 같음 |
| 20 | `D1\|H-S-0\|J2\|B\|flat\|K1\|VB\|e0.002` | `54717e21dc73e6de69712d31f5285736d6fe1a76d1c907cf7d21da9352a96ac1` | 95 | 같음 |
| 21 | `D1\|H-S-0\|J2\|M\|flat\|K1\|V0\|e0` | `bfc9de8e6a2d58847a671f8879ccd895752f9224e2c030c70b640bfbe084f119` | 94 | 같음 |
| 22 | `D1\|H-S-0\|J2\|M\|flat\|K1\|V0\|e0.002` | `6a4fe5149768b52218981e2b255adb6d288babc2ccc56945423e41640ea3aa5b` | 94 | 같음 |
| 23 | `D1\|H-S-0\|J2\|M\|flat\|K1\|VB\|e0` | `beed3a19ed74dcaab05ada827c74bee59be91fe331a071ae894b2654ee832311` | 94 | 같음 |
| 24 | `D1\|H-S-0\|J2\|M\|flat\|K1\|VB\|e0.002` | `ba0fc1b1d47f80c924c1c53ce1152fea7f0a213ffde343a391f420ab03a65557` | 94 | 같음 |
| 25 | `D1\|H-S-0\|J2\|T\|flat\|K1\|V0\|e0` | `a910b63b503d774a7e46c75a3d3a1d82ff3b35acb701385934cac3e989c6579b` | 92 | 같음 |
| 26 | `D1\|H-S-0\|J2\|T\|flat\|K1\|V0\|e0.002` | `a8597f4610a76e88922f42ed366e56315b5c4c33c38351e997c39f2c3808c43a` | 92 | 같음 |
| 27 | `D1\|H-S-0\|J2\|T\|flat\|K1\|VB\|e0` | `f28319bf5a8f43bb4ca014ab85bfb9763290259356e1b0d502ba9b78f367dc3f` | 93 | 같음 |
| 28 | `D1\|H-S-0\|J2\|T\|flat\|K1\|VB\|e0.002` | `5567b0f350c07a23295537991713e0cca2da1932e33f837adc472d0b2b1ddbd7` | 92 | 같음 |
| 29 | `D1\|H-S-1\|S1\|B\|flat\|K1\|V0\|e0` | `977dc20f93f0a889c828177d12ddda7fb64c35a909133ca682d2e2abe0ccb848` | 96 | 같음 |
| 30 | `D1\|H-S-1\|S1\|B\|flat\|K1\|V0\|e0.002` | `dbdc810b56f8233eddfa17225df0204db5ff8ec39a267c56cfede3659f020e04` | 94 | 같음 |
| 31 | `D1\|H-S-1\|S1\|B\|flat\|K1\|VB\|e0` | `a416584957909540d6ad40bfcb6d266649fa09ca7b75a4f374d922ab692deda1` | 94 | 같음 |
| 32 | `D1\|H-S-1\|S1\|B\|flat\|K1\|VB\|e0.002` | `7ca89b4a949eeef173ff36ab9f0fc9e3e691a61675dc755c1d2b82430b54bdc5` | 95 | 같음 |
| 33 | `D1\|H-S-1\|S1\|M\|flat\|K1\|V0\|e0` | `4c04dc45a4e55bdea7444d2a2199f4fc30982d2e914d04613b4cb5b9f4efe697` | 96 | 같음 |
| 34 | `D1\|H-S-1\|S1\|M\|flat\|K1\|V0\|e0.002` | `7bdc61c8c3f16e77cd5bbcdd2d5270e237f11aa4d09cbf37f348ebed098b8eb5` | 94 | 같음 |
| 35 | `D1\|H-S-1\|S1\|M\|flat\|K1\|VB\|e0` | `544bbf18449dbf6e75ae73b00f8bdf167ed23c7ac1a2047ded452116c60552c9` | 94 | 같음 |
| 36 | `D1\|H-S-1\|S1\|M\|flat\|K1\|VB\|e0.002` | `cd94f90e8ed8a287d45b3d9e107c9c0f1fcbddd76f46744c802eadf57eb1cd98` | 94 | 같음 |
| 37 | `D1\|H-S-1\|S1\|T\|flat\|K1\|V0\|e0` | `1cce0fb640bc6ed84b1ddaabb4800805bff808f83b7a853cbccf471783ee0dda` | 96 | 같음 |
| 38 | `D1\|H-S-1\|S1\|T\|flat\|K1\|V0\|e0.002` | `247aa5ad16c0a24b26f381bfde240f78e52b657a48fc241b5c778d5e24d8a0bd` | 95 | 같음 |
| 39 | `D1\|H-S-1\|S1\|T\|flat\|K1\|VB\|e0` | `47ead0c3a7de6242e1acd910a4a70b12ac794cedbca56b9d7eefff0a6aafba3f` | 96 | 같음 |
| 40 | `D1\|H-S-1\|S1\|T\|flat\|K1\|VB\|e0.002` | `9aef943f98d90de493909802c484e43fc959fe1f83333e26f984e0260b51c7e5` | 96 | 같음 |
| 41 | `D1\|H-S-A-J2\|G1+J2@FL\|T\|flat\|K1\|V0\|e0` | `4761352bd10a9a548e19bb75866c8ea6f24708365062e9e58c8ad3355ca53a24` | -5 | 바뀜 |
| 42 | `D1\|H-S-A-J2\|G1+J2@FL\|T\|flat\|K1\|V0\|e0.002` | `39278322f8775f25bf6c4e2c2f3f2ca8c4c9146f8f3b0e18365d3c8cbdc1d538` | -8 | 바뀜 |
| 43 | `D1\|H-S-A-J2\|G1+J2@FL\|T\|flat\|K1\|VB\|e0` | `84e60b8d062a472df8271a80e839af923b824a512030a67c64ab082d35b2a7eb` | -8 | 바뀜 |
| 44 | `D1\|H-S-A-J2\|G1+J2@FL\|T\|flat\|K1\|VB\|e0.002` | `66c5e1b0f1341b8c70a579d9e72e6dfa754fcd638c73e8fad87364179a1ee81b` | -4 | 바뀜 |
| 45 | `D1\|H-S-A\|G1+J1@FL\|B\|flat\|K1\|V0\|e0.002` | `ea32519dd82181468228be5c44a6e55bfb4a29e9f7fc801903f8de4e71d170fc` | -5 | 바뀜 |
| 46 | `D1\|H-S-C\|J1\|B\|flat\|K1\|c-edge@FL\|V0\|e0` | `92ccfede693529566f4068ce3d3377d64327a17e44c361808fb115b42fc7a5a0` | 40 | 같음 |
| 47 | `D1\|H-S-C\|J1\|B\|flat\|K1\|c-edge@FL\|V0\|e0.002` | `7cdba851c40f4a74a5f6a0c5264c86964ca02c6e35ec6ccdd28c300ea5f39eb4` | 40 | 같음 |
| 48 | `D1\|H-S-C\|J1\|B\|flat\|K1\|c-edge@FL\|VB\|e0` | `a1388f6652c9a1f63307351d54bd500e72cd6551a914739f0ebea141a5a26933` | 40 | 같음 |
| 49 | `D1\|H-S-C\|J1\|B\|flat\|K1\|c-edge@FL\|VB\|e0.002` | `efa261a6d9412afe35856260b66fa1532ee05471eefbba765f467fcf56c8a44b` | 40 | 같음 |
| 50 | `D1\|H-S-C\|J1\|B\|flat\|K1\|c-fast@FL\|V0\|e0` | `838b6ece525be1c401ebaf558aead4f88c9e855af1ddb1341d9df8bff4c8a6aa` | 40 | 같음 |
| 51 | `D1\|H-S-C\|J1\|B\|flat\|K1\|c-fast@FL\|V0\|e0.002` | `b6e63393818d701e95ad13231aeb01cc2a8f76d42a216654538ce301cf654ee6` | 40 | 같음 |
| 52 | `D1\|H-S-C\|J1\|B\|flat\|K1\|c-fast@FL\|VB\|e0` | `e4f40df9ac50f375eab6043151c844ab38635032cd587350394d4afb049b0367` | 40 | 같음 |
| 53 | `D1\|H-S-C\|J1\|B\|flat\|K1\|c-fast@FL\|VB\|e0.002` | `ca6c06b8fdafdc3edc0b4949079f1f7971899c926b44108daa3c2936f0b360ae` | 40 | 같음 |
| 54 | `D1\|H-S-C\|J1\|B\|flat\|K1\|c-mid@FL\|V0\|e0` | `d0ab3c0769a8ccc89fc4392f060cb397a1988f09ae57f648b25f4198f1d21303` | 40 | 같음 |
| 55 | `D1\|H-S-C\|J1\|B\|flat\|K1\|c-mid@FL\|V0\|e0.002` | `5207ee13067466be6ba2968ca3fbf3f92e2ee2537e08b684c07fd8cc03d7a4ec` | 40 | 같음 |
| 56 | `D1\|H-S-C\|J1\|B\|flat\|K1\|c-mid@FL\|VB\|e0` | `58bb37305c7a2fa12b5b44fc87584adb15bacfc35d2b7dd75a734db461f65e09` | 40 | 같음 |
| 57 | `D1\|H-S-C\|J1\|B\|flat\|K1\|c-mid@FL\|VB\|e0.002` | `1c23abc11882aa9fb4638773eed5b7cdae079f1ab700736a2d6e641e4637e180` | 40 | 같음 |
| 58 | `D1\|H-S-C\|J1\|B\|flat\|K1\|c-mid@RL\|V0\|e0` | `03846ccf05b211cc07a201c33a80bc085c3922488ff13177f66acb0af1d05861` | 40 | 같음 |
| 59 | `D1\|H-S-C\|J1\|B\|flat\|K1\|c-mid@RL\|V0\|e0.002` | `0df5f5df4c46d3fbd2f30b4ee860053160257ae9251cbb5aaf3c66ec1a48a9c6` | 40 | 같음 |
| 60 | `D1\|H-S-C\|J1\|B\|flat\|K1\|c-mid@RL\|VB\|e0` | `9da7fcaf78bcec0cb410cad177ae8fa406a72f39a5d7baae54d4a3aee23dbb31` | 40 | 같음 |
| 61 | `D1\|H-S-C\|J1\|B\|flat\|K1\|c-mid@RL\|VB\|e0.002` | `0a4fcb74dd255c1a31700a05ed9a73d754e5df3332e9a5f1451a11940acef595` | 40 | 같음 |
| 62 | `D1\|H-S-C\|J1\|B\|flat\|K1\|c-slow@FL\|V0\|e0` | `e307af08e2af64d2dc6ddd9fe31099b2a108c5f4bba69350702c2187bdf275fd` | 40 | 같음 |
| 63 | `D1\|H-S-C\|J1\|B\|flat\|K1\|c-slow@FL\|V0\|e0.002` | `a5174ef5b998c9d62414414a41e8523e86b237270d42ed6f08d101f9aef51e2a` | 40 | 같음 |
| 64 | `D1\|H-S-C\|J1\|B\|flat\|K1\|c-slow@FL\|VB\|e0` | `af7887732ffc023d2fd17eb56731c63070a362569a1f070c6bf73a0f8f6d0157` | 40 | 같음 |
| 65 | `D1\|H-S-C\|J1\|B\|flat\|K1\|c-slow@FL\|VB\|e0.002` | `5fa9c1e101a0789efb04b46eee55c172296eefb6b1872ce0c378a3e4949ee60c` | 40 | 같음 |
| 66 | `D1\|H-S-C\|J1\|M\|flat\|K1\|c-edge@FL\|V0\|e0` | `9c60d6a77d82ba87fa11b4c6f8950d8c0711af4247f4ca8e0ced5e0fc56dfaf9` | 39 | 같음 |
| 67 | `D1\|H-S-C\|J1\|M\|flat\|K1\|c-edge@FL\|V0\|e0.002` | `bfb42bbc2f57ee6540f7660c27a1ce457e342874aed690d519254d3779b25bb0` | 39 | 같음 |
| 68 | `D1\|H-S-C\|J1\|M\|flat\|K1\|c-edge@FL\|VB\|e0` | `fc6ecb98e5c0e66a3390dccbecb43ae635e67a6f87d43352a46138df68672dff` | 39 | 같음 |
| 69 | `D1\|H-S-C\|J1\|M\|flat\|K1\|c-edge@FL\|VB\|e0.002` | `8656093a38723886d418253a93b64eb409f5b31377695492b857ec45e98c206c` | 39 | 같음 |
| 70 | `D1\|H-S-C\|J1\|M\|flat\|K1\|c-fast@FL\|V0\|e0` | `372959e7b073d281e3d98d5a09779845cc2e47982839ef3702c8388b60adb2ec` | 39 | 같음 |
| 71 | `D1\|H-S-C\|J1\|M\|flat\|K1\|c-fast@FL\|V0\|e0.002` | `694c8b4acdba2e4bbfa5ec2864fa6a2e6d9cd557b3b392aecba4376289af464a` | 39 | 같음 |
| 72 | `D1\|H-S-C\|J1\|M\|flat\|K1\|c-fast@FL\|VB\|e0` | `92bec5b6939c6788010eb32564e6e16e0456d8c2133d9fa372015b3dcef50a0d` | 39 | 같음 |
| 73 | `D1\|H-S-C\|J1\|M\|flat\|K1\|c-fast@FL\|VB\|e0.002` | `7eb4e89d56bd7ecbd90c2751a028bbb845105585063f6f2c05c84e3123a882fc` | 39 | 같음 |
| 74 | `D1\|H-S-C\|J1\|M\|flat\|K1\|c-mid@FL\|V0\|e0` | `410dff2dfd4b2a1b435c5eeee856ca52ce4be29c1ea5d79b77deb7d6ccd3bcde` | 39 | 같음 |
| 75 | `D1\|H-S-C\|J1\|M\|flat\|K1\|c-mid@FL\|V0\|e0.002` | `6863e36d0aa2f0a8e41b889707eb3e57f0d355edde562096006c2d5efa7f6f5c` | 39 | 같음 |
| 76 | `D1\|H-S-C\|J1\|M\|flat\|K1\|c-mid@FL\|VB\|e0` | `96fcadf334566845473a2e25d007636e7d16a93d7a19960b8387914e61de90bb` | 39 | 같음 |
| 77 | `D1\|H-S-C\|J1\|M\|flat\|K1\|c-mid@FL\|VB\|e0.002` | `ca5820739c23b012537d3ce2751b65796a1d537544a4f9c793a04e2789312c90` | 39 | 같음 |
| 78 | `D1\|H-S-C\|J1\|M\|flat\|K1\|c-mid@RL\|V0\|e0` | `63a43067e1b86c6f8ce28c3e9d8af8675da6b4ed67cf0f45467ffaffea83f8bc` | 39 | 같음 |
| 79 | `D1\|H-S-C\|J1\|M\|flat\|K1\|c-mid@RL\|V0\|e0.002` | `e20c7517587c0ba8fb37ef64072dcf6d1c676bc9d89d4c9f9edf8c862756e1cb` | 39 | 같음 |
| 80 | `D1\|H-S-C\|J1\|M\|flat\|K1\|c-mid@RL\|VB\|e0` | `60edc6c6b30ffa7e473f3d0a98ed75fc3d083c6cf4afd361eb30ec673c29d383` | 39 | 같음 |
| 81 | `D1\|H-S-C\|J1\|M\|flat\|K1\|c-mid@RL\|VB\|e0.002` | `fd6a7afc332e7eb2d0ad3f3685e4bece10ab5335a3054b0ff9713a601418d6be` | 39 | 같음 |
| 82 | `D1\|H-S-C\|J1\|M\|flat\|K1\|c-slow@FL\|V0\|e0` | `66749788d3bc673dc852069ec84b353b8ce727acb2095798b6c9aca21ab8519b` | 39 | 같음 |
| 83 | `D1\|H-S-C\|J1\|M\|flat\|K1\|c-slow@FL\|V0\|e0.002` | `3e7570c4655998e72558e3df6048773f8e3b1b72bd5436d82a4085dac2f92b2c` | 39 | 같음 |
| 84 | `D1\|H-S-C\|J1\|M\|flat\|K1\|c-slow@FL\|VB\|e0` | `2961dc69b287eeb6f1fa9e235758e801969f238df2dcb4a1fc643b4a0f2863bc` | 39 | 같음 |
| 85 | `D1\|H-S-C\|J1\|M\|flat\|K1\|c-slow@FL\|VB\|e0.002` | `ea3de6254cc6c1b46f1cef3095910948e9e4c8a5a71465b607c6c5eb1cafe088` | 39 | 같음 |
| 86 | `D1\|H-S-C\|J1\|T\|flat\|K1\|c-edge@FL\|V0\|e0` | `42f6860c260762ee266d798e8bc5570b82a3ffe8cb704ac23df27447f8298fcf` | 38 | 같음 |
| 87 | `D1\|H-S-C\|J1\|T\|flat\|K1\|c-edge@FL\|V0\|e0.002` | `66719c25238da16969e225546b3a369233ddeab698d483680553b3813a89a9be` | 38 | 같음 |
| 88 | `D1\|H-S-C\|J1\|T\|flat\|K1\|c-edge@FL\|VB\|e0` | `c08762008c9983ef2d5b7b2e746cffe15fe320c611012cc0fadf59eca2f52a42` | 36 | 같음 |
| 89 | `D1\|H-S-C\|J1\|T\|flat\|K1\|c-edge@FL\|VB\|e0.002` | `b83325ece63e9b49e329e388b2880c4d26baea05ccbd82f25d5cd72da83fdf24` | 37 | 같음 |
| 90 | `D1\|H-S-C\|J1\|T\|flat\|K1\|c-fast@FL\|V0\|e0` | `7bf1ecc2514aed272506350f4cacd2b0b7c9cceb785de0ecad4524a19ab6021c` | 38 | 같음 |
| 91 | `D1\|H-S-C\|J1\|T\|flat\|K1\|c-fast@FL\|V0\|e0.002` | `6845cd118b80262ca386d66000328989cd7fcd35fe5fcc17219ea36bc9521c31` | 38 | 같음 |
| 92 | `D1\|H-S-C\|J1\|T\|flat\|K1\|c-fast@FL\|VB\|e0` | `b389c6650a073c69a37165db273d0666b62fd5190fd90effa3867c12a8283877` | 36 | 같음 |
| 93 | `D1\|H-S-C\|J1\|T\|flat\|K1\|c-fast@FL\|VB\|e0.002` | `cc8cee637b77e19dec5bbc77a83da76c737529d5fc39c76cb524cb0a8dba9379` | 37 | 같음 |
| 94 | `D1\|H-S-C\|J1\|T\|flat\|K1\|c-mid@FL\|V0\|e0` | `112d5b1cf6d9c1287c8104ce845094c527295f1cc045d6da9e405a4bb40537b2` | 38 | 같음 |
| 95 | `D1\|H-S-C\|J1\|T\|flat\|K1\|c-mid@FL\|V0\|e0.002` | `cc24e9c0e03bd333bff86af0b2f7117e6f43a5ac6bf23fe029aeb59d7bff59a6` | 38 | 같음 |
| 96 | `D1\|H-S-C\|J1\|T\|flat\|K1\|c-mid@FL\|VB\|e0` | `2d07a77ef74561925dd655a933581acab27a92a9bed3fc253c47fb04bdb61702` | 36 | 같음 |
| 97 | `D1\|H-S-C\|J1\|T\|flat\|K1\|c-mid@FL\|VB\|e0.002` | `939fd41a5d1640bfd04afb21a1ea21413f35feab9c70fa9c76c600559556a49d` | 37 | 같음 |
| 98 | `D1\|H-S-C\|J1\|T\|flat\|K1\|c-mid@RL\|V0\|e0` | `f5adb433dfef66b3ab5afd28d611d2c6f615e71d400ae8c24171148d3e1000ac` | 38 | 같음 |
| 99 | `D1\|H-S-C\|J1\|T\|flat\|K1\|c-mid@RL\|V0\|e0.002` | `2812ed79122b26f131264708bb98014b74951515aeb1eaf0af44035b6ae29572` | 38 | 같음 |
| 100 | `D1\|H-S-C\|J1\|T\|flat\|K1\|c-mid@RL\|VB\|e0` | `aaab9880a6d9dfb5691b4929fe3b7bddce8dafe0d0cc095c31ea315135e691a6` | 36 | 같음 |
| 101 | `D1\|H-S-C\|J1\|T\|flat\|K1\|c-mid@RL\|VB\|e0.002` | `ba88275c0fb2b0541c29d31c83dc781cad0c2e4674efbff8f5f09666b0ab9019` | 37 | 같음 |
| 102 | `D1\|H-S-C\|J1\|T\|flat\|K1\|c-slow@FL\|V0\|e0` | `156161159b2b6720bf4514c38b1c2f9c4d181cb697fa81dab3de13c5f56d64cd` | 38 | 같음 |
| 103 | `D1\|H-S-C\|J1\|T\|flat\|K1\|c-slow@FL\|V0\|e0.002` | `bafe13fe4ae6f49bade9a4d6e9373b7f5a3a576ad9c0c16f6e9923e991daf054` | 38 | 같음 |
| 104 | `D1\|H-S-C\|J1\|T\|flat\|K1\|c-slow@FL\|VB\|e0` | `f29de7546c46bff3d36b9728ecede2d2e853d468750647eb66bc577ecb1621f9` | 36 | 같음 |
| 105 | `D1\|H-S-C\|J1\|T\|flat\|K1\|c-slow@FL\|VB\|e0.002` | `2aaceb7231f6a68a9f82a2e6876eff3e82a9afe9273b14b4525aa33e53ff9369` | 37 | 같음 |
| 106 | `D1\|H-S-C\|J2\|B\|flat\|K1\|c-edge@FL\|V0\|e0` | `0469e325ec0bcbd5c045c8c4333c6d30c226a873efebecf41e4b2ee764223ce5` | 94 | 같음 |
| 107 | `D1\|H-S-C\|J2\|B\|flat\|K1\|c-edge@FL\|V0\|e0.002` | `b80c151a70fa717fbf665bc94390793a741a017346882cc3ad9e37394328b0e2` | 95 | 같음 |
| 108 | `D1\|H-S-C\|J2\|B\|flat\|K1\|c-edge@FL\|VB\|e0` | `cc1ab5a84cf0f36abab930df156cfebe1572fb33555d434cbca5a3b8193fd3dd` | 95 | 같음 |
| 109 | `D1\|H-S-C\|J2\|B\|flat\|K1\|c-edge@FL\|VB\|e0.002` | `b68e2bc96008777445ab9d61f1023173c9000acd937575e425ec7a7e0b1e6af0` | 95 | 같음 |
| 110 | `D1\|H-S-C\|J2\|B\|flat\|K1\|c-fast@FL\|V0\|e0` | `e844eeef1ef2b48bc6ed92e45f61ef42a859d63596a9c3e0af84b2d752e390fa` | 94 | 같음 |
| 111 | `D1\|H-S-C\|J2\|B\|flat\|K1\|c-fast@FL\|V0\|e0.002` | `3151725ff6a79d66e5900eb61acc4d8656f768432f333c633237b7b70ee69890` | 95 | 같음 |
| 112 | `D1\|H-S-C\|J2\|B\|flat\|K1\|c-fast@FL\|VB\|e0` | `7090f9ad019bc7108d3eae0a31133da4d284f30f6f31a546b7167bc8f395071b` | 95 | 같음 |
| 113 | `D1\|H-S-C\|J2\|B\|flat\|K1\|c-fast@FL\|VB\|e0.002` | `5e66840725c6cbe4b1c5aae74d9f446fa362e76f4e305d5ac635328a0849cc48` | 95 | 같음 |
| 114 | `D1\|H-S-C\|J2\|B\|flat\|K1\|c-mid@FL\|V0\|e0` | `26eb7cbd65abff67b6dd2f076ac933666c998cbc915819f4f8f2b8c2b61a7870` | 94 | 같음 |
| 115 | `D1\|H-S-C\|J2\|B\|flat\|K1\|c-mid@FL\|V0\|e0.002` | `8714ca888e322088eeaf8218186594390fa3fef71001176fbba5e976ad0b3c75` | 95 | 같음 |
| 116 | `D1\|H-S-C\|J2\|B\|flat\|K1\|c-mid@FL\|VB\|e0` | `d79ab9831533333cb00db44d34217d71a8c49f8f52006094d29dca5fba9e1ef1` | 95 | 같음 |
| 117 | `D1\|H-S-C\|J2\|B\|flat\|K1\|c-mid@FL\|VB\|e0.002` | `244c1b90810976ad47a5ff1d73b4e7913fa72d1f75ad9041f834d24e72c7fec3` | 95 | 같음 |
| 118 | `D1\|H-S-C\|J2\|B\|flat\|K1\|c-mid@RL\|V0\|e0` | `c42c7d9d1fe13060e89e6d6b3b7a19b3744d64a8092a19ef3f7646f2783fb149` | 94 | 같음 |
| 119 | `D1\|H-S-C\|J2\|B\|flat\|K1\|c-mid@RL\|V0\|e0.002` | `7bf01eb7fbb5df36fe758a97837657fe5975249d305ca5b04bc90b4845350d6d` | 95 | 같음 |
| 120 | `D1\|H-S-C\|J2\|B\|flat\|K1\|c-mid@RL\|VB\|e0` | `7e13732bc30c4d0f25e1b748f9ecaa16f98f6fc3f33d2dda182bd519b33cbaf6` | 95 | 같음 |
| 121 | `D1\|H-S-C\|J2\|B\|flat\|K1\|c-mid@RL\|VB\|e0.002` | `0586db4ec0afe4555c815f3d4ac1736405460d53fd7286bbd3d756165afdf527` | 95 | 같음 |
| 122 | `D1\|H-S-C\|J2\|B\|flat\|K1\|c-slow@FL\|V0\|e0` | `1f3da6e143762940ccbf3aa0d8d914e16c1d1bde55859b0ae03f0092b0cf7244` | 94 | 같음 |
| 123 | `D1\|H-S-C\|J2\|B\|flat\|K1\|c-slow@FL\|V0\|e0.002` | `db002ed4b57ce3a31fdd7b96fa0611f8916adfe843cf99702b3e08b93cfcc73e` | 95 | 같음 |
| 124 | `D1\|H-S-C\|J2\|B\|flat\|K1\|c-slow@FL\|VB\|e0` | `5730ed3f183799f51c79746595be6cdb47e546416672b4e485299245862da372` | 95 | 같음 |
| 125 | `D1\|H-S-C\|J2\|B\|flat\|K1\|c-slow@FL\|VB\|e0.002` | `3516c8870cb43ca1201a9c86ba56f168e6e6d5a545f5cb26dd5dba4e6aa471c3` | 95 | 같음 |
| 126 | `D1\|H-S-C\|J2\|M\|flat\|K1\|c-edge@FL\|V0\|e0` | `c2aae30cc7677e5713efdb597830ddd4750cd72aa4136e69964ad0d81230526e` | 94 | 같음 |
| 127 | `D1\|H-S-C\|J2\|M\|flat\|K1\|c-edge@FL\|V0\|e0.002` | `95c0b27ef309157d9b8c2e0b9dc197ad6bcbc8f508307fcd083a31899fd19ae4` | 94 | 같음 |
| 128 | `D1\|H-S-C\|J2\|M\|flat\|K1\|c-edge@FL\|VB\|e0` | `0ec8351eb9bd4a9909e51e9ce86326907e5ed99b13ecbd6aec1383f8d40184db` | 94 | 같음 |
| 129 | `D1\|H-S-C\|J2\|M\|flat\|K1\|c-edge@FL\|VB\|e0.002` | `fe2ab6a13bdbda0d05e7885e0503592b9bd598a92e530fad339138bd65d603d5` | 94 | 같음 |
| 130 | `D1\|H-S-C\|J2\|M\|flat\|K1\|c-fast@FL\|V0\|e0` | `b5519b968f1985ad1cde9771f8c7e18744ff47ad78f56a5b5c7a1bc3f84374fd` | 94 | 같음 |
| 131 | `D1\|H-S-C\|J2\|M\|flat\|K1\|c-fast@FL\|V0\|e0.002` | `de6e1f020fd30b3c031c44297b49be333b2283587c178963afbd5c1b7d44e590` | 94 | 같음 |
| 132 | `D1\|H-S-C\|J2\|M\|flat\|K1\|c-fast@FL\|VB\|e0` | `95c19c2c2ac118fe78bf2d5d7653839110fade62e93109379830566077b08a9b` | 94 | 같음 |
| 133 | `D1\|H-S-C\|J2\|M\|flat\|K1\|c-fast@FL\|VB\|e0.002` | `30fb63edda6de251351bd97fd1b712d49a4843745293508c22fd6b858cb0c087` | 94 | 같음 |
| 134 | `D1\|H-S-C\|J2\|M\|flat\|K1\|c-mid@FL\|V0\|e0` | `8c450ab10be2e4862450d9b84523b97ea4ec0aa70a0a5bf06500097202d80466` | 94 | 같음 |
| 135 | `D1\|H-S-C\|J2\|M\|flat\|K1\|c-mid@FL\|V0\|e0.002` | `500ab77b7200e40358ee6fffea77aab929a3468abc1e8e51f452f58090f09909` | 94 | 같음 |
| 136 | `D1\|H-S-C\|J2\|M\|flat\|K1\|c-mid@FL\|VB\|e0` | `500f40b40bd908f1bf48f87437764ad1b4766a1d7462676fe68e6fce509262e6` | 94 | 같음 |
| 137 | `D1\|H-S-C\|J2\|M\|flat\|K1\|c-mid@FL\|VB\|e0.002` | `a4ba88663e0cc83828cdab7d9f931baf3f4e982655d62be915f3809b686a7e7b` | 94 | 같음 |
| 138 | `D1\|H-S-C\|J2\|M\|flat\|K1\|c-mid@RL\|V0\|e0` | `52d3ac17e8f384a81cf04266901a2d5ed7c03dc0f997289e853425825fd0aae8` | 94 | 같음 |
| 139 | `D1\|H-S-C\|J2\|M\|flat\|K1\|c-mid@RL\|V0\|e0.002` | `1ad13ea8257b973db5410e5a8407da2634536c8c2990922c0bc38e3509f2e9a0` | 94 | 같음 |
| 140 | `D1\|H-S-C\|J2\|M\|flat\|K1\|c-mid@RL\|VB\|e0` | `42c991a952ebdc2f48fe4468cba1ae787350ae42d73b4792a3c1110b4136f7d9` | 94 | 같음 |
| 141 | `D1\|H-S-C\|J2\|M\|flat\|K1\|c-mid@RL\|VB\|e0.002` | `1b2e17d2c6b1b6961f3482053c30840ea20e848eea1368305efbf2aeeab57a4c` | 94 | 같음 |
| 142 | `D1\|H-S-C\|J2\|M\|flat\|K1\|c-slow@FL\|V0\|e0` | `547b43d1bf77b36c368be2c9052e642238c16b864832175224f4ae47f6dce773` | 94 | 같음 |
| 143 | `D1\|H-S-C\|J2\|M\|flat\|K1\|c-slow@FL\|V0\|e0.002` | `8d0da6bfbb07a82b123ca22afb2c7f6cd6f5b8888b818aac6c2f1f341cdc1257` | 94 | 같음 |
| 144 | `D1\|H-S-C\|J2\|M\|flat\|K1\|c-slow@FL\|VB\|e0` | `2c1e1b53945f9546f8e22e195e000a9d8a45a80dee7211732dc98dfc9f24e6aa` | 94 | 같음 |
| 145 | `D1\|H-S-C\|J2\|M\|flat\|K1\|c-slow@FL\|VB\|e0.002` | `7753a28dfd0d62566ce8470a802ba5e4b56bf0147a931826407abd778f7f4331` | 94 | 같음 |
| 146 | `D1\|H-S-C\|J2\|T\|flat\|K1\|c-edge@FL\|V0\|e0` | `e1cd4cc71f3b22ec2f8906abd11f06f6a42f90ae42ceae2477b804deb75e9ddc` | 92 | 같음 |
| 147 | `D1\|H-S-C\|J2\|T\|flat\|K1\|c-edge@FL\|V0\|e0.002` | `716df5ff91fe0263ce98f5ef2e5e086fc8101d830149a5ff381597f4c4c161f8` | 92 | 같음 |
| 148 | `D1\|H-S-C\|J2\|T\|flat\|K1\|c-edge@FL\|VB\|e0` | `1ccbdc0844e9b239f9b81d08458228e6c32ddc7c0dcee765a29833acba45700a` | 93 | 같음 |
| 149 | `D1\|H-S-C\|J2\|T\|flat\|K1\|c-edge@FL\|VB\|e0.002` | `95b7f7d9073ada4ca876483ae03d2fdb1b0bc9997859f745dda8949c05a8e6ee` | 92 | 같음 |
| 150 | `D1\|H-S-C\|J2\|T\|flat\|K1\|c-fast@FL\|V0\|e0` | `77da612919fcd7020dffe951fa5c44529e9292bdf0fed8cfa92ecf2e5d00b282` | 92 | 같음 |
| 151 | `D1\|H-S-C\|J2\|T\|flat\|K1\|c-fast@FL\|V0\|e0.002` | `acc939cc0275f806f10296cc85ddfe4b213130296c2b38ebe7da2cb72b7f5b47` | 92 | 같음 |
| 152 | `D1\|H-S-C\|J2\|T\|flat\|K1\|c-fast@FL\|VB\|e0` | `252ca25af4373539a80dd660f83c1eb6aeb8af94252e8a31c4e53b40f0bb4117` | 93 | 같음 |
| 153 | `D1\|H-S-C\|J2\|T\|flat\|K1\|c-fast@FL\|VB\|e0.002` | `a925c3a169956573b566f3638785ede1a5568bcd7f383c3568861cc6e536410c` | 92 | 같음 |
| 154 | `D1\|H-S-C\|J2\|T\|flat\|K1\|c-mid@FL\|V0\|e0` | `d44a72acac87c74219a50acd2c303b67651e06ff219c12648b70b58790224dab` | 92 | 같음 |
| 155 | `D1\|H-S-C\|J2\|T\|flat\|K1\|c-mid@FL\|V0\|e0.002` | `e0c08faaee7548eae125d63325b8d6de440082cf4587f4fee16800de706a3ba7` | 92 | 같음 |
| 156 | `D1\|H-S-C\|J2\|T\|flat\|K1\|c-mid@FL\|VB\|e0` | `5f01873ab4168266c731da8942b0db8db086f2b4b3f820e66b99d109fc0e91c9` | 93 | 같음 |
| 157 | `D1\|H-S-C\|J2\|T\|flat\|K1\|c-mid@FL\|VB\|e0.002` | `38db5b3cbe36a91f9df045a1f9550c3bfc8f847b4e0a77491ecf86b0d070ce56` | 92 | 같음 |
| 158 | `D1\|H-S-C\|J2\|T\|flat\|K1\|c-mid@RL\|V0\|e0` | `57f4ce6cde9673bd5c4f7f03fbda1298574e4ade94cb8953a899d65f33db9f7c` | 92 | 같음 |
| 159 | `D1\|H-S-C\|J2\|T\|flat\|K1\|c-mid@RL\|V0\|e0.002` | `6a2196e22d9e48a1117a03b9a38c3e1b8af90dd4bf53819fe48d4bb7a507e38e` | 92 | 같음 |
| 160 | `D1\|H-S-C\|J2\|T\|flat\|K1\|c-mid@RL\|VB\|e0` | `54314628f8aebed8b2797506013f286da3fb18b17f6f30fef1cad159b4777d3f` | 93 | 같음 |
| 161 | `D1\|H-S-C\|J2\|T\|flat\|K1\|c-mid@RL\|VB\|e0.002` | `236fc65455ccf16274d356ac01df4f60305af9812fd31999ecd364527f17988d` | 92 | 같음 |
| 162 | `D1\|H-S-C\|J2\|T\|flat\|K1\|c-slow@FL\|V0\|e0` | `fe430bf2c245e79c0e4f4b519f287bb625ba7fccb055aaf62510345a3182c4f8` | 92 | 같음 |
| 163 | `D1\|H-S-C\|J2\|T\|flat\|K1\|c-slow@FL\|V0\|e0.002` | `7bb8ddd5ff2a5ff1049718eb0372a69475f0558ff340b8ae1d50ac5eb0cc52e5` | 92 | 같음 |
| 164 | `D1\|H-S-C\|J2\|T\|flat\|K1\|c-slow@FL\|VB\|e0` | `b30f262458d1f1b9e3f6652a621da4b8e057d23941fd1fb05e20451b8a01923e` | 93 | 같음 |
| 165 | `D1\|H-S-C\|J2\|T\|flat\|K1\|c-slow@FL\|VB\|e0.002` | `96935e453deaa74582281fa4e956ec3ce582e4a19472febd1d96c45caef1e409` | 92 | 같음 |

## 부록 B. Y-0d·Y-Pb S-C 비R4 표본 40키

- 선택 규칙: S-C 456줄 중 `INFO_LOC_FLAT_SOIL_MARGIN`이 없는 291줄을 sha256(키 UTF-8)의 16진 문자열 오름차순으로 정렬해 앞 40키(시드 없음, 결정적).
- 목록 sha256 `ef6c010dcbc48db71cc79a87d7558f46a65f5f9f544cca2d00fc623b287de684` (40키)

| # | 키 | 저장 `commands_sha256` |
|---|---|---|
| 1 | `D1\|H-S-0\|G1\|B\|flat\|K1\|VB\|e0.002` | `9804ffa50fd1818e7b79ef2492a197497a6ec956afe480a4afb32363bfc59d50` |
| 2 | `D1\|H-S-0\|G1\|B\|fup-rec\|K1\|V0\|e0.002` | `19bc72c0e122b8c4ed49cb6211f13716def538f1939e25232e6a5add50bcc46e` |
| 3 | `D1\|H-S-0\|G1\|M\|flat\|K1\|VB\|e0` | `1ae6774941da1273c3288363fa65bf77901f89410b600ae11ecff4ae04879d9a` |
| 4 | `D1\|H-S-0\|G1\|M\|roll-rec\|K1\|VB\|e0.002` | `2ca630afae19d531240fe1ca5944c4cbde4275b11cfc4f840eaea884af202761` |
| 5 | `D1\|H-S-0\|G1\|T\|fdown-rec\|K1\|V0\|e0.002` | `9ed9e24c4b47ff83b9026368366cd4299cba2276b6f79cab75ca859f4c4ae0f5` |
| 6 | `D1\|H-S-0\|G1\|T\|fdown-rec\|K1\|VB\|e0` | `8b25882040a070aa2925696198842451539a631e06b46f7d6365c15f26c611c5` |
| 7 | `D1\|H-S-0\|G1\|T\|flat\|K1\|V0\|e0.002` | `7280a9d7d88b0963ecc903d57e7505f4c24da8cc3bcb5575367daa0da5322279` |
| 8 | `D1\|H-S-0\|G1\|T\|roll+rec\|K1\|VB\|e0` | `5d2fc4b7618c49cdf1073e0dd2d44f2b1e452540432773b764afb11eae51212d` |
| 9 | `D1\|H-S-0\|G1\|T\|roll-rec\|K1\|VB\|e0` | `a928dc39b63799237e9e786cbf183c4a60a5317b7119e45e2fcd6fdb11f5c39f` |
| 10 | `D1\|H-S-0\|J1\|B\|fdown-rec\|K1\|V0\|e0.002` | `f8b661dfa2c63bf28d3b1b1bc6f10105aa445a4ec8afe3b551a42661ba5993eb` |
| 11 | `D1\|H-S-0\|J1\|B\|roll-rec\|K1\|VB\|e0` | `9ecb00cc6bf3b0f967b1b777b72a516a944fb07c407e3031fc993dd76293f7ee` |
| 12 | `D1\|H-S-0\|J1\|B\|roll-rec\|K1\|VB\|e0.002` | `5f383fdfefccf41c339dc6648de2fcacab5d0f2c0dd3983470a6800fa5a89c3a` |
| 13 | `D1\|H-S-0\|J1\|M\|roll+rec\|K1\|V0\|e0` | `07d01e4f9bb8329be66aef30d4ec07a9cfd60e51b09ae9566a0a87d9d502c30b` |
| 14 | `D1\|H-S-0\|J1\|T\|fdown-rec\|K1\|V0\|e0.002` | `dd4c301e15698988bc5807b78fdc2a35c33225872e5c14725e589c42f43ff583` |
| 15 | `D1\|H-S-0\|J2\|B\|fdown-rec\|K1\|V0\|e0.002` | `1211820c73f227d3cf187fa837568487130dd6472cf332104e741a01fc5a22c2` |
| 16 | `D1\|H-S-0\|J2\|B\|fup-rec\|K1\|V0\|e0` | `5af68b794b223864c4149b842a65cb0483fea2faf16176640123e946dc81e139` |
| 17 | `D1\|H-S-0\|J2\|B\|fup-rec\|K1\|V0\|e0.002` | `e4a9e46f143354c83eb252460b822c6568ce42aed2ffa59441bd30472d665f42` |
| 18 | `D1\|H-S-0\|J2\|B\|roll-rec\|K1\|VB\|e0` | `0678ed35f90079dc450e7d4a2b1907a6b3805cf0539e8c4f4cc55ff2cc88a2cc` |
| 19 | `D1\|H-S-0\|J2\|M\|fup-rec\|K1\|VB\|e0` | `31943d3a59b47785148684cf32560501a72509e35e70451bc9e1cdbc74ce36f3` |
| 20 | `D1\|H-S-0\|J2\|M\|roll+rec\|K1\|V0\|e0` | `f324197a1bed8362cc66586461b372918f2aca5d66b516486375bdb7bd532c23` |
| 21 | `D1\|H-S-0\|J2\|M\|roll+rec\|K1\|V0\|e0.002` | `14d5b9b8fc7266f1df7d1b99d937e1e412bec6c2f633d93305d342081ff0df66` |
| 22 | `D1\|H-S-0\|J2\|T\|diag-rec\|K1\|VB\|e0.002` | `7c2cbe7e3e0f692661519a8664f572381a211e9e9092fd302933019bf77abdff` |
| 23 | `D1\|H-S-0\|J2\|T\|fup-rec\|K1\|V0\|e0` | `4c1643cab9a2980e33a91875f285f42ed5806f45d5857d4202644e564db22cdb` |
| 24 | `D1\|H-S-0\|J2\|T\|roll+rec\|K1\|VB\|e0` | `047dea52fe1571223ffc539ffb82855ed0e06941be3c77b76bbb0348ddb786ef` |
| 25 | `D1\|H-S-A\|G1+J1@FL\|B\|flat\|K1\|V0\|e0` | `c4c37a9cff8a57bd03c151c745b8652f6fdec9f0662e098ab00591ecf2f42dcd` |
| 26 | `D1\|H-S-A\|G1+J1@FL\|B\|flat\|K1\|VB\|e0` | `c9885721f328e93ab9ba6335f41e87d9f2dc68913cd917fc21567511b52f2992` |
| 27 | `D1\|H-S-A\|G1+J1@FL\|M\|flat\|K1\|V0\|e0` | `67077113694a07c3c7ec01ab7dbe65367a9ae09ca320ed5b673445315058668d` |
| 28 | `D1\|H-S-A\|G1+J1@FL\|M\|flat\|K1\|VB\|e0` | `e95a6388726420e00d220e864496caac3e15ba4dba965a59eb00755381e48dc6` |
| 29 | `D1\|H-S-A\|G1+J1@FR\|B\|diag-psa-soil\|K1\|VB\|e0` | `0a4b81c68c5a6f3182762a10408d22c51ce1b050566bbba544905f5fa0a87110` |
| 30 | `D1\|H-S-A\|G1+J1@FR\|M\|diag-psa-soil\|K1\|V0\|e0.002` | `e1339fbc3b63ae1dfc3b1da4d29630bcb719d0d150260a2b13bce0ce7430d855` |
| 31 | `D1\|H-S-A\|G1+J1@RL\|B\|fup-psa\|K1\|V0\|e0.002` | `6b4b7e8ee2f8969522841abb9cb5e0f7eeb28e3bd7c60d65d4eaa59ae6102db4` |
| 32 | `D1\|H-S-A\|G1+J1@RL\|B\|fup-psa\|K1\|VB\|e0` | `a6460e0df1ede2d57dccf131c27a5d1746e066f2d9b7fbdbd4ac4ec8b571527f` |
| 33 | `D1\|H-S-A\|G1+J1@RL\|B\|fup-psa\|K1\|VB\|e0.002` | `f804da7646f03a1c849e8cbb068c5ea98649db7f3b437b21fc6b065b990427bc` |
| 34 | `D1\|H-S-A\|G1+J1@RL\|B\|roll-op\|K1\|VB\|e0.002` | `864b0f7169d4681e46648141aec57364003a81495a258350e92857f0a9ac3951` |
| 35 | `D1\|H-S-A\|G1+J1@RL\|M\|fup-psa\|K1\|V0\|e0.002` | `363a1d37ad9873fe259263e1efa3b4c12e540637380077ecb2313c889ce34cc2` |
| 36 | `D1\|H-S-A\|G1+J1@RL\|M\|roll-op\|K1\|V0\|e0` | `2803084f23715627c7a9ee4b17233f8fcb22ea4d256cebddc45af738a7755476` |
| 37 | `D1\|H-S-C-g\|J1\|B\|diag-rec\|K1\|c-mid@FR\|dsb_gated_off\|VB\|e0` | `267c7be9e81fe903a62390b36c60136b9053f7a5d84abc26f3e17d532e20a15a` |
| 38 | `D1\|H-S-C-g\|J1\|B\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|V0\|e0` | `795edd2dfdffac80cc36a02774e689ad180922790c0e54715e8b8b3973d8462f` |
| 39 | `D1\|H-S-C-g\|J1\|M\|diag-rec\|K1\|c-mid@FR\|dsb_gated_off\|VB\|e0` | `0f231f70b513e32877c4192ce94aebcad99e72ae199f0f0db9ed49d12326056d` |
| 40 | `D1\|H-S-C-g\|J1\|M\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|VB\|e0` | `ccc1feb8bf9baae802a8fb6e3a3795989046da296756a67af1950875ff23f0f7` |

## 부록 C. Y-0b·Y-0c·Y-Sa·Y-Sb R-S 30키 (`revA_RS.jsonl` sha256 `7c407b6ee07b001f5504186fa013193ba6a2992516021f263b2bb537de43875d`)

- 목록 sha256 `19c78b49197ac53da5ae50808555c5879aabc90765589ea220830d5588a23950` (30키: D-1 20 + verdict 사례 10)
- Y-Sb 변경 예측 2키 목록 sha256 `56177ba0a566a28b3fb8422872118b8392f4b1bcb06e7b01065ac6bce061c8a5`, Y-Sa 변경 예측 1키 목록 sha256 `7a7caafd5e2b1aba0acbe88e5f85a54c15d2fd699b36d52fe931106a98022d76`
- 저장 해시는 P5r4 줄(Y-0b 기준). Y-0c 기준(P0)은 A안 원판 3.3의 L 줄(없으면 `revA_RP0.jsonl`, sha256 `9be02cafce97fa4e4a5f4892d55f5d3d8dcd652de85da0f5bdfbe0a34d127300`).

| # | 키 | 저장 P5r4 `commands_sha256` | P5r4 R4c30 | Y-Sa 예측 | Y-Sb 예측 |
|---|---|---|---|---|---|
| 1 | `D1\|H-R-A-J2\|rigid+J2@FL\|T\|flat\|K1\|VB\|e0` | `deffc51c3c31c7544d10d594c5bde1b43c70c52298ea2d7ec982ae62dcf1d815` | 없음 | 같음 | 같음 |
| 2 | `D1\|H-R-A-S1\|rigid+S1@FL\|T\|flat\|K1\|VB\|e0` | `8f8e15f12042a98f9986b3e720d9633523c93f5d30392b06d828be896310e93d` | 있음 | 같음 | 같음 |
| 3 | `D1\|H-R-A-stop\|rigid+J1@RL\|T\|fup-op\|K1\|VB\|e0` | `74d4adc2a610f92ef1b1faebea22518d1c3f8720c7affa17eb9b8becc4b70a48` | 없음 | 같음 | 같음 |
| 4 | `D1\|H-S-0\|G1\|T\|diag-rec\|K1\|VB\|e0` | `c94a8461d362ed092b46cc47ce84fe8cc59f58296075be18cbf0642dc5290fa1` | 없음 | 같음 | 같음 |
| 5 | `D1\|H-S-0\|G1\|T\|flat\|K1\|VB\|e0` | `77a9fcb1ba89ebeae1f52e24e207c6587c0a140a55a7f8146e2681c60554f3b1` | 없음 | 같음 | 같음 |
| 6 | `D1\|H-S-0\|J1\|T\|diag-rec\|K1\|VB\|e0` | `b222e3ec3ab2f53456f8a66ecb4cc565880a0df1ab2476841ecfde79392772dd` | 없음 | 같음 | 같음 |
| 7 | `D1\|H-S-0\|J1\|T\|flat\|K1\|V0\|e0` | `2a3b8618080698f7bd95258c100000b57d7de413f473be45a63989e0d1fe66c4` | 있음 | 같음 | 같음 |
| 8 | `D1\|H-S-0\|J1\|T\|flat\|K1\|VB\|e0` | `4cdb5661e644adc4fadff1092f9021b16ffb5d8f6e586164ea0973298c2054fa` | 있음 | 같음 | 같음 |
| 9 | `D1\|H-S-0\|J2\|T\|diag-rec\|K1\|VB\|e0` | `c23d6818bb900526eff2bde652e90371b447751131fa5bebe70b40338126415e` | 없음 | 같음 | 같음 |
| 10 | `D1\|H-S-0\|J2\|T\|flat\|K1\|VB\|e0` | `f28319bf5a8f43bb4ca014ab85bfb9763290259356e1b0d502ba9b78f367dc3f` | 있음 | 같음 | 같음 |
| 11 | `D1\|H-S-1\|S1\|B\|flat\|K1\|VB\|e0` | `a416584957909540d6ad40bfcb6d266649fa09ca7b75a4f374d922ab692deda1` | 있음 | 같음 | 같음 |
| 12 | `D1\|H-S-1\|S1\|M\|flat\|K1\|VB\|e0` | `544bbf18449dbf6e75ae73b00f8bdf167ed23c7ac1a2047ded452116c60552c9` | 있음 | 같음 | 같음 |
| 13 | `D1\|H-S-1\|S1\|T\|flat\|K1\|VB\|e0` | `47ead0c3a7de6242e1acd910a4a70b12ac794cedbca56b9d7eefff0a6aafba3f` | 있음 | 같음 | 같음 |
| 14 | `D1\|H-S-A-J2\|G1+J2@FL\|T\|flat\|K1\|VB\|e0` | `7a6cdcc59458ec84ad5d3a6d328a18a238d016af148fe929810529e5fb8fa926` | 있음 | 바뀜 | 바뀜 |
| 15 | `D1\|H-S-A\|G1+J1@FL\|T\|flat\|K1\|VB\|e0` | `eeacc7830847ecf2d597446d235277c990643f909dac06f8538038f29d5bbb9d` | 있음 | 같음 | 바뀜 |
| 16 | `D1\|H-S-A\|G1+J1@FR\|T\|diag-psa-soil\|K1\|VB\|e0` | `407205434b1418db59ded9563568c323b487f9a92a3f7ef2c5f6d33d07652ff7` | 없음 | 같음 | 같음 |
| 17 | `D1\|H-S-A\|G1+J1@RL\|T\|flat\|K1\|VB\|e0` | `84d8ce3b8a5be6d8bddc7e1cf1cc7508cf83375c231b692b6b0bcd233e45fd89` | 없음 | 같음 | 같음 |
| 18 | `D1\|H-S-C-g\|J1\|T\|fdown-rec\|K1\|c-mid@FL\|dsb_gated_off\|VB\|e0` | `6892340e39e5c6074512dfd0fd683bdec3f97db4f08e007311462482e79d8adc` | 없음 | 같음 | 같음 |
| 19 | `D1\|H-S-C\|J1\|T\|flat\|K1\|c-mid@FL\|VB\|e0` | `2d07a77ef74561925dd655a933581acab27a92a9bed3fc253c47fb04bdb61702` | 있음 | 같음 | 같음 |
| 20 | `D1\|H-S-C\|J1\|T\|flat\|K1\|c-mid@RL\|VB\|e0` | `aaab9880a6d9dfb5691b4929fe3b7bddce8dafe0d0cc095c31ea315135e691a6` | 있음 | 같음 | 같음 |
| 21 | `R12\|V0\|etadef\|e0\|o0` | `aa147ff6d2839b90dc27de7baff5bc2b24c330b1a3d5be169ff5b739a801b20b` | 없음 | 같음 | 같음 |
| 22 | `R12\|VB\|etadef\|e0\|o0` | `017b1959826bda43cb43e64b6de2a162e800f5ef26125dc7c8e21f23d8183646` | 없음 | 같음 | 같음 |
| 23 | `R14\|V0\|etadef\|e0\|o0` | `da0bc2da8b3e1ce529a3ad2020ddbae27c522fa04913c50f0800ab8fbf0f4970` | 없음 | 같음 | 같음 |
| 24 | `R14\|VB\|etadef\|e0\|o0` | `040df0e6aec69c89d858ff8abed178cd54b45acc040f923ed0f70ae2060aafbb` | 없음 | 같음 | 같음 |
| 25 | `R15\|V0\|etadef\|e0\|o0.05` | `ecd47c0a61f752c3f76869b5b6752941661aad49b64e0e2f8b05b4ecd56f5136` | 없음 | 같음 | 같음 |
| 26 | `R15\|VB\|etadef\|e0\|o0.05` | `55bca14142a32c9b35654b12058c40758368a354c82b28dc5c27e0bdef90700d` | 없음 | 같음 | 같음 |
| 27 | `R16\|V0\|etadef\|e0\|o0.05` | `83afbea09ebba4696970a2e957a2aba8106857a4eef1dabc4e731b9e92d3a5af` | 없음 | 같음 | 같음 |
| 28 | `R16\|VB\|etadef\|e0\|o0.05` | `25f053f17fc5c46e38f88b67fe59831b7fb483ef4df8b3e2f6c7608d557eba71` | 없음 | 같음 | 같음 |
| 29 | `R2\|V0\|etadef\|e0\|reanchor_on` | `871d93544e6f874cd9f00ab388939270c5d4b5afb8bbb470eabaef517c9764ab` | 없음 | 같음 | 같음 |
| 30 | `R2\|VB\|etadef\|e0\|reanchor_on` | `c1f06f2057b097c5180a67a7fce0c87168d8441b22563b72485a3d410016b6c4` | 없음 | 같음 | 같음 |

## 부록 D. Y-T R-T 192키 (`revA_RT.jsonl` sha256 `c72f7e0882c50d86e565366866526ed55073d8bfef5c9f959b82c0e2885afd54`)

- 목록 sha256 `4160bddfff318f8c13b36652c3203e89a02159b5fd5a624499aa6ef0940fe933` (192키, R4c30 행 0). 192키 모두 해시가 같아야 한다.

| # | 키 | 저장 `commands_sha256` |
|---|---|---|
| 1 | `D1\|H-R-0\|rigid\|T\|diag-op\|K1\|V0\|e0` | `46e7b1296ca5f437e1156faa89b87005ea033b12a06dd0aafb07418ea59f6177` |
| 2 | `D1\|H-R-0\|rigid\|T\|diag-op\|K1\|V0\|e0.002` | `2132cd63a94d457826f8797baea24ddc9b246cb23373c9c62e38bb03e9e7598f` |
| 3 | `D1\|H-R-0\|rigid\|T\|diag-op\|K1\|VB\|e0` | `904ad9c6c52da711f9f7f58d834a761d89451e99fa48e065961814d6b2bbbc7a` |
| 4 | `D1\|H-R-0\|rigid\|T\|diag-op\|K1\|VB\|e0.002` | `3277e0f03df83bfeb701890b7ea7da1fb935a3b6c56986291eb429c4c58648b5` |
| 5 | `D1\|H-R-0\|rigid\|T\|diag-op\|K3\|V0\|e0` | `ff75943e30691d66f745f4da1365888572a0bd3b0b0cbb65f038d22b6a3ea3d7` |
| 6 | `D1\|H-R-0\|rigid\|T\|diag-op\|K3\|V0\|e0.002` | `29647da440e302b2d68da73944fc856507222aecd81aea565957b97050a8e78f` |
| 7 | `D1\|H-R-0\|rigid\|T\|diag-op\|K3\|VB\|e0` | `a5d4a28a1326130ca6742fdbc4c7801b2c789a35f73b9b121f46d300383e70dc` |
| 8 | `D1\|H-R-0\|rigid\|T\|diag-op\|K3\|VB\|e0.002` | `7d587d1fe3f47e653e8a5e2914ff957974b589d578500514b84a26ba42b68a9a` |
| 9 | `D1\|H-R-0\|rigid\|T\|diag-val\|K1\|V0\|e0` | `48114616d0a470e133fe0d4f9de1dd35a2a94d9b1339d718af47929049eb94ac` |
| 10 | `D1\|H-R-0\|rigid\|T\|diag-val\|K1\|V0\|e0.002` | `b8c84f2ed2d686a1404e44e844a6a920aaca9df77d4c88819716c1dfb362dbc4` |
| 11 | `D1\|H-R-0\|rigid\|T\|diag-val\|K1\|VB\|e0` | `4442cbf39584def39d666e986eedae63e23db063eb7d27e5e760213016b2a46f` |
| 12 | `D1\|H-R-0\|rigid\|T\|diag-val\|K1\|VB\|e0.002` | `9e3bb5ec28929b94953de53c0f1d9621fa5de265b98577c70252b6823ac8c2cd` |
| 13 | `D1\|H-R-0\|rigid\|T\|diag-val\|K3\|V0\|e0` | `a4795c1dbc5f595e4ce8cb2c4d36733b0727358179b021c8c905e3d57558b0cc` |
| 14 | `D1\|H-R-0\|rigid\|T\|diag-val\|K3\|V0\|e0.002` | `e61694ef8c98caac280cd4dd7527cbe85975cca9c820660339bfb2ab5b1c8cfa` |
| 15 | `D1\|H-R-0\|rigid\|T\|diag-val\|K3\|VB\|e0` | `d09ecd5e3902a82a2f76f3f0bc06f4a792e525c83b86e4cab36ab32cc8890abb` |
| 16 | `D1\|H-R-0\|rigid\|T\|diag-val\|K3\|VB\|e0.002` | `62092e69be92b9ca843e4f503f723f9154277e83bd212749f5a5882b32a48abd` |
| 17 | `D1\|H-R-0\|rigid\|T\|roll+op\|K1\|V0\|e0` | `76868d9a73bbab5df1b57d45d9f2b39debd5fdb1228d35cc5a0a9729a680c943` |
| 18 | `D1\|H-R-0\|rigid\|T\|roll+op\|K1\|V0\|e0.002` | `a1e1b5a0e3318d5a9118ccc2eec269ef54456683e1935a42d7e3cb746241b633` |
| 19 | `D1\|H-R-0\|rigid\|T\|roll+op\|K1\|VB\|e0` | `9bc9bc9dbf40461b6537eaa5d75193ff6ca5ebd88e200031db5343ab9285112d` |
| 20 | `D1\|H-R-0\|rigid\|T\|roll+op\|K1\|VB\|e0.002` | `95fa3f64e2272a84344a6f5fd73cdec8fdc3ba2513164b482dfc8040e4c19b6c` |
| 21 | `D1\|H-R-0\|rigid\|T\|roll+op\|K3\|V0\|e0` | `519fca0abe759c360e9f49514eb2ffdbec8c48d2d14a7d1c9a05bc37a062390c` |
| 22 | `D1\|H-R-0\|rigid\|T\|roll+op\|K3\|V0\|e0.002` | `7bce0cdbe132bad2433419cf3f3a8fe2d908925d643d49559adfbd2529bd23ec` |
| 23 | `D1\|H-R-0\|rigid\|T\|roll+op\|K3\|VB\|e0` | `ac2323e059b814cad6dd6db7ca68ace060fff76727a8afe2ee6975149a77c323` |
| 24 | `D1\|H-R-0\|rigid\|T\|roll+op\|K3\|VB\|e0.002` | `2fa92137b9ae2e9fe22e996c520d18821100a1c81fa7e1ff8b1f85f5f1d5cd7b` |
| 25 | `D1\|H-R-0\|rigid\|T\|roll+val\|K1\|V0\|e0` | `8f055ad8bc148edf15ab60287e166968a7659396c268d976c974e502acd065ee` |
| 26 | `D1\|H-R-0\|rigid\|T\|roll+val\|K1\|V0\|e0.002` | `734c12f878c9770670a66759b9361bbcdea394928ef4f147b4b3c1785b4af8a3` |
| 27 | `D1\|H-R-0\|rigid\|T\|roll+val\|K1\|VB\|e0` | `37bf35d552db9c870ec698f50de41f5d26e62d4eb245edd3f0bbc8ba2b1484bd` |
| 28 | `D1\|H-R-0\|rigid\|T\|roll+val\|K1\|VB\|e0.002` | `18ae05aa759186e07aaa5a28829bf2bcc61575372ac01224e4c1cbd6db1d043c` |
| 29 | `D1\|H-R-0\|rigid\|T\|roll+val\|K3\|V0\|e0` | `4091870ab120be3f62a973e7e1edda4f6c1cacd73436b20665467c4082f40ae5` |
| 30 | `D1\|H-R-0\|rigid\|T\|roll+val\|K3\|V0\|e0.002` | `a67d9380a497542da7439fe51e8e8d1ccd57ca28576802a43dc83e543e46c341` |
| 31 | `D1\|H-R-0\|rigid\|T\|roll+val\|K3\|VB\|e0` | `41bed8e8015db263f05dca5023cf529a92d94f2b39053182a4f4b1d101d9e751` |
| 32 | `D1\|H-R-0\|rigid\|T\|roll+val\|K3\|VB\|e0.002` | `a4d0b81e05682001bafbaf3419365ab87c465375063ea52049816d02b8af40f7` |
| 33 | `D1\|H-R-0\|rigid\|T\|roll-op\|K1\|V0\|e0` | `532c14c9b00f516b1184238545618c14d082d3b06e1fd6e2ad05443405edd0a6` |
| 34 | `D1\|H-R-0\|rigid\|T\|roll-op\|K1\|V0\|e0.002` | `c6d0f1eab61eec187b19874185efda1c41386095ddf2eb8abdc6e79ffb869fc7` |
| 35 | `D1\|H-R-0\|rigid\|T\|roll-op\|K1\|VB\|e0` | `52f16113ad6216abbadaaacc5ac9d7af011f8cf0f18a43eb85468d4dea08781c` |
| 36 | `D1\|H-R-0\|rigid\|T\|roll-op\|K1\|VB\|e0.002` | `ab9f16d042162bf2bd87152406437e088ee80672a8914f203f3fd0806e31d728` |
| 37 | `D1\|H-R-0\|rigid\|T\|roll-op\|K3\|V0\|e0` | `8878611ff810949f49e0a251dc6f9911db60d4a125521c7fdfd6405b2a67ce8b` |
| 38 | `D1\|H-R-0\|rigid\|T\|roll-op\|K3\|V0\|e0.002` | `2bc8bf3e6fd309c5c8fe609eed86fca4bdd57b24dcaa6cecb33bdf10f3771938` |
| 39 | `D1\|H-R-0\|rigid\|T\|roll-op\|K3\|VB\|e0` | `baa4cc92ac602072b31979995bbd4de9edbdf2e22597b9521fd792fe1073b1d3` |
| 40 | `D1\|H-R-0\|rigid\|T\|roll-op\|K3\|VB\|e0.002` | `ce82ee09346a7a823739367e443f22867ca072f91ce2490be608b7a1c7bc5144` |
| 41 | `D1\|H-R-0\|rigid\|T\|roll-val\|K1\|V0\|e0` | `88d3dc091454e17a47e343b9e00f71c4d175ac6ffd55cccc3ee5857b7888d3e5` |
| 42 | `D1\|H-R-0\|rigid\|T\|roll-val\|K1\|V0\|e0.002` | `e7aaeabd67c3629525332a08bb4341f055cbab64ad18d32a1486e8e800414000` |
| 43 | `D1\|H-R-0\|rigid\|T\|roll-val\|K1\|VB\|e0` | `79094041724e9a1d8a97dbd7405cd2eca98e66e72560bb821a92bb85001b0482` |
| 44 | `D1\|H-R-0\|rigid\|T\|roll-val\|K1\|VB\|e0.002` | `553a60f98ffdca4f8a980645f371ece24b8cbeb8a6d62ace6a0b8608cdca80bc` |
| 45 | `D1\|H-R-0\|rigid\|T\|roll-val\|K3\|V0\|e0` | `755325d7db60ceb8faa29dbd28aac3a8e259a38a9a7e6275b64629625885e083` |
| 46 | `D1\|H-R-0\|rigid\|T\|roll-val\|K3\|V0\|e0.002` | `d73481e0cce335de117844a5cb40d0a8d331be201f6e560bfc31c94a700b2cee` |
| 47 | `D1\|H-R-0\|rigid\|T\|roll-val\|K3\|VB\|e0` | `bd24300474542189a5e20656cee667d2ec04e528b951410e17b8c8b4ab4080db` |
| 48 | `D1\|H-R-0\|rigid\|T\|roll-val\|K3\|VB\|e0.002` | `a17f24e4a758b8125e0868f7c1fbcb8b38bc3d8d8fa0a3c0f04689842a91da48` |
| 49 | `D1\|H-R-A\|rigid+J1@FL\|B\|fdown-psa\|K1\|V0\|e0` | `afd71b793ae886a8bdbf78184d25d86c4ef5890a87026410dc4c792f33d235e4` |
| 50 | `D1\|H-R-A\|rigid+J1@FL\|B\|fdown-psa\|K1\|V0\|e0.002` | `65ac19e5de39fef5967a940341beec90789675035d93e65f3e9e9257a97454de` |
| 51 | `D1\|H-R-A\|rigid+J1@FL\|B\|fdown-psa\|K1\|VB\|e0` | `ebd48cc7bf946cf24982e62a127519ed9ad76c7c745c3a4fd05b09d09c922cea` |
| 52 | `D1\|H-R-A\|rigid+J1@FL\|B\|fdown-psa\|K1\|VB\|e0.002` | `e2fcb32ff9049092810003268853b4c9902e1bd13eeee7b94576c9aaf04c9c30` |
| 53 | `D1\|H-R-A\|rigid+J1@FL\|B\|fdown-psa\|K3\|V0\|e0` | `85dbe8573094a7d6a4b1dde530d39316e7a700cceee74aca47f74e7589142bc6` |
| 54 | `D1\|H-R-A\|rigid+J1@FL\|B\|fdown-psa\|K3\|V0\|e0.002` | `e45522b6b5982f55f93307a28167dfde07f753936652321bbfbdbcaf4392cf92` |
| 55 | `D1\|H-R-A\|rigid+J1@FL\|B\|fdown-psa\|K3\|VB\|e0` | `f1aaeeb224b276cf00d4b1e4be84a5d1dba9ebe06710adc1dd34f4a198578527` |
| 56 | `D1\|H-R-A\|rigid+J1@FL\|B\|fdown-psa\|K3\|VB\|e0.002` | `cee528e30bdb8415f0109d3ebc69ed1a74db63990e784d221191af1cd9942461` |
| 57 | `D1\|H-R-A\|rigid+J1@FL\|B\|flat\|K1\|V0\|e0` | `9831add06a6031568c42f78800a40b045c043799ba1dfde631f36ac27feab612` |
| 58 | `D1\|H-R-A\|rigid+J1@FL\|B\|flat\|K1\|V0\|e0.002` | `6351fcefc627ff0cb02067574fa815916a0d2db564bb8babda3fb05e461283f8` |
| 59 | `D1\|H-R-A\|rigid+J1@FL\|B\|flat\|K1\|VB\|e0` | `6063d584dad3e34969a5ff08794b4534ffd91b37f3b33de77d034178ab6d1bb6` |
| 60 | `D1\|H-R-A\|rigid+J1@FL\|B\|flat\|K1\|VB\|e0.002` | `2aa7e134ab885afefaca1b42b0f51497e6b8c0e8d45d28de2d618aa4be5d7aa4` |
| 61 | `D1\|H-R-A\|rigid+J1@FL\|B\|flat\|K3\|V0\|e0` | `ae9142f446fb40b8cd7d803dd010f9af7f501bfa76a784eb018e8a0c41dbccbf` |
| 62 | `D1\|H-R-A\|rigid+J1@FL\|B\|flat\|K3\|V0\|e0.002` | `4561b00d70abe1a965d5572853789bde49be727db36f220a909d2c4944cc1d68` |
| 63 | `D1\|H-R-A\|rigid+J1@FL\|B\|flat\|K3\|VB\|e0` | `cda554c3c7d6818500291a48d5dab83f6ee8f05011ccddb9503a88d5f9ba15ee` |
| 64 | `D1\|H-R-A\|rigid+J1@FL\|B\|flat\|K3\|VB\|e0.002` | `05c4c2f404ffda39ad20798c77df3690fe4071e5aae06796fe97e32d72791b14` |
| 65 | `D1\|H-R-A\|rigid+J1@FL\|M\|fdown-psa\|K1\|V0\|e0` | `6de7c0af15a6b4d4e356499354dbf5a11f53df9fbb394e245bd20c9dcc5550b2` |
| 66 | `D1\|H-R-A\|rigid+J1@FL\|M\|fdown-psa\|K1\|V0\|e0.002` | `f2ffd279f92fb900c4aad192ff64e8dd31aa9cdcdbfe0a07f836814274162092` |
| 67 | `D1\|H-R-A\|rigid+J1@FL\|M\|fdown-psa\|K1\|VB\|e0` | `9182bd975dff4589043efae51303a5c3b9acbbd6e9baed56396f7e8b7bea2e68` |
| 68 | `D1\|H-R-A\|rigid+J1@FL\|M\|fdown-psa\|K1\|VB\|e0.002` | `149e722501e7e6d8b8d51ac1d4793653184e0b67a5e20df46a5f489f785f0bd0` |
| 69 | `D1\|H-R-A\|rigid+J1@FL\|M\|fdown-psa\|K3\|V0\|e0` | `56c81a717a0c6f69504a5e3f5454083609f6eec039696cc19fb0a444d5ed06fb` |
| 70 | `D1\|H-R-A\|rigid+J1@FL\|M\|fdown-psa\|K3\|V0\|e0.002` | `808e8d7f61628fed1b30876569a125546c79a1f8a4b0a8776d4f4ce615c374ea` |
| 71 | `D1\|H-R-A\|rigid+J1@FL\|M\|fdown-psa\|K3\|VB\|e0` | `0494767154a5f3eb19abc42658e8598f78e0d4d9dd1eef1cda94ea580921eff2` |
| 72 | `D1\|H-R-A\|rigid+J1@FL\|M\|fdown-psa\|K3\|VB\|e0.002` | `3b79a096f80c2be5623461c05d859a62c3707ea92ad052a75c5ee373839d0a38` |
| 73 | `D1\|H-R-A\|rigid+J1@FL\|M\|flat\|K1\|V0\|e0` | `80fdd357864735164f6d509f2ee919dcf14d6017c881585cc3160a52ecf8b621` |
| 74 | `D1\|H-R-A\|rigid+J1@FL\|M\|flat\|K1\|V0\|e0.002` | `df82cb61676f1a63e958b32fb45c1c54b4c3cf9b636f4da27678109acfc10747` |
| 75 | `D1\|H-R-A\|rigid+J1@FL\|M\|flat\|K1\|VB\|e0` | `694df8f520ab7bea5becf16c92f3e0c49cb7ae167a29ea62600e04a63c0f47c9` |
| 76 | `D1\|H-R-A\|rigid+J1@FL\|M\|flat\|K1\|VB\|e0.002` | `5da1600bc0717f149c78be30504b2723e07b9cd4dd234bdda8f064c4c1ab2278` |
| 77 | `D1\|H-R-A\|rigid+J1@FL\|M\|flat\|K3\|V0\|e0` | `ee42fcca328228f7887c6e8ce3458074158106484ef8a13458169dc594b6f772` |
| 78 | `D1\|H-R-A\|rigid+J1@FL\|M\|flat\|K3\|V0\|e0.002` | `3b6264515a1bdd10aa58606929d5391c2cf5b0da2ed3be52f0d9e9b7af8ffc4e` |
| 79 | `D1\|H-R-A\|rigid+J1@FL\|M\|flat\|K3\|VB\|e0` | `5119cdcba2e6bd72a479106334ef1f39b2522d1edb7a0712956b283a2d4cbfd4` |
| 80 | `D1\|H-R-A\|rigid+J1@FL\|M\|flat\|K3\|VB\|e0.002` | `eddd8dda503fdd005b4fde2f030c4417fd3e9b21a7d4b599563df2f722599782` |
| 81 | `D1\|H-R-A\|rigid+J1@FL\|T\|fdown-psa\|K1\|V0\|e0` | `eefceb4b1b4e0d2cb926adf4cad0367207458ab1c416231d00ad16cb7b3d7fe1` |
| 82 | `D1\|H-R-A\|rigid+J1@FL\|T\|fdown-psa\|K1\|V0\|e0.002` | `bc3a17d972d25aa7b013a284b586294dcec50867645819ff5f5214899137041f` |
| 83 | `D1\|H-R-A\|rigid+J1@FL\|T\|fdown-psa\|K1\|VB\|e0` | `689e2f704c0a57a35aacc114025066a0588427bf330378605526dd1ffeea6a2c` |
| 84 | `D1\|H-R-A\|rigid+J1@FL\|T\|fdown-psa\|K1\|VB\|e0.002` | `f3ff565a8da0543ce3469138749b1bc867cc57aca8071378c423838a6c686bd5` |
| 85 | `D1\|H-R-A\|rigid+J1@FL\|T\|fdown-psa\|K3\|V0\|e0` | `051a9782c31a08460153ce24fcf17d5ca265dff6d3ea0188355aaa57f306eea4` |
| 86 | `D1\|H-R-A\|rigid+J1@FL\|T\|fdown-psa\|K3\|V0\|e0.002` | `8f27408f50f6352be4047145e7b786c30e7dffcc0e6dae28d377a66a0d37da62` |
| 87 | `D1\|H-R-A\|rigid+J1@FL\|T\|fdown-psa\|K3\|VB\|e0` | `3cdf321479ce304ddb17a578aae53ac18e9c5cfab827ecb4ead56aa430ba3fb4` |
| 88 | `D1\|H-R-A\|rigid+J1@FL\|T\|fdown-psa\|K3\|VB\|e0.002` | `c9e9e2836dec309ff6742afb6efa991c6704c73b12b53cb45f282d8eeb666c52` |
| 89 | `D1\|H-R-A\|rigid+J1@FL\|T\|flat\|K1\|V0\|e0` | `37a948417a506af486db5d25119ca2450a727c30ee7f591a6472c4d7f34e760f` |
| 90 | `D1\|H-R-A\|rigid+J1@FL\|T\|flat\|K1\|V0\|e0.002` | `7405a0f87b80bc93b8f938666965b5254e16cd99b5de6116791eeee221520105` |
| 91 | `D1\|H-R-A\|rigid+J1@FL\|T\|flat\|K1\|VB\|e0` | `10ce717d7194a767497a2ef36dbe44ce10d0984365319af7b93da8eca8fb2d6b` |
| 92 | `D1\|H-R-A\|rigid+J1@FL\|T\|flat\|K1\|VB\|e0.002` | `5eb8a104a9468a6c742b116e262c811a6f82145ce3452dd927ed9e5cdfeb0500` |
| 93 | `D1\|H-R-A\|rigid+J1@FL\|T\|flat\|K3\|V0\|e0` | `d35675e4989933d7596ca0bda88d88ef7e02b900ba5756fcfe4d964e21d07407` |
| 94 | `D1\|H-R-A\|rigid+J1@FL\|T\|flat\|K3\|V0\|e0.002` | `cd2e089bad608dce536908879dec9869cd9f74ae5222e0932823c3e73e4f0742` |
| 95 | `D1\|H-R-A\|rigid+J1@FL\|T\|flat\|K3\|VB\|e0` | `48725e7dbd50cb960a0be927c9b6baf996acca9469818f64276044bad27a6878` |
| 96 | `D1\|H-R-A\|rigid+J1@FL\|T\|flat\|K3\|VB\|e0.002` | `7014daadb65e658f5a969b3ac0fce9fa917dacfc0152aca058c56f7bed2fa12c` |
| 97 | `D1\|H-R-A\|rigid+J1@FR\|B\|diag-op\|K1\|V0\|e0` | `1874301979b552f4352ab65d1e33b8adb4408b39586e166713275c426870f54f` |
| 98 | `D1\|H-R-A\|rigid+J1@FR\|B\|diag-op\|K1\|V0\|e0.002` | `7ea2eaa37948b8a887b63fae3cb1d4459d596c191eded0d76633e4462c5d89a4` |
| 99 | `D1\|H-R-A\|rigid+J1@FR\|B\|diag-op\|K1\|VB\|e0` | `48b91f564e11525bcee0c57ab924b7893b5436112a30ac470fe5dc154b8d7323` |
| 100 | `D1\|H-R-A\|rigid+J1@FR\|B\|diag-op\|K1\|VB\|e0.002` | `ce61d752e0483aa9695c030c0fb32f51b10fd0670b6214b1e7f47e6bc221124d` |
| 101 | `D1\|H-R-A\|rigid+J1@FR\|B\|diag-op\|K3\|V0\|e0` | `485496983fd2fbab11f47e753ab2633d949ceeee3658595537b5dee35ada67db` |
| 102 | `D1\|H-R-A\|rigid+J1@FR\|B\|diag-op\|K3\|V0\|e0.002` | `3d91ca95b85236dcb9cbcb6d0475d3c5b8253e69cb5f6a445af06e0241b07681` |
| 103 | `D1\|H-R-A\|rigid+J1@FR\|B\|diag-op\|K3\|VB\|e0` | `a229886970bdd9e65d2f909e6a16d895653e482e5b3b4c1e0ab316d57dd197df` |
| 104 | `D1\|H-R-A\|rigid+J1@FR\|B\|diag-op\|K3\|VB\|e0.002` | `e686b31a4537cb277549686ca959e0ab77c33885e526215786d467e6f86998e4` |
| 105 | `D1\|H-R-A\|rigid+J1@FR\|M\|diag-op\|K1\|V0\|e0` | `433d0af7a12a05c08a4afe98ed74ccb4f0763c11905fae1f4d2d4de12306a128` |
| 106 | `D1\|H-R-A\|rigid+J1@FR\|M\|diag-op\|K1\|V0\|e0.002` | `cc5208968d90d77e95b287de6bd87f989d9efb277a0a6fb40905b3faa220514a` |
| 107 | `D1\|H-R-A\|rigid+J1@FR\|M\|diag-op\|K1\|VB\|e0` | `b83f56e53d7c7fce591f9b47eb952a435a7e4f9b6e369703c0ff57677e85096d` |
| 108 | `D1\|H-R-A\|rigid+J1@FR\|M\|diag-op\|K1\|VB\|e0.002` | `daf5d80f98d31c4fe8a5f068ca50e96b1d105a2cc44a855cd7af888fa8addc89` |
| 109 | `D1\|H-R-A\|rigid+J1@FR\|M\|diag-op\|K3\|V0\|e0` | `ce3a9bef5e64a0fc15b77e867bd6f1ed969c4acd0e7b366ece39371035a0c489` |
| 110 | `D1\|H-R-A\|rigid+J1@FR\|M\|diag-op\|K3\|V0\|e0.002` | `d2c49d3deb1312d284aac93674db2252555ff48d32e23d9e8cdd35eb9b43896c` |
| 111 | `D1\|H-R-A\|rigid+J1@FR\|M\|diag-op\|K3\|VB\|e0` | `eb9bec90796a8a7e67ca2f75a23d1b5b96540f94b73579273d9645999b86627f` |
| 112 | `D1\|H-R-A\|rigid+J1@FR\|M\|diag-op\|K3\|VB\|e0.002` | `8e55c88d2643eb2cc883302b91f7d70639c81f717238295857db2e7921bce4bb` |
| 113 | `D1\|H-R-A\|rigid+J1@FR\|T\|diag-op\|K1\|V0\|e0` | `f857cf9e4edc4373fd5e197d8c4e4219810990f22c8295b0016de937cae124ab` |
| 114 | `D1\|H-R-A\|rigid+J1@FR\|T\|diag-op\|K1\|V0\|e0.002` | `89c9ba21363bde6cb3b1d756fdd434b641d6983215854a86f3a305aac0be13a1` |
| 115 | `D1\|H-R-A\|rigid+J1@FR\|T\|diag-op\|K1\|VB\|e0` | `a6189f0db3a96a503a9e4129b10eb66443011d4585a72934344a3e25a08fbd23` |
| 116 | `D1\|H-R-A\|rigid+J1@FR\|T\|diag-op\|K1\|VB\|e0.002` | `f29cd1692ae48713ac6db25fef577551031d93818587ccea58e974326c12c67a` |
| 117 | `D1\|H-R-A\|rigid+J1@FR\|T\|diag-op\|K3\|V0\|e0` | `08e7f53dab21d5e4d497c5bfa3b0c941aed9f4c44d3881a2582fc3f3f185491b` |
| 118 | `D1\|H-R-A\|rigid+J1@FR\|T\|diag-op\|K3\|V0\|e0.002` | `12534460248222b2e42df0fa3d8cfe16a21c368bfb595516e0c20e2944641026` |
| 119 | `D1\|H-R-A\|rigid+J1@FR\|T\|diag-op\|K3\|VB\|e0` | `78a8961f8cf441ac72cecf7b43d823384fb6fc0bbd66dc9cd490fee8eefa3533` |
| 120 | `D1\|H-R-A\|rigid+J1@FR\|T\|diag-op\|K3\|VB\|e0.002` | `20d659ea9f1afbdc8d0aff38e67da92c7a0fe6aeb7e68bad97c50034bc2c8e1c` |
| 121 | `D1\|H-R-A\|rigid+J1@RL\|B\|flat\|K1\|V0\|e0` | `8f00cbdea26805a92dde47c4bcb2b2bb83ac801e050e8393c8365d15772badfe` |
| 122 | `D1\|H-R-A\|rigid+J1@RL\|B\|flat\|K1\|V0\|e0.002` | `e40e4e3ccbf5ef3307f503fbdd431e83b5aa0f678ef2bc1cca882c84c6a6ae65` |
| 123 | `D1\|H-R-A\|rigid+J1@RL\|B\|flat\|K1\|VB\|e0` | `46c3fbab9aba02da1ae89ef72d226076eb962f25d36a2cb083b4bca183ed3f47` |
| 124 | `D1\|H-R-A\|rigid+J1@RL\|B\|flat\|K1\|VB\|e0.002` | `558ca763c53fdc0894be9d7474c458a7a4bcfa7c1e3d9fb1d432fdbd7f0c7959` |
| 125 | `D1\|H-R-A\|rigid+J1@RL\|B\|flat\|K3\|V0\|e0` | `36e7f3519748334fba4c839f0ac6e2b9902964aa11785e8b17855d19cd63edd2` |
| 126 | `D1\|H-R-A\|rigid+J1@RL\|B\|flat\|K3\|V0\|e0.002` | `2ef719f5d5e6c9e276777abe314f759246e6bdea9ef3c4b5eb7b8f99bd131673` |
| 127 | `D1\|H-R-A\|rigid+J1@RL\|B\|flat\|K3\|VB\|e0` | `4e0aac14008a0374899d83c325824f2622aed2b3ffc9c2d960c4f656404ca9ba` |
| 128 | `D1\|H-R-A\|rigid+J1@RL\|B\|flat\|K3\|VB\|e0.002` | `72fca45469034279190829aea7610d250ec5e49e5f627845e4b26885f6b0ee9f` |
| 129 | `D1\|H-R-A\|rigid+J1@RL\|B\|fup-psa\|K1\|V0\|e0` | `9db07abe5ce0ff8aa96e55c198c4f5bf544a45635b5e391dd17f6747005fabb9` |
| 130 | `D1\|H-R-A\|rigid+J1@RL\|B\|fup-psa\|K1\|V0\|e0.002` | `af6cf1fb94a2f55c77b81a1bbb854f930b208a4523de6b9b972172e5990ac31c` |
| 131 | `D1\|H-R-A\|rigid+J1@RL\|B\|fup-psa\|K1\|VB\|e0` | `251cf0e9b65f1aa6b109f2bb1784904eb6636f43cc769ad52eec8e02954c8e7f` |
| 132 | `D1\|H-R-A\|rigid+J1@RL\|B\|fup-psa\|K1\|VB\|e0.002` | `d6b958c29a9b922283be9e70eb549c75796ebcdff007da42d0bad0f52f7fe1a1` |
| 133 | `D1\|H-R-A\|rigid+J1@RL\|B\|fup-psa\|K3\|V0\|e0` | `7d7e58863405855702efd96ed655d212e87d7567fcbafc9e96757ae6c359d417` |
| 134 | `D1\|H-R-A\|rigid+J1@RL\|B\|fup-psa\|K3\|V0\|e0.002` | `16931e4e3c2e53f4f4f3a077a600ac04af2e703b4c6d39bd05e23064f9f410fc` |
| 135 | `D1\|H-R-A\|rigid+J1@RL\|B\|fup-psa\|K3\|VB\|e0` | `c0747289145d992336a7309c117b15ae7cd2ead9f49dc908a33d627ec7785eaa` |
| 136 | `D1\|H-R-A\|rigid+J1@RL\|B\|fup-psa\|K3\|VB\|e0.002` | `5d886667e5ebb4dd4898ece71930453315f9b01d3a54634d2fd8baaa208c062c` |
| 137 | `D1\|H-R-A\|rigid+J1@RL\|B\|roll-op\|K1\|V0\|e0` | `c5b1438f0c64238cc29afe8f8a90de5fc9e092f2888dddf0621da9671e806662` |
| 138 | `D1\|H-R-A\|rigid+J1@RL\|B\|roll-op\|K1\|V0\|e0.002` | `dc966c7dd7f87508ae38962c572af4b9c38ea912af31ba81fb94c3ac61517dd8` |
| 139 | `D1\|H-R-A\|rigid+J1@RL\|B\|roll-op\|K1\|VB\|e0` | `eb73dbcd051a9eff3a053c99db3e48ec205e5655f0521047cecec500f5d601ba` |
| 140 | `D1\|H-R-A\|rigid+J1@RL\|B\|roll-op\|K1\|VB\|e0.002` | `97c907436d8732220404969323c82aa87606fa1c6017270eb1afc842f0d721f8` |
| 141 | `D1\|H-R-A\|rigid+J1@RL\|B\|roll-op\|K3\|V0\|e0` | `10905be1644262da9c732123fbdcaff54b318ae59bdf365e006d9469ad393e34` |
| 142 | `D1\|H-R-A\|rigid+J1@RL\|B\|roll-op\|K3\|V0\|e0.002` | `0dafa3c95ec3fede264a2bc7ec089f13ca570ed9c5d19c32a8889136dd843c70` |
| 143 | `D1\|H-R-A\|rigid+J1@RL\|B\|roll-op\|K3\|VB\|e0` | `38581dcf48c1c31f2d3e28d0b12bf14a49e6de6343452f6745404f6cedfece78` |
| 144 | `D1\|H-R-A\|rigid+J1@RL\|B\|roll-op\|K3\|VB\|e0.002` | `24098592cf1a54f797a477049314a0a74d149aa84590982643acc4226c3f323d` |
| 145 | `D1\|H-R-A\|rigid+J1@RL\|M\|flat\|K1\|V0\|e0` | `3c291fab29592e7a6b2c660a5d6071171dd4f9398107c4084086dc2892315f19` |
| 146 | `D1\|H-R-A\|rigid+J1@RL\|M\|flat\|K1\|V0\|e0.002` | `1d2dd7c61b669c1a2859a6dfa95ff0e9836a5466055580d4d727e3f7bebbd35c` |
| 147 | `D1\|H-R-A\|rigid+J1@RL\|M\|flat\|K1\|VB\|e0` | `31c668000ad4c673d65e416e01207b908e6af83b16eb3f52fa4ba39013f605fc` |
| 148 | `D1\|H-R-A\|rigid+J1@RL\|M\|flat\|K1\|VB\|e0.002` | `de83502378932c625f4a8bf6240e8b96d71ab12e54b19564f7aaf63c60403ddb` |
| 149 | `D1\|H-R-A\|rigid+J1@RL\|M\|flat\|K3\|V0\|e0` | `8d91244003880195e55a379c19debfc8c52b88c6cb32429dc2b3d01cd88b9357` |
| 150 | `D1\|H-R-A\|rigid+J1@RL\|M\|flat\|K3\|V0\|e0.002` | `bc18b800d15a920c357700f987f68ebca569457bf176681dd4a95a13f0d7e2a4` |
| 151 | `D1\|H-R-A\|rigid+J1@RL\|M\|flat\|K3\|VB\|e0` | `eaa7e3eb51be1b3fe86e9d3b62345df1b34c374dfad0f9b867987da570c60518` |
| 152 | `D1\|H-R-A\|rigid+J1@RL\|M\|flat\|K3\|VB\|e0.002` | `95cd86e31210eb8c107491d95c36ddadd5b5e4702f9f62f5ab16685e501b9c32` |
| 153 | `D1\|H-R-A\|rigid+J1@RL\|M\|fup-psa\|K1\|V0\|e0` | `64aa70b65766dc96c5138b9c7deb3de9c7c45756a3a9fd06a3a5e662e73c805e` |
| 154 | `D1\|H-R-A\|rigid+J1@RL\|M\|fup-psa\|K1\|V0\|e0.002` | `daf933d7ddc15dde00d32118ec3c732ff3d89269b5df02d9523d234deb1c58ea` |
| 155 | `D1\|H-R-A\|rigid+J1@RL\|M\|fup-psa\|K1\|VB\|e0` | `7efe997eb89e0ea58e8e0ea2b64256a45c516ed7f34176058a1adc2e6881dd1e` |
| 156 | `D1\|H-R-A\|rigid+J1@RL\|M\|fup-psa\|K1\|VB\|e0.002` | `af4bd25acd0c30a31c38a1ffaf998be78328d36546a43c78fbeaf6889ff50088` |
| 157 | `D1\|H-R-A\|rigid+J1@RL\|M\|fup-psa\|K3\|V0\|e0` | `5367bd3c5f40a0e4a2973da57388ce62a4c5188ef8c165d8cacb860ea349e35d` |
| 158 | `D1\|H-R-A\|rigid+J1@RL\|M\|fup-psa\|K3\|V0\|e0.002` | `1fbaadb8c7276211f7e9bf87b55764414ffb2d24636a6a8d8fa79588c3aabbaa` |
| 159 | `D1\|H-R-A\|rigid+J1@RL\|M\|fup-psa\|K3\|VB\|e0` | `dc599cb6e4d7a57ed247d70633dff9ac607fb1f38bf5320a618ffd0049c8dbc8` |
| 160 | `D1\|H-R-A\|rigid+J1@RL\|M\|fup-psa\|K3\|VB\|e0.002` | `1412c910df9dc578f4e49bf27d1e73ded23c6de7b0d9c7b2560c2c75a68cd3ac` |
| 161 | `D1\|H-R-A\|rigid+J1@RL\|M\|roll-op\|K1\|V0\|e0` | `a8eee1114094511557156898e980947a912c4d614b12c705d22bd4baebe97773` |
| 162 | `D1\|H-R-A\|rigid+J1@RL\|M\|roll-op\|K1\|V0\|e0.002` | `0e872cfdbffe1edda87b53288f5d6f1d4557c30f2e19f228fb86f5ba4ad309c5` |
| 163 | `D1\|H-R-A\|rigid+J1@RL\|M\|roll-op\|K1\|VB\|e0` | `c3ee9aebd06ec84b7fb20948e5c91444b1ff5e3c53890c90164e1ba2e194c76f` |
| 164 | `D1\|H-R-A\|rigid+J1@RL\|M\|roll-op\|K1\|VB\|e0.002` | `6931a1e9541bb4567174fcb0505a3da5f2d546ef66cdb1315c7c520fdf6cdbfd` |
| 165 | `D1\|H-R-A\|rigid+J1@RL\|M\|roll-op\|K3\|V0\|e0` | `c52503d43793ea3901a086511625ab2c5368b76a9ba2586b34976e50ab0d73c1` |
| 166 | `D1\|H-R-A\|rigid+J1@RL\|M\|roll-op\|K3\|V0\|e0.002` | `23fbe36c903a4398fd91ceaf525e4e80c209be3864a421ce0569b8b6d1ded858` |
| 167 | `D1\|H-R-A\|rigid+J1@RL\|M\|roll-op\|K3\|VB\|e0` | `c16fa955d7dde46c4d900e7787ad72230ea4816e3cb98b8cbf9916334bba952c` |
| 168 | `D1\|H-R-A\|rigid+J1@RL\|M\|roll-op\|K3\|VB\|e0.002` | `59872668ff8f2a7e485c57e3aaa47dcb049cc015d0c7991fa8881569633f895e` |
| 169 | `D1\|H-R-A\|rigid+J1@RL\|T\|flat\|K1\|V0\|e0` | `3ec1dbcd2389379be1d055c8a2e57a6d11bd00783f46e535cc3a7761d507d199` |
| 170 | `D1\|H-R-A\|rigid+J1@RL\|T\|flat\|K1\|V0\|e0.002` | `9b2310eee5b44fde69cc400e0f8b4022cd47b0ab36b9b972fa51637073e5bcda` |
| 171 | `D1\|H-R-A\|rigid+J1@RL\|T\|flat\|K1\|VB\|e0` | `4791f9ed540caa42a8efcd51f642de33cd44b459a999bbcdd8da9992ae69dae4` |
| 172 | `D1\|H-R-A\|rigid+J1@RL\|T\|flat\|K1\|VB\|e0.002` | `9ca79b432495c9e7fa1c209256c52d40edb2866b497895288946947140553f8c` |
| 173 | `D1\|H-R-A\|rigid+J1@RL\|T\|flat\|K3\|V0\|e0` | `1abf40891d1ac71bcc07f15f85d34bd35b9eef4d9542e0d16a440772df50619d` |
| 174 | `D1\|H-R-A\|rigid+J1@RL\|T\|flat\|K3\|V0\|e0.002` | `6d93b7ccdb5ae271dbdb0aec115ff5cdc5f86411ff3ce3b5302cff736eec08b8` |
| 175 | `D1\|H-R-A\|rigid+J1@RL\|T\|flat\|K3\|VB\|e0` | `33d71d535614a419047c92b23bfae038b5051859d03af8205f872012aaf61d3d` |
| 176 | `D1\|H-R-A\|rigid+J1@RL\|T\|flat\|K3\|VB\|e0.002` | `4ae822108415de7ffe1e1f5edb61d66b05582645cc6b475d1583d51492db74f5` |
| 177 | `D1\|H-R-A\|rigid+J1@RL\|T\|fup-psa\|K1\|V0\|e0` | `6228dc6a4fbaa04fc5b934619bbadadb92a338452e39ab2da98bad28acc01955` |
| 178 | `D1\|H-R-A\|rigid+J1@RL\|T\|fup-psa\|K1\|V0\|e0.002` | `8d41b76b93999a8022dfc02b808401cdfb8596ef05c91e5031253fafc47714d7` |
| 179 | `D1\|H-R-A\|rigid+J1@RL\|T\|fup-psa\|K1\|VB\|e0` | `bc6336aafa4c32d0d1e71badfefdb66d436d704fe4e7df37be9084bd03e8f1e2` |
| 180 | `D1\|H-R-A\|rigid+J1@RL\|T\|fup-psa\|K1\|VB\|e0.002` | `d72bb232f8d466fe0424d3041e346021f64f72f50a82f07a6b94cf3327bba80c` |
| 181 | `D1\|H-R-A\|rigid+J1@RL\|T\|fup-psa\|K3\|V0\|e0` | `dd2c41264de388c3ee2cf760277b29217ad01356872c7432d9b4609ea9cd94e0` |
| 182 | `D1\|H-R-A\|rigid+J1@RL\|T\|fup-psa\|K3\|V0\|e0.002` | `c0be3623d8251c627b7aefa948b883195d512e50f9c472578facaf72833313d9` |
| 183 | `D1\|H-R-A\|rigid+J1@RL\|T\|fup-psa\|K3\|VB\|e0` | `56332905f2cfe608a21b5ad04f1c30b3dc1613facc8e8534c0b36dc48cb53b2f` |
| 184 | `D1\|H-R-A\|rigid+J1@RL\|T\|fup-psa\|K3\|VB\|e0.002` | `4756840a408e766dece1caf451f62fda9ba27a7fbd6cfabf2d00eb472329d671` |
| 185 | `D1\|H-R-A\|rigid+J1@RL\|T\|roll-op\|K1\|V0\|e0` | `a57a5b63000501505e06dd5680edbe988fcd94b382728f3b9c5eafd01abe967f` |
| 186 | `D1\|H-R-A\|rigid+J1@RL\|T\|roll-op\|K1\|V0\|e0.002` | `2783108feec3c4981159fa5f7272d3511b2700734255c4f02db766325f4fa54b` |
| 187 | `D1\|H-R-A\|rigid+J1@RL\|T\|roll-op\|K1\|VB\|e0` | `601d0398f90328d542d6a9f25a32dcbdcee15d70effffc59717b0f915deda612` |
| 188 | `D1\|H-R-A\|rigid+J1@RL\|T\|roll-op\|K1\|VB\|e0.002` | `f6f420b85178fec1d7851d2d878b3dd34fed29c39c9d7fbbb9e5d80f6923cda3` |
| 189 | `D1\|H-R-A\|rigid+J1@RL\|T\|roll-op\|K3\|V0\|e0` | `c12378ea03cefd0791e568376340724d95ece9299c8030ea6b35842044402252` |
| 190 | `D1\|H-R-A\|rigid+J1@RL\|T\|roll-op\|K3\|V0\|e0.002` | `9ea511fa96a6e9cd76c3cdd1df732c43f86077aae247b90f03b4fd9f326e757a` |
| 191 | `D1\|H-R-A\|rigid+J1@RL\|T\|roll-op\|K3\|VB\|e0` | `6789d8d6951d70eef93b806550d297389f40f66f937e709b86fa6808ea93ca6e` |
| 192 | `D1\|H-R-A\|rigid+J1@RL\|T\|roll-op\|K3\|VB\|e0.002` | `de8f2d02f90ae698bd79fe1697d1b4768a6103a8705510bd4e4955af1f012e57` |
