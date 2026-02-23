"""Tests for kfp_compilation module."""

from pathlib import Path

from ..kfp_compilation import (
    compile_and_get_yaml,
    find_decorated_functions_runtime,
    load_module_from_path,
)

RESOURCES_DIR = Path(__file__).parent.parent.parent / "validate_base_images/tests/resources"


class TestFindDecoratedFunctions:
    """Tests for find_decorated_functions function."""

    def test_find_component_functions(self):
        """Test finding @dsl.component decorated functions."""
        module_path = str(RESOURCES_DIR / "components/training/custom_image_component/component.py")
        module = load_module_from_path(module_path, "test_find_component")

        functions = find_decorated_functions_runtime(module, "component")

        assert len(functions) == 1
        assert functions[0][0] == "train_model"
        assert callable(functions[0][1])

    def test_find_pipeline_functions(self):
        """Test finding @dsl.pipeline decorated functions."""
        module_path = str(RESOURCES_DIR / "pipelines/training/multi_image_pipeline/pipeline.py")
        module = load_module_from_path(module_path, "test_find_pipeline")

        functions = find_decorated_functions_runtime(module, "pipeline")

        func_names = [f[0] for f in functions]
        assert "training_pipeline" in func_names

    def test_find_functools_partial_wrapped_component(self):
        """Test finding components decorated via functools.partial wrapper."""
        module_path = str(RESOURCES_DIR / "components/edge_cases/functools_partial_image/component.py")
        module = load_module_from_path(module_path, "test_functools_partial")

        functions = find_decorated_functions_runtime(module, "component")

        assert len(functions) == 1
        assert functions[0][0] == "component_with_partial_wrapper"
        assert callable(functions[0][1])

    def test_returns_empty_for_no_decorated_functions(self):
        """Test that empty list is returned when module has no decorated functions."""
        import types

        empty_module = types.ModuleType("empty_module")
        empty_module.regular_function = lambda x: x

        functions = find_decorated_functions_runtime(empty_module, "component")

        assert functions == []

    def test_skips_private_attributes(self):
        """Test that private attributes (starting with _) are skipped."""
        module_path = str(RESOURCES_DIR / "components/training/custom_image_component/component.py")
        module = load_module_from_path(module_path, "test_private")

        functions = find_decorated_functions_runtime(module, "component")

        func_names = [f[0] for f in functions]
        assert not any(name.startswith("_") for name in func_names)


class TestCompileResultAndExtractors:
    """Tests for two-doc return shape and get_base_images_from_compile_result."""

    def test_single_doc_returns_single_dict(self):
        """Single doc returns that doc (no pipeline_spec/platform_spec wrapper)."""
        import os
        import tempfile

        module_path = str(RESOURCES_DIR / "components/training/custom_image_component/component.py")
        module = load_module_from_path(module_path, "test_single_doc")
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            path = f.name
        try:
            result = compile_and_get_yaml(module.train_model, path)
            assert isinstance(result, dict)
            assert "pipeline_spec" not in result
            assert "deploymentSpec" in result
        finally:
            os.unlink(path)

    def test_get_base_images_single_doc(self):
        """get_base_images_from_compile_result with single dict matches pipeline spec extractor."""
        from ..base_image import extract_base_images_from_pipeline_spec, get_base_images_from_compile_result

        single = {"deploymentSpec": {"executors": {"e1": {"container": {"image": "img:1"}}}}}
        assert get_base_images_from_compile_result(single) == extract_base_images_from_pipeline_spec(single)

    def test_get_base_images_two_docs(self):
        """get_base_images_from_compile_result with two specs returns union."""
        from ..base_image import get_base_images_from_compile_result

        result = {
            "pipeline_spec": {
                "deploymentSpec": {"executors": {"e1": {"container": {"image": "pipeline:tag"}}}},
            },
            "platform_spec": {
                "platforms": {
                    "k8s": {
                        "deploymentSpec": {
                            "executors": {"e2": {"container": {"image": "platform:tag"}}},
                        },
                    },
                },
            },
        }
        images = get_base_images_from_compile_result(result)
        assert "pipeline:tag" in images
        assert "platform:tag" in images

    def test_extract_base_images_from_platform_spec(self):
        """extract_base_images_from_platform_spec reads platforms.*.deploymentSpec.executors."""
        from ..base_image import extract_base_images_from_platform_spec

        platform_spec = {
            "platforms": {
                "kubernetes": {
                    "deploymentSpec": {
                        "executors": {"exec-1": {"container": {"image": "myimg:1"}}},
                    },
                },
            },
        }
        assert extract_base_images_from_platform_spec(platform_spec) == {"myimg:1"}
