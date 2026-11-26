"""Q8-5: scan the edition 8 setting names and tag suffix for collisions (read only).

Usage: python -I -B scan_tokens.py <worktree root> <out json>

Scans only the sub-paths named in SCAN_ROOTS (never a parent folder). Prints counts only;
the hits with a short context go to the output file.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCAN_ROOTS = {
    "03_src": (".py",),
    "04_scripts": (".py",),
    "05_tests": (".py",),
    "00_docs": (".md", ".yaml", ".json"),
    "02_params": (".md", ".yaml", ".json"),
}
CONTEXT_CHARS = 60
PROPOSED_SETTINGS = (
    "VBN", "VBN0", "LSN1", "LSN2", "LSN3", "LSN4",
    *(f"VBN{key}" for key in ("slow", "fast", "c005", "c04", "b069", "b16", "h05", "h15",
                              "d05", "d15")),
    "VBKN", "VBKN0",
)
TOKEN_PATTERNS = {
    "VBN_any": re.compile(r"VBN"),
    "LSN_any": re.compile(r"LSN"),
    "VBKN_any": re.compile(r"VBKN"),
    "_E8_case_sensitive": re.compile(r"_E8"),
    "E8_word_case_sensitive": re.compile(r"(?<![A-Za-z0-9])E8(?![A-Za-z0-9])"),
    "e8_token_case_insensitive": re.compile(r"(?i)(?<![A-Za-z0-9])e8(?![A-Za-z0-9])"),
    "_e8_case_insensitive": re.compile(r"(?i)_e8"),
}


def iter_files(root: Path):
    for sub, suffixes in SCAN_ROOTS.items():
        base = root / sub
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix.lower() in suffixes:
                yield sub, path


def scan(root: Path) -> dict:
    hits: dict[str, list[dict]] = {name: [] for name in TOKEN_PATTERNS}
    files_scanned = 0
    for _, path in iter_files(root):
        files_scanned += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        for name, pattern in TOKEN_PATTERNS.items():
            for match in pattern.finditer(text):
                start = max(0, match.start() - CONTEXT_CHARS)
                end = min(len(text), match.end() + CONTEXT_CHARS)
                line_no = text.count("\n", 0, match.start()) + 1
                hits[name].append({"file": str(path.relative_to(root)).replace("\\", "/"),
                                   "line": line_no,
                                   "context": text[start:end].replace("\n", " | ")})
    return {"files_scanned": files_scanned, "roots": SCAN_ROOTS,
            "proposed_settings": list(PROPOSED_SETTINGS),
            "counts": {name: len(found) for name, found in hits.items()}, "hits": hits}


def main() -> int:
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    result = scan(root)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"files_scanned": result["files_scanned"], "counts": result["counts"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
