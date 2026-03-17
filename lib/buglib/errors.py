"""Error handling for production vs development environments."""

import os
import sys


def install_error_handler():
    """Suppress tracebacks unless BUG_STUDY_DEV is set."""
    if os.environ.get("BUG_STUDY_DEV"):
        return

    def _handler(exc_type, exc_value, exc_tb):
        print(f"Error: {exc_value}", file=sys.stderr)
        sys.exit(1)

    sys.excepthook = _handler
