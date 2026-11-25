"""Q7-H1 census: every extension release from a lock in a T4h folder, with or without a stale
retract M2 seed (record-only analysis of judged runs; read only).

Mechanism under test (harness ``harness_hydraulics.HydraulicsPlant``, commit 79495405):
``_step_with_line_fill_gate`` hands every finite ``opening_rod_pressure_Pa`` of the P1 line state
to ``_seed_rod_pressure`` whatever the lock state; the seed is cleared only by
``_start_release``. A retract line that fills while the leg is already moving (a reversal
extension -> retraction without a lock) leaves its seed until the next release, which may be an
extension release seconds later; the M2 lag then starts at the stale retract opening pressure.
Without a seed an extension lag starts at the locked truth and, for a compressive net force, can
only fall (r5 branch (b), r6 keeps it).

Per extension release (lock_events locked -> 0, next read class carry_ext / ext):
  stale      a moving retract opening since the previous release (p1 arrays when present:
             line_dir -1 and is_open with locked 0; else a read pair mv_ext -> mv_ret)
  p_lock     rod truth of the last locked read before the release [bar g]
  p_after    rod truth of the first read after the release [bar g]
  bound      ③ used bound of that read [bar g]
  breach     carry_ext / ext read with p_after > bound + 1 Pa

Run: hydraulics-dev python.exe -I -B h7r3_seed_census.py <out.txt> <t4h dir> [<t4h dir> ...]
     [--glob PATTERN]
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np

BAR = 1.0e5
LEGS = ["FL", "FR", "RL", "RR"]
CARRY_EXT, EXT = 2, 4
MV_EXT, MV_RET = 0, 1


def census(path: Path, out) -> list[dict]:
    d = np.load(path, allow_pickle=False)
    if "jp3_t_s" not in d.files or "lock_events" not in d.files:
        print(f"{path.stem:55s} skipped (no ③ trace or no lock events)", file=out)
        return []
    t = d["t_s"]
    jt = d["jp3_t_s"]
    jidx = {round(v, 4): i for i, v in enumerate(jt)}
    locked = d["locked"]
    has_p1 = "p1_line_dir" in d.files and bool(np.any(d["p1_read_found"]))
    ev = d["lock_events"]
    rows = []
    for leg in range(4):
        rel = [float(e[0]) for e in ev if int(e[1]) == leg and int(e[2]) == 0]
        prev = -1.0e9
        for t_rel in rel:
            after = np.flatnonzero(t >= t_rel - 1e-9)
            before = np.flatnonzero(t < t_rel - 1e-9)
            if after.size == 0 or before.size == 0:
                prev = t_rel
                continue
            ia, ib = int(after[0]), int(before[-1])
            ja = jidx.get(round(float(t[ia]), 4))
            if ja is None:
                prev = t_rel
                continue
            cls = int(d["jp3_class"][ja, leg])
            if cls not in (CARRY_EXT, EXT):
                prev = t_rel
                continue
            window = np.flatnonzero((t > prev) & (t < t_rel - 1e-9))
            stale_t = None
            if has_p1:
                hit = window[(d["p1_line_dir"][window, leg] == -1)
                             & d["p1_is_open"][window, leg] & ~locked[window, leg]]
                if hit.size:
                    stale_t = float(t[hit[0]])
            else:
                st = d["jp3_plant_state"]
                for k in window[1:]:
                    jk = jidx.get(round(float(t[k]), 4))
                    jp = jidx.get(round(float(t[k - 1]), 4))
                    if jk is None or jp is None:
                        continue
                    if st[jp, leg] == MV_EXT and st[jk, leg] == MV_RET:
                        stale_t = float(t[k])
                        break
            p_after = float(d["jp3_p_tr_Pa"][ja, leg]) / BAR
            bound = float(d["jp3_used_bound_Pa"][ja, leg]) / BAR
            row = {"file": path.stem, "leg": LEGS[leg], "t_rel": t_rel,
                   "phase": str(d["phase"][ia]), "stale": stale_t is not None,
                   "stale_t": stale_t, "p_lock": float(d["rod_pressure_Pa"][ib, leg]) / BAR,
                   "p_after": p_after, "bound": bound,
                   "breach": p_after > bound + 1e-5, "has_p1": has_p1}
            rows.append(row)
            print(f"{path.stem:55s} {LEGS[leg]} rel {t_rel:8.3f} {row['phase'][:5]:5s} "
                  f"stale {'Y' if row['stale'] else 'n'} "
                  f"{'' if stale_t is None else f'{stale_t:6.1f}':6s} "
                  f"p_lock {row['p_lock']:6.2f} p_after {p_after:6.2f} bound {bound:6.2f} "
                  f"breach {'Y' if row['breach'] else 'n'}", file=out)
            prev = t_rel
    return rows


def main() -> None:
    args = sys.argv[1:]
    pattern = "*.npz"
    if "--glob" in args:
        k = args.index("--glob")
        pattern = args[k + 1]
        del args[k:k + 2]
    out_path = Path(args[0])
    rows = []
    with open(out_path, "w", encoding="utf-8", newline="\n") as out:
        for folder in args[1:]:
            for path in sorted(Path(folder).glob(pattern)):
                rows += census(path, out)
        table = Counter((r["stale"], r["breach"]) for r in rows)
        probe = Counter((r["stale"], r["breach"]) for r in rows if r["phase"].startswith("probe"))
        rise = [r for r in rows if r["p_after"] > max(r["p_lock"], 5.0) + 0.5]
        rise_stale = sum(1 for r in rise if r["stale"])
        fresh = [r["p_after"] - max(r["p_lock"], 5.0) for r in rows if not r["stale"]]
        stale = [r["p_after"] - max(r["p_lock"], 5.0) for r in rows if r["stale"]]
        lines = [f"extension releases {len(rows)}",
                 f"(stale, breach) counts: {dict(table)}",
                 f"probe phase only: {dict(probe)}",
                 f"releases with p_after > max(p_lock, p_bB 5 bar) + 0.5 bar: {len(rise)}, "
                 f"of them stale {rise_stale}",
                 f"max(p_after - max(p_lock, 5 bar)) no seed {max(fresh, default=float('nan')):.2f}"
                 f" bar, stale seed {max(stale, default=float('nan')):.2f} bar"]
        breach = [r for r in rows if r["breach"]]
        if breach:
            gaps = [r["bound"] - max(r["p_lock"], 5.0) for r in breach]
            seeds = [r["p_after"] for r in breach]
            lines.append(f"breach releases {len(breach)}: bound - max(p_lock, 5 bar) min "
                         f"{min(gaps):.2f} max {max(gaps):.2f} bar (the gap a seed-free lag start "
                         f"would leave); p_after {min(seeds):.2f}-{max(seeds):.2f} bar")
        for line in lines:
            print(line, file=out)
            print(line)
        for r in rise:
            if not r["stale"]:
                line = (f"rise without detected seed: {r['file']} {r['leg']} rel {r['t_rel']:.3f} "
                        f"{r['phase']} p_lock {r['p_lock']:.2f} p_after {r['p_after']:.2f} "
                        f"bound {r['bound']:.2f} has_p1 {r['has_p1']}")
                print(line, file=out)
                print(line)


if __name__ == "__main__":
    main()
