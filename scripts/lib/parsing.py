"""AST-based utilities for finding KFP decorated functions."""

import ast
from pathlib import Path


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


def _is_target_decorator(decorator: ast.AST, decorator_type: str) -> bool:
    """Check if a decorator is a KFP component or pipeline decorator.

    Supports the following decorator formats (using component as an example):
    - @component (direct import: from kfp.dsl import component)
    - @dsl.component (from kfp import dsl)
    - @kfp.dsl.component (import kfp)
    - All of the above with parentheses: @component(), @dsl.component(), etc.

    Args:
        decorator: AST node representing the decorator.
        decorator_type: Type of decorator to find ('component' or 'pipeline').

    Returns:
        True if the decorator is the given decoration_type, False otherwise.
    """
    if isinstance(decorator, ast.Attribute):
        if decorator.attr == decorator_type:
            if isinstance(decorator.value, ast.Name) and decorator.value.id == "dsl":
                return True
            if (
                isinstance(decorator.value, ast.Attribute)
                and decorator.value.attr == "dsl"
                and isinstance(decorator.value.value, ast.Name)
                and decorator.value.value.id == "kfp"
            ):
                return True
        return False
    elif isinstance(decorator, ast.Call):
        return _is_target_decorator(decorator.func, decorator_type)
    elif isinstance(decorator, ast.Name):
        return decorator.id == decorator_type
    return False


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
