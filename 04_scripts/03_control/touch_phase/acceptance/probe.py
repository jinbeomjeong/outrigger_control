"""Short acceptance probes: each bundle's driver on a few items, 4 workers on E 24..27, CPU/wall and peak RSS of the tree.

Output probe.json. Results go to probe_out/ (never the acceptance folder). ``--only`` picks probes by name.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

import psutil

import build_steps as b

OUT = b.HERE / "probe_out"
MASK = 0x0F000000
CPUS = [24, 25, 26, 27]
W = 4
L2_KEYS = ["L2|s0|g6|52|ref|J1|top|Fs0", "L2|s1|g6|53|ref|J1|top|Fs4", "L2|s2|g6|56|ref|J2|top|Fs0", "L2|s3|g6|57|ref|J2|top|Fs4"]


def tree_probe(name: str, cmd: list[str], env: dict, n_items: int) -> dict:
    (OUT / name).mkdir(parents=True, exist_ok=True)
    log = (OUT / name / "stdout.log").open("w", encoding="utf-8")
    t0 = time.perf_counter()
    proc = subprocess.Popen(cmd, cwd=str(b.WT), env={**__import__("os").environ, **b.BASE_ENV, **env}, stdout=log, stderr=subprocess.STDOUT)
    parent = psutil.Process(proc.pid)
    parent.cpu_affinity(CPUS)
    parent.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    seen, cpu, peak, peak_each = {}, 0.0, 0.0, 0.0
    threads_max = 0
    while proc.poll() is None:
        total, threads = 0.0, 0
        try:
            procs = [parent] + parent.children(recursive=True)
        except psutil.Error:
            break
        for p in procs:
            try:
                info = p.memory_info()
                total += info.rss
                peak_each = max(peak_each, info.rss)
                threads = max(threads, p.num_threads())
                t = p.cpu_times()
                seen[p.pid] = t.user + t.system
            except psutil.Error:
                pass
        peak, threads_max = max(peak, total), max(threads_max, threads)
        time.sleep(1.0)
    wall = time.perf_counter() - t0
    cpu = sum(seen.values())
    rec = {"name": name, "exit": proc.returncode, "items": n_items, "workers": W, "wall_s": round(wall, 1), "cpu_s_seen": round(cpu, 1),
           "cpu_over_wall": round(cpu / wall, 2), "cpu_per_worker_over_wall": round(cpu / wall / W, 2), "peak_tree_rss_MB": round(peak / 2**20),
           "peak_proc_rss_MB": round(peak_each / 2**20), "max_threads_one_proc": threads_max, "wall_x_workers_per_item_s": round(wall * W / max(1, n_items), 1)}
    print(json.dumps(rec), flush=True)
    return rec


def probes() -> dict:
    py, launch = b.PY, str(b.LAUNCH)
    r79 = str(b.S8 / "r79_L3L4_final.py")
    return {
        "L2": (lambda: tree_probe("L2", [py, "-I", "-B", launch, r79, str(b.WT), "run", str(OUT / "L2" / "r.json"), "--workers", str(W), "--levels", "L1,L2", "--keys", ";".join(L2_KEYS + [k.replace("L2|s0", "L1|s0") for k in L2_KEYS[:1]])],
                                  {"R72_PATH": "per_leg"}, 5)),
        "L3": (lambda: tree_probe("L3", [py, "-I", "-B", launch, r79, str(b.WT), "run", str(OUT / "L3" / "r.json"), "--workers", str(W), "--levels", "L3", "--keys",
                                         ";".join(k.replace("L2|", "L3|").replace("s3|", "s0|") for k in L2_KEYS)], {"R72_PATH": "per_leg"}, 4)),
        "grid": (lambda: tree_probe("grid", [py, "-I", "-B", launch, str(b.S8 / "r67_g1_screen.py"), str(b.WT), str(OUT / "grid" / "r.json"), str(W)],
                                    {"R67_MODE": "screen", "R67_OFFSETS": "0,0.05", "R67_FILTER": "screen|top|0.0|level|FL,screen|top|8.0|level|RR,screen|bottom|0.0|ready|FL,screen|bottom|8.0|ready|RR"}, 4)),
        "soil": (lambda: tree_probe("soil", [py, "-I", "-B", launch, str(b.S9 / "s9_soil_event_screen.py"), str(b.WT), str(OUT / "soil" / "r.json"), str(W)],
                                    {"R426A_SET": "all", "R426A_FILTER": "A|G1|FL|Fs0|two,A|J2|RR|Fs8|two"}, 2)),
        "d8": (lambda: tree_probe("d8", [py, "-I", "-B", str(b.HERE / "acc_d8.py"), str(OUT / "d8" / "r.json"), "--workers", str(W), "--limit", "8"], {}, 8)),
        "crawler": (lambda: tree_probe("crawler", [py, "-I", "-B", str(b.HERE / "acc_crawler.py"), str(OUT / "crawler" / "r.json"), "--workers", str(W), "--limit", "4"], {}, 4)),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    table = probes()
    names = args.only.split(",") if args.only else list(table)
    path = b.HERE / "probe.json"
    done = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    for name in names:
        done[name] = table[name]()
        path.write_text(json.dumps(done, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
