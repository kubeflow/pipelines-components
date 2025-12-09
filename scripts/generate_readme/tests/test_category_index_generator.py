"""Tests for CategoryIndexGenerator."""
from pathlib import Path
from ..category_index_generator import CategoryIndexGenerator
from .conftest import create_component_dir


class TestCategoryIndexGenerator:
    """Test suite for CategoryIndexGenerator."""
    
    def test_init_component_category(self, tmp_path):
        """Test initialization for a component category."""
        category_dir = tmp_path / "components" / "dev"
        category_dir.mkdir(parents=True)
        
        generator = CategoryIndexGenerator(category_dir, is_component=True)
        
        assert generator.category_dir == category_dir
        assert generator.is_component == True
        assert generator.category_name == "dev"
    
    def test_init_pipeline_category(self, tmp_path):
        """Test initialization for a pipeline category."""
        category_dir = tmp_path / "pipelines" / "training"
        category_dir.mkdir(parents=True)
        
        generator = CategoryIndexGenerator(category_dir, is_component=False)
        
        assert generator.category_dir == category_dir
        assert generator.is_component == False
        assert generator.category_name == "training"
    
    def test_find_items_in_category_components(self, category_with_components):
        """Test finding all components in a category."""
        category_dir, comp_dirs = category_with_components
        
        # Create a directory without component.py (should be ignored)
        other_dir = category_dir / "other"
        other_dir.mkdir()
        (other_dir / "something.py").write_text("# not a component")
        
        # Create __pycache__ directory (should be ignored)
        pycache_dir = category_dir / "__pycache__"
        pycache_dir.mkdir()
        
        generator = CategoryIndexGenerator(category_dir, is_component=True)
        items = generator._find_items_in_category()
        
        assert len(items) == 2
        assert comp_dirs[0] in items
        assert comp_dirs[1] in items
        assert other_dir not in items
        assert pycache_dir not in items
    
    def test_find_items_in_category_pipelines(self, category_with_pipelines):
        """Test finding all pipelines in a category."""
        category_dir, pipe_dirs = category_with_pipelines
        
        generator = CategoryIndexGenerator(category_dir, is_component=False)
        items = generator._find_items_in_category()
        
        assert len(items) == 2
        assert pipe_dirs[0] in items
        assert pipe_dirs[1] in items
    
    def test_find_items_empty_category(self, tmp_path):
        """Test finding items in an empty category."""
        category_dir = tmp_path / "components" / "empty"
        category_dir.mkdir(parents=True)
        
        generator = CategoryIndexGenerator(category_dir, is_component=True)
        items = generator._find_items_in_category()
        
        assert len(items) == 0
    
    def test_extract_item_info_component(self, category_with_components):
        """Test extracting info from a component."""
        category_dir, comp_dirs = category_with_components
        item_dir = comp_dirs[0]  # Use first component
        
        generator = CategoryIndexGenerator(category_dir, is_component=True)
        info = generator._extract_item_info(item_dir)
        
        assert info is not None
        assert info['name'] == 'Sample Component'
        assert 'A sample component for testing' in info['overview']
        assert info['link'] == './component1/README.md'
    
    def test_extract_item_info_pipeline(self, category_with_pipelines):
        """Test extracting info from a pipeline."""
        category_dir, pipe_dirs = category_with_pipelines
        pipe_dir = pipe_dirs[0]  # Use first pipeline
        
        generator = CategoryIndexGenerator(category_dir, is_component=False)
        info = generator._extract_item_info(pipe_dir)
        
        assert info is not None
        assert info['name'] == 'Sample Pipeline'
        assert 'A sample pipeline for testing' in info['overview']
        assert info['link'] == './pipeline1/README.md'
    
    def test_extract_item_info_multiline_overview(self, tmp_path, component_multiline_overview):
        """Test that only first line of overview is used in index."""
        category_dir = tmp_path / "components" / "dev"
        category_dir.mkdir(parents=True)
        
        item_dir = create_component_dir(category_dir, "test_comp", component_multiline_overview)
        
        generator = CategoryIndexGenerator(category_dir, is_component=True)
        info = generator._extract_item_info(item_dir)
        
        assert info is not None
        assert info['overview'] == 'First line of overview.'
        assert 'longer description' not in info['overview']
    
    def test_extract_item_info_no_overview(self, tmp_path, component_no_docstring):
        """Test extraction when component has no docstring."""
        category_dir = tmp_path / "components" / "dev"
        category_dir.mkdir(parents=True)
        
        item_dir = create_component_dir(category_dir, "no_docs", component_no_docstring)
        
        generator = CategoryIndexGenerator(category_dir, is_component=True)
        info = generator._extract_item_info(item_dir)
        
        assert info is not None
        assert info['overview'] == 'No description available.'
    
    def test_extract_item_info_missing_file(self, tmp_path):
        """Test extraction when source file is missing."""
        category_dir = tmp_path / "components" / "dev"
        category_dir.mkdir(parents=True)
        
        item_dir = category_dir / "missing"
        item_dir.mkdir()
        # No component.py file
        
        generator = CategoryIndexGenerator(category_dir, is_component=True)
        info = generator._extract_item_info(item_dir)
        
        assert info is None
    
    def test_generate_component_index(self, category_with_components):
        """Test generating complete category index for components."""
        category_dir, _ = category_with_components
        
        generator = CategoryIndexGenerator(category_dir, is_component=True)
        content = generator.generate()
        
        assert '# Dev Components' in content
        assert 'Sample Component' in content
        assert 'A sample component for testing' in content
        assert './component1/README.md' in content
        assert './component2/README.md' in content
    
    def test_generate_pipeline_index(self, category_with_pipelines):
        """Test generating complete category index for pipelines."""
        category_dir, _ = category_with_pipelines
        
        generator = CategoryIndexGenerator(category_dir, is_component=False)
        content = generator.generate()
        
        assert '# Training Pipelines' in content
        assert 'Sample Pipeline' in content
        assert 'A sample pipeline for testing' in content
        assert './pipeline1/README.md' in content
        assert './pipeline2/README.md' in content
    
    def test_generate_empty_category(self, tmp_path):
        """Test generating index for empty category."""
        category_dir = tmp_path / "components" / "empty"
        category_dir.mkdir(parents=True)
        
        generator = CategoryIndexGenerator(category_dir, is_component=True)
        content = generator.generate()
        
        assert '# Empty Components' in content
        # Should have header but no items listed
        assert '###' not in content

    def test_metadata_yaml_name_preferred(self, tmp_path, sample_component_file):
        """Test that name from metadata.yaml is preferred over function name."""
        from generate_readme.tests.conftest import create_component_dir
        
        category_dir = tmp_path / "components" / "test"
        category_dir.mkdir(parents=True)
        
        # Create component with a name in metadata.yaml that differs from function name
        metadata_content = """name: My Custom Component Name
tier: core
"""
        comp_dir = create_component_dir(
            category_dir, 
            "test_comp", 
            sample_component_file,
            metadata_content
        )
        
        generator = CategoryIndexGenerator(category_dir, is_component=True)
        content = generator.generate()
        
        # Should use the formatted name from metadata.yaml, not the function name
        assert 'My Custom Component Name' in content
        # Should NOT contain the function name "sample_component"
        assert 'Sample Component' not in content
