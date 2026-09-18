# Run and review provenance

This note supplements the original raw result files without rewriting them.

- Run date: 2026-09-18. Repository revision at run start: `6dd43b9`.
- Code: Python 3.12.14; locked Python dependencies in `uv.lock` at that revision.
- Runtime: Ollama 0.34.1, Tesseract 5.5.3 with English data; Apple M5 Pro with 24 GB memory.
- Answer options: temperature 0, seed 42, num_ctx 8192, num_predict 1200, think false; prompt grounded-v1 from `pdf_qa.pipeline`.
- Embedding query instruction: "Given a question, retrieve relevant document passages that answer the question." Document passages have no instruction prefix. Embeddings are normalized and searched with inner product.
- Model names and immutable digests, source document hash, questions hash, extraction settings, raw retrieved text, scores, answers, and timings are recorded in the JSON files.
- The 800-character index was already built as a smoke check; the experiment loaded it. Its shorter ingest time is not a fair uncached indexing benchmark.
- Grading: AI-assisted manual evidence review by Codex (primary agent), independently cross-checked by a second coding agent. No independent human grader participated. Each accepted answer was checked against its cited text and expected facts. Raw results were not edited to improve scores.
- After the run started, the SDK-based cloud-alias check was replaced with raw model metadata validation because the SDK drops remote fields. The actual run used verified local model weights with OLLAMA_NO_CLOUD=1; no document was sent to a remote model. Prompt, generation options, extraction, embeddings, and retrieval did not change. Subsequent integration checks verify the new guard.
- This is one ten-question development experiment, not a repeated-trial estimate or held-out benchmark. Detailed failures and limitations are in `docs/RESULTS.md` at repository root.
