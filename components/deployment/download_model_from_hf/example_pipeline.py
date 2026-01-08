from kfp import kubernetes as k8s
from kfp.dsl import Else, If, pipeline
from kfp_components.components.deployment import download_model_from_hf


# download model from HuggingFace pipeline
@pipeline(name="download-hf-model", description="Download a model from HuggingFace to a local directory (PVC).")
def download_model_from_hf_pipeline(
    model_identifier: str,
    local_model_dir: str = "/models",
    pvc_name: str = "model-pvc",
    hf_connection_secret: str = None,
):
    """Download a model from HuggingFace to a local directory (PVC).

    Args:
        model_identifier: HuggingFace model identifier (e.g., "Qwen/Qwen3-VL-2B-Instruct")
        local_model_dir: Local directory to save the model files under (default: "/models")
        pvc_name: Name of the PVC to mount (default: "model-pvc")
        hf_connection_secret: Name of the secret to use for the HuggingFace connection (default: None)
    """
    with If(hf_connection_secret is not None):
        download_task = download_model_from_hf(model_identifier=model_identifier, local_model_dir=local_model_dir)
        download_task.set_cpu_limit("2")
        download_task.set_memory_limit("8Gi")
        download_task.set_cpu_request("2")
        download_task.set_memory_request("8Gi")

        k8s.mount_pvc(task=download_task, pvc_name=pvc_name, mount_path="/models")

        k8s.use_secret_as_env(
            download_task,
            secret_name=hf_connection_secret,
            secret_key_to_env={"HUGGINGFACE_TOKEN": "HUGGINGFACE_TOKEN"},
        )
    with Else():
        download_task = download_model_from_hf(model_identifier=model_identifier, local_model_dir=local_model_dir)
        download_task.set_cpu_limit("2")
        download_task.set_memory_limit("8Gi")
        download_task.set_cpu_request("2")
        download_task.set_memory_request("8Gi")

        k8s.mount_pvc(task=download_task, pvc_name=pvc_name, mount_path="/models")


if __name__ == "__main__":
    from kfp.compiler import Compiler

    Compiler().compile(download_model_from_hf_pipeline, package_path="download_model_from_hf_pipeline.yaml")
