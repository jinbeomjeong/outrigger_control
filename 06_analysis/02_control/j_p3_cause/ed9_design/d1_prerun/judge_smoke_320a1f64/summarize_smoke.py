"""Print the status, reasons and per-layer counts of the stage 5 smoke reports (no slot-level
values) and the aa-candidates counts."""
import json
import sys
from pathlib import Path

folder = Path(sys.argv[1])
for name in ("ed8", "ed8_j7a", "ed9"):
    report = json.loads((folder / f"stage5_{name}.json").read_text(encoding="utf-8"))
    layers = {layer: {key: values.get(key) for key in ("n", "x_aa", "n_aa", "cp95")}
              for layer, values in (report.get("layers") or {}).items()}
    basis = report.get("status_basis") or {}
    print(name, "status", report.get("status"), "reasons", report.get("reasons"),
          "merged", report.get("merged_why"), "slot_count", report.get("slot_count"),
          "layered", len(report.get("slot_layers") or {}),
          "aliases", len(report.get("first_aliases") or []),
          "basis_counts", {k: len(v) for k, v in basis.items()},
          "candidate_not_run", len(report.get("candidate_not_run") or []))
    print("   layers", layers)
    breakdown = report.get("aa_breakdown") or {}
    for layer, values in breakdown.items():
        print("   breakdown", layer, "n", values["n"], "x", values["x"],
              "source", values["source"], "item_group", values["item_group"])
listing = json.loads((folder / "aa_candidates_ed9.json").read_text(encoding="utf-8"))
print("aa-candidates", listing["status"], listing["slot_count"], listing["by_source"],
      "not_run_jobs", len(listing["not_run_jobs"]))
