"""Base image extraction and validation utilities."""

import os
import re
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .kfp_compilation import compile_and_get_yaml, find_decorated_functions_runtime, load_module_from_path
from .oci import validate_tag
from .parsing import get_base_image_locations


class BaseImageTagCheckError(RuntimeError):
    """Raised when base_image tag checking fails due to load/compile errors."""

    def __init__(self, asset_file: Path, message: str):
        """Create an error associated with a specific asset file."""
        super().__init__(message)
        self.asset_file = asset_file


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


def _is_allowlisted_image(image: str, allowlist: BaseImageAllowlist) -> bool:
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


def extract_base_images(ir_yaml: dict[str, Any]) -> set[str]:
    """Extract base_image values from a compiled KFP IR YAML.

    The KFP IR YAML structure typically has:
    - deploymentSpec.executors.<executor_name>.container.image

    Args:
        ir_yaml: Parsed IR YAML dictionary.

    Returns:
        Set of unique base image values.

    Raises:
        ValueError: If ir_yaml is None or not a dict.
    """
    if ir_yaml is None:
        raise ValueError("ir_yaml cannot be None")
    if not isinstance(ir_yaml, dict):
        raise ValueError(f"ir_yaml must be a dict, got {type(ir_yaml).__name__}")

    images: set[str] = set()

    deployment_spec = ir_yaml.get("deploymentSpec", {})
    executors = deployment_spec.get("executors", {})

    for _executor_name, executor_config in executors.items():
        container = executor_config.get("container", {})
        image = container.get("image")
        if image:
            images.add(image)

    root = ir_yaml.get("root", {})
    dag = root.get("dag", {})
    tasks = dag.get("tasks", {})

    for _task_name, task_config in tasks.items():
        component_ref = task_config.get("componentRef", {})
        if "image" in component_ref:
            images.add(component_ref["image"])

    components = ir_yaml.get("components", {})
    for _component_name, comp_config in components.items():
        executor_label = comp_config.get("executorLabel")
        if executor_label and executor_label in executors:
            container = executors[executor_label].get("container", {})
            if "image" in container:
                images.add(container["image"])

    return images


def is_valid_base_image(
    image: str,
    allowlist: BaseImageAllowlist | None = None,
) -> bool:
    """Check if a base image is valid according to configuration.

    Valid base images either:
    - Are empty/unset (represented as empty string or None)
    - Match the configured allowlist file

    Args:
        image: The base image string to validate.
        allowlist: Optional allowlist configuration.

    Returns:
        True if the image is valid, False otherwise.
    """
    if not image:
        return True
    if allowlist is not None:
        return _is_allowlisted_image(image, allowlist)
    return False


def validate_base_images(
    images: set[str],
    allowlist: BaseImageAllowlist | None = None,
) -> set[str]:
    """Validate a set of base images and return invalid ones.

    Args:
        images: Set of base image strings to validate.
        allowlist: Optional allowlist configuration.

    Returns:
        Set of invalid base image strings. Returns an empty set if all images are valid.
    """
    return {img for img in images if not is_valid_base_image(img, allowlist)}


def _sanitize_module_name(asset_file: Path, asset_type: str) -> str:
    name = re.sub(r"\W+", "_", f"check_base_image_tags_{asset_type}_{asset_file}")
    if not name.isidentifier():
        name = f"m_{name}"
    return name


def _discover_candidate_asset_files(directories: list[str]) -> list[tuple[str, Path]]:
    candidate_files: list[tuple[str, Path]] = []
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            continue
        candidate_files.extend(("component", p) for p in dir_path.rglob("component.py"))
        candidate_files.extend(("pipeline", p) for p in dir_path.rglob("pipeline.py"))
    candidate_files.sort(key=lambda x: str(x[1]))
    return candidate_files


def _compile_asset_images(asset_file: Path, asset_type: str, tmpdir: str) -> set[str] | None:
    module_name = _sanitize_module_name(asset_file, asset_type)
    try:
        module = load_module_from_path(str(asset_file), module_name)
    except Exception as e:
        raise BaseImageTagCheckError(asset_file, f"Failed to load module: {e}") from e

    functions = find_decorated_functions_runtime(module, asset_type)
    if not functions:
        return None

    images: set[str] = set()
    for func_name, func in functions:
        output_path = os.path.join(tmpdir, f"{module_name}_{func_name}.yaml")
        try:
            ir_yaml = compile_and_get_yaml(func, output_path)
        except Exception as e:
            raise BaseImageTagCheckError(
                asset_file,
                f"Compilation failed for function '{func_name}': {e}",
            ) from e
        images.update(extract_base_images(ir_yaml))
    return images


def check_base_image_tags(directories: list[str], image_prefix: str, expected_tag: str) -> tuple[bool, list[dict]]:
    """Compile components/pipelines and ensure resolved base images use the expected tag.

    This check enforces the policy on the resolved runtime image strings (as produced by KFP compilation).
    Only images that start with '{image_prefix}-' are checked; all other images are ignored.

    Args:
        directories: Directories to scan for components/pipelines.
        image_prefix: Image prefix to check (e.g., ghcr.io/kubeflow/pipelines-components).
        expected_tag: Expected tag for base images (default: "main").
    """
    prefix_with_dash = f"{image_prefix}-"
    expected_suffix = f":{expected_tag}"
    results: list[dict] = []

    candidate_files = _discover_candidate_asset_files(directories)
    if not candidate_files:
        return True, []

    with tempfile.TemporaryDirectory() as tmpdir:
        for asset_type, asset_file in candidate_files:
            try:
                images = _compile_asset_images(asset_file, asset_type, tmpdir)
            except BaseImageTagCheckError as e:
                results.append(
                    {
                        "file": str(asset_file),
                        "line_num": 0,
                        "status": "invalid",
                        "error": str(e),
                    }
                )
                continue
            if images is None:
                continue

            for image in sorted(img for img in images if img.startswith(prefix_with_dash)):
                if image.endswith(expected_suffix):
                    results.append({"file": str(asset_file), "line_num": 0, "status": "valid"})
                else:
                    results.append(
                        {
                            "file": str(asset_file),
                            "line_num": 0,
                            "status": "invalid",
                            "found": image,
                            "expected": f"{image_prefix}-<name>:{expected_tag}",
                        }
                    )

    all_valid = all(r["status"] == "valid" for r in results) if results else True
    return all_valid, results


def override_file_images(
    file_path: Path, container_tag: str, image_prefix: str, dry_run: bool = False
) -> tuple[bool, str | None]:
    """Override base_image values in KFP decorators, replacing the entire string literal.

    Only modifies images matching the prefix and tagged with :main.

    Raises:
        ValueError: If any base_image argument is not a string literal.
    """
    validate_tag(container_tag)

    base_images = get_base_image_locations(file_path)

    prefix_with_dash = image_prefix + "-"
    to_replace = [bi for bi in base_images if bi.value.startswith(prefix_with_dash) and bi.value.endswith(":main")]

    if not to_replace:
        return False, None

    lines = file_path.read_text().splitlines(keepends=True)

    # Process in reverse order to avoid column offset shifts from earlier replacements
    for bi in sorted(to_replace, key=lambda x: (x.start_line, x.start_col), reverse=True):
        if bi.start_line != bi.end_line:
            raise ValueError(f"Multi-line base_image values are not supported in {file_path}")

        new_value = bi.value.rsplit(":", 1)[0] + ":" + container_tag
        line_idx = bi.start_line - 1

        line = lines[line_idx]
        quote_char = line[bi.start_col]
        quote = quote_char * 3 if line[bi.start_col + 1 : bi.start_col + 3] == quote_char * 2 else quote_char
        new_line = line[: bi.start_col] + f"{quote}{new_value}{quote}" + line[bi.end_col :]
        lines[line_idx] = new_line

    new_content = "".join(lines)
    if not dry_run:
        file_path.write_text(new_content)
    return True, new_content


def override_base_images(
    directories: list[str],
    container_tag: str,
    image_prefix: str,
    dry_run: bool = False,
    verbose: bool = True,
) -> list[str]:
    """Override base_image values in all Python files, replacing entire string literals."""
    modified_files = []

    for py_file in _iter_python_files(directories):
        was_modified, _ = override_file_images(py_file, container_tag, image_prefix, dry_run)
        if was_modified:
            modified_files.append(str(py_file))
            if verbose:
                action = "Would update" if dry_run else "Updating"
                print(f"{action}: {py_file}")

    return modified_files


def _iter_python_files(directories: list[str]) -> Iterator[Path]:
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            continue
        yield from dir_path.rglob("*.py")
