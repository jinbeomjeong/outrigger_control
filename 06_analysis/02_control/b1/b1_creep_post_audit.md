# B1 크리프 근거 판정 후 감사 (verif-protocol-auditor, 2026-11-13, 판정서 커밋 직전)

아래는 감사 리포트 원문 그대로다. 처리는 맨 끝에 덧붙인다.

---

## 감사 요약
- 대상: `V5-B1-CREEP`, B1 크리프 근거 판정서. 시점은 판정 후(판정서 커밋 직전)이고, 저장소 master `bd64cc4`, 추적 변경 0이다.
- 판정서: `C:\workspace\outrigger_control\06_analysis\02_control\b1\b1_creep_basis_judgement.md`, 현재 sha256 `d59be349…`.
- 기준 문서:
  - 원판 `b1_creep_rules.md` `6b99702c…`(봉인 커밋 `1ad3e5d` 09:26:21)
  - rev1 `b1_creep_rules_rev1.md` `9f72af5b…`(`417ce28` 12:00:41)
  - 두 판 모두 `.sha256` 첫 토큰과 원시 바이트 해시가 같다. LF 전용이고 BOM이 없으며 `-text`로 보호된다.
- 판정: 차단 0 / 실행 전 수정 1 / 기록 6.
- 결론: 판정서의 등급·수치는 두 출력 및 result.json과 맞는다. 아래 [실행 전 수정] 1건을 처리하면 커밋할 수 있다. 그 1건은 `.gitattributes` 줄을 하네스 jsonl을 `git add` 하기 **전에** 넣는 것이다.

## 발견 사항 (심각도순)

**[실행 전 수정][S] 하네스 출력 폴더 `06_analysis/03_hydraulic/coupled/v5/b1/`에 줄바꿈 보호가 없다.** 판정서는 이 폴더 파일의 원시 sha를 인용한다.
- 근거:
  - `git check-attr text` 결과 `b1_H.jsonl`·`b1_H.jsonl.identity.json`이 `unspecified`이고 `core.autocrlf=true`다.
  - 바이트를 세면 `b1_H.jsonl`은 CRLF 32/32줄이다. 원시 `a7099db6…`가 판정서 20행에 인용돼 있고, LF로 바꾸면 `ce4dec55…`가 된다. `.identity.json`은 CRLF 87줄, `run/*`도 CRLF다.
  - 판정서 387행·451행에 이미 미처리로 적혀 있다.
- 실패 시나리오: 이대로 add 하면 인덱스에는 LF로 들어간다. 그러면 LF checkout(다른 PC, `autocrlf=false`)에서 인용 sha `a7099db6`이 재현되지 않는다.
- 권장 조치(메인 세션):
  1. `.gitattributes`에 `06_analysis/03_hydraulic/coupled/v5/b1/** -text`를 넣는다.
  2. 같은 커밋으로 `.gitattributes`와 jsonl을 함께 add 한다.
  3. add 뒤 `git ls-files --eol`이 `i/crlf w/crlf attr/-text`인지, 다시 해시한 값이 `a7099db6`인지 확인한다.
- 참고: npz 32개는 `.gitignore:41 *.npz`로 빠진다. 다른 clone에서는 V-4(npz sha) 재검사가 불가능하다(아래 확인 필요 1).

**[기록][C] 판정서 255행의 속도 범위 하한이 틀렸다.**
- 근거: 판정서는 "판독 행정 속도 3.6~21.3 mm/s"라고 적었다. 경로 2 `rows.*.R1_4.stroke_speed_nL`의 최솟값은 C3 RL 0.0031047 m/s = **3.1 mm/s**다. 3.6은 C5만 본 최솟값이다.
- 영향: 등급 영향 없음. "6행 모두 > 0"은 맞다.
- 권장: 판정서 작성자(control-expert)가 "3.1~21.3"으로 고친다.

**[기록][T] 판정서 24행의 이름 정정 문장이 부록 추가를 빠뜨린다.**
- 근거: 원본 파일 `b1_creep_judgement.md`(5a959fb0)는 지금 없다. 작성자 transcript `agent-a9ec64fd60de5f719.jsonl`에서 원본을 재구성했다(Write + Edit 2건 + PowerShell `.Replace()` 5건). 재구성 sha256은 `5a959fb0c280d812…`로 인용값과 같다.
- 재구성본과 현재 파일의 차이는 24행 1줄과 475~481행 부록 7줄뿐이다.
- 24행은 "이 줄만 고쳐…(내용 변경 없음)"이라고 적었다. 부록에는 머리 "메인 세션 기록"이 붙어 있어 출처는 알 수 있다. 그래도 24행 문장은 사실과 다르다.
- 권장: 24행에 "그 뒤 끝에 부록(판정 뒤 사용자 결정)을 더함"을 덧붙인다.

**[기록][R·C] D-d의 SGS 행 $s_{\max}$를 두 경로가 같은 방식으로 읽었다. 그래서 K-R로는 잡히지 않는다.**
- 근거: 원판 3.3 D-d(`b1_creep_rules.md:289`)는 "SGS 행은 $s_{\max}$를 가드 도달 값으로 둔다(하한, 7.4)"이다. 두 경로는 기록된 판독 최대(C4 681.197, C5 681.297 mm)를 그대로 썼다.
- 판정서 197행은 0.6828 m 읽기도 함께 적었다. 그 읽기로 다시 계산했다.
  - D-d: C4 e(P-A) −25.787, C5 −16.761 mm, $E_{P-A}$ 25.787 > 10 → PRED-FAIL 그대로다. P-G는 C4 +22.823이다. q* = P-A/P-D 동점도 그대로다.
  - D-c: C4 원시 +0.372이고 보정 구간 [−4.938, +3.584]는 미확정이다. C5 원시 +2.351, 보정 +3.963(+)이다. C2·C3가 +이므로 H-OPT 그대로다.
  - D-e: C1·C2의 $\tilde g$ < 20이므로 B1-OPEN 그대로다.
- 결론: 등급 불변이다. 판정서 공개는 충분하다.
- 권장: D-d 재등록 개정판(제안 1 (나))에서 이 문장의 뜻을 결과 전에 정한다(확인 필요 2).

**[기록][I] 경로 2 출력에는 도구 sha·커밋이 없다.**
- 근거: `b1_metrics_path2.json` 최상위에는 `tool = "b1_path2"`, `version = "2.0-rev1"`만 있다. 경로 1은 `tool_sha256` `6b6e04ac…`를 출력 안에 남긴다.
- 출력 ↔ 도구(`7a9d258f`) 연결은 prelaunch 10.2 문장에만 기대고 있다. 다만 worktree `b1-path2-fix`가 HEAD `24a108e`이고 깨끗하며, 그 커밋 blob의 sha가 `7a9d258f…`다. 그래서 지금은 확인할 수 있다.
- prelaunch 10.2·10.3에 적힌 명령은 실제 실행 명령이 아니다. 경로 2는 바꾼 인자를 문장으로만 적었고, 경로 1은 `BATCH_STAMP` 틀 그대로다.
- 권장: 다음 판부터 경로 2가 자기 sha·인터프리터를 출력하게 한다(위임 필요). prelaunch 11절에 실제 명령줄을 붙인다.

**[기록][T] 판정서 357행의 시각이 커밋과 조금 다르다.**
- 근거: 357행은 "12:56에 … `1ac4849`"라고 적었다. 커밋 author/committer 시각은 `2026-11-12T12:55:15+09:00`이고, 파일 mtime은 12:54:10이다.
- 영향: 순서 결론(첫 결과 15:10:50 전)에는 영향 없음.

**[기록][R] 원판 11절의 결과물 이름과 실제 이름이 다르다. 판정서는 그 사실을 적지 않았다.**
- 근거: 원판 11절(`b1_creep_rules.md:582`)은 "`B1_prelaunch.json`(배치 폴더에 채움, 판정 뒤 `06_analysis/02_control/b1/prelaunch/`에 사본 커밋)"과 `b1_harness_constants.json`을 적었다.
- 실제는 다음과 같다.
  - prelaunch는 `b1_creep_prelaunch.md`(분석 폴더, 추적 밖)이고, 배치 폴더에는 `B1_identity.json`만 있다.
  - 상수는 `b1_harness_constants_rev1.json`이다. 옛 `b1_harness_constants.json`(`0dd09ad0`)은 보관용이다(prelaunch 77행).
- 판정서 454행은 "`B1_prelaunch` 사본을 커밋할지"만 적었다.
- 권장: 판정서 6절에 "형식 차이: prelaunch는 md, 정체성은 `B1_identity.json`"을 한 줄 더한다.

## 재집계 표
판정서의 수치 토큰을 모두 두 출력의 값과 대조했다. 맞지 않은 토큰 35개는 차·합 산술, 절 번호, result.json·K-R 결과의 값이었고 아래에서 하나씩 확인했다. 주요 값은 키 이름으로 따로 읽었다.

| 항목 | 판정서 값 | 재집계 값(출처) | 차이 | 판단 |
|---|---|---|---|---|
| 2.1 b·b*, n_L1/n_L/취소, n_R, n_max, SGS, s(t_L), s_max, g (6행) | 표 그대로 | 경로 2 `rows.*.m` | 0 | 일치 |
| D-a $Z_{ch}$ / $Z^{corr}$ / $Z_{hn}$ | 13.337 / 11.481 / 7.168 | 13.3370 / 11.4810 / 7.1682 | 0 | 일치 |
| D-a 행별 원시·r_σ·하네스 VB/V0·z(t_max)−z(t_L) | 표 2.2 | `m.dz_post`·`gm.e/L.r_sigma`·`M10`·`dz_L_max` | 0 | 일치 |
| T-1 여유 | +3.169 / +1.313 | 13.337−7.168−3, 11.481−7.168−3 | 0 | 일치 |
| D-b δos C1~C3, 하네스 C2/C3, C1 하네스 n_sgs | 19.901/21.383/23.197, 2.366/4.064, 407 | `m.dos`, 경로 1 `harness.H-P|C*|VB|e0.M-5` | 0 | 일치 |
| D-c 원시·δgrid·보정 구간·δz1n·분류·산포 | 표 2.4 | `grades.D-c.detail`, `gm.max` | 0 | 일치 |
| D-d e(5후보×6행), E_q, q* | 표 2.5 | `pred.e`, `grades.D-d.E` | 0 | 일치 |
| M-12 max\|d\| | C5 0.048, C6 0.030, 나머지 0, 하네스 38 LOC ① | 경로 1 `m12` | 0 | 일치 |
| D-e g / g_corr / g̃ / 위상 범위 | 표 2.6 | `grades.D-e`, 경로 1 `g_corr_band_m` | 0 | 일치 |
| C5 RL δgrid / f, C6 FR δgrid / f | −1.612 / 0.98736, −1.125 / 0.99069 | `gm.max` | 0 | 일치 |
| C-5 (다) C5, C6 / 참고 z_max·df | +0.011, +1.105 / +0.420, −0.762 | 경로 1 `grid.*_df_*` | 0 | 일치 |
| 2.10 κ·C·δ_allow·κ 비·적합 다리 | 표 | `constants`(2,000 N 감도 NA 포함) | 0 | 일치 |
| 2.11 합 비·Ŵ | 표 | `R1_4` | 0 | 일치 |
| 2.11 속도 범위 | 3.6~21.3 | **3.1**~21.3 (C3 RL) | −0.5 | 기록(위) |
| P-1·P-2·P-14·P-15 값 | 판정서 3.1 | `dz_post` 뒷다리, `dz_R_end`, `n_creep`, `dz_max_R`, `gm` f 차 | 0 | 일치 |
| P-6 시각 | 50.2 / 38.7, LOC 46.4 / 34.7 | n_sgs 502 / 387, n_L 464 / 347 | 0 | 일치 |
| P-7 order_gate | C4 2, 나머지 0 | 경로 1 `order_gate_decisions` | 0 | 일치 |
| 4.1 K-R 단위·항목 수 | 2,751 / 2,629 / 120 / 1 / 1, 항목 102 / 1 / 1 / 4 / 1 | `b1_kr_result.json` `summary` | 0 | 일치 |
| C3 가드 초과 | FL 683.475, n 610, probe 59.7 → level 69.8, WARN·FAULT 없음 | result.json `phases`·`events` | 0 | 일치 |
| 0.6828 m 읽기 결과 | D-c·D-d·D-e 같음 | 직접 계산(위 발견 4) | 0 | 일치 |
| C3 벽시계·µs/스텝·n_steps·READY·재레벨 | 6,649 s, 3,955, 1,680,000, 116.2 / 118.8 / 149.0 | batch.json `wall_s`, result `wall_s`/`n_steps`, phases | 0 | 일치 |
| C3 동시 실행 2행 | 15:19:53 이후 | progress.log | — | 일치([추정] 원인 문장은 판정서 그대로) |
| C6 I-11 | W_ref/YAML = 9.80665, 플랜트 ×1.1 | result `mass_scale` | 0 | 일치 |

## I축 (실행 정체성) 결과
result.json과 batch.json에서 직접 확인했다.
- 6/6 행 공통으로 다음이 확인됐다.
  - 태그 `final_C4G2_P3_LAS_K1`, `expect_controller.ok` 참, 모든 checks 참
  - `num_threads_chrono` 4, `placement` pcore·PASSIVE, `affinity_ok`, `power_throttling_off_ok`
  - batch `pool` = `planned_pool` = pcore, `start_env OMP_WAIT_POLICY=PASSIVE`
  - hull requested = effective = fast, 출처 default, `fallback_reason` null, `mixed_hull_mode` False
  - DLL sha = 파일 `cec997d7…`
  - `meta.pad_variant.pad_variants_params_file_sha256` = YAML `ef2880f9…`
  - `code_at_launch.git` head `bd64cc4`, clean, dirty []
- argv(level부터)의 sha를 독립 재계산했다. 6/6이 af7d176e / 80c074e4 / 1dfd69db / 4f3506e1 / 8e0c4c8f / c6f2ee1b로 기대값과 같다.
- `B1_identity.json` `2a4a4662`은 6행 ok, `runner_log` 0/0이다.
- `log_errors.py`는 종료 0이다(7로그, `errors N` 줄 없음). `.log` 안에 Traceback·Error 0행이다.
- 도구 sha와 실행 sha
  - 경로 1: worktree `agent-a54833748c3f6b37d`의 HEAD `1ac4849`이고 깨끗하다. 파일 sha와 커밋 blob sha가 모두 `6b6e04ac…`이고, 출력 안 `tool_sha256`도 같다.
  - 경로 2: worktree `b1-path2-fix`의 HEAD `24a108e`이고 깨끗하다. 파일 sha와 blob sha가 모두 `7a9d258f…`다.
  - 두 커밋 모두 rev1 `417ce28`을 포함하고, 첫 result(15:10:50)보다 앞선다(12:55:15 / 13:00:54).
- 판정서 5절 표의 sha 인용은 모두 실제 파일과 같다. 다만 03_src·04_scripts 코드 파일(c2.py 등)의 인용은 `autocrlf` 작업 트리의 CRLF 원시 해시다(i/lf w/crlf). batch.json `code_at_launch`와 같은 관례라 결함으로 세지 않았다.

## S·T축 결과
- `seal_check.py` 결과: 규칙 2판 모두 raw 일치, `-text` 보호, CRLF 0, BOM 없음이다. 인용 해시 60개 가운데 25개가 풀리지 않았는데, 모두 직접 해시해 확인했다.
  - `.sha256` 파일: a269959a / 07026005
  - YAML: ef2880f9
  - DLL: cec997d7
  - `P7_REF`: 70e91ec1
  - 코드 9개: 5a243a1a, 198cf3bb, 565b2317, 9344e00f, f58ee42b, 9a0575aa, 34b21a78, afef13ec, 2acb3755
  - 배치표 3d3b0117: prelaunch 28행 인용(scratchpad 파일, 지금은 확인 불가)
  - argv 6개: 위 재계산과 일치
  - 5a959fb0: transcript 재구성으로 일치
  - 나머지: worktree·agent ID(해시 아님)
- `timeline.py` 결과:
  - 원판은 모든 결과보다 앞선다.
  - rev1은 하네스(11:30:16) 뒤에 썼고, 이를 rev1 0절이 밝힌다(`rev_after_results_declared`).
  - rev1·상수 커밋(12:08:03, git)·대응표(13:10:31)·결정(13:59:33)은 모두 첫 Chrono 결과보다 앞선다.
  - 경로 2 출력(17:27:24)이 경로 1 실행 시작(17:27:38)보다 앞선다. 근거는 mtime이라 [추정]이다.

## "판정서에 적을 것" 대조 (`judgement_checklist.py`)
- 결과: 항목 67, found 15, missing 0, ambiguous 52(작성자 보고와 같다), 종료 0.
- ambiguous 52개 가운데 51개는 규칙 자신의 공개 문장(0.2.1·0.3·0.4·7.1·rev1 0·R1-3·7절)이라 판정서 항목이 아니다.
- D048(2.3 G-S 시각·명령·출력 범위)은 판정서 1.6에 있다.
- 원판을 grep 해 직접 대조한 항목: 3.2 행 목록·행 수, 3.3 D-a·D-c·D-d·D-e·D-g, 안전 기록, 3.4 D-d·D-f·D-g, I-6, I-12, 4.3 `rerun_of`, 7.4 "하한 포함"(조건 PRED-q 불성립), 7.5 D-d 표 옆 $E_{P-A*}$·max|d|, 10.1 판정 후, 11절 목록. 모두 판정서 3절 표대로 있다.

## 공개 항목 점검
판정서에 다음이 모두 있다.
- K-R 제외 X-01~X-04·U-01~U-12·K-93: 4.2
- K-77·K-107: 4.3
- 정의 차이 9건: 4.4
- worktree 실행과 판정 뒤 병합: 4.6·5
- 경로 2 상수 파일 이름 변경: 4.6. 두 파일 `3b5e775b`는 내가 다시 해시해 같다.
- G-S 폴더 유지와 순서 편차: 1.6·4.6. 폴더 `07_results/S9/batch_V5-B1-CREEP-GS_20261112_112555`는 22파일 8.5 MB이고 progress.log 시각 11:25:55~11:34:08, wall 492 / 488 s다.
- 실행 중 도구 수정 시각: 4.6. 분 단위 차이는 위 기록.
- 독립성: 4.7
- 판정서 이름 정정: 24행. 부록 누락은 위 기록.

## 커밋 전 할 일 (권고)
1. **`.gitattributes`**: `06_analysis/03_hydraulic/coupled/v5/b1/** -text`가 필요하다(위 [실행 전 수정]). `06_analysis/02_control/b1/** -text`는 이미 있다. 판정서·K-R·출력·prelaunch는 `text: unset`으로 보호된다.
2. **두 수정 브랜치 병합과 sha 보존**
   - 두 브랜치는 모두 `bd64cc4`에서 갈라졌고, 바뀐 파일이 겹치지 않는다.
     - `1ac4849`: `b1_creep_metrics.py`, `test_b1_creep_metrics.py`
     - `24a108e`: `path2/b1_path2.py`, `b1_path2_selftest.py`, `README.md`
   - 그래서 충돌이 없고, `-text`·LF 그대로라 병합 뒤 sha가 보존된다.
   - squash·rebase 하지 말고 merge 한다. 판정서가 `1ac4849`·`24a108e`를 인용하므로 두 커밋이 계속 도달 가능해야 한다.
   - 병합 뒤 master `b1_creep_metrics.py` = `6b6e04ac…`, `path2/b1_path2.py` = `7a9d258f…`인지 다시 해시한다.
   - 판정서 360행의 "이 판정서를 쓸 때 master HEAD는 `bd64cc4`"는 시점을 적은 문장이므로 병합 뒤에도 사실이다.
3. **커밋할 것**(경로를 지정해 add 한다. 다른 미추적 묶음 `las_redesign/`·`v5_rerun/`·`s9/rev86/` 등은 섞지 않는다)
   - `06_analysis/02_control/b1/`: 판정서, `b1_creep_prelaunch.md`, `b1_creep_prerun_audit.md`, `b1_creep_fix_reaudit.md`, `b1_kr_audit.md`, `b1_kr_map.md`, `b1_kr_map_decisions.md`, `b1_kr_result.md`·`.json`, `b1_metrics_path1.json`·`path2.json`, `b1_constants_path2_rev1_run.json`, 옛 `b1_harness_constants.json`(rev1 0절 "본 것"의 근거, 보관)
   - 원판 11절의 prelaunch 사본: `prelaunch/`에 `B1_identity.json`(바이트 복사, sha `2a4a4662` 유지)과 `batch.json`·`progress.log` 사본. `07_results/`는 `.gitignore:39`로 빠지므로, 사본이 없으면 인용 sha `2a4a4662`를 다른 clone에서 확인할 수 없다.
   - `06_analysis/03_hydraulic/coupled/v5/b1/`: `b1_H.jsonl`, `b1_H.jsonl.identity.json`, `run/*`(1의 `-text`를 넣은 뒤)
4. **추적 밖으로 둘 것**
   - G-S 폴더와 Chrono 배치 폴더 전체(07_results 관례)
   - 하네스 npz(`*.npz`. 넣을지는 확인 필요 1)
   - `b1_c3_probe_guard_check.md`: 감사 중 00:19:16에 다른 세션이 새로 만든 파일이다. 이 감사에서 보지 않았으므로 판정서 커밋과 분리하기를 권한다.

## 확인 필요
1. 하네스 npz 32개(약 3.9 MB)를 강제 추가할지 여부. 넣지 않으면 V-4의 "npz sha = 줄 기록" 재검사는 이 PC에서만 된다.
2. D-d "가드 도달 값" 문장의 뜻(기록된 판독 최대 대 0.6828 m). 이번 등급은 불변이다. 재등록 개정판(부록의 B1 진행)에서 결과 전에 문장으로 정할 것(control-expert 초안).

## 위임 필요
- python-expert(경로 2 소유는 control-expert이므로 경로 2 작성자에게): 다음 판에서 경로 2 출력에 `tool_sha256`·`git_head`·인터프리터 버전을 넣는다(`06_analysis/02_control/b1/path2/b1_path2.py` 출력 dict 최상위). 경로 1의 `tool_sha256` 꼴과 맞춘다.
- control-expert(판정서 작성자): 판정서 255행 "3.6~21.3" → "3.1~21.3", 24행에 부록 추가 사실, 357행 "12:56" → "12:55", 6절에 원판 11절 결과물 형식 차이 한 줄. 판정서 sha가 바뀌므로 고친 뒤 sha를 다시 적는다.

## 메인 세션 권고
- `.gitattributes` 줄 추가 → 두 브랜치 merge → sha 다시 해시 → 경로 지정 add → integrity-checker → 커밋 순서로 진행한다.
- 커밋 뒤 `git ls-files --eol -- 06_analysis/03_hydraulic/coupled/v5/b1/b1_H.jsonl`이 `i/crlf … attr/-text`인지 확인한다.

## 검사하지 못한 것
- 배치표 `schedule_main.json`(3d3b0117): scratchpad 파일이라 재해시하지 않았다.
- 러너 status.txt의 I-1·I-10 시작·끝 HEAD: 파일을 찾지 않았다. `batch.json code_at_launch` 6/6 clean·`bd64cc4`로 대신 확인했다.
- 경로 2 독립성 transcript 재검색: 실행 전 감사 결과를 인용했다.
- K-R 항목별 재대조: 이미 감사한 `b1_kr_audit.md`에 기댔다. 이번에는 판정서 ↔ 출력만 봤다.
- `gate_scan`: 실행 전 감사에서 했고, 이번에는 다시 돌리지 않았다.
- `b1_c3_probe_guard_check.md`: 내용을 읽지 않았다.

## 실행한 검증
- 인터프리터는 python-dev `-I -B`(+`-X utf8`), `MKL_THREADING_LAYER=TBB`이고, 실행은 PowerShell 도구로 했다. git 조회는 Bash 도구로 했다. 대상 프로젝트 모듈과 판정 도구는 import하지 않았다.
- 실행한 도구
  - `tools/verif/seal_check.py --repo … --quoted 판정서 --hash-files …`: 종료 1, `quoted_unresolved` 25는 모두 직접 해소
  - `judgement_checklist.py`: 종료 0
  - `timeline.py`: 종료 0
  - `log_errors.py <배치 폴더>`: 종료 0
  - `placeholder_scan.py 판정서 prelaunch`: 종료 0
- 즉석 스크립트(scratchpad `verif\`)
  - `keys.py`, `numcheck.py`(판정서 숫자 ↔ 출력 잎 값), `tables.py`·`p1.py`·`p1b.py`(키 이름별 재집계)
  - `res.py`·`ident.py`(result.json·batch.json 정체성, argv sha 재계산)
  - `tx*.py`(transcript에서 원래 판정서 재구성)
  - 모두 지웠다(폴더 삭제 확인). 대상 폴더에 `__pycache__` 없음.
- `tools/verif` 후보(python-expert)
  - `judgement_numbers`: 입력은 판정서 md + 출력 json들. 수치 토큰을 출력 잎 값에 대조하되, 표 행 ↔ 키 경로 매핑을 받아 키 단위로 대조한다. 발견이 있으면 종료 1.
  - `doc_reconstruct`: 입력은 transcript jsonl + 대상 파일 이름. Write·Edit·PowerShell Replace를 재생해 sha를 내고 현재 파일과 diff 한다.
- 원본 불변: 위반 — 입력 폴더에 항목 추가 1건(b1_c3_probe_guard_check.md)
  - 원인: 다른 세션이 00:19:16에 만든 파일이다(크기 11,888 B). 이 감사는 프로젝트에 아무것도 쓰지 않았다.
  - 입력 30파일의 내용 변경은 0건이다. 이 밖에 `.git` 폴더 mtime 변경 1건이 있는데, 원인은 git 조회 명령이나 다른 세션으로 [추정]한다.
  - 판정 근거 줄(24·197·255·357행)은 다시 읽었다. 판정서 sha는 `d59be349`로 감사 시작 때와 같다.
- 메모리 갱신: `C:\Users\jinbeom\.claude\agent-memory\verif-protocol-auditor\audit_pitfalls.md`에 판정 후 감사 함정 1항목, `MEMORY.md` 색인 한 줄 보강.
- 사용한 스킬: 없음

---

## 메인 세션 처리 (2026-11-13)

- 기록 4건(속도 범위 3.1, 시각 12:55, 이름 정정 줄, 6절 형식 차이)을 판정서에 메인 세션이 고쳤다(수치는 감사 재집계 값 그대로, 등급 불변). 판정서 sha 2bd1d8f9389d5c56a078cab5a49f4aebe96015976e7c25a5e5c95f5feab2e88e.
- 하네스 npz: 사용자 결정 '넣지 않음, 공개' — 판정서 6절에 적음.
- .gitattributes에 06_analysis/03_hydraulic/coupled/v5/b1/** -text 추가 뒤 add. prelaunch 사본 06_analysis/02_control/b1/prelaunch/(B1_identity.json·batch.json·progress.log).
- b1_c3_probe_guard_check.md는 이 커밋에서 뺀다(별도 작업).
