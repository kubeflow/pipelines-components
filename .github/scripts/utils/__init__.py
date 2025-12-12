"""Shared utilities for scripts."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Sequence

# Add scripts directory to path for imports
_SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from generate_readme.metadata_parser import MetadataParser


def get_repo_root() -> Path:
    """Get the repository root directory."""
    return Path(__file__).resolve().parents[3]


def get_default_targets() -> tuple[Path, Path]:
    """Get the default component and pipeline target directories."""
    repo_root = get_repo_root()
    return (repo_root / "components", repo_root / "pipelines")


def normalize_targets(raw_paths: Sequence[str], repo_root: Path | None = None) -> List[Path]:
    """Normalize target paths to absolute Path objects.
    
    Args:
        raw_paths: Sequence of path strings (can be relative or absolute).
        repo_root: Repository root path. If None, will be calculated automatically.
    
    Returns:
        List of normalized absolute Path objects.
    
    Raises:
        FileNotFoundError: If any specified path does not exist.
    """
    if repo_root is None:
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


def find_pipeline_functions(file_path: Path) -> List[str]:
    """Find all function names decorated with @dsl.pipeline.
    
    Args:
        file_path: Path to the Python file to parse.
    
    Returns:
        List of function names that are decorated with @dsl.pipeline.
    """
    return find_functions_with_decorator(file_path, 'pipeline')


def find_functions_with_decorator(file_path: Path, decorator_type: str) -> List[str]:
    """Find all function names decorated with a specific KFP decorator
    
    Args:
        file_path: Path to the Python file to parse.
        decorator_type: Type of decorator to find ('component' or 'pipeline').
    
    Returns:
        List of function names that are decorated with the specified decorator.
    """
    import ast
    
    parser = MetadataParser(file_path, decorator_type)
    tree = parser._get_ast_tree()
    
    functions: List[str] = []
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                if parser._is_target_decorator(decorator):
                    functions.append(node.name)
                    break  # Found the decorator, no need to check other decorators
    
    return functions
