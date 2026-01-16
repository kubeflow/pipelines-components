"""Shared test utilities for scripts/lib tests."""

import shutil
from pathlib import Path


def copy_fixture(test_data_dir: Path, fixture_name: str, dest: Path) -> Path:
    """Copy a test fixture file to the destination path.

    Args:
        test_data_dir: Directory containing test fixtures.
        fixture_name: Name of the fixture file to copy.
        dest: Destination path for the copied file.

    Returns:
        Path to the copied file.
    """
    src = test_data_dir / fixture_name
    return Path(shutil.copy(src, dest))
