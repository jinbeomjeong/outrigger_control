# 감쇠비 조사와 설정값 (2026-10-20)

web-research-expert(정밀 모드) 조사 요약과 사용자 결정. 모델 반영은 [dynamics_model.md](dynamics_model.md).

## 결정 (사용자, 2026-10-20)

| 항목 | 이전 가정 | 결정 | 감도 범위 | 맞추는 모드 |
|---|---|---|---|---|
| 다리 축, 잠긴 실린더(L1·L2b 정지) | ζ 0.05 | **ζ 0.03** | 0.01~0.10 | 상하(heave) 모드 약 7.4 Hz |
| 다리 축, 이동 중(밸브 구동, L2) | — | ζ 0.10 | 0.05~0.20 | 같음 |
| 크롤러 접지 | ζ 0.10 | **콘크리트 0.05 / 토양 0.2** | 0.02~0.3 | 크롤러 지지 상하 모드 |
| 구조·마스트 모드(유연 모델 도입 시) | — | ζ 0.015 | 0.005~0.05 | — |

- 실 마찰(F_s)은 점성 감쇠에 섞지 않고 따로 모델링한다(이중 계상 방지).
- 다리마다 고정된 대시포트 c를 쓰면 모드별 감쇠비는 $\zeta_i = c\,\omega_i/(2k_i)$로 진동수에 비례한다. 상하 모드(7.4 Hz)에서 0.03으로 맞추면 로킹 모드(1.8 Hz)는 약 0.007로 낮아진다(보수적).
- 모든 값은 **문헌에서 끌어낸 추론값**이다. 잠긴 실린더·강재 트랙·강재-콘크리트 접촉의 감쇠 실측값은 공개 자료에서 찾지 못했다. 실측이나 제조사 자료가 나오면 바꾼다.

## 근거

### 유압 실린더
- "0.1~0.2"는 밸브가 열려 구동되는 위치 서보 실린더의 **경험값**이다. 원문: "Very often the relative damping is merely estimated based on experience. The typical values of the damping in oil hydraulic cylinder drives are 0.1-0.2." (Mäkinen, Virvalo, Vilenius 1999)
- 유압 감쇠는 대부분 밸브 유량-압력 계수 Kc에서 나온다. 원문: "Most of the hydraulic damping comes from the valve flow-pressure coefficient" (Rydberg). 파일럿 체크로 잠긴 실린더에는 이 항이 없다 → 점성 감쇠가 작다(추론).
- 실 마찰은 직경과 거의 무관하게 약 1.65 kN + 속도항, 압력 계수 0.004 /bar. "In some cases a friction of 10% of the nominal load force is assumed" (Kühnlein et al., IFK 2012).
- 쿨롱 마찰의 등가 점성 감쇠비 $\zeta_{eq}=2F_c/(\pi k X)$: k 2.1×10⁷ N/m, F_c 2 kN이면 진폭 1 mm에서 0.061, 5 mm에서 0.012. 진폭이 F_c/k(약 0.1 mm)보다 작으면 실이 붙어 감쇠로 작동하지 않는다(추론, Stutts 노트의 식).

### 장비 전체·구조
| ζ | 대상 | 출처 |
|---|---|---|
| 0.8 % / 7.8 % (버킷이 막장에 안 닿음 / 닿음), 약 0.6 Hz | 버킷휠 굴착기 SchRs 1320, 하중 순간 해제 시험 | Gottvald 2010 |
| 2.67 % (해석) / 3.1 % (실험) | 콘크리트 펌프트럭 붐 회전 진동 | Yang et al. 2017 (초록) |
| 6.6 % / 8.7 % | 선박 탑재 Palfinger 너클붐 크레인(유압계 포함) | Gunnerus digital twin 논문 |
| 약 0.8~6.4 % (대수감쇠율 0.05~0.40) | 천장·갠트리 크레인 구조 | Mironov et al. 2020(핸드북 재인용) |
| δs 0.012~0.05 (ζ 약 0.2~0.8 %) | 강구조물 일반 | EN 1991-1-4 Table F.2 |
| 용접 2 %/4 %, 볼트 4 %/7 % | 강구조(OBE/SSE) | NRC RG 1.61 Rev.1(2차 문서 재인용) |

- 크레인 규격(EN 13001-2, ISO 4302)은 감쇠비를 주지 않고 동적 계수로 다룬다.
- 시추 마스트 축소 모형(Lambrescu & Pana 2015)의 ζ 0.17은 표의 반전력 주파수와 맞지 않아(계산하면 약 0.022) 근거에서 뺐다.

### 패드-지면
- 콘크리트(강체): 방사 감쇠 없음.
- 단단한 토양: Lysmer 근사 $\zeta_z = 0.425/\sqrt{B_z}$, $B_z=(1-\nu)m/(4\rho r^3)$. r_eq 0.185 m, m 9,650 kg(다리당), ρ 1,900 kg/m³, ν 0.3 → B_z ≈ 141, **ζ_z ≈ 0.036**(추론). 지반 대시포트 $c_z \approx 3.4 r^2\sqrt{\rho G}/(1-\nu)$ ≈ 51 kN·s/m(G 50 MPa)를 다리와 직렬로 더하고, 재료 감쇠는 $2K\beta/\omega$(Gazetas 1991). SCM 재판정 때 쓴다.

### 크롤러-지면
- 강재 트랙 실측값 없음. 고무 트랙(Coneo et al. 2025), 오일샌드 광산 셔블(k 20 MN/m, c 120 kN·s/m; Frimpong & Thiruvengadam)만 있다.
- 크롤러 접지를 넓은 기초로 보면 토양에서 ζ ≈ 0.2~0.3(Lysmer 추론, 트랙 치수 가정).
- 아우트리거가 크롤러를 들어 올리므로 크롤러 ζ는 레벨링 초반 접지 전환에만 영향을 준다.

### Chrono SMC 입력 (main 브랜치 소스 해석, 설치본 pychrono 10.0.0 실측으로 확인 2026-10-20)
- Hooke, `UseMaterialProperties(false)`: `gn = eff_mass * mat.gn`, eff_mass = 접촉하는 두 바디의 m1·m2/(m1+m2). 바닥 1e9 kg이면 eff_mass ≈ 패드 질량.
- 따라서 상부체 상하 모드에 ζ를 주려면 $g_{n,input} = 2\zeta\sqrt{k\,m_{mode}}/m_{pad}$로 넣는다.
- `UseMaterialProperties(true)`(반발계수 e 입력)는 패드 질량 기준 접촉 진동자의 ζ라 상부체 모드 감쇠로 쓰지 않는다. e↔ζ: e 0.9 → 0.034, 0.7 → 0.113, 0.5 → 0.215.
- 시간 간격 관례: 접촉 지속시간 t_c = π/ω_d의 5~10 %(EDEM).
- 로컬 확인(2026-10-20, pychrono 10.0.0): 위와 같다. 바닥 질량 1e9/1e3/1 kg에서 c = gn·m₁m₂/(m₁+m₂)(복원 c 상대차 ≤ 2e-3), 두 재질의 kn·gn은 산술 평균으로 합성, YAML gn으로 4패드 강체 heave ζ 0.02999(설계 0.03)·7.3938 Hz(설계 7.3933). SMC 접촉력은 명시 적분이라 접촉 모드에 ωΔt/2 수치 감쇠가 없다(V8(a)·dt 규칙 재검토 대상). 근거 `06_analysis/01_chrono/00_conventions/smc_damping.json`, 회귀 `05_tests/chrono/test_smc_damping.py`.

## 주요 출처
Mäkinen, Virvalo, Vilenius 1999 (doi:10.5739/isfp.1999.709); Rydberg, Hydraulic Servo Systems (diva2:1045004); Gottvald 2010, Transport (VGTU); Yang et al. 2017 ITOEC (doi:10.1109/itoec.2017.8122502); Palfinger crane digital twin (Gunnerus, ASME); EN 1991-1-4 Table F.2; NRC RG 1.61 Rev.1 (ML091340748, ML101660039); Gazetas 1991 ASCE JGE; Lysmer & Richart 1966(2차 출처); Coneo et al. 2025 Sci. Rep.; Frimpong & Thiruvengadam GJRE; Chrono ChContactSMC.cpp (main, 2026-10 열람); Kühnlein et al. IFK 2012; Jaiswal, Sopanen, Mikkola 2021 Nonlinear Dyn.; Stutts, Equivalent Viscous Damping; Mironov et al. 2020 IOP MSE 862; Altair EDEM / Itasca PFC 문서.
