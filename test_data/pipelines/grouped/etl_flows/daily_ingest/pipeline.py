"""Daily ingest pipeline for testing subcategory support."""

from kfp import dsl


@dsl.pipeline
def daily_ingest(source_path: str, batch_size: int = 100):
    """Runs a daily data ingestion workflow.

    This pipeline orchestrates the daily ingestion of data from
    an external source into the data lake.

    Args:
        source_path: Path to the data source.
        batch_size: Number of records per batch.
    """
    pass
