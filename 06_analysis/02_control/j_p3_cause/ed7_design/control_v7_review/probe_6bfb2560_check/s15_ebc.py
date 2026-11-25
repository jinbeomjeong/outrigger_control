"""Whole-line extend_bound_check breach sums by plant x arm (record of the run's own monitor)."""
import sys
from pathlib import Path

import pandas as pd

L = pd.read_csv(Path(sys.argv[1]) / "lines.csv")
cols = [c for c in ("ebc_breach_reads", "ebc_jp3a_breach_reads", "ebc_jp3b_breach_reads",
                    "ebc_jp3c_breach_reads", "ebc_locked_over_tol") if c in L]
print("lines with ebc:", int(L[cols[0]].notna().sum()), "of", len(L))
print(L.groupby(["part", "plant"])[cols].sum().to_string())
print("lines with any > 0:")
print(L[(L[cols].fillna(0) > 0).any(axis=1)][["key", "plant", "arm", *cols]].to_string(index=False))
