"""GitLab authentication helper."""

from __future__ import annotations

import sys
from requests import Session


def gitlab_session(token: str | None = None) -> Session:
    """Return a :class:`~requests.Session` configured for the GitLab API.

    If *token* is provided the session sends a ``PRIVATE-TOKEN`` header on
    every request, giving access to the 2 000 authenticated req/hour rate
    limit.  If no token is given a warning is printed to stderr and the
    returned session is unauthenticated (500 req/hour, per IP).
    """
    session = Session()
    if token:
        session.headers["PRIVATE-TOKEN"] = token
    else:
        print(
            "Warning: GITLAB_TOKEN is not set; requests will be unauthenticated "
            "(rate-limited to 500 req/hour). "
            "Set GITLAB_TOKEN to a personal access token to raise the limit to 2 000 req/hour.",
            file=sys.stderr,
        )
    return session
