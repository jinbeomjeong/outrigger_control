# D8x 검증 범위 확장 판정서 (하네스 단계, 2026-11-10)

- 작성: control-expert, 2026-11-10 14:2x(+09:00). 메인 세션이 판정 후 감사·integrity 뒤 커밋한다(이 파일과 아래 산출물은 작성 시점 미추적).
- 고침: 2026-11-10, 판정 후 감사(`d8x_post_audit.md`, 차단 0·실행 전 수정 0·기록 6) F-1~F-6 반영과 사용자 확인·선택 기록. **등급은 바뀌지 않았다.**
- 대상: 원판 `d8x_rules.md` + rev1~rev6(봉인 7판, 5.2절). 판정 대상 묶음 G0, R-a, R-c. Chrono(C) 19행은 **돌리지 않았다**(사용자 결정 "미달이면 분석까지만", 원판 5.0 B-G1 "Chrono는 멈춘다").
- 새 시뮬레이션은 돌리지 않았다. 저장 결과를 읽고 집계만 했다.
- 규약: 기체 x 전방·y 좌측·z 상방, roll + = 왼쪽 높음, pitch θ > 0 = 앞내림. 각도는 바닥 경사 [°]. 힘은 참 실린더 순 힘 또는 패드 법선력 [N, kN]. 제어기는 이산 $T_s$ = 0.1 s, 출력 지연 $d$ = 1(R8 C2). 되먹임은 이 판정과 무관(시간 응답 집계)하다.

| 기호 | 뜻 | 값 |
|---|---|---|
| $F_{min}$ | 다리당 평균 하중 10 % | 9,414.589 N |
| $F_{D8}$ | D8 선 $F_{min}$ + 5 kN | 14,414.589 N |
| $R_v$ | 검증 사용률 $\lvert\varphi_g\rvert/5.7 + \lvert\theta_g\rvert/\Theta(\theta_g)$, $\Theta$ = 3.7(앞내림)·3.6(앞들림) | – |
| J3 | 패드 부상: TOUCH 끝 뒤 패드 법선력 $F_{cyl} + W_{rod} \le 0$인 1 ms 청크 수 | 0이어야 통과 |

## 1. 판정

**등급: 미달(분기 B-G1).** 두 경로 행 판정은 **일치**한다.

| 관문 | 결과 | 근거 |
|---|---|---|
| G-S | 통과 | 봉인 7판 raw 일치(5.2절), 실행 전 감사 차단 0(`d8x_prerun_audit.md` → `d8x_prerun_reaudit.md` "차단 0, 남은 수정 0"), 점 파일 I-3 통과(두 경로). 구현 시험은 이 판정에서 다시 돌리지 않았다 |
| G0 | **통과** 60/60 | 경로 1 `gate_G0 = pass`(재계산 60, 재사용 0, 닫힘 blob 19개 = `ba6671c`), 경로 2 `G0 pass 60/60` |
| G1 | **실패** | R-a 1,102 중 **74 fail**(K1 끔 910 중 68, K1 켬 192 중 6), 판정 불가 0. R-c 288 모두 pass. 실패 항목은 74행 모두 **J3 하나뿐**이다 |
| G2a·G2b | 실행 안 함 | B-G1(원판 5.0·11) |
| G3 | 두 경로 일치는 이 판정서에서 확인(6절). 판정 후 감사(verif-protocol-auditor, 원문 `d8x_post_audit.md`) 차단 0·실행 전 수정 0·기록 6. I-2/I-2b는 Chrono가 없어 **해당 없음**(사용자 확인 2026-11-10) | – |

- **F-1 손 적용(rev4 1.4):** K1 켬 팔 fail 경로 1 `len(k1_rows_failed)` = 6 / 경로 2 `k1_rows_fail` = 6, 같고 0보다 크다. 끔 팔도 68 fail이라 G1은 손 적용 전에도 실패다. **도구 등급: 경로 1 `report` `not_judgeable`, 경로 2 `미달`(provisional) → 판정 등급 미달.**
  - 경로 1 `report`의 `not_judgeable`은 묶음·G1 판정 불가가 아니다. 원인은 **G3 플래그 미지정**(`--recount-agrees`·`--audit-post-clear`·`--carry-over-confirmed`, 판정서 전이라 주지 않음)이다. `_grade`에서 G3 검사가 fail 검사보다 앞에 있다(`d8x_judge.py` 1324행 G3 → 1326행 fail). Chrono 묶음 수 검사(1328행)는 fail 검사 뒤라 이번 결과에 영향이 없다. 묶음·G1은 경로 1에서도 `fail`이다(`gates.G1 = "fail"`, R-a 종료 1, R-c 종료 0). rev5 3.1-1(도구 판정 불가 우선)은 "R-a·R-c 묶음 또는 G1을 판정 불가로 낼 때"이므로 적용되지 않는다.
  - rev5 3.1-6 순서(판정 불가 > 미달 > …)로 보면 판정 불가 관문이 없다(G-S·G0 통과, G2는 분기로 미실행, 두 경로 일치). 그래서 **미달**이다.
  - 해석 하나: rev5 3.1-2 "판정서의 최종 집계는 원판 3절의 모든 입력(… Chrono)이 들어간 실행에서만 한다"를 글자대로 읽으면 Chrono가 없는 이 판정서는 쓸 수 없다. 그러나 원판 5.0·11은 G1 실패면 Chrono를 멈추고 분석해 묻도록 정한다. 또 rev5 3.1-6 등급 순서(판정 불가 > 미달 > 보류)는 G2가 미실행(보류)인 상태에서 G1 실패가 미달로 가는 경우를 예정한다. 이 판정서는 3.1-2를 "G1 입력(R-a 끔·켬, R-c 끔·켬, G0)이 다 들어온 뒤"로 읽었다. G1 입력은 기대 수 그대로 모두 들어왔고(E-1), 어느 도구도 G1을 보류로 내지 않았다. **이 해석과 G3 I-2 "해당 없음"은 판정 후 감사를 거쳐 사용자가 확인했다(2026-11-10).**
- **A-2 손 적용(rev5 2.1):** 켬 팔 `INFO_LIFTOFF_SLOW` 수는 두 경로 모두 72키 전부 0이다. 끔 팔도 0이다. **도구 LAS_INACTIVE → 손 적용 뒤에도 LAS_INACTIVE.** V-2b 재실행 대상 없음.
- **V-1:** 짝 288(R-a 192 + R-c 96), 두 경로 모두 `K1_INVARIANT`. K1 켬 팔 6 fail은 끔 팔 td_main 6 fail과 **같은 id**이고, 짝마다 `commands_sha256`·J3 값이 같다(6.3절).
- **FLAG**(등급 영향 없음, G1이 먼저 막음): (i) J1·J2 < $F_{D8}$ + 2 kN 0건(J1 최소 R-a 36.62 kN, R-c 44.03 kN), (ii) 행정 여유 < 5 mm 0건(R-a 최대 671.43 mm → 가드 682.8 mm까지 11.4 mm, R-c 676.16 mm → 6.6 mm), (iii) 0건, (iv) G0-4 오차 > 0.02° 0건. K1 켬 팔 (i)·(ii) 기록도 0건.
- **W 선정**(G1 실패라 쓰지 않음, 기록): 두 경로 모두 `r+p+0.25` → `dxpp025`, $m$ = 43,127.913 N. d45 앞내림 점이 아니므로 rev2 3 위험(A1 여유 0.0015)은 현실화되지 않았다.

## 2. 시간 순서와 실행 정체성

| 시각(+09:00) | 일 |
|---|---|
| 13:15:08 | `d8x_expect_k1.json` 작성(sha256 `055e1a50…065ebd`) |
| 13:18:58~13:19:10 | chk-g0, head-g0, G0 rev3 재계산(11 s), g0-judge(경로 1, `--at-commit ba6671c`) |
| 13:19:11~13:35:52 | R-a 끔 prelaunch, head, 실행 910(992 s) |
| 13:35:52~13:40:49 | R-a 켬 prelaunch, head, 실행 192(288 s) |
| 13:40:50~13:53:08 | R-c 끔 chk, prelaunch, head, 실행 192(735 s) |
| 13:53:08~14:00:53 | R-c 켬 prelaunch, head, 실행 96(461 s) |
| 14:09:02 | 경로 2 `d8x_path2_harness.json` |
| 14:11:14~14:11:36 | 경로 1 judge-g0(재실행)·judge-ra·judge-rc·invariance·select-w·report(이 판정서 작성자) |

- $H_{impl}$ = master `ba6671c4faaf7a26773dcfb9f554ce2491b466ed`(메인 세션 지정, rev5 4). 실행 위치 main checkout. 러너 로그 사본 `.local_archive/session_6f3ebc4d_20261110/d8x_harness_runner/d8x_logs_P/`: 모든 단계 exit 0, `.done` 각 1개(재시작 없음). R-a `wall_s_this_start` 983.7 s = 단일 시작.
- 판정서 작성 시점(14:18) HEAD `ba6671c`, `git status --porcelain --untracked-files=no` 빈 상태. 경로 1 코드 blob = HEAD blob(`d8x_judge.py` `d2d9dd60…`, `d8x_spec.py` `6c45050a…`, `d8x_record.py` `d43fe594…`).
- 경로 2 산출(14:09:02)이 경로 1 산출(14:11:14~)보다 먼저다. 경로 2는 경로 1 출력을 읽지 않는다(원판 8).

### 2.1 개정 이력·통합 브랜치 커밋 (판정 후 감사 C-6·C-7)

- C-6(rev6 4 엄격 조건): rev6 4는 "실행 기록의 규칙 봉인 목록이 rev6까지 담지 않으면 원판 G-S 봉인 관문에서 판정 불가"로 정했다. 이번 실행 기록(G0 `meta.rules_seals`, R-a `meta.d8x.rules_seals`, R-c sidecar 각 start·end 항목, prelaunch 4개 `rules`)은 **모두 7판(원판~rev6)을 담고 모두 `ok`**다(5.1·5.2절). 그래서 이 조건으로 판정 불가가 되지 않는다.
- C-7: 통합 브랜치 `worktree-agent-ac6cd65fc4ec57212`의 커밋(커밋 시각 +09:00, `git show -s --format=%ci`). 모두 결과(13:18:59 시작) 전이다.

| 커밋 | 시각 | 내용(제목 요약) |
|---|---|---|
| `064a498` | 11:28:19 | `d8x-impl`(rev2 구현)을 K1 전환 위에 병합 |
| `20e8722` | 11:28:25 | G0 rev1 브랜치 병합 |
| `c2e35a5` | 12:01:13 | K1 전환 뒤 D8x: K1 끔 팔 명시, `_LAS_K1` 태그, E-6 시험 |
| `d98c935` | 12:03:55 | rev1 채택, 규칙 rev3·rev4 봉인 병합 |
| `fca7f46` | 12:03:55 | master `c731f4b` 병합(K1 전환 감사 원문) |
| `8c9e8b1` | 12:09:18 | `d8x-gate-meta` 병합(Chrono 실제 K1 관문 기록) |
| `b311169` | 12:15:26 | 경로 1 rev3·rev4: 봉인 rev4까지, E-6a~f, G0 rev3 재계산, G1 두 팔 |
| `dc416d8` | 12:29:26 | 규칙 rev5 봉인 병합 |
| `260c16d` | 12:34:07 | 경로 1 rev5: 봉인 rev5까지, Chrono E-6d 다섯 키, `k1_rows_failed` 없음 = 종료 2 |
| `fa612cc` | 12:35:11 | 규칙 rev6 봉인 병합 |
| `dd3440b` | 12:37:33 | 경로 1 rev6: 봉인 rev6까지, V-2 사건 목록 결측 = 판정 불가, G0 봉인 기록 |
| `0cbb320` | 12:44:40 | rev6 봉인 점검 R-1~R-3: 모든 행에 팔·결합 키, 실행 기록에 봉인 |
| `5fd1d11` | 12:45:06 | master `cd54f9f`를 통합 브랜치에 병합 |
| (master `99293a8`) | 13:02:22 | 통합 브랜치를 master에 병합 |
| (master `ba6671c` = $H_{impl}$) | 13:03:22 | `test_las_t3` 병합(T-3 도구 본문 불변) |

## 3. 규칙과 다른 실행

- 원판 3절 표·Q5는 하네스를 "E코어"로 적었다. **사용자 결정(2026-11-10 14시경)으로 하네스 묶음 전체를 P코어에서 돌렸다**(`d8x_prerun_record.md` 2절, 실행 전 감사 P-3). 이유: P코어가 비어 있었고(배경 9~19 %) E코어는 상주 프로세스가 약 31 %를 썼다. 원판 I-1은 "P코어 묶음은 배치표 값"을 허용하고, 하네스는 단일 스레드 결정론 계산이라 풀이 판정 값에 들어가지 않는다. rev7 없이 실행 전 기록과 이 절로 처리했다(사용자 결정).
- 배치(러너 로그에서 옮김): affinity `0xFFFF`(P 16논리), worker 8(끝까지), 우선순위 Normal, 완전 순차. 18단계 모두 `MKL_THREADING_LAYER=TBB`, `MKL/OMP/NUMBA/OPENBLAS_NUM_THREADS=1`. 실행 기록의 마스크도 `0xffff`다(5.1절).
- 그 밖에 규칙과 다른 실행은 없다.

## 4. 결과 전에 본 것 (공개)

| 시점 | 본 것 | 판정 사용 |
|---|---|---|
| rev3 봉인 뒤·rev4 봉인 전 | 탐침 3건(rev5 1.2): R-a `main\|C2_tv0.1\|top\|rigid\|pitch+` K1 끔(J1 61.0 kN, READY 43.4 s), R-c `fdown3.7` top VB ε 0 끔·켬(J1 53,835.95 N, READY 57.5 s). 통합 브랜치 `20e8722`, dirty | 안 씀 |
| rev5 봉인 뒤 | G0 rev3 탐침(rev6 공개, `b311169`) 60/60 `pass` | 안 씀 |
| 보존 | `.local_archive/session_6f3ebc4d_20261110/d8x_probes/`(`SHA256SUMS.txt` `0e239c7a…`, `SHA256SUMS_add.txt` `35889499…`) | – |

- 탐침에는 J3 실패 신호가 없었다. R-a 탐침 키(top·rigid·main·pitch+)는 정식 실행에서도 J3 통과(TOUCH 뒤 최소 패드 법선력 15.99 kN)다. 정식 R-a·R-c·G0 rev3 결과는 실행 전 0건이었다(재감사 "시작 상태").

## 5. 정체성 (P-2 손 확인)

### 5.1 정체성 표

| 기록 | HEAD | clean | 마스크 | MKL 계층 / 스레드 | Python | 봉인 기록 |
|---|---|---|---|---|---|---|
| G0 `d8x_g0_rev3.json` `meta.run_commit`·`clean`·`identity` | `ba6671c4…66ed` | true(시작·끝 status 빈 문자열) | `0xffff` | TBB / 1 | 3.12.15 | 7판, 경로 1 `rev6 4` 문제 0 |
| R-a 끔 `meta.git_head` / `identity_start` / `identity_end` | `ba6671c4…` / 같음 / 같음 | – / true / true | `0xffff` | TBB / 1(시작·끝) | 3.12.15 | 7판 모두 `ok` |
| R-a 켬 같은 키 | 같음 | true / true | `0xffff` | TBB / 1 | 3.12.15 | 7판 `ok` |
| R-c 끔 `hrx_off.identity.json` start[0]·end[0] | `ba6671c4…` | true / true | `0xffff` | TBB / 1 | 3.12.15 | 7판 `ok`(두 항목) |
| R-c 켬 `hrx_on.identity.json` start[0]·end[0] | `ba6671c4…` | true / true | `0xffff` | TBB / 1 | 3.12.15 | 7판 `ok` |
| prelaunch `ra_off`·`ra_on`·`rc_off`·`rc_on` `head` | 넷 모두 `ba6671c4…` | 넷 모두 true, `not_in_commit` 0 | `0xFFFF` | 기대값 TBB / 1 | dynamics-dev 3.12.15 | `rules` 7판 `ok` |

- 모두 $H_{impl}$·clean이다. sidecar 항목은 묶음마다 start 1·end 1개(재시작 없음).
- 태그 히스토그램(E-6, rev3 3.2): R-a 끔 `final_C4G2_LAS` 910, 켬 `final_C4G2_LAS_K1` 192, R-c 끔 VB `final_C4G2_P3_LAS` 96·V0 `final_C4G2_LAS` 96, 켬 VB `final_C4G2_P3_LAS_K1` 48·V0 `final_C4G2_LAS_K1` 48. 다른 태그 0. prelaunch 기대 태그와 같다.

### 5.2 규칙 봉인 손 확인 (rev6 4 = rev4 2-1 대체 문구)

**경로 2 `RULES_SHA256`(62~65행)은 원판·rev1·rev2만 대조한다. rev3·rev4·rev5·rev6의 봉인 일치는 경로 2가 보지 않으므로, 판정서 작성자가 각 `.sha256` 파일과 직접 해시로 손 확인하고 값을 적는다.**

| 파일 | raw sha256(판정 때 다시 계산) | `.sha256` 파일 안에 있음 | 경로 2 대조 |
|---|---|---|---|
| `d8x_rules.md` | `a377b9bb028385bb7d7d97312a71816ba0ca758e2cb193e25b2d092fff064da8` | 예 | pass |
| `d8x_rules_rev1.md` | `ad16f452fb4dce7395a059c73d7caf213f1a9a69f18af8d230bf03f4518e80d4` | 예 | pass |
| `d8x_rules_rev2.md` | `5f3fa620fe704834a9b6c0a65824b29b75e2a527ea8e97a17abb5e07987a8c27` | 예 | pass |
| `d8x_rules_rev3.md` | `2318fb5cf75b64b525c515566776ed1ec6cbb10743621edc04c092d6774c7301` | 예 | 보지 않음 |
| `d8x_rules_rev4.md` | `5233c517e6c0d17b0e26e902673e0d6990532ed1c54c82ae0801e688d50702a5` | 예 | 보지 않음 |
| `d8x_rules_rev5.md` | `63437019eaee2340fbbfc45efdcf78bfc5ba314f83085d55f19e323c6f5ffabe` | 예 | 보지 않음 |
| `d8x_rules_rev6.md` | `d584c8dafcb1aea9f289a4ffaf9f27cbcc9aa9d22da504a764fb44f041624697` | 예 | 보지 않음 |

- 경로 1은 실행마다 7판 봉인을 확인한다(`seals` 7판 모두 true). 실행 기록(G0 `meta.rules_seals`, R-a `meta.d8x.rules_seals`, R-c sidecar 각 항목 `rules_seals`, prelaunch `rules`)도 7판을 담는다(rev6 4 충족).

### 5.3 인용 파일 (F-3: `-text`와 sha256)

모든 인용 파일은 `git check-attr text` = `unset`(`-text`)이다. 아래 결과 파일은 작성 시점 git 미추적이라 `git ls-files --eol` 항목이 없다(규칙·`.sha256`·`d8x_points.json`은 추적됨: 규칙 `i/lf w/lf attr/-text`, 점 파일 `i/crlf w/crlf attr/-text`).

| 파일(`06_analysis/…`) | sha256 |
|---|---|
| `02_control/d8x/d8x_expect_k1.json` | `055e1a50e485d9589c4b39e51ae939b59325b7e595e5d15421b3d2b3eb065ebd`(결과 전 기록값과 같음, rev4 2-3) |
| `02_control/d8x/d8x_points.json` | raw `050145f6a965c851a014563f6219e61c1081716eb5ad5f7e8469a098d426c817`, LF 정규화 `a02a382f2509813f1caa1cb884984004d8caef7f66a5b7c9ab946eeda88c2eee`(R-a `meta.d8x.points_sha256`·경로 2 `sha256_lf`) |
| `00_dynamics/d8x_g0_rev3.json` | `7bd00422c6a96d951409684c950524e17b21eddc979581967c8b11aa5141a551` |
| `02_control/d8x/ra/ra_off.json` | `100985bfe00fa02e4c1c5c938ad9e08e83b441c00d666403dc60526fed3dcb10` |
| `02_control/d8x/ra/ra_on.json` | `e3c8c95ffd6a34afc10d119c27a0b29bf5a6d892ac6a4b8c78bd6edafd7f247a` |
| `02_control/d8x/rc/hrx_off.jsonl` | `2adae54fb118aa0b52c8970e313923c3b03978860d2a38c4c35d3076cfc73ef3` |
| `02_control/d8x/rc/hrx_on.jsonl` | `2ce7190d17071196b251a0e3b6bbc54d43d1c0df5586405d46a841acd2a37408` |
| `02_control/d8x/rc/hrx_off.identity.json` | `94215a401b15ce34bedc9d2c7fa729816a85e7074bdbad65ff7b13e811093b0d` |
| `02_control/d8x/rc/hrx_on.identity.json` | `b1e37d6180cbb9f1f74d2df28c257fb0020e66ee962374635b47b75892d14207` |
| `02_control/d8x/d8x_prelaunch_ra_off.json` / `_ra_on` / `_rc_off` / `_rc_on` | `5b19e36b…6e5f` / `f8108c74…a51` / `fc6f944b…5092` / `78e6c270…73dc` |
| `02_control/d8x/d8x_path2_harness.json`(경로 2) | `823493ced2fd23797d6373d4383a3f5b7576cda97fca8c47cfefc3c926397f6c` |
| 경로 2 도구 `.local_archive/session_9d4aec18_20261110/d8x_path2/d8x_recount.py` | `46010967729e190ab572775db9dd59b083a3856558c3f07a239bf601bed9d9d1`(리포트 `tool_sha256`과 같음, 결과 전 고정값과 같음) |
| `02_control/d8x/d8x_g0_judgement.json`(경로 1, 러너) | `676b330cb5b13004fb71bf0030cc22f2ed4cb48d3bf8ed76d2344796ebb972a1` |
| `02_control/d8x/d8x_p1_g0_rerun.json`(경로 1, 이 판정) | `676b330c…72a1`(러너 출력과 바이트 동일) |
| `02_control/d8x/d8x_p1_ra_judgement.json` | `01d50281d8727440d2b90c6885f94f0be23e4bb1e000a8550d0864b397874a1e` |
| `02_control/d8x/d8x_p1_rc_judgement.json` | `99da92fae5ea0a9a215a29f026b10281d65ec77916f1dfb939fd8ca3d7439646` |
| `02_control/d8x/d8x_p1_invariance.json` | `889798568e16df7e83e62cd1babe49638ed5f48d1bcb73a5ef9f271b7e45cd77` |
| `02_control/d8x/d8x_p1_select_w_record.json` | `e393655e3b000d18f10956526b1229cc133ad66624d7d9bef1c5b6fe2c05becd` |
| `02_control/d8x/d8x_p1_report.json` | `d95d614e5f1b08b2acd409eba79ca608a959cab6ff2336f6bb616814c721b83e` |
| `02_control/d8x/d8x_g1_fail_rows.csv`(실패 74행 표, 이 판정) | `0979cfcec0d23f37c0d5669ed33e50408803bb3234d0e7775d55b032b55816db` |

- 경로 2 리포트 `expect.source` = `06_analysis/02_control/d8x/d8x_expect_k1.json`(rev3 3.3 확인).

## 6. 두 경로 대조 (원판 8, rev6 1)

### 6.1 키 대응과 표기

| 경로 1 | 경로 2 | 비고 |
|---|---|---|
| R-a 행 결합 `id` + `k1` | `id` + `k1` | 실행 전 기록 3절 |
| R-c 행 결합 (`slope_name`, `level`, `crawler_k_scale`, `setting`, `eps`) + `k1` | (`floor`, `level`, `crawler_k_scale`, `setting`, `eps`) + `k1` | `floor` = `slope_name` |
| V-2 키 `ra\|<point>\|<level>` | `["R-a", <point>, <level>, n]` | rev6 1 |
| V-2 키 `rc\|<slope_name>\|<level>` | `["R-c", <floor>, <level>, n]` | rev6 1 |
| verdict `pass` / `fail` / `not_judgeable` | `pass` / `fail` / `unjudgeable` | 표기 대응 |
| 드라이버 오류 행 `not_judgeable` | `fail`("E-2 driver error") | 알려진 차이 → B-ID. **이번 실행 오류 행 0건**이라 생기지 않음 |

### 6.2 행 대조 결과

| 항목 | R-a 끔 910 | R-a 켬 192 | R-c 끔 192 | R-c 켬 96 |
|---|---|---|---|---|
| 키 집합 같음 | 예 | 예 | 예 | 예 |
| verdict 다른 행 | 0 | 0 | 0 | 0 |
| fail 행의 실패 항목 집합 다른 행 | 0(모두 `J3`) | 0(모두 `J3`) | – | – |
| 수치(J1, J2, 행정 최대) 상대차 > 1e-9 | 0 | 0 | 0(J1) | 0(J1) |

**판정: 일치**(행별 verdict, 묶음 수, 관문, W, V-1·V-2 분류 모두 같음, 수치 차 0).

### 6.3 묶음·K1 켬 팔 표 (rev5 3.2 의무 표)

| 경로 | 묶음 | 팔 | expected | actual | pass | fail | unjudgeable | 도구 G1 | 손 적용 G1 |
|---|---|---|---|---|---|---|---|---|---|
| 경로 1 | R-a | 끔 | 910 | 910 | 842 | 68 | 0 | fail(두 팔) | fail |
| 경로 1 | R-a | 켬 | 192 | 192 | 186 | 6 | 0 | 〃 | fail |
| 경로 1 | R-c | 끔 | 192 | 192 | 192 | 0 | 0 | pass(묶음) | pass |
| 경로 1 | R-c | 켬 | 96 | 96 | 96 | 0 | 0 | 〃 | pass |
| 경로 2 | R-a | 끔 | 910 | 910 | 842 | 68 | 0 | fail(끔 팔) | fail |
| 경로 2 | R-a | 켬 | 192 | 192 | 186 | 6 | 0 | `k1_rows_fail` 6 | fail |
| 경로 2 | R-c | 끔 | 192 | 192 | 192 | 0 | 0 | pass | pass |
| 경로 2 | R-c | 켬 | 96 | 96 | 96 | 0 | 0 | `k1_rows_fail` 0 | pass |

- 경로 1 `k1_rows_failed`(B-4: `judge-ra`·`judge-rc` 출력과 `report` 출력 **모두에 키 있음**): R-a 6 = `main|C2_tv0.1|top|stiff|pitch+`, `…|top|upper|pitch+`, `…|top|upper|r+p+0.25`, `…|top|rigid|r+p+0.5`, `…|top|stiff|r+p+0.5`, `…|top|upper|d45-+`. R-c `[]`. `report.problems` 빈 목록.
- 경로 2 `bundles["R-a"].k1_rows_fail` = 6, `bundles["R-c"].k1_rows_fail` = 0(`None` 아님). 두 경로 수가 같다(rev5 3.1-4).
- 켬 팔 6 fail id = 끔 팔 td_main fail 6 id(같은 집합). td_main 192 짝 모두 (`commands_sha256`, J3 수, TOUCH 뒤 최소 패드 법선력)이 끔·켬 같다.

### 6.4 V-1·V-2·W·G0

| 항목 | 경로 1 | 경로 2 | 일치 |
|---|---|---|---|
| V-1 | 짝 288, `K1_INVARIANT`, `K1_DEPENDENT` [] | 짝 288, `K1_INVARIANT`, [] | 예 |
| V-2 끔 팔 | 72키 모두 0, `LAS_DEPENDENT` [] | 72키 모두 0, `LAS_INACTIVE` | 예 |
| V-2 켬 팔(rev5 2.1 손 적용) | 72키 모두 0(사건 목록에서 셈) | 72키 모두 0(`record.las_events`) | 예. 결측 0(rev6 2: 모든 행이 (i)) |
| W(기록) | `r+p+0.25` / `dxpp025`, 43,127.913 N, 순위 11점 같음 | 같음 | 예 |
| G0 | `pass` 60, 실패 0 | `pass` 60/60 | 예 |
| FLAG | 0 | 0 | 예 |

- V-2 표(rev5 3.2 둘째 항목, 72키를 한 행으로 압축. 칸별 값은 `d8x_p1_invariance.json` `V-2.counts_by_arm`):

| (묶음, 점, 단계) | 끔 팔(도구) | 켬 팔(경로 1) | 켬 팔(경로 2) | 분류 |
|---|---|---|---|---|
| R-a 16점 × 3단계 48키 + R-c 8바닥 × 3단계 24키 = 72키 모두 | 0 | 0 | 0 | `LAS_INACTIVE` |

- (판정 후 감사 C-4) rev6 2 결측 처리의 적용 순서: (iv)·(v)(행 없음, 드라이버 오류·`d8x` 블록 없음, 또는 `fail`·불가 행의 사건 목록 없음)가 (i)·(ii)보다 먼저다. 이번에는 오류 행 0, 사건 목록 결측 0(경로 1 `missing_events` [], `record_only_rows` []; 경로 2 `las_events` `None` 0)이라 모든 행이 (i)이다.

**G0 기록 항목(원판 4.3 기록, 판정에 안 씀; `d8x_g0_rev3.json` 60평가)**

| 로드 SF 최소 | μN 이용률 최대 | $s_{max}$ 여유(G0-1) 최소 | 20 mm 틈 결과 | G0-4 관문 4점 역산 |
|---|---|---|---|---|
| 확장 하중 C45 1.295 / 20MnV6 1.911(middle `roll-`), YAML 하중 C45 0.842 / 20MnV6 1.242(top `roll-`). `rod_pair_ok_1.5` 거짓 9평가(세 단계 × `pitch-`·`roll+`·`roll-`) | 확장 μ 0.713(top `roll+`), YAML μ 1.000(top `roll-`). YAML μ 미끄럼 표시 6평가(세 단계 × `roll±`), 확장 μ 미끄럼 0 | +0.34 mm(bottom `d45-+`) | 틈 20 mm 행정 여유 최소 30.38 mm(bottom `d45-+`) | 오차 최대 0.0180°(top `pitch+`), $\hat R_v$ 최대 1.004917(top `pitch+`) ≤ 1.005 |

- 로드 SF 쌍·μN은 원판 4.3에서 기록 전용이다. 로드 소재(C45 여부)는 제조사 확인 대기(CLAUDE.md 미정 사항)이며 이 판정 등급과 무관하다.

**두 경로 일치의 범위(판정 후 감사 F-2):** J3 수(`J3_pad_lift_samples`)와 최소 패드 법선력은 하네스 안의 `d8x_record.py` `run_metrics`(245~259행)가 실행 중에 기록한 값이다. 두 경로는 이 기록값을 각자 읽어 같은 판정을 냈으므로 **두 경로 일치는 집계의 일치이고, J3 창 정의(TOUCH 끝부터 1 ms 청크 법선력 ≤ 0)의 독립 검증은 아니다.** 창 정의는 결과 전에 정해졌다(`d8x_record.py`의 마지막 변경 커밋 `0cbb320`, 12:44:40; `0cbb320`과 $H_{impl}$ `ba6671c` 사이 이 파일 차이 없음).

## 7. 두 경로 범위 차이 (rev4 2, rev6 4, rev3 3.3 의무 문구)

1. (rev6 4) **경로 2 `RULES_SHA256`(62~65행)은 원판·rev1·rev2만 대조한다. rev3·rev4·rev5·rev6의 봉인 일치는 경로 2가 보지 않으므로, 판정서 작성자가 각 `.sha256` 파일과 직접 해시로 손 확인하고 값을 적는다.** 값은 5.2절.
2. (rev4 2-2) G0 출처 점검: `--g0-base`를 주지 않았으므로 경로 2 `judge_g0`는 출처(재사용 0 / 재계산 60, `meta.rules_rev`, 실행 커밋 닫힘 blob)를 보지 않는다. 경로 1이 본 값: `meta.rules_rev` "rev3", reuse 0, recompute 60, `run_commit` `ba6671c4…`, clean true, 닫힘 blob 19개가 `ba6671c`와 모두 같음(`differences` 없음). rev3 4 기록: rev3 60평가와 rev1(e37f42c) 60평가의 `G0_COMPARE_KEYS` 차는 모두 0(`rev1_nonzero` 0).
3. (rev4 2-3) `--expect` 파일 sha256: 결과 전 기록 `055e1a50e485d9589c4b39e51ae939b59325b7e595e5d15421b3d2b3eb065ebd`, 판정 때 다시 계산한 값 같음.
4. (rev3 3.3) 경로 2는 Chrono 행의 `k1_order_gate`를 보지 않는다. 이번에는 Chrono 행이 없어 해당 없음.

## 8. 실패 분석 (B-G1)

### 8.1 무엇이 깼나

- **74행 모두 J3(패드 부상) 하나만 실패했다.** J1·J2·J4~J9·J11, E-2·E-3·E-8은 1,102행 모두 통과다(FAULT·WARN·REJ 0, 드라이버 `fails` 0).
- 경로 1의 J3 정의(`d8x_judge.py` 140행, `d8x_record.py` 245~259행): TOUCH 끝(`adapter.t_touch`, 네 패드 접지 판정) 뒤 1 ms 청크의 최소 패드 법선력 $F_{cyl}+W_{rod} \le 0$인 청크가 하나라도 있으면 fail. 원판 4.1 J3 "접지 뒤 참 법선력 ≤ 0, 0회"와 같다.
- 실패 행의 물리량

| 양 | 값(실패 74행) | 뜻 |
|---|---|---|
| TOUCH 뒤 최소 패드 법선력 | 모두 **0.0 N**(정확히 0) | 일방향 접촉이 실제로 떨어짐(접촉력 0으로 잘림) |
| 부상 청크 수 | 12~386(중앙 100) ≈ 12~386 ms | 짧은 접촉 상실 |
| 크롤러 이탈 뒤 최소 실린더 힘 J1 | 36.62~56.30 kN(> 0) | 부상은 **TOUCH 끝 ~ 크롤러 이탈 사이**(창 0.9~1.3 s)에서만 났다. 이탈 뒤에는 모든 다리 $F_{cyl}$ > 0이라 법선력 > 0 |
| 첫 READY | 42.2~44.8 s(≤ 120) | J5 통과 |
| READY 뒤 자세 오차 | ≤ 0.045° | J4 통과 |
| 판독 최대 행정 | ≤ 670.95 mm(가드까지 ≥ 11.9 mm) | 행정과 무관 |
| `INFO_LIFT_PAUSED`(P30fz 느린 들어 올림) | 실패 70/74행에서 작동. 다리: RR 57, RL 25, FR 8, FL 2(건수). 같은 점·상단의 통과 행도 215/274행에서 작동 | 하중이 빨리 빠지는 다리를 잡았지만 접촉 상실을 막지 못함 |

- 어느 패드가 떴는지와 정확한 시각은 저장 결과에 없다(J3는 수와 최솟값만 기록). `INFO_LIFT_PAUSED`·`INFO_TOUCH_DIP_HELD` 다리로 보면 앞내림 꼭짓점은 후방 두 다리, 대각·변 위 점은 roll 낮은 쪽의 후방 다리(`d45++`·`r+p+*` → RR, `d45-+`·`r-p+0.5` → RL; 앞내림 바닥에서 후방은 오르막 쪽)가 후보다. **추정**이며, 확정은 시계열 재생이 필요하다(11절 권고).

### 8.2 어디에 몰렸나 (K1 끔 팔 910)

| 구분 | fail / 전체 |
|---|---|
| 오거 단계 | **top 68/596**, middle 0/157, bottom 0/157 |
| 단계 | td_main 6/192, td_robust 52/592, td_kt 10/126 |
| 마스트(상단) | rigid 16/170, stiff 28/170, upper 24/128, **lower 0/128** |
| 변형 | β 1.6 16/112, β 0.69 6/112, d0 s0·s1·s2 각 6, seed 1·2 각 6, kt·ktd0 ×0.12 1·×0.40 2·×1.21 2(각 28·14 중) |
| 지면 | R-a·R-c 모두 강체 지면(SCM 없음, Q4). R-c(v5 하네스, $F_s$ 4 kN) 288행은 J3 0건 |

- d0 s0은 main과, d0 s1·s2는 seed 1·2와 명령 해시가 같은 궤적이다. 서로 다른 궤적으로 세면 끔 팔 68 fail은 **45궤적**이다(pitch+ 12, r+p+0.5 10, d45++ 6, d45-+ 6, r+p+0.25 4, r-p+0.5 4, r+p+0.75 2, roll− 1).

**상단 점 × 마스트(fail/전체), 그리고 TOUCH 뒤 최소 패드 법선력(상단 td_main, rigid / stiff / upper / lower) [kN]**

| 점 (φ, θ) | 위치 | rigid | stiff | upper | lower | 최소 법선력 td_main [kN] |
|---|---|---|---|---|---|---|
| `pitch+` (0, 3.7) | 앞내림 꼭짓점 | 0/14 | 12/14 | 8/8 | 0/8 | 15.99 / 0 / 0 / 16.49 |
| `r+p+0.25` (1.425, 2.775) | (+,+) 변 | 1/14 | 0/14 | 6/8 | 0/8 | 9.76 / 22.35 / 0 / 14.10 |
| `r+p+0.5` (2.85, 1.85) | (+,+) 변 중점 | 9/14 | 8/14 | 0/8 | 0/8 | 0 / 0 / 9.13 / 24.20 |
| `r+p+0.75` (4.275, 0.925) | (+,+) 변 | 1/8 | 1/8 | 0/8 | 0/8 | 13.69 / 1.98 / 13.34 / 21.98 |
| `d45++` (2.2627, 2.2627) | (+,+) 대각, $R_v$ 1.0085 | 2/14 | 5/14 | 1/8 | 0/8 | 7.41 / 7.08 / 1.15 / 14.61 |
| `d45-+` (−2.2627, 2.2627) | (−,+) 대각, $R_v$ 1.0085 | 1/8 | 0/8 | 8/8 | 0/8 | 8.75 / 7.39 / 0 / 15.09 |
| `r-p+0.5` (−2.85, 1.85) | (−,+) 변 중점 | 1/8 | 2/8 | 1/8 | 0/8 | 8.08 / 0.17 / 7.72 / 25.14 |
| `roll-` (−5.7, 0) | roll 꼭짓점 | 1/14 | 0/14 | 0/8 | 0/8 | 19.49 / 17.33 / 17.60 / 31.12 (fail 1행은 robust β 1.6) |
| `roll+` (5.7, 0) | roll 꼭짓점 | 0/14 | 0/14 | 0/8 | 0/8 | 20.50 / 17.98 / 18.02 / 31.57 |
| 앞들림 7점(θ < 0: `pitch-` −3.6, `r+p-*` 3점, `r-p-0.5`, `d45+-`, `d45--`) | 앞들림 꼭짓점·변·대각 | 0 | 0 | 0 | 0 | 상단 전 행 최소 11.53 kN(`d45+-` stiff) 이상 |

- **실패는 앞내림 쪽(θ > 0) 사분면 두 개와 앞내림 꼭짓점에 몰렸다.** 예외는 roll− 꼭짓점 1행(상단 rigid β 1.6)이다. **앞들림 3.6° 쪽은 꼭짓점·변·대각 모두 실패 0**이다. 새 경계 가운데 roll 5.7은 roll+ 0건, roll− 1건이다.
- 상단 앞내림 쪽은 통과 행도 여유가 작다. TOUCH 뒤 최소 패드 법선력(K1 끔 팔, 상단)의 중앙값 [kN]:

| 점 | 상단 전 행(실패 포함) 중앙값 | 통과 행만 중앙값(행 수) |
|---|---|---|
| `pitch+` | 4.00 | 15.99(24) |
| `r+p+0.5` | 1.43 | 9.10(27) |
| `d45++` | 7.39 | 7.69(36) |
| `r-p+0.5` | 7.77 | 8.08(28) |
| 앞들림 7점 | 22~39(실패 0이라 통과 행과 같음) | 같음 |
- 마스트 경우마다 실패 점이 바뀐다(예: `pitch+` rigid 0/14, stiff 12/14; `r+p+0.5` rigid 9/14, upper 0/8). 마스트 하한(lower)은 0이다. 접지 판정이 로킹의 어느 위상에서 걸리는가 하는 **이산 사건 민감도**(3.9.7.8 표 아래 "접지·크롤러 이탈 과도 하중" 행과 같은 성격)로 읽힌다(**추정**).
- R-c(v5 하네스)는 같은 앞내림 꼭짓점·대각 방향에서 통과했다: 상단 `fdown3.7` 최소 9.32 kN, `rpX` 16.19 kN, `rpX-+` 19.91 kN. R-a(FlexPlant, 마스트 4경우)와 R-c는 플랜트가 다르다(R-c: 유압 연성 하네스, $F_s$ 4 kN, 마스트 강체). R-c 통과는 R-a 실패를 상쇄하지 않는다(G1은 둘 다 요구).

### 8.3 이 실패가 새 범위 때문인가 (중요한 한계)

- **J3의 창(TOUCH 끝 ~ 크롤러 이탈)은 이전 검증에서 잰 적이 없다.** 3.9.7.8(R8 C2 890건, "부상 없음")과 옛 D8 576(`d8_both.json`)의 최소 힘·부상 기록은 **크롤러 이탈 뒤** 구간만 본다(`run_mast_flex_c2_check.extra_metrics` 560~568행, `d8_both.json` 행 키에 TOUCH 뒤 패드 법선력 없음). 따라서 현 검증 범위 5.5° / 3.5°가 이 J3를 통과하는지는 **저장 결과로 알 수 없다.**
- 실패한 점의 옛 마름모 사용률은 1.04~1.06(예: `pitch+` 3.7/3.5 = 1.057, `r+p+0.5` 1.047)으로 옛 경계 바로 밖이다. 상단 앞내림 쪽 통과 행의 법선력 여유가 0~수 kN이라는 점을 보면, 옛 경계에서도 J3가 걸릴 가능성을 배제할 수 없다(**추정**, 근거 없음).

### 8.4 사후 분석: 범위를 어디까지 줄이면 통과하는가 (판정에 쓰지 않음)

- **저장 결과로는 통과 경계를 추정할 수 없다.** R-a·R-c 점은 모두 새 마름모 경계 위($R_v$ = 1, d45 앞내림 1.0085)에 있어 안쪽 점이 없다. G0는 정적 계산이라 J3의 과도를 다루지 않는다.
- 저장 결과가 말해 주는 것은 방향뿐이다.
  - 통과 확인(모든 단계·마스트·변형): 앞들림 반축 3.6°와 앞들림 두 사분면, roll+ 5.7° 꼭짓점, 중·하단 전부.
  - 실패: 상단 앞내림 두 사분면(꼭짓점 3.7°, 변, d45 3.2°), 상단 roll− 5.7° 1행.
- "앞들림 쪽만 넓히고 앞내림은 그대로"나 "상단만 앞내림 반축을 줄임(B-G1 (b) 단계별 반축)"은 **줄일 값 X를 저장 결과로 정할 수 없고**, 옛 범위 자체의 J3 상태도 모른다. 줄이는 안을 택하면 새 점(안쪽)과 옛 경계 기준선을 돌려야 한다(11절).

## 9. 기록 전용 항목 (원판 4.2)

| 항목 | 값 |
|---|---|
| 판독 최대 행정, 가드 682.8 mm까지 여유 | R-a 671.43 mm(11.4 mm), R-c 676.16 mm(6.6 mm) |
| 크롤러 이탈 뒤 최소 실린더 힘 | R-a 36.62 kN(실패 행 `beta…top|stiff|r+p+0.75|1.6e+09`), R-c 44.03 kN |
| 최대 이동 압력 | R-a 122.4 bar, R-c 119.0 bar(≤ 210) |
| READY 뒤 자세 최대 오차 | R-a 0.0453°, R-c 0.0183°(≤ 0.2°) |
| 첫 READY | R-a ≤ 44.8 s, R-c ≤ 58.5 s |
| INFO 사건 수(`INFO_TOUCH_DIP_HELD` / `INFO_TOUCH_TWIST_HOLD` / `INFO_LIFT_PAUSED`) | **두 팔 합**: R-a 1,031 / 748 / 620, R-c 67 / 175 / 17. **K1 끔 팔만**: R-a 902 / 615 / 537, R-c 47 / 117 / 11. `INFO_LIFTOFF_SLOW` 0(두 묶음·두 팔) |
| VB − V0 J1 차(V-3, R-c 끔 96짝) | −2.37 ~ +0.65 kN |
| H4(J2) | 하네스는 H4 꺼짐(`reanchor_skipped:disabled`), J2 대상 행 0 |
| 로드 SF, μN, 마스트 상대 회전, Chrono−하네스 차 | 이번 단계에 없음(Chrono 미실행, G0 기록은 `d8x_g0_rev3.json`) |

## 10. 위험·알려진 한계

- (rev2 3 의무 위험 문구) W가 d45 앞내림 점으로 뽑히면 A1 허용까지 남는 여유는 1.01 − 1.008505 = 0.0015뿐이고, L2b 정착 자세가 바닥과 약 0.0055°보다 더 다르면 #6 시작이 `REJ_SLOPE_D8`로 거부될 수 있다. **이번 W는 `r+p+0.25`라 해당 없음**(G1 실패로 W도 쓰지 않음).
- J3 창은 이전 검증(3.9.7.8, 옛 D8)에 없던 구간이다(8.3절). 이 판정의 J3 실패는 "확장 범위"와 "TOUCH~크롤러 이탈 이양 과도" 가운데 어느 쪽 원인인지 저장 결과로 가를 수 없다.
- 부상 다리·시각·지속은 저장 결과에 없다(수와 최솟값만). 8.1의 다리 추정은 `INFO_*` 사건 다리로 본 것이다.
- 하네스는 강체 지면·이상 센서(시드 축 제외)·$\tau_v$ 0.1 s(**가정**)다. 실기 패드 접촉 순서·크롤러 제하 강성은 미확인(CLAUDE.md 미정 사항)이다.
- Chrono 19행과 I-2/I-2b는 이번 단계에 없다(판정 후 감사는 `d8x_post_audit.md`로 수행됨).
- 이 판정은 시간 응답 집계라 Julia 경로는 쓰지 않았다. 두 경로(경로 1 `d8x_judge.py` ↔ 경로 2 `d8x_recount.py`)는 서로 다른 코드가 같은 원 결과 파일을 읽은 독립 집계다.

## 11. 사용자 결정이 필요한 선택지

| # | 선택지 | 하는 일 | 비용·위험 |
|---|---|---|---|
| **1(추천)** | **진단 먼저(판정 아님), 그다음 결정** | (a) 실패 2~3행(`main\|…\|top\|stiff\|pitch+`, `main\|…\|top\|rigid\|r+p+0.5`, `main\|…\|top\|upper\|d45-+`)을 시계열 저장으로 다시 돌려 어느 패드가 언제 떴는지와 기전(크롤러 이양 중 하중 재분배·로킹 위상·P30fz 작동 시점)을 확정한다. (b) **현 검증 범위 5.5° / 3.5° 경계 16점 상단**(앞내림 쪽 우선)을 같은 J3 정의로 돌려 기준선을 잡는다 | (a) 행당 약 1~1.5분, `acc_d8.py`에 단일 id·시계열 저장 기능이 없어 python-expert 추가 필요. (b) 상단 main+robust 약 500행, P 8 worker로 약 10분(R-a 끔 910행 992 s 실측 비례). 새 점 파일은 판정용이 아니라 진단용으로 표시 |
| 2 | 검증 범위를 줄여 재판정(B-G1 (a)·(b)) | 앞내림 반축(또는 상단만 단계별 반축)을 줄인 새 마름모로 rev7 봉인 → 구현(`verification_ext` 단계별·방향별 반축이면 python-expert) → R-a·R-c 재실행. 앞들림 3.6°는 이번 결과로 J3 통과 | 줄일 값을 저장 결과로 정할 수 없다(8.4). 1(b)에서 옛 범위도 J3 실패면 줄여도 통과하지 않을 수 있다 |
| 3 | 제어기 수정(B-G1 (c)) | TOUCH 끝~크롤러 이탈 이양 구간의 들어 올림 규칙(P30fz 느린 들어 올림 조건, 첫 들어 올림 속도, 하한 감시)을 고쳐 패드 접촉을 유지. 별도 설계·봉인·회귀 | 1(b)에서 옛 범위도 실패면 이쪽이 맞다. 현 운용 범위에도 영향이 가므로 범위가 크다 |
| 4 | 현 5.5° / 3.5° 유지, D8x 종료 | D8x를 미달로 닫고 문서는 바꾸지 않는다(원판 10: 반영 문서는 통과·조건부 통과 때만) | 가장 싸다. 단 현 범위의 J3(이양 구간 패드 부상) 상태는 모른 채 남는다(8.3) |

- **사용자 선택(2026-11-10, 판정 후 감사 뒤): 선택지 1 "진단 먼저".** (a) 실패 2~3행 시계열 재생, (b) 현 5.5° / 3.5° 경계 기준선. 둘 다 **판정용이 아니다**(진단 산출물과 점 파일에 "판정 아님"을 표시한다). 진단 뒤 범위 축소(rev7)를 하게 되면, 그 개정은 **이 판정 결과와 진단 결과를 본 뒤의 개정**임을 rev7 공개 절에 밝힌다.
- **추천(작성 당시): 1.** 이유: 실패가 상단·앞내림·이양 구간 한 기전에 몰려 있지만, 그 구간을 이전에 잰 적이 없어 "범위 확장 탓"인지 "현 범위에도 있는 제어기 거동"인지 저장 결과로 가를 수 없다. 1(b)가 그 갈림을 정한다. 옛 범위 통과면 2(앞내림 축소 또는 단계별 반축), 옛 범위 실패면 3(제어기)과 현 운용 범위 재확인으로 간다.
- **하지 말 것:** 결과를 본 뒤 J3 창(TOUCH 끝부터)이나 문턱(0회)을 완화하는 개정. 결과에 맞춘 완화라 사전 봉인 원칙에 어긋난다.

## 12. 실행 명령과 산출물

경로 1(이 판정, dynamics-dev, 작업 폴더 `C:\workspace\outrigger_control`, `MKL_THREADING_LAYER=TBB`):

```powershell
$c='C:\ProgramData\miniforge3\Scripts\conda.exe'; $D='06_analysis/02_control/d8x'
& $c run -n dynamics-dev python -I -B 04_scripts/03_control/d8x/d8x_judge.py --out $D/d8x_p1_g0_rerun.json judge-g0 --g0 06_analysis/00_dynamics/d8x_g0_rev3.json --at-commit ba6671c   # exit 0
& $c run -n dynamics-dev python -I -B 04_scripts/03_control/d8x/d8x_judge.py --out $D/d8x_p1_ra_judgement.json judge-ra --off $D/ra/ra_off.json --on $D/ra/ra_on.json --prelaunch $D/d8x_prelaunch_ra_off.json   # exit 1
& $c run -n dynamics-dev python -I -B 04_scripts/03_control/d8x/d8x_judge.py --out $D/d8x_p1_rc_judgement.json judge-rc --off $D/rc/hrx_off.jsonl --on $D/rc/hrx_on.jsonl   # exit 0
& $c run -n dynamics-dev python -I -B 04_scripts/03_control/d8x/d8x_judge.py --out $D/d8x_p1_invariance.json invariance --ra-off $D/ra/ra_off.json --ra-on $D/ra/ra_on.json --rc-off $D/rc/hrx_off.jsonl --rc-on $D/rc/hrx_on.jsonl   # exit 0
& $c run -n dynamics-dev python -I -B 04_scripts/03_control/d8x/d8x_judge.py --out $D/d8x_p1_select_w_record.json select-w --g0-judgement $D/d8x_g0_judgement.json --ra-off $D/ra/ra_off.json --rc-off $D/rc/hrx_off.jsonl --selection-out <scratchpad>\d8xjudge\selection_p1.json   # exit 0, 기록용
& $c run -n dynamics-dev python -I -B 04_scripts/03_control/d8x/d8x_judge.py --out $D/d8x_p1_report.json report --g0-judgement $D/d8x_g0_judgement.json --ra-judgement $D/d8x_p1_ra_judgement.json --rc-judgement $D/d8x_p1_rc_judgement.json --invariance $D/d8x_p1_invariance.json --audit-pre-clear   # exit 2 (1절 설명)
```

- `select-w`의 `--selection-out`은 scratchpad로 돌렸다(`d8x_selection.json`을 만들지 않음, G1 실패로 W를 쓰지 않음).
- 경로 2(메인 세션, 14:09): `d8x_recount.py recount --points … --g0 … --ra ra_off.json --ra-k1 ra_on.json --rc hrx_off.jsonl --rc-k1 hrx_on.jsonl --expect d8x_expect_k1.json --rules-dir 06_analysis/02_control/d8x` → `d8x_path2_harness.json`. 경로 2 출력은 덮어쓰지 않았다.
- 두 경로 대조·실패 분석 스크립트(보조, 판정 도구 아님): scratchpad `d8xjudge\compare.py`, `fail_analysis.py`, `matrix.py`, `fail_csv.py`.
