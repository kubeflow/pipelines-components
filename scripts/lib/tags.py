"""Base image tag checking and override utilities."""

import re
from pathlib import Path


def find_base_image_references(file_path: Path, image_prefix: str) -> list[tuple[int, str]]:
    """Find lines containing base_image references to the given image prefix.

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
    """Check if a line uses the :main tag for the image.

    Args:
        line: The line content to check.
        image_prefix: The image prefix to look for.

    Returns:
        Tuple of (is_valid, image_reference). is_valid is True if :main tag is used.
    """
    escaped_prefix = re.escape(image_prefix)
    main_tag_pattern = rf"{escaped_prefix}-[A-Za-z0-9._-]+:main"
    if re.search(main_tag_pattern, line):
        return True, None

    image_pattern = rf"{escaped_prefix}-[A-Za-z0-9._-]+(?::[A-Za-z0-9._-]+)?"
    match = re.search(image_pattern, line)
    if match:
        return False, match.group(0)

    return False, None


def check_base_image_tags(directories: list[str], image_prefix: str) -> tuple[bool, list[dict]]:
    """Check all Python files in directories for proper base_image tag usage.

    Args:
        directories: List of directory paths to scan.
        image_prefix: The image prefix to look for.

    Returns:
        Tuple of (all_valid, results). all_valid is True if all references use :main tag.
        results is a list of dicts with file, line_num, status, and optionally found/expected keys.
    """
    results: list[dict] = []

    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            continue

        for py_file in dir_path.rglob("*.py"):
            try:
                refs = find_base_image_references(py_file, image_prefix)
            except (OSError, UnicodeDecodeError) as e:
                results.append(
                    {
                        "file": str(py_file),
                        "line_num": 0,
                        "status": "invalid",
                        "error": f"Failed to read file: {e}",
                    }
                )
                continue

            for line_num, line in refs:
                is_valid, found_image = check_main_tag(line, image_prefix)
                result: dict = {"file": str(py_file), "line_num": line_num}

                if is_valid:
                    result["status"] = "valid"
                else:
                    result["status"] = "invalid"
                    if found_image:
                        result["found"] = found_image
                        result["expected"] = f"{image_prefix}-<name>:main"
                    else:
                        result["error"] = "failed to parse base_image reference"
                        result["line"] = line

                results.append(result)

    all_valid = all(r["status"] == "valid" for r in results) if results else True
    return all_valid, results


def override_file_images(
    file_path: Path, commit_sha: str, image_prefix: str, dry_run: bool = False
) -> tuple[bool, str | None]:
    """Override base_image references in a single file from :main to :commit_sha.

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
    pattern = rf"({escaped_prefix}-[A-Za-z0-9._-]+):main"
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
    """Override base_image references in all Python files from :main to :commit_sha.

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

    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            continue

        for py_file in dir_path.rglob("*.py"):
            was_modified, _ = override_file_images(py_file, commit_sha, image_prefix, dry_run)
            if was_modified:
                modified_files.append(str(py_file))
                if verbose:
                    action = "Would update" if dry_run else "Updating"
                    print(f"{action}: {py_file}")

    return modified_files
