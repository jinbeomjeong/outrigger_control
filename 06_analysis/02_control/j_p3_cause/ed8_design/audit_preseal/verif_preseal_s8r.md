# S8-R 봉인 직전 감사 (verif-protocol-auditor, 2026-11-26)

## 감사 요약
- 본 결과: 판 8 설계 입력 자료만 봤다. 판정 대상 결과(census·G′·판 8 처리 줄)는 아직 없다. 본 것은 다음과 같다.
  - `control_level_deadlock/probe_8a2a52ce/report.md` 전체(P8-14 수치)
  - `h3p/report.md` 전체
  - `h3p_selection.json` 앞부분(sha 앞 8자, pair_union, t_ready_back)
  - P8-9·h3p·P8-14 `raw/runs.jsonl`의 구조(키 이름, 팔별 줄 수)와 `commands_sha256` 같음 여부. 해시 값은 출력하지 않았다.
  - 판 7 `j9_runs/8a2a52ce/j9main_a1/j9_main.jsonl`의 `job` 필드(설정별 건수, 회귀 키 3개 존재 여부)
  - 저장 `main.jsonl`의 `event_output` 키 이름과 `fast` 키 유무 건수
  - 키 파일 4개의 구조와 건수
  - 세션 subagent transcript에서 뽑은 도구 호출 경로, 그리고 P8-14·P8-9′ 규칙 문장(설계 입력 수치 포함, 이미 명세에 있는 값)
- 대상
  - S8-R 초안 `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\jp3_remedy_spec_v8_rules.md`: 개정 2, sha `5fdc0d7c`, 미추적, `.sha256` 없음. 감사 시작과 끝에 sha가 같았다.
  - 시점: 실행 전(봉인 직전).
  - 이어받는 기준(모두 커밋 blob과 바이트 같음)
    - `jp3_remedy_spec_v7.md` `10902ffd`(e241638d)
    - `jp3_remedy_spec_v7_erratum1.md` `74c49bda`(265dc641)
    - `jp3_ed7_judgement_8a2a52ce.md` `994102b7`(173b7c20)
- 판정: **차단 1 / 실행 전 수정 9 / 기록 8**. 차단 B-1(층 E 판별 키가 C-J·C-S V0 줄에 없음)을 고치기 전에는 봉인하지 않는다. 실행 전 수정 항목은 봉인 문면에 들어가므로 봉인 전에 고치기를 권한다.

## 발견 사항 (심각도순)

### [차단][R·E] B-1. 층 E 정의가 읽는 `event_output.fast`가 C-J·C-S V0 줄에 하나도 없다
- 근거
  - 명세 6.3: `jp3_remedy_spec_v8_rules.md:250`("V0 짝 줄이 빠른 사건(`event_output.fast` 참; 저장 격자 run은 같은 정의의 run 최상위 필드, Y8-6)"), `:254~255`(키 경로, "결측: … 키가 없으면 그 단계 `setting_defect`"), `:212`(C-J·C-S 층 입력).
  - 독립 확인: 저장 `06_analysis/03_hydraulic/coupled/v5/main.jsonl`(sha `9ad74990…`)의 사건 줄 603개 모두 `event_output`에 `fast` 키가 없다(0/603). `event_output` 키 30개 목록에도 없다.
  - python-expert 0c 보고(`ed8_design/python_0c_keys/report.md:5~19`, 감사 중 17:02~17:05에 생김)도 같은 결과다.
    - C-J는 사건 줄 200/388, C-S는 260/460이 `event_output.fast` 결측이다.
    - 격자 run(C-D·C-G)은 run 최상위 `fast`(bool)가 192/192·171/171 있다.
    - 생성 코드는 `r67_g1_screen.py` 436행 `"fast": is_fast(ev)`, 정의는 120~121행 `depth / ramp > V_MAX`다.
- 실패 시나리오
  - 문면대로 구현하면 C-J·C-S 사건 단위가 모두 `setting_defect`다. 그러면 census가 판정 불가가 되고 S8-C를 봉인하지 못한다.
  - 결측을 거짓으로 읽게 구현하면 C-J·C-S의 E층이 비고, 5.2의 "빈 층 = 해당 없음"으로 **E칸이 조용히 통과한다**. U832 E 실패가 N으로 옮겨 가 허용 수 0 판정의 칸 배정이 바뀐다.
- 권장 조치(control-expert 문면, 층 정의는 사용자 결정 4이므로 확인 필요 Q-1)
  - main.jsonl 짝의 빠른 사건 여부를 job twin 사건 이름(없으면 사례 기본값, `verdict_cases.py` 153~171)으로 정한다. 함수는 `r67_g1_screen.is_fast(r67.EVENTS[event])`이고, 격자 `fast`와 같은 함수다(0c 보고의 가능성 (가)).
  - 저장 격자 키 경로를 `runs[int(run_id)].fast`로 명시한다.
  - 사건 행 키 요구는 `reapproach_starts` 하나로 줄인다.
  - 1절에 0c 결과(F8-20)를 더하고, 4절 0c 행을 "끝남"으로 고친다.
  - 설계 근거 표에 `python_0c_keys/`를 더한다.

### [실행 전 수정][R] M-1. C-J 설정 대응 "VB → VBN, LS<n> → LSN<n>"이 실제 키 집합과 다르다
- 근거
  - `:206`.
  - `j9_runs/8a2a52ce/j9main_a1/j9_main.jsonl`(git 추적, sha 앞 `c89ec827`)의 `job.setting`은 `VBM` 100, `LSM1~4` 각 72다. 388줄 모두 서로 다른 job이다.
  - C-S(`:207` VBM<key>)와 C-G(`:209` VBM)는 VBM으로 적었다.
- 실패 시나리오: 문자열 대응을 문면대로 쓰면 고른 줄이 0이 된다(판정 불가). 도구가 다르게 해석하면 문면과 도구가 어긋난다.
- 권장: "VBM → VBN, LSM<n> → LSN<n>"으로 고치고 j9_main.jsonl 전체 sha를 인용한다(control-expert).

### [실행 전 수정][R·E] M-2. P8-16(검토 팔 재현 관문)의 기준·완결성·멈춤 동작이 덜 정해졌다
- 근거: `:357`, `:189`, `:196`, `:332`.
- (가) 키 집합
  - "P8-9 20키 + P8-14 27키"라고 적었지만, P8-9 20키는 모두 P8-14 VBM 23키 안에 있다(독립 대조). 합집합은 27키다.
  - P8-14 VBM 키 가운데 P8-9 밖 키는 R2 e0.001, S4 e0.002, S8 e0.0이고, 셋 다 판 7 j9_main VBM 줄에 있다(본 키).
  - h3p `raw/runs.jsonl`은 7줄뿐이다. 나머지 13키의 H3′ 기준은 P8-9 H3·A 줄에서 옮겨 온 값이다.
  - P8-14 B팔 `commands_sha256`은 h3p 줄과 오프라인 대응값에 **20/20 같다**(재계산).
  - 따라서 기준 원천은 P8-14 `raw/runs.jsonl` 하나(B 27줄, L2 27줄)로 적으면 된다.
- (나) r79 경로 실행 조건이 고정되지 않았다. P8-14 보고 94~99행 기준으로 다음이 있다.
  - 자체 계획 파일 `raw/plans/P814-{B,L2}-VBKM0.json`
  - `R79_ROD_MODEL=plant_truth`
  - seed s40·s41
  - 설정 이름 `P814-<팔>-VBKM0`
  - VBK 워커의 `sys.argv[1]` 루트 처리

  같은 비트를 내려면 이 입력들을 sha로 고정해야 한다.
- (다) 완결성
  - "27/27·27/27 줄이 해시와 함께 있어야 하고, 결측·오류 줄은 실패"라는 문장이 없다.
  - 대상 줄이 0이거나 일부만 돌면 "다른 줄 0"으로 읽힐 수 있다.
- (라) 멈춤 동작이 서로 어긋난다
  - P8-16의 "판정(관문, 4단계)"와 "다르면 멈춤(구현 결함, C8 전에 고침)"이 함께 적혀 있다.
  - 그런데 4단계는 C8에서 돌고(`:189`), 판정 실패는 "멈추고 묻는다. 재실행하지 않는다"(`:196`)이며, "C8이 바뀌면 4단계부터 다시"(`:332`)다.
- 권장(control-expert 문면, python-expert 구현)
  - P8-16을 구현 커밋(C8 전)에서 먼저 도는 관문으로 두고, 4단계에서 C8로 다시 돈다.
  - 4단계 실패 처리(멈춤, C8 교체 허용 여부)를 한 문장으로 정한다.
  - 기준 파일을 인용한다: `control_level_deadlock/probe_8a2a52ce/raw/runs.jsonl` sha `89efe66fc521f6d58c8c90304a9258747eef45d422ef43666a53f5ddd7fa9418`, 폴더 `SHA256SUMS` sha `1f4de0728d1e17e63cd2fe7d33c16392f053e8e40e012f7d7f7cf859eadad0d6`, 계획 파일 sha.
  - h3p를 보조로 남기면 h3p `raw/runs.jsonl` `06b9d8fc…`(SUMS `ff199285…`)와 P8-9 `raw/runs.jsonl` `3c0979f5…`(SUMS `a0468d1b…`)도 인용한다.

### [실행 전 수정][E] M-3. G′ 판정 가능성 규칙끼리의 우선순위가 없다
- 근거
  - `:282`: "1차 별칭 뒤 V0 통과 기회가 N 200 이상, E 16 이상. 미달이면 그 층은 판정 불가(멈추고 묻는다)"
  - `:283`: "한 층의 기회가 0이면 해당 없음"
- 실패 시나리오: E 기회 0은 두 문장에 모두 걸린다. 도구가 `:283`을 먼저 적용하면 n_min 정지가 사라지고 E가 "해당 없음"으로 지나간다.
- A/A 기회 0도 같다(7.4). N층은 CP95 상한이 1이 되어 암묵적으로 멈추지만, E층은 "실패 2 이상" 규칙만 있어 n_AA = 0이어도 멈추지 않는다.
- 권장: "n_min 점검(5단계)이 해당 없음 규칙보다 먼저"와 "층별 n_AA = 0이면 멈추고 묻는다"를 명시한다(control-expert, 필요하면 stats-design-expert).

### [실행 전 수정][S] M-4. `<S8R_CENSUS_KEYS_SHA256>`는 봉인 때 채울 수 없다
- 근거
  - `:210`, `:383`("키 생성 뒤(Y8-6)").
  - `census_keys_ed8.json`은 아직 없다(ref_check `ref_missing`).
- 실패 시나리오: 봉인 뒤 이 자리를 채우면 봉인 파일 바이트가 바뀐다. 그러면 `.sha256`이 깨지거나, 개정 없이 봉인 문면이 바뀐다.
- 권고
  - S8-R에는 구성 파일과 sha(be930b75·684054ab·d_grid blob a995abff·j9_main), 대응 규칙, 합계 1043만 두고, 자리를 "C8 상수 `ED8_KEY_FILE_SHA256`과 S8-C에 기록"으로 바꾼다. 판 7의 `ED7_KEY_FILE_SHA256` 방식과 같고, 11.1에 이미 적혀 있다.
  - census 키 파일이 구성 파일에서 결정적으로 다시 만들어진다는 시험을 P8-10에 넣는다.
- 나머지 두 자리는 봉인 때 채워도 된다
  - `<S8R_ED7_JUDGEMENT_SHA256>`: 지금 계산된다(`994102b728712aad7c2099bcc50084f9c5c3f37655a6e789d4efc2aa300a839a` = 173b7c20 blob).
  - `<S8R_HO_SEED>`: 봉인일 규칙(7.2)으로 정해진다. held-out 키 생성(Y8-6)보다 먼저 정해져야 하므로 반드시 봉인 문면에 채운다.

### [실행 전 수정][S] M-5. D 키 파일이 blob sha만 있고 커밋·경로가 없다
- 근거
  - `:208`: "git blob sha256 `a995abff…`".
  - 파일은 브랜치 `ed6-records` 커밋 3ecf61f1에만 있다. 작업 트리에는 없어 ref_check가 `ref_missing`을 냈다.
  - 재계산한 sha256 = `a995abff9d73816f58a0e3d67a59f18b3e60fb006fe48d824012b79b57d87981`(일치, `jobs` 12개).
  - worktree `ed6-records`는 잠겨 있다(`worktree_locks.py` 종료 0).
- 권장: `3ecf61f1:06_analysis/02_control/j_p3_cause/prelaunch_j9/run_records_ed6/d_grid_keys12.json`으로 적고, 판 8 판정이 끝날 때까지 브랜치와 잠금을 유지한다는 문장을 판 7처럼 넣는다.

### [실행 전 수정][S] M-6. 근거 폴더 SUMS의 빈 곳과 git 제외 파일
- 근거: 모든 SUMS 목록 해시는 맞았다(mismatch 0, missing 0, 아래 표). 다만 다음이 있다.
  - (a) `ed8_design/python_p1_p3/`에 SHA256SUMS가 없다. 파일은 `handback_p1_p3_7fc83456.md` 하나다. 명세 `:28`이 근거로 인용한다.
  - (b) 0c 근거 `ed8_design/python_0c_keys/`(SUMS 있음, 11항목 일치)가 명세 근거 표에 없다.
  - (c) 아래 npz는 `.gitignore:41 *.npz`에 걸려 커밋되지 않는다. SUMS에는 올라 있다.

    | 폴더 | 제외되는 npz |
    |---|---|
    | `dynamics_d1_d3` | 69 |
    | `dynamics_u832_o00` | 23 |
    | `control_early_handover/probe_8a2a52ce/diag` | 22 |
    | `control_level_deadlock/probe_8a2a52ce` | 82 |

    P8-16 기준인 `raw/runs.jsonl`은 제외되지 않는다(`git check-ignore` 출력 없음).
  - (d) 명세 `:21`은 "폴더 SHA256SUMS는 봉인 때 메인이 기입"이라고만 적었다. `control_level_deadlock/SHA256SUMS`(16:59:14)는 report.md 사후 편집(16:55) 뒤에 만들어졌다. 폴더 SUMS는 다시 쓰일 수 있다.
- 권장(메인)
  - `python_p1_p3` SUMS를 만든다.
  - npz는 LOCAL_ONLY 목록에 넣거나 `git add -f`로 처리한다.
  - 관문 기준(P8-16)과 판정 입력(키 파일)의 sha·SUMS sha는 명세 본문에 직접 인용한다(M-2).
  - 근거 표의 SUMS sha는 봉인 직전에 마지막으로 쓴다.

### [실행 전 수정][R] M-7. 봉인할 파일 안에 초안 상태 문구·메인용 메모·남은 자리 표시가 있다
- 근거
  - `:3`: "상태: 초안(개정 2…). 봉인 전이다"
  - `:438~445`: "메모(메인용, 명세 본문 아님)" 블록. 위임·권고와 사용한 스킬이 적혀 있다.
  - `:172`: "`<P814_VBK_KEYS>` 채움". 채운 뒤 남은 자리 이름이다.
- 권장: 봉인 해시를 재기 전에 메모 블록을 빼고, 상태 줄을 바꾸고, `:172` 자리 이름을 지운다(control-expert, 메인).

### [실행 전 수정][T·공개] M-8. 오염 보고 O8 목록이 행위를 다 적지 않았고, 한 보고는 사실과 반대다
- 근거: 이 세션 subagent transcript에서 Grep·Glob `path`와 셸 목록 명령을 훑었다.
  - **python Q8 확인**(`agent-a84e5dcdc0af34993.jsonl`, 2026-11-26T06:42:30Z)
    - Grep 1회의 `path`로 **worktree 루트** `C:\workspace\outrigger_control\.claude\worktrees\ed8-impl`을 썼다. glob `{03_src,04_scripts}/**/*.py`, 파일 목록 모드다.
    - O8 목록에 없다.
    - `python_q8_checks/report.md:6`은 "상위 폴더도 검색 범위로 쓰지 않았다. 검색 범위는 worktree의 `03_src`·`04_scripts`…"라고 적어 실제 호출과 다르다.
  - **stats S-1**(`agent-a3e4d098727bdf911.jsonl`, 05:24:39Z·05:24:40Z)
    - Glob `path` = `…\j_p3_cause` 2회(`jp3_*v7*.md`, `jp3_ed7_judgement*`).
    - `stats_s1/report.md:5~8`에는 공개했지만 명세 O8 목록에 옮기지 않았다.
  - **python 0c**(`python_0c_keys/report.md:106`): Grep `path` = `04_scripts` 폴더 전체. 초안 뒤에 생긴 행위다.
  - O8-6·O8-7·O8-8은 transcript와 맞는다. O8-7의 Glob 4회는 패턴까지 같다. control·dynamics 에이전트의 다른 상위 폴더 검색은 찾지 못했다.
  - 판 7 원인 분석(같은 세션 04:07Z·04:09Z ed7-impl worktree 루트 Grep 2회)은 O7-25에 있다.
- 권장
  - O8-9(python Q8: worktree 루트 Grep, 보고 문구와 다름), O8-10(stats S-1: Glob 2회), O8-11(python 0c: 04_scripts Grep), O8-12(이 감사의 행위, 아래 공개)를 더한다.
  - sha로 인용되는 `python_q8_checks/report.md`는 고치지 않고, 어긋남을 명세 O8-9에 적는다(control-expert).

### [실행 전 수정][E] M-9. 줄을 골라 비교하는 관문의 0건 처리가 없다
- 근거
  - `:345` P8-5: "스케일 mid가 옮겨지지 않은 라운드만 있는 줄"
  - `:348` P8-8: "…종료 시도가 없는 줄"
  - `:356` P8-15: "L-2 면제가 한 번도 쓰이지 않은 줄"
  - 셋 다 고른 줄에서 "명령이 같다"를 본다. 고른 줄이 0이면 비교 없이 통과할 수 있다.
- 권장: "고른 줄 0 = 판정 불가(멈춤)"와 최소 줄 수(예: P8-14 기록의 L-2 미작동 24키 수준)를 적는다(control-expert, 시험은 python-expert).

### [기록][T] R-1. P8-14·P8-9′ 규칙이 실행 전에 고정됐는지 — 확인했고, 문구가 실행 뒤 조금 바뀌었다
- P8-14
  - 규칙 문장이 control-expert 핸드백(`agent-a1b68f78668f32a86.jsonl`)에 2026-11-26T07:25:19Z(16:25 KST)와 07:28:38Z에 있다.
  - P8-14 원자료의 가장 이른 mtime은 16:34:53이다(첫 시작이 루트 문제로 멈춘 뒤 `p814_rerun.py` 16:35:13에 고쳐 다시 돌았다. 보고 99행에 공개). 실행 전 고정이 맞다.
  - 실행 뒤 문구가 바뀐 곳
    - (4) "면제·발사로 끝난 LEVEL의 |D| ≤ 15 kN" → "…LEVEL의 **DONE 때** |D| ≤ 15 kN"
    - (1)의 "(`t_ready_back_s` 유한, 최종 단계 ready)" 삭제
    - "키는 `control_level_deadlock/report.md` 6절" 삭제
- P8-9′
  - 규칙은 dynamics 지시(`agent-a7dc490bf7746b539.jsonl`, 07:17:33Z = 16:17:33 KST)에 있었다. h3p 실행은 16:19:48~58이다.
  - 실행 전 지시에는 "새 FAULT 0"과 확인 줄 1이 없었다. 명세 `:350`에는 둘 다 있다. 확인 줄은 dynamics가 스스로 더했고 보고에 공개했다.
- 판정 스크립트: `p814_analyze.py`(16:39:13)는 1차 묶음(13 job, `console_1` 16:38:45)이 끝난 뒤 작성됐다. 규칙 문장은 그보다 앞선다.
- O8-4의 "확인·선택 뒤 규칙·값은 바꾸지 않았다"는 뜻으로는 맞다. 다만 실행 전 문장을 그대로 두거나 "결과 뒤 문구 명확화"를 공개하기를 권한다.

### [기록][S] R-2. 저장 V0 `main.jsonl`은 git 추적 밖이다
- `.git/info/exclude:23`에 걸린다(seal_check `cited_ignored`). 명세는 앞 8자 `9ad74990`만 인용한다.
- 판 7도 같았다(이어받은 상태).
- 전체 sha `9ad749907c34c9e9efb77579a8ab6e3b1f86cdc32d36162c0029005ca545b29e`를 인용하기를 권한다.

### [기록][R] R-3. C-D 단위 칸 배정
- C-D가 소유한 병합 단위(6.2 (다))의 VBN 실패는 C-G 칸에 센다(`:222`·`:223`).
- 단계 소유와 집계 칸이 다르다는 것을 한 문장으로 적기를 권한다.

### [기록][R] R-4. 2차 별칭 뒤 k_N 재계산
- 7.5 `:293`의 "2차 뒤에는 n_N만 바꿔 다시 계산"은 S8-C에 봉인된 `ho_k_selection.json` 값과 최종 k_N이 다를 수 있다는 뜻이다.
- T8 도구가 동결된 x_AA·n_AA로 다시 계산한다는 것을 판정서에 적는다.

### [기록][S] R-5. CRLF md 3개
- `control_k1_window/loops/cmp_*.md` 3개에 CRLF가 각 28줄 있다.
- 해시는 맞고 `-text` 보호(check-attr `text: unset`)라 봉인에는 영향이 없다.

### [기록][S] R-6. 중첩 SUMS
- 상위 폴더 SUMS의 `sums_unlisted`는 모두 하위 폴더의 자체 SUMS 구조다.
  - `control_early_handover` 166
  - `control_early_handover/probe_8a2a52ce` 82
  - `control_level_deadlock` 182
  - `ed5_j9fail_606f8713`의 `hydraulics/` 4
- 결함은 아니다.

### [기록][R] R-7. 코드 동작 주장 대조 — 모두 맞다
- `two_pressure.py` 1760~1797: `witness is None` 경로가 판 6 D6이다.
- `c2.py` 7950~7960: `_has_twist_load_stopped_rising`. R8 상승 허용 600 N(`c2.py:1596`), drop 0(`:1595`). 호출처는 `_is_twist_relax_ok`(`:7935`) 하나다.
- `lock_start_b.py` 1232~1244: 조건 3 (다).
- `verdict_cases.py` 153~171: 사례 기본 다리. R12·R14 RR, R15·R16 FL.
- `verdict_runs.py` 574·587 `_run_event` / `r67.EVENTS[twin.event]`, `_ED8_RECORD` 328행.
- Y8-10의 n_still 정의(계수 시점, skip + 3, `ib_still_m`, LEVEL 밖 0, 한 주기 늦은 읽기)는 `p814_rerun.py` 203~276행과 같다.

### [기록][T] R-8. G′ 처리 팔(VBN 339)은 돌지 않았다
- 근거
  - 7fc83456 `*.py`에 VBN 설정 이름과 `census_keys_ed8`·`heldout_g_ed8`가 없다(`git grep` 종료 1).
  - 이름에 ed8이 든 커밋은 7fc83456 하나다.
  - 키 파일이 없다.
  - ed8 근거 폴더의 jsonl job 195개에 새 위상 O′(0.025 격자 밖)·F_s 1/3/6·depth/ramp 조건이 0건이다. 파일 이름에도 0건이다.
- 출력 경로 `j9_runs/<C8>/`는 C8이 없으므로 아직 없다. 블라인드를 품은 `j9_runs`는 목록을 열지 않았다.

## 통과로 확인한 것
- 줄 수 1043 = 388 + 460 + 24 + 171
  - j9_main 388: VBM 100, LSM1~4 각 72
  - `sens_keys_ed7.json`: `lines` 460, 판정 4설정(VBMslow·fast·c005·c04) 184, 기록 6설정
  - D `jobs` 12 × 2
  - G1 `lines` 171
- 키 파일 sha: sens `be930b75…`, G1 `684054ab…`, D blob `a995abff…`, grid192 `4e80e69b…`(`lines` 192), main.jsonl `9ad74990…` 모두 일치. C-D 키 파일에는 V0 짝이 없다(항목 키 `job`·`t4h_file`·`first_breach_leg`). G1 `v0_pair.run_id`는 문자열이다(명세 `:214`와 같음).
- P8-9′·P8-14는 본 키에서만 돌았다
  - P8-9 20키 ⊂ P8-14 23 VBM 키
  - 나머지 3키(R2 e0.001, S4 e0.002, S8 e0)는 판 7 j9_main VBM 줄에 있다
  - r79 4키는 판 5 공개 자료 `ed5_design/aa_stop_606f8713/`에서 골랐다(SUMS 종료 0)
- 상태 순서(`:318`), 판정 행 0 = 판정 불가(`:217`·`:318`·`:326`), 기록 실패 닫힌 목록(`:325`), 단계 전체 기회 0 = 판정 불가(`:224`). 단 B-1과 M-3 해소가 전제다.
- 판정/기록 구분이 4·10·12절 사이에서 같다(P8-7·P8-13 기록, P8-9·P8-9′·P8-14 설계 입력, 나머지 관문 판정).
- 줄바꿈 보호: 초안과 ed8_design 파일은 `-text`다(`git check-attr text` = unset, `core.autocrlf` true). 초안에 CRLF·BOM이 없다.

## 규칙↔도구 대조표 (판정 도구는 아직 없음 — 검토 스크립트·하네스 기준)
| 규칙(명세) | 코드·자료 | 결과 |
|---|---|---|
| 6.3 `event_output.fast` (`:250`) | main.jsonl `event_output` 키 30개에 없음, 격자 run 최상위 `fast` 있음(`r67_g1_screen.py:436`) | **불일치(B-1)** |
| 5.1 C-J VB/LS<n> (`:206`) | j9_main `job.setting` VBM/LSM<n> | **불일치(M-1)** |
| 5.1 C-S VBM<key> 10설정 (`:207`) | sens_keys settings_judged 4 / record 6 | 일치 |
| 6.3 사건 다리 기본값 (`:252`) | `verdict_cases.py:153~171` | 일치 |
| 3.8 L-2 조건 1~3 (`:162~166`), Y8-10 (`:421`) | `p814_rerun.py:203~276` | 일치 |
| 3.8 비틀림 완화 600 N (`:161`) | `c2.py:1596`, `:7950~7960` | 일치 |
| 3.2 D6 판 6 경로 (`:122`) | `two_pressure.py:1760~1797` | 일치 |
| P8-16 기준 줄 (`:357`) | P8-14 B 27 / L2 27줄, h3p 7줄 | 키 합집합 27, 원천 서로 같음 20/20 — 문면 정리 필요(M-2) |

## 확인 필요
- Q-1(사용자): B-1의 C-J·C-S 빠른 사건 판정을 "job twin 사건 이름 → `r67_g1_screen.is_fast(r67.EVENTS[event])`"(격자 `fast`와 같은 함수)로 정해도 되는가. 층 정의는 사용자 결정 4다.
- Q-2(control-expert): P8-16 4단계 실패 때 C8을 바꾸고 4단계부터 다시 돌리는 것을 허용하는가(`:196`과 `:332`가 어긋남).

## 위임 필요
- control-expert(명세 개정 3): B-1, M-1~M-9, R-1~R-4 문면.
- python-expert: Y8-6에서 main.jsonl 짝의 빠른 사건을 사건 이름으로 정하는 구현과 시험. P8-16 완결성 검사(27/27·27/27, 결측 = 실패)와 구현 커밋 사전 실행. P8-5·P8-8·P8-15의 고른 줄 0 처리.
- python-expert, `tools/verif` 후보
  - `transcript_scope.py`(가칭)
    - 입력: 세션 폴더, 제외할 에이전트, 시작 시각, 블라인드 목록
    - 출력: Grep·Glob `path`가 블라인드 상위 폴더 또는 worktree 루트인 호출, 상위 폴더를 훑는 셸 명령 목록
    - 종료 코드: 발견 시 1
    - 이번에 O8 누락 2건을 찾은 즉석 스크립트를 도구로 만드는 것이다.
  - `rule_anchor.py`(가칭)
    - 입력: 세션 폴더, 규칙 표지 문자열
    - 출력: 규칙 문장이 처음 나온 시각과 원자료 첫 mtime 비교, 그 뒤 문구 차이
  - `ref_check.py`는 표에 적힌 기준 폴더의 `../` 상대 경로(`:24`·`:38`)를 명세 폴더 기준으로 풀어 오탐을 냈다. 다른 브랜치에만 있는 코드 이름(`ed7_probe.py`·`ed8_probe.py`·`lock_start_b.py`)도 오탐이다. `--rev` 여러 개 지원을 검토해 달라.

## 메인 세션 권고
- B-1·M-1~M-9를 고친 개정 3이 나오면 짧게 다시 감사한다.
  - `placeholder_scan --skip-inline-code`, `ref_check --no-git --exclude …`
  - `.sha256`을 만든 뒤 `seal_check`
- 봉인·커밋 전에 할 일
  - `python_p1_p3` SUMS를 만든다.
  - npz LOCAL_ONLY 처리를 정한다.
  - `git status --ignored`로 인용 파일이 빠지지 않는지 본다.
  - `audit_preseal/` 폴더 SUMS는 마지막에 쓴다.
- P8-16 구현 커밋 사전 실행(54 job 정도)은 메인이 띄운다.

## 검사하지 못한 것
- `handoff_leak.py`는 돌리지 않았다. 경로 2 넘김 자료가 아직 없다. 9절 census 경로 2 넘김 전에 다시 본다.
- `gate_scan.py`, `junit_skips.py`, `key_presence --npz-dir`는 돌리지 않았다. 판 8 판정 도구·시험·건식 출력이 아직 없다.
- transcript 훑기는 이 세션(0d95027e) subagent만 했다. 메인 세션의 셸 명령과 다른 세션은 보지 않았다. P8-14 규칙 문장의 실행 전 원문은 핸드백 기록으로 확인했고, 명세 파일 자체의 이전 판은 남아 있지 않다(미추적, 덮어씀).
- stats S8-R 수치(정지 예보, MDE, A/A 바닥)는 재계산하지 않았다.

## 실행한 검증
- 인터프리터: python-dev `C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B`(`MKL_THREADING_LAYER=TBB`). 대상 프로젝트 모듈은 import하지 않았다.
- `baseline_check.py sums --repo C:\workspace\outrigger_control <폴더>`

  | 폴더 | 종료 | 내용 |
  |---|---|---|
  | `dynamics_d1_d3` | 1 | mismatch 0, missing 0, `cited_untracked` 118, `cited_ignored` 69 |
  | `hydraulics_h1_h2` | 1 | mismatch 0, missing 0, untracked 28 |
  | `stats_s1` | 1 | mismatch 0, missing 0, untracked 7 |
  | `dynamics_u832_o00` | 1 | mismatch 0, missing 0, untracked 96, ignored 23 |
  | `control_k1_window` | 1 | mismatch 0, missing 0, untracked 37 |
  | `control_early_handover` | 1 | mismatch 0, missing 0, untracked 9, unlisted 166(하위) |
  | `…/probe_8a2a52ce` | 1 | mismatch 0, missing 0, untracked 84, unlisted 82(하위) |
  | `…/diag` | 1 | mismatch 0, missing 0, untracked 65, ignored 22 |
  | `…/h3p` | 1 | mismatch 0, missing 0, untracked 17 |
  | `stats_s8r` | 1 | mismatch 0, missing 0, untracked 17 |
  | `python_q8_checks` | 1 | mismatch 0, missing 0, untracked 10 |
  | `control_level_deadlock` | 1 | mismatch 0, missing 0, untracked 5, unlisted 182(하위) |
  | `…/probe_8a2a52ce` | 1 | mismatch 0, missing 0, untracked 182, ignored 82 |
  | `ed5_design/aa_stop_606f8713` | 0 | – |
  | `ed5_j9fail_606f8713` | 1 | unlisted 4(중첩 SUMS) |
  | `python_0c_keys` | 1 | untracked 12 |
  | `ed7_design/ed7_j9fail_8a2a52ce` | 0 | – |

  `python_p1_p3`는 SUMS가 없어 돌리지 못했다. 종료 1은 모두 미추적(봉인 전 커밋 전)·git 제외·중첩 때문이고, 해시 불일치는 0이다.
- `ref_check.py`(`--exclude 06_analysis/02_control/j_p3_cause/j9_runs/606f8713/cdry_a1`, `--exclude 06_analysis/02_control/j_p3_cause/prelaunch_j9/ed6_inputs/x11`, `--exclude .claude`)
  - HEAD 트리 기준: 종료 1, missing 11, untracked 27, `excluded_references` 1
  - `--no-git`: 종료 1, missing 11
  - missing 11의 분류
    - 상대 경로 기준 오탐 3: `:24`·`:38`×2. 실제로 있다(`ls -d` 확인).
    - 다른 브랜치에만 있는 코드 3: `ed8_probe.py`·`ed7_probe.py`·`lock_start_b.py`. 7fc83456에 있다.
    - blob에만 있는 D 키 1(M-5)
    - 생성 예정 3: `census_keys_ed8.json`·`heldout_g_ed8.json`·`ho_k_selection.json`
    - 정정 공개 문장의 옛 경로 1: `:376`
- `placeholder_scan.py --pattern-set both`
  - `--skip-inline-code`: 종료 0
  - 전체: 종료 1. `--allow`에 S8R 3개와 S8C 10개를 이름으로 줬을 때 남은 5개는 설명 자리(`:3` `<S8C_…>`, `:197` `<C8 앞 8자>`·`<단계>`, `:384` `<S8C_*>`)와 `:172` `<P814_VBK_KEYS>`다. `--allow`는 정규식이 아니라 이름으로 받는다.
- `seal_check.py --repo … <v8 초안> <v7> <v7 정오 1> --quoted <v8 초안> --hash-files <키 파일·main.jsonl·ed7_j9fail·판정서> --min-hex-len 13`: 종료 1
  - `seal_missing` 1(봉인 전, 예상대로)
  - `quoted_unresolved` 1 = D blob. 손으로 일치를 확인했다.
  - `cited_ignored` 1 = main.jsonl
  - `rule_untracked` 1
  - `quoted_commit` 13(info)
- `worktree_locks.py --worktree <ed6-records> --worktree <ed7-impl>`: 종료 0.
- 직접 해시 확인: `Get-FileHash`와 hashlib(`git show` blob)로 v7·정오 1·판정서·키 파일·main.jsonl·D blob을 쟀다.
- `git check-ignore -v`, `git check-attr text eol`, `git ls-files --eol`, `git ls-tree -r 7fc83456/8a2a52ce`, `git grep 7fc83456`, `git worktree list`, `git log --all --grep=ed8`.
- 즉석 스크립트(scratchpad `verif-ed8-preseal\`, 보고 전 폴더째 지움)
  - `runs_shape.py`, `keysets.py`, `overlap.py`(P8-9 ⊂ P8-14, B 해시 20/20 같음), `extra_keys.py`, `j9keys.py`
  - `keycount.py`, `blobsha.py`, `fastfield.py`(fast 0/603)
  - `gprime_scan.py`(G′ 꼴 조건 0/195)
  - `tx_scan.py`·`tx_rule.py`·`tx_rule2.py`·`tx_rule3.py`(규칙 시각 고정), `tx_search.py`(상위 폴더 검색 훑기)
  - 산출 `ref_head.md`·`ref_disk.md`·`ph_*.md`·`seal.md`·`ed5fail_sums.md`·`guard.json`
  - 반복될 검사는 위 `tools/verif` 후보로 올렸다.
- 만든 부산물: `-B`로 실행해 `__pycache__`는 없다. scratchpad 하위 폴더는 지웠다(`Test-Path` False).
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v8_rules.md 5fdc0d7c…, jp3_remedy_spec_v7.md 10902ffd…, jp3_remedy_spec_v7_erratum1.md 74c49bda…, sens_keys_ed7.json be930b75…, confirm_g1_grid171.json 684054ab…, confirm_b_grid192.json 4e80e69b…, runs.jsonl 06b9d8fc…, runs.jsonl 89efe66f…, p814_rerun.py 0dade869…, report.md 5334a7b0…, report.md d302c4a3…, SHA256SUMS f2800274…, SHA256SUMS a0468d1b…, SHA256SUMS b1ac30c4…, SHA256SUMS ff199285…, SHA256SUMS 44c64c9a…, SHA256SUMS 6415cf83…, SHA256SUMS 1f4de072…, SHA256SUMS f1415f93…, SHA256SUMS b8600a6b…, SHA256SUMS 0c6d0bb8…, SHA256SUMS 893230cf…, SHA256SUMS ad5dee88…, SHA256SUMS 09a3166c…, jp3_ed7_judgement_8a2a52ce.md 994102b7…, 디렉터리 목록 동일, ~$ 임시 파일 없음) · 경고: 형제 항목 수정 시각만 변경 1건(ed8_design)
  - ed8_design 수정 시각이 바뀐 것은 감사 중 python-expert가 `python_0c_keys/`를 만든 탓이다. 내 쓰기가 아니다.
- 사용한 스킬: 없음

## 공개(행위 그대로, 명세 O8-12 후보)
1. **블라인드 상위 폴더 Grep**: Grep 1회의 `path`로 블라인드를 품은 `…\06_analysis\02_control\j_p3_cause`를 썼다. glob `jp3_remedy_spec_v6*.md`, 내용 모드(`-o`), 패턴은 `confirm_b_grid192` 경로 찾기였다. 출력은 v6 명세·v6 정오 1의 3줄이고, 블라인드 이름·건수는 없었다.
2. **블라인드 상위 폴더 목록**: PowerShell `Get-ChildItem -LiteralPath …\j_p3_cause -Filter "jp3_ed7_judgement*.md"`(비재귀)를 1회 돌렸다. 출력은 판정서 1개다.
3. **블라인드 파일의 부모 폴더 목록**: Bash `ls 06_analysis/02_control/j_p3_cause/prelaunch_j9/ed6_inputs/`(비재귀)를 1회 돌렸다. 블라인드 `x11/selection.json`의 부모 폴더다. 출력은 폴더 이름 `x11` 하나이고, `x11` 안은 열지 않았다. 같은 명령에서 없는 폴더 `prelaunch_j9/run_records_ed6/`의 `ls` 오류가 났다.
4. **금지된 Bash 파이프 2회**: `git -C <ed8-impl> status --short | head -5`(출력 없음), `git diff --stat 8a2a52ce 7fc83456 | tail -3`(3줄).
5. **ref_check 후보 이름 노출**: ref_check가 비슷한 이름 후보로 블라인드 정의 밖의 `j9_runs/…` 파일 이름을 화면에 냈다(`78fd5d2d/dry_a1/selection.json`, `ae9d0b2d/ed5_inputs/x11/selection.json`, `b51ed6e1/dry_a1/selection.json`, `6bfb2560/ed7_probe_a1/ed7_probe.jsonl`, `8a2a52ce/confirm_a1/…`, `1bd405c8/ed6_probe_a1/…`). 블라인드 접두는 `--exclude`로 뺐다(`excluded_references` 1).
6. **판 7 판정 끝난 결과 읽기**: 블라인드가 아닌 `j9_runs/8a2a52ce/j9main_a1/j9_main.jsonl`을 파일 경로로 지정해 `job` 필드만 셌다.
7. **transcript 읽기**: 이 세션 subagent transcript(`~/.claude/projects/C--workspace-outrigger-control/0d95027e-…/subagents/*.jsonl`)를 스크립트로 훑었다. 출력은 도구 호출 시각, 경로, glob과, P8-14·P8-9′ 규칙 문장이 든 줄(설계 입력 수치 포함, 명세에 이미 있는 값)뿐이다. 이 폴더에 Grep 건수 모드 1회(`jp3_remedy_spec_v8_rules`), 내 transcript에 내용 Grep 1회를 썼다.
8. **쓰기**: 감사자 메모리 `C:\Users\jinbeom\.claude\agent-memory\verif-protocol-auditor\audit_pitfalls.md`(항목 1개 추가)와 `MEMORY.md`(색인 꼬리)에 썼다. 그 밖의 쓰기는 scratchpad 하위 폴더뿐이고, 보고 전에 지웠다. 프로젝트 파일은 수정·생성·삭제하지 않았다.
9. **worktree·블라인드 경로**: worktree `ed8-impl` 코드 파일은 Read·Grep로 파일을 지정해 읽었다. 블라인드 경로(`j9_runs/606f8713/cdry_a1/VBK_c92*`·`VBK_c93*`·`logs/`와 그 worktree 사본, `prelaunch_j9/ed6_inputs/x11/selection.json`)는 열지도 검색하지도 않았다.
