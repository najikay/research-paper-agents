"""
src/tools/code_executor.py
===========================
PythonCodeExecutorTool — sandboxed Python execution for figure generation.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel

from src.config import CODE_EXECUTOR_TIMEOUT, logger
from src.tools.code_executor_validator import (
    _DEFAULT_FIGURES_DIR,
    APPROVED_IMPORTS,  # noqa: F401 — re-export
    CodeExecutorInput,
    _build_script,
    validate_imports,
)


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
    figures_dir: Path = _DEFAULT_FIGURES_DIR

    def _run(self, code: str, output_filename: str, **kwargs: Any) -> str:
        """Validate imports, run the script, and return SUCCESS or ERROR message."""
        # 0. Sanitise filename
        if not output_filename.endswith(".png"):
            return f"ERROR: output_filename must end in .png, got {output_filename!r}"
        output_filename = Path(output_filename).name
        output_path = self.figures_dir / output_filename

        # 1. AST import validation
        violations = validate_imports(code)
        if violations:
            msg = "SECURITY BLOCK — forbidden imports:\n" + "\n".join(
                f"  * {v}" for v in violations
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
