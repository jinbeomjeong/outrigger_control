# LAS-b P5r4 + K1 재판정 규칙 (새 원판)

- 작성: control-expert, 2026-11-10. 기준 master `b53d890`(K1 전환 병합). 봉인 전 정리: control-expert, 2026-11-11, 기준 master `da5e01b`(K-2 경로 2 병합 뒤, K-2 판정서는 main에서 미커밋).
- 상태: **새 원판.** 봉인 값(LF 줄 끝, BOM 없음으로 계산한 sha256)과 봉인 시각은 같은 폴더 `las_p5r4_k1_rules.sha256`에 둔다. **`.sha256`이 없거나 값이 다르면 이 파일은 봉인 전이며 실행·판정에 쓰지 않는다**(8.2 S-1). 봉인 뒤에는 고치지 않는다. 바꿀 일이 생기면 덧붙임 판 `las_p5r4_k1_rules_rev<n>.md`로 봉인하고, 결과를 보기 전인지 본 뒤인지를 첫머리에 적는다.
- 봉인 전 조건: `.gitattributes`에 `06_analysis/02_control/verif_matrix/las_p5r4_k1_rules* -text`와 `06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/*.jsonl -text`가 있어야 한다(`las_k1_rules*` 줄은 이 이름을 덮지 않는다).
- 이 판의 이력: 초안 `las_p5r4_k1_rules_draft.md`(커밋 `4df3d9b`)에 사용자 답(15절)과 재감사 `las_k1_adopt_rev1_d8x_rev3_audit.md`의 F-5·F-6·F-7을 반영했다(봉인 후보판, 커밋 `06d8e2d`). 봉인 전 정리(2026-11-11)에서 K-2 미채택(2절 끝)과 K-2 재발 방지 7항(16절)을 넣었다. 대상 행 수·판정 항목·문턱은 후보판과 같다. 초안 작성부터 이 판까지 이 규칙의 대상 행은 0행 실행됐다.
- 판의 성격: **새 원판**이다. A안 규칙(`las_revA_targeted_rules*`)의 rev가 아니다. 이유는 0.1절.
- 사용자 결정
  - 2026-11-09: "LAS-b P5r4는 K1 채택 뒤 P5r4+K1을 다시 판정한다(새 봉인 규칙 + Chrono)."
  - 2026-11-10: 판정 묶음은 **새 `_K1` 태그로 재실행**한다. `pre_k1_preset_runner.py`는 옛 결과 재현에만 쓴다.
  - 2026-11-10(초안 15절 답, 모두 추천안 A): Z-C 912줄, Chrono 12행, C-S 모든 짝 1 mm, G-2′C 절대 11.414589 kN, 하네스 `통과` 뒤 Chrono, D8x Chrono 먼저, C3·C4 180 s(BT-C는 앞 120 s), 조건부 PAIR_DIVERGE. 기록은 15절.
  - 2026-11-11: K-2 `_TCL`은 판정 불가로 끝나 채택하지 않았다(판정서 `06_analysis/02_control/k2/judgement/k2_judgement.md` 7절 D-1). v5 제어기는 현행 `final_C4G2_LAS_K1`로 확정했다. "P5r4+K1 먼저, 나머지는 순서대로." K-2 판정 후 감사(`k2/judgement/k2_post_audit.md` "kt × L1eq 충돌" 절)와 판정서 7.1절의 재발 방지 항목을 이 규칙에 넣는다(16절).
- 이어받는 규칙(바꾸지 않는다. 이 판과 다르면 이 판이 맞다)

| 파일 | sha256 | 이어받는 것 |
|---|---|---|
| `las_rev_targeted_rules.md` | `bb235f27567240b205a544ed7cfd10237827e4627088e0eab1f62b318416ff60` | 5.0 None 규칙, 5.2 C-2형·C-1·C-F·C-S·A-3·R-1·R-2·$\mathcal{P}$, 5.3, 6 C-4 예외, 4.2 DONE 기록 |
| `las_rev_targeted_rules_rev1.md` | `672bc8f81ba75419e5a201e05a94e2f9aead2de3c205f80c2661e7474cd9fd51` | 그대로 |
| `las_revA_targeted_rules.md` | `b09d004bb2f641db40cdd139a6fb2b1645651e4a3e45a9b16e81a5c938d5778f` | P5r4 정의(1.2·1.3), K-A1~K-A8, R1-1~R1-4, 6 램프 끝 조건 |
| `las_revA_targeted_rules_rev1.md` | `c02518021c00b69a9d02ec6bceddbea18b9686ef6de96bafe5e55b716b023960` | 그대로 |
| `las_revA_targeted_rules_rev2.md` | `9f478b7fbc5aa0bd8859716b056bf2d531ac02057dc36d218bada7d7f13e4565` | G-2′(11.414589 kN), R-0A·R-Q 정의 |
| `las_revA_targeted_rules_rev3.md` | `98082a368da626f90ce3b0a41f5c74145b4095c155f14b2b2f63eb319352d709` | Q-2 무리 정의(기록용) |
| `las_k1_rules.md` | `2742c9760ad55a87eccbf73e84025aafe0171a3555e1f54ab19fab24d888e4a0` | K1 정의 1.1·1.2, 4.3 C-2형·P3·C-S·C-F |
| `las_k1_rules_rev1.md` | `eeee4ab9661babff50117b8ff579aa41e27a98d083f1fc13f46fb5c733e0b4d3` | R1-1 P3 짝 정의, R1-2 C-2형 = `pair_violations` 정의 |
| `las_k1_rules_adopt.md` | `864836d852b4a783a577f01f738536b7c30c574bf4bebb3b0219e68e59b07ea8` | 9.2 원칙(봉인 판정 도구 상수 불변) |
| `las_k1_rules_adopt2.md` | `fb3a5696f24385e81acc9c564500b5e5a0547db45a5335272e7d18400f1e68e8` | decision 표·$L_1$·`POS`/`NONPOS`/`LATE_STRUCT`/`NO_R4`, K-0~K-10 꼴, 7 결측 |

- 규약
  - 제어: 이산 $T_s$ = 0.1 s(10 Hz), 출력 지연 $d$ = 1(주기 $k$의 명령은 $t_k+0.1$ s에 플랜트에 들어감), C2 음되먹임. $u$ = 다리 행정 속도 명령 [m/s]. 상태 되먹임 부호는 바꾸지 않는다.
  - 다리 순서 FL, FR, RL, RR(0~3). 힘은 실린더 순 힘 [N](표는 kN). $F_{min}$ = 9,414.589 N. 행정은 모터 행정 [m](표는 mm).
  - 시각 비교는 정수 주기 $n=\mathrm{round}(t/0.1)$(Python 내장)로 한다. Chrono 시각은 8 s 정착을 포함한 절대 시각이다.
  - **이름 주의**: 이 규칙의 "K1"은 R4c30 순서 관문(`slope_clearance_margin.flat_soil_margin_order_gate`)이다. 하네스 키 토큰 `K1`·`K3`(크롤러 강성 ×1·×3)과 다르다. Chrono 크롤러 강성 변형은 이 규칙에서 **Kc1·Kc3**로 적는다.
  - **이름 주의 2**: 9절 정체성 검사 `K-2`(코드 sha)는 터치 단계 크리프 래치 후보 K-2 `_TCL`(미채택)과 무관하다. 이 규칙에서 후보 K-2를 가리킬 때는 항상 "K-2 `_TCL`"로 적는다.

| 기호 | 뜻 | 단위 |
|---|---|---|
| P0 | LAS-b b0(β 3.5, $n_{min}$ 0, $N_r$ 0) = 채택 프리셋 | — |
| P5r4 | β 4.5, $n_{min}$ 0, $N_r$ 4(A안 1.2·1.3) | — |
| ref / cand | 짝의 기준(P0+K1) / 후보(P5r4+K1) | — |
| $F_{RL}$, $F_{judged,min}$ | 하네스 `diag.summary.F_RL_kN`, `F_judged_min_kN` | kN |
| $F^{C}_{after}$, $F^{C}_{tr}$ | Chrono `p3b.P3-3_leg_force.F_min_after_N`, `F_min_transient_N`(1 ms 참 $F_{cyl}$, 크롤러 이탈 뒤) | N |
| $s_{max}$ | 하네스 `d1.stroke_max_m`, Chrono `p3b.P3-5_clearance_stroke.s_motor_max_m` | m |
| $L_1$, dP | adopt2 기호 그대로(첫 R4 평가 LOC, $n_P-n_S$) | —, 주기 |
| $\lambda_0$ | 램프 시작 축척(A안 1.1) | — |

## 0. 목적과 판의 성격

### 0.1 새 원판으로 하는 이유

1. 짝의 기준이 바뀐다. A안 rev2의 기준 L은 **저장된 b0 줄(K1 꺼짐, 옛 태그)**이었다. 이 규칙의 기준은 **새 프리셋(P0+K1)으로 다시 돈 줄**이다(사용자 결정 11-10). 대상 집합·정체성 검사·도구가 모두 다르다.
2. Chrono 묶음이 새로 들어간다. A안 규칙에는 Chrono가 없었다(A안 10절 한계).
3. 봉인된 판정 도구(`las_rev_judge.py`, `las_revA_judge.py`, `k1_judge.py`, `fb_judge.py`, `u3_judge.py`, `las_k1_rem_judge.py`, `las_k1_sch_judge.py`, `las_k1_adopt_judge.py`)는 옛 태그 상수를 갖는다. adopt 9.2 원칙대로 고치지 않는다. 그래서 **이 규칙은 그 도구들로 판정하지 않고 새 도구 둘(11절)로 판정한다.** 앞으로 다른 규칙이 그 봉인 도구를 `_K1` 태그 결과에 쓰려면 그 규칙의 개정판(새 태그 상수 명시) 또는 새 도구가 필요하다.

### 0.2 질문

**K1 채택 제어기(P0+K1, 태그 `final_C4G2_LAS_K1` / `final_C4G2_P3_LAS_K1`)에서 LAS-b를 P5r4로 바꾸면, 나빠지는 것 없이 이륙 뒤 최소 힘 하한이 지켜지는가.** 하네스(재현 + 표본 밖 S-C)와 Chrono(혼합 지형·연약 지면)로 본다.

- 통과하면 **P5r4 채택 권고**다. 채택(프리셋 β·$N_r$ 변경, 새 태그, 전환 전 재현기, 전환 후 감사)은 사용자가 정하고 별도 전환 규칙으로 한다. 이 규칙은 프리셋을 바꾸지 않는다.

## 1. 봉인 전에 본 것 (공개)

### 1.1 이미 본 P5r4 결과 (과적합 공개)

| 자료 | 본 범위 | 이 규칙에서의 지위 |
|---|---|---|
| A안 rev2 판정서 `las_revA2_judgement.md`(R-0A 54, R-Q 48, R-T 192, R-S 30, R-P0 149, R-X 4) | 판정 값 전부 | Z-A·Z-T·Z-S는 **같은 키의 재실행**이다. 기구 확인·재현일 뿐 일반화 근거가 아니다 |
| K1 판정서 `las_k1_judgement.md`(Y-Sb P5r4/K1on 30, Y-T P5r4/K1on 192) | 판정 값 전부(경계 키 Y-Sb − Y-Sa −0.116 mm 등) | 같음 |
| 진단 `las_revA_diag_judgement.md`(경계 키 P0·P5·P5r4 3줄), 분석서 `las_revA_RGH_analysis.md` | 전부 | 같음 |
| K1 전환 G-3 재생(457줄, 새 프리셋에서 Y-Pa·Y-Pb·Y-Sa·Y-Sb·Y-T 해시 같음), 전환 후 감사 `las_k1_switch_post_audit.md` | 건수·해시 일치 | Z-S·Z-T 해시 예측의 근거 |
| Chrono: S-Ch 판정서, REM 판정서 `las_k1_rem_judgement.md`(R1~R8·F1·F2) | 판정 값 전부 | C-C 기준 줄의 비트 예측 근거. **P5r4 Chrono 결과는 없다(0행)** |

- **표본 밖 근거**는 다음뿐이다.
  - 하네스 Z-C의 S-C 456 전체 키 중 R-S와 겹치지 않는 **437키**(P5r4로 돈 적 없음)
  - Chrono 12행 전부(P5r4 Chrono 0행, 혼합 지형 행 0행, G1+J1@FL Chrono 0행)
- S-C P0 값: control-expert가 K1 원판 작성 때(2026-11-09) S-C P0 456줄의 $t_P$·$t_S$·LOC·R4·최대 행정을 봤다(K1 원판 0.2). 이 규칙(초안·봉인 후보판)을 쓰는 동안에는 값을 읽지 않았다(1.2).

### 1.2 이 규칙을 쓰려고 읽은 것 (초안·봉인 후보판)

- 문서: 위 표의 규칙·판정서 전부, 명세 436절(436.7·436.8), 전환 후 감사 원문(main checkout 미추적 파일 `las_k1_switch_post_audit.md`), `session_handoff.md`, decision_log 640~703행.
- 코드(읽기만): `run_S9.py` 1505~1575행(`CONTROLLER_EXPECTATIONS`, `_LAS_EXPECTATIONS`의 β 3.5 고정), `c2.py` `_liftoff_approach_slow_meta`(7948~7975), `LiftoffApproachSlowSettings` 필드(2121~2143), `las_chrono_rows.py`·`las_k1_chrono_rows.py`·`las_k1_rem_chrono_rows.py` 머리말·상수, `s9_batch.py` 369~378행.
- 저장 결과(값을 읽지 않은 스크립트, control-expert scratchpad `p5r4k1\`, `conda run -n dynamics-dev python -I -B`)
  - `scan_keys.py`: 하네스 jsonl 10개의 파일 sha256, 줄 수, `d1.key` 계열 건수, `las.candidate`/`controller_tag` 건수, `wall_s` 합·최대, 최상위 필드 이름.
  - `key_lists.py`: `rev.key` 목록과 목록 sha256(부록 A), S-C ∩ R-S = 19키.
  - `chrono_fields.py`: REM R1 `result.json`의 필드 이름만(`controller_meta.liftoff_approach_slow` 키, `p3b` 하위 키, `c2_setup` 키).
  - PowerShell `Get-FileHash`: REM R1·R4·R7·R8 `controller_commands.npz` sha256(4.4 BT-C 기준값).
  - (봉인 후보판 때 추가) `yp_blank.py`: `k1_YP.jsonl`에서 후보 필드가 없는 줄의 줄 번호·최상위 키·`rev.key`·`error`만 출력. `Select-String`으로 같은 키의 줄 번호만 찾음(부록 A).
  - (봉인 후보판 때 추가) 재감사 `las_k1_adopt_rev1_d8x_rev3_audit.md` F-5~F-7, `las_rev_targeted.py` 30~36행 docstring.
- 판정 값(힘·행정·READY·사건)은 이번에 저장 파일에서 새로 읽지 않았다. 판정서에 이미 적힌 값만 인용했다.
- (봉인 전 정리 때 추가, 2026-11-11)
  - 문서: K-2 판정 후 감사 `k2/judgement/k2_post_audit.md` 1~118행, 판정서 `k2/judgement/k2_judgement.md` 231~307행(7절·부록 A), `tools/verif` README의 `log_errors`·`placeholder_scan` 절.
  - 코드(읽기만, 16.1·16.5 근거): `run_S9.py` 95~108행(env 기본값)·2905~2923행(`--rigid-base`·`--crawler-kn-scale`·`--soil-patch` 거부), `hull_hook.py` 36~57행, `fb_targeted.py` 115~123행·1276~1470행 요약 출력, `run_v5.py` 295~308행·`maxtasksperchild`, `las_phase_diag.py` 770~810행(`install`), `c2.py` 2865~2900행(`with_10hz_d1`)·7946~8060행 메서드 이름, `v5_options.py` 태그 상수, 저장소 전체 grep(`light_leg_fraction_of_F_min`, `end_ramp_periods`, `flat_soil_margin_order_gate`, `os.environ`).
  - 저장 결과: 부록 A 재계산(식별 필드 `rev.key`·`las.key`·후보 이름·`k1.sub_bundle`·`error` 유무만). 판정 값은 읽지 않았다.

## 2. 후보와 기준 정의

| 이름 | 설정 | 하네스 구현 | Chrono 구현 |
|---|---|---|---|
| **ref = P0+K1** | `C2Config().with_10hz_d1()` 그대로(LAS-b b0, 관문 켬) | 프리셋 그대로, K1 토큰 없음 | `--las-candidate P0`(덮어쓰기 없음) |
| **cand = P5r4+K1** | 위 + `replace(las, light_leg_fraction_of_F_min=4.5, end_ramp_periods=4)` | `dataclasses.replace` 한 번 | `--las-candidate P5r4`(11.2) |

- 태그: 두 팔 모두 프리셋 태그다. V0 `final_C4G2_LAS_K1`, VB `final_C4G2_P3_LAS_K1`. 후보 구분은 태그가 아니라 `las_candidate` 필드로 한다(A안 관례와 같음).
- **두 번 적용 금지**
  - K1: 프리셋만 쓴다. 하네스 토큰 `K1on`, Chrono `--k1-order-gate`를 **주지 않는다**. 실효 값은 실행된 제어기의 `controller_meta.slope_clearance_margin.settings.flat_soil_margin_order_gate`와 `order_gate.enabled`로 확인한다(따로 만든 제어기 값으로 확인하지 않는다, 전환 후 감사 R-5).
  - LAS-b: 덮어쓰기는 한 번이다. 덮어쓰기 전 프리셋이 b0인지(β 3.5, $n_{min}$ 0, $N_r$ 0)와 관문 True를 먼저 확인한다. P0 팔은 덮어쓰지 않는다.
  - `--las-off`, `--k1-forced-block first`, `pre_*_preset_runner.py`는 이 규칙의 행에 쓰지 않는다. 섞이면 K 위반(stop).
  - **"LAS-b 꺼짐 + 관문 켬" 조합(`--las-off --k1-order-gate on`, 하네스 `pre_las_preset_runner.py` + `K1on`, 태그 `final_C4G2_K1`·`final_C4G2_P3_K1`)은 이 규칙에서 쓰지 않는다**(재감사 F-6). 이 규칙에는 LAS-b 단일 변수 짝(LAS 끔 대 켬)이 없다. 짝의 변수는 LAS-b 후보(P0 대 P5r4) 하나다. 그래서 그 조합 태그를 run_S9 `--expect-controller` choices에 더할 필요가 없다. 이 조합 행이 묶음에 하나라도 있으면 K-3 위반(stop)이고, 실행 전 감사가 행 목록에서 0건을 확인한다(9절 K-3, 11.5).
- 프리셋 기본값은 바꾸지 않는다.
- **K-2 `_TCL` 미채택 반영(2026-11-11)**: 두 팔 모두 터치 크리프 래치가 꺼진 현행 프리셋이다(`touch_creep_latch.enable` 거짓, 클래스·프리셋 기본값 그대로). 태그 접미사 `_TCL`(`v5_options.TOUCH_CREEP_TAG_SUFFIX`)이 붙은 태그(`final_C4G2_LAS_TCL`, `final_C4G2_LAS_K1_TCL` 등)와 K-2 `_TCL` 실행 도구·인자(`touch_creep_latch=True`를 넣는 경로)는 이 규칙의 행에 쓰지 않는다. 섞이면 K-3 위반(stop). 실효 값은 실행된 제어기 meta `touch_creep_latch`로 확인한다(K-4).

## 3. PAIR_DIVERGE 정의 (이 판에서 확정)

- adopt2는 3.4(조건부: "$L_1$ dP > 0이면 … 다르면 FLAG")와 6절(무조건: "짝 명령 sha가 다름")이 달랐다. REM에서는 두 정의 모두 0이라 결과에 닿지 않았다(REM 판정서 11절).
- **이 규칙의 정의(조건부)**: `PAIR_DIVERGE` = 결과 전에 정한 **짝 동일 전제**가 기록 특징으로 참인 짝에서 명령 해시가 다른 것.
  - 이 규칙의 짝 동일 전제: **cand의 LAS-b가 시작하지 않았다**(`las.start_t_s` None, Chrono는 `controller_meta.liftoff_approach_slow.start_s` None).
    - 근거: β가 커지면 S7_light 조건(min L < β $F_{min}$)이 참인 주기 집합은 커지기만 한다. LAS-b가 시작하기 전에는 두 팔의 입력열이 같다. 그래서 β 4.5에서 한 번도 시작하지 않았으면 β 3.5에서도 시작하지 않는다. 램프는 LAS-b 끝 뒤에만 작용한다.
  - 명령 해시: 하네스 `commands_sha256`. Chrono는 `controller_commands.npz`의 `t_s`·`issued_u_m_s` 배열 내용 해시(파일 sha는 기록).
  - **처리: stop(구현 결함 후보)**. A안 K-A7과 같은 사건이다. FLAG가 아니다.
- 전제가 거짓인 짝(cand LAS-b 시작)의 명령 차이는 **설계상 생긴다**. 이것은 `PAIR_CMD_DIFF` 건수로 **기록만** 한다.
- 조건부로 정한 이유
  1. 무조건 정의는 차이가 의도인 짝(이 규칙에서는 LAS-b가 작동한 모든 짝)에서 구조적으로 켜진다. 정보가 없고, 진짜 표류(전제가 참인데 다름)를 묻는다.
  2. adopt2 3.4의 문맥과 REM 경로 2의 계수가 조건부였다.
  3. 전제는 결과 전에 쓸 수 있고, 갈라지기 전 기록(LAS-b 시작 여부)으로 판단할 수 있다.
- adopt2와 REM 판정은 바꾸지 않는다(두 정의 모두 0).

## 4. 묶음

### 4.1 공통

- 하네스 출력은 새 폴더 `06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/`(main checkout, 로컬 전용, git exclude), 줄 파일 `p5k_<묶음>.jsonl`. 앞 폴더(`revA2/`, `k1/`)에 쓰지 않는다.
- Chrono 배치 이름 `V5-LAS-P5R4-K1`(`s9_batch` 등록), 결과 `07_results/S9/batch_V5-LAS-P5R4-K1_<시각>/`.
- 짝은 **전체 키**(`rev.key` = `d1.key|setting|e<eps>`, 격자 행은 줄 이름)로 맺는다.
- 키 목록은 저장 기준 파일에서 다시 계산하고 부록 A 목록 sha256과 대조한다. 다르면 실행하지 않는다. `--keys`·`--limit`은 본 실행에 쓰지 않는다.

### 4.2 하네스 묶음

| # | 묶음 | 키 | 팔 | 줄 | 기대(비트 예측, 4.4) |
|---|---|---|---|---|---|
| Z-0 | 비트 시험 b0 | A안 원판 7.1의 6작업(`revA_R0.jsonl` 키) | ref | 6 | `revA_R0.jsonl` 해시 6/6 |
| Z-A | (가)′ 재현 | R-0A 54(R-G 30 + R-H 24) + R-Q 48 | cand | 102 | `revA_R0A.jsonl`·`revA_RQ.jsonl` 해시 102/102 |
| Z-T | (나) | R-T 192키 | ref, cand | 384 | ref = 저장 L(`las_T1`·`las_T2` b0 줄) 192/192, cand = `revA_RT.jsonl` 192/192 |
| Z-S | (다) | R-S 30작업 | ref, cand | 60 | ref = `k1_YS.jsonl` P0 30/30, cand = `k1_YS.jsonl` P5r4 30/30 |
| Z-C | (라) **표본 밖** | S-C 456 전체 키(`s2d_SC.jsonl`) | ref, cand | 912 | ref = 저장(R4 평가 165키는 `k1_YP.jsonl` K1on 줄, 나머지 291키는 `s2d_SC.jsonl`) 456/456. cand는 예측 없음 |
| Z-X | C-4 예외 근거 | 예외를 주장하는 짝의 ref(DONE 기록 켬) | ref | ≤ 10 | ref 해시 = Z-T/Z-S ref 해시 |

- Z-A에는 ref 팔이 없다. (가)′는 A안 rev2처럼 cand 절대 하한(G-2′)만 본다. 짝 기준(K-A1~K-A4)은 R-0A의 저장 P5 짝이다(A안 rev2 R2-5).
- Z-C의 키는 S-C의 모든 계열(H-S-0 216, H-S-C 120, H-S-A 72, H-S-C-g 24, H-S-1 12, H-R-A-S1 4, H-R-A-J2 4, H-S-A-J2 4)과 VB·V0 × ε 0·0.002다. R-T와 겹치는 키는 0, R-S와 겹치는 키는 19다(1.1).
- 실행 순서: Z-0 → Z-A → Z-T·Z-S·Z-C → (필요하면) Z-X → 하네스 판정. Z-0 또는 Z-A에 비트 불일치가 한 줄이라도 있으면 다음 묶음을 돌지 않는다(8절 S-2).
- 스레드 1 고정(`fb_targeted.thread_problems`). 줄마다 작업자 마스크를 기록한다.

### 4.3 Chrono 묶음 (`V5-LAS-P5R4-K1`, 12행)

공통: 패드 B(`dwg_rear250`), F_s 4 kN, 오거 상단, 압력 normal, IMU ideal, seed 20261026, `--threads` = `run_S9.SCM_THREADS_FIXED`(4), start_env `OMP_WAIT_POLICY=PASSIVE`·`OUTRIGGER_HULL_HOOK=fast`, DLL sha `cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15`, 계획 풀 P(짝은 같은 풀 종류). `--expect-controller`는 VB `final_C4G2_P3_LAS_K1`, V0 `final_C4G2_LAS_K1`. 짝의 argv 차이는 `--las-candidate` 값 하나(+ `case`)다.

| # | id | 지형·조건 | 플랜트 | 폐루프 | 팔 | 짝 | 보는 것 |
|---|---|---|---|---|---|---|---|
| 1 | A1 | 혼합 지형 강체 + J1@FR(`las_chrono_rows` 꼴), 바닥 (2.3351, 1.5017)°, `record_only`, Kc1 | VB | 160 s | ref | A2 | 이륙 뒤 최소 힘(G-2′C) |
| 2 | A2 | 같음 | VB | 160 s | cand | A1 | |
| 3 | A3 | 같음, Kc3(`--crawler-kn-scale 3`) | VB | 160 s | ref | A4 | |
| 4 | A4 | 같음 | VB | 160 s | cand | A3 | |
| 5 | A5 | 같음, Kc1 | V0 | 160 s | ref | A6 | V0 위상 갈래(하네스 V0 칸이 낮았음) |
| 6 | A6 | 같음 | V0 | 160 s | cand | A5 | |
| 7 | B1 | G6 꼴 G1 바닥 + J1 패치@FL(`las_k1_chrono_rows` 꼴, 패치 세트만 J1), 평지 | VB | 200 s | ref | B2 | 경계 키 `D1\|H-S-A\|G1+J1@FL\|T\|flat\|K1\|VB\|e0`의 Chrono 대응(C-S, K1 막힘) |
| 8 | B2 | 같음 | VB | 200 s | cand | B1 | |
| 9 | C1 | P3b 균일 J2 평지(`las_k1_rem_chrono_rows` 꼴), ×1.0 | VB | 120 s | ref | C2 | K1이 R4c30을 계속 켜는가(R4_LOST, F2 한계 경로) |
| 10 | C2 | 같음 | VB | 120 s | cand | C1 | |
| 11 | C3 | 같음, ×1.1(`--mass-scale 1.1`) | VB | **180 s** | ref | C4 | |
| 12 | C4 | 같음 | VB | **180 s** | cand | C3 | |

- C3·C4를 180 s로 늘리는 이유: REM R8(같은 조건 ref)의 첫 READY가 117.6 s로 120 s 끝에 붙어 있다. cand가 조금만 늦어도 "READY 없음"(C-2형 (b))이 루프 길이 때문에 난다. 그래서 C3도 180 s로 돌리고, 비트 예측(4.4 BT-C)은 앞 120 s 구간으로 본다.
- 실행 순서: 하네스 판정 `통과` 뒤에만 시작한다(8절 S-6). 배치표는 compute-scheduler-expert(12절).

### 4.4 비트 예측 (판정 기준. 어긋나면 stop)

| # | 예측 | 근거 |
|---|---|---|
| BT-0 | Z-0 6/6 = `revA_R0.jsonl` | b0 경로, K1은 R4 평가 LOC에서만 작동하고 이 6작업은 토양 모드가 없다(Y-T 192/192와 같은 계열) |
| BT-A | Z-A 102/102 = `revA_R0A.jsonl`·`revA_RQ.jsonl`의 같은 줄 | 같은 계열(강체 + J1@FR), Y-T에서 K1on 192/192 같음 |
| BT-T | Z-T ref 192/192 = 저장 L, cand 192/192 = `revA_RT.jsonl`(= `k1_YT.jsonl`) | Y-T, R-P0 149/149, G-5b |
| BT-S | Z-S ref 30/30 = `k1_YS.jsonl` P0, cand 30/30 = `k1_YS.jsonl` P5r4 | G-3(새 프리셋에서 Y-Sa·Y-Sb 해시 같음) |
| BT-CR | Z-C ref 456/456 = 저장(165 `k1_YP.jsonl` K1on, 291 `s2d_SC.jsonl`) | Y-Pa·Y-Pb, G-3. R4 평가가 없는 줄에서 관문은 명령을 바꾸지 않는다 |
| BT-C | Chrono C1의 명령 배열(`t_s`·`issued_u_m_s` 내용 해시) = REM R7(파일 sha `ebf86d1d40af464e2e4e23d4ea79ad56721829e65d70cb4efb1d2cc072e4b559`의 내용). C3의 앞 120 s(t ≤ 128 s) 구간 = REM R8(`97aace614a534a6aa95f67857947dcd541f9ecca1e9974eb5105fc017bf7c8aa`의 내용) | REM R7·R8은 관문 켬 + LAS-b b0 + 같은 조건이다. 전환은 태그·기본값만 바꿨다. 같은 스레드 수·풀 |
| BT-X | Z-X ref 해시 = 같은 키 Z-T/Z-S ref 해시 | A안 원판 6절 |

- A1~A6, B1·B2, cand 행에는 비트 예측이 없다(새 조건).
- BT-C가 어긋나면 Chrono 판정을 멈추고 묻는다. 결과(짝 판정)는 정보용으로 적는다(전환이 설명되지 않는 변화를 냈다는 뜻이기 때문이다).

## 5. 줄·행마다 기록할 것 (실행 정체성)

### 5.1 하네스 줄

- `git_head`, `git_dirty`, `dirty_files`, `code_diff_sha256`(A안 원판 4.1. dirty는 시험 파일만, K1 rev1 R1-4)
- sha256: `c2.py`, `v5_options.py`, 실행 도구, 판정 도구, `las_revA_targeted.py`·`fb_targeted.py`·`las_targeted.py`·`k1_targeted.py`(import하면), 이 규칙 + 0절 표의 모든 규칙
- `controller_tag`: VB `final_C4G2_P3_LAS_K1`, V0 `final_C4G2_LAS_K1`(정확 일치. `v5_options.is_liftoff_slow_tag` 참도 함께 기록)
- `las_candidate`(`P0`/`P5r4`), `las.settings`(실행된 제어기의 asdict), `las.ramp`, `las.start_t_s`·`end_t_s`·`end_reason`
- `k1`: `enabled`(실행된 제어기 meta), `decisions`(adopt2 키 전부), `would_block_any`, `r4_applied`
- `rev.attempt`(1/2), `rev.resumed`, 작업자 마스크, 스레드 변수(`OMP_NUM_THREADS` 등 1)
- `done_trace`·`done_clock`(원판의 원판 4.2, cand와 Z-X ref)

### 5.2 Chrono 행 (result.json·batch.json)

- `code_state.git_at_start.head`, dirty 목록, 코드 sha(작업 트리 CRLF, HEAD blob LF): `run_S9.py`, `s9_batch.py`, `las_p5r4_k1_chrono_rows.py`, `c2.py`, `zero_calibration.py`, `hull_hook.py`, `late_loc_rule.py`, `v5_options.py`, `rigid_base.py`
- `c2_setup.las_candidate`(`requested`, 적용 뒤 `settings` asdict), `c2_setup.k1_order_gate`(= `preset`), `k1_order_gate_effective` 참, `c2_setup.k1_forced_block` `off`, 제어기 클래스 `C2Controller`
- `controller_meta.liftoff_approach_slow`(`settings`, `start_s`, `end_s`, `end_reason`, `active_periods`, `ramp`), `controller_meta.slope_clearance_margin`(`settings`, `order_gate.enabled`, `order_gate.decisions`), `controller_meta.loc_revoke`, `controller_meta.soil.mode_starts`
- `expect_controller.ok`, `args.threads` = `num_threads_chrono` = 4, batch `omp_wait_policy` PASSIVE, `hull_hook.mode` = `requested` = `fast`, `fallback_reason` None, batch `hull_hook_effective`·`mixed_hull_mode` 거짓, `placement`(풀, `affinity_ok`, `power_throttling_off_ok`)
- `rc`, `restored_from` None, `rerun_of`(재실행 행만)

## 6. 판정 기준

### 6.1 하네스 (가)′ — Z-A (cand 102줄)

| # | 기준 | 정의 |
|---|---|---|
| G-1 / G-1H / G-1Q | 하한 | `F_RL_kN`·`F_judged_min_kN` ≥ 10.400 kN(30 / 24 / 48줄) |
| G-2′ | 하한 여유 | 102줄 모두 `F_RL_kN`·`F_judged_min_kN` ≥ **11.414589** kN(A안 rev2 R2-1) |
| G-3 | 제외 검사 | A안 원판 G-3(묶음마다 모든 줄, 오류 0, LEVEL 예산 0, `gate_consistent` 참) |
| G-4 | 구현 예측 | K-A5·K-A6·K-A8, K-A1~K-A4(저장 P5 짝, A안 rev2 R2-5) |

- BT-A가 참이면 값은 A안 rev2 판정과 같다. 그래서 (가)′는 **재현 확인**이다(1.1).
- 기록: 원 G-2·G-2H, Q-1~Q-5(rev3 RQ3-1 분류), M-1~M-3.

### 6.2 하네스 (나) Z-T, (다) Z-S, (라) Z-C — 짝(cand − ref)

| # | 기준 | Z-T | Z-S | Z-C | 정의 |
|---|---|---|---|---|---|
| C-2형 | 나빠짐 0 | ○ | ○ | ○ | K1 rev1 R1-2(= `pair_violations` 정의: verdict None, `d1.items` 합집합, READY → None, 새 FAULT·WARN·`fail_items`). verdict 사례는 (b)·(c)만 |
| P3 | 끝 크롤러 | ○ | ○ | ○ | K1 rev1 R1-1(기준 참 → 후보 거짓/없음 = 위반, 기준 거짓은 `P3_baseline_false`로 적음) |
| C-1 | 계열 하중 | ○ | — | — | T-1 8키 cand `d1.F_judged_min_N` ≥ 10,414.589 N |
| C-F | 여유선 | ○ | ○ | ○ | ref ≥ 10,414.589 N인 짝에서 cand ≥ 10,414.589 N |
| C-S | 행정 | ○ | ○ | ○ | 모든 D-1 짝에서 $s_{max}$ 증가 ≤ 0.001 m |
| CK-1 | R4c30 유지 | ○ | ○ | ○ | ref의 $L_1$이 `applied` 참이면 cand에도 `applied` 참인 R4 평가 decision이 있다. 없으면 위반 `R4_LOST` |
| A-3 | 강체 균일 | ○ | — | — | H-R-0 48키 cand 해시 = ref 해시 |
| R-1 / R-2 | READY | ○ | 기록 | ○ | 해시가 바뀐 짝 모집단 $\mathcal{P}$(원판의 원판 5.2, C-4 예외 6절 + A안 6 램프 끝 조건)의 $\Delta t$ 중앙 ≤ +1.0 s, 최대 ≤ +5.0 s |

- CK-1은 이 규칙에서 새로 넣었다. K1의 알려진 한계(REM F2: 첫 R4 LOC가 막히면 R4c30이 끝까지 없음)가 P5r4의 LOC·토양 모드 순서 변화로 판정 행에서 생기는지를 직접 본다. 반대(cand에만 적용, `R4_GAINED`)는 FLAG로 적고 C-S가 판정한다.
- $\mathcal{P}$ 빈 집합: 해시가 바뀐 짝이 0이면 "해시 동일로 성립"이고 건수를 적는다. 바뀐 짝이 있는데 $\mathcal{P}$가 비면 `undecidable`(원판의 원판 5.2).
- 구현 예측 K-A7(전제 참 → 해시 같음)은 3절 `PAIR_DIVERGE`로 처리한다(stop). K-A8은 모든 cand 줄 `las.settings`가 P5r4, 모든 ref 줄이 b0임을 본다.
- Z-C는 판정 짝 456개다. 짝 단위로 센다.

### 6.3 Chrono — 짝(cand − ref)

| # | 기준 | 대상 | 정의 |
|---|---|---|---|
| CC-2 | 나빠짐 0 | 6짝 | (a) 판정 항목 집합 $I$의 각 항목: ref 참 → cand 거짓(또는 없음) = 위반. (b) ref 끝 단계 `ready` → cand 비ready = 위반, ref 첫 READY 있음 → cand 없음 = 위반. (c) cand `FAULT*`·`WARN*` 사건 이름 ⊆ ref 이름 |
| CC-F | 여유선 | 6짝 | ref $F^{C}_{after}$ ≥ 10,414.589 N이면 cand ≥ 10,414.589 N |
| G-2′C | 하한 여유 | A2·A4·A6 | cand $F^{C}_{after}$ ≥ 11,414.589 N **그리고** $F^{C}_{tr}$ ≥ 11,414.589 N |
| CC-S | 행정 | 6짝 | $s_{max}$ 증가 ≤ 0.001 m |
| CK-1C | R4c30 유지 | B·C 짝 | ref $L_1$ `applied` 참 → cand에 `applied` 참 R4 평가 decision 있음. 없으면 `R4_LOST` 위반 |
| CC-R | READY | 해시가 바뀐 짝 | $\Delta t$ = cand − ref `P3-6_ready.t_ready_after_loop_start_s`. 최대 ≤ +5.0 s, 중앙 ≤ +1.0 s(둘 다 값이 있는 짝). 바뀐 짝이 있는데 모집단이 비면 `undecidable` |

- 판정 항목 집합 $I$ = `p3b.checks`의 `P3-1_recontact_pass`, `P3-1_crawler_zero_after_ready`, `P3-2_within`, `P3-3_within`, `P3-4_within_0p2`, `P3-5_within`, `P3-6_within`, `P3-7_within`, `P3-8_within`.
  - 예외(명세 419.8): `P3-2_within` 참 → 거짓이어도 cand `P3-2_late_loc_reapproach` 또는 `P3-2_late_loc_revoked`가 참이면 위반이 아니라 FLAG `LATE_LOC_P32`다.
  - `P3-4_window_short`는 FLAG(명세 433.6)이고 $I$에 넣지 않는다.
  - $I$의 키가 한 행이라도 없으면 그 짝은 `undecidable`(구현자가 키 이름을 실행 전에 확인한다, 11절).
- **관측 요건(빈 집합 통과 금지)**: A 짝 3개 가운데 cand LAS-b가 시작하고 램프가 작용한(`ramp.periods_applied` ≥ 1) 짝이 **1개 이상** 있어야 한다. 없으면 Chrono `undecidable`(사유 `NO_P5R4_OBSERVATION`). B·C 짝에서 cand LAS-b가 시작하지 않으면 그 짝은 판정은 하되(동일 → 위반 없음) 판정서에 "P5r4 미작동, P5r4 근거 아님"을 적는다.
- `R4_GAINED`(cand에만 R4c30 적용)는 FLAG이고 CC-S가 판정한다.
- C3·C4의 READY·사건·항목은 180 s 전체로 본다.

### 6.4 기록 (판정 아님)

- 짝마다: LAS-b 시작·끝·끝 사유·작동 주기·$\lambda_0$·램프 끝 사유, LOC 시각, 토양 모드 시작, $L_1$ 튜플, `PAIR_CMD_DIFF`, READY $\Delta t$, 최소 힘 다리·시각, 끝 크롤러 틈, 최대 행정.
- FLAG: `R4_GAINED`, `LATE_LOC_P32`, `THIN_MARGIN`(cand $L_1$ dP ≤ 12), 10.400~10.4146 kN 사이 줄, Z-C의 R-S 겹침 19키 결과(표본 안)와 437키 결과(표본 밖)를 나눈 표.
- Chrono A 짝: ref 대비 cand 최소 힘 차, 하네스 같은 계열 값(`las_chrono_rows` 머리말 b0 11.377 kN)과의 차.

## 7. 사전 예측 (판정 기준 아님. 4.4 비트 예측만 판정 기준)

| # | 항목 | 예측 | 확신 |
|---|---|---|---|
| P-1 | Z-A·Z-T·Z-S 판정 | A안 rev2·K1 Y-S와 같은 값으로 모두 통과 | 높음(BT가 참이면 자명) |
| P-2 | Z-C cand LAS-b 시작 줄 | 456 가운데 40~140줄(9~31 %). 근거: R-S 30작업 중 P5r4 시작 5줄 | 중간 |
| P-3 | Z-C `PAIR_CMD_DIFF` | P-2의 시작 줄과 같은 수(시작 → 명령 다름) | 중간 |
| P-4 | Z-C C-S | 위반 0. 위반이 난다면 기구는 `R4_GAINED`(cand만 토양 모드 + dP > 0) | 중간(60 %) |
| P-5 | Z-C CK-1 | `R4_LOST` 0(균일 연약 지면 dP가 크다: S-C 진짜 연약 지면 dP ≥ +31주기) | 중간~높음 |
| P-6 | Z-C C-2형·P3·C-F | 위반 0 | 중간 |
| P-7 | Z-C R-1 / R-2 | 중앙 ≤ +0.5 s, 최대 ≤ +3 s | 중간 |
| P-8 | Chrono A2·A4·A6 | cand LAS-b 시작·램프 작용. $F^{C}_{after}$ 12.0~15.0 kN(G-2′C 통과). A6(V0)이 셋 중 가장 낮다 | 중간(하네스↔Chrono 이륙 과도 일치는 확인된 적 없음) |
| P-9 | Chrono A ref | $F^{C}_{after}$ 10.5~12.0 kN(하네스 b0 11.377 kN 근처) | 낮음~중간 |
| P-10 | Chrono B 짝 | ref·cand 모두 R4c30 없음(토양 모드 없음 또는 K1 막힘), $\lvert\Delta s_{max}\rvert$ ≤ 1 mm, C-S 통과 | 중간(60 %) |
| P-11 | Chrono C 짝 | ref·cand 모두 `POS`·$L_1$ 적용(REM dP +99·+198 대비 LAS-b 지연 ≤ 10주기), CK-1C 통과 | 높음 |
| P-12 | Chrono C 짝 C-S | $\lvert\Delta s_{max}\rvert$ ≤ 1 mm. 연약 지면 소성 침하가 들어 올림 속도에 따라 몇 mm 달라질 수 있어 **확신 낮음(50 %)** | 낮음 |
| P-13 | BT-C | C1 = R7, C3 앞 120 s = R8 | 높음 |
| P-14 | 전체 등급 | 하네스 `통과`, Chrono `통과`(가장 가능성 큰 미달 사유: P-12 C-S, 그다음 P-10) | 중간 |

## 8. 등급·순서·멈춤

### 8.1 묶음별 상태 (앞의 것이 이긴다)

| 순서 | 상태 | 조건 |
|---|---|---|
| 1 | `stop` | 비트 예측(4.4) 불일치, 구현 예측(K-A5·K-A6·K-A8) 불일치, `PAIR_DIVERGE`, 정체성 K 위반(9절), 두 번 적용 흔적(2절) |
| 2 | `undecidable` | 판정 필드 누락(원판의 원판 5.0, A안 R1-3), $\mathcal{P}$ 빈 집합인데 바뀐 짝 있음, Chrono 관측 요건 미달, 결측(10절) |
| 3 | `미달` | 6.1~6.3 기준 하나라도 위반. **나오는 즉시 확정**(K1 원판 SK-5). 판정을 되돌리거나 기준을 고치지 않는다 |
| 4 | `통과` | 모든 기준 참 |
| — | `incomplete` / `not_run` | 묶음 줄 없음 / 앞 단계 미통과로 안 돔 |

- 최종: 하네스(Z 전체)와 Chrono가 모두 `통과`면 **P5r4 채택 권고**. 하나라도 `미달`이면 P5r4 `미달`(P0 유지 권고, 채택 여부는 사용자). `stop`·`undecidable`은 묻는다.
- **우선순위는 기준·묶음·최종 모든 층에서 `stop` > `undecidable`(판정 불가) > `미달`(실패) > `통과`다**(16.6, K-2 경로 2 결함 C4). 위 "하나라도 `미달`이면 P5r4 `미달`"은 `stop`·`undecidable`이 하나도 없을 때의 문장이다. 자세한 합성 규칙은 16.6.

### 8.2 멈춤

| # | 조건 | 처리 |
|---|---|---|
| S-1 | 이 규칙·0절 표 규칙의 `.sha256`이 없거나 LF sha256이 다름 | 실행하지 않는다 |
| S-2 | Z-0·Z-A 비트 불일치 | 다음 묶음을 돌지 않는다. python-expert가 원인을 찾은 뒤 Z-0부터 다시(새 판 필요 여부는 감사가 정함) |
| S-3 | Z-T·Z-S·Z-C 비트 불일치(ref 또는 BT 대상 cand) | 진행 중 묶음은 끝까지 돌리고(정보용) `stop`, 묻는다 |
| S-4 | 기준 위반 | 즉시 `미달` 확정. 진행 중 묶음은 끝까지 돌리고 나머지 줄은 정보용으로 적는다. 다음 묶음(Chrono 포함)은 `not_run` |
| S-5 | 한 묶음에서 C-2형 위반 짝 누적 ≥ 5 | 그 묶음 남은 실행을 멈춘다(A안 H-8) |
| S-6 | 하네스 판정이 `통과`가 아님 | Chrono를 시작하지 않는다(사용자 결정이 있으면 예외, 판정서에 시각과 함께 적음) |
| S-7 | BT-C 불일치 | Chrono 판정 멈춤, 짝 결과는 정보용, 묻는다 |
| S-8 | C-4 예외 과다(한 묶음 > 5 또는 $\Delta t$ > +15 s) | 자동 권고하지 않고 묻는다 |
| S-9 | 실행 중 점검에서 단계 로그 `errors N`(N > 0) 또는 Chrono `progress.log` `rc≠0`(16.3) | 그 묶음의 다음 단계를 띄우지 않는다. 오류 줄은 10.1대로 처리하고, 원인이 정의·도구 결함이면 `stop` |
| S-10 | 판정 전 관문(16.3·16.4) 실패: 단계 로그 오류 > 0이 처리되지 않음, 채워지지 않은 자리표시 ≥ 1 | 판정 도구를 돌리지 않는다. 고친 뒤 관문부터 다시 |

- 미달이어도 값을 바꿔 다시 돌리지 않는다. β, $N_r$, 문턱, 키, 행을 결과를 본 뒤 바꾸려면 새 판(결과 본 뒤 판으로 공개)을 봉인한다.

## 9. 정체성·일관성 검사 (하나라도 거짓이면 stop)

| # | 검사 |
|---|---|
| K-0 | 이 규칙 sha256 = `.sha256` 기록. 두 판정 도구 sha256 = 실행 전 감사 기록 = prelaunch = postrun = judge. 실행 전 감사 리포트 파일(원문 그대로 저장) sha256 = prelaunch 기록 |
| K-1 | 하네스: 한 묶음·한 팔의 모든 줄이 한 `git_head`, dirty 허용 밖 0, `code_diff_sha256` 빈 해시. Chrono: 12행 `git_at_start.head` = prelaunch HEAD, `git diff --quiet <prelaunch> <postrun> -- 03_src 02_params 04_scripts` 참, `git status --porcelain --untracked-files=no` 허용 목록 밖 0줄 |
| K-2 | 코드 sha(5.1·5.2 목록) = 기록. `c2.py`·`v5_options.py` blob이 prelaunch HEAD blob과 같다 |
| K-3 | 태그: 모든 줄·행 `controller_tag`(Chrono `expect_controller`) = 설정별 새 태그 정확 일치. 옛 태그(`_LAS`로 끝나는 것 포함) 0. LAS 꺼짐 + 관문 켬 조합 태그(`final_C4G2_K1`, `final_C4G2_P3_K1`)와 `--las-off` 인자 0(2절, F-6). `_TCL` 접미사 태그 0(2절 끝) |
| K-4 | 관문: 모든 줄·행 실행된 제어기의 `flat_soil_margin_order_gate` 참, `order_gate.enabled` 참, `decisions` 키 있음. 하네스 줄에 K1 토큰 흔적 없음, Chrono `c2_setup.k1_order_gate` = `preset`. 실행된 제어기 meta `touch_creep_latch`의 켬 여부 거짓(2절 끝) |
| K-5 | LAS-b 설정: ref 줄·행 `settings`가 b0(β 3.5, $n_{min}$ 0, $N_r$ 0, 나머지 436.3 값), cand 줄·행이 P5r4(β 4.5, $N_r$ 4, 나머지 b0). `las_candidate` 필드와 맞음(K-A8) |
| K-6 | Chrono 실행 조건: threads 4 = `num_threads_chrono`, PASSIVE, hull `fast`·DLL sha·`fallback_reason` None·`mixed_hull_mode` 거짓, 풀 = 계획, 짝 같은 풀 종류, `affinity_ok`·`power_throttling_off_ok` 참. env 조항은 16.5 표의 "없거나 기본값" 꼴로 판정한다(실행기가 스스로 넣는 값 포함) |
| K-7 | Chrono 인자: 짝 argv 차이 = `--las-candidate` 값 하나(+ `case`). 고정값(seed, grade, F_s, pad, soil, level, mass_scale, duration, rigid-base, crawler-kn-scale, v5 인자) 일치. `--k1-order-gate`·`--k1-forced-block`·`--las-off` 없음 |
| K-8 | decision 기록 일관성: adopt2 K-8 (a)~(e)를 모든 행·줄에 적용 |
| K-9 | 목록: 묶음 키 목록 sha256 = 부록 A, 중복 줄 0, 목록 밖 줄 0, 짝 없는 키 0 |
| K-10 | 두 경로 재집계 완전 일치(10.2). 판정서가 도구 밖에서 확정한다 |

## 10. 결측·두 경로

### 10.1 결측·오류

| 경우 | 처리 |
|---|---|
| 하네스 오류 줄 | 같은 정체성으로 그 키만 1회 재실행(`rev.attempt` 2, 공개). 남으면 `incomplete` |
| Chrono 행 실패(rc ≠ 0, result.json 없음 등, 인프라 원인) | 같은 argv·같은 HEAD로 **1회만** 재실행(사용자에게 알린 뒤, `rerun_of`). 두 번째도 실패하면 그 짝 `undecidable` |
| Chrono 제어 FAULT·안전 정지로 끝남 | 결측이 아니다. CC-2로 판정한다 |
| 결측 행을 하네스·옛 Chrono 행으로 메움 | 금지 |

### 10.2 두 경로 재집계

- 경로 1: python-expert 판정 도구 두 개(11절). 잠정 등급, `k10: null`.
- 경로 2: control-expert 독립 재집계 스크립트(하네스 `p5k_recount.py`, Chrono `p5k_chrono_recount.py`, scratchpad). 판정 도구·프로젝트 모듈을 열지도 import하지도 않는다. jsonl·result.json·batch.json·이 규칙만 읽는다.
  - **결과 전 고정**: 구현이 끝난 뒤, 도구 단위 시험의 합성 줄(fixture)로만 맞춰 보고 sha256을 메인 세션에 넘긴다. 이 sha는 prelaunch에 기록한다. **판정 줄을 한 줄이라도 만든 뒤에는 고치지 않는다.** 첫 불일치 뒤 맞춘 항목은 독립이 아님을 공개한다.
  - 출처를 경로 1과 다르게 둔다: LOC는 decision 먼저·사건 대조, $t_S$는 `mode_starts` → 사건, 사건 이름은 `split(":",1)[0]` 정확 일치, READY는 `values.times.t_first_ready_s`(하네스)·`P3-6_ready`(Chrono).
  - 두 경로 모두 16.6 우선순위(`stop` > `undecidable` > `미달` > `통과`)를 기준·묶음·최종 층에 같은 꼴로 적용한다. 실행 오류 줄(`error` 키)은 판정 전에 따로 세어 출력한다(16.3). 목록 출력에 상한을 두지 않는다. 상한이 필요하면 `truncated: true`와 원래 수를 함께 낸다(K-2 판정 후 감사 C3).
  - **독립성**: 경로 2 작성자(control-expert)는 경로 1 코드·출력을 열지 않는다. 정의를 맞출 일이 생기면 이 규칙의 덧붙임 판 문장만 쓴다.
- K-10 비교 대상: 비트 예측 결과, 짝별 위반 목록·`items_only_*`, 기준별 참·거짓·개수·중앙·최대·최소, `PAIR_DIVERGE`·`PAIR_CMD_DIFF`, CK-1 분류, FLAG 건수, 등급. 수치 허용 1e-9(kN·s·m). 등급·목록은 완전 일치.

## 11. 구현 목록 (위임)

### 11.1 전환 후 감사 W-3 태그 소비자 — 이 규칙에서의 처리

| 소비자 | 이 규칙에서 쓰나 | 처리 |
|---|---|---|
| `s9_batch.V5_P3_LAS_K1_CONTROLLER`·`V5_LAS_K1_CONTROLLER`(정의만 있음) | 쓴다 | 새 행 모듈이 이 상수를 기대값으로 쓴다(연결) |
| `las_chrono_rows.py:75,144`(옛 `_LAS` 태그) | 지형 도우미만(`base_case`, `level_argv`) | 파일을 고치지 않는다. 새 모듈이 도우미를 import하고 태그는 직접 정한다. 옛 `V5-LAS-CHRONO` 4행은 436.8 재개 때 처리 |
| `las_k1_chrono_rows.py:50` | 지형 도우미만(G6 꼴, 패치 세트 인자) | 고치지 않는다(S-Ch 재현 정의 유지). 패치 세트를 인자로 받는 도우미가 없으면 새 모듈에 같은 꼴로 쓴다 |
| `las_k1_rem_chrono_rows.py:43` | 지형 도우미만(`base_case`, `level_argv`) | 고치지 않는다(REM 재현 정의 유지) |
| `d1_chrono_rows.py:101,160,164`, `v5_stage3_las_rows.py:108` | 쓰지 않는다 | 이 규칙 밖(436.8·D-1 Chrono 재개 규칙에서 "새 태그 재실행"으로 정함) |
| `u3_judge.py:70,72`, `u3_reuse.py:122,235` | 쓰지 않는다 | 이 규칙 밖(U-3·U-6는 436.8). 쓰려면 그 규칙 개정판 |
| `fb_judge.py`, `las_rev_judge.py`, `las_revA_judge.py`, `k1_judge.py`, `las_k1_*_judge.py`, `p3_hash_check.py`, `p3_chrono_check.py` | **판정에 쓰지 않는다** | 봉인·옛 결과 전용, 고치지 않는다. 필요한 함수(`pair_violations`, 정체성 검사)는 **복사**하고 원본 파일 sha를 새 도구 docstring·출력에 적는다 |
| `las_rev_targeted.py:33-34`(`controller_tag`가 `final_C4G2_LAS`/`final_C4G2_P3_LAS`가 아니면 묶음을 멈춤, 재감사 F-5) | 쓰지 않는다 | 크게 실패(새 태그 줄을 만들면 즉시 멈춤). 고치지 않는다(A안 원판의 원판 실행 도구, 옛 결과 전용). 새 실행 도구는 이 파일을 import해도 그 묶음 실행 경로는 부르지 않는다 |
| `v5_options.EXTEND_START_TAGS`·`j_p3_inputs.is_p3_expected`·`v5_rerun:423`·`u3_reuse:235`·`chrono_t45_replay:833` | 하네스 d1 항목 계산이 앞의 둘을 쓴다 | W-1 수정(사용자 결정 (a): ③ 판정을 `_K1`·`_LAS`를 벗긴 기준 태그로)이 **실행 전 조건**이다(11.5). 실행 전 시험: VB 새 태그 줄에서 `p3_expected` 참, V0 새 태그 줄에서 거짓 |
| `las_targeted._turn_preset_las_off`(재감사 F-7, 관문도 끄도록 python-expert 구현 중) | 쓰지 않는다 | 이 규칙의 행은 이 함수를 부르지 않는다. 그래도 같은 모듈을 import하는 도구가 있고 코드 sha가 기록되므로 **실행 전 조건**으로 둔다(11.5) |
| 조합 태그 `final_C4G2_K1`·`final_C4G2_P3_K1`(재감사 F-6) | 쓰지 않는다(2절) | run_S9 choices에 더하지 않아도 된다. run_S9는 `--las-off`와 `--las-candidate`를 함께 주면 종료 2 |

### 11.2 cad-expert (Chrono)

1. `run_S9.py level --las-candidate {P0,P5r4}`
   - 없으면 기존 동작 그대로(P0와 비트 같음). `P0`은 덮어쓰지 않고 기록만 한다.
   - 순서: 프리셋 → (기존 단계) → `--expect-controller` 점검(프리셋이 새 태그 기대값인지, `_LAS_EXPECTATIONS` β 3.5 포함) → 후보 적용(`replace(..., light_leg_fraction_of_F_min=4.5, end_ramp_periods=4)`) → **후보 기대값 점검**(만든 제어기의 `liftoff_approach_slow` 전체가 2절 표와 같은지; 다르면 종료 2).
     - 이유: `_LAS_EXPECTATIONS`는 β 3.5를 고정하므로 후보 적용 뒤에 같은 점검을 하면 항상 거부된다. 프리셋 점검과 후보 점검을 나눈다.
   - `c2_setup.las_candidate`(`requested`, `settings`)를 기록한다. 태그는 바꾸지 않는다.
   - `--las-off`와 함께 주면 종료 2. `--k1-forced-block first`와 함께 주면 종료 2.
2. `04_scripts/02_chrono/las_p5r4_k1_chrono_rows.py` + `s9_batch` 등록(`V5-LAS-P5R4-K1`): 4.3절 12행, 행 키 `case`, `p5k_id`, `las_candidate`, `pair_case`, `v5_setting`, `role` `judge`, `start_env`, `planned_pool`, `est_pool_s`. `argv_check`(짝 argv 차이 하나, 고정값 표, 새 태그 기대 통과, 후보 점검 통과, `--k1-order-gate` 없음).
3. 단위 시험 `05_tests/unit/test_las_p5r4_k1_chrono_rows.py`(시뮬레이션 없음): 12행, 짝 차이, 태그, C3·C4 180 s, `--las-candidate P0`와 무인자의 config 비트 동일.

### 11.3 python-expert (하네스·판정 도구)

1. `04_scripts/04_hydraulic/coupled/las_p5r4k1_targeted.py`: 묶음 Z-0·Z-A·Z-T·Z-S·Z-C·Z-X, 팔 ref/cand(2절), 프리셋 점검(b0 + 관문 참 + $N_r$ 0, `fb_targeted.check_preset_las`에 관문 점검을 더한 새 함수), K1 토큰 없음, 5.1 기록, 목록 sha 대조(부록 A), 앞 묶음 정체성 검사(같은 폴더 안), `rev.attempt`·`resumed`, 출력 폴더 `v5/las/p5r4k1/`. 봉인 도구(`las_revA_targeted.py` 등)는 고치지 않는다.
2. `06_analysis/02_control/verif_matrix/scripts/las_p5r4k1_judge.py`(하네스, 표준 라이브러리만): 4.4 비트 예측, 6.1·6.2, 3절, 8절 상태, 기록 6.4, 전체 자리 출력, 잠정 등급·`k10: null`, 종료 0 통과·1 미달/undecidable·2 stop·3 도구 오류.
3. `06_analysis/02_control/verif_matrix/scripts/las_p5r4k1_chrono_judge.py`: `prelaunch`·`postrun`·`judge`(REM 도구 꼴, 정체성 코드는 복사), BT-C(npz 배열 내용 해시, C3는 t ≤ 128 s 구간), 6.3, 9절 K-0~K-9.
4. 단위 시험: 상태 순서, `PAIR_DIVERGE`(전제 참·해시 다름 → stop, 전제 거짓·해시 다름 → 기록만), CK-1(`R4_LOST`·`R4_GAINED`), $I$ 키 누락 → undecidable, `LATE_LOC_P32` 예외, 관측 요건, $\mathcal{P}$ 빈 집합 두 경우, 사건 이름 정확 일치(`_SKIPPED` 함정), 하네스 팔의 관문 실효 값을 실행 제어기 meta에서 읽음.
5. 전환 후 감사 R-5 권고(`pre_*` 러너 관문 False subprocess 시험)는 이 규칙의 전제는 아니지만, 같은 작업 브랜치에서 하면 sha 기록에 들어간다.
6. (16절) 실행 도구는 묶음이 끝날 때 **일반 텍스트 한 줄 `errors N`**(JSON 안의 `"errors": N`만으로는 `log_errors.py` 기본 패턴에 걸리지 않는다)을 찍고, N > 0이면 0이 아닌 코드로 끝난다(`fb_targeted.main`의 `return 1` 꼴 유지). 두 판정 도구는 16.6 우선순위를 공통 함수 하나로 적용하고, 목록 출력에 상한을 두지 않는다(두면 `truncated`와 원래 수). 단위 시험에 우선순위 3경우(실패만 / 판정 불가만 / 둘 다)를 더한다.
7. (16.2) G-S 건조 실행 목록 생성기: 16.2 규칙으로 하네스 건조 줄 목록과 Chrono 건조 행 목록을 만들고 목록 sha256을 출력한다. 건조 실행 검사기는 오류 수·필드 존재·파일 존재만 출력하고 판정 값(힘·행정·시각·해시 값)은 출력하지 않는다.

### 11.4 control-expert

- 경로 2 두 스크립트를 합성 줄로 맞춘 뒤 sha를 넘긴다(10.2).
- 봉인 전: 부록 A 목록 sha 재계산 확인.

### 11.5 실행 전 조건 (모두 참이어야 Z-0을 시작한다. 실행 전 감사가 하나씩 확인한다)

| # | 조건 | 담당 | 근거 |
|---|---|---|---|
| E-1 | 이 규칙 봉인(`.sha256`), `.gitattributes` 두 줄 | 메인 세션 | 머리, S-1 |
| E-2 | **W-1 수정 병합**: ③ 판정(`EXTEND_START_TAGS` 소비자 4곳)을 기준 태그로 바꾸고, LAS on/off × 관문 on/off × ③ on/off 매개변수 시험으로 고정 | python-expert | 전환 후 감사 W-1, 사용자 결정 (a) |
| E-3 | **F-7 수정 병합**: `las_targeted._turn_preset_las_off`가 관문도 끈다(gate False 되돌림), 해시 재현 시험 통과 | python-expert(구현 중) | 재감사 F-7, 전환 후 감사 메인 세션 덧붙임 |
| E-4 | 11.2·11.3 구현과 단위 시험 병합, 실행 HEAD에서 단위 시험 통과 | cad-expert, python-expert | 11.2·11.3 |
| E-5 | 행 목록(하네스 묶음 계획·Chrono `s9_batch list V5-LAS-P5R4-K1`)에 `--las-off`, `--k1-order-gate`, `--k1-forced-block`, 조합 태그 0건. Chrono `check-sources`에서 12행 모두 `--expect-controller`가 `_LAS_K1` 태그 | 메인 세션, 감사 | 2절, K-3, K-7, 재감사 F-6 |
| E-6 | 경로 2 두 스크립트 sha를 메인 세션이 받음 | control-expert | 10.2 |
| E-7 | 실행 전 감사(verif-protocol-auditor `[시점] 실행 전`) 차단 0, 리포트 원문 저장 | 메인 세션 | K-0 |
| E-8 | **G-S 건조 실행 통과**(16.2): 옵션 팔 × 단계마다 1줄·1행, 오류 0, 판정 도구가 읽을 행 파일·필드가 모두 있음 | 메인 세션(실행), python-expert·cad-expert(생성기·검사기) | 16.2, K-2 판정 후 감사 "kt × L1eq", V-7 |
| E-9 | 옵션 × 단계 겹침 표(16.1)의 "확인 방법" 칸을 실행 HEAD에서 모두 확인(거부 문구 grep 포함) | 실행 전 감사 | 16.1 |
| E-10 | 실행 전 기록·manifest의 자리표시 목록과 채울 시점·책임자(16.4 표)가 prelaunch에 있음 | 메인 세션 | 16.4 |

- E-2·E-3이 늦어지면 이 규칙의 실행을 기다린다. 이 규칙만을 위해 두 조건을 빼려면 새 판이 필요하다.

### 11.6 메인 세션

- `.gitattributes` 두 줄(머리 인용 블록), 봉인(`.sha256`), 실행 전 감사(verif-protocol-auditor `[시점] 실행 전`, 리포트 원문 저장 → K-0), compute-scheduler-expert 배치표·예약, long-running-task-monitor 점검, prelaunch~postrun 동안 main checkout 커밋·병합 금지.
- (16절) G-S 건조 실행(E-8), 실행 중 점검의 단계 로그 오류 수(16.3), 자리표시 채움과 판정 전 점검(16.4).

## 12. 비용과 순서

### 12.1 하네스 (가정: 저장 `wall_s` 평균을 단가로 씀)

| 묶음 | 줄 | 단가 [s/줄] | CPU [s] |
|---|---|---|---|
| Z-0 | 6 | 110(R-0 단가 가정) | 660 |
| Z-A | 102 | 86(R-0A 4,654/54, R-Q 4,087/48) | 8,700 |
| Z-T | 384 | 92(R-T 17,695/192) | 35,300 |
| Z-S | 60 | 108(R-S 3,249/30) | 6,500 |
| Z-C | 912 | 124(S-C 56,759/456) | 113,500 |
| Z-X | ≤ 10 | 110 | ≤ 1,100 |
| 합 | ≤ 1,474 | — | 약 165,800(약 46 CPU-h) |

- 벽시계: 기계 전체(P 8 + E 12, 단일 스레드 작업) 동시 배율을 앞 묶음 실측처럼 약 11배로 보면 **약 4.2 h**, E만 쓰면 약 6~7 h(가정). Z-C가 68 %다.
- Z-C는 912줄 전부 돈다(사용자 결정 Q-1 A). ε 0만으로 줄이는 안(약 30 CPU-h)은 고르지 않았다.

### 12.2 Chrono (가정)

| 행 | 단가 근거 | 행당 [s] |
|---|---|---|
| A1~A6(혼합 지형 160 s) | `las_chrono_rows.MIXED_US_PER_STEP` P 2,800 µs/step × 168 s / 1e-4 × VB 1.2 = 5,600(**미측정 가정**, 혼합 지형 폐루프 실측 없음) | 5,600 |
| B1·B2(G6 J1@FL 200 s) | S-Ch(G6 J2@FL 200 s, P 2행 동시) 5,628~5,658 s × 4행 동시 1.2 | 6,800 |
| C1·C2(J2 ×1.0 120 s) | REM R1·R7 6,230~6,560 s(P 4행 동시) | 6,500 |
| C3·C4(J2 ×1.1 180 s) | REM R4·R8 6,083~6,668 s × 180/120 | 9,700 |

- 12행 직렬 합 약 79,600 s(22 h). **P만 4행씩**: 3묶음(가장 긴 C3·C4·B를 먼저) 약 6 h. **P 4 + E 3**(E 약 1.5배, 짝은 같은 풀 종류): 약 4.5 h. 12행 전부 돈다(사용자 결정 Q-2 A).
- 15분 넘게 걸리므로 compute-scheduler-expert 배치표·`reserve.py` 예약, long-running-task-monitor 점검이 필요하다.

### 12.3 D8x와의 순서 (사용자 결정 Q-6 A: D8x Chrono 먼저)

D8x는 E코어 하네스 R-a·R-c(약 3 h) → 관문 G1 → Chrono 19행(P, 약 1.5~2 h)이 이미 사용자 결정으로 정해져 있다. P코어를 다투는 것은 두 Chrono 묶음이다.

1. 지금(계산 없음): 이 규칙 봉인, 구현(11절), 실행 전 조건(11.5), 경로 2 고정, 실행 전 감사. D8x는 그대로 진행.
2. D8x E 하네스(약 3 h) 동안: P에서 이 규칙의 Z-0·Z-A(108줄, 약 15분)를 먼저 돌려 비트 시험을 끝낸다. 이어서 Z-T·Z-S(444줄)를 P에서.
3. D8x Chrono 19행이 P를 쓰는 동안(약 2 h): Z-C를 E에서(D8x E 하네스가 끝난 뒤).
4. D8x Chrono가 끝나고 하네스 판정이 `통과`면: 이 규칙의 Chrono 12행을 P(+E)에서 약 4.5~6 h.
5. 모든 것이 이어지면 시작부터 약 10~12 h(가정). 정확한 묶음·마스크는 compute-scheduler-expert가 정한다.

## 13. 판정서와 공개 체크리스트

- 판정서: `06_analysis/02_control/verif_matrix/las_p5r4_k1_judgement.md`.
- 적을 것: K1 원판 8절 체크리스트 1~11 전부, 이 규칙 1절 공개 원문, 비트 예측 결과(4.4), 묶음별 상태, 짝별 위반, $\mathcal{P}$ 크기·예외 짝, `PAIR_DIVERGE`·`PAIR_CMD_DIFF`, CK-1 분류, Z-C 표본 안(19키)/밖(437키) 분리 표, Chrono 관측 요건, 사전 예측 대조(7절), 실행 전 감사 원문 경로·sha, 두 경로 sha와 K-10 대조, REM F2 알려진 한계가 판정 행에서 나타났는지(`R4_LOST` 0이면 "관측 안 됨"을 그대로 적음). 16절 관문 결과: G-S 목록 sha·통과 여부·표본 밖 G-S 키 목록, 단계 로그 오류 수(`log_errors.py` 출력 경로), 자리표시 점검 결과와 채운 값(`{BATCH_CHRONO}`, `{JUDGE_COMMIT}` 등), 16.1 표 확인 결과, 16.6 우선순위로 정한 층별 상태.

## 14. 한계

- 하네스 Z-A·Z-T·Z-S는 이미 본 키의 재실행이다. 하네스 표본 밖 근거는 Z-C 437키뿐이다.
- Chrono는 결정론 1위상 표본이다. 하네스에서 이륙 첫 골이 위상에 따라 두 무리로 갈렸다(A안 rev2 R2-0). Chrono 3짝이 그 분포를 덮지 않는다.
- 잡음 등급 L1~L3, U-3·U-6, 경사 연약 지면, 오거 중·하단 ×1.1, 운용 중량 +20 %, S1 패치, t180은 보지 않는다(436.8 재개에서 본다).
- 혼합 지형 Chrono 비용은 미측정 가정이다.
- K1의 알려진 한계(REM F2)는 판정 행 C1~C4에서 `R4_LOST`가 0이면 여전히 판정 행에서 관측되지 않은 경로로 남는다.

## 15. 결과 전 사용자 결정 기록 (2026-11-10, 초안 15절 답)

모두 결과 전이다(이 규칙의 대상 행 0행). 고른 안은 본문에 반영했다.

| # | 질문 | 고른 안 | 반영한 곳 |
|---|---|---|---|
| Q-1 | Z-C 범위 | A: 912줄(S-C 456 전체 키 × 두 팔). 버린 안: ε 0만, 넣지 않음 | 4.2, 12.1 |
| Q-2 | Chrono 범위 | A: 12행. 버린 안: 8행(Kc3·V0 혼합 지형 뺌) | 4.3, 12.2 |
| Q-3 | Chrono C-S | A: 모든 짝 1 mm. 버린 안: B 짝만 1 mm. **알려진 위험**: C 짝은 연약 지면 침하로 수 mm 차가 날 수 있다(P-12, 확신 50 %) | 6.3 CC-S |
| Q-4 | G-2′C | A: 절대 11.414589 kN. 버린 안: 상대 ref − 0.3 kN | 6.3 |
| Q-5 | Chrono 시작 | A: 하네스 `통과` 뒤 | 4.3, 8.2 S-6 |
| Q-6 | D8x와의 순서 | A: D8x Chrono 먼저 | 12.3 |
| Q-7 | C3·C4 폐루프 | A: 180 s, BT-C는 앞 120 s(t ≤ 128 s) | 4.3, 4.4 |
| Q-8 | PAIR_DIVERGE | A: 조건부(stop) | 3절 |

- 재감사(`las_k1_adopt_rev1_d8x_rev3_audit.md`) 반영: F-5 → 11.1 표 `las_rev_targeted.py` 행, F-6 → 2절·K-3·11.5 E-5, F-7 → 11.1 표·11.5 E-3, W-1 → 11.1 표·11.5 E-2.

## 16. K-2 `_TCL` 재발 방지 (2026-11-11 사용자 승인, 결과 전)

- 출처: K-2 판정 후 감사 `06_analysis/02_control/k2/judgement/k2_post_audit.md`("kt × L1eq 충돌" 절, E·I 실행 전 수정 항목, C3·C4)와 판정서 `k2_judgement.md` 7.1절. 이 절은 대상 행·판정 항목·문턱을 바꾸지 않는다. 실행 전 관문·점검·우선순위 문장만 더한다.

| # | 재발 방지 항목 | 이 규칙의 자리 |
|---|---|---|
| 1 | 옵션·감도가 대상 행 단계가 이미 바꾸는 파라미터와 겹치는지 표 | 16.1, 11.5 E-9 |
| 2 | G-S "옵션 팔 × 단계마다 1행 건조 실행(오류 0)" | 16.2, 11.5 E-8 |
| 3 | 실행 중 점검·판정 전 관문 "단계 로그 `errors 0`"(`log_errors.py`) | 16.3, 8.2 S-9·S-10, 11.3 항목 6 |
| 4 | 판정 전 자리표시 점검(`placeholder_scan.py`), 채울 시점·책임자 | 16.4, 8.2 S-10, 11.5 E-10 |
| 5 | env "없다" 조항 → "없거나 기본값 X", 실행기가 스스로 넣는 env | 16.5, 9절 K-6 |
| 6 | 관문 우선순위 "판정 불가 > 실패 > 통과" | 16.6, 8.1, 10.2 |
| 7 | Chrono 배치가 판정 도구가 읽을 행 파일을 실제로 쓰는지 G-S에서 확인 | 16.2 (나) |

### 16.1 옵션 × 단계 겹침 표

- 이 규칙의 옵션은 팔(ref/cand)을 가르는 LAS-b 후보 덮어쓰기 하나다. 아래 표는 그 옵션과, 대상 행의 단계(묶음·계열·인자)가 이미 바꾸는 파라미터를 대조한다. 확인 방법 칸은 실행 전 감사가 실행 HEAD에서 확인한다(E-9). 줄 번호는 봉인 당시(master `da5e01b`) 참고값이고, 감사는 문구 grep으로 찾는다.

| # | 옵션·단계 | 바꾸는 것 | 같은 것을 바꾸는 다른 경로 | 겹침 판단 | 합성 규칙 | 확인 방법 |
|---|---|---|---|---|---|---|
| O-1 | cand LAS-b 후보(하네스 `replace` 1회, Chrono `--las-candidate P5r4`) | `liftoff_approach_slow.light_leg_fraction_of_F_min`(β 3.5 → 4.5), `end_ramp_periods`(0 → 4) | `las_rev_targeted`·`las_revA_targeted`의 후보 적용, `t4h_replay`·`chrono_t45_replay`의 LAS 설정 재구성, `--las-off`·`LAS_OFF_PRESET`·`pre_*_preset_runner.py` | 이 규칙 행에서는 O-1 하나만 쓴다(2절 두 번 적용 금지) → 설정 겹침 0 | 덮어쓰기 전 b0 확인 → 한 번 적용 → 후보 기대값 점검(11.2) | K-5·K-7, run_S9 `--las-candidate`+`--las-off` 종료 2(11.2), 새 실행 도구가 옛 후보 적용 함수를 부르지 않는지 grep |
| O-2 | Z-A 격자 단계(R-0A의 LT·LH, R-Q의 LQ) | `las_phase_diag.install`이 `C2Controller._apply_output_ramp`(touch budget 위상 격자)와, 기록 켬이면 `_apply_liftoff_approach_slow`(기록 감싸기)를 **클래스 수준**에서 감싼다 | O-1(같은 LAS-b 메서드의 설정) | 메서드는 겹치고 설정은 겹치지 않는다. 감싸기는 기록·출력 램프만 바꾼다(A안 rev2와 같은 합성) | 격자 훅은 작업마다 spawn 워커에서 1회 설치. 후보 설정은 O-1 그대로 | BT-A 102/102(합성 정합의 판정), `already installed in this process`·`not the original` 거부 문구 grep, G-S 격자 종류마다 1줄 |
| O-3 | 하네스 ε 0.002 | `run_v5._install_approach_scale`이 `harness_flow.FlowLimiter.limit`을 첫 접촉 전 ×(1−ε)로 감싼다(플랜트) | 없음(제어기 설정 아님) | 겹침 없음. 같은 프로세스에서 두 번 감싸면 (1−ε)²가 되므로 프로세스 재사용 여부가 조건이다 | 작업마다 spawn 워커 `maxtasksperchild=1` | `maxtasksperchild=1` grep(새 실행 도구 포함), G-S ε ≠ 0 1줄 |
| O-4 | VB 설정(③ 시작 연장, `v5_options`) | 시작 연장 플랜트·태그 | LAS-b·관문 설정을 바꾸지 않는다 | 겹침 없음 | ③ 판정은 `is_extend_start_tag`(기준 태그, E-2) | E-2 시험(VB 새 태그 `p3_expected` 참, V0 거짓) |
| O-5 | K1 관문(프리셋 참) | `slope_clearance_margin.flat_soil_margin_order_gate` | 하네스 `k1_targeted`(K1on 토큰), `ideal_sensor_targeted`(K1 끔 팔), `d8x_record`, Chrono `--k1-order-gate`, `LAS_OFF_PRESET`(관문 거짓) | 이 규칙 행에서는 프리셋만 → 겹침 0 | 프리셋만 | K-4, E-5 |
| O-6 | Chrono A3·A4 Kc3(`--crawler-kn-scale 3`) | 크롤러 구 강성·감쇠 ×3(플랜트) | — | 제어기 설정과 겹침 없음. **인자 조건**: `--rigid-base`가 없으면 run_S9가 거부한다(`--crawler-kn-scale needs --rigid-base`). A행은 `--rigid-base FR` | A행에서만 | 거부 문구 grep, G-S A-Kc3 1행 |
| O-7 | Chrono B1·B2 패치(`--soil-patch`, J1@FL) | 패치 토양(플랜트) | `--rigid-base`와 배타(`--rigid-base replaces --crawler-grid / --soil-patch`) | 인자 배타. B행에 `--rigid-base` 없음 | — | 거부 문구 grep, G-S B 1행 |
| O-8 | Chrono C3·C4 `--mass-scale 1.1` | 상부체 질량·관성(플랜트), W_ref 기록 | 제어기 $F_{min}$은 YAML 상수(`params.control.F_min_cylinder_N`)라 β $F_{min}$은 바뀌지 않는다. LAS-b 합 조건은 측정 Ŵ 기준이라 두 팔이 같다 | 겹침 없음 | REM R4·R8과 같은 조건 | result.json `mass_scale` 블록, G-S C×1.1 1행 |
| O-9 | Z-X DONE 기록 켬 | 기록만 | — | 겹침 없음 | — | BT-X |
| O-10 | K-2 `_TCL` 터치 크리프 래치 | 쓰지 않음(2절 끝) | K-2 `_TCL` 실행 도구 | 쓰지 않으므로 겹침 0 | — | K-3·K-4 |

- 표에 없는 옵션·단계가 행 목록에 있으면 실행하지 않는다(새 판).

### 16.2 G-S 건조 실행 (실행 전 관문, E-8)

- 시점: 11.5 E-1~E-7·E-9·E-10이 참이 된 뒤, Z-0 전에. 실행 HEAD = prelaunch HEAD. 출력은 본 실행 폴더와 다른 곳(하네스 `v5/las/p5r4k1/gs/`, Chrono 배치 이름 `V5-LAS-P5R4-K1-GS`)에 쓴다. G-S 줄·행은 판정에 쓰지 않는다.
- **(가) 하네스**: 묶음 × 팔 × 단계마다 1줄. 단계 = (`d1.key`의 계열 토큰, 격자 행은 줄 이름의 종류 `LT`·`LH`·`LQ`) × setting(VB/V0) × (ε = 0 / ε ≠ 0) 가운데 그 묶음에 있는 조합. 각 단계의 키는 그 단계 키 목록에서 **R-S와 겹치는 19키(표본 안)가 있으면 그중 정렬 첫 키, 없으면 정렬 첫 키**로 고른다. Z-X는 Z-T 첫 키의 ref + DONE 기록 켬 1줄. 목록은 11.3 항목 7 생성기로 만들고 목록 sha256을 prelaunch에 적는다.
  - 통과 조건: 줄 수 = 목록 수, `error` 키 줄 0, 단계 로그 `errors 0`(16.3), 실행 도구 종료 0, 하네스 판정 도구가 읽는 필드(5.1·6.1·6.2·6.4)가 모두 키로 있다(값은 None이어도 된다), K-3·K-4·K-5 참.
  - G-S 줄과 같은 키의 본 실행 줄은 `commands_sha256`이 같아야 한다(스레드 1·같은 HEAD). 판정 도구가 "같음/다름"만 출력하고, 다르면 S-3대로 `stop`.
  - R-S 겹침 키가 없는 단계의 Z-C cand G-S 줄은 표본 밖 키다. 그 줄의 값(힘·행정·시각·사건·해시 값)은 판정 전까지 아무도 읽지 않고, 검사기는 위 통과 조건만 출력한다. 판정서 1.1 공개 표에 그 키 목록을 적는다.
- **(나) Chrono**: 단계 = A-Kc1-VB, A-Kc3-VB, A-Kc1-V0, B, C×1.0, C×1.1의 6개 × 팔 2 = 12행. argv는 4.3절 본 행 그대로이고 `--duration`만 짧게 한다(기본 10 s. 짧은 루프에서 run_S9 사후 분석이 실패하면 실패하지 않는 가장 짧은 값을 구현자가 정하고 이유와 함께 prelaunch에 적는다). 배치표는 compute-scheduler-expert.
  - 통과 조건(K-2 V-7 결함 대응): 12행 모두 `progress.log` END `rc=0`, `<case>/result.json`, `<case>/controller_commands.npz`(배열 `t_s`·`issued_u_m_s`), `batch.json`의 행 항목이 **실제로 있다**. Chrono 판정 도구 `prelaunch`·`judge`를 G-S 배치에 "필드 점검" 모드로 돌려 5.2·6.3·9절이 읽는 키 경로(`p3b.checks`의 $I$ 키 이름, `p3b.P3-3_leg_force.F_min_after_N`·`F_min_transient_N`, `p3b.P3-5_clearance_stroke.s_motor_max_m`, `P3-6_ready.t_ready_after_loop_start_s`, `controller_meta.liftoff_approach_slow`·`slope_clearance_margin.order_gate`·`soil.mode_starts`, `c2_setup.las_candidate`, `hull_hook`, `placement`)가 모두 있음을 확인한다. 값은 출력하지 않는다.
  - 판정 도구가 읽는 행 파일 경로를 manifest의 자리표시로 두지 않는다. 도구는 batch 폴더 하나를 인자로 받고 그 아래 경로를 스스로 만든다(16.4).
- G-S 실패: 원인을 고친 뒤 G-S부터 다시 한다. 고친 것이 코드면 prelaunch HEAD가 바뀌므로 실행 전 감사를 다시 받는다.
- 비용(가정): 하네스 단계 수 × 약 110 s(약 1~4 CPU-h), Chrono 12행 × 약 10~15분(P 4행 동시면 약 40분).

### 16.3 단계 로그 오류 수 (실행 중 점검·판정 전 관문)

- 도구: `C:\Users\jinbeom\.claude\tools\verif\log_errors.py`(python-dev `python.exe -I -B`).
- 하네스: 실행 도구가 묶음 끝에 찍는 일반 텍스트 `errors N`(11.3 항목 6)을 본다. `log_errors.py <러너 로그 폴더> --require-line`. `no_errors_line`(줄 없음)은 "오류 0"이 아니다(warning → 실행 중이면 확인, 판정 전이면 S-10).
- Chrono: `log_errors.py <batch 폴더>\progress.log --pattern "\brc=(\d+)" --require-line`(END 줄의 `rc`가 0이 아니면 발견).
- 실행 중 점검: long-running-task-monitor 점검마다 위 두 명령 결과(`steps_with_errors`, `error_rows_total`)를 보고에 넣는다. N > 0이면 S-9.
- 판정 전 관문: 모든 묶음·G-S에서 마지막 값 N = 0, 또는 10.1 재실행 뒤 남은 오류 0(재실행 줄 `rev.attempt` 2 공개). 아니면 S-10.
- 종료 코드만으로 오류 없음을 판단하지 않는다(K-2: `errors 48`인데 rc 0).

### 16.4 자리표시 (판정 전 점검)

| 자리 | 놓이는 곳 | 채우는 때 | 책임 |
|---|---|---|---|
| `{RUN_HEAD}` | prelaunch 기록·manifest | prelaunch 작성 때(실행 전 감사 전) | 메인 세션 |
| `{BATCH_GS}` | 같음 | G-S Chrono 시작 직후, 첫 점검 전 | 메인 세션 |
| `{BATCH_CHRONO}` | 같음(`07_results/S9/batch_V5-LAS-P5R4-K1_<시각>/`) | Chrono 본 배치 시작 직후, 첫 점검 전(시작 뒤 15분 안) | 메인 세션 |
| `{POSTRUN_HEAD}` | postrun 기록 | postrun 때 | 메인 세션 |
| `{JUDGE_COMMIT}` | prelaunch 판정 절, 판정서 머리 | 판정 도구를 돌리기 직전. 판정 도구 sha를 확인한 커밋을 적는다 | 메인 세션 |

- 위 표에 없는 자리를 만들지 않는다. 명령 틀에 일부러 남기는 자리(`{MASK}`·`{WORKERS}`·`{POOL}` 등)는 prelaunch에 이름을 미리 적고 그 이름만 허용한다.
- 판정 전 점검: `C:\Users\jinbeom\.claude\tools\verif\placeholder_scan.py --repo <main checkout> "<prelaunch 폴더>/*.json" "<prelaunch 폴더>/*.md" --allow <prelaunch에 적은 틀 자리>`에서 `placeholder_unfilled` 0. 기본 패턴 `\{[A-Z][A-Z0-9_]*\}`(숫자 포함)를 쓴다. `\{[A-Z_]+\}`는 `{BATCH_V7}`을 놓친다. 0이 아니면 S-10.
- 판정서에는 채운 값(배치 폴더, `{JUDGE_COMMIT}` 커밋)을 그대로 적는다.

### 16.5 env 조항 ("없거나 기본값" 꼴)

- 판정은 **실효 값**(result.json·batch.json·하네스 줄 기록)으로 한다. env 원문은 기록만 한다. 실행기가 스스로 넣는 값이 있으므로 "없다" 꼴로 쓰지 않는다(K-2: `run_S8C`가 `OUTRIGGER_S8_CRAWLER=yaml`을 스스로 넣음).

| 변수 | 조항 | 실행기가 스스로 넣는 값(봉인 당시 코드) | 실효 값 기록 |
|---|---|---|---|
| `OMP_WAIT_POLICY`(Chrono) | 없거나 `PASSIVE` | run_S9 `setdefault` `PASSIVE`, s9_batch가 자식 env에 넣음 | result.json `placement.omp_wait_policy`, batch `omp_wait_policy` = `PASSIVE` |
| `OUTRIGGER_HULL_HOOK` | 없거나 `fast` | 미설정 = `fast`(`hull_hook.DEFAULT_MODE`) | `hull_hook.mode` = `requested` = `fast`, `fallback_reason` None |
| `OUTRIGGER_HULL_HOOK_DLL` | 없거나 기본 경로(`hull_hook.DLL_PATH`) | — | DLL sha `cec997d7…` |
| `OUTRIGGER_HULL_HOOK_ALLOW_UNVALIDATED` | 없거나 `1`이 아닌 값 | — | 기록 |
| `OUTRIGGER_HULL_HOOK_DUMP`·`_DUMP_EVERY`·`_DUMP_MAX` | 없거나 빈 값 | — | 기록 |
| `OUTRIGGER_PLACEMENT`(Chrono) | 없거나 그 행의 계획 풀 값(미설정 = `pcore`) | s9_batch가 행마다 `pcore`/`ecore`를 넣음 | `placement` 풀 = 계획(K-6) |
| `OPENBLAS_NUM_THREADS`·`MKL_NUM_THREADS`(Chrono) | 없거나 `1` | run_S9 `setdefault` `1` | 기록 |
| `MKL_NUM_THREADS`·`OMP_NUM_THREADS`·`OPENBLAS_NUM_THREADS`·`NUMBA_NUM_THREADS`(하네스) | 실효 `1`(호출자 값과 무관) | 하네스 도구가 `1`로 덮어씀(`fb_targeted.THREAD_VARIABLES` 꼴) | 줄 기록 = `1` |
| `MKL_THREADING_LAYER` | 없거나 `TBB` | `setdefault` `TBB`(dynamics-dev env 변수에도 있음) | 기록 |
| `OUTRIGGER_ROD_SIDE_MECHANICS` | 없거나 `one_sided_parallel` | S6C·S7C·S8C가 넣음. 이 규칙의 행(run_S9·하네스)은 판정에 쓰지 않음 | 기록 |
| 그 밖의 `OUTRIGGER_*` | 기록만. 실행 전 감사가 실행 HEAD에서 `os.environ[`·`setdefault` grep으로 실행기가 넣는 변수를 다시 찾고, 이 표에 없는 것이 판정 경로에 닿으면 실행하지 않는다(새 판) | — | — |

### 16.6 관문 우선순위 (판정 불가 > 실패 > 통과)

- 순서: `stop` > `undecidable`(판정 불가, `incomplete` 포함) > `미달`(실패) > `통과`. 두 경로가 같은 꼴로 적용한다(10.2).
- 층마다 적용한다.
  1. **기준**: 모집단(짝·줄·행)에 `undecidable`인 원소가 하나라도 있으면 그 기준은 `undecidable`이다. 다른 원소에 위반이 있어도 그렇다. 위반 원소는 목록으로 함께 적는다.
  2. **묶음**: 8.1 표대로. 기준 하나라도 `undecidable`이거나 묶음의 E·K 문제가 있으면 `undecidable`. 그렇지 않고 위반이 있으면 `미달`.
  3. **최종**: 묶음 상태들에 같은 순서를 적용한다. 앞 단계 `미달` 때문에 `not_run`인 묶음은 최종을 `undecidable`로 만들지 않는다(최종 = 앞의 `미달`).
- 8.1 "`미달` 즉시 확정"(SK-5)과 S-4는 뒤의 결과로 `미달`을 되돌리지 않고 다음 묶음을 돌리지 않는다는 뜻이다. 같은 묶음 또는 앞 묶음에 `undecidable`이 있으면 등급은 `undecidable`이고, `미달` 항목은 "판정 불가 아래의 위반"으로 참고 기록한다.
- 하네스가 `undecidable`이면 S-6대로 Chrono를 시작하지 않고 묻는다.

## 부록 A. 키 목록과 기준 파일 (봉인 때 다시 계산해 대조)

- 목록 sha256 규약: K1 원판 부록 규약과 같다(전체 키 `rev.key`를 파이썬 기본 문자열 정렬, 각 줄 끝 LF, UTF-8 바이트의 sha256).
- 아래 값은 초안 작성 때 control-expert scratchpad `p5r4k1\key_lists.py`로 계산했다(main checkout 저장 파일, 2026-11-10).

| 묶음 | 기준 파일(main checkout `06_analysis/03_hydraulic/coupled/v5/`) | 파일 sha256 | 키 | 목록 sha256 |
|---|---|---|---|---|
| Z-0 | `las/revA2/revA_R0.jsonl`(6줄) | `04cadd3cdd63372518ee8fcf3620bfef43695f08583a99b7458a0c53b7f777f3` | 6 | `4d1591ba30b686bb6484072c1e63df51130791c2d0cee7106d9ae7d1bc4b6c9e` |
| Z-A(R-0A) | `las/revA2/revA_R0A.jsonl`(54줄) | `28df99076cc309718e9dcfc270fed5d390a111f5ace8ce77ddbc3a3c8b0f14f8` | 2키 × 격자 54점 | 키 `14f89f1f9209114d7e5a2c84f5b45a7d6c650e44ac3de41dd4c93c8733451577`. 격자 점은 줄 이름(`P5r4-LT-…`, `P5r4-LH-…`)으로 짝짓고 도구가 이름 목록 sha를 기록한다 |
| Z-A(R-Q) | `las/revA2/revA_RQ.jsonl`(48줄) | `93ced32cedb57888c37ea06dfbbe966c12c35d858f5b92a543e816f86cf953ca` | 2키 × 격자 48점 | 위와 같음(`P5r4-LQ-…`) |
| Z-T | `las/revA2/revA_RT.jsonl`(192줄, cand 비트 기준) | `c72f7e0882c50d86e565366866526ed55073d8bfef5c9f959b82c0e2885afd54` | 192 | `4160bddfff318f8c13b36652c3203e89a02159b5fd5a624499aa6ef0940fe933` |
| Z-T ref | `las/las_T1.jsonl`(48줄 = 후보 6개 × 8, 그중 `las.candidate` `b0` 8줄)·`las/las_T2.jsonl`(184줄, 모두 `b0`) | T1 `3dee4f6b88e71654debd68b3ef5c5f1a9b01f1dba8fcd731d1355ec219d9a85b`, T2 `2fe6a54aafdc0c3ffbf1991907ee4e1af85761e1bef2e25bef07dd52ab199efb`(2026-11-11 봉인 전 기록) | 192(키는 `las.key`) | `4160bddfff318f8c13b36652c3203e89a02159b5fd5a624499aa6ef0940fe933`(= Z-T, 2026-11-11 확인) |
| Z-S | `las/revA2/revA_RS.jsonl`(30줄, 키 목록) | `7c407b6ee07b001f5504186fa013193ba6a2992516021f263b2bb537de43875d` | 30 | `19c78b49197ac53da5ae50808555c5879aabc90765589ea220830d5588a23950` |
| Z-S 비트 기준 | `las/k1/k1_YS.jsonl`(60줄 = P0 30 + P5r4 30) | `a31153a64ed9cbdf7410082e8dbda81b79e6d607c0a238d510ac34c0c9333ac6` | 30 × 2 | Z-S와 같아야 한다 |
| Z-C | `soil_defer/s2d_SC.jsonl`(456줄) | `70e91ec1234d56a918af1b4fc053c3175f0f14ab41e2b5f334890f7dc6cb08aa` | 456 | `fe6c9c46f2c799ee440d8a2a5d99d88099c51586297afd01d7201a52d26389d9` |
| Z-C 중 R4 평가 165키(ref 비트 기준) | `las/k1/k1_YP.jsonl`(206줄) | `0d985d5624f0fbb0219ca50d1c839b7db639011d6c2ab14fa9d84cfd197fc2c3` | 165 | `dc1e65d49bc0ea34fd04fdb7ba4eeceb7fc576ee15de9658dbe26927598b753b`(K1 원판 부록 A) |
| Z-C 중 R-S와 겹치지 않는 키(표본 밖) | — | — | 437 | `f20bb9e0b1b570660fd15c2a33a2abd66308efce10e1aeb3185cc178956edea7` |
| Z-X 참고(옛 R-X) | `las/revA2/revA_RX.jsonl`(4줄) | `04f7a4dcf435b66934a811af6cee4cb5fa657f8e897f4a503321dd126f4b0d78` | 4 | `bdad17c7c77abae2eb47c8b366d09d1882fe934fecd112b759040b894f79adfd` |

- 봉인 전 재계산(2026-11-11, control-expert scratchpad `p5k_seal\recheck_lists.py`·`yp_arms.py`, 식별 필드만 읽음): 위 표의 파일 sha256·줄 수·목록 sha256이 모두 같았다. Z-C 중 R4 평가 165키는 `k1.sub_bundle` = `Y-Pa` 줄이다(목록 sha `dc1e65d4…` 일치, Y-Pb 40키는 `ef6c010d…`).
- `k1_YP.jsonl`은 206줄이다(Y-Pa 165 + Y-Pb 40 + 오류 줄 1).
  - 오류 줄은 100번째 줄이다. 최상위 키는 `error`, `job`, `rev`, `tb`, `wall_s`뿐이고 `rev.key`는 `D1|H-S-1|S1|M|flat|K1|V0|e0.002`다. `error`는 `install: TimeoutExpired(['git', '-C', 'C:\\workspace\\outrigger_control', 'rev-parse', 'HEAD'], 60)`(설치 단계 git 조회 시간 초과, 인프라 원인)이다.
  - 같은 키의 줄이 105번째에 하나 더 있다(재실행 줄로 본다. 그 줄의 값은 읽지 않았다).
  - 도구 규칙: 비트 기준은 `error` 키가 없고 K1on·`las_candidate` P0인 줄만 쓴다. 같은 전체 키에 정상 줄이 정확히 1개여야 한다(아니면 S-3 stop). 오류 줄 수와 키를 출력한다.
- Chrono BT-C 기준: main checkout `07_results/S9/batch_V5-LAS-K1-REM_20261109_235554/`의 `REM_J2_B_top_Fs4_VB_gateon/controller_commands.npz`(`ebf86d1d…b559`), `REM_J2_B_top_Fs4_m1p1_VB_gateon/controller_commands.npz`(`97aace61…c8aa`). gateoff R1·R4 파일 sha도 각각 같다.
