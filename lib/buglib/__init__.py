"""Shared utilities for bug study tools."""

from buglib.errors import install_error_handler
from buglib.files import write_file, list_files_recursive
from buglib.jsonl import write_jsonl
from buglib.pagination import pages_iterator

__all__ = ["install_error_handler", "write_file", "list_files_recursive", "write_jsonl", "pages_iterator"]
