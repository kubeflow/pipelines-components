#!/usr/bin/env python3
"""Unit tests for compile_check."""

from __future__ import annotations

import argparse
import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import Any

import yaml

from .. import compile_check


def _write_file(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


def _ensure_packages(paths: dict[str, Path]) -> None:
    for package_path in paths.values():
        package_path.mkdir(parents=True, exist_ok=True)
        init_file = package_path / "__init__.py"
        if not init_file.exists():
            init_file.write_text("", encoding="utf-8")


class CompileCheckTestCase(unittest.TestCase):
    """Unit tests covering compile_check’s discovery, dependency, and compile paths."""

    def setUp(self) -> None:
        """Create a temporary repository root for each test case."""
        self._tempdir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self._tempdir.name)
        self.original_repo_root = compile_check.REPO_ROOT
        compile_check.REPO_ROOT = self.repo_root

    def tearDown(self) -> None:
        """Clean up temporary directories and restore global state."""
        compile_check.REPO_ROOT = self.original_repo_root
        self._tempdir.cleanup()

    def _run_check(self, **overrides) -> int:
        args = argparse.Namespace(
            path=[],
            fail_fast=False,
            include_flagless=False,
            verbose=False,
        )
        for key, value in overrides.items():
            setattr(args, key, value)

        return compile_check.run_validation(args)

    def _create_component(
        self,
        component_name: str,
        *,
        metadata: dict[str, Any],
        body: str,
    ) -> Path:
        component_root = self.repo_root / "components"
        training_dir = component_root / "training"
        component_dir = training_dir / component_name
        _ensure_packages(
            {
                "root": component_root,
                "category": training_dir,
                "component": component_dir,
            }
        )

        metadata_path = component_dir / "metadata.yaml"
        component_path = component_dir / "component.py"

        base_metadata: dict[str, Any] = {
            "name": component_name,
            "tier": "core",
            "stability": "stable",
            "ci": {"compile_check": True},
        }
        base_metadata.update(metadata)

        metadata_path.write_text(
            yaml.safe_dump(base_metadata, sort_keys=False),
            encoding="utf-8",
        )
        _write_file(
            component_path,
            textwrap.dedent(
                f"""\
                from kfp import dsl

                @dsl.component(base_image="python:3.11")
                def {component_name}_op(a: int = 1) -> int:
                    {body}
                """
            ),
        )
        return component_dir

    def _create_pipeline(
        self,
        pipeline_name: str,
        *,
        metadata: dict[str, Any],
        body: str,
        with_decorator: bool = True,
    ) -> Path:
        pipeline_root = self.repo_root / "pipelines"
        training_dir = pipeline_root / "training"
        pipeline_dir = training_dir / pipeline_name
        _ensure_packages(
            {
                "root": pipeline_root,
                "category": training_dir,
                "pipeline": pipeline_dir,
            }
        )

        metadata_path = pipeline_dir / "metadata.yaml"
        pipeline_path = pipeline_dir / "pipeline.py"

        base_metadata: dict[str, Any] = {
            "name": pipeline_name,
            "tier": "core",
            "stability": "stable",
            "ci": {"compile_check": True},
        }
        base_metadata.update(metadata)

        metadata_path.write_text(
            yaml.safe_dump(base_metadata, sort_keys=False),
            encoding="utf-8",
        )

        lines = [
            "from kfp import dsl",
            "",
            "@dsl.component",
            "def helper(x: int) -> int:",
            "    return x + 1",
            "",
        ]
        if with_decorator:
            lines.append('@dsl.pipeline(name="test")')
        lines.append(f"def {pipeline_name}_pipeline():")
        for line in textwrap.dedent(body).strip().splitlines():
            lines.append(f"    {line}")

        _write_file(pipeline_path, "\n".join(lines) + "\n")
        return pipeline_dir

    def test_successful_compile(self) -> None:
        """A valid component compiles and returns success."""
        self._create_component(
            "valid_component",
            metadata={"dependencies": {}},
            body="return a + 1",
        )
        exit_code = self._run_check()
        self.assertEqual(exit_code, 0)

    def test_successful_pipeline_compile(self) -> None:
        """A valid pipeline compiles and returns success."""
        self._create_pipeline(
            "valid_pipeline",
            metadata={"dependencies": {}},
            body="""
helper(x=1)
""",
        )
        exit_code = self._run_check()
        self.assertEqual(exit_code, 0)

    def test_dependency_validation_failure(self) -> None:
        """Invalid dependency entries cause a failure before compilation."""
        self._create_component(
            "bad_dependency_component",
            metadata={
                "dependencies": {
                    "kubeflow": [
                        {"name": "Pipelines", "version": ">>=bad"},
                    ]
                },
            },
            body="return a + 1",
        )
        exit_code = self._run_check()
        self.assertEqual(exit_code, 1)

    def test_pipeline_missing_decorator_fails(self) -> None:
        """A pipeline module without @dsl.pipeline decorator fails validation."""
        self._create_pipeline(
            "invalid_pipeline",
            metadata={"dependencies": {}},
            body="""
helper(x=1)
""",
            with_decorator=False,
        )
        exit_code = self._run_check()
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
