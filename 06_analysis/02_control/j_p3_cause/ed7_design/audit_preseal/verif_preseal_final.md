## 판 7 봉인 전 마지막 확인 (시점: 실행 전)
대상은 명세 `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\jp3_remedy_spec_v7.md` 작업본이다. sha 9017e0a8을 실측했고 1107행이다.

**판정: 차단 0. 봉인 전에 147행 한 줄만 고치면 봉인할 수 있다.**

### N-1, M-9 처리 결과
- **N-1 풀림.**
  - 4절 5(587행): P7-10과 P7-4만 C에서 판정한다. P7-0·P7-6은 P7-4가 덮는다. P7-1·P7-2·P7-3·P7-9는 C에서 실행만 하고 판정은 T에서 한다.
  - 4절 5a(588행), 5.2 판정 불가 목록(652행): "4절 5의 P7-1·P7-2·P7-3·P7-9 판정과 6~10단계의 모든 판정"으로 넓어졌다.
  - 5.2 항목 11(649행): `j9main --edition 7`, t8, cases, hash-match, 12a VBM/VBM0, 12b VBKM/VBKM0와 P-pred, 감도, G1이 다 들어갔다.
  - 5.1(629행), 12절(1065행), Q7-U6(1084행)도 같은 내용으로 맞춰졌다.
- **M-9 풀림.** 41·42행이 "개정 6 감사 반영 시점 값, 현재 값을 따라가지 않음"으로 바뀌었다.
- **R-11 풀림.** probe 폴더 `SHA256SUMS`는 662항목(npz 654 포함)이고 불일치·빠진 파일·목록 밖 파일이 모두 0이다. sha 2226fe2f는 146행과 같다.
- **R-12 풀림.** 1036행 FL-Fs4 문구와 198행 C 범위 문구가 고쳐졌다.

### 남은 것: 실행 전 수정 1건 (봉인 전 1행)
- **147행 `audit_preseal/SHA256SUMS` 값이 현재 파일과 다르다.**
  - 명세: "3항목, `0c355ad2…`"
  - 현재 파일: 4항목, sha 68c7390f. 메인이 10:25:40에 다시 썼고, 명세 저장(10:25:13)보다 늦다. `handback_spec_rev6_recheck_fix.md`가 더해졌다.
  - `baseline_check sums`로 보면 4항목 모두 불일치 0이다. 그러니 명세 147행만 현재 값으로 바꾸면 된다(control-expert 또는 메인).
  - 앞으로 이 폴더에 파일을 더 넣으면 다시 어긋난다. 봉인 커밋 전 마지막 갱신 뒤에 값을 넣는다.

### 새 결함·남은 빈 곳
- 새 결함은 위 147행 1건 외에 없다.
  - seal_check `--quoted`에서 7절 밖의 미해결 인용은 147행 한 건만 새로 나왔다.
  - 나머지 미해결 인용은 개정 시점 값, 외부 파일, 블롭 값이다. 모두 앞 감사에서 대조했다.
- 남은 빈 곳은 S(봉인본 sha)와 C(실행 커밋 sha)뿐이다.
  - placeholder_scan은 `<key>` 3건을 냈다. 156·649행의 `VBM<key>`로, 감도 설정 이름을 쓴 표기법이라 자리표시가 아니다(거짓 양성).

### 실행한 검증
- 인터프리터: python-dev `-I -B` + `MKL_THREADING_LAYER=TBB`
- 도구
  - `seal_check --quoted --hash-files`
  - `baseline_check sums` × 2: probe 폴더, audit_preseal
  - `placeholder_scan --pattern-set both --skip-inline-code`
  - 명세 Grep: N-1·M-9 문구 확인
- scratchpad `verif-ed7seal3\`(요약 스크립트, seal.json)는 지웠다.
- source_guard snapshot은 이번에 생략했다. 대신 끝에 원본 해시를 다시 쟀다. 명세 9017e0a8, audit_preseal SUMS 68c7390f로 처음과 같다. 쓰기는 하지 않았다.
- 사용한 스킬: 없음
