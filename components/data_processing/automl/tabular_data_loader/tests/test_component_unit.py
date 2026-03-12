"""Tests for the tabular_data_loader component.

boto3 and pandas are mocked via sys.modules so the real packages are not required.
Tests use the stdlib csv module for asserting on output CSV content.
"""

import csv
import io
import sys
from contextlib import contextmanager
from unittest import mock

import pytest

from ..component import automl_data_loader
from .mocked_pandas import MockedDataFrame, make_mocked_pandas_module

mocked_env_variables = {
    "AWS_ACCESS_KEY_ID": "test_key",
    "AWS_SECRET_ACCESS_KEY": "test_secret",
    "AWS_S3_ENDPOINT": "test_url",
}


@contextmanager
def _mock_boto3_module(get_object_return=None, get_object_side_effect=None):
    """Inject a fake boto3 module so the component does not require boto3 to be installed."""
    mock_boto3 = mock.MagicMock()
    mock_s3 = mock.MagicMock()
    if get_object_side_effect is not None:
        mock_s3.get_object.side_effect = get_object_side_effect
    else:
        mock_s3.get_object.return_value = get_object_return or {"Body": io.BytesIO(b"")}
    mock_boto3.client.return_value = mock_s3
    with mock.patch.dict(sys.modules, {"boto3": mock_boto3}):
        yield mock_s3


@contextmanager
def _mock_boto3_and_pandas(get_object_return=None, get_object_side_effect=None):
    """Inject mocked boto3 and pandas so the component runs without either dependency."""
    mocked_pandas = make_mocked_pandas_module()
    with _mock_boto3_module(
        get_object_return=get_object_return, get_object_side_effect=get_object_side_effect
    ) as mock_s3:
        with mock.patch.dict(sys.modules, {"pandas": mocked_pandas}):
            yield mock_s3


def _read_csv_path(path):
    """Read a CSV file with stdlib csv; return (headers, list of rows)."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        rows = list(reader)
    return header, rows


class TestAutomlDataLoaderUnitTests:
    """Unit tests for component logic."""

    def test_component_function_exists(self):
        """Test that the component function is properly imported."""
        assert callable(automl_data_loader)
        assert hasattr(automl_data_loader, "python_func")

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_component_with_default_parameters(self, tmp_path):
        """Test component with default sampling_method=None (resolved from task_type=regression -> random)."""
        csv_content = "a,b,c\n1,2,3\n4,5,6\n7,8,9\n"
        body_stream = io.BytesIO(csv_content.encode("utf-8"))

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}) as mock_s3:
            result = automl_data_loader.python_func(
                file_key="data/file.csv",
                bucket_name="my-bucket",
                workspace_path=str(tmp_path),
            )

            assert result is not None
            assert hasattr(result, "sample_config")
            assert result.sample_config["n_samples"] == 3
            mock_s3.get_object.assert_called_once_with(Bucket="my-bucket", Key="data/file.csv")
        expected_path = str(tmp_path / "datasets" / "full_dataset.csv")
        assert result.full_dataset_path == expected_path
        assert (tmp_path / "datasets" / "full_dataset.csv").exists()
        header, rows = _read_csv_path(result.full_dataset_path)
        assert header == ["a", "b", "c"]
        assert len(rows) == 3

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_component_explicit_first_n_rows(self, tmp_path):
        """Test component with explicit sampling_method='first_n_rows'."""
        csv_content = "x,y,z\n10,20,30\n40,50,60\n"
        body_stream = io.BytesIO(csv_content.encode("utf-8"))

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}):
            result = automl_data_loader.python_func(
                file_key="s3/path/data.csv",
                bucket_name="bucket",
                workspace_path=str(tmp_path),
                sampling_method="first_n_rows",
            )

            assert hasattr(result, "sample_config")
            assert result.sample_config["n_samples"] == 2
        header, rows = _read_csv_path(result.full_dataset_path)
        assert header == ["x", "y", "z"]
        assert len(rows) == 2

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_component_stratified_sampling_with_label_column(self, tmp_path):
        """Test component with sampling_method='stratified' and label_column."""
        csv_content = "feature1,feature2,target\n1,2,A\n2,3,A\n3,4,A\n4,5,B\n5,6,B\n6,7,B\n7,8,C\n8,9,C\n9,10,C\n"
        body_stream = io.BytesIO(csv_content.encode("utf-8"))

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}) as mock_s3:
            result = automl_data_loader.python_func(
                file_key="data/train.csv",
                bucket_name="my-bucket",
                workspace_path=str(tmp_path),
                sampling_method="stratified",
                label_column="target",
                task_type="multiclass",
            )

            assert hasattr(result, "sample_config")
            assert result.sample_config["n_samples"] == 9
            mock_s3.get_object.assert_called_once_with(Bucket="my-bucket", Key="data/train.csv")
        assert (tmp_path / "datasets" / "full_dataset.csv").exists()
        header, rows = _read_csv_path(result.full_dataset_path)
        assert "target" in header
        target_idx = header.index("target")
        target_vals = {row[target_idx] for row in rows}
        assert target_vals == {"A", "B", "C"}
        assert len(rows) == 9

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_component_stratified_requires_label_column(self, tmp_path):
        """Test that sampling_method='stratified' without label_column raises ValueError."""
        with _mock_boto3_and_pandas() as mock_s3:
            with pytest.raises(ValueError, match="label_column must be provided when sampling_method='stratified'"):
                automl_data_loader.python_func(
                    file_key="data/file.csv",
                    bucket_name="bucket",
                    workspace_path=str(tmp_path),
                    sampling_method="stratified",
                    label_column=None,
                    task_type="binary",
                )

            mock_s3.get_object.assert_not_called()

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_component_stratified_label_column_not_in_dataset(self, tmp_path):
        """Test that stratified sampling with missing target column raises ValueError."""
        csv_content = "a,b,c\n1,2,3\n4,5,6\n"
        body_stream = io.BytesIO(csv_content.encode("utf-8"))

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}):
            with pytest.raises(ValueError, match=r"Error reading CSV from S3"):
                automl_data_loader.python_func(
                    file_key="data/file.csv",
                    bucket_name="bucket",
                    workspace_path=str(tmp_path),
                    sampling_method="stratified",
                    label_column="label",
                    task_type="binary",
                )

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_component_stratified_drops_na_in_target(self, tmp_path):
        """Test that stratified sampling drops rows with NA in label_column."""
        csv_content = "f1,f2,target\n1,2,A\n2,3,\n3,4,B\n4,5,B\n"
        body_stream = io.BytesIO(csv_content.encode("utf-8"))

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}):
            result = automl_data_loader.python_func(
                file_key="data/file.csv",
                bucket_name="bucket",
                workspace_path=str(tmp_path),
                sampling_method="stratified",
                label_column="target",
                task_type="binary",
            )

            assert hasattr(result, "sample_config")
            assert result.sample_config["n_samples"] >= 2
        header, rows = _read_csv_path(result.full_dataset_path)
        target_idx = header.index("target")
        for row in rows:
            assert row[target_idx] != ""  # no NA/empty in target
        assert len(rows) >= 2

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_component_random_sampling_basic(self, tmp_path):
        """Test component with sampling_method='random' writes valid CSV and returns sample_config."""
        csv_content = "a,b,c\n1,2,3\n4,5,6\n7,8,9\n10,11,12\n"
        body_stream = io.BytesIO(csv_content.encode("utf-8"))

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}) as mock_s3:
            result = automl_data_loader.python_func(
                file_key="data/file.csv",
                bucket_name="my-bucket",
                workspace_path=str(tmp_path),
                sampling_method="random",
            )

            assert result.sample_config["n_samples"] == 4
            mock_s3.get_object.assert_called_once_with(Bucket="my-bucket", Key="data/file.csv")
        assert (tmp_path / "datasets" / "full_dataset.csv").exists()
        header, rows = _read_csv_path(result.full_dataset_path)
        assert header == ["a", "b", "c"]
        assert len(rows) == 4

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_component_random_sampling_deterministic(self, tmp_path):
        """Test that random sampling with fixed random_state is reproducible.

        Use a large BYTES_PER_ROW so the mock reports >1GB for few rows, triggering
        _sample_random's downsampling (component lines 173-176). Otherwise no sample()
        call runs and the test would trivially pass without exercising the seed logic.
        """
        csv_content = "x,y\n1,2\n3,4\n5,6\n7,8\n9,10\n"

        def get_object(**kwargs):
            return {"Body": io.BytesIO(csv_content.encode("utf-8"))}

        original_bytes_per_row = MockedDataFrame.BYTES_PER_ROW
        try:
            # 5 rows * 500M bytes/row = 2.5GB > 1GB limit -> triggers random downsampling
            MockedDataFrame.BYTES_PER_ROW = 500_000_000

            with _mock_boto3_and_pandas(get_object_side_effect=get_object):
                result1 = automl_data_loader.python_func(
                    file_key="data/file.csv",
                    bucket_name="bucket",
                    workspace_path=str(tmp_path / "ws1"),
                    sampling_method="random",
                )
                result2 = automl_data_loader.python_func(
                    file_key="data/file.csv",
                    bucket_name="bucket",
                    workspace_path=str(tmp_path / "ws2"),
                    sampling_method="random",
                )

            n1 = result1.sample_config["n_samples"]
            n2 = result2.sample_config["n_samples"]
            assert n1 == n2, "Same random_state should yield same sample size"
            assert n1 == 2, "Downsampling should have been triggered (2 rows * 0.5 GB/row = 1 GB)"
            _, rows1 = _read_csv_path(result1.full_dataset_path)
            _, rows2 = _read_csv_path(result2.full_dataset_path)
            assert rows1 == rows2, "Same random_state should yield identical rows"
        finally:
            MockedDataFrame.BYTES_PER_ROW = original_bytes_per_row

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_component_random_sampling_multiple_chunks(self, tmp_path):
        """Test random sampling with CSV large enough to trigger multiple chunks (>10k rows)."""
        header = "col1,col2\n"
        rows = "\n".join(f"{i},{i * 2}" for i in range(15000))
        csv_content = header + rows
        body_stream = io.BytesIO(csv_content.encode("utf-8"))

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}):
            result = automl_data_loader.python_func(
                file_key="data/large.csv",
                bucket_name="bucket",
                workspace_path=str(tmp_path),
                sampling_method="random",
            )

            assert result.sample_config["n_samples"] == 15000
        assert (tmp_path / "datasets" / "full_dataset.csv").exists()
        header_out, rows_out = _read_csv_path(result.full_dataset_path)
        assert header_out == ["col1", "col2"]
        assert len(rows_out) == 15000
