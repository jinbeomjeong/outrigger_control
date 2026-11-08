# v5 유압 연성 인수 기준 — 개정 12 (3단계 Chrono 묶음을 LAS 태그로 재실행)

작성: control-expert, 2026-11-08.

> **상태: 봉인(2026-11-08).** SHA-256과 봉인 시각은 같은 폴더 `v5_criteria_rev12.sha256`에 있다. 이 파일은 더 고치지 않는다.
> - **LAS 태그 재실행 결과를 보기 전에 정한다.** 3단계 Chrono 행의 LAS 태그 재실행은 아직 하지 않았다. 이 판을 쓰며 본 것은 다음뿐이다.
>   - 저장 `batch.json` 두 개의 행 이름·설정·짝·`--threads`·풀·벽시계: `07_results/S9/batch_V5-STAGE3_20261107_184239`(토양 11), `batch_V5-STAGE3_20261107_184341`(강체 23)
>   - `s9_batch.py`의 행 정의(worktree `11d28c6`)
>   - 저장 행의 판정 값은 이 판을 쓰며 열지 않았다.
> - 사용자 결정(2026-11-08, Q2): 3단계 Chrono 저장 행 전부(VB·LS·토양 VB와 그 V0 짝)를 LAS 태그로 재실행한다. 추천안(L2b 그림자 + 토양 표시)은 채택되지 않았다.
> - 판정 항목·문턱은 바꾸지 않는다.

**고치는 판**: 봉인본 `v5_criteria.md`(`06ed0384fb942cfd`)와 개정 1~11을 순서대로 덮어 읽은 판이다. 개정 11은 `ca6b5c95d8f544ff`다. 앞 판들과 각 `.sha256`은 고치지 않는다. 여기 적지 않은 항목은 앞 판 그대로다.

규약: 개정 8과 같다(음되먹임, $T_s$ 0.1 s, $d$ = 1, 압력 bar 게이지).

## 1. 바뀌는 항목

| # | 앞 판 위치 | 앞 판 문구 | 새 문구 |
|---|---|---|---|
| 1 | 개정 11 2절 "3단계 Chrono 저장 행" | LAS-b 결과로 읽지 않는다. 처리는 따로 정한다 | **LAS 태그 재실행 결과로 새로 판정한다.** 저장 행은 **전환 전 기준선**으로만 보존한다. 저장 행의 판정 문구(개정 6 `불일치` 확정, 개정 7 참고 재판정, 개정 8 7.3·개정 10 해시 대조)는 전환 전 제어기의 기록으로 남긴다. v5 결과로 인용하지 않는다 |
| 2 | 개정 6 3절(3단계 묶음 정의) | 제어기 `final_C4G2` | 재실행 제어기: VB·LS 행은 `final_C4G2_P3_LAS`(③ revision 4 + LAS-b, 개정 8·11), 그 밖 행(V0, V0v, S6SEED)은 `final_C4G2_LAS`. 플랜트·사례·사건·시드 인자는 저장 행과 같다 |
| 3 | (추가) 짝 비교 | — | 2.2절 |

## 2. 재실행 범위

### 2.1 행 목록 (34 + 짝 3 = 37행)

강체 L2b(`run_S8C.py`, 저장 `batch_V5-STAGE3_20261107_184341`, P코어)

| 행 | 저장 설정 | 재실행 태그 | 짝 |
|---|---|---|---|
| `E_G4_Fs4` | VB | `final_C4G2_P3_LAS` | V0 짝 = `batch_FINAL-R-C4G2_20261105/final_E_G4_Fs4/E_G4_Fs4`(3단계 밖 저장 행) → **짝 행 P-1로 재실행** |
| `E_G4_Fs4_ph0.05` / `E_G4_Fs4_ph0.05_V0` | VB / V0 | `final_C4G2_P3_LAS` / `final_C4G2_LAS` | 서로 짝 |
| `G1R_FS24_FL_top_o050_Fs0` / `G1R_FS24_FL_top_o050_Fs0_V0` | VB / V0 | `final_C4G2_P3_LAS` / `final_C4G2_LAS` | 서로 짝 |
| `E_G4_Fs8`, `E_G4_Fs8_LS1`, `E_G4_Fs8_LS4` | VB, LS1, LS4 | `final_C4G2_P3_LAS` | LS − VB |
| `E_RE1bF_Fs8`, `E_RE1bF_Fs8_LS1`, `E_RE1bF_Fs8_LS4` | VB, LS1, LS4 | `final_C4G2_P3_LAS` | LS − VB |
| `K0V_top_fup3.5_Fs0`, `…_LS1`, `…_LS4` | VB, LS1, LS4 | `final_C4G2_P3_LAS` | LS − VB |
| `E_RE1bF_Fs0`, `K0V_top_fdown3.5_Fs0`, `K0_top_fdown3.2_Fs0`, `K8_top_rpB_Fs8`, `K0V_top_roll5.5_Fs0`, `K0_top_fup3.2_Fs0`, `K0_top_rpBop_Fs0`, `K8_top_fdown3.5_Fs8`, `S_top_fdown3.5_wika_Fs8` | VB | `final_C4G2_P3_LAS` | – |

- 강체 합계: VB 15, LS 6, V0 2 = 23행.

토양 SCM(`run_S9.py level`, 저장 `batch_V5-STAGE3_20261107_184239`, 모두 `--threads 4`)

| 행 | 저장 설정 | 저장 풀 | 재실행 태그 | 짝 |
|---|---|---|---|---|
| `P3b_J1_B_top_Fs4` / `P3b_J1_B_top_Fs4_v0v` | VB / V0v | P / E | `final_C4G2_P3_LAS` / `final_C4G2_LAS` | 서로 짝 |
| `P3b_J2_B_top_Fs4_m1p1_t180` / `…_t180_v0v` | VB / V0v | P / E | `final_C4G2_P3_LAS` / `final_C4G2_LAS` | 서로 짝 |
| `S9SL_X6rpsa_J1_B_top_Fs4_r3p85_p0` / `…_p0_v0v` | VB / V0v | E / E | `final_C4G2_P3_LAS` / `final_C4G2_LAS` | 서로 짝 |
| `P3b_J2_B_top_Fs4_m1p1_t180_seed20261026`, `…_seed20261027`, `…_seed20261028`, `…_seed20261029` | S6SEED(유량 끔) | P | `final_C4G2_LAS` | 시드 기준 행 → **짝 행 P-2** |
| `P3b_J2_B_top_Fs4_m1p1_t180_seed20261026_flow` | S6SEED(유량 켬) | P | `final_C4G2_LAS` | 시드 기준 행 → **짝 행 P-3** |

- 토양 합계: VB 3, V0v 3, S6SEED 5 = 11행.

3단계 밖 짝 행(저장 판정의 비교 기준이 전환 전 제어기이므로 같이 재실행)

| # | 행 | 원 정의 | 재실행 태그 |
|---|---|---|---|
| P-1 | `E_G4_Fs4` V0 | `batch_FINAL-R-C4G2_20261105/final_E_G4_Fs4`의 argv(s9_batch `V5_FINAL_R_C4G2`) | `final_C4G2_LAS` |
| P-2 | S6 저장 시드 행, 유량 끔 | `v5_s6_seed_rows`가 시드를 바꾸기 전의 FINAL-REP-X S6 argv(`P3b_J2_B_top_Fs4_m1p1_t180` 계열, 저장 시드) | `final_C4G2_LAS` |
| P-3 | S6 저장 시드 행, 유량 켬 | 같은 함수의 COUPLED_eta085 S6 argv(저장 시드) | `final_C4G2_LAS` |

- 저장 행 이름은 `batch.json`의 `case` 그대로다. 재실행 행 이름은 cad-expert가 정한다(새 배치 폴더 안에서 같은 이름, 또는 접미사 `_las`). 결과 기록에 저장 행 경로(`stored_result`)를 둔다.
- 행이 34 + 3과 다르거나 저장 행과 사례 인자(플랜트·사건·시드·`--threads`)가 다르면 실행하지 않고 멈춘다.

### 2.2 짝 비교 규칙

| 비교 | 규칙 |
|---|---|
| 판정 | 재실행 결과에 앞 판들의 3단계 판정 항목을 그대로 적용한다. 대상은 T4·T5(개정 6·7 E·B1), J11, J-P3(개정 8, ③ 켬 행 전부, 개정 11 #4), D2·잠금 창 항목이다. 판정 문구는 이 새 결과로 쓴다 |
| VB ↔ V0(V0v) 짝, LS − VB, 시드 대 저장 시드 | 앞 판 규칙 그대로다. 짝의 **양쪽 모두** LAS 태그 재실행 결과끼리만 비교한다. 재실행 행과 저장 행을 섞어 짝을 만들지 않는다 |
| 재실행 ↔ 저장 행(같은 이름) | **기록만** 한다. 명령(`controller_commands`, run_S8C는 `r8_series` `issued_u`) 배열이 비트 단위로 같고 제어기 사건이 같으면 "LAS-b 미작동·③ 미작동 확인"으로 적는다. 다르면 "작동"으로 적고, 첫 다른 주기와 그 주기의 `INFO_LIFTOFF_SLOW*`·대체 사건을 함께 적는다. 이 비교는 판정에 쓰지 않는다 |
| 해시 비교가 성립하는 조건 | 저장·재실행이 **같은 `--threads`**(토양 4, 강체 저장 argv와 같음), 같은 `OMP_WAIT_POLICY`이고 **둘 다 P코어**일 때만이다. 저장 행이 E코어였던 4행(`P3b_J1_B_top_Fs4_v0v`, `P3b_J2_…_t180_v0v`, `S9SL_…_p0`, `S9SL_…_p0_v0v`)과 조건이 다른 행은 "조건 다름, 해시 비교 없음"으로 적는다. 판정에는 영향이 없다 |
| meta 차이 | 해시 비교가 성립하는 행에서 같은 명령인데 meta가 다른 것은 허용한다. 허용 키는 `controller_tag`, `liftoff_approach_slow` 블록, ③ 키(개정 10 1절)이고, `fallback_rod_estimate_Pa`는 개정 10 조건 A·B·C를 지킬 때만이다. 그 밖 키가 다르면 기록하고 python-expert에 원인 확인을 넘긴다 |

- 재실행 중 실패·오류 행이 있으면 그 묶음 판정을 하지 않고 멈춘다(앞 판 규칙).
- VB 고유 실패(V0 짝 통과, VB 실패)는 앞 판대로 묻는다.

## 3. 그 밖 (판정 무관, 기록)

- 개정 8 7.3과 개정 10의 Chrono 해시 대조(`E_G4_Fs8`, `S_top_fdown3.5_wika_Fs8`)는 닫힌 검사다. 저장 행 기준선의 기록으로 남는다.
- 3단계 Chrono 재실행의 비용·배치는 compute-scheduler-expert가 정한다. 토양 행은 SCM 실행 규칙(스레드 수 고정·기록, P 우선, `OMP_WAIT_POLICY=PASSIVE` 시작 전)을 따른다.

## 4. 가정

| 가정 | 값 |
|---|---|
| 짝 행 P-2·P-3의 정의 | `s9_batch.v5_s6_seed_rows`의 입력 argv(시드를 바꾸기 전)와 같다. cad-expert가 행 정의로 확정한다. 다르면 실행하지 않고 멈춘다 |
