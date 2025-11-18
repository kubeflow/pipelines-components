"""Tests for writer.py module."""

import pytest

from ..constants import CUSTOM_CONTENT_MARKER
from ..writer import ReadmeWriter


class TestReadmeWriter:
    """Tests for ReadmeWriter."""
    
    def test_init_with_component(self, component_dir):
        """Test initialization with component directory."""
        generator = ReadmeWriter(
            component_dir=component_dir,
            verbose=False,
            overwrite=True
        )
        
        assert generator.is_component is True
        assert generator.source_dir == component_dir
        assert generator.source_file == component_dir / 'component.py'
        assert generator.metadata_file == component_dir / 'metadata.yaml'
    
    def test_init_with_pipeline(self, pipeline_dir):
        """Test initialization with pipeline directory."""
        generator = ReadmeWriter(
            pipeline_dir=pipeline_dir,
            verbose=False,
            overwrite=True
        )
        
        assert generator.is_component is False
        assert generator.source_dir == pipeline_dir
        assert generator.source_file == pipeline_dir / 'pipeline.py'
        assert generator.metadata_file == pipeline_dir / 'metadata.yaml'
    
    def test_init_requires_one_directory(self):
        """Test that initialization requires exactly one directory."""
        with pytest.raises(ValueError):
            ReadmeWriter()  # Neither provided
    
    def test_init_rejects_both_directories(self, component_dir, pipeline_dir):
        """Test that initialization rejects both directories."""
        with pytest.raises(ValueError):
            ReadmeWriter(
                component_dir=component_dir,
                pipeline_dir=pipeline_dir
            )
    
    def test_extract_custom_content_not_exists(self, component_dir):
        """Test extracting custom content when README doesn't exist."""
        generator = ReadmeWriter(
            component_dir=component_dir,
            overwrite=True
        )
        
        result = generator._extract_custom_content()
        
        assert result is None
    
    def test_extract_custom_content_no_marker(self, component_dir):
        """Test extracting custom content when marker doesn't exist."""
        readme_file = component_dir / "README.md"
        readme_file.write_text("# Test\n\nSome content without marker")
        
        generator = ReadmeWriter(
            component_dir=component_dir,
            overwrite=True
        )
        
        result = generator._extract_custom_content()
        
        assert result is None
    
    def test_extract_custom_content_with_marker(self, component_dir):
        """Test extracting custom content when marker exists."""
        custom_text = "## Custom Section\n\nThis is custom content."
        readme_content = f"# Test\n\nAuto-generated content\n\n{CUSTOM_CONTENT_MARKER}\n\n{custom_text}"
        
        readme_file = component_dir / "README.md"
        readme_file.write_text(readme_content)
        
        generator = ReadmeWriter(
            component_dir=component_dir,
            overwrite=True
        )
        
        result = generator._extract_custom_content()
        
        assert result is not None
        assert CUSTOM_CONTENT_MARKER in result
        assert "Custom Section" in result
        assert "custom content" in result
    
    def test_generate_component_readme(self, component_dir):
        """Test generating README for a component."""
        generator = ReadmeWriter(
            component_dir=component_dir,
            overwrite=True
        )
        
        generator.generate()
        
        readme_file = component_dir / "README.md"
        assert readme_file.exists()
        
        content = readme_file.read_text()
        assert "# Sample Component" in content
        assert "## Overview" in content
        assert "## Inputs" in content
        assert "## Outputs" in content
        assert "## Usage Example" in content
        assert "## Metadata" in content
    
    def test_generate_pipeline_readme(self, pipeline_dir):
        """Test generating README for a pipeline."""
        generator = ReadmeWriter(
            pipeline_dir=pipeline_dir,
            overwrite=True
        )
        
        generator.generate()
        
        readme_file = pipeline_dir / "README.md"
        assert readme_file.exists()
        
        content = readme_file.read_text()
        assert "# Sample Pipeline" in content
        assert "## Overview" in content
        assert "## Usage Example" not in content  # Pipelines don't have usage examples
    
    def test_generate_preserves_custom_content(self, component_dir):
        """Test that generation preserves custom content."""
        # Create initial README with custom content
        custom_text = "## My Custom Section\n\nThis should be preserved."
        initial_content = f"# Test\n\n{CUSTOM_CONTENT_MARKER}\n\n{custom_text}"
        
        readme_file = component_dir / "README.md"
        readme_file.write_text(initial_content)
        
        # Generate new README
        generator = ReadmeWriter(
            component_dir=component_dir,
            overwrite=True
        )
        generator.generate()
        
        # Check that custom content was preserved
        new_content = readme_file.read_text()
        assert CUSTOM_CONTENT_MARKER in new_content
        assert "My Custom Section" in new_content
        assert "This should be preserved" in new_content
    
    def test_custom_output_file(self, component_dir, temp_dir):
        """Test generating README to a custom output file."""
        custom_output = temp_dir / "CUSTOM_README.md"
        
        generator = ReadmeWriter(
            component_dir=component_dir,
            output_file=custom_output,
            overwrite=True
        )
        generator.generate()
        
        assert custom_output.exists()
        assert (component_dir / "README.md").exists() is False
        
        content = custom_output.read_text()
        assert "# Sample Component" in content
    
    def test_generate_with_verbose(self, component_dir, caplog):
        """Test that verbose mode produces debug output."""
        import logging
        
        caplog.set_level(logging.DEBUG)
        
        generator = ReadmeWriter(
            component_dir=component_dir,
            verbose=True,
            overwrite=True
        )
        generator.generate()
        
        # Check that debug messages were logged
        assert any('Analyzing file' in record.message for record in caplog.records)
        assert any('Found target decorated function' in record.message for record in caplog.records)
    
    def test_write_readme_file_with_overwrite(self, component_dir):
        """Test writing README with overwrite flag."""
        readme_file = component_dir / "README.md"
        readme_file.write_text("Old content")
        
        generator = ReadmeWriter(
            component_dir=component_dir,
            overwrite=True
        )
        
        # This should not raise and should overwrite
        generator._write_readme_file("New content")
        
        assert readme_file.read_text() == "New content"
    
    def test_write_readme_file_errors_without_overwrite(self, component_dir):
        """Test that writing README errors when file exists and overwrite is not set."""
        import pytest
        
        readme_file = component_dir / "README.md"
        readme_file.write_text("Existing content")
        
        generator = ReadmeWriter(
            component_dir=component_dir,
            overwrite=False
        )
        
        # Should raise SystemExit when README exists and overwrite is False
        with pytest.raises(SystemExit) as exc_info:
            generator._write_readme_file("New content")
        
        assert exc_info.value.code == 1
        # Original content should be preserved
        assert readme_file.read_text() == "Existing content"
    
    def test_readme_includes_all_parameters(self, component_dir):
        """Test that generated README includes all component parameters."""
        generator = ReadmeWriter(
            component_dir=component_dir,
            overwrite=True
        )
        generator.generate()
        
        readme_file = component_dir / "README.md"
        content = readme_file.read_text()
        
        # Check all parameters are documented
        assert 'input_path' in content
        assert 'output_path' in content
        assert 'num_iterations' in content
        assert 'Path to input file' in content
        assert 'Path to output file' in content
    
    def test_readme_format_is_markdown(self, component_dir):
        """Test that generated README is valid markdown."""
        generator = ReadmeWriter(
            component_dir=component_dir,
            overwrite=True
        )
        generator.generate()
        
        readme_file = component_dir / "README.md"
        content = readme_file.read_text()
        
        # Check markdown formatting
        assert content.startswith('#')  # Has headers
        assert '```' in content  # Has code blocks
        assert '|' in content  # Has tables
        assert '##' in content  # Has subheaders

