#!/usr/bin/env python3
"""Unit tests for stale_component_handler.py."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest
import requests
import yaml

# Import the module object so we can use patch.object on it.
# String-based @patch() paths don't work because ".github" in the
# filesystem path confuses Python's resolve_name.
from .. import stale_component_handler as sch

# Also import individual functions for direct calls
from ..stale_component_handler import (
    get_issue_title,
    get_removal_pr_title,
    sanitize_branch_name,
)


class TestSanitizeBranchName:
    """Tests for sanitize_branch_name."""

    @pytest.mark.parametrize(
        "input_name, expected",
        [
            ("my-component", "my-component"),
            ("my component name", "my-component-name"),
            ("comp~name^v2", "comp-name-v2"),
            ("comp..name...test", "comp.name.test"),
            (".comp-name.", "comp-name"),
            ("comp---name", "comp-name"),
            ("My-Component", "my-component"),
            ("  My  Comp[lex]*Na?me  ", "my-comp-lex-na-me"),
            ("...", ""),
        ],
    )
    def test_sanitize(self, input_name, expected):
        """Verify branch name sanitization for various inputs."""
        assert sanitize_branch_name(input_name) == expected


class TestTitleGenerators:
    """Tests for issue and PR title generation."""

    def test_get_issue_title(self):
        """Verify issue title format."""
        assert get_issue_title("my-comp") == "Component `my-comp` needs verification"

    def test_get_removal_pr_title(self):
        """Verify removal PR title format."""
        assert get_removal_pr_title("my-comp") == "chore: Remove stale component `my-comp`"


class TestGetOwners:
    """Tests for get_owners."""

    def test_returns_approvers(self, tmp_path):
        """Return approvers list from a valid OWNERS file."""
        owners_data = {"approvers": ["alice", "bob"]}
        (tmp_path / "OWNERS").write_text(yaml.dump(owners_data))
        assert sch.get_owners(tmp_path) == ["alice", "bob"]

    def test_missing_owners_file(self, tmp_path):
        """Return empty list when OWNERS file does not exist."""
        assert sch.get_owners(tmp_path) == []

    def test_empty_owners_file(self, tmp_path):
        """Return empty list when OWNERS file is empty."""
        (tmp_path / "OWNERS").write_text("")
        assert sch.get_owners(tmp_path) == []

    def test_no_approvers_key(self, tmp_path):
        """Return empty list when OWNERS file has no approvers key."""
        (tmp_path / "OWNERS").write_text(yaml.dump({"reviewers": ["alice"]}))
        assert sch.get_owners(tmp_path) == []

    def test_malformed_yaml(self, tmp_path):
        """Return empty list when OWNERS file contains invalid YAML."""
        (tmp_path / "OWNERS").write_text("::not::valid::yaml[[[")
        assert sch.get_owners(tmp_path) == []


class TestIssueExists:
    """Tests for issue_exists."""

    def test_returns_true_when_matching_issue_found(self):
        """Return True when an open issue with the expected title exists."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"title": get_issue_title("my-comp")}]
        mock_resp.raise_for_status = MagicMock()

        with patch.object(sch.requests, "get", return_value=mock_resp):
            assert sch.issue_exists("owner/repo", "my-comp", "fake-token") is True

    def test_returns_false_when_no_match(self):
        """Return False when no open issue matches the expected title."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"title": "Some other issue"}]
        mock_resp.raise_for_status = MagicMock()

        with patch.object(sch.requests, "get", return_value=mock_resp):
            assert sch.issue_exists("owner/repo", "my-comp", "fake-token") is False

    def test_returns_true_on_api_error(self):
        """On failure, assume issue exists to prevent duplicates."""
        with patch.object(sch.requests, "get", side_effect=requests.exceptions.ConnectionError("fail")):
            assert sch.issue_exists("owner/repo", "my-comp", "fake-token") is True

    def test_no_auth_header_without_token(self):
        """Omit Authorization header when no token is provided."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()

        with patch.object(sch.requests, "get", return_value=mock_resp) as mock_get:
            sch.issue_exists("owner/repo", "my-comp", None)
            _, kwargs = mock_get.call_args
            assert "Authorization" not in kwargs["headers"]


class TestRemovalPrExists:
    """Tests for removal_pr_exists."""

    def test_returns_true_when_matching_pr_found(self):
        """Return True when an open PR with the expected title exists."""
        mock_result = MagicMock(
            stdout=json.dumps([{"title": get_removal_pr_title("my-comp")}]),
        )
        with patch.object(sch.subprocess, "run", return_value=mock_result):
            assert sch.removal_pr_exists("owner/repo", "my-comp") is True

    def test_returns_false_when_no_match(self):
        """Return False when no open PR matches the expected title."""
        mock_result = MagicMock(stdout=json.dumps([]))
        with patch.object(sch.subprocess, "run", return_value=mock_result):
            assert sch.removal_pr_exists("owner/repo", "my-comp") is False

    def test_returns_true_on_cli_failure(self):
        """On failure, assume PR exists to prevent duplicates."""
        with patch.object(sch.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "gh")):
            assert sch.removal_pr_exists("owner/repo", "my-comp") is True


class TestGetCurrentBranch:
    """Tests for get_current_branch."""

    def test_returns_branch_name(self):
        """Return the branch name when on a named branch."""
        with patch.object(sch.subprocess, "run", return_value=MagicMock(stdout="main\n")):
            assert sch.get_current_branch() == "main"

    def test_returns_none_for_detached_head(self):
        """Return None when in detached HEAD state."""
        with patch.object(sch.subprocess, "run", return_value=MagicMock(stdout="HEAD\n")):
            assert sch.get_current_branch() is None

    def test_returns_none_on_error(self):
        """Return None when git command fails."""
        with patch.object(sch.subprocess, "run", side_effect=subprocess.CalledProcessError(1, "git")):
            assert sch.get_current_branch() is None


class TestEnsureLabelsExist:
    """Tests for ensure_labels_exist."""

    def test_both_labels_exist(self):
        """Pass when both required labels exist in the repo."""
        mock_resp = MagicMock(status_code=200, raise_for_status=MagicMock())

        with patch.object(sch.requests, "get", return_value=mock_resp) as mock_get:
            assert sch.ensure_labels_exist("owner/repo", "fake-token", dry_run=False) is True
            assert mock_get.call_count == 2

    def test_missing_label_fails(self):
        """Fail when a required label is missing."""
        responses = [
            MagicMock(status_code=200, raise_for_status=MagicMock()),
            MagicMock(status_code=404),
        ]
        with patch.object(sch.requests, "get", side_effect=responses):
            assert sch.ensure_labels_exist("owner/repo", "fake-token", dry_run=False) is False

    def test_missing_label_warns_in_dry_run(self):
        """Warn but pass when a label is missing in dry-run mode."""
        responses = [
            MagicMock(status_code=200, raise_for_status=MagicMock()),
            MagicMock(status_code=404),
        ]
        with patch.object(sch.requests, "get", side_effect=responses):
            assert sch.ensure_labels_exist("owner/repo", "fake-token", dry_run=True) is True

    def test_api_error_fails(self):
        """Fail when the GitHub API request errors out."""
        with patch.object(sch.requests, "get", side_effect=requests.exceptions.ConnectionError("fail")):
            assert sch.ensure_labels_exist("owner/repo", "fake-token", dry_run=False) is False


class TestCreateIssue:
    """Tests for create_issue."""

    COMPONENT = {
        "name": "my-comp",
        "path": "components/category/my-comp",
        "last_verified": "2024-01-01",
        "age_days": 300,
    }

    def test_dry_run_returns_true(self, tmp_path):
        """Return True without calling the API in dry-run mode."""
        comp_dir = tmp_path / "components" / "category" / "my-comp"
        comp_dir.mkdir(parents=True)
        assert sch.create_issue("owner/repo", self.COMPONENT, tmp_path, "fake-token", dry_run=True) is True

    def test_success(self, tmp_path):
        """Return True when issue creation succeeds."""
        comp_dir = tmp_path / "components" / "category" / "my-comp"
        comp_dir.mkdir(parents=True)

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"html_url": "https://github.com/owner/repo/issues/1"}
        mock_resp.raise_for_status = MagicMock()

        with (
            patch.object(sch.requests, "post", return_value=mock_resp) as mock_post,
            patch.object(sch, "create_issue_body", return_value="body text"),
        ):
            assert sch.create_issue("owner/repo", self.COMPONENT, tmp_path, "fake-token", dry_run=False) is True
            mock_post.assert_called_once()

    def test_api_failure_returns_false(self, tmp_path):
        """Return False when the API request fails."""
        comp_dir = tmp_path / "components" / "category" / "my-comp"
        comp_dir.mkdir(parents=True)

        with (
            patch.object(sch.requests, "post", side_effect=requests.exceptions.HTTPError("403")),
            patch.object(sch, "create_issue_body", return_value="body text"),
        ):
            assert sch.create_issue("owner/repo", self.COMPONENT, tmp_path, "fake-token", dry_run=False) is False


class TestCreateRemovalPrCleanup:
    """Tests for create_removal_pr orphaned branch cleanup."""

    COMPONENT = {
        "name": "my-comp",
        "path": "components/category/my-comp",
        "last_verified": "2024-01-01",
        "age_days": 400,
    }

    def test_dry_run_returns_true(self, tmp_path):
        """Return True without side effects in dry-run mode."""
        comp_dir = tmp_path / self.COMPONENT["path"]
        comp_dir.mkdir(parents=True)
        assert sch.create_removal_pr("owner/repo", self.COMPONENT, tmp_path, dry_run=True) is True

    def test_cleans_up_remote_branch_on_pr_failure(self, tmp_path):
        """When push succeeds but gh pr create fails, the remote branch should be deleted."""
        comp_dir = tmp_path / self.COMPONENT["path"]
        comp_dir.mkdir(parents=True)

        def side_effect(cmd, **kwargs):
            cmd_list = cmd if isinstance(cmd, list) else [cmd]
            # gh repo view (get default branch)
            if "gh" in cmd_list and "repo" in cmd_list and "view" in cmd_list:
                return MagicMock(stdout="main\n")
            # gh pr create – simulate failure
            if "gh" in cmd_list and "pr" in cmd_list and "create" in cmd_list:
                raise subprocess.CalledProcessError(1, cmd, stderr="PR creation failed")
            # git push --delete (cleanup) – should succeed
            if "push" in cmd_list and "--delete" in cmd_list:
                return MagicMock(returncode=0)
            # All other git commands succeed
            return MagicMock(returncode=0)

        with (
            patch.object(sch.subprocess, "run", side_effect=side_effect) as mock_run,
            patch.object(sch, "get_current_branch", return_value="main"),
            patch.object(sch, "get_owners", return_value=["alice"]),
        ):
            result = sch.create_removal_pr("owner/repo", self.COMPONENT, tmp_path, dry_run=False)
            assert result is False

            # Verify cleanup was attempted
            delete_calls = [c for c in mock_run.call_args_list if "--delete" in (c[0][0] if c[0] else [])]
            assert len(delete_calls) == 1
            assert "remove-stale-my-comp" in delete_calls[0][0][0]

    def test_no_cleanup_when_push_fails(self, tmp_path):
        """When push itself fails, no remote cleanup should be attempted."""
        comp_dir = tmp_path / self.COMPONENT["path"]
        comp_dir.mkdir(parents=True)

        def side_effect(cmd, **kwargs):
            cmd_list = cmd if isinstance(cmd, list) else [cmd]
            if "gh" in cmd_list and "repo" in cmd_list and "view" in cmd_list:
                return MagicMock(stdout="main\n")
            # git push – simulate failure
            if "push" in cmd_list and "-u" in cmd_list:
                raise subprocess.CalledProcessError(1, cmd, stderr="push failed")
            return MagicMock(returncode=0)

        with (
            patch.object(sch.subprocess, "run", side_effect=side_effect) as mock_run,
            patch.object(sch, "get_current_branch", return_value="main"),
            patch.object(sch, "get_owners", return_value=[]),
        ):
            result = sch.create_removal_pr("owner/repo", self.COMPONENT, tmp_path, dry_run=False)
            assert result is False

            # No --delete call should have been made
            delete_calls = [c for c in mock_run.call_args_list if "--delete" in (c[0][0] if c[0] else [])]
            assert len(delete_calls) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
