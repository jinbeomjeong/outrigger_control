# 판 8 P8-9 조기 인계 후보 선택 재실행 (dynamics-expert, 2026-11-26)

## 판정: 두 후보 모두 부적격 → P8-9 멈춤 조건. 다음 진행은 사용자가 정한다

P8-9 선택 규칙은 실행 전에 고정돼 있었고, 명세 12절 문면 그대로 적용했다. 결과를 본 뒤 규칙을 바꾸지 않았다.

| 조건 | H-3 (T_r 0.5 s, N_s 4) | H-1 (W_d 0.6 s, B3 포함) |
|---|---|---|
| (1) U 군 5키 U832 통과 | **5/5 통과** | **0/5**(5키 모두 `U832_pair_union` 실패) |
| (2) FS24 키 통과 | 통과 | 통과 |
| (3) 위상·회귀 14키에서 A 대비 새 실패 게이트 | **2**: bottom-FR-Fs4-RE1bF-ready o0.075 `end_att`, R15 o0.05 `recurrence` | **1**: R15 o0.0 `end_att` |
| (3) 새 J7 항목 | 0 | 0 |
| (3) READY 미도달(A는 도달) | **1**: bottom-FR-Fs4 o0.075(60 s 창 끝까지 LEVEL) | **1**: R15 o0.0(마지막 단계 PROBE) |
| 적격 | **아니오**(3) | **아니오**(1)(3) |
| A와 명령이 다른 키 수(참고, 동률 판정용) | 17/20 | 16/20 |

- 선택 결과는 `choice = None`이다(`p89_selection.json`).
- 해석을 바꿔 봐도 결론은 같다. H-1은 (1)에서, H-3은 (3)의 게이트·READY 항목에서 탈락했다. 두 탈락 모두 J7 읽기 방식과 무관하다.

## 사용자 결정이 필요한 것(확인 필요)
P8-9는 "둘 다 부적격이면 묻는다"로 고정돼 있다. 판단 재료로 아래 사실을 적는다.

- **H-3이 U832를 고치는 기전**
  - 사건 다리의 재접근 종료가 0.4 s에서 1.0 s로 늦어진다. 0.4 s 시점은 연속 3표본을 채웠지만 4표본이 필요했고, 0.5 s 표본이 낮아 다시 0부터 셌다.
  - 그래서 대각 다리의 재접근이 1.0 s에 시작하고 2.0~2.1 s에 끝난다.
  - pair union은 U 5키에서 1.80~2.00 s → 1.54~1.60 s로 줄었다. 한계 1.8 s 대비 여유는 0.20~0.26 s다.
  - FS24 키도 1.047 → 0.894 s로 줄었다.
- **H-3의 탈락 두 건**
  - 위상 군 bottom-FR-Fs4 o0.075(G1 줄)
    - 사건 다리 FR 재접근이 0.025 s에 시작해 1.425 s에 한 번 끝나고, RL 재접근은 생기지 않았다.
    - 그 뒤 60 s 창 끝까지 LEVEL에 머물렀다. 끝 자세는 roll −0.0077°, pitch −0.006°로 작다.
    - 그래서 `end_att` 게이트가 실패했고 READY에 돌아오지 못했다.
    - 기전은 확인하지 않았다. 이번 실행은 T4h 행정 배열을 저장하지 않아 교착 서명을 계산할 수 없다. 기존 LEVEL 완료 교착(A(i)·A_ib 문턱 경쟁, D-3)일 가능성은 정황일 뿐이다.
    - 같은 위상의 FR-Fs2 키는 H-3에서도 통과했다.
  - 회귀 군 R15 o0.05
    - `recurrence` 게이트가 새로 실패했다(`sign_changes` 1 → 2).
    - 같은 줄에서 A의 `Fmin_after_W` 실패는 사라졌다. 최소 하중 2.05 → 11.73 kN이고, 이 줄의 F_min 미만 구간 146 ms가 0이 됐다.
    - R15·R16은 V0도 U832에 걸리는 기준선 실패 군집이다(설계 보고 3.2).
- **H-1이 U832를 악화시키는 기전**
  - 대각 다리 시작은 막혔지만, 사건 다리 자신이 +0.5 s에 다시 들려 재트리거를 3~4번 한다. 예: FR 재접근 구간 0.1→0.4, 0.5→1.0, 1.1→2.0, 2.1→2.4 s.
  - 대각 다리는 2.1~2.2 s에야 시작한다.
  - 그래서 pair union이 1.99~2.12 s로 오히려 늘었다.
  - 흔들림은 몸체 모드라 다리 하나를 붙잡아 두어도 감쇠되지 않는다. 원인은 종료 확인 쪽이다.
- **선택지(참고, 결정은 사용자 몫)**
  - (가) H-3을 그대로 두고 두 탈락의 원인을 계측 재실행으로 가린다. 예: FR-Fs4 o0.075 × A/H3에서 T4h·행정을 기록해 교착 서명과 A(i)·A_ib 경쟁을 본다.
  - (나) $T_r$·$N_s$를 다시 고른다. 다만 결과를 본 뒤의 재선택이라 공개 항목과 오염 보고가 늘어난다.
  - (다) 조기 인계 수정 없이 진행한다(U832를 세면 U 5키 실패가 남음).

## 수행한 작업
- **실행 환경**
  - 코드: worktree `C:\workspace\outrigger_control\.claude\worktrees\ed7-impl`, HEAD `8a2a52ce2c07d2af11a6212a2932d2061261f156`. import만 했다.
  - 실행 전후 `git status --short` 출력이 비어 있었다(깨끗함). 커밋하지 않았다.
  - 호출: PowerShell에서 `conda run -n dynamics-dev python -I -B <파일>`.
  - `reserve.py prune` 결과 removed 0, `list` 결과 예약 0건(2026-11-26 15:42)이어서 P코어 마스크 0xFFFF로 돌렸다.
  - 워커 수는 check 5개, main 8개다. `NUMBA_CACHE_DIR`는 scratchpad `dynamics-p89\numba_cache`를 썼고 작업 끝에 그 폴더를 지웠다.
- **팔 정의**
  - A: 키의 판 7 봉인 설정(VBM, LSM4, VBMslow)에 `probe_d6_settings` {witness 참, retract_position_target 거짓}을 준 것이다. U8-A·D8-*-A와 같다.
  - H3·H1: A에 monkeypatch를 더했다.
    - H3: `_end_finished_reapproaches`를 복사한 함수에 H-3 요구 표본 수 분기를 넣었다. 분기 조건은 `t − start ≤ T_r + 1e-9`이면 4다.
    - H1: `_start_reapproaches` 감싸기로 착지 표본을 기록한다. 판정 기준은 종료 뒤(t > t_end) 대각 다리의 $L$ ≥ 1.4 $F_{min}$이다.
    - H1: `_defers_reapproach`·`_deferred_event_name`을 감싸 대기와 사건 `leg_reapproach_deferred:<leg>:handover`를 넣었다.
    - H1: `_may_start_pre_twist`를 감싸 B3 선 비틀림 시작도 같은 조건으로 막았다.
    - H1: `_end_reapproach` 감싸기로 마지막 종료(다리, 시각, contact 여부)를 기록한다.
    - 모든 팔에 기록 전용 `_begin_reapproach`·`_end_reapproach` 감싸기를 넣었다.
  - 공개: 지시는 `_end_finished_reapproaches`·`_start_reapproaches`·`_may_start_pre_twist`의 monkeypatch였다. H-1의 대기 판정과 사건 이름은 원래 대기 경로(`_defers_reapproach`·`_deferred_event_name`)에 걸어 구현했다. 이렇게 하면 "대기 구간당 사건 한 번" 규칙을 원 코드 그대로 쓴다.
- **패치 확인(단위 수준, 본 실행 전)**
  1. 합성 단위 시험 `p89_rerun.py selftest` → `selftest_out.txt` SELFTEST OK(8/8 사례). 설계 보고 8절 시험 (2)~(4)를 따랐다.
     - 시작 0.1 s에 0.2·0.3·0.4 s 높음: 0.4 s에 끝나지 않고 0.5 s에 끝난다.
     - 0.5 s가 낮으면 끝나지 않는다.
     - 시작 0.075 s, 0.975 s 종료(늦은 인계): 바뀌지 않는다.
     - 경계(시작 뒤 정확히 0.5 s)에서는 4표본이 필요하다.
     - $T_r$ 뒤 표본에서는 3표본이면 끝난다.
  2. 하네스 확인 `check`: U 키 bottom-FR-Fs0-RE1bF-ready o0.0에서 5 job, 90.8 s → `check_out.json`.
     - A `a799807b…`가 저장된 U8-A와 같았다.
     - H3n3(H-3 경로, $N_s$ 3)과 H1off(H-1 경로, $W_d$ −1 s)는 A와 해시가 같았다. 복사·감싸기 코드의 항등성을 확인했다.
     - H3에서는 사건 다리 FR의 첫 종료가 요구 표본 수 4로 처리됐다. 기록상 0.4 s에 3표본·요구 4였고, 종료는 1.0 s로 늦어졌다.
     - H1에서는 대각 RL의 handover 대기가 3번 있었다.
  3. 본 실행 60 job(20키 × 3팔)은 세 번에 나눠 돌렸다(24·24·12 job, 290·282·155 s). 오류 0, 팔 정체성 불일치 0.
     - check 실행 뒤 `p89_rerun.py`에는 나눠 돌리는 인자만 더했다. 패치 코드는 바꾸지 않았다.
     - 같은 키의 A·H3·H1 해시는 check와 본 실행에서 같았다.
- **A 팔 재현**
  - 저장된 A 줄 10개와 `commands_sha256`가 모두 같았다.
  - U8-A는 U 6키, D8-*-A는 LSM4 top-FR-Fs0 o0.05, VBMslow top-FL-Fs0 o0.0, S7 e0.002, top-FR-Fs8 o0.0이다.
- held-out 후보 조건(새 위상 0.0125 등, 새 깊이·램프·F_s)은 돌리지 않았다. 60 job 모두 설계 보고 7절 목록의 본 키다.

## 지표 표(사건 기준 상대 시각 s, 프레임 무관 스칼라)
- 표기
  - 실패 = 거짓인 `event_output.gates`
  - PU = `pair_union_s`
  - tRb = `t_ready_back_s`(사건 뒤 READY 복귀까지 걸린 시간 [s], – = 미도달)
  - 재접근은 (다리 시작→종료)
- 전체 열(J7 집합, 다리별 최소 힘, 다리별 들림 구간 `lifts`, 명령 해시, H-3 연장·H-1 대기 시각)은 `p89_metrics.csv`와 `p89_analyze_out.txt`에 있다.

| 군 | 키 | A | H3 | H1 |
|---|---|---|---|---|
| U | bottom-FR-Fs0 o0.0 | U832_pu · PU 2.004 · tRb 29.0 · FR .1→.4, RL .4→2.6 | 통과 · 1.600 · 31.4 · FR .1→1.0, RL 1.0→2.1 | U832_pu · 2.123 · 28.8 · FR 4회(.1→.4 … 2.1→2.4) |
| U | bottom-FL-Fs4 o0.0 | U832_pu · 1.801 · 23.5 | 통과 · 1.537 · 23.9 | U832_pu, end_att · 2.038 · – (PROBE) |
| U | bottom-FL-Fs2 o0.0 | U832_pu · 1.831 · 23.5 | 통과 · 1.567 · 23.7 | U832_pu · 2.090 · 23.8 |
| U | bottom-FR-Fs2 o0.0 | U832_pu · 1.861 · 29.7 | 통과 · 1.586 · 50.5 | U832_pu · 2.075 · 29.4 |
| U | bottom-FR-Fs4 o0.0 | U832_pu · 1.837 · 50.2 | 통과 · 1.559 · 36.2 | U832_pu · 1.990 · 29.5 |
| U_FS24 | bottom-FR-Fs8-FS24 o0.0 | 통과 · 1.047 · 22.0 · FR .2→.5, RL .5→1.9 | 통과 · 0.894 · 22.0 · FR .2→1.0, RL 1.0→1.6 | 통과 · 1.111 · 22.7 |
| 위상 | bottom-FL-Fs2 o0.025(늦은 인계) | 통과 · 1.477 · 23.68 | **A와 해시 같음**(8ea4eee8) | 통과 · 1.523 · 24.28 |
| 위상 | bottom-FR-Fs2 o0.075 | 통과 · 1.590 · 30.13 | 통과 · 1.309 · 30.53(RL 재접근 없음) | 통과 · 1.654 · 29.93 |
| 위상 | bottom-FR-Fs4 o0.075 | 통과 · 1.581 · 40.53 | **end_att · 1.308 · –** (마지막 단계 LEVEL) | 통과 · 1.692 · 30.03 |
| 회귀 | R15 o0.0 | Fmin_after_W, U832_pu · 2.063 · 39.8 | U832_pu · 2.066 · 39.8 | **U832_pu, end_att · 2.406 · –** (PROBE) |
| 회귀 | R15 o0.05 | Fmin_after_W, U832_pu · 2.021 · 39.75 | **U832_pu, recurrence** · 2.021 · 37.85 | U832_pu · 2.396 · 36.05 |
| 회귀 | R16 o0.0 / 0.025 / 0.05 / 0.075 | 모두 U832_pu · 1.933 / 1.909 / 1.888 / 1.929 | 모두 U832_pu · 1.933 / 1.891 / 1.873 / 1.929 | 모두 U832_pu · 2.386 / 2.316 / 2.310 / 2.301 |
| 회귀 | LSM4 top-FR-Fs0 o0.05 | 통과 · tRb 37.35 | A와 해시 같음 | A와 해시 같음 |
| 회귀 | VBMslow top-FL-Fs0 o0.0 | 통과 · 22.6 · RR 3.2→3.6 | 통과 · 22.0 · RR 3.2→3.7(해시 다름) | A와 해시 같음 |
| 회귀 | S7 e0.002 | READY(t_first_ready 78.5 s) | A와 해시 같음 | A와 해시 같음 |
| 회귀 | top-FR-Fs8 o0.0 | 통과 · 22.5 · RL 1.7→2.2 | 통과 · RL 1.7→2.3(해시 다름) | A와 해시 같음 |
| 회귀 | top-FL-Fs8-RE1bF-level o0.0 | U832_pu · 1.916 · 23.9 | U832_pu · 1.916 · 23.8 | U832_pu · 2.087 · 23.8 |

- 최종 단계는 위 표 밖의 모든 줄에서 `ready`다. 예외는 H3 FR-Fs4 o0.075(level), H1 FL-Fs4 o0.0(probe), H1 R15 o0.0(probe)이다.
- J7 집합은 세 팔이 키마다 같다.
  - 사건 줄: `WARN_D1_IMU_GYRO_MISSING`
  - VBMslow 키: `WARN_PROBE_RETRACT_NOT_OPENED` 4다리(A 팔은 증인 판정이 켜져 있어 세 팔 모두 같음)
- 사건 뒤 최소 실린더 힘(다리 최소)은 세 팔이 키마다 같다.
  - RE1bF·FS24·R15·R16 키: −1.05 kN. 들린 사건 다리의 로드측 장력 바닥이다.
  - top 키: LSM4 16.52 kN, VBMslow 13.97 kN, top-FR-Fs8 15.08 kN.
- 회귀 군 R15·R16·top-FL-Fs8-level은 A에서 이미 U832가 실패한다(기준선 실패 군집). 선택 규칙 (3)은 A 대비 새 실패만 센다.

## 근거 수식·정의
| 기호 | 정의 | 값 |
|---|---|---|
| $L$ | 하한 하중 추정 `_load_estimate_N(cylinder_force_lower_N)` | kN |
| 종료 수준 | $F_{min}$ + `exit_margin_N` | 14.415 kN |
| 시작 수준 | 1.4 $F_{min}$ | 13.18 kN |
| H-3 | 실행 시작 뒤 $t - t_{start} \le T_r + 10^{-9}$ s인 표본에서 종료 요구 연속 표본 = $N_s$, 그 밖은 `exit_samples` 3. 계수 규칙(미달이면 0으로)은 그대로 | $T_r$ 0.5 s, $N_s$ 4 |
| H-1 | 마지막 종료가 contact인 다리 $p$의 대각 $d$(FL↔RR, FR↔RL)는 $t - t_{end} \le W_d$이고 종료 뒤 $L_d$ ≥ 시작 수준 표본이 없으면 시작 대기(B3 포함) | $W_d$ 0.6 s |
| U832 통과 | `U832_pair_union`(≤ 1.8 s)과 `U832_last_touch`(≤ 3.0 s)가 모두 참 | – |
| FS24 통과 | `event_output.pass`(모든 게이트 참). G1 키 파일의 V0 짝은 `v0_pass` 참 | – |
| 새 J7 | `jp3_ed7_rules.j7_items_ed7` 꼴의 항목 집합 차(A 대비) | – |
| READY 도달 | 사건 줄은 `t_ready_back_s` 유한, S7은 `t_first_ready_s` 있음 | – |

## 가정
- $T_r$ 0.5 s, $N_s$ 4, $W_d$ 0.6 s는 명세 3.7의 가정값 그대로다.
- H-1 착지 표본은 종료 시각보다 뒤의 표본만 센다. 재접근 장부(`_start_reapproaches`)가 도는 주기에서만 본다.
- 하네스는 결정적이다(seed 없음). 같은 키의 A 해시가 check와 본 실행, 그리고 저장 줄과 같았다.

## 출력(`C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\control_early_handover\probe_8a2a52ce\`)
| 파일 | 내용 |
|---|---|
| `p89_rerun.py` | 검토 스크립트(팔, 키 20, 패치, selftest·check·main) |
| `p89_check.py` → `check_out.json` | 패치 항등성·U 키 확인 |
| `p89_analyze.py` → `p89_selection.json`, `p89_metrics.csv`, `p89_analyze_out.txt` | P8-9 규칙 적용, 60줄 지표 |
| `p89_detail.py` → `p89_detail_out.txt` | 조건 (3) 실패 줄 세부(기록) |
| `selftest_out.txt`, `console_check.txt`, `console_main_1~3.txt` | 실행 로그 |
| `raw\runs.jsonl`, `raw\logs\*_p89.json` | 본 실행 원자료 60줄과 재접근·H-3·H-1 기록 |
| `raw_check\runs.jsonl`, `raw_check\logs\` | 확인 실행 원자료 5줄 |
| `provenance.json` | 커밋, 명령, 읽은 입력, 열 정의(`columns`) |
- SHA256SUMS는 만들지 않았다(메인이 고정할 때).

## 공개(행위 그대로)
- 블라인드 경로(`j9_runs/606f8713/cdry_a1/VBK_c92*`·`VBK_c93*`·`cdry_a1/logs/`와 worktree 사본, 판 6 `selection.json`)는 열지도 검색하지도 않았다. `j9_runs` 아래에는 어떤 도구로도 접근하지 않았다.
- 연 자료
  - 명세 v8 초안 1~145·200~369행, 명세 v7(J7 줄 Grep과 655~674행)
  - `control_early_handover/report.md`
  - `dynamics_u832_o00/u10_instrumented_rerun.py`·`rerun_raw/runs.jsonl`, `dynamics_d1_d3/d00_instrumented_rerun.py`·`rerun_raw/runs.jsonl`
  - `ed7_design/keys_seal_b46bdf8f/confirm_g1_grid171.json`·`sens_keys_ed7.json`(job 형식만)
- Glob은 `control_early_handover`, `dynamics_u832_o00`, `dynamics_d1_d3`, `ed7_design/keys_seal_b46bdf8f`를 범위로 썼다. 이 Glob은 하위 폴더까지 훑었다. 블라인드 경로는 없는 폴더들이다.
- 코드 Grep
  - worktree `03_src\outrigger_sim\control\c2.py`, `04_scripts\04_hydraulic\coupled\run_v5.py`를 파일로 지정했다.
  - `04_scripts\04_hydraulic\coupled`(glob `*.py`)와 worktree `04_scripts` 자체(glob `*.py`, 패턴 `def j7_items_ed7|…`) 각 1회. 후자는 `04_scripts` 하위가 아니라 그 폴더 자체를 path로 썼으므로 지시의 범위 해석에 따라 위반일 수 있어 적는다. 출력은 .py 3줄이다.
- 이 선택은 본 키만으로 했다(O8-4). 결과는 명세 `<S8R_HANDOVER_PROBE_REPORT>` 자리에 들어간다.

---
**의존성 점검:** 이 세션에서 depcheck를 따로 돌리지 않았다. 호출 규약대로 conda run 활성화 상태에서 실행했고 60+5 job 모두 오류 0이라 이 작업에 필요한 범위(numpy, pinocchio 미사용, worktree 하네스)는 정상으로 보았다.

**확인 필요**: P8-9 "둘 다 부적격" → 다음 진행(가·나·다 등)을 사용자에게 묻는다.

**위임 필요**: 없음. 사용자가 (가)를 고르면 dynamics-expert가 계측 재실행(FR-Fs4 o0.075 × A/H3, T4h·행정 기록)을 할 수 있다(2 job, 약 2분).

**메인 세션 권고**: 출력 폴더 SHA256SUMS(`baseline_check.py write-sums`)는 명세 인용 전에 메인이 만든다.

사용한 스킬: 없음
