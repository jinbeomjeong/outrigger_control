## 무결성 검사 요약
- 대상: 파일 3개(ed8-judge3의 변경 2 + 새 시험 1)와 근거 폴더 `t8ppp_evidence` 22개(범위: 호출자 지정, 전수)
- 판정: ✅ 통과. 차단 0, 권고 4(Low~Medium)
- 축별 발견: A 0 · B 0 · C 0 · D 1(Low) · 커밋 전 점검 3(권고)

## 차단 (커밋 전 고칠 것)
없음.

## 권고
1. [Medium] P8-4가 보고서 자체 인정대로 깨끗한 통과가 아니다.
   - 근거: junit을 직접 세어 보고서와 일치했다. T8‴ 9054건 = 통과 8916 / 실패 2 / 오류 2 / 건너뜀 134, 저장된 T8″ 9031건 = 8895 / 2 / 0 / 134.
   - 새 오류 2건은 `test_k2_chrono_runner`(`l1r_variant` import)다. 단독 실행은 30/30 통과(junit 직접 확인)이고, 바뀐 모듈과 무관하다.
   - 정식 P8-4를 러너로 다시 돌릴지(보고서의 (나))는 메인이 판단한다.
2. [Low] 보고서 5절에는 폴더 SUMS가 "쓰지 않았다"로 되어 있다. 지금 `SHA256SUMS`는 이미 존재하고(sha `cc09451b…`, 21 항목) 정상이다. 보고서 문구만 낡았다.
3. [Low, 커밋 절차] `t8ppp_evidence`(22개 파일)는 git에 추적되지 않은 상태이고 ignore에는 걸리지 않는다. `baseline_check sums`가 `cited_untracked` 22건을 냈다. 근거 폴더를 같이 커밋하려면 `git add`가 필요하고, 새 시험 파일도 `??` 상태다.
4. [Low] 보고서의 "Suspended git PID 58136"은 이미 없다. `Get-Process`로 58136과 89112를 조회했으나 둘 다 나오지 않았다. 재개 조치는 필요 없다.

## 이상 없음 (확인한 것)
1. 코드↔명세: diff 전문을 읽었다.
   - `ED8_JP3_JUDGED_SETTINGS`는 판정 10개로 `d1_settings.json`·명세 4절과 정확히 같다.
   - `ED8_P3_OFF_SETTINGS`는 ("VBN0", "VBKN0")이고, 명세·json과 일치한다.
   - `ed8_jp3_settings()`는 대입까지 `try` 안에 두고, `finally`에서 저장해 둔 원 튜플 객체를 되돌린다.
   - import 시점에는 아무것도 켜지 않는다. 켜는 곳은 `jp3_of`의 `with`와 `edition_8()`뿐이다.
   - `_tjr_judged_settings()`는 `tjr7.tjr.REV5_JUDGED_SETTINGS`를 저장했다가 `finally`에서 복원한다. `edition_8()`은 `ed8_identity(), ed8_jp3_settings(), _tjr_judged_settings()`를 한 `with`로 묶는다.
   - `j_p3_inputs.py` 줄 39·67을 읽어, 기존 튜플에 판 8 이름이 없고 VBKL·VBKM 대칭이 맞음을 확인했다.
2. 보고서↔증거
   - `baseline_check sums`: mismatch 0, missing 0, unlisted 0, crlf 0. 보고서 5절의 sha 접두사 21개 전부 SUMS와 일치한다.
   - 작업 파일 3개의 sha256 전체가 보고서와 일치한다(`c01004b1…`, `14c10caf…`, `bfd37f3f…`).
   - 시험 수 재계산:
     - 새 시험 23개(통과 12, T8″ 코드 위 실패 11)
     - T-f 두 cwd 각각 23/23
     - 기준 재실행 9031 = 8885 / 12 / 0 / 134
   - `byte_check_T8ppp.json`을 재현했다. "하지 말 것" 13개 파일은 5955f25b blob과 줄바꿈 정규화 기준으로 같다. `j_p3_inputs.py`는 C8(56849248) blob과도 같다.
   - `t8ppp_diff_tracked.txt`는 실제 `git diff 5955f25b -- 04_scripts`와 줄바꿈 정규화 기준으로 동일하다. 원본 바이트는 CRLF 때문에 다르고 내용은 같다.
3. git 범위
   - `diff --name-only 5955f25b`는 의도한 2개이고, `status --porcelain`은 M 2 + ?? 1이다. `--ignored`에도 `__pycache__`가 없다.
   - 작업 파일은 CRLF, 인덱스는 LF라 autocrlf가 작동하고 있다. HEAD는 5955f25b다.
   - worktree lock은 아직 없다(커밋 뒤 메인이 건다).
4. 규칙 줄 인용: `jp3_remedy_spec_v8_rules.md`를 직접 읽었다.
   - 3.6:154-157 ✓(VBN·LSN 판정 / VBN0 T8·12a / `VBN<key>` 4판정+6기록 / VBKN·VBKN0 12b)
   - 5.1:218-221 ✓
   - 5.2:232-235 ✓("기록 6설정은 기록" 233)
   - 9:332 ✓("C-S 판정 4설정 184")
   - docstring 인용은 모두 일치한다.
5. 시험 코드: 스텁은 `rod_reading`과 `condition_judgement` 두 개뿐이다. `jp3_of`·`j_p3_*`는 스텁하지 않았다(명세 T-c 준수). `monkeypatch.setattr` 두 곳(`ED7_BUNDLE`·`ED7_BASE`)은 T-d 시험 설정이다.

## 검사하지 못한 것
- 시험·ruff는 실행하지 않았다(정적 점검·junit 재집계만).
- 블라인드 경로의 값은 보지 않았고, 값 없는 스모크도 하지 않았다(verif-protocol-auditor 몫).
- 경로 2 도구와 "판 8 이름이 빠진 이름 튜플 전수 검색"은 하지 않았다(지시상 범위 밖).
- `ed8-judge3`의 `04_scripts`·`03_src`에서 `ed8_jp3_settings`를 쓰는 파일이 2개뿐이라는 T-e의 주장은 보고서 신뢰로 두었다. 시험이 이를 단언한다.

## 사용자 조치 필요
없음.

## 실행한 검증
- 읽은 파일: 명세 `control_d1_settings.md`, `d1_settings.json`, 보고서 `impl_report_t8ppp.md`, 근거 폴더 `SHA256SUMS`와 `byte_check_T8ppp.json`, 규칙 `jp3_remedy_spec_v8_rules.md`(151-161, 215-238, 330-334행과 헤딩 grep)
- ed8-judge3 `jp3_ed8_judge.py`·`jp3_tjr_judge_ed8.py` diff 전문, `j_p3_inputs.py` 줄 grep, `run_v5.py` ED8_SETTINGS 발췌, 시험 파일 grep
- `baseline_check.py sums`(python-dev `-I -B`) 실행 → `cited_untracked` 22건 외 이상 없음.
- 자체 검증 스크립트 1개를 scratchpad에서 실행(junit 재집계, git blob·diff 대조, sha 계산). 실행 뒤 하위 폴더 `integrity-t8ppp`를 삭제했다.
- git 조회: `diff --name-only`, `status --porcelain --ignored`, `ls-files --eol`, `check-attr`, `check-ignore`, `worktree list`.
- 파일은 수정하지 않았다. 판정 직전에 `git status`를 다시 조회했고 변화는 없었다.
- 사용한 스킬: 없음
- source_guard는 이번 호출에서 쓰지 않았다. 대신 위 `status` 재조회로 worktree가 바뀌지 않았음을 확인했다. "원본 불변: 확인" 줄은 낼 수 없다.
- 공개 범위: Grep·Glob은 단일 파일 또는 `…\ed8-judge3\05_tests\unit\test_ed8_jp3_settings.py`처럼 파일을 직접 지정했다. 블라인드(`j9_runs\56849248\impl_*_a1`, `l1ref_a1`), `stage4_prejudge`, 경로 2 도구는 열지 않았다. 블라인드를 품은 상위 폴더도 범위로 쓰지 않았다.
- 의존성 점검은 따로 실행하지 않았다(`depcheck.ps1` 미실행). 필요한 python-dev 패키지는 모두 정상 동작했다.
