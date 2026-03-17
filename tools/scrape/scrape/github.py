"""GitHub issue scraping logic."""

import os
from buglib import github_session, pages_iterator, write_file, write_jsonl


def output_issue(issue: dict, output_dir: str = "issues") -> None:
    try:
        if 'documentation' in issue['labels']:
            write_file(f"{output_dir}/documentation/{issue['id']}", issue['title'] + '\n' + (issue['description'] or ""))
        else:
            write_file(f"{output_dir}/{issue['id']}", issue['title'] + '\n' + (issue['description'] or ""))
    except TypeError:
        print(f"error with bug {issue['id']}")
        exit()


def scrape(repository: str, output_dir: str, jsonl: bool) -> None:
    session = github_session(os.environ.get("GITHUB_TOKEN"))

    per_page = 100
    url = f"https://api.github.com/repos/{repository}/issues?per_page={per_page}&state=all"
    check_url = f"https://api.github.com/repos/{repository}"

    check = session.get(check_url)
    check.raise_for_status()

    for index, response in enumerate(pages_iterator(session.get(url), session=session)):
        if not jsonl:
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

            if jsonl:
                write_jsonl(issue)
            else:
                output_issue(issue, output_dir)
