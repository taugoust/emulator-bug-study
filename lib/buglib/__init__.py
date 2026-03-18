"""Shared utilities for bug study tools."""

from buglib.checkpoint import clear_checkpoint, existing_issue_ids, read_checkpoint, write_checkpoint
from buglib.errors import install_error_handler
from buglib.files import write_file, list_files_recursive
from buglib.github import github_session
from buglib.gitlab import gitlab_session
from buglib.jsonl import write_jsonl
from buglib.pagination import pages_iterator

__all__ = [
    "clear_checkpoint", "existing_issue_ids", "read_checkpoint", "write_checkpoint",
    "install_error_handler",
    "write_file", "list_files_recursive",
    "github_session", "gitlab_session",
    "write_jsonl",
    "pages_iterator",
]
