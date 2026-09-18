"""Review evidence explicitly and report complete, separately grouped evaluations."""

import math
from collections import Counter
from statistics import median

from pdf_qa.types import AppError

FAILURE_CATEGORIES = (
    "none",
    "extraction_loss",
    "incomplete_retrieval",
    "generation_failure",
    "unsupported_answer",
    "operational_error",
)
FACT_FIELDS = ("evidence_present", "answer_correct", "citation_supported")


def grade_template(cases):
    """Leave every judgment unset; text matching never supplies semantic grades."""
    _case_ids(cases)
    return {
        case["case_id"]: {
            "facts": {fact["id"]: dict.fromkeys(FACT_FIELDS) for fact in case["facts"]},
            "unsupported_claims": None,
            "failure_category": None,
            "notes": "",
        }
        for case in cases
    }


def _case_ids(cases):
    ids = [case["case_id"] for case in cases]
    if len(ids) != len(set(ids)) or any(not isinstance(i, str) or not i for i in ids):
        raise AppError("Cases must have unique nonempty case IDs.")
    return set(ids)


def _records(cases, records):
    ids = _case_ids(cases)
    actual = [record["case_id"] for record in records]
    if len(actual) != len(set(actual)) or set(actual) != ids:
        raise AppError("Results must contain every case exactly once.")
    return {record["case_id"]: record for record in records}


def _quote(text):
    return "\n".join("> " + line for line in str(text).splitlines())


def review_packet(cases, records):
    """Render annotations and actual evidence together without assigning grades."""
    by_id = _records(cases, records)
    lines = [
        "# Evidence review packet",
        "",
        "Page numbers are physical PDF pages (one-based). Review semantic support manually.",
        "Every piece within an alternative is required; any complete alternative suffices.",
        "Exact excerpt matches are inspection aids, not automatic evidence or answer grades.",
    ]
    for case in cases:
        record = by_id[case["case_id"]]
        lines.extend(
            [
                "",
                f"## {case['case_id']}",
                "",
                f"Document: {case['document_id']}; variant: {case['variant']}; "
                f"split: {case['split']}; answerable: {case['answerable']}.",
                "",
                _quote(case["question"]),
                "",
                "### Expected facts and evidence",
                "",
            ]
        )
        if not case["answerable"]:
            lines.append(case["absence_reason"])
        for fact in case["facts"]:
            lines.extend([f"**{fact['id']}: {fact['text']}**", ""])
            for number, alternative in enumerate(fact["evidence"], 1):
                lines.extend([f"Alternative {number} (all pieces required):", ""])
                for piece in alternative:
                    lines.extend(
                        [f"Physical PDF page {piece['page']}:", _quote(piece["quote"]), ""]
                    )
        lines.extend(["### Extracted evidence pages", ""])
        for page in record.get("extracted_evidence_pages", []):
            lines.extend(
                [
                    f"Physical PDF page {page['number']} ({page['method']}):",
                    _quote(page["text"]),
                    "",
                ]
            )
        lines.extend(["### Retrieved passages", ""])
        for rank, hit in enumerate(record["hits"], 1):
            chunk = hit["chunk"]
            lines.extend(
                [
                    f"Rank {rank}; {chunk['id']}; physical PDF page {chunk['page']}; "
                    f"{chunk['method']}; score {hit['score']}.",
                    _quote(chunk["text"]),
                    "",
                ]
            )
        if not record["hits"]:
            lines.append("No passages retrieved.")
        lines.extend(["", "### Answer and outcome", "", f"Status: {record['status']}."])
        answer = record.get("answer")
        if answer:
            lines.extend(
                [
                    _quote(answer["text"]),
                    "",
                    f"Refused: {answer['refused']}; "
                    f"cited physical PDF pages: {answer['citations']}; "
                    f"cited chunk IDs: {answer['chunk_ids']}.",
                ]
            )
        if record.get("error"):
            lines.append(f"Error ({record['error']['stage']}): {record['error']['message']}")
        lines.extend(
            [
                "",
                "### Review fields",
                "",
                "For each fact: evidence_present, answer_correct, citation_supported (true/false).",
                "Record unsupported_claims, failure_category, and a specific review justification.",
            ]
        )
    return "\n".join(lines) + "\n"


def _validate(case, record, grade):
    prefix = case["case_id"] + ": "

    def require(condition, message):
        if not condition:
            raise AppError(prefix + message)

    require(record["status"] in ("ok", "error"), "result must be complete (ok or error).")
    require(case["variant"] in ("native", "scan", "mixed"), "unknown variant.")
    require(
        isinstance(grade.get("notes"), str) and grade["notes"].strip(),
        "a specific manual grading justification is required.",
    )
    require(type(grade.get("unsupported_claims")) is bool, "unsupported_claims must be boolean.")
    require(grade.get("failure_category") in FAILURE_CATEGORIES, "choose a failure category.")
    facts = grade.get("facts")
    require(
        isinstance(facts, dict) and set(facts) == {f["id"] for f in case["facts"]},
        "grades must contain exactly the expected fact IDs.",
    )
    for fact in facts.values():
        require(
            isinstance(fact, dict) and all(type(fact.get(k)) is bool for k in FACT_FIELDS),
            "every fact needs complete boolean evidence, answer, and citation grades.",
        )
    answer = record.get("answer")
    successful = record["status"] == "ok"
    if successful:
        require(
            isinstance(answer, dict) and type(answer.get("refused")) is bool,
            "successful result has no valid answer.",
        )
        require(
            isinstance(answer.get("text"), str) and answer["text"].strip(),
            "successful answer requires text.",
        )
        require(
            isinstance(answer.get("citations"), list) and isinstance(answer.get("chunk_ids"), list),
            "invalid citation fields.",
        )
    refused = successful and answer["refused"]
    nonrefused = successful and not refused
    if refused:
        require(
            answer["text"].strip() == "NOT FOUND"
            and not answer["citations"]
            and not answer["chunk_ids"],
            "a valid refusal is NOT FOUND without citations.",
        )
    if not nonrefused:
        require(not grade["unsupported_claims"], "errors and refusals have no unsupported answer.")
        require(
            not any(f["answer_correct"] or f["citation_supported"] for f in facts.values()),
            "errors and refusals cannot have correct answer or supported citation grades.",
        )
    require(
        bool(record["hits"][:4]) or not any(f["evidence_present"] for f in facts.values()),
        "evidence cannot be present without retrieved passages.",
    )
    require(
        all(not f["citation_supported"] or f["evidence_present"] for f in facts.values()),
        "a supported citation requires retrieved evidence for that fact.",
    )
    if nonrefused and (
        not grade["unsupported_claims"] or any(f["citation_supported"] for f in facts.values())
    ):
        chunks = {h["chunk"]["id"]: h["chunk"]["page"] for h in record["hits"][:4]}
        ids, pages = answer["chunk_ids"], answer["citations"]
        require(
            bool(ids)
            and all(isinstance(i, str) and i in chunks for i in ids)
            and all(type(p) is int for p in pages)
            and set(pages) == {chunks[i] for i in ids},
            "supported citations must name retrieved chunk IDs and their exact pages.",
        )
    evidence = case["answerable"] and all(f["evidence_present"] for f in facts.values())
    correct = refused
    if case["answerable"]:
        correct = (
            nonrefused
            and not grade["unsupported_claims"]
            and all(f["answer_correct"] and f["citation_supported"] for f in facts.values())
        )
    category = grade["failure_category"]
    require(
        (category == "operational_error") == (not successful),
        "operational_error is required only for operational errors.",
    )
    require(category != "none" or correct, "a failed answer cannot have category none.")
    require(
        category not in ("extraction_loss", "incomplete_retrieval")
        or (case["answerable"] and not evidence),
        "extraction/retrieval failure requires incomplete evidence.",
    )
    require(
        category != "generation_failure" or evidence or not case["answerable"],
        "generation_failure requires complete retrieved evidence.",
    )
    require(
        category != "generation_failure" or not correct,
        "a correct supported answer or correct refusal cannot be a generation failure.",
    )
    require(
        category != "unsupported_answer"
        or (
            nonrefused
            and (
                grade["unsupported_claims"]
                or any(not f["citation_supported"] for f in facts.values())
            )
        ),
        "unsupported_answer requires an unsupported, non-refused answer.",
    )
    for stage in ("retrieval", "generation"):
        value = record.get(stage + "_seconds")
        require(
            value is None or (type(value) in (int, float) and math.isfinite(value) and value >= 0),
            "stage timings must be finite nonnegative numbers or null.",
        )
    return {
        "case": case,
        "record": record,
        "grade": grade,
        "evidence": evidence,
        "correct": correct,
        "refused": refused,
        "nonrefused": nonrefused,
    }


def _fraction(count, denominator):
    return {
        "count": count,
        "denominator": denominator,
        "rate": count / denominator if denominator else None,
    }


def _metrics(rows):
    answerable = [row for row in rows if row["case"]["answerable"]]
    unanswerable = [row for row in rows if not row["case"]["answerable"]]
    nonrefused = [row for row in rows if row["nonrefused"]]
    hits = 0
    for row in answerable:
        pages = {
            piece["page"]
            for fact in row["case"]["facts"]
            for alternative in fact["evidence"]
            for piece in alternative
        }
        hits += any(h["chunk"]["page"] in pages for h in row["record"]["hits"][:4])
    metrics = {
        "hit_at_4": _fraction(hits, len(answerable)),
        "evidence_coverage_at_4": _fraction(
            sum(r["evidence"] for r in answerable), len(answerable)
        ),
        "answer_accuracy": _fraction(sum(r["correct"] for r in answerable), len(answerable)),
        "false_refusal_rate": _fraction(sum(r["refused"] for r in answerable), len(answerable)),
        "correct_refusal_rate": _fraction(
            sum(r["refused"] for r in unanswerable), len(unanswerable)
        ),
        "unsupported_answer_rate": _fraction(
            sum(r["grade"]["unsupported_claims"] for r in nonrefused), len(nonrefused)
        ),
        "operational_errors": sum(r["record"]["status"] == "error" for r in rows),
        "latency": {},
    }
    for stage in ("retrieval", "generation"):
        values = sorted(
            r["record"][stage + "_seconds"]
            for r in rows
            if r["record"].get(stage + "_seconds") is not None
        )
        metrics["latency"][stage] = {
            "count": len(values),
            "median_seconds": median(values) if values else None,
            "p95_seconds": values[math.ceil(len(values) * 0.95) - 1] if values else None,
        }
    return metrics


def summarize(cases, records, grades):
    """Reject incomplete reviews, then keep native and paired OCR accounting separate."""
    by_id = _records(cases, records)
    if not isinstance(grades, dict) or set(grades) != _case_ids(cases):
        raise AppError("Grades must contain every case exactly once.")
    rows = [_validate(case, by_id[case["case_id"]], grades[case["case_id"]]) for case in cases]
    native = [row for row in rows if row["case"]["variant"] == "native"]
    ocr = [row for row in rows if row["case"]["variant"] != "native"]
    pair_ids = sorted({(r["case"]["document_id"], r["case"]["id"]) for r in ocr})
    pairs = []
    for document_id, question_id in pair_ids:
        variants = {
            r["case"]["variant"]: r["case"]["case_id"]
            for r in rows
            if (r["case"]["document_id"], r["case"]["id"]) == (document_id, question_id)
        }
        pairs.append(
            {
                "question_id": question_id,
                "document_id": document_id,
                **{v + "_case_id": variants.get(v) for v in ("native", "scan", "mixed")},
            }
        )
    failures = [
        {
            "case_id": r["case"]["case_id"],
            "document_id": r["case"]["document_id"],
            "variant": r["case"]["variant"],
            "category": r["grade"]["failure_category"],
            "notes": r["grade"]["notes"],
        }
        for r in rows
        if r["grade"]["failure_category"] != "none"
    ]
    counts = Counter(f["category"] for f in failures)
    return {
        "native": {
            "overall": _metrics(native),
            "by_document": {
                document_id: _metrics(
                    [r for r in native if r["case"]["document_id"] == document_id]
                )
                for document_id in sorted({r["case"]["document_id"] for r in native})
            },
        },
        "ocr": {
            "overall": _metrics(ocr),
            "by_variant": {
                variant: _metrics([r for r in ocr if r["case"]["variant"] == variant])
                for variant in ("scan", "mixed")
            },
            "pairs": pairs,
        },
        "failures": failures,
        "failure_counts": {category: counts[category] for category in FAILURE_CATEGORIES[1:]},
    }
