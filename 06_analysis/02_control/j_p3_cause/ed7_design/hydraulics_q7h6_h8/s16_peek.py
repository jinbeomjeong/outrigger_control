"""Peek one T4h: phase values and FL command/stroke in the first probe window."""
import sys

import numpy as np

with np.load(sys.argv[1], allow_pickle=False) as d:
    t, phase, cmd, s = d["t_s"], d["phase"], d["command_m_s"], d["motor_stroke_m"]
print(sorted(set(phase.tolist())))
idx = np.flatnonzero(phase == phase[np.argmax(t > 30)])[:5]
leg = int(sys.argv[2])
sel = np.flatnonzero((t >= float(sys.argv[3])) & (t <= float(sys.argv[4])))
for k in sel:
    print(f"{t[k]:6.2f} {phase[k]:6s} {cmd[k, leg] * 1e3:8.3f} {s[k, leg] * 1e3:9.3f}")
