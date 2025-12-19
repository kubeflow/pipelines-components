import sys
from pathlib import Path

import pytest
from kfp import local


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart():
    """Pytest hook to add project root to the sys path for cleaner imports in the tests"""
    # Get the path of the current file
    this_file_path = Path(__file__).resolve()
    # Get the directory
    project_root = this_file_path.parent

    project_root_str = str(project_root)
    print(f'Adding project root "{project_root_str}" to the sys path for cleaner imports in tests')
    sys.path.append(project_root_str)


@pytest.fixture(scope="function")
def setup_and_teardown_subprocess_runner():
    """Setup LocalRunner environment for testing."""
    import os
    import shutil

    ws_root_base = "./test_workspace"
    pipeline_root_base = "./test_pipeline_outputs"
    ws_root = f"{ws_root_base}_subprocess"
    pipeline_root = f"{pipeline_root_base}_subprocess"
    Path(ws_root).mkdir(exist_ok=True)
    Path(pipeline_root).mkdir(exist_ok=True)
    local.init(
        runner=local.SubprocessRunner(use_venv=False),
        raise_on_error=True,
        workspace_root=ws_root,
        pipeline_root=pipeline_root,
    )
    yield
    try:
        if os.path.isdir(ws_root):
            shutil.rmtree(ws_root, ignore_errors=True)
        if os.path.isdir(pipeline_root):
            shutil.rmtree(pipeline_root, ignore_errors=True)
    except Exception as e:
        print(f"Failed to delete directory because of {e}")
