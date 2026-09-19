# Evidence evaluation report

Reviewer: Codex root AI-assisted manual review of candidate answers against frozen facts and actual cited chunks. Evidence judgments reused only after exact ordered-context equality with the control; unchanged refusals reuse prior judgments. Not independent human adjudication; external model review pending.

Split: development. OCR pairs are not independent questions.

| Group | Metric | Count | Denominator | Rate |
|---|---|---:|---:|---:|
| native-overall | hit_at_4 | 21 | 24 | 0.875 |
| native-overall | evidence_coverage_at_4 | 21 | 24 | 0.875 |
| native-overall | answer_accuracy | 8 | 24 | 0.333 |
| native-overall | false_refusal_rate | 1 | 24 | 0.042 |
| native-overall | correct_refusal_rate | 12 | 12 | 1.000 |
| native-overall | unsupported_answer_rate | 2 | 14 | 0.143 |
| native-nist-ai | hit_at_4 | 6 | 8 | 0.750 |
| native-nist-ai | evidence_coverage_at_4 | 6 | 8 | 0.750 |
| native-nist-ai | answer_accuracy | 1 | 8 | 0.125 |
| native-nist-ai | false_refusal_rate | 1 | 8 | 0.125 |
| native-nist-ai | correct_refusal_rate | 4 | 4 | 1.000 |
| native-nist-ai | unsupported_answer_rate | 1 | 4 | 0.250 |
| native-nist-csf | hit_at_4 | 7 | 8 | 0.875 |
| native-nist-csf | evidence_coverage_at_4 | 7 | 8 | 0.875 |
| native-nist-csf | answer_accuracy | 5 | 8 | 0.625 |
| native-nist-csf | false_refusal_rate | 0 | 8 | 0.000 |
| native-nist-csf | correct_refusal_rate | 4 | 4 | 1.000 |
| native-nist-csf | unsupported_answer_rate | 1 | 8 | 0.125 |
| native-osha | hit_at_4 | 8 | 8 | 1.000 |
| native-osha | evidence_coverage_at_4 | 8 | 8 | 1.000 |
| native-osha | answer_accuracy | 2 | 8 | 0.250 |
| native-osha | false_refusal_rate | 0 | 8 | 0.000 |
| native-osha | correct_refusal_rate | 4 | 4 | 1.000 |
| native-osha | unsupported_answer_rate | 0 | 2 | 0.000 |
| ocr-overall | hit_at_4 | 6 | 6 | 1.000 |
| ocr-overall | evidence_coverage_at_4 | 6 | 6 | 1.000 |
| ocr-overall | answer_accuracy | 6 | 6 | 1.000 |
| ocr-overall | false_refusal_rate | 0 | 6 | 0.000 |
| ocr-overall | correct_refusal_rate | 0 | 0 | N/A |
| ocr-overall | unsupported_answer_rate | 0 | 6 | 0.000 |
| ocr-scan | hit_at_4 | 3 | 3 | 1.000 |
| ocr-scan | evidence_coverage_at_4 | 3 | 3 | 1.000 |
| ocr-scan | answer_accuracy | 3 | 3 | 1.000 |
| ocr-scan | false_refusal_rate | 0 | 3 | 0.000 |
| ocr-scan | correct_refusal_rate | 0 | 0 | N/A |
| ocr-scan | unsupported_answer_rate | 0 | 3 | 0.000 |
| ocr-mixed | hit_at_4 | 3 | 3 | 1.000 |
| ocr-mixed | evidence_coverage_at_4 | 3 | 3 | 1.000 |
| ocr-mixed | answer_accuracy | 3 | 3 | 1.000 |
| ocr-mixed | false_refusal_rate | 0 | 3 | 0.000 |
| ocr-mixed | correct_refusal_rate | 0 | 0 | N/A |
| ocr-mixed | unsupported_answer_rate | 0 | 3 | 0.000 |

## Failures

- osha-02: operational_error. AI-assisted review: both generation attempts fail exact quote membership validation; no answer is emitted after the single permitted repair. This is an operational error, not a NOT FOUND refusal or a supported answer. Evidence-presence judgments are retained only after all ordered chunk objects exactly match the reviewed control. Raw attempts are preserved in results.json.
- osha-03: operational_error. AI-assisted review: both generation attempts fail exact quote membership validation; no answer is emitted after the single permitted repair. This is an operational error, not a NOT FOUND refusal or a supported answer. Evidence-presence judgments are retained only after all ordered chunk objects exactly match the reviewed control. Raw attempts are preserved in results.json.
- osha-04: operational_error. AI-assisted review: both generation attempts fail exact quote membership validation; no answer is emitted after the single permitted repair. This is an operational error, not a NOT FOUND refusal or a supported answer. Evidence-presence judgments are retained only after all ordered chunk objects exactly match the reviewed control. Raw attempts are preserved in results.json.
- osha-05: operational_error. AI-assisted review: both generation attempts fail exact quote membership validation; no answer is emitted after the single permitted repair. This is an operational error, not a NOT FOUND refusal or a supported answer. Evidence-presence judgments are retained only after all ordered chunk objects exactly match the reviewed control. Raw attempts are preserved in results.json.
- osha-07: operational_error. AI-assisted review: both generation attempts fail exact quote membership validation; no answer is emitted after the single permitted repair. This is an operational error, not a NOT FOUND refusal or a supported answer. Evidence-presence judgments are retained only after all ordered chunk objects exactly match the reviewed control. Raw attempts are preserved in results.json.
- osha-08: operational_error. AI-assisted review: both generation attempts fail exact quote membership validation; no answer is emitted after the single permitted repair. This is an operational error, not a NOT FOUND refusal or a supported answer. Evidence-presence judgments are retained only after all ordered chunk objects exactly match the reviewed control. Raw attempts are preserved in results.json.
- nist-ai-01: incomplete_retrieval. Prior judgment reused after exact matching refusal and ordered retrieved chunks against the reviewed control. AI-assisted manual semantic review: the native extraction of physical page 3 contains the 2028 deadline, but the four hits are p1-c1, p8-c3, p8-c2, and p47-c1. These discuss the title, framework development, and general updates without the review deadline. NOT FOUND is therefore a false refusal caused by missing retrieved evidence, not demonstrated extraction loss.
- nist-ai-02: operational_error. AI-assisted review: both generation attempts fail exact quote membership validation; no answer is emitted after the single permitted repair. This is an operational error, not a NOT FOUND refusal or a supported answer. Evidence-presence judgments are retained only after all ordered chunk objects exactly match the reviewed control. Raw attempts are preserved in results.json.
- nist-ai-03: unsupported_answer. AI-assisted manual review by Codex root: The answer incorrectly substitutes appropriate methods/metrics and effectiveness of controls for probability and consequences. Its quotes are genuine substrings of cited p34-c1, but that MEASURE-function passage does not define the two components of risk. Neither expected fact is retrieved. This directly demonstrates that quote membership does not establish semantic support.
- nist-ai-04: generation_failure. AI-assisted manual review by Codex root: The answer correctly gives reliability, including no failure, the time interval, and given conditions, supported by cited p18-c4. It entirely omits accuracy and its reference despite that evidence being retrieved. Only reliability is cited. This is an incomplete answer, not an invented claim.
- nist-ai-05: operational_error. AI-assisted review: both generation attempts fail exact quote membership validation; no answer is emitted after the single permitted repair. This is an operational error, not a NOT FOUND refusal or a supported answer. Evidence-presence judgments are retained only after all ordered chunk objects exactly match the reviewed control. Raw attempts are preserved in results.json.
- nist-ai-06: generation_failure. AI-assisted manual review by Codex root: The answer correctly lists systemic, computational/statistical, and human-cognitive bias. It entirely omits whether these can arise without prejudice, partiality, or discriminatory intent. Cited p23-c1 contains the complete fourth fact, but the displayed claim does not. Quote validation does not enforce question completeness.
- nist-ai-07: operational_error. AI-assisted review: both generation attempts fail exact quote membership validation; no answer is emitted after the single permitted repair. This is an operational error, not a NOT FOUND refusal or a supported answer. Evidence-presence judgments are retained only after all ordered chunk objects exactly match the reviewed control. Raw attempts are preserved in results.json.
- nist-csf-03: unsupported_answer. AI-assisted manual review by Codex root: The answer invents three Tiers and substitutes numbered labels for the requested names. Cited p29-c1 actually identifies Tier 1 as Partial and contains no support for the three-tier count. The four copied quotes all occur in that chunk, but do not support the generated claim. Only the expected Tier 1 name is present in retrieval/cited source; the answer fails all expected facts.
- nist-csf-05: generation_failure. AI-assisted manual review by Codex root: The answer correctly gives PR.DS-11's creation, protection, maintenance, and testing list, supported by cited p25-c2. It omits the RC.RP-03 integrity check before restoration despite that evidence being retrieved. The required second fact is neither answered nor cited.
- nist-csf-06: generation_failure. AI-assisted manual review by Codex root: Cited p11-c2 contains both full definitions. The answer now includes achieved or attempted outcomes, but omits how or to what extent outcomes are achieved, still required by frozen f1. The Target Profile definition is complete. All expressed claims are supported; this is an omission, not fabrication.

Latency and operational error counts are in summary.json; indexing is in run.json and excluded from query latency. Only the explicitly selected split is included in this report.
