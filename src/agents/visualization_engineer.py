"""
src/agents/visualization_engineer.py
======================================
VisualizationEngineer — Scientific Figure Generation Agent.

Persona:    Noa Shapira
Role:       Scientific Visualization & Sensor Data Engineering Specialist
Tools:      PythonCodeExecutorTool, SafeFileWriterTool
            (injected at crew-assembly time by crew.py)

Produces all 9 required figures for the IEEE paper as 300 DPI PNG files
saved to {run_folder}/latex/figures/. Each figure is fully labeled, captioned,
and formatted to IEEE publication standards.

The agent reads paper_outline.md from the task description context to determine
topic-appropriate figure filenames and content — it is not hardcoded to any
specific topic. Figure specifications live in create_task_figures().
"""

from __future__ import annotations

from typing import Any

from crewai import Agent

from src.config import AGENT_MAX_ITER, SONNET_LLM, logger

# ---------------------------------------------------------------------------
# Prompt constants
# ---------------------------------------------------------------------------

_ROLE = "Scientific Visualization & Sensor Data Engineering Specialist"

_GOAL = """
Generate all 9 publication-quality figures required for the IEEE paper.
The exact figure topics and filenames are specified in the task description,
which you must read before generating any figures.

Core standards that apply to EVERY figure you produce:

1. Write complete, runnable Python code — no pseudocode, no ellipsis.
2. Include all data generation inside the script (no external files required).
3. Use the injected variable `output_path` for saving:
       plt.savefig(output_path, dpi=300, bbox_inches='tight')
   DO NOT hardcode any file path — the tool injects `output_path` automatically.
4. Use plt.style.use('seaborn-v0_8-whitegrid') or equivalent for a clean base.
5. All axis labels, titles, and legends must be present and readable at A4 print size.
6. ALL text in figures (titles, axis labels, legends, annotations, tick labels) MUST be in English only. Do NOT use Hebrew in any matplotlib text — Hebrew causes RTL rendering issues and flipped characters in matplotlib.
7. After saving, call plt.close('all') to release memory.
8. Minimum font size for any text element (title, axis labels, tick labels, legend): 11pt.
   Use ax.tick_params(labelsize=11), ax.set_xlabel(..., fontsize=12), etc.
9. Use plt.tight_layout() before savefig for clean spacing.
10. Wide/multi-panel figures: figsize=(16, 7) or larger.

After completing all 9 figures, write a manifest to outputs/current/figures_manifest.md
listing: filename, title, caption (Hebrew), and the \\label{fig:...} key for LaTeX.
""".strip()

_BACKSTORY = """
Noa Shapira holds an M.Sc. in Computational Neuroscience from the Hebrew
University of Jerusalem, where her thesis modeled bat cochlear mechanics
using biophysical differential equations. She subsequently spent 8 years
as a research engineer at Mobileye and Rafael Advanced Defense Systems,
producing visualization pipelines for autonomous vehicle sensor fusion
and active sonar signal processing.

Her figures have appeared in 15 peer-reviewed publications across IEEE
Transactions on Robotics, IEEE Signal Processing Letters, ICRA, and IROS.
She contributed the visualization suite to the open-source BatSLAM library
and has given workshops on scientific figure design at Weizmann and Technion.

Noa's philosophy is unambiguous: "A figure is not decoration. It is the
primary evidence. If a reader cannot extract the key numerical result from
your figure in under 10 seconds, you have failed as an engineer."

She has been known to reject her own figure drafts six times before
submitting — citing insufficient label size (minimum 12pt), missing
units on axes, or color palettes inaccessible to colorblind readers.
Every figure she produces includes: a descriptive title, labeled axes
with units, a legend where multiple series are present, and a scale bar
where spatial data is shown.
""".strip()

_EXPECTED_TOOLS = [
    "PythonCodeExecutorTool — executes matplotlib/scipy code, saves PNG to latex/figures/",
    "SafeFileWriterTool     — writes figures_manifest.md to outputs/current/",
]


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------

def create_visualization_engineer(tools: list[Any] | None = None) -> Agent:
    """
    Instantiate the VisualizationEngineer agent.

    Args:
        tools: [PythonCodeExecutorTool(), SafeFileWriterTool()]
               Pass [] or None only in test/dry-run contexts.

    Returns:
        A configured CrewAI Agent.
    """
    if tools is None:
        tools = []
        logger.warning(
            "VisualizationEngineer created with NO tools. "
            "Expected: PythonCodeExecutorTool, SafeFileWriterTool. "
            "Acceptable for unit tests only."
        )

    logger.debug(
        f"Creating VisualizationEngineer | LLM={SONNET_LLM} "
        f"| tools={[type(t).__name__ for t in tools]} "
        f"| max_iter={AGENT_MAX_ITER['data_visualizer']}"
    )

    return Agent(
        role=_ROLE,
        goal=_GOAL,
        backstory=_BACKSTORY,
        tools=tools,
        llm=SONNET_LLM,
        verbose=True,
        allow_delegation=False,
        max_iter=AGENT_MAX_ITER["data_visualizer"],
        memory=False,                   # figures are deterministic; memory not needed
    )


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    agent = create_visualization_engineer()
    print(f"Role    : {agent.role}")
    print(f"LLM     : {agent.llm}")
    print(f"Max iter: {agent.max_iter}")
    print(f"Memory  : {agent.memory}")
    print(f"Tools   : {agent.tools} (empty — expected in self-test)")
    print("\nExpected live tools:")
    for t in _EXPECTED_TOOLS:
        print(f"  • {t}")
    print("\nRequired figures (9 total):")
    figures = [line.strip() for line in _GOAL.split("\n") if line.strip().startswith("[FIG")]
    for f in figures:
        print(f"  {f}")
