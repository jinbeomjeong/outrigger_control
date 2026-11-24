# 판 6 J-P3 경로 2 독립 판정(실행 커밋 79495405 출력, 2026-11-24, dynamics-expert)

- 정의: 넘김 7 `jp3_rev6_p2_handoff_ed6.md`(sha256 `55c8e92e30245e49…`, 대조함)이 우선하고, 넘김 6 `jp3_rev6_p2_handoff_ed5.md`와 정오 1·정오 8, 4a-7(+정오 1~3)·4a-8 8절·4a-8 정오 1 8절 넘김의 정의 문장만 썼다.
- 입력: 중립 사본 `C:\Users\jinbeom\.claude\p2_inputs\ed6_79495405\`. `SHA256SUMS`의 sha256 `731bc1bcecaab439…`(지시와 같음), 987개 파일을 모두 대조했다(불일치 0, 누락 0, 목록 밖 파일 0).
- 키 목록 sha256은 넘김 7 값과 같다: `confirm_a_keys_v2.json` `75413549…`, `confirm_b_grid192.json` `4e80e69b…`, `sens_keys_v2.json` `70f4bb6d…`.
- 도구: `scripts/jp3_ed6_judge_p2.py`(새로 씀)와 `scripts/jp3_rev5_judge_p2.py`(판 5 때 쓴 경로 2 모듈을 그대로 복사, 다리별 J-P3a/b/c 셈). 시험은 `scripts/test_jp3_ed6_judge_p2.py`(6개 통과)다. 작업 worktree는 `.claude/worktrees/p2-ed6`(브랜치 `p2-ed6`, master `bdb3739d`에서 만듦, 커밋 없음)다.
- 참고: (2)(3)(4)는 판 6이 확인 (가)에서 멈춘 뒤 돌린 **판정 후 기록용** 실행이다. 판 6 판정에 쓰지 않는다.

## 1. 판정 요약

| 묶음 | 입력 줄 | 판정 행(기대) | 헤드 전용 선언 | 판정 불가·결함 | 침범 줄 | 침범 읽기(a / b / c) | 경로 2 상태 |
|---|---|---|---|---|---|---|---|
| (1) 확인 (가) `confirm_a` (VBLc005·c04·v05·v15) | 216 | **56 (56)** | 160 | 0 | **0** | **0** (0 / 0 / 0) | **통과** |
| (2) 격자 (나) `confirm_b` (VBL) | 192 | 192 (192) | 0 | 0 | **44** | **62** (62 / 0 / 0) | **실패** (H-7) |
| (3) 감도 `sens` (VBLc005·c04·v05·v15) | 184 | 104 (104) | 80 | 0 | **3** | **3** (3 / 0 / 0) | **실패** (H-7) |
| (4) j9_main (VBL·LSL1~4) | 388 | 200 (200) | 188 | 0 | **0** | **0** (0 / 0 / 0) | **통과** |

- 판정 행은 모두 clean이다. 결함·판정 불가 사유가 있는 판정 행은 없다. 그래서 넘김 7 2.1의 상태 순서(실패 > `setting_defect` > 그 밖의 판정 불가 > 통과)를 어느 쪽으로 읽어도 결과가 같다.
- 키 목록 줄 가운데 결과가 없는 줄은 0이다. 키 목록에 없는 결과 줄도 0이다. 키 목록의 헤드 전용 선언과 T4h meta 선언은 모든 줄에서 같다. (나)는 키 목록 `t4h_file`과도 모두 같다.
- j9_main은 설정마다 판정 행 40이다. 사례별로는 R12 160, R14 10, R15 10, R16 20이고, 넘김 7 2.2와 같다.
- (나)는 V0 실패 줄(`v0_pass` 거짓 18줄)도 판정했다(넘김 7 2.4). 침범 44줄 가운데 1줄이 `v0_pass` 거짓 줄이다(기록).
- 등급: 판정 행은 모두 `sensor_grade` = ideal이다. 하네스 줄에는 `level`이 없다(넘김 7 2.1, 4a-7 4.3 3).
- 기록 키 대조(판정에 쓰지 않음): 줄에 기록된 다리별 J-P3 키 9종(`jp3a_reads` … `jp3c_fill_breach_reads`)이 경로 2 셈과 네 묶음 모든 판정 행에서 같았다. 기록 `jp3_judged_row`와 경로 2의 판정 행 선정도 다른 줄이 0이다.

## 2. 정체성(넘김 7 1.3)

- ③ 켬 줄 980개 모두 통과했다. 헤드 전용 선언 줄 428개는 1·4·5번, 이벤트 경로 줄 552개는 1~5번을 보았다.
  - 태그는 `final_C4G2_P3W_LAS_K1_LSB`이다. 기저 `final_C4G2_P3W` → 6. 줄 태그와 T4h meta 태그가 같다.
  - `rule_revision` 6, `spec_edition` `fe6f5844`
  - `lsb_components`는 집합으로 {A_i, A_ii, B3}이다. 중복이 없고 T4h meta와 같다.
- 4번: 모든 줄에 줄 수준 `run_extend_start_revision` 키가 **없다**. 그래서 `hydraulic_options`의 `extend_start_tracked`·`extend_start_hold`·`extend_start_witness`로 보았고, 모두 참이다.
- 기록: `carry_end_rule` = `inherit_when_gate_shut`, `retract_start_rule` = `with_tracker`(이벤트 경로 줄 전부)
- P4 증거(4a-8 8.1, 하네스 줄 k = 1): 이벤트 경로 줄은 모두 ① = ② > 0이다. 헤드 전용 선언 줄은 모두 ① = ② = 0이고 ③ record가 없다(None).
- 시험 전용 설정(`*_X11`, `VBG4`, `VBG5`)은 0줄이고, 묶음 밖 설정도 0줄이다.

## 3. 침범 읽기의 꼴

(2)와 (3)의 침범 65읽기(62 + 3)는 **모두 한 가지 꼴**이다.

| 항목 | 값 |
|---|---|
| 판정 | J-P3a만(`jp3a_breach_reads`). J-P3b·J-P3c 침범 0 |
| 기록 분류 | `carry_ext` |
| 플랜트 상태 | `moving_ext`. 바로 앞 읽기는 `locked_ext`다. 신장 잠김에서 풀려 움직이기 시작한 **첫 읽기**다 |
| 운반 안 위치 | `lock`/`locked_ext` 읽기 뒤 `carry_ext` 연속 구간의 셋째(32 + 2) 또는 넷째(30 + 1) 읽기 |
| 작용 단계 | `probe`(T4h `phase` 행 n−1과 행 n 모두 `probe`) |
| 작용 명령 $u$ | 2.48 mm/s 또는 3.393 mm/s(탐침 신장 램프 0.50 → 1.49 → 2.48 → 3.39 → 3.57 mm/s 도중) |
| 상계 | `jp3_ext_bound_Pa` = $\hat p+\delta_m$. (나) 14.19~30.70 bar, (3) 15.46~20.49 bar |
| 초과 $p_{tr}-(\hat p+\delta_m)$ | (나) 0.0055~22.43 bar(중앙 5.72 bar), (3) 1.20~16.64 bar |
| 로드 판독 대 상계 | 침범 읽기에서 `rod_pressure_Pa`가 `jp3_p_tr_Pa`와 **정확히 같다**(ideal 등급, P4). 그래서 판독 − 상계 = 참값 − 상계 > 0이고, 판독도 상계를 넘는다 |
| 지속 | 침범마다 한 읽기(0.1 s)다. 65읽기 모두 다음 읽기에서 $p_{tr}$이 상계 + 1 Pa 이하로 내려간다(예: 5.90 → **19.35** → 7.02 bar, 상계 16.70 → 14.25 bar). 한 줄 안의 침범 읽기는 모두 서로 다른 다리다 |
| R5-8~R5-10·판 6 구성 요소 | 관문 닫힘(`jp3_gate_open` 거짓), R5-8 목격 없음, R5-9 소단계 0, R5-10 후보 0. 침범 읽기에서 `lsb_a1_on`·`lsb_a2_on`·`lsb_b1_blocked`·`lsb_protected`는 모두 거짓이다 |
| 다리 | (나) RL 28, FR 19, RR 15. (3) RL 3. 침범 다리는 사건 쌍둥이 다리(`twin.leg`)와 겹친 적이 없다 |

### 3.1 (나) 격자 침범 줄 44의 분포(기록)
- 시점 `timing`: `level` 96줄 가운데 44줄, `ready` 96줄 가운데 0줄
- 사건·높이(침범 줄 / 전체): G4 bottom 5/32, G4 top 6/32, FS24 bottom 10/32, FS24 top 7/32, RE1bF bottom 9/32, RE1bF top 7/32
- 줄당 침범 읽기: 1읽기 26줄, 2읽기 18줄(같은 탐침에서 두 다리가 차례로)
- 시각: 41.8~50.4 s

### 3.2 (3) 감도 침범 줄 3
- R16 `VBLv05` offset 0.05·0.075 s, `VBLv15` offset 0.05 s. 모두 RL, t = 45.0~45.1 s
- VBLc005·VBLc04는 침범 0이다. R12·R14·R15 줄에도 침범이 없다.

### 3.3 해석(판정 아님, 동역학 쪽 소견)
- 침범은 모두 PROBE 신장이 신장 잠김(`locked_ext`)에서 출발해 플랜트가 이동으로 바뀌는 한 읽기에서만 나온다. 로드측 압력이 한 읽기 동안 치솟았다가 다음 읽기에 가라앉는다. 이 꼴은 잠김 해제 순간에 로드측 챔버가 눌리는 과도와 맞는다.
- 모니터의 $\hat p+\delta_m$은 그 과도를 덮지 못한다.
- 원인 확정에는 소단계(1 ms) 플랜트 기록이 필요하다. 이 판정의 범위 밖이다.

## 4. 수행한 작업
- 실행 환경: dynamics-dev `conda run -n dynamics-dev python -I -B`
- 명령(입력 `I` = `C:\Users\jinbeom\.claude\p2_inputs\ed6_79495405`):
  - `jp3_ed6_judge_p2.py judge --bundle confirm_a --records I\confirm_a\confirm_a.jsonl --key-list I\confirm_a_keys_v2.json --key-list-sha256 75413549… --expect-judged-rows 56 --expect-settings VBLc005 VBLc04 VBLv05 VBLv15 --out jp3_p2_confirm_a.json` → 종료 0
  - 같은 꼴로 `confirm_b`(키 `confirm_b_grid192.json`, 192, VBL) → 종료 1, `sens`(키 `sens_keys_v2.json`, 104) → 종료 1, `j9_main`(키 목록 없음, 200, VBL LSL1~4) → 종료 0
- 출력: `jp3_p2_confirm_a.json`, `jp3_p2_confirm_b.json`, `jp3_p2_sens.json`, `jp3_p2_j9_main.json`. 침범 읽기 하나하나는 각 json의 `breach_rows[].reads`에 있다.
- 도구 자체 검사
  - 침범 마스크를 다시 유도해 `judge_leg` 셈과 대조했다(`count_check`, 65읽기 모두 같음).
  - `jp3_t_s`와 `t_s`는 같은 격자다(`t4h_index_aligned` 참).
- 단위 시험 6개: 태그 기저, 정체성 1·4·5번 결함 주입, P4 증거, 선언·record 결함, 끔·묶음 밖 설정
- 보조 스크립트(기록용, `scripts/`)
  - `verify_sums.py`: 입력 SUMS 대조
  - `next_read_check.py`: 침범 다음 읽기와 줄 안 다리 구분
  - `v0pass_breach.py`: (나) 침범 줄의 `v0_pass`

## 5. 가정·해석(확인 필요)
1. `run_extend_start_revision` 키가 있으나 값이 null인 줄은 "키 없음"으로 읽게 했다. 실제로는 그런 줄이 없었다(모든 줄에 키 자체가 없음). 결과에 영향이 없다.
2. 키 목록의 `head_only_declared`가 T4h meta 선언과 다르거나, 결과 줄이 키 목록에 없으면 `setting_defect`로 두었다. 넘김에 명시된 규칙이 아니다. 해당 줄은 0이라 결과에 영향이 없다.
3. 상태 순서 "실패 > `setting_defect`"에서 실패는 결함 없는 판정 행의 H-7만 센다. 결함이 있는 판정 행은 0이라 결과에 영향이 없다.
4. 줄의 `lsb_components`와 T4h meta `lsb_components`, 줄 태그와 meta 태그가 다르면 `setting_defect`로 두었다(경로 2가 정한 일관성 검사). 해당 줄은 0이다.

## 6. 공개(실제로 연 것)
- 넘김: ed6(넘김 7), ed5(넘김 6), ed5_e1, ed5_e8, 4a7, 4a7e1, 4a7e2, 4a7e3, 4a8, 4a8e1
- 판 5 때 경로 2 worktree `.claude/worktrees/z4378-p2ed5`의 자기 모듈 `jp3_rev6_judge_p2.py`·`jp3_rev5_judge_p2.py`
- 중립 사본 입력 전체
- 키 목록 meta에는 경로 1 도구 이름과 `ed6_design` 경로 문자열이 들어 있다. 읽기만 했고 따라가지 않았다.
- 경로 1의 코드·출력·브랜치·판정 파일, 판 6 명세 원문·정오, `ed6_design/`, 감사·판정서 문서는 열지 않았다.
- **공개할 점**: 작업 초기에 넘김 파일을 찾으려고 `j_p3_cause` 폴더에서 Glob 패턴 `*handoff*`를 한 번 돌렸다. 이 Glob은 하위 폴더까지 훑는다. 그래서 `ed6_design/`와 블라인드 경로 `j9_runs/606f8713/cdry_a1/…`도 검색 범위에 들었다.
  - 돌아온 결과는 넘김 파일 15개와 `ed5_design\run_commit_606f8713_evidence\verif_at_run\handoff_leak.py`(파일 이름만)였다.
  - `ed6_design/`와 블라인드 경로의 파일 이름·건수는 결과에 나오지 않았다. 일치한 것이 없었기 때문이다.
  - 그 밖에 이 폴더들을 대상으로 한 Read·Grep·Glob은 없다.
- `git worktree list`로 worktree 이름(ed6-impl 등)을 보았다. 이름만 보았고, 그 안은 열지 않았다.
