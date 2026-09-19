# Phase 3 candidate: failed promotion gates, external review pending

**Closeout update:** Independent review is complete and confirms rejection. The
following report preserves the pre-review status at the time it was written.
See [review disposition](PHASE3-REVIEW.md) and [final verification](RELEASE.md).
Only experiment records/history are retained; the rejected generation code is
not part of the final application.

The quote-bearing candidate is **not suitable for promotion**. It passes its
structural tests but decreases supported accuracy, adds operational failures,
and still generates two false claims accompanied by genuine quotes. It remains
isolated on `feat/phase3`; production `main` is unchanged at `c1168a6`. Nothing
from Phase 3 has been merged or pushed. The user's independent tester report is
still pending and will be reviewed before deciding what, if anything, to retain.

## Implementation and controls

The [pre-run plan](PHASE3.md) limits this phase to quote-bearing generation and
its validation/evaluation. The new `parse_grounded_answer` validates strict JSON,
claim/evidence presence, bounded response sizes, retrieved chunk membership,
and exact quote substrings after whitespace collapsing. It derives citations
from evidence. Case, punctuation, and numbers are not normalized away. A matching
quote is deliberately **not** treated as proof that the claim follows from it.

The existing local Qwen3 model emits the new structured response. Invalid output
gets at most one repair; two invalid responses raise an operational error, not
NOT FOUND. Valid refusals are never retried. Raw responses from both attempts
are saved in benchmark results, with schema and parser-hash provenance in the
expanded runner. Existing UI, Answer records, retrieval, indexes, extraction,
models, dependencies, and generation parameters remain unchanged.

The control ran from clean commit `8da5449a0484e8c78ccd418e188dbff6d01606d6`;
the candidate ran from clean commit `dce4fd4e09ca3bbdc20662b96d735d6ff496ff07`.
The first control launch failed before creating a run because Ollama was stopped.
Restarting the existing local service with cloud disabled resolved that setup
issue; no benchmark answers had been produced or discarded.

All 42 control cases, ordered chunks, and answer/citation objects match the
reviewed Phase 2C control exactly. Its prior judgments are explicitly reused.
All 42 candidate cases and ordered chunks match the fresh control; only one
case has small cosine-score drift (maximum 0.000043392181396484375). Generation
never receives scores. Candidate answer grades use Codex root's manual semantic
review of actual cited chunks and frozen facts; evidence-presence judgments and
unchanged refusals reuse the matching control. This is AI-assisted review, not
independent human adjudication. No held-out questions were run.

## Results

| Native development metric | Control | Candidate |
|---|---:|---:|
| Complete evidence@4 | 21/24 | 21/24 |
| Strict supported accuracy | 12/24 | 8/24 |
| False refusals | 9/24 | 1/24 |
| Correct refusals on unanswerable cases | 12/12 | 12/12 |
| Unsupported / successful non-refused answers | 1/15 | 2/14 |
| Operational errors | 0 | 9 |

Per-document supported accuracy: OSHA 7/8 to 2/8; NIST AI RMF 2/8 to 1/8;
NIST CSF 3/8 to 5/8. Paired OCR evidence and accuracy remain 6/6, with zero
errors or unsupported answers. OCR variants are not independent questions.

The separate ten-question legacy candidate run falls to 3/7 supported answers,
with 3/3 correct refusals and two operational errors. Its reference is the
historical 7/7 legacy result, not a newly run legacy control. It does not select
a new chunk size: 800 characters was fixed throughout.

The [paired comparison](../evals/phase3/results/comparison-01.json) fails accuracy,
unsupported-answer, and zero-error gates. The additional predeclared
per-document and legacy gates also fail. The existing generation comparator's
false-refusal gate requires a strict decrease, which is stronger than this
phase's nonincrease requirement; both pass here, so this does not affect rejection.
Fewer refusals are not an improvement when they become errors, incomplete
answers, or false claims.

## Failures and tradeoffs

- All nine development repairs failed. Replaying the saved 51 raw responses
  produces 33 valid responses and 18 exact-quote validation failures. No extra
  generation retries or candidate tuning were performed.
- Several quotes silently clean up source text. For example, `osha-02` changes
  source `minimum .` to `minimum.`. Whitespace collapsing preserves one space;
  it does not delete the space before punctuation. `osha-05` additionally changes
  curly quotation marks to straight quotation marks. These are contract failures,
  not evidence that the proposed answer's safety facts are false.
- `nist-ai-03` invents a risk definition using methods, metrics, and controls.
  Its quotes genuinely occur in `p34-c1`, but describe the MEASURE function rather
  than probability and consequences. `nist-csf-03` invents three Tiers while
  quoting genuine text from `p29-c1`, which supplies only Tier 1's Partial name.
  Quote membership therefore fails as a semantic safeguard in real cases, not
  only the synthetic counterexample.
- Partial answers also pass the validator: `nist-ai-04` omits accuracy;
  `nist-ai-06` omits the absence-of-intent answer; `nist-csf-05` omits the
  restoration-integrity check. `nist-csf-06` includes attempted outcomes now,
  but still omits how or to what extent outcomes are achieved. Frozen facts
  were not relaxed to count these responses as complete.
- All regressions from previously supported answers are explicit: `osha-02`,
  `osha-03`, `osha-04`, `osha-05`, `osha-07`, and `nist-ai-02` become operational
  errors; `nist-csf-05` becomes incomplete. Improvements are `nist-csf-02`,
  `nist-csf-07`, and `nist-csf-08`, which now answer correctly. Other incorrect
  cases change failure type without becoming correct.
- Legacy `q1` and `q3` fail quote validation. Legacy `q4` omits annual maintenance;
  `q7` omits high-hazard priority after a successful repair. Only `q2`, `q5`,
  and `q6` remain fully correct and supported. Three legacy cases require a
  repair; only `q7` produces a structurally valid response afterward.

No normalization changes or further prompt edits were made after these results.
Weakening quote checks would not fix the genuine-quote/false-claim counterexamples.

## Verification, latency, and handoff

All **147 tests pass**, including three real local model/OCR integration tests.
Ruff lint and changed-file formatting checks pass. Tests cover adversarial
types/fields, duplicate keys, quote borrowing across chunks, changed numbers,
resource limits, bounded repair, raw-attempt preservation, and the known lack
of semantic entailment checking. No new dependencies were needed.

Native total-query median/p95, including failed attempts, rises from
**1.076/3.200 seconds** to **2.515/9.584 seconds**. This uses `total_seconds`
from all 36 native records; it includes per-query orchestration and cached
ingestion overhead, not a clean model-only timing. The existing summary's
generation latency excludes nine failures with missing generation timings, so
its 27-success population must not be compared as though it covered all queries.
OCR generation median/p95 is **2.535/2.910 seconds**, versus **1.538/1.769 seconds**
for control. These are single local sequential runs, not stable speed estimates.

The implementation is available to the external tester at `dce4fd4` in
`worktrees/phase3`. Subsequent branch commits preserve results and documentation,
not retuned inference code. Test using the shared environment with `PYTHONPATH=src`:

```sh
PYTHONPATH=src ../../code/.venv/bin/python -m pytest -q
```

Run that command from the worktree. For the three local integration tests,
override the default marker with
`-m 'integration or not integration'`. Do not run live inference concurrently
with another benchmark, modify the implementation worktree from a reviewer
session, inspect held-out questions, or promote this candidate based on unit
test success. The copy-paste testing prompt was supplied in chat before coding.

- [Control provenance and reused grades](../evals/phase3/results/control-01/)
- [Candidate raw attempts, grades, and review packet](../evals/phase3/results/candidate-01/)
- [Comparison and gate decisions](../evals/phase3/results/comparison-01.json)
- [Legacy outputs and manual grades](../evals/phase3/results/legacy-candidate-01/)

Next action is to review the user's tester output, not to merge, push, run held-out
evaluation, or silently try another candidate. The original production app remains
available and unchanged in `code/`.
