"""Example usage of the documents_lite_rag_optimization_pipeline."""

from kfp_components.pipelines.training.autorag.documents_lite_rag_optimization_pipeline import (
    documents_lite_rag_optimization_pipeline,
)


def example_minimal_usage():
    """Minimal example with only required parameters."""
    return documents_lite_rag_optimization_pipeline(
        test_data_secret_name="s3-test-data-secret",
        test_data_bucket_name="autorag-benchmarks",
        test_data_key="test_data.json",
        input_data_secret_name="s3-input-secret",
        input_data_bucket_name="my-documents-bucket",
        input_data_key="rh_documents/",
        chat_model_url="https://api.openai.com/v1",
        chat_model_token="your-chat-model-token",
        embedding_model_url="https://api.openai.com/v1",
        embedding_model_token="your-embedding-model-token",
    )


def example_full_usage():
    """Full example with optional parameters."""
    return documents_lite_rag_optimization_pipeline(
        test_data_secret_name="s3-test-data-secret",
        test_data_bucket_name="autorag-benchmarks",
        test_data_key="my-folder/test_data.json",
        input_data_secret_name="s3-input-secret",
        input_data_bucket_name="my-documents-bucket",
        input_data_key="rh_documents/",
        chat_model_url="https://api.openai.com/v1",
        chat_model_token="your-chat-model-token",
        embedding_model_url="https://api.openai.com/v1",
        embedding_model_token="your-embedding-model-token",
        optimization_metric="answer_correctness",
    )
