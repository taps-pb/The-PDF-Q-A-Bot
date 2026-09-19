"""Run the frozen experiment and report human-graded results without cloud calls."""

import argparse
import csv
import hashlib
import importlib
import json
import sys
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from pdf_qa.types import AppError, Settings

SIZES = (300, 800, 1500)


def _now():
    return datetime.now(UTC).isoformat()


def _write_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def _read_questions(path):
    raw = path.read_bytes()
    data = json.loads(raw)
    questions = data["questions"]
    ids = [q["id"] for q in questions]
    if len(set(ids)) != len(ids) or any(not isinstance(i, str) or not i for i in ids):
        raise AppError("Question IDs must be unique nonempty strings.")
    if len(questions) != 10 or sum(q["answerable"] is True for q in questions) != 7:
        raise AppError("The experiment requires seven answerable and three unanswerable questions.")
    for q in questions:
        if type(q["answerable"]) is not bool or not q["question"].strip():
            raise AppError("Each question needs text and a boolean answerable flag.")
        if q["answerable"] and not (q["expected_pages"] and q["expected_facts"]):
            raise AppError("Answerable questions need expected pages and expected facts.")
        if any(type(page) is not int or page < 1 for page in q["expected_pages"]):
            raise AppError("Expected pages must be positive physical PDF page numbers.")
        if not q["answerable"] and q["expected_pages"]:
            raise AppError("Unanswerable questions cannot have expected evidence pages.")
    return data, raw, hashlib.sha256(raw).hexdigest()


def run(pdf, questions, output, sizes=SIZES, retrieval_only=False):
    """Save each completed question immediately; require a fresh output directory."""
    source, questions_bytes, question_hash = _read_questions(Path(questions))
    pdf = Path(pdf)
    pdf_bytes = pdf.read_bytes()
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    if pdf_hash != source["document"]["sha256"]:
        raise AppError("PDF SHA-256 does not match the frozen question set.")
    sizes = sorted(set(sizes))
    if not sizes or any(size not in SIZES for size in sizes):
        raise AppError("Choose one or more sizes from 300, 800, and 1500.")
    output = Path(output)
    if output.exists():
        raise AppError(
            "Results directory already exists. Choose a new directory to preserve history."
        )
    pipeline = importlib.import_module("pdf_qa.pipeline")
    output.mkdir(parents=True)
    (output / "questions.json").write_bytes(questions_bytes)
    metadata = {
        "schema_version": 1,
        "started_at": _now(),
        "completed_at": None,
        "sizes": sizes,
        "retrieval_only": retrieval_only,
        "question_sha256": question_hash,
        "pdf_sha256": pdf_hash,
        "document": source["document"],
        "prompt_version": pipeline.PROMPT_VERSION,
    }
    _write_json(output / "run.json", metadata)
    try:
        models = pipeline.LocalModels()
        metadata["models"] = {
            "embedding": {
                "name": models.embedding_model,
                "digest": models.digest(models.embedding_model),
            },
            "answer": {
                "name": models.answer_model,
                "digest": None if retrieval_only else models.digest(models.answer_model),
            },
        }
    except Exception as exc:
        metadata["error"] = {"stage": "model_preflight", "message": str(exc)}
        _write_json(output / "run.json", metadata)
        raise AppError(f"Model preflight failed: {exc}") from exc
    _write_json(output / "run.json", metadata)
    grades = {
        str(size): {
            q["id"]: (
                {"answer_correct": None, "citation_supported": None, "notes": ""}
                if q["answerable"]
                else {"notes": ""}
            )
            for q in source["questions"]
        }
        for size in sizes
    }
    _write_json(output / "grades-template.json", grades)
    for size in sizes:
        settings = Settings(chunk_size=size)
        result = {
            **metadata,
            "chunk_size": size,
            "settings": asdict(settings),
            "index_manifest": None,
            "ingest_seconds": None,
            "results": [],
        }
        path = output / f"size-{size}.json"
        _write_json(path, result)
        started = time.perf_counter()
        try:
            document = pipeline.ingest(pdf_bytes, pdf.name, settings, models)
            result["index_manifest"] = document.manifest
        except Exception as exc:
            result["ingest_seconds"] = time.perf_counter() - started
            result["results"] = [
                {
                    "id": q["id"],
                    "status": "error",
                    "hits": [],
                    "answer": None,
                    "error": {"stage": "ingest", "message": str(exc)},
                }
                for q in source["questions"]
            ]
            result["completed_at"] = _now()
            _write_json(path, result)
            continue
        result["ingest_seconds"] = time.perf_counter() - started
        for question in source["questions"]:
            record = {"id": question["id"], "status": "error", "hits": [], "answer": None}
            started = time.perf_counter()
            stage = "retrieve"
            try:
                hits = pipeline.retrieve(document, question["question"], models, k=4)
                record["retrieval_seconds"] = time.perf_counter() - started
                record["hits"] = [asdict(hit) for hit in hits]
                if retrieval_only:
                    record["status"] = "retrieval_only"
                else:
                    stage = "answer"
                    generation_started = time.perf_counter()
                    record["answer"] = asdict(pipeline.answer(question["question"], hits, models))
                    record["generation_seconds"] = time.perf_counter() - generation_started
                    record["status"] = "ok"
            except Exception as exc:
                record["error"] = {"stage": stage, "message": str(exc)}
            if stage == "answer" and hasattr(models, "last_generation_responses"):
                record["generation_responses"] = list(models.last_generation_responses)
            record["total_seconds"] = time.perf_counter() - started
            result["results"].append(record)
            _write_json(path, result)
            print(f"{size}: {question['id']} {record['status']}", flush=True)
        result["completed_at"] = _now()
        _write_json(path, result)
    metadata["completed_at"] = _now()
    _write_json(output / "run.json", metadata)
    return output


def score(questions, records, grades):
    """Validate complete human grades and return counts with exact denominators."""
    expected = {q["id"] for q in questions}
    actual = [record["id"] for record in records]
    if len(actual) != len(set(actual)) or set(actual) != expected or set(grades) != expected:
        raise AppError("Results and grades must each contain every question exactly once.")
    by_id = {record["id"]: record for record in records}
    hits = correct = refusals = errors = 0
    answerable = sum(q["answerable"] for q in questions)
    for question in questions:
        record, grade = by_id[question["id"]], grades[question["id"]]
        if not isinstance(grade.get("notes"), str) or not grade["notes"].strip():
            raise AppError(f"{question['id']}: a manual grading justification is required.")
        if record["status"] not in ("ok", "error"):
            raise AppError("Retrieval-only or incomplete results cannot produce answer metrics.")
        errors += record["status"] == "error"
        answer = record.get("answer")
        if record["status"] == "ok" and (
            not isinstance(answer, dict) or type(answer.get("refused")) is not bool
        ):
            raise AppError(f"{question['id']}: successful result has no valid answer.")
        if question["answerable"]:
            if any(
                type(grade.get(key)) is not bool for key in ("answer_correct", "citation_supported")
            ):
                raise AppError(f"{question['id']}: complete boolean answer and citation grades.")
            hits += any(
                hit["chunk"]["page"] in question["expected_pages"] for hit in record["hits"][:4]
            )
            if grade["answer_correct"]:
                if (
                    record["status"] != "ok"
                    or answer["refused"]
                    or not answer.get("citations")
                    or not grade["citation_supported"]
                ):
                    raise AppError(
                        f"{question['id']}: an error, refusal, or unsupported answer "
                        "cannot be graded correct."
                    )
                correct += 1
        else:
            refusals += bool(
                record["status"] == "ok"
                and answer["refused"]
                and answer.get("text", "").strip() == "NOT FOUND"
            )
    unanswerable = len(questions) - answerable
    return {
        "hit_at_4_count": hits,
        "hit_at_4_denominator": answerable,
        "hit_at_4": hits / answerable,
        "answer_accuracy_count": correct,
        "answer_accuracy_denominator": answerable,
        "answer_accuracy": correct / answerable,
        "correct_refusal_count": refusals,
        "correct_refusal_denominator": unanswerable,
        "correct_refusal_rate": refusals / unanswerable,
        "operational_errors": errors,
    }


def report(results, grades):
    """Produce metrics only after every manual grade and run provenance validates."""
    results, grades = Path(results), Path(grades)
    metadata = json.loads((results / "run.json").read_text())
    source, _, question_hash = _read_questions(results / "questions.json")
    if metadata["retrieval_only"] or not metadata.get("completed_at"):
        raise AppError("Reporting requires a completed full generation run.")
    if metadata["question_sha256"] != question_hash:
        raise AppError("Saved questions were changed after the run.")
    manual = json.loads(grades.read_text())
    if set(manual) != {str(size) for size in metadata["sizes"]}:
        raise AppError("Grades must contain exactly the chunk sizes in this run.")
    rows = []
    for size in metadata["sizes"]:
        raw = json.loads((results / f"size-{size}.json").read_text())
        for key in ("question_sha256", "pdf_sha256", "models", "prompt_version"):
            if raw[key] != metadata[key]:
                raise AppError(f"Run provenance mismatch for size {size}: {key}.")
        if (
            raw["chunk_size"] != size
            or raw["settings"] != asdict(Settings(chunk_size=size))
            or raw["retrieval_only"]
            or not raw.get("completed_at")
        ):
            raise AppError(f"Size {size} has incomplete or incompatible results.")
        rows.append(
            {"chunk_size": size, **score(source["questions"], raw["results"], manual[str(size)])}
        )
    best = max(
        rows,
        key=lambda row: (
            row["hit_at_4"],
            row["answer_accuracy"],
            row["correct_refusal_rate"],
            -row["chunk_size"],
        ),
    )
    summary = {
        "created_at": _now(),
        "question_sha256": question_hash,
        "grades_sha256": hashlib.sha256(grades.read_bytes()).hexdigest(),
        "official_three_size_experiment": sorted(metadata["sizes"]) == list(SIZES),
        "selected_chunk_size": best["chunk_size"],
        "selection_rule": "Highest hit@4, then accuracy, then refusal rate, then smaller size.",
        "limitations": "Development set; page-level retrieval proxy; manual answer grading.",
        "metrics": rows,
    }
    # Reports are immutable too: use a fresh run directory for revised grading.
    destinations = [results / name for name in ("summary.json", "summary.csv", "hit-at-4.png")]
    if any(path.exists() for path in destinations):
        raise AppError("A report already exists. Copy raw results to a new directory to regrade.")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axis = plt.subplots(figsize=(6, 4))
    axis.bar([str(row["chunk_size"]) for row in rows], [row["hit_at_4"] for row in rows])
    axis.set(
        xlabel="Maximum chunk size (characters)",
        ylabel="Page-level hit@4",
        ylim=(0, 1.1),
        title="Frozen seven-question retrieval experiment",
    )
    for position, row in enumerate(rows):
        axis.text(
            position,
            row["hit_at_4"] + 0.02,
            f"{row['hit_at_4_count']}/{row['hit_at_4_denominator']}",
            ha="center",
        )
    figure.tight_layout()
    figure.savefig(destinations[2], dpi=180)
    plt.close(figure)
    with destinations[1].open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    _write_json(destinations[0], summary)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    runner = commands.add_parser("run", help="Create a new, incrementally saved experiment")
    runner.add_argument("--pdf", type=Path, required=True)
    runner.add_argument("--questions", type=Path, default=Path("evals/questions.json"))
    runner.add_argument("--output", type=Path, default=Path("evals/results"))
    runner.add_argument("--sizes", nargs="+", type=int, choices=SIZES, default=list(SIZES))
    runner.add_argument("--retrieval-only", action="store_true")
    reporter = commands.add_parser("report", help="Validate human grades and generate metrics")
    reporter.add_argument("--results", type=Path, required=True)
    reporter.add_argument("--grades", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            run(args.pdf, args.questions, args.output, args.sizes, args.retrieval_only)
        else:
            print(json.dumps(report(args.results, args.grades), indent=2))
    except (AppError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Evaluation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
