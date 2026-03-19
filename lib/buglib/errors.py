"""Error handling for production vs development environments."""

import os
import sys
from types import TracebackType


def install_error_handler() -> None:
    """Suppress tracebacks unless BUG_STUDY_DEV is set."""
    if os.environ.get("BUG_STUDY_DEV"):
        return

    def _handler(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_tb: TracebackType | None,
    ) -> None:
        print(f"Error: {exc_value}", file=sys.stderr)
        sys.exit(1)

    sys.excepthook = _handler
