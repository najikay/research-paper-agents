"""
src/tasks/tasks_research_core.py — outline, research, and figure task factories.
"""
from __future__ import annotations
from pathlib import Path
from crewai import Agent, Task
from src.tasks.staging import _STAGING


def create_task_outline(director: Agent, topic: str) -> Task:
    return Task(
        description=f"""
Analyze the topic '{topic}' and create a chapter-by-chapter outline for a 25–30 page IEEE paper.
Save the outline to {_STAGING}/paper_outline.md.

STEP 1 — Decompose '{topic}' into 8 content chapters:
    Chapter 1: Introduction — problem statement, motivation, contributions, paper roadmap
    Chapters 2–7: Core technical sub-domains SPECIFIC to '{topic}' (you decide the split)
    Chapter 8: Simulation/Experimental Results and Performance Analysis
    Chapter 9: Conclusion, Limitations, Future Work

STEP 2 — For each chapter specify:
    - Hebrew title for \\section{{...}} (use appropriate Hebrew technical terms for the domain)
    - 3–5 subsection titles (Hebrew)
    - 3+ equations (with LaTeX math, e.g. $x_{{k+1}} = Ax_k + Bu_k$)
    - 2 figure filenames: fig_<short_description>.png (exactly 9 figures total across all chapters)
    - 1 table topic (comparison or summary)
    - 3–5 English search keywords for Serper/ArXiv queries (ALL searches must be in English)

STEP 3 — Write the complete outline to {_STAGING}/paper_outline.md.
    The outline MUST be self-contained: downstream agents read only this file to understand
    the paper structure. Be specific about equations, figure content, and section labels.
""".strip(),
        expected_output=(
            f"Detailed chapter-by-chapter outline in {_STAGING}/paper_outline.md with topic-specific "
            f"Hebrew chapter titles, subsections, equations, figure filenames, and search keywords. "
            f"Confirmation: 'OUTLINE COMPLETE'."
        ),
        agent=director,
        # NO output_file — the agent writes via SafeFileWriterTool.
        # CrewAI's output_file would OVERWRITE the 18 KB outline with a 400-byte summary.
    )


def create_task_research(researcher: Agent, context: list[Task]) -> Task:
    return Task(
        description=f"""
Produce 8 detailed technical research briefs based on {_STAGING}/paper_outline.md.
Each brief must provide enough material for a 3–4 page chapter (600+ words of content).

STEP 1 — Read the outline:
    FileReaderTool("{_STAGING}/paper_outline.md")

STEP 2 — Research each sub-domain using web search:
    Use SerperDevSearchTool and ArxivSearchTool to find real papers, methods, and data.

STEP 3 — For each sub-domain produce:
  • 2–3 paragraph technical summary (Hebrew-language prose ready to paste)
  • All relevant equations with full variable definitions
  • Algorithm descriptions (pseudocode if applicable)
  • 3–5 specific BibTeX citations with author, title, year
  • Figure descriptions (what to plot and why)
  • A comparison table (at least 3 alternatives compared on 3+ criteria)

STEP 4 — Save ALL briefs using SafeFileWriterTool to {_STAGING}/research_briefs.md.
    IMPORTANT: Your response text is NOT saved to any file automatically.
    You MUST call SafeFileWriterTool to write the complete research content.
    The file must contain all 8 briefs (total ≥4800 words).
""".strip(),
        expected_output=f"8 structured research briefs in {_STAGING}/research_briefs.md, each providing ≥600 words of technical content. Confirmation: 'RESEARCH COMPLETE'.",
        agent=researcher,
        context=context,
        # NO output_file — the agent writes via SafeFileWriterTool.
        # CrewAI's output_file would OVERWRITE the real research content with a summary.
    )


def create_task_figures(visualizer: Agent, context: list[Task], run_folder: Path | None = None) -> Task:
    latex_figures = str(run_folder / "latex" / "figures") if run_folder else "latex/figures"
    return Task(
        description=f"""
Generate 9 IEEE-standard publication-quality figures as 300 DPI PNG files.

STEP 0 — READ THE OUTLINE to understand the topic and required figures:
    FileReaderTool("{_STAGING}/paper_outline.md")
    The outline lists required figures per chapter — use those filenames and topics.
    If the outline does not specify filenames, invent clear topic-appropriate names
    following the convention: fig_<topic_keyword>.png (e.g. fig_trajectory_3d.png).

STEP 1 — HOW TO CALL PythonCodeExecutorTool for each figure:
    - `code`: a complete matplotlib script ending with
      plt.savefig(output_path, dpi=300, bbox_inches='tight') and plt.close('all')
    - `output_filename`: the exact PNG filename (e.g. 'fig_trajectory_3d.png')

CRITICAL — `output_path` is a variable that the tool injects automatically into your script.
Do NOT hardcode any file path in plt.savefig(). Always write:
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
The tool will save the file to {latex_figures}/ automatically.

STEP 2 — GENERATE EXACTLY 9 FIGURES (call the tool once per figure, in order):
    Use the figures specified in the outline. At minimum, produce figures covering:
    1. A comparative pipeline/architecture flowchart for the paper's main contribution
    2. A 3D trajectory or spatial map (mpl_toolkits.mplot3d)
    3. A sensor confidence heatmap or occupancy grid (plt.imshow)
    4. A signal/spectrum analysis figure (spectrogram or time-frequency plot)
    5. A range/velocity or signal processing map
    6. An estimation uncertainty plot (e.g. EKF covariance ellipses or particle filter)
    7. A performance comparison bar chart (multiple algorithms × multiple metrics)
    8. A system architecture block diagram
    9. A multi-panel results summary (RMSE / ATE / RPE or equivalent metrics)

    Name each file to match the outline's specifications.

FIGURE QUALITY REQUIREMENTS:
    - plt.style.use('seaborn-v0_8-whitegrid') or equivalent clean base style
    - Wide/multi-panel figures: figsize=(16, 7) or larger
    - Minimum font size for ANY text element: 11pt
      (ax.tick_params(labelsize=11), ax.set_xlabel(..., fontsize=12))
    - All axes must have labels with units. Legends required when ≥2 series.
    - Include Hebrew labels/captions where specified in the outline.
    - Use plt.tight_layout() before savefig.

STEP 3 — After all 9 figures are saved, write a manifest to {_STAGING}/figures_manifest.md:
    One row per figure: filename | title | Hebrew caption | \\label{{fig:...}} key
""".strip(),
        expected_output=f"9 PNG files saved to {latex_figures}/ and manifest at {_STAGING}/figures_manifest.md listing all 9 filenames with captions and label keys. Confirmation: 'FIGURES COMPLETE'.",
        agent=visualizer,
        context=context,
        output_file=f"{_STAGING}/figures_status.md"  # separate from manifest content written via SafeFileWriterTool
    )
