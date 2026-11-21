"""Run the new e2e baseline-compare test against the b51ed6e1 module (expect it to fail)."""
import sys
from pathlib import Path

old_dir, worktree = sys.argv[1], Path(sys.argv[2])
sys.path.insert(0, str(worktree / "04_scripts" / "04_hydraulic" / "coupled"))
sys.path.insert(0, str(worktree / "05_tests" / "unit"))
sys.path.insert(0, old_dir)  # the old jp3_baseline_compare wins
import pytest  # noqa: E402

code = pytest.main([str(worktree / "05_tests" / "unit" / "test_jp3_judge_main_e2e.py"),
                    "-k", "baseline_compare", "-q", "-p", "no:cacheprovider"])
import jp3_baseline_compare  # noqa: E402

print("module", jp3_baseline_compare.__file__, "pytest exit", int(code))
