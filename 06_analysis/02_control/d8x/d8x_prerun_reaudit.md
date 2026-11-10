<!-- verif-protocol-auditor 리포트 원문(2026-11-10). 대상: D8x 하네스 실행 전 재감사, H_impl ba6671c. 메인 세션이 편집 없이 저장. -->

# D8x 하네스 실행 전 재감사 (verif-protocol-auditor, 2026-11-10)

## 결론
**차단 0, 남은 실행 전 수정 0, 기록 1. 지금 상태 그대로 실행해도 된다.** 앞 감사의 P-1·P-2·P-3·C-1·C-2는 모두 닫혔다. 대상은 HEAD `ba6671c4faaf7a26773dcfb9f554ce2491b466ed`, main checkout `C:\workspace\outrigger_control`이다.

## 닫힘 확인

| 항목 | 확인한 것 | 판단 |
|---|---|---|
| P-1 MKL 계층 | `d8x_steps_P.json`의 18단계 모두 `env.MKL_THREADING_LAYER = "TBB"`이고, `d8x_runner_P.ps1`에도 18곳 있다. 나머지 `*_NUM_THREADS=1`도 그대로다 | 닫힘 |
| C-2 g0 `-B` | g0-rev3 명령이 `... -I -B 04_scripts/01_dynamics/run_d8x_g0_rev3.py --workers 8`이다 | 닫힘 |
| P-2 HEAD 고정 | `check_head.py`는 HEAD가 지정 커밋(전체 sha)과 같고 `status --porcelain --untracked-files=no`가 비어야 0을, 아니면 1을 낸다. git이 실패하면 `check=True` 예외로 0이 아닌 값이 된다. `head-g0`, `head-ra-off`, `head-ra-on`, `head-rc-off`, `head-rc-on`이 각 실행 단계(g0-rev3, ra-off, ra-on, rc-off, rc-on) 바로 앞에 있다. 재시작 절차(`head-*`의 `.done`만 지우기, 첫 prelaunch 보존, 정체성 표 손 확인)는 `d8x_prerun_record.md:16`에 있다 | 닫힘 |
| P-3 P코어 전환 | `d8x_prerun_record.md:11-15`에 사용자 결정(14시경)과 이유, I-1 근거, rev7 없음, 마스크 0xFFFF·worker 8·Normal·같은 P 풀, 판정서 "규칙과 다른 실행" 절로 옮긴다는 내용이 있다. 단계의 prelaunch와 rc `--mask`도 모두 0xFFFF다 | 닫힘 |
| C-1 오류 행 표기 | `d8x_prerun_record.md:20`이 "경로 1 `not_judgeable` ↔ 경로 2 `fail` = 알려진 차이 → 판정 불가(B-ID)"로 결과 전에 고정했다 | 닫힘 |
| R-1·R-3·C-4 | 행 결합 키(`:19`), 실행 기록 봉인 위치(`:21`), 점 파일 해시 종류(`:22`)가 모두 적혀 있다 | 닫힘 |
| `--expect` 파일 | `d8x_expect_k1.json`: `Get-FileHash` 결과가 055E1A50…065EBD로 기록값과 같다. 내용은 rev3 3.3 JSON과 같다(ra off/on, rc VB/V0 off/on, chrono `final_C4G2_LAS_K1`). mtime 13:15:08이고, 결과보다 앞이다 | 맞음 |
| 시작 상태 | HEAD ba6671c, status 빈 상태다. `d8x/ra`, `d8x/rc`, `d8x_g0_rev3.json`은 없다. `d8x_prerun_record.md`·`d8x_prerun_audit.md`는 `-text`(check-attr `unset`)다 | 맞음 |

## 기록
- [기록][R] `d8x_prerun_audit.md`가 앞 감사 원문과 바이트 단위로 같은지는 이번에 대조하지 않았다. 판정서 커밋 전 감사에서 원문 대조를 한다.

## 실행한 검증
- 읽은 것: `check_head.py`, `d8x_prerun_record.md` 전체.
- 단계 파일 조회: python-dev `-I -B`로 각 단계의 id·env·명령 끝부분을 출력했다.
- 러너 Select-String: `MKL_THREADING_LAYER` 18곳.
- 시작 상태 확인: `git rev-parse HEAD`, `git status --porcelain --untracked-files=no`, `Get-FileHash`(expect 파일), `git check-attr text`, 출력 경로 `Test-Path`.
- 이번 재감사는 파일을 만들거나 지우지 않았다. source_guard는 짧은 재감사라 돌리지 않았다. 앞 감사의 판정 기준이 된 입력(규칙 7판, 경로 2, 코드)이 그대로인지는 HEAD와 status로만 확인했다.
- 사용한 스킬: 없음
