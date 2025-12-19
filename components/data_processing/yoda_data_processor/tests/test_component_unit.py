"""Tests for the yoda_data_processor component."""

from unittest import mock

from ..component import prepare_yoda_dataset


class TestYodaDataProcessorUnitTests:
    """Unit tests for component logic."""

    def test_component_function_exists(self):
        """Test that the component function is properly imported."""
        assert callable(prepare_yoda_dataset)
        assert hasattr(prepare_yoda_dataset, "python_func")

    @mock.patch.dict("sys.modules", {"datasets": mock.MagicMock()})
    @mock.patch("datasets.load_dataset")
    def test_component_with_default_parameters(self, mock_load_dataset):
        """Test component with default train_split_ratio."""
        # Setup mock dataset with proper chaining
        mock_dataset = mock.MagicMock()

        # Configure length to return 100 consistently
        mock_dataset.__len__.return_value = 100

        # Ensure all transformation methods return the same mock for chaining
        mock_dataset.rename_column.return_value = mock_dataset
        mock_dataset.remove_columns.return_value = mock_dataset
        mock_dataset.map.return_value = mock_dataset

        # Setup train/test split return values
        mock_train = mock.MagicMock()
        mock_train.__len__.return_value = 80
        mock_train.save_to_disk = mock.MagicMock()

        mock_test = mock.MagicMock()
        mock_test.__len__.return_value = 20
        mock_test.save_to_disk = mock.MagicMock()

        split_result = {"train": mock_train, "test": mock_test}
        mock_dataset.train_test_split.return_value = split_result

        mock_load_dataset.return_value = mock_dataset

        # Mock output datasets
        mock_train_output = mock.MagicMock()
        mock_train_output.path = "/tmp/train"
        mock_eval_output = mock.MagicMock()
        mock_eval_output.path = "/tmp/eval"

        # Call the actual python function
        prepare_yoda_dataset.python_func(
            yoda_input_dataset="test-dataset", yoda_train_dataset=mock_train_output, yoda_eval_dataset=mock_eval_output
        )

        # Verify interactions
        mock_load_dataset.assert_called_once_with("test-dataset", split="train")
        # Component makes two rename_column calls
        expected_rename_calls = [mock.call("sentence", "prompt"), mock.call("translation_extra", "completion")]
        mock_dataset.rename_column.assert_has_calls(expected_rename_calls)
        mock_dataset.remove_columns.assert_called_once_with(["translation"])
        mock_dataset.map.assert_called_once()
        # Check train_test_split call (with floating point tolerance for test_size)
        assert mock_dataset.train_test_split.call_count == 1
        call_args, call_kwargs = mock_dataset.train_test_split.call_args
        assert call_kwargs["seed"] == 42
        assert abs(call_kwargs["test_size"] - 0.2) < 1e-10  # Allow for floating point precision
        mock_train.save_to_disk.assert_called_once_with("/tmp/train")
        mock_test.save_to_disk.assert_called_once_with("/tmp/eval")
