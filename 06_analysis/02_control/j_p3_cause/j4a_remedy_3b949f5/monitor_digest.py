"""Digest of the ③ monitor's per-read trace over the T-JR-04 schedules (bit-identity check of a
controller refactor). Usage: python -I -B monitor_digest.py <03_src folder> <tests folder>"""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

source_dir, tests_dir = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(source_dir))

import numpy as np  # noqa: E402


def load(name):
    spec = importlib.util.spec_from_file_location(name, tests_dir / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prop = load("test_jp3_rev5_property")
edition4 = load("test_jp3_edition4")
import outrigger_sim.control.two_pressure as two_pressure  # noqa: E402

assert Path(two_pressure.__file__).resolve().is_relative_to(source_dir.resolve())
digest = hashlib.sha256()


def add(value) -> None:
    digest.update(json.dumps(value, sort_keys=True, default=repr).encode("utf-8"))


rng = np.random.default_rng(20261116)
for sequence in range(150):
    commands, forces = prop._random_schedule(rng)
    for revision, plant in ((5, prop.NEW_PLANT), (4, prop.NEW_PLANT), (4, prop.OLD_PLANT)):
        reads, monitors = [], []
        record = prop._closed_loop(prop.LegPlant(prop.P_EXT_PA, forces[0], **plant), commands,
                                   forces, revision, reads=reads, monitors=monitors)
        add(record)
        add([[float(r[2]), float(r[3]), r[5]] for r in reads])
        add(monitors[0].meta())
for case in (prop._case_5, prop._case_7, prop._case_8):
    start, force, commands, forces = case()
    reads = []
    add(prop._closed_loop(prop.LegPlant(start, force, **prop.NEW_PLANT), commands, forces, 5,
                          reads=reads))
    add([r[5] for r in reads])
run, moves, locks = edition4._carry_ret_ret_lock()
add([*moves, *locks])
add(run.monitor.meta())
print(digest.hexdigest(), two_pressure.__file__)
