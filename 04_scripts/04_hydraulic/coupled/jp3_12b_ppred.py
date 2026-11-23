"""436.9 edition 6 T-JR-12b: P-pred input statistics and the posterior-predictive k_allow.

``jp3_remedy_spec_v6.md`` 6.4 (revision 9, G-2 / G-3 / G-4; user decisions 2026-11-23 /
2026-11-24, b4 case B of stats ``ed6_design/stats_v6/s71_ppred_rev9.py``). A calculation
module with its tests (spec 8 Y-10 / Y-11); wiring it into ``jp3_12b_judge.py decide`` is the
tool commit after the seal.

Input statistics (:func:`input_statistics`) from the VBKL0 lines of the base blocks b1 and b2,
each line classified on its own by ``jp3_12b_judge.classify_line`` (erratum 1 / 8 order):

* kept lines: "opportunity" and "VBKL0 READY not reached"; "no trigger" and "pre-trigger
  fallback" lines are left out (they never enter n23); a "not latched" line is a setting defect
  (:class:`InputStop`), so no input comes from it;
* ``s_ij`` = 1 for a kept line that did not reach READY;
* per cell c in {tau_C, tau_R} (the case's cell phase of ``selection.json``): ``K_c`` stalled
  kept lines and ``N_c`` kept lines;
* per case: ``n_i`` kept lines (0 .. 2) and ``k_i = sum_j s_ij``;
* ``a30`` / ``n_both``: cases whose two lines are both kept and both reached READY, and of them
  those whose first-READY difference, rounded to 1e-6 s, is above 30 s.

b4 (G-2, case B, :func:`b4_input`): the VBKL0 b4 lines (phase TRw, one per case) form their own
cell TRw: ``K_TRw`` stalled and ``N_TRw`` kept b4 lines (same classification), and every b4
opportunity line joins the replay.

P-pred (:func:`k_allow_pred`; per parameter draw, in this generator order, as stats
``s71_ppred_rev9.inner``, which equals ``s70_12b_kallow.inner_pred`` without b4):

1. ``p_c ~ Beta(K_c + 0.5, N_c - K_c + 0.5)`` for tau_C, tau_R (Jeffreys);
2. ``r2 = 0.5 Beta(a30 + 0.5, max(n_both, 1) - a30 + 0.5)``;
3. ``rho``: pooled method-of-moments on a within-cell case bootstrap of the ``n_i`` = 2 cases,
   clipped to [0, 0.95] (0 when the mean is 0 or 1, or fewer than 2 cases);
4. with b4: ``p_TRw ~ Beta(K_TRw + 0.5, N_TRw - K_TRw + 0.5)``, and for a reached b4 line its
   own posterior ``p_TRw a / (a + 1)``, ``a = 1/rho - 1`` (``p_TRw`` when rho is 0);
5. ``n_rep`` replays: a b1 / b2 opportunity line stalls with ``pi_i = (alpha_c + k_i) /
   (alpha_c + beta_c + n_i)``, ``alpha_c = p_c a``, ``beta_c = (1 - p_c) a`` (``p_c`` when rho is
   0), a b4 opportunity line with step 4's value; a line that does not stall exceeds 30 s with
   ``r2``; n23 = the count (c = 1).

``k_allow`` = the smallest k with P(n23 > k) <= alpha (0.10), from ``n_par`` 20000 x
``n_rep`` 10 draws of ``numpy.random.default_rng(seed)`` (seed 20261125, user decisions
2026-11-24); the b1 / b2 decision and the b4 recalculation each start a new generator with
that seed.

The decision record (:func:`decision_record`): ``K_c``, ``N_c``, ``a30``, ``n_both``, per case
``(k_i, n_i)``, ``K_TRw`` / ``N_TRw`` (b4), the blocks used, the P-pred seed, ``k_allow``,
P(n23 > k) and P(n23 > k - 1), plus the left-out line counts.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import jp3_12b_judge as judge  # noqa: E402

ALPHA = 0.10
N_PAR = 20000
N_REP = 10
"""Spec 6.4 draw counts (user decision 2026-11-24, stats `s41_keys_review`: with 20000 x 10
the edition 5 data give k_allow 10 on every one of ten seeds; 1000 x 20 gave 9 or 10)."""
P_PRED_SEED = 20261125
"""Spec 6.4 P-pred seed (user decision 2026-11-24; the seal writes it into the spec)."""
READY_LIMIT_S = judge.READY_LIMIT_S
READY_ROUND_DIGITS = judge.READY_ROUND_DIGITS
RHO_MAX = 0.95
JEFFREYS = 0.5
BASE_BLOCKS = ("b1", "b2")
B4_BLOCK = "b4"
CELLS = ("tau_C", "tau_R")
"""The cells of the base blocks (``selection.json`` cell phases)."""
K_SEARCH_MAX = 200
LEFT_OUT = (judge.NO_TRIGGER, judge.PRE_FALLBACK)


class InputStop(Exception):
    """A line the input statistics cannot take (a setting defect, the run stops)."""


@dataclass
class CaseInput:
    """One case of the base blocks."""

    case: str
    cell: str
    stalls: list[int] = field(default_factory=list)
    """``s_ij`` of the kept lines, in block order."""
    ready_s: list[float | None] = field(default_factory=list)

    @property
    def n(self) -> int:
        return len(self.stalls)

    @property
    def k(self) -> int:
        return int(sum(self.stalls))


@dataclass
class InputStatistics:
    """Spec 6.4 G-4 inputs of b1 and b2 (cases in cell-table order)."""

    cases: dict[str, CaseInput]
    left_out: dict[str, int]

    def K(self, cell: str) -> int:  # noqa: N802 (the spec's symbol)
        return sum(case.k for case in self.cases.values() if case.cell == cell)

    def N(self, cell: str) -> int:  # noqa: N802 (the spec's symbol)
        return sum(case.n for case in self.cases.values() if case.cell == cell)

    @property
    def both_reached(self) -> list[CaseInput]:
        return [case for case in self.cases.values()
                if case.n == 2 and case.k == 0 and None not in case.ready_s]

    @property
    def n_both(self) -> int:
        return len(self.both_reached)

    @property
    def a30(self) -> int:
        return sum(round(abs(case.ready_s[0] - case.ready_s[1]), READY_ROUND_DIGITS)
                   > READY_LIMIT_S for case in self.both_reached)


@dataclass(frozen=True)
class B4Input:
    """The VBKL0 b4 lines as their own cell TRw (G-2 case B)."""

    stalled: int
    """``K_TRw``: kept b4 lines that did not reach READY."""
    kept: int
    """``N_TRw``: kept b4 lines."""
    opportunities: int
    left_out: dict[str, int]


def _line_category(block: str, key: str, line: judge.Line) -> str:
    category = judge.classify_line(line)
    if category == judge.UNLATCHED:
        raise InputStop(f"{block} {key}: not latched (setting defect, 6.4 G-4)")
    return category


def cell_of_case(selection: dict) -> dict[str, str]:
    """Case -> cell phase (tau_C / tau_R) of the selection's cell table."""
    return {row["case"]: row["phase"] for row in selection["cell_table"]}


def input_statistics(selection: dict, blocks: dict[str, dict[str, judge.Line]]
                     ) -> InputStatistics:
    """Spec 6.4 G-4 from the VBKL0 lines of b1 and b2 (module docstring).

    Args:
        selection: The ``selection.json`` document (cell table).
        blocks: ``{block: {key: Line}}`` of the VBKL0 arm (b1, b2; other blocks are ignored).

    Raises:
        InputStop: A base block is missing, or a "not latched" line.
    """
    missing = [block for block in BASE_BLOCKS if block not in blocks]
    if missing:
        raise InputStop(f"blocks {missing} missing")
    cases = {case: CaseInput(case, cell) for case, cell in cell_of_case(selection).items()}
    left_out = dict.fromkeys(LEFT_OUT, 0)
    for block in BASE_BLOCKS:
        for key, line in blocks[block].items():
            category = _line_category(block, key, line)
            if category in LEFT_OUT:
                left_out[category] += 1
                continue
            case = cases[judge.case_of(key)]
            case.stalls.append(int(category == judge.VBK0_NOT_READY))
            case.ready_s.append(judge.ready_time(line.row))
    return InputStatistics(cases, left_out)


def b4_input(lines: dict[str, judge.Line]) -> B4Input:
    """``K_TRw``, ``N_TRw`` and the opportunity count of the VBKL0 b4 lines.

    Raises:
        InputStop: A "not latched" b4 line.
    """
    counts = dict.fromkeys((*LEFT_OUT, judge.OPPORTUNITY, judge.VBK0_NOT_READY), 0)
    for key, line in lines.items():
        counts[_line_category(B4_BLOCK, key, line)] += 1
    stalled, reached = counts[judge.VBK0_NOT_READY], counts[judge.OPPORTUNITY]
    return B4Input(stalled, stalled + reached, reached,
                   {category: counts[category] for category in LEFT_OUT})


def _rho_bootstrap(rng: np.random.Generator, pair_k: list[np.ndarray]) -> float:
    """Pooled method-of-moments rho on a within-cell case bootstrap of the n_i = 2 cases."""
    resampled = [rng.choice(values, values.size) for values in pair_k if values.size]
    k = np.concatenate(resampled).astype(float) if resampled else np.zeros(0)
    pbar = k.mean() / 2.0 if k.size else 0.0
    if pbar <= 0.0 or pbar >= 1.0 or k.size < 2:
        return 0.0
    return float(np.clip(k.var(ddof=1) / (2.0 * pbar * (1.0 - pbar)) - 1.0, 0.0, RHO_MAX))


@dataclass(frozen=True)
class _ReplayCases:
    """The b1 / b2 opportunity lines as arrays (one entry per line, case-major)."""

    is_tau_c: np.ndarray
    k: np.ndarray
    n: np.ndarray


def _replay_cases(stats: InputStatistics) -> _ReplayCases:
    is_tau_c, k, n = [], [], []
    for case in stats.cases.values():
        for stall in case.stalls:
            if stall == 0:
                is_tau_c.append(case.cell == CELLS[0])
                k.append(case.k)
                n.append(case.n)
    return _ReplayCases(np.array(is_tau_c, bool), np.array(k, float), np.array(n, float))


def _line_probabilities(replay: _ReplayCases, p_tau_c: float, p_tau_r: float,
                        rho: float) -> np.ndarray:
    p_cell = np.where(replay.is_tau_c, p_tau_c, p_tau_r)
    if rho <= 0.0:
        return p_cell
    a = 1.0 / rho - 1.0
    return (p_cell * a + replay.k) / (a + replay.n)


def n23_draws(rng: np.random.Generator, stats: InputStatistics, b4: B4Input | None = None,
              n_par: int = N_PAR, n_rep: int = N_REP) -> np.ndarray:
    """``n_par * n_rep`` draws of the c = 1 null n23 (module docstring, steps 1 .. 5)."""
    replay = _replay_cases(stats)
    pair_k = [np.array([case.k for case in stats.cases.values()
                        if case.cell == cell and case.n == 2], int) for cell in CELLS]
    stalled = [stats.K(cell) for cell in CELLS]
    kept = [stats.N(cell) for cell in CELLS]
    a30, n_both = stats.a30, stats.n_both
    draws = []
    for _ in range(n_par):
        p = [float(rng.beta(k + JEFFREYS, n - k + JEFFREYS))
             for k, n in zip(stalled, kept, strict=True)]
        r2 = float(0.5 * rng.beta(a30 + JEFFREYS, max(n_both, 1) - a30 + JEFFREYS))
        rho = _rho_bootstrap(rng, pair_k)
        probabilities = [_line_probabilities(replay, p[0], p[1], rho)]
        if b4 is not None:
            p_trw = float(rng.beta(b4.stalled + JEFFREYS, b4.kept - b4.stalled + JEFFREYS))
            if rho > 0.0:
                a = 1.0 / rho - 1.0
                p_trw *= a / (a + 1.0)
            probabilities.append(np.full(b4.opportunities, p_trw))
        line_p = np.concatenate(probabilities)
        stall = rng.random((n_rep, line_p.size)) < line_p
        late = (~stall) & (rng.random((n_rep, line_p.size)) < r2)
        draws.append((stall | late).sum(axis=1))
    return np.concatenate(draws)


def pick(draws: np.ndarray, alpha: float = ALPHA) -> int:
    """The smallest k with P(n23 > k) <= alpha (stats ``pick``)."""
    for k in range(K_SEARCH_MAX + 1):
        if (draws > k).mean() <= alpha:
            return k
    return K_SEARCH_MAX


def k_allow_pred(stats: InputStatistics, b4: B4Input | None = None, *,
                 seed: int = P_PRED_SEED, alpha: float = ALPHA, n_par: int = N_PAR,
                 n_rep: int = N_REP) -> dict:
    """``k_allow`` with a new ``numpy.random.default_rng(seed)`` (b1 / b2, or b1 / b2 / b4)."""
    draws = n23_draws(np.random.default_rng(seed), stats, b4, n_par, n_rep)
    k = pick(draws, alpha)
    replay_lines = _replay_cases(stats).k.size + (0 if b4 is None else b4.opportunities)
    return {"k_allow": k, "p_n23_gt_k": float((draws > k).mean()),
            "p_n23_gt_k_minus_1": float((draws > k - 1).mean()),
            "replay_lines": int(replay_lines), "alpha": alpha, "n_par": n_par,
            "n_rep": n_rep, "seed": seed}


def decision_record(stats: InputStatistics, result: dict, b4: B4Input | None = None) -> dict:
    """Spec 6.4 G-3 with the b4 case B counts: what the decision record keeps."""
    record = {"K_c": {cell: stats.K(cell) for cell in CELLS},
              "N_c": {cell: stats.N(cell) for cell in CELLS},
              "a30": stats.a30, "n_both": stats.n_both,
              "cases": {case.case: {"k": case.k, "n": case.n} for case in stats.cases.values()},
              "left_out_lines": dict(stats.left_out),
              "blocks_used": [*BASE_BLOCKS, *([B4_BLOCK] if b4 is not None else [])],
              "p_pred_seed": result["seed"], "k_allow": result["k_allow"],
              "p_n23_gt_k": result["p_n23_gt_k"],
              "p_n23_gt_k_minus_1": result["p_n23_gt_k_minus_1"],
              "alpha": result["alpha"], "n_par": result["n_par"], "n_rep": result["n_rep"],
              "replay_lines": result["replay_lines"]}
    if b4 is not None:
        record["b4"] = {"K_TRw": b4.stalled, "N_TRw": b4.kept,
                        "opportunities": b4.opportunities, "left_out_lines": dict(b4.left_out)}
    return record
