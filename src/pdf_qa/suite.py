"""Versioned multi-document benchmarks, controlled PDF variants, and local runs."""

import argparse
import ast
import csv
import hashlib
import inspect
import io
import json
import platform
import re
import subprocess
import sys
import textwrap
import time
from contextlib import closing
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

import httpx
from pypdf import PdfReader, PdfWriter

from pdf_qa.evaluate import _now, _write_json
from pdf_qa.types import AppError, Settings

SPLITS = {"development", "heldout"}
CATEGORIES = {"direct", "list", "numeric", "identifier", "multi_passage", "unanswerable"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def pages_for(case):
    return sorted({e["page"] for f in case["facts"] for a in f["evidence"] for e in a})


def load_suite(path, corpus=None):
    """Validate annotations before a run; never infer answers from model output."""
    path = Path(path)
    suite = json.loads(path.read_text())
    if suite.get("schema_version") != 2 or not suite.get("name"):
        raise AppError("Unsupported suite schema; expected version 2 and a name.")
    if len(suite.get("documents", [])) != 3:
        raise AppError("Phase 2A requires three document manifests.")
    documents, cases, ids, families, question_texts = [], [], set(), {}, set()
    for name in suite["documents"]:
        if not isinstance(name, str) or Path(name).name != name or not name.endswith(".json"):
            raise AppError("Document manifests must be JSON filenames within the suite directory.")
        entry = json.loads((path.parent / name).read_text())
        if entry.get("schema_version") != 2:
            raise AppError("Document schema must be version 2.")
        doc = entry["document"]
        if (
            not re.fullmatch(r"[a-z0-9-]+", doc["id"])
            or Path(doc["filename"]).name != doc["filename"]
            or not doc["filename"].endswith(".pdf")
            or not re.fullmatch(r"[0-9a-f]{64}", doc["sha256"])
            or type(doc["pages"]) is not int
            or not 1 <= doc["pages"] <= 200
            or any(
                not isinstance(doc[k], str) or not doc[k].strip()
                for k in ("title", "edition", "url")
            )
            or any(d["id"] == doc["id"] or d["filename"] == doc["filename"] for d in documents)
        ):
            raise AppError("Invalid or duplicate document metadata.")
        reader = None
        if corpus is not None:
            source = Path(corpus) / doc["filename"]
            if sha(source.read_bytes()) != doc["sha256"]:
                raise AppError(f"Source hash mismatch for {doc['id']}.")
            reader = PdfReader(source)
            if len(reader.pages) != doc["pages"]:
                raise AppError(f"Page count mismatch for {doc['id']}.")
        counts = {(s, a): 0 for s in SPLITS for a in (True, False)}
        for q in entry["questions"]:
            if (
                not re.fullmatch(r"[a-z0-9-]+", q["id"])
                or q["id"] in ids
                or q["split"] not in SPLITS
                or type(q["answerable"]) is not bool
                or q["category"] not in CATEGORIES
                or not q["question"].strip()
                or not isinstance(q["family"], str)
                or not q["family"].strip()
            ):
                raise AppError("Invalid question or duplicate question ID.")
            text_key = normalize(q["question"]).casefold()
            if text_key in question_texts:
                raise AppError("Duplicate question text; paraphrases must also share a family.")
            question_texts.add(text_key)
            family = (doc["id"], q["family"])
            if family in families and families[family] != q["split"]:
                raise AppError(f"Question family crosses development/heldout split: {family}.")
            families[family] = q["split"]
            ids.add(q["id"])
            counts[q["split"], q["answerable"]] += 1
            if q["answerable"]:
                if not q["facts"] or q["category"] == "unanswerable":
                    raise AppError("Answerable questions need required facts and evidence.")
            elif q["facts"] or not q.get("absence_reason", "").strip():
                raise AppError("Unanswerable questions need an absence reason and no facts.")
            fact_ids = set()
            for fact in q["facts"]:
                if (
                    not fact["id"]
                    or fact["id"] in fact_ids
                    or not fact["text"].strip()
                    or not fact["evidence"]
                ):
                    raise AppError(
                        "Facts need unique IDs, expected text, and evidence alternatives."
                    )
                fact_ids.add(fact["id"])
                for alternative in fact["evidence"]:
                    if not alternative:
                        raise AppError("Evidence alternatives cannot be empty.")
                    for excerpt in alternative:
                        page = excerpt["page"]
                        if (
                            type(page) is not int
                            or not 1 <= page <= doc["pages"]
                            or not excerpt["quote"].strip()
                        ):
                            raise AppError("Evidence needs a valid physical PDF page and excerpt.")
                        if reader is not None and normalize(excerpt["quote"]) not in normalize(
                            reader.pages[page - 1].extract_text() or ""
                        ):
                            raise AppError(
                                f"Excerpt not found: {q['id']}/{fact['id']} page {page}."
                            )
            cases.append(
                {
                    **q,
                    "document_id": doc["id"],
                    "document": doc,
                    "case_id": q["id"],
                    "variant": "native",
                }
            )
        if counts != {
            ("development", True): 8,
            ("development", False): 4,
            ("heldout", True): 6,
            ("heldout", False): 2,
        }:
            raise AppError(f"Incorrect split or answerability counts for {doc['id']}.")
        first = next(q for q in cases if q["document_id"] == doc["id"])
        if first["split"] != "development" or not first["answerable"] or len(pages_for(first)) != 1:
            raise AppError("First question must be a single-page answerable development OCR case.")
        documents.append(doc)
        if reader is not None:
            reader.close()
    return {"schema_version": 2, "name": suite["name"], "documents": documents, "cases": cases}


def make_variant(source, selected_pages, mixed=False):
    """Rasterize only evidence pages; preserve all physical page numbers."""
    import pypdfium2 as pdfium
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    reader = PdfReader(io.BytesIO(source))
    writer = PdfWriter()
    with pdfium.PdfDocument(source) as rendered:
        for number, original in enumerate(reader.pages, 1):
            if number not in selected_pages:
                writer.add_page(original)
                continue
            with closing(rendered[number - 1]) as page:
                width, height = page.get_size()
                if width * height * (300 / 72) ** 2 > 40_000_000:
                    raise AppError("Variant page exceeds the OCR pixel limit.")
                with (
                    closing(page.render(scale=300 / 72)) as bitmap,
                    closing(bitmap.to_pil()) as image,
                ):
                    buffer = io.BytesIO()
                    extra = 24 if mixed else 0
                    pdf = canvas.Canvas(buffer, pagesize=(width, height + extra), invariant=1)
                    pdf.drawImage(ImageReader(image), 0, 0, width=width, height=height)
                    if mixed:
                        pdf.setFont("Helvetica", 9)
                        pdf.drawString(
                            12,
                            height + 8,
                            "Benchmark mixed page: native header with raster document text.",
                        )
                    pdf.save()
                    raster_reader = PdfReader(buffer)
                    writer.add_page(raster_reader.pages[0])
    result = io.BytesIO()
    writer.add_metadata({"/Producer": "pdf-qa phase2a raster-v1"})
    writer.write(result)
    reader.close()
    writer.close()
    return result.getvalue()


def prepare(suite_path, corpus):
    suite = load_suite(suite_path, corpus)
    corpus = Path(corpus)
    folder = corpus / "variants"
    folder.mkdir(exist_ok=True)
    manifest = {
        "recipe": "raster-v1",
        "dpi": 300,
        "tools": {
            package: version(package) for package in ("pypdf", "pypdfium2", "pillow", "reportlab")
        },
        "variants": [],
    }
    for doc in suite["documents"]:
        case = next(c for c in suite["cases"] if c["document_id"] == doc["id"])
        source = (corpus / doc["filename"]).read_bytes()
        for variant in ("scan", "mixed"):
            data = make_variant(source, pages_for(case), variant == "mixed")
            filename = f"{doc['id']}-{variant}.pdf"
            target = folder / filename
            if target.exists() and target.read_bytes() != data:
                raise AppError(f"Variant {filename} differs; use a new corpus directory.")
            if not target.exists():
                target.write_bytes(data)
            manifest["variants"].append(
                {
                    "case_id": f"{case['id']}--{variant}",
                    "question_id": case["id"],
                    "document_id": doc["id"],
                    "variant": variant,
                    "filename": f"variants/{filename}",
                    "sha256": sha(data),
                    "source_sha256": doc["sha256"],
                    "pages": doc["pages"],
                    "rasterized_pages": pages_for(case),
                    "page_mapping": "identity",
                    "ocr_mode": "auto" if variant == "scan" else "force",
                }
            )
    path = folder / "manifest.json"
    if path.exists() and json.loads(path.read_text()) != manifest:
        raise AppError("Variant manifest differs; preserve it and prepare a new corpus directory.")
    _write_json(path, manifest)
    return manifest


def selected_cases(suite, split, corpus):
    if split not in SPLITS:
        raise AppError("Select development or heldout explicitly.")
    cases = [c.copy() for c in suite["cases"] if c["split"] == split]
    if split == "development":
        variants = json.loads((Path(corpus) / "variants/manifest.json").read_text())
        expected = {(d["id"], v) for d in suite["documents"] for v in ("scan", "mixed")}
        actual = [(v["document_id"], v["variant"]) for v in variants["variants"]]
        if set(actual) != expected or len(actual) != len(expected):
            raise AppError("Expected exactly one scan and one mixed variant per document.")
        for variant in variants["variants"]:
            original = next(c for c in cases if c["id"] == variant["question_id"])
            first = next(c for c in suite["cases"] if c["document_id"] == original["document_id"])
            if (
                variant["source_sha256"] != original["document"]["sha256"]
                or variant["rasterized_pages"] != pages_for(original)
                or variant["pages"] != original["document"]["pages"]
                or variant["document_id"] != original["document_id"]
                or variant["question_id"] != first["id"]
                or variant["page_mapping"] != "identity"
                or variant["case_id"] != f"{original['id']}--{variant['variant']}"
                or variant["ocr_mode"] != ("auto" if variant["variant"] == "scan" else "force")
            ):
                raise AppError("Variant source identity or page mapping mismatch.")
            expected_name = f"variants/{original['document_id']}-{variant['variant']}.pdf"
            if variant["filename"] != expected_name:
                raise AppError("Unexpected variant filename.")
            source = Path(corpus) / expected_name
            if sha(source.read_bytes()) != variant["sha256"]:
                raise AppError("Variant hash mismatch.")
            cases.append(
                {
                    **original,
                    "variant": variant["variant"],
                    "case_id": f"{original['id']}--{variant['variant']}",
                    "document": {**original["document"], **variant},
                }
            )
    return cases


def generation_parameters(generate):
    """Read literal settings from the actual implementation, failing on drift."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(generate)))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            keywords = {k.arg: k.value for k in node.keywords}
            if {"options", "think", "keep_alive"} <= keywords.keys():
                return {
                    key: ast.literal_eval(keywords[key])
                    for key in ("options", "think", "keep_alive")
                }
    raise AppError("Generation parameters changed; update provenance before running.")


def provenance(suite, split, models):
    from pdf_qa import pipeline

    repo = Path(__file__).resolve().parents[2]

    def git(*args):
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()

    response = httpx.get("http://127.0.0.1:11434/api/version", trust_env=False, timeout=10)
    response.raise_for_status()
    return {
        "schema_version": 2,
        "suite_name": suite["name"],
        "split": split,
        "started_at": _now(),
        "completed_at": None,
        "code_revision": git("rev-parse", "HEAD"),
        "dirty_state": git("status", "--porcelain"),
        "lock_sha256": sha((repo / "uv.lock").read_bytes()),
        "pipeline_sha256": sha(Path(pipeline.__file__).read_bytes()),
        "suite_sha256": sha(json.dumps(suite, sort_keys=True).encode()),
        "prompt_sha256": sha(pipeline.SYSTEM_PROMPT.encode()),
        "prompt_version": pipeline.PROMPT_VERSION,
        "generation": generation_parameters(pipeline.LocalModels.generate),
        "generation_implementation": inspect.getsource(pipeline.LocalModels.generate),
        "query_instruction": pipeline.QUERY_INSTRUCTION,
        "settings": asdict(Settings()),
        "k": 4,
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "ollama": response.json()["version"],
            "tesseract": subprocess.check_output(
                ["tesseract", "--version"], text=True
            ).splitlines()[0],
        },
        "models": {
            name: {"name": model, "digest": models.digest(model)}
            for name, model in (
                ("answer", models.answer_model),
                ("embedding", models.embedding_model),
            )
        },
    }


def run(suite_path, corpus, split, output):
    from pdf_qa import pipeline
    from pdf_qa.evidence import grade_template, review_packet

    suite = load_suite(suite_path, corpus)
    cases = selected_cases(suite, split, corpus)
    output = Path(output)
    if output.exists():
        raise AppError("Output already exists; choose a new directory to preserve history.")
    models = pipeline.LocalModels()
    metadata = provenance(suite, split, models)
    output.mkdir(parents=True)
    _write_json(output / "cases.json", cases)
    metadata["cases_sha256"] = sha((output / "cases.json").read_bytes())
    _write_json(output / "run.json", metadata)
    _write_json(output / "grades-template.json", grade_template(cases))
    if split == "development":
        _write_json(
            output / "variants.json",
            json.loads((Path(corpus) / "variants/manifest.json").read_text()),
        )
    records, indexing = [], {}
    for case in cases:
        record = {
            "case_id": case["case_id"],
            "status": "error",
            "hits": [],
            "answer": None,
            "error": None,
            "extracted_evidence_pages": [],
            "retrieval_seconds": None,
            "generation_seconds": None,
        }
        started = time.perf_counter()
        stage = "ingest"
        try:
            source = Path(corpus) / case["document"]["filename"]
            key = str(source)
            settings = Settings(ocr_mode="force" if case["variant"] == "mixed" else "auto")
            if key not in indexing:
                tick = time.perf_counter()
                document = pipeline.ingest(source.read_bytes(), source.name, settings, models)
                indexing[key] = document
                metadata.setdefault("indexes", []).append(
                    {
                        "document_id": case["document_id"],
                        "variant": case["variant"],
                        "ingest_seconds": time.perf_counter() - tick,
                        "manifest": document.manifest,
                    }
                )
                _write_json(output / "run.json", metadata)
            document = indexing[key]
            # Read cached extraction for review only; it is never extra generation context.
            extracted, _ = pipeline._cached_pages(
                source.read_bytes(),
                settings,
                pipeline.data_dir(),
                None,
                False,
            )
            record["extracted_evidence_pages"] = [
                asdict(p) for p in extracted if p.number in pages_for(case)
            ]
            stage = "retrieve"
            tick = time.perf_counter()
            hits = pipeline.retrieve(document, case["question"], models, k=4)
            record["retrieval_seconds"] = time.perf_counter() - tick
            record["hits"] = [asdict(h) for h in hits]
            stage = "answer"
            tick = time.perf_counter()
            record["answer"] = asdict(pipeline.answer(case["question"], hits, models))
            record["generation_seconds"] = time.perf_counter() - tick
            record["status"] = "ok"
        except Exception as exc:
            record["error"] = {"stage": stage, "message": str(exc)}
        record["total_seconds"] = time.perf_counter() - started
        records.append(record)
        _write_json(output / "results.json", records)
        print(f"{case['case_id']}: {record['status']}", flush=True)
    metadata["completed_at"] = _now()
    metadata["results_sha256"] = sha((output / "results.json").read_bytes())
    _write_json(output / "run.json", metadata)
    (output / "review.md").write_text(review_packet(cases, records))
    return records


def report(results, grades, reviewer):
    from pdf_qa.evidence import summarize

    root = Path(results)
    metadata = json.loads((root / "run.json").read_text())
    if not metadata.get("completed_at"):
        raise AppError("Cannot report an incomplete run.")
    for filename, key in (("cases.json", "cases_sha256"), ("results.json", "results_sha256")):
        if sha((root / filename).read_bytes()) != metadata[key]:
            raise AppError(f"Run artifact changed: {filename}.")
    cases = json.loads((root / "cases.json").read_text())
    if any(c["split"] != metadata["split"] for c in cases):
        raise AppError("Run contains questions from an unrequested split.")
    records = json.loads((root / "results.json").read_text())
    grade_bytes = Path(grades).read_bytes()
    summary = summarize(cases, records, json.loads(grade_bytes))
    if not reviewer.strip():
        raise AppError("Explicit reviewer attribution is required.")
    summary["review"] = {
        "reviewer": reviewer,
        "grades_sha256": sha(grade_bytes),
        "reviewed_at": _now(),
    }
    names = ("summary.json", "metrics.csv", "report.md")
    if any((root / name).exists() for name in names):
        raise AppError("Report exists; preserve it and use a new review directory.")
    rows = []
    groups = {
        "native-overall": summary["native"]["overall"],
        **{f"native-{k}": v for k, v in summary["native"]["by_document"].items()},
        "ocr-overall": summary["ocr"]["overall"],
        **{f"ocr-{k}": v for k, v in summary["ocr"]["by_variant"].items()},
    }
    lines = [
        "# Evidence evaluation report",
        "",
        f"Reviewer: {reviewer}",
        "",
        f"Split: {metadata['split']}. OCR pairs are not independent questions.",
        "",
        "| Group | Metric | Count | Denominator | Rate |",
        "|---|---|---:|---:|---:|",
    ]
    for group, metrics in groups.items():
        for name, value in metrics.items():
            if isinstance(value, dict) and {"count", "denominator", "rate"} <= value.keys():
                rows.append({"group": group, "metric": name, **value})
                rate = "N/A" if value["rate"] is None else f"{value['rate']:.3f}"
                lines.append(
                    f"| {group} | {name} | {value['count']} | {value['denominator']} | {rate} |"
                )
    lines += ["", "## Failures", ""]
    for failure in summary["failures"]:
        lines.append(f"- {failure['case_id']}: {failure['category']}. {failure['notes']}")
    lines += [
        "",
        "Latency and operational error counts are in summary.json; indexing is in "
        "run.json and excluded from query latency. Only the explicitly selected split "
        "is included in this report.",
    ]
    _write_json(root / "summary.json", summary)
    with (root / "metrics.csv").open("x", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["group", "metric", "count", "denominator", "rate"]
        )
        writer.writeheader()
        writer.writerows(rows)
    (root / "report.md").write_text("\n".join(lines) + "\n")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "prepare", "run"):
        command = commands.add_parser(name)
        command.add_argument("--suite", type=Path, default=Path("evals/phase2a/suite.json"))
        command.add_argument("--corpus-dir", type=Path, required=True)
        if name == "run":
            command.add_argument("--split", choices=sorted(SPLITS), required=True)
            command.add_argument("--output", type=Path, required=True)
    command = commands.add_parser("report")
    command.add_argument("--results", type=Path, required=True)
    command.add_argument("--grades", type=Path, required=True)
    command.add_argument("--reviewer", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            suite = load_suite(args.suite, args.corpus_dir)
            print(
                f"Validated {len(suite['documents'])} documents, {len(suite['cases'])} questions."
            )
        elif args.command == "prepare":
            print(json.dumps(prepare(args.suite, args.corpus_dir), indent=2))
        elif args.command == "run":
            run(args.suite, args.corpus_dir, args.split, args.output)
        else:
            report(args.results, args.grades, args.reviewer)
    except (AppError, OSError, ValueError, KeyError, TypeError, StopIteration) as exc:
        print(f"Suite failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
