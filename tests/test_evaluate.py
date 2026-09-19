"""Evaluation accounting, grade validation, and offline runner integration."""

import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest

from pdf_qa.evaluate import report, run, score
from pdf_qa.types import Answer, AppError, Chunk, SearchHit


def question_set():
    return json.loads((Path(__file__).parents[1] / "evals/questions.json").read_text())


def graded_records():
    questions = question_set()["questions"]
    records, grades = [], {}
    for q in questions:
        answerable = q["answerable"]
        hits = (
            [asdict(SearchHit(Chunk("p5-c1", "Evidence", q["expected_pages"][0], "native"), 0.9))]
            if answerable
            else []
        )
        records.append(
            {
                "id": q["id"],
                "status": "ok",
                "hits": hits,
                "answer": asdict(
                    Answer(
                        "Supported answer" if answerable else "NOT FOUND",
                        q["expected_pages"],
                        ["p5-c1"],
                        not answerable,
                    )
                ),
            }
        )
        grades[q["id"]] = {"notes": "Manually checked expected facts against cited passage."}
        if answerable:
            grades[q["id"]].update(answer_correct=True, citation_supported=True)
    return questions, records, grades


def test_metrics_use_fixed_denominators_and_errors_are_not_refusals():
    questions, records, grades = graded_records()
    records[0]["status"] = "error"
    records[0]["answer"] = None
    grades["q1"]["answer_correct"] = False
    grades["q1"]["citation_supported"] = False
    records[1]["hits"] = []
    records[-1]["status"] = "error"
    records[-1]["answer"] = None
    metrics = score(questions, records, grades)
    assert metrics["hit_at_4"] == 6 / 7  # A generation error can still have a retrieval hit.
    assert metrics["answer_accuracy"] == 6 / 7
    assert metrics["correct_refusal_rate"] == 2 / 3
    assert metrics["operational_errors"] == 2
    assert metrics["answer_accuracy_denominator"] == 7
    assert metrics["correct_refusal_denominator"] == 3


def test_grade_validation_and_top_four_limit():
    questions, records, grades = graded_records()
    correct_hit = records[0]["hits"][0]
    unrelated = asdict(SearchHit(Chunk("p99-c1", "Unrelated", 99, "native"), 0.5))
    records[0]["hits"] = [unrelated] * 4 + [correct_hit]
    assert score(questions, records, grades)["hit_at_4_count"] == 6
    grades["q1"]["notes"] = ""
    with pytest.raises(AppError, match="justification"):
        score(questions, records, grades)
    grades["q1"]["notes"] = "Checked."
    grades["q1"]["citation_supported"] = False
    with pytest.raises(AppError, match="cannot be graded correct"):
        score(questions, records, grades)
    grades["q1"]["answer_correct"] = None
    with pytest.raises(AppError, match="boolean"):
        score(questions, records, grades)
    del grades["q1"]
    with pytest.raises(AppError, match="exactly once"):
        score(questions, records, grades)


def test_full_offline_run_report_and_preserved_history(tmp_path, monkeypatch):
    source = question_set()
    pdf = tmp_path / "handbook.pdf"
    pdf.write_bytes(b"fake PDF for pipeline substitute")
    source["document"]["sha256"] = hashlib.sha256(pdf.read_bytes()).hexdigest()
    questions = tmp_path / "questions.json"
    questions.write_text(json.dumps(source))
    output = tmp_path / "run"
    questions_by_text = {q["question"]: q for q in source["questions"]}

    def retrieve(document, text, models, k):
        q = questions_by_text[text]
        return (
            [SearchHit(Chunk(q["id"], "Evidence", q["expected_pages"][0], "native"), 0.8)]
            if q["answerable"]
            else []
        )

    def answer(question, hits, models):
        models.last_generation_responses = [question]
        return Answer(
            "Supported answer" if hits else "NOT FOUND",
            [hit.chunk.page for hit in hits],
            [hit.chunk.id for hit in hits],
            not hits,
        )

    fake = SimpleNamespace(
        PROMPT_VERSION="test-v1",
        LocalModels=lambda: SimpleNamespace(
            embedding_model="embed", answer_model="answer", digest=lambda name: name + "-digest"
        ),
        ingest=lambda *args: SimpleNamespace(manifest={"index_id": "test"}),
        retrieve=retrieve,
        answer=answer,
    )
    monkeypatch.setitem(sys.modules, "pdf_qa.pipeline", fake)
    run(pdf, questions, output)
    raw = json.loads((output / "size-800.json").read_text())
    assert raw["models"]["embedding"]["digest"] == "embed-digest"
    assert len(raw["results"]) == 10
    assert raw["results"][0]["hits"][0]["chunk"]["text"] == "Evidence"
    assert raw["results"][0]["generation_seconds"] >= 0
    assert raw["results"][0]["generation_responses"] == [source["questions"][0]["question"]]
    with pytest.raises(AppError, match="already exists"):
        run(pdf, questions, output)
    _, _, grades = graded_records()
    grades_file = output / "grades.json"
    grades_file.write_text(json.dumps({str(size): grades for size in (300, 800, 1500)}))
    summary = report(output, grades_file)
    assert summary["selected_chunk_size"] == 300
    assert summary["official_three_size_experiment"] is True
    assert all(row["answer_accuracy"] == 1 for row in summary["metrics"])
    assert (output / "hit-at-4.png").read_bytes().startswith(b"\x89PNG")
    assert "hit_at_4_denominator" in (output / "summary.csv").read_text()
    with pytest.raises(AppError, match="already exists"):
        report(output, grades_file)
    frozen = json.loads((output / "questions.json").read_text())
    frozen["questions"][0]["question"] += " Changed"
    (output / "questions.json").write_text(json.dumps(frozen))
    with pytest.raises(AppError, match="changed after"):
        report(output, grades_file)


def test_runner_records_failures_and_rejects_wrong_pdf(tmp_path, monkeypatch):
    source = question_set()
    pdf = tmp_path / "handbook.pdf"
    pdf.write_bytes(b"fake")
    questions = tmp_path / "questions.json"
    questions.write_text(json.dumps(source))
    output = tmp_path / "run"
    with pytest.raises(AppError, match="SHA-256"):
        run(pdf, questions, output)
    assert not output.exists()
    source["document"]["sha256"] = hashlib.sha256(pdf.read_bytes()).hexdigest()
    questions.write_text(json.dumps(source))

    def broken_ingest(*args):
        raise AppError("OCR failed")

    fake = SimpleNamespace(
        PROMPT_VERSION="test-v1",
        LocalModels=lambda: SimpleNamespace(
            embedding_model="embed", answer_model="answer", digest=lambda name: name + "-digest"
        ),
        ingest=broken_ingest,
    )
    monkeypatch.setitem(sys.modules, "pdf_qa.pipeline", fake)
    run(pdf, questions, output, sizes=[800], retrieval_only=True)
    raw = json.loads((output / "size-800.json").read_text())
    assert all(record["error"]["stage"] == "ingest" for record in raw["results"])
    assert raw["models"]["answer"]["digest"] is None
    with pytest.raises(AppError, match="full generation"):
        report(output, output / "grades-template.json")
