"""Tests for the tabular_data_loader component.

boto3, pandas, and sklearn are mocked via sys.modules so the real packages are not required.
Tests use the stdlib csv module for asserting on output CSV content.
"""

import csv
import io
import sys
from contextlib import contextmanager
from unittest import mock

import pytest

from ..component import automl_data_loader
from .mocked_pandas import MockedDataFrame, make_mocked_pandas_module, make_mocked_sklearn_module

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
    """Inject mocked boto3, pandas, and sklearn so the component runs without any dependency."""
    mocked_pandas = make_mocked_pandas_module()
    mock_sklearn, mock_model_selection = make_mocked_sklearn_module()
    with _mock_boto3_module(
        get_object_return=get_object_return, get_object_side_effect=get_object_side_effect
    ) as mock_s3:
        with mock.patch.dict(
            sys.modules,
            {
                "pandas": mocked_pandas,
                "sklearn": mock_sklearn,
                "sklearn.model_selection": mock_model_selection,
            },
        ):
            yield mock_s3


def _read_csv_path(path):
    """Read a CSV file with stdlib csv; return (headers, list of rows)."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        rows = list(reader)
    return header, rows


def _make_test_artifact(tmp_path, name="test_output.csv"):
    """Create a mock artifact with .path and .uri for sampled_test_dataset."""
    art = mock.MagicMock()
    art.path = str(tmp_path / name)
    art.uri = "/artifacts/test"
    return art


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
        sampled_test = _make_test_artifact(tmp_path)

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}) as mock_s3:
            result = automl_data_loader.python_func(
                file_key="data/file.csv",
                bucket_name="my-bucket",
                workspace_path=str(tmp_path),
                label_column="c",
                sampled_test_dataset=sampled_test,
            )

            assert result is not None
            assert hasattr(result, "sample_config")
            assert result.sample_config["n_samples"] == 3
            mock_s3.get_object.assert_called_once_with(Bucket="my-bucket", Key="data/file.csv")

        # Verify split outputs exist
        assert (tmp_path / "datasets" / "models_selection_train_dataset.csv").exists()
        assert (tmp_path / "datasets" / "extra_train_dataset.csv").exists()

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_component_explicit_first_n_rows(self, tmp_path):
        """Test component with explicit sampling_method='first_n_rows'."""
        csv_content = "x,y,z\n10,20,30\n40,50,60\n"
        body_stream = io.BytesIO(csv_content.encode("utf-8"))
        sampled_test = _make_test_artifact(tmp_path)

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}):
            result = automl_data_loader.python_func(
                file_key="s3/path/data.csv",
                bucket_name="bucket",
                workspace_path=str(tmp_path),
                label_column="z",
                sampled_test_dataset=sampled_test,
                sampling_method="first_n_rows",
            )

            assert hasattr(result, "sample_config")
            assert result.sample_config["n_samples"] == 2

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_component_stratified_sampling_with_label_column(self, tmp_path):
        """Test component with sampling_method='stratified' and label_column."""
        csv_content = "feature1,feature2,target\n1,2,A\n2,3,A\n3,4,A\n4,5,B\n5,6,B\n6,7,B\n7,8,C\n8,9,C\n9,10,C\n"
        body_stream = io.BytesIO(csv_content.encode("utf-8"))
        sampled_test = _make_test_artifact(tmp_path)

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}) as mock_s3:
            result = automl_data_loader.python_func(
                file_key="data/train.csv",
                bucket_name="my-bucket",
                workspace_path=str(tmp_path),
                sampling_method="stratified",
                label_column="target",
                task_type="multiclass",
                sampled_test_dataset=sampled_test,
            )

            assert hasattr(result, "sample_config")
            assert result.sample_config["n_samples"] == 9
            mock_s3.get_object.assert_called_once_with(Bucket="my-bucket", Key="data/train.csv")
        assert (tmp_path / "datasets" / "models_selection_train_dataset.csv").exists()

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_component_stratified_requires_label_column(self, tmp_path):
        """Test that sampling_method='stratified' without label_column raises ValueError."""
        sampled_test = _make_test_artifact(tmp_path)

        with _mock_boto3_and_pandas() as mock_s3:
            with pytest.raises(ValueError, match="label_column must be provided when sampling_method='stratified'"):
                automl_data_loader.python_func(
                    file_key="data/file.csv",
                    bucket_name="bucket",
                    workspace_path=str(tmp_path),
                    sampling_method="stratified",
                    label_column=None,
                    task_type="binary",
                    sampled_test_dataset=sampled_test,
                )

            mock_s3.get_object.assert_not_called()

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_component_stratified_label_column_not_in_dataset(self, tmp_path):
        """Test that stratified sampling with missing target column raises ValueError."""
        csv_content = "a,b,c\n1,2,3\n4,5,6\n"
        body_stream = io.BytesIO(csv_content.encode("utf-8"))
        sampled_test = _make_test_artifact(tmp_path)

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}):
            with pytest.raises(ValueError, match=r"Error reading CSV from S3"):
                automl_data_loader.python_func(
                    file_key="data/file.csv",
                    bucket_name="bucket",
                    workspace_path=str(tmp_path),
                    sampling_method="stratified",
                    label_column="label",
                    task_type="binary",
                    sampled_test_dataset=sampled_test,
                )

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_component_stratified_drops_na_in_target(self, tmp_path):
        """Test that stratified sampling drops rows with NA in label_column."""
        csv_content = "f1,f2,target\n1,2,A\n2,3,\n3,4,B\n4,5,B\n"
        body_stream = io.BytesIO(csv_content.encode("utf-8"))
        sampled_test = _make_test_artifact(tmp_path)

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}):
            result = automl_data_loader.python_func(
                file_key="data/file.csv",
                bucket_name="bucket",
                workspace_path=str(tmp_path),
                sampling_method="stratified",
                label_column="target",
                task_type="binary",
                sampled_test_dataset=sampled_test,
            )

            assert hasattr(result, "sample_config")
            assert result.sample_config["n_samples"] >= 2

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_component_random_sampling_basic(self, tmp_path):
        """Test component with sampling_method='random' writes valid CSV and returns sample_config."""
        csv_content = "a,b,c\n1,2,3\n4,5,6\n7,8,9\n10,11,12\n"
        body_stream = io.BytesIO(csv_content.encode("utf-8"))
        sampled_test = _make_test_artifact(tmp_path)

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}) as mock_s3:
            result = automl_data_loader.python_func(
                file_key="data/file.csv",
                bucket_name="my-bucket",
                workspace_path=str(tmp_path),
                label_column="c",
                sampled_test_dataset=sampled_test,
                sampling_method="random",
            )

            assert result.sample_config["n_samples"] == 4
            mock_s3.get_object.assert_called_once_with(Bucket="my-bucket", Key="data/file.csv")
        assert (tmp_path / "datasets" / "models_selection_train_dataset.csv").exists()
        assert (tmp_path / "datasets" / "extra_train_dataset.csv").exists()

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_component_random_sampling_deterministic(self, tmp_path):
        """Test that random sampling with fixed random_state is reproducible.

        Use a large BYTES_PER_ROW so the mock reports >1GB for few rows, triggering
        _sample_random's downsampling. Otherwise no sample() call runs and the test
        would trivially pass without exercising the seed logic.
        """
        csv_content = "x,y\n1,2\n3,4\n5,6\n7,8\n9,10\n"

        def get_object(**kwargs):
            return {"Body": io.BytesIO(csv_content.encode("utf-8"))}

        original_bytes_per_row = MockedDataFrame.BYTES_PER_ROW
        try:
            # 5 rows * 500M bytes/row = 2.5GB > 1GB limit -> triggers random downsampling
            MockedDataFrame.BYTES_PER_ROW = 500_000_000

            with _mock_boto3_and_pandas(get_object_side_effect=get_object):
                sampled_test1 = _make_test_artifact(tmp_path, "test1.csv")
                result1 = automl_data_loader.python_func(
                    file_key="data/file.csv",
                    bucket_name="bucket",
                    workspace_path=str(tmp_path / "ws1"),
                    label_column="y",
                    sampled_test_dataset=sampled_test1,
                    sampling_method="random",
                )
                sampled_test2 = _make_test_artifact(tmp_path, "test2.csv")
                result2 = automl_data_loader.python_func(
                    file_key="data/file.csv",
                    bucket_name="bucket",
                    workspace_path=str(tmp_path / "ws2"),
                    label_column="y",
                    sampled_test_dataset=sampled_test2,
                    sampling_method="random",
                )

            n1 = result1.sample_config["n_samples"]
            n2 = result2.sample_config["n_samples"]
            assert n1 == n2, "Same random_state should yield same sample size"
            assert n1 == 2, "Downsampling should have been triggered (2 rows * 0.5 GB/row = 1 GB)"
        finally:
            MockedDataFrame.BYTES_PER_ROW = original_bytes_per_row

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_component_random_sampling_multiple_chunks(self, tmp_path):
        """Test random sampling with CSV large enough to trigger multiple chunks (>10k rows)."""
        header = "col1,col2\n"
        rows = "\n".join(f"{i},{i * 2}" for i in range(15000))
        csv_content = header + rows
        body_stream = io.BytesIO(csv_content.encode("utf-8"))
        sampled_test = _make_test_artifact(tmp_path)

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}):
            result = automl_data_loader.python_func(
                file_key="data/large.csv",
                bucket_name="bucket",
                workspace_path=str(tmp_path),
                label_column="col2",
                sampled_test_dataset=sampled_test,
                sampling_method="random",
            )

            assert result.sample_config["n_samples"] == 15000
        assert (tmp_path / "datasets" / "models_selection_train_dataset.csv").exists()


class TestDataLoaderSplitLogic:
    """Tests for the train/test split logic integrated into the data loader."""

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_split_outputs_have_correct_paths(self, tmp_path):
        """Verify selection-train and extra-train are written to workspace/datasets/."""
        csv_content = "a,b,target\n1,2,X\n3,4,Y\n5,6,X\n7,8,Y\n9,10,X\n"
        body_stream = io.BytesIO(csv_content.encode("utf-8"))
        sampled_test = _make_test_artifact(tmp_path)

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}):
            result = automl_data_loader.python_func(
                file_key="data/file.csv",
                bucket_name="bucket",
                workspace_path=str(tmp_path),
                label_column="target",
                sampled_test_dataset=sampled_test,
            )

        assert "models_selection_train_dataset.csv" in result.models_selection_train_data_path
        assert "extra_train_dataset.csv" in result.extra_train_data_path
        assert result.models_selection_train_data_path.startswith(str(tmp_path))
        assert result.extra_train_data_path.startswith(str(tmp_path))

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_split_config_defaults(self, tmp_path):
        """Default split_config uses test_size=0.2, random_state=42, stratify=False for regression."""
        csv_content = "a,b,target\n1,2,10\n3,4,20\n5,6,30\n7,8,40\n9,10,50\n"
        body_stream = io.BytesIO(csv_content.encode("utf-8"))
        sampled_test = _make_test_artifact(tmp_path)

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}):
            result = automl_data_loader.python_func(
                file_key="data/file.csv",
                bucket_name="bucket",
                workspace_path=str(tmp_path),
                label_column="target",
                sampled_test_dataset=sampled_test,
                task_type="regression",
            )

        assert result.split_config["test_size"] == 0.2
        assert result.split_config["random_state"] == 42
        assert result.split_config["stratify"] is False

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_split_config_custom_values(self, tmp_path):
        """Custom split_config values are used and returned."""
        csv_content = "a,b,target\n1,2,10\n3,4,20\n5,6,30\n7,8,40\n9,10,50\n"
        body_stream = io.BytesIO(csv_content.encode("utf-8"))
        sampled_test = _make_test_artifact(tmp_path)

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}):
            result = automl_data_loader.python_func(
                file_key="data/file.csv",
                bucket_name="bucket",
                workspace_path=str(tmp_path),
                label_column="target",
                sampled_test_dataset=sampled_test,
                split_config={"test_size": 0.3, "random_state": 123},
            )

        assert result.split_config["test_size"] == 0.3
        assert result.split_config["random_state"] == 123

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_classification_stratify_default_true(self, tmp_path):
        """Binary/multiclass tasks default to stratify=True in split_config output."""
        csv_content = "a,b,target\n1,2,A\n3,4,B\n5,6,A\n7,8,B\n9,10,A\n"
        body_stream = io.BytesIO(csv_content.encode("utf-8"))
        sampled_test = _make_test_artifact(tmp_path)

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}):
            result = automl_data_loader.python_func(
                file_key="data/file.csv",
                bucket_name="bucket",
                workspace_path=str(tmp_path),
                label_column="target",
                sampled_test_dataset=sampled_test,
                task_type="binary",
            )

        assert result.split_config["stratify"] is True

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_classification_stratify_false_override(self, tmp_path):
        """Setting stratify=False in split_config disables stratification."""
        csv_content = "a,b,target\n1,2,A\n3,4,B\n5,6,A\n7,8,B\n9,10,A\n"
        body_stream = io.BytesIO(csv_content.encode("utf-8"))
        sampled_test = _make_test_artifact(tmp_path)

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}):
            result = automl_data_loader.python_func(
                file_key="data/file.csv",
                bucket_name="bucket",
                workspace_path=str(tmp_path),
                label_column="target",
                sampled_test_dataset=sampled_test,
                task_type="binary",
                split_config={"stratify": False},
            )

        assert result.split_config["stratify"] is False

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_sample_row_is_json_string(self, tmp_path):
        """sample_row output is a JSON string from the test set head(1)."""
        csv_content = "a,b,target\n1,2,X\n3,4,Y\n5,6,X\n7,8,Y\n9,10,X\n"
        body_stream = io.BytesIO(csv_content.encode("utf-8"))
        sampled_test = _make_test_artifact(tmp_path)

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}):
            result = automl_data_loader.python_func(
                file_key="data/file.csv",
                bucket_name="bucket",
                workspace_path=str(tmp_path),
                label_column="target",
                sampled_test_dataset=sampled_test,
            )

        import json

        parsed = json.loads(result.sample_row)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert isinstance(parsed[0], dict)

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_test_dataset_written_to_artifact(self, tmp_path):
        """Test dataset is written to the sampled_test_dataset artifact path."""
        csv_content = "a,b,target\n1,2,X\n3,4,Y\n5,6,X\n7,8,Y\n9,10,X\n"
        body_stream = io.BytesIO(csv_content.encode("utf-8"))
        sampled_test = _make_test_artifact(tmp_path)

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}):
            automl_data_loader.python_func(
                file_key="data/file.csv",
                bucket_name="bucket",
                workspace_path=str(tmp_path),
                label_column="target",
                sampled_test_dataset=sampled_test,
            )

        assert sampled_test.uri == "/artifacts/test.csv"
        header, rows = _read_csv_path(sampled_test.path)
        assert "target" in header
        assert len(rows) >= 1

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_all_return_fields_present(self, tmp_path):
        """Return value has all expected fields."""
        csv_content = "a,b,target\n1,2,X\n3,4,Y\n5,6,X\n7,8,Y\n9,10,X\n"
        body_stream = io.BytesIO(csv_content.encode("utf-8"))
        sampled_test = _make_test_artifact(tmp_path)

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}):
            result = automl_data_loader.python_func(
                file_key="data/file.csv",
                bucket_name="bucket",
                workspace_path=str(tmp_path),
                label_column="target",
                sampled_test_dataset=sampled_test,
            )

        assert hasattr(result, "sample_config")
        assert hasattr(result, "split_config")
        assert hasattr(result, "sample_row")
        assert hasattr(result, "models_selection_train_data_path")
        assert hasattr(result, "extra_train_data_path")

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_split_csv_files_have_label_column(self, tmp_path):
        """All split CSV outputs contain the label column."""
        csv_content = "a,b,target\n1,2,X\n3,4,Y\n5,6,X\n7,8,Y\n9,10,X\n"
        body_stream = io.BytesIO(csv_content.encode("utf-8"))
        sampled_test = _make_test_artifact(tmp_path)

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}):
            result = automl_data_loader.python_func(
                file_key="data/file.csv",
                bucket_name="bucket",
                workspace_path=str(tmp_path),
                label_column="target",
                sampled_test_dataset=sampled_test,
            )

        sel_header, _ = _read_csv_path(result.models_selection_train_data_path)
        extra_header, _ = _read_csv_path(result.extra_train_data_path)
        test_header, _ = _read_csv_path(sampled_test.path)
        assert "target" in sel_header
        assert "target" in extra_header
        assert "target" in test_header

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_invalid_task_type_raises(self, tmp_path):
        """Invalid task_type raises ValueError before any S3 access."""
        sampled_test = _make_test_artifact(tmp_path)

        with _mock_boto3_and_pandas() as mock_s3:
            with pytest.raises(ValueError, match=r"Invalid task_type"):
                automl_data_loader.python_func(
                    file_key="data/file.csv",
                    bucket_name="bucket",
                    workspace_path=str(tmp_path),
                    label_column="target",
                    sampled_test_dataset=sampled_test,
                    task_type="invalid",
                )

            mock_s3.get_object.assert_not_called()

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_invalid_sampling_method_raises(self, tmp_path):
        """Invalid sampling_method raises ValueError."""
        sampled_test = _make_test_artifact(tmp_path)

        with _mock_boto3_and_pandas():
            with pytest.raises(ValueError, match=r"Invalid sampling_method"):
                automl_data_loader.python_func(
                    file_key="data/file.csv",
                    bucket_name="bucket",
                    workspace_path=str(tmp_path),
                    label_column="target",
                    sampled_test_dataset=sampled_test,
                    sampling_method="invalid",
                )
