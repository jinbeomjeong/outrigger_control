# 유압 모델 도식 3장 내용 명세 (2026-11-06, 개정 5 2026-11-10)

작성: hydraulics-expert. 그림 작성: graphml-expert. 이 문서는 그림에 들어갈 **내용**(노드·엣지·그룹·범례)만 정한다. 코드·다른 문서는 고치지 않았고 새 시뮬레이션도 돌리지 않았다. 수치는 아래 원본에서 옮긴 값이다.

**갱신(2026-11-06, M2 개정 3)**: M2 로드 압력 법칙이 유량 제한(`flow_limited_r3`, B 호스 미포함, 사용자 결정 2026-11-06)으로 바뀌어 그림 3의 B_M2·B_ROD·B_LCCLOSE 노드, B_M2 관련 엣지, 3.4 하네스 주석과 그림 2의 M_M2REF 노드·M_M2REF ↔ M_HARN 엣지를 고쳤다. 다시 그릴 노드·엣지 id는 각 절 표의 "개정 3" 표시 행이다.

**갱신(2026-11-08, M2 r4·r5, v5 명세 개정 4)**: M2 법칙이 `flow_limited_r5`(개정 3 유량 제한 → r4 해제 이중 계산 제거 → r5 신장 뒤 잠금 앵커 B안)로 바뀌었고, 제어기에 ③ 대체 시작값 보강 옵션(프리셋 기본 꺼짐, 2026-11-08 v5 VB에서 켬으로 채택, `final_C4G2_P3`)과 관측 전용 기록이 생겼다. 그림 3의 변경안은 **3.7절**(바꿀 id 목록)에 모았고, 3.2·3.3·3.4·3.5·3.6 표의 해당 행에 "**r4·r5**" 표시를 달았다. 그림 2는 한 건(3.7절 끝)이다. graphml-expert가 그림 2·3을 이 명세대로 고쳤다(2026-11-08, 반영됨). 그림 1은 바뀌지 않는다. 그림 파일은 graphml-expert가 고친다(이 문서는 내용만).

**개정 5(2026-11-10, hydraulics-expert, 그림 3 기호 정렬)**: 그림 3이 논문 v5 그림 H-3(`09_paper/v5/figures/figH3_hyd_blocks.*`)의 원본이 되고 v4 그림 4(`figH1_hydraulic_coupling`)를 대체하므로(사용자 결정 2026-11-10 Q-5), 그림 3의 힘·마찰·감쇠·속도 기호를 논문 2.2·2.3절 기호(= 코드 `chrono/l2b_actuator.py`의 뜻)에 맞췄다. 핵심은 힘 기호 뒤집힘의 정정이다: 개정 4까지 이 문서의 $F_{cyl}$(마찰 포함 전체 힘)·$F_p=F-f$(압력 힘)를 논문대로 **$F_a$(다리 힘, 마찰 포함, → Chrono)**와 **$F_{cyl}=F_a-f_s=p_hA_p-p_rA_{ann}$(압력 순 힘)**으로 바꾸고, $F_{cyl}$ 합산점을 새 노드로 넣었다. 또 v4 그림 4에만 있던 요소(로드측 강성 $k_r$과 LOCK/FLOOR 전환, 바깥 직렬 강성 $k_{out}$, 압력 분할식 $r_k$, 행정 진값식, 판독 힘 $\hat F$, 패드 반력 주석, 이상 유량원 주석)를 해당 노드에 옮겼고, 코드와 다르던 엣지 하나(유량 분배의 부하 압력 출처)를 고쳤다. 판단 근거와 결정 표는 **3.8절**, graphml-expert용 변경 목록은 **3.9절**이다. 3.2·3.3 표의 해당 행에 "**개정 5**" 표시를 달았다. 그림 1·2는 바뀌지 않는다. 코드·논문 원고·그림 파일은 고치지 않았다.

| 원본 | 쓴 곳 |
|---|---|
| `09_paper/v5/draft/02_modeling.md` 기호 목록, 2.2절 식 (3)과 뒤 두 문단, 2.3절 식 (H1)~(H6), 2.5절 행정 진값(개정 5) | 그림 3 기호 |
| `CLAUDE.md` 현재 기준값 표, 모델 규약(구동기 운용안 B) | 세 그림 전체 |
| `00_docs/02_hydraulic/hydraulic_circuit.md` 1·4·5·7·8절 | 그림 1 |
| `00_docs/02_hydraulic/hydraulic_coupling.md` 2~4·8·9절 | 그림 1·2·3 |
| `00_docs/02_hydraulic/l2_hydraulic_model_spec.md` 머리말·0절 | 그림 2 |
| `00_docs/02_hydraulic/s8_seal_friction_counterbalance.md` 0·2·4·11절 | 그림 1·3 |
| `00_docs/02_hydraulic/v5_hydraulic_impl_spec.md` 개정 3 (2.0~2.6, 3.1, 3.3, 5절), **개정 4**(2.3.1 r4, 2.3.2 r5, 2.8 ③·기록, 3.4) | 그림 2·3 |
| `06_analysis/03_hydraulic/coupled/v5/p3_extend_start_spec.md` 3·12절, `03_src/outrigger_sim/control/extend_start_bound.py` | 그림 3 B_P3(r4·r5 갱신) |
| `03_src/outrigger_sim/hydraulics/*.py`, `chrono/l2b_actuator.py`, `sensors/hydraulic.py`, `sensors/pressure_error.py` | 그림 3 |
| `04_scripts/04_hydraulic/coupled/harness_hydraulics.py`, `04_scripts/02_chrono/l1r_variant.py` | 그림 2·3 |
| `02_params/rexome33.yaml` `actuator`, `legs.<leg>.cylinder`, `control`, `sensors` | 수치 |

## 0. 공통 규칙

- 압력은 따로 적지 않으면 **게이지(bar g)**다. 절대압은 "abs"를 붙인다(로드측 바닥 0.1 bar abs).
- 작동유: ISO VG 46, 50 °C, ρ 860 kg/m³, ν 32 mm²/s(**가정**, `hydraulic_coupling.md` 2.2), β_eff 1.0 GPa(**가정**, 감도 0.69~1.6 GPa, YAML `actuator.oil_bulk_modulus_eff_Pa`).
- 다리 이름 FL·FR·RL·RR. 전방 = FL·FR(ø130/ø110), 후방 = RL·RR(ø110/ø90), 행정 0.70 m.
- 라벨의 "A/B"는 **다리 기준 이름**(A = 헤드, B = 로드)이다. MCV 섹션 포트 문자는 FR·RR에서 반대다(`hydraulic_circuit.md` 8절). 그림 1에 이 주석을 한 줄 넣는다.
- **가정 표시**: 라벨 끝에 `(가정)`을 붙이거나, 노드 테두리 점선 + 범례 "가정값 포함"으로 표시한다. 아래 표의 "가정" 열이 ○인 노드가 대상이다.
- **v5 옵션 표시**: 라벨 끝 배지 `[v5 옵션 · 기본 끔]` 또는 `[v5 옵션 · VB 켬]`. v5 옵션은 모두 기본 끔이다(`v5_options.py` 머리말). VB = v5 기준 구성(유량 η_v 0.85 + M2 + LC + 새 잠금 창).
- **기호(개정 5, 그림 3)**: 논문 v5 `02_modeling.md` 기호 목록을 따른다. 코드 이름과의 대응은 아래와 같다. 그림 안에서 이 표 밖의 새 기호를 만들지 않는다.

| 그림 기호 | 뜻 | 코드(`chrono/l2b_actuator.py` 등) | 개정 4까지 이 문서 |
|---|---|---|---|
| $F_a$ | 다리 힘(실 마찰·대시포트 포함, Chrono 힘 모터에 넣는 값, 식 (1) $f_a$의 다리 성분) | `force`, `acting_force_N`(docstring의 F) | $F_{cyl}$, $F$ |
| $F_{cyl}=F_a-f_s=p_hA_p-p_rA_{ann}$ | 압력 순 힘(대시포트 몫 포함, 마찰 제외). 법칙 C 판정·유량 분배 부하 압력·압력 분할·두 센서 순 힘 진값의 입력 | `acting_pressure_force_N`, `fp_acting`, `advance(cylinder_force_N=…)` | $F_p=F-f$ |
| $f_s$, $F_s$ | 실 마찰 순간값, 크기(\|f_s\| ≤ F_s) | `sf.f`, `F_s_N` | $f$, $F_s$ |
| $c_{oil}(\dot s_{ref}-\dot s)$ | 대시포트(잠김·이동 별도 값). $\dot s_{ref}$ = 이번 훅이 정한 전달 속도 | `c * (u - ds)`, `u = reference.u_applied_m_s` | $c(u-\dot s)$ |
| $G$ | 실 마찰 경로의 유압유 기둥 힘(헤드 ∥ 로드측 상태 기계) | `oil.oil_force_N` | (없음) |
| $s$, $s_{ref}$, $s_p$ | 링크 변위, 지령 행정, 피스톤 위치 | `GetMotorPos()`, `s_ref_m`, `sf.s_p` | 같음 |
| $k_h=\beta_{eff}A_p/(L_{0h}+s_{ref})$ | 헤드 기둥 강성(**$s_{ref}$ 기준**) | `axial_stiffness_N_m(s_ref)`, `force_law` docstring | $L_{0h}+s$ |
| $k_r=\beta_{eff}A_{ann}/(s_{max}-s_{ref}+L_{0r})$ | 잠김 때 더해지는 로드측 강성($s_{lock}$에서 고정) | `l2b_rod_side.py` 머리말 | 툴팁에만 |
| $k_{out}=k_{rod}\oplus k_{frame}\,[\oplus k_{ct}]$ | 기름 밖 직렬 강성 | `stroke_true_m` flex | B_HEAD 툴팁에만 |
| $u_{c,i}$ → $u_{v,i}$ → $u_i$ → $v_i$ | C2 반환 명령 → 스풀 스텝 평균 → 요청 속도(LC·M1c 뒤) → 전달 속도(유량 분배 뒤) | 논문 식 (H1)·(H3) | $u_i$, $u_v$, $u$, $v_i$ |
| $\hat F_i$ | 제어기의 압력 판독 순 힘 | `control/two_pressure.py` | "순 힘 $F_i$" |
| $\hat p=p_r+\Delta w$ | **M2 보상 압력만**(식 (H4)) | `compensated_rod_pressure_Pa` | 같음 |
| (기호 없음, "상계") | ③ 대체 시작값 상계. 그림에서 $\hat p$를 쓰지 않는다(M2의 $\hat p$와 충돌) | `extend_start_bound` | $\hat p$ |
| "판독 $p_h$, $p_r$" | 압력 센서 출력(논문 식 (5)의 $p_m$). 그림에서 새 기호($\tilde p$)를 만들지 않는다 | `sensors/hydraulic.py` | $\tilde p_h$, $\tilde p_r$ |

---

## 그림 1. 대상 범위 — 실제 회로 중 무엇을 넣고 뺐는가

**구도**: 왼쪽에서 오른쪽으로 실제 회로 흐름(펌프 → 입구 블록 → MCV 4섹션 → 호스 → 로크 블록 → 센서 블록 → 실린더 4개). 다리 하나(FL)만 자세히 그리고 나머지 세 다리는 "×4(FR·RL·RR 같음)" 상자로 겹쳐 그린다. 노드 색은 범위 분류(넣음/단순화/뺌)로 칠한다. 오른쪽 아래에 "잠긴 체적 경계"(로크 블록의 실린더 쪽)를 점선 상자로 둘러 호스가 그 밖에 있음을 보인다.

### 1.1 그룹

| 그룹 id | 이름 | 뜻 |
|---|---|---|
| G_SUPPLY | 공급부 | 펌프·입구 블록·파일럿 공급 |
| G_MCV | MCV 4섹션 뱅크 | 비례 스풀·보상기·LS |
| G_LINE | 배관 | 잠긴 체적 밖 |
| G_LEG | 다리(×4) | 로크 블록·센서 블록·실린더 = **잠긴 체적** |
| G_SENS | 센서 | 압력·행정 |
| G_OUT | 범위 밖 | 모델에 없는 회로 요소와 물리 |

### 1.2 노드

분류: **넣음** = 물리 거동을 식으로 넣음, **단순화** = 대체 식이나 상수로 넣음, **뺌** = 모델에 없음.

| id | 라벨(그림에 쓰는 글) | 그룹 | 분류 | 가정 | 짧은 근거(그림 각주 또는 툴팁) |
|---|---|---|---|---|---|
| N_PUMP | 고정 용량 펌프 P6<br>30 cc/rev, 60.2 L/min | G_SUPPLY | 단순화 | ○ | 유량 상한으로만 넣음. L1 공통 속도 상한 20.924 mm/s = 60.2 L/min × η_v 0.95(가정) ÷ ΣA_p. 네 다리 공유 분배는 v5 옵션(η_v 0.85) |
| N_PCHK | 펌프 출구 체크 | G_SUPPLY | 뺌 | | 역류 방지만, 레벨링 거동과 무관 |
| N_INLET | 입구 LS 보상기(언로딩)<br>대기 차압 Δp_LS 20 bar | G_SUPPLY | 단순화 | ○ | 유량 분배 모델에서 준정적 바이패스 Q_byp만(`hydraulic_coupling.md` 3.2). LS 라인 동특성 제외(사용자 결정) |
| N_RELIEF | LS 파일럿 릴리프<br>210 bar | G_SUPPLY | 단순화 | | 이동 중 힘 포화(법칙 C)로 넣음: 전방 278.7 / 후방 199.6 kN(신장). 210 bar는 행정 끝에서만 도달(제조사 설명) |
| N_PILOT | 파일럿 감압 공급<br>(필터 + 감압 밸브) | G_SUPPLY | 뺌 | | 파일럿 소모·공유는 범위 밖(사용자 결정, `hydraulic_coupling.md` 머리말) |
| N_GAUGE | M 포트 압력계 400 bar<br>(P 갤러리) | G_SUPPLY | 뺌 | | 갤러리 계기, 제어에 안 씀 |
| N_SPOOL | 비례 방향 스풀 ×4<br>τ_v 0.1 s | G_MCV | 단순화 | ○ | 다리별 속도 명령 + 1차 지연(또는 명령 램프 0.1 s). 노치·미터아웃 비대칭 미확인(Q-M1). 오버랩 2 %는 v5 옵션 LC |
| N_COMP | 섹션 사전 보상기 ×4<br>Δp_c 10 bar | G_MCV | 단순화 | ○ | L1: 부하 무관 속도(이상적). v5 유량 분배: smin 법칙 + 펌프 부족 시 감속 |
| N_LS | LS 셔틀 사슬<br>(최고 부하 선택) | G_MCV | 단순화 | | 이상적 최댓값 신호 |
| N_NEUTRAL | 스풀 중립 형식<br>(A·B 차단 / A·B→T 미확정) | G_MCV | 단순화 | ○ | 미확정(Q-M1·V-6). LC는 A·B→T 전제, M1c는 VN·BL 두 가지 옵션 |
| N_PORTRV | 포트 릴리프·흡입 체크 | G_MCV | 뺌 | | 회로도에 없음(실물 확인 Q-M1) |
| N_LEVER | 수동 레버 | G_MCV | 뺌 | | 시뮬레이션 범위 밖 |
| N_HOSE | 호스 ② 3/8"<br>(잠긴 체적 밖) | G_LINE | 단순화 | ○ | 잠김 강성에서 뺌(로크 블록이 실린더 직결). M1c 옵션에서만 라인 체적 285 cm³, β_hose 0.5 GPa(가정). 압력 손실·파동 제외 |
| N_POC | 이중 파일럿 체크(로크 블록 ①)<br>중립에서 두 챔버 잠금 | G_LEG | 넣음 | ○ | 잠김 상태 기계(|u| ≤ 1×10⁻⁶ m/s면 잠금). 파일럿 비 3.5·크래킹 3 bar는 M1c 옵션만(가정). 시트 누설 0 |
| N_CB | 카운터 밸런스(옵션)<br>크래킹 330 bar, ψ 4 | G_LEG | 넣음 | ○ | `lock_valve="counterbalance"`, L2b만. 값 모두 가정(제조사 확인 U-S8-H5). 기본은 파일럿 체크 |
| N_SBLK | 센서 설치 블록 + 강관<br>(사체적) | G_LEG | 단순화 | ○ | 체적은 사체적 길이에 포함: L_0h 0.05 m(감도 0.05~0.08), L_0r 0.05 m(감도 0.02~0.1). 블록 체적 미확인(Q-M12) |
| N_HEAD | 헤드 챔버<br>A_p 1.3273 / 0.9503 ×10⁻² m² | G_LEG | 넣음 | ○ | 기름 강성 k_h = β A_p / (L_0h + s) |
| N_ROD | 로드 챔버<br>A_ann 3.770 / 3.142 ×10⁻³ m² | G_LEG | 넣음 | ○ | L1-R 상태 기계: 잠김에서만 한쪽 방향 병렬 스프링, 바닥 0.1 bar abs |
| N_SEAL | 실 마찰<br>F_s 4 kN(전방), 후방 ×0.833 | G_LEG | 넣음 | ○ | L2b만(L1 없음). Coulomb, 기름 스프링에만 병렬. 단품 시험 3.72 kN 근거 |
| N_PISTON | 피스톤 내부 누설 | G_LEG | 뺌 | | 0으로 둠(레벨링 수십 초 동안 무시). 실측 요청 ≤ 4 cm³/min @ 70 bar(U-R8-9) |
| N_CUSH | 행정 끝 쿠션 | G_LEG | 단순화 | | 별도 쿠션 없음. 끝 제동 = 명령 램프 한계 + 포화 정지 2 ms 감속 |
| N_PS | 압력 센서 ×8(WIKA A-10)<br>헤드·로드, 챔버 쪽 | G_SENS | 넣음 | | 0~400 bar g, ±4 bar, 10 Hz 순간 표본. 위치는 체크와 실린더 사이(U52, 제조사 답변) |
| N_SS | 행정 센서 ×4(실린더 내장) | G_SENS | 넣음 | ○ | 측정 끝 0.6948 m(가정, 단품 시험 값). 10 Hz |
| N_OUT_FLUID | 유온·점도 변화, 공기 혼입 | G_OUT | 뺌 | | β 일정 1.0 GPa. 공기는 β 감도로만 |
| N_OUT_HEAT | 열 수지·발열 | G_OUT | 뺌 | | 범위 밖 |
| N_OUT_WAVE | 관로 파동·압력 맥동 | G_OUT | 뺌 | | 집중 상수 모델 |
| N_OUT_LOSS | POC·호스 압력 손실,<br>압력 의존 η_v | G_OUT | 뺌 | | `hydraulic_coupling.md` 9절 한계 |
| N_OUT_CHAT | 저속 수축 POC 채터<br>(리밋 사이클 7.8~8.7 Hz) | G_OUT | 뺌 | | 실제 여부 미상(v5 명세 5절) |

### 1.3 엣지

| 출발 | 도착 | 라벨 | 선 |
|---|---|---|---|
| N_PUMP | N_INLET | P 1/2" | 실선(유압) |
| N_INLET | N_SPOOL | P 갤러리 | 실선 |
| N_INLET | N_RELIEF | LS 제한 | 점선(파일럿·신호) |
| N_PUMP | N_PILOT | 파일럿 공급 | 점선 |
| N_COMP | N_SPOOL | 보상 유량 | 실선 |
| N_SPOOL | N_LS | 부하 압력 | 점선 |
| N_LS | N_INLET | 최고 LS | 점선 |
| N_SPOOL | N_HOSE | A·B 3/8" | 실선 |
| N_HOSE | N_POC | V1·V2 | 실선 |
| N_POC | N_SBLK | C1·C2 | 실선 |
| N_SBLK | N_HEAD | 헤드 포트 | 실선 |
| N_SBLK | N_ROD | 로드 포트 | 실선 |
| N_SBLK | N_PS | p_h, p_r | 실선(계측) |
| N_HEAD | N_SS | 피스톤 위치 | 계측선 |
| N_CB | N_POC | 대체(옵션) | 점선 양방향 |
| N_SPOOL | N_PUMP | T 3/4" 리턴(p_T 2 bar, 가정) | 실선(탱크) |

### 1.4 강조 상자·주석

- 점선 상자 "잠긴 체적(체크의 실린더 쪽)": N_POC 출구, N_SBLK, N_HEAD, N_ROD, N_PS를 둘러싼다. 주석: "잠긴 뒤 다리 강성 = 실린더 안 기름 기둥 + 블록 통로. 호스는 밖".
- "4다리 공용 펌프" 주석(N_PUMP 옆): "네 다리 동시 v_max 수요 57.19 L/min = 60.2 × 0.95. η_v 0.85면 공급 51.17 L/min → 포화 시 부하 큰 쪽 다리 쌍부터 감속(사전 보상)".
- A/B 주석(N_SPOOL 옆): "그림의 A = 헤드, B = 로드(다리 기준). MCV 문자는 FR·RR에서 반대".

### 1.5 범례

| 기호 | 뜻 |
|---|---|
| 채운 초록 상자 | 넣음(식으로 모델링) |
| 채운 노랑 상자 | 단순화(대체 식·상수) |
| 회색 상자, 글자 흐리게 | 뺌(범위 밖) |
| 점선 테두리 | 가정값 포함(제조사 확인 전) |
| 실선 | 유압 유로 |
| 점선 화살표 | 파일럿·LS 신호 |
| 가는 실선 + 원 | 계측 |
| 점선 큰 상자 | 잠긴 체적 경계 |

(색은 graphml-expert가 정한다. 색각 안전을 위해 분류는 색과 함께 모서리 모양이나 아이콘으로도 구분한다.)

---

## 그림 2. 목적 — 모델별로 왜 두었고 무엇에 답하는가

**구도**: 가운데 세로로 모델 상자 6개(위에서 아래로 L1, L2b, L2 기준, 유량 연성 축소 모델, v5 하네스, M2 기준 모델 묶음). 왼쪽에 "질문·판정" 상자, 오른쪽에 "교차 검증 도구" 상자. 모델 → 질문 엣지는 "답함", 모델 ↔ 도구 엣지는 교차 검증 결과를 라벨로 붙인다. OpenModelica는 "범위 밖" 그룹에 회색 점선으로 둔다(실행하지 않았음을 보이기 위해).

### 2.1 그룹

| 그룹 id | 이름 |
|---|---|
| G_Q | 질문·판정 |
| G_MODEL | 플랜트 모델(Chrono·하네스) |
| G_REF | 기준·교차 검증 모델 |
| G_OUT | 범위 밖(실행하지 않음) |

### 2.2 노드

| id | 라벨 | 그룹 | 비고(툴팁) |
|---|---|---|---|
| M_L1 | L1(L1-R)<br>강체 위치 모터 + 집중 접촉<br>Chrono SMC, Δt 2×10⁻⁴ s | G_MODEL | 유압 = 기름·접촉 직렬 강성 하나 + 로드측 L1-R(실행 스위치, YAML 기본 `off`, `l1r_variant.py`). 실 마찰 없음. M2·M1c·LC 옵션 거부 |
| M_L2B | L2b-NSC<br>힘 법칙 다리 + 횡 부싱<br>Chrono NSC, Δt 1×10⁻⁴ s | G_MODEL | 헤드 기름 강성 직렬 법칙 + 로드측 L1-R(기본 켬) + 실 마찰 + CB 옵션. 토양 S9(SCM)도 L2b |
| M_L2 | L2 기준 모델(이력)<br>두 챔버 기름량, 한 다리<br>Python + Hopsan | G_REF | `l2_cylinder.py`, `hopsan_single_leg.py`. **옛 치수(REXOME33) 이력 고정**, L2b에 그대로 들어가지 않음 |
| M_FLOW | 유량 연성 축소 모델<br>네 다리 + 3자유도 몸체<br>numpy + Hopsan + 수계산 | G_REF | `coupled/model.py`, `coupled_four_leg.hmf`, `hand_calc.py`. 회로 대조용(과도 파형·긴 경사 이동 판정에 안 씀) |
| M_HARN | v5 하네스<br>축소 6자유도 폐루프 + v5 옵션<br>dynamics-dev, 1 ms 조각 | G_MODEL | `harness_hydraulics.py` + `harness_flow.py`, 인수 실행 1,200건(필수 72·회귀 28행 × 설정) |
| M_M2REF | M2 기준 묶음<br>Hopsan 두 챔버 · numpy · 3자유도 법칙 | G_REF | `pressure_review/{four_leg,m2_check}.py`. M2-6 정착값 기준. 개정 3: M2-13 Hopsan C2 감압 곡선(`05_tests/data/m2_13_hopsan_c2_release*`)도 이 묶음에서 옴 |
| M_CBHOP | CB 한 다리 Hopsan<br>`CbLeg.hmf` | G_REF | 릴리프 밸브 법칙 대조 |
| M_OM | OpenModelica + OpenHydraulics | G_OUT | **이 프로젝트에서 실행하지 않음**. L2 명세에서 생략(복동 실린더 회귀 `DoubleActingCylinderTestSimple1`이 OM 1.27.1에서 실패) |
| Q1 | 대량 제어기 개발·검증<br>(R8 C2, 수천 건, 강건성) | G_Q | 운용안 B의 L1 몫 |
| Q2 | 큰 경사·실 마찰·연약 지면 재판정<br>(F_s 0/2/4/8 kN, SCM) | G_Q | 운용안 B의 L2b 몫 |
| Q3 | 압력 센서 기반 접지 판정<br>두 센서 순 힘 ≥ F_min 9.415 kN | G_Q | F = p_h A_p − p_r A_ann. 압력 절대값만으로 판정하지 않음(U-S8-22) |
| Q4 | 압력 한계<br>이동 ≤ 210 bar, 잠김 ≤ 350 bar(경고 345) | G_Q | 다리별 힘: 잠김 464.6 / 332.6 kN |
| Q5 | 1스텝 지연·예측자, 판독 오차 기구<br>(L2b 힘 법칙 설계 근거) | G_Q | L2 명세 0·3.2·5절 |
| Q6 | 네 다리 펌프 공유 유량 포화<br>다리 속도 분배 | G_Q | 사전 보상, 쌍 단위 감속 |
| Q7 | v5: M2·LC·M1c·유량이<br>제어기 판정을 바꾸는가 | G_Q | 판정은 control-expert(`v5_criteria.md` 봉인) |
| Q8 | CB 옵션의 효과<br>(잠김 과압 제한) | G_Q | 제조사 계획(350 bar 초과 시) |

### 2.3 엣지 — 목적(모델 → 질문)

| 출발 | 도착 | 라벨 |
|---|---|---|
| M_L1 | Q1 | 주력(대량 실행) |
| M_L1 | Q3 | L1-R 로드 압력 진값 |
| M_L1 | Q4 | 법칙 C 판정(F_cyl − m_rod a) |
| M_L2B | Q2 | 주력(재판정) |
| M_L2B | Q3 | 헤드·로드 압력 진값, 실 마찰 반영 |
| M_L2B | Q4 | 잠김 압력 감시 |
| M_L2B | Q8 | lock_valve 옵션 |
| M_L2 | Q5 | 설계 근거(β·지연·판독 오차) |
| M_L2 | Q4 | D2 계단 최대 압력(옛 치수) |
| M_FLOW | Q6 | 정상상태 분배·포화 |
| M_HARN | Q7 | 인수 실행 1,200건 |
| M_HARN | Q6 | 폐루프 유량 포화(η_v 0.85) |
| M_HARN | Q1 | C4G2 판정 경로 공유 |

### 2.4 엣지 — 교차 검증(양방향, 라벨 = 결과)

| 출발 | 도착 | 라벨 | 원본 |
|---|---|---|---|
| M_L2 (Python) | M_L2 (Hopsan) | 9 시나리오 `허용 일치`, ω_h 6.610 Hz ↔ 6.592~6.618 Hz | L2 명세 0절 |
| M_FLOW (수계산·numpy) | M_FLOW (Hopsan) | 32건: 일치 27 · 허용 2 · 불일치 3 | `hydraulic_coupling.md` 8절 |
| M_M2REF | M_HARN | M2 개정 3: 정착값 Hopsan 2.344 · numpy 2.401 ↔ 하네스 2.475 kN(M2-6, 기준 2.43 ± 0.25) · Hopsan 감압 20 bar 도달 차 1.8 ms(M2-13) | v5 명세 3.1(개정 3) |
| M_CBHOP | M_L2B | CB 명세 모델 ↔ Hopsan 릴리프: `일치`(5 ms 계단 +4.5 %) | s8 문서 0·4.5절 |
| M_L2 | M_L2B | 법칙 이어 씀(예측자·압력 밸브 법칙), 직접 대조 없음 | L2 명세 머리말 |
| M_HARN | M_L2B | 옵션 끔 비트 동일 회귀(B-2·B-4·B-5), Chrono v5 행은 하네스 판정 뒤 결정(D-3) | v5 명세 3.2·5절 |
| M_OM | M_L2 | 생략(실행 안 함) | L2 명세 368행 |

M_L2·M_FLOW 안의 Python↔Hopsan 대조는 모델 상자 안에 두 칸(Python | Hopsan)으로 나눠 그리고 칸 사이에 양방향 화살표를 둔다.

### 2.5 범례

| 기호 | 뜻 |
|---|---|
| 굵은 실선 화살표 | 주 목적(그 모델이 주력인 질문) |
| 가는 실선 화살표 | 보조 목적 |
| 양방향 점선 | 교차 검증, 라벨에 결과 |
| 회색 점선 상자 | 실행하지 않은 경로 |
| 모델 상자 아래 작은 글씨 | 엔진·시간 간격·환경 |

---

## 그림 3. 모델링 부분 — 블록과 신호 흐름

**구도**: 폐루프 한 바퀴. 위쪽 줄 왼→오: 제어기 → 명령 경로(램프/밸브 → LC 꼬리 → M1c → 유량 포화 → 법칙 C → s_ref 적분). 오른쪽 아래로 꺾어 유압 힘 법칙(헤드 기름 강성 ∥ 로드측 상태 기계, M2·LC 닫힘이 로드측에 붙음, CB 옵션, 실 마찰) → F_a → 기계(Chrono), F_a에서 실 마찰을 뺀 압력 순 힘 F_cyl = F_a − f_s는 합산점에서 갈라져 법칙 C·유량 분배·진값으로 간다(개정 5). 아래쪽 줄 오→왼: 진값 → 센서 → 제어기. 다리 하나 기준이고, 유량 포화 블록만 네 다리를 묶는다("×4 공유" 배지). 블록 순서는 v5 명세 2.0 표의 L2b 열과 같다.

L1 경로는 별도 작은 삽화(오른쪽 위)로 둔다: "L1: s_ref → 강체 위치 모터 + 집중 접촉 강성(기름·로드·프레임·콘크리트 직렬) + L1-R(실행 스위치). 실 마찰·M2·M1c·LC 없음". **개정 5**: 끝에 "행정 진값 s_true = s_motor − F_a/k_h" 한 줄을 더한다(논문 2.5절).

### 3.1 그룹

| 그룹 id | 이름 |
|---|---|
| G_CTRL | 제어기 |
| G_CMD | 플랜트-명령 경로(밸브·유량) |
| G_HYD | 플랜트-유압(힘 법칙) |
| G_MECH | 플랜트-기계 |
| G_SENS | 센서 |
| G_OPT | v5 옵션(배지로 표시, 별도 상자 아님) |

### 3.2 노드

배지: `[기본]` = 항상 켬, `[v5 · 기본 끔]`, `[v5 · VB 켬]`, `[옵션]` = v5가 아닌 기존 옵션. 가정 열 ○는 점선 테두리.

| id | 라벨(2~3줄) | 그룹 | 핵심 식·값 1줄(툴팁 또는 상자 아래) | 원본 | 배지 | 가정 |
|---|---|---|---|---|---|---|
| B_C2 | 제어기 R8 C2<br>10 Hz, 출력 지연 d = 1 | G_CTRL | 다리별 속도 명령 $u_{c,i}$(**개정 5**, 옛 u_i), ±v_max 절단(v_max 20.924 mm/s) | `control/c2.py` `with_10hz_d1()`, YAML `actuator.max_speed_m_s` | [기본] | |
| B_RAMP | 명령 램프<br>0 → v_max 0.1 s | G_CMD | 가속 한계 0.209 m/s². 밸브 모델이 꺼진 경로(L1 기본, 토양 S9 기본) | YAML `actuator.command_ramp_s` | [기본] | ○ |
| B_VALVE | 밸브 지연 τ_v<br>0.1 s | G_CMD | u_a ← u_r + (u_a − u_r) e^(−Δt/τ_v), 스텝 평균 속도. 하네스·강체 S8C는 켬, 토양 S9는 `--valve-tau-s` | `actuation.py` `configure_valve`, v5 명세 2.2 | [기본](하네스·S8C) / [v5 · 기본 끔](S9) | ○ |
| B_LCCUT | LC 오버랩 꼬리 차단<br>δ_ol 2 % = 0.418 mm/s | G_CMD | 명령 0이고 \|u_v\| ≤ u_ol이면 u = 0. t_ol = t_0 + τ_v ln(max(\|u_last\|, u_ol)/u_ol) | `v5_options.LockClosureSetting`, v5 명세 2.5 | [v5 · 기본 끔] [VB 켬] | ○ |
| B_M1C | M1c 체크 개방 지연<br>VN / BL<br>(**개정 5** 논문판 라벨: "체크 밸브 열림 지연<br>(중립 환기 / A·B 차단)") | G_CMD | 라인 압력 p_A = p_T + x A_h β_h / V_line 이 파일럿 문턱(ψ 3.5, p_cr 3 bar)을 넘을 때까지 전달 속도 0. V_line 285 cm³, β_h 0.5 GPa | `hydraulics/check_open_delay.py`, v5 명세 2.4 | [v5 · 기본 끔] 참고값(단위 기준 미달) | ○ |
| B_FLOW | 펌프 유량 포화<br>×4 공유 | G_CMD | Σ Q_i + Q_byp = η_v Q_th, Q_th 60.2 L/min. Q_i = K_i √y_i, y_i = smin(Δp_c, (p_P − p_L,i) X²/(X² + K_i²)). Δp_c 10, Δp_LS 20, w 1 bar | `hydraulics/flow_share.py`, `flow_limit_run.py` | [v5 · 기본 끔] [VB 켬, η_v 0.85] | ○ |
| B_LAWC | 법칙 C 힘 포화<br>210 bar<br>(**개정 5** 논문판 라벨: "이동 중 힘 포화") | G_CMD | 판정 힘 = $F_{cyl}$(압력 순 힘, 실 마찰 제외, **개정 5**). $F_{cyl}$ ≥ 신장 278.7 / 199.6 kN, ≤ −수축 79.2 / 66.0 kN(전방 / 후방)이면 포화 정지 2 ms 감속, 행정 끝 제동 | `actuation.SpeedReference`, YAML `legs.<leg>.cylinder.max_force_*` | [기본] | |
| B_SREF | s_ref 적분<br>[0, 0.70] m | G_CMD | s_ref ← clip(s_ref + v_i Δt, 0, 0.70). 밸브가 넣은 기름 체적 / A_p. **개정 5** 상자 아래 주석: "밸브 = 이상 유량원 $Q=A_pv_i$ · 스풀 유량–압력 동특성·누설·배관 체적 생략"(유량 분배 B_FLOW를 켜면 준정적 부하 압력 결합만 들어간다) | `actuation.py`, YAML `actuator.stroke_m` | [기본] | |
| B_HEAD | 헤드 기름 강성<br>k_h = β_eff A_p/(L_0h + s_ref)<br>(**개정 5**: s → s_ref, β → β_eff; "바깥 k_out와 직렬" 문구는 B_FA로 옮김) | G_HYD | β_eff 1.0 GPa, L_0h 0.05 m. 기둥 길이는 지령 행정 s_ref에서 잰다(`force_law` docstring "oil column length is taken at s_ref"). 운용점 k_ax FL 2.59×10⁷, RL 1.95×10⁷ N/m | `chrono/l2b_actuator.py`, YAML `actuator.L2b_NSC.axial_stiffness` | [기본] | ○ |
| B_ROD | 로드측 L1-R 상태 기계<br>이동 ↔ 잠김(LOCK·FLOOR)<br>(**개정 5** 상자 안 두 줄 추가: "k_r = β_eff A_ann/(s_max − s_ref + L_0r)" · "LOCK: k_h + k_r → FLOOR(0.1 bar abs): k_h, 잠김 중 고정") | G_HYD | **개정 5**: 잠김 강성 k_1 = (k_h + k_r) ⊕ k_out, 로드 압력이 바닥에 닿으면(꺾임 dc_knee) k_2 = k_h ⊕ k_out(`l2b_rod_side.py` 머리말), k_h·k_r은 s_lock(= 잠그는 순간의 s_ref)에서 고정. 입력에 F_cyl(이동 목표 p* = max(p_bB, −F_cyl/A_ann), 잠김 p_r 분할). 잠김: F = F_lock + k_2 dc + (k_1 − k_2) min(dc, dc_knee). 잠금 \|u\| ≤ 1×10⁻⁶ m/s. p_r0 2 bar(신장 뒤) / 34.8 bar(FL 수축 뒤). 바닥 0.1 bar abs. 이동 중 1차 지연 τ 0.05 s, 신장 배압 목표 5 bar. **개정 3**: M2 켬이면 이 이동 중 추적 압력을 B_M2의 유량 제한으로 자른다(진값·판독도 그 값). **r5(M2 켬, 신장 뒤 잠금)**: p_r0 = max(min(p_tr, p_ext + max(p_tr − p*, 0)), p_floor) — 감압 안 끝난 몫을 앵커가 가짐(최대 31.8 bar), 감압 끝난 신장·매달린 다리는 2 bar 그대로. **r4**: 해제 순간 Δ = p_r0 − p_r,rel과 해제 감쇠 w를 B_M2에 넘김 | `hydraulics/l2b_rod_side.py`(앵커 :478-492, 해제 Δ :530-537), `rod_chamber.py`, YAML `actuator.rod_side.*` | [기본](L2b) / r5 앵커 [v5 · 기본 끔] [VB 켬] | ○ |
| B_M2 | M2 로드 압력 해제 이동<br>`flow_limited_r5`<br>(유량 제한 · 해제 보상 · 신장 잠금 앵커) | G_HYD | ① 이동 중 p_r^k = 1차 지연 p_lag를 밸브 유량으로 자름: 수축 승압 ≤ A_ann\|u\| Δt / C_r, 신장 감압 ≤ b_T A_h\|u\| √((p_r − p_T)/Δp_c) Δt / C_r, C_r = A_ann²(1/k_r + 1/k_h)(FL 1.80×10⁻¹² m³/Pa, B 호스 미포함). ② **r4**: 보상 압력 p̂ = p_r + Δ w(Δ = p_r0 − p_r,rel, w = e^(−(t − t_rel)/τ)), δs_ref = A_ann (p̂^(k−1) − p̂^k) / k_h — 해제 감쇠가 이미 옮기는 몫을 다시 옮기지 않음(뜬 다리 킥 2.08 → 1.02 mm). ③ **r5**: 신장 뒤 잠금 앵커는 B_ROD에서(p_tr 입력). 신장·수축 양방향, 잠김 0, u = 0이면 유량 쪽 정지. b_T 1.0, Δp_c 10 bar, p_T 2 bar, τ 0.05 s(가정) | `hydraulics/rod_release.py` `flow_limited_rod_pressure`·`RodPressureFlowLaw`·`RodReleaseShift`·`compensated_rod_pressure_Pa`(하네스·L2b 공용), v5 명세 2.3·2.3.1·2.3.2(개정 4). meta·digest `m2_law: "flow_limited_r5"`(M2 켬만, r3·r4 거부) | [v5 · 기본 끔] [VB 켬] | ○ |
| B_LCCLOSE | LC 체크 닫힘 지연<br>t_c 50 ms | G_HYD | 잠김 법칙 전환 t_lock = t_ol + t_c. t_c 동안 유량 0, 이동 법칙·이동 감쇠 유지. **개정 3**: M2 켬이면 t_c 동안 유량으로 채우는 쪽 로드 압력은 멈춤(u = 0) | `L2bRodSide(closing_delay_s)`, v5 명세 2.5 | [v5 · 기본 끔] [VB 켬] | ○ |
| B_CB | 카운터 밸런스<br>(로크 밸브 대체) | G_HYD | 잠김에서 p ≥ p_set − (ψ − 1) p_T면 Q = Q_r y 배출, s_ref 이동. p_set 330 bar, ψ 4, τ 10 ms, 60 L/min @ +20 bar | `hydraulics/counterbalance.py`, YAML `actuator.counterbalance` | [옵션] `lock_valve="counterbalance"`, 기본 끔 | ○ |
| B_SEAL | 실 마찰 f_s<br>\|f_s\| ≤ F_s, F_s 4 kN(전방), 후방 × 0.833<br>(**개정 5**: f → f_s) | G_HYD | 유압유 기둥 G와 병렬, k_out과 직렬: 피스톤 평형 k_out(s_p − s) = G(s_ref − s_p) + f_s(복귀 사상). 감도 0/2/4/8 kN. 출력 f_s는 B_FA(+, 평형식 안)와 B_FSUM(−) 두 곳으로 간다 | `hydraulics/seal_friction.py`, YAML `actuator.seal_friction` | [옵션] L2b만, YAML 기본 0, 실행이 덮어씀 | ○ |
| B_DAMP | 기름 감쇠<br>c_oil(ṡ_ref − ṡ)<br>(**개정 5**: c(u − ṡ) → c_oil(ṡ_ref − ṡ); ṡ_ref = 이번 훅의 전달 속도, 잠김·이동 별도 값) | G_HYD | 잠김 34,403.5 / 30,348.5, 이동 100,206 / 86,949 N·s/m(전방 / 후방, 잠김 다리 ζ 0.03, 이동 ζ 0.10) | `chrono/l2b_actuator.py` 머리말(dynamics 5.20.3) | [기본] | ○ |
| B_FA (**개정 5**, 옛 B_FCYL "실린더 힘 F_cyl") | 다리 힘 F_a<br>명시 1스텝 | G_HYD | 상자 안 식 두 줄: "F_a = k_out(s_p − s) + c_oil(ṡ_ref − ṡ)", "k_out = k_rod ⊕ k_frame [⊕ k_ct]". 상자 아래 작은 글씨: "마찰 없으면 F_a = k_ax(s_ref)(s_ref − s) + c_oil(ṡ_ref − ṡ), k_ax = (k_h [+ k_r]) ⊕ k_out(식 (3))". 훅에서 상태 t_n으로 F_a 계산 → `ChLinkMotorLinearForce`에 다음 스텝 적용 | `chrono/l2b_actuator.py` `force_law`, `_friction_hook`(`force = spring + c*(u - ds)`) | [기본] | |
| B_FSUM (**개정 5 새 노드**, 합산점 원) | F_cyl = F_a − f_s<br>(압력 순 힘) | G_HYD | 입력 F_a(+), f_s(−). = p_h A_p − p_r A_ann(두 센서 순 힘 진값). 실 마찰 없으면 F_cyl = F_a. 출력: 법칙 C 판정, 유량 분배 부하 압력, 압력 분할 진값, 로드측 상태 기계 | `acting_pressure_force_N`(`F - f`), `_friction_hook` `fp_acting`, 논문 2.2절 "F_cyl = F_a − f_s = p_hA_p − p_rA_ann" | [기본] | |
| B_MECH | Chrono 기계<br>다리·패드·접촉·상부체 | G_MECH | 상부체 38,400.8 kg, 이동부 106.78 / 73.16 kg, 구면 조인트, 횡 부싱, NSC 강체(μ 0.5) 또는 SCM 토양. **개정 5** 상자 안 한 줄: "패드 반력 N ≠ F_a(로드·패드 무게·관성)" | YAML `superstructure`, `legs.<leg>.moving_part`, `contact` | [기본] | ○ |
| B_TRUTH | 진값 계산<br>p_h, p_r, 행정<br>(별도 압력 상태 없음, 대수 분할) | G_SENS | **개정 5** 상자 안 식(v4 그림 4에서 옮김): "잠김 p_r = max(p_floor, p_r0 − r_k(F_cyl − F_lock)/A_ann), r_k = k_r/(k_h + k_r)"; "이동 중 p_r = 추적 압력(τ_r 0.05 s, M2 켬이면 식 (H5))"; "p_h = (F_cyl + p_r A_ann)/A_p"(바닥 분할: 잠김 0.1 bar abs, 이동 중 헤드 바닥 2 bar); "행정 진값 s_true = s + F_a/k_out(실 마찰 경로: s_p)". L1 삽화 쪽: s_true = s_motor − F_a/k_h(논문 2.5절) | `l2b_actuator.split_pressures`, `CLAUDE.md` 모델 규약 | [기본] | ○ |
| B_PSENS | 압력 센서 ×8<br>WIKA A-10, 10 Hz | G_SENS | 0~400 bar g, normal 등급 ±4 bar 절단, 4~20 mA 포화(−5 / 412.5 bar), 분해능 0.025 bar, 순간 표본 | `sensors/hydraulic.py`, `sensors/pressure_error.py` | [기본] | |
| B_SSENS | 행정 센서 ×4<br>10 Hz | G_SENS | 측정 끝 0.6948 m, FAULT 0.6938 m | YAML `sensors.stroke` | [기본] | ○ |
| B_IMU | IMU<br>100 Hz | G_SENS | 자세(roll·pitch) 입력. 유압 밖, 루프 완결용으로만 표시 | `CLAUDE.md` 센서·주기 | [기본] | |
| B_EST | 압력 신호 처리(제어기 안)<br>영점 교정 · 순 힘 · 잠금 창 | G_CTRL | 판독 순 힘 F̂ = p_h A_p − p_r A_ann(판독값, **개정 5**: F → F̂) ≥ F_min 9.415 kN, 350 bar 판정. 잠금 창 W = τ_v ln(·) + t_c + T(새 창은 v5 옵션) | YAML `control.F_min_cylinder_N`, `control/two_pressure.py`, v5 명세 2.6 | [기본] / 새 창 [v5 · 기본 끔] [VB 켬] | |
| B_P3 (**r4·r5 새 노드**) | ③ 대체 시작값 상계<br>(제어기 안, 기본 꺼짐) | G_CTRL | 플랜트와 같은 함수 `flow_limited_rod_pressure`를 보수 입력(β 0.69 GPa, L_0h 0.08, L_0r 0.10 m, B 호스 ×1.40, κ_x 0.8)으로 1 ms 소단계 실행 → 상계. 신장 뒤 잠금 시작값·신장 이동 추정 = max(13 bar, 상계 + 0.5 bar). 재신장 전 상계 ← max(상계, ④)(revision 4). **개정 5**: 그림에서 이 상계에 p̂를 쓰지 않는다(M2 보상 압력 p̂ = p_r + Δw와 같은 그림에서 충돌; impl spec 2.8의 p̂와 같은 양). 로드 센서 고장 다리의 대체 추정에만 쓰임 | `control/extend_start_bound.py`, `two_pressure.py` `extend_start_rule`, v5 명세 2.8, `p3_extend_start_spec.md` 3·12절 | [옵션 · VB에서 켬] `extend_start_rule="tracked_bound"`(revision 4, 프리셋·클래스 기본 꺼짐, v5 VB에서 켬 — 2026-11-08 채택, `final_C4G2_P3`) | ○ |

### 3.3 엣지

| 출발 | 도착 | 라벨(신호, 단위) |
|---|---|---|
| B_C2 | B_RAMP | u_c,i [mm/s] (밸브 끔 경로) (**개정 5**: u_i → u_c,i) |
| B_C2 | B_VALVE | u_c,i [mm/s] (밸브 켬 경로) (**개정 5**) |
| B_RAMP | B_FLOW | u_r (램프 경로는 LC·M1c를 거부하므로 건너뜀, v5 명세 2.4·2.5) |
| B_VALVE | B_LCCUT | u_v,i(스풀 스텝 평균) (**개정 5**: 첨자) |
| B_LCCUT | B_M1C | u_i(꼬리 0) (**개정 5**: u → u_i) |
| B_M1C | B_FLOW | 요청 속도 u_i |
| B_FLOW | B_LAWC | 전달 속도 v_i ≤ u_i |
| B_LAWC | B_SREF | 포화 뒤 속도 |
| B_SREF | B_HEAD | s_ref [m] |
| B_SREF | B_ROD | c = s_ref − s |
| B_HEAD | B_FA | 헤드 기둥 몫(G) (**개정 5**: 도착 B_FCYL → B_FA) |
| B_ROD | B_FA | 로드측 몫(잠김 스프링, G) (**개정 5**) |
| B_M2 | B_SREF | δs_ref(다음 스텝) |
| B_ROD | B_M2 | p*, p_r^(k−1), k_r·k_h(이동 중, 개정 3); **r4**: 해제 순간 Δ = p_r0 − p_r,rel, 해제 감쇠 w |
| B_LAWC | B_M2 | 전달 속도 ṡ_ref(유량 제한 입력, 개정 3; **개정 5**: u → ṡ_ref) — 점선 |
| B_M2 | B_ROD | 유량 제한된 p_r^k(L2b 추적 압력 대체, M2 켬, 개정 3) — 점선. **r5**: 잠금 훅 직전 p_tr → 신장 뒤 잠금 앵커 p_r0 |
| B_C2 | B_P3 | **r4·r5 새 엣지**: 작용 명령 u(직전 주기 출력) — 점선(옵션) |
| B_SSENS | B_P3 | **r4·r5 새 엣지**: 행정 판독(C_r(s), 끝 여유) — 점선 |
| B_PSENS | B_P3 | **r4·r5 새 엣지**: 헤드 판독(≥ 200 bar 포화 정지 판정) — 점선 |
| B_P3 | B_EST | **r4·r5 새 엣지**: ③ 시작값 max(13 bar, 상계 + 0.5 bar)(대체 다리만, 옵션 켬) — 점선 (**개정 5**: p̂ + δ_m → 상계 + 0.5 bar) |
| B_LCCLOSE | B_ROD | 잠금 시각 t_ol + t_c |
| B_LCCUT | B_LCCLOSE | t_ol |
| B_CB | B_SREF | 배출 체적 / A_p(옵션) |
| B_CB | B_ROD | 이동 중 로드측 목표 대체(옵션) |
| B_SEAL | B_FA | f_s(기름 기둥 G와 병렬, k_out과 직렬) (**개정 5**: f → f_s, 도착 B_FA) |
| B_SEAL | B_FSUM | − f_s (**개정 5 새 엣지**, 합산점 − 표시) |
| B_DAMP | B_FA | c_oil(ṡ_ref − ṡ) (**개정 5**) |
| B_FA | B_MECH | F_a [kN] (**개정 5**: F_cyl → F_a. 그림에서 생략하지 않는다) |
| B_FA | B_FSUM | + F_a (**개정 5 새 엣지**) |
| B_MECH | B_FA | s, ṡ(링크 변위) (**개정 5**: 도착 B_HEAD → B_FA. c = s_ref − s는 B_SREF → B_ROD 엣지 그대로) |
| B_MECH | B_SEAL | s(피스톤 평형 입력) |
| B_FSUM | B_LAWC | F_cyl(판정 힘, 다음 스텝 포화) (**개정 5**: 출발 B_FCYL → B_FSUM, 라벨 "판정 힘" → "F_cyl") |
| B_FSUM | B_TRUTH | F_cyl (**개정 5**: 옛 "F_p = F − f") |
| B_FSUM | B_ROD | F_cyl(이동 목표 p*·잠김 p_r 분할 입력) — 가는 실선 (**개정 5 새 엣지**; 코드 `spring_force_N(..., fp_acting)`) |
| B_ROD | B_TRUTH | p_r 진값 |
| B_TRUTH | B_PSENS | p_h, p_r [bar g] |
| B_TRUTH | B_SSENS | 행정 진값 s_true [m] |
| B_MECH | B_IMU | 데크 자세 |
| B_PSENS | B_EST | 판독 p_h, p_r 10 Hz (**개정 5**: p̃ 기호 쓰지 않음) |
| B_SSENS | B_C2 | 행정 10 Hz |
| B_IMU | B_C2 | 자세 100 Hz |
| B_EST | B_C2 | F̂_i(판독 순 힘), 접지·F_min (**개정 5**: "순 힘 F_i" → "F̂_i") |
| B_FSUM | B_FLOW | F_cyl(직전 스텝) → 부하 압력 p_L,i — 점선 (**개정 5**: 출발 B_ROD → B_FSUM) |

B_FSUM → B_FLOW 엣지는 유량 분배가 다리 부하 압력을 직전 스텝의 F_cyl에서 만든다는 뜻이고 점선으로 그린다(**개정 5 정정**: 개정 4까지는 B_ROD에서 p_h·p_r을 읽는 것으로 적었으나, 코드는 `flow_share.PumpFlowLimiter.load_pressures_Pa(u, F_cyl)`로 신장 p_L = (F_cyl + A_ann p_r,mo)/A_p, p_r,mo = p_T + 미터아웃 강하, 수축 p_L = 파일럿 문턱(35 bar, 가정)을 쓴다. 로드측 상태 기계의 p_r은 읽지 않는다. L2b `actuation.SpeedReference.advance(cylinder_force_N=fp_acting)`, 하네스 `harness_flow.py:141` 같음). 툴팁: "신장 p_L = (F_cyl + A_ann p_r,mo)/A_p, 수축 p_L = 파일럿 문턱". B_FLOW 블록에 "×4 공유: 네 다리 p_L,i 모두 입력" 배지를 단다.

### 3.4 하네스 경로 주석(그림 아래 작은 상자)

(**개정 5**: 논문판 H-3에서는 이 절의 두 상자를 그림 주로 옮긴다(3.8 (d)-8). 원본 그림은 상자 그대로.)

"v5 하네스(축소 6자유도, 1 ms 조각)는 같은 순서다: C2 → `_lagged_step`(τ_v 0.1 s 항상 켬) → LC 꼬리 → M1c → `FlowLimitedPlant` → 내부 스텝 `_rod_force`(LC 닫힘 타이머 → M2 이동 → 법칙 C·마찰 커널). 하네스에는 로드 압력 추적이 없어 M2용 로드 압력을 하네스가 직접 푼다(`harness_hydraulics._RodPressureLag`, 개정 3: L2b와 같은 공용 함수 `flow_limited_rod_pressure`, 입력 u는 LC 닫힘 타이머가 2ε로 바꾸기 전 커널 속도). **r4·r5**: 해제 보상 Δ w(Δ = G_r(t_rel)/A_ann)와 신장 뒤 잠금 앵커(`_anchor_extension_locks`)도 L2b와 같은 식이다. 하네스는 무장 때 네 다리가 잠긴 채 시작하므로 L2b의 무장 보정이 필요 없다."

**r4·r5 추가 주석 상자(그림 아래, 3.4 상자 옆)** — 관측 기록, 되먹임 없음: "기록만(명령·플랜트 값 불변): M2 해제 기록 `m2_releases`(L2b), 앵커 계수기 `ext_lock_*`, `hydraulics_record.tension_truth`(진값 진단), `extend_bound_check`(③ 켬만), 제어기 `review_record`(늘)". 블록에 엣지로 잇지 않는다(되먹임이 있는 것처럼 보이지 않게).

### 3.5 v5 설정 표(그림 오른쪽 아래 작은 표로 넣는다)

| 설정 | 유량(η_v) | M2 | LC(δ_ol / t_c) | 새 잠금 창 | M1c |
|---|---|---|---|---|---|
| V0(기본, final_C4G2와 비트 동일) | 끔 | 끔 | 끔 | 끔 | 끔 |
| **VB(v5 기준 구성)** | 0.85 | 켬 | 2 % / 50 ms | 켬 | 끔 |
| V4·V5 등(참고) | 0.85 | 켬 | 끔 | 끔 | VN / BL |

**r4·r5 표 주석**(표 아래 한 줄, 그림에 반영됨): "M2 켬 = 법칙 flow_limited_r5. ③ 대체 시작값 보강(extend_start_rule)은 프리셋 기본 꺼짐, v5 VB에서 켬."

**③ 열을 두지 않는다**(2026-11-08 결정, hydraulics-expert): ③가 켜지는 행은 VB 하나뿐이고 나머지 행(V0, V4·V5 등)은 모두 꺼짐이다. 열을 더하면 한 칸만 의미가 있고 표 폭만 늘어난다. 그래서 그림처럼 표 주석 한 줄로 둔다. VB 행 설정 칸은 그대로 둔다(③는 주석으로 표시). 설정이 더 생겨 ③ 켬·끔 행이 섞이면 그때 열을 더한다.

### 3.6 범례

| 기호 | 뜻 |
|---|---|
| 굵은 실선 | 명령·힘의 주 경로 |
| 가는 실선 | 상태 되먹임(s, p_r) |
| 점선 | 옵션 경로(v5·CB) 또는 다리 간 공유 신호 |
| 배지 [기본] | 항상 켬 |
| 배지 [v5 · 기본 끔] | 옵션 없으면 코드 경로가 돌지 않음 |
| 배지 [VB 켬] | v5 기준 구성에서 켬 |
| 배지 [옵션 · VB에서 켬](B_P3, **r4·r5**) | 제어기 옵션(B_P3): 프리셋 기본 꺼짐 · v5 VB에서 켬 |
| 회색 점선 테두리 주석 상자(**r4·r5**) | 관측 기록, 되먹임 없음 |
| 점선 테두리 | 가정값 포함 |
| 그룹 색 | 제어기 / 플랜트-명령 / 플랜트-유압 / 플랜트-기계 / 센서 |

### 3.7 r4·r5 변경안 (2026-11-08, graphml-expert용 목록)

그림 3(`hyd_fig3_blocks.graphml` → `.svg`·`.png`)에서 바꿀 것만 모았다. 아래에 없는 노드·엣지·위치는 그대로 둔다.

| # | 종류 | id | 지금(개정 3) | 바꿀 내용 |
|---|---|---|---|---|
| 1 | 노드 라벨 | B_M2 | "M2 로드 압력 해제 이동 / 유량 제한(개정 3, `flow_limited_r3`)" | "M2 로드 압력 해제 이동 / `flow_limited_r5` / (유량 제한 · 해제 보상 · 신장 잠금 앵커)". 상자 아래 식 한 줄: "p̂ = p_r + Δ·w,  δs_ref = A_ann(p̂^(k−1) − p̂^k)/k_h". 툴팁은 3.2 B_M2 행 |
| 2 | 노드 라벨·식 | B_ROD | 개정 3 문구 | 둘째 줄 아래 식 한 줄 추가: "신장 뒤 잠금(M2 켬): p_r0 = max(min(p_tr, p_ext + (p_tr − p*)⁺), p_floor)". 배지에 `[v5 · 기본 끔][VB 켬]`(r5 앵커 몫) 추가. 툴팁은 3.2 B_ROD 행 |
| 3 | 엣지 라벨 | B_ROD → B_M2(graphml `e14`) | "p*, p_r^(k−1), k_r·k_h(이동 중, 개정 3)" | 끝에 "· 해제 Δ, w(r4)" 추가 |
| 4 | 엣지 라벨 | B_M2 → B_ROD(점선, graphml `e15`) | "유량 제한된 p_r^k(…)" | 끝에 "· 잠금 직전 p_tr → 앵커(r5)" 추가 |
| 5 | 새 노드 | B_P3 | 없음 | G_CTRL 안, B_EST 왼쪽 또는 아래. 라벨 "③ 대체 시작값 상계 / (제어기 안)". **점선 테두리**(가정 포함) + 배지 `[옵션 · VB에서 켬]`(2026-11-08 ③ v5 VB 채택 뒤 갱신, 그림 반영됨). 툴팁은 3.2 B_P3 행 |
| 6 | 새 엣지 4개(모두 점선) | B_C2 → B_P3, B_SSENS → B_P3, B_PSENS → B_P3, B_P3 → B_EST | 없음 | 라벨은 3.3 표 "r4·r5 새 엣지" 행. 기존 B_PSENS → B_EST, B_SSENS → B_C2 엣지와 겹치지 않게 |
| 7 | 주석 상자 | 3.4 하네스 주석 | 개정 3 문구 | 3.4절 새 문구로 교체(끝에 r4·r5 두 문장) |
| 8 | 새 주석 상자 | N3_REC | 없음 | 회색 점선 테두리, 3.4 상자 옆. 문구는 3.4절 "r4·r5 추가 주석 상자". 어떤 블록과도 엣지로 잇지 않는다 |
| 9 | 표 주석 | 3.5 v5 설정 표 | 없음 | 표 아래 한 줄(3.5절 "r4·r5 표 주석") |
| 10 | 범례 | 3.6 | - | 두 줄 추가: 배지 `[옵션 · VB에서 켬]`(프리셋 기본 꺼짐 · v5 VB에서 켬), 회색 점선 주석 상자 = 관측 기록 |
| 11 | 그림 제목·캡션(있으면) | - | 개정 3 표시 | "M2 = `flow_limited_r5`(2026-11-08, v5 명세 개정 4)"로 날짜·법칙 표시 갱신 |

**넣지 않는 것**: ③ 채택 경위·조건 4 면제 문구(그림에는 배지 `[옵션 · VB에서 켬]`과 표 주석만), 판정 결과 수치(3단계 등), 개정 7 T4 규칙. 그림 3은 모델 구조도라서 판정 문구를 싣지 않는다.

**그림 2(반영됨, 2026-11-08 사용자 결정 ⑦)**: 엣지 M_M2REF ↔ M_HARN(graphml `x3`) 라벨 끝에 "· r4: 뜬 다리 킥 1.0214 mm ↔ 독립 두 챔버 1.03~1.06 mm(M2-14)"를 붙였다. 근거 v5 명세 3.1 M2-14 행. M2-6 값은 r5에서도 2.4746 kN이라 지금 라벨의 "2.475 kN"은 그대로 맞다.

### 3.8 개정 5 판단 (2026-11-10, hydraulics-expert)

논문 규격판 H-3(graphml-expert, 2026-11-10)을 논문 2.2·2.3절과 대조하며 올라온 결정 사항 (a)~(d)의 판단이다. 근거는 코드(`master` b82d328)와 impl spec 개정 4다. 새 시뮬레이션은 돌리지 않았다(문서·코드 대조만).

| # | 사항 | 판단 | 근거 |
|---|---|---|---|
| (a)-1 | 힘 기호 방향 | **논문 기호로 통일**: $F_a$ = 마찰·대시포트 포함 다리 힘(→ Chrono), $F_{cyl}=F_a-f_s$ = 압력 순 힘. 이 문서 개정 4까지의 $F_{cyl}$/$F_p$는 거꾸로였다 | 코드 `acting_pressure_force_N` = `F - f`("= two-sensor net force truth p_h A_p − p_r A_ann"), 법칙 C와 유량 분배가 읽는 힘이 `fp_acting`(`_friction_hook`), `split_pressures`의 입력이 압력 순 힘. 프로젝트 전반(F_min "실린더 순 힘 p_h·A_p − p_r·A_ann", L1 판정 "F_cyl − m_rod·a")도 F_cyl = 압력 순 힘이다. 논문 기호 목록·식 (3)·2.2절 끝 문장이 이미 이 뜻이다 |
| (a)-2 | $f$ / $F_s$ | $f_s$ = 순간 마찰, $F_s$ = 크기(\|f_s\| ≤ F_s). 이 문서의 $F_s$는 원래 크기 뜻이라 그대로, $f$만 $f_s$로 | `seal_friction.py`, 논문 기호 목록 |
| (a)-3 | 대시포트 | $c_{oil}(\dot s_{ref}-\dot s)$. 코드의 `u`는 이번 훅의 전달 속도 `u_applied` = $\dot s_{ref}$이고, 그림에는 제어기 명령 $u_{c,i}$·요청 속도 $u_i$가 따로 있어 $u$를 쓰면 헷갈린다 | `force_law` `c * (u - ds)`, `hook`의 `u = self.reference.u_applied_m_s` |
| (a)-4 | $F_{cyl}=F_a-f_s$ 합산점 | **넣는다**(새 노드 B_FSUM, 원 기호). 압력 순 힘이 법칙 C·유량 분배·진값 분할·로드측 상태 기계 네 곳의 입력이라 그림에서 갈림점이 필요하다. 사용자 결정 Q-5(H-3가 v4 그림 4를 대체)로 v4 그림 4의 합산점도 H-3에 있어야 한다(논문 02_modeling.md 78행 확인 항목) | `_friction_hook`: `fp_acting` → `advance`, `spring_force_N`, `_prepare_check_delay`; `f_p = force - sf.f` → `split_pressures` |
| (a)-5 | 정정(새로 찾음) | 유량 분배의 부하 압력 $p_{L,i}$는 로드측 상태 기계의 $p_h$·$p_r$가 아니라 직전 스텝 $F_{cyl}$에서 만든다. 엣지 출발을 B_ROD → B_FSUM으로 고친다 | `flow_share.load_pressures_Pa(u, F)`, `harness_flow.py:141` |
| (a)-6 | $k_h$ 길이 기준 | $L_{0h}+s$ → $L_{0h}+s_{ref}$ | `force_law` docstring, 논문 2.2절 |
| (b) | $k_r$·LOCK/FLOOR 전환을 B_ROD에 | **넣는다**(B_ROD 상자 안 두 줄). 논문 2.2절 본문이 "잠김에서는 $k_h+k_r$, 바닥 압력에 닿으면 $k_h$만"이라고 쓰고 기호 목록에 $k_r$이 있으며, v4 그림 4에 있던 요소다. $k_r$ 식의 $s_{ref}$는 코드의 $s_{lock}$(= 잠그는 순간 $s_{ref}$)과 같다 | `l2b_rod_side.py` 머리말 |
| (c)-1 | 압력 분할식 $r_k$ | **넣는다**(B_TRUTH). 논문 2.2절 본문 식이고 그림 H-3가 이 식의 유일한 도식이 된다 | `l2b_rod_side.py` 머리말 "Sensor truth" |
| (c)-2 | 패드 반력 $N\ne F_a$ | **넣는다**(B_MECH 한 줄). $F_a$를 Chrono로 보내는 엣지 옆에서 "다리 힘 = 지면 하중"으로 오독하지 않게 한다 | v4 그림 4, 로드·패드 무게·관성 |
| (c)-3 | 행정 진값 $s_{true}=s+F_a/k_{out}$ | **넣는다**(B_TRUTH, 실 마찰 경로는 $s_p$; L1 삽화에 $s_{motor}-F_a/k_h$) | `stroke_sensor_true_m`, `stroke_true_m`, 논문 2.5절 |
| (c)-4 | 제어기 $\hat F$ | **넣는다**(B_EST → B_C2 라벨 $\hat F_i$). 지금 그림의 "순 힘 $F_i$"는 정의 없는 기호다 | 논문 기호 목록 "$\hat F$: 압력 판독 힘" |
| (c)-5 | 이상 유량원 주석 | **넣는다**(B_SREF 아래). 다만 v5에서는 유량 분배를 켜면 준정적 부하 압력 결합이 들어가므로 "스풀 유량–압력 **동특성**·누설·배관 체적 생략"으로 쓴다 | 논문 2.2절 66행, 식 (H3) |
| (c)-6 | ③ 상계 기호 | 그림에서 $\hat p$를 쓰지 않고 "상계"로 쓴다(새로 찾음). 같은 그림의 M2 상자가 $\hat p=p_r+\Delta w$(식 (H4))를 쓴다 | impl spec 2.3.1·2.8이 같은 $\hat p$를 두 양에 쓰고 있음 |
| (c)-7 | 판독 압력 기호 | $\tilde p_h$, $\tilde p_r$ 대신 "판독 $p_h$, $p_r$". 논문은 판독 압력을 식 (5)의 $p_m$으로 쓰고 $\tilde p$는 정의하지 않는다 | 논문 2.5절 |
| (d)-1 | "법칙 C 힘 포화" → "이동 중 힘 포화" | **승인** | 논문 표 H-1 "이동 중 힘 포화" |
| (d)-2 | "M1c 체크 개방 지연 VN/BL" → "체크 밸브 열림 지연 / 중립 환기 / A·B 차단" | **수정 승인**: "체크 밸브 열림 지연(중립 환기 / A·B 차단 두 회로)". 지금 문구는 세 항목처럼 읽힌다. VN = 재충전 없는 중립 환기, BL = A·B 차단(impl spec 2.4 표) | impl spec 2.4 |
| (d)-3 | ③ 표기 삭제 | **승인**(라벨 "대체 시작값 상계"). 논문 본문이 ③을 쓰지 않는다 | 논문 2.3.4 |
| (d)-4 | "(하네스·S8C)/(S9)" → "하네스·강체 다물체 / 연약 지반 다물체" | **승인** | 논문 2.2절 70행 |
| (d)-5 | 개정 표시 삭제 | **승인**(논문판 한정. 원본 graphml의 개정 표시는 원본 이력이라 그대로 둬도 된다) | |
| (d)-6 | `flow_limited_r5` → 캡션 | **승인**. 캡션 문구는 notes.md 안("M2는 v5 명세 개정 4의 법칙(유량 제한 · 해제 보상 · 신장 잠금 앵커)")대로. 논문 본문에 법칙 이름이 2.3절 주석에만 있으므로 캡션에도 코드 토큰을 쓰지 않는 쪽이 낫다 | |
| (d)-7 | 엣지 라벨 축약·생략 | **조건부 승인**. 생략 가능: $u_i$ 단위, 헤드 기둥 몫, 판독 압력 라벨. **생략 불가**(기호 정렬의 핵심): B_FA → B_MECH의 $F_a$, B_FSUM에서 나가는 $F_{cyl}$(최소 B_LAWC·B_TRUTH 두 곳), B_SEAL → B_FSUM의 $-f_s$, B_DAMP 상자 안의 $c_{oil}(\dot s_{ref}-\dot s)$(상자 안에 있으면 엣지 라벨은 생략 가능), B_EST → B_C2의 $\hat F_i$ | |
| (d)-8 | 3.4 하네스 주석·관측 기록을 그림 주로 | **승인**. notes.md 문구 확인: 하네스 문구의 "힘 포화·마찰 커널"(옛 "법칙 C·마찰 커널")과 "체크 밸브 열림 지연"은 맞다. 관측 기록 문구도 맞다(되먹임 없음, impl spec 2.8 표) | |
| (d)-9 | 3.5 v5 설정 표를 그림에서 뺌(목록에 없던 처리) | **승인**. 논문 표 H-2가 같은 내용을 더 자세히 가진다. 단 그림 주나 캡션에 "설정별 켬·끔은 표 H-2"를 한 줄 넣는다 | 논문 2.3.4 |

### 3.9 개정 5 변경안 (graphml-expert용 목록)

두 파일에 같은 내용을 적용한다: 원본 `00_docs/02_hydraulic/figures/hyd_fig3_blocks.graphml`(→ svg·png)과 논문판 `09_paper/v5/figures/figH3_hyd_blocks.graphml`(→ pdf·png, 3.8 (d)의 풀어 쓰기 적용). 아래에 없는 노드·엣지·위치는 그대로 둔다. 노드 표·엣지 표의 "**개정 5**" 행이 원본이다.

| # | 종류 | id(graphml) | 지금 | 바꿀 내용 |
|---|---|---|---|---|
| 1 | 노드 id·라벨 | B_FCYL | "실린더 힘 $F_{cyl}$ / 명시 1스텝" | id B_FA, 라벨 "다리 힘 $F_a$ / 명시 1스텝". 상자 안 식 "$F_a=k_{out}(s_p-s)+c_{oil}(\dot s_{ref}-\dot s)$", "$k_{out}=k_{rod}\oplus k_{frame}\,[\oplus k_{ct}]$". 상자 아래 작은 글씨 "마찰 없으면 식 (3): $k_{ax}=(k_h[+k_r])\oplus k_{out}$" |
| 2 | 새 노드 | B_FSUM | 없음 | 합산점 원(작게). 라벨 "$F_{cyl}=F_a-f_s$"(원 옆). 입력 + $F_a$(B_FA), − $f_s$(B_SEAL). B_FA 오른쪽 아래 또는 B_FA와 B_TRUTH 사이 |
| 3 | 엣지 | e19 B_FCYL → B_MECH | 라벨 $F_{cyl}$ [kN](논문판 생략) | 출발 B_FA, 라벨 "$F_a$" — 논문판에서도 **보인다** |
| 4 | 엣지 | e33 B_FCYL → B_LAWC | "판정 힘" | 출발 B_FSUM, 라벨 "$F_{cyl}$" |
| 5 | 엣지 | e34 B_FCYL → B_TRUTH | "$F_p=F-f$" | 출발 B_FSUM, 라벨 "$F_{cyl}$" |
| 6 | 엣지 | e31 B_ROD → B_FLOW | "부하 압력 $p_{L,i}$" | 출발 **B_FSUM**, 라벨 "$F_{cyl}$ → $p_{L,i}$", 점선 유지 |
| 7 | 새 엣지 | B_FA → B_FSUM, B_SEAL → B_FSUM, B_FSUM → B_ROD | 없음 | 라벨 "+", "$-f_s$", "$F_{cyl}$"(B_FSUM → B_ROD는 가는 실선) |
| 8 | 엣지 | e22 B_SEAL → B_FCYL, e23 B_DAMP → B_FCYL, e18 B_HEAD → B_FCYL, e41 B_ROD → B_FCYL | 라벨 $f$(기름 법칙과 병렬) 등 | 도착 B_FA. e22 라벨 "$f_s$(기름 기둥과 병렬)", e23 라벨 "$c_{oil}(\dot s_{ref}-\dot s)$"(상자 안에 식이 있으면 생략 가능) |
| 9 | 엣지 | e20 B_MECH → B_HEAD | "$s$, $\dot s$" | 도착 B_FA(레이아웃상 B_HEAD 유지가 낫다면 유지해도 된다. 뜻은 힘 법칙 입력) |
| 10 | 노드 라벨 | B_HEAD | "$k_h=\beta A_p/(L_{0h}+s)$ / 바깥 $k_{out}$와 직렬" | "$k_h=\beta_{eff}A_p/(L_{0h}+s_{ref})$". "바깥 $k_{out}$와 직렬" 줄 삭제(B_FA로 옮김) |
| 11 | 노드 라벨 | B_ROD | 개정 4 문구 | 둘째 줄 아래 두 줄 추가: "$k_r=\beta_{eff}A_{ann}/(s_{max}-s_{ref}+L_{0r})$", "LOCK $k_h+k_r$ → FLOOR $k_h$(잠김 중 고정)" |
| 12 | 노드 라벨 | B_SEAL | "실 마찰 $F_s$ / 4 kN(전방), 후방 ×0.833" | "실 마찰 $f_s$, $\lvert f_s\rvert\le F_s$ / $F_s$ 4 kN(전방), 후방 ×0.833" |
| 13 | 노드 라벨 | B_DAMP | "$c(u-\dot s)$" | "$c_{oil}(\dot s_{ref}-\dot s)$ / 잠김·이동 별도 값" |
| 14 | 노드 라벨 | B_TRUTH | "$p_h$, $p_r$, 행정" | 3.2 B_TRUTH 행의 식 네 줄(잠김 $p_r$·$r_k$, 이동 중 $p_r$, $p_h$, $s_{true}$). 폭이 모자라면 $r_k$ 식과 $s_{true}$ 식을 우선하고 나머지는 그림 주로 |
| 15 | 노드 라벨 | B_MECH | "다리·패드·접촉·상부체" | 한 줄 추가 "패드 반력 $N\ne F_a$(로드·패드 무게·관성)" |
| 16 | 노드 라벨 | B_SREF | "$s_{ref}$ 적분 / [0, 0.70] m" | 상자 아래 작은 글씨 "이상 유량원 $Q=A_pv_i$ · 스풀 유량–압력 동특성·누설·배관 체적 생략" |
| 17 | 엣지 라벨 | e38 B_EST → B_C2 | "순 힘 $F_i$, 접지·$F_{min}$" | "$\hat F_i$, 접지·$F_{min}$" |
| 18 | 엣지 라벨 | e01·e02 B_C2 → B_RAMP·B_VALVE | "$u_i$" | "$u_{c,i}$" |
| 19 | 엣지 라벨 | e04, e05, e06 | "$u_v$(스풀 스텝 평균)", "$u$(꼬리 0)", "요청 속도" | "$u_{v,i}$(스풀 스텝 평균)", "$u_i$(꼬리 0)", "요청 속도 $u_i$" |
| 20 | 엣지 라벨 | e16 B_LAWC → B_M2 | (논문판 생략) "전달 속도 $u$" | "$\dot s_{ref}$"(논문판은 생략 유지 가능, 캡션 후보 문장의 $u$를 $\dot s_{ref}$로) |
| 21 | 엣지 라벨·노드 | e29 B_P3 → B_EST, B_P3 | "max(13 bar, $\hat p+\delta_m$)" | "max(13 bar, 상계 + 0.5 bar)". 그림 어디에도 ③ 상계를 $\hat p$로 쓰지 않는다 |
| 22 | 엣지 라벨 | e27 B_PSENS → B_EST | "$\tilde p_h$, $\tilde p_r$ 10 Hz"(논문판 생략) | "판독 $p_h$, $p_r$ 10 Hz" |
| 23 | 노드 라벨 | B_M1C(논문판) | "체크 밸브 열림 지연 / 중립 환기 / A·B 차단" | "체크 밸브 열림 지연 / (중립 환기 / A·B 차단 두 회로)" |
| 24 | 노드 라벨 | note_l1(L1 삽화) | 개정 4 문구 | 끝에 "행정 진값 $s_{true}=s_{motor}-F_a/k_h$" |
| 25 | 범례 | 3.6 | - | 한 줄 추가: "원 = 합산점($F_{cyl}=F_a-f_s$)" |
| 26 | 캡션·그림 주(논문판) | notes.md | - | (i) "생략한 엣지 라벨" 문단의 "실린더 힘 → Chrono 기계는 $F_{cyl}$ [kN]", "기름 감쇠 → 실린더 힘은 $c(u-\dot s)$" 문장 삭제(그림에 $F_a$·$c_{oil}(\dot s_{ref}-\dot s)$가 보이므로), "$\tilde p_h$, $\tilde p_r$" → "판독 $p_h$, $p_r$", "전달 속도 $u$" → "$\dot s_{ref}$". (ii) 한 줄 추가 "설정별 켬·끔은 표 H-2" |

**넣지 않는 것**: 압력 분할 식의 이동 중 M2 세부(식 (H5)는 B_M2·논문 식으로 충분), 감쇠 수치, 실 마찰 감도 값(그림 주에 이미 있으면 그대로).

---

## 4. 확인하지 못한 항목

| 항목 | 상태 | 그림에 주는 영향 |
|---|---|---|
| L1 대량 실행에서 L1-R(로드측 스프링)이 기본 켬인지 | YAML `actuator.rod_side.mechanics`는 `"off"`이고, 실행 스크립트가 환경 변수로 덮어쓴다(`l1r_variant.py`: 묶음 A = 끔, 묶음 B = 켬). `CLAUDE.md`는 L1 정의에 L1-R을 포함한다. 현재 C4G2 판정 실행이 어느 묶음인지는 확인하지 않았다 | 그림 2·3의 L1 상자에 "L1-R: 실행 스위치(YAML 기본 끔)"로 적었다. 확정이 필요하면 메인 세션이 실행 meta `l1r`를 확인한다 |
| v5 하네스의 자유도 | v5 명세 3.1 표 "하네스(dynamics-expert, 6자유도)"만 근거다. 하네스 코드(`c2py_r8d1_closed_loop.py`)는 읽지 않았다 | 그림 2 M_HARN 라벨 |
| L2b 감쇠 수치 | 코드 머리말(dynamics 개정 33 값)을 옮겼다. YAML `actuator.L2b_NSC.oil_damping_*`(31,342 / 104,474 N·s/m)는 개정 33 이전 키다 | 그림 3 B_DAMP |
| 토양 S9의 밸브 경로 | 저장 토양 행은 명령 램프(밸브 끔)다. v5에서 토양 밸브 켬 기준 행은 D-3(하네스 판정 뒤)로 미정이다 | B_VALVE 배지 |
| 법칙 C 판정 힘의 L1·L2b 차이 | L1은 F_cyl − m_rod a, L2b는 힘 법칙 값 그대로(`l2b_actuator.py` 머리말) | 그림 2 엣지 라벨만 |
| 중립 형식, 노치, 포트 릴리프, 블록 체적, CB·POC 사양, τ_v·δ_ol·t_c 실측 | 제조사·U-R8-9 미답(Q-M1·M2·M4·M5·M12, V-5·V-6) | 해당 노드 모두 가정 표시 |
| MCV A/B ↔ 헤드/로드 대응의 실물 배관 | 회로도 판독만(`hydraulic_circuit.md` 8절, 확인 필요) | 그림 1 주석 |
| OpenModelica 교차 검증 | 실행 기록 없음(L2 명세에서 생략). 이번에도 돌리지 않았다 | 그림 2 M_OM은 "실행 안 함"으로 표시 |
| 그림 2의 교차 검증 결과 수치 | 문서 값을 옮겼고 다시 실행하지 않았다 | 그림 2 엣지 라벨 |
| (r4·r5) 그림 3 현재 파일 상태 | 변경 전에는 B_M2 라벨이 `flow_limited_r3`, B_ROD 툴팁이 개정 3 문구였다. graphml-expert 반영 뒤(2026-11-08) graphml 텍스트로 B_P3 배지 `[옵션 · VB에서 켬]`, B_ROD 식 `(p_tr − p*)⁺`, 3.5 주석, 범례 문구, 그림 2 M2-14 라벨을 확인했다. 렌더 그림(svg·png)은 hydraulics-expert가 보지 않았다 | 3.7절 반영 확인 |
| (r4·r5) `rod_release.py` 문서 문구(fa55755로 수정 완료. meta는 정의 해시·명령 해시·재생 대조에 들어가지 않음 확인) | 수정 전에는 모듈 docstring·`meta()`가 r5 앵커를 상한 min(p_tr, ·) 없이 적었다. 동작 코드와 L2b meta에는 원래 상한이 있었다(v5 명세 5절) | 그림은 동작 코드 식(상한 포함)을 쓴다 |
| (개정 5) 하네스 쪽 힘 기호 | 하네스 유량 분배 입력 `oil_force_N`(`harness_flow.py:141`)을 L2b의 $F_{cyl}$과 같은 압력 순 힘으로 보았다. 하네스 커널의 마찰 분리 코드는 이번에 읽지 않았다 | 그림 3은 L2b 기준이라 영향 없음. 그림 주의 하네스 문장에는 힘 기호가 없다 |
| (개정 5) 렌더 확인 | 논문판 PNG(`figH3_hyd_blocks.png`, 2026-11-10)를 눈으로 보고 3.9 목록을 만들었다. 3.9 반영 뒤 그림은 아직 보지 않았다 | 반영 뒤 hydraulics-expert 또는 메인 세션이 B_FSUM 갈림과 $F_a$ 라벨을 확인 |
