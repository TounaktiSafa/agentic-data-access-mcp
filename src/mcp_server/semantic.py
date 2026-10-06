import json
import os
from pathlib import Path

import yaml

SEMANTIC_DIR = Path(os.getenv("SEMANTIC_DIR", Path(__file__).resolve().parents[2] / "semantic"))


def load_models() -> dict:
    """Read dbt manifest.json -> {'schema.table': {description, columns}}."""
    manifest = json.loads((SEMANTIC_DIR / "manifest.json").read_text())
    out = {}
    for node in manifest["nodes"].values():
        if node.get("resource_type") != "model":
            continue
        out[f'{node["schema"]}.{node["name"]}'] = {
            "description": node.get("description", ""),
            "columns": {c: v.get("description", "") for c, v in node.get("columns", {}).items()},
        }
    return out


def load_metrics() -> dict:
    return yaml.safe_load((SEMANTIC_DIR / "metrics.yml").read_text())["metrics"]
