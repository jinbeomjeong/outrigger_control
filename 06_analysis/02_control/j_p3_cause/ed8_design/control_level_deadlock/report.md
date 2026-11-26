# 판 8 LEVEL 완료 교착 수정 설계 (control-expert, 2026-11-26)

## 0. 요약
| 항목 | 결과 |
|---|---|
| 근거 | G1 `R12_bottom-FR-Fs4-o0.075-RE1bF-ready`(H3 팔): 뒤 두 다리 RL·RR이 사각 명령(평균 \|u\| 0.05~0.19 mm/s)에서 P1에 잠기고, 앞 두 다리만 비대칭으로 다듬어지는 동안 $D$가 0.2~0.3 kN/s로 오른다. 비틀림 완화 완료("$\lvert D\rvert$ 비상승")와 A_ib 조건 3 (다)가 함께 막아 60 s까지 LEVEL이 끝나지 않는다(dynamics 진단 1절) |
| 같은 기전 | D-3 꼬리(LSM4 top-FR-Fs0 o0.05, VBMslow top-FL-Fs0 o0, a2에서 40 s 넘는 LEVEL), 판 5 VBK0 교착 |
| 후보 | L-1 A_ib (다) 상승 절, L-2 비틀림 완화 상승 면제, L-3 다듬기 정지(버림) |
| 오프라인(첫 작동만) | G1 H3: L-1 +20.3 s, L-2 +30.2 s 면제(→ DONE 약 +31.2 s). D-3 a2 두 줄: L-1 +20.9~21.3 s, L-2 +30.0~30.2 s. D-3 A 두 줄과 G1 A의 L-2: 작동 없음 |
| 권고 | 재실행 P8-14로 고른다(규칙은 명세 12절에 고정). 동률이면 L-2(발사 없음) |

## 1. 기전과 코드 경로(ed8-impl 7fc83456, 읽기만)
- 완료(`c2.py` 7840~7868): 자세(`is_on_target`) ∧ 간극 ∧ 비틀림 조건을 `done_hold_s` 1.0 s 유지. LEVEL에서 비틀림 조건은 엄격 $\lvert D\rvert$ < `done_twist_N` 3 kN(642행) 또는 완화(7884~7902).
- 완화(7904~7942, 상수 1593~1599): 자세·간극·LOC가 끊김 없이 settle 10 s, 창 5 s가 차고, **창 안 $\lvert D\rvert$ 비상승**(지금 ≤ 창 시작 − 0, 창 최대 ≤ 창 시작 + 600 N; 7950~7960), $\lvert D\rvert\le$ 15 kN, 하한 하중 ≥ $F_{min}$.
- A_ib 막힘(`lock_start_b.py` 1203~1221): 조건 1(같은 부호 사각 명령 25주기), 우선, 조건 2(행정 정지 < 0.1 mm), 조건 3(1232~1244, (다) = 자세·간극 미완 또는 $\lvert D\rvert$ > 15 kN일 때만 열림).
- 교착: 자세·간극은 완료(on_target 1, 간극 1), $\lvert D\rvert$ < 15 kN이라 (다)가 닫히고, $D$가 올라 완화가 성립하지 않는다. 잠긴 다리 명령은 사각이라 A(i)도 작동하지 않는다. 진단 외삽으로 +62~63 s에 15 kN을 넘어야 (다)가 열린다.

## 2. 후보
| 후보 | 규칙 | 실기 적용성 | 다른 경로 영향 | 옛 설정 불변 조건 |
|---|---|---|---|---|
| L-1 | (다)를 자세·간극 완료이고 $\lvert D\rvert\le$ 15 kN이어도 $\lvert D\rvert(t)-\lvert D\rvert(t-W_r)>x_r$이면 연다. $W_r$ 5 s, $x_r$ 0.6 kN(완화 상승 허용과 같은 값). 조건 1·2·보호·래치는 그대로 | $D$(압력 판독), 명령, 행정 판독, 완료 플래그만 씀 | A_ib 발사가 잠긴 다리를 0.4~0.85 mm 움직인다(판 7 F7-5: 한 발 ΔD ±8~12 kN). 판 7 F7-6: 사각 체류 발사의 77 %가 $\lvert D\rvert$를 키웠다 → 위험. 발사 방향은 명령 부호라 자세 다듬기가 주도하면 $\lvert D\rvert$가 커질 수 있다 | `ib_rise_open_window_s` 기본 None |
| **L-2** | 완화에서 "비상승"을 면제: 창 5 s 전체에 걸쳐 어느 다리가 A_ib 조건 1·2(같은 부호 사각, 행정 정지)를 만족하고, 창 안 상승 ≤ 2.5 kN, $\lvert D\rvert$ + 0.5 kN ≤ 15 kN. settle 10 s·자세·간극·하한 하중 ≥ $F_{min}$·LOC는 그대로. DONE은 `INFO_TWIST_UNSETTLED` | 같음 | 발사가 없다. DONE으로 LEVEL이 끝나면 다듬기 명령이 멈춰 표류도 멈춘다. 받아들이는 비틀림은 지금 완화가 이미 허용하는 범위(≤ 15 kN)다. READY의 P5·R-5 규칙이 그 뒤 하중을 지킨다 | `locked_drift_waiver` 기본 거짓 |
| L-3(버림) | 자세·간극 완료이고 잠긴 다리가 있으면 자세 PI 다듬기·적분 정지 | 같음 | 자세 루프와 적분기를 건드려 모든 LEVEL 완료 경로를 바꾼다(발자국이 가장 큼) | – |
- 2.5 kN 근거: 관측 표류 0.19~0.32 kN/s(진단·D-3) → 5 s 상승 1~1.6 kN. 2.5 kN = 0.5 kN/s 상한. 0.5 kN 여유 = 상한 속도 × `done_hold_s`.
- L-2가 "사각 정지 다리" 조건을 두는 이유: 표류가 잠긴 다리 때문이라는 관측 가능한 증거일 때만 면제한다(다른 원인의 상승은 지금처럼 막음).

## 3. 오프라인 첫 작동(`l01_out.txt`, 사건 기준 s)
| 줄 | 기록된 경과 | L-1 첫 작동 | L-2 첫 면제(DONE 예상) |
|---|---|---|---|
| G1 FR-Fs4 o0.075 H3 | LEVEL 60 s까지 미완(교착) | +20.33 s($\lvert D\rvert$ 8.03, 상승 3.35 kN, RR) | +30.23 s($\lvert D\rvert$ 6.49, 상승 0.61, RL·RR) → +31.23 |
| G1 FR-Fs4 o0.075 A | DONE 28.5 s, $t_{back}$ 40.5 s | +18.53 s(상승 6.69, RL) | 없음 |
| LSM4 top-FR-Fs0 o0.05 a2 | 사건 뒤 LEVEL 40.4 s | +21.25 s | +30.15 s → +31.15 |
| LSM4 top-FR-Fs0 o0.05 A | LEVEL 24.4 s | 없음 | 없음 |
| VBMslow top-FL-Fs0 o0 a2 | LEVEL 40.8 s | +20.90 s | +30.00 s → +31.00 |
| VBMslow top-FL-Fs0 o0 A | LEVEL 9.6 s | 없음 | 없음 |
- 첫 작동 시각까지는 정확하다(기록된 명령 그대로). 그 뒤는 궤적이 바뀌어 재생하지 않았다.
- 대리 값: 행정 정지는 플랜트 잠김(`locked`)으로, 하한 하중은 판독으로 대신했다. d08 자취에는 간극 플래그가 없어 충족으로 두었다.
- L-1은 교착이 아닌 G1 A 팔에서도 작동한다(+18.5 s, 그 줄은 원래 28.5 s에 끝남) → 발자국이 L-2보다 크다. L-2는 A 팔 세 줄에서 작동하지 않는다.
- G1 H3에서 L-2 DONE 예상 +31.2 s는 A 팔의 DONE 28.5 s → $t_{back}$ 40.5 s(차 12 s)를 적용하면 $t_{back}$ 약 43 s로 60 s 창 안이다(추정, 재실행으로 확인).

## 4. 권고
- 재실행 P8-14로 L-1·L-2 중 고른다. 사전 판단은 L-2다(발사 없음, 교착 줄에서만 작동, 첫 작동 뒤 DONE 예상이 창 안). L-1은 판 7 증거(F7-6 77 %)상 $\lvert D\rvert$를 키울 위험이 있다.

## 5. 가정과 한계
| 구분 | 내용 |
|---|---|
| 가정 | $W_r$ 5 s, $x_r$ 0.6 kN, $\Delta_{max}$ 2.5 kN, 여유 0.5 kN |
| 한계 | 첫 작동만 재생. 작동 뒤 결과(READY 시각, 하중, $\lvert D\rvert$)는 재실행으로만 |
| 한계 | 판 5 VBK0 교착 키는 블라인드 폴더(`606f8713/cdry_a1`)를 쓰지 않고 공개 자료에서 골라야 한다(6절) |
| 한계 | 실기 표류 속도·잠김 거동은 밸브 오버랩·불감대 보상에 달려 미확인(U-R8-9 시험 제안: 잠긴 하중 다리에 ±0.2 mm/s 30 s) |

## 6. 메인 세션 권고: P8-14 재실행(본 키만, held-out 조건은 돌리지 않음, 실행 dynamics-expert)
- **선택 규칙**: 명세 12절 P8-14(실행 전에 고정).
- **코드**: 판 7 C 8a2a52ce(worktree `ed7-impl`) import만, 검토 스크립트의 monkeypatch(P8-9 `p89_rerun.py`와 진단 `diag_rerun.py` 방식). worktree 수정·커밋 없음.
- **팔**: B = A + H3′(H-3을 재트리거 아닌 실행에만; P8-9′와 같은 패치), B + L-1, B + L-2.
- **키**
  - (가) 교착: G1 `R12_bottom-FR-Fs4-o0.075-RE1bF-ready`(VBM)
  - (나) D-3: LSM4 R12 top-FR-Fs0 o0.05(LSM4), VBMslow R12 top-FL-Fs0 o0.0
  - (다) 판 5 교착 계열 본 키 `<P814_VBK_KEYS>`(최대 4): 판 5 공개 자료(`ed5_design/aa_stop_606f8713/`, `j_p3_cause/ed5_j9fail_606f8713/`; 경로 정정 2026-11-26, 처음 문면은 `ed5_design/ed5_j9fail_606f8713/`로 잘못 적었다)에서 키 이름만 고른다. 플랜트는 VBKM0(③ 끔 + 로드 고장 계획). `j9_runs/606f8713/cdry_a1/`는 열지 않는다(블라인드 폴더와 그 형제 파일 포함)
  - (라) 회귀: P8-9 20키 가운데 (가)(나)와 겹치지 않는 17키(U 5, FS24, 위상 FL-Fs2 o0.025·FR-Fs2 o0.075, R15 o0.0·o0.05, R16 4, S7 e0.002, top-FR-Fs8 o0.0, top-FL-Fs8-RE1bF-level o0.0) + 완화 완료 경로 3키(VBM S4 e0.002, VBM R2 e0.001, VBM S8 e0)
- **줄**: 약 (1 + 2 + 4 + 20) × 3팔 ≈ 81 job. P8-9 실측(24 job 약 290 s, 8 워커)으로 약 16~20분. compute-scheduler-expert 배치표.
- **지표**: 게이트 전부, `t_ready_back_s`, 최종 단계, 교착 서명(T4h 행정 기록 필수, 판 7 6.2 고정 읽기), L-1 열린 주기·발사, L-2 면제 사용과 그때 $\lvert D\rvert$, J7 이름, FAULT, `commands_sha256`.
- **출력**: `06_analysis\02_control\j_p3_cause\ed8_design\control_level_deadlock\probe_8a2a52ce\`(새 폴더).

## 7. 위임 필요(python-expert): 구현 명세 Y8-10(P8-14가 고른 후보만)
- **L-2**
  1. `TwistCompletionRelaxSettings`에 `locked_drift_waiver: bool = False`, `waiver_max_rise_N: float = 2500.0`, `waiver_margin_N: float = 500.0`(클래스 기본, 옛 pickle은 꺼짐).
  2. `_is_twist_relax_ok`(c2.py 7904~7942): `_has_twist_load_stopped_rising`이 거짓일 때, 면제가 켜져 있고 (i) 창 전체 기간 동안 같은 다리가 A_ib 조건 1·2를 만족(LockStartB에서 다리별 "사각·정지 연속 주기" 조회 함수를 새로 두고 그 값 ≥ 창 주기 수), (ii) 창 최대 − 창 시작 ≤ `waiver_max_rise_N`, (iii) $\lvert D\rvert$ + `waiver_margin_N` ≤ `max_twist_N`이면 참으로 본다. 나머지 조건 순서는 그대로.
  3. 기록: 면제로 끝난 DONE의 시각·$\lvert D\rvert$·상승·다리(`twist_relax` meta에 `n_waiver_done`, `waivers` 목록).
- **L-1**
  1. `LockStartBSettings`에 `ib_rise_open_window_s: float | None = None`, `ib_rise_open_N: float = 600.0`.
  2. LockStartB가 LEVEL 주기마다 $\lvert D\rvert$ 이력을 창 길이만큼 둔다(LEVEL 밖에서 비움).
  3. `_is_completion_open`의 (다) 분기: 지금 식 ∨ (창이 차고 $\lvert D\rvert$ − 창 시작 > `ib_rise_open_N`).
  4. 기록: 상승 절로 열린 주기 수와 그 주기의 발사.
- 판 8 설정만 켠다. `R8_D1_SETTINGS`·판 7 LSB 설정 불변.
- 시험: 꺼짐 비트 동일(P8-0·P8-15), 합성 $D$ 이력에서 경계(상승 = 문턱, 창 길이 한 주기 모자람), 잠긴 다리 연속 주기가 창보다 한 주기 짧은 경우, L-2 면제 뒤 `INFO_TWIST_UNSETTLED` 한 번.

## 8. 수행한 작업
- 실행: PowerShell `conda run -n dynamics-dev python -I -B l01_first_trigger.py`(`MKL_THREADING_LAYER=TBB`).
- 출력 폴더 `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\control_level_deadlock\`: `l01_first_trigger.py` → `l01_out.txt`, `provenance.json`(열 정의).
- SHA256SUMS는 만들지 않았다. worktree는 읽기만 했다. 커밋하지 않았다.

## 9. 공개(행위 그대로)
- 블라인드 경로는 열지도 검색하지도 않았다. `j9_runs` 아래에는 접근하지 않았다.
- 연 자료: `stats_s8r/report.md`, `python_q8_checks/report.md`, `control_early_handover/probe_8a2a52ce/report.md`·`diag/report.md`, `diag/diag_case1_trace.csv`(스크립트·PowerShell `Import-Csv` 파일 지정), `dynamics_d1_d3/d08_d3_tail_twist_trace.csv`, 폴더 목록 `Get-ChildItem diag -File`(비재귀).
- 코드 Grep: worktree `03_src\outrigger_sim\control\c2.py`·`lock_start_b.py` 파일 지정, `03_src\outrigger_sim\control`(glob `*.py`) 1회.

---
**의존성 점검:** depcheck control-expert OK(이 세션 앞 단계). 이 단계는 저장 자료 분석이라 스모크·Julia 대조는 하지 않았다.

**확인 필요:** 없음(P8-9′·P8-14는 고정 규칙으로 처리, 부적격이면 그때 묻는다).

**위임 필요**
- dynamics-expert: P8-9′(6줄, 진행 중), P8-14 재실행(6절), `<P814_VBK_KEYS>` 선택(블라인드 밖 판 5 공개 자료).
- python-expert: 명세 16절 Y8-1~Y8-10, 0c 층 입력 키 존재 확인(`key_presence.py`).
- verif-protocol-auditor: S8-R 봉인 전 감사(P8-9′·P8-14가 봉인 전 본 키에서만 이루어졌는지, G′ 처리 팔이 S8-C 전에 돌지 않는지, 층·병합·문턱이 도구와 같은지).

**메인 세션 권고:** P8-14 재실행 약 81 job(16~20분). census 1043줄(약 6시간), G′ 5단계 V0 약 680회(1~1.6 h), 8단계 VBN 339회(약 0.8 h).

사용한 스킬: 없음
