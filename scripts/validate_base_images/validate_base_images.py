#!/usr/bin/env python3
"""Validate base images used in Kubeflow Pipelines components and pipelines.

This script discovers all components and pipelines in the components/ and pipelines/
directories, compiles them using kfp.compiler to generate IR YAML, and extracts
base_image values from the pipeline specifications.

Usage:
    uv run python scripts/validate_base_images/validate_base_images.py
"""

import argparse
import importlib.util
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from kfp import compiler

ALLOWED_BASE_IMAGE_PREFIX = "ghcr.io/kubeflow/"
COMPONENT_FILENAME = "component.py"
PIPELINE_FILENAME = "pipeline.py"


@dataclass(frozen=True)
class BaseImageAllowlist:
    """Allowlist configuration for base images."""

    allowed_images: frozenset[str]
    allowed_image_patterns: tuple[re.Pattern[str], ...]


def load_base_image_allowlist(path: Path) -> BaseImageAllowlist:
    """Load and parse base image allowlist from YAML file.

    Args:
        path: Path to the allowlist YAML file.

    Returns:
        Parsed allowlist configuration.

    Raises:
        ValueError: If the allowlist file is malformed or contains invalid patterns.
    """
    data = yaml.safe_load(path.read_text())
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError(f"Allowlist must be a YAML mapping: {path}")

    allowed_images_raw = data.get("allowed_images", [])
    allowed_patterns_raw = data.get("allowed_image_patterns", [])

    if not isinstance(allowed_images_raw, list) or not all(isinstance(x, str) for x in allowed_images_raw):
        raise ValueError(f"'allowed_images' must be a list of strings: {path}")
    if not isinstance(allowed_patterns_raw, list) or not all(isinstance(x, str) for x in allowed_patterns_raw):
        raise ValueError(f"'allowed_image_patterns' must be a list of regex strings: {path}")

    try:
        patterns = tuple(re.compile(p) for p in allowed_patterns_raw)
    except re.error as e:
        raise ValueError(f"Invalid regex in allowlist {path}: {e}") from e

    return BaseImageAllowlist(
        allowed_images=frozenset(allowed_images_raw),
        allowed_image_patterns=patterns,
    )


def is_allowlisted_image(image: str, allowlist: BaseImageAllowlist) -> bool:
    """Check if an image matches the allowlist.

    Args:
        image: Image name to check.
        allowlist: Allowlist configuration.

    Returns:
        True if the image is in the allowlist or matches a pattern.
    """
    if image in allowlist.allowed_images:
        return True
    return any(p.match(image) for p in allowlist.allowed_image_patterns)


@dataclass
class ValidationConfig:
    """Configuration for base image validation."""

    allowed_prefix: str = ALLOWED_BASE_IMAGE_PREFIX
    allowlist_path: Path = Path(__file__).parent / "base_image_allowlist.yaml"
    allowlist: BaseImageAllowlist | None = None


_config: ValidationConfig | None = None


def get_config() -> ValidationConfig:
    """Get the current validation configuration."""
    global _config
    if _config is None:
        config = ValidationConfig()
        config.allowlist = load_base_image_allowlist(config.allowlist_path)
        _config = config
    return _config


def set_config(config: ValidationConfig) -> None:
    """Set the validation configuration."""
    global _config
    _config = config


def get_repo_root() -> Path:
    """Get the repository root directory."""
    return Path(__file__).parent.parent.parent.resolve()


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


def load_module_from_path(module_path: str, module_name: str) -> Any:
    """Dynamically load a Python module from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def find_decorated_functions(module: Any, decorator_type: str) -> list[tuple[str, Any]]:
    """Find all functions decorated with @dsl.component or @dsl.pipeline.

    Args:
        module: The loaded Python module
        decorator_type: Either 'component' or 'pipeline'

    Returns:
        List of tuples (function_name, function_object)
    """
    functions = []

    for attr_name in dir(module):
        if attr_name.startswith("_"):
            continue

        attr = getattr(module, attr_name, None)
        if attr is None or not callable(attr):
            continue

        is_component = (
            hasattr(attr, "component_spec")
            or getattr(attr, "__wrapped__", None) is not None
            and hasattr(getattr(attr, "__wrapped__"), "component_spec")
        )
        is_pipeline = hasattr(attr, "pipeline_spec") or getattr(attr, "_pipeline_func", None) is not None

        is_match = (decorator_type == "component" and is_component) or (decorator_type == "pipeline" and is_pipeline)
        if is_match:
            functions.append((attr_name, attr))

    return functions


def compile_and_get_yaml(func: Any, output_path: str) -> dict[str, Any] | None:
    """Compile a component or pipeline function and return the parsed YAML.

    Returns None if compilation fails.
    """
    try:
        compiler.Compiler().compile(func, output_path)
        with open(output_path) as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"  Warning: Failed to compile {func}: {e}")
        return None


def extract_base_images(ir_yaml: dict[str, Any]) -> set[str]:
    """Extract base_image values from a compiled KFP IR YAML.

    The KFP IR YAML structure typically has:
    - deploymentSpec.executors.<executor_name>.container.image

    Returns a set of unique base image values.
    """
    images = set()

    if not ir_yaml:
        return images

    deployment_spec = ir_yaml.get("deploymentSpec", {})
    executors = deployment_spec.get("executors", {})

    for executor_name, executor_config in executors.items():
        container = executor_config.get("container", {})
        image = container.get("image")
        if image:
            images.add(image)

    root = ir_yaml.get("root", {})
    dag = root.get("dag", {})
    tasks = dag.get("tasks", {})

    for task_name, task_config in tasks.items():
        component_ref = task_config.get("componentRef", {})
        if "image" in component_ref:
            images.add(component_ref["image"])

    components = ir_yaml.get("components", {})
    for comp_name, comp_config in components.items():
        executor_label = comp_config.get("executorLabel")
        if executor_label and executor_label in executors:
            container = executors[executor_label].get("container", {})
            if "image" in container:
                images.add(container["image"])

    return images


def is_valid_base_image(image: str, config: ValidationConfig | None = None) -> bool:
    """Check if a base image is valid according to configuration.

    Valid base images either:
    - Start with the configured allowed_prefix (default: 'ghcr.io/kubeflow/')
    - Are empty/unset (represented as empty string or None)
    - Match the configured allowlist file

    Args:
        image: The base image string to validate
        config: Optional ValidationConfig; uses global config if not provided

    Returns:
        True if the image is valid, False otherwise
    """
    if config is None:
        config = get_config()

    if not image:
        return True
    if image.startswith(config.allowed_prefix):
        return True
    if config.allowlist is None:
        config.allowlist = load_base_image_allowlist(config.allowlist_path)
    return is_allowlisted_image(image, config.allowlist)


def validate_base_images(images: set[str], config: ValidationConfig | None = None) -> list[str]:
    """Validate a set of base images and return invalid ones.

    Args:
        images: Set of base image strings to validate
        config: Optional ValidationConfig; uses global config if not provided

    Returns:
        List of invalid base image strings
    """
    if config is None:
        config = get_config()
    return [img for img in images if not is_valid_base_image(img, config)]


def _find_any_decorated_functions(module: Any) -> list[tuple[str, Any]]:
    """Fallback to find any KFP decorated functions in a module."""
    functions = []
    for attr_name in dir(module):
        if attr_name.startswith("_"):
            continue
        attr = getattr(module, attr_name, None)
        if attr is None or not callable(attr):
            continue
        if hasattr(attr, "component_spec") or hasattr(attr, "pipeline_spec"):
            functions.append((attr_name, attr))
    return functions


def _create_result(asset: dict[str, Any], asset_type: str) -> dict[str, Any]:
    """Create an initial result dict for an asset."""
    return {
        "category": asset["category"],
        "name": asset["name"],
        "type": asset_type,
        "path": str(asset["path"]),
        "base_images": set(),
        "invalid_base_images": [],
        "errors": [],
        "compiled": False,
    }


def process_asset(
    asset: dict[str, Any],
    asset_type: str,
    temp_dir: str,
    config: ValidationConfig | None = None,
) -> dict[str, Any]:
    """Process a single component or pipeline asset.

    Returns a dict with asset info and extracted base images.
    """
    if config is None:
        config = get_config()

    result = _create_result(asset, asset_type)
    module_name = f"{asset['category']}_{asset['name']}_{asset_type}"

    try:
        module = load_module_from_path(asset["module_path"], module_name)
    except Exception as e:
        result["errors"].append(f"Failed to load module: {e}")
        return result

    functions = find_decorated_functions(module, asset_type)
    if not functions:
        functions = _find_any_decorated_functions(module)

    if not functions:
        result["errors"].append(f"No @dsl.{asset_type} decorated functions found")
        return result

    for func_name, func in functions:
        output_path = os.path.join(temp_dir, f"{module_name}_{func_name}.yaml")
        ir_yaml = compile_and_get_yaml(func, output_path)
        if ir_yaml:
            result["compiled"] = True
            result["base_images"].update(extract_base_images(ir_yaml))

    result["invalid_base_images"] = validate_base_images(result["base_images"], config)

    return result


def _print_result(result: dict[str, Any]) -> None:
    """Print the processing result for a single asset."""
    if result["errors"]:
        for error in result["errors"]:
            print(f"    Error: {error}")
    elif result["base_images"]:
        for image in result["base_images"]:
            is_invalid = image in result["invalid_base_images"]
            status = " [INVALID]" if is_invalid else ""
            print(f"    Base image: {image}{status}")
    elif result["compiled"]:
        print("    No custom base image (using default)")


def _process_assets(
    assets: list[dict[str, Any]],
    asset_type: str,
    label: str,
    temp_dir: str,
    config: ValidationConfig | None = None,
) -> tuple[list[dict[str, Any]], set[str]]:
    """Process a batch of assets and return results and base images."""
    results: list[dict[str, Any]] = []
    base_images: set[str] = set()

    if not assets:
        return results, base_images

    print("-" * 70)
    print(f"Processing {label}")
    print("-" * 70)

    for asset in assets:
        print(f"  Processing: {asset['category']}/{asset['name']}")
        result = process_asset(asset, asset_type, temp_dir, config)
        results.append(result)
        base_images.update(result["base_images"])
        _print_result(result)

    print()
    return results, base_images


def _collect_violations(all_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collect all base image violations from results."""
    violations = []
    for result in all_results:
        if result["invalid_base_images"]:
            for image in result["invalid_base_images"]:
                violations.append(
                    {
                        "path": result["path"],
                        "category": result["category"],
                        "name": result["name"],
                        "type": result["type"],
                        "image": image,
                    }
                )
    return violations


def _print_violations(violations: list[dict[str, Any]], config: ValidationConfig) -> None:
    """Print base image violations."""
    print("=" * 70)
    print("BASE IMAGE VIOLATIONS")
    print("=" * 70)
    print()
    print(f"Found {len(violations)} violation(s).")
    print()

    print(f"Invalid base images ({len(violations)}):")
    print(f"  Base images must start with '{config.allowed_prefix}', be unset, or match the allowlist.")
    print(f"  Allowlist: {config.allowlist_path}")
    print()
    print("  To fix this issue, either:")
    print(f"    1. Use an approved base image (e.g., '{config.allowed_prefix}pipelines-components-<name>:<tag>')")
    print("    2. Leave base_image unset to use the KFP SDK default image")
    print(f"    3. Add an allowlist entry in {config.allowlist_path}")
    print()

    for violation in violations:
        print(f"  {violation['type'].title()}: {violation['category']}/{violation['name']}")
        print(f"    Path: {violation['path']}")
        print(f"    Invalid image: {violation['image']}")
        print()


def _compute_summary_counts(all_results: list[dict[str, Any]]) -> tuple[int, int, int, int, int]:
    total_assets = len(all_results)
    compiled_assets = sum(1 for r in all_results if r["compiled"])
    failed_assets = sum(1 for r in all_results if r["errors"])
    assets_with_images = sum(1 for r in all_results if r["base_images"])
    assets_with_invalid_images = sum(1 for r in all_results if r["invalid_base_images"])
    return (
        total_assets,
        compiled_assets,
        failed_assets,
        assets_with_images,
        assets_with_invalid_images,
    )


def _print_base_images_section(
    total_assets: int, failed_assets: int, all_base_images: set[str], violations: list[dict[str, Any]]
) -> None:
    if all_base_images:
        all_invalid = {v["image"] for v in violations}
        print("All unique base images found:")
        for image in sorted(all_base_images):
            status = " [INVALID]" if image in all_invalid else " [VALID]"
            print(f"  - {image}{status}")
        return

    if total_assets == 0:
        return

    if failed_assets > 0:
        print("No base images could be extracted (some assets failed to compile/load)")
        return

    print("No custom base images found (all using defaults)")


def _print_final_status(
    total_assets: int, failed_assets: int, violations: list[dict[str, Any]], config: ValidationConfig
) -> int:
    if total_assets == 0:
        print("No components or pipelines were discovered.")
        print("Components should be at: components/<category>/<name>/component.py")
        print("Pipelines should be at: pipelines/<category>/<name>/pipeline.py")
        return 0

    if violations:
        print(f"FAILED: {len(violations)} violation(s) found.")
        print(f"  - {len(violations)} invalid base image(s): must use '{config.allowed_prefix}' registry")
        print(
            f"    (e.g., '{config.allowed_prefix}pipelines-components-<name>:<tag>'), "
            f"leave unset, or match the allowlist."
        )
        print(f"    Allowlist: {config.allowlist_path}")
        return 1

    if failed_assets > 0:
        print(f"FAILED: {failed_assets} asset(s) could not be processed. See errors above.")
        return 1

    print("SUCCESS: All base images are valid.")
    return 0


def _print_summary(
    all_results: list[dict[str, Any]],
    all_base_images: set[str],
    config: ValidationConfig,
) -> int:
    """Print summary and return exit code."""
    violations = _collect_violations(all_results)

    if violations:
        _print_violations(violations, config)

    print("=" * 70)
    print("Summary")
    print("=" * 70)

    (
        total_assets,
        compiled_assets,
        failed_assets,
        assets_with_images,
        assets_with_invalid_images,
    ) = _compute_summary_counts(all_results)

    print(f"Total assets discovered: {total_assets}")
    print(f"Successfully compiled: {compiled_assets}")
    print(f"Failed to process: {failed_assets}")
    print(f"Assets with custom base images: {assets_with_images}")
    print(f"Assets with invalid base images: {assets_with_invalid_images}")
    print()

    _print_base_images_section(total_assets, failed_assets, all_base_images, violations)

    print()
    return _print_final_status(total_assets, failed_assets, violations, config)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Validate base images used by Kubeflow Pipelines components and pipelines.\n\n"
            "The validator compiles components/pipelines with the KFP compiler and extracts\n"
            "runtime images from the generated IR."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Valid base images are:
  - ghcr.io/kubeflow/* (Kubeflow registry images)
  - images matching scripts/validate_base_images/base_image_allowlist.yaml

Examples:
  # Run with default settings
  %(prog)s

  # Validate specific assets only
  %(prog)s --component components/training/sample_model_trainer
  %(prog)s --pipeline pipelines/training/simple_training
  %(prog)s --component components/training/sample_model_trainer --pipeline pipelines/training/simple_training
        """,
    )

    parser.add_argument(
        "--component",
        action="append",
        default=[],
        metavar="PATH",
        help=(
            "Validate a specific component. Accepts either a directory like "
            "'components/<category>/<name>' or a direct '.../component.py' path. Repeatable."
        ),
    )
    parser.add_argument(
        "--pipeline",
        action="append",
        default=[],
        metavar="PATH",
        help=(
            "Validate a specific pipeline. Accepts either a directory like "
            "'pipelines/<category>/<name>' or a direct '.../pipeline.py' path. Repeatable."
        ),
    )
    parser.add_argument(
        "--allow-list",
        default=None,
        metavar="PATH",
        help=(
            "Path to a base-image allowlist YAML file. Defaults to "
            "'scripts/validate_base_images/base_image_allowlist.yaml'."
        ),
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Main entry point for base image validation.

    Args:
        argv: Command line arguments (defaults to sys.argv).

    Returns:
        Exit code (0 for success, 1 for validation failures).
    """
    args = parse_args(argv)
    config = ValidationConfig()
    if args.allow_list:
        config.allowlist_path = Path(args.allow_list)
    config.allowlist = load_base_image_allowlist(config.allowlist_path)
    set_config(config)

    repo_root = get_repo_root()

    print("=" * 70)
    print("Kubeflow Pipelines Base Image Validator")
    print("=" * 70)
    print()
    print(f"Allowed prefix: {config.allowed_prefix}")
    print(f"Allowlist: {config.allowlist_path}")
    print()

    selected_components = bool(args.component)
    selected_pipelines = bool(args.pipeline)
    is_targeted = selected_components or selected_pipelines

    if is_targeted:
        components: list[dict[str, Any]] = []
        pipelines: list[dict[str, Any]] = []

        for raw in args.component:
            component_file = resolve_component_path(repo_root, raw)
            components.append(build_component_asset(repo_root, component_file))

        for raw in args.pipeline:
            pipeline_file = resolve_pipeline_path(repo_root, raw)
            pipelines.append(build_pipeline_asset(repo_root, pipeline_file))

        print(f"Selected {len(components)} component(s)")
        print(f"Selected {len(pipelines)} pipeline(s)")
    else:
        components = discover_assets(repo_root / "components", "component")
        print(f"Discovered {len(components)} component(s)")

        pipelines = discover_assets(repo_root / "pipelines", "pipeline")
        print(f"Discovered {len(pipelines)} pipeline(s)")
    print()

    all_results: list[dict[str, Any]] = []
    all_base_images: set[str] = set()

    with tempfile.TemporaryDirectory() as temp_dir:
        results, images = _process_assets(components, "component", "Components", temp_dir, config)
        all_results.extend(results)
        all_base_images.update(images)

        results, images = _process_assets(pipelines, "pipeline", "Pipelines", temp_dir, config)
        all_results.extend(results)
        all_base_images.update(images)

    return _print_summary(all_results, all_base_images, config)


if __name__ == "__main__":
    sys.exit(main())
