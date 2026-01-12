"""Training Component.

Reusable inline training component modeled after the OSFT notebook flow.
- Configurable logging
- Optional Kubernetes connection (remote or in-cluster)
- PVC-based caches/checkpoints
- Dataset resolution (HF repo id, or local path)
- Basic metrics logging and checkpoint export
"""

from kfp import dsl
from typing import Optional


@dsl.component(
    base_image="quay.io/opendatahub/odh-training-th04-cpu-torch29-py312-rhel9:latest-cpu",
    packages_to_install=[
        "kubernetes",
        "olot",
    ],
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
    # Workspace/PVC root (pass dsl.WORKSPACE_PATH_PLACEHOLDER at call site)
    pvc_path: str,
    # Outputs (no defaults)
    output_model: dsl.Output[dsl.Model],
    output_metrics: dsl.Output[dsl.Metrics],
    # Dataset input and optional remote artifact path via metadata (e.g., s3://...)
    dataset: dsl.Input[dsl.Dataset] = None,
    # Base model (HF ID or local path)
    training_base_model: str = "Qwen/Qwen2.5-1.5B-Instruct",
    # Training algorithm selector
    training_algorithm: str = "OSFT",
    # ------------------------------
    # Common params (used by both OSFT and SFT)
    # ------------------------------
    training_effective_batch_size: int = 128,
    training_max_tokens_per_gpu: int = 64000,
    training_max_seq_len: int = 8192,
    training_learning_rate: Optional[float] = None,
    training_backend: str = "mini-trainer",
    training_lr_warmup_steps: Optional[int] = None,
    training_checkpoint_at_epoch: Optional[bool] = None,
    training_num_epochs: Optional[int] = None,
    training_data_output_dir: Optional[str] = None,
    # HuggingFace token for gated models (optional - leave empty if not needed)
    training_hf_token: str = "",
    # Pull secret for registry.redhat.io in Docker config.json format (optional)
    training_pull_secret: str = "",
    # Env overrides: "KEY=VAL,KEY=VAL"
    training_envs: str = "",
    # Resource and runtime parameters (per worker/pod)
    training_resource_cpu_per_worker: str = "8",
    training_resource_gpu_per_worker: int = 1,
    training_resource_memory_per_worker: str = "32Gi",
    training_resource_num_procs_per_worker: str = "auto",
    training_resource_num_workers: int = 1,
    training_metadata_labels: str = "",
    training_metadata_annotations: str = "",
    # ------------------------------
    # OSFT-only params (see ai-innovation/training_hub/src/training_hub/algorithms/osft.py)
    # ------------------------------
    training_unfreeze_rank_ratio: float = 0.25,
    training_osft_memory_efficient_init: bool = True,
    training_target_patterns: str = "",
    training_seed: Optional[int] = None,
    training_use_liger: Optional[bool] = None,
    training_use_processed_dataset: Optional[bool] = None,
    training_unmask_messages: Optional[bool] = None,
    training_lr_scheduler: Optional[str] = None,
    training_lr_scheduler_kwargs: str = "",
    training_save_final_checkpoint: Optional[bool] = None,
    # ------------------------------
    # SFT-only params (see ai-innovation/training_hub/src/training_hub/algorithms/sft.py)
    # ------------------------------
    training_save_samples: Optional[int] = None,
    training_accelerate_full_state_at_epoch: Optional[bool] = None,
    # FSDP sharding strategy: FULL_SHARD, HYBRID_SHARD, NO_SHARD
    training_fsdp_sharding_strategy: Optional[str] = None,
    # KFP TaskConfig passthrough for volumes/env/resources, etc.
    kubernetes_config: dsl.TaskConfig = None,
) -> str:
    """Train model using TrainingHub (OSFT/SFT). Outputs model artifact and metrics.

    Args:
        pvc_path: Workspace PVC root path (use dsl.WORKSPACE_PATH_PLACEHOLDER).
        output_model: Output model artifact.
        output_metrics: Output training metrics artifact.
        dataset: Input training dataset artifact.
        training_base_model: Base model (HuggingFace ID or local path).
        training_algorithm: Training algorithm: OSFT or SFT.
        training_effective_batch_size: Effective batch size per optimizer step.
        training_max_tokens_per_gpu: Max tokens per GPU (memory cap).
        training_max_seq_len: Max sequence length in tokens.
        training_learning_rate: Learning rate (default: 5e-6).
        training_backend: Backend: mini-trainer (OSFT) or instructlab-training (SFT).
        training_lr_warmup_steps: Learning rate warmup steps.
        training_checkpoint_at_epoch: Save checkpoint at each epoch.
        training_num_epochs: Number of training epochs.
        training_data_output_dir: Directory for processed training data.
        training_hf_token: HuggingFace token for gated models.
        training_pull_secret: Pull secret for container registry.
        training_envs: Environment overrides as KEY=VAL,KEY=VAL.
        training_resource_cpu_per_worker: CPU cores per worker.
        training_resource_gpu_per_worker: GPUs per worker.
        training_resource_memory_per_worker: Memory per worker (e.g., 32Gi).
        training_resource_num_procs_per_worker: Processes per worker (auto or int).
        training_resource_num_workers: Number of training pods.
        training_metadata_labels: Pod labels as key=value,key=value.
        training_metadata_annotations: Pod annotations as key=value,key=value.
        training_unfreeze_rank_ratio: [OSFT] Fraction of parameters to unfreeze.
        training_osft_memory_efficient_init: [OSFT] Use memory-efficient initialization.
        training_target_patterns: [OSFT] Target layer patterns (comma-separated).
        training_seed: Random seed for reproducibility.
        training_use_liger: Enable Liger kernel optimizations.
        training_use_processed_dataset: Use pre-processed dataset.
        training_unmask_messages: Unmask assistant messages during training.
        training_lr_scheduler: LR scheduler type (cosine, linear, etc.).
        training_lr_scheduler_kwargs: LR scheduler kwargs as key=val,key=val.
        training_save_final_checkpoint: Save final checkpoint after training.
        training_save_samples: [SFT] Number of samples to save.
        training_accelerate_full_state_at_epoch: [SFT] Save full accelerate state.
        training_fsdp_sharding_strategy: [SFT] FSDP sharding strategy.
        kubernetes_config: KFP TaskConfig for volumes/env/resources passthrough.
    """
    import os, sys, json, time, logging, re, subprocess, shutil
    from typing import Dict, List, Tuple, Optional as _Optional

    # ------------------------------
    # Logging configuration
    # ------------------------------
    def _setup_logger() -> logging.Logger:
        """Configure and return a logger for this component."""
        _logger = logging.getLogger("train_model")
        _logger.setLevel(logging.INFO)
        if not _logger.handlers:
            _ch = logging.StreamHandler(sys.stdout)
            _ch.setLevel(logging.INFO)
            _ch.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
            _logger.addHandler(_ch)
        return _logger

    logger = _setup_logger()
    logger.info("Initializing training component")
    logger.info(f"pvc_path={pvc_path}, model_name={training_base_model}")

    # ------------------------------
    # Utility: find model directory (with config.json)
    # ------------------------------
    def find_model_directory(checkpoints_root: str) -> _Optional[str]:
        """Find the actual model directory containing config.json.

        Searches recursively for a directory with config.json, prioritizing
        the most recently modified one. Handles nested checkpoint structures
        like: checkpoints/epoch-1/samples_90.0/config.json
        """
        if not os.path.isdir(checkpoints_root):
            return None

        candidates: list = []
        for root, dirs, files in os.walk(checkpoints_root):
            if "config.json" in files:
                try:
                    mtime = os.path.getmtime(os.path.join(root, "config.json"))
                    candidates.append((mtime, root))
                except OSError:
                    continue

        if not candidates:
            # Fallback: return most recent top-level directory
            latest: _Optional[Tuple[float, str]] = None
            for entry in os.listdir(checkpoints_root):
                full = os.path.join(checkpoints_root, entry)
                if os.path.isdir(full):
                    try:
                        mtime = os.path.getmtime(full)
                    except OSError:
                        continue
                    if latest is None or mtime > latest[0]:
                        latest = (mtime, full)
            return latest[1] if latest else None

        # Return the most recently modified model directory
        candidates.sort(reverse=True)
        return candidates[0][1]

    # ------------------------------
    # Kubernetes connection
    # ------------------------------
    def _init_k8s_client() -> _Optional["k8s_client.ApiClient"]:
        """Initialize and return a Kubernetes client from env (server/token) or in-cluster/kubeconfig."""
        try:
            from kubernetes import client as k8s_client, config as k8s_config

            env_server = os.environ.get("KUBERNETES_SERVER_URL", "").strip()
            env_token = os.environ.get("KUBERNETES_AUTH_TOKEN", "").strip()
            if env_server and env_token:
                logger.info("Configuring Kubernetes client from env (KUBERNETES_SERVER_URL/_AUTH_TOKEN)")
                cfg = k8s_client.Configuration()
                cfg.host = env_server
                cfg.verify_ssl = False
                cfg.api_key = {"authorization": f"Bearer {env_token}"}
                k8s_client.Configuration.set_default(cfg)
                return k8s_client.ApiClient(cfg)
            logger.info("Configuring Kubernetes client in-cluster (or local kubeconfig)")
            try:
                k8s_config.load_incluster_config()
            except Exception:
                k8s_config.load_kube_config()
            return k8s_client.ApiClient()
        except Exception as _exc:
            logger.warning(f"Kubernetes client not initialized: {_exc}")
            return None

    _api_client = _init_k8s_client()

    # ------------------------------
    # Environment variables (defaults + overrides)
    # ------------------------------
    cache_root = os.path.join(pvc_path, ".cache", "huggingface")
    default_env: Dict[str, str] = {
        "XDG_CACHE_HOME": "/tmp",
        "TRITON_CACHE_DIR": "/tmp/.triton",
        "HF_HOME": "/tmp/.cache/huggingface",
        "HF_DATASETS_CACHE": os.path.join(cache_root, "datasets"),
        "TRANSFORMERS_CACHE": os.path.join(cache_root, "transformers"),
        "NCCL_DEBUG": "INFO",
    }

    def parse_kv_list(kv_str: str) -> Dict[str, str]:
        out: Dict[str, str] = {}
        if not kv_str:
            return out
        for item in kv_str.split(","):
            item = item.strip()
            if not item:
                continue
            if "=" not in item:
                raise ValueError(f"Invalid key=value item (expected key=value): {item}")
            k, v = item.split("=", 1)
            k = k.strip()
            v = v.strip()
            if not k:
                raise ValueError(f"Invalid key in key=value pair: {item}")
            out[k] = v
        return out

    def _configure_env(env_csv: str, base_env: Dict[str, str]) -> Dict[str, str]:
        """Merge base env with CSV overrides and export them to process env; return merged map."""
        overrides = parse_kv_list(env_csv)
        merged = {**base_env, **overrides}
        for ek, ev in merged.items():
            os.environ[ek] = ev
        logger.info(f"Env configured (keys): {sorted(list(merged.keys()))}")
        return merged

    merged_env = _configure_env(training_envs, default_env)

    # Add HuggingFace token to environment if provided
    if training_hf_token and training_hf_token.strip():
        merged_env["HF_TOKEN"] = training_hf_token.strip()
        os.environ["HF_TOKEN"] = training_hf_token.strip()
        logger.info("HF_TOKEN added to environment (for gated model access)")

    # ------------------------------
    # Dataset resolution
    # ------------------------------
    from datasets import load_dataset, load_from_disk, Dataset

    resolved_dataset_dir = os.path.join(pvc_path, "dataset", "train")
    os.makedirs(resolved_dataset_dir, exist_ok=True)

    def is_local_path(p: str) -> bool:
        return bool(p) and os.path.exists(p)

    def looks_like_url(p: str) -> bool:
        return p.startswith("s3://") or p.startswith("http://") or p.startswith("https://")

    def _resolve_dataset(input_dataset: _Optional[dsl.Input[dsl.Dataset]], out_dir: str) -> None:
        """Resolve dataset with preference: existing PVC dir > input artifact > remote artifact/HF > default.
        Remote path is read from input_dataset.metadata['artifact_path'] if present. If metadata['pvc_dir'] exists, prefer it.
        """
        # 0) If already present (e.g., staged by prior step), keep it
        if os.path.isdir(out_dir) and any(os.scandir(out_dir)):
            logger.info(f"Using existing dataset at {out_dir}")
            return
        # 1) Input artifact (can be a file or directory)
        if input_dataset and getattr(input_dataset, "path", None) and os.path.exists(input_dataset.path):
            src_path = input_dataset.path
            if os.path.isdir(src_path):
                logger.info(f"Copying input dataset directory from {src_path} to {out_dir}")
                shutil.copytree(src_path, out_dir, dirs_exist_ok=True)
            else:
                # It's a file (e.g., JSONL) - copy to out_dir with appropriate name
                logger.info(f"Copying input dataset file from {src_path} to {out_dir}")
                dst_file = os.path.join(out_dir, os.path.basename(src_path))
                # If basename doesn't have extension, assume it's a jsonl file
                if not os.path.splitext(dst_file)[1]:
                    dst_file = os.path.join(out_dir, "train.jsonl")
                shutil.copy2(src_path, dst_file)
                logger.info(f"Dataset file copied to {dst_file}")
            return
        # 2) Remote artifact (S3/HTTP) or HF repo id
        rp = ""
        try:
            if input_dataset and hasattr(input_dataset, "metadata") and isinstance(input_dataset.metadata, dict):
                pvc_path_meta = (
                    input_dataset.metadata.get("pvc_path") or input_dataset.metadata.get("pvc_dir") or ""
                ).strip()
                if pvc_path_meta and os.path.exists(pvc_path_meta):
                    if os.path.isdir(pvc_path_meta) and any(os.scandir(pvc_path_meta)):
                        logger.info(f"Using pre-staged PVC dataset directory at {pvc_path_meta}")
                        shutil.copytree(pvc_path_meta, out_dir, dirs_exist_ok=True)
                        return
                    elif os.path.isfile(pvc_path_meta):
                        logger.info(f"Using pre-staged PVC dataset file at {pvc_path_meta}")
                        dst_file = os.path.join(out_dir, os.path.basename(pvc_path_meta))
                        if not os.path.splitext(dst_file)[1]:
                            dst_file = os.path.join(out_dir, "train.jsonl")
                        shutil.copy2(pvc_path_meta, dst_file)
                        return
                rp = (input_dataset.metadata.get("artifact_path") or "").strip()
        except Exception:
            rp = ""
        if rp:
            if looks_like_url(rp):
                logger.info(f"Attempting to load remote dataset from {rp}")
                # Try a few common formats via datasets library
                ext = rp.lower()
                try:
                    if ext.endswith(".json") or ext.endswith(".jsonl"):
                        ds: Dataset = load_dataset("json", data_files=rp, split="train")
                    elif ext.endswith(".parquet"):
                        ds: Dataset = load_dataset("parquet", data_files=rp, split="train")
                    else:
                        raise ValueError(
                            "Unsupported remote dataset format. Provide a JSON/JSONL/PARQUET file or a HF dataset repo id."
                        )
                    ds.save_to_disk(out_dir)
                    return
                except Exception as e:
                    raise ValueError(f"Failed to load remote dataset from {rp}: {e}")
            else:
                # Treat as HF dataset repo id
                logger.info(f"Assuming HF dataset repo id: {rp}")
                ds: Dataset = load_dataset(rp, split="train")
                ds.save_to_disk(out_dir)
                return
        # 3) No fallback: require an explicit dataset source
        raise ValueError(
            "No dataset provided or resolvable. Please supply an input artifact, a PVC path via metadata "
            "('pvc_path' or 'pvc_dir'), or a remote source via metadata['artifact_path'] (S3/HTTP/HF repo id)."
        )

    _resolve_dataset(dataset, resolved_dataset_dir)

    # Export dataset to JSONL so downstream trainer reads a plain JSONL file
    jsonl_path = os.path.join(resolved_dataset_dir, "train.jsonl")
    try:
        # Try loading from the saved HF dataset on disk and export to JSONL
        ds_on_disk = load_from_disk(resolved_dataset_dir)
        # Handle DatasetDict vs Dataset
        train_split = ds_on_disk["train"] if isinstance(ds_on_disk, dict) else ds_on_disk
        try:
            # Newer datasets supports native JSON export
            train_split.to_json(jsonl_path, lines=True)
            logger.info(f"Wrote JSONL to {jsonl_path} via to_json")
        except AttributeError:
            # Manual JSONL write
            import json as _json

            with open(jsonl_path, "w") as _f:
                for _rec in train_split:
                    _f.write(_json.dumps(_rec, ensure_ascii=False) + "\n")
            logger.info(f"Wrote JSONL to {jsonl_path} via manual dump")
    except Exception as _e:
        logger.warning(f"Failed to export JSONL dataset at {resolved_dataset_dir}: {_e}")
        # Leave jsonl_path as default; downstream will fallback to directory if file not present

    # ------------------------------
    # Model resolution (supports HF ID/local path or oci:// registry ref)
    # ------------------------------
    def _skopeo_copy_to_dir(oci_ref: str, dest_dir: str, auth_json: str | None = None) -> None:
        """Use skopeo to copy a registry image to a plain directory ('dir:' transport)."""
        os.makedirs(dest_dir, exist_ok=True)
        authfile_path = None
        try:
            if auth_json:
                authfile_path = "/tmp/skopeo-auth.json"
                with open(authfile_path, "w") as f:
                    f.write(auth_json)
        except Exception as e:
            logger.warning(f"Failed to prepare skopeo auth file: {e}")
            authfile_path = None
        # skopeo syntax: skopeo copy [--authfile FILE] docker://REF dir:DESTDIR
        cmd = ["skopeo", "copy"]
        if authfile_path:
            cmd.extend(["--authfile", authfile_path])
        cmd.extend([f"docker://{oci_ref}", f"dir:{dest_dir}"])
        logger.info(f"Running: {' '.join(cmd)}")
        res = subprocess.run(cmd, text=True, capture_output=True)
        if res.returncode != 0:
            stderr = (res.stderr or "").strip()
            logger.error(f"skopeo copy failed (exit={res.returncode}): {stderr}")
            if "unauthorized" in stderr.lower() or "authentication required" in stderr.lower():
                logger.error(
                    "Authentication error detected pulling from registry. "
                    "Provide credentials via --authfile or mounted Docker config."
                )
            res.check_returncode()
        else:
            out_preview = "\n".join((res.stdout or "").splitlines()[-20:])
            if out_preview:
                logger.info(f"skopeo copy output (tail):\n{out_preview}")

    def _extract_models_from_dir_image(image_dir: str, out_dir: str) -> List[str]:
        """Extract 'models/' subtree from skopeo dir transport output into out_dir."""
        import tarfile

        os.makedirs(out_dir, exist_ok=True)
        extracted: List[str] = []
        logger.info(f"Extracting 'models/' from dir image {image_dir} to {out_dir}")
        try:
            for fname in os.listdir(image_dir):
                fpath = os.path.join(image_dir, fname)
                if not os.path.isfile(fpath):
                    continue
                if fname.endswith(".json") or fname in {"manifest", "index.json"}:
                    continue
                try:
                    with tarfile.open(fpath, mode="r:*") as tf:
                        for member in tf.getmembers():
                            if member.isfile() and member.name.startswith("models/"):
                                tf.extract(member, path=out_dir)
                                extracted.append(member.name)
                except tarfile.ReadError:
                    continue
                except Exception as _e:
                    logger.warning(f"Failed to extract from {fname}: {_e}")
        except Exception as e:
            logger.warning(f"Dir image extraction failed: {e}")
        logger.info(f"Extraction completed; entries extracted: {len(extracted)}")
        return extracted

    def _discover_hf_model_dir(root: str) -> _Optional[str]:
        """Find a Hugging Face model directory containing config.json, weights, and tokenizer."""
        weight_candidates = {
            "pytorch_model.bin",
            "pytorch_model.bin.index.json",
            "model.safetensors",
            "model.safetensors.index.json",
        }
        tokenizer_candidates = {"tokenizer.json", "tokenizer.model"}
        for dirpath, _dirnames, filenames in os.walk(root):
            fn = set(filenames)
            if "config.json" in fn and (fn & weight_candidates) and (fn & tokenizer_candidates):
                return dirpath
        return None

    def _log_dir_tree(root: str, max_depth: int = 3, max_entries: int = 800) -> None:
        """Compact tree logger for debugging large directories."""
        try:
            if not (root and os.path.isdir(root)):
                logger.info(f"(tree) Path is not a directory: {root}")
                return
            logger.info(f"(tree) {root} (max_depth={max_depth}, max_entries={max_entries})")
            total = 0
            root_depth = root.rstrip(os.sep).count(os.sep)
            for dirpath, dirnames, filenames in os.walk(root):
                depth = dirpath.rstrip(os.sep).count(os.sep) - root_depth
                if depth >= max_depth:
                    dirnames[:] = []
                indent = "  " * depth
                logger.info(f"(tree){indent}{os.path.basename(dirpath) or dirpath}/")
                total += 1
                if total >= max_entries:
                    logger.info("(tree) ... truncated ...")
                    return
                for fname in sorted(filenames)[:50]:
                    logger.info(f"(tree){indent}  {fname}")
                    total += 1
                    if total >= max_entries:
                        logger.info("(tree) ... truncated ...")
                        return
        except Exception as _e:
            logger.warning(f"Failed to render directory tree for {root}: {_e}")

    resolved_model_path: str = training_base_model
    if isinstance(training_base_model, str) and training_base_model.startswith("oci://"):
        # Strip scheme and perform skopeo copy to a plain directory on PVC
        ref_no_scheme = training_base_model[len("oci://") :]
        dir_image = os.path.join(pvc_path, "model-dir")
        model_out_dir = os.path.join(pvc_path, "model")
        # Clean output directory for a fresh extraction
        try:
            if os.path.isdir(model_out_dir):
                shutil.rmtree(model_out_dir)
        except Exception:
            pass
        # Use provided pull secret (Docker config.json content) if present
        auth_json = training_pull_secret.strip() or None
        _skopeo_copy_to_dir(ref_no_scheme, dir_image, auth_json)
        extracted = _extract_models_from_dir_image(dir_image, model_out_dir)
        if not extracted:
            logger.warning("No files extracted from '/models' in the OCI artifact; model discovery may fail.")
        _log_dir_tree(model_out_dir, max_depth=3, max_entries=800)
        # Typical extraction path is '<out_dir>/models/...'
        candidate_root = os.path.join(model_out_dir, "models")
        hf_dir = _discover_hf_model_dir(candidate_root if os.path.isdir(candidate_root) else model_out_dir)
        if hf_dir:
            logger.info(f"Detected HuggingFace model directory: {hf_dir}")
            resolved_model_path = hf_dir
        else:
            logger.warning(
                "Failed to detect a HuggingFace model directory after extraction; "
                "continuing with model_out_dir (may fail downstream)."
            )
            resolved_model_path = model_out_dir

    # ------------------------------
    # Training (placeholder for TrainingHubTrainer)
    # ------------------------------
    checkpoints_dir = os.path.join(pvc_path, "checkpoints")
    os.makedirs(checkpoints_dir, exist_ok=True)

    # Wire in TrainingHubTrainer (modularized steps)
    try:
        from kubeflow.trainer import TrainerClient
        from kubeflow.trainer.rhai import TrainingHubAlgorithms, TrainingHubTrainer
        from kubeflow_trainer_api import models as _th_models  # noqa: F401
        from kubeflow.common.types import KubernetesBackendConfig
        from kubeflow.trainer.options.kubernetes import (
            PodTemplateOverrides,
            PodTemplateOverride,
            PodSpecOverride,
            ContainerOverride,
        )

        if _api_client is None:
            raise RuntimeError("Kubernetes API client is not initialized")

        backend_cfg = KubernetesBackendConfig(client_configuration=_api_client.configuration)
        client = TrainerClient(backend_cfg)

        def _select_runtime(_client) -> object:
            """Return the 'training-hub' runtime from Trainer backend."""
            for rt in _client.list_runtimes():
                if getattr(rt, "name", "") == "training-hub":
                    logger.info(f"Found runtime: {rt}")
                    return rt
            raise RuntimeError("Training runtime 'training-hub' not found")

        th_runtime = _select_runtime(client)

        # Build training parameters (aligned to OSFT/SFT)
        parsed_target_patterns = (
            [p.strip() for p in training_target_patterns.split(",") if p.strip()] if training_target_patterns else None
        )
        parsed_lr_sched_kwargs = None
        if training_lr_scheduler_kwargs:
            try:
                items = [s.strip() for s in training_lr_scheduler_kwargs.split(",") if s.strip()]
                kv: Dict[str, str] = {}
                for item in items:
                    if "=" not in item:
                        raise ValueError(f"Invalid scheduler kwargs segment '{item}'. Expected key=value.")
                    key, value = item.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if not key:
                        raise ValueError("Empty key in training_lr_scheduler_kwargs")
                    kv[key] = value
                parsed_lr_sched_kwargs = kv
            except Exception as e:
                raise ValueError(f"Invalid training_lr_scheduler_kwargs format: {e}")

        def _parse_int(value: object, default_val: int) -> int:
            try:
                if value is None:
                    return default_val
                if isinstance(value, int):
                    return value
                s = str(value).strip()
                if not s:
                    return default_val
                return int(s)
            except Exception:
                return default_val

        def _compute_nproc_and_nodes() -> Tuple[int, int]:
            nproc_auto = str(training_resource_num_procs_per_worker).strip().lower() == "auto"
            nproc = (
                training_resource_gpu_per_worker
                if nproc_auto
                else _parse_int(training_resource_num_procs_per_worker, 1)
            )
            if nproc <= 0:
                nproc = 1
            nnodes = _parse_int(training_resource_num_workers, 1)
            if nnodes <= 0:
                nnodes = 1
            return nproc, nnodes

        def _build_params() -> Dict[str, object]:
            """Build OSFT/SFT parameter set for TrainingHub."""
            nproc_per_node, nnodes = _compute_nproc_and_nodes()
            base = {
                "model_path": resolved_model_path,
                # Prefer JSONL export when available; fallback to resolved directory
                "data_path": jsonl_path if os.path.exists(jsonl_path) else resolved_dataset_dir,
                "effective_batch_size": int(
                    training_effective_batch_size if training_effective_batch_size is not None else 128
                ),
                "max_tokens_per_gpu": int(training_max_tokens_per_gpu),
                "max_seq_len": int(training_max_seq_len if training_max_seq_len is not None else 8192),
                "learning_rate": float(training_learning_rate if training_learning_rate is not None else 5e-6),
                "backend": training_backend,
                "ckpt_output_dir": checkpoints_dir,
                "data_output_dir": training_data_output_dir
                or os.path.join(checkpoints_dir, "_internal_data_processing"),
                "warmup_steps": int(training_lr_warmup_steps) if training_lr_warmup_steps is not None else 0,
                "checkpoint_at_epoch": bool(training_checkpoint_at_epoch)
                if training_checkpoint_at_epoch is not None
                else False,
                "num_epochs": int(training_num_epochs) if training_num_epochs is not None else 1,
                "nproc_per_node": int(nproc_per_node),
                "nnodes": int(nnodes),
            }
            algo = (training_algorithm or "").strip().upper()
            if algo == "OSFT":
                base["unfreeze_rank_ratio"] = float(training_unfreeze_rank_ratio)
                base["osft_memory_efficient_init"] = bool(training_osft_memory_efficient_init)
                base["target_patterns"] = parsed_target_patterns or []
                if training_seed is not None:
                    base["seed"] = int(training_seed)
                if training_use_liger is not None:
                    base["use_liger"] = bool(training_use_liger)
                if training_use_processed_dataset is not None:
                    base["use_processed_dataset"] = bool(training_use_processed_dataset)
                if training_unmask_messages is not None:
                    base["unmask_messages"] = bool(training_unmask_messages)
                if training_lr_scheduler:
                    base["lr_scheduler"] = training_lr_scheduler
                if parsed_lr_sched_kwargs:
                    base["lr_scheduler_kwargs"] = parsed_lr_sched_kwargs
                if training_save_final_checkpoint is not None:
                    base["save_final_checkpoint"] = bool(training_save_final_checkpoint)
            elif algo == "SFT":
                if training_save_samples is not None:
                    base["save_samples"] = int(training_save_samples)
                if training_accelerate_full_state_at_epoch is not None:
                    base["accelerate_full_state_at_epoch"] = bool(training_accelerate_full_state_at_epoch)
                # SFT also supports lr_scheduler and warmup_steps
                if training_lr_scheduler:
                    base["lr_scheduler"] = training_lr_scheduler
                if training_use_liger is not None:
                    base["use_liger"] = bool(training_use_liger)
            # FSDP sharding strategy - stored as string, will be converted to FSDPOptions
            # in the custom training function below
            if training_fsdp_sharding_strategy:
                base["fsdp_sharding_strategy"] = training_fsdp_sharding_strategy.upper().strip()
                logger.info(f"Requested FSDP sharding strategy: {training_fsdp_sharding_strategy}")
            return base

        params = _build_params()

        # Determine which algorithm to use
        algo_str = (training_algorithm or "").strip().upper()
        use_sft = algo_str == "SFT"
        algo_value = TrainingHubAlgorithms.SFT if use_sft else TrainingHubAlgorithms.OSFT

        # Algorithm selection: include OSFT-only param when applicable
        if algo_value == TrainingHubAlgorithms.OSFT:
            params["unfreeze_rank_ratio"] = float(training_unfreeze_rank_ratio)

        # Store algorithm name in params for the training function
        params["_algorithm"] = "sft" if use_sft else "osft"

        # =======================================================================
        # Custom training function - handles FSDPOptions conversion
        # This function is extracted via inspect.getsource() and embedded in the
        # training pod, similar to how sft.ipynb works with SDK v1
        # SDK passes func_args as a SINGLE DICT argument (not **kwargs)
        # =======================================================================
        def _training_func_with_fsdp(parameters):
            """Training function that converts fsdp_sharding_strategy to FSDPOptions.

            This function is passed to TrainingHubTrainer and extracted via
            inspect.getsource(). It runs inside the training pod and can create
            Python objects like FSDPOptions that can't be serialized through params.

            Args:
                parameters: Dict of training parameters (passed by SDK as single arg)
            """
            import os

            # Extract algorithm and fsdp_sharding_strategy from parameters
            args = dict(parameters or {})
            algorithm = args.pop("_algorithm", "sft")
            fsdp_sharding_strategy = args.pop("fsdp_sharding_strategy", None)

            # Import the appropriate training function
            if algorithm == "sft":
                from training_hub import sft as train_algo
            else:
                from training_hub import osft as train_algo

            # Convert fsdp_sharding_strategy string to FSDPOptions object
            if fsdp_sharding_strategy:
                try:
                    from instructlab.training.config import FSDPOptions, ShardingStrategies

                    strategy_map = {
                        "FULL_SHARD": ShardingStrategies.FULL_SHARD,
                        "HYBRID_SHARD": ShardingStrategies.HYBRID_SHARD,
                        "NO_SHARD": ShardingStrategies.NO_SHARD,
                    }
                    if fsdp_sharding_strategy.upper() in strategy_map:
                        args["fsdp_options"] = FSDPOptions(
                            sharding_strategy=strategy_map[fsdp_sharding_strategy.upper()]
                        )
                        print(f"[PY] Using FSDP sharding strategy: {fsdp_sharding_strategy}", flush=True)
                    else:
                        print(f"[PY] Warning: Unknown FSDP strategy '{fsdp_sharding_strategy}'", flush=True)
                except ImportError as e:
                    print(f"[PY] Warning: Could not import FSDPOptions: {e}", flush=True)

            # Log and run training
            print(f"[PY] Launching {algorithm.upper()} training...", flush=True)
            result = train_algo(**args)
            print(f"[PY] {algorithm.upper()} training complete.", flush=True)
            return result

        # Build volumes and mounts (from passthrough only); do not inject env via pod overrides
        # Cluster policy forbids env in podTemplateOverrides; use trainer.env for container env

        volumes = []
        volume_mounts = []
        if kubernetes_config and getattr(kubernetes_config, "volumes", None):
            volumes.extend(kubernetes_config.volumes)
        if kubernetes_config and getattr(kubernetes_config, "volume_mounts", None):
            volume_mounts.extend(kubernetes_config.volume_mounts)

        # Container resources are not overridden here; rely on runtime defaults or future API support

        # Parse metadata labels/annotations for Pod template
        tpl_labels = parse_kv_list(training_metadata_labels)
        tpl_annotations = parse_kv_list(training_metadata_annotations)

        def _build_pod_spec_override() -> PodSpecOverride:
            """Return PodSpecOverride with mounts, envs, resources, and scheduling hints."""
            return PodSpecOverride(
                volumes=volumes,
                containers=[
                    ContainerOverride(
                        name="node",
                        volume_mounts=volume_mounts,
                    )
                ],
                # node_selector=(kubernetes_config.node_selector if kubernetes_config and getattr(kubernetes_config, "node_selector", None) else None),
                # tolerations=(kubernetes_config.tolerations if kubernetes_config and getattr(kubernetes_config, "tolerations", None) else None),
            )

        job_name = client.train(
            trainer=TrainingHubTrainer(
                # Use custom function to handle FSDPOptions conversion
                func=_training_func_with_fsdp,
                func_args=params,
                # Algorithm still needed for progression tracking
                algorithm=algo_value,
                packages_to_install=[],
                # Pass environment variables via Trainer spec (allowed by backend/webhook)
                env=dict(merged_env),
            ),
            options=[
                PodTemplateOverrides(
                    PodTemplateOverride(
                        target_jobs=["node"],
                        metadata={"labels": tpl_labels, "annotations": tpl_annotations}
                        if (tpl_labels or tpl_annotations)
                        else None,
                        spec=_build_pod_spec_override(),
                        # numProcsPerWorker=training_resource_num_procs_per_worker,
                        # numWorkers=training_resource_num_workers,
                    )
                )
            ],
            runtime=th_runtime,
        )
        logger.info(f"Submitted TrainingHub job: {job_name}")
        try:
            # Wait for the job to start running, then wait for completion or failure.
            client.wait_for_job_status(name=job_name, status={"Running"}, timeout=300)
            client.wait_for_job_status(name=job_name, status={"Complete", "Failed"}, timeout=1800)
            job = client.get_job(name=job_name)
            if getattr(job, "status", None) == "Failed":
                logger.error("Training job failed")
                raise RuntimeError(f"Training job failed with status: {job.status}")
            elif getattr(job, "status", None) == "Complete":
                logger.info("Training job completed successfully")
            else:
                logger.error(f"Unexpected training job status: {job.status}")
                raise RuntimeError(f"Training job ended with unexpected status: {job.status}")
        except Exception as e:
            logger.warning(f"Training job monitoring failed: {e}")
    except Exception as e:
        logger.error(f"TrainingHubTrainer execution failed: {e}")
        raise

    # ------------------------------
    # Metrics (hyperparameters + training metrics from trainer output)
    # ------------------------------
    def _get_training_metrics(search_root: str, algo: str = "osft") -> Dict[str, float]:
        """Find and parse TrainingHub metrics file (OSFT/SFT)."""
        import math

        # File patterns: OSFT=training_metrics_0.jsonl, SFT=training_params_and_metrics_global0.jsonl
        patterns = ["training_metrics_0.jsonl", "training_params_and_metrics_global0.jsonl"]
        if algo.lower() == "sft":
            patterns = patterns[::-1]

        mfile = None
        for root, _, files in os.walk(search_root):
            for p in patterns:
                if p in files:
                    mfile = os.path.join(root, p)
                    break
            if mfile:
                break

        if not mfile or not os.path.exists(mfile):
            logger.warning(f"No metrics file in {search_root}")
            return {}

        logger.info(f"Reading metrics from: {mfile}")
        metrics, losses = {}, []
        try:
            with open(mfile) as f:
                for line in f:
                    if line.strip():
                        try:
                            e = json.loads(line)
                            # Map fields: loss/avg_loss->loss, lr->learning_rate, gradnorm/grad_norm->grad_norm
                            for src, dst in [
                                ("loss", "loss"),
                                ("avg_loss", "loss"),
                                ("lr", "learning_rate"),
                                ("grad_norm", "grad_norm"),
                                ("gradnorm", "grad_norm"),
                                ("val_loss", "eval_loss"),
                                ("epoch", "epoch"),
                                ("step", "step"),
                            ]:
                                if src in e and dst not in metrics:
                                    try:
                                        metrics[dst] = float(e[src])
                                    except:
                                        pass
                            lv = e.get("loss") or e.get("avg_loss")
                            if lv:
                                try:
                                    losses.append(float(lv))
                                except:
                                    pass
                        except:
                            pass
            if losses:
                metrics["final_loss"] = losses[-1]
                metrics["min_loss"] = min(losses)
                metrics["final_perplexity"] = math.exp(min(losses[-1], 10))
            logger.info(f"Extracted {len(metrics)} metrics")
        except Exception as ex:
            logger.warning(f"Failed to parse metrics: {ex}")
        return metrics

    def _log_all_metrics() -> None:
        """Log hyperparameters and training metrics."""
        # 1. Log hyperparameters
        output_metrics.log_metric("num_epochs", float(params.get("num_epochs") or 1))
        output_metrics.log_metric("effective_batch_size", float(params.get("effective_batch_size") or 128))
        output_metrics.log_metric("learning_rate", float(params.get("learning_rate") or 5e-6))
        output_metrics.log_metric("max_seq_len", float(params.get("max_seq_len") or 8192))
        output_metrics.log_metric("max_tokens_per_gpu", float(params.get("max_tokens_per_gpu") or 0))
        output_metrics.log_metric("unfreeze_rank_ratio", float(params.get("unfreeze_rank_ratio") or 0))

        # 2. Find and parse training metrics file
        algo = (training_algorithm or "osft").strip().lower()
        training_metrics = _get_training_metrics(checkpoints_dir, algo)
        for k, v in training_metrics.items():
            output_metrics.log_metric(f"training_{k}", v)

    _log_all_metrics()

    # ------------------------------
    # Export most recent checkpoint as model artifact (artifact store) and PVC
    # ------------------------------
    def _persist_and_annotate() -> None:
        """Copy latest checkpoint to PVC and artifact store, then annotate output metadata."""
        latest = find_model_directory(checkpoints_dir)
        if not latest:
            raise RuntimeError(f"No model directory (with config.json) found under {checkpoints_dir}")
        logger.info(f"Found model directory: {latest}")
        # PVC copy
        pvc_dir = os.path.join(pvc_path, "final_model")
        try:
            if os.path.exists(pvc_dir):
                shutil.rmtree(pvc_dir)
            shutil.copytree(latest, pvc_dir, dirs_exist_ok=True)
            logger.info(f"Copied checkpoint to PVC dir: {pvc_dir}")
        except Exception as _e:
            logger.warning(f"Failed to copy model to PVC dir {pvc_dir}: {_e}")
        # Artifact copy
        output_model.name = f"{training_base_model}-checkpoint"
        shutil.copytree(latest, output_model.path, dirs_exist_ok=True)
        logger.info(f"Exported checkpoint from {latest} to artifact path {output_model.path}")
        # Metadata
        try:
            output_model.metadata["model_name"] = training_base_model
            output_model.metadata["artifact_path"] = output_model.path
            output_model.metadata["pvc_model_dir"] = pvc_dir
            logger.info("Annotated output_model metadata with pvc/artifact locations")
        except Exception as _e:
            logger.warning(f"Failed to set output_model metadata: {_e}")

    _persist_and_annotate()

    return "training completed"


if __name__ == "__main__":
    from kfp import compiler

    compiler.Compiler().compile(
        train_model,
        package_path=__file__.replace(".py", "_component.yaml"),
    )
    print("Compiled: train_model_component.yaml")
