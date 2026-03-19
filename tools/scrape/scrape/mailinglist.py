"""Mailing list scraping logic."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from hashlib import sha256
from os import makedirs, path
from re import search, match
from urllib.parse import urljoin
from urllib.request import urlopen

from bs4 import BeautifulSoup, Tag

from buglib import write_jsonl

from .launchpad import process_launchpad_bug, fetch_launchpad_bug
from .thread import process_thread, collect_thread


def months_iterator(start: datetime, end: datetime) -> Iterator[datetime]:
    current = start
    while current <= end:
        yield current
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)


def prepare_output(ml_dir: str, lp_dir: str) -> None:
    makedirs(ml_dir, exist_ok=True)
    makedirs(lp_dir, exist_ok=True)


def is_bug(text: str) -> bool:
    return bool(search(r'\[[^\]]*\b(BUG|bug|Bug)\b[^\]]*\]', text))


def scrape(
    base_url: str,
    start_date: datetime,
    end_date: datetime,
    output_dir: str,
    jsonl: bool,
) -> None:
    base_url = base_url.rstrip('/')

    ml_dir = path.join(output_dir, "mailinglist")
    lp_dir = path.join(output_dir, "launchpad")

    if not jsonl:
        prepare_output(ml_dir, lp_dir)

    seen_launchpad: set[str] = set()
    seen_threads: dict[str, dict[str, str]] = {}

    for month in months_iterator(start_date, end_date):
        if not jsonl:
            print(f"{month.strftime('%Y-%m')}")
        url = f"{base_url}/{month.strftime('%Y-%m')}/threads.html"
        html = urlopen(url).read()
        soup = BeautifulSoup(html, features='html5lib')

        body = soup.body
        if body is None:
            continue
        ul = body.find('ul')
        if not isinstance(ul, Tag):
            continue
        threads = ul.find_all('li', recursive=False)

        for li in reversed(threads):
            b_tag = li.find('b')
            if not isinstance(b_tag, Tag):
                continue
            a_tag = b_tag.find('a')
            if not isinstance(a_tag, Tag):
                continue

            text = a_tag.get_text(strip=True)
            href = a_tag.get('href')
            if not isinstance(href, str):
                continue

            if not is_bug(text):
                continue

            # bug issued in launchpad
            re_match = search(r'\[Bug\s(\d+)\]', text)
            if re_match:
                bug_id = re_match.group(1).strip()
                if jsonl:
                    if bug_id not in seen_launchpad:
                        seen_launchpad.add(bug_id)
                        result = fetch_launchpad_bug(bug_id)
                        if result:
                            write_jsonl(result)
                else:
                    process_launchpad_bug(bug_id, lp_dir)
                continue

            # existing thread
            re_match = match(r'(?i)^re:\s*(.*)', text)
            if re_match:
                title_hash = sha256(re_match.group(1).strip().encode()).hexdigest()[:12]
                if jsonl:
                    if title_hash in seen_threads:
                        seen_threads[title_hash]["content"] += "\n\n" + collect_thread(urljoin(url, href))
                else:
                    out_path = path.join(ml_dir, title_hash)
                    if path.exists(out_path):
                        process_thread(urljoin(url, href), out_path)
                continue

            # new thread
            title_hash = sha256(text.strip().encode()).hexdigest()[:12]
            if jsonl:
                if title_hash in seen_threads:
                    print(f"ERROR: {title_hash} should not exist!")
                    continue
                content = text + "\n\n" + collect_thread(urljoin(url, href))
                seen_threads[title_hash] = {
                    "id": title_hash,
                    "source": "mailinglist",
                    "title": text.strip(),
                    "content": content,
                }
            else:
                out_path = path.join(ml_dir, title_hash)
                if path.exists(out_path):
                    print(f"ERROR: {title_hash} should not exist!")
                    continue

                with open(out_path, "w") as file:
                    file.write(f"{text}\n\n")
                process_thread(urljoin(url, href), out_path)

    if jsonl:
        for record in seen_threads.values():
            write_jsonl(record)
