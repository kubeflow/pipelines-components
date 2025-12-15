from kfp import dsl
import kfp


@dsl.component(
    base_image="registry.access.redhat.com/ubi9/python-311:latest",
    packages_to_install=[
        "transformers",
        "torch",
        "accelerate",
        "lm-eval[vllm]",
        "unitxt",
        "sacrebleu",
        "datasets",
    ],
)
def evaluate_yoda_model(
        model_path: str,
        output_metrics: dsl.Output[dsl.Metrics],
        output_results: dsl.Output[dsl.Artifact],
        output_prompts: dsl.Output[dsl.Artifact],
        lora_adapter: dsl.Input[dsl.Model] = None,
        batch_size: int = 1,
        limit: int = None,
        max_model_len: int = 4096,
        gpu_memory_utilization: float = 0.8,
        dtype: str = "auto",
        add_bos_token: bool = True,
        include_classification_tasks: bool = True,
        include_summarization_tasks: bool = True,
        custom_translation_dataset: dsl.Input[dsl.Dataset] = None,
        log_prompts: bool = True,
        verbosity: str = "INFO",
        max_batch_size: int = None,
):
    import logging
    import os
    import json
    import time
    import random
    from typing import Dict, Any, Optional

    from lm_eval.tasks.unitxt import task
    from lm_eval.api.registry import get_model
    from lm_eval.api.model import LM
    from lm_eval.evaluator import evaluate
    from lm_eval.tasks import get_task_dict
    from lm_eval.api.instance import Instance
    from lm_eval import tasks
    from lm_eval.api.task import TaskConfig
    from lm_eval.api.metrics import mean
    from datasets import load_from_disk
    import torch
    import sacrebleu

    class TranslationTask(tasks.Task):
        """
        A custom lm-eval task for translation, using the greedy_until method
        and evaluating with the BLEU metric.
        """

        VERSION = 0

        def __init__(self, dataset_path, task_name: str, log_prompts=False, prompts_log=None):
            self.dataset_path = dataset_path
            self.task_name = task_name
            self.log_prompts = log_prompts
            self.prompts_log = [] if prompts_log is None else prompts_log
            config = TaskConfig(task=task_name, dataset_path=dataset_path)
            super().__init__(config=config)
            self.config.task = task_name
            self.fewshot_rnd = random.Random()

        def download(
                self, data_dir=None, cache_dir=None, download_mode=None, **kwargs
        ) -> None:
            self.dataset = {"test": load_from_disk(self.dataset_path)}

        def has_test_docs(self):
            return "test" in self.dataset

        def has_validation_docs(self):
            return False

        def has_training_docs(self):
            return False

        def test_docs(self):
            return self.dataset["test"]

        def doc_to_text(self, doc):
            return doc["prompt"]

        def doc_to_target(self, doc):
            return doc["completion"]

        def construct_requests(self, doc, ctx, **kwargs):
            kwargs.pop("apply_chat_template", False)
            kwargs.pop("chat_template", False)
            return Instance(
                request_type="generate_until",
                doc=doc,
                arguments=(ctx, {}),
                idx=0,
                **kwargs,
            )

        def process_results(self, doc, results):
            (generated_text,) = results

            prediction = generated_text.strip()

            if self.log_prompts:
                try:
                    self.prompts_log.append(
                        {"prompt": self.doc_to_text(doc), "response": prediction}
                    )
                except Exception:
                    # Best-effort logging; avoid breaking evaluation if logging fails
                    pass

            predictions = [prediction]
            references = [[self.doc_to_target(doc).strip()]]

            bleu_score = sacrebleu.corpus_bleu(predictions, references).score

            exact_match = 1.0 if prediction == references[0][0] else 0.0

            return {"bleu": bleu_score, "exact_match": exact_match}

        def aggregation(self):
            return {"bleu": mean, "exact_match": mean}

        def should_decontaminate(self):
            return False

        def doc_to_prefix(self, doc):
            return ""

        def higher_is_better(self):
            return {"bleu": True, "exact_match": True}

    TASK_CONFIGS = {
        "classification": [
            {
                "task": "classification_rte_simple",
                "recipe": "card=cards.rte,template=templates.classification.multi_class.relation.simple",
                "group": "classification",
                "output_type": "generate_until",
            },
            {
                "task": "classification_rte_default",
                "recipe": "card=cards.rte,template=templates.classification.multi_class.relation.default",
                "group": "classification",
                "output_type": "generate_until",
            },
            {
                "task": "classification_rte_wnli",
                "recipe": "card=cards.wnli,template=templates.classification.multi_class.relation.simple",
                "group": "classification",
                "output_type": "generate_until",
            },
        ],
        "summarization": [
            {
                "task": "summarization_xsum_formal",
                "recipe": "card=cards.xsum,template=templates.summarization.abstractive.formal,num_demos=0",
                "group": "summarization",
                "output_type": "generate_until",
            }
        ],
    }

    logging.basicConfig(
        level=getattr(logging, verbosity.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

    logger.info("Validating parameters...")

    if not torch.cuda.is_available():
        raise ValueError("CUDA is not available")

    if not (0.0 <= gpu_memory_utilization <= 1.0):
        raise ValueError("gpu_memory_utilization must be between 0.0 and 1.0")

    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    if max_model_len <= 0:
        raise ValueError("max_model_len must be positive")

    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive or None")

    if (
            not include_classification_tasks
            and not include_summarization_tasks
            and not custom_translation_dataset
    ):
        raise ValueError(
            "At least one of include_classification_tasks, include_summarization_tasks, or custom_translation_dataset must be provided"
        )

    logger.info("Parameter validation passed")

    logger.info("Creating tasks...")
    start_time = time.time()

    eval_tasks = []
    prompt_response_log = []

    if custom_translation_dataset:
        logger.info("Adding custom translation task...")
        translation_task = TranslationTask(
            custom_translation_dataset.path,
            "custom_translation",
            log_prompts=log_prompts,
            prompts_log=prompt_response_log,
        )
        eval_tasks.append(translation_task)

    if include_classification_tasks:
        logger.info("Adding classification tasks...")
        classification_configs = TASK_CONFIGS["classification"]

        for config in classification_configs:
            task_obj = task.Unitxt(config=config)
            # TODO: Remove after https://github.com/EleutherAI/lm-evaluation-harness/pull/3225 is merged.
            task_obj.config.task = config["task"]
            eval_tasks.append(task_obj)

    if include_summarization_tasks:
        logger.info("Adding summarization tasks...")
        summarization_config = TASK_CONFIGS["summarization"][0]

        task_obj = task.Unitxt(config=summarization_config)
        # TODO: Remove after https://github.com/EleutherAI/lm-evaluation-harness/pull/3225 is merged.
        task_obj.config.task = summarization_config["task"]
        eval_tasks.append(task_obj)

    task_dict = get_task_dict(eval_tasks)
    logger.info(f"Created {len(eval_tasks)} tasks in {time.time() - start_time:.2f}s")

    logger.info("Loading model...")
    start_time = time.time()

    try:
        model_args = {
            "add_bos_token": add_bos_token,
            "dtype": dtype,
            "max_model_len": max_model_len,
            "gpu_memory_utilization": gpu_memory_utilization,
            "pretrained": model_path,
            "trust_remote_code": True,
        }

        # Optionally provide LoRA adapter to lm-eval's VLLM backend
        # The backend expects `lora_local_path` and internally constructs the LoRARequest.
        if lora_adapter and lora_adapter.path:
            logger.info("LoRA adapter provided; passing lora_local_path to VLLM backend")
            model_args["lora_local_path"] = lora_adapter.path

        model_class = get_model("vllm")
        additional_config = {
            "batch_size": batch_size,
            "max_batch_size": max_batch_size,
            "device": None,
        }

        loaded_model = model_class.create_from_arg_obj(model_args, additional_config)
        logger.info(f"Model loaded successfully in {time.time() - start_time:.2f}s")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise RuntimeError(f"Model loading failed: {e}")

    logger.info("Starting evaluation...")
    start_time = time.time()

    results = evaluate(
        lm=loaded_model,
        task_dict=task_dict,
        limit=limit,
        verbosity=verbosity,
    )

    logger.info(f"Evaluation completed in {time.time() - start_time:.2f}s")

    logger.info("Saving results...")

    def clean_for_json(obj):
        """Recursively clean objects to make them JSON serializable."""
        if isinstance(obj, dict):
            return {k: clean_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_for_json(item) for item in obj]
        elif isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        else:
            # Convert non-serializable objects to string representation
            return str(obj)

    clean_results = clean_for_json(results)

    output_results.name = "results.json"

    with open(output_results.path, "w") as f:
        json.dump(clean_results, f, indent=2)
    logger.info(f"Results saved to {output_results.path}")

    # Save prompt/response log for custom TranslationTask only
    if log_prompts and custom_translation_dataset and len(prompt_response_log) > 0:
        try:
            output_prompts.name = "prompts.json"
            with open(output_prompts.path, "w") as f:
                json.dump(prompt_response_log, f, indent=2)
            logger.info(f"Prompt/response log saved to {output_prompts.path}")
        except Exception as e:
            logger.warning(f"Failed to save prompt/response log: {e}")

    logger.info("Logging metrics...")

    for task_name, task_results in clean_results["results"].items():
        for metric_name, metric_value in task_results.items():
            if isinstance(metric_value, (int, float)):
                # Skip metrics that are 0 due to a bug in the RHOAI UI.
                # TODO: Fix RHOAI UI to handle 0 values.
                # TODO: Ignore store_session_info from metrics in RHOAI UI.
                if metric_value == 0:
                    continue

                metric_key = f"{task_name}_{metric_name}"
                output_metrics.log_metric(metric_key, metric_value)
                logger.debug(f"Logged metric: {metric_key} = {metric_value}")

    logger.info("Metrics logged successfully")

    logger.info("Pipeline completed successfully")


if __name__ == "__main__":
    kfp.compiler.Compiler().compile(
        evaluate_yoda_model,
        package_path=__file__.replace(".py", "_component.yaml"),
    )