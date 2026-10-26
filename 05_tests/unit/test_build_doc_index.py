"""Tests for 04_scripts/00_docs/build_doc_index.py (Markdown line-range index)."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "04_scripts" / "00_docs" / "build_doc_index.py"
MODULE_NAME = "build_doc_index"


def _load_module():
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolves string annotations through sys.modules.
    sys.modules[MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


bdi = _load_module()


def _write_doc(tmp_path: Path, lines: list[str], name: str = "doc.md") -> Path:
    path = tmp_path / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return path


def _entries(path: Path, depth: int = 4, split_lines: int = 400):
    return bdi.build_entries(bdi.load_document(path), depth, split_lines)


def _headings_only(entries):
    return [entry for entry in entries if not entry.kind.startswith("+")]


SAMPLE_LINES = [
    "# 명세 제목",  # 1
    "",  # 2
    "머리말 문장이다. 둘째 문장.",  # 3
    "## 0. 요약",  # 4
    "",  # 5
    "| 표 | 건너뜀 |",  # 6
    "|---|---|",  # 7
    "![그림](a.png)",  # 8
    "요약 본문 첫 문장이다. 다음 문장.",  # 9
    "```python",  # 10
    "# 코드 안 주석은 제목이 아니다",  # 11
    "```",  # 12
    "## 2. 구현",  # 13
    "### 2.1 목표 자세",  # 14
    "$$",  # 15
    "# 수식 안 줄도 제목이 아니다",  # 16
    "$$",  # 17
    "$$J = \\begin{bmatrix}",  # 18
    "## 수식 안 (닫는 $$ 가 줄 끝에 있다)",  # 19 (inside math: odd count closes it)
    "### 2.2 다음 절",  # 20
    "$$x = 1$$",  # 21 one-line display math, does not open a block
    "#### 2.2.1 깊은 절",  # 22
    "~~~",  # 23
    "## 물결 펜스 안",  # 24
    "~~~",  # 25
    "# 개정 3 (2026-10-21): 결과 판단",  # 26
    "## 16. 판단",  # 27
    "끝 문장",  # 28
]


class TestBlocks:
    def test_code_fence_and_math_lines_are_not_headings(self, tmp_path):
        path = _write_doc(tmp_path, SAMPLE_LINES)
        start_lines = [entry.start_line for entry in _headings_only(_entries(path))]
        assert start_lines == [1, 4, 13, 14, 20, 22, 26, 27]

    def test_math_block_closing_mid_line(self):
        lines = ["$$J = a", "# inside", "b\\end{x}$$", "# outside"]
        assert bdi.mark_block_lines(lines) == [True, True, True, False]

    def test_one_line_display_math_does_not_open_block(self):
        lines = ["$$x$$", "# outside"]
        assert bdi.mark_block_lines(lines) == [True, False]

    def test_longer_fence_needs_longer_close(self):
        lines = ["````", "```", "# inside", "````", "# outside"]
        assert bdi.mark_block_lines(lines) == [True, True, True, True, False]

    def test_dollar_fence_inside_code_is_ignored(self):
        lines = ["```", "$$", "```", "# outside"]
        assert bdi.mark_block_lines(lines) == [True, True, True, False]


class TestSectionNumbers:
    @pytest.mark.parametrize(
        ("title", "number"),
        [
            ("0. 요약", "0"),
            ("2.1 목표 자세", "2.1"),
            ("3.9.7.1 모델", "3.9.7.1"),
            ("297. 개정 59 보완", "297"),
            ("개정 3 (2026-10-21): 결과", "개정 3"),
            ("개정 이력", ""),
            ("2026-10-21 메모", ""),
            ("요약", ""),
        ],
    )
    def test_extract(self, title, number):
        assert bdi.extract_section_number(title) == number

    def test_number_is_removed_from_title_column(self, tmp_path):
        path = _write_doc(tmp_path, SAMPLE_LINES)
        titles = {entry.number: entry.title for entry in _entries(path)}
        assert titles["0"] == "요약"
        assert titles["2.1"] == "목표 자세"
        assert titles["개정 3"] == "개정 3 (2026-10-21): 결과 판단"


class TestLineRanges:
    def test_end_lines_cover_subsections_and_stop_at_same_level(self, tmp_path):
        path = _write_doc(tmp_path, SAMPLE_LINES)
        ranges = {entry.start_line: (entry.end_line, entry.line_count) for entry in _entries(path)}
        assert ranges[1] == (25, 25)  # "#" ends before the next "#"
        assert ranges[4] == (12, 9)
        assert ranges[13] == (25, 13)  # "## 2." holds 2.1, 2.2, 2.2.1
        assert ranges[14] == (19, 6)
        assert ranges[20] == (25, 6)
        assert ranges[22] == (25, 4)
        assert ranges[27] == (28, 2)  # last section ends at the last line

    def test_ranges_match_source_lines(self, tmp_path):
        path = _write_doc(tmp_path, SAMPLE_LINES)
        source_lines = path.read_text(encoding="utf-8").split("\n")
        for entry in _headings_only(_entries(path)):
            assert source_lines[entry.start_line - 1].startswith("#")
            next_line = entry.end_line  # 0-based index of the line after the section
            if next_line < len(SAMPLE_LINES):
                level = len(entry.kind)
                following = source_lines[next_line]
                assert following.startswith("#")
                assert len(following) - len(following.lstrip("#")) <= level

    def test_crlf_and_missing_final_newline(self, tmp_path):
        path = tmp_path / "crlf.md"
        path.write_bytes("# A\r\n본문\r\n## B\r\n끝".encode())
        document = bdi.load_document(path)
        assert document.lines == ["# A", "본문", "## B", "끝"]
        assert document.total_bytes == path.stat().st_size
        entries = bdi.build_entries(document, 4, 400)
        assert [(e.start_line, e.end_line) for e in entries] == [(1, 4), (3, 4)]

    def test_depth_limits_listed_levels(self, tmp_path):
        path = _write_doc(tmp_path, SAMPLE_LINES)
        kinds = {entry.kind for entry in _entries(path, depth=2)}
        assert kinds == {"#", "##"}


class TestFirstSentence:
    def test_skips_tables_images_and_fences(self, tmp_path):
        path = _write_doc(tmp_path, SAMPLE_LINES)
        sentences = {entry.start_line: entry.first_sentence for entry in _entries(path)}
        assert sentences[1] == "머리말 문장이다."
        assert sentences[4] == "요약 본문 첫 문장이다."
        assert sentences[13] == ""  # next line is a heading
        assert sentences[27] == "끝 문장"

    def test_decimal_point_is_not_a_sentence_end(self):
        assert bdi.leading_sentence("값은 0.1 s다. 다음.") == "값은 0.1 s다."

    def test_long_sentence_is_truncated(self):
        sentence = bdi.leading_sentence("가" * 300)
        assert len(sentence) == bdi.SENTENCE_MAX_CHARS
        assert sentence.endswith("…")

    def test_blockquote_and_bold_markers_are_removed(self, tmp_path):
        path = _write_doc(tmp_path, ["## 1. 절", "> **현재 상태**: 개정 61이다. 끝."])
        assert _entries(path)[0].first_sentence == "현재 상태: 개정 61이다."


def _long_section_lines() -> list[str]:
    lines = ["## 5. 큰 절", "첫 문장이다."]  # 1-2
    lines += [f"본문 {i}" for i in range(3, 13)]  # 3-12
    lines += ["**판정 1**: 통과다. 이유."]  # 13
    lines += [f"본문 {i}" for i in range(14, 24)]  # 14-23
    lines += ["| 항목 | 값 |", "|---|---|", "| a | 1 |"]  # 24-26
    lines += ["**가까운 단락**"]  # 27, within min_gap of 24 -> merged
    lines += [f"본문 {i}" for i in range(28, 38)]  # 28-37
    lines += ["##### 5.1.1.1 깊은 제목", "깊은 본문이다."]  # 38-39
    lines += [f"본문 {i}" for i in range(40, 51)]  # 40-50
    lines += ["## 6. 다음"]  # 51
    return lines


class TestSplitLongSections:
    def test_split_rows_and_ranges(self, tmp_path):
        path = _write_doc(tmp_path, _long_section_lines())
        entries = _entries(path, split_lines=20)
        rows = [(e.kind, e.number, e.title, e.start_line, e.end_line) for e in entries]
        assert rows == [
            ("##", "5", "큰 절", 1, 50),
            ("+단락", "5", "판정 1", 13, 23),
            ("+표", "5", "표: 항목 / 값", 24, 37),
            ("+#####", "5.1.1.1", "깊은 제목", 38, 50),
            ("##", "6", "다음", 51, 51),
        ]
        assert entries[1].first_sentence == "통과다."
        assert entries[3].first_sentence == "깊은 본문이다."

    def test_short_section_is_not_split(self, tmp_path):
        path = _write_doc(tmp_path, _long_section_lines())
        assert all(not e.kind.startswith("+") for e in _entries(path, split_lines=400))

    def test_split_uses_own_body_not_subsections(self, tmp_path):
        lines = ["## 1. 부모", "짧다.", "### 1.1 자식"]  # 1-3
        lines += [f"줄 {i}" for i in range(4, 16)]  # 4-15
        lines += ["**굵게**"]  # 16
        lines += [f"줄 {i}" for i in range(17, 37)]  # 17-36
        path = _write_doc(tmp_path, lines)
        rows = [(e.kind, e.start_line, e.end_line) for e in _entries(path, split_lines=20)]
        assert rows == [("##", 1, 36), ("###", 3, 36), ("+단락", 16, 36)]

    def test_anchor_right_after_heading_is_merged_into_heading(self, tmp_path):
        lines = ["## 1. 절", "**바로 뒤 단락**"] + [f"줄 {i}" for i in range(30)]
        path = _write_doc(tmp_path, lines)
        assert [e.kind for e in _entries(path, split_lines=20)] == ["##"]


class TestRevisionSummary:
    def test_revision_table_is_copied_with_line_column(self, tmp_path):
        lines = [
            "# 명세",
            "| 개정 | 날짜 | 제목(요약) | 절 |",
            "|---|---|---|---|",
            "| 초판 | 2026-10-21 | 처음 | 0~1 |",
            "| 1 | 2026-10-22 | 둘째 | 2, 2.1 |",
            "| 2 | 2026-10-22 | 없음 | (번호 절 없음) |",
            "",
            "## 0. 요약",
            "## 1. 규약",
            "## 2. 구현",
            "### 2.1 목표",
            "끝",
        ]
        path = _write_doc(tmp_path, lines)
        document = bdi.load_document(path)
        summary = bdi.build_revision_summary(document, bdi.build_entries(document, 4, 400))
        assert summary[0] == "| 개정 | 날짜 | 제목(요약) | 절 | 줄 |"
        assert summary[2] == "| 초판 | 2026-10-21 | 처음 | 0~1 | 8–9 |"
        assert summary[3] == "| 1 | 2026-10-22 | 둘째 | 2, 2.1 | 10–12, 11–12 |"
        assert summary[4] == "| 2 | 2026-10-22 | 없음 | (번호 절 없음) |  |"

    def test_revision_paragraphs_become_a_table(self, tmp_path):
        lines = [
            "# 동역학",
            "",
            "개정 54(2026-10-26, **잠김 강성 범위(5.1, U-1)**, 실행 없음): 본문.",
            "",
            "개정 53(2026-10-25, **새 절 없음**): 본문.",
            "",
            "## 5. 검증",
            "### 5.1 강성",
            "끝",
        ]
        path = _write_doc(tmp_path, lines)
        document = bdi.load_document(path)
        summary = bdi.build_revision_summary(document, bdi.build_entries(document, 4, 400))
        assert summary[2] == "| 54 | 2026-10-26 | 잠김 강성 범위(5.1, U-1) | 5.1 | 8–9 |"
        assert summary[3] == "| 53 | 2026-10-25 | 새 절 없음 |  |  |"

    def test_no_revision_information(self, tmp_path):
        path = _write_doc(tmp_path, ["# 제목", "## 1. 절"])
        document = bdi.load_document(path)
        assert bdi.build_revision_summary(document, bdi.build_entries(document, 4, 400)) == []


class TestWriteIndex:
    def test_index_file_header_and_rows(self, tmp_path):
        path = _write_doc(tmp_path, SAMPLE_LINES)
        target = bdi.write_index(path, depth=4, split_lines=400)
        assert target == tmp_path / "doc_index.md"
        text = target.read_text(encoding="utf-8")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        assert f"`{digest}`" in text
        assert "- 총 줄 수: 28 " in text
        assert "Read에 offset=시작 줄, limit=줄 수" in text
        assert "| ### | 2.1 | 목표 자세 | 14 | 19 | 6 |" in text

    def test_pipe_in_title_is_escaped(self, tmp_path):
        path = _write_doc(tmp_path, ["## 1. a | b"])
        text = bdi.write_index(path, depth=4, split_lines=400).read_text(encoding="utf-8")
        assert "| ## | 1 | a \\| b |" in text

    def test_default_sources_filter(self, tmp_path, monkeypatch):
        docs = tmp_path / "00_docs"
        big_text = "# 큰 문서\n" + "x" * (bdi.LARGE_DOC_MIN_BYTES + 1)
        for relative in [
            "a/big.md",
            "a/history/big.md",
            "drafts/big.md",
            "a/big_index.md",
            "a/big_current.md",
        ]:
            target = docs / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(big_text, encoding="utf-8")
        (docs / "a" / "small.md").write_text("# 작다\n", encoding="utf-8")
        named = docs / "named.md"
        named.write_text("# 지정 문서\n", encoding="utf-8")
        monkeypatch.setattr(bdi, "DOCS_DIR", docs)
        monkeypatch.setattr(bdi, "DEFAULT_DOCS", (named,))
        assert bdi.default_sources() == sorted([(docs / "a" / "big.md").resolve(), named.resolve()])
