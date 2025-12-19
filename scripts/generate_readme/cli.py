"""Command-line interface for the generate_readme package."""

import argparse
import logging
import sys
from pathlib import Path

from scripts.generate_readme.constants import EXIT_DIFF_DETECTED, EXIT_SUCCESS
from scripts.generate_readme.writer import ReadmeWriter

logger = logging.getLogger(__name__)


def validate_component_directory(dir_path: str) -> Path:
    """Validate that the component directory exists and contains required files.

    Args:
        dir_path: String path to the component directory.

    Returns:
        Path: Validated Path object to the component directory.

    Raises:
        argparse.ArgumentTypeError: If validation fails.
    """
    path = Path(dir_path)

    if not path.exists():
        raise argparse.ArgumentTypeError(f"Component directory '{dir_path}' does not exist")

    if not path.is_dir():
        raise argparse.ArgumentTypeError(f"'{dir_path}' is not a directory")

    component_file = path / "component.py"
    if not component_file.exists():
        raise argparse.ArgumentTypeError(f"'{dir_path}' does not contain a component.py file")

    metadata_file = path / "metadata.yaml"
    if not metadata_file.exists():
        raise argparse.ArgumentTypeError(f"'{dir_path}' does not contain a metadata.yaml file")

    return path


def validate_pipeline_directory(dir_path: str) -> Path:
    """Validate that the pipeline directory exists and contains required files.

    Args:
        dir_path: String path to the pipeline directory.

    Returns:
        Path: Validated Path object to the pipeline directory.

    Raises:
        argparse.ArgumentTypeError: If validation fails.
    """
    path = Path(dir_path)

    if not path.exists():
        raise argparse.ArgumentTypeError(f"Pipeline directory '{dir_path}' does not exist")

    if not path.is_dir():
        raise argparse.ArgumentTypeError(f"'{dir_path}' is not a directory")

    pipeline_file = path / "pipeline.py"
    if not pipeline_file.exists():
        raise argparse.ArgumentTypeError(f"'{dir_path}' does not contain a pipeline.py file")

    metadata_file = path / "metadata.yaml"
    if not metadata_file.exists():
        raise argparse.ArgumentTypeError(f"'{dir_path}' does not contain a metadata.yaml file")

    return path


def parse_arguments():
    """Parse and validate command-line arguments.

    Returns:
        argparse.Namespace: Parsed and validated arguments.
    """
    parser = argparse.ArgumentParser(
        description="Generate README.md documentation for Kubeflow Pipelines components and pipelines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  Check mode (default):
    Validates that READMEs are up-to-date without modifying files.
    Exits with code 0 if all files are in sync, code 1 if diffs are detected.

  Fix mode (--fix):
    Updates or creates README files to match expected content.

Examples:
  # Check if READMEs are in sync (default, no changes made):
  python -m scripts.generate_readme --component components/some_category/my_component

  # Fix out-of-sync READMEs:
  python -m scripts.generate_readme --component components/some_category/my_component --fix

  # Check pipeline README:
  python -m scripts.generate_readme --pipeline pipelines/some_category/my_pipeline

  # Or with uv:
  uv run python -m scripts.generate_readme --component components/some_category/my_component --fix
        """,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--component",
        type=validate_component_directory,
        help="Path to the component directory (must contain component.py and metadata.yaml)",
    )

    group.add_argument(
        "--pipeline",
        type=validate_pipeline_directory,
        help="Path to the pipeline directory (must contain pipeline.py and metadata.yaml)",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output path for the generated README.md (default: README.md in component/pipeline directory)",
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")

    parser.add_argument(
        "--fix",
        action="store_true",
        help="Write/update README files. Without this flag, only checks for diffs (exits 1 if found).",
    )

    return parser.parse_args()


def main():
    """Main entry point for the CLI."""
    # Parse arguments
    args = parse_arguments()

    # Configure logging at application entry point
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    # Create the README writer
    writer = ReadmeWriter(
        component_dir=args.component,
        pipeline_dir=args.pipeline,
        output_file=args.output,
    )

    # Run in check mode (default) or fix mode
    has_diff = writer.generate(fix=args.fix)

    # Exit with appropriate code based on the mode and diff status
    if not has_diff:
        # No diffs - files are in sync (same message for both modes)
        logger.info("All README files are in sync.")
        sys.exit(EXIT_SUCCESS)
    elif args.fix:
        # Diffs detected and fixed in fix mode
        logger.info("README files updated successfully.")
        sys.exit(EXIT_SUCCESS)
    else:
        # Diffs detected in check mode
        logger.error("README files are out of sync. Run with --fix to update them.")
        sys.exit(EXIT_DIFF_DETECTED)
