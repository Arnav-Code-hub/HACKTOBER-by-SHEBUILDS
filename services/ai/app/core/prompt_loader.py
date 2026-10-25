"""Loads versioned prompt templates from prompts/.

Prompts are files, not string literals, because they change model behaviour the
way code changes program behaviour — they belong in review and in git history.
"""

from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"


@lru_cache
def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(PROMPT_DIR),
        undefined=StrictUndefined,  # a missing variable fails loudly, not silently
        autoescape=False,
    )


def render(template_name: str, **context: object) -> str:
    """Render `prompts/<template_name>` with the given context."""
    return _env().get_template(template_name).render(**context)
