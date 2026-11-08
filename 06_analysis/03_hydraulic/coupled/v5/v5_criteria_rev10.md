# v5 유압 연성 인수 기준 — 개정 10 (정정: 7.3 검사 ③에 대체 추정 그림자 끝값을 조건부 허용)

작성: control-expert, 2026-11-08.

> **상태: 봉인(2026-11-08).** SHA-256과 봉인 시각은 같은 폴더 `v5_criteria_rev10.sha256`에 있다. 이 파일은 더 고치지 않는다.
> - **결과를 본 뒤의 해석이다.** 개정 8 7.3 Chrono 해시 대조 2행(`E_G4_Fs8`, `S_top_fdown3.5_wika_Fs8`)에서 검사 ①②④⑤는 통과했다. 검사 ③(제어기 meta 차이가 ③ 키뿐)만 `two_pressure.fallback_rod_estimate_Pa` 한 경로 때문에 실패했다. 이 판은 그 결과를 보고 검사 ③의 허용 키를 조건부로 넓힌다.
> - **개정 8 작성 때의 누락이다.** 대체 상한 그림자 값이 ③ 켬에서 바뀌고 실행 끝 상태가 meta에 남는다는 것을 control-expert가 개정 8 7.3 허용 키에 넣지 않았다.
> - 사용자 승인(2026-11-08): 개정 10을 조건 A·B·C로 봉인.

**고치는 판**: 아래 열 판을 순서대로 덮어 읽은 판이다. 앞 판들과 각 `.sha256`은 고치지 않는다. 여기 적지 않은 항목은 앞 판 그대로다.

| 판 | 파일 | SHA-256(앞 16자리) |
|---|---|---|
| 봉인본 | `v5_criteria.md` | `06ed0384fb942cfd` |
| 개정 1 | `v5_criteria_rev1.md` | `cbfac2b2de571500` |
| 개정 2 | `v5_criteria_rev2.md` | `e120474b8ebd721e` |
| 개정 3 | `v5_criteria_rev3.md` | `7084da25c6129681` |
| 개정 4 | `v5_criteria_rev4.md` | `642e96f9cfd20a9c` |
| 개정 5 | `v5_criteria_rev5.md` | `945f714660cd3ec7` |
| 개정 6 | `v5_criteria_rev6.md` | `fd5117031ef460cf` |
| 개정 7 | `v5_criteria_rev7.md` | `9ccde7a5a4128317` |
| 개정 8 | `v5_criteria_rev8.md` | `c6ec89f71c1d8de4` |
| 개정 9 | `v5_criteria_rev9.md` | `3c50dda50ca6dca6` |

규약: 개정 8과 같다(음되먹임, $T_s$ 0.1 s, $d$ = 1, 압력 bar 게이지).

## 1. 바뀌는 항목

| # | 앞 판 위치 | 앞 판 문구 | 새 문구 |
|---|---|---|---|
| 1 | 개정 8 7.3 기대 ③ | `result.json` 제어기 meta 차이가 ③ 키(`extend_start_rule`, `extend_start_revision`, `extend_bound_check` 내용)뿐이다 | ③ 키(`two_pressure.settings.extend_start_rule`, `two_pressure.settings.extend_start_bound`, `two_pressure.extend_start_record`, `extend_bound_check`) **+ `two_pressure.fallback_rod_estimate_Pa`**(대체 추정 그림자의 실행 끝값). 이 마지막 키는 3절 조건 A·B·C를 모두 만족할 때만 허용한다 |

## 2. 근거 (코드, master 3d848a7)

| # | 위치 | 내용 |
|---|---|---|
| 1 | `03_src/outrigger_sim/control/two_pressure.py` 2268~2280 | 대체 상한 $\hat p_r$(`_LegWatch.rod_estimate_Pa`)는 로드 센서 상태와 무관하게 모든 다리에서 매 판독 갱신된다(docstring "used on fallback legs only") |
| 2 | 같은 파일 2792~2799 | ③ 켬이면 신장 이동 추정 = $\max(13\ \text{bar},\ \hat p+\delta_m)$(개정 8 5절 설계 그대로). 잠김 시작값 $M_j$(2590~2593, 2802~2812)와 ④ 상계(2621~)가 이를 이어받는다. revision 4 시드(2312~2320)도 올리기만 한다 |
| 3 | 소비처 전부(grep) | 힘 하한 `_fallback_forces`(2864~2870)는 **대체 다리에서만** 쓴다. `_count_tension`(2372)은 센서 비정상 다리에서만, 기록 전용. CB 경로(2436)는 파일럿 체크 VB에 없다. 그 밖은 meta(1692)뿐 |
| 4 | 결과 | 로드 센서가 실행 내내 정상이면 이 값은 명령에 닿지 않는다. 대체가 생기는 실행에서는 대체 시작부터 하한에 들어간다. 이것이 ③의 의도된 효과다(Dg-3 v4 135키 폐루프 판정, 개정 8 4절). 실제 대체가 있는 Chrono 폐루프가 없다는 남는 위험은 개정 8 4절 그대로다 |

## 3. `fallback_rod_estimate_Pa` 허용 조건 (모두 만족)

| # | 조건 | 이유 |
|---|---|---|
| A | 재실행 전체에서 대체 사건(`WARN_ROD_PRESSURE_FALLBACK`) 0 | 소비처가 대체 다리뿐이므로 명령 무관이 보장된다 |
| B | 검사 ①(배열 비트 동일)·②(사건 동일) 통과 | 명령·사건 불변의 직접 증거 |
| C | 다리마다 재실행 값 ≥ 저장 값 − 1 Pa | ③는 이동 추정·$M_j$·④를 올리기만 한다. 내려가면 ③ 밖의 원인이므로 결함이다 |

- 하나라도 어기면 검사 ③ 실패(개정 8 7.4 "멈춤").
- 하네스 7.2는 `hydraulics_record`만 비교하므로 이 판의 영향이 없다.

## 4. 판정

- 이 판을 적용하면 7.3은 ①②④⑤ 통과, ③은 허용 키만 다르고 A·B·C를 만족하면 통과다. 7.4대로 저장 VB·LS 결과를 `final_C4G2_P3` 결과로 읽는다.
- 도구(`p3_chrono_check.py`)에 A·B·C 확인을 넣는 일은 python-expert에 넘긴다. 그 전까지는 control-expert가 저장·재실행 `result.json`과 사건 파일로 A·B·C를 직접 확인해 판정한다.
