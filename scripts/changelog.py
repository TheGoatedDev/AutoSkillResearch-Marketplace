"""Generate changelog from experiment log kept entries."""


def generate_changelog(skill_name: str, log: dict, version: str | None = None) -> str:
    kept = [e for e in log.get("entries", []) if e.get("outcome") == "kept"]
    kept.sort(key=lambda e: e.get("timestamp", ""), reverse=True)

    lines = [f"# Changelog \u2014 {skill_name}", ""]

    for i, entry in enumerate(kept):
        v = version if i == 0 and version else None
        date = entry.get("timestamp", "unknown")[:10]
        summary = entry.get("change_summary", "No description")

        header = f"## {v} ({date})" if v else f"## {date}"
        lines.append(header)

        metric_parts = []
        for metric_name, values in entry.get("metrics", {}).items():
            if isinstance(values, dict) and "old" in values and "new" in values:
                metric_parts.append(f"{metric_name}: {values['old']:.2f} \u2192 {values['new']:.2f}")
        metric_str = f" ({', '.join(metric_parts)})" if metric_parts else ""

        lines.append(f"- Improved: {summary}{metric_str}")
        lines.append("")

    if not kept:
        lines.append("No improvements yet.")
        lines.append("")

    return "\n".join(lines)
