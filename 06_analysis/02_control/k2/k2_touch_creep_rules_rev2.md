# K-2 규칙 덧붙임 rev2 (결과 전, 2026-11-10)

- 작성: control-expert, 2026-11-10. 봉인 정보는 같은 폴더의 `k2_touch_creep_rules_rev2.sha256`.
- 원판 `k2_touch_creep_rules.md`(sha256 `a3658197bdab02870a0b362144606f404021ebac90662a35efacfa8dbe477263`)와 rev1(`5ba081c62f8aef0edc5bb99119d7586b0d2914761582f2323c289f472f244776`)을 고치지 않고 아래만 덧붙인다. 셋이 다르면 rev2 > rev1 > 원판 순으로 맞다.
- 시점: V-1~V-7 결과 0건(실행 전 감사 `prelaunch/k2_prerun_audit.md`, 차단 2·실행 전 수정 9·확인 필요 4·기록 6). 계기는 그 감사와 사용자 결정(2026-11-10)이다. 이 판을 쓰면서 새 결과는 보지 않았다.
- 등급 영향: 1·2는 V-5 판정을 criteria.md 문구 그대로 되돌린다(완화가 아니라 원래 기준). 3은 V-6 그림자 지표의 계산법을 정할 뿐이다. 4~7은 정체성·기록이다.

## 1. V-5 판정 기준 (원판 3.4 대체 해석)

원판 3.4의 "합격 기준을 글자 그대로"는 **criteria.md의 절대 항목을 K-2 팔에 그대로 적용하고, 통과→실패 비교만 저장 기준 쌍 대신 같은 `{RUN_HEAD}`의 끔 팔 대비로 한다**는 뜻이다. 끔 팔에도 같은 항목을 계산해 기록한다. 기준 파일은 `06_analysis/02_control/touch_phase/acceptance/criteria.md`(git blob `86aa624264b3add5f24866f8ad21d91cb2c855be` @ `6a44ff8`, LF 내용 sha256 `a7363e161fef616915bcafa4e1b7b182e9501b28326634f4540cc8fc5c80590d`, k2-run 작업 사본 sha256 `a392730fc2160faf5f6c2c327ec1c5b8ae251427e3b259ef3bb074e791ceb00c`)다.

**두 경로는 V-5 원 출력(아래 "출력" 칸)을 직접 읽는다.** 평탄화기(`k2_v5_flatten.py`) 출력은 경로 1의 편의 입력으로 쓸 수 있지만, 경로 2는 평탄 파일을 읽지 않는다(규칙 8 독립성).

| 묶음 | 출력(팔 폴더 `runs/v5/<arm>/`) | 절대 항목(K-2 팔, 하나라도 어기면 그 묶음 실패) | 끔 팔 대비 |
|---|---|---|---|
| 공통 | 모든 V-5 단계 | 단계 sidecar `rc` = 0(구동기의 `main_tree_modules` 감시는 0이 아니면 비정상 종료한다), 결과의 오류 행 0(`results[]`·`runs[]`에 `error` 키), provenance `c2_sha256` = k2-run 작업 사본 `03_src/outrigger_sim/control/c2.py`의 sha256(`f58ee42b0f10ea42ceac5768e6ed373a38ee5e14440d9fc831536700b45ba6b1`, blob `18c71876…`) | – |
| 격자 | `grid_r67_main.json`, `grid_r67_top.json`, `grid_r69_top.json`, `grid_r69_bottom.json` | 행 = `results[].runs[]`(키 (key, timing, event, offset_s, run 순번)). 오류 결과 0, `fault_periods`가 비어 있지 않은 행 0 | 통과→실패 0(`runs[].pass`), 짝 없는 키 0 |
| 토양 | `soil_A.json`의 `\|two` 키 | 행 수 60. `\|G1\|`·`\|J2\|` 행 가운데 `pass` 거짓 0. 오류 0, `fault_periods` 행 0 | 그 밖(강체) 행 통과→실패 0. 짝 없는 키 0 |
| D8 | `d8_both.json` `runs[]` | 행 수 576. 행마다 `error` 없음, `fails` 빈 목록, `fault` 거짓, `min_true_cyl_force_kN` ≥ 14.41, `ss_true_att_deg_maxabs` ≤ 0.2, `t_ready_s` 있고 ≤ 100 | 기록(READY 평균 차, 최소 힘 최악 차) |
| 잡음 L2 | `r79_L1L2.json`(원 실행), `r79_L1L2_judgement.json`(기존 판정) | L2 행(`inner`에 `S1@FL`·`S1@FR` 없음) 855, 실패 k의 단측 CP 95 % 상계 ≤ 3 %(두 계산 경로). 판정 파일 `unmatched` = 0, `errors` = 0, `reference`의 `group == "all"` 행 `false_loc` = 0(L1 거짓 LOC 0). 원 실행 `results[]`마다 `controller_settings` = `meta.preset_settings`(SGS 설정 불일치 0) | 통과→실패 행은 목록으로 기록 |
| 회귀 | `clip_harness`, `clip_p0`, `clip_x426_C`, `clip_x426_D`, `clip_A`(.json), `clip_r79_L1L2_judgement.json` | 판정 키 93(2절), 오류 0. r79 판정 파일 `unmatched` = 0, `errors` = 0 | 판정 93키 통과→실패 0(`acc_judge.is_good`: `True`·`"pass"`·`"stroke_limited_pass"`), 짝 없는 키 0 |
| PS-7 | `ps7.json` | 행 수 20, 오류 0 | 통과→실패 0 |
| G8 | `g8_jobs1.jsonl`, `g8_jobs3.jsonl`, `g8_jobs5.jsonl` | 행 수 83, 오류 0 | 원판 3.4 G8 행(READY 상실, 새 `FAULT_*` 종류, pass→fail) 그대로 |

- **K-2 켬 증거(E-4의 V-5판)**: 팔마다 provenance 전부에서 다음을 확인한다. 하나라도 어기면 그 묶음은 판정 불가다.
  - `combo`: G8은 `off`, 그 밖은 `preset`
  - `k2` = 팔
  - `touch_creep_latch` = (팔 = K-2)
  - `controller_tag`: K-2 팔은 `_TCL`로 끝나고, 끔 팔은 `_TCL`이 없다
  - 행에 사건 목록이 있는 출력(잡음 원 실행 `results[].events`, PS-7 `events`, `clip_r79_*` `events`): K-2 팔은 그 파일에서 `INFO_TOUCH_CREEP_LATCH`가 있는 행이 1개 이상이고, 끔 팔은 `INFO_TOUCH_CREEP_*`가 있는 행이 0이다
  - 행마다 같지 않아도 된다(사전 접지 시작 등 TOUCH를 거치지 않는 행이 있다)
- **결측(E-9)**: 위 항목 값이 없거나 NaN이면 그 항목은 실패로 센다. 두 경로는 결측 수를 묶음·항목별로 출력한다.

## 2. 회귀 행 수

- 회귀 묶음의 판정 행은 **93**이다(`prelaunch/k2_v5_regression_keys.json`, 키 sha256 `2900db889efc73070c3a8fbe557b1a4ad9ee3392afc099ba00be1d0549174ec9`). 정의는 `acc_judge`의 회귀 판정 행 그대로다.
- **기록 행은 49**다(sha256 `d4f58334c6ca7c393c35072a798c09f4995d7fde274e0af6b21b99f977d503eb`). 내역은 `clip_r79_L1L2`의 판정 행이 아닌 7과 `clip_r79_L3L4` 42다.
- 원판 3.4·criteria.md의 "118"은 옛 재실행 목록의 행 수로, 저장 출력으로는 다시 만들 수 없다. 이 판부터 E-1의 회귀 기대 수는 93이다.
- r79 L1 기준 행은 판정 행이 아니다. criteria.md의 "L1·L2 행 통과→실패"는 r79 판정 파일의 L2 판정 행과 `clip_harness`·`clip_p0`의 L1 하네스 행을 가리킨다.
- 실행 뒤 같은 키 함수(`prelaunch/regression_keys.py keys`)를 두 팔 폴더에 돌려 두 sha가 위 값과 같아야 한다. 다르면 V-5는 판정 불가다.

## 3. V-6 그림자 지표 계산 (원판 5.2를 V-6에 적용하는 방법)

V-6은 8행을 한 묶음으로 본다. 짝은 같은 기본 이름(`K2_<engine>_top_<floor>_Fs<f>`)의 `_off`·`_tcl`이다(4쌍).

| # | V-6 계산 | FLAG |
|---|---|---|
| SH-1 | K-2 행마다 다리별 `INFO_TOUCH_CREEP_LATCH` 시각 뒤 `t_touch`까지 `k2_pads.npz` `N` ≤ 0 청크 수 | 어느 K-2 행이든 > 0 |
| SH-2 | 행마다 `k2_rate.npz`(`t`, `body_omega`)의 [`t_touch` − 0.3 s, `t_touch`) 구간 roll·pitch 각속도 (값 − 구간 평균) 최대 절대값 [°/s]. 표본이 2개 미만이면 결측 | K-2 4행 중앙값 > 끔 4행 중앙값 |
| SH-3 | 짝 4개의 `t_ready_s` 차(K-2 − 끔) | 어느 짝이든 > +3.0 s |
| SH-4 | 묶음 최솟값끼리: min(K-2 4행 J1) − min(끔 4행 J1) | < −3.0 kN |
| SH-5 | K-2 4행의 `INFO_TOUCH_CREEP_CAP` 수 + **L1 K-2 2행의 공중 거짓 래치 수**(원판 3.5 정의). L2b의 공중 거짓 래치는 G-E 판정 항목이다(원판 3.5) | 합 > 0 |
| SH-6 | K-2 4행의 J1·J2 < $F_{D8}$ + 2 kN | 하나라도 |

- 결측(E-9): 지표 값이 없는 행은 그 지표 판단에서 빼지 않는다. "결측 FLAG"로 세고 결측 수를 출력한다. SH-2는 한쪽 팔 중앙값을 낼 행이 4개 미만이면 FLAG다.

## 4. E-5·I-9 확인 값 (원판 3.3·3.5, rev1)

**V-3**: 행의 `k2.aug` 기록이 팔 정의와 같아야 한다. 수치 대조는 상대차 ≤ 1e-9다. 어기면 그 행은 판정 불가다.

| 팔 | 크롤러 kt/kn 배수 | $F_s$ 전방 / 후방 배수 | 이동 중 축 감쇠 | 열림 문턱 | 크롤러 c 배수 |
|---|---|---|---|---|---|
| H0 | 1 (옵션 없음) | 0 | 끔 | – | 1 |
| L1eq | 0.233093 | 0 | 끔 | – | 1 |
| L1eq_fs | 0.233093 | 4,000 N / 0.8333 | 끔 | – | 1 |
| L1eq_zm | 0.233093 | 0 | ζ 0.10(cn만, cn_LOCK × 0.10/0.03) | 1e-6 m/s | 1 |
| AUG | 0.233093 | 4,000 N / 0.8333 | ζ 0.10 | 1e-6 m/s | 1 |
| AUG_crc2 | 0.233093 | 4,000 N / 0.8333 | ζ 0.10 | 1e-6 m/s | 2 |
| AUG_eps | 0.233093 | 4,000 N / 0.8333 | ζ 0.10 | 0.1 $v_{max}$ = 2.0924e-3 m/s | 1 |

- 크롤러 heave 감쇠비 0.05는 모든 L1eq 계열 팔의 기준값이다(`k2_dyn_spec.md` 1).
- **V-2·V-4**: 옵션은 모두 꺼져 있어야 한다. 행에 `aug_arm`이 없거나 None이고, `k2.aug`가 없거나 None이다.
- **V-6 E-5**: L1 4행은 이동 중 감쇠 켬(ζ 0.10), L2b 4행은 끔이다. `k2_row.json`의 행 기록(`moving_damping`, `pad_zeta_moving` 또는 같은 뜻의 키)으로 확인한다.
- **I-9 열림 비율**: V-3 행과 V-6 L1 행은 [`t_touch`, `t_lift`] 구간의 다리별 밸브 열림 시간 비율을 4개 다 가져야 한다. 각각 유한하고 [0, 1] 안이어야 하며, 없으면 그 행은 판정 불가다. 값 자체는 기록만 한다.

## 5. 풀 (원판 7의 "P코어" 대체)

- V-2~V-5는 P코어 `0xFFFF`, worker 8이다.
- **V-6·V-7은 E코어 `0x0FFF0000`이다(사용자 결정 2026-11-10).** V-6은 L1 `--placement ecore`, L2b `--workers e6`이고, V-7은 `--parallel 0 --parallel-e 4`다.
- 짝 규칙(같은 묶음·같은 팔 정의의 끔·K-2는 같은 풀)은 그대로다.
- 배치표: `prelaunch/sched/k2_placement_20261110.json`(계획 `k2-sched-20261110a`).
- 러너 띄우는 순서: E_pre 성공 확인 → E_V6 두 러너 → 두 러너 프로세스 확인 → E_V7. 러너가 이 순서를 스스로 강제하지 않으면 메인 세션이 이 순서로 띄운다.

## 6. 판정 후 정체성 전수 확인 목록 (G-F의 "판정 후 감사"에 포함)

`record_check identity`(또는 같은 일을 하는 스크립트)로 아래를 **전수** 확인한다. 하나라도 어기면 G-F는 판정 불가다.
1. 래퍼 sidecar 62개(`k2_commands.json`의 `identity_sidecar`)
   - `rc` = 0
   - 시작·끝 HEAD = `6a44ff81d25aea1fa162daf9b14c23b99beb9db0`, 시작·끝 clean
   - env의 `MKL_THREADING_LAYER=TBB`와 `*_NUM_THREADS=1`
   - affinity·자식 마스크 = 배치표 값
2. V-5 provenance 전부: `c2_sha256`, `combo`, `k2`, `touch_creep_latch`, `controller_tag`(1절)
3. V-6 `batch_meta.json` 4개
   - `identity_start`/`identity_end`: orig_argv, cwd, git HEAD·status, env, affinity
   - `all_rc_zero` = 참
   - `k2.start_states`가 7절과 같다
   - env에 `OUTRIGGER_S8_CRAWLER`가 없다
4. V-7 `batch.json`과 행 `result.json`: argv, rc, `--threads`, `OMP_WAIT_POLICY=PASSIVE`, `hull_hook_effective`, git
5. 인터프리터 버전: acc_d8 `meta.d8x.identity_start`와 V-5 provenance 출력의 인터프리터. sidecar에는 없다
6. I-4 저장 행: main checkout `06_analysis/02_control/d8x/ra/ra_off.json`(sha256 `100985bf…cb10`), `ra_on.json`(`e3c8c95f…247a`). 판정 때 sha를 다시 확인한다

## 7. I-1·시작 상태 기록

- **I-1**: 하네스·Chrono 모두 $H_{impl}$ = $M$ = `6a44ff81d25aea1fa162daf9b14c23b99beb9db0`에서 돈다. 이 커밋은 `6f2f7cb`(`d8x_diag.py`)를 조상으로 포함한다.
- **V-6 시작 상태 (9.3)**
  - **L1-R**: k2-run `07_results\states_L1R`에 있다. 폴더 집계 sha는 `b24066a9…`이고 감사값과 같다(cad-expert 확인).

    | 파일 | sha256 |
    |---|---|
    | `S6_crawler_top_fdown3.5.npz` | `8f93d107fcd7ff8e4f22a0952dd35ca5bb409645737a0260ee354a7b6bedf9bd` |
    | `S6_crawler_top_fdown3.5.meta.json` | `9bb73974458de347a65a3a151cd044e5b801676b7e8b38881b8e8f119c2d133a` |
    | `S6_crawler_top_k2pp025.npz` | `be765f360d4319e499768d6d5364a2cca6f34a540955d6210886e9cc10587014` |
    | `S6_crawler_top_k2pp025.meta.json` | `c49fbfcf508bab2fda07b780353077110cc2cfb49ed37a5195aaea5290f5a07a` |

  - **L2b-NSC 4행**: 파일 없이 실행 안에서 정착한다(`k2_chrono_rows.start_states()` `kind: in_run_settle`, `snapshot: None`).
    - 경로: `run_S8C.build_l2b` → `run_S7C.l2b_crawler_start`(다리 행정 0, hanging) → `run_S7C.settle_l2b`(`CRAWLER_SETTLE_S` 3.0 s(**가정**), dt 1e-4, 30,000스텝, 명령 0) → `run_S8C.check_settle`(크롤러 법선력 < 0.5 $W_n$이면 거부)
    - 결정적이다. 기록은 result.json `settings.l2b_start`(`start_t_s` 3.0)에 남는다.
    - 코드 blob @ `6a44ff8`: `run_S7C.py` `b2b4458b29ea8fd50786827c958551ef0a55d5f9`, `run_S8C.py` `cec2c696befad75530588d07426a907e9d620821`
    - 실행 env에 `OUTRIGGER_S8_CRAWLER`를 두지 않는다(= YAML 강체 NSC).

## 8. 경로 도구

- 원판 8의 두 경로는 이 판의 1~4를 구현한 판으로 바꾼다. 새 blob은 실행 전 기록(I-3)에 고정한다.
- 경로 1 `k2_judge.py`(python-expert)는 rev1·rev2 `.sha256` 대조를 더한다.
- 경로 2 `k2_recount.py`(control-expert)는 V-5 원 출력을 직접 읽는다.
- 바꾸기 전 blob(경로 2 `d2240795…`, 경로 1 `7ee9ccc1…`)은 어느 결과에도 쓰이지 않았다.
