# python-expert: 정오 6 봉인 전 C·D 키 존재 확인 (2026-11-22)

(hand-back 원문 그대로)

## 정오 6 봉인 전 확인 (control 지시 0번): 사례 C·D 기록의 키 존재

**결론: 6-2A "C의 위반 읽기를 D가 덮음"에 필요한 C(VBG4)의 위반 읽기마다의 (시각, 다리)는 두 꼴 모두 기록에 없습니다.** 기준선 221456d와 판 5 ae9d0b2d 출력의 구조는 같습니다.
- C에 있는 것은 다리별 위반 건수와 다리별 **첫** 위반 시각(이동·신장 구간만)뿐입니다. C의 T4h에는 읽기별 jp3 추적 배열이 없습니다(rev 4 실행은 쓰지 않음).
- 따라서 지금 문안대로 봉인하면 6-2A 60행("C 줄 기록에서 위반 읽기의 시각·다리를 얻을 수 없으면 판정 불가로 멈추고, 정오 7로 정의를 정한다")에 바로 걸립니다.
- D(VBG6) T4h에는 `jp3_used_bound_Pa`, `jp3_p_tr_Pa`, 명령 열이 모두 있습니다.
- 값은 열지 않았습니다. 키·배열 이름, shape, dtype만 봤고, 파일은 바꾸지 않았습니다.

### 1. C(VBG4) 위반 읽기의 시각·다리
- **기록 위치**: 기준선 `06_analysis/02_control/j_p3_cause/baseline_221456d/cd.jsonl` 1행(VBG4)과 판 5 `j9_runs/ae9d0b2d/cases_a1/cd.jsonl` 1행(VBG4). 둘 다 `hydraulics_record.extend_bound_check`에 같은 키가 있고, T4h `meta_json.extend_bound_check`에도 같은 이름이 있습니다.
- **있는 키**(모두 다리별 `list[4]`):
  - 이동·신장 구간(`ext_moving`): `reads`, `breach_reads`(건수), `margin_used_reads`, `min_gap_bar`, `min_gap_t_s`, `first_breach_t_s`(그 다리의 첫 위반 시각 하나)
  - 잠긴 뒤(`ext_locked`, ④ 대비): `locked_reads`, `locked_unpaired_reads`, `locked_breach_reads`, `locked_breach_over_tol_reads`, `locked_min_gap_bar`, `locked_min_gap_t_s`, `locked_bound_source`, `locked_tolerance_bar`, `locked_vs_extend_bound_reads`
  - 수축 구간: `retract_reads`, `retract_breach_reads`
  - 출처: `03_src/outrigger_sim/control/extend_start_bound.py:1504-1524`(`_add_moving`·`_add_locked`: 건수와 첫·최소 시각만 갱신), :1536-1549(`_revision_4_record`)
- **없는 것**: 위반 읽기 목록(읽기마다 시각과 다리). 잠긴 구간·수축 구간 위반에는 첫 위반 시각도 없습니다.
- **C의 T4h 배열**(`cd_t4h/R12_bottom-FL-Fs4-o0.0_VBG4.npz`, 두 꼴 같음): `command_m_s`, `head_pressure_Pa`, `rod_pressure_Pa`, `lock_events`, `locked`, `motor_stroke_m`, `phase`, `seal_band_N`, `t_s`, `true_force_N`, `true_force_min_N`, `meta_json`. 모두 (749, 4) 또는 (749,)입니다.
  - `jp3_*` 배열은 없습니다. 출처: `extend_start_bound.py:1532-1534`(`trace_arrays()`는 rev 4 실행에서 None), `04_scripts/04_hydraulic/coupled/verdict_runs.py:260-266`.
  - 판정에 쓰는 ③ 한계 $\hat p+\delta_m$와 ④의 읽기별 값도 기록되지 않습니다.
- **대체 후보**:
  - (a) `first_breach_t_s`와 `breach_reads`만 쓰기
    - 다리마다 위반이 1건 이하이고 위반이 이동·신장 구간뿐일 때만 (시각, 다리)가 완전히 정해집니다. 아니면 판정 불가입니다.
    - 다만 이 조건이 성립하는지는 값을 봐야 알 수 있으므로, 판정 도구가 실행 때 검사해야 합니다.
    - "rev 4 J-P3 위반"에 `locked_breach_*`·`retract_breach_reads`가 포함되는지는 정의(판 4a 5.3 C 행)가 정해야 합니다.
  - (b) D T4h에서 다시 계산하기
    - D의 `jp3_p_tr_Pa`는 C와 같은 플랜트 참값입니다(명령 해시가 같고 플랜트 옵션이 같다는 6-2A 전제가 맞을 때).
    - 그러나 C의 rev 4 한계는 D에 없습니다. D의 `jp3_ext_bound_Pa`·`jp3_model_bound_Pa`는 rev 6 값입니다(R5-9가 $\hat p$를 바꾸고, $M_j$ 형태도 다름). 그래서 C의 위반 읽기와 같다고 보장할 수 없습니다.
    - 쓰려면 "R5-9 전 구간은 같다" 같은 근거를 hydraulics나 control이 정해야 합니다. 권하지 않습니다.
  - (c) 기록 추가(새 실행 커밋의 코드 변경, 명령은 바뀌지 않음)
    - rev 4 `ExtendBoundCheck`에 위반 읽기 목록을 넣습니다. 예: `breach_log` = (t_s, 다리, 구간, gap) 행, 상한 있음. 또는 rev 4 T4h에 읽기별 한계·참값 배열을 둡니다(이름은 `jp3_t_s`와 겹치지 않게).
    - 영향:
      - 명령 해시(P4-1, P5-1, T8)는 그대로입니다.
      - T-JR-10 기록 대조는 `extend_bound_check`를 통째로 빼므로 영향이 없습니다(`jp3_t8_rules.py:13`, :49-56).
      - 기준선 대조의 rev 4 짝은 기준선 쪽에 `jp3_t_s`가 없어 계속 "not_applicable"입니다(`jp3_baseline_compare.py:519-520`).
      - rev 4 줄을 읽는 다른 도구에 새 키가 미치는 영향은 구현 때 점검이 필요합니다.
    - 가장 확실하지만, 기준선 221456d C에는 목록이 없습니다. 같은 새 커밋의 C만 쓰는 6-2A 문안과는 맞습니다.
  - (d) C T4h(명령, 헤드·로드 압력, `locked`, `phase`)로 rev 4 ③ 추적기와 ④를 오프라인에서 다시 만들기
    - 다시 만든 건수와 첫 시각이 기록된 `breach_reads`·`first_breach_t_s`와 같은지 자체 대조하는 조건이 붙습니다.
    - 도구를 새로 만들어야 하고 검증 비용이 큽니다.
- **명세 판단**: 필요합니다. 6-2A를 (a), (c), (d) 가운데 하나로 정하거나, 60행대로 정오 7로 넘깁니다. 위반에 포함할 구간(이동·잠김·수축)도 함께 정해야 합니다.

### 2. D 수치 조건에 쓸 명령 열과 D의 한계 열
- **C(VBG4) T4h 명령**
  - `command_m_s`(749, 4) float64와 `t_s`(749,)가 있습니다(두 꼴 모두).
  - 정의는 "issued leg command of the period"입니다(`03_src/outrigger_sim/contact_episode.py:96`, 쓰는 곳 :662 `series["issued_u"]`).
  - 주의: 작용 명령은 한 주기 뒤의 값입니다(출력 지연 d = 1). 재생 코드는 `acting = _previous(command_m_s, fill=0.0)`로 읽습니다(`03_src/outrigger_sim/control/contact_replay.py:755`). 6-2A "작용 명령"이 낸 명령인지, 한 주기 밀린 작용 명령인지 문안에 적어야 합니다.
- **D(VBG6) T4h 명령**: `command_m_s`(같은 정의), `jp3_u_m_s`(749, 4)가 있습니다. `jp3_u_m_s`는 그 읽기의 분류에 쓴 `commanded` 값입니다(`03_src/outrigger_sim/control/two_pressure.py:2763-2784`). C와 D의 명령 해시가 같으면 같은 수열입니다.
- **u_hold 값**
  - C(rev 4)의 meta `two_pressure_settings.extend_start_bound`에는 `hold_speed_ratio`가 없습니다(rev 4 설정).
  - D의 meta에는 `two_pressure_settings.extend_start_bound.hold_speed_ratio`가 있고, D 행에는 `lock_window_alignment.monitor_stretch_rule.hold_speed_m_s`가 있습니다.
  - 정의는 $u_{hold}$ = `hold_speed_ratio` × v_max입니다(`extend_start_bound.py:498`, 기본 `HOLD_SPEED_RATIO = 0.01` :171, 판별식 :563-576).
  - C에 쓸 u_hold의 출처(D 기록값을 쓸지, 상수 × YAML v_max를 쓸지)를 문안에 적어 주십시오.
- **D(VBG6) T4h의 한계 열**(`cd_t4h/R12_bottom-FL-Fs4-o0.0_VBG6.npz`)
  - `jp3_used_bound_Pa`(749, 4) float64와 `jp3_p_tr_Pa`(749, 4) float64가 **있습니다**.
  - 출처: `extend_start_bound.py:1635-1638`(`PER_LEG_FIELDS`), :1672(`used_bound_Pa` = 감시가 쓴 추정, `p_tr_Pa` = 읽기 때의 플랜트 로드 압력), :1718-1720(T4h 배열 이름).
  - 함께 있는 열: `jp3_t_s`, `jp3_class`·`jp3_class_names`, `jp3_ext_bound_Pa`, `jp3_model_bound_Pa`, `jp3_carry_bound_Pa`, `jp3_plant_state`, `jp3_r58_witness`, `jp3_r59_substeps`, `jp3_r510_candidates`
  - "49.1 s CARRY", "HOLD 간격" 같은 분류 조건은 `jp3_class`로 계산할 수 있습니다.

### 확인 필요 (control, 봉인 전)
1. 6-2A "덮음"의 C 위반 읽기 출처: 지금 기록으로는 정해지지 않습니다. 위 (a)~(d) 중 하나를 정하거나 정오 7로 넘깁니다. 위반에 포함할 구간도 정해야 합니다.
2. "작용 명령"의 시점: 낸 명령(`command_m_s[k]`)인지, 작용 명령(`command_m_s[k-1]`, d = 1)인지.
3. C에 쓸 u_hold의 출처.

### 실행한 검증
- 값을 내지 않는 구조 덤프 스크립트로 키 경로, 배열 이름, shape, dtype만 출력했고, 지정한 낱말로만 검색했습니다. 스크립트와 출력은 지웠습니다.
- 출처 줄은 실행 커밋 ed5-run3의 코드를 Read와 Grep으로 확인했습니다.

사용한 스킬: 없음
