# S-2 토양 모드 시작 유예 규칙 덧붙임 판 rev5 (S 판정 미달·S2D 기각, 남은 19키 정보용 실행)

- 이어받는 판
  - 원판 `s2_soil_defer_rules.md`(`838bd27761b74fdbe6cd5148929d7af0489f63568c2efcebebd57869b4b2ab20`)
  - rev1(`bc95453d7caf1d32408451e6d192cd3467407470202f9ae45999e372058807bd`)
  - rev2(`3768a892b6d34fabc93841d82cf36fbac111f34a8193e1c0ea6046b9ff4a2a04`)
  - rev3(`81bb429dec0ca48de7b188a438b8278d9bb5d0354f18d5874ba3c5c2092b34e8`)
  - rev4(`5eb3f2f3802a087f983b9ce65113becfbcf7c5dffa6540ea34aad1bcaa2967d4`)
- 앞 판들은 고치지 않는다. 이 판과 다르면 이 판이 맞다.
- 작성: control-expert, 2026-11-09
- 사용자 결정(2026-11-09 15시 30분대): 원인 분석 보고의 선택지 2 "S2D 기각 + 남은 19키 정보용 실행"

## RS5-0. 공개와 시간 순서

- **이 판은 사후 판이다.** S-D 결과 106줄과 부분 판정을 본 뒤에 쓴다.
  - S-D 106줄: `v5/soil_defer/s2d_SD.jsonl`, sha256 `16ca4e4f0a30cfff5e5da8445b2d9ddb31299dc43510b80f8cad5d47dd5a5787`
  - S-C 456줄: `v5/soil_defer/s2d_SC.jsonl`, sha256 `70e91ec1234d56a918af1b4fc053c3175f0f14ab41e2b5f334890f7dc6cb08aa`
  - 부분 판정: `judgeS_partial.json`(scratchpad, 15:15), sha256 `2df46281592670ab9005b7ec00465019918e8793c0d1643d53c63e938be09bc0`
  - control-expert 원인 분석: 위 두 jsonl을 읽기 전용으로 읽었다.
- 이 판이 바꾸는 것은 **정보용 실행 범위뿐이다.** 판정 기준(SC-2·SC-F·SC-S·SC-R·SC-T·K), 유예 값($N_d$ 5, $\Delta s_d$ 6 mm, $k_d$ 4), 이미 낸 판정은 바꾸지 않는다.
- 19키의 S2D 결과는 이 판을 쓰는 지금 **0줄이다.** 본 것은 같은 키의 S-C(P0) 줄뿐이다.

## RS5-1. S 판정 확정과 S2D 기각

- S-D는 15:12에 341건 가운데 106줄째에서 SH-8로 멈췄다.
  - SC-2·SC-S 위반 누적이 5짝이었다(아래 표).
  - 같은 시점 checks: SC-2 거짓, SC-S 거짓, SC-F·SC-R·SC-T·K 참.
- **S 판정은 `미달`로 확정한다.** 남은 줄의 결과와 무관하다. 위반은 이미 났고, 기준은 위반 0을 요구한다.
- **S2D는 기각한다.**
  - S2D 단독 채택도, "P5r4 + S2D" 채택도 하지 않는다.
  - A-S(324건), A-P0, Chrono S-Ch는 **하지 않는다.** 그래서 A 판정은 없다(`not_run`).
- **LAS-b 경계 키는 한계로 기록한다.**
  - 키: `D1|H-S-A|G1+J1@FL|T|flat|K1|VB|e0`
  - 현 제어기(LAS-b b0)와 A안 후보 P5r4는 이 키에서 C-S 1짝이 미달이다(A안 rev2 판정서).
  - 이 판에서는 개정 없이 알려진 한계로 둔다.

| SH-8 짝(S2D − P0) | 기준 | 내용 |
|---|---|---|
| `D1\|H-S-0\|J1\|B\|roll-rec\|K1\|V0\|e0` | SC-S | 행정 최대 +1.39 mm |
| `D1\|H-S-0\|J1\|B\|roll-rec\|K1\|V0\|e0.002` | SC-S | +1.38 mm |
| `D1\|H-S-0\|J1\|B\|roll-rec\|K1\|VB\|e0` | SC-S | +1.38 mm |
| `D1\|H-S-0\|J2\|B\|roll-rec\|K1\|V0\|e0.002` | SC-2 | 끝 단계 ready → level |
| `D1\|H-S-0\|J2\|M\|fdown-rec\|K1\|V0\|e0` | SC-2 + SC-S | +12.3 mm, `FAULT_LIFT_STROKE_LIMIT:soil:FL` 새로 발생, READY 소실 |

## RS5-2. 정보용 실행 (묶음 `S-D-info`)

### RS5-2.1 대상 19키

- 정의: 원판 3절 S-D 선택(`s2_defer_judge.sd_selection`, 341키) 가운데 `s2d_SD.jsonl` 106줄에 없는 235키를 본다. 그중 S-C(P0, 그림자 기록 켬) 줄의 `s2d.soil.defer.shadow`가 비어 있지 않은 키가 대상이다.
- 목록(파이썬 기본 문자열 정렬)

```
D1|H-S-0|J2|B|fdown-rec|K1|VB|e0
D1|H-S-0|J2|B|roll-rec|K1|VB|e0
D1|H-S-0|J2|B|roll-rec|K1|VB|e0.002
D1|H-S-0|J2|M|fdown-rec|K1|VB|e0
D1|H-S-0|J2|M|fdown-rec|K1|VB|e0.002
D1|H-S-0|J2|T|fdown-rec|K1|VB|e0
D1|H-S-A|G1+J1@FL|B|flat|K1|V0|e0.002
D1|H-S-C-g|J1|B|fdown-rec|K1|c-mid@FL|dsb_gated_off|V0|e0
D1|H-S-C-g|J1|B|fdown-rec|K1|c-mid@FL|dsb_gated_off|V0|e0.002
D1|H-S-C-g|J1|B|fdown-rec|K1|c-mid@FL|dsb_gated_off|VB|e0
D1|H-S-C-g|J1|B|fdown-rec|K1|c-mid@FL|dsb_gated_off|VB|e0.002
D1|H-S-C-g|J1|M|fdown-rec|K1|c-mid@FL|dsb_gated_off|V0|e0
D1|H-S-C-g|J1|M|fdown-rec|K1|c-mid@FL|dsb_gated_off|V0|e0.002
D1|H-S-C-g|J1|M|fdown-rec|K1|c-mid@FL|dsb_gated_off|VB|e0
D1|H-S-C-g|J1|M|fdown-rec|K1|c-mid@FL|dsb_gated_off|VB|e0.002
D1|H-S-C-g|J1|T|fdown-rec|K1|c-mid@FL|dsb_gated_off|V0|e0
D1|H-S-C-g|J1|T|fdown-rec|K1|c-mid@FL|dsb_gated_off|V0|e0.002
D1|H-S-C-g|J1|T|fdown-rec|K1|c-mid@FL|dsb_gated_off|VB|e0
D1|H-S-C-g|J1|T|fdown-rec|K1|c-mid@FL|dsb_gated_off|VB|e0.002
```

- 목록 sha256: `56a7981738326e6ef37943e90277a220e70771f7683c045b0c6eb995a1102ca7`
  - 계산법: 위 순서대로 각 키 뒤에 LF 하나를 붙인 UTF-8 바이트열(마지막 키 뒤에도 LF)
- 도구는 실행 전에 같은 정의로 목록을 다시 계산해야 한다. 이 목록·sha256과 다르면 실행하지 않는다(SH-4).

### RS5-2.2 돌리지 않는 216키와 근거

- 남은 235키 가운데 216키는 S-C 그림자 진입이 없다.
  - 192키: 토양 모드 시작은 있지만 그림자 진입이 없다. 원판 K-S2에 따라 S2D 줄의 해시가 P0와 같아야 한다.
  - 24키: 토양 모드 시작이 없다(무작위 40키의 나머지). 원판 K-S1에 따라 해시가 같아야 한다.
  - 그래서 이 216키는 SC 기준에서 짝 차이가 날 수 없다. 정보용으로 얻을 것이 없으므로 돌리지 않는다.
- 공개
  - 216키의 K-S1·K-S2는 **실행으로 확인하지 않았다.**
  - 이미 돈 106줄 안의 K-S1·K-S2(그림자 없는 57줄)는 위반 0이었다.
- S-C 그림자 진입 68키 = S-D 106줄 안의 49키 + 이 19키다. 선택 밖 그림자 키는 0이다.

### RS5-2.3 실행·출력

- 설정: 원판 2절 S2D(`mode_defer_periods` 5, `mode_defer_stroke_m` 0.006, `mode_defer_rise_factor` 4.0, `mode_defer_shadow` false). 작업 dict는 S-D와 같다(`d1.jsonl` `job`).
- 출력: main checkout `v5/soil_defer/s2d_SD_info.jsonl`(로컬 전용, git exclude, `-text`)
  - `s2d_SD.jsonl`(106줄)은 **고치지도, 덧붙이지도 않는다.** 실행 전후 sha256이 같아야 한다.
- 짝 기준: 같은 키의 `s2d_SC.jsonl` 줄(P0)이다. S-C 파일 sha256이 RS5-0 값과 다르면 실행하지 않는다(SH-4).
- **판정 불변**
  - 정보용 결과는 S 판정을 바꾸지 않는다.
  - SH-8은 적용하지 않는다. 위반이 몇 짝이 나와도 19키를 끝까지 돈다.
  - SH-6·SH-7도 적용하지 않는다. 묻는 단계가 없다.
- **그대로 적용하는 것**
  - 정체성(SH-4)
    - 한 커밋, 빈 코드 diff, dirty 문서만
    - 도구 sha256
    - 규칙 sha256: 원판~rev4 + **rev5**
  - 제어기 동일성: 정보용 줄의 `c2.py` sha256과 플랜트·하네스 경로 파일 sha256은 S-C·S-D 106줄의 값과 같아야 한다.
    - 현재 `c2.py` = `18f52a6035c89e35e91733c0936972f66ac31e80f99ecf6285a7984f82548199`
    - 바뀌는 것은 실행·판정 도구뿐이어야 한다. 다르면 SH-4다.
  - K-S3′(rev3 RS3-2, rev4 RS4-2 해석 포함)·K-S4·K-S5 비트 대조. 위반이면 SH-3이다. 그 키를 구현 결함 후보로 적고 멈춘다.
  - 실행 오류: SH-5(한 번 다시 돈다)

### RS5-2.4 보고할 것 (정보용, 판정서 부록)

- 짝별 표
  - 키, 유예(시작, 끝 사유, 주기 수)
  - SC-2(위반 항목: verdict, `fail_items`, 단계, 새 FAULT·WARN 이름)
  - SC-S(Δ`d1.stroke_max_m` [mm])
  - READY Δt, LOC 취소 유무, 최종 LOC 시각 차
- 방향을 구분해 센다. 개선(P0 FAULT·미완료 → S2D READY)과 악화를 따로 센다.
- **J2 fdown 계열 FAULT 반복 여부**
  - 대상: `J2|{B,M,T}|fdown-rec` 키
  - 새 `FAULT_LIFT_STROKE_LIMIT` 발생과 소실을 S-D 106줄의 같은 계열과 합쳐 표로 낸다.
- **P0 행정 예산 여유**
  - 19키와 S-D 106줄의 그림자 진입 49키 각각에 대해 682.8 mm − P0 `d1.stroke_max_m`을 적는다.
  - 19키의 P0 여유(실행 전 S-C 값, mm): J2 B fdown VB e0 0.4, J2 M fdown VB e0 13.3, J2 M fdown VB e0.002 0.2, J2 T fdown VB e0 11.6, J2 B roll-rec VB 38.5(두 키), H-S-A 213.8, H-S-C-g J1 fdown 12키 10.1~13.6
- 두 경로: 판정 도구 출력과 control-expert 재집계(jsonl만 읽음)가 개수·수치(1e-9)에서 같아야 확정이다.

## RS5-3. 판정서에 공개할 것

판정서 `s2_soil_defer_judgement.md`에 다음을 적는다.

1. **개선 짝**: `D1|H-S-0|J2|B|fdown-rec|K1|V0|e0`
   - P0 FAULT(행정 가드) → S2D READY, Δ행정 −13.1 mm
   - SC는 악화 쪽만 세므로 위반이 아니다. 효과가 양방향이라는 근거로 적는다.
2. **별도 한계 항목: P0 J2 fdown 행정 예산 여유 0~13 mm**
   - S-C 기준 J2 fdown 그림자 진입 키의 P0 최대 행정은 669.5~682.6 mm다. 여유는 0.2~13.3 mm다.
   - 일부 키는 P0 자체가 SGS 행정 가드로 멈춘다.
   - S2D와 무관한 현 제어기(LAS-b P0)의 한계다. LOC 시각 0.1~2 s 교란에도 경계를 넘는다.
3. **Q-S2 가정 깨짐**
   - S-C 그림자 진입은 토양 모드 키 301개 가운데 68개(22.6 %)로 예측 상한 20 %를 넘었다.
   - 그룹별로 H-S-0 J1 39/68(57 %), H-S-0 J2 16/72(22 %), H-S-C-g 12/20(60 %), H-S-A 1/1이다.
   - "진짜 연약 지면에서는 래치 해제 때 진입 조건이 거짓"이라는 봉인 전 가정(원판 0절·4.2절)은 틀렸다.
4. **원인 분석 요지(control-expert, 사후)**
   - 진입 특징(R, $\bar L/W$)이 경계 키(R 4.01 kN, 1.037)와 J1 토양 키(R 3.11 kN, 1.016)를 가르지 못한다.
   - 유예 중 밀어 올림 하한이 없어 가장 느린 다리 명령이 0~2.3 mm/s가 된다. 그래서 `rise` 만료가 가려진다.
     - P0 궤적 그림자는 26짝에서 2~3주기 `rise`로 끝났다.
     - S2D 실제 유예는 34짝이 `periods`로 끝났다.
   - LOC 시각 교란이 L1gs 취소 → 토양 모드 재시작 사슬을 거쳐 끝 행정을 옮긴다.
   - J2 B roll-rec e0.002의 ready → level은 재레벨 문턱 0.07°를 0.001° 넘은 칼날 사례다(끝 자세 0.027°).
   - 위반 정의는 바꾸지 않았으므로 SC-2 위반으로 남긴다.
5. **지난 실행 전 감사의 기록 3건**
   - (1) RS4-2의 "주기 기록이 없는 줄"은 코드에서는 원판 K-S3로 멈춘다. 규칙보다 엄격한 쪽이다. 이번 S-D 106줄에서 이 경로로 멈춘 줄은 없다.
   - (2) pre-rev4 이관(`history_pre_rev4`)으로 옮긴 S-C 줄은 0줄이다.
   - (3) K-S6(A) 건수: A-S를 돌리지 않으므로 해당 없음.

## RS5-4. 멈춤 조건 정리 (S-D-info)

| # | 적용 | 처리 |
|---|---|---|
| SH-1 | 적용(rev5 포함) | 실행하지 않는다 |
| SH-3 | 적용(K-S3′·K-S4·K-S5) | 멈춘다. 구현 결함 후보 |
| SH-4 | 적용(정체성, 목록 sha256, S-C·S-D 파일 sha256, 제어기 동일성) | 판정 불가, 멈춘다 |
| SH-5 | 적용 | 한 번 다시 돈다 |
| SH-6·SH-7·SH-8 | **적용하지 않음** | 정보용이라 묻지도 멈추지도 않는다 |
| SH-2·SH-9·SH-10 | 이미 통과(S-0 9/9, SH-9·SH-10 pass). 다시 돌지 않는다 | — |
