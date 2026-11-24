"""t_ready_back, final phase, gates and run end of R12 top-{FR,RL,RR}-Fs0 rows: V0 (stored),
edition 5 VBJ / LSJ (606f8713 j9_main) and the confirmation (가) settings."""
import json
from pathlib import Path

CAUSE = Path(r"C:\workspace\outrigger_control\06_analysis\02_control\j_p3_cause")
FILES = {"V0": CAUSE.parents[1] / "03_hydraulic/coupled/v5/main.jsonl",
         "ed5": CAUSE / "j9_runs/606f8713/j9main_a1/j9_main.jsonl",
         "ed6_confirm_a": CAUSE / "j9_runs/79495405/confirm_a1/confirm_a.jsonl"}


def main():
    for label, path in FILES.items():
        for text in path.read_text(encoding="utf-8").splitlines():
            if not text.strip():
                continue
            row = json.loads(text)
            job = row.get("job", {})
            twin = job.get("twin") or {}
            if job.get("case") != "R12" or twin.get("level") != "top" or twin.get("fs_kN") != 0.0:
                continue
            if twin.get("leg") not in ("FR", "RL", "RR", "FL"):
                continue
            if label == "V0" and job.get("setting") != "V0":
                continue
            ev = row.get("event_output") or {}
            fmin = ev.get("min_F_after_W_kN") or {}
            print(label, job.get("setting"), twin.get("leg"), job.get("offset_s"),
                  "final", ev.get("final_phase"), "t_back", ev.get("t_ready_back_s"),
                  "pass", ev.get("pass"), "Fmin_W", round(min(fmin.values()), 2) if fmin else None)


if __name__ == "__main__":
    main()
