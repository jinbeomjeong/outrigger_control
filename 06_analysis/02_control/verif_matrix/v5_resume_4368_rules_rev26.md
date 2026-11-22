# v5 재개 검증 436.8 규칙 — 개정 26 (H-3·H-4 판정 도구 보완과 재판정) (control-expert, 2026-11-22, 봉인 전 수정 7)

- 상태: **봉인 전**. 봉인하면 sha256과 시각을 같은 폴더 `v5_resume_4368_rules_rev26.sha256`에 적는다(첫 줄 이 파일, 다음 줄 부록 파일). 봉인 뒤에는 고치지 않는다.
- 수정 이력
  - 봉인 후보 초안
  - 수정 1: stats 검토 2
  - 수정 2: verif 봉인 전 감사, 사용자 결정 B-1 (가)
  - 수정 3: 재감사 N-1~N-3·W-a~W-e, 사용자 결정 N-1 (나)
  - 수정 4: 재재감사 `v5paper_imua_stats/audit_rev26_preseal_reaudit2_20261122.md` N-3b·W-f·W-g·W-h, 규칙 파일의 T26 포함
  - 수정 5: 네 번째 재감사 `v5paper_imua_stats/audit_rev26_preseal_reaudit3_20261122.md` B-4(`.gitattributes` 허용), W-i(worktree 깨끗함 기록), W-j(`--root .` 확정)
  - 수정 6: 다섯 번째 재감사 `v5paper_imua_stats/audit_rev26_preseal_reaudit4_20261122.md` B-5(사용자 결정 (가): 경로 2 입력 기준 인자 `--data-root`, 경로 1 실행본 입력 인자, 입력 기준 site 열거), W-l(줄바꿈 점검 대상), W-m(h11 문장), 기록 1(들여쓰기)
  - 수정 7(이 판): 여섯 번째 재감사 `v5paper_imua_stats/audit_rev26_preseal_reaudit5_20261123.md` B-6(NT 정규화를 2절 W 자료 위치로 넓힘, 부록 r5), W-n(줄바꿈이 비교 잎에 닿는 03_src 파일은 `v5_options.py`뿐), 기록 1(Chrono 매니페스트 기본값은 W)
- 봉인 전 확인: stats 검토 2·3, verif 봉인 전 감사·재감사·재재감사·네 번째·다섯 번째·여섯 번째 재감사(B-6 반영 확인 필요)
- 함께 고정하는 부록 파일(`.sha256`에 적음)
  - 규범 규칙 `v5_resume_4368/rev26_fixed/excl_fields_r5.py`
  - 원 출력 적용 목록 `v5_resume_4368/rev26_fixed/rev26_excluded_fields_r5.json`
- 근거 결정: 사용자 결정 136·139, 2026-11-22 Q-J1, B-1 (가), N-1 (나), B-5 (가)
- 고치는 판: 원판, rev1~rev25, 등급 대조 표 `judge_932f1fb/_fixed/grade/r4_grade_compare_table.md`, R4 공통 블록 `judge_932f1fb/_fixed/handoff/r4_common_block_draft.md`는 고치지 않는다. 이 문서가 다시 정하는 것은 1~5절과 부록뿐이다.

## 0. 공개 (결과를 본 뒤의 개정)
- **결과를 본 뒤의 재판정이다.** 대상 결함은 436.8 판정 후 감사(B-2)와 판정서 작성 중에 결과를 본 뒤 찾았다.
- 작성자(control-expert)가 아는 것
  - 436.8 하네스 판정서 0.2·4.4·4.5·10절을 읽었다.
  - H-3 연구별 집계, 멈춤 표지 집합(S-6 20줄, G-5 5키, G-6 3키, 경로 2 G-1 134), H-4 경로 2 `U-6.status` pass, `ind_las` 필드 상태(`record_state` "기록", `adapter_defect` 거짓, 판독 불가 0)를 안다.
  - 부록 B를 만들려고 R4 판정 출력의 키 구조, 경로 2 `harness.json`의 `v5_options`·`head_check` 블록, 경로 1 `head_check.json`, 절대 경로 문자열의 루트 집계를 열었다. M4 실행본 두 개를 읽었다. 그 밖의 값은 형태 검사에만 썼고 출력하지 않았다.
- **통계·감사 권고도 원 판정 세부를 본 뒤 나왔다**(stats 검토 1 7번·검토 2·3 [오염 후], verif 감사들은 원 출력 구조를 읽음).
- **결과 뒤에 넣은 예외 둘**
  1. IND_LAS 표지로 생긴 경로 1 H-4 `판정 불가`를 S-13으로 세지 않는다(1.2). 등급 대조 표 1.2 3·4에 예외를 하나 더하는 것이다. 436.8 데이터는 그 칸을 지나지 않는다(작성자가 안다).
  2. 부록 A의 C16 이름 예외(`x16_records`·`c16` 안에서 스칼라 `dt_s`·`duration_expected_s`·`folder`·`rc_source` 등을 뺌)는 "판정값은 빼지 않는다"의 예외다. 비교기 `compare_r4.py` 437~455행 선례를 따른다.
- 그래서 rev26 재판정 낱말은 **사전 등록 증거로 세지 않는다.** 원 판정 낱말(H-3 판정 불가 S-13, H-4 판정 불가)은 판정서에서 지우지 않고 새 낱말과 나란히 둔다.
- 결과를 내다보며 고를 수 있는 갈림길은 정의 문장으로 하나로 줄였다. 도구 커밋·실행본·실행 환경은 4′에서 고정한다. (d)의 비교 범위는 규범 스크립트로 정했다.
- A형 묶음(`v5paper_imua_rules_draft.md`, 봉인 뒤 `v5paper_imua_rules.md`)은 별도 커밋 TA로 판정한다(A형 규칙 3.1). TA의 436.8 모드 확인(A형 J-2) 출력은 rev26 낱말로 쓰지 않는다.

## 1. 범위 (구현자에게 넘기는 정의 문장)

### 1.1 표
| # | 묶음 | 경로 | 근거 정의 문장(파일:행) | 고칠 것 | 판단 |
|---|---|---|---|---|---|
| R26-1 | H-3 | 경로 2 | `u3_u6_rerun_rules.md`:19 "키 = v4 저장 파일의 `records[].id`(wrapper) 또는 `results[].key`(screen) 문자열 그대로" | screen 꼴 파일의 키를 위 정의대로 문자열 그대로 쓴다. 파일 이름을 키·suite에 섞지 않는다. 그 결과 V0·VB 짝과 연구 C·D의 G-5 탐지가 원 정의대로 된다 | 규칙 변경 아님. U-3 1,114 키는 연구 사이 중복 0·연구 안 중복 0(`v5paper_imua_stats/key_collide.json`) |
| R26-2 | H-4 | 경로 1 | 등급 대조 표 1.1(36~46행, 닫힌 어휘. 42행: 경로 1 기록 낱말은 `state` 키), H-4 행(105행), H-7 행(108행) | `ind_las` 출력에 `state`·`status`·`markers`를 더한다. 값은 1.2 표대로 기존 필드에서 기계적으로 정한다. 다른 필드는 바꾸지 않는다 | 키를 더하는 일. 값은 1.1 어휘만 쓰고 표로 고정한다 |
| R26-3 | H-4 | 두 경로 | 원판 4.1 표(70~75행), 80행 "섞이면 멈춘다(8.2 S-2)", 281행 S-2, `u3_u6_rerun_rules.md`:16(U-6은 VB만, C2 = ③ 켬) | u6 저장 줄마다 `records[].controller`와 `records[].v5.controller_tag`를 읽는다. 대응: **C2 → `final_C4G2_P3_LAS_K1`**(4.1 VB 행), **ABL → `ABL_LAS_K1`**, **IND → `IND`**, **IND_LAS → `IND_LAS`**. 두 필드가 모두 있고 `controller`가 이 네 이름 가운데 하나이며 `controller_tag`가 그 대응 문자열과 그대로 같을 때만 통과한다. 그 밖은 두 경로 모두 S-2다. 파일 머리의 `<제어기>.controller_tag` 메타 블록은 읽지 않는다. 접미사를 떼는 술어를 쓰지 않는다 | 규칙 변경 아님. `controller_tag`는 같고 `controller`만 다르면 281행 둘째 구로 읽는다. 436.8 입력의 쌍은 위 넷뿐이다(감사 실측). 436.8 데이터에서 걸리지 않는다((e) diff 0) |
| 모드 | H-1~H-12 | 두 경로 | — | 태그 모드는 실행 인자 `--tag-mode {4368,imua}`로만 고른다. 기본값은 `4368`이다. 436.8 재판정은 이 인자를 주지 않는다. `imua`는 TA에서만 쓴다. 모드는 출력에 새 키로 적지 않는다 | — |
| (범위 밖) | — | — | 436.8 판정서 10절 후보-1~6, 8~10, Chrono-1~ | 고치지 않는다 | — |

### 1.2 R26-2 값 대응표 (결과 전 고정)
- 입력 필드(경로 1 `ind_las.json` 기존 최상위 키): `record_state`(문자열), `adapter_defect`(참거짓), `gate_unreadable`(정수, "판독 불가 수")
- 표지 목록 `markers`는 아래 순서로 더한다.
  1. `adapter_defect`가 참 → `"IND_LAS:adapter_defect"`
  2. `gate_unreadable` > 0 → `"IND_LAS:판독 불가 <n>"`(n은 정수 그대로)
  3. `record_state` ≠ "기록", 또는 위 세 키 가운데 하나라도 없음 → `"IND_LAS:기록 상태 미정"`
- `markers`가 빈 목록이면 `state` = `status` = `"기록 완료"`, 아니면 둘 다 `"기록 불완전"`
- 436.8 데이터는 빈 목록 칸이다(`"기록 완료"`, `[]`).
- `state`는 등급 대조 표 1.1 42행(경로 1 기록 낱말 키), `status`·`markers`는 436.8 판정서 4.5절이 결측으로 적은 키다. 같은 값이다.
- 표지 꼴의 근거
  - 비교기 `bundle_markers`는 `r4_lists.json bundles.{b}.markers`·`harness.json bundles.{b}.gates`만 읽고 RD-8 유무만 본다(`compare_r4.py` 81·132·291·802~812·1094~1099행). `ind_las.json`은 읽지 않는다.
  - RD-4의 이름 구분 취지대로 등급 낱말을 표지 이름에 쓰지 않는다.
  - IND_LAS는 경로 1에만 있는 기록 열이다(등급 대조 표 61·105행). H-12처럼 "한 경로 기록"(115행)으로 다룬다.
- `markers`가 비어 있지 않으면 경로 1 H-4는 H-3과 같은 규칙으로 `판정 불가`다(105행).
- **결과 뒤 예외(0절 1)**: 이 `판정 불가`는 등급 대조 표 1.2 3·4에서 S-13으로 세지 않는다. 이유는 "IND_LAS 기록 불완전(한 경로 기록)"으로 적는다. `IND_LAS:` 표지는 `ind_las.json`에만 쓰고 `r4_lists.json bundles.H-4.markers`에는 옮기지 않는다.

## 2. 도구 커밋·checkout·실행본·실행 환경 (RD-1 4·5, RD-2를 대신하는 조건)
- **T26 = rev26 도구 커밋.** 기준 커밋은 M4 `932f1fb1724f074e4ee93a9c02193c7c840d13c4`다.
- 바꿔도 되는 파일
  - 경로 1 R4 허용 목록 파일(`judge_932f1fb/_fixed/run/run_judgement_path1_M4.ps1` 30~43행의 14개)
  - 경로 2 도구 폴더 `06_analysis/02_control/verif_matrix/v5_resume_4368/path2/`·`path2_v5c/`
  - 각 경로의 단위 시험
  - **규칙 파일**: `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev26.md`, `.sha256`, `v5_resume_4368/rev26_fixed/**`(master의 봉인 판과 바이트가 같아야 함). 두 경로 도구의 봉인 확인은 도구 checkout의 규칙 파일을 읽기 때문이다.
  - **`.gitattributes`**: 7절의 `-text` 줄을 더하는 변경만 허용한다(그 밖의 줄 diff 0). 규칙 파일이 worktree에서도 `-text`·LF로 체크아웃되어 봉인 sha가 같게 하기 위해서다.
- **03_src·02_params와 그 밖의 04_scripts는 바꾸지 않는다.** A형 처리는 T26에 넣지 않는다(A형 TA).
- **checkout(사용자 결정 N-1 (나))**: T26 전용 worktree `C:\workspace\outrigger_control\.claude\worktrees\rev26-t26`(HEAD = T26, `git worktree lock`, `core.autocrlf=true`). 도구는 worktree에서, 입력(436.8 저장 결과·근거)은 메인 checkout에서 읽는다. 출력은 메인 checkout 쪽 결과 폴더에 쓴다.
- **입력 기준(B-5, 사용자 결정 (가))**: 436.8 핵심 입력(`resume_k1`, `v5_rerun/las_k1`, `07_results`, v5 저장 결과 대부분)은 git 밖이라 worktree에 없다. 결과·데이터 입력은 모두 메인 checkout에서 읽고, 출력에 적는 입력 상대 경로도 메인 기준으로 만든다. 도구 저장소(worktree)에서는 아래 W만 읽는다.
  - 경로 2(T26 코드 변경): `p2_4368.py`·`p2_x16.py`·`p2_u3.py`·`p2v5c_common.py`의 최상위 인자 파서에 `--data-root <폴더>`(기본값 = `repo`)를 더한다. `repo`가 하던 일 가운데 D는 `--data-root`로 옮기고 W는 `repo`에 둔다. 인자가 없을 때의 동작은 `932f1fb`와 같아야 한다(단위 시험).

    | 구분 | 대상(932f1fb 코드 확인, 함수 단위) |
    |---|---|
    | D → `--data-root` | 상대 입력 경로를 푸는 곳과 출력에 적는 상대 경로의 기준. `p2_4368.py`: `rel_posix`와 그 모든 호출처, `_rel_entry_path`, `r4_input_check`, `key_source_index`, `cmd_harness`(매니페스트 `path`·`stored`·`key_source`·`key_source_override`), `cmd_anchors`(`--v5-root` 기본값), `jp_result_json`, Chrono 하위 명령의 `resolve_result`·`resolve_runner_row`·`runner_root`(5단계에서 돌지 않으나 같은 규칙). `p2_x16.py`: `cmd_g3`(`--las-k1-dir` 기본값과 `rel_posix`), `cmd_c16`(`rel_posix`). `p2_u3.py`: `study_keys`, `settle_v2_recount`, `rd7_row`. `p2v5c_*.py`: `rel_file`의 모든 호출처(`cmd_grid`·`cmd_noise`·`cmd_stage1`), `dg3_keys` 기본값 |
    | W → `repo` | 봉인 확인(`check_seals`·`check_chrono_seals`·`check_rev3`·`_check_one`, 규칙 sha 표), HEAD·git 기록(`git_head`·`head_check`·`git_commits_since`·`git_diff_stat`), 03_src(`load_is_extend_start`), 도구 스크립트(`run_judge`의 `r79_sensor_judge.py`와 그 sha, `cmd_openloop`), 02_params(`yaml_vmax`), Chrono 행 매니페스트(`cmd_chrono`의 매니페스트 기본값 = 아래 W 목록의 `chrono_rows_manifest.json`, 5단계에서 돌지 않음) |

    - `p2_d1.py`·`p2_v5j.py`·`p2_t3k.py`는 바꾸지 않는다(D 없음). `p2_x16.py d1`은 `--data-root`를 넘기지 않는다.
  - 경로 1(코드 변경 없음, 실행본 인자로 맞춤): 결과 입력을 도구 저장소 기준으로 푸는 기본값은 `h11 --las-k1-dir`와 `resume_k1_family.py --data-root` 둘이다. 실행본이 둘 다 cwd 상대 값으로 준다(5단계 경로 1의 5·6번). 그 밖의 결과 입력은 실행본 인자(cwd 상대) 또는 `--root .`·`--grid-root .`로 메인에서 읽는다.
  - W(두 경로 공통, 모두 T26 추적 파일): 규칙 파일(`verif_matrix/*.md`·`.sha256`, 원판 부록 A 34개, 모두 `-text`), 03_src·04_scripts·`paper_runs/scripts`·판정 도구 폴더의 코드(경로 1 `import-check`의 모듈 색인 포함), 판정·하네스 모듈이 자기 위치로 읽는 추적 자료(`02_params/{rexome33.yaml, scm_soil_sets.json, pad_variants.json}`, `06_analysis/00_dynamics/{slope_crawler_settle.json, pad_bekker_p0_soilsets.json}`, `06_analysis/02_control/s8/rev76/*`, `s8/s8_rev52_cs836_scope.json`, `s9/rev80/*`, `verif_matrix/v5_resume_4368/chrono_rows_manifest.json`), HEAD·git 기록
  - W 가운데 작업 트리 줄바꿈이 원 출력 비교 잎에 닿는 03_src 파일은 `03_src/outrigger_sim/hydraulics/v5_options.py`(`v5_options.sha256`)뿐이다(작성자 점검 2026-11-23: 비교 64자리 잎 2,402개 가운데 03_src·02_params 파일 sha와 같은 것은 7개, 모두 CRLF 꼴. 그 가운데 경로 1 `h6_L1_reference.json :: meta.c2_py_sha256`은 저장 입력 `h8_noise_VB.json`의 `meta`를 옮긴 값이라 checkout과 무관하다, 여섯 번째 재감사 W-n). 그래서 worktree는 `core.autocrlf=true`여야 한다.
  - W 자료를 가리키는 경로 문자열이 출력에 남는 곳은 worktree 절대 경로가 된다(원 출력의 예: 경로 1 `h2_select.json :: rules` = `d1_select`의 규칙 파일 기본값, 여섯 번째 재감사 B-6). 부록 A는 W 자료 위치를 도구 위치와 같이 NT로 정규화한다(r5). 부록 A의 W 자료 위치 목록은 위 W 목록과 같다(규칙 파일: `verif_matrix/` 바로 아래 `*.md`·`*.sha256`과 `v5/v5_criteria*.md`).
- RD-1 4를 대신하는 조건(메인이 5단계 전에 git으로 확인하고 `rev26_fixed/t26_identity.json`에 기록)
  1. `git diff --name-only 932f1fb..T26`가 위 허용 집합 안에 있고, 4′에서 고정한 "바뀐 파일 목록"과 같다
  2. `git diff --name-only b9f5707..T26 -- 03_src 02_params`가 비어 있다
  3. 허용 목록 파일 가운데 바뀌지 않은 파일은 `git show T26:<파일>`과 `git show 932f1fb:<파일>`의 LF 바이트 sha256이 같다
- RD-1 5를 대신하는 조건: 판정 도구는 HEAD = T26인 worktree의 파일로 돈다. 두 경로 head-check와 실행본 관문은 기대 HEAD와 비교 커밋을 모두 T26으로 본다.
- **5단계 실행본 — M4 실행본에서 바꾸는 줄(이것뿐)**
  - 경로 1 `run_judgement_path1_M4.ps1`
    1. `$M4`(13행)·`$R4`(14행) → T26
    2. `$Judge`(26행) → `<WT>\06_analysis\02_control\verif_matrix\scripts\resume4368_judge.py`, `$Co`(27행) → `<WT>\04_scripts\04_hydraulic\coupled`(`<WT>` = 위 worktree 절대 경로)
    3. `$FirstSidecars`(46행) → 메인 checkout의 저장소 사본 `06_analysis/02_control/verif_matrix/v5_resume_4368/judge_932f1fb/_fixed/tools/sidecars_b9f5707.py`(sha `0962f639…`)
    4. 출력 폴더(`$Out`, 21행) → `judge_rev26_<T26 앞 7자>/harness_path1`
    5. h11 호출(116행)에 `'--las-k1-dir', '06_analysis/02_control/v5_rerun/las_k1'`을 `--h11-dir` 쌍 바로 뒤에 더한다(cwd 상대, `/`)
    6. family_table 호출(109행)에 `'--data-root', '.'`을 출력 파일 인자 바로 뒤에 더한다
    7. `--root` 인자는 더하지 않는다. 결과 입력에 `--root`·`--grid-root`를 받는 하위 명령(r4-inputs·jp-reuse·r4-lists·grid-h10·family-f-trigger·family-f)은 M4 실행본이 이미 `.`을 준다. 기본 ROOT(= worktree)로 도는 head-check·import-check·appendix-a는 2절 '입력 기준'의 W만 읽는다
    - 그대로 두는 것: `Set-Location C:\workspace\outrigger_control`(12행, cwd = 메인. 입력 상대 경로 문자열이 원 출력과 같게 남음), `$Py`·`$PyDev`(인터프리터), 입력 변수(`$Rk`·`$V5`·`$U3`·`$Steps`·`$X`), head-check·import-check·appendix-a 호출(기본 ROOT = `$Judge`의 저장소 = worktree이므로 `--root`를 주지 않음)
  - 경로 2 `run_judgement_path2_M4.ps1`
    1. `$M4`(25행)·`$R4`(26행) → T26
    2. `$WT = <worktree>`를 더하고 `Set-Location -LiteralPath $WT`(24행). 관문 `Test-CheckoutState`(183~194행)와 끝 관문(412~414행)이 worktree의 HEAD·트리를 보게 하기 위해서다.
    3. `$P2`(38행) → `"$WT\$Base\path2"`, `$V5c`(39행) → `"$WT\$Base\path2_v5c"`
    4. `$AllowListPath2`(56~72행) → T26 blob 값(`git show T26:<파일>` raw 바이트 sha256)
    5. `$ManifestSource`(35행) → 메인 checkout의 저장소 사본 `…/judge_932f1fb/_fixed/manifest/p2_manifest_draft.json`(sha `fa0b72bf…`)
    6. 출력 폴더(`$Out`, 430행) → `"$Repo\$Base\judge_rev26_<T26 앞 7자>\harness_path2"`
    7. 입력을 읽는 9개 호출에 `'--data-root', $Repo`를 `--out <파일>` 쌍 바로 뒤에 더한다: harness·anchors·jp(`p2_4368.py`), g3·c16(`p2_x16.py`), u3(`p2_u3.py`), v5c_stage1·v5c_grid·v5c_noise(`p2v5c_*.py`). seal·d1·items·v5j_u9·v5c_merge에는 주지 않는다(D 없음)
    - 그대로 두는 것: `$Repo`(23행, 메인. 7번 `--data-root`의 값), 입력 변수(`$Rk`·`$Lk`·`$V5`·`$StoredGrid`·`$X`·`$JpBatches`, 40~46행), `$Conda`·`$CondaPython`(인터프리터)
  - **인터프리터 경로는 바꾸지 않는다**(원 출력의 인터프리터 원소가 비교 대상).
- **`rev26_fixed/t26_identity.json`(4′에서 고정)**: T26 전체 해시, 바뀐 파일 목록, 두 5단계 실행본 sha와 M4 실행본 대비 diff, `$AllowListPath2` 표, worktree 경로와 `core.autocrlf`, 외부 도구 sha(`~/.claude/tools/verif/log_errors.py` `3b9a8eac…`, sidecar 사본, 매니페스트 사본, `compare_r4.py` `8ff3d32b…`), 실행 환경(dynamics-dev·python-dev의 `conda list --export` sha와 python 판), 2절 '입력 기준' 표와 두 경로 구현 기록의 대조 결과, worktree의 `v5_options.py` raw sha256
- **worktree 깨끗함(W-i)**: 메인이 5단계 시작 직전과 끝난 직후에 `git -C <WT> status --porcelain`(추적·비추적 모두)이 비어 있는지 보고, 명령·시각·출력을 `t26_identity.json`의 `wt_status_before`·`wt_status_after`에 적는다. 비어 있지 않으면 시작하지 않는다(시작 전). 끝난 뒤라면 설정 결함으로 보고한다(끝난 뒤, 1회로 셈).
- **RD-2(봉인 확인)**: T26의 두 경로 도구는 봉인 확인 목록에 rev26을 더한다.
  - 경로 1: 최상위 `rules_seal`이 있는 출력에만, 그 출력의 **기존 하위 키 꼴**로 한 칸을 더한다.
    - revisions 꼴: `rules_seal.revisions."v5_resume_4368_rules_rev26.md".{expected_sha256, seal_file_sha256, rules_file_sha256}`
    - 파일 꼴(`judge4368_common.py`:720): 같은 이름 칸의 `{file_sha256, pinned_sha256, seal_file_sha256}`
    - `u3_judge.json`의 중첩 블록 `G-3.rules_seal`에도 같은 꼴로 더한다.
    - `rules_seal`이 없는 출력(`family_table`, `h12_t4h_replay`, `h2_select`, `h6_L1_reference`, `h6_r79_judge`, `log_errors_run_harness`, `sidecars`, `u3_judge_k1`)에는 넣지 않는다.
  - 경로 2: `seals` 블록의 같은 이름 칸
  - 새 최상위 키를 만들지 않는다. 판→sha 지도(`v5j_u9 :: r4_rev13_25_sha256` 등)에도 넣지 않는다.

## 3. 구현 조건
- 보완마다 근거 정의 문장(파일:행), 값 대응표, 동치 대안 확인을 구현 기록에 적는다. **동치 대안 확인은 판정 도구가 아니라 식별자만 읽는 점검으로 한다.**
- 작성자: 두 보완(R26-1 경로 2, R26-2 경로 1)은 **436.8 H-3·H-4 출력과 판정 후 감사의 해당 줄을 읽지 않은 새 인스턴스**가 한다. 서로 다른 경로의 코드·출력을 열지 않는다. R26-3·모드 인자·봉인 목록은 두 작성자가 1·2절 정의 문장만으로 각자 맞춘다. 부록 B는 작성자에게 넘기지 않는다.
- 경로 2 작성자는 2절 '입력 기준' 표대로 `--data-root`를 넣는다. 경로 1 작성자는 입력 해석을 바꾸지 않는다(입력 기준은 실행본 인자로 맞춘다, 2절 경로 1의 5·6번). 두 작성자는 자기 경로 하위 명령마다 입력 경로를 무엇 기준(cwd·실행본 인자·`--data-root`·도구 저장소)으로 푸는지, 출력에 적는 상대 경로를 무엇 기준으로 만드는지 구현 기록에 표로 적는다. 도구 저장소 기준인 곳이 2절 W와 같은지도 적는다. 각 작성자는 자기 경로 행만 쓴다.
- **보완 한 번 = 도구 커밋 하나(T26).**
  - 개발 시험은 합성 고정물로만 한다.
  - **판정 도구는 봉인 뒤 5단계 실행 전에 436.8 저장 결과에 돌리지 않는다(어느 묶음이든).**
  - (d)의 불변 diff는 5단계 1회 실행 출력과 원 출력 `judge_932f1fb/`의 비교로 확인한다.
  - 5단계는 메인이 1회만 하고, 명령·시각·sha를 기록한다.

## 4. 순서와 담당
| 단계 | 담당 | 일 |
|---|---|---|
| 1 | control-expert | 이 문안, 부록 A·B |
| 2 | stats-design-expert | 범위 확인(검토 2·3). 수정 2~4의 부록 규칙 변경 확인(선택) |
| 3 | 메인 | `-text` 보호(7절), 봉인(rev26 + `.sha256`, 부록 두 파일 sha), 인용 파일을 봉인 커밋에 함께 넣음 |
| 4 | python-expert(새 인스턴스 2개, 경로별) | `932f1fb`에서 브랜치를 만들어 R26-1·R26-2·R26-3·모드 인자·봉인 목록 구현, 봉인된 규칙 파일을 T26에 넣음. 합성 고정물 (e)·(f), R26-2 칸 고정물, 입력 경로 해석 기록 |
| 4′ | verif-protocol-auditor `[시점] 판정 전` | 아래 4′ 점검 |
| 5 | 메인 | 2절 실행본으로 436.8 저장 결과(R2 `b9f5707`)를 두 경로 판정 1회. 이어서 비교기 `compare_r4.py`(sha `8ff3d32b…`)를 M4 판정 때와 같은 인자로, 폴더만 새 폴더로 바꿔 돌린다 |
| 6 | verif-protocol-auditor `[시점] 판정 후` | 판정 도구가 436.8 저장 결과에 돈 횟수를 러너 로그와 셸 기록으로 세고(범위: 2026-11-16 R4 판정 뒤부터), 1이 아니면 공개한다. (a)~(h) 대조(부록 A 방법) |
| 7 | control-expert 판정서 덧붙임 → integrity-checker → 커밋 | 6절 |

**4′ 점검**
- 2절 RD-1 4 대체 1~3, 두 경로 독립, 작성자 조건, `t26_identity.json`과 고정 파일 sha
- 436.8 저장 결과에 판정 도구가 돈 기록 0(봉인 뒤 4′까지)
- **실행본**: 두 5단계 실행본과 M4 실행본의 diff가 2절 "바꾸는 줄"뿐인지, `ps1_lint.py` 종료 0인지. `$AllowListPath2` 값이 `t26_identity.json`의 T26 blob과 같은지
- **`.gitattributes`·줄바꿈(B-4)**: `git diff 932f1fb..T26 -- .gitattributes`가 7절의 `-text` 줄 추가뿐인지 본다. worktree에서 대상 4개 파일(`06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev26.md`, `…/v5_resume_4368_rules_rev26.sha256`, `…/v5_resume_4368/rev26_fixed/excl_fields_r5.py`, `…/v5_resume_4368/rev26_fixed/rev26_excluded_fields_r5.json`)의 `git check-attr text`가 `unset`(`-text`)이고 `git ls-files --eol`이 `w/lf`인지 본다. `rev26_fixed/**`의 폐기본(부록 B 폐기본 목록)은 `check-attr`가 `unset`인지만 보고 줄바꿈 꼴은 보지 않는다. 다르면 멈춘다.
- **입력 기준(B-5, 확인만)**: T26 코드와 3절 구현 기록으로 2절 '입력 기준'을 확인한다.
  - 경로 2: D의 site가 모두 `--data-root` 기준이고, `repo` 기준은 W뿐이다. 실행본의 `--data-root` 9개 호출이 2절 경로 2의 7번과 같다.
  - 경로 1: 결과 입력을 도구 저장소 기준으로 푸는 기본값은 `h11 --las-k1-dir`·`resume_k1_family.py --data-root` 둘뿐이고, 실행본이 둘 다 준다. 그 밖의 경로 1 하위 명령(`$Co` 스크립트 포함)에 결과 입력을 `ROOT / …`로 푸는 기본값이 남아 있으면 실행본 인자로 덮였는지 본다.
  - **입력을 도구 저장소 기준으로 푸는 곳 = 2절 W에 열거한 것뿐**이다. 판정 import 닫힘의 모듈이 자기 위치로 읽는 자료도 포함하고, 모두 T26 추적 파일이다.
  - 다르면 5단계로 가지 않고 멈춰 묻는다(규칙 수정은 새 사용자 결정).
- 경로 1 실행본의 입력 인자는 모두 cwd 상대 경로이고 `/` 구분자다(절대 경로·`\`·`./` 시작 없음). 2절 경로 1의 5·6번 값도 같다. 도구의 `repo_relative` 대체 동작이 원 출력과 같은 문자열을 내게 하기 위해서다.
- git 밖 입력은 메인에서만 읽는다(실행본 인자, `--data-root`). 추적 입력은 경로마다 `git ls-tree -r --name-only T26 -- <경로>` 수가 0이 아님을 먼저 확인한 뒤 `git diff --name-only 932f1fb..<메인 HEAD> -- <경로들>` 0건을 본다. 0개 폴더의 diff 0은 확인으로 치지 않는다.
- **줄바꿈 잎**: worktree의 `03_src/outrigger_sim/hydraulics/v5_options.py` raw sha256이 `git show 932f1fb:<파일>`의 CRLF 꼴 sha256과 같은지 본다(2절 '입력 기준' 끝 문장). 다르면 멈춘다.
- **도구 sha 잎 점검**: 원 출력의 비교 대상 잎(부록 B에서 I·S·F가 아닌 것) 가운데 64자리 16진 값이 `git show 932f1fb:<허용 목록 파일>`의 raw·LF·CRLF sha256과 같은 것이 0건
- **정체성 필드 덮음 점검**: T26 도구를 **합성 고정물로만, 2절 5단계 실행본과 같은 꼴(도구 = worktree, cwd·입력·경로 2 `--data-root`·경로 1 `--las-k1-dir`·`--data-root` = 메인 쪽 합성 폴더)**로 세 번 돌린다.
  1. 기준 실행
  2. 다른 출력 폴더·시각
  3. 다른 worktree(다른 절대 경로)에 빈 커밋 하나를 더 얹은 HEAD
  - 세 출력 사이에서 달라지는 필드가 모두 부록 A 규범 규칙의 I·S·F 제외 또는 NT·NM 정규화로 사라지거나 (g)·(h) 대상이어야 한다. NM 문자열에 worktree 루트가 남으면 입력을 worktree에서 읽은 것이므로 불일치다.
  - 합성 h11 출력에 `las_k1` 폴더 경로 문자열이 없고(파일 이름만), 경로 1 출력 어디에도 `--las-k1-dir`·`--data-root` 값이 없다(경로 1 출력은 argv를 적지 않음). 경로 2 출력에 `--data-root` 쌍이 남으면 부록 A I 인자 원소로 빠지는지 본다.
  - 아니면 5단계로 가지 않고 멈춰 묻는다. 규칙 수정은 새 사용자 결정이다.

## 5. 기대 효과 (재판정 전 sha 고정, 숫자·집합)
| # | 기대 효과 |
|---|---|
| (a) | 경로 2 G-1 = 0. V0·VB 키 집합 각 1,114, 짝 1,114 |
| (b) | 경로 2 H-3 G-5 키 집합 = 경로 1 원 출력 G-5 집합(C·D 포함). 경로 2 S-6·G-6 목록은 원 출력과 diff 0 |
| (c) | `ind_las.json`: `state` = `status` = `"기록 완료"`, `markers` = `[]`. 다른 필드는 원 출력과 diff 0(부록 B `c` 13 경로 제외, NT·NM 정규화) |
| (d) | 부록 A 범위의 모든 출력이 원 출력과 diff 0(부록 A 규칙: 각 쪽이 자기 목록을 지우고 정규화한 뒤 비교) |
| (e) | R26-3은 436.8 데이터에서 diff 0. 합성 고정물 5건(태그만 맞음 / controller만 맞음 / 둘 다 다름 / 하나 이상 없음 / 표에 없는 controller 이름)에서 두 경로 모두 S-2. 네 대응 쌍 고정물은 통과 |
| (f) | `--tag-mode` 없이(436.8 모드) `_IMUA` 접미 태그 합성 줄은 S-2. `--tag-mode imua`에서만 허용 |
| (g) | 경로 1 `head_check.json`: `head` = `expected_head` = T26, `markers` = `[]`, `src_params_changed` = `[]`, `diff_exit` = 0, `exit_code` = 0. `blobs[].file` 목록·순서는 원 출력과 같고, 바뀌지 않은 파일의 `blobs[].M4`·`R4`는 원 값과 같고, 바뀐 파일은 `M4` = `R4` = T26 blob, 모든 `same` = 참. 경로 2 `harness.json`: `head_check` = {`expect`: T26, `head`: T26, `ok`: 참, `why`: null}. `v5_options.sha256` = `d2b903a2a666c97859a4a73b908ebdabe2cef28ae1dd5f47b728527f5762b28e`(원 값. `core.autocrlf=true` 작업 트리 CRLF 바이트 sha. git blob LF sha는 `a88ad603…`), `v5_options.loaded` = 참, `v5_options.path`는 NT 정규화 뒤 원 값과 같다. 다른 출력(`p2v5c_*`, `v5j_u9`)의 `v5_options` 블록은 (d) 대상 |
| (h) | 봉인 확인: 경로 1에서 최상위 `rules_seal`이 있는 출력과 `u3_judge.json :: G-3.rules_seal`마다 기존 하위 키 꼴의 `v5_resume_4368_rules_rev26.md` 칸이 있고 그 sha 값들이 봉인 값과 같다. `rules_seal`이 없는 8개 출력에는 칸이 없다. 경로 2 `seals`에 같은 칸이 있고 확인 통과다. 새 최상위 키가 없고, 판→sha 지도에 rev26이 없다 |

- 하나라도 어긋나면 rev26 낱말은 **"판정 불가(rev26 기대 효과 불일치)"**이고, 새 사용자 결정 없이는 더 고치지 않는다.
- 재판정 뒤에도 두 경로 표지 집합이 다르면 S-13 판정 불가를 그대로 둔다(IND_LAS 표지는 1.2대로 세지 않음).
- 등급 낱말 자체는 예측하지 않는다.

**5단계 실패 처리**
| 상황 | 조치 | 1회로 셈 |
|---|---|---|
| head-check·실행본 관문 실패(S-12·S-11, "nothing judged") | 멈춤. 출력 보존. 원인이 `t26_identity.json`과 다르면 설정 결함으로 보고하고 사용자 결정 뒤 다시 실행 | 셈(판정 출력 없음을 기록) |
| 어느 단계든 종료 코드가 실행본의 기대 종료 코드 표 밖 | 멈춤. 출력 보존. 다시 실행은 사용자 결정 뒤 | 셈 |
| 판정 출력이 생긴 뒤 (a)~(h) 불일치 | "판정 불가(rev26 기대 효과 불일치)" | 셈 |
| 판정 출력을 본 뒤 | 다시 실행하지 않는다 | — |

- 모든 실행 시도를 로그에 남기고, 6단계에서 센다.

## 6. 판정서에 적을 것
- 원 낱말과 rev26 낱말을 나란히 적고, 0절 공개 문장(결과 뒤 예외 둘 포함)을 그대로 옮긴다.
- 결함의 발견 시점(판정 후 감사 B-2), 원인 코드 줄, 고친 범위(키·출력 키·멈춤 분기·태그 문자열 비교·모드 인자·봉인 목록)를 적는다.
- 판정 정의·문턱·등급 표는 바꾸지 않았다고 적는다(결과 뒤 예외 둘 공개).
- `t26_identity.json`, (a)~(h) 대조, 재판정 실행 명령·시각·sha, 판정 도구가 436.8 저장 결과에 돈 횟수를 적는다.

## 7. 메인 처리 사항
- `.gitattributes`에 `-text`를 더할 대상
  - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev26.md`
  - `v5_resume_4368_rules_rev26.sha256`
  - `v5_resume_4368_rules_rev26_seal_candidate_draft.md`
  - `v5_resume_4368/rev26_fixed/**`
  - `v5_resume_4368/judge_rev26_*/**`
  - `v5paper_imua_stats/**`
- T26에 들어갈 같은 규칙 파일·`.gitattributes` 줄도 같은 바이트로 넣는다(2절 허용 집합: `.gitattributes`는 이 `-text` 줄 추가만).
- `.sha256` 첫 줄은 이 파일 값, 다음 줄은 부록 두 파일이다.
- 인용 근거를 봉인 커밋에 함께 넣고 `git status --ignored`로 빠지는 것이 없는지 본다.
- T26 worktree를 2절 경로에 만들고 잠근다(판정서 커밋까지 유지). 5단계 동안 메인 checkout의 추적 트리는 깨끗해야 한다(경로 1 `Assert-CleanTree`는 cwd = 메인을 봄). worktree는 5단계 앞뒤 `git -C <WT> status --porcelain`이 비어 있어야 한다(2절 W-i).

## 부록 A. (d)·(c) 비교 범위와 규범 규칙
**규범**
- 제외·정규화는 규범 스크립트 `rev26_fixed/excl_fields_r5.py`의 규칙으로 정한다(docstring이 규칙 본문). **각 쪽은 자기 출력에 이 스크립트를 자기 인자로 적용해 자기 목록을 만들고, 자기 제외를 지우고, 자기 정규화를 한다.**
  - 원 출력의 인자: 커밋 `932f1fb…`, 출력 토큰 `judge_932f1fb`, 실행 창, `--main-root C:\workspace\outrigger_control`
  - 새 출력의 인자: 커밋 T26, 출력 토큰 `judge_rev26_<T26 앞 7자>`, 5단계 실행 창, `--main-root C:\workspace\outrigger_control --checkout-root <T26 worktree>`
- 원 출력에 적용한 결과가 부록 B다.
- 두 쪽에서 I·S·F를 지우고 NT·NM을 정규화한 나머지가 같아야 한다. 한쪽에만 남은 경로도 불일치다.

**범위**
- 원 출력: `judge_932f1fb/harness_path1/*.json`과 `harness_path2/*.json`. 같은 이름이 `harness_path1_retry1/`에 있으면 retry1 판을 원 출력으로 쓴다(`head_check.json`, `r4_inputs.json`, `stage1_judge.json`, `stroke_H-9.json`).
- 새 출력: 5단계 폴더의 같은 이름 파일. **두 쪽 파일 집합이 같아야 한다.**
- (d) 무리: 모든 파일. 다만 다른 기대 효과가 맡는 것은 뺀다.
  - 경로 2 `u3.json`: (a)·(b)
  - 경로 1 `ind_las.json`: (c)
  - 경로 1 `head_check.json`(두 폴더): (g)
  - 경로 2 `harness.json`의 `bundles.H-3`(a·b), `head_check`·`v5_options`(g)
- 경로 1 `u3_judge.json`과 경로 2 `harness.json`의 `bundles.H-4`도 (d) 대상이다.
- (c) 무리: 경로 1 `ind_las.json`의 최상위 봉인 블록만 빼고, 새 키 `state`·`status`·`markers`는 (c) 값으로 따로 본다.

**경로 표기와 비교 방법**
- 경로는 토큰 배열이다: dict 키 문자열(점이 든 키도 한 토큰), 리스트 원소 전체 `"[]"`, 키가 40개를 넘는 dict의 모든 키 `"{*}"`(원 출력 기준), 인자 목록 원소 `"#<i>"`(원 출력의 위치, 참고용).
- **인자 목록은 I 원소를 지운 뒤 남은 순서열로 비교한다**(위치 번호로 맞추지 않음).
- 정규화: NT 문자열은 메인 checkout과 T26 worktree 루트의 **모든 출현**을, NM 문자열은 메인 checkout 루트의 **모든 출현**을 `<ROOT>`로 바꾼다. 대소문자 무시, `\`·`/` 두 꼴, 긴 루트 먼저. NM 문자열에 남은 worktree 루트는 그대로 두어 불일치로 드러낸다.
- 그 뒤 완전 일치를 본다: dict는 키 집합 비교, 리스트는 순서 포함, 수치는 RD-5 K-10 꼴 |a − b| ≤ 10⁻⁹ max(1, |a|, |b|).
- 원 출력에 없는 경로가 새 출력에 생기면 불일치다.

**규칙 요약(정본은 스크립트 docstring)**
| 범주 | 규칙 |
|---|---|
| S 봉인 블록 | 출력 최상위(`u3_judge.json`은 `G-3` 바로 아래도) 키 `rules_seal`, `seals`, `rules_sha256`, `rules_rev*_sha256`, `rules_rev13_to_rev25_sha256`, `rules_revisions`, `seals_ok`, `seals_eol_only`, `rules_match_seal`, `rules_sealed_sha256`의 하위 나무 |
| S 도구 판 블록 | `diff_vs_existing`, `definition_changes`(어느 깊이든), `common_sha256`, `imports` 바로 아래의 `*_sha256` |
| S 도구 문자열·도구 sha | `tool`, `tool_sha256`, `script`, `script_sha256`, `version`, `new_version`, `old_tool`, `existing_tool`, `judge_tool`, `meta_script` — 스칼라이거나 경로·sha 블록일 때만 |
| F 자유 문장 | `problems`, `why`, `note(s)`, `times_note`, `reason(s)`, `message(s)`, `detail(s)`, `description`, `comment(s)` — 문자열·null·문자열 목록일 때만. C16 목록은 `x16_records.json`·`c16.json` 안에서만(결과 뒤 예외 0절 2) |
| I 실행 정체성 | 스칼라 문자열 가운데 도구 커밋·출력 폴더 토큰·실행 창 안 ISO 시각이 든 것. 시각 키(`created` 등)의 스칼라 값 |
| I 인자 원소 | 출력 폴더 토큰·도구 커밋이 든 원소, `.py`·`.ps1` 도구 경로, `--root`·`--data-root`·`--allowed-src-changes`와 다음 원소 |
| NT·NM 정규화 | 위에 들지 않고 checkout 루트가 든 문자열. 도구 위치(루트 뒤가 `03_src`·`04_scripts`·`05_tests`·`verif_matrix/scripts`·`v5_resume_4368/path2*`·`paper_runs/scripts`)와 2절 W 자료 위치(`verif_matrix/` 바로 아래 `*.md`·`*.sha256`, `v5/v5_criteria*.md`, `02_params/`, `00_dynamics/{slope_crawler_settle, pad_bekker_p0_soilsets}.json`, `s8/rev76/`, `s8/s8_rev52_cs836_scope.json`, `s9/rev80/`, `v5_resume_4368/chrono_rows_manifest.json`)는 NT, 그 밖은 NM |
| (비교) | 입력 경로·sha 블록(재재감사 W-g), 판정 목록 digest, 물리 시각, 판정값, 구조 노드 |

- 실행 창(원 출력): `harness_path1` 2026-11-16T16:28:00~16:31:00, `harness_path1_retry1` 16:43:00~16:45:00, `harness_path2` 13:55:00~16:33:00. 새 출력은 5단계 실행 기록의 시작~끝에 같은 여유(앞뒤 1~2분)를 둔다.

## 부록 B. 원 출력 적용 목록 (별도 파일, 봉인)
- 파일: `v5_resume_4368/rev26_fixed/rev26_excluded_fields_r5.json`(LF)
- 꼴: `{"rules": "excl_fields_r5", "scope_d_skipped_files", "scope_d_skipped_subtrees", "scope_c_files", "d": {"<폴더>/<파일>": [[<토큰 배열>, "<I|S|F|NT|NM>"], ...]}, "c": {...}}`
- 수: d 1,020 항목(68 파일. 제외 I 105 / S 647 / F 172, 정규화 NM 87 / NT 9), c 13 항목(S)
- 생성
  ```
  python -I -B -X utf8 excl_fields_r5.py <out> --root <judge_932f1fb> --commit 932f1fb1724f074e4ee93a9c02193c7c840d13c4 --out-token judge_932f1fb --window "harness_path1=2026-11-16T16:28:00/2026-11-16T16:31:00" --window "harness_path1_retry1=2026-11-16T16:43:00/2026-11-16T16:45:00" --window "harness_path2=2026-11-16T13:55:00/2026-11-16T16:33:00" --main-root "C:\workspace\outrigger_control"
  ```
- sha256은 `.sha256`에 적는다(생성 시 목록 `9e1831f5af2621510f9b6a7a8bf9f9c39c85f7633d8ef69bdc87895902e19283`, 스크립트 `bee9eee74a002d84710cde59fa20a1f2517c0b8cfa56173314d1d4eec36465f5`. r4 목록과는 `rules` 이름과 `harness_path1/h2_select.json :: rules`의 범주(NM → NT) 하나만 다르다)
- 폐기본(보존만)
  - `excl_fields.py`(`37c57662…`)·`rev26_d_excluded_fields.json`(`6051f77f…`)
  - `excl_fields_r1.py`(`3da897c3…`)·`rev26_excluded_fields_r1.json`(`8074503d…`)
  - `excl_fields_r2.py`(`bda5e7da…`)·`rev26_excluded_fields_r2.json`(`f450784b…`)
  - `excl_fields_r3.py`(`bfe6354e…`)·`rev26_excluded_fields_r3.json`(`3a5d637c…`)
  - `excl_fields_r4.py`(`1fb6f701…`)·`rev26_excluded_fields_r4.json`(`fafca423…`)
