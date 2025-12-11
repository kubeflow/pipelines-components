#!/usr/bin/env python3
"""
Check that base_image references to pipelines-components images use :main tag.

This ensures components reference the latest images rather than specific SHAs or versions.
The CI will override these with PR-specific tags during validation.
"""

import argparse
import re
import sys
from pathlib import Path


def find_base_image_references(file_path: Path, image_prefix: str) -> list[tuple[int, str]]:
    """
    Find lines containing base_image references to the given image prefix.

    Args:
        file_path: Path to the Python file to scan.
        image_prefix: The image prefix to look for (e.g., ghcr.io/kubeflow/pipelines-components).

    Returns:
        List of tuples (line_number, line_content) for matching lines.

    Raises:
        OSError: If the file cannot be read.
        UnicodeDecodeError: If the file contains invalid encoding.
    """
    matches = []
    content = file_path.read_text()
    for line_num, line in enumerate(content.splitlines(), start=1):
        if "base_image" in line and image_prefix in line:
            matches.append((line_num, line))
    return matches


def check_main_tag(line: str, image_prefix: str) -> tuple[bool, str | None]:
    """
    Check if a line uses the :main tag for the image.

    Args:
        line: The line content to check.
        image_prefix: The image prefix to look for.

    Returns:
        Tuple of (is_valid, image_reference). is_valid is True if :main tag is used.
    """
    escaped_prefix = re.escape(image_prefix)
    main_tag_pattern = rf"{escaped_prefix}-[^:\"']+:main"
    if re.search(main_tag_pattern, line):
        return True, None

    image_pattern = rf"{escaped_prefix}-[^\"\'\s]+"
    match = re.search(image_pattern, line)
    if match:
        return False, match.group(0)

    return False, None


def _build_valid_result(py_file: Path, line_num: int) -> dict:
    """Build a result dict for a valid reference."""
    return {"file": str(py_file), "line_num": line_num, "status": "valid"}


def _build_invalid_result(
    py_file: Path, line_num: int, line: str, found_image: str | None, image_prefix: str
) -> dict:
    """Build a result dict for an invalid reference."""
    result = {"file": str(py_file), "line_num": line_num, "status": "invalid"}
    if found_image:
        result["found"] = found_image
        result["expected"] = f"{image_prefix}-<name>:main"
    else:
        result["error"] = "failed to parse base_image reference"
        result["line"] = line
    return result


def _print_valid_reference(py_file: Path) -> None:
    """Print message for a valid reference."""
    print(f"  ✓ {py_file}: uses :main tag")


def _print_invalid_reference(py_file: Path, found_image: str | None, line: str, image_prefix: str) -> None:
    """Print message for an invalid reference."""
    if found_image:
        print(f"  ✗ {py_file}: does not use :main tag")
        print(f"    Found: {found_image}")
        print(f"    Expected: {image_prefix}-<name>:main")
    else:
        print(f"  ✗ {py_file}: failed to parse base_image reference")
        print(f"    Line: {line}")


def _print_summary(all_valid: bool) -> None:
    """Print the final summary."""
    print()
    if all_valid:
        print("✓ All base_image references use :main tag (or no references found)")
    else:
        print("✗ Some base_image references do not use :main tag")
        print("  Components should reference :main to use the latest images.")
        print("  The CI will override these with PR-specific tags during validation.")


def _get_python_files(directories: list[str]) -> list[Path]:
    """Get all Python files from the given directories."""
    files = []
    for directory in directories:
        dir_path = Path(directory)
        if dir_path.exists():
            files.extend(dir_path.rglob("*.py"))
    return files


def _process_reference(
    py_file: Path, line_num: int, line: str, image_prefix: str, verbose: bool
) -> dict:
    """Process a single base_image reference and return the result."""
    is_valid, found_image = check_main_tag(line, image_prefix)

    if is_valid:
        if verbose:
            _print_valid_reference(py_file)
        return _build_valid_result(py_file, line_num)

    if verbose:
        _print_invalid_reference(py_file, found_image, line, image_prefix)
    return _build_invalid_result(py_file, line_num, line, found_image, image_prefix)


def _collect_all_references(directories: list[str], image_prefix: str) -> list[tuple[Path, int, str]]:
    """Collect all base_image references from Python files in directories."""
    references = []
    for py_file in _get_python_files(directories):
        for line_num, line in find_base_image_references(py_file, image_prefix):
            references.append((py_file, line_num, line))
    return references


def check_base_image_tags(
    directories: list[str], image_prefix: str, verbose: bool = True
) -> tuple[bool, list[dict]]:
    """
    Check all Python files in directories for proper base_image tag usage.

    Args:
        directories: List of directory names to scan.
        image_prefix: The image prefix to look for.
        verbose: Whether to print progress messages.

    Returns:
        Tuple of (all_valid, results). all_valid is True if all references use :main tag.
        results is a list of dicts with file, line_num, status, and optionally found/expected keys.
    """
    if verbose:
        print("Checking that base_image references use :main tag...")

    references = _collect_all_references(directories, image_prefix)
    results = [
        _process_reference(py_file, line_num, line, image_prefix, verbose)
        for py_file, line_num, line in references
    ]
    all_valid = all(r["status"] == "valid" for r in results)

    if verbose:
        _print_summary(all_valid)

    return all_valid, results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check that base_image references use :main tag"
    )
    parser.add_argument(
        "image_prefix",
        nargs="?",
        default="ghcr.io/kubeflow/pipelines-components",
        help="Image prefix to check (default: ghcr.io/kubeflow/pipelines-components)",
    )
    parser.add_argument(
        "--directories",
        nargs="+",
        default=["components", "pipelines", "third_party"],
        help="Directories to scan (default: components pipelines third_party)",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress progress output"
    )

    args = parser.parse_args()

    all_valid, _ = check_base_image_tags(
        args.directories, args.image_prefix, verbose=not args.quiet
    )

    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())

