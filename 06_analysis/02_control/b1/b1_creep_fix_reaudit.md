# B1 도구 수정분 재감사 + K-R 대응표 (verif-protocol-auditor, 2026-11-12, Chrono 실행 중·결과 전)

아래는 감사 리포트 원문 그대로다. 처리는 맨 끝 '메인 세션 처리' 절에 덧붙인다.

---

## 감사 요약
- 대상: B1 크리프 판정 도구 수정분 재감사와 K-R 대응표 작성. 시점은 실행 전(Chrono 본 배치 실행 중)이다. master는 `bd64cc4`, 추적 변경 0(감사 중 두 번 확인).
- 기준 문서: 원판 `b1_creep_rules.md` `6b99702c`, rev1 `b1_creep_rules_rev1.md` `9f72af5b`, 실행 전 감사 원문 `7e22898a`, prelaunch(현재 `c5d0c13e`).
- 판정: 차단 0 / 실행 전 수정 3 / 기록 6. 실행 전 감사의 (a)(b)(c)는 규칙 문장대로 고쳐졌다. sha는 보고값과 같다. 남은 것은 prelaunch 문장 수정 2건과 결정 1건이다. Chrono 결과 전에 끝내면 된다(경로 1·2 코드는 다시 고치지 않아도 된다).
- 본 배치 `batch_V5-B1-CREEP_20261112_125134`는 열지 않았다(목록 조회도 하지 않음). 키 확인에는 G-S 배치만 썼다.

## 재감사 발견 (심각도순)

**[실행 전 수정][R·E] E-5 정의가 두 경로에서 다르다. 묶음 상태가 갈릴 수 있다.**
- 근거
  - 경로 1(`b1_creep_metrics.py:1864-1866`)은 identity JSON의 `runner_log.errors_total`·`errors_left`로 판정한다. prelaunch 10.1(`b1_creep_prelaunch.md:163`)은 이 값을 `log_errors.py`로 채우라고 적었다. 그런데 이 배치 로그에는 `errors N` 줄이 없다(실행 전 감사 기록). 그래서 사실상 항상 0이다.
  - 경로 2(`path2/b1_path2.py:1422-1436`, `:1582-1583`)는 `<case>.log`에 `Traceback`이 있으면 `BLOCKED_E5`를 낸다.
- 실패 시나리오: C3나 C6이 Traceback으로 죽고 다시 돌리지 않은 경우다. 경로 1은 그 행을 MISSING으로 보고 PARTIAL 등급을 낸다. 경로 2는 BLOCKED_E5를 내고 등급을 내지 않는다. K-02가 불일치하므로 전부 UNDETERMINED가 된다.
- 권장 조치(메인 세션, 결과 전): prelaunch 10.1의 `runner_log` 채우는 법을 경로 2와 같은 정의로 고친다. "최종 `<case>.log`에 Traceback이 있는 행 수 = `errors_total` = `errors_left`, rc는 batch.json"처럼 적는다. 코드는 바꾸지 않는다.

**[실행 전 수정][R] prelaunch 10.2의 경로 2 명령에 `--identity`가 없다.**
- 근거
  - `b1_path2.py`는 이번 수정에서 `--identity`를 `required=True`로 받는다(diff `:1637`).
  - `b1_creep_prelaunch.md:168`의 명령 줄에는 `--identity`가 없다(grep 0). 같은 파일 `:52`는 "더한다"고만 적었다.
- 실패 시나리오: 그대로 실행하면 argparse가 종료 2로 멈춘다(안전한 쪽 실패다). 고쳐 다시 실행하면 PATH2_RUN_AT 기록이 꼬인다.
- 권장 조치: 명령에 `--identity <배치 폴더>\B1_identity.json`을 넣는다. 경로 2 실행 전에 브랜치 `b1-path2-fix`를 병합해 main checkout의 `b1_path2.py` sha가 `7a9d258f`인지 확인한다.

**[실행 전 수정][R] K-R "M-1~M-12 모든 수치" 가운데 경로 2 출력에 대응 키가 없는 기록 항목이 12묶음 있다(대응표 14절 U-01~U-12).**
- 경로 2 출력에 없는 것
  - 경로 2는 VALID 행에만 지표를 낸다. 하네스 실행별 지표는 출력하지 않는다.
  - 출력에 없는 블록: M-1 t_dep, M-4h, M-7(ĉ(t_L) 빼고), M-8 나머지, M-9, M-10의 s_L·s_R·δos·g, M-11 일부, M-6 b*·b 밖 두 다리, P-G 보조 값, D-f 짝 이름 목록.
- 근거: `b1_path2.py:636-735`(`run_metrics` 키), `:1541-1570`(행 출력), `:1606-1611`(최상위 출력).
- 영향: 등급 계산에 쓰이는 항목은 없다. 다만 9절을 문자대로 읽으면 K-R 불일치다.
- 권장 조치: 결과 전에 사용자 결정 세 항목과 같은 방식("한 경로 기록, K-R 제외, 판정서 공개")으로 할지, 경로 2 출력에 더할지 정한다(확인 필요 1).

**[기록][R] 이미 알려진 정의 차이가 미수정으로 남아 대응표 항목에 걸린다.**
- K-93 D-a 하네스 보정량: 경로 1은 (원시 ZA-2, 보정 ZA-1)일 때만 값을 낸다. 경로 2는 최종 ZA-2이면 항상 낸다(`:1182`). 경로 1이 규칙 (나) 문장에 맞다.
- K-108 D-h 등급 순위: SAME과 NA가 섞이면 경로 1은 K-NA, 경로 2는 K-SAME을 낸다(`:1336`). 경로 1이 규칙 "모두 같음"에 맞다. 다만 prelaunch `:51`과 이전 감사에 따르면 지금 입력은 20/20 키가 일치해 섞일 일이 없다.
- D-d "하한 포함" 표시 정의가 다르다. 경로 2(`:1256`)가 7.4 문장에 더 가깝다. 등급에 쓰이지 않는다.
- D-c 계산 행: z(t_max)가 없는 행을 경로 1은 `undetermined`로 넣고, 경로 2는 뺀다(`:1221-1222`). 대응표에서 그런 행은 빼고 대조하도록 정했다.
- D-f READY 판별: 경로 2는 `not sgs and ready`로 본다.
- 처리: 대응표에 비교 방법을 정해 두었다. K-93 정의를 맞출지는 확인 필요 2다.

**[기록][R] pad_nodes 일치 검사의 필드 수와 허용이 다르다.**
- 경로 1은 8필드를 완전 일치로 본다(`b1_creep_metrics.py:173-175`, `:670-702`). 경로 2는 규칙의 5필드를 상대 1e-12로 본다(`b1_path2.py:1355-1387`).
- G-S 두 행(각 100주기)에서 8필드 모두 두 기준으로 차이가 0이었다(즉석 대조).

**[기록][I] 경로 1 I-11에 None 통과가 있다.**
- `c2_soil.W_ref_N`이 없으면 제어기 질량 검사를 건너뛴다(`:1162-1166`). 경로 2는 같은 경우 INVALID로 본다.
- G-S C6 result.json에는 두 경로가 읽는 키(`args.mass_scale` 1.1, `c2_soil.W_ref_N`, `mass_scale.*`)가 모두 있다. g = 9.80665와 일치한다.

**[기록][E] V-1 FAULT 끝 판별 방식이 다르다.**
- 경로 1 수정본은 `phases` 마지막 항목을 소문자로 바꿔 `FAULT_PHASES`와 비교한다(`:589-599`, `:1196`). G-S의 `phases` 값은 `check`·`touch`(소문자)라 이 비교가 맞게 동작한다.
- 경로 2는 `FAULT_` 접두 사건 유무로 본다(`:1446`). 사건 뒤에 단계가 바뀌는 경계 경우에만 갈린다.

**[기록][R] 경로 2 `h_rec.Z_k_star`가 항상 null이다.**
- 초기값을 넣은 뒤 다시 채우지 않는다(`:890`). 대신 `Z_k`는 t_e 값으로 낸다.
- K-R 대상(7.2는 m_L만)이 아니라 판정서의 P-A 한계 기록에만 영향이 있다.

**[기록][S] sha와 커밋이 보고값과 같다.**
- 경로 1 `b1_creep_metrics.py`: `6b6e04acfd0cfb77e53b35981984bd4a9e4ccad2b4ce5446b6e5e7c018dda9d9`(1ac4849, blob f7c9431a)
- 경로 2 `b1_path2.py`: `7a9d258fa3182506a82fbdca74c15a1b8a37bd7858cf413f959fe0f4f52183db`(24a108e, blob 32522171)
- 경로 2 selftest `6815d960…`, README `ae982a17…`, keymap `19021bc6…`
- 두 worktree 모두 추적 변경이 없다.

새로 생긴 빈 집합 통과·종료 코드 문제
- 없다. 경로 2는 이제 COMPLETE/PARTIAL에서만 0, 나머지는 1을 낸다(`:1656`). 등급은 COMPLETE/PARTIAL에서만 낸다(`:1589`).
- 정체성 파일이 없거나 행이 빠지면 종료 2다. 규칙·rev1·P7 sha가 다르면 종료 2다.
- gate_scan 결과는 이전과 같다. `all_without_count_guard` 2건은 고정 튜플 위의 all이라 오탐이다.

## K-R 대응표
- 파일: `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\6f3ebc4d-a5fb-4d9f-b214-d0ae5c515ee1\scratchpad\verif_b1fix_out\b1_kr_map.md`
- sha256: `d0f30e15223785934f1435ac1900a6d1e3ca124256f6e4777d2a3545de6601c8`
- 형식: 24,807바이트, 263줄, LF(CR 0), BOM 없음, placeholder_scan 종료 0(중괄호 0개). 머리에 "결과 전 작성, Chrono 본 배치 미열람"과 작성 시각 2026-11-12T13:10+09:00을 적었다.
- 프로젝트 경로에는 쓰지 않았다. 내 정의가 읽기 전용이라 프로젝트 파일을 만들 수 없다. 메인 세션이 `Copy-Item`으로 `C:\workspace\outrigger_control\06_analysis\02_control\b1\b1_kr_map.md`에 그대로 옮기면 sha가 유지된다. 그 경로의 `git check-attr text`는 `unset`(`-text` 보호)이다. 원본은 scratchpad에 남겨 두었으니 옮긴 뒤 지우면 된다.
- 내용
  - 대조 항목 K-01~K-109: 109개(다리·τ·모서리로 펼치기 전 개수). 행·묶음 상태, M-1~M-11, M-12 하네스 locs, 7.2 m_L·T-14, 7.3 상수·R1-3 감도·R1-4, 4.4 행별 분류, D-a~D-h 등급과 계산 행을 덮는다.
  - 유도 대응 6개(K-50·51·52·61·66·83), 규약 변환 5개(K-02·36·68·69·81).
  - 제외 4개(X-01~X-04). X-01 M-4 최대 침하율, X-02 Chrono M-12, X-03 E_P-A*·e(P-A*)·T-13 표시, X-04 T-13 문턱 행이다. 모두 "제외(한 경로 기록, 판정서 공개)"로 사용자 결정 2026-11-12를 따른다.
  - 대응 없음 12묶음(U-01~U-12): 위 실행 전 수정 3번째 항목이다.
- 허용: 규칙 9절 값은 이산 완전 일치와 길이 1e-9 m뿐이다. 그 밖의 단위는 모두 **제안**으로 표시했다: N 1e-6, rad 1e-12, 무차원·m/N 상대 1e-9, r_σ 1e-12, m/s 1e-9, s 1e-9.
- 대조 범위: M 수치는 두 경로 모두 VALID인 행만 대조한다. 경로 2가 VALID 행에만 값을 내기 때문이다. flags 문자열은 K-R 밖으로 두는 것을 제안했다(9절 목록에 없음).
- K-70~K-79(상수·R1-4 하네스)는 하네스 입력만 쓰므로 Chrono 결과 전에 대조할 수 있다.

## 확인 필요
1. U-01~U-12(경로 2에 대응 키가 없는 기록 항목)를 처리할 방법을 정한다. "한 경로 기록, K-R 제외, 판정서 공개"로 할지, 결과 전에 경로 2 출력에 더할지다. 특히 U-10은 5절 "M-1~M-12"에 하네스 실행이 들어가는지 문장이 정하지 않았다.
2. K-93 D-a 하네스 보정량의 정의 차이를 결과 전에 정한다. 기록 항목으로 K-R에서 뺄지, 경로 2를 규칙 (나)대로 고칠지다.
3. 대응표의 **제안** 허용값(N·rad·무차원 등)을 채택할지 정한다.

## 위임 필요
- 위임 필요(python-expert): tools/verif 후보 `kr_compare`(지난 감사와 같은 후보)
  - 입력: 두 경로 출력 json, 이 대응표를 기계가 읽는 꼴로 옮긴 json(키 경로, 변환 규약, 허용, 범위 조건 "두 경로 VALID")
  - 출력: 항목별 일치·불일치·대응 없음
  - 종료 코드: 0 일치 / 1 불일치 / 2 입력 오류
- 경로 2를 고치기로 하면 control-expert가 규칙 문장만 보고 고친다. 이 대응표는 경로 2 작성자에게 넘기지 않는다.

## 메인 세션 권고
- prelaunch 10.1(`runner_log` 정의)과 10.2(`--identity` 추가)를 고치고, 대응표를 옮겨 sha를 prelaunch에 적는다. 이 일은 결과 파일이 생기기 전에 끝낸다.
- 원하면 K-70~K-79를 지금 하네스만으로 대조한다. 경로 1 `constants` 하위 명령 출력과 경로 2 상수 파일은 이미 있다.

## 검사하지 못한 것
- 경로 1 pytest와 경로 2 selftest는 다시 돌리지 않았다.
- 두 경로를 G-S 입력으로 실행하지 않았다(출력 파일을 쓰는 실행이라). 그래서 대응표의 키는 코드 읽기로만 정했다. 실제 출력 JSON(`_jsonable` 뒤 정수 키가 문자열로 바뀌는 점 등)으로 한 번 확인하는 것을 권한다.
- 경로 2 JSON에서 줄 번호 키가 문자열인지는 `_jsonable`을 읽지 않아 [추정]이다.

## 실행한 검증
- git: `git diff bd64cc4 1ac4849`, `git diff bd64cc4 24a108e`, 두 worktree의 HEAD·status, master HEAD·status(두 번), `git check-attr text`(대응표 대상 경로).
- sha256: 두 도구, selftest, README, keymap을 바이트에서 직접 쟀다.
- python-dev `python.exe -I -B -X utf8`(MKL_THREADING_LAYER=TBB)로 즉석 스크립트 2개를 돌렸다. 둘 다 G-S 배치만 읽었다.
  - `gs_keys.py`: phases·mass_scale·s9_rows 키, 로그 Traceback 유무
  - `padnodes.py`: npz ↔ pad_nodes 8필드 대조
  - 둘 다 scratchpad `verif_b1fix\`에 두었고 폴더째 지웠다.
- verif 도구: `gate_scan.py`(두 도구), `placeholder_scan.py`(대응표, 종료 0).
- 대응표 줄바꿈·BOM: python 한 줄 명령으로 바이트를 셌다.
- 최종 판정 전에 worktree HEAD(1ac4849·24a108e), master `bd64cc4`, prelaunch 경로 2 명령의 `--identity` 부재(grep)를 다시 확인했다. 감사 중 바뀐 파일은 없다.
- 남긴 파일: scratchpad `verif_b1fix_out\b1_kr_map.md`(넘겨줄 산출물). 그 밖의 임시 파일은 지웠다.
- 메모리 `audit_pitfalls.md`·`MEMORY.md`에 일반 함정 2개를 추가했다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha b1_creep_rules.md 6b99702c…, b1_creep_rules_rev1.md 9f72af5b…, b1_creep_prelaunch.md c5d0c13e…, b1_creep_prerun_audit.md 7e22898a…, b1_creep_metrics.py 6b6e04ac…, b1_path2.py 7a9d258f…, b1_H.jsonl a7099db6…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음

---

## 메인 세션 처리 (2026-11-12, 결과 전)

- 실행 전 수정 1(E-5 정의): prelaunch 10.1 `runner_log`를 경로 2 정의(최종 `<case>.log` Traceback 행 수, rc는 batch.json)로 고쳤다. 코드 변경 없음.
- 실행 전 수정 2: prelaunch 10.2 경로 2 명령에 `--identity`를 넣고, 경로 2 실행 전 `b1-path2-fix` 병합·sha 확인을 적었다.
- K-R 대응표를 `06_analysis/02_control/b1/b1_kr_map.md`로 그대로 옮겼다(sha256 d0f30e15…, 원본과 같음).
- 실행 전 수정 3(U-01~U-12), 확인 필요 2(K-93), 확인 필요 3(제안 허용값)은 사용자에게 묻는다(결과 전).
