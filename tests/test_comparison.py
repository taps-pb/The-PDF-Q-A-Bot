"""Generation-only comparisons reject drift and keep their acceptance gates explicit."""

import json

import pytest

from pdf_qa.comparison import MATCHED_METADATA, compare, main
from pdf_qa.evidence import summarize
from pdf_qa.suite import sha
from pdf_qa.types import AppError


def _save(path, value):
    path.write_text(json.dumps(value))


def _refresh(directory, data, rebuild_summary=True):
    for name in ("cases", "results", "grades"):
        _save(directory / f"{name}.json", data[name])
    for name in ("cases", "results"):
        data["run"][name + "_sha256"] = sha((directory / f"{name}.json").read_bytes())
    if rebuild_summary:
        data["summary"] = summarize(data["cases"], data["results"], data["grades"])
    data["summary"]["review"] = {
        "reviewer": "AI-assisted test reviewer",
        "reviewed_at": "fixture",
        "grades_sha256": sha((directory / "grades.json").read_bytes()),
    }
    _save(directory / "run.json", data["run"])
    _save(directory / "summary.json", data["summary"])


def _run(directory, improved=False):
    directory.mkdir()
    cases, records, grades = [], [], {}
    for case_id, variant, answerable in (
        ("q1", "native", True),
        ("q2", "native", False),
        ("q1--scan", "scan", True),
        ("q1--mixed", "mixed", True),
    ):
        case = {
            "case_id": case_id,
            "id": case_id.split("--")[0],
            "document_id": "doc",
            "variant": variant,
            "split": "development",
            "answerable": answerable,
            "question": "Fixture question",
            "facts": [
                {"id": "f1", "text": "Evidence", "evidence": [[{"page": 1, "quote": "Evidence"}]]}
            ]
            if answerable
            else [],
        }
        refused = not answerable or (case_id == "q1" and not improved)
        records.append(
            {
                "case_id": case_id,
                "status": "ok",
                "hits": [
                    {
                        "chunk": {"id": "c1", "text": "Evidence", "page": 1, "method": "native"},
                        "score": 0.9,
                    }
                ],
                "answer": {
                    "text": "NOT FOUND" if refused else "Evidence",
                    "refused": refused,
                    "chunk_ids": [] if refused else ["c1"],
                    "citations": [] if refused else [1],
                },
                "retrieval_seconds": 1.0,
                "generation_seconds": 2.0 if improved else 3.0,
            }
        )
        grades[case_id] = {
            "facts": {
                "f1": {
                    "evidence_present": True,
                    "answer_correct": not refused,
                    "citation_supported": not refused,
                }
            }
            if answerable
            else {},
            "unsupported_claims": False,
            "failure_category": "generation_failure" if refused and answerable else "none",
            "notes": "Synthetic test judgments, not model evaluation.",
        }
        cases.append(case)
    data = {
        "cases": cases,
        "results": records,
        "grades": grades,
        "run": {
            **dict.fromkeys(MATCHED_METADATA, "fixed"),
            "schema_version": 2,
            "split": "development",
            "completed_at": "fixture",
            "k": 4,
            "prompt_sha256": "new" if improved else "old",
        },
    }
    _refresh(directory, data)
    return data


@pytest.fixture
def runs(tmp_path):
    baseline, candidate = tmp_path / "baseline", tmp_path / "candidate"
    old, new = _run(baseline), _run(candidate, improved=True)
    return baseline, candidate, tmp_path / "comparison.json", old, new


def test_deltas_acceptance_case_changes_latency_and_immutable_output(runs):
    baseline, candidate, output, _, _ = runs
    result = compare(baseline, candidate, output)
    assert result["acceptance"]["passed"] is True
    assert result["metrics"]["native"]["overall"]["delta"]["answer_accuracy"]["count"] == 1
    assert result["metrics"]["native"]["overall"]["delta"]["false_refusal_rate"]["count"] == -1
    assert result["metrics"]["ocr"]["overall"]["delta"]["answer_accuracy"]["count"] == 0
    assert result["cases"][0]["outcome"] == {"before": "false_refusal", "after": "correct_answer"}
    assert result["cases"][0]["failure"] == {"before": "generation_failure", "after": "none"}
    assert result["cases"][0]["latency_seconds"]["generation"]["delta"] == -1
    assert json.loads(output.read_text()) == result
    with pytest.raises(AppError, match="already exists"):
        compare(baseline, candidate, output)


@pytest.mark.parametrize("field", MATCHED_METADATA)
def test_provenance_must_match(runs, field):
    baseline, candidate, output, _, new = runs
    new["run"][field] = "changed"
    _refresh(candidate, new)
    with pytest.raises(AppError, match=field):
        compare(baseline, candidate, output)
    assert not output.exists()


@pytest.mark.parametrize("change", ["heldout_run", "heldout_case", "question", "hits", "evidence"])
def test_rejects_heldout_changed_cases_or_changed_evidence(runs, change):
    baseline, candidate, output, _, new = runs
    if change == "heldout_run":
        new["run"]["split"] = "heldout"
    elif change == "heldout_case":
        new["cases"][0]["split"] = "heldout"
    elif change == "question":
        new["cases"][0]["question"] = "Different question"
    elif change == "hits":
        new["results"][0]["hits"][0]["chunk"]["text"] = "Changed text"
    else:
        new["grades"]["q1"]["facts"]["f1"].update(evidence_present=False, citation_supported=False)
        new["grades"]["q1"]["failure_category"] = "incomplete_retrieval"
    _refresh(candidate, new)
    with pytest.raises(AppError):
        compare(baseline, candidate, output)


def test_score_only_drift_is_reported_without_changing_acceptance(runs):
    baseline, candidate, output, _, new = runs
    new["results"][0]["hits"][0]["score"] += 0.000104
    _refresh(candidate, new)
    result = compare(baseline, candidate, output)
    assert result["acceptance"]["passed"] is True
    assert result["retrieval_comparison"]["scores_changed_cases"] == ["q1"]
    assert result["retrieval_comparison"]["max_absolute_score_delta"] == pytest.approx(0.000104)


def test_changed_rank_is_rejected_even_with_the_same_passages(runs):
    baseline, candidate, output, old, new = runs
    additional = {
        "chunk": {"id": "c2", "text": "More", "page": 2, "method": "native"},
        "score": 0.8,
    }
    old["results"][0]["hits"].append(additional)
    new["results"][0]["hits"].insert(0, additional)
    _refresh(baseline, old)
    _refresh(candidate, new)
    with pytest.raises(AppError, match="ranked retrieved chunks"):
        compare(baseline, candidate, output)


@pytest.mark.parametrize("score", [float("nan"), float("inf"), "0.9", True])
def test_invalid_retrieval_scores_are_rejected(runs, score):
    baseline, candidate, output, _, new = runs
    new["results"][0]["hits"][0]["score"] = score
    _refresh(candidate, new)
    with pytest.raises(AppError, match="finite numbers"):
        compare(baseline, candidate, output)


@pytest.mark.parametrize("artifact", ["cases", "results", "grades", "summary"])
def test_rejects_tampered_artifacts(runs, artifact):
    baseline, candidate, output, _, new = runs
    if artifact == "summary":
        new[artifact]["native"]["overall"]["answer_accuracy"]["count"] = 999
        _save(candidate / "summary.json", new[artifact])
    else:
        (candidate / f"{artifact}.json").write_text("{}")
    with pytest.raises((AppError, KeyError, TypeError)):
        compare(baseline, candidate, output)


def test_rejects_incomplete_grades_even_when_grade_hash_updated(runs):
    baseline, candidate, output, _, new = runs
    new["grades"]["q1"]["facts"]["f1"]["answer_correct"] = None
    _refresh(candidate, new, rebuild_summary=False)
    with pytest.raises(AppError, match="boolean"):
        compare(baseline, candidate, output)


def test_explicit_refusal_unsupported_and_ocr_regression_gates(runs):
    baseline, candidate, output, _, new = runs
    new["results"][1]["answer"].update(
        text="Unsupported answer", refused=False, citations=[1], chunk_ids=["c1"]
    )
    new["grades"]["q2"].update(unsupported_claims=True, failure_category="unsupported_answer")
    new["results"][2]["answer"].update(text="NOT FOUND", refused=True, citations=[], chunk_ids=[])
    new["grades"]["q1--scan"]["facts"]["f1"].update(answer_correct=False, citation_supported=False)
    new["grades"]["q1--scan"]["failure_category"] = "generation_failure"
    _refresh(candidate, new)
    result = compare(baseline, candidate, output)
    assert result["acceptance"]["passed"] is False
    gates = result["acceptance"]["gates"]
    assert gates["native_accuracy_improves"] is True
    assert gates["native_correct_refusals_do_not_drop"] is False
    assert gates["native_unsupported_answers_do_not_rise"] is False
    assert gates["ocr_accuracy_does_not_drop"] is False
    assert gates["ocr_false_refusals_do_not_rise"] is False


def test_errors_fail_acceptance_and_cli_reports_validation_failures(runs, capsys):
    baseline, candidate, output, _, new = runs
    new["results"][0].update(status="error", answer=None, generation_seconds=None)
    new["grades"]["q1"]["facts"]["f1"].update(answer_correct=False, citation_supported=False)
    new["grades"]["q1"]["failure_category"] = "operational_error"
    _refresh(candidate, new)
    result = compare(baseline, candidate, output)
    assert result["acceptance"]["gates"]["native_zero_errors_in_both_runs"] is False
    assert result["cases"][0]["latency_seconds"]["generation"]["delta"] is None
    assert (
        main(["--baseline", str(baseline), "--candidate", str(candidate), "--output", str(output)])
        == 1
    )
    assert "already exists" in capsys.readouterr().err
