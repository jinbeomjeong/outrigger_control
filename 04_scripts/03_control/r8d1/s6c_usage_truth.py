"""A1 floor usage from (a) the controller CHECK value, (b) the true crawler attitude, (c) raw-sample mean."""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "03_src"))
from outrigger_sim.control import target as tg  # noqa: E402

batch = Path(sys.argv[1])


def rp_from_quat(q):
    w, x, y, z = q.T
    roll = np.arctan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    pitch = np.arcsin(np.clip(2 * (w * y - z * x), -1, 1))
    return roll, pitch


def raw_tilt(f):
    return np.arctan2(f[..., 1], f[..., 2]), np.arctan2(-f[..., 0], np.hypot(f[..., 1], f[..., 2]))


rows = []
for d in sorted(p for p in batch.iterdir() if (p / "result.json").exists()):
    res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    acc = res.get("acceptance") or {}
    lc = acc.get("last_check")
    if not lc:
        continue
    cm = res["controller_meta"]["target"]
    lim_d = cm["limits_rad"]
    limits = tg.TargetLimits(**{k: v for k, v in lim_d.items()})
    rec = np.load(d / "record" / "record.npz")
    r8 = np.load(d / "r8_series.npz")
    chk = np.where(r8["phase"] == "check")[0]
    if chk.size == 0:
        continue
    end = chk[-1] + 1  # decision period index
    w = slice(end - 9, end + 1)
    roll, pitch = rp_from_quat(rec["body_quat_wxyz"])
    true_c = (float(roll[w].mean()), float(pitch[w].mean()))
    rr, pp = raw_tilt(r8["imu_samples"][w])
    raw_c = (float(np.mean(rr)), float(np.mean(pp)))
    settle = None
    # settle map used by the run: rebuild from the controller default
    from outrigger_sim.control.c2 import C2Config  # noqa: E402
    sm = C2Config().with_10hz_d1().target.settle_map

    def use(c):
        fl = (sm or tg.CrawlerSettleMap.identity()).floor_from_crawler(c)
        return tg.floor_usage(fl, limits)

    ctrl = tuple(lc["crawler_attitude_rad"])
    t_dec = r8["t"][end] if end < len(r8["t"]) else np.nan
    last_move = r8["t"][chk][np.any(r8["issued_u"][chk] != 0, axis=1)]
    rows.append((d.name, res["settings"]["floor"], lc["code"], use(ctrl), use(true_c), use(raw_c),
                 np.degrees(ctrl[1] - true_c[1]), np.degrees(ctrl[0] - true_c[0]),
                 t_dec - (last_move.max() if last_move.size else np.nan), len(chk)))
print(f"{'case':42s} floor     code            u_ctrl  u_true  u_raw   dPitch  dRoll  t_after_move  nchk")
for r in rows:
    print(f"{r[0]:42s} {r[1]:9s} {r[2]:15s} {r[3]:.4f}  {r[4]:.4f}  {r[5]:.4f}  {r[6]:+.3f}  {r[7]:+.3f}  {r[8]:5.2f}  {r[9]}")
