#!/usr/bin/env python3
"""
Override base_image references from :main to PR-specific SHA tags.

This script is used during CI to replace :main tags with commit-specific SHA tags
so that PR validation tests use the freshly-built images instead of the latest main.
"""

import argparse
import re
import sys
from pathlib import Path


def override_file_images(
    file_path: Path, commit_sha: str, image_prefix: str, dry_run: bool = False
) -> tuple[bool, str | None]:
    """
    Override base_image references in a single file from :main to :commit_sha.

    Args:
        file_path: Path to the Python file to modify.
        commit_sha: The commit SHA to use as the new tag.
        image_prefix: The image prefix to look for.
        dry_run: If True, don't write changes to disk.

    Returns:
        Tuple of (was_modified, new_content). was_modified is True if changes were made.

    Raises:
        OSError: If the file cannot be read or written.
        UnicodeDecodeError: If the file contains invalid encoding.
    """
    original_content = file_path.read_text()

    escaped_prefix = re.escape(image_prefix)
    pattern = rf"({escaped_prefix}-[^:\"']+):main"
    replacement = rf"\1:{commit_sha}"

    new_content, count = re.subn(pattern, replacement, original_content)

    if count > 0:
        if not dry_run:
            file_path.write_text(new_content)
        return True, new_content

    return False, None


def override_base_images(
    directories: list[str],
    commit_sha: str,
    image_prefix: str,
    dry_run: bool = False,
    verbose: bool = True,
) -> list[str]:
    """
    Override base_image references in all Python files from :main to :commit_sha.

    Args:
        directories: List of directory names to scan.
        commit_sha: The commit SHA to use as the new tag.
        image_prefix: The image prefix to look for.
        dry_run: If True, don't write changes to disk.
        verbose: Whether to print progress messages.

    Returns:
        List of file paths that were modified.
    """
    modified_files = []

    if verbose:
        print(f"Overriding base_image references from :main to :{commit_sha}")

    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            continue

        for py_file in dir_path.rglob("*.py"):
            was_modified, _ = override_file_images(
                py_file, commit_sha, image_prefix, dry_run
            )
            if was_modified:
                modified_files.append(str(py_file))
                if verbose:
                    action = "Would update" if dry_run else "Updating"
                    print(f"{action}: {py_file}")

    return modified_files


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Override base_image references from :main to PR-specific SHA tags"
    )
    parser.add_argument(
        "commit_sha", help="The commit SHA to use as the new image tag"
    )
    parser.add_argument(
        "image_prefix",
        nargs="?",
        default="ghcr.io/kubeflow/pipelines-components",
        help="Image prefix to override (default: ghcr.io/kubeflow/pipelines-components)",
    )
    parser.add_argument(
        "--directories",
        nargs="+",
        default=["components", "pipelines", "third_party"],
        help="Directories to scan (default: components pipelines third_party)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be changed without making changes",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress progress output"
    )

    args = parser.parse_args()

    if not args.commit_sha:
        print("Error: commit_sha is required", file=sys.stderr)
        return 1

    override_base_images(
        args.directories,
        args.commit_sha,
        args.image_prefix,
        dry_run=args.dry_run,
        verbose=not args.quiet,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())

