"""
src/tasks/tasks_domain.py — domain-expert and domain-fix task factories.
"""
from __future__ import annotations

from crewai import Agent, Task

from src.tasks.domains import _DOMAIN_DESCRIPTIONS
from src.tasks.staging import _STAGING


def create_task_domain_expert(
    expert: Agent,
    domain_key: str,
    domain_description: str,
    context: list[Task],
) -> Task:
    """
    Generic domain-expert enrichment task.

    Design notes (v7 — file-read + anti-loop architecture):
      • File reading: domain experts now READ paper_outline.md and
        research_briefs.md explicitly via FileReaderTool. CrewAI context
        only passes the agent's response text (short confirmation), not
        the 15-32 KB file content. Explicit reads ensure domain experts
        have full context to produce high-quality contributions.
      • No escape hatch: the DOMAIN SKIP option is removed. Every domain
        expert MUST contribute content. The topic is broad enough for all.
      • Measurable output: the task requires a specific minimum (3 equations,
        5 references, 500+ words). Agents cannot shortcut to "COMPLETE."
      • No output_file: CrewAI's output_file parameter OVERWRITES the file
        that SafeFileWriterTool wrote with the agent's short final response.
        We intentionally omit it so the real 20 KB content is preserved.
    """
    return Task(
        description=f"""
You are a PhD-level domain specialist. You MUST contribute technical depth
to the academic paper being written.

Your domain expertise: {domain_description}

STEP 0 — Read the paper outline and research briefs to understand the topic:
    FileReaderTool("{_STAGING}/paper_outline.md")
    FileReaderTool("{_STAGING}/research_briefs.md")
    Then use web search (SerperDevSearchTool, ArxivSearchTool) to find domain-specific content.

YOUR MANDATORY OUTPUT — produce ALL of the following:

1. TECHNICAL ANALYSIS (500+ words):
   State-of-the-art methods, dominant approaches, and known failure modes
   from YOUR domain that are relevant to the paper topic. Be specific:
   name methods, cite years, give quantitative performance numbers.

2. EQUATIONS (minimum 3, LaTeX-ready):
   Each as: \\begin{{equation}} ... \\label{{eq:domain_{domain_key}_N}} \\end{{equation}}
   Include variable definitions after each equation.
   Only equations from YOUR domain — not already in the research briefs.

3. ALGORITHMS OR METHODS (minimum 2):
   Pseudocode or step-by-step descriptions of key algorithms from your field.

4. BIBTEX REFERENCES (minimum 5):
   Full BibTeX entries: @article{{Key, author=..., title=..., journal=..., year=..., doi=...}}
   Only real, verifiable references. No fabricated citations.

5. INTEGRATION NOTES (200+ words):
   How your domain contributions connect to the paper's overall system.

Write your complete contribution using SafeFileWriterTool to:
    {_STAGING}/domain_{domain_key}.md

IMPORTANT: You MUST produce all 5 sections. Do not skip any section.
Do not write "DOMAIN SKIP" or "DOMAIN EXPERT COMPLETE" without content.
Your output will be validated — empty or trivial responses will be flagged.
""".strip(),
        expected_output=(
            f"Complete domain contribution saved to {_STAGING}/domain_{domain_key}.md "
            f"containing: technical analysis (500+ words), 3+ LaTeX equations, "
            f"2+ algorithms, 5+ BibTeX references, and integration notes."
        ),
        agent=expert,
        context=context,
        # NO output_file here — CrewAI's output_file overwrites what SafeFileWriterTool
        # wrote (20 KB content → 2 KB summary). The real content lives in the file
        # written by the agent via SafeFileWriterTool during task execution.
    )


def create_task_fix_domain(
    fixer: Agent,
    domain_key: str,
    topic: str,
    outline_content: str,
) -> Task:
    """
    Task for the Research Fixer agent to produce content for a failed domain expert.
    The topic and outline are embedded directly in the task description (no file reads needed).
    """
    desc = _DOMAIN_DESCRIPTIONS.get(domain_key, domain_key)
    return Task(
        description=f"""
You are a Research Fixer. A domain expert failed to produce usable content.
Your job: produce the missing domain contribution yourself.

PAPER TOPIC: {topic}

PAPER OUTLINE:
{outline_content}

DOMAIN TO COVER: {desc}

Write a complete domain contribution with:
1. Technical analysis (500+ words) of state-of-the-art from this domain
2. At least 3 LaTeX-ready equations with variable definitions
3. At least 2 algorithm/method descriptions
4. At least 5 BibTeX references (real, verifiable)
5. Integration notes on how this domain connects to the paper

CRITICAL — use SafeFileWriterTool to write your output to EXACTLY this path:
    {_STAGING}/domain_{domain_key}.md
Do NOT change this filename. Do NOT use a different name.

You have web search tools (SerperDevSearchTool, ArxivSearchTool) — use them
to find real papers and data. Do NOT fabricate citations.
""".strip(),
        expected_output=(
            f"Domain contribution saved to {_STAGING}/domain_{domain_key}.md "
            f"with technical analysis, equations, algorithms, references, and integration notes."
        ),
        agent=fixer,
        # No output_file — agent writes via SafeFileWriterTool, don't overwrite.
    )
