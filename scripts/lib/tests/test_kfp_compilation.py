"""Tests for kfp_compilation module."""

from pathlib import Path

from ..kfp_compilation import (
    _merge_ir_docs,
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


class TestMergeIrDocs:
    """Tests for _merge_ir_docs: same behavior as pre-refactor merge."""

    def test_empty_docs_returns_empty_dict(self):
        """Empty doc list returns empty dict."""
        assert _merge_ir_docs([]) == {}

    def test_single_doc_returns_that_doc(self):
        """Single doc is returned unchanged."""
        doc = {"deploymentSpec": {"executors": {"e1": {"container": {"image": "img:1"}}}}}
        assert _merge_ir_docs([doc]) is doc

    def test_two_docs_merge_executors_root_components(self):
        """Two docs merge executors, root.dag.tasks, and components."""
        doc1 = {
            "deploymentSpec": {"executors": {"e1": {"container": {"image": "img1"}}}},
            "root": {"dag": {"tasks": {"t1": {"componentRef": {"name": "c1"}}}}},
            "components": {"c1": {"executorLabel": "e1"}},
        }
        doc2 = {
            "deploymentSpec": {"executors": {"e2": {"container": {"image": "img2"}}}},
            "root": {"dag": {"tasks": {"t2": {"componentRef": {"name": "c2"}}}}},
            "components": {"c2": {"executorLabel": "e2"}},
        }
        merged = _merge_ir_docs([doc1, doc2])
        assert merged["deploymentSpec"]["executors"]["e1"]["container"]["image"] == "img1"
        assert merged["deploymentSpec"]["executors"]["e2"]["container"]["image"] == "img2"
        assert "t1" in merged["root"]["dag"]["tasks"]
        assert "t2" in merged["root"]["dag"]["tasks"]
        assert "c1" in merged["components"]
        assert "c2" in merged["components"]

    def test_non_dict_doc_skipped(self):
        """Non-dict entries in doc list are skipped."""
        doc1 = {"components": {"a": {}}}
        merged = _merge_ir_docs([doc1, "not a dict", {"components": {"b": {}}}])
        assert merged["components"]["a"] == {}
        assert merged["components"]["b"] == {}

    def test_merged_result_works_with_extract_base_images(self):
        """Merged IR has the shape extract_base_images expects."""
        from ..base_image import extract_base_images

        doc1 = {
            "deploymentSpec": {"executors": {"e1": {"container": {"image": "first:tag"}}}},
            "root": {"dag": {"tasks": {}}},
            "components": {},
        }
        doc2 = {
            "deploymentSpec": {"executors": {"e2": {"container": {"image": "second:tag"}}}},
            "root": {"dag": {"tasks": {}}},
            "components": {},
        }
        merged = _merge_ir_docs([doc1, doc2])
        images = extract_base_images(merged)
        assert "first:tag" in images
        assert "second:tag" in images
