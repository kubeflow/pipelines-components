"""Unit tests for metadata utilities."""

from __future__ import annotations

from pathlib import Path

import yaml

from .. import metadata_utils


def _write_metadata(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_metadata_should_run_honors_flag() -> None:
    """Targets with compile_check disabled are skipped unless include_flagless is true."""
    metadata = {"ci": {"compile_check": False}}
    assert metadata_utils.metadata_should_run(metadata, include_flagless=False) is False
    assert metadata_utils.metadata_should_run(metadata, include_flagless=True) is False

    flagless_metadata = {}
    assert metadata_utils.metadata_should_run(flagless_metadata, include_flagless=False) is False
    assert metadata_utils.metadata_should_run(flagless_metadata, include_flagless=True) is True


def test_validate_dependencies_detects_invalid_version() -> None:
    """Invalid specifiers produce dependency validation errors."""
    metadata = {
        "dependencies": {
            "kubeflow": [
                {"name": "Pipelines", "version": ">>=bad"},
            ]
        }
    }
    errors, warnings = metadata_utils.validate_dependencies(metadata)
    assert warnings == []
    assert len(errors) == 1
    assert "invalid version specifier" in errors[0]


def test_create_metadata_targets_filters_and_validates(tmp_path: Path) -> None:
    """Targets are filtered by flag and path, and missing modules are skipped."""
    repo_root = tmp_path
    comp_dir = repo_root / "components" / "training" / "sample_component"
    comp_dir.mkdir(parents=True)
    (comp_dir / "__init__.py").write_text("", encoding="utf-8")
    component_file = comp_dir / "component.py"
    component_file.write_text(
        "from kfp import dsl\n\n@dsl.component\ndef sample_op() -> int:\n    return 1\n",
        encoding="utf-8",
    )

    metadata_path = comp_dir / "metadata.yaml"
    _write_metadata(
        metadata_path,
        {
            "name": "sample_component",
            "ci": {"compile_check": True},
            "dependencies": {},
        },
    )

    discovered = [(metadata_path, "component")]
    targets = metadata_utils.create_metadata_targets(
        discovered,
        include_flagless=False,
        path_filters=[],
        repo_root=repo_root,
    )
    assert len(targets) == 1

    # Compile check disabled should skip target unless include_flagless=True.
    _write_metadata(metadata_path, {"ci": {"compile_check": False}})
    targets = metadata_utils.create_metadata_targets(
        discovered,
        include_flagless=False,
        path_filters=[],
        repo_root=repo_root,
    )
    assert targets == []

    targets = metadata_utils.create_metadata_targets(
        discovered,
        include_flagless=True,
        path_filters=[],
        repo_root=repo_root,
    )
    assert targets == []

    # Restore metadata and ensure path filters operate on directories.
    _write_metadata(metadata_path, {"ci": {"compile_check": True}})
    targets = metadata_utils.create_metadata_targets(
        discovered,
        include_flagless=False,
        path_filters=[str(repo_root / "components" / "training")],
        repo_root=repo_root,
    )
    assert len(targets) == 1

    targets = metadata_utils.create_metadata_targets(
        discovered,
        include_flagless=False,
        path_filters=[str(repo_root / "pipelines")],
        repo_root=repo_root,
    )
    assert targets == []

    # If module file is missing, the target should be skipped.
    component_file.unlink()
    targets = metadata_utils.create_metadata_targets(
        discovered,
        include_flagless=False,
        path_filters=[],
        repo_root=repo_root,
    )
    assert targets == []
