"""
src/tasks/research_tasks.py
============================
Factory functions for the 5 NavigatorCrew tasks.
Architecture: Robust Sequential Pipeline v4.0.
"""

from __future__ import annotations
from crewai import Agent, Task
from src.config import logger

def create_task_outline(director: Agent, topic: str) -> Task:
    return Task(
        description=f"""
Decompose the topic '{topic}' into 8 sub-domains and create outputs/paper_outline.md.

TARGET: The final paper must be 25–30 printed A4 pages (IEEEtran, 10pt).
Each sub-domain chapter should contain at least 4 subsections, 3 equations,
2 figures, and 1 table — scaffold the outline to enforce this depth.

Sub-domains to cover:
  1. Biological basis: bat echolocation and acoustic fovea
  2. Sensor modalities: LiDAR, MEMS sonar, Vision-AI depth
  3. SLAM algorithms: EKF-SLAM, Graph-SLAM, ORB-SLAM3, AF-AFC controller
  4. Sensor fusion architecture: covariance intersection, EKF update
  5. Biomimetic algorithm design: full system pipeline
  6. NavigatorCrew AI system: agents, tools, LangGraph orchestration
  7. Simulation results and performance analysis
  8. Conclusion, limitations, future work

For each chapter specify: title (Hebrew), section label, 4+ subsection titles,
required equations, required figures (with filenames from latex/figures/),
required table topics, and 3–5 English search keywords the researcher should
use when querying Serper/ArXiv (all searches must be in English).
""".strip(),
        expected_output="Detailed chapter-by-chapter outline in outputs/paper_outline.md specifying subsections, equations, figures, and tables per chapter. Confirmation: 'OUTLINE COMPLETE'.",
        agent=director,
        output_file="outputs/paper_outline.md"
    )

def create_task_research(researcher: Agent, context: list[Task]) -> Task:
    return Task(
        description="""
Produce 8 detailed technical research briefs based on outputs/paper_outline.md.
Each brief must provide enough material for a 3–4 page chapter (600+ words of content).

For each sub-domain include:
  • 2–3 paragraph technical summary (Hebrew-language prose ready to paste)
  • All relevant equations with full variable definitions
  • Algorithm descriptions (pseudocode if applicable)
  • 3–5 specific BibTeX citations with author, title, year
  • Figure descriptions (what to plot and why)
  • A comparison table (at least 3 alternatives compared on 3+ criteria)

Write to outputs/research_briefs.md.
""".strip(),
        expected_output="8 structured research briefs in outputs/research_briefs.md, each providing ≥600 words of technical content. Confirmation: 'RESEARCH COMPLETE'.",
        agent=researcher,
        context=context,
        output_file="outputs/research_briefs.md"
    )

def create_task_figures(visualizer: Agent, context: list[Task]) -> Task:
    return Task(
        description="Generate 9 IEEE-standard figures and save to latex/figures/. Write manifest to outputs/figures_manifest.md.",
        expected_output="9 PNG files and a manifest in outputs/figures_manifest.md.",
        agent=visualizer,
        context=context,
        output_file="outputs/figures_manifest.md"
    )

def create_task_hebrew_prose(writer: Agent, context: list[Task]) -> Task:
    return Task(
        description="""
Read outputs/research_briefs.md and write polished Hebrew academic prose for
all chapters (CH02–CH09). Save to outputs/hebrew_prose.md.

For each chapter section write 150–250 words of Hebrew prose. Use your judgment
to keep standard academic English terms (SLAM, EKF, LiDAR, UAV, etc.) in English
— the same way a Technion robotics professor would write. Translate generic words
to Hebrew. Do not write LaTeX. Mark equation/figure/table placement with
[EQUATION: name], [FIGURE: name], [TABLE: description]. Mark citations with
[CITE: BibKey].
""".strip(),
        expected_output="outputs/hebrew_prose.md with Hebrew prose for all 8 chapters. Confirmation: 'HEBREW PROSE COMPLETE'.",
        agent=writer,
        context=context,
        output_file="outputs/hebrew_prose.md",
    )


def create_task_latex(author: Agent, context: list[Task]) -> Task:
    return Task(
        description="""
Write 9 LaTeX chapter files + references.bib based on the research briefs and figures manifest.
Target: 25–30 printed pages total (A4, IEEEtran, 10pt).

PRE-WRITTEN (PROTECTED — do NOT overwrite):
    latex/chapters/ch01_intro.tex    ← static, already written
    latex/chapters/ch04_slam.tex     ← static, already written
    latex/main.tex                   ← protected master document
    latex/chapters/cover.tex         ← protected cover page

FILES TO WRITE (exact paths — write ALL of these):
    latex/chapters/abstract.tex
    latex/chapters/ch02_bio_basis.tex
    latex/chapters/ch03_sensors.tex
    latex/chapters/ch05_fusion.tex
    latex/chapters/ch06_algorithm.tex
    latex/chapters/ch07_oursystem.tex
    latex/chapters/ch08_results.tex
    latex/chapters/ch09_conclusion.tex
    latex/references.bib

CONTENT DEPTH — each of ch02–ch09 must have:
    • Minimum 600 words of Hebrew prose
    • Minimum 4 \\subsection{} blocks
    • Minimum 3 numbered equations with derivation text
    • Minimum 2 \\includegraphics{} figures (using PNGs from the manifest)
    • Minimum 1 booktabs table
    ch06 (algorithm) and ch08 (results) must have ≥ 900 words each.

CITATION KEYS — references.bib MUST define ALL of these keys (and may add more):
    Thrun2005ProbRobotics, Kalman1960, Grisetti2010g2o, MurArtal2015ORB,
    Julier1997CovarianceIntersection, GriffinBatEcholocation,
    GriffithBatEcholocation, Simmons1979BatSonar, Schnitzler1968DSC,
    Schuller1974DSC, MossEcholocation, Rihaczek1969MatchedFilter,
    CrewAIDocs, AnthropicClaude
    These keys are cited in ch01_intro.tex and ch04_slam.tex — if they are
    missing from references.bib the PDF will have [?] markers.

EM DASH RULE — the character — is FORBIDDEN in Hebrew prose.
    Use colon (:) or comma (,) instead. Em dash is only permitted inside
    \\en{} abbreviation expansions, e.g., \\en{UAV — Unmanned Aerial Vehicles}.

FIGURES — use ONLY filenames confirmed in the figures manifest.
    Never write \\fbox{\\parbox{...PLACEHOLDER...}} boxes.
    Use: \\includegraphics[width=0.92\\columnwidth]{figures/fig_name.png}

COMPILER: XeLaTeX. Every file must compile without errors.
""".strip(),
        expected_output=(
            "10 .tex files and references.bib written to latex/. "
            "Each chapter ≥ 600 words, ≥ 4 subsections, ≥ 3 equations. "
            "references.bib contains all 14 required citation keys. "
            "No em dashes in Hebrew prose. No placeholder figure boxes. "
            "Confirmation: 'LATEX COMPLETE'."
        ),
        agent=author,
        context=context,
        output_file="latex/references.bib"
    )

def create_task_review(editor: Agent, context: list[Task]) -> Task:
    return Task(
        description="""
Conduct a peer review of all LaTeX files and output a report to outputs/quality_report.md.

**MANDATORY**: Your report MUST end with a machine-readable JSON verdict block:

```json
{
  "verdict": "PASS" or "FAIL",
  "score": <integer 0-100>,
  "failed_sections": ["section_name", ...]
}
```

Score below 75 = FAIL. Failed sections must use these exact names if applicable:
methodology, algorithms, related_work, equations, introduction, conclusion, references, figures.
""",
        expected_output="Quality report in outputs/quality_report.md ending with a JSON verdict block.",
        agent=editor,
        context=context,
        output_file="outputs/quality_report.md"
    )

def create_remediation_task(
    agent: Agent,
    failed_sections: list[str],
    quality_report_path: str,
    output_file: str,
) -> Task:
    """
    Targeted fix task. The agent reads the quality report and the existing
    output files, then patches ONLY the sections listed in failed_sections.
    """
    sections_str = ", ".join(failed_sections)
    return Task(
        description=f"""
REMEDIATION TASK. You are fixing specific quality failures identified by the QualityEditor.

1. Read the quality report at {quality_report_path} to understand each specific issue.
2. Read the existing output files to understand what currently exists.
3. Fix ONLY the following failed sections: [{sections_str}]
4. Do NOT modify sections that passed — this minimises unnecessary rewrites.
5. Overwrite only the files that contain the failing sections.
6. Produce the same output files as the original task, but with issues resolved.
""",
        expected_output=f"Fixed output file(s) addressing failures in: {sections_str}. Confirmation: 'REMEDIATION COMPLETE'.",
        agent=agent,
        output_file=output_file,
    )

def create_all_tasks(director, researcher, visualizer, hebrew_writer, author, topic) -> list[Task]:
    """
    5-task pipeline:
      outline → research → figures → hebrew_prose → latex
    Quality review is handled programmatically by the LangGraph gate.
    """
    t_outline  = create_task_outline(director, topic)
    t_research = create_task_research(researcher, [t_outline])
    t_figures  = create_task_figures(visualizer, [t_research])
    t_hebrew   = create_task_hebrew_prose(hebrew_writer, [t_research])
    t_latex    = create_task_latex(author, [t_hebrew, t_figures])
    return [t_outline, t_research, t_figures, t_hebrew, t_latex]
