# 판 8(436.9) 5단계 G′ V0 사전 실행 — 실행 전 감사 (verif-protocol-auditor, 2026-11-28)

## 감사 요약
- **본 결과**: 판정 대상 결과는 열지 않았다. 5단계 출력은 아직 없다.
  - `j9_runs\56849248\` 아래는 지정한 이름의 존재 여부만 `Test-Path`로 봤다.
  - 봉인 키 `heldout_g_ed8.json`에서 본 것: 줄 수, 설정 이름 분포, `aa_order` 길이 분포, 배치별 서로 다른 job 키 수, 필드 이름. 키 값은 보지 않았다.
  - C8 V0 스모크 줄 두 파일에서 본 것: 키가 있는지만(`key_presence`, 값은 출력하지 않음).
  - `confirm_b_grid192.json`에서 본 것: 필드 이름과 저장 격자 파일 이름 4개.
- **대상·시점·기준 문서**
  - 시점: 실행 전. 대상은 5단계 G′ V0 사전 실행(`ho_v0` 678, `ho_aa2` 339, `ho_aa3` 339 = 1356 run)이다.
  - 실행: C8 `56849248`(worktree `ed8-impl`, 잠김).
  - 판정: T8⁗ `7ea78232`(worktree `ed8-judge4`, 잠김).
  - 기준 문서
    - 규칙 `jp3_remedy_spec_v8_rules.md` `35f9eba8`(`.sha256`과 같음, 개정판 없음)
    - 결정문 `decision_p85_20261128.md` `1742fa05`
    - 키 파일 `heldout_g_ed8.json` `a18b5818`
- **판정: 차단 0 / 실행 전 수정 0 / 기록 19 — 실행 가능.** 기록 항목 가운데 다음 넷은 실행 직후나 판정 전에 메인이 할 일이 있다(메인 세션 권고 1·2·6·7).
  - 기록 8: 오류 줄 점검
  - 기록 12: 판정 명령 고정
  - 기록 14: 경로 2 금지 목록
  - 기록 13: S8-C 표기

## 발견 사항 (심각도순)

차단과 실행 전 수정은 없다. 아래는 모두 **기록**이다.

### [기록][T] 1. 결정문 sha·시각과 (가)·(라-1′) 종결 문장
- **sha**: 결정문 실측 `1742fa0524e70f74…`이다. `p85_options/SHA256SUMS`와 같다(`baseline_check sums` 0).
- **시각과 순서**
  - 첫 커밋은 `0aa6cbb8` `2026-11-28T09:23:30+09:00`이다(`git log -- decision_p85_20261128.md`).
  - 러너 생성은 `run_stage5.ps1:2`의 `2026-11-28T09:27:01+09:00`이다. 결정이 앞선다.
  - 5단계 `.done`·`.stop`·폴더는 모두 아직 없다. `ho_{v0,aa2,aa3}_a1`, `ho_*.done`, `ho_*.stop` 9개가 모두 `False`이다.
  - 러너 `logs\`는 09:27:08에 생긴 빈 폴더다. 그래서 `SkipDone`으로 건너뛸 단계가 없다.
  - **5단계 첫 `.done` 시각과의 대조는 실행 뒤에 한다**(결정문 34행).
- **종결 문장**: `decision_p85_20261128.md:17`에 "5단계 시작으로 (가)(쌍 보충)와 (라-1)·(라-1′)(반사실·그림자 팔)은 닫힌다"가 있다. 진행 결정은 10행 "사용자 결정으로 5단계에 진행한다"이다.

### [기록][E] 2. 5단계 러너와 단계 스크립트는 4단계 `.done`이 있는지만 본다
- **근거**
  - `check_c8.ps1:23-27`(`Test-Path "$RunsRoot\$Name.done"`)
  - `step5_heldout_v0_ed8.ps1:15-18`
  - `common.ps1:225`(`Get-StepFolder` → `.done`의 `folder`)
  - 4단계 판정 상태(미완, P8-5 판정 불가)는 어디에서도 읽지 않는다.
- **빈자리의 기록**: `p85_options_verif.md:101`(R-2)에 적혀 있다. 이 빈자리를 메우는 것은 결정문 10행이다. 결정문 6항은 이 기록을 감사 지시에 넣으라고 한다.
- **남는 점**: 러너·단계 기록 어디에도 결정문 sha가 남지 않는다. 5단계 판정서가 결정문 `1742fa05`를 인용해야 그 연결이 문서로 남는다.
- **6단계도 같은 꼴이다**: `step6_census_ed8.ps1:9-10`의 요구 조건은 `ho_v0` `.done` 하나다. 5단계 판정 상태(frozen/stop/not_judgeable)와 `ho_aa2`·`ho_aa3`는 보지 않는다. 결정문 10행 "6단계는 5단계 판정 뒤 다시 묻는다"가 유일한 연결이다. 6단계 실행 전 감사에서 다시 본다.

### [기록][I·R] 3. job은 V0만이다(VBN 계열 0). 다만 생산자에는 V0 확인이 없다
- **키 파일 실측**(python-dev 즉석 스크립트, 개수만)
  - 339줄이고 `expected_lines`도 339다.
  - `job`의 설정은 VBN 339, `v0_pair.job`은 V0 339다.
  - `aa_order` 전체 후보 2073개가 모두 V0다. 길이 분포는 3이 171, 7이 120, 15가 48이다.
  - 생산자 꼴로 다시 만든 배치: v0 678, aa2 339, aa3 339. 모두 V0이고, 배치 안·배치 사이 중복 job 키가 0개(합 1356 서로 다름)다. job 안에 `mask`·`t4h_dir`는 0개다. CRLF 0, BOM 없음이다.
- **생산자 건조 실행**: `run_v5.py <batch> --jobs-file <키> --list`의 출력은 `ed8_heldout_v0: 678 runs`, `ed8_heldout_aa2: 339 runs`, `ed8_heldout_aa3: 339 runs`(종료 0 셋)이다.
  - dynamics-dev `-I -B`, `NUMBA_CACHE_DIR`는 scratchpad, cwd는 worktree 밖이었다.
  - 실행 뒤 `ed8-impl`의 `status --porcelain --ignored`는 0줄이었다.
- **생산자에 확인이 없는 곳**: `run_v5.heldout_v0_jobs`(`run_v5.py:490-513`)는 `v0_pair.job`·`aa_order[i]`를 그대로 job으로 쓴다. 설정이 V0인지는 확인하지 않는다.
  - "V0만"(210행)은 키 파일의 내용과 sha 고정에 기댄다. sha는 `run_v5.py:466-469, 533-535`, `common_ed8.ps1:128-129, 249-253`에서 고정된다.
  - 판정 도구는 V0가 아닌 줄을 정체성 결함으로 본다(`jp3_ed8_judge.py:212-213, 1106`). 그러나 이것은 실행이 끝난 뒤의 일이다.
  - 지금 키 파일로는 VBN이 섞일 수 없다(위 실측).

### [기록][R] 4. 출력 경로는 새것이다(209행)
- **실행 전 거부 장치**
  - `check_c8.ps1:28-32`: `ho_*_a1`·`.done`·`.stop`이 있으면 거부한다.
  - `common.ps1:221`: `.done`이 있으면 종료 2.
  - `common.ps1:224`: 시도 폴더가 있으면 종료 2.
  - `common_ed8.ps1:258-263`: 출력 파일이 있으면 종료 2.
- `run_part.ps1:11`은 `-Attempt`를 넘기지 않는다. 그래서 다시 돌리면 늘 `_a1` 폴더가 있어 거부된다. 재실행에는 결정이 필요하다.
- **줄바꿈 보호**
  - 앞으로 생길 출력 경로 `j9_runs/56849248/ho_v0_a1/ed8_heldout_v0.jsonl`, `.identity.json`, `ho_v0.done`, `step_record.json`은 `git check-attr text`가 `unset`(-text)이다.
  - jsonl은 ignore 대상이 아니다. npz만 `.gitignore:41`이다.

### [기록][S] 5. 봉인과 키 sha 일치
- **규칙**: `35f9eba8…`가 `.sha256` 첫 토큰과 같다. LF 458줄, BOM 없음, `-text`, 추적 중이다.
- **키 파일**: `a18b5818…`이다. 다음 다섯 곳의 값과 모두 같다.
  - `keys_seal_41e107e9/SHA256SUMS`
  - `run_v5.ED8_KEY_FILE_SHA256`(`run_v5.py:468`)
  - `common_ed8.ps1:129`
  - 판정 도구 `PINNED_SHA256`(`jp3_ed8_judge.py:119`)
  - 단계 스크립트 머리 주석(`step5_heldout_v0_ed8.ps1:9`)
- **도구 결과**(모두 종료 0)
  - `seal_check --repo … --sums keys_seal/SHA256SUMS --rev 0aa6cbb8 --check-tracked --code jp3_ed8_gate_judge.py jp3_ed8_judge.py`: 발견 0. 인용 파일 5개 모두 추적 중이고 ignore 대상이 아니다. 고정 상수는 `jp3_ed8_gate_judge.py:93` 1개다.
  - `baseline_check sums`: `keys_seal_41e107e9` 2항목, `p85_options` 9항목. 불일치·누락·목록 밖 파일 모두 0.
  - `ref_check decision_p85_20261128.md --rev 0aa6cbb8`: 참조 7개 모두 확인, 없음 0.
  - `baseline_check identity`: C8 스모크 폴더 둘(`smoke_v0_56849248`, `smoke_v0twin_56849248`)에 `--expect-commit 56849248…`. 발견 0, 커밋 뒤 바뀐 파일 0.

### [기록][I] 6. 판정 커밋 T8⁗ `7ea78232`는 그대로다. 5단계 판정 경로는 T8″ 뒤로 바뀌지 않았다
- **worktree**
  - `worktree_locks --worktree ed8-judge4 --worktree ed8-impl`: 둘 다 `confirmed`(종료 0).
  - HEAD는 `7ea78232`·`56849248`이다. 두 worktree 모두 `status --porcelain --ignored` 0줄이다.
  - `ed8-impl`의 `HEAD:03_src`는 `ed797e8e…`이고 `$ControllerTree`(`common_ed8.ps1:57`)와 같다.
- **T8″ → T8⁗ 변경 범위**(`git diff 5955f25b 7ea78232`)
  - `jp3_ed8_judge.py`: J-P3 설정 context(262-292, 328-329)만 바뀌었다.
  - `jp3_ed8_gate_judge.py`: P8-0 키만 바뀌었다.
  - `jp3_ed8_rules.py`·`ed8_key_lists.py`: 바뀌지 않았다.
  - 따라서 T8″로 한 C8 V0 스모크의 정체성·A/A 판정 확인(`smoke_v0_report.md:6-16`, `smoke_v0twin_report.md:4-17`)이 T8⁗의 5단계 경로에 그대로 적용된다.

### [기록][I] 7. 실행 정체성: 4단계와 같다
- **mask·workers**: `steps_stage5.json:3-5`는 `-MaskHex 0xFFFF -Workers 8`, `steps_stage4.json:4-10`과 같다. `$RunnerMask = 65535`(`run_stage5.ps1:13`, 4단계 13행)도 같다.
- **환경**
  - 스레드 변수 1개씩과 `MKL_THREADING_LAYER=TBB`, `PYTHONDONTWRITEBYTECODE=1`(`common.ps1:44-50, 165-172`)
  - 인터프리터는 dynamics-dev `python.exe -I -B` 직접 호출(`common.ps1:32, 38`, `common_ed8.ps1:274`)
  - `NUMBA_CACHE_DIR`는 worktree 밖 `…\numba_cache\56849248`(`common_ed8.ps1:101-112, 275`). 4단계에서 쓴 캐시 폴더를 다시 쓴다.
- **job 키에서 mask를 뺀다(규칙 224행과 일치)**
  - `RUNTIME_JOB_KEYS = ("mask", "t4h_dir")`(`run_v5.py:759`)
  - `job_key`가 둘을 뺀다(768-770).
  - 저장 줄의 `job`에서도 둘을 지운다(1201-1202).
  - 판정 도구는 `run_v5.job_key`로 잇는다(`jp3_ed8_judge.py:1143, 1152, 1206`).
- **[추정]** mask·workers가 비트에 영향이 없다는 직접 근거는 이번에 찾지 못했다. 5단계 안의 A/A와 조건 V0는 같은 실행 조건이다. 1차 별칭은 다른 시점에 만든 저장 격자 run의 해시와 비교한다. 비트가 달라지면 별칭이 적게 잡히는 쪽으로만 작용한다.

### [기록][E] 8. run_v5 오류 줄은 종료 0으로 `.done`을 만든다. `log_errors`로는 보이지 않는다
- **근거**
  - `_run_pool`(`run_v5.py:1197-1208`)은 `error` 줄을 쓰고 계속 간다.
  - `Wait-Runs`(`common.ps1:269-279`)는 프로세스 종료 코드만 본다.
  - `log_errors <stage4\logs>`: 종료 0, 단계 10개 모두 `no_errors_line`이다. 실행 도구가 `errors N` 줄을 찍지 않으므로 공허한 관문이다.
- **판정 쪽은 실패 쪽으로 닫힌다**
  - 조건 V0 오류 → `NotJudgeable`(`jp3_ed8_judge.py:1144-1145`)
  - 후보 오류 → `NotJudgeable`(1155-1156)
  - 빠진·중복·여분 줄 → `not_judgeable`(437-458, 1200-1205)
  - 그래서 통과로 새지 않는다. 다만 러너는 `ho_v0`에 오류 줄이 있어도 `ho_aa2`·`ho_aa3`를 이어 돌린다.

### [기록][R·E] 9. 7.3·7.4·7.5와 T8⁗ 도구 대조: 모두 같다. 빈 집합이 통과가 되는 곳은 없다
- 대조 내용은 아래 대조표에 있다.
- **독립 재계산**(합성 입력, `jp3_ed8_rules.py`를 경로로 불러 대조)
  - Jeffreys 사후 예측 $k$ 6건, CP95 상한 5건: 내 구현과 차이 0.
  - 빈 슬롯 → `not_judgeable`, 모두 별칭 → `not_judgeable`
  - $n_E$ 15 → 합침(`n_E < 16`), 합친 N 200 → frozen
  - E A/A 실패 2 → `stop`
  - E 후보가 3회 모두 층이 엇갈림 → `n_AA,E = 0`으로 합침
  - N A/A 기회 0 → `stop`(`n_AA,N = 0`)
  - 기준 실패 50개 → n 190 → `not_judgeable`
  - 후보가 덜 주어짐·`aa_fail` None → `RuleInputError`(메인에서 `setting_defect`, `jp3_ed8_judge.py:1422-1423`)
- **`gate_scan`**(경고 8): 5단계 경로의 `tag_single_compare`(212, 214, 310, 1106)는 다르면 정체성 결함을 내는 쪽이라 거짓 양성이다. `empty_selection_sum_pass`(`jp3_ed8_rules.py:567`)는 8단계 함수이고, 같은 줄의 `n_units == 0` 처리와 575행 `total == 0` → `not_judgeable`이 있어 거짓 양성이다.
- **규칙에서 나오는 성질(결과 아님)**: N층 A/A 실패가 0이어도 CP95 ≤ 0.025가 되려면 $n_{AA,N}$ ≥ 119가 필요하다(0/118 → 0.02507 멈춤, 0/119 → 0.02486). 판정서에 기대 조건으로 적어 둘 만하다.

### [기록][R] 10. 도구 해석 상수는 결정이 있다
- **`AA_MATCH_LAYERS = "original"`(`jp3_ed8_rules.py:54`)과 `AA_SAME_HASH_TRIES_NEXT = False`(58)**: 실행 전 감사 `verif_c8_t8.md:148, 170`이 "사용자 확정"으로 대조했다.
- **A/A 기회는 조건 V0가 기준 통과일 때만 센다**(`jp3_ed8_rules.py:441`). 6.1 "단위 = 기준 통과 ∧ 처리 실패"에서 이끈 해석이다. 규칙 7.4 문면에 직접 쓰여 있지는 않다.
- **군집 키에 깊이·램프가 없다**(`ed8_key_lists.py:404-407`)
  - (나) 슬롯의 1차 별칭은 같은 RE1bF 군집의 저장 run과 비교한다.
  - (다) 슬롯은 새 $F_s$ {1, 3, 6}라 저장 군집이 없다. 그래서 1차 별칭이 될 수 없다.
  - 7.3 "같은 군집 본 위상 run" 문면과 맞는다.

### [기록][E] 11. 판정 도구는 "무시할" A/A 후보도 읽는다(실패 쪽으로 닫힘)
- `slot_inputs`(`jp3_ed8_judge.py:1151-1166`)는 결정된 짝 뒤의 후보도 3회까지 층을 계산하고 오류 줄인지 확인한다.
- 그래서 판정에 쓰지 않는 후보의 `reapproach_starts`가 빠지거나 오류 줄이면 5단계 전체가 `setting_defect`/`not_judgeable`이 된다. 통과로 새지는 않는다.
- 두 스모크에서 C8 V0 사건 줄에는 `event_output.reapproach_starts`가 있었다(기록 19).

### [기록][I] 12. 판정 입력 중 sha로 고정되지 않은 것과, 판정 명령이 아직 고정되지 않은 것
- **저장 격자 파일 4개는 sha 고정이 없다**: 1차 별칭은 `--grid-root` 아래 저장 격자 파일 4개를 이름으로 읽는다(`GridStore`, `jp3_ed8_judge.py:470-483`; `stored_cluster_hashes` 1069-1085).
  - 파일: `touch_phase/acceptance/c4g2_only/grid/grid_r67_main.json`, `grid_r67_top.json`, `grid_r69_bottom.json`, `grid_r69_top.json`
  - `grid_keys`(`confirm_b_grid192.json`)만 sha로 고정된다(121행).
  - 네 파일은 git 추적 중이고 작업 트리에 변경이 없다. 마지막 커밋은 `7320f005`(2026-11-05)다.
  - 작업 트리는 CRLF이고 `-text`가 없다. JSON 해석에는 영향이 없다.
- **판정 명령이 고정되지 않았다**: 5단계 판정 명령(`--v0-rows`·`--step-done` 세 쌍의 순서, `--grid-root`, `--out`, 인터프리터)을 고정한 파일이 없다. 4단계에는 `stage4_prejudge_t8pppp/run_stage4_gates_t8pppp.ps1`이 있었다.
  - 도구가 이미 막는 것: `--out`이 이미 있으면 거부(1415-1417), 파일 수·순서 확인(1229-1240), sha 고정 입력.
  - 그래서 남는 자유도는 `--grid-root`와 출력 위치뿐이다.

### [기록][T·R] 13. D-2 5 표기
- **세 문서에서 글자가 같다**
  - `decision_d2_p80p85_20261127.md:9`
  - `decision_p85_20261128.md:11`
  - `stage4_judgement_ed8.md:109`
  - 표기: "판 8 결과 판정 통과, 구현 확인 P8-5 판정 불가(사용자 결정으로 진행)"
- **뒤 판정서로 이어지는지는 아직 확인할 수 없다**: census·S8-C·G′ 판정서의 틀이 아직 없다. `ed8_design` 아래 md에서 이 표기를 담은 파일은 위 문서와 p85 분석 문서 7개뿐이다.
- `judgement_checklist`는 규칙 파일만 읽는다. 그래서 결정문에만 있는 이 표기는 판정 후 점검에서 자동으로 뽑히지 않는다.

### [기록][R] 14. 5단계와 경로 2 범위(규칙 332행·335행, 4단계 판정서 6절)
- **5단계 줄은 경로 2 J-P3 입력이 아니다**: 경로 2 범위의 G′는 7.6 "전 줄 … J-P3 침범 0(두 경로)", 곧 8단계 VBN 줄이다. 5단계는 V0만이고 ③이 없다(V0는 `T4H_SETTINGS` 밖, `run_v5.py:761-762`). 그래서 5단계 V0 줄은 J-P3 판정 행이 없고 경로 2 입력도 아니다. [추정] 경로 2 G′가 층·별칭을 쓰지 않는다는 읽기다(7.6 문면 "전 줄").
- **그래도 금지 목록에 더해야 할 것**: 335행 범주("경로 1 출력", "감사가 인용한 경로 1 줄")에 드는 다음 것을 4단계 판정서 6절의 목록처럼 경로 2 시작 전 블라인드 목록에 넣어야 한다.
  - 5단계 판정 출력(`ho_k_selection` 보고)
  - 이 감사 보고(`ed8_design/audit_stage5_prerun/`). 판정 도구 줄을 인용한다.
  - 5단계 판정 전 감사 원문
- `j9_runs/56849248/judge_7ea78232/`는 이미 목록에 있다(`stage4_judgement_ed8.md:350`). 5단계 판정 출력을 그 폴더에 두면 기존 항목이 덮는다.

### [기록][T] 15. 오늘 세션 호출 대조(`transcript_scope --with-main --since 2026-11-28T00:00`, 종료 1)
- 블라인드 목록은 비어 있다(`blind_paths.json:3`). 그래서 규칙 위반 판정 대상은 없다. 공개(O 목록)용으로 적는다.
- **compute-scheduler-expert(ab0a1f3c)**: 2026-11-28 09:26:32·09:26:35 KST에 `Glob path=…\j9_runs\56849248` 패턴 `*`·`ho_*`를 썼다. 4단계 출력 폴더의 이름 목록이 보였다. 4단계는 판정·커밋이 끝났다. 같은 에이전트의 Bash 파이프가 1건 있다(09:26:31).
- **메인**
  - Bash 파이프 6건(00:48~09:25 KST, 메모리·도구 README 조회·수정과 09:24:40 worktree 점검)
  - 메모리 파일 덧붙이기에 `cat >> … <<'EOF'` heredoc 2건(00:50, 09:25 KST)
- **서브에이전트 Bash 파이프 4건**: integrity-checker 2, 앞 verif 감사 1(이미 공개됨, `p85_options_verif.md:130`), compute-scheduler 1
- 훅 차단은 0건이다.

### [기록][I] 16. 실행 시간과 예약
- 규칙 7.6 비용 추정은 "5단계 V0 약 680회 1~1.6 h"다. 실제 실행은 1356회다(aa2·aa3를 늘 돌리기로 한 사용자 결정 A-1, `control_t8p_decisions.md:9, 17`).
- 단계 스크립트 추정은 `678 × 143 / 8` ≈ 3.4 h이고, 전체는 약 6.7 h다(`step5_heldout_v0_ed8.ps1:22`).
- 예약 TTL은 360분이고 단계마다 갱신한다(`run_stage5.ps1:32, 124-131, 142`). 가장 긴 단계보다 길다.
- `Wait-Runs`에는 제한 시간이 없다(`common.ps1:271`).

### [기록][I] 17. 자리표시·lint
- **`ps1_lint`**(러너 3개, 단계 스크립트 2개): error 0, warning 0. info 1(`tee_captured_with_return`, `run_stage5.ps1:50`, 정상 패턴)이다.
- **`placeholder_scan --pattern-set both`**(러너 json·ps1 4개, 단계 ps1 2개): 처음엔 종료 1이었다.
  - 걸린 것은 주석 안의 두 개다: `run_part.ps1:4`의 `<part>`, `run_stage5.ps1:95`의 `<LogDir>`.
  - `--allow`로 둘을 허용하면 종료 0(`placeholder_allowed` 2)이다. 실행 자료 안에 채우지 않은 자리는 없다.

### [기록][E] 18. `setting_coverage`(판정 모듈 `jp3_ed8_judge.py`·`jp3_ed8_rules.py`, `--settings-from run_v5.py:ED8_SETTINGS`, `--follow-imports 2`)
- **결과**: 종료 1. `not_covered` 0, `previous_without_current` 0, `patch_misses_binding` 0.
- **`setting_no_role` 6**: `VBNb069`·`VBNb16`·`VBNh05`·`VBNh15`·`VBNd05`·`VBNd15`. 규칙 3.6(156행)에서 기록 설정이다. 정상이다.
- **`closed_by_patch` 2**: `j_p3_inputs.py:39, 67`이 `jp3_ed8_judge.py:280-292`의 context로만 판 8 이름을 받는다. 그 context는 `jp3_of`(328-329)에서 돈다. 5단계 경로는 J-P3를 부르지 않으므로 해당하지 않는다.
- 5단계는 V0만이라, 판정 설정 범위 점검은 기록 3의 키 파일 설정 분포가 본 검사다.

### [기록][I] 19. 판정이 읽는 키가 C8 생산자 줄에 있다(건조 출력 대용)
- run_v5에는 결과를 쓰지 않는 건조 출력이 없다(`--list`는 개수만). 그래서 커밋된 C8 V0 스모크 줄로 대신했다. 이 줄은 `run_v5.run_one`·`_run_pool`·`_write_identity` 경로로 만들어졌다.
- **`key_presence`**: `smoke_v0_56849248\v0_smoke.jsonl`(2줄), `smoke_v0twin_56849248\v0_smoke.jsonl`(3줄)
  - 키: `job.setting`, `job.case`, `controller_tag`, `commands_sha256`, `event_output`, `event_output.reapproach_starts`, `final_phase`
  - 결과: 모두 2/2, 3/3 있다.
  - 내가 판정 키로 잘못 넣은 `ready`는 없다고 나왔다. 판정 도구가 읽는 키가 아니어서 결함이 아니다.
- **T4h 배열 점검은 해당 없다**: V0는 T4h를 쓰지 않는다.
- **꼴의 범위**: 첫 스모크 job은 G′ 조건과 꼴이 다르다(`smoke_v0_report.md:21-26`). twin 스모크가 RE1bF·FS24·G4 사건을 명시한 꼴을 덮는다(`smoke_v0twin_report.md:4-11`).
- **러너의 pwsh 경로**: `run_stage5.ps1:24-28`은 WindowsApps 별칭 경로의 pwsh를 쓴다. 4단계와 같고 4단계는 정상으로 끝났다. 러너를 WMI로 띄우면 바깥 pwsh는 실제 경로로 줘야 한다(전역 규칙 §4).

## 규칙↔도구 대조표 (R)
| 규칙 원문 | 도구 위치(T8⁗·C8) | 판단 |
|---|---|---|
| 210 "5단계는 V0만" | 키 파일 실측 1356/1356 V0; 생산자 `run_v5.py:490-513`(확인 없음); 판정 `jp3_ed8_judge.py:212-213, 1106` | 같음(내용에 기댐, 기록 3) |
| 209 새 출력 경로, 있으면 거부 | `common.ps1:221, 224`, `common_ed8.ps1:258-263`, `check_c8.ps1:28-32` | 같음 |
| 7.3 1차 별칭: 저장 V0 같은 군집 본 위상 run 해시와 같으면 빼고 기록 | `jp3_ed8_judge.py:1069-1085, 1147-1148`; `jp3_ed8_rules.py:462-463, 467` | 같음 |
| 6.3 층(RE1bF·변형, 대각, 0 ≤ t, `round(t, 3)` ≤ 0.450, `fast` 안 읽음, 결측 `setting_defect`) | `ed8_key_lists.py:94-95, 291-346`; `jp3_ed8_judge.py:494-502` | 같음 |
| 7.3 2: $n_E$ < 16이면 N에 합침(A/A 포함) | `jp3_ed8_rules.py:65, 466, 471`(`_layer_counts` merged) | 같음 |
| 7.3 3: 합친 뒤 $n_N$ < 200이면 판정 불가 | `jp3_ed8_rules.py:66, 472-474` | 같음 |
| 7.3 4 (가)·7.4: E A/A 실패 ≥ 2이면 멈춤, $n_{AA,E}$ = 0이면 합침 | `jp3_ed8_rules.py:68, 475-482` | 같음 |
| 7.3 4 (나)·7.4: N CP95 > 0.025이면 멈춤, $n_{AA,N}$ = 0이면 멈춤 | `jp3_ed8_rules.py:70-71, 488-494, 291-310` | 같음(재계산 5/5) |
| 7.3 298: $n_{min}$ 점검이 "해당 없음"보다 먼저 | 5단계 선택에는 해당 없음 상태가 없다. 472행이 맨 먼저 | 같음 |
| 7.4: 같은 층 짝만, 최대 3회, 없으면 기회 없음(기록), 엇갈림 기록, 같은 해시 제외(기록) | `jp3_ed8_rules.py:67, 373-416`; `jp3_ed8_judge.py:1151-1166` | 같음(해석 상수는 사용자 확정, 기록 10) |
| 7.4: V0($o''$) 처리 대 V0($o$) 기준, C-J (i) 항목 전부 | `jp3_ed8_judge.py:1088-1120`(J11은 자기 설정 기록, NB-1 결정 1.4) | 결정된 해석과 같음 |
| 7.5: $k_N$ Jeffreys(+0.5) α 0.025, $k_E$ 1, MDE80, 산출물 항목 | `jp3_ed8_rules.py:69, 72-73, 256-274, 317-338, 498-516` | 같음(재계산 6/6) |
| 7.4 동결 → S8-C | 8단계 `heldout_judgement`가 `selection["status"] == "frozen"`을 요구(540-541), sha는 CLI로 받음(`jp3_ed8_judge.py:1251`) | 같음 |
| 10 상태 순서·판정 행 0 = 판정 불가 | `jp3_ed8_rules.py:81-93`; 메인 1420-1432 | 같음 |

## 확인 필요
- 없음. 규칙 해석에서 새로 생긴 애매한 점은 없다. 기록 10의 해석 상수는 이미 사용자 확정이 있다.

## 위임 필요
- **python-expert: `tools/verif` 후보 1** — 키 파일 배치 설정 집계
  - 입력: 봉인 키 json과 배치 구성식(예: `v0_pair.job`+`aa_order[0]`, `aa_order[1]`, `aa_order[2]`)
  - 출력: 배치별 설정 이름 분포, 서로 다른 job 키 수, 배치 사이 중복 수, job 안 실행 키 수. 값은 출력하지 않는다.
  - 종료: 0 기대와 같음 / 1 다름 / 2 입력 오류
  - 이번에는 즉석 스크립트로 했다.
- **python-expert: `tools/verif` 후보 2** — `key_presence`에 "있으면 안 되는 키" 집계(`--absent-key error` 같은 옵션)
  - 생산자가 오류 줄을 쓰고도 종료 0으로 끝나는 경우를 실행 직후에 잡기 위해서다. 지금 도구는 빠진 키만 센다.
  - `commands_sha256` 결측으로 간접 확인할 수는 있다.

## 메인 세션 권고
1. **각 부분이 끝나면, 판정 전에 줄 상태를 확인한다**: `key_presence.py <ho_*_a1\ed8_heldout_*.jsonl> --key commands_sha256 --key controller_tag --key event_output.reapproach_starts`가 종료 0이어야 한다. 값은 출력하지 않는다. 오류 줄이 있으면 `commands_sha256`이 빠져 종료 1이 된다(기록 8). 종료 1이면 다음 부분으로 넘어가기 전에 멈추고 판단한다.
2. **5단계 판정 명령 파일을 결과를 열기 전에 고정한다**(기록 12). 담을 것:
   - T8⁗ `ed8-judge4`, dynamics-dev `python.exe -I -B`
   - `--keys` `keys_seal_41e107e9/heldout_g_ed8.json`
   - `--grid-keys` `ed6_design/keys/confirm_b_grid192.json`, `--grid-root` 메인 checkout
   - `--v0-rows`/`--step-done` 세 쌍(v0 → aa2 → aa3 순서)
   - `--out`(예: `j9_runs/56849248/judge_7ea78232/ho_k_selection.json`)
   - 그리고 판정 전 감사를 거친다. 판정서에는 저장 격자 파일 4개의 `git hash-object` 값(또는 blob과 clean 상태)을 적는다.
3. **실행은 약 6.7 h다**(기록 16). 전역 §3대로 long-running-task-monitor 점검 모드를 주기적으로 부른다.
4. **5단계 판정서에 적을 것**
   - 결정문 `1742fa05`와 그 커밋 시각
   - 5단계 첫 `.done` 시각과의 순서(결정문 34행)
   - 러너가 4단계 `.done`만 본다는 기록(기록 2)
   - 기록 15의 호출(O 목록)
5. **S8-C 봉인 문서에 D-2 5 종합 표기 문장과 결정문 sha를 넣는 것을 검토한다**(기록 13). 봉인 규칙에 들어가야 `judgement_checklist`가 뒤 판정서에서 그 표기를 자동으로 확인한다.
6. **경로 2를 시작하기 전에 블라인드 목록과 4단계 판정서 6절 꼴의 금지 목록에 넣는다**(기록 14): 5단계 판정 출력, 이 감사 보고(`ed8_design/audit_stage5_prerun/`), 5단계 판정 전 감사 원문.
7. **6단계를 띄우기 전에 확인한다**: 5단계 판정 상태가 `frozen`인지, 그리고 사용자 질문(결정문 10행). `step6_census_ed8.ps1:9-10`은 `ho_v0.done`만 요구한다(기록 2).
8. (선택) `check_c8.ps1 -Phase pre`에 결정문 sha `1742fa05` 확인을 더하면 진행 근거가 러너 로그에 남는다. 러너는 C8 밖이라 C8을 바꾸지 않는다. 고치면 `ps1_lint`를 다시 돌린다.

## 검사하지 못한 것
- **5단계 실제 출력**: 아직 없다. 판정 키가 실제로 나오는지, 첫 `.done`과 결정문의 시각 순서는 실행 뒤에 본다(권고 1·4).
- **mask·workers가 비트에 영향이 없는지 직접 근거**: 기록 7의 [추정]이다.
  - `j9_runs\b46bdf8f`의 json에서 mask 기록을 찾았으나 없었다.
- **`ed7.metric_of`가 V0 줄에서 읽는 키 전체 목록**: 판정 도구를 끝까지 따라가 키를 하나하나 열거하지는 않았다. T8″ 스모크의 끝까지 도는 판정(스텁 없음)과 T8″→T8⁗ 무변경(기록 6)으로 대신했다.
- **경로 2 G′가 5단계 층·별칭 정보를 쓰지 않는다는 점**: 7.6 문면으로만 판단했다([추정], 기록 14).

## 실행한 검증
- **인터프리터**
  - 도구와 즉석 스크립트: python-dev `C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B`(`MKL_THREADING_LAYER=TBB`)
  - 생산자 건조 실행: dynamics-dev `python.exe -I -B`(`PYTHONDONTWRITEBYTECODE=1`, 스레드 변수 1, `NUMBA_CACHE_DIR`는 scratchpad, cwd는 scratchpad)
- **명령**
  - `depcheck.ps1`(STAMP)
  - `source_guard snapshot` / `verify --strict-additions`(입력 19개)
  - `Get-FileHash`
  - git 조회: `log`, `ls-files --eol`, `check-attr text eol`, `check-ignore -v`, `status --porcelain --ignored`, `rev-parse`, `diff --stat`, `diff 5955f25b 7ea78232`, `worktree list`
  - verif 도구
    - `seal_check --sums --rev 0aa6cbb8 --check-tracked --code`
    - `baseline_check sums`(2개)·`identity`(2개)
    - `ref_check --rev --base-dir --exclude j9_runs --exclude .claude`
    - `worktree_locks`
    - `ps1_lint`(5개)
    - `placeholder_scan --pattern-set both`(+`--allow`)
    - `log_errors`(4단계 logs)
    - `key_presence`(스모크 2개)
    - `setting_coverage --follow-imports 2`
    - `gate_scan`
    - `transcript_scope --with-main --since 2026-11-28T00:00 --watch j9_runs/56849248`
  - `run_v5.py ed8_heldout_{v0,aa2,aa3} --jobs-file <키> --list`(3회 종료 0, 실행 뒤 `ed8-impl` `status --porcelain --ignored` 0줄)
  - 즉석 스크립트
    - `keyfile_shape.py`: 키 파일 개수·설정 분포
    - `rules_formula_check.py`: 7.3~7.5 독립 공식·합성 빈 집합 확인. `jp3_ed8_rules.py`를 경로로 불러 대조만 했고, 결과 재집계에는 쓰지 않았다.
  - `-c` 한 줄 두 번: `confirm_b_grid192.json`의 필드 이름·파일 이름
- **만든 뒤 지운 파일**
  - scratchpad `verif-stage5-prerun\`: `guard.json`, `keyfile_shape.py`, `rules_formula_check.py`, `setting_coverage.md`, `gate_scan.md`, `transcript_scope.md`, 빈 `numba\`
  - 폴더째 지웠고 `Test-Path`는 False다. `ed8-impl`·`ed8-judge4`의 `status --porcelain --ignored`는 마지막에도 0줄이었다.
- **이 감사의 행위 공개**
  - `j9_runs\56849248\` 아래는 지정 이름 21개에만 `Test-Path`를 썼다. 열거·Read·Grep은 하지 않았다.
  - `j9_runs\b46bdf8f`에 Grep 1회(glob `*.json`, 패턴 `"mask"|--mask|"workers"`, 내용 모드)를 썼고 결과는 없었다.
  - `ed8_design`에 md 대상 Grep 4회를 썼다(블라인드 없음).
  - Bash 파이프·heredoc은 쓰지 않았다. 프로세스는 종료하지 않았다.
- **에이전트 메모리**: `audit_pitfalls.md`에 "Covariate pre-run (V0-only) stage before a seal" 항목을 더했고, `MEMORY.md` 색인 한 줄을 고쳤다.
- **최종 판정 전 재확인**: `source_guard verify`로 입력 19개의 sha가 바뀌지 않았음을 확인했다. 감사 중 바뀐 파일은 없다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v8_rules.md 35f9eba8…, jp3_remedy_spec_v8_rules.md.sha256 e19aaa48…, decision_p85_20261128.md 1742fa05…, p85_options_verif.md eb5b05a2…, heldout_g_ed8.json a18b5818…, SHA256SUMS dbb4bb1b…, stage4_judgement_ed8.md fb0f4132…, run_stage5.ps1 ad035320…, steps_stage5.json 31af7391…, check_c8.ps1 08b4e524…, run_part.ps1 55f17d62…, step5_heldout_v0_ed8.ps1 528707c9…, common_ed8.ps1 6441b034…, run_v5.py d9afad5d…, jp3_ed8_judge.py c01004b1…, jp3_ed8_rules.py 6d6404ca…, v0_smoke.jsonl 35da6992…, v0_smoke.jsonl acec3aff…, ed8_run_config.json 8c71d03a…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
