from typing import NamedTuple, Optional

from kfp import dsl


@dsl.component(
    base_image="registry.redhat.io/rhoai/odh-pipeline-runtime-datascience-cpu-py312-rhel9@sha256:f9844dc150592a9f196283b3645dda92bd80dfdb3d467fa8725b10267ea5bdbc",  # noqa: E501
)
def automl_data_loader(
    file_key: str,
    bucket_name: str,
    full_dataset: dsl.Output[dsl.Dataset],
    sampling_method: Optional[str] = None,
    label_column: Optional[str] = None,
    task_type: str = "regression",
) -> NamedTuple("outputs", sample_config=dict):
    """Automl Data Loader component.

    Loads tabular (CSV) data from S3 in batches, sampling up to 1GB of data.
    The component reads data in chunks to efficiently handle large files without
    loading the entire dataset into memory at once.

    Args:
        file_key: S3 object key of the CSV file.
        bucket_name: S3 bucket name containing the file.
        label_column: Column name for labels/target (used for stratified sampling).
        full_dataset: Output dataset artifact for the sampled data.
        sampling_method: "first_n_rows", "stratified", or "random"; if None, derived from task_type.
        task_type: "binary", "multiclass", or "regression" (default); used when sampling_method is None.

    Returns:
        NamedTuple: Contains a sample configuration dictionary.
    """
    import io
    import logging
    import os

    import boto3
    import pandas as pd

    logger = logging.getLogger(__name__)

    MAX_SIZE_BYTES = 1024 * 1024 * 1024  # 1GB limit in bytes
    PANDAS_CHUNK_SIZE = 10000  # Rows per batch for streaming read
    DEFAULT_RANDOM_STATE = 42

    if sampling_method is None:
        if task_type in ("binary", "multiclass"):
            sampling_method = "stratified"
        else:
            sampling_method = "random"
        logger.info("Sampling method derived from task_type=%s: using %s", task_type, sampling_method)
    else:
        logger.info("Performing sampling: method=%s", sampling_method)

    def get_s3_client():
        """Create and return an S3 client using credentials from environment variables."""
        access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        endpoint_url = os.environ.get("AWS_S3_ENDPOINT")
        region_name = os.environ.get("AWS_DEFAULT_REGION")

        if (access_key and not secret_key) or (secret_key and not access_key):
            raise ValueError(
                "S3 credentials misconfigured: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must either "
                "both be set and non-empty, or both be unset. Check the 's3-secret' Kubernetes secret."
            )
        if not access_key and not secret_key:
            raise ValueError(
                "S3 credentials missing: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be provided via "
                "the 's3-secret' Kubernetes secret when using s3:// dataset URIs."
            )

        return boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region_name,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def _sample_first_n_rows(text_stream, chunk_size, max_size_bytes):
        """Take rows from the start of the stream until the size limit is reached."""
        chunk_list = []
        accumulated_size = 0

        try:
            for chunk_df in pd.read_csv(text_stream, chunksize=chunk_size):
                chunk_memory = chunk_df.memory_usage(deep=True).sum()

                if accumulated_size + chunk_memory > max_size_bytes:
                    remaining_bytes = max_size_bytes - accumulated_size
                    bytes_per_row = chunk_memory / len(chunk_df) if len(chunk_df) > 0 else 0
                    if bytes_per_row > 0:
                        rows_to_take = max(1, int(remaining_bytes / bytes_per_row))
                        chunk_df = chunk_df.head(rows_to_take)
                        chunk_list.append(chunk_df)
                    break

                chunk_list.append(chunk_df)
                accumulated_size += chunk_memory

                if accumulated_size >= max_size_bytes:
                    break
        except Exception as e:
            if not chunk_list:
                raise ValueError(f"Error reading CSV from S3: {str(e)}") from e

        return pd.concat(chunk_list, ignore_index=True) if chunk_list else pd.DataFrame()

    def _sample_stratified(text_stream, chunk_size, max_size_bytes, label_column):
        """Merge batches and subsample proportionally by target column to stay under the size limit."""
        subsampled_data = None

        try:
            for chunk_df in pd.read_csv(text_stream, chunksize=chunk_size):
                chunk_df = chunk_df.dropna(subset=[label_column])
                if chunk_df.empty:
                    continue
                if label_column not in chunk_df.columns:
                    raise ValueError(
                        f"Target column '{label_column}' not found in the dataset. "
                        f"Available columns: {list(chunk_df.columns)}"
                    )

                combined_data = (
                    pd.concat([subsampled_data, chunk_df], ignore_index=True)
                    if subsampled_data is not None
                    else chunk_df
                )
                combined_memory = combined_data.memory_usage(deep=True).sum()

                if combined_memory <= max_size_bytes:
                    subsampled_data = combined_data
                else:
                    sampling_frac = max_size_bytes / combined_memory
                    subsampled_data = (
                        combined_data.groupby(label_column, group_keys=False)
                        .apply(lambda x: x.sample(frac=sampling_frac, random_state=DEFAULT_RANDOM_STATE))
                        .reset_index(drop=True)
                    )

        except Exception as e:
            logger.debug("Error reading CSV and stratified sampling: %s", e, exc_info=True)
            if subsampled_data is None or subsampled_data.empty:
                raise ValueError(f"Error reading CSV from S3: {str(e)}") from e

        if subsampled_data is None:
            return pd.DataFrame()
        return subsampled_data.sample(frac=1, random_state=DEFAULT_RANDOM_STATE).reset_index(drop=True)

    def _sample_random(text_stream, chunk_size, max_size_bytes):
        """Iterate all batches, merge with accumulated data, randomly subsample when over the limit."""
        subsampled_data = None

        try:
            for chunk_df in pd.read_csv(text_stream, chunksize=chunk_size):
                data = (
                    pd.concat([subsampled_data, chunk_df], ignore_index=True)
                    if subsampled_data is not None
                    else chunk_df
                )
                combined_memory = data.memory_usage(deep=True).sum()

                if combined_memory <= max_size_bytes:
                    subsampled_data = data
                else:
                    sampling_frac = max_size_bytes / combined_memory
                    subsampled_data = data.sample(frac=sampling_frac, random_state=DEFAULT_RANDOM_STATE).reset_index(
                        drop=True
                    )

            return subsampled_data if subsampled_data is not None else pd.DataFrame()

        except Exception as e:
            if subsampled_data is None or subsampled_data.empty:
                raise ValueError(f"Error reading CSV from S3: {str(e)}") from e
            return subsampled_data

    def load_data_in_batches(
        s3_client,
        bucket_name,
        file_key,
        max_size_bytes,
        sampling_method,
        label_column,
    ):
        """Load CSV from S3 in batches and return a sampled dataframe using the chosen strategy."""
        if sampling_method == "stratified" and label_column is None:
            raise ValueError("label_column must be provided when sampling_method='stratified'")

        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        text_stream = io.TextIOWrapper(response["Body"], encoding="utf-8")

        if sampling_method == "stratified":
            return _sample_stratified(text_stream, PANDAS_CHUNK_SIZE, max_size_bytes, label_column)
        if sampling_method == "random":
            return _sample_random(text_stream, PANDAS_CHUNK_SIZE, max_size_bytes)
        return _sample_first_n_rows(text_stream, PANDAS_CHUNK_SIZE, max_size_bytes)

    s3_client = get_s3_client()
    sampled_dataframe = load_data_in_batches(
        s3_client,
        bucket_name,
        file_key,
        max_size_bytes=MAX_SIZE_BYTES,
        sampling_method=sampling_method,
        label_column=label_column,
    )

    n_samples = len(sampled_dataframe)
    logger.info("Read %d rows from s3://%s/%s (sampling_method=%s)", n_samples, bucket_name, file_key, sampling_method)

    # Save the sampled dataframe to the output artifact
    sampled_dataframe.to_csv(full_dataset.path, index=False)

    return NamedTuple("outputs", sample_config=dict)(sample_config={"n_samples": n_samples})


if __name__ == "__main__":
    from kfp.compiler import Compiler

    Compiler().compile(
        automl_data_loader,
        package_path=__file__.replace(".py", "_component.yaml"),
    )
