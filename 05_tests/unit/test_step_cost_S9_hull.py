"""step_cost_S9 summary rows carry the hull hook block (mode, source, DLL SHA-256; post-switch audit 2026-11-09)."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BENCHMARK_DIR = ROOT / "04_scripts" / "02_chrono" / "solver_benchmark"


def _module(monkeypatch):
    # the module sets BLAS thread env defaults at import; monkeypatch restores them after the test
    monkeypatch.delenv("OPENBLAS_NUM_THREADS", raising=False)
    monkeypatch.delenv("MKL_NUM_THREADS", raising=False)
    monkeypatch.syspath_prepend(str(BENCHMARK_DIR))
    return importlib.import_module("step_cost_S9")


def test_hull_hook_summary(monkeypatch) -> None:
    module = _module(monkeypatch)
    record = {"mode": "fast", "requested": "fast", "source": "default", "dll_sha256": "c" * 64,
              "fallback_reason": None, "stats": {"calls": 3}}
    assert module.hull_hook_summary(record) == {"mode": "fast", "source": "default", "dll_sha256": "c" * 64,
                                                "fallback_reason": None}
    assert module.hull_hook_summary(None) is None
    assert "step_cost_S9" in sys.modules
