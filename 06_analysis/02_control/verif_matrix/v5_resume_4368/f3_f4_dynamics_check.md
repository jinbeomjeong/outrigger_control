# 436.8 rev5 R5-D2·R5-D3 확인: F-3 사건 사례 바닥 각, F-4 패드 접촉력 (dynamics-expert)

- 작성 2026-11-13, dynamics-expert. 읽기와 계산만 했다(실행 행 없음, 추적 파일 수정 없음, 커밋 없음).
- 대상 구현: worktree `.claude/worktrees/agent-ac17a920b9079a929`, 커밋 `e8d413b`.
  - `04_scripts/04_hydraulic/coupled/verdict_runs.py`: `sa4_record`(178~197행), `EVENT_CASE_FLOOR`(510행), 정상 사례 F-3(432~433행)
  - `04_scripts/03_control/s8/r67_g1_screen.py`: `make_base`(155행), `branch`(243행)
  - `04_scripts/03_control/s9/s9_soil_slope.py`: `_lifted_legs`(746행)
- 규칙: `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev5.md` R5-D2(157행), R5-D3(162행). 부상 정의는 rev3 R3-G10 Q-14(476행): 패드 법선 접촉력(진값) ≤ 0인 1 ms 표본.
- 확인 계산: `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\6f3ebc4d-a5fb-4d9f-b214-d0ae5c515ee1\scratchpad\dyn-f3f4\f3f4_check.py`(결과 `f3f4_check.json`, 같은 폴더). 실행: `conda run -n dynamics-dev python -I -B f3f4_check.py`, E코어 affinity 0x00FF0000. 결정론적 계산이고, 난수는 2번 왕복 시험에만 썼다(시드 0).

## 판정 요약

| 항목 | 판정 | 핵심 근거 |
|---|---|---|
| F-3 사건 사례 `case_floor_deg` = [0, 0] | **충분** | `make_base` → `r51._reg_base(..., (0.0, 0.0), ...)` → `Plant(level, 0, 0)`. 이렇게 만든 플랜트의 바닥 법선은 `nrm` = (0, 0, 1)이고, roll·pitch 모두 0.000°로 실측했다. 사건은 패드 하나 아래 바닥을 국부적으로 내리는 것(`goff[leg]`)이고, 바닥 각은 바꾸지 않는다 |
| F-4 `lift_after_stop_ms`의 접촉력 | **충분**(필드 설명 수정 권고) | 근사가 아니다. `true_force + Wr`는 플랜트 커널이 계산한 패드 접촉력 `acc[11:15]` 그 자체를 되돌린 값이고, 부호(≤ 0 여부)가 비트 단위로 보존된다. 하네스 로드는 질량이 없는 준정적 모델이라 빠진 가속도 항이 없다. 실 마찰은 이 값에 들어가지 않는다. 토양 반력 지연은 이 정의를 보수 쪽으로만 민다 |

## 1. F-3: r67 사건 사례의 바닥 각

### 1.1 경로

1. `verdict_runs._run_event`(440행~)는 `r67.make_base(cl, c2, twin.level, twin.fs_kN, contact=judge)`로 플랜트를 만든다. 바닥 각 인자는 없다.
2. `r67_g1_screen.make_base`(159행): `base = r51._reg_base("b", level, (0.0, 0.0), fs_kN, [])`. 세 번째 인자가 `floor`다.
3. `r51_reapp_closed_loop.make_plant`(294~303행): `Plant(base["level"], base["floor"][0], base["floor"][1], Fs=0.0)`. 이 클래스는 `s8_g4_rodside_check.RodSidePlant`(→ `FlexPlant` → `run_control_comparison.Plant`)이고, 흐름 제한을 켜면 `FlowLimitedPlant`로 한 번 더 감싼다.
4. `run_control_comparison.Plant.__init__`(바닥 절): `sx = -tan(pitch)`, `sy = tan(roll)`, `n = (-sx, -sy, 1)/|n|`. roll = pitch = 0이면 `nrm` = (0, 0, 1)이다. 크롤러 접촉도 같은 `nrm`을 쓴다(커널 `physics_flex`의 크롤러 절). 따라서 패드 바닥과 크롤러 바닥이 모두 수평이다.
5. 사건 분기 `r67.branch`(249~254행)의 `floor_fn`은 `pl_.goff[leg] = depth·Poly345(τ)`만 바꾼다. 커널은 `gax = (n·p0 + goff_i)/a_n`이므로, 이 사건은 그 다리 패드 아래 바닥을 법선 방향으로 `depth`만큼 내린다. 바닥 평면의 각은 바뀌지 않는다. 사건 종류는 G4 11.5 mm/2 s, RE1bF 30 mm/0.05 s, FS24 24 mm/0.3 s, SS 11.5 mm/20 s다(`r67.EVENTS`, `verdict_runs.SS_EVENT`).
6. `make_base`를 부르기 전에 `cl.rmf.CONFIG.clear()`가 실행되므로, 마스트나 마찰 같은 변형 설정이 남지 않는다. `make_base`는 `init_ext`를 주지 않으므로 해석 정착 자세에서 시작한다.

### 1.2 실측 (`f3f4_check.json` `event_plant`, level top, F_s 4 kN)

| 양 | 값 | 단위·기준 |
|---|---|---|
| `nrm` | (0.0, −0.0, 1.0) | 월드 좌표 바닥 법선 |
| 법선에서 되돌린 바닥 roll / pitch | 0.000 / 0.000 | deg, ZYX(내재), `Plant.__init__`와 같은 식 |
| `goff` 초기값 | (0, 0, 0, 0) | m |
| 크롤러 정착 뒤 몸체 자세 roll / pitch | 0.00026 / 0.1787 | deg. 바닥이 아니라 몸체 자세다(하네스 강체 크롤러의 정착 앞내림, `s9_soil_closed_loop` 문서의 0.179°와 같다) |

### 1.3 판정과 주의

- **충분.** [0, 0]은 사례 정의(`_reg_base` 바닥 (0, 0))에서 나온 실제 플랜트 바닥 값이다. `case_floor_source` 문구("r67 event branch on the level rigid floor of the r51 harness (make_base has no floor angle)")도 코드와 맞는다.
- 주의 1: 바닥 각 0은 몸체 자세 0을 뜻하지 않는다. 정착 앞내림 0.179°가 있다. F-3를 J3 같은 판정에 쓸 때 몸체 자세와 섞지 않는다.
- 주의 2: 사건 사례에서 바닥이 평면이 아니게 되는 것은 사건 다리 아래 국부 침하(`goff`)뿐이다. 이것은 바닥 각이 아니므로 F-3에 들어가지 않는 것이 맞다.
- 참고(질문 범위 밖, 정상 사례 F-3): `values.case_floor_deg = [payload["roll_deg"], payload["pitch_deg"]]`는 사례가 지정한 **명목** 경사다. 토양 사례의 커널 바닥에는 정착 보정이 더해진다: P0 pitch 보정, 정착 표 `floor_roll_add_deg`·`floor_pitch_add_deg`, A1 보정 `droll`·`dpitch`(`s9_soil_closed_loop.make_plant` 345~353행, `s9_soil_slope._make_plant_with_settle`). 그래서 커널 바닥 각과 수 0.1° 다를 수 있다. 출처 문구가 "case roll_deg / pitch_deg"라서 정의상 틀린 것은 아니다. 다만 J3가 "실제 바닥"을 뜻한다면 별도 필드가 필요하다.

## 2. F-4: 부상 판정에 쓰는 패드 접촉력

### 2.1 정의를 따라가 본 결과

- 플랜트 커널 `run_mast_flex_c2_check.physics_flex`(패드 절, 300~350행)는 접촉 중(`c = x_i − gax > 0`)일 때 다음을 계산한다.
  $F_l = \max\!\big(0,\; k_{s,i}\,c + c_{n,i}\,(u_i - v_n/a_n)\big)$, `acc[11+i] = F_l`(fmode 0). 접촉이 아니면 `acc[11+i] = 0`이다.
  이 값이 몸체에 실제로 가해지는 패드 힘이다(`Fi = F_l e_z + F_t`).
- 하네스 플랜트는 fmode 0이다(실측 `fmode` 0). `acc[11+i]`는 로드 축 방향 성분이고, 바닥 법선 성분은 $N = F_l\,a_n$, $a_n = n\cdot e_z > 0$이다. 둘은 부호가 같으므로 ≤ 0 판정은 같다.
- 1 ms 행의 `TRUE_FORCE` 열은 `harness_flow.record_plant_state`(192행)에서 `accumulated[11:15] − plant.Wr`로 채운다. `accumulated`는 `RodSidePlant.step`이 묶은 값이고, 11:16 칸은 그 1 ms 청크의 **마지막 0.5 ms 스텝** 값이다(dt = 5×10⁻⁴ s, 실측).
- `sa4_record`는 `contact = TRUE_FORCE + Wr`로 이것을 되돌린다. 따라서 "참 F_cyl + 로드 무게"는 근사가 아니라 `acc[11:15]`를 그대로 복원한 것이다. 하네스 `s9_soil_slope._lifted_legs`(`fmin_kN + rod_weight_kN`, `control_period` 440행 `acc[11:15] − Wr`)와도 같은 양이다.
- 로드 무게: `Wr = rod_mass·g` = 1047.19 N(전방), 717.48 N(후방). rod_mass는 106.75 / 73.14 kg이다. `scale_plant_mass`는 `Wr`을 바꾸지 않는다. 런 도중 바뀌는 곳도 없다.

### 2.2 부호 보존 (`round_trip`)

- 0에서 시작하면 $(0 - W_r) + W_r = 0$이 float64에서 정확히 성립한다. 시험에서도 `zero_stays_zero` = true였다.
- 양수 $F \in [10^{-300}, 10^{6}]$ N 20만 개 × Wr 4개를 시험했다. 왕복 뒤 음수가 된 경우는 0건이었다. 0으로 떨어진 양수는 모두 $F \le 1.13\times10^{-13}$ N(Wr의 반 ulp 이하)이다. 물리적으로 0과 같으므로 판정이 뒤집히지 않는다.

### 2.3 경계 사례 검토

| 요인 | 하네스에서의 영향 | 판정이 뒤집히는가 |
|---|---|---|
| 실 마찰 F_s | 커널은 실 마찰을 로드 위치 `x_i`의 준정적 해(`_solve_leg_l1r`, 마찰 고착/미끄럼)에만 넣는다. `F_l`은 그 `x_i`에서 패드 스프링·감쇠로 직접 계산한다. `TRUE_FORCE = F_l − W_r`는 "기름 힘 + 로드측 힘 + 실 마찰"과 같다. 패드 힘을 되돌릴 때 마찰을 빼거나 더하는 근사가 없다 | 아니오. 다만 **`OIL_FORCE` 열(유량 제한기의 기름 힘, 마찰 제외)에 Wr을 더하는 식으로 바꾸면** 최대 F_s(4 kN, 후방 3.33 kN)와 로드측 힘만큼 틀린다. 지금 구현은 `TRUE_FORCE`를 쓰므로 해당하지 않는다 |
| 가동부(로드·패드) 질량 가속 | 하네스 로드는 질량이 없다. `x_i`를 매 스텝 힘 평형으로 대수적으로 풀고, 로드 질량은 정적 무게 `Wr`로만 들어간다. 따라서 플랜트에 "빠진 $m_r a$ 항"이 없다. 비교용으로만 크기를 적으면, 하네스 밸브 지연 0.1 s의 가속도 $v_{max}/\tau_v$ ≈ 0.21 m/s²에서 $m_r a$ ≈ 22 N(전방)이다. Chrono 2 ms 감속 정지라면 $v_{max}/0.002$ ≈ 10.5 m/s²에서 1.1 kN / 0.77 kN이 된다 | 하네스 안에서는 아니오. Chrono와 시각을 비교할 때만 차이 요인이 된다 |
| 토양 반력 지연(SCM형 요소) | 커널 `acc`는 직전 청크 상태에 대해 선형화한 토양 접선 스프링(`soil_floor`의 `ks_eff`, `goff = z0 − h`)으로 계산한 힘이다. 확정한 토양 요소 힘 `so.force`는 따로 있다. 시험(J1, 패드 B, F_s 4 kN, FL을 약 48 kN까지 눌렀다가 수축)에서 커널 접촉력은 토양 요소 힘보다 **11 ms(11청크) 먼저** 0이 됐다. v_max 수축(−20.9 mm/s)에서 커널이 0일 때 `so.force`는 2.45 kN이었고, 0.05 v_max에서는 0.28 kN이었다. 반대 경우(토양 요소 0, 커널 > 0)는 0청크였다. 차이의 대부분은 커널 접촉력에 들어 있는 다리 감쇠 항 $c_n u$다. v_max에서 $C_{MOVE}\,v_{max}$ ≈ 100206 × 0.0209 ≈ 2.1 kN이다 | 커널 정의가 부상을 **더 일찍, 더 자주** 잡는다(보수 쪽). "정지 뒤 부상 0"(Q-S6) 판정을 거짓 통과로 뒤집지는 않는다. 거짓 실패 가능성은 수축 중이거나 패드 속도가 클 때 ~10 ms 창에만 있다 |
| 1 ms 표본 | 청크의 마지막 0.5 ms 스텝만 남는다. 청크 첫 스텝에서만 0이 되고 끝에 다시 닿는 0.5 ms짜리 부상은 놓친다. 하네스 `_lifted_legs`도 같은 표본을 쓴다. `acc[24:28]`(호출 내 최소)은 `RodSidePlant.step`이 스텝마다 다시 초기화해서 청크 최소로 쓸 수 없다 | 실제로 문제 될 가능성은 낮다(0.5 ms 미만 부상). Q-14가 "1 ms 표본"으로 정의했으므로 정의에 맞는다 |
| `TRUE_FORCE` NaN | 행은 `limit()`가 만들고 `record_plant_state`가 채운다. 그 사이에 예외가 나지 않는 한 NaN이 없다. NaN이면 `NaN + Wr ≤ 0`이 거짓이 되어 접지로 셈한다(비보수) | 지금 경로에서는 해당 없음. 방어 검사를 권고한다(아래) |

### 2.4 플랜트에 더 직접적인 값이 있는가

| 후보 | 내용 | 평가 |
|---|---|---|
| `acc[11:15]` | 커널 패드 접촉력(로드 축 방향, 감쇠 포함, 0으로 자름). 몸체에 가해지는 힘 | **이것이 플랜트 값이다.** F-4는 이미 이 값을 쓰고 있다(왕복 복원) |
| `plant.soil.force` | 확정한 토양 요소 힘(암시 오일러, 1 ms마다). 토양 쪽 표현 | 몸체에 가해지는 힘이 아니다. 커널보다 ~11 ms 늦게 0이 되고, 1 ms 행에 기록되지 않는다. Chrono SCM `scm_pad_normal_N`과 비교하는 보조값으로는 쓸 수 있다 |
| `acc[49:53]` | 바닥 법선 N | fmode 1에서만 채운다. 하네스는 fmode 0이라 쓸 수 없다 |
| `acc[24:28]` | 호출 내 최소 접촉력 | 스텝마다 초기화되어 청크 최소가 아니다 |

### 2.5 판정

- **충분.** R5-D3의 첫 번째 경우("하네스 플랜트가 그 값을 따로 가지면 그 값을 쓴다")에 해당한다. `TRUE_FORCE + Wr`는 플랜트 패드 접촉력 `acc[11:15]`와 ≤ 0 판정이 비트 단위로 같다. 따라서 "근사 정의, dynamics 확인 대기" 표기는 필요 없다.
- 필드 설명 수정 권고(기록 문구만, 값은 그대로): `rule`을 "1 ms rows t >= t_stop with the harness kernel pad contact force acc[11:15] (= TRUE_FORCE + Wr, exact round trip; rod-axis component, leg dashpot included, clipped at 0) <= 0"으로 바꾼다. 로드 가속도 항을 무시한다는 가정은 적지 않는다. 하네스 로드는 질량이 없어서 그런 항이 없다.
- 판정서에 적을 한계 2줄:
  - (a) 이 정의는 "압축력 없음"이다. 토양 요소 힘이나 기하적 이격보다 ~10 ms 먼저 부상을 잡는 보수 쪽 정의다.
  - (b) Chrono SCM `scm_pad_normal_N`과 부상 시각을 비교하면 감쇠 항과 1 ms 표본 차이로 ms 단위 어긋남이 날 수 있다.
- 방어 검사 권고(위임 필요, python-expert, 값에 영향 없음):
  - `sa4_record`의 `getattr(plant, "Wr", 0.0)` 기본값 0은 `Wr`이 없는 플랜트에서 접촉력을 Wr만큼 낮게 읽어 거짓 부상을 만든다. 0 대신 예외를 내게 한다.
  - `t >= t_stop` 행의 `TRUE_FORCE`에 NaN이 있으면 예외를 내게 한다.

## 기호

| 기호 | 뜻 | 단위 |
|---|---|---|
| $F_l$ | 커널 패드 접촉력(로드 축 방향, `acc[11+i]`) | N |
| $k_{s,i}$ | 패드 직렬 스프링(강체 바닥: 로드·브래킷·슬래브 직렬, 토양: `ks_eff`) | N/m |
| $c_{n,i}$ | 다리 감쇠(`C_LOCK`/`C_MOVE`, 밸브 출력 \|u\| > 1e-6 m/s이면 이동 값) | N·s/m |
| $c$ | 패드 침투(`x_i − gax`) | m |
| $u_i$, $v_n$ | 다리 속도 명령(밸브 지연 평균), 패드점 속도의 법선 성분 | m/s |
| $a_n$ | $n\cdot e_z$(바닥 법선과 몸체 z축의 내적) | − |
| $W_r$ | 로드·패드 가동부 무게 `rod_mass·g` | N |

## 가정

- 토양 수축 시험은 J1, 패드 B, top, F_s 4 kN, FL 한 다리, 정착 훅 "p0"(기본)로 한 대표 조건 하나다. 지연 11 ms와 2.45 kN은 이 조건의 값이고, 다른 토양·속도에서는 크기가 다를 수 있다. 방향(커널이 먼저 0)은 감쇠 항의 부호에서 나오므로 일반적이다.
- 제어기 없이 다리 명령을 직접 주었다(정지 뒤 SA-4 실제 런이 아니다). 정의를 확인하는 용도다.

사용한 스킬: 없음
