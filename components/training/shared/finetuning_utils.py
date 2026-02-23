"""Shared utility functions for fine-tuning training components."""

import json
import logging
import os
import shutil
import subprocess
import sys
from typing import Dict, List, Optional


def create_logger(name: str = "train_model") -> logging.Logger:
    """Create and configure a logger for training components.

    Args:
        name: Logger name.

    Returns:
        Configured logger instance.
    """
    lg = logging.getLogger(name)
    lg.setLevel(logging.INFO)
    if not lg.handlers:
        h = logging.StreamHandler(sys.stdout)
        h.setLevel(logging.INFO)
        h.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        lg.addHandler(h)
    return lg


def find_model_dir(root: str) -> Optional[str]:
    """Find the most recent model checkpoint directory.

    Args:
        root: Root directory to search.

    Returns:
        Path to model directory, or None if not found.
    """
    if not os.path.isdir(root):
        return None
    cands = []
    for r, _, fs in os.walk(root):
        if "config.json" in fs:
            try:
                cands.append((os.path.getmtime(os.path.join(r, "config.json")), r))
            except OSError:
                pass
    if not cands:
        latest = None
        for e in os.listdir(root):
            p = os.path.join(root, e)
            if os.path.isdir(p):
                try:
                    m = os.path.getmtime(p)
                    if latest is None or m > latest[0]:
                        latest = (m, p)
                except OSError:
                    pass
        return latest[1] if latest else None
    cands.sort(reverse=True)
    return cands[0][1]


def init_k8s(log: logging.Logger) -> Optional[object]:
    """Initialize Kubernetes client from environment variables.

    Args:
        log: Logger instance.

    Returns:
        Kubernetes ApiClient, or None if initialization fails.
    """
    try:
        from kubernetes import client as k8s

        srv = os.environ.get("KUBERNETES_SERVER_URL", "").strip()
        tok = os.environ.get("KUBERNETES_AUTH_TOKEN", "").strip()
        if not srv or not tok:
            raise RuntimeError(
                "Kubernetes credentials missing or incomplete: both KUBERNETES_SERVER_URL and "
                "KUBERNETES_AUTH_TOKEN must be set and non-empty. Ensure the 'kubernetes-credentials' "
                "secret is configured and mounted into the training task."
            )

        log.info("Initializing Kubernetes client from environment variables")
        cfg = k8s.Configuration()
        cfg.host, cfg.verify_ssl = srv, False
        cfg.api_key = {"authorization": f"Bearer {tok}"}
        k8s.Configuration.set_default(cfg)
        return k8s.ApiClient(cfg)
    except Exception as e:
        log.warning(f"K8s client init failed: {e}")
        return None


def parse_kv(s: str) -> Dict[str, str]:
    """Parse comma-separated key=value pairs.

    Args:
        s: String containing key=value pairs.

    Returns:
        Dictionary of parsed key-value pairs.
    """
    out = {}
    if not s:
        return out
    for it in s.split(","):
        it = it.strip()
        if not it:
            continue
        if "=" not in it:
            raise ValueError(f"Invalid kv: {it}")
        k, v = it.split("=", 1)
        k, v = k.strip(), v.strip()
        if not k:
            raise ValueError(f"Empty key: {it}")
        out[k] = v
    return out


def configure_env(csv: str, base: Dict[str, str], log: logging.Logger) -> Dict[str, str]:
    """Configure environment variables.

    Args:
        csv: Comma-separated key=value pairs.
        base: Base environment dictionary.
        log: Logger instance.

    Returns:
        Merged environment dictionary.
    """
    m = {**base, **parse_kv(csv)}
    for k, v in m.items():
        os.environ[k] = v
    log.info(f"Env: {sorted(m.keys())}")
    return m


def setup_hf_token(menv: Dict[str, str], training_base_model: str, log: logging.Logger) -> None:
    """Setup HuggingFace token if available.

    Args:
        menv: Environment dictionary to update.
        training_base_model: Base model path/ID.
        log: Logger instance.
    """
    hf_tok = os.environ.get("HF_TOKEN", "").strip()
    if hf_tok:
        menv["HF_TOKEN"] = hf_tok
        os.environ["HF_TOKEN"] = hf_tok
        log.info("HF_TOKEN propagated")
    elif isinstance(training_base_model, str):
        b = training_base_model.strip()
        if b.startswith("hf://") or ("/" in b and not b.startswith("oci://") and not os.path.exists(b)):
            log.warning(f"HF_TOKEN not set; only public models accessible for '{training_base_model}'")


def resolve_dataset(inp, out_dir: str, log: logging.Logger) -> None:
    """Resolve and prepare dataset from various sources.

    Args:
        inp: Input dataset artifact.
        out_dir: Output directory.
        log: Logger instance.
    """
    from datasets import load_dataset

    if os.path.isdir(out_dir) and any(os.scandir(out_dir)):
        log.info(f"Using existing ds: {out_dir}")
        return
    if inp and getattr(inp, "path", None) and os.path.exists(inp.path):
        src = inp.path
        if os.path.isdir(src):
            log.info(f"Copy ds dir: {src}")
            shutil.copytree(src, out_dir, dirs_exist_ok=True)
        else:
            log.info(f"Copy ds file: {src}")
            dst = os.path.join(out_dir, os.path.basename(src))
            if not os.path.splitext(dst)[1]:
                dst = os.path.join(out_dir, "train.jsonl")
            shutil.copy2(src, dst)
        return
    rp = ""
    try:
        if inp and hasattr(inp, "metadata") and isinstance(inp.metadata, dict):
            pvc_m = (inp.metadata.get("pvc_path") or inp.metadata.get("pvc_dir") or "").strip()
            if pvc_m and os.path.exists(pvc_m):
                if os.path.isdir(pvc_m) and any(os.scandir(pvc_m)):
                    log.info(f"PVC ds dir: {pvc_m}")
                    shutil.copytree(pvc_m, out_dir, dirs_exist_ok=True)
                    return
                elif os.path.isfile(pvc_m):
                    log.info(f"PVC ds file: {pvc_m}")
                    dst = os.path.join(out_dir, os.path.basename(pvc_m))
                    if not os.path.splitext(dst)[1]:
                        dst = os.path.join(out_dir, "train.jsonl")
                    shutil.copy2(pvc_m, dst)
                    return
            rp = (inp.metadata.get("artifact_path") or "").strip()
    except Exception:
        rp = ""
    if rp:
        if rp.startswith("s3://") or rp.startswith("http://") or rp.startswith("https://"):
            log.info(f"Remote ds: {rp}")
            ext = rp.lower()
            if ext.endswith(".json") or ext.endswith(".jsonl"):
                ds = load_dataset("json", data_files=rp, split="train")
            elif ext.endswith(".parquet"):
                ds = load_dataset("parquet", data_files=rp, split="train")
            else:
                raise ValueError("Unsupported remote format")
            ds.save_to_disk(out_dir)
            return
        else:
            log.info(f"HF ds: {rp}")
            load_dataset(rp, split="train").save_to_disk(out_dir)
            return
    raise ValueError(
        "No dataset provided or resolvable. Please supply an input artifact, a PVC path via metadata "
        "('pvc_path' or 'pvc_dir'), or a remote source via metadata['artifact_path'] (S3/HTTP/HF repo id)."
    )


def prepare_jsonl(ds_dir: str, jsonl_path: str, log: logging.Logger) -> None:
    """Prepare JSONL file from dataset.

    Args:
        ds_dir: Dataset directory.
        jsonl_path: Output JSONL path.
        log: Logger instance.
    """
    from datasets import load_from_disk

    try:
        dsk = load_from_disk(ds_dir)
        tr = dsk["train"] if isinstance(dsk, dict) else dsk
        try:
            tr.to_json(jsonl_path, lines=True)
            log.info(f"JSONL: {jsonl_path}")
        except AttributeError:
            with open(jsonl_path, "w") as f:
                for r in tr:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            log.info(f"JSONL manual: {jsonl_path}")
    except Exception as e:
        log.warning(f"JSONL export failed: {e}")


def _skopeo_copy(ref: str, dest: str, auth: Optional[str], log: logging.Logger) -> None:
    """Copy OCI image using skopeo.

    Args:
        ref: Image reference.
        dest: Destination directory.
        auth: Authentication JSON.
        log: Logger instance.
    """
    os.makedirs(dest, exist_ok=True)
    af = None
    if auth:
        af = "/tmp/skopeo-auth.json"
        with open(af, "w") as f:
            f.write(auth)
    cmd = ["skopeo", "copy"]
    if af:
        cmd.extend(["--authfile", af])
    cmd.extend([f"docker://{ref}", f"dir:{dest}"])
    log.info(f"Run: {' '.join(cmd)}")
    r = subprocess.run(cmd, text=True, capture_output=True)
    if r.returncode != 0:
        log.error(f"skopeo fail: {r.stderr}")
        r.check_returncode()


def _extract_tar(img_dir: str, out: str, log: logging.Logger) -> List[str]:
    """Extract model files from OCI image layers.

    Args:
        img_dir: Image directory.
        out: Output directory.
        log: Logger instance.

    Returns:
        List of extracted file paths.
    """
    import tarfile

    os.makedirs(out, exist_ok=True)
    ext = []
    for fn in os.listdir(img_dir):
        fp = os.path.join(img_dir, fn)
        if not os.path.isfile(fp) or fn.endswith(".json") or fn in {"manifest", "index.json"}:
            continue
        try:
            with tarfile.open(fp, mode="r:*") as tf:
                for m in tf.getmembers():
                    if m.isfile() and m.name.startswith("models/"):
                        tf.extract(m, path=out)
                        ext.append(m.name)
        except Exception:
            pass
    log.info(f"Extracted: {len(ext)}")
    return ext


def _find_hf_model(root: str) -> Optional[str]:
    """Find HuggingFace model directory.

    Args:
        root: Root directory to search.

    Returns:
        Path to model directory, or None if not found.
    """
    wt = {"pytorch_model.bin", "pytorch_model.bin.index.json", "model.safetensors", "model.safetensors.index.json"}
    tk = {"tokenizer.json", "tokenizer.model"}
    for dp, _, fns in os.walk(root):
        fn = set(fns)
        if "config.json" in fn and (fn & wt) and (fn & tk):
            return dp
    return None


def _get_oci_auth(log: logging.Logger) -> Optional[str]:
    """Get OCI authentication from environment.

    Args:
        log: Logger instance.

    Returns:
        Authentication JSON string, or None.
    """
    raw = os.environ.get("OCI_PULL_SECRET_MODEL_DOWNLOAD", "").strip()
    if not raw:
        log.warning("OCI_PULL_SECRET_MODEL_DOWNLOAD not set")
        return None
    try:
        p = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "OCI_PULL_SECRET_MODEL_DOWNLOAD is set but is not valid JSON. "
            "It must contain Docker config.json content for skopeo authentication."
        ) from exc
    if not isinstance(p, dict) or not p.get("auths"):
        raise ValueError(
            "OCI_PULL_SECRET_MODEL_DOWNLOAD is set but does not look like a Docker config.json. "
            "Expected a JSON object with a non-empty 'auths' field."
        )
    log.info("OCI authentication configuration loaded successfully")
    return raw


def download_oci_model(model_ref: str, pvc_path: str, log: logging.Logger) -> str:
    """Download model from OCI registry.

    Args:
        model_ref: OCI model reference (oci://...).
        pvc_path: PVC root path.
        log: Logger instance.

    Returns:
        Path to extracted model.
    """
    ref = model_ref[6:]  # Remove "oci://" prefix
    img_dir = os.path.join(pvc_path, "model-dir")
    mod_out = os.path.join(pvc_path, "model")
    if os.path.isdir(mod_out):
        shutil.rmtree(mod_out, ignore_errors=True)
    _skopeo_copy(ref, img_dir, _get_oci_auth(log), log)
    _extract_tar(img_dir, mod_out, log)
    cand = os.path.join(mod_out, "models")
    hfd = _find_hf_model(cand if os.path.isdir(cand) else mod_out)
    return hfd if hfd else mod_out


def plot_training_loss(loss: list, path: str) -> None:
    """Plot training loss curve and save as HTML.

    Args:
        loss: List of loss values.
        path: Output HTML file path.
    """
    import base64
    from io import BytesIO

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if not loss:
        with open(path, "w") as f:
            f.write("<html><body><p>No loss data.</p></body></html>")
        return
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.plot(range(1, len(loss) + 1), loss, "b-", linewidth=2, label="Loss")
    ax.set_xlabel("Step")
    ax.set_ylabel("Loss")
    ax.set_title("Training Loss")
    ax.grid(True, alpha=0.3)
    ax.legend()
    ml, mi = min(loss), loss.index(min(loss))
    ax.annotate(
        f"Min:{ml:.4f}",
        xy=(mi + 1, ml),
        xytext=(10, 10),
        textcoords="offset points",
        fontsize=9,
        arrowprops=dict(arrowstyle="->", color="green"),
        color="green",
    )
    ax.annotate(
        f"Final:{loss[-1]:.4f}",
        xy=(len(loss), loss[-1]),
        xytext=(-60, 10),
        textcoords="offset points",
        fontsize=9,
        color="red",
    )
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    img = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    html = (
        f"<!DOCTYPE html><html><head><style>*{{margin:0;padding:0}}"
        f"body{{font-family:sans-serif;padding:5px}}.s{{font-size:10px;margin-bottom:5px}}"
        f".c{{width:100%}}</style></head><body>"
        f'<div class="s">Loss:{loss[0]:.4f}-{loss[-1]:.4f}(min {ml:.4f})|{len(loss)} steps</div>'
        f'<img class="c" src="data:image/png;base64,{img}"/></body></html>'
    )
    with open(path, "w") as f:
        f.write(html)


def persist_model(
    ckpt_dir: str,
    pvc_path: str,
    training_base_model: str,
    output_model,
    log: logging.Logger,
) -> None:
    """Persist trained model to PVC and output artifact.

    Args:
        ckpt_dir: Checkpoint directory.
        pvc_path: PVC root path.
        training_base_model: Base model name.
        output_model: Output model artifact.
        log: Logger instance.
    """
    latest = find_model_dir(ckpt_dir)
    if not latest:
        raise RuntimeError(f"No model found in {ckpt_dir}")
    log.info(f"Model: {latest}")
    pvc_out = os.path.join(pvc_path, "final_model")
    if os.path.exists(pvc_out):
        shutil.rmtree(pvc_out, ignore_errors=True)
    shutil.copytree(latest, pvc_out, dirs_exist_ok=True)
    log.info(f"Copied to {pvc_out}")
    output_model.name = f"{training_base_model}-checkpoint"
    shutil.copytree(latest, output_model.path, dirs_exist_ok=True)
    log.info(f"Artifact: {output_model.path}")
    output_model.metadata["model_name"] = training_base_model
    output_model.metadata["artifact_path"] = output_model.path
    output_model.metadata["pvc_model_dir"] = pvc_out


def extract_metrics_from_jsonl(metrics_file: str) -> tuple[Dict, List[float]]:
    """Extract training metrics from JSONL file.

    Args:
        metrics_file: Path to metrics JSONL file.

    Returns:
        Tuple of (metrics dict, loss values list).
    """
    if not os.path.exists(metrics_file):
        return {}, []

    met, loss = {}, []
    with open(metrics_file) as f:
        for ln in f:
            if ln.strip():
                try:
                    e = json.loads(ln)
                    for s, d in [
                        ("loss", "loss"),
                        ("avg_loss", "loss"),
                        ("lr", "learning_rate"),
                        ("grad_norm", "grad_norm"),
                        ("gradnorm", "grad_norm"),
                        ("val_loss", "eval_loss"),
                        ("epoch", "epoch"),
                        ("step", "step"),
                    ]:
                        if s in e and d not in met:
                            try:
                                met[d] = float(e[s])
                            except (ValueError, TypeError):
                                pass
                    lv = e.get("loss") or e.get("avg_loss")
                    if lv:
                        try:
                            loss.append(float(lv))
                        except (ValueError, TypeError):
                            pass
                except Exception:
                    pass
    if loss:
        met["final_loss"], met["min_loss"] = loss[-1], min(loss)
        met["final_perplexity"] = __import__("math").exp(min(loss[-1], 10))
    return met, loss
