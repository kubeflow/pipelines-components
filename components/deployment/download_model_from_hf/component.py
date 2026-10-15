"""Component to download a model from HuggingFace Hub to a local directory (PVC)."""

from kfp.dsl import component


@component(base_image="python:3.12-slim-bullseye", packages_to_install=["huggingface-hub"])
def download_model_from_hf(model_identifier: str, local_model_dir: str = "/models", if_exists: str = "skip"):
    """Downloads a model from HuggingFace Hub to a local directory

    (use mounted PVC path with sufficient storage for larger models).

    Args:
        model_identifier: HuggingFace model identifier (e.g., "Qwen/Qwen3-VL-2B-Instruct")
        local_model_dir: Local directory to save the model files to (default: "/models")
        if_exists: Behavior if files already exist in local_model_dir. Options: ["skip" (default), "overwrite", "error"]

    Environment Variables (Assumed mounted as secret via kfp.kubernetes.use_secret_as_env):
        HUGGINGFACE_TOKEN: HuggingFace token (optional)
    """
    import os
    import pathlib

    from huggingface_hub import snapshot_download

    print(f"Checking for existing model files in: {local_model_dir}")

    # Check if model files already exist
    output_path = pathlib.Path(local_model_dir)
    existing_files = []
    if output_path.exists() and output_path.is_dir():
        existing_files = [f for f in output_path.rglob("*") if f.is_file()]

    if existing_files:
        print(f"Found {len(existing_files)} existing files in {local_model_dir}")

        if if_exists == "skip":
            print("Skipping download - model files already exist (if_exists='skip')")
            print(f"\nExisting files ({len(existing_files)}):")
            for f in sorted(existing_files):
                rel_path = f.relative_to(output_path)
                size_mb = f.stat().st_size / (1024 * 1024)
                print(f"  {rel_path} ({size_mb:.2f} MB)")
            print(f"\nUsing existing model files from: {local_model_dir}")
            return
        elif if_exists == "error":
            raise RuntimeError(
                f"Model files already exist in {local_model_dir}. "
                f"Found {len(existing_files)} files. "
                f"Use if_exists='skip' to use existing files or if_exists='overwrite' to replace them."
            )
        elif if_exists == "overwrite":
            print("Overwriting existing files (if_exists='overwrite')")
        else:
            raise ValueError(
                f"Invalid value for if_exists: '{if_exists}'. " f"Must be one of: 'skip', 'overwrite', 'error'"
            )
    else:
        print(f"No existing files found in {local_model_dir}")

    print(f"Downloading model: {model_identifier}")

    # Download model to output directory
    # This will download all model files (config, tokenizer, model weights, etc.)
    snapshot_download(
        repo_id=model_identifier,
        local_dir=local_model_dir,
        local_dir_use_symlinks=False,
        token=os.getenv("HUGGINGFACE_TOKEN"),
    )

    # Verify downloaded files
    output_path = pathlib.Path(local_model_dir)
    if output_path.exists():
        files = list(output_path.rglob("*"))
        files = [f for f in files if f.is_file()]
        print(f"\nDownloaded {len(files)} files:")
        for f in sorted(files):
            # Show relative path from output_dir.path
            rel_path = f.relative_to(output_path)
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"  {rel_path} ({size_mb:.2f} MB)")
    else:
        raise RuntimeError(f"Output directory {local_model_dir} was not created")

    print(f"\nModel download complete. Files saved to: {local_model_dir}")


if __name__ == "__main__":
    # compile the component
    from kfp.compiler import Compiler

    compiler = Compiler()
    compiler.compile(download_model_from_hf, package_path="download_model_from_hf.yaml")
