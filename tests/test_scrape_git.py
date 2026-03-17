import pytest
from unittest.mock import patch, MagicMock
from scrape_git.main import detect_source, parse_github_url, resolve_gitlab_project_id


class TestDetectSource:
    def test_github(self):
        assert detect_source("https://github.com/qemu/qemu") == "github"

    def test_gitlab(self):
        assert detect_source("https://gitlab.com/qemu-project/qemu") == "gitlab"

    def test_github_with_path(self):
        assert detect_source("https://github.com/owner/repo/issues") == "github"

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Cannot detect source"):
            detect_source("https://bitbucket.org/owner/repo")

    def test_no_scheme_raises(self):
        with pytest.raises(ValueError):
            detect_source("not-a-url")


class TestParseGithubUrl:
    def test_basic(self):
        assert parse_github_url("https://github.com/qemu/qemu") == "qemu/qemu"

    def test_with_trailing_path(self):
        assert parse_github_url("https://github.com/owner/repo/issues") == "owner/repo"

    def test_trailing_slash(self):
        assert parse_github_url("https://github.com/owner/repo/") == "owner/repo"

    def test_too_short_raises(self):
        with pytest.raises(ValueError, match="Invalid GitHub URL"):
            parse_github_url("https://github.com/owner")


class TestResolveGitlabProjectId:
    def test_numeric_in_url(self):
        assert resolve_gitlab_project_id("https://gitlab.com/api/v4/projects/11167699") == 11167699

    def test_numeric_in_path(self):
        assert resolve_gitlab_project_id("https://gitlab.com/projects/12345") == 12345

    def test_resolves_via_api(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": 11167699}
        mock_response.raise_for_status = MagicMock()

        with patch("scrape_git.main.get", return_value=mock_response) as mock_get:
            result = resolve_gitlab_project_id("https://gitlab.com/qemu-project/qemu")

        assert result == 11167699
        mock_get.assert_called_once_with("https://gitlab.com/api/v4/projects/qemu-project%2Fqemu")
