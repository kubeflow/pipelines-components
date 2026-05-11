# Yoda Data Processor ✨

> ⚠️ **Stability: alpha** — This asset is not yet stable and may change.

## Overview 🧾

Prepare the training and evaluation datasets by downloading and preprocessing.

Downloads the yoda_sentences dataset from HuggingFace, renames columns to match the expected format for training
(prompt/completion), splits into train/eval sets, and saves them as output artifacts.

## Inputs 📥

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `yoda_train_dataset` | `dsl.Output[dsl.Dataset]` | `None` | Output dataset for training. |
| `yoda_eval_dataset` | `dsl.Output[dsl.Dataset]` | `None` | Output dataset for evaluation. |
| `yoda_input_dataset` | `str` | `dvgodoy/yoda_sentences` | Dataset to download from HuggingFace |
| `train_split_ratio` | `float` | `0.8` | Ratio for training (0.0-1.0), defaults to 0.8 |

## Metadata 🗂️

See [metadata.yaml](metadata.yaml) for the component's tags, dependencies, owners, and last verification date.

## Additional Resources 📚

- **Dataset**: [https://huggingface.co/datasets/dvgodoy/yoda_sentences](https://huggingface.co/datasets/dvgodoy/yoda_sentences)
