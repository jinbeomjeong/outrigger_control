저장 필요: C:\workspace\outrigger_control\06_analysis\02_control\verif_matrix\v5_resume_4368_rules_rev26_erratum3.md
# v5 재개 검증 436.8 규칙 rev26 — 정오 3 (5단계 1회차 멈춤 처리, 도구 커밋 T26′, 2회차 조건) (control-expert, 2026-11-26)

- **대상(봉인본)**
  - rev26 `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev26.md`
    - sha256 `f6591836a205dd52c698bbb613dbe4d74bfdc4b5a318dcb0d7873e9bb02c3b73`
    - `.sha256` `e74aeca93554d65a5e2344142827fa5cafa054153feff7f9d64406233676b80b`
    - 봉인 커밋 `c77b1dcfce9119106838d307302bf8a48a07bff9`
  - 정오 1 `…_rev26_erratum1.md` `5e3bf3e6ec35253cb58dad8ca34383359b43235b314888b4709cd36d24df11f7`(`.sha256` `27f98bae33b70c852ec7c34800cefbf3260e95e541bd700d7c68fe9025b4452f`)
  - 정오 2 `…_rev26_erratum2.md` `ec47e9d51f5b192d58e051d69bb68f75b816ed4836cc7fa39dc066dfef3edec6`(`.sha256` `f840fdc0a7fc51d2ce4219e1f916ba0b52685e15150a270ec6f877bba92d7c61`)
  - 부록 A r6 `rev26_e2_fixed/excl_fields_r6.py` `ce5208a8…`, 부록 B r6 `rev26_excluded_fields_r6.json` `36906ff2…`
  - 5단계 1회차 준비 커밋 master `6c42df04eaa3a13d97b9b27c6d60b29fbe6e5e6d`
  - 1회차 정체성 기록 `rev26_run/t26_identity.json` `e65e611c8bbe04131ad9ade778da463e019ef0f60e910970e1af1e4f6c6a2f7e`
- **날짜**: 2026-11-26
- **상태**: 봉인 전 초안이다. 메인이 `v5_resume_4368_rules_rev26_erratum3.sha256`으로 봉인한다.
- **근거**
  - 메인 확인 사실(5단계 1회차, 아래 E3-1)
  - 경로 2 수정 1 보고 `rev26_impl/path2_fix1_report.md`(sha256 `11684684cbef1f126eed9ed5d544510d4179209b4b980f1803688c7f05978d0d`)
  - 4′ 재감사 `rev26_run/audit_4prime_r2.md`(`8fd5a7dd7dcf7bb77548060ad06932f7fa9da0093c4207a1392f7bc63acf9f32`)
- **근거 결정**: 사용자 결정 2026-11-26. 경로 2 도구를 고친 뒤(수정 1, `rev26-p2` `d6e0630f`) 두 경로를 다시 실행한다.
- **바꾸지 않는 것**
  - 판정 정의, 문턱, 등급 대조 표, 상태 순서, 판정 불가 처리, 5절 실패 처리 표
  - 기대 효과 (a)~(h)의 값. (g)의 HEAD 값만 도구 커밋을 따라 T26′가 된다(E3-4)
  - 1절 범위표, 3절 구현 조건, 부록 A·B(r6 그대로)
  - 정오 1·2의 나머지
  - 1회차 기록(`rev26_run/**`, `rev26_stage5/**`, `judge_rev26_335004a/**`)과 옛 T26 worktree `rev26-t26`
- **요청 밖 추가**
  - ㉠ R26-1 키 정의 확인 문장(E3-2): screen 줄에 `key`가 없으면 `id`를 쓴다. 경로 2 넘김에 [정의] 문장으로 더한다.
  - ㉡ (a)의 키 집합 수는 문자열 키로 센다. `null` 키가 있으면 (a) 불일치다(E3-4).
  - ㉢ 6단계 기록 두 가지(E3-6): 1회차·2회차 경로 1 출력의 정규화 동일성 건수, 1회차 출력 열람 금지.
  - ㉣ `.gitattributes`에 `-text` 줄을 더한다. 대상은 1회차 기록 폴더 `rev26_stage5/**`, 2회차 폴더, 정오 3(E3-8).
  - ㉤ 4′ 권장 항목: 경로 2 실행본 꼴 합성 연쇄 1회(E3-7 6).

## 0. 공개 (2회차 전, 2회차 결과 보기 전)
- **5단계 1회차는 경로 2 도구 결함으로 기대 종료 코드 밖에서 멈췄다.**
  - 시각: 2026-11-26 23:19:34~23:21:01 KST
  - 결함: `p2_u3.py` 종료 3(`stopped: u3: exit 3`)
  - 그래서 (a)~(h) 대조와 rev26 판정 낱말은 만들지 않았다.
  - 경로 1은 끝까지 돌았고(종료 1) 출력이 폴더에 남아 있다. 경로 2는 u3 앞 6단계까지의 출력만 남았다.
- **출력 미열람**
  - 메인 확인에 따르면, 메인은 1회차 출력 json과 비교기 출력 `rev26_stage5/compare_r4_rev26.json`의 값을 열지 않았다.
  - 메인이 본 것은 실행 로그의 끝, 종료 코드, `u3.err`의 오류 추적뿐이다.
  - **이 확인이 2회차의 전제다**(5절 실패 처리 4행 "판정 출력을 본 뒤 다시 실행하지 않는다"에 해당하지 않음). 메인은 본 로그 줄을 판정서에 그대로 공개한다.
  - 그 줄에 판정 낱말(통과·미달·판정 불가 등)이나 판정값이 들어 있었다면 2회차 전에 사용자에게 알리고 결정을 받는다.
- **이 정오의 작성자**(control-expert)는 다음을 열지 않았다: `judge_rev26_335004a/`, `rev26_stage5/`의 파일 내용(파일 이름 목록만 봄), 원 출력, 436.8 저장 결과, 판정서, 판정 후 감사, 부록 B 내용, 블라인드 경로, 경로 1 코드.
- E3-2의 정의 확인 문장(요청 밖 ㉠)은 1회차가 멈춘 뒤에 썼다. 원인은 오류 추적과 코드로 알았다(정렬 TypeError, `None` 키). 판정값은 보지 않았다.
- rev26 0절, 정오 1·2의 공개는 그대로 유효하다.

## 1. 정오 항목 표
| # | rev26(정오) 위치 | 봉인 원문 | 정오 뒤 | 구분 | 근거 |
|---|---|---|---|---|---|
| E3-1 | 5절 실패 처리 2행(:184), 3절 :128 "5단계는 메인이 1회만" | "어느 단계든 종료 코드가 실행본의 기대 종료 코드 표 밖 → 멈춤. 출력 보존. 다시 실행은 사용자 결정 뒤 / 셈" | 1회차에 2행을 적용한다. 1회로 세고, 출력을 보존하고, 사용자 결정(2026-11-26) 뒤 2회차를 한다. :128의 "1회만"은 2행이 허용한 다시 실행 1번으로 대체한다. 2회차도 실패하면 5절 표를 그대로 적용하고, 3회차는 새 사용자 결정 없이 하지 않는다 | 실행 기록 | 메인 확인 사실 |
| E3-2 | 1.1 R26-1(:39) | "`results[].key`(screen) 문자열 그대로" | **[정의]** screen 줄의 키는 저장된 식별 문자열 그대로다. `key`를 쓰고, `key`가 없는(또는 비어 있는) 줄은 `id`를 쓴다(연구 D 꼴). 932f1fb판 `p2_u3.py:214` `r.get("key") or r.get("id")`와 같은 식이다. 파일 이름을 키·suite에 섞지 않는다는 R26-1의 나머지는 그대로다 | 정의 확인 | 요청 밖 ㉠, 수정 1 보고 1·2절 |
| E3-3 | 2절 T26 정의(:62), RD-1 4·5 대체 조건(:84~88), checkout(:70) | T26 = rev26 도구 커밋, worktree `rev26-t26` | 2회차 도구 커밋은 **T26′ = `74c27846cbfab498bd59340d1eaec344f1596b0b`**이고, worktree는 `C:\workspace\outrigger_control\.claude\worktrees\rev26-t26b`(locked)다. 2절과 4′의 "T26"은 2회차에서 모두 T26′로 읽는다. RD-1 4 대체 조건 1~3은 T26′로 다시 확인한다(E3-3 설명) | 실행 설정 | 사용자 결정 |
| E3-4 | 5절 (a)~(h)(:167~174), 부록 A 새 출력 인자(:213) | T26, `judge_rev26_<T26 앞 7자>` | 값은 바꾸지 않는다. (g)의 `head`·`expected_head`·경로 2 `head_check.expect`·`head`와 바뀐 파일의 `M4`=`R4` blob은 T26′ 값이다. 새 출력 인자는 커밋 T26′, 출력 토큰 `judge_rev26_74c2784`, 2회차 실행 창, `--checkout-root` `rev26-t26b`다. (a)의 "V0·VB 키 집합 각 1,114, 짝 1,114"는 문자열 키로 센다. `null` 키가 하나라도 있으면 (a) 불일치다(5절 3행) | 기대 효과(값 불변) | 요청 밖 ㉡ |
| E3-5 | 2절 5단계 실행본(:89~108), 정오 1 E1-1·E1-4 | 1회차 실행본 `rev26_run/run_judgement_path{1,2}_rev26.ps1` | 2회차 실행본은 새 폴더 `rev26_run2/`에 둔다. 1회차 실행본 대비 바뀌는 줄은 E3-5 설명의 줄뿐이다. 출력 폴더 줄은 바꾸지 않는다(`$M4`에서 `judge_rev26_74c2784`가 나온다) | 실행 설정 | 사용자 결정 |
| E3-6 | 4절 6단계(:139), 6절(:190~194) | "판정 도구가 436.8 저장 결과에 돈 횟수 … 1이 아니면 공개" | 이 횟수는 **2**다(1회차와 2회차). 1회차에는 경로 1의 모든 판정 단계와 경로 2의 u3까지의 단계가 저장 결과에 돌았다. 판정서·6단계 보고에 두 회차와 `p2_u3` 결함·수정을 적는다(E3-6 설명) | 기록 | 사용자 결정, 요청 밖 ㉢ |
| E3-7 | 4′(:142~162, 정오 1·2 3절) | — | 2회차 전 짧은 4′ 재확인(3절 표) | 판정 전 점검 | 사용자 결정 |
| E3-8 | 7절, 정오 1 E1-5, 정오 2 E2-10 | — | master `.gitattributes`에 `-text` 줄을 더한다(4절 2) | 기록 보호 | 요청 밖 ㉣ |

### E3-1 설명 (1회차 기록, 메인 확인 사실)
- 준비 커밋 master `6c42df04`, 도구 T26 `335004a7`, 출력 `judge_rev26_335004a/`, 실행 기록 `v5_resume_4368/rev26_stage5/`
- 경로 1: 종료 1, 끝까지 돌았다(실행본 기대표 안)
- 경로 2
  - `p2_u3.py`가 종료 3이었다(기대 0/1/2 밖, `stopped: u3: exit 3`).
  - 끝 관문 문제는 8건이다: u3 종료 3, 그리고 뒤 7단계 미실행.
- `compare_r4.py`: 종료 2(missing 16). 경로 2 출력이 없어서 생긴 결과다.
- worktree와 메인 추적 트리는 실행 전후 모두 깨끗했다. 환경 인벤토리(정오 2 E2-7)도 전후 같았다.
- 적용 행은 5절 실패 처리 2행이다. 3행((a)~(h) 불일치)은 대조 자체를 하지 않았으므로 적용하지 않는다.
- **1회차 낱말**: rev26 낱말 없음(멈춤). 판정서에는 "1회차: 5단계 멈춤(경로 2 `p2_u3` 종료 3), 1회로 셈"으로 적는다.

### E3-2 설명 (R26-1 키 정의 확인, 요청 밖 ㉠)
- **원인**(수정 1 보고 1절)
  - R26-1 첫 구현(`b587a841`)이 screen 키를 `results[].key`만으로 읽었다.
  - 그래서 `id`로 식별되는 screen 줄(연구 D 꼴)의 키가 `None`이 됐다.
  - 이 키가 문자열 키와 함께 정렬되면서 `TypeError`가 났다.
- **정의 확인**
  - 정의 문장 `u3_u6_rerun_rules.md`:19는 screen 키를 `results[].key`로 적는다. 이것을 "screen 줄의 저장 식별 문자열"로 읽는다.
  - 연구 D의 screen 파일은 그 문자열을 `id`에 둔다. 경로 2의 연구 키 목록 `study_keys`도 연구 D를 `results[].id`로 읽는다(수정 1 보고 1절).
  - 932f1fb판 경로 2도 같은 식을 썼다(`p2_u3.py:214`, `git grep` 확인). R26-1이 고치려던 것은 파일 이름을 키·suite에 섞는 일이었고, 식별 문자열을 고르는 방법은 바꿀 대상이 아니었다.
- **경로 2 넘김에 더할 [정의] 문장**: "R26-1 screen 키 = `results[].key`, 없거나 비어 있으면 `results[].id`(저장 문자열 그대로)."
  - 경로 2 수정 1(`d6e0630f`)이 이미 이렇게 구현했다(`records_loc` `r.get("key") or r.get("id")`).
  - 경로 1은 R26-1 대상이 아니다(1.1 표, 경로 2만). 그래서 경로 1 넘김에는 더할 것이 없다.
- `sort_key`(None 안전 정렬)는 결정적 순서를 위한 구현이고 판정 정의가 아니다. None이 없으면 일반 `sorted`와 순서가 같다(수정 1 보고 2절).

### E3-3 설명 (T26′와 RD-1 4 대체 조건, 작성자 git 확인 2026-11-26)
- **T26′의 꼴**
  - `932f1fb` 위의 단일 커밋이다(부모 1개 = `932f1fb`).
  - 트리는 경로 1 `ebda7c0c`의 경로 1 파일과 경로 2 `d6e0630f`의 경로 2 파일을 합친 것이다.
    - `git diff --name-only ebda7c0c 74c27846`은 `path2/`·`path2_v5c/` 13파일뿐이다.
    - `git diff --name-only d6e0630f 74c27846`은 경로 1 파일 7개뿐이다.
  - T26 → T26′: 바뀐 파일은 `path2/README.md`, `path2/p2_u3.py`, `path2/test_rev26_p2.py` 셋(M)뿐이다. 규칙 파일, `rev26_fixed/**`, `.gitattributes`는 T26과 바이트가 같다. 그래서 4′ :146 점검과 2절의 "master 봉인 판과 같은 바이트"는 그대로 성립한다.
- **조건 1**
  - `git diff --name-only 932f1fb..T26′`는 37개이고, T26의 37개와 같은 집합이다. 새 파일이 없다.
  - stdout sha256은 두 커밋 모두 `101cead446974df82fc27b954ec13051b877e7b907828c3da9c8ce4fbc2f333f`로 `t26_identity.json` 값과 같다.
  - 4′에서 고정한 "바뀐 파일 목록"은 그대로다.
- **조건 2**: `git diff --name-only b9f5707..T26′ -- 03_src 02_params` = 0건. T26′ 추적 수는 03_src 141, 02_params 18이다.
- **조건 3**: 허용 목록 29파일(경로 1 14 + 경로 2 15) 가운데 바뀌지 않은 10개는 `932f1fb`와 T26′의 LF 바이트 sha256이 같다. 바뀐 19개는 T26과 같은 집합이다.
- **RD-1 5**
  - worktree `rev26-t26b`: HEAD = T26′, `core.autocrlf=true`, `git status --porcelain` 0줄
  - `v5_options.py` raw sha256 = `d2b903a2a666c97859a4a73b908ebdabe2cef28ae1dd5f47b728527f5762b28e`((g) 기대값)
  - 두 경로 head-check와 실행본 관문은 기대 HEAD와 비교 커밋을 모두 T26′로 본다.

### E3-5 설명 (2회차 실행본, 1회차 실행본 대비 바뀌는 줄)
- **경로 1**(`rev26_run2/run_judgement_path1_rev26b.ps1` ← `rev26_run/run_judgement_path1_rev26.ps1` `3516ea5e…`)
  - 13행 `$M4`, 14행 `$R4` → T26′
  - 26행 `$Judge`, 27행 `$Co`: `…\worktrees\rev26-t26\…` → `…\worktrees\rev26-t26b\…`
  - 21행 `$Out`은 바꾸지 않는다(`judge_rev26_$($M4.Substring(0, 7))` → `judge_rev26_74c2784`).
  - M4 대비로 보면 정오 1 E1-1의 1~8번과 같은 줄이 다르다. 207줄이다.
- **경로 2**(`rev26_run2/run_judgement_path2_rev26b.ps1` ← `rev26_run/run_judgement_path2_rev26.ps1` `a6f0b90c…`)
  - 24행 `$WT` → `C:\workspace\outrigger_control\.claude\worktrees\rev26-t26b`
  - 26행 `$M4`, 27행 `$R4` → T26′
  - `$AllowListPath2`의 두 값을 T26′ blob raw sha256으로 바꾼다.
    - 58행 `path2/README.md` → `cf854f1afedb587c60f7ed6cd38a9aadc67d4165cc5f8e12b0a993f04dddef0c`
    - 60행 `path2/p2_u3.py` → `d9f9280b55535cb6aedbca499532f1a3752b41503a7a15d9104aa2674460f0ff`
  - 나머지 13값은 T26′ blob과 같으므로 그대로다. 키 15개, 순서, 개수 관문 "15 expected"도 그대로다.
  - `$P2`·`$V5c`(39·40행)는 `$WT`에서 따라오므로 줄을 바꾸지 않는다. 431행 `$Out`도 그대로다(→ `judge_rev26_74c2784`).
- `path2/test_rev26_p2.py`는 정오 1 E1-3대로 표에 넣지 않는다. T26′ blob raw sha256 `4430c1cfba25cf30c4ed23f7cfb8679b5f121c8512b7cd81d74444f7ce9525b1`을 2회차 정체성 기록에 적는다.
- **2회차 정체성 기록** `rev26_run2/t26b_identity.json`(1회차 `t26_identity.json`과 같은 꼴). 넣을 것:
  - T26′ 해시
  - RD-1 4 조건 1~3 결과(위)
  - 두 실행본 sha와 1회차·M4 대비 diff
  - `$AllowListPath2` 표
  - worktree·`core.autocrlf`·`v5_options` raw sha
  - 외부 도구 sha(1회차와 같은 값)
  - `input_basis_crosscheck`(1회차 값 + 아래 4′ 3절 5의 확인)
  - `env_inventory_before/after`(정오 2 E2-7 방법)
  - `wt_status_before/after`(rev26 :110)
  - 1회차 기록 참조(폴더, 종료 코드, 메인이 본 로그 줄)
- 2회차 실행 기록 폴더는 새 폴더(예: `rev26_stage5_run2/`)다. 1회차 `rev26_stage5/`에는 쓰지 않는다.

### E3-6 설명 (횟수와 판정서 기록)
- **6단계 횟수(:139)**: "판정 도구가 436.8 저장 결과에 돈 횟수"는 2로 센다.
  - 1회차: 경로 1의 모든 판정 단계, 경로 2의 seal·harness·anchors·jp·g3·d1 단계와 종료 3으로 멈춘 u3 단계, 비교기 `compare_r4.py`
  - 2회차
  - "1이 아니다"이므로 공개한다. 이유는 5절 2행 적용과 사용자 결정이다.
  - 정오 2 E2-6의 범위 밖 실행 2건은 이 횟수에 넣지 않고 그대로 따로 적는다.
- **판정서에 적을 것**
  1. 두 회차의 명령, 시각, 커밋(T26/T26′), 출력 폴더, 종료 코드
  2. 1회차의 멈춤 원인: `p2_u3` R26-1 첫 구현 결함과 `TypeError`
  3. 수정 1(`d6e0630f`)의 바뀐 줄과 시험(경로 2 355 통과, 새 시험이 첫 판에서 실패함을 확인)
  4. E3-2 정의 확인 문장과 그 공개(1회차 멈춤 뒤 작성)
  5. 메인이 1회차에서 본 로그 줄(0절)
- **1회차 출력의 처리(요청 밖 ㉢)**
  - `judge_rev26_335004a/**`와 `rev26_stage5/compare_r4_rev26.json`·콘솔 로그는 보존한다. 판정 낱말과 (a)~(h) 대조에 쓰지 않는다.
  - 판정서 커밋 전에는 sha와 파일 목록만 본다.
  - 6단계 감사자는 판정 뒤 기록으로 1회차·2회차 경로 1 출력을 부록 A r6 규칙(각 회차 자기 인자)으로 정규화해, 같은 파일의 동일성 건수만 낼 수 있다(값 비출력). 경로 1 코드는 두 회차에서 바이트가 같다.

## 2. 두 경로 범위 대조
- 이 정오에서 판정 정의에 닿는 것은 E3-2(R26-1 screen 키 식별 문자열)와 E3-4의 (a) `null` 키 처리뿐이다. 판정 집합, 0건 처리, 상태 이름은 바꾸지 않는다.
- 봉인본 1절(범위)·3절(작성자 조건)과 대조한 결과는 다음과 같다.
  - **경로 2 넘김**: E3-2의 [정의] 문장 하나를 더한다. 구현은 이미 그 문장과 같다(`d6e0630f`).
  - **경로 1 넘김**: 더할 문장이 없다(R26-1은 경로 2만).
  - E3-4의 `null` 키 처리는 6단계 (a) 대조 방법이고, 도구 동작이 아니다.
- 수정 1 작성자(경로 2)는 경로 1 자료를 열지 않았다고 공개했다(수정 1 보고 5절). 4′에서 transcript로 확인한다(3절 표 7).

## 3. 4′ 재확인(2회차 전, verif-protocol-auditor `[시점] 판정 전`)
| # | 항목 | 확인할 것 |
|---|---|---|
| 1 | 정오 3 봉인 | `.sha256` 줄의 sha와 파일 raw sha가 같다. 정오 1·2·rev26·부록 r6 sha는 바뀌지 않았다 |
| 2 | T26′ 대조 조건(E3-3) | RD-1 4 조건 1~3을 T26′로 다시 계산한다(37 같은 집합, stdout sha `101cead4…`; 03_src·02_params 0건, 추적 141·18; 29파일 중 10 LF 같음). T26→T26′ 바뀐 파일이 셋뿐이다. T26′ 경로 1 파일 = `ebda7c0c`, 경로 2 파일 = `d6e0630f`. 규칙 파일·`rev26_fixed/**`·`.gitattributes`가 T26과 바이트가 같다 |
| 3 | worktree | `rev26-t26b`: HEAD = T26′, locked, `core.autocrlf=true`, `v5_options.py` raw `d2b903a2…`, `status --porcelain` 0줄 |
| 4 | 실행본 | 두 2회차 실행본과 1회차 실행본의 diff가 E3-5의 줄뿐이다(경로 1: 13·14·26·27행, 경로 2: 24·26·27·58·60행, 줄 수 같음). `ps1_lint.py` 종료 0. `--tag-mode` 0건. `$AllowListPath2` 15값 = T26′ blob raw sha256이다. 표에 `test_rev26_p2.py`가 없고 "15 expected"가 그대로다. `t26b_identity.json`의 실행본 sha가 파일과 같다 |
| 5 | 입력 기준(B-5) | T26→T26′의 `p2_u3.py` diff(33줄 안팎)가 `--data-root`·`repo`·상대 경로·봉인·HEAD·출력 쓰기 코드에 닿지 않는다(작성자 `git diff -G` 확인 0건, 감사자가 diff를 직접 읽는다). 1회차 4′의 R-5 표는 그대로 유효하다 |
| 6 | 정체성 필드 덮음(:156~162) | **판단: 변형 1~3을 다시 하지 않는다. 경로 2 u3 합성 1회로 충분하다.** 근거: (i) T26′에서 실행본이 닿는 바뀐 바이트는 `p2_u3.py`뿐이다. `README.md`는 도구가 읽지 않고 시험 파일은 실행되지 않는다. (ii) 다른 도구는 `p2_u3`를 import하지 않는다(작성자 Grep: `path2`·`path2_v5c`의 `*.py`에서 시험 파일만 참조). (iii) 그 출력 `u3.json`은 (d)·(c)·(g) 밖이고((a)·(b) 값 대조), 성공 출력에는 `seals`가 없다(첫 4′ R-4). (iv) 나머지 도구와 실행본 줄은 T26판과 바이트가 같다. 그러니 첫 4′와 재감사의 변형 1~3 결과가 그대로 적용된다. **합성 1회의 조건**: 실행본 꼴(cwd = `rev26-t26b`, `--data-root` = 메인 쪽 합성 폴더, 실행본의 u3 인자 목록 그대로)에서, screen `key` 줄, screen `id` 줄(연구 D 꼴), suite 있는/없는 wrapper 줄을 모두 넣는다. 종료가 0/1/2 가운데 하나이고, `u3.json`의 짝 키에 `null`이 없어야 한다(식별자 없는 줄을 넣지 않은 고정물 기준). **권장(요청 밖 ㉤, 관문 아님)**: 경로 2 실행본 꼴 합성 연쇄(u3부터 끝 관문까지)를 1회 돌려 기대 종료 코드표 안에서 끝나는지 본다. 경로 2의 8~14단계는 저장 결과에서 아직 한 번도 돌지 않았다. 첫 4′ 합성은 연구 D 꼴 줄을 덮지 못했다 |
| 7 | 두 경로 독립 | 수정 1 작성자가 경로 1 코드·출력을 연 호출이 0이다. 1회차 출력 `judge_rev26_335004a/`를 연 호출도 0이다(transcript, 첫 4′ R-6 방식) |
| 8 | 판정 도구 실행 횟수 | 436.8 저장 결과에 판정 도구가 돈 기록이 1회차 하나뿐이다(1회차 뒤부터 4′까지 0) |
| 9 | 1회차 공개 | 메인이 본 로그 줄의 기록이 있고(0절), 판정 낱말·판정값이 그 안에 없다. 있으면 멈추고 사용자 결정을 받는다 |
| 10 | 기록 보호 | E3-8 줄이 있다. `rev26_run2/`·정오 3 파일의 `check-attr text` = `unset`. 커밋했으면 LF 파일은 `i/lf w/lf attr/-text`이고, 원 바이트 CRLF 파일(새 conda export를 저장하면)은 정오 2 E2-8과 같이 `i/crlf w/crlf`로 공개한다 |

- 위에 없는 첫 4′·재감사 항목은 다시 하지 않는다. 원 출력 쪽 도구 sha 잎은 `932f1fb` 기준이라 T26′와 무관하다.

## 4. 메인 처리 순서(2회차 전)
1. `rev26_run2/`에 두 실행본과 `t26b_identity.json`을 만든다(E3-5). 1회차 파일은 고치지 않는다.
2. master `.gitattributes`에 다음 `-text` 줄을 더한다(E3-8).
   - `06_analysis/02_control/verif_matrix/v5_resume_4368/rev26_run2/** -text`
   - `06_analysis/02_control/verif_matrix/v5_resume_4368/rev26_stage5/** -text`
   - 2회차 기록 폴더(예: `…/rev26_stage5_run2/** -text`)
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev26_erratum3.md -text`
   - `06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev26_erratum3.sha256 -text`
   - 2회차 출력 `judge_rev26_74c2784/**`는 rev26 7절의 `judge_rev26_*/**` 줄로 이미 덮인다(`check-attr` = `unset` 확인).
3. 이 정오를 봉인한다. 그 다음 4′ 재확인(3절)을 부른다. 지시문에 넣을 것: T26′, `rev26-t26b`, 두 실행본 경로, `t26b_identity.json` sha, 블라인드 경로, "`judge_rev26_335004a/`와 `rev26_stage5/compare_r4_rev26.json` 열지 않음".
4. 커밋 전 `git status --ignored`로 인용 파일이 빠지지 않는지 본다. 2회차 직전에는 메인 추적 트리 0줄, `wt_status_before`, `env_inventory_before`를 확인한다(rev26 :110, 정오 2 E2-7).
5. 2회차: 경로 1은 메인 cwd에서, 경로 2는 자체 `Set-Location`으로 돌린다. 이어서 `compare_r4.py`를 같은 인자로 돌리고, 폴더만 `judge_rev26_74c2784`로 한다. 끝난 직후 `wt_status_after`와 `env_inventory_after`를 적는다.

## 5. 자체 대조(봉인 전)
- **판정·기록 구분**: 1절 "구분" 열에 적었다. 상태 순서(판정 실패 > 설정 결함 > 판정 불가 > 통과)와 판정 행 0 처리는 rev26 그대로다.
- **계산되지 않는 경우**
  - 1회차는 5절 2행(멈춤, (a)~(h) 미계산)이다.
  - 2회차가 다시 기대표 밖에서 멈추면 2행을 적용하고, 3회차는 새 사용자 결정 뒤에만 한다.
  - `null` 키는 (a) 불일치(3행)다.
- **코드 주장 확인**
  - screen 키 식: T26′ `p2_u3.py` diff(`records_loc` `r.get("key") or r.get("id")`, `sort_key` 두 곳), 932f1fb `p2_u3.py:214`(`git grep`)
  - 다른 도구가 `p2_u3`를 import하지 않음: Grep
  - 출력 폴더가 `$M4`에서 나옴: 경로 1 21행, 경로 2 431행 읽음
  - `$AllowListPath2` 행 번호: 경로 2 실행본 57~73행 읽음
- **참조 경로 존재**
  - 있음: worktree `rev26-t26b`, T26′ 커밋, 수정 1 보고, `rev26_stage5/`(이름만)
  - 아직 없음(4절 1이 만듦): `rev26_run2/`와 그 파일
  - 아직 없음(2회차가 만듦): `judge_rev26_74c2784/`
- **항등 지표 점검**: 새 판정 지표를 만들지 않는다. 6단계 1회차·2회차 경로 1 동일성 건수는 기록이고, 같은 코드라 같아야 하는 값이다(구현 확인용).
- **아직 없는 해시**: 정오 3과 그 `.sha256`, 두 2회차 실행본, `t26b_identity.json`의 sha는 메인이 고정한다.

---

## 공개 (봉인본에서 뗌) — 작성자 행위, 확인 결과, 메인 참고

### 작성자 행위(그대로)
- **Read**
  - `rev26_impl/path2_fix1_report.md` 전체
  - `v5_resume_4368_rules_rev26_erratum2.sha256`
  - `rev26_run/audit_4prime_r2.md` 1~60행(그 밖은 Grep으로 절 제목과 판정 줄만)
  - `rev26_run/run_judgement_path1_rev26.ps1` 1~50행, `run_judgement_path2_rev26.ps1` 1~80행
  - `u3_u6_rerun_rules.md` 10~25행
- **Grep**
  - `rev26_impl/path1_report.md`, `path2_report.md`(screen 키 관련 줄)
  - `v5paper_imua_stats/key_collide.json`(키 이름 패턴, 0건). 이어서 PowerShell로 최상위 키 이름과 형만 출력했다(값 비출력).
  - T26′ worktree `path2`·`path2_v5c`의 `*.py`(`p2_u3`, 경로·glob 패턴)
- **git**(Bash)
  - `log`/`rev-parse`, `diff --name-status/--name-only/--stat`(932f1fb·T26·T26′·ebda7c0c·d6e0630f·b9f5707)
  - `diff -U1 T26 T26′ -- path2/p2_u3.py`(경로 2 코드 diff를 읽음. 나는 어느 경로의 작성자도 아니다), `diff -G` 패턴 점검
  - `git grep 932f1fb -- path2/p2_u3.py`, `worktree list --porcelain`, `check-attr`
- **Python**(python-dev `-I -B`, scratchpad `control-rev26e2\`)
  - `t26b_check.py`: RD-1 4 조건, blob sha, worktree 점검
  - `shas3.py`: 인용 파일 sha. `rev26_stage5/`는 파일 이름 목록만 봤다
- **열지 않은 것**
  - `judge_rev26_335004a/`(이름도 열거하지 않음)
  - `rev26_stage5/`의 파일 내용
  - 원 출력, 436.8 저장 결과, 판정서, 판정 후 감사, 부록 B 내용, 블라인드 경로, 경로 1 코드
- **하우스 규칙 위반 공개**: Bash에서 파이프를 두 번 썼다(`git diff --name-only … | sha256sum`, `| wc -l`). git 출력의 해시·줄 수를 세는 데 썼고, 판정 영향은 없다. 그 뒤로는 Python으로 대신했다.
- **상위 폴더 검색**: 상위 폴더를 검색 path로 쓰지 않았다. `ls`는 `verif_matrix` 아래 지정 파일 세 개와 `v5_resume_4368`의 하위 폴더 네 개(`rev26_e2_fixed`, `rev26_run`, `rev26_impl`, `rev26_stage5`)에만 썼다.
- **판정 도구 실행**: 0회. 종료한 프로세스: 없음. 설치: 없음.

### 확인 결과 요약(`t26b_check.py`)
- 조건 1: 37/37 같은 집합. 이름 목록 stdout sha `101cead4…`(T26·T26′ 같음)
- 조건 2: 0건(추적 03_src 141, 02_params 18)
- 조건 3: 29파일 = 바뀌지 않은 10개 LF 같음 + 바뀐 19개
- T26→T26′: README, p2_u3, test_rev26_p2. 경로 1 허용 목록 14개 변화 0. 규칙·`rev26_fixed`·`.gitattributes` 변화 0
- T26′ blob raw sha256(수정 1 보고 값과 같음)
  - README `cf854f1a…`
  - p2_u3 `d9f9280b…`
  - test_rev26_p2 `4430c1cf…`
- 나머지 13값은 1회차 실행본 표 값과 같다.
- worktree `rev26-t26b`: HEAD T26′, `core.autocrlf=true`, `v5_options` `d2b903a2…`, status 0줄

### 확인 필요(메인 → 사용자)
1. E3-2 [정의] 확인 문장(screen `key`가 없으면 `id`)은 요청 밖이다. 사용자 결정 "경로 2 수정 후 재실행"이 이 정의 읽기를 포함하는지 확인을 권한다. 포함하지 않는다면 봉인 전에 문장을 빼고, 수정 1의 해당 줄을 다시 정해야 한다.
2. 1회차에서 메인이 본 로그 끝 줄에 판정 낱말이나 판정값이 있었는지(0절 전제). 특히 경로 1 콘솔 로그 끝이 해당된다.
3. 4′ 3절 6의 권장 합성 연쇄(관문 아님)를 할지.

### 메인 참고
- scratchpad 근거 스크립트: `C:\Users\jinbeom\AppData\Local\Temp\claude\63917d480778c1ba\0d95027e-6012-4053-b99a-1e505935768c\scratchpad\control-rev26e2\t26b_check.py`, `…\shas3.py`(정오 2 시험 파일 `test_r6.py`·`test_r6_out.json`·`make_diff.py`·`shas.py`도 같은 폴더). 근거로 남기려면 프로젝트 근거 폴더로 복사한다.
- 4′ 재확인 지시문에는 블라인드 경로와 함께 "`judge_rev26_335004a/`, `rev26_stage5/compare_r4_rev26.json`·콘솔 로그 열지 않음"을 넣는다.

사용한 스킬: 없음
