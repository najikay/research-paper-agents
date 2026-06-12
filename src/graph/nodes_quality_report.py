"""
src/graph/nodes_quality_report.py
==================================
Quality gate report writer and bib/figure scoring helpers.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.config import PROJECT_ROOT, logger


def score_bib_and_figures(
    run_folder: Path, chapters_dir: Path, bib_path: Path, min_bib_entries: int,
) -> tuple[int, list[str], list[str]]:
    """Check references.bib and figure refs. Returns (penalty, issues, failed)."""
    penalty = 0
    issues: list[str] = []
    failed: list[str] = []

    if bib_path.exists():
        bib_text = bib_path.read_text(encoding="utf-8", errors="replace")
        entry_count = len(re.findall(r"@\w+\{", bib_text))
        if entry_count < min_bib_entries:
            issues.append(f"references.bib has only {entry_count} entries (need ≥{min_bib_entries})")
            penalty += max(0, (min_bib_entries - entry_count) * 2)
            failed.append("references")
    else:
        issues.append("references.bib does not exist")
        penalty += 20
        failed.append("references")

    figures_dir = run_folder / "latex" / "figures"
    missing_fig_penalty = 0
    for fpath in chapters_dir.glob("*.tex"):
        text = fpath.read_text(encoding="utf-8", errors="replace")
        for fig_ref in re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{figures/([^}]+)\}', text):
            if not (figures_dir / fig_ref).exists():
                issues.append(f"{fpath.name}: missing figure file 'figures/{fig_ref}'")
                failed.append("figures")
                if missing_fig_penalty < 20:
                    missing_fig_penalty += 2
    penalty += missing_fig_penalty

    static_files = {"cover.tex"}
    agent_tex = [f for f in chapters_dir.glob("*.tex") if f.name not in static_files]
    placeholder_files, emdash_files, center_files = [], [], []
    for fpath in agent_tex:
        text = fpath.read_text(encoding="utf-8", errors="replace")
        if "PLACEHOLDER" in text or r"\fbox{\parbox" in text:
            placeholder_files.append(fpath.name)
        clean = re.sub(r"\\en\{[^}]*\}", "", text)
        if "\u2014" in clean:
            emdash_files.append(fpath.name)
        if r"\begin{center}" in text:
            center_files.append(fpath.name)

    if placeholder_files:
        issues.append(f"Placeholder boxes found in: {placeholder_files}")
        penalty += 5
        failed.append("figures")
    if emdash_files:
        issues.append(f"Em dashes in Hebrew prose: {emdash_files}")
        penalty += 2
    if center_files:
        issues.append(f"\\begin{{center}} at document level (bidi crash risk): {center_files}")
        penalty += 10
        failed.append("methodology")

    return penalty, issues, failed


def write_quality_report(
    score: int,
    verdict: str,
    threshold: int,
    failed_sections: list[str],
    issues: list[str],
    chapter_min_reqs: dict[str, dict],
    default_min_reqs: dict,
    min_bib_entries: int,
) -> None:
    """Write the quality gate report to outputs/current/quality_report.md."""
    report_path = PROJECT_ROOT / "outputs" / "current" / "quality_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    issue_lines = "\n".join(f"- {i}" for i in issues) if issues else "- None"

    _def = default_min_reqs
    thresholds_lines = [
        f"- Default: eq>={_def['eq']}, fig>={_def['fig']}, "
        f"sub>={_def['sub']}, cite>={_def['cite']}, words>={_def['words']}"
    ]
    for fname, reqs in sorted(chapter_min_reqs.items()):
        diffs = [f"{k}>={v}" for k, v in reqs.items() if v != _def.get(k)]
        if diffs:
            thresholds_lines.append(f"- {fname}: {', '.join(diffs)}")

    report_content = f"""# Quality Gate Report

**Verdict:** {verdict}
**Score:** {score}/100
**Threshold:** {threshold}
**Failed Sections:** {failed_sections or 'none'}

## Issues Found

{issue_lines}

## Per-Chapter Thresholds

{chr(10).join(thresholds_lines)}
- references.bib: >={min_bib_entries} entries
- Missing figure files: <=-20 total penalty (capped)

```json
{{
  "verdict": "{verdict}",
  "score": {score},
  "failed_sections": {json.dumps(failed_sections)}
}}
```
"""
    report_path.write_text(report_content, encoding="utf-8")

    logger.info(f"[Graph] Quality verdict={verdict} score={score} failed={failed_sections}")
    if issues:
        for issue in issues[:5]:
            logger.warning(f"[Graph] Quality issue: {issue}")
