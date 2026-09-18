# Evidence evaluation report

Reviewer: Codex root (OSHA), phase2a_ai (NIST AI), phase2a_csf (NIST CSF); AI-assisted manual semantic review, root adjudication; not independent human review

Split: development. OCR pairs are not independent questions.

| Group | Metric | Count | Denominator | Rate |
|---|---|---:|---:|---:|
| native-overall | hit_at_4 | 21 | 24 | 0.875 |
| native-overall | evidence_coverage_at_4 | 21 | 24 | 0.875 |
| native-overall | answer_accuracy | 19 | 24 | 0.792 |
| native-overall | false_refusal_rate | 1 | 24 | 0.042 |
| native-overall | correct_refusal_rate | 12 | 12 | 1.000 |
| native-overall | unsupported_answer_rate | 3 | 23 | 0.130 |
| native-nist-ai | hit_at_4 | 6 | 8 | 0.750 |
| native-nist-ai | evidence_coverage_at_4 | 6 | 8 | 0.750 |
| native-nist-ai | answer_accuracy | 4 | 8 | 0.500 |
| native-nist-ai | false_refusal_rate | 1 | 8 | 0.125 |
| native-nist-ai | correct_refusal_rate | 4 | 4 | 1.000 |
| native-nist-ai | unsupported_answer_rate | 2 | 7 | 0.286 |
| native-nist-csf | hit_at_4 | 7 | 8 | 0.875 |
| native-nist-csf | evidence_coverage_at_4 | 7 | 8 | 0.875 |
| native-nist-csf | answer_accuracy | 7 | 8 | 0.875 |
| native-nist-csf | false_refusal_rate | 0 | 8 | 0.000 |
| native-nist-csf | correct_refusal_rate | 4 | 4 | 1.000 |
| native-nist-csf | unsupported_answer_rate | 1 | 8 | 0.125 |
| native-osha | hit_at_4 | 8 | 8 | 1.000 |
| native-osha | evidence_coverage_at_4 | 8 | 8 | 1.000 |
| native-osha | answer_accuracy | 8 | 8 | 1.000 |
| native-osha | false_refusal_rate | 0 | 8 | 0.000 |
| native-osha | correct_refusal_rate | 4 | 4 | 1.000 |
| native-osha | unsupported_answer_rate | 0 | 8 | 0.000 |
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

- nist-ai-01: incomplete_retrieval. AI-assisted manual semantic review: candidate returns NOT FOUND. Unchanged hits p1-c1, p8-c3, p8-c2, and p47-c1 contain no 2028 review deadline. The extracted source page 3 still contains that deadline, so this remains a false refusal with incomplete retrieval, not extraction loss.
- nist-ai-03: unsupported_answer. AI-assisted manual semantic review: the candidate claims the composite risk components are 'the risks and trustworthiness characteristics' and cites p34-c1. That passage discusses measurement selection and documentation; it does not define risk as those components. Neither probability nor consequence magnitude is retrieved or answered. Source page 9 contains the actual definition but is absent from the unchanged four hits. This regresses the baseline's refusal into an unsupported definition.
- nist-ai-04: unsupported_answer. AI-assisted manual semantic review, with root adjudication: cited p18-c4 fully supports the reliability answer, including no failure, a time interval, and conditions. Cited p19-c1 contains the complete accuracy definition, but the answer says only 'closeness of results to true values', omitting the frozen fact's alternative of values accepted as true; f2 answer_correct is false under the unchanged strict rubric while citation_supported remains true. Independently, the answer claims accuracy 'requires measures such as false positive and false negative rates, human-AI teaming, and external validity'; p19-c1 says measures should consider such metrics, not that the examples are required. That stronger normative claim is materially unsupported.
- nist-ai-06: generation_failure. AI-assisted manual semantic review, with root adjudication: cited p23-c1 supports the three bias categories and the absence of prejudice, partiality, or discriminatory intent. The candidate lists all categories accurately but states only that they can occur 'without discriminatory intent', omitting prejudice and partiality from frozen f4. This is a borderline completeness failure under the unchanged all-required-facts rubric, even though the answer addresses the question's wording. The omitted information is present in the citation, so citation_supported remains true; no unsupported extra claim is added.
- nist-csf-03: unsupported_answer. AI-assisted manual review: p29-c1 supports only Tier 1 = Partial; other hits are contents or appendix references. The candidate invents a three-tier count, Tier 2 'Formal Application', and Tier 3 'Comprehensive Application', and omits Tier 4. These claims are absent from its sole citation p29-c1 and contradict the intact source list on extracted pages 12 and 31. The identifiable Tier 1/Partial mapping receives f2 credit despite awkwardly joining the table label with adjacent prose; that does not validate the fabricated remaining tiers. Evidence grades match baseline. This is an unsupported-answer regression from the baseline refusal.

Latency and operational error counts are in summary.json; indexing is in run.json and excluded from query latency. Only the explicitly selected split is included in this report.
