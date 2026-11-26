# P8-14 교착 수정 후보 선택 재실행 (dynamics-expert, 2026-11-26)

## 판정: 두 후보 모두 적격 → **L-2 선택**

명세 12절 P8-14 규칙을 실행 전 고정된 문면 그대로 적용했다. 두 후보 모두 (1)~(4)를 만족했다. 그래서 B와 명령이 다른 키 수를 비교했고, 그 수가 더 적은 L-2를 골랐다(L-2 3키, L-1 6키).

| 조건 | B + L-1 | B + L-2 |
|---|---|---|
| (1) G1 `R12_bottom-FR-Fs4-o0.075-RE1bF-ready`: 게이트 전부 통과, READY 복귀(최종 ready) | **통과**: 게이트 실패 0, `t_ready_back_s` 34.93 s | **통과**: 게이트 실패 0, `t_ready_back_s` 41.03 s |
| (2) 판 5 교착 계열 4키: 교착 서명 거짓 | **4/4 거짓** | **4/4 거짓** |
| (3) 나머지 22키: B 대비 새 실패 게이트·새 J7·READY 미도달·새 FAULT | **0** | **0** |
| (4) 면제나 발사로 끝난 LEVEL의 DONE 시 \|D\| ≤ 15 kN | 통과(최대 4.38 kN) | 통과(최대 7.18 kN) |
| 적격 | **적격** | **적격** |
| B와 `commands_sha256`이 다른 키(27키 중) | 6 | **3** |
| 선택 | – | **L-2** |

- 기준 팔 B에서는 G1 교착이 다시 나온다. 해시 `17f5ecd5`는 H3와 같고, 교착 서명 참, 최종 단계 LEVEL, `end_att` 실패다. 판 5 계열 4키 가운데 B에서 교착 서명이 참인 키는 g6|56 하나다.
- P8-15 꼴 확인(기록): 후보가 한 번도 작동하지 않은 줄은 모두 B와 해시가 같았다. L-1은 21키, L-2는 24키가 같았다.

## 교착 서명(판 7 6.2 고정 읽기, `jp3_ed7_rules.is_stall_signature_ed7`, T4h phase·t_s·motor_stroke_m)
| 키 | B | L-1 | L-2 |
|---|---|---|---|
| G1 FR-Fs4 o0.075 | **참** | 거짓 | 거짓 |
| L2\|s40\|g6\|52\|ref\|J1\|top\|Fs0 | 거짓 | 거짓 | 거짓 |
| L2\|s40\|g6\|56\|ref\|J2\|top\|Fs0 | **참** | 거짓 | 거짓 |
| L2\|s40\|g6\|59\|ref\|J2\|bottom\|Fs4 | 거짓 | 거짓 | 거짓 |
| L2\|s41\|ref\|16\|J1\|B\|0,0 | 거짓 | 거짓 | 거짓 |
| 나머지 22키(D-3 2 + 회귀 20) | 모두 거짓 | 모두 거짓 | 모두 거짓 |
| 확인 줄: 판 5 저장 설정 VBK0, g6\|52 s40 | 참. 저장 서명과 같고 해시도 저장값 `d8ffb27c…`와 같음 | – | – |

## L-1이 연 주기와 발사(사건 줄은 사건 기준 s, VBK·S4 줄은 절대 s)
- "연 주기"는 A_ib 조건 1·2를 통과한 뒤 조건 3 (다)가 상승 절 때문에 열린 주기다.

| 키 | 연 주기(t, \|D\| kN, 5 s 상승 kN) | 그 주기의 발사(다리, 부호) | 그 뒤 DONE(경로, \|D\|) | t_ready (B) |
|---|---|---|---|---|
| G1 FR-Fs4 o0.075 | 1: (20.43, 7.95, 3.12) | RR −1 | 22.93 strict, 2.83 kN | 34.93 (–) |
| g6\|52 s40 | 1: (68.2, 3.97, 0.63) | RR +1 | 69.8 strict, 1.79 | 81.8 (86.8) |
| g6\|56 s40 | 4: (70.2, 4.38, 0.96), (78.3, 5.73, 0.99), (81.7, 5.45, 0.72), (87.6, 5.67, 1.06) | FR +1, FR −1, RR −1, FR +1 | 89.3 relax, 4.38 | 101.3 (–) |
| g6\|59 s40 | 1: (63.3, 3.52, 3.12) | FR −1 | 66.8 strict, 1.13 | 78.8 (80.0) |
| U bottom-FR-Fs2 o0.0 | 1: (22.5, 4.39, 0.74) | RL +1 | 25.2 strict, 2.02 | 37.2 (50.5) |
| S4 e0.002 | 1: (63.8, 2.23, 0.64) | RL −1 | 64.5 strict, 0.13 | 76.5 (76.5) |

- 설계 오프라인 예측대로 L-1은 교착이 아닌 줄(g6|52, g6|59, U FR-Fs2, S4)에서도 작동한다. 발자국이 L-2보다 크다.

## L-2 면제 사용 횟수와 그때의 |D|
- 면제 사용 횟수는 비상승 판정을 면제로 통과시킨 주기 수다.

| 키 | 면제 주기 수(시각 s) | 그때 \|D\| [kN] | 창 안 상승 [kN] | 조건 다리 | DONE(경로, \|D\|) | t_ready (B) |
|---|---|---|---|---|---|---|
| G1 FR-Fs4 o0.075 | 7 (28.43~29.03) | 6.16~6.26 | 0.02~0.26 | RL·RR | 29.03 relax, 6.26 | 41.03 (–) |
| g6\|56 s40 | 11 (86.8~87.8) | 4.48~5.30 | 0.58~1.23 | FR | 87.8 relax, 5.24 | 131.7 (–) |
| U bottom-FR-Fs2 o0.0 | 11 (29.3~30.3) | 6.72~7.18 | 1.97~2.13 | RL | 30.3 relax, 7.18 | 42.3 (50.5) |

- L-2는 위 세 줄에서만 작동했다. 모두 B에서 꼬리가 길거나 교착인 줄이다. 그 밖의 24키는 B와 비트가 같다.
- g6|56 L-2는 첫 DONE(87.8 s) 뒤 READY가 131.7 s다. 그 사이 두 번째 LEVEL이 119.7 s에 strict로 끝났다. 같은 키 L-1의 101.3 s보다 30 s 늦다. 이것은 P8-14 판정 항목이 아니라 기록이다.

## `commands_sha256`이 B와 다른 키
- L-1(6키): G1, g6|52, g6|56, g6|59, U bottom-FR-Fs2 o0.0, S4 e0.002
- L-2(3키): G1, g6|56, U bottom-FR-Fs2 o0.0

## 그 밖의 기록
- D-3 두 줄(LSM4 top-FR-Fs0 o0.05, VBMslow top-FL-Fs0 o0.0)
  - B(A + H3′)에서 꼬리가 끝났다. t_ready 37.35 s / 22.0 s, 해시는 P8-9 A 줄과 같다.
  - 두 후보 모두 작동하지 않았다. 해시가 B와 같다.
  - 판 7 a2에서 보인 40 s 넘는 꼬리는 방향 A·B 구성에서는 나오지 않는다.
- S8 e0.0은 세 팔 모두 `FAULT_LIFT_STROKE_LIMIT:soil:FR`로 끝났다(B 포함, 새 FAULT 아님). 해시가 같다.

## 판 5 교착 계열 키 `<P814_VBK_KEYS>` 선택 근거
- **고른 키**
  - `cand=current#L2|s40|g6|52|ref|J1|top|Fs0`
  - `cand=current#L2|s40|g6|56|ref|J2|top|Fs0`
  - `cand=current#L2|s40|g6|59|ref|J2|bottom|Fs4`
  - `cand=current#L2|s41|ref|16|J1|B|0,0`
- **근거 문장**
  - `aa_stall.json`: 네 키 모두 해당 seed 줄의 `ready`가 null이다. g6|52·g6|59는 b1(s40), ref|16은 b2(s41), g6|56은 b1·b2 둘 다 null이다.
  - `aa_stall_lock.json`: 그 줄들은 마지막 20 s에 네 다리 `locked_share` 1.0이고, `share_u_le_hold`가 대부분 1.0(|u| ≤ u_hold 0.2092 mm/s)이며, `stroke_span_mm`가 0.40~0.66이다. 잠긴 사각 교착 서명이다.
  - `j9fail_cause_analysis.md` 143행: "정오 8 8-1.2의 VBK0 교착 서명(마지막 20 s 네 다리 잠김, |u| ≤ u_hold)과 같은 계열". 71행: P1 불감대 "LEVEL 완료 교착과 같은 계열".
- **뺀 키**: `L2|g8|30|slope|rpB|top|4.0|RR|raised|140.0`. b1 줄에서 FL `locked_share`가 0.075로 잠기지 않았고, 정지 창의 하한 추정 \|D\|가 39.85 kN이다(`aa_stall_twist.json`). 사각 잠김 교착 꼴이 아니라서 뺐다.
- **fault 계획과 seed**
  - 저장 줄의 rod_fault 기록(`aa_inspect.json` 1377~1465행 등, `aa_detail.json` 452~467행)에서 seed와 fault를 그대로 옮겼다. g6|52 r044-RL-tau_C, g6|56 r048-FL-tau_C, g6|59 r051-FR-tau_R, ref|16 r164-RL-tau_C이고 모두 STUCK −100 bar다.
  - 재구성 확인: 판 5 설정 VBK0으로 g6|52 s40을 다시 돌린 결과 해시가 저장값 `d8ffb27c6a1b…`와 같았고 교착 서명도 참으로 재현됐다.

## 수행한 작업
- **코드**: worktree `ed7-impl` HEAD `8a2a52ce2c07d2af11a6212a2932d2061261f156`. import만 했다. 실행 전후 `git status --short`는 비어 있었다. 커밋하지 않았다.
- **배치**
  - 2026-11-26 16:34에 `reserve.py prune` 0건, `list` 예약 0건을 확인했다. P코어 마스크 0xFFFF, 워커 8로 돌렸다.
  - 82 job(81 + VBK0 확인 1)을 세 번에 나눠 돌렸다. 13 job 199 s, 35 job 441 s, 34 job 326 s로 합계 약 16분이고, 30분 안이다.
  - `OMP_NUM_THREADS` 1, NUMBA 캐시는 scratchpad `dynamics-p814`에 두었다가 지웠다.
- **팔**(`p814_rerun.py`)
  - B: 키 설정에 증인 판정 켬·(i-b) 끔 + H3′. h3p와 같은 `_end_finished_reapproaches` 복사본이다.
  - L1: B + `LockStartB._is_completion_open` 감싸기(상승 절, $W_r$ 5 s, $x_r$ 600 N).
  - L2: B + `C2Controller._has_twist_load_stopped_rising` 감싸기(사각·정지 연속 ≥ 50주기, 창 상승 ≤ 2.5 kN, \|D\| + 0.5 ≤ 15 kN).
  - 기록 감싸기: 재접근 시작·끝, A_ib 발사, `note_level_done`.
- **VBK 경로**
  - `r79_L3L4_final.run_one`을 워커 안에서 직접 불렀다.
  - 환경 변수: `R79_V5_SETTING` = P814-<팔>-VBKM0, `R79_ROD_MODEL=plant_truth`, 팔별 T4h 폴더, 저장 fault 4건만 담은 자체 계획 파일.
  - 설정 이름은 워커 안에서 `run_v5.ALL_SETTINGS`·`T4H_SETTINGS`·`ROD_FAULT_SETTINGS`에 더했다.
  - `r51`이 import할 때 `sys.argv[1]`을 프로젝트 루트로 읽으므로, VBK 워커에서는 `sys.argv[1]`을 worktree 루트로 두었다.
  - 첫 시작은 이 루트 문제로 곧바로 멈췄다. 그때 남은 빈 `runs.jsonl`은 내 파일이라 지웠다.
- **판정**: `p814_analyze.py`. 보조 집계는 `p814_actions.py`다.

## 출력(`C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\control_level_deadlock\probe_8a2a52ce\`)
| 파일 | 내용 |
|---|---|
| `p814_rerun.py`, `console_1~3.txt` | 실행 스크립트와 로그 |
| `raw\runs.jsonl`, `raw\logs\*_p814.json`, `raw\t4h\`, `raw\t4h_r79_*\`, `raw\plans\` | 82줄 원자료, 작동 기록, T4h, VBK fault 계획 |
| `p814_analyze.py` → `p814_selection.json`, `p814_metrics.csv`, `p814_analyze_out.txt` | 규칙 적용과 줄별 지표 |
| `p814_actions.py` → `p814_actions_out.txt` | L-1·L-2 작동 요약, P8-15 꼴 확인 |
| `provenance.json` | 커밋, 명령, 팔 정의, VBK 키 근거, 열 정의(`columns`) |
- SHA256SUMS는 메인 몫이다.

## 가정·한계
- 문턱은 설계 2절 값 그대로다($W_r$ 5 s, $x_r$ 0.6 kN, $\Delta_{max}$ 2.5 kN, 여유 0.5 kN).
- L-2의 "사각·정지 연속 주기"는 매 `apply_floors` 뒤에 센다. 그래서 완료 판정보다 한 주기 늦다. 행정 정지는 A_ib의 `_blind_still_m` < `ib_still_m`(0.1 mm)이고, 읽기가 skip + 3개 미만인 주기는 0으로 센다.
- L-1 상승 이력은 LockStartB 객체에 LEVEL 주기마다 쌓고, LEVEL 밖에서는 비운다.
- 이 구현은 검토용 monkeypatch다. 명세 Y8-10 구현(python-expert)과 비트가 같다는 보장은 없다. P8-15 관문으로 다시 확인해야 한다.
- 사건 줄의 `level_done` 기록에서 사건 전 DONE이 두 번 찍힌다. 기본 실행과 사건 갈래가 같은 목록에 기록하기 때문이다. 판정에는 쓰지 않았다.
- 판 5 키는 판 5 플랜트(VBK0)가 아니라 명세대로 VBKM0 + 판 8 구성 B에서 돌렸다. 그래서 B에서 교착은 g6|56 하나만 남았다.

## 공개(행위 그대로)
- **결과를 본 뒤의 선택이다.** 교착 수정 설계와 이 선택 재실행은 판 6·7 결과, P8-9·진단·H3′ 결과, 판 5 VBK0 교착(공개 자료)을 본 뒤에 했다(명세 13절 6, O8-4 확장). 선택 규칙 P8-14는 실행 전에 고정돼 있었고 결과를 보고 바꾸지 않았다. G1 FR-Fs4 o0.075는 P8-14 선택 키이므로 census에서 그 통과는 표본 내다(명세 6.3 끝 문단).
- **블라인드**
  - 블라인드 경로(`j9_runs\606f8713\cdry_a1\VBK_c92*`·`VBK_c93*`·`cdry_a1\logs\`와 형제 파일, worktree 사본, `prelaunch_j9\ed6_inputs\x11\selection.json`)는 열지도 검색하지도 않았다.
  - `j9_runs` 아래에는 어떤 도구로도 접근하지 않았다.
  - 판 5 저장 줄의 seed·fault·해시는 공개 폴더 `aa_stop_606f8713`의 json에서만 읽었다.
- **경로 정정**: 지시의 `…\ed5_design\ed5_j9fail_606f8713\`는 없다(`Get-ChildItem` 오류). 실제 위치는 `…\j_p3_cause\ed5_j9fail_606f8713\`다. 존재는 `Test-Path`로 확인하고 비재귀 목록만 본 뒤 `j9fail_cause_analysis.md`를 파일로 지정해 Grep했다.
- **연 자료**
  - `control_level_deadlock\report.md`, 명세 v8 Grep(P8-14 줄)과 336~346행
  - `aa_stop_606f8713\`: 비재귀 목록, `aa_stall_twist.json`·`aa_stall_lock.json`·`aa_stall.py`·`aa_inspect.py` 전체, `aa_inspect.json` 1~62·1370~1465행, `aa_detail.json` 440~469행, 이 폴더 `*.json` 대상 Grep 3회
  - `ed5_j9fail_606f8713\`: 비재귀 목록, `j9fail_cause_analysis.md` Grep 1회
  - P8-9·H3′ 원자료
- **코드 Grep**(파일 또는 파일이 든 폴더 지정)
  - worktree `run_v5.py`·`jp3_12b_plan.py`·`r79_sensor_screen.py`·`r79_L3L4_final.py`·`r67_g1_screen.py`·`r51_reapp_closed_loop.py`·`lock_start_b.py`·`c2.py`
  - 폴더 `04_scripts\04_hydraulic\coupled`(glob `*.py`) 1회, `04_scripts\03_control\s8`(glob `*.py`) 1회, `03_src\outrigger_sim\control`(glob `*.py`) 1회

---
**확인 필요**: 없음(규칙이 L-2를 골랐다).

**위임 필요**
- control-expert: 명세 3.8·`<S8R_DEADLOCK_CHOICE>` = L-2, `<S8R_P814_REPORT>` = 이 보고, `<P814_VBK_KEYS>` = 위 4키를 반영한다. g6|56 L-2의 READY 131.7 s(두 번째 LEVEL) 기록을 공개 항목에 넣을지 판단한다.
- python-expert: Y8-10 L-2 구현. 사각·정지 연속 주기 조회, 면제 기록(`n_waiver_done`, `waivers`), P8-15 시험. 이 검토 스크립트의 계수 시점(완료 판정보다 한 주기 늦음)을 구현과 맞출지는 명세에 적는다.

**메인 세션 권고**: 출력 폴더 SHA256SUMS는 메인이 만든다.

사용한 스킬: 없음
