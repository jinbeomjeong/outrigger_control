<!-- verif-protocol-auditor 리포트 원문(2026-11-10). 대상: D8x rev6 봉인 점검. 브랜치 worktree-agent-a9a55327c173a8e3e, 커밋 3c086ae. 메인 세션이 편집 없이 저장. 결정은 맨 끝 "메인 세션 덧붙임" 절에만 쓴다. -->

# D8x rev6 봉인 점검 감사 (verif-protocol-auditor, 2026-11-10)

## 감사 요약
- **시점과 축**: 개정판 봉인 점검이다(R-a·R-c 결과 전). 세 표준 시점에 들지 않아 `실행 전` 비중으로 봤다. 중심 축은 S·T·R·E이고, I는 E-6d 키와 행 정체성만 봤다.
- **대상**: 브랜치 `worktree-agent-a9a55327c173a8e3e` HEAD `3c086ae`(부모 `22521ec`, 2026-11-10T12:30:47+09:00). 이 커밋은 `d8x_rules_rev6.md`와 `.sha256` 두 파일만 더한다. 감사 시작과 끝에 HEAD는 그대로였고 status도 깨끗했다.
- **기준 문서**(raw sha256 앞 8자리): 원판 a377b9bb, rev1 ad16f452, rev2 5f3fa620, rev3 2318fb5c, rev4 5233c517, rev5 63437019, **rev6 d584c8da**(`.sha256` 파일 자체 sha 9fb95843).
  - 7판 모두 `.sha256` 첫 토큰과 raw로 일치한다. i/lf·w/lf, `-text`(check-attr `unset`), CRLF 0, BOM 없음이다.
  - 앞 점검 원문 `d8x_rev5_seal_audit.md`는 abd2f6d0이다(rev6:11 인용과 일치).
- **판정: 차단 0 / 실행 전 수정 3 / 기록 5. 등급에 영향이 있어 개정판(rev7)이 필요한 항목은 0건이다.**
  - rev5 점검의 B-1, B-2(규칙 쪽 문구), B-3 경계, B-3a·B-4(구현 전제), C-2, B-5·B-6은 모두 내용상 맞게 닫혔다.
  - 남은 실행 전 수정 셋은 모두 구현이나 실행 전 기록으로 닫을 수 있다(R-1·R-2·R-3). R-1·R-2는 python-expert 구현, R-3은 실행 전 기록에서 대상 파일을 정하면 된다.
  - 셋 모두 고치지 않으면 엄격한 쪽(판정 불가)으로 간다. 조용한 통과를 만드는 길은 없다.
  - 사용자 결정(개정 종료 기준)에 따르면 **rev7 없이 판정서·실행 전 기록으로 닫을 수 있다.**

## 닫힘 확인 (rev5 점검 항목별)

| 항목 | rev6 처리 | 판단 |
|---|---|---|
| B-1 비교 기준 | rev6:40-56. G1·V-2 = 경로 1 ↔ (경로 2 + 손 적용). 행 단위 대조 둘(켬 팔 verdict, 켬 팔 LAS 수). 끔 팔은 도구끼리 비교. 키 대응표. "손 적용 뒤에도 남는 차이만 불일치, 결과 뒤 경로 2 수정 금지" | 닫힘. 키 대응표(rev6:53-54)는 경로 2 코드와 맞다: R-a `(bundle, point, level)`은 `d8x_recount.py:1314`, R-c `r["floor"]`=`slope_name`은 `:812`·`:819`·`:1288`. 경로 1 `ra\|point\|level`·`rc\|slope_name\|level`은 b311169 `_las_activity`와 맞다. 남은 공백은 행 결합 키와 verdict 표기(R-1·R-2) |
| B-2 범위 차이 문구 | rev6:83-85. 경로 2는 원판~rev2만 보고, rev3~rev6은 판정서가 손으로 확인한다 | 닫힘. 경로 2 `RULES_SHA256`은 `:62-66`이고 항목 3개(원판·rev1·rev2)다. 인용 행 "62~65"는 사소한 차이다(C-5) |
| B-3 경계 5경우 | rev6:58-71, (i)~(v) | 닫힘. 경로 2는 `d8x.events` 결측 행을 unjudgeable로 둔다(`:713-715`, `:855-857`). 경로 1도 결측 행을 NotJudgeable로 둔다(b311169 `REQUIRED_D8X_KEYS`에 `events`). 그래서 (iii) "pass인데 사건 목록 없음"은 두 도구 모두에서 생기지 않는 방어 조항이고, 도구와 모순이 없다. 경우가 겹치는 곳은 C-4 |
| B-3a 다섯 키 | rev6:75-78. 구현 전제, 구현이 없으면 rev5 5절 글자대로 판정 불가 | 닫힘(규칙 쪽). "행 판정 불가 + 종료 2"는 경로 1 `EXIT_NOT_JUDGEABLE = 2`(b311169 `:48`)와 맞아 모순이 없다. 구현 확인은 실행 전 감사에서 한다 |
| B-4 경로 1 출력 | rev6:79. judge-ra/rc 출력과 report 둘 다 보고, `[]` 기본값 제거를 전제한다 | 닫힘(규칙 쪽). b311169 `:1174-1175`에는 아직 기본값 `[]`가 있다(python-expert가 고치는 중). 실행 전 감사 대상 |
| C-2 정정 | rev6:87-91 | 닫힘. 8c9e8b1 12:09:18 병합과 4e8eb9b 12:06:52를 git log로 확인했다 |
| B-5·B-6 공개 | rev6:16-38 | 닫힘. 표의 sha 5개, `SHA256SUMS.txt` 0e239c7a, `SHA256SUMS_add.txt` 35889499가 보존본 실측과 같다. `SHA256SUMS_add.txt` 본문의 다섯 줄도 표와 같다. d8xfix 원본과 바이트가 같고, 원본 mtime도 표와 같다(g0 12:15:48·12:15:51). G0 탐침 meta 주장(`rules_rev` rev3, `run_commit` b311169, `clean` true, reuse 0 / recompute 60, `rules_seals` 원판~rev4)과 judge `gate_G0`=`pass`를 파일에서 확인했다. 보존본 복사 시각 12:28:53은 rev6 봉인보다 앞이다 |

## 발견 사항 (심각도순)

### [실행 전 수정][R·I] R-1. rev6 1-1 "켬 팔 행별 verdict를 키로 이어 대조"의 **행 결합 키**가 정해지지 않았다. R-c는 두 경로의 행 키 형식이 다르다 — 등급 영향 없음(실행 전 기록으로 처리)
- **근거**
  - rev6:46 "경로 1 켬 팔 행 ↔ 경로 2 `report[...]["on"]["rows"][*]["verdict"]`를 키로 이어 모두 같아야 한다". 키 대응표(rev6:51-54)는 V-2 집계 키 (묶음, 점, 단계)뿐이고 행 키는 없다.
  - 경로 1 R-c 행 키(b311169 `_rc_key`, 약 `:681-684`): `f"{job.d1.key}|{setting}|e{eps:g}"`. 예: `D1|H-R-X|rigid|T|fdown3.7|K1|VB|e0` 꼴이고, 끝 `K1`은 크롤러 강성 토큰이다(rev5:51).
  - 경로 2 R-c 행 키(`d8x_recount.py:818`): `f"{slope_name}|{level}|x{crawler_k_scale:g}|{setting}|e{eps:g}"`.
  - R-a는 두 경로 모두 `id`를 가진다(경로 1 `id_key = "id"`, 경로 2 행 `"id": run.get("id")` `:664`). 결합은 된다(단 R-2).
- **실패 시나리오**: 판정자가 행 키를 결과를 본 뒤에 정하거나 문자열 그대로 이으면, R-c 켬 팔 96행이 모두 "짝 없음"이 된다. 원판 8 `:348` 불일치로 G3가 판정 불가(B-ID)가 된다. 엄격한 쪽이지만 틀린 등급이다.
- **권장 조치**: 실행 전 기록에 행 결합 규칙을 적는다(메인 세션 또는 control-expert). 예: "R-a = `id` + 팔, R-c = 원 jsonl 줄의 (`job.d1.slope_name`, `job.d1.level`, `job.d1.crawler_k_scale`, `job.setting`, `job.eps`) + 팔". 원판 8의 끔 팔 행별 대조에도 같은 규칙을 쓴다. 기준을 바꾸는 것이 아니라 비교 절차를 정하는 일이므로 rev7은 필요 없다.

### [실행 전 수정][E·I] R-2. 경로 1은 judge-ra/rc 출력의 `rows`에 두 팔을 합친다. 그런데 오류·판정 불가 행에는 팔 표시(`k1`)가 없고, R-a `id`에도 팔 토큰이 없다. 이 상태로는 켬 팔 행만 골라내기가 출력 순서에 기대게 된다 — 등급 영향 없음(구현으로 처리)
- **근거**
  - b311169 `_bundle_result`: `"rows": [r for part in parts.values() for r in part["rows"]]`(두 팔 합침).
  - 정상 행에는 `"k1": k1`이 있다(`:627`, `:714`). 반면 `:610`·`:624`(R-a 오류·NotJudgeable)와 `:690`·`:710`(R-c)의 반환은 `{"id"|"key", "verdict": "not_judgeable", "reason"}`뿐이다.
  - 탐침 `ra_probe_off.json`의 id는 `main|C2_tv0.1|top|rigid|pitch+`다(팔 토큰 없음). V-1이 같은 키로 짝을 짓는 구조라 켬 팔 id도 같을 가능성이 크다. `[추정]`: 켬 팔 id는 직접 보지 못했다.
  - 경로 2는 모든 행에 `"k1"`이 있다(`:664`, `:808`).
- **실패 시나리오**: 켬 팔 행 하나가 드라이버 오류로 `not_judgeable`이면, 경로 1 출력에서 그 행이 어느 팔인지 필드로 가를 수 없다. 대조가 어긋나면 불일치 → 판정 불가다. id 중복으로 끔 팔 행과 잘못 이으면 그 행의 대조가 틀린다. 통과 쪽으로 가는 길은 없다. 켬 팔 요약 `gate_rows_on`이 따로 있어 G1 자체는 막힌다.
- **권장 조치**(python-expert, 통합 브랜치): 오류·NotJudgeable 반환에도 `k1`을 넣거나, `rows_off`·`rows_on`으로 나눠 낸다. 시험: 켬 팔 오류 행이 출력에서 `k1 == "on"`으로 보이는지 확인한다.

### [실행 전 수정][R·S] R-3. rev6 4 "정식 G0 rev3·R-a·R-c·Chrono **실행 기록**의 규칙 봉인 목록도 rev6까지 담아야 한다. 담지 않으면 G-S에서 판정 불가"가 가리키는 파일이 묶음마다 정해지지 않았다. R-a 결과 파일의 `meta.rules`는 탐침에서 `null`이다 — 등급 영향: 실행 전 기록에서 대상 파일을 정하면 없음
- **근거**
  - rev6:84.
  - 실제로 봉인 목록을 쓰는 곳은 넷이다.
    - 경로 1 prelaunch 기록 `"rules": spec.seal_report()`(b311169 `cmd_prelaunch`, `:392`)
    - G0 `meta.rules_seals`(`run_d8x_g0_rev3.py:57`·`:148`)
    - Chrono `d8x_rules_meta()`(`run_S6C.py:1798`, `run_S8C.py:1020`)
    - 점 파일 `rules`(`d8x_spec.py:321`, `POINT_FILE_RULES` 부분집합)
  - 탐침 `ra_probe_off.json`의 `meta.rules`는 `null`이다. R-c jsonl 줄에 봉인 필드를 쓰는 코드는 찾지 못했다(Grep `seal_report|rules_seals|d8x_rules_meta`).
- **실패 시나리오**: "실행 기록"을 R-a·R-c 결과 파일로 글자대로 읽으면 두 묶음 모두 G-S 판정 불가가 된다. 반대로 대상을 정하지 않은 채 결과 뒤에 고르면 사후 해석이 된다.
- **권장 조치**: 실행 전 기록에 묶음별로 적는다. 예: "R-a·R-c = `d8x_prelaunch_<ra|rc>.json`의 `rules`, G0 = `meta.rules_seals`, Chrono = result.json `d8x` 블록의 `d8x_rules_meta`". 원판 G-S의 실패 처리는 "실행하지 않음"(`d8x_rules.md:275`)이고, rev6 4는 실행 뒤 발견을 "판정 불가"로 둔다. 둘이 모순되지 않는다는 것(실행 전 미충족 = 미실행, 실행 뒤 발견 = 판정 불가)도 함께 적는다. 구현으로 R-a·R-c 결과 meta에 `seal_report()`를 넣어 엄격한 읽기까지 만족시키는 방법도 있다(python-expert, 선택).

### [기록][R] C-4. rev6 2의 (i)~(v)가 서로 겹친다 — 등급 영향 없음(판정서 기록)
- 경로 2에서 `d8x.events`가 결측인 행은 `record.las_events = 0`이 있고(`:713-721`) verdict는 unjudgeable이다. 그래서 (i) "값이 있으면 쓴다"와 (v) "fail·불가 행은 기록만"에 동시에 해당한다.
- 드라이버 오류 행(`record: {}`)은 (ii) "필드 없음 → 손으로 센다"와 (iv)에 동시에 해당한다.
- 어느 쪽으로 읽어도 G1이 먼저 막으므로(rev5 3.1-1) 등급은 같다. 판정서에서 "(iv)·(v)가 (i)·(ii)보다 먼저"라고 적으면 된다.
- 같은 절의 "R-c 줄의 `d1` 사건 이름 목록"(rev6:65)은 두 경로가 실제로 읽는 `d1.d8x.events`로 적는 편이 정확하다(R-a는 `run.d8x.events`).

### [기록][R] C-5. 문구 정밀도 — 등급 영향 없음(판정서 기록)
- **verdict 표기**: 경로 1은 `"not_judgeable"`(b311169 `:610` 등), 경로 2는 `"unjudgeable"`(`:323`)이다. rev6 1-1의 "(`pass`/`fail`/불가)"는 개념으로는 맞다. 판정서 키 대응표에 표기 대응 한 줄을 더한다.
- **경로 2 V-2 키 표기**: rev6:53 `["R-a", <point>, <level>, n]`은 경로 2 `LAS_DEPENDENT` 출력 형식(`:1316`)이다. 켬 팔 손 집계는 행의 `point`·`level`(R-c는 `floor`)로 묶는다. 뜻은 같다.
- **인용 행 번호**: rev6:83 "62~65행"의 실제 dict는 `:62-66`이고 항목은 `:63-65`다(rev4는 "61~65"). 내용(원판·rev1·rev2만)은 맞다.

### [기록][R·T] C-6. rev6 머리말 "바뀐 것"(rev6:13)은 4절을 "판정서 범위 차이 문구"로만 적었다. 4절에는 엄격한 새 조건("rev6까지 담지 않은 실행 기록 → 판정 불가")도 들어 있다 — 등급 영향 없음
- 결과 전이고 엄격한 쪽이라 허용된다. rev5 C-2와 같은 종류다. 판정서 "개정 이력" 절에 한 줄로 적는다.

### [기록][T] C-7. rev6 공개 "본 것"(rev6:20)에 통합 브랜치 `dc416d8`(12:29:26, "Merge … D8x rules rev5 sealed")이 없다. rev6 봉인(12:30:47)보다 앞선 커밋이다 — 등급 영향 없음
- 내용은 규칙 브랜치 병합이고 결과를 만들지 않는다. 작성자가 봤는지는 확인하지 못했다(`[추정]`). 판정서 시간 순서 절에 통합 브랜치 커밋 목록으로 적으면 된다.
- 탐색 결과: rev5 점검 뒤(12:15) `%TEMP%\claude`에서 d8x 관련 새 파일은 공개된 G0 탐침 두 개(d8xfix 원본)뿐이다. 저장소 전체(main·worktree)에도 정식 산출물 이름(`d8x_g0_rev3*.json`, `ra_on*/ra_off*.json`, `hrx_*.jsonl`, `d8x_prelaunch*.json`, `d8x_expect_k1.json`, `d8x_selection.json`, `d8x_judgement*`)은 0건이다. rev6 "없는 것"(rev6:22)은 봉인 시점과 감사 시점 모두 참이다.

### [기록][S] C-8. rev5 점검 C-3(앞 점검 원문 커밋 보호)은 닫혔다 — 등급 영향 없음
- 감사 도중 master에 병합과 커밋이 들어왔다. `efc515b`(12:36:40)는 규칙 브랜치를 rev6까지 병합했고, `fbe9cab`(12:36:40)는 rev4·rev5 점검 원문을 커밋했다.
- main checkout `d8x_rev5_seal_audit.md`: `ls-files --eol` i/lf w/lf attr/-text, `check-attr text: unset`. 작업 파일 hash-object `3346b461…`은 HEAD blob과 같다. sha는 abd2f6d0으로 rev6:11 인용과 같다.
- master의 rev6·`.sha256`·rev5 blob은 worktree와 같다(`128da7bd…`, `fad7d887…`, `2c5b0292…`). main checkout의 rev6 두 파일도 i/lf w/lf -text다.

## 규칙↔도구 대조표 (rev6 변경분)

| 규칙 | rev6 | 경로 2(46010967) | 경로 1(b311169, 구현 중) | 결과 |
|---|---|---|---|---|
| G1 비교 기준 | 경로 1 ↔ 경로 2 + 손 적용(`:42-44`) | 끔 팔 status(`:1467-1474`), `k1_rows_fail` | 두 팔 `_status_of`, report `_gate_of` | 맞음 |
| 켬 팔 행별 verdict | 키로 이음(`:46`) | 행 `verdict`, `k1`, R-c 키 `:818` | 행 `verdict`(`not_judgeable`), R-c 키 `_rc_key`, 오류 행에 `k1` 없음 | 결합 키·표기 미정(R-1, R-2, C-5) |
| 켬 팔 LAS 수 | (묶음, 점, 단계)(`:47`) | 행 `record.las_events`(`:721`, `:863`) | `_las_activity` `counts_by_arm["on"]` | 맞음 |
| 결측 경계 | (i)~(v)(`:62-68`) | 결측 events → unjudgeable(`:713-715`, `:855-857`) | 결측 events → NotJudgeable | 맞음. 겹침은 C-4 |
| E-6d 다섯 키 | 각각 읽음, 없으면 판정 불가·종료 2(`:77`) | 보지 않음(rev3 3.3) | 둘만 봄(rev5 점검 B-3a) | 구현 전제. 실행 전 감사 대상 |
| report 결측 | 기본값 제거 전제(`:79`) | `k1_rows_fail` None | `.get(..., [])`(`:1174-1175`) | 구현 전제. 실행 전 감사 대상 |
| 봉인 손 확인 | rev3~rev6(`:83`) | `RULES_SHA256` 원판~rev2(`:62-66`) | `RULES_FILES` ~rev4, `LATEST_RULES_REV="rev4"` | 규칙은 맞음. 구현 rev5·rev6 추가는 실행 전 감사 대상 |
| 실행 기록 봉인 | rev6까지(`:84`) | — | prelaunch `rules`, G0 `meta.rules_seals`, Chrono `d8x_rules_meta`. R-a 결과 `meta.rules` null | 대상 파일 미정(R-3) |

## 확인 필요
1. (R-1, 메인 세션 또는 control-expert) 두 경로의 행 결합 키(R-a `id`+팔, R-c 원 줄 필드 5개+팔)와 verdict 표기 대응을 실행 전 기록에 적는 것으로 충분한지 정한다. 이 감사의 판단은 충분하다는 것이다. 등급 기준을 바꾸지 않으므로 rev7은 필요 없다.
2. (R-3, 메인 세션) rev6 4 "실행 기록"의 묶음별 대상 파일을 실행 전 기록에 정할지, 구현(R-a·R-c 결과 meta에 `seal_report()` 기록)으로 엄격한 읽기를 만족시킬지 정한다.

## 위임 필요
- **python-expert**(경로 1, 통합 브랜치 `worktree-agent-ac6cd65fc4ec57212`, 이미 진행 중인 B-2·B-3a·B-4에 더함)
  - R-2: judge-ra/rc의 오류·NotJudgeable 행 반환(b311169 `:610`, `:624`, `:690`, `:710`)에 `k1`을 넣거나 `rows_off`·`rows_on`으로 나눈다. 시험을 더한다.
  - R-3(선택): R-a·R-c 결과 meta에 규칙 봉인 목록(`seal_report()`, rev6까지)을 기록한다.
  - B-2 구현 때 `RULES_FILES`·`LATEST_RULES_REV`·`s6_stage2` 상수에 rev6 `d584c8dafcb1aea9f289a4ffaf9f27cbcc9aa9d22da504a764fb44f041624697`을 넣는다(rev6:84).
- **control-expert 또는 메인 세션**: R-1·R-3 실행 전 기록 문구, 판정서 C-4·C-5·C-6·C-7 기록.

## 메인 세션 권고
- D8x 실행 전 감사(통합 브랜치를 master에 병합한 뒤 $H_{impl}$ 지정)에서 볼 것
  - `RULES_FILES`에 rev5·rev6 포함
  - prelaunch C 행의 `k1_order_gate`
  - judge-chrono의 다섯 키 각각 읽기와 종료 2
  - report 기본값 `[]` 제거
  - 오류 행 `k1` 표시
  - 실행 전 기록의 행 결합 키와 실행 기록 봉인 대상 파일
- 이 감사는 실행하지 않았다. 건조 실행(prelaunch 등)도 하지 않았다.

## 검사하지 못한 것
- 통합 브랜치의 진행 중 편집(작업 트리, 줄 번호가 b311169와 달라짐). 구현 판단은 커밋 b311169 기준이고, 이번 점검 범위 밖이다.
- 경로 1의 켬 팔 R-a id 실제 형식(R-2 `[추정]` 부분). 끔 팔 탐침 한 건만 봤다.
- R-c harness jsonl에 `d1.events`처럼 `d1.d8x.events` 말고 다른 사건 목록이 있는지(C-4 문구). R-c 탐침 파일은 요약뿐이다.
- `gate_scan.py`, `timeline.py`는 돌리지 않았다. 관련 코드는 직접 읽었고, 시각은 git 커밋 시각과 파일 mtime으로 봤다.

## 실행한 검증
- 인터프리터: `C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B`(`MKL_THREADING_LAYER=TBB`, `-X utf8`). Python은 모두 PowerShell 도구로 실행했다. 프로젝트 모듈은 import하지 않았다.
- `depcheck.ps1` → STAMP(numpy 2.5.3, pyyaml 6.0.3, git OK).
- `source_guard.py snapshot`(12:32:55)과 `verify`(12:38:39), 입력 29개: worktree 규칙·`.sha256` 14개, 탐침 보존본 12개, 경로 2 사본, rev5 점검 원문, 규칙 브랜치 `.gitattributes`.
- `seal_check.py --repo <wt> "06_analysis/02_control/d8x/d8x_rules*.md" --quoted <rev6> --hash-files <보존 폴더 *> <rev5 점검 원문> <경로 2 사본>`
  - 7판 모두 raw 일치, `-text`, i/lf·w/lf, CRLF 0, BOM 없음.
  - 인용 16개 가운데 14개가 풀렸다. 못 푼 2개(`ac6cd65fc4ec57212`, rev6:30·:90)는 브랜치 이름이라 오탐이다.
- `Get-FileHash`: 보존본 12개, d8xfix 원본 5개. `SHA256SUMS_add.txt` 본문을 읽었다.
- scratchpad 스크립트(`keys.py`)와 한 줄 python: 탐침 R-a 키·`meta.rules`, G0 meta·`rules_seals`·`gate_G0`를 조회했다.
- git 조회: `log`(worktree, 통합 브랜치, master), `show --stat 3c086ae`, `show b311169:<d8x_judge.py|d8x_spec.py>`, `rev-parse master:<파일>`, `hash-object`, `ls-files --eol`, `check-attr`, `status`, `worktree list`.
- 파일 검색: `%TEMP%\claude`의 12:15 뒤 D8x 관련 이름, 저장소 전체의 정식 산출물 이름(0건), 통합 worktree의 봉인 기록 함수(Grep).
- 읽은 문서와 코드
  - rev6 전체, rev5 전체, rev4 전체, 원판 `:275-280`·`:325-354`, rev5 점검 원문 전체
  - 경로 2 `:55-69`, `:270-292`, `:655-729`, `:800-869`, `:1300-1324`와 Grep 결과
  - 경로 1 b311169 `:94-110`, `:150-200`, `:384-436`, `:636-700`, `:984-995`, `:1026-1053`, `:1150-1180`
  - 통합 worktree `d8x_spec.py:300-329`
- 만든 뒤 지운 것: scratchpad `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\6f3ebc4d-a5fb-4d9f-b214-d0ae5c515ee1\scratchpad\rev6_audit\`(guard.json, seal.md, keys.py)를 폴더째 지웠다. 남은 부산물은 없다.
- 메모리: `audit_pitfalls.md`에 일반 함정 한 줄을 더하고 `MEMORY.md` 색인을 갱신했다. 내용은 두 경로 행 단위 대조의 결합 키·verdict 표기·오류 행 팔 표시, "실행 기록 봉인" 대상 파일이다.
- 최종 판정 직전 확인: 대상 HEAD는 3c086ae 그대로이고 status는 깨끗하다. 입력 29개는 모두 해시·크기·mtime이 같다.
- 원본 불변: 위반 — 입력 폴더에 항목 추가 14건(d8x_rules.md, d8x_rules.sha256, d8x_rules_rev1.md 외 11건)
  - 설명: 입력 파일 29개는 해시·크기·mtime이 모두 같다. 추가 14건은 입력 폴더 가운데 main checkout `C:\workspace\outrigger_control\06_analysis\02_control\d8x\`에 생긴 원판~rev6 규칙과 `.sha256` 14개다.
  - 이 파일들의 mtime은 모두 12:36:40이다. 감사 도중(스냅숏 12:32:55 뒤) 다른 세션이 master에 커밋 `efc515b`(규칙 브랜치 병합)와 `fbe9cab`를 넣으면서 체크아웃된 것이다. 이 감사는 그 폴더에 쓰지 않았다.
  - 추가된 rev6 두 파일의 blob은 worktree와 같다(C-8).
- 사용한 스킬: 없음

---

## 메인 세션 덧붙임 (2026-11-10)

- 사용자 결정(개정 종료 기준, 12:3x)에 따라 rev7을 만들지 않는다(등급 영향 항목 0건). R-1·R-3은 D8x 실행 전 기록(prelaunch 기록과 판정서 머리)에서 정하고, R-2와 R-3의 엄격한 읽기(R-a·R-c 결과 meta에 `seal_report()`)는 python-expert 구현으로 닫는다. C-4~C-7은 판정서 기록 항목이다.
- "원본 불변 위반" 14건은 감사 도중 메인 세션이 규칙 브랜치를 master에 병합(efc515b)해 생긴 체크아웃이며, 감사가 쓴 것이 아니다.
