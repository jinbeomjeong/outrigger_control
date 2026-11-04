# C4G2 Chrono 다음 묶음 행 표 (cad-expert 전달용)

공통 조건: 유량 제한 끔, `OUTRIGGER_ROD_SIDE_MECHANICS=one_sided_parallel`, 전체 종료 규칙(READY 뒤 끝까지, 40 s 절단 없음), L2b-NSC 강체 크롤러, 패드 틈은 `L2bModel(pad_gap_offsets_m=...)`(FL, FR, RL, RR).

코드: python-expert의 **G2 수정 커밋**(판정량 $|n^T(l-\rho r)|$). 182f8d9가 아니다. 커밋 해시와 `c2.py` SHA-256을 `code_state.json`에 남기고, 시작 전 `G2 수정 커밋`을 실제 해시로 바꾼다.

| 약칭 | 프리셋 호출 |
|---|---|
| C4G2+K1 | `C2Config().with_10hz_d1(touch_twist_hold=True, reapproach_retrigger_two_samples=True)` |
| C4G2 단독 | `C2Config().with_10hz_d1(touch_twist_hold=True)` |
| 끔 | `C2Config().with_10hz_d1()` |

폴더 이름: `07_results\S8\c4g2_<행 이름>_<시각>\<사례>`. 판정은 `judge_batch`로 읽을 수 있게 사례 폴더 이름을 사례 ID로 둔다.

## 행

| # | 행 이름 | 사례 ID | 틈 (mm) | 설정 | 끔 짝 |
|---|---|---|---|---|---|
| 1 | R16_mirror2_d000_C4G2K1 | G1L_RE1bF_FL_top_o050_Fs4 | −2.00, +2.00, −2.00, +2.00 | C4G2+K1 | scratchpad `cad_asym\runs_r16\r16_mirror2_d000` (02efc57) |
| 2 | R16_mirror2_d070_C4G2K1 | G1L_RE1bF_FL_top_o050_Fs4 | −1.30, +2.70, −1.30, +2.70 | C4G2+K1 | scratchpad `cad_asym\runs_r16\r16_mirror2_d070` (02efc57) |
| 3 | R12_C4G2K1 | E_G4_Fs4 | 없음 | C4G2+K1 | `07_results\S8\final_E_G4_Fs4_20261030_233941` |
| 4 | R16_mirror2_d000_C4G2 | G1L_RE1bF_FL_top_o050_Fs4 | −2.00, +2.00, −2.00, +2.00 | C4G2 단독 | 1행과 같음. K1 효과는 1행과 비교 |
| 5 | R15_C4G2K1 | G1L_RE1bF_FL_top_Fs0 | 없음 | C4G2+K1 | `07_results\S8\final_G1L_RE1bF_FL_top_Fs0_20261031_003000` |
| 6 | R9_mirror2_d035_Fs4_C4G2K1 | A_bottom_rpB_Fs4 (아래 주의) | −1.65, +2.35, −1.65, +2.35 | C4G2+K1 | **없음**(결정 필요). F_s 0 비교 대상은 `c4g1_R9_mirror2_d035_20261104_211444`(켬), 8행(끔) |
| 7 | R9_mirror2_d000_off | A_bottom_rpB_Fs0 | −2.00, +2.00, −2.00, +2.00 | 끔 | 이 행 자체가 끔 짝. 켬은 `c4g1_R9_mirror2_d000_20261104_211444`(15176d1) |
| 8 | R9_mirror2_d035_off | A_bottom_rpB_Fs0 | −1.65, +2.35, −1.65, +2.35 | 끔 | 이 행 자체가 끔 짝. 켬은 `c4g1_R9_mirror2_d035_20261104_211444`(15176d1) |

**주의, 6행:** `s8_cases()`에는 `A_bottom_rpB_Fs0`, `A_bottom_rpB_Fs8`만 있다(`run_S8C.py` 741~745행). `A_bottom_rpB_Fs4`는 없으므로 러너에서 `A_bottom_rpB_Fs0`를 복제해 `fs_kN=4.0`으로 바꾸고 사례 ID만 새로 준다. `03_src`는 고치지 않는다. 복제가 `_bc(cid, ...)` 안의 다른 값에 영향을 주는지 cad-expert가 확인한다.

## 보는 양

모든 행 공통: 판정 행 실패 수, TOUCH 끝까지 끔과의 비트 비교(첫 차이 시각), `metrics.py`의 $\tau_{te}$, $D_{te}$, $\hat D$, 목표, $D_{lift}$, 이륙 시각, 다리별 최소, READY, 끝 자세, 행정 최대, 이동 압력, `touch_twist_hold` 메타(`end_reason`, `end_error_m` 포함), 최대 $|u|$ 대 $v_{max}$.

| # | 추가로 볼 양 | 끔 값 또는 기대 |
|---|---|---|
| 1 | 사건 뒤 RL·FR·FL·RR 최소와 부상 시간, 재접근 시작 순서, 재발동 보류 횟수 | 끔: RL 12.40, FR 15.45, FL −11.25 kN(0.80 s), RR −1.41 kN(1.20 s), READY 52.4 s, $D_{te}$ 12.79 kN. 하네스 C4G1+K1 RL 17.56~30.03 kN |
| 2 | 1행과 같음 | 끔: RL 21.16, FR 15.44, FL −11.33 kN(0.80 s), RR −1.43 kN(1.20 s), READY 52.5 s |
| 3 | 사건 뒤 RR 최소, 재READY | 끔: RR 11.14 kN(사건 +1.52 s), READY 42.7 s, 사건 47.7 s. 하네스 기대: 변화 없음. $\hat D$가 데드밴드 안이면 보류 없음 |
| 4 | 1행과 같음. K1 없는 C4G2의 RL | 끔: 1행과 같음. 하네스 C4G1 단독 RL 11.46~11.58 kN(끔 15.2~16.0). F_min 9.41 kN 아래면 보고 |
| 5 | 사건 뒤 RL·FR 최소, 재접근 보류 | READY 끔 55.0 s, 사건 28.05 s. 하네스 RL −0.72 → 8.30 kN, 여전히 F_min 아래. 규칙 종료가 20.1 s대 램프 전에 오는지 확인(하네스에서 관찰) |
| 6 | $\hat D$ 대 $n^T F_{cyl}$ 대 $n^T f_{seal}$(TOUCH 마지막 3표본), 실제 달성 $\tau$, 고착 상태, RL 최소 | $\hat D$ 오차 상한 약 ±7.3 kN(0.32 mm). F_s 0 켬: RL 44.47, $D_{lift}$ 18.59 kN |
| 7 | READY, 끝 자세, 판정 행. 40 s까지 저장 끔 실행(02efc57)과 비트 비교 | 40 s까지 비트 동일 기대. 저장값 RL 41.88 kN, $D_{lift}$ 31.21 kN |
| 8 | 7행과 같음 | 40 s까지 비트 동일 기대. 저장값 RL 29.50 kN, $D_{lift}$ 54.61 kN |

## 참고

- 비용: 지난 묶음 강체 행 약 320~860 s/건. 8건 배치는 compute-scheduler-expert에 받는다.
- 1·2·4행의 끔 짝은 02efc57이고 절단 등 뒤 변경이 없는 끔 경로다. C4G2 쪽 코드의 끔 비트 동일은 보고받은 것으로, 7·8행이 Chrono에서 이를 직접 확인한다.
- 켬 쪽 R9 mirror2는 15176d1(G1) 실행이고 이번 코드(G2)로 다시 돌리지 않는다. 행 6이 G2 코드의 유일한 R9 mirror2 켬이다. 하네스 R9는 두 정의가 같은 값이었으나 Chrono에서 확인한 것은 아니다.
