# Legacy candidate review

Codex root manually compared all ten outputs with the frozen expected facts and
actual cited passages. This is AI-assisted review, not independent human grading.
The result is 3/7 supported answers, 3/3 correct refusals, and two operational
errors. Questions q1 and q3 fail quote validation; q4 and q7 omit required facts.
Only q2, q5, and q6 are complete supported answers.

The candidate uses `quoted-claims-v1` from `dce4fd4` with unchanged dense retrieval
and generation parameters. The legacy runner records models, settings, prompt
version, source/index identities, and raw generation responses, but not the
candidate Git revision or parser hash. This note provides execution attribution;
the adjacent expanded candidate run records those additional provenance fields.
No inference code changed between the expanded and legacy candidate runs.

There were three repair attempts: q1 and q3 remained invalid; q7 became valid but
incomplete. The historical 7/7 result is the regression reference; a fresh legacy
control was not run. This run is a fixed-800 regression, not a new chunk-size
selection experiment. The candidate is not approved for production.
