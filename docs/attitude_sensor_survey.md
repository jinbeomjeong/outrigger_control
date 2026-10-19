# 자세 센서(경사계·산업용 IMU) 사양 조사 (2026-10-20)

> **2026-10-20 갱신**: 목표가 ±0.2°로 완화되고 IMU는 캐빈 바닥 아래 상부 프레임에 달기로 했다. 새 요구는 센서 정지 영점 오차 ≤ **0.13°(2.27 mg)**이며, 이 기준으로는 출하 상태 JN2101·SOLAR-2·Motus, 현장 영점 후 TE DPG·SICK TMM88D-MJI090A·M-A370이 통과한다. 아래 로킹 식 θ(1 − rω²/g)는 무게중심 회전 가정이라 틀리다(실제 회전 중심은 지면 아래) — 모드 형상 기반 결과는 [imu_cabin_and_accuracy_review.md](imu_cabin_and_accuracy_review.md). 이 문서의 나머지는 ±0.1° 당시 조사 기록이다.

web-research-expert(정밀 모드) 조사 요약. 요구(당시): 레벨링 ±0.1°를 위해 센서의 **정지 기울기 영점 오차 총합 ≤ 약 0.06°**(가속도계 바이어스 약 1.0 mg 이하, −20~+60 °C, 근거 [control_candidates_comparison.md](control_candidates_comparison.md)).

## 환산 방법

- 가속도계 바이어스 b → 기울기 오차 θ = asin(b/1 g). 1 mg ≈ 0.0573°, 0.06° ≈ 1.05 mg.
- A(출하 상태) = |초기 오차·정확도| + 온도계수 × 45 K(25 °C 기준 −20 °C 쪽) + 반복성/장기
- B(설치 후 현장 영점) = 온도계수 × 45 K + 반복성/장기 (영점 잡은 온도가 극단이면 ΔT 최대 80 K)
- 온도계수의 선형 확장은 근사다(ADI: "do not apply linear assumptions … over entire temperature range").
- 잡음은 0.06 Hz 대역에서 무시 가능(60 µg/√Hz → 약 0.001°). In-run bias stability(Allan)는 영점 예산과 거의 무관.

## 결론

| 분류 | 후보 | 비고 |
|---|---|---|
| **출하 상태로 만족** | ifm JN2101(CANopen, ±45°, A 0.056°) | 경계값. 2014 브로셔 기준이면 TC 2.5배로 불가(약 0.15°) — 최신 데이터시트 확인 필요 |
| | Level Developments SOLAR-2 온도보상형(±15°, −10~60 °C ±0.030°) | RS485만, −20 °C는 주문 교정 |
| | Advanced Navigation Motus(roll/pitch 0.05°) | 측정 조건·CAN 미확인 |
| **현장 영점 + 온도보정이면 가능** | Epson M-A370(수정 가속도계, B 0.035°) | 보드급, 하우징·CAN 변환 필요 |
| | ADI ADIS16575(온도분 1σ 0.017°) | 켤 때 반복성 1.4 mg 1σ 중 남는 몫 불명 |
| | TE DPG ±10°(영점 후 0.05°) | RS232·아날로그 |
| | Murata SCH16T(typ만) | 3σ로는 불가 |
| 경계(불가 쪽) | SICK TMM88D-MJI090A(동적, J1939, 영점 후 0.072°) | 크레인 레벨링 실적 계열 |
| **불가** | 동적 경사계 대부분(ifm JD2310, Baumer GIM700DR, POSITAL AKS, P+F IMUF99, Balluff), POSITAL ACS, Kübler IS40/IS60, Turck, Murata SCL3300/SCA3300 원시, ADIS16505/16470, Xsens MTi-630, SBG Ellipse-A(0.1°), VN-100 | 정적 정확도 0.1~0.4° 또는 온도계수가 큼 |

- **동적 경사계(자이로 융합)의 "dynamic accuracy"는 과도 상태 지표라 정상상태 영점 예산에 도움이 안 된다.**
- 출하 상태로 0.06°를 맞추는 CAN 출력 산업용 경사계는 사실상 JN2101 하나이고, 그것도 경계값이다. 실용적으로는 **현장 영점 교정 + 온도 보정**이 전제가 된다.

## 주요 제품 수치 (원문 값)

| 제품 | 종류 | 원문 정확도·영점·온도계수·반복성 | A 출하 | B 영점 후 | IF | IP | 가격 |
|---|---|---|---|---|---|---|---|
| ifm JN2101 | 정적 | Accuracy ≤±0.01°, Repeatability ≤±0.01°, TC ≤±0.0008 1/K | 0.056° | 0.046° | CANopen | IP65~69K | $594.80 |
| Level Dev. SOLAR-15 | 정적 | Acc@20 °C ±0.020°, −10~60 °C ±0.030°(보상), drift ±0.0003°/°C(보상) | 0.037°(보상) | 0.020° | RS232/485 | IP67 | — |
| SICK TMM88D-MJI090A | 동적 | Static ±0.1°, TC typ ±0.0016°/K | 0.17° | 0.072° | J1939 | IP6K7/6K9K | — |
| TE DPG ±10° | 정적 | Abs 0.15°(−40~85), offset drift 0.05°(−25~75) | 0.15° | 약 0.05° | RS232 | IP67 | — |
| Epson M-A370 | 수정 가속도계 | Bias temp error ±0.5 mG(−30~85 °C), rep ±0.1 mG(1년) | — | 0.035° | SPI/UART | — | — |
| ADI ADIS16575 | IMU | Repeatability 1.4 mg 1σ, error over temp ±0.3 mg 1σ | 0.097°(1σ) | 0.017°(1σ, 반복성 제외) | SPI | — | $1,067.70 |
| AdvNav Motus | AHRS | Roll & Pitch 0.05°, initial bias < 0.45 mg | 0.05°(조건 미상) | — | (CAN 미확인) | IP67 | — |
| Murata SCL3300 | 경사계 IC | Offset error ±10 mg(−40~125 °C) | 약 1.0° | 자체 교정 없이는 불가 | SPI | — | $38.38 |

## 로킹 가속도

- 센서가 로킹 축에서 높이 r에 있으면 가속도계의 겉보기 기울기 ≈ θ·(1 − rω²/g). r = 2 m에서 1.8 Hz면 약 26배, 3.9 Hz면 약 122배(실제 0.05° → 겉보기 1.3~6°).
- 영평균 진동이라 0.06 Hz 루프와 저역통과로 대부분 걸러지지만, 1차 LPF 0.5 Hz는 1.8 Hz에서 1/3.7뿐이라 부족하다 → **다단 LPF, 센서를 로킹 축 가까이 배치, 또는 자이로 융합**. 진동 정류(비선형)는 영점을 한쪽으로 밀 수 있다.

## 설치 후 영점 교정 기능

확인됨: SICK Zeroset, ifm "Set zero point"(SDO 2046h), Kübler IS40 teach, SOLAR-2 `setzcur`. POSITAL·Baumer·P+F는 미확인.

## 레벨링 적용 사례 (제품명 명시)

POSITAL TILTIX ACS(Bronto Skylift X/Y 레벨링), SICK TMM61(모바일 크레인 자동 레벨링), ifm JN2101("levelling of mobile machinery"), TE DOG2(아우트리거 안정성·크레인 자동 레벨링, 25 °C 0.15°), Rion ACA2200T(가위형 고소작업대, 제조사 마케팅 수치).

## 시뮬레이션 IMU 오차 모델 대표값 (3단계)

| 항목 | 우수 (JN2101 / M-A370 / ADIS16575 영점 후) | 보통 (TMM88D-MJI / ACS-080 / SCH16T) | 저가 (SCL3300 원시 / ADIS16470 / IS40) |
|---|---|---|---|
| 초기 영점(출하) | 0.01° (≈0.17 mg) | 0.1° (≈1.75 mg) | 0.3~0.57° (5~10 mg) |
| 켤 때마다 반복성 | 0.01° / 1.4 mg 1σ(ADI) | 0.05° | 0.1° |
| 온도 드리프트 | 0.0008°/K (≈0.014 mg/K) | 0.0016~0.004°/K | 0.008~0.015°/K |
| 장기 | 0.007° | 2 mg | 4~8 mg |
| 잡음 밀도 | 15 µg/√Hz | 60~82 µg/√Hz | 100 µg/√Hz |
| 대역·지연 | LPF 0.5~1 Hz(1차 1 Hz 군지연 약 0.16 s) | LPF 0.1~25 Hz | 10~70 Hz |

모델 형태 권장: b(T) = b0 + k_T·(T − 25) + b_rep(전원 투입마다 무작위) + 2차 비선형 항.

## 불확실

- ifm JN2101 온도계수: 데이터시트 JN2101-03(0.0008°/K) vs 2014 브로셔(0.002°/K) — 만족/불가가 갈린다. 제조사 확인 필요. J1939판 JN2301은 단종 가능성(대체 JN2300).
- Motus 0.05°의 측정 조건, Epson·SOLAR-2 −20 °C 수치는 제조사 문의로 확인하는 편이 빠르다.
- Exa agent_run에만 있고 원문을 대조하지 않은 제품(VN-100, Bewis, Rion ACA826T, Siko, MEMSIC, HG4930 등)은 표에서 뺐다.

## 주요 출처

ifm JN2101 데이터시트 JN2101-03 및 2014 제품 소식; Level Developments SOLAR-2; SICK TMM88D-MJI090A(2024-11-16), TMM88D-PCI090(2026-07-28); TE DPG-Series; Epson 가속도계 라인업(M-A370/A352/A552); ADI ADIS16575/16505/16470 데이터시트, ADI "Attitude Sensing in Highly Dynamic Inertial Conditions"; Murata SCL3300/SCA3300/SCH16T; Advanced Navigation Motus 사양; Xsens MTi-630(2025-02-07); SBG Ellipse-A; Baumer GIM700DR(2025-04-25); POSITAL ACS-080·AKS-180; P+F IMUF99; Kübler IS40·IS60; Balluff BSI; Turck B2N85H; Jewell DXI; POSITAL·SICK·TE·Rion 적용 사례 자료; DigiKey·ifm·Movella 가격 페이지(2026-10 조회).
