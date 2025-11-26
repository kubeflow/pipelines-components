"""KFP compilation utilities."""

import importlib.util
import sys
from pathlib import Path
from typing import Any

import yaml


def load_module_from_path(module_path: str, module_name: str) -> Any:
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


def compile_and_get_yaml(func: Any, output_path: str) -> dict[str, Any] | None:
    """Compile a component or pipeline function and return the parsed YAML.

    Args:
        func: The KFP component or pipeline function to compile.
        output_path: Path to write the compiled YAML.

    Returns:
        Parsed YAML dict, or None if compilation fails.
    """
    try:
        from kfp import compiler

        compiler.Compiler().compile(func, output_path)
        with open(output_path) as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"  Warning: Failed to compile {func}: {e}")
        return None


def module_path_from_file(py_file: Path) -> str:
    """Convert a file path to a Python module path.

    Args:
        py_file: Path to a Python file.

    Returns:
        Dotted module path string (e.g., 'components.training.my_component').
    """
    return ".".join(py_file.with_suffix("").parts)


def find_decorated_functions_runtime(module: Any, decorator_type: str) -> list[tuple[str, Any]]:
    """Find all functions decorated with @dsl.component or @dsl.pipeline at runtime.

    Args:
        module: The loaded Python module
        decorator_type: Either 'component' or 'pipeline'

    Returns:
        List of tuples (function_name, function_object)
    """
    functions = []

    for attr_name in dir(module):
        if attr_name.startswith("_"):
            continue

        attr = getattr(module, attr_name, None)
        if attr is None or not callable(attr):
            continue

        is_component = (
            hasattr(attr, "component_spec")
            or getattr(attr, "__wrapped__", None) is not None
            and hasattr(getattr(attr, "__wrapped__"), "component_spec")
        )
        is_pipeline = hasattr(attr, "pipeline_spec") or getattr(attr, "_pipeline_func", None) is not None

        is_match = (decorator_type == "component" and is_component) or (decorator_type == "pipeline" and is_pipeline)
        if is_match:
            functions.append((attr_name, attr))

    return functions


def find_any_decorated_functions(module: Any) -> list[tuple[str, Any]]:
    """Fallback to find any KFP decorated functions in a module.

    Args:
        module: The loaded Python module.

    Returns:
        List of tuples (function_name, function_object).
    """
    functions = []
    for attr_name in dir(module):
        if attr_name.startswith("_"):
            continue
        attr = getattr(module, attr_name, None)
        if attr is None or not callable(attr):
            continue
        if hasattr(attr, "component_spec") or hasattr(attr, "pipeline_spec"):
            functions.append((attr_name, attr))
    return functions
