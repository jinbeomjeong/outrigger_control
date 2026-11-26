# 판 8 조기 인계 수정 설계 (control-expert, 2026-11-26)

## 0. 요약
| 항목 | 결과 |
|---|---|
| 문제 | 앞 다리 bottom RE1bF에서 사건 다리의 재접근 종료(연속 3표본 $L\ge$ 14.415 kN, 10 Hz)가 3점 흔들림의 하중 창(0.18~0.45 s, 폭 0.25~0.27 s) 하나에 들어맞으면 0.40 s에 끝난다. single_leg 인계로 같은 주기에 대각 다리가 첫 들림 중(0.09~0.55 s)에 twist 재접근을 시작한다. 그러면 들림이 더 생기고 pair union이 1.8 s를 넘는다(U832). (dynamics U832 분석) |
| 코드 경로 | 종료: `c2.py` 6297~6320(`_end_finished_reapproaches`, `exit_samples` 3), 시작: 6325~6366(`_start_reapproaches`, 다른 다리 활성 중에는 낮은 표본 수를 0으로 되돌림, 프리셋 `samples` 1), 대기: 6368~6389(RT1 반대 대각·K1 재트리거 대기). 같은 주기에 종료 → 시작 순서(6288~6289) |
| 후보 | **H-3 짧은 실행의 종료 확인 연장(권고)**, H-1 대각 대기(대안), H-2 인계 표본 $L$ < 0이면 한 주기 대기(버림) |
| 오프라인 근거 | 재실행 23줄의 모든 대각 인계에서 대각 $L$ < 0(조기·늦은 인계 모두) → H-2·H-1의 인계 표본 조건은 조기 인계를 가르지 못한다. 조기 인계 실행은 시작 → 종료 0.3~0.4 s, 늦은 인계 0.9 s → H-3($T_r$ 0.5 s)만 조기 인계를 가른다 |
| 효과 | 오프라인으로는 알 수 없다(인계 뒤 궤적이 바뀜). 본 키 20개 × 2팔 짧은 재실행으로 고른다(7절, 선택 규칙은 명세 P8-9에 고정) |

## 1. 기전과 코드 경로(ed8-impl 7fc83456, 읽기만)
- 프리셋(`R8_D1_SETTINGS.lifted_reapproach`, `c2.py` 1654~1663): mode twist, `samples` 1, `single_leg` 참, `exit_samples` 3, `exit_margin_N` 5000, 재트리거 창·속도 배율, 반대 대각 창 켬, `retrigger_samples` 1.
- 주기마다 `_update_lifted_reapproach`(6269~6289)가 먼저 종료(6291~6323), 그다음 시작(6325~6366)을 본다.
- 종료: $L\ge F_{min}$ + 5 kN이면 `exit_samples_seen` +1, 아니면 0(6302~6305). 3에 닿으면 `contact`로 끝나고 `reapproach_last_end_s`·`last_sign`을 적는다(6413~6421).
- 시작: 다른 다리가 활성인 동안은 낮은 표본 수를 0으로 둔다(6337~6348). 그래서 사건 다리가 끝난 그 주기에 대각의 수가 1이 되고, `samples` 1이라 바로 시작한다. 이 시작은 재트리거 창 안이라 재트리거다(6407). 대각(FR↔RL, FL↔RR)은 비틀림 부호가 같으므로 반대 대각 창(RT1, 6345~6351)은 걸리지 않는다.
- 재실행(dynamics u11) VBM bottom-FR-Fs0 o0.0: FR 0.2·0.3·0.4 s 표본 47·212·113 kN → 0.4 s 종료, 같은 주기 RL 시작($L$ −2.52 kN). 0.5 s에 FR 다시 들림(−2.85 kN). RL 실행은 2.5 s에 끝난다.

## 2. 후보
| 후보 | 규칙 | 실기 적용성 | 다른 재접근 경로 영향 | 옛 설정 불변 조건 |
|---|---|---|---|---|
| **H-3(권고)** | 실행이 시작 뒤 $T_r$(0.5 s) 안에서 접촉 종료를 채우려 하면 연속 표본 $N_s$ = 4를 요구한다. $T_r$ 뒤에는 3 | 하한 하중 추정 $L$·표본 수·실행 시작 시각만 쓴다. $T_r$·$N_s$는 실기 흔들림 주기(상부 1/1.78 Hz = 0.56 s, 하부 1/2.84 Hz = 0.35 s, 가정)에 맞춰 다시 정한다 | 종료가 늦어지면 재트리거 창(RT2)·반대 대각 창(RT1)이 늦게 시작한다(종료 시각에서 잼). 재트리거 판정·속도 배율·`max_duration_s`·`max_travel_m`는 그대로. B3 선 비틀림의 `HANDOVER` 종료(10393~10396)는 활성 재접근이 있으면 걸리는 규칙이라 그대로 | 새 필드 `short_run_s` 기본 None(꺼짐), 클래스 기본값으로 옛 pickle도 꺼짐. `R8_D1_SETTINGS`·기존 프리셋 불변 |
| H-1(대안) | 접촉으로 끝난 $p$의 대각 $d$는 $p$ 종료 뒤 $W_d$(0.6 s) 안에서 $d$의 $L$이 시작 수준(1.4 $F_{min}$) 이상인 표본을 한 번 본 뒤에만 시작한다. 대기 중에는 `leg_reapproach_deferred:<d>:handover`(경고 아님), 가드 경로가 작동 | $L$·표본 수만 쓴다 | 새 대기 사유를 더한다. B3 선 비틀림이 같은 다리를 대신 당기지 않도록 `_may_start_pre_twist`(10368~10380)에 같은 조건을 넣어야 한다. 늦은 인계(0.975 s)에서도 대각 $L$ < 0이라 모든 대각 인계가 바뀐다 | `diag_wait_s` 기본 None |
| H-2(버림) | 인계 표본에서 대각 $L$ < 0이면 한 주기 대기 | 같음 | 모든 대각 인계를 0.1 s 늦출 뿐 | – |
- H-2를 버린 이유: 재실행 23줄 인계 표본의 대각 $L$이 모두 < 0(−2.27~−7.27 kN, `e01_rerun_handover.csv`)이라 조기·늦은 인계를 가르지 못한다. 한 주기 뒤(0.5 s)도 대각 첫 들림(끝 0.503~0.551 s) 안이다.
- H-1의 약점: 인계 표본 조건이 모든 인계에서 참이라 늦은 인계도 늦춘다. 기록된 옛 궤적에서 대각이 착지 표본을 본 뒤(0.6 s)에도 0.7 s에 다시 낮아져 곧 시작한다(흔들림이 이어짐). 효과는 재실행으로만 알 수 있다.

## 3. 오프라인 근거
### 3.1 첫 결정(정확, `e01_rerun_handover.csv`)
| 줄(재실행) | 인계 시각 [s] | 실행 길이 [s] | 대각 $L$ [kN] | H-2 대기 | H-1 대기 | H-3 연장 |
|---|---|---|---|---|---|---|
| V0 FR-Fs4 o0.025 / FL-Fs2 o0.025 / FL-Fs2 o0.05(늦은 인계) | 0.975 / 0.975 / 0.95 | 0.90 / 0.90 / 0.90 | −5.1 / −3.7 / −3.7 | 참 | 참 | **거짓** |
| V0 FR-Fs4 o0.0·o0.05·o0.075, FL-Fs2 o0.0·o0.075(조기) | 0.40~0.45 | 0.30~0.40 | −3.7~−5.1 | 참 | 참 | **참** |
| VBM 조기 7줄(RE1bF o0.0 5, o0.075 2) | 0.40~0.425 | 0.30~0.40 | −2.52~−4.63 | 참 | 참 | 참 |
| VBM FL-Fs2 o0.025(늦은) | 0.975 | 0.90 | −3.36 | 참 | 참 | 거짓 |
| VBM·A FS24 FR-Fs8 o0.0 | 0.5 | 0.30 | −7.27 / −6.2 | 참 | 참 | 참 |
| A 조기 5줄(RE1bF o0.0) | 0.40 | 0.30 | −2.27~−4.43 | 참 | 참 | 참 |
- 실행 길이 = 사건 다리 재접근 시작 → 종료(`u11_runs.csv` `reapp_starts`·`reapp_ends`).
- 그 뒤 결정은 궤적이 바뀌어 재생하지 않았다.

### 3.2 노출(저장 줄, `e01_out.txt`·`e02_out.txt`)
| 묶음 | 줄 | 재접근 있음(상한) | 대각 인계(H-1·H-2가 바꾸는 줄) | 0.5 s 안 연속 시작(H-3 하한) | 조기 인계(≤ 0.45 s) |
|---|---|---|---|---|---|
| 판 7 G1(VBM) | 171 | 149 | 42 | 37 | 19 |
| 판 7 j9_main(VBM, LSM1~4 각) | 100 / 72 | 26~27 | 6 | 6 | 0 |
| 판 7 감도(10설정 각) | 46 | 14~23 | 6 | 6 | 0 |
| 판 7 probe D(설정 각) | 12 | 12 | 1 | 0 | 0 |
| 판 6 격자(VBL) | 192 | 183 | 63 | 59 | 18 |
- j9_main·감도의 대각 인계 6줄은 R15·R16(top FL RE1bF, FL↔RR 교대가 0.3~0.5 s 간격으로 5~7번)이다. 이 줄들은 V0도 U832에 걸리는 기준선 실패 군집으로 보인다(dynamics 3.2). H-3은 이 교대 실행도 바꾼다. 그래서 회귀 군(7절)에 넣는다.
- H-3의 정확한 노출에는 실행 종료 시각이 필요하다(기록 키 Y8-8). 위 하한은 연속 시작 간격으로 센 값이다.

## 4. 권고
- **H-3**: $T_r$ = 0.5 s, $N_s$ = 4. 원인(종료 3표본이 흔들림 반주기 하나에 들어감)을 직접 다루고, 첫 결정에서 조기 인계만 가르며(3.1), 늦은 인계(V0 짧은 갈래 U 1.27~1.29 s)는 바꾸지 않는다.
- 최종 선택은 7절 재실행과 명세 P8-9 선택 규칙으로 한다.

## 5. 기호
| 기호 | 정의 | 값 |
|---|---|---|
| $L$ | 하한 하중 추정(`_load_estimate_N(cylinder_force_lower_N)`, `c2.py` 6287) | kN |
| 종료 수준 | $F_{min}$ + `exit_margin_N` | 14.415 kN |
| 시작 수준 | `load_fraction_of_F_min` × $F_{min}$ | 13.18 kN |
| $T_r$ | H-3 짧은 실행 시간 | 0.5 s(가정) |
| $N_s$ | H-3 짧은 실행 종료 표본 수 | 4(가정) |
| $W_d$ | H-1 대각 대기 창 | 0.6 s(가정) |

## 6. 가정과 한계
| 구분 | 내용 |
|---|---|
| 가정 | $T_r$·$N_s$·$W_d$는 하네스 흔들림 수치(하중 창 0.18~0.45 s, 대각 첫 들림 끝 0.50~0.55 s)에 맞춘 값 |
| 한계 | 효과는 재실행 전 미확인. 오프라인은 첫 결정과 노출만 |
| 한계 | H-3이 top 앞 다리 RE1bF(V0 기준선 실패)·FS24·LEVEL 시점 군집에 주는 영향 미확인 → 7절 회귀 군 |
| 한계 | 실기 흔들림 주기 미확인(U-R8-9에 더할 항목) |

## 7. 메인 세션 권고: 후보 선택 짧은 재실행(본 키만, held-out 후보 조건은 돌리지 않음)
- **누가**: dynamics-expert(`dynamics_u832_o00/u10_instrumented_rerun.py`를 바탕으로 후보 패치를 monkeypatch로 넣는 검토 스크립트) 또는 python-expert(ed8-impl에 설정 필드를 구현한 뒤 `ed8_probe.py` 팔로). worktree는 고치지 않고 커밋하지 않는다.
- **팔**: A(= 판 7 C에서 (i-b) 끔, 증인 판정 켬; dynamics U8-A와 같음, 기준) / A + H-3($T_r$ 0.5, $N_s$ 4) / A + H-1($W_d$ 0.6). PSW·증인 R2는 이 선택과 독립이므로 넣지 않는다(선택 뒤 census가 전체 구성을 본다).
- **키 20개**(모두 본 키)
  - U 군(6, VBM 플랜트): R12 bottom-{FR-Fs0, FL-Fs4, FL-Fs2, FR-Fs2, FR-Fs4}-RE1bF-ready o0.0, bottom-FR-Fs8-FS24-ready o0.0
  - 위상 군(3, VBM): R12 bottom-FL-Fs2-RE1bF-ready o0.025, bottom-FR-Fs2 o0.075, bottom-FR-Fs4 o0.075(판 7 G1 줄)
  - 회귀 군(11): 판 7 j9_main VBM R15 o0.0·o0.05, R16 o0.0·o0.025·o0.05·o0.075(대각 교대), LSM4 R12 top-FR-Fs0 o0.05(D-3), VBMslow R12 top-FL-Fs0 o0.0, VBM S7 e0.002, VBM R12 top-FR-Fs8 o0.0, VBM R12 top-FL-Fs8-RE1bF-level o0.0(V0 기준선 실패 군집, 기록)
- **줄**: 20 × 3팔 = 60 job. dynamics u10 실측(25 job 약 5분, 8 워커)으로 약 12~15분. compute-scheduler-expert 배치표.
- **지표**: `event_output.gates`(U832 포함 전부), `pair_union_s`, 재접근 시작·종료, `t_ready_back_s`, 최종 단계, `commands_sha256`, J7 이름 집합, 최소 힘(사건 뒤 W), 다리별 들림 구간.
- **선택 규칙**: 명세 P8-9(실행 전에 고정, 결과를 보고 바꾸지 않음).
- **출력**: `06_analysis\02_control\j_p3_cause\ed8_design\control_early_handover\probe_<커밋 앞 8자>\`(새 폴더).

## 8. 위임 필요(python-expert): 구현 명세(Y8-7·Y8-8)
- **Y8-7 H-3**(P8-9에서 H-3이 고르면)
  1. `LiftedReapproachSettings`에 `short_run_s: float | None = None`, `short_run_exit_samples: int = 4` 추가(클래스 기본값, 옛 pickle은 꺼짐). 검증: `short_run_s`는 None 또는 > 0, `short_run_exit_samples`는 정수 ≥ `exit_samples`.
  2. `_end_finished_reapproaches`(6297~6320): 요구 수 = `exit_samples`. `short_run_s`가 None이 아니고 `reading.t_s − run.start_s ≤ short_run_s + REAPPROACH_WINDOW_TOLERANCE_S`이면 요구 수 = `short_run_exit_samples`. `exit_samples_seen ≥ 요구 수`일 때 `contact`로 끝낸다. 계수 규칙(6302~6305)은 그대로.
  3. 판 8 설정만 `short_run_s` = 0.5, `short_run_exit_samples` = 4. `R8_D1_SETTINGS`·기존 프리셋 불변.
- **Y8-7 H-1**(P8-9에서 H-1이 고르면)
  1. `diag_wait_s: float | None = None` 추가.
  2. `_start_reapproaches`: 시작하려는 다리가 마지막 `contact` 종료 다리의 대각이고 `t − reapproach_last_end_s ≤ diag_wait_s`이며 그 종료 뒤 그 다리의 $L$이 시작 수준 이상인 표본이 없었으면 대기(사건 `leg_reapproach_deferred:<leg>:handover`, 대기 구간당 한 번, 경고 아님). 착지 표본 기록은 상태 필드(종료 때 지움).
  3. `_may_start_pre_twist`에 같은 조건.
- **Y8-8 기록**(명령 불변): 실행별 `exit_required_samples`, `short_run_extended`(보통 규칙이었다면 끝났을 시각 포함), 인계 표본의 대각 $L$, 재접근 종료 시각(`reapproach_ends`), r67 출력의 다리별 들림 구간 목록.
- **시험**: (1) 꺼짐이면 옛 설정과 비트 동일(P8-0·P8-8), (2) 합성 읽기: 시작 0.1 s, 0.2·0.3·0.4 s 하중 표본 → 꺼짐 0.4 s 종료, H-3 켬이면 0.5 s 표본까지 필요·0.5 s가 낮으면 계속, (3) 시작 0.075 s, 0.975 s 종료 경우는 H-3에서도 같음, (4) $T_r$ 경계(시작 뒤 정확히 0.5 s) 동작, (5) H-1이면 대기 사건 한 번·B3가 같은 다리를 당기지 않음, (6) 하네스: U 군 한 키에서 H-3 팔 `exit_required_samples` 기록이 4.
- K1 창(Y8-1~Y8-6)은 `control_k1_window/report.md` 8절, 증인 R2(Y8-3)는 그 보고 8절과 명세 3.2를 따른다.

## 9. 수행한 작업
- 실행: PowerShell `conda run -n dynamics-dev python -I -B <스크립트>`(`MKL_THREADING_LAYER=TBB`).
- 출력 폴더 `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\control_early_handover\`

| 파일 | 내용 |
|---|---|
| `e01_handover_exposure.py` → `e01_out.txt`, `e01_exposure.csv`, `e01_rerun_handover.csv` | 저장 줄 대각 인계·조기 인계 노출, 재실행 첫 인계 결정 |
| `e02_footprint.py` → `e02_out.txt` | 후보별 노출 상한·하한 |
| `provenance.json` | 입력, 읽은 코드 줄, 열 정의 |
- `control_k1_window\`에 잠시 만든 `k10_handover_exposure.py`는 이 폴더의 `e01`로 옮기고 지웠다(출력은 만들지 않았음). `control_k1_window\provenance.json`의 k07 경로 줄을 고쳤다(Julia 스크립트를 프로젝트 폴더로 옮김).
- SHA256SUMS는 만들지 않았다(메인이 고정할 때). worktree는 읽기만 했다. 커밋하지 않았다. scratchpad `control-ed8\`은 지웠다.

## 10. 공개(행위 그대로)
- 블라인드 경로는 열지도 검색하지도 않았다. `j9_runs` 아래에는 접근하지 않았다.
- 이 작업에서 연 자료: `dynamics_u832_o00\report.md`, `u11_periods.csv`·`u11_runs.csv`(PowerShell `Select-String`·`Import-Csv`로 파일 지정), `u01_scan_ed6/ed7.csv`(스크립트), 폴더 목록 `Get-ChildItem dynamics_u832_o00 -File`(비재귀).
- 코드 Grep은 worktree `03_src\outrigger_sim\control\c2.py` 파일 지정뿐이다.

---
**의존성 점검:** depcheck control-expert OK(이번 세션 앞 단계에서 실행). 이 단계는 저장 자료 분석이라 스모크·Julia 대조는 하지 않았다.

**확인 필요**: 없음(Q8-9·Q8-10은 P8-9 재실행 규칙으로 처리. 둘 다 부적격이면 그때 묻는다). Q8-11·Q8-12는 python 확인.

**위임 필요**
- python-expert: 명세 16절 Y8-1~Y8-8(상세는 두 보고 8절), Q8-4·Q8-5·Q8-11·Q8-12 확인.
- dynamics-expert 또는 python-expert: 7절 후보 선택 재실행(검토 스크립트, 본 키만).
- stats-design-expert: 명세 14절 `<S8R_CENSUS_*>`·`<S8R_HO_*>`·`<S8R_P0_UB_MAX>`, 층별 허용 수, G′ 원천 크기.
- verif-protocol-auditor: S8-R 봉인 전 감사(P8-9 선택이 봉인 전 본 키에서만 이루어졌는지, G′ 처리 팔이 S8-C 전에 돌지 않는지, 병합·층 규칙이 도구와 같은지).

**메인 세션 권고**: 7절 재실행(60 job, 약 12~15분). census는 S8-R·C8·T8 뒤 1043줄(약 6시간, 8 worker).

사용한 스킬: 없음
