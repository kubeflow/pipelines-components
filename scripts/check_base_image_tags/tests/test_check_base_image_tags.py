"""Tests for check_base_image_tags script."""

from pathlib import Path

from ...lib.base_image import check_base_image_tags

IMAGE_PREFIX = "ghcr.io/kubeflow/pipelines-components"


def _write_component_asset(tmp_path: Path, base_image: str | None) -> Path:
    asset_dir = tmp_path / "components" / "training" / "my_component"
    asset_dir.mkdir(parents=True)
    component_file = asset_dir / "component.py"

    decorator = "@dsl.component" if base_image is None else f'@dsl.component(base_image="{base_image}")'
    component_file.write_text(
        f"""from kfp import dsl

{decorator}
def my_component() -> str:
    return "ok"
"""
    )
    return component_file


def _write_pipeline_asset(tmp_path: Path, base_image: str) -> Path:
    asset_dir = tmp_path / "pipelines" / "training" / "my_pipeline"
    asset_dir.mkdir(parents=True)
    pipeline_file = asset_dir / "pipeline.py"
    pipeline_file.write_text(
        f"""from kfp import dsl

@dsl.component(base_image="{base_image}")
def inner() -> str:
    return "ok"

@dsl.pipeline
def my_pipeline():
    inner()
"""
    )
    return pipeline_file


def _write_bad_component_asset(tmp_path: Path) -> Path:
    asset_dir = tmp_path / "components" / "training" / "bad_component"
    asset_dir.mkdir(parents=True)
    component_file = asset_dir / "component.py"
    component_file.write_text("def oops(:\n  pass\n")
    return component_file


class TestCheckBaseImageTags:
    """Integration tests for compile-based check_base_image_tags."""

    def test_all_valid_returns_true(self, tmp_path: Path):
        """Returns all_valid=True when compiled images under the prefix use :main."""
        _write_component_asset(tmp_path, f"{IMAGE_PREFIX}-test:main")

        all_valid, results = check_base_image_tags([str(tmp_path / "components")], IMAGE_PREFIX, "main")

        assert all_valid is True
        assert len(results) == 1
        assert results[0]["status"] == "valid"

    def test_invalid_tag_returns_false(self, tmp_path: Path):
        """Returns all_valid=False when a compiled image under the prefix does not use :main."""
        _write_component_asset(tmp_path, f"{IMAGE_PREFIX}-test:sha123")

        all_valid, results = check_base_image_tags([str(tmp_path / "components")], IMAGE_PREFIX, "main")

        assert all_valid is False
        assert len(results) == 1
        assert results[0]["status"] == "invalid"
        assert results[0]["found"] == f"{IMAGE_PREFIX}-test:sha123"

    def test_ignores_non_prefix_images(self, tmp_path: Path):
        """Ignores images that don't match the configured prefix."""
        _write_component_asset(tmp_path, "python:3.11")

        all_valid, results = check_base_image_tags([str(tmp_path / "components")], IMAGE_PREFIX, "main")

        assert all_valid is True
        assert results == []

    def test_nonexistent_directory_is_valid(self, tmp_path: Path):
        """Treats nonexistent directories as valid (no assets found)."""
        all_valid, results = check_base_image_tags([str(tmp_path / "nonexistent")], IMAGE_PREFIX, "main")

        assert all_valid is True
        assert results == []

    def test_scans_subdirectories(self, tmp_path: Path):
        """Finds component.py assets in nested subdirectories."""
        _write_component_asset(tmp_path, f"{IMAGE_PREFIX}-training:main")

        all_valid, results = check_base_image_tags([str(tmp_path / "components")], IMAGE_PREFIX, "main")

        assert all_valid is True
        assert len(results) == 1

    def test_multiple_directories(self, tmp_path: Path):
        """Aggregates results across multiple directories."""
        _write_component_asset(tmp_path, f"{IMAGE_PREFIX}-a:main")
        _write_pipeline_asset(tmp_path, f"{IMAGE_PREFIX}-b:main")

        all_valid, results = check_base_image_tags(
            [str(tmp_path / "components"), str(tmp_path / "pipelines")], IMAGE_PREFIX, "main"
        )

        assert all_valid is True
        assert len(results) == 2

    def test_compile_failure_is_invalid(self, tmp_path: Path):
        """Returns all_valid=False and reports an error when compilation fails."""
        _write_bad_component_asset(tmp_path)

        all_valid, results = check_base_image_tags([str(tmp_path / "components")], IMAGE_PREFIX, "main")

        assert all_valid is False
        assert len(results) == 1
        assert results[0]["status"] == "invalid"
        assert "error" in results[0]

    def test_compile_failure_does_not_stop_other_assets(self, tmp_path: Path):
        """Continues checking other assets even if one asset fails to compile."""
        _write_component_asset(tmp_path, f"{IMAGE_PREFIX}-ok:main")

        _write_bad_component_asset(tmp_path)

        all_valid, results = check_base_image_tags([str(tmp_path / "components")], IMAGE_PREFIX, "main")

        assert all_valid is False
        statuses = [r["status"] for r in results]
        assert statuses.count("valid") == 1
        assert statuses.count("invalid") == 1

    def test_custom_expected_tag(self, tmp_path: Path):
        """Validates against a custom expected tag (e.g., for release branches)."""
        _write_component_asset(tmp_path, f"{IMAGE_PREFIX}-test:v1.11.0")

        all_valid, results = check_base_image_tags([str(tmp_path / "components")], IMAGE_PREFIX, expected_tag="v1.11.0")

        assert all_valid is True
        assert len(results) == 1
        assert results[0]["status"] == "valid"

    def test_custom_expected_tag_fails_on_main(self, tmp_path: Path):
        """Fails when image uses :main but release tag is expected."""
        _write_component_asset(tmp_path, f"{IMAGE_PREFIX}-test:main")

        all_valid, results = check_base_image_tags([str(tmp_path / "components")], IMAGE_PREFIX, expected_tag="v1.11.0")

        assert all_valid is False
        assert results[0]["status"] == "invalid"
        assert results[0]["expected"] == f"{IMAGE_PREFIX}-<name>:v1.11.0"
