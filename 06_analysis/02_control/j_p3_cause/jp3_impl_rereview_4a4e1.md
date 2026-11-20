# 436.9 J4a 보완 구현 4(`99e9132b`) 재검토 — 덧붙임 4a-4 정오 1(R-1·R-2)과 최종 고정 목록

작성: control-expert, 2026-11-21. 읽기·분석과 해시 측정만 했다. 코드 수정·시뮬레이션은 하지 않았고, 결과 파일 내용은 열지 않았다.
- 대상: worktree `C:\workspace\outrigger_control\.claude\worktrees\z4369-jp3`, `git diff b06e409e 99e9132b`(5파일, +332/−13). 커밋 `99e9132bafd30d149f254751664a50d8a44df7f4`이고 작업 트리는 깨끗하다(`git status --short` 빈 출력).
- 기준: 덧붙임 4a-4(`67380b10…`)와 정오 1(`1ccbe526…`, 사용자 확인: `--keys-file` 진행, R-2 포함)

## 1. 판정

| 항목 | 판정 | 근거 |
|---|---|---|
| R-1 `select --keys-file` | 적합 | `place_keys_file`: 기존 파일은 바이트(`key + "\r\n"`)가 같아야 하고, sha256은 `jp3_fixed_inputs.DRY_KEYS_FILE_SHA256` = `1a79e02f…`여야 한다. 아니면 멈춘다. 측정한 저장소 사본과 같다(33 bytes) |
| R-1 `summarize` | 적합 | `keys_file_problems`: 선택 기록 sha = 고정값, r79 출력 meta `keys_file.sha256` = 선택 기록, `n_keys` = 1. 하나라도 아니면 "다시 묻기"로 판정 불가다(정오 1 넷째 글머리) |
| R-2 `base-judge-compare` | 적합(권고 1) | H-6(`ea0ab94c…`), 새 판정 파일(인자 sha), 436.8 경로 1 판정 파일(`d95627ac…` 고정)을 대조한다. 같은 H-6 135줄을 두 판정 파일로 `grade_lines`해서 grade·failed_gates·flags를 키별로 비교하고, `h6_judge.json` line_details와도 대조한다. L1 참조 추출이 같은지 기록한다. 종료 1 = 차이(원인 확인 뒤 T-JR-12), 2 = 입력 없음 또는 sha 다름. 판정 조건이 아닌 기록이라고 명시돼 있다 |
| 권고 1 | 비차단 | 선택 입력 `--stored-h6-judge`(`h6_judge.json`)의 sha를 고정값 `f8352c5d…`로 대조한다(지금은 대조하지 않음) |

- prelaunch 순서 P-1a `base-judge` → R-2 `base-judge-compare` → P-1b `t12-selfcheck`는 4a-4 6절·정오 1과 맞다.
- 새 선택 결과(보고): 스캔 3,266파일, r79 키 2,324, seed 최대 24, 생성 키 `L2|s25|g6|0|g6|G1+J1@FL|top|Fs0`. 4a-4 1절 정의(작업 트리 `06_analysis/` 전체 스캔)대로이고, 파일 수는 근거 폴더가 늘어 커졌다.

## 2. 최종 고정 목록(sha256 직접 측정, 2026-11-21)

### 2.1 명세·덧붙임(`06_analysis/02_control/j_p3_cause/`)

| 경로 | sha256 | 추적 | 쓰는 곳 |
|---|---|---|---|
| `jp3_remedy_spec.md` | `8be9de229394882b06cf7cbf29dba754e7159150d4803d5ef729eab5424e9ede` | 예 | 봉인 명세 판 4a |
| `jp3_remedy_spec.md.sha256` | `174e6fb77fd5e87aacd1c3bed042eae88e3471ad2bc70d9de3f5cf12121bccf5` | 예 | 봉인 sha 파일 |
| `jp3_remedy_spec_addendum_4a1.md` | `4b122dd073196ed26d6721aabcde99a4cc4ee93e2e415b1781eef2f32582c41f` | 예(`143a0ef`) | 덧붙임 4a-1(`.sha256` 파일 없음) |
| `jp3_remedy_spec_addendum_4a2.md` | `2f3e36bdc2bf5ff76e2cdfe3ddfe41e23dbdd94b8fb9ea50b4bb532ffecf9b92` | 아니오 | 덧붙임 4a-2 |
| `jp3_remedy_spec_addendum_4a2.md.sha256` | `19063b360ebae9f0788e7497627ed85c627e55cd4890b0406b5d1844051f6cc2` | 아니오 | 그 sha 파일 |
| `jp3_remedy_spec_addendum_4a3.md` | `f001383a2e33598f0624c43b68c241c8e588a8734bb8d32c20ca8aaecd94fd20` | 아니오 | 덧붙임 4a-3 |
| `jp3_remedy_spec_addendum_4a3.md.sha256` | `3045bb46219b884a19d826d3fecb146946632fb88d42be68a98168d3028693d8` | 아니오 | 그 sha 파일 |
| `jp3_remedy_spec_addendum_4a4.md` | `67380b10957d6447386965a0de9a374324fad610ac1c8a1f7e611fb451b7aef6` | 아니오 | 덧붙임 4a-4 |
| `jp3_remedy_spec_addendum_4a4.md.sha256` | `c50c5aacf232340c35cbf7c8be2af57d547e65a2f8d717d34ad7fcf039c6442e` | 아니오 | 그 sha 파일 |
| `jp3_remedy_spec_addendum_4a4_erratum1.md` | `1ccbe5261ec97b764b2f4c4e8189b00acef0f76f1e5d01e4a07524bc6132c3e4` | 아니오 | 정오 1 |
| `jp3_remedy_spec_addendum_4a4_erratum1.md.sha256` | `27255e695d5205ec46ab364524b41f4566969953de2899402934cbce5f863f8f` | 아니오 | 그 sha 파일 |

### 2.2 기준선·저장 입력

| 경로 | sha256 | 추적 | 쓰는 곳 |
|---|---|---|---|
| `06_analysis/02_control/j_p3_cause/baseline_221456d/SHA256SUMS` | `197ac14e96822130ba4eee98486be6ba9646c207ed1a27936c275077b3a60361` | 예 | 기준선(4a-1), `jp3_baseline_compare`, select |
| `06_analysis/03_hydraulic/coupled/v5/main.jsonl` | `9ad749907c34c9e9efb77579a8ab6e3b1f86cdc32d36162c0029005ca545b29e` | 아니오(`.git/info/exclude`) | 22행 규칙(t8, `j9_t8 --p3-hash-source`, select) |
| `06_analysis/03_hydraulic/coupled/v5/resume_k1/h10_reuse_rerun.jsonl` | `ce526b1f71e635e6b80d538f36841ece01710af46f02acb4b3fa1355a5a4dcb3` | 아니오 | T-JR-10 저장 VB(t8 `--stored`) |
| `…/resume_k1/h6_dg3_v4on.json` | `ea0ab94c81e58eeb83ab2b6a63494a56c16bcd4165a62de47eba5efd03f23c89` | 아니오 | T-JR-12 VBH 기준, select `--dg3`, base-judge, R-2, self-check |
| `…/resume_k1/h7_dg3_off.json` | `43997bf164655b45aa21a0b8483801053e842b4bfb1a3e9e71cfcf55cb341b0f` | 아니오 | 4a-4 1절 표(스캔 집합) |
| `…/resume_k1/h8_noise_VB.json` | `2219ab9782b22fbe07e6c1f90e8b49c6b3703b0575b5d7cfb7d72b4f067bec43` | 아니오 | select `--noise`, base-judge L1 참조 |
| `…/resume_k1/h8_noise_V0.json` | `54d1731611a27982a9e618ac734b6ccb5ab06d6dfed182b30eadb25682a3709e` | 아니오 | 4a-4 1절 표 |
| `…/resume_k1/h8_seedext_VB.json` | `41afdc7780e0eb9bf162a5baaa47ad27ca2082cb8abc0a828be930a478b6c4bb` | 아니오 | 4a-4 1절 표 |
| `…/resume_k1/h8_seedext_V0.json` | `5f771ad24923867db5e37408a49026b32590a15d105ffa06e97058edfb158f4e` | 아니오 | 4a-4 1절 표 |
| `…/resume_k1/h9_grid/grid_r67_top.json` | `7160f9f19b497ea264e9dd90c58c2da25540ded51e8510197205cf91f00bd827` | 아니오 | F-A, case-f-path(5.2) |

### 2.3 T4h 폴더(파일 sha 목록의 정렬 manifest 해시)

manifest 해시 정의: 폴더 안 모든 파일의 `<sha256>  <상대 경로>\n` 줄을 경로 순으로 이은 문자열의 sha256.

| 폴더 | 파일 수 | manifest sha256 | 쓰는 곳 |
|---|---|---|---|
| `…/resume_k1/h10_reuse_rerun_t4h/` | 426 | `e9af5b859eb4f6daf293b45f84f5faa7bda06193f5d2ea747d828d1ccf6389d9` | T-JR-10 저장 줄 T4h meta(③ revision assert, C 기록) |
| `…/resume_k1/h6_dg3_v4on_t4h/` | 135 | `7e1fc01f827e942a7d735e77502676dd05dd10ff77aee12ce3e5001decebb315` | T-JR-12 기준 T4h |

- 실행 전에 메인이 두 폴더의 파일별 SUMS를 만들어 고정한다. 위 manifest 해시가 그 SUMS 내용과 맞는지 감사에서 대조한다.

### 2.4 키 파일·436.8 저장 판정

| 경로 | sha256 | 추적 | 쓰는 곳 |
|---|---|---|---|
| `06_analysis/02_control/j_p3_cause/j4a_remedy_b06e409e/dryrun_selection_r79_key.txt` | `1a79e02fc33ae8844d0cd5672e9e5e745215c354e58e9a8095376939c4335e74`(33 bytes, CRLF) | 아니오 | r79 건식 확인 `--keys-file`(정오 1) |
| `06_analysis/02_control/verif_matrix/v5_resume_4368/judge_932f1fb/harness_path1/h6_r79_judge.json` | `d95627ac83a0bfc165df763e898956fbdcbf7c299fb2d9face8915ef478ed57b` | 예 | R-2 `--stored-judge` |
| `…/harness_path1/h6_judge.json` | `f8352c5d12d31aebcffe2a4bc5bdfa7919e605a3f3261da8455640df3bad0d0b` | (같은 폴더) | R-2 `--stored-h6-judge`(권고 1: 고정값 대조) |
| `…/harness_path1/h6_L1_reference.json` | `a591c3a8c5b3ad5822877e7f69ce2acf75e4cc96fff139a52fef7b6439d56ce7` | (같은 폴더) | R-2 L1 참조 대조(기록) |

### 2.5 근거 폴더 SUMS(`06_analysis/02_control/j_p3_cause/`)

| 경로 | sha256 | 추적 | 쓰는 곳 |
|---|---|---|---|
| `j4a_remedy_3b949f5/SHA256SUMS` | `dba494a85c0b95178a4308c2d847c27b9779325de17bc5f6915384fb6f749eab` | 아니오 | 4a-3 1절 수치 |
| `j4a_remedy_738a09f/SHA256SUMS` | `82b6a851b7ec30bfa1b9b8cb36bb6a4739bd165dac12059bb6d968a1c99dcafb` | 아니오 | K-1~K-9 근거 |
| `j4a_remedy_b06e409e/SHA256SUMS` | `8235c5ced600a1e16aab353783154d7494700e2990b4ac98690ff0ddb18cb370` | 아니오 | 4a-4 근거·키 파일 |
| `j4a_remedy_99e9132b/SHA256SUMS` | `db2a2d31d17dbce5390cca9528920d4d009d1f9b8ce4a68254a4e96ec9880c40` | 아니오 | R-1·R-2 근거, prelaunch |

### 2.6 실행용 코드

| 항목 | 값 | 쓰는 곳 |
|---|---|---|
| worktree `.claude/worktrees/z4369-jp3`, 브랜치 `z4369-jp3` | 커밋 `99e9132bafd30d149f254751664a50d8a44df7f4`(작업 트리 깨끗) | 모든 실행·판정 도구. 실행 전 `git worktree lock`, 결과 identity `git.head` 대조 |

- git 추적: 2.1~2.5의 "아니오" 항목은 아직 추적되지 않는다. 해당 경로의 git `text` 속성은 unset(`-text`)이라, 커밋해도 줄 끝이 바뀌지 않아 sha가 유지된다. 커밋 뒤 위 sha와 다시 대조한다. 키 파일은 CRLF 바이트라 특히 대조한다.

## 3. 수행한 작업

- `git diff b06e409e 99e9132b`(`jp3_dryrun_evidence.py`, `jp3_fixed_inputs.py`, `jp3_tjr_judge.py`)를 읽었다.
- 해시 측정 스크립트를 `conda run -n dynamics-dev python -I -B`로 돌렸다. 파일 바이트의 sha256만 계산했다.
- `git ls-files`와 `git check-attr text`로 추적 여부와 줄 끝 속성을 확인했다.
- scratchpad `control-4a4e1\`는 지웠다.

## 4. 핸드오프

- 위임 필요(python-expert): 권고 1(`--stored-h6-judge` sha 고정, 선택).
- 위임 필요(메인·verif-protocol-auditor): 2절 목록의 고정(git 추가 또는 SUMS, T4h 폴더 SUMS 생성)과 실행 전 감사.
