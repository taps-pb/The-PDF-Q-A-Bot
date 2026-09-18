# Legacy candidate review

Codex root performed AI-assisted manual review of all ten recorded responses
against the frozen expected facts and actual cited chunks. This is not independent
human adjudication. All seven answerable cases are correct and citation-supported;
all three unanswerable cases return NOT FOUND. There are no operational errors.

This run used the frozen Phase 2C hybrid pipeline at `4bb8437`, before restoring
dense retrieval. The legacy runner records models/digests, index manifest,
questions, settings, and prompt version but not a Git revision or retrieval
configuration. This note supplies execution attribution; it does not claim those
fields were automatically captured. The adjacent
[expanded candidate run](../candidate-01/run.json) records full experiment
provenance. No source, prompt, or retrieval code changed between these runs.

The historical 7/7 supported-answer and 3/3 correct-refusal regression is retained.
A fresh legacy dense control was not run. Passing this small legacy suite does
not override the failed expanded development gates. The selected size of 800 is
a fixed regression setting, not a new three-size selection experiment.
