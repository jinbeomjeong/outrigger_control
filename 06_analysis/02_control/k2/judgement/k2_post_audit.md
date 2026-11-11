<!-- verif-protocol-auditor 리포트 원문(2026-11-11, 판정 후 감사). 대상: K-2 _TCL V-2~V-7, k2-run 6a44ff8, 판정 커밋 master da5e01b, 판정서 초안 k2_judgement_draft.md 0f9f0fa3. 메인 세션이 편집 없이 저장. -->

차단 2 / 실행 전 수정 6 / 확인 필요 4 (기록 9)

## 감사 요약
- 대상: K-2 `_TCL` V-2~V-7, 시점 **판정 후**. 실행 checkout은 k2-run `6a44ff8`, 판정 커밋은 master `da5e01b`이다. 판정서 초안은 `06_analysis/02_control/k2/judgement/k2_judgement_draft.md`(sha `0f9f0fa3…`, 미추적)이다.
- 기준 문서: 원판 `a3658197`, rev1 `5ba081c6`, rev2 `b3f1b41f`, rev3 `8bcdb0ed`, rev4 `82160ff5`, rev5 `73b87758`, rev6 `21268203`, rev7 `52d7dba9`, rev8 `e20ac116`, rev9 `797b8397`, 명세 `k2_dyn_spec.md` `502b0bb7`.
- 판정: **등급은 판정 불가로 확정할 수 있다. G-F는 판정 불가다.** 이번 감사에도 차단이 2건 있어서, 원판 7절 G-F의 "판정 후 감사 차단 0" 조건이 채워지지 않는다.
  - 초안의 판정 불가 근거 ①~③은 독립 재집계에서 모두 같은 값이 나왔다.
  - 초안에 없는 정체성 위반(규칙 문자 기준)이 1건 더 있다.
  - "판정 불가를 풀면 미달"이라는 서술을 독립 확인으로 받치는 항목은 G-E J9 하나뿐이다.

## 발견 사항 (심각도순)

**[차단][I] rev2 6절 3 "env에 `OUTRIGGER_S8_CRAWLER`가 없다"를 L2b batch_meta 2개가 문자 그대로 어긴다(초안에 없음)**
- 근거
  - `<k2-run>/07_results/S8/k2v6_L2b_off/batch_meta.json`과 `…/k2v6_L2b_tcl/batch_meta.json`의 `identity_start.env`·`identity_end.env`에 `"OUTRIGGER_S8_CRAWLER": "yaml"`이 있다.
  - 이 값은 실행기가 스스로 넣는다. `run_S8C.py:4372`에 `os.environ[CRAWLER_ENV] = args.crawler`가 있고, `:4307`에서 `--crawler`의 기본값이 `yaml`이다. 러너 step env(`steps_E_V6_*.json`)에는 이 변수가 없다.
  - 규칙 원문 rev2 7절의 "실행 env에 `OUTRIGGER_S8_CRAWLER`를 두지 않는다(= YAML 강체 NSC)"는 뜻(YAML 강체 NSC)으로는 지켜졌다. rev2 6절 3의 문자 조건은 어겼다. rev2 6절은 "하나라도 어기면 G-F는 판정 불가다"라고 정한다.
  - L1 2개 batch_meta에는 이 변수가 없다.
- 실패 시나리오: 판정 후 감사가 이 항목을 통과로 세면 봉인 문구와 다른 판정이 된다. 등급은 이미 판정 불가라서 바뀌지 않는다.
- 권장 조치
  - 판정서에 위반 사실과 의미상 동등함을 함께 적는다(확인 필요 Q1).
  - 다음 규칙에서는 "없거나 `yaml`"로 쓴다(control-expert).

**[차단][C·R] G-F 판정 불가 원인 재확인 — 초안 ①~③과 같다**
- rev9 3절 (b) TOUCH 시작 None 수
  - 오류가 아닌 하네스 행 6,642행이 모두 `k2.touch_start_s = None`이다.
  - 오류 행 576행에는 `k2` 블록 자체가 없다. 합계 7,218행 = V-2 2,204 + V-3 3,822 + V-4 1,192다.
  - Chrono V-6 8행은 `t_touch_start_s`가 모두 있다(None 0).
  - rev9 3절 원문: "0이 아니면 G-F는 판정 불가다".
- V-3 오류 행
  - L1eq 계열 6팔 × 2팔 × 48행 = 576행이다. 팔마다 kt 24행 + ktd0 24행이다.
  - 모든 행에 `ValueError('crawler_kt_rel together with ktcr_rel_kn')`가 있다.
  - 판정 팔 5개(L1eq, L1eq_fs, L1eq_zm, AUG, AUG_eps) × 48 = 240행이 E-5로 판정 불가다. rev6 3절에 따라 G-B도 판정 불가다.
- G-B 관문 값이 두 경로에서 다르다. 경로 1은 `not_judgeable`, 경로 2는 `fail`이다. 경로 2 코드 `k2_recount.py:1021-1024`는 실패 행이 있으면 `g_b="fail"`로 두고, 판정 불가 행은 problems에만 넣는다. rev6 3절에 맞는 쪽은 경로 1이다.
- 권장 조치: 초안 1.6절대로 판정 불가를 유지한다.

**[실행 전 수정][E] 하네스가 실행 오류를 행에 담고 종료 코드 0으로 끝나서, 오류가 약 4시간 동안 드러나지 않았다**
- 근거
  - `acc_d8.py:284`가 예외를 `{"error": repr(exc)}` 행으로 바꾼다. `:441`은 오류 수를 출력만 하고 종료한다.
  - 러너 로그 `scratchpad\sched\logs\P_main\v3_L1eq_off.log`에 `errors 48`이 있지만 sidecar `rc` = 0이다.
  - 첫 오류 단계는 23:49:40에 끝났다. 러너는 03:47까지 계속 돌았다.
  - rev2 6절 1의 "rc = 0"은 통과하지만, 이 경우에는 의미가 없는 검사다.
- 권장 조치(python-expert)
  - 오류 행이 1개 이상이면 acc_d8이 0이 아닌 코드(예: 2)로 끝나게 한다.
  - 또는 러너가 단계 출력의 `errors`를 보고 멈추게 한다.
  - 다음 실행 전 감사 항목에 "단계 로그 `errors 0`"을 넣는다.

**[실행 전 수정][R] kt × L1eq 충돌 — 실행 전 감사 5회와 G-S가 놓친 이유(요청 6)**
- 규칙에서
  - 원판 3.3절(`k2_touch_creep_rules.md:132`)은 L1eq 계열이 크롤러 kt/kn을 덮어쓴다고 정한다.
  - 같은 절의 대상 행(`:148-151`)에는 td_kt 48행이 들어 있다. 이 행들은 이미 `ktcr_rel_kn`으로 같은 kt를 바꾼다.
  - 같은 물리량을 두 번 덮어쓰는데, 두 정의를 어떻게 합칠지를 규칙과 명세(`k2_dyn_spec.md:16,26`) 어디에도 정하지 않았다.
- 코드에서
  - `KPlant` docstring(`run_s6_slope_boundary_check.py:577-578`)에 "refused together with `ktcr_rel_kn`"이 명시돼 있다.
  - 실제 거부는 `:643-644`의 `raise`다.
  - 즉 구현 단계에서 이미 알려진 거부였다.
- 검사에서
  - G-S의 I-8은 "옵션 모두 끔 = 비트 불변"(G0 60평가, R-c 24행)만 봤다.
  - 옵션을 켠 팔 × 단계(main, robust, kt)의 1행 실행은 G-S 근거(`gs_evidence/*.out`)에 없다. "L1eq"와 "--aug"로 grep해도 0건이다.
  - 실행 전 감사는 V-3 키 목록(273, `d4a030d7`, kt 48)을 재계산했다(`k2_prerun_audit.md:102`). 그러나 그 키가 각 팔에서 실행 가능한지는 보지 않았다.
- 재발 방지
  1. 규칙에서 보강·감도 옵션마다 "대상 행 단계가 이미 바꾸는 파라미터"와 겹치는지 표로 적는다.
  2. 실행 전 감사가 옵션 적용 코드의 `raise`·"together" 문구를 대상 키 단계와 grep으로 대조한다.
  3. G-S에 "팔 × 단계마다 1행 건조 실행(오류 0)"을 넣는다.
  4. 실행 중 점검에 단계 로그 `errors` 수를 넣는다(위 항목).

**[실행 전 수정][I] 자리표시가 채워지지 않아 V-7 기록 경로가 끊겼다**
- 근거
  - `prelaunch/k2_manifest.json`(추적, `9a34356`, sha `807e3690`)에 `{BATCH_V7}`이 그대로 있다. README `:44`는 "시작 뒤 채운다"고 했다.
  - 그래서 경로 1 `record_v7.json`이 `"file not found: {BATCH_V7}\\K2V7_…\\k2_row.json"`, exit 2로 끝났다.
  - `k2_commands_filled.json`의 `v7_k2_v7` 단계에서 `identity_sidecar`가 `{BATCH_V7}.launch.json`이다. 러너(`k2run_E_V7.ps1:24`)는 이 단계를 `Mask=$null`, 래퍼 없이 띄웠다. 그래서 sidecar가 없다.
  - `k2_prelaunch_v7.json:190`의 `{JUDGE_COMMIT}`도 채워지지 않았다. `da5e01b`는 scratchpad `k2judge\flat_main.ps1`·`path1.out`에만 남아 있다. rev7 3절은 "실행 전 기록에 적은 커밋"을 요구한다.
- 권장 조치(메인 세션): 판정 전 점검에 `\{[A-Z_]+\}` grep(manifest·prelaunch)을 넣는다. 판정서에 판정 커밋을 적는다.

**[실행 전 수정][C] 경로 1 출력이 잘렸다(C3 보강)**
- `judge_v3.json`의 `failed_rows`가 300개에서 끝난다(초안 C3과 같음).
- `problems`도 222개뿐이다. 그 가운데 E-5가 210개인데, 오류 행은 576행이다. [추정] 상한이 있다.
- 권장 조치(python-expert): 전체 출력 옵션을 두거나 상한을 없앤다. 잘렸으면 `truncated: true`와 원래 수를 출력한다.

**[실행 전 수정][R] 경로 2의 G-B 우선순위와 분기 계산(C4 보강)**
- `k2_recount.py:1021-1024`가 G-B를 정하는 방식이 rev6 3절과 맞지 않는다(위 차단 2의 근거와 같음).
- `:1744`는 G-B가 `fail`이면 B-4를 붙인다. B-4의 조건 "(현 모델은 통과)"는 보지 않는다.
- 권장 조치(control-expert, 다음 후보 경로 고정 전): 판정 불가가 실패보다 우선하게 고치고, 분기 조건을 규칙 원문대로 판정하게 한다.

**[실행 전 수정][I] rev2 6절 5 "V-5 provenance 출력의 인터프리터"를 확인할 근거가 없다**
- 근거
  - 두 팔의 `runs/v5/<arm>/provenance/*.json` 14개에는 `threads`·`argv`·`script`만 있다. 인터프리터 경로와 버전 필드가 없다.
  - `d8_both.json` `meta`에도 없다.
  - V-2~V-4의 acc_d8 `meta.d8x.identity_start`에는 `dynamics-dev\python.exe`, `3.12.15`가 20개 파일 모두에 있다.
  - sidecar의 `argv[0]`로 dynamics-dev 경로는 알 수 있지만 버전은 없다.
- 권장 조치: 확인 필요 Q2. 다음부터는 provenance에 `sys.executable`과 `sys.version`을 기록한다(python-expert).

**[기록]**
1. **"실질 미달"의 독립 근거는 G-E J9 1행뿐이다.**
   - G-A·G-B·G-C의 실패 항목은 모두 J3다. rev9 2.2절은 J3 1 ms 재계산을 "정렬된 정의"로 분류했다.
   - G-D(V-5 결과 종류)는 rev7 2절에서 정렬된 정의다.
   - 독립 확인(rev9 2.1)에 드는 실패는 V-6 `K2_L1_top_fdown3.5_Fs0_tcl`의 J9 `WARN_GYRO_BIAS_SKIPPED` 하나다.
   - 판정서에는 등급을 "판정 불가"로만 적고, 미달은 참고 서술로 둔다. 근거 항목의 독립·정렬 구분을 함께 적는다.
   - 참고: 이번 감사의 독립 재집계(행 필드 + 1 ms 시계열)에서도 J3 실패 수가 같았다.
2. 초안 0절 "실행된 분기 B-1, B-2, B-4, B-5, B-6, B-7"(`:24`) 가운데 세 분기는 괄호 조건이 원문 그대로는 맞지 않는다(원판 10.1).
   - B-2 "V-2 K-2만 실패": G-C도 실패다.
   - B-4 "현 모델은 통과": H0와 V-2·V-4가 실패다.
   - B-5 "하네스 통과": 하네스가 실패다.
   - 분석 범위를 정할 뿐이라 등급 영향은 없다(확인 필요 Q4).
3. V-7 I-6은 충족한다.
   - 4행 모두 `--threads 4`, `OMP_WAIT_POLICY=PASSIVE`다.
   - `hull_hook_effective`는 `fast`, `fallback_reason`은 null이다.
   - E코어 논리 프로세서 16~27(`0x0FFF0000`), rc 0, `code_at_launch.git` HEAD `6a44ff8` clean이다.
   - 두 팔이 같다.
   - 다만 git 기록은 시작 때뿐이고 끝 기록이 없다. 경로도 일부다. `planned_pool: "pcore"`가 실제 `pool: "ecore"`와 다르다. rev2 5절은 E코어를 정했으므로 실제 값이 맞다.
4. rev2 6절 1의 "sidecar 62개"와 실제 `k2_commands.json`의 `identity_sidecar` 63개(V-7 자리표시 포함)가 다르다. rev6 4절로 2개를 빼면 60개가 되고, 실제 60개가 모두 있다.
5. 초안 4.1절 문구: 576 오류 행은 "None"이 아니라 `k2` 블록이 없는 것이다(센 수는 같다).
6. 두 도구 모두 rev7~rev9 상수가 없다(seal_check `code_pin_missing`, `k2_judge.py:53`, `k2_recount.py:88`). rev8 3절·rev9 4절에 공개돼 있고, 이번 seal_check로 대조했다.
7. 경로 1 `judge_v3`의 "E-1 … 225 rows, expected 273"은 K1 끔 하위 묶음 기준이다. 묶음 요약은 `expected 273 / actual 273`으로 경로 2와 같다.
8. 사전 예측 범위 밖: L2b 4행의 J3 창 최소 패드 법선력은 31,494 / 31,752 / 31,494 / 31,757 N이다(예측 ≥ 40 kN). 초안과 같다.
9. 잡음 L2 끔 팔은 k = 8이다(기록만, K-2 팔은 k = 5).

## 규칙↔도구 대조표 (등급 산정, 요청 4)

| 규칙 원문 | 초안·도구 | 판단 |
|---|---|---|
| 원판 10절 "판정 불가: 빈 집합 방지·정체성·두 경로 일치 가운데 하나라도 실패", 순서 "판정 불가 > 미달 > …" | 초안 2절: 판정 불가 | 맞다 |
| rev6 3절 "판정 팔 6개의 E-5·I-9 위반은 … 그 행을 판정 불가 … G-B도 판정 불가" | 경로 1 `not_judgeable` / 경로 2 `fail`(`k2_recount.py:1021`) | 경로 1이 맞다. 초안 1.1절도 같은 판단 |
| rev6 3절 AUG_crc2는 기록 | 두 경로 모두 G-B에서 뺌 | 맞다 |
| rev9 3절 (b)·(c) "0이 아니면 G-F는 판정 불가" | (b) 6,642 + 576 결측, (c) 0 | 초안과 같다 |
| 원판 3.6절 V-7 "판정에 쓰지 않는다", 7절 관문에 V-7 없음, 11절 E-1 "V-7 4" | 초안 5절: 등급 영향 없음, 해석은 감사에 넘김 | 실제 행 4개(batch.json cases 4, rc 0, `failed: false`)라 E-1 수는 맞는다고 읽는다. 빠진 것은 3.6절 기록 항목(`k2_row.json`)이다. 빈 집합이 아니라 기록 공백이다(Q3) |
| rev2 6절 3 `OUTRIGGER_S8_CRAWLER` 없음 | L2b batch_meta에 `yaml` | 위반(새 발견) |

## 재집계 표 (요청 3, 독립 스크립트. 판정 도구 import 없음)

| 항목 | 판정서 값 | 재집계 값 | 차이 | 판단 |
|---|---|---|---|---|
| V-2 끔 pass/fail | 1,028 / 74 | 842+186 / 68+6 | 0 | 일치(실패 항목 J3뿐) |
| V-2 K-2 | 1,086 / 16 | 895+191 / 15+1 | 0 | 일치 |
| V-4 끔 / K-2 | 528/68, 582/14 | 같음 | 0 | 일치 |
| V-3 H0 끔 / K-2 | 205/68/0, 258/15/0 | 같음 | 0 | 일치 |
| V-3 L1eq 끔 / K-2 | 194/31/48, 219/6/48 | 같음 | 0 | 일치 |
| V-3 L1eq_fs 끔 / K-2 | 223/2/48 둘 다 | 같음 | 0 | 일치 |
| V-3 L1eq_zm·AUG·AUG_eps K-2 실패 | 5·2·2 | 5·2·2(끔 23·3·3) | 0 | 일치 |
| AUG_crc2 끔 / K-2 실패 | 1 / 5 | 1 / 5 | 0 | 일치 |
| 오류 행 | 576(kt·ktd0 48 × 12) | 576(각 팔 kt 24 + ktd0 24) | 0 | 일치 |
| J3 행 필드 ↔ 1 ms 재계산(판정 종류) | 차이 0 | 7,218행 중 0 | 0 | 일치 |
| TOUCH 시작 None | 전 행 | 6,642 None + 576 블록 없음 | 0 | 일치(문구만 다름) |
| V-6 J6 잠김 None | 0(116.5~128.9 bar) | 0(116.53~128.90) | 0 | 일치 |
| V-6 실패 | K-2 1행 J9 | `fdown3.5_Fs0_tcl` J9, 끔 짝도 같은 WARN | 0 | 일치 |
| V-5 토양 | 60, 실패 1 | 60, `A\|J2\|FL\|Fs8\|two` 회차 1(끔 `t_ready_back` 60.0 = `run_after` 60.0, K-2 `probe`) | 0 | 일치 |
| V-5 G8 | 83, READY 상실·새 FAULT 4 | 83, 같은 4키(s6·s8·s10·s16), `FAULT_LIFT_STROKE_LIMIT` | 0 | 일치 |
| V-5 잡음 L2 K-2 | k 5, CP 0.012256339337941437 | k 5, 이분법 0.012256339337941402 | 상대 약 3e-15 | 일치(반올림) |
| V-5 잡음 통과→실패(기록) | 5 | 같은 5키 | 0 | 일치 |
| V-5 D8 | 576, 절대 위반 0 | 576, 0 | 0 | 일치 |
| V-5 격자 | 768, 통과→실패 0 | 192 × 4, 0, `fault_periods` 0 | 0 | 일치 |
| V-5 PS-7 | 20 | 20, 오류 0 | 0 | 일치 |
| I-4 끔 팔 명령 해시 | – | 910 / 192행 차이 0, 저장 `ra_off` `100985bf…cb10`·`ra_on` `e3c8c95f…247a` sha 재확인 | – | 통과 |
| E-4·E-6 | – | 위반 0. 태그는 팔마다 하나(`final_C4G2_LAS[_K1][_TCL]`, `touch_creep_latch`·K1 플래그 일치) | – | 통과 |

## 정체성 전수 (요청 2)
- sidecar 60개: 모두 rc 0이다.
  - 시작·끝 HEAD는 `6a44ff8`이고 clean이다.
  - env 5개(`MKL_THREADING_LAYER=TBB`, `*_NUM_THREADS=1`)가 맞다.
  - affinity·자식 마스크가 모두 `0xFFFF`(배치표 값)이다.
  - argv가 `inner_argv`와 같고 cwd도 같다.
  - 문제 0건이다. V-7 자리표시 1개는 제외했다.
- `flat_main` 2개(rev7 3절): 기대값과 모두 같다.
  - rc 0, HEAD `da5e01b`(시작·끝 같음), clean이다.
  - env 5개가 맞고, 마스크 `0x0FFF0000`, argv·cwd(main)가 같다.
  - `da5e01b:04_scripts/03_control/k2/k2_v5_flatten.py`의 blob은 `b3851190`이다.
  - 단, sidecar에 `--git-dir` 값 필드는 없다. HEAD가 main과 같아서 main checkout으로 판단했다.
- V-6 batch_meta 4개
  - HEAD `6a44ff8` clean(시작·끝), `all_rc_zero` 참, 행 exit 0이다.
  - affinity `0xfff0000`, `MKL_THREADING_LAYER=TBB`, pychrono 10.0.0이다.
  - `k2.start_states`가 rev2 7절과 같다. L1R 스냅숏 4개 파일의 sha가 rev2 7절 값과 같다.
  - **L2b 2개에서만 `OUTRIGGER_S8_CRAWLER` 위반**이 있다(위 차단).
- V-5 provenance: 14단계 × 2팔과 d8 meta에서 `c2_sha256` `f58ee42b…`, `combo`, `k2`, `touch_creep_latch`, `controller_tag`, `git_head`가 모두 맞다. G8 83행의 `touch_creep_latch`·`_TCL`도 맞다. 인터프리터는 기록이 없다(위 항목).
- V-7: 위 기록 3.

## 시간 순서 (요청 5, T축)
- 봉인 시각: rev9 `.sha256`이 22:14:28, 커밋 `b8e63c6`이 22:15:26이다. 병합 `da5e01b`는 22:17:17이다.
- 첫 결과: V-2 sidecar `start` 22:18:18, V-6 `identity_start` 22:18:19 KST(13:18:19Z), V-7 `taken_utc` 14:17:58Z = 23:17:58이다.
- `timeline.py`의 690개 비교가 모두 `before`였다. info 5건은 batch json의 mtime 근거라서, 위의 레코드 안 시각으로 대신했다.
- 판정 도구가 판정 뒤에 바뀌지 않았다. HEAD와 작업 트리의 blob이 같다.
  - `k2_recount.py` `82299dd2`(LF sha `1951c5ea`이 출력 `tool_sha256`과 같음)
  - `k2_judge.py` `74d72d5e`
  - `d8x_recount.py` `d47c10e9`
  - `k2_v5_flatten.py` `b3851190`
  - 마지막 변경은 `87a245f` 21:55:37이다. 판정 출력 시각은 03:55~03:57이다. main의 추적 파일은 clean이다.
- 봉인(S): seal_check 결과 10판이 모두 raw 일치다. LF, BOM 없음, `-text` 보호다. `judgement/`·`runs/` 출력도 `text: unset`(보호)이다.

## 확인 필요
- Q1. rev2 6절 3 `OUTRIGGER_S8_CRAWLER` "없다"를 문자 그대로 볼지, 뜻(YAML 강체 NSC, 값 `yaml`)으로 볼지. 문자로 보면 G-F 판정 불가 원인이 하나 더 생긴다. 어느 쪽이든 등급은 판정 불가 그대로다.
- Q2. rev2 6절 5의 V-5 인터프리터 확인 근거가 없는 것을 위반(판정 불가)으로 볼지, 기록 공백으로 볼지.
- Q3. V-7: 실제 4행이 있으니 E-1은 충족하고 3.6절 기록만 빠졌다고 보는 이 감사의 해석을 판정서에 쓸지. 다른 해석은 "E-1 묶음 판정 불가 → 원판 10절 빈 집합 방지 실패"다.
- Q4. 초안의 "실행된 분기" 표기를 원문 괄호 조건대로 고칠지(B-2·B-4·B-5).

## 사용자 결정 D-1~D-7에 덧붙일 것 (요청 7)
- D-1(가): 등급 칸에는 "판정 불가"만 쓴다. "실질 미달"은 참고 서술로 두고, 독립 근거가 G-E J9 1행뿐이며 J3·V-5는 정렬된 정의라는 점을 함께 적는다.
- D-3(나): 다음 규칙에서 처음부터 빼는 것이면 결과 전 정의다. 이번 규칙의 rev10으로 하면 결과 뒤 개정이므로 공개 절과 원판 기준 결과를 함께 적는다.
- D-5: B-6 가름 실행도 `run_with_identity` 래퍼(sidecar)로 돌리고, 기록 전용임을 실행 전 기록에 적는다. 합격 수를 바꾸지 않는다는 문구를 그대로 둔다.
- D-6: 어댑터는 결과 뒤에 쓰는 새 코드다. blob을 고정하고, "기록 전용·결과 뒤 작성"을 공개한다. 출력은 결과 폴더가 아닌 `judgement/v7_rows/`에 둔다. manifest `{BATCH_V7}`를 채운 판의 sha를 판정서에 적는다.
- D-7 추가: acc_d8 오류 행 비영 종료, 경로 1 `problems` 상한, 자리표시 점검, provenance 인터프리터 기록, 분기 조건 판정.
- (새) D-8: Q1·Q2의 해석.
- (새) D-9: 다음 후보 규칙의 G-S에 "옵션 팔 × 단계 1행 건조 실행"을 넣을지.

## 위임 필요
- python-expert
  - `acc_d8.py:284,441`: 오류 행이 1개 이상이면 0이 아닌 종료.
  - `k2_judge.py`: `failed_rows`·`problems` 전체 출력 또는 `truncated` 표시.
  - provenance 출력(`ACC_PROVENANCE` 기록기)에 `sys.executable`·`sys.version` 추가.
  - V-7 SCM 기록 어댑터(초안 5절, D-6 승인 뒤).
- control-expert: 다음 후보 경로 2의 G-B 우선순위(`k2_recount.py:1021-1024`)와 분기 조건(`:1744`). 판정서 문구(기록 1·2·5, Q1~Q4).
- `tools/verif 후보`
  - "단계 로그 `errors N` 비영 탐지"(입력: 러너 로그 폴더, 출력: 단계별 오류 수, 종료 1)
  - "manifest·실행 전 기록 자리표시 `{[A-Z_]+}` 탐지"(입력: json 글롭, 종료 1)

## 메인 세션 권고
- 판정서에 판정 커밋 `da5e01b`, flat_main HEAD, manifest sha `807e3690`(자리표시가 남은 판)을 적는다.
- V-7을 기록하려면 D-6 결정 뒤 어댑터를 만들고 `record-v7`을 다시 돌린다(시뮬레이션 재실행 없음).

## 검사하지 못한 것
- SH-1~SH-6 FLAG 값 자체(중앙값, SH-1 청크)를 독립으로 다시 계산하지 않았다. 결측 처리 차이는 규칙 문구로만 판단했다.
- V-5 회귀 93키는 전부 다시 세지 않았다. 실패 1키는 토양 같은 키(`clip_A` `A|J2|FL|Fs8|two` 회차 1)로만 확인했다. 판정 키 sha `2900db88…`, 기록 키 sha `d4f58334…`의 재계산도 하지 않았다.
- E-7(각도 ↔ 점 파일)과 E-5 V-3 `resolved` 값의 수치 대조는 하지 않았다.
- D̂ 기록(rev1 4절)과 5.4 사전 예측의 나머지 항목은 대조하지 않았다.
- 경로 1·2 transcript(독립성 공개 보완)는 이번에 다시 검색하지 않았다.

## 실행한 검증
- 인터프리터: python-dev `C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B -X utf8`, `MKL_THREADING_LAYER=TBB`. 대상 프로젝트 import는 없고, dynamics-dev는 쓰지 않았다(원 결과 JSON·npz만 읽음).
- 도구
  - `seal_check.py --repo . "06_analysis/02_control/k2/k2_touch_creep_rules*.md" k2_dyn_spec.md --code 04_scripts/03_control/k2`: warning 3, 모두 기록 6과 명세 `.sha256` 없음(원판 3.3절에 해시가 적혀 있고 `502b0bb7`과 일치)
  - `timeline.py --rules <10판> --results <launch 64, batch.json, batch_meta 4> --time-field start`
- 즉석 스크립트(scratchpad `verifk2post\`): `ident.py`(sidecar 60 + flat_main), `v6meta.py`, `prov.py`, `recount.py`(V-2~V-4 행 판정·1 ms J3·TOUCH 시작·오류 행), `v5recount.py`, `e4i4.py`, `peek5.py`. 보고 전에 폴더째 지웠다(`Test-Path` False).
- 조회 명령: `git rev-parse`·`hash-object`·`log`·`reflog`·`check-attr`·`status`, `Get-FileHash`, Grep.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha k2_touch_creep_rules_rev1.md 5ba081c6…, k2_touch_creep_rules_rev2.md b3f1b41f…, k2_touch_creep_rules_rev3.md 8bcdb0ed…, k2_touch_creep_rules_rev4.md 82160ff5…, k2_touch_creep_rules_rev5.md 73b87758…, k2_touch_creep_rules_rev6.md 21268203…, k2_touch_creep_rules_rev7.md 52d7dba9…, k2_touch_creep_rules_rev8.md e20ac116…, k2_touch_creep_rules_rev9.md 797b8397…, k2_touch_creep_rules.md a3658197…, k2_touch_creep_rules_rev1.sha256 fdf6d8ca…, k2_touch_creep_rules_rev2.sha256 2fd7dc24…, k2_touch_creep_rules_rev3.sha256 de03d989…, k2_touch_creep_rules_rev4.sha256 735815f4…, k2_touch_creep_rules_rev5.sha256 f3e5eb8e…, k2_touch_creep_rules_rev6.sha256 e31f6204…, k2_touch_creep_rules_rev7.sha256 9d702767…, k2_touch_creep_rules_rev8.sha256 591d35e0…, k2_touch_creep_rules_rev9.sha256 2b4c4305…, k2_touch_creep_rules.sha256 6a7d3b25…, k2_dyn_spec.md 502b0bb7…, k2_judgement_draft.md 0f9f0fa3…, k2_path2.json 8948c5ed…, path2_selftest_d8x.json 7d360489…, path2_selftest_v5_stored.json d79c8231…, judge_v2.json fcf84d40…, judge_v3.json 7bfe603f…, judge_v4.json a187ce9d…, judge_v5.json fde6e143…, judge_v6.json 34e0a0a8…, record_v7.json 36a25851…, report_pre_gf.json b7667a27…, k2_manifest.json 807e3690…, k2_fields.json 0c5aafc4…, k2_expect.json ecef70d2…, k2_commands.json ce6e04a2…, k2_commands_filled.json 402a1ef3…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 최종 판정 직전에 초안 `:18`, `:24`, `:195`를 다시 확인했다. source_guard verify 결과 감사 중 바뀐 입력은 없다.
- 메모리: `C:\Users\jinbeom\.claude\agent-memory\verif-protocol-auditor\audit_pitfalls.md`에 함정 4개를 추가했다(팔 × 단계 옵션 거부가 오류 행 rc 0으로 숨음, env "없음" 조항과 실행기 자체 설정, 자리표시 미기입, 정렬 항목에 기댄 "실질 실패"). `MEMORY.md` 색인도 고쳤다.
- 사용한 스킬: 없음
