"""Deterministic reports with provenance on every rendering surface."""

import json
import re


def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def safe(value):
    # Render references as text, never executable HTML or Markdown links.
    value = re.sub(r"([\\`*_{}\[\]()#+.!|<>~-])", r"\\\1", str(value))
    return value.replace("\n", " ").replace("\r", " ")


def banner(result):
    p = result["provenance"]
    return ("DATA PROVENANCE: Real inputs (caller-labelled as Henry's own hand-entered data): "
            + (", ".join(p["real_input_ids"]) or "none")
            + ". Synthetic inputs (illustrative fixtures, not real customer results): "
            + (", ".join(p["synthetic_input_ids"]) or "none")
            + ". Source references and measurements are supplied, not independently verified.")


def render(result, fmt="md"):
    if fmt == "json":
        return json_text(dict(result, provenance_banner=banner(result)))
    lines = ["# Sparrow Case Study Generator", "", safe(banner(result)), "",
             f"As of: {result['as_of']}", "",
             "Publishable means completed, permission supplied, and evidence references supplied.",
             "Savings are baseline minus outcome. Negative values are regressions.",
             "Mixed totals include synthetic inputs and must not be claimed as real savings.", ""]
    for key, count in result["counts"].items():
        lines.append(f"- {key}: {count}")
    lines.append("")
    for unit, total in result["totals"].items():
        lines.append(f"- {unit} saved: {total['saved']} across {total['measured_cases']} paired measurements. {total['label']}.")
    lines += ["", "## Publishable case studies", ""]
    for c in result["cases"]:
        lines += [f"### {safe(c['id'])}: {safe(c['title'])}", "", "Provenance: " + ("SYNTHETIC, illustrative" if c["synthetic"] else "real, caller-labelled Henry input"), f"Completed: {c['completed_on']}", f"Work source: {safe(c['source'])}", "Evidence: " + "; ".join(safe(e) for e in c["evidence"])]
        for unit in ("minutes", "gbp"):
            if unit not in c["measured"]:
                lines.append(f"{unit} saved: unmeasured; no measured savings claim available.")
        for unit, m in c["measured"].items():
            lines.append(f"- {unit}: baseline {m['baseline']}, outcome {m['outcome']}, saved {m['saved']}. {m['label']}. Source: {safe(m['source'])}.")
        for unit, h in c["hypothetical"].items():
            lines.append(f"- {unit}: {h['value']} ({h['label']}).")
        lines.append("")
    lines += ["## Excluded work", ""]
    for e in result["excluded"]:
        lines.append(f"- {safe(e['id'])}: {'; '.join(e['reasons'])}")
    return "\n".join(lines) + "\n"
