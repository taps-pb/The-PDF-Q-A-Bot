# Phase 2C: hybrid retrieval rejected, dense retrieval retained

Hybrid retrieval recovered all three missing evidence sets, but supported answer
accuracy fell and incomplete citation support increased. **The candidate is not
enabled in the app.** Production retains dense top-four retrieval, cosine scores,
and the original `grounded-v1` prompt. This phase ships retrieval-aware paired
comparison, expanded provenance, regression tests, and the preserved experiment.
No new dependencies, index formats, cloud calls, or model changes were introduced.

## Controlled experiment

The [scope and gates](PHASE2C.md) were committed before inference. One candidate
combined the top 20 dense passages with up to 20 positive BM25 matches using
equal-weight reciprocal rank fusion (constant 60), returning four passages.
BM25 used k1=1.2 and b=0.75, with fixed tokenization and stopwords. There was no
corpus-specific tuning or second candidate after reviewing results.

A fresh dense control ran from clean revision `71fb8ac48a3f442357e16e169bf73f6512ed4c04`.
The hybrid candidate ran from clean revision `4bb843789f9f806c3222ef00d1e97b8c913bd553`.
Each run used 36 native development questions and six paired OCR variants.
All 24 held-out questions remain unrun. The ten original OSHA regression
questions were also run separately against the candidate at chunk size 800.

The comparator verifies matching selected cases, PDF/index identities and
checksums, extraction code, prompt and generation implementation, model digests,
runtime, locked dependencies, chunking, and generation settings. Only retrieval
policy and resulting passages/evidence grades differ. Forty-one of 42 cases have
different ordered passage objects; `nist-ai-07` retains identical passages.
Cosine and RRF scores are different metrics: their numerical deltas are not
computed or presented as quality improvements.

Every fresh-control case, ordered chunk object, and answer/citation object exactly
matches the previously reviewed Phase 2A output. Its grades therefore reuse those
judgments with explicit attribution; timings and provenance are new. Candidate
grades use AI-assisted manual semantic review under the same frozen rubric:
the root reviewed OSHA and legacy questions; separate agents reviewed each NIST
document. The root integrated the grades and cross-reviewed the OSHA citation
regression. These are not independent human judgments or generalization estimates.

## Results and decision

| Native development metric | Dense control | Hybrid candidate |
|---|---:|---:|
| Page hit@4 | 21/24 | 24/24 |
| Complete evidence@4 | 21/24 | 24/24 |
| Strict supported answer accuracy | 12/24 | 11/24 |
| False refusals | 9/24 | 9/24 |
| Correct refusals on unanswerable questions | 12/12 | 12/12 |
| Unsupported answers / successful non-refused answers | 1/15 | 2/15 |
| Operational errors | 0 | 0 |

| Document | Complete evidence, control / candidate | Supported accuracy, control / candidate | False refusals, control / candidate |
|---|---:|---:|---:|
| OSHA | 8/8 / 8/8 | 7/8 / 5/8 | 0/8 / 1/8 |
| NIST AI RMF | 6/8 / 8/8 | 2/8 / 4/8 | 5/8 / 3/8 |
| NIST CSF | 7/8 / 8/8 | 3/8 / 2/8 | 4/8 / 5/8 |

Both OCR evidence coverage and supported accuracy remain 6/6: 3/3 automatic scan
OCR and 3/3 forced mixed-page OCR. There are no OCR unsupported answers or errors.
These paired variants are not six additional independent questions. The separate
legacy candidate run retains 7/7 supported answers, 3/3 correct refusals, and zero
errors. It is compared with the frozen prior legacy regression, not a newly run
legacy control.

The generated [comparison](../evals/phase2c/results/comparison-01.json) rejects
the candidate on two gates: native supported accuracy drops, and the native
unsupported-answer count rises. All other development gates pass. Passing the
legacy suite does not offset the expanded-benchmark failures.

## Improvements and every regression

- `nist-ai-01`: the review-by-2028 evidence is now retrieved and correctly answered.
- `nist-ai-03`: the probability/consequence definition of risk is now retrieved
  and correctly answered, without the invention seen in the rejected Phase 2B prompt.
- `nist-csf-03`: all four Tier names and mappings are now present in `p31-c4`,
  but the model still refuses. Its failure changes from incomplete retrieval
  to generation despite complete evidence.
- `osha-04` regresses from supported correct to incomplete chunk attribution.
  The answer remains factually correct and cites physical page 49, but only cites
  `p49-c1`, which ends at "other control". The remaining "circuit type device"
  phrase is in retrieved but uncited `p49-c2`. Under the frozen citation-level
  rule, the complete second claim lacks cited support. This is **not fabricated
  safety guidance**; the same rule already penalizes the uncited additional
  relationship in `nist-ai-07`.
- `osha-05` newly refuses despite rank-one `p76-c2` supplying both the defective
  ladder tag wording and removal-until-repair/replacement instruction.
- `nist-csf-04` newly refuses despite rank-one `p23-c4` supplying all four
  ID.AM-05 prioritization factors.

The two recovered answers are offset by two new false refusals, leaving the
aggregate false-refusal count unchanged. The extra citation failure reduces
supported accuracy by one. All nine remaining native false refusals now have
complete retrieved evidence; better retrieval alone did not solve generation.
Changed context/order is a plausible contributor to the regressions, not a
proven single cause from one run.

The pre-existing strict completeness penalties remain: `osha-08` omits the
public-domain/copyright-free detail; `nist-csf-06` omits outcomes an organization
is attempting to achieve. No annotations were relaxed to favor either system.
A looser page-level citation interpretation could accept `osha-04`, but that is
not the frozen rule and would need a separately versioned future evaluation.

## Latency and implementation limits

Native retrieval median/p95 is **0.032/0.079 seconds** for dense and
**0.032/0.039 seconds** for hybrid. Generation median/p95 is **1.043/2.644 seconds**
and **0.933/2.499 seconds**, respectively. OCR candidate retrieval median/p95 is
**0.024/0.031 seconds**; generation is **1.147/1.701 seconds**. Indexing is excluded
and recorded separately in each `run.json`. Indexes were reused. These are single
sequential local runs with different answers and warm-up effects; they do not
establish a hybrid speed advantage. No hard latency gate was specified.

Lexical statistics were recomputed per query using existing chunks and the
standard library. A read-only code audit also identified a tie caveat: with no
lexical matches, fusion preserves the top-20 dense search's order, but FAISS can
order identical-score vectors differently when asked for 20 instead of four.
An isolated identical-vector check returned `[3,2,1,0]` for top four and
`[19,18,17,16]` when truncating top 20. Thus the pre-run fallback wording must not
be read as byte-identical old top-four results under ties. This does not explain
the observed benchmark regressions; the frozen candidate was not retuned.

## Reproduce and audit

Final verification passes **116 tests**, including three real local model/OCR
integration tests. Ruff lint and formatting checks pass. Both published Phase 2B
and Phase 2C comparisons reproduce exactly, including their artifact hashes and
gate decisions. The restored pipeline and UI match the fresh dense control
byte-for-byte; a new regression test protects dense top-k and cosine scores.

The rejected implementation and its five focused tests remain in Git at
`4bb8437`; they are removed from the active application instead of exposing an
unapproved runtime option. Create a detached worktree at that revision beneath
the workspace's `worktrees/` directory to reproduce hybrid inference. Use the
locked environment and [development-run instructions](PHASE2A.md) with a fresh
output directory. Current `main` intentionally runs dense retrieval.

From current code, reproduce the published retrieval comparison:

```sh
uv run python -m pdf_qa.comparison --mode retrieval \
  --baseline evals/phase2c/results/control-01 \
  --candidate evals/phase2c/results/candidate-01 \
  --output /tmp/pdf-qa-phase2c-comparison.json
```

Use a new output path. CLI success means a valid comparison was generated, not
that its candidate passed: inspect `acceptance.passed` and each gate. Legacy
approval remains separate. Default `--mode generation` retains the stricter
requirement for identical ranked passages and evidence grades; the published
Phase 2B comparison is unchanged when recomputed.

- [Fresh dense control and provenance](../evals/phase2c/results/control-01/)
- [Hybrid outputs, review packet, and fact-level grades](../evals/phase2c/results/candidate-01/)
- [Per-document metrics and latency](../evals/phase2c/results/candidate-01/summary.json)
- [Legacy regression and review attribution](../evals/phase2c/results/legacy-candidate-01/)

Phase 2C ends here. A subsequent reviewed phase can investigate conservative
generation and citation completeness with fixed evidence. No further candidate
or held-out evaluation is authorized by this report.
