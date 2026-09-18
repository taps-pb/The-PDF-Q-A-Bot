# Phase 2A evidence report

Reviewer: Codex root (OSHA), phase2a_ai (NIST AI), phase2a_csf (NIST CSF); AI-assisted manual semantic review; not independent human adjudication

Split: development. OCR pairs are not independent questions.

| Group | Metric | Count | Denominator | Rate |
|---|---|---:|---:|---:|
| native-overall | hit_at_4 | 21 | 24 | 0.875 |
| native-overall | evidence_coverage_at_4 | 21 | 24 | 0.875 |
| native-overall | answer_accuracy | 12 | 24 | 0.500 |
| native-overall | false_refusal_rate | 9 | 24 | 0.375 |
| native-overall | correct_refusal_rate | 12 | 12 | 1.000 |
| native-overall | unsupported_answer_rate | 1 | 15 | 0.067 |
| native-nist-ai | hit_at_4 | 6 | 8 | 0.750 |
| native-nist-ai | evidence_coverage_at_4 | 6 | 8 | 0.750 |
| native-nist-ai | answer_accuracy | 2 | 8 | 0.250 |
| native-nist-ai | false_refusal_rate | 5 | 8 | 0.625 |
| native-nist-ai | correct_refusal_rate | 4 | 4 | 1.000 |
| native-nist-ai | unsupported_answer_rate | 1 | 3 | 0.333 |
| native-nist-csf | hit_at_4 | 7 | 8 | 0.875 |
| native-nist-csf | evidence_coverage_at_4 | 7 | 8 | 0.875 |
| native-nist-csf | answer_accuracy | 3 | 8 | 0.375 |
| native-nist-csf | false_refusal_rate | 4 | 8 | 0.500 |
| native-nist-csf | correct_refusal_rate | 4 | 4 | 1.000 |
| native-nist-csf | unsupported_answer_rate | 0 | 4 | 0.000 |
| native-osha | hit_at_4 | 8 | 8 | 1.000 |
| native-osha | evidence_coverage_at_4 | 8 | 8 | 1.000 |
| native-osha | answer_accuracy | 7 | 8 | 0.875 |
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

- osha-08: generation_failure. Strict frozen-fact completeness: p5-c2 plus p5-c3 retrieve both facts, but the answer omits the public-domain/copyright-free detail included in f1. Only p5-c3 is cited; it does not contain the public-domain clause. The requested permission and credit answers themselves are correct and supported. This is a borderline annotation-completeness failure, not an invented claim.
- nist-ai-01: incomplete_retrieval. AI-assisted manual semantic review: the native extraction of physical page 3 contains the 2028 deadline, but the four hits are p1-c1, p8-c3, p8-c2, and p47-c1. These discuss the title, framework development, and general updates without the review deadline. NOT FOUND is therefore a false refusal caused by missing retrieved evidence, not demonstrated extraction loss.
- nist-ai-03: incomplete_retrieval. AI-assisted manual semantic review: native physical page 9 contains both probability and consequence magnitude in the risk definition. Retrieved p1-c1, p4-c1, p34-c1, and p47-c1 contain a title, contents, measurement practices, and general framework attributes; none states the two components. NOT FOUND is a false refusal with incomplete retrieval.
- nist-ai-04: generation_failure. AI-assisted manual semantic review: p18-c4 includes the complete reliability definition, including required performance without failure, time interval, and conditions. p19-c1 supplies accuracy as closeness to true or accepted-as-true values. The trailing standards citation is cut in p18-c4, but no requested fact is missing. NOT FOUND occurs despite sufficient evidence for both facts.
- nist-ai-05: generation_failure. AI-assisted manual semantic review: the top hit p22-c3 names de-identification and aggregation, and explicitly explains the loss of accuracy under conditions such as data sparsity and its fairness/value implications. The complete three-fact answer is present in one passage. The model nevertheless returns NOT FOUND.
- nist-ai-06: generation_failure. AI-assisted manual semantic review: p23-c1 lists systemic, computational and statistical, and human-cognitive bias, then explicitly says each can occur without prejudice, partiality, or discriminatory intent. All four requested facts are intact in the top hit, yet the answer is NOT FOUND.
- nist-ai-07: unsupported_answer. AI-assisted manual semantic review: cited p21-c3 supplies both requested definitions, and p21-c4 elaborates mechanisms and output meaning; the expected facts are correct and supported. However, the answer also claims that these concepts together with transparency support each other. That material relationship is stated in retrieved p22-c1, which is not cited; cited p21-c3/p21-c4 do not establish the three-way relationship. Thus this is incomplete citation support for an added claim, not fabrication absent from the retrieved context.
- nist-csf-02: generation_failure. AI-assisted manual review: rank-one p31-c2 explicitly lists all six functions, Govern, Identify, Protect, Detect, Respond, and Recover. Extraction on physical pages 8 and 31 also preserves the full list. Despite complete retrieved evidence, the model returns NOT FOUND without citations. This is a demonstrated false refusal, not missing retrieval.
- nist-csf-03: incomplete_retrieval. AI-assisted manual review: p29-c1 supports Tier 1 = Partial, so f2 has semantic evidence even though this alternative page was not enumerated in the frozen annotations. Other hits are contents or introductory references. None gives the four-tier count or Tier 2/3/4 names. Extracted pages 12 and 31 retain the complete list but are not retrieved. NOT FOUND leaves every answer and citation fact false.
- nist-csf-06: generation_failure. AI-assisted manual review: p11-c2 contains both complete definitions and is cited correctly on physical page 11. The answer gives currently achieved outcomes and extent of achievement, but omits the required f1 qualification that a Current Profile also includes outcomes the organization is attempting to achieve. Under complete-fact grading this leaves f1 incomplete; the expressed current-profile statements themselves are supported. The target definition and its extra anticipated-change examples are supported. This is an omission, not an unsupported added claim.
- nist-csf-07: generation_failure. AI-assisted manual review: rank-two p15-c1 contains all four negative-risk options, mitigating, transferring, avoiding, and accepting, within the Section 5 paragraph. The source extraction is complete. The model nevertheless returns NOT FOUND without citations, so all four answer and citation grades are false despite complete evidence.
- nist-csf-08: generation_failure. AI-assisted manual review: p14-c4 explicitly maps new Informative Reference suggestions to olir@nist.gov and additional QSG topics to cyberframework@nist.gov. Both complete addresses and their purposes appear in the retrieved text and source extraction. NOT FOUND is a false refusal with no citations.

Latency and operational error counts are in summary.json; indexing is in run.json and excluded from query latency. Only the explicitly selected split is included in this report.
