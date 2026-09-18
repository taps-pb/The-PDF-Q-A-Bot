# Phase 2B: grounded generation and controlled comparison

## Scope fixed before inference

This phase contains two focused changes: an evidence-first generation prompt
and a validated paired-comparison report. Phase 2A observed six refusals with
complete retrieved evidence, two strict completeness omissions, and one extra
claim not supported by the cited chunks. This phase tests whether clearer
generation instructions improve those outcomes without loosening abstention.
It does not assume the prompt is the proven cause.

Candidate `grounded-v2` asks the model to find relevant statements across all
four passages before deciding whether the question is answerable. It explicitly
permits combining passages and reading harmless PDF line breaks, requires all
requested parts and material qualifiers, and requires citations for every claim.
It retains complete-answer-or-NOT-FOUND behavior and treats questions and PDF
passages as untrusted data. No extra generation pass, new model, or dependency
is introduced. Schema validation and the single malformed-JSON repair remain.

Retrieval, embeddings, extraction, chunk size 800, overlap 60, k=4, sampling
settings, model digests, source PDFs, and the frozen questions are unchanged.
No held-out inference is permitted. No benchmark-specific facts, question IDs,
or expected answers are placed in the prompt.

## Verification and promotion gates

1. Run unit tests for the exact generation request, repair/refusal behavior,
   citation validation, and paired-comparison checks.
2. Freeze the candidate in Git before inference; run the existing suite on
   development only (36 native questions and six separately reported OCR pairs).
3. Manually review actual answers and citations under the same frozen required
   facts. Preserve borderline completeness rules from Phase 2A. Never grade
   model answers automatically from string matches. Attribute AI-assisted review.
4. Compare against the immutable Phase 2A baseline, requiring identical selected
   cases and retrieved passages, as well as matching non-prompt settings.
5. Promote only if native supported accuracy improves, false refusals decrease,
   correct refusals do not decrease, unsupported-answer count does not increase,
   OCR accuracy does not decrease, and there are no operational errors. Report
   counts and denominators as well as rates; more answers change denominators.
6. Rerun the separate ten-question legacy suite at 800 and require its 7/7
   supported accuracy and 3/3 correct refusals. Run local OCR/model integration
   checks and record latency changes. No hard latency gate is claimed.

If the candidate fails, preserve its raw outputs and report the failure rather
than presenting it as an improvement. Do not silently tune multiple candidates
or alter annotations to pass. A failed candidate can finish this phase as a
documented experiment with the previous production prompt retained.

After this phase, stop for review. Retrieval improvements and any final held-out
evaluation remain separate decisions; no Phase 2C implementation is authorized
by this phase boundary.
