"""README content generator for KFP components and pipelines."""

import re
from pathlib import Path
from typing import Any, Dict, List, Union

import yaml
from jinja2 import Environment, FileSystemLoader

from .constants import logger


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
        
        # Set up Jinja2 environment
        template_dir = Path(__file__).parent
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.template = self.env.get_template('README.md.j2')
    
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
    
    def _format_title(self, title: str) -> str:
        """Format a title from snake_case or camelCase to Title Case.
        
        Args:
            title: The title to format.
            
        Returns:
            Formatted title in Title Case with spaces.
        """
        # First, handle camelCase by inserting spaces before capitals
        title = re.sub(r'([a-z])([A-Z])', r'\1 \2', title)
        
        # Replace underscores with spaces
        title = title.replace('_', ' ')
        
        # Split into words and capitalize each
        words = title.split()
        formatted_words = []
        
        for word in words:
            # Keep known acronyms in uppercase
            if word.upper() in ['KFP', 'API', 'URL', 'ID', 'UI', 'CI', 'CD']:
                formatted_words.append(word.upper())
            else:
                formatted_words.append(word.capitalize())
        
        return ' '.join(formatted_words)
    
    def _format_key(self, key: str) -> str:
        """Format a metadata key for human-readable display.
        
        Args:
            key: The key to format.
            
        Returns:
            Formatted key as a string.
        """
        return self._format_title(key)

    def _format_value(self, value: Any, depth: int = 0) -> str:
        """Format a metadata value for human-readable display.
        
        Args:
            value: The value to format.
            depth: Current nesting depth (0 = top level).
            
        Returns:
            Formatted value as a string with proper markdown list indentation.
        """
        indent = '  ' * depth  # 2 spaces per depth level
        
        if isinstance(value, bool):
            return 'Yes' if value else 'No'
        
        elif isinstance(value, list):
            if not value:
                return 'None'
            items = []
            for item in value:
                if isinstance(item, dict):
                    # Dict in list: format as comma-separated key-value pairs
                    parts = [f"{self._format_key(k)}: {v}" for k, v in item.items()]
                    items.append(', '.join(parts))
                else:
                    # Simple item: just convert to string
                    items.append(str(item))
            return '\n' + indent + '  - ' + f'\n{indent}  - '.join(items)
        
        elif isinstance(value, dict):
            if not value:
                return 'None'
            items = []
            for k, v in value.items():
                key = self._format_key(k)
                val = self._format_value(v, depth + 1)
                # If value has newlines (nested structure), format with colon on same line
                if '\n' in val:
                    items.append(f"{key}:{val}")
                else:
                    items.append(f"{key}: {val}")
            return '\n' + indent + '  - ' + f'\n{indent}  - '.join(items)
        
        elif value is None:
            return 'None'
        
        else:
            return str(value)
    
    def _format_metadata(self) -> Dict[str, str]:
        """Format the YAML metadata for human-readable display.
        
        Returns:
            Dictionary with formatted keys and values.
        """
        return {
            self._format_title(key): self._format_value(value)
            for key, value in self.yaml_metadata.items()
        }
    
    def generate_readme(self) -> str:
        """Dynamically generate complete README.md content from component or pipeline metadata
        
        Returns:
            Complete README.md content as a string.
        """
        context = self._prepare_template_context()
        return self.template.render(**context)
    
    def _prepare_template_context(self) -> Dict[str, Any]:
        """Prepare the context data for the Jinja2 template.
        
        Returns:
            Dictionary containing all variables needed by the template.
        """
        component_name = self.metadata.get('name', 'Component')
        
        # Prepare title
        title = self._format_title(component_name)
        
        # Prepare overview
        overview = self.metadata.get('overview', '')
        if not overview:
            overview = f"A Kubeflow Pipelines component for {component_name.replace('_', ' ')}."
        
        # Prepare parameters with formatted defaults
        parameters = {}
        for param_name, param_info in self.metadata.get('parameters', {}).items():
            param_type = param_info.get('type', 'Any')
            default_str = f"`{param_info['default']}`" if 'default' in param_info else "Required"
            description = param_info.get('description', '')
            
            parameters[param_name] = {
                'type': param_type,
                'default_str': default_str,
                'description': description,
            }
        
        # Prepare returns
        returns = self.metadata.get('returns', {})
        if returns:
            returns = {
                'type': returns.get('type', 'Any'),
                'description': returns.get('description', 'Component output'),
            }
        
        # Prepare usage example parameters
        usage_params = self._prepare_usage_params()
        
        # Prepare formatted metadata for human-readable display
        formatted_metadata = self._format_metadata() if self.yaml_metadata else {}
        
        return {
            'title': title,
            'overview': overview,
            'parameters': parameters,
            'returns': returns,
            'is_component': self.is_component,
            'component_name': component_name,
            'usage_params': usage_params,
            'formatted_metadata': formatted_metadata,
        }
    
    def _prepare_usage_params(self) -> Dict[str, str]:
        """Prepare example parameters for the usage example.
        
        Returns:
            Dictionary mapping parameter names to example values as strings.
        """
        parameters = self.metadata.get('parameters', {})
        
        # Show required params or first 2 params
        required_params = {k: v for k, v in parameters.items() if v.get('default') is None}
        params_to_show = required_params if required_params else dict(list(parameters.items())[:2])
        
        usage_params = {}
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
            
            usage_params[param_name] = example_value
        
        return usage_params

