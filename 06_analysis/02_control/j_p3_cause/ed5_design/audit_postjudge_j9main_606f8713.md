## 감사 요약
- 본 결과: `j9main_a1/judge/j9main_judge.json`(항목 목록·관문 이름·건수·detail 문자열), `j9_main.jsonl`과 `v5/main.jsonl` V0 100줄(J1 pass·gates, J2 최소 힘, t_back, t_ready, final_phase, n_rev, lock_window_alignment, soil_stop_crawler, extend_bound_check 합), `v0_sample.json`, `l1_input_guard.json`, `_identity_checks/j9main_a1*.md`, `step_record.json`. 이 감사는 판정 뒤 감사라서 수치를 본 것이 규칙에 맞습니다. `cdry_a1/VBK_c92*`·`VBK_c93*`·`cdry_a1/logs/`는 열지 않았습니다.
- 대상·시점·기준 문서: 판 5 step8 j9_main, 시도 a1. 판정 후 감사입니다. 실행 커밋 606f8713, 도구 커밋 74a4bbf4입니다.
  - 기준 문서: `jp3_remedy_spec_v5.md`(fe6f5844), 정오 1~8(정오 2 639c54e9, 정오 8 8c420e85), `v5_criteria.md`(06ed0384)와 rev1~rev12b.
  - seal_check 결과, 봉인 26판 모두 raw 일치입니다. 봉인이 없는 것은 draft 두 개뿐입니다.
- 판정: 차단 0 / 실행 전 수정 2 / 기록 5. **판정 "실패(종료 1)"는 규칙상 확정입니다. 도구 결함 때문에 다시 판정할 필요는 없습니다.**
  - 아래 차이는 모두 "실패 1건 이상"이라는 결론을 바꾸지 않습니다. 규칙대로 세도 실패는 75 항목(짝·항목 72)입니다.

## 발견 사항 (심각도순)

[실행 전 수정][R·C] R15 J1 2건이 2-9.3 "기준선 실패"인데 77에 들어갔습니다. `baseline_failures.counted: 0`은 계산한 값이 아니라 상수입니다.
- 규칙 원문: `jp3_remedy_spec_v5_erratum2.md:220` "같은 짝에서 V0도 그 항목을 실패하면 VBJ 실패로 세지 않는다". `:223`은 R15를 예로 직접 듭니다: "R15에서 V0도 실패한 다른 항목(예: … J1 `event_output.pass`)은 … 기준선 실패로 기록만 한다". `v5_criteria.md:55`의 사건 행 J1은 `event_output.pass`이고, "V0 통과가 설정에서 실패"일 때 실패입니다.
- 도구가 세는 방식: J1을 관문 단위로 셉니다(`judge_stage1_4368.py:216-223` D-07, "V0에 없던 관문 실패"마다 항목 하나).
  - R15 두 위상에서 V0도 J1을 실패합니다(관문 `Fmin_after_W`·`U832_pair_union`, 0.05에는 `U57_outside`도). VBJ는 새 관문 `end_att` 때문에 J1 실패 2건으로 셉니다.
  - `jp3_j9main_judge.py:723-724` 문서 문자열은 "a J item fails only where the reference passes it, D-07 .. D-17 by construction"이라고 적지만, 관문 단위인 D-07에서는 이 말이 맞지 않습니다. `:729`의 `"counted": 0`은 고정값입니다.
- 재집계(독립 스크립트): 도구의 J1 37건은 관문 단위로 다시 세면 정확히 같습니다. J1이 아닌 40건도 같습니다. 항목 단위로 세면 R15 J1 2건이 기준선 실패로 빠집니다.
- 실패 시나리오: 다음 판정에서 V0가 이미 실패한 항목에 새 관문 실패만 생기면, 규칙상 통과(기록)인 줄이 실패(종료 1)로 나옵니다. 안전 쪽으로 어긋나는 것이지만 규칙과 다릅니다. 시험(`test_jp3_j9main.py:224-239`)은 V0와 VB에 같은 관문만 주므로 이 경우를 보지 못합니다.
- 권장 조치
  - 해석(확인 필요): R15에서 V0가 실패한 J1에 새 관문이 더해지면 기준선인지 실패인지 control-expert가 정합니다. `:223` 예시는 최소 힘 관문만 말합니다.
  - 기준선으로 정하면 python-expert가 고칩니다: J1 기준선 판정을 항목 단위로 하고, `counted`를 계산값으로 바꾸고, 시험(V0 관문 {A} 대 설정 {A, B})을 더합니다.
  - 이번 판정서에는 "77 = 관문 단위 항목 수. 2-9.3 항목 단위로는 75 항목, 짝·항목 72"를 함께 적습니다.

[실행 전 수정][E·R] S8 F-5 판정 불가 20건은 하네스 구조 때문이라 이번 실행의 설정 결함이 아닙니다. 다만 이대로면 j9_main은 종료 0에 닿을 수 없습니다.
- 근거
  - S8 줄 20개(VBJ 4, LSJ1~4 각 4)는 모두 `soil_stop_crawler.after_stop_chunks` = 0이고, `margin_at_stop_kN`·`max_after_stop_kN`이 None입니다.
  - 저장 V0 S8 4줄도 똑같습니다(after 0, None).
  - `verdict_metrics.py:621-623`: "A run that ends at the stop (the reduced harness stops at the FAULT) has no after-stop chunk: … None". 축소 하네스는 정지에서 끝나므로 6절 조항 "정지 뒤 크롤러 하중"을 잴 표본이 없습니다.
  - 도구는 None을 판정 불가로 둡니다(`jp3_j9main_judge.py:554-559`, 재감사 경고 3). 규칙(`v5_criteria.md:112-122`, 정오 2 2-9.3 `:225`)은 이 경우를 정하지 않았습니다.
  - 정체성·명령은 정상이고 V0도 같으므로 설정 결함이 아닙니다.
- 실패 시나리오: J 실패가 0이어도 S8 20건 때문에 항상 종료 2가 됩니다. 그러면 4a-5 5.3의 재실행 경로나 사람 판단으로 넘어갑니다.
- 권장 조치: control-expert가 다음 판 전에 개정 문장으로 정합니다. 예: "축소 하네스 S8은 FAULT에서 끝나므로 F-5 조항과 6절 멈춤 값은 하네스에서 해당 없음(Chrono 몫)으로 기록한다", 또는 하네스에 정지 뒤 구간을 더합니다. 이번 판정서에는 2-10 마지막 문장(`erratum2.md:283`)대로 판정 불가 20건을 실패와 함께 공개합니다.

[기록][C] 77의 단위는 "관문·항목 항목 수"입니다. 짝별 실패 수가 아닙니다.
- 근거: J1 37건(R12 35 = 32짝, 그 가운데 3짝에서 관문 2개; R15 2)과 J2 31, J4 4, J5 4, J3 1입니다. 고유 (행, 위상, 항목)은 74, 2-9.3 항목 단위로는 72입니다.
- R12 관문 분포: `Fmin_after_event` 32(R12 4 + G4 28), `end_att` 2(G4), `no_lift` 1(G4).

[기록][C] R12 J1·J2는 짝 단위로 진짜 악화입니다(V0 통과 → VBJ 실패).
- R12 본 행 4위상: J1 4/4, J2 4/4.
- G4 폭 격자 28: J1 28/28, J2 27/28, J4 2, J5 2.
- J2 짝 31개 모두 V0 ≥ 9,414.589 N이고 VBJ < F_min인 것을 독립 재계산으로 확인했습니다(사건 행 E-3 = `min_F_after_W_kN` 최솟값, `v5_criteria.md:74`).
- 그 밖: R15 J4·J5 각 2건(V0 통과 → VBJ 끝 상태 probe, t_back 없음), S5 J3 1건(V0 100 s 안 → VBJ 넘음). V0 쪽 실패는 없습니다.
- v5 기준 11절 H-2 외에 H-3("VB의 R12 또는 G4 폭 격자에서 V0 통과 수 감소", `v5_criteria.md:216`)에도 걸립니다. 도구는 H-3을 따로 세지 않습니다. 판정서의 멈춤 근거에 H-2·H-3·H-6을 함께 적기를 권합니다.

[기록][R] `baseline_failures.J_vs_V0` 47건의 구성과 77과 겹치는 부분
- 47 = R1~R11 J3 `record` 30(V0 `case_floor_deg` 없음, 판정 아닌 FLAG; VBJ `pass`) + R16 J1 4 + R15 J1 5(관문 단위, 2위상) + S8 J4 4 + S8 J6 4입니다.
- 77과 겹치는 것은 R15 J1 두 짝뿐입니다(첫 발견). 나머지 45건은 77에 없습니다.
- 30건은 기준선 "실패"가 아니라 기록 상태인데 같은 목록에 섞여 있습니다. 이름만 고치면 되는 문제입니다.
- 항목 단위로 다시 센 기준선 실패는 16건입니다(R16 J1 4, S8 J4 4, S8 J6 4, R15 J1 2, R15 J2 2). R15 J2는 나빠짐 규칙이 맡습니다.

[기록][R] L-b를 VBJ 짝 기준(상대)으로 셉니다. 원문 "J3·J5는 7절 한계 안"을 그대로(절대) 읽으면 10건입니다.
- 근거
  - `v5_criteria.md:170`, 정오 2 `:234`. 도구 `jp3_j9main_judge.py:323-324`는 LS-vs-VB 표의 J3·J5 `fail`(VB 통과, LS 실패)만 셉니다.
  - 옛 `judge_stage1_r5.py:218-225`는 LS 자체의 절대 한계(`Lb_limit_violations`)를 셌습니다.
  - 정오 2 2-10.1 2(`:296`) "LSJ의 기준선 실패 기록은 VBJ도 그 항목을 실패한 짝"이 상대 읽기의 근거가 될 수 있습니다.
- 재집계: 상대 5건(도구와 일치), 절대 10건. 더해지는 것은 R15 J5(LS1 1, LS2 1, LS3 2)와 VBJ도 J5를 실패한 R12 짝(LS1·LS2 각 +1)입니다. L-b 위반이 있다는 사실(H-6 멈춤)은 두 읽기에서 같습니다.

[기록][R] J3을 상대로 구현했지만, 이번 자료에서는 원판 6.5·2-7.1의 "절대 한계"와 같은 결과입니다.
- 근거: `jp3_remedy_spec_v5.md:363`, `erratum2.md:140`은 "첫 READY가 7절 절대 한계를 넘거나 …". 도구(D-11, `judge_stage1_4368.py:273-281`)는 V0가 한계 안일 때만 실패로 셉니다.
- V0 토양 행(S1~S5·S7)에 J3 실패가 0이므로 두 읽기 모두 S5 1건입니다.

## 규칙↔도구 대조표
| 항목 | 규칙 원문 | 도구 | 판단 |
|---|---|---|---|
| 설정 대응 | 2-7.1 2 VB→VBJ, LS→LSJ (`erratum2.md:138`) | `SETTING_MAP` `jp3_j9main_judge.py:79` | 같음 |
| V0 기준 | `v5/main.jsonl` V0 100줄, sha 9ad74990 (2-9.2 `:215`) | `stored_v0_rows` :104-120, 명령의 `--v0-sha256` | 같음. 짝 100/100, 중복 0 |
| 짝 | 같은 행·같은 위상 (`v5_criteria.md:36`) | `_full_items` :254 (row, phase) | 같음. 행 이름 규칙(R2ra·G4 twin) 재구현과 일치 |
| J1 사건 행 | `event_output.pass`, V0 통과→설정 실패 (:55) | 관문 단위 D-07 | 기준선 경우에 어긋남(위 R15 2건) |
| J2 | F_min 9,414.589 N, 강체 사건은 E-3 (:56, :74) | D-08 :246-266 | 같음 |
| J3 | 절대 100 s 또는 V0 도달·설정 미도달 (6.5) | 상대 D-11 | 이번 자료에서는 같은 결과 |
| J4·J5·J6·J10 | :58-60, :64 | `J_fails` | 같음 |
| J7·J8·J9·J11 | :61-65 | D-09·J_fails·D-10 | 같음. 재집계 0건, J11 VB 100줄 pass |
| R15 나빠짐 | 2-9.3 J2만, 구분됨이면 실패 (:221-222) | `r15_worsening` :573-596 | 같음(2짝, VBJ가 나쁘지 않음 → 실패 0) |
| S8 F-5 | 6절, 멈춤 −6.92 / 14.21 kN (:122) | `s8_items` :532-566 | 상수 같음. None이면 판정 불가(규칙 미정) |
| L-a | VB 통과 행에서 J1·J2·J4·J6·J7 (:169) | :320-322 | 같음, 0 |
| L-b | J3·J5 7절 한계 안 (:170) | 상대 | 위 기록 |
| L-c | n_rev ≥ 2×·+6, V0 같은 행 최댓값 (:81-86) | :500-529 | 같음, 0 |
| L-e | 대체 다리 n_late = 0 (:173) | :328 | 같음, 0 |
| 상태 순서 | 2-10 실패 > 결함 > 판정 불가 > 통과 (`erratum2.md:271-278`) | `_status` :418-427 | 같음 |
| J-P3 | rev 6 줄, 판정 행 0 = 판정 불가 (2-7.1 3) | `j_p3_over_rows` | 같음. 판정 행 200, breach 합 0 재확인 |

## 재집계 표
| 항목 | 판정서(도구) 값 | 재집계 값 | 차이 | 판단 |
|---|---|---|---|---|
| VBJ J1~J11 항목 수(관문 단위) | 77 | 77 (J1 37 + 그 밖 40, 키별 일치) | 0 | 일치 |
| 고유 (행, 위상, 항목) | 74 | 74 | 0 | 일치 |
| 2-9.3 항목 단위 실패 | - | 72 (R15 J1 2 제외) | −2 | 규칙 읽기 차이, 결론 같음 |
| R12 J1 / J2 / J4 / J5 | 35 / 31 / 2 / 2 | 32짝 / 31 / 2 / 2 | J1은 관문 중복 3 | 진짜 악화(V0 통과) |
| R15 J1 / J4 / J5 | 2 / 2 / 2 | 0(항목 단위) 또는 2(관문 단위) / 2 / 2 | 위 | - |
| S5 J3 | 1 | 1 | 0 | 일치 |
| R15 나빠짐 실패 | 0 | 0 | 0 | 일치 |
| 위상 산포 의심 | 0 | 0 | 0 | 일치 |
| 기준선 실패(항목 단위) | 목록 47(기록 30 포함) | 16 | 구성 차이 | 기록 |
| L-a / L-b / L-c / L-e | 0 / 5 / 0 / 0 | 0 / 5(상대)·10(절대) / 0 / 0 | L-b 읽기 | 기록 |
| S8 F-5 판정 불가 | 20 | 20 (after_stop_chunks 0, V0 4줄도 같음) | 0 | 구조 원인 |
| J-P3 rev6 판정 행 / breach 합 | 200 / 0 | 200 / 0 | 0 | 일치 |
| VB J11 멈춤 | 0 | 0 | 0 | 일치 |

## 정체성·시간 순서(I·T)
- 정체성은 모두 정상입니다.
  - 줄 388 = VBJ 100 + LSJ1~4 각 72, 오류 0.
  - 모든 줄의 태그 `final_C4G2_P3W_LAS_K1`, `extend_start_tracked/hold/witness` 모두 참.
  - ③ 기록 200줄은 `rule_revision` 6·`spec_edition` fe6f5844이고, 기록이 None인 188줄은 `head_only_declared` 참입니다.
  - 실행 identity의 시작·끝 head는 606f8713, is_clean True. 판정 명령 3개는 74a4bbf4, is_clean True, 스크립트는 ed5-tool8입니다. 지금 그 worktree HEAD = 74a4bbf4이고, 판정 관련 파일 diff는 0입니다.
  - `v0_sample.json` same(48/48, 키 파일 7da16a4f는 FIXED_INPUTS_606f8713:28에 있음).
  - `l1_input_guard` clean(목록 sha 2ab6f76d·304023ff = FIXED_INPUTS_606f8713:251-252 l1ref_a1, dg3_a1 두 파일, 공유 0).
  - log_errors: 오류 줄 0입니다.
- 시간 순서
  - 규칙 커밋은 마지막 정오 8이 2026-11-23T13:37(cd2de978)입니다. j9main 시작은 16:53:32입니다. 결과는 e029dc8c(18:29)에 커밋됐고 작업 트리와 같습니다.
- 멈춤·재시도
  - `j9main.stop`(reason "j9main_judge exit 1")이 있고 `.done`과 a2는 없습니다. 2-7.1 멈춤 조건 "v5 기준 1단계 불합격"(`erratum2.md:148`)에 맞게 멈췄습니다.
  - 실행 명령은 모두 종료 0이고 중단·자원 문제도 없으므로, 4a-5 5.3 가(실행 환경 원인) 재시도 대상이 아닙니다.
  - 4a-5 5.1(`addendum_4a5.md:93`) "종료 1 … 멈춘다. 다시 돌려 바꾸지 않는다"와 5.4(`:131`)를 적용하면 재실행하지 않습니다.

## 확인 필요
1. R15처럼 V0가 이미 J1(최소 힘 관문)을 실패한 짝에서 VBJ에 새 관문(`end_att`)이 더해지면, 2-9.3 기준선(기록)인가 실패인가. 원문 `:220`은 항목 단위라 기준선이고, `:223`의 근거는 최소 힘만 말합니다. control-expert가 판단합니다.
2. L-b를 상대(VBJ 짝)로 읽을지 절대(LS 자체 7절 한계)로 읽을지. 판정서에는 두 값을 모두 적기를 권합니다.
3. 축소 하네스 S8의 F-5 조항·6절 멈춤 값(정지 뒤 표본 없음)을 "해당 없음"으로 둘지 "판정 불가"로 둘지.
4. 12절 "불합격" 문구는 11절대로 사용자 결정 뒤에 씁니다. 지금 확정된 것은 "1단계 합격 아님(status failed, 종료 1), 멈춤 근거 11절 H-2·H-3·H-6"입니다. 원판 8절 5와 2-7.1에 따라 원인 분석과 후보 안까지만 진행합니다.

## 위임 필요
- python-expert(다음 판정 도구, 지금 재판정용 아님)
  - `jp3_j9main_judge.py:618-751`: J1 기준선 판정을 항목 단위로 하고, J_vs_V0 집계에서 V0가 그 항목을 실패한 짝을 빼거나 따로 셉니다. `:729` `counted`를 계산값으로 바꿉니다.
  - 목록에서 `record`·`flag` 상태를 실패와 나눕니다.
  - 시험을 더합니다: V0 관문 {A} 대 설정 {A, B} → 기준선, 종료 0.
  - 확인 필요 1의 답에 따라 진행합니다.
- control-expert: 확인 필요 1~3의 개정 문장.
- `tools/verif` 후보(python-expert): "판정 전·후 짝 재집계"(쌍 키, 항목 단위·관문 단위 두 셈, 기준 실패 분리, 상대·절대 한계 두 셈)를 즉석 스크립트로 또 했습니다. 입력: 판정 줄 jsonl, 기준 jsonl, 판정 json. 출력: 항목별 집합 차와 종료 0/1/2.

## 메인 세션 권고
- 실행이 필요한 확인은 없습니다.
- 판정서 초안에 다음을 넣습니다.
  - 2-10 "실패와 함께 기록된 판정 불가 사유 전부"(S8 F-5 20)
  - 77의 단위와 2-9.3 항목 단위 75/72
  - L-b 두 값
  - H-3 해당

## 검사하지 못한 것
- S8 SA-4 일곱 항목을 독립 재계산하지 않았습니다. 도구 결과는 실패 0·판정 불가 0이며, 결론에는 영향이 없습니다.
- L-d(기록) 26×4행을 다시 세지 않았습니다.
- J7 대체 사유의 시각 비교는 제어 주기 반올림(0.1 s)으로 재구현해 0건이 일치했습니다. 사건 목록 200개 절단 여부는 따로 세지 않았습니다.
- P-4 lock window 메타는 `hydraulic_options`에 해당 키가 없어 대조하지 않았습니다(이번 질문 범위 밖).
- 436.8 저장 VB S8 줄의 `after_stop_chunks`는 보지 않았습니다(V0로 갈음).
- 정오 6 6-6 건식 확인이 S8 F-5 판정 불가 20을 기대값으로 가졌는지 확인하지 않았습니다. `[추정]` 합성 입력이 `main.jsonl` 사본이면 같은 None이 나왔을 것입니다.

## 실행한 검증
- 인터프리터: python-dev `python.exe -I -B -X utf8`(PowerShell, `MKL_THREADING_LAYER=TBB`). 판정 모듈은 import하지 않았습니다.
- 명령
  - depcheck: STAMP
  - source_guard snapshot/verify(입력 29)
  - `seal_check.py --repo … "jp3_remedy_spec_v5*.md" "v5_criteria*.md"`: 종료 1, draft 2개 seal_missing뿐
  - `log_errors.py <j9main_a1\logs>`: 종료 0
  - 즉석 스크립트 peek·dump·recount(독립 J1~J11, L-a~L-e, R15, S8, 위상 산포)·ident(H-2)·jp3(breach 합)
  - git log·show·diff(규칙 첫 커밋, e029dc8c 범위, ed5-tool8 HEAD·diff)
- 만든 뒤 지운 파일: scratchpad `auditor-j9post\`의 스크립트 6개, guard.json, seal.md. 폴더째 지웠고 남은 것은 없습니다. 대상 폴더에 `__pycache__`도 남기지 않았습니다.
- 메모리: `audit_pitfalls.md`에 판정 뒤 재집계 함정 1항목을 더하고 MEMORY.md 색인 한 줄을 고쳤습니다.
- 최종 판정 전 확인: source_guard verify로 입력 29개가 바뀌지 않은 것을 확인했습니다. 인용한 코드 줄은 HEAD 74a4bbf4의 diff 0을 확인한 worktree에서 읽었습니다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v5.md fe6f5844…, jp3_remedy_spec_v5.md.sha256 0dd1676c…, jp3_remedy_spec_v5_erratum1.md 4721352e…, jp3_remedy_spec_v5_erratum1.md.sha256 d508c2df…, jp3_remedy_spec_v5_erratum2.md 639c54e9…, jp3_remedy_spec_v5_erratum2.md.sha256 054bfb8d…, jp3_remedy_spec_v5_erratum3.md 7bab9217…, jp3_remedy_spec_v5_erratum3.md.sha256 29f02a7f…, jp3_remedy_spec_v5_erratum4.md 4bc4ecdd…, jp3_remedy_spec_v5_erratum4.md.sha256 0422bf7d…, jp3_remedy_spec_v5_erratum5.md 8487bd55…, jp3_remedy_spec_v5_erratum5.md.sha256 aef4a8cf…, jp3_remedy_spec_v5_erratum6.md 9a92bd34…, jp3_remedy_spec_v5_erratum6.md.sha256 eadc3068…, jp3_remedy_spec_v5_erratum7.md 38fdc574…, jp3_remedy_spec_v5_erratum7.md.sha256 5192e12a…, jp3_remedy_spec_v5_erratum8.md 8c420e85…, jp3_remedy_spec_v5_erratum8.md.sha256 a95fc2fe…, j9main_judge.json fbdf6c41…, v0_sample.json b2e63a51…, l1_input_guard.json a9ac752f…, j9_main.jsonl 883a2538…, j9_main.identity.json 3cbde533…, v0_sample.jsonl eec86755…, step_record.json 7b7525ae…, j9main.stop 7b7525ae…, j9main_a1.md 8a11f9c3…, j9main_a1_v0_sample.md 2ed86d89…, main.jsonl 9ad74990…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음

관련 경로
- C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\j9_runs\606f8713\j9main_a1\judge\j9main_judge.json
- C:\workspace\outrigger_control\.claude\worktrees\ed5-tool8\04_scripts\04_hydraulic\coupled\jp3_j9main_judge.py
- C:\workspace\outrigger_control\.claude\worktrees\ed5-tool8\04_scripts\04_hydraulic\coupled\judge_stage1_4368.py
- C:\workspace\outrigger_control\.claude\worktrees\ed5-tool8\04_scripts\04_hydraulic\coupled\verdict_metrics.py
- C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\jp3_remedy_spec_v5_erratum2.md
- C:\workspace\outrigger_control\06_analysis\03_hydraulic\coupled\v5\v5_criteria.md
