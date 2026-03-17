"""Unified scraper for GitHub, GitLab, and mailing list archives."""

from argparse import ArgumentParser
from datetime import datetime
from urllib.parse import urlparse, quote
from requests import get


def detect_source(url: str) -> str:
    """Detect whether a URL points to GitHub, GitLab, or a mailing list."""
    host = urlparse(url).hostname or ""
    if "github.com" in host:
        return "github"
    elif "gitlab.com" in host:
        return "gitlab"
    elif host:
        return "mailinglist"
    else:
        raise ValueError(f"Cannot detect source from URL: {url}")


def parse_github_url(url: str) -> str:
    """Extract owner/repo from a GitHub URL."""
    path = urlparse(url).path.strip("/")
    parts = path.split("/")
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub URL: {url} (expected https://github.com/owner/repo)")
    return f"{parts[0]}/{parts[1]}"


def resolve_gitlab_project_id(url: str) -> int:
    """Resolve a GitLab project ID from a URL.

    Accepts either an API URL with a numeric ID or a human-readable path,
    in which case the GitLab API is queried to look up the numeric ID.
    """
    parsed = urlparse(url)
    path = parsed.path.strip("/")

    for segment in reversed(path.split("/")):
        if segment.isdigit():
            return int(segment)

    for prefix in ("api/v4/projects/",):
        if path.startswith(prefix):
            path = path[len(prefix):]

    encoded = quote(path, safe="")
    response = get(f"https://{parsed.hostname}/api/v4/projects/{encoded}")
    response.raise_for_status()
    return response.json()["id"]


def main():
    parser = ArgumentParser(prog='scrape')
    parser.add_argument('url', help="Source URL (GitHub, GitLab, or mailing list archive)")
    parser.add_argument('-o', '--output-dir', default='issues', help="Output directory (default: issues)")
    parser.add_argument('--jsonl', action='store_true', help="Write JSONL to stdout instead of individual files")
    parser.add_argument('--start', type=str, help="Start month YYYY-MM (mailing list only)")
    parser.add_argument('--end', type=str, help="End month YYYY-MM (mailing list only)")
    args = parser.parse_args()

    source = detect_source(args.url)

    if source == "github":
        from scrape.github import scrape
        repository = parse_github_url(args.url)
        scrape(repository, args.output_dir, args.jsonl)

    elif source == "gitlab":
        from scrape.gitlab import scrape
        project_id = resolve_gitlab_project_id(args.url)
        scrape(project_id, args.output_dir, args.jsonl)

    elif source == "mailinglist":
        from scrape.mailinglist import scrape
        if not args.start or not args.end:
            parser.error("--start and --end are required for mailing list scraping")
        start_date = datetime.strptime(args.start, "%Y-%m")
        end_date = datetime.strptime(args.end, "%Y-%m")
        scrape(args.url, start_date, end_date, args.output_dir, args.jsonl)


if __name__ == "__main__":
    main()
