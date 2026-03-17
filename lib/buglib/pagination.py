"""HTTP link-header pagination helper."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from requests import Response, Session


def pages_iterator(first: "Response", session: "Session | None" = None) -> "Iterator[Response]":
    """Yield successive pages by following ``Link: rel=next`` headers.

    The caller must pass the first :class:`~requests.Response` object.  Each
    yielded response has already been checked with
    :meth:`~requests.Response.raise_for_status`.

    If a :class:`~requests.Session` is provided it is used for all follow-on
    requests, so headers such as ``Authorization`` are forwarded automatically.
    """
    from requests import get

    fetch = session.get if session is not None else get

    current = first
    while current.links.get("next"):
        current.raise_for_status()
        yield current
        current = fetch(url=current.links.get("next").get("url"))
    current.raise_for_status()
    yield current
