# The PDF Q&A Bot

Ask questions about one English PDF and inspect the evidence behind each answer. This Streamlit app runs entirely locally: selectable text is extracted directly, scanned pages use Tesseract OCR, and Ollama generates answers with physical PDF page citations. An expandable panel shows retrieved passages and cosine similarity scores. Unsupported questions return `NOT FOUND`; operational errors appear separately.

## Run locally

Install Python 3.12, uv, Ollama, and Tesseract English. Start `OLLAMA_NO_CLOUD=1 ollama serve`, then download `qwen3:8b` and `qwen3-embedding:0.6b`. From this repository:

```sh
uv sync --locked
uv run streamlit run app.py
```

See [setup instructions](docs/SETUP.md) for model storage, private data directories, and verification. Downloads require internet once; document processing needs no cloud service. Uploads are limited to 50 MiB and 200 pages. Choose forced OCR when images contain text alongside selectable text. Diagram interpretation and conversation memory are outside this release.

## Architecture in five lines

1. Validate the PDF and extract page-preserving text, using local OCR when needed.
2. Split pages into overlapping chunks and embed them with Qwen3 Embedding.
3. Persist normalized vectors in FAISS with JSON metadata and content-based cache keys.
4. Retrieve four passages and ask local Qwen3 for a grounded, structured answer.
5. Validate citation IDs, display evidence, and evaluate through the same pipeline.

## Measured choices

The frozen evaluation uses seven answerable and three unanswerable questions from the public-domain OSHA/NIOSH handbook. Grades use AI-assisted manual evidence review; these are development results, not independent validation.

| Chunk characters | Hit@4 | Supported accuracy | Correct refusals |
|---|---|---|---|
| 300 | 7/7 | 5/7 | 3/3 |
| **800** | **7/7** | **7/7** | **3/3** |
| 1500 | 7/7 | 5/7 | 3/3 |

Choose **800 characters**, fixed **60-character overlap**, and **k=4**: accuracy breaks the retrieval tie. Generation uses temperature zero with thinking disabled. [Raw results, grades, and plot](evals/results/run-01/) preserve every response.

## What went wrong

At 300 characters, retrieval truncated the seventh program element; the bot refused an answerable question. Page-level hit@4 still counted success.

At 1500 characters, the bot refused the ladder-height question despite retrieving both units. This was a generation failure; distracting context and extraction spacing are possible contributors, not proven causes.

Next: evaluate additional documents, measure passage-level coverage, and test reranking against these failures. [Evaluation instructions](docs/EVALUATION.md) explain reproduction and limitations.
