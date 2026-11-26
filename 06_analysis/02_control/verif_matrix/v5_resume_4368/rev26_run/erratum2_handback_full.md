저장 필요: C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368_rules_rev26_erratum2.md
# v5 재개 검증 436.8 규칙 rev26 — 정오 2 (부록 A r6: 같은 실행의 파트 digest, 4′ 감사 반영) (control-expert, 2026-11-26)

- **대상(봉인본)**
  - rev26 `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev26.md`
    - sha256 `f6591836a205dd52c698bbb613dbe4d74bfdc4b5a318dcb0d7873e9bb02c3b73`
    - `.sha256` `e74aeca93554d65a5e2344142827fa5cafa054153feff7f9d64406233676b80b`
    - 봉인 커밋 master `c77b1dcfce9119106838d307302bf8a48a07bff9`
  - 정오 1 `…/v5_resume_4368_rules_rev26_erratum1.md` sha256 `5e3bf3e6ec35253cb58dad8ca34383359b43235b314888b4709cd36d24df11f7`, `.sha256` `27f98bae33b70c852ec7c34800cefbf3260e95e541bd700d7c68fe9025b4452f`
  - 부록 A r5 `v5_resume_4368/rev26_fixed/excl_fields_r5.py` `bee9eee74a002d84710cde59fa20a1f2517c0b8cfa56173314d1d4eec36465f5`
  - 부록 B r5 `v5_resume_4368/rev26_fixed/rev26_excluded_fields_r5.json` `9e1831f5af2621510f9b6a7a8bf9f9c39c85f7633d8ef69bdc87895902e19283`(이 정오 작성자는 sha만 계산했다)
  - T26 `335004a7ad9f5f988e7543dd98d45bf2b96e4294`
- **날짜**: 2026-11-26
- **상태**: 봉인 전 초안이다. 메인이 4절 순서대로 부록 B r6를 만들고 점검한 뒤 `v5_resume_4368_rules_rev26_erratum2.sha256`으로 봉인한다.
- **근거 감사**: 4′ 점검 `v5_resume_4368/rev26_run/audit_4prime.md`(sha256 `c95bf8a3f8f8ed1072dbc02197a150d3c261a55df289518c926f9d5fc0d9b197`)의 B-1(차단), W-1, W-2, W-4, R-7, R-8, R-10, R-11
- **근거 결정**: 사용자 결정 2026-11-26
  1. B-1: `harness_path2/p2v5c_merge.json :: parts[].sha256`를 부록 A r6에서 I(같은 실행의 출력 digest)로 정한다. r6 파일은 새 폴더 `rev26_e2_fixed/`에 둔다. r5와 다른 규칙은 이것 하나뿐이다. 원 출력 적용 목록 r6은 메인이 규범 스크립트 r6으로 만들고 공개한다.
  2. (e)의 "두 경로 모두 S-2"는 "S-2가 나옴"으로 읽는다. 최상위 태그만 다른 실데이터 줄 때문에 생길 수 있는 S-13 위험은 판정서 기록 항목으로 둔다.
  3. rev26:126 "어느 묶음이든"에는 두 작성자 시험의 실데이터 읽기 2건이 들지 않는다(:138 정의). 판정서에 "범위 밖 실행 2건"으로 따로 공개한다.
  4. python-dev `conda list --export`가 실행마다 다르다. export sha는 기록으로 두고 이 비결정성을 공개한다. 전후 대조는 `stable_inventory` sha로 하고, 이것을 기록에 더한다.
  5. 감사 R-11(conda export 두 파일은 원 바이트 CRLF 보존)과 W-4(`input_basis_crosscheck`를 감사 R-5 표로 채움)를 반영한다.
  6. B-1 해소 뒤 4′ 재실행 범위: 변형 1~3(변형 3 = 다른 worktree + 빈 커밋)과 원 출력 쪽 도구 sha 잎 개수 점검(값 비출력, 사용자 승인). 감사자가 한다.
- **바꾸지 않는 것**
  - 판정 정의, 문턱, 등급 대조 표, 상태 순서, 판정 불가 처리, 5절 실패 처리
  - 기대 효과 (a)~(h)의 값(E2-4는 (e) 문장을 어떻게 읽을지만 정한다)
  - 1절 범위표, 3절 구현 조건, 2절 RD-1 4·5 대체 조건, 두 5단계 실행본(`rev26_run/run_judgement_path{1,2}_rev26.ps1`)
  - `rev26_fixed/**` 14파일(봉인 사본, 바이트 그대로)
- **정오 1과의 관계**: 정오 1은 부록 A·B를 "바꾸지 않는 것"에 두었다. 이 정오가 그 둘을 바꾼다(E2-1·E2-2). 정오 1의 나머지는 그대로 유효하다. 정오 1 2절 (가)의 "4′에서 판단"은 E2-4로 닫는다. 3절 "(새) 기록 보호" 행은 E2-8로 고친다.
- **T26은 바꾸지 않는다.**
  - 이 정오의 파일은 T26에 넣지 않는다.
  - T26 판정 도구는 부록 A·B를 읽지 않는다. T26 worktree의 `verif_matrix/scripts`, `path2`, `path2_v5c`의 `*.py`에서 `excl_fields|rev26_fixed|excluded_fields`를 Grep한 결과 0건이었다.
  - 그래서 RD-1 4 대체 조건 1의 바뀐 파일 37개와 4′ :146의 T26 `.gitattributes` 점검은 바뀌지 않는다.
- **요청 밖 추가**(사용자 결정 1~6 밖에서 이 정오가 더한 것)
  - ㉠ r5↔r6 목록 대조 도구 `rev26_e2_fixed/list_diff_r5_r6.py`와 그 결과 기록 `list_diff_r5_r6_stdout.json`을 둔다. 결정 1의 "메인이 생성하고 공개"를 기계적으로 점검하려는 것이다(E2-2).
  - ㉡ master `.gitattributes`에 `-text` 세 줄을 더한다(E2-10). 정오 1 E1-5와 같은 방식이다.
  - ㉢ 6절 기록 항목 둘을 더한다. 하나는 merge `parts[].sha256`이 같은 폴더 파트 파일과 맞는지 보는 내부 일치 기록이고(E2-11 (5)), 다른 하나는 E2-5에 감사 R-9 6절 5(`harness.json bundles.H-4.tags`)를 함께 적는 것이다.
  - ㉣ `t26_identity.json`에 `erratum2`·`appendix_a_r6` 칸과 `env_inventory_before/after` 칸을 더한다(E2-7, E2-9).

## 0. 공개 (결과 보기 전, 5단계 전)
- **436.8 재판정 결과를 보기 전, 5단계 실행 전의 정오다.** 판정 도구가 436.8 저장 결과(R2 `b9f5707`)에 돈 횟수는 4′ 감사 R-7 기준으로 0이다. 6단계에서 다시 센다.
- **이 정오의 작성자**(control-expert 새 인스턴스)가 열지 않은 것
  - 436.8 결과 json(`judge_932f1fb\` 아래 `_fixed` 밖)
  - 판정서, 판정 후 감사
  - 부록 B r5의 내용(sha만 계산)
  - 블라인드 경로
  - 경로 1 코드
- **연 것**(행위 그대로)
  - 4′ 감사 전체, rev26 전체, 정오 1 전체, `excl_fields_r5.py` 전체, `rev26_fixed/excl_check.py`
  - 경로 2 5단계 실행본 320~439행
  - `t26_identity.json` 1~40행과 1045~1134행
  - T26 worktree `path2_v5c/p2v5c_stage1.py` 690~779행(`cmd_merge`, 경로 2 코드). merge 출력의 구조를 코드로 확인하려고 열었다.
- **B-1 규칙은 원 출력 값을 보고 고르지 않았다.** 근거는 코드 구조뿐이다(merge가 같은 실행의 파트 파일 raw sha를 적는다). 이 필드는 데이터와 상관없이 실행마다 달라진다. 원 출력에서 이 필드가 어떤 구조인지는 메인이 r6을 원 출력에 적용해 확인하고 공개한다(E2-2).
- rev26 0절 공개(원 작성자가 아는 것, 결과 뒤 예외 둘)와 정오 1 0절 공개는 그대로 유효하다. 이 정오는 결과 뒤 예외를 더하지 않는다.

## 1. 정오 항목 표
| # | rev26(정오 1) 위치 | 봉인 원문 | 정오 뒤 | 구분 | 근거 |
|---|---|---|---|---|---|
| E2-1 | 부록 A 규범(:14~15, :211, 규칙 요약 :242 I 행), 머리말의 "함께 고정하는 부록 파일" | 규범 스크립트 `rev26_fixed/excl_fields_r5.py` | 규범 스크립트는 **`rev26_e2_fixed/excl_fields_r6.py`**다. I 규칙 하나를 더한다: `harness_path2/p2v5c_merge.json`에서 최상위 목록 `parts`의 각 원소 안의 스칼라 `sha256`(토큰 경로 `parts / [] / sha256`)은 I(같은 실행의 출력 digest)다. 그 밖의 규칙은 r5와 바이트가 같다(아래 설명의 diff). 두 쪽 모두 r6을 자기 인자로 적용한다(:211~213은 스크립트 이름만 바뀐다) | 비교 규칙(판정 정의 아님) | 결정 1, 감사 B-1 |
| E2-2 | 부록 B(:16, :214, :249~257), (c)(:169) "부록 B `c` 13 경로" | `rev26_fixed/rev26_excluded_fields_r5.json`(d 1,020 / c 13) | 원 출력 적용 목록은 **`rev26_e2_fixed/rev26_excluded_fields_r6.json`**이다. 메인이 4절 1·2로 만들고 점검한다. 기대값은 r5 목록에 `harness_path2/p2v5c_merge.json` 행 `[["parts","[]","sha256"],"I"]` 하나가 더해진 것이다: d 1,021 항목(68 파일, I 106 / S 647 / F 172 / NM 87 / NT 9), c 13(S). r5 목록과 r5 스크립트는 `rev26_fixed/`에 폐기본으로 남는다 | 비교 목록 | 결정 1 |
| E2-3 | 4′ :155(도구 sha 잎), :156~162(정체성 필드 덮음) | 부록 B r5, 부록 A 규범 규칙(r5) | 3절 표대로 한다. r6 규칙과 r6 목록을 쓴다. 변형 1~3을 모두 하고, 원 출력 쪽 도구 sha 잎은 개수와 경로만 낸다. B-1 해소(이 정오 봉인) 뒤 감사자가 한다 | 판정 전 점검 | 결정 6, 감사 W-1·W-2 |
| E2-4 | 5절 (e)(:171) | "합성 고정물 5건 …에서 두 경로 모두 S-2" | "두 경로의 판정 출력에 **모두 S-2가 나온다**"로 읽는다. S-2와 함께 다른 표지가 나와도 (e) 충족을 막지 않는다 | 해석(정의·값 불변) | 결정 2, 감사 R-8 |
| E2-5 | 6절 판정서에 적을 것(:190~194) | — | 기록 항목을 더한다. 최상위 `controller_tag`만 다른 u6 줄이 있을 때의 S-13 위험(아래 설명) | 기록 | 결정 2, 감사 R-8·R-9 |
| E2-6 | 3절 :126 "(어느 묶음이든)", 4절 6단계(:139), 6절(:194) | "판정 도구는 봉인 뒤 5단계 실행 전에 436.8 저장 결과에 돌리지 않는다(어느 묶음이든)" | 대상은 :138이 정의한 436.8 저장 결과(R2 `b9f5707`)에 판정 도구를 돌린 실행이다. 두 작성자 시험의 실데이터 읽기 2건은 범위 밖이다. 6단계 횟수(1회)에 세지 않고, 판정서와 6단계 보고에 "범위 밖 실행 2건"으로 따로 공개한다 | 해석·기록 | 결정 3, 감사 R-7 |
| E2-7 | 2절 :109 실행 환경 | "`conda list --export` sha와 python 판" | export sha는 그대로 기록으로 남기고, python-dev export의 비결정성을 공개한다. 5단계 직전·직후의 환경 대조는 `stable_inventory` sha로 하고, 그 값을 `t26_identity.json`의 `env_inventory_before`·`env_inventory_after`에 기록한다. 관문은 아니다 | 기록 | 결정 4, 감사 R-10 |
| E2-8 | 정오 1 3절 "(새) 기록 보호" 행 | "`rev26_run/` 파일의 … `git ls-files --eol` = `i/lf w/lf attr/-text`" | `conda_list_export_dynamics-dev.txt`·`conda_list_export_python-dev.txt` 두 파일은 `i/crlf w/crlf attr/-text`다(stdout 원 바이트 CRLF, 각 580·380줄). raw sha256은 `t26_identity.json` 값(`6cca76b4…`, `d5d66884…`)과 같아야 한다. 그 밖의 `rev26_run/` 파일은 원문 그대로 `i/lf w/lf attr/-text`다 | 판정 전 점검 | 결정 5, 감사 R-11 |
| E2-9 | 2절 :109 "2절 '입력 기준' 표와 두 경로 구현 기록의 대조 결과" | (`t26_identity.json` `input_basis_crosscheck` = null) | 4′ 감사 R-5 표(7행)와 그 아래 확인(:153 추적 입력, NM의 WT 루트 잔존 0)으로 채운다. 출처는 `audit_4prime.md` sha와 절 번호로 적는다. 채운 뒤 `t26_identity.json` sha를 다시 고정한다 | 기록 | 결정 5, 감사 W-4 |
| E2-10 | 7절(:197~206), 정오 1 4절 3 | — | master `.gitattributes`에 세 줄을 더한다(4절 3). T26 `.gitattributes`는 그대로다 | 기록 보호 | 요청 밖 ㉡ |
| E2-11 | 6절(:190~194) | — | 판정서에 적을 것을 더한다(아래 목록) | 기록 | 결정 1~5, 요청 밖 ㉢ |

### E2-1 설명 (B-1, 부록 A r6)
- **필드의 출처(코드)**
  - T26 `path2_v5c/p2v5c_stage1.py` `cmd_merge`(703~768행)가 `--part`마다 `rec = {"path": p, "sha256": cm.sha256_file(p), "tool": t, "status", "stop_codes", "tool_sha256", "head"}`를 만들어 최상위 `parts`에 넣는다(716~719행, 762행 `body = {"parts": parts, …}`). 멈춤 꼴(733행)도 같은 `parts`를 쓴다.
  - 감사 B-1에 따르면 932f1fb:712는 같은 줄이다.
  - `p`는 같은 실행이 같은 폴더에 쓴 `$Out\p2v5c_noise.json`, `$Out\p2v5c_stage1.json`, `$Out\p2v5c_grid.json`이다(5단계 경로 2 실행본 392~394행).
- **(d)에서 반드시 불일치하는 이유**
  - 파트 파일에는 실행마다 달라지는 I·S 필드가 들어 있다: `created`, 출력 경로, `tool_sha256`·`common_sha256`, `head_check.head`, `seals`의 rev26 칸(감사 B-1).
  - 그래서 파일 raw sha는 데이터와 상관없이 원 출력과 다르다.
  - r5 `classify`에서 키 `sha256`은 S·F·I 이름이 아니고 값에 커밋·출력 토큰·시각도 없다. 그래서 비교 대상이 된다(감사 B-1, 합성 이중 실행에서 48/48 파일 가운데 불일치는 이 3잎뿐).
- **잃는 비교가 없는 이유**
  - 파트 세 파일 `harness_path2/p2v5c_{noise,stage1,grid}.json`은 각각 (d) 무리의 파일이다(:218~220. r5 `SKIP_D_FILES`·`SKIP_D_SUBTREES`는 `u3.json`, `ind_las.json`, `head_check.json`, `harness.json` 일부만 뺀다). 각 파일은 자기 I·S·F를 지우고 NT·NM을 정규화한 뒤 그대로 비교된다.
  - r6이 빼는 것은 이 내용을 raw 바이트로 묶은 digest 하나다. 이 digest는 I·S 필드가 섞인 값이라 판정값 비교에 보태는 것이 없다.
  - merge 자신의 내용은 계속 비교된다: `RD-7`, `RD-7_sha256`, `RD-8`~`RD-10`, `RD-13`, `RD-13_sha256`, `markers`, `status`, `stop_codes`, `parts[].status`·`parts[].stop_codes`.
  - `parts[].path`(출력 토큰)와 `parts[].head`(도구 커밋)는 r5에서 이미 I이고, `parts[].tool`·`tool_sha256`은 이미 S다.
  - "merge가 같은 폴더의 그 파트 파일을 읽었다"는 연결은 (d)의 동치 항목이 아니다. 각 쪽 안의 기록으로 남긴다(E2-11 (5)).
- **범위를 좁게 둔 방식**: 폴더 `harness_path2`, 파일 `p2v5c_merge.json`, 최상위 `parts` 목록 원소 바로 아래의 스칼라 `sha256`만 해당한다. 다른 파일의 `sha256`, 중첩된 `parts`, 입력 경로·sha 블록, 같은 이름의 다른 폴더 파일은 r5처럼 비교한다(:245 "(비교) 입력 경로·sha 블록"은 그대로).
- **원 출력 최상위가 키 40개를 넘는 경우**: 이 경우 토큰이 `{*}`가 되어 r6 규칙이 걸리지 않는다. 코드상 최상위 키는 40개보다 훨씬 적다. 그래도 E2-2 점검(기대 행이 없으면 종료 1)이 이 경우를 잡는다.
- **r5 대비 차이**: `rev26_e2_fixed/excl_fields_r5_to_r6.diff`(LF 37줄, sha256 `273c3715bf27125ac7716c8c098151931b4ccc1a6c4718051884bd94646c12d2`). 다른 곳은 다음뿐이고, 나머지 줄은 바이트가 같다.
  - docstring: 판 번호, 개정 이력의 r6 구, I 범주 3줄
  - 사용법 줄의 파일 이름
  - 상수 `SAME_RUN_DIGESTS` 1줄
  - `classify`의 2줄(`TIME_NAMES` 판정 바로 뒤)
  - 출력 `rules` 이름 `excl_fields_r6`
- r6 스크립트: `rev26_e2_fixed/excl_fields_r6.py` sha256 `ce5208a8387acea5fcb94b3cbc9c5da3539f8375fdf6848a458cba31134f860e`(LF 327줄)
- 규칙 요약 표(:242)의 I 행은 이렇게 읽는다: "스칼라 문자열 가운데 도구 커밋·출력 폴더 토큰·실행 창 안 ISO 시각이 든 것. 시각 키(`created` 등)의 스칼라 값. **경로 2 `p2v5c_merge.json`의 `parts[].sha256`(같은 실행이 쓴 파트 파일의 raw sha, r6)**"

### E2-2 설명 (부록 B r6)
- 생성 명령은 :255와 같다. 스크립트 이름과 출력 파일만 바꾼다(4절 1).
- 점검: `list_diff_r5_r6.py`(sha256 `e08f5c36563082c35d799bb575f391b76181e3c1f8c959b190829703953ae1bb`)가 종료 0이어야 하고, 결과 기록이 아래 값과 같아야 한다.
  - `checks` 여섯 항목이 모두 참이다(규칙 이름, 범위 키 같음, d 파일 집합 같음, c 같음, 더해진 행은 기대 행 하나뿐, 빠진 행 없음).
  - `d_files` = [68, 68]
  - `d_entries` = [1020, 1021]
  - `d_by_cat_r6` = {F 172, I 106, NM 87, NT 9, S 647}
  - `c_entries` = [13, 13]
- 종료 1이나 2이면 봉인하지 않는다. r6 목록을 쓰지 않고 멈춰 사용자 결정을 받는다(:162와 같은 처리).
  - 이 도구는 다른 행이 있을 때만 그 행의 토큰 경로와 범주를 낸다(한쪽 최대 20). 원 출력 값은 내지 않는다.
  - `d_entries`의 r5 쪽이 1,020이 아니면, 봉인된 부록 B r5 파일이 아니라는 뜻이니 역시 멈춘다.
- (c)(:169)의 "부록 B `c` 13 경로 제외"는 r6 목록의 `c` 13 경로다(r5와 같음).

### E2-4·E2-5 설명 ((e)의 읽기와 기록 항목)
- **E2-4 근거(감사 R-8)**
  - 경로 1 실행본에서 `r4_inputs`는 `-Always` 관문이고, 종료 코드가 0이 아니면 "nothing judged"로 멈춘다(`run_judgement_path1_rev26.ps1:90~91`).
  - R26-3이 실패한 u6 줄은 r4-inputs에서 S-2(종료 1)를 낸다. 그래서 실행본 꼴에서는 record-check의 S-3이 판정 출력에 실리지 않는다.
  - 경로 2는 S-2만 낸다.
  - 단위 시험에서 경로 1이 S-2와 S-3을 함께 내는 것은 "S-2가 나옴"을 충족한다.
- **E2-5 판정서 기록 항목(판정 정의 불변, 새 예외 없음)**
  - u6 저장 줄의 (`controller`, `v5.controller_tag`) 쌍은 R26-3 대응과 맞는데 최상위 `controller_tag`만 다른 줄이 있다고 하자.
    - 경로 1 r4-inputs는 통과하지만, record-check(`abl_line`, 최상위 태그를 먼저 읽음)는 S-3을 낸다.
    - 경로 2는 v5 쌍만 읽으므로 이 줄에 S-3을 내지 않는다.
    - 그러면 두 경로의 표지 집합이 갈려 S-13이 될 수 있다. rev26:177대로 S-13 판정 불가를 그대로 둔다.
  - 같은 부류가 경로 2 `harness.json bundles.H-4.tags`의 (d) 불일치로 드러날 수도 있다(감사 R-9 6절 5, 요청 밖 ㉢). 이 경우는 5절 실패 처리 3행을 따른다.
  - 판정서에 적을 것: 5단계 출력에서 (i) 경로 1 record-check의 S-3 줄 수, (ii) 그 줄이 이 부류(최상위 태그 ≠ v5 태그)인지, (iii) 그 결과로 생긴 S-13·(d) 불일치 유무. 이 위험은 rev26 "436.8 입력의 쌍은 넷뿐(감사 실측)"이 최상위 태그까지 말하지 않아서 생긴다는 점도 적는다.

### E2-6 설명 (범위 밖 실행 2건, 감사 R-7)
1. 경로 1 작성자 시험의 G-S 건조 실행 배치 3건(`batch_V5-RESUME-K1-GS_20261113_*`)
   - 2026-11-13 건조 실행 배치이고, :138의 R2 `b9f5707` 저장 결과가 아니다.
   - 도구 `chrono_rows_judge_4368`은 5단계 실행본에 없다.
   - 출력은 pytest tmp에만 썼다.
2. 경로 2 작성자 시험의 `s9/rev85` 키 파일 읽기
   - 추적된 v4 연구 키 입력(D 자리)을 932f1fb판 `study_keys`가 읽었다.
   - 판정 출력을 만들지 않았고, 출력은 tmp에만 썼다.
- 판정서와 6단계 보고에 "범위 밖 실행 2건"으로 이 둘을 적는다. 6단계의 "판정 도구가 436.8 저장 결과에 돈 횟수"(:139)에는 넣지 않는다.

### E2-7 설명 (실행 환경)
- **python-dev**
  - export sha `d5d668845af0375786b1bb91ecd175ff8aceb16ea56980ab85f7d8617c2d0f63`(2026-11-26 20:35 캡처, 380줄)는 기록으로 남긴다.
  - 같은 날 다시 뽑은 값은 `faad5d83…`로 달랐다.
  - 원인: 네 프로젝트(onnxruntime, platformdirs, protobuf, soupsieve)의 dist-info가 둘씩 있어서 `conda list --export`가 매번 하나를 임의로 고른다(`t26_identity.json` `environment.export_stability_note`).
  - 판정 영향은 없다. 5단계의 python-dev 단계(log_errors, sidecars 사본, x16_records)는 이 넷을 import하지 않는다(감사 R-10).
- **dynamics-dev**: export sha `6cca76b4…`는 다시 뽑아도 같았다.
- **전후 대조**
  - 메인이 5단계 시작 직전과 끝난 직후에 두 env의 `stable_inventory`를 같은 방법으로 다시 계산한다. 방법은 `t26_identity.json` `environment.<env>.stable_inventory.method`다.
  - 명령, 시각, sha256, `conda_meta_count`, `dist_info_count`를 `env_inventory_before`·`env_inventory_after`에 적는다.
  - 4′ 기준값: python-dev `b32b783e582f26d708e9d9d6d3db57e458364f7129fc69d4677af8818906a817`, dynamics-dev `c27f109fa9015b5d38f5a8fe7edf72e136d6bdac0aff0f969704222844283cc8`
  - 값이 달라지면 판정서에 공개한다(기록이고 관문은 아니다).
- dist-info 중복 정리는 환경 변경이라 이 정오에서 다루지 않는다(사용자 결정 사항, 5단계 뒤).

### E2-11 판정서에 더 적을 것(6절)
1. 부록 A r6(E2-1)와 그 근거, r5 대비 diff 파일과 sha, 부록 B r6 생성·점검 기록(`list_diff_r5_r6_stdout.json`과 4절 1·2의 명령·시각)
2. E2-4의 (e) 읽기, E2-5 기록 항목
3. 범위 밖 실행 2건(E2-6)
4. 실행 환경: export sha, 비결정성 공개, `env_inventory_before/after`(E2-7). conda export 두 파일은 LF가 아니라 원 바이트를 보존했다(E2-8)
5. (요청 밖 ㉢) 각 쪽의 merge `parts[].sha256`이 같은 폴더 파트 파일(`p2v5c_noise.json`, `p2v5c_stage1.json`, `p2v5c_grid.json`)의 raw sha256과 같은지. 판정이 아니라 기록이고, 건수만 적고 값은 쓰지 않는다. 새 출력 쪽은 경로 2 `sha256_manifest.txt`와도 대조한다
6. 4′ 재실행 결과(3절)와 `t26_identity.json`의 최종 sha

## 2. 두 경로 범위 대조
- 이 정오가 바꾸는 것은 셋이다: 부록 A·B(비교 규칙과 목록), (e) 문장의 읽기, 기록 항목.
- 판정 정의(판정 집합, 0건·결측 처리, 상태 이름)는 바꾸지 않는다.
- 봉인본 1절(범위)·3절(작성자 조건)과 대조했다.
  - 부록 A·B는 작성자에게 넘기지 않는 비교 도구다(:122 "부록 B는 작성자에게 넘기지 않는다").
  - (e)의 읽기는 이미 구현된 두 경로의 동작을 바꾸지 않는다.
  - T26은 그대로다.
- 그래서 **경로 2 넘김에 더할 [정의] 문장은 없다.** 경로 1도 같다.

## 3. 4′ 점검 변경(rev26 4′ :142~162, 정오 1 3절에 대한 정오)
| 4′ 항목 | 봉인 원문(정오 1 포함) | 정오 뒤 |
|---|---|---|
| (새) 정오 2 봉인 | — | `.sha256`이 적은 sha와 각 파일 raw sha가 같아야 한다. 대상: 정오 2 `.md`, `rev26_e2_fixed/` 다섯 파일(`excl_fields_r6.py`, `excl_fields_r5_to_r6.diff`, `list_diff_r5_r6.py`, `rev26_excluded_fields_r6.json`, `list_diff_r5_r6_stdout.json`). `list_diff_r5_r6_stdout.json`은 E2-2 기대값과 같아야 한다(`status` ok). `rev26_fixed/**` 14파일의 sha는 바뀌지 않아야 한다. 감사자가 `list_diff_r5_r6.py`를 봉인된 두 목록에 다시 돌려 종료 0인지 본다(목록 파일만 읽고, 원 출력은 읽지 않는다) |
| 도구 sha 잎(:155) | 부록 B r5로 원 출력의 I·S·F를 뺀 비교 잎 | **원 출력 쪽을 한다(사용자 승인 2026-11-26, 값 비출력).** 부록 B r6으로 원 출력(`judge_932f1fb/harness_path1`·`harness_path1_retry1`·`harness_path2`의 `*.json`)에서 I·S·F를 뺀다. 남은 잎의 64자리 16진 값 가운데 `git show 932f1fb:<허용 목록 29파일>`(경로 1 14 + 경로 2 15)의 raw·LF·CRLF sha256과 같은 것의 **건수와 잎 경로만** 낸다. 0건이어야 한다. 0이 아니면 멈추고 사용자 결정을 받는다. 새 출력 쪽(합성)은 아래 정체성 점검의 출력으로 r6 규칙에서 다시 한다 |
| 정체성 필드 덮음(:156~162) | 부록 A 규범 규칙(r5), 변형 1~3 | 규칙은 **r6**이다(`excl_fields_r6`의 `Rules`·`classify`). **변형 1~3을 모두 한다.** 변형 3은 T26에서 만든 두 번째 worktree(예: `.claude\worktrees\rev26-t26x`, 메인이 만들고 `git commit --allow-empty`)다. 합성 입력은 첫 4′에서 만들지 못한 출력(감사 W-1 목록: 경로 1 약 20개, 경로 2 `d1.json`)을 되도록 보강한다. 통과 조건은 :160 그대로다. B-1의 3잎은 r6에서 I로 빠져야 하고, 그 밖에 새로 달라지는 필드가 있으면 멈추고 사용자 결정을 받는다(:162). 끝내 만들지 못한 출력은 목록과 정적 검토 근거를 4′ 보고에 적는다. 그 출력이 5단계에서 (d) 불일치를 내면 5절 실패 처리 3행을 따른다(새 예외 없음). 남은 목록이 0이 아니면 메인이 사용자 확인을 받은 뒤 5단계로 간다 |
| `t26_identity.json`(:143, 정오 1 3절 첫 줄) | 고정 파일 sha | 새 sha(E2-9 채움, R-10 공개, ㉣ 칸 더함 뒤 메인이 고정)와 같아야 한다. `input_basis_crosscheck`가 null이 아니고 감사 R-5 표와 같아야 한다 |
| 기록 보호(정오 1 3절 "(새) 기록 보호") | `rev26_run/` 파일 `i/lf w/lf attr/-text` | E2-8대로 한다(conda export 두 파일은 `i/crlf w/crlf attr/-text`). 정오 2 파일과 `rev26_e2_fixed/**`는 `git check-attr text` = `unset`, 커밋했으면 `git ls-files --eol` = `i/lf w/lf attr/-text`다 |
| 실행 환경 | — | E2-7의 4′ 기준값이 `t26_identity.json`에 있어야 한다. python-dev export 재추출 sha가 달라도 점검 실패가 아니다(공개 문장이 있는지만 본다) |
| 나머지 | — | 첫 4′의 충족 항목(R-1~R-6, R-13)은 다시 하지 않는다. 다만 `t26_identity.json` sha가 바뀌므로, 그 안의 실행본·도구·규칙 파일 sha 값이 첫 4′ 재계산값과 같은지는 다시 본다 |

## 4. 메인 처리 순서(5단계 전)
1. **부록 B r6 생성.** python-dev로 원 출력에 적용한다. 출력은 목록 파일 하나이고, stdout은 개수뿐이다.
   ```
   & C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B -X utf8 C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368\rev26_e2_fixed\excl_fields_r6.py C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368\rev26_e2_fixed\rev26_excluded_fields_r6.json --root C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368\judge_932f1fb --commit 932f1fb1724f074e4ee93a9c02193c7c840d13c4 --out-token judge_932f1fb --window "harness_path1=2026-11-16T16:28:00/2026-11-16T16:31:00" --window "harness_path1_retry1=2026-11-16T16:43:00/2026-11-16T16:45:00" --window "harness_path2=2026-11-16T13:55:00/2026-11-16T16:33:00" --main-root "C:\workspace\outrigger_control"
   ```
   - 기대 stdout: `d_files` 68, `d_entries` 1021, `d_by_cat` {I 106, S 647, F 172, NM 87, NT 9}, `c_entries` 13
2. **점검.**
   ```
   & C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B -X utf8 C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368\rev26_e2_fixed\list_diff_r5_r6.py C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368\rev26_fixed\rev26_excluded_fields_r5.json C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368\rev26_e2_fixed\rev26_excluded_fields_r6.json --out C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368\rev26_e2_fixed\list_diff_r5_r6_stdout.json
   ```
   - 종료 0이고 E2-2 기대값과 같아야 한다.
   - 다르면 봉인하지 않고, r6 목록 파일과 결과 파일을 보존한 채 멈춘다. 그리고 사용자에게 결과(토큰 경로·범주·개수, 값 없음)를 그대로 전한다.
   - 1·2의 명령·시각·종료 코드는 판정서 기록용으로 남긴다.
3. **`.gitattributes`(master, 요청 밖 ㉡).** 아래 세 줄을 더한다. `rev26_e2_fixed/`와 정오 2를 `git add`하는 커밋과 같은 커밋이나 그보다 앞선 커밋에 넣는다.
   - `06_analysis/02_control/verif_matrix/v5_resume_4368/rev26_e2_fixed/** -text`
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev26_erratum2.md -text`
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev26_erratum2.sha256 -text`
4. **봉인.** `v5_resume_4368_rules_rev26_erratum2.sha256`의 첫 줄은 이 정오 파일이다. 다음 줄은 차례로 `rev26_e2_fixed/excl_fields_r6.py`, `excl_fields_r5_to_r6.diff`, `list_diff_r5_r6.py`, `rev26_excluded_fields_r6.json`, `list_diff_r5_r6_stdout.json`이다.
   - `rev26_e2_fixed/`에는 봉인 뒤 파일을 더하지 않는다. 감사·검토 hand-back은 다른 폴더에 둔다.
   - `rev26_fixed/**`에는 손대지 않는다.
5. **`t26_identity.json`을 다시 만든다**(메인 또는 준비 작성자). 넣을 것:
   - (E2-9) `input_basis_crosscheck` = 감사 R-5 표. 출처는 `audit_4prime.md` sha `c95bf8a3…`와 "R-5"
   - (E2-7) `environment.python-dev`에 비결정성 공개 문장, `env_inventory_before/after` 빈 칸(5단계 때 채움)
   - `open_items`의 python-dev 항목을 "정오 2 E2-7로 닫음"으로 옮긴다
   - (㉣) `erratum2` 칸(`.md`·`.sha256` raw sha, 추적 여부, `in_t26: false`), `appendix_a_r6` 칸(r6 스크립트·diff·list_diff 도구·r6 목록·list_diff 결과의 sha)
   - 새 sha는 메인이 고정해 4′ 재감사에 넘긴다.
6. **변형 3 준비**(감사 메인 권고 2).
   ```
   git -C C:\workspace\outrigger_control worktree add .claude\worktrees\rev26-t26x -b rev26-t26x 335004a7
   git -C C:\workspace\outrigger_control\.claude\worktrees\rev26-t26x commit --allow-empty -m "4' variant 3"
   ```
   - 4′ 감사자를 이어 부르고, 3절 표와 승인 문구 "judge_932f1fb 원 출력에 값 비출력 개수 스크립트 허용"을 넘긴다.
   - 끝나면 `rev26-t26x`를 지운다.
7. 감사 메인 권고 3·4·6(메인 추적 트리 정리, 커밋 순서와 `ls-files --eol` 확인, 5단계 직전 `wt_status_before`와 `env_inventory_before`)은 그대로 따른다. 커밋 순서에는 이 정오와 `rev26_e2_fixed/`를 더한다.

## 5. 자체 대조(봉인 전)
- **판정·기록 구분**: 1절 표의 "구분" 열에 적었다. 상태 순서(판정 실패 > 설정 결함 > 판정 불가 > 통과)와 판정 행 0 처리는 rev26 그대로다.
- **계산되지 않는 경우의 처리**
  - E2-2 점검이 종료 1이나 2이면 봉인하지 않고 멈춘다.
  - 4′에서 만들지 못한 출력이 남으면 목록으로 적고, 5단계에서 불일치가 나면 5절 3행을 따른다.
  - 원 출력 쪽 도구 sha 잎이 0건이 아니면 멈춘다.
- **닿는 경로 확인(코드)**
  - r6 규칙이 실제 경로에서 걸리는지는 `classify`를 부르는 `walk`(r6 227~242행)로 확인했다. 부르는 조건은 dict가 40키 이하일 때이고, 넘으면 E2-2 점검이 잡는다.
  - merge 출력 구조는 T26 `p2v5c_stage1.py` 703~768행에서 확인했다.
  - 파트 파일 세 개가 `harness_path2/*.json`이라는 것은 경로 2 실행본 392~394행에서 확인했다.
- **참조 경로 존재 확인**
  - 있음(작업 트리, 추적 안 됨): `rev26_e2_fixed/excl_fields_r6.py`, `excl_fields_r5_to_r6.diff`, `list_diff_r5_r6.py`. 메인 checkout에서 ignore에 걸리지 않는다(`git check-ignore` 종료 1).
  - 4절 1·2가 만들 생성물: `rev26_excluded_fields_r6.json`, `list_diff_r5_r6_stdout.json`. 생성 명령은 4절에 있다.
  - `audit_4prime.md`, `t26_identity.json`은 있다(`rev26_run/`, 추적 안 됨).
- **항등 지표 점검**: r6은 비교에서 빼는 규칙이고 새 판정 지표를 만들지 않는다. E2-11 (5)는 기록이다. 같은 실행 안에서 파트 파일과 merge digest가 같은지는 정의상 같아야 하는 값이므로 구현 확인 용도로만 둔다.
- **아직 없는 해시**: 부록 B r6 목록, list_diff 결과 파일, 이 정오와 그 `.sha256`, 새 `t26_identity.json`의 sha는 메인이 고정한다. 본문에는 자리로만 적었다.

---

## 공개 (봉인본에서 뗌) — 작성자 행위, 시험, 메인용 공개 문장 초안

### 작성자 행위(그대로)
- **Read**
  - `rev26_run/audit_4prime.md` 전체
  - `v5_resume_4368_rules_rev26.md` 전체, `…_rev26_erratum1.md` 전체
  - `rev26_fixed/excl_fields_r5.py` 전체, `rev26_fixed/excl_check.py` 전체
  - `rev26_run/run_judgement_path2_rev26.ps1` 320~439행
  - `rev26_run/t26_identity.json` 1~40행, 1045~1134행
  - T26 worktree `path2_v5c/p2v5c_stage1.py` 690~779행(경로 2 코드. merge 출력 구조 확인용이고, 나는 두 경로 어느 쪽의 작성자도 아니다)
- **Grep**
  - `t26_identity.json`(패턴 `stable_inventory|input_basis_crosscheck|conda_list|python-dev|export`, 줄 출력)
  - T26 worktree `verif_matrix/scripts`·`v5_resume_4368/path2`·`v5_resume_4368/path2_v5c`의 `*.py`(패턴 `excl_fields|rev26_fixed|excluded_fields`, 파일 목록 모드, 3곳 모두 0건)
- **Bash**
  - `ls`: `v5_resume_4368/`(폴더 이름 목록), `rev26_fixed/`
  - `mkdir`: `rev26_e2_fixed/`, scratchpad `control-rev26e2/`
  - `cp`: r5 → r6 시작본
  - `git check-attr`/`check-ignore`: 새 파일 경로 셋
  - `git rev-parse`·`git log -1`(c77b1dcf, 335004a7)
  - `git worktree list`
- **sha만 계산(내용 비출력)**: `rev26_excluded_fields_r5.json`, `audit_4prime.md`, `t26_identity.json`, rev26·정오 1 `.md`·`.sha256`, 경로 2 실행본
- **열지 않은 것**
  - 436.8 결과 json(`judge_932f1fb\` 아래 `_fixed` 밖. 위 `ls`는 `v5_resume_4368/` 바로 아래 폴더 이름만 보였다)
  - 판정서, 판정 후 감사, 부록 B 내용, 블라인드 경로, 경로 1 코드
- **상위 폴더 검색**: 상위 폴더(저장소 루트, `06_analysis`, `02_control`, `verif_matrix`)를 검색 path로 쓰지 않았다. 맨 이름 Glob도 쓰지 않았다.
- **판정 도구 실행**: 0회. 부록 A 스크립트 r5·r6과 `list_diff`만 scratchpad 합성 고정물에 돌렸다.
- **종료한 프로세스**: 없음
- **설치**: 없음

### 합성 시험(scratchpad `control-rev26e2\test_r6.py`, python-dev `-I -B`, 결과 `test_r6_out.json` status ok)
- **고정물**: 두 쪽 A(원 출력 꼴: 커밋 `a…`, 토큰 `judge_aaaaaaa`, 11-16 창)와 B(새 출력 꼴: 커밋 `b…`, 토큰 `judge_rev26_bbbbbbb`, 11-27 창, `--checkout-root` = 합성 WT)
  - 파일 8개(+ 범위 밖 `u3`·`ind_las`·`head_check`)
  - `harness_path2/p2v5c_merge.json`의 `parts` 3원소: `sha256`은 두 쪽이 다르고, `path`는 토큰을 품고, `head`는 커밋이다
  - 대조군: 중첩 `R4.parts[].sha256`, `harness_path2/other.json`의 최상위 `parts[].sha256`, 같은 이름의 `harness_path1/p2v5c_merge.json`, 입력 sha 블록, NT·NM 문자열, argv
- **결과**
  1. **목록**: 두 쪽 모두 r5 = 32 항목(I 13 / S 17 / NT 1 / NM 1), r6 = 33 항목(I 14). `list_diff_r5_r6.py`는 종료 0이고, 더해진 행은 `harness_path2/p2v5c_merge.json [parts, [], sha256] I` 하나다. 대조군 `sha256` 잎은 r6에서도 행이 생기지 않았다(비교 유지). `--out` 기록 파일은 stdout과 같고 CR은 0이다.
  2. **끝-끝 비교**(각 쪽이 자기 I·S·F를 지우고 NT·NM을 정규화): r5는 불일치가 `p2v5c_merge.json`의 `parts/0..2/sha256` 3잎뿐이었다(감사 B-1 재현). r6은 8/8 파일 모두 같았다.
  3. **`list_diff` 음성 시험**: 아래 네 경우 모두 종료 1이었다. 입력 파일이 없으면 종료 2였다.
     - 기대 행이 빠짐
     - 다른 파일에 행이 더해짐
     - 기존 행이 빠짐
     - `c`가 바뀜
- **파일 꼴**: r6·diff·list_diff 모두 LF(CR 0), UTF-8
- **시험 뒤**: `rev26_fixed/`는 14파일 그대로이고 하위 폴더(`__pycache__`) 0이다. `rev26_e2_fixed/`는 3파일이다.

### r5 → r6 diff(`rev26_e2_fixed/excl_fields_r5_to_r6.diff`와 같은 내용)
```diff
--- rev26_fixed/excl_fields_r5.py
+++ rev26_e2_fixed/excl_fields_r6.py
@@ -1,2 +1,2 @@
-"""rev26 normative exclusion / normalisation rules for the (d) and (c) comparisons, revision 5.
+"""rev26 normative exclusion / normalisation rules for the (d) and (c) comparisons, revision 6.
 
@@ -7,3 +7,4 @@
 the path 1 ``resume_k1_family.py`` is an identity pair like ``--root``), r5 (re-audit 5 B-6: NT also covers the rev26
-section 2 W data locations, files the tools read from their own checkout by design).
+section 2 W data locations, files the tools read from their own checkout by design), r6 (4' audit B-1, erratum 2: the
+same-run part digests ``parts[].sha256`` of path 2 ``p2v5c_merge.json`` are I).
 
@@ -34,2 +35,5 @@
      ``created_at``, ``generated_at``, ``started_at``, ``finished_at``.
+  I  same-run output digests: in path 2 ``harness_path2/p2v5c_merge.json`` the scalar ``sha256`` of every element of
+     the top-level list ``parts`` (path ``parts / [] / sha256``): the raw sha256 of a part file written by the same
+     run; each part file is itself a (d) file and is compared there.
   I  argument lists (keys ``argv``, ``args``, ``cmd``, ``command``, ``commands_run``): the ELEMENTS that hold the
@@ -63,3 +67,3 @@
 Usage (dynamics-dev or python-dev):
-  python -I -B -X utf8 excl_fields_r5.py <out.json> --root <judge output dir> --commit <tool commit>
+  python -I -B -X utf8 excl_fields_r6.py <out.json> --root <judge output dir> --commit <tool commit>
       --out-token <output-folder token> --window <folder>=<start>/<end> [...]
@@ -98,2 +102,3 @@
               "created_at", "generated_at", "started_at", "finished_at"}
+SAME_RUN_DIGESTS = {("harness_path2", "p2v5c_merge.json"): {("parts", "[]", "sha256")}}
 ARG_NAMES = {"argv", "args", "cmd", "command", "commands_run"}
@@ -211,2 +216,4 @@
     if name in TIME_NAMES and is_scalar(v):
+        return "I"
+    if tuple(path + [name]) in SAME_RUN_DIGESTS.get((folder, fname), ()) and is_scalar(v):
         return "I"
@@ -293,3 +300,3 @@
     rules = Rules(a.commit, a.out_token, windows, a.main_root, a.checkout_root)
-    out = {"rules": "excl_fields_r5", "scope_d_skipped_files": sorted(f"{x}/{y}" for x, y in SKIP_D_FILES),
+    out = {"rules": "excl_fields_r6", "scope_d_skipped_files": sorted(f"{x}/{y}" for x, y in SKIP_D_FILES),
            "scope_d_skipped_subtrees": {f"{x}/{y}": [list(s) for s in v] for (x, y), v in SKIP_D_SUBTREES.items()},
```
(difflib 문맥 1줄이라 `classify` 쪽 hunk는 기존 `return "I"` 줄을 기준으로 보인다. 실제로 더한 것은 `if tuple(path + [name]) …` 조건과 그 아래 `return "I"` 두 줄이다.)

### 산출 파일(전체 경로, sha256)
| 파일 | sha256 | 비고 |
|---|---|---|
| `C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368\rev26_e2_fixed\excl_fields_r6.py` | `ce5208a8387acea5fcb94b3cbc9c5da3539f8375fdf6848a458cba31134f860e` | 규범 스크립트 r6, LF 327줄 |
| `C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368\rev26_e2_fixed\excl_fields_r5_to_r6.diff` | `273c3715bf27125ac7716c8c098151931b4ccc1a6c4718051884bd94646c12d2` | r5 대비 unified diff, LF 37줄 |
| `C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368\rev26_e2_fixed\list_diff_r5_r6.py` | `e08f5c36563082c35d799bb575f391b76181e3c1f8c959b190829703953ae1bb` | 요청 밖 ㉠, LF 88줄 |
| (메인 생성 예정) `…\rev26_e2_fixed\rev26_excluded_fields_r6.json`, `…\rev26_e2_fixed\list_diff_r5_r6_stdout.json` | — | 4절 1·2 |
| scratchpad `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\0d95027e-6012-4053-b99a-1e505935768c\scratchpad\control-rev26e2\test_r6.py`, `…\test_r6_out.json`, `…\make_diff.py`, `…\shas.py` | — | 시험 근거. 정오 근거로 남기려면 메인이 프로젝트 근거 폴더(예: `rev26_e2_fixed`가 아닌 별도 `audit_preseal/` 계열)로 복사한다 |

### 메인용 공개 문장 초안(부록 B r6 생성, 4절 1·2 뒤 판정서·정오 기록에 쓴다. `<…>`는 메인이 채운다)
> 부록 B r6(`rev26_e2_fixed/rev26_excluded_fields_r6.json`, sha256 `<…>`)은 메인이 2026-<…> <시각>에 만들었다. 규범 스크립트 r6(`excl_fields_r6.py`, `ce5208a8…`)을 원 출력 `judge_932f1fb/`(`harness_path1`·`harness_path1_retry1`·`harness_path2`의 `*.json`)에 rev26:255와 같은 인자로 적용했다.
>
> 이 스크립트는 판정 도구가 아니다. 원 출력의 키 구조를 토큰 경로와 범주로만 목록에 적고, 값은 출력하지 않는다. 그러니 rev26:126의 "436.8 저장 결과에 판정 도구를 돌림"에 해당하지 않는다.
>
> 이어 `list_diff_r5_r6.py`(`e08f5c36…`)로 봉인된 부록 B r5(`9e1831f5…`)와 비교했다. 결과는 종료 <0>, 기록 `list_diff_r5_r6_stdout.json`(sha256 `<…>`)이다. r5 목록에 `harness_path2/p2v5c_merge.json : [["parts","[]","sha256"],"I"]` 한 행만 더해졌다(d 1,020 → 1,021 항목, I 105 → 106. 나머지 범주, 파일 68개, c 13은 같음).
>
> 메인은 이 과정에서 원 출력 파일의 내용을 <열지 않았다 / 다음을 열었다: …>. 이 생성은 4′ 재감사 전, 5단계 전, 결과를 보기 전에 했다.

### 위임 필요·메인 세션 권고
- **메인**: 4절 1~7(r6 목록 생성·점검, `.gitattributes`, 봉인, `t26_identity.json` 재작성, 변형 3 worktree, 4′ 재감사 호출)
- **verif-protocol-auditor** `[시점] 판정 전`(SendMessage로 이어 부르기 권장): 3절 표의 4′ 재실행. 승인 문구 "judge_932f1fb 원 출력에 값 비출력 개수 스크립트 허용"을 포함한다.
- **python-expert**(선택, 감사 위임 필요 그대로): `tools/verif` `rerun_identity` 후보. 정체성 점검을 r6 규범 스크립트 경로를 인자로 받게 만들면 변형 3에 바로 쓸 수 있다.

사용한 스킬: 없음
