"""Append the rev26 section 7 ``-text`` lines to a worktree .gitattributes (CRLF work tree)."""

import sys
from pathlib import Path

LINES = (
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev26.md -text",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev26.sha256 -text",
    "06_analysis/02_control/verif_matrix/v5_resume_4368_rules_rev26_seal_candidate_draft.md -text",
    "06_analysis/02_control/verif_matrix/v5_resume_4368/rev26_fixed/** -text",
    "06_analysis/02_control/verif_matrix/v5_resume_4368/judge_rev26_*/** -text",
    "06_analysis/02_control/verif_matrix/v5paper_imua_stats/** -text",
)


def main() -> int:
    path = Path(sys.argv[1])
    data = path.read_bytes()
    if not data.endswith(b"\r\n"):
        raise SystemExit("unexpected ending")
    text = "".join(f"{line}\r\n" for line in LINES)
    path.write_bytes(data + text.encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
