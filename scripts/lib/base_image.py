"""Base image extraction and validation utilities."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ALLOWED_BASE_IMAGE_PREFIX = "ghcr.io/kubeflow/"


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
    allowed_prefix: str = ALLOWED_BASE_IMAGE_PREFIX,
    allowlist: BaseImageAllowlist | None = None,
) -> bool:
    """Check if a base image is valid according to configuration.

    Valid base images either:
    - Start with the configured allowed_prefix (default: 'ghcr.io/kubeflow/')
    - Are empty/unset (represented as empty string or None)
    - Match the configured allowlist file

    Args:
        image: The base image string to validate.
        allowed_prefix: Required prefix for valid images.
        allowlist: Optional allowlist configuration.

    Returns:
        True if the image is valid, False otherwise.
    """
    if not image:
        return True
    if image.startswith(allowed_prefix):
        return True
    if allowlist is not None:
        return _is_allowlisted_image(image, allowlist)
    return False


def validate_base_images(
    images: set[str],
    allowed_prefix: str = ALLOWED_BASE_IMAGE_PREFIX,
    allowlist: BaseImageAllowlist | None = None,
) -> list[str]:
    """Validate a set of base images and return invalid ones.

    Args:
        images: Set of base image strings to validate.
        allowed_prefix: Required prefix for valid images.
        allowlist: Optional allowlist configuration.

    Returns:
        List of invalid base image strings.
    """
    return [img for img in images if not is_valid_base_image(img, allowed_prefix, allowlist)]
