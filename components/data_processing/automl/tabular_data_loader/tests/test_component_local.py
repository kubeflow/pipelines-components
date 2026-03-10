"""Local runner tests for the tabular_data_loader component."""

import pytest

from ..component import automl_data_loader


class TestAutomlDataLoaderLocalRunner:
    """Test component with LocalRunner (subprocess execution)."""

    @pytest.mark.skip(reason="LocalRunner test requires S3 credentials and a real bucket")
    def test_local_execution(self, setup_and_teardown_subprocess_runner):  # noqa: F811
        """Test component execution with LocalRunner."""
        # TODO: Implement local runner test with real S3 or mock.
        # Component signature: file_key, bucket_name, full_dataset,
        # sampling_method ("first_n_rows" | "stratified"), label_column (required if stratified).
        assert automl_data_loader is not None
