"""Tests for content_generator.py module."""
from ..content_generator import ReadmeContentGenerator


class TestReadmeContentGenerator:
    """Tests for ReadmeContentGenerator."""
    
    def test_init_with_component(self, component_dir, sample_extracted_metadata):
        """Test initialization with component metadata."""
        metadata_file = component_dir / "metadata.yaml"
        
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            metadata_file,
            is_component=True
        )
        
        assert generator.metadata == sample_extracted_metadata
        assert generator.is_component is True
        assert generator.yaml_metadata is not None
    
    def test_init_with_pipeline(self, pipeline_dir, sample_extracted_metadata):
        """Test initialization with pipeline metadata."""
        metadata_file = pipeline_dir / "metadata.yaml"
        
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            metadata_file,
            is_component=False
        )
        
        assert generator.is_component is False
    
    def test_load_yaml_metadata(self, component_dir, sample_extracted_metadata):
        """Test loading YAML metadata from file."""
        metadata_file = component_dir / "metadata.yaml"
        
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            metadata_file,
            is_component=True
        )
        
        assert 'name' in generator.yaml_metadata
        assert generator.yaml_metadata['name'] == 'sample_component'
        assert 'tier' in generator.yaml_metadata
    
    def test_load_yaml_metadata_excludes_ci(self, temp_dir, sample_extracted_metadata):
        """Test that 'ci' field is excluded from YAML metadata."""
        metadata_file = temp_dir / "metadata.yaml"
        metadata_file.write_text("""name: test
tier: core
ci:
  test: value
  another: field
""")
        
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            metadata_file,
            is_component=True
        )
        
        assert 'ci' not in generator.yaml_metadata
        assert 'name' in generator.yaml_metadata
        assert 'tier' in generator.yaml_metadata
    
    def test_generate_title(self, component_dir, sample_extracted_metadata):
        """Test title generation."""
        metadata_file = component_dir / "metadata.yaml"
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            metadata_file,
            is_component=True
        )
        
        title = generator._generate_title()
        
        assert '# Sample Component ✨' in title
        assert 'sample_component' not in title  # Should be title cased
    
    def test_generate_overview(self, component_dir, sample_extracted_metadata):
        """Test overview generation."""
        metadata_file = component_dir / "metadata.yaml"
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            metadata_file,
            is_component=True
        )
        
        overview = generator._generate_overview()
        
        assert '## Overview' in overview
        assert 'sample component' in overview.lower()
    
    def test_generate_overview_with_custom_text(self, component_dir):
        """Test overview generation with custom overview text."""
        metadata_file = component_dir / "metadata.yaml"
        custom_metadata = {
            'name': 'test_component',
            'overview': 'This is a custom overview text.',
            'parameters': {},
            'returns': {}
        }
        
        generator = ReadmeContentGenerator(
            custom_metadata,
            metadata_file,
            is_component=True
        )
        
        overview = generator._generate_overview()
        
        assert 'custom overview text' in overview
    
    def test_generate_inputs_outputs(self, component_dir, sample_extracted_metadata):
        """Test inputs and outputs section generation."""
        metadata_file = component_dir / "metadata.yaml"
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            metadata_file,
            is_component=True
        )
        
        content = generator._generate_inputs_outputs()
        
        assert '## Inputs' in content
        assert '## Outputs' in content
        assert 'input_path' in content
        assert 'output_path' in content
        assert 'num_iterations' in content
        assert 'str' in content
        assert 'int' in content
    
    def test_generate_inputs_outputs_with_defaults(self, component_dir, sample_extracted_metadata):
        """Test that default values are shown correctly."""
        metadata_file = component_dir / "metadata.yaml"
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            metadata_file,
            is_component=True
        )
        
        content = generator._generate_inputs_outputs()
        
        assert 'Required' in content  # For params without defaults
        assert '`10`' in content  # For num_iterations default
    
    def test_generate_usage_example_component(self, component_dir, sample_extracted_metadata):
        """Test usage example generation for components."""
        metadata_file = component_dir / "metadata.yaml"
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            metadata_file,
            is_component=True
        )
        
        example = generator._generate_usage_example()
        
        assert '## Usage Example' in example
        assert 'from kfp import dsl' in example
        assert 'sample_component' in example
        assert '@dsl.pipeline' in example
        assert 'input_path' in example
        assert 'output_path' in example
    
    def test_generate_metadata_section(self, component_dir, sample_extracted_metadata):
        """Test metadata section generation."""
        metadata_file = component_dir / "metadata.yaml"
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            metadata_file,
            is_component=True
        )
        
        metadata = generator._generate_metadata()
        
        assert '## Metadata' in metadata
        assert '```yaml' in metadata
        assert 'name: sample_component' in metadata
        assert 'tier: core' in metadata
    
    def test_generate_readme_component(self, component_dir, sample_extracted_metadata):
        """Test complete README generation for a component."""
        metadata_file = component_dir / "metadata.yaml"
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            metadata_file,
            is_component=True
        )
        
        readme = generator.generate_readme()
        
        # Check all sections are present
        assert '# Sample Component' in readme
        assert '## Overview' in readme
        assert '## Inputs' in readme
        assert '## Outputs' in readme
        assert '## Usage Example' in readme
        assert '## Metadata' in readme
    
    def test_generate_readme_pipeline(self, pipeline_dir, sample_extracted_metadata):
        """Test complete README generation for a pipeline."""
        metadata_file = pipeline_dir / "metadata.yaml"
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            metadata_file,
            is_component=False
        )
        
        readme = generator.generate_readme()
        
        # Check sections are present
        assert '# Sample Component' in readme
        assert '## Overview' in readme
        assert '## Inputs' in readme
        assert '## Outputs' in readme
        assert '## Metadata' in readme
        
        # Usage example should NOT be present for pipelines
        assert '## Usage Example' not in readme
    
    def test_generate_readme_empty_metadata(self, temp_dir):
        """Test README generation with empty metadata."""
        metadata_file = temp_dir / "metadata.yaml"
        metadata_file.write_text("name: test\n")
        
        minimal_metadata = {
            'name': 'test',
            'overview': '',
            'parameters': {},
            'returns': {}
        }
        
        generator = ReadmeContentGenerator(
            minimal_metadata,
            metadata_file,
            is_component=True
        )
        
        readme = generator.generate_readme()
        
        # Should still generate basic sections
        assert '# Test' in readme
        assert '## Overview' in readme
    
    def test_usage_example_parameter_types(self, component_dir):
        """Test that usage examples use correct value types."""
        metadata_file = component_dir / "metadata.yaml"
        metadata = {
            'name': 'test_component',
            'parameters': {
                'str_param': {'name': 'str_param', 'type': 'str', 'default': None},
                'int_param': {'name': 'int_param', 'type': 'int', 'default': None},
                'bool_param': {'name': 'bool_param', 'type': 'bool', 'default': None},
                'other_param': {'name': 'other_param', 'type': 'custom', 'default': None},
            },
            'overview': 'Test',
            'returns': {}
        }
        
        generator = ReadmeContentGenerator(
            metadata,
            metadata_file,
            is_component=True
        )
        
        example = generator._generate_usage_example()
        
        # Check type-specific example values
        assert '"str_param_value"' in example  # String should have quotes
        assert '42' in example  # Int should be numeric
        assert 'True' in example  # Bool should be boolean
        assert 'other_param_input' in example  # Custom type uses generic format

