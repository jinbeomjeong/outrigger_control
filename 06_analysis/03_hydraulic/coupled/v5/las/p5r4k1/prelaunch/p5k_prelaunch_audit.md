# P5r4+K1 실행 전 감사 1 (verif-protocol-auditor, 2026-11-11, HEAD 4b36cf5)

아래는 감사 리포트 원문 그대로다. 결정·조치는 맨 끝 '메인 세션 처리' 절에 덧붙인다.

---

차단 0 / 실행 전 수정 6 / 기록 8 / 확인 필요 4. 이대로는 시작할 수 없습니다. 실행 전 수정 1·2·3번은 지금 상태로 띄우면 하네스와 Chrono가 시작 단계에서 종료 2 또는 stop으로 멈춥니다. 틀린 통과가 나오는 경로는 찾지 못했습니다. 5번(Chrono 풀)과 6번(R-1/R-2 경계 허용)은 등급에 영향이 있으니 결정을 먼저 받아야 합니다.

## 감사 요약
- **대상**: LAS-b P5r4+K1 재판정. G-S(하네스 117줄, Chrono 12행)와 본 실행(하네스 6묶음 최대 1,474줄, Chrono 12행).
- **시점**: 실행 전. master HEAD `4b36cf5`, main checkout, 결과 0건.
  - `p5r4k1/`에는 `prelaunch/`만 있습니다.
  - `07_results/S9`에 `*P5R4*` 폴더가 없습니다.
- **기준 문서**: 원판 `las_p5r4_k1_rules.md`(5ee2bac0), rev1(f39846d6), rev2(e0a7d1e5), 이어받는 규칙 10개.
  - 13개 모두 LF·BOM 없음입니다. `.sha256` 첫 토큰과 같고, 두 경로 도구의 상수와도 같습니다(seal_check, 고정 58곳).
  - 봉인 커밋 `d6c65b5` 09:29:34, `9bcbcaa` 10:40:20, `1b03bbb` 11:04:55.
- **K-0 기준값** (main checkout은 `verif_matrix/scripts/* -text`라 작업 트리가 LF이고, raw = LF입니다)
  - `las_p5r4k1_judge.py` `4c07bfef331078fc329bd065e4a78bb73dec1c9bd8e6b8ce1bd1561ce3f1ee3a`
  - `las_p5r4k1_chrono_judge.py` `2b7dcb7b54ed8b8c27fc0ebbeab3aadd47e2f11341fa3d92be1fd3844c1371c4`
  - `las_p5r4k1_gs.py` `34ce26f846cecb30c4a1230d2e4680dcbe6066af4c0d8b0da7534b81e1e4c250`
  - 경로 2 `p5k_recount.py` fac91918…, `p5k_chrono_recount.py` 56f424a4…, `test_p5k_recount.py` dd5964a0…(LF, `-text`, blob이 prelaunch 기록과 같음)
  - 하네스 실행 도구 `las_p5r4k1_targeted.py`는 `-text` 밖이라 작업 트리가 CRLF입니다. raw `16f35625…`, LF `6997bf5e…`, blob `187dd34e…`.

## 발견 사항 (심각도순)

**[실행 전 수정][S·I] 1. 판정 도구 기대 sha가 CRLF 값으로 적혀 있습니다. main checkout에서는 판정이 바로 멈춥니다. (등급 영향 없음, 크게 멈춤)**
- 근거
  - `prelaunch/commands.md:106`은 `--expect-judge-sha f4ef93d5…`, `:128`은 `--expect-tool-sha 8d869e53…`입니다.
  - 그런데 `git ls-files --eol`은 두 도구를 `i/lf w/lf attr/-text`로 보이고, 작업 트리 CRLF 수는 0입니다.
  - 하네스 판정 도구는 `las_p5r4k1_judge.py:2104-2106`에서 raw·LF 어느 쪽과도 다르면 InputError를 냅니다. Chrono 판정 도구는 `las_p5r4k1_chrono_judge.py:905-909`에서 K-0 거짓이 됩니다.
- 권장 조치: 두 값을 위 K-0 기준값 `4c07bfef…`, `2b7dcb7b…`로 바꿉니다(메인 세션, commands.md). `commands.md:110`·`:132`의 설명도 함께 고칩니다.
- 참고: `--expect-judge-sha`를 빼면 하네스 K-0이 아무 말 없이 건너뜁니다(`:2090`의 기본값 None). 반드시 줍니다.

**[실행 전 수정][I·T] 2. 자리표시를 추적 중인 prelaunch 파일에 채우게 되어 있습니다. 채우는 순간 작업 트리가 dirty가 되고, 정체성 관문이 시작을 거부합니다. (등급 영향 없음, 크게 멈춤)**
- 근거
  - `prelaunch/*`는 git이 추적하는 파일입니다(커밋 `63cf816`, `ls-files` `i/lf w/crlf`).
  - 하네스는 `las_p5r4k1_judge.py:261-265`의 `ALLOWED_DIRTY`(시험 파일 3개)와 `:1250`(K-1 dirty)로 막습니다. 실행 도구 `prepare`는 `las_p5r4k1_targeted.py:792-795`에서 종료 2로 끝납니다.
  - Chrono는 `chrono_judge.py:415-425`가 `--untracked-files=no` 상태를 허용 목록(`commands.md`에는 `--allow-dirty`가 없어 빈 목록)과 대조합니다. prelaunch·postrun이 stop이 됩니다.
  - 원판 11.6은 prelaunch부터 postrun까지 커밋을 금지합니다. 그래서 `{RUN_HEAD}`는 그 HEAD를 담은 커밋 안에 채울 수 없습니다(순환).
  - `{BATCH_GS}`를 G-S 직후 manifest·commands에 채우면 본 하네스 Z-0과 Chrono prelaunch가 거부됩니다.
- 현재 상태
  - placeholder_scan 결과 미채움 22건: `{RUN_HEAD}` 3, `{BATCH_GS}` 6, `{BATCH_CHRONO}` 9, `{POSTRUN_HEAD}` 2, `{JUDGE_COMMIT}` 2. `commands_path2.md`에 3건이 있습니다.
  - 16.4는 `{RUN_HEAD}`를 "실행 전 감사 전"에 채우게 정하는데, 지금 채워져 있지 않습니다.
- 권장 조치(메인 세션, prelaunch 전에 한 번만 커밋)
  - `prelaunch/`를 git 추적에서 빼고 내용은 그대로 둡니다(`git rm --cached`, 그리고 `.git/info/exclude`). 그 뒤 채우기는 추적 밖에서 합니다.
  - 또는 채운 값을 추적 밖 sidecar 파일에 두는 방식을 확인 필요 1로 정합니다.
  - 채운 뒤에는 `commands_path2.md`의 raw sha(manifest `path2_commands`)도 바뀝니다. 판정서에 원래 값과 채운 뒤 값을 함께 적습니다.

**[실행 전 수정][I] 3. 추적 파일 `06_analysis/02_control/k2/judgement/k2_dyn_sensitivity.md`가 수정된 상태입니다. (등급 영향 없음, 크게 멈춤)**
- 근거: `git status --untracked-files=no`가 ` M …k2_dyn_sensitivity.md`를 보입니다. 2번과 같은 관문에서 하네스는 종료 2, Chrono prelaunch는 stop이 됩니다.
- 권장 조치: prelaunch 전에 커밋하거나 되돌립니다(메인 세션). 그 뒤 HEAD가 바뀌므로 실행 HEAD를 다시 적습니다.

**[실행 전 수정][S] 4. prelaunch 기록과 새 결과 폴더 일부가 줄바꿈 보호 밖에 있습니다. manifest의 sha가 main checkout 파일과 맞지 않습니다. (등급 영향 없음)**
- 보호 상태
  - `git check-attr text`: `prelaunch/*.json`·`*.md`, `p5r4k1/gs/*.jsonl`, `p5k_prelaunch_audit.md`(K-0이 해시하는 감사 원문), `p5k_chrono_prelaunch.json`, `verif_matrix/p5k_judge/`는 모두 `unspecified`입니다. `core.autocrlf=true`입니다.
  - `.gitattributes:33`은 `p5r4k1/*.jsonl`만 덮습니다.
- manifest sha 불일치
  - `manifest.json`의 `schedules.sched_gs.json` `8450a862…`, `sched_main.json` `7e499ba8…`, `path2_commands` `e61fa81d…`는 LF 내용의 sha입니다. main checkout 파일(CRLF)의 raw sha는 각각 `fbefc73a…`, `7e82ec75…`, `4becce15…`입니다.
  - 반면 `chrono_batch_plan` `2d1363c1…`는 CRLF raw입니다. 한 manifest 안에서 규약이 섞여 있습니다.
- 규칙과 다른 점: 원판 4.1은 출력 폴더를 "git exclude"로 정했지만 `.git/info/exclude`에 `p5r4k1` 항목이 없습니다.
- 권장 조치: 2번과 같은 커밋에 `-text` 줄을 넣습니다(`v5/las/p5r4k1/prelaunch/**`, `v5/las/p5r4k1/**/*.json*`, `verif_matrix/p5k_judge/**`). exclude 항목을 더합니다. manifest에 "sha 규약(LF/raw)"을 적습니다(메인 세션).

**[실행 전 수정][I·R] 5. Chrono 배치표가 원판 4.3 "계획 풀 P"와 다르고, 두 경로가 계획 풀을 다른 곳에서 읽습니다. 지금 계획이면 경로 2가 E 행 4개에서 K-6 stop을 냅니다. (등급 영향 있음: Chrono가 구조적으로 stop·K-10 불일치)**
- 규칙: 원판 `las_p5r4_k1_rules.md:152`는 "계획 풀 P(짝은 같은 풀 종류)"입니다. 12.2(`:444`)에는 "P 4 + E 3"이 비용 가정으로만 나옵니다.
- 계획 파일
  - `sched_main.json:1`의 `e_cases`는 A5·A6·C3·C4입니다. `chrono_batch_plan.json`도 이 네 행을 `ecore`로 둡니다.
  - 그런데 `chrono_rows_main.json`(행 모듈)의 `planned_pool`은 12행 모두 `pcore`입니다. s9_batch는 이 값을 batch.json `planned_pool`에 그대로 씁니다(`s9_batch.py:920-921`, 1683).
- 두 경로의 차이
  - 경로 1 `chrono_judge.py:1163-1166`은 placement = batch `pool` = prelaunch `batch_plan`(ecore)를 봅니다. 통과합니다.
  - 경로 2 `p5k_chrono_recount.py:527-529`는 `pl.mode == e.planned_pool and e.pool == e.planned_pool`을 요구합니다. ecore ≠ pcore이므로 K-6 거짓이 되고, `:784-798`에 따라 stop입니다.
- BT-C 근거와의 관계: 4.4 BT-C 근거(`:181`)는 "같은 스레드 수·풀"입니다. REM R8은 pcore에서 돌았는데(REM batch 10행 모두 pcore) C3는 ecore로 계획돼 있습니다. [추정] E 풀에서 비트가 같다는 근거는 찾지 못했습니다(decision_log·00_docs에서 grep 0건).
- 권장 조치
  - 12행을 모두 P로 돌립니다. `sched_main.json`의 `e_cases`를 비우고 `parallel_e`를 0으로, `chrono_batch_plan.json` pool을 모두 `pcore`로 바꿉니다. 원판 12.2 기준 약 6 h입니다(compute-scheduler-expert 재배치).
  - 이 방법은 규칙·도구 변경 없이 규칙 원문을 따르고 BT-C 전제도 맞춥니다.
  - E를 꼭 써야 한다면 rev3(결과 전)와 경로 2 수정이 필요합니다.

**[실행 전 수정][R·C] 6. 경계값 비교에서 두 경로가 다릅니다. 경로 1은 1e-9 여유를 두고 경로 2는 엄격하게 비교합니다. (등급 영향 있음: 경계에서 통과 ↔ 미달, K-10 불일치 → 판정 불가)**
- 근거
  - 경로 1: `las_p5r4k1_judge.py:1622`(C-S `> 0.001 + 1e-9`), `:1740-1741`(R-1/R-2 `<= limit + 1e-9`). `chrono_judge.py:1493`, `:1657-1659`도 같습니다.
  - 경로 2: `p5k_recount.py:1180`(`med <= R1_MEDIAN_S`), `:508`(`(sc - sr) > CS_LIMIT_M`), `p5k_chrono_recount.py:764`. 여유가 없습니다.
  - 규칙 10.2의 "수치 허용 1e-9"는 두 경로의 값을 대조할 때 쓰는 허용이고, 문턱 비교에 대한 문장은 없습니다.
- 실패 시나리오: READY 시각은 0.1 s 단위로 양자화됩니다. Δt 중앙값이 정확히 +1.0 s(부동소수 1.0000000000000142 등)이거나 최대가 +5.0 s이면, 경로 1은 통과이고 경로 2는 미달입니다.
- 권장 조치: 결과 전에 둘 중 하나로 맞춥니다.
  - (가) rev3 한 문장("문턱 비교는 1e-9 허용" 또는 "정수 주기로 비교")과 두 경로 반영
  - (나) 경로 1의 여유를 없앱니다(python-expert). 도구 sha가 바뀌므로 K-0 값을 다시 고정합니다.
  - 어느 쪽인지는 확인 필요 2입니다.

**[기록][T] 7. 봉인 뒤 결과 전에 구현자가 돌린 짧은 실행이 있습니다. 판정서 1.1 공개에 넣어야 합니다.**
- cad-expert(`agent-ae7ef1adcc8406210`)
  - 01:34:50Z(10:34 KST, 원판 봉인 뒤, rev1 봉인 전)에 `s9_batch run V5-LAS-P5R4-K1-GS --only P5K_A4_…_P5r4 --e-cases …`(10 s, E 풀)을 돌렸습니다.
  - 출력은 키 이름뿐입니다(`p3b.P3-3_leg_force` → `['criterion']`, departure 없음). 01:47:20에 batch 폴더를 지웠고, 커밋 `ff07ac9` 메시지에 남아 있습니다.
- python-expert(`agent-ab36bf883368e6b9d`)
  - 01:46~01:58Z에 trial 3건을 scratchpad `p5k1\trial_*.jsonl`로 돌렸습니다: Z-0 ref 1줄 `D1|H-R-A|rigid+J1@FR|T|diag-op|K3|VB|e0.002`, Z-A cand 1점 `…#P5r4-LT-c1-j1`, Z-S 짝 `D1|H-S-A|G1+J1@FL|T|flat|K1|VB|e0`.
  - 출력은 비트 일치 참·거짓과 키 이름, 그리고 trial 판정 `stop: identity` 사유뿐입니다. 셋 다 표본 안의 키입니다.
- rev1·rev2의 "대상 행 0행"은 글자 그대로는 맞습니다. 다만 판정서에는 이 실행들(시각, 명령, 출력 범위)을 적어야 합니다.

**[기록][I] 8. 두 경로 독립성: 경로 사이에 코드·출력이 오간 흔적은 없습니다. 다만 경로 2가 프로젝트 모듈을 읽었습니다(10.2 원문 "프로젝트 모듈을 열지 않는다"와 다름).**
- 경로 2 transcript(`agent-a243ef335c218e144.jsonl`, 도구 호출 239건)
  - 경로 1 파일명, 브랜치, worktree로 검색했습니다. 걸린 것은 규칙 본문 인용, 01:19:02의 파일명·줄 수 목록, 저장 줄 필드 이름뿐입니다.
  - 그 밖에 읽은 것
    - `c2.py`: 01:24~01:26, 01:50~01:51
    - `git show ff07ac9:run_S9.py` 4010~4160행, `las_p5r4_k1_chrono_rows.py` 375~454행: 01:50~01:51. 메인 세션이 "cad-expert 코드는 읽어도 됨"이라고 허락했습니다.
    - 자기의 앞선 경로 2 `k1rem_twopath/recount_rem.py`
  - 이 읽기는 handback(01:48:39, 01:54:11)에는 공개돼 있지만 봉인 문서(rev2)에는 RV2-3 인용 하나뿐입니다.
- 경로 1 transcript(`agent-ab36bf883368e6b9d.jsonl`, 519건): 경로 2 파일은 `git rev-parse` blob id와 `commands_path2.md`의 `Get-FileHash`만 했습니다. 경로 1은 그 다음 자리표시 점검에서 `commands_path2.md`를 뺐습니다. 내용은 열지 않았습니다.
- 권장 조치: 판정서 독립성 절에 위 읽기 목록을 적습니다. 메인 세션 허락이 10.2 원문과 다르다는 점도 함께 적습니다.

**[기록][E] 9. 경로 2 하네스는 묶음당 파일 하나만 읽고 `p5k_<묶음>_resume.jsonl`을 읽지 않습니다.**
- 근거: `p5k_recount.py:827-837`, `--bundle`은 경로 하나입니다(`:1350`). 경로 1은 `p5k_Z*.jsonl` 전부를 읽습니다.
- 실패 시나리오: 10.1 `--resume`으로 재실행하면 경로 2의 `errors_left`가 0보다 커져 incomplete가 됩니다. K-10 불일치로 이어지고, 판정은 보수 쪽(판정 불가)입니다.
- 권장 조치: 재실행은 묶음 안 attempt 2(같은 파일)로 끝내고 `--resume`은 쓰지 않습니다. 써야 한다면 판정 불가를 받아들이고 공개합니다.

**[기록][E] 10. gate_scan 경고 11건을 직접 확인했습니다. 빈 집합 통과는 없습니다.**
- `bit_predictions`(`:1338`)는 빠진 줄을 completeness(`:1311-1316`)가 incomplete로 잡습니다. 순서 관문(`targeted.py:700`)도 Z-0·Z-A 건수를 정확히 요구합니다.
- `rules_record`의 `all()`(`chrono_judge.py:512`)은 봉인 규칙 13개가 고정이라 빌 수 없습니다.
- `per_row_check`(`:1223`)는 빠진 행을 `missing_reasons`가 따로 처리합니다.
- 태그 단일 비교 2건은 setting 비교(VB/V0)이고 태그 선택이 아닙니다.
- 경로 2 Chrono `k_ok = all(i["ok"] is not False)`(`:784`)는 None 항목(키 부재 등)을 통과로 셉니다. 경로 1은 같은 경우를 stop으로 봅니다. 보수 쪽 K-10 불일치일 뿐 거짓 통과는 아닙니다.

**[기록][R] 11. 실행 도구가 스스로 정한 해석입니다(확정된 문장 없음, 판정서에 적을 것).**
- S-5 누적에 판정 불가 짝도 넣습니다(`targeted.py:576-592`). 규칙의 "위반 짝 ≥ 5"보다 엄격합니다.
- Z-X 순서 관문은 앞 묶음에 줄이 있는지만 보고, 앞 묶음의 미달 여부는 보지 않습니다(`:702`). S-4 "다음 묶음 not_run"은 메인 세션이 지켜야 합니다.
- `p5r4_config`는 LAS-b가 꺼진 config와 이미 P5r4인 config를 그대로 둡니다(`:146-162`, 건수만 기록). K-5가 줄마다 잡으므로 결과에는 닿지 않습니다.

**[기록][S] 12. 봉인 관련 기록입니다.**
- `las_rev_targeted_rules_rev1.sha256`에 봉인 시각이 없습니다(seal_check에 `-`로 나옴).
- `las_k1_rules_adopt_rev1.md`(730dbb3d)는 0절 표에 없습니다(code_pin_missing 2건). 원판 0절이 adopt 9.2만 이어받으므로 규칙과 맞습니다.
- 같은 폴더의 `las_p5r4_k1_rules_rev2_draft.md`가 `las_p5r4_k1_rules*` 이름에 걸리지만 도구는 이름 상수로 고정합니다. 영향은 없습니다.

**[기록][I] 13. G-S 필드 점검(`las_p5r4k1_gs.py:236-243`)은 경로 1이 읽는 필드만 봅니다.**
- 경로 2가 모든 줄에서 읽는 `values.times.t_first_ready_s`(`p5k_recount.py:105,111`)는 D-1 줄에서 점검하지 않습니다.
- 저장 기준 줄 1,098줄에는 이 키가 모두 있습니다. `d1.t_ready_s`와도 같습니다: 일치 1,031, 다름 0, 둘 다 None 46.
- 따라서 잠재 결함일 뿐입니다.

**[기록][R] 14. 단계 로그 `errors N`은 첫 시도를 포함합니다(`targeted.py:848`, RV2-8).**
- 묶음 안 재실행이 성공해도 `errors 1`이 찍히고, `log_errors.py`가 발견으로 보고합니다. 도구 종료 코드도 1입니다(`:855`).
- 그런데 `commands.md:95`는 "0이 아니면 다음 묶음을 띄우지 않는다"고 적습니다. 이 문장대로면 회복된 인프라 오류에도 진행이 멈춥니다. 확인 필요 3입니다.

## 규칙↔도구 대조표 (주요 항목)

| 항목 | 규칙 | 도구 | 판단 |
|---|---|---|---|
| 묶음 줄 수 Z-0/A/T/S/C | 6/102/384/60/912(`rules.md:136-143`) | `targeted.py list` 출력 6/102/384/60/912, problems 0 | 같음 |
| 부록 A 목록 sha 9개 | `rules.md:591-601` | list 재계산·manifest | 모두 같음 |
| Chrono 12행 argv | 4.3 | `chrono_rows_main.json` | `--threads 4`, seed, `--expect-controller` 새 태그, `--las-candidate`만 다름. 금지 인자(`--las-off`·`--k1-*`·`_TCL`·`--k2`) 0. G-S argv는 `--duration 10`만 다름(12/12) |
| 풀 | 4.3 "계획 풀 P" | sched_main E 4행 | **다름**(5번) |
| `--las-candidate` 순서·거부 | 11.2 | `run_S9.py:3966-4044`(b0+관문 점검 → 덮어쓰기 → 후보 점검 → 만든 제어기 점검, `--las-off`·`--k1-forced-block first`·`--k2 on`이면 종료 2) | 같음 |
| 16.1 거부 문구 | O-2·O-3·O-6·O-7 | `las_phase_diag.py:778,784`, `targeted.py:634`(maxtasksperchild=1), `run_S9.py:2916,2919` | 있음 |
| 하네스 두 번 적용 | 2절 | `install_all`(`:412-431`): FB 후보 L은 감싸기 없음, 옛 후보 감싸기 호출 0, 덮어쓰기 재설치 거부(`:174`) | 없음 |
| 16.5 env | 표 | 실행기가 넣는 값: `run_S9.py:101,102,108`, `fb_targeted.py:122-123`, `run_v5.py:42-43`, `las_targeted.py:81-82`, `verdict_runs.py:18-22`. 저장 기준 줄 threads는 모두 1, TBB | 표에 없는 변수 0 |
| E-2 W-1 | ③ 판정을 기준 태그로 | `is_p3_expected`(`final_C4G2_P3_LAS_K1`) = 참, `final_C4G2_LAS_K1` = 거짓, `_P3_K1`·`_TCL` 조합 = 참 | 충족 |
| RV2-2·3·13·14 | rev2 | C-S·C-F의 None 처리, departed 3분기, BT-C 128.0 이하, 토큰 키 4개 | 두 경로 같음(경계 허용 6번만 다름) |
| BT-C 기준 npz | `rules.md:181` | REM R7 `ebf86d1d…`, R8 `97aace61…`, 지금 파일과 같음 | 같음 |

## 확인 필요
1. 자리표시를 채울 위치(2번): prelaunch 폴더를 추적에서 빼는 커밋 1회 / 추적 밖 sidecar 파일 / 도구 허용 목록 변경(코드 변경, 재감사) 중 하나. 16.4 표의 "놓이는 곳"과 S-10 점검 대상을 어떻게 읽을지도 함께 정해야 합니다.
2. 문턱 경계 비교(6번): 1e-9 허용, 엄격 비교, 정수 주기 비교 중 무엇으로 할지. rev3가 필요한지 판정 에이전트(control-expert)가 정합니다.
3. S-9 "errors N > 0"을 attempt 2가 성공한 경우에도 적용하는지, 아니면 `errors_left` 0이면 진행하는지(14번).
4. Chrono E 풀 사용 여부(5번): 원판 4.3을 따라 P만 쓸지(권장), E를 쓰려고 rev3와 경로 2를 고칠지.

## 위임 필요
- **compute-scheduler-expert**: Chrono 12행 P 전용 배치표. `sched_main.json` e_cases 0, `chrono_batch_plan.json` pool 모두 pcore.
- **python-expert** (확인 필요 2에서 (나)를 고르면): `las_p5r4k1_judge.py:1622,1740-1741`, `las_p5r4k1_chrono_judge.py:1493,1657,1659`의 `+ TOLERANCE`를 없앱니다. 바뀐 sha로 K-0을 다시 고정합니다.
- **tools/verif 후보** (python-expert): "두 경로 G-S 필드 합집합 점검". 입력은 경로 1·2 도구의 읽는 키 목록과 G-S 줄, 출력은 빠진 키, 종료 코드는 0/1/2입니다.

## 메인 세션 권고
- prelaunch 전에 한 번 커밋합니다: 3번(k2 md), 4번(`-text`·exclude), 2번(prelaunch 추적 해제 또는 정한 방식). 그 뒤 HEAD를 실행 HEAD로 적고, 그때부터 postrun까지는 커밋·병합을 하지 않습니다.
  - 미병합 브랜치 `worktree-agent-ad8565b34cde410d8`(`04_scripts/03_control/k2/loc_shadow/*` 6개)와 `ideal-stage1-judge-fix`(`ideal_stage1_judge.py`)가 `04_scripts`를 건드립니다. 병합하면 Chrono K-1 `git diff --quiet … -- 04_scripts`가 깨집니다.
- 실행 HEAD에서 단위 시험을 돌립니다(E-4).
  - 저는 경로 1 판정 시험 64개와 경로 2 시험 40개를 돌렸고 모두 통과했습니다.
  - `test_las_p5r4k1_targeted.py`(dynamics-dev)와 `05_tests/unit/test_las_p5r4_k1_chrono_rows.py`(Chrono-dev)는 돌리지 않았습니다.
- commands.md의 두 기대 sha를 1번 값으로 고친 뒤 G-S를 시작합니다(E-8).
- 판정 전 자리표시 점검에는 `commands_path2.md`도 넣습니다(16.4 글롭 `prelaunch/*.md`에 포함됨).

## 검사하지 못한 것
- 재집계(C축): 결과가 0건이라 대상이 없습니다.
- 경로 1 하네스 판정 도구의 Z-A 격자 판정, C-4 예외, CK-1 세부와 경로 2의 항목별 동치: 단위 시험 통과와 rev2 항목 표본 대조(RV2-2·3·13·14)만 했습니다.
- G-S 목록 117줄의 단계 분할이 16.2·RV2-5와 맞는지 전수로 다시 세지 않았습니다. 묶음별 건수(Z-0 6, Z-A 6, Z-T 16, Z-S 24, Z-C 64, Z-X 1)와 표본 밖 23만 확인했습니다.
- 경로 1 판정 도구가 복사해 온 옛 판정 함수(`pair_violations` 등)가 원본과 같은지는 대조하지 않았습니다.
- `v5_rerun:423`, `u3_reuse:235`, `chrono_t45_replay:833`의 W-1 반영: 이 규칙의 판정 경로 밖이라 보지 않았습니다.

## 실행한 검증
- **인터프리터**: python-dev `-I -B`(`MKL_THREADING_LAYER=TBB`). 프로젝트 import가 필요한 것만 dynamics-dev·Chrono-dev `-I -B`에 `PYTHONDONTWRITEBYTECODE=1`을 붙였습니다.
- **봉인·관문 도구**
  - `seal_check.py`: 규칙 13판과 코드 5개(경고 2: `code_pin_missing` adopt_rev1)
  - `gate_scan.py`: 도구 6개(경고 11, 모두 직접 확인)
  - `placeholder_scan.py`: prelaunch(미채움 22)
  - `source_guard` snapshot/verify
- **즉석 스크립트**(scratchpad `verif\`, 보고 전 삭제)
  - manifest 해시·blob 대조, 저장 줄 키 존재와 READY 출처 일치 수
  - transcript 3개 검색(경로 1·2, cad-expert)
- **건조 실행·시험**
  - `las_p5r4k1_targeted.py list`(dynamics-dev, 종료 0)
  - `s9_batch.py list V5-LAS-P5R4-K1`(Chrono-dev, 12행)
  - pytest: 경로 1 판정 시험 64개(python-dev), 경로 2 시험 40개(dynamics-dev), 모두 통과
  - `is_p3_expected` 한 줄 확인
- **git 조회**: log, diff --stat, ls-files --eol, check-attr, worktree list, 브랜치별 diff --name-only
- **부산물**: 대상 폴더 `__pycache__`·`.pyc` 새로 생긴 것 0. scratchpad `verif\` 폴더는 지웠습니다.
- **재확인**: 최종 판정 직전 HEAD `4b36cf5` 그대로이고, 입력 23개 sha가 snapshot과 같습니다.
- **메모리 갱신**: `C:\Users\jinbeom\.claude\agent-memory\verif-protocol-auditor\audit_pitfalls.md`, `MEMORY.md`(자리표시 dirty 관문, `-text` 도구의 CRLF 기대 sha, 두 경로 1e-9 허용·resume 파일, K-6 계획 풀 출처 갱신)
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha las_p5r4_k1_rules_rev1.md f39846d6…, las_p5r4_k1_rules_rev1.sha256 5e07519e…, las_p5r4_k1_rules_rev2_draft.md 2ebd6446…, las_p5r4_k1_rules_rev2.md e0a7d1e5…, las_p5r4_k1_rules_rev2.sha256 24e4ee95…, las_p5r4_k1_rules.md 5ee2bac0…, las_p5r4_k1_rules.sha256 9c56f11b…, chrono_batch_plan.json 2d1363c1…, chrono_rows_main.json e40788ff…, commands_path2.md 4becce15…, commands.md cf5388c1…, gs_list.json a903bd8e…, manifest.json 9f54dd43…, sched_gs.json fbefc73a…, sched_main.json 7e82ec75…, las_p5r4k1_chrono_judge.py 2b7dcb7b…, las_p5r4k1_gs.py 34ce26f8…, las_p5r4k1_judge.py 4c07bfef…, p5k_chrono_recount.py 56f424a4…, p5k_recount.py fac91918…, test_p5k_recount.py dd5964a0…, las_p5r4k1_targeted.py 16f35625…, las_p5r4_k1_chrono_rows.py 517ffb74…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음

---

## 메인 세션 처리 (2026-11-11, 감사 원문 뒤 덧붙임)

사용자 결정(AskUserQuestion):
1. 5번(Chrono 풀, 등급 영향): 12행 모두 P. 원판 4.3 그대로, 규칙·도구 변경 없음. compute-scheduler-expert에 P 전용 배치표를 다시 받는다.
2. 6번(문턱 경계 비교, 등급 영향): rev3 한 문장 "문턱 비교는 1e-9 허용"으로 두 경로를 통일한다. 경로 2에 허용을 더하고 경로 1은 그대로 둔다.
3. 2번·확인 1(자리표시 위치): prelaunch 폴더를 git 추적에서 뺀다(`git rm --cached` + `.git/info/exclude`). 채우기는 추적 밖에서 하고, 판정서에 채우기 전·후 sha를 함께 적는다.
4. 14번·확인 3(errors N): attempt 2가 성공해 `errors_left` 0이면 다음 묶음으로 진행한다. 회복된 오류는 판정서에 기록한다.

등급 영향 없는 1·3·4번은 메인 세션이 실행 전 커밋에서 처리한다. 그 뒤 재감사한다.
