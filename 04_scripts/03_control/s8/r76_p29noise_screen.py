"""Spec rev. 75 draft: P-S8-29 noise-margin candidates on the G6 / G8 harnesses (project controller bee0693 +
subclass / config change; 03_src read only). Reuses the r74_p30_screen.py jobs (its controller factory is swapped).

  proj   project controller
  Pa     (a) the relaxed-completion test sees the 1 s moving mean of |D| (last 10 calls of _is_twist_relax_ok;
         the buffer empties with the relax history)
  Pb     (b) rise tolerance 0.3 -> 0.6 kN (config twist_completion_relax.rise_tol_N)

Usage (repo root, dynamics-dev): python -I r76_p29noise_screen.py <project_root> <out_json> [workers]
Env: R76_VARIANTS (default proj,Pa,Pb), R76_SET (comma: g6, g6r, g8slope, g8wide, g8flat), R76_FILTER,
     R76_AFFINITY (hex mask on the parent).
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import deque
from dataclasses import replace
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT / "04_scripts" / "03_control" / "s8"))

import r74_p30_screen as r74  # noqa: E402

VARIANTS = {"proj": None, "Pa": {"mean_n": 10}, "Pb": {"rise_tol_N": 600.0}}


def make_class(c2, params):
    class P29nController(c2.C2Controller):
        p29n = params

        @classmethod
        def from_params(cls, p, config):
            if cls.p29n.get("rise_tol_N") is not None:
                config = replace(config, twist_completion_relax=replace(
                    config.twist_completion_relax, rise_tol_N=float(cls.p29n["rise_tol_N"])))
            return super().from_params(p, config)

        def _clear_twist_relax(self):
            buf = getattr(self, "_p29n_buf", None)
            if buf is not None:
                buf.clear()
            return super()._clear_twist_relax()

        def _is_twist_relax_ok(self, reading, twist_load_N, is_on_target, is_clearance_done):
            n = self.p29n.get("mean_n")
            if n:
                buf = getattr(self, "_p29n_buf", None)
                if buf is None:
                    buf = self._p29n_buf = deque(maxlen=int(n))
                buf.append(abs(float(twist_load_N)))
                twist_load_N = float(sum(buf) / len(buf))
            return super()._is_twist_relax_ok(reading, twist_load_N, is_on_target, is_clearance_done)

    return P29nController


def job(key):
    var = key.rsplit("|", 1)[1]
    r74.VARIANTS[var] = VARIANTS[var]
    r74.make_p30_class = make_class  # the r74 jobs build the variant controller through this name
    rec = r74.job(key)
    return rec


def main():
    variants = os.environ.get("R76_VARIANTS", "proj,Pa,Pb").split(",")
    for v in variants:
        r74.VARIANTS[v] = VARIANTS[v]
    jobs = r74.all_jobs(os.environ.get("R76_SET", "g6,g6r").split(","), variants)
    filt = os.environ.get("R76_FILTER")
    if filt:
        jobs = [j for j in jobs if any(f in j for f in filt.split(","))]
    if len(sys.argv) > 2 and sys.argv[2] == "--list":
        print("\n".join(jobs))
        return
    os.environ["R74_AFFINITY"] = os.environ.get("R76_AFFINITY", "")
    if os.environ["R74_AFFINITY"]:
        r74.set_parent_placement()
    out = Path(sys.argv[2])
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    t0 = time.perf_counter()
    with Pool(max(1, min(workers, len(jobs)))) as pool:
        res = pool.map(job, jobs, chunksize=1)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"meta": {"script": "04_scripts/03_control/s8/r76_p29noise_screen.py",
                                        "variants": {v: VARIANTS[v] for v in variants}, "n_jobs": len(jobs),
                                        "wall_s": round(time.perf_counter() - t0, 1)},
                               "results": res}, indent=1, default=float), encoding="utf-8")
    print("done", round(time.perf_counter() - t0, 1), "s ->", out)


if __name__ == "__main__":
    main()
