"""Step convergence with xcheck.py converge: Hopsan 1e-5 -> 5e-6 s, numpy 5e-5 -> 2.5e-5 s.

Steady means over the scenario window. Writes xcheck/converge_<scenario>_<path>.json and
converge_summary.json.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from params import LEGS, OUT_DIR  # noqa: E402
from scenarios import BY_NAME  # noqa: E402

XCHECK = Path.home() / ".claude" / "tools" / "hydraulics" / "xcheck.py"
NAMES = ("B85p", "B85c", "C185c", "C385c", "T185p", "B90c")


def quantities(sc, path: str) -> list[dict]:
    win = [sc.t_end - sc.window, sc.t_end]
    q = []
    for leg in LEGS:
        var_v = f"Mass{leg}#P2#Velocity" if path == "hopsan" else f"v_{leg}"
        q.append({"name": f"v_{leg}", "var": {"var": var_v, "unit": "m/s"}, "metric": "mean", "window": win,
                  "unit": "m/s", "floor": 1e-3, "kind": "flow"})
        var_p = f"Spool{leg}#PA#Pressure" if path == "hopsan" else f"p_h_{leg}"
        spec = {"var": var_p, "unit": "Pa"}
        if path == "numpy":
            spec["pressure_ref"] = "gauge"
        q.append({"name": f"p_h_{leg}", "var": spec, "metric": "mean", "window": win, "unit": "Pa", "floor": 1e5,
                  "kind": "pressure"})
    spec = {"var": "Pump#P2#Pressure" if path == "hopsan" else "p_P", "unit": "Pa"}
    if path == "numpy":
        spec["pressure_ref"] = "gauge"
    q.append({"name": "p_P", "var": spec, "metric": "mean", "window": win, "unit": "Pa", "floor": 1e5, "kind": "pressure"})
    return q


def main() -> None:
    out_dir = OUT_DIR / "xcheck"
    out = {}
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    for name in NAMES:
        sc = BY_NAME[name]
        for path, kind in (("hopsan", "hopsan"), ("numpy", "om")):
            map_path = out_dir / f"converge_{name}_{path}_map.json"
            map_path.write_text(json.dumps({"quantities": quantities(sc, path)}), encoding="utf-8")
            report = out_dir / f"converge_{name}_{path}.json"
            cmd = [sys.executable, "-I", str(XCHECK), "converge", "--map", str(map_path), "--run-kind", kind, "--ratio", "2",
                   "--run", str(OUT_DIR / path / f"{name}.csv"), "--run", str(OUT_DIR / path / f"{name}_dt2.csv"),
                   "--out", str(report), "--warnings-ok"]
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, check=False)
            lines = proc.stdout.strip().splitlines()
            if not lines:
                raise RuntimeError(f"{name} {path}: {proc.stderr[-800:]}")
            rep = json.loads(report.read_text(encoding="utf-8"))
            flat = {r["quantity"]: float(r["rel"]) for r in rep["rows"]}
            worst = max(flat, key=flat.get)
            out[f"{name}/{path}"] = {"verdict": rep["verdict"], "worst": worst, "worst_change": flat[worst], "exit": proc.returncode}
            print(name, path, rep["verdict"], worst, f"{flat[worst]:.5f}")
    (OUT_DIR / "converge_summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
