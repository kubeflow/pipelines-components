"""Metadata parsers for KFP components and pipelines."""

import ast
import importlib.util
import inspect
from pathlib import Path
from typing import Any, Dict, Optional, Union
from abc import ABC, abstractmethod

from docstring_parser import parse as parse_docstring

from .constants import logger

# For Union type checking in _get_type_string
try:
    from types import UnionType
except ImportError:
    UnionType = type(Union[int, str])  # Fallback for older Python versions


class MetadataParser(ABC):
    """Base class for parsing KFP function metadata with shared utilities."""

    def __init__(self, file_path: Path):
        """Initialize the parser with a file path.
        
        Args:
            file_path: Path to the Python file containing the function.
        """
        self.file_path = file_path
    
    def _parse_google_docstring(self, docstring: str) -> Dict[str, Any]:
        """Parse Google-style docstring to extract Args and Returns sections.
        
        Args:
            docstring: The function's docstring.
            
        Returns:
            Dictionary containing parsed docstring information.
        """
        if not docstring:
            return {'overview': '', 'args': {}, 'returns_description': ''}
        
        # Parse docstring using docstring-parser library
        parsed = parse_docstring(docstring)
        
        # Extract overview (short description + long description)
        overview_parts = []
        if parsed.short_description:
            overview_parts.append(parsed.short_description)
        if parsed.long_description:
            overview_parts.append(parsed.long_description)
        overview = '\n\n'.join(overview_parts)
        
        # Extract arguments
        args = {param.arg_name: param.description for param in parsed.params}
        
        # Extract returns description
        returns_description = parsed.returns.description if parsed.returns else ''
        
        return {
            'overview': overview,
            'args': args,
            'returns_description': returns_description
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
    
    def _extract_function_metadata(self, function_name: str, module_name: str = "module") -> Dict[str, Any]:
        """Extract metadata from a KFP function (component or pipeline).
        
        Args:
            function_name: Name of the function to introspect.
            module_name: Name to use for the module during import.
            
        Returns:
            Dictionary containing extracted metadata.
        """
        try:
            # Import the module to get the actual function object
            spec = importlib.util.spec_from_file_location(module_name, self.file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            func_obj = getattr(module, function_name)
            
            # KFP decorators wrap functions; access the underlying function
            # Components use 'python_func', pipelines use 'pipeline_func'
            if hasattr(func_obj, 'python_func'):
                func = func_obj.python_func
            elif hasattr(func_obj, 'pipeline_func'):
                func = func_obj.pipeline_func
            else:
                # Fallback to the object itself if neither attribute is available
                func = func_obj
            
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

    def _is_decorated_with(self, decorator: ast.AST, decoration_type: str,) -> bool:
        """Check if a decorator is a KFP component or pipeline decorator.
        
        Supports the following decorator formats (using component as an example):
        - @component (direct import: from kfp.dsl import component)
        - @dsl.component (from kfp import dsl)
        - @kfp.dsl.component (import kfp)
        - All of the above with parentheses: @component(), @dsl.component(), etc.
        
        Args:
            decorator: AST node representing the decorator.
            decoration_type: The type of decoration to check for (e.g. 'component', 'pipeline').

        Returns:
            True if the decorator is the given decoration_type, False otherwise.
        """
        if isinstance(decorator, ast.Attribute):
            # Handle attribute-based decorators
            if decorator.attr == decoration_type:
                # Check for @dsl.<decoration_type>
                if isinstance(decorator.value, ast.Name) and decorator.value.id == 'dsl':
                    return True
                # Check for @kfp.dsl.<decoration_type>
                if (isinstance(decorator.value, ast.Attribute) and 
                    decorator.value.attr == 'dsl' and
                    isinstance(decorator.value.value, ast.Name) and
                    decorator.value.value.id == 'kfp'):
                    return True
            return False
        elif isinstance(decorator, ast.Call):
            # Handle decorators with arguments (e.g., @<decoration_type>(), @dsl.<decoration_type>())
            return self._is_decorated_with(decorator.func, decoration_type)
        elif isinstance(decorator, ast.Name):
            # Handle @<decoration_type> (if imported directly)
            return decorator.id == decoration_type
        return False

    @abstractmethod
    def extract_metadata(self, function_name: str) -> Dict[str, Any]:
        """Extract metadata from the function.
        
        Args:
            function_name: Name of the function to introspect.
            
        Returns:
            Dictionary containing extracted metadata.
        """
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def find_function(self) -> Optional[str]:
        """Find the function decorated with the decorator of the subclass.
        
        Returns:
            The name of the function, or None if not found.
        """
        raise NotImplementedError("Subclasses must implement this method")


class ComponentMetadataParser(MetadataParser):
    """Introspects KFP component functions to extract documentation metadata."""
    
    def find_function(self) -> Optional[str]:
        """Find the function decorated with @dsl.component.
        
        Returns:
            The name of the component function, or None if not found.
        """
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
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
            logger.error(f"Error parsing file {self.file_path}: {e}")
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
        return self._is_decorated_with(decorator, 'component')

        
    def extract_metadata(self, function_name: str) -> Dict[str, Any]:
        """Extract metadata from the component function.
        
        Args:
            function_name: Name of the component function to introspect.
            
        Returns:
            Dictionary containing extracted metadata.
        """
        return self._extract_function_metadata(function_name, "component_module")


class PipelineMetadataParser(MetadataParser):
    """Introspects KFP pipeline functions to extract documentation metadata."""
    
    def find_function(self) -> Optional[str]:
        """Find the function decorated with @dsl.pipeline.
        
        Returns:
            The name of the pipeline function, or None if not found.
        """
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if function has @dsl.pipeline decorator
                    for decorator in node.decorator_list:
                        if self._is_pipeline_decorator(decorator):
                            return node.name
            
            return None
        except Exception as e:
            logger.error(f"Error parsing file {self.file_path}: {e}")
            return None
    
    def _is_pipeline_decorator(self, decorator: ast.AST) -> bool:
        """Check if a decorator is a KFP pipeline decorator.
        
        Supports the following decorator formats:
        - @pipeline (direct import: from kfp.dsl import pipeline)
        - @dsl.pipeline (from kfp import dsl)
        - @kfp.dsl.pipeline (import kfp)
        - All of the above with parentheses: @pipeline(), @dsl.pipeline(), etc.
        
        Args:
            decorator: AST node representing the decorator.
            
        Returns:
            True if the decorator is a KFP pipeline decorator, False otherwise.
        """
        return self._is_decorated_with(decorator, 'pipeline')
    
    def extract_metadata(self, function_name: str) -> Dict[str, Any]:
        """Extract metadata from the pipeline function.
        
        Args:
            function_name: Name of the pipeline function to introspect.
            
        Returns:
            Dictionary containing extracted metadata.
        """
        return self._extract_function_metadata(function_name, "pipeline_module")

