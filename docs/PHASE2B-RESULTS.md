# Phase 2B: candidate rejected, production prompt retained

The evidence-first prompt improved answer completion but failed the predeclared
unsupported-answer gate. **It is not enabled in the app.** Production remains
`grounded-v1`, byte-for-byte identical to the Phase 2A pipeline. This phase ships
the paired-comparison tool, its regression tests, and the complete experiment
record. No retrieval changes or new dependencies were introduced.

## Controlled experiment

One candidate, `grounded-v2`, was frozen at clean revision
`84ffc54d3cfe86ab22b6f5e04e920ee094f6ae18` before local inference. Its prompt asked
the model to inspect all passages before refusing, combine evidence, retain
qualifiers, and cite every substantive claim. See the [pre-run scope and gates](PHASE2B.md).
No second candidate was tuned after seeing results.

The 36 native development cases and six paired OCR cases used the same frozen
questions, source PDFs, model digests, generation options, chunking, embeddings,
runtime versions, and ranked passage objects as Phase 2A. All 24 held-out
questions remain unrun. The comparison revalidates raw-artifact hashes, complete
manual grades, saved metrics, selected cases, and recorded controls.

Seven cases have small retrieval-score differences (maximum absolute difference
0.00010323524475097656), but passage text, IDs, pages, extraction methods, and
rank order are identical across all 42 cases. Generation never receives scores.
The comparison records this drift rather than treating it as a changed model
input; changed passages or ranking still cause a hard validation failure.

Grades use the same frozen required facts and AI-assisted manual semantic review
as Phase 2A. The root agent reviewed OSHA and the legacy suite; separate agents
reviewed each NIST document; the root adjudicated borderline cases. This is not
independent human adjudication or a statistically representative benchmark.

## Results

| Native development metric | Phase 2A | Candidate |
|---|---:|---:|
| Complete evidence@4 | 21/24 | 21/24 |
| Strict supported answer accuracy | 12/24 | 19/24 |
| False refusals | 9/24 | 1/24 |
| Correct refusals on unanswerable questions | 12/12 | 12/12 |
| Unsupported answers / successful non-refused answers | 1/15 | 3/23 |
| Operational errors | 0 | 0 |

Per-document supported accuracy changes: OSHA 7/8 to 8/8, NIST AI RMF 2/8 to
4/8, and NIST CSF 3/8 to 7/8. The six OCR variants remain 6/6 supported correct.
The separate ten-question candidate regression retains 7/7 supported answers and
3/3 correct refusals. These are separate denominators, not one pooled score.

The generated [comparison](../evals/phase2b/results/comparison-01.json) records
`acceptance.passed: false`. Every development gate passes except the requirement
that the native unsupported-answer count not increase. Passing easy refusal
questions and the original ten-question suite does not offset that failure.

## Why the candidate was rejected

- `nist-ai-03`: the correct definition is absent from retrieval. Instead of the
  baseline refusal, the candidate incorrectly defines risk using “risks and
  trustworthiness characteristics,” citing a passage about measurement practices.
- `nist-csf-03`: retrieval contains only partial tier evidence. The candidate
  invents a three-tier structure and the names “Formal Application” and
  “Comprehensive Application.” The cited passage does not support those claims.
- `nist-ai-04`: despite retrieving the right definitions, the candidate adds an
  unsupported strengthening: examples of metrics that the source says should be
  considered become required measures. Its accuracy definition also omits the
  alternative of values accepted as true under the frozen completeness rubric.

The old citation-coverage failure, `nist-ai-07`, is repaired by removing its
unsupported extra relationship. Nevertheless, three new unsupported answers
replace one old failure. The observed tradeoff is more willingness to answer,
not an unqualified quality improvement. No claim is made that any single phrase
in the revised prompt caused a particular response.

`nist-ai-06` is a separate borderline annotation-completeness failure: the answer
correctly lists the bias categories and says they can occur without discriminatory
intent, but omits prejudice and partiality from the frozen required fact. A looser
question-level rubric could count that answer and yield 20/24; it would not remove
the unsupported-answer regression. OSHA's copyright-free explanation and CSF's
attempted-outcome qualifier now satisfy their previously incomplete facts.
Future rubric revisions should distinguish essential answers from explanatory
details before new inference, without rewriting either published run.

## Latency and limits

Native generation median/p95 rises from **1.005/2.518 seconds** to
**1.973/3.280 seconds**; retrieval is **0.029/0.046 seconds** for the candidate.
Candidate OCR generation median/p95 is **1.816/2.160 seconds** across six cases.
Indexing is excluded. These are single sequential local runs; fewer short
refusals and longer answers affect latency, so this is not an isolated estimate
of prompt overhead. Temperature zero and a fixed seed do not guarantee identical
outputs across all runtime conditions. No hard latency gate was used.

Prompt-only changes did not recover missing evidence. The still-missing evidence
led to two fabricated answers and one continued refusal. A next reviewed phase
can investigate retrieval coverage while retaining the conservative prompt.
Evidence verification is another candidate intervention, but no additional model
or architecture is justified solely by this one experiment. Phase 2C has not
started; held-out evaluation remains deferred.

## Reproduce and audit

Final verification: 93 tests pass, including three real local model/OCR tests;
Ruff checks pass. One initial verification attempt lost the Ollama connection
because the local service was stopped. Restarting it with cloud disabled allowed
the full suite to pass; no application change was needed for that failure.

The rejected prompt is available in Git at `84ffc54`, not as a runtime option.
Create a worktree under the workspace's `worktrees/` folder at that revision,
install the locked environment, and follow the existing suite's development-run
instructions with a fresh output directory. Do not rerun it from current `main`
and label the result `grounded-v2`: current `main` intentionally uses `grounded-v1`.

From current repository code, reproduce the comparison of published runs:

```sh
uv run python -m pdf_qa.comparison \
  --baseline evals/phase2a/results/baseline-01 \
  --candidate evals/phase2b/results/candidate-01 \
  --output /tmp/pdf-qa-phase2b-comparison.json
```

Use a new output path; the tool never overwrites an existing report. A successful
CLI exit means the comparison was generated, **not** that the candidate passed.
Inspect `acceptance.passed` and the individual gates. Legacy regression approval
is explicitly separate; the tool does not claim to verify it automatically.

- [Candidate provenance, actual outputs, and review packet](../evals/phase2b/results/candidate-01/)
- [Fact-level candidate grades](../evals/phase2b/results/candidate-01/grades.json)
- [Candidate per-document metrics and latency](../evals/phase2b/results/candidate-01/summary.json)
- [Case-by-case comparison and acceptance decision](../evals/phase2b/results/comparison-01.json)
- [Separate candidate legacy regression](../evals/phase2b/results/legacy-candidate-01/)

Only repository code, public-source evaluation artifacts, and documentation are
committed. PDFs, model weights, local indexes, skills, and worktrees remain outside
the `code/` repository.
