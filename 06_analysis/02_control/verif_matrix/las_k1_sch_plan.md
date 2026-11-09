# LAS-b K1 S-Ch 보충 계획 — Chrono SCM 패치 1키 (봉인판)

- 작성: control-expert, 2026-11-09
- 상태: **봉인판. S-Ch 실행 전에 봉인한다.** 봉인 시각과 sha256은 같은 폴더의 `las_k1_sch_plan.sha256`에 있다. 이 판을 바꾸려면 새 판(`las_k1_sch_plan_rev1.md` …)을 만들고, 첫머리에 결과를 보기 전인지 본 뒤인지 적는다.
- **시점: 결과 전.** S-Ch 결과(result.json)는 0건이다. 봉인 전에 본 자료는 7절에 적었다.
- 봉인 이력(공개): 19:05:07 +09:00에 한 번 봉인했다(sha256 `802e1643…522e`). 커밋·감사 전에 판정서가 커밋 `986f1a0`으로 바뀐 것을 발견해 7절 판정서 행과 2.1절 HEAD 주석만 고쳐 다시 봉인했다. 판정 기준·예측·정의는 바꾸지 않았다. 유효한 봉인은 `.sha256` 파일의 값 하나다.
- 근거 규칙
  - 원판 `las_k1_rules.md` sha256 `2742c9760ad55a87eccbf73e84025aafe0171a3555e1f54ab19fab24d888e4a0`. 3.5절(S-Ch), 5.5절(Q-C1~Q-C4), 4.4·4.5절(등급·종료 코드), 6·7·8절을 따른다.
  - rev1 `las_k1_rules_rev1.md` sha256 `eeee4ab9661babff50117b8ff579aa41e27a98d083f1fc13f46fb5c733e0b4d3`. R1-1(P3 짝 상대 정의)과 R1-2(C-2형 합집합 규칙)를 S-Ch 짝에 옮긴다.
  - 이 계획은 원판 5.5절에 **수치를 덧붙이고, 방향은 바꾸지 않는다.** 원판·rev1과 다르게 읽히는 곳이 있으면 원판·rev1이 우선한다. 단, Chrono 결과 필드로 옮기는 정의(2~4절)는 이 계획이 정한다.
- 원판 순서: Y 묶음 `통과`(판정서 `las_k1_judgement.md`, 판정 도구 `status` `pass`, 11-09 18:38 실행 끝) → cad-expert 행 정의(master `f25b043`) → **이 계획 봉인** → verif-protocol-auditor 실행 전 감사(차단 0) → 실행 → 판정.
- 규약
  - 제어: 이산 $T_s$ = 0.1 s(10 Hz), 출력 지연 $d$ = 1, C2 음되먹임($u$ = 다리 행정 속도 명령 [m/s]).
  - 단위: 행정은 모터 행정 [m](표에서는 mm), 힘은 실린더 순 힘 또는 SCM 법선력 [N], 틈은 [m](표에서는 mm).
  - 시각: Chrono 절대 시각 [s]이다. 정착 8 s 뒤 폐루프가 시작된다. 모든 시각 비교는 정수 주기 $n = \mathrm{round}(t/T_s)$로 한다(원판 5.0.2).
- 이름 구분(S2D·K1 교훈): **하네스 키의 `K1`은 크롤러 강성 ×1이다.** 순서 관문은 행 필드 `k1_candidate`(`K1off`·`K1on`)와 `--k1-order-gate`(`off`·`on`)로만 부른다.

## 1. 대상 행 (cad-expert 정의, master `f25b043`)

### 1.1 배치와 짝

| 항목 | 값 |
|---|---|
| 배치 | `V5-LAS-K1-CHRONO`(`s9_batch.py`, 정의 `04_scripts/02_chrono/las_k1_chrono_rows.py`) |
| 기준 행(base) | `SCh_G1_J2FL_B_top_Fs4_VB_gateoff` — `--k1-order-gate off`, `k1_candidate` `K1off` |
| 후보 행(cand) | `SCh_G1_J2FL_B_top_Fs4_VB_gateon` — `--k1-order-gate on`, `k1_candidate` `K1on` |
| **판정 짝** | **gateon(후보) 대 gateoff(기준)** |
| `las_candidate` | 두 행 모두 `P0`(LAS-b b0 채택 프리셋). P5r4는 이 계획의 대상이 아니다 |
| 하네스 대응 키 | `D1\|H-S-A-J2\|G1+J2@FL\|T\|flat\|K1\|VB\|e0`(`d1_rows.py` 287행 `_row("H-S-A-J2", "G1", "top", "flat", patch_soil="J2", patch_leg="FL")`, 모듈 상수 `PAD = "B"`, `FS_KN = 4.0`, `ROLE_RECORD`) |

### 1.2 공통 조건

| 항목 | 값 | 출처 |
|---|---|---|
| 지면 | 바닥 G1(SCM 격자 0.02 m) + J2 패치 @FL(격자 0.01 m, `--soil-patch FL:J2 --soil-patch-grid 0.01`), 크롤러 격자 0.04 m, 평지 | `run_S9.g6_case` |
| 패드·오거·마찰 | 패드 B(`dwg_rear250`), 오거 상단(top), $F_s$ 4 kN | 행 정의 |
| 시간 | 정착 8 s, 폐루프 200 s, dt 1×10⁻⁴ s | `K1C_DURATION_S` |
| 플랜트 | VB(`s9_batch.v5_vb_argv()`) | 행 정의 |
| 제어기 | `C2Config().with_10hz_d1()`, `--expect-controller final_C4G2_P3_LAS`. 두 행 모두 `--k1-order-gate`를 명시한다 | 행 정의 |
| 센서 | 압력 normal, IMU ideal, seed 20261026 | 행 정의 |
| 실행 | `--threads` 4(`SCM_THREADS_FIXED`), 시작 env `OMP_WAIT_POLICY=PASSIVE`, `OUTRIGGER_HULL_HOOK=fast`(명시 모드), P 풀(`planned_pool` `pcore`) | 행 정의, 프로젝트 SCM 규칙 |
| 볼록 껍질 DLL | `03_src/outrigger_sim/native/chrono_hull/bin/chrono_hull_hook.dll` sha256 `cec997d7a549788dab269b5e77cbad081796f58fd17d62c853d1164572c67e15`(= `hull_hook.VALIDATED_DLL_SHA256`, 봉인 전 작업 트리에서 다시 계산, 69,632 B) | 7절 |
| 예상 시간(가정) | 행당 약 3.3~3.5 h(`K1C_EST_S` 12,600 s). 2행을 P 풀에서 병렬로 돌리면 벽시계 약 3.5 h | cad-expert |

- 두 행의 argv 차이는 `--k1-order-gate` 값과 `--case` 값뿐이다(cad-expert 확인. 판정 때 K-0g로 다시 본다).

### 1.3 하네스 작업 dict 대조 (cad-expert 요청 5)

- 결과: **일치.** 바닥 G1, 패치 J2 @FL, 오거 top, 평지, 패드 B, $F_s$ 4 kN, 설정 VB, 위상 ε 0이 하네스 키 `D1|H-S-A-J2|G1+J2@FL|T|flat|K1|VB|e0`와 같다.
- control-expert는 `d1_rows.py` 287행(`H-S-A-J2` 행)과 모듈 상수 `PAD`·`FS_KN`을 직접 읽어 다시 확인했다.
- 하네스와 Chrono는 플랜트가 다르다(SCM 토양·크롤러 접촉). 그래서 하네스 수치(Y-Pa·Y-0c·Y-Sa)는 예측 근거로만 쓰고, 짝 기준으로는 쓰지 않는다.

## 2. 코드·실행 정체성 (K-0)

### 2.1 봉인한 sha256 (봉인 전에 control-expert가 다시 계산)

| 파일 | git blob(LF, `f25b043`) | 작업 트리 원시 바이트(CRLF) | 결과에 기록되는 곳 |
|---|---|---|---|
| `04_scripts/02_chrono/run_S9.py` | `914f2678f0399ba59f2616412add81c8339a9791e12210a989b9338fd6a9e3d7` | `f672622a37041f6e1b848987a677b22c8993286f586d65fbb1cd81f4c6fd23db` | 기록 없음 → 2.3 실행 전후 점검 |
| `04_scripts/02_chrono/las_k1_chrono_rows.py` | `594198eab169715c62ca1e6fd3f06d836f099859d957c5e66a1d599459324569` | `7e1d01ec86e4cff9d4e7c495ca7474c37efe612269cab03a614008457f2c20e0` | 기록 없음 → 2.3 |
| `04_scripts/02_chrono/s9_batch.py` | `18aee56052c90df4b919168bf6bcd203c2663606359c2ed2ac74208f7ff646b4` | `13e32ccad018984ffd0f0bdbc4df05dcf33a04098f3847a33384a966db99402e` | 기록 없음 → 2.3 |
| `03_src/outrigger_sim/control/c2.py` | `254921d1a8b0c6764ef9f5266be05fad61b7d5e7c73a6e0110802491e8aaa1de` | `a75d278030fffdeba3d3d88376a9d26eca80b79cb87c48fbb5b0ede3857fe0ed`(Y 묶음 줄의 기록값과 같다) | result.json `code_state.files_at_start["outrigger_sim.control.c2"].sha256`, batch.json `code_at_launch.files` |
| `03_src/outrigger_sim/control/zero_calibration.py` | `e55d3dd646db62bfe7409857b8467ab09713df9feedfe599b97047246e038132` | `b63a7a4713bc5be53098c08a375c348aca5769c11ac9fe5e6b085f39bcc0ffb1` | 같은 두 곳 |
| `03_src/outrigger_sim/chrono/hull_hook.py` | `aae8495824089e7932ec5f677f85d313ecc81a23db21e4747aedfb472be65ece` | `afef13ec8f75d42d95ddaf3342273c2ec476ae35450c665055f40100a5e3bdc3` | 기록 없음 → 2.3 |
| `04_scripts/03_control/s9/late_loc_rule.py`(run_S9가 실행 끝에 파일 경로로 읽음) | `76b549108ca39b9970e4906c5f4fe2de4ff71a6abc25989765ed552400075ee4` | 같음(LF 파일) | `p3b.P3-1_crawler.recontact_events.chatter.constants_source` |

- 봉인 시점 master HEAD는 `986f1a0`(판정서·decision_log 커밋)이다. `git diff --quiet f25b043 986f1a0 -- 03_src 02_params 04_scripts`는 참(코드 변경 없음)이므로, 위 blob 값은 `986f1a0`에서도 같다.
- 여섯 개 CRLF 작업 트리 파일 모두 "blob을 CRLF로 바꾼 바이트 = 작업 트리 바이트"를 확인했다. LF로 정규화한 작업 트리 바이트도 blob과 같다.
- **대조 기준(cad-expert 요청: 어느 sha로 볼지)**
  - 정본은 **git blob(LF) sha256**이다. 실행 HEAD에서 `git show <HEAD>:<경로>`의 sha256이 위 LF 값과 같아야 한다.
  - result.json `code_state.files_at_start`와 batch.json `code_at_launch.files`는 **작업 트리 원시 바이트(CRLF)**의 sha256을 적는다(`run_S9.code_state_files`, `s9_batch.launch_code_state`). 그래서 이 두 기록은 위 **CRLF 열**과 대조한다. LF 값과 다르다는 이유로 불일치로 판정하지 않는다.
  - run_S9.py·행 정의·s9_batch.py·hull_hook.py는 실행이 sha를 남기지 않는다. 그래서 2.3의 실행 전후 점검 파일로 CRLF 값을 확인한다.

### 2.2 정체성 항목 (두 행 모두, 행 사이 같음)

| # | 항목 | 기준 | 읽는 곳 |
|---|---|---|---|
| K-0a | 실행 HEAD | 두 행이 같다. `git diff --quiet f25b043 <HEAD> -- 03_src 02_params 04_scripts`가 참(변경 없음)이다 | result.json `code_state.git_at_start.head`. 그 값이 `{"error": …}`이면 batch.json `code_at_launch.git.head`를 쓴다(K1 Y-P에서 `git rev-parse` 시간 초과가 있었다). 둘 다 없으면 K-0a 거짓 |
| K-0b | 제어기 트리 깨끗함 | `code_state.git_at_start.dirty` = 빈 목록(두 행) | result.json |
| K-0c | 제어기 파일 sha | 2.1 CRLF 열(c2.py `a75d2780…`, zero_calibration.py `b63a7a47…`)과 같다. result.json과 batch.json 두 곳 모두 | result.json, batch.json |
| K-0d | 실행 전후 점검 | 2.3의 `sch_prelaunch.json`·`sch_postrun.json`이 있고 모든 항목이 참이다 | 2.3 |
| K-0e | 볼록 껍질 훅 | result.json `hull_hook`: `mode` = `fast`, `requested` = `fast`, `fallback_reason` = None, `dll_sha256` = `cec997d7…7e15`, `dll_sha_validated` 참. batch.json: `hull_hook_requested` = `fast`, `hull_hook_effective.mode` = `fast`, 배치 `mixed_hull_mode` 거짓 | result.json, batch.json |
| K-0f | 스레드·OMP·배치 | `args.threads` = 4, `num_threads_chrono` = 4, batch.json `omp_wait_policy` = `PASSIVE`, `pool` = `pcore`, result.json `placement.mode` = `pcore`, `placement.affinity_ok` 참, `placement.power_throttling_off_ok` 참 | result.json, batch.json |
| K-0g | 인자 | result.json `args`를 두 행에서 비교했을 때 다른 키가 정확히 {`k1_order_gate`, `case`}다. `k1_order_gate`는 gateoff `off`, gateon `on`이다. batch.json `argv`의 차이도 같은 두 값뿐이다. 그 밖에 `seed` 20261026, `pressure_grade` `normal`, `imu_grade` `ideal`, `fs_kN` 4.0, `duration` 200.0, `soil` `G1`, `soil_patch` `FL:J2`, `level` `top`, `expect_controller` `final_C4G2_P3_LAS`다 | result.json, batch.json |
| K-0h | 제어기 태그 | `v5_hydraulics.controller_tag` = `final_C4G2_P3_LAS`, `c2_setup.expect_controller.ok` 참, `c2_setup.k1_order_gate` = 행의 값(두 행) | result.json |
| K-0i | 종료 | batch.json `rc` = 0, `failed` 거짓(두 행) | batch.json |
| K-0j | 규칙·계획 파일 | 판정 시점에 원판·rev1·이 계획 파일의 sha256이 봉인 값과 같다 | 판정 도구가 다시 계산 |

- K-0a~K-0j 중 하나라도 거짓이면 **`stop`**(원판 SK-1)이다. 판정 등급을 내지 않고 사용자에게 묻는다.
- 판정은 결과 파일만 읽는다. 단 K-0a의 `git diff`와 K-0j의 sha 계산은 판정 도구가 실행 시점에 직접 한다(읽기 전용 git 조회).

### 2.3 실행 전후 점검 (메인 세션)

- **실행 직전**(배치를 띄우기 바로 앞)과 **두 행의 result.json이 모두 생긴 뒤**에 판정 도구의 `prelaunch`·`postrun` 하위 명령(5절)으로 아래를 기록한다.
- 출력: `06_analysis/03_hydraulic/coupled/v5/las/k1/sch_prelaunch.json`, `…/sch_postrun.json`(로컬 전용).
- 기록 항목
  - (1) `git rev-parse HEAD`
  - (2) `git diff --quiet f25b043 HEAD -- 03_src 02_params 04_scripts`의 결과
  - (3) `git status --porcelain=v1 -- 03_src 02_params 04_scripts`
    - 허용 목록: `04_scripts/02_chrono/run_S2a.py`, `04_scripts/02_chrono/render_S2_gifs.py`만 허용한다.
    - 이 두 파일은 지금 수정 상태이고, run_S9·s9_batch·행 정의가 import하지 않는다(봉인 전 grep으로 확인). 다른 경로가 있으면 거짓이다.
  - (4) 2.1 표의 일곱 파일 작업 트리 원시 sha256(CRLF 열과 같아야 함)
  - (5) DLL sha256
  - (6) 원판·rev1·이 계획의 sha256
- **실행 중에는 `03_src`·`02_params`·`04_scripts`의 작업 트리를 바꾸지 않고 master에 커밋하지 않는다.**
  - run_S9는 실행 끝(p3b 집계)에서 모듈과 `late_loc_rule.py`를 늦게 읽는다. 그래서 실행 중에 파일이 바뀌면 sha 기록 없이 다른 코드가 섞인다.
  - postrun의 (1)~(5)가 prelaunch와 같아야 K-0d가 참이다.

## 3. K1 작동 확인과 구조 (K-S)

### 3.1 기록 필드

- `controller_meta.slope_clearance_margin`
  - `order_gate.enabled`
  - `order_gate.decisions[]`: 항목마다 `t_loc_s`, `t_P_s`, `t_S_s`, `n_P`, `n_S`, `dP`, `r4_due_without_gate`, `would_block`, `applied`
  - `clearance_target_m`(실행 끝의 유효 틈 목표 [m])
  - `flat_soil_margin_applied`, `flat_soil_margin_t_s`, `is_applied`(P-S8-31 E3c10), `settle_attitude_deg`
- 사건(`events[].name`)
  - `INFO_LOC_FLAT_SOIL_MARGIN:<mm>`: R4c30 적용
  - `INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED:order`: 관문이 막음
  - `soil_mode_start`, `crawler_liftoff_confirmed`(LOC)
- **사건 이름은 `:` 앞 이름의 정확한 일치로 센다**(rev1 R1-5 2). 부분 문자열로 세지 않는다.

### 3.2 K1 작동 판정 (Q-C4 분기, 다른 판정보다 먼저)

- 기준 행(gateoff)의 `decisions`에서 `r4_due_without_gate` 참이고 `would_block` 참인 첫 항목을 **K1 작동 LOC**라 한다. 그 시각을 $t_{LOC}^{K}$ = `t_loc_s`, $n_{LOC}^{K}$ = round($t_{LOC}^{K}$/0.1)로 둔다.
- 다음 중 하나이면 **`K1 미작동(정보)`**(원판 Q-C4)이다.
  - `decisions`가 빈 목록이다. 토양 모드가 없었거나(사건 `soil_mode_start` 0건) P-S8-31 E3c10이 적용된 LOC뿐이었거나 LOC가 없었다. 판정서에 어느 경우인지 적는다.
  - `r4_due_without_gate` 참인 항목이 없다.
  - 그런 항목은 있으나 모두 `would_block` 거짓이다($n_P > n_S$).
- `K1 미작동(정보)`이면 실패가 아니다. 이때는 다음만 확인한다.
  - K-0 전부
  - K-S1·K-S2(아래)
  - **K-4형**: gateon 행 `controller_commands.npz`의 전체 `t_s`·`issued_u_m_s`가 gateoff와 비트 단위로 같다. 다르면 `stop`이다.
- 그 밖의 판정(4절)은 정보로만 적는다. 판정서에 공개하고 사용자에게 다른 패치 키를 더할지 묻는다.
- **기록 누락과 미작동을 구분한다**(부분 기록 교훈). `controller_meta.slope_clearance_margin` 또는 `order_gate` 키가 없거나 `{"error": …}`이면 미작동이 아니라 `incomplete`(6절)다.

### 3.3 구조 항목 (K1이 작동한 경우 전부, 미작동이면 K-S1·K-S2만)

| # | 기준 |
|---|---|
| K-S1 | `order_gate.enabled`가 gateoff 거짓, gateon 참이다. `c2_setup.k1_order_gate`가 `off` / `on`이다 |
| K-S2 | gateoff: 모든 decision에서 `applied` = `r4_due_without_gate`이다. `INFO_LOC_FLAT_SOIL_MARGIN_SKIPPED` 0건, `INFO_LOC_FLAT_SOIL_MARGIN` 건수 = `applied` 참 건수 |
| K-S3 | gateon: 모든 decision에서 `applied` = `r4_due_without_gate` ∧ ¬`would_block`이다. `_SKIPPED` 건수 = (`r4_due_without_gate` ∧ `would_block`) 건수, `INFO_LOC_FLAT_SOIL_MARGIN` 건수 = `applied` 참 건수 |
| K-S4 | 두 행 모든 decision에서 `t_P_s`·`t_S_s`로 $n_P$, $n_S$(round(t/0.1)), dP, `would_block`(= r4_due ∧ ($n_P$ 또는 $n_S$ 없음 ∨ $n_P \le n_S$))를 다시 계산한 값이 기록과 같다 |
| K-S5 | gateon에 round(`t_loc_s`/0.1) = $n_{LOC}^{K}$인 decision이 있고, 그 `t_P_s`·`t_S_s`가 gateoff의 K1 작동 LOC 값과 **부동소수까지 같다**(같은 전제 경로) |
| K-S6 | 실행 끝 `clearance_target_m`: gateoff는 R4c30이 적용됐으면 0.05 + 0.03 = 0.08 m, gateon은 모든 R4 평가 LOC가 막혔으면 0.05 m다(절대차 ≤ 1e-12 m). gateon에서 뒤 LOC(LOC 취소 뒤)에 R4c30이 적용되면 0.08 m이고, 그 사실을 공개한다 |
| K-S7 | **LOC 전 명령 같음(prefix)**(4.1 C-P) |

- K-S1~K-S7 중 하나라도 거짓이면 `stop`이다(원판 4.4 K 거짓).

## 4. 판정 기준 (K1이 작동한 경우)

### 4.1 C-P: LOC까지 명령 같음 (cad-expert 요청 4, = K-S7)

- 파일: 두 행의 `controller_commands.npz`(`t_s` [s] 길이 N, `issued_u_m_s` [m/s] N×4, 10 Hz 발행 명령)
- 주기 번호: $k_i$ = round(`t_s[i]`/0.1). |`t_s[i]`/0.1 − $k_i$| ≤ 1e-6이어야 한다(아니면 C-P 거짓).
- **자르는 점**: $n_{LOC}^{K}$(3.2, gateoff의 K1 작동 LOC 주기)다. prefix = $k_i < n_{LOC}^{K}$인 행이다.
  - LOC 주기 자체의 명령은 넣지 않는다. LOC를 처리한 주기에 틈 목표가 바뀌고, 같은 주기의 명령이 새 목표를 쓸 수 있기 때문이다.
- prefix 해시: sha256( `t_s[prefix]`를 `<f8` C 연속 바이트로 + `issued_u_m_s[prefix]`를 `<f8` C 연속 바이트로 ). 행 순서는 파일 순서 그대로다.
- **C-P 참**의 조건
  - 두 행의 prefix 행 수가 같고 1 이상이다(빈 prefix는 통과로 치지 않는다)
  - prefix 해시가 같다
  - `np.array_equal`이 참이다(두 배열 모두)
- 기록(판정 아님)
  - 처음 달라지는 주기 $k_{diff}$(예측 ≥ $n_{LOC}^{K}$)
  - LOC 주기 명령의 같음 여부
  - 전체 명령 sha256(두 행)
  - $n_{LOC}^{K}$ 전 사건 목록(이름, 주기)의 같음 여부
- C-P 거짓이면 `stop`이다. 같은 정체성에서 비트 결정성이 깨졌거나, K1이 LOC 전에 무언가를 바꿨다는 뜻이기 때문이다.

### 4.2 E-6형 (후보 gateon 행 절대 판정, 원판 Q-C3)

- 원래 E-6(명세 426.9 연구 A, 사용자 결정 (가) 2026-10-30)은 토양 사건 뒤의 크롤러 판정이다.
  - W 안 재접촉 = FLAG `E-6_event_transient_recontact`
  - W 밖·느린 사건 뒤 재접촉 = 실패
  - 끝 크롤러 하중 > 0 = 실패
  - 끝 전 절점 틈이 0 초과 25 mm 미만이고 크롤러 0이면 FLAG `E-6_post_event_clearance`
- 이 행에는 사건이 없다. 그래서 아래처럼 옮긴다(cad-expert 요청 1~3).

| # | 항목 | 정의 | 판정 |
|---|---|---|---|
| E-6a | 끝 크롤러 하중 0 | `step_series.npz`의 `scm_crawler_normal_N`(1 ms, 크롤러 SCM 법선력 합 [N])에서 끝 창 $[t_{end} - 1.0\ \mathrm{s},\ t_{end}]$($t_{end}$ = `t_s[-1]`, 창 약 1,000표본)의 최댓값 ≤ 0.0 N | 거짓이면 실패 |
| E-6b | 끝 전 절점 틈 | **판정값 = `p3b_ext.crawler_gap.grid_end_m`**(크롤러 바닥 격자점만, 마지막 10 Hz 행) | ≥ 0.025 m이면 참. 0 < 값 < 0.025 m이고 E-6a 참이면 FLAG `E-6_post_event_clearance`(실패 아님, 결정 (가) 그대로). ≤ 0 m이면 실패 |
| E-6b′ | 모서리 기록 | `p3b_ext.crawler_gap.end_m`(상자 모서리 48개 포함 전 절점)을 함께 적는다. `end_m` < `grid_end_m` − (마지막 `s9_rows` 행의 `crawler_gap_point_near_sinkage_m` + 0.005 m)이면 FLAG `SCh_end_corner_gap`(기록) | 판정 아님 |
| E-6c | W 밖·느린 사건 뒤 재접촉 0 | `p3b.departure.departed` 참이고 `t_confirmed_s`가 있으며, `p3b.P3-1_crawler.recontact_events.events` 중 `class` = `strict_fail` 0건 | 이탈 확인이 없으면 **거짓**(빈 사건 목록을 통과로 치지 않음). `strict_fail` ≥ 1건이면 실패 |
| E-6c′ | 짧은 재접촉 | 같은 목록의 `transient_flag`·`threshold_chatter` 건수와 각 사건의 시작·길이·최대 [N] | FLAG로 기록(`P3-1_transient_recontact`·`P3-1_threshold_chatter`, U-S9-G6d·Q-G 정의 그대로). E-6 원 정의의 `E-6_event_transient_recontact`에 해당한다 |
| E-6d | READY | `phases`에 `ready`가 있고, 마지막 `phases` 항목이 `ready`다 | 거짓이면 실패 |

- **E-6b를 `grid_end_m`으로 정한 이유**(cad-expert 요청 2)
  - 상자 모서리 48개는 트랙 가장자리에 있다. 가장 가까운 SCM 절점이 바퀴 자국 밖에 있으면 침하 0으로 읽혀, 틈이 크롤러 침하만큼 음으로 치우친다(`run_S9.py` 2049~2052·2103행 주석, G1 평지 정착 −3.9 mm).
  - P3-5·SL-3의 Chrono 판정값도 이미 `grid_min_m`(격자)으로 정해져 있다(control-expert 2026-10-28, `run_S9.py` 2115행). 같은 규칙을 따른다.
  - 전 절점 값은 E-6b′로 함께 공개한다.
- **E-6a 창을 1.0 s, 문턱을 0.0 N으로 정한 이유**(cad-expert 요청 3)
  - 끝 창 1.0 s는 P3-4 끝 창(`P3B_END_WINDOW_S` = 1.0 s)과 같다.
  - 0.0 N은 P3-1 READY 창 판정(`crawler_zero` = `cn[w].max() <= 0.0`)과 같다. 즉 SCM 접촉 패치가 하나라도 힘을 내면 실패다.
  - 끝값(`scm_crawler_normal_N[-1]`)과 창 안 접촉 패치 최대(`scm_crawler_patches`)도 기록한다.
- **E-6형 등급**
  - gateon에서 E-6a·E-6b(≤ 0)·E-6c·E-6d 중 하나가 실패이고 **gateoff는 같은 항목이 참**이면 `미달`이다(K1이 만든 나빠짐, 원판 SK-5와 같이 즉시 확정).
  - gateon과 gateoff가 **같은 항목에서 모두 실패**하면 `stop`이다. 채택된 프리셋(R4c30 적용)도 Chrono에서 이 기준을 넘지 못한다는 뜻이므로, K1 판정과 별개로 사용자에게 묻는다. 이 경우를 `미달`로 바꾸거나 기준을 고치지 않는다.
  - E-6형은 gateoff에도 같은 정의로 계산해 기록한다(짝 비교용).

### 4.3 짝 비교 (gateon 대 gateoff)

| # | 기준 | Chrono 정의 |
|---|---|---|
| C-2형 | 나빠짐 0(rev1 R1-2 합집합 규칙을 옮김) | (a) 아래 `p3b.checks` 불리언 9개 각각에서, 기준이 참 또는 None이고 후보가 거짓이면 위반이다. 기준이 참이고 후보가 None(키 없음 포함)이어도 위반이다: `P3-1_crawler_zero_after_ready`, `P3-1_recontact_pass`, `P3-2_within`, `P3-3_within`, `P3-4_within_0p2`, `P3-5_within`, `P3-6_within`, `P3-7_within`, `P3-8_within`. (b) 마지막 phase가 기준 `ready` → 후보 비ready이거나, 기준에 첫 READY 시각이 있고 후보는 없으면 위반. (c) 후보 사건 중 이름(`:` 앞)이 `FAULT_` 또는 `WARN_`로 시작하고 기준에 없는 이름이 있으면 위반 |
| P3 | 끝 크롤러 나빠짐 0(rev1 R1-1을 옮김) | 항목 `P3-1_crawler_zero_after_ready`, `P3-1_recontact_pass`, `P3-5_within`에 대해: 기준 참 → 후보 거짓 또는 None이면 위반, 기준 None → 후보 거짓이면 위반. 기준 거짓은 위반으로 세지 않고 `P3_baseline_false`로 적는다. 양쪽 None이면 해당 없음으로 센다 |
| C-S | 행정(1 mm, 원판 그대로) | $s_{max}$ = max(`p3b.P3-5_clearance_stroke.s_motor_max_m`)(네 다리 1 ms 모터 행정 최대 중 최대 [m]). 후보 − 기준 ≤ 0.001 m |
| C-F | 힘 여유선(원판 그대로, Chrono 대응량) | $F_{min}$ = min(`p3b.P3-3_leg_force.F_min_after_N`)(이탈 뒤 네 다리 실제 실린더 힘 최소 [N]). 기준 ≥ 10,414.589 N이면 후보도 ≥ 10,414.589 N. 기준이 문턱 아래면 해당 없음으로 적는다. 하네스 `F_judged_min_N`과 같은 양이 아니라는 점을 판정서에 적는다 |
| READY | 기록 | Δt = 후보 − 기준 첫 READY(`phases`의 첫 `ready` 시각)를 주기 단위와 s로 적는다. 판정에 쓰지 않는다. `P3-6_within`의 나빠짐은 C-2형 (a)로 본다 |
| 기록 | 판정 아님 | 끝 `clearance_target_m`, `rut_clearance_min_after_first_ready_m`, `p3b_ext.crawler_gap.after_first_ready.grid_min_m`·`all_min_m`, LOC 시각, 끝 자세(P3-4), 다리별 $s_{max}$, 이탈 시각, FLAG 목록(P3-2·P3-4·P3-1), INFO 사건 이름 집합 차 |

- 비교 허용치: 행정·힘·틈은 절대값 그대로 비교한다(원판 4.3, 부등호는 표에 적은 대로).

### 4.4 등급과 종료 코드

| 등급(판정서 어휘) | 도구 `status` | 종료 코드 | 조건 |
|---|---|---|---|
| `통과` | `pass` | 0 | K-0·K-S 전부 참, K1 작동, C-P 참, E-6형 실패 0, C-2형·P3·C-S·C-F 위반 0. FLAG(E-6b, E-6b′, E-6c′)는 통과와 함께 공개한다 |
| `미달` | `fail` | 1 | E-6형(gateon만 실패)·C-2형·P3·C-S·C-F 중 하나라도 위반. **나오는 즉시 확정**한다(원판 SK-5). 판정을 되돌리거나 기준을 고치지 않는다 |
| `stop` | `stop` | 2 | K-0·K-S·C-P 거짓, 또는 E-6형 같은 항목 양쪽 실패. 멈추고 사용자에게 묻는다. `미달`과 함께 나오면 `미달`이 우선이고 `stop` 사유를 공개 항목에 적는다(원판 4.5) |
| `K1 미작동(정보)` | `k1_inactive` | 2 | 3.2. 실패가 아니다. 사용자에게 다른 패치 키 추가 여부를 묻는다(원판 Q-C4). K-4형이 거짓이면 `stop`이 우선이다 |
| `incomplete` | `incomplete` | 3 | 6절 |

- 판정서는 도구의 `status`를 위 표대로 옮기고 다른 낱말로 바꾸지 않는다.

## 5. 판정 도구 명세

- 경로: `06_analysis/02_control/verif_matrix/scripts/las_k1_sch_judge.py`(이미 `scripts/* -text` 보호 범위다. `04_scripts` 밖이라 K-0a 코드 diff 범위에 들지 않는다).
- 구현: **cad-expert**(Chrono result.json·npz 구조 담당). 메인 세션이 python-expert로 넘겨도 된다.
- **실행 전 감사 전에 커밋한다.** 감사가 이 명세와 도구를 대조한다. 도구 sha256은 판정서에 적는다.
- 환경·규칙
  - 환경은 `conda run -n dynamics-dev python -I`다.
  - 읽기 전용이다. 자식 프로세스는 `git` 조회뿐이다(`rev-parse`, `diff --quiet`, `status --porcelain`, `show`).
  - `run_S9`·`s9_batch`·프로젝트 모듈을 import하지 않는다. json·numpy·hashlib만 쓴다.
  - 공통 CLI 계약: 종료 코드 0/1/2/3, `--out`·`--format json|md`, 마지막 줄 JSON.
- 하위 명령

| 하위 명령 | 입력 | 출력 |
|---|---|---|
| `prelaunch` | `--root`(기본 프로젝트) | 2.3 (1)~(6) → `…/v5/las/k1/sch_prelaunch.json`. 하나라도 어긋나면 종료 2이고 배치를 띄우지 않는다 |
| `postrun` | `--root` | 같은 항목 → `…/v5/las/k1/sch_postrun.json`. prelaunch와의 차이 목록 |
| `judge` | `--batch <07_results/S9/batch_V5-LAS-K1-CHRONO_<stamp>>`, `--prelaunch`, `--postrun` | `…/v5/las/k1/judge_SCh.json`: 2~4절 항목별 값·참거짓·등급, 4.1 prefix 정보, FLAG 목록, 사전 예측 대조표(6.1, 범위 안/밖 — 판정 아님), 읽은 파일 sha256 목록 |

- `judge` 입력 점검(7절 교훈)
  - batch.json `cases`의 행 이름이 정확히 두 개(1.1의 두 이름)이고, `pair_case`가 서로를 가리킨다. 이름이 더 있거나 빠지면 `stop`이다.
  - 각 행 폴더에 `result.json`, `step_series.npz`, `controller_commands.npz`가 있다. 없으면 `incomplete`다.
  - 필요한 기록 블록(`code_state`, `p3b`, `p3b.checks`, `p3b_ext.crawler_gap`, `controller_meta.slope_clearance_margin.order_gate`, `hull_hook`)이 `{"error": …}`이거나 없으면 `incomplete`다.
  - progress.log의 `START`·`END`·`RESUME_SKIP`·`SKIP`·`MIXED_HULL_MODE` 줄을 세어 기록한다.

### 5.1 두 경로 재집계

- 경로 1: 판정 도구 `judge` → `judge_SCh.json`
- 경로 2: control-expert 독립 집계(scratchpad, 판정 도구를 import하지 않고 같은 result.json·npz만 읽음). 2.2·3·4절 항목을 따로 구현한다.
- 대조
  - 수치 절대차 ≤ 1e-9
  - 불리언·사건 건수·주기 번호·prefix 해시는 완전 일치
  - 하나라도 다르면 판정서를 내지 않고 원인을 먼저 찾는다
- 이 행은 2짝 1개라 수작업으로도 할 수 있다. 그래도 두 경로를 모두 돌린다.

## 6. 멈춤·재실행·부분 기록

| # | 조건 | 처리 |
|---|---|---|
| SC-1 | prelaunch 어긋남 | 실행하지 않는다. 고친 뒤 prelaunch를 다시 돌린다(실행 전이라 공개만 한다) |
| SC-2 | 행 `rc` ≠ 0, result.json 없음, 필수 블록 오류 | 그 행만 같은 정체성으로 1회 다시 돌린다: `s9_batch.py run V5-LAS-K1-CHRONO --resume <같은 폴더>`, P 1슬롯. 끝난 행은 `RESUME_SKIP`으로 남는다. 재실행 전 prelaunch를 다시 기록하고, 같지 않으면 재실행하지 않는다(`stop`). 다시 실패하면 `incomplete`다 |
| SC-3 | K-0·K-S·C-P 거짓 | `stop`. 묻는다 |
| SC-4 | E-6형(gateon만)·C-2형·P3·C-S·C-F 위반 | 즉시 `미달` 확정 |
| SC-5 | K1 미작동 | `K1 미작동(정보)`. 묻는다 |

- 재실행 기록: 재실행한 행 이름, 1회차 실패 내용(`rc`, 로그 끝, git 시간 초과 여부), 2회차 HEAD·sha를 판정서에 적는다. 1회차 폴더 내용은 지우지 않는다. 이름이 같은 행 폴더를 덮어쓰기 전에 1회차 `result.json`이 있었으면 `<case>/attempt1/`로 옮겨 둔다(메인 세션).
- 두 행은 한 번의 `s9_batch run`(P 2슬롯)으로 함께 띄운다. 한 행이 먼저 실패해도 다른 행은 이미 돌고 있다(배치는 대기 행만 `SKIP`한다).
- `--keys`·`--only`·`--row-filter`는 쓰지 않는다. 배치의 두 행 전체를 돌린다. 재실행에만 `--resume`을 쓴다.

## 6.1 사전 예측 (원판 5.5 방향 유지, 수치 덧붙임)

- 예측은 판정 기준이 아니다(원판 5.0.1). 어긋나면 판정서에 숫자와 함께 적는다.
- 근거
  - 하네스 같은 키: Y-0c·Y-Pa·Y-Sa에서 dP −4~−8(P0), K1 효과 최대 행정 −29.96~−30.01 mm, $F_{judged,min}$ 비트 동일
  - 저장 Chrono 1건(7절, 2026-10-28 옛 제어기, 틈 목표 50 mm = K1이 막은 경우와 같은 목표): FL 최대 행정 472.9 mm, READY 후 바퀴 자국 틈 최소 55.9 mm, 이탈 33.02 s, 토양 모드 35.0 s → LOC 35.4 s, 끝 1 s 크롤러 최대 0.0 N, P3 전 항목 참
  - 명세 426.9: J2 B Chrono 틈은 하네스보다 약 −11.6 mm 작다

| # | 예측 (기준 = gateoff, 후보 = gateon) |
|---|---|
| Q-C1 | gateoff에서 `soil_mode_start` ≥ 1건, R4c30 적용(`INFO_LOC_FLAT_SOIL_MARGIN:80` 정확히 1건, 끝 `clearance_target_m` 0.08 m). K1 작동 LOC의 dP ∈ [−12, −1]주기(중앙 −6, $n_P \le n_S$), `would_block` 참. 토양 모드 시작은 LOC보다 앞서고 차이는 1~10주기다. LOC 절대 시각 ∈ [30, 40] s |
| Q-C2 | gateon에서 R4c30 막힘(`_SKIPPED:order` 1건, `INFO_LOC_FLAT_SOIL_MARGIN` 0건, 끝 `clearance_target_m` 0.05 m). C-P 참($k_{diff} \ge n_{LOC}^{K}$, $k_{diff}$ − $n_{LOC}^{K}$ ∈ [0, 5]주기). 최대 행정: gateoff ∈ [480, 530] mm, gateon ∈ [450, 500] mm, **Δ ∈ [−35, −25] mm**(중앙 −30). C-S 통과. $F_{min}$(C-F 대응량): 이탈 뒤 최소가 LOC 전이면 Δ = 0, 아니면 \|Δ\| ≤ 5 kN, 두 행 모두 ≥ 10,414.589 N |
| Q-C3 | gateon: E-6a 끝 1 s 크롤러 최대 0.0 N. E-6b `grid_end_m` ∈ [30, 70] mm(≥ 25 mm, FLAG 없음), gateoff ∈ [60, 100] mm, Δ ∈ [−35, −25] mm. E-6c 이탈 확인, `strict_fail` 0. E-6d 마지막 phase `ready`. P3-5 바퀴 자국 틈 최소(첫 READY 뒤): gateon ∈ [35, 70] mm, gateoff ∈ [65, 100] mm. C-2형·P3 위반 0, 새 FAULT·WARN 0. READY Δt ∈ [−5, +2] s. 전체 `통과` |
| Q-C4 | Q-C1이 틀려 K1이 작동하지 않으면($n_P > n_S$, 토양 모드 없음, E3c10 적용) `K1 미작동(정보)`다. 그때 두 행 명령은 전체가 비트 단위로 같다 |

## 7. 봉인 전에 본 자료 (과적합 공개)

| 자료 | 무엇을 봤나 |
|---|---|
| 원판 `las_k1_rules.md`(0~9절, 부록 목록 제목), rev1 전문 | 규칙 전체 |
| 판정서 `las_k1_judgement.md` | Y 묶음 판정값 전부: 경계 키 Δ −0.116 mm, 패치 키 5개 dP −8~−4·Δ −29.96~−30.02 mm, C_SA −30.009 mm, `p3_baseline_false` 17. Y 결과 jsonl 원본은 열지 않았다. 처음 읽은 판은 미커밋 작업 트리(sha256 `3761e92437b53e156081f2a4f9fa4f2f8c1a91359015469d337cdea3a7949e1f`)였다. 그 뒤 메인 세션이 커밋 `986f1a0`(2026-11-09 19:02:08 +09:00)으로 넣은 판은 sha256 `fdb8fab4f485ac99a1a1ab6b5b15b03ec401da255b87cbb188c5560f0241e103`이다. 이 계획이 쓴 값(위 수치)은 커밋 판에도 그대로 있음을 확인했다 |
| 코드(`f25b043`) | `las_k1_chrono_rows.py` 전문. `run_S9.py`의 `run_level`(5700~6000행), `CrawlerGapProbe`·`crawler_gap_summary`(2035~2136행), `recontact_events`(3279~3339행), `p3b_checks`·`p3b_records` 앞부분(5168~5360행), `code_state_files`·`git_state`(3862~3940행), 상수(`P3B_*`, `P3A_OFF_FRACTION`, `SCM_THREADS_FIXED`, `K1_ORDER_GATE_*`). `s9_batch.py`의 `launch_code_state`·`run_batch`(1355~1650행). `c2.py` 순서 관문 부분(3890~3921, 8726~8860행). `hull_hook.py` 기록 필드. `d1_rows.py` 280~291행 |
| 저장 Chrono 결과 1건 | `07_results/S9/batch_G6P_20261028_154030/G6_G1_B_top_Fs4_spJ2FL/`(같은 바닥·패치·패드·오거·$F_s$, 2026-10-28 옛 제어기, VB 아님, R4c30·K1 없음). 본 값: `p3b.checks` 전부, `s_motor_max_m`(FL 472.9 mm), `rut_clearance_min_after_first_ready_m` 55.9 mm, 이탈·LOC·토양 모드 시각, phases, 끝 1 s 크롤러 최대 0.0 N, 명령 npz 형식(`t_s` 8.1 s부터 0.1 s 간격, `issued_u_m_s` 2000×4). 이 실행에는 `crawler_gap`·`code_state`·`hull_hook` 기록이 없었다 |
| 명세 `s6_control_spec.md` | E-6 정의와 사용자 결정 (가)(17266·17354~17360행), 426.9 Chrono 틈 비교(18756행), R4c30 채택(18055~18066행) |
| 해시 | 2.1의 파일과 DLL을 봉인 전에 다시 계산했다(blob과 작업 트리 양쪽) |

- S-Ch 결과는 0건이다(배치 폴더 `batch_V5-LAS-K1-CHRONO_*` 없음).
- 사전 예측의 수치는 위 자료를 본 뒤 정했다.

## 8. S2D·K1에서 얻은 교훈 체크리스트 (판정서에 항목마다 적는다)

1. **짝 없는 키·목록 밖·중복**: 행은 정확히 두 개이고 `pair_case`가 서로를 가리킨다. 건수를 0이어도 적는다.
2. **빈 집합 통과 금지**: 이탈 확인이 없으면 E-6c 거짓, prefix 0행이면 C-P 거짓, decisions가 비면 미작동(통과 아님)으로 처리한다.
3. **부분 기록**: `{"error": …}` 블록은 `incomplete`로 보고 미작동·통과로 치지 않는다. `git_at_start` 오류는 batch.json 값으로 대체하고, 그 사실을 적는다.
4. **재실행 기록**: SC-2 재실행 행, `RESUME_SKIP` 줄, 1회차 보관 위치, git 시간 초과(Suspended git 추정) 여부를 적는다.
5. **이름 혼동**: 하네스 키 `K1`(크롤러 강성) ≠ 순서 관문. `las_candidate`·`k1_candidate`·`k1_order_gate`를 행마다 집계한다.
6. **정확한 사건 이름**: `:` 앞 이름의 일치로 센다(`INFO_LOC_FLAT_SOIL_MARGIN` ≠ `…_SKIPPED`).
7. **정수 주기 비교**: 모든 시각 비교는 round(t/0.1)로 한다.
8. **sha 기준**: 기록 sha는 CRLF 작업 트리 값이고, 정본은 LF blob이다(2.1). 둘을 섞어 거짓 불일치를 내지 않는다.
9. **실행 중 작업 트리 고정**: 실행 중 커밋하거나 코드를 바꾸지 않는다(실행 끝의 늦은 import). prelaunch와 postrun이 같아야 한다.
10. **봉인 시각 대 커밋 시각**: 이 계획 봉인 시각(.sha256)과 봉인 커밋 시각, 판정 도구 커밋 시각, 실행 시작 시각의 순서를 표로 적는다.
11. **미달·stop 우선순위**: 둘이 함께 나오면 `미달`이 우선이고 stop 사유를 공개한다.
12. **결과 본 뒤 규칙 변경 금지**: E-6b FLAG 구간, 1 mm, 10,414.589 N, 1.0 s 창, 0.0 N, 25 mm는 결과를 보고 바꾸지 않는다. 바꿔야 하면 "결과 본 뒤" 새 판으로 공개한다.
13. **볼록 껍질 대체 동작**: 명시 모드 fast가 DLL 없음·sha 다름으로 끝나면 종료 2이고, 기본 모드였다면 `off`로 조용히 대체됐을 것이다. `hull_hook_effective`로 실제 모드를 확인한다.
14. **두 경로 재집계**를 실제로 실행하고, 그 결과를 판정서에 적는다.

## 9. 이 계획이 하지 않는 것

- K1 채택(프리셋 기본 켬), LAS-b P5r4 처리, B1, 이상적 센서 진단, 재개 검증 436.8. 원판 9절 그대로 사용자가 정한다.
- 다른 패치 키 추가(Q-C4가 나오면 사용자에게 묻는다).
- 실행·코드 수정·커밋(이 계획 작성자는 하지 않는다).
