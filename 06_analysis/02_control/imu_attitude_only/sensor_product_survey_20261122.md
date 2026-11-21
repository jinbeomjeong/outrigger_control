# 경사계·AHRS 제품 사양 조사 (web-research-expert, 정밀, 2026-11-22) — hand-back 원문 요지

## 조사 요약
- **정적 경사계 필터 가정(2단 저역 1 Hz)은 제조사 설정 범위 안이다.**
  - Level Developments SOLAR-2가 가장 가깝다: 2차 Bessel IIR, 기본 1 Hz [3].
  - ifm JN2101: FIR, 기본 5 Hz, 1 Hz도 선택 가능 [1].
  - POSITAL ACS: 기본 200 ms 이동평균 [4].
  - 1 Hz 2차 필터는 그 자체로 군지연이 약 0.2 s다(계산). 가정 지연 20 ms는 이와 별도의 전송 지연으로 보아야 한다.
  - 경사계 지연(latency) 수치를 공개한 제조사는 없다.
- **AHRS 지연 가정(10 ms)은 보수적이다.** SBG는 처리 지연이 "대개 1 ms 미만"이라고 밝힌다 [14]. 나머지 제조사는 지연 값을 내지 않는다.
- **AHRS 분해능 가정(0.001°)은 CAN 출력 기준으로 낙관적이다.** CAN 각도 양자화는 다음과 같다.
  - SBG: 1e-4 rad = 0.0057° [15]
  - Xsens: 2^-7° = 0.0078° [20]
  - SICK: 기본 PGN 0.01°, 확장 PGN 1/32768° [11]
  - POSITAL: 0.01° [6]
- **가속도 보정 교차 주파수를 공개한 AHRS 제조사는 없다.** 대부분 프로파일만 고를 수 있다(Xsens Responsive/Robust/General, SBG Heavy Machinery, Motus 차량 프로파일). 시간 상수를 직접 설정할 수 있는 제품은 SICK TMM88D 하나다("Interference suppression time" 100~10,000 ms, 기본 5,000 ms [11]).
- **동적 정확도 사양은 ±0.25~0.5°다.** 프로젝트의 정상상태 허용치 ±0.2°보다 크다. 정적 정확도는 0.05~0.3°다.

## 표 1. 정적 경사계
| 항목 | ifm JN2101 (CANopen) | Level Developments SOLAR-2 | POSITAL TILTIX ACS |
|---|---|---|---|
| 정적 정확도 | 출처마다 다름: 제품 페이지 ≤±0.01°, TC ≤±0.0008°/K [2] / 기기 매뉴얼 ≤±0.5°, 반복성 ≤±0.1° [1] | ±0.010~0.040°@20°C, 보상형 ±0.025~0.065° [3] | ±0.10°(INL), TC 0.004°/K [5] |
| 내부 필터 | FIR. 끔/10/5/1/0.5 Hz, **기본 5 Hz** [1] | **2차 Bessel IIR**. 0.125~16 Hz, **기본 1 Hz** [3] | 모드 0~6(이동평균·Butterworth 1~10차·임계감쇠·Kalman). **기본 200 ms 이동평균** [4] |
| 출력 주기 | TPDO 기본 10 ms [1] | 없음 [3] | 센서 500 µs, Cyclic 기본 꺼짐 [4][5] |
| 지연 | 없음 | 없음 | 없음(정착 시간 30~200 ms) |
| 분해능 | 0.001° 선택 가능, **기본 0.01°** [1] | 0.001° @1 Hz [3] | 0.01° [4][5] |
| 출력 항목 | 경사 X/Y, 온도 | 경사각만 | 경사 + 가속도 X/Y/Z |
| 인터페이스 | CANopen(J1939판 JN2301) | RS232/RS485만(CAN 없음) | CANopen |
| 가정 대비 | 1 Hz 선택 가능. FIR이라 위상 특성이 다르고, 기본값은 더 빠르다 | 가장 가깝다. 분해능은 가정보다 10배 곱다. CAN이 없다 | 기본(군지연 ≈100 ms, 계산)은 가정보다 빠르다. Butterworth 1 Hz 2차로 설정하면 가정과 같다 |

## 표 2. 동적 경사계·AHRS
| 항목 | SICK TMM88D-MJI090A (J1939) | POSITAL TILTIX AKS | SBG Ellipse-A | Xsens MTi-630/680G | Advanced Navigation Motus |
|---|---|---|---|---|---|
| 정적 / 동적 정확도 | ±0.1° / ±0.25°(2024) [10]. 2019 매뉴얼: ±0.3~0.5° / ±0.5° [11] | ±0.30° / **±0.50°** [7] | 0.1° / 0.4° (1σ) [12][13] | 0.2° / 0.5° RMS [18] | 0.05° [22][23] |
| 융합·필터 설정 | Interference suppression time 100~10,000 ms(기본 5,000), 디지털 LP 8차 0.1~25 Hz(기본 5 Hz) [11] | 각도 필터 설정 없음 [8] | Motion profile(Heavy Machinery 등) [16] | 필터 프로파일 [18] | 차량 프로파일 [24] |
| 출력 주기 | 200 Hz 샘플, PGN 기본 10 ms | 1 ms | ≤1 kHz | 자세 ≤400 Hz | ≤1000 Hz |
| 지연 | 수치 없음(PGN latency 필드만 있음) | 없음 | **처리 <1 ms**(전송은 별도) [14] | 600 계열 수치 없음 | 없음 |
| 분해능 | 0.01°(확장 PGN 1/32768°) | 0.01° | CAN 0.0057° | CAN 0.0078° | 미확인 |
| 출력 항목 | 각도·각속도·가속도 PGN | 각도·가속도·각속도 | 자세·IMU 가속도·각속도 | 자세·가속도·각속도 | 센서값·자세 |
| 인터페이스 | J1939 | CANopen(J1939판 있음) | CAN 2.0 | CAN | RS232/422(CAN 없음) |
| 가정 대비 | 교차 0.05 Hz(τ ≈ 3.2 s)는 설정 범위 안이다. 기본 5 s는 ≈0.032 Hz에 해당한다(추정) | 교차 주파수를 설정할 수 없다. 분해능이 거칠다 | 지연은 보수적이다. 분해능은 낙관적이다 | 분해능이 낙관적이다 | CAN 없음 |

## 필터 지연 계산(조사자 계산)
- 1 Hz 2차 Bessel의 저주파 군지연은 약 0.217 s, 2차 Butterworth는 약 0.225 s다.
- **1차 필터 둘(각 1 Hz)을 이은 경우**는 약 0.318 s이고, 전체 −3 dB 점이 약 0.64 Hz로 내려간다.
- 설계서 2.1절 A 식은 1차 필터 두 단을 이은 꼴이다(메인 확인). 따라서 가정 경사계는 SOLAR-2(2차 Bessel 1 Hz)보다 위상 손실이 크다. 보수 쪽이다.

## 불일치·불확실한 점
- ifm JN2101 정확도: 제품 페이지와 매뉴얼 값이 50배 다르다.
- SICK: 2024 A세대 데이터시트와 2019 매뉴얼 값이 다르다. 기본값은 2019 매뉴얼 기준이다.
- 동적 정확도 정의가 제조사마다 달라서 직접 비교할 수 없다.

## Sources
[1] ifm Device manual JN2101 11609306/00 (04/2024) https://media.ifm.com/dam/01a0a4a9-938f-78aa-b6da-e48ffb8ad5a4/Original/JN2101_11609306_GB.pdf
[2] ifm JN2101 제품 페이지 (2025-02-05) https://www.ifm.com/us/en/product/JN2101
[3] SOLAR-2 datasheet Rev 10 https://www.leveldevelopments.com/wp/wp-content/uploads/documents/SOLAR-2_Dual_Axis_Inclinometer.pdf
[4] POSITAL TILTIX ACS CANopen manual 20240517 https://dms.posital.com/pdf/manual-tiltix-acs3-ca.pdf
[5] POSITAL ACS-090-2-CA01-HW3-PL https://www.posital.com/en/products/inclinometers/ACS-090-2-CA01-HW3-PL/3491229
[6] POSITAL AKS-3 CANopen manual 20240924 https://dms.posital.com/pdf/manual-tiltix-aks3-ca03.pdf
[7] POSITAL AKS-090-2-CA03-HK3-PW https://www.posital.com/en/products/inclinometers/AKS-090-2-CA03-HK3-PW/3353311
[8] POSITAL Inclinometer Specifications https://www.posital.com/en/inclinometer-specifications
[9] POSITAL Dynamic TILTIX news (2024-10-31) https://www.posital.com/en/news-events/dynamic-inclinometer-nextgen
[10] SICK TMM88D-MJI090A datasheet (2024-11-16, 미러) https://www.motionworld.com/assets/SICK-TMM88D_MJI090A-Datasheet.pdf
[11] SICK TMS/TMM88 Dynamic J1939 Operating Instructions (2019-06-27, 미러) https://anv-tech.ru/assets/docs/67uow9k3exnfvisg-i8.pdf
[12] SBG Ellipse-A leaflet https://www.sbg-systems.com/wp-content/uploads/SBG-Ellipse-A-MK067EN.pdf
[13] SBG Ellipse performance specs https://support.sbg-systems.com/sc/el/latest/ellipse-documentation/performance-specifications
[14] SBG KB time/sync https://support.sbg-systems.com/sc/kb/latest/inertial-sensors-operation/time-synchronization-and-event-management
[15] sbgECom 5.1 CAN protocol https://developer.sbg-systems.com/sbgECom/5.1/md_doc_can_protocol.html
[16] SBG Ellipse configuration https://support.sbg-systems.com/sc/el/latest/getting-started/sbgcenter-manual/ellipse-configuration
[17] SBG New Ellipse test report https://www.sbg-systems.com/wp-content/uploads/SBG-New-ellipse-test-report.pdf
[18] Xsens MTi 600-series datasheet (2020.B) https://www.xsens.com/hubfs/Downloads/Leaflets/MTi%20600-series%20Datasheet.pdf
[19] MTi-630 leaflet (2025-02) https://www.xsens.com/hubfs/MTi%20product%20leaflet_07022025_MTi-630.pdf
[20] Xsens MT CAN Protocol MT1604P (2020.A) https://www.xsens.com/hubfs/Downloads/Manuals/MT%20CAN%20Protocol%20Documentation.pdf
[21] Xsens MTi-7 news https://www.xsens.com/resources/news/new-xsens-mti-7-module-with-external-gnss-receiver-input
[22] Motus Datasheet v2.4 (미러) https://cdn.geo-matching.com/1pAV04do.pdf
[23] Motus Navigation Specifications https://docs.advancednavigation.com/motus/NavigationSpecifications.htm
[24] Motus Vehicle Profiles https://docs.advancednavigation.com/motus/Operation/VehicleProfiles.htm
[25] ifm JN2301 datasheet https://media.ifm.com/dam/052f5272-2e19-4db6-aec4-95eb89df386f/Original/JN2301-02_EN-GB.pdf
