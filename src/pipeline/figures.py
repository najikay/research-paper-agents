"""
figures.py
==========
Fallback figure generation pipeline: stub diversification, cross-chapter
deduplication, and chapter-appropriate matplotlib figure creation.
"""

import re
from pathlib import Path

from src.config import logger
from src.pipeline.figure_renderer import (
    _CHAPTER_FIGURE_STYLE,
    _infer_style_from_name,
    _render_fallback_figure,
)


def _diversify_stub_figures(run_folder: Path) -> None:
    """
    Replace shared fig_stub.png references with chapter-specific filenames.

    In smoke mode (and sometimes when the VisualizationEngineer fails), every
    chapter points to the same ``figures/fig_stub.png``.  This function rewrites
    each chapter's \\includegraphics to use a unique per-chapter filename so the
    fallback generator can create visually distinct figures for each chapter.
    """
    chapters_dir = run_folder / "latex" / "chapters"
    if not chapters_dir.exists():
        return

    for tex_file in chapters_dir.glob("*.tex"):
        if tex_file.name == "cover.tex":
            continue
        text = tex_file.read_text(encoding="utf-8", errors="replace")
        if "fig_stub.png" not in text:
            continue
        ch_match = re.match(r"(ch\d+)", tex_file.name)
        if not ch_match:
            continue
        ch_id = ch_match.group(1)

        occurrence = [0]

        def _replace_stub(m: re.Match, _occ=occurrence, _ch=ch_id) -> str:  # noqa: B006
            _occ[0] += 1
            suffix = f"_{_occ[0]}" if _occ[0] > 1 else ""
            return m.group(0).replace("fig_stub.png", f"fig_{_ch}_auto{suffix}.png")

        new_text = re.sub(
            r'\\includegraphics(\[[^\]]*\])?\{figures/fig_stub\.png\}',
            _replace_stub,
            text,
        )
        if new_text != text:
            tex_file.write_text(new_text, encoding="utf-8")
            logger.info(f"[Diversify] {tex_file.name}: replaced fig_stub.png -> chapter-specific names")


def _deduplicate_cross_chapter_figures(run_folder: Path) -> None:
    """
    When two different chapters reference the same figure file, rename the
    second occurrence to a chapter-specific name. The fallback figure generator
    will then create a distinct figure for it.
    """
    chapters_dir = run_folder / "latex" / "chapters"
    if not chapters_dir.exists():
        return

    fig_usage: dict[str, list[Path]] = {}
    for tex_file in sorted(chapters_dir.glob("ch*.tex")):
        text = tex_file.read_text(encoding="utf-8", errors="replace")
        for fig_ref in re.findall(
            r'\\includegraphics(?:\[[^\]]*\])?\{figures/([^}]+)\}', text
        ):
            if fig_ref == "fig_stub.png":
                continue
            fig_usage.setdefault(fig_ref, []).append(tex_file)

    for fig_name, users in fig_usage.items():
        if len(users) <= 1:
            continue
        for tex_file in users[1:]:
            ch_match = re.match(r"(ch\d+)", tex_file.name)
            ch_id = ch_match.group(1) if ch_match else "dup"
            base, ext = fig_name.rsplit(".", 1) if "." in fig_name else (fig_name, "png")
            new_name = f"{base}_{ch_id}.{ext}"
            text = tex_file.read_text(encoding="utf-8", errors="replace")
            new_text = text.replace(f"figures/{fig_name}", f"figures/{new_name}")
            if new_text != text:
                tex_file.write_text(new_text, encoding="utf-8")
                logger.info(f"[Dedup] {tex_file.name}: {fig_name} -> {new_name}")


def _generate_fallback_figures(run_folder: Path) -> None:
    """
    For any figure referenced in chapter .tex files that doesn't exist yet,
    generate a real, chapter-appropriate matplotlib figure.
    """
    figures_dir = run_folder / "latex" / "figures"
    chapters_dir = run_folder / "latex" / "chapters"
    if not chapters_dir.exists():
        return

    referenced: dict[str, str] = {}
    for tex_file in chapters_dir.glob("*.tex"):
        text = tex_file.read_text(encoding="utf-8", errors="replace")
        ch_match = re.match(r"(ch\d+)", tex_file.name)
        ch_id = ch_match.group(1) if ch_match else "unknown"
        for fig_ref in re.findall(
            r'\\includegraphics(?:\[[^\]]*\])?\{figures/([^}]+)\}', text
        ):
            if fig_ref not in referenced:
                referenced[fig_ref] = ch_id

    stub_size = 69
    missing: list[tuple[str, str]] = []
    for fig_name, ch_id in referenced.items():
        fig_path = figures_dir / fig_name
        if not fig_path.exists() or fig_path.stat().st_size <= stub_size + 20:
            missing.append((fig_name, ch_id))

    if not missing:
        return

    logger.info(f"[Fallback] Generating {len(missing)} fallback figures: "
                f"{[n for n, _ in missing]}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        logger.warning("[Fallback] matplotlib not available -- skipping")
        return

    figures_dir.mkdir(parents=True, exist_ok=True)

    for fig_name, ch_id in missing:
        try:
            label = fig_name.replace("fig_", "").replace(".png", "").replace("_", " ").title()
            style = _CHAPTER_FIGURE_STYLE.get(ch_id, "")
            if not style:
                style = _infer_style_from_name(fig_name)

            _render_fallback_figure(plt, np, figures_dir / fig_name, label, style)
            logger.info(f"[Fallback] Generated: {fig_name} (style={style})")
        except Exception as e:
            logger.warning(f"[Fallback] Failed to generate {fig_name}: {e}")
            plt.close("all")
