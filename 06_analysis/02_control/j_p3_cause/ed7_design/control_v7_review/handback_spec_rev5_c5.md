## 개정 5 안의 Q7-C5 채우기 완료

명세 `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\jp3_remedy_spec_v7.md`의 Q7-C5 자리 표시를 채웠습니다. 코드는 고치지 않았고 봉인하지 않았습니다.

- 직전 sha256: `fd550252…`
- **새 sha256: `ebb79469875863e8fae3eb0f7acfbdb99c1abbdb66e2c361452a5d88fbe0a36a`**(848줄)
- 근거: 구현 보고 `ed7_design\tool_b46bdf8f\handback_record_keys.md`(sha256 `33fe6270…`)

### 바뀐 곳
| 위치 | 내용 |
|---|---|
| 머리(인용 기준) | 현재 최신 구현 커밋을 **b46bdf8f**(부모 9d8e78a4)로 적었습니다. a6fc3dd5 줄 인용은 봉인 전에 실행 커밋 기준으로 다시 확인한다고 두었습니다. 남은 빈 곳에서 Q7-C5 줄은 지우고, "새 구현 커밋"은 "실행 커밋(현재 b46bdf8f, 봉인 때 고정)"으로 바꿨습니다. |
| 3.1 기록 목록 (자리 1) | `lsb_record.blind.level_done`: `{t_s, path strict\|relax, twist_load_N}`이고, strict와 relax의 판별 기준과 구현 함수를 적었습니다. |
| 3.1 기록 목록 (계속) | `lsb_record.blind.twist_over_limit`: `{limit_N, entries, periods, episodes[...]}`이고 `entries`가 진입 수입니다. 상한은 `ib_twist_limit_N`이며, 없으면 relax 15 kN을 씁니다. T4h `lsb_ib_twist_load_N`은 10 Hz $D$입니다. 세 기록 모두 A_ib를 켠 실행에서만 생긴다고 적었습니다. |
| 7절 범례 (자리 2) | DONE 경로 열은 `level_done[*].path`, \|D\|>15 열은 `twist_over_limit.entries`에서 읽습니다. 두 열은 b46bdf8f 이후 실행 출력에서 채웁니다. probe 6bfb2560 행의 "†기록 없음"은 그대로 둡니다. |
| 8절 Y7-1 (자리 3) | "구현됨(b46bdf8f)"으로 바꾸고 확인 결과를 적었습니다. P7-0 옛 플랜트 7줄의 해시가 같고, P7-1 VBM R12와 VBM0의 해시가 같고, probe 재현 8 job의 `commands_sha256`이 8/8 같습니다. a2 114행 전체 해시는 봉인 전 P7-3에서 다시 확인합니다. |
| 4.2 결과 | b46bdf8f `FIXED_READING`으로 다시 판정한 결과 `adoption_b46bdf8f.json`도 `decided`, a2 유지입니다. 32 조합은 `interp_grid`에 기록만 했습니다. |
| 6.1 Q7-C4 | b46bdf8f의 시험 고정을 한 줄 더했습니다. `J7_EXEMPT_WARNINGS`에는 강성 경고 하나만 있고, retract WARN은 예외가 아니며 fail로 셉니다. |
| 13절 | Q7-C5를 닫았습니다. |

### 남은 확인 필요
- **채택 도구 맞추기(Y7-5, python-expert)**: 팔 3·4가 둘 다 채택 조건을 만족하는 경우, 도구는 지금도 `undecided`를 냅니다. 명세 4.2의 「팔 3·4 모두 만족 시」 규칙(같은 세 기준으로 둘을 비교하고, 가려지지 않으면 팔 2 유지)에 맞춰야 합니다. 4.2에 이 일이 남아 있다고 적었습니다.

명세 파일과 구현 보고 파일만 읽고 고쳤습니다. Grep은 명세 하나에만 썼고, scratchpad는 쓰지 않았습니다.

사용한 스킬: 없음
