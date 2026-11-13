# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev14 (H-0 S-13 뒤: 러너 기록 `enable` 추가와 경로 2 dg3 줄 수정을 담은 R2, H-0 재실행, 모든 묶음 `git_at_start` = R2, R2에서 G-S 전체, 본 묶음 결과 전, 봉인 후보 초안)

- **상태: 봉인 후보 초안(봉인 전).** 봉인 전에는 실행·판정에 쓰지 않는다. 봉인 때 바꿀 머리 줄은 끝 절에 원문으로 적었다.
- 원판 `v5_resume_4368_rules.md`(sha256 `9019b405…`), rev1(`d9094fda…`), rev2(`497e4614…`), rev3(`dad8dfa6…`), rev4(`7ea87a30…`), rev5(`452a8436…`), rev6(`809e5639…`), rev7(`e81f7d31…`), rev8(`3ecafaaf…`), rev9(`4cf7843c…`), rev10(`62a0bd8d…`), rev11(`9bac4524…`), rev12(`78f1f99b…`), rev13(`383bffc1…`)은 고치지 않는다. 이 판은 rev13(sha256 `383bffc1f2d920dbba5b5a8c0871786a43e983d83e2d5c1e477718257f70973b`, 봉인 커밋 `b202ab1`) 위에 쌓인다. 전체 sha256은 각 판의 `.sha256`에 있다. 봉인 뒤 이 판과 앞 판이 다르면 이 판이 맞다. 이 판이 말하지 않는 것은 앞 판 그대로다.
- **시점: 436.8 본 묶음(H-1~H-10, Chrono C-1~C-8과 probe) 결과가 없을 때(봉인 SEAL_TIME, 봉인 커밋 SEAL_COMMIT).** `a861981`에서 돈 H-0 출력과 그 두 경로 판정은 있다. 그 출력은 이 판으로 대체되고 판정에 쓰지 않는다(R14-0, R14-2).
- 작성: control-expert, 2026-11-13. 기준 R = `75c5f75`(rev13 R13-4의 R). 계기: H-0 판정에서 두 경로의 등급이 갈렸다(원판 8.2 S-13). 경로 1은 통과, 경로 2는 H-T3-3 멈춤이다. FLAG는 만들지 않았고 본 묶음은 시작하지 않았다.
  - (A) 경로 2 `p2_t3k`가 D-1 파일 안의 dg3 줄(`t3.kind == "dg3"`)을 D-1 줄로 셌다. `las_targeted_rules_rev5.md` 2.5("R-0 = D-1 5 + dg3 2")와 다르므로 도구 결함이다.
  - (B) `las_targeted_rules_rev5.md` 2.2(57행)는 줄마다 `slope_clearance_margin.enable` True를 대조하게 정한다. 그런데 하네스 줄의 `resume_k1.slope_clearance_margin.settings`에 `enable` 키가 없었다. 이것은 기록 결함이다.
- **봉인 준비판이다.** 사용자 결정이 필요한 새 항목은 없다(R14-9 결정 표). 사용자 결정(2026-11-13: B는 기록 결함으로 보고 러너 수정 + H-0 재실행, A는 도구만 수정, R2에서 G-S 전체)은 R14-1~R14-8에 반영했다. 이 줄은 봉인 때 바뀐다.
- **바꾸지 않는 것**: 숫자 문턱, 등급과 우선순위, 멈춤 조건의 뜻, 묶음 범위와 행 목록, 사전 예측 값(P-1~P-15), P-1·P-2 앵커(rev1 RV1-5), 두 경로 요건(원판 9.2), `las_targeted_rules` 원판~rev5의 H-0 판정 규칙, K-0 조건(rev6 R6-C2), rev13의 A-5 범위·파일별 판단(R13-1~R13-3)·K-0 두 읽기 공개(R13-6). 고쳐 쓰는 것은 rev13 R13-4(R과 `git_at_start`)·R13-5(순서·G-S)·R13-6의 두 커밋 문장뿐이다(R14-3~R14-5). 이 판은 새 숫자를 쓰지 않는다.

## R14-0. 근거와 공개 (H-0 첫 실행 뒤, 본 묶음 결과 전)

- 2026-11-13 확인: 436.8 본 묶음 출력이 없다. `a861981`의 H-0 실행(17:47~18:11, 종료 0)과, R에서 두 경로가 낸 그 판정이 있다.
  - 경로 1 `h0_judge\path1\las_t3_judge_4368_path1.json`(`a5fafca5…`)은 통과다.
  - 경로 2 `h0_judge\path2\p2_t3k_h0.json`(`970a0ecb…`)은 H-T3-3 멈춤이다.
- **이전 H-0 출력을 본 범위(공개)**:
  - 메인 세션: 출력 폴더의 파일 이름 목록만 보았다(rev13 R13-0과 같음).
  - 실행 감사자: 러너 로그의 경고 사건 이름과 개수를 보았다.
  - 두 경로 판정자: 판정하려고 출력 내용을 읽었다.
  - 이 판의 작성자: H-0 출력과 두 판정 파일의 내용을 열지 않았다. 위 판정 결과와 원인 (A)·(B)는 메인 세션이 전한 요약이다.
- 사후 판단의 공개:
  - (A) 수정과 (B) 수정, H-0 재실행은 첫 실행의 판정을 본 뒤 정했다.
  - 바꾼 것은 기록 한 키(B)와 경로 2의 줄 세기를 rev5 2.5 문장에 맞춘 것(A)뿐이다. 판정 규칙·문턱·등급은 바꾸지 않았다.
  - **재실행 결과가 무엇이든 그 결과로 판정한다.** 첫 실행 결과를 골라 쓰지 않는다(R14-2).
- 판단 근거는 코드 diff이고(`git diff 75c5f75..ed7942b`, `git diff 75c5f75..f7c6d55`), blob sha256은 `git show <커밋>:<파일>`의 바이트로 계산했다.
- 실행 확인 두 건은 메인 세션이 전한 사실이고, 이 작성자는 그 출력을 열지 않았다. 확인 실행은 dynamics-dev, E 마스크로 했고 R14-1에 적는다.
- 읽은 규칙: rev13 전체, `las_targeted_rules_rev5.md` 2.2·2.5, 원판 A-5·5.1·6절·8.2·9.2·11.2, rev12 R12-3·R12-6, rev6 R6-C2.
- 이 작성자는 경로 2 작성자가 아니다(rev2 R2-0). 경로 2 코드는 열지 않았다.

## R14-1. A-5 재확인 (R → R2)

- `git diff --name-status 75c5f75..ed7942b`(러너 수정, 브랜치 `z4371-r4c30`, 부모 R)는 다음 두 파일이다.
  - `04_scripts/04_hydraulic/coupled/resume_k1_record.py` (+4/−1)
  - `05_tests/unit/test_resume4368.py` (+27, 시험 4개 추가)
- `git diff --name-status 75c5f75..f7c6d55`(경로 2 수정, 브랜치 `z4371-p2dg3`, 부모 R)는 `06_analysis/02_control/verif_matrix/v5_resume_4368/path2/` 아래 `p2_t3k.py`(+10/−1), `test_p2_t3k.py`(+35), `README.md`(+35/−9)다. 이 셋은 `03_src`·`02_params`·`04_scripts` 밖이고 판정 도구다.
- `resume_k1_record.py`는 rev13 A-5 범위 38개 안의 파일이다(R13-2 #7, `04_hydraulic` 23개 가운데 하나). 판단: **명령 비트 영향 없음(기록 전용)**. 근거는 셋이다.
  1. 바뀐 곳은 `controller_record()`가 돌려주는 사전의 `slope_clearance_margin.settings`에 `"enable": margin_settings.get("enable")`를 더한 한 줄과 docstring뿐이다. `margin_settings`는 이미 읽던 `controller.meta()`의 같은 블록이고, 새 호출은 없다.
  2. 부르는 순서: `verdict_runs._finish`는 238행에서 `commands_sha256`을 만들고, 245행에서 이 블록을 붙인다. 다른 호출처(`d1_runs`, `v5_rerun.run_record`, `r67_g1_screen`, `r79_sensor_screen`, H-0 러너)도 rev13 R13-2 #4·#8·#10·#19대로 명령을 만든 뒤에 부른다.
  3. 확인 실행 두 건(메인 세션 전달, dynamics-dev, E 마스크): H-0 R-0 1키와 H-1 1키의 `commands_sha256`이 저장값과 같다. 저장값은 각각 `a861981`의 H-0 출력과 `a861981` G-S다. 차이는 새 키, `wall_s`, 실행 정체성, 절대경로 1개뿐이다.
- `05_tests/unit/test_resume4368.py`는 러너가 import하지 않는 시험 파일이고 A-5 범위(`03_src`·`02_params`·하네스 경로) 밖이다.
- **P-1·P-2 앵커는 유지한다**(rev13 R13-3 그대로). A-5의 조건은 R2에서 R14-3 3의 확인이 참일 때 충족된다.
- **실행 env 고정(공개)**: Chrono-dev로 돌리면 하네스 명령 해시가 달라진다(메인 세션 확인). 원판 5.1(하네스 묶음은 dynamics-dev)대로 H-0과 H-1~H-10은 dynamics-dev로만 돌린다. 판정에서는 `.identity.json`의 `python`이 dynamics-dev 인터프리터인지 확인한다(rev6 R6-C2 정체성 표의 항목과 같은 원본). 다르면 원판 8.2 S-11이다.
- 결정 필요: **아니오**.

## R14-2. H-0 재실행과 첫 실행 출력의 처리

- `a861981`의 H-0 출력은 지우지 않는다. 출력 폴더 전체를 추적 밖 `06_analysis/03_hydraulic/coupled/v5/las/t3_k1_a861981_superseded/`로 옮긴다. 옮긴 폴더와 그 안 파일은 커밋하지 않는다. 그 폴더는 `.gitattributes` `t3_k1/**` 줄에 들지 않는다.
- 옮기기 전과 뒤의 파일 목록과 sha256을 판정서에 적는다. 두 경로 판정 파일(경로 1 `a5fafca5…` 통과, 경로 2 `970a0ecb…` H-T3-3 멈춤)도 지우지 않는다. 이것들은 **기록으로만** 둔다. 판정서에는 S-13 경과로 적고, 판정 등급·사전 예측 대조·한계 문장의 근거로 쓰지 않는다.
- H-0은 R2에서 같은 러너·같은 조건으로 처음부터 다시 돈다. 조건: `las_targeted_rules_rev5.md` 2.6의 출력 이름, identity `start`·`end` 사이드카, 작업자 12, affinity 마스크 `0x00FF5500`, dynamics-dev. 이전 출력 위에 이어 쓰지 않는다(옮긴 뒤 빈 폴더에서 시작).
- 재실행 H-0의 판정은 rev5와 이 문서(원판~rev14)의 두 경로로 낸다. 그 결과가 원판 A-3·S-14의 H-0 판정이다.
- S-13의 처리: 첫 실행의 S-13은 원인 (A)·(B)가 정해졌고 사용자 결정으로 닫혔다(R14-9). 재실행에서 두 경로 등급이 다시 갈리면 원판 S-13 그대로 멈추고 묻는다.
- 결정 필요: **아니오**(사용자 결정 2026-11-13: B는 기록 결함, 러너 수정 + H-0 재실행).

## R14-3. 커밋 R2와 `git_at_start` (rev13 R13-4를 고쳐 씀)

- **정의**:
  1. H-0, H-1~H-10, Chrono C-1~C-8, probe, J_P 재실행이 생기면 `JP`까지 모든 묶음의 `git_at_start`는 R2 하나다. rev13 R13-4 1·2의 구분(H-0 `a861981`, 본 묶음 R)은 없어진다. 원판 A-5 첫 문장 "모든 묶음이 같은 `git_at_start`"는 문장 그대로 다시 성립한다. 원판 0절 1항 "한 커밋에서 한 번만"도 rev13 R13-4 4의 읽기 없이 문장 그대로 성립한다.
  2. **R2의 모양**(rev13 R13-4 3과 같은 형식):
     - 봉인 커밋 S2: 부모 = R `75c5f75`(5행의 봉인 커밋 값 = `75c5f75`). S2가 바꾸는 것은 (가) 세 파일과 (나) `.gitattributes` 3줄뿐이다.
     - S2 위에서 `z4371-r4c30`(`ed7942b`)을 `--no-ff`로 병합한다(병합 커밋 M1).
     - M1 위에서 `z4371-p2dg3`(`f7c6d55`)를 `--no-ff`로 병합한다. 이 마지막 병합 커밋이 R2다.
     - R..R2 사이 커밋은 S2, `ed7942b`, M1, `f7c6d55`뿐이고, 모두 아래 허용 목록 안의 파일만 바꾼다.
  3. **R2의 조건**(모두 참이어야 한다):
     - R2가 2의 모양이다. `git rev-list --parents -n 1 R2`의 부모가 M1과 `f7c6d55`, M1의 부모가 S2와 `ed7942b`, S2의 부모가 `75c5f75`다.
     - `git diff --name-only 75c5f75..R2 -- 03_src 02_params`의 출력이 비어 있다.
     - `git diff --name-only 75c5f75..R2 -- 04_scripts`의 출력이 정확히 `04_scripts/04_hydraulic/coupled/resume_k1_record.py` 한 줄이다. 이것이 R2에서 A-5의 확인이다. `c6bb55b`..R2의 차이는 rev13 R13-2 표에 #7의 이 수정을 더한 것과 같다.
     - `git diff --name-only 75c5f75..R2`의 모든 파일이 허용 목록 안이다. blob sha256은 `git show R2:<파일>`의 바이트(저장소의 LF 바이트)로 잰다.
       - (가) `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev14.md`, `v5_resume_4368_rules_rev14.sha256`, `v5_resume_4368_rules_rev14_seal_candidate_draft.md`
       - (나) `.gitattributes`에 (가) 세 파일의 `-text` 줄 3개를 더한 것만(더한 줄 3개, 지운 줄 0개). 출력 폴더 줄은 R에 이미 있다(rev13 R13-4 3 (나)).
       - (다) `04_scripts/04_hydraulic/coupled/resume_k1_record.py`: blob `e5414bf3ca02f8b6f1ab8316b100f2c2e41a5534eef5f8729ced4feefe9fa371`
       - (라) `05_tests/unit/test_resume4368.py`: blob `8b1e4de15dda89ac2c145e83660f056ae2cb24cb70aacc9c0130a78a5e98fd35`
       - (마) `06_analysis/02_control/verif_matrix/v5_resume_4368/path2/` 아래 `p2_t3k.py` blob `44141c9f74a6e8099218722fd731888e9c765832614e788114ef6089da8b9a79`, `test_p2_t3k.py` blob `e6b5e11a15b2530e56481897f29360761df8a2dd4c49336c284334e94962899c`, `README.md` blob `c6ed7e13104bbba0b89bb6abb9758aa8e5c94b5af9a8b6642e2ac9714a4134ef`
       - (바) rev8 R8-4의 판정서·감사 기록, `00_docs/decision_log.md`·`00_docs/00_roadmap.md`·`00_docs/handoff/session_handoff.md`의 문서 갱신(rev13 R13-4 3 (라)·(마)와 같음)
     - 하나라도 거짓이면 어떤 묶음도 시작하지 않는다.
  4. sha 표기 주의: `core.autocrlf=true` checkout의 작업 복사본은 CRLF다. 그래서 (다)·(라)를 작업 복사본으로 재면 각각 `ed95e8da…`·`66f923c9…`가 나온다(LF blob을 CRLF로 바꾼 바이트의 sha256과 같음). 조건 대조에는 blob sha256만 쓰고, 작업 복사본 sha256은 판정서에 참고로 적는다.
- 결정 필요: **아니오**(사용자 결정 2026-11-13: 러너 수정 + 도구 수정을 R2에, R2에서 G-S 전체).

## R14-4. 순서와 G-S (rev12 R12-6을 Y = R2로, rev13 R13-5를 고쳐 씀)

- **순서**:
  1. 이 판을 봉인한다(sha256과 봉인 시각 확정). 실행 중인 묶음이 없으므로, 봉인 파일은 S2를 만들 때 메인 checkout에 넣는다.
  2. 첫 H-0 출력 폴더를 R14-2대로 옮긴다(추적 밖, 커밋 없음).
  3. `tools/verif/seal_check.py`로 확인한 뒤 S2를 만든다. 이어서 `ed7942b`, `f7c6d55`를 차례로 `--no-ff` 병합해 R2를 만든다. R14-3 3을 확인한다.
  4. **R2에서 G-S 전체를 다시 돈다**: 하네스 G-S, Chrono G-S, 두 경로의 G-S 확인. 커밋 정체성을 대조하는 도구에는 `--git-at-start R2`를 준다(rev12 R12-3, R14-6). 출력은 untracked `gs_harness_<R2>/`·`gs_chrono_<R2>/`에 두고 sha는 판정서에 적는다(rev11 R11-6).
  5. R2의 G-S가 원판 11.2·rev11·rev12·R14-6대로 통과하면 H-0을 R2에서 다시 돈다(R14-2). H-0 판정이 원판 A-3·S-14를 통과하면 본 묶음을 R2에서 시작한다(원판 11절 1·3).
  6. R2 뒤에는 모든 묶음이 끝날 때까지 커밋·병합하지 않는다(원판 A-5 둘째 문장, S-12).
- **R12-6과의 관계**: R12-6은 문장 그대로 적용하되 최종 Y = R2다. "R2에서 이 판 봉인 뒤 G-S 전체를 다시 돌린 것을 원판 11.2 충족으로 본다." 모든 묶음의 `git_at_start`는 R2이고, 판정서·감사 기록만 더한 커밋은 모든 묶음이 끝난 뒤에만 만든다. R(`75c5f75`)과 `a861981`을 포함해 R2보다 앞선 커밋의 G-S는 기록만 하고 인용하지 않는다.
- **K-0·R11-4·S-12**: 모든 묶음이 한 `git_at_start` R2를 쓴다.
  - H-0 재실행의 `.identity.json` `start`·`end` `git.head`는 모두 R2여야 한다(rev6 R6-C2, 기록이 여러 개이면 rev13 R13-6의 두 읽기 공개).
  - Chrono 행의 `code_at_launch.git.head`, level·L2b·L1-R 행의 `result.json` `code_state.git_at_start`, 하네스 줄·사이드카의 커밋도 모두 R2다.
  - 다르면 원판 8.2 S-12다.
  - rev13 R13-5·R13-6의 "묶음별 `git_at_start`" 문장은 R2 하나로 읽는다.
- 결정 필요: **아니오**(사용자 결정 2026-11-13: R2에서 G-S 전체).

## R14-5. rev5 2.2 `enable` 대조의 두 경로 읽기 (공개)

- 규칙 문장(rev5 2.2): "줄마다 제어기 설정을 대조한다: … `slope_clearance_margin.enable` True, `flat_soil_margin_m` 0.03. 어긋나면 그 줄은 오류 줄이다(H-T3-2 재시도 뒤에도 남으면 H-T3-3)."
- 두 경로가 읽는 원본이 다르다.

| 경로 | 읽는 것 | 어긋날 때 |
|---|---|---|
| 경로 1 | 러너 `las_t3.py`가 실행 중 설정 객체를 검사한다(`controller_problems` → `config_problems` → `gate_problems`, 351·353행 `margin.enable`·`flat_soil_margin_m`). 판정기는 그 결과인 `error` 줄 수(H-T3-2·H-T3-3)를 읽는다 | 러너가 `error` 줄을 쓴다 |
| 경로 2 | 줄 필드 `resume_k1.slope_clearance_margin.settings.enable`(와 `flat_soil_margin_m`)를 직접 읽는다 | 키 없음·True 아님 = 어긋남 |

- R2의 러너는 이 키를 기록한다(R14-1, `controller.meta()`의 값). 그래서 재실행 H-0 줄에서는 두 읽기가 같은 사실(실행한 제어기의 R4c30 `enable`)을 본다. 판정서에는 위 표를 원판 9.2 "두 경로 정의가 다른 곳" 표로 싣고, 줄마다 두 읽기의 결과 수(어긋난 줄 수)를 함께 적는다. 등급이 갈리면 원판 S-13이다.
- **경로 1 판정기에 이 키 확인을 더하지 않는다.** 이유는 셋이다.
  1. 경로 1의 원본(실행 중 설정 객체)은 줄 필드보다 앞 단계의 같은 값이다. 규칙이 정한 결과("오류 줄")를 그대로 낸다.
  2. 판정기 코드를 바꾸면 R2에 경로 1 변경이 더해진다. 그러면 허용 목록과 검토 범위가 넓어진다.
  3. 두 경로가 서로 다른 원본으로 같은 사실을 보는 것은 원판 9.2의 독립성 취지에 맞는다.
- 결정 필요: **아니오**(사용자 결정 2026-11-13의 코드 변경 최소화와 같은 방향).

## R14-6. 감사 지적의 기록 정리

1. **하네스 G-S 도구 `resume4368_judge`와 rev12 R12-3**: R12-3의 대상은 "커밋 정체성을 대조하는 두 경로의 도구"다. `resume4368_judge`의 하네스 G-S 하위 명령은 커밋을 대조하지 않으므로 R12-3의 `--git-at-start` 필수 대상이 아니다. 하네스의 커밋 대조는 R2 G-S와 본 실행 모두에서 사이드카 `.identity.json`의 `start`·`end` `git.head`를 하나도 빠짐없이 R2와 대조하는 것으로 한다(rev6 R6-C2, 원판 6절 커밋 행). 판정서에는 사이드카 수, 대조한 기록 수, 어긋난 수를 적는다.
2. **rev13 R13-5 "G-S에 H-0 줄 종류(R-0·R-0K·T-3K)가 들어 있다"는 바로잡는다.** 실제 하네스 G-S의 H-0 항목은 R-0 대리 1줄뿐이다. 이 판부터 H-0의 원판 11.2 근거는 다음 둘이다.
   - (a) R2 G-S의 그 R-0 대리 1줄(키 경로 존재 확인)
   - (b) 재실행 H-0 출력 자신의 키 경로 확인. 판정 전에 R-0·R-0K·T-3K 각 파일에서 판정 도구가 읽는 키(rev5 2.2 대조 키, rev11 R11-1 줄 종류 키, K-0 정체성 키)가 모든 줄에 있는지 본다. 값은 출력하지 않는다. 결측이 있으면 그 묶음은 판정하지 않고 멈춘다(원판 S-11).
   - R-0K·T-3K 줄 종류에 대한 G-S 행이 따로 없다는 사실은 판정서에 공개한다.
3. **경로 2 `p2_t3k` `--git-at-start`**: 이 도구에서 이 인자는 선택 인자로 구현되어 있어 R12-3("필수")과 다르다. 이번 판에서는 코드를 고치지 않는다(다음 개정으로 미룸). 운용 규칙은 다음과 같다.
   - H-0 경로 2 판정에는 항상 `--git-at-start R2`를 준다. 판정서에 준 값과 명령 줄을 적는다.
   - 이 인자 없이 낸 경로 2 출력은 R12-3의 입력 오류로 보고 판정에 쓰지 않는다.
- 결정 필요: **아니오**.

## R14-7. 봉인 확인

- 도구의 봉인 확인 목록(경로 1·경로 2 모두)은 rev12까지 그대로 둔다(rev13 R13-7). `f7c6d55`·`ed7942b`도 봉인 목록을 바꾸지 않는다.
- rev13과 rev14의 sha256은 `tools/verif/seal_check.py`로 확인한다. 시점은 묶음마다 실행 전 감사(원판 A-10)와 판정서 커밋 전이다. 다르거나 `.sha256`이 없으면 원판 8.2 S-1이다.
- 결정 필요: **아니오**.

## R14-9. 결정 표

| 항목 | 권고·정의 | 결정 필요 |
|---|---|---|
| R14-1 A-5 재확인 | R..R2의 `04_scripts` 변경은 `resume_k1_record.py` 1건(A-5 범위 38개 안, R13-2 #7). 기록 전용, 명령 해시 같음(확인 실행 2건). `05_tests`는 범위 밖. P-1·P-2 앵커 유지. 하네스는 dynamics-dev만 | 아니오 |
| R14-2 H-0 재실행 | 첫 출력은 `t3_k1_a861981_superseded/`로 옮겨 기록만, 두 판정 파일도 기록만. R2에서 같은 러너·조건으로 처음부터. 재실행 결과로 판정 | 결정됨: 사용자 결정 2026-11-13(B는 기록 결함, 러너 수정 + H-0 재실행) |
| R14-3 R2·`git_at_start` | 모든 묶음 R2. S2(부모 `75c5f75`, rev14 세 파일 + `.gitattributes` 3줄) → `ed7942b` `--no-ff` → `f7c6d55` `--no-ff` = R2. `03_src`·`02_params` diff 0, `04_scripts` 1파일, `05_tests` 1파일, path2 세 파일, blob sha 고정 | 결정됨: 사용자 결정 2026-11-13(A는 도구만 수정, 러너 수정, R2) |
| R14-4 순서·G-S | 봉인 → 첫 출력 이동 → S2·병합 = R2 → R2에서 G-S 전체 → H-0 재실행·판정 → 본 묶음. R12-6은 Y = R2, 앞 커밋 G-S는 기록만 | 결정됨: 사용자 결정 2026-11-13(R2에서 G-S 전체) |
| R14-5 `enable` 두 읽기 | 경로 1 = 러너 실행 중 검사·`error` 줄, 경로 2 = 줄 필드. 판정서에 공개. 경로 1 판정기에 키 확인을 더하지 않음 | 아니오 |
| R14-6 감사 지적 | `resume4368_judge`는 R12-3 대상 아님, 하네스 커밋 대조는 사이드카 head 전수. R13-5의 H-0 줄 종류 문장 정정(R-0 대리 1줄 + 재실행 출력 키 경로 확인). `p2_t3k --git-at-start`는 운용상 항상, 코드 수정은 다음 개정 | 아니오 |
| R14-7 봉인 확인 | 도구 목록 rev12까지, rev13·rev14는 `seal_check.py` | 아니오 |

### 결과 전 사용자 결정 기록

| 날짜 | # | 결정 | 반영 |
|---|---|---|---|
| 2026-11-13 | H-0 S-13 (B) | 사용자 결정 2026-11-13: B(`enable` 키 없음)는 기록 결함으로 본다. 러너가 이 값을 기록하도록 고치고(`ed7942b`) H-0을 다시 실행한다 | R14-1, R14-2, R14-5 |
| 2026-11-13 | H-0 S-13 (A) | 사용자 결정 2026-11-13: A(dg3 줄을 D-1 줄로 셈)는 경로 2 도구만 고친다(`f7c6d55`, 결정 19, rev5 2.5) | R14-3 (마) |
| 2026-11-13 | R2·G-S | 사용자 결정 2026-11-13: 두 수정을 담은 새 커밋 R2에서 G-S 전체(하네스·Chrono·두 경로)를 다시 돈다 | R14-3, R14-4 |

## 봉인 때 바꿀 머리 줄 (메인 세션)

1. 파일 이름: `v5_resume_4368_rules_rev14_seal_candidate_draft.md` → `v5_resume_4368_rules_rev14.md`(같은 폴더). 초안 파일은 지우지 않고 그대로 둔다.
2. 1행을 다음으로 바꾼다:
   `# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev14 (H-0 S-13 뒤: 러너 기록 `enable` 추가와 경로 2 dg3 줄 수정을 담은 R2, H-0 재실행, 모든 묶음 `git_at_start` = R2, R2에서 G-S 전체, 본 묶음 결과 전, 봉인)`
3. 3행(첫 글머리 "상태")을 다음으로 바꾼다:
   `- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev14.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev14_seal_candidate_draft.md`와 1·3·5·9행만 다르다.`
4. 5행("시점")에서 `SEAL_TIME`(예: 2026-11-13 10:00:00 +09:00)과 `SEAL_COMMIT`(봉인 파일을 넣는 커밋 S2의 부모 = R `75c5f75`, R14-3 2)을 값으로 바꾼다. 이 두 이름 말고는 5행을 바꾸지 않는다.
5. 9행("봉인 준비판이다")을 다음으로 바꾼다:
   `- **봉인본이다.** 사용자 결정이 필요한 새 항목은 없었고, 사용자 결정(2026-11-13: B는 기록 결함으로 보고 러너 수정 + H-0 재실행, A는 도구만 수정, R2에서 G-S 전체)은 R14-1~R14-7과 R14-9 결정 표에 반영했다.`
6. 바꾼 뒤 sha256을 계산해 `v5_resume_4368_rules_rev14.sha256`에 `<sha256>  v5_resume_4368_rules_rev14.md  sealed <SEAL_TIME 값> (436.8 rev14: after the H-0 S-13 at a861981 (path 1 pass, path 2 H-T3-3) on top of rev13; cause A path 2 p2_t3k counted the dg3 rows of the D-1 file as D-1 rows (tool fix only, f7c6d55, rev5 2.5), cause B the harness lines lacked resume_k1.slope_clearance_margin.settings.enable that rev5 2.2 compares (record defect, runner fix ed7942b in resume_k1_record.py, record only after commands_sha256, two check runs with equal hashes); A-5 recheck R..R2: 04_scripts change = resume_k1_record.py only (inside the 38, R13-2 #7), 05_tests outside, P-1 / P-2 anchors kept, harness in dynamics-dev only; first H-0 output moved untracked to t3_k1_a861981_superseded/ and both judgements kept as record only, H-0 rerun from scratch at R2 with the same runner (12 workers, 0x00FF5500, identity start / end), judged by the rerun whatever it is; every bundle git_at_start = R2 = --no-ff merges of z4371-r4c30 and z4371-p2dg3 on the seal commit whose parent is R 75c5f75, 03_src / 02_params diff 0, fixed blobs resume_k1_record.py e5414bf3, test_resume4368.py 8b1e4de1, p2_t3k.py 44141c9f, test_p2_t3k.py e6b5e11a, README.md c6ed7e13 (LF blobs; CRLF working copies differ), 3 .gitattributes lines; order seal -> move first output -> R2 -> full G-S at R2 -> H-0 rerun and judgement -> main bundles, R12-6 with Y = R2, earlier G-S record only; rev5 2.2 enable read by the runner config check and error lines (path 1) vs the line field (path 2) disclosed, no path 1 judge change; resume4368_judge harness G-S not an R12-3 commit tool, harness commit check by every sidecar head; R13-5 H-0 line kinds corrected to one R-0 proxy G-S line plus a key-path check of the rerun outputs; p2_t3k --git-at-start always given, code fix deferred; tool seal lists stay at rev12, rev13 / rev14 by seal_check.py; user decisions 2026-11-13; thresholds and grades unchanged)` 한 줄로 쓴다.
7. `.gitattributes`에 다음 3줄을 더한다(지우는 줄 없음, R14-3 3 (나)):
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev14.md -text`
   - `…/v5_resume_4368_rules_rev14.sha256 -text`
   - `…/v5_resume_4368_rules_rev14_seal_candidate_draft.md -text`
8. `tools/verif/seal_check.py`와 `tools/verif/placeholder_scan.py`로 확인한다. 봉인본의 5행 자리 값(`SEAL_TIME`·`SEAL_COMMIT`)이 값으로 바뀌었는지 본다. 이 절의 안내 문구에는 두 이름이 남는다(rev12·rev13과 같은 선례). 그 뒤 봉인 커밋 S2를 만든다(부모 `75c5f75`, R14-4 순서 3). 봉인 뒤 이 문서를 고치지 않는다. 고칠 것이 생기면 `v5_resume_4368_rules_rev15.md`로 새로 봉인한다.
