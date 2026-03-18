import pytest
import os
import tempfile
from unittest.mock import MagicMock, patch
from buglib.files import write_file, list_files_recursive
from buglib.github import github_session
from buglib.gitlab import gitlab_session
from buglib.pagination import pages_iterator


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

    def test_overwrites_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sub", "file.txt")
            write_file(path, "first")
            write_file(path, "second")
            assert open(path).read() == "second"


class TestListFilesRecursive:
    def test_flat_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ['a', 'b', 'c']:
                open(os.path.join(tmpdir, name), 'w').close()
            result = list_files_recursive(tmpdir)
            assert len(result) == 3

    def test_nested_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, 'sub')
            os.makedirs(subdir)
            open(os.path.join(tmpdir, 'a'), 'w').close()
            open(os.path.join(subdir, 'b'), 'w').close()
            result = list_files_recursive(tmpdir)
            assert len(result) == 2

    def test_basename_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, 'sub')
            os.makedirs(subdir)
            open(os.path.join(subdir, 'myfile'), 'w').close()
            result = list_files_recursive(tmpdir, basename=True)
            assert result == ['myfile']

    def test_nonexistent_directory(self):
        result = list_files_recursive('/nonexistent/path')
        assert result == []

    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = list_files_recursive(tmpdir)
            assert result == []


class TestGithubSession:
    def test_with_token_sets_auth_header(self):
        session = github_session("mytoken")
        assert session.headers["Authorization"] == "Bearer mytoken"

    def test_without_token_no_auth_header(self):
        session = github_session(None)
        assert "Authorization" not in session.headers

    def test_empty_token_no_auth_header(self):
        # GITHUB_TOKEN=$(gh auth token ...) yields "" when gh is not set up
        session = github_session("")
        assert "Authorization" not in session.headers

    def test_without_token_warns(self, capsys):
        github_session(None)
        err = capsys.readouterr().err
        assert "Warning" in err
        assert "GITHUB_TOKEN" in err

    def test_empty_token_warns(self, capsys):
        github_session("")
        err = capsys.readouterr().err
        assert "Warning" in err
        assert "GITHUB_TOKEN" in err

    def test_with_token_no_warning(self, capsys):
        github_session("mytoken")
        assert capsys.readouterr().err == ""


class TestGitlabSession:
    def test_with_token_sets_private_token_header(self):
        session = gitlab_session("mytoken")
        assert session.headers["PRIVATE-TOKEN"] == "mytoken"

    def test_without_token_no_private_token_header(self):
        session = gitlab_session(None)
        assert "PRIVATE-TOKEN" not in session.headers

    def test_empty_token_no_private_token_header(self):
        # GITLAB_TOKEN=$(glab auth token ...) yields "" when glab is not set up
        session = gitlab_session("")
        assert "PRIVATE-TOKEN" not in session.headers

    def test_without_token_warns(self, capsys):
        gitlab_session(None)
        err = capsys.readouterr().err
        assert "Warning" in err
        assert "GITLAB_TOKEN" in err

    def test_empty_token_warns(self, capsys):
        gitlab_session("")
        err = capsys.readouterr().err
        assert "Warning" in err
        assert "GITLAB_TOKEN" in err

    def test_with_token_no_warning(self, capsys):
        gitlab_session("mytoken")
        assert capsys.readouterr().err == ""


def _mock_response(has_next: bool) -> MagicMock:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.links = {"next": {"url": "https://api.github.com/page2"}} if has_next else {}
    return response


class TestPagesIteratorSession:
    def test_session_used_for_next_page(self):
        first = _mock_response(has_next=True)
        second = _mock_response(has_next=False)
        session = MagicMock()
        session.get.return_value = second

        pages = list(pages_iterator(first, session=session))

        assert len(pages) == 2
        session.get.assert_called_once_with(url="https://api.github.com/page2")

    def test_without_session_uses_requests_get(self):
        first = _mock_response(has_next=True)
        second = _mock_response(has_next=False)

        with patch("requests.get", return_value=second) as mock_get:
            pages = list(pages_iterator(first))

        assert len(pages) == 2
        mock_get.assert_called_once_with(url="https://api.github.com/page2")
