"""Tests for discovery module."""

from pathlib import Path

import pytest

from ..discovery import (
    build_component_asset,
    build_pipeline_asset,
    discover_assets,
    find_assets_with_metadata,
    get_all_assets_with_metadata,
)


def _make_component(base: Path, category: str, name: str, *, subcategory: str | None = None) -> Path:
    """Create a minimal component directory structure and return the component.py path."""
    if subcategory:
        comp_dir = base / "components" / category / subcategory / name
    else:
        comp_dir = base / "components" / category / name
    comp_dir.mkdir(parents=True, exist_ok=True)
    comp_file = comp_dir / "component.py"
    comp_file.write_text('"""Component."""\n')
    return comp_file


def _make_pipeline(base: Path, category: str, name: str, *, subcategory: str | None = None) -> Path:
    """Create a minimal pipeline directory structure and return the pipeline.py path."""
    if subcategory:
        pipe_dir = base / "pipelines" / category / subcategory / name
    else:
        pipe_dir = base / "pipelines" / category / name
    pipe_dir.mkdir(parents=True, exist_ok=True)
    pipe_file = pipe_dir / "pipeline.py"
    pipe_file.write_text('"""Pipeline."""\n')
    return pipe_file


def _make_metadata(base: Path, asset_type: str, category: str, name: str, *, subcategory: str | None = None) -> Path:
    """Create a minimal metadata.yaml in an asset directory."""
    if subcategory:
        asset_dir = base / asset_type / category / subcategory / name
    else:
        asset_dir = base / asset_type / category / name
    asset_dir.mkdir(parents=True, exist_ok=True)
    meta = asset_dir / "metadata.yaml"
    meta.write_text("name: test\n")
    return meta


class TestDiscoverAssets:
    """Tests for discover_assets()."""

    def test_returns_empty_for_nonexistent_dir(self, tmp_path: Path):
        """Return empty list when base_dir does not exist."""
        result = discover_assets(tmp_path / "nonexistent", "component")
        assert result == []

    def test_discovers_direct_component(self, tmp_path: Path):
        """Discover a component directly under a category."""
        _make_component(tmp_path, "training", "my_trainer")

        result = discover_assets(tmp_path / "components", "component")

        assert len(result) == 1
        assert result[0]["category"] == "training"
        assert result[0]["name"] == "my_trainer"
        assert result[0]["subcategory"] is None
        assert result[0]["path"].name == "component.py"

    def test_discovers_direct_pipeline(self, tmp_path: Path):
        """Discover a pipeline directly under a category."""
        _make_pipeline(tmp_path, "training", "my_pipeline")

        result = discover_assets(tmp_path / "pipelines", "pipeline")

        assert len(result) == 1
        assert result[0]["category"] == "training"
        assert result[0]["name"] == "my_pipeline"
        assert result[0]["subcategory"] is None
        assert result[0]["path"].name == "pipeline.py"

    def test_discovers_subcategory_component(self, tmp_path: Path):
        """Discover a component nested under a subcategory."""
        _make_component(tmp_path, "training", "logistic_regression", subcategory="sklearn_trainer")

        result = discover_assets(tmp_path / "components", "component")

        assert len(result) == 1
        assert result[0]["category"] == "training"
        assert result[0]["subcategory"] == "sklearn_trainer"
        assert result[0]["name"] == "logistic_regression"
        assert result[0]["path"].name == "component.py"

    def test_discovers_subcategory_pipeline(self, tmp_path: Path):
        """Discover a pipeline nested under a subcategory."""
        _make_pipeline(tmp_path, "training", "batch_training", subcategory="ml_workflows")

        result = discover_assets(tmp_path / "pipelines", "pipeline")

        assert len(result) == 1
        assert result[0]["category"] == "training"
        assert result[0]["subcategory"] == "ml_workflows"
        assert result[0]["name"] == "batch_training"
        assert result[0]["path"].name == "pipeline.py"

    def test_discovers_mixed_direct_and_subcategory(self, tmp_path: Path):
        """Discover both direct and subcategory assets in the same category."""
        _make_component(tmp_path, "training", "simple_trainer")
        _make_component(tmp_path, "training", "logistic_regression", subcategory="sklearn_trainer")
        _make_component(tmp_path, "training", "random_forest", subcategory="sklearn_trainer")

        result = discover_assets(tmp_path / "components", "component")

        assert len(result) == 3
        names = {(a["subcategory"], a["name"]) for a in result}
        assert names == {
            (None, "simple_trainer"),
            ("sklearn_trainer", "logistic_regression"),
            ("sklearn_trainer", "random_forest"),
        }
        # All should share the same category
        assert all(a["category"] == "training" for a in result)

    def test_discovers_across_multiple_categories(self, tmp_path: Path):
        """Discover assets across multiple categories with and without subcategories."""
        _make_component(tmp_path, "training", "my_trainer")
        _make_component(tmp_path, "evaluation", "accuracy", subcategory="metrics")

        result = discover_assets(tmp_path / "components", "component")

        assert len(result) == 2
        categories = {a["category"] for a in result}
        assert categories == {"training", "evaluation"}

    def test_ignores_hidden_and_underscore_dirs(self, tmp_path: Path):
        """Skip directories starting with . or _."""
        # Hidden category
        comp_dir = tmp_path / "components" / ".hidden" / "foo"
        comp_dir.mkdir(parents=True)
        (comp_dir / "component.py").write_text("")

        # Underscore category
        comp_dir2 = tmp_path / "components" / "_private" / "bar"
        comp_dir2.mkdir(parents=True)
        (comp_dir2 / "component.py").write_text("")

        # Hidden item inside valid category
        cat = tmp_path / "components" / "training"
        cat.mkdir(parents=True)
        hidden_item = cat / ".internal"
        hidden_item.mkdir()
        (hidden_item / "component.py").write_text("")

        # Underscore subcategory item
        under_sub = cat / "sklearn" / "_hidden_comp"
        under_sub.mkdir(parents=True)
        (under_sub / "component.py").write_text("")

        result = discover_assets(tmp_path / "components", "component")
        assert result == []

    def test_ignores_dirs_without_asset_file(self, tmp_path: Path):
        """Directories without component.py or pipeline.py are silently skipped."""
        # Category with a subdir that has no component.py
        empty_dir = tmp_path / "components" / "training" / "incomplete"
        empty_dir.mkdir(parents=True)

        result = discover_assets(tmp_path / "components", "component")
        assert result == []


class TestFindAssetsWithMetadata:
    """Tests for find_assets_with_metadata()."""

    def test_finds_direct_component_metadata(self, tmp_path: Path):
        """Find metadata.yaml in a direct component directory."""
        _make_metadata(tmp_path, "components", "training", "my_trainer")

        result = find_assets_with_metadata("components", tmp_path)

        assert result == ["components/training/my_trainer"]

    def test_finds_subcategory_component_metadata(self, tmp_path: Path):
        """Find metadata.yaml in a subcategory component directory."""
        _make_metadata(tmp_path, "components", "training", "logistic_regression", subcategory="sklearn_trainer")

        result = find_assets_with_metadata("components", tmp_path)

        assert result == ["components/training/sklearn_trainer/logistic_regression"]

    def test_finds_direct_pipeline_metadata(self, tmp_path: Path):
        """Find metadata.yaml in a direct pipeline directory."""
        _make_metadata(tmp_path, "pipelines", "training", "my_pipeline")

        result = find_assets_with_metadata("pipelines", tmp_path)

        assert result == ["pipelines/training/my_pipeline"]

    def test_finds_subcategory_pipeline_metadata(self, tmp_path: Path):
        """Find metadata.yaml in a subcategory pipeline directory."""
        _make_metadata(tmp_path, "pipelines", "training", "batch_training", subcategory="ml_workflows")

        result = find_assets_with_metadata("pipelines", tmp_path)

        assert result == ["pipelines/training/ml_workflows/batch_training"]

    def test_finds_mixed_metadata(self, tmp_path: Path):
        """Find both direct and subcategory metadata in same category."""
        _make_metadata(tmp_path, "components", "training", "simple_trainer")
        _make_metadata(tmp_path, "components", "training", "logistic_regression", subcategory="sklearn_trainer")

        result = find_assets_with_metadata("components", tmp_path)

        assert len(result) == 2
        assert "components/training/simple_trainer" in result
        assert "components/training/sklearn_trainer/logistic_regression" in result

    def test_returns_empty_for_missing_dir(self, tmp_path: Path):
        """Return empty list when asset_type directory does not exist."""
        result = find_assets_with_metadata("components", tmp_path)
        assert result == []

    def test_ignores_hidden_dirs(self, tmp_path: Path):
        """Skip hidden and underscore directories."""
        meta_dir = tmp_path / "components" / ".hidden" / "foo"
        meta_dir.mkdir(parents=True)
        (meta_dir / "metadata.yaml").write_text("name: test\n")

        result = find_assets_with_metadata("components", tmp_path)
        assert result == []


class TestGetAllAssetsWithMetadata:
    """Tests for get_all_assets_with_metadata()."""

    def test_combines_components_and_pipelines(self, tmp_path: Path):
        """Return metadata from both components and pipelines."""
        _make_metadata(tmp_path, "components", "training", "my_comp")
        _make_metadata(tmp_path, "pipelines", "training", "my_pipe")

        result = get_all_assets_with_metadata(tmp_path)

        assert len(result) == 2
        assert "components/training/my_comp" in result
        assert "pipelines/training/my_pipe" in result

    def test_includes_subcategory_assets(self, tmp_path: Path):
        """Return subcategory metadata from both asset types."""
        _make_metadata(tmp_path, "components", "training", "lr", subcategory="sklearn")
        _make_metadata(tmp_path, "pipelines", "training", "batch", subcategory="ml_wf")

        result = get_all_assets_with_metadata(tmp_path)

        assert "components/training/sklearn/lr" in result
        assert "pipelines/training/ml_wf/batch" in result


class TestBuildComponentAsset:
    """Tests for build_component_asset()."""

    def test_direct_component(self, tmp_path: Path):
        """Build asset dict for a direct category component."""
        comp_file = _make_component(tmp_path, "training", "my_trainer")

        result = build_component_asset(tmp_path, comp_file)

        assert result["category"] == "training"
        assert result["name"] == "my_trainer"
        assert result["subcategory"] is None

    def test_subcategory_component(self, tmp_path: Path):
        """Build asset dict for a subcategory component."""
        comp_file = _make_component(tmp_path, "training", "logistic_regression", subcategory="sklearn_trainer")

        result = build_component_asset(tmp_path, comp_file)

        assert result["category"] == "training"
        assert result["subcategory"] == "sklearn_trainer"
        assert result["name"] == "logistic_regression"

    def test_raises_on_wrong_filename(self, tmp_path: Path):
        """Raise ValueError when the file doesn't match component.py."""
        bad_file = tmp_path / "components" / "training" / "my_comp" / "wrong.py"
        bad_file.parent.mkdir(parents=True)
        bad_file.write_text("")

        with pytest.raises(ValueError, match="Expected component.py"):
            build_component_asset(tmp_path, bad_file)

    def test_raises_on_too_shallow_path(self, tmp_path: Path):
        """Raise ValueError when path has fewer than 3 parts."""
        shallow_file = tmp_path / "components" / "training" / "component.py"
        shallow_file.parent.mkdir(parents=True)
        shallow_file.write_text("")

        with pytest.raises(ValueError, match="Path must be"):
            build_component_asset(tmp_path, shallow_file)

    def test_raises_on_too_deep_path(self, tmp_path: Path):
        """Raise ValueError when path has more than 4 parts."""
        deep_file = tmp_path / "components" / "cat" / "sub" / "subsub" / "name" / "component.py"
        deep_file.parent.mkdir(parents=True)
        deep_file.write_text("")

        with pytest.raises(ValueError, match="Path must be"):
            build_component_asset(tmp_path, deep_file)


class TestBuildPipelineAsset:
    """Tests for build_pipeline_asset()."""

    def test_direct_pipeline(self, tmp_path: Path):
        """Build asset dict for a direct category pipeline."""
        pipe_file = _make_pipeline(tmp_path, "training", "my_pipeline")

        result = build_pipeline_asset(tmp_path, pipe_file)

        assert result["category"] == "training"
        assert result["name"] == "my_pipeline"
        assert result["subcategory"] is None

    def test_subcategory_pipeline(self, tmp_path: Path):
        """Build asset dict for a subcategory pipeline."""
        pipe_file = _make_pipeline(tmp_path, "training", "batch_training", subcategory="ml_workflows")

        result = build_pipeline_asset(tmp_path, pipe_file)

        assert result["category"] == "training"
        assert result["subcategory"] == "ml_workflows"
        assert result["name"] == "batch_training"
