# 436.8 경로 2 — Chrono C-1~C-8 (C-1~C-5 판정 블록 재계산·재집계, C-6·C-7·C-8 값)

- 작성: control-expert(새 인스턴스, 2026-11-13). 이 작성자는 경로 1 도구를 만들거나 고친 적이 없다(아래 "독립성 공개").
- 규칙: 원판 `v5_resume_4368_rules.md`(9019b405), rev1(d9094fda), rev2(497e4614), rev3(dad8dfa6) ~ rev10(62a0bd8d, 우선, 아래 판별 줄). 9.1 표 C-1~C-5 행의 경로 2 = "`series.npz`·`r8_series` 재계산". 입력 파일은 rev3 R3-G2(SCM `step_series.npz`·`r8_series.npz`, L2b `pads.npz`, L1-R `record/record.npz` + `pads.npz`). 담당 범위는 rev2 R2-0 + rev3 R3-G11(C-6·C-7·C-8 추가).
- **rev10(62a0bd8d, 우선, 2026-11-13 반영)**: 봉인 확인 목록에 rev10을 넣었다(raw sha = 코드 봉인 sha = `.sha256` 첫 토막, 다르거나 없으면 S-1, R10-3). R10-1a: 전체 묶음 이름(`V5-RESUME-K1-` 접두어 포함)은 `batch.json` 최상위 `batch` 값이고 폴더 이름의 `batch_`~`_<YYYYmmdd_HHMMSS>` 부분과 대조한다(`p2_chrono.batch_name_of`). 키가 없으면 폴더 이름 부분을 쓴다. 키와 폴더 부분이 다름, 둘 다 정할 수 없음, manifest `batches` 키가 아님 = 묶음 이름 불명. 키는 있는데 폴더 이름이 그 꼴이 아니어서 대조할 수 없는 경우도 불명으로 둔다(경로 2 읽기, 6절 R-5). 짧은 묶음 ID(`C5` 등)는 manifest 키가 아니어서 불명이 된다. R10-1b(`ls_input_case`): 묶음 이름 불명, manifest `batches.<이름>.rows[]`에 같은 case 0개·여럿, `batch.json` `cases[]`에 같은 case 0개·여럿은 LS 판별 판정 불가다. 이전 rev9판은 manifest 행 0개(또는 묶음 없음)이고 `batch.json` 값도 없으면 "LS 아님"으로 읽었다. 이 경우를 판정 불가로 고쳤다. "LS 아님"은 두 출처 모두 그 case가 정확히 한 행이고 둘 다 `v5_setting`이 없거나 None일 때만이다. manifest 파일이 없거나, JSON으로 읽히지 않거나, `batches` 객체가 없으면 입력 오류(종료 2, S-11)다. C-5 `judge`는 rev9판부터 없음을 종료 2로 처리했고, 이번에 JSON 오류·`batches` 없음을 더했다. `gs-load`도 manifest를 필수로 바꿨다(R10-2: G-S가 모든 Chrono 행을 본다). R10-2: `gs-load`가 행마다 `r10`(전체 묶음 이름과 그 근거, manifest 행 수, `batch.json` 항목 수, R10-1b 경우 라벨, `s11`)을 내고, 끝에 `rev10_R10_2_gs_items`(경우별 행 수: 묶음 이름 불명, manifest 0개·여럿, `batch.json` 0개·여럿, 두 출처 값 없음; S-11 행 수; rev10 봉인 상태)를 낸다(값·verdict 없음). `r10`은 열린 루프 C-6C7을 포함한 모든 G-S 행에 대해 적재 전에 만든다.
- **rev9(4cf7843c, 2026-11-13 반영)**: 봉인 확인 목록에 rev9를 넣었다(raw sha = 코드 봉인 sha = `.sha256` 첫 토막, 다르거나 없으면 S-1, R9-8). R9-1: 열린 루프 C-6C7을 뺀 모든 묶음의 모든 행에 `R9-1_expect_controller` 항목을 더했다. SCM `c2_setup.expect_controller.ok`, L2b·L1-R `expect_controller.ok`가 참이 아니면(거짓·키 없음) 그 항목이 S-2 멈춤이다(G-S에서는 S-11로도 센다). J-P3만 판정 불가로 두지 않는다. R9-2: `law_locked` 형식 검사 여섯 항목(1 시간 열, 2 [N, 4]·N = 시간 열 길이, 3 int8, 4 {−1, 0, 1}, 5 인접 Δt 모두 \|Δt − 1 ms\| ≤ 10⁻⁶ s, 6 R9-3 −1 꼴)을 SCM·L2b에 같게 쓰고, 문제마다 항목 부호(`R9-2.1`~`R9-2.6`, 키 없음 = `key`)를 붙인다. R9-3: 첫 무장 전 −1(실행 처음부터, 네 다리가 같은 표본에서 함께 벗어남)만 허용하고 잠김으로 읽는다. 무장 뒤 −1·전 구간 −1·다리별 시점 불일치는 형식 오류다(이전 판의 "무장 뒤 −1 = 판정 불가 + 멈춤" 별도 분기는 없앴다). R9-4: LS 행은 manifest `batches.<묶음>.rows[].v5_setting`과 S9 배치 `batch.json` `cases[]` 같은 case의 `v5_setting`으로만 판별한다(이름 토큰 안 씀, `--manifest` 기본 = `v5_resume_4368/chrono_rows_manifest.json`, C-5 judge에서 manifest가 없으면 종료 2). 둘 다 없음·None = LS 아님, 한쪽만·다름 = 판정 불가(대체 다리 n_late > 0이면 "LS 판별 불가"로 멈춤), LS인데 태그가 ③가 아니면 S-2. 묶음 ID는 `batch.json` `batch`, 없으면 폴더 이름 `batch_<ID>_<stamp>`. R9-5: C-5 행 두 엔진 모두 `law_locked` 키 없음·형식 오류 = J11 판정 불가 + 멈춤(L2b 키 없음 = rev6 R6-B7·rev3 R3-C7 처리를 대체). R9-6: C-5 밖 닫힌 루프 묶음(C-1~C-4, C-8)에 `J11_record`(같은 계산, 멈춤 없음, 결측·형식 오류는 `input_absent`로 셈, `bundle_result.rev9_R9_6_j11_record`)를 더했다. R9-7은 경로 2가 태그를 재계산하지 않으므로 바꿀 것이 없었다(`is_extend_start_tag("final_C4G2_K1")` 거짓, `"final_C4G2_P3_K1"` 참을 시험으로 확인). `gs-load`는 행마다 `r9`(R9-1 확인값·S-2, R9-5 분류, R9-4 LS 분류)와 `law_locked_record.codes`·`pattern`을, 끝에 `rev9_R9_8_gs_items`(R9-1 S-2 수, R9-2 항목별 어긋난 행 수, R9-3 꼴별 수, R9-4 LS 행·판정 불가 수, C-5 S-11 후보 수, R9-6 입력 없음 수, rev9 봉인 상태)를 낸다(값·verdict 없음).
- **rev8(3ecafaaf, 2026-11-13 반영)**: 봉인 확인 목록에 rev8을 넣었다(raw sha = 코드 봉인 sha = `.sha256` 첫 토막, 다르거나 없으면 S-1, R8-4). R8-2: J-P3 적용 범위를 행 태그로 판별한다(원판 4.1 `v5_options.is_extend_start_tag`, rev3 R3-C8). 태그 = argv `--expect-controller`이고 실행 기록의 확인(SCM `c2_setup.expect_controller`, L2b `expect_controller`)이 참이어야 한다. 태그가 서지 않으면 S-2, ③ 요청 기록(argv `--extend-start-tracked`, `v5_hydraulics` 블록이 있으면 `hydraulic_options.extend_start_tracked`도, 키 없음 = 끔)이 태그와 다르면 S-2, 비③ 태그는 해당 없음, ③ 태그에서 `two_pressure.settings.extend_start_rule` 없음은 판정 불가(9.3), `tracked_bound`가 아니면 S-2. R8-3: SCM C-5 J11은 `step_series.npz` `law_locked`(시간축 `t_s`), L2b는 `pads.npz` `law_locked`(`t`)로 개정 6 6절·rev6 R6-B7·rev2 D-1 그대로 판정한다. 형식(R8-3a: [N, 4] int8, 같은 파일 시간축과 행 수 같음, 1 ms, 값 {1, 0, −1})이 틀리면 그 배열을 쓰지 않는다. SCM 키 없음·형식 오류는 J11 판정 불가 + 멈춤(대체 다리 유무와 무관, Q-R8-1 = B)이다. L2b 키 없음은 rev6 R6-B7 그대로다. `gs-load` 출력에 `law_locked_record`(키 있음·형식)와 `jp3_scope`(R8-4 G-S 기록용 범위 분류)를 더했다. R8-1(r79·격자 태그 재계산)은 경로 1 도구 몫이라 바꾸지 않았다(5.0절).
- **rev7(e81f7d31, 2026-11-13 반영)**: 봉인 확인에 rev7을 넣고, 436.8 규칙 파일(원판·rev1~rev7)은 raw sha가 코드의 봉인 sha와 같은 폴더 `.sha256` 첫 토막 둘 다와 같아야 통과한다(R7-7, 없거나 다르면 S-1). R7-4: 판정의 키 결측 처리는 원판 9.3·rev2 R2-2 그대로이고, 켬 팔에서 없어도 되는 `c2_setup.las_off`는 끔이 아닌 것으로 읽는다(끔 팔 = argv `--las-off`, 기록과 다르거나 끔 팔에서 키가 없으면 identity 판정 불가). 팔별 키 있음은 `identity.r7_4_las_keys`에 기록만 한다(키 있음 확인은 경로 1 `gs-check --manifest`). R7-5: L2b·L1-R 행 폴더는 행 로그 `<batch>/<case>.log`의 마지막 `batch wall … -> <폴더>` 줄을 먼저 쓰고(태그 대조), `rows[].folder_method`에 방법을 적는다. C-6·C-7 경로 2는 이 도구(`--bundle C-6C7`, rev3 R3-G11). R7-6: `rows[].placement_record`에 풀·마스크 기록. R7-1·R7-2·R7-3은 하네스·경로 1 몫이라 바꾸지 않았다(5.1절). G-S에서 드러난 J-P3 V0 행 처리도 고쳤다(2절 표).
- **rev5(452a8436)·rev6(809e5639)**: 시각 원점(R6-1: L2b·L1-R `phases`만 상대 → + `start_t_s`, 사건·`fallback_lock_log`·npz는 절대), L1-R D8 t_lift = 첫 10 Hz 행 t_b(t_a 기록, R6-B1), L2b 판정 힘 = S8-A2(`F_cyl_min_interval`, 부상 표본은 `F_cyl_mean_20ms`; R40-2 느린 성분도 같은 힘, R6-B2), 377 창의 LOC = 첫 확정 LOC(최종 LOC로 했을 때 결과는 기록, R6-B3), t_D = 100표본(R6-B4), 이동 압력 = `record.npz` 10 Hz 행의 `u_applied`·`F_cyl`(R6-B5), 실제 대체 다리 = 로그 ∪ 대체 사건(로그에만 있으면 S-11, R6-B7), S-01·02 안전 정지 허용(R6-B8), SGS 부상 = 정지 뒤 패드 법선 ≤ 0(R6-B9), U-S9-G6c `P3-8_preloc_loss` 분기(R6-C3), J11 `fallback_lock_log`(`leg`·`t_start_s`·`window_end_s`, R5-B1)·LS 행 L-e(R5-B3), D2 사유 = `INFO_ROD_PRESSURE_FAULT_REASON:<다리>:<사유>`가 `D2`로 시작(R5-B2), PS-c 순서(R5-B4).
- **rev4(7ea87a30) R4-A2 (사용자 결정 Q-R4-1 = C)**: C-5 J-P3(`hydraulics_record.extend_bound_check.breach_reads`)·J11 창(`pads.npz` `law_locked` + 명령 기록 + `fallback_lock_log`)·D2(사유 D2 대체 사건, `d2_violation_start_ratio`)는 **재계산** 층. C-5 T4-0·T4·T5는 경로 2가 `chrono_t45_replay`를 **직접 실행**(`p2_t45.py`: 도구 파일 f46b5ab 뒤 0커밋 확인, 개정 7 95행 회귀 18행 확인, 출력은 경로 2 폴더, 등급은 `p2_kinds.t45_items`가 따로 적용). PS-c E-1~E-6(재계산)·E-7(연구 A 판정 함수 실행)은 **아직 만들지 않았다**(PS-c 행이 생기면 그 행은 판정 불가). 한계 공개 문장은 rev4 R4-A2 문장을 판정서에 그대로 적는다.
- (이전) **세 층(rev3 R3-G1, 사용자 결정 Q-C1 = A)**: (1) 시계열로 정의가 닫히는 항목은 재계산, (2) 감시기·사건 판정 논리가 필요한 항목(C-5 T4-0·T4·T5·J11 창·J-P3·D2, PS-c E-1~E-4·E-6·E-7)은 `result.json`의 항목별 기록 결과를 **재집계**하고 등급 규칙(FLAG·멈춤·해당 없음)을 경로 2가 따로 적용, (3) 출력의 `bundle_result.TABLE_REAGG`(항목·행 수·출처 키·판정 수)와 `recalculated_judged_items`·`reaggregated_items`. **재집계 항목은 독립 재계산이 아니다**(판정서 한계 절에 rev3 R3-G1 문장을 그대로 적는다).
- 이 도구는 결과의 **판정 값을 입력으로 쓰지 않는다**(재집계 층 제외). 규칙이 이름으로 지정한 입력 키 두 개만 읽는다: `p3b.weight_N`(rev2 R2-5의 W), `p3b_ext.start_condition.crawler_attitude_deg`(원판 9.1 C-8). rev3 R3-G13이 이를 위반 아님으로 정했다.
- C-6·C-7은 `openloop_compare.py`의 `analyse`(함수·상수 정의만 `ast`로 꺼내 그대로 실행, 고정 실행 목록 드라이버는 실행 안 함)이고, 그 함수가 읽는 `p3a`의 저장 판정 복사 키(`stored_*`)는 출력에서 뺀다. 속도비 r_vu·r_v는 rev2 R2-4 식으로 따로 계산한다.
- 행마다 읽은 원 파일 이름과 sha256을 `rows[].input_files_sha256`에 적는다(rev3 R3-G2).

## 1. 실행

dynamics-dev 활성화, PowerShell, E코어(0x00FF0000)로 돌렸다.

```powershell
[System.Diagnostics.Process]::GetCurrentProcess().ProcessorAffinity = [IntPtr]0x00FF0000
$d = "<repo>\06_analysis\02_control\verif_matrix\v5_resume_4368\path2_chrono"
& C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B "$d\p2_chrono.py" seal
& C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B "$d\p2_chrono.py" judge --bundle C-1 `
    --batch <repo>\07_results\S9\batch_V5-RESUME-K1-C1_<stamp>\batch.json --out <출력>\p2_C1.json
& C:\ProgramData\miniforge3\Scripts\conda.exe run -n dynamics-dev python -I -B "$d\test_p2_synthetic.py" --tmp <빈 폴더>
```

- `--bundle`은 `C-1`·`C-2`·`C-3`·`C-4`·`C-5`·`C-6C7`·`C-8`이다.
- `gs-load --batch <G-S batch.json> --out <출력> [--results-root R] [--row-dir CASE=PATH]`: G-S 행(`r4368.role` = `gs`)마다 폴더를 찾고 적재해 그 묶음의 항목 함수를 돌린다. 출력은 폴더·찾은 방법·입력 sha·입력이 없어 판정 불가·기록이 된 항목 이름과 사유·예외·R7-4 팔별 키·R7-6 키 있음·`law_locked_record`(rev8 R8-3a 키 있음·형식·문제 목록)·`jp3_scope`(rev8 R8-2 범위 분류 `applicable`/`not_applicable`/`key_missing_9.3`/`S-2`, 태그, 대조한 요청 기록)·`r9`(rev9 R9-1·R9-4·R9-5 분류)·`r10`(rev10 R10-2)과 끝의 `rev9_R9_8_gs_items`·`rev10_R10_2_gs_items`(G-S 기록 항목 수)뿐이다(값·verdict·묶음 상태 없음, 판정 아님). `--manifest` 기본은 `v5_resume_4368/chrono_rows_manifest.json`이고, 없거나 읽히지 않거나 `batches`가 없으면 종료 2다(rev10 R10-1b). 종료 0 = 모든 행이 예외 없이 돌았음, 1 = 예외 행 있음 또는 G-S 행 0, 2 = 봉인 오류.
- C-5는 먼저 `p2_t45.py <repo(git_at_start checkout)> <07_results> <경로 2 출력 폴더> <C-5 L2b 행 폴더 ...>`로 도구 관문·회귀·재생을 돌리고(종료 0 = 관문·회귀 통과), 그 `t45_path2.json`을 `judge --bundle C-5 ... --aux t45=<경로>`로 넘긴다.
- `judge`는 `batch.json`의 `cases[]` 가운데 `criteria_id`(최상위 또는 `r4368.criteria_id`)가 묶음과 같고 G-S가 아닌 행만 판정한다. 행 폴더(`rows[].folder_method`):
  - SCM: `batch.json` 폴더/`case`(`batch_folder`).
  - L2b·L1-R: 행 로그 `<batch>/<case>.log`의 마지막 `batch wall … -> <러너 폴더>` 줄의 `<러너 폴더>/<argv --only>/`(`case_log`). 러너 폴더 이름에 argv `--tag`가 없으면 종료 2. 그 폴더에 `result.json`이 없으면 결과 루트 아래 같은 상대 경로(`07_results` 뒤, `case_log_relocated`), 그래도 없으면 종료 2.
  - 그 줄이 없으면 `07_results/S8|S6/*<argv --tag>*/<argv --only>/`가 정확히 1개일 때만(`tag_glob`), 아니면 종료 2.
  - `--row-dir CASE=PATH`(`row_dir`)가 모두에 앞선다.
  - 경로 1(R7-5)의 시각 창 방법은 쓰지 않는다. 같은 태그로 G-S를 여러 번 돌린 결과 루트에서는 `tag_glob`가 여러 폴더를 찾으므로(2026-11-13 G-S 배치에서 확인) 행 로그를 먼저 쓴다. 행 로그는 실행 기록이고 경로 1 출력이 아니다.
- 도구 sha(rev10 반영판, 2026-11-13): 공통 4파일 + `p2_t45.py`(`seal`·`gs-load`) `171104adba556a15ddc616de9353e796bed59ed0f50d672045d7953117e95151`(이전 rev9판 `6f229e07…`). 묶음별 `tool_sha256`: C-1 `5fabbcd4…`, C-2 `d21a3ef9…`, C-3 `47426e7a…`, C-4 `76ebc158…`, C-5 `31e6fe46…`, C-6C7 `4a70a76f…`, C-8 `e4a998a1…`. 파일별: `p2_chrono.py` `ade96ef0…`, `p2_rules.py` `f72263b7…`, `p2_core.py` `52be8dff…`(rev9판과 같음), `p2_kinds.py` `561dffec…`, `p2_t45.py` `b56275ba…`(변경 없음), `p2_b_c5.py` `4a5e3536…`(그 밖 묶음 모듈은 바뀌지 않음). 자체 시험 167/167(`--lawlock-record` 포함, 없으면 163/163, 이전 153/153). README·`test_p2_synthetic.py`는 도구 sha에 들지 않는다.
- (이전) rev9 반영판 공통 `6f229e07…`, C-5 `c716c711…`. rev8 반영판 공통 `b4d3c177…`, C-5 `ef2c91cb…`.
- 자체 시험의 `--lawlock-record <SCM 행 폴더>`(선택): 러너 커밋 `7527fc3`으로 만든 짧은 SCM 기록(경로 1 산출물 아님)으로 `step_series.npz` `law_locked` 읽기·형식·J11 계산·전이 수·J-P3 태그 판별을 본다(이 기록의 argv는 result.json에 없어 시험이 ③ VB argv를 준다). 2026-11-13 사용 기록: scratchpad `cad-lawlock\new\LL_new`(3600행, 1 ms, int8, 값 {0, 1}, 다리마다 1→0→1→0→1).
- ③ 판별(원판 4.1)은 이 checkout의 `03_src/outrigger_sim/hydraulics/v5_options.py`를 `03_src`에서 불러와 `is_extend_start_tag`만 부른다(다른 경로에서 불러오면 입력 오류). 이 파일은 제어기 옵션 코드이고 436.8 판정 도구가 아니다. sha는 `seal.recorded`에 기록만 한다.
- 종료: 0 = 묶음 `통과`·`기록 완료`, 1 = `미달`·`판정 불가`·`기록 불완전`·멈춤 있음, 2 = 입력·봉인 오류(S-1), 3 = 내부 오류. 마지막 줄 JSON에 `tool_sha256`(공통 4파일 + 묶음 모듈, 파일별 sha를 이름순 "이름 sha\n"로 이은 문자열의 sha256), `out_sha256`(출력 파일 바이트).
- 봉인 대조(원판 8.2 S-1, rev2 R2-9, rev7 R7-7, rev8 R8-4, rev9 R9-8, rev10 R10-3): 436.8 규칙 원판·rev1~rev10은 raw sha만 보고, 그 sha가 코드의 봉인 sha와 같은 폴더 `.sha256` 첫 토막 둘 다와 같아야 한다(`sidecar_missing`·`sidecar_mismatch`·`mismatch`는 S-1). 부록 A 파일(d1 규칙·rev1, v5 rev6·12·12a·12b, `las_p5r4_k1_judgement.md`)은 raw가 다르면 CRLF→LF 정규화 sha를 보고 같으면 통과 + "CRLF 변환만 다름" 공개. 명세·YAML sha는 기록만.

## 2. 파일과 규칙 절 ↔ 함수

| 파일 | 역할 |
|---|---|
| `p2_rules.py` | 봉인 대조, 문턱 숫자(각 줄에 원문 절), 7.6 비교 허용(`ge`·`lt`·`gt`·`le`) |
| `p2_core.py` | 행 적재(`load_row`), 시각·항목 계산 |
| `p2_kinds.py` | 행 종류별 항목 묶음(D8·P, P3/G6, C-5), 묶음 상태(8.1) |
| `p2_b_c1.py`~`p2_b_c5.py`, `p2_b_c8.py` | 묶음별 행 종류 대응과 기대 행 수 |
| `p2_chrono.py` | CLI |
| `test_p2_synthetic.py` | 합성 입력 자체 시험(실제 결과를 읽지 않음) |

| 규칙 절 | 함수 | 정의(이 도구가 쓴 문장) |
|---|---|---|
| 원판 7.6 | `p2_rules.ge/lt/gt/le` | 비교 허용 10⁻⁹(그 단위) |
| 명세 284 P3-2 t_D, rev2 R2-5 | `p2_core.t_departure` | 폐루프 시작 뒤 크롤러 1 ms 법선 < 0.01 W가 0.1 s 이상 이어지는 첫 구간의 첫 표본. W = `p3b.weight_N` |
| v5 rev6 5 t_lift | `t_lift`, `t_lift_sus` | 단계가 idle·check·touch가 아니고 크롤러 ≤ 0인 첫 1 ms 표본, 1 ms 기록이 없으면 10 Hz 괄호(t_a + 1 ms) |
| 424.8.1 최종 LOC | `loc_times` | 뒤에 `INFO_LOC_REVOKED`가 없는 마지막 `crawler_liftoff_confirmed` |
| P3-1 + U-S9-G6d + 423.3 Q-G | `recontacts`, `classify_recontact`, `p3_1` | t_D 뒤 ≥ 0.01 W 구간을 사건으로. 최종 LOC 이전 시작: 지속 ≤ 0.5 s ∧ LOC 전 종료 ∧ 최대 ≤ 0.15 W → transient FLAG. LOC 뒤: 시작 ≤ LOC + 1.0 s ∧ 지속 ≤ 0.1 s ∧ 최대 ≤ 1.2 × 0.01 W → chatter FLAG. READY 뒤 시작·LOC 없음 → 엄격 실패. READY ~ +10 s 크롤러 최대 > 0 → 실패, 창이 안 차면 판정 불가 |
| P3-2 + 419.8/419.8.1 + 424.8.1 | `p3_2`, `reapproach_intervals` | 최종 LOC 존재 ∧ 첫 DONE 전 ∧ (t_LOC − 0.1, t_LOC] 크롤러 최대 < 0.01 W ∧ t_LOC − t_D ≤ T_lim. T_lim = 0.010/(0.25 v_max) + 1.0 s(YAML v_max, 규칙 표기 2.9 s는 기록). 시간만 넘으면 419.8 다섯 조건(창 재시작 포함 재접근, 재접근 끝 기준 지연, 거짓 LOC 아님, P3-3·FAULT 0, 순서) 또는 424.8.1 다섯 조건 + 조건 6(424.9: t_LOC_fin − t_off ≤ (1 + n_revoke) T_lim, rev3 R3-G12)이 모두 참일 때 FLAG. 취소된 LOC의 하중 중 확정은 기록만(R3-G10 Q-17) |
| P3-3 | `p3_3`, `min_force_after` | [t_D, 끝] 다리별 1 ms 참 F_cyl 최소 ≥ F_min(YAML) |
| P3-4 + 284.1 + 433.6, rev3 R3-G7·G9 | `creep_stop_times`, `p3_4` | 1.0 s 후향 침하 속도(`pad_sinkage_geometric_m` 차분) \|v\| < 0.1 mm/s 네 패드가 끝까지 이어지는 마지막 구간 시작, 없으면 부호 판정 + `creep_vibration_suspect`. 창 = [max(그 시각, 마지막 READY 진입), 끝], 창 안 \|roll\|·\|pitch\| 최대 ≤ 0.2°(장착 몫 더하지 않음). 창 < 5 s → `window_short` FLAG(항목 집계는 통과 아님 `item_tally`, 행 등급은 실패 아님) |
| P3-5 | `p3_5` | 첫 READY ~ 끝 `s9_rows.rut_clearance_m` 최소 ≥ 25 mm, 실행 전체 `s_motor_m` 최대 ≤ 0.6848 m |
| P3-6, d1 rev1 | `ready_item` | 첫 READY 진입 − 폐루프 시작 ≤ 한계 |
| P3-8 + 377 | `p3_8` | min(첫 LOC, 토양 모드 시작) 전 `leg_reapproach_start`·`relevel_predicted`·`probe_aborted_low_load` 0. G6 행만 377 강등: 시작 다리 [시작, 첫 LOC + 1 s] 최소 ≥ F_min(rev3 R3-G8) ∧ FAULT 0이면 FLAG |
| P3-9 | `p3_9` | 기록: `leg_reapproach_deferred`마다 보류 다리 [보류, 다음 재접근 시작 + 0.3 s] 최소 |
| G6-6 | `items_p3(g6=True)` | FAULT 0 ∧ READY ≤ 120 s |
| 398.1 SL-1, 427.12.5 SA-4 | `items_p3`, `stop_classification` | `WARN_LIFT_STROKE_LIMITED` → FAULT 0·부상 0·P3-1·P3-3·P3-4 통과면 P3-5 완화. `FAULT_LIFT_STROKE_LIMIT:soil` → SA-4 조건 전부 ∧ 이탈 뒤 정지면 `stroke_limited_stop`(허용 행은 통과), 아니면 실패 |
| 명세 3 항목 2·3·4, d1 11 D8·P | `d8_force`, `d8_end_attitude`, `pressure_item`, `ready_item` | t_lift 뒤 1 ms 최소(L2b·L1-R `F_cyl_min_interval`) ≥ F_min. 마지막 5 s(전부 READY) \|자세 − 목표\| 최대 + 0.02 ≤ 0.2°. 헤드 등가 F_cyl/A_p: 작용 명령 ≠ 0(\|u\| > 10⁻⁹, rev3 R3-G10 Q-13) 표본 ≤ 180 bar, 전 표본 ≤ 350 bar. READY 평지 90 / 경사 120 s. FAULT 0. 이륙 = rev6 t_lift(rev3 R3-G5) |
| 명세 210.2 R40-2, rev3 R3-G6 | `d8_force(rigid_nsc_hold=True)` | L2b 판정 행: 원값 최소 < F_min ∧ 그 시각이 t_lift + 8 s 안 ∧ 같은 8 s의 1 s 중심 이동평균 최소 ≥ F_min + 5 kN(14,414.589 N) → `hold`(행은 판정 불가, 멈춤 "d1 8절 L1 짝으로 풀거나 묻기") |
| rev3 R3-G1 재집계 | `reagg_item`, `reagg_table`, `items_c5`, `p2_b_c2._psc` | `result.json`에서 항목 이름(T4-0·T4·T5·J11·J-P3·D2·E-k와 별칭)인 키를 찾아 그 값(bool, 또는 `verdict`·`status`·`result`·`passed`·`ok`·`pass`)을 pass/fail/flag로 읽는다. 못 찾거나 못 읽으면 판정 불가. 등급 규칙: T4-0 실패 → 도구 결함 멈춤, T4·T5 실패 → H-7, J-P3는 `two_pressure.extend_start_rule` = `tracked_bound`(③ 켬) 행만, J11은 `fallback_lock_log`가 비면 `not_computed` 기록(rev3 R3-C7), 있으면 재집계하고 실패 → H-7 |
| rev2 R2-4, 원판 5.3·9.1 | `p2_b_c67` | `analyse` 그대로 + r_vu·r_v. 명세 11047 FLAG = 이륙 전 최소 < F_min |
| 원판 4.2·6, rev2 R2-3, rev1 RV1-10 a | `identity_scm`, `identity_l2b` | 기록 확인(어긋나면 판정 불가 + S-2/S-3/S-4 검토) |
| rev7 R7-4, rev2 R2-2, 원판 9.3 | `identity_scm`, `r7_4_las_presence` | 끔 팔 = argv `--las-off`. `c2_setup.las_off`는 켬 팔에서 없어도 끔 아님으로 읽고(결측 아님), 끔 팔에서 없거나 기록이 argv와 다르면 identity 판정 불가. R7-4 표의 팔별 키(`c2_setup.las_off`, `liftoff_approach_slow.start_s`·`end_s`·`end_reason`·`active_periods`·`ramp`·`ramp.periods_applied`) 있음과 표의 조건은 기록만(`absent_where_required`). 판정의 `start_s` 없음은 R2-2대로 LAS-b 시작 안 함. `p3b.P3-3_leg_force` 두 키는 경로 2가 읽지 않는다(P3-3은 1 ms 시계열로 다시 계산) |
| 436.8 rev8 R8-2, 원판 4.1·6, rev3 R3-C8, v5 rev8 3.2·rev9 3.2 (J-P3 적용 범위) | `jp3_item`, `p2_core.row_tag`, `is_extend_start_tag` | ③ 판별 = 행 태그(argv `--expect-controller`, 확인 `ok` 참, 기록 `name`이 있으면 같아야 함)의 `v5_options.is_extend_start_tag`. 태그가 서지 않음 → S-2. 요청 기록 대조: argv `--extend-start-tracked`, `v5_hydraulics` 블록이 있으면 `hydraulic_options.extend_start_tracked`(키 없음 = 끔)도. 다르면 S-2. 블록이 없으면 argv만. 비③ 태그 → 해당 없음(`extend_start_rule` 없어도 결측 아님). 단 비③ 태그인데 `extend_start_rule` = `tracked_bound`면 태그와 실행 제어기가 다르므로 S-2(경로 2 읽기, 6절 R-2). ③ 태그: `controller_meta.two_pressure.settings.extend_start_rule` 없음 → 판정 불가(9.3), `tracked_bound`가 아님 → S-2, 맞으면 `extend_bound_check.breach_reads` 합 > 0 → 실패 + H-7. rev7판의 `two_pressure.extend_start_rule`(settings 밖) 대체 읽기는 뺐다(R8-2가 settings 키를 지정) |
| 436.8 rev9 R9-2·R9-3·R9-5 (rev8 R8-3·R8-3a 대체), v5 rev6 6, rev6 R6-B7, rev2 D-1, rev5 R5-B1 (J11) | `j11_item`, `p2_core.law_locked_check`, `law_locked_pattern`, `law_lock_view` | 잠금 상태: SCM `step_series.npz` `law_locked`(시간 열 `t_s`), L2b `pads.npz` `law_locked`(`t`). R9-2 형식(두 엔진 같음): 1 시간 열 있음, 2 [N, 4]·N = 시간 열 길이, 3 int8, 4 값 ⊂ {−1, 0, 1}, 5 인접 Δt 모두 \|Δt − 10⁻³\| ≤ 10⁻⁶ s(절차 값), 6 R9-3 꼴. R9-3: −1이 없거나, 실행 처음부터 이어지는 −1을 네 다리가 같은 표본에서 함께 벗어나고 그 뒤 −1이 없으면 허용(그 −1 = 잠김). 무장 뒤 −1(`after_arming`)·전 구간 −1(`whole_run`)·다리별 시점 불일치(`per_leg_mismatch`)는 형식 오류. R9-5: C-5 행에서 키 없음·형식 오류 → 배열을 쓰지 않고 J11 판정 불가 + 멈춤(SCM·L2b, 대체 다리 유무와 무관). 창 끝·짝짓기·늦음은 위 P-1 읽기 그대로(t_w + 10⁻⁶ s 뒤 첫 표본이 잠김이 아니면 늦음) |
| 436.8 rev9 R9-4 + rev10 R10-1, rev5 R5-B3 (J11 LS 행) | `ls_classification`, `ls_input_case`, `ls_item`, `manifest_rows`, `batch_case_counts`, `p2_chrono.batch_name_of`·`batch_ctx` | manifest `batches.<전체 묶음 이름>.rows[]` 같은 `case`의 `v5_setting`과 `batch.json` `cases[].v5_setting`. 묶음 이름 불명·manifest 행 0개/여럿·`batch.json` 항목 0개/여럿 → 판정 불가(R10-1b). 두 출처 모두 한 행: 같고 ∈ LS1~LS4 → LS(n_late > 0 = L-e), 같고 그 밖 → LS 아님(H-7), 둘 다 값 없음·None → LS 아님, 한쪽만·다름 → 판정 불가(`LS_class` indeterminate, n_late > 0이면 "LS 판별 불가" 멈춤). LS인데 태그 비③ → S-2. C-5 행에서만 씀 |
| 436.8 rev9 R9-1 (원판 6 태그 칸, 8.2 S-2) | `expect_item`, `p2_chrono.augment_items` | C-6C7을 뺀 모든 묶음 행: `c2_setup.expect_controller.ok`(SCM) / `expect_controller.ok`(L2b·L1-R)가 참이 아님(거짓·키 없음) → S-2 멈춤(G-S S-11) |
| 436.8 rev9 R9-6 (C-5 밖 J11) | `j11_record_item`, `p2_chrono.r9_6_summary` | C-1~C-4·C-8 행: `j11_item`과 같은 계산을 기록만(`verdict` = record, `stop` 없음, C-5였다면의 멈춤 문구는 `c5_stop_would_be_record`), `law_locked` 결측·형식 오류는 `input_absent`로 셈 |
| rev7 R7-6, 원판 6 풀 | `p2_chrono.placement_record` | 행마다 `placement_record`: 배치 행 `pool`·`planned_pool`·`placement_applied`, result.json `placement.affinity_mask_process`·`affinity_mask_ok`·`power_throttling_off_ok`, batch.json `affinity_masks`, `r4368.arm`. 기록만(등급에 넣지 않음). `affinity_mask_ok` 거짓, `pool` ≠ `planned_pool`, `r4368.arm`과 argv `--las-off` 불일치는 `notes`에 적는다 |
| 원판 7.2, rev2 R2-1·R2-2 | `k1_classification` | 기록 모순(`would_block`∧¬due, `applied`∧¬due, `applied`∧`would_block`) → S-5. `_SKIPPED:order` 수 ≠ 막힘 수 → S-5 |
| v5 rev6 5 H-9 | `items_c5` | M2 켬(`v5_hydraulics.hydraulic_options.m2_law`) 행에서 `hydraulics_record.m2_clip_times_s` 중 t_lift 뒤 잘림 > 0 → H-9 멈춤 |
| v5 rev6 6, rev8 R8-3 (기록) | `items_c5` | `law_locked` 잠김↔이동 전이 수(SCM·L2b, 첫 무장 전 −1 = 잠김), 첫 무장 뒤 −1 표본 수 |
| 원판 7.4, rev2 R2-5·R2-6 | `p2_b_c8.judge_row`, `p2_b_c4` | m = t ≥ t_D 다리별 최소의 네 다리 최소 → 멈춤 / 여유 기록 / 기록. F<F_min·F<F_min+2 kN 시간 = [t_D, t_D + 8 s] 표본 수 × 1 ms(끝까지 창은 기록) |

## 3. 묶음별 대응

| 묶음 | 행 | 판정 항목(경로 2) | 등급에 넣는 항목 |
|---|---|---|---|
| C-1 | C2-01·02·04·05·06·08 L2b | D8·P | F·끝 자세·READY·압력·FAULT 0·기록 확인·K1 분류 |
| C-1 | C1-09~12 L1-R | D8·P(기록) | 기록 행 |
| C-2 | C2-03·07 L2b / S-01·02 SCM / 기준선 추가 / PS-c | D8·P / P3 + READY 120 s + `stroke_limited_stop` 허용 / 같은 계열 / E-5만 | 고정 4행 정확히 1번씩(rev2 R2-8), 추가 ≤ 4, PS-c ≤ 2, 합 4~10 |
| C-3 | S-03·04 SCM | P3 + G6(P3-6 90 s는 기록) | 2행 |
| C-4 | 4행 SCM 혼합 | D8 + G6 + P3-3 + R_c + 8 s 창 시간 + K1(끔 팔 'LAS 없음') | 기록 묶음 |
| C-5 | 35행 | 재계산: t_lift·H-9, J-P3(436.8 rev8 R8-2, 태그 ③ 행), J11 창(실제 대체 다리, rev2 D-1, SCM `step_series.npz`·L2b `pads.npz` `law_locked`, rev9 R9-2·R9-3·R9-5), LS 분류(rev9 R9-4, `rev9_R9_4_ls`), D2(기록), K1, R9-1. 도구 실행: T4-0·T4·T5(L2b 행만, SCM은 해당 없음). 묶음 문구 개정 6 4.6(`rev6_4_6_phrase`) | H-9, K1, J-P3, J11 창, T4-0·T4·T5, R9-1 |
| C-6C7 (`--bundle C-6C7`) | C-6 1 + C-7a 1 + C-7b 1 | `analyse` 값, 명세 11047 FLAG, r_vu·r_v | 기록 묶음(rev3 R3-G11) |
| C-8 | O-C5 2행 | 7.4 m·처리 칸·시간·R_c | 기록 묶음(rev3 R3-G11) |

## 4. 읽은 것 (원판 9.2, 1.2절 꼴)

- 규칙: 원판 전체, rev1 전체, rev2 전체(코디네이터 통지 뒤, master `b33e686`), rev3 1~32행·360~553행(R3-F·R3-G·결정 표, master `9ce2fdc`), `d1_selection_rules.md` 1~64행·145~204행, `d1_selection_rules_rev1.md` 전체, `v5_criteria_rev6.md` 81~200행 + T4·T5·J11 줄 grep, `v5_criteria_rev12.md` 전체, `v5_criteria_rev12a.md` 60~105행, `v5_criteria_rev12b.md` 15~47행.
- 명세 `00_docs/04_control/s6_control_spec.md`(sha `1924ae89…`): 300~345행(S6 항목 1~8), 11010~11075행(284·284.1), 14278~14300행(377), 14795~14812행·15138~15165행(423.3), 15340~15360행(424.8.1), 16940~16975행(419.8), 17246~17270행(426.3), 15420~15435행(424.9 조건 6), 그리고 grep 결과 줄(D8, 180 bar, 마지막 5 s, 8 s 규칙 210.2, chatter, `window_short`·433.6, `stroke_limited_stop`, 427.12, 17279·17475 줄 등).
- rev5 89~119행·140~156행, rev6 25~183행(master 병합 `825159f`). 제어기 코드 `03_src/outrigger_sim/control/two_pressure.py`의 `window_end_s` 대입부(2525~2562행, `_open_lock_stretch` 창 식). 제어기 코드이고 판정 도구가 아니다. G-S L2b 행 `controller_meta.two_pressure`와 `settings`·`extend_bound_check`의 키 이름(값 없음).
- rev4 전체(master `136b455`), v5 rev7 1~130행, rev8 40~75행, rev9 45~67행, rev2 72행(D-1). `chrono_t45_replay.py`의 docstring(1~60행)·`summary`·`rev7_summary`·`report_of`·`parse_args`·`main`·`replay_case` 행 키(R4-A2가 실행을 지정한 도구, 436.8 경로 1 도구 아님). 회귀용 저장 3단계 L2b 18행 폴더 이름(`07_results/S8/v5s3_*`).
- `06_analysis/03_hydraulic/coupled/v5/paper_runs/scripts/openloop_compare.py` 전체(R3-G11이 지정한 기존 분석 정의, 436.8 경로 1 도구 아님). G-S 열린 루프 행 `GS_P3a_G1_B_VB_prop_lift10`의 `flow_series.npz` 열 이름과 `series.npz` 배열 이름, `result.json` 키 이름 검색(T4·T5·J11·J-P3·D2 등, 값 없음).
- YAML `02_params/rexome33.yaml`의 `head_area_m2`, `max_speed_m_s`, `F_min_cylinder_N` 줄.
- 원 데이터(키 이름·형식 확인, G-S 배치만): `batch_V5-RESUME-K1-GS_20261113_010654`(두 행), `_012403`·`_020211`의 `batch.json`, `07_results/S8/r4368gs_D1C2_middle_fdown3.2_Fs4_20261113_020211/`, `07_results/S6/bundleC_d1c1_r4368gs_D1C1_top_flat_crx3_L1R_20261113_020211/`. 읽은 것: npz 배열 이름·모양, `result.json` 키 트리(값은 기록 필드만: `phases`, `events`, `settings`, `controller_tag`, `expect_controller`, `pad_record`, `runner`, `s9_rows[0]`, `start_condition` 키 이름, `mass_scale.judgement_weights`, `c2_setup.expect_controller`, `hydraulics_record.m2_*`, `v5_hydraulics.hydraulic_options`, `c2_soil`의 두 키, `args` 일부), `controller_events.json` 형식, 시각 기준(쿼터니언 ↔ `roll_pitch_deg` 차 3×10⁻¹²°, L2b·L1-R 단계·사건 시각 = `settings.start_t_s` 기준 상대). G-S 행으로 적재기·항목 함수가 키 결측 없이 도는지만 봤고 값·판정은 출력하지 않았다.
- rev7 반영(2026-11-13, worktree `292f9d2`): rev7 전체와 `.sha256`, 원판·rev1~rev6 `.sha256` 첫 토막, rev2 R2-2 표(30~44행), 원판 6절 표·9.3, v5 rev8 42·59행 줄과 rev9 1~65행 grep 줄(J-P3 적용 범위). G-S 배치 `07_results/S9/batch_V5-RESUME-K1-GS_20261113_082117`: `batch.json`(키 이름, `cases[]`의 `case`·`criteria_id`·`r4368`·`pool`·`placement_applied`·`argv`), 행 로그 `GS_D1C1_*.log`·`GS_D1C2_*.log` 본문(러너 폴더 줄), L2b·L1-R 러너 폴더 목록, SCM C-5 G-S 세 행의 `controller_meta.two_pressure` 키 이름·`settings` 키 이름과 `v5_hydraulics.hydraulic_options` 값. `gs-load` 출력(값·verdict 없음)만 보았다.
- rev8 반영(2026-11-13, worktree `y4368-p2c`, 9b8c449·7527fc3 병합본): rev8 전체와 `.sha256`. `03_src/outrigger_sim/hydraulics/v5_options.py`의 import 줄과 `switch_base_tag`·`is_extend_start_tag` 정의(원판 4.1이 지정한 판별 함수, 판정 도구 아님). 러너 기록 `cad-lawlock\new\LL_new`(7527fc3, 경로 1 산출물 아님): `step_series.npz` 배열 이름·`law_locked` 모양·자료형·값 집합·전이 시각, `t_s` 간격, `result.json`의 `step_series.law_locked_rule` 문장, `controller_meta.two_pressure` 키 이름과 `settings`의 잠금 창 세 값, `fallback_lock_log`(빈 목록), `c2_setup.expect_controller`, `v5_hydraulics.hydraulic_options`. G-S 배치 `…_082117`은 `gs-load` 출력(값·verdict 없음, `law_locked_record`·`jp3_scope`)만 보았다.
- rev9 반영(2026-11-13, worktree `y4368-p2c`, master `e5a2c19` 병합본 `8a1b903`): rev9 전체와 `.sha256`. `v5_resume_4368/chrono_rows_manifest.json`(R9-4가 판별 입력으로 지정한 공용 행 목록, 경로 1 산출물 아님): 최상위 키, `batches`의 묶음 이름·행 수, `rows[]` 필드 이름, C-5·GS 묶음 행의 `case`·`v5_setting`·`criteria_id`·`controller`. G-S 배치 `…_082117`의 `batch.json` 최상위 키·`batch` 값, `cases[]`의 `case`·`v5_setting`. 배치 `…_094502`는 `batch.json`이 없는 미완 폴더임을 목록으로만 보았다. 이 배치로 `gs-load`를 다시 돌려 R9 기록(값·verdict 없음)만 보았다(5.2절).
- rev10 반영(2026-11-13, master `8b4ad93` 병합본 `6bc1102`): rev10 전체와 `.sha256`. README 5.0절 표기 정정을 위해 `path2_v5c/p2v5c_common.py`의 `P2_V5J_SHA`·`P2_CORE_SHA` 두 줄 위치를 이 브랜치·master·`y4368`에서 grep으로만 보았다(dynamics-expert 경로 2 파일, 경로 1 아님).
- **보지 않은 것**: `resume4368_judge.py`, `u3_judge_k1.py`, `resume_k1_record.py`, `resume_k1_steps.py`, `gs_check_*.txt`, `chrono_rows_check.json`, `chrono_rows_manifest.json`(rev9 반영 전까지. 위 줄의 필드만 rev9 R9-4로 읽음), `run_S9.py`·`run_S8C.py`·`run_S6C.py`·p3b 판정 함수, `result.json`의 `p3b`(위 `weight_N` 1개 제외)·`p3b_ext`(위 1개 키와 `start_condition` 키 이름 제외)·`acceptance`·`h4`·`c2`·`stroke`·`s8_end` 값, `las_p5r4_k1_judgement.md` 본문(sha만), `03_src` 코드.

### 독립성 공개

- 이 작성자는 rev1·rev2를 쓴 control-expert와 같은 에이전트 정의지만 다른 실행이다. 이 실행에서 경로 1 코드·출력은 열지 않았다.
- 에이전트 메모리 색인(`MEMORY.md`, 일반 함정 목록)이 시작 때 문맥에 들어 있었다. 이 프로젝트 경로 1의 코드·값은 들어 있지 않다.
- `d1_selection_rules_interp.md`(부록 A 밖 해석 문서)의 11행 한 줄을 grep 출력으로 보았다("D8 잠김 ≤ 350 bar = 실행 전체 F_cyl/A_p 최대"). 이 도구의 350 bar 정의(전 표본)는 그 줄과 같다. 그 문서의 나머지는 열지 않았다.
- rev1 머리 6행은 "경로 2는 dynamics-expert"라고 적었고, rev2 R2-0이 Chrono C-1~C-5를 새 control-expert 인스턴스로 다시 배정했다(사용자 결정 2026-11-13).

## 5. 만들지 않은 것 · 재집계로 낮춘 것

| 항목 | 처리 |
|---|---|
| C-5 T4-0·T4·T5 | 도구 실행(rev4 R4-A2 c). 감시기 독립 재구현(B안)은 하지 않았다 |
| PS-c E-1~E-6 / E-7 | **미구현**(rev4 b / c). E-5만 재계산. PS-c 행이 H-2에서 생기면 만들어야 한다 |
| C-5 짝 비교(VB↔V0, LS−VB, 시드), 재실행↔저장 비트 비교, 12a 플랜트 선행 | 만들지 않음(기록 항목, 판정 무관) |
| S-01·02 "토양 사건 0.5 s 평균(v5 3.1 ⑦)" | 만들지 않음(원문 미독) |
| D8 LAS-b 설정 9값 대조 | 만들지 않음(프리셋 값이 규칙 문장에 없음) |
| R40-2 보류의 해제(d1 8절 L1 짝 대조) | 자동화하지 않음. 보류 행은 판정 불가 + 멈춤 문구 |

### 5.000 rev10에서 바꾸지 않은 것

| rev10 절 | 이유 |
|---|---|
| R10-3 순서·`git_at_start`·G-S 재실행 | 메인 세션 절차. 이 도구는 봉인 목록에 rev10을 넣고 `gs-load`가 R10-2 항목을 내는 것까지다 |
| 본 실행의 LS 판별 불가 처리 | rev9 R9-4 그대로(늦은 대체 다리가 있으면 "LS 판별 불가"로 멈춤, 없으면 기록). R10-1b의 새 경우는 `LS_class.input.blocking`에 라벨로 남는다 |
| 숫자·등급 | rev10은 새 숫자가 없다 |

### 5.00 rev9에서 바꾸지 않은 것

| rev9 절 | 이유 |
|---|---|
| R9-7 (K1 단독 태그, R8-1c 규칙 3·5) | 태그 재계산(R8-1)은 경로 1 도구 몫이다(R8-1d). 경로 2는 행 태그를 argv `--expect-controller`로 받고 ③만 `v5_options.is_extend_start_tag`로 읽는다. `final_C4G2_K1` → 비③, `final_C4G2_P3_K1` → ③을 시험으로 확인만 했다 |
| R9-8 순서·`git_at_start`·G-S 재실행 | 메인 세션 절차. 이 도구는 봉인 목록에 rev9를 넣고, 최종 Y에서 `gs-load`가 R9-8 기록 항목(`rev9_R9_8_gs_items`)을 내는 것까지다 |
| 숫자 문턱·등급 | rev9 새 숫자는 절차 값 10⁻⁶ s 하나이고, 이 도구는 rev8 때부터 같은 값을 쓰고 있었다(검사 방식만 "증가 확인 + 최대 편차"에서 "모든 Δt가 허용 안"으로 고쳐 비증가 시간 열도 R9-2.5로 셈) |
| T4-0·T4·T5, J-P3 판정 문장 | rev9가 바꾸지 않았다. R9-1 S-2는 J-P3의 rev8 태그 불성립 S-2와 별도 항목으로 겹쳐 나온다(멈춤 사유 둘) |

### 5.0 rev8에서 바꾸지 않은 것

| rev8 절 | 이유 |
|---|---|
| R8-1 (T4h 없는 r79·격자 태그 재계산 대조) | 하네스 r79·격자 기록의 최상위 `controller_tag` 대조이고 R8-1d가 "대조는 경로 1 도구가 한다"고 정했다. Chrono 행 태그는 그대로 argv `--expect-controller`와 확인 `ok`(R8-2도 같은 읽기)로 본다 |
| R8-4 순서 중 `path2_v5c`의 `P2_CORE_SHA` | 그 값은 `path2/p2_4368.py`(dynamics-expert 경로 2) 파일 sha다. 위치는 최종 Y 후보 `y4368`의 `path2_v5c/p2v5c_common.py`의 상수 `P2_V5J_SHA`·`P2_CORE_SHA`이고(줄 번호는 개정마다 바뀌므로 이름으로 적는다), 현재 값은 rev10판 `6e297ea3…`다. 이 README의 앞 판은 "14·43행"이라고 적었는데, 14행은 docstring의 두 이름 언급이고 43행은 갱신 전 판(이 브랜치·master는 아직 42·43행)의 위치라 최종 Y 기준으로는 틀렸다. 이 도구의 파일이 아니므로 이 작성자가 바꿀 것은 없다. 갱신은 `path2`·`path2_v5c` 작성자 몫이다 |
| R8-4 `git_at_start`·G-S 재실행 | 메인 세션 절차. 이 도구는 Y에서 `gs-load`로 `law_locked_record`·`jp3_scope`를 내는 것까지다 |
| 숫자 문턱·등급 | rev8은 새 숫자를 쓰지 않는다(머리 10행). R8-3a "1 ms"의 형식 허용 10⁻⁶ s는 판정 문턱이 아닌 도구 읽기다(6절 R-4) |
| L2b J11 키 없음 | R8-3 정의 4 "L2b 행은 … rev6 R6-B7 그대로". 결측 시 멈춤 문장은 SCM 절에만 있어 L2b는 그대로 두었다(rev9 R9-5가 대체: 지금은 SCM과 같이 판정 불가 + 멈춤) |

### 5.1 rev7에서 바꾸지 않은 것

| rev7 절 | 이유 |
|---|---|
| R7-1a·R7-1b (r79·격자 최상위 태그) | 하네스 r79·격자 기록이고 대조는 경로 1 도구가 한다고 정했다. Chrono 행 태그는 그대로 `--expect-controller`·`expect_controller.ok`(L2b·L1-R)와 `v5_hydraulics.controller_tag`(SCM)로 본다 |
| R7-1c (T-3K R-0 태그 키) | 하네스 T-3K 줄. Chrono 경로 2와 무관 |
| R7-2 (첫 DONE) | r79 하네스 `base` 기록 모양의 규칙. Chrono 첫 DONE은 `phases`(L2b·L1-R은 + `start_t_s`, rev6 R6-1)의 첫 `done`이고, 419.8 조건 5는 이미 엄격 비교(최종 LOC < 첫 DONE − 10⁻⁹, rev3 Q-12, `p3_2`)다. DONE 없음은 조건 참(Q-12) |
| R7-3 (이름 대응표) | 하네스 `d1.g6_preloc`·T-3K 정체성. Chrono 377 창은 rev6 R6-B3(첫 확정 LOC + 1 s) 그대로 |
| R7-5 경로 1 v2 시각 창 | 경로 1 방법. 경로 2는 행 로그 → 태그 검색 순서를 따로 정했다(1절) |
| R7-8 숫자 | ±2 s는 경로 1 절차 값이라 쓰지 않는다. 5 ms는 R7-2 하네스 대조 |

### 5.2 G-S 적재 확인 (판정 아님, 2026-11-13)

- 배치 `07_results/S9/batch_V5-RESUME-K1-GS_20261113_082117`, `gs-load` 종료 0, 12행 예외 0. L2b·L1-R 두 행은 `case_log`로 찾았다(같은 태그 G-S 폴더가 여럿이라 `tag_glob`였으면 종료 2였다).
- 입력이 없어 판정 불가·기록이 된 항목은 10 s G-S 길이 때문(READY·LOC·이륙 없음: P3-1·P3-2·P3-4·P3-5·D8 F·H-9)과 SCM C-5 행의 `pads.npz law_locked` 없음(J11 창은 실제 대체 다리가 없으면 기록, 있으면 판정 불가, rev6 R6-B7 그대로)이다. V0 SCM 행의 J-P3는 이번 수정으로 해당 없음이다.
- 이 배치는 마스크 기록 도입(`e860578`) 전 실행이라 `placement.affinity_mask_*`·`affinity_masks`·`placement_applied`가 없다. `placement_record`는 None으로 적는다.
- rev8판으로 같은 배치를 다시 적재(2026-11-13, `gs-load` 종료 0, 12행 예외 0): SCM C-5 세 행의 `law_locked_record.present` = 거짓이고 J11 사유가 "step_series.npz law_locked missing"이다. 이 배치는 7527fc3 이전 실행이라 예상된 결과다(rev8 R8-4: 기록 추가 이전 G-S는 기록만). L2b 행(`GS_D1C2_…`)의 `pads.npz` `law_locked`는 형식 확인을 통과했다. `jp3_scope`: VB SCM 행 `applicable`(argv·`hydraulic_options` 대조), V0v 행 `not_applicable`(argv·`hydraulic_options`), S6SEED V0 행 `not_applicable`(`v5_hydraulics` 블록 없음 → argv만), S-2 0행.

- rev9판으로 같은 배치를 다시 적재(2026-11-13, `gs-load` 종료 0, 12행 예외 0, 출력 sha `0935be85…`): `rev9_R9_8_gs_items` = R9-1 S-2 0행(11행 모두 `ok` 참, C-6C7은 대상 아님), R9-2 항목별 어긋난 행 `key` 10(C-5 SCM 3 + C-5 밖 SCM 6 + L1-R 1), `R9-2.1`~`R9-2.6` 0, R9-3 꼴 `none` 1(L2b 행), R9-4 LS 0·판정 불가 0(C-5 G-S 세 행 S6SEED·VB·V0v가 manifest·`batch.json`에서 같음), C-5 S-11 후보 3, R9-6 입력 없음 7, rev9 봉인 `match`.

- rev10판으로 같은 배치를 다시 적재(2026-11-13, `gs-load` 종료 0, 12행 예외 0, 출력 sha `9f934a00…`): `rev10_R10_2_gs_items` = 12행 모두 전체 묶음 이름 `V5-RESUME-K1-GS`(`batch` 키 = 폴더 이름 부분), manifest 행과 `batch.json` 항목이 case마다 1개씩, 묶음 이름 불명 0·manifest 0개/여럿 0·`batch.json` 0개/여럿 0, 두 출처 값 없음 1(`GS_D1C1_top_flat_crx3`, L1-R 행), S-11 0행, rev10 봉인 `match`. rev9 항목은 앞 줄과 같다.

## 6. 확인 필요

### 6.00000 rev10 뒤

| # | 곳 | 이 도구의 읽기 | 묻는 것 |
|---|---|---|---|
| R-5 | R10-1a `batch` 키는 있는데 폴더 이름이 `batch_<이름>_<YYYYmmdd_HHMMSS>` 꼴이 아님 | R10-1a는 "키가 폴더 부분과 다름"과 "키 없음 + 폴더 꼴 아님"만 불명으로 적었다. 키가 있어도 폴더로 대조할 수 없으면 "폴더 이름으로 대조"를 할 수 없으므로 불명(판정 불가)으로 둔다 | 이 읽기가 맞는가. 실제 S9 배치 폴더는 늘 그 꼴이라(`s9_batch.py`, R10-0) 본 행에서는 생기지 않을 것으로 본다 |

### 6.0000 rev9 뒤 (R-1 → R9-3, R-3 → R9-2·R9-5, R-4 → R9-2 항목 5로 정해짐)

- 새로 묻는 것 없음. R-2(비③ 태그 + `tracked_bound` = S-2)는 rev9가 다루지 않아 이 도구의 읽기 그대로다.
- 사실 기록: 저장 G-S `…_082117`은 7527fc3 이전 실행이라 SCM 행 `step_series.npz`에 `law_locked`가 없다. 이 도구로 적재하면 C-5 SCM 세 행이 R9-5 S-11 후보, C-5 밖 SCM·L1-R 일곱 행이 R9-6 입력 없음으로 셈해진다(5.2절). rev9 R9-8대로 최종 Y에서 G-S 전체를 다시 돌린 결과가 기준이다.

### 6.000 rev8 뒤 남은 것 (P-3 → R8-2, P-4 → R8-3로 정해짐. R-1·R-3·R-4는 rev9에서 정해짐)

| # | 곳 | 이 도구의 읽기 | 묻는 것 |
|---|---|---|---|
| R-1 | J11 `law_locked` −1 | 개정 6 6절은 "첫 무장 전 −1 = 잠김"만 정한다. 그 다리의 첫 무장 표본 뒤에 −1이 나오면 읽기가 정해지지 않았으므로 J11 판정 불가 + 멈춤으로 둔다 | 무장 뒤 −1이 실제로 생길 수 있는가(러너 쪽 `LAW_LOCK_UNARMED`의 뜻). 생기지 않으면 이 분기는 쓰이지 않는다 |
| R-2 | J-P3 비③ 태그 + `tracked_bound` | R8-2는 ③ 태그 행의 "다른 값 = S-2"만 적었다. 비③ 태그인데 실행 제어기가 `tracked_bound`이면 같은 이유(태그와 실행 제어기 다름, 원판 8.2 S-2)로 S-2로 둔다 | 이 대칭 읽기가 맞는가 |
| R-3 | L2b `law_locked` 형식 오류 | R8-3a 표가 L2b 형식도 정하므로 형식 오류는 SCM과 같이 판정 불가 + 멈춤으로 둔다(키 없음은 rev6 R6-B7 그대로) | 맞는가 |
| R-4 | R8-3a "1 ms" | 시간축 간격이 모두 1 ms ± 10⁻⁶ s가 아니면 형식 오류로 본다(도구 허용값, 판정 문턱 아님). 7527fc3 SCM 기록과 G-S L2b 행은 통과했다 | 없음(기록) |

### 6.00 rev6 뒤 남은 것 (rev7은 P-1·P-2를 다루지 않았다. P-3·P-4는 rev8에서 정해짐)

| # | 곳 | 이 도구의 읽기 | 묻는 것 |
|---|---|---|---|
| P-3 | J-P3 V0 행 | (정해짐: 436.8 rev8 R8-2. 판별은 태그, 두 필드는 대조. 2절 표) | — |
| P-4 | SCM C-5 J11 창 | (정해짐: 436.8 rev8 R8-3·R8-3a, Q-R8-1 = B. SCM `step_series.npz` `law_locked`. 2절 표) | — |

(아래는 rev6 뒤 표 그대로)

| # | 곳 | 이 도구의 읽기 | 묻는 것 |
|---|---|---|---|
| P-1 | J11 창 끝 재계산 | 다리별 발령 명령(`r8_series` `issued_u`)이 0이 아닌 값 뒤 처음 0인 제어 시각 t_s에서 구간이 열리고, u_last = 바로 앞 발령 명령, t_w = t_s + τ_v ln(max(\|u_last\|, ε)/ε) + t_c + T(`two_pressure.settings`의 `lock_window_valve_tau_s`·`lock_window_eps_m_s`·`lock_window_closing_delay_s`; 감시기 docstring의 10.4 ② 식). 로그 항목과 `t_start_s`(반 주기 안)로 짝짓고 `window_end_s`와 10⁻¹² s 대조, 어긋나면 S-11 | t_s·u_last의 기준(발령 명령인지 작용 명령인지)이 맞는가. 맞지 않으면 실제 대체 다리가 있는 첫 행에서 S-11로 드러난다 |
| P-2 | PS-c | E-1~E-7 미구현(R5-B4 순서: PS-c 행이 정해지면 G-S 1행으로 열 확인 → 본 행 전 구현·sha 고정) | 없음(순서대로 진행) |

### 6.0 rev4 뒤 남은 것 (rev5·rev6에서 정해짐: M-1 → R5-B1, M-2 → R5-B2, M-3 → R5-B3, M-4 → R5-B4)

| # | 곳 | 이 도구의 읽기 | 묻는 것 |
|---|---|---|---|
| M-1 | J11 창 끝 | `fallback_lock_log` 항목에서 `leg`와 이름에 `window_end`가 든 키를 읽는다. L2b·L1-R은 `settings.start_t_s`를 더해 절대 시각으로 본다(사건과 같은 상대 시각으로 가정). 키가 없으면 판정 불가 | 로그 항목의 필드 이름과 시각 기준. 비대체 다리의 n_late(기록)는 창 끝 식이 규칙에 없어 계산하지 않았다 |
| M-2 | D2 사유 | 사건 `WARN_ROD_PRESSURE_FALLBACK:<leg>:...`의 세 번째 이후 토막에 `D2`가 있으면 D2 대체로 센다 | 사유가 사건 이름에 어떻게 적히는가 |
| M-3 | J11 LS 행 | n_late > 0은 모두 H-7 멈춤으로 둔다 | 원판 65행 "LS 행은 L-e"를 C-5 LS 행에 적용하는가 |
| M-4 | PS-c | E-1~E-7 미구현 | H-2가 PS-c를 넣으면 만든다(형식 확인 필요: `soil_event_series.npz` 열, 연구 A 판정 함수 호출 꼴) |

### 6.1 rev3 뒤 새로 생긴 것 (rev4에서 정해짐: N-1·N-2 → R4-A2, N-4 → R4-A3)

| # | 곳 | 사실 | 묻는 것 |
|---|---|---|---|
| N-1 | C-5 재집계 입력 | G-S L2b 행 `result.json`의 키 이름 검색(T4·T5·J11·J-P3·D2·`lock_log`·`records` 등)에서 항목별 T4·T5·J-P3·D2 결과 키가 없었다(`controller_meta.two_pressure.fallback_lock_log`, `review_record.d2_violation_start_ratio`, `v5_hydraulics.records`만 있음). 본 행에도 없으면 C-5 재집계 항목은 모두 판정 불가다 | 재집계할 항목별 결과가 `result.json`의 어느 키에 쓰이는가(또는 어느 기록 파일인가). 정해지면 `REAGG_ALIASES`에 출처를 고정한다 |
| N-2 | PS-c 재집계 입력 | E-k 키가 `result.json`에 있는지 확인하지 못했다(PS-c G-S 행 없음) | N-1과 같음 |
| N-3 | C-6·C-7 `analyse` | G-S 열린 루프 행(10 s)에서는 이탈이 없어 `analyse`가 예외로 끝났다(그 함수의 `first_run`이 None). 본 행 길이에서는 나지 않을 것으로 본다 | 없음(기록) |
| N-4 | C-6·C-7 `criteria_id` | G-S에는 `C-6`만 있다. C-7 행의 값(`C-7` / `C-7a` / `C-7b`)을 모두 받는다 | cad 행 생성기의 실제 값 |

### 6.2 rev3 R3-G에서 정해진 앞 질문 (Q-1~Q-18, 기록)

모두 rev3 R3-G1~G13·R3-G10 표대로 반영했다(Q-1 → G1 재집계, Q-2 → G2, Q-3 → G3 허용, Q-4 → G4, Q-5 → G5, Q-6 → G6 F_min + 5 kN, Q-7 → G7 FLAG, Q-8 → G8 F_min, Q-9 → G9, Q-10~Q-14·Q-17 → G10, Q-15 → G11, Q-16 → G12 조건 6, Q-18 → G13). 아래는 원 질문 표(기록)다.

| # | 곳 | 이 도구의 읽기 | 묻는 것 |
|---|---|---|---|
| Q-1 | C-5 9.1 경로 2 | T4·T5·J-P3·D2는 만들지 않아 C-5 행 전부 판정 불가 | C-5 경로 2의 범위(감시기 독립 재구현을 누가 하는가, 또는 경로 2를 t_lift·H-9·전이 기록으로 좁히는가). 그대로면 C-5는 S-13에 준해 판정 불가 |
| Q-2 | RV1-10 h | L2b·L1-R의 1 ms 참 F_cyl·크롤러·자세는 `r8_series`·`s8_series`(10 Hz)에 없어 `pads.npz`(`F_cyl_min_interval`, `F_cyl`, `crawler_normal_N`, `body_quat_wxyz`, `N`, `law_locked`)와 `record/record.npz`(L1-R 자세·크롤러 10 Hz)를 읽었다 | 이 두 파일을 경로 2 입력으로 인정하는가 |
| Q-3 | d1 11 S-03·04 | H-S-A처럼 `stroke_limited_stop` 허용 | S-03·04 행에 허용이 적혀 있지 않다. 허용인가 |
| Q-4 | d1 11 S-03·04 READY | P3-6(90 s)은 기록, G6-6에서 READY ≤ 120 s 판정 | rev1이 H-S-A G1 평지를 90 s로 정했는데 Chrono S-03·04에도 적용하는가 |
| Q-5 | D8 "이륙" | L2b·L1-R·SCM 모두 rev6 5 t_lift(단계 조건 + 크롤러 ≤ 0 첫 표본) | 명세 3 "법선력 합이 0이 된 첫 시각"·P3 t_D 중 무엇인가 |
| Q-6 | R40-2 | 느린 성분 문턱 14.41 kN(문자 그대로), `hold` 행은 판정 불가 | 현 F_min 기준(F_min + 5 kN = 14.415 kN)인가, `hold` 행의 등급은 무엇인가 |
| Q-7 | 433.6 `window_short` | 통과로 세지 않으므로 판정 불가 | d1 3절 "FLAG는 pass"와 충돌. 등급은 무엇인가 |
| Q-8 | 377 강등 문턱 | ≥ F_min(377)과 ≥ 14.4 kN(17279행 "424.11.2와 같음")이 갈리면 판정 불가 | 어느 문턱인가 |
| Q-9 | P3-4 장착 몫 | P3-4는 창 최대 ≤ 0.2°(장착 몫을 더하지 않음, 284.1 `sensor_allowance_left_deg` 식으로 읽음). D8 끝 자세는 + 0.02° | 맞는가 |
| Q-10 | P3-8 구간 | min(첫 LOC(취소된 것 포함), 토양 모드 시작) 전. 둘 다 없으면 실행 전체 | 맞는가 |
| Q-11 | 재접촉 지속 | (마지막 표본 − 첫 표본 + 1 ms) | 표본 수 × 1 ms로 맞는가 |
| Q-12 | P3-2 순서 | DONE이 없으면 순서 조항 참 | 맞는가 |
| Q-13 | 이동 압력 | 작용 명령(발령 `issued_u`가 다음 주기를 구동) \|u\| > 10⁻⁶을 이동으로, 압력 = F_cyl/A_p. 밸브 지연 꼬리는 이동으로 세지 않는다. L2b `head_pressure`·`law_locked`는 쓰지 않는다 | 맞는가 |
| Q-14 | 부상 | t_D 뒤 패드 법선 ≤ 0 표본(SCM `scm_pad_normal_N`, L2b `N`) | 부상 정의 원문 |
| Q-15 | 배정 | C-8은 배정 밖이지만 rev2 R2-5·R2-6을 받아 `p2_b_c8.py`로 더했다. C-6·C-7(R2-4)은 9.1이 경로 2를 `openloop_compare.py analyse`로 정해 만들지 않았다 | C-8을 이 도구로 낼지, C-6·C-7 경로 2 담당 |
| Q-16 | 424.11.2 "조건 1~6" | 424.8.1 다섯 조건만 구현 | 6번째 조건 원문 |
| Q-17 | P3-2 하중 조항 | 최종 LOC 주기만 본다(취소된 LOC는 LOC로 보지 않음, 424.8.1) | 원 표 "크롤러가 하중을 진 동안 LOC 0"을 취소된 LOC에도 적용하는가 |
| Q-18 | rev2 R2-5 W | `p3b.weight_N`을 읽는다(판정 블록 안의 키 1개). `mass_scale.judgement_weights.weight_N`과 다르면 기록 | 판정 블록 키 1개 읽기를 독립성 위반으로 보지 않는가 |
