# 436.9 판 8 5단계(G′ V0 사전 실행) 판정서 — 실행 C8 `56849248` · 판정 T8⁗ `7ea78232`

작성: control-expert, 2026-11-28. **상태: 초안 개정 2(커밋 전 감사 반영).** 개정 2는 커밋 전 감사 `ed8_design/audit_ed8_closing/verif_ed8_closing_precommit.md`(`6638a4db…`, 차단 0)의 M-1~M-6과 R-2·R-5·R-7을 반영했다(0절 45행, 2.2, 4절 3·13, 5절, 6.2, 7절, 8절, 9절, 10.2). 판정 내용은 바꾸지 않았다. 개정 1은 앞 초안(메인 저장본 sha `ba2f09f1…`)에 다음을 반영했다. 판정을 새로 내리지 않았다.
- 사용자 결정 `ed8_design/stage5_decisions/decision_stage5_20261128.md`(이하 "결정 5단계-n")
- verif 결함 독립 확인 `ed8_design/audit_stage5_prerun/verif_stage5_defect_check.md`
- dynamics 원인 분석 `ed8_design/stage5_aa_cause/aa_cause_analysis.md`

**5단계 상태: stop(유지).** 결정 5단계-1 (가).
- 도구가 낸 사유 "E A/A failures 2 >= 2"는 규칙 사유가 아니다. 판정 도구 슬롯 키 결함(2절)이 낳은 값이기 때문이다.
- 판정서에 적는 멈춤 근거는 N층 A/A 상한이다. 자기 짝 A/A 실패가 최소 6이고, CP(6, 312) = 0.0376 > 0.025(규칙 307행)다.
- 이 하한은 결과를 본 뒤 감사자가 센 값이고, 사전 등록 도구의 계산이 아니다(2.4).
- 판정 커밋 T8⁗는 바꾸지 않는다. 그래서 재판정하지 않고, 4단계도 다시 판정하지 않는다.
- 판 8은 5단계 멈춤으로 종료한다(결정 5단계-2). 6단계 census·S8-C 봉인·8단계 G′·12a·12b는 하지 않는다. 봉인 규칙 문면은 고치지 않는다.
- 커밋 전에 verif-protocol-auditor 판정 후 감사와 integrity-checker 점검을 받는다.

의존성 점검: 생략했습니다. 제어 수치 설계·해석은 없습니다. 재집계는 건수와 Clopper–Pearson 상한 재계산(dynamics-dev scipy)뿐입니다. Python과 Julia로 비교할 양이 없어 Julia 교차 검증은 해당하지 않습니다.

## 머리말

### 기준 문서·결정
| 문서 | sha256 | 관계 |
|---|---|---|
| 봉인 규칙 `j_p3_cause/jp3_remedy_spec_v8_rules.md`(S8-R 개정 3) | `35f9eba8f98f93ddb0fa850ff60844ebd7a443f819febcdf0906a5502c121520` | 판정 기준(4절 표, 7.1~7.6, 10절, 13절) |
| P8-5 처리 결정 `ed8_design/p85_options/decision_p85_20261128.md` | `1742fa0524e70f74a3db82ac5f688b19fb5d63dd4b3c2c24b58266624671b728` | (나) + (라-2): P8-5 판정 불가 유지, 사용자 결정으로 5단계 진행. 첫 커밋 `0aa6cbb8` 2026-11-28T09:23:30+09:00 |
| P8-5 공개 문안 `ed8_design/p85_options/p85_disclosure_text.md` | `42614b21e37cfa2d24cb370cd4a1b052c393db62903226c7e834f0688f682ced` | 최종 판정서 공개 칸용(6.3) |
| 결정 D-2 `ed8_design/audit_t8ppp/decision_d2_p80p85_20261127.md` | `0a636250b69afe3bc080220701de1d51ffa25511cd281f6801f0e0a330c69808` | 5: 판 8 종합 표기 |
| 4단계 판정서 `ed8_design/stage4_judgement/stage4_judgement_ed8.md`(개정 5, 커밋 `acba3304`) | `fb0f41321dedc65edc2d81f35d8c0938b93ddeb393809b5f27c07fc1a5bee98a` | 4단계 미완(P8-5 판정 불가) |
| 5단계 실행 전 감사 `ed8_design/audit_stage5_prerun/verif_stage5_prerun.md` | `af3b40b323e1b7711c5c0536cef7f0c0c6149d9f598b136706b7bd7225b41358` | 기록 15(호출 대조) 등 |
| 5단계 판정 전 감사 `ed8_design/audit_stage5_prerun/verif_stage5_prejudge.md` | `05d8dacd2191202ca95c0d535767137441a928a0770978c40f5c0f98681dd257` | "5단계 판정서에 적을 것" 1~13, "판정 뒤 처리 준비" stop 행 |
| 결함 독립 확인(판정 후) `ed8_design/audit_stage5_prerun/verif_stage5_defect_check.md` | `bec52a1478333b89957520041fecacc0105a02860384cdfe31407c0febd119b5` | 주장 1~5 맞음, 발견 기록 1(x_N ≥ 6), 8단계 실행 전 수정 2, 놓친 이유 공개 문장안 |
| 원인 분석 `ed8_design/stage5_aa_cause/aa_cause_analysis.md`(dynamics-expert) | `32c2a68594b77065902b168cacc88698add91babb2bca72036003d42b96b5dfa` | 결과 본 뒤의 분석, 기록(5절) |
| 5단계·판 8 종료 결정 `ed8_design/stage5_decisions/decision_stage5_20261128.md` | `7d236aa2495d1a72008e23d06d6a65879fa031f0c3a8d025f5d6d33cacebda7f`(미커밋, 이 개정 작성 중 잼) | 1: (가) stop 유지·사유 정정, 2: 판 8 종료, 3: 진단 실행 시점, 4: 결과 본 뒤의 결정 공개 |

### 판정 정체성
| 항목 | 값 |
|---|---|
| 실행 커밋 C8 | `56849248371b4916e2fe683265e7abffdd6fb8d7`(worktree `ed8-impl`, locked) |
| 5단계 실행 | 2026-11-28. 러너 `~/.claude/runners/outrigger-ed8/stage5/`. `check_pre` 10:44:14, `ho_v0` 10:44:17~11:12:27(1691 s), `ho_aa2` 11:12:29~11:27:04(875 s), `ho_aa3` 11:27:07~11:41:39(874 s), `check_post` ok. 예약 `r-20261128104412-aca21d`는 해제했고, key_presence 오류 줄은 0이다 |
| 판정 커밋 T8⁗ | `7ea782323c427917709ecbb365a58044449beac2`(worktree `ed8-judge4`, locked). 출력 `judge_code`: head `7ea78232…`, `is_clean` true |
| 판정 실행 | 2026-11-28 12:11:50.93~12:11:52.80 KST(`run_console.log`). dynamics-dev `python.exe -I -B jp3_ed8_judge.py stage5`. 출력 mtime 12:11:52.56 |
| 판정 출력 | `j9_runs/56849248/judge_7ea78232_s5/ho_k_selection.json`, sha256 `ff4b1c538ee6468f87191b7bbf2b4463ab0b193922aabd34af71bb02f2d9df04`(이 초안 작성 중 다시 재어 같음) |
| 종료 | stdout 마지막 JSON `{"status": "stop", …}`, `stage5 exit 1`, ps1 `exit 1`(`run_console.log` 2-4행) |

## 0. 판정 요약
- **판정 도구 출력**: `status` **stop**, `reasons` ["E A/A failures 2 >= 2"], 종료 1. 도구가 이 사유로 적용한 규칙 문면은 7.3 4(가)와 7.4 308행(E층 A/A 실패 ≥ 2 → 멈추고 묻는다)이다.
- **판정 도구 결함(2절)**
  - 키 파일 `heldout_g_ed8.json` 339줄의 `slot` 이름은 291개뿐이다. 원천 `a_phase`와 `b_shape`가 48개 이름을 함께 쓴다. 규칙 7.2는 슬롯을 (원천 표지, 슬롯 키)로 정렬한다.
  - 도구는 A/A 짝 사전을 `slot` 이름만으로 만든다(`jp3_ed8_rules.py:464`). 그래서 48쌍에서 나중에 쓴 `b_shape` 슬롯의 짝이 `a_phase` 슬롯의 짝을 덮어쓰고, 수 세기(`_layer_counts` 440행, `aa_summary` 426행)는 그 짝을 두 슬롯에 모두 쓴다.
  - 출력에서 다시 센 결과, 자기 짝이 출력에 남은 E층 슬롯 15개(유일 이름 8 + `b_shape` 7)의 A/A 실패는 **0**이다. 도구가 센 E 실패 2는 N층 `b_shape` 짝의 실패를 E층 `a_phase` 슬롯이 빌려 센 값이다.
  - `a_phase` E층 슬롯(9개) 자신의 A/A 짝은 계산은 됐지만 출력·수 세기에서 사라졌다. 그래서 E층 A/A 실패의 참값은 출력만으로 정할 수 없다. verif 결함 독립 확인은 주장 1~5를 모두 "맞음"으로 확인했다.
- **규칙 분류(결정 5단계-1 (가)): stop.** 판정서에는 도구 사유를 규칙 사유로 적지 않는다.
  - 도구 사유가 무효인 이유: 판정 도구가 슬롯을 `slot` 이름(291)만으로 식별해, 규칙 7.1·7.2·7.4의 (원천, 슬롯) 339단위 가운데 48슬롯을 다른 슬롯의 A/A 짝으로 셌다.
  - 판정서에 적는 멈춤 근거: N층 상한이 문턱을 넘는다. 자기 짝 A/A 실패가 최소 6이고, CP(6, 312) = 0.0376 > 0.025(규칙 307행)다(2.4).
  - 이 하한은 결과를 본 뒤 감사자가 센 값이다. 사전 등록 도구의 계산이 아니다.
  - 10:345 읽기(A/A 세부 기록 결측 → `setting_defect`)는 적용하지 않는다. `a_phase` 48슬롯의 A/A 세부 기록이 빠진 것은 기록 실패로만 적는다(1.2).
  - 결함 자체는 판 9 구현 과제로 넘긴다(2.3).
- **규칙상 하지 않는 것**(3절): 재실행, 재판정, S8-C 봉인, 6단계 census, 8단계 G′, 12a·12b
  - 8단계 판정은 `frozen`을 요구한다(`jp3_ed8_rules.py:540-541`, 판정 전 감사 기록 14). 도구 출력은 frozen이 아니다.
- **N층 점검(7.3 4(나))은 도구가 계산하지 않았다.** E 점검에서 일찍 돌아왔기 때문이다(`jp3_ed8_rules.py:477-479`).
  - 출력의 `layers.N.cp95` 0.0541은 결함의 영향을 받은 수(x 10, n 310)다.
  - 멈춤 근거는 위 하한이다.
- **A/A 값을 본 것이 됐다.** 이 판정서 뒤의 결정(결정 5단계-1~4)은 모두 결과를 본 뒤의 결정이다(6.3).
- **판 8 종합 표기**(결정 5단계-2)
  - D-2 5 문장(글자 그대로): "판 8 결과 판정 통과, 구현 확인 P8-5 판정 불가(사용자 결정으로 진행)"
  - 이 문장은 결과 판정이 있을 때를 위한 것이었다. 판 8 결과 판정은 G′(8단계)·census(6단계)에 이르지 못했으므로 종합 표기는 판 8 종료 판정서의 문안으로 바꾼다. 결정문 문안은 "판 8 5단계 멈춤(G′ V0 A/A N층 바닥 초과), 결과 판정 미실시, 구현 확인 P8-5 판정 불가"다.
- **원인 분석**(5절, 결과 본 뒤의 기록)
  - 실제 A/A 실패는 N층에 있다. 기전은 10 Hz 표본 위상에 따른 가짜 D1 FAULT 3건과 1회성 경고 J7 플립 8건이다.
  - E층 자기 짝 A/A는 0/24다.

## 1. 판정 출력 옮김(`ho_k_selection.json`)

### 1.1 상태·사유·층(출력 그대로)
| 키 | 값 |
|---|---|
| `rule` | "jp3_remedy_spec_v8_rules.md 7.3 .. 7.5 (stage 5, V0 only), T8" |
| `status` | `stop` |
| `reasons` | ["E A/A failures 2 >= 2"] |
| `status_basis` | `failures` [], `setting_defects` [], `not_judgeable` [] |
| `identity_defects` | [] |
| `first_aliases` | [](1차 별칭 0) |
| `n_before_merge` | E 24, N 312 |
| `merged` / `merged_why` | false / null |
| `layers.E` | n 24, x_aa 2, n_aa 22, cp95 0.25946653222843696, k null, mde80 null |
| `layers.N` | n 312, x_aa 10, n_aa 310, cp95 0.05410248375064101, k null, mde80 null |
| `mde80_definition` | "spec 7.5 MDE80: least p with P(Bin(n, p) > k) >= 0.8, independent units, k the frozen layer k; published table used n_AA = n_N (f4_checks.py:43-44)" |
| `spec_v8_sha256` | `35f9eba8…`(규칙과 같음) |
| `run_commit` | `56849248…` |
| `judge_code` | checkout `ed8-judge4`, head `7ea78232…`, `is_clean` true |

- `status_basis`가 비어 있는데도 상태는 stop이다. 멈춤은 상태 순서(10:338)의 목록 밖이고, 도구는 사유를 `reasons`에 적는다(`jp3_ed8_rules.py:509`).
- `k`·`mde80`은 frozen일 때만 계산한다(505-507행). 그래서 null이다. `<S8C_HO_K_SELECTION_SHA256>`을 채울 동결 값은 없다.

### 1.2 A/A 요약(`aa_summary`, 출력 그대로)
| 층 | `same_hash_slots` | `same_hash_with_same_layer_after` | `crossed_tries` | `none_in_layer_slots` | `pairs` |
|---|---|---|---|---|---|
| E | 0 | 0 | 14 | 2 | 22 |
| N | 0 | 0 | 22 | 3 | 312 |

- 주의: `aa_summary`(426행)도 2절의 이름 사전을 쓴다. 이 수는 결함의 영향을 받는다. 참값은 N `none_in_layer` 3, E 0이다. 출력의 E 2는 빌린 짝에서 나왔다(verif 결함 확인, 기록 "`aa_summary`는 결함의 영향을 받는다").
- **기록 실패(결정 5단계-1)**: `a_phase` 48슬롯의 A/A 세부 기록(10:344의 기록 항목 "A/A 세부")이 출력에 없다. 10:345 닫힌 목록 밖이지만, 결정에 따라 `setting_defect`로 읽지 않고 기록 실패로만 적는다. 판정 상태를 바꾸지 않는다.

### 1.3 기록 항목(출력 그대로)
- `aa_item_scope`: items "C-J (i) J1..J11", `own_setting_items` {J11: V0}, `structural_no_input` [J9, J11], basis "control_nb1_decision.md 1.4"
- `aa_j11_states`: {"입력 없음": 336}(기대 "입력 없음"과 같음). 슬롯 목록을 직접 세므로 이름 결함과 무관하다.
- `aa_shape_record`(stats Q-3, 기록): harsher 짝 10·실패 1, milder 짝 15·실패 0, not_comparable 0·0. `same` 행은 출력에 없다.
  - 경로상으로는 빌린 짝을 읽지만 값은 바뀌지 않는다(verif 결함 확인).
    - `jp3_ed8_judge.py:892-897`은 `base_pass`·`aa_pairs`를 이름으로 읽는다. 그래서 `a_phase` 겹침 48줄은 `b_shape`의 짝·`tries`·`base_pass`를 쓴다.
    - 그러나 `a_phase` 겹침 줄은 조건 job(0/48)과 후보 `aa_order[:3]`(0/144) 모두 `depth_m`·`ramp_s`가 없다. 그래서 `effective_shape`가 둘 다 기본값이고(878-884) `shape_severity`가 `"same"`을 돌려 기록에서 빠진다(869-870). **a_phase 줄은 늘 same이라 빠진다.**
    - `b_shape` 48줄은 이름 사전에서 마지막에 쓰인 쪽이라 자기 짝을 읽는다.
    - 원인 분석의 자기 짝 재계산도 같다: harsher 10/1, milder 15/0(same 309/10)(`aa_cause_analysis.md` 1절 표).
- 슬롯별 `slot_layers`·`aa_pairs`는 출력에 각 291항목이다(키 파일 339슬롯). 2절 결함의 직접 증거다.

## 2. 판정 도구 결함: A/A 짝 기록이 유일하지 않은 슬롯 이름으로 묶여 있다

### 2.1 사실
| 확인 | 결과 | 근거 |
|---|---|---|
| 키 파일 줄 수와 이름 수 | 339줄, 서로 다른 `slot` 291, 두 번 쓰인 이름 48(모두 2회) | `ed8_design/keys_seal_41e107e9/heldout_g_ed8.json`(`a18b5818…`, 출력 `inputs.keys`와 같음). 이 초안의 즉석 스크립트(건수·필드 이름만) |
| 원천별 | `a_phase` 171, `b_shape` 48, `c_fs` 120. 겹치는 48 이름은 모두 (`a_phase`, `b_shape`) 짝 | 같음. 줄 필드 `source`가 있고 (`source`, `slot`)은 339개 모두 서로 다름 |
| 키 파일 순서 | 겹치는 48 이름 모두 `b_shape` 줄이 뒤다(줄 순서: a_phase → b_shape → c_fs) | 같음. 규칙 7.2 "정렬: (원천 표지, 슬롯 키) 문자열 오름차순" |
| 규칙의 슬롯 정체 | 7.1은 (가) 새 위상 171슬롯과 (나) 깊이·램프 48슬롯을 "그중 RE1bF 군집 48"에서 만든다. 그래서 (나)는 (가)와 같은 군집·이름을 갖는다 | 규칙 278-279·285행 |
| 도구의 슬롯 이름 | `slot_inputs`가 키 파일 `line["slot"]`을 그대로 쓴다 | `jp3_ed8_judge.py:1167` |
| A/A 짝 사전 | `pairs = {slot["slot"]: aa_pair_of(slot) for slot in kept}`. 같은 이름이면 나중 것이 남는다 | `jp3_ed8_rules.py:464` |
| 층 수 세기 | 슬롯마다 `pairs[slot["slot"]]`을 읽어 그 슬롯 자신의 층에 센다 | `jp3_ed8_rules.py:435-444`(440행) |
| 요약 | 같은 사전을 읽는다 | `jp3_ed8_rules.py:419-433`(426행) |
| 출력의 증거 | `slot_layers`·`aa_pairs` 각 291항목. 그러나 `n_before_merge` 합은 336이다(n은 기준 V0 통과 슬롯만 셈) | 출력. 사전 항목 수 < 센 단위 수 |

### 2.2 영향(출력만으로 다시 셈, 기준 V0 통과 여부는 기록에 없어 무시)
| 슬롯 묶음 | 층 | 슬롯 수 | A/A 짝(`pair`) | 실패 | 비고 |
|---|---|---|---|---|---|
| 유일 이름(243) | E | 8 | 8 | 0 | 자기 짝 |
| 유일 이름 | N | 235 | 234(`none_in_layer` 1) | 6 | 자기 짝 |
| 겹치는 이름, 출력에 남은 `b_shape` 짝(48) | E | 7 | 7 | 0 | 자기 짝(마지막에 씀) |
| 같음 | N | 41 | 39(`none_in_layer` 2) | 3 | 자기 짝. 같은 이름의 `a_phase` 슬롯도 이 짝을 빌려 씀 |
| 겹치는 이름의 `a_phase` 슬롯(48) | 출력에 층 없음 | 48 | 자기 짝은 계산됐지만 출력·수 세기에 없음 | 미상 | 빌린 짝으로 셈 |
| **도구 합계** | E | n 24 | n_aa 22 | **x_aa 2** | |
| **도구 합계** | N | n 312 | n_aa 310 | **x_aa 10** | |

- **읽기**(산술)
  - 자기 짝이 출력에 남은 E층 슬롯 15개의 실패는 0이다. 그런데 도구 E 실패는 2다. 그러면 그 2는 E층 `a_phase` 슬롯이 N층 `b_shape` 슬롯(실패 3 중)의 짝을 빌려 센 값이다.
  - N층 x_aa 10 = 유일 6 + `b_shape` 3 + 빌려 센 1이다. 이 마지막 1은 산술상 맞춘 값이다. 원인 분석은 이 1을 줄 190(`b_shape`)의 실패가 같은 이름의 `a_phase` 슬롯에 한 번 더 세어진 것으로 특정했다(`aa_cause_analysis.md` 1절 표 "같은 원인의 다른 영향").
  - **E층 멈춤 사유는 E층 자신의 A/A 실패에서 나온 것이 아니다.** E층 A/A 실패의 참값은 `a_phase` E층 슬롯의 자기 짝에 달렸고, 출력에 없다.
- 층 배정(`layer`)은 슬롯마다 자기 줄로 정하므로 `n_before_merge`(E 24, N 312)는 결함의 영향을 받지 않는다. `_layer_counts` 438-439행은 `slot["layer"]`·`slot["base_pass"]`를 슬롯 자신에서 읽고, 층은 `slot_inputs`가 줄마다 정한다(`jp3_ed8_judge.py:1146`; verif 결함 확인 주장 4로 확인). 따라서 7.3 2·3(E 합침 16, $n_N$ ≥ 200)의 판단은 영향이 없다. `aa_j11_states`(1172-1181)와 1차 별칭 목록(462, 0건)도 영향이 없다.
- 보충(verif 결함 확인 주장 3a·3c)
  - 336은 남은 슬롯 수가 아니라 기준 V0 통과 수다. 1차 별칭이 0이라 남은 슬롯은 339이고, 기준 V0 실패 3은 모두 N층이다.
  - 자기 짝이 남은 E층 15개는 c_fs 8 + b_shape 7이다(앞 초안의 "유일 이름 8"은 c_fs 8).
  - `a_phase` E층 9슬롯은 전부 겹치는 이름이다. E 후보 사건은 RE1bF(6.3)이고 (나) 원천이 RE1bF 48군집이므로(7.1:279), 결함이 E층 전체에 걸린다.
  - 빌린 두 실패는 N층 `b_shape` 슬롯의 짝이다.
  - 원인 분석은 줄 번호로 특정했다: E 줄 10이 줄 173의 짝을, E 줄 28이 줄 179의 짝을 받았다. 두 E 슬롯의 자기 짝은 통과다(`aa_cause_analysis.md` 1절).

### 2.3 규칙·선례와의 관계
- 규칙 7.4는 "A/A 짝은 V0($o''$)의 층이 V0($o$)와 같을 때만 기회로 센다"이다. 슬롯마다 자기 짝을 세라는 뜻이다. 빌린 짝을 세는 것은 규칙 문면과 다르다.
- 같은 꼴의 선례: 4단계 P8-0(T8‴). 공용 줄 키가 `setting`을 떼어 114 job이 27키로 접혔다. 결정 D-2 1은 이를 "판정 도구 줄 키 결함에 따른 판정 불가"로 분류했고, 고친 판정 커밋으로 다시 판정했다(4단계 판정서 O8-14).
- 생산자는 슬롯 정체를 (원천, 키)로 둔다(`ed8_key_lists.py:508` 정렬, `:539` `{"source": …, "slot": …}`; verif 결함 확인 주장 1a). 판정 도구만 `jp3_ed8_judge.py:1167`에서 `slot`만 넘기고 `source`를 버린다. 규칙 문면도 생산자도 같은 정체를 가리키므로 규칙 해석 문제가 아니라 판정 도구 결함이다.
- 결정 5단계-1 (가)로 판정 커밋은 바꾸지 않는다. 그래서 4단계 재판정(4단계 판정서 3절)은 생기지 않는다.
- **결함이 닿는 곳(판 9 구현 과제, 결정 5단계-1)**
  - 5단계: `jp3_ed8_rules.py` 464(짝 사전)·440(`_layer_counts`)·426(`aa_summary`)·468(`slot_layers`)·484(합침 경로, 이번엔 닿지 않음), `jp3_ed8_judge.py` 892-897(`aa_shape_record`)·1167(`slot_inputs`)
  - 8단계: `jp3_ed8_judge.py` 1278(단위 `id`·`slot`), `jp3_ed8_rules.py` 544·551(1차 별칭 이름 집합)·584-589(`_unit_layer`)
  - 기록 문구: `jp3_ed8_judge.py` 1269·1277·1285(`not_judgeable`·`fault_basis` 문구가 이름만 씀), `jp3_ed8_rules.py` 180(병합 구성원 `members`에 같은 id가 둘씩)
  - 시험: 기록 항목 수 = 입력 줄 수, 이름이 같은 합성 슬롯
  - 결정문 목록 밖(verif 결함 확인 위임 목록에만 있음): `jp3_ed8_rules.py` 462(`first_aliases` 이름 목록), 558(eps 병합 행 키 `"row": unit["slot"]`). 둘 다 이번에는 영향이 없고 키가 이름이다(판 8 종료 판정서 4.1 표).
- **8단계 영향**(verif 결함 확인 "실행 전 수정" 2건, 이번에는 8단계에 가지 않으므로 판정에 닿지 않음)
  - **층 배정**: `_unit_layer`(584-589)가 `selection["slot_layers"][unit["slot"]]`, 곧 이름 사전을 읽는다. 그래서 `a_phase` 48단위가 `b_shape` 슬롯의 층을 받는다. 층이 다른 쌍이 적어도 2개 있다. E가 합쳐지지 않은 상태로 8단계에 가면 단위가 잘못된 층에 세어진다. 판정에 영향을 준다.
  - **1차 별칭 제외**: 544·551이 이름 집합을 쓴다. 겹치는 이름 하나가 별칭이면 두 원천의 단위가 모두 빠진다. 이번에는 별칭이 0건이라 영향이 없지만 코드 경로는 결함이다.
  - eps 병합(위상 `"o"`가 `EPS_MERGE_PHASES` 밖, 44·156-162·558)은 원천 사이 병합을 만들지 않는다. 해시 병합(151-155)은 규칙 6.2 (가)다. 다만 `members` 기록이 모호해진다(10:344 기록 항목).
  - **시험 공백**
    - 끝까지 도는 시험 `test_t2_stage5_end_to_end_on_the_sealed_jobs_is_judgeable`(`05_tests/unit/test_ed8_t8pp.py:199-206`)은 실제 키 파일로 돌지만, 단언은 `status ∈ {frozen, stop}`, 종료 코드, `aa_item_scope`, J11 상태, `identity_defects` 넷뿐이다. `len(slot_layers) == 339`를 보지 않는다.
    - 규칙 단위 시험의 합성 슬롯은 `N{i}`·`E{i}` 유일 이름이다(`test_ed8_judge_rules.py:196-200`). 이름 충돌 경로가 한 번도 돌지 않았다.
- **감사자 도구 공백**(verif 결함 확인 기록): `record_check.py identity heldout_g_ed8.json --unique slot --expect-distinct 339 --expect-count 339`는 json 최상위가 dict(`lines` 목록)라 파일 전체를 레코드 하나로 본다(`records 1`). `--list-key`가 없다. 그래서 종료 1이 나오지만 이름 중복 때문이 아니라 구조 때문이다. 지금 도구로는 "이 꼴은 `record_check --unique`로 잡힌다"가 성립하지 않는다. 판 9 전에 `tools/verif` 후보로 넘긴다.
- **실행 전·판정 전 감사와 작성자가 놓친 이유**(공개 문장, verif 결함 확인 "놓친 이유" 문장안 그대로)

  > 5단계 실행 전 감사(af3b40b3)와 판정 전 감사(05d8dacd)는 키 파일에서 줄 수(339), 설정 분포, 배치 안·배치 사이 job 키 유일성(1356개 모두 다름), 판정 키 존재를 확인했다. 그러나 판정 도구가 사전 키로 쓰는 `slot` 필드의 유일성은 세지 않았다. job이 모두 다르다는 사실이 식별자가 겹친다는 사실을 가렸다. 규칙↔도구 대조(7.4 행)는 슬롯 하나 안의 짝 고르기 논리만 대조했고, 그 결과를 담는 사전의 키는 대조하지 않았다. 판정 전 감사는 "판정 도구가 실제 입력으로 끝까지 도는지"를 검사하지 못한 것으로 적었고, 그 대신 기댄 T8″ 끝까지 도는 시험은 상태 종류만 단언하고 기록 항목 수를 단언하지 않았다. 규칙 단위 시험의 합성 슬롯 이름은 모두 유일했다. 또 명세 7.1은 (나) 원천을 (가) 원천의 군집에서 만들어 같은 슬롯 키를 갖게 했지만, 정체를 (원천, 슬롯 키)로 적은 곳은 정렬 문장(7.2)뿐이고 판정 도구가 쓸 결합 키는 적지 않았다.

  - 명세 작성자는 control-expert다(판 8 S8-R 개정 3).
  - 앞으로 잡을 방법(판 9로 넘김): (1) 실행 전 감사에서 판정 도구의 모든 "레코드 필드 → 사전·집합 키"에 대해 봉인 입력의 서로 다른 값 수와 줄 수를 대조한다. (2) 끝까지 도는 시험에 "기록 항목 수 = 입력 줄 수"를 단언한다. (3) 판정 직후 기록 항목 수와 키 파일 줄 수를 대조한다.

### 2.4 멈춤 근거: N층 A/A 상한(결정 5단계-1, verif 결함 확인 발견 기록 1)
- **성격: 결과를 본 뒤 감사자가 센 하한이다.** 봉인 뒤 고정한 판정 도구의 계산이 아니다. 판정서는 이 성격을 공개하고 이 하한을 멈춤 근거로 적는다(결정 5단계-1).
- 출력만으로 낸 구조 수
  - E층: 슬롯 24, n_E 24, 기준 통과 24/24
  - N층: 슬롯 315, n_N 312. 기준 V0 실패 3은 모두 N층이다.
  - `aa_j11_states` 합 336 = 판정된 짝 수. 339 − 336 = 3은 짝이 없는 슬롯이고 `none_in_layer` 3과 같다. 따라서 덮어써진 `a_phase` 48슬롯은 모두 자기 짝이 판정됐다.
- 하한 계산
  - 남은 N층 항목 276개(유일 이름 235 + `b_shape` 41)의 **자기 짝** 실패는 9다(유일 6 + `b_shape` 3). `b_shape`는 사전에 마지막으로 쓰인 쪽이라 자기 짝을 읽으므로 이 3은 유효하다.
  - 앞 초안은 이 `b_shape` 3을 빼고 세어 하한을 3까지 낮췄다. verif가 바로잡았다.
  - 기준 V0 실패 슬롯은 N층에 3개뿐이다. 그래서 $x_{AA,N}$ ≥ 9 − 3 = **6**이고, $n_{AA,N}$ ≤ 312다.
  - 단측 95 % Clopper–Pearson 상한은 x에 대해 늘고 n에 대해 준다. 그래서 CP95 ≥ **CP(6, 312) = 0.037602** > 0.025(규칙 307행)다.
- 고친 도구(같은 짝 판정, 키만 (원천, 슬롯))로 셌다면
  1. 1차 별칭 0, n_E 24 ≥ 16이라 합치지 않는다. n_N 312 ≥ 200이라 판정 가능하다.
  2. E 점검: n_AA,E = 24이고, x_AA,E는 `a_phase` E 9슬롯 자기 짝의 실패 수다(출력에 없음).
  3. 2 이상이면 E 사유로 멈춘다. 2 미만이면 N 점검으로 가고, 위 하한으로 멈춘다.
  - 어느 경우든 **stop**이다. 사유만 E 또는 N이다.
- 독립 재계산(verif, 이항 정의에서 이분법)

  | (x, n) | CP95 |
  |---|---|
  | (10, 310) | 0.054102(도구 값과 같음) |
  | (2, 22) | 0.259467(도구 값과 같음) |
  | (6, 312) | 0.037602 |
  | (6, 310) | 0.037842 |
  | (6, 336) | 0.034939 |
  | (5, 312) | 0.033399 |
  | (3, 312) | 0.024663 |

- 한계
  - 이 하한은 도구의 후보별 짝 판정(`aa_pair_verdict`, C-J (i) 항목)이 맞다고 보고 센다. 이 판정은 이름 충돌과 무관한 경로다.
  - verif는 jsonl을 열지 않아 독립 재판정은 하지 않았다.
  - 원인 분석은 판정 도구 함수로 고유 이름(`<source>|<slot>`) 재계산을 해 E 0/24, N 11/310, CP95 0.058051을 냈다(5절). 하한 6과 어긋나지 않는다. 판정 근거로는 결정 5단계-1의 하한(6, 312)만 쓴다.

## 3. 규칙·결정에 따라 하지 않는 것
| 하지 않는 것 | 규칙 원문·결정 |
|---|---|
| 재판정·판정 커밋 교체·4단계 재판정 | 결정 5단계-1: "판정 커밋 T8⁗ 7ea78232는 바꾸지 않는다. 그러므로 재판정하지 않고, 4단계도 다시 판정하지 않는다." |
| 12a·12b, 판 8 계속 | 결정 5단계-2: 판 8은 5단계 멈춤으로 종료하고 판 9로 넘어간다. 규칙 문면은 고치지 않는다(211행 꼴) |
| 재실행 | 208행: "판정 실패는 멈추고 묻는다. 재실행하지 않는다." 판정 전 감사 stop 행: "멈추고 묻는다. 재실행하지 않는다." 판정 도구를 다시 돌리면 새 `--out`·새 numba 폴더가 필요하고 공개한다(판정 전 감사 212행) |
| A/A 멈춤 뒤 진행 | 307행: "N층(합침 뒤 포함): 단측 95 % Clopper–Pearson 상한 > 0.025면 멈추고 묻는다. **$n_{AA,N}$ = 0이면 멈추고 묻는다.**" 308행: "E층(합치지 않은 경우): A/A 실패가 2 이상이면 멈추고 묻는다. **$n_{AA,E}$ = 0이면 E를 N에 합친다**" |
| S8-C 봉인 | 4절 표 7단계는 census(6단계) 뒤. 7.4 305행: "$x_{AA}$·$n_{AA}$(층별, 합침 뒤에는 합친 값)는 5단계 값으로 동결하고 S8-C에 봉인한다." 동결 값(`k`)이 없다 |
| 6단계 census | 결정문 1742fa05 1번: "6단계는 5단계 판정 뒤 다시 묻는다." |
| 8단계 G′ | 8단계 판정은 `selection["status"] == "frozen"`을 요구한다(`jp3_ed8_rules.py:540-541`, 판정 전 감사 기록 14) |
| 규칙 변경 | 결과(A/A 값)를 본 뒤의 개정이 된다. 하면 공개한다(판정 전 감사 stop 행) |

## 4. 실행·입력 기록(판정 전 감사 "5단계 판정서에 적을 것" 1~13)
1. **결정문**: `decision_p85_20261128.md` `1742fa05…`, 첫 커밋 `0aa6cbb8` 2026-11-28T09:23:30+09:00. `check_pre` 10:44:14, 첫 시작 10:44:17, 첫 `.done` 11:12:27. timeline 6/6 `before`(판정 전 감사 기록 7).
2. **러너·단계 스크립트는 4단계 `.done`만 본다.** 판정 상태는 읽지 않는다(실행 전 감사 기록 2, 판정 전 감사 기록 13). 6단계 `step6_census_ed8.ps1`도 `ho_v0.done`만 요구한다.
3. **판정 명령**: `ed8_design/stage5_prejudge/run_stage5_judge_t8pppp.ps1` sha256 `9482528cb72612b49e71592821b6f21b112832d4d759899ea3f167632539144a`
   - 판정 전 감사 때는 `10a8095e`였다. 실행 전 수정 1 (가)로 `--out`을 새 폴더 `judge_7ea78232_s5\`로 옮겨 바뀌었다.
   - 같은 폴더 `SHA256SUMS` `ad466c57fdaee4077f6a36e11b60a05034367ee8f0706e1fe1d4bbe03e75820d`. 감사 때 값 `a3d2b446`에서 바뀌었다.
   - 작성 시각(감사 때 판): Write 11:48:46, 마지막 Edit 11:49:13, `grid_blobs.txt` 11:50:02, SUMS 11:50:23. 바뀐 판(실행 전 수정 1 (가) 반영, python-expert 12:09:55~12:11:16 구간): ps1 마지막 수정 12:10:40.733, SUMS 12:10:51.790. 둘 다 판정 시작(12:11:50.93) 전이다(커밋 전 감사 M-2).
   - 폴더는 미추적이었다(판정 전 감사 기록 7).
4. **저장 격자 4개**: `grid_blobs.txt` `673d0c927b407fd164284342a3e863bb89d8b33871df72f43718f68e05da8318`. main HEAD `0aa6cbb8`, 마지막 수정 커밋 `7320f005`(2026-11-05), 4파일 clean, `text: unspecified`

   | hash-object = HEAD blob | sha256 raw | sha256 LF | bytes | path(`06_analysis/02_control/touch_phase/acceptance/c4g2_only/grid/`) |
   |---|---|---|---|---|
   | `1f88d9c98760353e90dbcdc6c00123c320cf8020` | `a2e74481…316d` | `0496e08f…e370` | 503144 | `grid_r67_main.json` |
   | `8797afe1dd3e9d4dbe7508c1070eda330d6cfe57` | `1d07e49f…2559` | `f0a56208…cee` | 501873 | `grid_r67_top.json` |
   | `d4f3f8c69358f858daa34144e3531cda6fb9919e` | `91026c46…8a89` | `ac5df53e…3929` | 481989 | `grid_r69_bottom.json` |
   | `33e7508d5f027aef1884066f43e28bce183e8b9c` | `87e8d72a…2390` | `256f2d79…494c` | 501858 | `grid_r69_top.json` |

   - 세 커밋(`0aa6cbb8`·`56849248`·`7ea78232`)에서 blob이 같다(판정 전 감사 기록 4).
   - 판정 도구는 이 파일들을 고정하지 않고(`GridStore`, 이름으로 읽음) ps1이 고정한다. raw sha는 줄바꿈에 따라 바뀐다(작업 트리 `w/crlf`).
5. **입력 sha**
   - 키 `heldout_g_ed8.json` `a18b5818…`, 격자 키 `confirm_b_grid192.json` `4e80e69b…`(둘 다 출력 `pinned` true)
   - jsonl 3: `ed8_heldout_v0.jsonl` `fd5f85f5…`, `ed8_heldout_aa2.jsonl` `182dcaab…`, `ed8_heldout_aa3.jsonl` `a2d65df1…`
   - `.done` 3: `ho_v0` `c5f2df09…`, `ho_aa2` `6432bccb…`, `ho_aa3` `4669f443…`(출력 `inputs.v0_rows`와 같음)
   - `.identity.json` 3: `696fd2ab…`/`03cdd535…`/`c38d8d25…`(판정 전 감사 기록 3)
   - `_identity_checks\ho_*_a1.md`: `176cafb8…`/`c17c3fde…`/`ea07a503…`
   - V0 사전 실행 목록 `j9_runs/56849248/ho_v0_prerun.SHA256SUMS` `5c41c18336f315f5bd3b365d41fb04146b15073b4141f8c9ef5263fd6ccf9f6c`(27항목) = `<S8C_V0_PRERUN_SUMS_SHA256>` 후보(판정 전 감사 확인 필요 1). S8-C는 봉인하지 않는다(3절).
6. **판정 checkout**
   - 출력 `judge_code`: head `7ea78232`, clean
   - ps1 사후 점검: HEAD와 `status --porcelain --ignored`를 보고, 다르면 종료 4다(`run_stage5_judge_t8pppp.ps1:129-141`). 종료 1이므로 통과다.
   - 이 초안 작성 중 다시 확인: ed8-judge4 HEAD `7ea78232`, `status --porcelain --ignored` 0줄
   - 판정 시각은 `run_console.log`(sha256 `471314fc88d434f020676ba99f6bbc30ed77ff2dce1b23fab837ef270ce11ae6`): start 12:11:50.93, end 12:11:52.80. report에는 시각 필드가 없다.
7. **실행 정체성**: dynamics-dev `python.exe` 3.12.15, 스레드 1(MKL/OMP/NUMBA/OPENBLAS), `MKL_THREADING_LAYER` TBB, `affinity_mask 0xffff`, C8 clean. 4단계 7단계와 같다.
   - 4단계와 다른 점: 4단계 `p816·p85·p88·p815`는 `conda run`으로 불렸고, 5단계는 직접 호출이다. 프로세스 안 정체성은 같다(판정 전 감사 기록 3).
   - 판정 도구는 `.identity.json`을 읽지 않는다. 이 대조는 감사의 메타 대조가 유일하다.
8. **실행 시간**: `actual_over_estimate` 0.139 / 0.144 / 0.143(판정 전 감사 기록 10). 규칙 7.6 추정 "680회 1~1.6 h"에 대해 실제는 1356회, 약 57분(1691 + 875 + 874 s)이다.
   - compute history 734~736에 실측을 남겼고, P correction은 0.5762로 되돌렸다(사용자 승인, 메인 기록).
   - `log_errors`는 공허한 관문이다. 러너 로그 7개 모두 `no_errors_line`이다(기록 9).
   - `record.json` `note`는 이름표가 "436.9 J4a step ho_v0"로 틀렸다(기록).
9. **상태별 내용**(stop): 1절. 합치지 않았으므로 E 기전 결과(합쳤을 때의 원래 E 단위 실패 수) 기록은 해당 없음. `aa_item_scope`, `aa_j11_states`("입력 없음" 336), `aa_shape_record`, 1차 별칭 0.
10. **7.4 공개 문장(309행)과 13절 14**(규칙 원문)
    - 309행: "공개: A/A는 처리 팔 귀무 바닥의 하한이다(섭동이 작음). 참 바닥이 A/A의 3배면 권고 N 규칙 거짓 실패는 $p_0^{AA}$ 0.002에서 3.2~11.4 %, 0.005에서 17~30 %이고, 그 경우 A/A 멈춤 확률은 20~27 %다(거짓 실패와 멈춤이 맞바뀜; stats S8-R 3·5절)."
    - 13절 14: "G′ 원천·문턱(339슬롯, Jeffreys 예측, $k_E$ 1, $n_{min}$, E 미달 합침, A/A 같은 층·최대 3회·동결, $n_{AA}$ = 0 처리)은 판 6·7 결과를 본 뒤 정했으나 G′의 판 8 처리 결과는 판정 전에 보지 않는다. A/A는 귀무 바닥의 하한이다(7.4). E는 기전 시험이다(7.5)."
    - G′ VBN 처리 팔은 돌지 않았다(규칙 210행). 판 8 처리 결과는 아무도 보지 않았다.
11. **O 목록**: 6.2.
12. **D-2 5 표기**(글자 그대로): "판 8 결과 판정 통과, 구현 확인 P8-5 판정 불가(사용자 결정으로 진행)". 결과 판정이 없으므로 판 8 종료 판정서의 종합 표기로 바꾼다(결정 5단계-2, 0절).
13. **감사 sha**: 실행 전 감사 `af3b40b3…`, 판정 전 감사 `05d8dacd…`, 결함 독립 확인 `bec52a14…`(머리말 표). 이 판정서와 판 8 종료 판정서의 커밋 전 감사: `ed8_design/audit_ed8_closing/verif_ed8_closing_precommit.md` sha256 `6638a4db08f39dde3e69bea680ac475705b8eea29ca912943790e74e26e7e71c`(차단 0·커밋 전 수정 6·기록 8).

## 5. 원인 분석(결과 본 뒤의 분석, 기록)
- 출처: dynamics-expert `ed8_design/stage5_aa_cause/aa_cause_analysis.md`(sha256 `32c2a68594b77065902b168cacc88698add91babb2bca72036003d42b96b5dfa`), 근거 파일은 같은 폴더(`provenance.json`에 입력 sha·열 정의).
- **성격**
  - 5단계 결과를 본 뒤의 분석이다. 판정이 아니라 기록이다. 재실행은 하지 않았다.
  - [추정]이 남아 있다(기전 시계열 미확인).
  - 확정을 위한 진단 실행은 판 8 종료 판정서를 커밋한 뒤에 한다(결정 5단계-3). 판정에 쓰지 않는 기록이고 판 9 설계 입력이다.
- **방법 공개**
  - T8⁗(`ed8-judge4` 7ea78232)의 판정 도구·실행 경로 모듈을 읽기 전용으로 import해 339슬롯을 다시 계산했다. 원인 분석 1절은 대표 함수(`jp3_ed8_judge.slot_inputs`, `jp3_ed8_rules.aa_pair_of`·`stage5_selection`, `unit_item_verdicts`)만 적었다.
  - 실제 스크립트(`stage5_aa_cause/scripts/*.py`)가 import한 모듈(커밋 전 감사 M-6)
    - `jp3_ed8_judge`(`GridStore`, `stored_cluster_hashes`, `effective_shape`, `shape_severity`, `V`, `TREATMENT_LABEL`, `AA_OWN_SETTING_ITEMS` 포함)
    - `jp3_ed8_rules`
    - `jp3_ed7_judge`(`metric_of`, `t`)
    - `jp3_ed8_gate_judge`(`read_rows`)
    - `ed8_key_lists`(`main_line_starts`)
    - `run_v5`(`job_key`)
    - 이 가운데 `run_v5`·`ed8_key_lists`는 C8 실행 경로 모듈의 ed8-judge4 사본이다(규칙 9:335 범주).
  - `provenance.json`(sha로 인용되므로 고치지 않음) 7행은 `shape_severity`를 더한 5개 함수만 적는다. 위 모듈 목록과 다르다. 이 판정서의 목록이 실제 import 범위다.
  - CLI는 돌리지 않았고 판정 도구는 아무 파일도 쓰지 않았다.
  - "판정 도구를 돌리지 말고" 지시를 받기 전에 이 호출을 이미 했다(분석 문서 1절 공개). 그래서 C-J 항목 판정은 판정 도구 함수가 계산한 값이다.
  - 따로 한 손 대조(`scripts/s10_hand.py`)는 이산 필드만 비교했다.
  - 저장 jsonl 세 개(1356줄 전수)와 키 파일을 읽었다(6.2 O8-48).
- **결론(분석 문서 0절 요약을 옮김)**

  | 질문 | 답 |
  |---|---|
  | 도구가 센 "E A/A 실패 2"의 정체 | 판정 도구 결함(슬롯 이름 충돌). E층 `a_phase` 슬롯 2개(줄 10, 28)가 같은 이름의 N층 `b_shape` 슬롯(줄 173, 179)의 실패 짝을 빌려 셌다 |
  | E층 자기 짝 | 24슬롯 모두 같은 층 짝이 있고(n_AA,E 24), 실패 **0** |
  | 결함이 없었다면 | 그래도 멈춤. 고유 이름 재계산 N층 11/310, CP95 0.058051 > 0.025(판정 도구 함수로 재계산, 기록) |
  | 실제 실패의 기전 | 결정적 하네스에서 **10 Hz 압력 표본 위상**에 따라 결과가 갈린다. (a) 앞다리 RE1bF에서 패드가 10 Hz 표본 직후 0~3 ms 안에 들리면 헤드압 D1 단계 진단이 가짜 FAULT를 낸다(`FAULT_HEAD_PRESSURE` D1_step, **3건**: 줄 173·179·270). (b) 1회성 경고 `WARN_D1_IMU_GYRO_MISSING`이 위상에 따라 생기거나 안 생겨 J7 집합이 갈린다(**8건**: 줄 112·120·228·252·280·190·53·89) |
  | 판 5 선례와 같은 꼴인가 | 아니다. 판 5는 seed에 따라 갈린 LEVEL 완료 교착이었다. 이번은 seed 없는 위상 결정적 진단 FAULT와 경고 집합 차이다 |
  | 층 E 고유 성질인가 | E층 A/A 실패는 관측되지 않았다(0/24). 실제 실패는 모두 N층이고, V0 기준선 자체의 표본 위상 민감도다. (b)는 판정 정의 문제(J7이 위상에 따라 뒤집히는 진단 경고를 셈)이기도 하다 |

- **사실과 [추정]의 구분**(분석 문서 2.3)
  - 사실: 1356줄 가운데 `final_phase = fault`는 8줄이다. 8줄 모두 앞다리 RE1bF, 오프셋 0.0875 s, 사건 다리 들림이 10 Hz 표본 뒤 0.000~0.003 s, 사유 `INFO_HEAD_PRESSURE_FAULT_REASON:<인접 다리>:D1_step`이다. 기준 실패 3슬롯(줄 5·29·181)도 이 FAULT다. 저장 V0 본 위상 {0, 0.025, 0.05, 0.075}에서는 들림 위상이 0.012~0.092 s라 이 창이 표본에 들어간 적이 없다.
  - [추정]: 들림이 표본 직후이면 인접 다리의 한 주기 Δp_h가 가장 커진다. 동시에 지레 보정 없는 f_z(`WARN_D1_IMU_GYRO_MISSING`)로 잔차가 0.5·|Δp_h|A_p 넘게 변해 센서 도약으로 판정된다.
  - 가정: 10 Hz 표본 시각 = 0.1 s 정수배. `max_step_Pa`는 클래스 기본 100 bar로 썼고 R8 프리셋 값은 확인하지 않았다.
- **원인 분류**(분석 문서 4절): (1) 판정 도구 구현 결함(슬롯 식별자), (2) V0 기준선 위상 민감도(N층, 가짜 D1 FAULT 3·경고 플립 8), (3) 판정 정의 — (가) J7이 1회성 진단 경고를 셈, (나) A/A 층 짝짓기가 후보 자신의 결과로 층을 정해 FAULT 줄이 구조상 N이 됨, (다) `b_shape` A/A 짝이 형상도 바꿈.
- **판 9 설계 선택지**: 분석 문서 5절 표(슬롯 식별, D1 가짜 FAULT, J7 경고 플립, 층 E 정의, A/A 문턱, 원천 선택). 결정은 사용자 몫이다. 판 8 종료 판정서 "판 9로 넘길 것"에 옮긴다.
- 이 판정서의 멈춤 근거(2.4)는 원인 분석 값이 아니라 결정 5단계-1의 하한이다.

## 6. 공개

### 6.1 P8-5 공개 문안의 위치
- `p85_disclosure_text.md`(`42614b21…`)의 세 문안(O8-17 보강, 같은 꼴 관문 P8-8·P8-15, 가림 한계)은 결정문 1742fa05 3번대로 **판 8 최종 판정서의 공개 칸**에 넣는다. 결정문 1번 (라-2)의 N-1 전제 시험 범위 기록과 같은 자리다. 이 5단계 판정서에는 sha로만 인용한다.
- 결정 5단계-2에 따라 판 8 종료 판정서(`ed8_design/ed8_closing/ed8_closing_judgement.md`) 공개 칸에 넣는다. (라-2) N-1 시험 범위 기록도 같은 곳이다.

### 6.2 O 목록(O8-39~)
| # | 누가·언제 | 내용 | 노출 | 근거 |
|---|---|---|---|---|
| O8-39 | 메인, 2026-11-28 00:48~09:25 KST | Bash 파이프 6건(메모리·도구 README 조회·수정, 09:24:40 worktree 점검) | 없음(판정 자료 아님) | 실행 전 감사 기록 15 |
| O8-40 | 메인, 00:50·09:25 KST | 메모리 파일 덧붙이기에 `cat >> … <<'EOF'` heredoc 2건 | 없음 | 같음 |
| O8-41 | 서브에이전트, 2026-11-28 | Bash 파이프 4건: integrity-checker 2, 앞 verif 감사 1(`p85_options_verif.md:130`에 공개됨), compute-scheduler 1(09:26:31) | 없음 | 같음 |
| O8-42 | compute-scheduler-expert(ab0a1f3c), 09:26:32·09:26:35 KST | `Glob path=…\j9_runs\56849248` 패턴 `*`·`ho_*`. 4단계 출력 폴더 이름 목록(4단계 판정·커밋 끝난 뒤) | 파일 이름 | 같음 |
| O8-43 | compute-scheduler-expert(aaa89835), 11:45:14~11:45:28 KST | `j9_runs\56849248` 아래 `*.sample.json` 재귀 목록, `ho_v0_a1\logs\*.sample.json`·`*.record.json`·`ho_v0.done` 머리·러너 로그 읽기 | 메타(시간·메모리) | 판정 전 감사 기록 12 |
| O8-44 | long-running-task-monitor(af9863b2), 10:59:45~11:00:06·11:14:52·11:29:44 KST | `Get-Content <jsonl> \| Measure-Object -Line` 3회(v0 376줄, aa2 53줄, aa3 57줄). 진행 중 줄 수 세기. 내용을 파이프로 읽었지만 출력은 줄 수뿐 | 줄 수 | 같음 |
| O8-45 | python-expert(aa2e704f), 11:45~11:50 KST와 12:09:55~12:11:16 KST(두 구간) | (첫 구간) 출력 6개 sha(바이트), 격자 키 `v0_pair.file` 이름, `stage5 --help`, 사전 거부 사본 시험. `step_records.py`(판정 도구 import)는 자동 모드 분류기가 거부해 실행되지 않음. (둘째 구간, 메인 SendMessage 12:09:28 뒤) `run_stage5_judge_t8pppp.ps1` Edit 3회(12:09:55·12:09:57·12:10:40), `stage5_prejudge\SHA256SUMS` 재작성(mtime 12:10:51.790), `j9_runs\56849248\ho_v0_prerun.SHA256SUMS` 작성(12:10:59, jsonl·logs를 바이트 해시만, 내용 해독·출력 없음), `baseline_check sums`. 모두 판정 시작(12:11:50.93) 전 | 없음 | 판정 전 감사 기록 12, 커밋 전 감사 M-2 1 |
| O8-52 | verif-protocol-auditor 판정 전 감사(ab55ca9d), 11:51:55~12:05:15 KST | `ho_*_a1\logs\*.record.json`·`identity_check.log`, `ho_*.done`·`step_record.json`·`.identity.json` 전문(메타), jsonl 3개 sha·크기·mtime, `key_presence` 건수(값 출력 없음), 러너 로그 제어 줄, `judge_7ea78232\` 파일 이름·크기. 스텝 `.log`·`.err`는 열지 않음 | 메타(시간·정체성·건수) | `verif_stage5_prejudge.md` 4-10행, 커밋 전 감사 M-2 2 |
| O8-46 | 메인, 판정 뒤(12:12:00) | 판정 출력의 최상위 키 이름 전체, `status`, `reasons`, `judge_code` head·`is_clean`, ed8-judge4 `status --porcelain --ignored` 줄 수를 출력했다 | 키 이름·상태·사유 | 커밋 전 감사 M-2 3 |
| O8-47 | 이 판정서 작성(control-expert), 판정 뒤 | `ho_k_selection.json` 전체(슬롯별 층·A/A 짝 상태·`aa_fail` 참거짓 포함)를 Read했다. 키 파일 `heldout_g_ed8.json`을 즉석 스크립트로 읽어 이름 수·원천별 수·줄 순서만 냈다(값 출력 없음). 판정 도구 `jp3_ed8_rules.py` 360-513행·`jp3_ed8_judge.py` 1100-1239행을 읽었고 판정 모듈은 import하지 않았다. jsonl·스텝 `.log`·`.err`는 열지 않았다 | 슬롯 이름·층·A/A 참거짓 | 7절 |
| O8-48 | dynamics-expert 원인 분석, 판정 뒤 | 저장 5단계 jsonl 세 개(1356줄 전수)와 키 파일을 읽었다. T8⁗(ed8-judge4)의 모듈 `jp3_ed8_judge`(`GridStore`, `stored_cluster_hashes`, `effective_shape`, `shape_severity`, `V`, `TREATMENT_LABEL`, `AA_OWN_SETTING_ITEMS` 포함)·`jp3_ed8_rules`·`jp3_ed7_judge`(`metric_of`, `t`)·`jp3_ed8_gate_judge`(`read_rows`)·`ed8_key_lists`(`main_line_starts`)·`run_v5`(`job_key`)를 읽기 전용으로 import해 339슬롯을 다시 계산했다("판정 도구를 돌리지 말고" 지시 전에 실행; 5절 방법 공개, `provenance.json`은 함수 5개만 적음). CLI는 돌리지 않았고 worktree에는 쓰지 않았다. P8-2 경로 2 자료는 열지 않았다 | 줄 값 전부(사건·힘·자세·단계), 슬롯별 A/A 판정 | `aa_cause_analysis.md` 머리·1절·근거 파일 |
| O8-49 | verif-protocol-auditor 결함 독립 확인, 판정 뒤 | 판정 출력 `ho_k_selection.json`의 상태·사유·층·요약 키를 화면에 냈고, 슬롯별 `slot_layers`·`aa_pairs`는 스크립트 안에서 묶음별 건수로만 셌다. 키 파일은 줄 수·필드 이름·원천별 수·이름 겹침·줄 순서·job 유일성·형상 필드 유무만 셌다. 판정 도구 코드를 읽었고 import하지 않았다. 5단계 jsonl·스텝 `.log`·`.err`·`run_console.log`는 열지 않았다. **Bash 파이프 1회**: `git ls-tree -r 7ea78232 --name-only -- 04_scripts 03_src \| grep -E "jp3_ed8"`(출력: 판정 도구 파일 이름 3개) | 층·A/A 건수, 파일 이름 | `verif_stage5_defect_check.md` 감사 요약·"이 감사의 규칙 위반 1건" |
| O8-50 | 메인 세션, 판정 뒤 | 결정문 `stage5_decisions/decision_stage5_20261128.md`(`7d236aa2…`)를 썼다. 결정 때 알던 것: 판정서 초안 2절, 원인 분석(고유 이름 재계산 E 0/24, N 11/310, CP95 0.058), verif 하한(x_N ≥ 6)(결정 5단계-4) | 위 세 문서 값 | 결정문 4번 |
| O8-51 | verif-protocol-auditor 커밋 전 감사(a3e8bed7), 12:55 KST~ | `ho_k_selection.json` 최상위 키 구조. 판정서 1.1~1.3 값은 스크립트 안에서 출력과 같은지만 비교(화면에는 OK/BAD). 슬롯별 `slot_layers`·`aa_pairs`는 (원천 묶음, 층)별 건수(n, state, aa_fail 참 개수)로만 셈(판정서 2.2에 있는 값). 키 파일은 줄 수·이름 수·원천별 수·겹침 조합·줄 순서만. `run_console.log` 4줄 전문. 5단계 jsonl 3개와 `logs\*`(.log·.err 포함)는 바이트 해시로만 대조(`ho_v0_prerun.SHA256SUMS` 27항목). 원인 분석 근거 csv·json은 열지 않음(예외 `provenance.json` 입력 sha·import 줄 Grep, scripts import 줄 Grep). 판정 도구 `jp3_ed8_rules.py` 419-443·456-513·536-591행. transcript는 11:45 이후 도구 호출 입력만 파싱. P8-2 경로 2 자료는 열지 않음 | 건수·OK/BAD·로그 4줄 | `verif_ed8_closing_precommit.md` 감사 요약 "본 결과" |

- 판정 대상 값(jsonl 줄 내용, 스텝 `.log`·`.err`, `judge_7ea78232` json 값)을 연 호출은 판정 전 10:30 이후 transcript에 없다(판정 전 감사 기록 12).

### 6.3 결과를 본 뒤의 결정
- 결정 5단계-1~4(분류 (가)·사유 정정, 10:345 비적용, 판 8 종료, 진단 실행 시점)는 모두 5단계 A/A 값을 본 뒤에 내렸다(결정 5단계-4).
- 결정 때 알던 것: 판정서 초안 2절, 원인 분석(고유 이름 재계산 E 0/24, N 11/310, CP95 0.058), verif 하한(x_N ≥ 6).
- 멈춤 근거로 쓴 하한(2.4)도 결과를 본 뒤 감사자가 센 값이다.
- 고친 도구로 셌어도 상태는 stop이다(2.4). 그래서 결과를 본 뒤의 결정이 결과 쪽으로 기울 여지는 사유 문구에 한정된다(verif 결함 확인 발견 기록 1 "함의").

## 7. 경로 2
- 9:332 경로 2 범위에 G′가 있다. 5단계는 V0 사전 실행(기록·공변량)이다. 판정 출력(층·A/A)은 G′ 판정의 입력이다.
- **경로 2 작성자가 열면 안 되는 자료에 더할 것**(규칙 9:335, 4단계 판정서 6절 목록에 덧붙임)
  - `j9_runs/56849248/judge_7ea78232_s5/`
  - `j9_runs/56849248/ho_*_a1/logs/*.log`·`*.err`(run별 `final_phase`·해시)
  - 이 5단계 판정서(`ed8_design/stage5_judgement/`, `run_console.log` 포함)
  - `ed8_design/audit_stage5_prerun/`(실행 전·판정 전 감사, 판정 도구 줄 인용)
  - `ed8_design/stage5_prejudge/`
  - `ed8_design/stage5_aa_cause/`
  - `ed8_design/stage5_decisions/`
  - 판 8 종료 판정서(`ed8_design/ed8_closing/`)
  - 개정 2에서 더함(커밋 전 감사 M-5, 사용자 결정 "둘 다 넣음")
    - `j9_runs/56849248/ho_*_a1/` 전체(jsonl 포함; `final_phase`·해시 등 A/A 결과가 있음), `j9_runs/56849248/ho_*.done`, `j9_runs/56849248/ho_v0_prerun.SHA256SUMS`
    - `j9_runs/56849248/_identity_checks/ho_*_a1.md`
    - 5단계 러너 `~/.claude/runners/outrigger-ed8/stage5/`(사본을 만들면 사본도)
    - `ed8_design/audit_ed8_closing/`(커밋 전 감사)
    - `ed8_design/stage5_aa_diag/`(진단 출력, 8·9절)
    - `ed8_design/p85_options/`
- 메인은 경로 2를 시작하기 전에 이 경로들을 블라인드 목록에 넣는다. 판 8은 5단계에서 끝나므로(결정 5단계-2) 판 8의 경로 2(P8-2·census·G′)는 실행되지 않는다. 위 목록은 판 9 경로 2의 금지 목록 원본이 된다.
- 2절의 결함은 경로 1 판정 도구의 결함이다. 경로 2 작성자에게 넘길 것은 규칙 정의 문장뿐이다.
- **[정의] (원천, 슬롯)**: G′ 단위를 (원천, 슬롯)으로 식별하라는 [정의] 문장은 판 9 규칙 몫으로 넘긴다(결정 5단계-2로 판 8 경로 2가 없어 앞 초안의 확인 필요 C는 닫힘). 판 8 문면은 고치지 않는다.

## 8. 판정서 커밋에 넣을 근거 폴더(제안)
| 폴더(`06_analysis/02_control/j_p3_cause/` 아래) | SUMS | 메모 |
|---|---|---|
| `j9_runs/56849248/judge_7ea78232_s5/` | 없음(커밋 직전 작성) | `ho_k_selection.json` 1개 |
| `j9_runs/56849248/ho_v0_a1/`·`ho_aa2_a1/`·`ho_aa3_a1/`, `ho_*.done`, `ho_v0_prerun.SHA256SUMS` | 목록 `5c41c183…`(27항목) | 하위 폴더 `logs\`와 빈 `judge\`(파일 0개, git에 들어가지 않음)가 있다. 10^8 B 초과 없음(최대 4.56 MB), ignore 대상 없음(판정 전 감사 기록 11) |
| `j9_runs/56849248/_identity_checks/` | 다시 씀(커밋 직전) | `ho_*_a1.md` 3개가 더해져 지금 `sums_unlisted` 3 |
| `ed8_design/stage5_prejudge/` | `ad466c57…`(있음) | 판정 명령 |
| `ed8_design/stage5_judgement/` | 없음(md 확정 뒤) | 이 판정서, `run_console.log` |
| `ed8_design/audit_stage5_prerun/` | 없음(감사 폴더, 마지막에 `--top-only`) | 실행 전·판정 전 감사, 결함 독립 확인(`bec52a14…`), 3개 |
| `ed8_design/audit_ed8_closing/` | 없음(감사 폴더, 마지막에 `--top-only`) | 이 판정서와 판 8 종료 판정서의 커밋 전 감사(`6638a4db…`). 감사 원문 저장 위치는 이 폴더다(M-3) |
| (진단 출력) `ed8_design/stage5_aa_diag/` | 이 커밋에 넣지 않음 | 진단 실행(결정 5단계-3)은 커밋 뒤에 이 형제 폴더에 쓴다. `stage5_aa_cause/` 안(`diag\`)에 쓰지 않는다. 그 폴더 `--recursive` SUMS가 낡기 때문이다(M-1) |
| `ed8_design/stage5_aa_cause/` | 없음(커밋 직전 작성, 하위 폴더 `scripts\`가 있어 `--recursive`) | 원인 분석 `aa_cause_analysis.md`(`32c2a685…`)와 근거 파일·스크립트(23항목). 진단 실행 출력은 이 폴더 밖 `ed8_design/stage5_aa_diag/`에 둔다(아래 행, M-1) |
| `ed8_design/stage5_decisions/` | 없음(커밋 직전 작성) | 결정문 `decision_stage5_20261128.md`(`7d236aa2…`) |
| `ed8_design/ed8_closing/` | 없음(md 확정 뒤) | 판 8 종료 판정서 |
| 러너 사본 `~/.claude/runners/outrigger-ed8/stage5/` | – | 4단계와 같은 꼴로 사본을 넣을지 메인이 정한다(넣으면 `--recursive`) |

## 9. 확인 필요·위임 필요·메인 세션 권고

### 앞 초안 확인 필요의 처리(결정 5단계, `7d236aa2…`)
- **A. 5단계 결과의 규칙 분류**: 결정됨(결정 5단계-1). (가) stop 유지, 사유 정정(0절·2.4), 10:345 비적용(1.2), 판정 커밋 유지, 결함은 판 9 과제(2.3).
- **B. 판 8 종합 표기**: 결정됨(결정 5단계-2). 판 8 종료 판정서에 "판 8 5단계 멈춤(G′ V0 A/A N층 바닥 초과), 결과 판정 미실시, 구현 확인 P8-5 판정 불가" 꼴로 적는다. P8-5 공개 문안과 (라-2) 기록도 그 문서 공개 칸에 넣는다(6.1).
- **C. 경로 2 [정의] 문장**: 닫힘(결정 5단계-2로 판 8 경로 2가 없음). (원천, 슬롯) [정의]는 판 9 규칙 몫으로 넘긴다(7절).

### 위임 필요
- **python-expert**(판 9 구현 과제, 결정 5단계-1): 2.3 "결함이 닿는 곳"의 5단계·8단계·기록 문구 위치를 (원천, 슬롯) 결합 키로 바꾼다. 시험: 실제 키 파일 기록 항목 수 = 339, 이름이 같은 합성 슬롯 둘(원천만 다름, 층·실패 다름)이 각자 자기 짝으로 세어짐, 8단계 `_unit_layer`·별칭. 판 8 판정 커밋은 바꾸지 않는다.
- **python-expert: `tools/verif` 후보**(verif 결함 확인 위임 필요): `record_check identity --list-key`, `gate_scan` 규칙 `dict_keyed_by_record_field`. 판 9 실행 전 감사 전에 둔다.
- **python-expert(진단 실행 trace 옵션)**: 결정 5단계-3. 판 8 종료 판정서 커밋 뒤, D1 내부 기록을 켜고 job 4개를 다시 돌린다. 대상 job과 기록 항목은 `aa_cause_analysis.md` "메인 세션 권고"에 있다. 출력 경로는 형제 폴더 `ed8_design/stage5_aa_diag/`로 고정한다(8절, 커밋 전 감사 M-1). 원인 분석 문서의 권장 경로 `diag/`(`stage5_aa_cause/` 안)는 쓰지 않는다.
- **verif-protocol-auditor**: 이 판정서 개정 1의 판정 후 감사. 2.4의 성격 공개와 0절 사유 문면이 결정 5단계-1 문안과 맞는지 본다.

### 메인 세션 권고
- 판정은 다시 돌리지 않는다(결정 5단계-1).
- 7절 블라인드 목록은 판 9 경로 2 시작 전에 넣는다.
- 판 8 종료 판정서를 이 판정서와 함께 커밋한 뒤에 진단 실행을 띄운다(결정 5단계-3). 출력은 `ed8_design/stage5_aa_diag/`(M-1).
- SUMS 순서(커밋 전 감사 메인 세션 권고 2): `judge_7ea78232_s5 --top-only` → `_identity_checks --top-only --force` → `stage5_judgement --top-only` → `stage5_aa_cause --recursive` → `stage5_decisions --top-only` → `ed8_closing --top-only` → 마지막에 감사 폴더 `audit_stage5_prerun`·`audit_ed8_closing` `--top-only`. `ho_*_a1`은 `ho_v0_prerun.SHA256SUMS`로 고정되므로 새로 쓰지 않는다.

## 10. 이 초안 작성의 공개(읽은 것·실행한 것)
- **Read**
  - `ho_k_selection.json` 1-1717·2419-2508행(슬롯별 층·A/A 짝 포함)
  - 규칙 v8 276-327·379-400행
  - 판정 전 감사 1-274행, 실행 전 감사 175-199행
  - 결정문 1742fa05 전체, 공개 문안 42614b21 전체
  - `run_console.log`, `grid_blobs.txt`, 판정 ps1 100-141행
  - `jp3_ed8_rules.py`(ed8-judge4) 360-513행, `jp3_ed8_judge.py`(ed8-judge4) 1100-1239행
- **Grep**
  - `ho_k_selection.json` 최상위 키
  - 판정 전 감사(절 제목), 실행 전 감사(기록 15)
  - `jp3_ed8_rules.py`(`A/A failures|cp95|reasons`), `jp3_ed8_judge.py`(`"slot"`)
- **Glob**: `stage5_prejudge`
- **PowerShell**: `Get-FileHash` 10개, `ho_v0_prerun.SHA256SUMS` 줄 수, `judge_7ea78232_s5`·`audit_stage5_prerun` 파일 이름, 출력 mtime, ed8-judge4 `rev-parse`·`status --porcelain --ignored`(0줄)
- **스크립트**(scratchpad `control-expert-s5judge\`, 모두 지움, `Test-Path` False)
  - `recount_s5.py`(출력만, 층·A/A 재집계)
  - `slot_dup.py`(키 파일 이름 수·원천별 수, 값 없음)
  - `collision_effect.py`(겹치는 이름 기준으로 출력 수를 나눔)
  - `order_cp.py`(키 파일 줄 순서, CP95 표)
  - 실행: python-dev `-X utf8 -I -B` 또는 dynamics-dev `conda run … python -I -B`
- **열지 않은 것**: 5단계 jsonl 줄, 스텝 `.log`·`.err`, P8-2 경로 2 자료, 다른 세션 기록. 판정 모듈은 import하지 않았고 판정 도구를 돌리지 않았다.
- **쓰기**: 프로젝트 파일 없음(이 판정서는 메인이 저장). 에이전트 메모리 `per-line-gate-join-key.md`에 한 단락(기록 사전 키 수 대 센 단위 수 점검)을 더했고 `MEMORY.md` 색인 줄을 늘렸다.
- Bash 파이프·heredoc을 쓰지 않았다. 프로세스를 종료하지 않았다.

### 10.1 개정 1 작성의 공개(2026-11-28)
- **Read**: 결정문 `decision_stage5_20261128.md` 전체, verif 결함 독립 확인 전체, 원인 분석 `aa_cause_analysis.md` 전체, 이 판정서 전체
- **PowerShell**: `Get-FileHash`(위 세 문서, 4단계 판정서), `git log -1`(결정문 커밋 여부, `2715230e`·`acba3304` 시각)
- **쓰기**: 이 판정서만 Edit로 고쳤다. 근거 폴더와 scratchpad에는 쓰지 않았다
- 원인 분석 근거 파일(jsonl 전수 요약 csv 등), 5단계 jsonl, 스텝 로그, P8-2 경로 2 자료는 열지 않았다. Bash 파이프·heredoc을 쓰지 않았다

### 10.2 개정 2 작성의 공개(2026-11-28)
- **Read**: 커밋 전 감사 `verif_ed8_closing_precommit.md` 전체
- **Grep**: 이 판정서와 판 8 종료 판정서(단일 파일, 고칠 행 찾기)
- **PowerShell**: `Get-FileHash`(커밋 전 감사, 두 판정서)
- **쓰기**: 이 판정서와 판 8 종료 판정서만 Edit로 고쳤다. 원인 분석·결정문·공개 문안 등 sha로 인용된 문서와 근거 폴더에는 쓰지 않았다
- 원인 분석 scripts·`provenance.json`은 직접 열지 않았다. M-6 모듈 목록은 감사 원문에서 옮겼다

사용한 스킬: 없음
