"""Local runner tests for the tabular_train_test_split component."""

import pytest

from ..component import tabular_train_test_split


class TestTrainTestSplitLocalRunner:
    """Test component with LocalRunner (subprocess execution)."""

    @pytest.mark.skip(reason="LocalRunner test requires pandas and sklearn in subprocess")
    def test_local_execution(self, setup_and_teardown_subprocess_runner):  # noqa: F811
        """Test component execution with LocalRunner."""
        # Component signature: dataset, sampled_train_dataset, sampled_test_dataset, test_size.
        assert tabular_train_test_split is not None
