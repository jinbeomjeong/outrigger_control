# LAS-b P5r4 + K1 재판정 규칙 덧붙임 판 rev1 (LOC 앵커 기록 항목, 결과 전)

- 원판: `las_p5r4_k1_rules.md` sha256 `5ee2bac0451f0ca00139a5a2d238c38d13a6b0f430efc5b44fe0e8b929c2f979`(봉인 2026-11-11 09:29:16 +09:00, 커밋 `d6c65b5`). **원판은 고치지 않는다.** 이 판은 원판에 덧붙인다. 두 판이 다르면 이 판이 맞고, 이 판이 말하지 않는 것은 원판 그대로다.
- 작성: control-expert, 2026-11-11. 기준 master `fc6fa19`.
- **시점: 결과 전.** 이 판을 쓸 때 원판의 대상 행은 0행 실행됐다. 확인한 근거는 두 가지다(2026-11-11 10:25 +09:00).
  - 하네스 출력 폴더 `06_analysis/03_hydraulic/coupled/v5/las/p5r4k1/`(main checkout)가 없다.
  - `07_results/S9/` 아래에 `batch_V5-LAS-P5R4-K1*` 폴더가 없다.
- 계기: LOC 앵커 검토 `06_analysis/02_control/k2/judgement/loc_anchor_review.md`(sha256 `98f7bd6125d8062cb428b89b2a3136e4de2fb67e2c9c30158a3183ea67026e90`, main checkout 미추적 파일) 6절 권고와 사용자 결정(2026-11-11, D-3 (a): 지금 제어기 + 봉인 규칙 그대로 + 결과 전 rev1, 기록 항목만).
- **이 판이 바꾸지 않는 것**: 대상 행·묶음·키 목록, 판정 기준(6.1~6.3)과 문턱, 비트 예측(4.4), 등급·우선순위 규칙(8절·16.6), 멈춤 조건(8.2), 사전 예측(7절). 이 판은 **기록 항목과 FLAG 하나, 판정서 문장 둘**만 더한다.

## RV1-0. 이 판을 쓰려고 본 것 (공개)

- 문서: 원판 전체, `loc_anchor_review.md` 전체, 원판 0절 표의 이어받는 규칙(`las_rev_targeted_rules.md`·rev1, `las_revA_targeted_rules.md`·rev1~rev3, `las_k1_rules.md`·rev1, `las_k1_rules_adopt2.md` 118~342행).
- 코드(읽기만): `c2.py` 1685~1691행(사건 이름 상수 `SOIL_EVENT_CLEARANCE_BIAS`, `SOIL_EVENT_LOC_ANCHOR`), 9306~9346행(`_soil_meta`).
- 저장 결과(값을 읽지 않음, control-expert scratchpad `p5k_path2\struct_paths.py`·`names_only.py`): `k1_YS.jsonl`·`revA_R0A.jsonl`의 필드 이름과 값의 형(type), REM R7 `result.json`·`batch.json`의 필드 이름과 형, 원판 부록 A 기준 파일들의 식별 필드(`rev.key`·`rev.label`·후보 이름·`k1.sub_bundle`·`controller_tag`·`error` 유무·`job` 키 이름), `revA_R0A.jsonl`의 `diag.force_window.columns` 이름 목록, `k1_YS.jsonl`(원판 1.1에 공개된 파일)의 사건 이름별 건수(`event_name_census.py`). 힘·행정·시각·해시 값은 읽지 않았다.
- 확인한 사실: 하네스 줄의 `events`는 경고·고장 사건만 담고 시각이 붙은 LOC·보정 사건은 없다. LOC·보정 사건은 `event_names`(이름별 횟수)에만 있다. 그래서 하네스의 사건 기반 항목은 시각 없이 이름·건수로만 정한다(RV1-1).

## RV1-1. 앵커 기록 항목 (원판 6.4 기록에 더함, 판정 아님)

짝마다 두 팔(ref, cand) 각각에 대해 다음을 기록한다. 하네스 줄(Z-T·Z-S·Z-C의 짝, Z-X ref)과 Chrono 6짝 모두에 적용한다. Z-0·Z-A는 짝이 아니므로 줄마다 같은 항목을 기록만 한다.

| 항목 | 정의 | 하네스 출처 | Chrono 출처 |
|---|---|---|---|
| 보정 경로 `anchor_path` | 사건 이름(`split(":",1)[0]` 정확 일치) 기준. `INFO_CLEARANCE_BIAS`가 1건 이상이면 ①, `INFO_LOC_CLEARANCE_ANCHOR`가 1건 이상이면 ②, 둘 다 있으면 `①+②`, 둘 다 없으면 ③(LOC가 없는 실행 포함) | `event_names`(키의 이름 부분, 횟수 합) | `events[].name` |
| LOC 수 | 사건 `crawler_liftoff_confirmed` 건수 | `event_names` 횟수 합 | `events` 건수 |
| $t_L$ 첫·끝 | 첫·마지막 LOC 확정 시각 | `values.events.t_loc_first_s`·`t_loc_last_s` | 첫·마지막 `crawler_liftoff_confirmed` 사건의 `t_s` |
| $t_P$ 끝 | 실행 끝 토양 meta의 `t_P_s`(마지막 LOC의 S-1 평탄 창 시작, `soil.plateau_start_s`) | `anchor.soil_meta.t_P_s`(RV1-5) | `controller_meta.soil.t_P_s` |
| $t_P$ 첫 | 첫 LOC의 `t_P_s` | `anchor.loc_calls[0].t_P_s`가 있으면 그것, 없으면 `k1.loc_calls[0].t_P_s`, 없으면 LOC가 1건일 때만 $t_P$ 끝 | `order_gate.decisions` 가운데 `t_loc_s` 주기 = 첫 LOC 주기인 항목의 `t_P_s`, 없으면 LOC가 1건일 때만 $t_P$ 끝 |
| raw 보정값 | `bias_corner_raw_m`(4모서리, m, `corner_order` 순서) | `anchor.soil_meta` | `controller_meta.soil` |
| 적용 보정값 | `bias_corner_m`(4모서리, m). 경로 ②이면 `loc_anchor_bias_mm`(다리 순서 mm)도 함께 | `anchor.soil_meta` | `controller_meta.soil` |
| meta 대조 `anchor_meta_agree` | 경로 ② ⇔ `loc_anchor_applied` 참, 그리고 경로 ①·② 가운데 하나라도 있으면 `bias_corner_m`에 0이 아닌 값이 있다 | `anchor.soil_meta` | `controller_meta.soil` |

- 시각은 원판 규약대로 정수 주기 $n=\mathrm{round}(t/0.1)$로 바꿔 함께 적는다($n_P$, $n_L$).
- 토양 meta는 실행 끝 값이다. LOC 취소 뒤 다시 LOC하면 마지막 LOC의 값으로 덮인다. 그래서 첫 LOC의 raw·적용 보정값은 하네스 `anchor.loc_calls`가 있을 때만 기록한다(Chrono는 기록하지 않는다).
- 출처 필드가 없으면 그 항목은 None이고, 짝에 사유 `ANCHOR_RECORD_MISSING`(빠진 필드 이름)을 적는다. **판정 불가로 만들지 않는다**(기록 항목이므로 원판 5.0·8.1의 판정 필드 누락 규칙을 적용하지 않는다).

## RV1-2. FLAG `ANCHOR_SAMPLE_SHIFT`

- 정의: 두 팔 가운데 **하나라도** 보정 경로가 ① 또는 ②(`①+②` 포함)이고, 두 팔에서 같은 자리의 $n_P$가 다른 짝.
  - 비교하는 자리는 "$t_P$ 첫"과 "$t_P$ 끝" 둘이다. 두 팔 모두 값이 있는 자리만 비교한다. 하나라도 다르면 FLAG다.
  - 비교할 자리가 하나도 없으면(어느 팔에서든 두 값이 모두 None) FLAG 값은 None이다. 사유 `ANCHOR_RECORD_MISSING`으로 따로 센다.
  - 두 팔 모두 ③이면 FLAG가 아니다(앵커가 쓰이지 않는다).
- 함께 적는 것: 두 팔의 경로, $\Delta n_P$(cand − ref, 첫·끝), $\Delta n_L$, 두 팔의 raw·적용 보정값.
- 이 FLAG는 등급에 영향을 주지 않는다. 원판 10.2 K-10 비교 대상의 "FLAG 건수"에 들어간다(두 경로가 같은 건수·같은 짝 목록을 내야 한다).

## RV1-3. C-S·P3 위반과 FLAG가 겹친 짝 (판정서 문장)

- 대상
  - 하네스: C-S 위반 짝, P3 위반 짝(원판 6.2).
  - Chrono: CC-S 위반 짝, CC-2 (a) 위반 짝(판정 항목 $I$는 모두 `P3-*` 항목이다).
- 위 위반 짝이 `ANCHOR_SAMPLE_SHIFT`를 가지면 판정 도구는 그 짝을 `anchor_effect_possible` 목록에 넣는다. 판정서에는 그 짝마다 **"앵커 표본 효과 가능"**이라고만 적는다.
- **판정은 규칙대로 둔다.** 위반은 위반이고 등급(`미달`, 원판 SK-5 즉시 확정)과 우선순위(16.6)는 바뀌지 않는다. 이 문장은 사후 해석으로 판정을 바꾸는 근거가 아니다. 채택 여부는 원판대로 사용자가 정한다.
- FLAG가 None(기록 누락)인 위반 짝은 `anchor_effect_unknown` 목록에 넣고 판정서에 "앵커 기록 없음"을 적는다.

## RV1-4. C-S 1 mm 허용의 양자화 민감도 (판정서 문장)

- 판정서의 C-S·CC-S 절에 다음 취지를 적는다.
  - 경로 ①·②에서 보정 $b_k$는 $t_P$ 주기의 행정 평면 $c_k(t_P)$와 그 주기의 원시 기울기로 정해진다(`loc_anchor_review.md` 2절).
  - LOC 꼬리 동안 행정 평면은 주기당 약 1~2 mm 움직인다(G8 FL 10 mm/1.1 s, 같은 문서 6절). 그래서 $t_P$가 한 주기만 바뀌어도 $c_k(t_P)$가 약 1~2 mm 바뀌고, LOC 뒤 heave 목표를 통해 $s_{max}$가 같은 크기로 바뀔 수 있다.
  - 따라서 **C-S 1 mm 허용은 앵커 시각 양자화 자체에 민감하다.** `ANCHOR_SAMPLE_SHIFT` 짝의 C-S 위반은 이 양자화만으로도 날 수 있다.
- 이 문장은 C-S 문턱(0.001 m)과 대상 짝을 바꾸지 않는다.

## RV1-5. 하네스 실행 도구가 줄에 남길 필드 (원판 5.1에 더함)

- 하네스 줄마다 최상위 `anchor` 블록을 남긴다. 판정 도구 두 경로는 이 블록을 읽고, 없으면 RV1-1의 대체 출처를 쓴다.
  - `anchor.soil_meta`: 실행이 끝났을 때 제어기 `controller_meta.soil`(= `_soil_meta()`)에서 다음 키를 그대로 복사한다. `t_P_s`, `t_loc_s`, `bias_corner_raw_m`, `bias_corner_m`, `corner_order`, `loc_anchor_applied`, `loc_anchor_bias_mm`, `clearance_at_P_m`, `clearance_at_loc_m`. 토양 대응이 꺼져 키가 없으면 그 키를 None으로 둔다.
  - `anchor.loc_calls`: LOC 확정 때마다 한 항목, 시간 순서. 항목 키는 `t_loc_s`, `t_P_s`(그 LOC의 `soil.plateau_start_s`), `bias_corner_raw_m`, `bias_corner_m`이다. 값은 그 LOC 확정 주기의 제어기 상태에서 읽는다. LOC가 없으면 빈 목록이다.
- **비트 불변**: 이 기록은 명령을 바꾸지 않아야 한다. 값은 이미 계산된 상태를 읽기만 한다. 원판 비트 예측(4.4)이 그 확인이다.
- Chrono는 새 필드를 요구하지 않는다(`controller_meta.soil`과 `events`가 이미 있다).

## RV1-6. 정체성 기록 (원판 5.1·5.2·9절 K-0에 더함)

- 하네스 줄과 Chrono 행·prelaunch 기록의 규칙 sha256 목록에 이 판(`las_p5r4_k1_rules_rev1.md`)을 더한다. K-0은 원판과 이 판의 `.sha256`을 모두 확인한다.
- 원판 8.2 S-1("이 규칙·0절 표 규칙의 `.sha256`이 없거나 LF sha256이 다름 → 실행하지 않는다")은 이 판에도 적용한다.

## RV1-7. 경로 2 위치 (원판 10.2·11.4의 기록)

- 원판 10.2는 경로 2 스크립트를 "scratchpad"에 둔다고 적었다. 재현을 위해 두 스크립트와 단위 시험을 저장소 `06_analysis/02_control/verif_matrix/p5k_path2/`에 커밋한다(`p5k_recount.py`, `p5k_chrono_recount.py`, `test_p5k_recount.py`). 앞선 경로 2(`k1rem_twopath/recount_rem.py`)와 같은 관례다.
- 결과 전 고정(원판 10.2)은 그대로다. 커밋한 blob sha와 파일 sha256을 메인 세션에 넘기고 prelaunch에 기록한다. 판정 줄을 한 줄이라도 만든 뒤에는 고치지 않는다.
