"""GitLab issue scraping logic."""

from __future__ import annotations

import os
import sys
from json import JSONDecodeError
from typing import Any

from tomlkit import dumps

from buglib import (
    clear_checkpoint, existing_issue_ids, read_checkpoint, write_checkpoint,
    gitlab_session, pages_iterator, write_file, write_jsonl,
)
from .description_parser import parse_description


def find_label(labels: list[str], keyword: str) -> str:
    match = next((s for s in labels if f"{keyword}:" in s), None)
    if not match:
        return f"{keyword}_missing"
    return match.replace(": ", "_")


def output_issue(issue: dict[str, Any], output_dir: str = ".") -> None:
    labels: list[str] = issue['labels']
    issue_id: int = issue['id']
    toml_string = dumps(issue)

    target_label = find_label(labels, "target")
    host_label = find_label(labels, "host")
    accel_label = find_label(labels, "accel")
    write_file(f"{output_dir}/issues_toml/{target_label}/{host_label}/{accel_label}/{issue_id}.toml", toml_string)

    text_path = f"{output_dir}/issues_text/{target_label}/{host_label}/{accel_label}/{issue_id}"
    write_file(text_path, issue['title'] + "\n")
    with open(text_path, "a") as file:
        if issue['description'] != "n/a":
            file.write("Description of problem:\n" + issue['description'] + "\n")
        if issue['reproduce'] != "n/a":
            file.write("Steps to reproduce:\n" + issue['reproduce'] + "\n")
        if issue['additional'] != "n/a":
            file.write("Additional information:\n" + issue['additional'] + "\n")


def _parse_issue(i: dict[str, Any]) -> dict[str, Any]:
    """Return a normalised issue dict from a raw GitLab API response item."""
    issue: dict[str, Any] = {
        "id": i['iid'],
        "title": i['title'],
        "state": i['state'],
        "created_at": i['created_at'],
        "closed_at": i['closed_at'] if i['closed_at'] else "n/a",
        "labels": i['labels'],
        "url": i['web_url'],
    }
    return issue | parse_description(i['description'])


def scrape(project_id: int, output_dir: str, jsonl: bool) -> None:
    session = gitlab_session(os.environ.get("GITLAB_TOKEN"))

    per_page = 100
    url = f"https://gitlab.com/api/v4/projects/{project_id}/issues?per_page={per_page}"

    if jsonl:
        for response in pages_iterator(session.get(url), session=session):
            try:
                items = response.json()
            except JSONDecodeError:
                print(f"Warning: non-JSON response from {response.url}, skipping page", file=sys.stderr)
                continue
            for i in items:
                write_jsonl(_parse_issue(i))
        return

    checkpoint_url = read_checkpoint(output_dir)
    start_url = checkpoint_url or url
    existing_ids = existing_issue_ids(os.path.join(output_dir, "issues_text"))
    use_early_stop = checkpoint_url is None

    for response in pages_iterator(session.get(start_url), session=session):
        print(f"Current page: {response.headers['x-page']}")
        write_checkpoint(output_dir, response.url)

        try:
            items = response.json()
        except JSONDecodeError:
            print(f"Warning: non-JSON response from {response.url}, skipping page", file=sys.stderr)
            continue

        all_existing = True
        for i in items:
            issue = _parse_issue(i)
            if issue['id'] in existing_ids:
                continue
            all_existing = False
            output_issue(issue, output_dir)

        if use_early_stop and all_existing:
            break

    clear_checkpoint(output_dir)
