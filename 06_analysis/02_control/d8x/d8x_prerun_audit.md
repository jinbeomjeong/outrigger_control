<!-- verif-protocol-auditor 리포트 원문(2026-11-10). 대상: D8x 하네스 본 실행 전 감사, H_impl ba6671c. 메인 세션이 편집 없이 저장. 결정은 맨 끝 "메인 세션 덧붙임" 절에만 쓴다. -->

# D8x 하네스 본 실행 전 감사 (verif-protocol-auditor, 2026-11-10)

## 감사 요약
- **시점**: 실행 전. 중심 축은 S·E·I·R이고, T는 눈에 띄는 것만 봤다. C축은 결과가 없어 해당이 없다.
- **대상**: D8x 하네스 묶음. 순서는 G0 rev3 60평가 → R-a off 910 / on 192 → R-c off 192 / on 96이다. Chrono 19행은 범위 밖이다.
  - 실행 위치: master `ba6671c`(H_impl, main checkout `C:\workspace\outrigger_control`).
  - 감사 시작과 끝 모두 HEAD는 `ba6671c`였고, `git status --porcelain --untracked-files=no`는 비어 있었다.
- **도중 반영**: 실행 계획 변경 두 건을 감사에 넣었다.
  - P코어로 전환(사용자 결정, 14시경)
  - 확정 러너 `d8x_runner_P.ps1`·`d8x_steps_P.json`·`make_d8x_runner_P.ps1`·`check_empty.py` 추가
- **기준 문서**(`06_analysis/02_control/d8x/`): 원판 a377b9bb, rev1 ad16f452, rev2 5f3fa620, rev3 2318fb5c, rev4 5233c517, rev5 63437019, rev6 d584c8da.
  - 7판 모두 `.sha256` 첫 토큰과 raw로 일치한다.
  - 7판 모두 i/lf·w/lf이고 `-text`(check-attr `unset`)이며, CRLF 0, BOM 없음이다.
- **판정: 차단 0 / 실행 전 수정 3 / 기록 9.**
  - 실행 전 수정 셋은 모두 러너 설정이나 실행 전 기록으로 몇 분 안에 닫을 수 있다.
  - 어느 것도 고치지 않으면 엄격한 쪽(판정 불가)이 아니라 **기록이 조용히 흐려지는 쪽**으로 간다(P-1, P-2).
- **결론: P-1·P-2를 러너에 반영하고 P-3을 실행 전 기록에 적으면 실행할 수 있다.** 규칙 개정(rev7)이 필요한 항목은 없다. P-3만 사용자 확인이 필요하다.

## 발견 사항 (심각도순)

### [실행 전 수정][I] P-1. 러너 공통 env에 `MKL_THREADING_LAYER`가 없다. dynamics-dev를 활성화 없이 `python.exe`로 직접 부르면 이 값이 비고, R-a·G0와 R-c의 MKL 계층이 갈린다 — 등급 영향: 고치면 없음
- **근거**
  - `csx\make_d8x_runner_P.ps1`의 `$env1`에는 `MKL/OMP/NUMBA/OPENBLAS_NUM_THREADS`만 있다. `d8x_runner_P.ps1:24-36`의 13단계 `Env`도 모두 같다.
  - 실측: `C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B -c "...os.environ.get('MKL_THREADING_LAYER')"` → `None`. 메인 세션 셸에서도 값이 비어 있었다(사용자·시스템 변수도 비어 있음).
  - R-c는 영향이 없다. `verdict_runs.py:18`이 `os.environ.setdefault("MKL_THREADING_LAYER", "TBB")`를 하고, `run_v5.py:548`이 풀을 띄우기 전에 import하므로 spawn 자식이 TBB를 물려받는다.
  - R-a(`acc_d8.py`, `acc_common.py`)와 G0(`run_d8x_g0_rev3.py`)는 이 값을 설정하지 않는다. `c2py_r8d1_closed_loop.py` docstring은 "MKL_THREADING_LAYER=TBB"로 실행하라고 적었다.
  - 공개된 R-a 탐침(`.local_archive\...\d8x_probes\ra_probe_off.json`)의 `meta.d8x.identity_start.threads`는 `MKL_THREADING_LAYER: TBB`로 기록돼 있다.
  - prelaunch 기록의 `threads_expected`는 `"MKL_THREADING_LAYER": "TBB"`다(`d8x_judge.py:396-398`). 그러나 실제 값과 대조하는 코드가 없다.
- **실패 시나리오**
  - 한 행렬 안에서 R-a·G0는 기본 MKL 계층, R-c는 TBB로 돈다. 원판 I-1은 이 값의 기록만 요구하지만, 탐침·옛 계열과 정체성이 달라진다.
  - MKL 기본 계층에서 worker가 0xC06D007F로 죽으면 `Pool.imap_unordered`가 멈추거나 오류 행이 생길 수 있다. 판정 불가 쪽이고 조용한 통과는 아니다.
- **권장 조치**(메인 세션): `$env1`에 `MKL_THREADING_LAYER='TBB'`를 더하고 러너를 다시 생성한다. 실행 뒤 판정서에서 R-a `meta.d8x.identity_start/end.threads`, R-c `hrx_*.identity.json`, G0 `meta.identity`의 값이 모두 TBB인지 확인한다.

### [실행 전 수정][I·E] P-2. 이어 돌리기(`--skip-done`)를 하면 확인 단계와 prelaunch가 건너뛰어진다. R-a 드라이버는 partial을 이어 쓰면서 `identity_start`를 새로 쓴다. 또 어느 경로도 묶음 사이 HEAD = H_impl을 확인하지 않는다 — 등급 영향: 실행 중 커밋이나 재시작이 없으면 없음
- **근거**
  - 러너(`d8x_runner_P.ps1:123-125`): `.done`가 있으면 그 단계를 건너뛴다. `chk-*`와 `*-pre`도 `.done`를 남기므로, 재시작하면 빈 폴더 확인과 I-1(clean) 검사가 모두 빠진다.
  - `acc_d8.py:284-293`
    - `identity_start`는 프로세스가 시작할 때마다 새로 잰다.
    - `<out>.partial.jsonl` 줄은 id만 보고 "끝남"으로 센다.
    - 줄 안에는 커밋이 없다. `module_files_sha256`는 파일 **이름** 목록의 해시다(`d8x_record.py:288-290`).
  - 경로 1
    - `d8x_judge.py`에는 `identity_start`·`identity_end`·`is_clean`·`head`를 검사하는 코드가 없다(Grep 0건).
    - `judge_ra_file`(:576-598)은 stages·k1·봉인만 본다. `_rc_identity_seal_problems`(:611-625)는 봉인만 본다.
  - 경로 2(`d8x_recount.py:736-756`)
    - 묶음 안의 start/end clean과 같은 HEAD만 본다.
    - R-a는 마지막 시작의 start만 남는다.
    - R-c는 `starts[0]`·`ends[-1]`을 쓴다(:774).
    - 어느 경로도 "HEAD == ba6671c"와 묶음 사이 동일성을 보지 않는다.
  - prelaunch를 다시 돌리면 `--record-out` 파일을 덮어쓴다(`d8x_judge.py:416-417`).
- **실패 시나리오**
  - ra-off가 도중에 끊긴다. 그 사이 다른 세션이 master에 커밋한다(감사 중에도 13:07에 새 worktree 3개가 생겼다. 기록 C-8). 러너를 다시 띄운다.
  - 그러면 chk와 pre가 건너뛰어지고, 옛 HEAD의 partial 줄과 새 HEAD의 줄이 한 `ra_off.json`에 섞인다. 그런데 `identity_start`와 `identity_end`는 모두 새 HEAD라 두 경로 모두 정체성 문제를 내지 않는다.
  - rev4 3·rev5 4의 "H_impl 한 커밋"이 조용히 깨진다.
- **권장 조치**(메인 세션)
  1. 각 실행 단계(g0-rev3, ra-off, ra-on, rc-off, rc-on) 바로 앞에 **HEAD 고정 단계**를 둔다. 내용은 `git rev-parse HEAD`가 `ba6671c4faaf7a26773dcfb9f554ce2491b466ed`이고 status가 비어 있지 않으면 exit 1이다.
  2. 재시작할 때는 이 단계의 `.done`만 지운다. `chk-*`의 `.done`은 남긴다. off 결과가 있으므로 지우면 빈 폴더 확인이 실패하는데, 그것은 설계대로다.
  3. 재시작하면 첫 prelaunch 기록을 다른 이름으로 보존한다.
  4. 판정서에 정체성 표를 손으로 적는다. 대상: G0 `meta.run_commit`·`clean`, R-a `meta.d8x.identity_start/end.git`·`meta.git_head`(acc provenance), R-c sidecar의 모든 start/end 항목, prelaunch 4개의 `head`. 모두 `ba6671c`이고 clean인지 확인한다.
  5. 실행이 끝날 때까지 master 커밋과 병합을 금지한다(전제 재확인).

### [실행 전 수정][R·T] P-3. E코어 → P코어 전환은 봉인 원문 3절 표의 "E코어"와 다르다. 다만 I-1이 "P코어 묶음은 배치표 값"을 허용하고, 기준·문턱과는 무관하다 — 등급 영향 없음(실행 전 기록으로 처리)
- **근거**
  - 원판 `d8x_rules.md:34`(Q5 "축소·하네스는 E코어에서 지금"), `:134`("E코어 축소·하네스"), `:166-167`(3절 표 R-a·R-c "E코어").
  - 같은 원판 `:154` I-1: "affinity 마스크(E코어 `0x0FFF0000`, P코어 묶음은 배치표 값)".
  - 두 경로 모두 마스크로 판정하지 않는다. 경로 2는 `affinity_mask`를 기록만 한다(`d8x_recount.py:745`).
  - 확정 러너: 마스크 0xFFFF, worker 8, Normal. 끔·켬 팔은 같은 P 풀이다(`d8x_steps_P.json`의 prelaunch·rc 단계 `--mask 0xFFFF`, 러너 마스크가 자식에게 상속됨).
- **실패 시나리오**: 기록 없이 돌리면 원판 3절 글자대로는 "정한 엔진·도구와 다른 실행"이 된다. 결과를 본 뒤에 사정을 설명하면 사후 해석이 된다.
- **권장 조치**(메인 세션)
  - 실행 전에 결정 기록(decision_log 한 줄 또는 prelaunch 옆 메모)에 적는다: 사용자 결정 시각(14시경), 이유, P 마스크 0xFFFF, worker 8, 우선순위 Normal, "모든 하네스 묶음과 두 팔이 같은 P 풀".
  - 판정서 "규칙과 다른 실행" 절에 옮긴다.
  - rev7로 할지는 확인 필요 1이다. 이 감사의 판단은 실행 전 기록으로 충분하다는 것이다. 이유는 I-1이 P 묶음을 명시적으로 허용하고, 하네스는 단일 스레드 결정론 계산이라 풀이 판정 값에 들어가지 않기 때문이다.
  - `run_d8x_g0_rev3.py:16` docstring의 "E-cores"는 문구만 다르다.

### [기록][E·R] C-1. 드라이버 오류 행의 verdict가 두 경로에서 다르다. 경로 1은 `not_judgeable`, 경로 2는 `fail`("E-2 driver error")이다 — 등급 영향: 오류 행이 생기면 G3 판정 불가(엄격한 쪽)
- 근거: 경로 1 `d8x_judge.py:649-650`(R-a), `:746-747`(R-c). 경로 2 `d8x_recount.py:668-670`, `:826-828`.
- 오류 행이 하나라도 생기면 rev6 1-1 행별 대조가 어긋난다. rev5 3.1-1(판정 불가 우선)에 따라 등급은 판정 불가(B-ID, 재실행)가 된다. 미달로 가지 않는다.
- rev6 2 (iv)가 이 두 처리("판정 불가(E-1)나 `fail`(E-2)")를 이미 인정하고 있다. 결과 전에 판정서 키 대응표(rev6 C-5 표기 대응)에 "오류 행: 경로 1 not_judgeable ↔ 경로 2 fail = 알려진 차이, B-ID"를 적어 두면 사후 해석을 피할 수 있다.

### [기록][E] C-2. `g0-rev3` 단계만 `-B` 없이 `-I`로 돈다
- 근거: `d8x_steps_P.json` g0-rev3 `"... -I 04_scripts/01_dynamics/run_d8x_g0_rev3.py --workers 8"`. 다른 단계는 모두 `-I -B`다.
- 저장소에 `__pycache__`가 생긴다. 추적 밖이라 I-1 status에는 영향이 없다. `-B`를 붙이는 편이 깨끗하다.

### [기록][S] C-3. `d8x_record.py:44`의 `RULES_PATH`(원판만)는 쓰이지 않는 상수다
- `seal_check` `code_pin_missing`(rev1~rev6 빠짐)은 오탐이다. 저장소 Grep 결과 `d8x_record.RULES_PATH`를 쓰는 곳이 없다.
- 실제 봉인 대조는 `d8x_spec.RULES_FILES`(7판, `d8x_spec.py:42-57`)가 하고, `LATEST_RULES_REV="rev6"`다. `s6_stage2.py:104-117`에도 7판이 고정돼 있다.

### [기록][S] C-4. `d8x_points.json`은 인덱스부터 CRLF다(`i/crlf w/crlf attr/-text`)
- I-3은 JSON 내용으로 비교하므로 영향이 없다(`d8x_judge.py:262-270`, 감사 확인 `points_equal_fresh True`).
- R-a meta의 `points_sha256`는 LF 정규화 해시다(`d8x_record.py:61-63`). raw sha와 값이 다르므로, 판정서가 sha를 인용할 때 어느 해시인지 밝힌다.

### [기록][I] C-5. 우선순위와 풀 라벨은 러너 로그(scratchpad)에만 남는다
- `d8x_runner_P.ps1:144-145`가 단계마다 `mask`·`priority`를 `d8x_logs_P`에 쓴다.
- 프로젝트 기록에는 마스크만 남는다: prelaunch `affinity_mask` 인자, `run_identity`의 psutil 부모 마스크(`d8x_record.py:306-312`).
- R-c 줄의 `job.mask`는 기록 전에 지워진다(`run_v5.py:566-567`).
- scratchpad는 휘발성이므로 실행 뒤 러너 로그를 `.local_archive`로 보존하고 판정서에 단계별 마스크·우선순위를 옮긴다.

### [기록][E] C-6. `check_empty.py`의 범위
- g0는 `d8x_g0_rev3.json`만 본다. ra·rc는 `ra_*.json`, `*.partial.jsonl`, `hrx_*.jsonl`, `*.identity.json`을 본다.
- 결과 이름 패턴은 모두 덮는다. prelaunch 기록과 `d8x_g0_judgement.json`은 보지 않지만, 둘 다 덮어쓰는 파일이라 섞임 위험이 없다.
- 재시작 때 `.done` 때문에 chk가 건너뛰어지는 것은 설계상 맞다(on 앞에는 off 결과가 있음). 위험은 HEAD 섞임이고, P-2의 HEAD 고정 단계가 그것을 막는다.
- 현재 상태: `d8x/ra`·`d8x/rc` 폴더 없음, `d8x_g0_rev3.json`·`d8x_expect_k1.json`·prelaunch·selection 없음(Test-Path로 확인).

### [기록][E] C-7. `gate_scan` 경고 3건은 모두 오탐이다
- `run_d8x_g0_rev3.py:95`: `required`가 늘 3개 이상이다.
- `d8x_judge.py:552`: `items`가 G0-1~3으로 늘 3개 이상이다.
- `d8x_judge.py:498` `"ok": not differences`: 기록이 비면 `:489-490`이 따로 문제를 낸다.

### [기록][T] C-8. 다른 에이전트가 진행 중이다
- 감사 도중 13:07에 worktree 3개가 새로 생겼다(`agent-a2d2d914a133c1be5`, `agent-a5b6a582c60728dec`, `agent-ae275bd048e09d38a`). 담긴 것은 체크아웃된 추적 파일뿐이고 결과는 없다.
- 미병합 브랜치 `worktree-agent-a5f85594522e11cd2`는 `las_p5r4_k1_rules.md` 한 파일만 더한다. 실행 경로 밖이다.
- 실행 중 이 브랜치들의 병합·커밋이 P-2의 위험원이다.

### [기록][S] C-9. `04_scripts\03_control\s9\__pycache__` 폴더의 mtime이 13:08:27로 바뀌었다
- 그 안에 새 파일은 없다(가장 새 파일이 11-08).
- 이 감사는 `-B`와 `PYTHONDONTWRITEBYTECODE=1`로만 실행했다. 다른 세션의 활동으로 보인다 `[추정]`.

## 지난 점검 항목의 닫힘 (rev6 점검 R-1~R-3, rev5 점검 B-2·B-3a·B-4)

| 항목 | 위치(ba6671c) | 판단 |
|---|---|---|
| R-1 행 결합 키 | R-a `identity = {"id", "k1", ...}`(`d8x_judge.py:647-648`), R-c `RC_JOIN_FIELDS`(slope_name, level, crawler_k_scale, setting, eps)+`k1`(`:724-737`). 경로 2 `key_tuple`(`d8x_recount.py:812-813`)과 같은 필드 | 닫힘. 실행 전 기록에 이 규칙을 그대로 적는다 |
| R-2 오류 행 팔 표시 | 오류와 NotJudgeable 반환에도 `**identity`(`:650`, `:664`, `:747`, `:767`). `rows_off`·`rows_on`을 따로 냄(`:696`) | 닫힘 |
| R-3 실행 기록 봉인 | R-a `meta.d8x.rules_seals`(`acc_d8.py:266`), R-c `<out>.identity.json`의 start/end마다 `rules_seals`(`run_v5.py:513-522` → `d8x_record.run_identity` `:325-331`), G0 `meta.rules_seals`(`run_d8x_g0_rev3.py:58-66`, `:149`). 판정 쪽 대조: `d8x_judge.py:584`, `:707`, `:482-487`(7판 모두 sha 일치 요구) | 닫힘 |
| B-2 봉인 목록 rev5·rev6 | `d8x_spec.py:42-63`, `s6_stage2.py:104-117` | 닫힘 |
| B-3a Chrono 다섯 키 | `CHRONO_GATE_KEYS` 각각 + prelaunch `rows[case].k1_order_gate`(`:967-979`, `:1039-1045`, `:430-433`) | 닫힘(Chrono는 범위 밖, 코드만 확인) |
| B-4 report 기본값 | `k1_rows_failed` None → G1 not_judgeable, 종료 2(`:1257-1267`) | 닫힘 |

## 규칙↔도구 대조표 (이번 실행분)

| 규칙 | 원문 | 도구 | 결과 |
|---|---|---|---|
| 기대 수 G0 60 / R-a 910+192 / R-c 192+96 | 원판 3 `:165-190`, rev4 1.1 | `EXPECTED_COUNTS`(`d8x_spec.py:155`). 감사 재계산: `expected_ra_ids` off 910(고유 910)·on 192, `expected_rc_keys` off 192·on 96. `run_v5.py d1 --group H-R-X --k1 off/on --list` → 192/96 | 맞음 |
| R-a 세부 192/448/144/126 | 원판 `:176-180` | `acc_d8.d8x_cases`(`:72-131`) ↔ `spec.expected_ra_ids`(`:356-390`): 하단 robust β2+d0 1, kt 하단 rigid ×3 kt만 | 맞음(손계산 16·3·4, 16·4·7, 6·2·4·3, 7·2·3·2+7·2·3) |
| 점 좌표 rev1 1.2 | rev1 `:59-104` | `d8x_points.json` = `build_points()` 새로 만든 값(같음), 16/4/4, `point_table_problems` 0 | 맞음(값을 표와 하나씩 대조) |
| 팔 명시 | rev3 2 | `acc_d8.py:240-241`, `run_v5.py:507-508`, `d1_runs.py:489-490`, `d8x_record.k1_arm_is_on`(`:143-151`), prelaunch `:401-402` | 맞음(None이면 거부) |
| 끔 팔 False 설치 / 켬 팔 True | rev3 1·2 | `install_k1_order_gate`(`d8x_record.py:109-140`, 다른 값 두 번 설치 = 오류, 같은 값 = 멱등). 프리셋 gate True·LAS True·태그 `final_C4G2_LAS_K1`, 클래스 기본 False(감사 실측) | 맞음. 이중 적용 없음(같은 키 replace) |
| 기록: 요청과 실제 관문 | rev3 2 | R-a `run.k1_order_gate = effective_k1(controller)`(`acc_d8.py:178`), R-c `d1.d8x.k1_order_gate`(`d1_runs.py:450`), 요청 `meta.d8x.k1`·`job.k1` | 맞음 |
| 태그(E-6a~f) | rev3 1·3.1 | `EXPECTED_TAGS`(`d8x_spec.py:162-167`), `_tag_problems`(`:201-219`, `is_liftoff_slow_tag`·`is_order_gate_tag`, 접미사 문자열 비교 없음), 태그 히스토그램(`:628-637`) | 맞음 |
| 경로 2 `--expect` | rev3 3.3 | `path2_expect_doc()` = rev3 `:90-93` JSON(감사 비교 True), `expect-file`가 sha 출력(`:440-448`) | 맞음. 러너 전에 메인 세션이 만들고 sha를 적는다 |
| 빈 집합 | 원판 E-1, E-5 | 0행 → `actual != expected` → 판정 불가(`_status_of` `:235-238`, `_gate_of` `:1277-1281`). 중복 id·key 검출(`:643-645`, `:742-744`). G0 60 대조(`:530-531`) | 맞음 |
| I-1 clean·HEAD | 원판 `:154` | 시작 전에는 prelaunch만(`:418`). 끝 상태와 묶음 사이 HEAD는 경로 1이 보지 않고, 경로 2는 묶음 안에서만 본다 | **P-2** |
| 실행 기록 봉인 위치 | rev6 4, R-3 | 위 표 | 맞음 |
| G0 실행 위치·재계산 | rev3 4, rev4 3 | `run_d8x_g0_rev3`가 reuse 0·recompute 60·clean·closure blob을 기록. `judge-g0 --at-commit ba6671c`가 blob을 대조(`:465-499`) | 맞음 |
| 풀 | 원판 3 "E코어", I-1 | P 0xFFFF | **P-3** |
| `-text` | rev4 4 | `.gitattributes:42` `d8x/** -text`, `:43` `d8x_g0*.json -text`. 감사: ra/rc/partial/identity/expect/prelaunch/points/g0_rev3/g0_judgement 모두 `text: unset`. `core.autocrlf=true` | 맞음 |

## 확인 필요
1. (P-3, 사용자 또는 메인 세션) P코어 전환을 실행 전 결정 기록과 판정서 "규칙과 다른 실행" 절로 처리할지, rev7로 봉인할지 정한다.
   - 이 감사의 판단은 실행 전 기록으로 충분하다는 것이다. I-1 원문이 P 묶음 마스크를 허용하고, 기준·문턱·명령에는 변화가 없다.
2. (C-1, control-expert 또는 메인 세션) 드라이버 오류 행의 두 경로 표기 차이(`not_judgeable` ↔ `fail`)를 결과 전 키 대응표에 "알려진 차이 → B-ID"로 적을지 정한다. 등급 규칙을 바꾸지 않는다.

## 위임 필요
- 없음(코드 결함 없음). 선택 사항: python-expert에 경로 1 `judge-ra`·`judge-rc`의 I-1 끝 상태 검사와 `--expect-head` 검사(identity start/end clean, HEAD = 지정 커밋)를 넣는 안이 있다. 이번 실행에서는 P-2의 러너 단계와 판정서 손 확인으로 대신한다.
- `tools/verif` 후보(python-expert): "실행 기록들의 HEAD·clean 일괄 대조" 검사. 입력은 G0 json `meta`, R-a json `meta.d8x.identity_*`·`meta.git_head`, R-c `*.identity.json`의 start/end 목록, prelaunch json들, 그리고 기대 커밋이다. 출력은 파일별 head/clean 표이고, 불일치가 있으면 종료 1이다.

## 메인 세션 권고
- 러너 시작 전
  1. `$env1`에 `MKL_THREADING_LAYER='TBB'`를 넣는다(P-1).
  2. g0-rev3에 `-B`를 붙인다(C-2).
  3. 각 실행 단계 앞에 HEAD 고정 단계를 넣는다(P-2).
  4. 러너를 다시 생성한다.
  5. `d8x_judge.py expect-file`로 `d8x_expect_k1.json`을 만들고 출력 sha256을 적는다.
  6. P코어 결정을 기록한다(P-3).
- 실행 중: master와 다른 브랜치의 커밋·병합을 금지한다. 재시작은 P-2 절차대로 한다.
- 실행 뒤: 러너 로그 `d8x_logs_P`를 보존한다(C-5). 판정서에 정체성 표(P-2-4)와 MKL 계층 확인(P-1)을 적는다.

## 검사하지 못한 것
- 본 실행과 결과를 쓰는 건조 실행(acc_d8에는 결과를 쓰지 않는 하위 명령이 없다)은 돌리지 않았다. R-a 건수는 `d8x_spec.expected_ra_ids`와 손계산으로만 확인했다.
- `prelaunch`·`points`(쓰기)·`expect-file`은 파일을 쓰므로 실행하지 않았다.
- 두 경로가 결과에서 실제로 같은지(R-1 결합 결과)는 결과가 없어 볼 수 없다.
- MKL 기본 계층에서 R-a worker가 실제로 죽는지는 시험하지 않았다(P-1은 정체성 불일치만 근거로 함).
- `make_runner.py`가 만든 러너의 나머지 로직(예약·Job 제한)은 compute-scheduler-expert 범위라 보지 않았다.

## 실행한 검증
- 인터프리터
  - python-dev `C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B`(`MKL_THREADING_LAYER=TBB`, `-X utf8`): seal_check, gate_scan, source_guard, 한 줄 조회
  - dynamics-dev `C:\ProgramData\miniforge3\envs\dynamics-dev\python.exe -I -B`(`MKL_THREADING_LAYER=TBB`, `PYTHONDONTWRITEBYTECODE=1`): 프로젝트 모듈 import(`d8x_spec`·`C2Config`·`v5_options`), `run_v5.py d1 --group H-R-X --k1 off|on --list`(쓰기 없음)
  - Python은 모두 PowerShell 도구로 실행했다.
- `depcheck.ps1` → STAMP(이번 세션 이미 점검함).
- `seal_check.py --repo . "06_analysis/02_control/d8x/d8x_rules*.md" --code 04_scripts/03_control/d8x 04_scripts/02_chrono/s6_stage2.py 04_scripts/01_dynamics/run_d8x_g0_rev3.py`
  - 7판 모두 raw 일치, 고정 29곳, `code_pin_missing` 1건(오탐, C-3).
- `gate_scan.py`: d8x_judge·d8x_record·run_d8x_g0_rev3, 경고 3건(오탐, C-7).
- scratchpad `d8x_prerun_audit\counts.py`: 점 파일 = 새로 만든 값, 문제 0, R-a 910/192, R-c 192/96, `--expect` 문서 = rev3 3.3, 기본 태그, `arm_tag`.
- git 조회: `rev-parse`, `status`, `log`, `diff --stat 99293a8 ba6671c`(test_las_t3.py 한 파일), `diff --stat master...worktree-agent-a5f85594522e11cd2`, `check-attr text`, `ls-files --eol`, `config core.autocrlf`, `worktree list`.
- 파일 검색: 12:30(rev6 봉인) 뒤 `%TEMP%\claude`와 저장소에서 D8x 산출물·탐침 이름 → 정식 산출물 0건. 새 탐침 없음(worktree 체크아웃 파일만).
- 읽은 것
  - 규칙 7판 전체, rev6 봉인 점검 원문 전체
  - `d8x_judge.py` 전체, `d8x_spec.py`·`d8x_record.py` 전체, `acc_d8.py` 전체, `run_d8x_g0_rev3.py` 전체
  - `run_v5.py:330-570`, `d1_runs.py:380-503`, `d1_rows.py` H-R-X 부분, `acc_common.py` 조회 부분
  - 경로 2 `d8x_recount.py:640-880`과 Grep 결과
  - 러너 초안과 확정판(`make_d8x_runner_P.ps1`, `d8x_steps_P.json`, `d8x_runner_P.ps1`의 단계·skip-done 부분, `check_empty.py`)
- 만든 뒤 지운 것: scratchpad `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\6f3ebc4d-a5fb-4d9f-b214-d0ae5c515ee1\scratchpad\d8x_prerun_audit\`(guard.json, seal.md, counts.py)를 폴더째 지웠다. 이 감사가 남긴 `__pycache__`는 없다(C-9는 다른 출처 `[추정]`).
- 최종 판정 직전 확인: HEAD `ba6671c`, status 빈 목록, `d8x/ra`·`d8x/rc`·`d8x_g0_rev3.json` 없음.
- 메모리: `audit_pitfalls.md`에 일반 함정 두 줄을 더하고 `MEMORY.md` 색인을 갱신했다. 내용은 (1) skip-done + partial 이어 쓰기에서 생기는 HEAD 섞임, (2) env를 활성화하지 않고 직접 실행하면 MKL 계층이 빠지는 문제다.
- 원본 불변: 위반 — 입력 폴더에 항목 추가 7건(check_empty.py, d8x_runner_P.ps1, d8x_steps_P.json 외 4건)
  - 설명: 추가 7건과 변경 1건은 입력 폴더 가운데 `scratchpad\csx\`에서 생겼다. 메인 세션이 감사 도중(13:07~13:10) P코어 러너 파일(`check_empty.py`, `d8x_runner_P.ps1`, `d8x_steps_P.json`, `make_d8x_runner_P.ps1`, `state_now.json`, `walls.py`, `walls2.py`)을 만든 것이다. 이 감사는 그 폴더에 쓰지 않았다.
  - 규칙·`.sha256`·경로 2·탐침·코드 입력 파일은 이 줄에서 위반으로 나오지 않았다. 마지막 seal_check와 HEAD·status 재확인으로도 바뀌지 않았음을 확인했다.
- 사용한 스킬: 없음

---

## 메인 세션 덧붙임 (2026-11-10)

- P-3: 사용자 결정(개정 종료 기준 = 등급 영향 없으면 rev7 없음)에 따라 실행 전 기록 `d8x_prerun_record.md` 2절과 판정서 "규칙과 다른 실행" 절로 처리한다.
- C-1: 실행 전 기록 3절에 "오류 행: 경로 1 not_judgeable ↔ 경로 2 fail = 알려진 차이 → B-ID"로 적었다.
- P-1·P-2·C-2: 러너 생성기에 `MKL_THREADING_LAYER=TBB`, g0-rev3 `-B`, HEAD 고정 단계 5개(`check_head.py`, ba6671c4… + clean)를 넣어 러너를 다시 만들었다. `check_head.py`는 지금 ok. `d8x_expect_k1.json` sha256 055e1a50…ebd. 재감사를 받는다.
