# B1 크리프 근거 실행 전 감사 (verif-protocol-auditor, 2026-11-12, HEAD bd64cc4)

아래는 감사 리포트 원문 그대로다. 결정은 맨 끝 '메인 세션 처리' 절에 덧붙인다.

---

## 감사 요약
- 대상: `V5-B1-CREEP` Chrono 본 배치 6행. 시점은 실행 전이고, 저장소 `C:\workspace\outrigger_control`, master `bd64cc405990101ca8f3398ba2b9db9edcfc01b4`다. 추적 파일 변경은 0이다(감사 시작과 끝에 모두 확인).
- 기준 문서
  - 원판 `06_analysis/02_control/b1/b1_creep_rules.md`: `6b99702c`, 봉인 커밋 `1ad3e5d`, 봉인 시각 09:26:11
  - rev1 `b1_creep_rules_rev1.md`: `9f72af5b`, 봉인 커밋 `417ce28`, 봉인 시각 11:59:43
  - 전제 문서: 격자 계획 `0e909bf1`, 계획 rev1 `3f354eb7`, 판정 `a483ac48`. 세 파일 모두 실제 해시와 같다.
- 판정: 차단 0 / 실행 전 수정 4 / 기록 9. **Chrono 6행을 시작해도 된다.** 실행 전 수정 4건은 모두 판정 도구 쪽이고 Chrono 명령과 입력을 바꾸지 않는다. 그래도 도구를 고치는 일(sha 다시 고정, 바뀐 부분 재감사)은 Chrono 결과 파일이 하나라도 생기기 전에 끝내야 한다. 결과 뒤에 고치면 9절 "도구를 결과에 맞춰 고치지 않는다"에 걸린다.
- 7.3 마지막 문장에 따라 이 보고에 적는 상수 sha: 경로 1 `b1_harness_constants_rev1.json` = `3d35a1d81a7c4c4a2e4a40d9c2e3c498753dc0e674fe41491e57007ec52f5ffe`(blob `95c114c8…`), 경로 2 scratch `b1_constants_path2_rev1.json` = `3b5e775b3542f8f1efeb8033f894c4f765944358db73f389d3bb8996b454665c`.
  - 두 상수를 직접 다시 대조했다. 상대차 최대 2.04e-14, 적합 다리 목록은 W_fit 1000·600·2000 N 세 경우 모두 같다. 적합·제외 수: 1000 N에서 전방 κ 13/27·C 4/36, 후방 κ 8/32·C 8/32. 2000 N 감도에서는 후방 κ·C와 전방 C의 적합 다리가 0개라 NA이고, 두 경로가 같다.

## 발견 사항 (심각도순)

**[실행 전 수정][R] 경로 1 D-h의 키 꼴이 P7_REF와 맞지 않는다. D-h는 항상 `K-NA`로 나온다.**
- 근거: `06_analysis/02_control/b1/b1_creep_metrics.py:1675` `key = f"{line['d1_key']}|{line['setting']}|e{float(line['eps']):g}"`
  - 하네스 `d1_key`는 이미 `D1|H-S-0|J2|B|fdown-rec|K1|VB|e0` 꼴이라 끝에 `|VB|e0`가 한 번 더 붙는다.
  - 키만 뽑아 대조한 결과: 경로 1 꼴은 P7_REF P0 키 456개 중 0/20, 경로 2 꼴(`b1_path2.py:1312`, `d1_key` 그대로)은 20/20.
  - 규칙 1.1 `P7_REF` "키는 줄의 `d1.key`로 H-P 실행 키와 맞춘다".
- 실패 시나리오: 경로 1은 D-h를 K-NA("기준에 그 키가 없음")로 내고, 경로 2는 K-SAME 또는 K-DIFF를 낸다. K-R에서 어긋나므로 9절에 따라 D-h는 UNDETERMINED가 된다. 경로 1만 보면 거짓 K-NA다.
- 권장 조치(python-expert): 키를 `line["d1_key"]`로 고친다. 고친 뒤 sha를 다시 고정하고 prelaunch 3절을 고친 뒤 바뀐 부분을 재감사받는다. D-h는 하네스와 P7만 쓰므로 Chrono 결과 전에 하네스 입력만으로 두 경로 D-h가 같은지 확인할 수 있다.

**[실행 전 수정][R] 경로 2에 원판 9절과 6절이 요구한 검사가 빠져 있다. 묶음·행 상태가 두 경로에서 갈릴 수 있다.**
- (a) 정체성 기록을 입력받지 않는다.
  - 경로 2 `row_status`(`path2/b1_path2.py:1338-1368`)는 result.json의 I-3·I-4·I-7만 본다. README A-2도 그렇게 적었다.
  - `--identity`가 없어 I-1·2·5·6·8·10·12~17을 모르고, I-11(C6 제어기 명목 질량)도 보지 않는다. 경로 1은 `b1_creep_metrics.py:1188-1194`(identity)와 `:1143-1152`(I-11)에서 본다.
  - 시나리오: C3 또는 C6의 I 항목 하나가 거짓이면 경로 1은 PARTIAL, 경로 2는 COMPLETE를 낸다. 묶음 상태가 어긋나 모든 등급이 UNDETERMINED가 된다. 규칙대로라면 PARTIAL 등급이 나와야 한다.
- (b) R-G1과 `s9_rows[].pad_nodes`의 일치 검사가 없다.
  - 원판 6절: "두 값이 같아야 한다(다르면 그 행의 격자 기록 전부 기록 무효)". 9절 구현 요구에도 있다.
  - 경로 2에 `pad_nodes`라는 문자열이 아예 없다(Grep 0건). 경로 1에는 있다(`:666-687`, `:612-615`).
- (c) E-5(러너 로그 오류)를 처리하지 않는다. 경로 1만 `blocked`를 낸다.
- 권장 조치(control-expert, 경로 2 작성자)
  - `--identity`(경로 1과 같은 파일)와 pad_nodes 검사를 넣고, Chrono 결과 전에 sha를 다시 고정한다.
  - 또는 결과 전에 "K-R의 행·묶음 상태는 경로 1과 (경로 2 + 정체성 기록 수작업 적용)을 비교한다"를 prelaunch나 개정판에 적는다.

**[실행 전 수정][R] D-b에서 경로 2가 SGS 행의 하네스 δos를 O에 넣는다.**
- 근거: `path2/b1_path2.py:1170-1179`
  - Chrono 자기 δos(`cv`)가 None인 행도 na_rows에 넣기만 하고, `vals`(하네스 VB e0 값)가 있으면 그 max를 `o_vals`에 넣는다.
  - 원판 3.3 D-b: "READY가 없는 행(SGS)은 δos = NA이고, 행 수에서 뺀 것을 적는다".
  - 경로 1(`b1_creep_metrics.py:1465-1468`)은 그 행을 통째로 뺀다.
- 시나리오: SGS로 끝난 행의 하네스 δos가 최대이면 O 값과 OS-MAX/OS-FINAL이 경로마다 달라진다. K-R이 어긋나 D-b가 UNDETERMINED가 된다.
- 권장 조치(control-expert): `cv is None`이면 그 행을 `continue`로 뺀다. 결과 전에 고친다.

**[실행 전 수정][R·E] K-R 대조 도구가 없다. 대조 대상 "M-1~M-12의 모든 수치" 가운데 구조적으로 어긋날 항목이 미리 보인다.**
- 두 출력은 스키마가 다르다(경로 1 `M-1`/`M-4` 블록, 경로 2 `m`/`gm`/`pred`). 대조 도구나 대응표가 저장소와 prelaunch에 없다(Grep `K-R`은 규칙 문장뿐).
- 이미 정해진 불일치 항목
  - ① Chrono M-12: 경로 2는 `m12_*` 키가 없어 NA를 낸다(`:898-902`, README A-5). 경로 1은 c2_soil과 R-G4로 재구성한다(`:1757-1809`).
  - ② E_P-A*와 T-13 "앵커 단일 표본 의존" 표시: 경로 2에는 구현이 없다(Grep 0건).
  - ③ M-4 "LOC 뒤 최대 침하율": 경로 2는 1 ms 계열이고 t_L 표본을 포함한다(`:689-698`). 경로 1은 10 Hz 주기이고 n > n_L만 본다(`:791-807`). 하네스 쪽은 경로 2가 1 ms 계열이 없어 None을 낸다.
- 셋 다 등급에 쓰이지 않는 기록 항목이라 등급이 바뀌지는 않는다. 다만 9절 문자대로면 K-R 불일치다.
- 권장 조치
  - 메인 세션이 결과 전에 K-R 대응표(키 경로 짝)를 고정한다. 위 ①~③을 "한 경로 기록, K-R 제외 또는 정의 차이 공개"로 할지 정한다(확인 필요 1).
  - 같은 꼴의 대조가 되풀이되므로 `위임 필요(python-expert): tools/verif 후보`로 올린다(아래).

**[기록][I] 하네스 커밋 `7246c19`와 G-S 커밋이 실행 HEAD 후보 `bd64cc4`와 다르다(I-9, 2.3 "같은 HEAD_M").**
- `git diff --stat 7246c19 bd64cc4`: `06_analysis/02_control/b1/` 아래 10파일(경로 1·2 도구, 시험, rev1, 상수)만 바뀌었다. `03_src`·`04_scripts`는 0이다.
- 하네스 identity: start·end HEAD 7246c19, clean, `code_diff_sha256` 빈 값, c2 sha `f58ee42b…`가 prelaunch 3절 값과 같다.
- 그래서 I-17 덤프도 7246c19와 bd64cc4에서 같다(c2.py가 바뀌지 않음).
- 처리: prelaunch `HARNESS_VS_RUN_DIFF` 칸에 "03_src 04_scripts 차이 없음(diff --stat 출력)"을 채운다. G-S도 같은 이유로 다시 하지 않아도 되며, 판정서 1절에 적는다.

**[기록][T] 처리 순서 3.0과 실제 순서가 다르다.**
- 실제 순서: 봉인 09:26 → 구현 병합 11:22 → 하네스 11:25:56–11:30:17과 G-S 11:25:55–11:34:08을 동시에 실행 → rev1 봉인 11:59 → 두 경로 sha 다시 고정 12:05 → 상수 커밋 12:08 → prelaunch 12:13.
- 어긋난 점: G-S가 "K 상수 고정"보다 먼저 돌았고, 경로 2 sha는 하네스 뒤에 다시 고정됐다. 후자는 rev1 4절이 정한 절차다.
- G-S 출력은 상수와 무관하므로 편향은 없다. 판정서 1절에 공개한다.
- rev1이 하네스 결과 뒤에 쓰였다는 사실은 rev1 0절에 공개돼 있다(timeline `rev_after_results_declared`). Chrono B1 결과 폴더는 0개다(`07_results/S9`에 GS 폴더뿐).

**[기록][S] 하네스 출력 폴더 `06_analysis/03_hydraulic/coupled/v5/b1/`에 `-text` 보호가 없다.**
- `b1_H.jsonl`은 CRLF 32줄이고 추적되지 않는다. `git check-attr text`는 unspecified, `core.autocrlf=true`다. 원시 바이트 sha `a7099db6`이 prelaunch와 두 경로 입력에 인용된다.
- 커밋하면 정규화돼, 다른 checkout에서 인용 sha가 깨진다. identity.json(CRLF 87줄)도 같다.
- 권장: 커밋하기 전에 `.gitattributes`에 `06_analysis/03_hydraulic/coupled/v5/b1/** -text`를 넣는다.
- 규칙·`.sha256`·상수·prelaunch·경로 1·2는 `06_analysis/02_control/b1/** -text`로 보호되고 모두 LF·BOM 없음이다. 판정 출력 `b1_metrics_path*.json`과 `b1_constants_path2_rev1.json`도 같은 줄로 덮인다.

**[기록][E] E-5와 I-12의 로그 관문이 사실상 비어 있다.**
- `log_errors.py`로 G-S 배치와 하네스 로그를 보면 "errors N" 줄이 없다(`no_errors_line` info 3/1).
- 경로 1은 `runner_log`가 없으면 `(… or 0)`로 막지 않는다(`b1_creep_metrics.py:1851-1853`).
- 실제로 오류를 알려 주는 것은 rc(V-1)다. prelaunch 10.1에 E-5가 읽을 근거를 적는다: rc, 로그의 `Traceback` 검색, `runner_log` 키가 있어야 한다는 조건.

**[기록][I] I-8의 출처 필드 이름이 다르다.**
- 규칙에는 result.json `params_file`로 적혀 있지만, 그런 최상위 키는 없다.
- `meta.params_sha256`(`9b32e36b…`)은 Params 정규화 해시라 YAML 원시 sha와 다르다. YAML 원시 sha `ef2880f9…`는 result.json 안의 `params_file_sha256`(record/meta.json:194와 같은 값)에 있다.
- prelaunch I-8 칸에 대조할 필드를 `params_file_sha256`로 적어야 한다. 그러지 않으면 postrun에서 거짓 I-8 실패가 날 수 있다.

**[기록][E] 경로 1 V-1의 FAULT 종료 판별이 쓰이지 않는다.**
- result.json에 최상위 `final_phase` 키가 없다(G-S 확인). 그래서 `b1_creep_metrics.py:1184` `FAULT_PHASES` 분기는 실행될 수 없다.
- 경로 2는 `FAULT_` 접두 사건이면 정상 종료로 본다(`:1345`).
- run_S9가 FAULT에서 일찍 멈추는 행이 생기면, 경로 1은 MISSING(보수 쪽), 경로 2는 VALID를 내서 K-R이 어긋난다. 정해진 시간까지 다 도는 행에는 영향이 없다.

**[기록][R] 두 경로의 작은 정의 차이**
- (1) b* 동점: 경로 1은 ε_th 안의 첫 다리(`:720`), 경로 2는 정확한 argmax(`:649`).
- (2) 1 ms 계열 끝을 넘는 조회: 경로 1은 None(`:335`), 경로 2는 마지막 표본으로 자른다(`:471`).
- (3) D-a 보정량 기록: 경로 1은 "원시 ZA-2·보정 ZA-1"일 때만(규칙 (나)), 경로 2는 최종이 ZA-2이면 항상 낸다(`:1166`).
- (4) D-h 등급 순위: 일부 NA에 일부 SAME이 섞이면 경로 2는 K-SAME을 낸다(`:1319`). 규칙은 "모두 같음"이다.
- (5) 경로 2는 실행할 때 규칙 파일 sha와 P7_REF sha를 대조하지 않는다. 경로 1은 둘 다 대조한다(`:2033-2041`, `:1663`).
- 대부분 경계 경우에만 차이가 난다. 앞의 실행 전 수정 때 같이 맞추거나 K-R 대응표에 적는다.

**[기록][T·독립성] 경로 2 작성자 transcript `agent-ac0313cdb25a6845c.jsonl`의 도구 호출을 검색했다.**
- 경로 1 파일(`b1_creep_metrics.py`, `b1_harness_constants*.json`, 경로 1 worktree)을 Read·Grep한 기록은 0건이다. 걸린 것은 규칙 초안을 쓰면서 이름이 나온 경우와 handback 문장뿐이다.
- rev1은 30–87행과 97–115행(2·4·5절)만 Read했다. 0·1·7절의 경로 1 상수 요약은 읽지 않았다.
- 경로 1 작성자 transcript `agent-a54833748c3f6b37d.jsonl`에서 경로 2 파일이 나온 곳은 prelaunch 해시 표를 Write한 경우뿐이다(내용을 Read한 기록 없음).
- [추정] 02:40Z handback의 "알려 주신 Q-1 Ŵ 문제"라는 말은 경로 2가 상수를 계산하기 전에 메인 세션이 Ŵ 문제(경로 1 결과 요약에서 나온 사실)를 알렸다는 뜻일 수 있다. 판정서의 독립성 공개에 한 줄 넣는 것을 권한다.
- 02:18Z에 메인 세션이 경로 2 코드의 색인 방식을 짚어 고치게 한 지시도 공개 대상이다(스키마 사실 전달).

**[기록][I] G-S 폴더가 아직 전체 출력을 담고 있다.**
- 규칙 2.3은 "끝나면 키 목록만 남긴다"이다. 그런데 `07_results/S9/batch_V5-B1-CREEP-GS_20261112_112555`에는 result.json·npz 전체가 남아 있다.
- 키 목록을 따로 남기고 정리할지, 남겨 둔 채로 공개할지 정한다.

## 규칙↔도구 대조표 (요약)
| 규칙 | 경로 1 | 경로 2 | 판단 |
|---|---|---|---|
| rev1 R1-1 Ŵ = r_i ΣF − F_i, Ê = r_i ΣF(`n` = n_L 행) | `:852-859`, `:843-846` | `:757-762` | 같음 |
| R1-2 C[max(Ê,F^pk)^5 − F^pk^5] | `:862-867` | `:420-424` | 같음 |
| R1-3 적합 집합(T-15 −1e-6 N), κ 비 inf, 감도 0.6·2 kN | `:1287-1348` | `:1013-1076` | 같음(상수 대조 2e-14) |
| R1-4 합 비 [1.00, 1.08], n_L 신장 | `:1351-1372` | `:1097-1110` | 같음 |
| R1-5 T-15 | `EPS_N` 1e-6 | `EPS_N` 1e-6 | 같음 |
| 문턱 T-1~T-6·T-13·T-14 | `:103-110` | `:46-52`, 코드 리터럴 | 같음 |
| 0.4 위상 범위(후방 −1.3/+4.2 %, 전방 −2.8/+5.0 %) | `:119` | `:54` | 같음 |
| R-C1은 n 색인, R-G1은 n_cycle + computed | `:600-637` | `:560-580` | 같음 |
| 격자 간격 static.grid_m → pads[i] → 오류 | `:640-654` | `:539-557` | 같음 |
| 3.2 묶음 상태(핵심 4 + H-P VB e0 5) | `:1813-1818` | `:1458-1465` | 같음 |
| V-2 정체성 | identity + 자체 검사 | I-3·4·7만 | **다름** |
| 6절 pad_nodes 일치 | 있음 | 없음 | **다름** |
| D-b SGS 행 처리 | 행을 뺌 | 하네스 값 포함 | **다름** |
| D-h 키 | `d1_key|setting|e` | `d1_key` | **경로 1 결함** |
| M-12 Chrono, E_P-A*, T-13 | 재구성 | NA, 미구현 | **다름(기록 항목)** |
| 2.1 행 6개 argv | `b1_creep_chrono_rows.py:60-67` | — | 표와 같음. `check` errors 0, `list` 6행 |

## 확인 필요
1. K-R에서 이미 정해진 기록 항목 불일치(Chrono M-12, E_P-A*·T-13, 최대 침하율)를 어떻게 다룰지 정한다. "한 경로 기록, K-R 제외(공개)"로 할지, 결과 전에 정의를 맞추는 개정판을 낼지다. 등급에는 영향이 없다.
2. 경로 2 정체성 입력: 경로 2를 고칠지, K-R의 행·묶음 상태를 "경로 2 + 정체성 기록 수작업 적용"과 비교한다고 결과 전에 적을지 정한다.
3. G-S 폴더를 "키 목록만" 남기고 정리할지 정한다(2.3).

## 위임 필요
- python-expert(경로 1): `b1_creep_metrics.py:1675` D-h 키를 `line["d1_key"]`로 고친다. 시험에 실제 P7 키 꼴 예시를 하나 넣는다. sha를 다시 고정하고 prelaunch 3절을 고친다. 선택 사항으로 `:1851` `runner_log`가 없으면 입력 오류로 하고, `:1184` FAULT 판별을 실제 키(`phases` 마지막 또는 사건)로 바꾼다.
- control-expert(경로 2): `path2/b1_path2.py`에서 (a) `--identity` 입력과 I-11, (b) pad_nodes 일치 검사, (c) D-b `cv is None` 행 제외(`:1176-1179`), (d) 선택 사항으로 규칙·P7 sha 대조와 docstring의 rev1 언급(1–8행)을 고친다. 경로 1 코드는 보지 않고 규칙 문장만으로 고친다. 고친 뒤 sha를 다시 고정한다.
- 위임 필요(python-expert): tools/verif 후보 `kr_compare`
  - 입력: 두 경로 출력 json과 키 경로 대응표 json
  - 출력: 항목별 일치·불일치(이산은 완전 일치, 실수는 절대차 1e-9 m), 대응표에 없는 키 목록
  - 종료 코드: 0 일치 / 1 불일치 / 2 입력 오류

## 메인 세션 권고
- 시작 직전: prelaunch 3절 sha 표를 다시 잰다(`RUN_SHA_RECHECK`). 위 도구를 고쳤다면 경로 1·2 sha 칸도 고친다.
- I-2 기대값으로 행 모듈 `argv` 하위 명령이 낸 `argv_level_sha256`를 배치 폴더 prelaunch에 옮긴다.
  - C1 `af7d176e…b027fb1`
  - C2 `80c074e4…ede6cfa3`
  - C3 `1dfd69db…c931b1a`
  - C4 `4f3506e1…b2744da6`
  - C5 `8e0c4c8f…a2744da6`
  - C6 `c6f2ee1b…bbf1c950`
- 실행 중(두 물결, 약 5 h) master 병합·커밋을 금지한다(I-10, main checkout에서 실행). 다른 worktree 브랜치도 병합하지 않는다.
- 본 실행 명령 블록(prelaunch 9절)을 확인했다.
  - env 4개 제거와 `git rev-parse`·`status` 전후 확인이 들어 있다.
  - `s9_batch.py run V5-B1-CREEP --schedule …schedule_main.json` 형식이 맞다(`--schedule`은 run 하위 명령 인자, `s9_batch.py:1956`).
  - 배치표: `parallel_p` 4, `e_cases` 없음, 핵심 4행 → C6 → C3 순서, sha `3d3b0117…`가 맞다.
  - `-I`가 있고 OMP는 배치가 넣는다(G-S에서 `start_env` PASSIVE 확인).

## 검사하지 못한 것
- 경로 1 pytest와 경로 2 selftest는 다시 돌리지 않았다.
- 경로 1 judge와 경로 2를 G-S 입력으로 돌리지 않았다(출력 파일을 쓰는 실행이라). 그래서 K-R 키 대응은 코드 읽기로만 확인했다.
- I-17 도구는 다시 실행하지 않았다(prelaunch 기록 값을 인용).
- 하네스 32실행의 판정 수치는 읽지 않았다. 다만 하네스 로그 끝 5줄에서 H-SH0·H-M0 실행 몇 건의 종료 상태 이름(fault/ready)이 눈에 들어왔다(공개).

## 실행한 검증
- 인터프리터: python-dev `python.exe -I -B`(MKL_THREADING_LAYER=TBB, 한글 출력에는 -X utf8). 행 모듈 `check`·`argv`와 `s9_batch.py list`는 Chrono-dev `python.exe -I -B`(건조 실행, 쓰기 없음, `__pycache__` 수 32→32, 추적 변경 0).
- seal_check
  - 두 판 모두 raw 일치, `-text`, LF, BOM 없음
  - `--const` 7개(경로 1 두 상수, 경로 2 두 상수, preset_dump_diff, harness, rows) 모두 일치
  - `--quoted prelaunch`의 미해결 해시는 git blob, 배치표, 경로 2 scratch, 격자 문서 해시였고 직접 해시해 모두 맞음
  - `code_pin_missing` 3건(rows, harness, preset_dump_diff가 rev1을 고정하지 않음)은 rev1이 실행 단위를 바꾸지 않으므로 정상
- gate_scan: `all_without_count_guard` 2건은 고정 튜플 위의 all이라 오탐이다. `min_default` 1건은 기록 항목이다.
- record_check identity `b1_H.jsonl`: 32건, `rules_sha256`·`schema` 균일, 발견 0.
- timeline: rev1이 하네스·G-S 뒤이고 그 사실을 선언했다(`rev_after_results_declared`).
- placeholder_scan: prelaunch.md·상수·keymap에서 0건. 규칙 파일에서 걸린 것은 LaTeX 첨자(`_{L1}`, `^{C6}`)라 오탐이고, `prelaunch_draft.md`의 94건은 틀 자리다.
  - 규칙 I-13의 `--allow`(파일 이름)와 도구의 `--allow`(자리 이름)는 뜻이 다르다(기록).
- log_errors: G-S·하네스 모두 `no_errors_line`.
- 즉석 스크립트(scratchpad `verif_b1pre\`, 보고 전에 폴더째 지움): G-S 키 목록·정체성 값 출력, D-h 키 대조, 두 경로 상수 대조, transcript 도구 호출 검색 2개.
- 최종 판정 전에 `b1_creep_metrics.py:1675`를 다시 Grep해 같은 줄인지 확인했다. HEAD는 감사 내내 `bd64cc4`, 추적 변경 0이었다.
- 메모리 `audit_pitfalls.md`·`MEMORY.md`에 일반 함정 3개를 추가했다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha b1_creep_rules.md 6b99702c…, b1_creep_rules.sha256 a269959a…, b1_creep_rules_rev1.md 9f72af5b…, b1_creep_rules_rev1.sha256 07026005…, b1_creep_prelaunch.md 06b4f145…, b1_creep_metrics.py a9518c65…, b1_preset_dump_diff.py 2acb3755…, b1_path2.py f4f8be83…, b1_keymap.json 19021bc6…, b1_harness_constants_rev1.json 3d35a1d8…, b1_harness_constants.json 0dd09ad0…, b1_H.jsonl a7099db6…, b1_grid_record.py 198cf3bb…, b1_creep_chrono_rows.py 5a243a1a…, b1_harness.py 565b2317…, b1_record.py 9344e00f…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음

---

## 메인 세션 처리 (2026-11-12)

- 사용자 결정: Chrono 6행을 지금 시작하고 도구 수정은 worktree에서 병행한다. 첫 행이 끝나기 전에 수정 도구 sha와 K-R 대응표를 고정한다. 그 전에 못 끝내면 결과 뒤 수정으로 공개하고 묻는다. 병합은 postrun 뒤.
- 확인 1: 기록 항목 세 가지(Chrono M-12, E_P-A*·T-13, M-4 최대 침하율)는 경로 1 값만 기록하고 K-R에서 뺀다(결과 전 대응표에 적고 판정서에 공개).
- 확인 2: 경로 2를 고친다(--identity, I-11, pad_nodes 일치, D-b SGS 행 제외; 규칙 문장만 보고).
- 확인 3: G-S 폴더는 남겨 두고 공개한다(규칙 2.3과 다름).
- 실행 HEAD = bd64cc405990101ca8f3398ba2b9db9edcfc01b4. 하네스·G-S HEAD 7246c19와의 차이는 06_analysis/02_control/b1/ 아래 10파일뿐이고 03_src·04_scripts는 0(감사 기록).
