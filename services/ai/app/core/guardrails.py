"""Output validation and safety checks.

Nothing an LLM produces is trusted. Every response is parsed into a Pydantic
schema before it leaves this service, so a hallucinated category or a malformed
score is rejected here rather than written to the database.

Report text is USER INPUT reaching a model — treat it as data, never as
instructions. Prompts must delimit it explicitly.
"""

# TODO(guardrails): schema validation, injection defences, PII redaction.
