# prelaunch_j9 — 436.9 J-P3 실행 전 고정 자료

| 파일 | 뜻 | 경로 기준 |
|---|---|---|
| `FIXED_INPUTS_d3c6c57e.SHA256SUMS` | **현행** 고정 입력 목록(90줄: `78fd5d2d` 목록 72(바뀐 파일 새 sha, `run_steps/step2_dry.ps1` 포함) + 4a-7 정오 3·4a-8·4a-8 정오 1 각 두 파일 + 멈춤 보고 + `audit_prelaunch5.md` + `FIXED_INPUTS_78fd5d2d`·`P1_OUTPUTS_78fd5d2d` + L1 키 파일·생성 명령 + `step6v_vbj_rejudge.ps1` + 근거 `j4a_remedy_78fd5d2d`·`j4a_remedy_d3c6c57e` SUMS + `dg3_a1_LOCAL_ONLY` SUMS + 재판정 입력 `dg3_VBJ0.json`·`dg3_VBJ.json`(로컬 전용)). 고친 커밋 `d3c6c57e27f5b5448ecc33708b955773705ab22e`(VBJ 재판정, 덧붙임 4a-8, worktree `.claude/worktrees/z4369-jp3`, locked) 기준 | 저장소 루트. 대조: 저장소 루트에서 `sha256sum -c 06_analysis/02_control/j_p3_cause/prelaunch_j9/FIXED_INPUTS_d3c6c57e.SHA256SUMS` |
| `FIXED_INPUTS_78fd5d2d.SHA256SUMS` | 옛 목록(72줄, 실행 커밋 `78fd5d2d` 때 `2183fdc9…`). `run_steps/step2_dry.ps1`은 그 뒤 4a-8 3절로 바뀌었다(새 sha는 `d3c6c57e` 목록) | 저장소 루트 |
| `FIXED_INPUTS_fa997f4c.SHA256SUMS`, `FIXED_INPUTS_b51ed6e1.SHA256SUMS`, `FIXED_INPUTS_d84ba7bd.SHA256SUMS`, `FIXED_INPUTS_325b77a8.SHA256SUMS`, `FIXED_INPUTS.SHA256SUMS` | 옛 목록(63줄 `fa997f4c` 때 `792f6bbe…` / 57줄 `b51ed6e1` 때 `ccebf70d…` / 55줄 `d84ba7bd` 때 `00736c77…` / 43줄 `325b77a8` 때 `5aeb5f96…` / 31줄 `99e9132b` 때 `f35fa862…`). 기록용 | 저장소 루트 |
| `P1_OUTPUTS_<커밋 8자>.SHA256SUMS` | (단계 1이 쓴다) P-1 판정 파일·L1 참조 sha. 단계 6 전에 커밋돼 있어야 한다. `P1_OUTPUTS_b51ed6e1`·`P1_OUTPUTS_fa997f4c`는 앞 시도의 기록, `P1_OUTPUTS_78fd5d2d`는 현행 실행의 것 | 저장소 루트 |
| `l1_keys_d3c6c57e.json`, `l1_keys_d3c6c57e.command.txt` | VBJ 재판정용 L1 키 파일(102키, sha `eea8ed0d…`, 덧붙임 4a-8 정오 1 3절)과 생성 명령 | – |
| `h10_reuse_rerun_t4h.SHA256SUMS` | 저장 h10 T4h 426개 | **T4h 폴더** `06_analysis/03_hydraulic/coupled/v5/resume_k1/h10_reuse_rerun_t4h/` 기준(그 폴더에서 `sha256sum -c`) |
| `h6_dg3_v4on_t4h.SHA256SUMS` | 저장 H-6 T4h 135개 | **T4h 폴더** `…/resume_k1/h6_dg3_v4on_t4h/` 기준 |
| `run_steps/` | 단계 (1)~(7) 실행 명령과 VBJ 재판정 `step6v_vbj_rejudge.ps1`(PowerShell). 실행: `pwsh -File run_steps\stepN_*.ps1 [-Attempt N]`. 인터프리터는 dynamics-dev `python.exe -I -B` 직접 호출(기준선·저장 실행과 같음, 메인 결정 2026-11-21) | – |
| `audit_prelaunch.md`~`audit_prelaunch5.md` | verif-protocol-auditor 실행 전 감사·좁은 재감사 원문과 사용자 결정 | – |
| `evidence_precheck_fa997f4c/` | 정오 2 4절 증거 사전 대조(fa997f4c (4a)·(4b) VBJ·LSJ1~4 줄 10/10 맞음, 값 비출력) 스크립트·출력 | 그 폴더 |

- `resume_k1/`(244 MB)와 `v5/main.jsonl`은 git 밖이다. 이 목록의 sha로만 고정한다(덧붙임 4a-3 5.4절 허용). 새 checkout에서는 대조할 수 없다. 100 MB 넘는 `j9_runs/78fd5d2d/dg3_a1/dg3_VBH.json`·`dg3_VBJ.json`도 로컬 전용이다(`j9_runs/78fd5d2d/dg3_a1_LOCAL_ONLY.SHA256SUMS`, 사용자 결정 2026-11-21).
- 실행 출력은 `06_analysis/02_control/j_p3_cause/j9_runs/<커밋 8자>/<단계>_a<시도>/`(덧붙임 4a-5 5.2절). 현행: 단계 (1)~(6)은 `j9_runs/78fd5d2d/`, VBJ 재판정은 `j9_runs/d3c6c57e/dg3_vbj_a1/`.
- 시도 기록:
  - 실행 커밋 `b51ed6e1` 시도(`j9_runs/b51ed6e1/`, master `5bc974c0`)는 단계 (4a)가 판정 도구 결함(종료 3)으로 멈췄다. 4a-5 5.3 나에 따라 고친 커밋 `fa997f4c`로 단계 (1)부터 다시 돌렸다(덧붙임 4a-6).
  - 실행 커밋 `fa997f4c` 시도(`j9_runs/fa997f4c/`, master `2e495d01`)는 단계 (5) t8이 판정 도구 기준 결함(setting_defect 72, 종료 2)으로 멈췄다. 4a-7(+ 정오 1~3)에 따라 고친 커밋 `78fd5d2d`로 단계 (1)부터 다시 돌렸다. 단계 (1)~(4b)는 `fa997f4c` 결과와만 일치 대조했다(4a-7 2절).
  - 실행 커밋 `78fd5d2d` 시도: 단계 (1) a1은 정체성 mtime 점검으로 멈췄고(내용 동일, 보존) a2부터 (5)까지 종료 0, 재실행 대조 모두 같음(master `1bdaeea7`). 단계 (6)은 t12 VBH 종료 1(실제 실패, T-JR-12 실패 확정)·VBJ 종료 2(규칙·코드 결함)로 멈췄고(master `dfe341ba`, 멈춤 보고 `jp3_tjr12_stop_report_78fd5d2d.md`) (7)은 돌리지 않는다(판 5로 넘김). VBJ 묶음만 덧붙임 4a-8(+ 정오 1)대로 고친 커밋 `d3c6c57e`에서 `step6v_vbj_rejudge.ps1`로 다시 판정한다(5.3 나 예외, 사용자 결정).

## 운영 규칙(메인 세션, 2026-11-21)

- 모든 단계 시작과 **모든 다시 돌리기(`-Attempt 2` 이상)는 사용자 승인 뒤에만** 한다.
- 단계 6이 T-JR-14 실패(`LockWindowMismatchError`, 종료 1)로 멈추면 단계 7은 돌리지 않는다(4a-5 5.1 "멈춘다"). 실패 사실은 t12 보고에 남는다.
- 앞 시도의 판정 보고에 실패 항목이 하나라도 있으면(상태 우선순위 때문에 종료 2로 끝났더라도) 그 단계는 결과를 본 것으로 보고 다시 돌리지 않는다(4a-5 5.4). 명령 파일의 자동 거부는 종료 코드 1만 보므로, 이 경우는 메인 세션이 판정 도구 로그 마지막 줄의 `failures_count`로 확인해 막는다(사용자 결정 2026-11-21: 수동 유지).
- 재실행 일치 대조(4a-6 4절)가 다름(종료 1)이면 판정 실패와 같게 보고 같은 단계의 새 시도를 거부한다(사용자 결정 2026-11-21).
- 실행 커밋을 만든 뒤 worktree 파일을 다시 checkout하거나 수정 시각을 바꾸지 않는다(단계 정체성 `--mtime` 점검, 78fd5d2d 단계 (1) a1 사례).
