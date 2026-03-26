from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def to_json_string(payload: Any, *, indent: int = 2) -> str:
    return json.dumps(payload, indent=indent, ensure_ascii=False)


def write_json_file(path: str | Path, payload: Any, *, indent: int = 2) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with target.open("w", encoding="utf-8") as outfile:
        json.dump(payload, outfile, indent=indent, ensure_ascii=False)
        outfile.write("\n")


def write_jsonl_file(path: str | Path, rows: list[dict[str, Any]]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with target.open("w", encoding="utf-8") as outfile:
        for row in rows:
            outfile.write(json.dumps(row, ensure_ascii=False))
            outfile.write("\n")
