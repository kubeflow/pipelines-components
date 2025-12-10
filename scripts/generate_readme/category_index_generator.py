"""Category index generator for KFP components and pipelines."""

import logging
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from jinja2 import Environment, FileSystemLoader

from .constants import CATEGORY_README_TEMPLATE
from .metadata_parser import MetadataParser
from .utils import format_title

logger = logging.getLogger(__name__)


# Maximum length of the overview string in the category index README.md
MAX_OVERVIEW_LENGTH = 120


class CategoryIndexGenerator:
    """Generates category-level README.md that indexes all components/pipelines in a category."""

    def __init__(self, category_dir: Path, is_component: bool = True):
        """Initialize the category index generator.

        Args:
            category_dir: Path to the category directory (e.g., components/dev/).
            is_component: True if indexing components, False if indexing pipelines.
        """
        self.category_dir = category_dir
        if category_dir.exists() is False:
            raise ValueError(f"Required category directory not found: {category_dir}")
        self.is_component = is_component
        self.category_name = category_dir.name

        # Set up Jinja2 environment
        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.template = self.env.get_template(CATEGORY_README_TEMPLATE)

    def _find_items_in_category(self) -> List[Path]:
        """Find all component/pipeline directories within the category.

        Returns:
            List of paths to component/pipeline directories.
        """
        items = []

        # Look for subdirectories containing component.py or pipeline.py
        target_file = "component.py" if self.is_component else "pipeline.py"

        for subdir in self.category_dir.iterdir():
            if subdir.is_dir() and not subdir.name.startswith("__"):
                target_path = subdir / target_file
                metadata_path = subdir / "metadata.yaml"
                if target_path.exists() and metadata_path.exists():
                    items.append(subdir)

        return items

    def _get_display_name(self, item_dir: Path) -> str:
        """Get the display name for an item, retrieved from the `name` field in metadata.yaml.

        Args:
            item_dir: Path to the component/pipeline directory.

        Returns:
            The display name to use.
        """
        # Try to load metadata.yaml
        metadata_file = item_dir / "metadata.yaml"
        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)
                if yaml_data and "name" in yaml_data:
                    return yaml_data["name"]
        except Exception as e:
            logger.debug(f"Could not load name from {metadata_file.name}: {e}")
            raise e
        raise ValueError(f"Required `name` field not found in {metadata_file.name}")

    def _extract_item_info(self, item_dir: Path) -> Optional[Dict[str, str]]:
        """Extract name and overview from a component/pipeline.

        Args:
            item_dir: Path to the component/pipeline directory.

        Returns:
            Dictionary with 'name', 'overview', and 'link' keys, or None if extraction fails.
        """
        try:
            # Determine source file and parser
            if self.is_component:
                source_file = item_dir / "component.py"
                parser = MetadataParser(source_file, "component")
            else:
                source_file = item_dir / "pipeline.py"
                parser = MetadataParser(source_file, "pipeline")

            # Find the function
            function_name = parser.find_function()
            if not function_name:
                logger.warning(f"No function found in {source_file}")
                return None

            # Extract metadata
            function_metadata = parser.extract_metadata(function_name)
            if not function_metadata:
                logger.warning(f"Could not extract function metadata from {source_file}")
                return None
            name = self._get_display_name(item_dir)
            # Format name to match individual README titles
            formatted_name = format_title(name)

            # Get overview from docstring
            overview = function_metadata.get("overview")
            overview = overview.split("\n")[0].strip()

            # Create relative link to the item's README
            link = f"./{item_dir.name}/README.md"

            return {
                "name": formatted_name,
                "overview": overview[:MAX_OVERVIEW_LENGTH],
                "link": link,
            }

        except Exception as e:
            logger.warning(f"Error extracting info from {item_dir}: {e}")
            return None

    def generate(self) -> str:
        """Generate the category index README content.

        Returns:
            Complete README.md content for the category index.
        """
        # Find all items in the category
        item_dirs = self._find_items_in_category()

        # Extract info for each item
        items = []
        for item_dir in item_dirs:
            item_info = self._extract_item_info(item_dir)
            if item_info:
                items.append(item_info)

        # Sort items by display name
        items.sort(key=lambda x: x["name"])

        # Prepare template context
        context = {
            "category_name": format_title(self.category_name),
            "is_component": self.is_component,
            "type_name": "Components" if self.is_component else "Pipelines",
            "items": items,
        }

        return self.template.render(**context)
