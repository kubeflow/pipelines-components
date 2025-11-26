"""Asset discovery utilities for components and pipelines."""

from pathlib import Path
from typing import Any

COMPONENT_FILENAME = "component.py"
PIPELINE_FILENAME = "pipeline.py"


def discover_assets(base_dir: Path, asset_type: str) -> list[dict[str, Any]]:
    """Discover all components or pipelines in a directory.

    Args:
        base_dir: Base directory to search (components/ or pipelines/)
        asset_type: Either 'component' or 'pipeline'

    Returns:
        List of dicts with 'path', 'category', 'name', and 'module_path' keys
    """
    assets = []
    filename = f"{asset_type}.py"

    if not base_dir.exists():
        return assets

    for category_dir in base_dir.iterdir():
        if not category_dir.is_dir() or category_dir.name.startswith(("_", ".")):
            continue

        for asset_dir in category_dir.iterdir():
            if not asset_dir.is_dir() or asset_dir.name.startswith(("_", ".")):
                continue

            asset_file = asset_dir / filename
            if asset_file.exists():
                assets.append(
                    {
                        "path": asset_file,
                        "category": category_dir.name,
                        "name": asset_dir.name,
                        "module_path": str(asset_file),
                    }
                )

    return assets


def find_assets_with_metadata(asset_type: str, base_path: Path | None = None) -> list[str]:
    """Find all asset directories that have metadata.yaml.

    Args:
        asset_type: Either 'components' or 'pipelines'
        base_path: Optional base path, defaults to current directory

    Returns:
        List of asset paths like 'components/training/my_component'
    """
    assets = []
    if base_path is None:
        base_path = Path(".")
    root = base_path / asset_type

    if not root.exists():
        return assets

    for category in root.iterdir():
        if not category.is_dir() or category.name.startswith((".", "_")):
            continue

        for asset in category.iterdir():
            if not asset.is_dir() or asset.name.startswith((".", "_")):
                continue

            if (asset / "metadata.yaml").exists():
                assets.append(f"{asset_type}/{category.name}/{asset.name}")

    return assets


def get_submodules(package_name: str) -> list[str]:
    """Dynamically discover submodules in a package directory.

    Args:
        package_name: Path to the package directory

    Returns:
        Sorted list of submodule names
    """
    package_path = Path(package_name)
    if not package_path.exists():
        return []

    submodules = []
    for item in package_path.iterdir():
        if item.is_dir() and (item / "__init__.py").exists() and not item.name.startswith("_"):
            submodules.append(item.name)

    return sorted(submodules)


def resolve_component_path(repo_root: Path, raw: str) -> Path:
    """Resolve and validate a component file path.

    Args:
        repo_root: Repository root directory.
        raw: Component path (directory or file path, relative or absolute).

    Returns:
        Resolved path to the component.py file.

    Raises:
        ValueError: If the path is invalid or outside the components directory.
    """
    path = Path(raw)
    if not path.is_absolute():
        path = repo_root / path
    path = path.resolve()

    if path.is_dir():
        path = (path / COMPONENT_FILENAME).resolve()

    components_root = (repo_root / "components").resolve()
    if not path.is_relative_to(components_root):
        raise ValueError(f"Component path must be under {components_root}: {path}")

    if path.name != COMPONENT_FILENAME:
        raise ValueError(f"Component path must point to {COMPONENT_FILENAME}: {path}")

    if not path.exists():
        raise ValueError(f"Component file not found: {path}")

    return path


def resolve_pipeline_path(repo_root: Path, raw: str) -> Path:
    """Resolve and validate a pipeline file path.

    Args:
        repo_root: Repository root directory.
        raw: Pipeline path (directory or file path, relative or absolute).

    Returns:
        Resolved path to the pipeline.py file.

    Raises:
        ValueError: If the path is invalid or outside the pipelines directory.
    """
    path = Path(raw)
    if not path.is_absolute():
        path = repo_root / path
    path = path.resolve()

    if path.is_dir():
        path = (path / PIPELINE_FILENAME).resolve()

    pipelines_root = (repo_root / "pipelines").resolve()
    if not path.is_relative_to(pipelines_root):
        raise ValueError(f"Pipeline path must be under {pipelines_root}: {path}")

    if path.name != PIPELINE_FILENAME:
        raise ValueError(f"Pipeline path must point to {PIPELINE_FILENAME}: {path}")

    if not path.exists():
        raise ValueError(f"Pipeline file not found: {path}")

    return path


def build_component_asset(repo_root: Path, component_file: Path) -> dict[str, Any]:
    """Build asset metadata dictionary for a component.

    Args:
        repo_root: Repository root directory.
        component_file: Path to the component.py file.

    Returns:
        Dictionary containing path, category, name, and module_path.
    """
    return _build_asset_dict_from_repo_path(repo_root, "components", component_file, COMPONENT_FILENAME)


def build_pipeline_asset(repo_root: Path, pipeline_file: Path) -> dict[str, Any]:
    """Build asset metadata dictionary for a pipeline.

    Args:
        repo_root: Repository root directory.
        pipeline_file: Path to the pipeline.py file.

    Returns:
        Dictionary containing path, category, name, and module_path.
    """
    return _build_asset_dict_from_repo_path(repo_root, "pipelines", pipeline_file, PIPELINE_FILENAME)


def _build_asset_dict_from_repo_path(
    repo_root: Path, asset_root: str, asset_file: Path, expected_filename: str
) -> dict[str, Any]:
    root = (repo_root / asset_root).resolve()
    resolved = asset_file.resolve()
    if resolved.name != expected_filename:
        raise ValueError(f"Expected {expected_filename} under {asset_root}: {asset_file}")
    rel = resolved.relative_to(root)
    if len(rel.parts) < 3:
        raise ValueError(f"Path must be {asset_root}/<category>/<name>/{expected_filename}: {asset_file}")
    category, name = rel.parts[0], rel.parts[1]
    return {"path": asset_file, "category": category, "name": name, "module_path": str(asset_file)}
