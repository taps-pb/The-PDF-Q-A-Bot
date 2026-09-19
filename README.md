# The PDF Q&A Bot

Query an English PDF locally. Verify cited pages: answers can be wrong or incomplete. Refusals return `NOT FOUND`; operational errors appear separately.

## Run locally

Install Python 3.12, uv, Ollama, and Tesseract English. Start Ollama with cloud disabled and download `qwen3:8b` and `qwen3-embedding:0.6b`; follow [setup instructions](docs/SETUP.md). From this repository:

```sh
uv sync --locked
export PDF_QA_DATA_DIR="$PWD/../data/app"
uv run streamlit run app.py
```

Downloads need internet once; processing stays local. Ollama must run alongside Streamlit; Community Cloud alone is insufficient.

## How to use

1. Open http://localhost:8501 and upload an English PDF (maximum 50 MiB, 200 pages).
2. Keep automatic extraction and 800-character chunks, then click **Build index**. Choose forced OCR for text inside images.
3. Enter a question and click **Find answer**. Check cited pages and expand **Retrieved passages** to inspect evidence and scores.
4. Reopen a PDF through **Saved index**, select its document, then click **Load index**. PDFs are searched individually, not together.
5. After [reranker setup](docs/RERANKING.md), optionally enable **Rerank passages (experimental)**. It defaults off; indexes need no rebuilding.

Questions are independent; conversation memory and diagram interpretation are unsupported.

## Architecture in five lines

1. Extract page-preserving text, using Tesseract OCR when needed.
2. Chunk text and create local Qwen3 embeddings.
3. Persist normalized vectors in FAISS with source metadata.
4. Retrieve four passages, or locally rerank 20 candidates to four with a cross-encoder.
5. Generate with local Qwen3, validate citation IDs, and display evidence through Streamlit.

## Measured choices

OSHA/NIOSH development results, with AI-assisted manual grading:

| Chunk characters | Hit@4 | Supported accuracy | Correct refusals |
|---|---|---|---|
| 300 | 7/7 | 5/7 | 3/3 |
| **800** | **7/7** | **7/7** | **3/3** |
| 1500 | 7/7 | 5/7 | 3/3 |

Defaults: **800 characters**, **60-character overlap**, **k=4**, temperature zero, thinking disabled. [Results and plot](evals/results/run-01/).

## What went wrong

At 300 characters, truncation of the seventh program element caused a false refusal despite a page hit.

At 1500 characters, the ladder-height answer was refused despite complete evidence; the cause remains unresolved.

Prompt, hybrid, and quote-validation experiments failed quality gates.

Reranking improved development page hit@4 from **21/24 to 24/24**; answer-quality gains remain unverified.

## Final verification

Dense held-out results: **11/18 supported answers**, **6/6 correct refusals**, zero operational errors. These small-corpus results are not a reliability guarantee.

**133 tests pass**, including local model/OCR and reranking checks. See [release results and limitations](docs/RELEASE.md).
