# 436.8 rev26 6단계 판정 후 감사 (2회차) — verif-protocol-auditor, 2026-11-27

## 감사 요약
- **본 결과**: 감사용으로 연 파일과 본 값은 다음과 같다.
  - 2회차 출력 `judge_rev26_74c2784/**`(json 전부, `logs/rc.tsv`·`rc_gate.tsv`·gate 파일)
  - 원 출력 `judge_932f1fb/harness_path1`·`harness_path1_retry1`·`harness_path2`(json 전부, `logs/rc.tsv`·`rc_gate.tsv`)
  - 1회차 출력 `judge_rev26_335004a/harness_path1/*.json`(정규화 비교와 `ind_las` 낱말만), `rev26_stage5/stage5_record.json`의 환경 칸
  - 2회차 기록 `rev26_stage5_run2/*` 전부, 원 비교기 결과 `_fixed/compare/compare_r4_result.json`
  - 본 값: H-3·H-4 등급 입력(상태 낱말, 멈춤 코드, 목록 행 수), 비교기 항목 상태와 다른 항목의 세부, 환경 인벤토리 sha, 종료 코드
  - 블라인드는 열지 않았고, 상위 폴더 검색·맨 이름 Glob도 하지 않았다.
- **대상**
  - 2회차: T26′ `74c27846cbfab498bd59340d1eaec344f1596b0b`, 2026-11-27 00:10:53~00:13:06 KST
  - 실행 경로: 드라이버 `~/.claude/runners/outrigger-rev26-stage5-run2/run_stage5_run2.ps1` → 실행본 `rev26_run2/run_judgement_path{1,2}_rev26b.ps1`(`42fdef01`·`2cfae0e9`) → `compare_r4.py`(`8ff3d32b`)
- **기준 문서**: rev26 `f6591836`, 정오 1 `5e3bf3e6`·2 `ec47e9d5`·3 `9d8ae6bc`, 부록 A r6 `ce5208a8`·B r6 `36906ff2`, `t26b_identity.json` `4c110234`. 모두 바뀌지 않았다(source_guard).
- **판정: 차단 0 / 판정 전 수정 0 / 기록 8.**
  - 기대 효과 (a)~(h)가 모두 일치한다. (e)(f)의 합성 부분은 구현 시험과 4′로 확인한 것을 인용한다.
  - 5절 실패 처리 표의 어느 행에도 해당하지 않는다.
  - **rev26 낱말을 확정할 수 있다**(사전 등록 증거로는 세지 않는다, rev26 0절).

## (a)~(h) 대조표
| # | 기대 효과 | 결과 | 근거 |
|---|---|---|---|
| (a) | 경로 2 G-1 = 0, V0·VB 키 집합 각 1,114, 짝 1,114(문자열 키, null 짝 키 = 불일치) | **일치** | `harness_path2/u3.json`: `U-3.stops`에 G-1 0건(멈춤 코드는 G-5·G-6뿐). `counts` 합 V0 1,114·VB 1,114. 짝 키(`differences`) 1,114개 모두 문자열이고 null·빈 키 0. `counts`의 suite 열쇠 `"null"`은 짝 키가 아니라서 세지 않았다(E3-4). 원 출력은 G-1 1건, 짝 1,047이었다 |
| (b) | 경로 2 G-5 키 집합 = 경로 1 원 출력 G-5 집합. 경로 2 S-6·G-6 목록이 원 출력과 diff 0 | **일치** | 새 경로 2 `U-3.G-5_list` 5키 = 원 경로 1 `u3_judge.json :: R4.G-5_list_RD7` 5키. 새 경로 2 `U-3.G-6_list`(3행)가 원 출력과 같다. `harness.json :: bundles.H-3`(S-6 멈춤 20줄 포함)이 NT·NM 정규화 뒤 원 출력과 잎 차이 0 |
| (c) | `ind_las.json`: `state` = `status` = `"기록 완료"`, `markers` = `[]`, 다른 필드 diff 0(c 13 경로 제외) | **일치** | 새 값이 정확히 그렇다. 원 출력에는 세 키가 없다. 나머지 필드는 r6 c 목록(양쪽 13행, S)을 빼고 정규화한 뒤 차이 0이다 |
| (d) | 부록 A r6 범위 모든 출력이 원 출력과 diff 0 | **일치** | 파일 집합이 같다(70 = 70). (d) 대상 67파일, 잎 307,582개 모두 같고 파일별 잎 수도 같다. 원 쪽은 부록 B r6, 새 쪽은 `excl_fields_r6.py`를 새 인자로 돌려 만든 목록(커밋 T26′, 토큰 `judge_rev26_74c2784`, 창 ±2분, checkout-root `rev26-t26b`; d 67파일 1,024행, c 13)을 썼다. 민감도 대조로 원 쪽에 r5 목록을 쓰면 `p2v5c_merge.json :: parts/[0..2]/sha256` 3잎만 갈린다 |
| (e) | R26-3: 436.8 데이터 diff 0. 합성 5건 S-2·4쌍 통과 | **일치** | 데이터: `harness.json :: bundles.H-4`, 경로 1 `r4_inputs.json`·`u3_judge.json`·`record_check.json`이 (d)에서 차이 0이다. 경로 1 r4-inputs의 H-4 멈춤 0. 합성 부분은 두 구현 시험(경로 1 714, 경로 2 355 통과)과 정오 2 E2-4 읽기를 인용한다 |
| (f) | `--tag-mode` 없이 `_IMUA` 줄은 S-2 | 일치(합성) | 두 실행본에 `tag-mode` 0건(4′). 합성 확인은 구현 시험을 인용한다 |
| (g) | 경로 1 `head_check`, 경로 2 `harness.json` `head_check`·`v5_options`(HEAD = T26′, E3-4) | **일치** | 경로 1: `head` = `expected_head` = T26′, `markers` []·`src_params_changed` []·`diff_exit` 0·`exit_code` 0. `blobs[].file` 14개 목록·순서가 원(retry1)과 같다. 바뀐 파일은 `M4` = `R4` = T26′ blob, 안 바뀐 파일은 원 값과 같다. 모든 `same`이 참이다. 경로 2: `head_check` = {expect T26′, head T26′, ok true, why null}. `v5_options.sha256` = `d2b903a2…`(원 값과 같음), `loaded` true, `path`는 NT 정규화 뒤 원 값과 같다 |
| (h) | 봉인 칸 | **일치** | 경로 1: `rules_seal`이 있는 출력 47개 모두 rev26 칸이 있고 sha가 봉인 값이다. `u3_judge.json :: G-3.rules_seal`에도 칸이 있다(값 일치). `rules_seal`이 없는 출력은 정확히 8개다: family_table, h12_t4h_replay, h2_select, h6_L1_reference, h6_r79_judge, log_errors_run_harness, sidecars, u3_judge_k1. 경로 2: `seals`가 있는 11개 출력 모두 `{sha256, want, seal_file_sha}` = `f6591836`, ok. 새 최상위 키 0(경로 1은 `ind_las`의 세 키뿐). 판→sha 지도에 rev26 0 |

- **(d) 범위 밖 출력도 원과 바이트가 같다**: `h1_d1_regraded.jsonl`, `family_table.json.sha256`, `items/*`, `h8_r79_judge/*`, `p2v5c_r79_judge/*` 등 28개가 원 출력과 raw 바이트로 같다.
- **출력 sha 목록**: `sha256_manifest.txt`를 다시 계산했다. 경로 1은 79항목, 경로 2는 19항목 모두 일치하고, 디스크 파일 수와 같다.

## 종료 코드와 실패 처리 표
- **경로 1(종료 1)**
  - `rc.tsv`의 0이 아닌 단계는 7개이고 모두 1이다: k1_class, h12, r4_lists, u3_judge_k1, u3_judge, h8_noise_judge, stage1_judge.
  - 실행본 문면에서 종료 1은 "findings or failures, read their reports"다. 2·3 같은 오류 코드는 없다.
  - 원 판정의 유효 기준(M4 + retry1)과 같은 집합이다. 원 M4 첫 실행의 stage1_judge 2·stroke_H-9 2는 `$Grid` 결함 때문이었고, retry1에서 stage1_judge 1로 고쳐졌다.
  - RUNSTART는 1회이고 시작·끝 관문을 모두 지났다(트리 깨끗).
- **경로 2(종료 0)**
  - `rc_gate.tsv` 14단계가 모두 `expected`이고 원 판정과 같은 열이다.
  - start_gate·end_gate 문제 0, `stopped.txt` 없음
- **비교기(종료 1)**
  - 종료 1 = "a difference"다(입력 오류 2가 아님). 19 같음 / 2 다름 / 결측 0
  - 다른 두 항목은 `RD-10 J11 undecidable / input missing`(H-9 input_missing 경로 1 288 대 경로 2 204)과 `C-9 .. C-11 records`(항목 값 차이)다.
  - `items` 전체가 원 판정 비교기 결과 `compare_r4_result.json`과 **깊은 비교로 같다**. `tool_sha256`, `column_map_sha256`, `baseline_sha256_fixed`, `rule`, `rd13_sha256`도 같다.
  - 두 항목 모두 rev26 범위(H-3·H-4) 밖이고 원 판정에 이미 있던 차이다.
  - 비교기 인자: 드라이버 26행. 기준선 경로와 실행 꼴이 원과 같고 폴더만 새 폴더다(rev26 4절 5단계).
- **실패 처리 표(5절)**
  - 1행(관문 실패)과 2행(기대표 밖 종료): 해당 없음
  - 3행((a)~(h) 불일치): 해당 없음
  - 그래서 rev26 낱말을 낸다.

## rev26 낱말 후보 (판정서가 원 낱말과 나란히 적을 것)
| 묶음 | 원 낱말(M4) | rev26 낱말 후보 | 근거(등급 대조 표 1.2·1.3·2절 H-3·H-4 행) |
|---|---|---|---|
| H-3 | 판정 불가(S-13) | **멈춤, 묻는다**(등급 주지 않음) | **두 경로의 멈춤 표지 집합이 같다.** 표지는 `u3 G-5 묻기`(G-5 5행), `G-6`(3행), `멈춤 S-6`(K1 막힘·균일 연약 20줄)이다. 경로 1은 연구 h9·g6·g8이 `stopped`(G-5 거짓; g8은 G-6도 거짓), `R4.G-5_list_RD7` 5행·G-6 3행, `r4_lists` H-3 `멈춤 S-6`, `k1_class` 해당 줄 20이다. 경로 2는 `U-3.status` stop, `stop_codes` G-5·G-6, `harness` H-3 stop S-6(20줄)이다. 원 판정의 S-13은 경로 2의 G-1 표지(짝 결함) 때문이었는데 이번에 사라졌다. 비교기 JD-2(G-5)·JD-7(G-6)·JD-8(H-3 표지)이 같다. **G-5 목록이 비어 있지 않으므로 u3 원판대로 사용자에게 묻는다**(표 2절 H-3 행) |
| H-4 | 판정 불가 | **통과**(IND_LAS 기록 열 `기록 완료`) | 경로 1: `u3_judge` u6 두 묶음의 관문 G-1·G-2·G-4가 모두 참이다. 436.8 층(1.4)에서 `r4_lists` H-4 markers는 []이고, record_check·k1_class·r4_inputs의 H-4 멈춤·판정 불가는 0이다. `ind_las` `state` = `기록 완료`, `markers` []이므로 1.2 결과 뒤 예외가 적용되지 않는다. 경로 2: `U-6.status` pass, `stop_codes` [], `harness` H-4 pass(멈춤 0, 판정 불가 0). 두 층 최악이 통과다. 비교기 JD-8도 같다 |

- 나머지 묶음의 낱말은 rev26 범위 밖이다. (d) 차이 0이므로 원 판정 낱말 그대로다.
- **rev26 0절**: 이 낱말은 결과 뒤 재판정이다. 사전 등록 증거로 세지 않는다. 원 낱말은 지우지 않고 나란히 둔다.

## 그 밖의 확인
### [기록] P-1 판정 도구가 436.8 저장 결과에 돈 횟수: 2(E3-6, 공개)
- transcript에서 드라이버가 띄워진 것은 두 번뿐이다.
  - 1회차: 메인 `2026-11-26T14:19:32Z` `run_stage5.ps1`
  - 2회차: 메인 `2026-11-26T15:10:48Z` `run_stage5_run2.ps1`
- 그 밖에 판정 도구·실행본을 실데이터에 돌린 셸 호출은 0이다. 감사자들의 실행은 모두 합성(scratchpad)이었다.
- 정오 2 E2-6의 범위 밖 실행 2건(작성자 시험)은 이 횟수에 넣지 않고 따로 적는다.

### [기록] P-2 1회차와 2회차 경로 1 출력의 정규화 동일성(E3-6 ㉢, 값 비출력)
- 방법: 각 회차가 자기 인자로 만든 r6 목록을 썼다.
  - 1회차: 커밋 T26, 토큰 `judge_rev26_335004a`, 창 23:17:34~23:23:01, checkout `rev26-t26`
  - 2회차: 위 (d)와 같은 인자
- **결과: (d) 범위의 경로 1 파일 53/53이 같다**(어느 한쪽에만 있는 파일 0).
- `ind_las.json`의 세 낱말도 두 회차가 같다(`기록 완료`, `[]`).
- `head_check.json`은 (g) 대상이라 세지 않았다. HEAD가 회차마다 다르다.

### [기록] P-3 실행 환경: 인벤토리 계산 방법이 E2-7과 다르다. 환경은 바뀌지 않았다
- **기록값**
  - `stage5_record.json`(1·2회차 모두 전후 같음): python-dev `89bb6bb1…`, dynamics-dev `aa9a3f91…`
  - 4′ 기준값: `b32b783e…`·`c27f109f…`
- **원인**
  - 메인의 상태 스크립트(scratchpad `main-t26\stage5_state.py:24~27`)는 이름 목록만 이어 sha를 낸다(`"\n".join(meta + dist) + "\n"`).
  - identity 방법(E2-7)은 두 머리줄 `# conda-meta`·`# dist-info`를 넣는다.
- **재계산**: 감사자가 지금 두 꼴로 다시 계산했다.
  - 머리줄 없는 꼴은 `89bb6bb1`·`aa9a3f91`로, 메인 값과 같다.
  - 머리줄 있는 꼴은 `b32b783e`·`c27f109f`로, 4′ 기준값과 같다.
  - 건수(280/236, 477/348)도 같다.
- 그러니 환경은 4′ 이후 바뀌지 않았다. 다만 E2-7 "같은 방법으로"는 문자 그대로 지켜지지 않았다.
- 판정서에 두 값과 이 대응을 공개한다(관문 아님).

### [기록] P-4 정체성·봉인·SUMS
- **봉인 sha**: 규칙·정오·부록 r6·`t26b_identity.json`의 sha는 4′ 값 그대로다. 커밋 `09dda89f`(2회차 준비)에 들어 있다.
- **`t26b_identity.json`의 null 칸**
  - `wt_status_before/after`와 `env_inventory_before/after`가 아직 null이다.
  - 실제 값은 `rev26_stage5_run2/stage5_record.json`에 있다: worktree·메인 추적 트리가 전후 모두 빈 줄(무시 파일 포함)이고, 인벤토리는 위 P-3이다.
  - identity를 채워 다시 고정하거나, 판정서에서 `stage5_record.json`을 정본으로 지목한다.
- **미추적인 것**: `judge_rev26_74c2784/`, `judge_rev26_335004a/`, `rev26_stage5/`, `rev26_stage5_run2/`, `rev26_impl/path2_fix1_report.md`
  - 모두 `check-attr text = unset`이고 ignore가 아니다. 출력 합계 41.8 MB이고 단일 파일 최대 10.3 MB라 원격 한도 미만이다.
- **`rev26_post/`는 아직 `-text` 대상이 아니다**(`unspecified`). 이 보고를 저장하기 전에 `.gitattributes`에 `…/rev26_post/** -text`를 더한다.
- **기록 보호 이상**: `rev26_run2/run1_main_seen_output.md`가 `i/mixed w/mixed`다(커밋 `09dda89f`). 1회차 화면 출력 원문을 옮긴 파일로 보이고, 원 바이트를 보존한 것이라면 E2-8처럼 판정서에 공개한다.

### [기록] P-5 E2-5·E2-11 기록 항목
- **E2-5**
  - 경로 1 `record_check.json`의 S-3 줄은 0이다(전체·H-3·H-4 모두).
  - 그래서 최상위 태그 차이로 인한 S-13 위험은 이번 데이터에서 실현되지 않았다.
  - `harness.json bundles.H-4.tags`의 (d) 불일치도 0이다.
- **E2-11 (5)**: merge `parts[].sha256` 3개가 같은 폴더 파트 파일 raw sha와 같다(원 3/3, 새 3/3). 새 쪽은 경로 2 `sha256_manifest.txt` 대조도 일치한다.
- **관문**: H-11 G-3은 두 경로·두 판 모두 참(경로 1 `pass` 참)이고, J_P 재사용도 두 경로 모두 참이다(원과 같음).

### [기록] P-6 정오 1 E1-6 / 정오 2 E2-6 / 정오 3 E3-1·E3-6 공개 항목은 판정서 몫이다(아래 목록)

### [기록] P-7 비교기 종료 1의 두 항목은 원 판정 K-R 처리와 같은 내용이다(rev26 범위 밖)

### [기록] P-8 worktree 상태
- `rev26-t26b`는 감사 뒤에도 `status --porcelain --ignored` 0줄이다.
- rev26 7절에 따라 판정서 커밋까지 `rev26-t26`·`rev26-t26b` lock을 유지한다.

## 판정서에 적을 것 (rev26 6절, 정오 1 E1-6, 정오 2 E2-11, 정오 3 E3-6)
1. 원 낱말과 rev26 낱말을 나란히 적는다: H-3 판정 불가(S-13) → 멈춤·묻는다(G-5 묻기), H-4 판정 불가 → 통과(IND_LAS 기록 완료). rev26 0절 공개 문장(결과 뒤 예외 둘 포함)을 그대로 옮긴다.
2. **H-3 G-5 5행에 대한 사용자 질문**(u3 원판 "묻기")
3. 결함 발견 시점(판정 후 감사 B-2), 원인 코드 줄, 고친 범위, 판정 정의·문턱·등급 표 불변
4. `t26_identity.json`(1회차)과 `t26b_identity.json`, (a)~(h) 대조(위 표), 재판정 명령·시각·sha(드라이버 두 개, `stage5_record.json`, 비교기 결과 `29b17946…`)
5. 판정 도구 실행 횟수 2(1회차 멈춤 원인 `p2_u3` 종료 3, 수정 1 `d6e0630f`, T26′), 범위 밖 실행 2건(E2-6)
6. 정오 3 0절의 1회차 화면 공개. 정오 3 E3-2 정의 확인 문장과 그것을 1회차 뒤에 썼다는 사실
7. 정오 1 E1-6: 경로 1 실행본 기준 M4_retry1(:218), 기록 위치, RD-13 H-4 문구가 R26-3 이전 꼴로 남은 것
8. 정오 2 E2-11: 부록 A r6·diff·부록 B r6 생성·점검 기록, E2-4·E2-5(S-3 0줄), 실행 환경(export 비결정성, 인벤토리 P-3 방법 차이), merge 내부 일치 건수
9. 비교기 19/2/0과 두 다른 항목이 원 판정과 같다는 것
10. 1회차와 2회차 경로 1 정규화 동일성 53/53(P-2)
11. 기록 보호 예외: conda export CRLF 두 파일(E2-8), `run1_main_seen_output.md` mixed(P-4)

## 메인 세션 권고 (판정서 전 할 일)
1. `.gitattributes`에 `06_analysis/02_control/verif_matrix/v5_resume_4368/rev26_post/** -text`를 더한 뒤 이 보고를 저장한다.
2. `t26b_identity.json`의 null 칸 처리를 정한다(P-4): 채우고 sha를 다시 고정하거나, `stage5_record.json`을 정본으로 지목한다.
3. 근거 폴더 SHA256SUMS를 쓴다. 대상은 `rev26_stage5_run2/`, `rev26_stage5/`, `rev26_post/`(저장 뒤)다. `tools\verif\baseline_check.py write-sums <폴더>`를 쓴다. 출력 폴더에는 `sha256_manifest.txt`가 이미 있고 일치한다.
4. H-3 G-5 묻기를 AskUserQuestion으로 사용자에게 묻는다. 그 뒤 control-expert에게 판정서 덧붙임 초안을 맡긴다(위 목록), 이어서 integrity-checker를 돌리고 커밋한다(rev26 4절 7단계).
5. 커밋 대상: 출력 두 폴더, 기록 두 폴더, `rev26_impl/path2_fix1_report.md`, 이 보고. 판정서 커밋 뒤에는 `rev26-t26`·`rev26-t26b` lock을 풀고 worktree를 정리한다(브랜치는 남김).

## 검사하지 못한 것
- (e)(f)의 합성 고정물 부분을 이 감사에서 다시 실행하지 않았다(구현 시험·4′ 결과를 인용).
- 1회차 경로 2 부분 출력(u3까지 7개)은 1회차가 멈춰 비교 대상이 아니므로 대조하지 않았다.

## 실행한 검증
- 인터프리터: python-dev `-I -B`(MKL_THREADING_LAYER=TBB). 판정 도구 실행은 0회다(읽기·정규화·해시만).
- **즉석 스크립트**(scratchpad `verif-rev26-post\`, 보고 전 폴더째 삭제)
  - `appA.py`: 목록 기반 부록 A 비교, 접두 제외, NT·NM, 인자 순서열, K-10 허용오차
  - `checks.py`: (a)(b)(c)(g)(h), manifest, rc
  - `h34.py`, `k1u.py`: H-3·H-4 등급 입력
  - `cmp_items.py`, `cmp2.py`: 비교기 항목, 깊은 비교, 커밋 상태
  - `extra_files.py`, `last.py`, `inv.py`: 인벤토리 직렬화 변형
  - `runs.py`: 드라이버 실행 횟수, transcript 입력
  - `shape.py`
- **규범 스크립트 실행**: `excl_fields_r6.py`를 2회차·1회차 출력에 각 자기 인자로 1회씩 돌렸다. 목록은 scratchpad에 쓰고 지웠다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha v5_resume_4368_rules_rev26.md f6591836…, v5_resume_4368_rules_rev26_erratum1.md 5e3bf3e6…, v5_resume_4368_rules_rev26_erratum2.md ec47e9d5…, v5_resume_4368_rules_rev26_erratum3.md 9d8ae6bc…, excl_fields_r6.py ce5208a8…, rev26_excluded_fields_r6.json 36906ff2…, t26b_identity.json 4c110234…, stage5_record.json 0e19f7a6…, compare_r4_rev26b.json 29b17946…, stage5_driver.log 6eec5e64…, sha256_manifest.txt 06ef3ffa…, sha256_manifest.txt d05ebdc1…, compare_r4_result.json 08691021…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음

## 공개 (행위 그대로)
- **연 것**: 위 "본 결과"에 적은 것. 그 밖에 드라이버 스크립트, 등급 대조 표 28~122행, `compare_r4.py` 1~60행과 Grep 줄, 메인 scratchpad의 `main-t26\stage5_state.py`(Select-String으로 계산 줄만)
- **transcript**: 이 세션의 셸 호출 입력만 봤다(드라이버 실행 횟수).
- **열지 않은 것**: 블라인드(`j9_runs\606f8713\cdry_a1\…`, `prelaunch_j9\ed6_inputs\x11\selection.json`). 판정서와 원 판정 후 감사 문서도 이번 감사에 쓰지 않았다.
- **종료한 프로세스**: 없음
- **지운 것**: scratchpad `verif-rev26-post\` 전체
