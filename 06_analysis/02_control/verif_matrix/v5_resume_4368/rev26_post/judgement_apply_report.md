# 436.8 하네스 판정서 rev26 덧붙임 반영 보고 (control-expert, 2026-11-27)

## 요약
- 대상: `C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368_harness_judgement.md`(원본 수정 허락, 사용자 결정 2026-11-27)
  - sha256: `a84558c72e4aa925d860f757d97c2138f969e02c884f5a1e8e44c4c1d2adf9df`(HEAD 판, 1,157줄) → **`c3fdedc2e037fd1061d37dc9065c94293198fd18f5691700bbd3ca21abede645`**(1,377줄)
  - LF(CR 0), 끝 개행 있음. 파일 속성 `-text`(`i/lf w/lf attr/-text`)는 그대로다.
  - `git status`: ` M`(미커밋)
- **원 줄은 하나도 바꾸지 않았다.** 다섯 곳에 삽입만 했다(HEAD 대비 difflib).

| # | 새 파일 줄 | 줄 수 | 넣은 곳(원 파일 기준) | 내용 |
|---|---|---|---|---|
| 1 | 50 | 1 | 0.1절 끝(원 49행 R16-15b 줄) 뒤, `### 0.2` 앞 | rev26 기준 종합 가리킴 줄(사전 등록 증거 아님): H-3 통과(한계 기록 동반)·H-4 통과 → 하네스 최악 미달, v5 종합 미달. 원 승인 문장 그대로 |
| 2 | 77 | 1 | 0.2절 "v5 종합 판정: 판정 불가" 줄(원 75행) 뒤 | rev26 재판정 낱말 가리킴 줄 |
| 3 | 310 | 1 | 4.4절 "재판정:" 줄(원 307행) 뒤 | → 13.1·13.2절: 통과(한계 기록 동반) |
| 4 | 322 | 1 | 4.5절 "재판정:" 줄(원 318행) 뒤 | → 13.1절: 통과(IND_LAS 기록 완료) |
| 5 | 933~1148 | 216 | 12절 끝(원 928행) 뒤, `## 부록 A` 앞 | 새 `## 13. rev26 재판정 덧붙임 (2026-11-27)`, 13.1~13.12 |

## 초안 대비 바꾼 것
- 초안: `rev26_post/judgement_addendum_draft.md`, sha256 `8975c342ca174f4f59dfb5afe830ff4ae41fb4e0ff72d622573b58d050b407c5`
- **`<G-5 사용자 결정>` 자리**: 두 곳 모두 A로 채웠다. 남은 자리 표시는 0개다.
  - 13.1 H-3 행: "→ 사용자 결정 2026-11-27(A) 뒤 **통과**(한계 기록 동반)". 근거 칸에 "세 표지는 결정 3·138로 모두 한계 기록·해소, 남은 표지 없음(1.3)"을 더했다.
  - 13.1 종합: 하네스 최악 미달(H-9 격자·H-10), Chrono 최악 미달(C-2·C-5), v5 종합 미달(rev26 기준, 사전 등록 증거 아님). 원 0.1절 판정 불가는 그대로 두었다. C-9~C-11은 기록 묶음이고, 다음 단계 문장은 0.1절 그대로라는 점을 적었다.
- **13.2 정리**
  - 제목에 "사용자 결정 2026-11-27 = A"를 넣었다.
  - 5키 표를 본문에 실었다("확인 필요 질문" 표를 참조하던 문장을 대신함). 처리 열은 결정 3·138이다.
  - "결정 A의 귀결"과 묶음 문구를 확정으로 적었다. 연구별 `vb_counts`도 함께 적었다.
  - B·C 행은 "고르지 않은 선택지" 표로 남겼다.
  - 셈 차이 53은 "기록(사용자 결정 2026-11-27, 등급 대조에 쓰지 않음)"으로 적었다.
- **확인 필요 3(g6 두 키의 하네스 VB 실패 항목)을 채웠다.** 저장 행 `06_analysis/02_control/v5_rerun/las_k1/u3_g6_VB.json`(sha256 `9a3dd41b…`) `records[97]`·`[101]`과 같은 id의 V0 행(`u3_g6_V0.json` `df91a50d…`)을 읽었다.

| 키 | VB `failed_rows` | VB `min_force_kN` | V0 `failed_rows` / `flags` | V0 `min_force_kN` | 판정기 등급(V0 / VB) |
|---|---|---|---|---|---|
| `g6r\|rigid+S1@FL\|top\|Fs4` | `G6-3_Fmin`, `G6-7_preloc` | 5.745 | `G6-7_preloc` / `P3-1_transient_recontact`, `G6-2_late_loc_reapproach` | 11.460 | FLAG / 실패 |
| `g6r\|rigid+S1@FR\|top\|Fs4` | `G6-3_Fmin`, `G6-7_preloc` | 6.842 | `G6-7_preloc` / `G6-2_late_loc_reapproach` | 10.203 | FLAG / 실패 |

  - 13.2에는 "VB 고유 항목은 G6-3($F_{min}$ 9.415 kN 아래)"을 **[해석]**으로 적었다.
    - 근거: V0의 `G6-7_preloc`은 판정기 강등(u3 원판 4절 377·424.11.2)으로 FLAG가 되었고, VB에만 있는 `G6-3_Fmin`이 실패를 남긴 것으로 읽었다.
    - 강등 조건의 행별 재계산은 하지 않았다.
  - 하네스는 VB 쪽 최소 힘이 낮고, C-10 Chrono는 V0 쪽이 나쁜 반대 방향이다. 이 대비는 결정 138대로 한계 기록에 함께 적었다.
- **근거 스크립트 인용**: `v5_resume_4368/rev26_post/control_evidence/` 경로로 적었다. 이번에 두 개를 더 넣었다(아래 표). 메인이 폴더 SHA256SUMS를 이미 썼다면 다시 써야 한다.
- 13.12에 덧붙임 초안 sha(`8975c342…`)를 근거 목록에 더했다.
- 초안의 "넣는 곳" 안내문, 확인 필요 질문 절, 공개 절은 판정서에 넣지 않았다.

## 산출·변경 파일
| 파일 | sha256 | 비고 |
|---|---|---|
| `C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368_harness_judgement.md` | `c3fdedc2e037fd1061d37dc9065c94293198fd18f5691700bbd3ca21abede645` | 수정(삽입 5곳, 220줄) |
| `C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368\rev26_post\control_evidence\g6_rows.py` | `f29f1249a3594065ee695601c2dcdc2aac58c18a42f4a96db8e83d3761e59be3` | 새로 넣음(g6 저장 행 읽기, 판정서 13.2 인용) |
| `C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368\rev26_post\control_evidence\judg_diff.py` | `f632012be0d83ed805a8b8323ba336b0294d76f3f8c5896d8059dff4864ae0fd` | 새로 넣음(HEAD 대비 바뀐 줄 범위·sha 계산, 이 보고의 표 근거) |

## 메인 처리 권고
1. `rev26_post/control_evidence/`에 파일 둘을 더했다. 이 폴더와 `rev26_post/`의 SHA256SUMS는 이 보고를 저장한 뒤 마지막으로 쓴다(`baseline_check.py write-sums`).
2. 판정서 커밋 전 순서: integrity-checker → (규칙상 필요하면) verif-protocol-auditor 판정서 커밋 직전 감사 → 커밋. 판정 후 감사의 메인 권고(`.gitattributes` `rev26_post/** -text`, 커밋 대상 목록, 커밋 뒤 `rev26-t26`·`rev26-t26b` lock 해제·정리)도 그대로 따른다.
3. 0.4절(결정 113~141 요지 표)에는 2026-11-26·27 결정 행을 넣지 않았다. 13절 머리에 적었다. 0.4절에도 넣으려면 결정 번호를 정해 알려 달라.
4. `00_docs/decision_log.md`와 로드맵에 "436.8 rev26 재판정: H-3 통과(한계 기록, G-5 = A), H-4 통과, rev26 기준 v5 종합 미달(사전 등록 증거 아님)" 기록이 필요하다(메인 몫).

## 공개 (행위 그대로)
- **Read**
  - 초안 `judgement_addendum_draft.md` 50~249행
  - 판정서 912~931행(삽입 위치 확인)
- **스크립트**(python-dev `-I -B`)
  - `g6_rows.py`: `las_k1/u3_g6_VB.json`·`u3_g6_V0.json`에서 두 키 행의 최상위 필드를 출력했다. 하위 dict는 키 이름만 출력했다.
  - `judg_diff.py`: `git show HEAD:<판정서>`와 작업 파일을 difflib로 비교했다.
- **Bash**
  - `ls`(`rev26_post`·`control_evidence`)
  - `sha256sum`·`wc -l`(지정 파일)
  - `git status`/`check-attr`/`ls-files --eol`(판정서 한 파일)
  - `cp`(scratchpad → `control_evidence` 두 파일)
- **Edit**: 판정서 다섯 곳 삽입
- **열지 않은 것**
  - 블라인드(`j9_runs\606f8713\cdry_a1\…`, `prelaunch_j9\ed6_inputs\x11\selection.json`)
  - 1회차 출력 `judge_rev26_335004a/`
  - `las_k1`의 g6 두 파일 밖 저장 결과
- 상위 폴더 검색·맨 이름 Glob은 하지 않았다. 판정 도구 실행 0, 종료한 프로세스 없음, 설치 없음.
- scratchpad `control-rev26e2\`의 스크립트(g5_peek*·g6_rows·judg_diff·shas* 등)는 사본이 `control_evidence/`에 있다. 정리는 메인 판단에 맡긴다.

사용한 스킬: 없음
