"""Example pipelines demonstrating usage of leaderboard_evaluation."""

from kfp import dsl
from kfp_components.components.training.autorag.leaderboard_evaluation import leaderboard_evaluation


@dsl.pipeline(name="autorag-leaderboard-evaluation-example")
def example_pipeline(
    optimization_metric: str = "faithfulness",
):
    """Example pipeline using leaderboard_evaluation.

    Args:
        optimization_metric: Metric to optimize for.
    """
    rag_patterns = dsl.importer(
        artifact_uri="gs://placeholder/rag_patterns",
        artifact_class=dsl.Artifact,
    )
    leaderboard_evaluation(
        rag_patterns=rag_patterns.output,
        optimization_metric=optimization_metric,
    )
