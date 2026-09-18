import io
import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest
from reportlab.pdfgen import canvas

from pdf_qa.pipeline import (
    LocalModels,
    answer,
    ingest,
    list_indexes,
    load_index,
    parse_answer,
    retrieve,
)
from pdf_qa.types import AppError, Chunk, SearchHit, Settings


class FakeModels:
    embedding_model = "test-local"

    def __init__(self):
        self.revision = "fixed-digest"
        self.calls = []

    def digest(self, model):
        return self.revision

    def embed(self, texts, query=False):
        self.calls.append((texts, query))
        return np.array(
            [
                [1 + text.lower().count("ladder"), 1 + text.lower().count("fire"), 1]
                for text in texts
            ],
            dtype="float32",
        )


def pdf_bytes(text="Ladder safety requires checking every rung before climbing."):
    buffer = io.BytesIO()
    writer = canvas.Canvas(buffer)
    writer.drawString(50, 750, text)
    writer.save()
    return buffer.getvalue()


def test_persist_reload_and_queries_never_reembed_document(tmp_path):
    models = FakeModels()
    pdf = pdf_bytes()
    document = ingest(pdf, "test.pdf", Settings(), models, tmp_path)
    assert len(models.calls) == 1
    reloaded = ingest(pdf, "renamed.pdf", Settings(), models, tmp_path)
    assert len(models.calls) == 1
    assert reloaded.path == document.path
    reloaded = load_index(document.path)
    hits = retrieve(reloaded, "What is ladder safety?", models)
    assert len(hits) == 1 and hits[0].chunk.page == 1
    assert -1 <= hits[0].score <= 1.00001
    assert models.calls[-1][1] is True
    assert list_indexes(tmp_path)[0]["filename"] == "test.pdf"


def test_settings_and_embedding_digest_invalidate_cache(tmp_path):
    models = FakeModels()
    pdf = pdf_bytes()
    original = ingest(pdf, "test.pdf", Settings(), models, tmp_path)
    changed = ingest(pdf, "test.pdf", Settings(chunk_size=300), models, tmp_path)
    assert changed.path != original.path
    models.revision = "new-digest"
    with pytest.raises(AppError, match="Embedding model changed"):
        retrieve(original, "ladder?", models)
    rebuilt = ingest(pdf, "test.pdf", Settings(), models, tmp_path)
    assert rebuilt.path != original.path


def test_corruption_is_reported_and_explicit_rebuild_preserves_old_files(tmp_path):
    models = FakeModels()
    pdf = pdf_bytes()
    document = ingest(pdf, "test.pdf", Settings(), models, tmp_path)
    (document.path / "index.faiss").write_bytes(b"corrupt")
    with pytest.raises(AppError, match="damaged"):
        load_index(document.path)
    assert "error" in list_indexes(tmp_path)[0]
    with pytest.raises(AppError):
        ingest(pdf, "test.pdf", Settings(), models, tmp_path)
    fixed = ingest(pdf, "test.pdf", Settings(), models, tmp_path, rebuild=True)
    assert fixed.index.ntotal == 1
    assert len(list((tmp_path / "retired").iterdir())) == 1


def test_document_identity_and_no_cross_document_retrieval(tmp_path):
    models = FakeModels()
    first = ingest(pdf_bytes(), "same.pdf", Settings(), models, tmp_path)
    second = ingest(
        pdf_bytes("Fire extinguishers must be inspected monthly and maintained annually."),
        "same.pdf",
        Settings(),
        models,
        tmp_path,
    )
    assert first.path != second.path
    hits = retrieve(second, "ladder?", models)
    assert all("Ladder" not in h.chunk.text for h in hits)


def test_invalid_input_fails_without_embedding(tmp_path):
    models = FakeModels()
    with pytest.raises(AppError, match="PDF"):
        ingest(b"not a pdf", "bad.pdf", Settings(), models, tmp_path)
    assert not models.calls


def test_citation_validation_and_refusal_are_distinct():
    hits = [SearchHit(Chunk("p3-c1", "A ladder extends three feet.", 3, "native"), 0.8)]
    good = json.dumps({"answer": "Three feet.", "chunk_ids": ["p3-c1"], "refused": False})
    result = parse_answer(good, hits)
    assert result.citations == [3] and not result.refused
    for invalid in [
        {"answer": "Three feet.", "chunk_ids": ["p99-c1"], "refused": False},
        {"answer": "Three feet.", "chunk_ids": [], "refused": False},
        {"answer": "NOT FOUND", "chunk_ids": [], "refused": "true"},
        {"answer": "NOT FOUND", "chunk_ids": ["p3-c1"], "refused": True},
    ]:
        with pytest.raises(ValueError):
            parse_answer(json.dumps(invalid), hits)
    assert parse_answer(
        '{"answer":"NOT FOUND","chunk_ids":[],"refused":true}',
        hits,
    ).refused


def test_model_repairs_once_then_reports_generation_failure():
    models = LocalModels()
    models.digest = Mock(return_value="digest")
    models.client = Mock()
    models.client.chat.return_value = SimpleNamespace(message=SimpleNamespace(content="invalid"))
    hits = [SearchHit(Chunk("p1-c1", "Text", 1, "native"), 1.0)]
    with pytest.raises(AppError, match="invalid answer twice"):
        answer("question", hits, models)
    assert models.client.chat.call_count == 2
    assert models.client.chat.call_args.kwargs["think"] is False
    assert models.client.chat.call_args.kwargs["options"]["temperature"] == 0
    assert answer("question", [], models).refused


def test_invalid_vectors_and_dimension_changes(tmp_path):
    models = FakeModels()
    document = ingest(pdf_bytes(), "test.pdf", Settings(), models, tmp_path)
    models.embed = Mock(return_value=[[0, 0, 0]])
    with pytest.raises(AppError, match="invalid vectors"):
        retrieve(document, "ladder?", models)
    models.embed = Mock(return_value=[[1, 1]])
    with pytest.raises(AppError, match="dimensions changed"):
        retrieve(document, "ladder?", models)
    with pytest.raises(AppError, match="question"):
        retrieve(document, " ", models)


@pytest.mark.integration
def test_real_local_model_answers_and_reloads(tmp_path):
    models = LocalModels()
    document = ingest(
        pdf_bytes("The project mascot is a purple otter named Juniper."),
        "local-test.pdf",
        Settings(),
        models,
        tmp_path,
    )
    document = load_index(document.path)
    hits = retrieve(document, "What is the mascot's name?", models)
    result = answer("What is the mascot's name?", hits, models)
    assert not result.refused and "Juniper" in result.text and result.citations == [1]
    missing = answer("What is the mascot's exact birth date?", hits, models)
    assert missing.refused and missing.text == "NOT FOUND"


def test_settings_validation():
    with pytest.raises(AppError):
        replace(Settings(), chunk_size=0)
    with pytest.raises(AppError):
        Settings(ocr_mode="cloud")
