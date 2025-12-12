# Base Image Validation

Validate base images used in Kubeflow Pipelines components and pipelines.

## Run

From the repo root:

```bash
uv run python scripts/validate_base_images/validate_base_images.py
```

## Validate specific assets only

Validate a single component (directory or `component.py`):

```bash
uv run python scripts/validate_base_images/validate_base_images.py \
  --component components/training/sample_model_trainer
```

Validate a single pipeline (directory or `pipeline.py`):

```bash
uv run python scripts/validate_base_images/validate_base_images.py \
  --pipeline pipelines/training/simple_training
```

Validate multiple targets (repeat the flags):

```bash
uv run python scripts/validate_base_images/validate_base_images.py \
  --component components/training/sample_model_trainer \
  --component components/evaluation/some_component \
  --pipeline pipelines/training/simple_training
```
