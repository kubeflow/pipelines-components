#!/usr/bin/env python3
"""
Compile and dependency validation tool for Kubeflow Pipelines components.

This script discovers component and pipeline modules based on the presence of
`metadata.yaml` files, validates declared dependencies, and ensures each target
compiles successfully with the Kubeflow Pipelines SDK.
"""

from __future__ import annotations

import argparse
import importlib
import logging
import sys
import tempfile
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import yaml

try:
    from packaging.specifiers import SpecifierSet
except ImportError:  # pragma: no cover - packaging is optional
    SpecifierSet = None  # type: ignore[assignment]

from kfp import compiler as pipeline_compiler
from kfp.dsl import base_component
from kfp.dsl import graph_component


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class MetadataTarget:
    """Represents a single component or pipeline discovered from metadata."""

    metadata_path: Path
    module_path: Path
    module_import: str
    tier: str
    target_kind: str  # "component" or "pipeline"
    metadata: Dict


@dataclass
class ValidationResult:
    target: MetadataTarget
    success: bool
    compiled_objects: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        logging.error(message)
        self.errors.append(message)
        self.success = False

    def add_warning(self, message: str) -> None:
        logging.warning(message)
        self.warnings.append(message)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compile Kubeflow components and pipelines."
    )
    parser.add_argument(
        "--tier",
        choices=["core", "all"],
        default="all",
        help="Limit validation to core tier only or run across all core assets (default: all).",
    )
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        help="Restrict validation to metadata paths under this directory. May be supplied multiple times.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop at the first validation failure.",
    )
    parser.add_argument(
        "--include-flagless",
        action="store_true",
        help="Include targets that do not set ci.compile_check explicitly.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    return parser.parse_args(argv)


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )


def discover_metadata_files(tier: str) -> List[Tuple[Path, str, str]]:
    """Return a list of (metadata_path, tier, target_kind)."""
    if tier not in ("core", "all"):
        return []

    search_roots: List[Tuple[Path, str]] = [
        (REPO_ROOT / "components", "component"),
        (REPO_ROOT / "pipelines", "pipeline"),
    ]

    discovered: List[Tuple[Path, str, str]] = []
    for root, target_kind in search_roots:
        if not root.exists():
            continue
        for metadata_path in root.glob("**/metadata.yaml"):
            discovered.append((metadata_path, "core", target_kind))
    return discovered


def should_include_target(
    metadata: Dict,
    include_flagless: bool,
) -> bool:
    ci_config = metadata.get("ci") or {}
    if "compile_check" in ci_config:
        return bool(ci_config["compile_check"])
    return include_flagless


def build_module_import_path(module_path: Path) -> str:
    relative = module_path.relative_to(REPO_ROOT)
    return ".".join(relative.with_suffix("").parts)


def load_metadata(metadata_path: Path) -> Dict:
    with metadata_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(f"Metadata at {metadata_path} must be a mapping.")
        return data


def create_targets(
    discovered: Iterable[Tuple[Path, str, str]],
    include_flagless: bool,
    path_filters: Sequence[str],
) -> List[MetadataTarget]:
    normalized_filters = [Path(p).resolve() for p in path_filters]
    targets: List[MetadataTarget] = []

    for metadata_path, tier, target_kind in discovered:
        if normalized_filters:
            absolute_metadata_dir = metadata_path.parent.resolve()
            if not any(
                absolute_metadata_dir.is_relative_to(f) for f in normalized_filters
            ):
                continue

        try:
            metadata = load_metadata(metadata_path)
        except Exception as exc:
            logging.error("Failed to read metadata %s: %s", metadata_path, exc)
            continue

        if not should_include_target(metadata, include_flagless):
            logging.debug("Skipping %s (compile_check disabled).", metadata_path)
            continue

        module_filename = (
            "component.py" if target_kind == "component" else "pipeline.py"
        )
        module_path = metadata_path.with_name(module_filename)
        if not module_path.exists():
            logging.error(
                "Expected module %s not found for metadata %s",
                module_path,
                metadata_path,
            )
            continue

        module_import = build_module_import_path(module_path)
        targets.append(
            MetadataTarget(
                metadata_path=metadata_path,
                module_path=module_path,
                module_import=module_import,
                tier=tier,
                target_kind=target_kind,
                metadata=metadata,
            )
        )
    return targets


def find_objects(
    module, target_kind: str
) -> List[Tuple[str, base_component.BaseComponent]]:
    found: List[Tuple[str, base_component.BaseComponent]] = []
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if target_kind == "pipeline":
            if isinstance(attr, graph_component.GraphComponent):
                found.append((attr_name, attr))
        else:
            if isinstance(attr, base_component.BaseComponent) and not isinstance(
                attr, graph_component.GraphComponent
            ):
                found.append((attr_name, attr))
    return found


def validate_dependencies(metadata: Dict, result: ValidationResult) -> None:
    dependencies = metadata.get("dependencies") or {}
    if not isinstance(dependencies, dict):
        result.add_error("`dependencies` must be a mapping.")
        return

    sections = [
        ("kubeflow", "Kubeflow dependency"),
        ("external_services", "External service dependency"),
    ]

    for section_key, label in sections:
        entries = dependencies.get(section_key, [])
        if not entries:
            continue
        if not isinstance(entries, list):
            result.add_error(f"`dependencies.{section_key}` must be a list.")
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                result.add_error(f"{label} entries must be mappings: {entry!r}")
                continue
            name = entry.get("name")
            version = entry.get("version")
            if not name:
                result.add_error(f"{label} is missing a `name` field.")
            if not version:
                result.add_error(
                    f"{label} for {name or '<unknown>'} is missing a `version` field."
                )
            elif SpecifierSet is not None:
                try:
                    SpecifierSet(str(version))
                except Exception as exc:
                    result.add_error(
                        f"{label} for {name or '<unknown>'} has an invalid version specifier "
                        f"{version!r}: {exc}"
                    )
            else:
                result.add_warning(
                    "packaging module not available; skipping validation for dependency versions."
                )
                return


def compile_pipeline(obj: graph_component.GraphComponent, output_dir: Path) -> Path:
    output_path = output_dir / f"{obj.name or 'pipeline'}.json"
    pipeline_compiler.Compiler().compile(
        pipeline_func=obj,
        package_path=str(output_path),
    )
    return output_path


def compile_component(obj: base_component.BaseComponent, output_dir: Path) -> Path:
    output_path = output_dir / f"{obj.name or 'component'}.yaml"
    obj.component_spec.save_to_component_yaml(str(output_path))
    return output_path


def validate_target(target: MetadataTarget) -> ValidationResult:
    result = ValidationResult(target=target, success=True)
    validate_dependencies(target.metadata, result)
    if not result.success and result.errors:
        return result

    try:
        if target.module_import in sys.modules:
            del sys.modules[target.module_import]
        module = importlib.import_module(target.module_import)
    except Exception:
        result.add_error(
            f"Failed to import module {target.module_import} defined in {target.module_path}.\n"
            f"{traceback.format_exc()}"
        )
        return result

    objects = find_objects(module, target.target_kind)
    if not objects:
        result.add_error(
            f"No {target.target_kind} objects discovered in module {target.module_import}."
        )
        return result

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        for attr_name, obj in objects:
            try:
                if target.target_kind == "pipeline":
                    compiled_path = compile_pipeline(obj, temp_path)
                else:
                    compiled_path = compile_component(obj, temp_path)
                result.compiled_objects.append(f"{attr_name} -> {compiled_path.name}")
                logging.debug(
                    "Compiled %s from %s to %s",
                    attr_name,
                    target.module_import,
                    compiled_path,
                )
            except Exception:
                result.add_error(
                    f"Failed to compile {target.target_kind} `{attr_name}` from {target.module_import}.\n"
                    f"{traceback.format_exc()}"
                )
                if result.errors:
                    # stop compiling additional objects from this module to avoid noise
                    break

    return result


def run_validation(args: argparse.Namespace) -> int:
    configure_logging(args.verbose)
    sys.path.insert(0, str(REPO_ROOT))

    discovered = discover_metadata_files(args.tier)
    targets = create_targets(discovered, args.include_flagless, args.path)

    if not targets:
        logging.info("No targets discovered for compile check.")
        return 0

    results: List[ValidationResult] = []
    for target in targets:
        logging.info(
            "Validating %s (%s) from %s",
            target.metadata.get("name", target.module_import),
            target.target_kind,
            target.metadata_path,
        )
        result = validate_target(target)
        results.append(result)

        if result.success:
            logging.info(
                "✓ %s compiled successfully (%s)",
                target.metadata.get("name", target.module_import),
                ", ".join(result.compiled_objects)
                if result.compiled_objects
                else "no output",
            )
        else:
            logging.error(
                "✗ %s failed validation (%d error(s))",
                target.metadata.get("name", target.module_import),
                len(result.errors),
            )
            if args.fail_fast:
                break

    failed = [res for res in results if not res.success]
    logging.info(
        "Validation complete: %d succeeded, %d failed.",
        len(results) - len(failed),
        len(failed),
    )

    if failed:
        logging.error("Compile check failed for the targets listed above.")
        return 1
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        return run_validation(args)
    finally:
        # Ensure repo root is removed if we inserted it.
        if sys.path and sys.path[0] == str(REPO_ROOT):
            sys.path.pop(0)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
