"""Local runner tests for the documents_lite_rag_optimization_pipeline pipeline."""

import pytest

from ..pipeline import documents_lite_rag_optimization_pipeline


class TestDocumentsRagOptimizationPipelineLocalRunner:
    """Test pipeline with LocalRunner (subprocess execution)."""

    @pytest.mark.skip(reason="Pipeline requires secrets and model URLs; run E2E in cluster")
    def test_local_execution(self, setup_and_teardown_subprocess_runner):  # noqa: F811
        """Test pipeline execution with LocalRunner."""
        result = documents_lite_rag_optimization_pipeline(
            test_data_secret_name="s",
            test_data_bucket_name="b",
            test_data_key="k",
            input_data_secret_name="s",
            input_data_bucket_name="b",
            input_data_key="k",
            chat_model_url="http://localhost",
            chat_model_token="t",
            embedding_model_url="http://localhost",
            embedding_model_token="t",
        )
        assert result is not None
