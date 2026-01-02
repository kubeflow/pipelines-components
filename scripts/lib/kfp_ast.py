"""AST-based KFP decorator detection utilities."""

import ast
from pathlib import Path

COMPONENT_DECORATORS = {"component", "container_component", "notebook_component"}
PIPELINE_DECORATORS = {"pipeline"}


def find_decorated_functions(file_path: Path) -> dict[str, list[str]]:
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
                decorator_name = _extract_decorator_name(decorator)

                if decorator_name in COMPONENT_DECORATORS:
                    result["components"].append(node.name)
                    break
                elif decorator_name in PIPELINE_DECORATORS:
                    result["pipelines"].append(node.name)
                    break

    return result


def _extract_decorator_name(decorator: ast.expr) -> str | None:
    """Extract the decorator name from an AST node."""
    if isinstance(decorator, ast.Name):
        return decorator.id
    elif isinstance(decorator, ast.Attribute):
        return decorator.attr
    elif isinstance(decorator, ast.Call):
        if isinstance(decorator.func, ast.Name):
            return decorator.func.id
        elif isinstance(decorator.func, ast.Attribute):
            return decorator.func.attr
    return None
