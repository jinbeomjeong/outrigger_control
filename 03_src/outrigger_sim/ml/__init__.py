"""Ground-contact ML/DL comparison candidates (spec ``s6_control_spec.md`` rev. 39 205, P-S8-2).

The ML judge is a comparison candidate to the physics combined judge J_C, never a controller
input without a shadow run and a user decision (205).

* ``dataset`` - episode npz -> causal per-leg windows (205.2), labels (205.1), weights (numpy).
* ``split`` - base-run split 70 / 15 / 15, stratified, plus the out-of-distribution sets (205.5).
* ``models`` - LightGBM baseline and a GRU network (torch), ONNX export (needs the ML env).
* ``evaluate`` - ML flags -> the 203.3 metrics, ECE, ONNX latency, the 205.6 verdict rows.
* ``synthetic`` - synthetic episodes in the episode schema for an end-to-end smoke run only.

Data come from the Chrono environment as episode npz (:mod:`outrigger_sim.contact_episode`);
training runs in ``pytorch_214_cuda_python_313`` (Python 3.13) in a separate process (205.4).
"""
