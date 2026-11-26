"""S8-R design, part 5: expected G' stratum sizes under the proposed slot design (assumption model).

Slots (one condition per slot, stored-V0 clean clusters only = 171 of 192):
  (a) phase  : 171 clusters x one phase from O' = {0.0125, 0.0375, 0.0625, 0.0875}
  (b) depth  : 48 clean RE1bF clusters x one (shape, phase), shape in {25/0.05, 30/0.04}, phase in O' + old 4
  (c) F_s    : 40 clean families x {1, 3, 6} kN, one phase in O' + old 4
P(E | slot) [assumption]: only the 8 bottom-front RE1bF/FS24 families can be E (s8r_frame).
  RE1bF: interval model of dynamics 4.3 (phi 0.0125 -> 0.5, 0.0375 -> 0, 0.0625 -> 1, 0.0875 -> 1) and
         stored V0 rates at old phases (o0.0 15/16, o0.025 0/8, o0.05 4/16, o0.075 8/8).
  FS24 : stored V0 at old phases (o0.05 16/16, else ~0); new phases q_fs (sensitivity 0, 0.125, 0.25).
  depth/F_s change the window: E probability multiplied by m_shift (sensitivity 1.0, 0.7).
Usage: python -I -B s8r_sizes.py <out_folder>
"""
import json
import sys
from pathlib import Path

import numpy as np

OUT = Path(sys.argv[1])
rng = np.random.default_rng(20261114)
REPS = 20000
NEW = [0.0125, 0.0375, 0.0625, 0.0875]
OLD = [0.0, 0.025, 0.05, 0.075]
P_RE_NEW = {0.0125: 0.5, 0.0375: 0.0, 0.0625: 1.0, 0.0875: 1.0}
P_RE_OLD = {0.0: 15 / 16, 0.025: 0.0, 0.05: 4 / 16, 0.075: 1.0}
P_FS_OLD = {0.0: 0.0, 0.025: 0.0, 0.05: 1.0, 0.075: 0.0}
N_CLEAN, N_RE1_CLEAN, N_FAM_CLEAN = 171, 48, 40
E_FAMS = [("RE1bF", t, leg) for t in ("level", "ready") for leg in ("FL", "FR")] + \
         [("FS24", t, leg) for t in ("level", "ready") for leg in ("FL", "FR")]
out = {"assumptions": __doc__, "cases": []}
txt = []
for q_fs in [0.0, 0.125, 0.25]:
    for m_shift in [1.0, 0.7]:
        nE = np.zeros(REPS, int)
        cov = np.zeros((REPS, 4), int)  # E units in each RE1bF E family
        for rep in range(REPS):
            e_count = 0
            fam_e = np.zeros(8, int)
            # (a) phase source: 4 Fs clusters per E family
            for fi, (ev, _, _) in enumerate(E_FAMS):
                for _ in range(4):
                    phi = NEW[rng.integers(4)]
                    p = P_RE_NEW[phi] if ev == "RE1bF" else q_fs
                    if rng.random() < p:
                        fam_e[fi] += 1
            # (b) depth source: RE1bF E families, 4 clusters each
            for fi, (ev, _, _) in enumerate(E_FAMS):
                if ev != "RE1bF":
                    continue
                for _ in range(4):
                    allp = NEW + OLD
                    phi = allp[rng.integers(8)]
                    p = (P_RE_NEW.get(phi) if phi in P_RE_NEW else P_RE_OLD[phi]) * m_shift
                    if rng.random() < p:
                        fam_e[fi] += 1
            # (c) F_s source: 3 new Fs per E family
            for fi, (ev, _, _) in enumerate(E_FAMS):
                for _ in range(3):
                    allp = NEW + OLD
                    phi = allp[rng.integers(8)]
                    if ev == "RE1bF":
                        p = P_RE_NEW.get(phi, P_RE_OLD.get(phi))
                    else:
                        p = q_fs if phi in P_RE_NEW else P_FS_OLD[phi]
                    if rng.random() < p * m_shift:
                        fam_e[fi] += 1
            nE[rep] = fam_e.sum()
            cov[rep] = fam_e[:4]
        total = N_CLEAN + N_RE1_CLEAN + 3 * N_FAM_CLEAN
        case = {"q_fs": q_fs, "m_shift": m_shift, "slots_total": total,
                "nE_mean": float(nE.mean()), "nE_p05": int(np.percentile(nE, 5)),
                "nE_p95": int(np.percentile(nE, 95)), "P_nE_lt_24": float((nE < 24).mean()),
                "P_nE_lt_20": float((nE < 20).mean()),
                "P_all4_RE1bF_fams_ge3": float((cov >= 3).all(1).mean()),
                "nN_mean": float(total - nE.mean())}
        out["cases"].append(case)
        txt.append(f"q_fs {q_fs} m_shift {m_shift}: slots {total}, nE mean {case['nE_mean']:.1f} "
                   f"(5-95 % {case['nE_p05']}-{case['nE_p95']}), P(nE<24) {case['P_nE_lt_24']:.3f}, "
                   f"P(nE<20) {case['P_nE_lt_20']:.3f}, P(all 4 RE1bF E families >= 3) "
                   f"{case['P_all4_RE1bF_fams_ge3']:.3f}, nN ~{case['nN_mean']:.0f}")
# phase source only (one phase per cluster), for the question "does the phase source alone reach n_min"
nE_a = []
for rep in range(REPS):
    c = 0
    for ev, _, _ in E_FAMS:
        for _ in range(4):
            phi = NEW[rng.integers(4)]
            c += rng.random() < (P_RE_NEW[phi] if ev == "RE1bF" else 0.125)
    nE_a.append(c)
nE_a = np.array(nE_a)
out["phase_only"] = {"nE_mean": float(nE_a.mean()), "nE_p95": int(np.percentile(nE_a, 95)),
                     "nN_mean": float(N_CLEAN - nE_a.mean()),
                     "nE_all_4_phases_RE1bF_max": 16 * 2.5, "note": "all 4 new phases of 16 RE1bF E clusters: 2-3 E each"}
txt.append(f"phase source only (1 phase/cluster): nE mean {nE_a.mean():.1f} (95 % {np.percentile(nE_a, 95):.0f}), "
           f"nN ~{N_CLEAN - nE_a.mean():.0f}; all 4 phases of the 16 RE1bF E clusters -> E 32-48 (2-3 per cluster)")
(OUT / "s8r_sizes.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
(OUT / "s8r_sizes.txt").write_text("\n".join(txt), encoding="utf-8")
print(json.dumps({"status": "ok"}))
