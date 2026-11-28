# 판 8 5단계 판정서 개정 1과 판 8 종료 판정서의 커밋 전 감사 (verif-protocol-auditor, 판정 후, 2026-11-28)

## 감사 요약
- 본 결과(값의 종류를 공개합니다)
  - `j9_runs\56849248\judge_7ea78232_s5\ho_k_selection.json`(ff4b1c53)
    - 최상위 키 구조를 봤습니다.
    - 판정서 1.1~1.3 표의 값은 스크립트 안에서 출력 값과 같은지만 비교했고, 화면에는 OK/BAD만 냈습니다.
    - 슬롯별 `slot_layers`·`aa_pairs`는 (원천 묶음, 층)별 건수(n, state, aa_fail 참 개수)로만 셌습니다. 이 건수는 판정서 2.2 표에 이미 있는 값입니다. 슬롯 이름과 슬롯별 값은 내지 않았습니다.
  - 키 파일 `heldout_g_ed8.json`: 줄 수, 이름 수, 원천별 수, 겹침 조합, 줄 순서만 셌습니다.
  - `run_console.log` 4줄 전문을 Read했습니다(시각, stdout `status` stop, 종료 1).
  - 5단계 jsonl 3개와 `logs\*`(.log·.err 포함)는 바이트 해시로만 대조했습니다(`ho_v0_prerun.SHA256SUMS` 27항목). 내용은 열지 않았습니다.
  - 원인 분석 근거 csv·json은 열지 않았습니다. 예외는 `provenance.json`으로, 입력 sha·import 줄을 Grep했습니다. scripts의 import 줄도 Grep했습니다.
  - 판정 도구 `jp3_ed8_rules.py` 419-443·456-513·536-591행을 읽었습니다(ed8-judge4).
  - transcript에서는 11:45 KST 이후 도구 호출의 **입력**만 파싱했습니다. 도구 결과는 읽지 않았습니다.
  - P8-2 경로 2 자료는 열지 않았습니다.
- 대상과 시점: 판정 후, 커밋 직전
  - 5단계 판정서 개정 1 `stage5_judgement_ed8.md`(f5cda2e3, 406줄)
  - 판 8 종료 판정서 `ed8_closing_judgement.md`(6376a9f3)
  - 결정문 `decision_stage5_20261128.md`(7d236aa2)
- 기준 문서
  - 봉인 규칙 `jp3_remedy_spec_v8_rules.md`(35f9eba8, `.sha256` e19aaa48 첫 토큰과 같음, seal_check 종료 0). 개정판은 없습니다.
  - 판정 커밋 T8⁗ 7ea78232(ed8-judge4: locked, HEAD 일치, `status --porcelain --ignored` 0줄)
  - 실행 커밋 C8 56849248
- 판정: **차단 0 / 커밋 전 수정 6 / 기록 8**
  - 두 판정서의 판정 내용은 결정문 1·2번과 맞습니다: stop 유지, 사유 정정, 하한의 성격 공개, 10:345 비적용, 판 8 종료.
  - 글자 그대로 옮겼다고 한 부분은 모두 원문과 같습니다. sha 표 28개, 커밋·시각, 재집계도 모두 맞습니다.
  - 커밋 전에 고칠 것은 다음 넷입니다.
    - 진단 출력 경로 모순
    - O 목록 빠짐 3건과 4절 3 시각 미기입
    - SUMS 계획에서 이 감사 폴더가 빠짐
    - 판 9 위치 목록 2행·경로 2 금지 목록·import 공개의 보강
  - 이것들을 고치면 커밋해도 됩니다.

## 발견 사항 (심각도순)

**[커밋 전 수정][S·I] M-1. 진단 실행 출력 권장 경로가 커밋 전에 `--recursive` SUMS를 쓸 근거 폴더 안이다**
- 근거
  - 5단계 판정서 8절(353행): `stage5_aa_cause/`는 "커밋 직전 작성, 하위 폴더 `scripts\`가 있어 `--recursive`"이고, "진단 실행 출력(`diag\`)은 … 별도 폴더로 둔다".
  - 같은 판정서 9절(368행): "출력 권장 경로는 `ed8_design/stage5_aa_cause/diag/`다(8절: 이 판정서 근거 폴더와 분리)". 8절과 서로 어긋납니다.
  - 종료 판정서 4.5(262행): "출력 권장: `ed8_design/stage5_aa_cause/diag/`. … 그 폴더 SUMS를 쓴 뒤라면 별도 폴더로 둔다." 진단은 커밋 뒤에 돌므로(결정 5단계-3) 이 조건은 언제나 참입니다. 그런데 권장 경로가 그대로 남아 있습니다.
  - `write-sums stage5_aa_cause --recursive --dry-run`: 23항목. 진단 뒤에 `diag\`가 생기면 `baseline_check sums`가 `sums_unlisted`를 냅니다.
- 실패 시나리오: python-expert가 권장 경로대로 `stage5_aa_cause\diag\`에 쓰면, sha로 인용되는 근거 폴더의 SUMS가 커밋 직후 낡습니다(같은 일이 2026-11-25에 3회 있었습니다).
- 권장 조치(control-expert): 세 곳(5단계 8절·9절, 종료 4.5)을 형제 폴더 하나로 고정합니다(예: `ed8_design/stage5_aa_diag/`). 원인 분석 문서의 "메인 세션 권고" `diag/`는 sha로 인용되므로 고치지 않고, 종료 판정서에 "원인 분석 권장 경로 대신 이 폴더"라고 적습니다.

**[커밋 전 수정][T] M-2. O 목록(O8-39~O8-50)과 실제 호출의 차이 3건, 4절 3의 바뀐 판 시각 미기입**
- 근거: 11:45 KST 이후 세션 transcript 35개(메인 포함)의 도구 호출 입력을 에이전트별·시간 구간별로 묶어 O 목록과 대조했습니다. `transcript_scope --with-main`도 함께 돌렸습니다: 발견 5, Bash 파이프는 서브에이전트 1·메인 0, 훅 차단 0. 그 파이프 1건은 O8-49에 공개된 그 호출입니다.
  1. **python-expert(aa2e704f)의 두 번째 구간 12:09:55~12:11:16이 빠졌습니다.**
     - O8-45는 "11:45~11:50 KST"만 적었습니다. 메인 SendMessage(12:09:28) 뒤 이 구간에서 한 일은 다음과 같습니다.
       - `run_stage5_judge_t8pppp.ps1` Edit 3회(12:09:55, 12:09:57, 12:10:40)
       - `stage5_prejudge\SHA256SUMS` 재작성(mtime 12:10:51.790)
       - `j9_runs\56849248\ho_v0_prerun.SHA256SUMS` 작성(12:10:59, mtime 12:11:00.159). 이 목록은 jsonl·logs(.log·.err 포함)를 바이트 해시만 합니다. transcript에 남은 스크립트 `prerun_sums.py` 본문으로 확인했습니다: "hashed as bytes only (no content is decoded or printed)".
       - `baseline_check sums` 실행
     - 노출은 없습니다. 모두 판정 시작(12:11:50.93) 전입니다.
  2. **판정 전 감사(ab55ca9d, 11:51:55~12:05:15) 자신의 열람 행이 없습니다.**
     - 열람한 것: `ho_*_a1\logs\*.record.json`·`identity_check.log`·`.done`·`.identity.json` 전문(메타), jsonl 해시
     - 그 감사 보고 4-7행에는 공개돼 있습니다. 앞 O 목록이 verif 감사의 행위를 따로 행으로 둔 관례(O8-12, O8-27, O8-38)와 다릅니다.
  3. **O8-46(메인 12:12:00)이 실제보다 좁게 적혔습니다.**
     - 실제로 출력한 것: 최상위 키 이름 전체, `status`, `reasons`, `judge_code` head·`is_clean`, ed8-judge4 `status --porcelain --ignored` 줄 수
     - 판정서에는 "상태와 사유 한 줄"로 적혀 있습니다.
  - 4절 3(227행) "바뀐 판의 시각은 메인이 덧붙인다"가 비어 있습니다. 채울 값: ps1 마지막 수정 12:10:40.733, SUMS 12:10:51.790. 모두 판정 시작 전입니다.
  - 이 감사(a3e8bed7, 12:55~) 행도 더해야 합니다(위 "본 결과").
  - 나머지 행은 transcript와 맞습니다: O8-43, O8-47(12:14:19 Read 등), O8-48, O8-49, O8-50(12:47:13 Write). 11:45 이후 heredoc·`python -`·프로세스 종료 호출은 없었습니다.
- 권장 조치(control-expert 또는 메인): O8-45에 두 번째 구간을 더하고(또는 새 번호), 판정 전 감사 행과 이 감사 행을 더합니다. O8-46을 넓히고 4절 3에 시각을 채웁니다.

**[커밋 전 수정][S] M-3. SUMS 계획에 이 감사의 저장 폴더 `audit_ed8_closing/`가 없다**
- 근거
  - 5단계 8절(352행)은 판정 후 감사를 `audit_stage5_prerun/`(마지막)에 넣는다고 적었습니다. 종료 6절(310행)은 "감사 폴더는 마지막"이라고만 적었습니다.
  - 메인이 준 저장 경로는 새 폴더 `ed8_design\audit_ed8_closing\`입니다.
- 실패 시나리오: 새 감사 폴더가 SUMS 없이 커밋되거나, 계획과 다른 폴더에 감사 원문이 들어갑니다.
- 권장 조치: 두 판정서의 SUMS 계획을 저장 경로 하나로 맞춥니다. `audit_stage5_prerun/`(3개)와 `audit_ed8_closing/` 둘 다 마지막에 `--top-only`로 씁니다.
  - 메인이 이 감사 sha를 5단계 판정서 4절 13에 덧붙이면 그 판정서의 sha(f5cda2e3)가 바뀝니다. 그러면 종료 판정서 머리(10행)와 5절 표도 고쳐야 합니다. 감사 뒤 수정은 이 보고의 항목과 sha 덧붙임으로 한정하고, integrity-checker로 다시 잽니다.

**[커밋 전 수정][R] M-4. 종료 판정서 4.1 위치 목록에 결함 확인 감사의 위임 목록 중 2행이 빠졌다**
- 근거
  - 결함 확인 감사 위임 필요(157행): `jp3_ed8_rules.py:462·464·468·484·426·440·544·551·558·584-589`, `jp3_ed8_judge.py:892-897·1167·1269·1277·1278·1285`
  - 종료 4.1 표(193-203행)에는 462와 558이 없습니다(180은 본문에서 더함). 5단계 2.3(157-164행)도 462는 빼고 558은 본문(164행)에만 둡니다.
  - 직접 읽은 결과
    - 462 `aliases = [slot["slot"] … if slot["first_alias"]]`: 출력 `first_aliases`가 이름 목록이고, 544가 이것을 받습니다.
    - 558 `"row": unit["slot"]`: eps 병합의 행 키. 이번에는 원천 사이 병합을 만들지 않지만 키가 이름입니다.
- 권장 조치(control-expert): 4.1 표에 두 행을 "영향 없음(이번), 키는 이름"으로 더합니다. 결정문 목록이 이 둘을 뺐으면 그 사실도 적습니다.

**[커밋 전 수정][R·T] M-5. 경로 2 금지 목록(5단계 7절)이 4단계 6절의 범주보다 좁다**
- 근거
  - 4단계 6절(350-357행)이 넣은 것: 실행 출력 폴더(`impl_cases_a1/` 전체), 실행 출력 sha 목록(`RUN_ALL`·`LOCAL_ONLY`), 러너 사본과 원본(`~/.claude/runners/outrigger-ed8/stage4/`)
  - 5단계 7절(332-339행)은 `ho_*_a1/logs/*.log`·`*.err`만 넣었습니다. 빠진 것은 다음과 같습니다.
    - `ho_*_a1/` 전체: jsonl에 `final_phase`·해시 등 A/A 결과가 있습니다.
    - `ho_*.done`, `ho_v0_prerun.SHA256SUMS`, `_identity_checks/ho_*_a1.md`
    - 러너 `~/.claude/runners/outrigger-ed8/stage5/`(사본을 만들면 사본도)
    - 이 감사 폴더 `audit_ed8_closing/`
    - 진단 출력 폴더(M-1)
  - 종료 4.2(220행)는 "4단계 6절 + 5단계 7절 + 이 판정서"를 원본이라고 적었습니다.
- 권장 조치(control-expert): 7절 목록에 위 항목을 더합니다. `p85_options/`(P8-5 verif 감사가 판정 도구 줄을 인용했을 수 있음)를 넣을지는 확인 필요 2.

**[커밋 전 수정][R] M-6. 원인 분석의 판정 도구 import 공개가 일부만 적혔다**
- 근거
  - 5단계 5절(275행), O8-48(317행), 종료 4.3(234행)이 적은 함수: `slot_inputs`, `aa_pair_of`, `stage5_selection`, `unit_item_verdicts`
  - `provenance.json` 7행은 `shape_severity`를 더해 5개입니다.
  - 실제 스크립트(`stage5_aa_cause/scripts/*.py`)가 ed8-judge4에서 import한 모듈: `jp3_ed8_judge`(`GridStore`, `stored_cluster_hashes`, `effective_shape`, `shape_severity`, `V`, `TREATMENT_LABEL`, `AA_OWN_SETTING_ITEMS` 포함), `jp3_ed8_rules`, `jp3_ed7_judge`(`metric_of`, `t`), `jp3_ed8_gate_judge`(`read_rows`), `ed8_key_lists`(`main_line_starts`), `run_v5`(`job_key`)
  - 판정 checkout은 지금 깨끗합니다(0줄).
- 실패 시나리오: 판 9 경로 2 작성자를 고를 때, dynamics-expert가 판 8 경로 1 판정 도구와 실행 경로 모듈을 import·열람한 범위가 실제보다 좁게 남습니다.
- 권장 조치(control-expert): 5절과 O8-48에 모듈 목록을 다 적습니다. `provenance.json`은 sha로 인용되므로 고치지 않고 판정서에 차이를 적습니다.

**[기록][R] R-1. 종료 0절 수치 표기**
- "단측 95 % 상한 CP(6, 312) = 0.0376"은 하한값입니다. 5단계 2.4(186행)는 "CP95 ≥ CP(6, 312) = 0.037602"로 적었습니다. "상한 ≥ 0.0376"으로 쓰면 같아집니다.
- 4.4 표(246행) "자기 짝 하한 6/312"도 "x ≥ 6, n ≤ 312"로 쓰는 편이 정확합니다.
- 재계산(이항 정의, 이분법)은 모두 판정서·결함 확인 감사와 같습니다(재집계 표).

**[기록][R] R-2. 5단계 0절 45행 "해당 규칙은 7.3 4(가)와 7.4 308행이다"**
- 도구 사유가 가리킨 규칙을 설명하는 문장입니다. 51행 "도구 사유를 규칙 사유로 적지 않는다"와 함께 읽으면 모순은 아닙니다.
- 다만 "도구가 이 사유로 적용한 규칙 문면은"으로 쓰면 결정 1번 문면과 더 분명히 맞습니다.

**[기록][R] R-3. 종료 2절 "4단계 P8-2 경로 2 하지 않음"의 근거**
- 결정 5단계-2의 "하지 않는 것"은 census·S8-C·G′·12a·12b뿐이고, P8-2 경로 2는 적혀 있지 않습니다.
- 결정 4단계-2(census 경로 2와 함께 S8-C 전)와 판 8 종료에서 나오는 귀결입니다. 0절의 "P8-2 경로 2 미대조"는 사실입니다(4단계 판정서 46·50·343행).
- 확인 필요 1.

**[기록][R] R-4. 종료 2절 "6 census(1043 단위)"**
- 규칙 82·222행은 "1043줄"입니다. 병합 뒤 단위 수와 다를 수 있으니 "1043줄"로 씁니다.

**[기록][I] R-5. `ho_*_a1\`에는 `logs\` 말고 빈 `judge\` 하위 폴더도 있다**
- 파일 0개라 git에 들어가지 않습니다. 5단계 8절(348행)의 "하위 폴더 `logs\`"에 덧붙여 적으면 됩니다.

**[기록][R] R-6. 원인 분석 0절과 1절의 방법 문면이 다르다**
- 원인 분석 0절(11행)은 "봉인 규칙 코드로 재계산"이라고 적었습니다. 실제 방법은 1절대로 판정 도구 함수 호출입니다.
- 5단계 5절은 "판정 도구 함수로 재계산"으로 바로 옮겼습니다. 원문은 sha로 인용되므로 그대로 둡니다.

**[기록][C] R-7. 5단계 2.2(141행) "빌려 센 1 … 슬롯은 특정하지 않았다"**
- 원인 분석 1절 29행이 줄 190으로 특정했습니다. 인용을 더할 수 있습니다.

**[기록][R] R-8. 규칙 7.5 315행 공개 MDE80과 7.4 309행 공개**
- 종료 판정서에는 309행 문장이 없습니다. 5단계 판정서 4절 10에는 글자 그대로 있습니다.
- MDE80은 `k`가 동결되지 않아 계산되지 않았습니다(1.1). 종료 3.3의 "돌지 않은 항목"에 "7.5 MDE80 공개: k 미동결로 해당 없음" 한 줄을 더하면 judgement_checklist의 모호 항목이 닫힙니다.

## 규칙↔결정↔판정서 대조표

| 볼 것 | 근거 원문 | 판정서 | 판단 |
|---|---|---|---|
| 도구 사유를 규칙 사유로 적지 않음 | 결정 1번 10행 | 5단계 머리 9행, 0절 51-53행, 1.1; 종료 1절 5행 | 맞음(R-2 문면) |
| 멈춤 근거 x_N ≥ 6, CP(6,312) = 0.0376 > 0.025(307행) | 결정 1번 13행, 규칙 307행 | 5단계 10행·2.4; 종료 0절 | 맞음(R-1 표기) |
| "결과 본 뒤 감사자가 센 하한" 성격 | 결정 1번 14행 | 5단계 11·54·177행, 6.3; 종료 0절·3.5 | 맞음 |
| 10:345 비적용, 기록 실패로만 | 결정 1번 15행, 규칙 345행 | 5단계 0절 55행, 1.2 100행 | 맞음 |
| 결함 위치(5·8단계·시험) | 결정 1번 16-19행, 결함 확인 감사 157행 | 5단계 2.3, 종료 4.1 | 결정과 같고 결함 확인 목록보다 2행 적음(M-4) |
| 8단계 영향 | 결함 확인 감사 36-42행 | 5단계 2.3 161-164행 | 맞음 |
| 놓친 이유 공개 | 결함 확인 감사 168행 | 5단계 2.3 171행 | 글자 그대로(들여쓰기만 다름) |
| 판 8 종료, 하지 않는 것 | 결정 2번, 규칙 208·211행 | 5단계 3절, 종료 2절 | 맞음(R-3) |
| 종합 표기 | 결정 2번 28행 | 종료 0절 13-15행 | 결정 문안 + 두 요소. 두 요소 모두 사실 |
| P8-5 공개 문안 3개 | `p85_disclosure_text.md` 8-61행 | 종료 3.1 | **글자 그대로**(인용 블록 51줄 같음, 머리글만 번호 바뀜) |
| 13절 1~20 | 규칙 380-399행 | 종료 3.3 129-148행 | **글자 그대로**(20줄) |
| O8-1~O8-12 | 규칙 60-74행 | 종료 3.4 156-170행 | **글자 그대로**(15줄) |
| 원인 분석 5절 선택지 | `aa_cause_analysis.md` 138-145행 | 종료 4.3 223-230행 | **글자 그대로**(8줄) |
| 3절 인용(208·307·308·305행, 결정문 1742fa05 1번 "6단계는 5단계 판정 뒤 다시 묻는다") | 원문 | 5단계 3절 | 모두 원문에 있음 |
| 4절 10(309행, 13절 14) | 규칙 309·393행 | 5단계 4절 10 | 원문에 있음 |
| D-2 5 문장 | D-2 9행 | 5단계 64·265행, 종료 20행 | 같음 |
| 5절 결론 | 원인 분석 0절 표 | 5단계 5절 표("옮김", 글자 그대로라고 하지 않음) | 뜻은 같음. 줄 번호를 더했고 "판정 도구 함수로 재계산"으로 바로잡음(R-6). [추정]·결과 본 뒤·import 공개 있음(M-6 범위) |

## 재집계 표

| 항목 | 판정서 값 | 재집계 값 | 차이 | 판단 |
|---|---|---|---|---|
| 1.1 출력 키 15종(rule~judge_code) | 표 | 출력과 비교 15/15 OK | 0 | 맞음 |
| 1.2 `aa_summary` E·N 5키 | 표 | 2/2 OK | 0 | 맞음 |
| 1.3 `aa_item_scope`·`aa_j11_states`·`aa_shape_record`(harsher 10/1, milder 15/0, not_comparable 0/0) | 표 | OK, `same` 수 행 없음 | 0 | 맞음 |
| `slot_layers`/`aa_pairs` 항목 수 | 291/291 | 291/291 | 0 | 맞음 |
| 키 줄 / 이름 / (원천, 이름) / 겹침 / 원천별 | 339/291/339/48, a 171·b 48·c 120 | 같음. 겹침은 모두 (a_phase, b_shape)이고 b_shape가 뒤 | 0 | 맞음 |
| 2.2 유일 이름 E | 8(c_fs) | c_fs 8, pair 8, 실패 0 | 0 | 맞음 |
| 2.2 유일 이름 N | 235, pair 234(none 1), 실패 6 | a_phase 123 + c_fs 112, none 1(c_fs), 실패 2 + 4 | 0 | 맞음(원인 분석 줄 112·120·228·252·270·280과 원천 분포 같음) |
| 2.2 b_shape E / N | 7·pair 7·실패 0 / 41·pair 39·none 2·실패 3 | 같음 | 0 | 맞음 |
| 출력 state 합 | none_in_layer 3 | pair 288, none_in_layer 3 | 0 | 맞음 |
| CP95 (10,310)/(2,22)/(6,312)/(6,310)/(6,336)/(5,312)/(3,312) | 0.054102/0.259467/0.037602/0.037842/0.034939/0.033399/0.024663 | 같음 | 0 | 맞음(결함 확인 감사와 같음) |
| CP95 (11,310)/(0,24) | 원인 분석 0.058051 / 0.117 | 0.058051 / 0.117346 | 반올림 | 맞음 |
| 종료 5절 sha 21 + 커밋 5 | 표 | 모두 같음 | 0 | 맞음 |
| 5단계 인용 sha(ps1, SUMS, grid_blobs, run_console, `.identity.json`·jsonl·`.done` 각 3, `_identity_checks` md 3, `confirm_b_grid192` 4e80e69b, 격자 4행) | 표·4절 | 모두 같음 | 0 | 맞음 |
| 1절 경과 커밋·시각 | 2715230e 18:33:27, acba3304 23:53:21, 0aa6cbb8 09:23:30, T8 사슬 4회 교체 | git: 같음, 부모 사슬 41e107e9 → 56849248 → ecf6c142 → 2bf16b31 → 5955f25b → 2263b246 → 7ea78232 | 0 | 맞음 |
| 4단계·5단계 실행·판정 시각 | 13:46:19~16:02:02, 20:44 / 10:44:17~11:41:39, 12:11:50~52 | 4단계 판정서 25·27행, `run_console.log` | 0 | 맞음 |

## 근거 폴더·SUMS 계획 점검(6)

| 폴더 | 파일 | 하위 폴더 | ignore | > 10^8 B | 추적 | SUMS 건식 |
|---|---|---|---|---|---|---|
| `judge_7ea78232_s5` | 1 | – | 0 | 0 | 미추적 | `--top-only` 1항목, would_write |
| `ho_v0_a1`·`ho_aa2_a1`·`ho_aa3_a1` + `.done` 3 | 24 + 3 | `logs`, 빈 `judge`(R-5) | 0 | 0(최대 4.56 MB) | 미추적 | `ho_v0_prerun.SHA256SUMS` 27/27 해시 같음, 목록 밖 파일 0 |
| `_identity_checks` | 12 | – | 0 | 0 | 기존 9 추적, 새 md 3 미추적 | `sums`: unlisted 3. `--top-only` 건식: added 3, removed 0, changed 0(would_differ → `--force` 필요) |
| `stage5_prejudge` | 3 | – | 0 | 0 | 미추적(cited_untracked 3, 커밋 전이라 정상) | unchanged(ad466c57) |
| `stage5_judgement` | 2 | – | 0 | 0 | 미추적 | 2항목 |
| `stage5_aa_cause` | 23 | `scripts`(캐시 폴더 0) | 0 | 0 | 미추적 | `--recursive` 23항목(M-1) |
| `stage5_decisions` | 1 | – | 0 | 0 | 미추적 | 1항목 |
| `ed8_closing` | 1 | – | 0 | 0 | 미추적 | 1항목 |
| `audit_stage5_prerun` | 3 | – | 0 | 0 | 미추적 | 3항목, 마지막(M-3) |
| `audit_ed8_closing`(이 감사) | – | – | – | – | – | 계획에 없음(M-3) |

- 줄바꿈: `core.autocrlf` true입니다. 대상 파일 모두 `text: unset`(-text)이라 체크아웃해도 sha가 바뀌지 않습니다. `ho_k_selection.json`(CRLF 2507), `run_console.log`(CRLF 4), `_identity_checks\ho_*_a1.md`(CRLF 18)도 보호됩니다.
- 앞서 인용된 추적 파일(규칙, `.sha256`, 4단계 판정서, D-1·D-2·결정 4단계, 4단계 감사 2, P8-5 폴더, 키 파일, RUN_ALL, LOCAL_ONLY, `confirm_b_grid192`)은 `status --porcelain --ignored` 0줄입니다.

## 경로 2 금지 목록 원본(7)
- 4단계 6절(350-357행) + 5단계 7절(332-339행) + 종료 판정서(`ed8_closing/`)는 서로 이어집니다.
- 빠진 항목은 M-5입니다: `ho_*_a1/` 전체, `.done`, prerun 목록, `_identity_checks/ho_*`, stage5 러너, `audit_ed8_closing/`, 진단 폴더.
- 판정 worktree ed8-judge4와 T8 계열 blob은 4단계 목록에 있습니다.
- 원인 분석이 import한 `run_v5`·`ed8_key_lists`(C8 실행 경로 모듈, ed8-judge4 사본)는 9:335 범주에 듭니다(M-6).

## 확인 필요
1. 4단계 P8-2 경로 2를 하지 않는 것이 결정 5단계-2(판 8 종료)에 들어가는지 사용자에게 확인합니다. 그렇다면 종료 2절의 근거를 "결정 5단계-2의 귀결(결정문에 따로 적지 않음)"로 적습니다(R-3).
2. 판 9 경로 2 금지 목록에 `ed8_design/p85_options/`(P8-5 verif 감사가 판정 도구 줄을 인용했다면 9:335 범주)와 `ho_*_a1/` jsonl을 넣을지 정합니다(M-5).
3. 이 감사 원문의 저장 위치를 정합니다: 새 `audit_ed8_closing/`(지시) 또는 5단계 8절이 적은 `audit_stage5_prerun/`(M-3).

## 위임 필요
- **control-expert**: M-1(진단 경로 세 곳), M-2(O 목록 3건 + 이 감사 행 + 4절 3 시각; 메인이 해도 됨), M-4, M-5, M-6, R-1~R-4·R-7·R-8. 두 판정서만 고치고, sha로 인용된 원인 분석·결정문·공개 문안은 고치지 않습니다.
- **python-expert: `tools/verif` 후보** — `transcript_scope --summary-by-agent`
  - 입력: 세션 폴더, `--since`, 경로 범주 정규식(판정 출력·jsonl·스텝 로그·판정 도구 import·Write 대상)
  - 출력: 에이전트·시간 구간(SendMessage로 이어진 두 번째 구간 분리)별 도구 호출 수, 범주별 건수, 대상 경로(결과 비출력)
  - 종료 코드: 0 / 1 발견 / 2 입력 오류
  - 이번에는 즉석 스크립트로 했습니다. M-2의 1번(두 번째 구간 누락)은 이 꼴로만 잡힙니다.
- 앞 감사가 낸 후보 `record_check identity --list-key`, `gate_scan dict_keyed_by_record_field`는 이미 판정서에 있습니다.

## 메인 세션 권고
1. 위 수정이 끝나면 sha를 다시 재고, 종료 판정서 머리 10행과 5절 표를 고칩니다. 그다음 integrity-checker로 sha 표와 SUMS를 확인합니다.
2. SUMS는 이 순서로 씁니다. `--top-only`/`--recursive` 둘 중 하나를 꼭 줍니다.
   1. `judge_7ea78232_s5 --top-only`
   2. `_identity_checks --top-only --force`(건식 added 3)
   3. `stage5_judgement --top-only`
   4. `stage5_aa_cause --recursive`
   5. `stage5_decisions --top-only`
   6. `ed8_closing --top-only`
   7. 마지막으로 감사 폴더(`audit_stage5_prerun`, `audit_ed8_closing`) `--top-only`
   - 쓴 뒤 각 폴더에 `baseline_check sums`를 돌리고, `git status --ignored`로 인용 파일이 ignore에 걸리지 않는지 봅니다.
   - `ho_*_a1`은 `ho_v0_prerun.SHA256SUMS`로 고정되므로 새로 쓰지 않습니다.
3. 진단 실행은 커밋 뒤, M-1에서 정한 형제 폴더에 씁니다.
4. 러너 사본(`~/.claude/runners/outrigger-ed8/stage5/`)을 넣을지 정하고, 넣으면 `--recursive`로 씁니다. 넣든 안 넣든 경로 2 목록에 원본을 넣습니다.

## 검사하지 못한 것
- 원인 분석의 C-J 항목 판정(판정 도구 함수 값)과 근거 csv·json의 독립 재계산. jsonl을 쓰지 않는 조건이라 하지 않았습니다.
- 11:45 이전 O 목록 행(O8-39~O8-42, O8-44)의 transcript 대조. 지시한 `--since` 범위 밖입니다.
- 러너 원본 폴더 `~/.claude/runners/outrigger-ed8/stage5/`의 내용·크기.
- `p85_options_verif.md`가 경로 1 줄을 인용했는지(확인 필요 2).

## 실행한 검증
- 인터프리터: python-dev `C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B`(`MKL_THREADING_LAYER=TBB`, `-X utf8`). 판정 모듈은 import하지 않았고 판정 도구도 실행하지 않았습니다.
- 도구
  - `depcheck`(STAMP)
  - `source_guard snapshot`(입력 21) / `verify`
  - `seal_check --repo … v8_rules.md`(종료 0)
  - `baseline_check sums`(stage5_prejudge: cited_untracked 3, `_identity_checks`: unlisted 3)
  - `baseline_check write-sums --dry-run` 8개 폴더
  - `transcript_scope … --with-main --blind-list … --since 2026-11-28T11:45 --watch 04_scripts`(발견 5: 경고 1, 참고 4)
  - `judgement_checklist`(종료 판정서: missing 0·ambiguous 22, 13절 글자 그대로라 모호는 토큰 문제, R-8. 5단계: missing 1 = 13절 13 census 칸, 종료 3.3에서 처리)
- git: `config core.autocrlf`, `check-attr text eol`, `check-ignore -v --no-index --stdin`(74개 0건), `ls-files`, `log -1`(커밋 10개), `log -- <규칙·결정문>`, `worktree list --porcelain`, ed8-judge4 `rev-parse`·`status --porcelain --ignored`(0줄, 시작과 끝 두 번), `status --porcelain --ignored -- <인용 추적 파일>`(0줄)
- Read
  - 두 판정서·결정문·원인 분석·결함 확인 감사·P8-5 결정문·공개 문안·D-2 전체
  - 규칙 55-79·195-214·274-348·376-401행, 4단계 판정서 336-361행
  - `run_console.log`, `grid_blobs.txt`, `ho_v0_prerun.SHA256SUMS`, `blind_paths.json`(blind 빈 목록)
  - 판정 도구 `jp3_ed8_rules.py` 419-443·456-513·536-591행
- Grep: 4단계 판정서(시각·커밋·경로 2·시험 이름), 판정 전 감사(본 결과), 규칙(1043), 원인 분석 scripts `*.py`(import·모듈 속성), `provenance.json`(sha·import)
- Glob: 대상 폴더 8개, `p85_options`, 세션 subagents 폴더, ed8-judge4 `04_scripts`(패턴 `**/jp3_ed8_*.py`)
- 즉석 스크립트(scratchpad `verif-ed8-closing\`): `hashes.py`, `folders.py`, `verbatim.py`, `out_struct.py`, `out_check.py`, `tscan.py`, `tdetail.py`, `twrite.py`. 모두 지웠고 폴더도 지웠습니다(`Test-Path` False). `__pycache__`는 만들지 않았습니다(-B).
- Bash 파이프·heredoc을 쓰지 않았습니다. 프로세스를 종료하지 않았습니다.
- 메모리: `audit_pitfalls.md`에 한 단락(커밋 전 종료 문서: 진단 경로·SendMessage 두 번째 구간·import 공개·위치 목록)을 더했고, `MEMORY.md` 색인 줄을 늘렸습니다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v8_rules.md 35f9eba8…, jp3_remedy_spec_v8_rules.md.sha256 e19aaa48…, stage5_judgement_ed8.md f5cda2e3…, run_console.log 471314fc…, ed8_closing_judgement.md 6376a9f3…, decision_stage5_20261128.md 7d236aa2…, aa_cause_analysis.md 32c2a685…, provenance.json 4f9ef07d…, verif_stage5_defect_check.md bec52a14…, verif_stage5_prerun.md af3b40b3…, verif_stage5_prejudge.md 05d8dacd…, decision_p85_20261128.md 1742fa05…, p85_disclosure_text.md 42614b21…, stage4_judgement_ed8.md fb0f4132…, ho_k_selection.json ff4b1c53…, heldout_g_ed8.json a18b5818…, ho_v0_prerun.SHA256SUMS 5c41c183…, run_stage5_judge_t8pppp.ps1 9482528c…, SHA256SUMS ad466c57…, grid_blobs.txt 673d0c92…, SHA256SUMS 63a99c3d…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음

## 커밋 가능 여부
차단은 없습니다. 판정 내용(5단계 stop, 사유 정정, 판 8 종료)과 글자 그대로 옮긴 부분, sha, 재집계는 모두 맞습니다. M-1~M-6을 고치고 메인 세션 권고 1·2를 마치면 커밋해도 됩니다. 기록 R-1~R-8은 함께 고치면 좋지만 커밋을 막지 않습니다.
