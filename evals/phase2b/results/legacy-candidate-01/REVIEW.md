# Candidate legacy regression review

The ten original questions were rerun with `grounded-v2` at 800 characters.
All seven answerable responses and three refusals were manually reviewed by the
root Codex agent against their actual cited passages. This is AI-assisted manual
semantic review, not independent human adjudication. Grades were not assigned
automatically or copied without checking the new outputs.

This candidate regression passes 7/7 supported accuracy and 3/3 correct refusals,
but the expanded development suite fails the unsupported-answer gate. The prompt
was rejected; a legacy pass does not override that decision.

The unchanged legacy runner does not capture the full code/dirty/runtime
provenance added to the expanded suite. It ran with the production module from
candidate revision `84ffc54`, before restoration to `grounded-v1`. The report
heading in suite.py and candidate result files were uncommitted at that time.
See `../candidate-01/run.json` for the complete clean-tree candidate provenance;
this note is not a retroactive clean-tree capture of the legacy run.
