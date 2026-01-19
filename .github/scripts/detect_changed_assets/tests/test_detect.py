#!/usr/bin/env python3
"""Unit tests for detect.py script."""

from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest

from ..detect import GitClient


class TestGitClientFetchBranch:
    """Test the GitClient.fetch_branch method."""

    def test_fetch_branch_skips_non_origin_refs(self):
        """Test that fetch_branch skips refs not starting with origin/."""
        client = GitClient()
        client.run = MagicMock()

        # These should not trigger any fetch
        client.fetch_branch("main")
        client.fetch_branch("HEAD")

        client.run.assert_not_called()

    def test_fetch_branch_skips_origin_head(self):
        """Test that fetch_branch skips origin/HEAD.

        origin/HEAD is a symbolic reference that exists after cloning and
        points to the default branch. It cannot be fetched like a regular
        branch since 'HEAD' is not a valid branch name on the remote.
        """
        client = GitClient()
        client.run = MagicMock()

        client.fetch_branch("origin/HEAD")

        client.run.assert_not_called()

    def test_fetch_branch_fetches_origin_main(self):
        """Test that fetch_branch fetches origin/main."""
        client = GitClient()
        client.run = MagicMock(return_value="")

        client.fetch_branch("origin/main")

        # Should attempt full fetch first
        client.run.assert_any_call(
            ["fetch", "origin", "main:refs/remotes/origin/main"],
            check=False,
        )

    def test_fetch_branch_fetches_release_branches(self):
        """Test that fetch_branch fetches release branches like origin/release-1.11."""
        client = GitClient()
        client.run = MagicMock(return_value="")

        client.fetch_branch("origin/release-1.11")

        # Should attempt full fetch first
        client.run.assert_any_call(
            ["fetch", "origin", "release-1.11:refs/remotes/origin/release-1.11"],
            check=False,
        )

    def test_fetch_branch_falls_back_to_shallow_fetch(self):
        """Test that fetch_branch falls back to shallow fetch when full fetch returns empty."""
        client = GitClient()
        client.run = MagicMock(return_value="")

        client.fetch_branch("origin/main")

        # Should try full fetch, then shallow fetch
        expected_calls = [
            call(["fetch", "origin", "main:refs/remotes/origin/main"], check=False),
            call(["fetch", "--depth=100", "origin", "main"], check=False),
        ]
        client.run.assert_has_calls(expected_calls)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
