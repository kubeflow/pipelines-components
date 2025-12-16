"""Path-related utility functions."""

from __future__ import annotations

from pathlib import Path
from typing import List, Sequence


def get_repo_root() -> Path:
    """Get the repository root directory."""
    return Path(__file__).resolve().parents[2]


def get_default_targets() -> tuple[Path, Path]:
    """Get the default component and pipeline target directories."""
    repo_root = get_repo_root()
    return (repo_root / "components", repo_root / "pipelines")


def normalize_targets(raw_paths: Sequence[str]) -> List[Path]:
    """Normalize target paths to absolute Path objects.

    Args:
        raw_paths: Sequence of path strings (can be relative or absolute).

    Returns:
        List of normalized absolute Path objects.

    Raises:
        FileNotFoundError: If any specified path does not exist.
    """
    repo_root = get_repo_root()
    default_targets = get_default_targets()

    if not raw_paths:
        return [target for target in default_targets if target.exists()]

    normalized: List[Path] = []
    for raw in raw_paths:
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = (repo_root / candidate).resolve()
        else:
            candidate = candidate.resolve()
        if not candidate.exists():
            raise FileNotFoundError(f"Specified path does not exist: {raw}")
        normalized.append(candidate)
    return normalized
