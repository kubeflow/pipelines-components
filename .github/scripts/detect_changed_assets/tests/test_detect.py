#!/usr/bin/env python3
"""Unit tests for detect.py script."""

from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest

from ..detect import ChangeDetector, GitClient


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


class TestParseChangedFiles:
    """Test the ChangeDetector._parse_changed_files method."""

    def _parse(self, files: list[str]) -> tuple[list[str], list[str]]:
        """Helper to call _parse_changed_files on a ChangeDetector."""
        detector = ChangeDetector(git_client=MagicMock())
        return detector._parse_changed_files(files)

    def test_direct_component(self):
        """Direct component path is detected correctly."""
        components, pipelines = self._parse(
            [
                "components/training/my_trainer/component.py",
            ]
        )
        assert components == ["components/training/my_trainer"]
        assert pipelines == []

    def test_direct_pipeline(self):
        """Direct pipeline path is detected correctly."""
        components, pipelines = self._parse(
            [
                "pipelines/training/my_pipeline/pipeline.py",
            ]
        )
        assert components == []
        assert pipelines == ["pipelines/training/my_pipeline"]

    def test_subcategory_component(self):
        """Subcategory component path outputs the leaf asset, not the subcategory."""
        components, pipelines = self._parse(
            [
                "components/training/sklearn_trainer/logistic_regression/component.py",
            ]
        )
        assert components == ["components/training/sklearn_trainer/logistic_regression"]
        assert pipelines == []

    def test_subcategory_pipeline(self):
        """Subcategory pipeline path outputs the leaf asset, not the subcategory."""
        components, pipelines = self._parse(
            [
                "pipelines/training/ml_workflows/batch_training/pipeline.py",
            ]
        )
        assert components == []
        assert pipelines == ["pipelines/training/ml_workflows/batch_training"]

    def test_subcategory_level_file_gives_subcategory(self):
        """A file at the subcategory level (e.g. OWNERS) returns the subcategory dir."""
        components, _ = self._parse(
            [
                "components/training/sklearn_trainer/OWNERS",
            ]
        )
        assert components == ["components/training/sklearn_trainer"]

    def test_mixed_direct_and_subcategory(self):
        """Mix of direct and subcategory paths are all detected correctly."""
        components, pipelines = self._parse(
            [
                "components/training/my_trainer/component.py",
                "components/training/sklearn_trainer/logistic_regression/component.py",
                "pipelines/etl/daily_ingest/pipeline.py",
                "pipelines/etl/batch_flows/nightly/pipeline.py",
            ]
        )
        assert components == [
            "components/training/my_trainer",
            "components/training/sklearn_trainer/logistic_regression",
        ]
        assert pipelines == [
            "pipelines/etl/batch_flows/nightly",
            "pipelines/etl/daily_ingest",
        ]

    def test_deduplication(self):
        """Multiple files in the same asset produce one entry."""
        components, _ = self._parse(
            [
                "components/training/sklearn_trainer/logistic_regression/component.py",
                "components/training/sklearn_trainer/logistic_regression/metadata.yaml",
                "components/training/sklearn_trainer/logistic_regression/tests/test_unit.py",
            ]
        )
        assert components == ["components/training/sklearn_trainer/logistic_regression"]

    def test_direct_component_tests_subdir_not_treated_as_subcategory(self):
        """A file under tests/ of a direct component resolves to the component."""
        components, _ = self._parse(
            [
                "components/training/my_trainer/tests/test_unit.py",
            ]
        )
        assert components == ["components/training/my_trainer"]

    def test_direct_pipeline_tests_subdir_not_treated_as_subcategory(self):
        """A file under tests/ of a direct pipeline resolves to the pipeline."""
        _, pipelines = self._parse(
            [
                "pipelines/etl/daily_ingest/tests/test_pipeline.py",
            ]
        )
        assert pipelines == ["pipelines/etl/daily_ingest"]

    def test_direct_component_shared_subdir_not_treated_as_subcategory(self):
        """A file under shared/ of a direct component resolves to the component."""
        components, _ = self._parse(
            [
                "components/training/my_trainer/shared/utils.py",
            ]
        )
        assert components == ["components/training/my_trainer"]

    def test_non_asset_paths_ignored(self):
        """Paths outside components/ and pipelines/ are ignored."""
        components, pipelines = self._parse(
            [
                "scripts/lib/discovery.py",
                "docs/CONTRIBUTING.md",
                ".github/workflows/ci.yml",
            ]
        )
        assert components == []
        assert pipelines == []

    def test_multiple_subcategory_assets(self):
        """Multiple assets in the same subcategory are listed separately."""
        components, _ = self._parse(
            [
                "components/training/sklearn_trainer/logistic_regression/component.py",
                "components/training/sklearn_trainer/random_forest/component.py",
            ]
        )
        assert components == [
            "components/training/sklearn_trainer/logistic_regression",
            "components/training/sklearn_trainer/random_forest",
        ]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
