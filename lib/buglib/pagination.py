"""HTTP link-header pagination helper."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from requests import Response


def pages_iterator(first: "Response") -> "Iterator[Response]":
    """Yield successive pages by following ``Link: rel=next`` headers.

    The caller must pass the first :class:`~requests.Response` object.  Each
    yielded response has already been checked with
    :meth:`~requests.Response.raise_for_status`.
    """
    from requests import get

    current = first
    while current.links.get("next"):
        current.raise_for_status()
        yield current
        current = get(url=current.links.get("next").get("url"))
    current.raise_for_status()
    yield current
