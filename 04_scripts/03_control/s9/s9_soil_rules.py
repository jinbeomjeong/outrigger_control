"""S9 C2 soil-response rule candidates (spec rev. 57) as a subclass of the project C2 (no 03_src change).

Rule set "LOC" (lift-off confirmation, rule names of spec 282):
  S-1  load-sum plateau: in LEVEL, before the lift-off is confirmed, a window of consecutive samples in which no
       leg retracted and the mean leg speed was >= ext_min_frac v_max (window_mode "no_retract"; the applied output
       of the period before each sample) and the mean motor stroke advanced >= win_m; the load-sum regression over
       the window rises by <= dF_thr_N over win_m, and the window-mean load sum >= rho W_ref (plausibility).
       -> lift-off confirmed (event crawler_liftoff_confirmed).
  S-2  crawler zone held until confirmed: when the crawler-zone latch would release (slow clearance >= 20 mm) without
       a confirmation, soil mode starts (event soil_mode_start): the zone stays latched and every leg extends at
       >= push_frac v_max (pure heave added), DONE is blocked.
  S-3  clearance bias per crawler corner (bias_mode "corner_imu"): at the window start t_P,
       b_k = c_hat_k(t_P) - (rho_k - min rho), rho_k = y_k d_phi - x_k d_theta (raw-tilt attitude change since the
       crawler settle), clipped at >= 0, used only when max b_k > bias_min_m; afterwards corner k reads c_hat_k - b_k.
  S-4  re-contact watch (optional, recontact_N): after the confirmation, while all legs extend, a load sum below the
       window mean minus recontact_N on 2 samples clears the confirmation (event crawler_recontact) -> S-2 again.
  S-5  limits: soil mode longer than max_push_m of mean extension -> WARN_CRAWLER_LIFTOFF_UNCONFIRMED and FAULT.
Defaults are the spec rev. 57 proposal; every key can be changed per run (dict ``soil_rule``).
Units SI.
"""
from __future__ import annotations

import math
from collections import deque

import numpy as np

DEFAULTS = {
    "win_m": 0.010,          # mean motor-stroke progress of the plateau window [m]
    "ext_min_frac": 0.15,    # every leg extending at >= this x v_max in each window period
    "dF_thr_N": 2000.0,      # max load-sum rise over win_m on the plateau [N] (spec rev. 57; 3 kN passed, 5 kN failed)
    "rho": 0.85,             # plausibility: window-mean load sum >= rho W_ref
    "push_frac": 0.25,       # soil mode: every leg >= this x v_max
    "bias_min_m": 0.020,     # S-3 dead zone [m]
    "recontact_N": None,     # S-4 off by default
    "max_push_m": 0.15,      # S-5 (observed soil-mode push <= 94 mm)
    "max_window_samples": 200,
    "window_mode": "no_retract",  # or "all_extend" (first candidate, fails the rigid-slope identity)
    "bias_mode": "corner_imu",    # or "scalar" (first candidate, over-corrects type A by 20-30 mm)
    "settle_samples": 10,         # periods of raw tilt at the TOUCH start = crawler settle attitude (CHECK in the field)
}


def make_class(c2):
    base = c2.C2Controller
    C2Phase = c2.C2Phase

    class SoilC2(base):
        soil_rule: dict = {}

        # ------------------------------------------------------------------ state
        def reset(self, *a, **kw):
            out = super().reset(*a, **kw)
            self._s9 = {"loc": False, "soil_mode": False, "bias_m": 0.0, "W_hat_N": None, "t_loc": None, "t_P": None,
                        "c_at_P": None, "win": deque(), "e_mode0": None, "low": 0, "n_recontact": 0,
                        "t_soil_mode": None, "log": [], "bias_corner_m": np.zeros(4), "settle_tilts": [],
                        "settle_att": None}
            self._s9_geom_installed = False
            return out

        def _rule(self, key):
            return self.soil_rule.get(key, DEFAULTS[key])

        def soil_meta(self):
            s = self._s9
            return {"loc": s["loc"], "t_loc_s": s["t_loc"], "t_P_s": s["t_P"], "bias_mm": s["bias_m"] * 1e3,
                    "clear_est_at_P_mm": None if s["c_at_P"] is None else s["c_at_P"] * 1e3,
                    "clear_est_at_loc_mm": None if s.get("c_at_loc") is None else s["c_at_loc"] * 1e3,
                    "window_s": s.get("window_s"), "bias_corner_raw_mm": s.get("bias_corner_raw_mm"),
                    "bias_corner_mm": (np.asarray(s["bias_corner_m"]) * 1e3).round(2).tolist(),
                    "settle_att_deg": None if s["settle_att"] is None else np.degrees(s["settle_att"]).tolist(),
                    "W_hat_N": s["W_hat_N"], "soil_mode_entered": s["t_soil_mode"], "n_recontact": s["n_recontact"],
                    "log": s["log"][:20], "rule": {k: self._rule(k) for k in DEFAULTS},
                    "rise_log": s.get("rise_log", [])[:400]}

        # ------------------------------------------------------------------ corrected clearance (S-3)
        def _install_geometry(self):
            if self._s9_geom_installed:
                return
            g = self.geometry
            holder = self._s9

            class SoilGeometry(type(g)):
                def clearance_corners_m(self_g, rod_stroke_m):
                    return super().clearance_corners_m(rod_stroke_m) - holder["bias_corner_m"]

            g2 = SoilGeometry.__new__(SoilGeometry)
            g2.__dict__.update(g.__dict__)
            self.geometry = g2
            self._s9_geom_installed = True

        # ------------------------------------------------------------------ S-1
        def _s9_update_window(self, reading):
            s = self._s9
            if s["loc"]:
                return
            vmax = self.geometry.max_speed_m_s
            applied = np.asarray(self._state.applied_output_m_s, float)
            if self._rule("window_mode") == "all_extend":
                ok = bool(np.all(applied >= self._rule("ext_min_frac") * vmax))
            else:  # "no_retract": every leg >= 0 and the mean >= ext_min_frac v_max
                ok = bool(np.all(applied >= 0.0) and float(np.mean(applied)) >= self._rule("ext_min_frac") * vmax)
            e_mean = float(np.mean(reading.motor_stroke_m))
            F_sum = float(np.sum(reading.cylinder_force_N))
            corners = np.asarray(self.geometry.clearance_corners_m(reading.rod_stroke_m), float).copy()
            c_est = float(corners.min())
            win = s["win"]
            if not ok:
                win.clear()
                return
            win.append((float(reading.t_s), e_mean, F_sum, c_est, corners, self._s9_raw_att()))
            while len(win) > self._rule("max_window_samples"):
                win.popleft()
            w_m = self._rule("win_m")
            # shortest tail of the window that spans w_m
            if win[-1][1] - win[0][1] < w_m:
                return
            k = len(win) - 1
            while k > 0 and win[-1][1] - win[k][1] < w_m:
                k -= 1
            seg = list(win)[k:]
            e = np.array([r[1] for r in seg]); F = np.array([r[2] for r in seg])
            slope = float(np.polyfit(e - e.mean(), F, 1)[0]) if len(seg) >= 3 else (F[-1] - F[0]) / max(e[-1] - e[0], 1e-9)
            rise = slope * w_m
            s.setdefault("rise_log", []).append((round(float(reading.t_s), 2), round(rise, 1),
                                                 round(float(F.mean()), 1)))
            W_ref = self._s9_W_ref()
            if rise <= self._rule("dF_thr_N") and float(F.mean()) >= self._rule("rho") * W_ref:
                s["loc"] = True
                s["t_loc"] = float(reading.t_s)
                s["t_P"] = seg[0][0]
                s["c_at_P"] = seg[0][3]
                s["W_hat_N"] = float(F.mean())
                s["c_at_loc"] = seg[-1][3]
                s["window_s"] = seg[-1][0] - seg[0][0]
                if self._rule("bias_mode") == "corner_imu":
                    bias_c = self._s9_corner_bias(seg[0][4], seg[0][5])
                    s["bias_corner_raw_mm"] = (bias_c * 1e3).round(2).tolist()
                    bias_c = np.maximum(bias_c, 0.0)  # never raise a corner's clearance estimate
                    if float(bias_c.max()) <= self._rule("bias_min_m"):
                        bias_c = np.zeros(4)
                    bias = float(bias_c.max())
                else:
                    bias = seg[0][3] if seg[0][3] > self._rule("bias_min_m") else 0.0
                    bias_c = np.full(4, bias)
                if bias > 0.0:
                    self._install_geometry()
                s["bias_m"] = bias
                s["bias_corner_m"] = bias_c
                if s["soil_mode"]:
                    s["soil_mode"] = False
                s["log"].append((round(float(reading.t_s), 2), "loc", round(rise, 1), round(float(F.mean()), 1),
                                 round(bias * 1e3, 2)))
                self._add_event(reading.t_s, "crawler_liftoff_confirmed")

        def _s9_raw_att(self):
            tilts = self._state.period_raw_tilts
            if not tilts:
                return (self._state.roll_rad, self._state.pitch_rad)
            return (float(np.mean([t.roll_rad for t in tilts])), float(np.mean([t.pitch_rad for t in tilts])))

        def _s9_corner_bias(self, corners_est, att_P):
            """b_k = c_hat_k(t_P) - (rho_k - min rho), rho_k = y_k d_phi - x_k d_theta: the attitude change of the
            body since the crawler settle moves corner k by rho_k; at t_P the last corner has just left the rut."""
            s = self._s9
            att0 = s["settle_att"] if s["settle_att"] is not None else att_P
            d_phi, d_theta = att_P[0] - att0[0], att_P[1] - att0[1]
            xy = self.geometry.crawler_corners_xy_m
            rho = xy[:, 1] * d_phi - xy[:, 0] * d_theta
            return np.asarray(corners_est, float) - (rho - rho.min())

        def _update_attitude_filters(self, measurements):
            super()._update_attitude_filters(measurements)
            s = self._s9
            if s["settle_att"] is None and self._state.phase is C2Phase.TOUCH:
                s["settle_tilts"].append(self._s9_raw_att())
                if len(s["settle_tilts"]) >= self._rule("settle_samples"):
                    s["settle_att"] = tuple(np.mean(s["settle_tilts"], axis=0))

        def _s9_W_ref(self):
            g = self.geometry
            m = g.superstructure_mass_kg or 38400.8
            return m * 9.80665

        # ------------------------------------------------------------------ S-4
        def _s9_recontact(self, reading):
            s = self._s9
            thr = self._rule("recontact_N")
            if thr is None or not s["loc"]:
                return
            vmax = self.geometry.max_speed_m_s
            applied = np.asarray(self._state.applied_output_m_s, float)
            if not np.all(applied >= self._rule("ext_min_frac") * vmax):
                s["low"] = 0
                return
            F_sum = float(np.sum(reading.cylinder_force_N))
            s["low"] = s["low"] + 1 if F_sum < s["W_hat_N"] - thr else 0
            if s["low"] >= 2:
                s["loc"] = False
                s["win"].clear()
                s["n_recontact"] += 1
                s["low"] = 0
                self._add_event(reading.t_s, "crawler_recontact")

        # ------------------------------------------------------------------ hooks into LEVEL
        def _level(self, reading):
            if self._state.phase is C2Phase.LEVEL:
                self._s9_update_window(reading)
                self._s9_recontact(reading)
            return super()._level(reading)

        def _update_crawler_zone(self, reading):
            zone = super()._update_crawler_zone(reading)
            s = self._s9
            if not zone and not s["loc"]:
                if not s["soil_mode"]:
                    s["soil_mode"] = True
                    s["t_soil_mode"] = float(reading.t_s)
                    s["e_mode0"] = float(np.mean(reading.motor_stroke_m))
                    s["log"].append((round(float(reading.t_s), 2), "soil_mode"))
                    self._add_event(reading.t_s, "soil_mode_start")
                self._state.in_crawler_zone = True
                zone = True
            if s["soil_mode"] and not s["loc"]:
                if float(np.mean(reading.motor_stroke_m)) - s["e_mode0"] > self._rule("max_push_m"):
                    self._add_event(reading.t_s, "WARN_CRAWLER_LIFTOFF_UNCONFIRMED", is_warning=True)
                    self._state.phase = C2Phase.FAULT
            return zone

        def _lift_without_retracting(self, leg_speeds):
            s = self._s9
            if s["soil_mode"] and not s["loc"]:
                vmax = self.geometry.max_speed_m_s
                floor = self._rule("push_frac") * vmax
                lifted = leg_speeds + max(0.0, floor - float(leg_speeds.min()))
                return c2.scale_to_speed_limit(lifted, vmax)
            return super()._lift_without_retracting(leg_speeds)

        def _update_completion(self, reading, filtered_clearance_m):
            done = super()._update_completion(reading, filtered_clearance_m)
            if not self._s9["loc"]:
                self._state.complete_since_s = None
                return False
            return done

    return SoilC2
