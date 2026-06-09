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


def _latex_shared_rules(chapters_dir: str, bib_path: str, latex_dir: str) -> str:
    """Shared LaTeX writing rules injected into both latex task descriptions."""
    return f"""
CONTENT DEPTH — each chapter file must have:
    • Minimum 1000 words of Hebrew prose (ch06, ch08 ≥ 1400 words each)
    • Minimum 5 \\subsection{{}} blocks
    • Minimum 4 numbered equations with derivation text surrounding each
    • Minimum 2 \\includegraphics{{}} figures (using PNGs from the manifest)
    • Minimum 1 booktabs table

FIGURE WIDTH RULES:
    • Single-column figures: [width=0.98\\columnwidth]
    • Wide figures (flowcharts, multi-panel): use {{figure*}} with [width=\\textwidth]
    • Wide figure names: fig_bat_vs_artificial, fig_results_summary,
      fig_sensor_modalities, fig_framework_comparison
    • NEVER use width smaller than 0.9\\columnwidth.

LABEL UNIQUENESS — every \\label{{}} must be globally unique:
    • Prefix with chapter ID: \\label{{fig:ch02_name}}, \\label{{eq:ch03_name}}, \\label{{tab:ch05_name}}
    • NEVER reuse a label name from another chapter.

INLINE ENGLISH — every English word inside Hebrew prose MUST be wrapped:
    \\en{{SLAM}}, \\en{{EKF-SLAM}}, \\en{{LiDAR}}, \\en{{ORB-SLAM3}}, \\en{{IMU}}, etc.
    Math environments ($...$, \\begin{{equation}}) do NOT need \\en{{}}.
    Section titles mixing Hebrew+English: wrap the English part in \\en{{}}.

EM DASH RULE — character — is FORBIDDEN in Hebrew prose.
    Use colon (:) or comma (,). Only permitted inside \\en{{}} expansions.

FIGURES — CRITICAL:
    Read {_STAGING}/figures_manifest.md and use ONLY the exact filenames listed there.
    NEVER invent figure names. Never write \\fbox{{\\parbox{{...PLACEHOLDER...}}}}.
    Format: \\includegraphics[width=0.98\\columnwidth]{{figures/EXACT_NAME.png}}

PROTECTED (never overwrite):
    {chapters_dir}/ch01_intro.tex  {chapters_dir}/ch04_slam.tex
    {latex_dir}/main.tex           {chapters_dir}/cover.tex

Use SafeFileWriterTool for EVERY file. COMPILER: XeLaTeX.
""".strip()


def create_task_latex_part1(author: Agent, context: list[Task], run_folder: Path | None = None) -> Task:
    """
    Part 1 of 2: writes abstract + early chapters + references.bib.
    Files: abstract.tex, ch02_bio_basis.tex, ch03_sensors.tex, ch05_fusion.tex, references.bib
    """
    latex_dir = str(run_folder / "latex") if run_folder else "latex"
    chapters_dir = f"{latex_dir}/chapters"
    bib_path = f"{latex_dir}/references.bib"
    rules = _latex_shared_rules(chapters_dir, bib_path, latex_dir)
    return Task(
        description=f"""
You are writing the FIRST HALF of a 25–30 page IEEE paper in XeLaTeX (Hebrew primary language).

STEP 1 — READ ALL INPUTS first (FileReaderTool for each):
    FileReaderTool("{_STAGING}/hebrew_prose.md")      ← primary prose (read fully)
    FileReaderTool("{_STAGING}/figures_manifest.md")  ← exact figure filenames
    FileReaderTool("{_STAGING}/domain_biology.md")    ← biological ground truth
    FileReaderTool("{_STAGING}/domain_physics.md")    ← acoustics, matched filter
    FileReaderTool("{_STAGING}/domain_vision_ai.md")  ← vision/depth equations
    Files beginning with "DOMAIN SKIP:" — ignore.

STEP 2 — PLAN before writing. Output a one-line plan per file listing the key
    sections and equations you will include. Then write each file in order.

STEP 3 — WRITE these 5 files (ALL are required — do not skip any):

  {chapters_dir}/abstract.tex
      Short abstract (200–300 words Hebrew). No equations, no figures.
      Summarise: motivation, method, key contributions, main result.

  {chapters_dir}/ch02_bio_basis.tex
      \\section{{בסיס ביולוגי: אקולוקציה של עטלפים}}
      ≥1000 Hebrew words. Integrate biology + physics domain content.
      Cover: CF-FM pulse design, acoustic fovea mechanics, DSC control loop,
      neural computation (IC delay-tuned neurons, hippocampal place cells),
      bio-inspired engineering mappings. Include matched-filter equation.

  {chapters_dir}/ch03_sensors.tex
      \\section{{מודאליות חישה: LiDAR, סונאר MEMS, וראייה ממוחשבת}}
      ≥1000 Hebrew words. Integrate vision-AI domain content.
      Cover: LiDAR principle + range equation, MEMS sonar array + beamforming,
      monocular depth estimation (MonoDepth2/MiDaS), sensor comparison table.

  {chapters_dir}/ch05_fusion.tex
      \\section{{ארכיטקטורת היתוך חישנים}}
      ≥1000 Hebrew words. Integrate algorithms domain content.
      Cover: covariance intersection formula, EKF update equations,
      information-theoretic fusion, sensor weighting table.

  {bib_path}
      Full BibTeX file. MUST contain ALL 14 required keys:
      Thrun2005ProbRobotics, Kalman1960, Grisetti2010g2o, MurArtal2015ORB,
      Julier1997CovarianceIntersection, GriffinBatEcholocation,
      GriffithBatEcholocation, Simmons1979BatSonar, Schnitzler1968DSC,
      Schuller1974DSC, MossEcholocation, Rihaczek1969MatchedFilter,
      CrewAIDocs, AnthropicClaude.
      Add domain-expert references from domain files (≥5 additional entries).

{rules}
""".strip(),
        expected_output=(
            "5 files written: abstract.tex, ch02_bio_basis.tex, ch03_sensors.tex, "
            "ch05_fusion.tex, references.bib. Each chapter ≥1000 words, ≥5 subsections, "
            "≥4 equations. references.bib has all 14 required keys. "
            "Confirmation: 'LATEX PART 1 COMPLETE'."
        ),
        agent=author,
        context=context,
        output_file=f"{_STAGING}/latex_status_part1.md",
    )


def create_task_latex_part2(author: Agent, context: list[Task], run_folder: Path | None = None) -> Task:
    """
    Part 2 of 2: writes the later chapters (algorithm, system, results, conclusion + appendix).
    Files: ch06_algorithm.tex, ch07_oursystem.tex, ch08_results.tex, ch09_conclusion.tex
    """
    latex_dir = str(run_folder / "latex") if run_folder else "latex"
    chapters_dir = f"{latex_dir}/chapters"
    bib_path = f"{latex_dir}/references.bib"
    rules = _latex_shared_rules(chapters_dir, bib_path, latex_dir)
    return Task(
        description=f"""
You are writing the SECOND HALF of a 25–30 page IEEE paper in XeLaTeX (Hebrew primary language).
Part 1 (abstract, ch02, ch03, ch05, references.bib) has already been written.

STEP 1 — READ ALL INPUTS first (FileReaderTool for each):
    FileReaderTool("{_STAGING}/hebrew_prose.md")       ← primary prose (read fully)
    FileReaderTool("{_STAGING}/figures_manifest.md")   ← exact figure filenames
    FileReaderTool("{_STAGING}/domain_algorithms.md")  ← algorithm pseudocode/proofs
    FileReaderTool("{_STAGING}/domain_aerospace.md")   ← UAV/AUV/INS methods
    FileReaderTool("{_STAGING}/domain_vision_ai.md")   ← semantic SLAM, ViT
    Files beginning with "DOMAIN SKIP:" — ignore.

STEP 2 — PLAN before writing. Output a one-line plan per file listing key
    sections and equations. Then write each file in order.

STEP 3 — WRITE these 4 files (ALL required — do not skip any):

  {chapters_dir}/ch06_algorithm.tex
      \\section{{האלגוריתם הביו-מימטי המוצע}}
      ≥1400 Hebrew words. Integrate algorithms domain content.
      Cover: full algorithm description with \\begin{{algorithm}} pseudocode block,
      EKF predict/update derivation, complexity analysis O(n) table,
      convergence proof sketch, comparison to baseline algorithms.

  {chapters_dir}/ch07_oursystem.tex
      \\section{{פלטפורמת NavigatorCrew: עיצוב מערכת}}
      ≥1000 Hebrew words. Integrate aerospace domain content.
      Cover: system architecture (LangGraph state machine diagram description),
      agent pipeline table (role, tools, max_iter per agent),
      hardware deployment specs (Jetson, MEMS array), UAV dynamics model.

  {chapters_dir}/ch08_results.tex
      \\section{{תוצאות סימולציה וניתוח}}
      ≥1400 Hebrew words.
      Cover: simulation setup table, RMSE/ATE/RPE results table (4 algorithms × 3 metrics),
      ablation study (each sensor modality removed, performance drop),
      runtime analysis, figures from manifest (trajectory, heatmap, results_summary).

  {chapters_dir}/ch09_conclusion.tex
      \\section{{סיכום ומסקנות}}
      ≥800 Hebrew words for conclusion prose.
      Cover: contributions summary, limitations, future work (3 directions).
      After the conclusion, add appendix at the end of this file:
          \\appendix
          \\section{{רשימת סמלים ומשתנים}}
          booktabs table: Symbol | Definition | Units (≥20 rows covering all paper equations).
          This appendix adds ~1 organic page without padding.

{rules}
""".strip(),
        expected_output=(
            "4 files written: ch06_algorithm.tex (≥1400w), ch07_oursystem.tex (≥1000w), "
            "ch08_results.tex (≥1400w), ch09_conclusion.tex (≥800w + appendix). "
            "All labels unique with chapter prefix. All English wrapped in \\en{}. "
            "Confirmation: 'LATEX PART 2 COMPLETE'."
        ),
        agent=author,
        context=context,
        output_file=f"{_STAGING}/latex_status.md",
    )


# Keep the single-task version as an alias for backward compat with remediation
def create_task_latex(author: Agent, context: list[Task], run_folder: Path | None = None) -> Task:
    """Backward-compatible wrapper used by remediation node. Calls part2 logic."""
    return create_task_latex_part2(author, context, run_folder=run_folder)


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
        → figures → hebrew_prose
        → latex_part1 (abstract + ch02/03/05 + bib)
        → latex_part2 (ch06/07/08/09 + appendix)

    Splitting LaTeX into two tasks gives each half its own max_iter budget
    so the author is never cut off mid-paper.
    """
    t_outline  = create_task_outline(director, topic)
    t_research = create_task_research(researcher, [t_outline])

    t_dom_vision_ai   = create_task_domain_expert(dom_vision_ai,   "vision_ai",   _DOMAIN_DESCRIPTIONS["vision_ai"],   [t_research])
    t_dom_physics     = create_task_domain_expert(dom_physics,     "physics",     _DOMAIN_DESCRIPTIONS["physics"],     [t_research])
    t_dom_algorithms  = create_task_domain_expert(dom_algorithms,  "algorithms",  _DOMAIN_DESCRIPTIONS["algorithms"],  [t_research])
    t_dom_aerospace   = create_task_domain_expert(dom_aerospace,   "aerospace",   _DOMAIN_DESCRIPTIONS["aerospace"],   [t_research])
    t_dom_biology     = create_task_domain_expert(dom_biology,     "biology",     _DOMAIN_DESCRIPTIONS["biology"],     [t_research])

    domain_tasks = [t_dom_vision_ai, t_dom_physics, t_dom_algorithms, t_dom_aerospace, t_dom_biology]

    t_figures   = create_task_figures(visualizer, [t_research], run_folder=run_folder)
    t_hebrew    = create_task_hebrew_prose(hebrew_writer, [t_research] + domain_tasks)
    t_latex1    = create_task_latex_part1(author, [t_hebrew, t_figures], run_folder=run_folder)
    t_latex2    = create_task_latex_part2(author, [t_latex1], run_folder=run_folder)

    return [
        t_outline, t_research,
        t_dom_vision_ai, t_dom_physics, t_dom_algorithms, t_dom_aerospace, t_dom_biology,
        t_figures, t_hebrew, t_latex1, t_latex2,
    ]
