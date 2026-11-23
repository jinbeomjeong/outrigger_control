## 436.9 J-P3 판 5 경로 2 독립 판정 보고 (dynamics-expert, 2026-11-23)

### 판정 (경로 2)

**T-JR-12b: pass (종료 0).** J-P3 rev 6 판정은 VBK 판정 행 334개와 T-JR-12a VBJ 판정 행 1개 모두 pass다(breach 합 0).

| 항목 | 경로 2 값 | 기준(넘김) |
|---|---|---|
| 상태 | **pass**, 실패 사유 0, 판정 불가 사유 0, setting_defect 0 | e8 2.7 상태 순서 |
| 블록·seed | b1 = s40, b2 = s41, N = 334 | e8 2.1 |
| 셀 표 | 경로 2가 h8_noise_VB.json에서 다시 만든 167행 표가 `selection.json` cell_table과 같다 | e1 2.1 |
| 분류(VBK0) | 트리거 없음 0, 트리거 전 대체 0, 미래치 0, VBK0 READY 미도달 7, 기회 327 | 2.2·e1 2.2 |
| **N_opp** | **327** (≥ 0.9N = 300.6 → b3 불필요, ≥ 301) | 2.5·e8 2.5 |
| **목격 기회 k** | **160** (≥ 45 → b4 불필요) | 2.6 |
| (1) 새 FAULT | **0** (판정 짝 N1 = 327 + 7 = 334). 짝당 95 % 상한 0.00893 | 2.7 (1)·e1 |
| **(2)+(3) n23** | **2 ≤ k_allow 7** (READY 상실 2, 지연 0) | e8 2.7 |
| (4) VBK J-P3 | 판정 행 334, jp3a 0 / jp3b(허용 초과) 0 / jp3c 0, judged_key_missing 0, 헤드 전용 선언 0 | 2.7 (4) |
| 짝 동일성 (가)(나)(다) | 334짝 모두 같다 | 2.4 |
| 통과 문장 핵심 | 기회 짝 327개(블록 b1, b2). (1) 새 FAULT 0: N1 = 334, 상한 0.00893. (2)+(3) n23 = 2 (k_allow = 7). (4) J-P3 H-7 0. 목격 기회 짝 k = 160개, 짝당 상한 0.01855 | e8 2.7 |

**J-P3 (③ revision 6)**

| 묶음 | 판정 행 | breach 합 (a/b/c) | judged_key_missing | 헤드 전용 선언 | 기록 행 | 상태 |
|---|---|---|---|---|---|---|
| VBK b1·b2 (334줄) | 334 (기회 327 + VBK0 READY 미도달 7) | 0 / 0 / 0 | 0 | 0 (모두 `level` 있는 이벤트 경로 줄) | 0 | pass |
| T-JR-12a VBJ (135줄) | 1 (`L2|s0|g6|52|ref|J1|top|Fs0`, normal) | 0 / 0 / 0 | 0 | 0 | 134 (L3 conservative) | pass |
| VBJ0 (135줄) | 0. ③ 끔이라 J-P3 줄이 아니다 | — | — | 0 | 135 (기준 줄) | B2 위반 0 |

- per-read 배열(jp3_*)이 VBK·VBJ T4h에 모두 있어 판정했다. 코드표는 판 4a 표와 같다.
- 판정 집합 읽기 수(VBK 334줄 합계): jp3a 610,885, jp3b 184,277, jp3c 14,270.
- B2 증거는 모든 줄에서 ① = k·② > 0이다. VBK k = 1인 줄 234, k = 2(g8)인 줄 100이고, VBK0·VBJ0도 위반이 없다.
- 리비전 검사: 태그 base, `extend_bound_check.rule_revision`, `run_extend_start_revision`이 VBK·VBJ 줄 모두 6이다.
- 참고(판정에 쓰지 않음): 줄에 기록된 jp3 키 9개가 경로 2 재계산과 판정 행 335개 모두에서 같다.

### 기록 항목 (e8 2.9, 판정 상태를 바꾸지 않음)

- **by_block**:
  - b1: 기회 163, 미도달 4, k 80, n23 1
  - b2: 기회 164, 미도달 3, k 80, n23 1
- **by_cell** (기회 / k / n23):

  | 셀 | 기회 | k | n23 |
  |---|---|---|---|
  | 0 FL τC | 40 | 15 | 0 |
  | 1 FL τR | 42 | 15 | 0 |
  | 2 FR τC | 40 | 20 | 0 |
  | 3 FR τR | 41 | 15 | 2 |
  | 4 RL τC | 40 | 25 | 0 |
  | 5 RL τR | 42 | 15 | 0 |
  | 6 RR τC | 42 | 33 | 0 |
  | 7 RR τR | 40 | 22 | 0 |

- **READY 상실 2건**: `cand=current#L2|s40|g8|31|slope|rpB|top|4.0|RR|raised|170.0`과 그 s41 짝.
  - VBK0 READY는 각각 66.6 s, 66.8 s다.
  - VBK 줄은 READY 없음, fault 단계 진입 없음, 마지막 단계 level, T4h 마지막 t_s 180.1 s다.
  - **LEVEL 교착 서명이 아니다.** 마지막 20 s 행정 폭이 FL 2.63 / 2.68 mm로 1 mm를 넘는다. 고장 다리는 FR이다.
- **VBK0 서명 줄 5개** (마지막 t_s 250.1 s, 단계 level):
  - s40 `g6|52|ref|J1|top|Fs0`
  - s40 `g6|56|ref|J2|top|Fs0`
  - s40 `g6|59|ref|J2|bottom|Fs4`
  - s41 `g6|56|ref|J2|top|Fs0`
  - s41 `ref|16|J1|B|0,0`
- **VBK0 READY 미도달 7짝**: 위 서명 5개 + s40·s41 `g8|30|slope|rpB|top|4.0|RR|raised|140.0`. VBK0만 나쁜 짝은 0이다(미도달 짝 중 VBK가 READY에 닿은 짝 0, 기회 짝 중 VBK0 − VBK > 30 s인 짝 0).
- **A/A** (VBK0 b1 대 b2, 167쌍 모두 있음): 센 쌍은 4개다.
  - g6|52, g6|59, ref|16: 한쪽만 READY 없음
  - g6|61|ref|S1|top|Fs4: |Δ| 47.1 s
  - 두 쪽 모두 READY 없는 쌍은 2개다.
- **τ_R 트리거가 걸린 단계**: probe 144, level 22. "트리거 읽기의 작용 단계"로 세든 "첫 고장 읽기의 작용 단계"로 세든 같다.
- **커버리지** (기회 짝 VBK 팔, 고장 다리, 래치 읽기부터 T4h로 셈):
  - `jp3_r58_witness`: 276짝, 목격 구간 438개
  - `jp3_r59_substeps`: 164짝, 합 121,138
  - `jp3_r510_candidates`: 123짝, 합 494
- **센서 등급(S-1~S-6) 전이**: 계산하지 않았다. 등급 키가 넘김에 정의돼 있지 않고, r79 등급 재구현은 넘김 7 2절에서 범위 밖이다.

### 경로 2가 직접 유도한 것 (기록 키와 대조)

T4h 배열(`phase`, `command_m_s`, `motor_stroke_m`, `rod_pressure_Pa`, `rod_fault_applied`)과 T4h meta `events` 전체 목록에서 다음을 직접 계산했다.

- 트리거 읽기: 334짝 모두 기록된 `trigger_read`·`first_applied_read`와 같다.
- 주입: −100 bar 고정, 적용 읽기 수, 다른 다리에는 주입 없음.
- 같은 읽기 D1 래치: 모두 래치됐다.
- 트리거 전 대체: 기록 `pre_trigger_fallback`과 같다.
- 첫 고장 읽기 전 명령 행: 두 팔이 같고, 기록 sha도 같다.
- 목격 k, 새 FAULT 쌍(`PHASE_FAULT` 진입 포함), n23, 교착 서명.

### 수행한 작업

- **입력 대조**: `SHA256SUMS` 950파일 모두 일치, 누락 0, 여분 0.
- **도구**: worktree `C:\workspace\outrigger_control\.claude\worktrees\z4378-p2ed5`, 브랜치 `z4378-p2ed5`(z4369-p2에서 분기), 커밋 **`dde4499dd6676a580181df17a50532318aa91d93`**. master 병합·push는 하지 않았다.
  - `04_scripts\path2\tjr12b_p2.py` (신규)
  - `04_scripts\path2\jp3_rev6_judge_p2.py` (신규, rev 5 경로 2의 다리별 판정을 재사용)
  - `05_tests\unit\test_tjr12b_p2.py` (합성 시험 17개)
- **시험**: 경로 2 시험 3파일 108 passed. ruff 통과.
- **환경**: dynamics-dev `python.exe -I -B`, PATH에 Library\bin, MKL_THREADING_LAYER=TBB.
- **결과 파일**: `C:\Users\jinbeom\.claude\p2_inputs\ed5_606f8713\p2_out\`

  | 파일 | sha256 |
  |---|---|
  | `tjr12b_p2.json` | `926823d832a2d45885f2b8cadfc4a8c64d3ce36c3bb8cfc72fc3e391fd6de235` |
  | `jp3_rev6_VBJ_VBJ0_p2.json` | `afe5ffaebcdb3ddb2c1a7558f3f724bb2b1a1341520f88995fc8c5405abbb86b` |
  | `run_commands.txt` (실행 명령 전체, 도구 커밋, 도구 파일 sha, 입력 대조 결과) | `2fbd9500…cfc8` |

  - 콘솔 기록 `*.console.txt`와 목록 `SHA256SUMS_p2_out`도 같은 폴더에 있다.

### 공개 (실제 행위)

- 연 파일:
  - 넘김 9개 (ed5, ed5_e1, ed5_e8, 4a7, 4a7e1~e3, 4a8, 4a8e1, tjr12)
  - 중립 입력 폴더
  - 내 이전 경로 2 도구 (z4369-p2의 `jp3_rev5_judge_p2.py`)
  - 시험 파일 형식을 맞추려고 연 내 경로 2 시험 `test_tjr12_p2.py`
- 금지 폴더·worktree(`jp3_*` 스크립트, j9_runs, ed5_design, prelaunch_j9, ed5_j9fail, 판정서, ed5-run5, ed5-tool8)와 판 5 원문·정오 8 원문은 열지 않았다.
- 입력 줄과 `selection.json` 안의 실행 쪽 경로 문자열은 따라가지 않았다.
- 결과 줄에 기록된 jp3 키는 비교용 echo에만 썼다. 판정에는 쓰지 않았다.

### 확인 필요 (추측하지 않고 가정·기록으로 둔 것)

1. **rev 6 태그 base**: 넘김에 "태그 base revision = 6"의 대응이 없다. 입력 줄의 태그 `final_C4G2_P3W_LAS_K1`을 보고 `final_C4G2_P3W` → 6으로 **가정**했다(CLI `--rev6-tag-base`). 대응이 다르면 VBK·VBJ 모든 줄이 setting_defect가 된다.
2. **rev 6 정체성 검사(13.6 대응)**: 넘김에 정의가 없다. 값만 기록했다: `spec_edition` fe6f5844, `carry_end_rule` inherit_when_gate_shut, `retract_start_rule` with_tracker. 판정에는 쓰지 않았다.
3. **2.6 목격 k의 "첫 LEVEL 뒤" 조건 적용 여부**: 두 해석 모두 k = 160이다(판정에 영향 없음). 기본은 래치 뒤 조건만 쓴다.
4. **u_hold 값**: 0.20924 mm/s(표기값)와 0.01 v_max = 0.209243016 mm/s 사이에 든 명령 읽기가 0이라 판정에 영향이 없다.
5. **T-JR-12a VBJ 판정 행 기대 수 1**: rev 5 T-JR-12 규칙(4a-7 e1 7절)을 이어 썼다. 판 5에서도 1인지 확인이 필요하다.
6. **seed 충돌 스캔**: 경로 2가 다시 하지 않았다(스캔 대상에 경로 1 폴더가 포함됨). 넘김대로 40·41을 썼고 키·seed_index가 일치함만 확인했다. `selection.json`의 dry seed는 92·93이고 정오 1에는 90·91로 적혀 있다. 범위 밖이라 기록만 한다.
7. **1.5 `commands_sha256` 앞 판 대조**: rev 5 출력이 입력에 없어 하지 않았다.

사용한 스킬: 없음
