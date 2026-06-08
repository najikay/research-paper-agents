"""
src/tasks/research_tasks.py
============================
Factory functions for the 5 NavigatorCrew tasks.
Architecture: Robust Sequential Pipeline v4.0.

All intermediate outputs are staged to outputs/current/ during a run.
main.py moves them to the per-run archive folder on completion and cleans up.
"""

from __future__ import annotations
from pathlib import Path
from crewai import Agent, Task
from src.config import logger

# Staging directory for all intermediate outputs during a run.
# Always use this constant — never hardcode "outputs/" directly.
_STAGING = "outputs/current"


def create_task_outline(director: Agent, topic: str) -> Task:
    return Task(
        description=f"""
Decompose the topic '{topic}' into 8 sub-domains and create {_STAGING}/paper_outline.md.

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
        expected_output=f"Detailed chapter-by-chapter outline in {_STAGING}/paper_outline.md specifying subsections, equations, figures, and tables per chapter. Confirmation: 'OUTLINE COMPLETE'.",
        agent=director,
        output_file=f"{_STAGING}/paper_outline.md"
    )


def create_task_research(researcher: Agent, context: list[Task]) -> Task:
    return Task(
        description=f"""
Produce 8 detailed technical research briefs based on {_STAGING}/paper_outline.md.
Each brief must provide enough material for a 3–4 page chapter (600+ words of content).

For each sub-domain include:
  • 2–3 paragraph technical summary (Hebrew-language prose ready to paste)
  • All relevant equations with full variable definitions
  • Algorithm descriptions (pseudocode if applicable)
  • 3–5 specific BibTeX citations with author, title, year
  • Figure descriptions (what to plot and why)
  • A comparison table (at least 3 alternatives compared on 3+ criteria)

Write to {_STAGING}/research_briefs.md.
""".strip(),
        expected_output=f"8 structured research briefs in {_STAGING}/research_briefs.md, each providing ≥600 words of technical content. Confirmation: 'RESEARCH COMPLETE'.",
        agent=researcher,
        context=context,
        output_file=f"{_STAGING}/research_briefs.md"
    )


def create_task_figures(visualizer: Agent, context: list[Task], run_folder: Path | None = None) -> Task:
    latex_figures = str(run_folder / "latex" / "figures") if run_folder else "latex/figures"
    return Task(
        description=(
            f"Generate 9 IEEE-standard figures and save them to {latex_figures}/.\n"
            f"Wide figures (fig_bat_vs_artificial, fig_sensor_modalities, fig_results_summary, "
            f"fig_framework_comparison) should use figsize=(16, 7) or larger to ensure all "
            f"text labels are readable at A4 print size. Minimum font size in any figure: 11pt.\n"
            f"Use the EXACT absolute path '{latex_figures}/' in every plt.savefig() call.\n"
            f"After saving all 9 figures, write the manifest to {_STAGING}/figures_manifest.md."
        ),
        expected_output=f"9 PNG files in {latex_figures}/ and a manifest in {_STAGING}/figures_manifest.md.",
        agent=visualizer,
        context=context,
        output_file=f"{_STAGING}/figures_manifest.md"
    )


def create_task_domain_expert(
    expert: Agent,
    domain_key: str,
    domain_description: str,
    context: list[Task],
) -> Task:
    """
    Generic domain-expert enrichment task.
    Each specialist reads the outline + research briefs and contributes
    domain-specific depth (equations, algorithms, insights, references).
    If the topic is outside their domain they write a single DOMAIN SKIP line.
    """
    return Task(
        description=f"""
You are a PhD-level domain specialist contributing technical depth to an academic paper.

STEP 1 — Read existing work (use FileReaderTool for each):
    FileReaderTool("{_STAGING}/paper_outline.md")
    FileReaderTool("{_STAGING}/research_briefs.md")

STEP 2 — Assess relevance of your domain to this paper topic:
    Your domain: {domain_description}

STEP 3a — If your domain IS relevant to the topic:
    Contribute content NOT already covered in the research briefs:
    • Domain-specific equations with full derivations and variable definitions
      (numbered, LaTeX-ready format)
    • Algorithms, methods, or design principles unique to your field
    • Physical, biological, or theoretical insights that deepen any chapter
    • 3–5 key BibTeX-formatted references from your domain
      (format: @article{{Key, author=..., title=..., journal=..., year=..., doi=...}})
    Precision standard: PhD-level. Cite primary sources. No padding.

STEP 3b — If your domain has NO meaningful intersection with this topic:
    Write exactly one line: "DOMAIN SKIP: [brief reason]"
    Do NOT pad with generic content — professional silence is valued.

Write your output to {_STAGING}/domain_{domain_key}.md
""".strip(),
        expected_output=(
            f"Domain contribution at {_STAGING}/domain_{domain_key}.md "
            f"with equations, algorithms, and references, OR a single 'DOMAIN SKIP:' line."
        ),
        agent=expert,
        context=context,
        output_file=f"{_STAGING}/domain_{domain_key}.md",
    )


def create_task_hebrew_prose(writer: Agent, context: list[Task]) -> Task:
    return Task(
        description=f"""
Read all research and domain-expert materials, then write polished Hebrew academic
prose for all chapters (CH02–CH09). Save to {_STAGING}/hebrew_prose.md.

STEP 1 — READ ALL INPUTS (use FileReaderTool for each):
    FileReaderTool("{_STAGING}/research_briefs.md")       ← primary technical input
    FileReaderTool("{_STAGING}/domain_vision_ai.md")      ← Vision-AI expert
    FileReaderTool("{_STAGING}/domain_physics.md")        ← Physics expert
    FileReaderTool("{_STAGING}/domain_algorithms.md")     ← Algorithms expert
    FileReaderTool("{_STAGING}/domain_aerospace.md")      ← Aerospace/Marine expert
    FileReaderTool("{_STAGING}/domain_biology.md")        ← Biology expert
    Files that begin with "DOMAIN SKIP:" have no relevant content — ignore them.
    All other domain files contain PhD-level contributions — incorporate them fully.

STEP 2 — Write Hebrew prose for each chapter (CH02–CH09):
    TARGET: 25–30 printed pages total. Each chapter must be 3–4 pages ≈ 800–1200 words.
    Chapters ch06 (algorithm) and ch08 (results) must reach 1200–1500 words each.

    Per-chapter minimum content:
        • 4+ subsections with substantive prose under each heading
        • All equations listed in research briefs: write context paragraphs before/after each
        • All algorithm steps: explain each step in prose (1–2 sentences per step)
        • All tables: describe what the table shows and what the reader should conclude
        • Mark placements inline: [EQUATION: name], [FIGURE: filename], [TABLE: description]
        • Mark citations inline: [CITE: BibKey]

    Language rules (CRITICAL — LaTeX will crash otherwise):
        • Write prose in Hebrew.
        • Keep standard technical acronyms in English: SLAM, EKF, UKF, LiDAR, UAV, IMU,
          GPS, MEMS, ORB-SLAM3, iSAM2, GTSAM, CNN, ViT, ReLU, etc.
        • NEVER use the em dash character (—). Use colon (:) or comma (,) instead.
        • Do NOT write LaTeX commands — only prose text with inline markers.

    Integrate ALL domain-expert contributions:
        • Biology expert: bat mechanics, DSC, acoustic fovea
        • Physics expert: matched filter math, Doppler, beamforming
        • Algorithms expert: filter math, complexity, convergence proofs
        • Aerospace expert: UAV dynamics, INS, AUV parallels
        • Vision-AI expert: depth estimation, semantic SLAM
        Each non-SKIP domain file adds mandatory content to at least 2 chapters.
""".strip(),
        expected_output=f"{_STAGING}/hebrew_prose.md with Hebrew prose for all 8 chapters incorporating domain expert contributions. ≥800 words per chapter, ≥1200 for ch06/ch08. Confirmation: 'HEBREW PROSE COMPLETE'.",
        agent=writer,
        context=context,
        output_file=f"{_STAGING}/hebrew_prose.md",
    )


def create_task_latex(author: Agent, context: list[Task], run_folder: Path | None = None) -> Task:
    latex_dir = str(run_folder / "latex") if run_folder else "latex"
    chapters_dir = f"{latex_dir}/chapters"
    bib_path = f"{latex_dir}/references.bib"
    return Task(
        description=f"""
Write 9 LaTeX chapter files + references.bib based on the research briefs and figures manifest.
Target: 25–30 printed pages total (A4, IEEEtran, 10pt).

STEP 1 — READ INPUTS BEFORE WRITING ANYTHING:
    FileReaderTool("{_STAGING}/hebrew_prose.md")          ← primary prose input
    FileReaderTool("{_STAGING}/figures_manifest.md")      ← authoritative figure filenames
    FileReaderTool("{_STAGING}/domain_vision_ai.md")      ← Vision-AI equations/algorithms
    FileReaderTool("{_STAGING}/domain_physics.md")        ← Physics derivations
    FileReaderTool("{_STAGING}/domain_algorithms.md")     ← Algorithm pseudocode/proofs
    FileReaderTool("{_STAGING}/domain_aerospace.md")      ← Aerospace/Marine methods
    FileReaderTool("{_STAGING}/domain_biology.md")        ← Biological ground truth
    Files beginning with "DOMAIN SKIP:" contain no content — ignore them.

PRE-WRITTEN (PROTECTED — do NOT overwrite):
    {chapters_dir}/ch01_intro.tex    ← static, already written
    {chapters_dir}/ch04_slam.tex     ← static, already written
    {latex_dir}/main.tex             ← protected master document
    {chapters_dir}/cover.tex         ← protected cover page

FILES TO WRITE (exact paths — write ALL of these):
    {chapters_dir}/abstract.tex
    {chapters_dir}/ch02_bio_basis.tex
    {chapters_dir}/ch03_sensors.tex
    {chapters_dir}/ch05_fusion.tex
    {chapters_dir}/ch06_algorithm.tex
    {chapters_dir}/ch07_oursystem.tex
    {chapters_dir}/ch08_results.tex
    {chapters_dir}/ch09_conclusion.tex
    {bib_path}

CONTENT DEPTH — each of ch02–ch09 must have:
    • Minimum 1000 words of Hebrew prose
    • Minimum 5 \\subsection{{}} blocks
    • Minimum 4 numbered equations with derivation text surrounding each
    • Minimum 2 \\includegraphics{{}} figures (using PNGs from the manifest)
    • Minimum 1 booktabs table
    ch06 (algorithm) and ch08 (results) must have ≥ 1400 words each.

FIGURE WIDTH RULES (critical for readability):
    • Single figures spanning one column: [width=0.98\\columnwidth]
    • Wide figures (flowcharts, block diagrams, multi-panel): [width=\\textwidth]
    • Figures in {{figure*}} float span both columns: use for fig_bat_vs_artificial,
      fig_results_summary, fig_sensor_modalities, fig_framework_comparison
    • NEVER use width smaller than 0.9\\columnwidth — figures must be readable in print.
    • Prefer {{figure*}} for any figure wider than it is tall.

LABEL UNIQUENESS (prevents multiply-defined label warnings):
    • Every \\label{{}} must be globally unique across ALL chapter files.
    • Convention: \\label{{fig:ch02_bat_vs_art}}, \\label{{eq:ch03_lfm}}, \\label{{tab:ch07_specs}}
    • Prefix every label with the chapter ID (ch02_, ch03_, etc.).

INLINE ENGLISH (prevents bidi language-switch crashes):
    • Every English word or phrase inside Hebrew prose MUST be wrapped: \\en{{word}}
    • Examples: \\en{{SLAM}}, \\en{{EKF-SLAM}}, \\en{{LiDAR}}, \\en{{ORB-SLAM3}}
    • Math environments ($...$, \\begin{{equation}}) are already in a neutral mode — no \\en{{}} needed inside math.
    • Section titles that mix Hebrew and English: use \\en{{}} for the English parts.
    • Failure to wrap English causes "Missing character" warnings and corrupt PDF rendering.

APPENDIX: Add an appendix section after ch09 with:
    \\appendix
    \\section{{רשימת סמלים ומשתנים}}  (List of symbols and variables)
    A two-column table: Symbol | Definition | Units
    Include at least 20 symbols used in the paper's equations.
    This adds 1–2 pages organically without padding prose.
    (Appendix content goes at the bottom of ch09_conclusion.tex after the conclusion text,
    preceded by \\appendix.)

CITATION KEYS — references.bib MUST define ALL of these keys (and may add more):
    Thrun2005ProbRobotics, Kalman1960, Grisetti2010g2o, MurArtal2015ORB,
    Julier1997CovarianceIntersection, GriffinBatEcholocation,
    GriffithBatEcholocation, Simmons1979BatSonar, Schnitzler1968DSC,
    Schuller1974DSC, MossEcholocation, Rihaczek1969MatchedFilter,
    CrewAIDocs, AnthropicClaude
    These keys are cited in the static protected chapters (ch01, ch04) — if
    they are missing from references.bib the PDF will have [?] markers.

EM DASH RULE — the character — is FORBIDDEN in Hebrew prose.
    Use colon (:) or comma (,) instead. Em dash is only permitted inside
    \\en{{}} abbreviation expansions, e.g., \\en{{UAV — Unmanned Aerial Vehicles}}.

FIGURES — CRITICAL RULE:
    1. Read {_STAGING}/figures_manifest.md FIRST with FileReaderTool.
    2. Extract the EXACT filenames listed there (e.g. fig_bat_vs_artificial.png).
    3. Use ONLY those exact filenames in \\includegraphics{{}} commands.
    4. NEVER invent figure names. A figure that does not exist in the manifest
       will cause a fatal LaTeX compile error (! Unable to load picture).
    5. Never write \\fbox{{\\parbox{{...PLACEHOLDER...}}}} boxes.
    Format: \\includegraphics[width=0.92\\columnwidth]{{figures/EXACT_NAME.png}}

COMPILER: XeLaTeX. Every file must compile without errors.

IMPORTANT — references.bib MUST be written using SafeFileWriterTool with path
"{bib_path}". Do NOT rely on the task output mechanism to write it —
that mechanism only captures your final status message, NOT the BibTeX content.
Use SafeFileWriterTool for EVERY file you write (chapters AND references.bib).
""".strip(),
        expected_output=(
            "10 .tex files and references.bib written to latex/. "
            "Each chapter ≥ 1000 words, ≥ 5 subsections, ≥ 4 equations. "
            "references.bib contains all 14 required citation keys. "
            "No em dashes in Hebrew prose. No placeholder figure boxes. "
            "No multiply-defined labels. All English wrapped in \\en{}. "
            "Confirmation: 'LATEX COMPLETE'."
        ),
        agent=author,
        context=context,
        output_file=f"{_STAGING}/latex_status.md"
    )


def create_task_review(editor: Agent, context: list[Task]) -> Task:
    return Task(
        description=f"""
Conduct a peer review of all LaTeX files and output a report to {_STAGING}/quality_report.md.

**MANDATORY**: Your report MUST end with a machine-readable JSON verdict block:

```json
{{
  "verdict": "PASS" or "FAIL",
  "score": <integer 0-100>,
  "failed_sections": ["section_name", ...]
}}
```

Score below 75 = FAIL. Failed sections must use these exact names if applicable:
methodology, algorithms, related_work, equations, introduction, conclusion, references, figures.
""",
        expected_output=f"Quality report in {_STAGING}/quality_report.md ending with a JSON verdict block.",
        agent=editor,
        context=context,
        output_file=f"{_STAGING}/quality_report.md"
    )


def create_remediation_task(
    agent: Agent,
    failed_sections: list[str],
    quality_report_path: str,
    output_file: str,
    run_folder: Path | None = None,
) -> Task:
    """
    Targeted fix task. The agent reads the quality report and the existing
    output files, then patches ONLY the sections listed in failed_sections.
    """
    sections_str = ", ".join(failed_sections)

    # If this is a LaTeX author task and we know the run folder, include
    # the absolute write paths so the agent writes to the correct location.
    latex_paths_note = ""
    if run_folder is not None:
        chapters_dir = run_folder / "latex" / "chapters"
        bib_path     = run_folder / "latex" / "references.bib"
        latex_paths_note = f"""
WRITE PATHS — use these exact absolute paths with SafeFileWriterTool:
    Chapters : {chapters_dir}/<filename>.tex
    BibTeX   : {bib_path}
"""

    return Task(
        description=f"""
REMEDIATION TASK. You are fixing specific quality failures identified by the QualityEditor.

1. Read the quality report: FileReaderTool("{quality_report_path}")
2. Read the existing output files to understand what currently exists.
3. Fix ONLY the following failed sections: [{sections_str}]
4. Do NOT modify sections that passed — this minimises unnecessary rewrites.
5. Overwrite only the files that contain the failing sections.
6. Produce the same output files as the original task, but with issues resolved.
{latex_paths_note}
""",
        expected_output=f"Fixed output file(s) addressing failures in: {sections_str}. Confirmation: 'REMEDIATION COMPLETE'.",
        agent=agent,
        output_file=output_file,
    )


_DOMAIN_DESCRIPTIONS: dict[str, str] = {
    "vision_ai": (
        "Visual SLAM, monocular/stereo depth estimation, semantic segmentation, "
        "optical flow, neural feature descriptors, vision transformers, edge inference"
    ),
    "physics": (
        "Matched filter theory, LFM/FM sonar signal design, acoustic wave propagation, "
        "Doppler physics, cochlear mechanics, range-Doppler ambiguity, beamforming"
    ),
    "algorithms": (
        "EKF/UKF/particle filters, factor graph SLAM (g2o/GTSAM/iSAM2), "
        "covariance intersection, loop closure, CRLB, computational complexity of SLAM"
    ),
    "aerospace": (
        "UAV 6-DOF flight dynamics, IMU strapdown/INS, GPS-denied navigation, "
        "AUV/submarine sonar, DVL, multi-path acoustics, submarine↔cave navigation parallel"
    ),
    "biology": (
        "Bat echolocation (CF-FM sonar, acoustic fovea, DSC mechanism), "
        "neural computation for spatial mapping, bio-inspired algorithm design, "
        "dolphin biosonar, lateral line sensing"
    ),
}


def create_all_tasks(
    director,
    researcher,
    dom_vision_ai,
    dom_physics,
    dom_algorithms,
    dom_aerospace,
    dom_biology,
    visualizer,
    hebrew_writer,
    author,
    topic,
    run_folder: Path | None = None,
) -> list[Task]:
    """
    11-task pipeline:
      outline → research
        → domain_vision_ai → domain_physics → domain_algorithms
        → domain_aerospace → domain_biology
        → figures → hebrew_prose → latex
    Quality review is handled programmatically by the LangGraph gate.
    Domain experts each read the research briefs independently and add
    domain-specific depth. They write "DOMAIN SKIP:" if the topic is
    outside their expertise.
    """
    t_outline  = create_task_outline(director, topic)
    t_research = create_task_research(researcher, [t_outline])

    # Domain expert enrichment — all read research briefs, run sequentially
    t_dom_vision_ai   = create_task_domain_expert(dom_vision_ai,   "vision_ai",   _DOMAIN_DESCRIPTIONS["vision_ai"],   [t_research])
    t_dom_physics     = create_task_domain_expert(dom_physics,     "physics",     _DOMAIN_DESCRIPTIONS["physics"],     [t_research])
    t_dom_algorithms  = create_task_domain_expert(dom_algorithms,  "algorithms",  _DOMAIN_DESCRIPTIONS["algorithms"],  [t_research])
    t_dom_aerospace   = create_task_domain_expert(dom_aerospace,   "aerospace",   _DOMAIN_DESCRIPTIONS["aerospace"],   [t_research])
    t_dom_biology     = create_task_domain_expert(dom_biology,     "biology",     _DOMAIN_DESCRIPTIONS["biology"],     [t_research])

    domain_tasks = [t_dom_vision_ai, t_dom_physics, t_dom_algorithms, t_dom_aerospace, t_dom_biology]

    t_figures  = create_task_figures(visualizer, [t_research], run_folder=run_folder)
    t_hebrew   = create_task_hebrew_prose(hebrew_writer, [t_research] + domain_tasks)
    t_latex    = create_task_latex(author, [t_hebrew, t_figures], run_folder=run_folder)

    return [
        t_outline, t_research,
        t_dom_vision_ai, t_dom_physics, t_dom_algorithms, t_dom_aerospace, t_dom_biology,
        t_figures, t_hebrew, t_latex,
    ]
