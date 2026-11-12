# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev1 (구현 질문 해소와 2026-11-13 사용자 결정 문장화, 결과 전, 봉인)

- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev1.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev1_seal_candidate_draft.md`와 1·3·5·8행만 다르다.
- 원판 `v5_resume_4368_rules.md`(sha256 `9019b405b7a196f28a756e7ca91f443f6241a58bd8e1eee0361483066cb19524`, 봉인 2026-11-13 00:46:07 +09:00, 커밋 `f46b5ab`)는 고치지 않는다. 봉인 뒤 이 판과 원판이 다르면 이 판이 맞다. 이 판이 말하지 않는 것은 원판 그대로다.
- **시점: 436.8 본 실행 결과가 없을 때(봉인 2026-11-13 01:49:34 +09:00, 봉인 커밋 71baa2b).** 436.8 본 묶음과 0단계 T-3K는 한 줄·한 행도 돌지 않았다. 있는 것은 Chrono G-S 배치 2개뿐이다(RV1-0).
- 작성: control-expert, 2026-11-13. 기준 master `71baa2b`(작성 시점 HEAD). 경로 1 구현 worktree `agent-ad7e24bd7496f7e54`(커밋 `24495d8`), Chrono 행 worktree `agent-a7addabbe8e298481`(커밋 `058d4dd`·`2102d3f`, 작업본 수정 1파일)를 읽었다. 이 작성자는 경로 2 작성자가 아니다(경로 2는 dynamics-expert, 원판 9.2).
- **바꾸지 않는 것**: 숫자 문턱, 등급과 우선순위(원판 8.1), 멈춤 조건 S-1~S-15의 뜻, 묶음 범위(원판 5.1·5.2의 묶음과 Chrono 행 목록·argv), 두 경로 요건(원판 9.2), 사전 예측 P-1~P-15의 예측 내용. 이 판은 원판 문장으로 풀리지 않는 곳의 해석·대응 규칙과 줄 수·이름만 정한다.
- **Q-1 답(사용자 결정 2026-11-13): A안.** RV1-3이 그 답이다(저장 키 집합 + 저장소 러너, `LAS_T3_DG3_P3=off`는 H-7에만). 봉인본이다.

## RV1-0. 결과 전 근거와 공개

### RV1-0.1 지금 있는 결과 (2026-11-13, main checkout과 두 worktree에서 확인)

- 하네스: `06_analysis/03_hydraulic/coupled/v5/resume_k1/`, `06_analysis/02_control/v5_rerun/las_k1/`, `06_analysis/03_hydraulic/coupled/v5/las/t3_k1/`이 세 checkout 어디에도 없다.
- Chrono: `07_results/S9/`에서 이름에 `RESUME-K1`이 든 폴더는 G-S 배치 `batch_V5-RESUME-K1-GS_20261113_010654`(main checkout과 Chrono worktree)와 `batch_V5-RESUME-K1-GS_20261113_012403`(Chrono worktree)뿐이다. G-S는 판정하지 않는다(원판 11.2).
- 이 작성자가 G-S에서 읽은 것은 `v5_resume_4368/gs_check_20261113_010654.txt`(키 경로 존재 여부와 `conditional_absent` 키 이름)뿐이다. 힘·행정·판정 값은 읽지 않았다.

### RV1-0.2 이 판을 쓰려고 읽은 것

- 규칙: 원판, `u3_u6_rerun_rules.md`, `u3_u6_rerun_rules_rev2.md`, `las_targeted_rules_rev5.md`, `las_p5r4_k1_rules.md` 599~607행(Z-C 비트 기준), `v5_criteria.md`·rev2·rev4·rev8(7.2 p3_hash)·rev11, `k2/loc_shadow/hsh_report.md` 4.1절.
- 코드(정의만, 경로 1 worktree): `run_v5.py`(`p3_hash_jobs`, `job_key`, `overlap_reference`, `OVERLAP_REFERENCE_PATH`), `resume_k1_steps.py`(`BLOCKED`, `h10_counts`), `resume_k1_record.py`, `las_t3_dg3.py`, `r79_L3L4_final.py`(`cmd_run`, `plain_jobs`), `r79_sensor_screen.py`·`r67_g1_screen.py` 변경분, `b5_baseline_compare.py`(`--pad`), `v5_options.py`(`controller_tag`), `loc_anchor_shadow.py`(`ENV_SWITCH`, `install`), `u3_judge.py` ↔ `u3_judge_k1.py` 차이. Chrono worktree: `v5_resume_4368_chrono_rows.py`(`PROBE_*`, `K_DECIMALS`, `gs_rows`, `SERIES_FILES`), `run_S9.py`·`run_S8C.py`·`run_S6C.py` 출력 파일 이름.
- 저장 결과는 식별 필드만 읽었다: `results[].key`, `job`, `las.candidate`, `k1.sub_bundle`, `meta`(스크립트·레벨·오프셋·건수·설정). 계산은 scratchpad 읽기 전용 스크립트 4개(`anchor_keys.py`, `anchor_select.py`, `keysets.py`, `h10_count.py`)로 했다. 값(해시·판정·힘·행정)은 읽지 않았다.
- 문서: `06_analysis/02_control/stroke_input_review.md`(sha256 `2f4d0dc0…`), `06_analysis/03_hydraulic/end_stop_cushion_model_review.md`(sha256 `7497c98b…`)의 결론 표(RV1-10 i·j 근거).

## RV1-1. A-4 행 생성기 목록 (질문 1)

- 원판 3절 A-4의 목록에서 `las_k1_chrono_rows.py`(`V5-LAS-K1-CHRONO`)와 `las_k1_rem_chrono_rows.py`(`V5-LAS-K1-REM`)를 뺀다. 두 묶음은 K1 채택 판정의 관문 끔·켬 짝이고 436.8 C-1~C-8에 없다. 두 생성기는 그대로 둔다(각 봉인 규칙 K-5의 태그 유지).
- A-4 목록은 다음으로 읽는다: `d1_chrono_rows.py`, `v5_stage3_las_rows.py`, `las_chrono_rows.py`, `v5_resume_4368_chrono_rows.py`(436.8 Chrono 행 생성기), 개정판 `u3_judge`(`u3_judge_k1.py`).
- 436.8 행은 빠진 두 생성기로 만들지 않는다. 11.1 겹침 표에 두 생성기 사용 0을 적는다.

## RV1-2. H-10 줄 수 440 (질문 2)

- H-10의 p3_hash 22작업은 main VB·LS 388작업 가운데 사례마다 첫 VB 작업과 `run_v5.job_key`가 같다(22/22, 2026-11-13 계산). 같은 커밋·같은 설정의 결정론 실행이므로 같은 실행이다.
- 그래서 H-10 표의 줄 수는 **440**(main VB·LS1~LS4 388 + U-9 VB 28 + item8 12 + overlap 12)이다. p3_hash를 따로 돌리지 않는다. 같은 파일 `h10_reuse_rerun.jsonl`의 main VB 줄이 그 22작업이다.
- 개정 8 7.2의 p3_hash 해시 대조는 닫힌 검사(개정 11 47행)이므로 436.8에서 다시 판정하지 않는다. 22줄은 v5 기준으로 main 줄과 같이 한 번 판정한다.
- 원판 5.1의 본 묶음 합계는 **9,778줄**(9,800 − 22)로 읽는다. 원판 5.1 끝 문장(S-15)의 대조값은 이 판의 값이다.

## RV1-3. H-6~H-9 러너·작업 키·출력 (질문 3, 사용자 결정 Q-1 = A)

### RV1-3.1 원칙

- 원판 5.1의 "원 명령"은 저장소에 없는 scratchpad 래퍼를 가리켜 그대로 따를 수 없다. 이 묶음들은 **저장 결과의 작업 키 집합 + 저장소 러너**로 정의한다.
  - 작업 키 집합 = 아래 표의 저장 파일(sha256 확인)의 `results[].key` 전부. 새 출력의 키 집합이 이것과 같지 않으면 S-15다.
  - 러너는 저장소 파일만 쓴다. `C2Config.with_10hz_d1()` 기본값을 바꾸는 래퍼는 쓰지 않는다(원판 4.2 그대로).
- 출력은 러너 고유 형식(`<이름>.json` + `<이름>.json.partial.jsonl`)으로 `06_analysis/03_hydraulic/coupled/v5/resume_k1/` 아래에 쓴다. 원판 4.3의 `h6_dg3_v4on.jsonl`, `h7_dg3_off.jsonl`, `h8_noise.jsonl`과 `h9_stage1.jsonl` 격자 부분은 RV1-3.3 이름으로 바꾼다.
- 각 출력의 `.identity.json`은 그 단계의 앞·뒤에 python-expert의 정체성 기록 단계가 쓴다(`run_v5._write_identity`와 같은 `run_identity` 기록). 러너 코드에 넣지 않아도 된다.

### RV1-3.2 묶음별 정의

| # | 러너(저장소) | 조건 | 작업 키 원본(sha256 앞 16자리) | 수 |
|---|---|---|---|---|
| H-6 | `04_scripts/04_hydraulic/coupled/las_t3_dg3.py`(`r79_L3L4_final.py`를 그대로 부름) `run --levels L2,L3 --keys <135키>` | env `R79_V5_SETTING=VB`, `R72_PATH=per_leg`, `R79_T4H_DIR`(T4h 폴더), `LAS_T3_DG3_LAS=on`, `LAS_T3_DG3_K1=on`, `LAS_T3_DG3_P3=on` | `v5/dg3/dg3_v4_on.json`(`5f912ca0d25d6dfe`) | 135(L3 134 + L2 1) |
| H-7 | 같음 | 같음, 단 `LAS_T3_DG3_P3=off` | `v5/dg3/off/dg3_off.json`(`95b81f82d800ae3c`), 키 집합은 H-6과 같다 | 135 |
| H-8 잡음 VB·V0 | `04_scripts/03_control/s8/r79_L3L4_final.py run --levels L1,L2,L3`(키 지정 없음) | env `R79_V5_SETTING=VB` 또는 `V0`, `R72_PATH=per_leg` | `v5/noise_vb/r79_VB_L1L2L3.json`(`d3c9bba1abd3c1fb`), `v5/noise_v0/r79_V0_L1L2L3.json`(`af6a7ae51abe4b90`), 두 키 집합은 같다 | 1,503 × 2 |
| H-8 seedext | `r79_L3L4_final.py run --levels L2`에 저장 키 목록을 그대로 받는 저장소 옵션(python-expert 추가, 아래) | env `R79_V5_SETTING=VB` 또는 `V0`, `R72_PATH=per_leg` | `v5/seedext/r79_VB_seedext.json`(`6ddca3d5ce5dc628`), `…/r79_V0_seedext.json`(`f2c01d65238cac50`), 두 키 집합은 같다(2기본 키 × 시드 0~24) | 50 × 2 |
| H-9 격자 | 저장 V0 짝 provenance의 `script`와 같은 파일: `grid_r67_main`·`grid_r67_top` = `r67_g1_screen.py`, `grid_r69_bottom`·`grid_r69_top` = `r69_g5_screen.py` | env `R67_*`는 저장 `v5/grid_vb/<파일>.json` `meta`(`offsets_s`, `n_jobs`, `candidate` = current, `v5_setting` = VB)가 같아지도록 python-expert가 정한다 | `v5/grid_vb/grid_r67_main.json`(`8ef4237dc7658559`), `…_r67_top`(`498aa41199b2e4ed`), `…_r69_bottom`(`ee84750be278a2c2`), `…_r69_top`(`c132fd41f13b8033`) | `runs[]` 192 × 4 = 768 |

- **H-7의 ③ 끔**: `LAS_T3_DG3_P3=off`는 `run_v5.SETTINGS["VB"]`에서 `extend_start_tracked`만 뺀다(`las_t3_dg3.py` 66~71행, 봉인 rev3~rev5 T-3b가 같은 러너로 쓴 끔 팔). 프리셋 `with_10hz_d1()` 기본값은 건드리지 않는다. **원판 4.2의 금지 래퍼에 해당하지 않는 것으로 H-7에만 허용한다.** H-6·H-8·H-9·H-10에는 `LAS_T3_DG3_P3=off`를 쓰지 않는다. `LAS_T3_DG3_LAS=off`는 어느 묶음에도 쓰지 않는다.
- **H-7 기대 태그**: VB 플랜트지만 ③ 꺼짐이므로 `final_C4G2_LAS_K1`이다(원판 4.1 "그 밖 ③ 없는 설정"). `is_extend_start_tag`가 거짓이어야 하고, 실행된 프리셋의 `two_pressure.extend_start_rule`이 `tracked_bound`가 아니어야 한다. H-6은 `final_C4G2_P3_LAS_K1`, `tracked_bound`다.
- **seedext 키 옵션**: `r79_L3L4_final.py` `cmd_run`은 기본 시드 밖의 키를 거부한다(`keys not in the job list`). python-expert가 저장 키 목록 파일을 그대로 받는 옵션을 저장소에 넣는다. 그 옵션은 작업 목록만 바꾸고 작업마다 `run_one`을 그대로 부른다. 그 커밋은 `git_at_start` 이전이어야 한다(원판 A-5). G-S(11.2)에서 시드 ≥ 3인 키 1줄을 돌려 받아들여지는지 본다.
- **H-8의 dg3 대체**: 원판 5.1 H-8 "dg3가 대체한 L3 134·L2 1의 처리는 원 규칙 그대로"는 그대로다. 그 135키는 H-6 줄로 판정한다. 같은 키의 H-6 줄과 H-8 VB 줄의 `commands_sha256` 같음 여부를 기록한다(같다고 예측한다. 다르면 기록하고 python-expert에 원인 확인을 넘긴다. 멈춤 사유가 아니다).
- **H-8 seedext와 잡음의 겹침**: seedext 키 가운데 시드 0~4의 10키는 잡음 키와 같다. 파일이 달라 줄 수는 원판대로 센다(H-8 = 1,503 + 1,503 + 50 + 50 = 3,106).
- **H-9 격자의 줄 수**: 격자 파일의 S-15 대조값은 `runs[]` 수(파일마다 192, 합 768)다. 격자 줄의 태그 확인(원판 4.1·S-2)과 4.2 기록 확인은 각 run의 `resume_k1` 블록과 v5 기록 칸으로 한다. 태그 필드가 run에 없으면 G-S에서 멈추고 묻는다(S-11).

### RV1-3.3 출력 이름 (원판 4.3 표의 해당 칸을 바꾼다)

| 묶음 | 출력(`06_analysis/03_hydraulic/coupled/v5/resume_k1/` 아래) |
|---|---|
| H-6 | `h6_dg3_v4on.json`(+ `.partial.jsonl`), T4h `h6_dg3_v4on_t4h/` |
| H-7 | `h7_dg3_off.json`(+ `.partial.jsonl`), T4h `h7_dg3_off_t4h/` |
| H-8 | `h8_noise_VB.json`, `h8_noise_V0.json`, `h8_seedext_VB.json`, `h8_seedext_V0.json`(각 + `.partial.jsonl`) |
| H-9 | main·pressure_only는 원판대로 `h9_stage1.jsonl`. 격자는 `h9_grid/grid_r67_main.json`, `h9_grid/grid_r67_top.json`, `h9_grid/grid_r69_bottom.json`, `h9_grid/grid_r69_top.json` |

- 각 출력에 `.identity.json`이 동반한다(RV1-3.1).
- 이어쓰기는 러너의 `.partial.jsonl` 규칙대로이고, 저장 기준선 파일(`v5/dg3/`, `v5/noise_*`, `v5/seedext/`, `v5/grid_vb/`)에는 쓰지 않는다(원판 A-9).

## RV1-4. overlap 기준 시각 다시 계산 (질문 4)

- H-10 overlap의 기준 시각 `t_a`는 **현행 제어기로 다시 구한다.** `v5_criteria.md` 261행은 `t_a`를 "VB 기준 실행"에서 정하고, 개정 4·5·6은 그 기준 실행 1건을 overlap 묶음에 넣는다. 저장 `v5/overlap_t_a.json`(sha256 `39bc75cb…`)은 ③·LAS-b·K1 전 VB에서 나온 값이고, 436.8은 재사용하지 않는다(사용자 결정 Q1 (a)).
- 기준 실행은 같은 `git_at_start`에서 VB(③ 켬, 프리셋 그대로) 1건이고, 결과를 `resume_k1/h10_overlap_t_a.json`에 쓴다. 저장 `v5/overlap_t_a.json`은 읽지도 덮어쓰지도 않는다. 이 경로를 쓰도록 `run_v5.py`에 경로 인자를 더하는 일은 python-expert 몫이다(16절).
- 기준 실행 1건은 줄이 아니므로 H-10 줄 수(440)에 세지 않는다. 판정서에 저장 `t_a`와 새 `t_a`, 새 기준 실행의 `commands_sha256`을 함께 적는다(기록).

## RV1-5. P-1·P-2 비트 앵커의 줄 대응 (질문 5)

- 앵커 줄과 H-1 줄은 **`run_v5.job_key(line["job"])`이 같은 것끼리** 짝짓는다(`job`에서 `mask`·`t4h_dir`만 뺀 전체 사전). `rev.key`·`d1.key` 같은 문자열 키는 대응에 쓰지 않는다. 2026-11-13 계산에서 여섯 앵커 파일의 모든 줄이 `d1_rows.jobs()`의 작업과 이 방식으로 맞았다.
- 앵커 줄 고르기(각 파일에서 `error` 키가 없는 줄만):

| 예측 | 앵커 파일(sha256) | 고르는 줄 | 키 수 |
|---|---|---|---|
| P-1 T-1 | `v5/las/las_T1.jsonl`(`3dee4f6b88e71654debd68b3ef5c5f1a9b01f1dba8fcd731d1355ec219d9a85b`) | `las.candidate` = `b0` | 8(H-R-A) |
| P-1 T-2 | `v5/las/las_T2.jsonl`(`2fe6a54aafdc0c3ffbf1991907ee4e1af85761e1bef2e25bef07dd52ab199efb`) | `las.candidate` = `b0` | 184(H-R-0 48 + H-R-A 136) |
| P-1 나머지 | `v5/d1.jsonl`(`9039b36a1a9c4ba5ed63528bb7384773018d4c7377dccbf76b18fbcfda86707f`) | 위 192키 밖의 H-R-0 줄 | 216 |
| P-2 Y-Pa | `v5/las/k1/k1_YP.jsonl`(`0d985d5624f0fbb0219ca50d1c839b7db639011d6c2ab14fa9d84cfd197fc2c3`) | `k1.sub_bundle` = `Y-Pa` ∧ `las.candidate` = `P0` | 165 |
| P-2 나머지 | `v5/soil_defer/s2d_SC.jsonl`(`70e91ec1234d56a918af1b4fc053c3175f0f14ab41e2b5f334890f7dc6cb08aa`) | Y-Pa 165키 밖의 줄 | 291 |

- 고른 앵커는 키마다 정확히 1줄이어야 한다. 0줄이나 2줄 이상이면 S-7이다. 2026-11-13 계산: 중복 0, T-1·T-2 겹침 0, 192키 ⊂ 강체 412, Y-Pa 165 ⊂ 토양 456, `s2d_SC.jsonl`이 토양 456을 모두 덮는다. H-R-A-stop 4줄은 원판대로 예측하지 않는다.
- 대조하는 값은 `commands_sha256`(64자리)뿐이다.

## RV1-6. 7.2 계열 판정과 적용 범위 (질문 6, 덧붙임 발견 1건)

- **계열 표**: python-expert가 H-1·H-3·H-4·H-6~H-10의 모든 작업 키를 세 계열(강체 / 패치·처방 침하 / 균일 연약) 가운데 하나로 나눈 표를 실행 전에 만든다. 분류는 문자열 추측이 아니라 그 러너가 그 키로 만드는 지면 정의(바탕 토양, 패치 토양·다리, 처방 침하)에서 읽는다. 표의 sha256을 첫 본 실행 전에 기록하고 11.1 겹침 표와 함께 실행 전 감사가 본다.
- 원판 7.2 "균일 연약 지면 계열" = 계열 표의 균일 연약(바탕이 연약 토양이고 패치·처방 침하가 없음)이다.
- **표가 나누지 못한 키는 균일 연약으로 다룬다.** 그 키의 K1 막힘은 S-6(멈추고 묻는다)이다. "family unresolved"로 판정을 계속하지 않는다.
- 경로 2는 이 표를 쓰지 않고 원 규칙의 정의 문장과 키·지면 기록으로 따로 나눈다. 두 경로 분류가 다르면 그 줄은 원판 9.2대로 `판정 불가`(S-13)다.
- **덧붙임(발견)**: `resume_k1` 블록의 `applicable`이 거짓인 실행(C2 설정이 없는 IND·IND_LAS)은 K1 관문이 없으므로 원판 7.2 분류와 4.2 기록 확인의 대상이 아니다. 그 줄은 "해당 없음"으로 적고 원판 7.2 끝 문장(키 없음 = `판정 불가`)을 적용하지 않는다. ABL(`ABL_LAS_K1`)은 대상이다.

## RV1-7. 7.4 `F<F_min` 시간의 두 경로 (질문 7)

- 7.4 기록 항목 가운데 `F<F_min` 시간과 `F<F_min+2 kN` 시간은 `result.json`에 없다. 이 두 값은 **경로 1도 `step_series.npz`(1 ms 참 실린더 힘)에서 P5r4 판정서 8.2 표와 같은 정의로 계산한다.** 원판 9.1 C-8 행의 경로 1 입력에 이 두 값에 한해 `step_series.npz`를 더한다.
- 경로 2는 원판대로 따로 계산한다. 두 값은 기록 항목이며 멈춤(S-9)은 `result.json`의 다리별 `F_min_after_N` 최소 `m`으로만 정한다(원판 7.4 그대로).

## RV1-8. H-4 IND_LAS 단계의 인자 (질문 8)

- H-4의 IND_LAS 단계 argv는 같은 묶음(wide 또는 main)의 C2·ABL·IND 단계 argv와 `--controllers`·`--out`만 다르다. wide의 `--cases wide --official --ids-from rev84/fin2_b5_wide_official.json --pad B`는 원판 3절 "293사례 중 패드 B 226"을 만드는 원 명령 꼴이다(`--pad B`가 없으면 293). main은 `--pad` 없이 16사례다.
- 확인: IND_LAS의 키 집합 = IND의 키 집합 = 242(u3_u6 rev2 3절 G-1).

## RV1-9. `OUTRIGGER_LOC_SHADOW` 확인 방법 (질문 9)

- 하네스 줄에는 env 기록이 없다. 원판 4.2의 이 env 금지는 하네스에서 다음 두 가지로 확인한다.
  1. 단계 파일(`steps_*.json`)의 `env`와 러너 시작 env 기록에 이 이름이 없다.
  2. `git_at_start`에서 436.8 하네스 러너가 부르는 모듈 가운데 `loc_anchor_shadow`를 import하거나 `install`을 부르는 것이 없다(python-expert가 11.1 겹침 표에 import 경로 점검 결과를 적는다). 그림자 훅은 `install()`을 부르는 러너(`hsh_run.py`, `g8_shadow.py`, `b1_harness.py`)에서만 걸리므로, 이 env가 있어도 436.8 러너에서는 동작하지 않는다.
- Chrono 행은 원판대로 `start_env`와 result.json의 env 기록으로 확인한다.

## RV1-10. 사용자 결정 2026-11-13의 문장화 (질문 10, 결과 전 해석)

a. **L2b·L1-R 태그 확인**: `run_S8C.py`(L2b)와 `run_S6C.py`(L1-R)에 `--expect-controller`와 결과 태그 기록이 들어간다(python-expert 구현). 원판 6절 L2b·L1-R 칸의 "같음"은 `--expect-controller` = 원판 4.1 값이고 결과 기록의 확인이 참이라는 뜻이다. 그 구현 커밋은 `git_at_start` 이전이다(A-5). 구현이 없으면 그 엔진 행을 시작하지 않는다(A-4). L2b·L1-R 행의 argv에는 `--expect-controller <원판 4.1 태그>`가 붙는다(cad-expert 행 생성기). 원판 4.2의 Chrono 금지 목록은 이 인자를 막지 않는다.

b. **C-4 끔 팔의 7.2 분류**: `--las-off` 행은 "LAS 없음"으로 분류한다. LAS-b 키(`liftoff_approach_slow.*`)가 없는 것이 정상이고 결측(9.3)으로 보지 않는다. K1 부분은 원판 7.2 그대로 나눈다(LAS 없음·미작동 / LAS 없음·K1 막힘). 끔 팔에는 비트 앵커가 없으므로 미작동 해시 대조는 하지 않는다. 4.2 기록 확인에서 끔 팔은 `c2_setup.las_off` = true이고 `liftoff_approach_slow` 블록이 없거나 `enable` 거짓이다. 켬 팔은 `c2_setup.las_off`가 없거나 거짓이다.

c. **A-7**: cad-expert의 목록에서 fdown3.5 L1R 스냅숏을 시작 상태로 쓰는 436.8 행이 0이면 A-7은 "해당 없음"이고 스냅숏 재생성을 기다리지 않는다. 0이 아니면 원판 A-7 그대로다.

d. **O-C5 `k` 반올림**: 원판 5.4의 `k_1`, `k_2`, `k_3`은 계산 즉시 Python `round(x, 4)`로 반올림하고, 그 뒤 계산(바닥 각, 다음 `k`, 할선)은 반올림한 값을 쓴다. 첫 축척은 C-8a 0.9179, C-8b 0.8829다. `(0, 1]` 검사도 반올림한 값으로 한다.

e. **`PROBE_DURATION`**: 원판 5.4-1의 "CHECK 끝"은 저장 `phases`의 `touch` 단계 시작 시각(폐루프 시작 기준)으로 읽는다. 저장 A3·A5 모두 4.8 s이므로 `PROBE_DURATION` = **7 s**(두 행 같음)다. cad-expert는 이 근거를 행 `note`에 적는다. 두 배 재실행(5.4-3)은 14 s다.

f. **G-S 전체 길이 행**: 원판 11.2에 다음을 더한다.
   - 엔진 대표 1행씩, L2b(NSC)와 L1-R은 `--duration`을 줄이지 않고 전체 길이로 돈다(러너 `--tag`만 다름). 값은 출력·판정하지 않고, 본 행을 대신하지 않는다. 이 두 행의 G-S는 RV1-10 a의 `--expect-controller` 구현이 `git_at_start`에 들어간 뒤 그 argv로 돈 것만 인정한다. 그 전에 돈 엔진 G-S(2026-11-13, rc 0)는 기록으로만 두고 병합 뒤 다시 돈다.
   - SCM G-S 행은 원판대로 `--duration`만 짧게 돈다. 짧은 실행에서 이탈 뒤에만 생기는 키(예: `p3b.P3-3_leg_force.F_min_after_N`, `controller_meta.liftoff_approach_slow.start_s`)는 G-S 결과에 "조건부 결측"으로 적는다. 그 키는 각 SCM 묶음의 첫 본 행이 끝났을 때, 어떤 판정보다 먼저 존재를 확인한다. 없으면 S-11이다.
   - 열린 루프(C-6·C-7) G-S는 `--duration`이 없는 동작이므로 `--lift-s`만 줄인다.
   - G-S 행은 판정·해시 비교를 하지 않으므로 원판 6절의 풀 조건(`pcore`)에서 빠진다.

g. **C-2 행 수 검사**: C-2의 S-15 대조값은 H-2 출력이 정한 행 수다. 원판 5.2의 "PS-c 0~2"는 **행 수**다. H-2 선별(`d1_selection_rules.md` 111행)은 촉발된 프로파일마다 그 프로파일의 사건 행과 그 다리의 기준 행(`depends_on`)을 넣으므로, 사건 행과 기준 행을 모두 센다(같은 다리 기준 행은 한 번). 같이 검사한다: L2b·SCM 고정 4행 + 기준선 실패 추가 행 0~4(원판 "최대 8") + PS-c 행 0~2 = 합 4~10. **PS-c 행이 2를 넘으면** 합이 10 안이어도 S-15로 멈추고 묻는다. 기준선 실패 추가 행이 4를 넘거나 합이 4~10 밖이어도 S-15다.

h. **시계열 파일 이름**: 원판 9.1·9.2의 `series.npz`는 SCM `level` 행에서 `step_series.npz`(1 ms 참값)와 `r8_series.npz`(10 Hz), L2b·L1-R 행에서 그 러너가 쓰는 `r8_series.npz`·`s8_series.npz`로 읽는다. 열린 루프(C-6·C-7)는 그 동작이 쓰는 `series.npz` 그대로다. `r8_series`는 `r8_series.npz`다.

i. **행정 좌표 명시(판정서 기록 항목)**: 판정서에 다음 한 줄을 적는다. "제어기 행정 입력 `stroke_m` = 기름 부피 좌표(L1 모터 위치 = L2b `s_ref`, 하네스 `plant.sref`), `stroke_corrected_m` = 피스톤, 두 좌표의 용도 구분은 `c2.py` R1 설계 결정이다." 근거는 `stroke_input_review.md` Q3 결정이다. 원판 2절의 "행정은 모터 행정 [m]"은 이 기름 좌표다.

j. **행정 끝 한정과 노출 집계(판정서 기록 항목)**: 판정서 한계 절에 "플랜트에는 피스톤 끝 정지와 신장 끝 쿠션이 없다(쿠션은 판독 678~694.8 mm)."를 한정으로 적는다. 근거는 `end_stop_cushion_model_review.md`다. 그리고 다음을 묶음(하네스 줄·Chrono 행)마다 집계해 기록한다.
   - 최대 행정 ≥ 678 mm인 줄·행 수
   - 최대 행정 ≥ 684.8 mm인 줄·행 수
   - `FAULT_STROKE_END`가 있는 줄·행 수
   - 행정 기준은 `s_ref`(`stroke_m`)와 피스톤(`stroke_corrected_m`) 둘 다 따로 센다. 어떤 묶음의 기록에 한 좌표의 최대값이 없으면 그 좌표 칸에 "기록 없음"과 그 줄·행 수를 적는다. 추가 실행은 하지 않는다.
   - 이 집계는 기록이다. 등급·멈춤에 쓰지 않고, 두 경로가 필요 없다(경로 1 집계 1회, 원판 9.1의 기록 행과 같다). 비교는 7.6 비교 허용(10⁻⁹ m)을 쓴다.

## RV1-11. 원판 7.6·13절에 더하는 것

- 7.6 숫자 표에 더한다(모두 절차 값 또는 기록 기준이고 판정 문턱이 아니다): `PROBE_DURATION` 7 s(RV1-10 e), `k` 소수 넷째 자리(RV1-10 d), 678 mm·684.8 mm(RV1-10 j, 기록 집계 기준, 원본 `end_stop_cushion_model_review.md`), H-10 440·본 묶음 합 9,778(RV1-2).
- 13절 판정서 항목에 더한다:
  12. RV1-2 p3_hash 처리, RV1-3 묶음별 러너·키 원본 sha·H-6↔H-8 VB 해시 같음 기록, RV1-4 저장·새 `t_a`, RV1-5 앵커 대응 결과, RV1-6 계열 표 sha와 미분류 키 수.
  13. 행정 좌표 한 줄(RV1-10 i).
  14. 행정 끝 한정과 노출 집계 표(RV1-10 j).
- 16절 구현 목록에 더한다: python-expert — seedext 키 옵션(RV1-3.2), 격자 env 재구성, H-6·H-7 단계와 RV1-3.3 이름, 정체성 기록 단계, `run_v5.py` overlap 기준 경로 인자(RV1-4), 계열 표(RV1-6), import 경로 점검(RV1-9), 7.4 시간 경로 1 계산(RV1-7), 행정 노출 집계(RV1-10 j). cad-expert — 행 `note`의 `PROBE_DURATION` 근거(RV1-10 e), G-S 조건부 결측 목록(RV1-10 f).

## RV1-12. 바뀐 줄 수 (S-15 대조값)

| 묶음 | 원판 | 이 판 | 이유 |
|---|---|---|---|
| H-10 | 462 | **440** | RV1-2 |
| H-8 | 3,106(파일 1개) | 3,106(파일 4개: 1,503 + 1,503 + 50 + 50) | RV1-3 |
| H-9 | 1,676(파일 1개) | 1,676(`h9_stage1.jsonl` 908 + 격자 `runs[]` 768) | RV1-3 |
| H-6·H-7 | 각 135 | 각 135(키 집합은 저장 dg3와 같음) | RV1-3 |
| 본 묶음 합 | 9,800 | **9,778** | RV1-2 |
| overlap 기준 실행 | (저장 재사용) | 1건, 줄 수에 세지 않음 | RV1-4 |

## 사용자 결정 기록 (결과 전)

| 날짜 | # | 결정 | 반영 |
|---|---|---|---|
| 2026-11-13 | 10-a | L2b·L1-R 러너에 `--expect-controller`·결과 태그 기록 추가 | RV1-10 a |
| 2026-11-13 | 10-b | C-4 끔 팔은 'LAS 없음' 분류 | RV1-10 b |
| 2026-11-13 | 10-c | A-7은 사용 행 0이면 해당 없음 | RV1-10 c |
| 2026-11-13 | 10-d | O-C5 `k` 넷째 자리 반올림 | RV1-10 d |
| 2026-11-13 | 10-e | `PROBE_DURATION` 7 s(CHECK 끝 = touch 시작) | RV1-10 e |
| 2026-11-13 | 10-f | 엔진별 대표 1행 전체 길이 G-S | RV1-10 f |
| 2026-11-13 | 10-g | C-2 PS-c 0~2 검사 | RV1-10 g |
| 2026-11-13 | 10-h | 규칙 문구 `series.npz` → 실제 `step_series.npz`·`r8_series.npz` | RV1-10 h |
| 2026-11-13 | 10-i | 행정 좌표 명시(판정서 기록, `stroke_input_review.md` Q3) | RV1-10 i |
| 2026-11-13 | 10-j | 행정 끝 한정과 노출 집계(판정서 기록, `end_stop_cushion_model_review.md` Q2) | RV1-10 j |
| 2026-11-13 | Q-1 | A안: H-6~H-9는 저장 키 집합 + 저장소 러너, `LAS_T3_DG3_P3=off`는 H-7에만 | RV1-3 |
| 2026-11-13 | C-2 PS-c | "PS-c 0~2"는 행 수(사건 행 + 기준 행), 2행 초과면 S-15 | RV1-10 g |

## 부록 B. 이 판이 쓰는 저장 파일 (sha256 전체, 2026-11-13 main checkout)

| 파일(`06_analysis/03_hydraulic/coupled/v5/` 아래) | sha256 | 쓰는 곳 |
|---|---|---|
| `d1.jsonl` | `9039b36a1a9c4ba5ed63528bb7384773018d4c7377dccbf76b18fbcfda86707f` | RV1-5 |
| `las/las_T1.jsonl` | `3dee4f6b88e71654debd68b3ef5c5f1a9b01f1dba8fcd731d1355ec219d9a85b` | RV1-5 |
| `las/las_T2.jsonl` | `2fe6a54aafdc0c3ffbf1991907ee4e1af85761e1bef2e25bef07dd52ab199efb` | RV1-5 |
| `las/k1/k1_YP.jsonl` | `0d985d5624f0fbb0219ca50d1c839b7db639011d6c2ab14fa9d84cfd197fc2c3` | RV1-5 |
| `soil_defer/s2d_SC.jsonl` | `70e91ec1234d56a918af1b4fc053c3175f0f14ab41e2b5f334890f7dc6cb08aa` | RV1-5 |
| `overlap_t_a.json` | `39bc75cb3aa0b6678d75e9ce06aac39f34fcb3debff0fa872bf640ac6d7c77ce` | RV1-4(기록만) |
| `main.jsonl` | `9ad749907c34c9e9efb77579a8ab6e3b1f86cdc32d36162c0029005ca545b29e` | RV1-2 |
| `dg3/dg3_v4_on.json` | `5f912ca0d25d6dfe0114e05bf8c7a083fa542ad3de71e76c472e44a1a351167d` | RV1-3 H-6 |
| `dg3/off/dg3_off.json` | `95b81f82d800ae3ccf0dd15e205f12ec4b8795a1dcb482e6e30ed41aa0cfd5ce` | RV1-3 H-7 |
| `noise_vb/r79_VB_L1L2L3.json` | `d3c9bba1abd3c1fbc700a26527856e14f7754740192c55a404bc203ef8a763b9` | RV1-3 H-8 |
| `noise_v0/r79_V0_L1L2L3.json` | `af6a7ae51abe4b9094db9b21cf49f8770861fb0ed91cb269effb6b2cab9b459a` | RV1-3 H-8 |
| `seedext/r79_VB_seedext.json` | `6ddca3d5ce5dc6286c319de13d779bbb419df8fbee2bd13577d04b0f4c2d6f57` | RV1-3 H-8 |
| `seedext/r79_V0_seedext.json` | `f2c01d65238cac50da57c26ca33541b9506ff50b14aee80d65f31e1378dabaa8` | RV1-3 H-8 |
| `grid_vb/grid_r67_main.json` | `8ef4237dc7658559efa04ac07edc1641fe422cbb55e5fee902fbac94eac13ef7` | RV1-3 H-9 |
| `grid_vb/grid_r67_top.json` | `498aa41199b2e4ed3467573c061ab2d6a182ffcd10871fe9bc7420989e6e6412` | RV1-3 H-9 |
| `grid_vb/grid_r69_bottom.json` | `ee84750be278a2c284bf1fe614155240c0a4c2b564762862276a007afc9609e9` | RV1-3 H-9 |
| `grid_vb/grid_r69_top.json` | `c132fd41f13b8033b25804fbc777408a5d1729f31348af34aadd7fd6dfaad325` | RV1-3 H-9 |

- 실행 전에 이 sha256을 다시 확인한다. 다르면 그 묶음을 시작하지 않는다(S-1과 같은 처리).

## 봉인 때 바꿀 머리 줄 (메인 세션)

1. 파일 이름: `v5_resume_4368_rules_rev1_seal_candidate_draft.md` → `v5_resume_4368_rules_rev1.md`(같은 폴더). 초안 파일은 지우지 않고 그대로 둔다.
2. 1행을 다음으로 바꾼다:
   `# v5 재개 검증 436.8 판정 규칙 덧붙임 판 rev1 (구현 질문 해소와 2026-11-13 사용자 결정 문장화, 결과 전, 봉인)`
3. 3행(첫 글머리 "상태")을 다음으로 바꾼다:
   `- **상태: 봉인.** 봉인 값(LF, BOM 없음)과 봉인 시각은 같은 폴더 `v5_resume_4368_rules_rev1.sha256`에 둔다. `.sha256`이 없거나 값이 다르면 실행·판정에 쓰지 않는다(원판 8.2 S-1). 봉인 후보 초안 `v5_resume_4368_rules_rev1_seal_candidate_draft.md`와 1·3·5·8행만 다르다.`
4. 5행("시점")에서 `SEAL_TIME`(예: 2026-11-13 10:00:00 +09:00)과 `SEAL_COMMIT`(봉인 파일을 넣는 커밋의 앞 커밋, 7자리)을 값으로 바꾼다. 이 두 이름 말고는 5행을 바꾸지 않는다.
5. 8행("Q-1 답")을 다음으로 바꾼다:
   `- **Q-1 답(사용자 결정 2026-11-13): A안.** RV1-3이 그 답이다(저장 키 집합 + 저장소 러너, `LAS_T3_DG3_P3=off`는 H-7에만). 봉인본이다.`
6. 바꾼 뒤 sha256을 계산해 `v5_resume_4368_rules_rev1.sha256`에 `<sha256>  v5_resume_4368_rules_rev1.md  sealed <SEAL_TIME 값> (436.8 rev1: implementation questions resolved before results; A-4 list, H-10 440, H-6..H-9 runner/key/output mapping, overlap t_a recomputed, P-1/P-2 anchor mapping, 7.2 family table, user decisions 2026-11-13; thresholds and grades unchanged)` 한 줄로 쓴다.
7. `.gitattributes`에 `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev1.md -text`, `…/v5_resume_4368_rules_rev1.sha256 -text`, `…/v5_resume_4368_rules_rev1_seal_candidate_draft.md -text`를 더한다.
8. `tools/verif/seal_check.py`와 `tools/verif/placeholder_scan.py`(봉인본에 `SEAL_TIME`·`SEAL_COMMIT`이 남지 않음)로 확인한 뒤 커밋한다. 봉인 뒤 이 문서를 고치지 않는다. 고칠 것이 생기면 `v5_resume_4368_rules_rev2.md`로 새로 봉인한다.
