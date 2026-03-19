from __future__ import annotations

from re import compile, search, DOTALL

from bs4 import BeautifulSoup
from requests import get


def extract_message(html: str) -> str:
    """Extract plain text from an HTML message body."""
    soup = BeautifulSoup(html, 'html.parser')
    return soup.get_text(separator='\n', strip=True)


def collect_thread(url: str) -> str:
    """Fetch a thread and return its full text content."""
    parts: list[str] = []
    _walk_thread(url, parts)
    return "\n\n".join(parts)


def process_thread(url: str, file_path: str) -> None:
    """Fetch a thread and append its content to *file_path*."""
    _walk_thread(url, None, file_path)


def _walk_thread(
    url: str,
    parts: list[str] | None = None,
    file_path: str | None = None,
) -> None:
    pattern = compile(r'\[<a\s+href="([^"]+)">Next in Thread</a>\]')
    current_url: str | None = url

    while current_url is not None:
        request = get(current_url)
        text = request.text

        match = search(r'<!--X-Body-of-Message-->(.*?)<!--X-Body-of-Message-End-->', text, DOTALL)
        if match:
            message = extract_message(match.group(1).strip())
            if parts is not None:
                parts.append(message)
            if file_path is not None:
                with open(file_path, "a") as file:
                    file.write(f"{message}\n\n")

        next_url: str | None = None
        for line in text.splitlines():
            if "Next in Thread" in line:
                next_match = pattern.search(line)
                if next_match:
                    from urllib.parse import urljoin
                    next_url = urljoin(current_url, next_match.group(1))
                    break
        current_url = next_url
