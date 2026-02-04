"""Category and subcategory index generators for KFP components and pipelines."""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml
from jinja2 import Environment, FileSystemLoader

from scripts.generate_readme.constants import (
    CATEGORY_README_TEMPLATE,
    MAX_LINE_LENGTH,
    SUBCATEGORY_README_TEMPLATE,
)
from scripts.generate_readme.metadata_parser import MetadataParser
from scripts.generate_readme.utils import format_title

logger = logging.getLogger(__name__)


class _BaseIndexGenerator:
    """Base class for index generators with shared Jinja2 setup and item extraction."""

    def __init__(self, directory: Path, template_name: str, is_component: bool = True):
        """Initialize the base index generator.

        Args:
            directory: Path to the directory to index.
            template_name: Name of the Jinja2 template to use.
            is_component: True if indexing components, False if indexing pipelines.
        """
        if not directory.exists():
            raise ValueError(f"Required directory not found: {directory}")

        self.directory = directory
        self.is_component = is_component
        self.type_name = "Components" if is_component else "Pipelines"
        self._target_file = "component.py" if is_component else "pipeline.py"

        # Set up Jinja2 environment
        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.template = self.env.get_template(template_name)

    def _get_display_name(self, item_dir: Path) -> str:
        """Get the display name for an item from the `name` field in metadata.yaml.

        Args:
            item_dir: Path to the component/pipeline directory.

        Returns:
            The display name to use.

        Raises:
            ValueError: If the `name` field is not found in metadata.yaml.
        """
        metadata_file = item_dir / "metadata.yaml"
        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)
                if yaml_data and "name" in yaml_data:
                    return yaml_data["name"]
        except Exception as e:
            logger.debug(f"Could not load name from {metadata_file.name}: {e}")
            raise
        raise ValueError(f"Required `name` field not found in {metadata_file.name}")

    def _extract_item_info(self, item_dir: Path) -> Optional[Dict[str, str]]:
        """Extract name and overview from a component/pipeline.

        Args:
            item_dir: Path to the component/pipeline directory.

        Returns:
            Dictionary with 'name', 'overview', and 'link' keys, or None if extraction fails.
        """
        try:
            source_file = item_dir / self._target_file
            parser_type = "component" if self.is_component else "pipeline"
            parser = MetadataParser(source_file, parser_type)

            function_name = parser.find_function()
            if not function_name:
                logger.warning(f"No function found in {source_file}")
                return None

            function_metadata = parser.extract_metadata(function_name)
            if not function_metadata:
                logger.warning(f"Could not extract function metadata from {source_file}")
                return None

            name = self._get_display_name(item_dir)
            formatted_name = format_title(name)

            overview = function_metadata.get("overview", "")
            overview = overview.split("\n")[0].strip()

            link = f"./{item_dir.name}/README.md"

            return {
                "name": formatted_name,
                "overview": overview[:MAX_LINE_LENGTH],
                "link": link,
            }

        except Exception as e:
            logger.warning(f"Error extracting info from {item_dir}: {e}")
            return None

    def _find_asset_dirs(self) -> List[Path]:
        """Find component/pipeline directories that contain a target file and metadata.yaml.

        Skips directories starting with '__' and directories named 'shared' or 'tests'.

        Returns:
            List of paths to component/pipeline directories.
        """
        items = []
        for subdir in self.directory.iterdir():
            if subdir.is_dir() and not subdir.name.startswith("__") and subdir.name not in {"shared", "tests"}:
                if (subdir / self._target_file).exists() and (subdir / "metadata.yaml").exists():
                    items.append(subdir)
        return items

    def _collect_items(self, item_dirs: List[Path]) -> List[Dict[str, str]]:
        """Extract and sort item info from a list of directories.

        Args:
            item_dirs: List of paths to component/pipeline directories.

        Returns:
            Sorted list of item info dictionaries.
        """
        items = []
        for item_dir in item_dirs:
            item_info = self._extract_item_info(item_dir)
            if item_info:
                items.append(item_info)
        items.sort(key=lambda x: x["name"])
        return items


class CategoryIndexGenerator(_BaseIndexGenerator):
    """Generates category-level README.md that indexes all components/pipelines in a category."""

    def __init__(self, category_dir: Path, is_component: bool = True):
        """Initialize the category index generator.

        Args:
            category_dir: Path to the category directory (e.g., components/dev/).
            is_component: True if indexing components, False if indexing pipelines.
        """
        super().__init__(category_dir, CATEGORY_README_TEMPLATE, is_component)
        self.category_dir = category_dir
        self.category_name = category_dir.name

    def _is_subcategory(self, subdir: Path) -> bool:
        """Check if a directory is a subcategory (contains child dirs with component.py/pipeline.py).

        Args:
            subdir: Path to check.

        Returns:
            True if the directory is a subcategory.
        """
        for child in subdir.iterdir():
            if child.is_dir() and not child.name.startswith("__") and child.name not in {"shared", "tests"}:
                if (child / self._target_file).exists():
                    return True
        return False

    def _find_items_in_category(self) -> Tuple[List[Path], List[Path]]:
        """Find all component/pipeline directories and subcategories within the category.

        Returns:
            Tuple of (direct_items, subcategories) where each is a list of paths.
        """
        direct_items = []
        subcategories = []

        for subdir in self.category_dir.iterdir():
            if subdir.is_dir() and not subdir.name.startswith("__"):
                if (subdir / self._target_file).exists() and (subdir / "metadata.yaml").exists():
                    direct_items.append(subdir)
                elif self._is_subcategory(subdir):
                    subcategories.append(subdir)

        return direct_items, subcategories

    @staticmethod
    def _extract_subcategory_info(subcat_dir: Path) -> Dict[str, str]:
        """Extract display info for a subcategory directory.

        Args:
            subcat_dir: Path to the subcategory directory.

        Returns:
            Dictionary with 'name' and 'link' keys.
        """
        return {
            "name": format_title(subcat_dir.name),
            "link": f"./{subcat_dir.name}/README.md",
        }

    def generate(self) -> str:
        """Generate the category index README content.

        Returns:
            Complete README.md content for the category index.
        """
        item_dirs, subcategory_dirs = self._find_items_in_category()

        items = self._collect_items(item_dirs)

        subcategories = [self._extract_subcategory_info(d) for d in subcategory_dirs]
        subcategories.sort(key=lambda x: x["name"])

        context = {
            "category_name": format_title(self.category_name),
            "is_component": self.is_component,
            "type_name": self.type_name,
            "items": items,
            "subcategories": subcategories,
        }

        return self.template.render(**context)


class SubcategoryIndexGenerator(_BaseIndexGenerator):
    """Generates subcategory-level README.md that indexes all components/pipelines in a subcategory."""

    def __init__(self, subcategory_dir: Path, is_component: bool = True):
        """Initialize the subcategory index generator.

        Args:
            subcategory_dir: Path to the subcategory directory
                (e.g., components/training/sklearn_trainer/).
            is_component: True if indexing components, False if indexing pipelines.
        """
        super().__init__(subcategory_dir, SUBCATEGORY_README_TEMPLATE, is_component)
        self.subcategory_dir = subcategory_dir
        self.subcategory_name = subcategory_dir.name

    def generate(self) -> str:
        """Generate the subcategory index README content.

        Returns:
            Complete README.md content for the subcategory index.
        """
        item_dirs = self._find_asset_dirs()
        items = self._collect_items(item_dirs)

        context = {
            "subcategory_name": format_title(self.subcategory_name),
            "is_component": self.is_component,
            "type_name": self.type_name,
            "items": items,
        }

        return self.template.render(**context)
