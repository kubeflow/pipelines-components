"""Shared helpers for working with component and pipeline metadata."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml
from packaging.specifiers import SpecifierSet

from .discovery import get_repo_root

LOGGER = logging.getLogger(__name__)


@dataclass
class MetadataTarget:
    """Represents a component or pipeline discovered via metadata."""

    metadata_path: Path
    module_path: Path
    target_kind: str  # "component" or "pipeline"
    # requires from typing import Any
    metadata: dict[str, Any]


def discover_metadata_files(repo_root: Optional[Path] = None) -> list[tuple[Path, str]]:
    """Return a list of (metadata_path, target_kind) for the repository.

    Args:
        repo_root: Optional repository root. Defaults to the project root.
    """
    if repo_root is None:
        repo_root = get_repo_root()

    search_roots: list[tuple[Path, str]] = [
        (repo_root / "components", "component"),
        (repo_root / "pipelines", "pipeline"),
    ]

    discovered: list[tuple[Path, str]] = []
    for root, target_kind in search_roots:
        if not root.exists():
            continue
        for metadata_path in root.glob("**/metadata.yaml"):
            discovered.append((metadata_path, target_kind))
    return discovered


def load_metadata(metadata_path: Path) -> dict[str, Any]:
    """Load and validate a metadata YAML file."""
    with metadata_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(f"Metadata at {metadata_path} must be a mapping.")
        return data


def metadata_should_run(metadata: dict[str, Any], include_flagless: bool) -> bool:
    """Return whether metadata indicates the target should be processed."""
    ci_config = metadata.get("ci") or {}
    if "compile_check" in ci_config:
        return bool(ci_config["compile_check"])
    return include_flagless


def _normalize_path_filters(path_filters: Sequence[str], repo_root: Path) -> list[Path]:
    normalized: list[Path] = []
    for raw in path_filters:
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = (repo_root / candidate).resolve()
        else:
            candidate = candidate.resolve()
        normalized.append(candidate)
    return normalized


def create_metadata_targets(
    discovered: Iterable[tuple[Path, str]],
    include_flagless: bool,
    path_filters: Sequence[str],
    *,
    repo_root: Optional[Path] = None,
    logger: Optional[logging.Logger] = None,
) -> list[MetadataTarget]:
    """Build MetadataTarget objects from discovered metadata files.

    Args:
        discovered: Iterable of (metadata_path, target_kind) tuples.
        include_flagless: Whether to include metadata without explicit flags.
        path_filters: Optional path filters to limit processed metadata.
        repo_root: Optional repository root override.
        logger: Optional logger for diagnostics.
    """
    if repo_root is None:
        repo_root = get_repo_root()
    log = logger or LOGGER
    normalized_filters = _normalize_path_filters(path_filters, repo_root)

    targets: list[MetadataTarget] = []

    for metadata_path, target_kind in discovered:
        metadata = load_metadata(metadata_path)

        if not metadata_should_run(metadata, include_flagless):
            log.debug("Skipping %s (compile_check disabled).", metadata_path)
            continue

        module_filename = "component.py" if target_kind == "component" else "pipeline.py"
        module_path = metadata_path.with_name(module_filename)
        metadata_dir = metadata_path.parent.resolve()
        metadata_file = metadata_path.resolve()
        module_file = module_path.resolve()

        if normalized_filters:
            matched = False
            for filter_path in normalized_filters:
                if filter_path.is_dir():
                    if metadata_dir.is_relative_to(filter_path):
                        matched = True
                        break
                else:
                    if metadata_file == filter_path or module_file == filter_path:
                        matched = True
                        break
            if not matched:
                continue

        if not module_path.exists():
            log.error(
                "Expected module %s not found for metadata %s",
                module_path,
                metadata_path,
            )
            continue

        targets.append(
            MetadataTarget(
                metadata_path=metadata_path,
                module_path=module_path,
                target_kind=target_kind,
                metadata=metadata,
            )
        )
    return targets


def validate_dependencies(metadata: dict[str, Any]) -> tuple[list[str], list[str]]:
    """Validate dependency metadata declared for a target.

    Returns:
        Tuple of (errors, warnings).
    """
    dependencies = metadata.get("dependencies") or {}
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(dependencies, dict):
        errors.append("`dependencies` must be a mapping.")
        return errors, warnings

    sections = [
        ("kubeflow", "Kubeflow dependency"),
        ("external_services", "External service dependency"),
    ]

    for section_key, label in sections:
        entries = dependencies.get(section_key, [])
        if not entries:
            continue
        if not isinstance(entries, list):
            errors.append(f"`dependencies.{section_key}` must be a list.")
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                errors.append(f"{label} entries must be mappings: {entry!r}")
                continue
            name = entry.get("name")
            version = entry.get("version")
            if not name:
                errors.append(f"{label} is missing a `name` field.")
            if not version:
                errors.append(f"{label} for {name or '<unknown>'} is missing a `version` field.")
            else:
                try:
                    SpecifierSet(str(version))
                except Exception as exc:
                    errors.append(
                        f"{label} for {name or '<unknown>'} has an invalid version specifier {version!r}: {exc}"
                    )

    return errors, warnings
