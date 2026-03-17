import pytest
import os
import tempfile
from scrape_git.github import output_issue


class TestOutputIssue:
    def test_normal_issue(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            issue = {
                "id": 42,
                "title": "Something broke",
                "labels": ["bug"],
                "description": "Details here",
            }
            output_issue(issue, tmpdir)
            path = os.path.join(tmpdir, "42")
            assert os.path.exists(path)
            content = open(path).read()
            assert "Something broke" in content
            assert "Details here" in content

    def test_documentation_label(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            issue = {
                "id": 99,
                "title": "Docs update",
                "labels": ["documentation"],
                "description": "Fix typo",
            }
            output_issue(issue, tmpdir)
            path = os.path.join(tmpdir, "documentation", "99")
            assert os.path.exists(path)

    def test_none_description(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            issue = {
                "id": 1,
                "title": "No body",
                "labels": [],
                "description": None,
            }
            output_issue(issue, tmpdir)
            content = open(os.path.join(tmpdir, "1")).read()
            assert "No body" in content
