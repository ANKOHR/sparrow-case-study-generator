from sparrow_case_study_generator.core import compute
from sparrow_case_study_generator.fixtures import expectations, fixture_data


def test_fixtures_labelled_synthetic():
    data = fixture_data()
    assert data["synthetic"] is True
    assert data["_comment"].startswith("SYNTHETIC")
    assert all(r["synthetic"] is True for r in data["records"])
    assert expectations()["synthetic"] is True


def test_fixture_ground_truth_matches_hand_computed():
    result, expected = compute(fixture_data()), expectations()
    assert result["counts"] == expected["counts"]
    assert result["totals"]["minutes"]["saved"] == expected["saved_minutes"]
    assert result["totals"]["gbp"]["saved"] == expected["saved_gbp"]
    assert result["totals"]["minutes"]["measured_cases"] == expected["measured_minutes_cases"]
    assert result["totals"]["gbp"]["measured_cases"] == expected["measured_gbp_cases"]
    assert [c["id"] for c in result["cases"]] == expected["publishable_ids"]
    assert [c["id"] for c in result["excluded"]] == expected["excluded_ids"]
