"""README content generator for KFP components and pipelines."""

from pathlib import Path
from typing import Any, Dict

import yaml

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
        """Dynamically generate complete README.md content from component or pipeline metadata
        
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

