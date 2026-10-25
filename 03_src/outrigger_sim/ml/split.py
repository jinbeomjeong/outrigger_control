"""Train / validation / test split by base run (spec 205.5).

Every episode branched from one base run goes to the same share, so the test share holds base
runs the models never saw. Shares are 70 / 15 / 15, stratified by the front-leg seal friction bin
(0-2, 2-4, 4-6, 6-8 kN) and the auger level. Out-of-distribution sets are taken out of the
pool first: OOD-1 = every middle-auger base, OOD-2 = bases with ``|floor roll| > 4.4 deg``.
The seed is fixed and returned with the split (205.5).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

SHARES = (0.70, 0.15, 0.15)
FRICTION_BINS_KN = (2.0, 4.0, 6.0)
"""Upper edges of the first three friction bins; the last bin is open."""
OOD_LEVEL = "middle"
OOD_ROLL_LIMIT_DEG = 4.4
SPLIT_SEED = 20261024


@dataclass(frozen=True)
class Split:
    """Episode indices per share."""

    train: tuple[int, ...]
    validation: tuple[int, ...]
    test: tuple[int, ...]
    ood_level: tuple[int, ...]
    ood_roll: tuple[int, ...]
    seed: int

    def to_dict(self) -> dict[str, Any]:
        return {name: list(getattr(self, name)) if name != "seed" else self.seed
                for name in self.__dataclass_fields__}


def _stratum(meta: Mapping[str, Any]) -> tuple[int, str]:
    friction = meta.get("seal_friction_N") or [0.0]
    friction_kN = float(np.asarray(friction, dtype=float)[0]) / 1e3
    friction_bin = int(np.searchsorted(FRICTION_BINS_KN, friction_kN, side="right"))
    return friction_bin, str(meta.get("level"))


def _is_ood_roll(meta: Mapping[str, Any]) -> bool:
    roll = meta.get("floor_roll_deg")
    return roll is not None and abs(float(roll)) > OOD_ROLL_LIMIT_DEG


def _allocate(ordered_bases: list[str]) -> list[list[str]]:
    """Walk the stratum-ordered bases and give each to the share furthest below its target.

    This spreads every stratum over the three shares even when a stratum has one or two bases
    (rounding per stratum would put all of them in the training share).
    """
    shares: list[list[str]] = [[] for _ in SHARES]
    for position, base in enumerate(ordered_bases, start=1):
        deficits = [target * position - len(share) for target, share in zip(SHARES, shares,
                                                                               strict=True)]
        shares[int(np.argmax(deficits))].append(base)
    return shares


def split_by_base(metas: Sequence[Mapping[str, Any]], seed: int = SPLIT_SEED) -> Split:
    """Split episodes (given by their meta) by ``meta['base_id']``.

    Args:
        metas: Episode meta dicts (``base_id``, ``level``, ``seal_friction_N``,
            ``floor_roll_deg``).
        seed: Shuffle seed.
    """
    bases: dict[str, list[int]] = defaultdict(list)
    for index, meta in enumerate(metas):
        bases[str(meta.get("base_id"))].append(index)
    base_meta = {base: metas[indices[0]] for base, indices in bases.items()}
    ood_level = sorted(b for b, m in base_meta.items() if str(m.get("level")) == OOD_LEVEL)
    ood_roll = sorted(
        b for b, m in base_meta.items() if _is_ood_roll(m) and b not in ood_level
    )
    pool = [b for b in sorted(bases) if b not in ood_level and b not in ood_roll]
    strata: dict[tuple[int, str], list[str]] = defaultdict(list)
    for base in pool:
        strata[_stratum(base_meta[base])].append(base)
    rng = np.random.default_rng(seed)
    ordered: list[str] = []
    for key in sorted(strata):
        members = list(strata[key])
        rng.shuffle(members)
        ordered += members
    shares = _allocate(ordered)

    def episodes_of(base_ids: list[str]) -> tuple[int, ...]:
        return tuple(sorted(i for base in base_ids for i in bases[base]))

    train, validation, test = (episodes_of(share) for share in shares)
    return Split(train, validation, test, episodes_of(ood_level), episodes_of(ood_roll), seed)
