from __future__ import annotations

import sys
from argparse import ArgumentParser
from os import makedirs, path
from typing import TextIO

from buglib import install_error_handler, list_files_recursive


def output_csv(dictionary: dict[str, int], file: TextIO = sys.stdout) -> None:
    file.write("category, count\n")
    for key, value in dictionary.items():
        file.write(f"{key}, {value}\n")


def duplicate_bug(file_path: str, category: str, output_dir: str) -> None:
    output_path = path.join(output_dir, category)
    makedirs(output_path, exist_ok=True)
    with open(file_path, "r") as file:
        text = file.read()
    with open(path.join(output_path, path.basename(file_path)), "w") as file:
        file.write(text)


def main() -> None:
    install_error_handler()
    parser = ArgumentParser(prog='analyze-results')
    parser.add_argument('-b', '--bugs', required=True, help="Directory of known bugs to look up")
    parser.add_argument('-d', '--search-directory', required=True, help="Classifier output directory to search in")
    parser.add_argument('-o', '--output', help="Copy matched bugs into this directory, organized by category")
    args = parser.parse_args()

    result: dict[str, int] = {}
    known_bugs = list_files_recursive(args.bugs, True)
    classified_bugs = list_files_recursive(args.search_directory, False)

    for known_bug in known_bugs:
        for bug in classified_bugs:
            if known_bug == path.basename(bug):
                category = path.basename(path.dirname(bug))
                if args.output:
                    duplicate_bug(bug, category, args.output)
                if category in result:
                    result[category] += 1
                else:
                    result[category] = 1
                continue

    output_csv(result)


if __name__ == "__main__":
    main()
