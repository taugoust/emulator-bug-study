from argparse import ArgumentParser
from os import path, listdir, makedirs
import sys

def list_files_recursive(directory, basename = False):
    result = []
    for entry in listdir(directory):
        full_path = path.join(directory, entry)
        if path.isdir(full_path):
            result = result + list_files_recursive(full_path, basename)
        else:
            if basename:
                result.append(path.basename(full_path))
            else:
                result.append(full_path)
    return result

def output_csv(dictionary, file=sys.stdout):
    file.write("category, count\n")
    for key, value in dictionary.items():
        file.write(f"{key}, {value}\n")

def duplicate_bug(file_path, category, output_dir):
    output_path = path.join(output_dir, category)
    makedirs(output_path, exist_ok = True)
    with open(file_path, "r") as file:
        text = file.read()
    with open(path.join(output_path, path.basename(file_path)), "w") as file:
        file.write(text)

def main():
    parser = ArgumentParser(prog='analyze-results')
    parser.add_argument('-b', '--bugs', required=True, help="Directory of known bugs to look up")
    parser.add_argument('-d', '--search-directory', required=True, help="Classifier output directory to search in")
    parser.add_argument('-o', '--output', help="Copy matched bugs into this directory, organized by category")
    args = parser.parse_args()

    result = {}
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
