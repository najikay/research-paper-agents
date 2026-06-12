"""
sanitizer_figures.py
====================
PNG dimension reading and wide-figure upgrade helpers used by the LaTeX sanitizer.

Detects figures whose PNG aspect ratio (width/height) > 1.8 and converts
single-column \\begin{figure} to \\begin{figure*} for IEEE two-column format.
"""

import re
import struct
from pathlib import Path


def _get_png_dimensions(png_path: Path) -> tuple[int, int] | None:
    """Read width and height from a PNG file header (bytes 16-23). No deps needed."""
    try:
        with open(png_path, 'rb') as f:
            header = f.read(24)
            if len(header) < 24 or header[:8] != b'\x89PNG\r\n\x1a\n':
                return None
            w, h = struct.unpack('>II', header[16:24])
            return (w, h)
    except (OSError, struct.error):
        return None


def _upgrade_wide_figures(text: str, figures_dir: Path) -> str:
    """
    Fix 24: Upgrade single-column \\begin{figure} to \\begin{figure*} for wide images.

    Detects figures whose PNG aspect ratio (width/height) > 1.8 and converts:
      \\begin{figure}[htbp]  ->  \\begin{figure*}[htbp]
      width=0.98\\columnwidth ->  width=\\textwidth
      \\end{figure}           ->  \\end{figure*}

    This makes wide charts, architecture diagrams, and multi-panel figures span
    both columns in IEEE two-column format -- matching real paper conventions and
    significantly increasing page utilization.
    """
    # Find all single-column figure blocks (not already figure*)
    pattern = re.compile(
        r'(\\begin\{figure\})(\[[^\]]*\])(.*?)(\\end\{figure\})',
        re.DOTALL,
    )

    def _maybe_upgrade(m: re.Match) -> str:
        _begin, placement, body, _end = m.group(1), m.group(2), m.group(3), m.group(4)
        # Extract the figure filename from \includegraphics
        fig_match = re.search(r'\\includegraphics(?:\[[^\]]*\])?\{figures/([^}]+)\}', body)
        if not fig_match:
            return m.group(0)  # no includegraphics -- leave unchanged

        fig_name = fig_match.group(1)
        fig_path = figures_dir / fig_name
        dims = _get_png_dimensions(fig_path)
        if dims is None:
            return m.group(0)  # can't read dimensions -- leave unchanged

        w, h = dims
        if h == 0:
            return m.group(0)

        aspect = w / h
        # Upgrade if aspect ratio > 1.8 (clearly wide/landscape)
        if aspect > 1.8:
            new_body = body.replace(r'width=0.98\columnwidth', r'width=\textwidth')
            new_body = new_body.replace(r'width=0.9\columnwidth', r'width=\textwidth')
            new_body = new_body.replace(r'width=\columnwidth', r'width=\textwidth')
            return r'\begin{figure*}' + placement + new_body + r'\end{figure*}'

        return m.group(0)

    return pattern.sub(_maybe_upgrade, text)
