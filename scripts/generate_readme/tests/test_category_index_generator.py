"""Tests for CategoryIndexGenerator."""
from pathlib import Path
from scripts.generate_readme.category_index_generator import CategoryIndexGenerator


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
    
    def test_find_items_in_category_components(self, tmp_path):
        """Test finding all components in a category."""
        category_dir = tmp_path / "components" / "dev"
        category_dir.mkdir(parents=True)
        
        # Create component directories
        comp1_dir = category_dir / "component1"
        comp1_dir.mkdir()
        (comp1_dir / "component.py").write_text("# component 1")
        
        comp2_dir = category_dir / "component2"
        comp2_dir.mkdir()
        (comp2_dir / "component.py").write_text("# component 2")
        
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
        assert comp1_dir in items
        assert comp2_dir in items
        assert other_dir not in items
        assert pycache_dir not in items
    
    def test_find_items_in_category_pipelines(self, tmp_path):
        """Test finding all pipelines in a category."""
        category_dir = tmp_path / "pipelines" / "training"
        category_dir.mkdir(parents=True)
        
        # Create pipeline directories
        pipe1_dir = category_dir / "pipeline1"
        pipe1_dir.mkdir()
        (pipe1_dir / "pipeline.py").write_text("# pipeline 1")
        
        pipe2_dir = category_dir / "pipeline2"
        pipe2_dir.mkdir()
        (pipe2_dir / "pipeline.py").write_text("# pipeline 2")
        
        generator = CategoryIndexGenerator(category_dir, is_component=False)
        items = generator._find_items_in_category()
        
        assert len(items) == 2
        assert pipe1_dir in items
        assert pipe2_dir in items
    
    def test_find_items_empty_category(self, tmp_path):
        """Test finding items in an empty category."""
        category_dir = tmp_path / "components" / "empty"
        category_dir.mkdir(parents=True)
        
        generator = CategoryIndexGenerator(category_dir, is_component=True)
        items = generator._find_items_in_category()
        
        assert len(items) == 0
    
    def test_extract_item_info_component(self, tmp_path, sample_component_file):
        """Test extracting info from a component."""
        category_dir = tmp_path / "components" / "dev"
        category_dir.mkdir(parents=True)
        
        item_dir = category_dir / "hello_world"
        item_dir.mkdir()
        (item_dir / "component.py").write_text(sample_component_file)
        
        generator = CategoryIndexGenerator(category_dir, is_component=True)
        info = generator._extract_item_info(item_dir)
        
        assert info is not None
        assert info['name'] == 'hello_world'
        assert 'Simple greeting component' in info['overview']
        assert info['link'] == './hello_world/README.md'
    
    def test_extract_item_info_pipeline(self, tmp_path, sample_pipeline_file):
        """Test extracting info from a pipeline."""
        category_dir = tmp_path / "pipelines" / "dev"
        category_dir.mkdir(parents=True)
        
        item_dir = category_dir / "hello_pipeline"
        item_dir.mkdir()
        (item_dir / "pipeline.py").write_text(sample_pipeline_file)
        
        generator = CategoryIndexGenerator(category_dir, is_component=False)
        info = generator._extract_item_info(item_dir)
        
        assert info is not None
        assert info['name'] == 'hello_pipeline'
        assert 'Simple hello world pipeline' in info['overview']
        assert info['link'] == './hello_pipeline/README.md'
    
    def test_extract_item_info_multiline_overview(self, tmp_path):
        """Test that only first line of overview is used in index."""
        category_dir = tmp_path / "components" / "dev"
        category_dir.mkdir(parents=True)
        
        item_dir = category_dir / "test_comp"
        item_dir.mkdir()
        
        component_code = '''
from kfp import dsl

@dsl.component
def test_comp(text: str) -> str:
    """First line of overview.
    
    This is a longer description that should not
    appear in the category index.
    
    Args:
        text: Input text.
        
    Returns:
        Output text.
    """
    return text
'''
        (item_dir / "component.py").write_text(component_code)
        
        generator = CategoryIndexGenerator(category_dir, is_component=True)
        info = generator._extract_item_info(item_dir)
        
        assert info is not None
        assert info['overview'] == 'First line of overview.'
        assert 'longer description' not in info['overview']
    
    def test_extract_item_info_no_overview(self, tmp_path):
        """Test extraction when component has no docstring."""
        category_dir = tmp_path / "components" / "dev"
        category_dir.mkdir(parents=True)
        
        item_dir = category_dir / "no_docs"
        item_dir.mkdir()
        
        component_code = '''
from kfp import dsl

@dsl.component
def no_docs(text: str) -> str:
    return text
'''
        (item_dir / "component.py").write_text(component_code)
        
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
    
    def test_generate_component_index(self, tmp_path, sample_component_file):
        """Test generating complete category index for components."""
        category_dir = tmp_path / "components" / "dev"
        category_dir.mkdir(parents=True)
        
        # Create two components
        comp1_dir = category_dir / "component1"
        comp1_dir.mkdir()
        (comp1_dir / "component.py").write_text(sample_component_file)
        
        comp2_dir = category_dir / "component2"
        comp2_dir.mkdir()
        (comp2_dir / "component.py").write_text(sample_component_file)
        
        generator = CategoryIndexGenerator(category_dir, is_component=True)
        content = generator.generate()
        
        assert '# Dev Components' in content
        assert 'hello_world' in content
        assert 'Simple greeting component' in content
        assert './component1/README.md' in content
        assert './component2/README.md' in content
    
    def test_generate_pipeline_index(self, tmp_path, sample_pipeline_file):
        """Test generating complete category index for pipelines."""
        category_dir = tmp_path / "pipelines" / "training"
        category_dir.mkdir(parents=True)
        
        # Create pipeline
        pipe_dir = category_dir / "my_pipeline"
        pipe_dir.mkdir()
        (pipe_dir / "pipeline.py").write_text(sample_pipeline_file)
        
        generator = CategoryIndexGenerator(category_dir, is_component=False)
        content = generator.generate()
        
        assert '# Training Pipelines' in content
        assert 'hello_pipeline' in content
        assert 'Simple hello world pipeline' in content
        assert './my_pipeline/README.md' in content
    
    def test_generate_empty_category(self, tmp_path):
        """Test generating index for empty category."""
        category_dir = tmp_path / "components" / "empty"
        category_dir.mkdir(parents=True)
        
        generator = CategoryIndexGenerator(category_dir, is_component=True)
        content = generator.generate()
        
        assert '# Empty Components' in content
        # Should have header but no items listed
        assert '###' not in content
    
    def test_write_creates_file(self, tmp_path, sample_component_file):
        """Test that write() creates the README file."""
        category_dir = tmp_path / "components" / "dev"
        category_dir.mkdir(parents=True)
        
        # Create a component
        comp_dir = category_dir / "test_comp"
        comp_dir.mkdir()
        (comp_dir / "component.py").write_text(sample_component_file)
        
        generator = CategoryIndexGenerator(category_dir, is_component=True)
        generator.write()
        
        readme_file = category_dir / "README.md"
        assert readme_file.exists()
        
        content = readme_file.read_text()
        assert '# Dev Components' in content
        assert 'hello_world' in content
    
    def test_write_overwrites_existing(self, tmp_path, sample_component_file):
        """Test that write() overwrites existing README."""
        category_dir = tmp_path / "components" / "dev"
        category_dir.mkdir(parents=True)
        
        # Create existing README
        readme_file = category_dir / "README.md"
        readme_file.write_text("Old content")
        
        # Create a component
        comp_dir = category_dir / "test_comp"
        comp_dir.mkdir()
        (comp_dir / "component.py").write_text(sample_component_file)
        
        generator = CategoryIndexGenerator(category_dir, is_component=True)
        generator.write()
        
        content = readme_file.read_text()
        assert 'Old content' not in content
        assert '# Dev Components' in content


