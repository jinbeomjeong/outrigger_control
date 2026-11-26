# v5 재개 검증 436.8 규칙 rev26 — 정오 1 (5단계 실행본 기준과 기록 위치) (control-expert, 2026-11-26)

- **대상(봉인본)**: `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev26.md`
  - sha256 `f6591836a205dd52c698bbb613dbe4d74bfdc4b5a318dcb0d7873e9bb02c3b73`
  - `.sha256` 파일 sha256 `e74aeca93554d65a5e2344142827fa5cafa054153feff7f9d64406233676b80b`
  - 봉인 커밋: master `c77b1dcfce9119106838d307302bf8a48a07bff9`. 부록 두 파일(`rev26_fixed/excl_fields_r5.py` `bee9eee7…`, `rev26_fixed/rev26_excluded_fields_r5.json` `9e1831f5…`)은 그대로다.
- **날짜**: 2026-11-26
- **상태**: 봉인 전 초안이다. 메인이 `v5_resume_4368_rules_rev26_erratum1.sha256`으로 봉인한다.
- **근거 결정**: 사용자 결정 2026-11-26
  1. 경로 1 5단계 실행본의 기준은 M4_retry1이다(153~155행 `$gname`).
  2. `path2/test_rev26_p2.py`는 `$AllowListPath2`에 넣지 않고, sha를 `t26_identity.json`에 적는다.
  3. `t26_identity.json`과 5단계 실행본은 `rev26_run/`에 둔다. master `.gitattributes`에 `rev26_run/** -text`를 더한다.
  4. 두 작성자의 확인 필요 (가)(나)(다)는 이 정오에서 판단한다.
- **근거 자료**
  - `v5_resume_4368/rev26_run/prep_report.md` 3절(ps1_lint 종료 1)과 5절 1~4
  - M4 실행본 `judge_932f1fb/_fixed/run/run_judgement_path1_M4.ps1`(sha `868fa7b712eea4c3071c413f854143c376718ff776902392e3bd4bff7368c915`)
  - M4_retry1 실행본 `…/run_judgement_path1_M4_retry1.ps1`(sha `c93cfc5c883d661c7cb41bf92ad697f1d2a54ca124b0251656683bc17f1a5ef4`). 두 실행본은 21·153·154·155행만 다르다.
  - `v5_resume_4368/rev26_impl/path1_report.md` 5절 1, `path2_report.md` 6절 1·2
- **바꾸지 않는 것**
  - 판정 정의, 문턱, 등급 대조 표
  - 기대 효과 (a)~(h)의 값, 상태 순서, 판정 불가 처리, 5절 실패 처리
  - 1절 범위표, 3절 구현 조건, 부록 A·B
- **T26(`335004a7ad9f5f988e7543dd98d45bf2b96e4294`)은 바꾸지 않는다.** 이 정오 파일은 T26에 넣지 않는다. 두 경로 도구가 읽는 봉인은 rev26 그대로다. 2절 RD-1 4 대체 조건 1의 "바뀐 파일 목록"은 지금의 37개(`git diff --name-only 932f1fb..T26`) 그대로다.
- **요청 밖 추가**(사용자 결정 1~4 밖에서 이 정오가 더한 것)
  - ㉠ 이 정오 파일과 그 `.sha256`에 `-text`를 단다(5절 2).
  - ㉡ 4′에서 두 실행본의 `--tag-mode` 출현 0건을 확인한다. rev26:42 "436.8 재판정은 이 인자를 주지 않는다"를 기계로 확인하는 일이다(4절).
  - ㉢ 판정서 6절에 RD-13 낡은 문구를 기록한다((다), 1절 E1-6).

## 0. 공개
- **결과 보기 전, 5단계 실행 전 정오다.**
  - 판정 도구가 436.8 저장 결과에 돈 횟수는 준비 보고(`prep_report.md` 0절·7절) 기준 0이다. 4′·6단계에서 확인한다.
  - 이 정오의 작성자(control-expert 새 인스턴스)는 다음을 열지 않았다: 436.8 결과 json, 판정서, 판정 후 감사, 부록 B 파일, 블라인드 경로, 두 경로 코드.
- rev26 0절의 공개(원 작성자가 아는 것, 결과 뒤 예외 둘)는 그대로 유효하다.
- M4와 retry1 가운데 무엇을 고를지는 실행본의 갈림길이다. 이 정오는 새 결과를 보고 고르지 않았다. 원 출력의 기준을 retry1로 정한 봉인 문장 rev26:218을 따랐다(아래 E1-1).

## 1. 정오 항목 표
| # | rev26 위치 | 봉인 원문 | 정오 뒤 | 구분 | 근거 |
|---|---|---|---|---|---|
| E1-1 | 2절 "5단계 실행본 — M4 실행본에서 바꾸는 줄(이것뿐)", 경로 1 1~7(:89~98) | 1~7번만 바꾼다 | **8번을 더한다.** 루프 153~155행의 변수 `$grid`를 `$gname`으로 바꾼다. 세 줄은 `run_judgement_path1_M4_retry1.ps1` 153~155행과 바이트가 같아야 한다. "이것뿐"은 1~8번이다. 21행(출력 폴더)은 retry1의 `harness_path1_retry1`을 쓰지 않는다. 4번 `judge_rev26_<T26 앞 7자>/harness_path1` 그대로다 | 실행 설정 | 아래 표 밑 설명 |
| E1-2 | 4′ "실행본"(:145) | "두 5단계 실행본과 M4 실행본의 diff가 2절 '바꾸는 줄'뿐인지, `ps1_lint.py` 종료 0인지" | 3절 표대로 바꾼다. 경로 1의 기준 diff는 M4 대비 1~8번이다. 같은 뜻으로, M4_retry1 대비로는 1~7번만 다르고 153~155행은 바이트가 같다. ps1_lint는 두 실행본 모두 종료 0이어야 한다 | 판정 전 점검 | E1-1 |
| E1-3 | 2절 경로 2 4번(:103), 4′(:145) "`$AllowListPath2` 값이 `t26_identity.json`의 T26 blob과 같은지" | (새 시험 파일을 어떻게 다룰지 정하지 않음) | `$AllowListPath2`는 M4의 15개 파일 그대로이고 값만 T26 blob raw sha256으로 바꾼다. 개수 관문(M4 206행, rev26 실행본 207행 "15 expected")도 그대로다. `path2/test_rev26_p2.py`(T26에 새로 생긴 시험 파일)는 표에 넣지 않는다. 그 T26 blob raw sha256 `3e8166b2132a530d4330f6c150fb594eb0c12f87fbd3e4c2df9ee8cc76ca2877`을 `t26_identity.json`에 적는다 | 기록(정체성) | 사용자 결정 2. 아래 설명 |
| E1-4 | `rev26_fixed/t26_identity.json`이라고 적은 곳: :84, :109, :110(W-i), :143, :145, :194 | `rev26_fixed/t26_identity.json` | `06_analysis/02_control/verif_matrix/v5_resume_4368/rev26_run/t26_identity.json`. 5단계 실행본도 같은 폴더에 둔다: `rev26_run/run_judgement_path1_rev26.ps1`, `rev26_run/run_judgement_path2_rev26.ps1`. 실행 환경 기록 `rev26_run/conda_list_export_{dynamics-dev,python-dev}.txt`도 같은 폴더다. `rev26_fixed/**`는 봉인 사본 폴더라 파일을 더하지 않는다 | 기록 위치 | 사용자 결정 3 |
| E1-5 | 7절 `.gitattributes` 대상(:197~204) | 6줄 | master `.gitattributes`에만 `06_analysis/02_control/verif_matrix/v5_resume_4368/rev26_run/** -text`를 더한다. T26의 `.gitattributes`는 그대로다. 그래서 2절 :68과 4′ :146의 "`git diff 932f1fb..T26 -- .gitattributes` = 7절 6줄 추가뿐" 점검은 바뀌지 않는다 | 기록 보호 | 사용자 결정 3, `prep_report.md` 5절 4 |
| E1-6 | 6절 판정서에 적을 것(:190~194) | — | 다음을 더 적는다. (1) 경로 1 5단계 실행본의 기준이 M4_retry1이고(E1-1) 그 근거가 :218이라는 것. (2) `t26_identity.json`과 실행본의 위치(E1-4). (3) 2절 (가)(나)(다)의 처리와 RD-13 H-4 항목 문구가 R26-3 이전 꼴로 남아 있다는 것 | 기록 | 이 정오 2절 |

**E1-1 설명**
- 봉인 근거 문장은 rev26:218(부록 A 범위)이다. "원 출력: `judge_932f1fb/harness_path1/*.json`과 `harness_path2/*.json`. 같은 이름이 `harness_path1_retry1/`에 있으면 retry1 판을 원 출력으로 쓴다(`head_check.json`, `r4_inputs.json`, `stage1_judge.json`, `stroke_H-9.json`)."
- 결함
  - M4 153행 `foreach ($grid in 'grid_r67_main', …)`는 PowerShell 변수 이름의 대소문자를 구분하지 않는다. 그래서 62행 `$Grid`(격자 4파일 배열)를 덮어쓴다.
  - 덮어쓴 값은 159행 stage1_judge(`--grid` 뒤 `+ $Grid`)와 183행 stroke_H-9(`+ $Grid`)가 읽는다. 루프가 끝난 뒤 `$Grid`는 문자열 `'grid_r69_top'` 하나다.
- retry1은 루프 변수만 `$gname`으로 바꿨다. 그래서 159·183행이 4파일 배열을 받는다. (d)의 원 출력 `stage1_judge.json`·`stroke_H-9.json`이 바로 이 꼴로 나왔다.
- 루프 안의 keyset 단계 이름(`keyset_<격자 이름>`)과 출력 파일 이름은 두 변수 이름에서 같게 펼쳐진다. 그래서 keyset 출력에는 영향이 없다.
- M4 그대로 돌리면 이렇게 된다(추정, 실행하지 않음).
  - 4′ "ps1_lint 종료 0"(:145)과 2절 "이것뿐"(:89)이 함께 성립하지 않는다(`prep_report.md` 3절: `case_variant_overwrite` error 1건).
  - 두 단계가 원 출력과 다른 입력으로 돌아 (d) 불일치가 날 수 있다.

**E1-3 설명(표에 넣지 않아도 되는 이유)**
- 2절 경로 2 4번은 "56~72행 → T26 blob **값**"이라고 적는다. 값만 바꾸는 규정이다. 개수 관문 줄은 바꾸는 줄에 없다.
- 시험 파일은 5단계 실행본이 실행하지 않는다. 두 실행본 모두 pytest 호출이 0건이다(작성자 grep).
- 그 파일 내용은 다음 세 가지가 고정한다.
  - 경로 2 HEAD 관문(rev26 실행본 184행 `Test-CheckoutState`의 HEAD = T26과 187행 추적 변경 0, 413~415행 끝 관문)
  - W-i(worktree `status --porcelain` 비어 있음, :110)
  - RD-1 4 대체 조건 1의 바뀐 파일 목록
- 작성자가 `git cat-file blob 335004a7:…/path2/test_rev26_p2.py`의 sha256으로 위 값을 다시 계산했고, 같았다.

## 2. 확인 필요 (가)(나)(다) 처리
| 항목 | 이 정오에서 | 436.8 재판정 영향 | 근거 |
|---|---|---|---|
| (가) 경로 1 `record-check`의 ABL 한쪽 S-3 잔존(`path1_report.md` 5절 1) | **다루지 않는다. 4′에서 판단.** | 경로 1 `abl_line`(rev16 R16-3, 4.2 기록 확인)은 T26에서 바뀌지 않았다(`path1_report.md` 5절 1). 그래서 436.8 데이터에서는 이 경로의 출력이 원 판정과 같은 코드로 다시 나온다. 다르면 (d) 비교에서 드러난다. 판정 정의를 바꾸지 않는다 | 사실만 적는다. ① R26-3 문장(rev26:41)은 u6 줄 (controller, `v5.controller_tag`) 쌍 검사의 결과를 S-2로 정한다. 1.1 표에는 R16-3 기록 확인을 없애라는 문장이 없다. ② 합성 "ABL 한쪽" 줄에서 경로 1은 r4-inputs S-2와 record-check S-3을 함께 내고, 경로 2는 S-2만 낸다(`path2_report.md` 2.2 "예전 R16-3 S-3을 대신"). 합성 (e) "두 경로 모두 S-2"(rev26:171)를 "S-2가 남"으로 읽을지 "S-2만 남"으로 읽을지는 4′가 판단한다. 4′가 불충족으로 보면 규칙 수정은 새 사용자 결정이다(rev26:151·162와 같은 처리) |
| (나) 경로 2 imua 모드를 "더 받아들임"으로 구현(`path2_report.md` 6절 2) | **다루지 않는다.** 정의 쪽 결정은 TA(A형 규칙) 몫이다. T26 기록에 적을지는 4′에서 판단 | **영향 없음.** ① rev26:42는 모드를 실행 인자로만 고르고(기본 `4368`), 436.8 재판정은 이 인자를 주지 않는다고 정한다. ② 두 5단계 실행본(`rev26_run/run_judgement_path{1,2}_rev26.ps1`)에서 `tag-mode`·`imua`는 0건이다(작성자 grep). ③ 4368 모드에서 경로 2 `tag_matches`는 그대로 같음만 통과시킨다(`path2_report.md` 2.3). "더 받아들임"은 `--tag-mode imua`일 때만 작동한다 | 참고로 경로 1은 imua에서 4.1 문자열 뒤에 `_IMUA`를 붙인 값과 비교한다(`path1_report.md` 2.3). 그러니 imua 모드에서는 두 경로가 다르게 읽는다. A형 J-2 전에 TA 쪽에서 정해야 한다 |
| (다) 경로 2 RD-13 항목 문구에 "하나만 맞으면 S-3"이 남음(`path2_report.md` 6절 1) | **문구를 고치지 않는다. 판정서에 기록만 한다(E1-6).** | 영향 없음. 이 문구는 판정값이 아니라 설명 문자열이다. `rd13_items.json`에서 원 출력과 같은 문자열이므로 (d) 비교에서 같게 나온다. 고치면 오히려 (d) 불일치가 난다 | 실제 동작(S-2)과 문구(S-3)가 어긋난다는 사실을 판정서 덧붙임에 적는다 |

- 두 경로 범위 대조: 이 정오는 판정 정의(판정 집합, 0건·결측 처리, 상태 이름)를 바꾸지 않는다. 봉인본 1절(범위)·3절(작성자 조건)과 대조한 결과, 경로 2 넘김에 더할 [정의] 문장은 없다. 두 경로 구현은 끝났고, 이 정오는 실행본·기록만 다룬다.

## 3. 4′ 점검 변경(rev26 4′ :142~162에 대한 정오)
| 4′ 항목 | 봉인 원문 | 정오 뒤 |
|---|---|---|
| 첫 줄(:143) | "`t26_identity.json`과 고정 파일 sha" | `rev26_run/t26_identity.json`과 고정 파일 sha |
| 실행본 diff(:145) | M4 대비 diff = 2절 "바꾸는 줄"뿐 | 경로 1: M4 대비 다른 줄 = 13·14·21·26·27·46·109·116·153·154·155행(2절 1~8번)이다. M4_retry1 대비로는 13·14·21·26·27·46·109·116행뿐이고 153~155행은 바이트가 같다. 줄 수는 M4와 같은 207줄이다. 경로 2: 원문 그대로(2절 경로 2 1~7번, `$WT` 1줄 삽입) |
| ps1_lint(:145) | 종료 0 | 두 실행본 모두 종료 0. 경로 1 실행본에 `case_variant_overwrite`가 없어야 한다 |
| `$AllowListPath2`(:145) | 값이 T26 blob과 같은지 | 15개 값이 모두 `git cat-file blob T26:<파일>` raw sha256과 같다. 표에 `path2/test_rev26_p2.py`가 없다. 개수 관문 "15 expected"는 바뀌지 않았다. `t26_identity.json`의 `test_rev26_p2.py` 칸이 `3e8166b2…ca2877`이고 T26 blob 재계산값과 같다. 그 파일이 RD-1 4 대체 조건 1의 바뀐 파일 목록에 있다 |
| (새) 모드 인자 | — | 두 5단계 실행본에 `--tag-mode`가 0건이다(rev26:42 확인, 요청 밖 추가 ㉡) |
| (새) 기록 보호 | — | master `.gitattributes`에 `rev26_run/** -text` 줄이 있다. `rev26_run/` 파일의 `git check-attr text` = `unset`, `git ls-files --eol` = `i/lf w/lf attr/-text`다(커밋한 경우). raw sha256이 `t26_identity.json`에 적은 실행본 sha와 같다. T26의 `.gitattributes` diff 점검(:146)은 원문 그대로다 |
| 나머지(:144, :146~162) | — | 바꾸지 않는다 |

## 4. 메인 처리 순서(5단계 전)
1. 경로 1 실행본을 다시 만든다(준비 작성자 python-expert 또는 메인).
   - `rev26_run/run_judgement_path1_rev26.ps1`의 153~155행만 retry1 153~155행으로 바꾼다.
   - 지금 초안 sha `c7298f64…`는 폐기한다.
   - 작성자가 scratch 사본으로 미리 확인한 결과는 이렇다(참고). 같은 바이트로 만들면 LF 207줄, sha256 `3516ea5e27db31e3d3127d64d33f84e55602343231ccf4641dd9542009d6a563`, ps1_lint 종료 0(error 0·warning 0)이고, diff 집합은 3절 표와 같다. scratch 사본은 지웠으니 4′가 다시 계산한다.
   - 경로 2 실행본(`a6f0b90c…`)은 그대로다.
2. `rev26_run/t26_identity.json`을 다시 만든다.
   - 실행본 sha, M4·M4_retry1 대비 diff, retry1 sha `c93cfc5c…`, ps1_lint 결과(종료 0)를 넣는다.
   - `open_items` 1~3을 이 정오로 닫았다고 적는다.
   - 기존 `not_listed_new_file_t26_blob_raw_sha256` 칸은 유지한다.
   - `location_note`가 이 정오 E1-4를 가리키게 한다.
3. master `.gitattributes`에 다음 세 줄을 더한다.
   - `06_analysis/02_control/verif_matrix/v5_resume_4368/rev26_run/** -text`
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev26_erratum1.md -text`
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev26_erratum1.sha256 -text`
   - `rev26_run/` 파일을 `git add`하는 커밋과 같은 커밋이나 그보다 앞선 커밋에 넣는다.
4. 이 정오를 봉인한다(`.sha256`). 그 다음 4′(verif-protocol-auditor `[시점] 판정 전`) 지시문에 다음을 넣는다: 이 정오 경로·sha, `t26_identity.json`의 새 위치, 3절 점검표.
5. 5단계 전에 메인 checkout의 추적 트리를 정리한다(`prep_report.md` 6절: 경로 1 `Assert-CleanTree 'start'`).

## 5. 자체 대조(봉인 전)
- 판정·기록 구분은 1절 표의 "구분" 열에 적었다. 판정 항목의 정의·상태 순서(판정 실패 > 설정 결함 > 판정 불가 > 통과)·판정 행 0 처리는 rev26 그대로다.
- 참조 경로 존재 확인
  - `rev26_run/`의 `t26_identity.json`, 두 실행본, conda export 두 파일: 있음(작업 트리, 아직 추적 안 됨)
  - M4·M4_retry1 실행본: git 추적
  - T26 커밋: 있음
- 코드 동작 주장 확인
  - `$Grid` 덮어쓰기: M4 62·153·159·183행을 읽어 확인했다.
  - 개수 관문: rev26 실행본 207행을 읽어 확인했다.
  - pytest·`tag-mode` 0건: 두 실행본을 grep해 확인했다.
  - 경로 코드에 대한 주장(abl_line, `tag_matches`, `mode_tag`)은 두 구현 보고의 문장을 인용한 것이다. 이 작성자는 코드를 열지 않았다.
- 아직 없는 해시: 다시 만들 경로 1 실행본의 최종 sha와 이 정오의 sha는 메인이 고정한다. 4절 1의 sha는 참고값이다.
