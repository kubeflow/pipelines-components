#!/usr/bin/env python3
"""Validate that all components and pipelines compile successfully."""

import ast
import sys
from pathlib import Path


def find_decorated_functions(file_path: Path) -> dict[str, list[str]]:
    """Find functions decorated with KFP decorators in a Python file.
    
    Returns a dict mapping decorator type to list of function names.
    """
    try:
        content = file_path.read_text()
        tree = ast.parse(content)
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"  Warning: Could not parse {file_path}: {e}")
        return {}

    component_decorators = {"component", "container_component"}
    pipeline_decorators = {"pipeline"}

    result = {"components": [], "pipelines": []}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                decorator_name = None
                if isinstance(decorator, ast.Name):
                    decorator_name = decorator.id
                elif isinstance(decorator, ast.Attribute):
                    decorator_name = decorator.attr
                elif isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Name):
                        decorator_name = decorator.func.id
                    elif isinstance(decorator.func, ast.Attribute):
                        decorator_name = decorator.func.attr

                if decorator_name in component_decorators:
                    result["components"].append(node.name)
                    break
                elif decorator_name in pipeline_decorators:
                    result["pipelines"].append(node.name)
                    break

    return result


def validate_imports() -> bool:
    """Validate that package structure imports correctly."""
    print("Validating package imports...")
    success = True

    packages = [
        ("components", ["training", "evaluation", "data_processing", "deployment"]),
        ("pipelines", ["training", "evaluation", "data_processing", "deployment"]),
    ]

    for package, submodules in packages:
        for submodule in submodules:
            module_path = f"{package}.{submodule}"
            try:
                __import__(module_path)
                print(f"  ✓ {module_path}")
            except ImportError as e:
                print(f"  ✗ {module_path}: {e}")
                success = False

    return success


def validate_compilation() -> bool:
    """Find and validate all components and pipelines."""
    print("\nValidating component/pipeline compilation...")

    try:
        from kfp import compiler
    except ImportError:
        print("  Error: kfp not installed")
        return False

    success = True
    found_any = False

    for directory in ["components", "pipelines", "third_party"]:
        dir_path = Path(directory)
        if not dir_path.exists():
            continue

        for py_file in dir_path.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue

            decorated = find_decorated_functions(py_file)
            if not decorated["components"] and not decorated["pipelines"]:
                continue

            found_any = True
            module_path = str(py_file.with_suffix("")).replace("/", ".")

            # Validate components using component_spec
            for func_name in decorated["components"]:
                try:
                    module = __import__(module_path, fromlist=[func_name])
                    func = getattr(module, func_name)

                    # Components have component_spec attribute - save it to validate
                    if hasattr(func, "component_spec"):
                        func.component_spec.save(f"/tmp/{func_name}_component.yaml")
                        print(f"  ✓ {module_path}.{func_name} (component)")
                    else:
                        print(f"  ✗ {module_path}.{func_name}: not a valid KFP component")
                        success = False
                except Exception as e:
                    print(f"  ✗ {module_path}.{func_name}: {e}")
                    success = False

            # Validate pipelines using compiler
            for func_name in decorated["pipelines"]:
                try:
                    module = __import__(module_path, fromlist=[func_name])
                    func = getattr(module, func_name)

                    compiler.Compiler().compile(func, f"/tmp/{func_name}_pipeline.yaml")
                    print(f"  ✓ {module_path}.{func_name} (pipeline)")
                except Exception as e:
                    print(f"  ✗ {module_path}.{func_name}: {e}")
                    success = False

    if not found_any:
        print("  No components or pipelines found to compile")

    return success


def main() -> int:
    sys.path.insert(0, ".")

    imports_ok = validate_imports()
    compilation_ok = validate_compilation()

    print()
    if imports_ok and compilation_ok:
        print("✓ All validations passed")
        return 0
    else:
        print("✗ Some validations failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
