"""README writer for KFP components and pipelines."""

import logging
import sys
from pathlib import Path
from typing import Optional

from scripts.generate_readme.category_index_generator import CategoryIndexGenerator
from scripts.generate_readme.constants import CUSTOM_CONTENT_MARKER, EXIT_ERROR
from scripts.generate_readme.content_generator import ReadmeContentGenerator
from scripts.generate_readme.metadata_parser import MetadataParser

logger = logging.getLogger(__name__)


class ReadmeWriter:
    """Writes README documentation for Kubeflow Pipelines components and pipelines."""

    def __init__(
        self,
        component_dir: Optional[Path] = None,
        pipeline_dir: Optional[Path] = None,
        output_file: Optional[Path] = None,
    ):
        """Initialize the README writer.

        Args:
            component_dir: Path to the component directory (must contain component.py and metadata.yaml).
            pipeline_dir: Path to the pipeline directory (must contain pipeline.py and metadata.yaml).
            output_file: Optional output path for the generated README.
        """
        # Validate that exactly one of component_dir or pipeline_dir is provided
        if not component_dir and not pipeline_dir:
            logger.error("Either component_dir or pipeline_dir must be provided")
            raise ValueError("Either component_dir or pipeline_dir must be provided")
        if component_dir and pipeline_dir:
            logger.error("Cannot specify both component_dir and pipeline_dir")
            raise ValueError("Cannot specify both component_dir and pipeline_dir")

        # Determine which type we're generating for
        self.is_component = component_dir is not None
        if self.is_component:
            self.source_dir = component_dir
            self.source_file = component_dir / "component.py"
            self.function_type = "component"
        else:
            self.source_dir = pipeline_dir
            self.source_file = pipeline_dir / "pipeline.py"
            self.function_type = "pipeline"

        self.category_dir = self.source_dir.parent
        self.category_index_file = self.category_dir / "README.md"

        self.parser = MetadataParser(self.source_file, self.function_type)
        self.metadata_file = self.source_dir / "metadata.yaml"
        self.readme_file = output_file if output_file else self.source_dir / "README.md"

    def _extract_custom_content(self) -> Optional[str]:
        """Extract custom content from existing README if it has a custom-content marker.

        Returns:
            The custom content (including marker) if found, None otherwise.
        """
        if not self.readme_file.exists():
            return None

        try:
            with open(self.readme_file, "r", encoding="utf-8") as f:
                content = f.read()

            if CUSTOM_CONTENT_MARKER in content:
                marker_index = content.find(CUSTOM_CONTENT_MARKER)
                custom_content = content[marker_index:]
                logger.debug(f"Found custom content marker, preserving {len(custom_content)} characters")
                return custom_content

            return None
        except Exception as e:
            logger.warning(f"Error reading existing README for custom content: {e}")
            return None

    def _read_file_content(self, file_path: Path) -> Optional[str]:
        """Read content from a file if it exists.

        Args:
            file_path: Path to the file to read.

        Returns:
            File content as string, or None if file doesn't exist.
        """
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Error reading {file_path}: {e}")
            return None

    def _has_diff(self, expected: str, actual: Optional[str]) -> bool:
        """Check if expected content differs from actual content.

        Args:
            expected: The expected content.
            actual: The actual file content (None if file doesn't exist).

        Returns:
            True if there's a diff, False if content matches.
        """
        if actual is None:
            return True
        return expected != actual

    def _check_category_index(self, category_content: str) -> bool:
        """Check if category index matches expected content.

        Args:
            category_content: The expected category index content.

        Returns:
            True if there's a diff, False if content matches.
        """
        actual_content = self._read_file_content(self.category_index_file)
        has_diff = self._has_diff(category_content, actual_content)
        if has_diff:
            logger.warning(f"Out of sync: {self.category_index_file}")
        return has_diff

    def _write_category_index(self, category_content: str) -> None:
        """Write the category-level README index.

        Args:
            category_content: The generated category index content to write.
        """
        if self.category_index_file.exists():
            logger.info(f"Category index exists at {self.category_index_file}, regenerating entries.")
        else:
            logger.info(f"Category index does not exist yet at {self.category_index_file}, creating new file")

        try:
            with open(self.category_index_file, "w", encoding="utf-8") as f:
                f.write(category_content)

            logger.info(f"Category index generated at {self.category_index_file}")

        except Exception as e:
            logger.error(f"Could not write category index: {e}")
            sys.exit(EXIT_ERROR)

    def _check_readme_file(self, readme_content: str) -> bool:
        """Check if README matches expected content.

        Args:
            readme_content: The expected README content.

        Returns:
            True if there's a diff, False if content matches.
        """
        # Include custom content in comparison if it exists
        custom_content = self._extract_custom_content()
        if custom_content:
            readme_content = f"{readme_content}\n\n{custom_content}"

        actual_content = self._read_file_content(self.readme_file)
        has_diff = self._has_diff(readme_content, actual_content)
        if has_diff:
            logger.warning(f"Out of sync: {self.readme_file}")
        return has_diff

    def _write_readme_file(self, readme_content: str) -> None:
        """Write the README content to the README.md file.

        Preserves any custom content after the <!-- custom-content --> marker.

        Args:
            readme_content: The content to write to the README.md file.
        """
        # Extract any custom content
        custom_content = self._extract_custom_content()

        # Append custom content if it was found
        if custom_content:
            readme_content = f"{readme_content}\n\n{custom_content}"
            logger.info("Preserved custom content from existing README")

        # Ensure parent directories exist for custom output paths
        self.readme_file.parent.mkdir(parents=True, exist_ok=True)

        # Write README.md
        with open(self.readme_file, "w", encoding="utf-8") as f:
            logger.debug(f"Writing README.md to {self.readme_file}")
            f.write(readme_content)
        logger.info(f"README.md generated successfully at {self.readme_file}")

    def generate(self, fix: bool = False) -> bool:
        """Generate the README documentation.

        Args:
            fix: If True, write/update README files.
                 If False, only check for diffs without writing files.

        Returns:
            True if there are diffs detected, False otherwise.

        Raises:
            SystemExit: If function is not found or metadata extraction fails.
        """
        # Find the function
        logger.debug(f"Analyzing file: {self.source_file}")
        function_name = self.parser.find_function()

        if not function_name:
            logger.error(f"No component/pipeline function found in {self.source_file}")
            sys.exit(EXIT_ERROR)

        logger.debug(f"Found target decorated function: {function_name}")

        # Extract metadata
        metadata = self.parser.extract_metadata(function_name)
        if not metadata:
            logger.error(f"Could not extract metadata from function {function_name}")
            sys.exit(EXIT_ERROR)

        logger.debug(f"Extracted metadata for {len(metadata.get('parameters', {}))} parameters")

        # Generate README content
        readme_content_generator = ReadmeContentGenerator(metadata, self.source_dir)
        readme_content = readme_content_generator.generate_readme()

        # Generate category index content
        index_generator = CategoryIndexGenerator(self.category_dir, self.is_component)
        index_content = index_generator.generate()

        # Check for diffs (in both modes)
        readme_has_diff = self._check_readme_file(readme_content)
        category_has_diff = self._check_category_index(index_content)
        has_diff = readme_has_diff or category_has_diff

        if has_diff and fix:
            # Fix mode: write files
            self._write_readme_file(readme_content)
            self._write_category_index(index_content)

            # Log metadata statistics
            logger.debug(f"README content length: {len(readme_content)} characters")
            logger.debug(f"Target decorated function name: {metadata.get('name', 'Unknown')}")
            logger.debug(f"Parameters: {len(metadata.get('parameters', {}))}")
            logger.debug(f"Has return type: {'Yes' if metadata.get('returns') else 'No'}")

        return has_diff
