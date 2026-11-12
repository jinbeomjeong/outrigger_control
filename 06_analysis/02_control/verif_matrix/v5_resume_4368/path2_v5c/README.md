# 436.8 경로 2 — v5 기준 원 규칙 등급 재집계 (H-6·H-8·H-9·H-10)

- 규칙: 436.8 원판 `../../v5_resume_4368_rules.md`(`9019b405…`), rev1(`d9094fda…`), rev2(`497e4614…`). 원 규칙은 원판 부록 A의 `v5_criteria.md` + 개정 1~12b. 실행할 때마다 `p2_4368.check_seals`로 세 규칙 파일(raw sha, LF·BOM 없음)과 부록 A 33개 파일을 확인한다(R2-9 CRLF 정규화 일치면 통과, `seals.eol_only_detail`에 공개). 어긋나면 종료 2(S-1).
- 작성자: terramechanics-expert(경로 2, 사용자 결정 2026-11-13). 경로 1 도구를 만들거나 고친 적이 없다. 아래 "독립성 공개"에 읽은 것을 적었다.
- 환경: `conda run -n dynamics-dev python -I -B <도구> ...`. 표준 라이브러리, numpy(T4h npz), scipy(CP 두 경로)만 쓴다.
- 공통 CLI: `--repo`(기본: 이 폴더에서 다섯 단계 위), `--out <JSON>`, `--p2-dir`(아래 import 위치), `--allow-import-sha`. 종료 0(멈춤·실패·판정 불가 없음), 1(실패 또는 판정 불가), 2(멈춤 H-*·S-*·P-*, 규칙 sha 불일치, import 파일 sha 불일치 `P2-SHA`), 3(도구 오류). stdout 마지막 줄은 ASCII JSON(`tool_sha256`, `common_sha256`, `status`, `exit`, `out_sha256`, `stop_codes`). 본문은 `--out`(UTF-8, LF).

## import (복사하지 않음)

메인 세션 결정(2026-11-13: 경로 2 안에서 J 항목 정의를 하나로)에 따라 J 항목은 dynamics-expert 파일을 경로로 import한다. 파일은 고치지 않는다.

| 파일 | 위치(기본 탐색 순서: `--p2-dir` → `../path2` → dynamics-expert worktree `agent-a2e81c57365f0d7bb`) | 고정 sha256 | 쓰는 것 |
|---|---|---|---|
| `p2_v5j.py`(커밋 `bf52c89`) | `v5_resume_4368/path2/` | `559bd34f173e50791ccdd3b0af7be8bda44dcbb72acdd4c8ba7671c2a35a45ea` | `judge_pair`, `j_values`, `jp3`, `nrev_max_by_row`, `pair_key`, `row_key`, `rod_reading_from_t4h`, `tag_of`, `is_event` |
| `p2_4368.py`(`p2_v5j.core`) | 같음 | `1294dc4e1d3226eb8389f5112ad6ae7be6cc5551b81f6656f0c530f76a5fa753` | `check_seals`, `load_is_extend_start`, `Findings`, `t_ge/t_lt/t_gt`(7.6 허용 1e-9), `num`, `dig`, `read_jsonl`, `F_MIN_N` |

sha가 다르면 종료 2(`P2-SHA`)다. J 항목 정의가 움직였다는 뜻이므로 판정 전에 메인 세션이 확인한다.

## 도구와 sha256 (각 묶음 첫 결과 전 고정, 2026-11-13)

| 도구 | 묶음 | sha256 |
|---|---|---|
| `p2v5c_common.py` | 공통 | `f92211b05548236e8a5ab51da0dc6e5616be08c90a788a6b37938a696c5554be` |
| `p2v5c_stage1.py stage1` | H-10, H-9(main·pressure_only) | `660688bc2251234bc6e1025a947d536ec6d46aa20b9cfc36c555365c16f181d7` |
| `p2v5c_grid.py grid` | H-9(격자 768) | `60a0d445b5af35b8637b90559bb48fb16309a0f43f7d10325ba786e5902244d0` |
| `p2v5c_noise.py noise` | H-6, H-8(부분) | `9e8532622b699934cf57637f7df064eb15bbeb35115231d96177158f63c2013e` |
| `test_p2v5c.py` | 자체 시험 16개 | `bd452ca22fa671c4681faf7f98deaec8dde851318c6f34facafbce07c84b3b3c` |

## 규칙 절 ↔ 함수

| 규칙 | 내용 | 함수 |
|---|---|---|
| v5 3 J1~J11, 개정 2 2.1(J9 이륙 뒤), 개정 8 3.2·개정 9 3(J-P3) | 줄마다 V0 짝 대비 | `p2_v5j.judge_pair`(import) |
| v5 2 P-6, P-7 | L2 = L1 해시 8행, L1 ≠ V0 | `stage1.check_p6_p7` |
| v5 6 S8 F-5 | 조항 = 정지 뒤 최대 ≤ 정지 때 + 0.01 W, 유량 끔 조항 실패·VB 여유 < −6.92 kN·정지 뒤 최대 > 14.21 kN = H-5 | `stage1.f5_clause` + `cmd_stage1` |
| v5 8 VB × L1 표 | VB 실패면 멈춤, VB 통과·L1 실패는 기록 | `stage1.l1_table` |
| v5 8 L-a~L-e | a·b·c·e 위반 = H-6, d = `감도 큼` 기록 | `stage1.ls_conditions` |
| v5 11 H-2·H-3·H-4·H-7·H-8·H-9 | VB J 실패, R12 V0 통과 수 감소, 리밋 사이클(VB·L1), $n_{late}$ 대체, S7 분류, 이륙 뒤 잘림 | `stage1.cmd_stage1` |
| v5 13.1 ① | R6·R8·R9 × 4위상 이륙 뒤 최소 중앙값·범위 순서 | `stage1.item8_order` |
| v5 13.3 ③ | 겹침(`overlap_found.over_ms` > 0) ∧ J1·J2 변화 = `FLAG_overlap`, 기록 | `stage1.overlap_record` |
| v5 13.4 ⑥ | `unit_status` 표시 확인, 기록 | `stage1.pressure_only_record` |
| 개정 4 #4·5 #1·6 #9 | M2 켬 = `m2_law` `flow_limited_r5`, M2 끔 = 키 없음 | `stage1.m2_law_check` |
| 436.8 5.1·RV1-2·RV1-12 | 줄 수 S-15(h9 908, h10 440, 설정별) | `stage1.split_lines` |
| 명세 342.3(r67 행 관문) | 기록 필드로 관문 재계산, 기록 관문과 대조 | `grid.gates_p2` |
| v5 10 격자 | 통과→실패 0(V0 짝), FAULT 0, H-10 | `grid.cmd_grid` |
| 개정 5 #5·5.1 계열 $\mathcal F$ | `screen|top|0.0|ready|FR/FL` FS24의 `Fmin_after_W`·`U57_outside`만 위상 분포 규칙 → 따로 냄(판정 불가) | `grid.cmd_grid` |
| 개정 3 #1~#3, 개정 8 #6, 개정 6 9(H-15), v5 10·423.1 | 수준 수, dg3 135키 대체·해시 같음 기록, seedext 시드 0~4 해시, S1 전방 제외 n, CP 한계(두 경로) | `noise.cmd_noise`, `noise.seedext`, `noise.cp_table` |

## 실행 예

```powershell
$d = '<repo>\06_analysis\02_control\verif_matrix\v5_resume_4368\path2_v5c'
$r = '<repo>\06_analysis\03_hydraulic\coupled\v5\resume_k1'
$c = 'C:\ProgramData\miniforge3\Scripts\conda.exe'
& $c run -n dynamics-dev python -I -B "$d\p2v5c_stage1.py" --out <out>\h10_h9s.json stage1 --h9 "$r\h9_stage1.jsonl" --h10 "$r\h10_reuse_rerun.jsonl" --t4h-root <H-10 T4h 폴더> --overlap-ta "$r\h10_overlap_t_a.json"
& $c run -n dynamics-dev python -I -B "$d\p2v5c_grid.py" --out <out>\h9_grid.json grid --vb grid_r67_main="$r\h9_grid\grid_r67_main.json" --vb grid_r67_top=... --vb grid_r69_bottom=... --vb grid_r69_top=... --v0 grid_r67_main=<V0 짝> ...
& $c run -n dynamics-dev python -I -B "$d\p2v5c_noise.py" --out <out>\h6_h8.json noise --noise-vb "$r\h8_noise_VB.json" --noise-v0 "$r\h8_noise_V0.json" --h6 "$r\h6_dg3_v4on.json" --seedext-vb "$r\h8_seedext_VB.json" --seedext-v0 "$r\h8_seedext_V0.json"
& $c run -n dynamics-dev python -I -B -m pytest -q -p no:cacheprovider --basetemp <scratch>\pt "$d\test_p2v5c.py"
```

## 동작 확인 (판정 아님, 저장 기준선 = 옛 태그·LAS-b 전)

| 도구 | 입력 | 결과 |
|---|---|---|
| stage1 | 저장 `main.jsonl`·`pressure_only.jsonl`·`item8.jsonl`·`overlap.jsonl`·`u9_targeted.jsonl` VB를 h9 908 / h10 440 꼴로 scratchpad에 묶음, T4h `v5/main/t4h` | 줄 수 S-15 0. 옛 태그라 VB·LS의 J-P3가 전부 `not_applicable_tag` → 판정 불가(기대대로). 옛 L1 설정에서 H-7($n_{late}$ 대체) 6건 |
| grid | 저장 `grid_vb/` 4파일 + V0 짝 `touch_phase/acceptance/c4g2_only/grid/` 4파일 | 기록 관문과 재계산 관문 차이 **0/768**. 통과→실패 2건, 둘 다 계열 $\mathcal F$(`Fmin_after_W`만) → 판정 불가. 옛 태그 J-P3 768건 판정 불가 |
| noise | 저장 `noise_vb`·`noise_v0`·`dg3_v4_on`·`seedext` | 수준 수 167/835/501, dg3 L2 1 + L3 134, CP 한계 n 835 → 16(상계 2.8958 %, 두 경로 차 5e-17), n 501 → 8. 저장 r79 기록에 명령 해시 필드가 없어 해시 비교는 판정 불가 |

## 확인 필요 (rev3 문장화 대상 후보)

| # | 내용 | 이 도구의 가정 |
|---|---|---|
| Q-G1 | H-9 격자 VB의 V0 짝. 436.8은 격자 V0를 다시 돌리지 않는다(5.1 H-9는 "격자 VB"만). V0 제어기가 `final_C4G2_LAS_K1`로 바뀌었으므로 저장 V0(옛 제어기)를 짝으로 써도 되는가 | `--v0`로 받은 파일을 그대로 짝으로 쓰고 V0 태그를 출력에 적는다. 주지 않으면 판정 불가 |
| Q-G2 | 계열 $\mathcal F$ 위상 분포 규칙(개정 5 5.2)의 VB 32·V0 32 실행이 436.8 묶음에 없다 | $\mathcal F$ 두 관문만으로 생긴 통과→실패는 판정 불가로 따로 낸다(H-10을 걸지 않음) |
| Q-N1 | 잡음 줄 하나의 판정(r79 S-1~S-6, 명세 405~407.2·419.8·423.1)을 경로 2가 다시 정의할 문장 | 이 작성자는 정의하지 않았다. 줄 판정·L2 CP 등급·L1 게이트·L3 기록은 내지 않고 H-6·H-8은 판정 불가 |
| Q-N2 | r79 기록에 `commands_sha256`이 어디에 있는가(저장 기록에는 없음). RV1-3.2 H-6↔H-8 해시 기록과 H-15 시드 0~4 대조에 필요 | `commands_sha256` → `r79.commands_sha256` → `resume_k1.commands_sha256` 순. 없으면 판정 불가(멈춤 아님) |
| Q-S1 | J1 정상 행에 v5 3이 적은 `failed_rows` 필드가 기록에 없다 | `p2_v5j` 정의(`harness_class`)를 그대로 쓴다 |
| Q-S2 | S8(행정 가드 안전 정지)의 J6: 마지막 5 s 자세가 V0·VB 모두 None → `p2_v5j`는 판정 불가로 센다 | 그대로(정의 변경은 rev3) |
| Q-S3 | J-P3 헤드 전용 선언: 저장 main 정상 행에는 `head_only_declared`가 없다. 436.8 줄에도 없으면 T4h 로드 판독 없음 + 선언 없음 → `p2_v5j.jp3`가 설정 결함(#4) 멈춤을 낸다 | 그대로. 436.8 줄에 필드가 있는지 G-S에서 확인 권고 |
| Q-S4 | P-7 "L1 해시 ≠ V0 해시"가 줄마다인지 묶음 전체인지 | 모든 L1 줄이 V0와 같을 때만 멈춤, 같은 줄 수는 기록 |
| Q-S5 | 13.1 "중앙값 순서가 반대": 이웃 한 쌍만 뒤집혀도 반대인가 | 이웃 쌍 하나라도 겹침 없이 뒤집히면 `reversed` |
| Q-S6 | v5 6 SA-4의 다른 항목(같은 주기 WARN→FAULT:soil, 정지 뒤 네 다리 ≥ $F_{min}$, 부상 0, 포화 차단 0)과 "조항만 실패"의 판별 | 조항 값과 멈춤 두 문턱만 재계산, 나머지는 J 항목에 맡김 |
| Q-S7 | H-8 "FL 가드 시각" 필드 | 기록에 다리별 가드 시각이 없어 `values.guard_active_s`를 기록만 |
| Q-S8 | item8 VB 6줄의 J 항목 실패도 H-2에 넣는가 | 넣는다(VB 줄이므로) |
| Q-S9 | L-d "위상 산포 안" 조항 | 쓰지 않고 1 kN·1 s만으로 `감도 큼` 기록 |
| Q-S10 | U-9 VB 28줄(H-10 안)의 등급 | `p2_v5j.py u9`(dynamics-expert)가 낸다. 이 도구는 줄 수만 센다 |
| Q-G3 | 격자 J-P3 로드 판독 | 두 압력 사건 경로라 판독 있음으로 둔다(개정 9 3.2 #4) |

## 독립성 공개 (436.8 9.2, 이 도구를 쓰려고 읽은 것)

- 규칙: 436.8 원판 전체, rev1 전체, rev2 전체. `v5_criteria.md` 전체, 개정 1·2 전체, 개정 3 2~5절, 개정 4 2·4·5절, 개정 5 2·4·5절, 개정 6 2·9~12·14.5절, 개정 8 2·3·7.4·8절, 개정 9 2·3절, 개정 10 1·3·4절, 개정 11 1·2절, 개정 7·12·12a·12b는 머리 목록만(Chrono 전용). 명세 `s6_control_spec.md` 342.1~342.3절, 405~407.1 앞부분, 423.1·423.4절, 11025행(P3-2).
- 같은 경로 2: dynamics-expert `path2/README.md`, `p2_4368.py`의 머리·상수·도우미·`check_seals`·`main`, `p2_v5j.py` 1~350행과 `main`(import할 함수).
- 원 데이터(구조와 식별 필드, 동작 확인용): 저장 `v5/main.jsonl`·`pressure_only.jsonl`·`item8.jsonl`·`overlap.jsonl`·`u9_targeted.jsonl`·`overlap_t_a.json`, `grid_vb/grid_r67_main.json`, `touch_phase/acceptance/c4g2_only/grid/grid_r67_main.json`(관문 이름·실패 예 2건), `seedext/r79_VB_seedext.json`, `dg3/dg3_v4_on.json`(③ 기록 키 이름).
- 보지 않은 것: `verif_matrix/scripts/resume4368_judge.py`, `u3_judge_k1.py`, `resume_k1_record.py`, `resume_k1_steps.py`, `resume_k1_family.py`, `resume_k1_identity.py`, `v5_resume_4368/gs_check_*.txt`·`chrono_rows_*.json`, r79·r67·r69·`las_t3_dg3` 판정 함수와 러너 코드, `dg3v4_judge` 계열, `run_v5.py`, 이전 단계 v5 판정 스크립트, 이전 단계 다른 작성자의 경로 2 도구(`p5k_path2` 등), 저장 `seedext/seedext_check.json`, `grid_v0/g0_compare.json`.
