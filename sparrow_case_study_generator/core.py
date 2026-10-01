"""Pure validation and evidence computation. No predictions or inferred savings."""

from datetime import date
from decimal import Decimal, InvalidOperation


class SchemaError(ValueError):
    """An input field violates the documented schema."""


def fail(field, message):
    raise SchemaError(f"SchemaError: {field}: {message}")


def text(value, field, limit=10000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        fail(field, f"must be nonempty text of at most {limit} characters")
    if chr(8212) in value or any(ord(c) < 32 and c not in "\n\t" for c in value):
        fail(field, "em dash or control character is not allowed")
    return value


def amount(value, field):
    if not isinstance(value, str) or len(value) > 32:
        fail(field, "must be a nonnegative decimal string")
    try:
        number = Decimal(value)
    except InvalidOperation:
        fail(field, "must be a nonnegative decimal string")
    if not number.is_finite() or number < 0 or number > Decimal("1000000000"):
        fail(field, "must be finite and between 0 and 1000000000")
    if number.as_tuple().exponent < -2:
        fail(field, "at most two decimal places are allowed")
    return number


def fields(obj, required, optional, field):
    if not isinstance(obj, dict):
        fail(field, "must be an object")
    missing = set(required) - obj.keys()
    extra = obj.keys() - set(required) - set(optional)
    if missing or extra:
        fail(field, f"missing fields {sorted(missing)}; unknown fields {sorted(extra)}")


def validate(data):
    fields(data, ["schema_version", "synthetic", "as_of", "records"], ["_comment"], "input")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        fail("schema_version", "must be 1")
    if type(data["synthetic"]) is not bool:
        fail("synthetic", "must be boolean")
    try:
        cutoff = date.fromisoformat(data["as_of"])
    except (ValueError, TypeError):
        fail("as_of", "must be an ISO date YYYY-MM-DD")
    if cutoff.isoformat() != data["as_of"]:
        fail("as_of", "must be YYYY-MM-DD")
    if not isinstance(data["records"], list):
        fail("records", "must be an array")
    ids = set()
    for i, record in enumerate(data["records"]):
        prefix = f"records[{i}]"
        fields(record, ["id", "title", "status", "completed_on", "permission", "synthetic", "source", "evidence"], ["measurements", "hypothetical"], prefix)
        rid = text(record["id"], prefix + ".id", 128)
        if rid in ids:
            fail(prefix + ".id", f"duplicate id {rid}")
        ids.add(rid)
        for key in ("title", "source"):
            text(record[key], prefix + "." + key)
        if record["status"] not in ("completed", "draft"):
            fail(prefix + ".status", "must be completed or draft")
        if type(record["permission"]) is not bool or type(record["synthetic"]) is not bool:
            fail(prefix, "permission and synthetic must be boolean")
        if data["synthetic"] and not record["synthetic"]:
            fail(prefix + ".synthetic", "synthetic input cannot contain real records")
        try:
            completed = date.fromisoformat(record["completed_on"])
        except (ValueError, TypeError):
            fail(prefix + ".completed_on", "must be YYYY-MM-DD")
        if completed.isoformat() != record["completed_on"] or completed > cutoff:
            fail(prefix + ".completed_on", "must be YYYY-MM-DD and not after as_of")
        if not isinstance(record["evidence"], list):
            fail(prefix + ".evidence", "must be an array of source references")
        for ref in record["evidence"]:
            text(ref, prefix + ".evidence")
        metrics = record.get("measurements", {})
        fields(metrics, [], ["minutes", "gbp"], prefix + ".measurements")
        for unit, measurement in metrics.items():
            path = prefix + ".measurements." + unit
            fields(measurement, ["baseline", "outcome", "source"], [], path)
            amount(measurement["baseline"], path + ".baseline")
            amount(measurement["outcome"], path + ".outcome")
            text(measurement["source"], path + ".source")
        hypothetical = record.get("hypothetical", {})
        fields(hypothetical, [], ["minutes", "gbp"], prefix + ".hypothetical")
        for unit, value in hypothetical.items():
            amount(value, prefix + ".hypothetical." + unit)
    return data


def compute(data):
    """Savings are signed baseline minus outcome, including regressions."""
    validate(data)
    cases, excluded = [], []
    totals = {"minutes": Decimal(0), "gbp": Decimal(0)}
    measured_counts = {"minutes": 0, "gbp": 0}
    for r in sorted(data["records"], key=lambda r: r["id"]):
        reasons = []
        if r["status"] != "completed":
            reasons.append("not completed")
        if not r["permission"]:
            reasons.append("publication permission missing")
        if not r["evidence"]:
            reasons.append("evidence references missing")
        if reasons:
            excluded.append({"id": r["id"], "reasons": reasons})
            continue
        measured = {}
        for unit, m in r.get("measurements", {}).items():
            delta = amount(m["baseline"], unit) - amount(m["outcome"], unit)
            measured[unit] = {"baseline": format(Decimal(m["baseline"]), ".2f"), "outcome": format(Decimal(m["outcome"]), ".2f"), "saved": format(delta, ".2f"), "source": m["source"], "label": "measured from supplied baseline and outcome; not independently verified"}
            totals[unit] += delta
            measured_counts[unit] += 1
        cases.append({"id": r["id"], "title": r["title"], "completed_on": r["completed_on"], "synthetic": r["synthetic"], "source": r["source"], "evidence": r["evidence"], "measured": measured, "hypothetical": {u: {"value": format(Decimal(v), ".2f"), "label": "hypothetical, not measured; excluded from totals"} for u, v in sorted(r.get("hypothetical", {}).items())}})
    real_ids = sorted(r["id"] for r in data["records"] if not r["synthetic"])
    synthetic_ids = sorted(r["id"] for r in data["records"] if r["synthetic"])
    return {"schema_version": 1, "as_of": data["as_of"], "provenance": {"real_input_ids": real_ids, "synthetic_input_ids": synthetic_ids, "real_data_declaration": "Caller-labelled real inputs entered by Henry; ownership and measurements are not independently verified", "synthetic_label": "Synthetic fixtures are illustrative, not evidence of real customer outcomes"}, "counts": {"input": len(data["records"]), "publishable": len(cases), "excluded": len(excluded), "real": len(real_ids), "synthetic": len(synthetic_ids)}, "totals": {u: {"saved": format(v, ".2f"), "measured_cases": measured_counts[u], "label": "computed from supplied paired measurements of publishable cases only; synthetic values are illustrative"} for u, v in totals.items()}, "cases": cases, "excluded": excluded}
