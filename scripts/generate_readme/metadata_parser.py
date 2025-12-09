"""Metadata parsers for KFP components and pipelines.

This module uses AST (Abstract Syntax Tree) parsing to extract metadata from
Python source files WITHOUT executing them. This is important for security
since we don't want to run arbitrary user-provided code.
"""

import ast
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

from docstring_parser import parse as parse_docstring

logger = logging.getLogger(__name__)


class MetadataParser:
    """Base class for parsing KFP function metadata with shared utilities.

    Uses AST parsing to safely extract metadata without executing code.
    """

    def __init__(self, file_path: Path, function_type: str):
        """Initialize the parser with a file path.

        Args:
            file_path: Path to the Python file containing the function.
            function_type: Type of function to parse ('component' or 'pipeline').
        """
        self.file_path = file_path
        self._source: Optional[str] = None
        self._tree: Optional[ast.AST] = None
        self.function_type = function_type

    def _get_ast_tree(self) -> ast.AST:
        """Get the parsed AST tree, caching for reuse.

        Returns:
            The parsed AST tree.
        """
        if self._tree is None:
            with open(self.file_path, "r", encoding="utf-8") as f:
                self._source = f.read()
            self._tree = ast.parse(self._source)
        return self._tree

    def _parse_google_docstring(self, docstring: str) -> Dict[str, Any]:
        """Parse Google-style docstring to extract Args and Returns sections.

        Args:
            docstring: The function's docstring.

        Returns:
            Dictionary containing parsed docstring information.
        """
        if not docstring:
            return {"overview": "", "args": {}, "returns_description": ""}

        # Parse docstring using docstring-parser library
        parsed = parse_docstring(docstring)

        # Extract overview (short description + long description)
        overview_parts = []
        if parsed.short_description:
            overview_parts.append(parsed.short_description)
        if parsed.long_description:
            overview_parts.append(parsed.long_description)
        overview = "\n\n".join(overview_parts)

        # Extract arguments
        args = {param.arg_name: param.description for param in parsed.params}

        # Extract returns description
        returns_description = parsed.returns.description if parsed.returns else ""

        return {"overview": overview, "args": args, "returns_description": returns_description}

    def _annotation_to_string(self, node: Optional[ast.AST]) -> str:
        """Convert an AST type annotation to string.

        Args:
            node: AST node representing a type annotation.

        Returns:
            String representation of the type, or 'Any' if None.
        """
        if node is None:
            return "Any"
        return ast.unparse(node)

    def _default_to_value(self, node: Optional[ast.AST]) -> Any:
        """Convert an AST default value to a Python value.

        Args:
            node: AST node representing a default value.

        Returns:
            The Python value for simple literals, string for complex expressions,
            or None if no default.
        """
        if node is None:
            return None

        # For constants (int, float, str, bool, None), return the actual value
        if isinstance(node, ast.Constant):
            return node.value

        # For everything else, return the source code string
        return ast.unparse(node)

    def _extract_decorator_name(self, decorator: ast.AST) -> Optional[str]:
        """Extract the 'name' parameter from a decorator if present.

        Args:
            decorator: AST node representing the decorator.

        Returns:
            The name parameter value if found, None otherwise.
        """
        # Check if decorator is a Call node (has arguments)
        if isinstance(decorator, ast.Call):
            # Look for name parameter in keyword arguments
            for keyword in decorator.keywords:
                if keyword.arg == "name":
                    # Extract the string value
                    if isinstance(keyword.value, ast.Constant):
                        return keyword.value.value
        return None

    def _find_function_node(self, function_name: str) -> Optional[Union[ast.FunctionDef, ast.AsyncFunctionDef]]:
        """Find the AST node for a function by name.

        Args:
            function_name: Name of the function to find.

        Returns:
            The AST FunctionDef or AsyncFunctionDef node, or None if not found.
        """
        tree = self._get_ast_tree()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
                return node
        return None

    def _get_name_from_decorator_if_exists(self, function_name: str) -> Optional[str]:
        """Get the decorator's name parameter for a specific function.

        Args:
            function_name: Name of the function to find.

        Returns:
            The name parameter from the decorator if found, None otherwise.
        """
        try:
            func_node = self._find_function_node(function_name)
            if func_node is None:
                return None

            # Check decorators for name parameter
            for decorator in func_node.decorator_list:
                decorator_name = self._extract_decorator_name(decorator)
                if decorator_name:
                    return decorator_name

            return None
        except Exception as e:
            logger.debug(f"Could not extract decorator name from AST: {e}")
            return None

    def _extract_function_metadata(self, function_name: str) -> Dict[str, Any]:
        """Extract metadata from a KFP function using AST parsing.

        This method uses AST parsing to safely extract metadata WITHOUT
        executing any code from the source file. This is important for
        security when processing user-provided files.

        Args:
            function_name: Name of the function to introspect.

        Returns:
            Dictionary containing extracted metadata.
        """
        try:
            func_node = self._find_function_node(function_name)
            if func_node is None:
                logger.error(f"Function {function_name} not found in {self.file_path}")
                return {}

            # Try to get name from decorator, fall back to function name
            decorator_name = self._get_name_from_decorator_if_exists(function_name)
            component_name = decorator_name if decorator_name else function_name

            # Extract docstring using ast.get_docstring
            docstring = ast.get_docstring(func_node) or ""

            # Parse docstring for Args and Returns sections
            docstring_info = self._parse_google_docstring(docstring)

            # Extract basic function information
            metadata = {"name": component_name, "docstring": docstring, "parameters": {}, "returns": {}}
            metadata.update(docstring_info)

            # Extract parameter information from AST
            args_node = func_node.args

            # Process regular positional/keyword arguments
            # Defaults are aligned to the END of the args list
            num_defaults = len(args_node.defaults)
            num_args = len(args_node.args)
            for i, arg in enumerate(args_node.args):
                default_node = None
                if i >= num_args - num_defaults:
                    # This arg has a default
                    default_idx = i - (num_args - num_defaults)
                    default_node = args_node.defaults[default_idx]

                metadata["parameters"][arg.arg] = {
                    "name": arg.arg,
                    "type": self._annotation_to_string(arg.annotation),
                    "default": self._default_to_value(default_node),
                    "description": metadata.get("args", {}).get(arg.arg, ""),
                }

            # Process keyword-only arguments
            for arg, default_node in zip(args_node.kwonlyargs, args_node.kw_defaults):
                metadata["parameters"][arg.arg] = {
                    "name": arg.arg,
                    "type": self._annotation_to_string(arg.annotation),
                    "default": self._default_to_value(default_node),
                    "description": metadata.get("args", {}).get(arg.arg, ""),
                }

            # Extract return type information
            if func_node.returns is not None:
                metadata["returns"] = {
                    "type": self._annotation_to_string(func_node.returns),
                    "description": metadata.get("returns_description", ""),
                }

            return metadata

        except Exception as e:
            logger.error(f"Error extracting metadata for function {function_name}: {e}")
            return {}

    def _is_target_decorator(self, decorator: ast.AST) -> bool:
        """Check if a decorator is a KFP component or pipeline decorator.

        Supports the following decorator formats:
        - @component (direct import: from kfp.dsl import component)
        - @dsl.pipeline (from kfp import dsl)
        - @kfp.dsl.component (import kfp)
        - All of the above with parentheses: @pipeline(), @dsl.component(), etc.

        Args:
            decorator: AST node representing the decorator.

        Returns:
            True if the decorator is the given decoration_type, False otherwise.
        """
        if isinstance(decorator, ast.Attribute):
            # Handle attribute-based decorators
            if decorator.attr == self.function_type:
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
            return self._is_target_decorator(decorator.func)
        elif isinstance(decorator, ast.Name):
            # Handle @<function_type> (if imported directly)
            return decorator.id == self.function_type
        return False

    def extract_metadata(self, function_name: str) -> Dict[str, Any]:
        """Extract metadata from the component function.

        Args:
            function_name: Name of the component function to introspect.

        Returns:
            Dictionary containing extracted metadata.
        """
        return self._extract_function_metadata(function_name)

    def find_function(self) -> Optional[str]:
        """Find the function decorated with @dsl.component.

        Returns:
            The name of the component function, or None if not found.
        """
        try:
            tree = self._get_ast_tree()

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Check if function has @dsl.component decorator
                    for decorator in node.decorator_list:
                        if self._is_target_decorator(decorator):
                            return node.name

            return None
        except Exception as e:
            logger.error(f"Error parsing file {self.file_path}: {e}")
            return None
