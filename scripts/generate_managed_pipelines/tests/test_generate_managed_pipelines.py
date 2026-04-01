"""Tests for ManagedPipelineEntry and collect_managed_pipelines."""

from pathlib import Path

import pytest

from ..generate_managed_pipelines import (
    METADATA_STABILITY_VALUES,
    STABILITY_TO_MANAGED_DISPLAY,
    ManagedPipelineMetadataError,
    collect_managed_pipelines,
    managed_pipeline_entry_from_dir,
)


def test_from_managed_pipeline_dir_success(tmp_path: Path):
    """Build entry when name, stability, and path are valid."""
    repo = tmp_path
    pipe_dir = repo / "pipelines" / "training" / "p"
    pipe_dir.mkdir(parents=True)
    (pipe_dir / "pipeline.py").write_text("from kfp import dsl\n\n@dsl.pipeline\ndef p():\n    pass\n")

    metadata = {
        "name": "my_pipeline",
        "stability": "alpha",
        "managed": True,
    }
    entry = managed_pipeline_entry_from_dir(
        dir_path=pipe_dir,
        repo_root=repo,
        metadata=metadata,
    )
    assert entry.name == "my_pipeline"
    assert entry.stability == "Development Preview"
    assert entry.path == "pipelines/training/p/pipeline.py"
    assert isinstance(entry.description, str)
    assert entry.description == ""


def test_from_managed_pipeline_dir_success_with_pipeline_description(tmp_path: Path):
    """Build entry with description extracted from @dsl.pipeline(description=...)."""
    repo = tmp_path
    pipe_dir = repo / "pipelines" / "training" / "p"
    pipe_dir.mkdir(parents=True)
    (pipe_dir / "pipeline.py").write_text(
        'from kfp import dsl\n\n@dsl.pipeline(description="keyword description")\ndef p():\n    pass\n'
    )

    metadata = {
        "name": "my_pipeline",
        "stability": "alpha",
        "managed": True,
    }
    entry = managed_pipeline_entry_from_dir(
        dir_path=pipe_dir,
        repo_root=repo,
        metadata=metadata,
    )
    assert entry.description == "keyword description"


@pytest.mark.parametrize(
    ("metadata", "reason"),
    [
        ({}, "empty metadata"),
        ({"name": "x"}, "missing stability"),
        ({"stability": "alpha"}, "missing name"),
        ({"name": "", "stability": "alpha"}, "empty name"),
        ({"name": "x", "stability": ""}, "empty stability"),
        ({"name": "x", "stability": "omega"}, "invalid stability"),
        ({"name": "x", "stability": "experimental"}, "experimental disallowed"),
        ({"name": 1, "stability": "alpha"}, "non-str name"),
    ],
)
def test_from_managed_pipeline_dir_invalid_metadata_raises(tmp_path: Path, metadata: dict, reason: str):
    """Invalid metadata raises ManagedPipelineMetadataError."""
    _ = reason
    repo = tmp_path
    pipe_dir = repo / "pipelines" / "training" / "p"
    pipe_dir.mkdir(parents=True)
    (pipe_dir / "pipeline.py").touch()

    with pytest.raises(ManagedPipelineMetadataError):
        managed_pipeline_entry_from_dir(
            dir_path=pipe_dir,
            repo_root=repo,
            metadata=metadata,
        )


@pytest.mark.parametrize(
    ("metadata_stability", "expected_display"),
    [
        ("alpha", "Development Preview"),
        ("beta", "Technology Preview"),
        ("stable", "General Availability"),
    ],
)
def test_stability_mapped_to_display_labels(tmp_path: Path, metadata_stability: str, expected_display: str):
    """JSON stability uses product labels, not metadata keywords."""
    repo = tmp_path
    pipe_dir = repo / "pipelines" / "x" / "p"
    pipe_dir.mkdir(parents=True)
    (pipe_dir / "pipeline.py").touch()

    entry = managed_pipeline_entry_from_dir(
        dir_path=pipe_dir,
        repo_root=repo,
        metadata={"name": "n", "stability": metadata_stability, "managed": True},
    )
    assert entry.stability == expected_display


def test_metadata_stability_values_match_validate_metadata():
    """Keep in sync with scripts/validate_metadata STABILITY_OPTIONS."""
    assert METADATA_STABILITY_VALUES == frozenset({"experimental", "alpha", "beta", "stable"})
    assert set(STABILITY_TO_MANAGED_DISPLAY) == {"alpha", "beta", "stable"}


def test_collect_managed_pipelines_missing_pipelines_root_raises(tmp_path: Path):
    """Missing pipelines/ must not yield an empty list silently."""
    repo = tmp_path
    with pytest.raises(FileNotFoundError, match="pipelines directory not found"):
        collect_managed_pipelines(repo)


def test_collect_managed_pipelines_skips_non_mapping_metadata(tmp_path: Path):
    """Non-mapping YAML content should be ignored safely."""
    repo = tmp_path
    pipe_dir = repo / "pipelines" / "training" / "p"
    pipe_dir.mkdir(parents=True)
    (pipe_dir / "pipeline.py").touch()
    (pipe_dir / "metadata.yaml").write_text("- not-a-mapping\n", encoding="utf-8")

    assert collect_managed_pipelines(repo) == []
