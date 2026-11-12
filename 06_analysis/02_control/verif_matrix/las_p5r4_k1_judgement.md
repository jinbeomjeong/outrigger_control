# LAS-b P5r4 + K1 재판정 판정서

- **상태: 확정**(2026-11-12, 사용자 결정 "미달 확정·P0 유지·판정서 커밋", 10절). 초안 `las_p5r4_k1_judgement_draft.md`(sha256 `398e62242df70f1b5200f012876718c0f70d8e52680d1b2ee6d79e75f6ea39a5`)에 판정 후 감사 `las_p5r4_k1_post_audit.md`(차단 0)의 기록 2~8과 확인 1·2 결정, 그리고 D-2 진단 결과를 반영했다. 등급·K-10은 초안과 같다.
- 작성: control-expert(경로 2 작성자), 2026-11-12. 판정 기준 HEAD `8ea3aa1a099adc65e167bc81266959ddc601157e`(= JUDGE_COMMIT = Chrono 실행 HEAD = postrun HEAD, postrun_r2 08:35:35·judge 08:36:22 시점). 그 뒤 2026-11-12 09:26:21에 `1ad3e5d`(B1 규칙 문서 6개만, `06_analysis/02_control/b1/`, 코드 경로 0)가 master에 들어왔다. **이 판정서는 `1ad3e5d` 위에 커밋한다**(무관 문서 커밋 1개). 하네스 판정 커밋은 `18b1425`다(2.1절).
- 규칙(모두 LF sha256 = `.sha256` 첫 토큰, 2026-11-12 재계산)

| 판 | sha256 | 봉인 시각(`.sha256` 기록) | 봉인 커밋·커밋 시각(K1 원판 8절 #1) |
|---|---|---|---|
| 원판 `las_p5r4_k1_rules.md` | `5ee2bac0451f0ca00139a5a2d238c38d13a6b0f430efc5b44fe0e8b929c2f979` | 2026-11-11 09:29:16 +09:00 | `d6c65b5` 09:29:34 |
| rev1 | `f39846d6067a7bd409b4ac930d73ebde58a721728ec7d93703ff4627bf21e4b6` | 10:40:10 | `9bcbcaa` 10:40:20 |
| rev2 | `e0a7d1e56b57df5336fc2fd40835624d93585fb224063f6c8068c2b1ba7b10fc` | 11:04:55 | `1b03bbb` 11:04:55 |
| rev3 | `31ba01dff9defb4b7274b27b9df1a427c460fa9ccc5efd84f5a3145e0d3ef8f6` | 12:51:28(재봉인) | `0827c8f` 12:51:36(첫 봉인 `561d158` 12:45:20은 무효, 2.2) |
| rev4 | `aff149c345d78ea2e03f29acc9412c886c3913fc3574c19b9053b3b3a02ccfaf` | 23:17:19 | `8ea3aa1` 23:18:29 |

- 모든 봉인 커밋은 해당 판의 결과보다 앞선다(원판~rev3는 하네스 첫 줄 13:44:43 전, rev4는 Chrono r2 시작 23:28:32 전).

## 1. 판정

| 층 | 경로 1 (잠정) | 경로 2 (잠정) | K-10 | 확정(이 판정서) |
|---|---|---|---|---|
| 하네스 Z-0·Z-A·Z-T·Z-S·Z-C·Z-X | 모두 `통과` | 모두 `통과` | 일치 | **`통과`** |
| Chrono `V5-LAS-P5R4-K1` r2 | `미달`(G-2′C, CC-S, CC-R) | `미달`(같은 셋) | 일치 | **`미달`** |
| 최종(16.6) | `미달` | `미달` | 일치 | **P5r4 `미달` → P0 유지 권고** |

- `stop`·`undecidable`은 어느 층에도 없다. 그래서 16.6 우선순위로도 최종은 `미달`이다(SK-5 즉시 확정, 되돌리지 않음).
- **v5 제어기는 `final_C4G2_LAS_K1`(VB `final_C4G2_P3_LAS_K1`) 그대로다.** 이 규칙은 프리셋을 바꾸지 않는다(원판 0.2).
- 사용자 사전 채택 방침("통과면 v5 뒤 후보")은 미달이므로 해당 없다.
- 미달 짝 요약(원인은 8절)

| 기준 | 짝 | 값 | 문턱(rev3 RV3-1 허용 포함) | 어긋난 크기 |
|---|---|---|---|---|
| G-2′C | A3/A4(VB, Kc3) | cand RL $F^{C}_{after}$ = $F^{C}_{tr}$ = 11,356.209 N | ≥ 11,414.589 − 1e-9 N | −58.380 N(−0.51 %) |
| CC-S | B1/B2(G1+J1@FL) | FL $s_{max}$ 438.603 → 441.430 mm, $\Delta s$ = +2.827 mm | ≤ 1.000 mm + 1e-9 m | +1.827 mm |
| CC-R | 해시가 바뀐 4짝 | $\Delta t$ = {+1.2, 0.0, 0.0, +7.7} s, 중앙 +0.6 s, 최대 +7.7 s | 중앙 ≤ 1.0 s, 최대 ≤ 5.0 s | 최대 +2.7 s(B1/B2) |

### 1.1 기호

| 기호 | 뜻 | 단위 |
|---|---|---|
| $F^{C}_{after}$ | Chrono `p3b.P3-3_leg_force.F_min_after_N`의 다리별 최소(크롤러 이탈 뒤, 1 ms 참 $F_{cyl}$) | N |
| $F^{C}_{tr}$ | 같은 블록 `F_min_transient_N`(이탈 + 8 s까지) | N |
| $s_{max}$ | `p3b.P3-5_clearance_stroke.s_motor_max_m`의 다리별 최대 | m |
| $\Delta s$ | $\max_i s^{cand}_{max,i} - \max_i s^{ref}_{max,i}$ | m |
| $\Delta t$ | cand − ref `P3-6_ready.t_ready_after_loop_start_s` | s |
| $F_{min}$ | 9,414.589 N(YAML `control.F_min_cylinder_N`) | N |
| β, $N_r$ | LAS-b `light_leg_fraction_of_F_min`, `end_ramp_periods` | —, 주기 |
| $T_s$ | 제어 주기 0.1 s(10 Hz, 출력 지연 $d$ = 1, 음되먹임 C2) | s |

판정식(rev3 RV3-1, $\epsilon_{thr}$ = 1e-9, 필드 단위):

$$\text{G-2′C: } \min_i F^{C}_{after,i} \ge 11414.589 - \epsilon_{thr} \;\wedge\; \min_i F^{C}_{tr,i} \ge 11414.589 - \epsilon_{thr}$$
$$\text{CC-S: } \Delta s \le 0.001 + \epsilon_{thr}, \qquad \text{CC-R: } \operatorname{median}(\Delta t) \le 1.0 + \epsilon_{thr},\; \max(\Delta t) \le 5.0 + \epsilon_{thr}$$

## 2. 공개 (원판 1절·13절 체크리스트, 감사 1·2·3·4)

### 2.1 실행 HEAD·커밋

| 항목 | 값 |
|---|---|
| 하네스 실행 HEAD | `18b1425`(2026-11-11 12:59:47, prelaunch 추적 해제 커밋, rev3 RV3-3 1) |
| 하네스 실행 | 13:44:43 ~ 16:09:40(Z-0 → Z-A → Z-T → Z-S → Z-C → Z-X, 모두 exit 0, `errors_left` 0), env 기록 `env_main_harness.txt`(13:44:43) 0바이트 |
| **하네스 판정 커밋** | **`18b1425`**. 경로 1 2026-11-11 16:22:32, 경로 2 16:22:42. 그 사이 첫 커밋은 `7a469f7`(22:51)이므로 이때 HEAD는 `18b1425`다. 하네스 판정 시점에 실제 자리 JUDGE_COMMIT(`commands.md:119`)·POSTRUN_HEAD(`:157`)·BATCH_CHRONO(첫 배치 시작 16:23:05 뒤 채움)가 채워지지 않은 상태였다(감사 3에서도 미채움으로 확인). `commands.md:119`(§5 "하네스 판정" 안)에 지금 들어 있는 값 `8ea3aa1a…`는 **Chrono 판정 커밋**이고 하네스 판정 커밋이 아니다(판정 후 감사 기록 2). 2.6절 S-10 읽기 참고 |
| 첫 Chrono 배치 | `07_results/S9/batch_V5-LAS-P5R4-K1_20261111_162306`, 16:23:06 ~ 22:28:09, 12행 END `rc=0`, `log_errors.py`(progress.log `rc`) 발견 0. **postrun(22:42:20) K-1 `stop`**: `git status --porcelain --untracked-files=no` 허용 밖 2줄 ` M .claude/agents/paper-reviewer.md`, ` M CLAUDE.md`(실행 중 다른 세션의 문서 수정). **판정에 쓰지 않았고 값은 누구도 읽지 않았다(rev4 RV4-1).** 이 판정서도 progress.log START/END `rc`, `log_errors`, postrun 정체성 필드만 봤다. 첫 배치 env 기록 `env_main_chrono_before.txt`(16:23:05)는 0바이트다 |
| env 기록 0바이트 두 개의 뜻(감사 4 기록 4) | `env_main_harness.txt`·`env_main_chrono_before.txt`는 러너 셸에서 `Get-ChildItem env:OUTRIGGER*, env:OMP*, env:MKL*`를 `OMP_WAIT_POLICY` 설정 전에 찍은 것이다. 해당 변수가 셸에 없으면 출력이 없으므로 0바이트가 맞다. 다만 0바이트만으로는 "변수 없음"과 "기록 실패"를 가르지 못한다. 판정은 실효 값으로 한다(16.5): 하네스 줄 스레드 변수 모두 `1`·`MKL_THREADING_LAYER` `TBB`, Chrono result.json `placement.omp_wait_policy` `PASSIVE`. r2 기록부터는 변수가 없을 때 "none" 한 줄을 남겼다 |
| 하네스 결과를 본 뒤 Chrono 재실행(감사 3 기록 4, rev4 RV4-0.2) | Chrono r2는 하네스 결과(판정 16:22) 뒤에 결정·실행됐다. 원판 S-6 순서(하네스 `통과` 뒤 Chrono)는 원래 그렇다. 재실행 이유는 첫 배치 postrun 정체성 `stop`(K-1)이고 값을 보고 다시 돈 것이 아니다. 바뀐 것은 HEAD(문서 2줄 `7a469f7` + 봉인 `8ea3aa1`)뿐이고 행·argv·풀·스케줄은 그대로다. 첫 배치 값은 아무도 읽지 않았다. **새 배치 12행 `rerun_of` 모두 None**(감사 3 결정 B, result.json·경로 1 rows에서 확인) |
| `7a469f7` | 2026-11-11 22:51:05, 문서 2줄(CLAUDE.md env 표·paper-reviewer 호출, `-I -B`). 첫 postrun 뒤, Chrono 새 prelaunch 전 |
| rev4 봉인 커밋 | `8ea3aa1`(23:18:29) = Chrono 실행 HEAD |
| Chrono r2 | prelaunch_r2 23:28:09(HEAD `8ea3aa1`, 추적 dirty 0, 감사 파일 `p5k_prelaunch_audit3.md`), 배치 `07_results/S9/batch_V5-LAS-P5R4-K1_20261111_232832` 23:28:32 ~ **2026-11-12 04:47:46**, 12/12 END `rc=0`, `failed=False`, P 4행 병렬(E 0), `OMP_WAIT_POLICY=PASSIVE`, `hull_hook=fast`. 러너 `run_chrono_r2.done` = `done exit=0`. env 기록 `env_main_chrono_r2_before.txt` = "none"(감사 4 기록 4 반영) |
| postrun_r2 | 2026-11-12 08:35:35, `status pass`, HEAD `8ea3aa1`, dirty 0, 코드 diff 0, 감사 파일 sha 같음 |
| RV4-7 2 수동 확인 | 초안 작성 때(2026-11-12 09:26 전) `git rev-parse HEAD` = `8ea3aa1a…`, `git log 8ea3aa1..HEAD` 비어 있음, 추적 dirty 0줄. postrun_r2(08:35:35)와 judge(08:36:22)도 그 전이다. 그 뒤 09:26:21에 `1ad3e5d`(B1 규칙 문서 6개, 코드 경로 0)가 들어왔고, 확정본은 그 위에 커밋한다. K-1·RV4-7 2에는 영향이 없다(판정 후 감사 기록 3) |
| 실행 중 점검 공백 | 15분 점검 cron이 **02:24 ~ 08:35 사이 돌지 않았다**(세션 유휴, 메인 세션 전달). Chrono r2는 04:47에 끝났고 postrun은 08:35에 했다. 그 사이 실행 중 점검(RV4-7 1: `log_errors`, git status, HEAD)은 없었다. 사후 확인으로 progress.log `rc` 0 12건, HEAD·dirty 변화 없음(postrun_r2 `git_status.lines` 0, `head.ok`)을 봤다. 러너 기록 `run_chrono_r2_status.txt`에도 시작(23:28:32)·끝(04:47:46) HEAD가 모두 `8ea3aa1a099adc65e167bc81266959ddc601157e`로 적혀 있다(판정 후 감사 기록 8). 점검 공백 동안 추적 파일이 바뀌었다가 되돌려졌을 가능성은 postrun으로 배제할 수 없다(사실로 적음, 등급 영향 없음 — K-1은 실행 시작·끝 HEAD·dirty와 코드 diff만 정의함) |

### 2.2 rev3 재봉인

- 첫 봉인 `561d158`(12:45:20)의 rev3는 머리 줄이 초안 표기였다. 결과 0건일 때 `0827c8f`(12:51:36)로 다시 봉인했다. 초안·첫 봉인 sha **`5798dd32…`는 무효**이고, 두 경로 도구에 이 값을 쓰는 곳은 없다(감사 2 "rev3 재봉인 경위"). 경로 2는 `98bdabf`(12:51:52)에서 5798dd32로 맞췄다가 `0ec945b`(12:52:23)에서 31ba01df로 바꿨고, 경로 1은 `c157b5a`(12:53:02)다.

### 2.3 실행 전 감사 파일

| 파일(`06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/prelaunch/`, 추적 밖) | sha256(raw = LF) | 내용 | K-0 대상 |
|---|---|---|---|
| `p5k_prelaunch_audit.md` | `0bbb7d5cc9e915231fe4da55e42b0e070308bf2d08f54ab690f7749db045c6a2` | 감사 1(HEAD `4b36cf5`) + 메인 처리 + 감사 2(HEAD `18b1425`) + 메인 처리 | 하네스·첫 Chrono 배치(하네스 판정 도구는 감사 파일 sha를 보지 않음, 감사 3 기록 5) |
| `p5k_prelaunch_audit3.md` | `32cc102ad6089d3dc4cf1148b69ce2404a737fae5d39c0487892fd220cf432e0` | 감사 3(HEAD `7a469f7`) + 메인 처리 + 감사 4(HEAD `8ea3aa1`) + 메인 처리 | Chrono r2(prelaunch_r2·postrun_r2·judge 모두 `32cc102a…`) |

### 2.4 감사 1 기록 7~14 (판정서 옮김)

| # | 내용 |
|---|---|
| 7 | 봉인 뒤·결과 전 구현자 짧은 실행. cad-expert: 2026-11-11 01:34:50Z `s9_batch run V5-LAS-P5R4-K1-GS --only P5K_A4_…_P5r4`(10 s, E 풀), 출력은 키 이름뿐(`p3b.P3-3_leg_force` → `['criterion']`, departure 없음), 배치 폴더 01:47:20Z 삭제, 커밋 `ff07ac9` 메시지에 기록. python-expert: 01:46~01:58Z trial 3건(scratchpad, Z-0 ref `D1\|H-R-A\|rigid+J1@FR\|T\|diag-op\|K3\|VB\|e0.002`, Z-A cand `…#P5r4-LT-c1-j1`, Z-S 짝 `D1\|H-S-A\|G1+J1@FL\|T\|flat\|K1\|VB\|e0`), 출력은 비트 일치 참·거짓·키 이름·trial `stop: identity` 사유뿐. 모두 표본 안 키, 판정 값 출력 없음(rev3 RV3-0.3) |
| 8 | 경로 2 독립성: 경로 사이 코드·출력 이동 흔적 없음. 다만 경로 2 작성자가 `c2.py`(01:24~01:26, 01:50~01:51Z), `git show ff07ac9:run_S9.py` 4010~4160행, `las_p5r4_k1_chrono_rows.py` 375~454행(메인 세션 허락 "cad-expert 코드는 읽어도 됨"), 자기의 앞선 경로 2 `k1rem_twopath/recount_rem.py`를 읽었다. **원판 10.2 "프로젝트 모듈을 열지 않는다"와 다르다**(메인 세션 허락이 원문과 다름). handback에는 공개했고 봉인 문서에는 RV2-3 인용 하나뿐이다. 감사 2 기록 8: 그 뒤 회차(rev3 반영)에도 경로 1 코드·출력 Read 0건. rev3 작성자는 감사 1 원문(경로 1 코드 위치·비교 꼴 인용 포함)을 읽었고 RV3-0.2에 공개했다 |
| 9 | 경로 2 하네스는 묶음당 파일 하나만 읽고 `p5k_<묶음>_resume.jsonl`을 읽지 않는다. **이번 실행에서 resume은 쓰지 않았다**(모든 묶음 `errors_total` 0, attempt 2 줄 0) |
| 10 | gate_scan 경고 11건(감사 2 때 10건, 줄 이동) 직접 확인, 빈 집합 통과 없음. 경로 2 Chrono `k_ok = all(ok is not False)`는 None을 통과로 센다(경로 1은 stop) — 보수 쪽 차이. 이번 Chrono 판정에서 경로 2 K 항목 None은 0건(6.3절) |
| 11 | 실행 도구 자체 해석(확정 문장 없음): S-5 누적에 판정 불가 짝도 넣음(규칙보다 엄격), Z-X 순서 관문은 앞 묶음 줄 존재만 봄(S-4는 메인 세션 몫), `p5r4_config`는 LAS-b 꺼진 config·이미 P5r4인 config를 그대로 둠(K-5가 줄마다 잡음). 이번 실행에서 S-5·S-4는 발동하지 않았다(C-2형 위반 0) |
| 12 | 봉인 기록: `las_rev_targeted_rules_rev1.sha256`에 봉인 시각 없음, `las_k1_rules_adopt_rev1.md`(730dbb3d)는 0절 표 밖(규칙과 맞음), `las_p5r4_k1_rules_rev2_draft.md` 이름 겹침은 도구가 이름 상수로 고정해 영향 없음 |
| 13 | G-S 필드 점검이 경로 1 필드만 봄 → 감사 2에서 해결(`values.times.t_first_ready_s` 추가). 이번 실행 `ready_source_disagree` 0(Z-T·Z-S·Z-C) |
| 14 | `errors N`은 첫 시도 포함 → RV3-2(`errors_left` 0이면 진행). 이번 실행은 모든 묶음 `errors N` = 0이라 해당 없음 |

### 2.5 감사 2 기록

- **기록 3 / 확인 2(K-A2·K-A4·K-A5 정의 차이, 사용자 결정: 그대로 두고 갈리면 보수 쪽)**
  - K-A4 행 맞추기: 경로 1은 겹치는 구간 [max 첫 시각, min 끝 시각] 안의 행 목록 전체 일치, 경로 2는 두 쪽에 정확히 같은 시각이 있는 행만 비교.
  - K-A5: 경로 2는 원문 "`start_factor` = λ0"를 검사하지 않고 시작 판단이 `start_factor < 1 − 1e-9`, 경로 1은 마지막 작동 주기 `is_scaled`와 λ0 비교 허용 1e-4(규칙 문장에 없는 허용, 옛 도구에서 복사).
  - `las.end_t_s` None 줄: 경로 1은 K-A2·K-A4를 건너뛰고 경로 2는 `ok=False`.
  - **결과**: 두 경로 모두 G-4(K-A1~K-A8) 통과, 경로 2 K-A1~K-A4 각 54짝, K-A5·K-A8 102줄 실패 0, K-A6 대상 0. BT-A 102/102 참이라 차이가 드러날 자리가 없었다. 갈린 곳 0.
- **기록 4**: 6.1 기록 항목(원 G-2H, Q-1~Q-5, M-1~M-3)은 경로 2만 다시 계산했다. 경로 1은 `"Q_M_records": "not recomputed: BT-A true reproduces …"`이고 G-2는 `G-2_cells`만 낸다. K-10 대상이 아니다. 4.2절 기록 값의 출처는 경로 2다(BT-A 참이므로 A안 rev2 재현). 경로 2가 표 밖 비교(K-A5 λ0 < 1, 격자 선택 j ≤ 3/3.5)에도 1e-9 꼴을 쓴 것은 커밋 `98bdabf` 메시지에 공개돼 있다.
- **기록 5**: manifest의 "lf_sha256 … (= main checkout file, -text, LF)" 문장은 `-text`인 5개 파일에만 맞는다. 나머지 18개(`c2.py`, `run_S9.py` 등)는 작업 트리 `w/crlf`이고 raw = `crlf_sha256`이다. 값은 모두 맞다(기대값으로 쓰는 도구 없음).
- **기록 6**: `4b36cf5..18b1425` 코드 경로 변경은 `07b092b`의 `04_scripts/03_control/k2/loc_shadow/*` 6개 추가뿐이고 실행 경로에서 import 0건.

### 2.6 자리표시 (16.4, rev3 RV3-3 4, rev4 RV4-5)

| 파일 | 마지막 추적 커밋 `e9ca269` blob / blob 내용 sha256 | RUN_HEAD 채움(감사 2) | 첫 채움(첫 배치, 감사 3) | 재채움(r2 배치) | 판정 전(JUDGE_COMMIT·POSTRUN_HEAD 채움) |
|---|---|---|---|---|---|
| `commands.md` | `609378453c11…` / `0b8f0030664b3290779e535b8844fff228f3ef0c645b6cfedb7010c947f0b1c0` | `402634bb…` | `2a34ed60…` | `5dbbad6c…` | **`667ee729f2f3d55bed8ce006016c8aa1b7f6dabecb89b4fd317f36f5f3acff19`** |
| `commands_path2.md` | `3ac3b0440ac9…` / `ea4faef6b415…` | 같음 | `57f04a03…` | **`0fef348db4ab41c101e4431da8bb4471d422df3e2b2222c51e10ee1e13be50cc`** | 같음 |
| `manifest.json` | `cff7dc59f966…` / `b190ef83c3b2c6c9b91b48fe720f9a14bc08ee14302ae211a1ae60f9a25c2984` | `3dd77112…` | `99702564…` | **`3159b97459c5d76e77da6293bef1ff3591bd06bba739daffe5dceae21ebd2f40`** | 같음 |

- sha 규약: 모두 main checkout 파일 raw 바이트(= LF, `-text`). manifest `path2_commands`는 채우기 전 값이다(감사 2 기록 10).
- 채운 값: RUN_HEAD `18b142511406ff71cfa92f0eaaa8c04a6036937b`, BATCH_GS `07_results/S9/batch_V5-LAS-P5R4-K1-GS_20261111_131719`, BATCH_CHRONO `07_results/S9/batch_V5-LAS-P5R4-K1_20261111_232832`(재채움, 폴더 이름 끝부분만 4/2/1곳), JUDGE_COMMIT `8ea3aa1a099adc65e167bc81266959ddc601157e`(`commands.md:119`), POSTRUN_HEAD `8ea3aa1a…`(`commands.md:157`).
- 판정 전 점검(이 판정서 작성 때 재실행): `placeholder_scan.py --repo C:\workspace\outrigger_control "…/prelaunch/*.json" "…/prelaunch/*.md"` → 미채움 20건 = 고정 제외 20곳과 정확히 같음(`commands.md:6` 6건, `commands_path2.md:20` 1건, `manifest.json:283,289,295,301,307` 5건, `p5k_prelaunch_audit.md:39,40,42(5),43` 8건). 실제 자리 남은 것 0. S-10 통과. 출력: `06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/judge_gates/placeholder_scan_prelaunch.json`(로컬 전용 폴더).
- **S-10을 읽은 방식(판정 후 감사 기록 2·확인 1, 사용자 결정 2026-11-12: 공개만)**: 원판은 S-6(하네스 `통과` 뒤 Chrono)과 16.4(BATCH_CHRONO는 Chrono 시작 직후, JUDGE_COMMIT 자리 하나)를 함께 두었다. 그래서 하네스 판정(16:22, `18b1425`) 때는 JUDGE_COMMIT·POSTRUN_HEAD·BATCH_CHRONO가 아직 채울 수 없는 자리였고, S-10 "미채움 0"을 하네스 판정 시점에 지킬 방법이 없었다(규칙 안의 모순). **이번에는 S-10을 "최종 판정 전 한 번"으로 읽었다**(위 판정 전 점검). 자리표시는 판정 입력이 아니고 하네스 판정 도구 출력은 결정론(같은 도구 sha `d07888ba…`, 같은 입력)이라 하네스 판정 값은 달라지지 않는다. 하네스 판정을 다시 돌리지 않았다. **다음 규칙은 단계별 자리(하네스 판정 커밋·Chrono 판정 커밋을 따로)와 단계별 관문을 둔다.**

### 2.7 이 판정서 작성자가 이번에 읽은 것 — 원판 10.2 문언과 다름(두 출력 확정 뒤)

- **원판 10.2는 "경로 2 작성자(control-expert)는 경로 1 코드·출력을 열지 않는다"이고 시점 제한이 없다. 이 판정서 작성자는 경로 2 작성자이고, K-10 비교를 위해 경로 1 출력 2개(`judge_p5k_harness.json`, `judge_p5k_chrono.json`)를 읽고 경로 1 도구 두 개를 `touch_creep`로 grep했다.** 두 경로 출력이 모두 확정된 뒤(하네스 16:22, Chrono 08:36)였다. 경로 2 파일은 바뀌지 않았다: `p5k_recount.py` blob `1b85aacc` = HEAD = 작업 트리(sha `5c827f2f…`), `p5k_chrono_recount.py` blob `8888336e` = HEAD = 작업 트리(sha `e3cb1c4a…`), 마지막 변경 `0ec945b`(11-11 12:52). 판정 후 감사도 오염 흔적이 없다고 봤다(기록 7). 감사 1 기록 8(2.4절)과 같은 꼴의 문언 차이로 공개한다.
- 두 경로 판정 출력 4개(K-10 비교), 규칙 5판, 감사 파일 두 개의 해당 절, prelaunch·postrun 기록(r2와 첫 배치 정체성 필드), r2 배치의 `result.json`·`step_series.npz`·`r8_series.npz`(원인 분석), 하네스 줄 파일의 `touch_creep` 필드(6.3절).
- 경로 1 코드는 K-10 차이 진단 때 `las_p5r4k1_judge.py`·`las_p5r4k1_chrono_judge.py`에서 `touch_creep` grep 결과만 봤다(두 경로 출력이 확정된 뒤). `c2.py` 7950~8060행(LAS-b 램프 시작 조건)을 원인 분석에 읽었다.
- 첫 Chrono 배치의 결과 값(result.json·npz)은 읽지 않았다.

### 2.8 원판 1절 공개 원문 (원판 13절 "이 규칙 1절 공개 원문")

아래는 `las_p5r4_k1_rules.md`(`5ee2bac0…`) 60~92행(1절 전체)을 그대로 옮긴 것이다.

> ## 1. 봉인 전에 본 것 (공개)
>
> ### 1.1 이미 본 P5r4 결과 (과적합 공개)
>
> | 자료 | 본 범위 | 이 규칙에서의 지위 |
> |---|---|---|
> | A안 rev2 판정서 `las_revA2_judgement.md`(R-0A 54, R-Q 48, R-T 192, R-S 30, R-P0 149, R-X 4) | 판정 값 전부 | Z-A·Z-T·Z-S는 **같은 키의 재실행**이다. 기구 확인·재현일 뿐 일반화 근거가 아니다 |
> | K1 판정서 `las_k1_judgement.md`(Y-Sb P5r4/K1on 30, Y-T P5r4/K1on 192) | 판정 값 전부(경계 키 Y-Sb − Y-Sa −0.116 mm 등) | 같음 |
> | 진단 `las_revA_diag_judgement.md`(경계 키 P0·P5·P5r4 3줄), 분석서 `las_revA_RGH_analysis.md` | 전부 | 같음 |
> | K1 전환 G-3 재생(457줄, 새 프리셋에서 Y-Pa·Y-Pb·Y-Sa·Y-Sb·Y-T 해시 같음), 전환 후 감사 `las_k1_switch_post_audit.md` | 건수·해시 일치 | Z-S·Z-T 해시 예측의 근거 |
> | Chrono: S-Ch 판정서, REM 판정서 `las_k1_rem_judgement.md`(R1~R8·F1·F2) | 판정 값 전부 | C-C 기준 줄의 비트 예측 근거. **P5r4 Chrono 결과는 없다(0행)** |
>
> - **표본 밖 근거**는 다음뿐이다.
>   - 하네스 Z-C의 S-C 456 전체 키 중 R-S와 겹치지 않는 **437키**(P5r4로 돈 적 없음)
>   - Chrono 12행 전부(P5r4 Chrono 0행, 혼합 지형 행 0행, G1+J1@FL Chrono 0행)
> - S-C P0 값: control-expert가 K1 원판 작성 때(2026-11-09) S-C P0 456줄의 $t_P$·$t_S$·LOC·R4·최대 행정을 봤다(K1 원판 0.2). 이 규칙(초안·봉인 후보판)을 쓰는 동안에는 값을 읽지 않았다(1.2).
>
> ### 1.2 이 규칙을 쓰려고 읽은 것 (초안·봉인 후보판)
>
> - 문서: 위 표의 규칙·판정서 전부, 명세 436절(436.7·436.8), 전환 후 감사 원문(main checkout 미추적 파일 `las_k1_switch_post_audit.md`), `session_handoff.md`, decision_log 640~703행.
> - 코드(읽기만): `run_S9.py` 1505~1575행(`CONTROLLER_EXPECTATIONS`, `_LAS_EXPECTATIONS`의 β 3.5 고정), `c2.py` `_liftoff_approach_slow_meta`(7948~7975), `LiftoffApproachSlowSettings` 필드(2121~2143), `las_chrono_rows.py`·`las_k1_chrono_rows.py`·`las_k1_rem_chrono_rows.py` 머리말·상수, `s9_batch.py` 369~378행.
> - 저장 결과(값을 읽지 않은 스크립트, control-expert scratchpad `p5r4k1\`, `conda run -n dynamics-dev python -I -B`)
>   - `scan_keys.py`: 하네스 jsonl 10개의 파일 sha256, 줄 수, `d1.key` 계열 건수, `las.candidate`/`controller_tag` 건수, `wall_s` 합·최대, 최상위 필드 이름.
>   - `key_lists.py`: `rev.key` 목록과 목록 sha256(부록 A), S-C ∩ R-S = 19키.
>   - `chrono_fields.py`: REM R1 `result.json`의 필드 이름만(`controller_meta.liftoff_approach_slow` 키, `p3b` 하위 키, `c2_setup` 키).
>   - PowerShell `Get-FileHash`: REM R1·R4·R7·R8 `controller_commands.npz` sha256(4.4 BT-C 기준값).
>   - (봉인 후보판 때 추가) `yp_blank.py`: `k1_YP.jsonl`에서 후보 필드가 없는 줄의 줄 번호·최상위 키·`rev.key`·`error`만 출력. `Select-String`으로 같은 키의 줄 번호만 찾음(부록 A).
>   - (봉인 후보판 때 추가) 재감사 `las_k1_adopt_rev1_d8x_rev3_audit.md` F-5~F-7, `las_rev_targeted.py` 30~36행 docstring.
> - 판정 값(힘·행정·READY·사건)은 이번에 저장 파일에서 새로 읽지 않았다. 판정서에 이미 적힌 값만 인용했다.
> - (봉인 전 정리 때 추가, 2026-11-11)
>   - 문서: K-2 판정 후 감사 `k2/judgement/k2_post_audit.md` 1~118행, 판정서 `k2/judgement/k2_judgement.md` 231~307행(7절·부록 A), `tools/verif` README의 `log_errors`·`placeholder_scan` 절.
>   - 코드(읽기만, 16.1·16.5 근거): `run_S9.py` 95~108행(env 기본값)·2905~2923행(`--rigid-base`·`--crawler-kn-scale`·`--soil-patch` 거부), `hull_hook.py` 36~57행, `fb_targeted.py` 115~123행·1276~1470행 요약 출력, `run_v5.py` 295~308행·`maxtasksperchild`, `las_phase_diag.py` 770~810행(`install`), `c2.py` 2865~2900행(`with_10hz_d1`)·7946~8060행 메서드 이름, `v5_options.py` 태그 상수, 저장소 전체 grep(`light_leg_fraction_of_F_min`, `end_ramp_periods`, `flat_soil_margin_order_gate`, `os.environ`).
>   - 저장 결과: 부록 A 재계산(식별 필드 `rev.key`·`las.key`·후보 이름·`k1.sub_bundle`·`error` 유무만). 판정 값은 읽지 않았다.

### 2.9 K1 원판 8절 체크리스트 중 이 판정에 해당하는 항목 (`las_k1_rules.md` 8절 #1·#3·#4·#6·#7·#9)

| # | 항목 | 값 |
|---|---|---|
| 1 | 봉인 시각과 봉인 커밋 시각 | 머리 규칙 표(원판 `d6c65b5` 09:29:34, rev1 `9bcbcaa` 10:40:20, rev2 `1b03bbb` 11:04:55, rev3 `0827c8f` 12:51:36, rev4 `8ea3aa1` 23:18:29). 모두 대상 결과보다 앞섬 |
| 3 | 스레드 | 하네스: 1,468줄 모두 `MKL_NUM_THREADS`·`OMP_NUM_THREADS`·`OPENBLAS_NUM_THREADS`·`NUMBA_NUM_THREADS` = `1`, `MKL_THREADING_LAYER` = `TBB`. Chrono: 12행 모두 `args.threads` = `meta.num_threads_chrono` = 4(`run_S9.SCM_THREADS_FIXED`) |
| 3 | `las_candidate` 집계(줄·행 수) | Z-0 P0 6, Z-A P5r4 102, Z-T P0 192 / P5r4 192, Z-S P0 30 / P5r4 30, Z-C P0 456 / P5r4 456, Z-X P0 4. Chrono P0 6행(A1·A3·A5·B1·C1·C3) / P5r4 6행(A2·A4·A6·B2·C2·C4) |
| 4 | `--keys`·`--limit` | 쓰지 않음(하네스 단계 로그 6개·`prelaunch/commands.md`에 두 인자 0건, 묶음 줄 수 = 목록 수). 목록 sha 재계산(경로 2 K-9, 모두 부록 A와 같음): Z-0 `4d1591ba…`, Z-A 키 `14f89f1f…`(격자 이름 목록 sha 경로 1 R-0A `e58a2842…`·R-Q `21c1129a…`, 경로 2 `5b658a7c…`), Z-T `4160bddf…`(= Z-T ref 기준 `las.key` 목록), Z-S `19c78b49…`, Z-C `fe6c9c46…`, Z-C 중 R4 평가(Y-Pa) `dc1e65d4…`, Z-C 표본 밖 437키 `f20bb9e0…`. 기준 파일 sha 13개도 부록 A와 같음 |
| 6 | 짝 없는 키·목록 밖 줄·중복 줄(0이어도 적음) | 경로 1 completeness: 모든 묶음·팔에서 missing 0, duplicates 0, out_of_list 0, reruns 0. 짝 없는 키(unpaired): Z-T 0, Z-S 0, Z-C 0. 판정 후 감사 재집계도 짝 없는 키 0 |
| 7 | would_block·Q-0b | 해당 없음. 이 규칙은 K1 관문 차단(would_block)을 판정 기준으로 쓰지 않고, decision 기록 일관성은 K-8(adopt2 K-8 (a)~(e))로 대체했다. K-8 두 경로 모두 참. Q-0b(K1 원판의 사전 예측 대조)는 이 규칙에 대응 항목이 없다 |
| 9 | 해당 없음(None) 건수 | Chrono A1~A6 6행(3짝 × 두 팔) `P3-5_within` = None(`reason: no rut clearance row after the first READY`, 강체 바닥이라 틈 기록 없음). 두 팔 같음. ref가 참이 아니므로 CC-2 (a) 위반이 아니고, 키는 있으므로 `undecidable`도 아니다. 그 밖 판정 항목 None 0 |

## 3. 실행 정체성·관문

| 항목 | 결과 |
|---|---|
| K-0 | 규칙 sha = `.sha256`(5판). 판정 도구 sha: 하네스 `d07888ba…`, Chrono `0b357e38…` = 감사 2 고정값 = prelaunch(_r2) = postrun(_r2) = judge. 경로 2 `p5k_recount.py` `5c827f2f…`(blob `1b85aacc`), `p5k_chrono_recount.py` sha256 `e3cb1c4addd1d7732fd847e57a246b1f141ad3dc7a0c74c1120cdcde9429f080`(blob `8888336e`, prelaunch_r2 `path2_sha256`, prelaunch 명령이 확인하는 값). 감사 파일 sha(Chrono) `32cc102a…` 세 시점 같음 |
| K-1 | 하네스: 묶음·팔마다 identity 1개(`git_head` `18b1425`), `code_diff_sha256` 빈 해시. Chrono: 12행 `git_at_start.head` = `8ea3aa1`, 코드 diff 0, dirty 0 |
| K-2~K-9 | 두 경로 모두 참(경로 1 `identity[*].ok`, 경로 2 `k_checks`/`k_items` False 0). 경로 2 하네스 K-4의 `touch_creep_latch_off` 하위 항목은 None(6.3절) |
| BT-0·BT-A·BT-T·BT-S·BT-CR·BT-X | 6/6, 102/102, ref 192/192·cand 192/192, 30/30·30/30, 456/456, 4/4 |
| BT-C | C1 = REM R7(내용 해시 `1aa23d35…`, 1,200행), C3 앞 120 s(n ≤ 1280) = REM R8(`5ea9a64a…`, 1,200행) |
| G-S(16.2) | 하네스 117줄(목록 sha `41157880063e171fb35b1fb664d22b59923325b4602da0a92edda8e107851dc3`), Chrono 12행(`9d3a5f200daa6559e0e5abbbe1b421df9d1972be987428bc32f27391b7083602`, `--duration 10`), 통과(감사 2·prelaunch). G-S 줄과 본 실행 줄 `commands_sha256` 같음 116/116(비교 가능 116줄, 경로 1 `gs_equality`). rev4 RV4-3 6: Chrono r2는 G-S를 다시 하지 않음(코드 diff 0) |
| 표본 밖 G-S 키(23) | `D1\|H-R-A-J2\|rigid+J2@FL\|T\|flat\|K1\|{V0 e0, V0 e0.002, VB e0.002}`, `D1\|H-R-A-S1\|rigid+S1@FL\|T\|flat\|K1\|{V0 e0, V0 e0.002, VB e0.002}`, `D1\|H-S-0\|G1\|B\|diag-rec\|K1\|{V0, VB}\|e0.002`, `D1\|H-S-1\|S1\|B\|flat\|K1\|{V0 e0, V0 e0.002, VB e0.002}`, `D1\|H-S-A-J2\|G1+J2@FL\|T\|flat\|K1\|{V0 e0, V0 e0.002, VB e0.002}`, `D1\|H-S-A\|G1+J1@FL\|B\|fdown-psa\|K1\|{V0 e0, V0 e0.002, VB e0.002}`, `D1\|H-S-C-g\|J1\|B\|diag-rec\|K1\|c-mid@FR\|dsb_gated_off\|{V0 e0, V0 e0.002, VB e0.002}`, `D1\|H-S-C\|J1\|B\|flat\|K1\|c-edge@FL\|{V0 e0, V0 e0.002, VB e0.002}`(`prelaunch/gs_list.json` `out_of_sample_units`) |
| 단계 로그(16.3) | 하네스 `log_errors.py <p5r4k1 폴더> --require-line`: 단계 로그 12개(run_Z-* 6, gs/run_GS_Z-* 6) 모두 `errors 0`. `no_errors_line` 경고 2건은 Chrono 러너 로그 `run_chrono_main.log`·`run_chrono_r2_main.log`(배치 경로 한 줄뿐, Chrono는 progress.log `rc` 규칙)이다. Chrono r2 progress.log `rc`: 발견 0. 첫 배치 progress.log: 발견 0. 출력(판정서 작성 때, 로컬 전용 폴더 `06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/judge_gates/`): `log_errors_harness.json`(sha256 앞 16자 `109f12b9e179d2bc`), `log_errors_chrono_r2.json`(`f99bed170eb94a12`), `log_errors_chrono_first.json`(`dc36b80a60afc87c`) |
| errors_total / errors_left | 모든 하네스 묶음 0 / 0(두 경로). RV3-2 첫 시도 오류 기록 대상 없음 |
| 16.1 | 감사 1(E-9)·감사 2 기록 6 그대로(실행 경로 코드 diff 0) |
| 16.6 층별 | 기준: Chrono G-2′C·CC-S·CC-R `미달`, 그 밖 `통과`. 묶음: 하네스 6묶음 `통과`, Chrono `미달`. 최종: `미달` |

## 4. 하네스 (`통과`, 두 경로 일치)

### 4.1 Z-A (가)′ — cand 102줄

| 기준 | 결과 |
|---|---|
| G-1 / G-1H / G-1Q | 30 / 24 / 48줄 모두 ≥ 10.400 kN |
| G-2′ | 102줄 모두 ≥ 11.414589 kN. 최소 min(`F_RL_kN`, `F_judged_min_kN`) = **12.452 kN**(여유 +1.04 kN) |
| G-3, G-4(K-A1~K-A8) | 통과(경로 2: K-A1~A4 각 54, K-A5·K-A8 102, K-A6 0) |
| T-15 띠(10.400 ≤ v < 10.414589 kN) | 0건(두 경로) |
| 기록(경로 2만) | M-1 참(중앙 ΔF +3.32 kN), M-2 거짓(max R_c 2.871 kN), M-3 참, Q-1~Q-5 참. 원 G-2 ≤ 0.5 kN: VB c1·c0.94만 참 |

### 4.2 Z-T·Z-S·Z-C 짝

| 묶음 | 짝 | cand LAS 시작 | ref LAS 시작 | 해시 바뀜(PAIR_CMD_DIFF) | PAIR_DIVERGE | C-2형·P3·C-F·C-S·CK-1·C-1·A-3 위반 | $\Delta s$ 범위 [mm] | READY $\mathcal{P}$ / 중앙 / 최대 [s] | FLAG |
|---|---|---|---|---|---|---|---|---|---|
| Z-T | 192 | 144 | 62 | 144 | 0 | 0 | −0.073 ~ +0.202 | 144 / +0.2 / +2.3 | 0 |
| Z-S | 30(D-1 20 + verdict 10) | 5 | 3 | 5 | 0 | 0 | −0.116 ~ +0.316 | 4 / +0.15 / +0.8(기록, 바뀐 짝 1개 `D1\|H-R-A-stop\|rigid+J1@RL\|T\|fup-op\|K1\|VB\|e0`는 READY 없음) | THIN_MARGIN 2 |
| Z-C | 456 | 58 | 43 | 56 | 0 | 0 | −0.150 ~ +0.345 | 56 / +0.2 / +0.8 | THIN_MARGIN 12 |

- CK-1: Z-T `NONE` 192, Z-S `KEPT` 9·`NONE` 21, Z-C `KEPT` 160·`NONE` 296. **`R4_LOST` 0, `R4_GAINED` 0.** REM F2 한계는 하네스 판정 짝에서 관측되지 않았다.
- C-4 예외: Z-T 후보 4짝 모두 `E < 0.8 Δt`로 예외 아님, $\mathcal{P}$에 남음. Z-X 4줄(대상 4키 ≤ 10) BT-X 4/4.
- Z-C 표본 안(R-S 겹침 19키) / 표본 밖(437키): 바뀐 짝 4 / 52, LAS 시작 4 / 54, C-2형·C-S·P3·C-F·CK-1 위반 0 / 0.
- Z-C에서 cand LAS가 시작했는데 해시가 같은 짝 2개(`D1|H-R-A-S1|rigid+S1@FL|T|flat|K1|V0|e0`, `…|e0.002`). 전제(시작 안 함)가 거짓이므로 PAIR_DIVERGE 대상이 아니다. 사전 예측 P-3("PAIR_CMD_DIFF = 시작 줄 수")은 틀렸다(2 차이, 7절).
- ANCHOR_SAMPLE_SHIFT 0, anchor_effect_possible/unknown 0, ANCHOR_RECORD_MISSING 0(세 묶음).
- C-F 범위 밖(ref < 10,414.589 N): Z-S 1짝, Z-C 3짝(ref = cand 5.745 kN의 짝 포함). 위반 아님(범위 조건).

## 5. Chrono r2 (`미달`, 두 경로 일치)

### 5.1 짝 표

| 짝 | 조건 | cand LAS-b(시작~끝, 작동/축척 주기, 램프) | $F^{C}_{after}$ ref → cand [kN](다리, 이탈 뒤 시각) | CC-F | G-2′C | $s_{max}$ ref → cand [mm](다리) | $\Delta t$ READY [s] | PAIR_CMD_DIFF(첫 차이 주기, 경로 1) | CK-1C |
|---|---|---|---|---|---|---|---|---|---|
| A1/A2 | 혼합 강체+J1@FR, Kc1, VB | 34.7~35.5 s(8/—), 램프 4주기 λ0 0.336 | 10.814(RL +0.71 s) → **14.417**(RL +0.22 s) | 범위 안, 통과 | 통과 | 658.007 → 658.711(FR), Δ +0.704 | +1.2 | 참(348) | NONE |
| A3/A4 | 같음, **Kc3** | 34.2~35.1 s(9/—), 램프 4주기 λ0 0.336 | **8.637**(RL +0.71 s) → **11.356**(RL +0.28 s) | ref 범위 밖 | **위반 −58.4 N** | 657.897 → 658.122(FR), Δ +0.224 | 0.0 | 참(352) | NONE |
| A5/A6 | 같음, Kc1, **V0** | 33.3~34.2 s(9/—), 램프 4주기 λ0 0.336 | **8.509**(RL +0.49 s) → **14.794**(RL +0.23 s) | ref 범위 밖 | 통과 | 658.806 → 659.004(FR), Δ +0.197 | 0.0 | 참(343) | NONE |
| B1/B2 | G1 + J1 패치@FL, 평지, VB | 34.5~34.9 s(4/3), **램프 미적용**(`start_factor` None) | 38.369(RR) → 35.285(RR) | 통과 | — | **438.603 → 441.430(FL), Δ +2.827** | **+7.7**(66.8 → 74.5) | 참(346) | NONE |
| C1/C2 | J2 균일 평지 ×1.0 | **시작 안 함** | 67.250 → 67.250 | 통과 | — | 533.219 → 533.219, Δ 0 | 0.0 | 거짓(해시 같음) | KEPT(dP +99) |
| C3/C4 | J2 ×1.1, 180 s | **시작 안 함** | 73.608 → 73.608 | 통과 | — | 615.378 → 615.378, Δ 0 | 0.0 | 거짓(해시 같음) | KEPT(dP +198) |

- ref LAS-b(b0): A1 34.8~35.5, A3 34.2~35.1, A5 33.3~34.2, B1 34.7~35.1 시작. C1·C3 시작 안 함.
- CC-2: 위반 0(두 경로). 판정 항목 $I$ 중 ref가 참이 아닌 항목: A3·A5 `P3-3_within` 거짓(ref $F^{C}_{after}$ < $F_{min}$), C3 `P3-2_within`·`P3-6_within`·`P3-7_within` 거짓, **A 6행(A1~A6, 두 팔) `P3-5_within` None**(강체 바닥, 첫 READY 뒤 틈 기록 없음, 두 팔 같음; 키가 있으므로 `undecidable` 아님, ref 참이 아니므로 위반 아님). cand에서 A4·A6 `P3-3_within`은 참이 됐다(개선). C4는 C3와 같음.
- `LATE_LOC_P32` FLAG 0(C3/C4는 ref도 `P3-2_within` 거짓이라 예외 문장 대상 아님; 두 행 모두 `P3-2_late_loc_revoked` 참, LOC 취소 1회).
- 관측 요건(6.3): A 3짝 모두 cand LAS 시작 + 램프 4주기 작용 → 충족(`NO_P5R4_OBSERVATION` 아님).
- **P5r4 미작동 짝(`p5r4_not_acting`)**: C1/C2, C3/C4. cand LAS-b가 시작하지 않아 명령 해시가 같다. 판정은 했으나(위반 없음) **"P5r4 미작동, P5r4 근거 아님"**이다. B1/B2는 LAS-b는 시작했지만(β 4.5로 0.2 s 일찍) **끝 램프는 작용하지 않았다**(8.3절).
- CK-1C: C 짝 `KEPT`(두 팔 같은 decision, $L_1$ applied). **`R4_LOST` 0 → REM F2 한계는 판정 행 C1~C4에서 관측되지 않았다**(C 짝은 P5r4 미작동이라 원래 예측 대상과 같은 궤적).
- FLAG: R4_GAINED 0, THIN_MARGIN 0, ANCHOR_SAMPLE_SHIFT 0(6짝 모두 두 팔 경로 ③), `P3-4_window_short` 0.
- RV1-3: CC-S 위반 짝 B1/B2는 `ANCHOR_SAMPLE_SHIFT` 거짓(두 팔 경로 ③, 보정 미적용)이다. `anchor_effect_possible`·`anchor_effect_unknown` 0. **앵커 표본 효과는 해당하지 않는다.**
- RV1-4(C-S 1 mm 허용의 양자화 민감도): 판정서 문장으로 적는다. 경로 ①·②에서 보정 $b_k$는 $t_P$ 주기의 행정 평면 $c_k(t_P)$로 정해지고, LOC 꼬리 동안 행정 평면이 주기당 약 1~2 mm 움직이므로 $t_P$가 한 주기 바뀌면 $s_{max}$가 같은 크기로 바뀔 수 있다. **C-S 1 mm 허용은 앵커 시각 양자화에 민감하다.** 이번 B1/B2 위반은 경로 ③(앵커 미사용)이라 이 기구가 아니라, 8.3절의 다른 기구(정착 시간 차에 따른 연약 패치 크리프)에서 나왔다. 문턱·대상은 바꾸지 않는다.
- 하네스 같은 계열 대비(6.4 기록)
  - 원판 6.4 문구대로 `las_chrono_rows` 머리말 b0 11.377 kN 하나와 비교한 값(경로 2 `record_A`, K-10 일치): ref −0.563 / −2.740 / −2.868 kN, cand +3.040 / −0.021 / +3.417 kN(A1/A2, A3/A4, A5/A6 순).
  - **키별 비교로 정정**(11.377 kN은 K1·VB 키 값이다): 하네스 b0 K1 VB 11.377, **K3 VB 11.281**, **K1 V0 11.443** kN. ref 차 A1 −0.56, **A3 −2.64**, **A5 −2.93** kN, cand 차 A2 +3.04, A4 +0.08, A6 +3.35 kN. 결론(Chrono 골이 하네스 b0보다 0.6~2.9 kN 깊음)은 같다.

### 5.2 기준 표

| 기준 | 상태 | 내용 |
|---|---|---|
| CC-2 | 통과 | 위반 0 |
| CC-F | 통과 | 범위 안 4짝(A1/A2, B, C 두 짝), 위반 0. A3/A4·A5/A6은 ref < 10,414.589 N이라 범위 밖 |
| G-2′C | **미달** | A3/A4 위반(위 1절) |
| CC-S | **미달** | B1/B2 위반 |
| CK-1C | 통과 | B 짝 NONE, C 짝 KEPT |
| CC-R | **미달** | 바뀐 짝 4 = 모집단 4, 중앙 +0.6 s(통과), 최대 +7.7 s(B1/B2, 위반) |
| 관측 요건 | 충족 | A 3짝 |

## 6. K-10 두 경로 대조

### 6.1 방법

- 비교 스크립트: control-expert scratchpad `p5kj\k10_compare.py`(python-dev `-I -B`). 두 경로 출력 4개만 읽는다.
  - 경로 1: `06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/judge_p5k_harness.json`(sha256 `a0efbb7c5d1de5db…`, 16:22:32), `judge_p5k_chrono.json`(`f8f5da5ffd17f0e1…`, 2026-11-12 08:36:22)
  - 경로 2: `06_analysis/02_control/verif_matrix/p5k_judge/path2_harness.json`(`4a381ca926986d40…`, 16:22:42), `path2_chrono.json`(`56f9d3e6e31955c3…`, 2026-11-12 08:36:24)
- 비교 대상(10.2): 묶음·기준 상태, 비트 예측 결과(건수·불일치 목록), 짝별 위반 목록과 `items_only_*`, 기준별 개수·중앙·최대, `PAIR_DIVERGE`·`PAIR_CMD_DIFF` 목록, CK-1 분류, FLAG 목록(R4_GAINED·THIN_MARGIN·ANCHOR_SAMPLE_SHIFT·ANCHOR_RECORD_MISSING·LATE_LOC_P32·window_short·anchor_effect_*), Z-X 대상 키, Chrono 관측 요건·BT-C, 짝별 값(힘·행정·$\Delta s$·READY·$\Delta t$, $n_P$·$n_L$ 차, 앵커 경로)과 그 참·거짓. 수치 허용 1e-9, 상태·목록 정확 일치.
- 세운 비교 수: 수치 10,927, 참·거짓 6,803, 목록 1,404, 상태 2,075. **수치 최대 차 0.0**(비트 같음).

### 6.2 결과: **일치**

- 실질 불일치 0. 비교 스크립트가 낸 차이 2건은 표현 차이다.
  1. Z-X 비트: 경로 1 `bits.ref.expected` 659는 대조 기준 풀의 줄 수이고 `equal` 4다. 경로 2는 `n` 4 / `n_equal` 4. 둘 다 4줄 모두 같음.
  2. Z-S R-1/R-2: 원판 6.2 표에서 Z-S는 "기록"이다. 경로 1 `ready.R-1` 참, 경로 2 `status` None + `status_record_only` `pass`. 같은 뜻이다.
- Chrono CK-1: 경로 1은 `R4_LOST`·`R4_GAINED` 참·거짓과 $L_1$, 경로 2는 분류(`NONE`/`KEPT`)를 낸다. C 짝 두 팔 $L_1$ applied 참 = `KEPT`, 나머지 $L_1$ None = `NONE`으로 같다.
- 등급: 하네스 `통과`/`통과`, Chrono `미달`/`미달`, 실패 사유 목록 {G-2′C, CC-S, CC-R} 같음.

### 6.3 두 경로 정의가 다른 곳 (등급에 닿지 않음, 공개)

| # | 항목 | 경로 1 | 경로 2 | 이번 결과 |
|---|---|---|---|---|
| D-1 | K-A4 행 맞추기(감사 2 기록 3) | 겹치는 구간 안 행 목록 전체 | 같은 시각 행만 | 둘 다 통과(BT-A 참) |
| D-2 | K-A5(감사 2 기록 3) | `is_scaled` + λ0 허용 1e-4 | `start_factor < 1 − 1e-9`, λ0 조건 없음 | 둘 다 통과 |
| D-3 | K-A2·K-A4 `las.end_t_s` None | 건너뜀 | `ok=False` | 해당 줄 없음(실패 0) |
| D-4 | 6.1 기록 M·Q·G-2H | 다시 계산 안 함 | 계산 | K-10 대상 아님(감사 2 기록 4) |
| D-5 | **하네스 K-4 `touch_creep_latch` 꺼짐** | `p5k.touch_creep_latch_enabled`와 `effective.touch_creep_latch_enable`이 `False`가 아니면 문제(`las_p5r4k1_judge.py:1263-1267`) | dict 키 `touch_creep_latch`를 찾음 → 하네스 줄에는 그 이름의 dict가 없어 **1,468줄 모두 None("absent")**, None은 실패로 세지 않음 | 경로 2는 이 하위 항목을 **평가하지 못했다**(키 이름 불일치, 경로 2 결함). 판정서가 직접 확인: 하네스 1,468줄 모두 `p5k.touch_creep_latch_enabled` false, `effective.touch_creep_latch_enable` false, `p5k.touch_creep_meta.settings.enable` false(scratchpad `tcl_lines.py`). Chrono는 경로 2 K 항목 None 0건. K-4 참은 성립하고, 경로 2는 결과 뒤 고치지 않는다(10.2) |
| D-6 | 경로 2 Chrono `k_ok` None 처리(감사 1 기록 10) | None → stop | None → 통과 | 이번 Chrono None 0건 |

- **판정 후 감사 확인 2 결정(사용자, 2026-11-12)**: 원판 10.2의 K-10 비교 대상(비트 예측, 위반 목록, 기준 값, FLAG, 등급)에는 K 하위 항목이 없으므로 **이번 판정은 문언대로 K-10 `일치`를 유지한다.** 다음 규칙부터는 **K 항목 값 None을 stop으로** 두고 두 경로를 고친다(경로 2: `p5k_recount.py`의 K-4 TCL 출처를 `p5k.touch_creep_latch_enabled`·`effective.touch_creep_latch_enable`로 맞추고 None 통과 제거, `p5k_chrono_recount.py` `k_ok`도 같게). tools/verif 후보 `k_census`(두 경로 판정 json의 (K, item) × ok 값별 건수, None > 0이면 종료 1)를 python-expert에 올린다.

## 7. 사전 예측 대조 (판정 기준 아님)

| # | 예측 | 결과 | 맞음 |
|---|---|---|---|
| P-1 | Z-A·Z-T·Z-S 통과 | 통과 | 맞음 |
| P-2 | Z-C cand LAS 시작 40~140줄 | 58 | 맞음 |
| P-3 | Z-C PAIR_CMD_DIFF = P-2 수 | 시작 58, 해시 다름 56(시작했으나 해시 같음 2) | **틀림**(2 차이) |
| P-4 | Z-C C-S 위반 0 | 0(최대 +0.345 mm) | 맞음 |
| P-5 | Z-C `R4_LOST` 0 | 0 | 맞음 |
| P-6 | Z-C C-2형·P3·C-F 위반 0 | 0 | 맞음 |
| P-7 | Z-C R 중앙 ≤ +0.5, 최대 ≤ +3 s | +0.2 / +0.8 | 맞음 |
| P-8 | A cand 시작·램프, $F^{C}_{after}$ 12.0~15.0 kN, G-2′C 통과, A6 최저 | 시작·램프 맞음. 14.42 / **11.36** / 14.79. A4 최저(A6 아님). G-2′C 미달 | **틀림**(A4) |
| P-9 | A ref 10.5~12.0 kN | 10.81 / **8.64** / **8.51** | **틀림**(A3·A5, 하네스보다 2.7~2.9 kN 낮음) |
| P-10 | B: R4c30 없음, $\lvert\Delta s\rvert$ ≤ 1 mm, C-S 통과 | R4c30 없음은 맞음. Δs +2.83 mm | **틀림** |
| P-11 | C: POS·$L_1$ 적용, CK-1C 통과 | 맞음(cand LAS 미작동이라 궤적 동일) | 맞음 |
| P-12 | C C-S $\lvert\Delta s\rvert$ ≤ 1 mm | 0 | 맞음 |
| P-13 | BT-C | 참 | 맞음 |
| P-14 | 전체 통과(가장 큰 위험 P-12, 다음 P-10) | Chrono 미달(P-10의 B + 예측 밖 A4 G-2′C·B CC-R) | **틀림** |

## 8. 미달 원인 분석

이 절의 원인 해석은 기록 값으로 확인한 사실과 추정을 나눠 적는다. 등급은 1절 그대로다.

### 8.1 P5r4가 실제로 작동했는가

| 짝 | β 4.5(시작) | 끝 램프 $N_r$ 4 | 판단 |
|---|---|---|---|
| A1/A2 | 시작 0.1 s 빠름(34.7 vs 34.8 s) | 4주기 작용(λ0 0.336 → 1) | 작동 |
| A3/A4, A5/A6 | 시작 같음(ref·cand 같은 주기) | 4주기 작용 | 램프만으로 차이(첫 명령 차이 주기 352·343 = LAS 끝 다음 주기) |
| B1/B2 | 시작 0.2 s 빠름(34.5 vs 34.7 s) | **작용 안 함** | β만 작동 |
| C1/C2, C3/C4 | 시작 안 함(두 팔 모두) | — | **미작동**(`p5r4_not_acting`) |

- B2에서 램프가 시작하지 않은 이유(코드로 확인, `c2.py` `_should_start_liftoff_ramp` 7994~8002행): 램프는 `sum`/`time` 끝이면서 **마지막 작동 주기가 축척된 경우**(`last_scale_factor < 1`)에만 시작한다(A안 1.3). B2는 LAS-b 작동 4주기 중 축척 3주기였고, 34.8 s에 P-S8-30 느린 들어 올림(`INFO_LIFT_PAUSED:RR`, 평균 0.16 $v_{max}$)이 먼저 걸려 마지막 주기 평균 속도가 이미 LAS-b 목표(0.16 $v_{max}$) 이하였다. 그래서 축척 1 → 램프 시작 조건 거짓이다. ref B1에는 `INFO_LIFT_PAUSED`가 없다.

### 8.2 G-2′C (A3/A4) — 램프는 바닥을 올렸지만 Kc3에서 여유선에 58 N 모자람

사실(1 ms 참 $F_{cyl}$, RL, 이탈 + 8 s 창):

| 행 | 팔 | 이탈 $t_d$ [s] | RL 최소 [kN] | 최소 시각 | $F < F_{min}$ 시간 | $F < F_{min}$ + 2 kN 시간 |
|---|---|---|---|---|---|---|
| A1 | P0, Kc1, VB | 35.229 | 10.814 | $t_d$ + 0.71 s | 0 ms | 131 ms |
| A2 | P5r4 | 35.415 | 14.417 | + 0.22 s | 0 | 0 |
| A3 | P0, **Kc3** | 34.868 | **8.637** | + 0.71 s | **195 ms** | 362 ms |
| A4 | P5r4, Kc3 | 34.868 | 11.356 | + 0.28 s | 0 | **27 ms** |
| A5 | P0, Kc1, **V0** | 34.007 | **8.509** | + 0.49 s | **67 ms** | 161 ms |
| A6 | P5r4, V0 | 34.007 | 14.794 | + 0.23 s | 0 | 0 |

- 최소 다리는 모두 RL(J1 패치 FR의 대각 반대). 이탈 뒤 0.2~0.7 s의 골이다. 같은 다리의 늦은 구간 최소(`F_min_late_N`)는 약 40 kN이다. (초안은 이 골을 "이륙 과도"라 불렀으나, D-2 진단에서 준정적 비틀림이 주성분으로 판단됐다. 아래 "D-2 진단 요약".)
- P5r4는 세 A 짝 모두에서 골을 올렸다: +3.60 / +2.72 / +6.29 kN. 골 시각은 이탈 + 0.5~0.7 s에서 + 0.22~0.28 s로 앞당겨졌다.
- 크롤러 강성 ×3(Kc3)은 골을 깊게 한다: P0 10.81 → 8.64 kN(−2.18), P5r4 14.42 → 11.36 kN(−3.06).
- A4는 $F_{min}$보다 1.94 kN 위다(`P3-3_within` 참). G-2′C 선($F_{min}$ + 2 kN)만 58 N(0.51 %), 27 ms 동안 밑돈다.
- **곁 발견(중요, 판정 밖)**: 채택 제어기 P0+K1이 Chrono A3(Kc3)·A5(V0)에서 **`P3-3_within` 거짓**이다(RL 8.64 / 8.51 kN < $F_{min}$, 195 / 67 ms). 혼합 지형 Chrono는 이번이 처음이다(원판 1.1 "혼합 지형 행 0행"). CC-2는 "ref 참 → cand 거짓"만 위반이므로 이 사실은 P5r4 판정에 닿지 않는다(오히려 cand가 개선).
- **A행 시작 조건(초안 정정)**: 바닥 공칭 경사 (2.3351°, 1.5017°)의 $R_c = \lvert\phi_g\rvert/4.4° + \lvert\theta_g\rvert/3.2°$ = 0.5307 + 0.4693 = 0.99999(경계 안)이다. 그러나 **실행이 계산한 SL-2 $R_c$**(CHECK 끝 크롤러 IMU 자세, result.json `p3b_ext.start_condition.R_c_operating`)는 A3/A4 **1.035**, A1/A2·A5/A6 **1.076**이고 `operating_rule_rejects: true`다. 즉 A행은 **운용 시작 조건 밖**이며 `start_limit record_only`라서 시작했다. B·C행은 0.027~0.047(`false`). 초안의 "경계"는 공칭 값만 본 표현이었다.

#### D-2 진단 요약 (판정 밖 기록, 2026-11-12)

- **dynamics-expert**: RL 하회의 주성분은 **준정적 4점 비틀림**이다. 크롤러 이탈 뒤 네 다리 오일 기둥의 비틀림 강성은 $1/C \approx 5.93\times10^{6}$ N/m이고, 명령 비틀림 1 mm가 RL 하중 약 −6.5 kN에 해당한다. 비틀림을 만든 것은 (1) LAS-b 끝 다음 한 주기에 원래 속도로 복귀하는 명령(RL $u$ = 0, 비틀림 방향 성분 $w\cdot u$ +5~7 mm/s)과 (2) FR 연약 패치 침하다. **동적 과도가 아니다.** 모델 상부체가 강체이므로(실기 구조 유연성이 비틀림 강성을 낮춤) 이 값은 보수 쪽이다. β에 민감하다.
- **control-expert**: P3-3 판정 창 정의(이탈 뒤 1 ms 참 $F_{cyl}$ 최소)는 맞게 잡혀 있다. 0.1 s 이동 평균으로 바꿔도 A3는 $F_{min}$ 아래다. 평균 창으로 통과시킨 선례도 없다. A행은 운용 시작 조건 밖(위 SL-2)이므로 **"알려진 한계로 기록"**이 맞다. 운용 범위 안 조건에서 같은 현상이 없는지 확인하는 실행(O-C5)을 제안한다.
- 이 진단으로 아래 해석 중 "과도" 해석을 정정했다.

제어 관점 해석(추정, 진단 반영):
- 하회는 LAS-b 끝 경계에서 명령이 한 주기에 원속도로 돌아갈 때 생기는 **비틀림 계단**이 오일 기둥 강성(약 6.5 kN/mm)을 통해 RL 하중으로 바로 옮겨진 것이다. P5r4의 끝 램프(4주기에 걸쳐 축척 λ0 → 1)는 정확히 이 계단을 나누어 주므로 골이 +2.7~+6.3 kN 올라간 것과 맞는다.
- Kc3에서 골이 더 깊은 것은 크롤러가 더 늦게까지 하중을 잡다가 이탈 순간 비틀림 몫이 다리로 더 많이 넘어오는 것으로 본다(추정).
- 따라서 A4의 미달은 **개념 문제가 아니라 크기(파라미터) 문제**로 본다(추정). 램프 길이·시작 축척을 키우거나 끝 복귀 명령의 비틀림 성분을 제한하면 골이 더 올라갈 여지가 있다. 다만 결과를 본 뒤 고른 값은 과적합이므로 새 원판(결과 뒤 판 공개)과 새 표본 밖 조건이 필요하다. 또 A행은 운용 시작 조건 밖이므로, 재설계 근거로 쓰기 전에 범위 안 조건(O-C5)을 먼저 본다.

### 8.3 CC-S·CC-R (B1/B2) — β의 이른 시작이 사건 사슬을 바꿔 정착이 7.7 s 늦어졌고, 그동안 J1 패치가 더 가라앉음

사실:

| 시각 [s] | B1(ref, P0) | B2(cand, P5r4) |
|---|---|---|
| 33.4 | LEVEL 시작 | 같음 |
| LAS-b | 34.7 시작(RR) ~ 35.1 끝(sum), 4주기 | 34.5 시작(RR) ~ 34.9 끝(sum), 4주기(축척 3) |
| `INFO_LIFT_PAUSED` | 없음 | 34.8(RR) |
| LOC | 35.6 | 35.8($t_P$ 34.7 → 34.8, $\Delta n_P$ +1, 두 팔 앵커 경로 ③) |
| DONE(`INFO_TWIST_UNSETTLED`) | 62.8(\|D\| 14.1 kN) | **70.5**(\|D\| 12.0 kN) |
| PROBE → READY | 62.9 → 74.8 | 70.6 → 82.5 |
| READY(루프 시작 기준) | 66.8 | 74.5(**+7.7 s**) |

- 1 ms 참 행정·침하 차(cand − ref): 35~60 s에는 cand 행정이 0.4~2.8 mm **작다**(이른 감속). 65 s 뒤부터 FL이 커져 90 s 이후 **FL 행정 +2.83 mm, FL 패드 침하 +2.75 mm**로 고정된다(다른 다리 ≤ 0.63 mm). FL 최대 행정 시각은 64.6 s(ref) / 72.3 s(cand)이고 둘 다 DONE 직후 탐침 구간이다. 탐침 침하량은 같다(2.78 / 2.74 mm).
- 즉 **FL 행정 증가는 FL 패드(J1 연약 패치)의 추가 침하**이고, 그 침하는 cand가 LEVEL에 7.7 s 더 머무는 동안 생겼다. 높이 들어 올림이 커서 생긴 것이 아니다(z 원점 끝 차 +0.31 mm).
- DONE이 늦어진 이유: 비틀림 완료 완화(P-S8-29 V2b) DONE은 "LOC 뒤 자세·틈 10 s 유지 + 5 s 창 \|D\| 비증가 + \|D\| ≤ 15 kN + 하한 ≥ $F_{min}$"이다. 두 팔 모두 LOC + 10 s(약 46 s)보다 훨씬 늦게 DONE했으므로 \|D\| 비증가 창이 지배 조건이다(추정). 연약 패치 위 비틀림 힘 $D(t)$가 크리프로 천천히 움직이면, 같은 문턱(재상승 허용 0.6 kN)을 넘는 시각이 작은 궤적 차이에 크게 반응한다(문턱 사건 시각의 민감도).
- CC-R 최대 +7.7 s는 이 B1/B2 한 짝에서 나왔다. A 짝은 +1.2 / 0 / 0 s다.

제어 관점 해석(추정):
- B의 두 위반은 P5r4의 의도된 기구(LAS-b 끝 경계의 비틀림 계단 완화)와 무관한 **이산 사건 사슬의 결과**다: β 4.5 → LAS-b 0.2 s 일찍 시작 → 하중 궤적 변화 → P-S8-30 일시 감속 발동 → 램프 미발동 → LOC 0.2 s 늦음 → 비틀림 완료 창 통과 시각 7.7 s 늦음 → 연약 패치 크리프 시간 증가 → FL 행정 +2.8 mm.
- 하네스의 같은 경계 키(`D1|H-S-A|G1+J1@FL|T|flat|K1|VB|e0`)는 ref LAS-b 시작 없음, cand 시작 + 램프 4주기, Δs −0.12 mm, Δt +0.8 s였다. Chrono는 ref부터 LAS-b가 시작했고 cand에서 P-S8-30 감속이 끼어 램프가 없었다. 하네스와 Chrono는 이 키에서 **사건 순서부터 다르다**.
- CC-S 1 mm 문턱은 RV1-4가 말한 앵커 양자화 외에도 **정착 시간에 비례하는 연약 지면 크리프**에 민감하다(원판 7절 P-12 "확신 50 %"가 같은 위험을 적었다). 이번 위반은 그 위험이 B 짝에서 실현된 것이다.
- 따라서 B는 **P5r4 개념 결함이라기보다 LAS-b × P-S8-30 상호작용과 DONE 관문의 시각 민감도**가 드러난 것으로 본다(추정). 같은 상호작용은 P0에서도 다른 조건에서 생길 수 있다(β 3.5 시작 직후 감속이 끼는 경우).

### 8.4 PAIR_CMD_DIFF의 뜻

- `PAIR_CMD_DIFF` = 짝 동일 전제(cand LAS-b 시작 안 함)가 거짓인 짝에서 명령 해시가 다른 것. 설계상 생기는 차이이고 **기록만** 한다(원판 3절).
- Chrono 4짝(A1/A2, A3/A4, A5/A6, B1/B2) 모두 cand LAS-b가 시작한 짝이다. 첫 명령 차이 주기(경로 1 기록)는 348 / 352 / 343 / 346이고, 각각 cand의 LAS-b 시작 또는 끝(램프 시작) 주기와 맞는다. 전제가 참인 C 2짝은 해시가 같다 → **`PAIR_DIVERGE` 0, 구현 표류 없음.** BT-C 참과 함께 실행 경로가 결정론적이고 의도대로임을 뜻한다.
- 하네스: Z-T 144, Z-S 5, Z-C 56, PAIR_DIVERGE 0.

### 8.5 하네스는 통과, Chrono는 미달인 이유

| 항목 | 하네스 | Chrono | 해석 |
|---|---|---|---|
| A 계열 b0 이륙 골 | 키별 K1 VB 11.377 / K3 VB 11.281 / K1 V0 11.443 kN | A1 10.814 / A3 8.637 / A5 8.509 kN | Chrono 골이 키별로 0.56 / 2.64 / 2.93 kN 깊다 |
| A 계열 P5r4 골 | Z-A 최소 12.45 kN(G-2′ 여유 +1.04) | 11.36~14.79 kN | Kc3에서 하네스 여유가 Chrono에서 사라짐 |
| B 경계 키 사건 순서 | ref LAS 없음, cand LAS + 램프 | ref·cand 모두 LAS, cand 감속 끼어듦·램프 없음 | 사건 순서가 다름 |
| B 행정·READY | Δs −0.12 mm, Δt +0.8 s | +2.83 mm, +7.7 s | 정착 시간 차 + SCM 크리프 |

- 하네스는 축약 모델이다: 크롤러 집중 모델, 독립 numpy 플랜트, 연약 지면 근사. Chrono는 크롤러 D안(롤러 6/측 + 끝 슈) SMC 접촉, 구조 부싱·패드 구면 조인트, SCM Bekker-Wong 연약 지면을 쓴다. **하네스↔Chrono 이륙 구간(이탈 전후) 일치는 확인된 적이 없다**(원판 7절 P-8 "확신 중간"의 근거 문장). 이번 결과는 그 불일치가 A 계열에서 0.6~2.9 kN(Chrono가 더 보수적), B 계열에서 사건 순서 수준임을 보였다.
- 알려진 한계와의 관계(D-2 진단 반영, 일부 추정): A 골은 준정적 비틀림이 주성분이므로 깊이는 오일 기둥 비틀림 강성(β_eff·사체적, 즉 잠김 다리 강성 $k_{lock}$), FR 연약 패치 침하, 크롤러 제하 강성(Kc1/Kc3), 상부체 강체 가정에 좌우된다. 대부분 실측 전 가정치다(β_eff 감도 0.69~1.6 GPa, 사체적 Q-M12 대기). 하네스와 Chrono는 비틀림 강성·패치 침하 모델이 다르다(추정). 그래서 A의 수치(특히 58 N 차)는 이 가정치의 범위 안에서 쉽게 뒤집힐 수 있는 크기다. 이 점은 판정을 바꾸지 않는다(SK-5).

### 8.6 등급의 함의

- 규칙상 P5r4는 `미달`이다. 되돌리거나 문턱을 고치지 않는다(원판 8.1·8.2 끝 문장).
- P0 유지 권고이고, v5 제어기는 바뀌지 않는다.
- 다만 결과는 "P5r4가 나빠졌다"가 아니다. A 계열에서는 P5r4가 P0보다 확실히 좋다(골 +2.7~+6.3 kN, P0의 $F_{min}$ 위반 2건 해소). 미달은 (1) Kc3 한 조건에서 F_min + 2 kN 여유선을 0.5 % 밑돈 것과 (2) B 한 짝에서 사건 사슬로 생긴 정착 지연·크리프 행정 때문이다.
- 제어 관점 의견(추정): **P5r4 개념(이륙 전후 속도 성형, 특히 LAS-b 끝 복귀를 나누는 램프)은 맞는 방향이고, 실패는 파라미터 크기(A4)와 다른 규칙과의 상호작용(B)이다.** 개념 자체를 버릴 근거는 이번 결과에 없다. 반대로 지금 값(β 4.5, $N_r$ 4)으로 채택할 근거도 없다.

## 9. REM F2·기타 기록

- REM F2(첫 R4 LOC가 K1에 막히면 R4c30이 끝까지 없음): 하네스 `R4_LOST` 0, Chrono `R4_LOST` 0. **판정 행에서 관측 안 됨.**
- Chrono 행 실행 시간(wall_s, P 4행 병렬): B1 7,658, B2 8,894, C3 9,430, C4 9,398, A1 4,413, A2 4,333, A3 4,297, A4 4,289, A5 3,885, A6 3,997, C1 5,457, C2 5,391 s. 혼합 지형 A행 실측 약 3,900~4,400 s(가정 5,600 s보다 짧음).

## 10. 결정 기록 (사용자, 2026-11-12)

| # | 결정 | 고른 안 | 처리 |
|---|---|---|---|
| D-1 | P5r4 종결 | **`미달` 확정, P0 유지, 판정서 커밋** | 이 판정서. v5 제어기 `final_C4G2_LAS_K1`(VB `final_C4G2_P3_LAS_K1`) 불변, 프리셋 변경 없음 |
| 확인 1(판정 후 감사) | 단계별 판정에서 S-10 읽기 | **공개만** | 2.1·2.6절. 이번에는 S-10을 최종 판정 전 한 번으로 읽었다. 하네스 판정은 다시 돌리지 않았다. 다음 규칙은 단계별 자리·관문을 둔다 |
| 확인 2(판정 후 감사) | 경로 2 K 항목 None | **K-10 `일치` 유지**(10.2 문언) | 6.3절. 다음 규칙부터 K 항목 None = stop, 두 경로 수정, tools/verif 후보 `k_census` |
| D-2 | P0+K1 Chrono A3·A5 $F_{min}$ 하회 | 진단(dynamics-expert·control-expert) 완료 → **알려진 한계로 기록** 방향 | 8.2절 "D-2 진단 요약". A행은 운용 시작 조건 밖(SL-2 $R_c$ 1.035~1.076, `record_only`). 운용 범위 안 확인 실행 O-C5는 제안 상태(새 실행, 별도 승인) |
| D-3 | LAS-b 후속 설계 | 결정 없음(보류) | 재설계하면 LAS-b × P-S8-30 상호작용(감속 중 LAS-b 끝의 램프 정의)과 LAS-b 끝 복귀 비틀림을 먼저 보고, 새 원판에 결과 뒤 판·과적합을 공개한다. O-C5 결과를 근거로 정한다 |
| D-4 | 다음 규칙 문장 | 결정 없음(다음 원판 작성 때 검토) | C-S "같은 시각 비교" 또는 "DONE 시각 행정", CC-R 정착 관문 지연 분해 기록, 단계별 자리표시, K 항목 None = stop |
| D-5 | 경로 2 K-4 키 이름 결함 | 확인 2와 같음 | 다음 경로 2 판에서 고침(control-expert), 이번 결과에는 적용 안 함 |
| D-6 | 점검 공백(02:24~08:35) | 운용 개선 항목 | 등급 영향 없음 |

## 11. 재현

- K-10 비교: `C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B <scratchpad>\p5kj\k10_compare.py`(두 경로 출력 4개만 읽음).
- 원인 분석: `conda run -n dynamics-dev python -I -B <scratchpad>\p5kj\rows_summary.py`, `dip.py`, `series_cmp.py <ref case> <cand case>`, `pair_detail.py <ref case> <cand case>`(python-dev).
- 관문: `log_errors.py` 세 번(하네스 폴더, r2·첫 배치 progress.log `--pattern "\brc=(\d+)" --require-line`), `placeholder_scan.py`(prelaunch 전체).
- 하네스 줄 `touch_creep` 확인: `tcl_lines.py`.
- 경로 1·경로 2 명령은 `prelaunch/commands.md`(§판정)·`commands_path2.md`.
