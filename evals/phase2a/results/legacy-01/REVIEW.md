# Legacy regression review

The original ten questions were rerun at the unchanged 800-character setting
after the Phase 2A development baseline. This is not another chunk-size tuning
experiment. The root Codex agent manually reviewed all ten actual answers,
retrieved passages, and cited chunk IDs; notes are in `grades.json`.
Review attribution: AI-assisted manual semantic review, not human adjudication.

The legacy runner preserves its existing metadata format. It does not capture
the expanded code/dirty-state/runtime provenance added by `pdf_qa.suite`.
This run used revision `7c9917a` (only suite tests changed from baseline revision
`b57230b`) and the same unchanged production pipeline and local models as
`../baseline-01/`. Documentation and benchmark results were uncommitted during
the regression. Use the baseline's `run.json` for the fully captured experiment;
do not treat this note as a retroactive clean-tree provenance capture.

Result: seven supported correct answers and three correct refusals, with no
operational errors. No old grades were copied without reviewing the new outputs.
