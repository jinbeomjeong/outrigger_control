# 436.8 rev26 경로 2 수정 1: p2_u3 종료 3 (정렬 TypeError)

python-expert(경로 2 작성자), 2026-11-26. 사용자 결정 2026-11-26에 따라 경로 2 도구만 고쳤습니다.

`p2_u3` U-3 재집계가 끝까지 돌도록 고쳤습니다. 경로 2 시험은 모두 통과합니다(355개). 새 시험은 첫 판 `p2_u3.py`에서 종료 3으로 실패하는 것을 확인했습니다.

## 0. 커밋

- **커밋 `d6e0630f4dc58efcd8b5856efed62c8d08922431`**: `b587a841` 위 커밋 하나
- 브랜치·worktree: `rev26-p2`, `C:\workspace\outrigger_control\.claude\worktrees\rev26-p2`
- 바뀐 파일은 `path2/` 아래 3개입니다(경로 앞부분은 `06_analysis/02_control/verif_matrix/v5_resume_4368/`).

| 파일 | blob raw sha256 | 비고 |
|---|---|---|
| `path2/p2_u3.py` | `d9f9280b55535cb6aedbca499532f1a3752b41503a7a15d9104aa2674460f0ff` | 첫 판 `7ec2d245…` |
| `path2/test_rev26_p2.py` | `4430c1cfba25cf30c4ed23f7cfb8679b5f121c8512b7cd81d74444f7ce9525b1` | |
| `path2/README.md` | `cf854f1afedb587c60f7ed6cd38a9aadc67d4165cc5f8e12b0a993f04dddef0c` | |
| `path2/p2_4368.py` | `4c89a375…` | 그대로라 `p2v5c_common.P2_CORE_SHA`도 그대로 맞음 |

- 커밋 뒤 `git status --porcelain --ignored`는 비어 있습니다.
- 메인이 할 일: `$AllowListPath2`의 `p2_u3.py` 값은 위 blob으로 다시 계산해 주십시오.

## 1. 원인

원인은 코드로 추정한 것입니다. 오류 추적 말고는 실데이터를 보지 않았습니다.

- **알려 주신 추정과 다릅니다.** 정렬 대상 짝 키 `k`에는 suite가 들어가지 않습니다. screen 꼴은 키만 씁니다.
- **실제 원인: 첫 판(b587a84) `records_loc`가 screen 꼴 키를 `results[].key`만으로 읽었습니다.**
  - 932f1fb는 `key`가 없으면 `id`를 읽었습니다.
  - 그래서 `id`로 식별하는 screen 줄은 키가 None이 됐습니다. 연구 D 꼴이 이렇습니다.
    - `p2_u3.study_keys`가 연구 D를 `results[].id`로 읽습니다.
    - `p2_x16.G3_PAIRS`의 `u3_D`는 `run.commands_sha256`를 씁니다.
  - 그 키가 `sorted(set(V0) & set(VB))`(583행)에서 문자열 키와 비교되어 `TypeError`가 났습니다.
- R26-1의 "문자열 그대로"를 제가 지나치게 좁게 구현한 결함입니다.

## 2. 고친 것 (`p2_u3.py`)

1. **screen 키를 932f1fb와 같은 문자열로 되돌렸습니다.** `records_loc` screen 키 = `key`, 없으면 `id`입니다. R26-1의 나머지(파일 이름을 키·suite에 넣지 않음)는 그대로입니다.
2. **None이 섞여도 결정적으로 정렬합니다.** 새 함수 `sort_key`를 썼습니다.
   - 순서: None이 모든 문자열보다 앞, 튜플은 원소별
   - None이 없으면 일반 `sorted`와 같은 순서입니다. 그래서 키 문자열과 순서가 None 없는 경우 932f1fb판과 같습니다(`test_r261_wrapper_keys_unchanged`, `test_r261_sort_key_order`).
   - 적용한 곳 두 군데
     - 짝 키 루프(`recount_u3`)
     - D-1 재사용 `(setting, suite)` 루프. suite가 None일 수 있어 같은 꼴의 위험이 있었습니다.
3. 모듈 docstring과 README rev26 절에 수정 1을 적었습니다.

## 3. 같은 꼴 정적 점검

경로 2 도구 전체에서 `sorted(set(…`, `sorted({…`, `sorted(… keys …` 꼴을 Grep으로 찾았습니다.

| 위치 | 판단 |
|---|---|
| `p2_u3.py` 583행, 640행 | 고침(위 2.2) |
| `p2_u3.py` 475행, 748행 | `map(str, …)`로 정렬하므로 None 안전 |
| `p2_u3.py`의 나머지 | 수치·멈춤 코드·`_row_sort`(결과 파일·위치 문자열) 정렬이라 None 키를 정렬하지 않음 |
| `p2_u3.py` 출력 dict(`counts`, `differences`) | None 키는 JSON에 `"null"`로 적힐 뿐 정렬하지 않음 |
| v5j_u9 (`p2_v5j.py` 475·637행) | 키 읽기가 932f1fb 그대로이고 R26-1과 무관 |
| c16·items (`p2_x16.py` 167행) | 고정 이름만 정렬 |
| v5c_* (`p2v5c_common.py` 235행, `p2v5c_grid.py` 91·295·414행, `p2v5c_noise.py` 443·668행, `p2v5c_stage1.py` 112·694·731행) | 키 읽기가 932f1fb 그대로이고 R26-1과 무관 |
| `p2_4368.py` harness | u3 screen 줄 키를 `line_key`(`key`, 그다음 `id`, 그다음 `case`)로 읽어 바뀌지 않음 |
| `p2_t3k.py`, `p2_d1.py` | 바뀌지 않음 |

- R26-1 때문에 suite나 키가 None이 될 수 있는 곳은 `p2_u3`뿐입니다. `records_loc`를 쓰는 도구가 `p2_u3`뿐이기 때문입니다.

## 4. 시험

**새 시험 `test_fix1_main_mixed_wrapper_and_screen_keys`**
- 입력 줄 다섯 꼴을 섞었습니다.
  - suite 있는 wrapper 줄
  - suite 없는 wrapper 줄
  - `key`로 식별하는 screen 줄
  - `id`로 식별하는 screen 줄(D 꼴)
  - 식별자가 없는 screen 줄
- `main`을 끝까지 돌립니다. 연구 키 파일은 합성 `--data-root` 아래에 둡니다.
- 확인하는 것
  - 종료 코드가 0, 1, 2 가운데 하나
  - 두 번 실행한 출력이 같음
  - `differences` 키 순서가 `sort_key`와 같음
  - D 꼴은 id로, wrapper는 `<suite>|<id>`로, suite 없는 wrapper는 id로 짝을 지음
- 첫 판 `p2_u3.py`(b587a84)로 바꿔 끼워 돌리면 이 시험은 실패합니다. 종료 3으로 출력 파일이 없었습니다. 확인 뒤 수정본으로 되돌렸고, sha256 같음을 확인했습니다.

**새 시험 `test_r261_sort_key_order`**
- None이 없으면 `sorted`와 같은 순서이고, None이 맨 앞이며, `(setting, suite)` 튜플도 결정적으로 정렬됨을 봅니다.

**경로 2 시험 전체**
- 명령: `conda run --no-capture-output -n dynamics-dev python -I -B -m pytest -q -p no:cacheprovider -k "not test_rev3_study_key_files_real and not test_dg3_key_source"`
- 대상: `test_p2_4368`, `test_p2_u3`, `test_p2_x16`, `test_p2_v5j`, `test_p2_d1`, `test_p2_t3k`, `test_p2v5c`, `test_rev26_p2`
- **결과: 355 passed, 2 deselected, 실패 0, skip 0.** 빠진 2개는 실데이터를 읽는 시험이라 앞 판과 같이 뺐습니다.

**린트·맞춤법**
- ruff `F,E9`: 통과
- 새 시험 파일 120자 E501: 통과(파일 꼴 기준)
- codespell(`abl,pres` 제외): 0건

## 5. 공개 (행위 그대로)

**연 파일**
- worktree의 `p2_u3.py`(213~240행 근처, Grep으로 본 `sorted(` 줄)
- 경로 2 도구 폴더 `p2*.py`

**검색 path**
- worktree의 `06_analysis/02_control/verif_matrix/v5_resume_4368` 아래 `p2*.py`(glob)
- 이 범위에 `path2_chrono`가 포함돼 결과에 함께 나왔지만, 그 파일은 열지 않았습니다.

**열지 않은 것**
- 경로 1 자료
- 436.8 결과 json(이번 실행 출력 `judge_rev26_335004a\` 포함)
- 판정서, 판정 후 감사, 부록 B, 블라인드 경로

**판정 도구를 저장 결과에 돌린 횟수: 0.** 모든 실행은 pytest 임시 폴더의 합성 입력이었습니다.

**그 밖**
- 확인을 위해 worktree의 `p2_u3.py`를 잠시 `b587a84` 판으로 바꿔 끼웠다가(`git checkout b587a84 -- <파일>`), 시험 뒤 수정본으로 되돌리고 index도 되돌렸습니다.
- scratchpad 하위 폴더 `python-rev26-p2-fix1`은 지웠습니다.

## 6. 메인 세션 권고

- 경로 1 브랜치와 다시 합쳐 새 T26을 만든 뒤 두 경로를 재실행해 주십시오(사용자 결정대로).
- `$AllowListPath2`의 `p2_u3.py`·`test_rev26_p2.py`·`README.md` 값을 새 T26 blob으로 고쳐 주십시오.
