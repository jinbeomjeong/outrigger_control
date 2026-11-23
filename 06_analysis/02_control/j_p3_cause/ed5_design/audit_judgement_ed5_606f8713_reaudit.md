## 감사 요약 (판정서 재감사, 커밋 직전)
- 본 결과: 판정 후 감사라서 값을 봤다. 본 파일은 다음과 같다.
  - `jp3_rev6_j9main_p2.json`(상태, 건수, `by_setting`, flags, 정체성 값)과 `j9main_judge.json` `J-P3.rev6`
  - `t12_VBH.json`·`t12_VBJ.json`(READY 실패 키, 등급 전이, 추적기 기록)
  - `ckdrop_record.json`(`d1_undecided_periods`), `baseline_compare.json`(`case_bd.D.numeric`)
  - `verif_at_run/SHA256SUMS`, 경로 2 보고 `p2_report_dynamics_j9main.md`
  - 블라인드 경로(`cdry_a1/VBK_c92*`·`VBK_c93*`·`logs/`)는 열지 않았다.
- 대상: `06_analysis/02_control/j_p3_cause/jp3_ed5_j9main_judgement_606f8713.md` sha256 `9a54ffac…`(감사 시작과 끝에 같음). 기준 문서는 지난 감사와 같다.
- 판정: 차단 0 / 수정 필요 0 / 기록 5
- **판정서 커밋 가능.** 지난 감사의 M-1~M-9와 고칠 문장 목록 1~16이 모두 반영됐다. 경로 2 j9_main J-P3 결과는 원본과 맞는다. 기록 5건은 선택 사항이다(고치지 않아도 커밋해도 된다).

## (1) 고칠 문장 1~16과 M-1~M-9 반영 확인
| 항목 | 판정서 위치 | 결과 |
|---|---|---|
| M-1 12b 통과 문장 | 2.1, 94행 | 정오 8 8-10 원문(`erratum8.md:287`)과 문장이 같다. 값은 `judge.json` `pass_sentence`와 같다(327, 334, 0.008929, 2 ≤ 7, k 160, 0.018549) |
| 8-5 표·해석·약점·3.2 %/0.4 % | 98~110행 | 정오 8 `:127-134`·`:82`·`:87`과 네 행 모두 수치가 같다 |
| 기회 분류·n23 분해·셀·블록·k·A/A·서명·등급 전이·ungraded | 111~147행 | `judge.json`과 같다. 등급 전이 키 3개와 `ungraded_pairs` 0도 맞다 |
| M-2 j9_main J-P3 경로 2 | 0절 16행, 7.2 414~421행 | 범위 근거 세 가지를 인용했다. 경로 2 실행 결과를 넣었다 |
| M-3 c 건식 seed | 76행, 5절 6 288~291행, 7.3 #6 | 정오 6 6-3과 실행 전 감사 7항 인용이 맞다 |
| M-4 공개 의무 | 5절 14 (가)~(차), 2.2 | 인용이 원문과 같다(원판 `:166`, `:468`, `:520`, 정오 1 8절과 2-2 `:56-57`, 정오 2 `:199`·`:256-259`, 정오 5 `:8`, 정오 7 `:18`). 결과값도 원본과 같다: (바) `computed: false`와 사유, (아) `same_order` false·`status` record와 실패 문자열 두 개 |
| 2.2 13.9 기록 값 | 149~159행 | `t12_VBH.json`·`t12_VBJ.json`과 같다(READY 실패 키 4개, L3 전이, 개선 2키, 7,812/7,812/311, 380·7.8 s, VBJ 42/42/0·5·0.2 s) |
| M-5 | 5절 5·6·11 | $k_{allow}$ 결정 순서, 8003083d 처리, 도구 sha가 맞다. `baseline_check.py` b31dde7f…와 `_git.py` 49c60bc7…는 `verif_at_run/SHA256SUMS`와 같다. 블록 40~43과 로컬 전용 입력 목록도 맞다 |
| M-6 '잠정' | 15·18~23행 | 9절 T4h 행과 개정 8 8절을 근거로 들고, 앞 ③의 3단계 문구를 분리해 적었다. 규칙에 맞다 |
| M-8 | 213~214행 | "(S8 제외)", "거의 모두"가 들어갔다 |
| R-1, R-4~R-6, R-8 | 2.1, 7.2, 0절, 2절, 5절 1 | 반영됐다 |
- seal_check `--quoted`로 새로 들어간 해시가 모두 풀렸다(572f2f39, b31dde7f, 49c60bc7, f7ee17d2, 78fe9724). 풀리지 않은 것은 두 종류뿐이다.
  - 이번 실행에서 규칙 파일 인자를 빼서 생긴 것(넘김·v5 기준 해시). 지난 감사에서 풀렸다.
  - 원래부터 파일 해시가 아닌 것: 명령 해시 3개와 앞 판정서 해시 07dfa030.

## (2) 경로 2 j9_main J-P3
- 중립 입력: `INPUTS_j9main.SHA256SUMS` 389항목을 원본(`j9main_a1/j9_main.jsonl`, `j9_main_t4h` 388개)과 독립 대조했다. 389/389가 일치하고 누락은 0이다.
- 값 대조: 경로 2 `jp3_rev6_j9main_p2.json`(572f2f39)과 경로 1 `J-P3.rev6`를 비교했다.

  | 항목 | 경로 2 | 경로 1 |
  |---|---|---|
  | 상태 | pass | pass |
  | 판정 행 | 200(설정마다 40) | `runs_judged` 200 |
  | breach | 0/0/0 | 0/0/0 |
  | `judged_key_missing` | 0 | 0 |
  | 로드 판독 없음 | 188(VBJ 60, LSJ 각 32) | `no_rod_reading` 188 |
  | 기록 행 | 0 | `record_only_sensor_grade` 0 |
  | 결함 | 0 | 0 |

  판정서 7.2 402~405행과 모두 같다.
- 도구: `65e0678d`의 부모는 dde4499d다. 바뀐 파일은 path2 판정 둘과 시험 하나다. worktree는 locked이고 깨끗하다. 12a·12b 결과는 dde4499d에서 만들었다고 7.1에 바르게 적혀 있다.
- 독립성: 보고 공개 절(`p2_report_dynamics_j9main.md:65-67`)은 새로 연 것이 중립 입력 `j9main\`과 그 SHA 목록뿐이라고 적는다. 대화 기록과 대조하지는 않았다.
- 근거 폴더: `ed5_p2_606f8713/SHA256SUMS` 12항목이 mismatch 0, missing 0, unlisted 0이고 LF다. 무시 규칙에 걸리는 파일은 없다.

## (3) 메인 몫
- M-7
  - `decision_log.md:813`에 불합격, 경로 2 실행, 읽기 (1)~(3), P1 공칭·안 C 버림, D0, 낙관 공개가 들어갔다.
  - 로드맵에는 27·331·355행이 들어갔다.
- M-9: `baseline_check sums` 결과는 다음과 같다.

  | 대상 | 항목 | mismatch | missing | CRLF | 비고 |
  |---|---|---|---|---|---|
  | `ed5_j9fail_606f8713/SHA256SUMS` | 16(원문 md와 INPUTS SUMS 포함) | 0 | 0 | 0 | unlisted 4는 하위 `hydraulics/`(자기 SUMS가 덮음) |
  | `hydraulics/SHA256SUMS` | 3(원문 md 포함) | 0 | 0 | 0 | – |
  | `ed5_judgement_606f8713/SHA256SUMS` | – | 0 | 0 | 0 | 그대로 |

  `cited_untracked`는 아직 커밋 전이라 나온다. ignore 0이다.
- 판정서 감사 원문 `ed5_design/audit_judgement_ed5_606f8713.md`가 있다. 원문의 특징 문장 3개를 확인했다.

## (4) 새 오류
- ref_check의 ref_missing은 18건이다. 지난 13건에서 5건이 늘었다.
  - 늘어난 것 가운데 셋은 같은 꼴의 오탐이다. 미추적 근거 폴더 안의 맨 이름 `tjr12b_p2.json`(132행), `jp3_rev6_j9main_p2.json`, `p2_report_dynamics_j9main.md`(373행)이다.
  - 나머지 둘은 로컬 전용(ignore) 입력 이름이다. 318행 `dg3_VBH.json`·`dg3_VBJ.json`과 319행 `L1_VBJ.json`이고, 5절 11에 로컬 전용으로 공개돼 있다.
  - 새 결함은 없다.

## 기록 (선택)
1. 2.1 123행 "판정 후 감사의 `decision.witness_pairs` 재계수"는 출처가 틀렸다. "판정서 감사"가 맞다.
2. 7.2 376행은 대조 스크립트를 `p1p2_compare.py`라고 적었다. 그러나 j9_main 4행은 그 스크립트 밖에서 손으로 옮긴 값이다(`p1p2_compare.json` 입력은 12b·12a 둘뿐이고 SUMS도 그대로다). 408행 출처 문장에 "스크립트 밖 손 대조, 판정서 재감사가 독립 확인"을 더하면 정확해진다.
3. 표지 값이 두 경로에서 다르다. 판정 키가 아니고 7.2 표에도 없다. 2.1 147행처럼 경로 1 표지를 적을 때 두 경로 값을 비교 가능한 것으로 읽지 않게 한다.
   - `jp3a_margin_used` 표지: 경로 1은 j9_main 0·12b 0, 경로 2는 j9_main 25,434·12b 207,299다.
   - [추정] 정의가 다르다.
4. 경로 2 j9_main 출력의 `constants.spec_edition`이 rev 5 값 `8be9de22`다. 정체성은 기록만 했고 관측값은 fe6f5844다. 판정 영향은 없다. 판 6 넘김(정체성 문장)과 함께 정리할 일이다.
5. 넘김 번호 중복("넘김 6")과 경로 2 도구가 브랜치에만 있는 문제는 지난 기록 그대로다. 브랜치는 lock으로 보존된다.

## 검사하지 못한 것
- 경로 2가 실제로 연 파일은 보고서의 자기 진술로만 확인했다. 대화 기록과 대조하지 않았다.
- 65e0678d의 "rev 5 동작 불변"은 시험 109 통과라는 보고로만 확인했다. 경로 2 시험을 다시 돌리지 않았다.
- 판정서 비교 대상 `audit_judgement_ed5_606f8713.md`가 원문을 전부 그대로 담았는지는 특징 문장 3개로만 확인했다.

## 실행한 검증
- python-dev `-I -B -X utf8`, `MKL_THREADING_LAYER=TBB`, PowerShell 도구로 실행했다.
- 도구
  - `seal_check`(`--quoted` 77, 풀리지 않은 9건은 위 사유)
  - `ref_check`
  - `baseline_check sums` ×4
  - `source_guard` snapshot·verify
- 즉석 스크립트 `r1.py`(중립 입력 389 대조, 경로 2·경로 1 값)와 `r2.py`(2.2·5절 14 원천 값)는 scratchpad `auditor-ed5report2\`에 두었다가 폴더째 지웠다.
- git 조회: `log`, `diff --stat`, `worktree list`, `status`, `check-ignore`, `ls-files --eol`.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_ed5_j9main_judgement_606f8713.md 9a54ffac…, jp3_rev6_j9main_p2.json 572f2f39…, p2_report_dynamics_j9main.md eaaa7612…, SHA256SUMS 95a1e18f…, SHA256SUMS 49bf07af…, SHA256SUMS 26c1efa3…, j9main_judge.json fbdf6c41…, decision_log.md dc1bfbed…, 00_roadmap.md a18557ba…, jp3_remedy_spec_v5_erratum8.md 8c420e85…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
