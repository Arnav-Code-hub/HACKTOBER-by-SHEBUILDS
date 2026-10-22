"""Token accounting and the daily budget guardrail.

A runaway retry loop against a paid API is a real way to lose a hackathon.
Calls are refused once DAILY_TOKEN_BUDGET is exceeded.
"""

# TODO(cost): per-capability token accounting, budget enforcement.
