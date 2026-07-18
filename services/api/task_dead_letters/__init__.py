"""Dead-letter storage for exhausted Celery tasks (DEV-55)."""

from .models import TaskDeadLetter, ensure_task_dead_letters_schema
from .repository import record_dead_letter

__all__ = [
    "TaskDeadLetter",
    "ensure_task_dead_letters_schema",
    "record_dead_letter",
]
