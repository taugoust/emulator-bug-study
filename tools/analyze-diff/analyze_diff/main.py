from __future__ import annotations

import sys
from argparse import ArgumentParser
from os import walk
from pathlib import Path
from typing import TextIO


def find_changes(old_directory: str, new_directory: str) -> list[dict[str, str]]:
    old_files: dict[str, str] = {}
    for root, _dirs, files in walk(old_directory):
        for file in files:
            relative_path = Path(root).relative_to(old_directory)
            old_files[file] = str(relative_path)

    new_files: dict[str, str] = {}
    for root, _dirs, files in walk(new_directory):
        for file in files:
            relative_path = Path(root).relative_to(new_directory)
            new_files[file] = str(relative_path)

    changed_files: list[dict[str, str]] = []
    for file in old_files:
        if file in new_files and old_files[file] != new_files[file]:
            changed_files.append({
                'name': file,
                'old': old_files[file],
                'new': new_files[file],
            })

    return changed_files


def output_diff(changed_files: list[dict[str, str]], file: TextIO = sys.stdout) -> None:
    file.write(f"{len(changed_files)} changes:\n")
    for change in changed_files:
        file.write(f"{change['name']}: {change['old']} -> {change['new']}\n")


def main() -> None:
    parser = ArgumentParser(prog='analyze-diff')
    parser.add_argument('old', help="Path to the old classifier run")
    parser.add_argument('new', help="Path to the new classifier run")
    parser.add_argument('-o', '--output', help="Write diff to file instead of stdout")
    args = parser.parse_args()

    result = find_changes(args.old, args.new)

    if args.output:
        with open(args.output, "w") as f:
            output_diff(result, f)
    else:
        output_diff(result)


if __name__ == "__main__":
    main()
