import json

import pytest

from sparrow_case_study_generator.core import compute
from sparrow_case_study_generator.fixtures import expectations, fixture_data
from sparrow_case_study_generator.report import render


def test_report_matches_ground_truth_exact():
    r = json.loads(render(compute(fixture_data()), "json"))
    e = expectations()
    assert r["counts"] == e["counts"]
    assert r["totals"]["minutes"]["saved"] == e["saved_minutes"]
    assert r["totals"]["gbp"]["saved"] == e["saved_gbp"]
    assert len(r["cases"]) == 120


def test_report_zero_false_positives():
    r = json.loads(render(compute(fixture_data()), "json"))
    actual = {c["id"] for c in r["cases"]}
    expected = set(expectations()["publishable_ids"])
    assert actual - expected == set()
    assert expected - actual == set()


@pytest.mark.parametrize("fmt", ["md", "json"])
def test_report_carries_provenance_banner(fmt):
    report = render(compute(fixture_data(5)), fmt)
    assert "DATA PROVENANCE" in report
    assert "Synthetic inputs" in report
    assert "illustrative" in report
    assert "Real inputs" in report


@pytest.mark.parametrize("fmt", ["md", "json"])
def test_hypothetical_figures_labelled(fmt):
    result = compute(fixture_data(5))
    report = render(result, fmt)
    assert "hypothetical, not measured" in report
    assert "excluded from totals" in report
    assert result["totals"]["minutes"]["saved"] == "35.00"
    if fmt == "md":
        assert "unmeasured" in report


def test_handles_unicode_and_long_inputs():
    data = fixture_data(5)
    data["records"][0]["title"] = "Café 工程 🐦 " + "a" * 9000
    data["records"][0]["source"] = "C:" + chr(92) + "Users" + chr(92) + "Henry" + chr(92) + "notes.md"
    for fmt in ("md", "json"):
        output = render(compute(data), fmt)
        assert "Café 工程 🐦" in output
        assert "a" * 9000 in output


def test_markdown_escapes_untrusted_text():
    data = fixture_data(5)
    data["records"][0]["title"] = "<script>alert(1)</script>"
    output = render(compute(data))
    assert "<script>" not in output


def test_no_em_dashes_in_outputs():
    for fmt in ("md", "json"):
        assert chr(8212) not in render(compute(fixture_data()), fmt)
