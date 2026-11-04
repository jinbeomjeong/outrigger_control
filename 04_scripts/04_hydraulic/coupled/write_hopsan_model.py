"""Write coupled_four_leg.hmf from hopsan_spec.json with the hopsan-mcp library.

Same functions as the MCP tool create_model (parse_spec, validate_spec, write_model);
the spec has too many parts to pass inline. Run in env hopsan-mcp.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from hopsan_mcp.catalog import Catalog
from hopsan_mcp.config import hopsan_paths
from hopsan_mcp.hmf import parse_spec, write_model
from hopsan_mcp.validation import has_errors, parameter_types_for, validate_spec

HERE = Path(__file__).resolve().parent


def main() -> int:
    spec = json.loads((HERE / "hopsan_spec.json").read_text(encoding="utf-8"))
    model = parse_spec(spec)
    cat = Catalog(hopsan_paths())
    issues = validate_spec(model, cat)
    for i in issues:
        print(i.as_dict())
    if has_errors(issues):
        print("errors: not written")
        return 1
    target = HERE / "coupled_four_leg.hmf"
    write_model(model, target, parameter_types_for(model, cat))
    print(f"written {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
