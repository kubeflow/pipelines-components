from kfp import dsl


@dsl.component(
    base_image="registry.redhat.io/rhoai/odh-pipeline-runtime-datascience-cpu-py312-rhel9@sha256:f9844dc150592a9f196283b3645dda92bd80dfdb3d467fa8725b10267ea5bdbc",
    packages_to_install=["boto3"],
)
def test_data_loader(test_data_bucket_name: str, test_data_path: str, test_data: dsl.Output[dsl.Artifact] = None):
    """Download test data json file from S3 into a KFP artifact.

    The component reads S3-compatible credentials from environment variables
    (injected by the pipeline from a Kubernetes secret) and downloads a JSON
    test data file from the provided bucket and path to the output artifact.

    Args:
        test_data_bucket_name: S3 (or compatible) bucket that contains the test
            data file.
        test_data_path: S3 object key to the JSON test data file.
        test_data: Output artifact that receives the downloaded file.

    Environment variables (required when run with pipeline secret injection):
        AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_ENDPOINT, AWS_DEFAULT_REGION.

    Raises:
        ValueError: If S3 credentials are missing or misconfigured.
        Exception: If the download fails or the path is not a JSON file.
    """
    import logging
    import os
    import sys

    import boto3
    from botocore.exceptions import ClientError

    logger = logging.getLogger("Test Data Loader component logger")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(handler)

    def get_test_data_s3():
        """Validate S3 credentials and download the JSON test data file."""
        s3_creds = {
            k: os.environ.get(k)
            for k in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_S3_ENDPOINT", "AWS_DEFAULT_REGION"]
        }
        for k, v in s3_creds.items():
            if v is None:
                raise ValueError(
                    "%s environment variable not set. Check if kubernetes secret was configured properly" % k
                )

        s3_client = boto3.client(
            "s3",
            endpoint_url=s3_creds["AWS_S3_ENDPOINT"],
            region_name=s3_creds["AWS_DEFAULT_REGION"],
            aws_access_key_id=s3_creds["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=s3_creds["AWS_SECRET_ACCESS_KEY"],
        )

        if test_data_path.endswith(".json"):
            logger.info(f"Fetching test data from S3: bucket={test_data_bucket_name}, path={test_data_path}")
            try:
                logger.info(f"Starting download to {test_data.path}")
                s3_client.download_file(test_data_bucket_name, test_data_path, test_data.path)
                logger.info("Download completed successfully")
            except ClientError as e:
                if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
                    raise FileNotFoundError(
                        "Test data object not found in S3. bucket=%r, key=%r. "
                        "Check that test_data_key (pipeline parameter) is the full object key to an existing JSON file."
                        % (test_data_bucket_name, test_data_path)
                    ) from e
                logger.error("Failed to fetch %s: %s", test_data_path, e)
                raise
            except Exception as e:
                logger.error("Failed to fetch %s: %s", test_data_path, e)
                raise
        else:
            logger.error("Test data must be a json file: %s", test_data_path)
            raise

    get_test_data_s3()


if __name__ == "__main__":
    from kfp.compiler import Compiler

    Compiler().compile(
        test_data_loader,
        package_path=__file__.replace(".py", "_component.yaml"),
    )
