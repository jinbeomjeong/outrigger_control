# SCM 토양 파라미터 문헌 조사 (2026-10-25, web-research-expert 정밀 모드)

S9(SCM 연약 지면)에 넣을 토양 파라미터를 문헌에서 조사한 원 기록이다. 판정용·감도용 토양 세트와 Chrono 입력표는 이 기록을 바탕으로 dynamics-expert가 `dynamics_model.md`에 정리한다. 이 문서의 계산값(침하, q_ult, Lysmer K·R, 단위 환산)은 조사 에이전트의 계산이며 검증이 필요하다.

## 요약

- Wong 표(통칭 "표 2.3") 원문 대조: 지금 쓰는 SI 값은 맞다. 저소성 점토 22 %·32 %, 중점토 40 %, 사질 양토 행을 Bekker(1969) 영미단위 원표 재수록 [3], NASA TM 2025 [1], 태국 교재(Wong 1978 인용) [2]로 대조했다. 2차 출처 오탈자 3곳을 찾았다(아래 표).
- 0.7~1.2 MPa 소형 패드용으로 측정된 Bekker 값은 문헌에 없다. Bekker 판은 9.5~76 mm이고 [3], bevameter 시험은 차량 접지압 약 100 kPa를 중심으로 설계한다 [10].
- 지지력 표 기준으로 0.7~1.2 MPa를 맨땅이 받는 경우는 조밀 자갈(허용 > 600 kPa), 매우 굳은 점토(300~600 kPa), 암반 정도다 [11][12][13]. 판정용("패드 압력 ≤ q_ult/2")으로 쓸 수 있는 Wong 표 행은 중점토 25 %뿐이고, 저소성 점토 22 %는 경계다.
- Chrono의 elastic_K·R에는 측정 근거가 없다(데모값 K 2e8 또는 4e7 Pa/m, R 3e4 Pa·s/m [6][7][8]). Lysmer 상사·K30 환산으로는 K 1e8~7e8 Pa/m, R 3e5~6e5 Pa·s/m(데모 R의 약 10배).
- SCM은 Bekker 식과 소성 침하만 계산하고 지지력 파괴는 모델에 없다. "p ≤ q_ult/2" 판정은 SCM 밖에서 따로 한다.

## 1. Wong 표 원문 대조

SI 단위: kc kN/m^(n+1), kφ kN/m^(n+2). Chrono 입력은 ×1000(N/m^(n+1), N/m^(n+2)) [9]. 환산식 SI = 영미값 × 4.448e-3 / 0.0254^(n+1)(kc; kφ는 n+2).

| 행 | 영미 원값 [3] n / kc / kφ / c[psi] / φ | SI [1] n / kc / kφ / c[kPa] / φ | 판정 |
|---|---|---|---|
| 저소성 점토 22 % (WES) | 0.20 / 45 / 120 / 10 / 20° | 0.2 / 16.43 / 1724.69 / 68.95 / 20 | 일치 [1][3][4] |
| 저소성 점토 32 % (WES) | 0.15 / 5 / 10 / 2 / 11° | 0.15 / 1.52 / 119.61 / 13.79 / 11 | 일치 |
| 중점토 40 % (WES) | 0.11 / 7 / 10 / 3 / 6° | 0.11 / 1.84 / 103.27 / 20.69 / 6 | 일치 |
| 중점토 25 % (WES) | 0.13 / 45 / 140 / 10 / 34° | 0.13 / 12.70 / 1555.95 / **68.95** / 34 | NASA TM의 c 69.95는 오탈자 |
| 사질 양토 LLL 15 % | (원값 미확인) | 0.7 / 5.27 / 1515.04 / 1.72 / 29 | [1][2] 일치 |
| 사질 양토 LLL 22 % | 0.20 / 7 / 3 / 0.2 / 38° | 0.2 / 2.56 / 43.12 / 1.38 / 38 | 일치 |
| 사질 양토 Michigan 11 % | 0.9 / 11 / 6 / 0.7 / 20° | 0.9 / 52.53 / **1127.97** / 4.83 / 20 | NASA TM의 kφ 11127.97은 오탈자 |
| 사질 양토 Michigan 23 % | — | 0.4 / 11.42 / 808.96 / 9.65 / 35 | [1][2] 일치 |
| 사질 양토 Hanamoto 26 % / 32 % | 0.3 / 5.3 / 6.8 / 2 / 22° ; 0.5 / 0.7 / 1.2 / 0.75 / 11° | 0.3 / 2.79 / 141.11 / 13.79 / 22 ; 0.5 / 0.77 / 51.91 / 5.17 / 11 | 일치 |
| 건조 모래 LLL | 1.1 / 0.1 / 3.9 / 0.15 / 28° | 1.1 / **0.99** / 1528.43 / 1.04 / 28 | 태국 교재 0.95는 오탈자 |

"사질 양토"는 LLL·Michigan·Hanamoto 6행이 같은 이름이다. 프로젝트가 어느 행을 쓰는지 명시해야 한다.

그 밖의 행(NASA TM [1], 원 출처 Wong):

| 토양 | n | kc | kφ | c [kPa] | φ |
|---|---|---|---|---|---|
| LETE sand | 0.79 | 102 | 5301 | 1.3 | 31.1° |
| Upland sandy loam 51 % | 1.10 | 74.6 | 2080 | 3.3 | 33.7° |
| Rubicon sandy loam 43 % | 0.66 | 6.9 | 752 | 3.7 | 29.8° |
| North Gower clayey loam 46 % | 0.73 | 41.6 | 2471 | 6.1 | 26.6° |
| Grenville loam 24 % | 1.01 | 0.06 | 5880 | 3.1 | 29.8° |
| Clayey soil (Thailand) 38 % | 0.5 | 13.19 | 692.15 | 4.14 | 13° |
| Clayey soil (Thailand) 55 % | 0.7 | 16.03 | 1262.53 | 2.07 | 10° |

c·φ는 bevameter 전단 링 표면값이며 지반공학 cu·φ'와 같지 않다 [3][10].

## 2. 범주별 후보

- 다짐 토사·자갈(작업장, 임시 도로): 측정된 Bekker 값 없음. 대체 근거
  - Bowles 지반반력계수 [14]: 조밀 모래 64,000~128,000 kN/m³, 중간 조밀 모래 9,600~80,000, 점토 섞인 중간 조밀 모래 32,000~80,000.
  - 국내 K30(30 cm 판, KS F 2310) [16](시험업체 2차 출처): 노체 ≥ 98.1 MN/m³(콘크리트 포장, 1.25 mm), 노상 ≥ 147.1(콘크리트, 1.25 mm) / ≥ 196.1(아스팔트, 2.5 mm), 보조기층 ≥ 294(아스팔트, 2.5 mm).
  - SCM 대응(조사자 추론): n = 1, kc = 0, kφ ≈ K30 → 1e8~3e8 N/m³. K30은 작은 침하 할선값이라 1 MPa 비선형은 모름.
  - 단단한 점토 측정 사례: WES 1964 저소성 점토 CI 207 psi, n 0.365, kc 75, kφ 133(영미) [3] → SI 약 kc 50 kN/m^1.365, kφ 3.50e3 kN/m^2.365(조사자 환산; Mason 투고본 값).
- 점토·실트: 건조·굳음 = 중점토 25 %, 저소성 점토 22 %; 습윤 = 저소성 점토 32 %, 중점토 40 %. WES 점토 n 0.11~0.20 [3].
- 모래: 건조 모래 LLL, LETE, Upland·Rubicon 사질 양토.
- 연약(참고): Chrono 데모 soft(Kφ 2e6, n 1.1, φ 30°), 점토 32 %·40 %.

## 3. 패드 1 MPa 적용 계산 (조사자 계산, 검증 필요)

정팔각형 0.1071 m², b = 2A/둘레 ≈ 0.18 m(Chrono 방식 [5][9]; 정사각 패드는 2A/L = 변/2로 Bekker "짧은 변"과 2배 다름).

| 토양 | 1 MPa 침하 | Terzaghi q_ult(정사각, γ 18 kN/m³, B 0.3 m) | 0.7~1.2 MPa 판정 |
|---|---|---|---|
| 중점토 25 % | ≈ 0.024 m | ≈ 4.8 MPa | 판정용 가능 |
| 저소성 점토 22 % | ≈ 0.05 m | ≈ 1.6 MPa | 경계 |
| WES 저소성 점토 CI 207 | ≈ 0.026 m | — | — |
| Chrono hard (Kφ 2e7) | ≈ 0.066 m | — | — |
| LETE sand | ≈ 0.11 m | ≈ 0.12 MPa | 불가 |
| Grenville loam | ≈ 0.17 m | ≈ 0.19 MPa | 불가 |
| 사질 양토 LLL 15 % | ≈ 0.54 m | ≈ 0.11 MPa | 불가 |
| Chrono soft (2e6) | ≈ 0.53 m | — | — |
| 건조 모래 | ≈ 0.68 m | ≈ 0.07 MPa | 불가 |
| 저소성 점토 32 %, 중점토 40 % | 10³ m 이상 | 0.19 / 0.21 MPa | 불가 |
| North Gower | — | ≈ 0.25 MPa | 불가 |
| K30 147 MN/m³(선형) | ≈ 7 mm | — | — |

표면 전단 c·φ라 모래 q_ult는 과소평가일 수 있다(조밀 모래 φ' 35~40°, 일반 지식).

## 4. Bekker 고압·소형 판 적용 한계

- Bekker 판 9.5~76 mm. 모래는 작은 판이 침하 과대평가(보수), 점토는 크기 영향 작다고 봄 [3].
- 가정: 준정적, 균일 압력, 판 크기·형상 무시. 하중 속도가 다르면 차이 [17].
- 작은 판 5개로 큰 판 예측 시 침하 과소예측(RMSE 0.039 m, MRPD 71.9 %) [19].
- bevameter 설계는 100 kPa 중심, 정적 침하의 6~8배 깊이까지 측정 권고 [10].
- 상한 압력을 명시한 문헌은 찾지 못함. 대안: Reece 무차원 식 p = (c·k'c + γ·b·k'φ)(z/b)^n [20], 차원해석 [21].

## 5. 상관식 (입력 → Bekker)

| 입력 | 식 | 범위·한계 | 출처 |
|---|---|---|---|
| CI (psi) | 점토: kc = 0.19·CI, kφ = 0.48·CI (영미) | WES 1964, Vicksburg 점토 | [3] |
| CI | 모래: kc = 0.15·CI − 3.20, n ≈ 1, kφ는 Janosi 식 반복 | Yuma 모래 등 | [3] |
| CI 깊이 분포 | Janosi(1959) 원추-Bekker 적분식 | Bekker가 검증 부족이라 함, c·φ는 CI와 무관 | [3] |
| CI 연속 | Huang·Wong 등(2020) 개선 모델 + DFOA | LETE·KRC | [22] |
| ks 또는 K30 | n = 1, kc = 0, kφ ≈ ks(판 폭 ≈ 패드 폭) | 조사자 추론 | [14][16] |
| 허용 지지력 qa | Bowles: ks ≈ 40·SF·qa (kN/m³, qa kPa, 25 mm) | 대략값 | [15] |
| SPT·cu | 직접 상관식 없음 → 지반 범주 → 허용 지지력 표 | — | [11] |

## 6. Chrono SCM elastic_K·R

- API 주석 [5]: elastic_K "elastic stiffness K per unit area, [Pa/m] (must be larger than Kphi)", damping_R "[Pa.s/m]", "A very large value of K and R=0 reproduce the original SCM". 근거 논문 Gallina·Krenn 등 [23].
- 제하는 기울기 K 탄성 구간, s_p = s − σ/K, σ_tot = σ + v_n·R. K는 순수 소성 Bekker의 수치 불안정 방지용 [9].

| 출처 | Kφ | kc | n | c | φ | Janosi | K [Pa/m] | R [Pa·s/m] |
|---|---|---|---|---|---|---|---|---|
| SCMTerrain.cpp 생성자 기본값 [7] | 2e6 | 0 | 1.1 | 50 | 20° | 0.01 | 5e7 | 0 |
| Wheeled 데모 [6] | 2e6 | 0 | 1.1 | 0 | 30° | 0.01 | 2e8 | 3e4 |
| Tracked 데모 [6] | 2e7 | 0 | 1.1 | 0 | 20° | 0.01 | 2e8 | 3e4 |
| cosim scm_soft.json [8] | 2e6 | 0 | 1.1 | 0 | 30° | 0.01 | 4e7 | 3e4 |
| cosim scm_hard.json [8] | 2e7 | 0 | 1.1 | 0 | 20° | 0.01 | 2e8 | 3e4 |

- 측정 근거 1, Wong 반복하중: 제하 기울기 k_u = k0 + Au·z_u, LETE Au = 503,000 kN/m⁴ [24](검색 발췌만). z_u 2~5 cm에서 k_u 약 1e7~2.5e7 Pa/m.
- 근거 2, Lysmer 상사 [25][26]: k = 4GR/(1−ν), c = 3.4R²√(ρG)/(1−ν) → 면적당 R ≈ 1.08ρVs/(1−ν). ρ 1800, ν 0.3, R_eq 0.185 m에서 Vs 100 m/s: K ≈ 1.8e8 Pa/m, R ≈ 2.8e5 Pa·s/m; Vs 200 m/s: K ≈ 7e8, R ≈ 5.6e5(작은 변형 탄성값이라 K는 상한 쪽).
- 근거 3, K30 재재하 기울기: 1e8~3e8 Pa/m [16].
- Janosi K: Chrono 주석 "usually few mm or cm" [7], 데모 0.01 m [6], 달 토양 1.78 cm [27], 사질토 bevameter 약 5~56 mm [10]. 정지 패드에서는 영향 작음.

## 7. 지반 범주별 지지력 표

CPA 1402 (2014) Annex B, presumed allowable bearing value [kN/m²] [11]: 조밀 자갈(SPT > 50) > 600, 중간 조밀 자갈 < 200~600, 느슨한 자갈 < 200, 조밀 모래(SPT 30~50) > 300, 중간 조밀 모래 100~300, 느슨한 모래 < 100, 매우 굳은 점토(cu > 150) 300~600, 굳은 점토(cu 70~150) 150~300, 견고한 점토(cu 40~75) 75~150, 연약 점토(cu 20~40) < 75, 매우 연약 점토 Nil, 유기질·매립 20~50. (예시에서 극한값에 안전율 2.)

CICA & CANZ Table 2, 최대 허용 지압 [12][13]: 경암 2000 kPa, 셰일·사암 800, 다짐 자갈(모래 ≤ 20 %) 400, 아스팔트·다짐 모래·굳은 점토(건조) 200, 연약 점토(건조)·느슨한 모래 100, 습윤 점토 < 100.

국내 「건축물의 구조기준 등에 관한 규칙」 별표 8, 장기 허용지내력 [kN/m²](단기 = ×1.5) [28]: 경암반 4000, 연암반 2000/1000, 자갈 300, 자갈·모래 혼합 200, 모래 섞인 점토·롬토 150, 모래 또는 점토 100. 국내 아우트리거 받침판 규격표는 단기값을 쓴다고 밝힘 [29].

국내 천공기·항타기 지침: 수치 기준 없음. KOSHA C-71-2012는 아우트리거 설치 후 사용·지내력 확보를 정성적으로만 기술 [30], 항타기 작업계획서 지침은 소요/작업장소 지내력과 철판 보강 기재 [31].

## 8. 불확실·미확인

- Wong 원서는 열람하지 않았다(표 번호·쪽 미확인; 판마다 다를 수 있음, Chrono 포럼은 Terramechanics 책 "Table 12.10" 언급 [9b]).
- WES CI 207 행은 Mason 투고본 값(게재본 미대조). K30 기준은 2차 출처(원 시방 조항 미확인). Janosi K의 Wong 대표값은 출처 미발견.
- 로컬 확인 필요(chrono-rag): PyChrono 10.0 SCMTerrain의 패치 b 계산이 2A/둘레인지(dynamics 개정 45에서 볼록 껍질 2A/둘레로 확인됨), elastic_K > Kφ 조건 검사 여부와 n ≠ 1 처리.

## 출처

[1] NASA TM-20250006958 (2025), https://ntrs.nasa.gov/api/citations/20250006958/downloads/TM-20250006958.pdf
[2] Kasetsart Univ. 전자책 p.457 표 8.4 (Wong 1978 인용), https://ebook.lib.ku.ac.th/ebook27/ebook/20150106/files/basic-html/page467.html
[3] Mason et al., An overview of methods to convert Cone Index to Bevameter Parameters (2019 투고본), https://apps.dtic.mil/sti/pdfs/AD1112095.pdf (doi 10.1016/j.jterra.2019.10.001)
[4] 基于滚动阻力实时监测的软路面识别方法 (2014), https://www.ingentaconnect.com/content/tcsae/tcsae/2014/00000030/00000011/art00006
[5] Chrono SCMTerrain.h, https://raw.githubusercontent.com/projectchrono/chrono/main/src/chrono_vehicle/terrain/SCMTerrain.h
[6] Chrono release/10.0 데모 demo_VEH_SCMTerrain_WheeledVehicle.cpp / TrackedVehicle.cpp
[7] Chrono release/10.0 SCMTerrain.cpp, ChTireTestRig.h
[8] Chrono release/10.0 data/vehicle/cosim/terrain/scm_soft.json, scm_hard.json
[9] SBEL TR-2017-01, https://sbel.wisc.edu/wp-content/uploads/sites/569/2018/05/TR-2017-01.pdf ; Chrono 지형 문서 https://api.projectchrono.org/vehicle_terrain.html ; [9b] projectchrono Google 그룹 "SCM Terrain Parameter Units" (2024-08)
[10] Kruger, Bevameter in-situ plate sinkage and shear (Univ. Pretoria, 2023); Apfelbeck et al. (2011), https://elib.dlr.de/69724/1/Apfelbeck_BevameterTest_JTerra2011.pdf
[11] CPA 1402 Ground Conditions for Construction Plant (2014), https://www.ipaf.org/sites/default/files/2019-11/SFPSG-Guidance-on-Ground-Conditions-for-Construction-Plant.pdf
[12] CICA & CANZ Guidance Note: Crane stability and ground pressure, https://www.cranes.org.nz/uploads/2/0/5/7/20572552/crane_stability_and_ground_pressure.pdf
[13] John Holland GMR 3.3
[14] Strand7 – Modulus of Subgrade Reaction (Bowles 1997)
[15] LUSAS 1004 Winkler spring models (요약만)
[16] 한국시험공사 – 도로평판재하(KS F 2310) (2차); KS F 2310 표준 정보(최종 개정 2025-12-02)
[17] Feng & Ma (2017), doi 10.2991/ammee-17.2017.29
[18] Bearing capacity (Terzaghi 식), Wikipedia
[19] Rashidi et al., Evaluation of Bekker Model under Field Conditions (MEJSR)
[20] Salman & Kiss (2019), doi 10.21791/ijems.2019.1.24.
[21] Scaling considerations in plate-sinkage tests, HRR 145 (1966)
[22] Huang, Wong et al., Predicting terrain parameters from cone index data (2019/2020), DTIC AD1082843
[23] Gallina, Krenn et al. (2013), J. Field Robotics, doi 10.1002/rob.21480
[24] Wong, Theory of Ground Vehicles 3판 / Terramechanics and Off-Road Vehicle Engineering 2판 (LETE Au, 발췌만)
[25] Lysmer, Vertical Motion of Rigid Footings (1965)
[26] Asik (1993, TTU); Olmos et al. (2019), doi 10.21595/vp.2019.20913
[27] Carrier, Lunar soil trafficability parameters (LPI)
[28] 건축물의 구조기준 등에 관한 규칙 별표 8 (개정 2021-08-27)
[29] 프로메카 – 아우트리거 받침판 규격표 (2020, 업체 블로그)
[30] KOSHA GUIDE C-71-2012
[31] 항타기·항발기 사용 작업계획서 작성지침
