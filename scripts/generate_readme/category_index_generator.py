"""Category index generator for KFP components and pipelines."""
import logging
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from jinja2 import Environment, FileSystemLoader

from .constants import CATEGORY_README_TEMPLATE
from .metadata_parser import MetadataParser

logger = logging.getLogger(__name__)


class CategoryIndexGenerator:
    """Generates category-level README.md that indexes all components/pipelines in a category."""
    
    def __init__(self, category_dir: Path, is_component: bool = True):
        """Initialize the category index generator.
        
        Args:
            category_dir: Path to the category directory (e.g., components/dev/).
            is_component: True if indexing components, False if indexing pipelines.
        """
        self.category_dir = category_dir
        self.is_component = is_component
        self.category_name = category_dir.name
        
        # Set up Jinja2 environment
        template_dir = Path(__file__).parent / 'templates'
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
        target_file = 'component.py' if self.is_component else 'pipeline.py'
        
        for subdir in self.category_dir.iterdir():
            if subdir.is_dir() and not subdir.name.startswith('__'):
                target_path = subdir / target_file
                metadata_path = subdir / 'metadata.yaml'
                if target_path.exists() and metadata_path.exists():
                    items.append(subdir)
        
        return items
    
    def _get_preferred_name(self, item_dir: Path, metadata: Dict, function_name: str) -> str:
        """Get the preferred name for an item, checking metadata.yaml first.
        
        This matches the priority used in individual README generation:
        1. Name from metadata.yaml
        2. Name from function decorator
        3. Function name
        
        Args:
            item_dir: Path to the component/pipeline directory.
            metadata: Extracted metadata from the function.
            function_name: The function's name.
            
        Returns:
            The preferred name to use.
        """
        # Try to load metadata.yaml
        metadata_file = item_dir / 'metadata.yaml'
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    yaml_data = yaml.safe_load(f)
                    if yaml_data and 'name' in yaml_data:
                        return yaml_data['name']
            except Exception as e:
                logger.debug(f"Could not load name from {metadata_file}: {e}")
        
        # Fall back to decorator name, then function name
        return metadata.get('name', function_name)
    
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
                source_file = item_dir / 'component.py'
                parser = MetadataParser(source_file, 'component')
            else:
                source_file = item_dir / 'pipeline.py'
                parser = MetadataParser(source_file, 'pipeline')
            
            # Find the function
            function_name = parser.find_function()
            if not function_name:
                logger.warning(f"No function found in {source_file}")
                return None
            
            # Extract metadata
            metadata = parser.extract_metadata(function_name)
            if not metadata:
                logger.warning(f"Could not extract metadata from {source_file}")
                return None
            
            # Get name - prefer metadata.yaml, then decorator name, then function name
            name = self._get_preferred_name(item_dir, metadata, function_name)
            # Format name to match individual README titles
            formatted_name = format_title(name)
            
            # Get overview from docstring
            overview = metadata.get('overview', '')
            if not overview:
                overview = "No description available."
            else:
                # Take only the first line/sentence for the index
                overview = overview.split('\n')[0].strip()
            
            # Create relative link to the item's README
            link = f"./{item_dir.name}/README.md"
            
            return {
                'name': name,
                'overview': overview,
                'link': link,
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
        items.sort(key=lambda x: x['name'])
        
        # Prepare template context
        context = {
            'category_name': self.category_name.replace('_', ' ').title(),
            'is_component': self.is_component,
            'type_name': 'Components' if self.is_component else 'Pipelines',
            'items': items,
        }
        
        return self.template.render(**context)
    
