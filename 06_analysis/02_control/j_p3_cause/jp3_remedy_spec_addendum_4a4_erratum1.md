# 덧붙임 4a-4 정오 1 (2026-11-21, control-expert 문안)

- 대상: `jp3_remedy_spec_addendum_4a4.md`(sha256 `67380b10…`) 3절. 그 밖의 4a-4 문장과 봉인 본문·4a-1~4a-3은 바뀌지 않는다. 결과 전 정정이다.
- 3절 명령 꼴의 키 입력 `--keys "<생성 키>"`를 `--keys-file <한 줄 키 파일>`로 바꾼다. 이유: 실행기 `r79_L3L4_final.cmd_run`의 `--keys`는 기본 seed 잡 목록 안의 키만 받아 s25 키를 거부한다. `--keys-file`은 seed ≥ 0인 표 규칙 사례 키를 받는다(436.8 seedext 경로). 두 옵션은 키 목록의 출처만 다르고 실행 함수·환경 변수·preset 검사는 같다. 실행기(`las_t3_dg3.py`)와 환경 변수는 3절 그대로다.
- 키 파일은 `select`가 쓴 한 줄 파일이다. 실행에는 저장소 사본 `06_analysis/02_control/j_p3_cause/j4a_remedy_b06e409e/dryrun_selection_r79_key.txt`(sha256 `1a79e02fc33ae8844d0cd5672e9e5e745215c354e58e9a8095376939c4335e74`, 내용 `L2|s25|g6|0|g6|G1+J1@FL|top|Fs0`)를 쓴다.
- 4a-4 2절의 "실행기 수용" 확인에 다음을 더한다: r79 출력 meta의 `keys_file.sha256`이 위 sha와 같고, `keys_file.n_keys` = 1이다. 다르면 판정 불가로 멈춘다.

## 사용자 확인(2026-11-21, 메인 세션 덧붙임)

- 위 정오로 진행한다(사용자 확인). 재검토 `jp3_impl_rereview_4a4.md` 3절 권고 R-2(새 H-6 판정 파일과 436.8 저장 경로 1 r79 판정의 키별 등급 대조, 기록·판정 조건 아님, 다르면 원인을 본 뒤 T-JR-12)도 넣는다.
