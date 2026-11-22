# 기준선 실행 정체성 점검 (baseline_check identity)

- 파일 2개, git 블록 4개, 기대 커밋 876d8a49fe8b89c66d7781d0d0440ff87486fb2d
- head 값: 876d8a49fe8b89c66d7781d0d0440ff87486fb2d

| 파일 | 위치 | head | is_clean | 실행 시각 |
|---|---|---|---|---|
| `L1_VBJ.identity.json` | `$.start[0].git` | 876d8a49fe8b | True | 2026-11-23 00:04:27 +0900 |
| `L1_VBJ.identity.json` | `$.end[0].git` | 876d8a49fe8b | True | 2026-11-23 00:42:05 +0900 |
| `L1_VBJ0.identity.json` | `$.start[0].git` | 876d8a49fe8b | True | 2026-11-23 00:04:27 +0900 |
| `L1_VBJ0.identity.json` | `$.end[0].git` | 876d8a49fe8b | True | 2026-11-23 00:41:37 +0900 |

## mtime 검사

- 커밋 876d8a49fe8b89c66d7781d0d0440ff87486fb2d 시각 2026-11-22T23:55:24+09:00, 변경 파일 6개, 가장 이른 실행 2026-11-23T00:04:27+09:00
- 커밋 뒤에 바뀐 파일 6개 

## 발견 사항

### 경고 (warning) — 6건

| 분류 | 위치 | 대상 | 내용 |
|---|---|---|---|
| mtime_after_commit_before_run | C:\workspace\outrigger_control\.claude\worktrees\ed5-run4\06_analysis\02_control\j_p3_cause\ed5_design\junit\junit_769c379d_merged_all.pytest.log |  | 06_analysis/02_control/j_p3_cause/ed5_design/junit/junit_769c379d_merged_all.pytest.log: mtime 2026-11-22 23:55:37이 커밋 뒤, 실행 시작 2026-11-23 00:04:27 전: 실행이 커밋과 다른 내용을 읽었을 수 있다(지금 내용은 커밋과 같다(저장만 했거나 되돌렸을 수 있음)) |
| mtime_after_commit_before_run | C:\workspace\outrigger_control\.claude\worktrees\ed5-run4\06_analysis\02_control\j_p3_cause\ed5_design\junit\junit_769c379d_merged_all.record.json |  | 06_analysis/02_control/j_p3_cause/ed5_design/junit/junit_769c379d_merged_all.record.json: mtime 2026-11-22 23:55:37이 커밋 뒤, 실행 시작 2026-11-23 00:04:27 전: 실행이 커밋과 다른 내용을 읽었을 수 있다(지금 내용은 커밋과 같다(저장만 했거나 되돌렸을 수 있음)) |
| mtime_after_commit_before_run | C:\workspace\outrigger_control\.claude\worktrees\ed5-run4\06_analysis\02_control\j_p3_cause\ed5_design\junit\junit_769c379d_merged_all.skips.log |  | 06_analysis/02_control/j_p3_cause/ed5_design/junit/junit_769c379d_merged_all.skips.log: mtime 2026-11-22 23:55:37이 커밋 뒤, 실행 시작 2026-11-23 00:04:27 전: 실행이 커밋과 다른 내용을 읽었을 수 있다(지금 내용은 커밋과 같다(저장만 했거나 되돌렸을 수 있음)) |
| mtime_after_commit_before_run | C:\workspace\outrigger_control\.claude\worktrees\ed5-run4\06_analysis\02_control\j_p3_cause\ed5_design\junit\junit_769c379d_merged_all.xml |  | 06_analysis/02_control/j_p3_cause/ed5_design/junit/junit_769c379d_merged_all.xml: mtime 2026-11-22 23:55:37이 커밋 뒤, 실행 시작 2026-11-23 00:04:27 전: 실행이 커밋과 다른 내용을 읽었을 수 있다(지금 내용은 커밋과 같다(저장만 했거나 되돌렸을 수 있음)) |
| mtime_after_commit_before_run | C:\workspace\outrigger_control\.claude\worktrees\ed5-run4\06_analysis\02_control\j_p3_cause\ed5_design\junit\junit_769c379d_merged_t45data.worktree_tests.json |  | 06_analysis/02_control/j_p3_cause/ed5_design/junit/junit_769c379d_merged_t45data.worktree_tests.json: mtime 2026-11-22 23:55:37이 커밋 뒤, 실행 시작 2026-11-23 00:04:27 전: 실행이 커밋과 다른 내용을 읽었을 수 있다(지금 내용은 커밋과 같다(저장만 했거나 되돌렸을 수 있음)) |
| mtime_after_commit_before_run | C:\workspace\outrigger_control\.claude\worktrees\ed5-run4\06_analysis\02_control\j_p3_cause\ed5_design\junit\junit_769c379d_merged_t45data.xml |  | 06_analysis/02_control/j_p3_cause/ed5_design/junit/junit_769c379d_merged_t45data.xml: mtime 2026-11-22 23:55:37이 커밋 뒤, 실행 시작 2026-11-23 00:04:27 전: 실행이 커밋과 다른 내용을 읽었을 수 있다(지금 내용은 커밋과 같다(저장만 했거나 되돌렸을 수 있음)) |
