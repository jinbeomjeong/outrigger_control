# 436.8 경로 2 — v5 기준 원 규칙 등급 재집계 (H-6·H-8·H-9·H-10)

- 규칙: 436.8 원판 `../../v5_resume_4368_rules.md`(`9019b405…`), rev1(`d9094fda…`), rev2(`497e4614…`), **rev3(`dad8dfa6…`, 봉인 2026-11-13 03:13:21, master 9ce2fdc)**. 원 규칙은 원판 부록 A의 `v5_criteria.md` + 개정 1~12b다.
  - 실행할 때마다 `p2_4368.check_seals`(원판·rev1·rev2·rev3, 부록 A 33개, R2-9·R3-F4 CRLF 정규화)와 이 폴더의 `check_rev3`(rev3 raw sha, `.sha256` 기록, LF·BOM 없음)로 확인한다.
  - 어긋나면 종료 2(S-1)다.
- 작성자: terramechanics-expert(경로 2, 사용자 결정 2026-11-13). 경로 1 도구를 만들거나 고친 적이 없다. 읽은 것은 아래 "독립성 공개"에 적었다.
- 환경: `conda run -n dynamics-dev python -I -B <도구> ...`. 표준 라이브러리, numpy(T4h npz), scipy(CP 두 근, Fisher 정확 검정)만 쓴다.
- 공통 CLI:
  - 인자: `--repo`(기본: 이 폴더에서 다섯 단계 위), `--out <JSON>`, `--p2-dir`, `--allow-import-sha`.
  - 종료 코드: 0(멈춤·실패·판정 불가 없음), 1(실패 또는 판정 불가), 2(멈춤 H-*·S-*·P-*, 규칙 sha 불일치, import sha 불일치 `P2-SHA`), 3(도구 오류).
  - stdout 마지막 줄은 ASCII JSON(`tool_sha256`, `common_sha256`, `status`, `exit`, `out_sha256`, `stop_codes`)이다.
- `.gitattributes`에서 이 폴더 전체를 `-text`로 둔다. 도구 sha는 LF 바이트 기준이다.

## import (복사하지 않음)

메인 세션 결정(2026-11-13)에 따라 J 항목(R3-C3~C8 포함)은 dynamics-expert 파일을 경로로 import한다. 그 파일은 고치지 않는다.
- 찾는 순서: `--p2-dir` → `../path2` → dynamics-expert worktree `agent-a2e81c57365f0d7bb`의 `v5_resume_4368/path2/`.
- sha가 다르면 종료 2(`P2-SHA`)다.

| 파일 | 고정 sha256(rev3 판, 2026-11-13 03:16·03:18 파일) | 쓰는 것 |
|---|---|---|
| `p2_v5j.py` | `ceb75ee9a6081b73e158a7db42cc11c9cfb6f9ccb4bae480775128a2f6616eac` | `judge_pair`(J1~J11 + J-P3, R3-C3~C8), `j_values`, `jp3`, `nrev_max_by_row`, `pair_key`, `row_key`, `rod_reading_from_t4h`, `tag_of`, `is_event` |
| `p2_4368.py`(`p2_v5j.core`) | `cf0b643c8293e8757b21e3627e9585319af1d2068b32dfd5a1b1612f6c5954de` | `check_seals`, `load_is_extend_start`, `Findings`, `t_ge/t_lt/t_gt`(7.6 허용 1e-9), `num`, `dig`, `read_jsonl`, `F_MIN_N` |

- 앞 판 고정값은 `p2_v5j` `559bd34f…`(bf52c89)와 `p2_4368` `1294dc4e…`였다.

## 도구와 sha256 (rev3 판, 각 묶음 첫 결과 전 고정)

| 도구 | 묶음 | sha256 |
|---|---|---|
| `p2v5c_common.py` | 공통(rev3 확인, import, CP) | `de03987d1fbb97f81f9d9eb827b4975317c683887e94e5f6dd503464f96d9a7e` |
| `p2v5c_stage1.py stage1` | H-10, H-9(main·pressure_only) | `dfa6094af3073ee12a1a2eae1db01261a0c969412a0e389defad67e312abd7da` |
| `p2v5c_grid.py grid` | H-9(격자 768, V0 짝, 계열 𝓕) | `44588bd1ecd38c5299530007aa7064744efb33d925c81f4450cac6d386015b65` |
| `p2v5c_noise.py noise` | H-6, H-8 | `3a6096da51637544c9316e3801099d62496910704b354da63046f0ba34556e76` |
| `test_p2v5c.py` | 자체 시험 21개 | `3af140e8d94e69268cdbde43c1954cce07dc8bd8ef614e65fd19ad337a981987` |

## 규칙 절 ↔ 함수

| 규칙 | 내용 | 함수 |
|---|---|---|
| v5 3 J1~J11, 개정 2 2.1, 개정 8 3.2·9 3, rev3 R3-C3~C8 | 줄마다 V0 짝 대비 | `p2_v5j.judge_pair`(import) |
| v5 2 P-6·P-7, R3-E5 Q-S4 | L2 = L1 해시 8행. 모든 L1이 V0와 같을 때만 P-7 위반 | `stage1.check_p6_p7` |
| v5 6 S8, R3-E5 Q-S6 | 조항(정지 뒤 최대 ≤ 정지 때 + 0.01 W)과 SA-4 나머지 7항목. 나머지가 하나라도 거짓이면 실패, 기록이 없으면 판정 불가. 조항만 실패하면 유량 켬은 F-5 기록(J1 실패를 세지 않음), 유량 끔은 H-5. VB 여유 < −6.92 kN 또는 정지 뒤 최대 > 14.21 kN이면 H-5 | `stage1.f5_clause`, `stage1.sa4_rest` |
| v5 8 VB × L1 표 | VB 실패면 멈춤 | `stage1.l1_table` |
| v5 8 L-a~L-e, R3-E5 Q-S9 | a·b·c·e 위반은 H-6. d는 \|E_r\| ≥ 1 kN·1 s ∧ 구분됨(\|E_r\| > S_r, 짝 차 부호 같음, `m1_criteria.md` 5)일 때 `감도 큼` 기록 | `stage1.ls_conditions`, `stage1.ld_large` |
| v5 11 H-2·H-3·H-4·H-7·H-9 | VB J 실패(item8 VB 포함, Q-S8), R12 V0 통과 수 감소, 리밋 사이클, 대체 $n_{late}$, 이륙 뒤 잘림 | `stage1.cmd_stage1` |
| v5 11 H-8, R3-E5 Q-S7 | S7 분류와 FL 첫 `WARN_LIFT_STROKE_LIMITED:` 주기(round(t/0.1)) | `stage1.fl_guard_cycle` |
| v5 13.1, R3-E5 Q-S5 | 완전 역순(상 > 중 > 하, 겹침 없음)만 실패(H-11). 그 밖은 FLAG | `stage1.item8_order` |
| v5 13.3·13.4 | `FLAG_overlap`·`unit_status` 기록 | `stage1.overlap_record`, `stage1.pressure_only_record` |
| 개정 6 #9 | `m2_law` `flow_limited_r5` | `stage1.m2_law_check` |
| 436.8 5.1·RV1-12, R3-F1, R3-E5 Q-S10 | 묶음별 줄 수 S-15(h9 908, h10 440). U-9 VB 28은 줄 수만 센다(등급은 H-5) | `stage1.split_lines` |
| 명세 342.3 | r67 행 관문을 기록 필드로 재계산하고 기록 관문과 대조 | `grid.gates_p2` |
| R3-E1(Q-E1 = A) | V0 짝. 8작업 표본(파일마다 첫·마지막 결과의 첫 run) 해시가 모두 같으면 저장 V0, 다르면 `resume_k1/h9_grid_v0/` | `grid.sample_jobs`, `grid.v0_pair` |
| v5 10 격자 | 통과→실패 0, FAULT 0(H-10) | `grid.cmd_grid` |
| 개정 5 5.2, R3-E2(Q-E2 = A) | 계열 𝓕 두 관문만의 통과→실패가 있으면 64실행으로 R-1(m 4)~R-4(m_Σ 6). 통과하면 H-10에서 빼고, 실패하면 H-10 멈춤 | `grid.family_f_rule` |
| R3-E3(Q-E3 = A) 재계산 | 수준 수, S1 전방 제외 n, CP 두 근, L1 게이트 개수, dg3 대체·해시, seedext 시드 0~4, 419.8 조건, J-P3, J9, H-7 | `noise.levels`, `noise.l1_gate`, `noise.cp_pair`, `noise.seedext`, `noise.late_loc_conditions`, `noise.run_checks` |
| R3-E3 재집계 | r79 관문 S-1~S-6 결과에 13.2·419.8(`S4_late_loc`), 423.1(새 `strict_fail`만 실패, chatter는 FLAG)을 적용해 줄 등급을 낸다. 그 등급으로 L2 실패 수·CP(> 3 %면 H-10), L3 기록, seedext k/25·CP·Fisher 문구를 만든다. 항목 목록은 출력 `TABLE_REAGG` | `noise.line_grade`, `noise.cmd_noise`, `noise.seedext_record` |
| R3-E4 | r79 결과 최상위 `commands_sha256`만 읽는다. 없으면 `기록 불완전`(멈춤 아님) | `noise.h` |

## r79 관문 입력 꼴 (`--gates LABEL=<json>`, LABEL: `noise_VB`, `noise_V0`, `H-6`, `seedext_VB`, `seedext_V0`)

이 도구가 정한 입력 계약이다. 경로 1 판정기 출력을 이 꼴로 옮기는 어댑터는 메인 세션이 정한다(확인 필요 Q-R1).
- 받는 꼴은 셋이다: `{key: {"S-1": bool, …, "S-6": bool, "s4_reasons": [...]}}`, `{key: {"gates": {...}, "s4_reasons": [...]}}`, `{"results": [{"key": ..., ...}]}`.
- `s4_reasons`에 쓰는 이름:
  - `time_clause`: LOC − 이탈 > $T_{lim}$. 419.8 다섯 조건이 모두 참이면 FLAG, 하나라도 거짓이면 실패, 기록이 없으면 판정 불가.
  - `recontact_strict_new`: 실패.
  - `recontact_chatter`: FLAG.
  - 그 밖의 이름: 실패.
  - 사유가 없으면 보수 쪽으로 실패다.

## 실행 예

```powershell
$d = '<repo>\06_analysis\02_control\verif_matrix\v5_resume_4368\path2_v5c'; $r = '<repo>\06_analysis\03_hydraulic\coupled\v5\resume_k1'
$c = 'C:\ProgramData\miniforge3\Scripts\conda.exe'
& $c run -n dynamics-dev python -I -B "$d\p2v5c_stage1.py" --out <o>\h10_h9s.json stage1 --h9 "$r\h9_stage1.jsonl" --h10 "$r\h10_reuse_rerun.jsonl" --t4h-root <H-10 T4h 폴더> --overlap-ta "$r\h10_overlap_t_a.json"
& $c run -n dynamics-dev python -I -B "$d\p2v5c_grid.py" --out <o>\h9_grid.json grid --vb grid_r67_main="$r\h9_grid\grid_r67_main.json" (… 4개) --v0-stored grid_r67_main=<저장 V0> (… 4개) --v0-sample grid_r67_main=<표본> (…) [--v0-new grid_r67_main="$r\h9_grid_v0\grid_r67_main.json" (… 4개)] [--family-f "$r\h9_family_F.jsonl"]
& $c run -n dynamics-dev python -I -B "$d\p2v5c_noise.py" --out <o>\h6_h8.json noise --noise-vb "$r\h8_noise_VB.json" --noise-v0 "$r\h8_noise_V0.json" --h6 "$r\h6_dg3_v4on.json" --seedext-vb "$r\h8_seedext_VB.json" --seedext-v0 "$r\h8_seedext_V0.json" --gates noise_VB=<…> --gates noise_V0=<…> --gates H-6=<…> --gates seedext_VB=<…> --gates seedext_V0=<…>
& $c run -n dynamics-dev python -I -B -m pytest -q -p no:cacheprovider --basetemp <scratch>\pt "$d\test_p2v5c.py"
```

## 동작 확인 (판정 아님, 저장 기준선 = 옛 태그·LAS-b 전, rev3 판으로 다시 돌림)

| 도구 | 입력 | 결과 |
|---|---|---|
| stage1 | 저장 main·pressure_only·item8·overlap·u9 VB를 h9 908 / h10 440 꼴로 묶음 | 줄 수 S-15 0. 옛 태그라 VB·LS J-P3가 판정 불가. S8 SA-4 "정지 뒤 부상 0" 기록 필드가 없어 S8 줄이 판정 불가(Q-R2). 옛 L1에서 H-7 |
| grid | 저장 `grid_vb/` + V0로 `c4g2_only/grid`(`--v0-new`로 줌) | 기록 관문과 재계산 관문 차이 0/768(앞 판에서 확인). 계열 𝓕 두 관문만의 통과→실패 2건 → `--family-f`가 없어 판정 불가(규칙대로 64실행 입력 필요) |
| noise | 저장 잡음·dg3·seedext, `--gates` 없음 | 수준 수 167/835/501, dg3 1 + 134, L1 게이트 개수 0/0/0/0, 저장 기록에 최상위 해시가 없어 해시 항목은 `기록 불완전`. 관문 입력이 없어 줄 등급은 판정 불가 |

## 확인 필요 (rev3 뒤 남은 것)

| # | 내용 | 이 도구의 처리 |
|---|---|---|
| Q-R1 | 경로 1 r79 판정기의 관문 결과(S-1~S-6, S-4 사유)를 위 `--gates` 꼴로 옮길 위치와 어댑터. R3-E3 재집계의 입력이다 | 입력이 없으면 판정 불가 |
| Q-R2 | SA-4 "정지 뒤 부상 0"(R3-E5 Q-S6)의 하네스 줄 기록 필드 이름. 저장 기록에는 없다 | 후보 `soil_stop_crawler.pad_lift_after_stop_ms`·`soil_stop_crawler.lift_ms_after_stop`·`values.lift_after_stop_ms`. 없으면 그 S8 줄은 판정 불가(규칙대로). G-S에서 확인 권고 |
| Q-R3 | 419.8 조건 5(LOC가 첫 DONE보다 먼저)를 r79 기록에서 읽을 첫 DONE 시각. 저장 r79 기록에는 `n_done_entries`만 있다 | `events`의 `first_done`·`done`·`phase:done`·`DONE` 이름을 찾고, 없으면 그 줄은 판정 불가 |
| Q-R4 | L1 게이트 개수 정의. 거짓 LOC = L1 `r79.crawler_at_loc_over_W` ≥ 0.01, unmatched = L1 짝(harness, case_index, inner)이 없는 L2·L3 줄, errors = `meta.n_errors` + `error` 항목, 설정 불일치 = `v5_setting` ≠ VB | 이 정의로 센다(가정) |
| Q-R5 | `--v0-sample` 파일 꼴 | 격자 꼴(`results[].runs[]`, run에 `commands_sha256`)로 받고 (stem, key, event, offset)로 맞춘다 |
| Q-R6 | `h9_family_F.jsonl` 줄 꼴 | 줄마다 `key`, `setting`(V0·VB), run(`run` 아래 또는 줄 최상위, `offset_s` 포함)으로 받는다 |
| Q-R7 | H-6 등급 | 135줄의 J-P3·J9·H-7 멈춤이나 줄 등급 판정 불가가 있으면 그것으로 정하고, 없으면 통과로 둔다. L2 1키는 H-8 CP에 들어가고 L3 134키는 기록이다 |

## 독립성 공개 (436.8 9.2, 이 도구를 쓰려고 읽은 것)

- 규칙: 436.8 원판·rev1·rev2 전체, rev3의 머리·R3-1·R3-C·R3-E·R3-F·R3-G1·R3-G10·R3-9. `v5_criteria.md` 전체, 개정 1·2 전체, 개정 3 2~5절, 4 2·4·5절, 5 2·4·5절, 6 2·9~12·14.5절, 8 2·3·7.4·8절, 9 2·3절, 10 1·3·4절, 11 1·2절. 개정 7·12·12a·12b는 머리 목록만 읽었다. `pressure_review/m1_criteria.md` 38~40행.
- 명세 `s6_control_spec.md`: 342.1~342.3, 405~407.1 앞부분, 419.8·419.8.1, 423.1·423.4, 11025·11980행.
- 같은 경로 2(dynamics-expert): `path2/README.md`, `p2_4368.py`의 머리·상수·도우미·`check_seals`·`main`, `p2_v5j.py`(bf52c89 판) 1~350행과 `main`, rev3 판의 함수 목록과 머리 주석.
- 원 데이터(구조와 식별 필드, 동작 확인용): 저장 `v5/main.jsonl`·`pressure_only.jsonl`·`item8.jsonl`·`overlap.jsonl`·`u9_targeted.jsonl`·`overlap_t_a.json`, `grid_vb/` 4파일, `touch_phase/acceptance/c4g2_only/grid/` 4파일, `seedext/r79_*_seedext.json`, `noise_*/r79_*_L1L2L3.json`, `dg3/dg3_v4_on.json`.
- 보지 않은 것: `verif_matrix/scripts/resume4368_judge.py`, `u3_judge_k1.py`, `resume_k1_record.py`·`_steps.py`·`_family.py`·`_identity.py`, `v5_resume_4368/gs_check_*.txt`·`chrono_rows_*.json`, r79·r67·r69·`las_t3_dg3` 판정 함수와 러너 코드, `dg3v4_judge` 계열, `run_v5.py`, 이전 단계 v5 판정 스크립트, 이전 단계 다른 작성자의 경로 2 도구, 저장 `seedext/seedext_check.json`, `grid_v0/g0_compare.json`.
