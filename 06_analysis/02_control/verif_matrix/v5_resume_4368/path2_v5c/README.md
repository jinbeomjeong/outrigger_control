# 436.8 경로 2 — v5 기준 원 규칙 등급 재집계 (H-6·H-8·H-9·H-10)

- 규칙: 436.8 원판 `../../v5_resume_4368_rules.md`(`9019b405…`), rev1(`d9094fda…`), rev2(`497e4614…`), rev3(`dad8dfa6…`), rev4(`7ea87a30…`), **rev5(`452a8436…`, 커밋 31d543e), rev6(`809e5639…`, 커밋 d581df4)**. 원 규칙은 원판 부록 A의 `v5_criteria.md` + 개정 1~12b다.
  - 실행할 때마다 두 곳에서 확인한다.
    - `p2_4368.check_seals`: 원판~rev4, 부록 A, R2-9·R3-F4 CRLF 정규화.
    - 이 폴더의 `check_rev3`: rev3~rev6의 raw sha, `.sha256` 기록, LF·BOM 없음.
  - 어긋나면 종료 2(S-1)다.
- 작성자: terramechanics-expert(경로 2, 사용자 결정 2026-11-13). 경로 1 도구를 만들거나 고친 적이 없다. 읽은 것은 아래 "독립성 공개"에 적었다.
- 환경: `conda run -n dynamics-dev python -I -B <도구> ...`. 쓰는 것은 표준 라이브러리, numpy, scipy, 그리고 git(`log`·`rev-parse` 조회만)이다.
- 공통 CLI:
  - 인자: `--repo`, `--out <JSON>`, `--p2-dir`, `--allow-import-sha`.
  - 종료 코드: 0(이상 없음), 1(실패 또는 판정 불가), 2(멈춤 H-*·S-*·P-*, 규칙 sha 불일치, import sha 불일치 `P2-SHA`), 3(도구 오류).
  - stdout 마지막 줄은 ASCII JSON(`tool_sha256`, `common_sha256`, `status`, `exit`, `out_sha256`, `stop_codes`)이다.
- `.gitattributes`에서 이 폴더 전체를 `-text`로 둔다. 도구 sha는 LF 바이트 기준이다.

## import (복사하지 않음, 메인 세션 결정 2026-11-13)

J 항목(R3-C3~C8, R4-C5의 `values.case_floor_deg`로 정하는 J3 바닥 각)은 dynamics-expert 파일을 경로로 import한다. 그 파일은 고치지 않는다.
- 찾는 순서: `--p2-dir` → `../path2` → dynamics-expert worktree `agent-a2e81c57365f0d7bb`.
- sha가 다르면 종료 2(`P2-SHA`)다.

| 파일 | 고정 sha256(rev5·rev6 판, 커밋 `7b1e2e8`·`d49068e`) | 쓰는 것 |
|---|---|---|
| `p2_v5j.py` | `5772624cb28e414ceeb38af3eb6d386a2e0a78857db8a5ea9a5d3cd2ec5f7d8b` | `judge_pair`(M-3: LS J11 n_late > 0 → stop, 이 도구의 L-e로 이어짐), `j_values`, `jp3`, `nrev_max_by_row`, `pair_key`, `row_key`, `rod_reading_from_t4h`, `tag_of`, `is_event` |
| `p2_4368.py`(`p2_v5j.core`) | `dc631509b90296d842ec382c911f6a0abfd8944e170802386221eb2a1f315a27` | `check_seals`, `load_is_extend_start`, `Findings`, `t_ge/t_lt/t_gt`, `num`, `dig`, `read_jsonl`, `F_MIN_N` |

## 도구와 sha256 (rev6 판, 각 묶음 첫 결과 전 고정)

| 도구 | 묶음 | sha256 |
|---|---|---|
| `p2v5c_common.py` | 공통 | `511c03bf23171a22961917aa5ec898a566ea6584631a6338a9a0508184c1b70d` |
| `p2v5c_stage1.py stage1` | H-10, H-9(main·pressure_only) | `e419475980ee217d4519e19c7fed7afaeb9a3cdfcb35224ebd81e46877b45562` |
| `p2v5c_grid.py grid` | H-9(격자 768, V0 짝, 계열 𝓕) | `68d7359db7b2e580686ae98499629890cf613a04801c2644fe758a1a4d5d642b`(rev4 판과 같음) |
| `p2v5c_noise.py noise` | H-6, H-8 | `8f15b56ef5f6cf8e7762032aaebbbde62a80655f8707c8a8801eed175fca8520` |
| `test_p2v5c.py` | 자체 시험 23개 | `4244968efd346cf3eca81575b6ecc5ca37e41c02335fcbec5d4603fa65883694` |

## rev5·rev6 반영

| 규칙 | 반영 | 함수 |
|---|---|---|
| R5-C1 | 판정기 출력에 없는 L1 게이트 개수(지금 `settings_mismatch`)는 경로 2가 센 값이 판정 값이다. 출력에는 `"대조 대상 없음"`으로 적고 판정 불가로 두지 않는다 | `noise.cmd_noise` |
| R5-C2 | 하위 항목으로도 13.2로도 설명되지 않는 S-4 실패는 실패다. 판정기 S-4 `flags`에 기존 FLAG 꼬리표(`S4_…`)가 있으면 그 FLAG로 둔다 | `noise.line_grade` |
| R5-C3 | seedext 판정기 입력은 seedext 파일과 같은 설정의 `h8_noise_<설정>.json` 두 파일이다. 경로 2가 입력 파일을 따로 만들지 않는다 | `noise.cmd_noise` |
| R5-E | 판정기 조건 1은 `r79_sensor_judge.py`만 본다. 판정기가 import하거나 같이 쓰는 모듈(`s9/late_loc_rule.py`, `s8/r79_sensor_screen.py`, `s9/s9_slope_fix_candidates.py`, 러너 `s8/r79_L3L4_final.py`)은 `git diff --stat f46b5ab..GIT_AT_START`를 `judge_tool.related_modules_diff_stat`에 기록한다. "기록 전용 변경"인지는 판정서에서 판단한다. `r79_L3L4_final.py`의 판정 함수는 쓰지 않는다 | `noise.cmd_noise` |
| R6-C1 | SA-4 "정지 뒤 네 다리 ≥ F_min"은 F-9 `values.sa4.F_min_after_stop_N`의 네 다리 최소 ≥ 9,414.589 N으로 본다. F-9가 없으면 이륙 뒤 최소 ≥ F_min이 충분조건이고, 아니면 판정 불가다. "포화 차단 0"은 `values.pressure.saturation_leg_chunks` = 0이다(정의 확인은 G-S) | `stage1.sa4_rest` |

## 규칙 절 ↔ 함수

| 규칙 | 내용 | 함수 |
|---|---|---|
| v5 3 J1~J11, 개정 2 2.1, 개정 8 3.2·9 3, rev3 R3-C3~C8, rev4 R4-C5 | 줄마다 V0 짝 대비 | `p2_v5j.judge_pair`(import) |
| v5 2 P-6·P-7, R3-E5 Q-S4 | L2 = L1 해시 8행. 모든 L1이 V0와 같을 때만 P-7 | `stage1.check_p6_p7` |
| v5 6 S8, R3-E5 Q-S6, **R4-B1** | 조항과 SA-4 나머지 7항목. "정지 뒤 부상 0" = `values.sa4.lift_after_stop_ms` 네 다리 모두 0. 필드가 없으면 판정 불가. F-5 기록, H-5 | `stage1.f5_clause`, `stage1.sa4_rest` |
| v5 8 VB × L1, L-a~L-e, Q-S9 | 멈춤 / H-6 / `감도 큼` 기록(구분됨일 때만) | `stage1.l1_table`, `stage1.ls_conditions`, `stage1.ld_large` |
| v5 11 H-2·H-3·H-4·H-7·H-8·H-9, Q-S7·Q-S8 | VB J 실패(item8 포함), R12, 리밋 사이클, 대체 n_late, S7 분류·FL 가드 주기, 이륙 뒤 잘림 | `stage1.cmd_stage1`, `stage1.fl_guard_cycle` |
| v5 13.1 Q-S5, 13.3, 13.4 | 완전 역순만 실패(H-11), `FLAG_overlap`, `unit_status` | `stage1.item8_order`, `stage1.overlap_record`, `stage1.pressure_only_record` |
| 개정 6 #9, 436.8 5.1·RV1-12·R3-F1·Q-S10 | `m2_law` r5. 묶음별 줄 수 S-15 | `stage1.m2_law_check`, `stage1.split_lines` |
| 명세 342.3 | r67 행 관문 재계산, 기록 관문과 대조 | `grid.gates_p2` |
| R3-E1, **R4-B4** | V0 표본 `resume_k1/h9_grid_v0_sample/<stem>.json`. 한 작업 = 저장 파일의 `results[]` 항목 하나(파일마다 첫·마지막). 그 항목의 모든 run 해시가 같아야 "같음"이다. 8작업이 모두 같으면 저장 V0를 쓰고, 아니면 `h9_grid_v0/` | `grid.sample_jobs`, `grid.v0_pair` |
| v5 10 격자 | 통과→실패 0, FAULT 0(H-10) | `grid.cmd_grid` |
| 개정 5 5.2, R3-E2, **R4-B5** | 𝓕 두 관문만의 통과→실패가 있으면 `h9_family_F.jsonl`의 `event` = FS24 64줄로 R-1~R-4를 판정한다. 다른 사건 줄은 빼고 수만 적는다. 원시 필드가 없으면 줄의 기록 `gates`를 쓰고 수를 적는다 | `grid.family_f_rule` |
| **R4-A2 안 c** | 잡음 S-1~S-6과 L1 게이트의 항목 값은 경로 2가 `r79_sensor_judge.py judge`·`judge-merged … --s4-late-loc`를 직접 실행해 얻는다. 출력은 `--judge-dir`에 쓴다. 조건 1(`git log f46b5ab..GIT_AT_START -- r79_sensor_judge.py` 0커밋, 아니면 S-11)을 확인하고 도구 sha256을 적는다. 경로 1 출력은 읽지 않는다 | `noise.run_judge`, `cmd_noise` |
| R3-E3 재집계, R4-A2 조건 4 | 판정기의 항목 행(`runs[].rows.S-1…S-6`)으로 줄 등급을 경로 2가 다시 만든다. S-1·S-2·S-3·S-5·S-6은 `ok`, S-4는 하위 항목(`fail_misfire_new`, `miss`, `recontact_new` 실패, `loc_minus_off_s` > T_lim이면 경로 2의 419.8 재계산)으로 본다. 판정기의 `pass`·표·결론은 쓰지 않고, 다른 줄 수만 적는다 | `noise.line_grade`, `noise.grade_set` |
| **R4-B2** | 419.8 조건 5: 첫 DONE = `base.t_done_s`(None = DONE 없음), 최종 LOC = `base.t_loc_final_s`. `base.phase_path`의 첫 `done`과 다르면 S-11 | `noise.late_loc_conditions` |
| **R4-B3** | L1 게이트 네 개수를 실행 기록에서 센 값과 판정기 출력(`errors`, `unmatched`, `settings_mismatch`, `reference[].false_loc`)을 함께 적는다. 다르면 S-13(판정 불가) | `noise.l1_gate`, `noise.l1_gate_judge` |
| v5 10 L2·L3, rev3 | S1 전방 제외, CP 두 근(> 3 %면 H-10), L3 기록(실패 수, CP, 대체 행 수, n_late) | `noise.cmd_noise` |
| 개정 6 9 | seedext: 판정기 입력 = seedext + 잡음 파일의 같은 사례 L1(경로 2 폴더에 씀). k/25, CP, Fisher 단측, 문구 두 가지. 시드 0~4 해시(H-15) | `noise.seedext_with_l1`, `noise.seedext_record`, `noise.seedext` |
| **R4-B6** | H-6 등급: J-P3·J9·H-7 멈춤, 같은 사례 L1에 없던 FAULT 이름 = 미달, 줄 등급 판정 불가 = 판정 불가, L3 실패 수 기록 | `cmd_noise` |
| R3-E4 | r79 결과 최상위 `commands_sha256`만. 없으면 `기록 불완전` | `noise.h` |

## 실행 예

```powershell
$d = '<repo>\06_analysis\02_control\verif_matrix\v5_resume_4368\path2_v5c'; $r = '<repo>\06_analysis\03_hydraulic\coupled\v5\resume_k1'
$c = 'C:\ProgramData\miniforge3\Scripts\conda.exe'
& $c run -n dynamics-dev python -I -B "$d\p2v5c_stage1.py" --out <o>\h10_h9s.json stage1 --h9 "$r\h9_stage1.jsonl" --h10 "$r\h10_reuse_rerun.jsonl" --t4h-root <H-10 T4h> --overlap-ta "$r\h10_overlap_t_a.json"
& $c run -n dynamics-dev python -I -B "$d\p2v5c_grid.py" --out <o>\h9_grid.json grid --vb <stem>="$r\h9_grid\<stem>.json" (4개) --v0-stored <stem>=<저장 V0 c4g2_only/grid> (4개) --v0-sample <stem>="$r\h9_grid_v0_sample\<stem>.json" (4개) [--v0-new <stem>="$r\h9_grid_v0\<stem>.json"] [--family-f "$r\h9_family_F.jsonl"]
& $c run -n dynamics-dev python -I -B "$d\p2v5c_noise.py" --out <o>\h6_h8.json noise --noise-vb "$r\h8_noise_VB.json" --noise-v0 "$r\h8_noise_V0.json" --h6 "$r\h6_dg3_v4on.json" --seedext-vb "$r\h8_seedext_VB.json" --seedext-v0 "$r\h8_seedext_V0.json" --judge-dir <o>\r79_judge --git-at-start <GIT_AT_START>
& $c run -n dynamics-dev python -I -B -m pytest -q -p no:cacheprovider --basetemp <scratch>\pt "$d\test_p2v5c.py"
```

## 동작 확인 (저장 기준선 = 옛 태그·LAS-b 전, 판정 아님, rev4 판)

| 도구 | 결과 |
|---|---|
| noise | 판정기 조건 1: `r79_sensor_judge.py`(sha `6c72b785…`)는 `f46b5ab..HEAD` 0커밋이다. 판정기 4회 실행, 모두 종료 0. L1 게이트 개수는 경로 2와 판정기가 같다(0/0/0, 판정기 출력에 `settings_mismatch` 키 없음). 재집계: L2 실패 5/835(CP 1.25 %), L3 10/501, FLAG 28(`S4_late_loc`). dg3 L3 실패 9는 개정 8 7.1 표의 "L3 9"와 같다. 판정기 `pass`와 다른 줄은 1. seedext 재집계는 `ref|J2|top|Fs0` VB 16/25 대 V0 1/25(Fisher p 5.3e-6, "의심" 문구). 옛 태그라 J-P3가 판정 불가 → H-6·H-8 판정 불가 |
| grid | 저장 V0를 표본으로도 넣으면 8/8 같음 → 저장 V0 짝(경로 확인). 𝓕 통과→실패 2건, `--family-f`가 없어 판정 불가 |
| stage1 | 앞 판과 같다(SA-4 부상 필드가 없어 S8 판정 불가) |

- 저장 기준선 seedext 값은 옛 제어기 결과의 동작 확인일 뿐 436.8 판정이 아니다.
- rev6 판으로 다시 돌린 결과:
  - 판정기 4회 모두 종료 0이다.
  - R5-C3 입력으로 바꾼 뒤에도 seedext 재집계는 같다(`ref|J2|top|Fs0` VB 16/25 대 V0 1/25, slope 3/25 대 0/25).
  - R5-E 기록: `r79_sensor_screen.py`는 `f46b5ab..HEAD` 사이 15줄 추가가 있다. 나머지 세 파일은 차이가 없다. `r79_L3L4_final.py`도 차이가 없다. rev5가 적은 `cf88ea8`이 이 브랜치의 조상이 아니기 때문이다(확인 필요 Q-R11).

## 확인 필요

| # | 내용 | 처리 |
|---|---|---|
| Q-R8 | 판정기 출력에 `settings_mismatch` 키가 없다(저장 기준선으로 확인). R4-B3 대조의 넷째 개수 | 키가 없으면 그 개수는 대조에서 빼고 `None`으로 적는다 |
| Q-R9 | S-4 항목 `ok` 거짓을 하위 항목(`fail_misfire_new`, `miss`, `recontact_new`, 시간 조항)이 설명하지 못하는 줄 | 보수 쪽으로 실패로 두고 사유를 적는다 |
| Q-R10 | (rev5 R5-C3로 닫힘) seedext 판정기 입력 = seedext 파일 + 같은 설정 잡음 파일 | 시드 0~4는 잡음 L2 줄과 키가 같다. 판정기 출력에서는 같은 키의 마지막 줄(잡음 파일 쪽)을 읽는다. H-15가 두 줄의 해시가 같음을 확인한다 |
| Q-R11 | R5-E는 `r79_L3L4_final.py`에 `f46b5ab` 뒤 커밋 `cf88ea8`이 있다고 적었다. `cf88ea8`은 있지만, 이 브랜치 HEAD(master d581df4 위)의 조상이 아니다(`git merge-base --is-ancestor` 거짓). 그래서 `f46b5ab..HEAD`에 그 파일의 차이가 없다. seedext `--keys-file` 옵션이 아직 master에 없을 수 있다 | 기록만 한다. 판정서에서 `GIT_AT_START`로 다시 센다 |

## 독립성 공개 (436.8 9.2)

- 규칙:
  - 436.8 원판·rev1·rev2 전체, rev3(머리·R3-1·C·E·F·G1·G10·9), rev4(머리·R4-0·A·B·9).
  - v5 기준 원판과 개정 1~11의 해당 절, `m1_criteria.md` 38~40행.
  - 명세 342.1~342.3, 405~407.1, 419.8·419.8.1, 423.1·423.4, 11025·11980행.
- 원 규칙이 지정한 판정 도구 `r79_sensor_judge.py`(R4-A2 안 c, 경로 2가 실행):
  - 머리 docstring(1~50행)과 `main`(773~822행)만 읽었다. CLI를 알기 위해서다.
  - 판정 함수 본문은 읽지 않았다.
  - 출력은 이 작성자가 직접 만든 것만 읽었다(키 구조).
- 같은 경로 2(dynamics-expert): README, `p2_4368.py`의 공통 부분, `p2_v5j.py`(bf52c89 판) 1~350행과 `main`, rev3·rev4 판의 함수 목록.
- 원 데이터(구조·식별 필드, 동작 확인용): 저장 `v5/main.jsonl`·`pressure_only`·`item8`·`overlap`·`u9_targeted`·`overlap_t_a.json`, `grid_vb/`, `c4g2_only/grid/`, `noise_*`, `seedext/`, `dg3/dg3_v4_on.json`.
- 보지 않은 것:
  - 경로 1 도구: `resume4368_judge.py`, `u3_judge_k1.py`, `resume_k1_*`, `gs_check_*`·`chrono_rows_*`, r67·r69·`las_t3_dg3` 판정 함수와 러너, `dg3v4_judge`, `run_v5.py`, 이전 단계 판정 스크립트.
  - 경로 1이 만든 r79 판정 출력 전부, 저장 r79 판정 파일(`s8/rev79/*judgement*`).
  - 이전 단계 다른 작성자의 경로 2 도구, `seedext_check.json`, `g0_compare.json`.
