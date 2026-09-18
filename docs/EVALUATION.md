# Reproducing the experiment

Download the public-domain handbook from the URL recorded in `evals/questions.json`.
Keep the PDF outside the repository. The runner verifies its SHA-256 before model
calls. That file freezes seven answerable questions, three unanswerable questions,
expected facts, physical PDF pages, and grading rules before tuning.

With Ollama running and both documented models installed:

```sh
uv run python -m pdf_qa.evaluate run --pdf ../data/osha-small-business.pdf \
  --questions evals/questions.json --output evals/results/my-run
```

The default run evaluates 300, 800, and 1500 **characters**, each with 60-character
overlap and top four retrieval. Native extraction/OCR and persisted indexes use
the same pipeline as the app. Set `PDF_QA_DATA_DIR` to keep indexes outside Git.
Run one model experiment at a time. Every output directory must be new; results
are saved after every question. An interrupted run retains completed questions
but cannot produce a final report. Start a new run; cached indexes remain reusable.

`--sizes 800` runs a subset. `--retrieval-only` skips answer generation for retrieval
probes; these results cannot produce answer metrics. Reports from subsets are
explicitly marked as incomplete three-size experiments.

Each run saves the frozen questions, their byte-level hash, source PDF hash,
timestamps, model names and digests, prompt version, index manifests, settings,
passages, scores, generated answers, citations, timings, and operational errors.
Errors remain separate from `NOT FOUND` refusals. Indexing errors count as failures
for all questions at that size. Generation errors retain retrieval evidence.

## Manual grading

Copy `grades-template.json` to `grades.json` in the run directory. Review every
answer against the expected facts **and the actual cited retrieved passages**.
For every answerable question fill boolean `answer_correct`, boolean
`citation_supported`, and a specific justification in `notes`. Correct means all
expected facts are present, the cited passages support them, and no material
unsupported claims appear. Refusals and operational errors are incorrect.
For unanswerable questions supply review notes; refusal success is computed from
the recorded answer, never from a human override. Do not change the raw outputs.

```sh
uv run python -m pdf_qa.evaluate report --results evals/results/my-run \
  --grades evals/results/my-run/grades.json
```

Reporting rejects missing grades, missing justifications, inconsistent grades,
incomplete runs, and changed question provenance. It writes `summary.json`,
`summary.csv`, and `hit-at-4.png`. It does not overwrite an existing report.
For revised grades, copy the raw JSON files and frozen questions into a fresh
directory, retain the earlier report, and document the reason for regrading.

- Hit@4: answerable questions with an expected page among the first four retrieved
  passages, divided by **7**. This page-level proxy does not prove passage relevance.
- Answer accuracy: fully correct, supported answers, divided by **7**.
- Correct-refusal rate: explicit `NOT FOUND` refusals on unanswerable questions,
  divided by **3**. Operational errors never count as refusals.

Select the highest hit@4, then highest answer accuracy, then highest refusal rate,
then smaller chunk size. Metrics are development-set results, not an independent
generalization estimate. Record two observed failures with actual evidence in
the README; additional exploratory questions must remain outside these metrics.

The committed run uses AI-assisted manual review by Codex, not independent human
grading. See [measured results and failure analysis](RESULTS.md). A reviewer can
reproduce the run and replace those judgments with independently documented grades.
# Expanded benchmark

For the three-document development/held-out suite and paired OCR checks, see
[Phase 2A](PHASE2A.md) and its [baseline results](PHASE2A-RESULTS.md). The original
ten-question experiment above remains a separate, unchanged regression suite.

For paired experiments, [Phase 2B](PHASE2B-RESULTS.md) documents generation-only
comparison and [Phase 2C](PHASE2C-RESULTS.md) documents `--mode retrieval` with fixed
generation, extraction, and source indexes. Both reject their candidates and
preserve the original production behavior. A successful comparison command does
not imply promotion; inspect its acceptance gates and review legacy results
separately.
