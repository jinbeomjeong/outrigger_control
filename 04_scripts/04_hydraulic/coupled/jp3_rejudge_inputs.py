"""Fixed inputs of the 436.9 VBJ re-judgement (addendum 4a-8 4, 6, 7).

Kept apart from ``jp3_fixed_inputs`` on purpose: that module is in the static import closure
of the Dg-3 / L1 runner ``las_t3_dg3.py`` (through ``run_v5``), and 4a-8 6.1 allows the VBJ
re-judgement exception only when the fixed commit leaves that closure unchanged. Only judge
tools import this module (``jp3_import_closure.py`` shows it outside the closure).
"""

L1_KEY_COUNT = 102
"""4a-8 4.2: distinct (harness, inner) of the stored H-6 135 lines (g6 63, g8 29, ref 10)."""

RUN_COMMIT_78FD5D2D = "78fd5d2d03e40ac7d9143429f602b58255c762fc"
"""The run commit of the Dg-3 outputs the re-judgement reads (4a-8 6.2 3)."""

DG3_VBJ_SHA256 = "603e4b815d8abc11f09bb85731f9591df5e4c6cc812f2dd9f0e6c7ebae070cd0"
"""4a-8 6.2 3 / 7: ``j9_runs/78fd5d2d/dg3_a1/dg3_VBJ.json`` (161,168,847 B, local only)."""
DG3_VBJ0_SHA256 = "c1201b2d160dc2fee08671cdb285df65fa367e22b2e6af643e87c5216252b9c7"
"""4a-8 6.2 3 / 7: ``j9_runs/78fd5d2d/dg3_a1/dg3_VBJ0.json`` (committed)."""
DG3_VBH_SHA256 = "1cf7f86691163267777f003747b7347f4e000a053f929ad88e2bd099f5c5fe03"
"""4a-8 7: ``j9_runs/78fd5d2d/dg3_a1/dg3_VBH.json`` (167,317,196 B, local only; not re-judged)."""
