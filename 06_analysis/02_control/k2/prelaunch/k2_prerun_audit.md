<!-- verif-protocol-auditor 리포트 원문(2026-11-10, 실행 전). 대상: K-2 _TCL V-2~V-7, RUN_HEAD 6a44ff8, 실행 전 기록 47e9b07. 메인 세션이 편집 없이 저장. -->

**차단 2건, 실행 전 수정 9건, 확인 필요 4건** (기록 6건)

## 감사 요약
- 대상: K-2 `_TCL` 검증 묶음 V-2~V-7 본 실행. 시점은 실행 전입니다. 결과는 0건이고 `k2-run\06_analysis\02_control\k2\runs`, `07_results\S6|S8|S9`의 k2 폴더가 모두 없습니다.
- 기준 문서
  - 원판 `k2_touch_creep_rules.md` a3658197
  - rev1 5ba081c6
  - dyn 명세 502b0bb7
  - 실행 전 기록: 브랜치 `k2-prelaunch-record` 47e9b07, worktree `C:\workspace\outrigger_control\.claude\worktrees\agent-af7124b8517fd4c3a`
- 판정: 차단 2 / 실행 전 수정 9 / 기록 6.
  - 실행 자체(명령·마스크·입력·봉인)는 규칙대로 준비돼 있습니다.
  - 다만 차단 2건은 고정한 경로 2(`k2_recount.py`)를 고쳐야 풀립니다. 규칙 8은 경로 2를 "어느 결과가 나오기 전에" 고정하라고 합니다. 그래서 **본 실행 전에** 경로 2 수정과 rev2 봉인이 필요하고, 지금 상태로는 G-S 자동 시작 조건(차단 0)을 채우지 못합니다.

## 발견 사항 (심각도순)

**[차단][R·E] 1. V-5 판정이 criteria.md의 절대 기준을 "끔 팔 대비 통과→실패"로 바꿔 버림. 두 경로가 모두 같음**
- 근거(규칙)
  - 규칙 3.4는 기준 파일의 "합격 기준을 글자 그대로" 쓰라고 합니다(`k2_touch_creep_rules.md:162`). 바꾸는 것은 비교 쌍뿐입니다.
  - criteria.md에는 절대 항목이 있습니다.
    - 격자 "FAULT 0"(`criteria.md:24`)
    - 토양 "G1 20·J2 20 실패 0, FAULT·재접촉 실패 0"(`:25`)
    - D8 "`fails` 빈 목록, FAULT 0, ≥ 14.41 kN, ≤ 0.2°, READY ≤ 100 s"(`:26`)
    - 잡음 "L1 거짓 LOC 0, unmatched 0, errors 0, SGS 불일치 0"(`:38`)
    - 공통 "오류 행 0, `main_tree_modules` 0, `c2_sha256`"(`:9`)
  - 옛 `acc_judge`도 이 항목들을 절대값으로 봤습니다: grid `not fault_runs`(`acc_judge.py:212`), soil `not soft and not fault_runs`(`:219`), d8 `bad` 목록 전부(`:133-143`), noise `unmatched`·`errors`(`:128`).
- 근거(도구)
  - manifest `v5`는 grid·d8·soil·regression·ps7를 모두 `kind: pass_to_fail`, noise를 `noise_cp`(CP만)로 둡니다(`prelaunch/k2_manifest.json`).
  - 경로 1 `v5_bundle`(`k2_judge.py:829-883`)과 경로 2 `v5_bundle`(`k2_recount.py:602-660`) 모두 이 세 종류만 지원하고, 절대 판정 종류가 없습니다.
  - 평탄화기(`k2_v5_flatten.py:153-163`)는 D8 조건을 행 `pass`에 넣지만, 판정은 pass→fail 비교라서 두 팔이 함께 실패한 행은 사라집니다.
  - grid의 `fault_periods`, noise L1 행·unmatched·errors는 평탄 행에 아예 없습니다.
- 실패 시나리오: K-2 팔 D8 행이 14 kN이고 같은 키 끔 팔도 14 kN이면 G-D는 통과로 나옵니다. criteria.md 기준으로는 실패입니다. 두 경로가 같은 평탄 파일을 읽으므로 G-F 일치 검사로도 잡히지 않습니다. 규칙 8은 "원 결과 파일을 직접 읽는다"고 하는데, 두 경로가 같은 중간 파일에 의존해 독립성도 잃습니다.
- 권장 조치(실행 전)
  - control-expert: rev2에 "V-5 절대 항목은 K-2 팔에 그대로 적용, 통과→실패는 끔 팔 대비"를 적고 봉인합니다.
  - python-expert: 경로 1·2에 절대 종류(예: `kind: absolute`, 또는 묶음별 항목 목록)를 넣고 평탄화기에 `fault`·`error`·noise L1/unmatched/errors 필드를 더합니다.
  - control-expert: 경로 2는 V-5 원 출력(`d8_both.json`, `grid_*.json`, `soil_A.json`, `r79_L1L2_judgement.json`)을 직접 읽도록 고칩니다.
  - 그 뒤 새 blob을 실행 전 기록에 고정합니다.

**[차단][R·E] 2. 그림자 지표 SH-1~SH-6의 V-6(Chrono) 계산이 두 경로 모두에서 빠지거나 부족함**
- 근거(규칙)
  - 5.2: "대상은 V-2·V-3·V-4(하네스)와 V-6(Chrono K-2 행 vs 끔 행)"(`k2_touch_creep_rules.md:277`).
  - 3.5: "L1 K-2 행도 같은 두 항목(공중 거짓 래치·CAP)을 기록하고 FLAG(SH-5)로 센다"(`:195`).
- 근거(도구)
  - 경로 1 `cmd_judge_v6`(`k2_judge.py:1033-1065`)는 `sh` 키를 만들지 않습니다. `cmd_report`는 `doc.get("sh")`에서만 FLAG를 모읍니다(`:1104`). 그래서 V-6의 FLAG는 0으로 나옵니다.
  - 경로 2 `recount_v6`(`k2_recount.py:868-875`)는 SH-5(cap)·SH-1·SH-6만 셉니다. SH-2(중앙값), SH-3(READY +3 s), SH-4(묶음 최솟값 차)와 L1 공중 거짓 래치의 SH-5는 셈하지 않습니다.
- 실패 시나리오: V-6 K-2 행의 READY가 끔 대비 +4 s여도 등급이 "통과"로 나옵니다. 규칙대로면 "조건부 통과"입니다. SH-3 누락은 두 경로가 같아서 G-F로 잡히지 않습니다. SH-1·5·6은 경로 1만 빠뜨려 G-F에서 판정 불가로 끝납니다.
- 권장 조치: 차단 1과 같은 경로 2 수정(control-expert)·경로 1 수정(python-expert)·rev2 기록에 묶습니다.

**[실행 전 수정][E] 3. E-5·I-9 일부를 두 경로 모두 확인하지 않음**
- V-3: 규칙은 "요청 옵션 값이 3.3 팔 정의와 같고"를 요구합니다(`:433`). 경로 1은 `plant_aug.options`가 비어 있지 않은지만 보고(`k2_judge.py:738-746`), 경로 2는 `aug_arm`·`is_kplant`만 봅니다(`k2_recount.py:807-818`). 값 0.233093, 4 kN, ζ 0.10, ε 0.1 v_max는 아무도 대조하지 않습니다.
- V-2·V-4 "옵션 모두 끔", V-6 "L1 이동 중 감쇠 켬 / L2b 끔", V-6 I-9의 다리별 열림 비율은 두 경로 모두 확인하지 않습니다(`CHRONO_ROW_KEYS` `k2_judge.py:913-932`, `DEFAULT_FIELDS["chrono_row"]` `k2_recount.py:106-117`).
- 결과: 판정 불가여야 할 행이 통과로 셀 수 있습니다. 차단 1·2의 경로 2 수정에 함께 넣으십시오.

**[실행 전 수정][E·I] 4. V-5 K-2 팔이 실제로 켜졌는지 행 단위 증거를 확인하지 않음**
- `ACC_K2`는 `with_10hz_d1`의 키워드 기본값만 바꿉니다(`acc_common.py:113-124`). provenance에는 부모 프로세스 설정 하나만 남습니다(`:140-157`).
- 평탄 행 가운데 태그·`touch_creep_latch`를 옮기는 것은 ps7·g8뿐입니다(`k2_v5_flatten.py:166-181`). 두 경로 모두 V-5 행의 E-4·E-6을 보지 않습니다.
- 결과: 어떤 구동기가 K-2를 적용받지 못하면 V-5는 "끔 대 끔"이 되어 자명하게 통과합니다.
- 권장 조치(판정 전): 팔별 provenance의 `touch_creep_latch`·`controller_tag`·`c2_sha256`·`main_tree_modules`를 전수 확인하고, 사건 기록이 있는 출력에서는 `INFO_TOUCH_CREEP_LATCH`가 있는지 확인합니다. 경로 반영은 python-expert와 control-expert입니다.

**[실행 전 수정][R] 5. 실행 전 기록(I-3, 3.4, 9.3)에 빠진 항목**
- V-5의 grid·d8·soil·noise·ps7·g8 키 목록 sha가 없습니다. 3.4는 "행 목록과 수는 I-3에 키 목록 sha256로 고정"이라고 하는데, 지금은 regression만 고정돼 있습니다.
- V-2·V-4 "행 목록과 그 sha256"이 없습니다.
- 9.3 V-6 시작 상태 목록과 sha가 없습니다. 감사 중 잰 값을 적습니다.
  - `S6_crawler_top_fdown3.5.npz` 8f93d107…, `.meta.json` 9bb73974…
  - `S6_crawler_top_k2pp025.npz` be765f36…, `.meta.json` c49fbfcf…
  - L2b 시작 상태는 확인하지 못했습니다.
- G-S의 "구현 시험 9.2, I-4 축소·I-5·I-8 통과" 근거는 커밋 메시지(`ba3adcc`, `d68be62`, `1c8d95f`)에만 있습니다. 출력이나 해시 기록이 없습니다. `1c8d95f..6a44ff8` 사이에 하네스 경로(03_src, 04_scripts/03_control 판정 대상)는 `run_ps7.py`만 바뀌었으므로 근거가 유효할 가능성은 큽니다. 그래도 기록은 남겨야 합니다.

**[실행 전 수정][T·E] 6. 러너 의존 순서**
- E_V6_off·E_V6_tcl은 `$WaitArguments = $null`입니다(`k2run_E_V6_off.ps1:22`, tcl도 같음). README의 "snaps-k2 확인만, 아니면 멈추고 묻는다"를 러너가 강제하지 않습니다. 지금 스냅숏은 있으니(위 sha) 실제 위험은 낮습니다.
- E_V7은 `--proc-absent k2run_E_V6_*.ps1 --consecutive 2 --interval 30`입니다(`k2run_E_V7.ps1:22`). V-6 러너보다 먼저 띄우면 약 60 s 뒤 바로 시작합니다. 결과 비트에는 영향이 없을 것으로 봅니다(`--threads` 고정). 다만 E코어 12개에 L2b 6+6과 SCM 4×4 스레드가 겹칩니다.
- 순서는 E_pre 끝 확인 → E_V6 두 러너 → 두 러너의 프로세스 확인 → E_V7입니다.

**[실행 전 수정][S] 7. 경로 1이 rev1 봉인을 대조하지 않음**
- `seal_problems()`는 원판 `.sha256`과 명세만 봅니다(`k2_judge.py:131-144`). seal_check 결과도 `code_pin_missing`(rev1)입니다.
- 경로 2는 rev1까지 봅니다(`k2_recount.py:959-973`). 다만 `--rules-dir`를 줄 때만 보므로(`:706`) 판정 명령에 반드시 넣어야 합니다.
- 담당: python-expert.

**[실행 전 수정][E] 8. 경로 1의 SH 계산이 결측을 조용히 건너뜀**
- `sh1 or []`, `_median`이 None을 거름, t_ready가 없으면 SH-3를 건너뜀(`k2_judge.py:492-533`). 결측 행은 FLAG 판단에서 빠지고 따로 세지도 않습니다.
- E-9는 "NaN·None이면 그 항목 fail"입니다. 결측 수를 출력하게 하십시오(python-expert).

**[실행 전 수정][I] 9. 판정 후 정체성 전수 확인 목록을 미리 선언하지 않음**
- sidecar(`run_with_identity.py`)는 argv·cwd·env 일부·마스크·rc·시작/끝 HEAD·clean을 남깁니다(`:133-154`). 인터프리터 버전과 `PYTHONDONTWRITEBYTECODE`는 남기지 않습니다. 버전은 acc_d8 `identity_start`나 provenance에서 확인해야 합니다.
- V-7은 래퍼 없이 돌아 HEAD·clean이 run_S9 result.json에 의존합니다 `[추정]`.
- 아래 "판단" 2번의 확인 목록을 README나 rev2에 미리 적어 두십시오.

**[기록]**
- (a) 실행 전 기록 안에서 숫자가 서로 다릅니다. `k2_prelaunch_v*.json` `v5_regression_rows`와 `k2_expect.json` note는 "other 25 of the 118", README 3.1은 "판정하지 않는 출력 49"입니다.
- (b) `criteria.md`는 `text: unspecified`(autocrlf true)이고 해시를 고정하지 않았습니다. "글자 그대로"의 기준 파일이므로 실행 전 기록에 sha를 적으십시오.
- (c) I-4 저장 행은 main checkout의 git 제외 파일입니다(`ra_off.json` 100985bf…cb10, `ra_on.json` e3c8c95f…247a, 실측 일치). 판정 때 두 경로 모두 이 sha를 다시 확인하지 않습니다. 판정 후 감사에서 대조하겠습니다.
- (d) I-1 문구는 "하네스는 H_impl, Chrono는 M"인데, 전부 M = 6a44ff8에서 돕니다. 6f2f7cb를 포함하고(ancestor 확인), H_impl 이후 하네스 코드 변경은 위 5번과 같으므로 판정 영향은 없을 것으로 봅니다. 판정서에 "H_impl = M"을 적으십시오.
- (e) V-7 Job 메모리 상한 6144 MB 안에 SCM 4행이 동시에 돕니다(`k2run_E_V7.ps1`) `[추정]`. 넘으면 Job 전체가 kill됩니다(기록 전용 묶음).
- (f) 도구 공백: `gate_scan.py`는 `--no-git`을 받지 않습니다(종료 2 `unrecognized arguments`). 다른 verif 도구와 공통 인자 계약이 다릅니다.

## 규칙↔도구 대조표 (요지)

| 항목 | 규칙 | 도구·기록 | 판단 |
|---|---|---|---|
| V-2 건수·태그 | 1,102×2, `_LAS`/`_LAS_K1`(+`_TCL`) (`:92,101`) | expect 910+192, 태그 히스토그램. 경로 1 `expected_tag` 정확 비교 | 일치 |
| V-3 키 | 273, sha d4a030d7, main 28·robust 197·kt 48, 고유 명령 165, 밖 1행 `beta…roll-…` (`:148-151`) | 저장 ra_off로 독립 재계산: 273 / d4a030d7… / 28·197·48 / 165 / 같은 1행, `k2_v3_keys.txt`와 같음 | 일치 |
| V-3 판정 팔 | 6개, AUG_crc2 기록 (`:134-142`) | 두 경로 `V3_JUDGED` 같음 | 일치 |
| V-4 점 | rev1 2 | 경로 2 points-check: diamond 0, d45 1.11e-5°, 그 밖 0 | 일치 |
| V-4 건수 | 596, 상단 | `--levels top --stages main,robust,kt`, expect 596 | 일치(실행 전 수 확인은 못 함) |
| V-5 기준 | 글자 그대로 (`:162-172`) | pass→fail·CP만 | **불일치(차단 1)** |
| V-5 회귀 | 118 | 판정 93 + 비판정 49 = 142 | 확인 필요 1 |
| V-6 | 8행, K1 끔, 태그, `floor_true_deg` | 행 정의 `k2_chrono_rows.py:111-115`, 태그 `:66`, 러너 `--k1-order-gate off --expect-controller` | 일치. E-5·I-9 확인 없음(3) |
| SH-1~6 | V-2·3·4·6 (`:277`) | V-6 누락·부분 | **불일치(차단 2)** |
| SH-4 | 묶음 최솟값 차 < −3 kN | 두 경로 모두 묶음 최솟값 | 일치 |
| 등급 순서 | 판정 불가 > 미달 > 범위 한정 > 조건부 > 통과 (`:408`) | `_grade`·`grade` 같음 | 일치 |
| G-A~G-E | (`:337-341`) | 두 경로 모두 K-2 팔 fail 수로 결정 | 일치 |
| 태그 접미사 | `_LAS`→`_K1`→`_TCL`, ③는 `is_extend_start_tag` | `switch_base_tag`가 `_TCL`을 먼저 벗김(`v5_options.py:482-497`). 04_scripts/03_control에서 단일 문자열 태그 비교는 0건(Grep) | 일치 |
| 이중 적용 | – | V-2~V-4는 `--k2`, env에 `ACC_K2` 없음(acc_d8은 있으면 멈춤, `acc_d8.py:317`). V-5는 `ACC_K2` 한 번(`_acc_k2_patched` 가드), `ACC_COMBO=preset`은 조합 패치 없음 | 이중 적용 없음 |
| SCM 기록 | I-6 | V-7 env `OMP_WAIT_POLICY=PASSIVE`, `--threads`는 FINAL-REP argv(`k2_chrono_rows.py:726-744` 확인 함수), hull fast, batch `hull_hook_effective` | 기록 경로 있음. 사후 확인 대상 |
| `-text` | – | 원판·rev1·`.sha256`·명세·점 파일·manifest·keys·`runs/`(예정)·`d8x/ra` 모두 `-text`, i/lf w/lf. `07_results` 출력은 unspecified(무시 경로, 해시 인용 전) | 이상 없음 |

## 확인 필요
1. **V-5 회귀 118 ↔ 93(+49) — 봉인 규칙과 양립하는가**
   - 규칙 E-1은 "V-5 3.4 키 목록 수"이고, 3.4 본문도 "행 목록과 수는 I-3 실행 전 기록에 키 목록 sha256로 고정"이라고 위임합니다(`:174,429`). 그래서 판정 키 93(2900db88)을 I-3에서 고정하는 것은 E-1 문구와 형식상 맞습니다.
   - 그러나 3.4 표의 "118"은 봉인 문구이고, 142·93 어느 쪽으로도 다시 만들 수 없습니다. "118은 옛 재실행 목록 행 수"라는 설명은 `[추정]`입니다(목록 파일 없음).
   - 실행 전 기록 안의 숫자도 25와 49로 어긋납니다(기록 a).
   - 권고: 어차피 차단 1·2로 rev2가 필요하니, rev2에 "회귀 = 판정 93(키 sha 2900db88, acc_judge 정의) + 기록 49(d4f58334), 118은 다시 만들 수 없는 옛 목록 수"를 명시하십시오. "정정만, rev2 없음"은 결과 뒤 해석 다툼의 여지가 남습니다.
   - 같은 rev2에 "r79 L1 기준 행은 판정 행이 아니다"도 적으면 "L1·L2 행 통과→실패" 문구와 맞습니다.
2. **V-6 E코어**: 규칙 7과 Q-8은 "이상적 센서 1단계 뒤 **P코어**"입니다(`:344`, `:460`). V-7의 E는 사용자 결정이라고 들었지만 V-6의 E는 근거를 찾지 못했습니다. 사용자 결정으로 기록하거나 P로 바꾸십시오. 두 팔이 같은 풀이고 `--threads`와 무관하면 비트 영향은 없을 것으로 봅니다 `[추정]`.
3. "이상적 센서 1단계가 끝난 뒤" 조건(규칙 7)이 충족됐는지는 확인하지 않았습니다.
4. V-6 L2b(`K24_*`) 시작 상태 정의(9.3 "목록을 선언")를 cad-expert가 확인해야 합니다.

## 요청하신 판단
1. **규칙↔도구↔manifest·expect**: 위 대조표와 같습니다.
   - I-4: 경로 1·2 모두 (id, k1)로 행마다 대조하고, 수가 같은지도 봅니다(`k2_judge.py:543-560`, `k2_recount.py:821-829`). 저장 파일 sha는 판정 때 다시 확인하지 않습니다(기록 c).
   - I-5·I-8: G-S 근거 기록이 없습니다(5).
   - I-10: 두 경로에서 확인합니다.
   - rev1 점 파일·D̂: 두 경로 모두 반영돼 있습니다. 경로 1은 rev1 봉인 대조만 없습니다(7).
2. **정체성 관문 — 둘 것을 권합니다.** 규칙 G-F에 이미 "판정 후 감사 차단 0"이 있으므로 별도 개정 없이 그 감사 범위로 두면 됩니다. 확인 목록을 실행 전에 선언하십시오.
   - sidecar 62개: rc 0, `git_start`/`git_end` head = 6a44ff8 / clean, env, affinity·child mask
   - V-5 provenance: `c2_sha256`, combo, k2, `touch_creep_latch`, tag
   - V-6 `batch_meta` 4개(각각 identity_start/end, `all_rc_zero`)
   - V-7 batch.json과 행 result.json: argv, rc, threads, OMP, `hull_hook_effective`, git
   - 이를 `record_check identity --meta`로 전수 확인합니다.
3. **V-5 건수**: 확인 필요 1.
4. **입력**
   - `07_results\states_L1R` 사본: 72개 파일 모두 main과 바이트가 같습니다. 집계 sha b24066a9…(파일명+sha 정렬)입니다.
   - V-5 하네스의 git 제외 입력: Grep으로 본 범위에서는 런타임에 `07_results`나 main 경로를 읽는 곳이 없었습니다. 남는 것은 `s6_control.PS7_TOUCH_REF_DEFAULT`(Chrono PS-7 판정용, run_ps7 경로가 아님), `r8d1_lin.py`의 main sys.path(acc_common `MainTreeGuard`가 제거), `s9_runs.sensor_cases`(코드 생성)입니다.
   - 전수 추적은 하지 못했습니다(검사하지 못한 것).
5. **러너**
   - 6개 러너의 argv·cwd·env·순서가 `k2_commands_filled.json`(402a1ef3)과 같습니다(스크립트로 전수 대조). scratch 원본과 `prelaunch/sched` 사본의 sha도 같습니다.
   - 마스크: P 0xFFFF / Normal, E 0x0FFF0000 / BelowNormal. worker 8. P_main 56단계는 끔·K-2 교대.
   - P_post는 36개 `.done`을 기다립니다(timeout 14 h). `.done`은 exit 0일 때만 써집니다.
   - `--job-kill-on-close`는 모든 러너에서 켜져 있습니다.
   - 예약 TTL: P 120분, E_V6 120분, E_V7 480분, P_post 60분.
   - 의존 순서는 6번 발견을 따르십시오.
6. **실행 중 master 커밋**
   - k2-run은 6a44ff8 detached이고 master는 이미 b82d328로 진행했습니다. main checkout에 커밋해도 k2-run 파일과 실행에는 영향이 없습니다.
   - 영향이 있는 것은 다음 넷입니다: worktree 제거·정리(`git worktree list`에 lock이 없음), dynamics-dev·Chrono-dev env 변경, `~/.claude/tools/cpu-scheduler` 변경, main의 `d8x/ra/*.json` 변경(판정 때 I-4에 영향).
   - 실행 전 기록 브랜치 병합: 47e9b07은 결과 전 시각(18:52)을 담은 증거이니 rebase나 amend를 하지 마십시오. rev2와 경로 2 수정 뒤 실행 전 기록을 다시 만들어(새 blob) 커밋하고, integrity-checker를 거쳐 **실행 시작 전에** master에 병합하는 것을 권합니다. `{BATCH_V7}` 채움은 시작 뒤 별도 커밋으로 합니다.

## 위임 필요
- **python-expert**
  - `k2_judge.py`: `cmd_judge_v6`에 SH-1~SH-6과 L1 거짓 래치 SH-5 추가, `seal_problems`에 rev1 `.sha256` 대조 추가, SH 결측 수 출력, E-5 옵션 값 대조, V-6 E-5·I-9 대조.
  - V-5 `kind: absolute` 지원.
  - `k2_v5_flatten.py`: `fault`·`error`·noise L1/unmatched/errors 필드 추가.
- **control-expert**
  - rev2: V-5 절대 항목, 회귀 93/49/118 정리, V-6 SH 계산 명시, V-6 풀.
  - `k2_recount.py`: V-5 원 출력 직접 읽기, 절대 종류, V-6 SH-2·3·4와 L1 거짓 래치, E-5 값·V-6 E-5·I-9 확인. 새 blob을 실행 전 기록에 고정.
- **cad-expert**: V-6 L2b 시작 상태 선언(9.3).
- **tools/verif 후보 (python-expert)**
  - `gate_scan.py`가 `--no-git`을 받도록 함(효과 없음, 공통 계약).
  - 새 검사 "러너 단계 ↔ 명령 JSON 대조": 입력은 steps_*.json, runner ps1, filled.json. 출력은 argv·cwd·env·순서 차이. 종료 0/1/2.

## 메인 세션 권고
- dynamics-dev, E코어에서 `05_tests/unit/test_k2_hashes.py`(T-K2-1, T-K2-2, I-8 G0·R-c)를 6a44ff8 k2-run 기준으로 다시 돌리고, 출력과 pass/skip 수를 실행 전 기록에 남기십시오. R-c는 main 파일이 없으면 skip되니 skip 0을 확인해야 합니다.
- `git worktree lock` k2-run(사용자 확인 뒤).
- 출발 순서: E_pre 끝 확인 → E_V6 두 러너 → 프로세스 확인 → E_V7.

## 검사하지 못한 것
- V-4·V-2 건수 건조 실행(acc_d8에 결과를 쓰지 않는 dry-run이 없음).
- V-5 구동기 전 모듈의 git 제외 파일 읽기 전수 추적.
- L2b 시작 상태.
- 이동 중 감쇠 끔 = 비트 불변(9.3).
- V-7 Job 메모리.
- T·C축 결과 비교(결과 0건).
- "이상적 센서 1단계 끝" 여부.

## 실행한 검증
- 인터프리터는 python-dev `-I -B`(필요할 때 `-X utf8`, `MKL_THREADING_LAYER=TBB`)입니다.
- verif 도구
  - `seal_check.py`(원판·rev1·`--code k2`): raw 일치 2/2, `-text`, LF, `code_pin_missing` 1
  - `gate_scan.py`(judge, recount, flatten, wrapper): `empty_pass_not` 1(`k2_recount.py:323`, points_check. 태그 집합이 고정돼 있어 오탐), 좋은 패턴 10
- `k2_recount.py points-check`: scratch 출력, ok.
- 즉석 스크립트 3개(입력 sha 대조·states 대조·러너 대조, V-3 키 독립 재계산, 명령 요약)는 scratchpad에 두고 지웠습니다.
- git 조회: rev-parse, hash-object, status, check-attr, ls-files --eol, merge-base, log, diff --stat, worktree list.
- 메모리 갱신: `C:\Users\jinbeom\.claude\agent-memory\verif-protocol-auditor\audit_pitfalls.md`(항목 1개), `MEMORY.md` 색인.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha k2_touch_creep_rules.md a3658197…, k2_touch_creep_rules.sha256 6a7d3b25…, k2_touch_creep_rules_rev1.md 5ba081c6…, k2_touch_creep_rules_rev1.sha256 fdf6d8ca…, k2_dyn_spec.md 502b0bb7…, k2_points_5p5_3p5.json a15cbe95…, k2_commands.json ce6e04a2…, k2_expect.json e19cef82…, k2_fields.json 0c5aafc4…, k2_manifest.json d54752c6…, k2_prelaunch_v2.json 291c00c5…, k2_prelaunch_v3.json eace8e3f…, k2_prelaunch_v4.json d0c6f366…, k2_prelaunch_v5.json 66397702…, k2_prelaunch_v6.json 95eb73d4…, k2_prelaunch_v7.json 83d57cdd…, k2_v3_keys.txt 506b93a4…, k2_v5_regression_keys.json f2970048…, make_prelaunch.py df26c830…, README.md 1ded5767…, regression_keys.py 31ee5cc9…, aff.json 68bb2fb1…, build_runners.py 7182fb37…, k2_commands_filled.json 402a1ef3…, k2_placement_20261110.json f349ce4e…, k2_sched_lanes.json 1b5fc744…, p_main_done_markers.txt ac277f80…, state.json 257a8ab2…, steps_E_pre.json b725bdfe…, steps_E_V6_off.json 1ec165c4…, steps_E_V6_tcl.json d04502cf…, steps_E_V7.json 0713920f…, steps_P_main.json 033496df…, steps_P_post.json 5dd80d49…, k2run_E_pre.ps1 5e8a85db…, k2run_E_V6_off.ps1 8c25c06e…, k2run_E_V6_tcl.ps1 cff4c587…, k2run_E_V7.ps1 e5c94ae7…, k2run_P_main.ps1 1c4c4c58…, k2run_P_post.ps1 434c109b…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
