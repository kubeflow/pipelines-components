from kfp import dsl
from kfp.kubernetes import use_secret_as_env
from kfp_components.components.data_processing.autorag.documents_discovery import (
    documents_discovery,
)
from kfp_components.components.data_processing.autorag.test_data_loader import (
    test_data_loader,
)
from kfp_components.components.data_processing.autorag.text_extraction import (
    text_extraction,
)
from kfp_components.components.training.autorag.leaderboard_evaluation import (
    leaderboard_evaluation,
)
from kfp_components.components.training.autorag.rag_templates_optimization.component import (
    rag_templates_optimization,
)
from kfp_components.components.training.autorag.search_space_preparation.component import (
    search_space_preparation,
)

SUPPORTED_OPTIMIZATION_METRICS = frozenset({"faithfulness", "answer_correctness", "context_correctness"})


@dsl.pipeline(
    name="documents-lite-rag-optimization-pipeline",
    description=(
        "Automated system for building and optimizing Retrieval-Augmented Generation (RAG) applications "
        "(lite version). The lite version does not use llama-stack API for inference and vector database "
        "operations."
    ),
)
def documents_lite_rag_optimization_pipeline(
    test_data_secret_name: str,
    test_data_bucket_name: str,
    test_data_key: str,
    input_data_secret_name: str,
    input_data_bucket_name: str,
    input_data_key: str,
    chat_model_url: str,
    chat_model_token: str,
    embedding_model_url: str,
    embedding_model_token: str,
    optimization_metric: str = "faithfulness",
    optimization_max_rag_patterns: int = 8,
):
    """Automated system for building and optimizing Retrieval-Augmented Generation (RAG) applications.

    The Documents Lite RAG Optimization Pipeline is an automated system for building and optimizing
    Retrieval-Augmented Generation (RAG) applications within Red Hat OpenShift AI. It leverages
    Kubeflow Pipelines to orchestrate the optimization workflow, using the ai4rag optimization
    engine to systematically explore RAG configurations and identify the best performing parameter
    settings based on an upfront-specified quality metric.

    The system integrates with OpenAI API for inference and in-memory ChromaDB vector database operations,
    producing optimized RAG patterns as artifacts that can be deployed and used for production
    RAG applications.

    Args:
        test_data_secret_name: Name of the Kubernetes secret holding S3-compatible credentials for
            test data access. The following environment variables are required:
            AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_ENDPOINT, AWS_DEFAULT_REGION.
        test_data_bucket_name: S3 (or compatible) bucket name for the test data file.
        test_data_key: Object key (path) of the test data JSON file in the test data bucket.
        input_data_secret_name: Name of the Kubernetes secret holding S3-compatible credentials
            for input document data access. The following environment variables are required:
            AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_ENDPOINT, AWS_DEFAULT_REGION.
        input_data_bucket_name: S3 (or compatible) bucket name for the input documents.
        input_data_key: Object key (path) of the input documents in the input data bucket.
        chat_model_url: Inference endpoint URL for the chat/generation model (OpenAI-compatible endpoint).
        chat_model_token: API token or key for authenticating with the chat model endpoint.
        embedding_model_url: Inference endpoint URL for the embedding model.
        embedding_model_token: API token or key for authenticating with the embedding model endpoint.
        optimization_metric: Quality metric used to optimize RAG patterns. Supported values:
            "faithfulness", "answer_correctness", "context_correctness". Defaults to "faithfulness".
        optimization_max_rag_patterns: Maximum number of RAG patterns to generate. Passed to ai4rag
            (max_number_of_rag_patterns). Defaults to 8.
    """
    test_data_loader_task = test_data_loader(
        test_data_bucket_name=test_data_bucket_name,
        test_data_path=test_data_key,
    )

    documents_discovery_task = documents_discovery(
        input_data_bucket_name=input_data_bucket_name,
        input_data_path=input_data_key,
        test_data=test_data_loader_task.outputs["test_data"],
    )

    text_extraction_task = text_extraction(
        documents_descriptor=documents_discovery_task.outputs["discovered_documents"],
    )

    for task, secret_name in zip(
        [test_data_loader_task, documents_discovery_task, text_extraction_task],
        [test_data_secret_name, input_data_secret_name, input_data_secret_name],
    ):
        use_secret_as_env(
            task,
            secret_name=secret_name,
            secret_key_to_env={
                "AWS_ACCESS_KEY_ID": "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY": "AWS_SECRET_ACCESS_KEY",
                "AWS_S3_ENDPOINT": "AWS_S3_ENDPOINT",
                "AWS_DEFAULT_REGION": "AWS_DEFAULT_REGION",
            },
        )

    mps_task = search_space_preparation(
        test_data=test_data_loader_task.outputs["test_data"],
        extracted_text=text_extraction_task.outputs["extracted_text"],
        chat_model_url=chat_model_url,
        chat_model_token=chat_model_token,
        embedding_model_url=embedding_model_url,
        embedding_model_token=embedding_model_token,
    )

    hpo_task = rag_templates_optimization(
        extracted_text=text_extraction_task.outputs["extracted_text"],
        test_data=test_data_loader_task.outputs["test_data"],
        search_space_prep_report=mps_task.outputs["search_space_prep_report"],
        chat_model_url=chat_model_url,
        chat_model_token=chat_model_token,
        embedding_model_url=embedding_model_url,
        embedding_model_token=embedding_model_token,
        optimization_settings={
            "metric": optimization_metric,
            "max_number_of_rag_patterns": optimization_max_rag_patterns,
        },
        test_data_key=test_data_key,
        input_data_key=input_data_key,
    )

    leaderboard_evaluation(
        rag_patterns=hpo_task.outputs["rag_patterns"],
        optimization_metric=optimization_metric,
    )


if __name__ == "__main__":
    from kfp.compiler import Compiler

    Compiler().compile(
        documents_lite_rag_optimization_pipeline,
        package_path=__file__.replace(".py", "_pipeline.yaml"),
    )
