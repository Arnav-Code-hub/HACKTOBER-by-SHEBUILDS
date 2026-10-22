"""Business logic for auth. THE PUBLIC FACE of this module.

Firebase token exchange, session issue and refresh.

# Module boundary: other modules may import this file and schemas.py.
# They must NEVER import models.py or repository.py — see the import-linter
# contract in pyproject.toml. That rule is what makes this module extractable
# into its own service later without touching a single caller.
"""

# TODO(auth): service functions.
