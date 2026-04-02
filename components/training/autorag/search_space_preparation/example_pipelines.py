"""Example pipelines demonstrating usage of search_space_preparation."""

from kfp import dsl
from kfp_components.components.training.autorag.search_space_preparation import search_space_preparation


@dsl.pipeline(name="search-space-preparation-example")
def example_pipeline(
    metric: str = "faithfulness",
):
    """Example pipeline using search_space_preparation.

    Args:
        metric: Evaluation metric name.
    """
    test_data = dsl.importer(
        artifact_uri="gs://placeholder/test_data",
        artifact_class=dsl.Artifact,
    )
    extracted_text = dsl.importer(
        artifact_uri="gs://placeholder/extracted_text",
        artifact_class=dsl.Artifact,
    )
    search_space_preparation(
        test_data=test_data.output,
        extracted_text=extracted_text.output,
        metric=metric,
    )
