"""Tests for kfp_compilation module."""

from pathlib import Path

from ..kfp_compilation import find_decorated_functions, load_module_from_path

RESOURCES_DIR = Path(__file__).parent.parent.parent / "validate_base_images/tests/resources"


class TestFindDecoratedFunctions:
    """Tests for find_decorated_functions function."""

    def test_find_component_functions(self):
        """Test finding @dsl.component decorated functions."""
        module_path = str(RESOURCES_DIR / "components/training/custom_image_component/component.py")
        module = load_module_from_path(module_path, "test_find_component")

        functions = find_decorated_functions(module, "component")

        assert len(functions) == 1
        assert functions[0][0] == "train_model"
        assert callable(functions[0][1])

    def test_find_pipeline_functions(self):
        """Test finding @dsl.pipeline decorated functions."""
        module_path = str(RESOURCES_DIR / "pipelines/training/multi_image_pipeline/pipeline.py")
        module = load_module_from_path(module_path, "test_find_pipeline")

        functions = find_decorated_functions(module, "pipeline")

        func_names = [f[0] for f in functions]
        assert "training_pipeline" in func_names

    def test_find_functools_partial_wrapped_component(self):
        """Test finding components decorated via functools.partial wrapper."""
        module_path = str(RESOURCES_DIR / "components/edge_cases/functools_partial_image/component.py")
        module = load_module_from_path(module_path, "test_functools_partial")

        functions = find_decorated_functions(module, "component")

        assert len(functions) == 1
        assert functions[0][0] == "component_with_partial_wrapper"
        assert callable(functions[0][1])

    def test_returns_empty_for_no_decorated_functions(self):
        """Test that empty list is returned when module has no decorated functions."""
        import types

        empty_module = types.ModuleType("empty_module")
        empty_module.regular_function = lambda x: x

        functions = find_decorated_functions(empty_module, "component")

        assert functions == []

    def test_skips_private_attributes(self):
        """Test that private attributes (starting with _) are skipped."""
        module_path = str(RESOURCES_DIR / "components/training/custom_image_component/component.py")
        module = load_module_from_path(module_path, "test_private")

        functions = find_decorated_functions(module, "component")

        func_names = [f[0] for f in functions]
        assert not any(name.startswith("_") for name in func_names)
