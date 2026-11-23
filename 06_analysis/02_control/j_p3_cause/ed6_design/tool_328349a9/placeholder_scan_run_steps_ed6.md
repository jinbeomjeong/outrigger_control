# placeholder_scan — 채워지지 않은 자리표시

- 파일 12개, 자리표시 0개(허용 2개) · 오류 0 · 경고 0 · 참고 2
- 패턴 묶음 `both`, 패턴 `\{[A-Z][A-Z0-9_]*\}|<[^\W\d][^<>"\n]{0,120}>`, 토큰: `<ED6_RUN_COMMIT>` 1, `<ED6_RUN_WORKTREE>` 1
- 자리표시로 보지 않고 건너뜀 0개 · 수식 건너뜀 True, 백틱 건너뜀 False

## 발견 사항

### 참고 (info) — 2건

| 분류 | 위치 | 대상 | 내용 |
|---|---|---|---|
| placeholder_allowed | C:\workspace\outrigger_control\.claude\worktrees\ed6-run6\06_analysis\02_control\j_p3_cause\prelaunch_j9\run_steps_ed6\ed6_run_config.template.json:3 | <ED6_RUN_COMMIT> | <ED6_RUN_COMMIT> (JSON $.run_commit) |
| placeholder_allowed | C:\workspace\outrigger_control\.claude\worktrees\ed6-run6\06_analysis\02_control\j_p3_cause\prelaunch_j9\run_steps_ed6\ed6_run_config.template.json:4 | <ED6_RUN_WORKTREE> | <ED6_RUN_WORKTREE> (JSON $.worktree) |
