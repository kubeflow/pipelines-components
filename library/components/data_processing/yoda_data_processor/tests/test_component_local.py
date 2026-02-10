"""Tests for the yoda_data_processor component."""

from ..component import prepare_yoda_dataset


class TestYodaDataProcessorLocalRunner:
    """Test component with LocalRunner (subprocess execution)."""

    def test_local_execution(self, setup_and_teardown_subprocess_runner):  # noqa: F811
        """Test component execution with LocalRunner."""
        # Execute the component
        prepare_yoda_dataset(yoda_input_dataset="dvgodoy/yoda_sentences")
