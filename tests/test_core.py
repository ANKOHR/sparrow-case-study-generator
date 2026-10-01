from copy import deepcopy

import pytest

from sparrow_case_study_generator.core import SchemaError, compute
from sparrow_case_study_generator.fixtures import fixture_data


def test_tiny_hand_written_ground_truth():
    r = compute(fixture_data(5))
    assert r["counts"]["publishable"] == 3
    assert r["totals"]["minutes"]["saved"] == "35.00"
    assert r["totals"]["gbp"]["saved"] == "25.00"
    assert r["cases"][1]["measured"]["minutes"]["saved"] == "-5.00"


@pytest.mark.parametrize("mutation,field", [
    (lambda d: d["records"][0]["measurements"]["minutes"].update(baseline="-1"), "baseline"),
    (lambda d: d["records"][0]["measurements"]["gbp"].update(outcome="NaN"), "outcome"),
    (lambda d: d["records"][0]["measurements"]["gbp"].update(outcome="Infinity"), "outcome"),
    (lambda d: d["records"][0]["measurements"]["gbp"].update(outcome="0.001"), "outcome"),
    (lambda d: d["records"][0]["measurements"]["gbp"].update(outcome=1.5), "outcome"),
    (lambda d: d["records"][0]["measurements"]["minutes"].pop("baseline"), "baseline"),
    (lambda d: d["records"][0].update(completed_on="2026-10-01"), "completed_on"),
    (lambda d: d["records"][0].update(title="x" * 10001), "title"),
    (lambda d: d["records"][1].update(id="000-A"), "duplicate"),
    (lambda d: d["records"][0].update(permission="yes"), "boolean"),
    (lambda d: d["records"][0].update(estimated_savings="100"), "estimated_savings"),
    (lambda d: d["records"][0].update(title="bad" + chr(8212)), "em dash"),
    (lambda d: d["records"][0].update(synthetic=False), "synthetic"),
    (lambda d: d.update(schema_version=True), "schema_version"),
])
def test_rejects_adversarial_values(mutation, field):
    data = fixture_data(5)
    mutation(data)
    with pytest.raises(SchemaError, match=field):
        compute(data)


def test_corrupted_fixture_changes_computed_figures():
    data = fixture_data()
    original = compute(data)
    data["records"][0]["measurements"]["minutes"]["outcome"] = "21"
    changed = compute(data)
    assert original["totals"]["minutes"]["saved"] == "1400.00"
    assert changed["totals"]["minutes"]["saved"] == "1399.00"
    data["records"][0]["permission"] = False
    assert compute(data)["counts"]["publishable"] == 119


def test_real_and_mixed_provenance():
    data = fixture_data(5)
    data["synthetic"] = False
    data["records"][0]["synthetic"] = False
    result = compute(data)
    assert result["provenance"]["real_input_ids"] == ["000-A"]
    assert result["counts"]["synthetic"] == 4


def test_no_input_mutation_and_missing_evidence():
    data = fixture_data(5)
    data["records"][0]["evidence"] = []
    before = deepcopy(data)
    result = compute(data)
    assert data == before
    assert result["counts"]["publishable"] == 2
    assert result["excluded"][0]["reasons"] == ["evidence references missing"]
