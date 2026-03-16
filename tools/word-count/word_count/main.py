from os import path, listdir
from argparse import ArgumentParser

def list_files_recursive(directory):
    result = []
    if not path.isdir(directory):
        return result
    for entry in listdir(directory):
        full_path = path.join(directory, entry)
        if path.isdir(full_path):
            result = result + list_files_recursive(full_path)
        else:
            result.append(full_path)
    return result

def main():
    parser = ArgumentParser(prog='word-count')
    parser.add_argument('directories', nargs='+', help="Directories containing bug report files")
    args = parser.parse_args()

    files = []
    for directory in args.directories:
        dir_files = list_files_recursive(directory)
        print(f"{directory} has {len(dir_files)} reports")
        files = files + dir_files

    if not files:
        print("No files found")
        return

    word_count = 0
    for file_path in files:
        with open(file_path, "r") as file:
            words = len(file.read().split(" "))
            word_count = word_count + words

    avg_word_per_bug = word_count / len(files)
    print(f"Total reports: {len(files)}")
    print(f"Total words: {word_count}")
    print(f"Average words per report: {avg_word_per_bug:.1f}")

if __name__ == "__main__":
    main()
