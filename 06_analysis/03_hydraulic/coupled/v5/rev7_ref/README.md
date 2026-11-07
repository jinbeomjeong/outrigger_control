# rev7_ref — 개정 7 참조 구현·회귀 기준

`v5_criteria_rev7.md` 4절이 가리키는 참조 스크립트와 값(봉인 해시는 `v5_criteria_rev7.sha256`).

정오(2026-11-08, integrity 점검): `h7_sum_v2.json`의 `guard_bad`(9)는 참조 스크립트 `h7_exclusion.py`가 가드에 `truth + seal band < F_min`을 더한 엄격한 정의로 센 행 수다. 개정 7 3.2의 가드(강제 하한 < 0 kN)로는 위반이 0이다(제외 표본 강제 하한 최대 −4.50 kN). 도구 회귀 대조는 `guard_bad`가 아니라 `guard_forced_negative_all`(모든 행 참)로 한다. 봉인 문서는 고치지 않는다.
