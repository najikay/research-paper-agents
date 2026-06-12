"""
src/tasks/research_tasks.py
============================
Backward-compatible facade. The task factories were split into focused modules
(tasks_research_core, tasks_domain, tasks_prose, tasks_latex_*, tasks_assemble,
tasks_remediate, tasks_smoke) to satisfy the 150-line-per-file rule. Existing
imports `from src.tasks.research_tasks import ...` continue to work unchanged.
"""
from src.tasks.staging import _STAGING
from src.tasks.domains import _DOMAIN_DESCRIPTIONS
from src.tasks.tasks_research_core import (
    create_task_outline, create_task_research, create_task_figures,
)
from src.tasks.tasks_domain import (
    create_task_domain_expert, create_task_fix_domain,
)
from src.tasks.tasks_prose import create_task_hebrew_prose
from src.tasks.tasks_latex_rules import _latex_shared_rules
from src.tasks.tasks_latex_parts import (
    create_task_latex_part1, create_task_latex_part2, create_task_latex,
)
from src.tasks.tasks_latex_split import (
    create_task_latex_a, create_task_latex_b, create_task_latex_c,
)
from src.tasks.tasks_assemble import (
    create_research_tasks, create_writing_tasks, create_all_tasks,
)
from src.tasks.tasks_remediate import (
    create_task_review, create_remediation_task,
)
from src.tasks.tasks_smoke import (
    create_task_latex_smoke, create_smoke_tasks,
)

__all__ = [
    "create_task_outline", "create_task_research", "create_task_figures",
    "create_task_domain_expert", "create_task_fix_domain",
    "create_task_hebrew_prose", "_latex_shared_rules",
    "create_task_latex_part1", "create_task_latex_part2", "create_task_latex",
    "create_task_latex_a", "create_task_latex_b", "create_task_latex_c",
    "create_research_tasks", "create_writing_tasks", "create_all_tasks",
    "create_task_review", "create_remediation_task",
    "create_task_latex_smoke", "create_smoke_tasks",
    "_DOMAIN_DESCRIPTIONS", "_STAGING",
]
