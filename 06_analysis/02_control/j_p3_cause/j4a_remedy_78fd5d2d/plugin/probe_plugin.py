"""pytest plugin: pin ``outrigger_sim`` to PROBE_SOURCE and record which package loaded."""
import os
import sys
from pathlib import Path


def pytest_configure(config):
    source = os.environ.get("PROBE_SOURCE")
    if source:
        sys.path.insert(0, source)
        import outrigger_sim  # noqa: F401  (cached: test-file path inserts cannot win)


def pytest_sessionfinish(session, exitstatus):
    out = os.environ.get("PROBE_PLUGIN_OUT")
    if not out:
        return
    import outrigger_sim

    worker = os.environ.get("PYTEST_XDIST_WORKER", "main")
    with Path(out).open("a", encoding="utf-8") as handle:
        handle.write(f"{worker} {outrigger_sim.__file__}\n")
