"""
src/tasks/tasks_prose.py — Hebrew academic prose task factory.
"""
from __future__ import annotations
from pathlib import Path
from crewai import Agent, Task
from src.tasks.staging import _STAGING


def create_task_hebrew_prose(writer: Agent, context: list[Task]) -> Task:
    return Task(
        description=f"""
Read all research and domain-expert materials, then write polished Hebrew academic
prose for ALL chapters (CH01–CH09). Save prose to {_STAGING}/hebrew_prose.md.

STEP 1 — READ ALL INPUTS (use FileReaderTool for each):
    FileReaderTool("{_STAGING}/paper_outline.md")         ← chapter structure, titles, equations
    FileReaderTool("{_STAGING}/research_briefs.md")       ← primary technical input
    FileReaderTool("{_STAGING}/domain_vision_ai.md")      ← Vision-AI expert (if not DOMAIN SKIP)
    FileReaderTool("{_STAGING}/domain_physics.md")        ← Physics expert (if not DOMAIN SKIP)
    FileReaderTool("{_STAGING}/domain_algorithms.md")     ← Algorithms expert (if not DOMAIN SKIP)
    FileReaderTool("{_STAGING}/domain_aerospace.md")      ← Aerospace/Marine expert (if not DOMAIN SKIP)
    FileReaderTool("{_STAGING}/domain_biology.md")        ← Biology expert (if not DOMAIN SKIP)
    FileReaderTool("{_STAGING}/domain_signal_processing.md") ← Signal processing expert
    FileReaderTool("{_STAGING}/domain_control_systems.md")   ← Control systems expert
    FileReaderTool("{_STAGING}/domain_ml.md")                ← ML expert
    Files that begin with "DOMAIN SKIP:" have no relevant content — skip them.

STEP 2 — Write Hebrew prose for ALL nine chapters. You MUST write in THREE separate
    batches because a single call will be truncated by the output token limit.

    BATCH 1 — call SafeFileWriterTool ONCE to write {_STAGING}/hebrew_prose_part1.md:
        ## CH01: <title>   (≥1200 Hebrew words, 3+ subsections)
        ## CH02: <title>   (≥1500 Hebrew words, 4+ subsections)
        ## CH03: <title>   (≥1500 Hebrew words, 4+ subsections)
        After writing, confirm: "BATCH 1 WRITTEN — 3 chapters."

    BATCH 2 — call SafeFileWriterTool ONCE to write {_STAGING}/hebrew_prose_part2.md:
        ## CH04: <title>   (≥1500 Hebrew words, 4+ subsections)
        ## CH05: <title>   (≥1500 Hebrew words, 4+ subsections)
        ## CH06: <title>   (≥1800 Hebrew words, 5+ subsections — this is the core algorithm chapter)
        After writing, confirm: "BATCH 2 WRITTEN — 3 chapters."

    BATCH 3 — call SafeFileWriterTool ONCE to write {_STAGING}/hebrew_prose_part3.md:
        ## CH07: <title>   (≥1500 Hebrew words, 4+ subsections)
        ## CH08: <title>   (≥1800 Hebrew words, 5+ subsections — this is the results chapter)
        ## CH09: <title>   (≥900 Hebrew words, 3+ subsections)
        After writing, confirm: "BATCH 3 WRITTEN — 3 chapters."

    STEP 2b — Read back all 3 batch files, then combine into the FINAL file:
        FileReaderTool("{_STAGING}/hebrew_prose_part1.md")
        FileReaderTool("{_STAGING}/hebrew_prose_part2.md")
        FileReaderTool("{_STAGING}/hebrew_prose_part3.md")
        Then call SafeFileWriterTool to write {_STAGING}/hebrew_prose.md with ALL 9 chapters.

    CRITICAL: Do NOT write all 9 chapters in a single SafeFileWriterTool call.
    You MUST write 3 separate batch files first, then combine them.

    Per-chapter content:
        • Section marker: ## CH01: <Hebrew title from outline>
        • 3+ subsections marked: ### <Hebrew subsection title>
        • Inline markers for equations: [EQUATION: description]
        • Inline markers for figures: [FIGURE: fig_filename.png]
        • Inline markers for tables: [TABLE: description]
        • Citation markers: [CITE: AuthorYear]

    EM DASH PROHIBITION (ABSOLUTE RULE — violating this breaks the PDF):
        The character — (U+2014) is COMPLETELY FORBIDDEN anywhere in the output.
        Use colon (:) or comma (,) instead. Check every sentence.

    Language rules:
        • Prose in Hebrew. Technical acronyms stay in English: SLAM, EKF, LiDAR, UAV, IMU.
        • Do NOT write LaTeX commands — only prose text with inline markers.

STEP 3 — After writing, output a short confirmation: 'HEBREW PROSE COMPLETE'.
    Do NOT output the full prose in your final response — just the confirmation.
    The prose is already saved to the file by SafeFileWriterTool.
""".strip(),
        expected_output=(
            f"Hebrew prose written in 3 batches (part1/part2/part3) then combined into {_STAGING}/hebrew_prose.md. "
            f"≥1200-1800 words per chapter. Zero em dash characters. Confirmation: 'HEBREW PROSE COMPLETE'."
        ),
        agent=writer,
        context=context,
        output_file=f"{_STAGING}/hebrew_prose_status.md",
    )
