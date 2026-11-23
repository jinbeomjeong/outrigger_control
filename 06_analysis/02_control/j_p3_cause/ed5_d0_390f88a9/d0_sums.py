"""Write SHA256SUMS (LF) of this folder and INPUTS.SHA256SUMS of the inputs read."""
import hashlib
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = Path(r"C:\workspace\outrigger_control")
INPUTS = [
    ROOT / "06_analysis/02_control/j_p3_cause/j9_runs/390f88a9/d0_plant_split_a1/d0_summary.json",
    ROOT / "06_analysis/02_control/j_p3_cause/j9_runs/390f88a9/d0_plant_split_a1/d0_plant_split.jsonl",
    ROOT / "06_analysis/03_hydraulic/coupled/v5/main.jsonl",
    ROOT / "06_analysis/02_control/j_p3_cause/j9_runs/606f8713/j9main_a1/j9_main.jsonl",
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


files = [p for p in sorted(OUT.iterdir()) if p.is_file() and p.name not in ("SHA256SUMS", "INPUTS.SHA256SUMS")]
(OUT / "SHA256SUMS").write_bytes(("\n".join(f"{sha(p)}  {p.name}" for p in files) + "\n").encode())
(OUT / "INPUTS.SHA256SUMS").write_bytes(
    ("\n".join(f"{sha(p)}  {p.relative_to(ROOT).as_posix()}" for p in INPUTS) + "\n").encode())
print((OUT / "SHA256SUMS").read_text(), (OUT / "INPUTS.SHA256SUMS").read_text(), sep="\n")
