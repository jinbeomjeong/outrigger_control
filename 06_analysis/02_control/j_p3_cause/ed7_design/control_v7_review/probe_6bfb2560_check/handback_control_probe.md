## 판 7 probe 분석 ① — 사전 예측 대조 (control-expert)

대상은 probe `j9_runs\6bfb2560\ed7_probe_a1`입니다(구현 커밋 6bfb2560, identity start·end `is_clean` true, 654줄, 오류 줄 0). 조건 도구 출력은 `condition_ad7a716e.json`만 읽었고 옛 `condition.json`은 쓰지 않았습니다. 코드는 고치지 않았습니다.
읽기 전용 분석이라 Python↔Julia 교차 검증은 해당이 없습니다. 대신 ③ 조건 읽기는 도구와 독립 계산 두 경로로 비교했습니다. 360개 조건 읽기의 gap 목록이 도구와 정확히 같았습니다(`anomalies.json` = []).
되먹임 부호·단위 규약: 하네스 기름 좌표 `stroke_m`, 압력 bar(=1e5 Pa), 주기 0.1 s(10 Hz 읽기), 다리 순서 FL·FR·RL·RR입니다.

### 판정 요약
| 항목 | 결과 |
|---|---|
| P7-7 (기록) | **정성적으로 맞음**, 수치는 범위에서 조금 벗어남(아래 1절) |
| P7-8 봉인 전 관문(침범·FAULT) | **통과**: D 24줄 J-P3a 조건 침범 0/360읽기, FAULT 0/24, 24줄 모두 final READY |
| P7-8 여유 "≥ +7.9 bar" (예측 수치) | **어떤 양으로 재느냐에 따라 부분 어긋남**(2절). 관문의 멈춤 조건(침범·FAULT)과는 별개입니다 |
| 기록 이상(3절) | 필드 누락·모순 **0건**. 다만 역순 탐침·래치·$n_{rev}$·보호·`completion_known=False` 경로는 probe에서 **한 번도 일어나지 않아 실데이터로는 검증되지 않았습니다** |

### 1. P7-7 (VBMslow × $F_s$ 0, R12 FL 상태)
**근거 줄**: 키 `R12 top-FR-Fs0 o0.0 / o0.05`, `R12 top-RL-Fs0 o0.0`의 FL 첫 탐침 라운드(t 32.1 s). 상태는 $p_h$ 99.39~99.48 bar, s 408.36 mm로, 예측의 상태(99.39 bar, 408.36 mm)와 같습니다.
- 팔 c2: 증인과 위치 목표를 모두 끈 팔이라 수축은 2 mm뿐입니다.
- 팔 a1~a6: 위치 목표를 켠 팔입니다.

| 양 | 예측 | 실측 Mslow | 실측 M(공칭) |
|---|---|---|---|
| 2 mm만(c2) 열림 | 안 열림, 보낸 기름/need 0.92~0.99 | **안 열림**. 명령 2.098 mm / need 2.322 mm = 0.903, 충전 x 최대 2.001 / need 2.330 = 0.859, 행정 E3 변화 0 | 열림. 2.098 / 1.513 = **1.386**(예측 1.41~1.50) |
| 로드 진값 상승(갇힘) | 20.5~21.6 bar | **20.13**(32.1 s), 20.35~20.43 bar(62 s 라운드). 중립 뒤 약 25 bar에 갇힘 | 열림 값 기준 35.6 bar (예측 꼴 28~36) |
| D6 대체 | 0 (상승 > 요구 8.3 bar) | **0**. c2의 판 6 D6에서 로드 판독 상승 19.7 bar, 대체 사건은 모든 줄에서 0 | 0 |
| 위치 목표를 켜면 | 열림 | **열림**(a1~a6). 명령 4.50 mm, E3 2.23 mm, 상승 31.9 bar | 열림 |

- **probe 전체(위치 목표를 켠 팔)**: 증인 라운드 2336개 모두 열림 판정입니다.
  - `not_judgeable` 0, `INFO_D6_NOT_OPENED` 0, `WARN_PROBE_RETRACT_NOT_OPENED` 0, `retract_target_reached` 2336/2336.
  - 깊이를 넘는 추가 수축은 Mslow 중앙 1.6 mm(최대 2.8), M 1.1 mm(최대 2.1)입니다.
  - D6 상승(판독)은 M 전방 25.6~35.2 bar, 후방 15.8~32.6 bar입니다.
- **Mslow c2 (2 mm만)**: 탐침 수축 89개 가운데 19개가 열리지 않았습니다.
  - 안 열린 쪽: FL 99.5~100.3 bar, RL 84.4~93.0 bar, FR 87.8 bar(비 0.99, 경계).
  - 열렸지만 E3 < 0.3 mm인 것이 16개 더 있습니다. 증인을 켜고 위치 목표만 끈 조합이 있었다면 판정 불가 라운드가 되었을 후보입니다.
  - 다른 플랜트의 c2는 91/91 모두 열렸습니다.
- **어긋남의 원인 후보** (확정이 아니라 후보입니다)
  - ① 하네스 need가 손계산보다 큽니다. Mslow 2.32~2.34 mm 대 2.125~2.285, M 1.51~1.53 대 1.40~1.49입니다.
    - 충전 중 헤드 판독이 99.4에서 105.5 bar로 오릅니다. b0 형식에서 헤드가 $A_{ann}\Delta p/A_h$를 따라가므로 need가 커집니다. 명세 3.3 (b)의 "need가 더 커서 보수적"과 같은 방향입니다.
  - ② 실효 충전이 명령보다 4.6 % 적습니다(x 2.001 / 2.098 mm). 첫 읽기 지연이나 배수가 후보입니다.
  - ③ ①·②로 충전이 적으면 갇힌 상승도 0.1~0.4 bar 낮아지는 방향이라 서로 맞습니다.
  - hydraulics 재확인이 필요한 수준인지는 판단을 넘깁니다.
- **검증 불가**: "WARN은 이 경우에 난다(H3 후보를 끄면)" 문장은 probe 팔 구성상 검증할 수 없습니다. c2는 증인과 위치 목표를 함께 끄고, a1~a6은 둘 다 켭니다.

### 2. P7-8 (D 12키 × {VBM, VBMslow} × a2 = 24줄)
- **J-P3a 조건 침범**: 0/360읽기(줄당 15읽기)입니다. 도구 `condition_ad7a716e.json`과 독립 계산(T4h `jp3_*`)이 일치했습니다.
  - 같은 24줄의 줄 전체 판정 집계(`extend_bound_check`의 jp3a·jp3b·jp3c)도 모두 0입니다.
  - 기록: 옛 필드 `breach_reads`(rev 5 전 ext_moving 규칙)는 Mslow `R12_bottom-RR-Fs0-o0.05-G4-level`에서 2입니다. 판정 필드가 아닙니다.
- **FAULT**: 0/24, final_phase READY 24/24입니다.
  - 경고는 `WARN_PROBE_STIFFNESS_OUT_OF_RANGE` 5줄과 `WARN_D1_IMU_GYRO_MISSING` 2줄입니다.
  - 일부 줄(VBM 6줄, VBMslow 6줄)의 `min_F_after_event_kN`이 −0.72~−1.05 kN입니다. 해당 줄의 `event_output.pass`는 True입니다. 사건 다리의 값으로 보이지만 확인하지 않았습니다.
- **봉인 전 관문**: 침범 0, FAULT 0이라 **통과**입니다.
- **"사용 상계 − 해제 직전 진값 ≥ +7.9 bar"**: 측정 정의에 따라 결과가 다릅니다.

| 측정 정의 | M 최소 | Mslow 최소 | 7.9 대비 |
|---|---|---|---|
| (a) 전환(locked_ext→moving_ext) 이음매의 carry 읽기 1~4번째: 사용 상계 − 해제 직전 잠김 진값 | 8.54 | 8.34 | 만족 |
| (b) 5번째 carry 읽기(다리가 움직인 뒤 사용 상계가 신장 상계로 내려감): 사용 상계 − 해제 직전 진값 | **2.90** | **2.90** | 미달(59/360읽기, 24줄 전부에 있음) |
| 같은 읽기의 사용 상계 − 그 읽기 진값 | 2.86 | 2.89 | 양수(침범 아님) |
| (c) 전환 전 잠긴 구간 전체에서 ④(pilot_model) − 진값 | **7.68** | **7.68** | 미달. `R12 top-RR-Fs0-o0.0-RE1bF` FR, t 41.0 s, 신장 뒤 다시 잠기는 첫 읽기(④ 바닥 13.0, 진값 5.32)이고 충전 갇힘이 없는 이음매. 중앙값 8.0 |

- 예측 근거(hydraulics 1.4)는 "갇힌 충전 압력 ≤ $p_{rod,open}$이고 $p^*_{ret}$와의 여유가 ≥ 7.9 bar"입니다. 이에 해당하는 양은 (a)이고 (a)는 만족합니다.
- (b)와 (c)의 최소는 예측이 다룬 기전과 다른 곳에서 나옵니다. (b)는 움직이는 신장 상계로의 전환, (c)는 다시 잠기는 이음매입니다.
- 7절 고정 값으로 어느 정의를 쓸지는 명세(hydraulics) 결정이 필요합니다. 문면 그대로("사용 상계 − 해제 직전 진값")를 모든 carry 읽기에 적용하면 미달입니다.
- **VBM 12줄의 V0 대비는 하지 않았습니다.** 이유는 두 가지입니다.
  - V0 줄이 허용된 검색 범위(`j9_runs\6bfb2560\`) 밖에 있습니다.
  - V0 대비 단위 판정은 Q7-C4 결정 뒤의 봉인 문면으로 계산하도록 되어 있습니다(6.1, P7-9).
  - 필요하면 판 6 V0 줄의 경로를 받아 따로 하겠습니다.

### 3. 기록 이상 (3.1·3.2 문안 대조)
- **D6 증인** (`probe_d6_record.rounds` 2336행)
  - 필드 `is_reversed`, `k1_mid_opened`, `retract_witness_m`, `is_opened`, `retract_target_reached`, `retract_extra_m`이 모든 행에 있습니다.
  - `is_opened`가 (witness ≥ 0.3 mm)와 모두 일치합니다.
  - `not_judgeable_rounds`가 안 열린 행 수와 같고, `INFO_D6` 사건 수가 그 합과 같습니다(모두 0).
  - `reversed_rounds.not_substituted`가 역순 행 수와 같습니다(모두 0). 비역순 행의 `k1_mid_opened`는 모두 null입니다.
  - T4h meta의 라운드 수가 줄의 라운드 수와 같습니다.
- **기록 블록 유무**
  - 증인 팔의 event 경로 줄은 348줄 가운데 346줄에 기록이 있습니다.
  - 빠진 2줄은 Mslow a1의 `R15_o0.0`과 `R15_o0.05`입니다.
    - `R15_o0.0`: PROBE 중 RR 수축이 85.2 s에 시작했고 실행이 86.7 s에 끝났습니다.
    - `R15_o0.05`: 21.6 s부터 끝까지 LEVEL에 머물렀습니다.
    - 둘 다 끝난 라운드가 없으므로 기록이 만들어지지 않는 코드 경로와 맞습니다(`two_pressure.py` 1825~1835, 1883~1884). 이상이 아닙니다.
  - c2는 증인을 끈 팔이라 기록이 없고, head-only 줄도 기록이 없습니다. 둘 다 설계대로입니다.
- **역순 탐침**: probe 전체에서 **0라운드**입니다(대체 0, 비대체 0). 역순 경로의 `k1_mid_opened`(bool)와 대체/비대체 집계는 실데이터로 검증되지 않았습니다. 단위 시험(`test_ed7_units.py` 332~)만 덮습니다.
- **A_ib (`lsb_record.blind`)**: 발사 334회입니다.
  - 다리별 `triggers`, `trigger_periods` 길이, shots 수가 모두 같습니다.
  - T4h `lsb_ib_on` 상승 에지 수도 triggers와 모든 줄에서 같습니다.
  - 끝 사유 수 + 끝나지 않은 shot 수가 triggers와 같습니다. 사유는 moved 221, sign 111, phase 2이고 zero·cap은 0입니다.
  - A_ib를 끈 a1 팔의 발사는 0입니다.
- **A_ib 경로 횟수**
  - `completion_known=False` 0/334(플래그 없는 주기의 발사 0)
  - 래치 0, $n_{rev}$ 0, 같은 다리 발사 부호 전환 0(줄·다리당 최대 2발)
  - 보호 막힘 0주기, `INFO_LSB_BLIND_LATCH`·`INFO_LSB_BLIND_PROTECT`·`INFO_LSB_CAP` 사건 0
  - 그래서 래치·$n_{rev}$·보호 기록 경로는 **probe에서 검증되지 않았습니다**. S4 e0.002는 래치·$n_{rev}$ 경로용으로 고른 키인데, 반대 부호 발사가 나오지 않았습니다.
- **3.1 기록 목록의 "LEVEL 완료 경로(엄격/relax)"**: jsonl 전체에 "relax" 문자열이 0건입니다. 이 기록은 줄에 없습니다. 기록 누락 후보이고, 구현 확인은 python-expert 몫입니다.

### 4. 7절 표 빈칸 제안 (채우지 않음)
제안 CSV는 모든 팔을 담았습니다. 봉인 구성 팔은 채택 도구가 정한 뒤 고르면 됩니다.

| 7절 열 | 이 probe로 채움 | 출처 |
|---|---|---|
| 키 × 플랜트 | 예 | `job`, `ed7_probe.plant/arm` |
| V0 대비 / 단위 판정·실패 항목 | **아니오** | V0 줄과 Q7-C4 뒤 봉인 문면이 필요 |
| 최소 힘 [kN] | 조건부 | `values.forces.after_liftoff.min_kN` 또는 `event_output.min_F_after_event_kN`. 일부 사건 줄은 음수(−0.72~−1.05)라 "사건 다리 제외" 같은 정의를 먼저 정해야 함 |
| 사건 뒤 LEVEL 길이 [s] | 예 | T4h `phase`=level이고 t ≥ `t_event_s`인 읽기 수 × 0.1 s. a2 D줄 11.6~14.4 s |
| DONE 경로(엄격/relax) | **아니오** | 기록 없음(3절) |
| 사각 트리거 수 | 예 | `blind.legs.*.triggers` 합. a2 본 행 0~3, D줄 모두 0 |
| ΔD 중앙/최대 [kN] | 예 | shots의 \|`delta_D_N`\|. a2 최대 7.56 |
| 비틀림 묶음 트리거 수 | 예 | `four_leg_twist_triggers`. 모두 0 |
| \|D\| > 15 진입 수 | **아니오** | D 추적값이 기록에 없음(shot 앞뒤 값만 있음) |
| $n_{rev}$·래치 | 예 | 모두 0 |
| D6 판정 불가 라운드 | 예 | 모두 0 |
| J-P3 | 예 | ③ rev 7 조건 읽기·침범(D 24줄 침범 0), 줄 전체 jp3a/b/c 0 |
| 비고 | 예 | FAULT 0. final_phase가 READY가 아닌 줄 17개(PROBE·LEVEL로 시간 종료)는 채택 도구 관점에서 볼 항목 |

### 수행한 작업
- 모든 실행은 `C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B <스크립트>`로 PowerShell에서 했습니다.
- 스크립트(근거로 남길 것): `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\0d95027e-6012-4053-b99a-1e505935768c\scratchpad\control-ed7probe\`
  - `s05_extract.py`: jsonl 스트리밍 + T4h 읽기, 독립 조건 읽기 계산, 기록 일치 점검
  - `s06_summary.py`, `s07_p77.py`, `s09_final.py`, `s11_dgap.py`, `s12_lockgap.py`, `s13_min_lock.py`, `s14_table7.py`, `s15_ebc.py`
  - `s08_seg_trace.py`, `s10_r15.py`: 개별 줄 추적
- 결과 폴더: 위 경로의 `out\`
  - `lines.csv`, `d6_rounds.csv`, `ib_shots.csv`, `d_condition_reads.csv`, `d_lock_gaps.csv`, `table7_proposal_all_arms.csv`, `anomalies.json`([]), `final.txt`
  - `summary.txt`와 `p77.txt`의 x/need·`p1_open_any` 열은 창 안에서 방향을 거르지 않은 중간값이라 쓰지 않습니다. 확정값은 `final.txt`와 `probe_retract_segments.csv`의 `p1_open_ret`·`p1_ret_*` 열입니다.
- 메인이 프로젝트 근거 폴더로 옮길 것: 위 스크립트와 `out\`

### 블라인드 경로 공개 (실제 행위)
- 지시를 받기 전에 worktree 루트(`...\.claude\worktrees\ed7-impl`)를 범위로 검색을 4번 했습니다.
  - Grep 2회: glob `*.py`, 패턴은 `probe_d6_record|d6_witness|...`와 `probe_consistency_check`
  - Glob 2회: `**/ed7_probe*.py`, `**/jp3_rev7_condition.py`
- 결과에는 03_src·04_scripts·05_tests의 .py 경로만 나왔고, 06_analysis 아래 경로(블라인드 사본 포함)는 이름·건수 모두 나오지 않았습니다. 다만 검색 범위가 그 폴더를 포함했던 것은 사실입니다.
- 지시 뒤에는 worktree 루트·06_analysis를 대상으로 검색하지 않았습니다.
- 메인 checkout에서 읽은 것은 `j9_runs\6bfb2560\` 아래와 명세·`ed7_design` 설계 문서(hydraulics h7 검토 등)뿐입니다. `606f8713\cdry_a1`은 열지 않았습니다.

### 가정
- "R12 FL 상태"는 R12 top-FR/RL-Fs0 키의 FL 첫 탐침 라운드(32.1 s)로 보았습니다. $p_h$와 s가 예측 상태와 같습니다.
- 7.9 bar 여유는 세 가지 정의로 나눠 냈습니다. 어느 정의가 명세 의도인지는 명세 작성 쪽이 정할 일입니다.

### 핸드오프·위임 필요
- **hydraulics-expert**
  - P7-7 수치 어긋남 검토: 하네스 need가 손계산보다 1.6~10 % 크고, 실효 충전이 명령보다 4.6 % 적습니다.
  - P7-8 "≥ 7.9 bar"의 측정 정의 확정: (a), (b), (c) 가운데 어느 것인지.
  - "WARN은 H3 후보를 끄면 난다"가 probe 팔 구성으로 검증 불가하다는 공개 여부.
- **python-expert**
  - 3.1 기록 "LEVEL 완료 경로(엄격/relax)"가 줄 기록에 없음.
  - 7절 표의 \|D\| > 15 진입 수에 필요한 D 추적 기록이 없음.
  - 기록 키 추가가 필요하면 명령은 바꾸지 않습니다.
- **메인**
  - VBM 12줄의 V0 대비가 필요하면 판 6 V0 줄 경로를 주시면 됩니다.
  - 역순 탐침·래치·$n_{rev}$·보호 경로는 probe에서 0회라 실데이터 근거가 없습니다. 봉인 공개 항목에 넣을지 정해야 합니다.

사용한 스킬: 없음
의존성 점검: 생략(읽기 전용 분석, dynamics-dev의 numpy·pandas만 사용)
메모리: `record-path-exercise-check.md`를 새로 썼습니다(기록 경로가 실제로 일어났는지 먼저 세라는 일반 교훈).
