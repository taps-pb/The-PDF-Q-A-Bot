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

## Final result

The local capstone is ready for handoff. The demonstrated audit blocker is fixed;
there are no remaining known functional blockers within the agreed scope.
**This is not a production-grade answer-accuracy claim.** Answers can omit facts,
refuse answerable questions, or lack full citation support. The existing UI
caption now says so explicitly. No prompt, parser, retrieval, model, dependency,
index, or extraction behavior was changed to improve final evaluation results.

The frozen inference revision is `35c75a36fac66c1cda98bc31562601091fcf36fd`.
The held-out run was completed once on 2026-09-19, using all 24 previously unrun
questions. All 24 cases and the ten legacy cases retained their original raw
responses; replay through the original parser reproduces every saved answer.
Every case succeeded operationally on its first model response; no repair was
needed. Historical control traces remain unavailable and were not reconstructed.

| Held-out metric | Result |
|---|---:|
| Expected-page hit@4 | 17/18 |
| Complete evidence@4 | 14/18 |
| Strict supported answer accuracy | 11/18 (61.1%) |
| False refusals on answerable questions | 5/18 |
| Correct refusals on unanswerable questions | 6/6 |
| Unsupported / successful non-refused answers | 2/13 |
| Operational errors | 0/24 |

Supported accuracy by document is OSHA **5/6**, NIST AI RMF **3/6**, and NIST CSF
**3/6**. Every document's two unanswerable cases were correctly refused. The
held-out questions were not used for tuning, but come from the same three PDFs
as development: this is a question holdout, not an unseen-document evaluation.
Grades are AI-assisted manual review by Codex root, not independent human grading.
The questions are now consumed and must not be described as untouched in future
experiments. No held-out comparison/tuning loop was run.

The separate fresh legacy regression remains **7/7 supported answers**, **3/3
correct refusals**, and zero operational errors. Its raw attempts are now captured
as well. The legacy runner does not record a Git revision; execution attribution
is documented in its review note and tied to the expanded run's frozen revision.

## Remaining limitations, not hidden fixes

- `osha-15` and `nist-ai-16` refuse despite complete retrieved evidence.
- `nist-csf-13`, `nist-csf-17`, and `nist-csf-18` refuse after retrieval misses
  required details. Extracted source pages contain those details intact.
- `nist-ai-13` retrieves a comparison/gap clause but misses the following
  action-plan sentence. Its proposed action recommendation lacks cited support
  and omits a frozen qualifier. The full source contains the missing evidence;
  it was not available in the retrieved context.
- `nist-ai-15` supplies both required TEVV facts, but adds a lifecycle-cooperation
  statement supported only by an uncited retrieved passage. The unchanged strict
  citation-level rubric counts that response as unsupported. Citation-ID validity
  does not establish semantic support for every claim.

There is no after-the-fact relaxation of annotations or accuracy target. Broader
experiments were rejected when they regressed quality, rather than added to the
app. Phase 3's independent review is [recorded separately](PHASE3-REVIEW.md).
Use this app to inspect and navigate document evidence; verify source passages
before relying on answers, especially for consequential decisions.

## Verification completed

- **117 tests passed**, including the existing three real local model/OCR tests
  and six Streamlit interaction tests. Ruff lint and changed-file formatting pass.
- An additional Streamlit AppTest smoke used a synthetic PDF through the actual
  extraction, local embeddings, persisted FAISS index, and local answer pipeline.
  Upload/build, a supported answer, page citation, retrieved scores, a correct
  refusal, and saved-index reload in a fresh session all passed. Only the upload
  widget was supplied synthetic bytes; the document/model pipeline was not mocked.
  Temporary synthetic indexes were automatically cleaned up.
- A temporary loopback-only Streamlit instance returned health `ok` and homepage
  HTTP 200. It was stopped afterward; the existing port-8501 instance was untouched.
  This is an application/HTTP smoke check, not a manual browser visual review.
- Held-out retrieval median/p95 was **0.028/0.037 seconds**; generation was
  **1.254/2.410 seconds**. These are single-run local timings excluding indexing,
  not a hardware-independent speed guarantee.
- Original prompt, response schema, parsing, retrieval, and ingestion match the
  retained production logic. Runtime code changes are limited to trace capture
  and the wording of the existing UI warning. No dependencies were added.
- PDFs, model weights, application indexes, secrets, root skill installations,
  and sibling worktrees are not tracked. Git history preserves rejected experiments
  without enabling their runtime implementations.

## Run and audit

Follow [SETUP.md](SETUP.md) to start cloud-disabled Ollama and the Streamlit app.
The repository remains `code/`; local data and worktrees stay outside it.

- [One-time held-out run, provenance, raw responses, and manual grades](../evals/release/results/heldout-01/)
- [Held-out report](../evals/release/results/heldout-01/report.md)
- [Final legacy regression and review attribution](../evals/release/results/legacy-01/)
- [Phase 3 independent review and rejection](PHASE3-REVIEW.md)

No remaining feature phase is planned. Future work should respond to a concrete
user need or reproduced defect, not expand the architecture by default.
