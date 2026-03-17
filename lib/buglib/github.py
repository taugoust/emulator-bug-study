"""GitHub authentication helper."""

from __future__ import annotations

import sys
from requests import Session


def github_session(token: str | None = None) -> Session:
    """Return a :class:`~requests.Session` configured for the GitHub API.

    If *token* is provided the session sends an ``Authorization: Bearer``
    header on every request, giving access to the 5 000 req/hour rate limit.
    If no token is given a warning is printed to stderr and the returned
    session is unauthenticated (60 req/hour, per IP).
    """
    session = Session()
    if token:
        session.headers["Authorization"] = f"Bearer {token}"
    else:
        print(
            "Warning: GITHUB_TOKEN is not set; requests will be unauthenticated "
            "(rate-limited to 60 req/hour). "
            "Set GITHUB_TOKEN to a personal access token to raise the limit to 5 000 req/hour.",
            file=sys.stderr,
        )
    return session
