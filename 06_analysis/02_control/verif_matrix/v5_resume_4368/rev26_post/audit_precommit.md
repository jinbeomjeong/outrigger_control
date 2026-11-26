# 436.8 rev26 판정서 덧붙임 커밋 직전 감사 — verif-protocol-auditor, 2026-11-27

## 감사 요약
- **본 결과**
  - 판정서 `v5_resume_4368_harness_judgement.md`: 덧붙인 줄과 13절 전체
  - 2회차와 원 출력의 `u3_judge.json`(`vb_counts`, `grades`, `R4.G-5_list_RD7`), 경로 2 `u3.json`(`sentence_VB`, `G-5_list`)
  - 저장 결과 `las_k1/u3_g6_{V0,VB}.json` 두 행, `u3_g8_VB.json` 두 행, `u3_h9_VB.json` 한 행(키·`failed_rows`·`flags`·`min_force_kN`·`verdict`)
  - 인용된 파일들의 sha
  - 블라인드는 열지 않았고, 상위 폴더 검색도 하지 않았다.
- **대상**
  - 판정서 HEAD `09dda89f` blob(sha256 `a84558c7…`) → 작업 트리 sha256 `c3fdedc2…`
  - `.gitattributes`
  - 커밋 대상 6곳
- **판정: 차단 0 / 커밋 전 수정 0 / 기록 2. 커밋해도 된다.**

## 점검 결과
| 항목 | 결과 | 근거 |
|---|---|---|
| 원 줄 불변(삽입만) | **충족** | `git diff --numstat HEAD`: +220 / −0. 삽입 위치 5곳: 50행(0.1 아래 rev26 기준 종합 가리킴), 77행(0.2 아래), 310행(4.4 끝), 322행(4.5 끝), 933~1148행(13절). 0.1·0.2 원 낱말과 원 종합(판정 불가)은 그대로다. LF, BOM 없음, `-text`, `i/lf w/lf` |
| rev26 0절 공개 문장 그대로 옮김 | **충족** | 판정서 953~964행에서 `> `를 떼면 rev26 21~32행 12줄과 바이트가 같다 |
| 결과 뒤 예외·사전 등록 증거 아님 표기 | **충족** | 0.1 가리킴(50행), 13.1 인용(962행), 966행(예외 1은 이번 데이터에서 걸리지 않음), 13.1 종합(967행), 13.3 끝(1028행) |
| 13.2 묶음 문구 982/23/68/41 | **일치** | 경로 1 `u3_judge.json :: u3.<연구>.vb_counts` 아홉 연구의 합: pass 982 / flag 23 / safe_stop 68 / fail 41(합 1,114). 연구별 수가 13.2 1001행과 모두 같다. 원 출력 `vb_counts`와도 같다 |
| G-5 5키(키·파일·위치) | **일치** | 2회차 경로 1 `R4.G-5_list_RD7` = 원 출력(완전 일치) = 경로 2 `U-3.G-5_list.rows`. 위치는 `records[97]`·`[101]`(g6), `[15]`·`[138]`(g8), `[0]`(h9) |
| V0·VB 등급 | **일치** | `u3.g6.grades`: 두 키 V0 flag / VB fail. g8 두 키와 h9 키: V0 pass / VB fail |
| g6 두 키 `failed_rows`·`min_force_kN` | **일치** | VB `records[97]`: [`G6-3_Fmin`, `G6-7_preloc`], 5.745. VB `[101]`: 같은 두 항목, 6.842. V0 `[97]`: [`G6-7_preloc`], flags [`P3-1_transient_recontact`, `G6-2_late_loc_reapproach`], 11.460. V0 `[101]`: [`G6-7_preloc`], flags [`G6-2_late_loc_reapproach`], 10.203. 파일 sha `9a3dd41b`·`df91a50d`가 판정서와 같다 |
| g8·h9 VB 실패 사유 | **일치** | `u3_g8_VB.json` `[15]`·`[138]` 실패 사유 [`T2`]. `u3_h9_VB.json` `[0]` [`P3-5`] |
| 경로 2 셈(기록) | **일치** | `sentence_VB` 새 957/23/57/24, 원 895/18/57/24. 차이 62/5/0/0 = 연구 C(29/5/0/0) + D(33/0/0/0) |
| 비교기 19/2/0, 53/53 | **일치** | 판정 후 감사(`29420fde`)의 13.9·13.10 수치와 같다 |
| 인용 sha(26개) | **모두 일치** | 판정 후 감사 `29420fde`; `stage5_record` 2회차 `0e19f7a6`·1회차 `23c8dac9`; 드라이버 로그 `e84dd2ff`·`6eec5e64`; 비교기 결과 `bbdb8dc7`·`29b17946`·원 `08691021`; 드라이버 `55749bfe`·`445a103c`; `run1_main_seen_output.md` `639f0165`; 수정 1 보고 `11684684`; 4′ 감사 `c95bf8a3`·`8fd5a7dd`·`1802af21`; 덧붙임 초안 `8975c342`; manifest `06ef3ffa`·`d05ebdc1`; identity `e65e611c`·`4c110234`; 정오 3 `.sha256` `ecf41f33`; `control_evidence` 다섯 스크립트(`22817c29`·`64078f5e`·`3db4eab9`·`f29f1249`·`5603fabc`) |
| 판정 후 감사 "판정서에 적을 것" 1~11 | **빠짐 없음** | 1→13.1과 0절 인용, 2→13.2(사용자 결정 A), 3→13.3, 4→13.4, 5→13.5, 6→13.6, 7→13.7, 8→13.8, 9→13.9, 10→13.10, 11→13.11 |
| 정체성 정본 | 반영 | 13.4: `stage5_record.json`(`0e19f7a6`)이 정본이고, identity의 null 칸은 고치지 않는다(메인 결정) |
| `.gitattributes` `rev26_post/** -text` | **충족** | HEAD 대비 `+` 한 줄. `rev26_post/` 14파일의 `check-attr`가 모두 `unset` |
| 커밋 대상 ignore·크기·eol | **충족** | 아래 표 |

**커밋 대상 상태**
| 대상 | 파일 | 바이트(최대 파일) | ignore | `check-attr` | CRLF 파일 |
|---|---|---|---|---|---|
| `judge_rev26_74c2784/` | 238 | 41.8 MB(10.26 MB) | 0 | 모두 unset | 142 |
| `judge_rev26_335004a/` | 213 | 29.5 MB(10.26 MB) | 0 | 모두 unset | 129 |
| `rev26_stage5/` | 7 | 16 KB | 0 | 모두 unset | 4 |
| `rev26_stage5_run2/` | 7 | 25 KB | 0 | 모두 unset | 4 |
| `rev26_impl/path2_fix1_report.md` | 1 | 7 KB | 0 | unset | 0 |
| `rev26_post/` | 14 | 84 KB | 0 | 모두 unset | 0 |

- 모두 미추적이다.
- 단일 파일은 모두 원격 한도(10⁸ B)보다 훨씬 작다.
- CRLF 파일은 도구·콘솔이 쓴 원 바이트다. `-text`라 그대로 커밋되고, 섞인 줄바꿈 파일은 0이다.
- 출력 json은 (d) 비교가 정규화로 다뤘고, 범위 밖 파일 28개는 원 출력과 raw 바이트가 같다(판정 후 감사).
- `.gitattributes` 외에 `00_docs/decision_log.md`도 수정 상태다(메인 결정 줄).

## 발견 사항 (기록)

### [기록] K-1 13.6의 "판정 낱말이나 판정값이 든 줄은 없다"는 정오 3 0절보다 강한 표현이다
- 정오 3 0절(48~51행)은 두 가지를 결과 정보로 적었다.
  - 1회차 화면의 경로 1 "종료 1 단계 7개" = findings 유무
  - 비교기 `equal 5 / differ 0`
- 13.6도 그 줄들을 나열했으므로 사실 누락은 없다.
- **권장(선택)**: 1089행 뒤에 "다만 단계 종료 1(findings 유무)과 두 경로 대조 일치 건수는 결과 정보다(정오 3 0절)"를 한 구절 더한다. 삽입만이라 원 줄 불변 조건은 유지된다.

### [기록] K-2 SUMS 순서
- 이 보고(`audit_precommit.md`)를 `rev26_post/`에 저장한 **뒤에** 메인이 SHA256SUMS를 써야 한다.
- 판정서는 `rev26_post` 파일을 개별 sha로 인용한다(감사 `29420fde`, 초안 `8975c342`). 폴더 SUMS는 인용하지 않으므로 순서만 지키면 낡지 않는다.

## 메인 세션 권고
1. (선택) K-1 구절을 더한다. 더했다면 판정서 sha를 새로 기록한다.
2. 이 보고를 저장한다. 이어서 `baseline_check.py write-sums`로 `rev26_post/`·`rev26_stage5/`·`rev26_stage5_run2/`의 SHA256SUMS를 쓴다.
3. integrity-checker를 돌린 뒤 커밋한다. 대상: 판정서, `.gitattributes`, `decision_log.md`, 위 6곳.
4. 커밋 뒤 `git ls-files --eol`로 LF 파일 `i/lf`, CRLF 파일 `i/crlf`(`attr/-text`)를 확인한다.
5. 판정서 커밋 뒤 `rev26-t26`·`rev26-t26b` worktree의 lock을 풀고 정리한다(브랜치는 남김).

## 검사하지 못한 것
- 13절 서술 가운데 결정 3·138·9절 한계 내용의 의미 대조(도메인 판단)는 하지 않았다. 수치·sha·낱말·인용 일치만 봤다.

## 실행한 검증
- python-dev `-I -B`(MKL_THREADING_LAYER=TBB)
- 즉석 스크립트 `pc.py`(인용 대조, 재집계, 인용 sha), `pc2.py`(등급, `.gitattributes`, 커밋 대상 상태). scratchpad `verif-rev26-pc\`에 두고 보고 전에 지웠다.
- git 조회: diff(`--numstat`·`-U0`), rev-parse, hash-object, check-attr, check-ignore, ls-files
- 판정 도구 실행은 0회다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha v5_resume_4368_harness_judgement.md c3fdedc2…, v5_resume_4368_rules_rev26.md f6591836…, .gitattributes d3db7f9a…, audit_post_run2.md 29420fde…, 디렉터리 목록 동일, ~$ 임시 파일 없음) · 경고: 형제 항목 수정 시각만 변경 1건(.git)
- 사용한 스킬: 없음

## 공개 (행위 그대로)
- **연 것**
  - 판정서 46~79, 305~324, 928~1152행
  - 위 "본 결과"의 출력 키와 저장 결과 행
  - `rev26_post/` 파일 이름 목록
- **열지 않은 것**: 블라인드, 원 판정 후 감사 문서, `rev26_post`의 다른 보고 본문(sha만)
- **종료한 프로세스**: 없음
