"""Small-document lexical ranking and reciprocal rank fusion; no persistent index."""

import math
import re
from collections import Counter

HYBRID_CONFIG = {
    "version": "hybrid-v1",
    "method": "hybrid",
    "score": "rrf",
    "dense_candidates": 20,
    "lexical_candidates": 20,
    "rrf_k": 60,
    "bm25_k1": 1.2,
    "bm25_b": 0.75,
    "tokenizer": "alphanumeric-casefold-stopwords-v1",
}
STOPWORDS = frozenset(
    "a an and are as at be been by can do does for from how i in is it its of on or "
    "that the their this to was were what when where which who why will with you your".split()
)


def tokens(text):
    return [word for word in re.findall(r"[^\W_]+", text.casefold()) if word not in STOPWORDS]


def lexical_rank(chunks, question):
    """Return positions with positive BM25 scores; ties use document chunk order."""
    terms = sorted(set(tokens(question)))
    if not chunks or not terms:
        return []
    # ponytail: recompute for the 200-page limit; cache per loaded index if profiling warrants it.
    frequencies = [Counter(tokens(chunk.text)) for chunk in chunks]
    lengths = [sum(freq.values()) for freq in frequencies]
    average = sum(lengths) / len(chunks)
    if not average:
        return []
    counts = {term: sum(term in freq for freq in frequencies) for term in terms}
    k1, b = HYBRID_CONFIG["bm25_k1"], HYBRID_CONFIG["bm25_b"]
    scores = []
    for position, (freq, length) in enumerate(zip(frequencies, lengths, strict=True)):
        score = 0.0
        for term in terms:
            tf = freq[term]
            if tf:
                idf = math.log1p((len(chunks) - counts[term] + 0.5) / (counts[term] + 0.5))
                score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * length / average))
        if score > 0:
            scores.append((position, score))
    return [position for position, _ in sorted(scores, key=lambda item: (-item[1], item[0]))]


def hybrid_rank(chunks, question, dense_positions, k):
    """Fuse top-20 lists; scores are rank-fusion values, never cosine/confidence."""
    dense = list(dense_positions)[: HYBRID_CONFIG["dense_candidates"]]
    lexical = lexical_rank(chunks, question)[: HYBRID_CONFIG["lexical_candidates"]]
    scores = Counter()
    for ranking in (dense, lexical):
        for rank, position in enumerate(ranking, 1):
            scores[position] += 1 / (HYBRID_CONFIG["rrf_k"] + rank)
    dense_rank = {position: rank for rank, position in enumerate(dense)}
    selected = sorted(scores, key=lambda p: (-scores[p], dense_rank.get(p, len(chunks)), p))
    return [(position, scores[position]) for position in selected[:k]]
