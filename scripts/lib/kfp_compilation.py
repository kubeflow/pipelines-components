"""KFP module loading and compilation utilities."""

import ast
import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml

COMPONENT_DECORATORS = {"component", "container_component", "notebook_component"}
PIPELINE_DECORATORS = {"pipeline"}


def _merge_ir_docs(docs: list[dict[str, Any]]) -> dict[str, Any]:
    """Merge multiple IR YAML docs so deploymentSpec, root, components are combined."""
    if not docs:
        return {}
    if len(docs) == 1:
        return docs[0]

    def _get(d: Any, path: list[str]) -> dict[str, Any]:
        for k in path:
            d = (d.get(k) or {}) if isinstance(d, dict) else {}
        return d if isinstance(d, dict) else {}

    def _ensure_and_merge(out: dict[str, Any], path: list[str], src: dict[str, Any]) -> None:
        cur: Any = out
        for k in path[:-1]:
            cur = cur.setdefault(k, {}) if isinstance(cur, dict) else {}
        if not path or not isinstance(cur, dict):
            return
        key = path[-1]
        target = cur.get(key)
        if not isinstance(target, dict):
            cur[key] = {}
            target = cur[key]
        target.update(src)

    out: dict[str, Any] = dict(docs[0])
    paths = [["deploymentSpec", "executors"], ["root", "dag", "tasks"], ["components"]]
    for doc in docs[1:]:
        if not isinstance(doc, dict):
            continue
        for path in paths:
            src = _get(doc, path)
            if src:
                _ensure_and_merge(out, path, src)
    return out


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

    Uses safe_load_all; merges deploymentSpec/root/components when multiple docs.

    Args:
        func: The KFP component or pipeline function to compile.
        output_path: Path to write the compiled YAML.

    Returns:
        Parsed YAML dict.

    Raises:
        Exception: If compilation fails.
    """
    compiler_mod = importlib.import_module("kfp.compiler")
    compiler_class = getattr(compiler_mod, "Compiler")
    compiler_class().compile(func, output_path)
    with open(output_path) as f:
        docs = list(yaml.safe_load_all(f))
    if not docs:
        return {}
    if len(docs) == 1:
        return docs[0]
    return _merge_ir_docs(docs)


def find_decorated_functions_runtime(module: Any, decorator_type: str) -> list[tuple[str, Any]]:
    """Find all functions decorated with @dsl.component or @dsl.pipeline at runtime.

    Args:
        module: The loaded Python module.
        decorator_type: Either 'component' or 'pipeline'.

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
        is_component = hasattr(attr, "component_spec") or (
            getattr(attr, "__wrapped__", None) is not None and hasattr(getattr(attr, "__wrapped__"), "component_spec")
        )
        is_pipeline = hasattr(attr, "pipeline_spec") or getattr(attr, "_pipeline_func", None) is not None
        is_match = (decorator_type == "component" and is_component) or (decorator_type == "pipeline" and is_pipeline)
        if is_match:
            functions.append((attr_name, attr))
    return functions


def find_decorated_function_names_ast(file_path: Path) -> dict[str, list[str]]:
    """Find functions decorated with KFP decorators in a Python file.

    Args:
        file_path: Path to the Python file to analyze.

    Returns:
        A dict mapping decorator type to list of function names:
        {"components": [...], "pipelines": [...]}
        Returns empty dict {} if the file cannot be parsed.
    """
    try:
        content = file_path.read_text()
        tree = ast.parse(content)
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"  Warning: Could not parse {file_path}: {e}")
        return {}

    result: dict[str, list[str]] = {"components": [], "pipelines": []}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                decorator_name = extract_decorator_name(decorator)
                if decorator_name is not None and decorator_name in COMPONENT_DECORATORS:
                    result["components"].append(node.name)
                    break
                if decorator_name is not None and decorator_name in PIPELINE_DECORATORS:
                    result["pipelines"].append(node.name)
                    break

    return result


def extract_decorator_name(decorator: ast.expr) -> str | None:
    """Extract the name from a decorator AST node.

    Handles @name, @module.name, and @name() call forms.

    Args:
        decorator: AST node representing the decorator.

    Returns:
        The decorator name, or None if it cannot be determined.
    """
    if isinstance(decorator, ast.Name):
        return decorator.id
    if isinstance(decorator, ast.Attribute):
        return decorator.attr
    if isinstance(decorator, ast.Call):
        if isinstance(decorator.func, ast.Name):
            return decorator.func.id
        if isinstance(decorator.func, ast.Attribute):
            return decorator.func.attr
    return None
