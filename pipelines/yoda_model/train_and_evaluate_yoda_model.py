import kfp
from kfp import dsl, kubernetes

from components.data_processing.yoda_data_preparation import prepare_yoda_dataset
from components.training.train_yoda_model import train_model
from components.evaluation.evaluate_yoda_model import evaluate_yoda_model


@dsl.pipeline(
    name="Yoda finetune",
    description="Prepare Yoda dataset, finetune a base model with LoRA, and evaluate baseline vs fine-tuned",
    pipeline_config=dsl.PipelineConfig(
        workspace=dsl.WorkspaceConfig(
            size="20Gi",
            kubernetes=dsl.KubernetesWorkspaceConfig(
                pvcSpecPatch={
                    "accessModes": ["ReadWriteMany"],
                    "storageClassName": "efs-sc",
                }
            )
        ),
    )
)
def yoda_finetune_and_evaluate(
        model_name: str = "meta-llama/Llama-3.2-3B-Instruct",
        eval_limit: int = None,
):
    """Prepare, finetune, and evaluate a model using the Yoda dataset.

    Args:
        model_name (str): HuggingFace model ID for both baseline and training.
            Defaults to "meta-llama/Llama-3.2-3B-Instruct".
        eval_limit (int): Maximum number of examples per task for evaluation.
            Use None to evaluate all available examples. Defaults to None.
    """

    # 1) Prepare dataset splits
    prepare_dataset_op = (
        prepare_yoda_dataset(yoda_input_dataset="dvgodoy/yoda_sentences",
                             operation_map={"rename_column": {"sentence":"prompt"},
                                            "translation": {"translation_extra":"completion"},
                                            "remove_columns": "translation"})
        .set_caching_options(enable_caching=False)
        .set_retry(3)
    )

    # 2 Train LoRA adapter on Yoda train split
    train_model_op = (
        train_model(
            input_dataset=prepare_dataset_op.outputs["yoda_train_dataset"],
            model_name=model_name,
            pvc_path=dsl.WORKSPACE_PATH_PLACEHOLDER,
            run_id=dsl.PIPELINE_JOB_ID_PLACEHOLDER,
        )
        .after(prepare_dataset_op)
        .set_caching_options(enable_caching=False)
        .set_cpu_request("2")
        .set_cpu_limit("2")
        .set_memory_request("30Gi")
        .set_memory_limit("30Gi")
        .set_accelerator_type("nvidia.com/gpu")
        .set_accelerator_limit("1")
    )

    # Ensure HF token available for gated model access during training
    kubernetes.use_secret_as_env(
        task=train_model_op,
        secret_name="hf-token",
        secret_key_to_env={"HF_TOKEN": "HF_TOKEN"},
    )


    # 3) Baseline evaluation (no adapter)
    baseline_eval_op = (
        evaluate_yoda_model(
            model_path=model_name,
            custom_translation_dataset=prepare_dataset_op.outputs["yoda_eval_dataset"],
            limit=eval_limit,
        )
        .set_caching_options(enable_caching=False)
        .set_accelerator_type("nvidia.com/gpu")
        .set_accelerator_limit("1")
        .set_cpu_request("4000m")
        .set_memory_request("100G")
    )

    # Ensure HF token available for gated model access during baseline eval
    kubernetes.use_secret_as_env(
        task=baseline_eval_op,
        secret_name="hf-token",
        secret_key_to_env={"HF_TOKEN": "HF_TOKEN"},
    )

    # 4) Fine-tuned evaluation (with LoRA adapter)
    finetuned_eval_op = (
        evaluate_yoda_model(
            model_path=model_name,
            custom_translation_dataset=prepare_dataset_op.outputs["yoda_eval_dataset"],
            lora_adapter=train_model_op.outputs["output_model"],
            limit=eval_limit,
        )
        .set_caching_options(enable_caching=False)
        .set_accelerator_type("nvidia.com/gpu")
        .set_accelerator_limit("1")
        .set_cpu_request("4000m")
        .set_memory_request("100G")
    ).after(train_model_op)

    # Ensure HF token available for gated model access during fine-tuned eval
    kubernetes.use_secret_as_env(
        task=finetuned_eval_op,
        secret_name="hf-token",
        secret_key_to_env={"HF_TOKEN": "HF_TOKEN"},
    )


if __name__ == "__main__":
    kfp.compiler.Compiler().compile(
        pipeline_func=yoda_finetune_and_evaluate,
        package_path=__file__.replace(".py", ".yaml"),
    )