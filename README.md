# The PDF Q&A Bot

Ask questions about one English PDF using local Streamlit, native extraction, Tesseract OCR, FAISS, and Ollama. Answers cite PDF pages; expandable passages show retrieval scores. Refusals return `NOT FOUND`; operational errors appear separately. Verify cited passages: answers can be wrong or incomplete.

## Run locally

Install Python 3.12, uv, Ollama, and Tesseract English. Start Ollama with cloud disabled and download `qwen3:8b` and `qwen3-embedding:0.6b`; follow [setup instructions](docs/SETUP.md). From this repository:

```sh
uv sync --locked
export PDF_QA_DATA_DIR="$PWD/../data/app"
uv run streamlit run app.py
```

Downloads need internet once; processing stays local. Uploads are limited to 50 MiB and 200 pages. Use forced OCR when images contain text alongside selectable text. Diagram interpretation and conversation memory are outside scope.

## Architecture in five lines

1. Validate the PDF and extract page-preserving text, using local OCR when needed.
2. Split pages into overlapping chunks and embed them with Qwen3 Embedding.
3. Persist normalized vectors in FAISS with JSON metadata and content-based cache keys.
4. Retrieve four passages and ask local Qwen3 for a grounded, structured answer.
5. Validate citation IDs, display evidence, and evaluate through the same pipeline.

## Measured choices

The OSHA/NIOSH development evaluation uses seven answerable and three unanswerable questions, with AI-assisted manual grading:

| Chunk characters | Hit@4 | Supported accuracy | Correct refusals |
|---|---|---|---|
| 300 | 7/7 | 5/7 | 3/3 |
| **800** | **7/7** | **7/7** | **3/3** |
| 1500 | 7/7 | 5/7 | 3/3 |

Production uses **800 characters**, **60-character overlap**, and **k=4**, with temperature zero and thinking disabled. [Original results and plot](evals/results/run-01/) preserve the experiment.

## What went wrong

At 300 characters, retrieval truncated the seventh program element and caused a false refusal despite a page-level retrieval hit.

At 1500 characters, the ladder-height answer was refused despite complete evidence. The cause was not isolated.

Prompt, hybrid-retrieval, and quote-validation experiments failed quality gates; none replaced the original pipeline.

Optional [local reranking](docs/RERANKING.md) improved development page hit@4 from 21/24 to 24/24. Answer-quality gains remain unverified.

## Final verification

The one-time held-out run achieved **11/18 supported answers**, **6/6 correct refusals**, and zero operational errors. Five answerable questions were refused; two responses lacked complete cited support. These small-corpus, AI-assisted grades are not a production reliability guarantee.

All **133 tests** pass, including local model/OCR and reranking checks. The dense legacy regression retains 7/7 supported answers and 3/3 refusals. See [release results and limitations](docs/RELEASE.md).
