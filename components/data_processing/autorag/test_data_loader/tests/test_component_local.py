"""Local runner tests for the test_data_loader component."""

import pytest

from ..component import test_data_loader


class TestTestDataLoaderLocalRunner:
    """Test component with LocalRunner (subprocess execution)."""

    @pytest.mark.skip(reason="Requires S3 credentials (AWS_* env); run E2E in pipeline with secrets")
    def test_local_execution(self, setup_and_teardown_subprocess_runner):  # noqa: F811
        """Test component execution with LocalRunner."""
        result = test_data_loader(
            test_data_bucket_name="test-bucket",
            test_data_path="test-key.json",
        )
        assert result is not None
