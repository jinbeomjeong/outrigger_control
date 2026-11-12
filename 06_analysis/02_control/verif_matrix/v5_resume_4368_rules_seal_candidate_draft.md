# v5 재개 검증 436.8 판정 규칙 (제어기 `final_C4G2_LAS_K1`) — 봉인 후보 초안

- **상태: 봉인 후보 초안(미봉인).** 이 파일은 `.sha256`이 없으므로 실행·판정에 쓰지 않는다. 봉인은 메인 세션이 하고, 봉인 때 바꾸는 것은 끝의 "봉인 때 바꿀 머리 줄" 절에 적힌 세 줄과 파일 이름뿐이다.
- 작성: control-expert, 2026-11-13. 기준 master `3d41083`(작성 시점 HEAD). 입력 초안 `v5_resume_4368_plan_draft.md`(sha256 `141e4958f39b7c74…`, 이 폴더).
- **시점: 436.8의 어떤 실행 결과도 없을 때.** 436.8 묶음(0단계 T-3K 포함)은 한 줄도 돌지 않았다. 이 규칙을 쓰려고 읽은 것은 1절에 모두 적었다.
- 이 문서 하나가 다음 셋을 겸한다(판이 따로 없다): (가) v5 기준 개정 13(`v5_criteria.md` 계열, 2절 이하 "개정 13 몫"), (나) `u3_u6_rerun_rules` rev3(4.2절·7.1절 H-3·H-4 행, "rev3 몫"), (다) O-C5 기록 행 규칙(5.4절·7.4절). 앞 판들은 고치지 않는다. 이 문서와 앞 판이 다르면 이 문서가 맞고, 이 문서가 말하지 않는 것은 앞 판 그대로다.

## 0. 목적과 판의 성격

1. v5 확정 제어기 `final_C4G2_LAS_K1`(VB `final_C4G2_P3_LAS_K1`, ABL `ABL_LAS_K1`)로 v5 검증 묶음 전체를 **한 커밋에서 한 번만** 다시 돌려 v5 판정을 낸다(사용자 결정 2026-11-10 "436.8은 확정 제어기로 한 번만").
2. LAS-b 전환(명세 436)과 K1 전환(명세 437) 뒤 그림자·재사용으로 덮지 못한 묶음을 모두 채운다.
3. 논문 2.8용 G1 열린 루프 새 행 3개(VB 비례 1, 속도 낮춤 VB·V0 2), 운용 시작 조건 안 확인 기록 행 O-C5 **2개**(A3 조건 VB + V0 짝, 사용자 결정 2026-11-12 R-3)를 더한다.
4. **숫자 문턱을 새로 만들지 않는다.** 새로 넣는 것은 규칙 문장(태그·옵션·K1 분류·재사용·시작 조건 밖 처리·O-C5 멈춤·두 경로)뿐이다. 7.6절에 이 문서가 쓰는 숫자 전부를 적었다.
5. LAS-c 재설계(`06_analysis/02_control/las_redesign/las_redesign_v1_draft.md`)는 v5 뒤 과제이고 436.8 범위 밖이다. 436.8에는 LAS-c 후보·진단 probe·표본 밖 판정 행(O-H*, O-C1~O-C4)을 넣지 않는다(사용자 결정 2026-11-12 E-4).

## 1. 봉인 전에 본 것 (공개)

### 1.1 이미 알려진 결과 (과적합 공개)

| 원본 | 알려진 값 | 이 규칙에서 쓴 곳 |
|---|---|---|
| `las_p5r4_k1_judgement.md`(sha256 `5e9fb33b7419d624…`) 5.1·8.2·9·10절 | P0+K1 Chrono A1/A3/A5(혼합 지형 강체 + J1@FR, 바닥 (2.3351°, 1.5017°), `record_only`): RL 이탈 뒤 최소 10.814 / **8.637** / **8.509** kN, $F<F_{min}$ 시간 A3 195 ms, A5 67 ms. 실행 SL-2 $R_c$ A1·A5 1.076, A3 1.035(`operating_rule_rejects` 참). A행 wall_s 3,885~4,413 s(P 4병렬) | 5.4절 O-C5 정의·첫 축척, 7.4절, 10절 P-9·P-13, 12절 비용 |
| `06_analysis/02_control/b1/prelaunch/batch.json`(B1 본 배치, 커밋 `bd64cc4`) | SCM 6행 wall_s 6,649~8,898 s(P 4병렬, `--threads 4`, 훅 fast) | 12절 단가만(힘·행정 값은 읽지 않음) |
| `07_results/S9/batch_V5-STAGE3_20261107_184341/batch.json` | L2b 23행 wall_s 862~1,869 s, 합 28,412.8 s(P) | 12절 단가만 |
| `07_results/S9/batch_V5-STAGE3_20261107_184239/batch.json` | SCM 11행 wall_s 10,900~19,178 s(P/E 혼합, 볼록 껍질 훅 채택 전), 합 168,603 s | 12절 민감도 상한만 |
| 초안 `v5_resume_4368_plan_draft.md` 0절 머리 표 | 저장 기준선(LAS-b 전환 전·K1 관문 꺼짐)의 줄 수·`soil_mode_started`·`INFO_LOC_FLAT_SOIL_MARGIN` 개수·wall_s(판정 값은 아님) | 5.1·5.5절, 10절 P-1~P-8 |

- 436.8 행과 같은 정의의 결과로 이미 있는 것은 P5r4 A1·A3(C-4 켬 팔과 같을 수 있음, 5.2절)뿐이다. 그 값은 10절 P-9에 예측으로 적고, 판정은 436.8 커밋에서 다시 돈 결과로만 한다(사용자 결정 R-2).

### 1.2 이 규칙을 쓰려고 읽은 것

- 규칙·판정서: 부록 A의 봉인 문서 전부(sha256을 `.sha256` 기록과 대조, 모두 일치), `las_p5r4_k1_judgement.md`, `las_k1_rem_judgement.md`, 명세 `00_docs/04_control/s6_control_spec.md` 436·437절, CLAUDE.md 기준값 표.
- 코드(정의 확인만, 실행 안 함): `03_src/outrigger_sim/hydraulics/v5_options.py`(`is_extend_start_tag`, `switch_base_tag`, `EXTEND_START_TAGS`), `04_scripts/02_chrono/s9_batch.py`(`V5_LAS_K1_CONTROLLER` = `final_C4G2_LAS_K1`, `V5_P3_LAS_K1_CONTROLLER` = `final_C4G2_P3_LAS_K1`), `run_S9.py`(`--las-off`·`--k1-order-gate {preset,off,on}`·`--start-limit`·`--floor-roll`·`--floor-pitch`·`--crawler-kn-scale {1,3}`, `SCM_THREADS_FIXED` = 4, `start_condition_record`의 $R_c$ 식), `las_chrono_rows.py`(`V5-LAS-CHRONO` 4행 정의), `las_p5r4_k1_chrono_rows.py`(A1~A6 정의).
- 해시 앵커 커밋 `c6bb55b` 이후 `03_src`·`02_params` 변경: `03_src/outrigger_sim/chrono/b1_grid_record.py` 추가 1건(Chrono 전용, `--b1-grid-record`를 줄 때만 동작). 하네스 경로 변경 없음(`git diff --stat c6bb55b..3d41083`). 실행 커밋에서 다시 확인한다(3절 A-5).

## 2. 규약과 기호

- 이산 $T_s$ = 0.1 s(10 Hz), 출력 지연 $d$ = 1, C2 음되먹임($u$ = 다리 행정 속도 명령 [m/s], + = 신장). 정수 주기 $n = \mathrm{round}(t/T_s)$로 시각을 비교한다.
- 다리 순서 FL, FR, RL, RR(0~3). 힘은 실린더 순 힘 [N](표는 kN). 압력은 bar 게이지. 행정은 모터 행정 [m](표는 mm).
- "Kc1"·"Kc3"은 크롤러 접촉 강성 ×1·×3이다. K1 R4c30 순서 관문(이하 "K1 관문")과 하네스 키 토큰 `K1`(크롤러 ×1)과 다르다.

| 기호 | 정의 | 단위 |
|---|---|---|
| $F_{min}$ | YAML `control.F_min_cylinder_N` = 9,414.589 | N |
| $F^{\mathrm{a}}_{min}$ | Chrono `p3b.P3-3_leg_force.F_min_after_N`(이탈 뒤 1 ms 참 $F_{cyl}$ 다리별 최소) | N |
| $F^{\mathrm{t}}_{min}$ | Chrono `p3b.P3-3_leg_force.F_min_transient_N` | N |
| $R_c$ | SL-2 운용 사용률 $\lvert\phi_c\rvert/4.4° + \lvert\theta_c\rvert/3.2°$, $(\phi_c, \theta_c)$ = CHECK 끝 크롤러 IMU 자세(result.json `p3b_ext.start_condition.R_c_operating`) | – |
| $k$ | O-C5 바닥 축척. 바닥 $(\phi_g, \theta_g) = k\cdot(2.3351°, 1.5017°)$ | – |
| `git_at_start` | 묶음 실행을 시작한 커밋 | – |

## 3. 전제·실행 전 조건 (하나라도 거짓이면 그 묶음을 시작하지 않는다)

| # | 조건 | 확인 방법 |
|---|---|---|
| A-1 | v5 제어기 = `final_C4G2_LAS_K1`. P5r4(`미달`, P0 유지)·K-2·K-2b·B1 결과는 제어기를 바꾸지 않았다 | `k2/judgement/k2_judgement.md`, `las_p5r4_k1_judgement.md` 10절 |
| A-2 | 이 문서가 봉인됐다(`.sha256`과 파일 sha256 같음, LF·BOM 없음, `.gitattributes -text`) | `tools/verif/seal_check.py` 종료 0 |
| A-3 | 0단계 T-3K(`las_targeted_rules_rev5.md`, 360건)가 판정까지 끝났다. T-3K가 `통과`가 아니면 본 묶음을 시작하지 않고 묻는다 | T-3K 판정서 |
| A-4 | 행 생성기·판정 도구가 `_LAS_K1` 태그를 기대한다(감사 W-3 해소): `d1_chrono_rows.py`, `v5_stage3_las_rows.py`, `las_chrono_rows.py`, `las_k1_chrono_rows.py`, `las_k1_rem_chrono_rows.py`, 개정판 `u3_judge`. 봉인 도구 `u3_judge`의 상수는 고치지 않는다 | 16절 위임 결과 + G-S(11.2) |
| A-5 | 모든 묶음이 같은 `git_at_start`. 실행 중 master 커밋·병합 금지(전용 worktree 예외, 그때도 `git_at_start`는 하나). `git_at_start`에서 `03_src`·`02_params`·하네스 경로가 `c6bb55b`와 다르면(1.2의 Chrono 전용 1건 제외) 10절 P-1·P-2 비트 예측의 앵커를 실행 전에 다시 정하는 개정을 봉인한다 | `git diff --stat c6bb55b..GIT_AT_START -- 03_src 02_params` |
| A-6 | 볼록 껍질 훅 DLL SHA-256이 검증 빌드 `cec997d7…`. 새 worktree에는 DLL을 복사했다 | `hull_hook` 기록 |
| A-7 | fdown3.5 L1R 스냅숏 재생성(cad-expert, RMS < 0.01 °/s)이 끝났고, 그 스냅숏을 시작 상태로 쓰는 436.8 행 목록을 cad-expert가 냈다. 그 행은 저장 행과 "조건 다름, 해시 비교 없음"으로 적는다 | cad-expert 보고 |
| A-8 | 재발 방지 4항: 옵션 × 단계 겹침 표(11.1), G-S 건조 실행(11.2), 러너 로그 `errors 0`(11.3), 자리표시 점검(11.4) | 11절 |
| A-9 | 출력은 4.3절의 새 이름으로만 쓴다. 저장 기준선과 `_LAS` 전용으로 예정됐던 이름(`v5/d1_las.jsonl`, `v5_rerun/las/`)은 쓰지 않는다 | 실행 전 감사 |
| A-10 | 묶음마다 verif-protocol-auditor `[시점] 실행 전` 감사 차단 0 | 감사 리포트 |

## 4. 제어기 태그와 옵션 (래퍼·프리셋 이중 적용 금지)

### 4.1 기대 태그와 ③ 판별

| 행 종류 | 기대 태그(`controller_tag`, Chrono `--expect-controller` 같은 값) |
|---|---|
| V0·V0v·S6SEED·V3·그 밖 ③ 없는 설정 | `final_C4G2_LAS_K1` |
| VB·LS1~LS4(③ 켬) | `final_C4G2_P3_LAS_K1` |
| ABL | `ABL_LAS_K1`(명령은 `ABL_LAS`와 같음, 437.3) |
| IND / IND_LAS(기록 열) | `IND` / `IND_LAS`(`_K1` 없음, 437.3) |
| C-4 끔 팔 2행만 | V0 `final_C4G2_K1` / VB `final_C4G2_P3_K1`(`--las-off --k1-order-gate on`) |
| 열린 루프 C-6·C-7 | 제어기 없음(`controller_options.applied` = false). 태그 검사 대상 아님 |

- **③ 켬 판별**은 `v5_options.is_extend_start_tag(tag)`(기준 태그 `switch_base_tag(tag)` = `final_C4G2_P3`)로만 한다. 집합 `EXTEND_START_TAGS`, 태그 문자열 접미사 비교, 정규식은 판정·선택에 쓰지 않는다. 접미사 조합(`_LAS`, `_K1`, `_LAS_K1`, `_TCL`)이 무엇이든 기준 태그가 같으면 같은 ③ 판별이다.
- 한 판정 묶음 안의 실행은 모두 위 표의 같은 판이다(개정 11 #6). 섞이면 멈춘다(8.2 S-2).
- 개정 11 #5의 감시기 설정 재구성에 "태그에 `_K1` 접미사(`v5_options`의 순서 관문 접미사 분해 함수가 참)면 관문 켬"을 더한다.

### 4.2 금지 옵션·env (한 번이라도 있으면 그 행은 무효, 8.2 S-3)

| 대상 | 금지 |
|---|---|
| 모든 하네스 줄 | 후보 토큰·래퍼(`K1on`, `LASoff`, `TCL`, `P5r4` 등 `C2Config.with_10hz_d1()` 기본값을 다시 적용하거나 바꾸는 키 토큰), `OUTRIGGER_LOC_SHADOW` env(사용자 결정 Q5 (a)) |
| 모든 Chrono 행(C-4 끔 팔 제외) | `--k1-order-gate`(값 무관), `--las-off`, `--las-candidate`, `--k1-forced-block`, `--k2`, `--no-controller-check`, `pre_*_preset_runner.py` 경유, `OUTRIGGER_LOC_SHADOW` |
| C-4 끔 팔 2행 | 위에서 `--las-off`와 `--k1-order-gate on` 두 개만 허용(437.4의 LAS-b 단일 변수 짝). 그 밖은 같음 |
| 모든 SCM 행 | `OUTRIGGER_HULL_HOOK` 설정(미설정 = fast가 기본), `OUTRIGGER_HULL_HOOK_ALLOW_UNVALIDATED`, `--allow-mixed-hull` |

- 기록 확인(전 행, 실행 직후·판정 전): `c2_setup.k1_order_gate` = `preset`(C-4 끔 팔은 `on`), `c2_setup.k1_order_gate_effective` = true, `controller_meta.slope_clearance_margin.settings.flat_soil_margin_order_gate` = true, `liftoff_approach_slow.settings` 9값이 프리셋 값(C-4 끔 팔은 꺼짐, `c2_setup.las_off` = true). 하네스 줄은 같은 의미의 줄 필드. 하나라도 다르면 8.2 S-3.

### 4.3 출력 이름 (고정)

| 묶음 | 출력 |
|---|---|
| 하네스 H-1·H-5·H-6·H-7·H-8·H-9·H-10 | `06_analysis/03_hydraulic/coupled/v5/resume_k1/` 아래 `h1_d1.jsonl`, `h5_u9_v0.jsonl`, `h6_dg3_v4on.jsonl`, `h7_dg3_off.jsonl`, `h8_noise.jsonl`, `h9_stage1.jsonl`, `h10_reuse_rerun.jsonl`(각 `.identity.json` 동반) |
| H-2 | `resume_k1/h2_d1_select.json` |
| H-3·H-4 | `06_analysis/02_control/v5_rerun/las_k1/` 아래 `u3_*.json`, `u6_*.json`(파일 구성은 `u3_u6_rerun_rules` 원판~rev2의 꼴, 폴더만 바꿈) |
| H-0 T-3K | `las_targeted_rules_rev5.md` 2.6절 그대로 |
| Chrono | `07_results/S9/batch_V5-RESUME-K1-<묶음 ID>_<stamp>`(묶음 ID: `C1`, `C2`, `C3`, `C4`, `C5`, `C6C7`, `OC5PROBE`, `OC5`, J_P 재실행이 생기면 `JP`) |

- python-expert가 다른 이름이 필요하면 봉인 전에 이 표를 고친다. 봉인 뒤에는 바꾸지 않는다.

## 5. 묶음과 행

### 5.1 하네스 묶음 (dynamics-dev, 하네스 축소 모델)

| # | 묶음 | 행 수 | 정의 | 판정 규칙 |
|---|---|---|---|---|
| H-0 | T-3K(0단계, 봉인 rev5) | 360(R-0 7 + R-0K 45 + T-3K 308) | rev5 그대로. 다른 묶음보다 먼저, 판정 뒤 본 묶음 시작(Q3 (a)) | `las_targeted_rules` 원판~rev5 |
| H-1 (J-1) | D-1 하네스 전부 | 868(V0 434 + VB 434) | 키·플랜트·시드는 저장 `v5/d1.jsonl`과 같다. 태그만 다르다 | `d1_selection_rules{,_rev1}` 판정 항목 + v5 기준 + H-7′ |
| H-2 (J-2) | D-1 선별 | 1(계산) | H-1 출력이 입력(G-1~G-5 그대로) | `d1_selection_rules{,_rev1}` |
| H-3 (J-7) | U-3 V0·VB | 2,228(slope V0 110 포함, D-1 재사용 12는 H-1 출력에서 Q-1~Q-5로) | 옛 태그 `u3_slope_V0.json`은 판정하지 않는다(해시 기록만) | `u3_u6_rerun_rules` 원판~rev2 + 이 문서 rev3 몫 |
| H-4 (J-8) | U-6 VB(C2·ABL·IND) + 기록 열 IND_LAS | 726 + 242(기록) | ABL은 `ABL_LAS_K1` | 같음 |
| H-5 (J-9) | U-9 V0 | 14 | 같음 | `u9_targeted_rules_rev1` + 7.1 태그 읽기 |
| H-6 (J-10) | dg3 v4_on(2단계 잡음 L3 VB 대체) | 135 전부(Q1 (a)) | 그림자 작동 38키·미작동 97키 모두 재실행 | v5 개정 8 2절 #6 |
| H-7 (J-11) | dg3 off(③ 끔 비교) | 135 전부(Q4 (a)) | 기록 행 | 기록 |
| H-8 (J-12) | 2단계 잡음 VB·V0, seedext | 3,106(VB 1,503·V0 1,503·seedext 100) | 원 명령, 새 이름. dg3가 대체한 L3 134·L2 1의 처리는 원 규칙 그대로 | r79·v5 기준 |
| H-9 (J-13) | 1단계 main V0~V8·L1·L2, pressure_only V0·V4·V5, 격자 VB | 812 + 96 + 768 | 원 명령, 새 이름 | v5 기준 |
| H-10 | 재사용 예정이던 하네스: main VB·LS1~LS4, U-9 VB, p3_hash VB, item8(VB 6 + V0 6), overlap(VB 4 + V0 4 + V3 4) | 388 + 28 + 22 + 12 + 12 = 462 | 재사용하지 않고 재실행(Q1 (a)) | v5 기준(재사용 표시 없이 새 결과로 판정) |

- 본 묶음 합계 9,800행(H-1 868 + H-3 2,228 + H-4 968 + H-5 14 + H-6·H-7 270 + H-8 3,106 + H-9 1,676 + H-10 462) + 0단계 360. 묶음별 실제 줄 수는 python-expert가 `steps_h2.json`에서 세고, 이 표와 다르면 실행하지 않고 멈춘다(8.2 S-15). 차이의 원인이 원 규칙의 줄 정의(예: dg3 대체분)이면 봉인 전에 이 표를 고친다.

### 5.2 Chrono 묶음 (Chrono-dev)

| # | 묶음 | 행 | 엔진 | 정의 | 판정 규칙 |
|---|---|---|---|---|---|
| C-1 (J-3) | D-1 고정 강체 | 10(L2b VB 6: C2-01·02·04·05·06·08, L1-R V0 Kc×3 4: C1-09~12) | L2b NSC / L1-R | 미실행 행. 태그만 `_LAS_K1` | D-1 선별 규칙 11절 |
| C-2 (J-4) | D-1 선별 행 + PS-c | 4(L2b C2-03·07, SCM S-01·02) + 기준선 실패 시 칸당 +1(최대 8) + PS-c 0~2(SCM) = 4~10 | L2b / SCM | H-2 출력으로 정한다 | 같음 |
| C-3 (J-5) | D-1 고정 토양 S-03·S-04(`D1S_G1_B_{middle,bottom}_Fs4_spJ1FL` 두 행) | 2 | SCM | 재실행이 판정, 저장(옛 VB 태그) 결과는 기준선 기록(명세 436.9.7) | 같음 |
| C-4 (J-14) | LAS Chrono 확인 `V5-LAS-CHRONO`(혼합 지형 강체 + J1@FR, 바닥 (2.3351°, 1.5017°), `record_only`, 160 s, VB) | 4 = Kc1·Kc3 × LAS 켬·끔 | SCM 혼합 | 켬 팔 = 현행 프리셋(P0+K1), 태그 `final_C4G2_P3_LAS_K1`. 끔 팔 = `--las-off --k1-order-gate on`, 태그 `final_C4G2_P3_K1`. 켬 팔이 P5r4 A1(Kc1)·A3(Kc3)와 같은 정의이면(cad-expert가 `option_diff`로 확인, 차이 허용은 `--las-candidate P0` 한 개) 436.8 커밋에서 다시 돌리고 A1·A3과의 명령 비트 비교는 기록만 한다(R-2 (a)) | 기록(하네스 T-1 짝과 나란히), D8·G6. 7.4 시작 조건 밖 처리 |
| C-5 (J-15) | 3단계 Chrono(`V5-STAGE3-LAS` 정의를 `_LAS_K1`로) | 논리 37, **실행 35** = L2b 24(강체 23 + 짝 P-1) + SCM 11. 짝 P-2·P-3은 S6SEED `…_seed20261026`·`…_seed20261026_flow`와 정체성 5항목이 같아 빼고, 판정에서는 그 두 행을 P-2·P-3으로도 읽는다(12c 대기분을 이 문서가 확정) | L2b / SCM | 개정 12 2.1 행 그대로, 태그만 4.1 | 개정 12·12a·12b + 이 문서 |
| C-6 | G1 열린 루프 VB 비례 `P3a_G1_B_VB_prop` | 1 | SCM(L2b 다리, 제어기 없음) | 5.3절 | 기록(7.5) |
| C-7 | G1 열린 루프 속도 낮춤 VB `P3a_G1_B_VB_FB` + V0 `P3a_G1_B_V0_FB` | 2 | 같음 | 5.3절 | 기록(7.5) |
| C-8a | **O-C5 VB**: A3 조건(Kc3, VB)을 운용 시작 조건 안으로 | 1 + $R_c$ probe 1~3 | SCM 혼합 | 5.4절 | 기록 행 + 멈춤(7.4) |
| C-8b | **O-C5 V0 짝**: A5 조건(Kc1, V0)을 운용 시작 조건 안으로(사용자 결정 R-3, 확인 필요 질문 Q-A) | 1 + $R_c$ probe 1~3 | SCM 혼합 | 5.4절 | 기록 행 + 멈춤(7.4) |
| 재사용 | J_P Chrono 12(`V5-JP-{VB,V0}`) | 0(조건 실패 시 12) | L2b | 7.3 조건이 참이면 저장 판정 그대로(재사용 표시). 거짓이면 저장 argv 그대로·태그만 4.1로 묶음 `JP`에서 재실행해 판정한다(멈추지 않음) | 저장 판정 / 재실행 판정 |
| 재사용 | 열린 루프 `V5-OPENLOOP-{VB,V0,VB-PROP,FB}`, `V5-OPENLOOP-R`·`RFU` | 0 | – | 제어기 없음 | 그대로 |

- Chrono 합계: **60~66행**(C-1 10 + C-2 4~10 + C-3 2 + C-4 4 + C-5 35 + C-6·C-7 3 + C-8 2) + $R_c$ probe 2~6건(행마다 최대 3, CHECK까지) + J_P 조건 실패 시 12.
- 엔진별: L2b·L1-R 36~38행(C-1 10, C-2 2~4, C-5 24), SCM 24~28행(C-2 2~6, C-3 2, C-4 4, C-5 11, C-6·C-7 3, C-8 2).
- 행 이름의 최종 문자열(`case`)은 cad-expert가 정하고 `batch.json`에 `criteria_id`로 이 표의 # 값을 남긴다.

### 5.3 G1 열린 루프 새 행 (C-6·C-7)

| 항목 | C-6 VB 비례 | C-7a 속도 낮춤 VB | C-7b 속도 낮춤 V0 |
|---|---|---|---|
| 바탕 행 | `batch_V5-OPENLOOP-VB_20261108_112044\P3a_G1_B_VB`(VB: η_v 0.85, 51.17 L/min, 우선 분배, τ_v 0.1 s, M2 `flow_limited_r5`) | 같음 | `batch_V5-OPENLOOP-V0_20261108_123517\P3a_G1_B_V0` |
| 바꾸는 인자 | `--flow-law proportional`만 | `--lift-s 31.93 --lift-speed-fraction 0.87684`만 | 같은 두 인자만 |
| `check-sources` | `ok_expected_diff`, 차이 = VB 인자 + `flow_law` | 차이 = VB 인자 + 두 인자 | 차이 = 두 인자 |
| 짝(기록) | 저장 G1 v4·V0·VB(우선) | 저장 G1 v4·V0·VB, C-6, C-7b | C-7a |
| 값 계산 | `paper_runs/scripts/openloop_compare.py`의 `analyse` 정의(속도비 창 8.5 s < t ≤ 실행 끝) | 같음 + 유량 제한 0행 확인 | 같음(V0라 유량 항목 해당 없음, 속도비는 10~20 s $\dot s_{motor}$) |

### 5.4 O-C5 기록 행 (C-8a·C-8b)과 바닥 각 결정 절차

| 항목 | C-8a(VB) | C-8b(V0 짝) |
|---|---|---|
| 행 이름 | `OC5_mixed_rigid_J1FR_Kc3_VB_top` | `OC5_mixed_rigid_J1FR_Kc1_V0_top` |
| 바탕 | P5r4 A3 행 정의(`las_p5r4_k1_chrono_rows` → `las_chrono_rows.level_argv`: 강체 + J1@FR `--rigid-base FR --soil J1 --grid 0.01`, `--crawler-kn-scale 3`, VB `s9_batch.v5_vb_argv()`, 패드 B, 오거 상단, $F_s$ 4 kN, 압력 normal·IMU ideal·시드 20261026, 160 s) | P5r4 A5 행 정의(같은 지형, Kc1 = 크롤러 인자 없음, V0 = v5 인자 없음) |
| 제어기 | 현행 프리셋, 태그 `final_C4G2_P3_LAS_K1` | 현행 프리셋, 태그 `final_C4G2_LAS_K1` |
| 바탕과 다른 인자 | `--floor-roll`·`--floor-pitch`(바닥 축척 $k$)와 `--las-candidate P0` 없음, 이 둘뿐 | 같음 |
| 시작 제한 | `--start-limit record_only`(A행과 같음). $R_c$는 판정 대상 여부를 정하는 값으로만 쓴다 | 같음 |
| 첫 축척 | $k_1 = 0.95 / 1.035 = 0.9179$ | $k_1 = 0.95 / 1.076 = 0.8829$ |
| 비교 짝(기록) | P5r4 A3(같은 Kc·플랜트, 바닥만 다름) | P5r4 A5(같은 Kc·플랜트, 바닥만 다름) |
| C-8a↔C-8b | 크롤러 강성과 플랜트 두 변수가 다르다. 둘의 차는 단일 변수 효과로 읽지 않는다(기록만) | |

**바닥 각 결정 절차(행마다 따로, 본 행 결과 전)**

1. **probe 정의**: 본 행 argv에서 `--duration`만 `PROBE_DURATION`으로 바꾼 실행이다. `PROBE_DURATION` = 같은 바탕 행(A3 또는 A5)의 저장 `phases`에서 CHECK 끝 시각(폐루프 시작 기준) + 2 s를 올림한 정수 초. cad-expert가 시각만 읽어 정하고 `batch.json` 행 `note`에 적는다. 같은 커밋·스레드·풀·훅·start env.
2. probe에서 읽는 것은 `p3b_ext.start_condition`의 `crawler_attitude_deg`·`R_c_operating`, 바닥 인자, `phases`뿐이다. probe 판독 도구는 이것만 출력한다. 힘·행정·판정 블록은 읽지 않고, 판정서에도 쓰지 않는다.
3. probe 결과에 `R_c_operating`이 없으면(CHECK가 끝나지 않음) `PROBE_DURATION`을 두 배로 한 번 다시 돈다. 이 재실행은 probe 개수에 세지 않는다. 그래도 없으면 그 행의 절차를 멈추고 묻는다.
4. $|R_c(k_1) - 0.95| \le 0.02$이면 $k = k_1$.
5. 아니면 $k_2 = k_1 \cdot 0.95 / R_c(k_1)$로 둘째 probe. $|R_c(k_2) - 0.95| \le 0.02$이면 $k = k_2$.
6. 아니면 할선 $k_3 = k_1 + (0.95 - R_c(k_1))(k_2 - k_1)/(R_c(k_2) - R_c(k_1))$로 셋째 probe. $|R_c(k_3) - 0.95| \le 0.02$이면 $k = k_3$.
7. 멈춤: 셋째 probe 뒤에도 허용 밖, $R_c(k_2) = R_c(k_1)$(할선 정의 불가), 계산한 $k \notin (0, 1]$ 중 하나면 그 행의 본 실행을 하지 않고 멈춘 뒤 묻는다(다른 묶음은 계속). **probe는 행마다 최대 3건**이다.
8. 바닥 인자 값: $\phi_g = \mathrm{round}(k \cdot 2.3351, 4)$°, $\theta_g = \mathrm{round}(k \cdot 1.5017, 4)$°. $k$는 소수 넷째 자리로 적는다. 실제 argv 문자열이 원본이다.
9. 본 행은 정한 $k$로 처음부터 끝까지 돈다. 본 행의 실행 $R_c$를 다시 기록하고 정한 probe의 $R_c$와 비교한다(같은 argv 앞부분이므로 같다고 예측, 10절 P-14). 다르면 기록하고 python-expert에 원인 확인을 넘긴다(멈추지 않음).
   - 본 행 $R_c \le 1$: O-C5로 읽는다(7.4).
   - 본 행 $R_c > 1$: O-C5로 읽지 않는다. 대체 행을 넣지 않고, 기록하고 묻는다.
10. probe와 본 행의 $k$, 바닥 각, $R_c$, probe 개수는 모두 판정서에 적는다. 목표 0.95, 허용 0.02, 최대 3건은 **절차 값(가정)**이고 판정 문턱이 아니다(사용자 결정 R-1).

### 5.5 재사용

- 재사용은 **J_P Chrono 12**와 **제어기 없는 열린 루프**뿐이다(Q1 (a)). 하네스는 재사용하지 않는다. 재실행 결과와 저장 해시가 같으면 "미작동 확인"으로 적는다(개정 11 2절 문구).

## 6. 실행 정체성 기록 (줄·행마다, 판정 전 확인)

| 항목 | 하네스 | Chrono SCM(`run_S9.py level`, 열린 루프·probe 포함) | Chrono L2b(`run_S8C.py`) / L1-R |
|---|---|---|---|
| 프리셋 | `C2Config.with_10hz_d1()` 기본값(LAS-b 켬, K1 관문 켬, ③는 VB·LS만). 4.2 금지 토큰 없음 | 같음, `--k1-order-gate` 없음(= `preset`) | 같음 |
| 태그 | 4.1 표. `controller_tag` 필드 | `--expect-controller` = 4.1 값, `expect_controller.ok` 참 | 같음 |
| 커밋 | 줄마다 `git_at_start`(+ dirty 여부). 묶음 안에서 하나 | `batch.json` `git_at_start`, result.json 커밋 | 같음 |
| 스레드 | 작업자마다 `MKL_NUM_THREADS`·`OMP_NUM_THREADS`·`OPENBLAS_NUM_THREADS`·`NUMBA_NUM_THREADS` = 1, `MKL_THREADING_LAYER` = TBB, spawn. 기록만(결과가 스레드와 무관) | `--threads 4`, result.json `num_threads_chrono` = 4. 다르면 8.2 S-4 | 저장 argv와 같은 값 |
| start env | – | 행 키 `start_env`에 `OMP_WAIT_POLICY=PASSIVE`, result.json에 같은 값 기록. 없거나 다르면 8.2 S-4 | – |
| 풀 | 기록(P·E 혼합 가능) | `pool` = `planned_pool` = `pcore`, result.json `placement`(affinity 마스크·논리 CPU 목록), `power_throttling_off_ok` 참, 실행 중 affinity 변경 기록. E로 돈 행은 저장 행과 해시 비교를 하지 않고 "조건 다름"으로 적는다(개정 12 2.2). `pool` ≠ `planned_pool`이면 기록하고 그 행의 해시 비교만 뺀다 | `pcore` |
| 볼록 껍질 훅 | – | `hull_hook_requested`·`hull_hook_effective` 전 행 fast, `fallback_reason` 없음, batch `MIXED_HULL_MODE` 없음. 하나라도 어긋나면 8.2 S-4 | – |
| 센서 | 각 묶음 원 정의(압력 normal 등급, IMU 원 정의, 시드 원 값) | 같음 | 같음 |
| 예약 | 30분 넘는 묶음은 `reserve.py add`(러너면 `--reserve-owner`) | 같음 | 같음 |
| 시작 제한 | – | C-4·C-8·probe `--start-limit record_only` | – |

## 7. 판정 기준

### 7.1 원본 기준 (바꾸지 않는다)

| 묶음 | 기준 원본(봉인, 부록 A) | 이 문서가 더하는 것 |
|---|---|---|
| 전부 | `v5_criteria.md` + 개정 1~12b | 태그를 4.1로(개정 11 #1·#2·#5, 개정 12 #2). 개정 11 #4 "③ 켬 실행 전부, 대상 0이면 판정하지 않고 멈춘다"의 ③ 켬은 4.1 판별. #6 "한 판정 묶음은 같은 제어기 판". #7 `INFO_LIFTOFF_SLOW*`는 기록 항목 |
| H-1·H-2·C-1·C-2 | `d1_selection_rules.md` + rev1 | 입력 이름만 4.3(`h1_d1.jsonl`). rev1에 태그 문자열이 없으므로 규칙 문장은 그대로 |
| H-3·H-4 (rev3 몫) | `u3_u6_rerun_rules.md` + rev1 + rev2 | G-2 태그: V0 `final_C4G2_LAS_K1`, VB C2 `final_C4G2_P3_LAS_K1`, ABL `ABL_LAS_K1`, IND `IND`, IND_LAS `IND_LAS`. D-1 재사용 입력 `d1_las.jsonl` → `resume_k1/h1_d1.jsonl`. 출력 폴더 `v5_rerun/las/` → `v5_rerun/las_k1/`. 판정 도구는 봉인 도구 `u3_judge`가 아니라 개정판 도구(16절)이고, 개정판은 태그 상수와 입출력 경로만 다르다(그 밖 코드 차 0을 `git diff`로 보인다) |
| H-5 | `u9_targeted_rules_rev1.md` | 태그 읽기 `final_C4G2` → `final_C4G2_LAS_K1`, `final_C4G2_P3` → `final_C4G2_P3_LAS_K1` |
| 작동 행 | `las_targeted_rules` 원판~rev4c(H-7′), rev5(T-3K) | H-7′의 "작동 행"을 7.2 분류의 LAS-b 작동·K1 막힘·둘 다로 넓힌다 |
| C-5 | 개정 12 2.2(짝은 재실행끼리만, 재실행↔저장은 기록, 해시 비교는 같은 `--threads`·둘 다 P), 12a(OMP 기록 + 플랜트 선행 검사), 12b(핵심·보조 배열) | 실행 35행(5.2) |
| C-6·C-7 | 명세 11047(열린 루프 이륙 전 최소 $F_a$ < $F_{min}$이면 FLAG), `run_S9.py` `p3a.checks` P3a-1~5 | 7.5 |

### 7.2 K1 작동 분류 (줄·행마다, 관문 켬 실행)

| 분류 | 조건(`controller_meta`) | 처리 |
|---|---|---|
| 미작동 | `liftoff_approach_slow.start_s` = None **이고** `slope_clearance_margin.order_gate.decisions`의 모든 항목이 `would_block` 거짓 | 명령 해시가 10절 비트 예측(P-1·P-2) 앵커 또는 저장 행 해시와 같아야 한다(해당 앵커가 있는 줄만). 다르면 멈춘다(8.2 S-5) |
| LAS-b 작동 | `start_s` ≠ None, K1 막힘 없음 | H-7′ 적용 |
| K1 막힘 | 어떤 `decisions` 항목이 `would_block` 참 ∧ `r4_due_without_gate` 참, LAS-b 작동 없음 | H-7′ 적용(C2·C3·C4′·C5′·P3-2 유지, None은 실패). 사건 `INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order` 수 = `decisions` 막힘 수(다르면 8.2 S-5) |
| K1 막힘 — 균일 연약 지면 계열 | K1 막힘 ∧ 계열이 H-S-0·H-S-1, U-3·잡음의 균일 J1·J2·S1 바탕(패치·처방 침하 없음), Chrono 균일 SCM 행 | **멈추고 묻는다**(8.2 S-6). 근거: REM R1~R8 첫 R4 LOC dP +99~+206주기, 437.5 F2 |
| 둘 다 | LAS-b 작동 ∧ K1 막힘 | H-7′ 적용, 원인 칸에 둘 다 |

- 패치·처방 침하 계열(H-S-A, H-S-A-J2, H-R-A-J2, H-R-A-S1, H-S-C, H-S-C-g, G6 계열)의 K1 막힘은 의도된 동작(437.1)이다. 기록하고 H-7′만 적용한다.
- 관문 켬 실행이므로 각 `decisions` 항목에서 `applied`와 `would_block`이 함께 참이면 안 된다. 함께 참인 항목이 있으면 8.2 S-5.
- 분류에 쓰는 키가 없으면 그 줄은 `판정 불가`(None은 실패가 아니라 결측, 9.3).

### 7.3 J_P 재사용 조건 (모두 참이어야 재사용)

1. LAS-b 그림자 미작동(`shadow_jp_b0.jsonl`, 개정 11 2절).
2. K1 무영향: 저장 결과의 사건 기록에 `INFO_LOC_FLAT_SOIL_MARGIN`(R4c30 적용)이 0개이고 토양 모드 시작이 없다. 관문은 R4c30을 막기만 하므로 R4c30이 한 번도 적용되지 않은 실행은 관문 켬에서도 명령이 비트 단위로 같다(437.1).
3. 2의 판독은 python-expert가 사건 기록 형식(`controller_events.json`)을 코드로 확인한 판독 도구로 낸다. 문자열 검색은 근거로 쓰지 않는다(초안 단계 문자열 검색에서 `"INFO_` 자체가 검색되지 않았다).
- 하나라도 거짓이거나 판독 불가이면 J_P 12행을 묶음 `JP`로 재실행해 판정한다(5.2).

### 7.4 운용 시작 조건 밖 행과 O-C5

- **운용 시작 조건 밖 행**: 실행 $R_c$ > 1인 Chrono 행(예상: C-4 4행)의 $F_{min}$ 하회(`P3-3_within` 거짓)는 L-5 알려진 한계로 적는다. 묶음을 멈추지 않고 판정 등급에 넣지 않는다. 그 밖 판정 항목은 원 규칙대로 판정한다.
- **O-C5(C-8a·C-8b)는 기록 행이다.** 판정 등급(`통과`·`미달`)을 만들지 않는다. 본 행 $R_c \le 1$일 때 $m$ = 네 다리 $F^{\mathrm{a}}_{min}$의 최소로 다음을 적용한다.

| 조건 | 처리 |
|---|---|
| $m < F_{min}$ (= 9,414.589 N) | **멈춤**(8.2 S-9): 판정서에 적기 전에 사용자에게 다시 묻는다. 다른 묶음은 멈추지 않는다. 판정서 종합 문장과 L-5는 결정 뒤에 쓴다 |
| $F_{min} \le m < F_{min} + 2000$ N | 기록, L-5에 여유 값 $m - F_{min}$을 함께 적는다 |
| $m \ge F_{min} + 2000$ N | 기록 |

- 기록 항목(두 행 같음): 다리별 $F^{\mathrm{a}}_{min}$·$F^{\mathrm{t}}_{min}$과 그 시각, $F<F_{min}$ 시간, $F<F_{min}+2$ kN 시간(P5r4 판정서 8.2 표와 같은 정의, 1 ms 참 $F_{cyl}$), `P3-3_within`, LAS-b 시작·끝 주기와 끝 사유, K1 `decisions`, 실행 $R_c$·크롤러 자세·바닥 각·$k$, P3-1~P3-9·D8·G6 값.
- C-8a와 C-8b가 둘 다 멈춤에 걸리면 한 번에 묻는다.

### 7.5 열린 루프 (C-6·C-7)

- 기록이다. P3a-1~5 결과와 명세 11047 FLAG 여부를 적고, 논문 표 7·그림 5의 값 원본으로 쓴다. 실패·FLAG는 멈춤 사유가 아니다. 다만 P3a-1(힘 한계) 실패나 실행 오류는 판정서에 따로 적는다.

### 7.6 이 문서가 쓰는 숫자 (전부)

| 숫자 | 쓰는 곳 | 성격 |
|---|---|---|
| $F_{min}$ = 9,414.589 N | 7.4 | 기존 문턱(YAML) |
| $F_{min}$ + 2000 N = 11,414.589 N | 7.4 | 기존 문턱(G-2′와 같은 값) |
| $R_c$ ≤ 1 | 7.4, 5.4-9 | 기존 운용 시작 조건(CLAUDE.md, SL-2) |
| 0.95, 0.02, 최대 3건, +2 s, ×2 | 5.4 | 절차 값(가정, 판정 문턱 아님) |
| 1.035, 1.076 | 5.4 첫 축척 | 알려진 값(1.1절) |
| `--threads` 4 | 6 | 기존 실행 정체성 |
| 원 규칙의 문턱 | 7.1 | 바꾸지 않음(원문 그대로) |

- 문턱 비교: "$v \ge X$"는 $v \ge X - 10^{-9}$(그 단위)일 때 참, "$v < X$"는 $v < X - 10^{-9}$일 때 참, "$v > X$"는 $v > X + 10^{-9}$일 때 참, "$\lvert v - c\rvert \le e$"는 $\lvert v - c\rvert \le e + 10^{-9}$일 때 참이다. 이 비교 허용은 9.2의 두 경로 값 대조 허용과 다른 것이다.

## 8. 상태·멈춤

### 8.1 묶음별 상태 (앞의 것이 이긴다)

`판정 불가` > `미달` > `통과`. 기록 묶음(H-7, IND_LAS, C-4 기록 항목, C-6·C-7, C-8)은 등급 없이 `기록 완료` / `기록 불완전`. v5 종합 판정은 판정 묶음 상태의 최악이다. O-C5 멈춤이 걸리면 종합 문장은 사용자 결정 뒤에 쓴다.

### 8.2 멈춤 (그 묶음의 실행·판정을 멈추고 묻는다. 적힌 경우 말고는 다른 묶음은 계속)

| # | 조건 |
|---|---|
| S-1 | 이 문서·부록 A 문서의 sha256이 기록과 다르다(전 묶음 멈춤) |
| S-2 | 4.1 태그와 다르거나 한 묶음 안에 두 판이 섞였다 |
| S-3 | 4.2 금지 옵션·env가 있거나 4.2 기록 확인이 어긋났다(이중 적용 의심) |
| S-4 | SCM 정체성: `num_threads_chrono` ≠ 4, `OMP_WAIT_POLICY=PASSIVE` 없음, 훅이 fast가 아니거나 `fallback_reason` 있음, `MIXED_HULL_MODE` |
| S-5 | 7.2 미작동 줄의 해시 변화, `_SKIPPED:order` 수 ≠ 막힘 수, `applied` ∧ `would_block` |
| S-6 | 균일 연약 지면 계열의 K1 막힘(7.2) |
| S-7 | 비트 예측 P-1·P-2가 어긋났다(판정 전 멈춤, 원인을 본다) |
| S-8 | ③ 켬 대상 0(개정 11 #4), G-4·G-6 빈 선택(`u3_u6` 원판) |
| S-9 | O-C5 본 행 $R_c \le 1$에서 $m < F_{min}$(7.4). 그 행만 멈춤 |
| S-10 | O-C5 절차 멈춤(5.4-3·7), 본 행 $R_c > 1$(5.4-9). 그 행만 멈춤 |
| S-11 | 러너 로그 `errors` ≠ 0, 자리표시 남음, G-S 실패(11절) |
| S-12 | 한 묶음 안 커밋이 둘 이상이거나 실행 중 master 커밋·병합 |
| S-13 | 두 경로 등급이 다르다(9.2) — 그 묶음 `판정 불가` |
| S-14 | T-3K가 `통과`가 아니다(본 묶음 시작 전, 전 묶음 멈춤) |
| S-15 | 묶음 줄·행 수가 5.1·5.2 표와 다르다 |

## 9. 두 경로 판정

### 9.1 경로 표

| 묶음 | 두 경로 | 경로 1 | 경로 2(독립) |
|---|---|---|---|
| H-0 T-3K | 필요(rev3~5) | `las_judge`/H-7′ 모듈 | jsonl 재집계 |
| H-1·H-2 | 필요 | `run_v5.py d1` 판정 블록 + `d1_select.py` | jsonl 직접 재집계·재선별 |
| H-3·H-4 | 필요 | 개정판 `u3_judge` | 재집계 |
| H-5·H-6·H-8·H-9·H-10 | 필요 | 각 판정 도구 | 재집계 |
| H-7, IND_LAS | 불필요(기록) | 집계 1회 | – |
| 7.2 K1 분류 | 필요 | 판정 도구 | `decisions`·사건 수 재집계 |
| C-1~C-5 | 필요 | 행 판정기(`result.json` 판정 블록) | `series.npz`·`r8_series` 재계산 |
| C-6·C-7 | 필요(논문 표 7 값) | `result.json` `p3a` | `openloop_compare.py` `analyse`(`series.npz`) |
| C-8a·C-8b | 필요(7.4 멈춤과 L-5 값) | `result.json` 판정 블록(`P3-3_within`, $F^{\mathrm{a}}_{min}$, $R_c$) | 1 ms 참 $F_{cyl}$ 다리별 최소·시간을 `series.npz`에서 재계산, $R_c$는 기록된 크롤러 자세에서 2절 식으로 재계산 |
| $R_c$ probe | 불필요(절차 값) | 1회 | – |
| 7.3 J_P 재사용 판독 | 필요 | python-expert 판독 도구 | `controller_events.json` 직접 재집계 |

### 9.2 독립성과 대조

- **경로 2 작성자 요건**: 경로 2는 경로 1 도구를 만들거나 고친 사람(에이전트 실행)이 아닌 작성자가 쓴다. 경로 2 작성자에게는 이 문서, 부록 A 원 규칙, 원 데이터(jsonl·`result.json`·`series.npz`·`controller_commands.npz`·`controller_events.json`·`batch.json`)만 준다. 경로 1의 코드·출력·중간 파일·로그는 주지 않는다. 정의를 맞출 때는 이 문서와 원 규칙의 정의 문장만 쓴다.
- 경로 2 작성자는 판정서에 읽은 것 목록을 적는다(1.2절과 같은 꼴). 경로 1 코드를 본 사실이 있으면 그대로 적고, 그 묶음의 두 경로 판정은 `판정 불가`로 둔다.
- 순서: 두 경로 출력 파일을 모두 확정(sha256 기록)한 뒤 대조한다. 상대 출력을 본 뒤에는 어느 경로도 고치지 않는다. 고쳐야 하면 새 봉인 개정을 거친다.
- **대조(K-10 꼴)**: 등급·참거짓·목록·개수·분류는 완전 일치. 수치 값은 같은 단위에서 $\lvert a - b\rvert \le 10^{-9}\max(1, \lvert a\rvert, \lvert b\rvert)$(힘 N, 시간 s, 행정 m, $R_c$ 무차원)이면 일치. 판정서가 도구 밖에서 확정한다.
- 등급이 다르면 그 묶음은 `판정 불가`(8.2 S-13), 두 출력을 그대로 적고 묻는다. 등급은 같고 수치만 허용 밖이면 기록하고 python-expert에 원인 확인을 넘긴다(공개).
- 두 경로 정의가 다른 곳은 판정서에 표로 공개한다(P5r4 판정서 6.3 꼴).

### 9.3 결측

- 판정에 쓰는 키가 없거나 None인 항목은 원 규칙이 None을 실패로 정한 곳(H-7′ 등)만 실패이고, 그 밖은 `판정 불가`다. 결측 개수를 묶음마다 적는다.

## 10. 사전 예측 (P-1·P-2만 판정 전 확인 항목, 나머지는 판정 기준 아님)

| # | 대상 | 예측 | 근거 |
|---|---|---|---|
| P-1 | H-1 강체 412줄(H-R-0 264, H-R-A 144, H-R-A-stop 4) | K1 `decisions` 막힘 0. 명령 해시: T-1·T-2에서 돈 192키는 `las_T1.jsonl`·`las_T2.jsonl` b0 해시, H-R-0 나머지 216줄은 저장 `d1.jsonl` 해시. H-R-A-stop 4줄은 예측하지 않는다 | 저장 412줄 토양 모드 0·R4c30 0, 437.1, `k1_YT.jsonl` 192/192 |
| P-2 | H-1 토양 456줄(S-C) | 명령 해시가 H-SH 앵커와 같다: `k1_YP.jsonl`(`0d985d56…`) 165줄 + `soil_defer/s2d_SC.jsonl`(`70e91ec1…`) 291줄 | `k2/loc_shadow/hsh_report.md` 0·4.1절(`c6bb55b`에서 456/456) |
| P-3 | H-1 K1 막힘 | 패치·처방 침하 계열에만, 균일 계열(H-S-0·H-S-1) 0 | 437.1 |
| P-4 | H-2 | 옛 G-3 정지 행 `D1\|H-R-A\|rigid+J1@FR\|T\|diag-op\|K1` ε 0이 풀린다 | `las_judgement.md` 8.2 |
| P-5 | H-3·H-4·H-8·H-9 | 강체 바탕 K1 막힘 0. LAS-b 작동은 강체 + J1 패치·잡음 L3 G6 계열에 몰린다 | `las_judgement.md` 5절 |
| P-6 | H-10 main VB·LS 388 | R4c30 없는 322줄은 저장 해시와 같다. R4c30 있는 66줄은 강체 바탕이면 같고 패치 바탕이면 막힘이 생길 수 있다 | 초안 3.6절 |
| P-7 | C-3 | K1 무영향, LAS-b 미작동 → 같은 `--threads`·P면 저장과 명령 비트 같음(기록) | `v5_paper_runs_judgement.md` 7.4 |
| P-8 | C-5 토양 균일 행 | K1 막힘 0 | 437.2 |
| P-9 | C-4 | 켬 팔: P5r4 A1·A3와 같은 크기(Kc1 VB RL 약 10.81 kN, Kc3 VB 약 8.64 kN < $F_{min}$), $R_c$ 1.076 / 1.035(L-5, 멈춤 없음). 끔 팔과는 방향만(켬 ≥ 끔) | P5r4 판정서 5.1·8.2 |
| P-10 | C-6 | 속도비 0.8947 ± 0.001, 이륙 18.91 ± 0.15 s, 끝 \|Δpitch\| ≤ 0.1°, 다리 사이 행정 차 ≤ 2 mm, 이륙 전 후방 최소 $F_a$ 11.0~13.6 kN(FLAG 없음), P3a-1~5 통과 | `v5_paper_runs_judgement.md` 1.2·1.6절 |
| P-11 | C-7a | 유량 제한 0행, $Q_{sum}$ 최대 ≤ 50.2 L/min, 속도비 0.8769, 이륙 19.29 ± 0.15 s, 그 밖 C-6과 같은 크기 | 같은 문서 1.7절 |
| P-11b | C-7b | 속도비 0.8769, 이륙 19.29 ± 0.15 s(C-7a보다 0~0.1 s 이름), 후방 최소 C-7a와 ±0.5 kN 안, 끝 자세 ±0.02°, P3a-1~5 통과 | 같은 문서 1.7절 V0_FB |
| P-13 | C-8a | 본 행 $R_c$ 0.93~0.97. RL 최소는 A3의 8.64 kN보다 높다. **크기와 $F_{min}$ 위아래, LAS-b 시작 여부는 예측하지 않는다.** 최소 다리 RL | P5r4 판정서 8.2 |
| P-13b | C-8b | 본 행 $R_c$ 0.93~0.97. RL 최소는 A5의 8.51 kN보다 높다. 크기·$F_{min}$ 위아래·LAS-b 시작 여부는 예측하지 않는다. 최소 다리 RL | 같음 |
| P-14 | C-8 probe ↔ 본 행 | 정한 probe의 $R_c$와 본 행 $R_c$가 비트 같다(argv가 `--duration`만 다름) | 결정론 실행(P5r4 판정서 8.4) |
| P-15 | 전체 | 새 FAULT·실행 오류 0, `errors 0`, `MIXED_HULL_MODE` 0 | 재발 방지 4항 |

## 11. 순서와 관문

1. 0단계 H-0 T-3K → 판정(S-14).
2. 하네스 H-1 → H-2 → C-2 행 확정. H-3~H-10은 H-1과 병행 가능(H-3은 H-1 출력의 D-1 재사용 12를 쓰므로 H-1 뒤에 판정).
3. Chrono C-1·C-3·C-4·C-5·C-6·C-7과 O-C5 probe는 H-0 판정 뒤 바로 시작할 수 있다. C-2는 H-2 뒤. C-8 본 행은 그 행의 $k$가 정해진 뒤.
4. 묶음마다 아래 관문을 통과해야 시작·판정한다.

### 11.1 옵션 × 단계 겹침 표

python-expert가 묶음마다 "행 종류 × (프리셋·래퍼·argv·env)" 표를 만들어 4.2 금지와 4.1 태그가 맞는지 보인다. 실행 전 감사가 대조한다.

### 11.2 G-S 건조 실행

묶음마다 옵션 팔 × 단계 1행(하네스는 1줄, Chrono는 `--duration`만 짧게)을 같은 커밋에서 돌려, 판정 도구가 읽는 키 경로(4.2 기록 확인 키, 7.2 분류 키, 7.4 기록 키, 6절 정체성 키)가 **실제로 있음**을 확인한다. 값은 출력하지 않는다. G-S 결과는 판정하지 않는다. O-C5는 probe가 G-S를 겸하지 않는다(probe는 시작 조건 키만 읽음). C-8 G-S는 $k$ = 1(A행 바닥)로 `--duration`만 짧게 돈다.

### 11.3 러너 로그

`tools/verif/log_errors.py <러너 로그 폴더>` 종료 0(단계별 `errors 0`, `.done exit=0`)을 실행 중 점검과 판정 전에 확인한다.

### 11.4 자리표시

`tools/verif/placeholder_scan.py <prelaunch>/*.json` 종료 0. 판정서의 채울 칸(14절 `OC5A_SENTENCE`·`OC5B_SENTENCE`·`G1_VB_PROP_SENTENCE` 등, 중괄호 없는 대문자 이름)은 판정서 커밋 전에 모두 값으로 바꾼다. 남으면 S-11.

## 12. 비용 (가정, 사용자 결정 R-3 반영 재계산)

### 12.1 단가

| 엔진·행 종류 | 단가 [s/행] | 근거(1.1절) |
|---|---|---|
| SCM 균일·패치 토양(C-2 SCM, C-3, C-5 SCM) | 6,649~8,898 | B1 본 배치 6행 실측, P 4병렬, `--threads 4`, 훅 fast(사용자 지시 "B1 배치 4병렬 행당 6,600~8,900 s") |
| C-3 상한만 | 12,600 | 명세 436.9.7 어림(B1 상한보다 큼) |
| SCM 혼합 지형(C-4, C-8) | 3,885~4,413 | P5r4 A행 실측, P 4병렬 |
| L2b | 862~1,869 | 3단계 L2b 23행 실측, P |
| L1-R | 600 | 가정(측정 없음) |
| G1 열린 루프 | C-6 1,581, C-7a 1,754, C-7b 1,748 | 저장 G1 VB 1,581·V0 1,576 s × 39.93/36 |
| $R_c$ probe | 900~1,800 | 가정(CHECK까지, 미측정) |

### 12.2 묶음별 (CPU·s 합, 4병렬 실측 단가)

| 묶음 | 행(초안) | 행(이 문서) | 비용 [ks](이 문서) | 초안 비용 [ks] |
|---|---|---|---|---|
| C-1 | 10 | 10 | 7.6~13.6 | 약 7 |
| C-2 | 4~10 | 4~10 | 15.0~60.9(최소 L2b 2 + SCM 2, 최대 L2b 4 + SCM 6) | 19~46 |
| C-3 | 2 | 2 | 13.3~25.2 | 약 25 |
| C-4 | 4 | 4 | 15.5~17.7 | 약 17 |
| C-5 | 35 | 35 | 102.4~128.2(L2b 24: 29.3~30.3, SCM 11: 73.1~97.9) | 186~210 |
| C-6·C-7 | 3 | 3 | 5.1 | 5.1 |
| C-8 O-C5 | 1 + probe 2~3 | **2 + probe 2~6** | 9.6~19.6(본 행 7.8~8.8 + probe 1.8~10.8) | 6~10 |
| **Chrono 합** | 59~65 + probe 2~3 | **60~66 + probe 2~6** | **168.5~270.3** | 265~320 |
| (J_P 재사용 실패 시) | – | +12 | +10.3~22.4 | – |
| 하네스(H-0~H-10) | 360 + 9,800 | 360 + 9,800 | 약 740(변화 없음) | 약 740 |

- **R-3(V0 짝)로 늘어난 것**: Chrono 행 +1(C-8b), probe 최대 +3, 비용 +4.8~9.8 ks(본 행 3.9~4.4 + probe 0.9~5.4).
- C-5가 초안보다 작은 이유: 초안은 개정 12의 옛 어림(훅 채택 전, P/E 혼합)을 썼다. 저장 3단계 SCM 11행 실측 합은 168.6 ks(훅 채택 전, P/E 혼합)이고, 이를 상한 민감도로 두면 Chrono 합 상한은 약 311 ks다.
- 벽시계(어림): SCM·혼합·probe는 P에서 4병렬(16 논리 CPU) — CPU·s 합 129.9~218.9 ks → **9.0~15.2 h**. probe는 행마다 직렬 최대 3건(최대 약 1.5 h)이 C-8 본 행 앞에 온다. L2b·L1-R(38.6~51.4 ks)은 compute-scheduler-expert 배치(E에 두면 E/P 약 2.4~2.5배). 하네스 약 740 ks는 28 작업자에서 약 7.5 h(D-1 실측 비율). 전체 **약 1~2일**. 배치표·동시 개수·예약은 compute-scheduler-expert가 정한다.

## 13. 판정서에 적을 것

판정서 `06_analysis/02_control/verif_matrix/v5_resume_4368_judgement.md`에 다음을 모두 적는다.

1. 이 문서와 부록 A의 sha256, `git_at_start`, 묶음별 실행 기간·러너 로그 경로.
2. 묶음별 상태(8.1), v5 종합 판정, 멈춤이 있었으면 그 조건·사용자 결정.
3. 4.2 기록 확인 결과(행 수·어긋난 수), 6절 정체성 표(SCM 행 `num_threads_chrono`·`start_env`·`pool`·`planned_pool`·`placement`·훅).
4. 7.2 분류 표(묶음 × 분류 줄 수), K1 막힘 계열 목록, 미작동 줄 해시 비교 결과.
5. 7.3 J_P 판독 결과와 재사용 여부.
6. 10절 사전 예측 대조(맞음·틀림, P-1·P-2 결과 먼저).
7. 9절 두 경로: 경로별 작성자·읽은 것, 출력 sha256, K-10 대조 결과, 정의가 다른 곳 표.
8. O-C5: 5.4 절차 기록(행마다 probe 수, $k$, 바닥 각, $R_c$), 7.4 기록 항목, 멈춤 여부.
9. 시작 조건 밖 행 목록과 그 행들의 $F_{min}$ 하회(L-5 근거).
10. 11절 관문 결과(G-S 목록 sha, `log_errors.py` 출력 경로, `placeholder_scan.py` 결과), 실행 전 감사 리포트 경로·sha.
11. 14절 한계 문장 L-1~L-5(채울 칸을 값으로 바꾼 것).

## 14. 한계 문장 (판정서 한계 절에 그대로, 논문은 문체만 맞춤)

**L-1 비틀림 이득과 θ 채널 $M_s$** (원본 `06_analysis/02_control/k2b/twist_gain_margin.md` 5절)

> 하네스는 잠긴 다리의 로드측 강성이 없어 비틀림 루프 이득이 실기보다 최대 1/1.3배 작다. 실기 이득에서도 비틀림 채널은 $M_s \le 1.25$, GM ≥ 6.0, PM ≥ 73.7°이다. 다만 오거 상단·β 1.6 GPa·마스트 대리 조합 한 점에서 자세 θ 채널 $M_s$가 1.53(기준 1.5)으로, 이 점은 비틀림 이득과 무관한 상계 대리값이며 L1-R Chrono 대표 행이 판정한다.

**L-2 LOC 앵커 단일 표본 기울기** (원본 `06_analysis/02_control/k2/judgement/loc_anchor_review.md` 4절, `06_analysis/02_control/k2/loc_shadow/hsh_report.md` 0절)

> 크롤러 이탈 확인(LOC) 때의 틈 추정 기준은 이탈 순간 한 주기(0.1 s)의 원시 기울기를 자세로 쓴다. 그래서 단단한 바닥의 이탈 과도에서는 틈 추정이 ±(10~20) mm 흔들리고, 균일 연약 지면 Chrono에서는 −5.5~+2.7 mm다. 중심 1 s 평균을 쓴 그림자 추정과 비교하면 D-1 토양 계열 하네스 456줄에서 차이가 −18.1~+0.53 mm였고, 판정 여유 안쪽에 든 줄은 없었다. 그 밖 묶음은 미측정이다. 추정기 수정은 v5 뒤 과제로 둔다.

**L-3 하네스 $k_{lock}$ 미포함** (원본 `06_analysis/02_control/k2/judgement/k2_dyn_sensitivity.md` 덧붙임 A)

> 하네스 축소 모델에는 잠긴 다리의 로드측 기름 기둥 강성 $k_{lock}$이 없어, 늦게 닿는 대각 쌍이 먼저 래치된 쌍의 하중을 가져가는 비틀림 결합(M2)에서 뒷다리 하중 손실을 약 25 % 작게 본다(β 1.0 GPa에서 −5.2 대 −7.0 kN/mm). 그래서 하네스의 TOUCH·이탈 판정은 이 기구에 대해 비보수 쪽이고, 잠김 상태 판정에 대한 영향은 방향이 정해지지 않았다. v5 하네스 결과는 이 모델 그대로 판정했으며, $k_{lock}$을 포함한 Chrono L1-R 대표 행이 교차 확인을 맡는다.

**L-4 유량 분배 법칙** (원본 `v5/v5_paper_runs_judgement.md` 1.6절, 사용자 결정 11-10 Q-2·11-11 Q6)

> 폐루프 판정(VB)은 우선 분배 법칙을 기준으로 했고, 비례 분배는 열린 루프(J1·G1)에서만 확인했다. G1_VB_PROP_SENTENCE

**L-5 운용 시작 조건 밖의 이탈 뒤 비틀림 하회** (원본 `las_p5r4_k1_judgement.md` 8.2절·"D-2 진단 요약"·10절 D-2, 사용자 결정 2026-11-12)

> 혼합 지형(강체 바닥 + 전방 우측 패드 아래 연약 패치) Chrono에서 채택 제어기는 크롤러 이탈 뒤 0.5~0.7 s에 대각 반대 다리(후방 좌측)의 실린더 힘이 $F_{min}$ 아래로 내려갔다(크롤러 강성 ×3·VB 8.64 kN 195 ms, ×1·V0 8.51 kN 67 ms). 주성분은 동적 과도가 아니라 준정적 4점 비틀림이다. 이탈 감속(LAS-b)이 끝난 다음 주기에 명령이 원래 속도로 돌아가며 생긴 비틀림 계단과 연약 패치 침하가, 이탈 뒤 네 다리 기름 기둥 강성(명령 비틀림 1 mm당 후방 좌측 하중 약 −6.5 kN)을 거쳐 하중으로 옮겨졌다. 이 행들은 실행 시작 자세 비 $R_c$ 1.035~1.076으로 운용 시작 조건($R_c \le 1$) 밖이다. 모델 상부체는 강체라 비틀림 강성을 크게 보므로 이 값은 보수 쪽이고, 유압유 체적 탄성 계수 β에 민감하다. OC5A_SENTENCE OC5B_SENTENCE 이탈 감속 끝 처리의 재설계는 v5 뒤 과제로 둔다.

- 채울 칸: `G1_VB_PROP_SENTENCE` = C-6 결과 한 문장(값만, 해석 없음). `OC5A_SENTENCE` = "운용 시작 조건 안($R_c$ = 값)으로 옮긴 같은 조건(크롤러 강성 ×3·VB)에서 후방 좌측 최소 힘은 값 kN이었다." 꼴, `OC5B_SENTENCE` = 같은 꼴(×1·V0). 7.4 멈춤에 걸리면 L-5 전체를 사용자 결정 뒤 다시 쓴다. C-8 본 행 $R_c > 1$이면 그 행의 칸은 "운용 시작 조건 안으로 옮기지 못했다($R_c$ = 값)."로 쓴다.
- C-4 켬 팔에서 같은 하회가 다시 나오면 그 값도 L-5 근거로 판정서에 함께 적는다.

## 15. 결과 전 사용자 결정 기록

| 날짜 | # | 결정 | 반영 |
|---|---|---|---|
| 2026-11-11 | Q1 | (a) 하네스 재사용분 전부 재실행(H-10 462 + dg3 v4_on 135), Chrono J_P 12만 7.3 조건으로 재사용 | 5.1, 5.2, 7.3 |
| 2026-11-11 | Q2 | (b) G1 속도 낮춤 VB + V0 2행 | 5.3 |
| 2026-11-11 | Q3 | (a) T-3K는 0단계로 먼저, 판정 뒤 본 묶음 | 11, S-14 |
| 2026-11-11 | Q4 | (a) dg3 off 135 전부 | 5.1 H-7 |
| 2026-11-11 | Q5 | (a) LOC 앵커 그림자 훅을 걸지 않음 | 4.2, L-2 |
| 2026-11-11 | Q6 | 넷째 한계 문장 = L-4 | 14 |
| 2026-11-12 | E-1 | P5r4 `미달` 확정, P0 유지 | A-1 |
| 2026-11-12 | E-2 | O-C5 기록 행, 범위 안 하회면 다시 묻는 멈춤 | 5.4, 7.4, S-9 |
| 2026-11-12 | E-3 | 한계 문장 L-5 | 14 |
| 2026-11-12 | E-4 | LAS-c는 범위 밖 | 0-5 |
| 2026-11-12 | R-1 | 바닥 각 절차 허용 ±0.02, probe 최대 3건 | 5.4 |
| 2026-11-12 | R-2 | C-4는 `_LAS_K1`로 다시 돌린다(P5r4 결과 재사용 안 함) | 5.2 C-4 |
| 2026-11-12 | R-3 | **V0 짝을 둔다**(초안 추천 '없음'과 다름) | 5.2 C-8b, 5.4, 7.4, 12 |

## 16. 구현 목록 (위임, 봉인 전 정의·봉인 뒤 실행 전 감사)

| 대상 | 일 |
|---|---|
| python-expert | A-4 행 생성기 5개 기대 태그 `_LAS_K1`, 개정판 `u3_judge`(태그 상수·경로만), 4.3 출력 이름, `steps_h2.json` 갱신과 줄 수(5.1), 7.2 분류 판정 모듈, 7.3 J_P 사건 판독 도구, 4.2 기록 확인 검사, 11.1 겹침 표, 11.2 G-S(하네스), 경로 1 판정 도구 |
| cad-expert | C-1~C-5 행 정의 태그 갱신 확인, C-4 끔 팔 `--las-off --k1-order-gate on`, C-4 켬 팔 ↔ P5r4 A1·A3 `option_diff`, C-6·C-7 3행(`check-sources`), C-8a·C-8b 행 정의(바닥 인자만 다름), $R_c$ probe 실행기·판독기(5.4-1~3, 시작 조건 키만 출력), `PROBE_DURATION` 결정, A-7 스냅숏 사용 행 확인, 행별 est_s, Chrono G-S |
| control-expert 아닌 경로 2 작성자 | 9.2 요건의 경로 2(묶음별). 작성자 배정은 메인 세션 |
| compute-scheduler-expert | 배치표(SCM P 4병렬, L2b·하네스 배치, probe 직렬), 예약 |
| verif-protocol-auditor | 묶음마다 `[시점] 실행 전`, 판정서 커밋 전 |

## 17. 가정

| 가정 | 값 | 근거 |
|---|---|---|
| 하네스 R4c30 사건 판독(초안 단계) | 줄 문자열에 `INFO_LOC_FLAT_SOIL_MARGIN`이 있으면 R4c30 적용 | 저장 기록이 K1 전이라 `_SKIPPED`가 없다 |
| G1 속도 낮춤 인자 | J1과 같은 `--lift-s 31.93 --lift-speed-fraction 0.87684` | 같은 펌프·실린더·명령 행정 |
| O-C5 절차 | 목표 0.95, 허용 0.02, probe 최대 3건, 첫 축척은 $R_c$가 바닥 각에 비례한다는 가정 | 사용자 결정 R-1 |
| C-8b 바탕 | A5 조건(Kc1, V0) | 초안 R-3 (b) 문구, 확인 필요 질문 Q-A |
| 비용 단가 | 12.1 표 | 실측 + 가정(L1-R, probe) |
| T-3K 결과 | 통과로 가정하고 계획 | 미실행 |

## 부록 A. 기준 파일 (봉인 때 다시 계산해 대조, sha256 전체, 2026-11-13 `3d41083` 작업 트리, `.sha256` 기록과 모두 일치)

| 파일 | sha256 |
|---|---|
| `06_analysis/03_hydraulic/coupled/v5/v5_criteria.md` | `06ed0384fb942cfdf9ab481878ffd5f19d5faab4e6163aa986dcdda5156e080e` |
| `…/v5_criteria_rev1.md` | `cbfac2b2de571500fbf5410dd5456bfa82d4a05cf25f21c76feb25fab1308fab` |
| `…/v5_criteria_rev2.md` | `e120474b8ebd721e6edc4fec8eef811ce810006b8c489e38cecbb7ae5caeed77` |
| `…/v5_criteria_rev3.md` | `7084da25c6129681086efc4fbc5afb315d7b4d424cbed123746ec32b4ea61ec2` |
| `…/v5_criteria_rev4.md` | `642e96f9cfd20a9c2a016ed128a6ce7d584718e5728d6008640f8703a5acbd72` |
| `…/v5_criteria_rev5.md` | `945f714660cd3ec7e749151bcd81b1f9da35b6001d7fd9c7e2cfeee21fcd320b` |
| `…/v5_criteria_rev6.md` | `fd5117031ef460cf4c6aa74807b2e73de984b014abb89a952b593499841da39c` |
| `…/v5_criteria_rev7.md` | `9ccde7a5a4128317ed832dd2f92cd2368280f18cefa6827f1b1731c6d4e9aab3` |
| `…/v5_criteria_rev8.md` | `c6ec89f71c1d8de4c06000568c2e5978fd7f9fe58a53defea728f2f4886bb25f` |
| `…/v5_criteria_rev9.md` | `3c50dda50ca6dca60177f26d91d86c009eeb4f9321f5ffd0c98ddc27cf62e981` |
| `…/v5_criteria_rev10.md` | `bd65db24f68a6d4c3a8346447a0cbfdd89e97cd07f4b295237127c304174e182` |
| `…/v5_criteria_rev11.md` | `ca6b5c95d8f544ff8ec5db2e1ec193d2b200df74c2e9c7decdb56b61757e2ecb` |
| `…/v5_criteria_rev12.md` | `e02d63cc1290383ee85d9a1f3a20c6348224b60999cccaf8d587cf610c5f5eb2` |
| `…/v5_criteria_rev12a.md` | `e171141dce180fbb48493b9b95503ff3577d16f17cc54061ce3ad6e9efd51458` |
| `…/v5_criteria_rev12b.md` | `0d17f87e9532d558efcab9fa89648e2790ece9c7568a802fbaa4c7631824e75d` |
| `06_analysis/02_control/verif_matrix/d1_selection_rules.md` | `51dea528e57fa0c4378cda110addb73da20339535e16189452af2d06b60736e9` |
| `…/d1_selection_rules_rev1.md` | `eb730bddae35e76bc2569503605dea714b066fa42de7bc7b98efdde3edb3e868` |
| `…/u3_u6_rerun_rules.md` | `8de318825764114ad14afcec362c87c1e01a2ad47195b8491b1c96056e1960b3` |
| `…/u3_u6_rerun_rules_rev1.md` | `2c5e69213b29fc930c478306676efc72b515d67af08634adab3eba2d05f5f15d` |
| `…/u3_u6_rerun_rules_rev2.md` | `be1584a4448d68a30c4fe9ec613d3d7b3cb0b47169c2f5eff72e9a9ca0776880` |
| `…/u9_targeted_rules_rev1.md` | `644005b706ba46cebba11b975ded474226cc4eab5030ee18e9f91dacd2d14587` |
| `…/las_targeted_rules.md` | `00b48fd834d81b9d499015f2d44380623e9fbcb2f1515913a8fd0589503eaf40` |
| `…/las_targeted_rules_rev1.md` | `0d5f59f8e4a09448b93e0cde42adb7d23c2f99f6b365809876efaa6212d27625` |
| `…/las_targeted_rules_rev2.md` | `6be736cb98cea34e4a606606b4009668bbc1470c8a7db23b6a119ef033c97960` |
| `…/las_targeted_rules_rev3.md` | `956f65c74e36eb8fe921dc6399b0d5f2f04099b7852380362351f658c9791cd1` |
| `…/las_targeted_rules_rev4.md` | `05fbde22009c10b74ddf0df071452a99631bb319c2f482df83be59adfad1de6d` |
| `…/las_targeted_rules_rev4a.md` | `3cbbfb5d8afda9075bf9631accf1b8bee4c1ee02edafa34a7869091175a73b15` |
| `…/las_targeted_rules_rev4b.md` | `add921e4978ef16abcc22dfc88dc25e51a770dc98d2d540526f48cf6ea7a6f3f` |
| `…/las_targeted_rules_rev4c.md` | `7e45993f667382f56aeb1b72bb5e7023ecfe3048a3723ac050cefc3b2a721417` |
| `…/las_targeted_rules_rev5.md` | `879d0e4d715b2e9f4e51257863fc259ccfe48105ca019299547d58dca24949b2` |
| `…/las_k1_rules_adopt2.md` | `fb3a5696f24385e81acc9c564500b5e5a0547db45a5335272e7d18400f1e68e8` |
| `…/las_k1_rules_adopt_rev1.md` | `730dbb3d30dffca6d652953c22b62563141beeee6af6f045d6b2cb59f60deb65` |
| `…/las_p5r4_k1_judgement.md`(봉인 아님, 1.1 근거) | `5e9fb33b7419d624d8dc305ad93121be090802cc5c85ea29fbc823e019fc9e2f` |
| `…/v5_resume_4368_plan_draft.md`(봉인 아님, 입력 초안) | `141e4958f39b7c7470bb4c66003877f2af0c14c93300a705eb60988e2a04033d` |

## 봉인 때 바꿀 머리 줄 (메인 세션)

1. 파일 이름: `v5_resume_4368_rules_seal_candidate_draft.md` → `v5_resume_4368_rules.md`(같은 폴더). 초안 파일은 지우지 않고 그대로 둔다.
2. 1행을 다음으로 바꾼다:
   `# v5 재개 검증 436.8 판정 규칙 (제어기 `final_C4G2_LAS_K1`, 봉인)`
3. 3행(첫 글머리 "상태")을 다음으로 바꾼다:
   `- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_seal_candidate_draft.md`와 1·3·5행만 다르다.`
4. 5행("시점")을 다음으로 바꾼다:
   `- **시점: 436.8의 어떤 실행 결과도 없을 때(봉인 SEAL_TIME, 봉인 커밋 SEAL_COMMIT).** 436.8 묶음(0단계 T-3K 포함)은 한 줄도 돌지 않았다. 이 규칙을 쓰려고 읽은 것은 1절에 모두 적었다.`
   - `SEAL_TIME`(예: 2026-11-13 10:00:00 +09:00)과 `SEAL_COMMIT`(봉인 파일을 넣는 커밋의 앞 커밋, 7자리)은 메인 세션이 값으로 바꾼다. 이 두 이름 말고는 본문을 바꾸지 않는다.
5. 바꾼 뒤 sha256을 계산해 `v5_resume_4368_rules.sha256`에 `<sha256>  v5_resume_4368_rules.md  sealed <SEAL_TIME 값> (436.8 v5 resume rules: v5 criteria rev13 + u3_u6 rev3 + O-C5 VB/V0 record rows; thresholds unchanged)` 한 줄로 쓴다.
6. `.gitattributes`에 `06_analysis/02_control/verif_matrix/v5_resume_4368_rules.md -text`와 `…/v5_resume_4368_rules.sha256 -text`를 더한다.
7. `tools/verif/seal_check.py`로 확인한 뒤 커밋한다. 봉인 뒤 이 문서를 고치지 않는다. 고칠 것이 생기면 `v5_resume_4368_rules_rev1.md`로 새로 봉인한다.
