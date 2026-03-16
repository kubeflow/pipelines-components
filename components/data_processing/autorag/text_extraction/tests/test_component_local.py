"""Local runner tests for the text_extraction component."""

import pytest

from ..component import text_extraction


class TestTextExtractionLocalRunner:
    """Test component with LocalRunner (subprocess execution)."""

    @pytest.mark.skip(reason="Requires input artifact and S3; run E2E in pipeline")
    def test_local_execution(self, setup_and_teardown_subprocess_runner):  # noqa: F811
        """Test component execution with LocalRunner."""
        result = text_extraction(
            documents_descriptor=...,
            extracted_text=...,
        )
        assert result is not None
