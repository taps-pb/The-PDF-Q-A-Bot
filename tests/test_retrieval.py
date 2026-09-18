"""Deterministic lexical/fusion behavior, including dense fallback and persisted indexes."""

from unittest.mock import Mock

import numpy as np

from pdf_qa.pipeline import DocumentIndex, retrieve
from pdf_qa.retrieval import hybrid_rank, lexical_rank, tokens
from pdf_qa.types import Chunk


def chunks(*texts):
    return [Chunk(f"p1-c{i + 1}", text, 1, "native") for i, text in enumerate(texts)]


def test_tokens_identifiers_numbers_and_stopwords():
    assert tokens("What is PR.DS-11, by 2028?") == ["pr", "ds", "11", "2028"]
    assert tokens("NOT without safety") == ["not", "without", "safety"]


def test_bm25_prefers_relevant_short_passage_and_ignores_query_repetition():
    source = chunks(
        "general manual " * 30, "The violet mascot is Juniper.", "Juniper " + "other " * 30
    )
    assert lexical_rank(source, "What is the violet mascot?")[0] == 1
    assert lexical_rank(source, "Juniper Juniper") == lexical_rank(source, "Juniper")
    assert lexical_rank(source, "unmatched") == []
    assert lexical_rank(chunks("the and", ""), "mascot") == []
    assert lexical_rank([], "mascot") == []


def test_fusion_can_recover_lexical_evidence_and_break_ties_deterministically():
    source = chunks("irrelevant", "Juniper mascot", "Juniper mascot")
    result = hybrid_rank(source, "Juniper", [0, 2, 1], 3)
    assert [p for p, _ in result] == [1, 2, 0]
    assert result == hybrid_rank(source, "Juniper", [0, 2, 1], 3)
    assert result[0][1] == 1 / 61 + 1 / 63
    tied = hybrid_rank(source, "Juniper", [2, 1, 0], 3)
    assert [p for p, _ in tied] == [2, 1, 0]
    assert tied[0][1] == tied[1][1]


def test_lexical_zero_matches_preserves_dense_order_and_limits():
    source = chunks("apple", "pear", "plum")
    assert [p for p, _ in hybrid_rank(source, "???", [2, 0, 1], 2)] == [2, 0]
    assert [p for p, _ in hybrid_rank(source, "unknown", [2, 0, 1], 20)] == [2, 0, 1]
    assert hybrid_rank([], "hello", [], 4) == []


def test_pipeline_searches_broader_pool_without_reembedding_document(tmp_path):
    source = chunks(*[f"ordinary passage {i}" for i in range(24)], "rare violet mascot")
    index = Mock(d=2)
    index.search.return_value = (np.zeros((1, 20)), np.array([list(range(20))]))
    models = Mock(embedding_model="local")
    models.digest.return_value = "digest"
    models.embed.return_value = [[1.0, 0.0]]
    document = DocumentIndex(
        tmp_path, {"embedding_model": "local", "embedding_digest": "digest"}, source, index
    )
    hits = retrieve(document, "rare violet mascot", models)
    assert index.search.call_args.args[1] == 20
    assert len(hits) == 4 and hits[1].chunk == source[24]
    assert all(0 < hit.score < 1 for hit in hits)
    models.embed.assert_called_once_with(["rare violet mascot"], query=True)
