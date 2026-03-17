"""JSONL (JSON Lines) output helper."""

import json
import sys


def write_jsonl(record: dict, file=sys.stdout) -> None:
    """Write *record* as a single JSON line to *file*."""
    file.write(json.dumps(record, ensure_ascii=False))
    file.write("\n")
    file.flush()
