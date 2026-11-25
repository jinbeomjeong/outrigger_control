## 후속 확인: 6bfb2560 P1 보완 1-1·1-4 (hydraulics-expert)

두 항목 모두 **그대로**입니다. 코드는 고치지 않았고 시뮬레이션도 돌리지 않았습니다. `git diff a6fc3dd5 6bfb2560`(check_open_delay·v5_options·ed7 시험)과 구현 보고 원문만 읽었고, 블라인드 경로는 건드리지 않았습니다.

**1. 로드 체크가 열릴 때 Δp_fill만 지우고 `void_fill_m`은 남김: 그대로**
- 신장 중 로드 체크가 파일럿으로 열리면 바닥압(0.1 bar abs)의 로드 챔버가 B 라인과 이어집니다. B 라인 압력(p_bB 수준, p_T 2 bar 이상)이 챔버보다 높으므로 기름은 챔버 안으로 들어올 뿐 나가지 않습니다. 따라서 이미 채운 void 몫을 지우면 틀립니다.
- 실제로는 이 동안 B 라인이나 탱크에서 역류해 void가 더 채워질 수 있습니다. 하네스는 부분 충전량만 기억하므로 다음 수축 재열림이 늦어지는 쪽, 즉 보수 쪽입니다. 이 차이는 하네스 void가 운동학으로 정해지는 gate-only 한계 안에 있어 고칠 필요는 없습니다.
- 해제와 새 잠김에서 함께 지우는 것도 맞습니다. 해제 뒤에는 커널의 운동학 void가 다시 기준이 됩니다.
- 사소한 점(수정 불필요): 잠긴 채 void가 0이 됐다가 다시 생기면 옛 `void_fill_m`이 남지만, `min(void_fill_m, 현재 void)`로 상한이 걸리므로 그대로 둡니다.

**2. 1-1·1-4 구현이 권고와 같은가: 그대로**
- **1-4**
  - `_extend_step`에서 잠긴 다리의 `rod_released`가 거짓→참이 되는 순간 `fill_rise_Pa = 0`으로 둡니다.
  - 기록은 `rod_check_clear_log`, `rod_check_clear_count`, `rod_check_clear_log_truncated`에 남습니다.
  - 수축 열림 해제는 base + Δp_fill(옛 시드와 같음)에서 출발하는 그대로이고, 시험 `test_retract_release_still_starts_on_the_held_rise`가 이를 확인합니다.
  - 탐침 C 꼴 시험은 세 가지를 확인합니다: 로드 체크가 열리는 시점에 Δp_fill이 0이 됨, 헤드 열림 시각이 상승 없을 때와 같음, `_start_release` 입력(lag 출발 = base, `ReleaseStart`)이 상승 없을 때와 같음. 권고(hydraulics_p1a_review.md 1-4)와 같습니다.
- **1-1**
  - 충전 중 `void_fill_m = max(void_fill_m, min(x, void))`를 유지합니다.
  - 중립 바닥은 `max(상승 기반 갇힌 몫, min(void_fill_m, 현재 void))`이고, `clear_fill`에서 함께 지웁니다. 로드 진값은 바꾸지 않습니다.
  - 탐침 B 꼴 시험: 0.5 mm가 남고, void가 줄면 바닥도 따라 줄어듭니다. 권고 1-1과 같습니다.
- 2절 P4 가드(`rod_reading_truth` 요구)도 권고대로 들어갔습니다.

**남은 검증 공백(수정 아님)**: 미리보기 4줄에서는 1-4 경로가 한 번도 발동하지 않았습니다(`rod_check_clear_count` 0). probe 654줄 실행 뒤 VBM 계열에서 `rod_check_clear_count > 0`인 줄이 있는지 보고, 그 줄의 신장 해제에서 lag 출발 = 잠김 진값인지 기록으로 확인하기를 권합니다(메인 세션 권고, 별도 실행 없음).

사용한 스킬: 없음
