from os import path, listdir, makedirs
from datetime import timedelta
from time import monotonic
from argparse import ArgumentParser
from re import sub

def list_files_recursive(directory, basename = False):
    result = []
    if not path.isdir(directory):
        return result
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

def write_output(text, category, labels, scores, identifier, output_dir, start_time, reasoning=None):
    print(f"Category: {category}, Time: {timedelta(seconds=monotonic() - start_time)}")
    file_path = path.join(output_dir, category, identifier)
    makedirs(path.dirname(file_path), exist_ok = True)

    with open(file_path, "w") as file:
        for label, score in zip(labels, scores):
            if label == "SPLIT":
                file.write(f"--------------------\n")
            else:
                file.write(f"{label}: {score:.3f}\n")

        file.write("\n")
        file.write(text)

    if reasoning:
        reasoning_dir = path.join(path.dirname(output_dir), "reasoning")
        file_path = path.join(reasoning_dir, category, identifier)
        makedirs(path.dirname(file_path), exist_ok = True)

        with open(file_path, "w") as file:
            file.write(reasoning)

def get_category(classification, positive_categories, negative_categories, architectures, multi_label):
    highest_category = classification['labels'][0]

    if not multi_label:
        return highest_category

    if all(i < 0.8 for i in classification["scores"]):
        return "none"
    elif sum(1 for i in classification["scores"] if i > 0.85) >= 20:
        return "all"
    elif classification["scores"][0] - classification["scores"][-1] <= 0.2:
        return "unknown"

    result = highest_category
    arch = None
    pos = None
    for label, score in zip(classification["labels"], classification["scores"]):
        if label in negative_categories and (not arch and not pos or score >= 0.92):
            return label

        if label in positive_categories and not pos and score > 0.8:
            pos = label
            if not arch:
                result = label
            else:
                result = label + "-" + arch

        if label in architectures and not arch and score > 0.8:
            arch = label
            if pos:
                result = pos + "-" + label

    return result

def compare_category(classification, category, positive_categories):
    for label, score in zip(classification["labels"], classification["scores"]):
        if label in positive_categories and score >= 0.85:
            return category
        if label in category and score >= 0.85:
            return category

    return "review"

def main():
    parser = ArgumentParser(prog='bug-classify')
    parser.add_argument('-i', '--input-dir', required=True, action='append', help="Input directory containing bug files (repeatable)")
    parser.add_argument('-o', '--output-dir', default='output', help="Output directory (default: output)")
    parser.add_argument('-m', '--multi-label', action='store_true', help="Enable multi-label classification")
    parser.add_argument('--ollama', nargs='?', const="deepseek-r1:7b", type=str, help="Use a local model via Ollama (optionally specify model name)")
    parser.add_argument('--preamble', type=str, help="Path to preamble/prompt file (required with --ollama)")
    parser.add_argument('--model', default="facebook/bart-large-mnli", type=str, help="HuggingFace model for zero-shot classification")
    parser.add_argument('--compare', nargs='?', const="MoritzLaurer/deberta-v3-large-zeroshot-v2.0", type=str, help="Second model for cross-validation")
    parser.add_argument('--positive', nargs='+', default=['semantic', 'TCG', 'assembly', 'architecture', 'mistranslation', 'register', 'user-level'], help="Positive category labels")
    parser.add_argument('--negative', nargs='+', default=['boot', 'network', 'kvm', 'vnc', 'graphic', 'device', 'socket', 'debug', 'files', 'PID', 'permissions', 'performance', 'kernel', 'peripherals', 'VMM', 'hypervisor', 'virtual', 'other'], help="Negative category labels")
    parser.add_argument('--architectures', nargs='+', default=['x86', 'arm', 'risc-v', 'i386', 'ppc'], help="Architecture labels")
    args = parser.parse_args()

    positive_categories = args.positive
    negative_categories = args.negative
    architectures = args.architectures
    categories = positive_categories + negative_categories + architectures

    if args.ollama and not args.preamble:
        parser.error("--preamble is required when using --ollama")

    start_time = monotonic()

    if not args.ollama:
        from transformers import pipeline
        classifier = pipeline("zero-shot-classification", model=args.model)
        print(f"The model {args.model} will be used")
        compare_classifier = None
        if args.compare:
            compare_classifier = pipeline("zero-shot-classification", model=args.compare)
            print(f"The comparison model {args.compare} will be used")
    else:
        from ollama import chat
        print(f"The model {args.ollama} will be used")
        with open(args.preamble, "r") as file:
            preamble = file.read()

    processed_bugs = list_files_recursive(args.output_dir, True)

    bugs = []
    for input_dir in args.input_dir:
        bugs = bugs + list_files_recursive(input_dir)

    print(f"{len(bugs)} number of bugs will be processed")
    for i, bug in enumerate(bugs):
        print(f"Bug: {bug}, Number: {i+1},", end=" ")

        if path.basename(bug) in processed_bugs:
            print("skipped")
            continue

        with open(bug, "r") as file:
            text = file.read()

        if args.ollama:
            response = chat(args.ollama, [{'role': 'user', 'content': text + "\n" + preamble}])
            category = sub(r'[^a-zA-Z]', '', response['message']['content'].split()[-1]).lower()
            if category not in categories:
                category = "manual-review"
            write_output(text, category, [], [], path.basename(bug), args.output_dir, start_time, response['message']['content'])
        else:
            result = classifier(text, categories, multi_label=args.multi_label)
            category = get_category(result, positive_categories, negative_categories, architectures, args.multi_label)

            if args.compare and compare_classifier and sum(1 for c in positive_categories if c in category) >= 1:
                compare_result = compare_classifier(text, categories, multi_label=args.multi_label)
                category = compare_category(compare_result, category, positive_categories)

                result['labels'] = result['labels'] + ['SPLIT'] + compare_result['labels']
                result['scores'] = result['scores'] + [0] + compare_result['scores']

            write_output(text, category, result['labels'], result['scores'], path.basename(bug), args.output_dir, start_time)

    end_time = monotonic()
    print(timedelta(seconds=end_time - start_time))

if __name__ == "__main__":
    main()
