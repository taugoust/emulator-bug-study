from requests import get
from buglib import pages_iterator
from .description_parser import parse_description
from .output import output_issue
from argparse import ArgumentParser


def main():
    parser = ArgumentParser(prog='scrape-gitlab')
    parser.add_argument('-p', '--project-id', required=True, type=int, help="GitLab project ID")
    parser.add_argument('-o', '--output-dir', default='.', help="Output directory (default: current directory)")
    args = parser.parse_args()

    per_page = 100
    url = f"https://gitlab.com/api/v4/projects/{args.project_id}/issues?per_page={per_page}"

    for response in pages_iterator(get(url)):
        print(f"Current page: {response.headers['x-page']}")

        data = response.json()
        for i in data:
            issue = {
                "id": i['iid'],
                "title": i['title'],
                "state": i['state'],
                "created_at": i['created_at'],
                "closed_at": i['closed_at'] if i['closed_at'] else "n/a",
                "labels": i['labels'],
                "url": i['web_url']
            }

            issue = issue | parse_description(i['description'])
            output_issue(issue, args.output_dir)

if __name__ == "__main__":
    main()
