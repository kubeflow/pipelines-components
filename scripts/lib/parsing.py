"""KFP module loading, compilation, and decorator discovery utilities."""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml


def get_ast_tree(file_path: Path) -> ast.AST:
    """Get the parsed AST tree for a Python file.

    Args:
        file_path: Path to the Python file to parse.

    Returns:
        The parsed AST tree.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()
    return ast.parse(source)


def is_target_decorator(decorator: ast.AST, decorator_type: str) -> bool:
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
        # Handle attribute-based decorators
        if decorator.attr == decorator_type:
            # Check for @dsl.<function_type>
            if isinstance(decorator.value, ast.Name) and decorator.value.id == "dsl":
                return True
            # Check for @kfp.dsl.<function_type>
            if (
                isinstance(decorator.value, ast.Attribute)
                and decorator.value.attr == "dsl"
                and isinstance(decorator.value.value, ast.Name)
                and decorator.value.value.id == "kfp"
            ):
                return True
        return False
    elif isinstance(decorator, ast.Call):
        # Handle decorators with arguments (e.g., @<function_type>(), @dsl.<function_type>())
        return is_target_decorator(decorator.func, decorator_type)
    elif isinstance(decorator, ast.Name):
        # Handle @<function_type> (if imported directly)
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
    tree = get_ast_tree(file_path)
    functions: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                if is_target_decorator(decorator, decorator_type):
                    functions.append(node.name)
                    break

    return functions


def load_module_from_path(module_path: str, module_name: str) -> ModuleType:
    """Dynamically load a Python module from a file path.

    Args:
        module_path: File path to the Python module.
        module_name: Name to assign to the loaded module.

    Returns:
        The loaded module object.

    Raises:
        ImportError: If the module cannot be loaded.
    """
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def compile_and_get_yaml(func: Any, output_path: str) -> dict[str, Any]:
    """Compile a component or pipeline function and return the parsed YAML.

    Args:
        func: The KFP component or pipeline function to compile.
        output_path: Path to write the compiled YAML.

    Returns:
        Parsed YAML dict.

    Raises:
        Exception: If compilation fails.
    """
    from kfp import compiler

    compiler.Compiler().compile(func, output_path)
    with open(output_path) as f:
        return yaml.safe_load(f)
