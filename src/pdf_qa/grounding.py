"""Validate quoted source membership, not semantic entailment or answer completeness."""

import json

from pdf_qa.types import Answer, SearchHit

GROUNDED_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "maxItems": 12,
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "minLength": 1, "maxLength": 12000},
                    "evidence": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 4,
                        "items": {
                            "type": "object",
                            "properties": {
                                "chunk_id": {"type": "string", "minLength": 1},
                                "quote": {"type": "string", "minLength": 1, "maxLength": 12000},
                            },
                            "required": ["chunk_id", "quote"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["text", "evidence"],
                "additionalProperties": False,
            },
        },
        "refused": {"type": "boolean"},
    },
    "required": ["claims", "refused"],
    "additionalProperties": False,
}


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate response field")
        value[key] = item
    return value


def _fields(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError("Unexpected response fields")


def _text(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 12000:
        raise ValueError("Invalid or excessive response text")
    return value.strip()


def parse_grounded_answer(content: str, hits: list[SearchHit]) -> Answer:
    """Check every quote in its named chunk; a matching quote can still be irrelevant."""
    if not isinstance(content, str) or len(content) > 100000:
        raise ValueError("Invalid or excessive response size")
    try:
        value = json.loads(content, object_pairs_hook=_unique_object)
    except RecursionError as exc:
        raise ValueError("Response nesting is too deep") from exc
    _fields(value, ("claims", "refused"))
    claims, refused = value["claims"], value["refused"]
    if not isinstance(claims, list) or len(claims) > 12 or type(refused) is not bool:
        raise ValueError("Invalid claims or refusal flag")
    if refused:
        if claims:
            raise ValueError("A refusal cannot contain claims")
        return Answer("NOT FOUND", [], [], True)
    if not claims:
        raise ValueError("An answer requires claims")
    lookup = {hit.chunk.id: hit.chunk for hit in hits}
    if len(lookup) != len(hits):
        raise ValueError("Ambiguous retrieved chunk IDs")
    texts, ids = [], []
    for claim in claims:
        _fields(claim, ("text", "evidence"))
        text = _text(claim["text"])
        if text == "NOT FOUND":
            raise ValueError("Use the refusal structure for NOT FOUND")
        texts.append(text)
        evidence = claim["evidence"]
        if not isinstance(evidence, list) or not 1 <= len(evidence) <= 4:
            raise ValueError("Every claim requires one to four evidence items")
        for item in evidence:
            _fields(item, ("chunk_id", "quote"))
            chunk_id = item["chunk_id"]
            if not isinstance(chunk_id, str) or chunk_id not in lookup:
                raise ValueError("Unknown evidence chunk ID")
            quote = " ".join(_text(item["quote"]).split())
            source = " ".join(lookup[chunk_id].text.split())
            if quote not in source:
                raise ValueError("Evidence quote is not present in its cited chunk")
            if chunk_id not in ids:
                ids.append(chunk_id)
    text = " ".join(texts)
    if len(text) > 12000:
        raise ValueError("Combined answer is too long")
    return Answer(text, sorted({lookup[i].page for i in ids}), ids, False)
