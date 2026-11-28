"""Status, reasons and layer counts of the T9 stage 5 smoke (no slot-level value)."""
import json
import sys
from pathlib import Path

folder = Path(sys.argv[1])
for name in ("ed8", "ed8_j7a", "ed9"):
    report = json.loads((folder / f"stage5_{name}.json").read_text(encoding="utf-8"))
    layers = {layer: (values.get("x_aa"), values.get("n_aa"), values.get("n"))
              for layer, values in (report.get("layers") or {}).items()}
    basis = report.get("status_basis") or {}
    print(name, report.get("status"), report.get("reasons"), "slot_count",
          report.get("slot_count"), "layers (x, n_aa, n)", layers,
          "basis", {k: [str(t)[:90] for t in v][:2] for k, v in basis.items() if v},
          "identity_defects", len(report.get("identity_defects") or []),
          "run_commit", report.get("run_commit"))
    breakdown = report.get("aa_breakdown") or {}
    for layer, values in breakdown.items():
        print("  ", layer, "exclusive", values.get("item_group_exclusive"))
