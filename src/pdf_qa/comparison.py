"""Compare fully reviewed development runs with unchanged retrieval and runtime settings."""

import argparse
import json
import math
import sys
from pathlib import Path

from pdf_qa.evidence import _validate, summarize
from pdf_qa.suite import sha
from pdf_qa.types import AppError

MATCHED_METADATA = (
    "schema_version",
    "suite_name",
    "suite_sha256",
    "settings",
    "k",
    "models",
    "lock_sha256",
    "runtime",
    "generation",
    "query_instruction",
)


def _load(directory):
    directory = Path(directory)
    artifacts = {
        name: (directory / f"{name}.json").read_bytes()
        for name in ("run", "cases", "results", "grades", "summary")
    }
    loaded = {name: json.loads(data) for name, data in artifacts.items()}
    metadata, cases, grades = loaded["run"], loaded["cases"], loaded["grades"]
    if metadata.get("split") != "development" or not metadata.get("completed_at"):
        raise AppError("Comparison requires completed development runs only.")
    if not cases or any(case["split"] != "development" for case in cases):
        raise AppError("Comparison cannot include held-out or empty case sets.")
    for name in ("cases", "results"):
        if sha(artifacts[name]) != metadata.get(f"{name}_sha256"):
            raise AppError(f"Run artifact changed: {directory}/{name}.json.")
    review = loaded["summary"].get("review", {})
    if (
        not isinstance(review.get("reviewer"), str)
        or not review["reviewer"].strip()
        or sha(artifacts["grades"]) != review.get("grades_sha256")
    ):
        raise AppError("Grading hash or reviewer attribution is missing or changed.")
    summary = summarize(cases, loaded["results"], grades)
    if {key: value for key, value in loaded["summary"].items() if key != "review"} != summary:
        raise AppError("Saved summary does not match the revalidated grades and results.")
    loaded["hashes"] = {name: sha(data) for name, data in artifacts.items()}
    loaded["summary"] = summary
    return loaded


def _delta(before, after):
    if isinstance(before, dict):
        if set(before) != set(after):
            raise AppError("Metric groups differ between runs.")
        return {key: _delta(before[key], after[key]) for key in before}
    return after - before if before is not None and after is not None else None


def _change(before, after):
    return {"before": before, "after": after, "delta": _delta(before, after)}


def _outcome(case, record, grade):
    validated = _validate(case, record, grade)
    if record["status"] == "error":
        return "operational_error"
    if validated["refused"]:
        return "false_refusal" if case["answerable"] else "correct_refusal"
    return "correct_answer" if case["answerable"] and validated["correct"] else "incorrect_answer"


def compare(baseline, candidate, output):
    """Write an immutable JSON comparison; legacy regression approval stays separate."""
    output = Path(output)
    if output.exists():
        raise AppError("Comparison output already exists; choose a new path.")
    before, after = _load(baseline), _load(candidate)
    for key in MATCHED_METADATA:
        if key not in before["run"] or key not in after["run"]:
            raise AppError(f"Missing comparison provenance: {key}.")
        if before["run"][key] != after["run"][key]:
            raise AppError(f"Generation-only comparison requires matching {key}.")
    if before["cases"] != after["cases"]:
        raise AppError("Generation-only comparison requires exactly the same frozen cases.")
    records = [{record["case_id"]: record for record in run["results"]} for run in (before, after)]
    case_changes, scores_changed_cases = [], []
    max_absolute_score_delta = 0.0
    for case in before["cases"]:
        case_id = case["case_id"]
        first, second = records[0][case_id], records[1][case_id]
        if [hit["chunk"] for hit in first["hits"]] != [hit["chunk"] for hit in second["hits"]]:
            raise AppError(f"{case_id}: ranked retrieved chunks changed.")
        # Generation receives ranked chunks, never retrieval scores. Record numeric drift.
        deltas = []
        for old_hit, new_hit in zip(first["hits"], second["hits"], strict=True):
            scores = (old_hit["score"], new_hit["score"])
            if any(type(score) not in (int, float) or not math.isfinite(score) for score in scores):
                raise AppError(f"{case_id}: retrieval scores must be finite numbers.")
            deltas.append(abs(scores[1] - scores[0]))
        if any(deltas):
            scores_changed_cases.append(case_id)
            max_absolute_score_delta = max(max_absolute_score_delta, *deltas)
        grades = [run["grades"][case_id] for run in (before, after)]
        evidence = [
            {key: fact["evidence_present"] for key, fact in grade["facts"].items()}
            for grade in grades
        ]
        if evidence[0] != evidence[1]:
            raise AppError(f"{case_id}: evidence judgments changed despite identical retrieval.")
        case_changes.append(
            {
                "case_id": case_id,
                "document_id": case["document_id"],
                "variant": case["variant"],
                "outcome": {
                    "before": _outcome(case, first, grades[0]),
                    "after": _outcome(case, second, grades[1]),
                },
                "failure": {
                    "before": grades[0]["failure_category"],
                    "after": grades[1]["failure_category"],
                },
                "latency_seconds": {
                    stage: _change(first.get(stage + "_seconds"), second.get(stage + "_seconds"))
                    for stage in ("retrieval", "generation")
                },
            }
        )
    metrics = {}
    for group, subgroup in (("native", "by_document"), ("ocr", "by_variant")):
        old, new = before["summary"][group], after["summary"][group]
        metrics[group] = {
            "overall": _change(old["overall"], new["overall"]),
            subgroup: {
                key: _change(old[subgroup][key], new[subgroup][key]) for key in old[subgroup]
            },
        }
    old_native, new_native = (run["summary"]["native"]["overall"] for run in (before, after))
    gates = {
        "native_accuracy_improves": new_native["answer_accuracy"]["count"]
        > old_native["answer_accuracy"]["count"],
        "native_false_refusals_drop": new_native["false_refusal_rate"]["count"]
        < old_native["false_refusal_rate"]["count"],
    }
    for group in ("native", "ocr"):
        old, new = (run["summary"][group]["overall"] for run in (before, after))
        gates[f"{group}_correct_refusals_do_not_drop"] = (
            new["correct_refusal_rate"]["count"] >= old["correct_refusal_rate"]["count"]
        )
        gates[f"{group}_unsupported_answers_do_not_rise"] = (
            new["unsupported_answer_rate"]["count"] <= old["unsupported_answer_rate"]["count"]
        )
        gates[f"{group}_zero_errors_in_both_runs"] = (
            old["operational_errors"] == new["operational_errors"] == 0
        )
        if group == "ocr":
            gates["ocr_accuracy_does_not_drop"] = (
                new["answer_accuracy"]["count"] >= old["answer_accuracy"]["count"]
            )
            gates["ocr_false_refusals_do_not_rise"] = (
                new["false_refusal_rate"]["count"] <= old["false_refusal_rate"]["count"]
            )
    result = {
        "schema_version": 1,
        "retrieval_comparison": {
            "ranked_chunks_identical": True,
            "scores_changed_cases": scores_changed_cases,
            "max_absolute_score_delta": max_absolute_score_delta,
            "policy": "Generation receives ranked chunks, not scores. Score drift is diagnostic.",
        },
        "sources": {
            name: {"directory": str(path), "artifact_sha256": run["hashes"]}
            for name, path, run in (("baseline", baseline, before), ("candidate", candidate, after))
        },
        "metrics": metrics,
        "cases": case_changes,
        "acceptance": {
            "passed": all(gates.values()),
            "gates": gates,
            "legacy_regression": "Separate review required; not included in this gate.",
            "latency_policy": "Reported without an automatic acceptance threshold.",
        },
    }
    with output.open("x") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = compare(args.baseline, args.candidate, args.output)
    except (AppError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Comparison failed: {exc}", file=sys.stderr)
        return 1
    print(f"Development acceptance passed: {result['acceptance']['passed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
