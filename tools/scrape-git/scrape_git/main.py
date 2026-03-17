"""Unified scraper for GitHub and GitLab issues."""

from argparse import ArgumentParser
from urllib.parse import urlparse
from requests import get


def detect_source(url: str) -> str:
    """Detect whether a URL points to GitHub or GitLab."""
    host = urlparse(url).hostname or ""
    if "github.com" in host:
        return "github"
    elif "gitlab.com" in host:
        return "gitlab"
    else:
        raise ValueError(f"Cannot detect source from URL: {url} (expected github.com or gitlab.com)")


def parse_github_url(url: str) -> str:
    """Extract owner/repo from a GitHub URL."""
    path = urlparse(url).path.strip("/")
    parts = path.split("/")
    if len(parts) < 2:
        raise ValueError(f"Invalid GitHub URL: {url} (expected https://github.com/owner/repo)")
    return f"{parts[0]}/{parts[1]}"


def resolve_gitlab_project_id(url: str) -> int:
    """Resolve a GitLab project ID from a URL.

    Accepts either an API URL with a numeric ID
    (``https://gitlab.com/api/v4/projects/11167699``) or a human-readable
    path (``https://gitlab.com/qemu-project/qemu``), in which case the
    GitLab API is queried to look up the numeric ID.
    """
    parsed = urlparse(url)
    path = parsed.path.strip("/")

    # Check for numeric ID in the URL
    for segment in reversed(path.split("/")):
        if segment.isdigit():
            return int(segment)

    # Remove common prefixes
    for prefix in ("api/v4/projects/",):
        if path.startswith(prefix):
            path = path[len(prefix):]

    # URL-encode the path and look up the project
    from urllib.parse import quote

    encoded = quote(path, safe="")
    response = get(f"https://{parsed.hostname}/api/v4/projects/{encoded}")
    response.raise_for_status()
    return response.json()["id"]


def main():
    parser = ArgumentParser(prog='scrape-git')
    parser.add_argument('url', help="Repository URL (GitHub or GitLab)")
    parser.add_argument('-o', '--output-dir', default='issues', help="Output directory (default: issues)")
    parser.add_argument('--jsonl', action='store_true', help="Write JSONL to stdout instead of individual files")
    args = parser.parse_args()

    source = detect_source(args.url)

    if source == "github":
        from scrape_git.github import scrape
        repository = parse_github_url(args.url)
        scrape(repository, args.output_dir, args.jsonl)

    elif source == "gitlab":
        from scrape_git.gitlab import scrape
        project_id = resolve_gitlab_project_id(args.url)
        scrape(project_id, args.output_dir, args.jsonl)


if __name__ == "__main__":
    main()
