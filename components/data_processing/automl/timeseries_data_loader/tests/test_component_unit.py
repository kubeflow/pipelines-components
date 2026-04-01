"""Unit tests for the timeseries_data_loader component.

boto3 and pandas are mocked via ``sys.modules`` so those packages are not required.
Output CSVs are asserted with the stdlib :mod:`csv` module.
"""

import csv
import io
import json
import os
import sys
from contextlib import contextmanager
from unittest import mock

import pytest

from ..component import timeseries_data_loader
from .mocked_pandas import make_mocked_pandas_module

mocked_env_variables = {
    "AWS_ACCESS_KEY_ID": "test_key",
    "AWS_SECRET_ACCESS_KEY": "test_secret",
    "AWS_S3_ENDPOINT": "https://s3.example.local",
    "AWS_DEFAULT_REGION": "us-east-1",
}


class _MockSSLError(Exception):
    """Stand-in for botocore.exceptions.SSLError used in unit tests."""

    pass


@contextmanager
def _mock_boto3_module(get_object_return=None, get_object_side_effect=None):
    """Inject fake boto3/botocore so tests don't require real packages for SSLError handling."""
    mock_boto3 = mock.MagicMock()
    mock_s3 = mock.MagicMock()
    if get_object_side_effect is not None:
        mock_s3.get_object.side_effect = get_object_side_effect
    else:
        mock_s3.get_object.return_value = get_object_return or {"Body": io.BytesIO(b"")}
    mock_boto3.client.return_value = mock_s3

    mock_botocore = mock.MagicMock()
    mock_botocore_exceptions = mock.MagicMock()
    mock_botocore_exceptions.SSLError = _MockSSLError
    mock_botocore.exceptions = mock_botocore_exceptions

    with mock.patch.dict(
        sys.modules,
        {
            "boto3": mock_boto3,
            "botocore": mock_botocore,
            "botocore.exceptions": mock_botocore_exceptions,
        },
    ):
        yield mock_s3


@contextmanager
def _mock_boto3_and_pandas(get_object_return=None, get_object_side_effect=None):
    """Inject mocked boto3 and pandas so the component runs without those dependencies."""
    mocked_pandas = make_mocked_pandas_module()
    with _mock_boto3_module(
        get_object_return=get_object_return, get_object_side_effect=get_object_side_effect
    ) as mock_s3:
        with mock.patch.dict(sys.modules, {"pandas": mocked_pandas}):
            yield mock_s3


def _make_test_artifact(tmp_path, name="sampled_test.csv"):
    """Create a simple artifact-like object for sampled_test_dataset."""
    art = mock.MagicMock()
    art.path = str(tmp_path / name)
    return art


def _read_csv_rows(path):
    """Read CSV rows as list[dict] with stdlib csv module."""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _timeseries_csv(n_rows=10):
    """Build deterministic timeseries CSV content with required columns."""
    lines = ["item_id,timestamp,target,feature"]
    for i in range(n_rows):
        lines.append(f"series-1,2024-01-{i + 1:02d},{i},{i * 10}")
    return "\n".join(lines) + "\n"


class TestTimeseriesDataLoaderUnitTests:
    """Unit tests for timeseries_data_loader behavior."""

    def test_component_function_exists(self):
        """Component exposes a KFP python_func entrypoint."""
        assert callable(timeseries_data_loader)
        assert hasattr(timeseries_data_loader, "python_func")

    @mock.patch.dict(os.environ, mocked_env_variables, clear=True)
    def test_component_default_split_outputs(self, tmp_path):
        """Default split creates expected files with chronological partitioning."""
        body_stream = io.BytesIO(_timeseries_csv(10).encode("utf-8"))
        sampled_test = _make_test_artifact(tmp_path)

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}) as mock_s3:
            result = timeseries_data_loader.python_func(
                file_key="timeseries/train.csv",
                bucket_name="my-bucket",
                workspace_path=str(tmp_path),
                target="target",
                id_column="item_id",
                timestamp_column="timestamp",
                sampled_test_dataset=sampled_test,
            )

            mock_s3.get_object.assert_called_once_with(Bucket="my-bucket", Key="timeseries/train.csv")

        selection_rows = _read_csv_rows(result.models_selection_train_data_path)
        extra_rows = _read_csv_rows(result.extra_train_data_path)
        test_rows = _read_csv_rows(sampled_test.path)

        assert len(selection_rows) == 2
        assert len(extra_rows) == 6
        assert len(test_rows) == 2
        assert selection_rows[0]["target"] == "0"
        assert extra_rows[0]["target"] == "2"
        assert test_rows[0]["target"] == "8"

        assert result.sample_config["sampling_method"] == "first_n_rows"
        assert result.sample_config["total_rows_loaded"] == 10
        assert result.split_config["test_size"] == 0.2
        assert result.split_config["selection_train_size"] == 0.3

    @mock.patch.dict(os.environ, mocked_env_variables, clear=True)
    def test_per_series_split_each_id_gets_holdout(self, tmp_path):
        """Panel data: every series with >=2 rows contributes late timestamps to test, not only tail IDs."""
        lines = ["item_id,timestamp,target,feature"]
        for sid, letter in enumerate(["A", "B"]):
            base = sid * 10
            for i in range(10):
                lines.append(f"{letter},2024-01-{i + 1:02d},{base + i},{i}")
        body_stream = io.BytesIO(("\n".join(lines) + "\n").encode("utf-8"))
        sampled_test = _make_test_artifact(tmp_path)

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}):
            timeseries_data_loader.python_func(
                file_key="ts.csv",
                bucket_name="b",
                workspace_path=str(tmp_path),
                target="target",
                id_column="item_id",
                timestamp_column="timestamp",
                sampled_test_dataset=sampled_test,
            )

        test_rows = _read_csv_rows(sampled_test.path)
        by_id = {letter: [r["target"] for r in test_rows if r["item_id"] == letter] for letter in ("A", "B")}
        assert sorted(by_id["A"], key=int) == ["8", "9"]
        assert sorted(by_id["B"], key=int) == ["18", "19"]
        assert len(test_rows) == 4

    @mock.patch.dict(os.environ, mocked_env_variables, clear=True)
    def test_component_custom_selection_train_size(self, tmp_path):
        """Custom selection_train_size is reflected in split sizes and output metadata."""
        body_stream = io.BytesIO(_timeseries_csv(10).encode("utf-8"))
        sampled_test = _make_test_artifact(tmp_path)

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}):
            result = timeseries_data_loader.python_func(
                file_key="timeseries/train.csv",
                bucket_name="my-bucket",
                workspace_path=str(tmp_path),
                target="target",
                id_column="item_id",
                timestamp_column="timestamp",
                sampled_test_dataset=sampled_test,
                selection_train_size=0.5,
            )

        selection_rows = _read_csv_rows(result.models_selection_train_data_path)
        extra_rows = _read_csv_rows(result.extra_train_data_path)

        assert len(selection_rows) == 4
        assert len(extra_rows) == 4
        assert result.split_config["selection_train_size"] == 0.5

    @mock.patch.dict(os.environ, mocked_env_variables, clear=True)
    def test_sample_rows_json_matches_test_tail(self, tmp_path):
        """sample_rows returns JSON records from test split tail (up to 5 rows)."""
        body_stream = io.BytesIO(_timeseries_csv(30).encode("utf-8"))
        sampled_test = _make_test_artifact(tmp_path)

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}):
            result = timeseries_data_loader.python_func(
                file_key="timeseries/train.csv",
                bucket_name="my-bucket",
                workspace_path=str(tmp_path),
                target="target",
                id_column="item_id",
                timestamp_column="timestamp",
                sampled_test_dataset=sampled_test,
            )

        parsed = json.loads(result.sample_rows)
        assert isinstance(parsed, list)
        assert len(parsed) == 5
        assert parsed[-1]["target"] == "29"

    @mock.patch.dict(os.environ, mocked_env_variables, clear=True)
    def test_no_data_rows_raises(self, tmp_path):
        """Header-only CSV yields zero rows; fail before split with a clear error."""
        body_stream = io.BytesIO(b"item_id,timestamp,target,feature\n")
        sampled_test = _make_test_artifact(tmp_path)
        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}):
            with pytest.raises(ValueError, match="loaded dataset has no data rows"):
                timeseries_data_loader.python_func(
                    file_key="timeseries/train.csv",
                    bucket_name="my-bucket",
                    workspace_path=str(tmp_path),
                    target="target",
                    id_column="item_id",
                    timestamp_column="timestamp",
                    sampled_test_dataset=sampled_test,
                )

    @mock.patch.dict(os.environ, mocked_env_variables, clear=True)
    def test_missing_required_columns_raises(self, tmp_path):
        """Missing target/id/timestamp columns causes ValueError."""
        csv_content = "item_id,timestamp,feature\nseries-1,2024-01-01,10\n"
        body_stream = io.BytesIO(csv_content.encode("utf-8"))
        sampled_test = _make_test_artifact(tmp_path)

        with _mock_boto3_and_pandas(get_object_return={"Body": body_stream}):
            with pytest.raises(ValueError, match="Missing required columns in dataset"):
                timeseries_data_loader.python_func(
                    file_key="timeseries/train.csv",
                    bucket_name="my-bucket",
                    workspace_path=str(tmp_path),
                    target="target",
                    id_column="item_id",
                    timestamp_column="timestamp",
                    sampled_test_dataset=sampled_test,
                )

    @mock.patch.dict(os.environ, {"AWS_ACCESS_KEY_ID": "test_key"}, clear=True)
    def test_partial_credentials_raises(self, tmp_path):
        """Setting only one credential variable raises a configuration error."""
        sampled_test = _make_test_artifact(tmp_path)
        with _mock_boto3_and_pandas():
            with pytest.raises(ValueError, match="S3 credentials misconfigured"):
                timeseries_data_loader.python_func(
                    file_key="timeseries/train.csv",
                    bucket_name="my-bucket",
                    workspace_path=str(tmp_path),
                    target="target",
                    id_column="item_id",
                    timestamp_column="timestamp",
                    sampled_test_dataset=sampled_test,
                )

    @mock.patch.dict(os.environ, {}, clear=True)
    def test_missing_credentials_raises(self, tmp_path):
        """No AWS credentials configured raises an explicit error."""
        sampled_test = _make_test_artifact(tmp_path)
        with _mock_boto3_and_pandas():
            with pytest.raises(ValueError, match="S3 credentials missing"):
                timeseries_data_loader.python_func(
                    file_key="timeseries/train.csv",
                    bucket_name="my-bucket",
                    workspace_path=str(tmp_path),
                    target="target",
                    id_column="item_id",
                    timestamp_column="timestamp",
                    sampled_test_dataset=sampled_test,
                )

    @mock.patch.dict(os.environ, mocked_env_variables, clear=True)
    def test_invalid_selection_train_size(self, tmp_path):
        """Test that invalid selection_train_size raises ValueError."""
        sampled_test = _make_test_artifact(tmp_path)
        with _mock_boto3_and_pandas():
            with pytest.raises(ValueError, match="must be in a range 0 to 1"):
                timeseries_data_loader.python_func(
                    file_key="timeseries/train.csv",
                    bucket_name="my-bucket",
                    workspace_path=str(tmp_path),
                    target="target",
                    id_column="item_id",
                    timestamp_column="timestamp",
                    sampled_test_dataset=sampled_test,
                    selection_train_size=1.5,
                )

    @mock.patch.dict(os.environ, mocked_env_variables, clear=True)
    def test_invalid_selection_train_size_at_upper_bound(self, tmp_path):
        """selection_train_size == 1 is outside (0, 1)."""
        sampled_test = _make_test_artifact(tmp_path)
        with _mock_boto3_and_pandas():
            with pytest.raises(ValueError, match="must be in a range 0 to 1"):
                timeseries_data_loader.python_func(
                    file_key="timeseries/train.csv",
                    bucket_name="my-bucket",
                    workspace_path=str(tmp_path),
                    target="target",
                    id_column="item_id",
                    timestamp_column="timestamp",
                    sampled_test_dataset=sampled_test,
                    selection_train_size=1.0,
                )

    @mock.patch.dict(os.environ, mocked_env_variables, clear=True)
    def test_invalid_selection_train_size_non_numeric(self, tmp_path):
        """selection_train_size must be int or float."""
        sampled_test = _make_test_artifact(tmp_path)
        with _mock_boto3_and_pandas():
            with pytest.raises(TypeError, match=r"not supported between instances of 'str' and 'int'"):
                timeseries_data_loader.python_func(
                    file_key="timeseries/train.csv",
                    bucket_name="my-bucket",
                    workspace_path=str(tmp_path),
                    target="target",
                    id_column="item_id",
                    timestamp_column="timestamp",
                    sampled_test_dataset=sampled_test,
                    selection_train_size="0.3",
                )

    @mock.patch.dict(os.environ, mocked_env_variables, clear=True)
    def test_invalid_file_key(self, tmp_path):
        """Test that invalid file_key format raises ValueError."""
        sampled_test = _make_test_artifact(tmp_path)
        with _mock_boto3_and_pandas():
            with pytest.raises(ValueError, match="valid S3 object key"):
                timeseries_data_loader.python_func(
                    file_key="/invalid/path/",
                    bucket_name="my-bucket",
                    workspace_path=str(tmp_path),
                    target="target",
                    id_column="item_id",
                    timestamp_column="timestamp",
                    sampled_test_dataset=sampled_test,
                )

    @mock.patch.dict(os.environ, mocked_env_variables, clear=True)
    def test_invalid_file_key_double_slash(self, tmp_path):
        """file_key must not contain '//'."""
        sampled_test = _make_test_artifact(tmp_path)
        with _mock_boto3_and_pandas():
            with pytest.raises(ValueError, match="valid S3 object key"):
                timeseries_data_loader.python_func(
                    file_key="timeseries//train.csv",
                    bucket_name="my-bucket",
                    workspace_path=str(tmp_path),
                    target="target",
                    id_column="item_id",
                    timestamp_column="timestamp",
                    sampled_test_dataset=sampled_test,
                )

    @mock.patch.dict(os.environ, mocked_env_variables, clear=True)
    def test_empty_string_inputs_raise_type_error(self, tmp_path):
        """Required string parameters must be non-empty."""
        sampled_test = _make_test_artifact(tmp_path)
        with _mock_boto3_and_pandas():
            with pytest.raises(ValueError, match="bucket_name must be a non-empty string"):
                timeseries_data_loader.python_func(
                    file_key="timeseries/train.csv",
                    bucket_name="   ",
                    workspace_path=str(tmp_path),
                    target="target",
                    id_column="item_id",
                    timestamp_column="timestamp",
                    sampled_test_dataset=sampled_test,
                )

    @mock.patch.dict(os.environ, mocked_env_variables, clear=True)
    def test_ssl_error_retries_with_verify_false(self, tmp_path):
        """SSLError on get_object triggers a retry with verify=False."""
        csv_content = _timeseries_csv(10)
        call_count = 0

        def get_object_side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise _MockSSLError("SSL validation failed")
            return {"Body": io.BytesIO(csv_content.encode("utf-8"))}

        sampled_test = _make_test_artifact(tmp_path)

        with _mock_boto3_and_pandas(get_object_side_effect=get_object_side_effect) as mock_s3:
            import boto3 as mocked_boto3

            result = timeseries_data_loader.python_func(
                file_key="timeseries/train.csv",
                bucket_name="my-bucket",
                workspace_path=str(tmp_path),
                target="target",
                id_column="item_id",
                timestamp_column="timestamp",
                sampled_test_dataset=sampled_test,
            )

        assert result.sample_config["total_rows_loaded"] == 10
        assert mock_s3.get_object.call_count == 2

        client_calls = mocked_boto3.client.call_args_list
        assert len(client_calls) == 2
        assert client_calls[0][1].get("verify", True) is True
        assert client_calls[1][1]["verify"] is False
