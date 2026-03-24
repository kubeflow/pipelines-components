"""Tests for the documents_discovery component."""

import sys
from unittest import mock

from ..component import documents_discovery

mocked_env_variables = {
    "AWS_ACCESS_KEY_ID": "test_key",
    "AWS_SECRET_ACCESS_KEY": "test_secret",
    "AWS_S3_ENDPOINT": "test_url",
    "AWS_DEFAULT_REGION": "us-east-1",
}


class _MockSSLError(Exception):
    """Stand-in for botocore.exceptions.SSLError used in unit tests."""

    pass


class TestDocumentsDiscoveryUnitTests:
    """Unit tests for component logic."""

    def test_component_function_exists(self):
        """Test that the component function is properly imported."""
        assert callable(documents_discovery)
        assert hasattr(documents_discovery, "python_func")

    def test_component_with_default_parameters(self):
        """Test component has expected interface (required args)."""
        import inspect

        sig = inspect.signature(documents_discovery.python_func)
        params = list(sig.parameters)
        assert "input_data_bucket_name" in params
        assert "input_data_path" in params

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_ssl_error_retries_with_verify_false(self, tmp_path):
        """SSLError on list_objects_v2 triggers a retry with verify=False."""
        mock_boto3 = mock.MagicMock()
        mock_s3_ok = mock.MagicMock()
        mock_s3_fail = mock.MagicMock()

        mock_s3_fail.list_objects_v2.side_effect = _MockSSLError("SSL validation failed")
        mock_s3_ok.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "docs/file1.pdf", "Size": 1000},
            ]
        }

        call_count = 0

        def fake_client(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_s3_fail
            return mock_s3_ok

        mock_boto3.client.side_effect = fake_client

        mock_botocore = mock.MagicMock()
        mock_botocore_exceptions = mock.MagicMock()
        mock_botocore_exceptions.SSLError = _MockSSLError
        mock_botocore.exceptions = mock_botocore_exceptions

        discovered = mock.MagicMock()
        discovered.path = str(tmp_path / "output")

        with mock.patch.dict(
            sys.modules,
            {
                "boto3": mock_boto3,
                "botocore": mock_botocore,
                "botocore.exceptions": mock_botocore_exceptions,
            },
        ):
            documents_discovery.python_func(
                input_data_bucket_name="my-bucket",
                input_data_path="docs/",
                discovered_documents=discovered,
            )

        assert call_count == 2
        second_call_kwargs = mock_boto3.client.call_args_list[1][1]
        assert second_call_kwargs["verify"] is False
