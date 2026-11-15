# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev22 (R3c C-5 묶음 등급 멈춤 뒤: t45 행 짝짓기, 도구 보완 커밋 R3d, 재사용·재확인, 결과 본 뒤 개정, 봉인 후보 초안)

- **상태: 봉인 후보 초안(봉인 전).** 봉인 전에는 실행·판정에 쓰지 않는다. 봉인 때 바꿀 머리 줄은 끝 절에 원문으로 적었다.
- 원판~rev20은 고치지 않는다. 이 판은 rev21(sha256 `ecd709495f203eae1769ae42e67b5ae5bf2fb457146b558c12e46d636ed03f9a`, 봉인 2026-11-15 16:41:22 +09:00, 봉인 기준 커밋 S8 `4d8a95d086ab196b268a9a494098b8458386e1a9`, 봉인 파일 커밋 S9 `da126224b1aa3f02baf97f5e420e1854b4adda8f`, 브랜치 `z4373-s4`) 위에 쌓인다. 봉인 뒤 이 판과 앞 판이 다르면 이 판이 맞다. 이 판이 말하지 않는 것은 앞 판 그대로다. 용어(봉인 기준 커밋, 봉인 파일 커밋)는 rev16 4행과 같다.
- **시점: R3c `f9bc3c7` 경로 1 Chrono 판정에서 C-1·C-2·C-3 묶음 등급이 나오고 C-5 묶음 등급이 입력 거부(종료 2)로 멈춘 뒤, 메인 checkout은 R3c(봉인 SEAL_TIME, 봉인 기준 커밋 SEAL_COMMIT).** 이 판은 결과를 본 뒤의 개정이다. 본 자료는 R22-0에 적었다.
- 작성: control-expert, 2026-11-15. 기준: R2 `b9f5707`(실행), R3c `f9bc3c775d09d0588adb388dec96614fd95f2929`(판정 도구), S9 `da12622`(rev21).
  - 계기: `chrono_bundle_grade_4368.py --t45`가 "--t45 lists E_RE1bF_Fs8 twice"로 입력을 거부했다. t45 재생 출력의 행 이름(`case`)이 판정 행 이름이 아니라 실행 폴더 안쪽 이름이라, 같은 안쪽 이름을 가진 LS1·LS4·VB 행이 겹친다.
  - 사용자 결정 74~77(2026-11-15)과 봉인 전 감사(차단 2·권고 5)를 R22-1~R22-5에 반영했다. 결정 75는 경로 2 봉인 목록 rev22 추가(`z4376-p2chrono`), t45 짝짓기 대조 기준(`dir` 전체 경로), 경로 2 넘길 문장, 결정 76은 경로 2 출력의 재사용과 재판정, 결정 77은 경로 1 봉인 목록 정의 위치(rows judge)와 경로 1 행 판정 재실행이다.
- **봉인 준비판이다.** 봉인 전에 답이 필요한 항목은 없다(확인 필요 0). 이 줄은 봉인 때 바뀐다.
- **바꾸지 않는 것**: 숫자 문턱, 등급과 우선순위(원판 8.1), 멈춤 조건의 뜻(원판 8.2), 묶음 범위와 행 목록, 사전 예측, 두 경로 요건, 실행 커밋 R2, 이미 돈 실행의 argv·코드, T4·T5 판정 내용(v5 기준 개정 7), 두 경로 판정 도구의 판정 코드(봉인 목록 정의 밖, 경로 1 짝짓기 밖), rev16~rev21의 다른 조항.

## R22-0. 결과 본 뒤 개정의 공개 (본 자료 목록)

- 이 작성자(control-expert)가 본 것(읽기 전용, 2026-11-15): 메인 세션이 전한 멈춤 사실(위 계기), `judge_f9bc3c7/chrono_path1/`의 파일 목록, `run_path1_r3c.ps1`(19·22·57~60·89·95~103·105·117행), `t45_C5.json`(sha256 `aa19ebcf3fed31842ae76f554efc82ab7c22c0b48dbfff3b8b7e67f366ad477f`)의 키 구성과 `case` 값, `judge_C5.json`(sha256 `c1ba93823eee39c47b099042193ad54e29ae513bb7cbda3ae52a8437b27ad76a`)의 `case`·`dir` 짝, R3c `chrono_bundle_grade_4368.py`(74·76·134~141·864~878·1297행), `chrono_rows_judge_4368.py`(93~94·124행), `chrono_t45_replay.py`(876~885·1020~1032행), 메인 세션이 전한 `judge_f9bc3c7/chrono_path2/outputs.sha256`의 파일 sha256.
- **열람 공개**: 이 작성자는 첫 초안을 쓸 때 `t45_C5.json`의 머리(앞 1,500바이트)를 출력해 `summary` 블록 전체(T4·T5 초과 수, J-P3·rev7 요약, settings_equal·t4_0 통과 수 등)를 한 번 보았다. 봉인 전 감사자도 같은 블록을 한 번 의도치 않게 열람했다. 이 블록은 C-5 T4_T5 항목의 판정과 같은 값을 담는다. 두 경우 모두 그 값은 이 판의 정의에 쓰지 않았고 이 판에 적지 않는다. R22-1 짝짓기의 정의는 t45 값에 기대지 않는다(행 순서·경로·이름만 쓴다). C-1~C-3 묶음 등급 값과 경로 2 R3c 판정 결과는 이 판을 쓰는 데 쓰지 않았다.
- 판정서에는 이 목록을 그대로 싣고, 이 판의 정의를 "결과 본 뒤 정한 정의"로 적는다.

## R22-1. t45 행 짝짓기 (경로 1 전용)

- **[정의] 짝짓기**: `chrono_bundle_grade_4368.py`는 `--t45` 출력의 행을 이름이 아니라 **t45 입력 폴더 목록의 순서**로 판정 행에 짝짓는다. i번째 t45 행 ↔ i번째 입력 폴더 ↔ 그 폴더를 `dir`로 가진 `judge_C5.json` 행(판정 행 이름).
- **[정의] 근거 사슬**
  - 대상 행 목록의 원천은 집계 도구의 `T45_CASES`(18개, v5 기준 개정 6 3절 1~18행)다. R3c 실행 스크립트의 `$T45Cases`(18개)와 같은 목록이어야 하고, 판정서에 두 목록이 같음을 보인다. 다르면 S-11이다.
  - R3c t45 입력 폴더 목록은 R3c 실행 스크립트의 규칙("`judge_C5.json`의 `rows` 순서에서 `case`가 대상 목록에 든 행의 `dir`")을 sha256 대조한 R3c `judge_C5.json`(`c1ba9382…d76a`)에 적용한 것이다. 집계 도구는 같은 규칙으로 목록을 다시 만든다. 목록 파일을 인자로 받으면 그 목록은 다시 만든 목록과 같아야 한다. 다르면 S-11이다.
  - 원천 고정: R3c `judge_C5.json`(`c1ba9382…d76a`)에서 만든 목록 = R3d `judge_C5.json`(R22-3 재판정 출력)에서 만든 목록(순서·`dir` 완전 일치)이어야 한다. 다르면 S-11이다. 짝짓기에는 이 같은 목록을 쓴다.
  - 대소문자: 실행 스크립트의 PowerShell `-in`은 대소문자를 가리지 않는다. 집계 도구는 대상 목록 소속을 문자열 완전 일치(대소문자 구분)로 판정하고, 대소문자 무시로 고른 목록과 완전 일치로 고른 목록이 다르면 S-11이다.
  - 판정 행의 `dir`이 비었거나 None이면 S-11이다.
  - 도구는 쓴 목록과 그 sha256, 대상 목록 대조 결과를 출력의 짝짓기 기록 블록에 적는다.
- **[정의] 대조**(모두 참이어야 짝짓는다)
  1. t45 행 수 = 입력 폴더 수. 다르면 S-15다.
  2. 같은 순서에서 i번째 판정 행의 `dir` 전체 경로 = i번째 t45 입력 폴더 경로(같은 목록에서 온 문자열의 완전 일치).
  3. 행마다 t45 `case` = 그 입력 폴더의 안쪽 이름(경로 마지막 이름).
  4. 입력 폴더 경로가 목록 안에서 겹치지 않고, 짝지은 판정 행 이름이 겹치지 않으며, 그 이름 집합이 대상 행 목록과 정확히 같다.
  - 2~4 가운데 하나라도 거짓이면 S-11이다. 멈추면 등급을 내지 않는다.
- **[정의] 바꾸지 않는 것**: T4·T5 항목의 판정 로직(`t45_item`)·문턱·키, 다른 묶음·다른 항목, `chrono_t45_replay.py`, 행 판정 도구의 판정 코드.
- **[정의] 시험**: 집계 도구의 시험에 다음 합성 입력 시험을 더한다: 같은 안쪽 이름을 가진 세 행(바깥 폴더만 다름)의 바른 짝, 행 수 불일치(S-15), 순서가 바뀐 `dir` 경로, 안쪽 이름 불일치, 입력 폴더 경로 겹침, 대상 목록 불일치, 빈 `dir`, 대소문자만 다른 대상 이름, 목록 파일과 다시 만든 목록의 불일치(S-11).
- 결정 필요: **아니오**(사용자 결정 74의 2, 75의 2).

## R22-2. 도구 보완 커밋 R3d의 순서와 조건

- **[정의] 순서**
  1. 이 판을 봉인한다. 봉인 파일 커밋 S10을 S9 `da12622` 위에 만든다(부모 = S9 = 봉인 기준 커밋 SEAL_COMMIT = `da126224b1aa3f02baf97f5e420e1854b4adda8f`, 브랜치 `z4373-s4`). S10이 바꾸는 것은 이 판의 세 파일과 `.gitattributes`의 `-text` 3줄뿐이다.
  2. 경로 1 도구 브랜치 `z4376-p1chrono`(python-expert)를 R3c `f9bc3c7`에서 가르고, S10을 병합한 뒤 R22-1과 경로 1 봉인 목록 정의의 rev22 추가만 구현한다.
  3. 경로 2 도구 브랜치 `z4376-p2chrono`(원 경로 2 작성자)를 R3c `f9bc3c7`에서 가르고, S10을 병합한 뒤 경로 2 봉인 목록 정의의 rev22 추가만 한다.
  4. 메인 세션이 R3c에서 통합 브랜치 `z4373-r3d`를 만들고 `z4376-p1chrono` → `z4376-p2chrono`를 `--no-ff`로 병합한다. 마지막 병합 커밋이 **R3d**다.
  5. 판정 전 감사 뒤 메인 checkout을 `git merge --ff-only z4373-r3d`로 R3c에서 R3d로 맞추고, master와 `z4373-s4`·`z4376-p1chrono`·`z4376-p2chrono`를 함께 푸시한다. R3c..R3d에는 S10과 두 도구 브랜치의 커밋만 있다.
  - R4: 하네스 도구 브랜치 `z4373-p1harness`·`z4373-p2harness`와 `z4373-r4`는 **R3d**에서 가르고, R4 조건의 Chrono 판정 도구·허용 목록 기준점은 **R3d..R4**다(rev21 R21-3의 R3c를 R3d로 읽음). 하네스 도구(R4)의 봉인 목록에는 rev22를 더한다(rev13~rev22).
- **[정의] 봉인 목록**: 두 경로의 Chrono 판정 도구 봉인 목록에 rev22를 더한다(rev16~rev22, 그 앞의 목록 항목은 그대로). 두 경로의 목록은 같다(rev18 R18-1 2 그대로, 예외 없음).
- **[정의] 경로 1 봉인 목록의 위치**: 경로 1의 봉인 목록 정의는 행 판정 도구에 있고 집계 도구는 그것을 불러 쓴다(rev18 R18-1 2의 "Chrono 판정 도구"는 두 파일을 함께 가리킨다).
- **[정의] 봉인 목록 변경의 범위**(두 경로 같은 꼴): 봉인 목록 정의(항목 추가, 최신 판 표지 이동, 원문 비교 집합, 목록 설명 문자열 수정: 범위 표기와 판별 설명에 rev22를 넣는 것)와 그것을 검사하는 시험 기대값(기대 sha 표와 설명 검사), README의 규칙 해시·도구 sha 표.
- **[정의] R3d 조건**(모두 참이어야 R3d로 판정한다. 거짓이면 판정하지 않고 멈춘다, 원판 8.2 S-11)
  - `git diff --name-only f9bc3c7..R3d -- 03_src 02_params`가 비어 있다.
  - `git diff --name-only f9bc3c7..R3d`의 모든 파일이 다음 허용 목록 안이다.
    - (가) rev22 규칙 파일 세 개(`v5_resume_4368_rules_rev22.md`, `.sha256`, `_seal_candidate_draft.md`)와 그 `.gitattributes` `-text` 3줄(지운 줄 0)
    - (나) 경로 1: `04_scripts/02_chrono/chrono_bundle_grade_4368.py`(R22-1 짝짓기, 그 호출과 입력 폴더 목록 인자, 짝짓기 기록을 출력에 쓰는 부분, 판 문자열(`TOOL_VERSION`·`RULES_TEXT`), 모듈 docstring의 C-5 설명, argparse 도움말), `04_scripts/02_chrono/chrono_rows_judge_4368.py`(봉인 목록 변경의 범위만, 판 문자열은 바꾸지 않는다), `04_scripts/02_chrono/chrono_rows_judge_4368_README.md`(짝짓기 설명, 규칙 해시·도구 sha 표), `05_tests/unit/test_chrono_bundle_grade_4368.py`(R22-1 시험, 봉인 목록 기대값), `05_tests/unit/test_chrono_rows_judge_4368.py`(봉인 목록 기대값만)
    - (다) 경로 2: `06_analysis/02_control/verif_matrix/v5_resume_4368/path2_chrono/` 아래의 봉인 목록 변경의 범위만
    - (라) rev8 R8-4의 판정서·감사 기록, `00_docs/decision_log.md`·`00_docs/00_roadmap.md`·`00_docs/handoff/session_handoff.md`
  - 따라서 `chrono_t45_replay.py`, 러너·실행 경로, manifest, `resume4368_judge.py`, `path2/`는 diff 0이다.
  - 두 경로 모두 바뀐 파일마다 `git diff -U0 f9bc3c7 R3d -- <파일>`의 덩어리 표(덩어리 머리, 감싸는 함수 또는 정의 이름, 위 허용 범위의 어느 것인지)를 판정서에 싣는다. 허용 범위 밖의 덩어리가 있으면 S-11이다.
- 결정 필요: **아니오**(사용자 결정 74의 3·5, 75의 1, 77).

## R22-3. 재사용과 재판정

- **[정의] K-10 비교에서 빼는 것**(두 경로 공통): 봉인 블록, 도구 판·규칙 설명 문자열, 도구 sha·공개 블록, 입력 파일 경로·sha256 블록(그 입력은 앞 단계에서 K-10으로 대조된 것)을 빼고 나머지를 K-10 꼴(등급·참거짓·목록·개수·분류 완전 일치, 수치 상대 1e-9)로 대조한다. 같은 뜻의 키는 각 경로가 판정서에 키 대응표로 밝힌다.
- **[정의] 경로 1의 빼는 키 이름**: `tool`, `rules`, `seals`, 도구 sha 블록, 행 판정 출력의 `disclosure` 블록(새 판 공개 항목·그 sha256·짝, 행 판정 도구의 공개 함수가 만든다), 새 짝짓기 기록 블록, `inputs`의 `rows_judge.path`·`rows_judge.sha256`. `inputs`의 `rows_judge_tool`과 `runner_judge_dir`은 같아야 하므로 대조에 남긴다.
- **[정의] 경로 1 재사용**: R3c 러너 출력(R3c 경로 1 판정 폴더 안의 러너 판정 관련 파일로 `SHA256SUMS.txt`(120항목)에 든 것), `runner_judge/` 출력, `t45_C5.json`은 다시 만들지 않고 R3c `SHA256SUMS.txt`와 대조한 뒤 쓴다. 하나라도 다르면 S-11이다.
- **[정의] 경로 1 재판정**
  1. R3d 행 판정 도구로 C-1~C-8 행 판정(`judge_C*.json` 전부)을 다시 돌리고, 묶음마다 R3c `judge_C*.json`과 빼는 키 밖에서 K-10 꼴로 대조한다. C-1~C-8 묶음 출력이 양쪽에 모두 있어야 하며, 없으면 멈춘다(S-15).
  2. R3d 집계 도구로 C-1·C-2·C-3·C-5 묶음 등급을 R3d 행 판정 출력에서 내고(C-5는 재사용한 `t45_C5.json`과 R22-1 짝짓기), C-1~C-3은 R3c 묶음 등급 출력과 빼는 키 밖에서 K-10 꼴로 대조한다. 이어서 `records`·`k1view` 단계를 R3d 도구로 돈다.
  - 대조가 다르면 판정서에 표로 싣고 그 묶음은 판정 전에 멈추고 묻는다. 같으면 R3d 출력을 판정에 쓴다.
- **[정의] 경로 1 실행 스크립트**: R3c 실행 스크립트를 R3d 출력 폴더에 `run_path1_r3d.ps1`로 복사해 쓰고, 그 sha256과 R3c 판과의 diff를 판정서에 싣는다. 허용 변경은 셋뿐이다.
  1. 출력 변수(출력 폴더)를 R3d 폴더로 바꾼다.
  2. 재사용 입력(러너 판정 폴더, t45 출력, R3c 행 판정 출력과 묶음 등급 출력 중 대조용)의 경로를 R3c 폴더로 둔다. 쓰기 전에 R3c `SHA256SUMS.txt`와 대조한다.
  3. 짝짓기 입력 폴더 목록 인자를 더하고, 행 판정 재실행 단계와 대조 단계를 더한다.
  - R3c 폴더에는 쓰지 않는다. 실행 전후에 R3c `SHA256SUMS.txt`의 모든 파일을 대조하고, 달라진 파일이 있으면 S-11이다.
- **[정의] 경로 2 재사용과 재판정**
  1. 경로 2 R3c 판정은 R3c 도구로 끝까지 돌린다. 판정 중 도구 커밋이 바뀌면 S-12다.
  2. R3d 뒤에는 경로 2 R3c의 t45 재생 출력을 다시 만들지 않고, R3c 판정 직후의 출력 sha256 목록 파일(`outputs.sha256`, 그 파일의 sha256은 `bd49fb6b7a95cfa9b9322e9578d678c7fa3637454c624317668469a0b6b6409f`)과 대조한 뒤 쓴다. 다르면 S-11이다.
  3. R3d 경로 2 도구로 C-1~C-8 판정을 다시 돌린다(입력은 R3c와 같은 실행 기록과 위 t45 재생 출력). R3d 재판정 출력은 새 폴더에 두고 R3c 경로 2 출력 폴더에는 쓰지 않는다. 재판정 전후에 `outputs.sha256`의 모든 항목을 대조하고, 다르면 S-11이다.
  4. 묶음마다 R3c 경로 2 판정 출력과 빼는 것 밖에서 K-10 꼴로 대조한다. C-1~C-8 묶음 출력이 양쪽에 모두 있어야 하며, 없으면 멈춘다(S-15). 다르면 판정서에 표로 싣고 그 묶음은 판정 전에 멈추고 묻는다. 같으면 R3d 출력을 판정에 쓴다.
- 결정 필요: **아니오**(사용자 결정 74의 4, 75의 1, 76, 77).

## R22-4. 두 경로에 넘기는 문장

- **[정의]** 경로 1 작성자에게 R22-1·R22-2·R22-3의 [정의] 글머리(경로 2 재사용과 재판정 글머리는 빼고)를 넘긴다. 파일·줄 위치는 규칙 문장에 적힌 것 말고는 더하지 않는다. 경로 2 작성자에게는 R22-2의 순서 3, "봉인 목록", "봉인 목록 변경의 범위" 글머리, R3d 조건의 (다), R22-3의 "K-10 비교에서 빼는 것"과 "경로 2 재사용과 재판정" 글머리(그 안의 출력 위치·쓰기 금지·전후 대조 문장 포함)만 넘긴다. 경로 1 봉인 목록의 위치와 경로 1의 빼는 키 이름 글머리는 넘기지 않는다. 경로 2 자신의 도구 디렉터리 이름(R3d 조건 (다)) 말고는 파일·줄 위치를 경로 2 몫에 넣지 않는다. R22-0·R22-5와 다른 경로의 코드·출력은 넘기지 않는다. 지시문에 "이 판의 다른 절은 열지 않는다"를 넣는다.
- 결정 필요: **아니오**(사용자 결정 74의 7, 75의 3).

## R22-5. 공개

- **[사실]** 판정서 한계 절에 그대로 적는다: "rev22는 R3c 경로 1 판정에서 C-1~C-3 묶음 등급이 나오고 C-5 묶음 등급이 t45 입력 거부로 멈춘 뒤 정했다. 바뀐 것은 경로 1 집계 도구가 t45 재생 출력의 행을 판정 행에 짝짓는 방법(이름 → 입력 폴더 순서와 `dir` 경로·안쪽 이름 대조)과 두 경로 Chrono 판정 도구의 봉인 목록 정의(rev22 추가)뿐이고, T4·T5 판정 로직·문턱·키와 다른 묶음의 규칙은 바뀌지 않았다. 두 경로는 R3d 도구로 C-1~C-8 판정을 다시 내어 R3c 출력과 대조했고, 러너 출력과 t45 재생 출력은 sha256 대조 뒤 재사용했다. 작성 중 t45 재생 출력의 요약 블록을 열람한 사실은 R22-0에 적었다."
- **[사실]** 9.2: 이 판은 경로 1 출력을 본 뒤 정했다. 경로 2 도구에서 바뀌는 것은 봉인 목록 정의뿐이다. 이 판의 정의는 경로 2 R3c 판정 결과를 보지 않고 정했다.

### 결정 표

| 항목 | 정의 | 결정 필요 |
|---|---|---|
| R22-1 t45 짝짓기 | 입력 폴더 순서 + `dir` 전체 경로 = 입력 폴더 경로 + 안쪽 이름, 근거 사슬(`T45_CASES` = `$T45Cases`, 목록 재생성, 대소문자, 빈 `dir`), 행 수 S-15, 그 밖 S-11, 판정 로직 불변, 시험 | 결정됨: 사용자 결정 74의 2, 75의 2 |
| R22-2 R3d | S10(부모 S9, `z4373-s4`) → `z4376-p1chrono`·`z4376-p2chrono`(R3c에서, S10 병합 뒤) → `z4373-r3d`(p1 → p2 `--no-ff`) → 감사 → 메인 ff-only·푸시; 봉인 목록 두 경로 rev16~22(경로 1 정의는 행 판정 도구), 봉인 목록 변경 범위 일반형, 허용 (가)~(라), 덩어리 표 두 경로; R4는 R3d에서, 하네스 rev13~22 | 결정됨: 사용자 결정 74의 3·5, 75의 1, 77 |
| R22-3 재사용·재판정 | 빼는 것(공통 일반형, 경로 1 키 이름에 `disclosure`, 키 대응표); C-5 목록 원천 R3c = R3d; 경로 1: 러너·runner_judge·t45 출력 SHA256SUMS 대조 재사용, C-1~C-8 행 판정·묶음 등급 R3d 재실행과 K-10 대조, 실행 스크립트 허용 변경 셋, R3c 폴더 쓰기 금지·전후 대조; 경로 2: R3c 끝까지, t45 출력 `outputs.sha256` 대조 재사용, C-1~C-8 R3d 재판정(새 폴더, R3c 폴더 쓰기 금지, `outputs.sha256` 전후 대조)과 K-10 대조, 묶음 출력 없으면 S-15 | 결정됨: 사용자 결정 74의 4, 75의 1, 76, 77 |
| R22-4 넘길 문장 | 경로 1: R22-1~R22-3 [정의](경로 2 글머리 뺌), 경로 2: 순서 3·봉인 목록·변경 범위·(다)·빼는 것(일반형)·경로 2 재사용 [정의]만, 경로 1 구조·키 이름 없음, 자기 도구 디렉터리 말고 파일·줄 위치 없음 | 결정됨: 사용자 결정 74의 7, 75의 3 |
| R22-5 공개 | 결과 본 뒤 개정, 바뀐 것은 짝짓기와 봉인 목록 정의뿐, 요약 블록 열람 | 결정됨: 사용자 결정 74의 6 |

### 결과 본 뒤 사용자 결정 기록

| 날짜 | # | 결정 | 반영 |
|---|---|---|---|
| 2026-11-15 | 77 | 사용자 결정 77(2026-11-15, rev22 봉인 전 감사 차단 1): 경로 1 봉인 목록 정의는 행 판정 도구에 있으므로 그 정의와 시험 기대값만 rev16~22로 바꾸고, 경로 1도 R3d 도구로 C-1~C-8 행 판정을 다시 돌려 봉인 블록 밖을 R3c와 K-10으로 대조한다. 러너·runner_judge·t45 출력은 SHA256SUMS 대조 뒤 재사용한다. 두 경로 봉인 목록은 같고 예외는 없다. 경로 2 재판정 범위도 C-1~C-8 전체다 | R22-2, R22-3 |
| 2026-11-15 | 76 | 사용자 결정 76(2026-11-15): 경로 2 출력 처리는 R3c 판정을 끝까지 돌리고, R3d 뒤 t45 재생 출력을 sha 대조 뒤 재사용하며, R3d 경로 2 도구로 판정만 다시 돌려 봉인·도구 sha 블록 밖을 R3c 출력과 K-10으로 대조한다(다르면 멈추고 묻는다) | R22-3 |
| 2026-11-15 | 75 | 사용자 결정 75(2026-11-15, rev22 초안 보고의 확인 필요 2건): ① 경로 2도 봉인 목록에 rev22를 넣는다(`z4376-p2chrono`, R18-1 2 예외 없음), 경로 2 출력 재사용 규칙은 결정 76으로 정했다. ② t45 짝짓기 대조는 판정 행 `dir` 전체 경로 = t45 입력 폴더 경로 + 안쪽 이름 일치, 바깥 폴더 표지 대조는 쓰지 않는다. ③ 경로 2 넘길 문장은 봉인 목록과 재사용 정의 | R22-1~R22-4 |
| 2026-11-15 | 74 | 사용자 결정 74(2026-11-15): R3c C-5 묶음 등급의 t45 입력 거부를 경로 1 집계 도구의 t45 행 짝짓기 보완(R3d)으로 풀고, R3c 출력은 sha 대조 뒤 재사용해 `grade_C5`부터 잇는 rev22를 S9 위 S10으로 봉인한다(재사용·재판정 범위는 결정 76·77이 고쳐 씀) | R22-1~R22-5 |

## 봉인 때 바꿀 머리 줄 (메인 세션)

1. 봉인 전 확인 필요는 없다(S9 해시·rev21 봉인 sha는 4행에 적었다).
2. 파일 이름: `v5_resume_4368_rules_rev22_seal_candidate_draft.md`를 같은 폴더에 `v5_resume_4368_rules_rev22.md`로 복사한다. 초안 파일은 지우지 않는다.
3. 1행을 다음으로 바꾼다:
   `# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev22 (R3c C-5 묶음 등급 멈춤 뒤: t45 행 짝짓기, 도구 보완 커밋 R3d, 재사용·재확인, 결과 본 뒤 개정, 봉인)`
4. 3행(첫 글머리 "상태")을 다음으로 바꾼다:
   `- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev22.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev22_seal_candidate_draft.md`와 1·3·5·9행만 다르다.`
5. 5행("시점")에서 `SEAL_TIME`과 `SEAL_COMMIT`(S9 `da12622`)을 값으로 바꾼다. 이 두 이름 말고는 5행을 바꾸지 않는다.
6. 9행("봉인 준비판이다")을 다음으로 바꾼다:
   `- **봉인본이다.** 봉인 전 확인 필요는 없었고(S9 해시·rev21 봉인 sha는 4행), 사용자 결정 74~77(2026-11-15)과 봉인 전 감사의 차단·권고는 R22-1~R22-5에 반영했다.`
7. 바꾼 뒤 sha256을 계산해 `v5_resume_4368_rules_rev22.sha256`에 `<sha256>  v5_resume_4368_rules_rev22.md  sealed <SEAL_TIME 값> (436.8 rev22: after the R3c f9bc3c7 path 1 Chrono judgement stopped at the C-5 bundle grade (--t45 lists an inner case name twice) on top of rev21; thresholds, grades and stop meanings unchanged, seen-data list disclosed incl. one look at the t45 summary block (values unused); seal commit S10 on S9 da12622; path 1 bundle grade pairs t45 rows with judged rows by the t45 input folder order: target list T45_CASES = the runner $T45Cases, list rebuilt from the sha-checked judge_C5.json (case-sensitive, empty dir S-11), judged row dir path = input folder path and inner case name (count S-15, other mismatches S-11), T4 / T5 logic, thresholds and keys unchanged, tests added; tool fix commit R3d = z4373-r3d (--no-ff merges of z4376-p1chrono and z4376-p2chrono cut from R3c after merging S10), audit, main fast-forwarded R3c -> R3d and pushed with the seal and tool branches; seal lists of both Chrono paths gain rev22 (path 1 list defined in the rows judge, read by the bundle grade; no exception), seal-list change scope = list definition, its test expectations and the README hash / tool sha tables; 03_src / 02_params diff 0, allow list (a)-(d), hunk tables for both paths; K-10 excludes the seal block, tool / rules strings and tool-sha / disclosure blocks (path 1 names tool, rules, seals, tool sha, disclosure, pairing record; key maps disclosed); C-5 pairing list from R3c judge_C5.json = from R3d judge_C5.json; path 1 reuses runner / runner_judge / t45 outputs after the SHA256SUMS check, re-runs C-1..C-8 rows judge and the bundle grades at R3d and compares K-10 style with R3c, run_path1_r3d.ps1 changes limited to the output folder, the R3c reuse inputs and the pairing / re-run steps, no writes to the R3c folder, SHA256SUMS checked before and after; path 2 R3c judgement run to the end, its t45 replay outputs reused after the outputs.sha256 check, C-1..C-8 re-judged with the R3d tool into a new folder (no writes to the R3c path 2 folder, outputs.sha256 checked before and after) and compared K-10 style, missing bundle outputs S-15; harness rev13..22, R4 cut from R3d; user decisions 74-77; 9.2 disclosed)` 한 줄로 쓴다.
8. `.gitattributes`에 다음 3줄을 더한다(**`git add`보다 먼저**, 지우는 줄 없음):
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev22.md -text`
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev22.sha256 -text`
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev22_seal_candidate_draft.md -text`
9. 확인: `tools/verif/seal_check.py`와 `tools/verif/placeholder_scan.py`를 돌리고, 봉인본 5행에 `SEAL_TIME`·`SEAL_COMMIT`이 남지 않았는지 Grep으로 따로 본다.
10. `git add`(세 파일과 `.gitattributes`)와 봉인 파일 커밋 S10을 S9 위에 만든다(브랜치 `z4373-s4`). 메인 checkout의 HEAD는 바꾸지 않는다(R3c 그대로, R22-2 순서 5에서 R3d로 맞춘다). 봉인 뒤 이 문서를 고치지 않는다.
