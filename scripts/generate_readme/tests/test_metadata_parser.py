"""Tests for metadata_parser.py module."""

import ast
from pathlib import Path

from ..metadata_parser import (
    ComponentMetadataParser,
    MetadataParser,
    PipelineMetadataParser,
)

import pytest


class TestMetadataParser:
    """Tests for the MetadataParser base class."""
    
    def test_parse_google_docstring_with_args_and_returns(self):
        """Test parsing a complete Google-style docstring."""
        parser = MetadataParser(Path("dummy.py"))
        docstring = """A sample function.
        
        This does something useful.
        
        Args:
            param1 (str): First parameter description.
            param2 (int): Second parameter description.
            
        Returns:
            The result of processing.
        """
        
        result = parser._parse_google_docstring(docstring)
        
        # docstring-parser normalizes whitespace and joins short + long description
        assert result['overview'] == "A sample function.\n\nThis does something useful."
        assert 'param1' in result['args']
        assert result['args']['param1'] == "First parameter description."
        assert result['args']['param2'] == "Second parameter description."
        assert 'result of processing' in result['returns_description']
    
    def test_parse_google_docstring_empty(self):
        """Test parsing an empty docstring."""
        parser = MetadataParser(Path("dummy.py"))
        result = parser._parse_google_docstring("")
        
        assert result['overview'] == ''
        assert result['args'] == {}
        assert result['returns_description'] == ''
    
    def test_parse_google_docstring_multiline_arg_description(self):
        """Test parsing arguments with multi-line descriptions."""
        parser = MetadataParser(Path("dummy.py"))
        docstring = """Sample function.
        
        Args:
            long_param (str): This is a very long parameter description
                that spans multiple lines and should be concatenated together.
        """
        
        result = parser._parse_google_docstring(docstring)
        
        assert 'long_param' in result['args']
        assert 'multiple lines' in result['args']['long_param']
        assert 'concatenated together' in result['args']['long_param']
    
    def test_get_type_string_basic_types(self):
        """Test type string conversion for basic types."""
        parser = MetadataParser(Path("dummy.py"))
        
        assert parser._get_type_string(str) == 'str'
        assert parser._get_type_string(int) == 'int'
        assert parser._get_type_string(bool) == 'bool'
        assert parser._get_type_string(float) == 'float'
    
    def test_get_type_string_optional(self):
        """Test type string conversion for Optional types."""
        from typing import Optional
        
        parser = MetadataParser(Path("dummy.py"))
        result = parser._get_type_string(Optional[str])
        
        # Should contain Optional (or Union with None in some Python versions)
        assert 'Optional' in result or ('Union' in result and 'None' in result)
    
    def test_get_type_string_list(self):
        """Test type string conversion for List types."""
        from typing import List
        
        parser = MetadataParser(Path("dummy.py"))
        result = parser._get_type_string(List[str])
        
        # Should contain list (or List) - case insensitive check
        assert 'list' in result.lower()


class TestComponentMetadataParser:
    """Tests for ComponentMetadataParser."""
    
    def test_find_function_with_dsl_component(self, temp_dir):
        """Test finding a function with @dsl.component decorator."""
        component_file = temp_dir / "component.py"
        component_file.write_text("""
from kfp import dsl

@dsl.component
def my_component(param: str):
    pass
""")
        
        parser = ComponentMetadataParser(component_file)
        result = parser.find_function()

        assert result == "my_component"

    def test_find_function_with_component_decorator(self, temp_dir):
        """Test finding a function with @component decorator."""
        component_file = temp_dir / "component.py"
        component_file.write_text("""
from kfp.dsl import component

@component
def my_component(param: str):
    pass
""")
        
        parser = ComponentMetadataParser(component_file)
        result = parser.find_function()

        assert result == "my_component"

    def test_find_function_with_call_decorator(self, temp_dir):
        """Test finding a function with @dsl.component() decorator."""
        component_file = temp_dir / "component.py"
        component_file.write_text("""
from kfp import dsl

@dsl.component()
def my_component(param: str):
    pass
""")
        
        parser = ComponentMetadataParser(component_file)
        result = parser.find_function()
        
        assert result == "my_component"
    
    def test_find_function_not_found(self, temp_dir):
        """Test when no component function is found."""
        component_file = temp_dir / "component.py"
        component_file.write_text("""
def regular_function(param: str):
    pass
""")
        
        parser = ComponentMetadataParser(component_file)
        result = parser.find_function()
        
        assert result is None
    
    def test_is_component_decorator_dsl_component(self):
        """Test _is_component_decorator with @dsl.component."""
        parser = ComponentMetadataParser(Path("dummy.py"))
        
        # Create AST node for @dsl.component
        code = "@dsl.component\ndef func(): pass"
        tree = ast.parse(code)
        decorator = tree.body[0].decorator_list[0]
        
        assert parser._is_component_decorator(decorator) is True
    
    def test_is_component_decorator_direct_import(self):
        """Test _is_component_decorator with @component."""
        parser = ComponentMetadataParser(Path("dummy.py"))
        
        # Create AST node for @component
        code = "@component\ndef func(): pass"
        tree = ast.parse(code)
        decorator = tree.body[0].decorator_list[0]
        
        assert parser._is_component_decorator(decorator) is True
    
    def test_is_component_decorator_kfp_dsl_component(self):
        """Test _is_component_decorator with @kfp.dsl.component."""
        parser = ComponentMetadataParser(Path("dummy.py"))
        
        # Create AST node for @kfp.dsl.component
        code = "@kfp.dsl.component\ndef func(): pass"
        tree = ast.parse(code)
        decorator = tree.body[0].decorator_list[0]
        
        assert parser._is_component_decorator(decorator) is True
    
    def test_is_component_decorator_wrong_decorator(self):
        """Test _is_component_decorator with non-component decorator."""
        parser = ComponentMetadataParser(Path("dummy.py"))
        
        # Create AST node for @pipeline
        code = "@pipeline\ndef func(): pass"
        tree = ast.parse(code)
        decorator = tree.body[0].decorator_list[0]
        
        assert parser._is_component_decorator(decorator) is False
    
    def test_extract_decorator_name_component(self, temp_dir):
        """Test extracting name parameter from @dsl.component decorator."""
        component_file = temp_dir / "component.py"
        component_file.write_text("""
from kfp import dsl

@dsl.component(name='custom-component-name', base_image='python:3.10')
def my_component(param: str) -> str:
    '''A component with custom name in decorator.
    
    Args:
        param: Input parameter.
        
    Returns:
        Output value.
    '''
    return param
""")
        
        parser = ComponentMetadataParser(component_file)
        
        # Test finding the function
        function_name = parser.find_function()
        assert function_name == 'my_component'
        
        # Test extracting decorator name from AST (without executing the code)
        decorator_name = parser._get_name_from_decorator_if_exists('my_component')
        
        # Should extract the decorator name
        assert decorator_name == 'custom-component-name'
    
    def test_extract_decorator_name_component_no_name(self, temp_dir):
        """Test extracting name when decorator has no name parameter."""
        component_file = temp_dir / "component.py"
        component_file.write_text("""
from kfp import dsl

@dsl.component(base_image='python:3.10')
def my_component(param: str) -> str:
    '''A component without custom name in decorator.'''
    return param
""")
        
        parser = ComponentMetadataParser(component_file)
        
        # Test extracting decorator name (should return None)
        decorator_name = parser._get_name_from_decorator_if_exists('my_component')
        
        # Should return None when no name in decorator
        assert decorator_name is None

    def test_extract_metadata_basic(self, temp_dir):
        """Test extracting metadata from a basic component."""
        component_file = temp_dir / "component.py"
        component_file.write_text("""
from kfp import dsl

@dsl.component
def my_component(input_text: str, count: int = 5) -> str:
    '''A sample component for testing.

    This component processes text input.

    Args:
        input_text: The text to process.
        count: Number of times to repeat. Defaults to 5.

    Returns:
        The processed text output.
    '''
    return input_text * count
""")

        parser = ComponentMetadataParser(component_file)
        metadata = parser.extract_metadata('my_component')

        # Verify basic metadata
        assert metadata['name'] == 'my_component'
        assert 'A sample component for testing' in metadata['overview']
        assert 'processes text input' in metadata['overview']

        # Verify parameters
        assert 'input_text' in metadata['parameters']
        assert metadata['parameters']['input_text']['type'] == 'str'
        assert metadata['parameters']['input_text']['default'] is None
        assert 'text to process' in metadata['parameters']['input_text']['description']

        assert 'count' in metadata['parameters']
        assert metadata['parameters']['count']['type'] == 'int'
        assert metadata['parameters']['count']['default'] == 5
        assert 'Number of times' in metadata['parameters']['count']['description']

        # Verify returns
        assert metadata['returns']['type'] == 'str'
        assert 'processed text output' in metadata['returns']['description']

    def test_extract_metadata_uses_function_name(self, temp_dir):
        """Test that component uses function name when no decorator name exists."""
        component_file = temp_dir / "component.py"
        component_file.write_text("""
from kfp import dsl

@dsl.component
def my_custom_component(param: str):
    '''A component using function name.

    Args:
        param: Input parameter.
    '''
    print(param)
""")

        parser = ComponentMetadataParser(component_file)
        metadata = parser.extract_metadata('my_custom_component')

        # Should use the function name since components don't support 'name' parameter
        assert metadata['name'] == 'my_custom_component'
        assert 'function name' in metadata['overview']

    def test_extract_metadata_no_docstring(self, temp_dir):
        """Test extracting metadata from component without docstring."""
        component_file = temp_dir / "component.py"
        component_file.write_text("""
from kfp import dsl

@dsl.component
def my_component(param: str) -> str:
    return param
""")

        parser = ComponentMetadataParser(component_file)
        metadata = parser.extract_metadata('my_component')

        # Should still extract basic info
        assert metadata['name'] == 'my_component'
        assert metadata['overview'] == ''
        assert 'param' in metadata['parameters']
        assert metadata['parameters']['param']['type'] == 'str'
        assert metadata['returns']['type'] == 'str'

    def test_extract_metadata_optional_types(self, temp_dir):
        """Test extracting metadata with Optional types."""
        component_file = temp_dir / "component.py"
        component_file.write_text("""
from typing import Optional
from kfp import dsl

@dsl.component
def my_component(required_param: str, optional_param: Optional[int] = None):
    '''Component with optional types.

    Args:
        required_param: A required parameter.
        optional_param: An optional parameter.
    '''
    print(f"{required_param}: {optional_param}")
""")

        parser = ComponentMetadataParser(component_file)
        metadata = parser.extract_metadata('my_component')

        # Verify optional parameter type
        assert 'optional_param' in metadata['parameters']
        param_type = metadata['parameters']['optional_param']['type']
        # Should contain Optional (or Union with None)
        assert 'Optional' in param_type or ('Union' in param_type and 'None' in param_type)
        assert metadata['parameters']['optional_param']['default'] is None

    def test_extract_metadata_list_types(self, temp_dir):
        """Test extracting metadata with List types."""
        component_file = temp_dir / "component.py"
        component_file.write_text("""
from typing import List
from kfp import dsl

@dsl.component
def my_component(items: List[str]) -> List[int]:
    '''Component with list types.

    Args:
        items: List of string items.

    Returns:
        List of integers.
    '''
    return [len(item) for item in items]
""")

        parser = ComponentMetadataParser(component_file)
        metadata = parser.extract_metadata('my_component')

        # Verify list parameter type
        assert 'items' in metadata['parameters']
        param_type = metadata['parameters']['items']['type'].lower()
        assert 'list' in param_type

        # Verify list return type
        return_type = metadata['returns']['type'].lower()
        assert 'list' in return_type

    def test_extract_metadata_no_return_annotation(self, temp_dir):
        """Test extracting metadata from component without return annotation."""
        component_file = temp_dir / "component.py"
        component_file.write_text("""
from kfp import dsl

@dsl.component
def my_component(param: str):
    '''Component without return annotation.

    Args:
        param: Input parameter.
    '''
    print(param)
""")

        parser = ComponentMetadataParser(component_file)
        metadata = parser.extract_metadata('my_component')

        # Should handle missing return annotation
        assert metadata['name'] == 'my_component'
        assert 'param' in metadata['parameters']
        # Returns should be empty dict when no annotation
        assert metadata['returns'] == {}

    def test_extract_metadata_multiple_params_with_defaults(self, temp_dir):
        """Test extracting metadata with multiple parameters and various defaults."""
        component_file = temp_dir / "component.py"
        component_file.write_text("""
from kfp import dsl

@dsl.component
def my_component(
    name: str,
    age: int = 25,
    active: bool = True,
    score: float = 0.95
) -> str:
    '''Component with multiple parameters.

    Args:
        name: Person's name.
        age: Person's age.
        active: Whether person is active.
        score: Performance score.

    Returns:
        Summary string.
    '''
    return f"{name}: {age}, {active}, {score}"
""")

        parser = ComponentMetadataParser(component_file)
        metadata = parser.extract_metadata('my_component')

        # Verify all parameters
        assert len(metadata['parameters']) == 4

        assert metadata['parameters']['name']['type'] == 'str'
        assert metadata['parameters']['name']['default'] is None

        assert metadata['parameters']['age']['type'] == 'int'
        assert metadata['parameters']['age']['default'] == 25

        assert metadata['parameters']['active']['type'] == 'bool'
        assert metadata['parameters']['active']['default'] is True

        assert metadata['parameters']['score']['type'] == 'float'
        assert metadata['parameters']['score']['default'] == pytest.approx(0.95)


class TestPipelineMetadataParser:
    """Tests for PipelineMetadataParser."""
    
    def test_find_function_with_dsl_pipeline(self, temp_dir):
        """Test finding a function with @dsl.pipeline decorator."""
        pipeline_file = temp_dir / "pipeline.py"
        pipeline_file.write_text("""
from kfp import dsl

@dsl.pipeline(name='test-pipeline')
def my_pipeline(param: str):
    pass
""")
        
        parser = PipelineMetadataParser(pipeline_file)
        result = parser.find_function()
        
        assert result == "my_pipeline"
    
    def test_find_function_with_pipeline_decorator(self, temp_dir):
        """Test finding a function with @pipeline decorator."""
        pipeline_file = temp_dir / "pipeline.py"
        pipeline_file.write_text("""
from kfp.dsl import pipeline

@pipeline
def my_pipeline(param: str):
    pass
""")
        
        parser = PipelineMetadataParser(pipeline_file)
        result = parser.find_function()
        
        assert result == "my_pipeline"
    
    def test_find_function_not_found(self, temp_dir):
        """Test when no pipeline function is found."""
        pipeline_file = temp_dir / "pipeline.py"
        pipeline_file.write_text("""
def regular_function(param: str):
    pass
""")
        
        parser = PipelineMetadataParser(pipeline_file)
        result = parser.find_function()
        
        assert result is None
    
    def test_is_pipeline_decorator_dsl_pipeline(self):
        """Test _is_pipeline_decorator with @dsl.pipeline."""
        parser = PipelineMetadataParser(Path("dummy.py"))
        
        # Create AST node for @dsl.pipeline
        code = "@dsl.pipeline\ndef func(): pass"
        tree = ast.parse(code)
        decorator = tree.body[0].decorator_list[0]
        
        assert parser._is_pipeline_decorator(decorator) is True
    
    def test_is_pipeline_decorator_with_args(self):
        """Test _is_pipeline_decorator with @dsl.pipeline(name='test')."""
        parser = PipelineMetadataParser(Path("dummy.py"))
        
        # Create AST node for @dsl.pipeline(name='test')
        code = "@dsl.pipeline(name='test')\ndef func(): pass"
        tree = ast.parse(code)
        decorator = tree.body[0].decorator_list[0]
        
        assert parser._is_pipeline_decorator(decorator) is True
    
    def test_is_pipeline_decorator_wrong_decorator(self):
        """Test _is_pipeline_decorator with non-pipeline decorator."""
        parser = PipelineMetadataParser(Path("dummy.py"))
        
        # Create AST node for @component
        code = "@component\ndef func(): pass"
        tree = ast.parse(code)
        decorator = tree.body[0].decorator_list[0]
        
        assert parser._is_pipeline_decorator(decorator) is False
    
    def test_extract_decorator_name_pipeline(self, temp_dir):
        """Test extracting name parameter from @dsl.pipeline decorator."""
        pipeline_file = temp_dir / "pipeline.py"
        pipeline_file.write_text("""
from kfp import dsl

@dsl.pipeline(name='custom-pipeline-name', description='A test pipeline')
def my_pipeline(input_data: str) -> str:
    '''A pipeline with custom name in decorator.
    
    Args:
        input_data: Input data path.
        
    Returns:
        Output data path.
    '''
    return input_data
""")
        
        parser = PipelineMetadataParser(pipeline_file)
        
        # Test finding the function
        function_name = parser.find_function()
        assert function_name == 'my_pipeline'
        
        # Test extracting decorator name from AST (without executing the code)
        decorator_name = parser._get_name_from_decorator_if_exists('my_pipeline')
        
        # Should extract the decorator name
        assert decorator_name == 'custom-pipeline-name'
    
    def test_extract_decorator_name_pipeline_no_name(self, temp_dir):
        """Test extracting name when decorator has no name parameter."""
        pipeline_file = temp_dir / "pipeline.py"
        pipeline_file.write_text("""
from kfp import dsl

@dsl.pipeline(description='A test pipeline')
def my_pipeline(input_data: str) -> str:
    '''A pipeline without custom name in decorator.'''
    return input_data
""")
        
        parser = PipelineMetadataParser(pipeline_file)
        
        # Test extracting decorator name (should return None)
        decorator_name = parser._get_name_from_decorator_if_exists('my_pipeline')
        
        # Should return None when no name in decorator
        assert decorator_name is None

    def test_extract_metadata_basic(self, temp_dir):
        """Test extracting metadata from a basic pipeline."""
        pipeline_file = temp_dir / "pipeline.py"
        pipeline_file.write_text("""
from kfp import dsl

@dsl.component
def dummy_component():
    pass

@dsl.pipeline
def my_pipeline(input_path: str, output_path: str, num_epochs: int = 10):
    '''A sample training pipeline.

    This pipeline trains a machine learning model.

    Args:
        input_path: Path to input training data.
        output_path: Path to save the trained model.
        num_epochs: Number of training epochs. Defaults to 10.
    '''
    dummy_component()
""")

        parser = PipelineMetadataParser(pipeline_file)
        metadata = parser.extract_metadata('my_pipeline')

        # Verify basic metadata
        assert metadata['name'] == 'my_pipeline'
        assert 'sample training pipeline' in metadata['overview']
        assert 'trains a machine learning model' in metadata['overview']

        # Verify parameters
        assert 'input_path' in metadata['parameters']
        assert metadata['parameters']['input_path']['type'] == 'str'
        assert metadata['parameters']['input_path']['default'] is None
        assert 'training data' in metadata['parameters']['input_path']['description']

        assert 'output_path' in metadata['parameters']
        assert metadata['parameters']['output_path']['type'] == 'str'
        assert metadata['parameters']['output_path']['default'] is None

        assert 'num_epochs' in metadata['parameters']
        assert metadata['parameters']['num_epochs']['type'] == 'int'
        assert metadata['parameters']['num_epochs']['default'] == 10
        assert 'training epochs' in metadata['parameters']['num_epochs']['description']

    def test_extract_metadata_with_custom_name(self, temp_dir):
        """Test extracting metadata when decorator has custom name."""
        pipeline_file = temp_dir / "pipeline.py"
        pipeline_file.write_text("""
from kfp import dsl

@dsl.component
def dummy_comp():
    pass

@dsl.pipeline(name='custom-pipeline-name')
def my_pipeline(data_path: str):
    '''A pipeline with custom name.

    Args:
        data_path: Path to data.
    '''
    dummy_comp()
""")

        parser = PipelineMetadataParser(pipeline_file)
        metadata = parser.extract_metadata('my_pipeline')

        # Should use the decorator name, not function name
        assert metadata['name'] == 'custom-pipeline-name'
        assert 'custom name' in metadata['overview']

    def test_extract_metadata_no_docstring(self, temp_dir):
        """Test extracting metadata from pipeline without docstring."""
        pipeline_file = temp_dir / "pipeline.py"
        pipeline_file.write_text("""
from kfp import dsl

@dsl.component
def dummy_comp():
    pass

@dsl.pipeline
def my_pipeline(param: str):
    dummy_comp()
""")

        parser = PipelineMetadataParser(pipeline_file)
        metadata = parser.extract_metadata('my_pipeline')

        # Should still extract basic info
        assert metadata['name'] == 'my_pipeline'
        assert metadata['overview'] == ''
        assert 'param' in metadata['parameters']
        assert metadata['parameters']['param']['type'] == 'str'

    def test_extract_metadata_optional_types(self, temp_dir):
        """Test extracting metadata with Optional types."""
        pipeline_file = temp_dir / "pipeline.py"
        pipeline_file.write_text("""
from typing import Optional
from kfp import dsl

@dsl.component
def dummy_comp():
    pass

@dsl.pipeline
def my_pipeline(
    required_input: str,
    optional_config: Optional[str] = None
):
    '''Pipeline with optional parameters.

    Args:
        required_input: Required input path.
        optional_config: Optional configuration path.
    '''
    dummy_comp()
""")

        parser = PipelineMetadataParser(pipeline_file)
        metadata = parser.extract_metadata('my_pipeline')

        # Verify optional parameter type
        assert 'optional_config' in metadata['parameters']
        param_type = metadata['parameters']['optional_config']['type']
        # Should contain Optional (or Union with None)
        assert 'Optional' in param_type or ('Union' in param_type and 'None' in param_type)
        assert metadata['parameters']['optional_config']['default'] is None

    def test_extract_metadata_dict_types(self, temp_dir):
        """Test extracting metadata with Dict types."""
        pipeline_file = temp_dir / "pipeline.py"
        pipeline_file.write_text("""
from typing import Dict
from kfp import dsl

@dsl.component
def dummy_comp():
    pass

@dsl.pipeline
def my_pipeline(config: Dict[str, str], hyperparams: Dict[str, float]):
    '''Pipeline with dictionary parameters.

    Args:
        config: Configuration dictionary.
        hyperparams: Hyperparameter dictionary.
    '''
    dummy_comp()
""")

        parser = PipelineMetadataParser(pipeline_file)
        metadata = parser.extract_metadata('my_pipeline')

        # Verify dict parameter types
        assert 'config' in metadata['parameters']
        config_type = metadata['parameters']['config']['type']
        assert 'Dict' in config_type or 'dict' in config_type.lower()

        assert 'hyperparams' in metadata['parameters']
        hyperparams_type = metadata['parameters']['hyperparams']['type']
        assert 'Dict' in hyperparams_type or 'dict' in hyperparams_type.lower()

    def test_extract_metadata_no_parameters(self, temp_dir):
        """Test extracting metadata from pipeline without parameters."""
        pipeline_file = temp_dir / "pipeline.py"
        pipeline_file.write_text("""
from kfp import dsl

@dsl.component
def dummy_comp():
    pass

@dsl.pipeline
def my_pipeline():
    '''A simple pipeline with no parameters.

    This pipeline runs a fixed workflow.
    '''
    dummy_comp()
""")

        parser = PipelineMetadataParser(pipeline_file)
        metadata = parser.extract_metadata('my_pipeline')

        # Should handle no parameters gracefully
        assert metadata['name'] == 'my_pipeline'
        assert 'simple pipeline' in metadata['overview']
        assert len(metadata['parameters']) == 0

    def test_extract_metadata_complex_pipeline(self, temp_dir):
        """Test extracting metadata from a complex pipeline with many parameters."""
        pipeline_file = temp_dir / "pipeline.py"
        pipeline_file.write_text("""
from typing import List, Optional
from kfp import dsl

@dsl.component
def dummy_comp():
    pass

@dsl.pipeline(name='complex-ml-pipeline')
def my_pipeline(
    dataset_path: str,
    model_type: str = "xgboost",
    learning_rate: float = 0.01,
    num_iterations: int = 1000,
    enable_validation: bool = True,
    feature_columns: Optional[List[str]] = None
):
    '''A complex machine learning pipeline.

    This pipeline demonstrates various parameter types and defaults.

    Args:
        dataset_path: Path to the training dataset.
        model_type: Type of model to train.
        learning_rate: Learning rate for optimization.
        num_iterations: Number of training iterations.
        enable_validation: Whether to run validation.
        feature_columns: Optional list of feature column names.
    '''
    dummy_comp()
""")

        parser = PipelineMetadataParser(pipeline_file)
        metadata = parser.extract_metadata('my_pipeline')

        # Verify custom name
        assert metadata['name'] == 'complex-ml-pipeline'
        assert 'complex machine learning pipeline' in metadata['overview']

        # Verify all parameters with correct types and defaults
        assert len(metadata['parameters']) == 6

        assert metadata['parameters']['dataset_path']['type'] == 'str'
        assert metadata['parameters']['dataset_path']['default'] is None

        assert metadata['parameters']['model_type']['type'] == 'str'
        assert metadata['parameters']['model_type']['default'] == "xgboost"

        assert metadata['parameters']['learning_rate']['type'] == 'float'
        assert metadata['parameters']['learning_rate']['default'] == pytest.approx(0.01)

        assert metadata['parameters']['num_iterations']['type'] == 'int'
        assert metadata['parameters']['num_iterations']['default'] == 1000

        assert metadata['parameters']['enable_validation']['type'] == 'bool'
        assert metadata['parameters']['enable_validation']['default'] is True

        feature_type = metadata['parameters']['feature_columns']['type']
        assert 'Optional' in feature_type or 'Union' in feature_type
        assert metadata['parameters']['feature_columns']['default'] is None
