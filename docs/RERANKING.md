# Optional local reranking

## Plan fixed before measurement

The requested extension adds one optional local cross-encoder stage: retrieve
20 dense FAISS candidates, jointly score each question/passage pair, and keep
the best four. The existing dense top-four path remains the default. No prompt,
generation model, chunking, index format, or multi-document search changes are
included. Existing indexes must work without rebuilding.

Use `cross-encoder/ms-marco-MiniLM-L6-v2` from a pinned public model revision.
Download weights explicitly during setup, outside Git. At runtime, load only
local ONNX/tokenizer files and perform inference on CPU. No remote code is loaded. No document
contents may be sent to a model service. Use the existing `SearchHit` record;
reranked scores are relevance logits, not cosine similarities or probabilities.
Keep stable candidate order for equal scores. Missing weights/dependencies and
invalid model outputs must fail visibly, never silently switch retrieval modes.

Verify ranking, ties, invalid outputs, fewer than 20 passages, local-only loading,
UI mode switching, and document isolation. Run the existing regression tests and
a real local reranker smoke test. Compare dense hit@4 with reranked hit@4 on the
existing development questions and OCR variants, recording model identity,
index identity, passages, timings, and errors. Do not rerun the consumed holdout.

This is a retrieval experiment, not proof of improved answers. Report gains and
regressions without tuning against the results. Keep reranking opt-in until a
separate answer-quality evaluation supports changing the default.

## Multi-document scope

The app stores multiple independent PDF indexes and lets the user select one.
Switching documents clears prior answers and evidence. Each search is restricted
to the selected PDF. Combined search across PDFs with source filters is not
implemented by this extension.

## Setup and use

From `code/`, install the optional dependency and download the pinned weights:

```sh
uv sync --locked --extra rerank
uv run --extra rerank python -m pdf_qa.rerank --output ../data/models/reranker
export PDF_QA_RERANKER_DIR="$PWD/../data/models/reranker"
export PDF_QA_DATA_DIR="$PWD/../data/app"
HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 uv run --extra rerank streamlit run app.py
```

Keep the existing cloud-disabled Ollama service running. In the sidebar, enable
**Rerank passages (experimental)** before asking a question. There is no need to
rebuild a PDF index. Clear the checkbox to return to dense search. Changing the
mode clears the displayed answer/evidence but keeps the selected document.
Keep `--extra rerank` in `uv run` commands so uv does not remove the optional
packages. Other checkouts can use any model/data directory outside Git.

The model is an English MS MARCO cross-encoder, not a domain-specific verifier.
Question/passage pairs are truncated to 512 tokens; long pairs can lose evidence.
Its scores are relevance logits, not answer-confidence probabilities. CPU
reranking adds latency and optional ONNX Runtime/Tokenizers dependencies. No new
service is required. The baseline install does not need the rerank extra.

Model source: [model card](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2).
Local-only loading uses [ONNX Runtime](https://onnxruntime.ai/docs/api/python/api_summary.html)
and the [Tokenizer API](https://huggingface.co/docs/tokenizers/api/tokenizer).

Before benchmark inference, a PyTorch implementation passed an isolated smoke
but crashed when combined with FAISS on this Mac. It was replaced with the
official ONNX export of the same model before measurement. No benchmark results
were used to select a different model; PyTorch is not a runtime dependency.

## Reproduce the retrieval measurement

With the environment variables above and the existing prepared corpus:

```sh
uv run --extra rerank python -m pdf_qa.rerank_eval \
  --corpus-dir ../data/corpus --output evals/reranking/results/new-run
```

Output directories cannot be overwritten. This runner selects development only;
it does not run held-out questions, generate answers, or perform semantic grading.
Page hit@4 means at least one retrieved passage lies on an annotated evidence
page. It does not mean all required evidence was retrieved. OCR variants are
reported separately because they repeat native questions. Latencies include
query embedding, digest checks, retrieval, and optional reranking, but exclude
indexing and model loading (recorded separately). Dense runs first for each pair;
these single-run timings are descriptive, not a controlled speed benchmark.
