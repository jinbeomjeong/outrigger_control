# prelaunch_j9 — 436.9 J-P3 실행 전 고정 자료

| 파일 | 뜻 | 경로 기준 |
|---|---|---|
| `FIXED_INPUTS_b51ed6e1.SHA256SUMS` | **현행** 고정 입력 목록(57줄: `325b77a8` 목록 43 + 4a-5 정오 1 두 파일 + 근거 `d84ba7bd`·`b51ed6e1` SUMS + `audit_prelaunch2.md` + 명령 파일 9개). 실행 커밋 `b51ed6e1090cb0a54f2c24799f372fb02c50653c`(worktree `.claude/worktrees/z4369-jp3`, locked) 기준 | 저장소 루트. 대조: 저장소 루트에서 `sha256sum -c 06_analysis/02_control/j_p3_cause/prelaunch_j9/FIXED_INPUTS_b51ed6e1.SHA256SUMS` |
| `FIXED_INPUTS_d84ba7bd.SHA256SUMS`, `FIXED_INPUTS_325b77a8.SHA256SUMS`, `FIXED_INPUTS.SHA256SUMS` | 옛 목록(55줄 `d84ba7bd` 때 `00736c77…` / 43줄 `325b77a8` 때 `5aeb5f96…` / 31줄 `99e9132b` 때 `f35fa862…`). 기록용 | 저장소 루트 |
| `P1_OUTPUTS_b51ed6e1.SHA256SUMS` | (단계 1이 쓴다) P-1 판정 파일·L1 참조 sha. 단계 6 전에 커밋돼 있어야 한다 | 저장소 루트 |
| `h10_reuse_rerun_t4h.SHA256SUMS` | 저장 h10 T4h 426개 | **T4h 폴더** `06_analysis/03_hydraulic/coupled/v5/resume_k1/h10_reuse_rerun_t4h/` 기준(그 폴더에서 `sha256sum -c`) |
| `h6_dg3_v4on_t4h.SHA256SUMS` | 저장 H-6 T4h 135개 | **T4h 폴더** `…/resume_k1/h6_dg3_v4on_t4h/` 기준 |
| `run_steps/` | 단계 (1)~(7) 실행 명령(PowerShell). 실행: `pwsh -File run_steps\stepN_*.ps1 [-Attempt N]`. 인터프리터는 dynamics-dev `python.exe -I -B` 직접 호출(기준선·저장 실행과 같음, 메인 결정 2026-11-21) | – |
| `audit_prelaunch.md`, `audit_prelaunch2.md` | verif-protocol-auditor 실행 전 감사·좁은 재감사 원문과 사용자 결정 | – |

- `resume_k1/`(244 MB)와 `v5/main.jsonl`은 git 밖이다. 이 목록의 sha로만 고정한다(덧붙임 4a-3 5.4절 허용). 새 checkout에서는 대조할 수 없다.
- 실행 출력은 `06_analysis/02_control/j_p3_cause/j9_runs/b51ed6e1/<단계>_a<시도>/`(덧붙임 4a-5 5.2절).

## 운영 규칙(메인 세션, 2026-11-21)

- 모든 단계 시작과 **모든 다시 돌리기(`-Attempt 2` 이상)는 사용자 승인 뒤에만** 한다.
- 단계 6이 T-JR-14 실패(`LockWindowMismatchError`, 종료 1)로 멈추면 단계 7은 돌리지 않는다(4a-5 5.1 "멈춘다"). 실패 사실은 t12 보고에 남는다.
- 앞 시도의 판정 보고 `failures`에 항목이 하나라도 있으면(상태 우선순위 때문에 종료 2로 끝났더라도) 그 단계는 결과를 본 것으로 보고 다시 돌리지 않는다(4a-5 5.4). 명령 파일의 자동 거부는 종료 코드 1만 보므로, 이 경우는 메인 세션이 보고를 확인해 막는다.
