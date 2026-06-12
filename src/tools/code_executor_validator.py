"""
src/tools/code_executor_validator.py
======================================
Import validation, script building, and input schema for PythonCodeExecutorTool.
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

from pydantic import BaseModel, Field

from src.config import PROJECT_ROOT

# ---------------------------------------------------------------------------
# Approved import whitelist
# ---------------------------------------------------------------------------

APPROVED_IMPORTS: frozenset[str] = frozenset({
    "matplotlib", "mpl_toolkits",
    "matplotlib.pyplot", "matplotlib.patches", "matplotlib.colors",
    "matplotlib.cm", "matplotlib.ticker", "matplotlib.gridspec",
    "matplotlib.patheffects", "matplotlib.lines", "matplotlib.collections",
    "numpy", "scipy", "scipy.signal", "scipy.ndimage", "scipy.fft",
    "pandas",
    "pathlib", "os", "os.path", "math", "json", "csv", "io",
    "base64", "collections", "itertools", "functools", "typing",
    "dataclasses", "enum", "re", "datetime", "textwrap", "warnings", "sys",
})

# Default figures directory — used only when no run_folder is configured.
_DEFAULT_FIGURES_DIR: Path = PROJECT_ROOT / "latex" / "figures"


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------

class CodeExecutorInput(BaseModel):
    """Arguments for PythonCodeExecutorTool."""

    code: str = Field(
        ...,
        description=(
            "Complete Python script that generates a matplotlib figure and "
            "saves it via plt.savefig(output_path, dpi=300, bbox_inches='tight'). "
            "The variable `output_path` is injected automatically by the executor."
        ),
    )
    output_filename: str = Field(
        ...,
        description=(
            "Basename only (e.g. 'fig_trajectory_3d.png'). "
            "Must end in .png. Saved to the run's figures directory."
        ),
    )


# ---------------------------------------------------------------------------
# AST validator
# ---------------------------------------------------------------------------

def validate_imports(code: str) -> list[str]:
    """
    Parse code with ast and return a list of violation strings.
    Returns [] if the script is clean.
    """
    violations: list[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [f"SyntaxError: {exc}"]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top not in APPROVED_IMPORTS and alias.name not in APPROVED_IMPORTS:
                    violations.append(f"Forbidden import: {alias.name!r}")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                if top not in APPROVED_IMPORTS and node.module not in APPROVED_IMPORTS:
                    violations.append(f"Forbidden 'from' import: {node.module!r}")
    return violations


# ---------------------------------------------------------------------------
# Script builder
# ---------------------------------------------------------------------------

_SCRIPT_TEMPLATE = """\
import matplotlib
matplotlib.use("Agg")

output_path = {output_path!r}

{user_code}
"""


def _build_script(code: str, output_path: Path) -> str:
    """Wrap user code in the template (Agg backend + injected output_path)."""
    return _SCRIPT_TEMPLATE.format(
        output_path=str(output_path),
        user_code=textwrap.dedent(code),
    )
