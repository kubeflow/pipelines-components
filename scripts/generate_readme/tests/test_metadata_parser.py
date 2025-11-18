"""Tests for metadata_parser.py module."""

import ast
from pathlib import Path

import pytest

from ..metadata_parser import (
    ComponentMetadataParser,
    MetadataParser,
    PipelineMetadataParser,
)


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

