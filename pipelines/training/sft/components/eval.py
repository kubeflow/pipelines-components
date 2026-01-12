"""Universal LLM Evaluator Component.

A comprehensive LLM evaluation component using EleutherAI's lm-evaluation-harness.
Supports both standard benchmark evaluation and custom holdout evaluation.
"""

from kfp import dsl
import kfp


@dsl.component(
    base_image="registry.access.redhat.com/ubi9/python-311:latest",
    packages_to_install=[
        "lm-eval[vllm]",  # The core harness with vLLM backend
        "unitxt",  # For IBM/generic dataset recipes
        "sacrebleu",  # For translation/BLEU metrics
        "rouge-score",  # For ROUGE metrics (summarization)
        "datasets",
        "accelerate",
        "torch",
        "transformers",
    ],
)
def universal_llm_evaluator(
    output_metrics: dsl.Output[dsl.Metrics],
    output_results: dsl.Output[dsl.Artifact],
    output_samples: dsl.Output[dsl.Artifact],
    # --- Generic Inputs ---
    task_names: list,
    model_path: str = None,  # Optional: Use for HF Hub models (e.g. "ibm/granite-7b")
    model_artifact: dsl.Input[dsl.Model] = None,  # Optional: Use for upstream pipeline models
    eval_dataset: dsl.Input[dsl.Dataset] = None,  # Optional: Eval dataset for custom holdout evaluation
    model_args: dict = {},
    gen_kwargs: dict = {},
    batch_size: str = "auto",
    limit: int = -1,
    log_samples: bool = True,
    verbosity: str = "INFO",
    # --- Custom Eval Options ---
    custom_eval_max_tokens: int = 256,
):
    """A Universal LLM Evaluator component using EleutherAI's lm-evaluation-harness.

    Supports two types of evaluation:
    1. Benchmark evaluation: Standard lm-eval tasks (arc_easy, mmlu, gsm8k, etc.)
    2. Custom holdout evaluation: When eval_dataset is provided, evaluates on your held-out data

    Args:
        output_metrics: Output metrics artifact with evaluation scores.
        output_results: Output artifact containing full evaluation results JSON.
        output_samples: Output artifact containing logged evaluation samples.
        task_names: List of benchmark task names (e.g. ["mmlu", "gsm8k"]).
        model_path: String path or HF ID. Used if model_artifact is None.
        model_artifact: KFP Model artifact from a previous pipeline step.
        eval_dataset: JSONL dataset in chat format for custom holdout evaluation.
        model_args: Dictionary for model initialization (e.g. {"dtype": "float16"}).
        gen_kwargs: Dictionary of generation kwargs passed to the model.
        batch_size: Batch size for evaluation ("auto" or integer).
        limit: Limit number of examples per task (-1 for no limit).
        log_samples: Whether to log individual evaluation samples.
        verbosity: Logging verbosity level (DEBUG, INFO, WARNING, ERROR).
        custom_eval_max_tokens: Max tokens for generation in custom eval (default: 256).
    """
    import logging
    import json
    import os
    import time
    import random
    import torch

    # Delayed imports for lm-eval
    from lm_eval import tasks
    from lm_eval.api.registry import get_model
    from lm_eval.evaluator import evaluate
    from lm_eval.tasks import get_task_dict
    from lm_eval.api.instance import Instance
    from lm_eval.api.task import TaskConfig
    from lm_eval.api.metrics import mean

    # --- 1. Setup Logging ---
    logging.basicConfig(
        level=getattr(logging, verbosity.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("UniversalEval")

    if not torch.cuda.is_available():
        logger.warning("CUDA is not available! Evaluation will be extremely slow.")

    # =========================================================================
    # Dataset Format Validation
    # =========================================================================
    def extract_chat_parts(messages: list) -> tuple:
        """Extract system, user, and assistant content from messages array."""
        system_content = None
        user_content = None
        assistant_content = None

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "system" and system_content is None:
                system_content = content
            elif role == "user" and user_content is None:
                user_content = content
            elif role == "assistant" and assistant_content is None:
                assistant_content = content

        return system_content, user_content, assistant_content

    def validate_chat_format(data: list, logger) -> tuple:
        """Validate that the dataset is in the expected chat format."""
        if not data:
            return False, 0, "Dataset is empty"

        valid_count = 0
        errors = []

        for i, doc in enumerate(data[: min(10, len(data))]):
            if "messages" not in doc:
                errors.append(f"Line {i + 1}: Missing 'messages' field")
                continue

            messages = doc["messages"]
            if not isinstance(messages, list):
                errors.append(f"Line {i + 1}: 'messages' is not an array")
                continue

            if len(messages) < 2:
                errors.append(f"Line {i + 1}: 'messages' must have at least 2 messages (user + assistant)")
                continue

            system_content, user_content, assistant_content = extract_chat_parts(messages)

            if not user_content:
                errors.append(f"Line {i + 1}: No message with role='user' found")
                continue

            if not assistant_content:
                errors.append(f"Line {i + 1}: No message with role='assistant' found")
                continue

            valid_count += 1

        if valid_count == 0:
            error_summary = "\n".join(errors[:5])
            return False, 0, f"No valid examples found. Errors:\n{error_summary}"

        if errors:
            logger.warning(f"Some examples have format issues ({len(errors)} warnings in first 10 samples)")
            for err in errors[:3]:
                logger.warning(f"  - {err}")

        return True, valid_count, None

    # =========================================================================
    # Custom Chat Holdout Task
    # =========================================================================
    class ChatHoldoutTask(tasks.Task):
        """A custom lm-eval task for evaluating on chat-format holdout data."""

        VERSION = 0

        def __init__(
            self,
            dataset_path: str,
            task_name: str = "custom_holdout_eval",
            max_gen_toks: int = 256,
            log_prompts: bool = False,
            prompts_log: list = None,
        ):
            self.dataset_path = dataset_path
            self.task_name = task_name
            self.max_gen_toks = max_gen_toks
            self.log_prompts = log_prompts
            self.prompts_log = [] if prompts_log is None else prompts_log

            config = TaskConfig(task=task_name, dataset_path=dataset_path)
            super().__init__(config=config)
            self.config.task = task_name
            self.fewshot_rnd = random.Random()

        def download(self, data_dir=None, cache_dir=None, download_mode=None, **kwargs) -> None:
            """Load the chat JSONL dataset."""
            data = []
            with open(self.dataset_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data.append(json.loads(line))

            self.dataset = {"test": data}
            logger.info(f"Loaded {len(data)} examples from {self.dataset_path}")

        def has_test_docs(self):
            return "test" in self.dataset

        def has_validation_docs(self):
            return False

        def has_training_docs(self):
            return False

        def test_docs(self):
            return self.dataset["test"]

        def doc_to_text(self, doc):
            """Extract prompt from messages with chat template."""
            messages = doc.get("messages", [])
            system_content, user_content, _ = extract_chat_parts(messages)

            if not user_content:
                return ""

            prompt_parts = []

            if system_content:
                prompt_parts.append(f"<|im_start|>system\n{system_content}<|im_end|>")

            prompt_parts.append(f"<|im_start|>user\n{user_content}<|im_end|>")
            prompt_parts.append("<|im_start|>assistant\n")

            return "\n".join(prompt_parts)

        def doc_to_target(self, doc):
            """Extract assistant message as target (expected response)."""
            messages = doc.get("messages", [])
            _, _, assistant_content = extract_chat_parts(messages)
            return assistant_content or ""

        def construct_requests(self, doc, ctx, **kwargs):
            """Create generation and loglikelihood requests for metrics + perplexity."""
            kwargs.pop("apply_chat_template", None)
            kwargs.pop("chat_template", None)
            target = self.doc_to_target(doc)
            return [
                Instance(
                    request_type="generate_until",
                    doc=doc,
                    arguments=(
                        ctx,
                        {
                            "until": ["<|im_end|>", "<|endoftext|>", "</s>", "<|end|>", "\n\nUser:", "\n\nHuman:"],
                            "max_gen_toks": self.max_gen_toks,
                        },
                    ),
                    idx=0,
                    **kwargs,
                ),
                Instance(
                    request_type="loglikelihood",
                    doc=doc,
                    arguments=(ctx, target),
                    idx=1,
                    **kwargs,
                ),
            ]

        def process_results(self, doc, results):
            """Calculate metrics between prediction and target, plus perplexity."""
            import sacrebleu
            import math
            from rouge_score import rouge_scorer

            generated_text = results[0]
            loglik_result = results[1]

            prediction = generated_text.strip()
            target = self.doc_to_target(doc).strip()

            # Calculate perplexity from loglikelihood
            try:
                logprob = loglik_result[0] if isinstance(loglik_result, tuple) else loglik_result
                num_tokens = max(len(target.split()), 1)
                perplexity = math.exp(-logprob / num_tokens) if logprob < 0 else math.exp(-logprob)
                perplexity = min(perplexity, 10000.0)
                nll = -logprob / num_tokens if logprob < 0 else -logprob
            except Exception:
                perplexity = 10000.0
                nll = 10.0

            if self.log_prompts:
                try:
                    self.prompts_log.append(
                        {
                            "prompt": self.doc_to_text(doc),
                            "target": target,
                            "prediction": prediction,
                        }
                    )
                except Exception:
                    pass

            exact_match = 1.0 if prediction.lower() == target.lower() else 0.0

            target_start = target.lower()[:50] if len(target) > 50 else target.lower()
            contains_match = 1.0 if target_start in prediction.lower() else 0.0

            try:
                bleu = sacrebleu.sentence_bleu(prediction, [target]).score / 100.0
            except Exception:
                bleu = 0.0

            try:
                scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
                rouge_scores = scorer.score(target, prediction)
                rouge1 = rouge_scores["rouge1"].fmeasure
                rouge2 = rouge_scores["rouge2"].fmeasure
                rougeL = rouge_scores["rougeL"].fmeasure
            except Exception:
                rouge1 = 0.0
                rouge2 = 0.0
                rougeL = 0.0

            pred_words = set(prediction.lower().split())
            target_words = set(target.lower().split())
            if pred_words and target_words:
                overlap = len(pred_words & target_words)
                precision = overlap / len(pred_words) if pred_words else 0
                recall = overlap / len(target_words) if target_words else 0
                f1_overlap = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            else:
                f1_overlap = 0.0

            return {
                "exact_match": exact_match,
                "contains_match": contains_match,
                "bleu": bleu,
                "rouge1": rouge1,
                "rouge2": rouge2,
                "rougeL": rougeL,
                "f1_overlap": f1_overlap,
                "perplexity": perplexity,
                "loss": nll,
            }

        def aggregation(self):
            return {
                "exact_match": mean,
                "contains_match": mean,
                "bleu": mean,
                "rouge1": mean,
                "rouge2": mean,
                "rougeL": mean,
                "f1_overlap": mean,
                "perplexity": mean,
                "loss": mean,
            }

        def should_decontaminate(self):
            return False

        def doc_to_prefix(self, doc):
            return ""

        def higher_is_better(self):
            return {
                "exact_match": True,
                "contains_match": True,
                "bleu": True,
                "rouge1": True,
                "rouge2": True,
                "rougeL": True,
                "f1_overlap": True,
                "perplexity": False,
                "loss": False,
            }

    # =========================================================================
    # Main Evaluation Logic
    # =========================================================================

    # --- 2. Resolve Model Path ---
    final_model_path = None
    if model_artifact:
        meta = getattr(model_artifact, "metadata", {}) or {}
        pvc_model_dir = meta.get("pvc_model_dir")
        if pvc_model_dir and os.path.isdir(pvc_model_dir):
            logger.info(f"Using model from PVC path (via metadata): {pvc_model_dir}")
            final_model_path = pvc_model_dir
        elif os.path.isdir(model_artifact.path):
            logger.info(f"Using model from artifact path: {model_artifact.path}")
            final_model_path = model_artifact.path
        else:
            logger.warning(f"Artifact path not found: {model_artifact.path}, checking metadata...")
            if pvc_model_dir:
                logger.info(f"Falling back to PVC path from metadata: {pvc_model_dir}")
                final_model_path = pvc_model_dir

    if not final_model_path and model_path:
        logger.info(f"Using model from string path/ID: {model_path}")
        final_model_path = model_path

    if not final_model_path:
        raise ValueError("No model provided! You must pass either 'model_path' (string) or 'model_artifact' (input).")

    # Verify model directory has config.json (required by vLLM)
    config_path = os.path.join(final_model_path, "config.json")
    if not os.path.exists(config_path):
        logger.error(f"Model directory missing config.json: {final_model_path}")
        logger.error(
            f"Directory contents: {os.listdir(final_model_path) if os.path.isdir(final_model_path) else 'NOT A DIRECTORY'}"
        )
        raise ValueError(f"Invalid model directory - no config.json found at {final_model_path}")

    # --- 3. Prepare eval dataset info and custom task ---
    eval_dataset_info = {}
    eval_jsonl_path = None
    custom_task = None
    prompt_response_log = []

    if eval_dataset:
        eval_meta = getattr(eval_dataset, "metadata", {}) or {}
        eval_dataset_info = {
            "num_examples": eval_meta.get("num_examples", "unknown"),
            "split": eval_meta.get("split", "eval"),
            "pvc_path": eval_meta.get("pvc_path", eval_dataset.path),
        }
        logger.info(
            f"Eval dataset: {eval_dataset_info['num_examples']} examples from {eval_dataset_info['split']} split"
        )
        logger.info(f"Eval dataset path: {eval_dataset_info['pvc_path']}")

        candidate_paths = [
            eval_dataset_info["pvc_path"],
            eval_dataset.path,
        ]

        for candidate in candidate_paths:
            if candidate and os.path.exists(candidate):
                if os.path.isfile(candidate):
                    eval_jsonl_path = candidate
                    break
                elif os.path.isdir(candidate):
                    for f in os.listdir(candidate):
                        if f.endswith(".jsonl") or f.endswith(".json"):
                            eval_jsonl_path = os.path.join(candidate, f)
                            break
                    if eval_jsonl_path:
                        break

        if eval_jsonl_path and os.path.exists(eval_jsonl_path):
            logger.info(f"Found eval JSONL for custom evaluation: {eval_jsonl_path}")

            try:
                with open(eval_jsonl_path, "r") as f:
                    sample_data = []
                    for i, line in enumerate(f):
                        if i >= 10:
                            break
                        line = line.strip()
                        if line:
                            sample_data.append(json.loads(line))

                is_valid, valid_count, error_msg = validate_chat_format(sample_data, logger)

                if not is_valid:
                    logger.error("=" * 60)
                    logger.error("CUSTOM EVAL SKIPPED - Invalid dataset format!")
                    logger.error("=" * 60)
                    logger.error(f"Error: {error_msg}")
                else:
                    logger.info(f"Dataset format validated: {valid_count}/10 samples checked OK")
                    custom_task = ChatHoldoutTask(
                        dataset_path=eval_jsonl_path,
                        task_name="custom_holdout_eval",
                        max_gen_toks=custom_eval_max_tokens,
                        log_prompts=log_samples,
                        prompts_log=prompt_response_log,
                    )
                    logger.info("Custom holdout evaluation task created")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse eval dataset as JSONL: {e}")
            except Exception as e:
                logger.error(f"Error validating eval dataset: {e}")
        else:
            logger.warning("Could not find eval JSONL file for custom evaluation. Skipping custom eval.")

    # --- 4. Input Sanitization ---
    def parse_input(val, default):
        if val is None:
            return default
        if isinstance(val, str):
            try:
                return json.loads(val)
            except:
                return val
        return val

    tasks_list = parse_input(task_names, [])
    m_args = parse_input(model_args, {})
    g_kwargs = parse_input(gen_kwargs, {})
    limit_val = None if limit == -1 else limit

    # --- 5. Build task dict ---
    task_dict = {}

    if tasks_list:
        logger.info(f"Adding benchmark tasks: {tasks_list}")
        benchmark_task_dict = get_task_dict(tasks_list)
        task_dict.update(benchmark_task_dict)

    if custom_task:
        task_dict["custom_holdout_eval"] = custom_task
        logger.info("Added custom holdout task to evaluation")

    if not task_dict:
        raise ValueError("No tasks to evaluate! Provide task_names or eval_dataset.")

    logger.info(f"Total tasks to evaluate: {len(task_dict)}")

    # --- 6. Load Model ---
    logger.info("Loading model with vLLM backend...")
    start_time = time.time()

    try:
        vllm_model_args = {
            "pretrained": final_model_path,
            "trust_remote_code": True,
            "gpu_memory_utilization": 0.8,
            "dtype": "auto",
        }
        vllm_model_args.update(m_args)

        model_class = get_model("vllm")

        if batch_size == "auto":
            bs = "auto"
        else:
            try:
                bs = int(batch_size)
            except:
                bs = "auto"

        additional_config = {
            "batch_size": bs,
            "device": None,
        }

        loaded_model = model_class.create_from_arg_obj(vllm_model_args, additional_config)
        logger.info(f"Model loaded successfully in {time.time() - start_time:.2f}s")
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise RuntimeError(f"Model loading failed: {e}")

    # --- 7. Run Evaluation ---
    logger.info("Starting evaluation...")
    start_time = time.time()

    try:
        results = evaluate(
            lm=loaded_model,
            task_dict=task_dict,
            limit=limit_val,
            verbosity=verbosity,
        )
    except Exception as e:
        logger.error(f"Evaluation failed: {str(e)}")
        raise RuntimeError(f"Fatal error in evaluation: {e}")

    duration = time.time() - start_time
    logger.info(f"Evaluation completed in {duration:.2f}s")

    # --- 8. Output Processing ---
    def clean_for_json(obj):
        if isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        elif hasattr(obj, "item"):
            return obj.item()
        elif isinstance(obj, dict):
            return {k: clean_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean_for_json(item) for item in obj]
        return str(obj)

    clean_results = clean_for_json(results)

    # --- Log Evaluation Metadata ---
    output_metrics.log_metric("eval_duration_seconds", round(duration, 2))
    output_metrics.log_metric("eval_tasks_count", len(task_dict))

    custom_eval_ran = custom_task is not None and "custom_holdout_eval" in str(clean_results.get("results", {}))
    output_metrics.log_metric("custom_eval_enabled", 1 if custom_eval_ran else 0)

    try:
        output_metrics.metadata["eval_benchmark_tasks"] = ",".join(tasks_list)
        output_metrics.metadata["eval_custom_task"] = "custom_holdout_eval" if custom_task else "none"
        output_metrics.metadata["eval_model_path"] = final_model_path
        output_metrics.metadata["eval_batch_size"] = str(batch_size)
        output_metrics.metadata["eval_limit"] = str(limit_val) if limit_val else "all"
        if eval_dataset_info:
            output_metrics.metadata["eval_dataset_examples"] = str(eval_dataset_info.get("num_examples", ""))
            output_metrics.metadata["eval_dataset_path"] = eval_dataset_info.get("pvc_path", "")
            output_metrics.metadata["eval_custom_data_used"] = "true" if custom_eval_ran else "false"
    except Exception as e:
        logger.warning(f"Could not set metadata: {e}")

    # --- Log Task Metrics ---
    if "results" in clean_results:
        for task_name, metrics in clean_results["results"].items():
            display_name = metrics.get("alias", task_name)

            if task_name == "custom_holdout_eval":
                prefix = "holdout"
                logger.info("=== CUSTOM HOLDOUT EVALUATION RESULTS ===")
            else:
                prefix = display_name

            for key, value in metrics.items():
                if isinstance(value, (int, float)) and key != "alias":
                    safe_key = f"{prefix}_{key}".replace(" ", "_").replace("/", "_")
                    output_metrics.log_metric(safe_key, value)

                    if task_name == "custom_holdout_eval":
                        logger.info(f"  {key}: {value:.4f}" if isinstance(value, float) else f"  {key}: {value}")

        if custom_eval_ran and "custom_holdout_eval" in clean_results["results"]:
            custom_results = clean_results["results"]["custom_holdout_eval"]
            exact_match = custom_results.get("exact_match,none", custom_results.get("exact_match", "N/A"))
            contains_match = custom_results.get("contains_match,none", custom_results.get("contains_match", "N/A"))
            logger.info(f"=== HOLDOUT EXACT MATCH: {exact_match} ===")
            logger.info(f"=== HOLDOUT CONTAINS MATCH: {contains_match} ===")
            logger.info("This metric shows how well the model performs on YOUR held-out data.")

    # --- Save Artifacts ---
    output_results.name = "eval_results.json"
    with open(output_results.path, "w") as f:
        json.dump(clean_results, f, indent=2)

    if log_samples and custom_task and len(prompt_response_log) > 0:
        try:
            output_samples.name = "eval_samples.json"
            with open(output_samples.path, "w") as f:
                json.dump(prompt_response_log, f, indent=2)
            logger.info(f"Prompt/response log saved with {len(prompt_response_log)} samples")
        except Exception as e:
            logger.warning(f"Failed to save prompt/response log: {e}")
    elif log_samples and "samples" in clean_results:
        output_samples.name = "eval_samples.json"
        with open(output_samples.path, "w") as f:
            json.dump(clean_results["samples"], f, indent=2)


if __name__ == "__main__":
    kfp.compiler.Compiler().compile(universal_llm_evaluator, package_path="universal_llm_evaluator.yaml")
