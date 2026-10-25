"""Chrono case folders -> contact episode npz files (spec rev. 39 203 / 205, P-S8-1 / P-S8-2).

Runs in ``Chrono-dev`` (reads the YAML for the controller geometry; no simulation):

    C:\\ProgramData\\miniforge3\\envs\\Chrono-dev\\python.exe -I \\
        04_scripts/05_ml/build_contact_episodes.py <out folder> <case folder> [<case folder> ...]

A case folder holds ``record/record.npz``, ``r8_series.npz``, ``pads.npz``, ``result.json`` and
``controller_events.json`` (bundle C, S7 ctrl3, S8). The file and key knowledge is in
:mod:`outrigger_sim.contact_episode`; the episode is written as ``<out>/<case>.npz`` and a line
with the replayed J_P / J_C event counts is printed, then the episode count per crawler
contact model.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "03_src"))

from outrigger_sim.contact_episode import (  # noqa: E402
    MachineConstants,
    build_episode,
    count_by_crawler_contact,
    save_episode,
)
from outrigger_sim.control.c2 import C2Geometry  # noqa: E402
from outrigger_sim.control.contact_replay import Judge, replay_both  # noqa: E402
from outrigger_sim.params import load_params  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    out = Path(argv[0])
    geometry = C2Geometry.from_params(load_params())
    machine = MachineConstants.from_geometry(geometry)
    metas = []
    for case in argv[1:]:
        case_dir = Path(case)
        episode = build_episode(case_dir, machine,
                                nominal_stiffness_N_m=geometry.load_sensitivity_diag_N_m)
        path = save_episode(episode, out / f"{case_dir.name}.npz")
        replay = replay_both(episode)
        counts = {judge.value: len(replay[judge].events) for judge in Judge}
        print(f"{path.name}: {episode.sample_count} samples, replay events {counts}")
        metas.append(episode.meta)
    print(f"episodes per crawler contact model: {count_by_crawler_contact(metas)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
