"""Tests for content_generator.py module."""
from ..content_generator import ReadmeContentGenerator


class TestReadmeContentGenerator:
    """Tests for ReadmeContentGenerator."""
    
    def test_init_with_component(self, component_dir, sample_extracted_metadata):
        """Test initialization with component metadata."""
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            component_dir
        )
        
        assert generator.metadata == sample_extracted_metadata
        assert generator.feature_metadata is not None
    
    def test_init_with_pipeline(self, pipeline_dir, sample_extracted_metadata):
        """Test initialization with pipeline metadata."""
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            pipeline_dir
        )
        
        assert generator.metadata == sample_extracted_metadata
    
    def test_load_feature_metadata(self, component_dir, sample_extracted_metadata):
        """Test loading YAML metadata from file."""
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            component_dir
        )
        
        assert 'name' in generator.feature_metadata
        assert generator.feature_metadata['name'] == 'sample_component'
        assert 'tier' in generator.feature_metadata
    
    def test_load_feature_metadata_excludes_ci(self, temp_dir, sample_extracted_metadata):
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
            temp_dir
        )
        
        assert 'ci' not in generator.feature_metadata
        assert 'name' in generator.feature_metadata
        assert 'tier' in generator.feature_metadata
    
    def test_load_owners_file_exists(self, component_dir, sample_extracted_metadata):
        """Test loading OWNERS file when it exists."""
        # Create an OWNERS file
        owners_file = component_dir / "OWNERS"
        owners_file.write_text("""approvers:
  - user1
  - user2
reviewers:
  - user3
  - user4
""")
        
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            component_dir
        )
        
        # Check that owners were loaded into feature_metadata
        assert 'owners' in generator.feature_metadata
        assert 'approvers' in generator.feature_metadata['owners']
        assert 'reviewers' in generator.feature_metadata['owners']
        assert generator.feature_metadata['owners']['approvers'] == ['user1', 'user2']
        assert generator.feature_metadata['owners']['reviewers'] == ['user3', 'user4']
    
    def test_load_owners_file_not_exists(self, component_dir, sample_extracted_metadata):
        """Test that missing OWNERS file doesn't cause errors."""
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            component_dir
        )
        
        # Should not have owners in feature_metadata when OWNERS doesn't exist
        assert 'owners' not in generator.feature_metadata
    
    def test_owners_in_generated_readme(self, component_dir, sample_extracted_metadata):
        """Test that OWNERS data appears in generated README."""
        # Create an OWNERS file
        owners_file = component_dir / "OWNERS"
        owners_file.write_text("""approvers:
  - alice
  - bob
reviewers:
  - charlie
""")
        
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            component_dir
        )
        
        readme = generator.generate_readme()
        
        # Check that owners appear in the README
        assert 'Owners' in readme
        assert 'alice' in readme
        assert 'bob' in readme
        assert 'charlie' in readme
        assert 'Approvers' in readme or 'approvers' in readme.lower()
        assert 'Reviewers' in readme or 'reviewers' in readme.lower()
    
    def test_prepare_template_context(self, component_dir, sample_extracted_metadata):
        """Test template context preparation."""
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            component_dir
        )
        
        context = generator._prepare_template_context()
        
        # Check all required context keys are present
        assert 'title' in context
        assert 'overview' in context
        assert 'parameters' in context
        assert 'returns' in context
        assert 'component_name' in context
        assert 'example_code' in context
        assert 'formatted_metadata' in context
        
        # Check title is properly formatted
        assert context['title'] == 'Sample Component'
        assert context['component_name'] == 'sample_component'
        
        # Check example_code is empty string when no example_pipeline.py exists
        assert context['example_code'] == ''
        
        # Check formatted metadata exists
        assert isinstance(context['formatted_metadata'], dict)
        assert len(context['formatted_metadata']) > 0
        
    def test_prepare_template_context_custom_overview(self, component_dir):
        """Test template context with custom overview text."""
        custom_metadata = {
            'name': 'test_component',
            'overview': 'This is a custom overview text.',
            'parameters': {},
            'returns': {}
        }
        
        generator = ReadmeContentGenerator(
            custom_metadata,
            component_dir
        )
        
        context = generator._prepare_template_context()
        
        assert context['overview'] == 'This is a custom overview text.'
    
    def test_prepare_template_context_parameters(self, component_dir, sample_extracted_metadata):
        """Test that parameters are properly formatted in context."""
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            component_dir
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
    
    def test_load_example_pipeline(self, component_dir, sample_extracted_metadata):
        """Test loading example_pipeline.py file."""
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            component_dir
        )
        
        # When no example_pipeline.py exists, should return empty string
        example_code = generator._load_example_pipeline()
        assert example_code == ''
        
        # Create an example_pipeline.py file
        example_file = component_dir / 'example_pipeline.py'
        example_content = 'from kfp import dsl\n\n@dsl.pipeline()\ndef my_pipeline():\n    pass'
        example_file.write_text(example_content)
        
        # Now it should load the content
        example_code = generator._load_example_pipeline()
        assert example_code == example_content
    
    def test_generate_readme_component(self, component_dir, sample_extracted_metadata):
        """Test complete README generation for a component."""
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            component_dir
        )
        
        readme = generator.generate_readme()
        
        # Check all sections are present (except Usage Example since no example_pipeline.py exists)
        assert '# Sample Component' in readme
        assert '## Overview' in readme
        assert '## Inputs' in readme
        assert '## Outputs' in readme
        assert '## Metadata' in readme
        
        # Usage Example should NOT be present when example_pipeline.py doesn't exist
        assert '## Usage Example' not in readme
        
        # Now test with example_pipeline.py present
        example_file = component_dir / 'example_pipeline.py'
        example_file.write_text('from kfp import dsl\n\n@dsl.pipeline()\ndef test_pipeline():\n    pass')
        
        # Regenerate readme
        generator2 = ReadmeContentGenerator(
            sample_extracted_metadata,
            component_dir
        )
        readme2 = generator2.generate_readme()
        
        # Now Usage Example should be present
        assert '## Usage Example' in readme2
        assert 'from kfp import dsl' in readme2
    
    def test_generate_readme_pipeline(self, pipeline_dir, sample_extracted_metadata):
        """Test complete README generation for a pipeline."""
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            pipeline_dir
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
            temp_dir
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
    
    def test_format_title_snake_case(self, component_dir, sample_extracted_metadata):
        """Test formatting snake_case titles."""
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            component_dir
        )
        
        assert generator._format_title('my_field_name') == 'My Field Name'
        assert generator._format_title('test_value') == 'Test Value'
        assert generator._format_title('single') == 'Single'
    
    def test_format_title_camel_case(self, component_dir, sample_extracted_metadata):
        """Test formatting camelCase titles."""
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            component_dir
        )
        
        assert generator._format_title('myFieldName') == 'My Field Name'
        assert generator._format_title('testValue') == 'Test Value'
    
    def test_format_title_acronyms(self, component_dir, sample_extracted_metadata):
        """Test that known acronyms are kept uppercase."""
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            component_dir
        )
        
        assert generator._format_title('kfp_version') == 'KFP Version'
        assert generator._format_title('api_endpoint') == 'API Endpoint'
        assert generator._format_title('user_id') == 'User ID'
    
    def test_format_value_basic_types(self, component_dir, sample_extracted_metadata):
        """Test formatting basic value types."""
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            component_dir
        )
        
        assert generator._format_value(True) == 'Yes'
        assert generator._format_value(False) == 'No'
        assert generator._format_value('test string') == 'test string'
        assert generator._format_value(123) == '123'
        assert generator._format_value(None) == 'None'
    
    def test_format_value_list(self, component_dir, sample_extracted_metadata):
        """Test formatting list values."""
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            component_dir
        )
        
        # Single item list - should still use nested list format
        result_single = generator._format_value(['item1'])
        assert '\n  - item1' in result_single
        
        # Multiple items list
        result = generator._format_value(['item1', 'item2', 'item3'])
        assert '\n  - item1' in result
        assert '\n  - item2' in result
        assert '\n  - item3' in result
        
        # Empty list
        assert generator._format_value([]) == 'None'
    
    def test_format_value_dict(self, component_dir, sample_extracted_metadata):
        """Test formatting dict values."""
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            component_dir
        )
        
        test_dict = {'key1': 'value1', 'key2': 'value2'}
        result = generator._format_value(test_dict)
        
        assert 'Key1: value1' in result
        assert 'Key2: value2' in result
        assert '\n  - ' in result
    
    def test_format_metadata(self, component_dir, sample_extracted_metadata):
        """Test complete metadata formatting."""
        generator = ReadmeContentGenerator(
            sample_extracted_metadata,
            component_dir
        )
        
        formatted = generator._format_metadata()
        
        # Check that keys are formatted
        assert 'Name' in formatted
        assert 'Tier' in formatted
        
        # Check that values are present
        assert formatted['Name'] == 'sample_component'
        assert formatted['Tier'] == 'core'

