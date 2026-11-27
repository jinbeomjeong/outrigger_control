# 436.9 판 8 4단계 출력(C8 56849248), 관문 판정 전 점검 — M-5 키 존재와 생산자 꼴 읽기 스모크 (T8″ 5955f25b)

의존성 점검: 모두 있음 (python-dev 21개 패키지, CHECKED 2026-11-27 16:12)

## 0. 결론
- **차단 결함 1건(D-1)을 찾아 멈췄습니다.**
  - T8″의 J-P3 읽기가 판 8 설정 이름(VBN·LSN1~4 등)을 판정 대상으로 알지 못합니다.
  - 그래서 판 8 줄은 어떤 경우든 "J-P3 0 judged rows" = **not_judgeable**이 됩니다.
  - 4단계 관문 가운데 `cases`(P8-2)가 구조적으로 판정 불가이고, 6·8단계 census(C-J (iii)·C-S·C-D·C-G)와 G′의 J-P3도 같은 상태가 됩니다.
  - 판정 도구는 locked라서 고치지 않았습니다.
- 나머지 관문 경로는 키·꼴 결함이 없습니다: p80, p816, p85, p88, p815(설계대로 r79 4쌍 제외), t8, l1ref.
  - 읽기 함수 스모크에서 예외 0, 정체성 결함 0, step 기록 문제 0이었습니다.
- 판정 값(통과·실패 수, 지표, 층 분포, 줄별 결과)은 출력하지도 보지도 않았습니다.
- 관문 판정은 돌리지 않았습니다.

## 1. M-5 키 존재 점검 결과
도구 `key_presence.py`(python-dev `-I -B`) 기록은 `kp_*.json`에 있습니다. 즉석 스크립트 `m5_keys.py`·`m5_extra.py`로 줄 종류별 셈·T4h meta 조회·꼴(값 없음)을 봤고, 결과는 `m5_keys.json`, `m5_summary.txt`, `m5_extra.json`, `shape_probe.json`입니다(모두 `stage4_prejudge\`).

| 키 | 대상 줄 종류 | 있음/없음 | 기대와 일치 |
|---|---|---|---|
| `commands_sha256`(64자 hex) | 4단계 9개 파일 전 줄(1,064줄) | 전부 있음 | 일치 |
| `t4h_file`, `controller_tag`, `hydraulic_options`, `lsb_components`, `lsb_settings`, `probe_d6_settings`, `hydraulics_record`, `head_only_declared`, `events`, `event_names` | run_v5 판 8 줄(t8 VBN 22·VBN0 22, cases 10) | 54/54 (`kp_run_v5.json` 종료 0) | 일치 |
| `ed8_settings`와 하위 7개(`probe_k1_scale_settings.scale_mid_min_piston_travel_m`, `r8.stiffness_warning_range`, `r8.lifted_reapproach.short_run_s`·`short_run_exit_samples`, `twist_completion_relax.locked_drift_waiver`·`waiver_max_rise_N`·`waiver_margin_N`) | run_v5 판 8 줄 | 54/54 non-null | 일치(값 대조는 아래 정체성 스모크에서 결함 0) |
| `ed8_record.reapproach_runs`, `ed8_record.twist_waiver.n_waiver_done`·`n_waiver_periods`, `probe_stiffness_record` | run_v5 판 8 줄 | 54/54. 꼴: reapproach 항목에 `short_run_extended` 있음, waiver 수 int 54/54, stiffness는 `twist_stiffness_scale` 항목 리스트 | 일치 |
| `lock_window_alignment` | run_v5 판 8 줄 / probe 팔 / r79 / P7 줄 | 전부 있음(dict) | 일치(M′-4 "판 8 줄에 있음") |
| `lock_window_alignment` 등 `V0_ABSENT_KEYS` 10개 | **5단계 V0 줄** | 4단계에는 V0 줄이 없어 해당 없음. 참고로 C8 V0 스모크 `smoke_v0_56849248\v0_smoke.jsonl`(2줄, 감사가 본 자료, sha 35da6992)을 보면 10개 모두 없음, `hydraulic_options`·`hydraulics_record` null 2/2, `controller_tag`·`commands_sha256`·`event_output.reapproach_starts` 있음 2/2 | 일치(5단계 실출력에서 다시 볼 것) |
| `hydraulics_record.extend_bound_check` | ③-on: cases 10, t8 VBN 이벤트 줄 4 | 있음. t8 VBN 18줄은 null인데 모두 `head_only_declared` true | 일치 |
| 같은 키 | ③-off: t8 VBN0 22 | null 22/22 | 일치 |
| `event_output.reapproach_starts`, `event_output.pass/gates.fault0/fault_periods/fault_events` | 이벤트 줄(t8 각 4, cases 10, probe M 17·LSM4·Mslow) | 있음. 정상(steady) head-only 줄에는 없음 | 일치(V0 쪽에서 읽는 키) |
| `probe_d6_record.not_opened_rounds`·`would_warn` | run_v5 판 8 줄 | 기록 있는 줄 18(t8 VBN 4·VBN0 4·cases 10)은 모두 길이 4 int/bool 꼴. 나머지 36줄은 null(head-only). 다른 꼴 0 | 일치(null은 jx가 따로 셈) |
| `INFO_ROD_PRESSURE_FAULT_REASON:<leg>:<reason>` | run_v5 판 8 줄 | **0건**(`WARN_ROD_PRESSURE_FALLBACK`도 0) | 꼴 확인 불가(관찰 O-2) |
| 같은 사건 | r79 KM0 줄(p815·p816 각 팔 4줄) | 팔마다 4건, 모두 ':' 3분할, 다리 이름 정상, 첫 토큰이 6종 안 4/4(분포 D1 4) | 일치 |
| 사건 원소 꼴 `[t, name]` | 전 파일 | 쌍 아님 0, 상한(200) 도달 줄 0 | 일치 |
| P8-5 `probe_stiffness_record` | p85 a8·a8_psw_off 46줄 | 46/46 리스트 꼴 | 일치 |
| P8-8 `ed8_record.reapproach_runs[*].short_run_extended` | p88 켬 팔 a8 23줄 | 꼴 정상 23/23(끈 팔 a8_h3_off는 18/23이 다른 꼴인데, 판정은 켬 팔만 읽음) | 일치 |
| P8-15 `ed8_record.twist_waiver` 수 | p815 켬 팔 a8 | r79 아닌 23줄은 int 23/23(MALFORMED 0). r79 KM0 4줄은 없음(줄과 T4h meta 모두) → 설계대로 빠지고 기록 실패 (1)(`kp_probe_on_arm.json` 종료 1, 이 4줄만) | 일치 |
| r79 L1 줄 `key`, `v5_setting`, `level`, `rod_model`, `t4h_file`, `controller_tag`, `hydraulic_options.p1_patch`, `hydraulic_options.ed8_settings`(A-4), `base`, `lock_window_alignment` | l1ref 4파일 538줄 | 538/538(`kp_l1ref.json` 종료 0) | 일치 |
| r79 L1 `lsb_components`·`lsb_settings`·`probe_d6_settings` | l1ref | 줄에는 없고 T4h meta에 538/538 | 일치(R79_META_FIELDS) |
| r79 `ed8_record`, `probe_stiffness_record`, 최상위 `ed8_settings` | l1ref·KM0 | 없음(줄과 meta 모두) | 기대대로 없음(R-1, 기록 실패 (1)) |
| `run_extend_start_revision` | L1 VBN / VBN0 | VBN 있음 / VBN0 없음 | 일치(③-on만 요구) |
| L1 문서 `meta.keys_file.sha256`·`n_keys` | l1ref 4파일 | 있음 | 일치 |
| `commands_sha256`, `job` | p80 114줄 | 114/114(`kp_p80.json` 종료 0) | 일치 |

## 2. 생산자 꼴 읽기 스모크 (dynamics-dev, cwd = ed8-judge2, 상태만)
- 스크립트: `read_smoke.py`, `read_smoke_detail.py`, `read_smoke_detail2.py`, `jp3_cause_probe.py`
- 결과: `read_smoke.json`, `read_smoke_detail.json`, `read_smoke_detail2.json`, `jp3_cause_probe.json`
- 전 실행 기준
  - 예외 0
  - stderr 0줄
  - import된 판정 모듈 38개가 모두 ed8-judge2 아래에서 왔습니다(`module_files_outside_judge_root` 빈 목록).

| 읽기 함수(감사 표 행) | 입력 | 상태 |
|---|---|---|
| 고정 입력 `pinned_input` | main.jsonl, p80 기준, grid192 | ok 3/3. P8-16 기준 runs.jsonl sha = `89efe66f…`(상수와 같음) |
| `step_output_problems` | 8개 .done | 문제 0 / 8 |
| `identity_defects`(101) | impl_t8 44, impl_cases 10 | 결함 줄 0 / 0 |
| `metric_of`(101) | C-J 꼴 32줄(VBN→VB, LSN→LS), 같은 job의 V0 main 23줄 | 계산 32/32, 23/23, 예외 0 |
| `unit_item_verdicts` C-J(101) | VBN 24단위 | 판정 가능 23, 판정 불가 1(V0 main 줄 없는 사례 줄 1 = `no_reference`, 스모크 구성 탓) |
| `is_base_pass` | V0 23 | 계산 23/23 |
| `layer_of`(V0 시작 목록) | VBN 24 | 계산 24/24, LayerInputError 0 |
| C-J (ii) 묶음 | LS 대 VB | 실행됨. 판정 불가 L-c 4개는 모두 "no V0 n_rev maximum of the group"(V0 main 줄 없는 사례 1행 탓, 스모크 구성 탓) |
| **`jp3_of`(101)** | impl_cases 10 | **판정 행 0, not_judgeable 2("J-P3 0 judged rows", "J-P3 no_judged_runs"), setting_defect 0 → D-1** |
| `jp3_of` | t8 VBN 22(이벤트 줄 4만 봐도 같음) | 판정 행 0, not_judgeable 2 → D-1 |
| `jp3_of` | t8 VBN0 22 | setting_defect 2, 판정 행 0. ③-off 줄이라 J-P3 판정 대상이 아니고 P8-1은 해시만 읽음 → 기록 |
| `jx_line_counts`(101) | t8 VBN 22, cases VBN 2 | 예외 0. 증인 꼴: 기록 4·2, 기록 없음 18·0, 다른 꼴 0. 기회 줄 0, unknown 0 |
| C-S `unit_table`·`unit_verdicts` | 54줄을 자기 설정 이름으로 | 54단위 가운데 판정 가능 47, 판정 불가 7. 7개는 "no V0 line" 5(사례 줄)와 R15 2(VBN·VBN0은 감도 설정이 아님)로 스모크 구성 탓 |
| C-D `d_lines_of` | 54 | 예외 0. V0 비교 결측 54(grid 짝 없는 줄), condition·J-P3a 읽기 None 40(head-only 36 + ③-off 이벤트 4), FAULT 키 결측 36(head-only) |
| C-G `grid_line_values` | 54 | 예외 0. grid 짝 0(이 줄들은 grid 행이 아님), FAULT 읽기 불가 36(head-only) |
| `line_records`, `waiver_lines` | 54 | 정지 서명 읽기 불가 0, twist 기록 결측 0. waiver 실행됨 |
| heldout 줄 단위 읽기(102) | t8 VBN 22 대 V0 main | 예외 0, 판정 불가 항목 0, base 계산 22/22. FAULT 읽기 불가 18(head-only. G′ 줄은 이벤트 줄). heldout `jx_line_counts` 실행됨. J-P3는 위 D-1과 같은 경로 |
| 12b `load_lines`(103) | l1ref 4파일(167·167·102·102) | setting_defect 0, not_judgeable 0. T4h 찾음·meta 읽힘 전부, 사례 고유 |
| 12b `line_identity_problems`(A-4 스위치, 줄 또는 T4h meta) | l1ref 538 | 문제 줄 0, 예외 0. `ed8_settings_problems(whole_options=False)` 0 |
| 12b `l1_reference_problems` | 실제 키 파일 sha(`ed5_inputs\l1_keys_12b.txt`, `l1_keys_d3c6c57e.json`) | 문제 0 / 4파일 |

- 공개 1: 12b 정체성 스모크는 l1ref 관문의 판정 내용(정체성)과 겹칩니다.
  - l1ref 관문의 상태는 pass·setting_defect·not_judgeable뿐이고 failed가 없습니다.
  - 그래서 "결함 0"을 공개하면 l1ref 관문의 정체성 부분 결과가 사실상 드러납니다.
  - cases의 `identity_defects` 0도 P8-2 setting_defect 근거의 일부입니다.
- 공개 2: `load_lines`는 L1 줄에 쓰려고 이 프로세스 안에서만 `SETTING_OF_ARM`을 VBN0/VBN으로 바꿔 돌렸습니다. 파일은 바꾸지 않았습니다.
  - 12b 본 경로(VBKN0 블록 + `selection.json`)는 생산자 꼴로 시험되지 않았습니다(블라인드 selection, 10단계 출력 없음).

## 3. 결함 목록

### [차단] D-1. `j_p3_inputs.REV5_JUDGED_SETTINGS`에 판 8 이름이 없다 → 판 8 J-P3는 항상 판정 불가
- **위치**: ed8-judge2 `04_scripts\04_hydraulic\coupled\j_p3_inputs.py:57-68`
  - `REV5_JUDGED_SETTINGS = (VBJ…, *ED6_JUDGED_SETTINGS, *ED7_JUDGED_SETTINGS)`
  - VBN·LSN1~4·VBKN·VBN 감도 이름이 없습니다.
- **사용처**: `j_p3_inputs.py:253` `_revision_5_judgement`
  - 판 8 줄(③ rev 7 hold)이 판정 대상에서 빠지면 `no_judged_runs`가 됩니다.
  - 이어서 `jp3_ed7_judge.jp3_basis`가 "J-P3 0 judged rows"를 내고 not_judgeable이 됩니다.
- **확인**: 판 8 판정 도구(`jp3_ed8_*`)에는 이 튜플을 바꾸는 곳이 없습니다. Grep `JUDGED_SETTINGS`(coupled `*.py`)로 확인했습니다.
- **원인 확인 실험** `jp3_cause_probe.json`(파일 수정 없음)
  - 이 프로세스 메모리에서만 `run_v5.ED8_JUDGED_SETTINGS`(VBN, LSN1~4)를 더했습니다.
  - 그러자 impl_cases 판정 행이 0 → **10(= CASE_ROWS)**이 되고, setting_defect·not_judgeable 목록이 비었습니다.
  - 실패 목록과 J-P3 상태는 출력하지 않았습니다.
- **영향**
  - 4단계 `cases`(P8-2 "10줄 J-P3 판정 키 0"): `judge_cases`의 `jp3_basis`가 "J-P3 0 judged rows"를 넣어 **not_judgeable, 종료 2**가 됩니다. 판정 행 0은 `not in (0, 10)` 검사를 통과하므로 setting_defect는 아닙니다.
  - 6단계 census: `cj_stage`·`cs_stage`·`cd_stage`·`cg_stage`의 `jp3_of`가 같은 상태라 census 전체가 not_judgeable이 됩니다.
  - 8단계 G′: `judge_heldout`의 `jp3_of`가 같은 상태입니다.
- **관련(추정, 확인 안 함)**: `jp3_tjr_judge.py:680`(`_check_lines`)이 같은 튜플로 "J-P3 줄의 P4 증거" 검사를 거릅니다.
  - 판 8 VBN 줄은 이 검사를 건너뛸 수 있습니다(조용한 누락).
  - 같은 함수의 `JP3_LINE_SETTINGS`/`ED6_LINE_SETTINGS`(:661-677)도 판 8 이름이 있는지 봐야 합니다(9단계 12a).
- **시험이 못 잡은 이유(추정)**: 앞 감사 기록상 census·cases 시험에서 J-P3 읽기가 스텁이었습니다.
- **수정 방향(위임)**: T8 위 새 판정 커밋(T8‴)에서 판 8 판정 대상 이름을 더합니다.
  - 판 7 목록이 VBM·LSM1~4·VBKM·VBMslow·VBMfast·VBMc005·VBMc04였습니다. 같은 꼴이면 VBN·LSN1~4·VBKN·VBNslow·VBNfast·VBNc005·VBNc04가 후보입니다.
  - 정확한 목록은 명세 3.6·5.2·8의 판정 대상 정의로 정합니다(확인 필요 1).
  - 아울러 생산자 줄 시험이 필요합니다: 실제 판 8 줄로 `jp3_of` 판정 행 수를 단언하는 시험.

### 관찰(결함 아님, 기록)
- **O-1. r79 KM0 T4h는 하위 폴더에 있다.** 위치는 `p815_t4h\r79_P8-KM0-a8\` 등입니다.
  - gate `line_lookup`(gate:407-425)은 `<stem>_t4h\<t4h_file>`만 봅니다. 그래서 KM0 8줄은 meta를 읽지 못하고 None이 됩니다.
  - 하위 폴더 meta에도 `ed8_record`·`probe_stiffness_record`가 없으므로 결과는 같습니다. P8-15 r79 4쌍이 빠지고 기록 실패 (1)이 됩니다.
  - 다음 판에서 기록이 meta에만 있으면 놓칠 수 있습니다(잠재).
- **O-2. 사유 사건 꼴 확인 범위.** run_v5 판 8 줄(t8·cases)에는 대체·사유 사건이 0건이라 그 줄에서는 사유 토큰 꼴을 확인할 수 없었습니다.
  - 꼴은 r79 KM0 줄(4/4 정상)로만 확인했습니다.
  - census VBN 줄에서 처음 나올 수 있습니다. 기록 칸이고, unknown으로 셉니다.
- **O-3. `probe_d6_record` 꼴 차이.** p816 B_impl·L2_impl 줄과 p80 P7 줄의 `probe_d6_record`는 증인 꼴(길이 4 리스트)과 다릅니다.
  - jx가 읽지 않는 줄이라 영향은 없습니다(기록).
  - p85·p88·p815 a8 팔과 run_v5 판 8 줄은 정상 꼴입니다.
- **O-4. 끈 팔의 기록 부분 결측.** a8_l2_off에는 twist_waiver가 없고, a8_h3_off는 reapproach 항목 꼴이 다르고, psw_off·h3_off는 해당 `ed8_settings` 값이 null입니다.
  - gate는 켬 팔만 읽으므로 영향이 없습니다.
- **O-5. 단계 폴더 SUMS 범위.** `baseline_check sums` 9폴더 모두 mismatch 0·missing 0입니다(이번 작업으로 바뀐 것 없음).
  - SUMS가 최상위 파일만 담아 T4h npz·logs가 미등재입니다(예: l1ref 555, p80 119).
  - l1ref 큰 JSON 4개는 git ignore 대상입니다(`cited_ignored` 4).
  - LOCAL_ONLY·백업 여부는 메인이 정합니다.
- **O-6. P8-10.** T8″에는 impl_scope를 읽는 하위 명령이 없습니다.
  - 범위는 `impl_scope.done` `codes.scope` "in scope"와 P8-4 재생성 시험이 근거입니다.

## 4. 관문 판정 명령 초안 (D-1 처리 전에는 실행 보류 권고)
- **보류를 권하는 이유**
  - D-1을 고치면 판정 커밋이 바뀝니다. 4단계 관문을 T8″로, census·G′를 T8‴로 판정하면 11.2 단일 T8 원칙에 어긋납니다(verif_t8p.md:15와 같은 논리).
  - `cases`는 지금 돌리면 not_judgeable(종료 2)입니다.
- **P8-15 사용자 결정은 도구에 반영돼 있습니다**(인자 불필요).
  - gate:104 `UNREAD_PAIRS_LEFT_OUT={"p815"}`: 결측 쌍을 빼고 기록 실패 (1)
  - gate:338-351 `has_no_waiver`가 비정수를 `MALFORMED`로 표시
  - gate:387-389: MALFORMED는 setting_defect
  - 이번 출력은 비정수 0, 빠지는 쌍 4(r79)입니다.

```powershell
$j  = 'C:\workspace\outrigger_control\.claude\worktrees\ed8-judge2'
$py = 'C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe'
$r  = 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\56849248'
$o  = "$r\judge_5955f25b"     # 새 폴더(단계 폴더 밖, judge worktree 밖), 도구가 mkdir, 기존 --out은 거부
$env:MKL_THREADING_LAYER = 'TBB'; $env:PYTHONDONTWRITEBYTECODE = '1'
$env:NUMBA_CACHE_DIR = 'C:\Users\jinbeom\.claude\runners\outrigger-ed8\numba_cache\judge_5955f25b'
Push-Location $j
$g = '04_scripts/04_hydraulic/coupled/jp3_ed8_gate_judge.py'; $e = '04_scripts/04_hydraulic/coupled/jp3_ed8_judge.py'
& $py -I -B $g p80  --rows "$r\impl_p80_a1\ed7_probe_a2.jsonl" --step-done "$r\impl_p80.done" --reference 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\b46bdf8f\repro_a2\ed7_probe_a2.jsonl' --out "$o\p80.json"; "p80 $LASTEXITCODE"
& $py -I -B $g p816 --rows "$r\impl_p816_a1\p816.jsonl" --step-done "$r\impl_p816.done" --reference 'C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed8_design\control_level_deadlock\probe_8a2a52ce\raw\runs.jsonl' --out "$o\p816.json"; "p816 $LASTEXITCODE"
& $py -I -B $g p85  --rows "$r\impl_p85_a1\p85.jsonl"   --step-done "$r\impl_p85.done"  --out "$o\p85.json";  "p85 $LASTEXITCODE"
& $py -I -B $g p88  --rows "$r\impl_p88_a1\p88.jsonl"   --step-done "$r\impl_p88.done"  --out "$o\p88.json";  "p88 $LASTEXITCODE"
& $py -I -B $g p815 --rows "$r\impl_p815_a1\p815.jsonl" --step-done "$r\impl_p815.done" --out "$o\p815.json"; "p815 $LASTEXITCODE"
& $py -I -B $g t8   --rows "$r\impl_t8_a1\ed8_t8.jsonl" --step-done "$r\impl_t8.done" --main-jsonl 'C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\main.jsonl' --out "$o\t8.json"; "t8 $LASTEXITCODE"
& $py -I -B $e cases --rows "$r\impl_cases_a1\ed8_cases.jsonl" --step-done "$r\impl_cases.done" --out "$o\cases.json"; "cases $LASTEXITCODE"   # D-1: 지금은 not_judgeable
& $py -I -B $e l1ref --rows "$r\l1ref_a1\L1_VBN0.json" --rows "$r\l1ref_a1\L1_VBN.json" --rows "$r\l1ref_a1\L1a_VBN0.json" --rows "$r\l1ref_a1\L1a_VBN.json" --step-done "$r\l1ref.done" --out "$o\l1ref.json"; "l1ref $LASTEXITCODE"
Pop-Location
git -C $j status --porcelain --ignored   # 비어 있어야 함
```

- 종료 코드: 0 pass / 1 failed / 2 setting_defect·not_judgeable / 3 error.
  - stdout 마지막 줄 JSON에는 status와 경로만 있습니다.
  - 명세 4절 4단계에 따라 failed·setting_defect면 멈추고 묻습니다.
- P8-10은 하위 명령이 없습니다(O-6).

## 5. 확인 필요
1. D-1 수정 범위: 판 8에서 J-P3로 판정하는 설정 목록. 판 7 꼴(VBN·LSN1~4·VBKN·VBNslow·VBNfast·VBNc005·VBNc04)인지 명세 원문으로 정해야 합니다.
   - 근거 위치: 규칙 문서 `jp3_remedy_spec_v8_rules.md` 3.6·5.2·8 ↔ 도구 `j_p3_inputs.py:62-68`
   - 명세 작성 에이전트(control-expert) 몫입니다.
2. 4단계 관문을 T8″로 먼저 판정할지, D-1 수정 커밋(T8‴)과 재감사 뒤 모든 판정을 T8‴로 할지 — 11.2 단일 T8(사용자 결정).

## 6. 위임 필요
- python-expert(T8‴, ed8-judge2 위 새 커밋, C8 불변):
  - D-1 수정
  - 실제 판 8 줄로 `jp3_of` 판정 행 수를 단언하는 시험(생산자 꼴, CWD 분리)
  - `jp3_tjr_judge.py:661-684`의 판 8 이름 점검
  - (선택) O-1 하위 폴더 조회
- verif-protocol-auditor: T8‴ 재감사. 판 8 이름이 빠진 설정 이름 튜플을 전수 검색해 달라는 요청입니다(`*_JUDGED_SETTINGS`, `*_LINE_SETTINGS`, `T8_JUDGED_SETTINGS` 등).

## 7. 실행한 검증과 종료 코드
- 인터프리터
  - python-dev `-I -B`(`MKL_THREADING_LAYER=TBB`): 키·꼴 스크립트, verif 도구
  - dynamics-dev `python.exe -I -B`(cwd ed8-judge2, `PYTHONDONTWRITEBYTECODE=1`, `NUMBA_CACHE_DIR`=scratchpad 하위): 판정 도구 import 스모크 4개, 모두 종료 0
- key_presence 종료 코드
  - run_v5 0, cases ③ 0, l1ref 0, p80 0
  - probe 전체 1: key_absent 8. r79 KM0 16줄의 ed8 기록과 끈 팔 waiver(설계상)
  - probe 켬 팔 1: key_absent 4. p815 r79 KM0 4줄
- `baseline_check sums` 9폴더: 종료 1. mismatch 0·missing 0이고, 사유는 미추적·미등재(O-5)입니다.
- `ruff check --isolated`(내 스크립트): 종료 1
  - RUF100 15건: 격리 기본 규칙에서 쓰지 않는 E402 noqa
  - B023 1건: 루프 안 람다를 즉시 평가하므로 무해
  - 실행한 그대로 근거로 남기려고 고치지 않았습니다.
- codespell: 종료 0.
- ed8-judge2 `git status --porcelain --ignored`: 작업 후 빈 출력, HEAD 5955f25b. numba 캐시 파일 0, scratchpad 하위 폴더는 지웠습니다.
- 4단계 단계 폴더와 빈 `judge\`에는 아무것도 쓰지 않았습니다(SUMS 대조 mismatch 0).
- 판정 도구는 import·호출만 했습니다. 바꾼 것은 프로세스 메모리 안의 두 가지뿐입니다: `SETTING_OF_ARM`(12b 스모크), `REV5_JUDGED_SETTINGS`(원인 실험). 둘 다 복원했고 파일은 그대로입니다.
- `stage4_prejudge\` 산출물(SUMS는 쓰지 않음)
  - 스크립트 8개: `shape_probe.py`, `m5_keys.py`, `m5_summary.py`, `m5_extra.py`, `read_smoke.py`, `read_smoke_detail.py`, `read_smoke_detail2.py`, `jp3_cause_probe.py`
  - 키 목록 3개: `keys_*.txt`
  - 결과: `kp_*.json` 6개, `m5_keys.json`, `m5_summary.txt`, `m5_extra.json`, `shape_probe.json`, `read_smoke*.json` 3개, `jp3_cause_probe.json`

## 8. 읽은 파일·검색 범위 (오염 보고용)
- **audit_prerun**
  - Read: `verif_t8pp.md`(전체), `t8pp_report.md`(전체), `t8p_report.md`(30~144행), `verif_t8p.md`(전체)
  - Grep: `verif_c8_t8.md`("M-5" 주변), `t8p_report.md`("키|M-5"), `verif_t8p.md`("M′-4")
- **명세** `jp3_remedy_spec_v8_rules.md`: Grep만("probe_8a2a52ce", "P8-10|P8-2 |P8-1 ")
- **ed8-judge2(읽기·import만)**
  - Read: `jp3_ed8_gate_judge.py`(전체), `jp3_ed8_judge.py`(1~1040, 1200~1400행), `jp3_12b_judge_ed8.py`(전체), `jp3_12b_judge_ed7.py`(전체), `jp3_12b_judge.py`(215~414, 1060~1259행), `jp3_ed7_judge.py`(280~769, 805~836, 1050~1179, 1460~1629행), `j_p3_inputs.py`(50~264행), `p816_compare.py`(1~75행), `jp3_tjr_judge_ed8.py`(전체), `jp3_tjr_judge.py`(660~699행)
  - Grep 단일 파일: `jp3_ed6_judge.py`, `jp3_j9main_judge.py`, `judge4368_common.py`, `jp3_rev7_condition.py`, `ed8_key_lists.py`, `jp3_t8_rules.py`, `jp3_12b_judge.py`, `jp3_ed7_judge.py`(L-c)
  - Grep 폴더: `04_scripts\04_hydraulic\coupled`(glob `*ed8*.py`, `*.py`)
  - Glob: `ed8-judge2\04_scripts`(모듈 이름 8개 지정 패턴)
- **ed8-impl run_steps_ed8**: 파일 목록, `step4_impl_ed8.ps1` Read, `common_ed8.ps1` Grep 2회
- **j9_runs\56849248(블라인드 아님)**
  - 목록: 루트와 9개 단계 폴더(이름·크기·수), T4h 폴더 5개(하위 폴더 이름·수)
  - Read: `l1ref.done`. Grep: `impl_scope.done`
  - 9개 출력 파일: 스크립트로 키 이름·건수·꼴만 셌습니다.
  - T4h: meta 키 존재만 봤습니다. 판정 함수가 메모리에서 읽은 T4h 배열 값은 출력하지 않았습니다.
- **그 밖의 입력**
  - `06_analysis\03_hydraulic\coupled\v5\main.jsonl`(O8-1 기존 열람 자료)과 그 V0 T4h: 판정 함수가 메모리에서만 읽음
  - `ed6_design\keys\confirm_b_grid192.json`: sha 확인과 짝 표
  - `j9_runs\b46bdf8f\repro_a2\ed7_probe_a2.jsonl`, `ed8_design\control_level_deadlock\probe_8a2a52ce\raw\runs.jsonl`: sha만
  - `prelaunch_j9\ed5_inputs\l1_keys_12b.txt`, `prelaunch_j9\l1_keys_d3c6c57e.json`: sha만
  - `prelaunch_j9\ed8_run_config.json`: 내용
  - `ed8_design\smoke_v0_56849248\v0_smoke.jsonl`: 키 존재
  - `Test-Path`는 위 단일 경로들에 직접 썼습니다.
- **블라인드**: `j9_runs\606f8713\cdry_a1\`의 `VBK_c92*`·`VBK_c93*`·`logs\`, `prelaunch_j9\ed6_inputs\x11\selection.json`, worktree 사본
  - Read·Grep·Glob·목록 어디에도 쓰지 않았습니다.
  - 블라인드를 품은 상위 폴더(j_p3_cause 루트, j9_runs, 06_analysis, worktree 루트, repo 루트)를 검색 범위로 쓰지 않았습니다.
- **셸**: Bash는 쓰지 않았고 파이프 검색도 없습니다. 프로세스를 종료하지 않았고 병렬 실행도 없었습니다.

## 9. 메모리 반영안
- `tool_edition_wrapper_patch.md`에 4항을 더했습니다: 공용 읽기 모듈의 판별 설정 이름 튜플이 새 판에 맞게 확장되지 않는 함정, 그리고 판정 행 수 꼴 확인. MEMORY.md 색인 줄도 고쳤습니다.

사용한 스킬: 없음
