# Phase 3: evidence-backed generation candidate

## Frozen scope before implementation and inference

The user authorized Phase 3 on 2026-09-19 and requested an independent model's
testing report before integration. Work remains on `feat/phase3` in the sibling
`worktrees/phase3` directory. Do not merge or push until that report is reviewed.
Production `main` remains at `c1168a6` while this candidate is evaluated.

Two focused deliverables:

1. A quote-bearing generation response and deterministic structural validator.
2. Adversarial tests and preserved development evaluation with audit traces.

Dense retrieval, four passages, extraction/OCR, indexes, models, dependencies,
chunking, and generation parameters remain unchanged. Do not combine this with
the rejected Phase 2B prompt or Phase 2C hybrid retrieval. No held-out evaluation,
cloud inference, new model downloads, or automatic promotion.

## Shared interface for independent testing

`pdf_qa.grounding.parse_grounded_answer(content, hits) -> Answer` accepts JSON
with exactly `claims` and boolean `refused`. Each claim has exactly nonempty
`text` and nonempty `evidence`; each evidence item has exactly `chunk_id` and
nonempty `quote`. Every ID must name a retrieved passage and its quote must be
a substring of that same passage after collapsing whitespace only. Case,
punctuation, and numbers are not normalized away. Refusal requires empty claims
and returns the existing `Answer("NOT FOUND", [], [], True)`.

For an answer, claim texts are stripped and joined with single spaces. Citation
IDs are deduplicated in first-use order; physical page numbers are unique and
sorted. At most 12 claims, four evidence items per claim, 12,000 answer characters,
and 100,000 raw response characters are accepted. Reject duplicate JSON keys,
unknown/extra fields, invalid types, unknown chunk IDs, empty values, and invalid
quotes. An affirmative answer cannot be the reserved `NOT FOUND` response.

**Quote membership is not semantic entailment.** A real quote can accompany a
false or irrelevant claim. This candidate improves inspectable attribution, not
proof of truth. Adversarial tests must explicitly demonstrate that limitation.
Manual fact-level grading remains mandatory. Do not label this a hallucination
detector, independent verifier, or guaranteed grounded-answer system.

The model receives untrusted questions/passages separately from system rules,
must copy relevant evidence before stating each claim, and must refuse missing
facts without inventing details. Preserve the one-repair limit: malformed JSON
or invalid quotes get one repair; repeated invalid output raises `AppError`.
Valid refusals are not retried. Transport/model failures remain operational errors.
No retries or retrieval fallback are introduced to improve benchmark outcomes.

The benchmark saves original generation responses, including an invalid first
attempt, so quote validation and repair behavior can be audited. Record the
schema and parser hash as additional provenance. No private uploads are committed;
only the existing public development corpus is used for published experiments.

## Experiment and gates

Run a fresh dense/original-generation control, then freeze one candidate revision
before any candidate inference. Use the same 36 native development questions and
six separately reported OCR variants. Reuse old semantic grades only after exact
case, ordered-passage, and answer equality; disclose attribution. Otherwise grade
afresh under the frozen rubric. Do not rewrite annotations or tune a second
candidate after observing outcomes.

Compare in generation mode: identical cases and ordered retrieved passages are
required. Native strict supported accuracy must improve, false refusals must not
increase, unsupported-answer counts must not increase, correct refusals must not
decrease, and both runs must have zero operational errors. OCR evidence/accuracy
must not decrease. Additionally, no document may lose supported accuracy. The
separate legacy suite must retain 7/7 supported answers and 3/3 correct refusals.
Report latency and repair counts; no hard latency threshold is declared.

The existing comparator provides aggregate gates; per-document and legacy gates
require explicit review. Unit/integration success alone is not promotion evidence.
Preserve runs even if invalid responses cause the candidate to fail. Pending
manual grades or external testing mean pending promotion, not an implicit pass.

The independent tester receives the interface in a copy-paste chat prompt and
works separately on synthetic cases without concurrent live inference. The main
agent reviews the tester's findings with the user before any merge or push.

## Recorded outcome (after the single candidate run)

The candidate fails promotion: native supported accuracy is 8/24 versus 12/24,
with nine operational errors and two unsupported answers. Legacy accuracy is
3/7. See [the full results](PHASE3-RESULTS.md). No inference code was retuned.
The branch remains isolated pending the user's independent tester report;
production is unchanged and nothing has been merged or pushed.
