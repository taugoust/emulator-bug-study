from os import listdir, path
from argparse import ArgumentParser
import sys

def parse_iteration(directory):
    dictionary = {}
    for entry in listdir(directory):
        full_path = path.join(directory, entry)
        if path.isdir(full_path):
            dictionary[entry] = len([name for name in listdir(full_path)])
    return dictionary

def output_csv(dictionary, file=sys.stdout):
    file.write("category, count\n")
    for key, value in dictionary.items():
        file.write(f"{key}, {value}\n")

def main():
    parser = ArgumentParser(prog='analyze-csv')
    parser.add_argument('directory', nargs='?', help="Single classifier run directory to summarize")
    parser.add_argument('-r', '--root', help="Root directory containing multiple classifier runs")
    parser.add_argument('-o', '--output', help="Write CSV to file instead of stdout")
    args = parser.parse_args()

    if not args.directory and not args.root:
        parser.error("Provide either a directory or --root")

    if args.directory:
        dictionary = parse_iteration(args.directory)
        if args.output:
            with open(args.output, "w") as f:
                output_csv(dictionary, f)
        else:
            output_csv(dictionary)
    elif args.root:
        for entry in listdir(args.root):
            full_path = path.join(args.root, entry)
            if path.isdir(full_path):
                dictionary = parse_iteration(full_path)
                out_path = path.join(full_path, 'categories.csv')
                with open(out_path, "w") as f:
                    output_csv(dictionary, f)
                print(f"Wrote {out_path}")

if __name__ == "__main__":
    main()
