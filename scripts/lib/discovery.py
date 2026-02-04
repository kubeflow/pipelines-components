"""Asset discovery utilities for KFP components and pipelines."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

_COMPONENT_FILENAME = "component.py"
_PIPELINE_FILENAME = "pipeline.py"
_RESERVED_SUBDIRS = {"tests", "shared"}


def get_repo_root() -> Path:
    """Get the repository root directory."""
    return Path(__file__).resolve().parents[2]


def _get_default_targets() -> tuple[Path, Path]:
    """Get the default component and pipeline target directories."""
    repo_root = get_repo_root()
    return repo_root / "components", repo_root / "pipelines"


def normalize_targets(raw_paths: Sequence[str]) -> list[Path]:
    """Normalize target paths to absolute Path objects.

    Args:
        raw_paths: Sequence of path strings (can be relative or absolute).

    Returns:
        List of normalized absolute Path objects.

    Raises:
        FileNotFoundError: If any specified path does not exist.
    """
    repo_root = get_repo_root()
    default_targets = _get_default_targets()

    if not raw_paths:
        return [target for target in default_targets if target.exists()]

    normalized: list[Path] = []
    for raw in raw_paths:
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = (repo_root / candidate).resolve()
        else:
            candidate = candidate.resolve()
        if not candidate.exists():
            raise FileNotFoundError(f"Specified path does not exist: {raw}")
        normalized.append(candidate)
    return normalized


def discover_assets(base_dir: Path, asset_type: str) -> list[dict[str, Any]]:
    """Discover all components or pipelines in a directory.

    Args:
        base_dir: Base directory to search (components/ or pipelines/)
        asset_type: Either 'component' or 'pipeline'

    Returns:
        List of dicts with 'path', 'category', 'subcategory', 'name', and 'module_path' keys.
        'subcategory' is None for direct category assets.
    """
    assets = []
    filename = f"{asset_type}.py"

    if not base_dir.exists():
        return assets

    for category_dir in base_dir.iterdir():
        if not category_dir.is_dir() or category_dir.name.startswith(("_", ".")):
            continue

        for item_dir in category_dir.iterdir():
            if not item_dir.is_dir() or item_dir.name.startswith(("_", ".")):
                continue

            # Check if this is a direct asset
            asset_file = item_dir / filename
            if asset_file.exists():
                assets.append(
                    {
                        "path": asset_file,
                        "category": category_dir.name,
                        "subcategory": None,
                        "name": item_dir.name,
                        "module_path": str(asset_file),
                    }
                )
            else:
                # This might be a subcategory
                for subitem_dir in item_dir.iterdir():
                    if (
                        not subitem_dir.is_dir()
                        or subitem_dir.name.startswith(("_", "."))
                        or subitem_dir.name in _RESERVED_SUBDIRS
                    ):
                        continue

                    sub_asset_file = subitem_dir / filename
                    if sub_asset_file.exists():
                        assets.append(
                            {
                                "path": sub_asset_file,
                                "category": category_dir.name,
                                "subcategory": item_dir.name,
                                "name": subitem_dir.name,
                                "module_path": str(sub_asset_file),
                            }
                        )

    return assets


def find_assets_with_metadata(asset_type: str, base_path: Path | None = None) -> list[str]:
    """Find all asset directories that have metadata.yaml.

    Args:
        asset_type: Either 'components' or 'pipelines'
        base_path: Optional base path, defaults to current directory

    Returns:
        List of asset paths like 'components/training/my_component' or
        'components/training/sklearn_trainer/logistic_regression'
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

        for item in category.iterdir():
            if not item.is_dir() or item.name.startswith((".", "_")):
                continue

            # Check if this is a direct asset
            if (item / "metadata.yaml").exists():
                assets.append(f"{asset_type}/{category.name}/{item.name}")
            else:
                # This might be a subcategory
                for subitem in item.iterdir():
                    if not subitem.is_dir() or subitem.name.startswith((".", "_")) or subitem.name in _RESERVED_SUBDIRS:
                        continue

                    if (subitem / "metadata.yaml").exists():
                        assets.append(f"{asset_type}/{category.name}/{item.name}/{subitem.name}")

    return assets


def get_all_assets_with_metadata(base_path: Path | None = None) -> list[str]:
    """Get all assets with metadata from the repository."""
    return find_assets_with_metadata("components", base_path) + find_assets_with_metadata("pipelines", base_path)


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
        path = (path / _COMPONENT_FILENAME).resolve()

    components_root = (repo_root / "components").resolve()
    if not path.is_relative_to(components_root):
        raise ValueError(f"Component path must be under {components_root}: {path}")

    if path.name != _COMPONENT_FILENAME:
        raise ValueError(f"Component path must point to {_COMPONENT_FILENAME}: {path}")

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
        path = (path / _PIPELINE_FILENAME).resolve()

    pipelines_root = (repo_root / "pipelines").resolve()
    if not path.is_relative_to(pipelines_root):
        raise ValueError(f"Pipeline path must be under {pipelines_root}: {path}")

    if path.name != _PIPELINE_FILENAME:
        raise ValueError(f"Pipeline path must point to {_PIPELINE_FILENAME}: {path}")

    if not path.exists():
        raise ValueError(f"Pipeline file not found: {path}")

    return path


def _build_asset_dict_from_repo_path(
    repo_root: Path, asset_root: str, asset_file: Path, expected_filename: str
) -> dict[str, Any]:
    """Build asset metadata dictionary from a file path.

    Args:
        repo_root: Repository root directory.
        asset_root: Either 'components' or 'pipelines'.
        asset_file: Path to the asset file (component.py or pipeline.py).
        expected_filename: Expected filename (component.py or pipeline.py).

    Returns:
        Dictionary containing path, category, subcategory, name, and module_path.
        'subcategory' is None for direct category assets.

    Raises:
        ValueError: If the path structure is invalid.
    """
    root = (repo_root / asset_root).resolve()
    resolved = asset_file.resolve()
    if resolved.name != expected_filename:
        raise ValueError(f"Expected {expected_filename} under {asset_root}: {asset_file}")
    rel = resolved.relative_to(root)

    if len(rel.parts) == 3:
        # Direct category asset: category/name/filename
        category, name = rel.parts[0], rel.parts[1]
        subcategory = None
    elif len(rel.parts) == 4:
        # Subcategory asset: category/subcategory/name/filename
        category, subcategory, name = rel.parts[0], rel.parts[1], rel.parts[2]
    else:
        raise ValueError(
            f"Path must be {asset_root}/<category>/<name>/{expected_filename} or "
            f"{asset_root}/<category>/<subcategory>/<name>/{expected_filename}: {asset_file}"
        )

    return {
        "path": asset_file,
        "category": category,
        "subcategory": subcategory,
        "name": name,
        "module_path": str(asset_file),
    }


def build_component_asset(repo_root: Path, component_file: Path) -> dict[str, Any]:
    """Build asset metadata dictionary for a component.

    Args:
        repo_root: Repository root directory.
        component_file: Path to the component.py file.

    Returns:
        Dictionary containing path, category, subcategory, name, and module_path.
        'subcategory' is None for direct category components.
    """
    return _build_asset_dict_from_repo_path(repo_root, "components", component_file, _COMPONENT_FILENAME)


def build_pipeline_asset(repo_root: Path, pipeline_file: Path) -> dict[str, Any]:
    """Build asset metadata dictionary for a pipeline.

    Args:
        repo_root: Repository root directory.
        pipeline_file: Path to the pipeline.py file.

    Returns:
        Dictionary containing path, category, subcategory, name, and module_path.
        'subcategory' is None for direct category pipelines.
    """
    return _build_asset_dict_from_repo_path(repo_root, "pipelines", pipeline_file, _PIPELINE_FILENAME)
