"""README content generator for KFP components and pipelines."""

import logging
import re
from pathlib import Path
from typing import Any, Dict

import yaml
from jinja2 import Environment, FileSystemLoader

from .constants import README_TEMPLATE

logger = logging.getLogger(__name__)


class ReadmeContentGenerator:
    """Generates README.md documentation content for KFP components and pipelines."""

    def __init__(self, metadata: Dict[str, Any], source_dir: Path):
        """Initialize the generator with metadata.

        Args:
            metadata: Metadata extracted by ComponentMetadataParser or PipelineMetadataParser.
            source_dir: Path to the component/pipeline directory.
        """
        self.metadata = metadata
        self.source_dir = source_dir
        self.metadata_file = source_dir / "metadata.yaml"
        self.example_file = source_dir / "example_pipelines.py"
        self.owners_file = source_dir / "OWNERS"
        self.feature_metadata = self._load_feature_metadata()

        # Set up Jinja2 environment
        template_dir = Path(__file__).parent / 'templates'
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.template = self.env.get_template(README_TEMPLATE)
    
    def _load_feature_metadata(self) -> Dict[str, Any]:
        """Load and parse feature metadata from metadata.yaml and OWNERS files.

        Loads metadata from metadata.yaml (excluding 'ci' field) and augments it
        with owners information from OWNERS file if it exists.

        Returns:
            Dictionary containing the aggregated feature metadata.
        """
        try:
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)

            # Remove 'ci' field if present
            if yaml_data and "ci" in yaml_data:
                yaml_data.pop("ci")

            yaml_data = yaml_data or {}
        except Exception as e:
            logger.warning(f"Could not load metadata.yaml: {e}")
            yaml_data = {}

        # Augment with owners information from OWNERS file
        owners_data = self._load_owners()
        if owners_data:
            yaml_data["owners"] = owners_data

        return yaml_data

    def _load_owners(self) -> Dict[str, Any]:
        """Load the OWNERS file if it exists.

        Returns:
            Dictionary containing owners data (approvers and reviewers) if file exists, empty dict otherwise.
        """
        if self.owners_file.exists():
            try:
                with open(self.owners_file, "r", encoding="utf-8") as f:
                    owners_data = yaml.safe_load(f)
                return owners_data or {}
            except Exception as e:
                logger.warning(f"Error reading OWNERS file ({self.owners_file}): {e}")
                return {}
        return {}

    def _load_example_pipelines(self) -> str:
        """Load the Example Pipeline file if it exists.

        Returns:
            Contents of Example Pipeline file if it exists, empty string otherwise.
        """
        if self.example_file.exists():
            try:
                with open(self.example_file, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Error reading Example Pipelines file ({self.example_file}): {e}")
                return ""
        return ""

    def _format_title(self, title: str) -> str:
        """Format a title from snake_case or camelCase to Title Case.

        Args:
            title: The title to format.

        Returns:
            Formatted title in Title Case with spaces.
        """
        # First, handle camelCase by inserting spaces before capitals
        title = re.sub(r"([a-z])([A-Z])", r"\1 \2", title)

        # Replace underscores with spaces
        title = title.replace("_", " ")

        # Split into words and capitalize each
        words = title.split()
        formatted_words = []

        for word in words:
            # Keep known acronyms in uppercase
            if word.upper() in ["KFP", "API", "URL", "ID", "UI", "CI", "CD"]:
                formatted_words.append(word.upper())
            else:
                formatted_words.append(word.capitalize())

        return " ".join(formatted_words)

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
        indent = "  " * depth  # 2 spaces per depth level

        if isinstance(value, bool):
            return "Yes" if value else "No"

        elif isinstance(value, list):
            if not value:
                return "None"
            items = []
            for item in value:
                if isinstance(item, dict):
                    # Dict in list: format as comma-separated key-value pairs
                    parts = [f"{self._format_key(k)}: {v}" for k, v in item.items()]
                    items.append(", ".join(parts))
                else:
                    # Simple item: just convert to string
                    items.append(str(item))
            return "\n" + indent + "  - " + f"\n{indent}  - ".join(items)

        elif isinstance(value, dict):
            if not value:
                return "None"
            items = []
            for k, v in value.items():
                key = self._format_key(k)
                val = self._format_value(v, depth + 1)
                # If value has newlines (nested structure), format with colon on same line
                if "\n" in val:
                    items.append(f"{key}:{val}")
                else:
                    items.append(f"{key}: {val}")
            return "\n" + indent + "  - " + f"\n{indent}  - ".join(items)

        elif value is None:
            return "None"

        else:
            return str(value)

    @property
    def formatted_feature_metadata(self) -> Dict[str, str]:
        """Format the YAML metadata for human-readable display.

        Returns:
            Dictionary with formatted keys and values.
        """
        return {self._format_title(key): self._format_value(value) for key, value in self.feature_metadata.items()}

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
        # Prefer name from metadata.yaml over function name
        component_name = self.feature_metadata.get("name", self.metadata.get("name", "Component"))

        # Prepare title
        title = self._format_title(component_name)

        # Prepare overview
        overview = self.metadata.get("overview", "")
        if not overview:
            overview = f"A Kubeflow Pipelines component for {component_name.replace('_', ' ')}."

        # Prepare parameters with formatted defaults
        parameters = {}
        for param_name, param_info in self.metadata.get("parameters", {}).items():
            param_type = param_info.get("type", "Any")
            default_str = f"`{param_info['default']}`" if "default" in param_info else "Required"
            description = param_info.get("description", "")

            parameters[param_name] = {
                "type": param_type,
                "default_str": default_str,
                "description": description,
            }

        # Prepare returns
        returns = self.metadata.get("returns", {})
        if returns:
            returns = {
                "type": returns.get("type", "Any"),
                "description": returns.get("description", "Component output"),
            }

        # Load example pipeline if it exists
        example_code = self._load_example_pipelines()

        # Extract links for separate Additional Resources section (removes from feature_metadata)
        links = self.feature_metadata.pop("links", {})

        return {
            "title": title,
            "overview": overview,
            "parameters": parameters,
            "returns": returns,
            "component_name": component_name,
            "example_code": example_code,
            "formatted_metadata": self.formatted_feature_metadata,
            "links": links,
        }
