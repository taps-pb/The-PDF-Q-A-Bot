"""Frozen-suite validation, deterministic OCR variants, and offline run/report flow."""

import io
import json
from types import SimpleNamespace

import pytest
from pypdf import PdfReader
from reportlab.pdfgen import canvas

from pdf_qa import suite
from pdf_qa.types import Answer, AppError, Chunk, Page, SearchHit


def write_json(path, value):
    path.write_text(json.dumps(value))


def test_provenance_records_actual_generation_settings_without_network(monkeypatch):
    def command(args, **kwargs):
        if args[0] == "tesseract":
            return "tesseract test-version\n"
        return "a" * 40 if "rev-parse" in args else ""

    monkeypatch.setattr(suite.subprocess, "check_output", command)
    monkeypatch.setattr(
        suite.httpx,
        "get",
        lambda *args, **kwargs: SimpleNamespace(
            raise_for_status=lambda: None, json=lambda: {"version": "test-version"}
        ),
    )
    models = SimpleNamespace(
        answer_model="local-answer",
        embedding_model="local-embedding",
        digest=lambda model: "digest-" + model,
    )
    metadata = suite.provenance({"name": "fixture"}, "development", models)
    assert metadata["generation"] == {
        "options": {"temperature": 0, "seed": 42, "num_ctx": 8192, "num_predict": 1200},
        "think": False,
        "keep_alive": "30m",
    }
    assert metadata["code_revision"] == "a" * 40
    assert metadata["dirty_state"] == ""
    assert metadata["runtime"]["ollama"] == "test-version"
    assert metadata["models"]["answer"]["digest"] == "digest-local-answer"
    assert len(metadata["lock_sha256"]) == len(metadata["prompt_sha256"]) == 64
    assert metadata["answer_schema"]["required"] == ["answer", "chunk_ids", "refused"]


def test_generation_provenance_rejects_unrecognized_implementation():
    with pytest.raises(AppError, match="Generation parameters changed"):
        suite.generation_parameters(write_json)


@pytest.fixture
def corpus(tmp_path):
    manifests = tmp_path / "suite"
    manifests.mkdir()
    documents = tmp_path / "corpus"
    documents.mkdir()
    filenames = []
    for document_id in ("alpha", "beta", "gamma"):
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=(180, 180), invariant=1)
        for page in range(1, 4):
            pdf.drawString(12, 100, f"{document_id} evidence page {page}")
            pdf.showPage()
        pdf.save()
        source = buffer.getvalue()
        (documents / f"{document_id}.pdf").write_bytes(source)
        questions = []
        for number in range(1, 21):
            answerable = number <= 8 or 13 <= number <= 18
            questions.append(
                {
                    "id": f"{document_id}-{number:02d}",
                    "split": "development" if number <= 12 else "heldout",
                    "family": f"family-{number}",
                    "category": "direct" if answerable else "unanswerable",
                    "question": f"{document_id} question {number:02d}?",
                    "answerable": answerable,
                    "facts": [
                        {
                            "id": "f1",
                            "text": "Expected evidence",
                            "evidence": [
                                [
                                    {
                                        "page": 2,
                                        "quote": f"{document_id} evidence page 2",
                                    }
                                ]
                            ],
                        }
                    ]
                    if answerable
                    else [],
                    "absence_reason": "The document does not specify this fact."
                    if not answerable
                    else "",
                }
            )
        filename = f"{document_id}.json"
        filenames.append(filename)
        write_json(
            manifests / filename,
            {
                "schema_version": 2,
                "document": {
                    "id": document_id,
                    "filename": f"{document_id}.pdf",
                    "title": f"{document_id} fixture",
                    "edition": "test-v1",
                    "url": f"https://example.com/{document_id}.pdf",
                    "sha256": suite.sha(source),
                    "pages": 3,
                },
                "questions": questions,
            },
        )
    manifest = manifests / "suite.json"
    write_json(manifest, {"schema_version": 2, "name": "test-suite", "documents": filenames})
    return manifest, documents


def test_load_suite_validates_exact_counts_and_source_excerpts(corpus):
    manifest, documents = corpus
    loaded = suite.load_suite(manifest, documents)
    assert len(loaded["documents"]) == 3
    assert len(loaded["cases"]) == 60
    assert sum(c["split"] == "development" for c in loaded["cases"]) == 36
    assert all(c["case_id"] == c["id"] and c["variant"] == "native" for c in loaded["cases"])


@pytest.mark.parametrize(
    "mutation, message",
    [
        (lambda e: e["questions"][1].update(id=e["questions"][0]["id"]), "duplicate"),
        (lambda e: e["questions"][12].update(family=e["questions"][0]["family"]), "crosses"),
        (lambda e: e["questions"].pop(), "counts"),
        (lambda e: e["questions"][0].update(facts=[]), "required facts"),
        (lambda e: e["questions"][8].update(absence_reason=""), "absence reason"),
        (lambda e: e["questions"][0]["facts"][0]["evidence"][0][0].update(page=4), "physical"),
        (
            lambda e: e["questions"][0]["facts"][0]["evidence"][0][0].update(quote="missing"),
            "Excerpt",
        ),
        (lambda e: e["document"].update(sha256="0" * 64), "hash mismatch"),
        (lambda e: e["document"].update(pages=2), "Page count"),
        (lambda e: e["document"].update(filename="../escape.pdf"), "metadata"),
    ],
)
def test_load_suite_rejects_bad_annotations_and_sources(corpus, mutation, message):
    manifest, documents = corpus
    entry_path = manifest.parent / "alpha.json"
    entry = json.loads(entry_path.read_text())
    mutation(entry)
    write_json(entry_path, entry)
    with pytest.raises(AppError, match=message):
        suite.load_suite(manifest, documents)


def test_cli_requires_explicit_run_split(tmp_path, capsys):
    with pytest.raises(SystemExit) as error:
        suite.main(["run", "--corpus-dir", str(tmp_path), "--output", str(tmp_path / "run")])
    assert error.value.code == 2
    assert "--split" in capsys.readouterr().err


def test_variants_preserve_pages_content_and_deterministic_hashes(corpus):
    _, documents = corpus
    source = (documents / "alpha.pdf").read_bytes()
    scan = suite.make_variant(source, [2])
    mixed = suite.make_variant(source, [2], mixed=True)
    assert scan == suite.make_variant(source, [2])
    assert mixed == suite.make_variant(source, [2], mixed=True)
    native_reader = PdfReader(io.BytesIO(source))
    for data, is_mixed in ((scan, False), (mixed, True)):
        reader = PdfReader(io.BytesIO(data))
        assert len(reader.pages) == 3
        for page in (0, 2):
            assert reader.pages[page].extract_text() == native_reader.pages[page].extract_text()
        text = reader.pages[1].extract_text()
        assert "alpha evidence" not in text
        assert bool(text.strip()) is is_mixed
        if is_mixed:
            assert "native header" in text
            assert len(text.strip()) > 40  # Exercises auto-OCR's native-text gate.
        assert len(reader.pages[1].images) == 1


def test_prepare_and_select_variants_without_heldout_leakage(corpus):
    manifest, documents = corpus
    variants = suite.prepare(manifest, documents)
    assert variants == suite.prepare(manifest, documents)
    assert len(variants["variants"]) == 6
    loaded = suite.load_suite(manifest, documents)
    selected = suite.selected_cases(loaded, "development", documents)
    assert len(selected) == 42
    assert len({case["case_id"] for case in selected}) == 42
    assert all(case["split"] == "development" for case in selected)
    for case in selected[-6:]:
        assert case["id"].endswith("-01")
        assert case["document"]["page_mapping"] == "identity"
        assert case["document"]["rasterized_pages"] == [2]
        assert case["document"]["source_sha256"] == next(
            d["sha256"] for d in loaded["documents"] if d["id"] == case["document_id"]
        )
    heldout = suite.selected_cases(loaded, "heldout", documents)
    assert len(heldout) == 24
    assert all(case["variant"] == "native" and case["split"] == "heldout" for case in heldout)
    with pytest.raises(AppError, match="explicitly"):
        suite.selected_cases(loaded, None, documents)
    (documents / "variants/alpha-scan.pdf").write_bytes(b"changed")
    with pytest.raises(AppError, match="hash mismatch"):
        suite.selected_cases(loaded, "development", documents)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda entries: entries[0].update(source_sha256="0" * 64),
        lambda entries: entries[0].update(rasterized_pages=[1]),
        lambda entries: entries[0].update(pages=4),
        lambda entries: entries[0].update(filename="../alpha.pdf"),
        lambda entries: entries.append(entries[0]),
    ],
)
def test_selected_cases_rejects_variant_identity_changes(corpus, mutation):
    manifest, documents = corpus
    variants = suite.prepare(manifest, documents)
    mutation(variants["variants"])
    write_json(documents / "variants/manifest.json", variants)
    with pytest.raises(AppError):
        suite.selected_cases(suite.load_suite(manifest, documents), "development", documents)


def test_run_and_report_with_local_fakes_preserve_history(corpus, tmp_path, monkeypatch):
    from pdf_qa import pipeline

    manifest, documents = corpus
    suite.prepare(manifest, documents)
    loaded = suite.load_suite(manifest, documents)
    by_text = {case["question"]: case for case in loaded["cases"]}
    indexed = []

    def ingest(source, name, settings, models):
        indexed.append((name, settings.ocr_mode))
        return SimpleNamespace(manifest={"index_id": name})

    def retrieve(document, text, models, k):
        assert k == 4
        case = by_text[text]
        return (
            [SearchHit(Chunk("c1", "Expected evidence", 2, "native"), 0.9)]
            if case["answerable"]
            else []
        )

    def answer(text, hits, models):
        models.last_generation_responses = [text]
        if text == "alpha question 02?":
            raise AppError("Synthetic generation failure")
        return Answer(
            "Expected evidence" if hits else "NOT FOUND",
            [2] if hits else [],
            ["c1"] if hits else [],
            not hits,
        )

    monkeypatch.setattr(pipeline, "LocalModels", SimpleNamespace)
    monkeypatch.setattr(pipeline, "ingest", ingest)
    monkeypatch.setattr(pipeline, "retrieve", retrieve)
    monkeypatch.setattr(pipeline, "answer", answer)
    monkeypatch.setattr(
        pipeline, "_cached_pages", lambda *args: ([Page(2, "Full text", "native")], None)
    )
    monkeypatch.setattr(pipeline, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(
        suite,
        "provenance",
        lambda loaded, split, models: {
            "split": split,
            "completed_at": None,
            "test_provenance": True,
        },
    )
    output = tmp_path / "run"
    records = suite.run(manifest, documents, "development", output)
    assert len(records) == 42
    assert len(indexed) == 9  # One ingestion per native document or OCR variant.
    assert sum(mode == "force" for _, mode in indexed) == 3
    failed = next(record for record in records if record["case_id"] == "alpha-02")
    assert failed["error"]["stage"] == "answer"
    assert failed["hits"] and failed["retrieval_seconds"] is not None
    assert failed["generation_seconds"] is None
    assert failed["generation_responses"] == ["alpha question 02?"]
    assert records[0]["generation_responses"] == ["alpha question 01?"]
    assert (output / "review.md").exists()
    with pytest.raises(AppError, match="already exists"):
        suite.run(manifest, documents, "development", output)
    grades = json.loads((output / "grades-template.json").read_text())
    for record in records:
        grade = grades[record["case_id"]]
        failed = record["status"] == "error"
        for fact in grade["facts"].values():
            fact.update(
                evidence_present=True, answer_correct=not failed, citation_supported=not failed
            )
        grade.update(
            unsupported_claims=False,
            failure_category="operational_error" if failed else "none",
            notes="Test fixture judgments; no model evaluation claimed.",
        )
    grade_path = output / "grades.json"
    write_json(grade_path, grades)
    result = suite.report(output, grade_path, "AI-assisted test reviewer")
    assert result["native"]["overall"]["answer_accuracy"] == {
        "count": 23,
        "denominator": 24,
        "rate": 23 / 24,
    }
    assert result["native"]["overall"]["operational_errors"] == 1
    assert result["ocr"]["overall"]["answer_accuracy"]["count"] == 6
    assert result["review"]["reviewer"] == "AI-assisted test reviewer"
    assert all((output / name).exists() for name in ("summary.json", "metrics.csv", "report.md"))
    with pytest.raises(AppError, match="Report exists"):
        suite.report(output, grade_path, "AI-assisted test reviewer")
    (output / "cases.json").write_text("[]")
    with pytest.raises(AppError, match="artifact changed"):
        suite.report(output, grade_path, "AI-assisted test reviewer")
