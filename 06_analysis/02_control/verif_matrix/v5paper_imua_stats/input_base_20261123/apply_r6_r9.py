"""Apply the rev26 (fix 5 -> 6) and A-type (fix 8 -> 9) replacement lists to copies of the project files.

Usage: python -I -B -X utf8 apply_r6_r9.py <rev26.md> <imua_draft.md> <out_rev26> <out_imua>
Every replacement must hit its expected count, else exit 2 and nothing is written. Output LF, no BOM.
Prints per file: sha256, lines before / after, changed-line counts from difflib.
"""
import difflib
import hashlib
import sys
from pathlib import Path


class Doc:
    def __init__(self, path):
        raw = Path(path).read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]
        self.orig = raw.decode("utf-8").replace("\r\n", "\n")
        self.text = self.orig
        self.log = []

    def sub(self, old, new, count=1, tag=""):
        n = self.text.count(old)
        if n != count:
            raise SystemExit(f"[{tag}] expected {count} hit(s), found {n}: {old[:60]!r}")
        self.text = self.text.replace(old, new)
        self.log.append((tag, n))

    def _line_index(self, prefix, tag):
        lines = self.text.split("\n")
        idx = [i for i, l in enumerate(lines) if l.startswith(prefix)]
        if len(idx) != 1:
            raise SystemExit(f"[{tag}] prefix hit {len(idx)}: {prefix[:60]!r}")
        return lines, idx[0]

    def insert_after(self, prefix, block, tag=""):
        lines, i = self._line_index(prefix, tag)
        lines[i + 1:i + 1] = block.rstrip("\n").split("\n")
        self.text = "\n".join(lines)
        self.log.append((tag, 1))

    def replace_line(self, prefix, block, tag=""):
        lines, i = self._line_index(prefix, tag)
        lines[i:i + 1] = block.rstrip("\n").split("\n")
        self.text = "\n".join(lines)
        self.log.append((tag, 1))

    def replace_range(self, first_prefix, last_prefix, block, tag=""):
        lines, i = self._line_index(first_prefix, tag)
        _, j = self._line_index(last_prefix, tag)
        if j < i:
            raise SystemExit(f"[{tag}] range order")
        lines[i:j + 1] = block.rstrip("\n").split("\n")
        self.text = "\n".join(lines)
        self.log.append((tag, 1))


def rev26(d):
    d.sub("봉인 전 수정 5)", "봉인 전 수정 6)", tag="1")
    d.replace_line(
        "  - 수정 5(이 판): 네 번째 재감사",
        "  - 수정 5: 네 번째 재감사 `v5paper_imua_stats/audit_rev26_preseal_reaudit3_20261122.md` B-4(`.gitattributes` 허용), "
        "W-i(worktree 깨끗함 기록), W-j(`--root .` 확정)\n"
        "  - 수정 6(이 판): 다섯 번째 재감사 `v5paper_imua_stats/audit_rev26_preseal_reaudit4_20261122.md` B-5(사용자 결정 (가): "
        "경로 2 입력 기준 인자 `--data-root`, 경로 1 실행본 입력 인자, 입력 기준 site 열거), W-l(줄바꿈 점검 대상), "
        "W-m(h11 문장), 기록 1(들여쓰기)",
        tag="2")
    d.sub("네 번째 재감사(B-4 반영 확인 필요)", "네 번째·다섯 번째 재감사(B-5 반영 확인 필요)", tag="3")
    d.sub("B-1 (가), N-1 (나)", "B-1 (가), N-1 (나), B-5 (가)", tag="4")
    d.sub("excl_fields_r3", "excl_fields_r4", count=4, tag="5a")
    d.sub("rev26_excluded_fields_r3.json", "rev26_excluded_fields_r4.json", count=2, tag="5b")
    d.sub("    - **`.gitattributes`**:", "  - **`.gitattributes`**:", tag="6")
    d.insert_after("- **checkout(사용자 결정 N-1 (나))**", BLOCK7, tag="7")
    d.replace_line("    5. `--root` 인자는 더하지 않는다(봉인 전 확정).", BLOCK8, tag="8")
    d.sub("head-check 호출(기본 ROOT = `$Judge`의 저장소 = worktree이므로 `--root`를 주지 않음)",
          "head-check·import-check·appendix-a 호출(기본 ROOT = `$Judge`의 저장소 = worktree이므로 `--root`를 주지 않음)",
          tag="9")
    d.insert_after("    6. 출력 폴더(`$Out`, 430행)", LINE10, tag="10")
    d.sub("    - 그대로 두는 것: `$Repo`(23행, 메인),", "    - 그대로 두는 것: `$Repo`(23행, 메인. 7번 `--data-root`의 값),", tag="11")
    d.sub("실행 환경(dynamics-dev·python-dev의 `conda list --export` sha와 python 판)",
          "실행 환경(dynamics-dev·python-dev의 `conda list --export` sha와 python 판), 2절 '입력 기준' 표와 두 경로 구현 기록의 "
          "대조 결과, worktree의 `c2.py`·`v5_options.py` raw sha256", tag="12")
    d.replace_line("- 각 작성자는 자기 경로 하위 명령마다 입력 경로를", LINE13, tag="13")
    d.sub("worktree에서 `git check-attr text -- <rev26 규칙 파일·부록>`이 `unset`(`-text`)이고 "
          "`git ls-files --eol -- <같은 파일>`이 `w/lf`인지 본다. 다르면 멈춘다.", LINE14, tag="14")
    d.replace_range("- **입력 경로 해석(확인만)**", "  - 두 실행본이 읽는 추적 입력 경로 전체에 대해", BLOCK15, tag="15")
    d.sub("**합성 고정물로만, 2절 5단계 실행본과 같은 꼴(도구 = worktree, cwd·입력 = 메인 쪽 합성 폴더)**로",
          "**합성 고정물로만, 2절 5단계 실행본과 같은 꼴(도구 = worktree, cwd·입력·경로 2 `--data-root`·경로 1 "
          "`--las-k1-dir`·`--data-root` = 메인 쪽 합성 폴더)**로", tag="16")
    d.insert_after("  - 세 출력 사이에서 달라지는 필드가", LINE17, tag="17")
    d.sub("`--root`·`--allowed-src-changes`와 다음 원소", "`--root`·`--data-root`·`--allowed-src-changes`와 다음 원소", tag="18")
    d.sub("(생성 시 목록 `3a5d637c9efc170b07a6a92b1abefa855b9729aece5fec45563a0228d55aa05e`, "
          "스크립트 `bfe6354e91d800f5c4479affda9582a110a0cccee6b20a3ded16ca057e39a142`)",
          "(생성 시 목록 `fafca4235c267620bde8738bb0b7277559eb376d868554f8011355a59b3ddeec`, "
          "스크립트 `1fb6f701a483f0b7ebcf9ffb78530649edfc46c9151f9ff36f99fdc7037c4a41`. r3 목록과는 `rules` 이름만 다르다)",
          tag="19")
    d.insert_after("  - `excl_fields_r2.py`",
                   "  - `excl_fields_r3.py`(`bfe6354e…`)·`rev26_excluded_fields_r3.json`(`3a5d637c…`)", tag="20")


BLOCK7 = """- **입력 기준(B-5, 사용자 결정 (가))**: 436.8 핵심 입력(`resume_k1`, `v5_rerun/las_k1`, `07_results`, v5 저장 결과 대부분)은 git 밖이라 worktree에 없다. 결과·데이터 입력은 모두 메인 checkout에서 읽고, 출력에 적는 입력 상대 경로도 메인 기준으로 만든다. 도구 저장소(worktree)에서는 아래 W만 읽는다.
  - 경로 2(T26 코드 변경): `p2_4368.py`·`p2_x16.py`·`p2_u3.py`·`p2v5c_common.py`의 최상위 인자 파서에 `--data-root <폴더>`(기본값 = `repo`)를 더한다. `repo`가 하던 일 가운데 D는 `--data-root`로 옮기고 W는 `repo`에 둔다. 인자가 없을 때의 동작은 `932f1fb`와 같아야 한다(단위 시험).

    | 구분 | 대상(932f1fb 코드 확인, 함수 단위) |
    |---|---|
    | D → `--data-root` | 상대 입력 경로를 푸는 곳과 출력에 적는 상대 경로의 기준. `p2_4368.py`: `rel_posix`와 그 모든 호출처, `_rel_entry_path`, `r4_input_check`, `key_source_index`, `cmd_harness`(매니페스트 `path`·`stored`·`key_source`·`key_source_override`), `cmd_anchors`(`--v5-root` 기본값), `jp_result_json`, Chrono 하위 명령의 `resolve_result`·`resolve_runner_row`·`runner_root`·`cmd_chrono` 매니페스트 기본값(5단계에서 돌지 않으나 같은 규칙). `p2_x16.py`: `cmd_g3`(`--las-k1-dir` 기본값과 `rel_posix`), `cmd_c16`(`rel_posix`). `p2_u3.py`: `study_keys`, `settle_v2_recount`, `rd7_row`. `p2v5c_*.py`: `rel_file`의 모든 호출처(`cmd_grid`·`cmd_noise`·`cmd_stage1`), `dg3_keys` 기본값 |
    | W → `repo` | 봉인 확인(`check_seals`·`check_chrono_seals`·`check_rev3`·`_check_one`, 규칙 sha 표), HEAD·git 기록(`git_head`·`head_check`·`git_commits_since`·`git_diff_stat`), 03_src(`load_is_extend_start`), 도구 스크립트(`run_judge`의 `r79_sensor_judge.py`와 그 sha, `cmd_openloop`), 02_params(`yaml_vmax`) |

    - `p2_d1.py`·`p2_v5j.py`·`p2_t3k.py`는 바꾸지 않는다(D 없음). `p2_x16.py d1`은 `--data-root`를 넘기지 않는다.
  - 경로 1(코드 변경 없음, 실행본 인자로 맞춤): 결과 입력을 도구 저장소 기준으로 푸는 기본값은 `h11 --las-k1-dir`와 `resume_k1_family.py --data-root` 둘이다. 실행본이 둘 다 cwd 상대 값으로 준다(5단계 경로 1의 5·6번). 그 밖의 결과 입력은 실행본 인자(cwd 상대) 또는 `--root .`·`--grid-root .`로 메인에서 읽는다.
  - W(두 경로 공통, 모두 T26 추적 파일): 규칙 파일(`verif_matrix/*.md`·`.sha256`, 원판 부록 A 34개, 모두 `-text`), 03_src·04_scripts·`paper_runs/scripts`·판정 도구 폴더의 코드(경로 1 `import-check`의 모듈 색인 포함), 판정·하네스 모듈이 자기 위치로 읽는 추적 자료(`02_params/{rexome33.yaml, scm_soil_sets.json, pad_variants.json}`, `06_analysis/00_dynamics/{slope_crawler_settle.json, pad_bekker_p0_soilsets.json}`, `06_analysis/02_control/s8/rev76/*`, `s8/s8_rev52_cs836_scope.json`, `s9/rev80/*`, `verif_matrix/v5_resume_4368/chrono_rows_manifest.json`), HEAD·git 기록
  - W 가운데 작업 트리 줄바꿈이 원 출력 비교 잎에 닿는 파일은 `03_src/outrigger_sim/control/c2.py`(경로 1 `h6_L1_reference.json :: meta.c2_py_sha256`)와 `03_src/outrigger_sim/hydraulics/v5_options.py`(`v5_options.sha256`)뿐이다(작성자 점검 2026-11-23: 비교 64자리 잎 2,402개 가운데 03_src·02_params 파일 sha는 이 7개, 모두 CRLF 꼴). 그래서 worktree는 `core.autocrlf=true`여야 한다."""

BLOCK8 = """    5. h11 호출(116행)에 `'--las-k1-dir', '06_analysis/02_control/v5_rerun/las_k1'`을 `--h11-dir` 쌍 바로 뒤에 더한다(cwd 상대, `/`)
    6. family_table 호출(109행)에 `'--data-root', '.'`을 출력 파일 인자 바로 뒤에 더한다
    7. `--root` 인자는 더하지 않는다. 결과 입력에 `--root`·`--grid-root`를 받는 하위 명령(r4-inputs·jp-reuse·r4-lists·grid-h10·family-f-trigger·family-f)은 M4 실행본이 이미 `.`을 준다. 기본 ROOT(= worktree)로 도는 head-check·import-check·appendix-a는 2절 '입력 기준'의 W만 읽는다"""

LINE10 = ("    7. 입력을 읽는 9개 호출에 `'--data-root', $Repo`를 `--out <파일>` 쌍 바로 뒤에 더한다: harness·anchors·jp"
          "(`p2_4368.py`), g3·c16(`p2_x16.py`), u3(`p2_u3.py`), v5c_stage1·v5c_grid·v5c_noise(`p2v5c_*.py`). "
          "seal·d1·items·v5j_u9·v5c_merge에는 주지 않는다(D 없음)")

LINE13 = ("- 경로 2 작성자는 2절 '입력 기준' 표대로 `--data-root`를 넣는다. 경로 1 작성자는 입력 해석을 바꾸지 않는다(입력 기준은 "
          "실행본 인자로 맞춘다, 2절 경로 1의 5·6번). 두 작성자는 자기 경로 하위 명령마다 입력 경로를 무엇 기준(cwd·실행본 인자·"
          "`--data-root`·도구 저장소)으로 푸는지, 출력에 적는 상대 경로를 무엇 기준으로 만드는지 구현 기록에 표로 적는다. "
          "도구 저장소 기준인 곳이 2절 W와 같은지도 적는다. 각 작성자는 자기 경로 행만 쓴다.")

LINE14 = ("worktree에서 대상 4개 파일(`06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev26.md`, "
          "`…/v5_resume_4368_rules_rev26.sha256`, `…/v5_resume_4368/rev26_fixed/excl_fields_r4.py`, "
          "`…/v5_resume_4368/rev26_fixed/rev26_excluded_fields_r4.json`)의 `git check-attr text`가 `unset`(`-text`)이고 "
          "`git ls-files --eol`이 `w/lf`인지 본다. `rev26_fixed/**`의 폐기본(부록 B 폐기본 목록)은 `check-attr`가 `unset`인지만 "
          "보고 줄바꿈 꼴은 보지 않는다. 다르면 멈춘다.")

BLOCK15 = """- **입력 기준(B-5, 확인만)**: T26 코드와 3절 구현 기록으로 2절 '입력 기준'을 확인한다.
  - 경로 2: D의 site가 모두 `--data-root` 기준이고, `repo` 기준은 W뿐이다. 실행본의 `--data-root` 9개 호출이 2절 경로 2의 7번과 같다.
  - 경로 1: 결과 입력을 도구 저장소 기준으로 푸는 기본값은 `h11 --las-k1-dir`·`resume_k1_family.py --data-root` 둘뿐이고, 실행본이 둘 다 준다. 그 밖의 경로 1 하위 명령(`$Co` 스크립트 포함)에 결과 입력을 `ROOT / …`로 푸는 기본값이 남아 있으면 실행본 인자로 덮였는지 본다.
  - **입력을 도구 저장소 기준으로 푸는 곳 = 2절 W에 열거한 것뿐**이다. 판정 import 닫힘의 모듈이 자기 위치로 읽는 자료도 포함하고, 모두 T26 추적 파일이다.
  - 다르면 5단계로 가지 않고 멈춰 묻는다(규칙 수정은 새 사용자 결정).
- 경로 1 실행본의 입력 인자는 모두 cwd 상대 경로이고 `/` 구분자다(절대 경로·`\\`·`./` 시작 없음). 2절 경로 1의 5·6번 값도 같다. 도구의 `repo_relative` 대체 동작이 원 출력과 같은 문자열을 내게 하기 위해서다.
- git 밖 입력은 메인에서만 읽는다(실행본 인자, `--data-root`). 추적 입력은 경로마다 `git ls-tree -r --name-only T26 -- <경로>` 수가 0이 아님을 먼저 확인한 뒤 `git diff --name-only 932f1fb..<메인 HEAD> -- <경로들>` 0건을 본다. 0개 폴더의 diff 0은 확인으로 치지 않는다.
- **줄바꿈 잎**: worktree의 `03_src/outrigger_sim/control/c2.py`·`03_src/outrigger_sim/hydraulics/v5_options.py` raw sha256이 `git show 932f1fb:<파일>`의 CRLF 꼴 sha256과 같은지 본다(2절 '입력 기준' 끝 문장). 다르면 멈춘다."""

LINE17 = ("  - 합성 h11 출력에 `las_k1` 폴더 경로 문자열이 없고(파일 이름만), 경로 1 출력 어디에도 `--las-k1-dir`·`--data-root` 값이 "
          "없다(경로 1 출력은 argv를 적지 않음). 경로 2 출력에 `--data-root` 쌍이 남으면 부록 A I 인자 원소로 빠지는지 본다.")


def imua(d):
    d.sub("봉인 전, 수정 8)", "봉인 전, 수정 9)", tag="A1")
    d.insert_after(
        "  - 수정 8: verif rev26 네 번째 재감사",
        "  - 수정 9: verif rev26 다섯 번째 재감사 B-5(사용자 결정 (가): T26 경로 2 `--data-root`와 경로 1 실행본 입력 인자를 "
        "TA·J-2·A형 판정에 그대로, TA가 더하는 입력 읽기도 같은 기준, J-2 제외 1a), 기록 3(경로 2 `--allowed-src-changes`는 받기만 함)",
        tag="A2")
    d.sub("목록에 있는 03_src·02_params 변경만 허용. 인자가 없으면 허용 없음),",
          "목록에 있는 03_src·02_params 변경만 허용. 인자가 없으면 허용 없음. 경로 2 도구는 HEAD만 보고 03_src diff는 보지 않으므로 "
          "경로 2 쪽 이 인자는 **받기만 한다**. 경로 2의 03_src 확인은 실행본 PowerShell 관문(3.2의 3번)이 맡는다), (iv) T26 경로 2의 "
          "입력 기준 인자 `--data-root`(rev26 2절 '입력 기준')를 그대로 물려받는다. TA가 더하는 입력 읽기도 같은 기준을 따른다: 경로 2는 "
          "D를 `--data-root`로, 경로 1은 실행본 인자로 읽고, 도구 저장소에서는 rev26 W 범위의 추적 파일만 읽는다,",
          tag="A3")
    d.sub("excl_fields_r3.py", "excl_fields_r4.py", count=2, tag="A4a")
    d.sub("`--allowed-src-changes` 쌍은 r3 규칙이 인자 목록에서 이미 뺀다.",
          "`--allowed-src-changes`·`--data-root` 쌍은 r4 규칙이 인자 목록에서 이미 뺀다.", tag="A4b")
    d.insert_after(
        "  1. 모든 출력의 `v5_options` 하위 나무",
        "     - 1a. 경로 1 `h6_L1_reference.json :: meta.c2_py_sha256`(3.1 2항 목록에 `03_src/outrigger_sim/control/c2.py`가 있을 때만). "
        "비교 잎 가운데 03_src·02_params 파일 sha를 담은 것은 1과 1a뿐이다(작성자 점검 2026-11-23 `src_sha_leaves.py`: 436.8 원 출력의 "
        "비교 64자리 잎 2,402개 가운데 7개, `v5_options.sha256` 6곳과 이것)",
        tag="A5")
    d.sub("- 그대로 두는 것: cwd·입력 루트(메인 checkout), 인터프리터, 그 밖의 줄",
          "- 그대로 두는 것: cwd·입력 루트(메인 checkout), 입력 기준 인자(경로 2 `--data-root $Repo` 9개 호출, 경로 1 h11 "
          "`--las-k1-dir 06_analysis/02_control/v5_rerun/las_k1`·family_table `--data-root .`; rev26 2절), 인터프리터, 그 밖의 줄",
          tag="A6")
    d.sub("외부 도구·환경(rev26 `t26_identity.json`과 같은 항목)",
          "외부 도구·환경(rev26 `t26_identity.json`과 같은 항목), 입력 기준 표와 TA 구현 기록의 대조(TA가 더한 site 포함)", tag="A7")
    d.sub("TA worktree에서 rev26 규칙 파일·부록이 `-text`, `w/lf`;",
          "TA worktree에서 rev26 4′ W-l 대상 4개 파일(rev26 `.md`·`.sha256`·`excl_fields_r4.py`·`rev26_excluded_fields_r4.json`)이 "
          "`unset`·`w/lf`이고 폐기본은 `unset`만;", tag="A8a")
    d.sub("을 J-2 전에 verif가 한다.",
          "을 J-2 전에 verif가 한다. rev26 4′의 입력 기준 점검(TA 코드 기준)과 줄바꿈 잎 점검(TA worktree `c2.py`·`v5_options.py` "
          "raw sha = TA blob의 CRLF 꼴 sha. 3.1 목록에 든 파일은 J-2 제외 1·1a로 빠지므로 기록만 한다)도 함께 한다.", tag="A8b")


def report(name, d, out):
    a, b = d.orig.split("\n"), d.text.split("\n")
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    rem = add = 0
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op != "equal":
            rem += i2 - i1
            add += j2 - j1
    data = d.text.encode("utf-8")
    Path(out).write_bytes(data)
    crlf = b"\r\n" in data
    bom = data.startswith(b"\xef\xbb\xbf")
    print(f"{name}: sha256 {hashlib.sha256(data).hexdigest()} lines {len(a)} -> {len(b)} "
          f"removed {rem} added {add} edits {len(d.log)} crlf {crlf} bom {bom}")


def main():
    src26, srca, out26, outa = sys.argv[1:5]
    d26, da = Doc(src26), Doc(srca)
    rev26(d26)
    imua(da)
    report("rev26.r6", d26, out26)
    report("imua.r9", da, outa)


if __name__ == "__main__":
    main()
