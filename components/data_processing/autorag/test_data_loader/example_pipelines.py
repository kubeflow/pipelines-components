"""Example pipelines demonstrating usage of test_data_loader."""

from kfp import dsl
from kfp_components.components.data_processing.autorag.test_data_loader import test_data_loader


@dsl.pipeline(name="test-data-loader-example")
def example_pipeline(
    test_data_bucket_name: str = "my-bucket",
    test_data_path: str = "test_data/questions.json",
):
    """Example pipeline using test_data_loader.

    Args:
        test_data_bucket_name: S3 bucket containing test data.
        test_data_path: Path to the test data file within the bucket.
    """
    test_data_loader(
        test_data_bucket_name=test_data_bucket_name,
        test_data_path=test_data_path,
    )
