# 436.8 R4 하네스 판정 실행 전 감사 (verif-protocol-auditor, 2026-11-16)

## 감사 요약
- 시점: 실행 전(M4 병합 전, R4 = `z4373-r4` `2ceafef123f5f65e462c418c835d15588596aac8`, worktree `C:\workspace\z4373-r4` clean; master `da339b7`).
- 기준 문서: 원판~rev25 26판(rev25 `c0b778fd`, `C:\workspace\z4373-s4\06_analysis\02_control\verif_matrix\`), R4 공통 블록 `scratchpad\r4-handoff\r4_common_block_draft.md`(파일 `d4788a60`, 표지 사이 `e451f067`), 보충 1 `8736f68d`·보충 2 `a9a15a13`(`supplement_r4_1.md` `b5f4df93`), 보충 3 `5360becf`(`supplement_r4_2.md` `400fc632`), 사용자 결정 113~126(메모리 `gs-4368-decisions-20261113.md` `84087f77`), 기준 집합 `scratchpad\main\r4_baseline_sets.json` `a5627304`.
- 판정: 차단 2 / 권고 7 / 참고 12. 차단 2건(경로 2 harness 목록 파일 규칙 부재, 계열 𝓕 R-1~R-4 단계 누락)을 정하기 전에는 M4 병합 뒤 판정 실행을 시작하지 않는 것이 맞다. 두 건 모두 "실행 뒤 고치기"가 RD-6(상대 출력을 본 뒤 도구·출력 수정 금지)에 막혀 되돌릴 길이 없다.

## 발견 사항 (심각도순)

### [차단][I·R·E] B-1 경로 2 `p2_4368.py harness`의 목록 파일(manifest)을 R4에서 어떻게 만들지 정해지지 않았다. 앞 판 방식을 다시 쓰면 RD-7 3 줄 식별이 깨진다
- 근거
  - 도구는 파일마다 `kind` 하나만 받는다. `kind` "auto"(줄마다 `job.setting`으로 판별)는 `--gs`일 때만 허용되고, 그 밖에는 `ValueError`다: `path2/p2_4368.py:1010-1017`. 한 파일에 태그가 섞이면 줄마다 S-2다(`:1089-1090`).
  - 결과 파일 열은 manifest에 적힌 입력 경로 그대로(`rel_posix(path)`, `:1036`, `:901-906`), 위치는 그 입력 파일의 물리 줄·목록 번호다(`:784-806`).
  - 키·설정 열은 파일 이름으로 고른다: `h1_d1.jsonl`, `h5_u9_v0.jsonl`·`h9_stage1.jsonl`·`h10_reuse_rerun.jsonl`, r79 8개 이름, `grid_*`, `u3_`/`u6_` 접두(`:909-933`). 이름이 다르거나(나눈 파일 `h1_d1.VB.jsonl`), u3 C·D를 `r79_json` 꼴로 주면 키·설정은 `null`이다.
  - H-4 IND·IND_LAS는 파일당 242줄을 요구한다(`HARNESS_FILE_COUNTS`, `:275`). 원 파일은 main 16 + wide 226으로 나뉘어 있어, 이 검사를 통과하려면 두 원 파일을 합친 파일이 필요하다.
  - 태그가 섞인 원 결과 파일(식별 필드만 셈): `h1_d1.jsonl` VB 434·V0 434, `h10_reuse_rerun.jsonl` VB 138·LS1~LS4 각 72·V0 10·V3 4, `u6_b5_main_VB.json`·`u6_b5_wide_VB.json` C2·ABL·IND 섞임.
  - 첫 판정(`judge_b9f5707\harness_path2\p2h_manifest_harness.json`·`_b.json`)은 H-1·H-10·H-4를 `judge_b9f5707\harness_path2\inputs\`로 나누고 합친 파일로 넣었고, u3 C·D는 A판에서 `r79_json`, B판에서 나눈 `*.records.json`이었다.
  - RD-7 3은 줄 식별을 "원판 4.3·RV1-3.3의 최종 출력 파일(저장소 루트 상대) + 그 파일의 물리 줄·목록 번호"로 정한다(블록 68~69행). 경로 1 `r4-lists`는 R2 원 파일을 바로 읽는다(`resume4368_judge.py:3080`, `:3195`).
  - S6-base 67줄 가운데 4줄이 `u3_C_V0.json`(2)·`u3_C_VB.json`(1)·`u3_D_V0.json`(1)의 원 파일 `results[i]` 위치다(기준 집합 파일 식별 필드만 셈).
  - manifest에 없는 묶음은 `bundles`에 생기지 않아 S-15(`:1232-1237`)·S-8(`:1241`) 검사도 하지 않는다(빈 목록이 조용히 나옴).
- 실패 시나리오
  - 첫 판 manifest를 다시 쓰면 H-3 멈춤 S-6 4줄이 A판에서는 키·설정 `null`, B판에서는 결과 파일·위치가 다르다. RD-7 2 대조에서 S-13이 나고 JD-3에서 멈춘다. 위반이 늘거나 준 것이 아닌데도 멈춘다.
  - H-1·H-4·H-10의 목록(멈춤 S-6, RD-8 `lines`, 키 원본 `differ_keys`)이 비어 있지 않으면 같은 이유로 S-13이 난다.
  - manifest에서 묶음 하나를 빠뜨리면 그 묶음의 목록·RD-9가 비어도 멈추지 않는다.
  - 결과를 본 뒤 manifest를 고쳐 다시 돌리는 것은 RD-6에 걸린다.
- 권장 조치(실행 전, 결정은 사용자)
  1. 태그가 하나인 원 파일은 manifest에 원 경로(저장소 루트 상대)로 넣는다. u3 22개(C·D 포함, 모두 `u3_json`), r79 8개, 격자 4개와 V0 표본, `h5_u9_v0.jsonl`, `h9_stage1.jsonl`이 여기에 든다.
  2. 태그가 섞인 세 원본(`h1_d1`, `h10_reuse_rerun`, `u6_b5` main·wide)은 다음 둘 가운데 하나로 정한다.
     - (a) 2-dyn 작성자(dynamics-expert)가 `--gs` 없이도 줄마다 kind를 읽는 꼴(설정·controller별 기대 줄 수 포함)을 더하고, 원 파일·물리 줄로 낸다. 새 커밋이므로 R4를 다시 만들고 다시 감사한다.
     - (b) 나눈 파일을 쓰되, 나눈 파일의 위치를 원 파일 위치로 바꾸는 대응표를 결과 전에 sha로 고정한다. 나누는 스크립트의 sha와 함께 JD-6에 적는다. 키·설정 `null`은 대응표로 메울 수 없으므로, 이 세 묶음의 목록 대조 규칙도 결과 전에 문장으로 정해야 한다.
  3. manifest에 묶음 집합(H-1, H-3~H-10, H-9-V0-sample)과 파일별 기대 줄 수(`expect_lines`)를 넣는다. 메인이 실행 전에 파일 수와 줄 수를 대조한다.
  4. `key_source`·`key_source_override`는 rev1 RV1-3.2 키 원본(P2-12, 지시문 1054~1057행)대로 채운다. H-8 VB 잡음만 `key_source_override` = `v5/dg3/dg3_v4_on.json`이다.
  5. manifest 파일과 그 sha를 판정 전 감사 대상(MD-2)에 더한다.

### [차단][E·R] B-2 계열 𝓕 R-1~R-4(rev3 R3-E2, rev4 R4-B5)를 내는 단계가 두 경로 실행 계획 모두에 없다
- 근거
  - rev3:297·301은 격자 VB 판정에서 계열 𝓕 두 관문만의 통과→실패가 있으면 64실행을 R-1~R-4로 판정한다고 정한다. 통과하면 그 12행을 두 관문에 대해 H-10 계산에서 뺀다.
  - 이번에는 촉발돼 64실행을 돌렸다: `run_b9f5707\family_f\run_family_f.ps1`(11-14 23:57), `logs\h9_family_F_collect.done`(11-15 00:30), 결과 `resume_k1\h9_family_F.jsonl`.
  - RD-7 1은 family run을 "family 판정 R-1~R-4에만 쓰고, 그 입력과 셈은 앞 판 그대로"라고 적는다.
  - 경로 1: 초안 `run_judgement_path1_draft.ps1`에는 `family-f-trigger`(140행)만 있고 `family-f --lines`가 없다. README_judges_4368.md:171의 단계 목록도 같다. 첫 판정 출력에도 `family_f_trigger.json`만 있다. 하위 명령 자체는 있다(`resume4368_judge.py` `family-f`, 4251~4253행).
  - 경로 2: `p2v5c_grid.py`는 `--family-f`가 없으면 계열 𝓕 판정 불가(`p2v5c_grid.py:341-342`)이고, 실패면 H-10 멈춤이다(`:347`). 첫 판정 argv(`p2h_v5c_grid.json`)에는 `--family-f`가 없었고, 2-terra README 실행 예(130행)에서도 선택 인자다.
- 실패 시나리오: 경로 1은 R-1~R-4를 내지 않는다(12행 제외를 판정서가 적용할 근거가 없다). 경로 2는 판정 불가를 낸다. 그러면 H-9·H-10 등급·항목이 두 경로에서 갈려 S-13이 나거나, 규칙이 정한 제외 없이 등급이 정해진다.
- 권장 조치
  - 경로 1 실행 스크립트에 `family-f --lines 06_analysis/03_hydraulic/coupled/v5/resume_k1/h9_family_F.jsonl --out <Out>/family_f.json`을 넣는다.
  - 경로 2 `grid`에 `--family-f <repo>\06_analysis\03_hydraulic\coupled\v5\resume_k1\h9_family_F.jsonl`을 넣는다.
  - 첫 판정이 R-1~R-4를 내지 않았다는 사실은 판정서에 공개한다(확인 필요 Q2).

### [권고][E] A-1 기준 집합(JP-base·S6-base)·G-5 5키·G-6 3키·RD-8 표지와 비교하는 단계가 아직 어디에도 없다. 열 이름도 경로마다 다르다
- 근거
  - 이 비교는 설계상 메인 몫이다(블록 JD-1·JD-2·JD-3·JD-7·JD-8, MD-3). 두 경로 실행 스크립트에는 이 비교가 없다.
  - 열 이름: 경로 1 `r4-lists`는 `result_file`·`location`(`resume4368_judge.py:3080`), 경로 2 harness 멈춤 S-6은 `result_file`·`position`(`p2_4368.py:1174`), 경로 2 `path2_v5c` J-P3·J11 목록은 `file`·`position`(`path2_v5c/README.md:65-66`), 기준 집합 파일은 `file`·`location`이다(행 키 `bundle, file, location, info[, leg]`).
- 실패 시나리오: 이름 그대로 비교하면 모든 줄이 한쪽에만 있는 것으로 나와 멈춘다. 결과를 본 뒤 비교 규칙을 정하면 사후 결정이 된다.
- 권장 조치(메인): 결과 전에 비교 스크립트를 scratchpad에 쓰고 sha를 고정한다. 담을 내용은 다음과 같다.
  - 열 이름 대응
  - RD-5 허용 오차
  - JD-1 (묶음, 파일, 위치, 다리) = JP-base
  - JD-3 S-6을 (묶음, 파일, 위치)로 줄인 집합 = S6-base. 빈 목록이면 멈춘다
  - JD-2 G-5 키 집합 = 5키
  - JD-7 G-6 키 집합 = 3키
  - JD-8 묶음별 표지 유무가 두 경로에서 같은지
  - RD-11 행 항목
  - 이 비교 출력의 sha도 판정서에 싣는다.

### [권고][I] A-2 경로 2의 RD-1 5·RD-1 4를 실행 스크립트 단에서 해야 한다
- 근거
  - `p2_d1.py`(H-1·H-2)는 `--expect-head`가 없다(인자 `--repo`·`--out`·`--h1`뿐).
  - `p2_4368.py`의 HEAD 확인은 `harness`·`anchors`·`jp`만 한다(`R4_CMDS`, `p2_4368.py:167`, `:2947`).
  - 경로 1 `head-check`는 경로 1 허용 목록 12개만 대조한다(초안 30~43·69행, README_judges_4368.md:167 "경로 2 파일의 RD-1 4 blob 대조는 메인 세션이 git으로 따로 한다").
- 권장 조치(메인 ps1 맨 앞)
  - `git rev-parse HEAD` = M4 40자리인지 본다. 아니면 S-12로 멈춘다.
  - (라) 15개 파일마다 `git show <M4>:<f>`·`git show <R4>:<f>` raw sha가 같은지 본다(A-7). 아니면 S-11로 멈춘다.
  - `git diff --name-only b9f5707..<M4> -- 03_src 02_params`가 비어 있는지 본다.

### [권고][I] A-3 HEAD 확인에 추적 파일 dirty 검사가 없다(두 경로)
- 근거
  - `resume4368_judge.py:4155-4183` `head_check`는 `rev-parse HEAD`만 보고 `git status`를 보지 않는다. `p2_4368.head_check`도 HEAD 대조뿐이다(`:566-`).
  - `--r4`에 `--files`를 비워 주면 `all([])`이 참이라 blob 대조를 통과한다(`:4180`). 초안은 12개를 주므로 지금은 잠복이다.
- 실패 시나리오: M4 checkout에 추적 파일 수정이 남아 있어도 판정 도구가 그 작업본으로 돈다.
- 권장 조치(메인): 두 ps1 시작과 끝에서 `git status --porcelain --untracked-files=no`가 빈 출력인지 본다. 아니면 멈춘다. 끝 결과는 기록에 남긴다. head-check에는 `--files` 개수 기대값(12)을 메인이 확인한다.

### [권고][E] A-4 경로 1 초안의 조용한 건너뜀과 rc 처리
- 근거
  - `-Only`를 주면 `head_check`가 목록에 없는 한 실행되지 않고, 실패해도 `throw`하지 않는다(초안 49·71행). 부분 재실행이 HEAD 관문 없이 돈다.
  - `sidecars`는 보존 사본이 없으면 rc 줄 없이 건너뛴다(83~85행). `sidecars_b9f5707.py`는 `*.identity.json`이 0개여도 `problems` 0으로 종료 0이다(빈 집합 통과).
  - 그 밖 단계의 rc는 `rc.tsv`에만 남고 관문이 아니다.
  - `$U3Files`·`$U6Files` 글롭의 개수(22·4)를 확인하지 않는다(63~64행).
- 권장 조치(메인)
  - `-Only` 실행에도 `head_check`를 먼저 강제한다.
  - 사본이 없으면 rc 2로 기록한다.
  - `sidecars.json`의 `files` 수를 첫 판정 수와 대조한다.
  - 판정 전에 `rc.tsv`의 단계별 기대 rc 표를 만든다(예: `r4-lists`는 표지가 있으면 1). 결과 전에 고정한다.
  - 글롭 개수를 대조한다.

### [권고][공개] A-5 JD-6 공개 목록에 들어가지 않은 항목
- 근거: 블록 JD-6 표(109~140행)는 결정 114~121 몫까지다.
- 판정서 공개 표에 더할 것
  1. 결정 122: 멈춤 S-6 목록 대상 묶음을 닫음, J-P3 목록에서 H-1·H-3·H-4를 뺌, RD-4 이름 구분.
  2. 결정 123: 출처를 본 뒤 고른 것이다. H-4 41줄을 뺐고, H-3 4줄을 경로 1 B판에서 넣었다. MD-3 5가 이 선택을 JD-6에 공개하라고 정한다. 같은 결정에 따라 시나리오 ① twin FL과 위반 다리 RR의 구분도 공개한다.
  3. 결정 125: `sidecars` 보존 사본(`0962f639`)은 R4 blob 밖이다. rc `.done` 0개·2개 이상·`exit=` 없음은 `기록 불완전`이다(control-expert가 더함).
  4. 보충의 "JD-6에 더할 줄": `supplement_r4_1.md:162-172`의 8줄, `supplement_r4_2.md:98-104`의 3줄.
  5. 결정 113: rev26 후보, 새 판정서 문서.
  6. R4 작성자들이 구조 확인 중 함께 본 결과 값(아래 출처).
     - `path2/README.md:759`: `d1.j_p3` 값, 재접촉 기록 수 VB 5·V0 8·C 0, `fallback_legs` 조합별 수, `late` 길이별 수.
     - `path2/README.md:782`: C9on 끝 파일 `decisions` 길이 0.
     - `README_judges_4368.md:198`: H-11 8키 양쪽 건수.
  7. 경로 1 `x16-records`가 읽는 Chrono 판정 모듈(`chrono_bundle_grade_4368.py`)은 M4 blob이 R4 blob과 다르다(`25effee`, `TOOL_VERSION` 문자열만 바뀜).
  8. `p2_d1.py`는 도구 단 HEAD 확인이 없고, 실행 스크립트 단에서 확인한다(A-2).
  9. B-1·B-2를 정한 내용.

### [권고][T] A-6 기준 집합 sha를 판정서 초안·JD-6 줄에 아직 적지 않았다
- 근거
  - MD-3 6은 "그 sha256을 R4 판정 출력이 나오기 전에 판정서 초안과 JD-6 공개 줄에 적는다"고 정한다.
  - 지금 sha는 `r4_baseline_sets.sha256`(고정 11:36:07, `a5627304…`)에만 있다.
  - scratchpad에서 하네스 판정서 초안 파일을 찾지 못했다.
- 권장 조치: M4 병합 전에 판정서 초안(또는 scratchpad 기록 파일)에 sha, 뽑은 사람(python-expert, 메인 위임), 시각, 출처 87개 sha, 뽑기 스크립트 sha를 시각과 함께 적는다.

### [권고][S] A-7 R4 blob 표의 "LF 바이트" 정의가 CRLF 저장 파일 3개에서 갈린다
- 근거
  - `path2_v5c/p2v5c_common.py`·`p2v5c_grid.py`·`p2v5c_stage1.py`는 `-text`이고 blob 자체가 CRLF다(R3f부터 그랬다). raw와 LF 정규화 sha가 다르다.

    | 파일 | raw | LF 정규화 |
    |---|---|---|
    | `p2v5c_common.py` | `8785db56` | `827e0fdb` |
    | `p2v5c_grid.py` | `863cbe83` | `c25af90f` |
    | `p2v5c_stage1.py` | `67f3eaf6` | `77ad24e9` |

  - 2-terra README 표와 `merge` 단계의 도구 sha 대조는 raw다. 경로 1 `head_check`는 `lf_normalised_sha256`다(`resume4368_judge.py:4172`).
- 실패 시나리오: 메인이 LF로 바꿔 표를 만들면 README 값과 달라 보여 S-11로 잘못 읽는다.
- 권장 조치: R4 blob 표는 `git show R4:<파일>` raw 바이트 sha(작업본 = blob)로 적는다. 필요하면 LF 열을 따로 둔다. 아래 표가 이번 감사가 본 값이다.

## 규칙↔도구 대조표 (R축)

| 규칙 | 확인 | 결과 |
|---|---|---|
| RD-1 2 `b9f5707..R4 -- 03_src 02_params` 빈 diff | `git diff --name-only` | 비어 있음 |
| RD-1 2 R3f..R4 변경 26개가 허용 목록 (다)·(라) 안 | name-status 대조(rev16:324-325) | 26개 모두 안. (가)·(나)·(마), `.gitattributes`, `00_docs`, 규칙 파일 변경 0 |
| RD-1 2 Chrono 판정 도구·행 정의·manifest R3f..R4 diff 0 | `04_scripts/02_chrono`, `path2_chrono/`, `chrono_rows_manifest.json` | 0 |
| rev16:319 + rev18:39 `b9f5707..R4 -- 04_scripts` 목록 | 9개(chrono 4 + coupled 5) | 허용 10개 안 |
| RD-1 7 `00_docs`·판정서·감사 기록 미수정 | R3f..R4 | 미수정 |
| M4 병합 충돌 가능성 | master `8a0c843..da339b7` 변경 파일과 R4 변경 파일 교집합 | 교집합 0. M4의 (다)·(라) blob = R4 blob 예상 |
| RD-2 26판 값 | 블록 표 = 파일 raw sha = `.sha256` 첫 토큰 = 작업본, LF·BOM 없음 | 26/26 일치 |
| RD-2 두 경로 봉인 목록 | `judge4368_common.py` `SEALED_RULES`, `resume4368_judge.py` `SEALED_REVISIONS`, `p2_4368.py` `R4_SEALS_EXTRA`(+원판~rev12), `p2v5c_common.py` `RD2_SEALS` | 네 목록 모두 26/26, 26판 밖 값 0 |
| `P2_CORE_SHA` `dd3f266e…` / `P2_V5J_SHA` `b815771d…` | R4 blob sha | 둘 다 같음 |
| 블록 sha | 세 넘김 파일 표지 사이 | 셋 다 `e451f067db97…`. 세 README(경로 1 README_judges:3·78, path2/README:638, path2_v5c/README:4·58)에 기록 |
| 보충 구간 sha | `supplement_r4_1/2.md`와 경로별 사본 | 보충 1 `8736f68d`, 보충 2 `a9a15a13`, 보충 3 `5360becf`. 모든 사본에서 같고 README 기록과 같음 |
| 넘김 파일 sha(README 기록) | `369fb3cd`, `54b1305e`, `bafbdd52`, `c09aa889`, `f3651bf5`, `62721996` | 모두 같음 |
| RD-1 5 HEAD 확인 | 경로 1 `head-check --expect`, 경로 2 `--expect-head` | 경로 1·경로 2 harness·anchors·jp·u3·v5j u9·x16·v5c는 있음. `p2_d1.py`·`seal`은 없음(A-2) |
| RD-7 3 줄 식별 | 경로 1 원 파일 + 물리 줄 / 경로 2 harness = manifest 입력 파일 | 경로 2는 manifest에 달림(B-1) |
| RD-9 S-8 | 경로 1 `r4-lists`, 경로 2 harness(manifest에 있는 묶음만) + v5c merge | manifest 누락 시 공백(B-1) |
| rev3 R3-E2 R-1~R-4 | 경로 1 `family-f` / 경로 2 `grid --family-f` | 두 실행 계획에 없음(B-2) |

## R4 blob 표 (2ceafef, `git show` raw 바이트 sha256; 판정 전 감사 대조용)

| 파일 | sha256 |
|---|---|
| 04_scripts/04_hydraulic/coupled/README_judges_4368.md | e6db5d2bb1200610f369e04920de2dd6e0ef50623231d82b919af0bcaf0b096b |
| 04_scripts/04_hydraulic/coupled/h6_judge_4368.py | e9ae3ed9866dd8cc91ba8db275985544c1ab489bb297f9d672d3f8b7a224c31e |
| 04_scripts/04_hydraulic/coupled/judge4368_common.py | 274b0ddbe157fd6e34b619c61d55193d89728909a745f814577ef49af39bb4b4 |
| 04_scripts/04_hydraulic/coupled/judge_stage1_4368.py | 5d69e01335b2bd73397e4679423661046a53761cb646b91679834e6b0ae2d4ee |
| 04_scripts/04_hydraulic/coupled/u3_judge_4368.py | b46cfa7cc80211905c1c83c9bce5e8b16c2d567e2cc267b08c68d3854766096e |
| 05_tests/unit/test_judges_4368.py | d46ed1568225fc822588ee73c410b82068e9daed2ba7c793efef2168ea912703 |
| 05_tests/unit/test_judges_4368_h6_h8.py | ea81a4c6bc526ac8fec9b9b38516e58df89e37916a7f41dbea32cefd7e98b259 |
| 05_tests/unit/test_resume4368.py | b8851f7d80a8a185a577dd66f1a3a991511ce0fe60129bc64ee175fd37ac0498 |
| 05_tests/unit/test_resume4368_rev1.py | aaabe890a0317460cda85ead807e8e0d89936987776ba03dc9177c696b09c19e |
| 05_tests/unit/test_resume4368_rev16.py | 761f3d110da9958453faf35f71e147511e363465ce7509047d4798d3c4f1acc2 |
| 06_analysis/02_control/verif_matrix/scripts/resume4368_judge.py | d9216a9ac2def9722d718a159e263dc98151455dc1ce8da5479f80824aeda8b2 |
| .../v5_resume_4368/path2/README.md | 3334505232a0c9835979a7a45bae75375e1149ea67ed21f7d20944b668a9ff49 |
| .../path2/p2_4368.py | dd3f266ee34bb2b75f8ac66b6995170ca067a65b3372df03f42f6c6938d7c9cb |
| .../path2/p2_u3.py | 7eb119223dfbb5236ee43213843edb1ae4e2ea1e618b5a33b72ae22660ffaf72 |
| .../path2/p2_v5j.py | b815771dcaee69f5b474a7a6328f7699631d4c69309a973314a0ba3eaf06ecb8 |
| .../path2/p2_x16.py | 80cf8ee92a8c60543000fe586d7cc91ade41e977ec3ac1e631901669bb2b59bc |
| .../path2/test_p2_4368.py | 513cc9cfe799b70d4df6dbbc728de968c80067f48f3b469b1fda88a0018e6f99 |
| .../path2/test_p2_u3.py | 533501dd889e8f263eee8215910d18f451bc0fca576732c8eb452d527a619c23 |
| .../path2/test_p2_v5j.py | 017d432730bc6e52d11fc116cd29692f1af3b38b4d098b53f80edb7a061f9092 |
| .../path2/test_p2_x16.py | 66f6ff73a935613d9305448324eed1b098c98dc16f0c114e8b40c4b3d1e311a8 |
| .../path2_v5c/README.md | bbab63618b5b86342ea36c672d4df948058823062d5117fa3ccdfe0f4522c13c |
| .../path2_v5c/p2v5c_common.py (CRLF blob) | 8785db56da617a705f63449d271a1a3d39ab702e92ff2b9ea4ae124f79eba9a2 |
| .../path2_v5c/p2v5c_grid.py (CRLF blob) | 863cbe8310ad865979e153a72a20daec7045dc2af4167bd25690949ac25607ee |
| .../path2_v5c/p2v5c_noise.py | 7fa4153fe254d0d59d2f4dbb94b543f9235b6b76adea071ee637b16a73a112a1 |
| .../path2_v5c/p2v5c_stage1.py (CRLF blob) | 67f3eaf6758048d0dc0b4030b1331767e6f6618d336ee0b1fb233538e92a56ab |
| .../path2_v5c/test_p2v5c.py | cdd4a48e51f66a75850021e656b975717843134ff6fd8688856cf6bb07b42d35 |

- `h8_noise_judge_4368.py`는 R3f..R4에서 바뀌지 않았다. 경로 1 README 기록 값은 `c037fe9e…`다.
- 경로 1 README 표의 11개와 경로 2 README 표(보충 2판 `path2/`, 보충 3 판 `path2_v5c/`)는 위 값과 같다.

## 메인이 만들 경로 2 ps1에 들어갈 명령 (README와 첫 판정 argv에서 뽑음)

R4 판정 출력 폴더는 `judge_<M4 7자리>\harness_path2\`이고, 경로 1과 같은 7자리를 쓴다. 인터프리터는 `conda run -n dynamics-dev python -I -B`다. 단계마다 stdout 끝 JSON의 `exit`·`out_sha256`을 기록한다.

0. 시작 관문(A-2·A-3): HEAD가 M4인지, 추적 파일이 clean인지, (라) 15개의 M4와 R4 raw blob이 같은지, `b9f5707..M4 -- 03_src 02_params`가 비어 있는지 본다. 하나라도 어긋나면 멈춘다.
1. `path2\p2_4368.py --out <o>\seal.json seal`
2. `path2\p2_4368.py --out <o>\harness.json harness --manifest <o>\manifest.json --expect-head <M4>`(manifest는 B-1에서 정한 규칙대로. manifest 파일과 sha를 먼저 고정)
3. `path2\p2_4368.py --out <o>\anchors.json anchors --h1 <repo>\06_analysis\03_hydraulic\coupled\v5\resume_k1\h1_d1.jsonl --expect-head <M4>`(첫 판정에 있었음)
4. `path2\p2_4368.py --out <o>\jp.json jp --shadow ...\v5\las\shadow_jp_b0.jsonl --batch ...\07_results\S9\batch_V5-JP-VB_20261108_115631 --batch ...\batch_V5-JP-V0_20261108_131212 --expect-head <M4>`(VB 먼저)
5. `path2\p2_d1.py --h1 ...\resume_k1\h1_d1.jsonl --out <o>\d1.json`(HEAD 확인 없음 → 0단계가 대신함)
6. `path2\p2_x16.py --out <o>\g3.json g3 --h11-dir ...\07_results\S9\R4368X_b9f5707_20261115_013947\H-11 --expect-head <M4>`. G-3이 거짓이면 H-3·H-4 판정 결과를 쓰지 않고 멈춘다(rev16:142; `p2_u3`에는 G-3 입력이 없으므로 메인이 처리한다).
7. `path2\p2_u3.py --out <o>\u3.json --u3 V0=<las_k1\u3_*_V0.json>`(11개)`--u3 VB=<…_VB.json>`(11개)`--u6 ALL=<u6_b5_main_VB.json> --u6 ALL=<u6_b5_wide_VB.json> --u6 IND_LAS=<u6_b5_main_VB_IND_LAS.json> --u6 IND_LAS=<u6_b5_wide_VB_IND_LAS.json> --h1 <h1_d1.jsonl> --expect-head <M4>`. 첫 판정 argv가 출력에 남지 않아 정확한 인자는 메인의 첫 실행 기록으로 확인해야 한다.
8. `path2\p2_v5j.py --out <o>\v5j_u9.json u9 --v0 ...\resume_k1\h5_u9_v0.jsonl --vb <…> [--h0-ref …] [--stored-main ...\v5\main.jsonl] [--stored-p3 ...\v5\p3_hash.jsonl] [--t4h-root …] --expect-head <M4>`. 첫 판정 argv가 남지 않았으므로 같은 방식으로 확인한다.
9. `path2\p2_x16.py --out <o>\c16.json c16 --out-root ...\R4368X_b9f5707_20261115_013947 --expect-head <M4>`(정체성·러너 폴더는 기본값)
10. `path2\p2_x16.py --out <o>\rd13_items.json items`
11. `path2_v5c\p2v5c_stage1.py --expect-head <M4> --out <o>\p2v5c_stage1.json stage1 --h9 ...\h9_stage1.jsonl --h10 ...\h10_reuse_rerun.jsonl --overlap-ta ...\h10_overlap_t_a.json`
12. `path2_v5c\p2v5c_grid.py --expect-head <M4> --out <o>\p2v5c_grid.json grid`에 다음 인자를 붙인다: `--vb` 4개, `--v0-stored` 4개(`06_analysis\02_control\touch_phase\acceptance\c4g2_only\grid\<stem>.json`), `--v0-sample` 4개, `--family-f ...\resume_k1\h9_family_F.jsonl`(B-2)
13. `path2_v5c\p2v5c_noise.py --expect-head <M4> --out <o>\p2v5c_noise.json noise --noise-vb … --noise-v0 … --h6 … --seedext-vb … --seedext-v0 … --judge-dir <o>\p2v5c_r79_judge --git-at-start b9f5707d7f3f7a26230b25f4edbc1fec587ca612`
14. `path2_v5c\p2v5c_stage1.py --expect-head <M4> --out <o>\p2v5c_merge.json merge --part <o>\p2v5c_noise.json --part <o>\p2v5c_stage1.json --part <o>\p2v5c_grid.json`(11~13 확정 뒤)
15. 출력 전체 sha256 목록 파일(RD-6, 경로 1 6단계와 같은 꼴)
16. 끝 관문: HEAD·clean 다시 확인
- 첫 판정에 있던 `p2h_k0_sidecars_*`·`p2h_head_tally`·`p2h_t4h_lookup`·`p2h_settle_v2_axis`·`p2h_survey`는 도구 출력이 아니다(`tool` 키 없음). R4에서 다시 낼지, 대체하는 정체성 단계를 둘지 정해야 한다(확인 필요 Q4).
- K-10 대조(`p2_4368.py compare --a --b --map`)는 두 경로 출력과 sha를 모두 확정한 뒤 메인이 돌린다.

## 확인 필요
- Q1 (B-1) 섞인 태그 원본 세 개를 (a) 2-dyn 도구 보완(새 R4 + 재감사)으로 처리할지, (b) 나눈 입력 + 결과 전 대응표·대조 규칙 고정으로 처리할지 정해야 한다. u3 C·D를 `u3_json` 원 파일로 넣는 것은 규칙 문장(RD-7 3)으로 닫히는 적용이다.
- Q2 (B-2) R4 재판정에 계열 𝓕 R-1~R-4를 두 경로 모두 넣는지 정해야 한다. 첫 판정이 넣지 않은 사실은 판정서에 공개한다.
- Q3 경로 2 manifest의 `stored`(7.2 저장 행 해시)와 `key_source`(R16-5 2·RV1-3.2)를 파일별로 무엇으로 줄지 정해야 한다. 첫 판 `stored` 값을 그대로 쓸지도 포함한다. `H-9-V0-sample` 묶음을 R4에도 넣을지 정해야 한다.
- Q4 첫 판정 경로 2의 보조 출력(정체성 sidecar 표, head tally, T4h 찾기, settle_v2 축 표, survey)을 R4에서 어떻게 대신할지 정해야 한다. 경로 1은 `sidecars`(보존 사본)로 정체성 표를 다시 낸다.

## 위임 필요
- dynamics-expert(경로 2-dyn 작성자 몫): Q1을 (a)로 정하면 `p2_4368.py harness`에 원 파일의 줄별 kind 판별(설정·controller별 기대 줄 수)을 넣는다. RD-7 3 결과 파일·위치는 원 파일 기준으로 낸다. 키·설정은 원 파일 이름으로 정한다. 새 커밋 뒤 `p2v5c_common.py` `P2_CORE_SHA`를 다시 고정한다(2-terra 몫). R4를 다시 만들고 다시 감사한다.
- (선택, tools/verif 후보, python-expert): "두 경로 목록 열 이름 대응 + 기준 집합 대조" 검사기. 입력은 두 경로 목록 JSON, 열 대응표, 기준 집합. 출력은 (묶음, 파일, 위치[, 다리]) 차이와 값 열 차이다. 종료 코드는 0 같음 / 1 다름 / 2 입력 오류(빈 목록 포함)다.

## 메인 세션 권고
- M4 병합 전: B-1·B-2 결정 → manifest와 비교 스크립트(A-1)를 sha로 고정 → 판정서 초안에 기준 집합 sha를 적음(A-6) → 판정 전 감사(MD-2)에서 manifest·비교 스크립트·R4 blob 표(위 표)를 대조.
- R4(또는 M4)에서 두 경로 자체 시험을 메인이 한 번 돌려 통과 수를 판정서에 적는다. 경로 1은 `05_tests/unit/test_judges_4368*.py`·`test_resume4368*.py`, 경로 2는 `path2/test_*.py` 273개와 `path2_v5c/test_p2v5c.py` 45개다(`-p no:cacheprovider --basetemp <scratch>`). 감사자는 실행하지 않았다.

## 참고
- N-1 R4 조건 전부 참이다(대조표). M4 병합은 충돌 없이 될 것으로 보인다.
  - master `8a0c843..da339b7`의 판정서·`judge_*` 462파일·`.gitattributes`·`00_docs` 3개·`chrono_bundle_grade_4368.py`(`TOOL_VERSION` 문자열만)·그 README는 R4 변경 파일과 겹치지 않는다.
  - 그래서 M4의 (다)·(라) blob = R4 blob이 예상된다. `b9f5707..M4 -- 04_scripts`도 같은 9개 그대로다.
- N-2 봉인 26판이 블록·파일·`.sha256`·네 도구 목록에서 모두 같다. `seal_check`는 `seal_missing` 26건을 냈는데, 모두 `_seal_candidate_draft.md`(봉인 대상 아님)다. 규칙 파일 26개는 모두 `-text`이고 `core.autocrlf` true다.
- N-3 `P2_CORE_SHA`·`P2_V5J_SHA`는 R4 blob과 같다. `P2_FALLBACK`(옛 에이전트 worktree)은 `../path2`가 있으면 쓰이지 않고, 쓰여도 sha 대조로 막힌다(`p2v5c_common.py:502-520`).
- N-4 공통 블록 sha가 세 넘김 파일·세 README 기록에서 같다. 보충 구간 sha도 모든 사본에서 같다.
- N-5 두 경로 독립(R3f..R4 추가 줄, 상대 경로 이름 사전 `r4_p1_names.json`·`r4_p2_names.json`, 4자 이상·상수는 단어 경계)
  - 경로 2 쪽에서 경로 1 이름이 1건 걸렸다: `path2_v5c/README.md`의 `family-f`인데, 이것은 경로 2 자기 CLI 인자다(우연 일치).
  - 경로 1 쪽에서 경로 2 이름은 0건이다.
- N-6 시간 순서
  - 블록 11:15, 넘김 파일 11:19:34, 기준 집합 고정 11:36:07은 첫 도구 커밋(`361e559` 11:52:23)보다 앞선다.
  - 보충 1·2(12:07:13)는 `da1e00e`·`815a78a`(12:17)보다, 보충 3(12:46:20, 경로별 사본 12:47:57)은 `2aa0a40`(12:51)·`60fc72e`(12:52)·`e268b26`(12:57)보다 앞선다.
  - R4 판정 출력 폴더는 아직 없다.
  - 11:36 뒤 scratchpad에 생긴 실데이터 판정 출력은 없다(`p2dyn\rd13_items.json`은 정적 항목 목록).
- N-7 `log_errors.py`는 네 폴더 모두 종료 0이지만, 대부분 `errors N` 줄이 없어 공허하다: `run_b9f5707\logs\run_harness` 68/74, `_runners` 12/32, `H-11` 28/28, `H-12` 10/10. 판정서에는 rc·`.done`을 근거로 적는다.
- N-8 인터프리터가 섞여 있다. 판정서 정체성에 적는다.
  - 경로 1: dynamics-dev `python.exe` 직접 실행, `MKL_THREADING_LAYER=TBB`, `*_NUM_THREADS=1`. `x16-records`·`sidecars`·`log_errors`만 python-dev다.
  - 경로 2: `conda run -n dynamics-dev`.
- N-9 `path2/README.md`와 경로 1 시험 5개는 `-text`가 없어 작업본이 CRLF다(index LF). 도구가 sha를 재는 파일이 아니고, 앞 판부터 그랬다.
- N-10 `gate_scan` `all_without_count_guard` 3건은 확인 결과 결함이 아니다.
  - `p2v5c_common.check_rev3`: 상수 목록 23판이다.
  - `p2v5c_stage1.item8_order:416`: `sorted(vals) == [0, .001, .002, .003]` 가드가 있다.
  - `resume4368_judge.soil_event_series_presence`: Chrono G-S이고 R4 범위 밖이다.
- N-11 경로 1 `x16-records`는 Chrono 판정 모듈 두 개를 import한다(`chrono_rows_judge_4368.judge_scm`, `chrono_bundle_grade_4368.p3_items`). RD-1 4 blob 대조 범위 밖이다. M4에서는 `TOOL_VERSION` 문자열만 다르다(A-5의 7).
- N-12 경로 1 `head_check`는 `--expect`가 40자리 hex인지 검사하지 않는다. 자리표시가 남아도 HEAD와 달라 S-12로 멈추므로 안전하다. 다만 `New-Item`이 그보다 먼저 `judge_M4_FULL\harness_path1\logs`를 만든다(초안 21~22행).

## 검사하지 못한 것
- 두 경로 자체 시험 실행(읽기 전용 원칙, 메인 권고).
- `p2_u3.py`·`p2_v5j.py u9`·`p2_d1.py`의 첫 판정 정확한 argv(출력에 argv가 없다).
- 경로 1 `r4-lists`·`x16-records`·`h12`, 경로 2 `c16`·`g3`의 세부 판정 로직(정의 대조). 이번 감사는 실행 계획·정체성·봉인·E 관문 중심이다.
- 결과 값(R2 하네스 판정 값, 첫 판정 출력 내용)은 열지 않았다. 식별 필드(설정·태그 수, 기준 집합의 묶음·파일·위치 꼴, 첫 판정 경로 2 출력의 argv·manifest 입력 목록)만 셌다.

## 실행한 검증
- 인터프리터: python-dev `C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B [-X utf8]`, `MKL_THREADING_LAYER=TBB`. 대상 프로젝트 모듈은 import하지 않았다.
- 도구
  - `seal_check.py --repo C:\workspace\z4373-r4 "06_analysis/02_control/verif_matrix/v5_resume_4368_rules*.md" --code <네 도구>`: 종료 1, `seal_missing` 26 = draft.
  - `gate_scan.py`(p2_x16, p2v5c_stage1, p2v5c_common, resume4368_judge): 종료 1, 후보 3건을 손으로 확인.
  - `log_errors.py` 4폴더: 종료 0.
  - `source_guard.py snapshot/verify`.
- 즉석 스크립트(scratchpad `audit-r4-prerun\`, 보고 전에 지움)
  - `blocksha.py`(블록 sha), `suppsha.py`(보충 구간 sha)
  - `seals26.py`(26판 값 ↔ blob·작업본·`.sha256`·네 도구 목록), `blobtable.py`(R4 blob 표 raw·LF)
  - `kinds.py`(결과 파일별 설정·태그 수), `base_shape.py`(기준 집합 꼴), `argv.py`(첫 판정 경로 2 argv)
  - `leak.py`(두 경로 이름 교차 검사)
- git 조회: `log`, `diff --name-status/--name-only`, `show`, `ls-files --eol`, `check-attr`, `merge-base`, `check-ignore`, `status`.
- 다시 읽은 근거: R4 HEAD `2ceafef`, master `da339b7`, worktree clean을 보고 직전에 다시 확인했다.
- 원본 불변: (source_guard verify report_line은 핸드백 말미에 그대로 붙임; 입력 68개 모두 불변, 디렉터리 목록 동일)
- 사용한 스킬: 없음
