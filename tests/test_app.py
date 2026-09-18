"""Exercise document isolation and recovery without accessing local models."""

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from pdf_qa import pipeline
from pdf_qa.types import Answer, AppError, Chunk, SearchHit

APP = Path(__file__).resolve().parents[1] / "app.py"


def click(app, label):
    return next(button for button in app.button if button.label == label).click().run()


@pytest.fixture
def ui(tmp_path):
    st.cache_resource.clear()
    documents = []
    for name in ("first", "second"):
        path = tmp_path / name
        path.mkdir()
        (path / "manifest.json").write_text("{}")
        manifest = {
            "path": str(path),
            "filename": f"{name}.pdf",
            "index_id": name,
            "page_count": 2,
            "chunk_count": 5,
            "settings": {"chunk_size": 800, "overlap": 60, "ocr_mode": "auto"},
            "warnings": [],
        }
        documents.append(SimpleNamespace(path=path, manifest=manifest))
    hit = SearchHit(Chunk("p2-c1", "Document evidence.", 2, "native"), 0.9)
    result = Answer("Supported answer.", [2], ["p2-c1"], False)
    with (
        patch.object(pipeline, "LocalModels") as models,
        patch.object(
            pipeline, "list_indexes", return_value=[d.manifest for d in documents]
        ) as listing,
        patch.object(
            pipeline, "load_index", side_effect=lambda p: next(d for d in documents if d.path == p)
        ) as load,
        patch.object(pipeline, "ingest", return_value=documents[0]) as ingest,
        patch.object(pipeline, "retrieve", return_value=[hit]) as retrieve,
        patch.object(pipeline, "answer", return_value=result) as answer,
        patch.object(st, "file_uploader", return_value=None) as upload,
    ):
        yield SimpleNamespace(
            app=AppTest.from_file(str(APP)),
            documents=documents,
            models=models,
            listing=listing,
            load=load,
            ingest=ingest,
            retrieve=retrieve,
            answer=answer,
            upload=upload,
        )
    st.cache_resource.clear()


def load_saved(ui):
    app = ui.app.run()
    app.radio(key="source").set_value("Saved index").run()
    click(app, "Load index")
    assert not app.exception
    return app


def ask(app):
    app.text_input(key="question").set_value("What does the PDF say?")
    click(app, "Find answer")
    assert not app.exception


def test_saved_index_answer_and_document_switch(ui):
    app = ui.app.run()
    assert app.text_input(key="question").disabled
    app = load_saved(ui)
    ask(app)
    assert "Supported answer." in [element.value for element in app.text]
    assert any("Source PDF pages: 2" in element.value for element in app.caption)
    assert any("score 0.9000" in element.value for element in app.markdown)
    assert ui.load.call_count == 1
    app.selectbox(key="saved_path").set_value(str(ui.documents[1].path)).run()
    assert app.text_input(key="question").disabled
    assert "last_answer" not in app.session_state
    click(app, "Load index")
    assert app.subheader[0].value == "second.pdf"
    assert "last_hits" not in app.session_state
    assert not app.exception


def test_upload_settings_and_bytes_clear_document(ui):
    uploaded = BytesIO(b"first pdf")
    uploaded.name = "first.pdf"
    ui.upload.return_value = uploaded
    app = ui.app.run()
    click(app, "Build index")
    ask(app)
    app.select_slider(key="chunk_size").set_value(300).run()
    assert app.text_input(key="question").disabled
    assert "last_answer" not in app.session_state
    click(app, "Rebuild index")
    assert ui.ingest.call_args.kwargs["rebuild"] is True
    assert ui.ingest.call_args.args[2].chunk_size == 300
    app.selectbox(key="extraction").set_value("Force OCR for all pages").run()
    assert app.text_input(key="question").disabled
    click(app, "Build index")
    assert ui.ingest.call_args.args[2].ocr_mode == "force"
    ui.upload.return_value = BytesIO(b"different pdf")
    ui.upload.return_value.name = "different.pdf"
    app.run()
    assert app.text_input(key="question").disabled
    assert not app.exception


def test_generation_error_clears_previous_answer_but_keeps_evidence(ui):
    app = load_saved(ui)
    ask(app)
    ui.answer.side_effect = AppError("Ollama is unavailable.")
    ask(app)
    assert app.error[0].value == "Ollama is unavailable."
    assert "last_answer" not in app.session_state
    assert "Document evidence." in [element.value for element in app.text]
    assert "NOT FOUND" not in [element.value for element in app.text]
    ui.answer.side_effect = None
    ui.answer.return_value = Answer("NOT FOUND", [], [], True)
    ask(app)
    assert "NOT FOUND" in [element.value for element in app.text]


def test_corrupt_saved_index_explains_rebuild(ui):
    ui.listing.return_value = [
        {
            "path": str(ui.documents[0].path),
            "filename": "first.pdf",
            "index_id": "first",
            "error": "Index checksum mismatch.",
        }
    ]
    app = ui.app.run()
    app.radio(key="source").set_value("Saved index").run()
    assert app.error[0].value == "Index checksum mismatch."
    assert next(button for button in app.button if button.label == "Load index").disabled
    assert any("Upload the original PDF" in element.value for element in app.info)
    assert not app.exception


def test_source_switch_and_failed_build_clear_saved_document(ui):
    app = load_saved(ui)
    ask(app)
    app.radio(key="source").set_value("Upload PDF").run()
    assert app.text_input(key="question").disabled
    assert "last_answer" not in app.session_state
    uploaded = BytesIO(b"damaged pdf")
    uploaded.name = "damaged.pdf"
    ui.upload.return_value = uploaded
    ui.ingest.side_effect = AppError("This PDF is damaged.")
    app.run()
    click(app, "Build index")
    assert app.error[0].value == "This PDF is damaged."
    assert app.text_input(key="question").disabled
    assert not app.exception


def test_saved_index_loads_after_session_restart_and_refreshes_after_rebuild(ui):
    load_saved(ui)
    assert ui.load.call_count == 1
    ui.app = AppTest.from_file(str(APP))
    load_saved(ui)
    assert ui.load.call_count == 1
    (ui.documents[0].path / "manifest.json").write_text('{"rebuilt": true}')
    click(ui.app, "Load index")
    assert ui.load.call_count == 2
    assert not ui.app.exception
