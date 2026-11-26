# S8-R 개정 3 hand-back 메모 (control-expert, 2026-11-26; 봉인본 밖)

## 반영 대조
| 감사 항목 | 반영 위치 |
|---|---|
| verif B-1 / stats B-1·B-2 | 6.3 E 후보 사건(입력 사건 판별, `fast` 안 읽음, 결측은 `reapproach_starts`만), F8-20, 4절 0c·0c′, 13절 9(stats 오기 정정), Y8-6 |
| verif M-1 | 5.1 C-J 대응 VBM → VBN·LSM<n> → LSN<n>, j9_main.jsonl 전체 sha |
| verif M-2 / stats R-6 | P8-16(기준 원천 `raw/runs.jsonl` 89efe66f·SUMS 1f4de072·계획 파일 99e50653·검토 스크립트 0dade869, 키별 기준 = 실행 출처만, 완결성 27/27·27/27, r79 조건, 두 시점), 머리말 근거 표 |
| verif M-3 / stats R-2 | 7.3 5단계 처리 순서, 7.4 $n_{AA}$ = 0 처리 |
| verif M-4 | 5.1 census 키 sha → C8 상수·S8-C, P8-10 재생성 시험, 11.3 |
| verif M-5 | 5.1 D 키 커밋 경로, 브랜치·잠금 유지 |
| verif M-6 | 근거 표에 `python_0c_keys/`, npz 한 줄, 근거 표 SUMS는 봉인 직전 기입(메인) |
| verif M-7 | 상태 줄 "봉인 대상(개정 3)", 메모 블록 제거(이 파일로 분리), `<P814_VBK_KEYS>` 자리 이름 제거, 설명용 자리 표시(`<C8 앞 8자>`·`<단계>`·`<S8C_*>`)를 문장으로 바꿈 |
| verif M-8 | O8-9~O8-12 |
| verif M-9 | P8-5(15줄)·P8-8(5줄)·P8-15(20줄) 최소 줄 수와 0건 = 판정 불가, P8-5 고르는 기준을 "스케일 값 같은 줄"로 바꿈 |
| verif R-1 | 13절 18 |
| verif R-2 | 5.1 main.jsonl 전체 sha |
| verif R-3 | 5.2 C-D 칸 문장, 6.2 (다) |
| verif R-4 | 7.5 동결 값 재계산과 판정서 기록 |
| stats R-1 | 7.3 2(E 미달 합침, 사용자 결정) |
| stats R-3 | 7.4 3회 실패 = A/A 기회 없음 |
| stats R-4 | 5.2·5.3·13절 13 선택 사용 키 전체, T8 기록 칸 |
| stats R-5 | 8절 "든다(판 8 12b 계획 키로 확인)", 4사례 제외 기록 |
| stats R-7 | 8절 충돌 스캔에 4단계 P8-16 출력 |
| stats R-8 | F8-20, 근거 표 sha |
| stats R-9 | 7.4 공개에 A/A 멈춤 20~27 % |
| 사용자 결정 1~4 | 15절 Q8-17~Q8-20 |

## 요청 밖 추가(공개)
- P8-5의 고르는 기준을 "스케일 mid가 옮겨지지 않은 라운드만 있는 줄"에서 "모든 라운드의 `twist_stiffness_scale`이 두 팔에서 같은 줄"로 바꿨다. 재생에서 mid 이동은 다리 단위로 흔해(방향 A 21/67) 앞 기준으로는 고른 줄이 최소 수에 못 미칠 위험이 컸다. PSW는 스케일(과 경고 사건)로만 명령에 닿으므로 새 기준이 명령 동일성의 충분 조건이다. 경고 사건은 명령에 닿지 않는다.
- E층 $n_{AA,E}$ = 0이고 $n_E$ ≥ 16일 때 E를 N에 합치는 규칙(7.4)을 넣었다. 사용자 결정 2에 없는 경우라 **확인 필요**(Q8-21)로 올렸다.

## 확인 필요
- Q8-21: 위 E층 $n_{AA,E}$ = 0 처리(제안: N에 합침 / 대안: 멈추고 묻기).

## 이번 단계에서 연 자료
- `python_0c_keys/report.md`, `audit_preseal/stats_final_review.md`, `audit_preseal/verif_preseal_s8r.md`.
- PowerShell `Get-FileHash`로 해시를 잰 파일: `control_level_deadlock/probe_8a2a52ce/raw/plans/*.json`(4)·`raw/runs.jsonl`·`SHA256SUMS`·`p814_rerun.py`·`p814_selection.json`, `control_early_handover/probe_8a2a52ce/raw/runs.jsonl`·`SHA256SUMS`·`h3p/raw/runs.jsonl`·`h3p/SHA256SUMS`, `python_0c_keys/SHA256SUMS`·`layer_keys_0c.json`. 파일 경로를 하나씩 지정했다.
- 코드·`j9_runs`·블라인드 경로는 열지 않았다.

## 위임 필요
- python-expert: 명세 16절(특히 Y8-6 층 판별·0c′·5단계 순서, Y8-10, P8-16 구현 커밋 사전 실행 54줄과 완결성 검사, P8-5·P8-8·P8-15 팔과 최소 줄 수).
- verif-protocol-auditor: 개정 3 짧은 재감사(`placeholder_scan --skip-inline-code`, `ref_check --no-git --exclude …`, `.sha256` 뒤 `seal_check`).
- 메인: 근거 표 폴더 SUMS sha 기입(봉인 직전), `python_p1_p3` SUMS, npz LOCAL_ONLY 처리, `git status --ignored`, `audit_preseal/` SUMS는 마지막.

사용한 스킬: 없음
