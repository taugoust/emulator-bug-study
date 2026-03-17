import pytest
import os
import tempfile
from scrape_github.output import output_issue, write_file


class TestWriteFile:
    def test_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sub", "file.txt")
            write_file(path, "hello")
            assert open(path).read() == "hello"

    def test_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "a", "b", "c", "file.txt")
            write_file(path, "nested")
            assert os.path.exists(path)


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


class TestWordCount:
    """Test word_count by exercising list_files_recursive."""

    def test_list_files(self):
        from word_count.main import list_files_recursive

        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ['a', 'b']:
                open(os.path.join(tmpdir, name), 'w').close()
            subdir = os.path.join(tmpdir, 'sub')
            os.makedirs(subdir)
            open(os.path.join(subdir, 'c'), 'w').close()

            result = list_files_recursive(tmpdir)
            assert len(result) == 3

    def test_empty_dir(self):
        from word_count.main import list_files_recursive

        with tempfile.TemporaryDirectory() as tmpdir:
            result = list_files_recursive(tmpdir)
            assert result == []
