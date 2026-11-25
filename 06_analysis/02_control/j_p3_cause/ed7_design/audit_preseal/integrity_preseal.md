의존성 점검: STAMP(이 세션에서 이미 점검함), 필요한 것은 모두 있음.

## 무결성 검사 요약
- 대상: 명세 `jp3_remedy_spec_v7.md`(sha 6dcccae2…, 1036줄), 근거 폴더 `ed7_design`(파일 251개, SHA256SUMS 17개), worktree `ed7-impl`(HEAD b46bdf8f, 추적 변경 0). 범위는 호출자 지정이다.
- 판정: ⚠️ 경미한 결함. 봉인을 막을 수치 불일치나 깨진 해시는 없다. 봉인 전에 정리할 문서 결함이 2건 있고, 커밋 때 알아야 할 ignore 건이 1건 있다.
- 축별 발견: A 0건 · B 1건 · C 0건 · D 5건. 합계는 High 1 / Medium 3 / Low 3(High는 B축의 ignore 건)이다.

## 발견 사항 (심각도순)

[🟠 High][B] `06_analysis/02_control/j_p3_cause/j9_runs/6bfb2560/ed7_probe_a1/` — 명세가 sha로 인용하고 고정 표의 입력이기도 한 probe 출력이 git에 들어가지 않는다.
  근거:
  - `git status --short --ignored`에서 `ed7_probe.jsonl`과 `ed7_probe_t4h/`가 `!!`로 나온다.
  - `git check-ignore -v`: jsonl은 `.git/info/exclude:107`, npz는 `.gitignore:41 *.npz`에 걸린다.
  - `large_outputs.py` 건식: jsonl 147.6 MiB는 `over_limit`(원격 한도 10**8 초과)이고, T4h npz 654개(150,217,851 B)는 `needs_add_force` 654이다.
  - jsonl은 `6bfb2560_LOCAL_ONLY.SHA256SUMS`에 sha 1줄(`1107b309…`)로 고정돼 있어 의도된 로컬 전용으로 보인다. sha는 현재 파일과 일치한다.
  - npz 654개는 그 목록에 없다. 이 npz가 고정 표와 조건 도구의 입력이다.
  - 앞서 기준선 npz 18개가 `*.npz`로 빠진 사례와 같은 유형이다.
  권장 조치: 메인이 npz 654개의 보존 방식을 정한다. `git add -f` 하거나, 100 MB를 넘는 jsonl처럼 LOCAL_ONLY sha 목록(`large_outputs.py --backup` 건식 → `--apply`)에 넣는다. 정하지 않으면 새 checkout에서 P7-3·P7-9 재현 대조가 입력 없이 막힌다. 참고: `ed7_design` 아래에는 ignore에 걸린 파일이 0개이고, `__pycache__`·`.pyc`·`~$` 파일도 없다. 다만 `ed7_design/`·`j9_runs/6bfb2560/`·`jp3_remedy_spec_v7.md`는 아직 미추적(`??`)이다.

[🟡 Medium][D] 명세 163행(개정 6 요약 표, 13절 줄) — "Q7-C10(x·y) 열림"이라고 쓰였는데 13절 본문은 닫혔다고 쓴다.
  근거:
  - 1016행: "Q7-C10 | 예측 문장 x·y | 사용자 결정 | **닫힘**(2026-11-25, 결정 9)".
  - 199행: "봉인 전 확인 필요: 없음(예측 문장 n·x·y·d까지 채움)".
  - 163행만 "열림"이라 옛 표기가 남은 것이다.
  권장 조치: 163행을 "닫힘"으로 고친다(담당: control-expert).

[🟡 Medium][D] 명세 961행(12절 공개 항목) — "O7-1~O7-7"만 판정서로 옮기라고 쓰였다.
  근거:
  - 오염 표에는 O7-8~O7-13이 있고(262~267행), 이 중 O7-8·O7-9만 979행에 따로 나온다.
  - O7-10(hydraulics가 블라인드 사본의 파일 이름 3개를 노출), O7-11(control·python의 worktree 루트 범위 검색), O7-12(메인의 권한 막힌 시도), O7-13(control의 j_p3_cause 루트 Glob)은 12절에 없다.
  - 264·266행에는 "지시 규칙 위반"과 "공개(감사 기록)"라고 적혀 있다.
  권장 조치: 961행을 "O7-1~O7-13"으로 고치거나 979행 줄에 O7-10~O7-13을 더한다(담당: control-expert). 이 항목들이 판정서로 넘어가지 않을 수 있다.

[🟡 Medium][D] 명세 41·42행(개정 3 근거 표) — 폴더 `SHA256SUMS`의 sha가 지금 파일과 다르다.
  근거:

  | 폴더 | 명세 값 | 현재 sha |
  |---|---|---|
  | `control_v7_review` | `d62c22ea…` | `ad37ad0e…` |
  | `hydraulics_v7_review` | `8ff7c74b…` | `20028dd1…` |

  - 두 SUMS는 개정 3 뒤 항목이 늘었다(control 11항목, hydraulics 3항목).
  - 명세가 같은 줄에 인용한 파일 sha(`41c99910…`, `e9827b14…`)는 그 SUMS 안의 값과 일치한다.
  - `baseline_check sums`에서 mismatch 0, missing 0이다.
  권장 조치: 봉인 전에 두 SUMS sha를 현재 값으로 고치거나 "작성 시 값"이라고 표기한다(담당: control-expert). 나머지 폴더 SUMS는 모두 명세 값과 같다(fixed_table `4160cafb`, keys_seal `b8fad2e1`, suite `37376a81`, stats_stopcond `4e4779e4`, tool_9d8e78a4 `0f793271`, probe_check 두 개 `aaa00b00`·`ede263c5` 등).

[⚪ Low][D] 명세 266·267행과 1021·1022행 — 항목 순서가 거꾸로다.
  근거: 오염 표에서 O7-13이 O7-12보다 앞에 오고, 13절에서 Q7-H8이 Q7-H7보다 앞에 온다.
  권장 조치: 순서를 바로잡는다. 번호나 내용은 틀리지 않다.

[⚪ Low][D] `ed7_design/control_v7_review/handback_spec_rev6_xy.md:6` — 줄 수 표기가 실제와 다르다.
  근거: 이 보고는 "새 sha 6dcccae2…(972줄)"이라고 쓴다. 파일 sha는 같은데 실제 LF 개수는 1036이고 CR는 0이다. 줄을 센 방식이 다른 것으로 보이고 내용 불일치는 아니다.

[⚪ Low][B] ref_check `ref_missing` 12건(master HEAD 기준)
  근거:
  - `lock_start_b.py`, `jp3_ed7_rules.py`, `ed7_key_lists.py`, `ed7_probe.py` 등은 master에 없고 `ed7-impl`(미병합)·`ed6-tool` 브랜치에만 있다.
  - `git branch --contains b46bdf8f`는 ed7-impl만 가리킨다.
  - `d_grid_keys12.json`은 브랜치 `ed6-records`의 3ecf61f1 blob에만 있다. 이 blob의 sha256은 `a995abff…`이고, 명세 554행과 코드 `D_KEY_FILE_SHA256`과 같다.
  - 실제 결함은 아니다. 봉인 뒤 실행 커밋 C가 어느 브랜치에 놓이는지에 따라 정해질 일이다.
  - 같은 ref_check에서 `ref_missing`으로 걸린 `**/ed7_probe*.py`, `**/jp3_rev7_condition.py`(265행 Glob 패턴), `confirm_g1_grid171.json,g1_pool_ed7.json`(920행 쉼표 나열)은 파일 이름이 아니라 패턴과 나열이므로 의도된 표기로 보고 제외한다.

## 확인한 항목 (차이 없음)

**수치와 표 합계**
- 7절 표는 114행이다(본 15키 × 6플랜트 = 90, D 12키 × 2 = 24).
- 범위 밖 50행(VBM 15 + VBL 15 + 감도 비감도 20), 통과 63행(39 + V0 기회 12 + 기록 12), 실패 1행으로 합계 64행이다. 실패 1행은 VBMslow `S7_e0.001`(J3 t_ready 77.1 → 102.9)이다.
- 7절의 최소 힘·사건 뒤 LEVEL 길이·`cmd` 8자·사각 트리거 수·$n_{rev}$·D6 판정 불가 라운드·J-P3 칸(조건 r/b, 최소 간격, 줄)을 control 제안 CSV a2 114행과 대조했다. 차이는 0건이다.
- 7절의 판정 칸·`cmd`·최소 힘을 `fixed_table_a2.csv` 64행과 대조해도 차이가 0건이다.
- D 24줄 가운데 최소 힘이 음수인 줄은 16줄이다(범위 −1.0472~−0.7175 kN). 이 중 최소 다리가 사건 다리인 줄은 6줄이다. 명세 724행의 "−0.72~−1.05, 16줄, 사건 다리 6·대각 짝 10"과 일치한다.
- 7절의 ΔD 중앙/최대, 사건 뒤 LEVEL 일부, 비고는 샘플 확인 수준이다. 열 전체를 전수 대조하지는 않았다.
- 감도 단위 수 산식(46 = 4×7 + 2×9 = 4위상 7행 + 2위상 9행, 4설정 합 184 − 본 40 = 미관측 144), 195 = 171 + 24, 168 = 171 − 3, 654 = 15×6×7 + 24, 독립 군집 13 = 15 − 2는 모두 맞다.
- 6.3 예측 문장의 x 0.24/0.57/1.08/1.92/3.09와 거짓 실패 0.00/0.23/2.28/12.65/37.39 %는 `r10_recompute.json`·`.txt`의 `168|null|f1` 값과 같다(txt의 E는 ×100 표기). `r10` json·txt의 sha(`971d2421…`·`d39e18a0…`)도 맞다.

**handback 원문 ↔ 명세**
- 채택 도구(`tool_9d8e78a4/handback_adoption.md`): 실패 단위 a2/a3/a4 = 3/2/3(VBM 5개·강성 예외), |D| 비율 24/47 = 0.511과 28/53 = 0.528, 결론 a2, 32개 해석 모두 a2, a3 대 a2 차이는 VBMc04 `R12_top-FR-Fs0-o0.05` 하나 — 명세 540~545행과 일치한다.
- 키 파일(`keys_seal_b46bdf8f/handback_keys.md`): 171/168/171, U832 오프셋 o0.025·o0.075·o0.075, FL-Fs4 o0.0, 겹침 0, V0 짝 171/171, seed 20261126, sha `684054ab…`·`be930b75…` — 명세 662~667행과 578행의 `ED7_KEY_FILE_SHA256` 제안 dict와 같다.
- suite: `suite_judgement.json` sha `5cca501f…`, 8688/8671/2/15(8671 + 2 + 15 = 8688), `new_failure`·`core_not_passing`·`new_skip_or_xfail` 모두 빈 목록, 기준 목록 sha `571f42a1…`, junit 복사본 sha `c88e5898…`. 명세 587행과 985행에서 인용한 값과 같다.
- probe 654줄 = 252 + 339 + 63. 252는 head-only(210 + 42), 339는 5×63 + 24이고, 252는 명세 984행에 나온다. jsonl 줄 수 654와 sha `1107b309…`가 맞다.

**해시와 개정 연쇄**
- 근거 폴더 SUMS 17개를 모두 돌려 `mismatch` 0, `missing` 0이었다.
- `unlisted`(control_v7_review 29, hydraulics_v7_review 20, tool_a6fc3dd5 1)는 하위 `probe_6bfb2560_check/`가 자체 SUMS를 가진 구조와 SUMS 파일 자신이 목록에 없는 데서 온 것이다. 다만 `tool_a6fc3dd5`의 1건은 이름을 확인하지 않았다.
- 명세에 적힌 64자 sha 50개 중 42개가 폴더 파일과 일치했다. 나머지 8개는 개정 표의 옛 명세 sha 4개(`85ce6e2a…`, `6ad1236c…`, `eae2b90b…`, `ebb79469…`)와 위 Medium의 SUMS 2개, 폴더 밖 `ed7_probe.D_KEY_FILE_SHA256` 2회 인용이다.
- 개정 연쇄는 control의 handback 기록으로 이어진다: 85ce6e2a → 6ad1236c → eae2b90b → ebb79469 → 305bbb91 → 9a0e2007 → 6dcccae2. 개정 6의 직전·새 sha가 서로 맞물린다. 옛 명세 파일 사본은 없어서 개정 2~4와 개정 5의 본문 자체는 sha 재계산을 못 했다.
- 8절 밖에서 인용한 폴더 밖 파일의 현재 sha가 인용값과 같다: `v5/main.jsonl` `9ad74990…`, `confirm_b_grid192.json` `4e80e69b…`, `ed7_probe.identity.json` `16116fa2…`, `condition_ad7a716e.json` `9bd2dba8…`, 판 6 판정서 `e40c35d4…`(커밋 f2fddc68 blob `00bca52b…`과 일치), `probe_keys_ed7.json` `189dbb13…`.
- `adoption_b46bdf8f.json`은 `status: decided`, 결론 a2, 읽기 이름 `j7=ed7_new stiffness=sens_exempt plants=vbm5 ratio=known_shots n_rev=sum`이다. 코드 `FIXED_READING_VALUES`와 같다.
- 커밋 sha 실재: 79495405, 6bfb2560, 9d8e78a4, ad7a716e, a6fc3dd5, 96dd7bf2, f2fddc68, 3ecf61f1 모두 존재한다.

**참조 번호**
- 절 번호 0~13과 부록 A는 연속이고, P7-0~10, Y7-1~8, O7-1~13, Q7 항목이 모두 정의돼 있다. `md_links.py` 결과 깨진 링크는 0이다.

**코드 ↔ 명세 (b46bdf8f, `03_src`·`04_scripts`·`05_tests`만)**
- 명세 174~197행 줄 번호 표가 b46bdf8f와 일치한다. 대상은 c2.py 1599·2910·1980·7815·7826·7856·7820~7822·7836·7838·7518~7525·7906·9791·9840~9857, lock_start_b.py 1006~1014, ground_contact.py 991~993·918~929·1239, two_pressure.py 1777·1780, run_v5.py 390·847~848, harness_hydraulics.py 100·932, jp3_ed7_rules.py 40·59, ed7_key_lists.py 20·21·77·79·141·278·283·284, jp3_12b_plan.py 187·212·586 등이다.
- 확인한 상수와 이름:
  - `J7_EXEMPT_WARNINGS` = {`STIFFNESS_WARNING`}, 판정은 `bool(names) and names <= J7_EXEMPT_WARNINGS`(명세 608행과 같음)
  - `FIXED_READING`(ed7_condition3_adoption.py 369)
  - `level_done`·`twist_over_limit`(`entries`) 키, `LevelDonePath` 값 `strict`/`relax`, T4h `lsb_ib_twist_load_N`(코드는 `ib_twist_load_N`에 `lsb_` 접두, 시험에서 확인)
  - `HEAD_ONLY_STATE = "head_only"`, `HEAD_ONLY_KEY = "head_only_declared"`, 판단 순서 meta → 줄(명세 476행과 같음)
  - `ED7_BLIND_PREFIXES` 세 항목(`VBK_c92*`, `VBK_c93*`, `logs`)
  - `ED7_KEY_FILE_SHA256 = {}`와 `JP3_SPEC_EDITION_V7 = "85ce6e2a"`는 아직 봉인 전 값이다.
  - 태그 기저 `final_C4G2_P3X`, 구성 요소 `A_ib`, meta `probe_d6_settings`·`p1_patch`, 키 `stale_seed_release`, 설정 이름 `VBKM`·`VBMc005` 등
- 본문의 79495405 줄 인용도 79495405 blob에서 확인했다(`HOLD_SPEED_RATIO` 171, lock_start_b.py 164, 3801~3808, 702~708, 628~630, harness 599~600·699~704·844~857, judge_stage1_4368.py 173~175·293~307, two_pressure.py 617~622·1742~1763). 이 줄들은 b46bdf8f에서는 줄이 달라진 곳이 있지만, 명세가 "79495405 기준"이라고 밝혔고 개정 6 재확인 표에서 다룬 항목만 b46bdf8f 줄로 적혀 있다.

## 검사하지 못한 것
- 개정 2·3·4의 옛 명세 본문(사본 없음)은 sha 재계산을 못 했다. handback의 sha 기록으로만 연쇄를 확인했다.
- 7절의 ΔD 중앙/최대 칸은 전수 대조하지 않았다.
- `ed7_design`의 직접 참조 파일(`handback_*`, `d7_dynamics_review.md` 등) 안의 서술 수치는 명세가 인용한 부분만 봤다. 전체 문서 내용은 읽지 않았다.
- 판 6 쪽 인용(`ed6_design/…` SUMS `57d0faa7…`, `ed6_p2_79495405` `07a003ba…`)은 접두 8자만 파일 목록으로 대조했다. 머리말 212행의 `06ed0384…`(`v5_criteria.md`)는 `ed7_design` 밖이라 확인하지 못했다.
- 블라인드 경로(`606f8713/cdry_a1/VBK_c92*`, `VBK_c93*`, `logs/`)는 메인 checkout과 worktree 사본 모두 열거나 검색하지 않았다. `j_p3_cause`·`j9_runs`·`06_analysis`·worktree 루트를 대상으로 Grep·Glob은 하지 않았다.

## 절차 공개
- 내 스크립트가 `j_p3_cause` 최상위의 파일 목록(`os.listdir`)을 한 번 읽었다. `os.walk`로는 `ed7_design`, `ed6_design`, `ed6_p2_79495405`만 순회했다. `j9_runs`는 순회하지 않았고, 블라인드 경로의 이름·건수·내용은 접하지 않았다.
- `git ls-files --others --ignored --exclude-standard`와 `large_outputs.py`는 `j9_runs/6bfb2560`(블라인드 아님)만 대상으로 돌렸다.
- 점검 도중 `%TEMP%\x.tmp` 작은 임시 파일 하나를 만들었다가 바로 지웠다(`Test-Path` False 확인). 대상 폴더에는 쓰지 않았다.

## 사용자 조치 필요
- 없음.

## 실행한 검증
- `baseline_check.py sums`를 SUMS 17개 각각에 실행했다(모두 mismatch 0, missing 0). 파이썬 스크립트 `shachk`로 64자 sha 대조와 8자 접두 대조를 했고, `tab7`·`tab7b`로 7절 표 파싱·CSV 대조를 했다.
- `md_links.py --check-code-paths`: 깨진 링크 0. `ref_check.py`: `ref_missing` 12(위 Low), `ref_untracked` 52.
- `git rev-parse`, `branch --contains`, `show <rev>:<path>`로 커밋 존재와 79495405·b46bdf8f 줄을 확인했다. D 키 blob 3ecf61f1의 sha256은 파이썬으로 계산했다.
- `git check-attr text`: 세 대상 모두 `text: unset`이다. CRLF는 spec이 LF 1036, CR 0이라 해당 없음이다.
- 검사용 인터프리터는 python-dev(`-I -B`)이고, 표 재계산에 행렬 연산이 없어 `MKL_THREADING_LAYER` 문제는 걸리지 않았다.
- 감사 도중 대상 파일이 바뀌지 않았음을 `source_guard verify`로 확인했다. 최종 판정은 보고 직전 다시 읽은 값(sha·줄 번호) 기준이다.
- 사용한 스킬: 없음
- scratchpad `integrity-ed7seal\`는 지웠다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v7.md 6dcccae2…, 트리 ed7_design 파일 251개 manifest 89d15088…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
