"""Paired development-only retrieval benchmark; does not generate or grade answers."""

import argparse
import time
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

import numpy as np

from pdf_qa import pipeline, rerank
from pdf_qa.evaluate import _now, _write_json
from pdf_qa.suite import load_suite, pages_for, provenance, selected_cases, sha
from pdf_qa.types import AppError, Settings


def summarize(records):
    groups = {}
    for group in ("native", "ocr"):
        subset = [r for r in records if (r["variant"] == "native") == (group == "native")]
        answerable = [r for r in subset if r["answerable"]]
        groups[group] = {"answerable": len(answerable), "cases": len(subset)}
        for mode in ("dense", "reranked"):
            timings = [r[mode]["seconds"] for r in subset if r[mode]["error"] is None]
            groups[group][mode] = {
                "page_hit_at_4": sum(r[mode]["page_hit"] for r in answerable),
                "errors": sum(r[mode]["error"] is not None for r in subset),
                "median_seconds": float(np.median(timings)) if timings else None,
                "p95_seconds": float(np.percentile(timings, 95)) if timings else None,
            }
        groups[group]["gains"] = [
            r["case_id"]
            for r in answerable
            if r["reranked"]["page_hit"] and not r["dense"]["page_hit"]
        ]
        groups[group]["regressions"] = [
            r["case_id"]
            for r in answerable
            if r["dense"]["page_hit"] and not r["reranked"]["page_hit"]
        ]
    return groups


def run(suite_path, corpus, output):
    output = Path(output)
    if output.exists():
        raise AppError("Output already exists; choose a new directory.")
    suite = load_suite(suite_path, corpus)
    cases = selected_cases(suite, "development", corpus)
    models = pipeline.LocalModels()
    metadata = provenance(suite, "development", models)
    metadata.update(
        evaluation_kind="retrieval-only; no answer-quality claim",
        reranker=rerank.model_identity(),
        rerank_sha256=sha(Path(rerank.__file__).read_bytes()),
        evaluator_sha256=sha(Path(__file__).read_bytes()),
        packages={
            name: version(name) for name in ("onnxruntime", "tokenizers")
        },
    )
    # Model loading is separate from per-question retrieval latency.
    tick = time.perf_counter()
    rerank._load(str(rerank.model_path()))
    metadata["reranker_load_seconds"] = time.perf_counter() - tick
    output.mkdir(parents=True)
    _write_json(output / "cases.json", cases)
    metadata["cases_sha256"] = sha((output / "cases.json").read_bytes())
    _write_json(output / "run.json", metadata)
    records, documents = [], {}
    for case in cases:
        source = Path(corpus) / case["document"]["filename"]
        if source not in documents:
            settings = Settings(ocr_mode="force" if case["variant"] == "mixed" else "auto")
            document = pipeline.ingest(source.read_bytes(), source.name, settings, models)
            documents[source] = document
            metadata.setdefault("indexes", []).append(
                {
                    "document_id": case["document_id"],
                    "variant": case["variant"],
                    "manifest": document.manifest,
                }
            )
        document = documents[source]
        record = {
            "case_id": case["case_id"],
            "variant": case["variant"],
            "document_id": case["document_id"],
            "answerable": case["answerable"],
            "expected_pages": pages_for(case),
        }
        for mode in ("dense", "reranked"):
            result = {"error": None, "hits": [], "page_hit": False}
            options = {"reranker": rerank.rerank} if mode == "reranked" else {}
            tick = time.perf_counter()
            try:
                hits = pipeline.retrieve(document, case["question"], models, **options)
                result["hits"] = [asdict(h) for h in hits]
                result["page_hit"] = bool(
                    set(record["expected_pages"]) & {h.chunk.page for h in hits}
                )
            except Exception as exc:
                result["error"] = str(exc)
            result["seconds"] = time.perf_counter() - tick
            record[mode] = result
        records.append(record)
        _write_json(output / "results.json", records)
        print(
            f"{case['case_id']}: dense={record['dense']['page_hit']} "
            f"reranked={record['reranked']['page_hit']}",
            flush=True,
        )
    metadata["completed_at"] = _now()
    metadata["results_sha256"] = sha((output / "results.json").read_bytes())
    _write_json(output / "run.json", metadata)
    summary = summarize(records)
    _write_json(output / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=Path("evals/phase2a/suite.json"))
    parser.add_argument("--corpus-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(run(args.suite, args.corpus_dir, args.output))


if __name__ == "__main__":
    main()
