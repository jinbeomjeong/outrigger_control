"""Write SHA256SUMS (sha256sum format) for the files of this folder and of the inputs read."""
import hashlib
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = Path(r"C:\workspace\outrigger_control")
INPUTS = [
    ROOT / "06_analysis/03_hydraulic/coupled/v5/main.jsonl",
    ROOT / "06_analysis/02_control/j_p3_cause/j9_runs/606f8713/j9main_a1/j9_main.jsonl",
    ROOT / "06_analysis/02_control/j_p3_cause/j9_runs/606f8713/j9main_a1/judge/j9main_judge.json",
    ROOT / "06_analysis/02_control/j_p3_cause/j9_runs/606f8713/t8_a1/j9_t8.jsonl",
    ROOT / "06_analysis/02_control/j_p3_cause/j9_runs/78fd5d2d/t8_a1/j9_t8.jsonl",
    ROOT / "06_analysis/02_control/j_p3_cause/j9_runs/fa997f4c/t8_a1/j9_t8.jsonl",
]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


lines = [f"{sha(p)}  {p.name}" for p in sorted(OUT.iterdir())
         if p.is_file() and p.name not in ("SHA256SUMS", "INPUTS.SHA256SUMS")]
(OUT / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
inp = [f"{sha(p)}  {p.relative_to(ROOT).as_posix()}" for p in INPUTS]
(OUT / "INPUTS.SHA256SUMS").write_text("\n".join(inp) + "\n", encoding="utf-8")
print("\n".join(lines + ["--- inputs"] + inp))
