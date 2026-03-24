"""Tests for the text_extraction component."""

import json
import sys
from unittest import mock

from ..component import text_extraction

mocked_env_variables = {
    "AWS_ACCESS_KEY_ID": "test_key",
    "AWS_SECRET_ACCESS_KEY": "test_secret",
    "AWS_S3_ENDPOINT": "test_url",
    "AWS_DEFAULT_REGION": "us-east-1",
}


class _MockSSLError(Exception):
    """Stand-in for botocore.exceptions.SSLError used in unit tests."""

    pass


class TestTextExtractionUnitTests:
    """Unit tests for component logic."""

    def test_component_function_exists(self):
        """Test that the component function is properly imported."""
        assert callable(text_extraction)
        assert hasattr(text_extraction, "python_func")

    def test_component_with_default_parameters(self):
        """Test component has expected interface (required args)."""
        import inspect

        sig = inspect.signature(text_extraction.python_func)
        params = list(sig.parameters)
        assert "documents_descriptor" in params
        assert "extracted_text" in params

    @mock.patch.dict("os.environ", mocked_env_variables)
    def test_ssl_error_retries_with_verify_false(self, tmp_path):
        """SSLError on download_file triggers a retry with verify=False."""
        # Write a descriptor file
        descriptor_dir = tmp_path / "descriptor"
        descriptor_dir.mkdir()
        descriptor = {
            "bucket": "my-bucket",
            "prefix": "docs/",
            "documents": [{"key": "docs/file1.pdf", "size_bytes": 1000}],
            "total_size_bytes": 1000,
            "count": 1,
        }
        descriptor_path = descriptor_dir / "documents_descriptor.json"
        descriptor_path.write_text(json.dumps(descriptor))

        mock_boto3 = mock.MagicMock()
        mock_s3_fail = mock.MagicMock()
        mock_s3_ok = mock.MagicMock()

        mock_s3_fail.download_file.side_effect = _MockSSLError("SSL validation failed")
        mock_s3_ok.download_file.return_value = None

        session_call_count = 0

        def fake_session_client(*args, **kwargs):
            nonlocal session_call_count
            session_call_count += 1
            if session_call_count == 1:
                return mock_s3_fail
            return mock_s3_ok

        mock_session = mock.MagicMock()
        mock_session.client.side_effect = fake_session_client
        mock_boto3.session.Session.return_value = mock_session

        mock_botocore = mock.MagicMock()
        mock_botocore_exceptions = mock.MagicMock()
        mock_botocore_exceptions.SSLError = _MockSSLError
        mock_botocore.exceptions = mock_botocore_exceptions

        # Mock docling modules
        mock_docling = mock.MagicMock()
        mock_docling_datamodel = mock.MagicMock()
        mock_docling_accel = mock.MagicMock()
        mock_docling_base = mock.MagicMock()
        mock_docling_pipeline = mock.MagicMock()
        mock_docling_converter = mock.MagicMock()

        documents_descriptor_artifact = mock.MagicMock()
        documents_descriptor_artifact.path = str(descriptor_dir)

        extracted_text_artifact = mock.MagicMock()
        extracted_text_artifact.path = str(tmp_path / "output")

        with mock.patch.dict(
            sys.modules,
            {
                "boto3": mock_boto3,
                "botocore": mock_botocore,
                "botocore.exceptions": mock_botocore_exceptions,
                "docling": mock_docling,
                "docling.datamodel": mock_docling_datamodel,
                "docling.datamodel.accelerator_options": mock_docling_accel,
                "docling.datamodel.base_models": mock_docling_base,
                "docling.datamodel.pipeline_options": mock_docling_pipeline,
                "docling.document_converter": mock_docling_converter,
            },
        ):
            text_extraction.python_func(
                documents_descriptor=documents_descriptor_artifact,
                extracted_text=extracted_text_artifact,
            )

        assert session_call_count == 2
        second_call_kwargs = mock_session.client.call_args_list[1][1]
        assert second_call_kwargs["verify"] is False
