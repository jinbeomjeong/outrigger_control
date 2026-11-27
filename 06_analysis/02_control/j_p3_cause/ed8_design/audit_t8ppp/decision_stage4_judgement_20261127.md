# 판 8 4단계 판정서 초안 확인 필요에 대한 사용자 결정 (2026-11-27)

근거: 판정서 초안 `../stage4_judgement/stage4_judgement_ed8.md`(25ce1bbc) 8절.

1. P8-4 판정 근거(확인 필요 1): (나) T8⁗ 7ea78232 깨끗한 checkout에서 `tools/verif/worktree_tests.py` 꼴(C8 run과 같은 방식, main 자료 붙임)로 한 번 더 돌려 규칙 기준선 `p84_suite_41e107e9_56849248/base/junit.xml`과 직접 대조한다. C8 재실행은 아니다. 그 결과로 P8-4를 판정하고, 사슬 근거는 보조로 적는다.
2. P8-2 경로 2(확인 필요 2): census 경로 2와 함께 S8-C 전에 한다. 그때까지 판정서에는 "경로 1 통과, 경로 2 대조 대기"로 적는다.
3. 실행 출력 커밋(확인 필요 3): 판 7 판정서 7.5 꼴. 원격 한도(10^8 B) 초과 3파일과 npz는 LOCAL_ONLY 목록과 백업으로 sha를 고정하고 나머지를 커밋한다. `tools/integrity/large_outputs.py`는 건식으로 먼저 본다. 4단계 러너 `~/.claude/runners/outrigger-ed8/stage4/` 사본을 근거에 넣는다.
4. (낮음, 추천안 그대로) 공개 번호는 O8-13~로 이어 붙인다. FS24·G4 `effective_shape` RE1bF 기본값은 도구를 고치지 않고 G′ 판정서 기록 칸에 적는다.
