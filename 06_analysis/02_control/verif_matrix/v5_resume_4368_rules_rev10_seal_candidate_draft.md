# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev10 (R9-4 LS 판별의 입력 경계: 전체 묶음 이름·manifest 행 수·manifest 파일, 결과 전, 봉인 후보 초안)

- **상태: 봉인 후보 초안(봉인 전).** 봉인 전에는 실행·판정에 쓰지 않는다. 봉인 때 바꿀 머리 줄은 끝 절에 원문으로 적었다.
- 원판 `v5_resume_4368_rules.md`(sha256 `9019b405…`), rev1(`d9094fda…`), rev2(`497e4614…`), rev3(`dad8dfa6…`), rev4(`7ea87a30…`), rev5(`452a8436…`), rev6(`809e5639…`), rev7(`e81f7d31…`), rev8(`3ecafaaf…`), rev9(`4cf7843c…`)는 고치지 않는다. 이 판은 rev9(sha256 `4cf7843ce469df511d7b99c7236f0b245afae9fb4ba5ad903e1c2da823a59a6d`, 봉인 커밋 `e5a2c19`) 위에 쌓인다. 전체 sha256은 각 판의 `.sha256`에 있다. 봉인 뒤 이 판과 앞 판이 다르면 이 판이 맞다. 이 판이 말하지 않는 것은 앞 판 그대로다.
- **시점: 436.8 본 실행 결과가 없을 때(봉인 SEAL_TIME, 봉인 커밋 SEAL_COMMIT).** 436.8 본 묶음과 0단계 T-3K는 한 줄·한 행도 돌지 않았다. 있는 것은 G-S 실행뿐이다(R10-0).
- 작성: control-expert, 2026-11-13. 기준 master `e5a2c19`(rev9 봉인 커밋). 계기는 하나다.
  - 최종 Y 후보 `d37cc60` 점검에서 rev9 R9-4(LS 판별)의 입력 경계를 두 경로가 다르게 읽는 경우가 나왔다. 사용자 결정 16(2026-11-13)은 결과 전에 rev10 문장으로 확정하는 것이다(권고 "판정서에 공개"와 다름)
  - 지금 manifest에는 C-5 35행이 모두 있고, LS 판별이 멈춤 사유(H-7 / L-e)를 고르는 곳은 늦은 대체 다리가 있는 C-5 행뿐이라, 현재 데이터로는 두 경로 결과가 달라지지 않는다(메인 세션 전달)
- **봉인 준비판이다.** 사용자 결정이 필요한 새 항목은 없다(R10-9 결정 표). 사용자 결정 16(2026-11-13)은 R10-1~R10-3에 반영했다. 이 줄은 봉인 때 바뀐다.
- **바꾸지 않는 것**: 숫자 문턱, 등급과 우선순위, 멈춤 조건의 뜻, 묶음 범위와 행 목록, 사전 예측 값, 두 경로 요건(원판 9.2), rev1~rev9의 정의(R10-1~R10-3이 보충·고쳐 쓰는 R9-4·R9-8 문장만 예외). 이 판은 새 숫자를 쓰지 않는다.

## R10-0. 결과 전 근거와 공개

- 2026-11-13 확인: 436.8 본 출력이 없다. G-S는 기록 전용 출력만 있다(rev8 R8-4, rev9 R9-8).
- 읽은 것:
  - 규칙: 원판~rev9(특히 원판 4.3 Chrono 출력 이름, 8.2 S-11, 9.3, 11.2, rev7 R7-4, rev9 R9-4·R9-8)
  - 기록 사실(이름과 값 꼴만, 판정 값 아님): 저장 G-S `07_results/S9/batch_V5-RESUME-K1-GS_20261113_082117/batch.json`의 최상위 `batch` 키(값 `V5-RESUME-K1-GS`)와 `cases` 키, `04_scripts/02_chrono/s9_batch.py`의 `batch.json` 쓰기(`"batch": name`)와 폴더 이름 꼴(`07_results/S9/batch_<name>_<YYYYmmdd_HHMMSS>`), `v5_resume_4368/chrono_rows_manifest.json`의 `batches` 키 10개(`V5-RESUME-K1-C1` … `V5-RESUME-K1-GS`)
  - 메인 세션이 전한 사실: `d37cc60` 점검의 두 경로 읽기(이 판 R10-1 표의 "지금" 칸)
  - 두 경로의 코드는 열지 않았다.
- 이 작성자는 경로 2 작성자가 아니다(rev2 R2-0).

## R10-1. R9-4 LS 판별의 입력 경계 (rev9 R9-4 보충, 사용자 결정 16)

### R10-1a. 전체 묶음 이름

- **용어**: 이 판의 대조 기준은 **전체 묶음 이름**이다. `V5-RESUME-K1-` 접두어를 포함한 이름(예: `V5-RESUME-K1-C5`, `V5-RESUME-K1-GS`)이고, 다음 셋이 같은 문자열이다.
  - S9 배치 폴더 `batch.json`의 최상위 `batch` 값
  - 폴더 이름에서 `batch_` 뒤, `_<YYYYmmdd_HHMMSS>` 앞의 부분
  - manifest `batches`의 키(10개, `V5-RESUME-K1-C1` … `V5-RESUME-K1-GS`)
- 원판 4.3의 **짧은 묶음 ID**(`C1`, `C2`, `C3`, `C4`, `C5`, `C6C7`, `OC5PROBE`, `OC5`, `JP`; 폴더 이름 꼴 `batch_V5-RESUME-K1-<묶음 ID>_<stamp>`의 `<묶음 ID>`)와 다르다. 짧은 묶음 ID 목록에 G-S(`GS`)는 없다. 이 판은 짧은 묶음 ID를 대조에 쓰지 않는다.
- **정의**: 행의 전체 묶음 이름은 그 행을 돌린 S9 배치 폴더 `batch.json`의 최상위 `batch` 값이다. 폴더 이름의 해당 부분은 대조에 쓴다.
  - `batch` 키가 있고 폴더 이름의 해당 부분과 같으면 그 값이다.
  - `batch` 키가 없으면 폴더 이름의 해당 부분을 쓴다.
  - `batch` 키가 있는데 폴더 이름의 해당 부분과 다르거나, 둘 다 정할 수 없으면(키 없음 + 폴더 이름이 `batch_<이름>_<YYYYmmdd_HHMMSS>` 꼴이 아님) **묶음 이름 불명**이다.
  - 정한 이름이 manifest `batches`의 키가 아니어도 묶음 이름 불명이다.
- 근거: 원판 4.3(Chrono 출력 폴더 꼴)과 `04_scripts/02_chrono/s9_batch.py`(`status = {"batch": name, …}`로 `batch.json`에 쓰고, 폴더를 `batch_{name}_{stamp}`로 만든다). 같은 `name`이 두 곳에 들어가므로, 기록 키를 먼저 쓰고 폴더 이름으로 대조하면 두 출처가 어긋나는 경우를 놓치지 않는다. 감사에서 G-S 배치 4건으로 `batch` 값 = 폴더 이름의 해당 부분임을 확인했다(메인 세션 전달).

### R10-1b. 경우별 처리 (LS 판별 한 행마다)

| 경우 | 지금 경로 1 / 경로 2 | 처리 |
|---|---|---|
| 묶음 이름 불명(R10-1a) | 판정 불가 / (manifest 쪽 없음으로 보고) `batch.json`에도 값이 없으면 LS 아님 | **LS 판별 `판정 불가`** |
| manifest `batches.<전체 묶음 이름>.rows[]`에 같은 `case` 행이 0개 | 판정 불가 / `batch.json`에도 값이 없으면 LS 아님 | **LS 판별 `판정 불가`** |
| 같은 `case` 행이 2개 이상 | 판정 불가 / 같음 | **LS 판별 `판정 불가`** |
| `batch.json` `cases[]`에 같은 `case` 항목이 0개 또는 2개 이상 | (점검에 나오지 않음) | **LS 판별 `판정 불가`**(같은 규칙을 대칭으로 쓴다) |
| manifest 파일이 없거나 JSON으로 읽히지 않거나 `batches` 키가 없음 | 판정 불가로 두고 계속 / 입력 오류로 종료 2 | **입력 오류**: 그 판정 도구는 입력 오류로 끝나고(공통 종료 코드 2), 그 Chrono 묶음은 판정하지 않고 멈춘다(원판 8.2 S-11). G-S에서는 G-S 실패다 |
| 두 출처 모두 행이 정확히 1개 있고, 두 행의 `v5_setting`이 모두 없거나 None | LS 아님 / LS 아님 | **LS 아님**(rev9 R9-4 그대로) |

- "manifest에 행 없음"과 "값 없음"의 구분: **행 없음**은 manifest `batches.<전체 묶음 이름>.rows[]`에 그 `case`를 가진 항목이 하나도 없는 것이다(출처 자체가 없음). **값 없음**은 그 `case` 항목이 정확히 하나 있고 그 항목의 `v5_setting` 키가 없거나 값이 None인 것이다(출처는 있고 v5 설정이 없음). R9-4의 "두 값이 모두 없거나 None이면 LS 아님"은 두 출처 모두에서 **값 없음**인 경우에만 쓴다.
- `판정 불가`가 된 행의 처리는 rev9 R9-4 그대로다: 그 행에서 실제 대체 다리 $n_{late}$ > 0이 나오면 H-7·L-e 어느 쪽이든 멈춤이므로 멈추고, 판정서에 "LS 판별 불가"와 그 경우(위 표의 행)를 적는다. 늦은 대체 다리가 없는 행은 LS 판별이 결과를 바꾸지 않으므로 기록만 한다.
- 근거:
  - 행 없음·여럿·묶음 불명: R9-4는 LS 판별을 **두 출처가 같을 때**만 정했다. 한 출처를 정할 수 없으면 "한 값만 있거나 둘이 다르면 판정 불가"와 같은 처지이고, 원판 9.3(판정에 쓰는 키가 없으면 판정 불가)에 해당한다. 출처가 없는 것을 "v5 설정이 없다"로 읽으면 결측을 값으로 바꾸게 된다.
  - manifest 파일 없음: manifest는 rev7 R7-4가 내용(`table_sha256`)과 작업본 sha256까지 적은 판정 입력이다. 원판 11.2의 G-S는 판정 도구가 읽는 입력이 실제로 있음을 확인하는 단계이므로, 그 입력 자체가 없는 것은 한 행의 결측이 아니라 도구·입력 결함(S-11)이다. 행마다 판정 불가로 두고 계속하면 같은 결함이 묶음 전체에 퍼진다.
  - 원판 8.2 S-11 문장은 "러너 로그 `errors` ≠ 0, 자리표시 남음, G-S 실패"다. 본 실행에서 manifest가 없을 때 S-11을 쓰는 것은 이 판이 S-11의 범위를 "판정 입력 파일 없음"까지 넓히는 것이다(멈춤의 뜻 — 그 묶음의 실행·판정을 멈추고 묻는다 — 은 같다).
- 결정 필요: **아니오**(원판 9.3·11.2·8.2 S-11과 R9-4 문장의 적용).

## R10-2. 이 판의 G-S 확인 항목 (원판 11.2 보충)

- G-S에서 Chrono 행마다 R10-1a의 전체 묶음 이름이 정해지고, manifest와 `batch.json` `cases[]`에 같은 `case`가 정확히 하나씩 있는지 확인한다. 하나라도 어긋나면 G-S 실패(S-11)로 센다.
- G-S 결과로 적을 것: rev9 R9-8의 항목에 더해 R10-1b 경우별 행 수(묶음 이름 불명, manifest 행 0개·여럿, `batch.json` 항목 0개·여럿, 두 출처 값 없음)와 rev10 봉인 확인 결과.
- 결정 필요: **아니오**(원판 11.2의 키 있음 확인을 이 판의 입력에 적용).

## R10-3. 수정 순서와 `git_at_start` (rev9 R9-8 고쳐 씀)

- **순서**:
  1. 이 판을 봉인한다.
  2. 최종 Y에 두 경로의 수정을 더한다. rev9 R9-8의 Y 구성은 그대로이고, 다음을 더한다.
     - 경로 1·2 모두: R10-1·R10-2의 읽기.
     - 봉인 확인 목록(`chrono_rows_judge_4368.py` `RULES_SEALS`, `judge4368_common.py`, `resume4368_judge` 봉인 목록, 경로 2 도구의 봉인 목록)에 rev10 파일과 그 봉인 sha를 더한다. 도구는 파일 sha256이 봉인 sha와 `.sha256` 기록 둘 다와 같은지 보고, 다르거나 없으면 원판 8.2 S-1이다.
     - 경로 2 작성자가 경로 2를 고치고, 원판 9.2의 독립성 요건은 그대로다. 두 경로는 이 판의 문장만 공통으로 쓴다.
  3. 최종 Y에서 G-S 전체를 다시 돈다.
- **최종 Y에서 이 판 봉인 뒤 G-S 전체를 다시 돌린 것을 원판 11.2 충족으로 본다.** `git_at_start`는 최종 Y이거나, 그 위에 판정서·감사 기록만 더한 커밋이다(rev8 R8-4의 확인 방법 그대로). 최종 Y보다 앞선 커밋(`d37cc60` 포함)에서 돈 G-S는 기록만 한다.
- 결정 필요: **아니오**(메인 세션 지시의 순서).

## R10-9. 결정 표

| 항목 | 권고·정의 | 결정 필요 |
|---|---|---|
| R10-1a 전체 묶음 이름 | 대조 기준 = `V5-RESUME-K1-` 접두어 포함 전체 이름(`batch.json` `batch` 값 = 폴더 이름의 `batch_`~`_<stamp>` 사이 = manifest `batches` 키), 원판 4.3 짧은 묶음 ID와 다름. `batch` 값을 쓰고 폴더 이름으로 대조, 키 없음 = 폴더 이름, 다름·정할 수 없음·manifest에 없는 이름 = 묶음 이름 불명 | 아니오 |
| R10-1b 경우별 처리 | 묶음 이름 불명·manifest 행 0개/여럿·`batch.json` 항목 0개/여럿 = LS 판별 판정 불가, manifest 파일 없음 = 입력 오류(종료 2, S-11, 묶음 판정 안 함), 두 출처 모두 행 1개 + 값 없음 = LS 아님 | 결정됨: 사용자 결정 16(2026-11-13) |
| R10-2 G-S 확인 | 전체 묶음 이름과 두 출처의 `case` 1개씩을 G-S에서 확인 | 아니오 |
| R10-3 순서 | rev10 봉인 → 최종 Y에 두 경로 수정 + rev10 봉인 확인 → 최종 Y에서 G-S 전체, `git_at_start` = 최종 Y(+ 판정서·감사 기록만) | 아니오 |

### 결과 전 사용자 결정 기록

| 날짜 | # | 결정 | 반영 |
|---|---|---|---|
| 2026-11-13 | 16 | R9-4 LS 판별의 입력 경계(묶음 이름 불명, manifest 행 없음·여럿, manifest 파일 없음)를 두 경로가 다르게 읽는 것을 rev10 문장으로 확정한다(권고 "판정서에 공개"와 다름) | R10-1~R10-3 |

## 봉인 때 바꿀 머리 줄 (메인 세션)

1. 파일 이름: `v5_resume_4368_rules_rev10_seal_candidate_draft.md` → `v5_resume_4368_rules_rev10.md`(같은 폴더). 초안 파일은 지우지 않고 그대로 둔다.
2. 1행을 다음으로 바꾼다:
   `# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev10 (R9-4 LS 판별의 입력 경계: 전체 묶음 이름·manifest 행 수·manifest 파일, 결과 전, 봉인)`
3. 3행(첫 글머리 "상태")을 다음으로 바꾼다:
   `- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev10.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev10_seal_candidate_draft.md`와 1·3·5·9행만 다르다.`
4. 5행("시점")에서 `SEAL_TIME`(예: 2026-11-13 10:00:00 +09:00)과 `SEAL_COMMIT`(봉인 파일을 넣는 커밋의 앞 커밋, 7자리)을 값으로 바꾼다. 이 두 이름 말고는 5행을 바꾸지 않는다.
5. 9행("봉인 준비판이다")을 다음으로 바꾼다:
   `- **봉인본이다.** 사용자 결정이 필요한 새 항목은 없었고, 사용자 결정 16(2026-11-13)은 R10-1~R10-3과 R10-9 결정 표에 반영했다.`
6. 바꾼 뒤 sha256을 계산해 `v5_resume_4368_rules_rev10.sha256`에 `<sha256>  v5_resume_4368_rules_rev10.md  sealed <SEAL_TIME 값> (436.8 rev10: R9-4 LS classification input boundaries on top of rev9; full batch name with the V5-RESUME-K1- prefix (batch.json batch value = folder name part between batch_ and _<stamp> = manifest batches key, not the short batch ID of the original 4.3) from the batch key checked against the folder name (no key = folder name; mismatch, undeterminable or not a manifest batch = unknown); unknown batch name, zero or several manifest rows or batch.json cases[] entries for the case = LS classification not judgeable; missing or unreadable manifest = input error (exit 2), bundle not judged (S-11); value absent or None in exactly one row of both sources = not LS; G-S checks one row per source; order rev10 seal -> both path fixes and rev10 seal check in the final Y -> full G-S at the final Y = 11.2; user decision 16 2026-11-13; thresholds and grades unchanged)` 한 줄로 쓴다.
7. `.gitattributes`에 다음을 더한다:
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev10.md -text`
   - `…/v5_resume_4368_rules_rev10.sha256 -text`
   - `…/v5_resume_4368_rules_rev10_seal_candidate_draft.md -text`
8. `tools/verif/seal_check.py`와 `tools/verif/placeholder_scan.py`(봉인본에 `SEAL_TIME`·`SEAL_COMMIT`이 남지 않음)로 확인한 뒤 커밋한다. 봉인 뒤 이 문서를 고치지 않는다. 고칠 것이 생기면 `v5_resume_4368_rules_rev11.md`로 새로 봉인한다.
