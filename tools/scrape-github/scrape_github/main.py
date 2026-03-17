from requests import get
from buglib import pages_iterator
from .output import output_issue
from argparse import ArgumentParser


def main():
    parser = ArgumentParser(prog='scrape-github')
    parser.add_argument('-r', '--repository', required=True, help="Repository to download issues from (format: owner/repo)")
    parser.add_argument('-o', '--output-dir', default='issues', help="Output directory (default: issues)")
    args = parser.parse_args()

    per_page = 100
    url = f"https://api.github.com/repos/{args.repository}/issues?per_page={per_page}&state=all"
    check_url = f"https://api.github.com/repos/{args.repository}"

    check = get(check_url)
    check.raise_for_status()

    for index, response in enumerate(pages_iterator(get(url))):
        print(f"Current page: {index+1}")

        data = response.json()
        for i in data:
            if "pull_request" in i:
                continue

            issue = {
                "id": i['number'],
                "title": i['title'],
                "labels": [label['name'] for label in i['labels']],
                "description": i['body'],
            }

            output_issue(issue, args.output_dir)

if __name__ == "__main__":
    main()
