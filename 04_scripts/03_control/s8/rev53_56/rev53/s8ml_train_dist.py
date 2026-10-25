"""Training-distribution check for the gate misses (read only): episode keys, and truth U/L
episodes in the train / validation / test shares by seal friction, depth below F_min and
duration; also how many look like the two misses (F_s,RR >= 5.5 kN, U only, depth <= 3 kN,
duration <= 0.5 s)."""
import os
import sys
from pathlib import Path

os.environ.setdefault("MKL_THREADING_LAYER", "TBB")
# --- paths (migrated from the session scratchpad 2026-10-25; repository-relative) ---
import os as _os
from pathlib import Path as _Path
REPO = _Path(__file__).resolve().parents[5]  # 04_scripts/03_control/s8/rev53_56/<rev>/ -> repo root
# ---
ROOT = REPO
sys.path.insert(0, str(ROOT / "03_src"))

import numpy as np  # noqa: E402

from outrigger_sim.contact_episode import load_episode  # noqa: E402
from outrigger_sim.ml.dataset import liftoff_transient_rows  # noqa: E402
from outrigger_sim.ml.reading_basis import pad_record_at_samples, pads_path  # noqa: E402
from outrigger_sim.ml.split import SPLIT_SEED, split_by_base  # noqa: E402
from outrigger_sim.verify.contact_metrics import ContactClass, contact_episodes, truth_classes  # noqa: E402

RUN = ROOT / r"07_results\S8\ml_main_20261025_090131"
paths = sorted((RUN / "ml_dataset").glob("*.npz"))
first = load_episode(paths[0])
print("episode keys:", sorted(first.keys()) if hasattr(first, "keys") else "n/a")
print("meta keys:", sorted(first.meta))
episodes = [load_episode(p) for p in paths]
split = split_by_base([e.meta for e in episodes], seed=SPLIT_SEED)
share_of = {}
for name in ("train", "validation", "test", "ood_level", "ood_roll"):
    for i in getattr(split, name):
        share_of[i] = name
rows = []
for i, ep in enumerate(episodes):
    try:
        _, seal = pad_record_at_samples(pads_path(ep, ROOT), ep["t_s"])
    except Exception:  # noqa: BLE001
        seal = None
    cls = truth_classes(ep["true_force_min_N"], ep.rod_weight_N, ep.F_min_N)
    lifted = np.asarray(ep["is_lifted"], bool)
    trans = liftoff_transient_rows(ep)
    cls = np.where((lifted & ~trans)[:, None], cls, ContactClass.UNKNOWN)
    t = np.asarray(ep["t_s"], float)
    tfm = np.asarray(ep["true_force_min_N"], float)
    try:
        events = contact_episodes(cls)
    except Exception as exc:  # noqa: BLE001
        print("contact_episodes failed", exc)
        raise
    for ev in events:
        leg = ev.leg
        on, off = ev.on_row, getattr(ev, "off_row", ev.on_row)
        fs = float(np.nanmedian(seal[:, leg])) if seal is not None else np.nan
        depth = ep.F_min_N - float(np.nanmin(tfm[on:off + 1, leg]))
        rows.append((share_of.get(i, "?"), leg, fs, depth, t[off] - t[on] + 0.1,
                     bool(getattr(ev, "is_lift", False)), str(ep.meta.get("episode_id"))))
arr = rows
print("total events", len(arr))
for share in ("train", "validation", "test", "ood_level", "ood_roll"):
    sub = [r for r in arr if r[0] == share]
    hi = [r for r in sub if r[2] >= 5.5e3]
    like = [r for r in hi if not r[5] and r[3] <= 3e3 and r[4] <= 0.6]
    like_rr = [r for r in like if r[1] == 3]
    print(f"{share:10s} events {len(sub):4d}  F_s,leg>=5.5kN {len(hi):4d}  "
          f"of which U-only depth<=3kN dur<=0.6s {len(like):3d} (RR {len(like_rr)})")
    if share == "train":
        bins = [0, 2e3, 4e3, 5.5e3, 7e3, 1e4]
        h = np.histogram([r[2] for r in sub], bins=bins)[0]
        print("   train events per F_s,leg bin [0,2,4,5.5,7,10] kN:", h.tolist())
        print("   train U-only events:", sum(1 for r in sub if not r[5]),
              " lift events:", sum(1 for r in sub if r[5]))
