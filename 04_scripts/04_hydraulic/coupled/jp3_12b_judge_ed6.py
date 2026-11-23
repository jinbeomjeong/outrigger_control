"""436.9 edition 6 T-JR-12b judge (``jp3_remedy_spec_v6.md`` 4 step 4a, 6.4; 8 Y-10 / Y-5):
the edition 5 tool ``jp3_12b_judge.py`` with the edition 6 rules.

The sub-commands and their arguments, exit codes and outputs are those of ``jp3_12b_judge.py``
(``decide``, ``judge``, ``grade-judge``, ``l1-overlap``); while one runs, the edition 6 rules
replace the edition 5 ones (:func:`edition_6`):

* arms VBKL0 (``--vbk0``) and VBKL (``--vbk``); L1 references VBL0 / VBL;
* ``decide``: ``allow_k`` is the P-pred value (``jp3_12b_ppred.py``: n_par 20000 x n_rep 10,
  ``numpy.random.default_rng(20261125)``, b4 case B) of the used blocks - never the edition 5
  fixed 7 / 9 (6.4); the record ``p_pred`` keeps K_c, N_c, a30, n_both, (k_i, n_i), the blocks,
  K_TRw / N_TRw with b4, the seed, k_allow, P(n23 > k) and P(n23 > k - 1). Edition 6 has no
  fixed VBKL0 input values (the edition 5 erratum 8 8-1.3 ones belong to VBK0), so
  ``--expect-vbk0-*`` is not read. A VBKL0 line whose ``lsb_components`` / ``lsb_settings`` /
  tag is not the sealed ③-off identity (6.1 item 5) is a setting defect;
* ``judge``: the decision's ``allow_k`` must be the P-pred value recomputed from the same VBKL0
  b1 / b2 (/ b4) lines (not judgeable else); every VBKL line has the 6.1 ③-on identity (tag
  ``final_C4G2_P3W_LAS_K1_LSB``, revision 6 keys, ``lsb_components``, ``lsb_settings``); the
  tau_R trigger phase is recorded over the opportunity pairs (``tau_r_trigger_phase``) and over
  every tau_R pair with a trigger (``tau_r_trigger_phase_all``, the 6.3.3 wording).

Usage (dynamics-dev, the code checkout root): as ``jp3_12b_judge.py``, e.g.
  python -I -B 04_scripts/04_hydraulic/coupled/jp3_12b_judge_ed6.py decide --selection <x11>
      --selection-sha256 <sha> --vbk0 b1=<VBKL0_b1.json> --vbk0-t4h b1=<folder> ... --out <rec>
"""
from __future__ import annotations

import contextlib
import functools
import sys
from collections.abc import Iterator
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import jp3_12b_judge as judge  # noqa: E402
import jp3_12b_ppred as ppred  # noqa: E402

SETTING_OF_ARM = {"vbk0": "VBKL0", "vbk": "VBKL"}
L1_SETTING_OF_ARM = {"vbk0": "VBL0", "vbk": "VBL"}
RULE = "jp3_remedy_spec_v6.md 6.4 (edition 6 T-JR-12b, P-pred)"


def p_pred_decision(selection: dict, blocks: dict, used: list[str]) -> dict:
    """The P-pred allowance and its decision record of the used VBKL0 blocks (6.4)."""
    stats = ppred.input_statistics(selection, blocks)
    b4 = ppred.b4_input(blocks["b4"]) if "b4" in used else None
    result = ppred.k_allow_pred(stats, b4)
    return ppred.decision_record(stats, result, b4)


@functools.cache
def _sealed_settings() -> dict:
    import jp3_ed6_judge as ed6

    return ed6.sealed_lsb_settings()


def _vbkl0_identity_problems(blocks: dict) -> list[str]:
    import jp3_ed6_judge as ed6

    expected = _sealed_settings()
    return [f"VBKL0 {key}: {problem}" for lines in blocks.values() for key, line in lines.items()
            for problem in ed6.ed6_identity_problems(line.row, expected, p3_on=False)]


def _decide(original):
    def decide(selection: dict, blocks: dict) -> dict:
        problems = _vbkl0_identity_problems(blocks)
        if problems:
            raise judge.Stop("setting_defect", f"{len(problems)} VBKL0 identity problems: "
                                               f"{problems[:3]}")
        out = original(selection, blocks)
        if out.get("status") != "decided":
            return out
        try:
            record = p_pred_decision(selection, blocks, out["blocks_used"])
        except ppred.InputStop as exc:
            raise judge._with_record(judge.Stop("setting_defect", str(exc)), out) from exc
        out.update(allow_k=record["k_allow"], p_pred=record, edition=6, rule_allow_k=RULE)
        return out

    return decide


def _decision_block_problems(decision: dict) -> list[str]:
    """Edition 5 8-8.2 shape checks without the fixed values: ``allow_k`` an int and the P-pred
    record present (its value is checked against the lines in :func:`_judge_pairs`)."""
    problems = []
    for name in ("allow_k", "blocks_used", "p_pred"):
        if name not in decision:
            problems.append(f"decision record without {name}")
    if problems:
        return problems
    if set(decision["blocks_used"]) != set(decision.get("blocks") or []):
        problems.append("blocks_used is not the set of blocks")
    if sorted(decision["blocks_used"]) not in (["b1", "b2"], ["b1", "b2", "b4"]):
        problems.append(f"blocks_used {decision['blocks_used']}")
    if type(decision["allow_k"]) is not int or decision["allow_k"] != decision["p_pred"].get(
            "k_allow"):
        problems.append("allow_k is not the decision's P-pred k_allow")
    return problems


def _revision_problems(original):
    def revision_problems(line) -> list[str]:
        """Edition 5 4.6 plus the edition 6 tag and the 6.1 item 5 / ``lsb_settings``."""
        import jp3_ed6_judge as ed6

        problems = original(line)
        tag = line.row.get("controller_tag")
        if tag != ed6.ED6_TAG:
            problems.append(f"controller_tag {tag!r} is not {ed6.ED6_TAG}")
        return problems + ed6.lsb_identity_problems(line.row, _sealed_settings())

    return revision_problems


def _judge_pairs(original, selection_ref: list):
    def judge_pairs(blocks0: dict, blocks1: dict, decision: dict, problems) -> dict:
        try:
            recomputed = p_pred_decision(selection_ref[0], blocks0, decision["blocks_used"])
        except ppred.InputStop as exc:
            recomputed = {"error": str(exc)}
        if recomputed.get("k_allow") != decision["allow_k"] or (
                recomputed != decision.get("p_pred")):
            problems.not_judgeable.append("the decision's P-pred record is not the one of these "
                                          "VBKL0 lines (6.4)")
        found = original(blocks0, blocks1, decision, problems)
        found["tau_r_trigger_phase_all"] = tau_r_phases_all(blocks0, decision)
        found["p_pred_recomputed"] = recomputed
        return found

    return judge_pairs


def tau_r_phases_all(blocks0: dict, decision: dict) -> dict[str, int]:
    """The trigger phase of every tau_R VBKL0 line with an injected fault (6.3.3 wording)."""
    out: dict[str, int] = {}
    for block in decision["blocks"]:
        for line in blocks0[block].values():
            if line.fault.get("anchor") != judge.TAU_R_ANCHOR or not judge.is_injected(
                    line.fault):
                continue
            phase = judge.trigger_phase(line)
            out[phase] = out.get(phase, 0) + 1
    return out


def _load_selection(original, selection_ref: list):
    def load_selection(path, expected_sha256):
        selection = original(path, expected_sha256)
        selection_ref[0] = selection
        return selection

    return load_selection


@contextlib.contextmanager
def edition_6() -> Iterator[None]:
    """The edition 6 rules inside ``jp3_12b_judge`` for one command (restored afterwards)."""
    selection_ref: list = [None]
    saved = {name: getattr(judge, name) for name in (
        "SETTING_OF_ARM", "L1_SETTING_OF_ARM", "decide", "decision_block_problems",
        "revision_problems", "judge_pairs", "expected_input_problems", "load_selection")}
    try:
        judge.SETTING_OF_ARM = SETTING_OF_ARM
        judge.L1_SETTING_OF_ARM = L1_SETTING_OF_ARM
        judge.decide = _decide(saved["decide"])
        judge.decision_block_problems = _decision_block_problems
        judge.revision_problems = _revision_problems(saved["revision_problems"])
        judge.judge_pairs = _judge_pairs(saved["judge_pairs"], selection_ref)
        judge.expected_input_problems = lambda args, inputs: ({"edition_6": "no fixed values"},
                                                              [])
        judge.load_selection = _load_selection(saved["load_selection"], selection_ref)
        yield
    finally:
        for name, value in saved.items():
            setattr(judge, name, value)


def main(argv: list[str] | None = None) -> int:
    with edition_6():
        return judge.main(argv)


if __name__ == "__main__":
    sys.exit(main())
