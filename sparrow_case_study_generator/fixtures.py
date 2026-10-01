"""Labelled synthetic records and independently specified arithmetic expectations."""


def tiny():
    """Five hand-written scenarios repeated by the larger deterministic fixture."""
    common = {"completed_on": "2026-09-29", "synthetic": True, "source": "synthetic work log", "permission": True, "status": "completed", "evidence": ["synthetic sign-off"]}
    return [
        dict(common, id="A", title="Invoice reconciliation", measurements={"minutes": {"baseline": "60", "outcome": "20", "source": "synthetic stopwatch"}, "gbp": {"baseline": "100", "outcome": "75", "source": "synthetic ledger"}}),
        dict(common, id="B", title="Order handover", measurements={"minutes": {"baseline": "30", "outcome": "35", "source": "synthetic stopwatch"}}),
        dict(common, id="C", title="Unfinished work", status="draft"),
        dict(common, id="D", title="Private client work", permission=False),
        dict(common, id="E", title="Completed checklist", hypothetical={"minutes": "90", "gbp": "50"}),
    ]


def fixture_data(size=200):
    records = []
    for group in range(size // 5):
        for r in tiny():
            r["id"] = f"{group:03d}-{r['id']}"
            records.append(r)
    return {"_comment": "SYNTHETIC FIXTURE: illustrative, not real customer evidence", "schema_version": 1, "synthetic": True, "as_of": "2026-09-30", "records": records}


def expectations():
    # Hand arithmetic: 40 groups, 3 publishable per group, (40 - 5) minutes,
    # 25 GBP per group. Draft C and private D are excluded. E is hypothetical.
    return {"_comment": "SYNTHETIC ground truth, hand-computed independently of core", "synthetic": True, "counts": {"input": 200, "publishable": 120, "excluded": 80, "real": 0, "synthetic": 200}, "saved_minutes": "1400.00", "saved_gbp": "1000.00", "measured_minutes_cases": 80, "measured_gbp_cases": 40, "publishable_ids": [f"{g:03d}-{letter}" for g in range(40) for letter in ("A", "B", "E")], "excluded_ids": [f"{g:03d}-{letter}" for g in range(40) for letter in ("C", "D")]}
