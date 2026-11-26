# 436.9 J-P3 판 7 판정서 커밋 직전 감사 (verif-protocol-auditor, 2026-11-26)

## 감사 요약
- 본 결과: 판정이 끝난 뒤라서 아래 자료를 열었다.
  - 판정 report 7개(`judge_60ebb4a4\*_a1\*.json`): status, status_basis, 실패 항목 detail(t_ready·t_back·gate·WARN 이름), 단위 verdict·role, cluster, count, J-P3·rev7_condition 요약, inputs sha, code_identity
  - `b03_untested_paths_main.json`의 라운드·트리거 계수
  - `.done` 8개, chain log 3개, `main_checks` 기록의 마지막 줄
  - `p51_record_compare.json`의 status
  - 큰 파일 4개와 단계 SUMS 해당 줄의 sha
  - 원인 분석 원문 전체
- 대상: 판 7 판정서 `06_analysis\02_control\j_p3_cause\jp3_ed7_judgement_8a2a52ce.md`(sha256 `dec184b3…`, 미추적)
  - control-expert 초안을 메인이 세 곳 고친 판이다.
  - 시점: 판정 후(판정서 커밋 직전)
- 기준 문서
  - 봉인 명세 `jp3_remedy_spec_v7.md` rev 6: `10902ffd…`(`.sha256`과 일치)
  - 정오 1 `jp3_remedy_spec_v7_erratum1.md`: `74c49bda…`(`.sha256`과 일치)
  - 판 6 명세 `jp3_remedy_spec_v6.md`: 396~401·436~445·484~491·770~777행
  - `06_analysis\03_hydraulic\coupled\v5\v5_criteria.md`: 214·218·233·234행
  - 판정 후 감사 `a8e409b4…`, 실행 전 감사 `dcc6937a…`, 원인 분석 `177950d1…`. 세 값 모두 판정서 인용과 같다.
- **판정: 차단 0 / 판정서 확정 전 수정 3 / 기록 9**
  - **커밋 가능.** 판정 결과(판 7 불합격)와 그 근거 수치는 report·`.done`·chain log와 모두 맞는다.
  - 확정 전 수정 3건은 문면 정정이다. 결과를 바꾸지 않으며, 커밋 전에 반영하기를 권한다.
  - 사용자 결정 넷이 판정서에 반영돼 있다.
    - 불합격과 그 근거: 0절 4~10행
    - J-P3 경로 2 미실행: 24·361행
    - 12a·12b 미실행: 21·209행
    - 판 8 방향 A: 34·325행

## 발견 사항 (심각도순)

### [판정서 확정 전 수정][I] F-1 7.5절의 "T4h npz 1752개"는 틀렸다. 실제는 npz 1749개와 `*.partial.jsonl` 3개다. 이 3개는 LOCAL_ONLY 목록에도 백업에도 없다
- 근거
  - 판정서 322행: "T4h npz 1752개는 판 6과 같이 git 제외(로컬)이고 단계 폴더 SHA256SUMS가 sha를 고정한다"
  - 디스크에서 센 npz는 1749개다: confirm 195, cases 10, probe 114, t8 44, j9main 388, l1ref 538, sens 460.
  - `git ls-files --others --ignored --exclude-standard -- j9_runs/8a2a52ce/`의 ignore 파일은 1756개다. 큰 파일 4개와 npz 1749개를 빼면 다음 3개가 남는다.
    - `l1ref_a1\L1_VBM0.json.partial.jsonl`(6,806,398 B)
    - `l1ref_a1\L1a_VBM.json.partial.jsonl`(74,111,779 B)
    - `l1ref_a1\L1a_VBM0.json.partial.jsonl`(4,126,165 B)
  - 세 파일은 원래 있던 규칙 `.git/info/exclude:37 *.partial.jsonl`에 걸린다(`git check-ignore -v`).
  - 단계 SUMS에는 세 파일이 있다. `l1ref_a1\SHA256SUMS`의 `L1a_VBM.json.partial.jsonl`은 `5e6bd70c…`다. 그러나 `8a2a52ce_LOCAL_ONLY.SHA256SUMS`(4항목)와 백업 `~\.claude\backups\outrigger-ed7\j9_runs_8a2a52ce\`(4개 + 목록)에는 없다.
  - `baseline_check sums --repo`의 `cited_ignored` 합도 같다: l1ref 544, sens 461, confirm 195, j9main 388, t8 44, cases 10, probe 114, 합계 1756.
- 실패 시나리오
  - 판정서 숫자가 디스크와 다르다(1752 대 1749).
  - 다른 checkout이나 백업에서 l1ref 단계 SUMS를 대조하면, 판정서가 "로컬"이라고 밝히지 않은 3개가 누락으로 나온다. 그 3개는 백업도 없다.
- 권장 조치(메인)
  - 322행을 다음처럼 고친다: "T4h npz 1749개와 `l1ref_a1`의 `*.partial.jsonl` 3개(L1_VBM0·L1a_VBM·L1a_VBM0, 기존 `*.partial.jsonl` 제외 규칙)는 git 제외(로컬)이고 단계 폴더 SHA256SUMS가 sha를 고정한다"
  - 세 파일을 LOCAL_ONLY 목록·백업에 넣을지는 메인이 정한다. 넣으면 LOCAL_ONLY 목록의 sha `d49f40d1…`가 바뀌므로 322행도 함께 고친다.

### [판정서 확정 전 수정][T] F-2 메인이 고친 뒤에도 "예정", "아직 감사 안 받음", "초안" 문구가 남아 있다
- 근거
  - 319행: "(판정 후 감사 M-2, 예정)". 같은 절 322행은 처리 결과를 적었다.
  - 374행: "M-2 → 7.5절(로컬 전용 예정, sha는 메인이 채움)". sha는 이미 채워졌다.
  - 386행: "이 판정서는 아직 판정서 감사를 받지 않았다. 메인이 `judgement_checklist.py`로 대조한다."
  - 1행 제목: "(2026-11-26, control-expert 초안)"
- 실패 시나리오: 커밋된 판정서가 자기 상태(처리 완료, 감사 완료)와 다른 문장을 담는다.
- 권장 조치(메인)
  - 319·374행에서 "예정"과 "메인이 채움"을 지운다.
  - 386행은 "판정서 감사 `ed7_design/postjudge/audit_judgement_ed7_8a2a52ce_20261126.md`, judgement_checklist 결과 경로(아래 R-8)"로 바꾼다.
  - 제목에는 "control-expert 초안, 메인 수정"을 적는다.

### [판정서 확정 전 수정][I] F-3 이 감사의 블라인드 절차 공개를 7.4절에 더한다(O7-27)
- 근거: 아래 「실행한 검증」의 블라인드 절차 (a)~(c)
  - (b)는 지시 규칙 위반이다. 블라인드를 품은 상위 폴더 `j_p3_cause`를 Grep의 `path`로 썼다.
  - (c)는 저장소 루트 전체를 순회해 합계 건수만 출력했다.
- 권장 조치(메인): 7.4 표에 다음 행을 더한다. "O7-27 | 판정서 감사 | (a)~(c)" 내용은 아래 원문을 그대로 쓴다.

### [기록][R] R-1 judgement_checklist의 missing 2건은 실질적으로 충족됐다
- D021(봉인 228행 "`JP3_SPEC_EDITION_V7` = 봉인본 sha 앞 8자, 실행 커밋 C의 sha를 정오나 판정서에 적는다")
  - C 전체 sha는 판정서 39행에 있다. 값 `"10902ffd"`는 120행에 ③ 기록 줄의 `spec_edition`으로 있다.
  - 상수 이름만 없다. 원하면 120행에 "(`JP3_SPEC_EDITION_V7`)"을 덧붙인다.
- D144(정오 1-20 224행 "report의 `rev7_condition.summary.no_event_lines`와 판정 등급 줄 수가 다르면 적는다")
  - 12a·12b가 미실행이라 report가 없다. 7.2절 13(269행)이 "12a·12b 미실행이라 없다"고 적었다.
- ambiguous 113건을 원문으로 보았다.
  - 봉인 12절 1024~1067행의 34항목은 7.1절 1~34와 하나씩 대응한다. 1028~1031행은 5번, 1043~1046행은 17번, 1050~1051행은 21번, 1059~1062행은 29번에 묶였다.
  - 정오 1 「판정서에 옮길 것」 17항목(229~249행)은 7.2절 1~17과 대응한다.
  - 1-2 조건 3(75행, 판 6 방식과의 차이), 1-6(103행), 1-7(113·118·119행, P5-1 경로·결과), 1-16(189행, 기록 설정 침범), 1-15·1-4 번호(90·183행)도 판정서에 있다.
  - 빠진 공개는 R-2 하나뿐이다.

### [기록][R] R-2 봉인 11절 1021행의 "공개" 문장이 판정서에 없다
- 원문: "공개: 판 6 경로 2 작성자(dynamics-expert)가 판 7 설계 검토(D1·D2)를 맡았다. 그 검토는 경로 2 자료를 열지 않았다고 밝혔다(d7 머리말)."
- 판 7 경로 2는 미실행이라 판정에는 영향이 없다. 그러나 이 문장은 공개 동사로 정해져 있다. 9절에 한 줄 더하기를 권한다.

### [기록][R] R-3 따옴표 안의 인용이 원문과 글자 그대로는 아니다(뜻은 같다)
- 10행 "판정 실패는 멈추고 묻는다, 재실행하지 않는다"
  - 원문 판 6 400행: "판정 실패(종료 1)는 멈추고 사용자에게 묻는다. 재실행하지 않는다(4a-5 5.1)."
- 84행 "j9_main에는 적용하지 않음"
  - 원문 판 6 488행: "적용하지 않는 것: `VBL`·`VBL0`·`LSL1~4`(j9_main)…"
- 7행 "H-2(VB에서 J3·J7 실패 1건 이상)"
  - 원문 `v5_criteria.md` 214행: "VB에서 5절 구분 기준 J1, J2, J3, J4, J5, J7 실패 1건 이상, 또는 위상 산포 안 실패가 V0에 없던 행"
  - 판정서는 걸린 항목만 적었다.
- 5·6행(판 6 443행, `v5_criteria` 234행)은 원문과 같다.
- 권장: 따옴표를 원문 그대로로 바꾸거나 따옴표를 뗀다.

### [기록][E] R-4 원인 절의 F2 인과 문장과 7.1절 11의 "실현됐다"는 해석이다. 해석 표시가 약하다(판정은 바뀌지 않는다)
- 165~167행(F2): "그래서 S7 READY 기저가 +5.5 s다 … 그래서 재레벨이 … 바뀌었다"에 추정이나 해석 표시가 없다. 원인 분석 3.2절은 같은 내용을 "해석:"(132행)으로 적었다.
  - F1(159행 "추정")·F3(171행 "소거법 추정")·4절 149행("추정")은 표시돼 있다.
- 229행 "FL-Fs4 위험 **실현됐다**"
  - 사실: 그 줄이 `U832_pair_union`으로 실패했고 o0.0이다. report `confirm.json` lines에서 `failed_gates`·`offset_s` 0.0을 확인했다.
  - 그러나 봉인 1037행의 위험은 "U832가 o0.0에 묶인 기전이면 거짓 실패가 오른다"이다. 기전 확인은 없다.
- 판정 결과를 바꾸는 문장은 없다.
  - 5절 153행이 "판정 결과는 바뀌지 않는다"고 적었다.
  - 85행 "강성 경고 14를 빼도 결론은 같다"는 결론을 유지하는 문장이다.
  - 8절은 "판정 아님"으로 표시돼 있다.
- 권장
  - 166·167행 앞에 "(해석)"을 붙인다.
  - 229행은 "위험 시나리오와 같은 꼴의 실패가 났다(기전 미확인)"로 바꾼다.

### [기록][I] R-5 판정서 O7-25(310행)가 원인 분석 원문의 자기 공개 문단보다 넓다
- `cause_analysis.md` 286~290행에 적힌 것
  - "블라인드 경로는 열지도, 검색하지도 않았다"
  - "`j9_runs\606f8713` 바로 아래 폴더 이름 목록을 한 번 봤다"
- 판정서 O7-25에는 다음이 더 있다. 출처는 `ed7_j9fail_8a2a52ce\handback_judgement_draft_full.md` 310·397~400행이다.
  - `j9_runs` 최상위 목록
  - `j9_runs\79495405` 하위 폴더 목록
  - C worktree 루트를 `path`로 쓴 Grep 2회
- `cause_analysis.md`는 판정서가 sha(`177950d1…`)로 인용하므로 고치지 않는다.
- 권장: O7-25 끝에 "원인 분석 원문 공개 문단(286~290행)보다 이 행이 넓다. 출처 `handback_judgement_draft_full.md` 397~400행"을 붙인다.

### [기록][I] R-6 b01·b02는 콘솔 출력만 있다. `ed7_j9fail_8a2a52ce\`에는 SHA256SUMS가 없다
- 판정서 52행은 "이 판정서용 b01~b03"을 근거로 든다. 그런데 저장된 출력은 `b03_untested_paths_main.json` 하나다.
- b01·b02가 낸 사실은 report에서 다시 읽을 수 있다. 이 감사가 report에서 직접 대조했다(재집계 표). 그래서 근거가 비지는 않는다.
- 원인 분석 10절 282행: "SHA256SUMS는 만들지 않았다(메인이 근거 폴더로 고정할 때 작성)"
- 권장: 커밋 전에 메인이 `baseline_check.py write-sums`로 이 폴더의 SUMS를 만든다(CLAUDE.md §1 근거 폴더 규칙).

### [기록][I] R-7 커밋 대상에 50 MB를 넘는 미추적 파일 2개가 남는다(10⁸ B 미만)
- `j9main_a1\j9_main.jsonl` 78,844,771 B
- `confirm_a1\confirm_g1.jsonl` 60,076,418 B
- 둘 다 ignore가 아니라 그대로 커밋된다. 원격 한도(10⁸ B) 안이라 막히지는 않는다. 원격의 50 MB 경고가 날 수 있다.

### [기록][I] R-8 judgement_checklist 결과가 세션 scratchpad에만 있다
- `…\scratchpad\main-judge\judgement_checklist_r1.md`
- 판정서 386행이 이 대조를 언급한다. CLAUDE.md §1의 "scratchpad에만 있는 근거" 규칙에 해당한다.
- 권장: 커밋 전에 `ed7_design\postjudge\`로 복사한다.

### [기록][R] R-9 7.1절은 22항목을 "그대로"(봉인 문면 참조)로 옮겼다
- 봉인본이 sha로 고정돼 있어 참조로 옮기는 것은 성립한다. 34항목 대응은 R-1에서 확인했다.
- 판정서 쪽에서 판 7 실측을 덧붙인 항목(#4·5·8·11·13·17·18·22·24·26·30)의 수치는 모두 report·b03과 맞는다(재집계 표).

## 판정서 수치 대조표 (C·T축)
| 판정서 위치 | 판정서 값 | 대조 값(출처) | 판단 |
|---|---|---|---|
| 48행 report sha 앞 8자 | 58065781·1a0c6327·c5cdd453·a3e61d78·02175169·0b87b60b·b178de9e | 같음(파일 해시) | 일치 |
| 47행 판정 SUMS | `c7d9548a…`, 14항목 | 같음. `baseline_check sums` 종료 0, 14항목 | 일치 |
| 40행 code_identity | head T′, `is_clean` true | 7개 report 모두 `60ebb4a4`·true. T′ worktree 지금 0항목, lock 사유 = HEAD(`worktree_locks` 종료 0) | 일치 |
| 49행 고정 입력 | 9ad74990·f7754a69·be930b75·684054ab·4e80e69b·1107b309·189dbb13, pinned | report `inputs` 같음, `pinned: true` | 일치 |
| 14행 l1ref | 167·167·102·102, 문제 0, 출처 7항목 | 같음. `identity_sources` 키 7개가 116행 목록과 같음 | 일치 |
| 15행 t8 | 22쌍, 태그 VBM `…P3X_LAS_K1_LSB` 22, VBM0 `…LAS_K1_LSB` 22 | `judged_pairs` 22, `controller_tags` 같음, `fallback_pairs_record` 0 | 일치 |
| 16·130행 cases | 10행, 조건 줄 10·읽기 158·침범 0 | 같음 | 일치 |
| 17행 probe-repro | 114/114, 40단위 + D 24 차이 0 | `compared` 114, `differing` 0, `units` 40·`d_lines` 24·차이 0 | 일치 |
| 18·106~111행 confirm | 기회 168, 실패 3(줄 이름·사유), D 고정 0, total 3 = k 3, FAULT 0, V0 결측 0, J-P3 171·조건 줄 167·읽기 2372·침범 0, U832 o0.025·o0.075·o0.075 | 같음(`count`, `lines`의 `failed_gates`, `u832_record`, `rev7_condition.summary`) | 일치 |
| 19·77~82행 j9main | VB 15(J7 14·J3 1), R12 Fs8 8·R14 2·R7 4, S7 e0.002 77.0 → 100.7, L-a 2·L-b 1(38.65 → None), 기준선 93·counted 0, S8 n/a 20, R15 구분됨 | `J_vs_V0.VB.items` 15건 행·위상·detail 같음, `L-a`·`L-b` 같음, 18건 모두 `base_other_phase_has_it` 거짓 | 일치 |
| 126행 j9main J-P3 | 200, head-only 188, 198/2791/0 | 같음 | 일치 |
| 20·90~101행 sens | 460 = 40 + 144 + 276, 재현 40 차이 0, 다위상 VBMslow S7, 단독 1, 실패 3건 값, 기록 실패 3, 예외 79 | role 수 같음, `cluster` 같음, 단위 `failed_items` 값 같음, `j7_stiffness_exempt` 79 | 일치 |
| 127~128행 sens J-P3 | 104/80/99/1414/0, 기록 156/120/151/2124/0, `runs_with_breach` 0 | 같음(`rev7_record_only` 156, `runs_with_breach` 0) | 일치 |
| 2절 시각·wall_s | 02:22:42 … 12:53:21, 4384·265·112·875·1670·2697·3413 s | chain_ed7_a1~a3.log `[start]`·`[end]`·`[pause]`·`[identity]` 줄과 같음 | 일치 |
| 62·64·66·67행 판정 시각 | 03:58:48~52, 11:07:46, 12:58:14·12:58:22, SUMS 12:58:42 | report·console.log·SUMS mtime 같음(미추적이라 mtime뿐, [추정] 수준 근거) | 일치 |
| 46·70행 `.done` | 8개, exit 0, commit C, `_a1`, `.stop*` 없음 | 같음(8개 모두 exit 0, `commit` = C, `folder` `_a1`, `previous_attempts` 빈 값, `.stop*` 0) | 일치 |
| 39~43행 커밋 | C 부모 b46bdf8f, T → T′ 계보, e241638d, 265dc641 00:14:27, eba3d0f5 02:22:24 | `git log` 같음 | 일치 |
| 43·198행 실행 설정 | `9ede99fb…`, eba3d0f5로 추적 | 작업본 blob = `eba3d0f5:` blob `e16c907d…`, sha `9ede99fb` | 일치 |
| 44행 러너 | `bc83c834…` | 같음 | 일치 |
| 261행 P5-1 | `2eb71be6…`, `equal` | 같음, 추적됨 | 일치 |
| 144·231·242행 b03 | D6 라운드 1476·1836·1024·96, 역순 0, 안 열림 0, 판정 불가 0, A_ib 트리거 123·184·31, 래치·n_rev·보호 0, 완료 미상 0, retract WARN·INFO 0 | `b03_untested_paths_main.json` 같음 | 일치 |
| 322행 LOCAL_ONLY | 4개, 목록 `d49f40d1…`, 백업 | 목록 sha 같음. 4개 sha·크기가 목록·단계 SUMS·백업 크기와 같음. 4개 `!!`(ignore), 목록 파일 `??`(ignore 아님, 커밋 가능). `baseline_check sums --base repo-root` mismatch 0·missing 0 | 일치(npz 수는 F-1) |
| 322행 npz 수 | 1752 | 디스크·ignore 모두 1749(+ partial 3) | **불일치 F-1** |
| 50~52행 감사·분석 sha | dcc6937a·a8e409b4…·177950d1 | 같음 | 일치 |
| 판정서 형식 | – | LF(CR 0), BOM 없음, 끝 LF, `text: unset`(-text), `{NAME}` 0. 꺾쇠 5개는 모두 백틱 안 경로 꼴(`<하위 명령>_a1`·`runs.<stem>`·`<jsonl…>`·`<메인>`). `--skip-inline-code`로 0 | 형식 맞음 |

- 판정 후 감사 M-1·M-2와 R-1~R-14의 반영(10절 372~384행 대응표)을 원문과 대조했다. 모두 판정서에 있다.
  - M-1: 24·123~133·361~364행
  - M-2: 319~322행. 문구는 F-2 참조.
  - R-7: 6.1절에는 key_presence 부분만 옮겼다. 빈 집합 표는 감사 원문에 남는다(기록).
- 정오 1 17항목, 봉인 12절 34행, O7-14~O7-26은 빠짐없다. 이 감사 몫 O7-27은 F-3이다.

## 확인 필요
1. F-1의 partial 3개를 LOCAL_ONLY 목록과 백업에 더할지, 판정서 문장만 고칠지(메인 판단). 더하면 목록 sha가 바뀌므로 322행도 함께 고친다.
2. 원인 분석 「확인 필요 3」(`WARN_PROBE_STIFFNESS_OUT_OF_RANGE`를 공칭 VBM에서 J7 실패로 둘지)은 판정서에 결정으로 적혀 있지 않다. 판 8 명세 몫이며 판 7 판정에는 영향이 없다. 판 8 명세 작성 때 사용자 결정으로 올린다.

## 위임 필요
- 없음. 도구 결함은 찾지 못했다.
  - 참고: `worktree_locks.py --worktree <이름>`은 cwd 기준 상대 경로로 풀려 종료 2가 났다. 절대 경로로는 종료 0이다. 사용법 문제다.

## 메인 세션 권고(커밋 전)
1. F-1·F-2·F-3을 판정서에 반영한다. R-2~R-5는 선택이다.
2. `ed7_design\ed7_j9fail_8a2a52ce\`에 `baseline_check.py write-sums`로 SUMS를 만든다(R-6).
3. judgement_checklist 결과를 `ed7_design\postjudge\`로 복사한다(R-8). 이 감사 원문도 같은 폴더에 저장한다. 그 폴더 SUMS는 마지막에 만든다.
4. 커밋 직전에 `git status --ignored -- 06_analysis/02_control/j_p3_cause/j9_runs/8a2a52ce 06_analysis/02_control/j_p3_cause/j9_runs/8a2a52ce_LOCAL_ONLY.SHA256SUMS`를 다시 돌린다.
   - 큰 파일 4개와 partial 3개, npz가 `!!`인지 본다.
   - 목록 파일과 판정서·report·단계 SUMS가 `??`(추가 대상)인지 본다.

## 검사하지 못한 것
- 판정 값 자체의 재계산(J-P3 rev 6/7, 조건 읽기 침범, 감도·j9main 재집계)은 이 감사 범위가 아니다. 판정 후 감사 R-1의 독립 재집계를 근거로 두었다. 이 감사는 판정서 수치를 report와 대조했다.
- O7-20의 행위자(python-expert)는 근거 파일 `handback_run_config_prep.md`에 이름이 없다. 메인 기록을 따랐다.
- O7-25·O7-26의 행위 자체(control-expert 대화)는 원문 transcript로 확인하지 않았다. 초안 원문 hand-back의 자기 공개만 대조했다.
- P5-1 33/33 건수는 status `equal`만 보았다.

## 실행한 검증
- 인터프리터: python-dev `C:\ProgramData\miniforge3\envs\python-dev\python.exe -X utf8 -I -B`, `MKL_THREADING_LAYER=TBB`. 프로젝트·판정 모듈은 import하지 않았다.
- verif 도구
  - `placeholder_scan`(판정서, `--pattern-set both`): 종료 1(백틱 안 경로 꼴 5)
  - `placeholder_scan`(판정서, `--skip-inline-code`): 종료 0
  - `baseline_check sums --no-git`(단계 폴더 8개 + `judge_60ebb4a4`): 모두 종료 0
  - `baseline_check sums --repo`(단계 7개): `cited_ignored` 계수, 커밋 전이라 종료 1은 예상대로
  - `baseline_check sums --base repo-root`(LOCAL_ONLY): mismatch 0·missing 0
  - `seal_check --quoted --hash-files`(인용 파일 20개, `--min-hex-len 13`, `--no-git`): 전체 sha256 인용 모두 해석. 미해석 2는 커밋 sha이고 `git log`로 따로 확인
  - `worktree_locks`(절대 경로): 종료 0
- 즉석 스크립트(scratchpad `verif-ed7jdoc\`)
  - 내용: checklist 축약, report 값 추출 3종, `.done`·mtime, ignore 집계, npz 계수, P5-1·러너·main_checks
  - 보고 전에 폴더째 지웠다.
- git 조회: `status --short`, `log -1`, `show --stat`, `hash-object`, `rev-parse`, `ls-files`(`--error-unmatch`·`--others --ignored`), `check-attr`, `check-ignore -v`, `worktree list --porcelain`, `config --get core.autocrlf`(true. 대상 파일은 -text라 보호됨)
- 메모리: `audit_pitfalls.md`·`MEMORY.md`에 프로젝트와 무관한 함정 1항목을 더했다.
- 블라인드 절차 공개(판정서 O7-27로 옮길 것)
  - **(a)** `Get-ChildItem <j_p3_cause> -File -Filter "jp3_remedy_spec_v7*"`(비재귀)를 1회 돌렸다. 최상위 명세·정오와 그 `.sha256` 4개 이름이 출력됐다.
  - **(b)** Grep 1회의 `path`로 블라인드를 품은 `j_p3_cause`를 썼다. glob은 `jp3_remedy_spec_v[67]*.md`, 패턴은 `ret_breach|_flag`, 건수 모드였다.
    - 출력은 `jp3_remedy_spec_v7.md:1` 한 줄뿐이다.
    - ripgrep이 `j9_runs` 아래를 순회했을 수 있다(O7-19·O7-22와 같은 종류).
    - 지시 규칙 위반이다.
  - **(c)** `baseline_check sums --base repo-root`(LOCAL_ONLY 목록 검증)가 저장소 루트 전체를 열거했다. 블라인드 폴더와 worktree 사본을 포함했을 수 있다. 출력은 합계 `unlisted 11635` 하나이고 이름은 없다.
  - 그 밖의 Glob·Grep은 블라인드를 품지 않은 하위 경로를 직접 지정했다: `j9_runs\8a2a52ce`, `ed7_design\…`, `ed7-impl\03_src`, 개별 파일.
  - 블라인드 경로(606f8713 `cdry_a1\VBK_c92*`·`VBK_c93*`·`logs\`, worktree 사본, 판 6 `selection.json`)는 Read·Grep·Glob 대상으로 지정하지 않았다.
- 최종 판정 직전 확인: 판정서 sha `dec184b3…`는 시작 snapshot과 끝 verify에서 같다. 감사 중 판정서는 바뀌지 않았다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_ed7_judgement_8a2a52ce.md dec184b3…, jp3_remedy_spec_v7.md 10902ffd…, jp3_remedy_spec_v7.md.sha256 8cfd1981…, jp3_remedy_spec_v7_erratum1.md 74c49bda…, jp3_remedy_spec_v7_erratum1.md.sha256 b1cfb220…, audit_postjudge_ed7_steps2_8_20261126.md a8e409b4…, cause_analysis.md 177950d1…, audit_prerun_main_ed7_20261126.md dcc6937a…, 8a2a52ce_LOCAL_ONLY.SHA256SUMS d49f40d1…, SHA256SUMS c7d9548a…, cases.json c5cdd453…, confirm.json 02175169…, j9main.json 0b87b60b…, l1ref.json 58065781…, probe-repro.json a3e61d78…, sens.json b178de9e…, t8.json 1a0c6327…, confirm.done dbe72606…, impl_cases.done f8a585c8…, impl_probe.done a06b6e6b…, impl_scope.done a354ce2a…, impl_t8.done b0ac99c3…, j9main.done 303091a0…, l1ref.done 9d21d982…, sens.done 9e3f35ad…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
