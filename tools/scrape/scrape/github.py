"""GitHub issue scraping logic."""

import os
import sys
from json import JSONDecodeError
from buglib import (
    clear_checkpoint, existing_issue_ids, read_checkpoint, write_checkpoint,
    github_session, pages_iterator, write_file, write_jsonl,
)


def output_issue(issue: dict, output_dir: str = "issues") -> None:
    if 'documentation' in issue['labels']:
        write_file(f"{output_dir}/documentation/{issue['id']}", issue['title'] + '\n' + (issue['description'] or ""))
    else:
        write_file(f"{output_dir}/{issue['id']}", issue['title'] + '\n' + (issue['description'] or ""))


def _parse_issue(i: dict) -> dict | None:
    """Return a normalised issue dict, or ``None`` for pull requests."""
    if "pull_request" in i:
        return None
    return {
        "id": i['number'],
        "title": i['title'],
        "labels": [label['name'] for label in i['labels']],
        "description": i['body'],
    }


def scrape(repository: str, output_dir: str, jsonl: bool) -> None:
    session = github_session(os.environ.get("GITHUB_TOKEN"))

    per_page = 100
    url = f"https://api.github.com/repos/{repository}/issues?per_page={per_page}&state=all"
    check_url = f"https://api.github.com/repos/{repository}"

    check = session.get(check_url)
    check.raise_for_status()

    if jsonl:
        for response in pages_iterator(session.get(url), session=session):
            try:
                items = response.json()
            except JSONDecodeError:
                print(f"Warning: non-JSON response from {response.url}, skipping page", file=sys.stderr)
                continue
            for i in items:
                issue = _parse_issue(i)
                if issue:
                    write_jsonl(issue)
        return

    checkpoint_url = read_checkpoint(output_dir)
    start_url = checkpoint_url or url
    existing_ids = existing_issue_ids(output_dir)
    use_early_stop = checkpoint_url is None

    for index, response in enumerate(pages_iterator(session.get(start_url), session=session)):
        print(f"Current page: {index+1}")
        write_checkpoint(output_dir, response.url)

        try:
            items = response.json()
        except JSONDecodeError:
            print(f"Warning: non-JSON response from {response.url}, skipping page", file=sys.stderr)
            continue

        all_existing = True
        has_issues = False
        for i in items:
            issue = _parse_issue(i)
            if issue is None:
                continue
            has_issues = True
            if issue['id'] in existing_ids:
                continue
            all_existing = False
            output_issue(issue, output_dir)

        if use_early_stop and has_issues and all_existing:
            break

    clear_checkpoint(output_dir)
