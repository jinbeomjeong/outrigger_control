# V5-OPENLOOP-R 후속 2행 사전 예측 (결과 보기 전 봉인)

- 작성: dynamics-expert, 2026-11-09. 사용자 결정(2026-11-09 새벽)에 따른 R 감도 후속 실행 2행이다. 이 문서를 쓸 때 두 행은 실행되지 않았다.
- 앞 문서: `openloop_R_prereg.md`(봉인 `69a1be91…`), `openloop_R_judgement.md`(개정 1). 이 문서는 앞 봉인을 바꾸지 않는다. 앞 판정(H-Ru 기각, H-C 판정 불가)도 이 문서로 다시 판정하지 않는다. 아래 (a)의 결과는 **보조 기록**으로만 붙인다.
- 행 정의(`s9_batch` 행 추가)는 하지 않았다. 실행 명세는 부록 A에 있고, 실행은 메인 세션이 compute-scheduler 배치로 한다.
- 기호: λ = R / 9.92×10⁵(J1 기준). 단위 kN, mm, s. 힘은 실린더 힘 $F_{cyl}$(신장 +). 시각은 절대 시각이고 들어 올림은 8 s에 시작한다. 중력 $-9.80665\,\hat z$ m/s². 크롤러 앞끝은 기체 x = +1.30 m 점(소각 근사, pitch > 0 = 앞내림).

## 0. 두 행

| 행 | 목적 | R [Pa·s/m] | λ | 코드 판 |
|---|---|---|---|---|
| (a) `P3a_J1_B_V0_rep` | 기준 행 비트 재현(판 차이 분리) | 992,000(재정의 없음) | 1 | dce5194 |
| (b) `P3a_J1_B_V0_R1490k` | R 상한(크롤러 heave 탄성 가지 ζ 0.3) | 1,490,000 | 1.5020 | dce5194 |

- ζ 대조: 같은 K(2×10⁸ Pa/m)·같은 모드에서 ζ ∝ R다. 기준 R 9.92×10⁵ ↔ ζ 0.2이므로 1.49×10⁶ ↔ ζ 0.2 × 1.49/0.992 = **0.3004**다.

## 1. (a) 기준 행 비트 재현

### 1.1 예측

- (a)의 `series.npz` SHA-256이 기준 행 `07_results\S9\batch_V5-OPENLOOP-V0_20261108_123517\P3a_J1_B_V0\series.npz` = `1da6ea10a775f51f5f9067ad74f89a7eb6af6217c887b5f1c642b95402e679b1`과 **같다**.
- 근거
  - 38d08ab(기준 행) → dce5194 코드 차이는 level 경로·태그·level 파서·c2/v5_options다. `machine` 경로는 쓰지 않는 것으로 추정한다(판정서 6절 [추정]).
  - 두 판 모두 `hull_hook.py`가 없다(`git ls-tree`로 확인, 2026-11-09). 볼록 껍질 훅 차이는 없다.
  - 같은 스레드 수(4)에서는 실행 사이에 비트가 같았다(G-C, R-0 재현 기록).
  - 파일 해시 비교는 유효하다. Chrono-dev numpy 2.5.4의 `np.savez`는 zip 항목 시각을 1980-01-01로 고정한다(2026-11-09 실측: 같은 배열을 2.5 s 간격으로 두 번 저장해 SHA-256이 같았다).
- 기준 행에는 `OMP_WAIT_POLICY` 기록이 없다. (a)는 PASSIVE로 돌린다(행 정의서 2절 가정: PASSIVE에서 비트 동일).

### 1.2 비교 절차 (결과 뒤 바꾸지 않음)

1. **정체성 확인**(하나라도 다르면 비교하지 않고 실행 문제로 보고한다): `result.json` `meta.params_sha256` = `d06a97dddf71553995b89254b5e1161cd85af43bc87a1c1658945cada64d8859`, `meta.scm_run_sha256` = `de20851ad27e121b9a30262685bf1af94be53a8419bbcbc7535ebed30310c07b`, 흙 `table_sha256` = `b21f0fc11b8883aa0402c5e4e6c1d97b846460f3a50417a34df8980357d739a3`, `pad_variants_sha256` = `00cf734bddc2877be1365da2cf995689b38ccb2736156ba6d307823cfab443ee`, `meta.scm.soil.chrono.damping_R` = 992000, `soil.overrides` 비어 있음, `args.threads` = 4, `placement.mode` = pcore, rc 0.
2. **파일 해시**: `series.npz` SHA-256이 `1da6ea10…`과 같으면 **비트 재현**이다. 끝.
3. 파일 해시가 다르면 **배열 비교**를 한다. 두 파일의 공통 키마다 dtype·shape·바이트(`ndarray.tobytes()`)가 같은지 본다. 한쪽에만 있는 키는 목록으로 적는다.
   - 공통 키가 모두 같고 차이가 기록 전용 키의 추가·삭제뿐이면 **핵심 비트 재현**으로 적는다. 판정에는 2번과 같게 취급한다.
   - 공통 키 하나라도 다르면 **비트 불일치**다. 처음 갈라진 표본(모든 공통 배열 가운데 가장 이른 시각 인덱스)과 그 시각, 첫 배열 이름을 적는다. 갈라진 시각이 후방 접지(기준 행 24.2985 s) 전이면 정착 상태 차(7~8 s pitch·z, 후방 접지 순간 크롤러 법선 힘)를 함께 적는다.

### 1.3 비트 불일치일 때 판 차이 판정 규칙

H-C 역전 3건(판정서 3절)은 모두 V0 → R888k 단계다(R-4 |Δz(+0.14 s)| 0.0029 mm, R-4c RR 0.021 kN, R-2 RR 0.029 kN). (a)는 R 3행과 같은 판(dce5194)이므로 판 차이를 분리할 수 있다.

1. (a)로 R-1(②′)·R-2·R-3·R-4·R-4c를 2.3절의 고정 스크립트로 계산한다.
2. **판 차이 크기** $D_m = |m(a) - m(\text{기준 행})|$을 세 역전 지표 $m$마다 구한다.
3. 단조성을 (a)를 V0 자리에 넣어 다시 본다: (a) → R888k → R600k → R300k 순서로 R-4 |Δz|는 증가, R-4c·R-2는 RL·RR 모두 감소해야 단조다.
4. 결과 분류(지표마다, 그리고 3건 전체로)
   - **판 차이로 설명됨**: (a) 기준으로 그 지표의 역전이 사라지고, $D_m$ ≥ 원래 역전 폭이다.
   - **판 차이로 설명 안 됨**: (a) 기준으로도 역전이 남는다.
   - **혼합**: 위 둘이 지표마다 다르다.
5. 이 분류는 **보조 기록**이다. 앞 봉인 규칙에 따른 H-C 판정(판정 불가)은 바꾸지 않는다. (a) 기준으로 3건이 모두 사라지면 판정서에 "역전은 판 차이에서 왔을 가능성이 크고, (a) 기준 R888k → R300k는 단조이나 변화 크기는 예측의 약 1/40"을 보조 기록으로 적는다.
6. 비트 불일치이면 (b) 비교의 기준도 (a)로 바꾼다(2.4절).

### 1.4 비트 재현일 때 기록

- 판 차이(38d08ab ↔ dce5194)는 `machine` 경로에서 0이다. 판정서 6절의 두 [추정]을 "확인"으로 바꾼다.
- 결정론이 확인되므로 역전 3건은 실행 산포가 아니라 모델의 실제 응답(작은 비단조)이다. 앞 규칙의 "F-6 산포 안 → 판정 불가"는 봉인대로 유지하고, 이 사실은 보조 기록으로 적는다.

## 2. (b) R 상한 ζ 0.3 행

### 2.1 가설

- **H-P(패드 소성 가지 국한)**: R은 고압 패드의 소성 가지에서만 결과를 좌우한다(지연 시정수 $\tau_{ld} = Rz/(n p)$, RL 패드 기준 R에서 0.57 s, λ 1.5에서 약 0.86 s). 크롤러의 τ는 작아서 이륙 전 후방 골은 R을 1.5배로 올려도 거의 바뀌지 않는다. R을 올리면 패드가 Bekker 곡선보다 더 늦게 가라앉아 크롤러가 더 일찍 뜬다.
- 근거 자료: `openloop_R_compare.json`, `openloop_R_def2.json`, `openloop_R_tm_check.json`(V0·R888k·R600k·R300k), terramechanics-expert 사전 예측 초안.

### 2.2 예측

| 항목 | 기준(V0, λ 1) | (b) 예측(λ 1.502) | 판정 사용 |
|---|---|---|---|
| R-1 ②′ 후방 최소 RL / RR | 11.660 / 11.730 | 기준 대비 \|Δ\| ≤ 0.5 kN(각 다리) | 확인·기각 |
| R-2 전방 접지 순간 후방 힘 RL / RR | 17.818 / 17.713 | \|Δ\| ≤ 0.5 kN | 확인 |
| R-4c 전방 접지 전 후방 피크 RL / RR | 18.962 / 18.870 | \|Δ\| ≤ 0.5 kN | 확인 |
| R-6 이륙 시각 차 Δt_lo | 0(19.086 s, 들어 올림 뒤) | **−0.10 ~ −0.30 s**(중심 −0.2) | 확인·기각 |
| RL 패드 이륙 지연 lag_lo | 9.155 mm | **12 ~ 15 mm**(중심 13.5) | 확인 |
| 크리프 정지 first(이륙 뒤) | 4.05 s | **4.3 ~ 5.3 s** | 확인 |
| C_rel = C/C_V0 (네 패드, $C = z_{end}/F_{max}^{1/n}$) | 1 | 0.97 ~ 1.03(네 패드 모두) | 확인 |
| 끝 자세 변화 Δroll·Δpitch의 기준 대비 차 | −0.288 / −0.271° | 각 \|차\| ≤ 0.15° | 확인 |
| R-5(a) FLAG(R-1 ②′ < 9.415 kN) | 없음 | 없음 | 확인 |
| R-5(b) 후방 SCM 패드 법선 ≤ 0 표본(후방 접지~끝) | 0 / 0 | 0 / 0 | 확인 |
| (기록) RL 이륙 뒤 크리프 | 31.15 mm | 31.5 ~ 34 mm | 기록 |
| (기록) 끝 침하 RL | 89.74 mm | 87 ~ 90 mm | 기록 |
| (기록) H-C 방향: R-4 \|Δz(+0.14 s)\|, R-4 속도 | 0.5590 mm, −7.22 mm/s | 같거나 약간 작음 | 기록 |
| (기록) 끝 Δroll | −0.288° | −0.29 ~ −0.36° | 기록 |

- terramechanics-expert 초안 대비 내가 바꾼 것(근거는 모두 앞 3행 실측값)
  - **이륙 시각**: 초안 −0.05~−0.15 s → −0.10~−0.30 s. 이륙 시각 차는 이륙 순간 RL 지연의 차를 신장 속도로 나눈 값과 맞는다($\Delta t_{lo} \approx -\Delta lag/u$, u = 20.924 mm/s: R888k 0.047 대 실측 0.064 s, R600k 0.165 대 0.170 s, R300k 0.292 대 0.246 s). RL 지연은 λ에 거의 선형이다(9.155 → 8.163 → 5.710 → 3.051 mm, 기울기 약 8.75 mm/λ). 그래서 λ 1.502에서 Δlag ≈ +4.4 mm, Δt_lo ≈ −0.21 s다. τ가 커지면 지연이 포화할 수 있으므로 하한 쪽(−0.10 s)을 넓게 뒀다. 실측 이륙 지연 기울기도 λ가 클수록 커졌다(0.25 → 0.37 → 0.61 s/λ). 그래서 −0.15 s 상한은 너무 좁다고 판단했다.
  - **크리프 정지**: 초안 4.3~4.8 s → 4.3~5.3 s. 실측 기울기가 구간마다 0.93~2.08 s/λ로 흩어진다. Δλ 0.502를 곱하면 +0.47~+1.04 s(4.52~5.09 s)이고, 여기에 ±0.2 s를 더했다.
  - **RL 지연 12~15 mm**: 초안 그대로다. 선형 외삽값 13.55 mm, 포화 시 약 12 mm. 정의는 2.3절의 `openloop_R_tm_check.py`(행 자신의 C 기준)다. terramechanics-expert 정의(V0 10.0 mm)와 다르다.
  - **C_rel 0.97~1.03**: 초안 그대로다. 앞 3행 실측은 0.974~1.032(R300k)이고 R600k(Δλ 0.40)는 0.999~1.019다. Δλ 0.50이면 R600k 수준으로 본다.
  - R-1·R-2·R-4c ≤ 0.5 kN, 끝 자세 ≤ 0.15°: 초안 그대로다. λ 0.30(Δλ −0.70)에서도 R-4c·R-2는 ≤ 0.34 kN, R-1은 ≤ 0.61 kN(RR R300k) 바뀌었다.

### 2.3 판정 정의 (사전 등록 이탈 방지)

- **계산 스크립트를 고정한다.** 아래 세 파일을 쓰고, 바꾸는 것은 `RUNS` 사전(행 경로·u·λ)에 (a)·(b)를 더하는 줄뿐이다. 출력 이름만 `openloop_R_followup_*.json`으로 바꾼다. 사본을 만들면 원본과의 diff가 `RUNS`·출력 경로 줄뿐임을 판정서에 보인다.

| 스크립트(`paper_runs/scripts/`) | SHA-256(봉인 시점) | 쓰는 항목 |
|---|---|---|
| `openloop_R_compare.py` | `ccd4528b3740c8a21e7d11564981b9f47222ec34d51d9fae509a51413f204aaa` | R-2, R-3, R-4, R-4c, R-5, R-6(이륙 시각·크리프·크리프 정지·끝 자세·피크), ① 재계산 |
| `openloop_R_def2.py` | `99bcdc01f805ba3452702c699eb5120fd27d4eda37e8834d4df83c3b65d1cd4d` | R-1 ②′ |
| `openloop_R_tm_check.py` | `878b54a23a43bc7d3b086ea7a9cc94dc7a4ff3ec26a3c2687776c841cacfab91` | lag_lo, C_rel |

- **R-1(판정값) = ②′**: 다리별로, 후방 접지(RL swivel 첫 사건 $t_c$)부터 전방 접지(FL swivel 첫 사건 $t_f$) 전까지의 $F_{cyl}$ argmax(후방 피크 $k_p$)를 찾고, $k_p$부터 크롤러 이륙 $k_{lo}$까지의 최솟값이다. 크롤러 이륙은 8 s 뒤 크롤러 법선 힘 < 0.01 W가 처음 0.1 s 이어진 구간의 첫 표본이다(`openloop_R_def2.py` 44~48행).
- **R-1 ①(병기)**: 저장 규칙 `p3a.P3a-9_min_cylinder_force.before_liftoff`와 그 재계산(1.4 F_min = 13.18 kN을 처음 넘은 뒤부터 이륙까지의 최솟값)을 함께 적는다.
- **①과 ②′가 다를 때**(차 > 0.001 kN): 판정은 ②′로 하고 차와 원인(창 시작 시각)을 적는다. 후방 피크가 13.18 kN 미만이면 ①은 골을 놓친다(창 함정). 이 경우도 ②′로 판정한다.
- **정의가 성립하지 않을 때**: $t_f \le t_c$이거나 swivel 사건이 없거나 이륙 구간을 찾지 못하면 R-1을 "정의 실패"로 적고, H-P는 **판정 안 함**이다. 다른 정의로 바꿔 판정하지 않는다.
- 글자 그대로의 정의 ②(후방 접지~이륙 최솟값, 접지 순간 인장값으로 퇴화)는 쓰지 않는다. 기록 열로만 둔다.
- Δ는 모두 **(b) − 기준**이다. 기준은 2.4절대로 정한다.
- 이륙 시각은 `openloop_R_compare.py`의 `R6.t_liftoff_after_start_s`(위 이륙 정의)다. 저장값 `P3a-2_liftoff`는 병기한다. lag_lo는 `openloop_R_tm_check.py`대로 저장 `t_liftoff_s` 시각을 쓴다(스크립트 그대로).
- 크리프 정지 first: 이륙 뒤, 네 패드 모두 1 s 창 침하 속도 < 0.1 mm/s가 처음 되는 시각 − 이륙 시각.
- 끝 자세 변화: 마지막 표본 − 들어 올림 직전 표본의 (roll, pitch)[°]. 기준 대비 차는 이 값끼리의 차다.

### 2.4 비교 기준 행

- (a)가 비트 재현(1.2절 2·3번)이면 기준은 원래 기준 행(`batch_V5-OPENLOOP-V0_20261108_123517\P3a_J1_B_V0`)이다. 두 행이 같으므로 어느 쪽이어도 값이 같다.
- (a)가 비트 불일치이면 기준은 **(a)**다. (b)와 같은 판(dce5194)이기 때문이다. 원래 기준 행 대비 값도 병기한다.
- (a)가 정체성 확인(1.2절 1번)에 실패하거나 실행되지 않으면 원래 기준 행을 기준으로 쓰고, 판 차이가 분리되지 않았다고 적는다.

### 2.5 판정 규칙 (결과 뒤 바꾸지 않음)

- **실행 정체성**(먼저 본다, 실패하면 판정 안 함): 1.2절 1번과 같은 해시, `meta.scm.soil.chrono.damping_R` = 1490000, `soil.overrides` = {damping_R: 1490000}, threads 4, pcore, rc 0, 실행 판 dce5194.
- **H-P 기각**: 다음 가운데 하나라도 해당한다.
  - R-1 ②′가 어느 다리든 기준과 1.0 kN 넘게 다르다(|Δ| > 1.0 kN).
  - 이륙이 늦어진다(Δt_lo > 0 s).
- **H-P 확인**: 2.2 표에서 "확인" 표시 항목이 모두 예측 범위 안이다.
- 그 밖이면 **부분 확인**으로 쓰고, 빠진 항목과 값을 적는다.
- "기록" 항목은 판정에 쓰지 않는다.
- 판정 순서: 정체성 → 기각 조건 → 확인 조건. 기각 조건에 걸리면 확인 조건을 다시 보지 않는다.

## 3. (b) 실행 판 결정: dce5194 worktree

- **결정: (b)도 (a)와 같은 dce5194 detached worktree에서 돌린다.** master(ca2dc7f)에서 돌리지 않는다. 볼록 껍질 훅 env(`OUTRIGGER_HULL_HOOK`)는 지정하지 않는다. dce5194에는 `hull_hook.py`가 없어서 그 값을 읽는 코드가 없다.
- 근거
  1. V5-OPENLOOP-R 3행이 dce5194에서 돌았다. (b)를 같은 판에서 돌리면 R 4행과 (a)가 모두 같은 코드다. 그러면 행 사이의 차이는 `damping_R` 하나뿐이고, 이것을 추정이 아니라 git 판으로 보증할 수 있다.
  2. master에서 `OUTRIGGER_HULL_HOOK=off`로 돌려도 코드 경로가 같아지지 않는다. dce5194..ca2dc7f 사이에 `scm_model.py` +288줄(혼합 지형 `rigid_base`, 기본 꺼짐, 훅 연동), `run_S9.py` 49줄(`OMP_WAIT_POLICY` 기본값, `placement.omp_wait_policy` 기록, `hull_hook` 기록, `build_machine`의 `rigid_base` 분기)이 바뀌었다. 정적으로는 꺼진 경로이지만, 같다고 쓰려면 줄 단위 대조나 별도 비트 재현이 필요하다.
  3. master fast로 돌리면 위 2에 훅 경로가 더해진다. 훅은 G-A(무작위·격자 400만 + 실제 패치 12,000, 비트 불일치 0)·G-B(그림자 487만 회 비교, 불일치 0)·G-C(대표 SCM npz 비트 동일)로 비트 동일이 근거가 있다. 그래도 이 행에서 직접 보증하지는 않는다.
  4. 비용 차이는 작다. dce5194(훅 없음)에서 R 행 wall은 약 1,424 s였다. fast는 G-D 기준 약 1.30배 빠르므로(약 1,100 s 추정) 차이는 약 5분이다.
- `--soil-override damping_R=…` 지원 확인(dce5194 소스, 2026-11-09): `run_S9.py` 5994행 `--soil-override`(nargs `*`), 2362행 `_soil_overrides`(`k=v` → float), 2407행 `load_soil_set(…, overrides=…)`. `scm_model.load_soil_set`은 chrono 키가 아니면 거부하고, `check_soil`은 `damping_R`이 유한한 ≥ 0 값인지만 본다. 따라서 1,490,000을 받는다. V5-OPENLOOP-R 3행의 `meta.scm.soil.chrono.damping_R`·`soil.overrides` 기록도 같은 경로가 동작함을 보인다.
- 공개: (b)는 현재 master(ca2dc7f, 훅 fast 기본)가 아니라 **전환 전 코드**로 돈다. 그래서 (b) 결과는 master 기본 실행의 결과가 아니다. master에서 같은 결과가 나온다는 것은 G-A~G-C 근거에 기대는 [추정]으로 남는다.

## 4. 한계

- (a)·(b)는 각각 실행 1회다. (a)가 비트 재현이면 같은 판·같은 스레드에서 결정론이 확인되므로 반복 산포는 0으로 본다.
- (b)의 R은 네 패드와 크롤러에 함께 들어간다(SCM 지형 하나). 크롤러만의 효과는 분리되지 않는다.
- 크롤러 τ가 µs~ms라는 terramechanics-expert 값은 크롤러 마디 압력·침하가 기록되지 않아 재계산하지 않았다. H-P의 "이륙 전 둔감" 부분은 그 결과(R-1·R-2·R-4c)로만 시험한다.
- 이륙 시각 예측은 앞 3행에서 본 선형 관계를 Δλ +0.5로 외삽한 것이다. 외삽 방향(λ > 1)은 아직 관측된 적이 없다.

## 부록 A. 실행 명세 (행 정의 아님)

- 공통
  - 인터프리터: `C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe`(Chrono-dev, 활성화 없이 직접. 앞 행과 같다)
  - worktree: dce5194 detached. 예 `git -C C:\workspace\outrigger_control worktree add --detach C:\workspace\outrigger_control\.claude\worktrees\rfu-dce5194 dce5194`. 아래 `<WT>`가 그 경로다. 경로는 메인 세션이 정하고 판정서에 적는다.
  - 출력: `--out-root`를 본 저장소의 새 배치 폴더로 준다. 예 `C:\workspace\outrigger_control\07_results\S9\batch_V5-OPENLOOP-RFU_<stamp>`. worktree 안에 쓰지 않는다.
  - env(부모 프로세스에서 설정): `OMP_WAIT_POLICY=PASSIVE`(dce5194의 `run_S9.py`는 기본값을 넣지 않으므로 **반드시** 명시), `OUTRIGGER_PLACEMENT=pcore`. `OUTRIGGER_HULL_HOOK`은 설정하지 않는다(dce5194에는 읽는 코드가 없음). `OPENBLAS_NUM_THREADS`·`MKL_NUM_THREADS`는 스크립트가 1로 둔다.
  - 풀: P코어(pcore). 두 행을 동시에 돌려도 된다(각 `--threads 4`, 앞 R 배치는 3행 동시). 예상 wall 각 약 1,430 s(dce5194 R 행 실측 1,424~1,426 s).
  - 실행 전 확인(판정 자료 아님, 결과는 공개): worktree에서 짧은 빌드 시험 1회(`--t-settle 1 --lift-s 1`)로 import·SCM 생성·`meta` 해시를 확인할 수 있다. 하면 시각과 명령을 판정서에 공개한다.
  - 실행 뒤 기록: batch 또는 실행 기록에 실행 판(`git -C <WT> rev-parse HEAD` = dce5194…), worktree 경로, env 두 값, 풀, 시작·끝 시각, rc, wall.
- (a) `P3a_J1_B_V0_rep`

```
C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe -I -X utf8 -u <WT>\04_scripts\02_chrono\run_S9.py machine --soil J1 --pad-variant dwg_rear250 --grid 0.01 --crawler-grid 0.04 --settle-dashpot zrp --lift-s 28 --level top --threads 4 --abort-on-limit --case P3a_J1_B_V0_rep --out-root <OUT>
```

- (b) `P3a_J1_B_V0_R1490k`

```
C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe -I -X utf8 -u <WT>\04_scripts\02_chrono\run_S9.py machine --soil J1 --pad-variant dwg_rear250 --grid 0.01 --crawler-grid 0.04 --settle-dashpot zrp --lift-s 28 --level top --threads 4 --abort-on-limit --soil-override damping_R=1490000 --case P3a_J1_B_V0_R1490k --out-root <OUT>
```

- 원래 argv(기준 행·V5-OPENLOOP-R 행, `batch.json`)와의 차이: 스크립트 경로가 `<WT>`로 바뀐 것, `--case`·`--out-root`(s9_batch가 실행 때 붙이는 인자, `SOURCE_ARGS_IGNORE` 대상)뿐이다. (b)는 여기에 `--soil-override damping_R=1490000`이 더해진다(V5-OPENLOOP-R 행과 값만 다름).
