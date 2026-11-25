## 봉인 준비 ② 결과: b46bdf8f에서 G1 키 파일 생성과 확인

G1 키 파일은 seed 20261126으로 만들었고 확인 항목은 모두 통과했습니다. **FL-Fs4 추출 오프셋은 o0.0**입니다. 다만 봉인 전에 정할 일이 셋 있습니다(아래 확인 필요 1~3). 해석과 권고는 넣지 않았습니다.

worktree ed7-impl는 그대로입니다: HEAD b46bdf8f, 생성 전후 모두 `git status --porcelain` 0줄, 커밋 없음, 안에 생긴 파일 없음. 명세는 개정 6(sha256 `305bbb91…`)으로 대조했습니다. 실행 커밋 C는 만들지 않았습니다.

### 파일
폴더: `C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause\ed7_design\keys_seal_b46bdf8f\`

| 파일 | sha256 | 내용 |
|---|---|---|
| `confirm_g1_grid171.json` | `684054abb1ad05d8f82141f58eafdfa3c096edae1c05c9a4b9e8ae9ffe5b5dec` | G1 171줄, seed 20261126 |
| `sens_keys_ed7.json` | `be930b75a375877d07fc84fa98a9f8b0ee463f5b592319cfd6869fcc62a05b1b` | 감도 460줄, b46bdf8f에서 생성 |
| `g1_pool_ed7.json` | `07dd13743f2aa2a529ff6be002d779e16fff9e92f46979828bb0429036043c65` | 풀 계수(기록) |
| `verify_g1.py` / `verify_g1.json` | `063292aa…` / `92bf0e26…` | 키만 본 확인 |
| `manifest.json` | `71646a3e…` | 명령, 입력 sha, b46bdf8f clean, 결정성 기록 |
| `SHA256SUMS` | `f4888e9023212ed64372bf9b171ca2e4728959ff0fcb4ca3140ed0d7a76d4d69` | 6항목, `baseline_check write-sums` |

- 생성 명령(dynamics-dev `python.exe -I -B`): `ed7_key_lists.py --out-dir <위 폴더> --pool-csv ed7_design\stats_v7\s30_pool_runs.csv --grid-root 06_analysis\02_control\touch_phase\acceptance\c4g2_only\grid --repo C:\workspace\outrigger_control --only confirm_g1_grid171.json,g1_pool_ed7.json --g1-seed 20261126`
- 풀 csv sha256은 `8d2626af…`이고, 도구에 고정된 값과 같습니다.

### 확인 결과
- **줄 수**:
  - 171줄, 171군집, T4h 이름 171개 모두 고유, 설정은 모두 VBM입니다.
  - `k_counted_lines` 168, `fault_jp3_judged_lines` 171, `expected_j_p3_judged_rows` 171, head-only 0입니다.
- **U832**: `counted_for_k` false는 정확히 3줄이고, 모두 U832 군집입니다.
  - `bottom-FL-Fs2-RE1bF-ready` o0.025
  - `bottom-FR-Fs2-RE1bF-ready` o0.075
  - `bottom-FR-Fs4-RE1bF-ready` o0.075
  - `judged_fault_jp3`는 171줄 모두 참입니다.
- **D 키 대조**:
  - G1 줄 가운데 D 12키(blob `3ecf61f1:…/d_grid_keys12.json`, git blob `58268f22…`)와 겹치는 줄은 0입니다.
  - 판 6 격자 `confirm_b_grid192.json`과 겹치는 줄도 0, probe 키(`189dbb13…`)와 겹치는 줄도 0입니다.
  - D 12키는 모두 판 6 격자 192 안에 있습니다.
- **V0 짝 해시**: 171줄 모두 저장 V0 격자 run의 `commands_sha256`이 키 파일 값과 같고, 저장 run `pass`도 모두 참입니다.
- **FL-Fs4(`R12 bottom-FL-Fs4-RE1bF-ready`) 추출 오프셋: o0.0**. 줄 이름은 `R12_bottom-FL-Fs4-o0.0-RE1bF-ready_VBM.npz`이고 `counted_for_k`는 참입니다. 명세 6.3이 공개 대상으로 정한 값입니다.
- **결정성**: 같은 seed와 같은 `--out-dir`로 두 번 만들었습니다. confirm_g1, g1_pool, sens 모두 바이트가 같았습니다. 첫 실행 결과는 옆으로 옮기고 두 번째 실행 결과를 남겼습니다.
- **기존 키와 대조**: b46bdf8f에서 다시 만든 `probe_keys_ed7.json`과 `sens_keys_ed7.json`은 tool_6bfb2560 판과 `lines`가 같습니다. 다른 필드는 `code_identity`(6bfb2560 clean 대 b46bdf8f)와 `generation_command` 둘뿐입니다.

### 봉인 상수 후보 (`run_v5.py` 390행: `ED7_KEY_FILE_SHA256: dict[str, str]`)
`sealed_key_jobs`는 이 dict를 **파일 이름**으로 찾고, 줄의 설정이 `ALL_SETTINGS` 안에 있어야 합니다.

```python
ED7_KEY_FILE_SHA256: dict[str, str] = {
    "sens_keys_ed7.json": "be930b75a375877d07fc84fa98a9f8b0ee463f5b592319cfd6869fcc62a05b1b",
    "confirm_g1_grid171.json": "684054abb1ad05d8f82141f58eafdfa3c096edae1c05c9a4b9e8ae9ffe5b5dec",
}
```
- 대안: 감도 키에 기존 tool_6bfb2560 판(`3b622bbde052e17a11b38804915a350c6be5f706233695b23a76b3ef64238a49`)을 쓸 수도 있습니다. `lines`는 같고, 6bfb2560에서 생성됐습니다. 명세 5.1 1단계의 "b46bdf8f(clean)에서 키 파일을 만든다"에 맞는 쪽은 위 b46bdf8f 판입니다.
- 상수에 넣지 않는 참고 sha:
  - probe 키 `probe_keys_ed7.json` `189dbb1315e2267812a1a14724c1cf405c96b70e2f43735ee22da940b28053da`: probe 6bfb2560 실행이 쓴 파일이고 명세 4.2의 "키 파일 sha" 자리입니다. 설정이 `P7-*`라서 `ed7_keys` 배치 입력이 아닙니다.
  - D 키 `d_grid_keys12.json` `a995abff9d73816f58a0e3d67a59f18b3e60fb006fe48d824012b79b57d87981`: `ed7_probe.D_KEY_FILE_SHA256`에 이미 고정돼 있습니다.

### 확인 필요
1. **D 24줄 확인 단계 키 파일이 없습니다**
   - 명세 4절 6과 Y7-6은 확인 단계 실행을 "G1 171 + D 24 = 195줄"로 정합니다.
   - 하지만 b46bdf8f의 `ed7_key_lists.py`가 만드는 출력은 probe, sens, g1_pool, confirm_g1(171) 넷뿐입니다. D 24줄(봉인 구성 팔, VBM/VBMslow)을 `ed7_keys` 배치로 돌릴 키 파일과 그 sha 자리가 없습니다.
   - 두 가지 길이 있습니다: ed7_probe의 D 부분(arm a2)으로 다시 돌리거나, 키 파일을 새로 만드는 것. 어느 쪽인지 명세에서 정해야 합니다. 새 키 파일을 만들면 코드 변경이 필요하고, 그 변경이 P7-10 범위에 들어가는지도 함께 정해야 합니다.
2. **G1 `v0_pair.run_id`가 문자열입니다**
   - `ed7_key_lists.stored_grid_runs`가 `str(run_id)`로 씁니다(171줄 모두 `"5"` 같은 문자열). 판 6 키 파일은 정수였습니다.
   - 판 6 도구 `jp3_ed6_judge.grid_v0_run`은 `pair["run_id"] >= len(...)`로 비교하므로, G1 판정에 그대로 다시 쓰면 TypeError가 납니다.
   - 키 파일 sha가 봉인되므로 형식은 바꾸지 않았습니다. 봉인 뒤 G1 판정 도구가 문자열 run_id를 받게 만들지, 봉인 전에 형식을 정할지 결정이 필요합니다.
3. **키 파일 sha는 출력 폴더 경로에 따라 달라집니다**
   - `generation_command` 필드에 `--out-dir`가 들어가기 때문입니다.
   - 재현 대조는 같은 경로로 하거나 `lines` 비교로 해야 합니다.

### 실행한 검증
- `verify_g1.py`(python-dev): 결과 ok, 종료 0.
- 두 번 생성한 바이트 비교: 세 파일 모두 같음.
- 블라인드 경로(`606f8713/cdry_a1/...`), worktree 루트, `06_analysis` 전체는 검색하지 않았습니다. 경로는 모두 직접 지정했습니다.
- scratchpad `python-ed7keys\`는 지웠습니다.

사용한 스킬: 없음
