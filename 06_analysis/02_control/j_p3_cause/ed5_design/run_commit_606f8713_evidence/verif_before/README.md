# verif 도구 모음
소유: python-expert(구현) / 사용: verif-protocol-auditor, 메인 세션

사전 등록(봉인)한 판정 규칙대로 실행·판정했는지 **읽기 전용으로** 감사하는 CLI 스크립트 모음이다.
읽기 전용 에이전트 `verif-protocol-auditor`의 "2단계: 감사 여섯 축" 중 S·E·I·C·T축 반복 검사(재생 대조 재집계, 반올림 저장의 문턱 경계 포함)를 즉석 스크립트 없이 하도록 만들었다(R축 규칙↔도구 대조는 규칙 원문을 읽어야 하므로 도구가 없다).

**모든 분류는 휴리스틱이다.** 도구가 낸 발견은 "이 줄을 읽어라"는 표시이고, 결함인지 아닌지의 확정 판정은 에이전트가 코드·규칙 원문을 읽고 내린다.

| 스크립트 | 하는 일 | 정의 축 |
|---|---|---|
| `seal_check.py` | 규칙 원판·개정판(`_rev<N>` 숫자 순)의 원시·LF 정규화 SHA-256 ↔ `.sha256`(`<stem>.sha256`, 없으면 `<name>.sha256` = `spec.md.sha256`) 첫 토큰, CRLF·BOM·끝 줄바꿈, `.gitattributes` 줄바꿈 보호(`-text` 또는 `eol=lf`, git check-attr 우선), `--code`의 64hex 상수·파일 이름 고정과 빠진 판, 인용 파일(판·봉인·`--hash-files`·`--sums` 목록과 그 항목)의 git 추적·무시 규칙(2026-11-17) | S |
| `gate_scan.py` | `ast`로 빈 선택이 통과로 끝날 수 있는 관문: 태그 단일 비교, 가드 없는 `all(...)`, `"pass": not x`, `min(default=)`·`or 0`, 경고 뒤 계속 진행, 필터 선택의 합계·any·all로 분기하고 else/기본이 pass인데 그 선택의 0건 처리가 없음(`empty_selection_sum_pass`, 2026-11-17), 키가 없을 때 조회 기본값(`x.get(k, 0)`·`x.get(k) or [0]`)으로 통과하는 판정(`missing_key_default_pass`, 2026-11-20), 레코드·행 값을 기준 폴더 없이 경로로 여는 코드(`Path(row["f"])`·`np.load(rec.get("p"))`, `row_value_path_no_base`, 2026-11-21), 좋은 패턴(건수 대조·태그 집합) | E |
| `baseline_check.py sums` | `SHA256SUMS` 목록: 항목 ↔ 실제 해시(줄바꿈만 다름 표시), 목록 밖 파일, CRLF 줄(떼고 읽되 보고)·BOM·중복·형식 오류·빈 목록, 목록과 항목의 git 추적(색인 또는 `--rev` 커밋)·무시 규칙(2026-11-17). 항목 경로 기준 `--base sums-dir`(기본)·`repo-root`, 항목이 모두 없으면 다른 기준 힌트 `sums_base_hint`(2026-11-21) | I |
| `baseline_check.py identity` | 기준선 폴더의 `*identity*.json` 안 모든 `"git"` 블록을 본다(2026-11-17). 볼 것: `head` ↔ `--expect-commit`(없으면 모두 같은지), `is_clean`, 선택으로 기준 커밋이 고친 파일의 mtime이 커밋 뒤·실행 전인지. 빈 head, 전체 커밋이 아닌 head, git 실패 표지는 error다(2026-11-21) | I |
| `ref_check.py` | 명세 md의 백틱 경로·파일 이름을 `--rev`(기본 HEAD) 트리에서 찾는다(루트·문서 폴더·경로 꼬리·이름·폴더·글롭). 없으면 이름 줄기가 비슷한 추적 파일 후보, 작업 트리에만 있으면 따로 표시(2026-11-17) | I |
| `junit_skips.py` | JUnit XML(pytest `--junitxml`)의 건너뛴 시험과 사유, `--critical` 패턴에 걸리는 건너뜀 = 미실행, 그 패턴의 시험이 아예 없음, 실패·오류, 시험 0개(2026-11-17), 예상 실패(xfail, warning)·strict XPASS(error)를 건너뜀과 따로 셈(2026-11-20) | E |
| `record_check.py identity` | 결과 레코드의 필수 정체성 필드, 균일해야 할 필드(태그·설정·커밋)의 고유값, 건수, 허용 태그, 첫·끝 키 차이, json 파일 메타, npz 키 | I |
| `record_check.py recount` | `--where`로 고른 레코드의 건수·값별 건수·min/max/mean 독립 재집계와 판정서 값 대조. 빈 선택은 오류 | C |
| `replay_recount.py` | 재생 jsonl(여러 부분 합침)을 저장 원본 jsonl과 키로 이어 (a) 선택 규칙(`r4+N` 등) 일치, (b) 재생 해시 ↔ 저장 해시 사본 ↔ 원본 해시, (c) 판별 조건 줄 수(`k1.would_block_any` 등) 재집계 | I·C |
| `timeline.py` | 규칙·개정판 봉인 시각(`.sha256`·git 첫 커밋·머리 날짜) ↔ 결과 최초 시각(레코드·csv 열 시각 필드·git·mtime, 근거 표시). 결과 jsonl·json·npz·csv·md·txt, `--repo` 기준 경로·글롭 | T |
| `judgement_checklist.py` | 규칙 원판·덧붙임 판의 "판정서에 적을 것"·"판정서에 적는다/싣는다/보인다/공개한다"·공개·사후 관찰 지시와 `[참고] 사전 예측 P-n` 줄(대조 의무)을 항목으로 뽑아, 항목마다 핵심 토큰(해시 접두·항목 기호·수치·시각·코드·따옴표 구절, 예측은 P-n + 맞음·틀림)이 판정서에 있는지 대조(found/missing/ambiguous, 근거 `path:line`). 토큰 없는 지시는 바로 앞 목록의 토큰을 빌린다(2026-11-16). 판정 뒤에 쓴다 | 판정서 |
| `ps1_lint.py` | PowerShell 실행 스크립트 정적 검사(실행하지 않음, PowerShell AST, 없으면 정규식): 앞서 대입한 변수를 대소문자만 다른 이름으로 `foreach`·대입에서 다시 씀(`$Grid` ← `foreach ($grid …)`), `Tee-Object` + 값 `return` 함수, 남은 자리표시(`*_FULL_HASH`·`{NAME}`·`<NAME>`), `-NoExit`(2026-11-16). `--allow`는 `placeholder_scan`과 같은 뜻(`NAME`·`<NAME>`·`{NAME}`)이고 허용 자리만 남으면 종료 0(`placeholder_allowed` info, 2026-11-22) | E·I |
| `handoff_leak.py` | 넘김 파일에서 이름 사전 JSON(파일·줄기·상수·하위 명령·폴더·브랜치)의 이름을 단어 경계·최소 길이로 찾아 파일별 누설 줄을 내고, 선택으로 표지 사이 블록(`<!-- 라벨 시작 -->`~`끝 -->`)의 원시 바이트 sha256을 파일끼리·기대값과 대조(2026-11-16) | 두 경로 독립 |
| `log_errors.py` | 러너 로그 폴더의 단계 로그(`**/*.log`)에서 `errors N`(N > 0)을 찾는다. 단계별 마지막·최대 N, 같은 이름 `.done`의 `exit=` 함께 표시(2026-11-11) | E·I |
| `placeholder_scan.py` | json·md 글롭에서 채워지지 않은 `{NAME}` 자리표시(기본 `\{[A-Z][A-Z0-9_]*\}`, 숫자 포함)를 찾는다. json은 그 문자열의 JSON 경로도 표시, `--allow`로 템플릿 자리(info) 지정(2026-11-11). `--pattern-set angle|both`로 `<name>` 자리(`<prelaunch>`·`<judge_sha256 of P-1a>`·`<실행 커밋>`)도 찾고, md 코드 밖의 배치용 HTML(`<br>` 등)과 자동 링크는 건너뛴다(2026-11-21) | I |
| `key_presence.py` | jsonl 줄·json `results[]`(또는 `--list-key`) 행마다 필수 키(점 경로)가 있는지만 센다: 키별 있음·없음·null/전체 행, `--where`로 행 거르기. `--npz-dir`·`--array`이면 폴더의 `.npz`마다 판정이 읽을 배열이 있는지(zip 항목 이름만, 빈 폴더 → 2). **값은 읽어 쓰지 않는다(판정 결과 블라인드)**(2026-11-21) | I |
| `threshold_boundary.py` | 점수를 반올림해 저장한 결과 CSV에서 문턱 경계 행(\|표기값 − 문턱\| ≤ ½ulp, 자릿수는 지정 또는 파일별 추정)을 세고, 판정 단위(`--group-by` 열·`@file`)별 통과 수를 표기값 기준·모호 제외·모호 포함으로 낸다(2026-11-15) | C |
| `missing_scan.py` | 판정 출력 JSON 폴더에서 판정 불가·계산 불가로 표시된 행(실행 쪽 행·키를 못 찾은 입력 결측 등)의 **이름만** 뽑는다. 키(`missing_inputs`)·사유 정규식·수치 조건(`runner_rows_found == 0`) 규칙을 인자로, 프로젝트 프리셋 `v5-resume-4368`(436.8 rev23 R23-3). 등급·수치는 싣지 않는다(2026-11-15) | E |
| `worktree_tests.py` | worktree 시험 파일을 scratch에 복사해 `__file__`은 원본 경로로 고정하고 저장 자료 경로(`07_results` 등)만 메인 checkout으로 바꿔, worktree 코드로 pytest를 돌린다. 결과(JUnit, skip = warning), `--probe-module`이 worktree에서 import됐는지(xdist 작업자마다), 원본 불변을 보고하고 복사본을 지운다. **verif에서 유일하게 코드를 실행하는 도구**(2026-11-22) | E |
| `smoke.py` | 의존성 버전 + 도구(seal_check·gate_scan·record_check 2종·timeline·replay_recount·log_errors·placeholder_scan·threshold_boundary·missing_scan·ps1_lint(정규식 파서)·handoff_leak·baseline_check 2종·ref_check(`--no-git`)·junit_skips) 1회 실행 + gate_scan 키 기본값 표본·junit_skips xfail 표본(이 둘은 분류가 요약에 있는지도 본다, 2026-11-20) + placeholder_scan `--pattern-set angle`·key_presence 2회(모두 있음·키 없음)·baseline_check sums `--base repo-root`와 기본 기준 힌트·gate_scan 기준 폴더 없는 레코드 경로(분류 확인 포함, 2026-11-21), JSON 한 개 출력(마지막 키 `"status"`) | — |

공용 모듈: `_cli.py`(종료 코드·출력 규약, `tools/integrity/_cli.py`에서 복사), `_findings.py`(심각도·발견 사항·보고서 쓰기, integrity에서 복사),
`_files.py`(파일 수집·바이트 사실·`--out` 위치 검사), `_git.py`(읽기 전용 git 조회), `_rules.py`(판 수집·`.sha256` 파싱·해시),
`_records.py`(jsonl·json·npz 로더, 점 경로 `a.b.c`, `--sample`), `_directives.py`(규칙 문서의 판정서 지시·토큰 추출, `judgement_checklist`용),
`_ps1_facts.py`(PowerShell 스크립트 사실: AST 실행기와 정규식 대체 추출기, `ps1_lint`용), `_ps1_ast.ps1`(pwsh가 실행하는 AST 추출 도우미, 읽기만 하고 JSON을 stdout에 쓴다),
`_selection_flow.py`(함수 범위의 선택·집계·0건 처리·판정 분기, `gate_scan`의 `empty_selection_sum_pass`용), `_absence_flow.py`(키가 모두 없을 때의 추상 평가와 판정 방향, `gate_scan`의 `missing_key_default_pass`용, 2026-11-20), `_sums.py`(`SHA256SUMS` 파서: GNU·`*`·BSD 형식, CRLF 줄 수), `_tracking.py`(인용 파일의 git 추적·무시 규칙과 `cited_*` 발견, `seal_check`·`baseline_check`용) — 2026-11-17. `_row_paths.py`(레코드 값이 기준 폴더 없이 경로로 열리는 곳, `gate_scan`의 `row_value_path_no_base`용, 2026-11-21). `_hashrefs.py`(봉인 파일 밖 해시 참조: 코드 상수 `--const`와 문서 인용 해시 `--quoted` 해석, `seal_check`용). `_slots.py`(자리 이름: `MASK`·`{MASK}`·`<MASK>` → `MASK`, `placeholder_scan`·`ps1_lint`의 `--allow` 공용, 2026-11-22). `_source_rebase.py`(복사한 시험 소스의 `__file__` 고정·데이터 경로 감싸기, 바이트 위치 편집이라 줄 번호 유지), `_wt_probe.py`(`worktree_tests`가 실행 폴더에 복사해 `-p _wt_probe`로 싣는 pytest 플러그인: `rebase_data`·probe 기록, 표준 라이브러리만) — 2026-11-22.

## 환경

- 인터프리터: `C:\ProgramData\miniforge3\envs\python-dev\python.exe` (Python 3.13). **항상 `-I -B`로 실행**하고, PATH의 `python`과 `conda run`은 쓰지 않는다.
- 의존성: 표준 라이브러리 + numpy 2.5.3(npz 헤더 읽기에만, 없으면 npz를 건너뛰고 `npz_keys` info로 남김). numpy 선형대수를 쓰지 않지만 python-dev 관례대로 `MKL_THREADING_LAYER=TBB`를 붙여도 된다.
- git: 선택. 조회 명령만 부른다(`GIT_OPTIONAL_LOCKS=0`, 표준 입력은 항상 빈 파이프): `rev-parse`, `check-attr -z`, `ls-files`(`--eol`, 추적 여부), `ls-tree -r --name-only`(`--rev` 커밋 트리), `check-ignore -v -z --no-index --stdin`, `log`, `diff-tree --name-only`, `hash-object`(`-w` 없음: 객체를 쓰지 않는다), `config --get`. `--no-git`이면 자식 프로세스를 하나도 띄우지 않는다.
- PowerShell(`ps1_lint`만, 선택): PATH의 `pwsh`(7.x, 2026-11-16 확인: Store판 `WindowsApps\…\pwsh.exe`), 없으면 `powershell`(5.1), 또는 `--pwsh PATH`. `pwsh -NoProfile -NonInteractive -ExecutionPolicy Bypass -File _ps1_ast.ps1 <파일…>`로 **한 번** 띄운다(`Bypass`는 그 자식 프로세스에만 적용, 시스템 정책은 바꾸지 않는다). 대상 스크립트는 `Parser::ParseInput`으로 구문만 읽고 실행하지 않는다. 4파일 약 0.7 s.
- `-I`는 스크립트 폴더를 `sys.path`에 넣지 않으므로 각 CLI가 첫머리에서 자기 폴더를 넣는다. stdout/stderr는 UTF-8로 재설정한다.

```powershell
$py = "C:\ProgramData\miniforge3\envs\python-dev\python.exe"
$tools = "C:\Users\jinbeom\.claude\tools\verif"
$scratch = "<scratchpad>\verif"
```

## 공통 규약

- **입력 파일은 절대 쓰지 않는다.** `--out`이 입력 파일과 같거나 **입력 파일의 폴더(또는 입력으로 준 폴더) 안**이면 종료 코드 2로 거부한다. `--out`은 scratchpad에만 둔다.
- `--out` 없이 실행하면 전체 보고서를 stdout에 출력한다. `--out`을 주면 UTF-8 파일로 쓰고 stdout에는 경로만 출력한다.
- `--format md|json`(기본 md, 한국어 표제·영어 JSON 키). stdout **마지막 줄은 항상 JSON 한 줄**이고 첫 키가 `status`다(`ok`·`findings`·`input_error`·`internal_error`, 종료 코드 0·1·2·3과 같은 뜻, 2026-11-08 추가). 이어서 `ok`, `exit_code`, `tool`, `command`, `error`, `warning`, `info`, `categories`, 도구별 건수. 입력 오류·내부 오류 때는 `status`, `ok`, `exit_code`, `error`(메시지)만 있다.
- 한글·공백 경로, CRLF/LF, UTF-8 BOM 입력을 받는다(UTF-8 → cp949 → 대체 문자 순으로 해독).
- 폴더 입력(`--code`, `gate_scan`)은 `*.py`를 재귀로 찾고 `__pycache__`, `.git`, `.venv`, `venv`, `node_modules`, `.mypy_cache`, `.claude\worktrees` 아래는 건너뛴다.

### 종료 코드

| 코드 | 의미 |
|---|---|
| 0 | `--fail-on` 수준 이상의 발견 없음 |
| 1 | 발견 있음. 기본 `--fail-on warning`(error·warning이면 1). `--fail-on error`면 error만 |
| 2 | 입력 오류: 경로 없음, 지원하지 않는 형식, 잘못된 인자·정규식·`--expect` 라벨, `--out` 위치 |
| 3 | 내부 오류(버그) — traceback은 stderr |

info는 종료 코드에 영향을 주지 않는다.

### 발견 사항 JSON

`findings[]`: `severity`(`error`/`warning`/`info`), `category`, `file`(절대 경로), `line`(1부터, 0은 파일 전체), `message`, `target`(판 이름·필드·`module:function` 등). `gate_scan`은 `function`, `source`(그 줄 코드 앞부분)를 더한다.

## seal_check.py — 봉인 (S축)

```powershell
& $py -I -B "$tools\seal_check.py" "<규칙 폴더>\las_targeted_rules.md" "<규칙 폴더>\u3_u6_rerun_rules.md" --code "<프로젝트>\04_scripts\04_hydraulic\coupled"
& $py -I -B "$tools\seal_check.py" "<v5>\v5_criteria.md" --format json --out "$scratch\seal.json"
# 저장소 기준 글롭 + 도구 상수 + 판정서 인용 해시 (2026-11-08 추가)
& $py -I -B "$tools\seal_check.py" --repo "<프로젝트>" "06_analysis/02_control/verif_matrix/*_rules*.md" "06_analysis/03_hydraulic/coupled/v5/v5_criteria*.md" `
    --const "04_scripts/04_hydraulic/coupled/fb_targeted.py:RULES_SHA256" --const "04_scripts/04_hydraulic/coupled/fb_targeted.py:RULES_REV1_SHA256" `
    --code "04_scripts/04_hydraulic/coupled" --quoted "06_analysis/02_control/verif_matrix/las_judgement.md" `
    --hash-files "06_analysis/03_hydraulic/coupled/v5/las/*.jsonl" --out "$scratch\seal.md"
```

인자: `RULE...`(원판·개정판 `.md` 또는 글롭, 0개면 종료 2), `--repo DIR`(상대 경로·글롭·`--code`·`--const`·`--quoted`·`--hash-files`·`--sha-dir`·`--gitattributes`의 기준, 기본 현재 폴더), `--revs auto|none`(기본 auto), `--sha-dir DIR`(기본 규칙 폴더), `--code PATH...`(여러 값, 여러 번), `--const FILE:NAME`(한 번에 하나, 여러 번), `--quoted DOC`(한 번에 하나, 여러 번, 글롭 허용), `--hash-files GLOB...`(여러 값, 여러 번), `--gitattributes FILE`, `--no-git`, `--out`, `--format`, `--fail-on`.

인자 추가(2026-11-17): `--sums GLOB...`(여러 값, 여러 번: `SHA256SUMS` 목록. 목록 자체와 그 항목 중 있는 파일을 인용 파일로 본다), `--check-tracked`(판·봉인·`--hash-files`까지 추적 안 함을 error로), `--rev REV`(추적 여부를 색인 대신 그 커밋 트리로 본다. `--no-git`과 함께·저장소 밖·없는 커밋이면 종료 2).

```powershell
# 봉인 커밋 시점에 목록 항목이 커밋에 들어 있었는지 + spec.md.sha256 봉인
& $py -I -B "$tools\seal_check.py" --repo "<프로젝트>" "06_analysis/02_control/j_p3_cause/jp3_remedy_spec.md" `
    --sums "06_analysis/02_control/j_p3_cause/baseline_221456d/SHA256SUMS" --rev f67745f --check-tracked --out "$scratch\seal_jp3.md"
```

반복 인자(2026-11-09 수정): `--code`·`--hash-files`는 `--hash-files a b`(한 번에 여러 값)와 `--hash-files a --hash-files b`(여러 번) 모두 **전부 합친다**(`action="extend"`). 이전에는 여러 번 주면 마지막 것만 남아(argparse last-wins) 앞 글롭의 결과 해시 인용이 `quoted_unresolved`로 나왔다. `--const`·`--quoted`는 원래부터 여러 번 줘야 누적되고 한 번에 값 하나만 받는다(`--quoted a b`는 종료 2: `unrecognized arguments`). 여러 값 인자 바로 뒤에 규칙 인자를 적으면 그 값으로 먹히므로 규칙 인자는 맨 앞에 둔다.

판정 규칙:
- 입력 모으기: 규칙 인자에 `*`·`?`·`[`가 있으면 `glob`(`**` 재귀, 와일드카드는 숨김 폴더 `.git`·`.claude\worktrees`에 들어가지 않음. 글롭에 그 폴더를 글자 그대로 적으면 들어간다: `".claude/worktrees/<wt>/06_analysis/**/*.jsonl"`, 2026-11-09)으로 펼친다. `--quoted`·`--hash-files` 글롭도 같다. **맞는 파일이 0개인 글롭은 종료 2**(빈 선택은 통과가 아니다). 펼친 파일 중 `<stem>_rev<N>[a-z].md`이고 옆에 `<stem>.md`가 있으면 그 묶음의 판으로 합친다(원판과 개정판이 둘 다 맞아도 한 번만 잰다). `--revs none`이면 자동 수집 없이 이름이 주어진 개정판만 잰다. `x_rules_interp.md`, `x_draft.md`처럼 판 이름이 아닌 파일은 자기 이름의 묶음이 된다(봉인이 없으면 `seal_missing`).
- 개정판은 같은 폴더의 `<stem>_rev<N>[a-z].md`. 0 채움이 없으므로 **숫자 순**(rev2 < rev10), 문자 접미(rev12a, rev12b)는 같은 번호 뒤. `<stem>_rev_draft.md`, `<stem>_interp.md` 같은 이름은 판이 아니다.
- `.sha256`은 `<sha-dir>/<파일 stem>.sha256`, 그것이 없으면 `<sha-dir>/<파일 이름>.sha256`(`sha256sum x.md > x.md.sha256` 관례, 예 `jp3_remedy_spec.md.sha256`, 2026-11-17). 둘 다 있으면 stem 쪽을 쓰고 다른 쪽은 `seal_two_files` info. 한 줄 `<64hex>  <파일명>  sealed YYYY-MM-DD HH:MM:SS +09:00 (<메모>)`에서 **첫 토큰만 해시**로 본다(나머지는 선택, 메모는 비ASCII 허용). `sha256sum -b`의 `<64hex> *<파일명>`에서 `*`는 이름이 아니다(`seal_name_mismatch`가 나지 않는다). 코드의 이름 고정도 `x.md.sha256`을 알아본다.
- 인용 파일 git 추적(2026-11-17): 판·봉인·`--hash-files`·`--sums` 목록·목록 항목(있는 파일)마다 `git ls-files`(또는 `--rev`면 `git ls-tree -r <커밋>`)로 추적 여부, `git check-ignore -v --no-index`로 무시 규칙을 본다. 추적 안 함 + 무시 규칙 → `cited_ignored`(error, 역할과 무관, 규칙 `source:line:pattern` 표시). 추적 안 함 + 규칙 없음 → `--sums` 목록·항목은 `cited_untracked`(error), 판·봉인·`--hash-files`는 `--check-tracked`일 때만 `cited_untracked`(아니면 판·봉인은 예전처럼 `rule_untracked` info). 추적 중인데 무시 규칙에 걸림(강제 추가) → `cited_ignored_tracked` info. git 작업 트리 밖 → `cited_outside_repo` info. 목록 항목 파일이 없으면 `sums_entry_missing` warning(해시 대조는 `baseline_check.py sums`).
- 해시는 두 규약을 모두 잰다: 원시 바이트(`raw`)와 CRLF→LF 정규화(`lf`). 둘 다 다르면 `seal_mismatch`. 이때 LF→CRLF 변환 해시와 같으면 메시지에 "줄바꿈만 다름"을 붙인다.
- 줄바꿈 보호: 규칙·개정판·`.sha256` 각각에 `git check-attr text eol`을 묻는다. `text`가 `unset`(= `-text`·`binary`)이면 보호 `-text`, 아니고 `eol`이 `lf`이면(예: `* text=auto eol=lf`) 보호 `eol=lf`(2026-11-11: 체크아웃이 `core.autocrlf`와 무관하게 LF라 봉인이 깨지지 않는다. `attr_protected_eol_lf` info로 남긴다 — `-text`와 달리 CRLF로 커밋된 내용은 다음 add 때 LF로 정규화될 수 있다). `eol=crlf`는 보호가 아니다. git이 없거나 저장소 밖이면 `--gitattributes`(없으면 규칙 폴더에서 위로 찾은 `.gitattributes`)를 직접 해석한다(마지막 일치 줄 우선, `/`가 있는 패턴은 그 파일 폴더 기준, 대소문자 무시).
- 코드 고정(`--code`): docstring이 아닌 문자열 상수만 본다.
  - `hash` 고정: 64hex 상수가 어느 판의 원시·LF·봉인 해시와 같음.
  - `name` 고정: 상수의 마지막 경로 성분이 판 파일 이름(`x_rev1.md`) 또는 그 `.sha256` 이름과 같음(예: `RULES_PATH.with_name("x_rev1.md")`). 실행 중 `.sha256`을 읽어 대조하는 도구가 여기에 해당한다.
  - 한 파일이 어떤 묶음의 판을 하나라도 고정하면, 같은 묶음에서 고정하지 않은 판을 `code_pin_missing`으로 적는다(고정 방식 `hash`/`name` 표시).
  - 맞는 판이 없는 64hex 상수는 **가장 가까운 소유 이름**(대입 대상, dict 키, 키워드 인자)에 `rule`·`criteria`·`seal`이 있고, 그 상수가 점검 중인 묶음의 고정으로 보일 때만 `code_pin_stale`. 그 밖의 64hex(데이터 해시 등)는 `unrelated_hex_constants`로 센다.
  - 계열 판별(2026-11-15 수정): 상수 **옆 문자열**(같은 튜플·리스트·집합, 같은 dict 항목의 키·값, 같은 호출의 인자·키워드 인자)이 규칙 파일 이름(`<stem>[_rev<N>[a-z]].md`·`.sha256`)이면 그 이름의 묶음(stem)의 고정으로 보고, 그 묶음을 점검 중일 때만 `code_pin_stale`이다(메시지 "옆 문자열이 가리키는 규칙"). 옆에 규칙 파일 이름이 없으면 예전처럼 파일 어딘가에 점검 묶음 이름이 있으면 `code_pin_stale`(메시지 "언급된 규칙"). 이전에는 `v5_resume_4368_rules*`만 점검해도 `SEALED = [("…/v5_criteria_rev7.md", "<hash>", …)]`처럼 **다른 계열**(v5_criteria·d1_selection_rules·판정서)의 해시가 같은 파일에 있으면 오탐이 났다(경로 2 `p2_rules.py` 11건). 다른 계열 고정은 `pins`에도 넣지 않는다. `pins[].named_families`에 옆 이름의 묶음을 적는다.
- 파일 사실(규칙 판과 `.sha256` 각각): CRLF 줄 수, LF만 있는 줄 수, BOM, `git ls-files --eol`(`i/`·`w/`·`attr/`), 추적 여부(ls-files에 있으면 추적), 마지막 커밋 시각(`git log -1 --format=%cI`), mtime(로컬 시간대 ISO). `--no-git`이거나 저장소 밖이면 추적은 `null`(모름)이다.
- `core.autocrlf`: 저장소마다 `git config --get core.autocrlf`를 읽는다. `true`·`input`인데 **규칙 판**에 보호(`-text`·`eol=lf`)가 없으면 `attr_unprotected_autocrlf`(error, 체크아웃·커밋 때 줄바꿈이 바뀌어 봉인이 깨진다). `.sha256`은 첫 토큰이 CRLF로도 살아남으므로 `attr_unprotected`(warning) 그대로다. git을 못 쓰면 autocrlf를 모르므로 warning만 낸다.
- `--const FILE:NAME`: 마지막 `:`에서 나눈다(`C:\...` 드라이브 허용). `NAME`에 대한 **첫 대입**(`NAME = ...`, `NAME: str = ...`, `obj.NAME = ...`)의 값 안에 있는 64hex 문자열(튜플·dict 안 포함)을 모두 꺼내, 모든 판의 원시·LF·봉인 해시와 비교한다. 파일이 없거나 `FILE:NAME` 형식이 아니거나 파이썬 구문 오류면 종료 2.
- `--quoted DOC`: 각 줄에서 다른 영숫자·`_`에 붙지 않은 16진수 8~64자를 접두로 보고 후보 해시(판의 원시·LF·봉인, `--hash-files`의 원시·LF)의 앞부분과 맞춘다. **숫자만인 토큰(날짜·건수)과 UUID(`8-4-4-4-12`, 세션 id)는 뺀다.** 안 맞으면 문서가 git 저장소 안이고 40자 이하일 때 `git rev-parse --verify <접두>^{commit}`으로 커밋인지 본다.

| 분류 | 심각도 | 내용 |
|---|---|---|
| `seal_mismatch` | error | 봉인 해시 ≠ 원시 해시 그리고 ≠ LF 정규화 해시 |
| `seal_eol_convention` | warning | 원시 해시와는 다르고 LF 정규화 해시와 같음(작업 트리가 CRLF) |
| `seal_missing` | warning | 판에 `.sha256` 없음 |
| `sha_file_malformed` | warning | 첫 토큰이 64자리 16진수가 아님 |
| `seal_name_mismatch` | warning | 봉인 줄의 파일 이름이 그 판 이름과 다름 |
| `code_pin_missing` | warning | 코드가 고정한 판과 빠진 판(파일별) |
| `code_pin_stale` | warning | 규칙용으로 보이는 해시 상수가 어느 판과도 안 맞음 |
| `const_not_found` | error | `--const`의 이름에 대한 대입이 그 파일에 없음 |
| `const_mismatch` | error | `--const` 값의 64hex가 어느 판의 원시·LF·봉인 해시와도 다름 |
| `attr_unprotected_autocrlf` | error | 규칙 판에 `-text`도 `eol=lf`도 없고 `core.autocrlf`가 `true`·`input` |
| `attr_unprotected` | warning | `text`가 `unset`이 아니고 `eol`이 `lf`가 아님(보호 없음). autocrlf가 false·없음·모름, 또는 `.sha256` |
| `attr_protected_eol_lf` | info | 보호가 `-text`가 아니라 `eol=lf`(LF 체크아웃 고정, 2026-11-11) |
| `const_no_hash` | warning | `--const` 대입 값에 64hex 문자열이 없음 |
| `quoted_unresolved` | warning | 인용 접두가 어느 후보 파일 해시와도, 커밋과도 맞지 않음(데이터·명령 해시면 그 원본을 `--hash-files`로 준다) |
| `eol_crlf` | 규칙 `.md` warning / `.sha256` info | CRLF 줄 수 |
| `code_pin_unchecked` | info | 고정이 있는데 `hashlib`·`sha256(`·`.sha256` 흔적 없음(텍스트 휴리스틱) |
| `rev_gap` | info | 개정 번호 빠짐 |
| `bom`, `no_final_newline` | info | BOM 있음, 끝 줄바꿈 없음 |
| `code_unparsable` | info | 코드 구문 오류로 건너뜀 |
| `rule_untracked` | info | 규칙 판·`.sha256`을 git이 추적하지 않음(봉인 시각의 git 근거 없음). `--check-tracked`면 대신 `cited_untracked` |
| `cited_ignored` | error | 인용 파일이 추적 안 되고 `.gitignore` 규칙에 걸림(`git add`가 조용히 뺀다, 2026-11-17) |
| `cited_untracked` | error | `--sums` 목록·항목(또는 `--check-tracked`면 모든 인용 파일)이 색인·`--rev` 트리에 없음 |
| `sums_entry_missing` | warning | `--sums` 목록이 가리키는 파일이 없음 |
| `cited_ignored_tracked` | info | 추적 중이지만 무시 규칙에 걸림(강제 추가 — 같은 규칙의 새 파일은 빠진다) |
| `cited_outside_repo` | info | 인용 파일이 git 작업 트리 밖 |
| `seal_two_files` | info | `<stem>.sha256`과 `<name>.sha256`이 둘 다 있음(stem 쪽을 씀) |
| `quoted_commit` | info | 인용 접두가 파일 해시가 아니라 git 커밋으로 풀림 |
| `quoted_ambiguous` | info | 인용 접두가 서로 다른 파일 두 개 이상의 해시와 맞음 |

JSON 키: `repo`, `tracking_basis`(`index` 또는 `commit <sha>`), `tracking[{path, role(rule·seal·hash_file·sums_list·sums_entry), relative, tracked, ignore_rule}]`, `rules[{path, family, rev, sha256_raw, sha256_lf, sealed_hash, sealed_at, note, seal_path, match}]`(`match` ∈ `raw`·`lf`·`none`·`no_sha`), `files[{path, role(rule·seal), family, rev, crlf, lf, bom, tracked, git_eol{index, worktree, attr}, last_commit_at, mtime}]`, `pins[{code_path, line, kind, hash, name, owner, matches[], named_families[]}]`, `attributes[{path, protected, protection, text, eol, source, autocrlf}]`(`protection` ∈ `-text`·`eol=lf`·`null`), `consts[{spec, path, name, line, hash, matches[{path, label, basis, hash}]}]`(`basis` ∈ `raw`·`lf`·`seal`), `quoted[{document, line, prefix, context, is_commit, matches[]}]`, `git`, `summary{findings, editions, families, code_files, pins, unrelated_hex_constants, consts, quoted, quoted_unresolved, sums_lists, cited_files, cited_untracked, cited_ignored, …}`.

## gate_scan.py — 빈 집합·0건 통과 (E축)

```powershell
& $py -I -B "$tools\gate_scan.py" "<코드>\u3_judge.py" "<코드>\p3_chrono_check.py" "<코드>\j_p3_inputs.py"
& $py -I -B "$tools\gate_scan.py" "<코드 폴더>" --tag-names controller_tag,tag,setting --allow-tags "^TAG_IND$" --format json
& $py -I -B "$tools\gate_scan.py" "<코드>\jp3_baseline_compare.py" --bare-get   # 기본값 없는 x.get(k)도 출처로
```

인자: `PATH...`, `--tag-names`(기본 `controller_tag,tag,setting`), `--allow-tags REGEX`(맞는 상수와의 비교는 빼기), `--bare-get`(기본값 없는 `x.get(k)`(`None`)도 `missing_key_default*`의 출처로 센다, 2026-11-20), `--no-row-paths`(`row_value_path_*` 규칙을 끈다 = 2026-11-20까지의 규칙 집합과 같은 결과, 2026-11-21), `--out`, `--format`, `--fail-on`.

판정 규칙(정적 `ast`, 코드를 실행하지 않는다):
- 태그 표현: `.get("<tag-name>")`, `["<tag-name>"]`, 이름·속성이 tag-name으로 끝나는 것(대소문자 무시, UPPER_CASE 이름은 제외). 상수 쪽: 문자열 상수 또는 UPPER_CASE 이름·속성(`TAG_VB`, `v5_rerun.TAG_VB`, `EXPECTED_TAG`).
- 건수 가드(같은 함수 본문 어디든): `len(...)`이나 `*_COUNT`가 들어간 비교, `bool(x) and ...`, `if not <이름·속성·첨자>`.
- `all(...)` 판정값: dict의 `"pass"`·`"ok"`·`"verdict"` 값, `return` 값, `ok`·`passed`·`is_pass`·`verdict` 이름이나 `x["pass"]`로의 대입 우변. 모듈 최상위의 가드는 모듈 전체를 본다.
- 경고 뒤 진행: `warnings.warn`, `logging.warning`, `logger.warning`, `log.warning`, `print("WARN…")`/`print(f"WARN…")` 문장 뒤 같은 블록에 `return`·`raise`·`continue`·`break`·`sys.exit`가 없음(뒤 문장 안쪽까지 본다).
- 빈 선택 합계 통과(`empty_selection_sum_pass`, 2026-11-17, `_selection_flow.py`). 사건: 221456d의 J-P3 판정이 `judged = [… if case == JUDGED]` → `sums = {k: sum(… for r in judged)}` → `if not records … elif any(sums.values()): H-7 else: pass`라 판정 행 0개도 pass였다(`not records`는 입력을 지킬 뿐 `judged`를 지키지 않음, ad5024b에서 `elif not judged` 추가). 함수(또는 모듈 최상위)마다:
  - **선택**: `if`가 있는 컴프리헨션, `filter(…)`(`list`·`sorted`로 감싸도), `x = []` 뒤 `for` 안 `if` 아래 `x.append/add`, 그리고 선택을 그대로 옮긴 컴프리헨션(그 선택이 부모).
  - **집계**: 선택을 `all/sum/max/min/fsum/mean`에 통째로 넘김, `all/any/sum/…`에 넘긴 컴프리헨션이 선택을 돎, 선택을 도는 `for`에서 누적(`+=`, `x = f(x)`, `True/False` 깃발, `append`). 집계에서 나온 이름을 두 번 따라간다. **선택의 참거짓·`len`·`any(선택)`은 집계가 아니다**(`"fail" if failed else "pass"`처럼 실패 집합이 비면 통과인 관용구, 오탐을 막으려고 뺀다).
  - **판정**: `if/elif` 사슬의 시험이 집계를 읽고 어느 가지·`else`·앞선 pass 기본값(`status = "pass"` 뒤 `if`)·멈추는 가지 뒤의 `return "pass"`가 pass; pass 값이 있는 조건식; `ok`·`passed`·`verdict` 이름이나 `"pass"`·`"ok"` 키의 값. pass 값: `"pass"`·`"passed"`·`"ok"`·`"통과"`(대소문자 무시), `PASS`/`*_PASS`/`*_OK` 이름, 그런 값을 `status`·`verdict` 등 키에 담은 dict.
  - **0건 처리**(같은 함수 어디든): `not x`, `not len(x)`, `bool(x)`, `len(x)`(또는 `n = len(x)`의 `n`)과의 비교, 선택을 돈 `for`의 카운터를 최솟값으로 비교(`n < K`, `n <= K`, `n == K`). 단 **스스로 pass를 내는 시험·값 안의 것은 빼고**, 거기서는 `x and …`·`bool(x) and …`·`len(x) > 0 and …`만 센다. 선택이 0건 처리된 다른 선택에서 걸러졌으면(실패 부분집합) 처리된 것으로 본다. 함수 인자 같은 원래 입력의 0건 처리는 선택을 덮지 않는다.
  - 발견 줄은 `if/elif` 사슬의 첫 `if`(또는 조건식·대입) 줄이고, 메시지에 선택 이름과 그 줄을 적는다. warning이라 기본 종료 1.
  - 실데이터(읽기만): z4369-jp3 `03_src/outrigger_sim/control/extend_start_bound.py` 221456d판 → `j_p3_judgement_rev5` 1건(`judged` 1605행, 분기 1618행, 종료 1), ad5024b판 → 0건(종료 0). 같은 worktree `03_src`·`04_scripts` 1,075파일 전체에서 7건(사건 판 제외).
- 키 기본값 통과(`missing_key_default_pass`, 2026-11-20, `_absence_flow.py`). 사건: z4369-jp3 `jp3_baseline_compare.py`(ad5024b)의 `if sum(check.get("retract_tracker_dominated_reads") or [0]) or …: failures.append(…)`(234행)와 `failures += [… for key in JUDGED_KEYS if sum(check.get(key) or [0])]`(238행)는 키가 없는 기록을 "0건"으로 읽어 실패를 적지 않는다. 함수(또는 모듈 최상위)마다 **"조회한 키가 모두 없다"는 가정으로 한 번 평가**한다:
  - **출처**: `x.get(k, D)`, `x.get(k) or D`(`D`는 상수나 상수만 든 리스트·튜플·집합·dict, `list()`·`dict()`). 기본값 없는 `x.get(k)`는 `None`으로 평가하되 `--bare-get`일 때만 출처로 센다. `os.environ.get`은 설정이라 뺀다.
  - **평가**: 참거짓, 알면 정확한 값, 컨테이너면 비었는지·원소가 모두 참/거짓인지. `sum`·`any`·`all`·`len`·`max`·`min`·`bool`·`int`·`float`, `and`·`or`·`not`, 비교(양쪽 값을 알 때), `+`, 컴프리헨션(필터가 거짓이면 빈 것)을 따른다. 대입·`+=`·`d[k] += …`·`dict.fromkeys(…, 0)`은 소스 순서로 이름에 싣고(상수 키 `d["k"]`는 따로), 두 번 대입한 이름은 둘이 같은 것만 남긴다. 대문자 상수 이름(`JUDGED_KEYS`)은 비지 않은 모음으로 본다. 결과를 정한 피연산자의 출처만 남긴다(`a and b`에서 `a`가 거짓이면 `a`의 출처만).
  - **판정과 경고**(warning): `if/elif` 사슬을 가정대로 따라가서 실패 동작(`failures.append`·`problems.extend`·`+=`, `raise`, `sys.exit(≠0)`, `ok = False`·`status = "fail"`·`"H-7"`, `return False`)이 든 가지를 건너뛰거나, 통과 가지·`else`의 통과로 가면; 조건식이 통과 값으로 가면; 판정값(`"pass"`·`"ok"` 키, `ok = …`)이나 불 모양 `return`이 참이면; 실패 목록(이름에 fail·problem·error·issue·violation·stop·blocker·blocked·mismatch·reject·missing·bad)을 채우는 컴프리헨션이 비면; 빈 기본값을 도는 `for`의 몸에 실패 동작이 있으면.
  - **안전 방향은 조용하다**: 가정대로 따라간 가지가 실패 동작이면(`if judged == 0: raise NotJudgeable`) 보고하지 않고, 그 출처는 "잡힘"으로 표시해 같은 출처의 다른 판정도 보고하지 않는다(`if len(rows) != count: problems.append(…)` 뒤의 `if rows:`).
  - **참고**(info, `missing_key_default`): 판정이 기본값을 읽지만 방향을 평가할 수 없음. 단순 조회(`value = d.get("a", 0)`만)는 보고하지 않는다. 출처 묶음이 같은 발견은 하나만 남긴다(warning 우선, 줄 순).
  - 실데이터(읽기만, ad5024b): 재현 표본 4줄 → 1건(4행, 종료 1, 이전 0건). `jp3_baseline_compare.py` → warning 2(234·238행), `--bare-get`이면 6(200·225·227·234·238·240행). z4369-jp3 `03_src`·`04_scripts` 1,075파일 → warning 50·info 27(약 39 s). 눈으로 본 거짓 양성 꼴: 설정 기본값 비교(`b.get("force_point", "contact_point") == "ball_centre"`·`TGT.get("ra_mode", "rel")`), 멱등 표식(`__dict__.get(MARK, False)`).
- 기준 폴더 없는 레코드 경로(`row_value_path_no_base`, 2026-11-21, `_row_paths.py`). 사건: 436.9 J-P3 `jp3_baseline_compare.py`(보관본 `j4a_remedy_f83a51e3/old/`)의 `new_npz = Path(new["t4h_file"])`(510행). run_v5 행의 `t4h_file`은 **파일 이름만**이라 현재 폴더(CWD) 기준으로 열려 `FileNotFoundError`가 났다. 함수(또는 모듈 최상위)마다:
  - **레코드 값**: 문자열 상수 키의 `x["key"]`·`x.get("key"[, 기본값])`(`os.environ` 제외). `str(…)`·`os.fspath(…)`·`… or 기본값`으로 감싸도 같다. 한 번만 대입된 이름(`name = row["file"]`), 레코드 값을 도는 `for`·컴프리헨션 변수(`for f in rec["files"]`, 키 표시 `files[]`)도 그 값을 나른다. 두 번 이상 대입된 이름과 lambda 인자와 같은 이름은 따라가지 않는다.
  - **여는 곳**: 인자 하나인 `Path(v)`·`PurePath(v)`, `open`·`io.open`, `np.load`·`loadtxt`·`genfromtxt`·`fromfile`, `pd.read_csv`·`read_json`·`read_parquet`·`read_excel`·`read_table`, `h5py.File`, `loadmat`, `Image.open`, `cv2.imread`, `ZipFile`, `tarfile.open`의 경로 인자(첫 위치 인자, 없으면 `file`·`path`·`fname`·`filename`·`filepath_or_buffer`·`name`·`fp` 키워드).
  - **보고하지 않는 꼴**: `base / Path(v)`·`base / v`(바로 이음), `os.path.join(base, v)`, `Path(v).name`·`.stem`·`.suffix`·`.suffixes`·`.parts`·`.is_absolute()` 등 이름만 읽는 속성(`.parent`를 거쳐도: `Path(v).parent.name`), `p = Path(v)` 뒤에 `base / p`·`x.joinpath(p)`·`os.path.join(a, p)`로 이은 `p`, 같은 범위에서 `.is_absolute()`·`os.path.isabs`로 검사한 이름·키.
  - **절대 경로 주석**: 여는 줄이나 바로 윗줄 주석에 `absolute`·`abs path`·`절대`가 있으면 warning 대신 `row_value_path_noted`(info). 주석은 주장일 뿐이므로 감사자가 쓰는 쪽(기록 코드)을 확인한다.
  - **오탐 판별법**(감사자가 줄을 읽고 정한다): ① 그 키를 쓰는 코드(러너·기록 함수)가 절대 경로를 저장하는가 — `str(path.resolve())`·`repo_path(...)`·`Path(job["t4h_dir"]) / name`처럼 이은 값을 쓰면 오탐, `path.name`·파일 이름만 쓰면 결함. ② 레코드가 코드 안에서 이은 경로로 방금 만든 dict인가(`located = locate_t4h(...)` 뒤 `np.load(located["path"])`처럼 검색 함수가 절대 경로를 돌려줌) — 그러면 오탐. ③ 실행 위치가 고정된 일회성 스크립트에서 CWD 기준을 일부러 쓰는가 — 판정 경로라면 그래도 결함으로 본다. 판정이 서면 코드에 `base / 값` 또는 `assert Path(v).is_absolute()`를 넣게 권한다(권고는 코드 담당 에이전트 몫).
  - 실데이터(읽기만, 2026-11-21): 보관본 `old/jp3_baseline_compare.py` → 510행 warning(183행 `Path(record['t4h_file']).name`은 조용). 메인 checkout `03_src`·`04_scripts` 1,071파일 → `row_value_path_no_base` 69(약 52 s, 나머지 분류 건수는 `--no-row-paths`와 같음). 눈으로 본 꼴: 러너가 절대 경로를 적는 `case["dir"]`·`job["out_dir"]`(오탐 다수, ①로 판별), 설정 dict `cfg["out"]`, 코드가 만든 dict `located["path"]`(②).

| 분류 | 심각도 | 내용 |
|---|---|---|
| `tag_single_compare` | warning | 태그를 `==`/`!=` 한 값과 비교(새 태그 판에서 0건 선택) |
| `all_without_count_guard` | warning | 가드 없는 함수의 `all(...)` 판정값(`all([])`은 참) |
| `empty_pass_not` | warning | `"pass": not <목록>` / `x["pass"] = not <목록>` |
| `min_default` | info | `min`/`max`에 `default=` |
| `min_or_zero` | info | `min`/`max` 인자 안 `or 0`·`or 0.0` |
| `empty_selection_sum_pass` | warning | 필터 선택의 집계로 분기하고 else·기본이 pass인데 그 선택의 0건 처리가 없음(판정 대상 0개면 pass) |
| `missing_key_default_pass` | warning | 키가 모두 없을 때 조회 기본값 때문에 실패 기록을 건너뛰거나 통과로 감(메시지에 출처 코드·줄과 건너뛴 줄) |
| `missing_key_default` | info | 판정이 조회 기본값을 읽지만 방향을 평가하지 못함 |
| `row_value_path_no_base` | warning | 레코드·행 값을 기준 폴더 없이 경로로 엶(메시지에 식과 키, 이름을 거쳤으면 그 이름·대입 줄, 2026-11-21) |
| `row_value_path_noted` | info | 위와 같은 꼴인데 절대 경로라는 주석이 붙음(주석 앞부분 표시) |
| `warn_and_continue` | info | 경고 뒤 계속 진행 |
| `tag_set_compare` | info | 태그 `in`/`not in` 집합(좋은 패턴, 보고서 표) |
| `count_guard` | info | `len(x) == N`·`== *_COUNT`(좋은 패턴, 보고서 표) |
| `unparsable` | info | 구문 오류 파일 |

JSON 키: `findings[]`에 `function`(`Class.method`, 최상위는 `<module>`), `source`; `target`은 `module:function`. 최상위 `bare_get`(2026-11-20), `row_paths`(규칙을 켰는지, 2026-11-21). `summary{files, functions_scanned, …}`.

호환(2026-11-21): 새 warning 규칙이라 예전에 종료 0이던 파일이 종료 1이 될 수 있다. 예전 결과와 맞춰 보려면 `--no-row-paths`를 붙인다(다른 분류의 건수는 바뀌지 않는다: 메인 checkout 1,071파일로 확인).

## record_check.py — 실행 정체성 (I축)·재집계 (C축)

```powershell
& $py -I -B "$tools\record_check.py" identity "<v5>\las\las_T1.jsonl" --require job.setting,d1.key,commands_sha256 --uniform controller_tag --expect-count 48
& $py -I -B "$tools\record_check.py" identity "<v5_rerun>\u3_slope_V0.json" --meta meta.v5.code.commit
& $py -I -B "$tools\record_check.py" recount "<v5>\las\las_T1.jsonl" --where las.candidate=b0 --count-by d1.verdict --min d1.F_judged_min_N --expect min=10740 --rtol 1e-4
```

로더(`_records.py`):
- `.jsonl`: 빈 줄을 뺀 줄마다 JSON 하나(CRLF/LF, BOM 허용). 깨진 줄은 `record_parse_error`(error).
- `.json`: 리스트, 또는 객체의 `entries`→`records` 순으로 처음 찾은 리스트. 그 객체의 나머지 키는 **파일 메타**(`--meta`가 읽음). 리스트 키가 없으면 객체 하나를 레코드 하나로 본다.
- `.npz`: zip 안 `.npy` 헤더만 읽어 키·shape·dtype을 낸다(배열을 메모리에 올리지 않고 pickle을 풀지 않는다). 재집계 대상이 아니다.
- 점 경로 `a.b.c`는 dict 키를 따라가고 숫자 성분은 리스트 인덱스로도 쓴다.
- `--sample N`: 앞·뒤 N건만 본다(전체 건수는 셈, `sampled` info).

`identity` 인자: `--require a.b,c`, `--uniform a,b`, `--expect-count N`(파일마다), `--tags <점경로> --allowed v1,v2`, `--meta <점경로>`(json 파일 메타), `--sample N`.
- `--tags`와 `--allowed`는 **함께** 준다. 한쪽만 주면 입력 오류(종료 2).
- jsonl·json 입력을 모두 합쳐 레코드가 0건이면 `no_records`(error)다(빈 집합은 통과가 아니다). npz만 준 경우는 레코드 파일이 아니므로 해당하지 않는다.
- `--uniform`은 **모든 파일을 합쳐** 센다. 필드가 일부 레코드에만 있으면 `<없음>`도 하나의 값으로 센다(예: VB 레코드에만 있는 `controller_tag` → 섞임).
- 필수 필드는 없거나 `null`이면 빠진 것으로 센다.

| 분류 | 심각도 | 내용 |
|---|---|---|
| `no_records` | error | 입력 jsonl·json 전체 레코드 0건(파일은 있으나 레코드 없음) |
| `identity_missing` | error | 필수 필드 없는 레코드 수·첫 예시 줄 |
| `identity_mixed` | error | 균일 필드(또는 파일 메타) 고유값 2개 이상 — 값과 개수 |
| `count_mismatch` | error | 파일 레코드 수 ≠ `--expect-count` |
| `tag_not_allowed` | error | `--allowed` 밖 태그(없음 포함) |
| `record_parse_error` | error | 읽을 수 없는 줄·파일 |
| `identity_field_absent` | info | 균일 필드가 모든 레코드에 없음 |
| `keys_first_last_differ` | info | 첫·마지막 레코드 최상위 키 차이 |
| `npz_keys` | info | npz 키·shape·dtype(또는 numpy 없음) |
| `sampled` | info | `--sample`로 일부만 봄 |

`--no-git`(2026-11-10): 두 하위 명령 모두 받는다(하위 명령 앞·뒤 어디든). record_check는 git을 부르지 않으므로 아무 효과가 없고, 다른 도구와 같은 인자를 붙인 감사 명령이 종료 2(`unrecognized arguments`)로 끝나지 않게 하려고 둔다.

`recount` 인자: `--where a.b=값`(여러 번 = AND), `--count-by a.b`, `--min`/`--max`/`--mean a.b`(여러 번 가능), `--expect 라벨=숫자`(여러 번), `--rtol`(기본 1e-9), `--sample N`.
- `--where` 값은 문자열로 비교하고(`true`·`null`은 JSON 표기), 값이 숫자처럼 보이고 필드가 숫자면 숫자로도 비교한다(`12000` = `12000.0`).
- 통계는 숫자(불리언 제외, 유한값)만 쓴다. `null`·문자열은 `non_numeric_skipped`로 센다.
- `--expect` 라벨: `selected`, `count:<값>`(= `count_by:<값>`, `--count-by`의 값별 건수), `min`·`max`·`mean`(그 통계 필드가 하나일 때) 또는 `min:<필드>`. 건수는 정확히, 통계는 `|차이| ≤ rtol·max(|기대|, |재집계|)`. 판정서가 kN·소수 3자리처럼 반올림해 적었으면 단위를 맞추고 `--rtol`을 그 자릿수에 맞춘다(예: 10.740 kN → `min=10740 --rtol 1e-4`).
- 판정 도구 모듈을 import하지 않는다(C축 독립성).

| 분류 | 심각도 | 내용 |
|---|---|---|
| `selection_empty` | error | `--where`로 고른 레코드 0건(빈 집합은 통과가 아니다) |
| `expect_mismatch` | error | 재집계 값 ≠ 기대값(값·기대·차이) |
| `record_parse_error` | error | 읽을 수 없는 줄·파일 |
| `field_absent` | warning | 통계 필드가 고른 레코드 모두에 없음 |
| `non_numeric_skipped` | info | 숫자 아닌 값 제외 건수 |
| `npz_keys`, `sampled` | info | 위와 같음 |

JSON 키: `records`, `selected`, `where[]`, `counts{}`, `stats{"min:<필드>": {field, stat, value, n, non_numeric, absent}}`, `expectations[{label, expected, actual, diff, ok}]`, `files[{path, kind, records, checked, sampled, container_key}]`. identity는 `first_record_keys{}`, `uniform_values{}`, `meta_values{}`.

## replay_recount.py — 재생 대조 재집계 (I·C축, 2026-11-10)

재생 하네스(저장된 결과 줄을 다시 돌려 명령 해시를 비교하는 것, 예: `replay_k1.py`)의 출력 jsonl을 저장 원본 jsonl과 키로 잇는다. 프로젝트 코드를 import하지 않는다.

```powershell
# G-3: K1 재생 457줄 — 하위 묶음 키, 오류 줄 제외, 재시도는 뒤 것(last), 판별 줄 수
& $py -I -B "$tools\replay_recount.py" --replay "<k1sw>\g3.jsonl" `
    --source "<v5>\las\k1\k1_YP.jsonl" "<v5>\las\k1\k1_YS.jsonl" "<v5>\las\k1\k1_YT.jsonl" `
    --replay-key key,sub_bundle --source-key rev.key,k1.sub_bundle `
    --source-where no:error --source-in "k1.sub_bundle=Y-Pa,Y-Pb,Y-Sa,Y-Sb,Y-T" --source-duplicates last `
    --replay-stored-hash stored_hash --count k1.would_block_any --expect selected=457 --expect hash_same=457 `
    --out "$scratch\g3.md"
# G-5a: d1.jsonl의 r4+20(R4 적용 169 + 비R4 앞 20), 이어 돌리기 1부·2부 합치기
& $py -I -B "$tools\replay_recount.py" --replay "<k1sw>\g5a_part1.jsonl" "<k1sw>\g5a_part2.jsonl" `
    --source "<v5>\d1.jsonl" --source-key rev.key --source-key "{job.d1.key}({job.setting!r}, {job.eps!r})" `
    --source-where no:error --select-flagged has:event_names.INFO_LOC_FLAT_SOIL_MARGIN --select-others 20 `
    --replay-stored-hash stored_hash --expect selected=189 --expect flagged=169 --expect hash_same=189 --format json
```

인자:
- `--replay FILE...`(여러 값·여러 번, 모두 합침), `--source FILE...`(jsonl·json, 여러 값·여러 번).
- `--replay-key SPEC`(기본 `key`), `--source-key SPEC`(필수). 여러 번 주면 **대체 순서**다: 앞 SPEC이 풀리지 않는 줄(필드 없음·`null`·`""`)은 다음 SPEC을 쓴다(하네스의 `a or b`). SPEC 형식:
  - `rev.key` — 점 경로 하나, `rev.key,k1.sub_bundle` — 여러 필드 = 튜플 키(양쪽 필드 수가 같아야 이어진다)
  - `{job.d1.key}({job.setting!r}, {job.eps!r})` — 틀. `{경로}`는 값 글자(문자열 그대로, 그 밖은 JSON), `{경로!r}`는 JSON 값의 Python `repr`(`'VB'`, `0.002`, `0.0`) — `str((setting, eps))`로 만든 키를 그대로 재현한다.
- `--replay-hash FIELD`(기본 `hash`), `--replay-stored-hash FIELD`(재생 기록에 들어 있는 저장 해시 사본, 선택), `--source-hash FIELD`(기본 `commands_sha256`).
- 원본 필터: `--source-where PRED`(여러 번 = AND), `--source-in FIELD=V1,V2,...`(값 중 하나, 여러 번 = AND). 필터 뒤 키 중복은 `--source-duplicates error|last|first`(기본 `error`; `last`는 뒤 시도가 이기고 위치는 처음 것 — `dict` 대입과 같다).
- 선택 규칙: `--select-flagged PRED`(조건 맞는 원본 전부) + `--select-others N`(조건 안 맞는 원본 중 원본 순서로 앞 N개). 둘 다 없으면 필터 뒤 원본 전부. `r4+20` = `--select-flagged has:event_names.INFO_LOC_FLAT_SOIL_MARGIN --select-others 20`.
- 판별: `--count PRED`(선택된 원본에서), `--count-replay PRED`(재생 기록에서), 여러 번.
- `--replay-error-field FIELD`(기본 `error`, 값이 참이면 재생 실패), `--expect LABEL=건수`(여러 번), `--no-git`(효과 없음, 공통 계약용), `--out`, `--format`, `--fail-on`.

PRED(조건) 형식: `경로`(참: JSON 값이 `null`·`false`·`0`·`""`·`[]`·`{}`가 아님), `not:경로`(거짓 또는 없음), `has:경로`(있음), `no:경로`(없음), `경로=값`(같음, 숫자는 숫자로도 비교 `12000` = `12000.0`).

`--expect` 라벨: `replay_records`(재생 파일 줄 수 합), `replayed`(키 있는 재생 기록, 중복 제외), `source_records`, `source_filtered`, `source_unique`, `selected`, `flagged`, `others`, `matched`(원본에 있는 재생 키), `hash_same`, `count:<PRED>`, `replay_count:<PRED>`. 건수는 정확히 비교한다. 라벨 안의 `=`는 마지막 `=`에서 나눈다(`count:k1.sub_bundle=Y-Pa=40`). 선언하지 않은 `count:` 조건, 모르는 라벨, 숫자가 아닌 기대값은 종료 2.

종료 코드는 공통 계약 그대로다: 0 일치, 1 불일치(발견), 2 입력·인자 오류(파일 없음, 형식, `--out` 위치 포함), 3 내부 오류. 줄 단위 JSON 깨짐은 2가 아니라 `record_parse_error`(error, 종료 1)다.

| 분류 | 심각도 | 내용 |
|---|---|---|
| `selection_missing` | error | 선택 규칙이 고른 원본 키가 재생에 없음 |
| `replay_not_selected` | error | 원본(필터 뒤)에 있지만 선택 규칙 밖인 재생 키 |
| `replay_key_unknown` | error | 원본(필터 뒤)에 없는 재생 키 |
| `replay_key_duplicate` | error | 재생 키가 두 번 이상(부분 파일 사이 포함, 첫·둘째 위치 표시) |
| `replay_key_missing` / `source_key_missing` | error | 키 SPEC이 모두 풀리지 않는 줄(원본은 필터 뒤 줄만) |
| `source_key_duplicate` | error | 필터 뒤 원본 키 중복(`--source-duplicates error`, 처음 것을 쓴다) |
| `hash_mismatch` | error | 재생 해시 ≠ 원본 해시(앞 12자 표시) |
| `stored_hash_mismatch` | error | 재생 기록의 저장 해시 사본 ≠ 원본 해시(재생이 다른 원본 판을 읽음) |
| `hash_missing` | error | 어느 쪽 해시가 없거나 `null`(쪽 표시) |
| `replay_error` | error | 재생 기록의 `--replay-error-field` 값이 참 |
| `replay_empty` / `selection_empty` | error | 재생 기록 0건 / 선택된 원본 0건(빈 집합은 일치가 아니다) |
| `expect_mismatch` | error | 재집계 건수 ≠ `--expect` |
| `record_parse_error` | error | 읽을 수 없는 줄 |
| `source_key_duplicate_resolved` | info | `last`·`first` 정책으로 줄인 원본 중복 건수 |
| `replay_parts` | info | 재생 파일 2개 이상을 합침(파일별 건수) |

JSON 키: `files[{role(replay·source), path, records}]`, `replay_key[]`, `source_key[]`, `numbers{replay_records, replayed, source_records, source_filtered, source_unique, selected, flagged, others, matched, hash_same}`, `counts{<PRED>: n}`, `replay_counts{<PRED>: n}`, `expectations[{label, expected, actual, ok}]`, `problems{<분류>: [키 …]}`(목록형 발견의 전체 키), `summary`, `findings`. 마지막 줄 요약에는 `numbers`·`counts`·`replay_counts`가 그대로 들어간다. md 보고서는 분류마다 키를 30개까지 보인다.

실데이터 확인(2026-11-10, K1 전환 감사 증거 `.local_archive\session_9d4aec18_20261110\k1sw\` ↔ 현재 `06_analysis\03_hydraulic\coupled\v5\`): G-3 457/457(원본 458줄 중 오류 1줄 제외, `k1.would_block_any` 8), G-4 70/70(k1_Y0 105줄 중 Y-0c·Y-0d, `would_block_any` 1), G-5a 189/189 = R4 169 + 비R4 20(d1.jsonl 868줄, 1부 40 + 2부 149), G-5b 21/21 = R4 1 + 20(revA_RP0 149줄). 모두 종료 0, `hash_same` = 선택 수.

## timeline.py — 시간 순서 (T축)

```powershell
& $py -I -B "$tools\timeline.py" --rules "<규칙 폴더>\las_targeted_rules.md" --results "<v5>\las\las_T1.jsonl"
& $py -I -B "$tools\timeline.py" --rules "<v5>\v5_criteria.md" --results "<v5>\main.jsonl" --time-field run.started_at --format json
& $py -I -B "$tools\timeline.py" --repo "<프로젝트>" --rules docs/processing/preregistration_x_v1.md --results "docs/processing/x_summary.csv" docs/processing/x_judgement.md --out "$scratch\timeline.md"
```

인자: `--rules RULE...`(원판, 개정판은 seal_check와 같은 규칙으로 자동 수집), `--results FILE_OR_GLOB...`, `--repo DIR`(상대 경로·글롭의 기준, 기본 현재 폴더, 2026-11-11), `--revs auto|none`, `--sha-dir DIR`(상대면 `--repo` 기준), `--time-field <점경로 | csv 열 이름>`, `--no-git`, `--out`, `--format`, `--fail-on`.

결과 형식(2026-11-11 확장): `.jsonl`·`.json`·`.npz`는 레코드(`--time-field` = 점경로), `.csv`는 표(`--time-field` = 열 이름, 빈 칸 제외), `.md`·`.txt`는 문서(레코드 없음 — git 첫 추가 커밋과 mtime만, `--time-field`를 주면 `time_field_not_applicable` info). 그 밖의 확장자와 없는 파일·0개 글롭은 종료 2. 결과마다 최초 시각과 그 근거(`field:<이름>`·`git`·`mtime`)를 `results[].earliest`·`earliest_basis`와 md 표 "최초(근거)" 열에 적는다.

반복 인자(2026-11-10 수정, seal_check `--hash-files`와 같은 방식): `--rules`·`--results`는 `--rules a b`와 `--rules a --rules b` 모두 **전부 합친다**(`action="extend"`). 이전에는 여러 번 주면 마지막 것만 남았다(argparse last-wins). 같은 파일을 두 번 주면 한 번만 비교한다(경로 대소문자 무시).

판정 규칙:
- 규칙 시각은 `.sha256`의 `sealed <시각>` → git 첫 추가 커밋(`%cI`) → 파일 앞 40줄의 `봉인(YYYY-MM-DD)`·`작성: …, YYYY-MM-DD` 순으로 처음 있는 것. 머리 날짜는 **날짜 단위**로 비교한다.
- 결과 최초 시각은 `--time-field` 최솟값(ISO 8601 문자열 또는 10⁹ 이상의 epoch 초), git 첫 추가 커밋, mtime 중 **가장 이른 것**.
- 오프셋이 없는 시각은 naive로 두고, 오프셋이 있는 시각과 비교할 때만 로컬 시간대로 읽으며 `basis`에 `[로컬 시간대로 비교]`를 붙인다(+09:00을 가정하지 않는다).
- 결과 뒤 개정 선언: `.sha256` 메모나 개정판 본문에 `AFTER`(대문자), `after seeing`, `결과를 본 뒤`, `결과 뒤`, `결과를 보고`가 있으면 선언으로 본다.

| 분류 | 심각도 | 내용 |
|---|---|---|
| `rule_after_results` | error | 원판 시각 > 결과 최초 시각 |
| `rev_after_results` | warning | 개정판이 결과 뒤인데 선언 없음 |
| `seal_time_missing` | warning | `.sha256`에 봉인 시각이 없음(또는 `.sha256` 없음) |
| `rev_after_results_declared` | info | 개정판이 결과 뒤이고 그렇다고 밝힘 |
| `mtime_only_basis` | info | 결과 최초 시각의 근거가 mtime `[추정]`. 커밋 전에 쓴 파일은 mtime이 커밋보다 이르므로 정상적으로도 나온다 |
| `time_field_not_applicable` | info | `--time-field`를 줬는데 결과가 md·txt(레코드 없음) |
| `git_unavailable` | info | `--no-git`, git 없음, 저장소 밖 |

JSON 키: `repo`, `rules[{path, rev, sealed_at, git_added_at, header_date, declares_after}]`, `results[{path, kind(records·table·document), mtime, git_added_at, field_min, field_max, earliest, earliest_basis}]`, `comparisons[{rule, rev, result, rule_time, rule_basis, result_time, result_basis, verdict}]`(`verdict` ∈ `before`·`after`·`unknown`), `git`.

## log_errors.py — 단계 로그 오류 수 (E·I축, 2026-11-11)

하네스가 실패 사례를 오류 행으로 남기고 `errors N`만 찍은 뒤 종료 코드 0으로 끝나면 rc 검사로는 보이지 않는다(K-2 V-3, 2026-11-10: `acc_d8.py` `errors 48`, rc 0, 약 4시간 진행). 실행 중 점검과 판정 전 점검에 쓴다.

```powershell
& $py -I -B "$tools\log_errors.py" "<scratchpad>\sched\logs" --out "$scratch\log_errors.md"
& $py -I -B "$tools\log_errors.py" "<logs>\P_main" "<logs>\P_post\v5_judge.log" --require-line --format json
```

인자: `INPUT...`(러너 로그 폴더 또는 `.log` 파일), `--glob`(폴더 안 글롭, 기본 `**/*.log`), `--pattern`(캡처 그룹 1개 = 오류 수, 기본 `\berrors\s*[:=]?\s*(\d+)\b`), `--require-line`, `--out`, `--format`, `--fail-on`.
- 단계 = `.log` 파일 하나(단계 이름은 입력 폴더 기준 상대 경로에서 확장자를 뺀 것). 로그 안의 모든 일치를 센다. 단계 값은 마지막 일치(마지막 요약 줄)이고 최대값도 낸다. **0보다 큰 일치가 하나라도 있으면 발견**이다.
- 같은 이름의 `.done`(러너가 쓰는 `… exit=0 wall_s=…`)이 있으면 그 줄과 `exit=` 값을 붙인다. `exit=0`인데 오류가 있으면 메시지에 `.done exit=0`이 보인다.
- 로그 파일이 하나도 없으면 종료 2(빈 선택은 통과가 아니다). 일치가 없는 로그는 "오류 0"이 아니라 `no_errors_line`이다.

| 분류 | 심각도 | 내용 |
|---|---|---|
| `log_errors_nonzero` | error | `errors N`, N > 0 (일치한 줄마다 하나) |
| `no_errors_line` | info (`--require-line`이면 warning) | 로그에 `errors N` 줄이 없음 |

JSON 키: `pattern`, `glob`, `steps[{step, log, matches[{line, count}], done_exit, done_line, last_count, max_count}]`, `summary{logs, steps_with_errors, steps_without_line, error_rows_total(단계별 마지막 값의 합), …}`, `findings`.

실데이터 확인(2026-11-11, K-2 러너 로그 72개): `steps_with_errors` 12(V-3 L1eq 계열 6팔 × 2팔, 각 48), `error_rows_total` 576 — 판정 후 감사의 576행과 같다. `no_errors_line` 42(V-5 회귀·G8·V-6 등 `errors` 줄을 찍지 않는 단계).

## placeholder_scan.py — 채워지지 않은 자리표시 (I축, 2026-11-11)

실행 전 기록·manifest에 "시작 뒤 채운다"고 남긴 `{NAME}` 자리가 그대로면 판정 경로가 끊긴다(K-2: manifest `{BATCH_V7}` → `record-v7` `file not found`). 판정 전 점검에 쓴다.

```powershell
& $py -I -B "$tools\placeholder_scan.py" --repo "<프로젝트>" "06_analysis/02_control/k2/prelaunch/*.json" `
    "06_analysis/02_control/k2/prelaunch/*.md" --allow MASK WORKERS POOL --out "$scratch\placeholders.md"
```

인자: `INPUT...`(파일 또는 글롭, `--repo` 기준), `--repo DIR`(기본 현재 폴더), `--allow NAME...`(남아도 되는 템플릿 자리, `MASK`·`{MASK}`·`<MASK>` 모두 됨, 반복 누적), `--pattern-set brace|angle|both`(기본 `brace`, 2026-11-21), `--pattern REGEX`(묶음 대신 쓸 정규식. `--pattern-set`과 함께 주면 종료 2), `--out`, `--format`, `--fail-on`.
- **기본 패턴은 숫자를 허용한다.** 감사 리포트의 `\{[A-Z_]+\}`는 `{BATCH_V7}`(숫자 7)을 놓친다(2026-11-11 실측).
- 패턴 묶음(2026-11-21): `brace` = `\{[A-Z][A-Z0-9_]*\}`(기본, 예전 기본 패턴과 같다), `angle` = `<[^\W\d][^<>"\n]{0,120}>`, `both` = 둘을 `|`로 이은 것. 인자 없이 실행하면 예전과 같은 결과다.
  - `angle`은 `<` 다음이 글자나 `_`(한글 포함)이고 안에 `<`·`>`·`"`·줄바꿈이 없는 토큰이다. 요청 예시 `<[A-Za-z_][^>]*>`와 달리 한글로 시작하는 `<실행 커밋>`도 잡고, `a<b <name>`이 한 토큰으로 붙지 않으며, 한 줄 JSON의 두 문자열(`"a<b", "c>d"`)을 잇지 않는다. 닫는 태그 `</td>`·주석 `<!-- -->`·PowerShell `<# #>`·비교 `x < y`는 처음부터 맞지 않는다.
  - 건너뛰는 것(`skipped`, 발견이 아님): 자동 링크 `<https://…>`·`<mailto:…>`·`<a@b.c>`(모든 파일), md의 **코드 펜스·인라인 코드 밖** 배치용 HTML 태그(`br`·`hr`·`sup`·`sub`·`b`·`i`·`u`·`em`·`strong`·`kbd`·`details`·`summary`·`div`·`span`·`p`·`img`·`a`·`table`·`tr`·`td`·`th`·`ul`·`ol`·`li`·`code`·`pre`·`small` 등, 따옴표 없는 속성 허용 `<img src=a.png>`. 따옴표 속성 `<img src="a.png">`는 `"` 때문에 처음부터 토큰이 아니다). 자리표시로도 읽히는 `head`·`time`·`data`·`path`·`input`·`output`·`source`·`title`·`label`은 일부러 목록에서 뺐다(`<head>`는 보고). 코드 펜스(```` ``` ````·`~~~`)와 백틱 안은 명령이 사는 곳이라 `<br>`도 보고한다.
  - `--pattern`(사용자 정규식)에는 이 건너뛰기를 적용하지 않는다(예전 동작 그대로).
  - md 문서 자체(감사 보고·README)는 설명용 `<이름>`이 많다. 실행 자료(run_steps·명령 json·ps1)만 입력으로 준다.
- 줄마다 모든 일치를 센다(줄·열). `.json`이 파싱되면 그 토큰을 담은 문자열의 JSON 경로(`$.v7.rows.<case>.row_json`)를 붙인다. 파싱이 안 되면 줄 위치만 낸다.
- 맞는 파일이 0개인 글롭은 종료 2.
- 명령 템플릿(`k2_commands.json`의 `{MASK}`·`{WORKERS}`·`{POOL}`)처럼 일부러 남긴 자리는 `--allow`로 info로 돌린다. 무엇을 허용할지는 감사자가 정한다.

| 분류 | 심각도 | 내용 |
|---|---|---|
| `placeholder_unfilled` | error | 허용 목록에 없는 자리표시 |
| `placeholder_allowed` | info | `--allow`에 있는 자리표시 |

JSON 키: `pattern`(쓴 정규식), `pattern_set`(`brace`·`angle`·`both`·`custom`, 2026-11-21), `allow`, `files`, `matches[{file, line, column, token, allowed, json_paths}]`, `skipped[{file, line, column, token, reason}]`(`reason` ∈ `html_tag`·`autolink`, 2026-11-21), `summary{files, unfilled, allowed, tokens{토큰: 수}, skipped, …}`, `findings`.

실데이터 확인(2026-11-11, K-2 `prelaunch/*.json` + `prelaunch/sched/*.json` 22개): `{BATCH_V7}` 13, `{JUDGE_COMMIT}` 6, `{RUN_HEAD}` 2, `{PLAN_ID}` 1, 템플릿 자리 `{MASK}` 157·`{WORKERS}` 81·`{POOL}` 68·`{L2B_WORKERS}` 5·`{PLACEMENT}` 5·`{P}` 2.

실데이터 확인(2026-11-21, 436.9 J-P3 `prelaunch_j9/**/*.md`·`*.ps1` + `j4a_remedy_fa997f4c/**/*.json` 21파일, `--pattern-set both`): run_steps ps1·records json은 0건. 보고 31건은 모두 README·감사 보고 md의 설명용 자리(`<prelaunch>`·`<judge_sha256 of P-1a>`·`<실행 커밋>`·`<worktree coupled>` 등)였고 `skipped` 0. 기본(`brace`)은 `{NAME}` 1건(감사 보고의 설명 문장)으로 예전과 같다.

```powershell
# 실행 자료의 <name> 자리 (명령 json·ps1·run_steps md)
& $py -I -B "$tools\placeholder_scan.py" --repo "<프로젝트>" "<prelaunch>/run_steps/*.ps1" "<prelaunch>/*.json" `
    --pattern-set both --allow MASK --out "$scratch\placeholders_angle.md"
```

## key_presence.py — 필수 키 존재 (I축, 2026-11-21)

판정이 `row.get(key) or 0`처럼 읽으면 키가 없는 행이 "0건"이 된다(`gate_scan`의 `missing_key_default_pass`). 판정 전에 판정이 읽을 키가 **모든 대상 행에 있는지**를 센다(436.9 J-P3 실행 전 감사가 `hydraulics_record.relock_step_over_1bar_count`·`lock_window_alignment.n_late_fallback`를 즉석 스크립트로 확인한 일을 도구로 옮겼다).

**판정 결과 블라인드를 지키는 도구다.** 필수 키는 "있는가, 값이 null인가"만 묻고 값을 출력·저장·집계하지 않는다. 보고서·stdout에는 키 이름, 건수, 빠진 행의 위치(줄 번호·항목 번호)만 나온다. 그래서 판정 전에 보면 안 되는 결과 파일에도 쓸 수 있다. `--where`는 자기 필드를 명령줄 값과 비교하는 데만 읽고 출력하지 않는다 — **판정값 필드로 거르지 않는다**(거른 행 수가 판정값을 드러낸다).

```powershell
& $py -I -B "$tools\key_presence.py" --repo "<프로젝트>" "<결과 폴더>/run_v5*.jsonl" `
    --key hydraulics_record.relock_step_over_1bar_count,lock_window_alignment.n_late_fallback --where job.setting=VBJ --out "$scratch\keys.md"
& $py -I -B "$tools\key_presence.py" "<판정 폴더>\judge.json" --keys-file "$scratch\judged_keys.txt" --list-key results --format json --out "$scratch\keys.json"
```

인자: `INPUT...`(jsonl·json 파일 또는 글롭, `--repo` 기준, 0개 글롭은 종료 2), `--key a.b,c`(여러 번, 쉼표 구분), `--keys-file FILE`(한 줄에 키 하나, `#` 주석, 쉼표 허용), `--repo DIR`, `--list-key a.b`(행 목록의 점 경로: json 문서, 또는 jsonl의 **각 줄** 안), `--where a.b=값`(여러 번 = AND, `record_check --where`와 같은 비교: 글자 그대로 또는 같은 수), `--allow-null`, `--out`, `--format`, `--fail-on`.
- 행: `.jsonl`은 빈 줄을 뺀 줄마다 하나. `.json`은 최상위 리스트, 또는 최상위 객체의 `results`→`entries`→`records`→`rows` 중 처음 찾은 리스트(`container_key`로 보고), 그런 리스트가 없으면 문서 하나가 한 행. `--list-key`를 주면 그 리스트의 항목이 행이다(json에서 그 경로가 리스트가 아니면 종료 2, jsonl에서 그 경로가 없는 줄은 `list_key_absent`).
- 키는 점 경로(`a.b.c`, 숫자 성분은 리스트 인덱스로도). 점이 든 키 이름은 다룰 수 없다.
- 값이 `null`인 키는 기본으로 **없음**으로 센다(`record_check identity`와 같다). `--allow-null`이면 있음으로 센다. 없음(`absent`)과 null은 따로 센다.
- `--where` 필드가 없는 행은 고르지 않고 `where_field_absent`(info)로 센다.
- 종료 코드: 0 = 고른 모든 행에 모든 키가 있음, 1 = 빠진 행 있음(또는 행 0개·선택 0개·읽을 수 없는 줄 — 빈 집합은 통과가 아니다), 2 = 입력 오류(키 없음·점 경로 아님·`--where` 형식·지원하지 않는 형식·`--list-key` 불일치·`--out` 위치), 3 = 내부 오류.

| 분류 | 심각도 | 내용 |
|---|---|---|
| `key_absent` | error | 키가 없는 행 수/대상 행 수(처음 5개 위치) |
| `key_null` | error | 키는 있는데 값이 null인 행 수(`--allow-null`이면 내지 않음) |
| `no_rows` | error | 파일에 행 0개 |
| `selection_empty` | error | `--where`로 고른 행 0개 |
| `record_parse_error` | error | JSON으로 읽을 수 없는 줄·파일 |
| `list_key_absent` | error | `--list-key` 목록이 없는 jsonl 줄 수 |
| `where_field_absent` | info | `--where` 필드가 없어 빠진 행 수 |

JSON 키: `keys_required[]`, `where[]`, `list_key`, `allow_null`, `keys[{key, present, absent, null, missing, first_missing[]}]`(전체 합), `files[{path, container_key, rows, selected, where_field_absent, parse_errors, list_key_absent, keys[…]}]`, `summary{files, rows, selected, keys, keys_complete, keys_incomplete, …}`, `findings`. `first_missing`은 `<파일 이름> 줄 N`(jsonl), `줄 N #k`(jsonl 줄 안 목록), `항목 #k`(json).

실데이터 확인(2026-11-21, 읽기만): `baseline_221456d/*.jsonl` 3파일 18행, 키 4개 → `hydraulics_record.relock_step_over_1bar_count`가 `j9_cases.jsonl` 15행 중 5행에 없음(종료 1, 0.13 s). 나머지 3키는 18/18.

### npz 배열 (2026-11-21)

사건: 436.9 단계 (6)의 판정은 T4h의 per-read `jp3_*` 배열을 읽었는데, r79 경로의 T4h에는 그 배열이 처음부터 없었다. 실행 전에 이것을 본 검사가 없었다. 그래서 실행 전 감사에서 **판정이 읽을 T4h 배열이 실제(건식) 출력에 있는지**를 이 도구로 본다.

```powershell
& $py -I -B "$tools\key_presence.py" --npz-dir "<건식 출력>\VBJ_t4h" --npz-dir "<건식 출력>\VBH_t4h" `
    --array jp3_t_s,jp3_class,jp3_class_names,jp3_used_bound_Pa,jp3_p_tr_Pa --out "$scratch\arrays.md"
& $py -I -B "$tools\key_presence.py" "<건식 출력>/r79_*.json" --key hydraulics_record.rod_reading_truth_calls `
    --npz-dir "<건식 출력>\VBJ_t4h" --arrays-file "$scratch\judged_arrays.txt"   # 행 키와 배열을 한 번에
```

- 인자: `--npz-dir DIR`(여러 번, 비재귀), `--npz-glob`(기본 `*.npz`), `--array a,b`(여러 번), `--arrays-file FILE`(한 줄에 이름 하나, `#` 주석). 행 파일(`INPUT…` + `--key`)과 함께 줄 수 있다. 둘 중 하나는 있어야 하고, 각각 짝(`INPUT`↔`--key`, `--npz-dir`↔`--array`)이 맞아야 한다(아니면 종료 2).
- **값을 읽지 않는다.** `zipfile`로 zip 항목 이름만 나열한다(`numpy.savez`는 배열 `name`을 `name.npy`로 넣는다). 배열을 메모리에 올리지 않고 numpy도 쓰지 않는다.
- 없는 폴더, 맞는 파일이 0개인 폴더는 **종료 2**다(빈 폴더는 통과가 아니다).
- 분류: `npz_array_absent`(error, 파일마다 빠진 배열 이름), `npz_unreadable`(error, zip으로 열 수 없음). 요약 키: `npz_files`, `arrays`, `arrays_incomplete`. JSON `npz{glob, dirs[], arrays_required[], arrays[{array, present, absent, first_missing[]}], files[{path, readable, missing[]}]}`.
- 시험 픽스처: r79 꼴 T4h(`t_s`·압력·`meta_json`만, `jp3_*` 없음) 2개와 하네스 꼴 T4h 1개(`jp3_*` 있음). 결과는 r79 쪽 `npz_array_absent` 2(종료 1), 하네스 쪽 0이다. 배열 값은 stdout에 나오지 않는다. 전체 시험은 2026-11-21 기준 253개 중 252 passed다. 실패 1건 `test_ref_check.py::test_real_spec_names_dg3_hash_as_first_candidate`는 실데이터 시험이다. 저장소에 `l1_keys*` 파일이 새로 생기면서 후보 순위가 바뀌어 실패했고, 이번 변경과는 관계없다.

## threshold_boundary.py — 반올림 저장과 문턱 경계 (C축, 2026-11-15)

결과 CSV가 점수를 소수 `d`자리로 반올림해 저장하면, 표기값 `0.25`인 박스가 `conf > 0.25`를 통과했는지 CSV만으로는 다시 셀 수 없다. 참값은 `[0.25 − h, 0.25 + h]`(`h = ½ulp = 0.5·10^−d`) 어디든 될 수 있다(gpr_detection M3-3 D0 판정 후 감사, 2026-11-15). CSV로 재집계하기 전, 판정 후 감사에서 쓴다.

```powershell
& $py -I -B "$tools\threshold_boundary.py" --repo "<프로젝트>" "<결과 폴더>/*_boxes.csv" `
    --score conf --threshold 0.25 --op ">" --group-by fold condition set class --out "$scratch\boundary.md"
& $py -I -B "$tools\threshold_boundary.py" "<결과>\fold_*.csv" --score score --threshold 0.5 --op ge `
    --decimals 4 --group-by "@file" --format json --out "$scratch\boundary.json"
```

인자: `INPUT...`(CSV 파일 또는 글롭, `--repo` 기준), `--score COLUMN`(필수), `--threshold T`(필수, 10진수로 정확히 읽음), `--op`(필수, `>`·`>=` 또는 셸 리디렉션을 피하는 `gt`·`ge`. PowerShell에서는 `">"`처럼 따옴표), `--decimals N|auto`(기본 `auto`), `--group-by COLUMN...`(판정 단위 열, 반복 누적, `@file` = 그 파일), `--repo DIR`, `--delimiter CHAR`(기본 `,`), `--max-listed N`(md에 적는 모호 행 수, 기본 200; JSON은 전부), `--out`, `--format`, `--fail-on`.
- 값은 `Decimal`로 읽는다(float 변환 없음). 빈칸·글자·`nan`·`inf`는 해석 불가로 세고 집계에서 뺀다. 빈 줄은 건너뛴다. 줄 번호는 CSV 레코드가 끝나는 물리 줄이다.
- **자릿수 `auto`는 파일별로 그 점수 열에 찍힌 소수 자릿수의 최댓값**이다. 기록기가 끝의 0을 지우므로(`0.3` = `0.3000`) 값마다의 자릿수를 쓰지 않는다. 분포는 `decimals_estimated` info와 JSON `fraction_digits`에 남는다. 15자리 이상이면 반올림 없이 저장했을 가능성이 크다(`full_precision` info).
- **모호 = |표기값 − 문턱| ≤ h(닫힌 구간)**. 모호하지 않은 행은 표기값으로 판정이 정해진다. 단위별로 `pass_displayed`(표기값을 참값으로 본 통과 수 — CSV 재집계가 내는 값), `pass_excluding_ambiguous`(모호 행이 모두 탈락), `pass_including_ambiguous`(모두 통과), `difference`(= 모호 수)를 낸다. `--op`는 통과 수만 바꾸고 모호 판정은 바꾸지 않는다.
- 문턱의 소수 자릿수가 `d`보다 많으면(예: 문턱 0.255, `d` = 2) 표기값이 문턱과 달라도 구간에 든다(`threshold_finer` info, 0.25·0.26 둘 다 모호).
- 맞는 파일이 0개인 글롭, 점수 열·단위 열이 없는 파일, 숫자 점수가 한 행도 없는 입력, 잘못된 문턱·`--op`·`--decimals`·`--delimiter`, 입력 폴더 안의 `--out`은 종료 2. 헤더만 있는 파일은 다른 파일에 행이 있으면 `empty_file` warning.

| 분류 | 심각도 | 내용 |
|---|---|---|
| `boundary_rows` | error | (파일, 판정 단위)마다 모호 행 수·그중 표기값 = 문턱 수, 첫 행 줄 번호 |
| `score_unparsable` | warning | 점수를 숫자로 읽지 못한 행(파일마다 하나, 첫 줄) |
| `decimals_below_data` | warning | `--decimals`보다 소수 자릿수가 많은 값이 있음(지정이 데이터와 모순) |
| `empty_file` | warning | 데이터 행이 없는 파일 |
| `decimals_estimated` | info | `auto` 추정 자릿수와 소수 자릿수별 행 수 |
| `full_precision` | info | 자릿수 15 이상 |
| `threshold_finer` | info | 문턱 자릿수 > 표기 자릿수 |

종료 코드: 모호 행이 있으면 1(error). 모호 행이 없어도 warning이 있으면 기본 `--fail-on warning`에서 1이고, `--fail-on error`면 0이다.

JSON 키: `score_column`, `threshold`, `op`, `group_by`, `decimals`(`auto` 또는 지정값), `files[{path, label, rows, unparsable, decimals, decimals_source(auto·given), fraction_digits{자릿수: 행 수}, half_ulp, ambiguous, equal}]`, `units[{unit{열: 값}, label, rows, pass_displayed, ambiguous, equal, pass_excluding_ambiguous, pass_including_ambiguous, difference}]`(숫자 값은 값 순: fold 2가 10보다 앞), `boundary_rows[{file, line, unit, value, equal}]`, `summary{files, rows, unparsable, equal, ambiguous, units, units_with_ambiguous, …}`, `findings`.

## judgement_checklist.py — 판정서 지시 대조 (판정 뒤)

```powershell
& $py -I -B "$tools\judgement_checklist.py" --repo "<프로젝트>" `
    --rules "06_analysis/02_control/verif_matrix/fb_targeted_rules*.md" `
    --judgement "06_analysis/02_control/verif_matrix/fb_judgement.md" --out "$scratch\fb_checklist.md"
& $py -I -B "$tools\judgement_checklist.py" --repo "<프로젝트>" --rules "<규칙 폴더>/las_phase_diag_plan*.md" `
    --judgement "<규칙 폴더>/las_phase_diag_judgement.md" --format json --out "$scratch\las_checklist.json"
```

인자: `--rules RULE...`(원판·`_rev<N>` 판 `.md` 또는 글롭, 여러 번 줄 수 있음), `--judgement DOC...`(판정서, 글롭 허용, 여럿이면 합쳐서 찾음), `--repo DIR`(상대 경로·글롭 기준, 기본 현재 폴더), `--out`, `--format`, `--fail-on`.
- 판은 seal_check와 같은 규칙으로 묶는다(`<stem>_rev<N>[a-z].md` 숫자 순). `--revs`는 없다 — 준 파일만 읽는다(글롭 `x_rules*.md`가 원판·개정판을 다 고른다). **맞는 파일이 0개인 글롭은 종료 2.**

추출 규칙(보수적: 놓치느니 ambiguous):
- **지시 절**: 수준 2 이상 제목이 `판정서에 적을|적는|기록|남길`·`판정서 기록`이면 강한 절, `공개`·`사후 관찰`이면 약한 절. 다음 같은 수준 이하 제목까지의 목록 항목(들여쓴 이어짐 줄 포함)·표 데이터 줄·인용(`>`) 줄·일반 줄이 **각각 한 항목**이다. 수준 1 제목(문서 제목)은 절을 열지 않는다. 코드 블록·표 머리·구분 줄은 건너뛴다.
- 약한 절의 항목은 항목 자체가 판정서를 지시하면(아래 강한 문장) 강한 항목이 된다. 약한 절(공개)에는 다음 판에 대한 절차(예: "덧붙임 판에는 다음을 적는다")도 섞여 있어서다.
- **문장 지시**(지시 절 밖): 문장(표는 칸 단위)에 `판정서` + 기록 동사가 80자 안에 있으면 강한 항목, `공개`·`사후 관찰`만 있으면 약한 항목. 기록 동사: `적는·적을·적고·적어·적었·기록·요약·남긴·남기·쓴다`, 2026-11-15부터 `싣(싣는다·싣고·싣되)·실어·실을·실린·실었`, `보인다·보이고·보여·보일`, `밝힌·밝히·밝혀·밝힐`, `넣는·넣고·넣어·넣을`, `첨부`, 2026-11-16부터 `공개한·공개하·공개해·공개할`("판정서에 공개한다"는 전에는 약한 항목이었다). 이전에는 "판정서에 표로 싣고", 조건부 "그 행과 사유를 판정서 표에 싣고", "판정서에 두 목록이 같음을 보인다"를 놓쳤다(436.8 rev22 22·58·69·70·79행, rev23 91·103행. 같은 꼴의 rev23 90행은 같은 줄에 `적는다`가 있어서 뽑혔고 91행은 `싣고`뿐이라 빠졌다 — 중복 제거 때문이 아니다). 그 문장에 토큰이 없으면 둘러싼 항목(목록 항목·표 칸)의 토큰을 빌린다(`scope: context`).
- **앞 목록 빌리기**(2026-11-16): 문장 지시에 자기 토큰도 둘러싼 항목의 토큰도 없으면 **바로 앞 목록**의 토큰을 빌린다(`scope: preceding`). 목록 항목이면 같은 들여쓰기의 바로 앞 형제 항목과 그 하위 항목 전부(부모 항목에 닿으면 멈춤), 일반 줄이면 바로 위 목록 덩어리 전체. 같은 절(제목) 안에서만 빌린다. 예: rev16:64 "면제 사실과 대체 점검 결과는 판정서에 공개한다"는 59~63행(11.2 항목과 H-11·H-12·C-9~C-11 하위 항목)을 빌리고, 58행(11.1)은 빌리지 않는다. 판 해시 토큰이 더해지면(`sha256` 언급) `scope`는 `sentence`가 된다.
- **사전 예측 줄**(2026-11-16): `[참고] 사전 예측 P-n`(`**[참고]**`, `P-a·P-b`, `P-a~P-b` 범위는 30개까지 펼침)이 있는 줄은 어디에 있든 강한 항목(`origin: prediction`)이다. 토큰은 P-n마다 `label`(P-n 언급)과 `prediction`(**같은 판정서 줄에 P-n과 대조 낱말** `맞음·맞았·맞다·틀림·틀렸·틀리다·적중·빗나·부분 맞음·대조 불가·판정 불가·미확인`). 예측 문장의 `sha256`은 예측 내용이라 판 해시 토큰을 더하지 않는다. `[참고] 사전 예측: 하지 않는다.`처럼 P-n이 없는 줄은 예측 항목이 아니다.
- 강한 항목 바로 뒤의 인용 줄(`>`, "다음 문구를 적는다")은 줄마다 강한 항목이다.
- 토큰: 백틱 코드(64hex면 해시, `<n>` 같은 틀·`.sha256`처럼 `.`로 시작·3자 미만은 뺌, 끝 `*`·`…` 제거), 따옴표 구절(`"…"`·`“…”`·`「…」`), 16진 7~64자(숫자와 a~f를 모두 포함), 항목 기호(`R2-3`·`C-4`·`F-6`·`P3-2`·`D-b`), 시각(`19:00:42`), 소수(`0.876840`), 세 자리 이상 정수. 날짜와 절 번호(`3.1절`, `원판 3.1`)는 수치로 보지 않는다.
- 항목에 `sha256`이 있고 명시 해시가 없으면, 그 묶음에서 **그 판까지의** 판마다 해시 토큰(`rules sha256`, `rev1 sha256` …)을 더한다. 후보는 `.sha256` 첫 토큰·원시·LF 해시이고, 판정서의 16진 8자 이상 접두와 맞으면 있음이다.

대조 규칙:
- 해시: 서로 접두(짧은 쪽 7자 이상). 항목 기호·시각: 앞뒤가 영숫자·`-`·`:`에 붙지 않은 일치. 수치: 값 비교(`0.87684` = `0.876840`). 코드: 부분 문자열, 경로면 마지막 성분으로도. 따옴표 구절: 공백 정규화한 부분 문자열(줄을 넘는 구절도 찾음). `**`는 지우고 찾는다.
- 코드 토큰이 판정서 파일 이름이면(예: "판정서(`fb_judgement.md`)에 적을 문구") 판정서 자체로 있음(근거 `<판정서>:0 (판정서 자체)`).
- 상태: 토큰이 모두 있으면 `found`. **강한 항목의 자기 토큰이 하나도 없을 때만 `missing`**(`no_token_found`), 또는 강한 항목이 앞 목록에서 빌린 토큰이 하나도 없을 때(`preceding_none_found`, 공개할 목록이 판정서에 전혀 없다는 뜻). 그 밖(토큰 없음 `no_key_tokens`, 일부만 `partial`, 예측 P-n은 있으나 대조 낱말이 같은 줄에 없음 `prediction_not_compared`, 약한 항목 `weak_none_found`·`weak_partial`, 둘러싼 항목에서 빌린 토큰 `context_none_found`·`context_partial`, 앞 목록에서 빌린 토큰 일부 `preceding_partial`)은 `ambiguous`.
- 추출 항목이 0개면 `status: ok`, `items: 0`, `note`("통과가 아니다")와 `no_items` info. 빈 추출을 통과로 숨기지 않는다.

| 분류 | 심각도 | 내용 |
|---|---|---|
| `item_missing` | error | 강한 지시 항목의 토큰(또는 앞 목록에서 빌린 토큰)이 판정서에 하나도 없음 |
| `item_ambiguous` | info | 판단 보류(이유·없는 토큰 표시). 감사자가 항목 표를 읽고 판정한다 |
| `no_items` | info | 규칙에서 지시를 하나도 뽑지 못함 |

JSON 키: `repo`, `rules[{path, family, edition, items}]`, `judgements[]`, `items[{id, status, reason, rule("path:line"), edition, section, unit(list·table·quote·paragraph), origin(section·inline·prediction), strength(strong·weak), scope(item·sentence·context·preceding), text, tokens[{kind, value, found, evidence[]}]}]`(`kind` ∈ `hash`·`edition_hash`·`label`·`number`·`time`·`code`·`quote`·`prediction`), `summary{rules, judgements, items, found, missing, ambiguous, note?, …}`. md 보고서는 **추출 항목 전체**를 표로 낸다(감사자 검토용).

실데이터 회귀(2026-11-15, 프로젝트 `06_analysis/**/*rules*.md`·`v5_criteria*.md`·`*_plan*.md` 151판, 빈 판정서): 고치기 전 2134항목 → 고친 뒤 2187항목. **이전에 뽑던 항목 중 빠진 것 0**, 새로 뽑힌 53항목에 rev22 22·58·69·70·79행과 rev23 91·103행이 모두 들었다. 새 항목 중 `las_p5r4_k1_rules.md:12`("판정서 7.1절의 … 항목을 이 규칙에 넣는다")처럼 판정서를 **출처로** 말하는 문장도 뽑힌다(과잉 쪽, 알려진 한계).

실데이터 회귀(2026-11-16, 436.8 `v5_resume_4368_rules_rev16.md`·`_rev17.md`(묶음 규칙상 원판 `v5_resume_4368_rules.md`도 함께 읽힘, 3판) ↔ `v5_resume_4368_harness_judgement.md`, 읽기만): 확장 전 105항목(found 40 · missing 6 · ambiguous 59) → 확장 뒤 109항목(found 46 · missing 4 · ambiguous 59). 새 항목 4개는 사전 예측 줄 rev16:146 P-16·182 P-17·253 P-18·261 P-19(넷 다 found, 판정서 519~522행 대조 표). 상태가 바뀐 기존 항목 9개: rev16:64(면제 공개)는 약한 `no_key_tokens` → 강한 `preceding_partial`(H-11·H-12·C-9·C-11·`--check-recorded`·11.2는 있고 R16-11b·R16-14·11.1은 없음), rev16:91 두 문장은 앞 형제의 "저장 해시 없음"으로 `found`, rev16:304·rev17:37은 `preceding_partial`, rev16:174·327은 판 해시 토큰만 있던 `missing` → 앞 목록 토큰이 더해져 `partial`(missing 6 → 4의 이유), 원판 321·rev16:178은 약한 → 강한(`공개한다` 동사, 둘 다 found 그대로).

## missing_scan.py — 판정 불가·결측 행 이름 (E축, 2026-11-15)

판정 도구는 행을 판정하지 못하면(실행 쪽 출력의 행·키를 못 찾음, 계산 불가 멈춤) 목록 키(`missing_inputs`)·사유 문자열(`runner judge rows of <case>`, `not computable`)·건수(`runner_rows_found == 0`)로 표시한다. 436.8 rev23 R23-3처럼 "등급을 보기 전에 그런 행을 판정서 표에 싣고 멈춘다"는 규칙의 확인용이다. **행 이름과 표시 위치(JSON 경로)만** 내고 등급·수치·판정 값은 싣지 않는다.

```powershell
# 436.8 프리셋(두 경로 공통)
& $py -I -B "$tools\missing_scan.py" "<판정 출력>\chrono_path1" --preset v5-resume-4368 --out "$scratch\missing_p1.md"
& $py -I -B "$tools\missing_scan.py" "<판정 출력>\chrono_path2" --preset v5-resume-4368 --format json --out "$scratch\missing_p2.json"
# 일반 규칙
& $py -I -B "$tools\missing_scan.py" --repo "<프로젝트>" "<결과>/judge_*.json" `
    --key missing_inputs not_computable --text-in "reason,why=not computable" --where "rows_found == 0" "runner_file == null"
```

인자: `INPUT...`(폴더면 그 안의 `*.json`, `--recursive`면 하위 폴더까지; 파일·글롭은 `--repo` 기준), `--repo DIR`(기본 `.`), 규칙(여러 값·여러 번 누적, 하나 이상 필수): `--key NAME...`, `--text REGEX...`, `--text-in KEY[,KEY]=REGEX...`, `--where "KEY OP VALUE"...`, `--preset NAME`; `--name-key KEY...`(기본 `case name row id label key`, 주면 대체), `--show-text`, `--out`, `--format`, `--fail-on`. 여러 값 옵션(`--key`·`--text`·`--text-in`·`--where`·`--preset`·`--name-key`)은 뒤따르는 값을 모두 먹으므로 `INPUT`은 그 옵션들보다 **앞에** 둔다.

규칙:
- `--key NAME`: 객체의 키 `NAME` 값이 비지 않은 목록·객체·문자열, `true`, 0이 아닌 수이면 표시. `null`·`[]`·`0`·`false`는 표시 아님.
- `--text REGEX`: 모든 문자열 값(목록 안 문자열 포함)에 `re.search`. `(?i)`로 대소문자 무시. `--text-in KEY[,KEY]=REGEX`는 그 키 바로 아래 문자열(목록이면 그 목록의 문자열)만.
- `--where "KEY OP VALUE"`: `OP` ∈ `== != < <= > >=`, `VALUE`는 수·`null`·`true`·`false`·문자열(따옴표 벗김). **형 엄격**: 수와 비교할 때 `true`·`false`·`null`은 맞지 않는다(`runner_rows_found == 0`은 `false`를 잡지 않는다). `< <= > >=`는 수만.
- 행 이름: 표시 위치에서 위로 올라가며 이름 키(`--name-key` 순서)가 문자열인 가장 가까운 객체. 이름 있는 객체가 없으면 표시가 들어 있는 객체·목록의 경로가 행이다(이름 칸 `-`, `names_by_file`에는 경로). 같은 행의 여러 표시는 한 행으로 묶는다.
- 프리셋 `v5-resume-4368`(436.8 rev23 R23-3, 2026-11-15 outrigger_control R3d 판정 전 감사 리포트 `r3d_prejudge_audit.md`의 "판정 때 확인할 것" — 그 리포트는 세션 scratchpad에만 저장돼 저장소에는 없다): 키 `missing_inputs`·`not_computable`·`absent_inputs`; 문자열 `runner judge rows of`·`row missing`(모든 키); `reason,stops,why,note` 아래 `not computable`·`rev23 R23-1`(규칙 설명 키 `rule`의 같은 말은 빼려고 키를 좁혔다); `reason` 아래 `(?i)\bmissing\b|\babsent\b|\bnot found\b|\bno\s`(경로 2 도구의 결측 사유 단어); 조건 `runner_rows_found == 0`·`runner_file == null`. 사유 단어 규칙은 **넓게** 잡는다(rev23 103행 "사유로 원인을 가릴 수 없는 결측도 넣는다"). 표시된 행이 실제 결측인지는 감사자·메인 세션이 판단한다.
- 종료 코드: 표시된 행이 하나라도 있으면 1(`missing_row` error, 행마다 하나), 없으면 0. 규칙 없음, 잘못된 정규식·`--text-in`·`--where`, 없는 경로, 맞는 파일이 0개인 글롭, `.json`이 없는 폴더, **JSON으로 읽히지 않는 파일**(검사가 불완전), 입력 폴더 안의 `--out`은 2.
- `--show-text`: 맞은 문자열(키 규칙은 목록의 문자열을 ` | `로 이음, 그 밖은 `<형 이름>`, 200자에서 자름)을 `hits[].text`와 md 표에 싣는다. 사유에 수치가 들 수 있으므로 기본은 끈다.

| 분류 | 심각도 | 내용 |
|---|---|---|
| `missing_row` | error | 표시된 행: 이름, 맞은 규칙, 표시 위치(처음 3곳 + 나머지 수) |

JSON 키: `preset[]`, `rules[]`(규칙 표기 `key:…`·`text:…`·`text-in:…`·`where:…`), `name_keys[]`, `files[]`, `names_by_file{파일: [이름 또는 경로]}`, `rows[{file, path, name, rules[], hits[{path, rule, text?}]}]`, `summary{files, rows, names, by_rule{규칙: 행 수}, …}`, `findings`.

실데이터 확인(2026-11-15, 436.8 R3d `judge_0220671`, 읽기만, 실행 전후 117파일 SHA256 같음): `chrono_path1` 25파일 → 행 5(모두 `reason` 사유 단어 규칙, 이름 키 `case`·`key`), `chrono_path2` 14파일 → 행 20(`absent_inputs` 6, 사유 단어 20, 이름 없는 2행은 `$.runs.C-6…`·`$.runs.C-7a…` 경로). 두 경로 모두 `missing_inputs`·`not_computable`·`runner judge rows of`·`not computable`·`R23-1`·`runner_rows_found == 0`·`runner_file == null`은 0행이었다. 출력에 값 키가 없는지(`rows[]`는 `file·path·name·rules·hits`, `hits[]`는 `path·rule`만) 확인했다.

## ps1_lint.py — PowerShell 실행 스크립트 정적 검사 (E·I축, 2026-11-16)

436.8 판정 실행 스크립트에서 난 사고를 실행 전에 찾는다. 사고 판 `run_judgement_path1_M4.ps1`은 62행 `$Grid = @(…격자 4파일…)`을 153행 `foreach ($grid in 'grid_r67_main', …)`가 덮어써(PowerShell 변수 이름은 대소문자를 가리지 않는다) 159·183행의 `$Grid`가 마지막 격자 이름 하나가 됐다. 고친 판 `_retry1.ps1`은 루프 변수를 `$gname`으로 바꿨다. 스크립트는 **실행하지 않는다**.

```powershell
& $py -I -B "$tools\ps1_lint.py" "<판정 폴더>\_fixed\run\run_judgement_path1_M4.ps1" --out "$scratch\ps1_lint.md"
& $py -I -B "$tools\ps1_lint.py" --repo "<프로젝트>" "06_analysis/**/run_*.ps1" --format json --out "$scratch\ps1_lint.json"
# 정규식 파서 강제, 자리표시 추가·허용
& $py -I -B "$tools\ps1_lint.py" "<스크립트>.ps1" --parser regex --placeholder "<RUN_[A-Z]+>" --allow MASK
# 실행 직전에 채우는 자리만 남은 실행 스크립트(판 5 run_steps_ed5, 2026-11-22): 그 둘만 남았으면 종료 0
& $py -I -B "$tools\ps1_lint.py" --repo "<prelaunch>\run_steps_ed5" "*.ps1" `
    --allow ED5_RUN_COMMIT ED5_RUN_WORKTREE --format json --out "$scratch\ps1_lint_ed5.json"
```

인자: `INPUT...`(파일·글롭, `--repo` 기준), `--repo DIR`(기본 `.`), `--parser auto|ast|regex`(기본 `auto`: AST, PowerShell이 없거나 도우미가 실패하면 정규식 + `parser_fallback` info. `ast`인데 못 쓰면 종료 2), `--pwsh PATH`, `--placeholder REGEX...`(기본 패턴에 더함), `--allow NAME...`(남아도 되는 자리, `placeholder_scan --allow`와 같은 뜻: `MASK`·`{MASK}`·`<MASK>` 모두 자리 `MASK`를 가리키고 그 자리의 `{MASK}`·`<MASK>`를 함께 허용, 반복 누적, 2026-11-22. 그 전에는 글자 그대로만 맞았고 허용한 토큰은 보고에서 사라졌다), `--out`, `--format`, `--fail-on`.

- 허용한 자리는 문자열·맨 단어·주석 어디서든 `placeholder_allowed`(info)로 남는다. 그래서 **허용 목록의 자리만 남은 경우** 종료 0(`status: ok`)이고, 남은 자리 수는 끝줄 JSON `categories.placeholder_allowed`로 구별한다. 허용 목록 밖 자리가 하나라도 문자열에 있으면 예전처럼 `placeholder_unfilled`(error, 종료 1). 무엇을 허용할지는 감사자가 정한다.
- `.ps1`은 `placeholder_scan --pattern-set both`보다 이 도구가 맞다: 이 도구는 주석을 info로 나누지만 `placeholder_scan`은 주석 안의 설명용 `<report>`·`<run commit 8>`도 error로 센다(run_steps_ed5 17파일에서 14건, 모두 주석, 2026-11-22). 반대로 이 도구의 기본 꺾쇠 패턴은 대문자 `<NAME>`만 보므로 소문자 자리(`<run head>`)는 `--placeholder`로 더한다.

규칙:
- **(a) 변수 대소문자 재사용**: 같은 범위(스크립트 최상위, 또는 함수 하나) 안에서 변수 이름(소문자로 비교)의 **첫 쓰기**(대입·`foreach` 변수·매개변수) 뒤에 대소문자만 다른 철자로 `foreach` 변수나 대입을 쓰면 잡는다. 그 쓰기가 끝난 뒤(`foreach`는 루프 끝, 대입은 문장 끝) 사이에 다른 쓰기 없이 **처음 철자**로 읽는 줄이 있으면 `case_variant_overwrite`(error, 읽는 줄 표시), 없으면 `case_variant_reuse`(warning). 같은 철자로 일반 대입 뒤 `foreach` 변수로 다시 쓰고 루프 뒤 읽으면 `foreach_overwrites_variable`(warning). 범위 한정자가 붙은 이름(`$env:…`·`$script:…`)과 자동·선호 변수(`$_`·`$args`·`$LASTEXITCODE`·`$ErrorActionPreference` 등)는 뺀다. `$x[0] = …`·`$x.Name = …`은 변수 재대입이 아니다.
- **(b) `Tee-Object` + `return`**: 한 함수(중첩 함수 제외) 안에 출력이 잡히지 않은 `Tee-Object`(별칭 `tee`)와 값이 있는 `return`이 함께 있으면 `tee_with_return`(warning, 반환값에 tee 출력이 섞여 배열이 된다). 출력이 잡힌 경우(대입 `$x = … | Tee-Object`, `[void](…)`, 뒤에 `Out-Null`·`Out-File`·`Set-Content`·`Add-Content`, 출력 스트림 리디렉션 `>`·`1>`·`*>`)만 있으면 `tee_captured_with_return`(info).
- **(c) 자리표시**: 기본 패턴 `[A-Z][A-Z0-9_]*_FULL_HASH`, `{NAME}`(`${Name}` 변수 문법은 제외), `<NAME>`(대문자), `PLACEHOLDER`·`FILL_ME`·`TO_BE_FILLED`. 문자열·here-string·맨 단어(따옴표 없는 인자)에 있으면 `placeholder_unfilled`(error), 주석이면 `placeholder_in_comment`(info). `$M4_FULL_HASH`처럼 변수 이름이면 잡지 않는다.
- **(d) `-NoExit`**: 매개변수(`pwsh -NoExit`, 약어 `-noe`·`-noex`·`-noexi`, 대소문자 무시)나 문자열 안(`-ArgumentList '-NoExit', …`)이면 `noexit`(warning: 창이 닫히지 않아 프로세스 종료 대기가 끝나지 않는다), 주석이면 `noexit_in_comment`(info). `-ne`·`-not`은 아니다.
- 구문 오류(AST)는 `parse_error`(error)로 줄마다 낸다.

| 분류 | 심각도 | 내용 |
|---|---|---|
| `case_variant_overwrite` | error | 대소문자만 다른 이름으로 덮어쓴 뒤 처음 철자로 읽음(읽는 줄) |
| `placeholder_unfilled` | error | 문자열·맨 단어의 자리표시 |
| `parse_error` | error | PowerShell 구문 오류 |
| `case_variant_reuse` | warning | 대소문자만 다른 이름으로 다시 씀(뒤에 처음 철자로 읽지 않음) |
| `foreach_overwrites_variable` | warning | 대입한 변수를 같은 철자의 루프 변수로 덮어쓰고 루프 뒤 읽음 |
| `tee_with_return` | warning | 잡히지 않은 Tee-Object 출력 + 값 return 한 함수 |
| `noexit` | warning | `-NoExit`(매개변수·문자열) |
| `tee_captured_with_return` | info | Tee-Object 출력이 잡혀 있고 return이 있는 함수 |
| `placeholder_in_comment`, `noexit_in_comment` | info | 주석 안 |
| `placeholder_allowed` | info | `--allow`에 있는 자리(문자열·주석 모두, 2026-11-22) |
| `parser_fallback` | info | AST를 못 써 정규식 파서로 검사(이유) |

JSON 키: `placeholder_patterns[]`, `allow[]`(자리 이름, 꺾쇠·중괄호를 뗀 것), `files[{path, parser(ast·regex), parse_errors, variables, functions, error, warning, info}]`, `summary{files, parsers[], …}`, `findings`(`target`은 변수 `$Grid`·함수 이름·토큰).

실데이터 확인(2026-11-16, `judge_932f1fb\_fixed\run\`의 `.ps1` 5개, 읽기만): AST·정규식 두 파서 모두 사고 판 `run_judgement_path1_M4.ps1:153`을 `case_variant_overwrite`(62행 `$Grid`, 읽는 줄 159·183, 종료 1)로, 고친 판 `_retry1.ps1`은 발견 0(종료 0)으로 냈다. 초안 `run_judgement_path1_draft.ps1`은 같은 `$Grid` 덮어쓰기 + 13·14행 `M4_FULL_HASH`·`R4_FULL_HASH`(error) + 5행 주석 안 같은 이름(info), 경로 2 두 스크립트는 `run_judgement_path2.ps1`의 25·26행 자리표시만(경로 2 M4 판은 0).

실데이터 확인(2026-11-22, 판 5 `prelaunch_j9\run_steps_ed5\*.ps1` 17파일, AST, 읽기만): 허용 없이 `placeholder_unfilled` 2건(`<ED5_RUN_COMMIT>`·`<ED5_RUN_WORKTREE>`, 종료 1). 고치기 전에도 `--allow "<ED5_RUN_COMMIT>" "<ED5_RUN_WORKTREE>"`(글자 그대로)는 종료 0이었지만 허용 토큰이 보고에서 사라졌고, `--allow ED5_RUN_COMMIT ED5_RUN_WORKTREE`(이름만)는 종료 1이었다. 고친 뒤 두 형식 모두 종료 0, `placeholder_allowed` 2건.

## handoff_leak.py — 넘김 글머리 누설 검사 (두 경로 독립, 2026-11-16)

두 경로 판정에서 경로마다 넘기는 글(436.8 R4: 경로 1 하나, 경로 2 둘)에 상대 경로의 파일·줄기·상수·하위 명령·폴더·브랜치 이름이 들어가지 않았는지(원판 9.2, rev2 R2-0), 그리고 세 곳에 같은 바이트로 넣어야 하는 공통 블록이 정말 같은지를 본다. 메인 세션이 R4 넘김 때 쓴 즉석 스크립트(4자 이상 이름, 단어 경계 `[A-Za-z0-9_-]`, 표지 사이 줄의 sha256)를 도구로 옮겼다.

```powershell
# 경로 2 넘김 두 개에 경로 1 이름이 없는지 + 공통 블록 sha 고정
& $py -I -B "$tools\handoff_leak.py" "<넘김 폴더>\final\r4_handoff_path2_*.md" --names "<사전>\r4_p1_names.json" `
    --expect-block "R4 공통 블록=e451f067" --out "$scratch\leak_p2.md"
# 세 곳 공통 블록 안에 두 경로 이름이 모두 없는지(블록 안만)
& $py -I -B "$tools\handoff_leak.py" "<넘김 폴더>\supplement_r4_*.md" --names "<사전>\r4_p1_names.json" "<사전>\r4_p2_names.json" `
    --scope blocks --format json --out "$scratch\leak_blocks.json"
```

인자: `INPUT...`(넘김 파일·글롭, `--repo` 기준), `--names DICT.json...`(필수, 여러 개 합침), `--extra-name NAME...`(사전 밖 이름, 분류 `extra`), `--allow NAME...`(검사에서 뺄 이름), `--min-length N`(기본 4, 짧은 이름은 빼고 `names_skipped_short` info), `--boundary word|substring`(기본 `word`: 앞뒤가 `[A-Za-z0-9_-]`가 아님), `--ignore-case`(기본은 대소문자 구분), `--scope all|blocks`(기본 `all`, `blocks`면 표지 사이 줄만), `--blocks`(블록 찾기·대조 켬), `--block-pattern REGEX`(이름 있는 그룹 `label`·`edge` 필수, 기본 `^\s*<!--\s*(?P<label>.+?)\s+(?P<edge>시작|끝|start|end|begin)\s*-->\s*$`, 대소문자 무시), `--expect-block LABEL=SHA256...`(64자 또는 8자 이상 접두, 주면 `--blocks` 켬), `--repo DIR`, `--out`, `--format`, `--fail-on`. 여러 값 옵션은 뒤따르는 값을 모두 먹으므로 `INPUT`은 앞에 둔다.

규칙:
- 이름 사전: JSON 객체의 **목록 값마다 분류**(`files`·`stems`·`constants`·`subcommands`·`folders`·`outputs`·`branches` …), 목록이 아닌 값(`"source": "…"`)은 무시. 맨 목록은 분류 `names`. 같은 이름은 한 번만(처음 분류). 남는 이름이 0개면 종료 2(빈 선택은 통과가 아니다).
- 한 줄에서 긴 이름부터 찾고, 이미 잡힌 더 긴 이름의 구간 안에 있는 짧은 이름은 버린다(`z4373-p1harness` 안의 `p1harness`는 경계 규칙으로도 안 잡힌다). 경계 문자에 `.`이 없으므로 줄기(`judge_stage1_4368`)는 파일 이름(`judge_stage1_4368.py`) 안에서도 잡힌다 — 파일 이름만 허용하려면 줄기도 `--allow`에 준다.
- 누설 줄마다 `name_leak`(error): 이름(분류)과 줄 발췌(160자).
- 블록: 한 파일에서 라벨마다 시작 표지 1개가 끝 표지 1개보다 앞서야 한다(아니면 `block_markers` error). 블록 바이트 = 시작 표지 줄 다음 줄부터 끝 표지 줄 앞 줄까지의 **원시 바이트**(줄바꿈 포함). 메인 세션 스크립트의 `"\n".join(사이 줄) + "\n"`과 LF 파일에서 같다(R4 공통 블록 `e451f067…`로 확인). 같은 라벨의 블록은 입력 순서 첫 파일을 기준으로 원시 sha256을 비교하고(`block_mismatch` error, LF 정규화 값이 같으면 "줄바꿈만 다름"), 모두 같으면 `block_same` info, 한 파일에만 있으면 `block_single` info. `--expect-block`은 그 라벨의 모든 블록이 원시 sha256 접두와 같아야 한다(`block_expect_mismatch`, 라벨이 없으면 `block_expect_absent`, 둘 다 error).

| 분류 | 심각도 | 내용 |
|---|---|---|
| `name_leak` | error | 사전 이름이 있는 줄(이름·분류·발췌) |
| `block_markers` | error | 라벨의 시작·끝 표지 수·순서가 틀림 |
| `block_mismatch` | error | 같은 라벨 블록의 원시 sha256이 기준 파일과 다름 |
| `block_expect_mismatch` | error | 블록 sha256 ≠ `--expect-block` 값 |
| `block_expect_absent` | error | `--expect-block` 라벨이 어느 파일에도 없음 |
| `block_same` | info | 같은 라벨 블록 모두 같음(sha256) |
| `block_single` | info | 라벨이 한 파일에만 있음 |
| `names_skipped_short` | info | `--min-length` 미만이라 뺀 이름 수·예시 |

JSON 키: `boundary`, `ignore_case`, `min_length`, `scope`, `files[]`, `leaks[{file, line, names[{name, category, column}], text}]`, `leak_names[]`, `blocks[{file, label, start_line, end_line, sha256_raw, sha256_lf, bytes}]`, `summary{files, names_used, names_skipped_short, leak_lines, leak_names, blocks, …}`, `findings`.

실데이터 확인(2026-11-16, `judge_932f1fb\_fixed\handoff\`, 사전은 같은 세션 scratchpad `r4-handoff\r4_p1_names.json`(460개)·`r4_p2_names.json`(235개), 읽기만): 경로 2 넘김 두 개(`final\r4_handoff_path2_dyn.md`·`_terra.md`)에 경로 1 이름 누설 0, R4 공통 블록 네 곳(최종 세 개 + 초안) 모두 `e451f067db97…`(30,414 바이트, 커밋 메시지의 블록 `e451f067`과 같음). 경로 1 넘김의 블록 안에 경로 2 이름 0. 블록 밖까지 보면 경로 1 넘김·초안 뒷부분에는 경로 1 이름이 있다(그 경로 자신의 글이므로 정상). `supplement_r4_1.md`의 "보충 1 경로 2 전용" 블록은 두 사전으로 `--scope blocks`를 돌리면 경로 2 이름(`path2_chrono`·`p2_4368.py`·`oc5k`)으로 잡힌다 — 경로 2 전용 글이라 정상이고, 사전은 받는 쪽의 **상대** 사전만 준다.

## baseline_check.py — 봉인 기준선 폴더 (I축, 2026-11-17)

```powershell
# 해시 목록: 지금 색인 기준 / 봉인 커밋 기준
& $py -I -B "$tools\baseline_check.py" sums --repo "<프로젝트>" "06_analysis/02_control/j_p3_cause/baseline_221456d/SHA256SUMS" --out "$scratch\sums.md"
& $py -I -B "$tools\baseline_check.py" sums --repo "<프로젝트>" "06_analysis/**/baseline_*/SHA256SUMS" --rev f67745f --allow-extra "*.md" --format json --out "$scratch\sums.json"
# 저장소 최상위 기준 이름을 적은 목록(FIXED_INPUTS_*.SHA256SUMS 등, 2026-11-21)
& $py -I -B "$tools\baseline_check.py" sums --repo "<프로젝트>" "06_analysis/02_control/j_p3_cause/prelaunch_j9/FIXED_INPUTS_fa997f4c.SHA256SUMS" --base repo-root --out "$scratch\fixed.md"
# 실행 정체성: 모든 git.head = 기준 커밋, is_clean, (선택) 커밋 뒤·실행 전에 고친 파일
& $py -I -B "$tools\baseline_check.py" identity --repo "<기준 커밋이 있는 작업 트리>" "<기준선 폴더>" --expect-commit 221456d --mtime --out "$scratch\identity.md"
```

`sums` 인자: `LIST...`(파일 또는 글롭, `--repo` 기준. 0개 글롭은 종료 2), `--repo`, `--rev REV`(추적 여부를 그 커밋 트리로), `--base sums-dir|repo-root`(항목 경로의 기준, 기본 `sums-dir`, 2026-11-21), `--allow-extra GLOB`(여러 번, 목록 폴더 기준 상대 경로 `fnmatch` — 목록에 없어도 되는 파일), `--no-git`, `--out`, `--format`, `--fail-on`.
- 형식: GNU `<64hex>  <이름>`·`<64hex> *<이름>`, BSD `SHA256 (<이름>) = <64hex>`. 빈 줄·`#` 주석은 건너뛴다. 줄 끝 `\r`은 떼고 읽고 줄 수를 `sums_crlf`로 보고한다(사건: `-text`로 커밋된 CRLF 목록을 `split()`으로 읽으면 마지막 이름에 `\r`이 남았다).
- 항목 경로 기준(`--base`, 2026-11-21): 기본 `sums-dir`은 **목록 파일이 있는 폴더**다(`_sums.py`가 `목록.parent / 이름`으로 푼다. 이 옵션 전의 유일한 동작이고 기본값도 그대로다). `repo-root`는 `--repo`를 주면 그 폴더, 안 주면 목록이 든 git 작업 트리 최상위(`git rev-parse --show-toplevel`)다. `--repo`도 git도 없으면(`--no-git`, 저장소 밖) 종료 2. `seal_check --sums`는 계속 목록 폴더 기준이다.
  - 사건: 436.9 J-P3 `prelaunch_j9/FIXED_INPUTS_fa997f4c.SHA256SUMS`는 이름을 저장소 최상위 기준(`06_analysis/…`)으로 적었다. 기본 기준으로는 63항목이 모두 `sums_file_missing`이다(2026-11-21 실측). 실행 전 감사는 이 확인을 즉석 스크립트로 대신했다.
  - 기준 힌트: 한 목록의 **항목이 모두 없으면** 다른 기준(`sums-dir` ↔ `repo-root`)으로 다시 찾아 `sums_base_hint`(info)를 낸다. "다른 기준으로는 N/M개가 있고 해시 일치 K개"면 기준 오류(오탐), "다른 기준으로도 0개"면 파일이 정말 없다. 일부만 없으면 힌트를 내지 않는다. 다른 기준 폴더를 모르면(`sums-dir`에서 `--repo` 없이 `--no-git`) 힌트 없음. 힌트는 종료 코드를 바꾸지 않는다(`sums_file_missing` error는 그대로).
- 해시는 원시 바이트, 다르면 CRLF→LF 정규화 해시와도 비교해 "줄바꿈만 다름"을 붙인다.
- 목록 밖 파일: 목록 폴더 아래(재귀, `__pycache__`·`.git` 등 제외) 파일 중 어느 항목도, 입력한 목록 파일도 아닌 것.
- git: 목록과 있는 항목마다 `seal_check`와 같은 규칙(`_tracking.py`)으로 `cited_untracked`·`cited_ignored`(error), `cited_ignored_tracked`·`cited_outside_repo`(info).

| 분류 | 심각도 | 내용 |
|---|---|---|
| `sums_file_missing` | error | 항목의 파일 없음 |
| `sums_hash_mismatch` | error | 목록 해시 ≠ 실제(줄바꿈만 다르면 메시지에 표시) |
| `sums_empty` | error | 항목 0개(빈 목록은 통과가 아니다) |
| `cited_ignored` / `cited_untracked` | error | 위 `seal_check`와 같음 |
| `sums_crlf` | warning | CRLF 줄 수(떼고 읽음) |
| `sums_unlisted` | warning(`--base repo-root`는 info) | 목록 폴더에 있는데 목록에 없는 파일(`--allow-extra`로 제외). repo-root 목록은 저장소 곳곳의 파일을 적으므로 제 폴더가 목록 대상이 아니다. 그래서 기록만 하고 종료 코드를 바꾸지 않는다(2026-11-21 재감사 5 N-6) |
| `sums_duplicate` | warning | 같은 이름이 두 번(대소문자 무시) |
| `sums_malformed_line` | warning | 해시 줄로 읽히지 않는 줄 |
| `sums_base_hint` | info | 항목이 모두 없을 때 다른 `--base`로 찾은 결과(있는 수·해시 일치 수, 2026-11-21) |
| `sums_bom`, `cited_ignored_tracked`, `cited_outside_repo` | info | |

JSON 키: `repo`, `git`, `tracking_basis`, `base`(`sums-dir`·`repo-root`), `lists[{path, entry_base, base_hint{base, folder, present, hash_ok, entries}|null, entries, crlf_lines, lf_lines, malformed_lines, ok, missing, mismatch, unlisted[], allowed_extra[], results[{line, name, path, listed, actual, actual_lf, status}]}]`, `tracking[]`, `summary{base, lists, entries, mismatch, missing, unlisted, crlf_lines, cited_untracked, cited_ignored, …}`. `entry_base`·`base_hint`·`base`는 2026-11-21에 더한 키다(기존 키는 그대로).

실데이터 확인(2026-11-21, 읽기만): `FIXED_INPUTS_fa997f4c.SHA256SUMS`(63항목) — 기본 `sums-dir`은 없음 63(종료 1) + `sums_base_hint`(repo-root로 63/63, 해시 일치 63). `--base repo-root`는 없음 0·불일치 0이고, 지금 색인 기준 `cited_untracked` 15·`cited_ignored` 1·`sums_unlisted` 7(종료 1)이 남는다(감사자가 판단할 사실). 2026-11-21 N-6 뒤로 repo-root의 `sums_unlisted`는 info다(목록 `unlisted[]`·요약 `unlisted` 수는 그대로).

`identity` 인자: `PATH...`(기준선 폴더 또는 identity json, 글롭 허용), `--glob`(폴더 안, 기본 `**/*identity*.json`), `--expect-commit SHA`(7자 이상 16진, 접두 비교), `--repo`, `--mtime`, `--no-git`, `--out`, `--format`, `--fail-on`.
- 파일마다 JSON 어디든 `"git": {…}` 블록을 모두 찾는다(`$.start[0].git`, `$.end[0].git` …). 같은 dict의 `time`(또는 `started`·`start_time`·`started_at`)을 실행 시각으로 읽는다.
- `--expect-commit`이 없으면 모든 `head`가 같은지만 본다(다르면 `baseline_head_mixed`).
- `--mtime`(git 필요): 기준 커밋(`--expect-commit`, 없으면 하나뿐인 head)의 `diff-tree` 변경 파일 중 `--repo` 작업 트리의 mtime이 커밋 시각보다 늦은 것. 가장 이른 실행 시각보다도 이르면 `mtime_after_commit_before_run`(warning, "지금 내용은 커밋과 같음/다름"을 `hash-object`로 덧붙임), 실행 뒤면 `mtime_after_commit`(info). 실행 시각이 없으면 모두 warning. mtime은 체크아웃·저장만으로도 바뀌므로 확정이 아니라 "읽어 볼 곳"이다.
- identity 파일 0개, 깨진 JSON, 잘못된 `--expect-commit`은 종료 2.
- head는 전체 커밋(16진 40자, SHA-256 저장소면 64자)이어야 한다. 그렇지 않으면 `is_clean` 값과 관계없이 `baseline_head_invalid`(error)다. 빈 값 `""`, 짧은 값, 16진이 아닌 값이 여기에 걸린다. git 블록에 실패 표지 `error`가 있으면 `identity_git_error`(error)다. 비교는 "기록된 head가 `--expect-commit`으로 시작"하는 한 방향뿐이다(2026-11-21).
  - 사건: `d8x_record.git_state`는 git 호출이 실패하면 head `""`·`is_clean: true`를 남긴다. 예전 양방향 접두 비교에서는 `""`가 어떤 기대 커밋과도 맞았다(436.9 덧붙임 4a-5 4절).

| 분류 | 심각도 | 내용 |
|---|---|---|
| `identity_git_absent` | error | 파일에 git 블록이 없음 |
| `baseline_head_missing` | error | git 블록에 `head` 없음 |
| `baseline_head_invalid` | error | `head`가 전체 16진 커밋이 아님(빈 값 = git 조회 실패) |
| `identity_git_error` | error | git 블록에 실패 표지(`error`)가 있음 |
| `baseline_head_mismatch` | error | `head` ≠ `--expect-commit` |
| `baseline_head_mixed` | error | (`--expect-commit` 없이) `head`가 두 가지 이상 |
| `baseline_dirty` | error | `is_clean: false`(변경 줄 앞 5개 표시) |
| `baseline_clean_unknown` | warning | `is_clean` 없음 |
| `baseline_clean_inconsistent` | warning | `is_clean: true`인데 `status_porcelain`이 비어 있지 않음 |
| `mtime_after_commit_before_run` | warning | 커밋 뒤·실행 전에 mtime이 바뀐 파일 |
| `mtime_after_commit` | info | 커밋과 실행 뒤에 바뀐 파일 |

JSON 키: `expect_commit`, `files[]`, `heads[]`, `blocks[{file, json_path, head, is_clean, status_porcelain, run_time}]`, `mtime{commit, commit_time, earliest_run, changed_files, late_files[{path, mtime, before_run, same_as_commit_now}], note}`(`--mtime` 없으면 null), `summary{files, git_blocks, heads, dirty, …}`.

2026-11-21: `test_baseline_check.py`에 시험 5건을 더했다. head `""`·공백·12자·16진이 아닌 40자는 `baseline_head_invalid`(종료 1, `--expect-commit` 없이도), git 실패 표지는 `identity_git_error`. 전체 228 passed. 실제 `baseline_221456d` identity `--expect-commit 221456d`는 그대로 종료 0이다(6블록). 같은 날 N-6: repo-root 목록의 `sums_unlisted` info 시험 1건을 더했다(전체 250 passed).

실데이터 확인(2026-11-17, 읽기만): `baseline_221456d/SHA256SUMS`(27항목) — 지금 색인 기준 해시 불일치 0·목록 밖 0, `sums_crlf`(27줄) warning, `*.npz` 18개 `cited_ignored_tracked` info(143a0ef에서 강제 추가). `--rev f67745f`(목록을 봉인한 커밋) → npz 18개 `cited_ignored` error(종료 1) — 사건 재현. identity 3파일·git 블록 6개: `--expect-commit 221456d` 종료 0, `--expect-commit ad5024b` → `baseline_head_mismatch` 6. z4369-jp3 작업 트리 기준 `--mtime`: 221456d가 고친 26파일 중 11개가 커밋 뒤 mtime, 그중 `jp3_case_replay.py` 1개가 커밋(21:54) 뒤·첫 실행(23:10) 전(22:18, 지금 내용은 커밋과 같음) → warning 1.

## ref_check.py — 명세가 가리킨 파일이 저장소에 있는가 (I축, 2026-11-17)

```powershell
& $py -I -B "$tools\ref_check.py" --repo "<프로젝트>" "06_analysis/02_control/j_p3_cause/jp3_remedy_spec.md" --out "$scratch\ref.md"
& $py -I -B "$tools\ref_check.py" --repo "<worktree>" "06_analysis/**/*_spec*.md" --rev HEAD --allow "^audit-" --format json --out "$scratch\ref.json"
```

인자: `DOC...`(md 파일·글롭, `--repo` 기준), `--repo`(기본 현재 폴더, 하위 폴더를 줘도 작업 트리 루트로 올린다), `--rev`(기본 `HEAD`), `--include-fences`(코드 블록 줄도 읽음), `--allow REGEX`(여러 번, 건너뛸 토큰), `--max-candidates N`(기본 5), `--no-git`(git 트리 대신 디스크 폴더), `--out`, `--format`, `--fail-on`.
- 토큰: 인라인 코드(백틱) 안을 공백으로 나눈 조각 중 알려진 확장자(`py md json jsonl npz npy csv txt yaml ps1 sha256 h5 mat xlsx log done …`)로 끝나거나 `SHA256SUMS` 등 이름이거나 `/`·`\`로 끝나는(폴더) 것. 앞뒤 따옴표·괄호·문장부호와 `:79·184`·`:12-30`·`#L12`·`::test_name` 꼬리를 뗀다. `<…>`·`{…}`·`$`·`%`·`…`가 든 토큰은 자리표시로 세고 건너뛴다. URL, `np.load` 같은 식별자는 대상이 아니다. 절대 경로는 저장소 안이면 상대 경로로 바꾸고 밖이면 `external`로 센다. 같은 문서의 같은 토큰은 한 번만(첫 줄·횟수).
- 찾는 순서: 저장소 루트 상대 → 문서 폴더 상대 → 경로 꼬리(`02_chrono/x.py` = `…/02_chrono/x.py`) 또는 이름만이면 파일 이름 → 폴더 → 글롭 `fnmatch`. 결과에 `how`(`root`·`document`·`suffix`·`name`·`folder`·`glob`)를 적는다.
- 못 찾으면: 대소문자만 다르면 `ref_case_mismatch`, 트리에는 없고 디스크(루트·문서 폴더)에 있으면 `ref_untracked`, 둘 다 아니면 `ref_missing` + 후보. 후보 점수 = ½·difflib 비율(줄기) + ½·공유 줄기 조각 비율(조각마다 희소도 가중 1/log2(2+그 조각이 든 파일 이름 수) — `keys`처럼 흔한 조각보다 `dg3`처럼 드문 조각을 높게 친다).
- 저장소가 git 작업 트리가 아니거나(`--no-git` 없이), `--rev`를 못 읽거나, 트리가 비었거나, 0개 글롭·잘못된 정규식·입력 폴더 안의 `--out`은 종료 2.

| 분류 | 심각도 | 내용 |
|---|---|---|
| `ref_missing` | error | 트리에도 작업 트리에도 없음(비슷한 이름 후보 표시) |
| `ref_untracked` | warning | 작업 트리에만 있음(새 체크아웃·다른 worktree에는 없다) |
| `ref_case_mismatch` | warning | 대소문자만 다른 파일이 있음 |

JSON 키: `repo`, `tree`, `tree_files`, `references[{document, line, token, normalized, count, status(ok·case_mismatch·untracked·missing), how, resolved[], candidates[]}]`, `summary{documents, references, resolved, missing, untracked, case_mismatch, templates, external, allowed, …}`.

실데이터 확인(2026-11-17, 읽기만): `outrigger_control` HEAD에서 `jp3_remedy_spec.md` 참조 70개 중 66개 확인, `ref_missing` 4개 — `dg3_keys.txt`(429행, 첫 후보 `…/judge_932f1fb/harness_path1/dg3_hash.json` — 사건의 실제 목록), `audit-jp3r4\report.md`(scratchpad 감사 보고), `verif_matrix/v5_resume_4368/run_b9f5707/logs/run_harness.out.log`(미추적 로그), `jp3_case_replay.py`(z4369-jp3 브랜치에만 있음). 0.3 s.

## junit_skips.py — 건너뛴 시험 = 미실행 (E축, 2026-11-17)

```powershell
& <프로젝트 인터프리터> -m pytest 05_tests -q -p no:cacheprovider --junitxml="$scratch\junit.xml"
& $py -I -B "$tools\junit_skips.py" "$scratch\junit.xml" --critical "test_.*record" --critical "test_rev7_regression" --out "$scratch\skips.md"
& $py -I -B "$tools\junit_skips.py" "$scratch\junit.xml" --critical "test_t_jr_04"   # 봉인 예측 시험이 xfail이면 error
```

인자: `REPORT...`(JUnit XML 파일·글롭, 현재 폴더 기준), `--critical REGEX`(여러 번, `classname::name`·`file`·사유에 대해 search), `--fail-on-skip`(그 밖의 건너뜀도 warning), `--out`, `--format`, `--fail-on`.
- `<testcase>`의 첫 `failure`·`error`·`skipped` 자식이 결과다. 사유는 `message`(없으면 본문) 200자.
- 예상 실패는 건너뜀과 따로 센다(2026-11-20): `<skipped type="pytest.xfail">` → `xfailed`(warning — 봉인 예측 시험이 xfail로 가려지면 예측이 맞았는지 모른다), `<failure message="[XPASS(strict)] …">` → `xpassed`(error, `strict: true`, 사유는 접두를 뗀 것). `--critical`에 걸린 xfail은 예전처럼 `critical_skipped`(error). 그래서 xfail만 있는 실행도 기본 `--fail-on warning`에서 종료 1이다(알고 있는 xfail만이면 `--fail-on error`).
- pytest JUnit XML(pytest 9.1, 2026-11-20 확인)은 xfail이 strict인지 적지 않고(`strict: null`), strict 아닌 XPASS는 자식 없는 통과로 적는다 — 이 도구로는 보이지 않으므로 필요하면 pytest를 `-rxX`로 돌려 요약 줄을 함께 남기거나 `-o xfail_strict=true`로 돌린다.
- 깨진 XML, 없는 파일, 0개 글롭, 잘못된 정규식, 입력 폴더 안의 `--out`은 종료 2.

| 분류 | 심각도 | 내용 |
|---|---|---|
| `critical_skipped` | error | `--critical`에 걸리는 시험이 건너뜀 — 미실행 |
| `critical_absent` | error | `--critical` 패턴에 맞는 시험이 하나도 없음(수집되지 않음) |
| `test_failed` | error | failure·error |
| `no_tests` | error | 시험 0개(빈 실행은 통과가 아니다) |
| `xpassed` | error | strict 예상 실패가 통과함(`[XPASS(strict)]`, 2026-11-20) |
| `xfailed` | warning | 예상 실패(xfail)와 사유, strict 여부는 JUnit에 없음(2026-11-20) |
| `skipped` | info(`--fail-on-skip`이면 warning) | 그 밖의 건너뜀과 사유 |

JSON 키: `critical[]`, `cases[{report, node_id, file, outcome, type, reason, strict}]`(통과 제외, `outcome`은 `failed`·`error`·`skipped`·`xfailed`·`xpassed`, `strict`는 strict XPASS만 `true`이고 나머지는 `null`), `summary{reports, tests, passed, failed, errors, skipped, xfailed, xpassed, critical_skipped, …}`. **2026-11-20부터 `skipped`에 xfail이 들지 않는다**(예: J4a worktree 실행 `junit_wt.xml` — 이전 skipped 134 → 지금 skipped 132 + xfailed 2, 종료 코드는 실패 2건 때문에 전후 모두 1).

## worktree_tests.py — worktree 코드 + 메인 checkout 저장 자료로 시험 (E축, 2026-11-22)

저장 결과 경로를 시험 파일 위치로 정하는 시험(`PROJECT_ROOT = Path(__file__).resolve().parents[2]` → `PROJECT_ROOT / "07_results" / …`)은 worktree에서 돌리면 git 제외 자료가 없어 skip되고, 메인 checkout에서 돌리면 master 코드가 돈다. worktree 안 정션·링크는 금지다(2026-11-20). 판 5 작업의 우회(`make_data_copies.py`: 시험 파일 복사 → `07_results` 경로만 메인으로 → `-c <worktree>\pyproject.toml` → probe)를 일반화했다. **verif에서 이 도구만 코드를 실행한다**(프로젝트 시험). worktree·데이터 root에는 아무것도 쓰지 않는다.

```powershell
$wt = "C:\workspace\outrigger_control\.claude\worktrees\<이름>"
& $py -I -B "$tools\worktree_tests.py" --worktree $wt --data-root C:\workspace\outrigger_control `
    --python C:\ProgramData\miniforge3\envs\Chrono-dev\python.exe --scratch "$scratch\wt_runs" `
    --test 05_tests/unit/test_chrono_t45_replay.py 05_tests/unit/test_las_off_chrono.py `
    --probe-module outrigger_sim chrono_t45_replay j_p3_inputs --format json --out "$scratch\wt_tests.json"
# xdist 등 pytest 인자는 -- 뒤에(그대로 넘김). 시험이 sys.path를 바꾸기 전에 고정하려면 --pin-module
& $py -I -B "$tools\worktree_tests.py" ... --pin-module outrigger_sim -- -n 4 --dist loadfile
```

인자: `--worktree DIR`(코드), `--data-root DIR`(저장 자료, 보통 메인 checkout), `--python PATH`(프로젝트 인터프리터, 절대경로), `--scratch DIR`(실행 폴더 `wt_tests_<시각>_<pid>`를 만들 곳 — worktree·데이터 root 밖이어야 함), `--test FILE...`(worktree 기준 파일·글롭, 반복 누적), `--probe-module NAME...`(worktree에서 import됐는지 볼 모듈), `--rebase-dir NAME...`(데이터 root에서 읽을 최상위 폴더, 기본 `07_results`, 데이터 root에 없으면 종료 2), `--support FILE...`(함께 복사·변환할 worktree 보조 모듈), `--pin-module NAME...`(`pytest_configure`에서 먼저 import), `--inifile FILE`(기본: worktree의 `pytest.ini` → `[tool.pytest.ini_options]`가 있는 `pyproject.toml` → `tox.ini`·`setup.cfg`), `--env NAME=VALUE`(반복), `--timeout S`(기본 3600, 넘으면 자기가 띄운 pytest 프로세스 트리를 PID로 끝냄), `--keep`(실행 폴더를 남김), `--out`, `--format`, `--fail-on`, `-- <pytest 인자>`.

하는 일:
1. `--test` 파일과, worktree 루트부터 그 폴더까지의 `conftest.py`·`__init__.py`, `--support` 파일을 `<실행 폴더>\tree\<같은 상대 경로>`로 복사한다. 복사본마다 (가) `__file__` 이름을 **원본 절대경로 문자열**로 바꾸고(그래서 `parents[2]`·fixture·보조 경로는 worktree를 가리킨다), (나) 데이터 경로 식 — `X / "07_results"`(`"07_results/S8"`도), `X.joinpath("07_results", …)`, `Path(…)`·`PurePath(…)`·`os.path.join(…)`의 `"07_results"` 인자 — 을 `__import__("_wt_probe").rebase_data(…)`로 감싼다. 감싼 함수는 실행 중 `<worktree>\07_results\…`를 `<데이터 root>\07_results\…`로 바꾼다(상대 경로는 현재 폴더 = worktree 기준). 줄은 더하지 않으므로 traceback 줄 번호가 원본과 같다(`_source_rebase.py`). 복사본은 원본 줄바꿈 그대로 쓴다(`newline=""`, 2026-11-22: 이전에는 CRLF 원본이 `\r\r\n`이 되어 줄 번호가 두 배가 되고 `\` 줄 잇기가 있는 파일이 SyntaxError로 수집 실패했다).
2. `<python> -B -m pytest <복사본…> --rootdir <tree> --confcutdir <tree> -c <worktree ini> -p no:cacheprovider -p _wt_probe --junitxml … -q -rfEsxX [-- 인자]`를 **현재 폴더 worktree**로 돌린다. 상속된 `PYTHONPATH`·`PYTEST_ADDOPTS`·`PYTEST_PLUGINS`는 빼고(보고에 `dropped_environment`), `PYTHONPATH`=실행 폴더(플러그인만), `PYTHONDONTWRITEBYTECODE=1`. ini의 `pythonpath`는 ini 폴더(worktree) 기준이라 `03_src`가 worktree를 가리킨다. 원본 시험 폴더는 `sys.path` **끝**에 붙여 같은 폴더의 보조 모듈(`helper_mod`)이 worktree에서 import된다.
3. 플러그인 `_wt_probe.py`가 pytest 프로세스마다(xdist 작업자 포함) `probe_<worker>.json`에 `--probe-module`의 `__file__`과 바꾼 경로 수를 남긴다. 도구는 JUnit XML(`junit_skips.read_test_cases`), probe, 원본 SHA-256(전후)을 읽은 뒤 실행 폴더를 지운다(`--keep`이 아니면).

종료 코드: 0 = pytest 종료 0 · 모든 시험이 돌았음(skip·xfail 0) · probe 모듈 모두 worktree · 원본 불변. 1 = 발견(아래 error·warning). 2 = 입력 오류(폴더·파일·인터프리터 없음, worktree 밖 시험, 데이터 root에 없는 `--rebase-dir`, worktree·데이터 root 안의 `--scratch`·`--out`, 원본 구문 오류, pytest 사용법 오류 = pytest 종료 4). 3 = 이 도구의 내부 오류.

| 분류 | 심각도 | 내용 |
|---|---|---|
| `test_failed`, `xpassed` | error | 실패·오류 시험, strict XPASS(`junit_skips`와 같음, 위치는 원본 상대 경로) |
| `no_tests` | error | 시험 0개(pytest 종료 5 포함) |
| `pytest_timeout`, `pytest_interrupted`, `pytest_internal_error` | error | 시간 초과(트리 종료), pytest 종료 2·3 |
| `junit_missing`, `pytest_failed_unseen` | error | JUnit XML 없음, 종료 1인데 JUnit에 실패 없음(로그 끝 확인) |
| `probe_missing` | error | probe 기록 없음(플러그인이 돌지 않음) |
| `probe_foreign` | error | probe 모듈이 worktree 밖(예: 메인 checkout)에서 import됨 — 위치·작업자 표시 |
| `original_changed` | error | 원본 파일 바이트가 실행 중 바뀜 |
| `skipped` | warning | 건너뜀 = 검증 공백(사유 표시) |
| `xfailed` | warning | 예상 실패 |
| `probe_not_loaded` | warning | probe 모듈을 어느 프로세스도 import하지 않음(확인 불가) |
| `data_literal_not_rebased` | warning | 감싸지 않은 식 안의 `07_results` 글자(`NAME = "07_results"` 뒤 `ROOT / NAME`) — 그 줄은 worktree를 읽는다 |
| `rebase_never_used` | warning | 실행 중 데이터 경로가 한 번도 바뀌지 않음 |
| `cleanup_failed` | warning | 실행 폴더 삭제 실패(경로 표시) |
| `probe_worktree` | info | probe 모듈이 worktree에서 import됨(위치·작업자) |
| `no_data_paths` | info | 그 시험 파일에 바꿀 데이터 경로가 없음(worktree에서 그냥 돌려도 같다) |
| `rebase_unmatched` | info | 감싼 식의 값이 worktree·데이터 root 어느 쪽도 아니라 그대로 둠(`tmp_path`의 합성 `07_results`, 하드코딩한 메인 경로) |

JSON 키: `worktree`, `data_root`, `python`, `inifile`, `rebase_dirs[]`, `probe_modules[]`, `pin_modules[]`, `run_dir`, `pytest{command[], cwd, dropped_environment[], set_environment[], exit_code, wall_s, log_tail[]}`(로그 끝 60줄), `tests{tests, passed, failed, errors, skipped, xfailed, xpassed}`, `cases[]`(통과 제외), `probe_records[{worker, pid, cwd, modules{이름: 파일 또는 null}, pinned{}, rebase{rebased, already_in_data_root, unmatched}, rebased_examples[], unmatched_values[]}]`, `rebase_totals`, `copies[{file, is_test, file_references, wrapped[{line, expression}], unwrapped_literals[{line, text}]}]`, `originals{경로: sha256}`, `summary{pytest_exit, pytest_exit_text, tests…, probe{이름: worktree·foreign·not_loaded}, rebased_paths, copies, originals_unchanged, run_dir_removed, …}`, `findings`.

실데이터 확인(2026-11-22, 판 5 worktree `z4369-ed5` `fcf57a41`, Chrono-dev Python 3.12 / pytest 9.1.1, 데이터 root 메인 checkout): `test_chrono_t45_replay.py`·`test_las_off_chrono.py` → 28 passed · skip 0(우회 스크립트로 돌린 같은 두 파일의 28 passed와 같음), 280 s, 복사본 3(두 시험 + `05_tests/conftest.py`), 감싼 식 6(25·28·31·35·38행, 22행), 실행 중 바꾼 경로 6, probe `outrigger_sim`·`chrono_t45_replay`·`j_p3_inputs` 모두 worktree, `t4h_replay`는 두 파일이 import하지 않아 `probe_not_loaded`(그래서 종료 1 — probe 목록은 그 시험이 실제로 import하는 모듈로 준다). 실행 전후 메인 checkout·worktree `git status --short` 같음, 실행 폴더 삭제됨.

## 테스트

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
& $py -B -m pytest "$tools\tests" -q -p no:cacheprovider
& $py -I -B "$tools\smoke.py"
```

합성 픽스처(tmp_path, 한글·공백 폴더)로 위 표의 분류(2026-11-08 기준 중복 제외 51개, 2026-11-08 seal_check 8개 추가, 2026-11-17 seal_check·gate_scan·baseline_check·ref_check·junit_skips 분류 추가 — 시험 수는 아래 2026-11-17 줄)마다 최소 1건, 정상 종료 0, `--out` 입력 폴더 안 → 2, 입력 불변(SHA 전후), `--no-git`, `--format json`을 본다. git 경로 테스트는 tmp_path에 `git init`(+ 커밋, 저장소 로컬 `core.autocrlf`를 시험마다 지정)을 만들고, git이 없으면 건너뛴다. `test_seal_check_refs.py`는 `--repo`·글롭 접기·빈 글롭·`--revs none`·빈 `.sha256`·CRLF 줄 수·git 파일 사실·autocrlf true/input/false·미추적·`--const`(일치·튜플 안 낡은 값·없음·해시 없음·형식 오류)·`--quoted`(규칙·결과 파일 접두, 날짜·`0x`·UUID 제외, 커밋 풀이, 저장소 밖 문서)·`--hash-files`·`--code` 반복(여러 번 준 값이 모두 반영되는지, 한 번에 여러 값도 그대로인지, 2026-11-09)·`--out` 위치를 본다. `test_judgement_checklist.py`는 합성 규칙·판정서로 found·missing·ambiguous(partial·no_key_tokens·weak_none_found), 판 해시 토큰, 판정서 자체 참조, 인용 문구, 문서 제목·일반 줄 비추출, 빈 추출(`items: 0`·note, 종료 0), 빈 글롭 → 2, `--out` 위치·md 보고서를 본다. 2026-11-08: 63 passed. 2026-11-09: 67 passed. `test_replay_recount.py`(2026-11-10)는 합성 원본·재생으로 `r4+N` 선택 일치(입력 불변), 틀 키 `!r`(`0.0`·`'VB'`), 부분 파일 합치기(`--replay` 여러 값·여러 번)와 키 중복, 선택 누락·선택 밖·모르는 키, 해시 불일치·저장 사본 불일치·해시 없음·재생 실패, 원본 필터(`no:error`·`--source-in`)와 중복 정책 `last`(뒤 시도 해시)·`error`(처음 것 → 해시 불일치), 판별 건수(`count:`·`replay_count:`), 키 대체 순서, 빈 선택·기대 불일치, 인자 오류 6종 → 2, `--out` 위치를 본다. 같은 날 `record_check --no-git`(하위 명령 앞·뒤)과 `timeline --rules`·`--results` 반복 누적 시험을 더했다: 85 passed. 2026-11-11: `test_log_errors.py`(비영 오류·`.done exit=0` 표시·입력 불변, 0·줄 없음 info·`--require-line` warning, 마지막·최대 값, `--pattern` 사용자 지정·그룹 없음·잘못된 정규식 → 2, 빈 폴더·없는 경로 → 2, `--out` 위치)와 `test_placeholder_scan.py`(숫자 포함 토큰 `{BATCH_V7}`, JSON 경로, md 줄 위치, 소문자·공백·숫자 시작 비일치, `--allow` 두 형식·반복 누적, 사용자 패턴, 빈 글롭·없는 파일·잘못된 정규식·`--out` 위치 → 2)를 더했다. 같은 날 seal_check `eol=lf` 보호(git autocrlf true·false, `.gitattributes` 직접 해석과 `-eol` 덮어쓰기, `eol=crlf`는 보호 아님)와 timeline csv·md 결과(`--repo` 상대 경로·글롭, csv 열 `--time-field`, md `time_field_not_applicable`, mtime을 미래로 둔 csv의 git 근거, 지원 안 하는 확장자·없는 파일·없는 `--repo` → 2)를 더했다: 103 passed. 2026-11-15: `test_threshold_boundary.py`(4자리 반올림 합성 CSV에서 끝 0이 지워진 `0.25`까지 모호로 세기·한 ulp 떨어진 `0.2499`는 판정됨·단위별 통과 수 범위·자연 정렬·입력 불변, `>=`는 통과 수만 바뀜, 경계 없음 → 0, 문턱이 더 세밀할 때 이웃 두 값 모호, `--decimals`가 데이터보다 짧을 때 warning, 해석 불가 행 warning과 `--fail-on error` → 0, 글롭 여러 파일 `@file` 단위·헤더만 있는 파일, cp949 한글 헤더·`;` 구분자, md 보고서·`--max-listed`, 인자·입력 오류 11종 → 2, `--help`)를 더했다: 114 passed. 같은 날(감사 위임 3건): `test_missing_scan.py`(프리셋으로 경로 1·2 꼴 합성 출력의 행 이름만·등급과 수치 비출력·규칙 설명 키의 `not computable` 비표시·`false` ≠ 0·하위 폴더 비재귀·입력 불변, 깨끗한 출력 → 0, `--recursive`, `--text-in` 쉼표 키·`--where` 수·`false`, `--name-key`·`--show-text`, md 보고서, 규칙 오류 5종·입력 오류 4종 → 2), `test_judgement_checklist.py`에 rev22·rev23 꼴 기록 동사(싣는다·싣고·표에 싣고·보인다·밝힌다) 추출과 기존 동사(적는다·기록) 유지, `test_seal_check.py`에 옆 문자열이 다른 계열(`v5_criteria_rev7.md`·`d1_selection_rules_rev1.md`·판정서·키워드 인자)을 가리키는 해시는 `code_pin_stale` 아님·같은 계열의 틀린 해시는 그대로 stale을 더했다: 128 passed. 2026-11-16(436.8 감사 검사기 3건): `test_judgement_checklist.py`에 사전 예측 줄(`**[참고]**`·들여쓴 `[참고]`·범위 `P-20~P-21`, 대조 낱말 있는 줄 → found, P-n만 → `prediction_not_compared`, P-n 없는 "사전 예측: 하지 않는다" 비추출, 예측 문장의 `sha256`에 판 해시 토큰 안 붙음)과 앞 목록 빌리기(rev16 56~64 꼴: 앞 형제와 하위 항목만 빌리고 그 앞 11.1 항목은 안 빌림, 최상위 항목은 앞 `[정의]` 항목 전체, 판정서에 하나도 없으면 `preceding_none_found` missing) 3건, `test_ps1_lint.py` 16건(사고 꼴 `$Grid`/`$grid` → error·입력 불변, 고친 꼴 → 0, 대소문자 재사용 warning·같은 철자 foreach 덮어쓰기·읽지 않으면 없음, Tee-Object + return 잡힘·안 잡힘, 자리표시 문자열·주석·`${Mask}` 제외·`--allow`, `-NoExit` 문자열·`-noe` 약어·주석·`-ne` 제외 — 이 6건은 AST·정규식 두 파서로 각각, AST 구문 오류, `auto`인데 PowerShell 없음 → 정규식 + `parser_fallback`, `ast` 강제인데 없음 → 2, `--out` 위치 → 2; PowerShell이 없으면 AST 경우는 건너뛴다), `test_handoff_leak.py` 10건(단어 경계·긴 이름 우선·짧은 이름 빼기·입력 불변, `--allow`, `substring`·`--ignore-case`, 같은 블록 + `--expect-block` 접두 → 0, 바뀐 블록과 CRLF만 다른 블록 구분, 표지 수 틀림·기대 라벨 없음, `--scope blocks`, 빈 사전 → 2, 잘못된 `--expect-block` → 2, `--out` 위치 → 2)를 더했다: 157 passed(약 30~60 s). `smoke.py`에 ps1_lint(정규식)·handoff_leak을 더했다(12실행, `status: ok`). 2026-11-17(J-P3 사건 검사 6건): `test_gate_scan_selection.py` 14건(사건 꼴 1건·줄·함수·종료 1, 고친 꼴 0, 0건 처리 3종(raise·`len !=`·`n = len` 비교) → 0, 실패 집합 참거짓 → 0, `all(...)` 판정값 1건과 `bool(x) and` → 0, 앞선 pass 기본값·멈춤 뒤 `return "pass"`·루프 깃발 각 1, `append` 선택·모듈 최상위, 검사된 선택의 부분집합 → 0, 루프 카운터 최솟값 비교 → 0, 실제 z4369-jp3 221456d·ad5024b판(`git show`, 읽기만; 없으면 건너뜀)), `test_seal_check_tracking.py` 13건(`.md.sha256` 이름과 `*` 표시, 두 이름 공존 `seal_two_files`, `seal_missing` 메시지의 두 이름, 코드의 `.md.sha256` 이름 고정, `--sums`의 무시된 npz → `cited_ignored`, 강제 추가 → info·종료 0, `--rev HEAD~1` → `cited_ignored`, `--check-tracked`로 `rule_untracked` → `cited_untracked`, `--hash-files` 미추적은 `--check-tracked`일 때만, `sums_entry_missing`, `--rev` 입력 오류 2종, git 작업 트리 밖 → `cited_outside_repo` info), `test_baseline_check.py` 16건(깨끗한 목록·입력 불변, CRLF 목록, 해시 불일치·없음·줄바꿈만 다름, 목록 밖·`--allow-extra`, 중복·형식 오류·BSD·빈 목록, BOM, git 무시·`--rev`, 규칙 없는 미추적, 입력 오류 3종, 실제 `baseline_221456d` `--rev f67745f` → `cited_ignored` 18(없으면 건너뜀), identity 일치·불일치·head 없음·dirty·is_clean 없음·불일치·혼합 head·git 블록 없음·입력 오류 3종·`--mtime` 커밋 뒤/실행 전·후), `test_ref_check.py` 6건(찾는 순서 8종·대소문자·미추적·없음 + 후보 순위·자리표시·저장소 밖·코드 블록 제외·입력 불변, `--include-fences`·`--allow`, `--rev HEAD~1`, `--no-git`, 입력 오류 5종, 실제 `jp3_remedy_spec.md`의 `dg3_keys.txt` 첫 후보 `dg3_hash.json`), `test_junit_skips.py` 6건(건너뜀 info·입력 불변, `--critical` → 미실행 2, 패턴에 맞는 시험 없음, `--fail-on-skip`·실패·빈 실행, 입력 오류 4종, 실제 pytest `--junitxml` 출력)을 더했다: 212 passed(약 50 s). `smoke.py`에 baseline_check 2종·ref_check·junit_skips를 더했다(16실행, `status: ok`). 2026-11-20(키 기본값·xfail): `test_gate_scan_absence.py` 7건(재현 표본 → 4행 1건·입력 불변·요약 분류, 사건 꼴 실패 건너뜀 + 실패 목록 비움·기본값 없는 `get`은 출처 아님, 안전 방향(`judged == 0: raise`·`dict.fromkeys` 누적의 빈 분류 raise)과 명시 키 확인 → 0, `all(r.get("ok", True))` 판정값·빈 기본값 루프·조건식·방향 미정 info·단순 조회와 `os.environ` 제외, `--bare-get`일 때만 잡힘, 다른 판정에서 잡힌 출처 반복 안 함, 실제 `git show ad5024b:…/jp3_baseline_compare.py` → 234·238행, `--bare-get` → 225·227·240 포함(저장소 없으면 건너뜀)), `test_junit_skips.py` 4건(xfail·strict XPASS·skip 따로 세기와 심각도·`strict`·사유, xfail만 → 종료 1·`--fail-on error` → 0·`--critical` → `critical_skipped`, 실제 pytest xfail/strict xfail/XPASS/strict XPASS 출력(→ xfailed 2·xpassed 1·passed 1), J4a `junit_wt.xml` 132 + 2(없으면 건너뜀))을 더했다. `test_gate_scan_selection.py`의 사건 저장소 경로를 `C:\workspace\z4369-jp3`(옮겨져 없음 → 건너뛰던 시험)에서 메인 저장소 `C:\workspace\outrigger_control`로 바꿨다(같은 객체 저장소라 `git show`가 된다): 223 passed(약 51 s, 건너뜀 0). `smoke.py`에 gate_scan 키 기본값 표본·junit_skips xfail 표본을 더했다(18실행, 두 실행은 분류도 확인, `status: ok`). 2026-11-21(436.9 J-P3 감사 보완 4건): `test_placeholder_scan.py` 5건(기본 묶음은 `<…>`를 보지 않고 `pattern`이 예전과 같음, 명령 json의 `<prelaunch>`·`<judge_sha256 of P-1a>`와 JSON 경로·한 줄 JSON 두 문자열 안 붙음, md 코드 밖 `<br>`·`<sup>`·`<img src=…>`·`<br/>`는 `html_tag`(따옴표 속성 `<img src="…">`는 토큰 아님)·자동 링크 2종은 `autolink`로 건너뛰고 인라인 코드·코드 펜스 안 `<br>`과 `<head>`·`<프로젝트>`는 보고, ps1의 `<# #>`·`-lt` 비일치·`both`·`--allow <scratchpad>`/`scratchpad` 두 형식, `--pattern`+`--pattern-set` → 2·사용자 패턴은 건너뛰기 없음), `test_key_presence.py` 7건(키별 있음·없음·null 건수와 처음 위치·입력 불변, `--where`·`--allow-null`, **값이 stdout·md·json·`--out` 어디에도 안 나옴**, json `results[]` 자동·`--list-key` 중첩·객체 한 행, jsonl 줄 안 목록·`list_key_absent`, 행 0·선택 0·`--where` 필드 없음·깨진 줄, `--keys-file`과 입력 오류 7종 → 2), `test_baseline_check.py` 5건(저장소 기준 이름 목록: 기본은 없음 3 + `sums_base_hint`(repo-root 3/3·해시 3), `--base repo-root` → 0, 반대 방향 힌트, 정말 없으면 "기준 문제가 아니라"·일부만 없으면 힌트 없음, `--repo`·git 없으면 힌트 없음·`--base repo-root` → 2, git 작업 트리 최상위), `test_gate_scan_row_paths.py` 4건(합성 꼴 7곳 warning·주석 1곳 info, 조용한 꼴(바로 이음·이름만·`.parent.name`·뒤에 이은 이름·`is_absolute` 검사·`os.environ`·두 번 대입·lambda 인자), 메시지의 나르는 이름·`files[]`, `--no-row-paths`, 실제 보관본 `old/jp3_baseline_compare.py` 510행 잡힘·183행 조용(없으면 건너뜀))을 더했다: 249 passed. `smoke.py`에 6실행을 더했다(24실행, 분류 확인 6, `status: ok`). 2026-11-22: `test_ps1_lint.py` 8건(`--allow`가 `placeholder_scan`과 같은 뜻 — 이름만·꺾쇠·중괄호 섞음 세 형식에서 허용 자리만 남으면 종료 0·`placeholder_allowed` 3(주석 포함)·`allow`는 자리 이름, 하나만 허용하면 다른 하나는 error; 기존 자리표시 시험에 `placeholder_allowed` 확인 추가; AST·정규식 각각), `test_worktree_tests.py` 12건(worktree를 데이터 root 안에 둔 합성 배치: 다른 CWD(한글 폴더)에서 상대 `--test`로 `main` 끝까지 → 6 passed·skip 0·probe worktree 2개·감싼 줄 12·35·39·`tmp_path` 값은 `rebase_unmatched` info·scratch 비움·데이터 root 전체 SHA 불변, 자료 없음 → `skipped` warning·종료 1, 실패 → 원본 상대 경로의 `test_failed`·`probe_not_loaded`·`no_data_paths`·`rebase_never_used`, 시험이 메인 `03_src`를 `sys.path` 앞에 넣으면 `probe_foreign`·`--pin-module`이면 worktree, 감싸지 않은 `'07_results'` 글자 → 2행 warning, 시험 0개 → pytest 5·`no_tests`, `--keep` 복사본의 감싼 식·원본 경로 문자열·`__file__` 없음·줄 수 같음, 입력 오류(worktree 밖 시험·데이터 root에 없는 `--rebase-dir`·데이터 root 안 `--scratch`) → 2·scratch 비움, `_source_rebase` 단위 2건(다섯 형식·바깥 식 하나만 감쌈, CRLF·한글 앞 글자의 바이트 위치와 f-string 글자)): 273개 중 272 passed·1 failed(`test_ref_check.py::test_real_spec_names_dg3_hash_as_first_candidate` — 실제 저장소 HEAD를 읽는 시험이고 후보 1순위가 `04_scripts/01_dynamics/ds87_keys.py`로 바뀌어 실패, 이번 변경과 무관한 기존 실패), skip 0. `smoke.py`에 worktree_tests 1실행(25실행, 분류 `probe_worktree` 확인, `status: ok`).

## 알려진 한계

- **모두 휴리스틱이다.** 확정 판정은 에이전트가 코드·규칙을 읽고 내린다.
- `seal_check`의 코드 고정은 **파일 단위**다. 다른 모듈의 상수를 경유한 고정(`v5_rerun.RULES_PATH`를 `u3_judge`가 이어 쓰는 식)은 모르므로, 두 파일이 각각 일부 판만 고정한 것으로 나온다. 경로를 런타임에 조합하거나(`f"{stem}_rev{n}.md"`) 해시를 파일에서 읽어 오는 고정도 이름 문자열이 없으면 보이지 않는다.
- `code_pin_stale`은 소유 이름 휴리스틱(`rule`·`criteria`·`seal`)과 계열 판별(옆 문자열의 규칙 파일 이름, 없으면 파일 안 묶음 이름 언급)에 기댄다. 이름이 다르면 놓치고, 규칙 해시가 아닌 상수가 `RULES_*`라는 이름이면 잘못 잡는다. 경로와 해시를 다른 상수·다른 줄의 별도 목록에 두면(`PATHS = [...]`, `HASHES = [...]`) 옆 문자열이 없어 예전 규칙(파일 안 언급)으로 돌아간다.
- `--quoted`는 글자 패턴만 본다. 데이터·명령 해시(`commands_sha256` 등)는 그 원본 파일을 `--hash-files`로 주지 않으면 `quoted_unresolved`로 나온다. 숫자만인 해시 접두(8자 접두의 약 2 %)는 놓치고, 16진 글자만으로 된 일반 단어(8자 이상)는 잡힌다.
- `--const`는 첫 대입만 본다. 값을 함수·파일 읽기로 만드는 상수(`RULES_SHA256 = Path(...).read_text()...`)는 `const_no_hash`가 된다.
- `.gitattributes` 대체 해석은 매크로(`[attr]`), `!pattern` 부정, 문자 클래스 `[...]`를 다루지 않는다. git이 있으면 git 결과를 쓴다.
- `gate_scan`은 데이터 흐름을 따라가지 않는다. 가드가 다른 변수에 대한 것이어도 가드로 본다(놓침 쪽), 태그 이름 규칙에 맞는 무관한 변수(`setting == "VB"` 같은 분기)도 잡는다(과잉 쪽). 함수 밖에서 고른 집합이 비는지는 모른다.
- `record_check`는 레코드를 메모리에 다 올린다(수백 MB 결과는 `--sample`로). npz는 키·shape·dtype만, 값 재집계는 하지 않는다.
- `identity`의 `no_records`는 입력 **전체**가 0건일 때만 낸다. 여러 파일 중 일부만 비었으면 잡지 않으므로 파일마다 건수를 보려면 `--expect-count`를 쓴다. npz만 준 입력은 레코드 검사가 없는데도 0건 오류가 나지 않는다.
- `judgement_checklist`는 **글자 대조**다. 토큰이 판정서 어딘가에 있으면 found이므로, 같은 기호가 다른 맥락에 나와도 found가 된다(과잉 쪽). "위 문구", "그 이유"처럼 토큰 없는 지시는 ambiguous로만 남는다. 머리말의 사전 관찰 문장처럼 `공개`·`판정서`라는 말 없이 적힌 지시는 뽑지 못한다(놓침 쪽). 기록 동사 목록 밖의 말("판정서에 표를 둔다", "판정서로 옮긴다")도 놓친다. 반대로 판정서를 출처로 말하는 문장("판정서 7.1절의 항목을 이 규칙에 넣는다")은 뽑힌다(과잉 쪽, 토큰이 없으면 `item_missing`이 될 수 있다). 수치는 판정서 전체에서 값으로 찾으므로 흔한 값(`1.0` 등)은 쉽게 found가 된다. 앞 목록 빌리기는 **바로 앞 형제 하나**만 본다: 지시가 더 앞 형제나 다른 절을 가리키면 엉뚱한 토큰을 빌리고, 앞 목록이 규칙 내부 참조(`R16-11b`·`R16-14`)를 많이 담으면 판정서에 그 기호가 없어 `preceding_partial`이 되기 쉽다. 앞 목록 토큰이 판정서에 하나도 없을 때의 `missing`은 그 목록을 다른 말로 공개했어도 난다(과잉 쪽). 사전 예측 대조는 P-n과 대조 낱말이 **같은 줄**에 있어야 found다 — 표 행이면 맞고, "P-17은 … (줄바꿈) … 맞았다"처럼 줄이 갈리면 `prediction_not_compared`로 남는다. 대조 낱말이 다른 P-n의 것이어도(한 줄에 둘) found가 된다.
- `ps1_lint`(AST)는 범위를 **가장 가까운 함수**로만 나눈다. `& { … }`·`ForEach-Object { … }`·`Start-Job { … }` 같은 스크립트 블록은 둘러싼 범위와 같은 것으로 본다(`& { }`는 실제로는 새 범위라 과잉 쪽). 점 소싱(`. .\lib.ps1`)한 파일의 변수, 함수가 스크립트 범위 변수를 동적으로 읽는 경우, `Set-Variable -Name`·`New-Variable`로 만든 변수는 모른다(놓침 쪽). `return`은 함수 안 스크립트 블록의 것도 그 함수의 return으로 센다. `Tee-Object` 출력이 잡혔는지는 그 파이프라인 안에서만 본다(파이프라인을 감싼 `ForEach-Object`의 출력을 밖에서 잡는 경우는 모름). 자리표시는 기본 패턴 밖 형식(`TODO`·`<run head>` 소문자)을 놓치므로 `--placeholder`로 더한다.
- `ps1_lint`(정규식, `--parser regex` 또는 PowerShell이 없을 때)는 더 보수적이다: 문자열·주석은 작은 스캐너로 가리고(`'…'`·`"…"`·here-string·`#`·`<# #>`; `#`는 줄 처음이나 공백·`;({|` 뒤일 때만 주석), 함수·루프 범위는 중괄호 짝으로 찾는다. `"…$(…"…")…"`처럼 큰따옴표 안 부분식에 따옴표가 또 있으면 문자열 끝을 잘못 잡을 수 있다. 대입은 `$이름 =`(`+=` 등 포함) 꼴만, 문장 끝은 그 줄 끝이다(여러 줄 대입은 첫 줄에서 끝난 것으로 보므로, 우변 뒷줄에서 같은 변수를 읽으면 대입 뒤 읽기로 센다). `Tee-Object`가 잡혔는지는 **그 줄**만 본다. 백틱 줄 이음·여러 줄 파이프라인은 줄 단위로 끊긴다. 발견이 AST와 다르면 AST 결과를 믿는다.
- `handoff_leak`은 **글자 대조**다. 사전에 없는 이름(나중에 생긴 파일·상수)은 모르므로 사전을 넘김 직전의 코드에서 다시 뽑아야 한다(`--extra-name`으로 보탠다). 일반 낱말과 같은 이름(`COUNTS`·`TOOL_NAME`·`manifest`)은 정상 문장에서도 잡히므로(과잉 쪽) 확인한 뒤 `--allow`로 뺀다. 이름을 바꿔 쓴 누설(줄임말, 번역, 설명)은 못 잡는다(놓침 쪽). 블록 비교는 라벨이 같은 블록끼리만 하며, 라벨이 다르게 적힌(오타) 블록은 `block_single`로만 나온다. 표지 줄 자체(라벨 철자)는 블록 바이트에 들지 않는다.
- `missing_scan`은 **표시된 글자·키**만 본다. 판정 도구가 결측을 표시 없이 빈 등급·`null` 값으로만 남기면 그 키를 `--where "KEY == null"`로 따로 줘야 한다. 사유 단어 규칙(`\bno\s` 등)은 결측이 아닌 사유("no …")도 잡는다(과잉 쪽, rev23 103행이 넓게 잡으라고 한다). 행 이름은 이름 키에 기대므로, 이름 키가 없는 출력(`runs.C-6` 같은 dict 키 구조)은 경로로만 나온다. `--show-text`를 켜면 사유 문자열에 든 수치가 보일 수 있다.
- `replay_recount`는 원본·재생을 메모리에 다 올린다(G-3 원본은 jsonl 3개 약 36 MB, `--sample`은 없다). 키 SPEC은 양쪽이 같은 글자를 만들 때만 이어진다 — 하네스가 키를 다른 식으로 만들었으면(정렬·반올림) 전부 `replay_key_unknown`·`selection_missing`으로 나오므로 그때는 하네스 코드를 읽고 틀을 맞춘다. 선택 규칙은 "조건 전부 + 나머지 앞 N"만 표현한다(무작위 추출·묶음별 N은 안 됨). `--source-in` 값에는 쉼표를 쓸 수 없다(그때는 `--source-where 경로=값`).
- `log_errors`는 글자 패턴만 본다. `errors` 대신 다른 말로 실패를 찍는 단계(예: `failed 3`)는 `--pattern`을 주지 않으면 `no_errors_line`으로만 나온다. 로그가 잘렸거나 단계가 아직 끝나지 않았으면 마지막 값이 최종값이 아니다.
- `placeholder_scan`은 기본으로 중괄호 토큰만 본다. `<RUN_HEAD>` 같은 꺾쇠 자리는 `--pattern-set angle|both`로, `$MASK`·`TODO` 같은 다른 형식은 `--pattern`으로 따로 찾는다. f-string 문서 예시(`{NAME}`을 설명하는 md 문장)와 설명용 `<이름>`도 잡는다(과잉 쪽). `angle`은 120자를 넘는 꺾쇠 토큰, 숫자로 시작하는 `<1번>`, `"`가 든 `<a "b">`를 놓친다. md 코드 밖의 HTML 건너뛰기는 태그 이름 목록에 기대므로 목록에 있는 이름을 자리로 쓴 산문(`<p>`·`<a>`)은 놓치고, 목록 밖 HTML(`<section>`)은 보고한다. 코드 펜스는 줄 처음 ```` ``` ````·`~~~`만 알아보고 들여쓴 코드 블록(공백 4칸)은 산문으로 본다.
- `key_presence`는 키가 **있는지와 null인지**만 본다. 빈 문자열·빈 리스트·0·NaN처럼 "있지만 쓸 수 없는" 값은 있음으로 센다(값을 읽지 않는 블라인드 설계라서다. 값 검사가 필요하면 블라인드가 풀린 뒤 `record_check recount`). 점이 든 키 이름은 다룰 수 없다. 파일을 메모리에 다 올린다.
- `gate_scan`의 `row_value_path_no_base`는 함수 하나 안의 이름만 따라간다. 레코드 값을 다른 함수에 넘겨 그 안에서 여는 경우(`compare_reads(new_npz)`의 안쪽)는 넘기기 전의 `Path(...)`에서만 잡히고, 값을 속성·dict에 담았다가 여는 경우(`self.path`, `paths["a"]`는 `paths`가 레코드로 보여 오히려 잡힘)는 이름 규칙에 따라 놓치거나 잡는다. 레코드인지 설정·코드가 만든 dict인지는 구별하지 못한다(과잉 쪽, 판별법은 gate_scan 절). 변수 키(`row[key]`)는 보지 않는다(놓침 쪽).
- `threshold_boundary`의 `auto` 자릿수는 **찍힌 값에서 추정**한다. 행이 적거나 우연히 모든 값이 짧으면(예: 4자리 반올림인데 표본이 `0.5`·`0.25`뿐) 자릿수를 낮게 잡아 구간이 넓어진다(과잉 쪽). 저장 코드의 반올림 자릿수를 알면 `--decimals`로 준다. 반올림이 아니라 버림(truncate)으로 저장했으면 참값 구간은 `[v, v + 2h)`인데 이 도구는 대칭 구간만 본다(놓침 쪽). 판정이 float32 점수를 썼는지 등 저장 전 정밀도는 모른다. 행 필터(특정 class만)는 없다 — `--group-by`로 나눠 본다.
- `gate_scan`의 `empty_selection_sum_pass`는 함수 하나 안의 이름만 따라간다. 선택을 다른 함수에 넘겨 집계하거나(`judge(rows)` 안에서 `total(judged)`), 속성·dict 안에 담아 두었다가 쓰거나(`self.judged`, `groups["a"]`), 0건 처리를 다른 함수가 하면 놓치거나(앞 둘) 잘못 잡는다(뒤). 선택 자체의 참거짓(`if not judged: status = "pass"`)으로 pass를 내는 꼴은 실패 집합 관용구와 구별할 수 없어 보지 않는다(놓침 쪽). 0건 처리는 그 선택에 대한 것이기만 하면 위치를 묻지 않는다(판정 뒤에 있어도 처리로 본다). 2026-11-17 z4369-jp3 전체에서 나온 7건은 감사 에이전트가 코드를 읽고 판단할 후보다.
- `seal_check`·`baseline_check`의 추적 여부는 색인(`git ls-files`)이나 `--rev` 트리를 본다. "커밋돼 있다"를 증명하려면 판정에 쓴 커밋을 `--rev`로 준다(색인만 보면 아직 커밋하지 않은 `git add`도 추적으로 센다). 무시 규칙은 지금 작업 트리의 `.gitignore`로 본다(과거 커밋의 규칙이 아니다).
- `baseline_check identity`는 `"git"` 키 아래 dict만 git 블록으로 본다. 키 이름이 다른 정체성 형식(`commit`, `git_head` 평면 키)은 `identity_git_absent`로 나온다. `--mtime`은 지금 작업 트리의 mtime이라 다시 체크아웃하면 의미가 없다.
- `ref_check`는 인라인 코드 안의 토큰만 본다. 백틱 없이 쓴 파일 이름, 링크 `[x](path)`(→ integrity `md_links.py`), 알려진 확장자가 아닌 파일(`Makefile` 외 확장자 없는 이름)은 놓친다. 문서가 다른 저장소·worktree의 파일을 가리키면 `ref_missing`이 된다(그 저장소를 `--repo`로 따로 돌린다). 후보는 이름 줄기의 글자 비교라 이름이 전혀 다른 실제 파일(`keys` ↔ `hash`)은 공유 조각(`dg3`)이 있을 때만 위로 온다.
- `gate_scan`의 `missing_key_default_pass`는 **"조회한 키가 모두 없다"는 한 가지 가정**만 평가한다. 키 하나만 빠진 경우의 방향은 따로 보지 않는다. 다른 함수가 돌려준 기본값(`_check(record)`가 `… or {}`를 돌려줌), 속성(`self.x`), `getattr(o, "x", 0)`, 루프 반복(값이 반복마다 쌓이는 것)은 따라가지 않는다(놓침 쪽). 같은 이름을 두 번 대입하면 흐름과 무관하게 합치므로 뒤 대입이 앞 판정을 흐리게 한다(놓침 쪽). 대문자 이름은 비지 않은 모음으로 가정한다. 실패 동작·실패 목록은 이름 휴리스틱(fail·problem·error…)이라, 설정 기본값 비교(`mode == "off"`)·멱등 표식처럼 판정이 아닌 분기에서 `raise`·`return False`가 있으면 거짓 양성이 난다. 문자열 기본값끼리의 비교(`r.get("status", "pass") != "pass"`)는 잡지만 설정 분기와 구별하지 못한다. "잡힘" 억제는 같은 함수 안의 다른 판정만 본다.
- `junit_skips`는 JUnit XML만 읽는다. strict 아닌 XPASS는 pytest가 통과로 적으므로 보이지 않고, xfail의 strict 여부도 XML에 없다. `-rs` 텍스트 출력이나 junit을 남기지 않은 샤드는 볼 수 없다(사건의 `shard6: no junit xml`처럼). 패턴은 시험 이름 기준이라, 이름을 바꾼 필수 시험은 `critical_absent`로 드러난다.
- `worktree_tests`는 **복사한 파일 안의 글자 꼴**만 바꾼다. 데이터 경로를 다른 모듈(복사하지 않은 `04_scripts` 모듈·worktree 보조 모듈)에서 만들면 그 모듈은 worktree를 읽는다 — `--support`로 함께 복사하거나 그 모듈의 `ROOT`를 쓰는 식을 시험 쪽에서 감싸야 한다(`s9_batch.ROOT / "07_results"`는 시험 안이라 감싸진다). 폴더 이름을 상수·f-string으로 조합하면(`ROOT / NAME`, `f"{ROOT}/07_results"`) 감싸지 못하고 `data_literal_not_rebased`로만 알린다. `--rebase-dir`는 최상위 폴더 단위라 추적 폴더 안의 git 제외 파일(`06_analysis/**/*.npz`, `*.h5`)은 옮기지 못한다(그 폴더를 통째로 옮기면 worktree에서 바뀐 추적 파일까지 메인 것을 읽는다) — 그런 시험은 `OUTRIGGER_RECORDS_ROOT` 같은 시험 자체의 환경 변수(`--env`)를 쓴다. `__file__` 고정은 이름 `__file__`만 바꾸므로 `inspect.getfile(모듈)`·`sys.modules[__name__].__file__`처럼 다른 길로 얻은 위치는 복사본(scratch)이다. 패키지 안 상대 import(`from . import x`)로 같은 폴더 모듈을 읽는 시험은 그 모듈을 `--support`로 복사해야 한다. probe는 `pytest_sessionfinish`에서 `sys.modules`를 보므로, 시험이 도중에 지운 모듈이나 자식 프로세스(하네스 subprocess)가 import한 모듈은 모른다(`probe_not_loaded`). 실행 중 출력은 실행 폴더의 `pytest.log`에만 있고 보고에는 끝 60줄만 남는다(전체가 필요하면 `--keep`).
- `timeline`의 git 시각은 커밋 시각이라 "그때까지 있었다"는 상한일 뿐이다. 규칙을 결과와 같은 커밋에 넣었으면 git만으로는 순서를 가를 수 없다. mtime은 체크아웃·덧붙임으로 바뀐다.
