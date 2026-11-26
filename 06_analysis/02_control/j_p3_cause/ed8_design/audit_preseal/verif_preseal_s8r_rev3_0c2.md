# S8-R 개정 3 재감사 추가: 0c′ 결과 반영 (verif-protocol-auditor, 2026-11-26)

이 문서는 `verif_preseal_s8r_rev3.md`에 덧붙인다. 그 보고의 판정(차단 0 / 실행 전 수정 4 / 기록 4)과 "0c′를 봉인 조건으로 둔다" 권고는 그대로다. 아래는 0c′ 조건을 충족했는지에 대한 판단이다.

## 결론
- **0c′ 봉인 조건은 충족됐다.** python 보고와 지난 재감사 R-6 독립 확인의 수가 단계별로 모두 같다. 남은 일은 명세 문면 두 곳을 고치는 것뿐이다(아래 권고 1).
- 차단은 그대로 0이다.

## 대조 (값 비출력, 행 수만)
| 단계 | python 0c′ 사건 행 | 재감사 R-6 독립 집계 | twin 구조(python / 재감사) | 판단 |
|---|---|---|---|---|
| C-J | 200 / 388, 이름은 모두 사례 기본값 | 200 (R12 160 + R14 10 + R15 10 + R16 20) | `fs_kN,leg,level` 140 + twin 없음 60 / R12 twin 140(`event` 필드 없음) + 나머지 60 | 일치 |
| C-S | 260 / 460, 이름은 모두 사례 기본값 | 260 (R12 180 + R14 20 + R15 20 + R16 40) | 140 + 120 / R12 twin 140 + 120 | 일치 |
| C-D | 12키(census 24), 이름은 모두 twin `event` | 12, twin `event` 명시(FS24 4·G4 4·RE1bF 4) | `event,fs_kN,leg,level,timing` 12 | 일치 |
| C-G | 171, 이름은 모두 twin `event` | 171, twin `event` 명시 | 같은 구조 171 | 일치 |
- 이름 미정 0, `EVENTS` 밖 0, 다리 미정 0, `LEGS` 밖 0이다. R13 행은 census에 0줄이다. 이는 두 확인이 독립적으로 얻은 결과다.
- 입력 sha 6개가 일치한다. python 보고가 재계산했고, 재감사의 앞선 해시 확인과도 같다(main.jsonl `9ad74990…`, j9_main `c89ec827…`, sens `be930b75…`, D blob `a995abff…`, G1 `684054ab…`, grid192 `4e80e69b…`).
- 사례 기본값을 덮어쓰는 방식(`run_v5._case_of` 477~490행 `replace(case.twin, **job["twin"])`)은 6.3의 "twin `event`, 없으면 사례 기본값"과 같은 순서다(python 보고 30행).
- python 보고 33~39행의 교차 확인도 있다. 키 파일 job으로 정한 사건 이름이 C-D·C-G 격자 run의 `event`와 12/12·171/171 같다. 격자 run에 `leg`가 없어 다리는 대조하지 못했다는 점은 기록으로 둔다.
- 폴더 SUMS: `python_0c2_events/SHA256SUMS` sha256은 `44f8506dd8b6bab35013fd571143f32386661c791e8cbad36156df2f00ad63e8`다(재계산, 메인 통지와 같음). `baseline_check sums` 결과는 3항목, mismatch 0, missing 0이고, 종료 1의 사유는 커밋 전이라 생기는 `cited_untracked` 4뿐이다.

## 권고(봉인 전, 문면)
1. control-expert: 명세 문면 두 곳을 고친다.
   - 4절 0c 행(`:193`)의 0c′를 "끝남(미정 0)"으로 바꾸고 근거 경로를 적는다.
   - 머리말 근거 표에 `python_0c2_events/`(SUMS `44f8506d…`, `event_names_0c2.json` `c885d339…`)를 한 줄 더한다.
   - 지난 재감사 N-1~N-4와 함께 고친다.
2. 메인: 위 변경과 근거 표 SUMS 칸을 기입한 뒤, 바뀐 줄이 이 칸들과 N-1~N-4뿐인지 diff로 확인한다. 그 뒤 `.sha256`을 만들고 `seal_check`를 돌린다.

## 기록
- python 0c′의 첫 두 실행은 종료 3(도구 오류)이었다. 고친 뒤 종료 0이다. 음성 대조 6종으로 검출력도 확인했다. 결과 json sha는 ruff 수정 전후로 같다(python 보고 46~56행).
- python 보고는 `r67_g1_screen.py` 85~124행에서 `EVENTS` 깊이·램프 코드 상수를 보았다고 공개했다. 이 값은 판정 결과가 아니다.

## 실행한 검증
- `python_0c2_events/` 파일 목록(비재귀)을 보고, SUMS를 `Get-FileHash`로 재계산했다.
- `baseline_check.py sums --repo C:\workspace\outrigger_control <python_0c2_events>`를 python-dev `-I -B`로 실행했다. 결과는 종료 1(`cited_untracked` 4만)이다.
- `python_0c2_events/report.md`를 Read로 읽었다.
- 쓰기 없음. scratchpad를 쓰지 않았고, 프로젝트 파일도 쓰지 않았다.
- 원본 불변: 이번 추가 확인에서 쓰기 0회다. 직전 재감사 source_guard 결과는 "원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v8_rules.md f5508044…, control_rev3_handback_notes.md 7c4e3d77…, 디렉터리 목록 동일, ~$ 임시 파일 없음) · 경고: 형제 항목 수정 시각만 변경 1건(ed8_design)"이다.
- 사용한 스킬: 없음

## 공개(행위 그대로)
- `ed8_design/python_0c2_events/` 하나만 파일 경로를 지정해 읽었다. 블라인드 경로와 그 상위 폴더는 검색·목록 범위로 쓰지 않았다. Bash는 쓰지 않았다.
