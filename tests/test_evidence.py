"""Explicit evidence judgments, honest denominators, and paired-case reports."""

from copy import deepcopy

import pytest

from pdf_qa.evidence import grade_template, review_packet, summarize
from pdf_qa.types import AppError


def example(case_id="d-01", answerable=True, variant="native", document_id="d"):
    case = {
        "id": case_id.split("--")[0],
        "case_id": case_id,
        "document_id": document_id,
        "variant": variant,
        "split": "development",
        "question": "Name both requirements.",
        "answerable": answerable,
        "absence_reason": "No such fact in the document.",
        "facts": [
            {
                "id": "f1",
                "text": "First requirement",
                "evidence": [
                    [{"page": 2, "quote": "First piece"}, {"page": 3, "quote": "Second piece"}],
                    [{"page": 4, "quote": "Alternative wording"}],
                ],
            },
            {
                "id": "f2",
                "text": "Second requirement",
                "evidence": [
                    [{"page": 2, "quote": "Required final sentence"}],
                ],
            },
        ]
        if answerable
        else [],
    }
    record = {
        "case_id": case_id,
        "status": "ok",
        "hits": [
            {
                "chunk": {"id": "c1", "page": 2, "text": "First piece only", "method": "native"},
                "score": 0.8,
            },
        ],
        "answer": {
            "text": "An answer" if answerable else "NOT FOUND",
            "citations": [2] if answerable else [],
            "chunk_ids": ["c1"] if answerable else [],
            "refused": not answerable,
        },
        "error": None,
        "retrieval_seconds": 1.0,
        "generation_seconds": 3.0,
        "extracted_evidence_pages": [{"number": 2, "text": "Full page text", "method": "ocr"}],
    }
    grade = grade_template([case])[case_id]
    for fact in grade["facts"].values():
        fact.update(evidence_present=True, answer_correct=True, citation_supported=True)
    grade.update(unsupported_claims=False, failure_category="none", notes="Reviewed each fact.")
    return case, record, grade


def run(*examples):
    return summarize(
        [x[0] for x in examples],
        [x[1] for x in examples],
        {x[0]["case_id"]: x[2] for x in examples},
    )


def test_same_page_hit_is_not_complete_evidence_and_all_facts_are_required():
    case, record, grade = example()
    grade["facts"]["f2"].update(
        evidence_present=False, answer_correct=False, citation_supported=False
    )
    grade.update(unsupported_claims=True, failure_category="incomplete_retrieval")
    metrics = run((case, record, grade))["native"]["overall"]
    assert metrics["hit_at_4"] == {"count": 1, "denominator": 1, "rate": 1}
    assert metrics["evidence_coverage_at_4"]["rate"] == 0
    assert metrics["answer_accuracy"]["rate"] == 0
    assert metrics["unsupported_answer_rate"]["rate"] == 1


def test_review_shows_all_alternative_pieces_and_never_autogrades():
    case, record, _ = example()
    template = grade_template([case])
    assert template[case["case_id"]]["facts"]["f1"]["evidence_present"] is None
    packet = review_packet([case], [record])
    for text in (
        "First piece",
        "Second piece",
        "Alternative wording",
        "Required final sentence",
        "all pieces required",
        "Full page text",
        "Rank 1",
        "score 0.8",
        "c1",
    ):
        assert text in packet
    assert "Physical PDF page 3" in packet
    with pytest.raises(AppError, match="justification"):
        summarize([case], [record], template)


def test_errors_refusals_incorrect_answers_and_latency_denominators():
    good = example()
    refusal = example("d-02")
    refusal[1]["answer"] = {"text": "NOT FOUND", "citations": [], "chunk_ids": [], "refused": True}
    for fact in refusal[2]["facts"].values():
        fact.update(answer_correct=False, citation_supported=False)
    refusal[2]["failure_category"] = "generation_failure"
    error = example("d-03")
    error[1].update(status="error", answer=None, generation_seconds=None)
    for fact in error[2]["facts"].values():
        fact.update(answer_correct=False, citation_supported=False)
    error[2]["failure_category"] = "operational_error"
    missing = example("d-04", False)
    broken = example("d-05", False)
    broken[1].update(status="error", answer=None, retrieval_seconds=None, generation_seconds=None)
    broken[2]["failure_category"] = "operational_error"
    metrics = run(good, refusal, error, missing, broken)["native"]["overall"]
    assert metrics["answer_accuracy"]["rate"] == 1 / 3
    assert metrics["false_refusal_rate"]["rate"] == 1 / 3
    assert metrics["correct_refusal_rate"]["rate"] == 1 / 2
    assert metrics["evidence_coverage_at_4"]["count"] == 3
    assert metrics["unsupported_answer_rate"]["denominator"] == 1
    assert metrics["operational_errors"] == 2
    assert metrics["latency"]["retrieval"]["count"] == 4
    assert metrics["latency"]["generation"]["count"] == 3


def test_document_variant_groups_and_null_denominators():
    examples = [
        example(),
        example("d-01--scan", variant="scan"),
        example("d-01--mixed", variant="mixed"),
        example("x-01", document_id="x"),
    ]
    summary = run(*examples)
    assert summary["native"]["overall"]["answer_accuracy"]["denominator"] == 2
    assert summary["native"]["by_document"]["d"]["answer_accuracy"]["denominator"] == 1
    assert summary["ocr"]["overall"]["answer_accuracy"]["denominator"] == 2
    assert summary["ocr"]["by_variant"]["scan"]["answer_accuracy"]["denominator"] == 1
    assert summary["ocr"]["pairs"] == [
        {
            "question_id": "d-01",
            "document_id": "d",
            "native_case_id": "d-01",
            "scan_case_id": "d-01--scan",
            "mixed_case_id": "d-01--mixed",
        }
    ]
    assert summary["native"]["overall"]["correct_refusal_rate"]["rate"] is None
    empty = run()["native"]["overall"]
    assert empty["answer_accuracy"] == {"count": 0, "denominator": 0, "rate": None}
    assert empty["latency"]["generation"]["median_seconds"] is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("evidence_present", None),
        ("answer_correct", 1),
        ("citation_supported", "true"),
    ],
)
def test_fact_grades_require_strict_booleans(field, value):
    case, record, grade = example()
    grade["facts"]["f1"][field] = value
    with pytest.raises(AppError, match="boolean"):
        run((case, record, grade))


def test_missing_ids_duplicates_citations_and_invalid_categories():
    case, record, grade = example()
    with pytest.raises(AppError, match="exactly once"):
        summarize([case], [record], {})
    with pytest.raises(AppError, match="exactly once"):
        summarize([case], [record, record], {case["case_id"]: grade})
    for field, value in (("chunk_ids", ["unseen"]), ("citations", [7])):
        altered = deepcopy(record)
        altered["answer"][field] = value
        with pytest.raises(AppError, match="retrieved chunk"):
            run((case, altered, grade))
    for category in ("incomplete_retrieval", "extraction_loss", "operational_error"):
        altered = {**grade, "failure_category": category}
        with pytest.raises(AppError):
            run((case, record, altered))
    grade["facts"]["f1"].update(evidence_present=False, citation_supported=False)
    grade["failure_category"] = "generation_failure"
    with pytest.raises(AppError, match="complete retrieved evidence"):
        run((case, record, grade))


def test_supported_off_topic_unanswerable_answer_is_not_a_correct_refusal():
    case, record, grade = example(answerable=False)
    record["answer"].update(
        text="Supported but irrelevant", refused=False, citations=[2], chunk_ids=["c1"]
    )
    grade["failure_category"] = "generation_failure"
    metrics = run((case, record, grade))["native"]["overall"]
    assert metrics["correct_refusal_rate"]["rate"] == 0
    assert metrics["unsupported_answer_rate"]["rate"] == 0


def test_refusal_and_error_cannot_receive_positive_answer_grades():
    case, record, grade = example()
    record.update(status="error", answer=None)
    grade["failure_category"] = "operational_error"
    with pytest.raises(AppError, match="cannot have correct"):
        run((case, record, grade))
    case, record, grade = example(answerable=False)
    record["answer"]["text"] = "Perhaps not found"
    with pytest.raises(AppError, match="valid refusal"):
        run((case, record, grade))


def test_top_four_only_and_nonfinite_timings_rejected():
    case, record, grade = example()
    relevant = record["hits"][0]
    record["hits"] = [{"chunk": {"id": "wrong", "page": 9}}] * 4 + [relevant]
    with pytest.raises(AppError, match="retrieved chunk"):
        run((case, record, grade))
    case, record, grade = example()
    record["generation_seconds"] = float("nan")
    with pytest.raises(AppError, match="finite"):
        run((case, record, grade))
