# Phase 2C: retrieval coverage

## Scope fixed before inference

This phase tests one retrieval candidate and extends paired comparison to
retrieval changes. Generation remains `grounded-v1`; the rejected Phase 2B prompt
is not used. No held-out inference, question rewrites, model changes, or new
dependencies are permitted. Worktrees stay outside the `code/` repository.

The candidate combines dense and lexical search using reciprocal rank fusion:
20 dense candidates plus up to 20 positive BM25 candidates, equal rank weights,
RRF constant 60, and four final passages. BM25 uses k1=1.2, b=0.75, positive
log-IDF, lowercase alphanumeric tokens, and a fixed small English stopword list.
No corpus-specific terms, question IDs, expected pages, stemming, or learned
reranker are used. Ties are broken by dense rank then original chunk position.
If no query tokens match, dense retrieval order is preserved.

The lexical statistics are computed from the existing document's chunks in
memory for each query. This deliberately avoids a new index format or dependency
for the existing 200-page limit. Index persistence, OCR, embeddings, 800-character
chunks, 60-character overlap, context size, and generation options remain fixed.
Hybrid scores are RRF scores, not cosine similarities or confidence estimates;
the interface must label them accurately if the candidate is promoted.

Algorithm references: [the original RRF paper](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
defines rank fusion; [Elastic's BM25 documentation](https://www.elastic.co/docs/reference/elasticsearch/index-settings/similarity)
documents the standard k1=1.2 and b=0.75 defaults. These sources inform the
implementation, not a claim that hybrid retrieval will improve this corpus.

## Experiment and promotion rules

Freeze and run a fresh dense control with expanded retrieval/extraction
provenance, then freeze the single hybrid candidate. Each run uses the same
36 native development questions plus six separately reported OCR variants.
Check the fresh control against Phase 2A and disclose any output variation.
Manually review every changed retrieval/answer under the existing strict frozen
rubric; unchanged reviewed outputs may reuse judgments with explicit attribution.
The 24 held-out questions stay unrun.

The comparator must require matching cases, source/index identities, extraction
code, prompt and generation implementation, model digests, runtime, and fixed
settings. Only retrieval policy and resulting passages/evidence judgments may
change. Preserve the generation-only comparator's stricter existing behavior.

Promotion requires native complete evidence@4 to improve, native supported
accuracy and page hit@4 not to fall, false refusals not to rise, correct refusals
not to fall, unsupported-answer counts not to rise, OCR evidence and accuracy
not to fall, and no operational errors in either run. Compare both overall and
per-document outcomes and list every regression; do not conceal tradeoffs behind
one aggregate metric. Report counts, denominators, and query latency separately
from indexing. There is no predeclared hard latency threshold.

Run the separate ten-question legacy suite at 800; require 7/7 supported answers
and 3/3 correct refusals. Run unit and local OCR/model integration tests. Promote
only when all gates pass. If the candidate fails, preserve its outputs and retain
dense retrieval; do not silently tune another candidate or rewrite annotations.
Finish this phase with a report and stop for review before another phase or any
held-out evaluation.
