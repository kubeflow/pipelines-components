# Base Image Validation

Validate base images used in Kubeflow Pipelines components and pipelines.

## Run

From the repo root:

```bash
uv run scripts/validate_base_images/validate_base_images.py
```

## Allowlist

The validator accepts:

- `ghcr.io/kubeflow/*` images
- unset/empty images
- images matching the allowlist file: `scripts/validate_base_images/base_image_allowlist.yaml`

To update the allowlist, edit `scripts/validate_base_images/base_image_allowlist.yaml` and add either:

- `allowed_images`: exact image strings
- `allowed_image_patterns`: regex patterns matched against the full image string

To use a different allowlist file:

```bash
uv run scripts/validate_base_images/validate_base_images.py \
  --allow-list /path/to/allowlist.yaml
```

## Validate specific assets only

Validate a single component (directory or `component.py`):

```bash
uv run scripts/validate_base_images/validate_base_images.py \
  --component components/training/sample_model_trainer
```

Validate a single pipeline (directory or `pipeline.py`):

```bash
uv run scripts/validate_base_images/validate_base_images.py \
  --pipeline pipelines/training/simple_training
```

Validate multiple targets (repeat the flags):

```bash
uv run scripts/validate_base_images/validate_base_images.py \
  --component components/training/sample_model_trainer \
  --component components/evaluation/some_component \
  --pipeline pipelines/training/simple_training
```
