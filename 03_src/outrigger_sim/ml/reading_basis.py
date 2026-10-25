"""Reading bases of the miss evaluation: the V15 ratchet correction (spec rev. 52 232, U-S8-51).

In L2b-NSC + seal-friction records the cylinder net reading of a leg whose pad contact force
``N`` is below about 1.5 kN reads 0.43-0.49 kN low (NSC contact chatter ratchets the seal inside
its band, independent of ``F_s``; dynamics 5.29.2). A low reading sees a lift more easily, so it
is optimistic for the miss verdict. A real machine has no such bias.

Bases (each gives a copy of the episode with ``lower_reading_N`` and ``net_force_N`` shifted;
the J_C replay reads ``lower_reading_N``, the ML features are built from it):

* :attr:`ReadingBasis.RAW` - the recorded reading (record row).
* :attr:`ReadingBasis.CORRECTED` - default: ``+0.5 kN`` on the samples whose pad ``N`` at the
  10 Hz sample time (linear interpolation of the 1 ms pad record) is below 1.5 kN.
* :attr:`ReadingBasis.UPPER_BOUND` - sensitivity row: on the lifted samples (``N <= 0``) the net
  reading is set to the upper bound ``F_s,i - m_i g`` (seal sliding at its band end); the
  controller's zero offset and allowance (``net - lower``) are kept. The other ``N < 1.5 kN``
  samples get the ``+0.5 kN`` correction (the bound is undefined while in contact; ASSUMPTION).

``F_s,i`` is the 1 ms pad record's ``F_seal_limit`` at the sample time, so the runs whose meta
lacks ``seal_friction_N`` (MLJ, E / N) are covered too. numpy only.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from outrigger_sim.contact_episode import LEG_COUNT, PADS_FILE, Episode

RATCHET_CONTACT_LIMIT_N = 1500.0
"""Pad contact force below which the reading is corrected (spec 232)."""
RATCHET_CORRECTION_N = 500.0
"""Reading correction (deficit 0.44-0.49 kN, F_s-independent; dynamics 5.29.2)."""
LIFTED_CONTACT_N = 0.0
"""Pad contact force at or below which a leg counts as lifted for the upper bound."""
READING_FIELDS = ("lower_reading_N", "net_force_N")
"""Episode fields that carry the pressure-derived force reading."""


class ReadingBasis(StrEnum):
    """Which reading the judges and the ML features see."""

    RAW = "raw"
    CORRECTED = "corrected"
    UPPER_BOUND = "upper_bound"


class PadRecordError(FileNotFoundError):
    """The 1 ms pad record of an episode cannot be found."""


def pads_path(episode: Episode, project_root: Path) -> Path:
    """``pads.npz`` of the case folder the episode was built from (``meta["source"]``).

    Raises:
        PadRecordError: No source in the meta, or no pad record there.
    """
    source = episode.meta.get("source")
    if not source:
        raise PadRecordError(f"{episode.meta.get('episode_id')}: no source case folder in meta")
    folder = Path(str(source))
    if not folder.is_absolute():
        folder = project_root / folder
    path = folder / PADS_FILE
    if not path.is_file():
        raise PadRecordError(f"{episode.meta.get('episode_id')}: missing {path}")
    return path


def pad_record_at_samples(path: Path, t_s: NDArray[np.float64]
                          ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Pad contact force ``N`` and seal limit ``F_s`` per leg at the sample times (n, 4) each,
    linearly interpolated from the 1 ms pad record."""
    with np.load(path, allow_pickle=False) as pads:
        pad_t_s = np.asarray(pads["t"], dtype=float)
        contact_N = np.asarray(pads["N"], dtype=float)
        seal_limit_N = (np.asarray(pads["F_seal_limit"], dtype=float)
                        if "F_seal_limit" in pads.files else np.zeros_like(contact_N))
    t_s = np.asarray(t_s, dtype=float)
    at_contact = np.empty((t_s.size, LEG_COUNT))
    at_limit = np.empty((t_s.size, LEG_COUNT))
    for leg in range(LEG_COUNT):
        at_contact[:, leg] = np.interp(t_s, pad_t_s, contact_N[:, leg])
        at_limit[:, leg] = np.interp(t_s, pad_t_s, seal_limit_N[:, leg])
    return at_contact, at_limit


def reading_shift_N(
    basis: ReadingBasis,
    contact_N: NDArray[np.float64],
    seal_limit_N: NDArray[np.float64],
    net_force_N: NDArray[np.float64],
    rod_weight_N: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Per sample and leg, the amount added to the reading under ``basis`` (n, 4)."""
    shift = np.zeros(np.shape(contact_N))
    if basis is ReadingBasis.RAW:
        return shift
    is_low_contact = np.nan_to_num(contact_N, nan=np.inf) < RATCHET_CONTACT_LIMIT_N
    shift[is_low_contact] = RATCHET_CORRECTION_N
    if basis is ReadingBasis.UPPER_BOUND:
        is_lifted = np.nan_to_num(contact_N, nan=np.inf) <= LIFTED_CONTACT_N
        upper_bound_N = seal_limit_N - np.asarray(rod_weight_N, dtype=float)[None, :]
        shift[is_lifted] = (upper_bound_N - np.asarray(net_force_N, dtype=float))[is_lifted]
    return shift


def with_reading_basis(
    episode: Episode,
    basis: ReadingBasis,
    contact_N: NDArray[np.float64],
    seal_limit_N: NDArray[np.float64],
) -> Episode:
    """Copy of ``episode`` whose force readings follow ``basis`` (truth and meta unchanged)."""
    if basis is ReadingBasis.RAW:
        return episode
    shift = reading_shift_N(basis, contact_N, seal_limit_N, episode["net_force_N"],
                            episode.rod_weight_N)
    arrays = dict(episode.arrays)
    for name in READING_FIELDS:
        arrays[name] = np.asarray(episode[name], dtype=float) + shift
    return Episode(arrays, {**episode.meta, "reading_basis": str(basis)})


def corrected_sample_count(contact_N: NDArray[np.float64]) -> int:
    """Number of (sample, leg) readings the default correction changes."""
    return int(np.count_nonzero(np.nan_to_num(contact_N, nan=np.inf) < RATCHET_CONTACT_LIMIT_N))
