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
import logging
import re
import argparse
import importlib.util

# Set up logger
logger = logging.getLogger(__name__)


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
            logger.error(f"Error parsing file {self.component_file}: {e}")
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

        
    def extract_component_metadata(self, function_name: str) -> Dict[str, Any]:
        """Extract metadata from the component function.
        
        Args:
            function_name: Name of the component function to introspect.
            
        Returns:
            Dictionary containing extracted metadata.
        """
        try:
            # Import the module to get the actual function object
            spec = importlib.util.spec_from_file_location("component_module", self.component_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            component_obj = getattr(module, function_name)
            
            # The @dsl.component decorator wraps the function, so we need to access the underlying function
            # KFP components store the original function in the 'python_func' attribute
            if hasattr(component_obj, 'python_func'):
                func = component_obj.python_func
            else:
                # Fallback to the component object itself if python_func is not available
                func = component_obj
            
            # Extract basic function information
            metadata = {
                'name': function_name,
                'docstring': inspect.getdoc(func) or '',
                'signature': inspect.signature(func),
                'parameters': {},
                'returns': {}
            }
            
            # Parse docstring for Args and Returns sections
            docstring_info = self._parse_google_docstring(metadata['docstring'])
            metadata.update(docstring_info)
            
            # Extract parameter information
            for param_name, param in metadata['signature'].parameters.items():
                param_info = {
                    'name': param_name,
                    'type': self._get_type_string(param.annotation),
                    'default': param.default if param.default != inspect.Parameter.empty else None,
                    'description': metadata.get('args', {}).get(param_name, '')
                }
                metadata['parameters'][param_name] = param_info
            
            # Extract return type information
            return_annotation = metadata['signature'].return_annotation
            if return_annotation != inspect.Signature.empty:
                metadata['returns'] = {
                    'type': self._get_type_string(return_annotation),
                    'description': metadata.get('returns_description', '')
                }
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata for function {function_name}: {e}")
            return {}
    
    def _parse_google_docstring(self, docstring: str) -> Dict[str, Any]:
        """Parse Google-style docstring to extract Args and Returns sections.
        
        Args:
            docstring: The function's docstring.
            
        Returns:
            Dictionary containing parsed docstring information.
        """
        if not docstring:
            return {'overview': '', 'args': {}, 'returns_description': ''}
        
        # Split docstring into lines
        lines = docstring.strip().split('\n')
        
        # Extract overview (everything before Args/Returns sections)
        overview_lines = []
        current_section = None
        args = {}
        returns_description = ''
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if line.lower().startswith('args:'):
                current_section = 'args'
                i += 1
                continue
            elif line.lower().startswith('returns:'):
                current_section = 'returns'
                i += 1
                continue
            elif line.lower().startswith(('raises:', 'yields:', 'note:', 'example:')):
                current_section = 'other'
                i += 1
                continue
            
            if current_section is None:
                # Still in overview section
                overview_lines.append(lines[i])
            elif current_section == 'args':
                # Parse argument line
                arg_match = re.match(self.GOOGLE_ARG_REGEX_PATTERN, line)
                if arg_match:
                    arg_name, arg_type, arg_desc = arg_match.groups()
                    args[arg_name] = arg_desc.strip()
                elif line and args:
                    # Continuation of previous argument description
                    last_arg = list(args.keys())[-1]
                    args[last_arg] += ' ' + line
            elif current_section == 'returns':
                # Parse returns section
                if line:
                    returns_description += line + ' '
            
            i += 1
        
        return {
            'overview': '\n'.join(overview_lines).strip(),
            'args': args,
            'returns_description': returns_description.strip()
        }
    
    def _get_type_string(self, annotation: Any) -> str:
        """Convert type annotation to string representation.
        
        Args:
            annotation: The type annotation object.
            
        Returns:
            String representation of the type.
        """
        if annotation == inspect.Parameter.empty or annotation == inspect.Signature.empty:
            return 'Any'
        
        if hasattr(annotation, '__name__'):
            return annotation.__name__
        elif hasattr(annotation, '__origin__'):
            # Handle generic types like List[str], Dict[str, int], etc.
            origin = annotation.__origin__
            args = getattr(annotation, '__args__', ())
            
            if origin is Union:
                # Handle Optional[T] and Union types
                if len(args) == 2 and type(None) in args:
                    # Optional type
                    non_none_type = args[0] if args[1] is type(None) else args[1]
                    return f"Optional[{self._get_type_string(non_none_type)}]"
                else:
                    # Union type
                    type_strings = [self._get_type_string(arg) for arg in args]
                    return f"Union[{', '.join(type_strings)}]"
            elif args:
                # Generic type with arguments
                origin_name = getattr(origin, '__name__', str(origin))
                arg_strings = [self._get_type_string(arg) for arg in args]
                return f"{origin_name}[{', '.join(arg_strings)}]"
            else:
                # Generic type without arguments
                return getattr(origin, '__name__', str(origin))
        else:
            return str(annotation)




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
    
    # Configure logging based on verbose flag
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(levelname)s: %(message)s'
    )
    
    # Initialize introspector
    component_parser = ComponentMetadataParser(args.component_file)

    # Find the component function
    logger.debug(f"Analyzing component file: {args.component_file}")
    
    function_name = component_parser.find_component_function()
    if not function_name:
        logger.error(f"No function decorated with @dsl.component found in {args.component_file}")
        sys.exit(1)
    
    logger.debug(f"Found component function: {function_name}")
    
    metadata = component_parser.extract_component_metadata(function_name)
    if not metadata:
        logger.error(f"Could not extract metadata from function {function_name}")
        sys.exit(1)
    
    logger.debug(f"Extracted metadata for {len(metadata.get('parameters', {}))} parameters")
    

if __name__ == "__main__":
    main()
