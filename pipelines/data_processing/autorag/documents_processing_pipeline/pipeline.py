from typing import Optional

from kfp import dsl
from kfp.kubernetes import use_secret_as_env
from kfp_components.components.data_processing.autorag.documents_discovery.component import documents_discovery
from kfp_components.components.data_processing.autorag.test_data_loader.component import test_data_loader
from kfp_components.components.data_processing.autorag.text_extraction.component import text_extraction


@dsl.pipeline(
    name="AutoRAG Data Processing Pipeline", description="Pipeline to load test data and documents for AutoRAG."
)
def data_processing_pipeline(
    test_data_secret_name: str,
    input_data_secret_name: str,
    input_data_bucket_name: str,
    input_data_key: str,
    sampling_enabled: bool = False,
    sampling_max_size: Optional[float] = None,
    test_data_bucket_name: Optional[str] = None,
    test_data_key: Optional[str] = None,
):
    """Defines a pipeline to load and sample input data for AutoRAG.

    Args:
        test_data_secret_name: Name of the secret containing environment variables with S3 credentials
            used to access the test data.

        input_data_secret_name: Name of the secret containing environment variables with S3 credentials
            used to access the input data.

        test_data_bucket_name: S3 bucket that contains the test data file.

        test_data_key: S3 object key to the JSON test data file.

        input_data_bucket_name: Name of the S3 bucket containing input data.

        input_data_key: Path to folder with input documents within bucket.

        sampling_enabled: Whether to enable sampling or not.

        sampling_max_size: Maximum size of sampled documents (in gigabytes).
    """
    test_data_loader_task = test_data_loader(
        test_data_bucket_name=test_data_bucket_name,
        test_data_path=test_data_key,
    )

    documents_discovery_task = documents_discovery(
        input_data_bucket_name=input_data_bucket_name,
        input_data_path=input_data_key,
        test_data=test_data_loader_task.outputs["test_data"],
        sampling_enabled=sampling_enabled,
        sampling_max_size=sampling_max_size,
    )

    documents_discovery_task.set_caching_options(enable_caching=False)
    test_data_loader_task.set_caching_options(enable_caching=False)

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


if __name__ == "__main__":
    import pathlib

    from kfp.compiler import Compiler

    output_path = pathlib.Path(__file__).with_name("data_processing_pipeline.yaml")
    Compiler().compile(pipeline_func=data_processing_pipeline, package_path=str(output_path))
    print(f"Pipeline compiled to {output_path}")
