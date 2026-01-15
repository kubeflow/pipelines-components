# Lm Eval ✨

> ⚠️ **Stability: experimental** — This asset is not yet stable and may change.

## Overview 🧾

A Universal LLM Evaluator component using EleutherAI's lm-evaluation-harness.

Supports two types of evaluation:

1. Benchmark evaluation: Standard lm-eval tasks (arc_easy, mmlu, gsm8k, etc.)
2. Custom holdout evaluation: When eval_dataset is provided, evaluates on your held-out data

## Inputs 📥

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `output_metrics` | `dsl.Output[dsl.Metrics]` | `None` | Output metrics artifact with evaluation scores. |
| `output_results` | `dsl.Output[dsl.Artifact]` | `None` | Output artifact containing full evaluation results JSON. |
| `output_samples` | `dsl.Output[dsl.Artifact]` | `None` | Output artifact containing logged evaluation samples. |
| `task_names` | `list` | `None` | List of benchmark task names (e.g. ["mmlu", "gsm8k"]). |
| `model_path` | `str` | `None` | String path or HF ID. Used if model_artifact is None. |
| `model_artifact` | `dsl.Input[dsl.Model]` | `None` | KFP Model artifact from a previous pipeline step. |
| `eval_dataset` | `dsl.Input[dsl.Dataset]` | `None` | JSONL dataset in chat format for custom holdout evaluation. |
| `model_args` | `dict` | `{}` | Dictionary for model initialization (e.g. {"dtype": "float16"}). |
| `gen_kwargs` | `dict` | `{}` | Dictionary of generation kwargs passed to the model. |
| `batch_size` | `str` | `auto` | Batch size for evaluation ("auto" or integer). |
| `limit` | `int` | `-1` | Limit number of examples per task (-1 for no limit). |
| `log_samples` | `bool` | `True` | Whether to log individual evaluation samples. |
| `verbosity` | `str` | `INFO` | Logging verbosity level (DEBUG, INFO, WARNING, ERROR). |
| `custom_eval_max_tokens` | `int` | `256` | Max tokens for generation in custom eval (default: 256). |

## Metadata 🗂️

- **Name**: lm_eval
- **Stability**: experimental
- **Dependencies**:
  - Kubeflow:
    - Name: Pipelines, Version: >=2.15.2
  - External Services:
    - Name: lm-evaluation-harness, Version: >=0.4.0
    - Name: vLLM, Version: >=0.4.0
- **Tags**:
  - evaluation
  - llm
  - lm_eval
  - benchmarks
  - metrics
- **Last Verified**: 2026-01-14 00:00:00+00:00
- **Owners**:
  - Approvers:
    - briangallagher
    - Fiona-Waters
    - kramaranya
    - MStokluska
    - szaher

## Additional Resources 📚

- **Documentation**: [https://github.com/EleutherAI/lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness)
