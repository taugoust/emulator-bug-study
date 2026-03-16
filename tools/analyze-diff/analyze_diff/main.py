from os import path, walk
from pathlib import Path
from argparse import ArgumentParser
import sys

def find_changes(old_directory, new_directory):
    old_files = {}
    for root, dirs, files in walk(old_directory):
        for file in files:
            relative_path = Path(root).relative_to(old_directory)
            old_files[file] = str(relative_path)

    new_files = {}
    for root, dirs, files in walk(new_directory):
        for file in files:
            relative_path = Path(root).relative_to(new_directory)
            new_files[file] = str(relative_path)

    changed_files = []
    for file in old_files:
        if file in new_files and old_files[file] != new_files[file]:
            changed_files.append({
                'name': file,
                'old': old_files[file],
                'new': new_files[file]
            })

    return changed_files

def output_diff(changed_files, file=sys.stdout):
    file.write(f"{len(changed_files)} changes:\n")
    for change in changed_files:
        file.write(f"{change['name']}: {change['old']} -> {change['new']}\n")

def main():
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
