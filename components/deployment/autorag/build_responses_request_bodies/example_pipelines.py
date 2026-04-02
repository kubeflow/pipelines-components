"""Example pipelines demonstrating usage of prepare_responses_api_requests."""

from kfp import dsl
from kfp_components.components.deployment.autorag.build_responses_request_bodies import (
    prepare_responses_api_requests,
)


@dsl.pipeline(name="build-responses-request-bodies-example")
def example_pipeline():
    """Example pipeline using prepare_responses_api_requests."""
    rag_patterns = dsl.importer(
        artifact_uri="gs://placeholder/rag_patterns",
        artifact_class=dsl.Artifact,
    )
    prepare_responses_api_requests(rag_patterns=rag_patterns.output)
