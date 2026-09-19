"""Optional local cross-encoder. Model downloads happen only in the setup CLI."""

import argparse
import hashlib
import os
from functools import lru_cache
from pathlib import Path

import numpy as np

from pdf_qa.types import AppError, SearchHit

MODEL_ID = "cross-encoder/ms-marco-MiniLM-L6-v2"
MODEL_REVISION = "233902d25c440f23af6f7d6e94d2946bac0bee0a"
MODEL_FILES = ("onnx/model.onnx", "tokenizer.json")
RETRIEVAL_CONFIG = {
    "version": "cross-encoder-v1",
    "method": "dense-then-cross-encoder",
    "score": "relevance-logit",
    "candidates": 20,
    "model": MODEL_ID,
    "revision": MODEL_REVISION,
    "max_length": 512,
    "device": "cpu",
    "backend": "onnxruntime",
}


def model_path() -> Path:
    value = os.environ.get("PDF_QA_RERANKER_DIR")
    if not value:
        raise AppError("Set PDF_QA_RERANKER_DIR to the downloaded local reranker directory.")
    path = Path(value).expanduser().resolve()
    if not all((path / name).is_file() for name in MODEL_FILES):
        raise AppError("Reranker files are missing. Follow docs/RERANKING.md to download them.")
    return path


@lru_cache(maxsize=1)
def _load(path: str):
    try:
        import onnxruntime as ort
        from tokenizers import Tokenizer
    except ImportError as exc:
        raise AppError("Install the optional reranker with: uv sync --extra rerank") from exc
    try:
        ort.disable_telemetry_events()
        tokenizer = Tokenizer.from_file(str(Path(path) / "tokenizer.json"))
        tokenizer.enable_truncation(max_length=512)
        tokenizer.enable_padding(pad_id=0, pad_token="[PAD]")
        session = ort.InferenceSession(
            str(Path(path) / "onnx/model.onnx"),
            providers=["CPUExecutionProvider"],
        )
        return tokenizer, session
    except Exception as exc:
        raise AppError(f"Cannot load the local reranker: {exc}") from exc


def _scores(question, hits):
    tokenizer, session = _load(str(model_path()))
    encoded = tokenizer.encode_batch([(question, hit.chunk.text) for hit in hits])
    inputs = {
        name: np.asarray([getattr(item, attr) for item in encoded], dtype=np.int64)
        for name, attr in (
            ("input_ids", "ids"),
            ("attention_mask", "attention_mask"),
            ("token_type_ids", "type_ids"),
        )
    }
    logits = np.asarray(session.run(["logits"], inputs)[0])
    if logits.shape != (len(hits), 1):
        raise AppError("The local reranker returned invalid scores.")
    return logits[:, 0]


def rerank(question: str, hits: list[SearchHit], k: int = 4) -> list[SearchHit]:
    """Return new hits with relevance logits, preserving dense order on ties."""
    if not isinstance(question, str) or not question.strip() or len(question) > 2000:
        raise AppError("Reranking requires a nonempty question of at most 2,000 characters.")
    if type(k) is not int or not 1 <= k <= 20 or len(hits) > 20:
        raise AppError("Rerank at most 20 candidates and keep between 1 and 20 passages.")
    if not hits:
        return []
    try:
        scores = np.asarray(_scores(question.strip(), hits), dtype=float)
    except AppError:
        raise
    except Exception as exc:
        raise AppError(f"Local reranking failed: {exc}") from exc
    if scores.shape != (len(hits),) or not np.isfinite(scores).all():
        raise AppError("The local reranker returned invalid scores.")
    order = sorted(range(len(hits)), key=lambda i: -scores[i])[:k]
    return [SearchHit(hits[i].chunk, float(scores[i])) for i in order]


def model_identity() -> dict:
    """Hash the actual local artifacts instead of assuming they match a model name."""
    path = model_path()
    hashes = {}
    for name in MODEL_FILES:
        with (path / name).open("rb") as handle:
            hashes[name] = hashlib.file_digest(handle, "sha256").hexdigest()
    return {
        **RETRIEVAL_CONFIG,
        "files_sha256": hashes,
    }


def main():
    parser = argparse.ArgumentParser(description="Download the pinned public reranker weights.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        parser.error("Install the rerank extra first: uv sync --extra rerank")
    snapshot_download(
        repo_id=MODEL_ID,
        revision=MODEL_REVISION,
        local_dir=args.output,
        allow_patterns=list(MODEL_FILES),
    )
    print(f"Local reranker saved to {args.output.resolve()}")


if __name__ == "__main__":
    main()
