# Final verification and handoff

## Scope frozen before held-out inference

The user authorized blockers-only completion on 2026-09-19. No new product
features, models, dependencies, prompt tuning, or retrieval changes are included.
Production keeps `grounded-v1`, dense top-four retrieval, and the measured
800-character chunks with 60-character overlap. Phase 3 is rejected and its
records are preserved without enabling its generation code.

The demonstrated audit blocker is missing original-generation response traces.
Fix it before final evaluation: capture each raw model response, reset traces
for each call, and retain both attempts on repair failures in both existing
evaluation runners. Record the answer schema as provenance. Do not invent or
backfill unavailable historical control responses. Generation requests and
answer parsing must remain unchanged.

After tests pass, freeze the release implementation and run the 24 previously
unrun held-out questions once, plus the separate ten-question legacy regression.
The held-out set has 18 answerable and six unanswerable cases across three PDFs;
it has no OCR variants. Grade actual outputs against frozen required facts and
cited passages with explicit AI-assisted reviewer attribution. Do not tune or
rerun to improve held-out results. Any future use of these questions is no longer
an untouched holdout.

Acceptance is for a working local capstone, not a production-grade accuracy
claim: unit tests, existing local model/OCR integration tests, UI interaction
tests, and launch/health smoke checks must pass. The legacy suite must retain
7/7 supported answers and 3/3 correct refusals. Operational failures must be
investigated; report held-out answer quality honestly without inventing an
after-the-fact accuracy threshold. Existing unsupported answers and false
refusals are disclosed limitations, not hidden by citation-ID validation.

Final steps are to document results and limitations, verify that no PDFs,
private uploads, indexes, model weights, or skill installations are tracked,
then integrate and push the approved `code/` repository. No further feature
phase is planned.
