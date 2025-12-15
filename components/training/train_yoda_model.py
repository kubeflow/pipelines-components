from kfp import dsl
from typing import Optional
import kfp


@dsl.component(
    base_image="registry.access.redhat.com/ubi9/python-311:latest",
    kfp_package_path="git+https://github.com/kubeflow/pipelines@master#egg=kfp&subdirectory=sdk/python",
    packages_to_install=["kubernetes"],
    task_config_passthroughs=[
        dsl.TaskConfigField.RESOURCES,
        dsl.TaskConfigField.KUBERNETES_TOLERATIONS,
        dsl.TaskConfigField.KUBERNETES_NODE_SELECTOR,
        dsl.TaskConfigField.KUBERNETES_AFFINITY,
        dsl.TaskConfigPassthrough(field=dsl.TaskConfigField.ENV, apply_to_task=True),
        dsl.TaskConfigPassthrough(field=dsl.TaskConfigField.KUBERNETES_VOLUMES, apply_to_task=True),
    ],
)
def train_model(
        input_dataset: dsl.Input[dsl.Dataset],
        model_name: str,
        run_id: str,
        pvc_path: str,
        output_model: dsl.Output[dsl.Model],
        output_metrics: dsl.Output[dsl.Metrics],
        # Training configuration parameters
        epochs: int = 10,
        lora_rank: int = 8,
        learning_rate: float = 3e-4,
        batch_size: int = 16,
        max_length: int = 64,
        # Training control parameters
        max_steps: Optional[int] = None,
        logging_steps: int = 10,
        save_steps: Optional[int] = None,
        save_strategy: str = "epoch",
        # Optimizer parameters
        optimizer: str = "adamw_torch",
        adam_beta1: float = 0.9,
        adam_beta2: float = 0.999,
        adam_epsilon: float = 1e-8,
        weight_decay: float = 0.01,
        # Performance optimization
        use_flash_attention: bool = False,
        # Infrastructure parameters
        num_nodes: int = 2,
        trainer_runtime: str = "torch-distributed",
        kubernetes_config: dsl.TaskConfig = None,
):
    """Train a large language model using distributed training with LoRA fine-tuning.

    This function creates and manages a Kubernetes TrainJob for distributed training
    of a large language model using LoRA (Low-Rank Adaptation) fine-tuning. It handles
    the complete training workflow including job creation, monitoring, and artifact
    collection.

    Args:
        model_name (str): HuggingFace model identifier (e.g., "meta-llama/Llama-3.2-3B-Instruct").
        run_id (str): Unique identifier for this training run. Use dsl.PIPELINE_JOB_ID_PLACEHOLDER.
        dataset_path (str): Path to the training dataset within the PVC.
        pvc_path (str): Base path within the PVC for storing outputs.
        output_model (dsl.Output[dsl.Model]): Kubeflow output artifact for the trained model.
        output_metrics (dsl.Output[dsl.Metrics]): Kubeflow output artifact for training metrics.
        epochs (int, optional): Number of training epochs. Defaults to 10.
        lora_rank (int, optional): LoRA adapter rank (lower = fewer parameters, faster training). Defaults to 8.
        learning_rate (float, optional): Learning rate for training optimization. Defaults to 3e-4.
        batch_size (int, optional): Per-device training batch size. Defaults to 16.
        max_length (int, optional): Maximum token sequence length for training. Defaults to 64.
        max_steps (int, optional): Maximum number of training steps. If specified, overrides epochs. Defaults to None.
        logging_steps (int, optional): Number of steps between logging outputs. Defaults to 10.
        save_steps (int, optional): Number of steps between model checkpoints. Defaults to None.
        save_strategy (str, optional): Checkpoint saving strategy ("epoch" or "steps"). Defaults to "epoch".
        optimizer (str, optional): Optimizer to use (e.g., "adamw_torch", "adamw_torch_fused"). Defaults to "adamw_torch".
        adam_beta1 (float, optional): Beta1 parameter for Adam optimizer. Defaults to 0.9.
        adam_beta2 (float, optional): Beta2 parameter for Adam optimizer. Defaults to 0.999.
        adam_epsilon (float, optional): Epsilon parameter for Adam optimizer. Defaults to 1e-8.
        weight_decay (float, optional): Weight decay for regularization. Defaults to 0.01.
        use_flash_attention (bool, optional): Whether to use Flash Attention 2 for improved performance. Defaults to False.
        num_nodes (int, optional): Number of nodes for distributed training. Defaults to 2.
        trainer_runtime (str, optional): Runtime to use for Kubeflow Trainer. Defaults to "torch-distributed".
    """
    import json
    import os
    import shutil
    import textwrap
    import time
    import inspect

    from kubernetes import client as k8s_client, config
    from kubernetes.client.rest import ApiException

    def get_target_modules(model_name: str) -> list:
        """Get appropriate LoRA target modules based on model architecture.

        Selects optimal layers for LoRA adaptation based on research findings:
        - Attention layers (q_proj, k_proj, v_proj, o_proj) control attention patterns
        - MLP layers (gate_proj, up_proj, down_proj) store task-specific knowledge

        Model-specific targeting:
        - Granite: Attention layers only (q,k,v,o)
        - LLaMA/Mistral/Qwen: Full coverage (attention + MLP)
        - Phi: Uses 'dense' instead of 'o_proj'
        - Unknown: Conservative fallback (q,v)

        Based on LoRA (arXiv:2106.09685), QLoRA (arXiv:2305.14314), and model-specific research.
        """
        model_name_lower = model_name.lower()

        if "granite" in model_name_lower:
            return ["q_proj", "v_proj", "k_proj", "o_proj"]
        elif "llama" in model_name_lower:
            return [
                "q_proj",
                "v_proj",
                "k_proj",
                "o_proj",
                "gate_proj",
                "up_proj",
                "down_proj",
            ]
        elif "mistral" in model_name_lower or "mixtral" in model_name_lower:
            return [
                "q_proj",
                "v_proj",
                "k_proj",
                "o_proj",
                "gate_proj",
                "up_proj",
                "down_proj",
            ]
        elif "qwen" in model_name_lower:
            return [
                "q_proj",
                "v_proj",
                "k_proj",
                "o_proj",
                "gate_proj",
                "up_proj",
                "down_proj",
            ]
        elif "phi" in model_name_lower:
            return ["q_proj", "v_proj", "k_proj", "dense"]
        else:
            print(
                f"Warning: Unknown model architecture for {model_name}, using conservative LoRA targets"
            )
            return ["q_proj", "v_proj"]

    def train_model_func(
            lora_rank: int,
            learning_rate: float,
            batch_size: int,
            max_length: int,
            model_name: str,
            dataset_path: str,
            epochs: int,
            pvc_path: str,
            target_modules: list,
            max_steps: int,
            logging_steps: int,
            save_steps: int,
            save_strategy: str,
            optimizer: str,
            adam_beta1: float,
            adam_beta2: float,
            adam_epsilon: float,
            weight_decay: float,
            use_flash_attention: bool,
    ):
        import os
        import json
        import torch
        from datasets import load_from_disk
        from peft import get_peft_model, LoraConfig
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            TrainerCallback,
        )
        from trl import SFTConfig, SFTTrainer

        local_rank = int(os.environ.get("LOCAL_RANK", 0))
        world_rank = int(os.environ.get("RANK", 0))
        world_size = int(os.environ.get("WORLD_SIZE", 1))

        print(
            f"Worker info - Local rank: {local_rank}, World rank: {world_rank}, World size: {world_size}"
        )

        is_main_worker = world_rank == 0

        class MetricsCallback(TrainerCallback):
            def __init__(self, is_main_worker):
                self.is_main_worker = is_main_worker
                self.initial_loss = None
                self.final_loss = None

            def on_log(self, args, state, control, logs=None, **kwargs):
                if logs and self.is_main_worker and "loss" in logs:
                    if self.initial_loss is None:
                        self.initial_loss = logs["loss"]
                    self.final_loss = logs["loss"]

        metrics_callback = MetricsCallback(is_main_worker)

        print("Downloading and loading model")
        model_kwargs = {
            "device_map": "auto",
            "torch_dtype": torch.float16,
            "trust_remote_code": True,
        }
        if use_flash_attention:
            model_kwargs["attn_implementation"] = "flash_attention_2"

        model = AutoModelForCausalLM.from_pretrained(model_name, **model_kwargs)

        print(f"Using LoRA target modules for {model_name}: {target_modules}")

        config = LoraConfig(
            r=lora_rank,
            lora_alpha=lora_rank * 2,
            bias="none",
            lora_dropout=0.05,
            task_type="CAUSAL_LM",
            target_modules=target_modules,
        )
        model = get_peft_model(model, config)

        print("Loading dataset")
        dataset = load_from_disk(dataset_path)

        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        tokenizer.padding_side = "right"

        sft_config = SFTConfig(
            ## Memory optimization
            gradient_checkpointing=True,
            gradient_checkpointing_kwargs={"use_reentrant": False},
            gradient_accumulation_steps=1,
            per_device_train_batch_size=batch_size,
            auto_find_batch_size=True,
            ## Dataset configuration
            max_length=max_length,
            packing=use_flash_attention,  # Packing works best with Flash Attention
            ## Training parameters
            num_train_epochs=epochs if max_steps is None else None,
            max_steps=-1 if max_steps is None else max_steps,
            learning_rate=learning_rate,
            optim=optimizer,
            ## Optimizer parameters
            adam_beta1=adam_beta1,
            adam_beta2=adam_beta2,
            adam_epsilon=adam_epsilon,
            weight_decay=weight_decay,
            ## Logging and saving
            logging_steps=logging_steps,
            save_steps=save_steps,
            save_strategy=save_strategy,
            logging_dir="./logs",
            report_to="none",
        )
        trainer = SFTTrainer(
            model=model,
            processing_class=tokenizer,
            args=sft_config,
            train_dataset=dataset,
            callbacks=[metrics_callback],
        )

        train_result = trainer.train()

        if torch.distributed.is_initialized():
            torch.distributed.barrier()
            print(f"Worker {world_rank} - Training completed and synchronized")

        if not is_main_worker:
            print(
                f"Worker {world_rank} - Skipping model export and metrics (not main worker)"
            )
            # Clean up distributed process group for non-main workers
            if torch.distributed.is_initialized():
                print(f"Worker {world_rank} - Cleaning up distributed process group")
                torch.distributed.destroy_process_group()
                print(f"Worker {world_rank} - Distributed process group destroyed")
            return

        print("Main worker (rank 0) - Exporting model and metrics...")

        # Save LoRA adapter
        model_output_path = os.path.join(pvc_path, "adapter")
        model.save_pretrained(model_output_path)
        tokenizer.save_pretrained(model_output_path)
        print("LoRA adapter exported successfully!")

        # Clean up distributed process group for main worker AFTER model saving
        if torch.distributed.is_initialized():
            print(f"Worker {world_rank} - Cleaning up distributed process group")
            torch.distributed.destroy_process_group()
            print(f"Worker {world_rank} - Distributed process group destroyed")

        print(f"Collecting essential metrics")
        metrics_dict = {}

        if hasattr(train_result, "train_loss"):
            metrics_dict["final_train_loss"] = train_result.train_loss
        if hasattr(train_result, "train_runtime"):
            metrics_dict["train_runtime_seconds"] = train_result.train_runtime
        if hasattr(train_result, "train_samples_per_second"):
            metrics_dict["throughput_samples_per_sec"] = (
                train_result.train_samples_per_second
            )

        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        metrics_dict["total_parameters_millions"] = total_params / 1_000_000
        metrics_dict["trainable_parameters_millions"] = trainable_params / 1_000_000
        metrics_dict["lora_efficiency_percent"] = (
                                                          trainable_params / total_params
                                                  ) * 100

        metrics_dict["lora_rank"] = config.r
        metrics_dict["learning_rate"] = sft_config.learning_rate
        metrics_dict["effective_batch_size"] = (
                sft_config.per_device_train_batch_size * world_size
        )
        metrics_dict["dataset_size"] = len(dataset)

        metrics_dict["num_nodes"] = (
            world_size // torch.cuda.device_count()
            if torch.cuda.is_available() and torch.cuda.device_count() > 0
            else 1
        )
        if torch.cuda.is_available():
            metrics_dict["peak_gpu_memory_gb"] = torch.cuda.max_memory_allocated() / (
                    1024**3
            )

        if metrics_callback.initial_loss and metrics_callback.final_loss:
            metrics_dict["initial_loss"] = metrics_callback.initial_loss
            metrics_dict["loss_reduction"] = (
                    metrics_callback.initial_loss - metrics_callback.final_loss
            )
            metrics_dict["loss_reduction_percent"] = (
                                                             (metrics_callback.initial_loss - metrics_callback.final_loss)
                                                             / metrics_callback.initial_loss
                                                     ) * 100

        with open(os.path.join(pvc_path, "metrics.json"), "w") as f:
            json.dump(metrics_dict, f, indent=2)

        print(
            f"Exported {len(metrics_dict)} metrics to {os.path.join(pvc_path, 'metrics.json')}"
        )
        print("Model and metrics exported successfully!")

    print("Copying dataset to PVC...")
    dataset_path = os.path.join(pvc_path, "dataset", "train")
    os.makedirs(dataset_path, exist_ok=True)
    shutil.copytree(
        input_dataset.path,
        dataset_path,
        dirs_exist_ok=True,
    )
    print(f"Dataset copied successfully from {input_dataset.path} to {dataset_path}")

    print("=== Starting TrainJob creation process ===")

    target_modules = get_target_modules(model_name)
    print(f"Selected LoRA target modules for {model_name}: {target_modules}")

    with open(
            "/var/run/secrets/kubernetes.io/serviceaccount/namespace", "r"
    ) as ns_file:
        namespace = ns_file.readline()

    print("Generating command...")

    func_code = inspect.getsource(train_model_func)
    func_code = textwrap.dedent(func_code)

    func_call_code = f"""
import os
import json

# Parse function arguments from environment variable
config_json = os.environ.get("TRAINING_CONFIG", "{{}}")
func_args = json.loads(config_json)

# Call the training function with parsed arguments
{train_model_func.__name__}(**func_args)
"""

    func_code = f"{func_code}\n{func_call_code}"

    # Build package list based on configuration
    packages = ["transformers", "peft", "accelerate", "trl"]
    if use_flash_attention:
        packages.append("flash-attn")
    packages_str = " ".join(packages)

    install_script = f"""set -e
set -o pipefail

echo "=== Starting container setup ==="
echo "Python version: $(python --version)"

if ! [ -x "$(command -v pip)" ]; then
    echo "Installing pip..."
    python -m ensurepip || python -m ensurepip --user
fi

echo "Installing Python packages..."
PIP_DISABLE_PIP_VERSION_CHECK=1 python -m pip install --user --quiet --no-warn-script-location {packages_str}

echo "Creating training script..."
cat > ephemeral_component.py << 'EOF'
{func_code}
EOF

echo "Starting distributed training..."
torchrun --nproc_per_node=1 ephemeral_component.py"""

    command = ["bash", "-c", install_script]

    print(f"Generated command: {command}")
    print(f"Command length: {len(command)}")
    print(f"Command type: {type(command)}")

    print("Loading Kubernetes configuration...")
    try:
        config.load_incluster_config()
        print("Loaded in-cluster Kubernetes configuration")
    except config.ConfigException:
        config.load_kube_config()
        print("Loaded kubeconfig Kubernetes configuration")

    print("Creating Kubernetes API client...")
    api_client = k8s_client.ApiClient()
    custom_objects_api = k8s_client.CustomObjectsApi(api_client)
    print("Successfully created Kubernetes API client")

    print("Defining TrainJob resource...")

    env_vars = [
        {"name": "HOME", "value": "/tmp"},
        {
            "name": "TRAINING_CONFIG",
            "value": json.dumps(
                {
                    "lora_rank": lora_rank,
                    "learning_rate": learning_rate,
                    "batch_size": batch_size,
                    "max_length": max_length,
                    "model_name": model_name,
                    "dataset_path": dataset_path,
                    "epochs": epochs,
                    "pvc_path": pvc_path,
                    "target_modules": target_modules,
                    "max_steps": max_steps,
                    "logging_steps": logging_steps,
                    "save_steps": save_steps,
                    "save_strategy": save_strategy,
                    "optimizer": optimizer,
                    "adam_beta1": adam_beta1,
                    "adam_beta2": adam_beta2,
                    "adam_epsilon": adam_epsilon,
                    "weight_decay": weight_decay,
                    "use_flash_attention": use_flash_attention,
                }
            ),
        },
        *(kubernetes_config.env or []),
    ]

    train_job = {
        "apiVersion": "trainer.kubeflow.org/v1alpha1",
        "kind": "TrainJob",
        "metadata": {"name": f"kfp-{run_id}", "namespace": namespace},
        "spec": {
            "runtimeRef": {"name": trainer_runtime},
            "trainer": {
                "numNodes": num_nodes,
                "resourcesPerNode": kubernetes_config.resources,
                "env": env_vars,
                "command": command,
            },
            "podSpecOverrides": [
                {
                    "targetJobs": [{"name": "node"}],
                    "volumes": kubernetes_config.volumes,
                    "containers": [
                        {
                            "name": "node",
                            "volumeMounts": kubernetes_config.volume_mounts,
                        }
                    ],
                    "nodeSelector": kubernetes_config.node_selector,
                    "tolerations": kubernetes_config.tolerations,
                }
            ],
        },
    }

    print(f"TrainJob definition created:")
    print(f"  - Name: kfp-{run_id}")
    print(f"  - Namespace: {namespace}")

    print(f"  - Runtime: {trainer_runtime}")
    print(f"  - Nodes: {num_nodes}")
    print(f"  - Model: {model_name}")
    print(f"  - Dataset: {dataset_path}")
    print(f"  - Epochs: {epochs}")

    print("Submitting TrainJob to Kubernetes...")
    try:
        response = custom_objects_api.create_namespaced_custom_object(
            group="trainer.kubeflow.org",
            version="v1alpha1",
            namespace=namespace,
            plural="trainjobs",
            body=train_job,
        )
        job_name = response["metadata"]["name"]
        print(f"TrainJob {job_name} created successfully")
        print(f"Response metadata: {response.get('metadata', {})}")
    except ApiException as e:
        print(f"Error creating TrainJob: {e}")
        print(f"Error details: {e.body}")
        print(f"Error status: {e.status}")
        raise

    print(f"Starting to monitor TrainJob {job_name} status...")
    check_count = 0
    while True:
        check_count += 1
        try:
            print(f"Checking job status (attempt {check_count})...")
            job_status = custom_objects_api.get_namespaced_custom_object(
                group="trainer.kubeflow.org",
                version="v1alpha1",
                namespace=namespace,
                plural="trainjobs",
                name=job_name,
            )

            status = job_status.get("status", {})
            conditions = status.get("conditions", [])
            print(f"Job status conditions: {conditions}")

            completed = False
            failed = False

            for condition in conditions:
                condition_type = condition.get("type", "")
                condition_status = condition.get("status", "")
                condition_reason = condition.get("reason", "")
                condition_message = condition.get("message", "")

                print(
                    f"Condition: type={condition_type}, status={condition_status}, reason={condition_reason}"
                )

                if condition_type == "Complete" and condition_status == "True":
                    print(
                        f"Training job {job_name} completed successfully: {condition_message}"
                    )
                    completed = True
                    break
                elif condition_type == "Failed" and condition_status == "True":
                    print(f"Training job {job_name} failed: {condition_message}")
                    failed = True
                    break
                elif condition_type == "Cancelled" and condition_status == "True":
                    print(f"Training job {job_name} was cancelled: {condition_message}")
                    failed = True
                    break

            if completed:
                break
            elif failed:
                raise RuntimeError(f"Training job {job_name} failed or was cancelled")
            else:
                print(f"Job is still running, continuing to wait...")

        except ApiException as e:
            print(f"Error checking job status: {e}")
            print(f"Error details: {e.body}")

        print(f"Waiting 10 seconds before next check...")
        time.sleep(10)

    print(f"Training job {job_name} completed. Logs would be retrieved here.")

    print("Processing training results...")

    metrics_file_path = os.path.join(pvc_path, "metrics.json")
    print(f"Looking for metrics file at: {metrics_file_path}")
    if os.path.exists(metrics_file_path):
        print(f"Found metrics file, reading from {metrics_file_path}")
        with open(metrics_file_path, "r") as f:
            metrics_dict = json.load(f)

        print(f"Loaded {len(metrics_dict)} metrics from file")

        exported_count = 0
        for metric_name, metric_value in metrics_dict.items():
            # Ignore metrics that are 0 to avoid a bug in the RHOAI UI.
            if isinstance(metric_value, (int, float)) and metric_value != 0:
                output_metrics.log_metric(metric_name, metric_value)
                print(f"Exported metric: {metric_name} = {metric_value}")
                exported_count += 1

        print(f"Successfully exported {exported_count} metrics to Kubeflow")
        os.remove(metrics_file_path)
    else:
        print(f"Warning: Metrics file {metrics_file_path} not found")

    print("Copying model from PVC to Kubeflow output path...")
    model_source = os.path.join(pvc_path, "adapter")
    print(f"Model source: {model_source}")
    print(f"Destination: {output_model.path}")

    if not os.path.exists(model_source):
        raise FileNotFoundError(
            f"Trained model not found at expected location: {model_source}"
        )

    output_model.name = f"{model_name}-adapter"
    shutil.copytree(model_source, output_model.path, dirs_exist_ok=True)
    print(f"Model copied successfully from {model_source} to {output_model.path}")

    print("=== TrainJob process completed successfully ===")


if __name__ == "__main__":
    kfp.compiler.Compiler().compile(
        train_model,
        package_path=__file__.replace(".py", "_component.yaml"),
    )