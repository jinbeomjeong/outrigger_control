# 판 8 근거 폴더 SHA256SUMS 기록 (메인 세션, 2026-11-27)

- 2026-11-27 4단계 전 커밋 준비에서 메인이 `baseline_check.py write-sums --force`로 여러 폴더 SUMS를 다시 썼다. 이 도구는 gitignore된 npz를 빼므로 `p816_prerun_41e107e9`·`p816_prerun_27c0f046`·`p816_prerun_66648ea8`의 SUMS가 npz 없는 꼴로 바뀌었다(규칙 위반: sha로 인용된 근거 폴더 SUMS를 다시 씀).
- integrity-checker가 인용 sha 불일치로 찾아냈고, 메인이 같은 날 원래 꼴(폴더 안 모든 파일, npz 포함, 상대 경로 정렬, LF)로 다시 만들어 되돌렸다. 되돌린 sha: `p816_prerun_41e107e9` `0921e251…`(인용값과 같음), `p816_prerun_66648ea8` `fd9605f1…`(인용값과 같음), `p816_prerun_27c0f046` `384431fe…`. 파일 내용은 바뀌지 않았다.
- `impl_report_ed8\SHA256SUMS`: 앞 문서(`audit_prerun\verif_c8_t8.md:256`)가 인용한 `d9e4f2ba…`는 T8 증거를 더하기 전의 상태다. 그 뒤 T8 보고·증거가 같은 폴더에 들어왔고(작성자 에이전트), 원래 목록을 다시 만들지 못했다. 지금 SUMS는 하위 폴더까지 모든 파일을 덮는 꼴로 새로 썼다(26파일, SUMS sha256 `e6bcab7d23abb2b8665c78d51240ae8d80f87858f2befefad5eebaf5fecda227`). 인용 문서는 고치지 않는다.
- 그 밖에 이번에 처음 쓴 SUMS: `audit_prerun\stats_nb1`, `audit_prerun\control_t8p_evidence`, `keys_seal_41e107e9`, `post_seal_disclosure`, 그리고 커밋 직전의 `audit_prerun`(상위).
- npz 163개(p816 세 폴더 162, `dynamics_gp_window\g02_traces.npz` 1)는 `ed8_design_LOCAL_ONLY.SHA256SUMS`에 더하고 `~/.claude/backups/outrigger-ed8/ed8_design/`에 백업했다(sha 대조 일치).
