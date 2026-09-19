import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
import pytest

from pdf_qa import pipeline, rerank
from pdf_qa.types import AppError, Chunk, SearchHit


def hits(n=5):
    return [
        SearchHit(Chunk(f"p{i + 1}-c1", f"Passage {i}", i + 1, "native"), 0.9) for i in range(n)
    ]


def test_order_ties_and_preserved_chunks():
    original = hits()
    with patch.object(rerank, "_scores", return_value=[-3, 8, 8, 0, 9]) as score:
        result = rerank.rerank(" question ", original)
    assert [h.chunk for h in result] == [original[i].chunk for i in (4, 1, 2, 3)]
    assert [h.score for h in result] == [9, 8, 8, 0]
    assert all(h.score == 0.9 for h in original)
    score.assert_called_once_with("question", original)


@pytest.mark.parametrize("scores", [[float("nan")], [float("inf")], [], [[1]], [1, 2]])
def test_invalid_scores_fail_visibly(scores):
    with patch.object(rerank, "_scores", return_value=scores):
        with pytest.raises(AppError, match="invalid scores"):
            rerank.rerank("question", hits(1))


def test_small_empty_and_invalid_inputs():
    with patch.object(rerank, "_scores", return_value=[2]):
        assert len(rerank.rerank("question", hits(1))) == 1
    with patch.object(rerank, "_load") as load:
        assert rerank.rerank("question", []) == []
        for question, candidates, k in [
            ("", hits(), 4),
            ("x" * 2001, hits(), 4),
            ("q", hits(), 0),
            ("q", hits(21), 4),
        ]:
            with pytest.raises(AppError):
                rerank.rerank(question, candidates, k)
        load.assert_not_called()


def test_missing_local_configuration(monkeypatch, tmp_path):
    monkeypatch.delenv("PDF_QA_RERANKER_DIR", raising=False)
    with pytest.raises(AppError, match="PDF_QA_RERANKER_DIR"):
        rerank.model_path()
    monkeypatch.setenv("PDF_QA_RERANKER_DIR", str(tmp_path))
    with pytest.raises(AppError, match="files are missing"):
        rerank.model_path()


def test_model_failures_become_actionable_errors(tmp_path):
    rerank._load.cache_clear()
    with patch.dict("sys.modules", {"onnxruntime": None}):
        with pytest.raises(AppError, match="uv sync --extra rerank"):
            rerank._load(str(tmp_path))
    with patch.object(rerank, "_scores", side_effect=RuntimeError("failed")):
        with pytest.raises(AppError, match="Local reranking failed"):
            rerank.rerank("question", hits())


def test_load_is_local_safe_and_cached(tmp_path):
    ort, tokenizer = Mock(), Mock()
    rerank._load.cache_clear()
    with patch.dict(
        "sys.modules",
        {
            "onnxruntime": ort,
            "tokenizers": SimpleNamespace(Tokenizer=tokenizer),
        },
    ):
        rerank._load(str(tmp_path))
        rerank._load(str(tmp_path))
    ort.InferenceSession.assert_called_once_with(
        str(tmp_path / "onnx/model.onnx"),
        providers=["CPUExecutionProvider"],
    )
    ort.disable_telemetry_events.assert_called_once()
    tokenizer.from_file.assert_called_once_with(str(tmp_path / "tokenizer.json"))
    tokenizer.from_file.return_value.enable_truncation.assert_called_once_with(max_length=512)
    tokenizer.from_file.return_value.enable_padding.assert_called_once_with(
        pad_id=0, pad_token="[PAD]"
    )
    rerank._load.cache_clear()


def test_retrieval_requests_twenty_from_selected_document(tmp_path):
    models = Mock(embedding_model="local")
    models.digest.return_value = "digest"
    models.embed.return_value = [[1, 0]]
    index = Mock(d=2)
    index.search.return_value = (np.ones((1, 20)), np.arange(20).reshape(1, 20))
    chunks = [h.chunk for h in hits(25)]
    document = pipeline.DocumentIndex(
        tmp_path,
        {"embedding_model": "local", "embedding_digest": "digest"},
        chunks,
        index,
    )
    rank = Mock(side_effect=lambda question, candidates, k: candidates[-k:])
    result = pipeline.retrieve(document, "question", models, reranker=rank)
    assert index.search.call_args.args[1] == 20
    assert len(rank.call_args.args[1]) == 20
    assert [h.chunk for h in result] == chunks[16:20]
    models.embed.assert_called_once_with(["question"], query=True)


@pytest.mark.integration
def test_real_local_reranker():
    if not os.environ.get("PDF_QA_RERANKER_DIR"):
        pytest.skip("Optional local reranker is not configured.")
    candidates = [
        SearchHit(Chunk("p1-c1", "The cat sleeps on the sofa.", 1, "native"), 0.99),
        SearchHit(Chunk("p2-c1", "Paris is the capital of France.", 2, "native"), 0.8),
    ]
    rerank._load.cache_clear()
    with patch("socket.socket.connect", side_effect=AssertionError("Network forbidden")):
        result = rerank.rerank("What is the capital of France?", candidates)
    assert result[0].chunk.id == "p2-c1"
    assert result[0].score > result[1].score


def test_question_passage_pairs_and_onnx_tensor_mapping(tmp_path):
    tokenizer, session = Mock(), Mock()
    tokenizer.encode_batch.return_value = [
        SimpleNamespace(ids=[101, 7, 102, 9, 102], attention_mask=[1] * 5, type_ids=[0, 0, 0, 1, 1])
    ]
    session.run.return_value = [np.array([[3.5]])]
    candidates = hits(1)
    with (
        patch.object(rerank, "model_path", return_value=tmp_path),
        patch.object(rerank, "_load", return_value=(tokenizer, session)),
    ):
        assert rerank.rerank("question", candidates)[0].score == 3.5
        session.run.return_value = [np.array([[3.5, 7.0]])]
        with pytest.raises(AppError, match="invalid scores"):
            rerank.rerank("question", candidates)
    assert all(
        call.args == ([("question", "Passage 0")],)
        for call in tokenizer.encode_batch.call_args_list
    )
    assert session.run.call_args.args[0] == ["logits"]
    tensors = session.run.call_args.args[1]
    assert tensors["input_ids"].tolist() == [[101, 7, 102, 9, 102]]
    assert tensors["token_type_ids"].tolist() == [[0, 0, 0, 1, 1]]
    assert all(t.dtype == np.int64 for t in tensors.values())


def test_retrieval_summary_separates_ocr_errors_and_unanswerable():
    from pdf_qa.rerank_eval import summarize

    def record(case_id, variant, answerable, dense, reranked, error=None):
        return {
            "case_id": case_id,
            "variant": variant,
            "answerable": answerable,
            "dense": {"page_hit": dense, "seconds": 0.1, "error": None},
            "reranked": {"page_hit": reranked, "seconds": 0.3, "error": error},
        }

    result = summarize(
        [
            record("gain", "native", True, False, True),
            record("loss", "native", True, True, False, "model failed"),
            record("absent", "native", False, False, False),
            record("ocr", "scan", True, True, True),
        ]
    )
    assert result["native"]["answerable"] == 2
    assert result["native"]["dense"]["page_hit_at_4"] == 1
    assert result["native"]["reranked"]["errors"] == 1
    assert result["native"]["gains"] == ["gain"]
    assert result["native"]["regressions"] == ["loss"]
    assert result["ocr"]["answerable"] == 1


@pytest.mark.integration
def test_real_reranked_pipeline_keeps_saved_documents_separate(tmp_path):
    if not os.environ.get("PDF_QA_RERANKER_DIR"):
        pytest.skip("Optional local reranker is not configured.")
    from io import BytesIO

    from reportlab.pdfgen import canvas

    from pdf_qa.types import Settings

    models = pipeline.LocalModels()
    documents = []
    for name in ("Juniper", "Pebble"):
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer)
        pdf.drawString(40, 750, f"The project mascot is a purple otter named {name}.")
        pdf.save()
        document = pipeline.ingest(buffer.getvalue(), f"{name}.pdf", Settings(), models, tmp_path)
        documents.append(pipeline.load_index(document.path))
    assert documents[0].path != documents[1].path
    assert len(pipeline.list_indexes(tmp_path)) == 2
    for document, name, other in zip(
        documents, ("Juniper", "Pebble"), ("Pebble", "Juniper"), strict=True
    ):
        question = "What is the project mascot's name?"
        evidence = pipeline.retrieve(document, question, models, reranker=rerank.rerank)
        assert evidence and all(
            name in h.chunk.text and other not in h.chunk.text for h in evidence
        )
        answer = pipeline.answer(question, evidence, models)
        assert not answer.refused and name in answer.text and other not in answer.text
        assert answer.citations == [1]
