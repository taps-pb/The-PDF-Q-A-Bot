# Implementation agreement

Build a local Streamlit PDF Q&A app with English native extraction and OCR, one active document, page citations, retrieved text and scores, persistent FAISS indexes, ten evaluation questions, three chunk-size measurements, and a 300–400-word README grounded in real failures.

## Architecture

- Python 3.12, uv, Streamlit; direct Python modules, no separate server or database.
- pypdf text extraction, pypdfium2 rendering, Tesseract English OCR.
- Ollama qwen3:8b (thinking disabled) and qwen3-embedding:0.6b. Local connections only.
- Normalized embeddings in FAISS IndexFlatIP; top four passages; JSON metadata without pickle.
- Page-bounded, paragraph-aware chunks of 300/800/1500 characters, fixed 60-character overlap. Start at 800, select final setting from measured results.
- Cache identity: PDF SHA-256, extraction and chunk settings, embedding digest, format version. Persist atomically; reload without embedding the PDF again.
- Structured answer/refusal/cited chunk IDs. Validate references, allow one repair for malformed output, show operational errors separately from NOT FOUND.

## Limits

One English PDF, at most 50 MiB and 200 pages. Automatic OCR below 40 non-whitespace characters per page. Force OCR option for text within images on mixed pages. Physical PDF page numbers are one-based. No conversational retrieval, external model APIs, vision interpretation, OCR languages beyond English, hybrid search, reranking, or hosting in version one.

## Evaluation

Freeze seven answerable questions with expected facts and pages and three unanswerable questions before running models. Use the January 2024 OSHA/NIOSH handbook. Measure hit@4 over seven answerable questions, supported answer accuracy over those seven, and correct refusals over the other three. Manual grades require cited evidence and no material unsupported claim. Evaluate all three chunk sizes with other settings held constant. Choose highest hit@4, then answer accuracy, then correct-refusal rate, then smaller size. These are development results, not held-out estimates.

## Development workflow

Plan → setup → implementation. Git repository is code/ only; sibling worktrees contain branches from that repository. Skills, original brief and figure, model weights, uploaded documents, and indexes stay outside Git. Commit source, tests, lockfile, evaluation data/results, plot, and documentation. Use focused parallel tasks only after shared interfaces are settled; integrate and verify centrally. The user supplies the public remote.
