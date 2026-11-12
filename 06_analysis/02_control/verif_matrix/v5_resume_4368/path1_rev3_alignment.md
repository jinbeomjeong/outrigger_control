# 436.8 경로 1 판정기 ↔ rev3·rev4 정의 대조 (읽기 전용 대조, 결과 전)

- 작성: python-expert, 2026-11-13. 대상 규칙: rev3 `v5_resume_4368_rules_rev3.md`(dad8dfa6), rev4 `v5_resume_4368_rules_rev4.md`(7ea87a30, rev3보다 우선).
- 대조 기준 코드: worktree `worktree-agent-ac17a920b9079a929`, 커밋 `d4815d6` + master `136b455` 병합(`fccc037`). 이 대조를 위해 판정기 코드는 **고치지 않았다**.
- 표의 판정 칸은 세 가지다. **같음** = 판정기 코드가 정의 문장과 같은 값을 낸다. **다름** = 정의와 다른 값 또는 범위를 낸다(어떻게를 적음). **코드 없음** = 그 정의를 계산하는 코드가 판정기에 없다.
- 읽은 것: 아래 표의 판정기 파일(함수 단위), `v5_resume_4368_rules.md` 9.1 경로 표, `las_p5r4_k1_rules.md` 52행(봉인 판정 도구 목록), `u3_u6_rerun_rules_rev2.md`, `las_targeted_rules_rev3~rev5.md`, `d1_selection_rules_interp.md` 3행. 저장 결과의 값은 읽지 않았다.
- **대조하지 못한 범위**: R3-G(Chrono 경로 1 몫) 가운데 G3·G4·G5·G6·G8·G10은 `run_S9.py`·`run_S8C.py` 판정 블록 전체를 읽어야 해서 이번에 대조하지 않았다(표에 "미대조"로 적음).

## 1. 판정기와 봉인 상태

| 묶음 | 원판 9.1의 경로 1 | 실제 판정기 파일 | 봉인 상태 | 고칠 때 |
|---|---|---|---|---|
| H-1·H-2 | `run_v5.py d1` 판정 블록 + `d1_select.py` | `04_scripts/04_hydraulic/coupled/d1_runs.py`(`judgement`), `d1_select.py` | sha 봉인 목록에 없다. `d1_selection_rules_interp.md`가 구현 커밋 `21f7d65`를 적었을 뿐이다 | 원판 9.1이 지정한 도구다. 고치면 rev 문장에 적고 `git_at_start` 이전 커밋으로 넣는다(A-5) |
| H-3·H-4 | 개정판 `u3_judge` | `u3_judge_k1.py`(436.8 개정판) | `u3_judge.py`는 봉인 도구다(`las_p5r4_k1_rules.md` 52행). `u3_judge_k1.py`는 원판 7.1 "개정판은 태그 상수와 입출력 경로만 다르다(그 밖 코드 차 0을 `git diff`로 보인다)"에 묶여 있다(시험 `test_u3_judge_k1_differs_only_in_tags_and_paths`) | 판정 논리를 바꾸면 7.1 문장에 어긋난다. **새 파일(예: `u3_judge_k1r3.py`)과 rev 문장이 필요하다** |
| H-5 | 각 판정 도구 | `06_analysis/03_hydraulic/coupled/v5/paper_runs/scripts/u9_judge.py` | 봉인 목록에 없다. 입력 경로가 저장 파일로 고정돼 있다(`V5 = …\v5`, `u9_targeted.jsonl`·`p3_hash.jsonl`·`main.jsonl`) | 지금 그대로는 436.8 출력(`resume_k1/…`)을 읽지 못한다. 436.8용 판(입력 인자)이 필요하다 |
| H-6·H-8 | 각 판정 도구 | `r79_L3L4_final.py judge` / `r79_sensor_judge.py judge`(rev4 R4-A2 안 c의 지정 도구) | 사전 sha 봉인 없음. rev4 R4-A2 조건 1: `git log f46b5ab..GIT_AT_START -- <파일>` 0커밋 | `r79_sensor_judge.py`는 0커밋(확인). `r79_L3L4_final.py`는 `cf88ea8`(이 worktree, `cmd_run`만 바뀜, `cmd_judge` 그대로)이 있다. 2절 E행 참고 |
| H-9·H-10 | 각 판정 도구 | `v5/paper_runs/scripts/judge_stage1_r5.py`(v5 1단계 판정값, J1~J11) | 봉인 목록에 없다. 입력·출력 경로가 저장 파일로 고정돼 있다(`main`·`item8`·`overlap`·`pressure_only`, 저장 `overlap_t_a.json`) | 436.8 출력을 읽는 판정기가 **없다**. 새 판(입력 인자 + 아래 차이 반영)이 필요하다 |
| H-0 | `las_judge`/H-7′ 모듈 | `las_t3_judge.py`(`las_judge.py --stage T-3`), `las_h7.py` | 사전 sha 봉인 없음. 실행 때 줄마다 도구 sha256을 정체성으로 기록한다(rev3 K-0) | 고치면 K-0 정체성 기록이 바뀐다. 원 규칙(rev5)이 지정한 도구라 rev 문장이 필요하다 |
| C-1~C-5 | 행 판정기(`result.json` 판정 블록) | `run_S9.py`(`p3b_records`, `p34_judgement_window`, `late_loc_revoked_record`), `run_S8C.py` | 사전 sha 봉인 없음(러너 안 판정 블록) | 러너를 고치면 Chrono 행이 바뀐다. cad-expert 몫 |

## 2. 항목별 대조

### A. D-1 (`d1_runs.judgement`, `d1_select.py`) ↔ R3-A1~A3, R4-C1·C3

| 항목 | 판정 | 내용 |
|---|---|---|
| R3-A1 G-3 예외 범위 | 같음(면제) / 다름(기록) | `gate_g3`는 `slope == "fup-rec"`인 줄을 면제한다. `fup-rec`는 `SOIL_SLOPES`(H-S-0)에만 있고 `ASSUMED_BOUNDARY` 태그와 같은 집합이다. VB·V0, 모든 ε, 모든 오거 단계가 포함된다. **다름**: "가정 경계 미성립" 기록과 질문은 S2 선별(`select_soft_slope`)에서 `fup-rec`가 `fail`일 때만 나온다. G-3이 면제한 다른 `fup-rec` 줄(VB `fail`, V0 `pass`)에는 그 기록이 없다 |
| R3-A2 층 1(H-R 다섯 항목) | 같음(경로 1 값) | `_d8_items`가 `F_min`·끝 자세·READY·이동 180 bar·FAULT 0을 `d1.items`로 낸다 |
| R3-A2 층 2(강등·`allowed_stop`) | 다름 가능(확인 필요) | `judgement`에는 강등 단계가 없다. `fail_items` = 거짓 항목 전부다. `allowed_stop`은 `TAG_STROKE_STOP_ALLOWED` + `stroke_limited_stop`일 때 적용한다(같음). 강등은 하네스 판정 안에서 이미 반영된 값을 쓴다: slope 경로는 행 `pass`, g6 경로는 r72 `gates`. g6 경로에서 `G6-7_preloc`이 거짓이면 r72 쪽에서 377 강등이 반영됐는지 여부에 따라 `fail`이 된다. 강등을 따로 적용하는 코드는 없다 |
| R4-C3 `d1.demoted_items` | 코드 없음 | 필드가 없다(F-2, 3절에서 구현). 위 구조 때문에 "거짓 항목 − `fail_items`"는 정의상 늘 빈 집합이다 |
| R3-A3 READY 기준점 | 같음(값) / 코드 없음(원점) | t_READY = `values.times.t_first_ready_s`(폐루프 시작 기준)이고 `d1.t_ready_s`도 같은 값을 그대로 쓴다. 원점 확인(CHECK 시작 ≤ 0.1 s)은 코드가 없다. rev4 R4-C1: F-1 필드가 있으면 그것으로, 없으면 하네스 정의로 정한다 |
| R4-C1 `values.times.t_check_start_s` | 코드 없음 | F-1, 3절에서 구현 |

### B. U-3·U-6 (`u3_judge_k1.py`) ↔ R3-B1~B7, R4-C2

| 항목 | 판정 | 내용 |
|---|---|---|
| R3-B1·B6 정착 v2 재판정 | **다름** | ① slope·h6·x426b는 `s9_settle_rejudge.rejudge_record(entry, baseline)`으로 다시 판정한다. 기준은 저장 v4 재판정 파일(`baseline`)의 정착 v2이고, 그 실행 자신의 `settle_v2` 기록이 아니다. ② **h9와 D는 v2 재판정을 하지 않는다**(h9는 레코드 `verdict`, D는 `s9_soil_slope` v1 `verdict`). R3-B6은 둘 다 v2 대상으로 정한다. ③ `settle_v2.status`가 `no_table_check`이면 "해당 없음", `error`이면 판정 불가, 블록이 없으면 판정 불가로 처리해야 하는데 그 코드가 없다. ④ `gate`(`judged`·`settle_check_fail`·`record_only`)를 읽는 코드가 없다. ⑤ D-1 재사용 줄의 `u3.settle_v2`를 읽는 코드가 없다 |
| R3-B7 H8 시작 틈 목표 | 다름 | D는 v2를 쓰지 않는다. `s9_settle_rejudge.corrected_check`는 표 목표만 쓴다. 기록 `settle_v2`(b9e9d2d)는 시작 틈 목표를 쓴다(정의와 같음). 판정기는 그 기록을 읽지 않는다 |
| R4-C2 단위·허용·표 목표 | 코드 없음 | 판정기는 `tolerances`·`table_sha256`·`table_gap_target_mm`을 대조하지 않는다. F-5 필드는 3절에서 구현 |
| R3-B2 연구 B·C·D 셈 | 다름(작음) | C는 `fin_x426_C.json`(키 필터 패드 B, 34), D는 `fin_x426_D.json`(33)으로 같다. B는 입력 파일이 `rev85/finB2_x426b_rejudged.json`이다(규칙은 `finB2_x426b.json`). 또 `entries_of(payload, "x426b")`가 레코드 `suite`로 거른다. R3-B2는 "suite 이름은 셈에 쓰지 않는다"이다. 두 파일의 키 집합이 같은지는 확인하지 않았다 |
| R3-B3 재사용 필드 | 같음(개수) / 코드 없음(대조) | 재사용 수 = `reuse == "d1"`인 레코드 수(같음). `meta.v5.reuse_d1.<suite>.reused` 개수와의 대조, `d1_key`가 H-1 출력 한 줄을 유일하게 가리키는지 확인하는 코드는 없다 |
| R3-B4 C2 안전 종료 | 같음 | `_u6_counts`가 `official_verdict == "stroke_limited_stop"`을 센다. `official_verdict_strict`는 쓰지 않는다. 제어기별로 따로 센다 |
| R3-B5 IND_LAS 관문 | 코드 없음(이 판정기) | `u3_judge_k1`에는 없다. 경로 1 도구 `resume4368_judge.py ind-las`(d4815d6)가 b5 기록 전용 필드 `liftoff_slow_events`로 센다 |

### C. v5 판정기 (`judge_stage1_r5.py`, `u9_judge.py`) ↔ R3-C1~C8, Q-S1~S10, R4-B·C

공통: 두 판정기 모두 저장 파일 경로를 코드에 박아 두어 436.8 출력을 읽지 못한다(1절). 아래는 판정 정의의 차이다.

| 항목 | 판정 | 내용 |
|---|---|---|
| R3-C1 U-9 H0 ① 기준 줄 | 다름 | `u9_judge`는 저장 `p3_hash.jsonl`과 대조한다(`H0-1 p3_hash`). R3-C1은 같은 커밋 H-10 출력의 main VB 같은 (사례, ε) 줄이다 |
| R3-C2 H-5 등급 | 같음(대체로) | 0.85 VB·V0의 T1과 H0, 0.80의 T3·T4와 분류 A~D를 따로 낸다. "C면 묻기"는 사람 처리라 코드 몫이 아니다 |
| R3-C3 J1 | **다름** | 비사건 행: V0 `pass`/`stroke_limited_stop`이고 설정 등급이 V0와 **다르면** J1 실패다. 그래서 `pass` ↔ `stroke_limited_stop` 이동도 실패로 센다. R3-C3은 이를 기록으로 정하고, S8 기대 분류만 예외로 둔다 |
| R3-C4 J2 F_min | 다름 | 문턱 `F_MIN = 9.415`(kN, 반올림)과 `SPEC_RIGID = 14.415`(kN)을 쓴다. 정의는 9,414.589 N, 14,414.589 N이다(0.411 N 차). 사건 행은 `F_after_event`(사건 뒤)를 쓴다. R3-C4는 강체 사건 행에 E-3(창 뒤 1 ms ≥ F_min = `min_F_after_W`)를 쓴다(값 출처가 다름, 확인 필요) |
| R3-C5 J3 | 다름(일부) / 코드 없음 | 판정 쪽(S1~S5·S7, 첫 READY ≤ 100 s)은 같다. 강체 R1~R11의 FLAG(경사 120 s / 평지 90 s)는 코드가 없다. 경사 판별 입력인 바닥 각도 줄에 없다. rev4 F-3은 3절에서 구현 |
| R3-C6 J7 | **다름** | 사건 이름이 `run_m1.event_names`(`name.split(":")[0]`, 첫 구획만)다. 그래서 비수치 구획(다리·사유)도 버려진다. R3-C6은 수치 구획만 떼고 나머지를 남긴다. `WARN_ROD_PRESSURE_FALLBACK` 사유·시각 비교는 `fallback_events`로 따로 모으지만 J7 판정에는 쓰지 않는다 |
| R3-C7 J11 | 다름 | `n_late`가 None이면 판정하지 않고 건너뛴다(`J11_VB_skipped_rows` 기록). 정의는 대체 다리가 있는 줄의 None을 판정 불가로 둔다 |
| R3-C8 J-P3 | 코드 없음(이 판정기) | J-P3 판정은 `v5_rerun.j_p3_status`·`p3_*_check`에 있고 `judge_stage1_r5`에는 없다. 개정 9 3.2 표 #1~#5를 R3-C8의 두 입력 규칙(T4h `rod_pressure_Pa`, 구성 정의)으로 고른다는 대조는 하지 않았다 |
| Q-S1 `failed_rows` | 같음 | 등급은 `harness_class`로 판단한다 |
| Q-S2 S8 J6 | 같음 | 기준 `att_last5`가 None이면 J6를 보지 않는다 |
| Q-S4 P-7 | 다름(일부) | L1 줄 가운데 V0와 해시가 같은 키 목록만 기록한다. "모든 L1 줄이 같을 때만 위반(멈춤)"이라는 판정 코드는 없다 |
| Q-S5 13.1 순서 | 코드 없음 | `item8_values`만 있다 |
| Q-S6 SA-4 | 다름(일부) | S8 줄의 `same_cycle`·`stroke_end`·`F_after`·`p_move`를 기록한다. READY 0, 정지 뒤 부상 0(rev4 F-4), 포화 0은 코드가 없다 |
| Q-S7 FL 가드 시각 | 코드 없음 | `H8_S7`은 등급·가드 시간만 기록한다 |
| Q-S8 item8 | 같음 | item8 VB를 같은 위상 V0로 `J_fails` 적용한다 |
| Q-S9 L-d | 다름 | `|dF| ≥ 1 kN` 또는 `|dT| ≥ 1 s`이면 "큰 변화"로 센다. 위상 산포 정의(m1 5절 "구분됨")가 아니다 |
| Q-S10 U-9 VB 28줄 | 코드 없음 | `judge_stage1_r5`는 main만 읽는다(H-10 셈 없음) |
| R4-B6 H-6 등급 | 코드 없음 | `r79_L3L4_final.py judge`는 L3·L4 CP 판정이다. H-6(개정 8 #6) 항목 판정 코드는 없다 |

### D. T-3K (`las_t3_judge.py`, `las_h7.py`) ↔ R3-D1~D4, R4-C4

| 항목 | 판정 | 내용 |
|---|---|---|
| R3-D1 dg3 폴더 | **다름** | 기대 태그·해시 비교의 폴더를 키 목록 항목 `entry["folder"]`로 정한다(`expected_tag`). R3-D1은 기록의 `two_pressure.extend_start_rule`(`tracked_bound` = v4_on)로 정한다. 기록의 규칙 값은 K-3에서 대조만 한다 |
| R3-D1 키 접두 | 같음(경로 1) | 줄 키는 `t3.line_key`(러너가 만든 키)다. 경로 1 안에서는 접두 문제가 없다 |
| R3-D2 R-0 V0 태그 | 같음 | `expected_tag`가 R-0 V0를 None으로 둔다. 키가 없거나 null이면 같다. 빈 문자열이나 다른 문자열은 다르다 |
| R3-D3·R4-C4 K-0 | 다름(필드) | `identity_problems`는 `IDENTITY_KEYS = (git_head, sha256, c2_sha256, threads, workers, affinity)`를 줄과 헤더 사이에서 대조한다. R4-C4는 `.identity.json`의 `start/end.head`, `is_clean`, `status_porcelain`, `code_diff_sha256`, `c2_sha256`, `tools_sha256`, `env.*`, 금지 env를 정한다. T-3K 출력이 `.identity.json`을 쓰는지, 필드 이름이 맞는지는 확인하지 않았다(H-0 G-S 몫) |
| R3-D4 K-6 비교 허용 | 다름(경계만) | `las_h7`·`las_judge`의 READY +5.0 s, 행정 +0.001 m를 `>`로 비교하고 10⁻⁹ 허용이 없다. 원 규칙에 허용이 없으므로 R3-D4는 7.6의 10⁻⁹를 쓴다. (X, X + 10⁻⁹] 구간의 값만 결론이 갈린다 |

### G. Chrono 행 판정(경로 1 몫) ↔ R3-G, R4-A

| 항목 | 판정 | 내용 |
|---|---|---|
| R3-G7 `window_short` | 같음 | `p34_judgement_window`: 창이 짧고 값이 안이면 `verdict = flag`, `within_0p2 = False`, `absmax_within_0p2_record`는 값 판정이다. READY·크리프 정지가 없을 때는 `fail` + `window_short` 꼬리표다(R3-G7은 이 경우를 따로 말하지 않는다) |
| R3-G9 P3-4 장착 몫 | 같음 | 판정값에 장착 몫을 더하지 않는다. `sensor_allowance_left_deg` = 0.2 − 0.02 − 값 |
| R3-G12 조건 6 | 같음 | `late_loc_revoked_record`의 `6_total_delay`: t_LOC_fin − t_off ≤ (1 + n_revoke) T_lim(+eps) |
| R3-G5 D8 이륙·P3 t_D | 같음(P3) / 미대조(D8) | P3-3은 `crawler_departure`(0.01 W, 0.1 s)의 t_D다. D8 t_lift 조작 정의는 대조하지 않았다 |
| R3-G3·G4·G6·G8·G10 | 미대조 | 판정 블록 전체 대조가 필요하다 |
| R3-G2·G11·G13, R4-A2·A3 | 해당 없음 | 경로 2 입력·배정·읽기 규칙이다. 경로 1 코드 몫이 아니다 |

### E. H-6~H-10 경로 1 도구 (`resume4368_judge.py`, d4815d6) ↔ rev4

| 항목 | 판정 | 내용 |
|---|---|---|
| R4-B4 격자 V0 표본 | **다름** | `grid-v0-sample`은 표본 결과마다 첫 run만 비교한다(rev3 R3-E1 문장). R4-B4는 "그 항목의 모든 run 해시가 같아야 같음"이고, (stem, key, event, offset)으로 맞춘다. 이 대조 뒤 고쳤다(3절) |
| R4-B5 `h9_family_F.jsonl` 꼴 | 다름(필드) | 수집기가 `setting`·`key`와 run 필드를 쓰지만 `v5_setting`·`controller_tag`가 없다. 이 대조 뒤 고쳤다(3절) |
| R4-A2 조건 1(도구 0커밋) | 확인 필요 | `r79_sensor_judge.py`·`chrono_t45_replay.py`·`contact_replay.py`·`s9_soil_event_screen.py`는 f46b5ab 뒤 0커밋이다. R4-0이 같이 조회한 `r79_L3L4_final.py`는 이 worktree에 `cf88ea8`(`--keys-file`, `cmd_run`만)이 있다. 경로 2가 `r79_L3L4_final.py judge`를 쓰면 조건 1이 거짓이 된다. 또 `r79_sensor_screen.py`(`24495d8`·`d4815d6`)와 `s9_slope_fix_candidates.py`(`b9e9d2d`)는 지정 도구가 import하거나 같이 쓰는 모듈이다(조건 1은 파일 단위라 문장상으로는 걸리지 않는다) |

## 3. 정리 (메인 세션 결정용)

- **두 경로가 갈릴 가능성이 큰 차이**(S-13 위험)
  1. U-3 정착 v2: `u3_judge_k1`이 실행 기록 `settle_v2`를 쓰지 않는다. h9·D는 v2가 없다.
  2. J1: `pass` ↔ `stroke_limited_stop` 이동을 실패로 센다.
  3. J7: 사건 이름의 비수치 구획을 버린다.
  4. J11: `n_late` None을 건너뛴다.
  5. J2: F_min을 반올림했다.
  6. T-3K dg3 폴더를 키 목록에서 정한다.
  7. U-9 H0 ① 기준 줄이 저장 `p3_hash.jsonl`이다.
- **436.8 출력을 읽는 판정기가 없는 묶음**: H-9·H-10(`judge_stage1_r5`), H-5(`u9_judge`). 둘 다 저장 경로가 박혀 있다.
- **봉인 때문에 새 파일이 필요한 곳**: `u3_judge_k1.py`(원판 7.1의 "태그·경로만 다름" 조건). 나머지는 sha 봉인이 없다. 다만 원 규칙이 지정한 도구라 고치면 rev 문장이 필요하다.
- 이 대조 뒤 이어서 한 것(같은 worktree, 3절 커밋):
  - rev4 F-1~F-5 기록 필드
  - G-S 확인 항목
  - R4-B4 표본 비교(모든 run)
  - R4-B5 𝓕 줄 필드
  - 판정기 정의 차이(위 1~7)는 고치지 않았다.
