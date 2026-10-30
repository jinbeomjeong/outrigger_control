# docs — 이식 검토 문서

## 최종 제어기 블록 다이어그램 (2026-10-31)

| 파일 | 용도 |
|---|---|
| `controller_block_diagram.graphml` | yEd로 여는 원본(yFiles GraphML). 그룹·라벨을 yEd에서 고칠 수 있다 |
| `controller_block_diagram.png`, `controller_block_diagram.svg` | 미리보기와 문서 삽입용. matplotlib 렌더라 yEd 화면과 글꼴·간격이 조금 다를 수 있다 |

- 대상은 최종 제어기(R8 C2 + L1gs + DSb75 + SGS any_loc + R4c30)다. 10 Hz로 돌고 출력 지연은 d = 1이다.
- 신호 흐름은 왼쪽에서 오른쪽으로 간다. 입력(센서·목표) → 신호 처리 → 판정·추정 → 제어 법칙(LEVEL) → 최종 구성 추가 규칙 → 출력(행정 끝 감속, 증분 제한, d = 1 버퍼) → I/O·안전층(MCU) → 밸브 순이다. 상태 기계(`C2Phase`)는 아래쪽에 있다.
- 최종 구성 추가 규칙 4개는 빨간 굵은 테두리로 표시했다. 행정 예산 가드(P-S8-28)는 R8 C2 기본 규칙이고 SGS의 전제라서 같은 그룹에 빨간 점선 테두리로 넣었다.
- 점선 그룹 두 개는 이식 관점의 구분이다. 파란 점선은 Pi(Python)에서 실행하는 부분, 회색 점선은 I/O·안전층(MCU, 범위 밖)이다.
- 점선 엣지는 조건부 경로(고장, 재레벨, 진단 입력)를 뜻하고, 회색 점선 엣지는 진단·기록 경로를 뜻한다.
- 출처
  - 코드: `03_src/outrigger_sim/control/c2.py`(`update`, `_read`, `_update_attitude_filters`, `_phase_command`, `_level_step`, `_confirm_liftoff`, `_apply_slope_clearance_margin`, lift_stroke_guard·soil_stop, loc_revoke, diff_sink, `_apply_output_ramp`, `_delay_output`, `with_10hz_d1`)와 `two_pressure.py`, `ground_contact.py`, `zero_calibration.py`, `fault_reground.py`, `standstill.py`, `target.py`
  - 명세: `00_docs/04_control/s6_control_spec.md` 136·139절, 424.10.2, 424.11, 427.12.3, 427.12.5, 429.9, 429.11
  - CLAUDE.md "현재 기준값" 표, 상위 `README.md`(이식 조건 3: 안전 기능은 MCU에 둔다)
- 엣지는 모두 직교(수평·수직) 경로다. 꺾임점은 `y:Point`이고 `y:BendStyle smoothed="false"`다. 노드 좌표는 손으로 정한 배치를 쓰고, 경로는 격자 A* 맨해튼 라우팅(노드 회피, 다른 그룹 통과·겹침 벌점)으로 계산했다(2026-10-31).
- 이전판(직선 엣지)은 `history/controller_block_diagram_2026-10-31_straight.*`에 있다.
- 다시 만들 때: 명세 JSON과 라우팅 스크립트는 작성 세션 scratchpad에 있었고 저장소에는 넣지 않았다. 그림을 고칠 때는 yEd에서 graphml을 직접 편집한다(yEd의 Orthogonal Edge Router로 경로를 다시 잡을 수 있다).
