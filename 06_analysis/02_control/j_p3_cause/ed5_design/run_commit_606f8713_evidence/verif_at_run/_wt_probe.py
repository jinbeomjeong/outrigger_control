"""pytest plugin that ``worktree_tests.py`` copies into its run folder.

``worktree_tests.py`` loads it with ``-p _wt_probe``.

It runs inside the project's pytest (every xdist worker too) and does three things:

* ``rebase_data(path)``: the copied tests call it around their stored-data
  paths (see ``_source_rebase.py``); a path below ``<worktree>/<folder>`` comes
  back below ``<data root>/<folder>``. Relative paths are taken from the current
  folder first. Counts of rebased / already-in-data-root / unmatched values are
  kept for the probe record.
* ``pytest_configure``: appends the original test folders to ``sys.path`` (so a
  sibling helper module of a copied test imports from the worktree) and, when
  asked, imports the pinned modules early so that a later
  ``sys.path.insert(0, <other tree>)`` cannot swap them.
* ``pytest_sessionfinish``: writes ``probe_<worker>.json`` with the ``__file__``
  of every probe module that this process imported, and the rebase counts.

Configuration comes from the JSON file named by the environment variable
``WT_TESTS_CONFIG`` (set by ``worktree_tests.py``; xdist workers inherit it).
The plugin uses only the standard library and never writes outside the run folder.
"""

from __future__ import annotations

import functools
import importlib
import json
import os
import sys
from pathlib import Path, PurePath

CONFIG_VARIABLE = "WT_TESTS_CONFIG"
MAX_RECORDED_VALUES = 20

# Per-process run-time record; written once at session finish.
_counts = {"rebased": 0, "already_in_data_root": 0, "unmatched": 0}
_rebased_examples: list[list[str]] = []
_unmatched_values: list[str] = []
_pin_results: dict[str, str] = {}


@functools.cache
def _settings() -> dict:
    # Read lazily: importing this file outside a run (lint, vulture) must not fail.
    config_path = Path(os.environ[CONFIG_VARIABLE])
    return json.loads(config_path.read_text(encoding="utf-8"))


def _is_below(path: Path, folder: Path) -> bool:
    try:
        path.relative_to(folder)
    except ValueError:
        return False
    return True


def _remember(values: list, value: object) -> None:
    if len(values) < MAX_RECORDED_VALUES and value not in values:
        values.append(value)


def rebase_data(value: object) -> object:
    """Map a worktree data path onto the data root; anything else comes back as is."""
    settings = _settings()
    worktree = Path(settings["worktree"])
    data_root = Path(settings["data_root"])
    try:
        path = Path(os.fspath(value))  # type: ignore[arg-type]
    except TypeError:
        _counts["unmatched"] += 1
        _remember(_unmatched_values, repr(value))
        return value
    absolute = path if path.is_absolute() else Path.cwd() / path
    for folder in settings["rebase_dirs"]:
        source = worktree / folder
        if not _is_below(absolute, source):
            continue
        rebased = data_root / folder / absolute.relative_to(source)
        _counts["rebased"] += 1
        _remember(_rebased_examples, [str(absolute), str(rebased)])
        return rebased if isinstance(value, PurePath) else str(rebased)
    if any(
        _is_below(absolute, data_root / folder) for folder in settings["rebase_dirs"]
    ):
        _counts["already_in_data_root"] += 1
    else:
        _counts["unmatched"] += 1
        _remember(_unmatched_values, str(absolute))
    return value


def _module_location(module: object) -> str | None:
    location = getattr(module, "__file__", None)
    if location:
        return str(location)
    search_path = list(getattr(module, "__path__", []) or [])
    return str(search_path[0]) if search_path else None


def pytest_configure() -> None:
    """Make sibling helpers importable and pin the requested modules early."""
    settings = _settings()
    for folder in settings["support_paths"]:
        if folder not in sys.path:
            sys.path.append(folder)
    for name in settings["pin_modules"]:
        try:
            module = importlib.import_module(name)
        except ImportError as error:
            _pin_results[name] = f"import failed: {error}"
            continue
        _pin_results[name] = _module_location(module) or "(no file)"


def pytest_sessionfinish() -> None:
    """Write this process's probe record (pytest allows hooks without arguments)."""
    settings = _settings()
    worker = os.environ.get("PYTEST_XDIST_WORKER", "main")
    modules = {}
    for name in settings["probe_modules"]:
        module = sys.modules.get(name)
        modules[name] = None if module is None else _module_location(module)
    record = {
        "worker": worker,
        "pid": os.getpid(),
        "cwd": str(Path.cwd()),
        "modules": modules,
        "pinned": _pin_results,
        "rebase": dict(_counts),
        "rebased_examples": _rebased_examples,
        "unmatched_values": _unmatched_values,
    }
    probe_path = Path(settings["probe_dir"]) / f"probe_{worker}.json"
    probe_path.write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
