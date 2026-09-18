# Phase 2A: benchmark and evidence quality

This phase adds two modules: a versioned multi-document benchmark (`pdf_qa.suite`)
and explicit evidence grading (`pdf_qa.evidence`). It does not change extraction,
chunking, retrieval, prompts, models, or the Streamlit interface. Implementation
stops after this baseline for review before the next phase.

## Frozen corpus

The manifests in `evals/phase2a/` identify exact editions, download URLs, SHA-256
hashes, physical PDF page numbers, expected facts, and supporting excerpts.
The source documents are the January 2024 OSHA/NIOSH Small Business Safety and
Health Handbook, NIST AI RMF 1.0, and NIST CSF 2.0. PDFs and generated variants
remain outside the Git repository.

Each document has 20 new questions: 14 answerable and six unanswerable.
Development contains eight answerable and four unanswerable questions per
document; held-out contains six answerable and two unanswerable questions.
That is 36 development and 24 held-out questions. The original ten OSHA
questions remain a separate regression suite and are not included in those 60.

Questions cover direct facts, lists, numbers, identifiers, and multiple passages.
Related question families cannot cross splits within a document. This is not a
claim of completely unseen concepts: for example, profile concepts occur in
both NIST documents. Source annotations were cross-reviewed before inference.
Held-out annotations are validated, but held-out questions are not submitted
to the models during Phase 2A. These are small, manually constructed samples,
not representative estimates of performance on arbitrary PDFs.

## Controlled OCR pairs

The first development question from each document is paired with two variants:

- `scan`: rasterize only its evidence page at 300 DPI, leaving no native text on
  that page; run automatic OCR.
- `mixed`: use the same raster page plus a native header in an added top margin;
  run forced OCR. The original image is not obscured.

All other pages remain in the PDF and physical page numbering is unchanged.
The variants therefore retain the full-document retrieval competition. Forced
OCR processes the entire mixed PDF, not just the changed page. This is a test
of the existing manual override, not automatic mixed-page detection. The six
variant cases are paired robustness checks, not six independent questions.
They are reported separately from the 36 native cases. Clean rasterizations do
not approximate all camera scans, blur, skew, handwriting, or difficult layouts.

## Reproduce

Run from the Git repository or an implementation worktree with the locked
development dependencies installed. Start local Ollama with cloud disabled,
install the two models and Tesseract as described in [SETUP.md](SETUP.md), and
use an external corpus directory. For the normal `code/` checkout:

```sh
mkdir -p ../data/corpus
curl -fL https://stacks.cdc.gov/view/cdc/148137/cdc_148137_DS1.pdf -o ../data/corpus/osha.pdf
curl -fL https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf -o ../data/corpus/nist-ai.pdf
curl -fL https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf -o ../data/corpus/nist-csf.pdf
uv run python -m pdf_qa.suite validate --corpus-dir ../data/corpus
uv run python -m pdf_qa.suite prepare --corpus-dir ../data/corpus
PDF_QA_DATA_DIR=../data/app uv run python -m pdf_qa.suite run \
  --corpus-dir ../data/corpus --split development \
  --output evals/phase2a/results/my-run
```

`validate` checks source hashes, page counts, excerpts, question counts, unique
IDs, and family isolation. `prepare` saves deterministic variants and a recipe
manifest outside Git; it refuses to overwrite different variants. Hashes may
change with rendering library versions, so preserve the locked environment.
`run` requires an explicit split and a fresh output directory. No implicit
all-splits run exists. Use only `development` for this phase.

Review `review.md` against actual retrieved passages and cited chunk IDs. Copy
`grades-template.json` to `grades.json`, then fill every judgment and explanation.
Do not grade by matching expected strings or trusting generated answers.

```sh
uv run python -m pdf_qa.suite report \
  --results evals/phase2a/results/my-run \
  --grades evals/phase2a/results/my-run/grades.json \
  --reviewer 'Your name; manual evidence review'
```

The shipped baseline uses AI-assisted manual evidence review by Codex agents;
it is not independent human adjudication. Every fact is assessed for retrieved
support, answer correctness, and support in the cited passages. Evidence pieces
within one alternative are conjunctive; one complete alternative is sufficient.
Additional material claims without support in the cited passages invalidate an
otherwise correct answer, even when another retrieved passage supports them.
The frozen required facts control completeness; the results write-up explicitly
identifies borderline omissions rather than silently relaxing the rubric.

## Metrics and failure attribution

- Page hit@4: at least one annotated page appears among four retrieved passages.
  This legacy diagnostic does **not** prove the answer is present.
- Evidence coverage@4: every required fact is supported by the actual passages.
- Supported answer accuracy: all required facts are answered, cited, and supported,
  with no unsupported material claim. Denominator: answerable questions.
- False-refusal rate: `NOT FOUND` on an answerable question. Correct-refusal rate:
  `NOT FOUND` on an unanswerable question. Operational errors are never refusals.
- Unsupported-answer rate: unsupported claims among successful, non-refused
  answers, not among all questions. Empty denominators are `null`, not zero.

Reports include counts and denominators, per-document native metrics, separate
OCR metrics and pair IDs, operational errors, and retrieval/generation median
and nearest-rank p95 latency. Indexing and extraction time are recorded separately
and excluded from query latency. Timings are sequential local measurements, not
a load test; model loading and machine state can affect them.

Failure categories distinguish extraction loss, incomplete retrieval, generation
failure, unsupported answer, and operational error. Inspect extracted evidence
pages to distinguish extraction loss from retrieval loss. A failed generation
with complete retrieved evidence does not prove why the model failed: context
distraction, formatting, and model limitations remain hypotheses unless tested.

Each run preserves selected cases, actual passages/scores, answers/citations,
extracted evidence pages, settings, model digests, runtime versions, code revision
and dirty state, prompt and lock hashes, literal generation parameters, source
and variant hashes, index manifests, and artifact checksums. Reporting rejects
changed cases/results and incomplete grades. Do not overwrite a published run.

Run the separate ten-question regression at the fixed 800-character setting:

```sh
PDF_QA_DATA_DIR=../data/app uv run python -m pdf_qa.evaluate run \
  --pdf ../data/corpus/osha.pdf --questions evals/questions.json \
  --output evals/phase2a/results/my-legacy-run --sizes 800
```

Review and report it using [EVALUATION.md](EVALUATION.md). Do not merge its
denominators with the expanded benchmark or reuse old grades without review.
