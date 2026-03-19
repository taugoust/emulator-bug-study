"""JSONL (JSON Lines) output helper."""

import json
import sys
from collections.abc import Mapping
from typing import TextIO


def write_jsonl(record: Mapping[str, object], file: TextIO = sys.stdout) -> None:
    """Write *record* as a single JSON line to *file*."""
    file.write(json.dumps(record, ensure_ascii=False))
    file.write("\n")
    file.flush()
