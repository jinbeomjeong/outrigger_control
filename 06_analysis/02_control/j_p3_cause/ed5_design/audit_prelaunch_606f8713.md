# verif-protocol-auditor: 판 5 실행 커밋 606f8713 step0_cdry 직전 재감사 (2026-11-23)

(hand-back 원문 그대로)

## 감사 요약
- 대상: 436.9 J-P3 판 5. 실행 커밋은 `606f87131a7f13468f1db37cf6c811c442a6caf0`이고 worktree는 `C:\workspace\outrigger_control\.claude\worktrees\ed5-run5`(locked)다. 이번 감사는 step0_cdry 직전의 재감사이며, 시점은 실행 전이다.
- 기준 문서: 원판 `jp3_remedy_spec_v5.md`, 정오 1~7. seal_check 결과는 판 8개, 계열 8개, 발견 0이다. master HEAD는 `0520040e`다.
- 본 결과: 판정 값은 보지 않았다.
  - 본 것은 구조뿐이다. `x11/selection.json`에서는 seed_index, seed_repeats, dry.seeds, union_check, 스캔 파일 목록을 봤다. c92·c93·b1~b4 계획 파일은 키 수와 seed 토큰만 봤다.
  - 그 밖에 본 것: `dry_selection.json` 세 판의 구조 차이, identity 블록(head, is_clean), 로그의 `errors N` 줄 유무, junit 통과·skip 수.
  - judge 폴더, c 건식 출력, L1 출력 값, p52·p54 값은 열지 않았다.
- **판정: 차단 0 / 실행 전 수정 1 / 기록 4. step0_cdry 시작 가능.**

## 항목별 확인

**1. 정오 6·7 구현과 6-6 커버리지 표가 실행 커밋에 맞는가: 맞음**
- 계보:
  - `git merge-base --is-ancestor aa810ef1 606f8713`은 참이다. 722a1cbc(fix3)와 addc179a(정오 7)도 606f8713의 조상이다.
  - `git diff --stat aa810ef1 606f8713 -- 03_src 04_scripts 05_tests`의 출력은 비어 있다.
  - 606f8713 자체가 바꾼 것은 `ed5_design/run_commit_note.txt` 한 파일(16줄)뿐이다.
- `coverage_6_6_aa810ef1.md`를 독립 스크립트로 대조했다.
  - 별칭 15개, `별칭::시험` 참조 126개를 `junit_aa810ef1_fix3_all.xml`과 맞춰 보니 없는 것 0, 통과 아닌 것 0이다.
  - "해당 없음" 칸은 23개이고 모두 이유가 적혀 있다.
  - `junit_skips`는 582개 모두 통과, skip 0, 종료 0이다.

**2. mtime 도구 수정(`_git.py` f7ee17d2 → 49c60bc7)과 공개 방식**
- 지금 쓰는 `~/.claude/tools/verif/_git.py`의 sha는 `49c60bc79d10…`다.
- 옛 판은 `ed5_design/run_commit_606f8713_evidence/verif_before/_git.py`에 보존돼 있다(SUMS 25행 `f7ee17d2…`).
- 옛 판과 새 판으로 606f8713의 l1ref_a1·p5fixed_a1에 `identity --mtime`을 각각 돌렸다.
  - 결과는 같다: 변경 파일 1, 늦은 파일 0, error 0, 종료 0.
  - 606f8713은 부모가 하나인 커밋(부모 81871a68)이라, merge를 비교하는 방식의 수정과는 상관이 없다.
- 공개:
  - 앞선 merge 실행 커밋의 공허 통과는 `run_commit_note.txt` 10~13행에 적혀 있다.
  - 재집계 결과는 evidence `recount/*.json`에 있다.
- 남은 공백은 실행 전 수정 W-1로 적었다. 새 판 sha가 어디에도 고정되어 있지 않다.

**3. 고정 목록 `FIXED_INPUTS_606f8713.SHA256SUMS`(254항목): 맞음**
- 추적·속성:
  - git이 추적하고 있다(`--error-unmatch` 통과).
  - `i/lf w/lf attr/-text`이고, `text: unset`이다.
- `baseline_check sums --base repo-root --rev HEAD` 결과: 항목 254, mismatch 0, missing 0, CRLF 0. 종료 1은 cited 8건 때문이다(기록 R-1).
- 들어 있는지 독립 스크립트로 확인했고, 각각 1개씩 있다.
  - 정오 5·6·7과 각 `.sha256`
  - `x11/c92_plan`, `c92_keys`, `c93_plan`, `c93_keys`, `selection.json`
  - `606f8713/l1ref_a1/L1_VBJ.json`(304023ff, LOCAL_ONLY 목록과 같은 값), `L1_VBJ0.json`
  - `p5fixed_a1/judge/p52.json`, `p54.json`
  - `dry_selection.json`, `l1_keys_12b.txt`
  - v0 표본 키와 그 명령 파일
  - step0_cdry, common_ed5
- 그 밖의 수: ckdrop 11, b1~b4 계획 4, run_steps_ed5 19.
- 중복은 0이다. 876d8a49·ae9d0b2d 경로는 목록에 0개다.

**4. `dry_selection.json` sha가 바뀐 근거: 스캔 목록만 다름**
- 876d8a49판, ae9d0b2d판과 전체를 재귀로 비교했다. 다른 곳은 `.scan.excluded`, `.scan.files`, `.scan.files_excluded`, `.scan.files_scanned` 네 경로뿐이다. 생성 키와 가족별 선정은 같다.
- 키 파일 sha:
  - `dry_selection_r79_key_g8.txt`는 b7c7470a이고 옛 판과 같다.
  - `dry_selection_r79_key_ref.txt`는 95ce6f27이고 옛 판과 같다.
  - g6 키 파일 1a79e02f는 P5-3 기록 `hashed_files`에 있다.

**5. 정오 6 6-4의 "한 번" 규칙: 지켜짐**
- 시각 순서(모두 11-23):
  - 커밋 01:02:53
  - dry 01:04:12 → l1keys 01:04:21
  - l1ref.done 01:44:07(a1) → p5fixed.done 02:00:11(a1)
  - x11 02:05:20 → ckdrop 02:05:52 → v0sample 02:05:59
- `j9_runs/606f8713`에는 `l1ref_a1`, `p5fixed_a1`, `.done` 둘만 있다. `.stop`과 `_a2`는 없다.
- 코드에도 "있으면 거부" 장치가 있다.
  - `prelaunch_ed5.ps1:54,65,73,81`
  - `jp3_12b_l1_keys.py:79-87`(`open("x")`)
  - `step_l1ref.ps1:14`, `step_p5fixed.ps1:28`
- 보관:
  - `j9_runs/876d8a49`에는 ed5_inputs, l1ref_a1, l1ref.stop, SHA256SUMS가 있다.
  - `j9_runs/ae9d0b2d`에는 ed5_inputs와 출력 전부, cases.stop, SHA256SUMS가 있다.

**6. P5-3 집합을 정오 5 5-1 규칙으로 다시 뽑았는가: 맞음**
- ① `git diff --name-status --diff-filter=A 5632b618 606f8713 -- '05_tests/unit/test_*.py'`로 13개가 나왔다. `p53set_606f8713.txt`와 같다.
- ② `test_x10_rod_fault.py`를 `X10_BASE_ROOT=…\x10base`로 돌렸다. junit에서 x10 시험 줄 78개를 확인했다.
- ③ df95158d..606f8713 사이에 고친 파일 9개를 파일별로 `-U0` diff해서 새로 생긴 `def test_`를 찾았다. `test_jp3_prelaunch_audit2.py`의 3개뿐이고 `p53set3`과 같다.
  - `test_d1a`는 서명만 바뀌어서 새 시험이 아니다.
- junit 결과:
  - p53set: 352 통과, skip 0, 종료 0
  - p53set3: 3 통과, 종료 0
  - t45 데이터 재실행: 19 통과, 종료 0
- 회귀 기록 `regress4a`: 249개 중 244 통과, skip 5. skip 5개는 모두 `test_chrono_t45_replay`다(공개 의무는 기록 R-3).

**7. step0이 seed 92·93을 쓰는가, step1에 c 관문이 있는가: 둘 다 맞음**
- step0:
  - `step0_cdry.ps1:21` `$DryRuns = @('c92','c93')`
  - 31·33행은 런마다 자기 `${Run}_plan.json`과 `${Run}_keys.txt`를 쓴다.
  - 19행은 `union_check.ok`를 요구한다.
- selection 값: `dry.seeds = [92, 93]`, `union_check = {pairs 160, distinct_keys 160, cells 8, ok true}`. c92·c93 계획과 키는 각각 80개다.
- step1:
  - `step1_p1.ps1:14`에 `Requires @('cdry')`가 있고, 17~20행이 `Get-DryCStop`을 부른다.
  - `record_gates_ed5.ps1:139-149`: 파일이 없으면 3, status가 written이 아니면 2, c가 없으면 2, `c ≥ 0.5`면 2를 낸다.

**8. 도구 점검(종료 코드)**

| 도구 | 대상 | 종료 |
|---|---|---|
| seal_check | 원판 + 정오 1~7 | 0 |
| baseline_check sums | FIXED_INPUTS_606f8713 | 1(cited 8건, R-1, mismatch·missing 0) |
| baseline_check identity --mtime | l1ref_a1 / p5fixed_a1 | 0 / 0(head 1, dirty 0) |
| placeholder_scan --pattern-set both | run_steps_ed5/*.ps1 18개 | 0(허용 18건은 모두 `#` 주석 줄, 주석 밖 0) |
| ps1_lint | step0_cdry, common_ed5, record_gates_ed5, step1_p1 | 0(AST) |
| junit_skips | p53set / p53set3 / t45data / fix3_all | 0 / 0 / 0 / 0 |
| junit_skips --critical t45 | regress4a | 1(skip 5, 회귀 기록, R-3) |
| log_errors | l1ref_a1·p5fixed_a1 logs | 0 / 0 |
| ref_check --rev 606f8713 | 정오 6 / 정오 7 | 1(`ed5_inputs/`는 커밋 뒤에 만들어지는 설계라 정상) / 0 |

## 발견 사항 (심각도순)

[실행 전 수정][I·S] W-1. 단계의 정체성 관문이 저장소 밖 verif 도구를 sha 고정 없이 부른다
- 근거:
  - `common_ed5.ps1:211-217`의 `Invoke-IdentityCheckPart`와 4a `Invoke-IdentityCheck`는 `$VerifTools\baseline_check.py`를 부르고, 종료 코드가 0이 아니면 2로 멈춘다.
  - 단계 기록에는 명령줄만 남는다(213행).
  - evidence SUMS에는 옛 `_git.py`(f7ee17d2)만 있다. 새 판 `49c60bc7…`과 `baseline_check.py`의 sha는 저장소 어디에도 없다(Grep `49c60bc7` 0건).
- 실패 시나리오: 실행 도중(step0~step8, 몇 시간) python-expert가 tools/verif를 다시 고치면, 관문이 다른 판의 도구로 판정되는데 그 사실이 기록되지 않는다.
- 지금은 차단이 아니다. 606f8713에서는 옛 판과 새 판의 결과가 같음을 확인했기 때문이다(항목 2).
- 권장 조치(메인 세션):
  - step0 전에 `_git.py`와 `baseline_check.py`(가능하면 tools/verif/*.py 전부)의 sha를 evidence 폴더에 적는다(예: `verif_at_run/SHA256SUMS`, 사본 포함).
  - 판정이 끝날 때까지 tools/verif를 고치지 않는다.
  - 판정서 머리말에는 "정체성 관문 도구 sha"를 적는다.

[기록][R·T] R-2. 정오 6 6-3의 예상 "b 블록 50~53"이 실현되지 않았다. 실제는 40~43이고 반복 0이다
- 근거:
  - `selection.json`: `blocks.b1..b4.seed_index = 40..43`, `seed_repeats = 0`.
  - 정오 6 87행: "`ae9d0b2d`의 b 계획(40~43)이 스캔에 있으므로 50~53으로 옮겨질 것으로 본다. 반복 수를 기록한다."
- 원인(코드):
  - `jp3_12b_plan.py:96`의 `R79_KEY_PATTERN`은 `"key": "…"` 필드만 잡고, 98행에서 스캔 대상을 .json·.jsonl로 한정한다.
  - 계획 파일은 키를 dict 키로 담고 키 목록은 .txt다. 그래서 보관된 ae9d0b2d·dba05b3f 계획은 스캔은 됐지만 r79_keys가 0으로 나왔다(selection `scan.files`에서 확인).
- 원시 토큰 `L2|s4[0-3]|`을 06_analysis 전체(json·jsonl·txt·md)에서 찾았다.
  - 나온 곳은 dba05b3f·ae9d0b2d·현재의 b1~b4 계획과 키 파일뿐이다.
  - 실행 기록(결과 줄)은 0건이다. 40~43 키로 돌린 실행은 없고, 본 결과를 다시 쓰는 일도 없다.
  - 앞선 판 ae9d0b2d도 같은 꼴로 40~43이었다.
- step0에는 영향이 없다(c92·c93 키는 스캔과 충돌하지 않음, `dry_plans`가 확인).
- 권장 조치: 판정서에 "6-3 예상(50~53)과 달리 40~43, 반복 0, 이유는 4a-4의 r79 키 정의(실행 기록의 `key` 필드)"를 공개한다. 해석은 아래 확인 필요 1로 올린다.

[기록][S] R-1. 고정 목록의 cited 8건(ignore·미추적)은 ae9d0b2d 목록과 같은 집합이다
- 해당 파일:
  - `606f8713/l1ref_a1/L1_VBJ.json`(203.5 MB, `l1ref_a1_LOCAL_ONLY.SHA256SUMS`가 추적되고 sha가 같다, 백업 `~/.claude/backups/outrigger-ed5/606f8713_l1ref_a1/`)
  - 78fd5d2d `dg3_VBH`·`dg3_VBJ.json`(dg3_a1 LOCAL_ONLY 목록)
  - `v5/main.jsonl`과 `resume_k1` 네 파일(4a 고정 상수가 sha를 고정)
- 저장된 `sums_fixed_ae9d0b2d.json`에도 같은 cited 항목이 있다. 현재 목록에는 불일치·누락이 없다(ae9d0b2d 보고의 mismatch·missing은 판이 바뀐 뒤의 것).
- 판정서에는 로컬 전용 입력 목록으로 적는다.

[기록][E] R-3. 회귀 기록에서 `test_chrono_t45_replay`가 5개 skip됐다. 정오 5 5-1 33행에 따라 판정서에 공개할 대상이다
- 근거:
  - `junit_606f8713_regress4a.causes.json`: 원인은 시험 환경(worktree에 07_results 없음).
  - `worktree_tests.py`로 다시 돌린 결과(`junit_606f8713_regress4a_t45data.xml`)는 19 통과, 종료 0이다.
- 권장 조치: 판정서에 skip 사실과 재실행 근거 파일 두 개를 함께 적는다.

[기록][T] R-4. mtime 도구 수정의 공개 문장에는 공허 통과 건수와 도구 sha가 없다
- `run_commit_note.txt` 10~13행은 수정 사실만 적었다. 건수(dba05b3f 68, 8003083d 44, ae9d0b2d 4)는 evidence `recount/*.json`에만 있다.
- 판정서 공개 목록에 건수, 옛·새 sha, "606f8713에서 두 판의 결과가 같음"을 함께 적는다(W-1과 같이 처리).

## 확인 필요
1. 정오 6 6-3 87행의 "50~53으로 옮겨질 것으로 본다"를 어떻게 읽을지 정해야 한다(control 또는 사용자).
   - 예상 문장으로 읽으면: 6.3.1 규칙(4a-4 1절의 r79 키 = 실행 기록 `key`)대로 40~43, 반복 0이 맞고, 판정서 공개(R-2)로 충분하다.
   - 요구로 읽으면: 계획·키 파일의 키도 충돌로 쳐야 한다. 그러면 x11을 다시 만들어야 하는데, 이는 6-4 "한 번"과 부딪친다(멈추고 묻기).
   - 이 감사는 앞의 읽기를 가정했다. 근거는 원판 230행의 "r79 키"와, 40~43 키로 돌린 실행 기록이 0건이라는 점이다.

## 위임 필요
- 없음. 도구 결함은 찾지 못했다. W-1의 sha 고정은 메인 세션이 할 기록 작업이다.

## 메인 세션 권고
- step0_cdry 시작 전에 W-1(verif 도구 sha를 evidence에 고정)을 한다. 이 작업은 커밋 하나로 끝나고 실행 커밋과 FIXED 목록에는 영향이 없다.
- step0 뒤 step1 전에는 `log_errors.py <cdry_a1 logs>`와 `baseline_check identity`가 종료 0인지 본다(Invoke-IdentityCheck가 이미 관문으로 확인함).

## 검사하지 못한 것
- `X10_BASE_ROOT` worktree(`x10base`)가 X-10 이전 커밋인지는 다시 확인하지 않았다. 앞선 감사의 확인을 그대로 따랐다.
- c 건식은 실행 전이라 step0의 실제 키·계획 짝을 러너 가드와 맞춰 보지 못했다. 다만 키 수 80·80, union_check ok, 단계 스크립트가 seed별 짝을 쓰는 것은 확인했다.

## 실행한 검증
- 인터프리터는 python-dev(`-I -B -X utf8`, `MKL_THREADING_LAYER=TBB`)를 썼다.
- git 조회:
  - worktree HEAD·status·lock, `--is-ancestor`, `diff --stat`
  - P5-3 ①·③ 추출, `ls-files --eol`, `check-attr`
- verif 도구: seal_check, baseline_check sums, baseline_check identity ×2(새 판), 옛 `_git.py` 사본 identity ×2, placeholder_scan, ps1_lint, junit_skips ×5, log_errors ×2, ref_check ×2.
- 즉석 스크립트(구조만 봄): `inspect.py`, `scan.py`, `scan2.py`, `scan3.py`, `sums_cmp.py`, `cov.py`.
- scratchpad `…\scratchpad\verif-ed5run5\`(스크립트, 옛 도구 사본, guard state)는 보고 전에 지웠다(`Test-Path` False).
- 메모리 `audit_pitfalls.md`에 seed 스캔 키 정의 함정 한 줄을 Edit로 더했다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha FIXED_INPUTS_606f8713.SHA256SUMS d0222005…, common_ed5.ps1 579391e8…, step0_cdry.ps1 910446ca…, step1_p1.ps1 f933ec19…, record_gates_ed5.ps1 d00d52fc…, dry_selection.json 5085530b…, coverage_6_6_aa810ef1.md 31ae7a98…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
  - source_guard snapshot은 첫 도구 실행 뒤에 떴다. 그 전에 실행한 명령은 조회뿐이었다.
- 사용한 스킬: 없음
