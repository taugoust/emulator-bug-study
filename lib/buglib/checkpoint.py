"""Scraper checkpoint helpers.

A checkpoint is a plain text file named ``.checkpoint`` written inside the
scraper output directory.  It holds the URL of the page currently being
processed so that an interrupted run can resume from exactly that page rather
than starting over.

Typical flow inside a scraper
------------------------------
::

    checkpoint_url = read_checkpoint(output_dir)
    start_url      = checkpoint_url or default_first_page_url
    existing_ids   = existing_issue_ids(output_dir)
    use_early_stop = checkpoint_url is None   # only stop early on fresh runs

    for response in pages_iterator(session.get(start_url), session=session):
        write_checkpoint(output_dir, response.url)
        all_existing = True
        for issue in response.json():
            if issue["id"] in existing_ids:
                continue
            all_existing = False
            write_issue(issue, output_dir)
        if use_early_stop and all_existing:
            break        # Scenario A: caught up with already-fetched issues

    clear_checkpoint(output_dir)  # mark run as complete

Scenario A (re-run after a complete scrape)
    No checkpoint file is present.  ``use_early_stop`` is ``True``.
    New issues are written; as soon as a page consists entirely of already-
    known IDs the loop breaks, avoiding unnecessary API calls for older pages.

Scenario B (resume after an interrupted scrape)
    A checkpoint file is present with the URL of the interrupted page.
    Pagination resumes from that URL, ``use_early_stop`` is ``False``, and
    the loop runs to completion so that all missing older issues are fetched.
"""

from __future__ import annotations

import os
from buglib.files import list_files_recursive

_CHECKPOINT_FILENAME = ".checkpoint"


def read_checkpoint(output_dir: str) -> str | None:
    """Return the saved page URL, or ``None`` if no checkpoint exists."""
    path = os.path.join(output_dir, _CHECKPOINT_FILENAME)
    if os.path.exists(path):
        with open(path) as f:
            return f.read().strip() or None
    return None


def write_checkpoint(output_dir: str, url: str) -> None:
    """Persist *url* as the current page checkpoint.

    Called *before* processing a page so that a crash mid-page results in
    that page being re-fetched on the next run.  Already-written issues are
    skipped via :func:`existing_issue_ids`, making re-processing idempotent.
    """
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, _CHECKPOINT_FILENAME), "w") as f:
        f.write(url)


def clear_checkpoint(output_dir: str) -> None:
    """Delete the checkpoint file once a scrape completes successfully."""
    path = os.path.join(output_dir, _CHECKPOINT_FILENAME)
    if os.path.exists(path):
        os.remove(path)


def existing_issue_ids(output_dir: str) -> set[int]:
    """Return the set of issue IDs already present in *output_dir*.

    Scans *output_dir* recursively and collects integer leaf filenames.
    The ``.toml`` extension used by GitLab output files is stripped before
    attempting the conversion so both flat GitHub trees and nested GitLab
    trees are handled transparently.
    """
    ids: set[int] = set()
    for path in list_files_recursive(output_dir):
        name = os.path.basename(path)
        if name.endswith(".toml"):
            name = name[:-5]
        try:
            ids.add(int(name))
        except ValueError:
            pass
    return ids
