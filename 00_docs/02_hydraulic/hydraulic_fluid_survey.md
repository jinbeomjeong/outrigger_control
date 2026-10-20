# 유압유·유압 회로 특성 조사 (2026-10-19)

web-research-expert(정밀 모드) 조사 요약. 다리 축방향 강성 k = β_eff·A/L의 가정치 근거로 쓴다. 실기 유압 사양은 아직 없다.

## 결정

- **β_eff = 1.0 GPa 유지** (사용자 결정, 2026-10-19). 조사 권장 중앙값 1.3 GPa(범위 0.9~1.6)보다 낮아 다리를 조금 유연하게 보는 쪽이다. 감도 해석은 0.69(Merritt 보수 하한) ~ 1.6 GPa 범위로 한다.
- 강성을 크게 바꾸는 변수는 β보다 **기름 기둥 길이 L**(실제 신장량 + 사체적)이다. β 1.3 GPa에서 L = 0.68 m이면 k ≈ 2.0×10⁷ N/m, L = 0.3 m이면 k ≈ 4.5×10⁷ N/m.

## 핵심 수치

| 항목 | 값 | 출처 |
|---|---|---|
| 순수 광유(HM46) 등온 K_T, 101 bar | 20 °C 1.75 / 40 °C 1.58 / 60 °C 1.45 / 80 °C 1.33 GPa | Knežević 2016 (원자료 Mobil 1979) |
| 순수 광유(HM46) 단열 K_S, 101 bar | 20 °C 2.02 / 40 °C 1.83 / 60 °C 1.66 GPa | 같음 |
| 온도 영향 | 20 → 80 °C에서 약 −25 % | 같음 |
| 단열/등온 비 | 약 1.14~1.16 (진동 해석은 단열에 가까움) | Gholizadeh 2011, Knežević 2016 |
| 공기 영향 | 6~8.5 MPa 이상에서 작음. 다리 압력 7~12 MPa(정하중 70~120 kN ÷ 보어 면적) | Yang 2011, Feng 2017 |
| 실린더 강성 구성비(Ø160) | 유압유 약 80 %, 관 팽창 약 10 %, 로드 6 %, 호스 3 % | Feng 2017 |
| 실측 역산 β (Ø160, 16 MPa) | 약 1.37 GPa(호스 없음), 1.24 GPa(호스 포함) | Feng 2017 실측값에서 역산 |
| Merritt 설계값 | 100,000 psi = 0.69 GPa (보수적, 서보 시스템 전체) | US4337611A 인용 |
| Rexroth 공식집 | 1.4 GPa | Rexroth 2002 |
| 유사 장비 시뮬레이션 채택값 | 크레인·굴착기 1.5 GPa, 고소작업대 1.7 GPa | Cibicik 2019, Shetty 2025 등 |

- 이 실린더(Ø115 보어, Ø110 로드)는 로드가 굵어 로드 축강성이 기름 기둥 대비 1 % 안팎으로 무시할 수 있다. 조사 보고는 로드 길이 약 0.69 m로 2.9×10⁹ N/m(0.7 %)를 냈고, 동역학 모델(`dyn_model.k_rod`, L = 1.05 m)은 1.9×10⁹ N/m(1.2 %)를 쓴다. 결론은 같다.
- 파일럿 체크 밸브를 실린더에 직결하면 호스가 잠긴 체적에서 빠져 다리 강성과 무관해진다(권장 관행).

## 아우트리거 회로 일반 사양

- 수직 잭은 복동 실린더 + 파일럿 체크(로크) 밸브가 표준. 정격압 예 20.6 MPa(UNIC 트럭크레인).
- 파일럿 체크 밸브 누설 약 0~5 방울/min. 실린더 내부 누설 시험 기준 예: 1.5배 압력에서 0.5 mL/min 미만.
- 응답 시정수, 잠긴 잭의 감쇠비 실측값은 공개 자료에서 찾지 못했다.

## 감쇠·마찰

- 실 마찰: 정격 하중의 약 10 %로 가정하는 실무 관행, 압력에 따라 증가(K_p ≈ 0.004 1/bar). Kühnlein 2012.
- Merritt의 유압 감쇠비 0.1~0.2는 밸브 제어 상태 값이라 잠긴 상태에는 맞지 않는다.

## 남은 공백 (실기 사양으로 메울 것)

파일럿 체크 밸브 위치, 호스 길이·규격, 실린더 관 두께, 실제 레벨링 신장량, 오일 종류·운전 온도.

## 주요 출처

- Gholizadeh, Burton, Schoenau, "Fluid Bulk Modulus: A Literature Survey", IJFP, 2011
- Knežević et al., "Effect of bulk modulus of fluid on the dynamic behavior of the hydraulic system", Annals FIH Hunedoara, 2016
- Feng et al., "Modelling Study on Stiffness Characteristics of Hydraulic Cylinder under Multi-Factors", SV-JME 63(7-8), 2017
- Yang, Feng, Gong, "Measurement of Effective Fluid Bulk Modulus in Hydraulic System", ASME JDSMC, 2011
- US4337611A (Merritt 100,000 psi 인용), 1982
- Kühnlein et al., "Rapid Parameterisation of a Sealing Friction Model for Hydraulic Cylinders", IFK, 2012
- Cibicik, Pedersen, Egeland, "Dynamics of luffing motion of a flexible knuckle boom crane", Mech. Mach. Theory, 2019
- 제조사 TDS: Shell Tellus S2 MX, Mobil DTE 10 Excel, GS Kixx RD HD, SK ZIC SUPERVIS
