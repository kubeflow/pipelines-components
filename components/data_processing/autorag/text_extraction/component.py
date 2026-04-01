from kfp import dsl


@dsl.component(
    base_image="registry.redhat.io/rhoai/odh-pipeline-runtime-datascience-cpu-py312-rhel9@sha256:f9844dc150592a9f196283b3645dda92bd80dfdb3d467fa8725b10267ea5bdbc",
    packages_to_install=["docling[ort]"],
)
def text_extraction(
    documents_descriptor: dsl.Input[dsl.Artifact],
    extracted_text: dsl.Output[dsl.Artifact],
):
    """Text Extraction component.

    Reads the documents_descriptor JSON (from documents_discovery), fetches
    the listed documents from S3, and extracts text using the docling library.

    Args:
        documents_descriptor: Input artifact containing
            documents_descriptor.json with bucket, prefix, and documents list.
        extracted_text: Output artifact where the extracted text content will be stored.
    """
    import json
    import logging
    import os
    import sys
    import tempfile
    from concurrent.futures import ThreadPoolExecutor
    from functools import partial
    from pathlib import Path

    import boto3
    from botocore.exceptions import SSLError
    from docling.datamodel.accelerator_options import AcceleratorOptions
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PaginatedPipelineOptions, PdfPipelineOptions
    from docling.document_converter import (
        DocumentConverter,
        HTMLFormatOption,
        MarkdownFormatOption,
        PdfFormatOption,
        PowerpointFormatOption,
        WordFormatOption,
    )

    DOCUMENTS_DESCRIPTOR_FILENAME = "documents_descriptor.json"
    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".md", ".html", ".txt"}
    DOWNLOAD_MAX_WORKERS = 8
    BATCH_SIZE = 10

    logger = logging.getLogger("Text Extraction component logger")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(handler)

    descriptor_root = Path(documents_descriptor.path)
    if descriptor_root.is_dir():
        descriptor_path = descriptor_root / DOCUMENTS_DESCRIPTOR_FILENAME
    else:
        descriptor_path = descriptor_root

    if not descriptor_path.exists():
        raise FileNotFoundError(f"Descriptor not found: {descriptor_path}")

    with open(descriptor_path) as f:
        descriptor = json.load(f)

    bucket = descriptor["bucket"]
    documents = descriptor["documents"]

    s3_creds = {k: os.environ.get(k) for k in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_S3_ENDPOINT"]}
    for k, v in s3_creds.items():
        if v is None:
            raise ValueError(f"{k} environment variable not set. Check if kubernetes secret was configured properly.")

    s3_creds["AWS_DEFAULT_REGION"] = os.environ.get("AWS_DEFAULT_REGION", "")

    def _make_s3_client(verify=True):
        session = boto3.session.Session(
            aws_access_key_id=s3_creds["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=s3_creds["AWS_SECRET_ACCESS_KEY"],
            region_name=s3_creds.get("AWS_DEFAULT_REGION"),
        )
        return session.client(
            service_name="s3",
            endpoint_url=s3_creds["AWS_S3_ENDPOINT"],
            verify=verify,
        )

    s3_client = _make_s3_client()

    def download_document(doc: dict, base_path: Path) -> bool:
        nonlocal s3_client
        key = doc["key"]
        local_path = base_path / key
        local_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            logger.info("Downloading %s", key)
            s3_client.download_file(bucket, key, str(local_path))
            return True
        except SSLError:
            logger.warning(
                "SSL error when downloading %s, retrying with verify=False",
                key,
            )
            s3_client = _make_s3_client(verify=False)
            s3_client.download_file(bucket, key, str(local_path))
            return True
        except Exception as e:
            logger.error("Failed to fetch %s: %s", key, e)
            raise

    def process_document(file_path_str: str, output_dir_str: str) -> bool:
        try:
            path = Path(file_path_str)
            out_dir = Path(output_dir_str)
            output_file = out_dir / f"{path.name}.md"

            # Handle .txt files directly (docling doesn't support plain text as input format)
            if path.suffix.lower() == ".txt":
                logger.info("Processing TXT file %s (direct read)", path.name)
                text_content = path.read_text(encoding="utf-8")
                # Save as markdown (plain text is valid markdown)
                output_file.write_text(text_content, encoding="utf-8")
                logger.info("Successfully processed %s -> %s", path.name, output_file.name)
                return True

            # For all other formats, use docling
            # Configure pipeline options for PDF
            pdf_pipeline_options = PdfPipelineOptions()
            pdf_pipeline_options.do_ocr = False
            pdf_pipeline_options.do_table_structure = False
            pdf_pipeline_options.accelerator_options = AcceleratorOptions(device="cpu", num_threads=1)

            # Configure pipeline options for paginated documents (DOCX, PPTX)
            paginated_pipeline_options = PaginatedPipelineOptions()
            paginated_pipeline_options.generate_page_images = False
            paginated_pipeline_options.accelerator_options = AcceleratorOptions(device="cpu", num_threads=1)

            # Configure DocumentConverter with format options for all supported formats
            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_pipeline_options),
                    InputFormat.DOCX: WordFormatOption(pipeline_options=paginated_pipeline_options),
                    InputFormat.PPTX: PowerpointFormatOption(pipeline_options=paginated_pipeline_options),
                    InputFormat.HTML: HTMLFormatOption(),
                    InputFormat.MD: MarkdownFormatOption(),
                }
            )

            logger.debug("Processing %s with format %s using docling", path.name, path.suffix)
            result = converter.convert(path)
            markdown_content = result.document.export_to_markdown()
            output_file.write_text(markdown_content, encoding="utf-8")
            logger.debug("Successfully processed %s -> %s", path.name, output_file.name)
            return True
        except Exception as e:
            logger.error("Failed to process %s: %s", file_path_str, e)
            return False

    output_dir = Path(extracted_text.path)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_results = []
    batches = [documents[i : i + BATCH_SIZE] for i in range(0, len(documents), BATCH_SIZE)] if documents else []

    logger.info("Starting text extraction for %d documents in %d batch(es).", len(documents), len(batches))

    for batch_idx, batch_docs in enumerate(batches):
        logger.info("Processing batch %d/%d (%d documents).", batch_idx + 1, len(batches), len(batch_docs))

        with tempfile.TemporaryDirectory() as download_dir:
            batch_download_path = Path(download_dir)
            download_workers = min(DOWNLOAD_MAX_WORKERS, len(batch_docs))
            download_fn = partial(download_document, base_path=batch_download_path)
            with ThreadPoolExecutor(max_workers=download_workers) as executor:
                list(executor.map(download_fn, batch_docs))

            files_to_process = [
                f for f in batch_download_path.rglob("*") if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
            ]

            if not files_to_process:
                logger.warning(
                    "No supported files found in batch %d (downloaded %d files)", batch_idx + 1, len(batch_docs)
                )
                continue

            logger.debug("Found %d files to process in batch %d", len(files_to_process), batch_idx + 1)
            process_workers = min(os.cpu_count() or 1, len(files_to_process))
            worker_fn = partial(process_document, output_dir_str=str(output_dir))
            with ThreadPoolExecutor(max_workers=process_workers) as executor:
                batch_results = list(executor.map(worker_fn, [str(f) for f in files_to_process]))
            all_results.extend(batch_results)

    results = all_results
    processed_count = sum(1 for r in results if r)
    error_count = len(results) - processed_count

    summary = f"Text extraction completed. Total processed: {processed_count}, Errors: {error_count}."
    logger.info(summary)


if __name__ == "__main__":
    from kfp.compiler import Compiler

    Compiler().compile(
        text_extraction,
        package_path=__file__.replace(".py", "_component.yaml"),
    )
