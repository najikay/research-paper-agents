"""
src/tasks/staging.py
====================
Shared staging-directory constant for all task factories.

All intermediate outputs are staged to outputs/current/ during a run.
main.py moves them to the per-run archive folder on completion and cleans up.
Always use this constant — never hardcode "outputs/" directly.
"""

_STAGING = "outputs/current"
