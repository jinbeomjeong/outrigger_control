# chrono_hull — SCM 볼록 껍질 고속화 (비트 동일)

소유: cpp-expert(C/C++). Python 연동은 cad-expert가 맡는다.
상태: **기본 꺼짐.** 채택 여부는 관문 G-A~G-D를 통과한 뒤 사용자가 정한다.

## 무엇을 하나

PyChrono 10.0.0(conda `pychrono 10.0.0 py312h418371c_1198`)의 `SCMTerrain`은 매 스텝, 접촉 패치마다
`chrono::utils::ChConvexHull2D`(Jarvis 감싸기, O(n·h))로 패치의 면적과 둘레를 구한다. py-spy 실측으로 S9 실행 시간의
약 27 %를 차지한다. `chrono_hull_hook.dll`은 같은 프로세스 안에서 `Chrono_vehicle.dll`이 `Chrono_core.dll`에서
가져오는 함수 4개(생성자, 소멸자, `GetArea`, `GetPerimeter`)의 import 주소 테이블(IAT) 슬롯을 바꿔,
**비트 단위로 같은 결과**를 더 빠르게 낸다. Chrono 바이너리와 conda env는 바꾸지 않는다.

| 파일 | 내용 |
|---|---|
| `include/chrono_hull_hook.h` | C API(아래 계약) |
| `src/exact_fast_hull.{h,cpp}` | 비트 동일 고속 알고리즘(Chrono 링크 의존 없음, `ChVector2` 헤더만) |
| `src/chrono_hull_hook.cpp` | DLL: IAT 교체, 모드(off·fast·shadow·dump), 카운터 |
| `src/import_slots.{h,cpp}` | PE import 슬롯 찾기·쓰기, 파일 SHA-256 |
| `src/patch_dump.{h,cpp}` | 패치 점 덤프 형식(`.ohull`) |
| `tests/hull_equivalence_test.cpp` | G-A 동치 시험: conda `Chrono_core.dll`의 원본 생성자와 비트 비교 |
| `tests/hull_bench.cpp` | G-A 속도 측정(호출당 시간) |
| `tests/hook_scm_smoke.cpp` | 실제 SCMTerrain(C++, Python 없음)에서 off·fast·shadow·dump 종단 시험 |
| `build.ps1` | VS 2022 BuildTools + Ninja 빌드, `bin\chrono_hull_hook.dll` 설치 |

## 빌드

```powershell
& .\build.ps1             # 시험 포함
& .\build.ps1 -NoTests    # DLL만
```
- MSVC 14.44(VS 2022 BuildTools), C++20, `/MD /O2 /fp:precise /arch:AVX2 /EHsc /utf-8`.
- `CHRONO_PREFIX`(기본 `C:/ProgramData/miniforge3/envs/Chrono-dev/Library`)에서 헤더와 `.lib`만 읽는다. env는 바꾸지 않는다.
- 산출물: `bin\chrono_hull_hook.dll`(git 제외). 빌드 끝에 SHA-256을 출력한다.
- **`/MD` 고정**(conda 빌드와 CRT 힙·STL ABI 공유). `/MT`나 Debug로 빌드하면 객체를 공유할 수 없다.

## 정확성 근거

원본은 `(crt, next)` 단계마다 `perimeter += |next − crt|`, `area += SignedArea(next, crt, 0)`를 차례로 더한다.
그래서 같은 볼록 껍질이라도 단계 순서(공선점을 어디서 끊는지, 어디서 시작하는지)가 다르면 비트가 달라진다.
새 구현은 원본과 **같은 단계 순서열**을 만든다.

1. **격자 인증.** 각 축에서 최소 양의 간격으로 정수 인덱스를 구하고, 전체 폭으로 간격을 다시 맞춘 뒤 잔차 ρ를 잰다.
   같은 인덱스 점의 좌표는 비트까지 같아야 하고, 인덱스가 커질수록 좌표도 엄격히 커져야 한다.
   그러면 모든 삼중점의 `SignedArea` 계산값은 `Δx·Δy·(정수) ± E`가 된다. 오차 상한은
   `E = 4·D·τ + 2·τ² + 4·u·D²`, `τ = 2·(ρ + 4u(C + D)) + u·D`, `u = 2⁻⁵²`
   (D는 패치 폭, C는 최대 |좌표|)이다.
   **E ≤ 1e-11이고 Δx·Δy ≥ 1e-8일 때만** 고속 경로를 쓴다. 이때 Chrono의 허용치 술어(|값| < 1e-10이면 공선)는
   정수 정확 술어와 같다. SCM 점(`m_delta × 정수 노드`)은 이 조건을 넉넉히 만족한다.
2. **정확한 술어에서 Jarvis가 하는 일.** 엄격 꼭짓점에서는 나머지 점이 180° 미만의 원뿔 안에 있어 비교가 전순서가 된다.
   그래서 다음 점은 "현재 변 위 전방 공선점 가운데 인덱스가 가장 작은 점"이다. 변 내부 점에서도 결과는 같다.
   뒤쪽 공선점은 이미 추가돼 있고, 시작점만 예외다.
   경계 밖 점(내부점)이 결과에 영향을 주는 길은 두 가지다.
   - ① 첫 후보(인덱스 0부터 `crt`도 아니고 추가되지도 않은 첫 점)
   - ② 첫 변 위를 걷는 동안 첫 후보가 시작점이 되는 단계. 원본 스캔은 "선 밖 첫 점 j*"를 만나야 시작점을 버리므로,
     결과는 j*보다 인덱스가 큰 첫 전방 공선점이다.
3. **후보 축소.** 행별 최소·최대 x 점과 맨 아래·맨 위 행 전체를 남긴다. 이 집합은 경계점을 모두 포함한다.
   여기에 남기지 않은 점 중 인덱스가 가장 작은 점 하나를 더해 ①을 보존한다.
   이 후보들을 원래 인덱스 순서로 두고 **원본 루프를 그대로** 돈다.
   ②는 전체 입력에서 j*만 찾아 해결한다(`ResolveStepBehindFirst`). 원본이 껍질 안쪽으로 들어가는 경우만 포기한다.
4. **포기하는 경우.** 점 32개 미만, 격자 인증 실패, 중복 점, 한 행·한 열·전부 공선, 위 ②에서 안쪽으로 들어가는 경우, 크기 가드 초과.
   이때는 원본 함수를 그대로 부른다(fast 모드). 따라서 결과는 항상 원본과 같다.

## C API · 환경 변수 계약 (버전 1, `chrono_hull_hook_version() == 1`)

| 함수 | 반환 | 뜻 |
|---|---|---|
| `int chrono_hull_hook_install(int mode)` | 상태 코드 | 0 off(제거), 1 fast, 2 shadow, 3 dump. 이미 설치돼 있으면 모드만 바꾼다. 실패하면 프로세스는 그대로다 |
| `int chrono_hull_hook_install_from_env(void)` | 상태 코드 | 아래 환경 변수를 읽어 설치한다. **변수가 없거나 비어 있으면 off**(아무것도 바꾸지 않음) |
| `int chrono_hull_hook_uninstall(void)` | 상태 코드 | 슬롯 원복(설치 안 됐으면 무동작) |
| `int chrono_hull_hook_mode(void)` | 모드 | 현재 모드 |
| `int chrono_hull_hook_set_dump(const wchar_t* path, uint64 every_nth, uint64 max_records)` | 상태 코드 | 덤프 파일(UTF-16 경로, `NULL`이면 닫음). dump 모드는 every_nth번째 호출마다, shadow는 불일치 입력만 쓴다. max 0 = 무제한 |
| `int chrono_hull_hook_get_stats(ChronoHullHookStats*, uint32 size)` | 상태 코드 | 카운터(`calls`, `fast_computed`, `fallback`, `shadow_compared`, `shadow_mismatch`, `dumped_records`, `non_jarvis_calls`, `fallback_by_reason[8]`) |
| `void chrono_hull_hook_reset_stats(void)` | — | 카운터 0 |
| `const char* chrono_hull_hook_status_string(int)` | 정적 문자열 | 상태 코드 이름 |

상태 코드: 0 `ok`, −1 `bad_mode`, −2 `module_not_loaded`(Chrono_vehicle/core 미적재), −3 `hash_mismatch`,
−4 `import_not_found`, −5 `import_not_original`(슬롯이 이미 다른 값), −6 `protect_failed`, −7 `dump_file`, −8 `env_value`, −9 `stats_size`.

`fallback_by_reason` 인덱스: 1 too_few_points, 2 not_lattice, 3 duplicate_points, 4 collinear_input, 5 ambiguous_step, 6 loop_guard.

| 환경 변수 | 값 | 기본 |
|---|---|---|
| `OUTRIGGER_HULL_HOOK` | `off` \| `fast` \| `shadow` \| `dump`(대소문자 무관) | 없음 = off |
| `OUTRIGGER_HULL_HOOK_DUMP` | 덤프 파일 경로(`.ohull`) | 없음 |
| `OUTRIGGER_HULL_HOOK_DUMP_EVERY` | 정수 ≥ 1 | 1 |
| `OUTRIGGER_HULL_HOOK_DUMP_MAX` | 정수(0 = 무제한) | 0 |

모드:
- **off**: 원본 그대로(슬롯 원복).
- **fast**: 고속 경로를 쓰고, 포기하면 원본을 부른다.
- **shadow**: 원본 결과를 반환한다. 고속 경로도 함께 계산해 둘레·면적·`GetHull` 점을 비트 비교하고, 불일치 입력을 덤프한다. 결과는 off와 같고 비용은 off + fast.
- **dump**: 원본 결과를 반환하고 입력을 표본 추출해 덤프한다(덤프 경로 필요). 1 cm 패드 패치 하나가 약 16 KB/호출이므로 `DUMP_EVERY`/`DUMP_MAX`로 줄인다.

설치 조건(하나라도 어긋나면 설치하지 않고 오류 코드 반환):
- 두 DLL 파일의 SHA-256이 검증한 빌드와 같아야 한다.
  - `Chrono_core.dll` = `889b0d9d20c93f4933faa94ea8757b25287780c20039cc406db7dae47fadd502`
  - `Chrono_vehicle.dll` = `8f4a843ecc9bd2e4d9e4ffb3e1d2da6e8704c4f66c4627568da6687b58b69f62`
- 슬롯 4개가 모두 있고, 각각 `Chrono_core.dll` export 주소를 가리켜야 한다.
- pychrono를 갱신하면 설치가 `hash_mismatch`로 거부된다. 새 빌드는 G-A를 다시 통과한 뒤 상수를 갱신한다.

호출 시점과 스레드:
- `import pychrono.vehicle`(Chrono_vehicle.dll 적재) 뒤, **SCM 스텝을 돌리기 전**에 설치한다.
- 설치·제거는 스텝 중에 부르지 않는다. 카운터는 언제든 읽어도 된다.
- DLL을 `FreeLibrary`로 내리면 슬롯을 자동 원복한다.

### Python 연동 예 (cad-expert 참고용, 이 폴더에서는 실행하지 않음)

```python
import ctypes, os
import pychrono.vehicle  # Chrono_vehicle.dll을 먼저 적재

class HookStats(ctypes.Structure):
    _fields_ = [(n, ctypes.c_uint64) for n in (
        "calls", "fast_computed", "fallback", "shadow_compared", "shadow_mismatch",
        "dumped_records", "non_jarvis_calls")] + [("fallback_by_reason", ctypes.c_uint64 * 8)]

hook = ctypes.CDLL(r"...\03_src\outrigger_sim\native\chrono_hull\bin\chrono_hull_hook.dll")
hook.chrono_hull_hook_status_string.restype = ctypes.c_char_p
status = hook.chrono_hull_hook_install_from_env()      # OUTRIGGER_HULL_HOOK 없으면 off
if status != 0:
    raise RuntimeError(hook.chrono_hull_hook_status_string(status).decode())
# ... SCM 실행 ...
stats = HookStats()
hook.chrono_hull_hook_get_stats(ctypes.byref(stats), ctypes.sizeof(HookStats))
```

## 시험 (G-A)

실행할 때는 `PATH` 앞에 `Chrono-dev\Library\bin`을 둔다. env 자체는 바꾸지 않는다.

```powershell
$env:PATH = "C:\ProgramData\miniforge3\envs\Chrono-dev\Library\bin;$env:PATH"
build\hull_equivalence_test.exe --cases 1000000 --threads 4 --out eq.json   # 무작위·격자·퇴화
build\hull_equivalence_test.exe --dump patches.ohull --out eq_dump.json     # 실제 SCM 패치 덤프
build\hull_bench.exe --out bench.csv --samples 300                          # 호출당 시간
build\hook_scm_smoke.exe off 3000; build\hook_scm_smoke.exe fast 3000       # state_hash 비교
```
- 종료 코드: 0 = 불일치 없음, 1 = 불일치, 2 = 인자·입력 오류.
- 동치 시험의 정답은 conda `Chrono_core.dll`의 export 생성자다.
- 같은 결과를 원본 소스의 로컬 사본(`tests/reference_jarvis.h`)과도 비교해, 이 빌드의 부동소수 코드 생성이 conda 빌드와 같은지 함께 확인한다.
