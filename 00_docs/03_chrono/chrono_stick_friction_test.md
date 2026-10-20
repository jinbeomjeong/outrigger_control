# Chrono 10 정지 마찰(stick) 단순 시험 (2026-10-19)

목적은 두 가지다. 첫째, Chrono 10 SMC 접촉이 2° 경사에서 블록을 붙잡는지(V12: 미끄럼 < 0.1 mm), 수평 바닥에서 접선 스프링 $k_t$가 진동수로 드러나는지 확인한다. 둘째, 대안 두 가지(L1용 지면 고정 접선 부싱, L2b용 NSC 접촉)를 확인한다. 배경은 [actuator_L2_feasibility.md](../01_dynamics/actuator_L2_feasibility.md) 4절과 [dynamics_model.md](../01_dynamics/dynamics_model.md) 4절이다.

- 스크립트: `04_scripts/02_chrono/test_stick_friction.py` (재실행: `C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe -I 04_scripts/02_chrono/test_stick_friction.py`, 약 1분)
- 결과: `06_analysis/01_chrono/stick_friction.json`, 그림 `06_analysis/01_chrono/stick_friction.png`
- 환경: pychrono 10.0.0 (conda `Chrono-dev`, Python 3.12)

## 1. 방법

| 항목 | 값 | 출처 |
|---|---|---|
| 블록 질량 $m$ | 9,745.70 kg | `contact.rigid_floor.L1.derivation.damping_mass_kg` / 4 (다리 하나 몫) |
| $k_n$, $k_t$ | 2.0814×10⁷, 8.5105×10⁶ N/m | YAML L1 FL 값(패드당) |
| $c_n$, $c_t$ | 4.5038×10⁴, 2.8799×10⁴ N·s/m | YAML L1 FL 값 |
| μ | 0.5 | YAML (가정) |
| Δt | 2×10⁻⁴ s (수렴 확인은 1×10⁻⁴ s) | `simulation.L1.dt_s` |
| 접촉 형상 | 블록 = 구 1개(r 0.06 m), 바닥 = 고정 상자(경사각만큼 +y축 회전) | dynamics_model.md 4.2 |
| 회전 | 블록 회전을 `ChLinkLockAlign`으로 바닥에 고정한다(구가 구르지 않게 한다. 실제 구도 로드에 고정돼 있다) | 시험 가정 |
| 중력 | (0, 0, −9.80665) m/s², Z-up, 명시 설정 | |
| 적분기·솔버 | `EULER_IMPLICIT_LINEARIZED`. SMC는 `SPARSE_QR`, NSC는 `PSOR`(50/200) 또는 `APGD`(100) | |
| 초기 상태 | 정적 침투 $mg\cos\alpha/k_n$ 위치에 접선력 0으로 놓고 10 s | |
| 수평 진동 | 수평 바닥, 초기 접선 속도 10 mm/s, 감쇠 진동 곡선 맞춤으로 진동수·ζ 추정 | |

기준값(접선 스프링이 있을 때): $f=\sqrt{k_t/m}/2\pi$ = **4.703 Hz**, ζ 0.050. 2° 정적 접선 변형 $mg\sin\alpha/k_t$ = 0.3919 mm. 이 값은 **탄성 변형**이고 미끄럼이 아니다. 미끄럼은 부싱 고정점이 움직인 양(소성 변위)으로 따로 잰다.

## 2. 결과

### 2.1 SMC 접선 모델 (Hooke, `UseMaterialProperties(false)`)

| 경우 | 2° 10 s 변위 | 정상 미끄럼 속도 | 수평 v0 응답 |
|---|---|---|---|
| OneStep | **1,058.6 mm** | 0.1094 m/s | 진동 없음. 3.04 mm 표류 후 정지에 가까움(0 Hz) |
| MultiStep | 1,058.6 mm (OneStep과 **비트 단위 동일**) | 0.1094 m/s | OneStep과 동일 |
| None | 1,118.9 mm | 0.1158 m/s | — |
| OneStep, 슬립 속도 문턱 1e-6 / 1e-2 m/s (기본 1e-4) | 1,058.65 / 1,058.75 mm | 0.1094 m/s | — |
| OneStep, Δt/2 | 1,087.9 mm | 0.1125 m/s | — |

- MultiStep은 OneStep으로 대체된다. 헤더 주석(`ChSystemSMC.h:94`)이 실행 결과로 확인됐다.
- 미끄럼 속도가 $mg\sin\alpha/(k_t\Delta t + c_t)$ = 0.10935 m/s(Δt/2: 0.11248)와 4자리까지 맞는다. 따라서 OneStep 접선력은 $F_t = (k_t\Delta t + c_t)\,v_t$이고 μN에서 잘린다. **정지 마찰 스프링이 없는 점성 마찰**이다. Δt를 줄이면 None($c_t$만, 0.1158 m/s)으로 수렴한다. dynamics-expert 추정(L1 약 0.11 m/s)과 맞는다.
- 슬립 속도 문턱은 미끄럼 속도(0.11 m/s)보다 훨씬 작아 결과를 거의 바꾸지 않는다. 문턱 아래에서는 접선력이 0이 되어 표류만 남는다.

### 2.2 SMC 감쇠 입력의 단위 (실측)

| 시험 | 결과 | 해석 |
|---|---|---|
| 수직 자유 진동, 바닥 질량 1×10⁹ kg, `SetGn(c_n/m)` | 7.357 Hz, ζ 0.0502 (기준 7.355 Hz, 0.050) | Hooke의 `gn`·`gt`는 **유효 질량당 값**이다. 실제 감쇠 = $g\cdot m_{eff}$, $m_{eff}=m_1m_2/(m_1+m_2)$ |
| 같은 시험, 바닥 질량 1 kg(ChBody 기본값) | ζ **0.0010** | 고정 바닥도 질량이 $m_{eff}$에 들어간다. 바닥 질량을 크게 두지 않으면 감쇠가 사라진다 |
| `SetGt(c_t)`(N·s/m 그대로) | 발산(−2.3 m/s, 위로 튐) | 단위를 잘못 넣으면 감쇠가 $m$배가 되어 불안정해진다 |

### 2.3 대안 (a): 지면 고정 접선 부싱 (L1용)

구현은 다음과 같다. SMC 접촉은 수직력만 낸다($k_t=g_t=\mu=0$). 접선은 `ChLoadBodyBodyBushingSpherical`(블록–바닥, 경사면 x·y에 $k_t$, z 강성 0)로 준다. 매 스텝 뒤 Python에서 원형 Coulomb 복귀 사상(return mapping)을 한다. $k_t|d| > \mu N$이면 바닥 쪽 고정점을 옮기고(`SetApplicationFrameB`) 미끄럼 중에는 감쇠를 끈다. $N$은 `block.GetContactForce()`의 법선 성분이다.

| 경우 | 결과 | 기준 | 판정 |
|---|---|---|---|
| 2°, 10 s | 미끄럼(고정점 이동) **0.000 mm**, 항복 스텝 0. 탄성 변형 0.3923 mm(이론 0.3919, +0.1 %). 과도 최대 0.72 mm(탄성) | 미끄럼 < 0.1 mm | 통과 |
| 수평 v0, `c = c_t/2` 입력 | **4.7023 Hz**, ζ 0.0531 | 4.703 Hz, ζ 0.05 (+수치 감쇠 ωΔt/2 = 0.003) | 통과 |
| 수평 v0, `c = c_t` 입력 | 4.7013 Hz, ζ **0.103** | — | 부싱 감쇠는 입력의 **2배**로 작용한다(실측) → 입력을 $c_t/2$로 준다 |
| 수평 v0, `c = 0` | 4.7007 Hz, ζ 0.0014 | 수치 감쇠만 | 에너지 증가 없음 |
| 30°(tan 30° > μ, 미끄러져야 함), 2 s | 1,228.7 mm, 평균 μ_eff **0.505** (말기 속도 기준 약 0.52) | 1,315 mm, μ 0.5 | 미끄럼은 재현된다. 미끄럼 중 마찰이 $k_t v\Delta t$만큼 크다(1 m/s에서 +1.7 kN). 미세 미끄럼(mm/s)에서는 무시할 수 있다 |

Chrono 내장 `ChLoadBodyBodyBushingPlastic`(축별 상자 항복 + 내부 소성 상태, `SetYield`를 매 스텝 μN으로 갱신)도 시험했다.
- 2°에서는 같은 결과다(소성 0, 0.3923 mm).
- **미끄럼 구간이 틀린다.** 30°에서 392 mm(μ_eff 0.554)가 나왔다. `c = 0`이면 발산했다(9,380 m/s).
- 원인 추정: `ChLoadBodyBody`는 강성 행렬을 **유한차분**으로 구한다(헤더 주석). 이때 `ComputeBodyBodyForceTorque`가 섭동 상태로 여러 번 불리면서 소성 상태가 갱신되는 것으로 보인다. 그래서 쓰지 않는다.

### 2.4 대안 (b): NSC 접촉 (L2b용)

| 경우 | 결과 |
|---|---|
| 2°, PSOR 50 / 200회, Δt 2×10⁻⁴ | 미끄럼 2×10⁻¹² m(사실상 0). 50회로 충분하다 |
| 2°, APGD 100회 | 미끄럼 0.28 µm. 블록 하나에 10 s(벽시계)가 걸려 PSOR보다 25배 느리다 |
| 30°, PSOR 50 | 1,313.8 mm, μ_eff **0.5000** (해석해 1,315 mm) |
| 수평 v0 | 9.2 µm 뒤 즉시 정지. 강체 마찰이라 접선 진동이 없다. 접선 유연성은 L2b 횡 부싱이 맡는다 |

### 2.5 Δt 수렴 (Δt = 2×10⁻⁴ → 1×10⁻⁴ s)

| 경우 | Δt | Δt/2 | 판정 |
|---|---|---|---|
| 부싱 2° 탄성 변형 | 0.39229 mm | 0.39232 mm | 차 0.01 %. 미끄럼 둘 다 0 |
| 부싱 수평 진동수 / ζ | 4.7023 Hz / 0.0531 | 4.7023 Hz / 0.0516 | 진동수 일치. ζ 초과분(수치 감쇠)이 1/2로 준다(1차) |
| NSC 2° 미끄럼 | 2×10⁻¹² m | 2×10⁻¹² m | 일치 |
| SMC OneStep 2° 미끄럼 속도 | 0.1094 m/s | 0.1125 m/s | 수렴하지 않고 $c_t$만의 점성 표류(0.1158)로 간다 |

## 3. 결론과 권고

1. **Chrono 10 SMC에는 정지 마찰이 없다.** MultiStep은 OneStep과 같다. 2°에서 다리 하나 몫 블록이 0.109 m/s로 계속 미끄러지고, 수평에서는 접선 진동 없이 표류한다. V7·V8·V12의 전제(접선 정지 마찰 스프링)는 SMC 접촉만으로 성립하지 않는다.
2. **L1: 대안 (a) 지면 고정 접선 부싱을 쓴다.** 구현은 `ChLoadBodyBodyBushingSpherical` + Python 원형 Coulomb 복귀 사상이다. 2° 미끄럼 0, 진동수 4.702 Hz(이론 4.703), Δt 수렴을 확인했다. 전체 모델에서 지킬 것:
   - 부싱 감쇠 입력 = 원하는 값 / 2(실측 2배).
   - 패드별 수직력 $N$은 접촉 보고(`ReportContactCallback` 등)로 패드마다 따로 구한다(로드 바디에 다른 접촉이 없으면 `GetContactForce()`도 된다).
   - 부상하면 $N = 0$ → 고정점이 따라간다(이 시험의 복귀 사상이 그대로 처리한다).
   - SMC 접촉 재질은 $k_t=g_t=\mu=0$.
   - `ChLoadBodyBodyBushingPlastic`은 쓰지 않는다.
3. **L2b: 대안 (b) NSC 접촉을 쓴다.** PSOR 50회, Δt 2×10⁻⁴ s에서 2° 미끄럼 0, 30°에서 μ 0.5를 정확히 재현한다.
4. **SMC 공통 주의(수직 접촉에도 해당):**
   - Hooke `gn`·`gt`는 유효 질량당 값이다. 고정 바닥 바디 질량을 크게(예: 1×10⁹ kg) 두거나, 실제 유효 질량으로 나눠 넣는다.
   - 바닥 질량을 ChBody 기본값 1 kg으로 두면 수직 감쇠가 50분의 1로 사라진다(ζ 0.05 → 0.001). 전체 모델의 V7 감쇠 판정에 직접 영향이 있다.

## 4. 확인한 Chrono API (pychrono 10.0.0)

- `ChSystemSMC`
  - `SetContactForceModel(ChSystemSMC.Hooke)`, `UseMaterialProperties(False)`
  - `SetTangentialDisplacementModel(ChSystemSMC.OneStep | MultiStep | _None)`. Python에서 None은 `_None`이다. 기본값은 OneStep(=1)이다.
  - `SetSlipVelocityThreshold` / `GetSlipVelocityThreshold`(기본 1×10⁻⁴ m/s)
- `ChContactMaterialSMC`: `SetKn`, `SetKt`, `SetGn`, `SetGt`, `SetFriction`, `SetRestitution`
- `ChContactMaterialNSC`: `SetFriction`. 솔버는 `ChSystemNSC.SetSolverType(ChSolver.Type_PSOR)`, `GetSolver().AsIterative().SetMaxIterations(n)`
- `SetCollisionSystemType(ChCollisionSystem.Type_BULLET)`, `SetGravitationalAcceleration` (기본값은 0벡터)
- `ChCollisionShapeSphere(mat, r)`, `ChCollisionShapeBox(mat, lx, ly, lz)`(전체 길이), `body.AddCollisionShape(shape, ChFramed)`, `EnableCollision(True)`
- `ChLinkLockAlign`(상대 회전 3개만 구속)
- `ChLoadContainer` + `ChLoadBodyBodyBushingSpherical(bodyA, bodyB, abs_frame, k_xyz, c_xyz)`
  - `SetStiffness`, `SetDamping`, `SetApplicationFrameB(frame_local_B)`, `GetForce()`(B 프레임)
  - 힘은 B 바디(여기서는 바닥) 쪽 프레임 축 기준이다.
- `ChLoadBodyBodyBushingPlastic(..., yield_xyz)`: `SetYield`, `GetPlasticDeformation`. 축별 상자 항복이다. 미끄럼 구간이 불안정해서 쓰지 않는다.
- `ChBody`: `GetContactForce()`(이 시험에서는 블록이 회전하지 않아 전역/국부 프레임을 구분하지 못했다. 전체 모델에서 확인 필요), `AddAccumulator`/`EmptyAccumulator`/`AccumulateForce(idx, F, point, local)`
- 함정: `body.GetPos()`는 내부 벡터 참조를 돌려준다. 초기값을 저장하려면 `ChVector3d(body.GetPos())`로 복사한다.

## 5. 가정

| 가정 | 값 | 비고 |
|---|---|---|
| 블록 질량 | 다리 하나 몫 9,745.7 kg | 실제 패드별 하중은 V1에서 73.8~119.3 kN이다(이 시험은 평균 95.6 kN) |
| μ | 0.5 | YAML 가정 |
| 바닥 질량 | 1×10⁹ kg | $m_{eff}$ ≈ 블록 질량으로 만들기 위한 값 |
| 블록 회전 고정 | `ChLinkLockAlign` | 실제 모델에서는 구가 로드 바디에 붙어 있다 |
| 미끄럼 후 감쇠 재가동 속도 | 1 mm/s | 부싱 복귀 사상의 내부 설정. 30° 시험에만 영향 |
| 부싱 감쇠 2배 | 실측(ζ 0.103 vs 0.050) | 원인 미확인(헤더만 있음). Chrono 버전이 바뀌면 다시 잰다 |
