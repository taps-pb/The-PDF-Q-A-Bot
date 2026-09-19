# Final legacy verification

Codex root performed AI-assisted manual review of all ten outputs against frozen
expected facts and actual cited passages. All seven answerable questions are
complete and citation-supported; all three unanswerable questions return NOT FOUND.
There are no operational errors. Each case preserves one raw generation response,
and replay through the original parser exactly matches its saved answer.

This is the retained `grounded-v1`/dense retrieval pipeline at release revision
`35c75a36fac66c1cda98bc31562601091fcf36fd`. No inference code changed between the
expanded held-out run and this legacy run. The legacy runner records models,
digests, settings, prompt version, source/index identity, and raw responses, but
not the Git revision. This note supplies execution attribution rather than
pretending that metadata was automatically captured. Full frozen implementation
provenance is available in the adjacent held-out run.

This is a fixed-800 regression, not a new three-size selection experiment or an
unseen benchmark. Review is AI-assisted, not independent human adjudication.
