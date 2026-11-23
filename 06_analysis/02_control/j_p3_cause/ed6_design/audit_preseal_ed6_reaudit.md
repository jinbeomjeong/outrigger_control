## 감사 요약 (짧은 재감사, 실행 전)
- 본 결과: 판정 대상 결과는 보지 않았다. 본 것은 다음 둘뿐이다.
  - V0 기준 자료인 `keys/confirm_b_v0fail18.json`의 요약 키
  - 판 5 12b(판정 끝난 본 행)와 prelock T4h의 배열 **이름**(값은 보지 않음)
- 대상
  - 명세 `jp3_remedy_spec_v6.md` 개정 13: 15561255
  - 넘김 `jp3_rev6_p2_handoff_ed6.md`: 4b3c6b6c
  - 구현 HEAD 47b184af: ac3c25a7 대비 `lock_start_b.py` docstring 4줄만 바뀌었다. `git diff`로 확인했고, 코드와 행 번호는 그대로다.
- 판정: **차단 0 / 실행 전 수정 2 / 기록 6**
  - 실행 전 수정 2건은 문장 고침만이면 된다(N-1, N-2).
  - 고친 뒤 메인이 문장만 대조하고 봉인하면 된다. 재감사는 필요 없다.

## 앞 감사 지적의 반영 확인 (문장 대조)

| 지적 | 반영 위치(개정 13) | 판단 |
|---|---|---|
| B-1 12a 단축 실행 | 본 행 표 63행, O6-5(74행) 정정, O6-6(75행: 2회 95cae09d·755a15d8, 본 것·안 본 것), 12절 812-813행 | 반영됨 |
| B-2 봉인 뒤 도구 관문 | 4절 4a(376-384행: Y-5·Y-6·Y-10, 그 전 판정 불가, 판 5 도구 대체 금지), 506행 "감도 단계 = 6.2 + 6.3 (가)·(나)", Y-5·Y-10 표 | 반영됨 |
| M-1 A(ii) 단일 읽기 | 184·187행 | 반영됨 |
| M-2 출력 경로 순서 | 205·211·219행, Y-1 | 반영됨(ac3c25a7 행 번호 일치) |
| M-3 B3 끝 사유·보호 | 244행(고정 문턱), 263행(같은 LEVEL 구간), 264-265행, 289행(일곱 사유) | 반영됨 |
| M-4 VBL0 쓰임 | 297행 "12a 기준 팔(6.5)" | 반영됨 |
| M-5 꺼짐 줄 키 없음 | 310행 | 반영됨 |
| M-6 `lsb_settings` | 432행(경로 1만), Y-5 | 반영됨 |
| M-7 격자 VB 2줄 | 543행, 12절 815행 | 반영됨 |
| M-8 선정 출력 고정 | 명세 587행, 넘김 3.1(123행), sha 6687b2dc 일치 | 반영됨 |
| M-9 줄 누락 | 466·524행, 넘김 79·92행 | 반영됨 |
| M-10 key_presence 목록 | 6.6(644-653행) | 반영됨. 12b 배열 4개(`phase`·`command_m_s`·`motor_stroke_m`·`rod_fault_applied`)가 판 5 12b T4h 167개에 모두 있음을 `key_presence --npz-dir`(종료 0)로 확인했다 |
| M-11 P6-2 | 406행(발동 수는 기록) | 반영됨 |
| M-12 블라인드 건수 | O6-7(76행), 59행, 12절 814행 | 반영됨 |
| M-13 실제로 쓴 몫 규칙 | 341-344행, 12절 816행 | 반영됨 |
| 기록 1·3·4·6·7·8·9 | 345행 날짜, 515행, 넘김 3행 "개정 13", 47b184af, `stats_v6/SHA256SUMS` LF(CRLF 0), 516행·넘김 12행, 116행 | 반영됨 |
| 기록 2 낡은 표기 | 6·61·86·107·148·451·553행, 절 번호(6.5 = 12a, 6.6 = 판정 불가) | 대부분 반영됨. 남은 것은 기록 R-2 |
| 기록 5 P-pred 가장자리 경우 | 반영하지 않음 | 선택 사항이라 문제 없음 |
| 격자 V0 실패 18줄(사용자 결정) | 533-541행(기회 174, 허용 1 / 18줄은 FAULT 0·J-P3 / s42), 넘김 93행 | 반영됨 |

## 발견 사항

**[실행 전 수정][R/T] N-1. V0 실패 18줄의 봉인 전 확인이 끝났는데 명세에는 아직 "남은 것"으로 적혀 있다**
- 근거
  - 542행: "python-expert가 키 파일 또는 별도 기록에 남긴다 … `fault0`으로 실패한 줄이 있으면 봉인 전에 멈추고 묻는다".
  - 13절 864-865행 "남은 것"에 이 항목이 그대로 있다. 5행의 "남은 곳 없음"과 모순된다.
  - 명세에는 `confirm_b_v0fail18`가 0회 나온다(Grep).
  - 실제 기록이 있다: `ed6_design/keys/confirm_b_v0fail18.json`(17d7d144…), `.csv`(397b6e8f…), 생성 스크립트 `v0fail18.py`(ef4e9206…). 셋 다 `keys/SHA256SUMS`에 있고 해시 불일치는 0이다.
  - 그 기록의 결과: `fault0_failed_lines` 0, `fault_event_lines` 0, `hash_match_all`·`event_match_all`·`pass_false_all` 참. 멈춤 조건에 걸리지 않는다.
- 권장 조치: 542행과 13절에 파일, sha, 결과 "fault0 실패 0·FAULT 사건 0 → 멈춤 없음"을 적어 닫는다. 13절 "남은 것"은 "없음"으로 고친다.

**[실행 전 수정][I] N-2. probe 출력 폴더의 "로컬 전용" 범위가 실제 ignore 설정과 다르다**
- 근거
  - 348행은 "이 폴더(jsonl 86 MB, T4h npz)는 커밋하지 않는다"고 적었다.
  - 실제 ignore 설정
    - `.git/info/exclude:102`는 `ed6_probe.jsonl` 하나만 뺀다.
    - npz는 `.gitignore:41`이 뺀다.
  - 그래서 폴더째 `git add`하면 나머지 10개 파일이 커밋에 들어간다: `ed6_probe_share.json`·`.csv`, `identity.json`, `progress.json`, `sample.json`, `.done`, 로그 3개, `ed6_probe_a1_LOCAL_ONLY.SHA256SUMS`.
  - `LOCAL_ONLY.SHA256SUMS`에는 jsonl 1항목만 있다. 그런데 명세는 `ed6_probe_share.json` status decided를 sha 없이 인용한다.
- 권장 조치(메인, 둘 중 하나)
  - (가) 문장을 "jsonl·T4h npz만 로컬 전용, 나머지 파일은 커밋"으로 고친다.
  - (나) 폴더 전체를 exclude하고 `LOCAL_ONLY.SHA256SUMS`에 share.json 등의 sha를 더한다.
- (가)가 간단하고, 근거 파일(share.json)이 추적된다.

**[기록]**
- R-1 handoff_leak 재실행(사전 `p1_names_ed6.json`은 그대로, 앞 허용 목록 15개 + 2개)
  - 허용 없이 돌리면 50줄, 17개 이름이 걸린다.
  - 새로 걸린 `v0_pass`·`seed_repeats`는 경로 2가 읽는 입력 파일 필드다. 명세 535·587행에서 정의한 규칙 용어라서 허용 목록에 더했다.
  - 이 둘을 더해 돌리면 **누설 0**(종료 0)이다.
  - 대소문자 무시 검사는 25줄, 7개 이름이다. 일반 단어와 설정 VBK0, 그리고 허용한 이름이 대소문자만 다르게 걸린 것이다.
  - **양성 대조**: 사본에 6개 이름을 넣었고 6개 모두 잡혔다.
- R-2 남은 낡은 표기
  - 12절 790행 "O6-1~O6-5" → O6-1~O6-7
  - 560행·302행 "제안한다"
  - 10절 758행 "stats s40·s50 … 예측 문장은 봉인 때 고정" → s42, 개정 13에서 고정됨
- R-3 오탐
  - placeholder_scan 9건: 앞 감사와 같다(LaTeX 첨자, `<leg>`·`<j>` 사건 틀).
  - ref_check missing 24건: 미추적 폴더 안의 bare 이름이다. 새로 걸린 `lock_start_b.py`는 ed6-impl에만 있는 파일이고, `ed6_probe_a1/`는 로컬 전용 폴더라서 걸렸다. 두 파일 모두 실제로 있다.
- R-4 `ed6_design/audit_preseal_ed6.md`(앞 감사 원문)에는 경로 1 이름이 많이 들어 있다. 경로 2 지시문의 "열지 않을 것"에 `ed6_design/` 감사 파일을 명시하기를 권한다. 넘김 17행은 명세·정오 원문만 금지한다.
- R-5 12a 첫 단축 실행(95cae09d)의 출력은 지워져 근거가 없다. O6-6에 공개되어 있으니 그대로 두면 된다.
- R-6 47b184af 이후 시험(P6-4)은 실행 커밋에서 다시 돌아야 한다. docstring만 바뀌었으므로 P6-3 probe 재현 해시에는 영향이 없을 것으로 본다[추정].

## 봉인 가능 여부
- **N-1·N-2 문장을 고치면 봉인할 수 있다.** 차단은 없다.

## 봉인 커밋 파일 목록(갱신)
1. `jp3_remedy_spec_v6.md` + `.sha256`, `jp3_rev6_p2_handoff_ed6.md` + `.sha256`. 둘 다 LF이고 BOM이 없으며 `-text`다.
2. `ed6_design/`
   - `audit_preseal_ed6.md`
   - `stats_v6/`(41개, SUMS LF), `hydraulics_v6/`(7개), `control_v6/`(9개), `dynamics_v6/`(9개)
   - `probe_1bd405c8/`(추적 대상 22개)
   - `keys/`(9개, SUMS 8항목 불일치 0)
   - `ed6_p2_leak/`(13개, SUMS 12항목)
   - `prelock_12a_755a15d8/`(추적 대상 20개)
3. **`git add -f` 대상**
   - prelock의 ignore된 10개. 모두 prelock `SHA256SUMS`에 있으므로 필수다.
     - `dg3_VBL.json.partial.jsonl`, `dg3_VBL0.json.partial.jsonl`, `L1_VBL.json.partial.jsonl`, `L1_VBL0.json.partial.jsonl`
     - `dg3_VBL_t4h/*.npz` 2개, `dg3_VBL0_t4h/*.npz` 2개, `L1_VBL_t4h/*.npz`, `L1_VBL0_t4h/*.npz`
   - `probe_1bd405c8/b1off_check/ed6_probe_a1a2b3_t4h/*.npz` 40개는 선택이다. SUMS에 없으니 넣는다면 SUMS에도 더한다.
4. `prelaunch_j9/ed6_inputs/x11/` 9개(`selection.json` 6687b2dc)
5. `j9_runs/1bd405c8/`: `ed6_probe_a1_LOCAL_ONLY.SHA256SUMS`. 나머지 10개 파일은 N-2 결정에 따른다. jsonl과 npz는 커밋하지 않는다.

## 실행한 검증
- 인터프리터 python-dev `-I -B`(PowerShell). scratchpad `auditor-ed6seal2`는 보고 전에 지웠다.
- 도구
  - placeholder_scan `--pattern-set both`, ref_check
  - baseline_check sums ×5(keys, stats_v6, ed6_p2_leak, LOCAL_ONLY `--base repo-root`): 해시 불일치 0
  - handoff_leak ×4(허용 없음 / 허용 / 대소문자 무시 / 양성 대조)
  - key_presence `--npz-dir` ×2
- git 조회: log, diff, status `--ignored`, check-ignore, check-attr
- 이번에 쓴 파일(`ed6_design/ed6_p2_leak/`)
  - 새 파일 5개: `leak_p2_ed6_r13_raw.json`(87a44c19), `leak_p2_ed6_r13_allowed.json`(a440554e), `leak_p2_ed6_r13_allowed_ignorecase.json`(c0866eb9), `leak_positive_control_ed6_r13.json`(a2221bbc), `leak_run_ed6_r13.json`(681c5f60)
  - `SHA256SUMS` 다시 씀(12항목)
- 원본 불변: 위반 — 형제 항목 내용 변경 1건(SHA256SUMS) · 경고: 입력 폴더에 항목 추가 5건(leak_p2_ed6_r13_allowed.json, leak_p2_ed6_r13_allowed_ignorecase.json, leak_p2_ed6_r13_raw.json 외 2건)
  - 이 "위반"은 내가 지시받은 폴더 `ed6_p2_leak/`에서 `SHA256SUMS`를 새 결과 5개를 넣어 다시 쓴 것이다. 감시 입력이었던 `p1_names_ed6.json`의 형제 파일이라 잡혔다.
  - 감시 입력 6개(명세 15561255, 넘김 4b3c6b6c, `keys/SHA256SUMS`, `stats_v6/SHA256SUMS`, `selection.json`, `p1_names_ed6.json`)는 바뀌지 않았다. 마지막에 명세·넘김 sha를 다시 재어 같음을 확인했다.
- 사용한 스킬: 없음
