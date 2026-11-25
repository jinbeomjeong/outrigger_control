## 판 7 정오 1: 확인 감사 기록 R-a~R-d 반영 (봉인 전 최종본)

확인 감사의 기록 4건과 지시하신 두 줄(확인 감사 sha, `handoff_leak --shared`)을 모두 넣었습니다. 문면만 고쳤고 판정 정의·도구·T′는 바뀌지 않습니다.

- **새 sha256**: `74c49bdaddf3fa63feeb70dd24b04823d517df2dbdc7b72c7592e70b1ef81a5b`
  - 이전 값은 `e5e73119…`입니다.
  - 282줄, LF만, BOM 없음입니다.
- 파일: `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\jp3_remedy_spec_v7_erratum1.md`
- 봉인 명세 `jp3_remedy_spec_v7.md`는 그대로입니다(`git status`에 변경 없음). 커밋은 하지 않았습니다.

### 바꾼 행 (새 파일 기준)
| 행 | 항목 | 내용 |
|---|---|---|
| 24 | 머리말 | 재감사 반영 줄 끝에 확인 감사 원문 경로와 sha256을 적었습니다.<br>- 경로: `ed7_design/postseal/audit_confirm_erratum1_e5e73119_20261125.md`<br>- sha256: `02baa26c3b63f2877ef51722833259f2392a4e705d7d93bb0a7b7690853cac0c` (직접 계산해 맞춤)<br>대상 e5e73119, 차단 0, 기록 R-a~R-d와 각각을 반영한 곳도 함께 적었습니다. |
| 130 | R-c | 1-9 첫 줄의 "첫 실측은 l1ref"를 "첫 실측은 1단계 전 건식 확인(1-19), 판정 실측은 l1ref"로 바꿨습니다. |
| 165 | R-a | 1-13 T′ 요구 끝 문장의 "`not_applicable` 상태와 그 줄 수"를 "`no_event` 줄 수(`rev7_condition.summary.no_event_lines`)와 `rev7_condition_records`"로 바꿨습니다. T′ 552~573행과 같다는 근거를 붙였습니다. |
| 187 | R-b | 1-16의 "확인하지 않았다(재감사 확인 대상)"를 재감사 확인 항목 4·R-1의 답으로 바꿨습니다(아래 요약). |
| 247 | R-d | 「판정서에 옮길 것」 15번에 O7-19를 더했습니다. 확인 감사가 블라인드를 품은 상위 폴더 `j_p3_cause`를 범위로 Grep 1회(glob `jp3_remedy_spec*.md`, 건수 모드)를 했고, 출력은 명세·정오 8개 파일의 건수뿐이었습니다. ripgrep이 `j9_runs` 아래를 순회했을 수 있습니다(O7-13과 같은 종류). |
| 278 | 경로 2 넘김 | 「경로 2에 넘길 정의 문장」 절에 "넘김 때 `handoff_leak --shared`에는 436.9 원판 `jp3_remedy_spec.md`를 포함한다" 한 줄을 넣었습니다. |

**187행에 넣은 재감사 답의 요지**
- T에서 기록 설정의 침범(H-7)은 감도 status에 들어가지 않았습니다.
  - 근거: `jp3_basis` 468~469행의 `has_judged_breach`와 `j_p3_over_rows` 232~235행의 `status_by_revision`은 판정 몫인 `rev5/6/7`만 봅니다.
- T에서 status에 들어갈 수 있었던 것은 기록 줄의 줄 단위 결함 수 5종뿐이었습니다.
  - 5종: `rule_missing`·`test_only`·`l1_reference`·`revision_key_missing`·`revision_key_mismatch`
  - 위치: `j_p3_over_rows` 236~237행, `jp3_basis` 471~474행
- T′는 기록 줄을 J-P3 status에 넣지 않습니다. 다만 460줄 전체의 6.1 정체성 대조(`judge_sens` 933·947~948행)는 status에 남습니다.

### 이번에 연 것
- 정오 1과 확인 감사 원문의 sha만 다뤘습니다(원문 내용은 지시 문면을 그대로 따랐습니다).
- 블라인드 경로, 상위 루트 검색, 실행 출력은 열지 않았습니다.
- Python·scratchpad는 쓰지 않았고, 실행한 명령은 Get-FileHash와 git status뿐입니다.

### 메인 세션이 할 일
- 정오 1 `.sha256`(74c49bda…)을 만들고, 근거 폴더 5개와 함께 봉인 커밋해 주세요. `postseal` SUMS는 확인 감사 원문까지 넣은 뒤 마지막에 써 주세요.
- 경로 2 넘김 때 274~282행의 [정의 E7-P2-1]·[E7-P2-2]를 그대로 옮기고, `handoff_leak --shared`에 `jp3_remedy_spec.md`를 포함해 주세요.

사용한 스킬: 없음
