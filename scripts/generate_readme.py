#!/usr/bin/env python3
"""
Generate README.md documentation for Kubeflow Pipelines components.

This script introspects Python functions decorated with @dsl.component to extract
function metadata and generate comprehensive README documentation following the
standards outlined in KEP-913: Components Repository.

Usage:
    python scripts/generate_readme.py path/to/component.py
    python scripts/generate_readme.py --output custom_readme.md path/to/component.py
    python scripts/generate_readme.py --verbose --overwrite path/to/component.py
"""

import argparse
import importlib
from pathlib import Path
import sys
from typing import Any, Optional, Dict, Union
import ast
import inspect
import re
import argparse
import importlib.util


class ComponentMetadataParser:
    """Introspects KFP component functions to extract documentation metadata."""

    # Regex pattern for Google-style argument lines: "arg_name (type): description"    
    GOOGLE_ARG_REGEX_PATTERN = r'\s*(\w+)\s*\(([^)]+)\):\s*(.*)'

    
    def __init__(self, component_file: Path):
        """Initialize the introspector with a component file.
        
        Args:
            component_file: Path to the Python file containing the component function.
        """
        self.component_file = component_file
        self.component_function = None
        self.component_metadata = {}
    
    def find_component_function(self) -> Optional[str]:
        """Find the function decorated with @dsl.component.
        
        Returns:
            The name of the component function, or None if not found.
        """
        try:
            with open(self.component_file, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if function has @dsl.component decorator
                    for decorator in node.decorator_list:
                        if self._is_component_decorator(decorator):
                            return node.name
            
            return None
        except Exception as e:
            print(f"Error parsing file {self.component_file}: {e}")
            return None
    
    def _is_component_decorator(self, decorator: ast.AST) -> bool:
        """Check if a decorator is a KFP component decorator.
        
        Supports the following decorator formats:
        - @component (direct import: from kfp.dsl import component)
        - @dsl.component (from kfp import dsl)
        - @kfp.dsl.component (import kfp)
        - All of the above with parentheses: @component(), @dsl.component(), etc.
        
        Args:
            decorator: AST node representing the decorator.
            
        Returns:
            True if the decorator is a KFP component decorator, False otherwise.
        """
        if isinstance(decorator, ast.Attribute):
            # Handle attribute-based decorators
            if decorator.attr == 'component':
                # Check for @dsl.component
                if isinstance(decorator.value, ast.Name) and decorator.value.id == 'dsl':
                    return True
                # Check for @kfp.dsl.component
                if (isinstance(decorator.value, ast.Attribute) and 
                    decorator.value.attr == 'dsl' and
                    isinstance(decorator.value.value, ast.Name) and
                    decorator.value.value.id == 'kfp'):
                    return True
            return False
        elif isinstance(decorator, ast.Call):
            # Handle decorators with arguments (e.g., @component(), @dsl.component())
            return self._is_component_decorator(decorator.func)
        elif isinstance(decorator, ast.Name):
            # Handle @component (if imported directly)
            return decorator.id == 'component'
        return False



def validate_component_file(file_path: str) -> Path:
    """Validate that the component file exists and is a valid Python file.
    
    Args:
        file_path: String path to the component file.
        
    Returns:
        Path: Validated Path object.
        
    Raises:
        argparse.ArgumentTypeError: If validation fails.
    """
    path = Path(file_path)
    
    if not path.exists():
        raise argparse.ArgumentTypeError(f"Component file '{file_path}' does not exist")
    
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"'{file_path}' is not a file")
    
    if path.suffix != '.py':
        raise argparse.ArgumentTypeError(f"'{file_path}' is not a Python file (must have .py extension)")
    
    return path


def parse_arguments():
    """Parse and validate command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed and validated arguments.
    """
    parser = argparse.ArgumentParser(
        description="Generate README.md documentation for Kubeflow Pipelines components",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run scripts/generate_readme.py components/my_component/component.py
  uv run scripts/generate_readme.py --output custom_readme.md components/my_component/component.py
  uv run scripts/generate_readme.py --verbose components/my_component/component.py
        """
    )
    
    parser.add_argument(
        'component_file',
        type=validate_component_file,
        help='Path to the Python file containing the @dsl.component decorated function'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Output path for the generated README.md (default: README.md in component directory)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Overwrite existing README.md without prompting'
    )
    
    return parser.parse_args()


def main():
    """Main entry point for the script."""
    args = parse_arguments()
    
    # Initialize introspector
    component_parser = ComponentMetadataParser(args.component_file)

     # Find the component function
    if args.verbose:
        print(f"Analyzing component file: {args.component_file}")
    
    function_name = component_parser.find_component_function()
    if not function_name:
        print(f"Error: No function decorated with @dsl.component found in {args.component_file}")
        sys.exit(1)
    
    if args.verbose:
        print(f"Found component function: {function_name}")
    

if __name__ == "__main__":
    main()
