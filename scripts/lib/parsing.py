"""AST-based utilities for finding KFP decorated functions."""

import ast
from dataclasses import dataclass
from pathlib import Path

from .kfp_compilation import COMPONENT_DECORATORS, PIPELINE_DECORATORS, extract_decorator_name

_ALL_KFP_DECORATORS = COMPONENT_DECORATORS | PIPELINE_DECORATORS


@dataclass
class BaseImageInfo:
    """Information about a base_image argument in a KFP decorator."""

    func_name: str
    value: str
    start_line: int
    start_col: int
    end_line: int
    end_col: int


def _get_ast_tree(file_path: Path) -> ast.AST:
    """Get the parsed AST tree for a Python file.

    Args:
        file_path: Path to the Python file to parse.

    Returns:
        The parsed AST tree.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()
    return ast.parse(source)


def _is_target_decorator(decorator: ast.expr, decorator_type: str) -> bool:
    """Check if a decorator matches the given decorator type.

    Args:
        decorator: AST node representing the decorator.
        decorator_type: Type of decorator to find ('component', 'pipeline', etc.).

    Returns:
        True if the decorator matches the given type, False otherwise.
    """
    return extract_decorator_name(decorator) == decorator_type


def find_pipeline_functions(file_path: Path) -> list[str]:
    """Find all function names decorated with @dsl.pipeline.

    Args:
        file_path: Path to the Python file to parse.

    Returns:
        List of function names that are decorated with @dsl.pipeline.
    """
    return find_functions_with_decorator(file_path, "pipeline")


def find_functions_with_decorator(file_path: Path, decorator_type: str) -> list[str]:
    """Find all function names decorated with a specific KFP decorator.

    Args:
        file_path: Path to the Python file to parse.
        decorator_type: Type of decorator to find ('component' or 'pipeline').

    Returns:
        List of function names that are decorated with the specified decorator.
    """
    tree = _get_ast_tree(file_path)
    functions: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                if _is_target_decorator(decorator, decorator_type):
                    functions.append(node.name)
                    break

    return functions


def _is_kfp_decorator(decorator: ast.expr) -> bool:
    """Check if a decorator is a KFP component or pipeline decorator."""
    return extract_decorator_name(decorator) in _ALL_KFP_DECORATORS


def _get_base_image_keyword(decorator: ast.Call) -> ast.keyword | None:
    """Find the base_image keyword argument in a decorator call."""
    for keyword in decorator.keywords:
        if keyword.arg == "base_image":
            return keyword
    return None


def _extract_base_image_info(keyword: ast.keyword, func_name: str, file_path: Path) -> BaseImageInfo:
    """Extract BaseImageInfo from a base_image keyword, validating it's a string literal."""
    if not isinstance(keyword.value, ast.Constant) or not isinstance(keyword.value.value, str):
        raise ValueError(f"base_image must be a string literal for function '{func_name}' in {file_path}")

    return BaseImageInfo(
        func_name=func_name,
        value=keyword.value.value,
        start_line=keyword.value.lineno,
        start_col=keyword.value.col_offset,
        end_line=keyword.value.end_lineno or keyword.value.lineno,
        end_col=keyword.value.end_col_offset or keyword.value.col_offset,
    )


def get_base_image_locations(file_path: Path) -> list[BaseImageInfo]:
    """Extract base_image literals with their source positions from KFP decorators.

    Args:
        file_path: Path to the Python file to parse.

    Returns:
        List of BaseImageInfo for each base_image found in component/pipeline decorators.

    Raises:
        ValueError: If any base_image argument is not a string literal.
    """
    tree = _get_ast_tree(file_path)
    results: list[BaseImageInfo] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        for decorator in node.decorator_list:
            if not _is_kfp_decorator(decorator) or not isinstance(decorator, ast.Call):
                continue

            keyword = _get_base_image_keyword(decorator)
            if keyword:
                results.append(_extract_base_image_info(keyword, node.name, file_path))

    return results
