# Evidence evaluation report

Reviewer: Codex root AI-assisted manual review after the single frozen held-out run, using required facts, all retrieved chunks, actual citations, and extracted source pages for retrieval-loss checks. No tuning or annotation changes. Not independent human adjudication.

Split: heldout. OCR pairs are not independent questions.

| Group | Metric | Count | Denominator | Rate |
|---|---|---:|---:|---:|
| native-overall | hit_at_4 | 17 | 18 | 0.944 |
| native-overall | evidence_coverage_at_4 | 14 | 18 | 0.778 |
| native-overall | answer_accuracy | 11 | 18 | 0.611 |
| native-overall | false_refusal_rate | 5 | 18 | 0.278 |
| native-overall | correct_refusal_rate | 6 | 6 | 1.000 |
| native-overall | unsupported_answer_rate | 2 | 13 | 0.154 |
| native-nist-ai | hit_at_4 | 6 | 6 | 1.000 |
| native-nist-ai | evidence_coverage_at_4 | 5 | 6 | 0.833 |
| native-nist-ai | answer_accuracy | 3 | 6 | 0.500 |
| native-nist-ai | false_refusal_rate | 1 | 6 | 0.167 |
| native-nist-ai | correct_refusal_rate | 2 | 2 | 1.000 |
| native-nist-ai | unsupported_answer_rate | 2 | 5 | 0.400 |
| native-nist-csf | hit_at_4 | 5 | 6 | 0.833 |
| native-nist-csf | evidence_coverage_at_4 | 3 | 6 | 0.500 |
| native-nist-csf | answer_accuracy | 3 | 6 | 0.500 |
| native-nist-csf | false_refusal_rate | 3 | 6 | 0.500 |
| native-nist-csf | correct_refusal_rate | 2 | 2 | 1.000 |
| native-nist-csf | unsupported_answer_rate | 0 | 3 | 0.000 |
| native-osha | hit_at_4 | 6 | 6 | 1.000 |
| native-osha | evidence_coverage_at_4 | 6 | 6 | 1.000 |
| native-osha | answer_accuracy | 5 | 6 | 0.833 |
| native-osha | false_refusal_rate | 1 | 6 | 0.167 |
| native-osha | correct_refusal_rate | 2 | 2 | 1.000 |
| native-osha | unsupported_answer_rate | 0 | 5 | 0.000 |
| ocr-overall | hit_at_4 | 0 | 0 | N/A |
| ocr-overall | evidence_coverage_at_4 | 0 | 0 | N/A |
| ocr-overall | answer_accuracy | 0 | 0 | N/A |
| ocr-overall | false_refusal_rate | 0 | 0 | N/A |
| ocr-overall | correct_refusal_rate | 0 | 0 | N/A |
| ocr-overall | unsupported_answer_rate | 0 | 0 | N/A |
| ocr-scan | hit_at_4 | 0 | 0 | N/A |
| ocr-scan | evidence_coverage_at_4 | 0 | 0 | N/A |
| ocr-scan | answer_accuracy | 0 | 0 | N/A |
| ocr-scan | false_refusal_rate | 0 | 0 | N/A |
| ocr-scan | correct_refusal_rate | 0 | 0 | N/A |
| ocr-scan | unsupported_answer_rate | 0 | 0 | N/A |
| ocr-mixed | hit_at_4 | 0 | 0 | N/A |
| ocr-mixed | evidence_coverage_at_4 | 0 | 0 | N/A |
| ocr-mixed | answer_accuracy | 0 | 0 | N/A |
| ocr-mixed | false_refusal_rate | 0 | 0 | N/A |
| ocr-mixed | correct_refusal_rate | 0 | 0 | N/A |
| ocr-mixed | unsupported_answer_rate | 0 | 0 | N/A |

## Failures

- osha-15: generation_failure. AI-assisted manual review by Codex root: Rank-one p80-c2 explicitly gives at least 20 feet when the barrier alternative is not used. NOT FOUND is a false refusal despite complete evidence.
- nist-ai-13: unsupported_answer. AI-assisted manual review by Codex root: The displayed answer identifies gaps toward risk-management goals; p38-c3 supplies the comparison/gap clause and the preceding Target Profile goal definition, so f1 is supported semantically despite the final line break. However, the action-plan sentence is absent from every retrieved chunk. Full extracted page 38 contains it after p38-c3's cutoff, confirming retrieval loss rather than extraction loss. The proposed strategies/actions recommendation lacks cited support; it also omits the frozen category/subcategory-outcome detail, so f2 is incomplete. This is not proof of fabricated source content: the full source, unavailable to generation, does discuss action plans.
- nist-ai-15: unsupported_answer. AI-assisted manual review by Codex root: Cited p40-c5/p41-c1 supply lifecycle-wide TEVV and the ideal separation of verification/validation actors from test/evaluation actors. The design-phase detail is supported by p41-c1. However, the added claim that the actors work together to manage lifecycle risks appears in retrieved p14-c3, not the cited p40-c5/p41-c1/p16-c1. Under the unchanged citation-level rubric, that material extra claim lacks cited support, as in development nist-ai-07.
- nist-ai-16: generation_failure. AI-assisted manual review by Codex root: Rank-one p43-c4 explicitly names data, model, and concept drift as reasons for more frequent maintenance and corrective-maintenance triggers. NOT FOUND is a false refusal despite all three retrieved facts.
- nist-csf-13: incomplete_retrieval. AI-assisted manual review by Codex root: Retrieved p18-c1 supplies embarrassment as a dignity-type effect but cuts off before stigma and the three tangible harms. Full extracted page 18 contains all five examples, confirming retrieval loss rather than extraction loss. NOT FOUND is a document-level false refusal with incomplete retrieved evidence.
- nist-csf-17: incomplete_retrieval. AI-assisted manual review by Codex root: None of the four retrieved chunks contains PR.PS-05 or the unauthorized-software requirement. Full extracted page 25 contains it intact. NOT FOUND is a document-level false refusal caused by incomplete retrieval, not extraction loss.
- nist-csf-18: incomplete_retrieval. AI-assisted manual review by Codex root: Retrieved p17-c4 starts after the requested publication-number mappings; the other chunks do not supply either mapping. Full extracted page 17 contains SP 800-37 and SP 800-30 with both titles intact. NOT FOUND is a document-level false refusal with incomplete retrieval.

Latency and operational error counts are in summary.json; indexing is in run.json and excluded from query latency. Only the explicitly selected split is included in this report.
