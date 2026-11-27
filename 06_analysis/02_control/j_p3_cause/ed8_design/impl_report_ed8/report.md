# 판 8(436.9 J-P3 보완) 구현과 P8-16 사전 실행 보고 (python-expert, 2026-11-26)

판 8 구현을 ed8-impl에 커밋하고 단위 시험을 통과시켰습니다. P8-16 사전 실행은 54/54가 기준과 같아 통과했습니다. 구현 수정 없이 첫 시도에 통과했습니다. 지시대로 **C8을 만들기 전에 멈췄습니다**.

의존성 점검: 이번 세션에서 이미 점검한 상태(STAMP)이고, 필요한 도구는 모두 있습니다.

## 1. 커밋 (worktree `C:\workspace\outrigger_control\.claude\worktrees\ed8-impl`, 브랜치 ed8-impl, clean)

| 커밋 | 내용 |
|---|---|
| `66648ea8f5c3640955493a9e088b5dada8c52027` | 구현 Y8-1~Y8-10, 시험 |
| **`27c0f046eb15eaa83b4df7d547bcd22ada9de59a`** (HEAD, C8의 부모 후보) | run_v5 판 8 배치(`ed8_t8`·`ed8_cases`·`ed8_keys`·`ed8_heldout_v0`·`ed8_heldout_aa2/aa3`). `ED8_KEY_FILE_SHA256`는 빈 표이고 C8에서 채웁니다 |

- 두 번째 커밋을 따로 만든 이유: P8-10은 C8에 sha 표·시험·run steps만 허용합니다. 그래서 실행 경로 모듈인 run_v5의 배치 배선은 구현 커밋에 들어가야 했습니다.
- master·다른 worktree는 건드리지 않았습니다. 정션·링크도 만들지 않았습니다. 새 파일과 바뀐 파일은 커밋 전에 CRLF로 정규화했습니다.

바꾼 파일 17개(7fc83456 → 27c0f046):
- `03_src/outrigger_sim/control/`: `c2.py`, `ground_contact.py`, `lock_start_b.py`, `two_pressure.py`
- `03_src/outrigger_sim/hydraulics/v5_options.py`
- `04_scripts/04_hydraulic/coupled/`
  - 고친 파일: `run_v5.py`, `verdict_runs.py`, `verdict_cases.py`, `harness_hydraulics.py`, `ed8_probe.py`
  - 새 파일: `ed8_key_lists.py`, `p816_compare.py`
- `05_tests/unit/`
  - 새 파일: `test_ed8_impl.py`(47개), `test_ed8_impl_harness.py`(5개), `ed8_check_runner.py`
  - 기대값 갱신: `test_jp3_rev6.py`, `test_ed8_records.py`

## 2. Y8별 대응

| # | 구현 |
|---|---|
| Y8-1 PSW | **설정**: `ProbeSettings.scale_mid_min_piston_travel_m`(None이면 꺼짐).<br>**스케일 mid**: 다리 첫 탐침 주기의 피스톤 판독을 x₀로 둡니다. 지금 mid 이상이고 ext 전인 읽기 중, first_sign·(x−x₀) ≥ δ인 첫 읽기입니다(유지 구간 읽기 포함, ext 읽기 제외). `_step_rect`는 바꾸지 않았고, rect 프로필에서는 K1_sc = K1입니다.<br>**계산식** `psw_scale_stiffness_N_m`: mid가 없으면 K1, 스케일 mid가 없거나 이동 < 0.2 mm면 NaN.<br>**`ProbeResult` 새 필드 3개**: `scale_stiffness_N_m`, `scale_mid_shift_periods`, `moved_by_mid_m`.<br>**제어기**: `c2._psw_scale_ratios`(`_update_twist_stiffness_scale`만 부름)가 지금 조건 ∧ 유한 ∧ > 0.3 S_ii,nom인 다리만 씁니다.<br>**P-1 기록**: 다리별 `scale_k_N_m`·`scale_ratio`·`scale_mid_shift_periods`·`moved_by_mid_m`·`is_psw_scale_leg`를 PSW가 켜졌을 때만 남깁니다. |
| Y8-2 | **설정 경로**: `C2Config.with_ed8()`와 `HydraulicOptions.ed8_settings`(비면 꺼짐)로 경고 (0.8, 3.6), PSW, H3′, L-2를 켭니다.<br>**설정**: `run_v5.ED8_SETTINGS`(VBN, LSN1~4, VBN0, VBN⟨10키⟩, VBKN, VBKN0)를 ALL·T4H·ROD_FAULT 목록에 넣었습니다.<br>**태그**: `_ED8`을 맨 뒤에 붙입니다(`_split_tail`이 `_ED8` → `_TCL` → `_LSB` 순서로 뗌). `with_switch_tags`는 `C2Config.has_ed8_changes`일 때 `_ED8`을 붙이고, `with_lock_start_b_tag`는 `_ED8` 뒤에 `_LSB`를 다시 붙이지 않습니다.<br>**태그 실측**: VBN `final_C4G2_P3X_LAS_K1_LSB_ED8` → rev 7, LSB 참. VBN0 `final_C4G2_LAS_K1_LSB_ED8` → rev None, LSB 참. 옛 태그 16개는 결과가 모두 그대로입니다(표 시험).<br>**정체성 가드**: `check_ed8_config`.<br>**meta**: `ed8_settings` = {`probe_k1_scale_settings`, `r8.stiffness_warning_range`, `r8.lifted_reapproach`(H3′), `twist_completion_relax`(L-2)}. |
| Y8-3 R2 | `ProbeD6Settings.witness_mode`("judge" 기본 / "record"; record는 witness가 켜져 있어야 함). `D6Witness.is_record_only`이면 D6를 판 6 규칙으로 판정하고 사건은 내지 않습니다. 다리별 `not_opened_rounds`·`would_warn`을 기록합니다. `to_meta`는 "judge"일 때 이 키를 빼므로 판 7 meta는 그대로입니다. |
| Y8-4 | **완료 플래그 분해**: T4h `ed8_done_flags`(on_target, 간극, 비틀림, complete).<br>**A(i) 일화**: `lsb_record.a1_episodes`(끝 사유, 바닥 최대).<br>**잠긴 다리 명령**: T4h `ed8_held_legs`(플랜트 잠김 ∧ \|u\| > 0).<br>판 8 제어기에서만 이 기록을 남깁니다. 줄 키 `ed8_settings`·`ed8_record`를 `LINE_RECORD_KEYS`에 추가했습니다. |
| Y8-5 | `_ED8`·VBN·LSN·VBKN 토큰 재점검(03_src·04_scripts·05_tests·00_docs·02_params): 새 코드 밖 충돌은 0입니다. 명세가 이미 언급한 `verdict_runs._ED8_RECORD`만 있습니다. |
| Y8-6 | `ed8_key_lists.py`:<br>**census**: 1043줄. C-J 388·C-S 460·C-D 24·C-G 171이고, 0c′ 사건 이름 출처 집계는 건수만 담습니다.<br>**heldout**: 339슬롯(171·48·120). 슬롯은 (원천, 슬롯 키) 순서이고, `default_rng(20261127)`로 슬롯마다 `integers` 다음 `permutation`을 뽑습니다. 깨끗한 군집은 저장 V0 격자의 모든 저장 위상이 통과인 군집이고 G1의 171군집과 같음을 단언합니다. twin 필드는 `EventTwin`과 대조합니다.<br>**층 함수**: `stratum_of`·`event_of_job`·`main_line_starts`·`grid_run_starts`(run_id 정수화). 둘 다 결정적입니다. T8 판정 도구는 만들지 않았습니다. |
| Y8-7/8 H3′ | **설정·규칙**: `LiftedReapproachSettings.short_run_s`(None이면 꺼짐)·`short_run_exit_samples`(4)와 `exit_samples_of`. 재트리거가 아니고 t − start ≤ T_r + tol이면 4표본을 요구합니다.<br>**`_Reapproach` 기록**: `exit_required_samples`·`short_run_extended`·`ordinary_end_s`·`handover_diagonal_load_N`.<br>**event_output**: `reapproach_ends`·`lift_intervals`. |
| Y8-9 | `EventTwin.depth_m`·`ramp_s`(둘 다 주거나 둘 다 None). `verdict_runs.event_shape`, `GRID_TWIN_FIELDS` 추가와 T4h 이름 `-d…-r…`. 새 필드가 없으면 이름도 경로도 그대로입니다. |
| Y8-10 L-2 | **설정**: `TwistCompletionRelaxSettings.locked_drift_waiver`·`waiver_max_rise_N` 2.5 kN·`waiver_margin_N` 0.5 kN.<br>**계수**: `LockStartB.still_periods`를 매 `apply_floors` 뒤에 셉니다(`p814_rerun.py` 203~276행과 같은 조건, LEVEL 밖은 0). `_is_twist_relax_ok`는 비상승이 거짓일 때만 `_is_locked_drift_waived`를 부르고, 직전 주기까지의 값을 읽습니다.<br>**기록**: `twist_relax` meta에 `n_waiver_done`·`waivers`·`n_waiver_periods`·`waiver_periods`. |
| ed8_probe | **새 팔**: `a8`(=VBN), `a8_psw_off`·`a8_h3_off`·`a8_l2_off`(P8-5·8·15), `B_impl`(a2w+H3′), `L2_impl`(+L-2), `a2w_psw`(P8-6).<br>**새 플랜트** `KM0`(③ 끔, VBKM0 플랜트): 기본 `--plants`에서는 빠집니다.<br>**`--part p816`**: 27키. r79 4키는 P8-14와 같이 실행합니다(`R79_ROD_MODEL=plant_truth`, `sys.argv[1]`=checkout, `--r79-plan` sha `99e50653…` 단언).<br>**비교 도구** `p816_compare.py`: 종료 0 통과 / 1 실패 / 2 입력 / 3 도구 오류. |
| 정리 | `lock_start_b.py` docstring 두 곳: `b3_travel_cap_fraction`(47b184af 문구)과 `command_pre_twist`("가장 빠른 다리"). 동작은 바뀌지 않습니다. |

## 3. 시험 결과

**실행 명령**: worktree 루트에서 Chrono-dev `python -B -m pytest 05_tests/unit -n 12 --dist loadfile -p no:cacheprovider`, `OUTRIGGER_RECORDS_ROOT=C:\workspace\outrigger_control`.

**기준선**: 7fc83456을 `git archive`로 풀어 scratchpad에서 돌렸습니다. 결과는 **20 실패 / 8523 통과 / 138 skip**입니다.
- 기준선 실패 중 13건은 "git 저장소가 아님"(풀어 놓은 트리라서 생긴 문제)입니다.
- 기준선 실패 중 2건은 기존부터 실패하던 시험입니다: `test_hydraulics_flow_limit_run`(worktree에 07_results 없음), `test_d8x_diag`.

**66648ea8 전체 suite**(E 코어에서 P8-16과 동시 실행): **3 실패 / 8595 통과 / 134 skip**.

| 실패 | 판정 |
|---|---|
| `test_hydraulics_flow_limit_run::test_coupled_batch_rows_and_resume` | 기준선에도 있는 기존 실패 |
| `test_d8x_diag::test_rerun_gives_the_stored_command_hash` | 기준선에도 있는 기존 실패 |
| `test_k2_post_audit_fixes::test_acc_d8_error_row…` | 600 s 시간 초과입니다. E 코어 경합 때문입니다. 단독 재실행에서 82 s로 통과했습니다 |

**새 실패·새 skip**
- 새 실패: 0(위 시간 초과 1건은 단독 통과로 확인).
- 새 skip: 0. 시험 ID로 대조했고 pass → skip은 0건입니다. 대조 결과는 `tests\junit_diff_base_vs_66648ea8.txt`에 있습니다. xfail은 0입니다.

**커밋 전 worktree 실행에서 고친 것**
- `test_jp3_rev6`(ROD_FAULT 목록에 VBKN·VBKN0 추가)와 `test_ed8_records`(기본 계획 수에서 KM0 제외): 명세가 요구한 변경에 맞춰 기대값만 갱신했습니다.
- `test_s8_soil_restore` 10건: xdist 파일 배치에 따른 순서 의존 실패였습니다. 단독 실행과 66648ea8 전체 suite에서는 통과했습니다.

**27c0f046 이후 다시 돌린 것**
- `test_ed8_impl.py` 47개, `test_ed7_run_commit`·`test_ed7_units`·`test_ed6_prelock`·`test_jp3_rev6`·`test_ed8_records` 170개가 모두 통과했습니다.
- 전체 suite는 27c0f046에서 다시 돌리지 않았습니다. 바뀐 것은 run_v5 배치와 시험 1파일뿐입니다.

**명세 16절 시험 행 대응**
- **N-1 전제 1**: PSW 켬·끔에서 `ProbeResult` 기존 필드가 비트 단위로 같습니다.
- **N-1 전제 2**(AST 정적 시험): 새 필드를 읽는 곳은 `c2._psw_scale_ratios`뿐이고, 이 함수를 부르는 곳은 `_update_twist_stiffness_scale`뿐입니다.
- **합성 시험**
  - PSW: 고착 뒤 이동, 역순, ext만 이동이면 NaN, rect 프로필.
  - H3′: 짧은 첫 실행 3 → 4표본, 재트리거 실행은 3표본, 시작 뒤 정확히 0.5 s는 4표본, T_r 뒤는 3표본.
  - L-2: 상승 2.5 kN, n_still 49/50, \|D\|+0.5 = 15 kN 경계와 한 주기 늦은 계수.
  - 층 판별: twin/기본값, FS24·G4 → N, 깊이 변형 RE1bF → E 후보, 결측 → `setting_defect`, `fast` 무시, 음수 시작 무시, round(t, 3) ≤ 0.450 경계.
- **기타 시험**
  - 태그 표.
  - 옛 설정에서 새 코드 줄이 돌지 않음: 새 함수를 예외로 바꿔 끼운 시험입니다.
  - 키 파일 결정성(P8-10 재생성의 바탕).
  - 배치 수: 1043 / 339 / 678 / 44 / 10.
- **`p816_compare`**: 생산자 꼴 입력으로, CWD를 입력과 다른 폴더에 두고 `main`을 끝까지 돌렸습니다. 결과는 통과·불일치·결측·오류 줄·추가 키·기존 `--out` → 2·기준 sha 다름 → 2입니다.
- **하네스**(dynamics-dev, `test_ed8_impl_harness.py` 5개 통과)
  - **P8-6**: 방향 A 1회차 K1_sc가 `k02_legs.csv` `a0.05_k1`과 상대차 ≤ 1e-9입니다. 대상은 R12 top-FR-Fs8 o0.0 × {M, Mslow, Mh15, L}과 R7 e0.0 × M이고, 16다리 이상을 비교했습니다.
  - **생산자 꼴**: VBN 사건 행, VBN S8(head-only), VBN0 R16에서 `_ED8` 태그, `ed8_settings`·`ed8_record`, R2 증인 사건 없음, `reapproach_ends`·`lift_intervals`, T4h `ed8_done_flags`·`ed8_held_legs`·`lsb_ib_block`, PSW 라운드 필드를 확인했습니다.
- **미구현·미검증**: T8 판정 도구(나중 단계). P8-0의 114줄 대조는 이번에 돌리지 않았습니다(7절).

**정적 검사**
- ruff(프로젝트 설정): 내가 쓴 코드는 통과입니다. run_v5 argparse help E501 3건과 harness_hydraulics 21행 E501은 기존 위반입니다.
- codespell: `ABL` 7건만 나왔고 태그 이름이라 오탐입니다.

## 4. P8-0 확인 방법과 결과
- 새 필드는 모두 클래스 기본값이 꺼짐입니다. `R8_D1_SETTINGS`와 판 7 설정 값은 바꾸지 않았습니다.
- 옛 설정의 options dict에는 `ed8_settings`·`witness_mode`가 없습니다(전체 `ALL_SETTINGS` 시험).
- 기존 `test_ed8_harness`의 저장 해시 8 job 대조(V0·VB·VBM·VBM0·LSM4·VBMslow·P7-M-a2 등)는 전체 suite에서 통과했습니다.
- `test_ed7_harness`(판 6 설정 해시)도 통과했습니다.
- ed7_probe a2 114줄 대조는 4단계 P8-4 항목으로 남겼습니다(7절).

## 5. P8-16 결과

**시점 1: 구현 커밋에서**

| 실행 | 출력 | 결과 |
|---|---|---|
| 66648ea8 | `…\ed8_design\p816_prerun_66648ea8\` | **54/54 같음**(B_impl 27, L2_impl 27). `p816_compare.json` sha `cb9e75a4…`, SUMS `fd9605f1…` |
| **27c0f046**(최종 구현 커밋) | `…\ed8_design\p816_prerun_27c0f046\` | **54/54 같음**. 시작·끝 HEAD 27c0f046, clean. `p816.jsonl` `1fb3a42e…`, `p816_compare.json` `46fec3f0…`, SUMS `384431fe…`(64항목) |

**재시도 경과**
- 구현을 고친 일은 없습니다. 불일치는 0회입니다.
- 66648ea8 실행 중 한 번 멈췄습니다.
  - **증상**: Pool 워커 하나가 흔적 없이 사라져 53/54에서 대기했습니다. 빠진 job은 `P8-M-L2_impl R16 o0.05`입니다.
  - **확인**: `proc_snapshot`과 `py-spy`로 부모가 `pool.next`에서 기다리고 워커는 모두 놀고 있음을 확인했습니다.
  - **조치**: 내가 띄운 PID만 지정해 종료한 뒤 `--resume`(같은 계획)으로 그 1줄을 다시 돌렸고 기준과 같았습니다.
  - 27c0f046 실행은 중단 없이 끝났습니다.

**실행 조건과 기록**
- 실행 방식: `conda run --no-capture-output -n dynamics-dev python -I -B`(P8-14와 같은 방식), `MKL_THREADING_LAYER=TBB`, `OMP_NUM_THREADS=1`.
- `NUMBA_CACHE_DIR`는 scratchpad에 두었습니다(worktree 밖, 실행 뒤 삭제).
- 마스크 0xFFFF, 워커 8, 약 10분.
- `reserve.py` prune·list 결과 다른 예약은 0이었습니다. 실행할 때 예약하고 끝난 뒤 해제했습니다.
- 러너 스크립트(`run_p816.ps1`, `resume_p816.ps1`)는 각 출력 폴더에 보관했습니다.

## 6. C8 초안 (커밋하지 않음)
- **키 파일 초안**: `…\ed8_design\impl_report_ed8\keys_draft\`
  - 66648ea8 코드로 만들었습니다. 생성기는 27c0f046에서 바뀌지 않았습니다.
  - `census_keys_ed8.json` sha256 **`278b332f694405d5f9be432467e294b64492d5ffd638a76986e819460c88c535`**
  - `heldout_g_ed8.json` sha256 **`a18b5818734f1b10840c903fb9e4b5c140f619705048344f9ea48d16d3142ee5`**
  - 두 번 생성해 같은 바이트가 나왔습니다.
- **C8 계획 초안**: `…\impl_report_ed8\c8_draft\c8_plan_draft.json`(단계별 명령·줄 수).
- **run steps 초안**: `…\impl_report_ed8\c8_draft\numba_cache_ed8_fragment.ps1`
  - `NUMBA_CACHE_DIR` = `~/.claude/runners/outrigger-ed8/numba_cache/<C8 앞 8자>`로 둡니다(worktree·j9_runs 밖).
  - 경로가 그 안에 있으면 종료 3입니다.
  - 단계 앞뒤로 worktree `04_scripts`의 `.nbi/.nbc` 0개를 단언합니다.
  - 모든 실행 환경에 주입합니다.
  - 전체 run steps(`common_ed8.ps1` 등)는 C8 작업으로 남겼습니다.
- **시험 근거**: `…\impl_report_ed8\tests\`(junit 3개, 대조 스크립트·결과).

## 7. 메인 세션 권고 (직접 띄우지 않음)
- **P8-0 114줄**(4단계 P8-4)
  - 명령: C8 worktree에서 `ed7_probe.py --arms a2 --part all`을 돌리고, `j9_runs\b46bdf8f\repro_a2\ed7_probe_a2.jsonl`과 job별 `commands_sha256`를 대조합니다.
  - 예상 시간: 판 7 기록 기준 20워커 약 15분, 8워커면 30분 이상입니다.
- **P8-5·P8-8·P8-15**: 4단계 C8에서 `ed8_probe --part p816 --arms a8,a8_psw_off` / `a8,a8_h3_off` / `a8,a8_l2_off`로 돌립니다(`c8_plan_draft.json`). 각 46~54줄, 약 10분입니다.

## 8. 확인 필요
1. **`has_ed8_changes` 정의**: H3′만 켠 `B_impl`도 `_ED8` 태그와 판 8 기록을 갖습니다. 명세 3.6은 "판 8 config 스위치일 때 `_ED8`"이라고만 적어 두었습니다. 명령에는 영향이 없습니다(P8-16 54/54). 지금 정의를 유지할지 정해 주십시오.
2. **G′ 깨끗한 군집 판정**: 저장 격자 192군집 중 48군집은 저장 위상이 2개(0·0.05)뿐입니다. 그래서 "모든 저장 오프셋 통과"로 판정했습니다. 결과는 171·48·40가족으로 명세 수와 같고, G1 171군집과도 같습니다.
3. **H3′ 기록 범위**: `_Reapproach` 기록은 H3′가 켜진 설정에서만 남깁니다. 끔 팔(`a8_h3_off`)에는 `exit_required_samples`가 없습니다. P8-8은 켬 팔의 `short_run_extended`로 판정한다는 해석입니다.

## 9. 공개 (행위 그대로)
- **블라인드 경로**: 열지도, 검색 범위로 쓰지도 않았습니다.
- **Grep·Glob path로 쓴 곳**
  - worktree 하위 폴더: `03_src\outrigger_sim\control`, `03_src`, `04_scripts`(코드 glob `*.py`), `04_scripts\04_hydraulic\coupled`, `04_scripts\03_control\s8`, `04_scripts\03_control\s9`, `05_tests\unit`, `00_docs`, `02_params`, `06_analysis\02_control\j_p3_cause\prelaunch_j9\run_steps`(worktree 사본)과 `run_steps_ed7\common_ed7.ps1` 파일 지정.
  - 메인 checkout: `ed8_design\stats_s8r\report.md`(파일 지정), `ed7_design`(glob `*.md`), `ed8_design`(glob `*.md`).
  - `04_scripts` 폴더 자체를 path로 쓴 Grep은 3회입니다(glob `*.py`: `_ED8|VBN|LSN|VBKN` 건수·내용, `apply_controller_options|check_probe_d6_config`, `check_last_probe_d6`). 블라인드를 품지 않은 코드 폴더 전체 검색입니다(O8-11과 같은 꼴).
  - Glob은 worktree `04_scripts` 하위로 `**/s9_merge*`를 1회 썼습니다.
- **연 데이터 파일**(스크립트 포함, 파일 지정)
  - 명세 v8, 설계 보고 7개, `p814_rerun.py`, `p89_rerun.py`, P8-14 `provenance.json`·`console_1.txt`
  - P8-16 기준 `raw/runs.jsonl`(구조·해시), `k02_legs.csv`, `layer_keys_0c.py`, `s8r_frame.py`
  - `j9_runs\8a2a52ce\j9main_a1\j9_main.jsonl`(job 키만)
  - `sens_keys_ed7.json`, `confirm_g1_grid171.json`, `confirm_b_grid192.json`, git blob `d_grid_keys12.json`
  - `touch_phase\acceptance\c4g2_only\grid\` 저장 V0 격자 4개(pass 플래그와 위상 구조). 이 폴더는 비재귀 Glob(`grid_r6*.json`)과 `*.json` 목록을 한 번씩 했습니다.
  - 층 값(E/N)이나 재접근 시각은 실제 자료로 계산하지도 출력하지도 않았습니다.
- **실행 규칙**
  - Bash에서 `git diff --stat … | tail -3` 파이프를 2회 썼습니다(규칙 위반, Suspended 없음).
  - 처음 P8-16 러너를 잘못된 ExpectCommit으로 띄웠는데 HEAD 불일치로 종료 3을 내고 출력은 만들지 않았습니다.
- **scratchpad·worktree 정리**
  - scratchpad `python-ed8-impl\`(기준선 트리, numba 캐시 포함)은 지웠습니다.
  - worktree에는 무시 대상 `__pycache__`가 남아 있습니다(하네스 시험이 만든 것, git clean 상태에는 영향 없음).

## 메모리 반영안
- `env_pool_lost_task_hang.md`(새로 씀): spawn Pool `imap_unordered`가 사라진 워커의 작업을 잃고 n−1에서 영원히 기다린 사례입니다. `proc_snapshot`, 내 PID만 종료, `--resume`. MEMORY.md 색인 줄도 더했습니다.

사용한 스킬: 없음
