"""
src/tools/code_executor.py
===========================
PythonCodeExecutorTool — sandboxed Python execution for figure generation.
"""

from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from src.config import CODE_EXECUTOR_TIMEOUT, PROJECT_ROOT, logger

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
# At runtime PythonCodeExecutorTool is always instantiated with figures_dir
# pointing to {run_folder}/latex/figures/ so this constant is never hit.
_DEFAULT_FIGURES_DIR: Path = PROJECT_ROOT / "latex" / "figures"


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------

class CodeExecutorInput(BaseModel):
    """Arguments for PythonCodeExecutorTool: a complete matplotlib `code` script and the `output_filename` (.png basename) to save."""

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
    """Wrap the user code in the template (Agg backend + injected `output_path`) and return the full script as a string."""
    return _SCRIPT_TEMPLATE.format(
        output_path=str(output_path),
        user_code=textwrap.dedent(code),
    )


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------

class PythonCodeExecutorTool(BaseTool):
    """
    Executes a Python matplotlib script in a sandboxed subprocess.
    Instantiate with figures_dir pointing at {run_folder}/latex/figures/.
    """

    name: str = "PythonCodeExecutorTool"
    description: str = (
        "Execute a Python matplotlib script to generate a 300 DPI PNG figure. "
        "Supports matplotlib, mpl_toolkits.mplot3d, numpy, scipy, pandas. "
        "Provide the complete script in `code` and the output filename in "
        "`output_filename` (e.g. 'fig_trajectory_3d.png'). "
        "The variable `output_path` is pre-injected — call "
        "plt.savefig(output_path, dpi=300, bbox_inches='tight') in your script. "
        "Returns the absolute path on success or an error message on failure."
    )
    args_schema: type[BaseModel] = CodeExecutorInput
    # Per-run figures directory — set by crew.py at instantiation time.
    figures_dir: Path = _DEFAULT_FIGURES_DIR

    def _run(self, code: str, output_filename: str, **kwargs: Any) -> str:
        """Validate imports, run the script in a subprocess, and return a SUCCESS message with the saved figure's path or an ERROR/security-block message."""
        # 0. Sanitise filename
        if not output_filename.endswith(".png"):
            return f"ERROR: output_filename must end in .png, got {output_filename!r}"
        output_filename = Path(output_filename).name  # strip any path component
        output_path = self.figures_dir / output_filename

        # 1. AST import validation
        violations = validate_imports(code)
        if violations:
            msg = "SECURITY BLOCK — forbidden imports:\n" + "\n".join(
                f"  • {v}" for v in violations
            )
            logger.warning(f"PythonCodeExecutorTool blocked: {violations}")
            return msg

        # 2. Ensure output directory exists
        self.figures_dir.mkdir(parents=True, exist_ok=True)

        # 3. Build script
        script = _build_script(code, output_path)

        # 4. Write to temp file and execute
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", prefix="nav_fig_",
            delete=False, encoding="utf-8",
        ) as tmp:
            tmp.write(script)
            tmp_path = Path(tmp.name)

        logger.debug(
            f"PythonCodeExecutorTool: running {tmp_path.name} "
            f"→ {output_filename} (timeout={CODE_EXECUTOR_TIMEOUT}s)"
        )

        try:
            result = subprocess.run(
                [sys.executable, str(tmp_path)],
                capture_output=True,
                text=True,
                timeout=CODE_EXECUTOR_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            tmp_path.unlink(missing_ok=True)
            return (
                f"ERROR: script timed out after {CODE_EXECUTOR_TIMEOUT}s. "
                "Simplify the figure or reduce data resolution."
            )
        finally:
            tmp_path.unlink(missing_ok=True)

        # 5. Check return code
        if result.returncode != 0:
            stderr = result.stderr[-1200:] if result.stderr else "(no stderr)"
            return (
                f"ERROR: script exited with code {result.returncode}.\n"
                f"stderr:\n{stderr}"
            )

        # 6. Verify output file was created
        if not output_path.exists():
            return (
                f"ERROR: script completed but {output_filename!r} not found in "
                f"{self.figures_dir}. Ensure script calls "
                f"plt.savefig(output_path, dpi=300, bbox_inches='tight')."
            )

        size_kb = output_path.stat().st_size // 1024
        logger.info(f"PythonCodeExecutorTool: saved {output_filename} ({size_kb} KB)")
        return (
            f"SUCCESS: figure saved to {output_path} ({size_kb} KB). "
            f"stdout: {result.stdout.strip()[:300] if result.stdout else '(none)'}"
        )


if __name__ == "__main__":
    _SINE = """
import matplotlib.pyplot as plt
import numpy as np
t = np.linspace(0, 2 * np.pi, 400)
fig, ax = plt.subplots(figsize=(6, 4))
ax.plot(t, np.sin(t), color="#1f77b4", linewidth=2)
ax.set_title("Self-test — sine wave")
ax.set_xlabel("t [rad]")
ax.set_ylabel("sin(t)")
fig.tight_layout()
plt.savefig(output_path, dpi=300, bbox_inches="tight")
plt.close("all")
"""
    tool = PythonCodeExecutorTool()
    print(tool._run(code=_SINE, output_filename="selftest_sine.png"))
