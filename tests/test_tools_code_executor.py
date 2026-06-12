"""
tests/test_tools_code_executor.py
==================================
Unit tests for validate_imports() and PythonCodeExecutorTool.
"""

from __future__ import annotations

from src.tools.code_executor import PythonCodeExecutorTool, validate_imports

# ---------------------------------------------------------------------------
# validate_imports — whitelist tests
# ---------------------------------------------------------------------------

def test_validate_imports_allows_matplotlib():
    """import matplotlib.pyplot should produce no violations."""
    assert validate_imports("import matplotlib.pyplot as plt") == []


def test_validate_imports_allows_numpy():
    """import numpy should produce no violations."""
    assert validate_imports("import numpy as np") == []


def test_validate_imports_allows_scipy():
    """import scipy.signal should produce no violations."""
    assert validate_imports("import scipy.signal") == []


def test_validate_imports_blocks_socket():
    """import socket must produce at least one violation."""
    violations = validate_imports("import socket")
    assert len(violations) > 0
    assert any("socket" in v for v in violations)


def test_validate_imports_blocks_subprocess():
    """import subprocess must produce at least one violation."""
    violations = validate_imports("import subprocess")
    assert len(violations) > 0
    assert any("subprocess" in v for v in violations)


def test_validate_imports_blocks_requests():
    """import requests must produce at least one violation."""
    violations = validate_imports("import requests")
    assert len(violations) > 0
    assert any("requests" in v for v in violations)


def test_validate_imports_blocks_from_import():
    """from flask import Flask must produce at least one violation."""
    violations = validate_imports("from flask import Flask")
    assert len(violations) > 0
    assert any("flask" in v for v in violations)


def test_validate_imports_catches_syntax_error():
    """Code with a SyntaxError must return a violation list containing 'SyntaxError'."""
    violations = validate_imports("def broken(:\n    pass")
    assert len(violations) > 0
    assert any("SyntaxError" in v for v in violations)


def test_validate_imports_clean_code():
    """Empty string (no imports) must return an empty violations list."""
    assert validate_imports("") == []


# ---------------------------------------------------------------------------
# PythonCodeExecutorTool tests
# ---------------------------------------------------------------------------

def test_executor_blocks_forbidden_import():
    """Tool must return a SECURITY BLOCK string when code contains a forbidden import."""
    tool = PythonCodeExecutorTool()
    bad_code = "import socket\nprint(socket.gethostname())"
    result = tool._run(code=bad_code, output_filename="fig_test.png")
    assert "SECURITY BLOCK" in result


def test_executor_rejects_non_png():
    """Tool must return an ERROR when output_filename does not end in .png."""
    tool = PythonCodeExecutorTool()
    result = tool._run(code="import matplotlib.pyplot as plt", output_filename="fig.jpg")
    assert result.startswith("ERROR")
    assert ".png" in result


def test_executor_generates_png(tmp_path):
    """Tool must save a PNG file and return SUCCESS for a valid minimal matplotlib script."""
    figures_dir = tmp_path / "figures"
    figures_dir.mkdir(parents=True)

    simple_code = (
        "import matplotlib.pyplot as plt\n"
        "import numpy as np\n"
        "fig, ax = plt.subplots()\n"
        "ax.plot([0, 1], [0, 1])\n"
        "plt.savefig(output_path, dpi=72, bbox_inches='tight')\n"
        "plt.close('all')\n"
    )

    tool = PythonCodeExecutorTool(figures_dir=figures_dir)
    result = tool._run(code=simple_code, output_filename="fig_test_output.png")

    assert "SUCCESS" in result, f"Expected SUCCESS, got: {result}"
    assert (figures_dir / "fig_test_output.png").exists()
