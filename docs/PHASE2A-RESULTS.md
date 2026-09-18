# Phase 2A baseline results

Phase 2A is complete: the expanded benchmark and evidence-quality modules are
implemented. No production prompt, extraction, retrieval, model, or UI changes
were made. No held-out questions were run. Phase 2B has not started.

## Experiment

Run on September 18, 2026, on the local Mac with Ollama 0.34.1,
`qwen3:8b`, and `qwen3-embedding:0.6b`. The frozen baseline started from clean
revision `b57230bf9c96eb3562e04403580afd391857c2bb`: 800-character chunks,
60-character overlap, top four passages, temperature 0, seed 42, and thinking
disabled. Model digests, source hashes, exact runtime details, code/prompt/lock
hashes, and generation settings are in [run.json](../evals/phase2a/results/baseline-01/run.json).

All 36 native development cases, six paired OCR cases, and ten separate legacy
regression cases completed without operational errors. The 24 held-out questions
remain unrun. Results were manually reviewed by Codex agents against actual
passages and cited chunk IDs, with primary-agent integration. This is AI-assisted
review, not independent human adjudication. See [methodology](PHASE2A.md).

## Native development results

| Document | Page hit@4 | Complete evidence@4 | Strict supported accuracy | False refusals | Correct refusals |
|---|---:|---:|---:|---:|---:|
| OSHA | 8/8 | 8/8 | 7/8 | 0/8 | 4/4 |
| NIST AI RMF | 6/8 | 6/8 | 2/8 | 5/8 | 4/4 |
| NIST CSF | 7/8 | 7/8 | 3/8 | 4/8 | 4/4 |
| Total | 21/24 | 21/24 | 12/24 | 9/24 | 12/12 |

Unsupported-answer rate is **1/15 successful non-refused answers**. That failure
is missing citation coverage, not a fabricated statement: `nist-ai-07` adds a
relationship between transparency, explainability, and interpretability from
retrieved `p22-c1` but cites only page-21 chunks that do not support that added
relationship. The required definitions themselves are correct and cited.

The strict accuracy score includes two borderline completeness failures:

- `osha-08` correctly answers the permission and source-credit questions but
  omits the public-domain/copyright-free detail in the frozen expected fact.
  Its cited chunk also omits the public-domain clause.
- `nist-csf-06` correctly distinguishes Current and Target Profiles but omits
  the Current Profile's inclusion of outcomes the organization is *attempting*
  to achieve, although the cited evidence contains that qualifier.

The published grades preserve the frozen all-required-facts rule. Accepting both
borderline answers under a looser question-level rubric would give **14/24**,
not 12/24. That is a sensitivity illustration, not a replacement result or a
post-hoc corpus change. Future annotation revisions should separate required
answers from explanatory details before another experiment.

## Failure priorities for the next reviewed phase

1. **Generation/refusal behavior:** six false refusals occurred despite complete
   retrieved evidence: `nist-ai-04/05/06` and `nist-csf-02/07/08`. Together with
   the two completeness omissions, this yields eight `generation_failure`
   cases. The missing answers include intact definitions and lists; retrieval
   alone cannot explain these failures. Test one focused generation change at a
   time while preserving the refusal checks. Distracting passages, extraction
   artifacts, and prompt interpretation are hypotheses, not proven causes.
2. **Retrieval completeness:** three cases miss required evidence:
   `nist-ai-01` (2028 review deadline), `nist-ai-03` (risk components), and
   `nist-csf-03` (the complete tier list). Source extraction contains the missing
   material, so the observed failure is retrieval rather than extraction loss.
   Measure whether a broader candidate pool plus a simple selection strategy
   recovers it before choosing hybrid search or a reranking dependency.
3. **Citation coverage:** one answer has a material extra claim absent from its
   cited chunks. Valid chunk IDs do not guarantee complete claim support.
   Keep this case in future reviews; avoid adding a new verification model
   without first testing a simpler grounded-answer change.

These are priorities, not implemented fixes. The next phase should still contain
only one or two modules. OCR redesign, multi-document chat, and hosting have no
evidence-based priority from this small run. Review this baseline before choosing
the next intervention. Preserve the held-out set until the agreed final check.

## Paired OCR results

| Original question | Native | Scan + automatic OCR | Mixed + forced OCR |
|---|---|---|---|
| OSHA waste cans | Correct | Correct | Correct |
| NIST AI review deadline | Retrieval miss; refused | Correct | Correct |
| NIST CSF numbering gaps | Correct | Correct | Correct |

Both OCR groups score 3/3 for complete evidence and supported answers; pooled
OCR is 6/6, separately reported. Refusal specificity cannot be estimated from
these answerable-only variants. The NIST AI improvement coincides with changed
extracted text and chunks; it does not prove OCR generally improves retrieval.
All selected OCR facts survived extraction. Other CSF table content was damaged
by OCR, so these six successes do not establish full-document OCR fidelity.

## Latency and regression

Native retrieval median/p95: **0.027/0.029 seconds** across 36 queries.
Native generation median/p95: **1.005/2.518 seconds**. OCR retrieval median/p95:
**0.025/0.026 seconds**; OCR generation: **1.420/1.652 seconds** across six queries.
Nearest-rank p95 is used; for six samples it is simply the maximum. These are
single sequential local runs, not throughput or cold-start guarantees.

Ingestion is excluded from those timings. Forced-OCR ingestion took about
70.59 seconds for OSHA, 50.09 for NIST AI, and 32.14 for NIST CSF. Native OSHA
used a cached index; timings across ingestion modes are not controlled speed
comparisons. See the individual index manifests and times in `run.json`.

The separate [legacy regression](../evals/phase2a/results/legacy-01/) retains
7/7 page hits, 7/7 supported correct answers, and 3/3 correct refusals at 800
characters. It does not establish generalization to the new documents and is
not a fresh three-size selection experiment.

## Audit artifacts

- [Cases, passages, answers, extraction evidence, and review packet](../evals/phase2a/results/baseline-01/)
- [Manual fact-level grades](../evals/phase2a/results/baseline-01/grades.json)
- [Validated metrics and latencies](../evals/phase2a/results/baseline-01/summary.json)
- [Generated per-group report](../evals/phase2a/results/baseline-01/report.md)

Only code, public-source evaluation text, and documentation are committed.
PDFs, model files, private app data, skills, and sibling worktrees remain outside
the Git repository. No new dependencies or production abstractions were needed.
