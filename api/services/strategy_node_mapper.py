"""
Strategy Node Mapper.

Maps structured condition suggestions to canvas node definitions.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def map_suggestions_to_nodes(
    suggestions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert validated suggestions into canvas-ready node definitions.

    Each suggestion produces a condition node definition that the frontend
    can directly add to the React Flow canvas.

    Returns list of node mapping dicts:
        {
            "condition_type": str,
            "node_type": "condition",
            "params": dict,
            "label": str,
        }
    """
    from screener.conditions.registry import get_condition_metadata

    metadata = get_condition_metadata()
    nodes = []

    for s in suggestions:
        ctype = s.get("condition_type", "")
        params = s.get("params", {})

        if ctype not in metadata:
            continue

        meta = metadata[ctype]
        label = meta.get("label", ctype)

        # Merge defaults for any missing params
        param_defs = {p["name"]: p for p in meta.get("params", [])}
        merged_params = {}
        for pname, pdef in param_defs.items():
            if pname in params:
                merged_params[pname] = params[pname]
            elif "default" in pdef:
                merged_params[pname] = pdef["default"]

        nodes.append({
            "condition_type": ctype,
            "node_type": "condition",
            "params": merged_params,
            "label": label,
        })

    return nodes
