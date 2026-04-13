from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json_manifest(manifest_path: Path, payload: dict[str, Any]) -> None:
    manifest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")