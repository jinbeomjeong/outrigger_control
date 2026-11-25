## 판 7 probe 분석 ①: 남은 검증 공백 확인 (hydraulics-expert, 2026-11-24)

코드는 고치지 않았고 시뮬레이션도 돌리지 않았습니다. 6bfb2560 probe 출력(`ed7_probe.jsonl` 654줄, `ed7_probe_t4h\*.npz`)과 worktree 코드만 읽었습니다.
- 압력은 모두 게이지 bar입니다. 로드 바닥은 0.1 bar abs = −0.913 bar g입니다.
- 의존성 점검은 생략했습니다. 읽기 전용 분석이고 numpy·json만 썼습니다.
- 사용한 스킬: 없음

### 결론

| # | 항목 | 판정 |
|---|---|---|
| 1 | VBM 계열 `rod_check_clear_count > 0`인 줄과 지운 Δp_fill | **확인됨**: 549줄 중 20줄, 30건 |
| 2 | 지운 뒤 신장 해제의 lag 출발 = 잠김 진값, M2 출발에 갇힌 상승이 섞인 흔적 | **확인됨**: 30건 모두 신장 해제이고 시드·충전 해제 기록이 없습니다. 전체 4107건의 충전 해제는 모두 수축 해제입니다 |
| 3a | void 몫 가둠(`void_fill_m`)이 실제로 바닥을 정한 줄 | **0줄**. 이상은 아니고, 이 경로가 probe에서 한 번도 발동하지 않았다는 뜻입니다. 공백은 단위 시험(탐침 B)으로만 덮여 있습니다 |
| 3b | `log_truncated`·`rod_check_clear_log_truncated` | **발생 0건**. 다만 잘림 표시가 없는 `ext_starts`가 68줄에서 상한 600에 닿았습니다(기록 전용, 아래) |
| 4 | 옛 플랜트 L의 `stale_seed_release` | **확인됨(이상 없음)** |

### 1. 로드 체크 열림 때 Δp_fill을 지운 줄 (VBM 549줄)

| 플랜트 | 줄 | 지운 줄 | 건수 | 팔 × 키 (다리) | 지운 Δp_fill [bar] |
|---|---|---|---|---|---|
| M | 117 | 4 | 4 | a2·a3·a4·a6 × R12_top-FR-Fs0-o0.05 (RR) | 4.635 |
| Mslow | 117 | 5 | 15 | 모두 c2: R12_top-RL-Fs0-o0.0 4건, R12_top-FR-Fs0-o0.05 4건, R12_top-FR-Fs0-o0.0 4건, R15_o0.0 2건, R15_o0.05 1건 (FL·RL) | 17.62~21.04 |
| Mfast | 105 | 0 | 0 | 없음 | 없음 |
| Mc005 | 105 | 4 | 4 | a2·a3·a4·a6 × R12_top-FR-Fs0-o0.05 (RR) | 2.809 |
| Mc04 | 105 | 7 | 7 | R12_top-FR-Fs0-o0.0: a2·a3·a4·a6 (RR 3.436), c2 (RR 4.990). R15_o0.05: a1 (RL 0.444), a6 (RL 5.196) | 0.444~5.196 |

- 분포(30건)는 최소 0.444, 중앙 11.41, 최대 21.04 bar이고 두 무리로 나뉩니다.
  - 0.44~5.2 bar(15건): 사각 수축 평형 충전입니다. 검토 1-4에서 "수 bar"로 예상한 쪽입니다.
  - 17.6~21.0 bar(15건): 모두 Mslow c2의 열리지 않은 수축 hold입니다. 검토값 20.5 bar 수준입니다.
- a2 `d` 부분(M·Mslow 각 12줄)과 a5 팔에는 한 건도 없습니다.
- 30건 모두 `log_rows == count`이고 `rod_check_clear_log_truncated`는 False입니다.

### 2. 지운 뒤 해제: lag 출발 = 잠김 진값

**30건 전부 같은 결과입니다.**
- 다음 해제는 모두 신장 해제입니다. 근거:
  - 해제 3 ms 안에 그 다리의 신장 충전 열림(`fills` 방향 +1)이 있습니다.
  - 해제 뒤 첫 읽기의 밸브 속도가 +2.86 또는 +4.52 mm/s입니다.
  - `lock_log` `release_cause`가 모두 `gate`입니다.
- 지운 시각에서 해제까지는 0.087~0.312 s입니다.
- 해제 시각에 `p1_fill_release_log` 줄과 `p1_retract_seed_log` 줄이 없습니다. 지운 시각과 해제 사이에 수축 충전 열림도 없습니다.
- 코드 경로로 보면 이것이 "lag 출발 = 잠김 진값"과 같은 뜻입니다.
  - `_fill_release_start_Pa`는 상승이 0이면 NaN을 냅니다. 그러면 `start_Pa = locked_pressure_Pa`가 됩니다.
  - 시드 줄은 NaN이 아닐 때만 쓰입니다.
- 출발값(`lock_log` `p_tr_after + dp_tr_lock`, 같은 식)의 예: M RR 4.958, Mslow FL 15.634 / RL 20.330, Mc005 RR 5.493, Mc04 a1 RL 1.284, a6 RL 6.046, c2 RR 6.950 bar.

**갇힌 상승이 T4h 판독에 그대로 보입니다.** P4 진값 판독(이 probe에서는 오차가 없음)에서 잠긴 로드 판독 = 진값 + 갇힌 상승입니다. void hold 중 판독이 정확히 "바닥 + 나중에 지운 값"입니다.

| 줄 | hold 중 판독 | 바닥 + 지운 값 |
|---|---|---|
| Mc04 a1 RL | −0.469 bar | −0.913 + 0.444 |
| Mc04 a6 RL | 4.283 bar | −0.913 + 5.196 |
| Mc04 c2 RR | 4.076 bar | −0.913 + 4.990 |

**섞인 흔적이 없습니다(전체).**
- VBM 549줄의 `p1_fill_release_log` 4107줄은 모두 수축 해제입니다. 각 해제 3 ms 안에 수축 충전 열림이 있고, 신장 열림과 겹친 줄은 0줄입니다.
- 4107줄 모두 같은 시각의 시드 줄이 하나씩 있고, 시드 줄의 `step_Pa`가 `fill_rise_Pa`와 같습니다.
- `p1_retract_seed_count == len(p1_fill_release_log)`가 549줄 모두에서 성립합니다.

**참고(판정 영향 없음)**
- 해제 직전 마지막 읽기(10 Hz, 해제보다 최대 0.1 s 앞)의 판독과 해제 시각 진값은 −4.7~+2.4 bar 차이가 납니다.
- 판독은 이미 상승이 빠진 뒤 값이므로, 그 사이 다른 다리가 움직여 잠긴 진값이 변한 것으로 봅니다.
- 순간 표본만으로는 더 나누지 못합니다. 그래서 2번 판정은 기록 경로(위 세 가지)로 했습니다.

### 3. void 몫 가둠과 기록 잘림

**3a. `void_fill_m`: 바닥을 정한 줄 0**
- 전용 기록 키가 없습니다. 게이트 요약에도 T4h에도 없어서 간접 판정을 했습니다.
- 판정 논리: 잠긴 다리의 Δp_fill은 잠김 구간 안에서 줄지 않습니다. 줄어드는 경우는 로드 체크가 열려 지우는 때와 해제·재잠김뿐입니다.
  - 그래서 해제에 충전 해제 줄이 없고 구간 안에 지운 기록도 없으면, 그 구간 내내 상승은 0입니다.
  - 상승이 0인 구간에서 중립인데 x > 0이 유지되면, 그것은 `min(void_fill_m, void)` 바닥 때문입니다.
- 결과: 상승 0 구간의 중립 읽기 쌍(잠김, line_dir −1, |u| ≤ 1e-6, x > 0, 배수 > 0) 4338개는 모두 배수됐고 유지된 쌍은 0개입니다.
- 상승이 있는 구간의 유지 읽기는 1257개입니다.
  - 모두 로드 판독이 바닥보다 높습니다.
  - 상승이 0인데 유지되려면 void > 0, 즉 진값이 바닥에 있어야 하고, 그러면 판독이 정확히 −0.913이어야 합니다. 따라서 이 1257개는 모두 상승 > 0입니다.
  - 상승 몫 = void + V(Δp)/A_ann ≥ void ≥ min(void_fill_m, void)이므로, 이때는 항상 상승 몫이 바닥을 정합니다.
- 바닥 판독(−0.913 bar, 진값이 바닥이고 상승 0) 1417읽기는 모두 게이트가 잡은 수축 충전 중이었고, 중립은 0읽기였습니다.
- 결론: void 몫 가둠 경로는 이 probe에서 바닥을 정한 적이 없습니다. 판 7 VBM 결과에는 영향이 없고, 검증 공백은 남습니다(단위 시험 탐침 B만 있음).

**3b. 기록 잘림**
- `rod_check_clear_log_truncated`: 0/549줄
- L `stale_seed_release.log_truncated`: 0/105줄
- 상한 아래: `p1_fill_release_log`, `p1_retract_seed_log`, `lock_log`, `lock_events`(상한 2000), 게이트 `fills`(상한 600)
- **관찰**: 게이트 요약의 `ext_starts`는 상한 600에 닿은 줄이 68/549입니다(플랜트·팔 전반, Mfast가 가장 많음). 이 키에는 잘림 표시가 없습니다.
  - 기록 전용이고, 소비처는 옛 M1c 스크립트(`04_scripts\03_control\m1_check\`)뿐입니다. 판 7 판정과 위 1~3 확인에는 쓰지 않았습니다.
  - 이 키를 판정에 쓸 계획이 생기면 계수 또는 잘림 표시를 더해야 합니다(`위임 필요` 후보, 지금은 불필요).

### 4. 옛 플랜트 L `stale_seed_release` (105줄)
- 키는 105줄 모두에 있고, VBM 549줄에는 없습니다(예상대로).
- 모든 줄에서 다음이 성립합니다.
  - `releases_with_seed`가 `lock_log`의 `p1_retract_seed_count`와 같음
  - `log_rows == releases_with_seed`
  - `stale_releases`가 로그의 stale 줄 수와 같음
  - `stale ≤ releases`
  - 시드가 있는 해제 수 ≤ 해제 수
- 합계는 시드 해제 936건, 그중 stale 119건(12.7 %)입니다. 줄당 stale은 0~3건입니다.
  - (시드, stale) 분포: (6,0) 21, (6,2) 6, (7,2) 8, (7,3) 14, (9,1) 6, (10,0) 8, (11,1) 24, (12,1) 11, (12,2) 1, (13,1) 6
- stale 해제의 시드 − 잠김 진값은 −25.5~+19.9 bar입니다. 양쪽 부호가 다 나오며, 묵은 수축 열림 압력이라는 정의와 맞습니다.
- 이상은 없습니다. h7 검토의 "판 5·6 묵은 시드 해제 980건"은 줄 집합이 달라 이 수와 직접 비교하지 않습니다.

### 수행한 작업
모두 PowerShell에서 `C:\ProgramData\miniforge3\envs\hydraulics-dev\python.exe -I -B <스크립트> …`로 실행했습니다.
- 입력
  - `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\6bfb2560\ed7_probe_a1\ed7_probe.jsonl` (스트리밍)
  - `...\ed7_probe_a1\ed7_probe_t4h\*.npz` (VBM 549개)
  - identity: HEAD 6bfb2560, clean, 654/654 끝
- 읽은 코드(worktree `C:\workspace\outrigger_control\.claude\worktrees\ed7-impl`)
  - `03_src\outrigger_sim\hydraulics\check_open_delay.py` 1~694
  - `04_scripts\04_hydraulic\coupled\harness_hydraulics.py` 200~480, 540~960, 990~1050
- 스크립트와 출력은 scratchpad에만 있습니다(`C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\0d95027e-6012-4053-b99a-1e505935768c\scratchpad\hydraulics-ed7probe\`).
  - `s04_analyze.py` → `s04_result.json`: 1·2·3b·4 확인
  - `s05_show.py` → `s05_out.txt`: 표
  - `s06_detail.py` → `s06_out.txt`: Mc04 세 구간의 읽기, 해제 진값 대조
  - `s07_void.py` → `s07_result.json`: 3a
  - `s08_floor.py`: 바닥 판독 계수
  - `s01_structure.py`·`s02_npz.py`·`s03_survey.py`: 구조 조사

### 블라인드 공개(실제 행위 그대로)
1. 처음에 Grep(`files_with_matches`, 패턴 `ext_starts`)을 worktree 전체에 돌렸습니다. 그 결과 worktree 사본 `.claude\worktrees\ed7-impl\06_analysis\02_control\j_p3_cause\j9_runs\606f8713\cdry_a1\` 아래 파일 이름 세 개가 목록에 나왔습니다.
   - `VBK_c93.json`: 블라인드 패턴 `VBK_c93*`에 걸립니다.
   - `VBK0_c93.json`, `VBK0_c92.json`: 패턴 밖이지만 같은 폴더입니다.
   - 내용은 열지 않았습니다. 드러난 것은 파일 이름과 그 파일에 기록 키 `ext_starts`가 있다는 사실뿐입니다.
2. 앞서 한 Grep 두 번(`j_p3_cause` 아래 `*.md` 내용 검색, worktree `*.py` 건수 검색)도 범위가 `606f8713` 폴더를 포함했습니다. 블라인드 경로의 결과는 출력되지 않았습니다.
3. 그 뒤 검색은 `j9_runs\6bfb2560\`, worktree `03_src`·`04_scripts`, `ed7_design` 문서로만 좁혔습니다.

### 메인 세션 권고
- 위 스크립트와 출력이 근거라면 scratchpad에서 프로젝트로 옮겨 주십시오. 예: `06_analysis\02_control\j_p3_cause\ed7_design\hydraulics_v7_review\probe_6bfb2560_check\`, SHA256SUMS 포함.
- 블라인드 공개 1번은 지시문 규칙 위반이므로 감사 기록에 올려 주십시오.

### 확인 필요
- void 몫 가둠(1-1)은 probe에서 한 번도 발동하지 않았습니다. 판 7 판정이 이 경로에 기대지 않으므로 지금은 그대로 두기를 권합니다.
  - 꼭 덮어야 한다면 "로드 바닥에 있는 잠긴 다리에 상승 0 부분 충전 → 중립" 합성 사례를 하네스 단위 시험에 더하는 방법이 있습니다(python-expert 몫).
  - 더할지 정해 주십시오.

메모리: `gate-trapped-fill-m2-shift.md`에 두 줄을 더했습니다(probe 확인 결과, 그리고 void 몫이 상승 0일 때만 바닥을 정할 수 있다는 판독 요령).
