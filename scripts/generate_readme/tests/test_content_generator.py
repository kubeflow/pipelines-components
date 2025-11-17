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
    
    def test_prepare_template_context(self, component_dir, sample_extracted_metadata):
        """Test template context preparation."""
        metadata_file = component_dir / "metadata.yaml"
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            metadata_file,
            is_component=True
        )
        
        context = generator._prepare_template_context()
        
        # Check all required context keys are present
        assert 'title' in context
        assert 'overview' in context
        assert 'parameters' in context
        assert 'returns' in context
        assert 'is_component' in context
        assert 'component_name' in context
        assert 'usage_params' in context
        assert 'yaml_metadata' in context
        assert 'yaml_content' in context
        
        # Check title is properly formatted
        assert context['title'] == 'Sample Component'
        assert context['component_name'] == 'sample_component'
        assert context['is_component'] is True
        
    def test_prepare_template_context_custom_overview(self, component_dir):
        """Test template context with custom overview text."""
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
        
        context = generator._prepare_template_context()
        
        assert context['overview'] == 'This is a custom overview text.'
    
    def test_prepare_template_context_parameters(self, component_dir, sample_extracted_metadata):
        """Test that parameters are properly formatted in context."""
        metadata_file = component_dir / "metadata.yaml"
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            metadata_file,
            is_component=True
        )
        
        context = generator._prepare_template_context()
        
        # Check parameters have required fields
        assert 'input_path' in context['parameters']
        assert 'type' in context['parameters']['input_path']
        assert 'default_str' in context['parameters']['input_path']
        assert 'description' in context['parameters']['input_path']
        
        # Check defaults are formatted correctly
        assert context['parameters']['input_path']['default_str'] == 'Required'
        assert context['parameters']['num_iterations']['default_str'] == '`10`'
    
    def test_prepare_usage_params(self, component_dir, sample_extracted_metadata):
        """Test usage example parameter preparation."""
        metadata_file = component_dir / "metadata.yaml"
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            metadata_file,
            is_component=True
        )
        
        usage_params = generator._prepare_usage_params()
        
        # Should show required params (input_path, output_path have no defaults)
        assert 'input_path' in usage_params
        assert 'output_path' in usage_params
    
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
        
        usage_params = generator._prepare_usage_params()
        
        # Check type-specific example values
        assert '"str_param_value"' == usage_params['str_param']  # String should have quotes
        assert '42' == usage_params['int_param']  # Int should be numeric
        assert 'True' == usage_params['bool_param']  # Bool should be boolean
        assert 'other_param_input' == usage_params['other_param']  # Custom type uses generic format

