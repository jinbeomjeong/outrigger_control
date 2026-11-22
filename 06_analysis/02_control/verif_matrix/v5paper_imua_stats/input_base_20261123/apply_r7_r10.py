"""Apply the re-audit 5 fixes (B-6, W-n, record 1) to rev26 fix 6 -> 7 and the A-type draft fix 9 -> 10.

Usage: python -I -B -X utf8 apply_r7_r10.py <rev26.md> <imua_draft.md> <out_rev26> <out_imua>
Uses the Doc helper of apply_r6_r9.py (same folder). Every replacement must hit its expected count, else exit and
nothing is written. Output LF, no BOM.
"""
import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location("apply_r6_r9", Path(__file__).with_name("apply_r6_r9.py"))
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)
Doc, report = _base.Doc, _base.report

R5_LIST = "9e1831f5af2621510f9b6a7a8bf9f9c39c85f7633d8ef69bdc87895902e19283"
R5_SCRIPT = "bee9eee74a002d84710cde59fa20a1f2517c0b8cfa56173314d1d4eec36465f5"


def rev26(d):
    d.sub("봉인 전 수정 6)", "봉인 전 수정 7)", tag="1")
    d.sub("  - 수정 6(이 판):", "  - 수정 6:", tag="2a")
    d.insert_after(
        "  - 수정 6: 다섯 번째 재감사",
        "  - 수정 7(이 판): 여섯 번째 재감사 `v5paper_imua_stats/audit_rev26_preseal_reaudit5_20261123.md` B-6(NT 정규화를 2절 W "
        "자료 위치로 넓힘, 부록 r5), W-n(줄바꿈이 비교 잎에 닿는 03_src 파일은 `v5_options.py`뿐), 기록 1(Chrono 매니페스트 기본값은 W)",
        tag="2b")
    d.sub("네 번째·다섯 번째 재감사(B-5 반영 확인 필요)", "네 번째·다섯 번째·여섯 번째 재감사(B-6 반영 확인 필요)", tag="3")
    d.sub("excl_fields_r4", "excl_fields_r5", count=5, tag="4a")
    d.sub("rev26_excluded_fields_r4.json", "rev26_excluded_fields_r5.json", count=3, tag="4b")
    # record 1: the Chrono rows manifest default is W only
    d.sub("Chrono 하위 명령의 `resolve_result`·`resolve_runner_row`·`runner_root`·`cmd_chrono` 매니페스트 기본값"
          "(5단계에서 돌지 않으나 같은 규칙)",
          "Chrono 하위 명령의 `resolve_result`·`resolve_runner_row`·`runner_root`(5단계에서 돌지 않으나 같은 규칙)", tag="5a")
    d.sub("02_params(`yaml_vmax`) |",
          "02_params(`yaml_vmax`), Chrono 행 매니페스트(`cmd_chrono`의 매니페스트 기본값 = 아래 W 목록의 "
          "`chrono_rows_manifest.json`, 5단계에서 돌지 않음) |", tag="5b")
    # W-n and B-6
    d.replace_line(
        "  - W 가운데 작업 트리 줄바꿈이 원 출력 비교 잎에 닿는 파일은",
        "  - W 가운데 작업 트리 줄바꿈이 원 출력 비교 잎에 닿는 03_src 파일은 `03_src/outrigger_sim/hydraulics/v5_options.py`"
        "(`v5_options.sha256`)뿐이다(작성자 점검 2026-11-23: 비교 64자리 잎 2,402개 가운데 03_src·02_params 파일 sha와 같은 것은 "
        "7개, 모두 CRLF 꼴. 그 가운데 경로 1 `h6_L1_reference.json :: meta.c2_py_sha256`은 저장 입력 `h8_noise_VB.json`의 `meta`를 "
        "옮긴 값이라 checkout과 무관하다, 여섯 번째 재감사 W-n). 그래서 worktree는 `core.autocrlf=true`여야 한다.\n"
        "  - W 자료를 가리키는 경로 문자열이 출력에 남는 곳은 worktree 절대 경로가 된다(원 출력의 예: 경로 1 `h2_select.json :: rules`"
        " = `d1_select`의 규칙 파일 기본값, 여섯 번째 재감사 B-6). 부록 A는 W 자료 위치를 도구 위치와 같이 NT로 정규화한다(r5). "
        "부록 A의 W 자료 위치 목록은 위 W 목록과 같다(규칙 파일: `verif_matrix/` 바로 아래 `*.md`·`*.sha256`과 "
        "`v5/v5_criteria*.md`).",
        tag="6")
    d.sub("worktree의 `03_src/outrigger_sim/control/c2.py`·`03_src/outrigger_sim/hydraulics/v5_options.py` raw sha256이",
          "worktree의 `03_src/outrigger_sim/hydraulics/v5_options.py` raw sha256이", tag="7")
    d.sub("worktree의 `c2.py`·`v5_options.py` raw sha256", "worktree의 `v5_options.py` raw sha256", tag="8")
    d.sub("도구 위치(루트 뒤가 `03_src`·`04_scripts`·`05_tests`·`verif_matrix/scripts`·`v5_resume_4368/path2*`·"
          "`paper_runs/scripts`)는 NT, 그 밖은 NM",
          "도구 위치(루트 뒤가 `03_src`·`04_scripts`·`05_tests`·`verif_matrix/scripts`·`v5_resume_4368/path2*`·"
          "`paper_runs/scripts`)와 2절 W 자료 위치(`verif_matrix/` 바로 아래 `*.md`·`*.sha256`, `v5/v5_criteria*.md`, "
          "`02_params/`, `00_dynamics/{slope_crawler_settle, pad_bekker_p0_soilsets}.json`, `s8/rev76/`, "
          "`s8/s8_rev52_cs836_scope.json`, `s9/rev80/`, `v5_resume_4368/chrono_rows_manifest.json`)는 NT, 그 밖은 NM",
          tag="9")
    d.sub("정규화 NM 88 / NT 8)", "정규화 NM 87 / NT 9)", tag="10")
    d.sub("(생성 시 목록 `fafca4235c267620bde8738bb0b7277559eb376d868554f8011355a59b3ddeec`, "
          "스크립트 `1fb6f701a483f0b7ebcf9ffb78530649edfc46c9151f9ff36f99fdc7037c4a41`. r3 목록과는 `rules` 이름만 다르다)",
          f"(생성 시 목록 `{R5_LIST}`, 스크립트 `{R5_SCRIPT}`. r4 목록과는 `rules` 이름과 "
          "`harness_path1/h2_select.json :: rules`의 범주(NM → NT) 하나만 다르다)", tag="11")
    d.insert_after("  - `excl_fields_r3.py`",
                   "  - `excl_fields_r4.py`(`1fb6f701…`)·`rev26_excluded_fields_r4.json`(`fafca423…`)", tag="12")


def imua(d):
    d.sub("봉인 전, 수정 9)", "봉인 전, 수정 10)", tag="A1")
    d.insert_after(
        "  - 수정 9: verif rev26 다섯 번째 재감사",
        "  - 수정 10: verif rev26 여섯 번째 재감사 W-n(J-2 제외 1a 삭제: `c2_py_sha256`은 저장 입력 메타), rev26 부록 r5(B-6)",
        tag="A2")
    d.sub("excl_fields_r4.py", "excl_fields_r5.py", count=3, tag="A3a")
    d.sub("rev26_excluded_fields_r4.json", "rev26_excluded_fields_r5.json", count=1, tag="A3b")
    d.sub("r4 규칙이 인자 목록에서 이미 뺀다.", "r5 규칙이 인자 목록에서 이미 뺀다.", tag="A3c")
    d.replace_line(
        "     - 1a. 경로 1 `h6_L1_reference.json :: meta.c2_py_sha256`",
        "     - 비교 잎 가운데 checkout의 03_src·02_params 파일 sha를 담은 것은 1뿐이다. 경로 1 "
        "`h6_L1_reference.json :: meta.c2_py_sha256`은 저장 입력 `h8_noise_VB.json`의 `meta`를 옮긴 값이라 TA와 무관하므로 빼지 않는다"
        "(rev26 여섯 번째 재감사 W-n, 작성자 점검 `src_sha_leaves.py`)",
        tag="A4")
    d.sub("줄바꿈 잎 점검(TA worktree `c2.py`·`v5_options.py` raw sha = TA blob의 CRLF 꼴 sha. 3.1 목록에 든 파일은 "
          "J-2 제외 1·1a로 빠지므로 기록만 한다)",
          "줄바꿈 잎 점검(TA worktree `v5_options.py` raw sha = TA blob의 CRLF 꼴 sha. TA는 이 파일을 바꾸므로 J-2 제외 1로 빠지고 "
          "기록만 한다)", tag="A5")


def main():
    src26, srca, out26, outa = sys.argv[1:5]
    d26, da = Doc(src26), Doc(srca)
    rev26(d26)
    imua(da)
    report("rev26.r7", d26, out26)
    report("imua.r10", da, outa)


if __name__ == "__main__":
    main()
