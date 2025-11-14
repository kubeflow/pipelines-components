#!/usr/bin/env python3
"""
Generate README.md documentation for Kubeflow Pipelines components.

This script introspects Python functions decorated with @dsl.component to extract
function metadata and generate comprehensive README documentation following the
standards outlined in KEP-913: Components Repository.

Usage:
    python scripts/generate_readme.py --component components/my_component
    python scripts/generate_readme.py --pipeline pipelines/my_pipeline
    python scripts/generate_readme.py --component components/my_component --output custom_readme.md
    python scripts/generate_readme.py --component components/my_component --verbose
    python scripts/generate_readme.py --component components/my_component --overwrite
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
import yaml

# Set up logger
logger = logging.getLogger(__name__)


class MetadataParser:
    """Base class for parsing KFP function metadata with shared utilities."""

    # Regex pattern for Google-style argument lines: "arg_name (type): description"    
    GOOGLE_ARG_REGEX_PATTERN = r'\s*(\w+)\s*\(([^)]+)\):\s*(.*)'

    
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

    def extract_metadata(self, function_name: str) -> Dict[str, Any]:
        raise NotImplementedError("Subclasses must implement this method")

    def find_function(self) -> Optional[str]:
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
        if isinstance(decorator, ast.Attribute):
            # Handle attribute-based decorators
            if decorator.attr == 'pipeline':
                # Check for @dsl.pipeline
                if isinstance(decorator.value, ast.Name) and decorator.value.id == 'dsl':
                    return True
                # Check for @kfp.dsl.pipeline
                if (isinstance(decorator.value, ast.Attribute) and 
                    decorator.value.attr == 'dsl' and
                    isinstance(decorator.value.value, ast.Name) and
                    decorator.value.value.id == 'kfp'):
                    return True
            return False
        elif isinstance(decorator, ast.Call):
            # Handle decorators with arguments (e.g., @pipeline(), @dsl.pipeline())
            return self._is_pipeline_decorator(decorator.func)
        elif isinstance(decorator, ast.Name):
            # Handle @pipeline (if imported directly)
            return decorator.id == 'pipeline'
        return False
    
    def extract_metadata(self, function_name: str) -> Dict[str, Any]:
        """Extract metadata from the pipeline function.
        
        Args:
            function_name: Name of the pipeline function to introspect.
            
        Returns:
            Dictionary containing extracted metadata.
        """
        return self._extract_function_metadata(function_name, "pipeline_module")


class ReadmeContentGenerator:
    """Generates README.md documentation content for KFP components and pipelines."""
    
    def __init__(self, metadata: Dict[str, Any], metadata_file: Path, is_component: bool = True):
        """Initialize the generator with metadata.
        
        Args:
            metadata: Metadata extracted by ComponentMetadataParser or PipelineMetadataParser.
            metadata_file: Path to the metadata.yaml file.
            is_component: True if generating for a component, False for a pipeline.
        """
        self.metadata = metadata
        self.metadata_file = metadata_file
        self.is_component = is_component
        self.yaml_metadata = self._load_yaml_metadata()
    
    def _load_yaml_metadata(self) -> Dict[str, Any]:
        """Load and parse the metadata.yaml file, excluding the 'ci' field.
        
        Returns:
            Dictionary containing the YAML metadata without the 'ci' field.
        """
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                yaml_data = yaml.safe_load(f)
            
            # Remove 'ci' field if present
            if yaml_data and 'ci' in yaml_data:
                yaml_data.pop('ci')
            
            return yaml_data or {}
        except Exception as e:
            logger.warning(f"Could not load metadata.yaml: {e}")
            return {}
    
    def generate_readme(self) -> str:
        """Generate complete README.md content following KEP-913 template.
        
        Returns:
            Complete README.md content as a string.
        """
        sections = [
            self._generate_title(),
            self._generate_overview(),
            self._generate_inputs_outputs(),
        ]
        
        # Only add usage example for components, not pipelines
        if self.is_component:
            sections.append(self._generate_usage_example())
        
        sections.append(self._generate_metadata())
        
        return '\n\n'.join(filter(None, sections))
    
    def _generate_title(self) -> str:
        """Generate the title section."""
        component_name = self.metadata.get('name', 'Component')
        # Convert snake_case to Title Case
        title = ' '.join(word.capitalize() for word in component_name.split('_'))
        return f"# {title} ✨"
    
    def _generate_overview(self) -> str:
        """Generate the overview section."""
        overview = self.metadata.get('overview', '')
        if not overview:
            component_name = self.metadata.get('name', 'processing').replace('_', ' ')
            overview = f"A Kubeflow Pipelines component for {component_name}."
        
        return f"## Overview 🧾\n\n{overview}"
    
    def _generate_metadata(self) -> str:
        """Generate the metadata section from metadata.yaml.
        
        Returns:
            Metadata section as a formatted string with YAML content.
        """
        if not self.yaml_metadata:
            return ""
        
        # Convert metadata dict back to YAML format
        yaml_content = yaml.dump(self.yaml_metadata, default_flow_style=False, sort_keys=False)
        
        return f"""## Metadata 🗂️

```yaml
{yaml_content.strip()}
```"""
    
    def _generate_usage_example(self) -> str:
        """Generate a concise usage example section."""
        component_name = self.metadata.get('name', 'component')
        parameters = self.metadata.get('parameters', {})
        
        content = [
            "## Usage Example 🧪",
            "",
            "```python",
            "from kfp import dsl",
            f"from kfp_components.{component_name} import {component_name}",
            "",
            "@dsl.pipeline(name='example-pipeline')",
            "def my_pipeline():",
            f"    {component_name}_task = {component_name}(",
        ]
        
        # Add parameter examples (show required params or first 2 params)
        required_params = {k: v for k, v in parameters.items() if v.get('default') is None}
        params_to_show = required_params if required_params else dict(list(parameters.items())[:2])
        
        for param_name, param_info in params_to_show.items():
            param_type = param_info.get('type', 'Any')
            if 'str' in param_type.lower():
                example_value = f'"{param_name}_value"'
            elif 'int' in param_type.lower():
                example_value = '42'
            elif 'bool' in param_type.lower():
                example_value = 'True'
            else:
                example_value = f'{param_name}_input'
            
            content.append(f"        {param_name}={example_value},")
        
        content.extend([
            "    )",
            "```"
        ])
        
        return '\n'.join(content)
    
    def _generate_inputs_outputs(self) -> str:
        """Generate combined inputs and outputs section."""
        parameters = self.metadata.get('parameters', {})
        returns = self.metadata.get('returns', {})
        
        content = []
        
        # Inputs section
        if parameters:
            content.extend(["## Inputs 📥", ""])
            content.append("| Parameter | Type | Default | Description |")
            content.append("|-----------|------|---------|-------------|")
            
            for param_name, param_info in parameters.items():
                param_type = param_info.get('type', 'Any')
                default = param_info.get('default')
                default_str = f"`{default}`" if default is not None else "Required"
                description = param_info.get('description', '')
                
                content.append(f"| `{param_name}` | `{param_type}` | {default_str} | {description} |")
        
        # Outputs section
        if returns:
            return_type = returns.get('type', 'Any')
            description = returns.get('description', 'Component output')
            content.extend(["", "## Outputs 📤", ""])
            content.append("| Name | Type | Description |")
            content.append("|------|------|-------------|")
            content.append(f"| Output | `{return_type}` | {description} |")
        
        return '\n'.join(content)


class ReadmeGenerator:
    """Generates README documentation for Kubeflow Pipelines components and pipelines."""
    
    def __init__(self, component_dir: Optional[Path] = None, pipeline_dir: Optional[Path] = None,
                 output_file: Optional[Path] = None, verbose: bool = False, overwrite: bool = False):
        """Initialize the README generator.
        
        Args:
            component_dir: Path to the component directory (must contain component.py and metadata.yaml).
            pipeline_dir: Path to the pipeline directory (must contain pipeline.py and metadata.yaml).
            output_file: Optional output path for the generated README.
            verbose: Enable verbose logging output.
            overwrite: Overwrite existing README without prompting.
        """
        # Validate that at least one of component_dir or pipeline_dir is provided
        assert component_dir or pipeline_dir, "Either component_dir or pipeline_dir must be provided"
        assert not (component_dir and pipeline_dir), "Cannot specify both component_dir and pipeline_dir"
        self.is_component = component_dir is not None   
        
        # Determine which type we're generating for
        if self.is_component:
            self.source_dir = component_dir
            self.source_file = component_dir / 'component.py'
            self.parser = ComponentMetadataParser(self.source_file)
        else:
            self.source_dir = pipeline_dir
            self.source_file = pipeline_dir / 'pipeline.py'
            self.parser = PipelineMetadataParser(self.source_file)
        
        self.metadata_file = self.source_dir / 'metadata.yaml'
        self.readme_file = output_file if output_file else self.source_dir / "README.md"
        self.verbose = verbose
        self.overwrite = overwrite
  
        # Configure logging
        self._configure_logging()
    
    def _configure_logging(self) -> None:
        """Configure logging based on verbose flag."""
        log_level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(levelname)s: %(message)s'
        )

    def _write_readme_file(self, readme_content: str) -> None:
        """Write the README content to the README.md file.
        
        Args:
            readme_content: The content to write to the README.md file.
        """
        # Check if file exists and handle overwrite
        if self.readme_file.exists() and not self.overwrite:
            response = input(f"README.md already exists at {self.readme_file}. Overwrite? (y/N): ")
            if response.lower() not in ['y', 'yes']:
                print("Operation cancelled.")
                sys.exit(0)

        # Write README.md
        with open(self.readme_file, 'w', encoding='utf-8') as f:
            logger.debug(f"Writing README.md to {self.readme_file}")
            logger.debug(f"README content: {readme_content}")
            f.write(readme_content)
        logger.info(f"README.md generated successfully at {self.readme_file}")

    
    def generate(self) -> None:
        """Generate the README documentation.
        
        Raises:
            SystemExit: If function is not found or metadata extraction fails.
        """
        # Find the function
        logger.debug(f"Analyzing file: {self.source_file}")
        function_name = self.parser.find_function()
        
        if not function_name:
            logger.error(f"No component/pipeline function found in {self.source_file}")
            sys.exit(1)
        
        logger.debug(f"Found target decorated function: {function_name}")
        
        # Extract metadata
        metadata = self.parser.extract_metadata(function_name)
        if not metadata:
            logger.error(f"Could not extract metadata from function {function_name}")
            sys.exit(1)
        
        logger.debug(f"Extracted metadata for {len(metadata.get('parameters', {}))} parameters")
        
        # Generate README content
        readme_content_generator = ReadmeContentGenerator(metadata, self.metadata_file, self.is_component)
        readme_content = readme_content_generator.generate_readme()
        
        # Write README.md file
        self._write_readme_file(readme_content)

        # Log metadata statistics
        logger.debug(f"README content length: {len(readme_content)} characters")
        logger.debug(f"Target decorated function name: {metadata.get('name', 'Unknown')}")
        logger.debug(f"Parameters: {len(metadata.get('parameters', {}))}")
        logger.debug(f"Has return type: {'Yes' if metadata.get('returns') else 'No'}")
        

def validate_component_directory(dir_path: str) -> Path:
    """Validate that the component directory exists and contains required files.
    
    Args:
        dir_path: String path to the component directory.
        
    Returns:
        Path: Validated Path object to the component directory.
        
    Raises:
        argparse.ArgumentTypeError: If validation fails.
    """
    path = Path(dir_path)
    
    if not path.exists():
        raise argparse.ArgumentTypeError(f"Component directory '{dir_path}' does not exist")
    
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f"'{dir_path}' is not a directory")
    
    component_file = path / 'component.py'
    if not component_file.exists():
        raise argparse.ArgumentTypeError(f"'{dir_path}' does not contain a component.py file")
    
    metadata_file = path / 'metadata.yaml'
    if not metadata_file.exists():
        raise argparse.ArgumentTypeError(f"'{dir_path}' does not contain a metadata.yaml file")
    
    return path


def validate_pipeline_directory(dir_path: str) -> Path:
    """Validate that the pipeline directory exists and contains required files.
    
    Args:
        dir_path: String path to the pipeline directory.
        
    Returns:
        Path: Validated Path object to the pipeline directory.
        
    Raises:
        argparse.ArgumentTypeError: If validation fails.
    """
    path = Path(dir_path)
    
    if not path.exists():
        raise argparse.ArgumentTypeError(f"Pipeline directory '{dir_path}' does not exist")
    
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f"'{dir_path}' is not a directory")
    
    pipeline_file = path / 'pipeline.py'
    if not pipeline_file.exists():
        raise argparse.ArgumentTypeError(f"'{dir_path}' does not contain a pipeline.py file")
    
    metadata_file = path / 'metadata.yaml'
    if not metadata_file.exists():
        raise argparse.ArgumentTypeError(f"'{dir_path}' does not contain a metadata.yaml file")
    
    return path


def parse_arguments():
    """Parse and validate command-line arguments.
    
    Returns:
        argparse.Namespace: Parsed and validated arguments.
    """
    parser = argparse.ArgumentParser(
        description="Generate README.md documentation for Kubeflow Pipelines components and pipelines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run scripts/generate_readme.py --component components/my_component
  uv run scripts/generate_readme.py --pipeline pipelines/my_pipeline
  uv run scripts/generate_readme.py --component components/my_component --output custom_readme.md
  uv run scripts/generate_readme.py --component components/my_component --verbose
        """
    )
    
    parser.add_argument(
        '--component',
        type=validate_component_directory,
        help='Path to the component directory (must contain component.py and metadata.yaml)'
    )
    
    parser.add_argument(
        '--pipeline',
        type=validate_pipeline_directory,
        help='Path to the pipeline directory (must contain pipeline.py and metadata.yaml)'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=Path,
        help='Output path for the generated README.md (default: README.md in component/pipeline directory)'
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
    
    # Validate that at least one of --component or --pipeline is provided
    if not args.component and not args.pipeline:
        logger.error("Error: Either --component or --pipeline must be specified")
        sys.exit(1)
    
    if args.component and args.pipeline:
        logger.error("Error: Cannot specify both --component and --pipeline")
        sys.exit(1)
    
    # Create and run the generator
    generator = ReadmeGenerator(
        component_dir=args.component,
        pipeline_dir=args.pipeline,
        output_file=args.output,
        verbose=args.verbose,
        overwrite=args.overwrite
    )
    generator.generate()


if __name__ == "__main__":
    main()
