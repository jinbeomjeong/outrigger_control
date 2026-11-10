# D8x 하네스 실행 전 기록 (2026-11-10, 메인 세션)

결과 전에 쓴다. 실행 중 master 커밋 금지이므로 이 파일은 실행 뒤 판정서와 함께 커밋한다(그때까지 미추적).

## 1. 실행 정체성
- $H_{impl}$ = master `ba6671c4faaf7a26773dcfb9f554ce2491b466ed`(메인 세션 지정, rev4 3·rev5 4). 실행 위치 main checkout `C:\workspace\outrigger_control`. 시작 전 `git status --porcelain --untracked-files=no` 빈 상태.
- 규칙 7판: 원판 a377b9bb, rev1 ad16f452, rev2 5f3fa620, rev3 2318fb5c, rev4 5233c517, rev5 63437019, rev6 d584c8da(모두 `.sha256` raw 일치, `-text`).
- 경로 2: `.local_archive/session_9d4aec18_20261110/d8x_path2/d8x_recount.py` 46010967…(결과 전 고정, 고치지 않음).
- 경로 2 `--expect` 파일: `06_analysis/02_control/d8x/d8x_expect_k1.json`, sha256 `055e1a50e485d9589c4b39e51ae939b59325b7e595e5d15421b3d2b3eb065ebd`(`d8x_judge.py expect-file`, 결과 전 작성).

## 2. 규칙과 다른 실행 (실행 전 감사 P-3)
- 원판 3절 표·Q5는 하네스를 "E코어"로 적었다. **사용자 결정(2026-11-10 14시경)으로 하네스 묶음 전체를 P코어에서 돌린다.** 이유: P코어가 비어 있고(배경 9~19 %), E코어는 상주 프로세스가 약 31 %를 썼다. 원판 I-1은 "P코어 묶음은 배치표 값"을 허용하고, 하네스는 단일 스레드 결정론 계산이라 풀이 판정 값에 들어가지 않는다. 사용자 결정(개정 종료 기준)에 따라 rev7 없이 이 기록과 판정서 "규칙과 다른 실행" 절로 처리한다.
- 배치: affinity 마스크 `0xFFFF`(P 16논리), worker 8(끝까지 유지, 사용자 결정), 우선순위 Normal, 완전 순차. G0·R-a off/on·R-c off/on 모두 같은 P 풀·같은 worker 수. 공통 env `MKL_THREADING_LAYER=TBB`(감사 P-1), `MKL/OMP/NUMBA/OPENBLAS_NUM_THREADS=1`. 시작 조건 `wait_until P<30 %` 3회 연속.
- 러너: scratchpad `csx\d8x_runner_P.ps1`(생성기 `make_d8x_runner_P.ps1`, 단계 `d8x_steps_P.json`), 예약 `d8x-harness` TTL 480분, `--job-kill-on-close`, `--stop-on-fail`, `--skip-done`. 실행 뒤 러너 로그 `d8x_logs_P`를 `.local_archive`로 보존한다(감사 C-5).
- 단계: chk-g0, head-g0, g0-rev3, g0-judge(`--at-commit ba6671c`), chk-ra, ra-off-pre, head-ra-off, ra-off(910), ra-on-pre, head-ra-on, ra-on(192), chk-rc, rc-off-pre, head-rc-off, rc-off(192), rc-on-pre, head-rc-on, rc-on(96). `head-*`는 HEAD = $H_{impl}$·clean이 아니면 exit 1(감사 P-2).
- 재시작 절차(감사 P-2): `head-*`의 `.done`만 지우고 `chk-*`의 `.done`은 남긴다. 첫 prelaunch 기록은 다른 이름으로 보존한다. 판정서에 정체성 표(G0 `meta.run_commit`·`clean`, R-a `meta.d8x.identity_start/end.git`·`meta.git_head`, R-c sidecar 모든 start/end, prelaunch 4개 `head`)를 손으로 적고 모두 ba6671c·clean인지 본다.

## 3. 두 경로 대조 절차 (rev6 점검 R-1·R-3, 실행 전 감사 C-1)
- 행 결합 키: R-a = `id` + `k1`(팔). R-c = (`slope_name`, `level`, `crawler_k_scale`, `setting`, `eps`) + `k1`(경로 1 `RC_JOIN_FIELDS`, 경로 2 `key_tuple`). 끔 팔 행별 대조에도 같은 규칙.
- verdict 표기 대응: 경로 1 `not_judgeable` ↔ 경로 2 `unjudgeable`. **드라이버 오류 행은 경로 1 `not_judgeable` ↔ 경로 2 `fail`("E-2 driver error")로 표기가 다른 알려진 차이**이며, 생기면 rev5 3.1-1에 따라 등급은 판정 불가(B-ID, 재실행)다.
- 실행 기록 봉인 위치(rev6 4): R-a `meta.d8x.rules_seals`, R-c `<out>.identity.json`의 start/end 항목 `rules_seals`, G0 `meta.rules_seals`, prelaunch 기록 `rules`. 원판 G-S의 "실행 전 미충족 = 실행하지 않음"과 rev6 4의 "실행 뒤 발견 = 판정 불가"는 모순이 아니다.
- `d8x_points.json`은 인덱스부터 CRLF(`-text`)다. R-a meta `points_sha256`는 LF 정규화 해시라 raw sha와 다르다. 판정서에서 sha를 인용할 때 어느 해시인지 밝힌다(감사 C-4).

## 4. 결과 전에 본 것
- 공개 탐침(판정 미사용): `.local_archive/session_6f3ebc4d_20261110/d8x_probes/`(SHA256SUMS.txt, SHA256SUMS_add.txt; rev5·rev6 공개 절).
- 실행 전 감사 원문: `d8x_prerun_audit.md`(같은 폴더). 정식 R-a·R-c·Chrono·G0 rev3 결과 0건.

## 5. 다음 (사용자 결정)
- 하네스 G1 통과·W 선정 뒤 L1-R 스냅숏 → Chrono 19행(P코어, 실행 전 감사 별도). 판정·감사·커밋까지 자동, 미달이면 분석까지만.
- D8x 등급 `통과`면 CLAUDE.md·dynamics_model·명세 검증 범위(마름모 roll 5.7 / 앞내림 3.7 / 앞들림 3.6)를 자동 반영, 이어서 P5r4+K1 봉인·구현·실행 전 감사까지 자동(본 실행 시작만 질문).
