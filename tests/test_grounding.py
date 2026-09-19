"""Synthetic contract checks; passing quote membership does not prove entailment."""

import json

import pytest

from pdf_qa.grounding import parse_grounded_answer
from pdf_qa.types import Answer, Chunk, SearchHit

HITS = [
    SearchHit(Chunk("p3-c1", "Juniper is a purple otter.\nThe limit is 30 psi.", 3, "native"), 0.9),
    SearchHit(Chunk("p1-c1", "The deadline is 2028.\tDo not enter.", 1, "ocr"), 0.8),
]


def response(text="The limit is 30 psi.", quote="The limit is 30 psi.", chunk_id="p3-c1"):
    return {
        "claims": [{"text": text, "evidence": [{"chunk_id": chunk_id, "quote": quote}]}],
        "refused": False,
    }


def parse(value, hits=HITS):
    return parse_grounded_answer(json.dumps(value), hits)


def test_claims_preserve_first_use_ids_sort_pages_and_normalize_only_whitespace():
    value = response(" A purple otter. ", "Juniper is a purple otter.")
    value["claims"] += response("Deadline 2028.", "The deadline is 2028.\n Do not enter.", "p1-c1")[
        "claims"
    ]
    value["claims"] += response()["claims"]
    assert parse(value) == Answer(
        "A purple otter. Deadline 2028. The limit is 30 psi.", [1, 3], ["p3-c1", "p1-c1"], False
    )
    assert parse({"claims": [], "refused": True}) == Answer("NOT FOUND", [], [], True)


@pytest.mark.parametrize(
    "quote",
    [
        "",
        "   ",
        30,
        None,
        "The limit is 31 psi.",
        "the limit is 30 psi.",
        "The limit is 30 psi!",
        "The deadline is 2028.",
    ],
)
def test_invalid_quotes_and_cross_chunk_borrowing_fail(quote):
    with pytest.raises(ValueError):
        parse(response(quote=quote))


@pytest.mark.parametrize(
    "value",
    [
        [],
        {},
        {"claims": [], "refused": False},
        {"claims": [], "refused": 1},
        {"claims": [], "refused": "true"},
        {"claims": [], "refused": True, "extra": 1},
        {"claims": [{}], "refused": True},
        {"claims": "bad", "refused": False},
        response(text=""),
        response(text="NOT FOUND"),
        response(chunk_id="missing"),
        response(chunk_id=[]),
    ],
)
def test_invalid_top_level_and_claim_values_fail(value):
    with pytest.raises(ValueError):
        parse(value)


@pytest.mark.parametrize(
    "target,key,value",
    [
        ("claim", "extra", True),
        ("claim", "text", []),
        ("claim", "evidence", []),
        ("claim", "evidence", {}),
        ("claim", "evidence", [None]),
        ("evidence", "extra", 1),
    ],
)
def test_strict_nested_fields_and_types(target, key, value):
    raw = response()
    item = raw["claims"][0]
    if target == "evidence":
        item = item["evidence"][0]
    item[key] = value
    with pytest.raises(ValueError):
        parse(raw)


def test_resource_bounds_missing_fields_duplicate_keys_and_ambiguous_ids():
    values = []
    raw = response()
    raw["claims"] *= 13
    values.append(raw)
    raw = response()
    raw["claims"][0]["evidence"] *= 5
    values.append(raw)
    raw = response(text="x" * 6001)
    raw["claims"] *= 2
    values.append(raw)
    raw = response()
    del raw["claims"][0]["evidence"][0]["quote"]
    values.append(raw)
    for value in values:
        with pytest.raises(ValueError):
            parse(value)
    for content in ["x" * 100001, '{"claims": [], "refused": false, "refused": true}', "[" * 2000]:
        with pytest.raises(ValueError):
            parse_grounded_answer(content, HITS)
    with pytest.raises(ValueError, match="Ambiguous"):
        parse(response(), HITS + HITS)


def test_matching_quote_is_not_semantic_verification():
    # Deliberate limitation: the quote is real but does not support this claim.
    value = response(text="The limit is 300 psi.", quote="Juniper is a purple otter.")
    assert parse(value).text == "The limit is 300 psi."
