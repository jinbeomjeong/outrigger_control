# 판 8(436.9) 5단계 판정(T8⁗ `jp3_ed8_judge.py stage5`) 판정 전 감사 (verif-protocol-auditor, 2026-11-28)

## 감사 요약
- **본 결과**: 판정 대상 값은 열지 않았다. 본 것은 아래 메타뿐이다.
  - 5단계 jsonl 3개: sha256(바이트), 크기·mtime·ctime, `key_presence` 건수(키 9개의 있음·없음·null 수, 값은 출력되지 않음)
  - `ho_*.done`·`step_record.json`·`.identity.json` 전문(메타)
  - `ho_*_a1\logs\*.record.json`·`identity_check.log`(벽시계·CPU·마스크·정체성 점검 요약)
  - 러너 로그(`stage5\logs\` 제어 줄)
  - `judge_7ea78232\` 파일 이름·크기, 그 SUMS sha, `baseline_check sums` 결과(값 json은 열지 않음)
  - 스텝 `.log`·`.err`(run별 `final_phase`·해시를 찍는다)는 열지 않았다.
- **대상·시점·기준 문서**
  - 시점: 실행 전(5단계 run은 끝났고, 판정은 실행 전)
  - 규칙 `jp3_remedy_spec_v8_rules.md` `35f9eba8`(`.sha256` 첫 토큰과 같음), 7.3~7.5·4·10·11.3절
  - 결정문 `decision_p85_20261128.md` `1742fa05`
  - 앞 감사 `verif_stage5_prerun.md` `af3b40b3`
  - 판정 명령 `run_stage5_judge_t8pppp.ps1` `10a8095e`, `grid_blobs.txt` `673d0c92`, `SHA256SUMS` `a3d2b446`
  - 판정 T8⁗ `7ea78232`(ed8-judge4), 실행 C8 `56849248`(ed8-impl)
- **판정: 차단 0 / 실행 전 수정 1 / 기록 14 — 판정 실행 가능.**
  - 실행 전 수정 1(`--out` 위치)은 판정 전에 **정하기만** 하면 된다. 경로를 바꾸든, 지금 경로를 받아들이고 SUMS 처리를 미리 정하든 상관없다.
  - 판정 뒤 할 일은 "판정 뒤 처리 준비" 절에 상태별로 정리했다.

## 발견 사항 (심각도순)

### [실행 전 수정][I·T] 1. `--out`이 4단계의 커밋된 근거 폴더 `judge_7ea78232\` 안이다. 그 폴더 SUMS가 낡는다
- **근거**
  - `run_stage5_judge_t8pppp.ps1:29`: `$Out = Join-Path $RunRoot 'judge_7ea78232\ho_k_selection.json'`
  - `judge_7ea78232\SHA256SUMS`(sha `3e45f5c1…`)는 acba3304에 커밋됐다. 항목은 8개이고 `baseline_check sums` 종료 0이다.
  - 4단계 판정서 `stage4_judgement_ed8.md:394`는 이 폴더를 "8 json(최종)"으로 적는다. `:412`는 "커밋 직전에 SUMS를 쓸 폴더 5"다.
  - 실행 폴더 전체 목록 `RUN_ALL.SHA256SUMS`(`db24b030…`, `:400`)는 `judge_*` 16개를 담는다.
  - 전역 규칙: 판정서가 인용한 근거 폴더에는 뒤늦게 파일을 더하지 않는다.
  - 판정 도구가 막는 것은 judge worktree 안과 단계 폴더 안뿐이다(`jp3_ed8_judge.py:71-72`). 이 경로는 막히지 않는다.
  - 이 경로는 내가 앞 감사 권고 2에서 "예"로 든 것이다(`verif_stage5_prerun.md:250`).
- **같은 꼴이 이미 생긴 곳**: 러너가 `_identity_checks\`에 `ho_*_a1.md` 3개를 더했다. 그 폴더 SUMS(acba3304)는 지금 `sums_unlisted` 3(종료 1)이다.
- **실패 시나리오**: 판정 뒤 다음 둘 중 하나가 된다.
  - 4단계 근거 폴더의 커밋된 SUMS를 고쳐 쓴다. 4단계 판정서 394행 "8 json(최종)"이 낡는다.
  - 목록 밖 파일을 그대로 둔다. `baseline_check sums`가 계속 종료 1이다.
  - 판정 결과는 바뀌지 않는다.
- **권장 조치**(메인, 판정 전에 하나를 고른다)
  - (가) `$Out`을 새 폴더로 바꾼다(예: `j9_runs\56849248\judge_7ea78232_s5\ho_k_selection.json`). 그 뒤 `ps1_lint`, `SHA256SUMS`를 다시 쓴다. ps1 sha가 바뀌므로 판정서에 새 sha를 인용한다. 고칠 사람은 python-expert(작성자)다.
  - (나) 지금 경로를 받아들인다. 그 경우 5단계 판정 커밋 때 `judge_7ea78232\`·`_identity_checks\` SUMS를 다시 쓰고, 4단계 판정서와 다르다는 점을 5단계 판정서에 적기로 미리 정한다.

### [기록][I] 2. `.done`·`step_record.json`은 C8과 맞는다(python-expert가 못 한 사전 대조)
- **필드 대조**: 즉석 스크립트로 메타만 읽었고, 판정 도구 함수는 쓰지 않았다. 세 `.done` 모두 다음을 만족한다.
  - `exit_code 0`, `commit 56849248…`
  - `identity_start`·`identity_end`: head C8, `is_clean true`, `src_tree ed797e8e…`
  - `folder`가 `ho_*_a1`와 같다(resolve). jsonl이 그 폴더 안에 있다.
  - `previous_attempts []`
  - `step_record.json`은 `.done`과 바이트가 같다(sha 같음).
  - 판정 도구 `step_output_problems`(`jp3_ed8_gate_judge.py:168-189`)가 보는 네 조건과 같다.
- **도구 결과**
  - `baseline_check identity --repo ed8-impl <ho_v0_a1> <ho_aa2_a1> <ho_aa3_a1> --expect-commit 56849248… --mtime`: 종료 0, 파일 3, git 블록 6, head 1, dirty 0
  - 러너 자체 점검 `identity_check.log` 3개도 `ok`다.

### [기록][I] 3. 실행 정체성은 4단계와 같다
- **identity 블록**: 세 `.identity.json`의 start·end 블록이 모두 다음과 같다.
  - python `dynamics-dev\python.exe` 3.12.15
  - 스레드 `MKL/OMP/NUMBA/OPENBLAS_NUM_THREADS 1`, `MKL_THREADING_LAYER TBB`
  - `affinity_mask 0xffff`, git head C8 clean
  - `rules_seals` 블록 1종
  - 4단계 7개 단계(`impl_p80·p816·p85·p88·p815·t8·cases`)의 identity 블록과 모두 같다.
- **명령**: `.done` 명령은 `--workers 8 --mask 0xFFFF`, `NUMBA_CACHE_DIR …\numba_cache\56849248`(4단계와 같은 폴더), `dynamics-dev\python.exe -I -B` 직접 호출이다.
- **4단계와 다른 점**: 4단계 `p816·p85·p88·p815`는 `conda run -n dynamics-dev python -I -B`로 불렸다. `p80·t8·cases`와 5단계는 직접 호출이다. 프로세스 안 정체성(인터프리터·버전·스레드)은 같다.
- **판정 도구는 `.identity.json`을 읽지 않는다**(Grep `identity\.json|step_record` 0건; 판정은 `.done`과 줄만 읽는다). 그래서 이 실행 정체성(스레드·마스크·인터프리터)의 대조는 이 감사의 메타 대조가 유일하다. 판정서에 `.identity.json` sha(`696fd2ab…`/`03cdd535…`/`c38d8d25…`)와 이 감사를 인용한다.

### [기록][S·I] 4. 고정 입력 sha가 모두 맞고, 저장 격자 4개는 세 커밋에서 blob이 같다
- **ps1 `$PinnedSha`(36-41행)**: 실측과 8개 모두 같다.
  - 키 `a18b5818`, 격자 키 `4e80e69b`
  - jsonl `fd5f85f5`/`182dcaab`/`a2d65df1`
  - `.done` `c5f2df09`/`6432bccb`/`4669f443`
  - 판정 도구 `PINNED_SHA256`(`jp3_ed8_judge.py:119,121`)·`SPEC_V8_SHA256`(`jp3_ed8_gate_judge.py:93`, `seal_check --const` 일치)와도 같다.
- **저장 격자 4개**
  - `git hash-object` = `grid_blobs.txt`의 blob(`1f88d9c9`/`8797afe1`/`d4f3f8c6`/`33e7508d`)
  - `baseline_check blobs --rev 0aa6cbb8 --rev 56849248 --rev 7ea78232`: 4/4 `same`
  - `status --porcelain --ignored` 0줄
  - 격자 키 192줄의 `v0_pair.file`은 이 4개뿐이다(각 48)
- **`seal_check --quoted <ps1>`**: `quoted_unresolved` 4는 위 40자리 git blob(sha1)이다. sha256이 아니라 미해결로 나온 것이라 결함이 아니다.
- **raw sha256은 줄바꿈에 따라 바뀐다**: 작업 트리는 `w/crlf`, 속성 미지정이다(`ls-files --eol`). ps1의 raw sha256 단언(46-49, 86-87행)은 줄바꿈이 바뀐 checkout에서 종료 5로 거부한다(실패 쪽). 판정서에는 blob, raw, LF 세 값(`grid_blobs.txt:8-11`)을 함께 적는다.

### [기록][R] 5. 명령 파일 ↔ 도구 ↔ 규칙: 모두 같다(대조표 아래)
- **도구 결과**: `ps1_lint`(종료 0, AST), `placeholder_scan --pattern-set both`(종료 0, 미채움 0)
- **사전 거부 시험의 근거**: python-expert의 사전 거부 시험은 지워진 사본으로 했다. transcript의 생성 스크립트 `make_precheck_copies.py`를 읽어 확인한 내용은 다음과 같다.
  - 사본은 `$env:MKL_THREADING_LAYER = 'TBB'`(ps1 101행) 앞에서 잘랐다. 판정 호출 전이다.
  - 결과: `precheck_ok` 0, `badsha` 5, `badblob` 5(11:49:38 KST). 최종 ps1 수정은 11:49:13, 사본 생성은 11:49:31이다.
- **판정이 돌지 않았다는 근거**(지금)
  - `ho_k_selection.json` 없음
  - `numba_cache\judge_7ea78232_stage5` 없음
  - ed8-judge4 HEAD `7ea78232`, `status --porcelain --ignored` 0줄
  - `worktree_locks`(ed8-judge4·ed8-impl, 전체 경로): 둘 다 `confirmed`, 종료 0

### [기록][E] 6. 종료 2는 세 경우를 합친다
- **세 경우**
  - `setting_defect`
  - `not_judgeable`
  - argparse 오류 또는 `--out`이 이미 있음(이때는 판정 출력을 쓰지 않음, `jp3_ed8_judge.py:1415-1417, 1433-1434`)
- **나누는 법**: 메인은 stdout 마지막 JSON의 `status`와 `--out` 파일 유무로 나눈다. ps1이 `--out`이 있으면 미리 거부하므로, 종료 2인데 `--out`이 없으면 인자 오류다.
- **not_judgeable의 두 갈래**
  - 입력 쪽(`status_basis.not_judgeable`: 파일 수, 빠진·중복·여분 줄). 슬롯 계산 전에 돌아온다(1204-1205). 값이 없다.
  - 선택 쪽(`reasons`의 `n_N … < 200`, `jp3_ed8_rules.py:472-474`). 수가 계산된 뒤다. 공개 문구가 다르다.

### [기록][T] 7. 시간 순서
- **시각**
  - 결정문 첫 커밋 `0aa6cbb8` 2026-11-28T09:23:30+09:00
  - `check_pre` 10:44:14
  - `ho_v0` 시작 10:44:17
  - 첫 `.done`(`ho_v0`) 11:12:27
  - `timeline.py`(규칙·결정문 ↔ `step_record.json` `started`): 6/6 `before`. `seal_time_missing` 2는 `.sha256`에 시각이 없어서이고, git 시각으로 대신했다.
- **jsonl mtime은 각 단계 창 안이다**

  | 파일 | mtime | 단계 창 |
  |---|---|---|
  | `ho_v0` jsonl | 11:12:26.345 | 10:44:17~11:12:27 |
  | `ho_aa2` jsonl | 11:27:02.674 | 11:12:29~11:27:04 |
  | `ho_aa3` jsonl | 11:41:38.401 | 11:27:07~11:41:39 |

  ctime은 모두 단계 시작 3~5 s 뒤다.
- **판정 명령 파일**
  - 만든 시각: Write 11:48:46, 마지막 Edit 11:49:13(transcript), mtime 11:49:13, `grid_blobs.txt` 11:50:02, SUMS 11:50:23
  - 마지막 `.done`(11:41:39) 뒤다. 출력 sha를 고정해야 하므로 당연하다.
  - 판정 출력보다 앞선다(출력 아직 없음).
- **약한 고리**
  - `stage5_prejudge\`는 미추적이다(`baseline_check sums`: `cited_untracked` 3, 해시 불일치 0). 4단계도 같았다(`stage4_prejudge_t8pppp`는 판정 커밋 acba3304에 함께 들어감).
  - 판정 report에는 시각 필드가 없다(`main` 1426-1427: command, spec sha, run commit, `judge_code`).
  - ps1은 stdout을 파일로 남기지 않는다.
  - 그래서 "명령 → 출력" 순서의 근거는 mtime, transcript, 이 감사뿐이다(권고 3).

### [기록][E·I] 8. 오류 줄 0. V0 정체성 키가 판정의 기대와 맞는다(있음·없음만)
- **`key_presence` 결과**(678/339/339줄, 셋 다 같은 꼴)

  | 키 | 결과 |
  |---|---|
  | `commands_sha256`, `controller_tag`, `event_output.reapproach_starts`, `job.setting` | 전 줄 있음 |
  | `error` | 전 줄 없음 |
  | `hydraulic_options`, `hydraulics_record` | 전 줄 null |
  | `ed8_settings`, `lsb_record` | 전 줄 없음 |

- **뜻**
  - 오류 줄은 `commands_sha256`이 없다(`run_v5.py:942-944, 964-966`). 그래서 전 줄 있음 = 오류 줄 0이다.
  - null·없음의 꼴은 `v0_identity_problems`(`jp3_ed8_judge.py:217-224`)가 기대하는 V0 꼴이다. 태그 값·설정 값 자체는 보지 않았다.

### [기록][E] 9. `log_errors`는 공허한 관문이다
- `log_errors <stage5\logs>`: 종료 0, 로그 7개 모두 `no_errors_line`이다(앞 감사 기록 8과 같음).
- 스텝 `ho_*_a1\logs\ed8_heldout_*.log`에는 `_run_pool`(`run_v5.py:1206-1208`)이 run마다 `final_phase`·해시 앞 8자·wall을 찍는다. **판정 값이 든 로그다.** 그래서 `log_errors`·Read 대상에서 뺐다. 경로 2 금지 목록에도 넣는다(권고 6).

### [기록][I] 10. 실행 시간은 추정의 0.14배였다
- `record.json` `actual_over_estimate`: 0.139 / 0.144 / 0.143. CPU-s/run은 약 18.6(v0)이다.
- 규칙 7.6 비용 추정 "680회 1~1.6 h", 단계 스크립트 추정(143 s/run)보다 짧다.
- 완결성과 오류 줄은 위에서 확인했다. [추정] 판정 절차에는 영향이 없다.
- `record.json`의 `note`가 "436.9 J4a step ho_v0"로 적혀 있다(이름표만 틀림, 기록).

### [기록][I] 11. 5단계 SUMS가 없다. `<S8C_V0_PRERUN_SUMS_SHA256>`의 대상이 정해지지 않았다
- `ho_*_a1`에는 SUMS가 없다. 하위 폴더 `logs\`와 빈 `judge\`가 있다.
- `write-sums --dry-run`(선택 없음)은 `refused_subfolders`, `--recursive`는 항목 8(v0)이다.
- 규칙 11.3은 SUMS **하나**의 sha를 요구한다. 단계 폴더 3개와 `.done` 3개를 한 목록으로 묶을지, 단계별 목록 셋으로 할지 정해야 한다(확인 필요 1).
- 판정에는 영향이 없다. 판정 전에 써 두면 run 출력 고정 시각이 판정보다 앞선다는 근거가 된다(선택).
- 크기: 10^8 B를 넘는 파일 없음(최대 4.56 MB). ignore 대상 없음(`check-ignore` 종료 1). 모두 `-text`.

### [기록][T] 12. 오늘 10:30 이후 호출 대조(O 목록용)
- **도구 결과**: `transcript_scope --with-main --since 2026-11-28T10:30 --watch j9_runs/56849248`: 종료 0, watched 6, Bash 파이프 메인 0·서브 0, 훅 차단 0, 블라인드 목록 비어 있음
- **판정 대상 출력 근처 호출(값 출력 없음)**

  | 시각(KST) | 주체 | 내용 |
  |---|---|---|
  | 10:59:45~11:00:06 | long-running-task-monitor af9863b2 | `j9_runs\56849248`·`ho_v0_a1`·`logs` 이름 목록. `Get-Content ed8_heldout_v0.jsonl \| Measure-Object -Line`(내용을 파이프로 읽고 줄 수만 냄, 376줄) |
  | 11:14:52 | 같음 | 같은 꼴, aa2 53줄 |
  | 11:29:44 | 같음 | 같은 꼴, aa3 57줄 |
  | 11:14:34, 11:29:29, 11:44:34 | 메인 | `key_presence` 3회(값 없음), 러너 로그 |
  | 11:45:14~11:45:28 | compute-scheduler aaa89835 | `j9_runs\56849248` 아래 `*.sample.json` 재귀 목록, `ho_v0_a1\logs\*.sample.json`·`*.record.json`·`ho_v0.done` 머리·러너 로그 읽기(메타) |
  | 11:45~11:50 | python-expert aa2e704f | 출력 6개 sha(바이트), 격자 키 `v0_pair.file` 이름, `stage5 --help`, 사전 거부 사본 시험. `step_records.py`(판정 도구 `step_output_problems` import)는 자동 모드 분류기가 거부해 실행되지 않음 |
  | 11:55~ | 이 감사(ab55ca9d) | 메타 읽기와 이름 목록. "실행한 검증" 참조 |

- 스텝 `.log`·`.err`, jsonl 줄 내용, `judge_7ea78232` json 값을 연 호출은 10:30 이후 transcript에 없다. Read·Get-Content 대상과 도구 입력 문자열을 대조했다.

### [기록][R] 13. 결정문 6항 지시 항목 확인
- **결정문 sha·시각**: 기록 7
- **러너가 4단계 `.done`만 본다**: 앞 감사 기록 2가 그대로다. 5단계 러너도 판정 상태를 읽지 않는다. 6단계 `step6_census_ed8.ps1`도 `ho_v0.done`만 요구한다.
- **V0만**: 기록 8, 앞 감사 기록 3
- **새 출력 경로**: `ho_*_a1`, `previous_attempts []`, `.stop` 없음
- **T8⁗ 그대로**: 기록 5
- **D-2 5 표기**: 아직 이어지지 않았다. 5단계 판정서 틀이 없다. `judgement_checklist`는 규칙 파일만 읽는다. 그래서 5단계 판정서에 글자 그대로 옮기고, 판정서 커밋 전 감사에서 손으로 대조해야 한다(앞 감사 기록 13).

### [기록][R] 14. 7.4·11.3·4절 순서: frozen이어도 S8-C 봉인은 census(6단계) 뒤다
- 규칙 4절 표(202-204행): 5(G′ V0 사전 실행, 기록) → 6 census(관문) → 7 S8-C.
- 7.4(305행)는 "$x_{AA}$·$n_{AA}$는 5단계 값으로 동결하고 S8-C에 봉인"이다. 봉인 시점은 7단계다.
- 결정문 10행에 따라 6단계 시작 전에 사용자에게 묻는다.
- 8단계 판정은 `selection["status"] == "frozen"`을 요구한다(`jp3_ed8_rules.py:540-541`, 앞 감사 대조표). frozen이 아니면 G′가 판정되지 않는다.

## 규칙↔도구 대조표 (R)

| 항목 | 규칙·결정 | 명령 파일(`run_stage5_judge_t8pppp.ps1`) | 도구(T8⁗) | 판단 |
|---|---|---|---|---|
| 하위 명령 | 7.3~7.5 | 109 `stage5` | `COMMANDS` 1374, 파서 1385-1389 | 같음 |
| `--keys` | 7.2 키 파일 `a18b5818` | 31, 34, 110 | `sealed_lines(…,"heldout_keys")` 1189, `PINNED_SHA256` 119 | 같음 |
| `--grid-keys` | 7.1 `confirm_b_grid192.json` | 32, 35, 111 | `pinned(…,"grid_keys")` 1190, 121 | 같음 |
| `--grid-root` | 7.3 "저장 V0 같은 군집 run" | 112 `$MainRoot`, 격자 4개 blob·raw sha·clean 단언 76-89 | `GridStore` 470-483(고정 없음, 이름으로 읽음), `stored_cluster_hashes` 1069-1085 | 같음(고정은 ps1 쪽) |
| `--v0-rows`/`--step-done` 순서 | 결정 A-1: v0 → aa2 → aa3 | 113-115 | `STAGE5_BATCHES` 1218, `stage5_completeness` 1229-1240(개수·순서·줄 단위), 짝 수 1191-1192 | 같음 |
| 단계 기록 | 4·209 새 경로, C8 | `.done` sha 단언 37, 39, 41 | `checked_step`(`gate` 192-206): exit 0, commit, end identity, 폴더 안 | 같음(이 감사 기록 2에서 미리 확인) |
| `--out` | 새 파일, 덮어쓰지 않음 | 29, 92(있으면 5) | 1415-1417(있으면 2), `open("x")` 1429 | 같음. 위치는 실행 전 수정 1 |
| 판정 env | dynamics-dev `-I -B` | 26, 109, cwd = judge 루트 106 | docstring 71 | 같음 |
| `NUMBA_CACHE_DIR` | 새 폴더 | 30, 93(있으면 5), 103 | – | 같음(지금 없음) |
| 판정 checkout 점검 | locked, clean | 전 57-66, 후 127-138(4) | `code_identity` 209-223(report에 head·clean) | 같음 |
| 종료 0/1/2/3 | 10: 실패 > 설정 결함 > 판정 불가 > 통과, 7.3·7.4 멈춤 | 14-22 | docstring 57-69, `EXIT_OF_STATUS` 108, `gate` 88-90, 1432-1438 | 같음(2는 세 경우를 합침, 기록 6) |
| 종료 4/5 | – | 4 = 판정 checkout 변경·사후 점검 git 오류·시작 실패, 5 = 사전 거부(아무것도 쓰지 않음) | – | ps1 고유 |
| 상태 | 7.3 3(n_N < 200 판정 불가), 7.3 4·7.4(멈춤), 7.5(동결) | – | `stage5_selection` 447-495: `not_judgeable`/`stop`/`frozen` | 같음(앞 감사 재계산 5/5·6/6) |

## 판정 뒤 처리 준비 (메인, 상태별)

모든 상태에 공통이다.
- stdout 마지막 줄 JSON `status`와 ps1 종료 코드를 함께 적는다.
- `ho_k_selection.json`(또는 바꾼 경로)의 sha256을 바로 잰다.
- ed8-judge4 사후 점검(ps1이 함)이 0줄인지 확인한다.
- 경로 2 금지 목록(권고 6)을 넣는다.
- 판정은 다시 돌리지 않는다. 다시 돌리면 같은 결과라도 새 `--out`과 새 numba 폴더가 필요하다. 다시 돌린 사실은 공개한다.

| ps1 종료 | 상태 | 규칙 | 메인이 할 일 |
|---|---|---|---|
| 0 | `frozen` | 7.4 305, 7.5, 11.3, 4절 | 1. `ho_k_selection` sha → `<S8C_HO_K_SELECTION_SHA256>` 후보. 층별(또는 합친) $n$·$x_{AA}$·$n_{AA}$·CP95·$k$·MDE80·`merged`·`merged_why`가 들어 있는지 키 이름으로 확인한다.<br>2. 합쳤으면(`merged`) "E 기전 결과(원래 E 단위 실패 수)" 기록이 있는지 확인한다(7.3 2).<br>3. `<S8C_V0_PRERUN_SUMS_SHA256>` 목록을 쓴다(기록 11, 확인 필요 1).<br>4. 예측 문장 `<S8C_HO_PREDICTION>`(7.5 316, P8-13)을 S8-C 전에 만든다.<br>5. 5단계 판정서를 쓰고 커밋 전 감사를 받는다.<br>6. **6단계 census 진행은 사용자에게 묻는다**(결정문 10행).<br>7. S8-C 봉인은 census 통과 뒤(4절 7단계)다. 8단계 뒤 $k_N$은 2차 별칭 반영으로 다시 계산될 수 있다. 그러면 두 값을 다 적는다(7.5 312). |
| 1 | `stop` | 7.3 4, 7.4 307-308, 4절 208 | 멈추고 묻는다. 재실행하지 않는다. `reasons`(E A/A ≥ 2, $n_{AA,N}$ = 0, CP95 > 0.025)를 그대로 전한다. S8-C와 8단계로 갈 수 없다(8단계는 frozen을 요구한다). 6단계도 사용자 결정 전에는 띄우지 않는다. A/A 값을 본 것이 된다. 그 뒤 규칙을 바꾸면 결과 본 뒤의 개정으로 공개한다. |
| 2 | `not_judgeable`(입력 쪽: `status_basis.not_judgeable`) | 4절 209, 10 346 | 슬롯 계산 전에 멈춘 것이라 값이 없다. 사유(파일 수·빠진·중복·여분 줄)를 전하고 묻는다. 5단계를 다시 돌리려면 사용자 결정과 새 시도 폴더가 필요하다(`run_part.ps1`은 `-Attempt`를 넘기지 않는다, 앞 감사 기록 4). |
| 2 | `not_judgeable`(선택 쪽: `reasons` `n_N < 200`) | 7.3 3 | 멈추고 묻는다. 수를 본 것이 된다. 문턱은 바꾸지 않는다. 다음 처리(원천 확대 등)는 다음 판 문제로 사용자에게 묻는다. |
| 2 | `setting_defect` | 10 345, 결정문 17 | `status_basis.setting_defects`와 `identity_defects`(메타)만 읽고 묻는다.<br>- 실행 쪽(정체성·단계 기록·층 입력 `reapproach_starts` 결측)이면 5단계를 다시 돌릴지 사용자가 정한다.<br>- 판정 쪽(`RuleInputError`, 도구 해석)이면 T8 변경이다. 감사(P8-11)를 거쳐 새 `--out`으로 다시 판정한다. 그 경우 4단계 판정도 T8 교체에 걸리는지 본다. |
| 2 | (출력 없음) | – | argparse·인자 오류다. 명령 파일을 고친다. sha가 바뀌므로 짧은 재감사를 받는다. |
| 3 | `error` | – | traceback을 python-expert에 넘긴다(위임). `--out`이 생겼는지 확인한다. 생겼으면 새 경로로 옮긴다. 도구를 고치면 T8 변경 → 감사. |
| 4 | – | – | 판정 checkout이 바뀌었거나 사후 점검이 실패했다. 출력이 있어도 판정 근거로 쓰지 않고 묻는다. |
| 5 | – | – | 아무것도 쓰지 않았다. 사유가 환경(numba 폴더가 있음 등)이면 고치고 같은 ps1을 다시 돌린다. **고정 sha 불일치**(입력이 감사 뒤에 바뀜)면 멈추고 원인을 찾는다. |

**5단계 판정서에 적을 것**(앞 감사 권고 4 + 이번)
1. 결정문 `1742fa05`와 커밋 시각 09:23:30. 5단계 `check_pre` 10:44:14, 첫 시작 10:44:17, 첫 `.done` 11:12:27(결정문 34행).
2. 러너·단계 스크립트가 4단계 `.done`만 본다는 기록(앞 감사 기록 2). 6단계도 같다.
3. 판정 명령 `run_stage5_judge_t8pppp.ps1` sha(지금 `10a8095e`, 실행 전 수정 1로 바뀌면 새 값), `SHA256SUMS` sha, 작성 시각(기록 7). 미추적이었다는 점.
4. **grid blob 인용**: `grid_blobs.txt` `673d0c92`의 4줄.
   - (hash-object = HEAD blob, raw sha256, LF sha256, bytes, path)
   - main HEAD `0aa6cbb8`, 마지막 수정 커밋 `7320f005`(2026-11-05), clean
   - 세 커밋 blob 같음(기록 4)
   - 판정 도구는 이 파일들을 고정하지 않고 ps1이 고정한다는 점
5. 입력 sha: 키 `a18b5818`, 격자 키 `4e80e69b`, jsonl 3, `.done` 3, `.identity.json` 3(기록 3), `_identity_checks\ho_*_a1.md`(`176cafb8…`/`c17c3fde…`/`ea07a503…`).
6. 판정 report의 `judge_code`(head·clean)와 ps1 사후 점검 결과. 판정 시각(report에 없으니 콘솔 로그나 mtime, 권고 3).
7. 실행 정체성(기록 3)과 4단계와의 차이(`conda run` 4단계 일부).
8. 기록 10의 실행 시간, 기록 9의 `log_errors` 공허.
9. 상태별 내용: frozen이면 층별 값과 합침 여부·사유, E 기전 결과(합쳤을 때). `aa_item_scope`, `aa_j11_states`(기대 "입력 없음"), `aa_shape_record`(stats Q-3), 1차 별칭 목록 수.
10. 7.4 공개 문장(309행)과 13절 14.
11. O 목록: 앞 감사 기록 15 + 이번 기록 12. 판정 뒤 메인 열람도 더한다.
12. D-2 5 표기 글자 그대로(기록 13).
13. 이 감사 sha(메인 저장 뒤).

## 확인 필요
1. **`<S8C_V0_PRERUN_SUMS_SHA256>`가 가리킬 목록**: 다음 둘 중 하나를 정해야 한다. 정해지지 않으면 S8-C의 그 자리를 채울 수 없다.
   - (가) `j9_runs/56849248/` 아래 5단계 전체(`ho_*_a1/**`, `ho_*.done`)를 한 목록으로(`--base repo-root` 또는 실행 폴더 상대)
   - (나) 단계 폴더마다 `--recursive` 목록 셋. 이 경우 S8-C에 셋을 적도록 문면 해석이 필요하다.
   - 11.3은 단수다. 그래서 (가)가 문면에 가깝다고 본다.
2. **실행 전 수정 1의 (가)/(나) 선택**.

## 위임 필요
- **python-expert**: 실행 전 수정 1에서 (가)를 고르면 `$Out` 한 줄 수정, `ps1_lint`·`placeholder_scan`, `SHA256SUMS` 다시 쓰기. (나)면 할 일 없음.
- **python-expert: `tools/verif` 후보** — 단계 기록 사전 대조(`step_check`)
  - 입력: `.done` 경로와 기대 커밋, 출력 경로
  - 출력: exit_code·commit·identity_start/end head·clean·folder 포함 여부·`previous_attempts`·step_record 바이트 같음
  - 종료 0/1/2
  - 이유: 판정 도구 함수를 import하지 않는 독립 점검이다. 이번에 자동 모드 분류기가 판정 도구 import 방식을 막았다. 이번에는 즉석 스크립트로 했다.

## 메인 세션 권고
1. 실행 전 수정 1을 정한 뒤 `run_stage5_judge_t8pppp.ps1`을 실행한다. 판정 전 입력 sha가 바뀌지 않았는지는 ps1이 단언한다.
2. (선택) 판정 전에 5단계 V0 사전 실행 SUMS(확인 필요 1)를 `write-sums --recursive`(또는 `--base repo-root` 목록)로 쓴다. 그러면 run 출력 고정이 판정보다 앞선다.
3. **ps1 콘솔 출력을 저장한다**: 예를 들어 `pwsh -NoProfile -File <ps1> *>&1 | Tee-Object <ed8_design\stage5_judgement\run_console.log>`처럼 `--out` 폴더 밖에 둔다. 종료 코드는 `$LASTEXITCODE`로 따로 적는다. report에 시각 필드가 없어서, 판정 시각과 stdout `status`의 근거가 된다.
4. 판정 상태별 처리는 위 표대로 한다. frozen이어도 6단계는 사용자 질문 뒤에, S8-C는 census 뒤에 한다.
5. 5단계 판정서 커밋 전에 verif 판정 후 감사를 받는다. `_identity_checks\`(지금 `sums_unlisted` 3)와 판정 출력 폴더의 SUMS를 커밋 직전에 다시 쓴다.
6. **경로 2를 시작하기 전에 블라인드 목록과 금지 목록에 더할 것**(규칙 9:335)
   - 5단계 판정 출력(새 폴더면 그 폴더)
   - `ho_*_a1\logs\ed8_heldout_*.log`·`.err`(run별 `final_phase`·해시)
   - 5단계 판정서
   - `ed8_design\audit_stage5_prerun\`(앞 감사와 이 감사; 판정 도구 줄 인용)
   - `ed8_design\stage5_prejudge\`

## 검사하지 못한 것
- **판정 도구가 실제로 끝까지 도는지**(5단계 실제 입력으로): 판정을 돌리지 않으므로 보지 않았다. T8″ 스모크와 T8″→T8⁗ 무변경(앞 감사 기록 6), 키 존재(기록 8)로 대신했다.
- **`ed7.metric_of`·`ed7.t4h_folders_of`가 V0 줄에서 읽는 키 전체**: 앞 감사와 같은 공백이다.
- **스텝 `.err` 내용**(경고·traceback 수): 판정 값이 섞일 수 있어 열지 않았다. 오류 줄 0은 `key_presence`로 확인했다.
- **python-expert 사전 거부 사본의 실제 바이트**: 지워졌다. 생성 스크립트와 결과 문자열만 transcript에서 봤다.

## 실행한 검증
- **인터프리터**: python-dev `C:\ProgramData\miniforge3\envs\python-dev\python.exe -I -B`(`MKL_THREADING_LAYER=TBB`, 필요 시 `-X utf8`). dynamics-dev와 판정 도구는 실행하지 않았다.
- **명령**
  - `depcheck.ps1`(STAMP)
  - `source_guard snapshot`(입력 25) / `verify --strict-additions`
  - `Get-FileHash`
  - git 조회: `rev-parse`, `status --porcelain --ignored`(ed8-judge4·ed8-impl·격자 4개), `log`, `ls-files`(`--eol`), `check-attr text eol`, `check-ignore -v --no-index`, `hash-object`
  - verif 도구
    - `ps1_lint`, `placeholder_scan --pattern-set both`
    - `baseline_check sums`(stage5_prejudge, judge_7ea78232, _identity_checks), `write-sums --dry-run`(stage5_prejudge `--top-only`, ho_v0_a1 기본·`--recursive`), `identity`(세 단계 폴더), `blobs --rev ×3`
    - `worktree_locks`(전체 경로로 다시 실행; 처음 이름만 준 실행은 종료 2 입력 오류)
    - `log_errors`(stage5 러너 logs)
    - `key_presence`(jsonl 3개, 키 9)
    - `timeline`(`step_record.json` 3개, `--time-field started`; `.done` 확장자는 종료 2로 거부되어 바이트가 같은 `step_record.json`으로 대신함)
    - `seal_check --const --quoted --hash-files --min-hex-len 13`
    - `transcript_scope --with-main --since 2026-11-28T10:30 --watch …`(md·json)
  - `-c` 한 줄 2회(격자 키 파일 이름 수, stage5_prejudge 줄바꿈·BOM)
  - 즉석 스크립트 3개(scratchpad)
    - `ident_cmp.py`: `.done`·identity 메타 대조, 4단계 비교
    - `ts_reads.py`·`ts_agent.py`: transcript 도구 호출 대조
- **만든 뒤 지운 파일**: `verif-stage5-prejudge\`(`guard.json`, `ident_cmp.py`, `ts_reads.py`, `ts_agent.py`, `seal.md`, `transcript_scope.md`, `ts.json`). 폴더째 지웠고 `Test-Path` False다. 대상 폴더에 `__pycache__`는 만들지 않았다.
- **이 감사의 행위 공개**
  - `j9_runs\56849248\` 아래에서 한 것
    - `ho_*_a1` 3개의 재귀 `Get-ChildItem`(이름·크기·시각)
    - 최상위 `*.done` 목록
    - `judge_7ea78232\` 목록
    - 4단계 `impl_*_a1\logs\*.record.json` 읽기(벽시계·CPU)
    - 4단계 identity json 7개 메타
  - Grep 1회(`ed8_design` md, `3e45f5c1|judge_7ea78232`, 블라인드 없음), 세션 transcript Grep 건수 1회
  - jsonl·스텝 `.log`/`.err`·판정 json 값은 열지 않았다.
  - Bash·파이프·heredoc 0. 프로세스 종료 0.
- **최종 판정 전 재확인**
  - `source_guard verify`로 입력 25개의 sha가 같다.
  - `ho_k_selection.json`·판정 numba 폴더는 없다. ed8-judge4 HEAD `7ea78232`, 0줄. ed8-impl 0줄. ps1 sha `10a8095e`.
  - 감사 중 바뀐 파일은 없다.
- **에이전트 메모리**: `audit_pitfalls.md`에 "Pre-judge audit after the run, before the stage judge" 항목을 더했고, `MEMORY.md` 색인 한 줄을 고쳤다.
- 원본 불변: 확인 — 원본 쓰기 0회, 원본 디렉터리 쓰기 0건 (sha jp3_remedy_spec_v8_rules.md 35f9eba8…, jp3_remedy_spec_v8_rules.md.sha256 e19aaa48…, run_stage5_judge_t8pppp.ps1 10a8095e…, grid_blobs.txt 673d0c92…, SHA256SUMS a3d2b446…, decision_p85_20261128.md 1742fa05…, verif_stage5_prerun.md af3b40b3…, heldout_g_ed8.json a18b5818…, confirm_b_grid192.json 4e80e69b…, ho_v0.done c5f2df09…, ho_aa2.done 6432bccb…, ho_aa3.done 4669f443…, ed8_heldout_v0.jsonl fd5f85f5…, ed8_heldout_aa2.jsonl 182dcaab…, ed8_heldout_aa3.jsonl a2d65df1…, step_record.json c5f2df09…, step_record.json 6432bccb…, step_record.json 4669f443…, ed8_heldout_v0.identity.json 696fd2ab…, ed8_heldout_aa2.identity.json 03cdd535…, ed8_heldout_aa3.identity.json c38d8d25…, grid_r67_main.json a2e74481…, grid_r67_top.json 1d07e49f…, grid_r69_bottom.json 91026c46…, grid_r69_top.json 87e8d72a…, 디렉터리 목록 동일, ~$ 임시 파일 없음)
- 사용한 스킬: 없음
