# Prompts

Versioned prompt templates (Jinja2), loaded by `app/core/prompt_loader.py`.

**Prompts are code.** They change model behaviour the way code changes program
behaviour, so they get review, git history and a changelog entry when they move.
Never inline a prompt as a string literal in a capability.

## Conventions

- One file per prompt: `<capability>/<task>.jinja` — e.g. `classification/classify_report.jinja`
- A prompt file starts with a comment block: purpose, expected variables, output schema
- `StrictUndefined` is on, so a missing variable raises instead of rendering empty
- **Citizen report text is untrusted input.** Wrap it in explicit delimiters and
  instruct the model to treat it as data. A report that says "ignore previous
  instructions" must classify as a report, not act as a command.
- Changing a prompt means re-running its eval suite (`make evals`) before merge
